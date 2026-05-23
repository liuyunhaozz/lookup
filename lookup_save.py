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
import re
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


# --- definition formatting (HTML, for pretty Anki cards) ---------------------

# Reference sections we drop to keep cards readable (e.g. "run" has ~70 idioms).
# ORIGIN is kept — it sits at the end of the entry, after these.
_DROP_SECTIONS = ("DERIVATIVES", "PHRASES", "PHRASAL VERBS", "USAGE")

# Part-of-speech labels, longest first so multi-word ones win.
_POS = [
    "combining form", "modal verb", "auxiliary verb", "phrasal verb",
    "transitive verb", "intransitive verb", "plural noun", "proper noun",
    "mass noun", "definite article", "indefinite article",
    "cardinal number", "ordinal number",
    "noun", "verb", "adjective", "adverb", "pronoun", "preposition",
    "conjunction", "determiner", "exclamation", "interjection",
    "abbreviation", "symbol", "prefix", "suffix", "contraction",
]
_POS_RE = re.compile(r"(?:(?<=\A)|(?<=\.\s)|(?<=\)\s))(" + "|".join(_POS) + r")\b")
_SECTION_RE = re.compile(r"\b(ORIGIN|DERIVATIVES|PHRASES|PHRASAL VERBS|USAGE)\b")
_SENSE_RE = re.compile(
    r"(?:(?<=</b>\s)|(?<=\]\s)|(?<=\.\s)|(?<=\)\s))(\d{1,2})\s"
)


def trim_entry(body):
    """Keep core senses + ORIGIN; drop the long phrase/derivative reference lists."""
    cut = len(body)
    for kw in _DROP_SECTIONS:
        i = body.find(kw)
        if i != -1:
            cut = min(cut, i)
    core = body[:cut].rstrip()
    origin = body.find("ORIGIN")
    if origin >= cut:  # ORIGIN sits after the dropped sections (the usual case)
        return (core + " " + body[origin:].strip()).strip()
    return core  # ORIGIN (if any) is already inside core


def format_definition(body):
    """Turn the flat dictionary blob into structured HTML for Anki."""
    t = trim_entry(body.strip())
    t = re.sub(r"\s*\|\s*", " · ", t)                       # overloaded pipe -> middot
    t = t.replace(" · )", ")").replace(" · ;", ";").replace(" · ,", ",")
    t = _POS_RE.sub(r"<br><b>\1</b>", t)                    # parts of speech
    t = _SECTION_RE.sub(r'<br><br><span style="color:#888">\1</span>', t)
    t = _SENSE_RE.sub(r"<br><b>\1.</b> ", t)                # numbered senses
    t = t.replace(" • ", "<br>&nbsp;&nbsp;• ")              # sub-senses
    t = re.sub(r"\[([^\]]+)\]", r"<i>[\1]</i>", t)          # grammar labels
    t = re.sub(r":\s([^<]+?)(?=<|$)",                       # example sentences
               lambda m: ": <i>%s</i>" % m.group(1).rstrip(), t)
    t = re.sub(r"^(?:<br>)+", "", t)                        # no leading break
    t = t.replace("</b> <br>", "</b><br>")
    t = re.sub(r"[ ]{2,}", " ", t).strip()
    return t


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
        "definition": format_definition(definition),
        "date_saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": frontmost_app(),
    })
    notify("📖 Word saved", "%s ✓" % term)


if __name__ == "__main__":
    main()
