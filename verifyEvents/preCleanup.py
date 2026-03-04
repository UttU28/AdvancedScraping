"""
Pre-cleanup script for event URLs.

Reads the source CSV, normalizes the event URLs (e.g. trims trailing `/`),
removes duplicate events based on the normalized URL while keeping the first
occurrence, and writes the cleaned data back to the same CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timedelta


crawlerDir = Path(__file__).resolve().parent
txtDir = crawlerDir / "txtDir"

# Main source file used by server.py / aScrapeUrls.py
inputCsv = crawlerDir / "source.csv"


def normalizeUrl(url: str) -> str:
    """Return a normalized URL string for duplicate detection."""
    if not url:
        return ""
    url = url.strip()
    if url.endswith("/"):
        url = url[:-1]
    return url


def loadRows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load CSV rows and field names from the given path."""
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        # Capture field names from the reader to preserve column order
        fieldNames = [field for field in (reader.fieldnames or []) if field]

    if not rows:
        print(f"[preCleanup] No rows found in {path.name}. Nothing to clean.")
        return [], fieldNames

    if "Event URL" not in fieldNames:
        raise KeyError(
            f"'Event URL' column not found in {path.name}. "
            "Make sure the header row contains an 'Event URL' column."
        )

    return rows, fieldNames


def dedupeRows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """De-duplicate rows by normalized 'Event URL', keeping the first occurrence."""
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []

    for row in rows:
        rawUrl = (row.get("Event URL") or "").strip()
        normalizedUrl = normalizeUrl(rawUrl)
        row["Event URL"] = normalizedUrl

        if not normalizedUrl:
            deduped.append(row)
            continue

        if normalizedUrl in seen:
            continue

        seen.add(normalizedUrl)
        deduped.append(row)

    print(f"[preCleanup] URL de-duplication: {len(rows)} -> {len(deduped)} rows.")
    return deduped


def writeRows(path: Path, rows: list[dict[str, str]], fieldNames: list[str]) -> None:
    """Write cleaned rows back to CSV, preserving field order."""
    if not rows:
        print("[preCleanup] No rows to write; skipping CSV update.")
        return

    # Ensure field names do not contain None and preserve original order
    fieldNames = [field for field in fieldNames if field]

    # Prepare rows for writing: drop any keys not in fieldNames (e.g. None from extra columns)
    cleanedForWrite: list[dict[str, str]] = []
    allowedFields = set(fieldNames)
    for row in rows:
        cleanedRow = {key: value for key, value in row.items() if key in allowedFields}
        cleanedForWrite.append(cleanedRow)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldNames)
        writer.writeheader()
        writer.writerows(cleanedForWrite)

    print(f"[preCleanup] Wrote cleaned CSV to {path.name}.")


def printTxtdirAgeSummary(hours: float = 1.0, askDelete: bool = True) -> None:
    """Print count of txtDir files newer/older than the given hours and optionally delete older ones."""
    if not txtDir.exists():
        print(f"[preCleanup] {txtDir} does not exist.")
        return

    cutoff = datetime.now() - timedelta(hours=hours)

    newer = 0
    older = 0
    total = 0
    olderFiles: list[Path] = []

    for txtFile in txtDir.glob("*.txt"):
        total += 1
        modifiedTime = datetime.fromtimestamp(txtFile.stat().st_mtime)
        if modifiedTime >= cutoff:
            newer += 1
        else:
            older += 1
            olderFiles.append(txtFile)

    print(f"[preCleanup] txtDir summary for *.txt files:")
    print(f"  - Total files: {total}")
    print(f"  - Newer than {hours} hour(s): {newer}")
    print(f"  - Older than {hours} hour(s): {older}")

    if askDelete and olderFiles:
        choice = input(
            f"[preCleanup] Delete the {older} file(s) older than {hours} hour(s)? [y/N]: "
        ).strip().lower()
        if choice == "y":
            for txtFile in olderFiles:
                try:
                    txtFile.unlink()
                    print(f"  Deleted: {txtFile.name}")
                except Exception as exc:
                    print(f"  Could not delete {txtFile.name}: {exc}")


def main() -> None:
    """Run CSV pre-cleanup and txtDir age summary."""
    print(f"[preCleanup] Loading rows from {inputCsv.name}...")
    rows, fieldNames = loadRows(inputCsv)
    if not rows:
        return

    print("[preCleanup] De-duplicating by normalized 'Event URL'...")
    cleanedRows = dedupeRows(rows)

    print("[preCleanup] Writing cleaned data back to CSV...")
    writeRows(inputCsv, cleanedRows, fieldNames)
    print("[preCleanup] CSV normalization and de-duplication complete.")

    # Also print txtDir age summary (1 hour threshold) and optionally delete older files
    printTxtdirAgeSummary(1.0, askDelete=True)


if __name__ == "__main__":
    main()

