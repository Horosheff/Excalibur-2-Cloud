#!/usr/bin/env python3
"""Excalibur BLOG LLMs Generator: AI-First Crawler Policy.

Generates and maintains standard llms.txt and llms-full.txt in the root folder,
providing LLM-readable indices and plain-text summaries of all blog articles.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.excalibur_blog_site_base import redact_site_base  # noqa: E402


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def strip_html(html: str) -> str:
    # Remove script and style tags completely
    html = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", html, flags=re.IGNORECASE)
    # Convert paragraph endings and headers to newlines
    html = re.sub(r"</?(p|h1|h2|h3|li|div|blockquote)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Remove all other HTML tags
    # chr(60)/chr(62) avoids a tag-like regex in source
    _lt, _gt = chr(60), chr(62)
    text = re.sub(_lt + "[^" + _gt + "]+" + _gt, "", html)
    # Normalize whitespaces and newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def load_one_article(article_dir: Path) -> dict[str, Any] | None:
    """Load a single in-flight article_dir (meta + html)."""
    if not article_dir.is_dir():
        return None
    meta_path = article_dir / "article.meta.json"
    html_path = article_dir / "article.html"
    if not meta_path.is_file() or not html_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error loading {article_dir.name}: {exc}")
        return None
    if not isinstance(meta, dict):
        return None
    meta_ab = meta.get("meta_ab", {}) if isinstance(meta.get("meta_ab"), dict) else {}
    aeo_desc = (
        meta_ab.get("description_aeo")
        or meta_ab.get("description_seo")
        or meta.get("description", "")
    )
    return {
        "slug": meta.get("slug", article_dir.name),
        "title": meta_ab.get("title_aeo")
        or meta_ab.get("title_seo")
        or meta.get("title")
        or meta.get("h1", article_dir.name),
        "description": aeo_desc,
        "plain_text": strip_html(html_path.read_text(encoding="utf-8")),
    }


def load_articles(blog_dir: Path) -> list[dict[str, Any]]:
    """Load local article dirs (current scratch only in titles-only canon)."""
    articles = []
    if not blog_dir.is_dir():
        return articles

    for article_dir in blog_dir.iterdir():
        if not article_dir.is_dir():
            continue
        row = load_one_article(article_dir)
        if row:
            articles.append(row)
    return articles


def load_articles_from_titles(titles_path: Path) -> list[dict[str, Any]]:
    """Titles-only index rows from shared/published-titles.md (no bodies)."""
    articles: list[dict[str, Any]] = []
    if not titles_path.is_file():
        return articles
    for line in titles_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        topic, slug, title = cells[0], cells[1], cells[2]
        if topic.lower() == "topic_id" or set(topic) <= {"-"}:
            continue
        if not slug or not title:
            continue
        articles.append(
            {
                "slug": slug.strip().strip("/"),
                "title": title,
                "description": "",
                "plain_text": "",
            }
        )
    return articles


def merge_articles_by_slug(
    base: list[dict[str, Any]], extra: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Prefer extra (current article with body) over titles-only rows."""
    by_slug: dict[str, dict[str, Any]] = {}
    for row in base:
        by_slug[str(row.get("slug") or "")] = row
    for row in extra:
        by_slug[str(row.get("slug") or "")] = row
    return [v for k, v in by_slug.items() if k]


def article_url(site_base: str, blog_path: str, slug: str) -> str:
    site_base = site_base.rstrip("/")
    path = "/" + blog_path.strip("/")
    if path == "/":
        return f"{site_base}/{slug}/"
    return f"{site_base}{path}/{slug}/"


def build_llms_txt(
    site_name: str,
    site_desc: str,
    articles: list[dict[str, Any]],
    site_base: str,
    blog_path: str,
) -> str:
    lines = [
        f"# {site_name}",
        f"> {site_desc}",
        "",
        "## Blog Articles",
        ""
    ]
    for a in articles:
        url = article_url(site_base, blog_path, a["slug"])
        lines.append(f"- [{a['title']}]({url}): {a['description']}")

    return "\n".join(lines) + "\n"


