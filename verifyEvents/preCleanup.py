"""
Pre-cleanup script for event URLs.

Reads the source CSV, normalizes the event URLs (e.g. trims trailing `/`),
removes duplicate events based on the normalized URL while keeping the first
occurrence, and writes the cleaned data back to the same CSV (with a backup).
"""

from __future__ import annotations

import csv
from pathlib import Path


CRAWLER_DIR = Path(__file__).resolve().parent

# Main source file used by server.py / aScrapeUrls.py
INPUT_CSV = CRAWLER_DIR / "source.csv"


def normalize_url(url: str) -> str:
    """
    Normalize URLs for duplicate detection.

    - Strip whitespace
    - Remove a single trailing slash
    """
    if not url:
        return ""
    url = url.strip()
    if url.endswith("/"):
        url = url[:-1]
    return url


def load_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        # Capture fieldnames from the reader to preserve column order
        fieldnames = [f for f in (reader.fieldnames or []) if f]
    if not rows:
        print(f"No rows found in {path.name}. Nothing to clean.")
        return [], fieldnames
    if "Event URL" not in fieldnames:
        raise KeyError(
            f"'Event URL' column not found in {path.name}. "
            "Make sure the header row contains an 'Event URL' column."
        )
    return rows, fieldnames


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []

    for row in rows:
        raw_url = (row.get("Event URL") or "").strip()
        norm = normalize_url(raw_url)
        # Also write the normalized URL back into the row so later scripts see the cleaned version
        row["Event URL"] = norm

        if not norm:
            # Keep rows with empty URLs as-is
            deduped.append(row)
            continue

        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(row)

    print(f"Original rows: {len(rows)}; after de-dup: {len(deduped)}")
    return deduped


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    if not rows:
        print("No rows to write; skipping file update.")
        return

    # Ensure fieldnames do not contain None and preserve original order
    fieldnames = [f for f in fieldnames if f]

    # Prepare rows for writing: drop any keys not in fieldnames (e.g. None from extra columns)
    cleaned_for_write: list[dict[str, str]] = []
    allowed = set(fieldnames)
    for row in rows:
        cleaned_row = {k: v for k, v in row.items() if k in allowed}
        cleaned_for_write.append(cleaned_row)

    # Directly overwrite the original CSV with the cleaned data (no backups)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_for_write)
    print(f"Cleaned CSV written to {path.name}")


def main() -> None:
    print(f"Loading rows from {INPUT_CSV.name}...")
    rows, fieldnames = load_rows(INPUT_CSV)
    if not rows:
        return

    print("De-duplicating by normalized 'Event URL'...")
    cleaned_rows = dedupe_rows(rows)

    print("Writing cleaned data back to CSV...")
    write_rows(INPUT_CSV, cleaned_rows, fieldnames)
    print("Pre-cleanup complete.")


if __name__ == "__main__":
    main()

