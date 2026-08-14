#!/usr/bin/env python3
"""Structural preflight master gate — no prose rewrite.

Chains structural checks: canon, research report, links, html linter,
content-evidence, CTA, opening-meta.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _hard_ok(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    for key in ("status", "verdict"):
        raw = str(report.get(key) or "").strip().lower()
        if raw in {"pass", "ok"}:
            return True
        if raw:
            return False
    return False


def run_cmd(root: Path, argv: list[str]) -> int:
    proc = subprocess.run(argv, cwd=root, check=False)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Structural article preflight gate")
    parser.add_argument("--article-dir", type=Path, required=True)
    parser.add_argument("--site-base", type=str, default="")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("-o", "--output", type=str, default="structure-gate.json")
    args = parser.parse_args()
    root = project_root()
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    if not article_dir.is_dir():
        print(f"BLOCKER: article-dir not found: {article_dir}", file=sys.stderr)
        return 2

    html = article_dir / "article.html"
    if not html.is_file():
        print("BLOCKER: article.html missing", file=sys.stderr)
        return 2

    py = sys.executable
    scripts = root / "scripts"
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    canon = run_cmd(
        root,
        [py, str(scripts / "excalibur_blog_pipeline_canon.py"), "--article-dir", str(article_dir)],
    )
    record("pipeline_canon", canon == 0, f"exit={canon}")

    research = _load_json(article_dir / "research-agent-report.json")
    record(
        "research_agent_report",
        bool((article_dir / "research-notes.md").is_file()) and _hard_ok(research),
        f"status={(research or {}).get('status')}",
    )

    site_base = (args.site_base or os.environ.get("PUBLIC_SITE_URL") or "").strip()
    if args.skip_network:
        link = _load_json(article_dir / "link-verify.json")
        record("link_verify", _hard_ok(link), f"existing verdict={(link or {}).get('verdict')}")
    else:
        if not site_base:
            record("link_verify", False, "PUBLIC_SITE_URL / --site-base required")
        else:
            rc = run_cmd(
                root,
                [
                    py,
                    str(scripts / "excalibur_blog_link_verify.py"),
                    str(html),
                    "-o",
                    str(article_dir / "link-verify.json"),
                    "--site-base",
                    site_base,
                ],
            )
            link = _load_json(article_dir / "link-verify.json")
            record("link_verify", rc == 0 and _hard_ok(link), f"exit={rc}")

    lint_rc = run_cmd(
        root,
        [
            py,
            str(scripts / "excalibur_blog_html_linter.py"),
            str(html),
            "-o",
            str(article_dir / "html-linter-report.json"),
        ],
    )
    lint = _load_json(article_dir / "html-linter-report.json")
    record("html_linter", lint_rc == 0 and _hard_ok(lint), f"exit={lint_rc}")

    # content-evidence is optional legacy paperwork — skip if absent.
    if (article_dir / "content-evidence-report.json").is_file():
        evidence_rc = run_cmd(
            root,
            [
                py,
                str(scripts / "excalibur_blog_content_evidence_gate.py"),
                "--article-dir",
                str(article_dir),
            ],
        )
        evidence = _load_json(article_dir / "content-evidence-gate.json")
        record(
            "content_evidence",
            evidence_rc == 0 and _hard_ok(evidence),
            f"exit={evidence_rc}",
        )

    cta_rc = run_cmd(
        root,
        [
            py,
            str(scripts / "excalibur_blog_community_cta_gate.py"),
            "--article-dir",
            str(article_dir),
            "-o",
            "community-cta-gate.json",
        ],
    )
    cta = _load_json(article_dir / "community-cta-gate.json")
    record("community_cta", cta_rc == 0 and _hard_ok(cta), f"exit={cta_rc}")

    opening_rc = run_cmd(
        root,
        [
            py,
            str(scripts / "excalibur_blog_opening_meta_gate.py"),
            "--article-dir",
            str(article_dir),
            "-o",
            "opening-meta-gate.json",
        ],
    )
    opening = _load_json(article_dir / "opening-meta-gate.json")
    record("opening_meta", opening_rc == 0 and _hard_ok(opening), f"exit={opening_rc}")

    rewrite_rc = run_cmd(
        root,
        [
            py,
            str(scripts / "excalibur_blog_sol_rewrite_depth_gate.py"),
            "--article-dir",
            str(article_dir),
            "-o",
            "sol-rewrite-depth-gate.json",
        ],
    )
    rewrite = _load_json(article_dir / "sol-rewrite-depth-gate.json")
    record(
        "sol_rewrite_depth",
        rewrite_rc == 0 and _hard_ok(rewrite),
        f"exit={rewrite_rc}",
    )

    desc_rc = run_cmd(
        root,
        [
            py,
            str(scripts / "excalibur_blog_description_gate.py"),
            "--article-dir",
            str(article_dir),
            "-o",
            "description-gate.json",
        ],
    )
    desc = _load_json(article_dir / "description-gate.json")
    record("description", desc_rc == 0 and _hard_ok(desc), f"exit={desc_rc}")

    failed = [check["name"] for check in checks if not check["ok"]]
    report = {
        "gate": "structure",
        "status": "PASS" if not failed else "FAIL",
        "article_dir": str(article_dir.relative_to(root)).replace("\\", "/"),
        "checks": checks,
        "failed": failed,
        "note": "Structural/links/HTML only — does not rewrite prose.",
    }
    out = article_dir / Path(args.output).name
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Compat alias for older article dirs / checklists
    if Path(args.output).name != "geo-qa-gate.json":
        (article_dir / "geo-qa-gate.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
