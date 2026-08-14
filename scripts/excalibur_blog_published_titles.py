#!/usr/bin/env python3
"""Build titles-only ledger for Writer/Research (never article bodies).

Canon: long-term memory = published titles only (default last 30 days).
Writer may know WHAT was already covered (title + slug), but must never open
old article.html / drafts / lessons / covers. never article.html as a title source.

Sources (in order for title text):
1. article.meta.json in article_dir (current in-flight article)
2. previous shared/published-titles.md row for same topic_id
3. humanized slug fallback

Reads ledger dates from shared/published-articles.md only.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from excalibur_blog_article_meta_index import is_stale_article_dirname

HEADER = """# Published titles only — не читать тела статей

Единственная долгосрочная память Excalibur BLOG: **заголовки** уже
опубликованных статей (окно ниже). Никаких article.html, cover PNG,
research-notes, drafts.

**Запрещено:** открывать `memory/blog/articles/*/article.html`, covers,
lessons, benchmarks, QA reports или соседние research-notes как образец
прозы. Заголовки — только anti-dup.
"""

DEFAULT_DAYS = 30


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def humanize_slug(slug: str) -> str:
    text = (slug or "").strip().strip("/").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else ""


def parse_iso_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def load_ledger_rows(root: Path) -> list[dict[str, str]]:
    path = root / "shared" / "published-articles.md"
    rows: list[dict[str, str]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| 20"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        rows.append(
            {
                "date": cells[0],
                "topic_id": cells[1].upper(),
                "slug": cells[2].strip().strip("/"),
                "url": cells[3],
                "status": cells[4].lower(),
            }
        )
    return rows


def load_existing_titles(path: Path) -> dict[str, str]:
    """topic_id -> title from an existing titles markdown table."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        topic = cells[0].upper()
        title = cells[2].strip()
        if not topic or topic.lower() == "topic_id" or set(topic) <= {"-"}:
            continue
        if title:
            out[topic] = title
    return out


def title_from_meta(article_dir: Path) -> str:
    meta_path = article_dir / "article.meta.json"
    if not meta_path.is_file():
        return ""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(meta, dict):
        return ""
    for key in ("title", "h1"):
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return ""


def find_article_dir(blog_dir: Path, topic_id: str, slug: str) -> Path | None:
    preferred = blog_dir / f"{topic_id}-{slug}"
    if preferred.is_dir() and not is_stale_article_dirname(preferred.name):
        return preferred
    prefix = f"{topic_id}-"
    matches: list[Path] = []
    if not blog_dir.is_dir():
        return None
    for path in sorted(blog_dir.iterdir()):
        if not path.is_dir() or is_stale_article_dirname(path.name):
            continue
        if path.name.upper().startswith(prefix.upper()):
            matches.append(path)
    if not matches:
        return None
    if slug:
        for path in matches:
            if path.name.endswith(f"-{slug}") or slug in path.name:
                return path
    return matches[0]


def build_titles(
    root: Path,
    *,
    statuses: set[str] | None = None,
    days: int | None = DEFAULT_DAYS,
    as_of: date | None = None,
    previous_titles: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    allowed = statuses or {"published"}
    blog_dir = root / "memory" / "blog" / "articles"
    prev = previous_titles if previous_titles is not None else {}
    cutoff: date | None = None
    if days is not None and days >= 0:
        cutoff = (as_of or date.today()) - timedelta(days=days)

    latest: dict[str, dict[str, str]] = {}
    for row in load_ledger_rows(root):
        if row["status"] not in allowed:
            continue
        row_date = parse_iso_date(row["date"])
        if cutoff is not None and (row_date is None or row_date < cutoff):
            continue
        topic_id = row["topic_id"]
        slug = row["slug"]
        article_dir = find_article_dir(blog_dir, topic_id, slug)
        title = title_from_meta(article_dir) if article_dir else ""
        if not title:
            title = prev.get(topic_id, "")
        if not title:
            title = humanize_slug(slug)
        latest[topic_id] = {
            "topic_id": topic_id,
            "slug": slug,
            "title": title,
            "status": row["status"],
            "date": row["date"],
        }
    return sorted(latest.values(), key=lambda r: (r["date"], r["topic_id"]))


def render_markdown(rows: list[dict[str, str]], *, days: int | None) -> str:
    window = (
        f"Окно: последние **{days}** дней (published only)."
        if days is not None and days >= 0
        else "Окно: все статусы/даты по фильтру запуска."
    )
    lines = [
        HEADER.strip(),
        "",
        window,
        "",
        "| topic_id | slug | title | status |",
        "|----------|------|-------|--------|",
    ]
    for row in rows:
        title = row["title"].replace("|", "/")
        lines.append(
            f"| {row['topic_id']} | {row['slug']} | {title} | {row['status']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_titles(
    root: Path,
    *,
    out_path: Path | None = None,
    article_dir: Path | None = None,
    days: int | None = DEFAULT_DAYS,
    statuses: set[str] | None = None,
) -> dict[str, Any]:
    shared_path = out_path or (root / "shared" / "published-titles.md")
    prev = load_existing_titles(shared_path)
    rows = build_titles(
        root,
        statuses=statuses,
        days=days,
        previous_titles=prev,
    )
    text = render_markdown(rows, days=days)
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    shared_path.write_text(text, encoding="utf-8")
    article_copy: Path | None = None
    if article_dir is not None:
        article_dir.mkdir(parents=True, exist_ok=True)
        article_copy = article_dir / "published-titles-only.md"
        article_copy.write_text(text, encoding="utf-8")
    return {
        "count": len(rows),
        "shared_path": str(shared_path),
        "article_copy": str(article_copy) if article_copy else None,
        "days": days,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="shared/published-titles.md")
    parser.add_argument(
        "--article-dir",
        type=Path,
        default=None,
        help="Also write published-titles-only.md into article dir",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Keep titles with ledger date within N days (default 30; -1 = no date filter)",
    )
    parser.add_argument(
        "--status",
        action="append",
        default=None,
        help="Status filter (repeatable). Default: published only",
    )
    args = parser.parse_args()
    root = args.root or project_root()
    days = None if args.days is not None and args.days < 0 else args.days
    statuses = set(s.lower() for s in args.status) if args.status else {"published"}
    result = write_titles(
        root,
        out_path=args.out,
        article_dir=args.article_dir,
        days=days,
        statuses=statuses,
    )
    print(
        f"OK titles={result['count']} days={result['days']} shared={result['shared_path']}"
    )
    if result["article_copy"]:
        print(f"article_copy={result['article_copy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
