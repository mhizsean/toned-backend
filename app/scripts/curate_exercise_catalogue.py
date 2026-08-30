"""Regenerate the public exercise allowlist from the full dataset.

  python -m app.scripts.curate_exercise_catalogue
"""

from __future__ import annotations

import json

from app.catalogue.curation import (
    ALLOWLIST_PATH,
    DATASET_PATH,
    curate,
    write_allowlist,
)


def main() -> None:
    records = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    result = curate(records)
    write_allowlist(result, source_count=len(records))
    print(f"Source: {len(records)}")
    print(f"Kept: {len(result.kept)}")
    print(f"Removed: {len(result.removed)}")
    print(f"Families: {result.groups}")
    print(f"Wrote {ALLOWLIST_PATH}")


if __name__ == "__main__":
    main()
