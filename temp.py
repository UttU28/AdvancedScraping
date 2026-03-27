"""
Parse advisory-board HTML (team-member blocks) and write Name, Company, Position, LinkedIn CSV.

Input: aa.html next to this script (or path as first CLI arg).
Output: advisory_board.csv in the same folder.
"""

from __future__ import annotations

import argparse
import csv
import html
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parent


def _split_position_company(raw: str) -> tuple[str, str]:
    """Position text is usually 'Title @ Company'; split on first ' @ '."""
    text = html.unescape(raw).strip()
    if not text:
        return "", ""
    if " @ " in text:
        pos, company = text.split(" @ ", 1)
        return pos.strip(), company.strip()
    return text, ""


def parse_team_members(html_text: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows: list[dict[str, str]] = []
    for member in soup.select("div.team-member"):
        h4 = member.select_one("h4.light")
        pos_el = member.select_one("div.position")
        link_el = member.select_one('a[href*="linkedin"]')
        if not h4:
            continue
        name = html.unescape(h4.get_text(strip=True))
        pos_raw = pos_el.get_text(strip=True) if pos_el else ""
        position, company = _split_position_company(pos_raw)
        linkedin = (link_el.get("href") or "").strip() if link_el else ""
        rows.append(
            {
                "Name": name,
                "Company": company,
                "Position": position,
                "LinkedIn": linkedin,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export team HTML to CSV.")
    parser.add_argument(
        "input_html",
        nargs="?",
        default=str(_ROOT / "aa.html"),
        help="Path to HTML file (default: aa.html next to this script)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(_ROOT / "advisory_board.csv"),
        help="Output CSV path (default: advisory_board.csv)",
    )
    args = parser.parse_args()

    path = Path(args.input_html)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    html_text = path.read_text(encoding="utf-8", errors="replace")
    rows = parse_team_members(html_text)
    if not rows:
        print("No div.team-member entries found.", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output)
    fieldnames = ["Name", "Company", "Position", "LinkedIn"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
