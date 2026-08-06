"""Placeholder for importing/normalizing third-party exercise APIs."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Import third-party exercise data")
    parser.add_argument("--source", default="wger", help="Data source identifier")
    args = parser.parse_args()
    raise NotImplementedError(f"Import from {args.source} is not implemented yet")


if __name__ == "__main__":
    main()
