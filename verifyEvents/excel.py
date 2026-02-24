"""
Generate an Excel file from `extraction_results_clean.json`:
- Sort events by start_date (mm/dd/yyyy), unknown/TBD dates at the bottom
- Filter out past events (start_date < today)
- Excel columns: Event Title, Start Date, End Date, URL, Location, Attending, Notes

Usage (from verifyEvents folder):
  python excel.py        # generate Excel, then delete the cleaned JSON helpers
  python excel.py 1      # generate Excel and keep the cleaned JSON helpers
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from colorama import Fore, Style, init
from openpyxl.worksheet.datavalidation import DataValidation

init(autoreset=True)

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

    rowsForExcel = []
    for record in upcomingEvents:
        rowsForExcel.append(
            {
                "Event Title": record.get("event_name") or "",
                "Start Date": record.get("start_date") or "",
                "End Date": record.get("end_date") or "",
                "URL": record.get("url") or "",
                "Location": record.get("location") or "",
                "Attending": "",
                "Notes": record.get("notes") or "",
            }
        )

    df = pd.DataFrame(
        rowsForExcel,
        columns=["Event Title", "Start Date", "End Date", "URL", "Location", "Attending", "Notes"],
    )

    # Write with openpyxl so we can adjust column widths
    with pd.ExcelWriter(excelOutPath, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Events")
        ws = writer.sheets["Events"]
        # Rough, readable widths per column
        widths = {
            "A": 40,  # Event Title
            "B": 12,  # Start Date
            "C": 12,  # End Date
            "D": 45,  # URL
            "E": 25,  # Location
            "F": 15,  # Attending
            "G": 60,  # Notes
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

        # Dropdown with three options for Attending; cell starts blank, user chooses
        dv = DataValidation(type="list", formula1='"YES/NO,YES,NO"', allow_blank=True)
        ws.add_data_validation(dv)
        # Apply to Attending column (F), all data rows
        max_row = len(df) + 1  # +1 for header
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

