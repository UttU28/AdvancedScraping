"""
Read scraped *_homepage.txt, send to LLM to classify (event_page/newsletter/etc.)
and extract event name + dates. Save to extraction_results.json.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

# Transient errors worth retrying
def _retryable_exceptions():
    excs = [ConnectionError, TimeoutError]
    try:
        from http.client import RemoteDisconnected
        excs.append(RemoteDisconnected)
    except ImportError:
        pass
    try:
        from requests.exceptions import ConnectionError as ReqConnectionError, ReadTimeout
        excs.extend([ReqConnectionError, ReadTimeout])
    except ImportError:
        pass
    try:
        from urllib3.exceptions import ProtocolError
        excs.append(ProtocolError)
    except ImportError:
        pass
    return tuple(excs)


RETRYABLE = _retryable_exceptions()
MAX_RETRIES = 5
RETRY_DELAY_BASE = 2  # seconds

CRAWLER_DIR = Path(__file__).resolve().parent
TXT_DIR = CRAWLER_DIR / "txtDir"

from dotenv import load_dotenv
import openai
from server import read_events_csv

load_dotenv(CRAWLER_DIR / ".env")

openai.api_key = "sk-proj---"

EXTRACTION_SYSTEM_PROMPT = """You are analyzing scraped visible text from a single webpage. Your task is to:

1) CLASSIFY the page into exactly one of these site types:
   - event_page: The page describes one or more specific conferences, summits, expos, or events with names and dates.
   - newsletter: The page is primarily a newsletter, email signup, or article list rather than an event landing page.
   - generic_homepage: Company or organization homepage with no specific event, or generic marketing with no event name and dates.
   - other: None of the above (e.g. login page, error page, unrelated content).

2) EXTRACT EVENTS (only if site_type is "event_page"):
   - If the page lists ONE event: put one object in the "events" array with event_name, location, start_date (mm/dd/yyyy), end_date (mm/dd/yyyy), and optional notes.
   - If the page lists MULTIPLE events (different names, locations, or date ranges): add ONE object per event to the "events" array. Each event must have: event_name, location (city/country or "TBD"), start_date (mm/dd/yyyy), end_date (mm/dd/yyyy), and optional notes.
   - Convert any date format in the text to mm/dd/yyyy.
   - If no clear event(s) found, use events: [].

If site_type is NOT event_page, use "events": [].

Respond with a single JSON object only, no markdown or extra text. Use this exact structure:
{"site_type": "<event_page|newsletter|generic_homepage|other>", "events": [{"event_name": "<string>", "location": "<string>", "start_date": "<mm/dd/yyyy>", "end_date": "<mm/dd/yyyy>", "notes": "<optional string>"}, ...], "page_notes": "<short reason for classification for manual check>"}"""


def get_url_for_txt_file(txt_path: Path) -> str:
    stem = txt_path.stem.replace("_homepage", "").replace("_", " ")
    for row in read_events_csv():
        title = (row.get("Event Title") or "").strip()
        if title and stem.lower() in title.lower():
            return (row.get("Event URL") or "").strip()
    return ""


def extract_with_llm(page_text: str) -> dict:
    model = os.getenv("OPENAI_EXTRACT_MODEL", "gpt-3.5-turbo")
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this scraped page text and respond with the JSON object only.\n\n---\n{page_text[:12000]}\n---"},
                ],
                temperature=0.1,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            raw = (response["choices"][0]["message"]["content"] or "").strip()
            if "```" in raw:
                m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
                if m:
                    raw = m.group(1).strip()
            return json.loads(raw)
        except RETRYABLE as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} in {delay}s: {e}")
                time.sleep(delay)
            else:
                print(f"Error: {e}")
                raise
        except Exception as e:
            print(f"Error: {e}")
            raise
    raise last_error


def run_extraction(txt_path: Path, results_path: Path):
    text = txt_path.read_text(encoding="utf-8")
    url = get_url_for_txt_file(txt_path)
    out = extract_with_llm(text)
    site_type = out.get("site_type") or "other"
    if site_type not in ("event_page", "newsletter", "generic_homepage", "other"):
        site_type = "other"
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else []
    events = out.get("events")
    if isinstance(events, list) and len(events) > 0:
        for ev in events:
            if not isinstance(ev, dict):
                continue
            row = {
                "source_txt": txt_path.name,
                "url": url,
                "site_type": site_type,
                "event_name": ev.get("event_name"),
                "location": ev.get("location"),
                "start_date": ev.get("start_date"),
                "end_date": ev.get("end_date"),
                "notes": ev.get("notes") or out.get("page_notes"),
            }
            results.append(row)
    else:
        results.append({
            "source_txt": txt_path.name,
            "url": url,
            "site_type": site_type,
            "event_name": None,
            "location": None,
            "start_date": None,
            "end_date": None,
            "notes": out.get("page_notes"),
        })
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results[-1] if results else None


def main():
    if not openai.api_key:
        print("OPENAI_API_KEY is not set (verifyEvents/.env)")
        return

    results_path = CRAWLER_DIR / "extraction_results.json"

    # Single-file mode
    if len(sys.argv) > 1:
        txt_arg = Path(sys.argv[1])
        if not txt_arg.is_absolute():
            # First try inside txtDir, then relative to verifyEvents
            candidate = TXT_DIR / txt_arg
            if candidate.exists():
                txt_path = candidate
            else:
                txt_path = CRAWLER_DIR / txt_arg
        else:
            txt_path = txt_arg
        if not txt_path.exists():
            print(f"File not found: {txt_path}")
            return
        result = run_extraction(txt_path, results_path)
        print(json.dumps(result, indent=2))
        print(f"Saved to {results_path}")
        return

    # Batch mode: all *_homepage.txt inside txtDir
    if not TXT_DIR.exists():
        print(f"txtDir not found at {TXT_DIR}. Run open_first_url.py first.")
        return
    txt_files = sorted(TXT_DIR.glob("*_homepage.txt"))
    if not txt_files:
        print(f"No *_homepage.txt in {TXT_DIR}.")
        return
    for i, p in enumerate(txt_files, 1):
        print(f"[{i}/{len(txt_files)}] {p.name} ...")
        run_extraction(p, results_path)
    print(f"Done. Results in {results_path}")


if __name__ == "__main__":
    main()
