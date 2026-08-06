"""Third-party exercise APIs are intentionally disabled for now.

Catalogue data comes from the frozen MIT exercises-dataset JSON
(see app.scripts.seed_internal_exercises). Gym Visual media licensing
can be wired later via media_id.
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import third-party exercise data (not enabled yet)"
    )
    parser.add_argument("--source", default="wger", help="Data source identifier")
    args = parser.parse_args()
    print(
        f"Import from '{args.source}' is disabled.\n"
        "Use: python -m app.scripts.seed_internal_exercises\n"
        "Gym Visual / other licensed media can be added later via media_id.",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
