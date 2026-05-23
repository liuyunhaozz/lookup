# 📖 Save looked-up words to a list

Select a word anywhere on your Mac (Safari, your news app, Mail, anywhere), press a
keyboard shortcut, and the word + its dictionary definition is appended to a CSV file you
can open in Numbers or Excel. It uses the *same* dictionaries as Apple's Dictionary app.

> **Why a hotkey instead of "just watching Dictionary.app"?**
> The Dictionary app and the macOS "Look Up" popover keep no history and expose no hook —
> nothing can record what you look up there. So this gives you a deliberate *"look up **and
> save**"* gesture. Keep using Dictionary.app for casual browsing; use the hotkey for the
> words you actually want to keep.

## What's here

| File | Role |
|------|------|
| `lookup_save.py` | The worker. Looks up a word and appends it to the CSV. No installs needed — uses Apple's built-in `/usr/bin/python3`. |
| `Save to Word List.workflow` | The trigger: an Automator **Quick Action**. Already installed to `~/Library/Services/`. |

**Your list lives at:** `~/Documents/vocabulary.csv`
Columns: `word, pronunciation, definition, date_saved, source`.
To move it, change `CSV_PATH` at the top of `lookup_save.py`.

## One-time setup (≈1 minute)

The script and the Quick Action are already in place. You just need to assign a hotkey.

### 1. Assign the keyboard shortcut

1. Open **System Settings → Keyboard → Keyboard Shortcuts… → Services**.
2. Scroll to the **Text** section and find **“Save to Word List.”**
3. Tick its checkbox, then click **Add Shortcut** (or the shortcut field) and press your
   combo — e.g. **⌃⌥D** (Control-Option-D).
4. Close System Settings.

> If "Save to Word List" doesn't appear in the list yet, log out and back in once (or
> restart) — macOS sometimes needs a session refresh to pick up a newly installed Quick
> Action.

### 2. First-run permission prompts (expected, one time)

The first time you trigger it, macOS may ask to:

- **Allow notifications** — say yes, so you get the "Saved ✓" banner.
- **Control "System Events"** — this is only used to record *which app* you were in (the
  `source` column). Allowing it is nice-to-have; **denying it is fine** — the word still
  saves, the `source` column is just left blank.
- **Access your Documents folder** — needed to write the CSV. If you'd rather not grant
  this, change `CSV_PATH` in `lookup_save.py` to `~/vocabulary.csv` (your home folder isn't
  permission-protected).

## How to use it

1. Select a word while reading.
2. Press your shortcut (⌃⌥D).
3. A banner confirms **“📖 Word saved — <word> ✓.”** Done. It also tells you if a word is
   already on the list or has no dictionary entry.

Open `~/Documents/vocabulary.csv` in **Numbers** any time to browse your collection.

## Try it without the hotkey

```sh
echo "serendipity" | /usr/bin/python3 lookup_save.py
```

## If the Quick Action ever misbehaves — rebuild it by hand

The generated `.workflow` works on this machine, but if a macOS update breaks it, it's
trivial to recreate:

1. Open **Automator** → **New Document** → **Quick Action**.
2. At the top: set **“Workflow receives current”** to **text** in **any application**.
3. In the left search box, find **Run Shell Script** and drag it into the workflow.
4. Set **Shell** to `/bin/zsh` and **Pass input** to **to stdin**.
5. Replace the script box contents with exactly:
   ```sh
   /usr/bin/python3 "/Users/yunhao/Public/playground/lookup/lookup_save.py"
   ```
6. **File → Save**, name it **Save to Word List**. It installs itself; then redo step 1
   above to assign the hotkey.

## Uninstall

```sh
rm -rf "$HOME/Library/Services/Save to Word List.workflow"
```

(Your `vocabulary.csv` is untouched by this.)
