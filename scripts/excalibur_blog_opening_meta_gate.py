#!/usr/bin/env python3
"""Block research-brief / API-calque junk in article opening + meta description.

Opening lives in article.html (Sol final prose). Optional orphan lead.md is
scanned if present; missing file is OK.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from excalibur_blog_plain_language import allowlist_from_title, plain_language_errors
except ImportError:
    from scripts.excalibur_blog_plain_language import allowlist_from_title, plain_language_errors


# Calque of "API" that reads as machine Russian, not human voice.
STYK_API_RE = re.compile(
    r"стык(?:а|у|ом|е|и)?\s+(?:для\s+программ|с\s+(?:сайтом|api)|с\s+api)"
    r"|без\s+(?:готового\s+)?стыка"
    r"|где\s+стыка\s+нет"
    r"|открытого\s+стыка",
    re.IGNORECASE,
)

# Pipeline / research brief leaking into public text.
RESEARCH_BRIEF_RES = (
    re.compile(r"факты\s+запуска", re.I),
    re.compile(r"оговорк[аиуеы]\s+пресс", re.I),
    re.compile(r"смотрите\s+на\s+факты", re.I),
    re.compile(r"не\s+путайте\s+с\s+готовым", re.I),
    re.compile(r"VentureBeat\s+просит", re.I),
    re.compile(r"сверять\s+поколение", re.I),
    re.compile(r"reader_outcome|reader_problem|WORDSTAT|research_date", re.I),
    re.compile(r"^\s*\d{1,2}\s+[а-яё]+\s+20\d{2}\b", re.I | re.M),
    re.compile(r"^\s*\d{2}\.\d{2}\.20\d{2}\b", re.M),
)


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _hits(text: str) -> list[str]:
    found: list[str] = []
    if STYK_API_RE.search(text):
        found.append("api-calque-styk")
    for rx in RESEARCH_BRIEF_RES:
        m = rx.search(text)
        if m:
            found.append(f"research-brief:{m.group(0)[:48]}")
    return found


def check_article(article_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    orphan_lead = article_dir / "lead.md"
    meta_path = article_dir / "article.meta.json"
    html_path = article_dir / "article.html"

    if orphan_lead.is_file():
        lead = _plain(orphan_lead.read_text(encoding="utf-8"))
        for h in _hits(lead):
            errors.append(f"lead.md: {h}")

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            meta = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            errors.append("article.meta.json: invalid JSON")
            meta = {}
        blobs = [
            str(meta.get("description") or ""),
            str((meta.get("meta_ab") or {}).get("description_seo") or ""),
            str((meta.get("meta_ab") or {}).get("description_ctr") or ""),
            str((meta.get("meta_ab") or {}).get("description_aeo") or ""),
            str(meta.get("cover_hook") or ""),
        ]
        for i, blob in enumerate(blobs):
            for h in _hits(blob):
                errors.append(f"article.meta.json[{i}]: {h}")
    else:
        errors.append("article.meta.json missing")

    if html_path.is_file():
        raw_html = html_path.read_text(encoding="utf-8")
        html = _plain(raw_html)
        head = html[:900]
        for h in _hits(head):
            errors.append(f"article.html-head: {h}")
        if STYK_API_RE.search(html):
            errors.append("article.html: api-calque-styk")
        title = str(
            meta.get("h1")
            or meta.get("title")
            or ""
        )
        title_brief = {}
        tb_path = article_dir / "title-brief.json"
        if tb_path.is_file():
            try:
                loaded_tb = json.loads(tb_path.read_text(encoding="utf-8"))
                title_brief = loaded_tb if isinstance(loaded_tb, dict) else {}
            except json.JSONDecodeError:
                title_brief = {}
        allow = allowlist_from_title(
            title,
            str(title_brief.get("h1") or ""),
            str(title_brief.get("title") or ""),
            str(title_brief.get("subject") or ""),
        )
        # Opening must stay human Russian for beginners — not a term pile.
        errors.extend(
            plain_language_errors(
                head,
                allow=allow,
                max_latin=3,
                max_jargon=1,
                label="article.html-opening",
            )
        )
    else:
        errors.append("article.html missing")

    status = "PASS" if not errors else "BLOCK"
    return {
        "gate": "opening-meta",
        "status": status,
        "errors": errors,
        "article_dir": str(article_dir),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--article-dir", type=Path, required=True)
    ap.add_argument("-o", "--output", type=str, default="opening-meta-gate.json")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    if not article_dir.is_dir():
        print(f"BLOCKER: article-dir not found: {article_dir}", file=sys.stderr)
        return 2
    report = check_article(article_dir)
    out_name = Path(args.output).name
    out_path = article_dir / out_name
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
