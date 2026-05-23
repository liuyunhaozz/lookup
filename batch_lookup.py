#!/usr/bin/python3
"""
batch_lookup.py — Bulk-import words from CSV or Markdown files into your list.

Runs `lookup_save.py` once per word, so an existing list of words gets looked up
and appended (with full definitions) to `~/Documents/vocabulary.csv`, exactly as
the hotkey would. Where the words come from depends on the file extension:

  * `.csv`           — the **3rd column** of each row (change with --column).
  * `.md`/`.markdown` — every word/phrase inside "double quotes" on each line
                        (both straight "…" and curly "…" quotes are recognized).

Words with no dictionary entry, or already on the list, are skipped by
`lookup_save.py` itself — so a stray header cell like "word" just no-ops, and
re-running is safe.

Usage:
    /usr/bin/python3 batch_lookup.py --file words.csv
    /usr/bin/python3 batch_lookup.py --file notes.md
    /usr/bin/python3 batch_lookup.py --file *.csv *.md       # shell expands globs
    /usr/bin/python3 batch_lookup.py --file a.csv --column 2 --skip-header
"""

import argparse
import csv
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, "lookup_save.py")

# Text inside straight "…" or curly "…" quotes. Non-greedy, so multiple quoted
# spans on one Markdown line are matched separately.
QUOTE_RE = re.compile(r'"([^"]+)"|“([^”]+)”')


def words_from_csv(path, col_index, skip_header):
    """Yield the trimmed cell values from column `col_index` (0-based) of `path`."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        if skip_header:
            next(reader, None)
        for row in reader:
            if len(row) > col_index:
                cell = row[col_index].strip()
                if cell:
                    yield cell


def words_from_md(path):
    """Yield each trimmed quoted word/phrase, in order, from the Markdown file."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            for m in QUOTE_RE.finditer(line):
                word = (m.group(1) or m.group(2)).strip()
                if word:
                    yield word


def lookup(word):
    """Run the worker for one word. Returns True if it exited cleanly."""
    result = subprocess.run(
        ["/usr/bin/python3", WORKER, word],
        stdin=subprocess.DEVNULL,  # force argv path, never inherit a stray selection
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Look up and save every word in a CSV column via lookup_save.py."
    )
    parser.add_argument(
        "--file", required=True, nargs="+", metavar="FILE",
        help="One or more .csv or .md files (globs like *.csv are fine).",
    )
    parser.add_argument(
        "--column", type=int, default=3, metavar="N",
        help="1-based column to read words from in CSV files (default: 3).",
    )
    parser.add_argument(
        "--skip-header", action="store_true",
        help="Skip the first row of each CSV (ignored for .md files).",
    )
    args = parser.parse_args()

    if not os.path.exists(WORKER):
        sys.exit("Can't find lookup_save.py next to this script (%s)." % WORKER)

    # Expand any globs that the shell left unexpanded (e.g. quoted "*.csv").
    paths = []
    for pattern in args.file:
        matches = glob.glob(pattern)
        paths.extend(matches if matches else [pattern])

    col_index = args.column - 1
    if col_index < 0:
        sys.exit("--column must be 1 or greater.")

    total = 0
    for path in paths:
        if not os.path.exists(path):
            print("⚠️  Skipping (not found): %s" % path)
            continue
        print("📄 %s" % path)
        ext = os.path.splitext(path)[1].lower()
        if ext in (".md", ".markdown"):
            words = words_from_md(path)
        else:
            words = words_from_csv(path, col_index, args.skip_header)
        for word in words:
            total += 1
            print("   • %s" % word)
            lookup(word)

    print("\nDone — processed %d word%s." % (total, "" if total == 1 else "s"))


if __name__ == "__main__":
    main()
