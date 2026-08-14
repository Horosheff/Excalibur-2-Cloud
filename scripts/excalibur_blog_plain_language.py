#!/usr/bin/env python3
"""Plain-language / anti-jargon helpers for Excalibur BLOG gates.

Audience: beginners. Human Russian for a novice — not term dumps.
"""
from __future__ import annotations

import re
from typing import Iterable

# Technical English that must not pile up in openings / Dzen card teasers.
JARGON_RE = re.compile(
    r"\b("
    r"CVE-\d+|CVE|PoC|POC|RCE|OSS|SaaS|PaaS|IaaS|"
    r"endpoint|endpoints|runtime|workflow|workflows|"
    r"bearer|disclosure|exploit|payload|toolchain|"
    r"prompt\s*engineering|LLMOps|MLOps|DevOps|"
    r"auto[_-]?login|validate/code|exec\(\)|PR\b|KPI"
    r")\b",
    re.IGNORECASE,
)

LATIN_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.#/_-]{1,}\b")

# Always-allowed short brand tokens when present in title/subject.
DEFAULT_ALLOW = {
    "ai",
    "api",
    "gpt",
    "ui",
    "ux",
    "max",
    "vk",
    "ios",
    "android",
    "pdf",
    "url",
    "html",
    "css",
    "json",
    "rss",
}


def _plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def allowlist_from_title(*blobs: str) -> set[str]:
    allow = set(DEFAULT_ALLOW)
    for blob in blobs:
        for tok in LATIN_TOKEN_RE.findall(blob or ""):
            allow.add(tok.casefold())
    return allow


def latin_tokens(text: str, *, allow: Iterable[str] | None = None) -> list[str]:
    allow_set = {a.casefold() for a in (allow or ())}
    out: list[str] = []
    for tok in LATIN_TOKEN_RE.findall(_plain(text)):
        low = tok.casefold()
        if low in allow_set:
            continue
        out.append(tok)
    return out


def jargon_hits(text: str) -> list[str]:
    return [m.group(0) for m in JARGON_RE.finditer(_plain(text))]


def plain_language_errors(
    text: str,
    *,
    allow: Iterable[str] | None = None,
    max_latin: int = 2,
    max_jargon: int = 0,
    label: str = "text",
) -> list[str]:
    """Return human-readable blockers for jargon / latin dumps."""
    errors: list[str] = []
    jhits = jargon_hits(text)
    if len(jhits) > max_jargon:
        sample = ", ".join(jhits[:6])
        errors.append(f"{label}: jargon-dump ({len(jhits)}): {sample}")
    extras = latin_tokens(text, allow=allow)
    if len(extras) > max_latin:
        sample = ", ".join(extras[:8])
        errors.append(f"{label}: too-many-latin ({len(extras)}>{max_latin}): {sample}")
    return errors
