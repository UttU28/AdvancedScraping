"""CLI wrapper for CSV splitting (same logic as the Split tab in dashboard.py)."""

import os
import sys

from app import split_csv_chunks


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python split.py <input.csv>")
        sys.exit(1)
    inputPath = os.path.normpath(sys.argv[1])
    if not os.path.isfile(inputPath):
        print(f"Not found: {inputPath}")
        sys.exit(1)
    directory = os.path.dirname(os.path.abspath(inputPath))
    stem = os.path.splitext(os.path.basename(inputPath))[0]
    pattern = os.path.join(directory, f"{stem}_{{}}.csv")
    created = split_csv_chunks(inputPath, pattern, rows_per_file=40)
    for p in created:
        print(f"Created: {p}")


if __name__ == "__main__":
    main()
