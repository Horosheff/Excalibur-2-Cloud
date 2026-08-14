#!/usr/bin/env python3
"""Optional tenant brand badge on cover + inline panels.

Enabled only when tenant/setup provides handle + avatar. Missing config is a
skip (PASS), not a blocker — Excalibur-2-Cloud ships without a personal brand.

Config (first found):
  memory/cover/brand-telegram.json
  shared/tenant-config.json → cover_watermark
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_cfg(root: Path) -> dict | None:
    """Return watermark cfg or None when the tenant has not enabled it."""
    brand = _load_json(root / "memory/cover/brand-telegram.json")
    tenant = _load_json(root / "shared/tenant-config.json")
    wm = tenant.get("cover_watermark") if isinstance(tenant.get("cover_watermark"), dict) else {}

    enabled = brand.get("enabled")
    if enabled is None:
        enabled = wm.get("enabled")
    if enabled is False:
        return None

    cfg = dict(wm)
    cfg.update(brand)
    handle = str(
        (cfg.get("badge") or {}).get("text")
        or cfg.get("handle")
        or cfg.get("text")
        or ""
    ).strip()
    avatar_rel = str(
        (cfg.get("avatar") or {}).get("local_asset")
        or cfg.get("avatar_path")
        or ""
    ).strip()
    if not handle or not avatar_rel:
        return None
    if not (root / avatar_rel).is_file():
        return None
    cfg["handle"] = handle
    cfg.setdefault("badge", {})
    cfg["badge"]["text"] = handle
    cfg.setdefault("avatar", {})
    cfg["avatar"]["local_asset"] = avatar_rel
    return cfg


def require_pillow() -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401

        return True
    except ImportError:
        print("❌ BRAND WATERMARK BLOCKER: install Pillow", file=sys.stderr)
        return False


def load_font(size: int):
    from PIL import ImageFont

    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ):
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_badge(root: Path, cfg: dict):
    from PIL import Image, ImageDraw

    badge_cfg = cfg.get("badge") or {}
    avatar_rel = (cfg.get("avatar") or {}).get("local_asset")
    avatar_path = root / str(avatar_rel)
    if not avatar_path.is_file():
        raise FileNotFoundError(f"missing avatar: {avatar_path}")

    avatar_px = int(badge_cfg.get("avatar_px_at_badge") or 44)
    font_px = int(badge_cfg.get("font_px_at_badge") or 18)
    ring = 3
    pad = 6
    handle = str(badge_cfg.get("text") or cfg.get("handle") or "")
    accent = badge_cfg.get("accent_rgba") or [255, 20, 147, 255]
    pink = tuple(int(x) for x in accent)
    white = (255, 255, 255, 255)

    av = Image.open(avatar_path).convert("RGBA").resize((avatar_px, avatar_px), Image.Resampling.LANCZOS)
    mask = Image.new("L", (avatar_px, avatar_px), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_px - 1, avatar_px - 1), fill=255)
    circ = Image.new("RGBA", (avatar_px, avatar_px), (0, 0, 0, 0))
    circ.paste(av, (0, 0), mask)

    outer = avatar_px + ring * 2
    ring_im = Image.new("RGBA", (outer, outer), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring_im)
    rd.ellipse((0, 0, outer - 1, outer - 1), outline=pink, width=ring)
    ring_im.paste(circ, (ring, ring), circ)

    font = load_font(font_px)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = tmp.textbbox((0, 0), handle, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gap = 8
    w = ring_im.width + gap + tw + pad * 2
    h = max(ring_im.height, th) + pad * 2
    badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    pill_h = max(ring_im.height + 4, th + 10)
    bd.rounded_rectangle(
        (0, (h - pill_h) // 2, w - 1, (h + pill_h) // 2 - 1),
        radius=pill_h // 2,
        fill=(11, 11, 12, 185),
    )
    badge.paste(ring_im, (pad, (h - ring_im.height) // 2), ring_im)
    bd.text((pad + ring_im.width + gap, (h - th) // 2 - 1), handle, font=font, fill=white)
    return badge


def apply_to_panel(path: Path, badge, width_ratio: float, margin: int) -> None:
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    target_w = max(90, int(im.width * width_ratio))
    ratio = target_w / badge.width
    b = badge.resize((target_w, max(1, int(badge.height * ratio))), Image.Resampling.LANCZOS)
    x = im.width - b.width - margin
    y = margin
    out = im.copy()
    out.alpha_composite(b, (max(0, x), max(0, y)))
    out.convert("RGB").save(path, format="PNG", optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", required=True)
    args = ap.parse_args()
    if not require_pillow():
        return 2

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir
    cover_dir = article_dir / "cover"

    cfg = load_cfg(root)
    if cfg is None:
        print("OK watermark skipped (tenant cover_watermark not configured)")
        return 0

    try:
        badge = make_badge(root, cfg)
    except Exception as exc:
        print(f"❌ BRAND WATERMARK BLOCKER: {exc}", file=sys.stderr)
        return 1

    badge_cfg = cfg.get("badge") or {}
    width_ratio = float(badge_cfg.get("width_ratio_of_panel") or 0.14)
    margin_base = int(badge_cfg.get("margin_px_at_1920") or 28)
    files = ["cover.png", "inline-01.png", "inline-02.png", "inline-03.png"]
    from PIL import Image

    for name in files:
        path = cover_dir / name
        if not path.is_file():
            print(f"❌ BRAND WATERMARK BLOCKER: missing {path}", file=sys.stderr)
            return 1
        with Image.open(path) as im:
            margin = max(12, int(margin_base * (im.width / 1920)))
        apply_to_panel(path, badge, width_ratio, margin)
        print(f"OK watermark={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
