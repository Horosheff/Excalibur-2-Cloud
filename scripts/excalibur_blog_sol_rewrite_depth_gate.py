#!/usr/bin/env python3
"""FAIL when Sol article.html is mostly copy-paste from drafts/writer.html.

Human-first-v2: Sol must rewrite the WHOLE article into tenant SOUL voice, not
only stamp a formula opening. A styled lead with Writer body left intact is FAIL.
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from excalibur_blog_plain_language import allowlist_from_title, plain_language_errors
except ImportError:
    from scripts.excalibur_blog_plain_language import allowlist_from_title, plain_language_errors

# Substantial prose only — skip short crumbs / CTA crumbs.
MIN_PARA_CHARS = 40

# Hard caps (measurable rewrite depth).
MAX_VERBATIM_RATIO = 0.30
MAX_BODY_VERBATIM_RATIO = 0.35
MAX_PARA_SET_JACCARD = 0.35
# Token Jaccard alone is noisy (shared product names/numbers); use as
# secondary hard fail only when also near the verbatim ceiling.
MAX_TOKEN_JACCARD_SOFT = 0.62
MAX_TOKEN_JACCARD_HARD = 0.72

# Formula stamps — corpus tools, not mandatory checklist. Cap density.
SIGNATURE_RES = (
    re.compile(r"многие\s+люди\s+уверены", re.I),
    re.compile(r"\bточнее,", re.I),
    re.compile(r"почему\s+никто", re.I),
    re.compile(r"все\s+просто:", re.I),
    re.compile(r"\bлюбопытно,", re.I),
    re.compile(r"им\s+кажется", re.I),
    re.compile(r"мне\s+всегда\s+было\s+интересно", re.I),
)
MAX_SIGNATURE_IN_OPENING = 2
MAX_SIGNATURE_IN_ARTICLE = 3
HEAVY_OPENER_RE = re.compile(
    r"^\s*(многие\s+люди\s+уверены|любопытно,|мне\s+всегда\s+было\s+интересно)",
    re.I,
)

# Writer label dumps left untouched: "<b>Архитектура:</b> …"
LABEL_DUMP_RE = re.compile(
    r"^\s*(?:[«\"]?.{0,2})?(?:[А-ЯЁA-Z][^:<]{1,40}):\s+\S",
)
MAX_LABEL_DUMPS = 3

# Body plain-language (soft relative to opening_meta): fail only on dumps.
BODY_MAX_LATIN = 14
BODY_MAX_JARGON = 4

SPLIT_RE = re.compile(r"</(?:p|h2|h3|li|blockquote)>", re.I)
# chr(60)/chr(62) so source has no tag-shaped regex for HTML transports.
_LT, _GT = chr(60), chr(62)
TAG_RE = re.compile(_LT + "[^" + _GT + "]+" + _GT)
TOKEN_RE = re.compile(r"[а-яёa-z0-9%./+-]+", re.I)
FIRST_H2_RE = re.compile(r"<h2\b", re.I)


def _plain_chunk(raw: str) -> str:
    text = TAG_RE.sub(" ", raw or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def extract_paragraphs(html: str) -> list[str]:
    """Split on block closers; keep substantial plain paragraphs."""
    # Drop figures so alt/cover noise does not inflate overlap.
    cleaned = re.sub(r"<figure\b[\s\S]*?</figure>", " ", html or "", flags=re.I)
    chunks = SPLIT_RE.split(cleaned)
    out: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        # Skip heading text alone (no prose rewrite obligation on H2 string).
        if re.search(r"<h[23]\b", chunk, re.I) and not re.search(r"<p\b", chunk, re.I):
            continue
        plain = _plain_chunk(chunk)
        if len(plain) < MIN_PARA_CHARS:
            continue
        if plain in seen:
            continue
        seen.add(plain)
        out.append(plain)
    return out


def _tokens(paragraphs: list[str]) -> set[str]:
    return set(TOKEN_RE.findall(" ".join(paragraphs)))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _body_html(html: str) -> str:
    m = FIRST_H2_RE.search(html or "")
    if not m:
        return html or ""
    return html[m.start() :]


def _opening_plain(html: str, limit: int = 900) -> str:
    cleaned = re.sub(r"<figure\b[\s\S]*?</figure>", " ", html or "", flags=re.I)
    m = FIRST_H2_RE.search(cleaned)
    head = cleaned[: m.start()] if m else cleaned
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", head)).strip()[:limit]


def _signature_hits(text: str) -> list[str]:
    found: list[str] = []
    for rx in SIGNATURE_RES:
        m = rx.search(text or "")
        if m:
            found.append(m.group(0).casefold())
    return found


def _label_dump_count(html: str) -> int:
    """Count Writer-style bold label dumps left in Sol output."""
    cleaned = re.sub(r"<figure\b[\s\S]*?</figure>", " ", html or "", flags=re.I)
    n = 0
    for m in re.finditer(r"<p\b[^>]*>([\s\S]*?)</p>", cleaned, re.I):
        inner = m.group(1)
        # Prefer explicit <b>Label:</b> pattern.
        if re.search(r"<b>\s*[^<]{1,40}:\s*</b>", inner, re.I):
            n += 1
            continue
        plain = _plain_chunk(inner)
        if LABEL_DUMP_RE.match(plain):
            n += 1
    return n


def check_article(article_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    soft: list[str] = []
    writer_path = article_dir / "drafts" / "writer.html"
    article_path = article_dir / "article.html"

    if not writer_path.is_file():
        return {
            "gate": "sol-rewrite-depth",
            "status": "BLOCK",
            "errors": ["drafts/writer.html missing"],
            "soft_warnings": [],
            "metrics": {},
            "article_dir": str(article_dir),
        }
    if not article_path.is_file():
        return {
            "gate": "sol-rewrite-depth",
            "status": "BLOCK",
            "errors": ["article.html missing"],
            "soft_warnings": [],
            "metrics": {},
            "article_dir": str(article_dir),
        }

    writer_html = writer_path.read_text(encoding="utf-8")
    article_html = article_path.read_text(encoding="utf-8")

    writer_paras = extract_paragraphs(writer_html)
    article_paras = extract_paragraphs(article_html)
    writer_set = set(writer_paras)
    article_set = set(article_paras)

    verbatim_hits = [p for p in article_paras if p in writer_set]
    verbatim_ratio = (
        len(verbatim_hits) / len(article_paras) if article_paras else 0.0
    )
    para_jaccard = _jaccard(writer_set, article_set)
    token_jaccard = _jaccard(_tokens(writer_paras), _tokens(article_paras))

    body_writer = extract_paragraphs(_body_html(writer_html))
    body_article = extract_paragraphs(_body_html(article_html))
    body_writer_set = set(body_writer)
    body_verbatim = [p for p in body_article if p in body_writer_set]
    body_verbatim_ratio = (
        len(body_verbatim) / len(body_article) if body_article else 0.0
    )

    metrics: dict[str, Any] = {
        "writer_paragraphs": len(writer_paras),
        "article_paragraphs": len(article_paras),
        "verbatim_paragraphs": len(verbatim_hits),
        "verbatim_ratio": round(verbatim_ratio, 4),
        "body_verbatim_ratio": round(body_verbatim_ratio, 4),
        "paragraph_set_jaccard": round(para_jaccard, 4),
        "token_jaccard": round(token_jaccard, 4),
        "max_verbatim_ratio": MAX_VERBATIM_RATIO,
        "max_body_verbatim_ratio": MAX_BODY_VERBATIM_RATIO,
        "max_paragraph_set_jaccard": MAX_PARA_SET_JACCARD,
    }

    if not article_paras:
        errors.append("article.html: no substantial paragraphs to score")
    if verbatim_ratio > MAX_VERBATIM_RATIO:
        errors.append(
            f"verbatim-paragraph-ratio {verbatim_ratio:.2f} > {MAX_VERBATIM_RATIO:.2f} "
            f"({len(verbatim_hits)}/{len(article_paras)} article paras still in writer.html)"
        )
    if body_article and body_verbatim_ratio > MAX_BODY_VERBATIM_RATIO:
        errors.append(
            f"body-verbatim-ratio {body_verbatim_ratio:.2f} > {MAX_BODY_VERBATIM_RATIO:.2f} "
            "(Sol rewrote lead but left Writer body mostly intact)"
        )
    if para_jaccard > MAX_PARA_SET_JACCARD:
        errors.append(
            f"paragraph-set-jaccard {para_jaccard:.2f} > {MAX_PARA_SET_JACCARD:.2f}"
        )
    if token_jaccard > MAX_TOKEN_JACCARD_HARD:
        errors.append(
            f"token-jaccard {token_jaccard:.2f} > {MAX_TOKEN_JACCARD_HARD:.2f} "
            "(near-copy of Writer wording)"
        )
    elif token_jaccard > MAX_TOKEN_JACCARD_SOFT and verbatim_ratio > 0.18:
        errors.append(
            f"token-jaccard {token_jaccard:.2f} with verbatim_ratio {verbatim_ratio:.2f} "
            "(shallow rewrite)"
        )

    opening = _opening_plain(article_html)
    full_plain = re.sub(r"\s+", " ", TAG_RE.sub(" ", article_html)).strip()
    sig_open = _signature_hits(opening)
    sig_all = _signature_hits(full_plain)
    metrics["signature_markers_opening"] = sig_open
    metrics["signature_markers_article"] = sig_all

    if len(sig_open) > MAX_SIGNATURE_IN_OPENING:
        errors.append(
            f"formula-opening-stamp: {len(sig_open)} signature markers in lead "
            f"(max {MAX_SIGNATURE_IN_OPENING}): {', '.join(sig_open)}"
        )
    if len(sig_all) > MAX_SIGNATURE_IN_ARTICLE:
        errors.append(
            f"formula-marker-spam: {len(sig_all)} signature markers in article "
            f"(max {MAX_SIGNATURE_IN_ARTICLE}): {', '.join(sig_all)}"
        )
    if HEAVY_OPENER_RE.search(opening) and len(sig_open) >= 2:
        soft.append(
            "heavy formula opener + extra stamps in lead — vary openings; "
            "do not start every piece the same way"
        )

    label_dumps = _label_dump_count(article_html)
    metrics["label_dumps"] = label_dumps
    if label_dumps > MAX_LABEL_DUMPS:
        errors.append(
            f"writer-label-dumps {label_dumps} > {MAX_LABEL_DUMPS} "
            "(<b>Label:</b> / 'Ярлык:' vendor dumps not retold in everyday prose)"
        )

    # Soft body plain-language density (looser than opening_meta).
    meta: dict[str, Any] = {}
    meta_path = article_dir / "article.meta.json"
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            meta = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            meta = {}
    title_brief: dict[str, Any] = {}
    tb_path = article_dir / "title-brief.json"
    if tb_path.is_file():
        try:
            loaded_tb = json.loads(tb_path.read_text(encoding="utf-8"))
            title_brief = loaded_tb if isinstance(loaded_tb, dict) else {}
        except json.JSONDecodeError:
            title_brief = {}
    allow = allowlist_from_title(
        str(meta.get("h1") or meta.get("title") or ""),
        str(title_brief.get("h1") or ""),
        str(title_brief.get("title") or ""),
        str(title_brief.get("subject") or ""),
    )
    body_plain = re.sub(
        r"\s+", " ", TAG_RE.sub(" ", _body_html(article_html))
    ).strip()
    body_pl_errors = plain_language_errors(
        body_plain,
        allow=allow,
        max_latin=BODY_MAX_LATIN,
        max_jargon=BODY_MAX_JARGON,
        label="article.html-body",
    )
    # Soft: record always; hard-fail only when body is a jargon dump AND
    # rewrite depth already looks shallow (avoid punishing dense product names
    # in a truly rewritten piece).
    if body_pl_errors:
        soft.extend(body_pl_errors)
        if verbatim_ratio > 0.20 or body_verbatim_ratio > 0.25:
            errors.extend(body_pl_errors)

    status = "PASS" if not errors else "BLOCK"
    return {
        "gate": "sol-rewrite-depth",
        "status": status,
        "errors": errors,
        "soft_warnings": soft,
        "metrics": metrics,
        "article_dir": str(article_dir),
        "thresholds": {
            "max_verbatim_ratio": MAX_VERBATIM_RATIO,
            "max_body_verbatim_ratio": MAX_BODY_VERBATIM_RATIO,
            "max_paragraph_set_jaccard": MAX_PARA_SET_JACCARD,
            "max_token_jaccard_hard": MAX_TOKEN_JACCARD_HARD,
            "max_signature_in_opening": MAX_SIGNATURE_IN_OPENING,
            "max_signature_in_article": MAX_SIGNATURE_IN_ARTICLE,
            "max_label_dumps": MAX_LABEL_DUMPS,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--article-dir", type=Path, required=True)
    ap.add_argument("-o", "--output", type=str, default="sol-rewrite-depth-gate.json")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    if not article_dir.is_dir():
        print(f"BLOCKER: article-dir not found: {article_dir}", file=sys.stderr)
        return 2
    report = check_article(article_dir)
    out_path = article_dir / Path(args.output).name
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
