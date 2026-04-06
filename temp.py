#!/usr/bin/env python3
"""
Parse a Pinetool / Energy Tech Summit speakers list HTML export (e.g. aa.html)
into CSV: Name, Company, Position, Link.

The Link column is the full profile URL like:
  https://events.pinetool.ai/3652/#speakers/1043552?referrer%5Bpathname%5D=...
"""

from __future__ import annotations

import argparse
import csv
import html as html_module
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

SPEAKER_FRAGMENT_RE = re.compile(r"^#speakers/\d+", re.I)


def _text(el) -> str:
    if el is None:
        return ""
    return " ".join(el.get_text().split())


def parse_row(anchor, base_url: str) -> dict[str, str] | None:
    raw_href = (anchor.get("href") or "").strip()
    if not raw_href:
        return None
    href = html_module.unescape(raw_href)
    if not SPEAKER_FRAGMENT_RE.match(href.split("?", 1)[0]):
        return None

    info = anchor.select_one(".info")
    if info is None:
        return None

    name = _text(info.find("h3"))
    h4s = info.find_all("h4")
    if len(h4s) >= 2:
        position = " ".join(_text(h) for h in h4s[:-1]).strip()
        company = _text(h4s[-1])
    elif len(h4s) == 1:
        position = _text(h4s[0])
        company = ""
    else:
        position, company = "", ""

    base = base_url.rstrip("/")
    link = f"{base}/{href}"

    return {
        "Name": name,
        "Company": company,
        "Position": position,
        "Link": link,
    }


def extract_rows(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for a in soup.select('a[href^="#speakers/"]'):
        href = html_module.unescape((a.get("href") or "").strip())
        key = href.split("?", 1)[0]
        if key in seen:
            continue
        row = parse_row(a, base_url)
        if row:
            seen.add(key)
            rows.append(row)
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Speakers HTML → CSV (Name, Company, Position, Link).")
    p.add_argument(
        "input_html",
        nargs="?",
        default="aa.html",
        type=Path,
        help="Saved HTML (default: aa.html)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("speakers_from_html.csv"),
        help="Output CSV path",
    )
    p.add_argument(
        "-b",
        "--base-url",
        default="https://events.pinetool.ai/3652",
        help="Site base for Link column (default: https://events.pinetool.ai/3652)",
    )
    args = p.parse_args()

    path: Path = args.input_html
    if not path.is_file():
        print(f"Not found: {path}", file=sys.stderr)
        return 1

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    rows = extract_rows(soup, args.base_url)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["Name", "Company", "Position", "Link"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
