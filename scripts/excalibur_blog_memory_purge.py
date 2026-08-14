#!/usr/bin/env python3
"""Purge local article scratch after publish — keep titles only.

Canon: done articles leave ONLY a title row in shared/published-titles.md.
No cover PNG, article.html, research, schema, or drafts stay in
memory/blog/articles/ for published topics.

Usage:
  python3 scripts/excalibur_blog_memory_purge.py --all-published
  python3 scripts/excalibur_blog_memory_purge.py --drop-topic B159
  python3 scripts/excalibur_blog_memory_purge.py --all-published --dry-run
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from excalibur_blog_article_meta_index import is_stale_article_dirname  # noqa: E402
from excalibur_blog_published_titles import (  # noqa: E402
    DEFAULT_DAYS,
    load_ledger_rows,
    write_titles,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def articles_dir(root: Path) -> Path:
    return root / "memory" / "blog" / "articles"


def handoff_topic_id(root: Path) -> str | None:
    for rel in (
        ".cursor/excalibur-blog-handoff.md",
        "shared/excalibur-blog-handoff.md",
    ):
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"(?im)^\s*topic_id\s*[:=]\s*(B\d+)\b", text)
        if m:
            return m.group(1).upper()
    return None


def topic_from_dirname(name: str) -> str | None:
    m = re.match(r"^(B\d+|WP\d+)-", name, re.I)
    return m.group(1).upper() if m else None


def published_topic_ids(root: Path) -> set[str]:
    return {
        row["topic_id"]
        for row in load_ledger_rows(root)
        if row["status"] == "published"
    }


def list_article_dirs(root: Path) -> list[Path]:
    base = articles_dir(root)
    if not base.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(base.iterdir()):
        if not path.is_dir() or is_stale_article_dirname(path.name):
            continue
        out.append(path)
    return out


def drop_dir(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"DRY-RUN rm -rf {path}")
        return
    shutil.rmtree(path)
    print(f"REMOVED {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--all-published",
        action="store_true",
        help="Delete article dirs whose topic_id is status=published in ledger",
    )
    parser.add_argument(
        "--drop-topic",
        action="append",
        default=[],
        help="Delete article dir(s) for topic_id (repeatable), e.g. B159",
    )
    parser.add_argument(
        "--keep-topic",
        action="append",
        default=[],
        help="Never delete this topic_id (repeatable)",
    )
    parser.add_argument(
        "--protect-handoff",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip topic_id from handoff if present (default true)",
    )
    parser.add_argument(
        "--refresh-titles",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rewrite shared/published-titles.md (30d published) after purge",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.all_published and not args.drop_topic:
        parser.error("Specify --all-published and/or --drop-topic")

    root = args.root or project_root()
    keep = {t.upper() for t in args.keep_topic}
    if args.protect_handoff:
        hid = handoff_topic_id(root)
        if hid:
            keep.add(hid)
            print(f"KEEP handoff topic_id={hid}")

    targets: list[Path] = []
    drop_ids = {t.upper() for t in args.drop_topic}
    published = published_topic_ids(root) if args.all_published else set()

    for path in list_article_dirs(root):
        tid = topic_from_dirname(path.name)
        if not tid or tid in keep:
            continue
        if tid in drop_ids or (args.all_published and tid in published):
            targets.append(path)

    if not targets:
        print("OK nothing_to_purge")
    else:
        print(f"purge_candidates={len(targets)}")
        for path in targets:
            drop_dir(path, dry_run=args.dry_run)

    if args.refresh_titles and not args.dry_run:
        result = write_titles(root, days=args.days, statuses={"published"})
        print(
            f"OK titles_refreshed count={result['count']} days={result['days']} "
            f"path={result['shared_path']}"
        )
    elif args.refresh_titles and args.dry_run:
        print("DRY-RUN skip titles refresh")

    # Remove bulky llms-full regenerated from deleted corpus
    llms_full = root / "memory" / "blog" / "llms-full.txt"
    if llms_full.is_file() and not args.dry_run and (args.all_published or args.drop_topic):
        # Regenerated by indexer from titles+current; wipe stale full dump now
        llms_full.write_text(
            "# Excalibur BLOG — llms-full (titles-only mode)\n"
            "> Full historical article bodies are not stored in git.\n"
            "> See shared/published-titles.md and live WordPress permalinks.\n",
            encoding="utf-8",
        )
        print(f"RESET {llms_full}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
