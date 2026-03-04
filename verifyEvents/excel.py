"""
Generate an Excel file from `extraction_results_clean.json`:
- Sort events by start_date (mm/dd/yyyy), unknown/TBD dates at the bottom
- Filter out past events (start_date < today)
- Excel columns: Event Title, Start Date, End Date, URL, Location, Attending
- All text written as plain text to avoid encoding errors

Usage (from verifyEvents folder):
  python excel.py        # generate Excel, then delete the cleaned JSON helpers
  python excel.py 1      # generate Excel and keep the cleaned JSON helpers
"""
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
from colorama import Fore, Style, init
from openpyxl.worksheet.datavalidation import DataValidation

init(autoreset=True)


def toPlainText(value) -> str:
    """Convert to plain text string, stripping/replacing chars that can break Excel."""
    if value is None:
        return ""
    s = str(value).strip()
    # Replace symbols that often cause Excel/xlsx issues
    s = s.replace("\u00ae", "(R)")   # ®
    s = s.replace("\u2122", "(TM)")  # ™
    s = s.replace("\u2019", "'")     # smart apostrophe '
    s = s.replace("\u2018", "'")     # smart apostrophe '
    s = s.replace("\u201c", '"')     # smart quote "
    s = s.replace("\u201d", '"')     # smart quote "
    s = s.replace("\u2013", "-")     # en dash
    s = s.replace("\u2014", "-")     # em dash
    # Remove null bytes and control chars
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    # Normalize unicode
    s = unicodedata.normalize("NFKC", s)
    # Strip control chars (category C* except newline, tab, return)
    s = "".join(c for c in s if unicodedata.category(c)[0] != "C" or c in "\n\r\t")
    return s.strip()

verifyEventsDir = Path(__file__).resolve().parent
resultsCleanPath = verifyEventsDir / "extraction_results_clean.json"
excelOutPath = verifyEventsDir / "extraction_results_clean.xlsx"
resultsSinglePath = verifyEventsDir / "extraction_results_single.json"
resultsMultiPath = verifyEventsDir / "extraction_results_multi.json"
resultsRemovedPath = verifyEventsDir / "extraction_results_removed.json"


def parseDate(raw: str):
    """Parse mm/dd/yyyy to datetime.date, or return None if not parseable or TBD."""
    value = (raw or "").strip()
    if not value or value.upper() == "TBD":
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except Exception:
        return None


def sortKey(record: dict):
    dateValue = parseDate(record.get("start_date"))
    if dateValue is None:
        # Put unknown/TBD dates at the bottom; keep relative order via id
        return (1, record.get("id") or 0)
    return (0, dateValue)


def main():
    keepJson = len(sys.argv) > 1 and sys.argv[1].strip() == "1"

    if not resultsCleanPath.exists():
        print(f"{Fore.RED}Excel: {resultsCleanPath.name} not found. Run cleanup first.{Style.RESET_ALL}")
        return

    with resultsCleanPath.open(encoding="utf-8") as handle:
        cleanEvents = json.load(handle)

    if not isinstance(cleanEvents, list):
        print(f"{Fore.RED}Excel: {resultsCleanPath.name} is not a list.{Style.RESET_ALL}")
        return

    # Sort by start_date and drop events whose start_date is before today
    sortedRows = sorted(cleanEvents, key=sortKey)
    today = datetime.today().date()
    upcomingEvents: list[dict] = []
    for record in sortedRows:
        dateValue = parseDate(record.get("start_date"))
        if dateValue is None or dateValue >= today:
            upcomingEvents.append(record)

    # De-duplicate by exact same (start_date, end_date): keep only one event for each exact date pair
    seenDatePairs: set[tuple[str, str]] = set()
    dedupedEvents: list[dict] = []
    for record in upcomingEvents:
        start_raw = (record.get("start_date") or "").strip()
        end_raw = (record.get("end_date") or "").strip()
        key = (start_raw, end_raw)
        if key in seenDatePairs:
            continue
        seenDatePairs.add(key)
        dedupedEvents.append(record)

    rowsForExcel = []
    for record in dedupedEvents:
        rowsForExcel.append(
            {
                "Event Title": toPlainText(record.get("event_name")),
                "Start Date": toPlainText(record.get("start_date")),
                "End Date": toPlainText(record.get("end_date")),
                "URL": toPlainText(record.get("url")),
                "Location": toPlainText(record.get("location")),
                "Attending": "",
            }
        )

    df = pd.DataFrame(
        rowsForExcel,
        columns=["Event Title", "Start Date", "End Date", "URL", "Location", "Attending"],
    )

    # Write with openpyxl so we can adjust column widths and set plain text format
    with pd.ExcelWriter(excelOutPath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Events")
        ws = writer.sheets["Events"]
        # Set all cells to plain text format to avoid encoding errors
        max_row = len(df) + 1
        for col in "ABCDEF":
            for row in range(1, max_row + 1):
                cell = ws[f"{col}{row}"]
                cell.number_format = "@"
        # Rough, readable widths per column
        widths = {
            "A": 40,  # Event Title
            "B": 12,  # Start Date
            "C": 12,  # End Date
            "D": 45,  # URL
            "E": 25,  # Location
            "F": 15,  # Attending
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

        # Dropdown with three options for Attending; cell starts blank, user chooses
        dv = DataValidation(type="list", formula1='"YES/NO,YES,NO"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"F2:F{max_row}")

    print(f"{Fore.GREEN}Excel: wrote {len(df)} upcoming rows to {excelOutPath.name} with adjusted column widths{Style.RESET_ALL}")

    # Optional cleanup: remove auxiliary JSONs (single/multi/removed)
    for auxPath in (resultsSinglePath, resultsMultiPath, resultsRemovedPath):
        if auxPath.exists():
            auxPath.unlink()
            print(f"{Fore.YELLOW}Excel: removed {auxPath.name}{Style.RESET_ALL}")

    # By default also drop the cleaned JSON (we always keep the Excel); use arg 1 to keep JSON
    if not keepJson and resultsCleanPath.exists():
        resultsCleanPath.unlink()
        print(f"{Fore.YELLOW}Excel: removed {resultsCleanPath.name} (run with '1' to keep JSON){Style.RESET_ALL}")


if __name__ == "__main__":
    main()

