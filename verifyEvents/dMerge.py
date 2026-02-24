"""
Apply a blacklist to extraction results:
- Read blacklisted sites from a txt file (one URL or domain per line)
- Remove matching events from extraction_results.json and extraction_results_single.json
- Merge remaining into one list, re-number ids, and rewrite bulk + single + multi
- Append removed (blacklisted) records to extraction_results_removed.json with removed_reason "blacklisted"

Usage (from verifyEvents folder):
  python apply_blacklist.py
  python apply_blacklist.py removeLinks.txt
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from colorama import Fore, Style, init

init(autoreset=True)

verifyEventsDir = Path(__file__).resolve().parent

resultsCleanPath = verifyEventsDir / "extraction_results_clean.json"
resultsSinglePath = verifyEventsDir / "extraction_results_single.json"
resultsMultiPath = verifyEventsDir / "extraction_results_multi.json"
resultsRemovedPath = verifyEventsDir / "extraction_results_removed.json"
defaultBlacklistPath = verifyEventsDir / "removeLinks.txt"


def loadBlacklist(path: Path) -> set[str]:
    """One URL or domain per line; stripped and lowercased."""
    entries: set[str] = set()
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip().lower()
        if value and not value.startswith("#"):
            entries.add(value)
    return entries


def isBlacklisted(url: str, blacklist: set[str]) -> bool:
    url = (url or "").strip().lower()
    if not url:
        return False
    return any(entry in url or url in entry for entry in blacklist)


def main():
    blacklistArg = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else defaultBlacklistPath.name
    blacklistPath = verifyEventsDir / blacklistArg
    blacklist = loadBlacklist(blacklistPath)
    if not blacklist:
        print(f"{Fore.YELLOW}Merge: no blacklist entries in {blacklistPath.name} (or file missing). Exiting.{Style.RESET_ALL}")
        return

    if not resultsCleanPath.exists():
        print(f"{Fore.RED}Merge: {resultsCleanPath.name} not found. Run cleanup first.{Style.RESET_ALL}")
        return

    with resultsCleanPath.open(encoding="utf-8") as handle:
        cleanEvents = json.load(handle)
    if not isinstance(cleanEvents, list):
        print(f"{Fore.RED}Merge: extraction_results_clean.json is not a list.{Style.RESET_ALL}")
        return

    keptEvents: list[dict] = []
    blacklistedEvents: list[dict] = []
    for record in cleanEvents:
        if not isinstance(record, dict):
            continue
        url = (record.get("url") or "").strip()
        if isBlacklisted(url, blacklist):
            blacklistedEvents.append({**record, "removed_reason": "blacklisted"})
        else:
            keptEvents.append(record)

    for idx, record in enumerate(keptEvents, 1):
        record["id"] = idx

    groupedByUrl: dict[str, list[dict]] = defaultdict(list)
    for record in keptEvents:
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

    with resultsCleanPath.open("w", encoding="utf-8") as handle:
        json.dump(keptEvents, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Merge: kept events {len(keptEvents)} -> {resultsCleanPath.name}{Style.RESET_ALL}")

    singlePayload = {"count": len(singleEvents), "events": singleEvents}
    with resultsSinglePath.open("w", encoding="utf-8") as handle:
        json.dump(singlePayload, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Merge: single-event URLs {len(singleEvents)} -> {resultsSinglePath.name}{Style.RESET_ALL}")

    multiPayload = {"count": len(multiEntries), "entries": multiEntries}
    with resultsMultiPath.open("w", encoding="utf-8") as handle:
        json.dump(multiPayload, handle, indent=2, ensure_ascii=False)
    print(f"{Fore.CYAN}Merge: multi-event URLs {len(multiEntries)} -> {resultsMultiPath.name}{Style.RESET_ALL}")

    if blacklistedEvents:
        removedPayload = {"count": 0, "records": []}
        if resultsRemovedPath.exists():
            try:
                with resultsRemovedPath.open(encoding="utf-8") as handle:
                    removedPayload = json.load(handle)
            except json.JSONDecodeError:
                removedPayload = {"count": 0, "records": []}
            if isinstance(removedPayload, list):
                removedPayload = {"count": len(removedPayload), "records": removedPayload}

        removedPayload["records"].extend(blacklistedEvents)
        for idx, record in enumerate(removedPayload["records"], 1):
            record["id"] = idx
        removedPayload["count"] = len(removedPayload["records"])

        with resultsRemovedPath.open("w", encoding="utf-8") as handle:
            json.dump(removedPayload, handle, indent=2, ensure_ascii=False)
        print(f"{Fore.YELLOW}Merge: blacklisted events {len(blacklistedEvents)} -> {resultsRemovedPath.name} (total removed: {removedPayload['count']}){Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Merge: no records matched the blacklist.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
