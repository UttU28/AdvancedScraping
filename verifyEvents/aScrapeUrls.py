"""
Open Chrome, visit each URL from source.csv one by one,
scrape page text and save to verifyEvents/txtDir as *_homepage.txt.
URLs in removeLinks.txt (blacklist) are skipped.
"""
import re
from pathlib import Path
from time import sleep

from colorama import Fore, Style, init as colorama_init
from tqdm.auto import tqdm

CRAWLER_DIR = Path(__file__).resolve().parent
TXT_DIR = CRAWLER_DIR / "txtDir"
REMOVE_LINKS_PATH = CRAWLER_DIR / "removeLinks.txt"

from dotenv import load_dotenv

load_dotenv(CRAWLER_DIR / ".env")

from selenium.webdriver.common.by import By
from server import (
    startChrome,
    setupChromeDriver,
    cleanupChrome,
    read_events_csv,
    chromeDriverPath,
    chromeAppPath,
    chromeUserDataDir,
    debuggingPort,
)


def load_blacklist() -> set[str]:
    """Load blacklisted URL patterns from removeLinks.txt. Lines starting with # are ignored."""
    blacklist: set[str] = set()
    if not REMOVE_LINKS_PATH.exists():
        return blacklist
    with REMOVE_LINKS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                blacklist.add(line.lower())
    return blacklist


def is_url_blacklisted(url: str, blacklist: set[str]) -> bool:
    """Return True if url matches any blacklist entry (substring match either way)."""
    if not url:
        return False
    url_lower = url.lower()
    return any(entry in url_lower or url_lower in entry for entry in blacklist)


def sanitize_filename(name: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:max_len] or "page"


def main():
    colorama_init(autoreset=True)

    rows = read_events_csv()
    if not rows:
        print(Fore.YELLOW + "No rows in source.csv.")
        return
    blacklist = load_blacklist()
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    # Detect already-scraped pages so we can resume from where we left off
    existing_files = {p.name for p in TXT_DIR.glob("*_homepage.txt")}
    total = len(rows)

    chrome_app = None
    driver = None

    processed = 0
    skipped = 0
    errors = 0
    already = 0
    try:
        chrome_app = startChrome(debuggingPort, chromeUserDataDir, chromeAppPath)
        if not chrome_app:
            print(Fore.RED + "Chrome could not start (port in use?).")
            return
        driver = setupChromeDriver(debuggingPort, chromeDriverPath)
        with tqdm(total=total, unit="event", desc="Scraping") as pbar:
            for i, row in enumerate(rows, 1):
                url = (row.get("Event URL") or "").strip()
                title = (row.get("Event Title") or "").strip() or f"event_{i}"
                filename = f"{sanitize_filename(title)}_homepage.txt"
                out_path = TXT_DIR / filename

                # Default: assume we'll advance the bar for this row
                advance = True

                if not url:
                    skipped += 1
                    pbar.set_postfix(
                        processed=processed,
                        skipped=skipped,
                        errors=errors,
                        already=already,
                        current="no URL",
                    )
                    pbar.update(1)
                    continue

                if is_url_blacklisted(url, blacklist):
                    skipped += 1
                    pbar.set_postfix(
                        processed=processed,
                        skipped=skipped,
                        errors=errors,
                        already=already,
                        current="blacklisted",
                    )
                    pbar.update(1)
                    continue

                # Skip if we've already scraped this event (file exists and non-empty)
                if filename in existing_files:
                    try:
                        if out_path.stat().st_size > 0:
                            already += 1
                            pbar.set_postfix(
                                processed=processed,
                                skipped=skipped,
                                errors=errors,
                                already=already,
                                current="already scraped",
                            )
                            pbar.update(1)
                            continue
                    except FileNotFoundError:
                        # File disappeared since we scanned existing_files; treat as not scraped
                        existing_files.discard(filename)

                try:
                    driver.get(url)
                    # Let the page render
                    sleep(2)
                    # Simple scroll to load lazy content
                    for _ in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        sleep(1)
                    body_text = driver.find_element(By.TAG_NAME, "body").text
                    out_path.write_text(body_text, encoding="utf-8")
                    processed += 1
                    pbar.set_postfix(
                        processed=processed,
                        skipped=skipped,
                        errors=errors,
                        already=already,
                        current="ok",
                    )
                except Exception as e:
                    errors += 1
                    message = str(e)
                    # Treat common network/URL issues as "not found" without noisy stack traces
                    is_not_found = (
                        "net::ERR_NAME_NOT_RESOLVED" in message
                        or "invalid argument" in message
                    )
                    if not is_not_found:
                        print(Fore.RED + f"\n[ERROR] {title} ({url}): {message}")
                    pbar.set_postfix(
                        processed=processed,
                        skipped=skipped,
                        errors=errors,
                        already=already,
                        current="not_found" if is_not_found else "error",
                    )
                finally:
                    if advance:
                        pbar.update(1)
                    sleep(1)

        summary_color = Fore.GREEN if errors == 0 else Fore.YELLOW
        print(
            summary_color
            + "Scraping finished. "
            f"Processed: {processed}, Skipped: {skipped}, Already: {already}, Errors: {errors}."
        )
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        if driver:
            cleanupChrome(driver, chrome_app)
    print("Closed.")


if __name__ == "__main__":
    main()