def build_llms_full_txt(site_name: str, articles: list[dict[str, Any]], site_base: str, blog_path: str) -> str:
    lines = [
        f"# {site_name} - Full LLM Knowledge Base",
        "This file contains full plain-text articles optimized for AI reasoning and semantic search.",
        "",
        "---",
        ""
    ]

    for a in articles:
        url = article_url(site_base, blog_path, a["slug"])
        lines.extend([
            f"## {a['title']}",
            f"- **URL**: {url}",
            f"- **Summary**: {a['description']}",
            "",
            a["plain_text"],
            "",
            "---",
            ""
        ])

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate AI-friendly llms.txt and llms-full.txt")
    ap.add_argument("--blog-dir", type=Path, default=None)
    ap.add_argument(
        "--titles",
        type=Path,
        default=None,
        help="Titles-only ledger (default: shared/published-titles.md). Canon: no historical bodies.",
    )
    ap.add_argument(
        "--article-dir",
        type=Path,
        default=None,
        help="Optional current article dir to include full plain text in llms-full",
    )
    ap.add_argument(
        "--mode",
        choices=("titles", "local-dirs", "titles+current"),
        default="titles+current",
        help="titles=ledger only; local-dirs=legacy scan blog-dir; titles+current=ledger + optional --article-dir",
    )
    ap.add_argument("--site-name", type=str, default="Excalibur-2-Cloud")
    ap.add_argument("--site-desc", type=str, default="Блог.")
    ap.add_argument(
        "--site-base",
        type=str,
        default="{{SITE_BASE}}",
        help="Git-safe site base for committed llms artifacts (default: {{SITE_BASE}}; publish expands)",
    )
    ap.add_argument("--blog-path", type=str, default="/", help="URL prefix for posts, e.g. /blog/ or /")
    ap.add_argument("--out-dir", type=Path, default=None, help="Output directory for llms.txt/llms-full.txt")
    args = ap.parse_args()

    root = project_root()
    blog_dir = args.blog_dir or root / "memory/blog/articles"
    if not blog_dir.is_absolute():
        blog_dir = root / blog_dir
    titles_path = args.titles or root / "shared" / "published-titles.md"
    if not titles_path.is_absolute():
        titles_path = root / titles_path
    article_dir = args.article_dir
    if article_dir is not None and not article_dir.is_absolute():
        article_dir = root / article_dir

    out_dir = args.out_dir or root
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    site_base = (args.site_base or "").strip() or "{{SITE_BASE}}"
    if site_base == "[REDACTED]":
        print(
            "WARN --site-base [REDACTED] is invalid for git artifacts; using {{SITE_BASE}}",
            file=sys.stderr,
        )
        site_base = "{{SITE_BASE}}"

    if args.mode == "local-dirs":
        articles = load_articles(blog_dir)
    else:
        articles = load_articles_from_titles(titles_path)
        if args.mode == "titles+current" and article_dir is not None:
            one = load_one_article(article_dir)
            if one:
                articles = merge_articles_by_slug(articles, [one])

    print(f"Loaded {len(articles)} articles to index for LLMs (mode={args.mode}).")

    llms_txt = redact_site_base(
        build_llms_txt(args.site_name, args.site_desc, articles, site_base, args.blog_path)
    )
    full_rows = [a for a in articles if str(a.get("plain_text") or "").strip()]
    if not full_rows:
        llms_full_txt = (
            f"# {args.site_name} - Full LLM Knowledge Base\n"
            "> Historical article bodies are not stored in git (titles-only canon).\n"
            "> See shared/published-titles.md and live WordPress permalinks.\n"
        )
    else:
        llms_full_txt = redact_site_base(
            build_llms_full_txt(args.site_name, full_rows, site_base, args.blog_path)
        )

    llms_path = out_dir / "llms.txt"
    llms_full_path = out_dir / "llms-full.txt"

    out_dir.mkdir(parents=True, exist_ok=True)
    llms_path.write_text(llms_txt, encoding="utf-8")
    llms_full_path.write_text(llms_full_txt, encoding="utf-8")

    print(f"llms.txt generated at {llms_path.relative_to(root) if root in llms_path.parents else llms_path}")
    print(f"llms-full.txt generated at {llms_full_path.relative_to(root) if root in llms_full_path.parents else llms_full_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
