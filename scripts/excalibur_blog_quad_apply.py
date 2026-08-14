#!/usr/bin/env python3
"""Download ONE quad canvas URL, save canvas-quad.png, run split + optional inject.

``--inject-html`` delegates to ``excalibur_blog_cover_quad_split.py``, which
re-validates each existing ``data-slot`` figure against manifest ``h2_anchor``
(and src/alt). Wrong-H2 / stale figures are moved/rewritten — never silent skip.

After a successful split, optionally applies a tenant brand watermark
(``excalibur_blog_cover_brand_watermark.py``). Missing tenant config is a skip.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_download import download_url_bytes  # noqa: E402


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article-dir", required=True)
    ap.add_argument("--url", default="", help="MCP result URL (or read cover/quad-mcp-result.json)")
    ap.add_argument("--inject-html", action="store_true")
    ap.add_argument("--output-size", default="1200x675")
    ap.add_argument("--skip-brand-watermark", action="store_true")
    args = ap.parse_args()

    root = project_root()
    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir
    cover_dir = article_dir / "cover"
    cover_dir.mkdir(parents=True, exist_ok=True)

    url = args.url.strip()
    if not url:
        result_path = cover_dir / "quad-mcp-result.json"
        if result_path.is_file():
            url = (json.loads(result_path.read_text(encoding="utf-8")).get("url") or "").strip()
    if not url:
        print("❌ QUAD APPLY BLOCKER: pass --url or cover/quad-mcp-result.json", file=sys.stderr)
        return 1

    canvas_path = cover_dir / "canvas-quad.png"
    data, _evidence = download_url_bytes(url)
    canvas_path.write_bytes(data)
    print(f"OK canvas={canvas_path}")

    result_json = cover_dir / "quad-mcp-result.json"
    result_json.write_text(json.dumps({"url": url}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(root / "scripts" / "excalibur_blog_cover_quad_split.py"),
        "--article-dir",
        str(article_dir),
        "--manifest",
        "cover/quad-manifest.json",
        "--output-size",
        args.output_size,
    ]
    if args.inject_html:
        cmd.append("--inject-html")
    proc = subprocess.run(cmd, cwd=str(root))
    if proc.returncode != 0:
        return proc.returncode

    if not args.skip_brand_watermark:
        wm = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "excalibur_blog_cover_brand_watermark.py"),
                "--article-dir",
                str(article_dir),
            ],
            cwd=str(root),
        )
        if wm.returncode != 0:
            return wm.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
