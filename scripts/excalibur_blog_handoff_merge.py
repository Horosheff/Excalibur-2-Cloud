#!/usr/bin/env python3
"""Atomically merge expected parallel-agent fragments into the runtime handoff."""
from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path

_TOPIC_ID_RE = re.compile(r"(?m)^topic_id:\s*(B\d+)\s*$")


def parse_fragment(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        hint = ""
        if text.lstrip().startswith("==="):
            hint = (
                " (body-only marker block; add YAML frontmatter per "
                "shared/pipeline-fragment-protocol.md — B65/INC-20260720-1556)"
            )
        raise ValueError(f"{path}: frontmatter missing{hint}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{path}: frontmatter terminator missing")
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        meta[key.strip()] = value.strip()
    for key in ("role", "status", "completed_at", "incident_report", "topic_id"):
        if not meta.get(key):
            raise ValueError(f"{path}: frontmatter {key} missing")
    status = meta["status"]
    if status in {"✅", "❌", "ok", "OK", "pass", "blocker"}:
        raise ValueError(
            f"{path}: status={status!r} invalid; use PASS or BLOCKER "
            "(not emoji/lowercase) — shared/pipeline-fragment-protocol.md"
        )
    topic = meta["topic_id"]
    if not re.fullmatch(r"B\d+", topic):
        raise ValueError(
            f"{path}: topic_id={topic!r} invalid; expect B<digits> "
            "(INC-20260810-1620 stale-fragment guard)"
        )
    return meta, text[end + 5 :].strip()


def handoff_topic_id(text: str) -> str | None:
    """First topic_id in handoff body (usually SCOUT / current run)."""
    match = _TOPIC_ID_RE.search(text)
    return match.group(1) if match else None


def block_for(role: str, body: str) -> str:
    return f"\n<!-- EXCALIBUR FRAGMENT role={role} -->\n{body}\n<!-- /EXCALIBUR FRAGMENT -->\n"


def replace_role(handoff: str, role: str, body: str) -> str:
    pattern = re.compile(
        rf"\n<!-- EXCALIBUR FRAGMENT role={re.escape(role)} -->.*?<!-- /EXCALIBUR FRAGMENT -->\n",
        flags=re.S,
    )
    block = block_for(role, body)
    if pattern.search(handoff):
        return pattern.sub(block, handoff)
    return handoff.rstrip() + block


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True)
    parser.add_argument("--fragments-dir", required=True)
    parser.add_argument("--wave", required=True, help="comma-separated fragment basenames")
    parser.add_argument(
        "--expect-topic-id",
        default=None,
        help="reject fragments whose frontmatter topic_id differs (INC-20260810-1620)",
    )
    args = parser.parse_args()
    handoff = Path(args.handoff)
    fragments = Path(args.fragments_dir)
    expected = [item.strip() for item in args.wave.split(",") if item.strip()]
    if not handoff.is_file():
        parser.error(f"handoff missing: {handoff}")
    text = handoff.read_text(encoding="utf-8")
    expected_topic = args.expect_topic_id or handoff_topic_id(text)
    merged: list[str] = []
    for name in expected:
        path = fragments / f"{name}.md"
        if not path.is_file():
            parser.error(f"expected fragment missing: {path}")
        try:
            meta, body = parse_fragment(path)
        except ValueError as exc:
            parser.error(str(exc))
        if meta["status"] != "PASS":
            parser.error(f"{path}: status={meta['status']} (need PASS)")
        if not body:
            parser.error(f"{path}: body missing")
        frag_topic = meta["topic_id"]
        if expected_topic and frag_topic != expected_topic:
            parser.error(
                f"{path}: topic_id={frag_topic!r} != expect {expected_topic!r} "
                "(stale fragment from prior run? Write fragment fully before "
                "merge — INC-20260810-1620; Cover/Schema must not call merge "
                "in the same parallel tool-batch as Write fragment)"
            )
        text = replace_role(text, meta["role"], body)
        merged.append(meta["role"])

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=handoff.parent, delete=False) as tmp:
        tmp.write(text)
        tmp_name = tmp.name
    os.replace(tmp_name, handoff)
    topic_note = f" topic_id={expected_topic}" if expected_topic else ""
    print(f"OK merged={','.join(merged)} handoff={handoff}{topic_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
