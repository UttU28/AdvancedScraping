"""
Read scraped *_homepage.txt, send to LLM to classify (event_page/newsletter/etc.)
and extract event name + dates. Save to extraction_results.json.
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from colorama import Fore, Style, init as colorama_init
from tqdm.auto import tqdm


USE_MODEL = "GOOGLE"  # or "OPENAI"

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

# Load API keys from environment; support both OpenAI and Google Gemini
openai.api_key = os.getenv("OPENAI_API_KEY", "")

try:
    # google-genai 1.x (new Gemini SDK)
    from google import genai as google_genai  # type: ignore[attr-defined]
except Exception:
    google_genai = None  # type: ignore[assignment]

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


def _extract_with_openai(page_text: str) -> dict:
    model = os.getenv("OPENAI_EXTRACT_MODEL", "gpt-4o-mini")
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Analyze this scraped page text and respond with the "
                            "JSON object only.\n\n---\n"
                            f"{page_text[:12000]}\n---"
                        ),
                    },
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


def _extract_with_gemini(page_text: str) -> dict:
    if google_genai is None:
        raise RuntimeError("google-genai SDK is not installed; run `pip install google-genai` in verifyEvents env.")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is not set in verifyEvents/.env")

    model_name = os.getenv("GEMINI_EXTRACT_MODEL", "models/gemini-flash-lite-latest")

    client = google_genai.Client(api_key=api_key)

    prompt = (
        EXTRACTION_SYSTEM_PROMPT
        + "\n\nAnalyze this scraped page text and respond with the JSON object only.\n\n---\n"
        + page_text[:12000]
        + "\n---"
    )

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=google_genai.types.GenerateContentConfig(  # type: ignore[attr-defined]
                    temperature=0.1,
                ),
            )
            text = resp.text or ""
            raw = text.strip()
            if "```" in raw:
                m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
                if m:
                    raw = m.group(1).strip()
            return json.loads(raw)
        except RETRYABLE as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} in {delay}s (Gemini, network): {e}")
                time.sleep(delay)
            else:
                print(f"Error (Gemini, network): {e}")
                raise
        except Exception as e:
            # Treat 5xx / UNAVAILABLE errors from the Gemini API itself as retryable too
            msg = str(e)
            status_code = getattr(e, "status_code", None)
            is_server_side = False
            try:
                if status_code is not None and 500 <= int(status_code) < 600:
                    is_server_side = True
            except Exception:
                pass
            if "UNAVAILABLE" in msg or "try again later" in msg:
                is_server_side = True

            if is_server_side and attempt < MAX_RETRIES - 1:
                last_error = e
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} in {delay}s (Gemini, 5xx): {e}")
                time.sleep(delay)
                continue

            print(f"Error (Gemini): {e}")
            raise

    raise last_error


def extract_with_llm(page_text: str) -> dict:
    if USE_MODEL.upper() == "GOOGLE":
        return _extract_with_gemini(page_text)
    return _extract_with_openai(page_text)


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
    # Initialize color output once
    colorama_init(autoreset=True)

    if USE_MODEL.upper() == "OPENAI":
        if not openai.api_key:
            print("OPENAI_API_KEY is not set (verifyEvents/.env)")
            return
    else:
        if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            print("GOOGLE_API_KEY or GEMINI_API_KEY is not set (verifyEvents/.env)")
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
        print(Fore.GREEN + json.dumps(result, indent=2))
        print(Fore.GREEN + f"Saved to {results_path}")
        if results_path.exists():
            backup_path = results_path.with_suffix(results_path.suffix + ".bak")
            shutil.copy2(results_path, backup_path)
            print(Fore.CYAN + f"Backup saved to {backup_path.name}")
        return

    # Batch mode: all *_homepage.txt inside txtDir
    if not TXT_DIR.exists():
        print(f"txtDir not found at {TXT_DIR}. Run open_first_url.py first.")
        return
    txt_files = sorted(TXT_DIR.glob("*_homepage.txt"))
    if not txt_files:
        print(f"No *_homepage.txt in {TXT_DIR}.")
        return

    total = len(txt_files)
    processed = 0
    failed = 0

    with tqdm(total=total, unit="file", desc="LLM extraction") as pbar:
        for p in txt_files:
            pbar.set_postfix(current=p.name, processed=processed, failed=failed)
            try:
                run_extraction(p, results_path)
                processed += 1
            except Exception as exc:
                failed += 1
                # Show a concise, colored error but keep going
                print(
                    Fore.RED
                    + f"\n[ERROR] {p.name}: {exc}"
                )
            finally:
                pbar.set_postfix(current=p.name, processed=processed, failed=failed)
                pbar.update(1)

    summary_color = Fore.GREEN if failed == 0 else Fore.YELLOW
    print(
        summary_color
        + f"Extraction complete. Processed: {processed}, Failed: {failed}. "
        f"Results in {results_path}"
    )

    # Create backup at the end
    if results_path.exists():
        backup_path = results_path.with_suffix(results_path.suffix + ".bak")
        shutil.copy2(results_path, backup_path)
        print(Fore.CYAN + f"Backup saved to {backup_path.name}")


if __name__ == "__main__":
    main()
