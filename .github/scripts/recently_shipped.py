"""Refresh the "Recently shipped" list in README.md from the portfolio build log.

Reads https://franciscode.dev/build-log.json (override with BUILD_LOG_URL) and
rewrites the lines between the recently-shipped markers. If the feed is
unreachable or malformed, the README is left untouched and the script exits 0,
so a portfolio outage never breaks the profile.

Standard library only; keeps the README's existing line endings.
"""

import html
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

FEED = os.environ.get("BUILD_LOG_URL", "https://franciscode.dev/build-log.json")
README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- recently-shipped:start -->"
END = "<!-- recently-shipped:end -->"
LIMIT = 5


def fetch_entries():
    request = urllib.request.Request(FEED, headers={"User-Agent": "profile-readme-workflow"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    entries = []
    for item in payload.get("entries", [])[:LIMIT]:
        day = date.fromisoformat(str(item["date"]))
        # the note is plain text: flatten it and escape anything HTML-like
        note = html.escape(" ".join(str(item["note"]).split()), quote=False)
        if note:
            entries.append((day, note))
    return entries


def main():
    try:
        entries = fetch_entries()
    except Exception as error:  # network, JSON or shape problems: keep README as is
        print(f"recently-shipped: feed unavailable ({error}); README unchanged")
        return 0
    if not entries:
        print("recently-shipped: feed had no entries; README unchanged")
        return 0

    raw = README.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    start, end = raw.find(START), raw.find(END)
    if start == -1 or end == -1 or end < start:
        print("recently-shipped: markers not found in README.md", file=sys.stderr)
        return 1

    lines = [f"- {day.strftime('%b')} {day.day}, {day.year} → {note}" for day, note in entries]
    block = START + newline + newline.join(lines) + newline + END
    updated = raw[:start] + block + raw[end + len(END):]
    if updated != raw:
        README.write_bytes(updated.encode("utf-8"))
        print(f"recently-shipped: wrote {len(lines)} entries")
    else:
        print("recently-shipped: already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
