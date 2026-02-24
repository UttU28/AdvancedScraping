"""
Fix and clean extraction results JSON:
- Read from extraction_results.json or extraction_results copy.json
- Fill missing URLs by backtracking from source_txt into source.csv
- Keep only site_type == "event_page"
- Remove duplicates: same source_txt + start_date + end_date (keep first)
- Add numeric id to each row
- Split output:
  - extraction_results_single.json: URLs with exactly one event (count at top)
  - extraction_results_multi.json: URLs with multiple events; one entry per URL with all its events (count at top)

Usage (from verifyEvents folder):
  python cleanup.py
  python cleanup.py "extraction_results copy.json"
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from colorama import Fore, Style, init

init(autoreset=True)

verifyEventsDir = Path(__file__).resolve().parent
csvPath = verifyEventsDir / "source.csv"

# Treat the original as read-only; derive cleaned data into new files
inputCopyPath = verifyEventsDir / "extraction_results.json"
outputCleanPath = verifyEventsDir / "extraction_results_clean.json"
outputSinglePath = verifyEventsDir / "extraction_results_single.json"
outputMultiPath = verifyEventsDir / "extraction_results_multi.json"
removedPath = verifyEventsDir / "extraction_results_removed.json"


def loadEventsCsv() -> list[dict]:
    rows = []
    with csvPath.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    return rows


def normalizeTitle(text: str) -> str:
    text = (text or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def hasCjk(text: str) -> bool:
    """Return True if text contains any CJK (e.g. Chinese) characters."""
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def inferUrlFromSource(sourceTxt: str, csvRows: list[dict]) -> str:
    if not sourceTxt:
        return ""
    base = sourceTxt.replace("_homepage.txt", "").replace(".txt", "")
    base = base.replace("_", " ").strip()
    normBase = normalizeTitle(base)
    if not normBase:
        return ""
    for row in csvRows:
        title = (row.get("Event Title") or "").strip()
        url = (row.get("Event URL") or "").strip()
        if not url or not title:
            continue
        normTitle = normalizeTitle(title)
        if not normTitle:
            continue
        if normBase == normTitle or normBase in normTitle or normTitle in normBase:
            return url
    return ""


def main():
    # Always use the copy as the read-only source; never modify the original
    if len(sys.argv) > 1 and sys.argv[1].strip():
        inputPath = verifyEventsDir / sys.argv[1].strip()
    else:
        inputPath = inputCopyPath

    if not inputPath.exists():
        print(f"{Fore.RED}Cleanup: input not found -> {inputPath}{Style.RESET_ALL}")
        return
    if not csvPath.exists():
        print(f"{Fore.RED}Cleanup: missing source.csv at {csvPath}{Style.RESET_ALL}")
        return

    try:
        with inputPath.open(encoding="utf-8") as handle:
            rawResults = json.load(handle)
    except json.JSONDecodeError as exc:
        print(f"{Fore.RED}Cleanup: could not parse {inputPath.name}: {exc}{Style.RESET_ALL}")
        return

    if not isinstance(rawResults, list):
        print(f"{Fore.RED}Cleanup: input JSON is not a list; aborting.{Style.RESET_ALL}")
        return

    csvRows = loadEventsCsv()
    cleanedEvents: list[dict] = []
    removedEvents: list[dict] = []
    seenDedupKeys: set[tuple[str, str, str]] = set()  # (source_txt, start_date, end_date)

    for record in rawResults:
        if not isinstance(record, dict):
            continue

        siteType = (record.get("site_type") or "").strip() or "other"
        if siteType != "event_page":
            removedEvents.append({**record, "removed_reason": "non_event_site_type"})
            continue

        eventName = (record.get("event_name") or "").strip()
        if hasCjk(eventName):
            removedEvents.append({**record, "removed_reason": "non_latin_title"})
            continue

        sourceTxt = record.get("source_txt") or ""
        startDate = (record.get("start_date") or "").strip()
        endDate = (record.get("end_date") or "").strip()
        dedupKey = (sourceTxt, startDate, endDate)
        if dedupKey in seenDedupKeys:
            removedEvents.append({**record, "removed_reason": "duplicate_source_start_end"})
            continue
        seenDedupKeys.add(dedupKey)

        url = (record.get("url") or "").strip()
        if not url:
            url = inferUrlFromSource(sourceTxt, csvRows)
            record["url"] = url

        cleanedEvents.append(record)

    def sortKey(rec: dict):
        return (
            (rec.get("start_date") or "9999/99/99"),
            (rec.get("event_name") or "").lower(),
            (rec.get("url") or "").lower(),
        )

    cleanedEvents.sort(key=sortKey)

    for idx, record in enumerate(cleanedEvents, 1):
        record["id"] = idx

    groupedByUrl: dict[str, list[dict]] = defaultdict(list)
    for record in cleanedEvents:
        url = (record.get("url") or "").strip()
        groupedByUrl[url].append(record)

    singleEvents: list[dict] = []
    multiEntries: list[dict] = []
    for url, events in groupedByUrl.items():
        if len(events) == 1:
            singleEvents.append(events[0])
        else:
            multiEntries.append(
                {
                    "url": url,
                    "source_txt": events[0].get("source_txt") if events else "",
                    "event_count": len(events),
                    "events": events,
                }
            )

    with outputCleanPath.open("w", encoding="utf-8") as handle:
        json.dump(cleanedEvents, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Cleanup: clean events {len(cleanedEvents)} -> {outputCleanPath.name}{Style.RESET_ALL}")

    singlePayload = {"count": len(singleEvents), "events": singleEvents}
    with outputSinglePath.open("w", encoding="utf-8") as handle:
        json.dump(singlePayload, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Cleanup: single-event URLs {len(singleEvents)} -> {outputSinglePath.name}{Style.RESET_ALL}")

    multiPayload = {"count": len(multiEntries), "entries": multiEntries}
    with outputMultiPath.open("w", encoding="utf-8") as handle:
        json.dump(multiPayload, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Cleanup: multi-event URLs {len(multiEntries)} -> {outputMultiPath.name}{Style.RESET_ALL}")

    for idx, record in enumerate(removedEvents, 1):
        record["id"] = idx

    removedPayload = {"count": len(removedEvents), "records": removedEvents}
    with removedPath.open("w", encoding="utf-8") as handle:
        json.dump(removedPayload, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.YELLOW}Cleanup: removed records {removedPayload['count']} -> {removedPath.name}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
