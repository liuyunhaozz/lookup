#!/usr/bin/python3
"""
lookup_save.py — Look up a word in the macOS dictionary and save it to a list.

Reads a word/phrase from stdin (how the Automator Quick Action passes the current
selection) or from command-line arguments, fetches the definition from the same
dictionaries the Dictionary.app uses, and appends it to a CSV file.

Must run under Apple's /usr/bin/python3, which ships with the DictionaryServices
framework — no third-party packages required.

Manual test:
    echo "serendipity" | /usr/bin/python3 lookup_save.py
"""

import csv
import os
import subprocess
import sys
from datetime import datetime

# Where the running list lives. ~/Documents is TCC-protected; if the first write
# triggers a permission prompt you'd rather avoid, change this to "~/vocabulary.csv".
CSV_PATH = os.path.expanduser("~/Documents/vocabulary.csv")

FIELDNAMES = ["word", "pronunciation", "definition", "date_saved", "source"]


def get_definition(term):
    """Return the dictionary text for `term`, or None if there is no entry."""
    from DictionaryServices import DCSCopyTextDefinition

    result = DCSCopyTextDefinition(None, term, (0, len(term)))
    return str(result) if result else None


def parse_definition(raw):
    """Best-effort split of the raw blob into (pronunciation, definition body).

    Format is roughly:  "<headword> <syllables> | <pronunciation> | <senses…>"
    Senses can themselves contain '|', so we only treat the first two '|' as
    structural and rejoin the rest.
    """
    segs = raw.split("|")
    if len(segs) >= 3:
        pronunciation = segs[1].strip()
        body = "|".join(segs[2:]).strip()
    else:
        pronunciation = ""
        body = raw.strip()
    return pronunciation, body


def frontmost_app():
    """Best-effort name of the app the selection came from. Blank if unavailable."""
    script = (
        'tell application "System Events" to get name of '
        "first application process whose frontmost is true"
    )
    try:
        out = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def notify(title, text):
    """Show a macOS notification banner. Failures are non-fatal."""
    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    script = 'display notification "%s" with title "%s"' % (esc(text), esc(title))
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
    except Exception:
        pass


def read_term():
    """The word/phrase to look up: stdin first, then argv."""
    data = ""
    if not sys.stdin.isatty():
        data = sys.stdin.read()
    if not data.strip() and len(sys.argv) > 1:
        data = " ".join(sys.argv[1:])
    # Collapse whitespace/newlines from a messy selection into a single term.
    return " ".join(data.split())


def existing_words(path):
    """Lowercased set of words already in the CSV (for dedup)."""
    words = set()
    if not os.path.exists(path):
        return words
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                w = (row.get("word") or "").strip().lower()
                if w:
                    words.add(w)
    except Exception:
        pass
    return words


def append_row(path, row):
    """Append a row, creating the file with a header if needed."""
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def main():
    term = read_term()
    if not term:
        notify("📖 Word list", "Nothing selected to look up.")
        return

    raw = get_definition(term)
    if not raw:
        notify("📖 Word list", 'No dictionary entry for "%s" — not saved.' % term)
        return

    if term.lower() in existing_words(CSV_PATH):
        notify("📖 Word list", "Already saved: %s" % term)
        return

    pronunciation, definition = parse_definition(raw)
    append_row(CSV_PATH, {
        "word": term,
        "pronunciation": pronunciation,
        "definition": definition,
        "date_saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": frontmost_app(),
    })
    notify("📖 Word saved", "%s ✓" % term)


if __name__ == "__main__":
    main()
