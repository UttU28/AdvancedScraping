"""
Open Chrome, visit each URL from source.csv one by one,
scrape page text and save to verifyEvents/txtDir as *_homepage.txt.
"""
import re
from pathlib import Path
from time import sleep

CRAWLER_DIR = Path(__file__).resolve().parent
TXT_DIR = CRAWLER_DIR / "txtDir"

from dotenv import load_dotenv
load_dotenv(CRAWLER_DIR / ".env")

from selenium.webdriver.common.by import By
from app import (
    startChrome, setupChromeDriver, cleanupChrome, read_events_csv,
    chromeDriverPath, chromeAppPath, chromeUserDataDir, debuggingPort,
)


def sanitize_filename(name: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\s-]", "", name)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:max_len] or "page"


def main():
    rows = read_events_csv()
    if not rows:
        print("No rows in source.csv.")
        return
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    # Detect already-scraped pages so we can resume from where we left off
    existing_files = {p.name for p in TXT_DIR.glob("*_homepage.txt")}
    total = len(rows)

    chrome_app = None
    driver = None
    try:
        chrome_app = startChrome(debuggingPort, chromeUserDataDir, chromeAppPath)
        if not chrome_app:
            print("Chrome could not start (port in use?).")
            return
        driver = setupChromeDriver(debuggingPort, chromeDriverPath)
        for i, row in enumerate(rows, 1):
            url = (row.get("Event URL") or "").strip()
            title = (row.get("Event Title") or "").strip() or f"event_{i}"
            filename = f"{sanitize_filename(title)}_homepage.txt"
            out_path = TXT_DIR / filename

            if not url:
                print(f"[{i}/{total}] Skipping (no URL): {title}")
                continue

            # Skip if we've already scraped this event (file exists and non-empty)
            if filename in existing_files and out_path.stat().st_size > 0:
                print(f"[{i}/{total}] Skipping (already scraped): {title}")
                continue

            print(f"[{i}/{total}] {title}")
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
                print(f"  Saved: {out_path.name}")
            except Exception as e:
                print(f"  Error: {e}")
            sleep(1)
        print("Done.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        if driver:
            cleanupChrome(driver, chrome_app)
    print("Closed.")


if __name__ == "__main__":
    main()
