"""Download images from URLs.

Usage:
    python tools/title_optimize/download.py
    python tools/title_optimize/download.py --url https://example.com/img.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent
PHOTO_DIR = BASE / "temp_photo"


def download(url: str, out_dir: Path) -> Path:
    """Download an image from url, save to out_dir. Returns saved path."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Derive filename from URL
    parsed = urlparse(url)
    name = Path(parsed.path).name or "image.jpg"
    out_path = out_dir / name

    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        print(f"Warning: Content-Type is '{content_type}', saving anyway...")

    out_path.write_bytes(resp.content)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download images from URLs")
    parser.add_argument("--url", default="", help="Image URL to download")
    args = parser.parse_args()

    test_urls = []
    if args.url:
        test_urls.append(args.url)

    if not test_urls:
        # Default test URL
        test_urls.append(
            "https://4u8setxxirg508ln.imgsapp.com/afsd/8349/9370411279502525647017.jpg"
        )

    for url in test_urls:
        print(f"Downloading: {url}")
        try:
            path = download(url, PHOTO_DIR)
            size_kb = path.stat().st_size / 1024
            print(f"  → {path} ({size_kb:.1f} KB)")
        except requests.RequestException as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
