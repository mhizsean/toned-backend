"""Download the pinned exercises-dataset JSON into data/.

Pinned commit SHA lives in data/exercises_dataset.sha.
See data/exercises_dataset.SOURCE.md for license notes.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SHA_PATH = DATA_DIR / "exercises_dataset.sha"
OUT_PATH = DATA_DIR / "exercises_dataset.json"
RAW_URL = (
    "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/"
    "{sha}/data/exercises.json"
)


def pinned_sha() -> str:
    if not SHA_PATH.exists():
        raise FileNotFoundError(f"Missing pin file: {SHA_PATH}")
    sha = SHA_PATH.read_text(encoding="utf-8").strip()
    if not sha:
        raise ValueError(f"Empty pin file: {SHA_PATH}")
    return sha


def download(*, force: bool = False) -> Path:
    if OUT_PATH.exists() and not force:
        print(f"Already present: {OUT_PATH}")
        return OUT_PATH

    sha = pinned_sha()
    url = RAW_URL.format(sha=sha)
    print(f"Downloading exercises dataset @ {sha[:12]}…")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, OUT_PATH)
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUT_PATH} ({size_mb:.1f} MiB)")
    return OUT_PATH


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the file already exists",
    )
    args = parser.parse_args()
    download(force=args.force)
