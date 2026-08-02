# Graphic Sync

A Flame 2027 Python tool for keeping the **text of Type (Timeline FX) graphics**
identical across many sequences and aspect-ratio versions — and for managing the
**layout connections** between them — from one place.

Built for broadcast legal / disclaimer lines that must read identically across
16×9, 9×16, 1×1, 4×5, etc. while each aspect keeps its own framing. Works for any
Flame-generated Type graphic.

> Status: 1.0.0 — first public release, looking for testers. See
> [Known limitations](#known-limitations) before running it on production work.

<!-- TODO: add a screenshot or short GIF of the four tabs here -->

## How it works

A per-project JSON **registry** is the single source of truth for each graphic's
text. Segments are tagged `graphicNN` and receive their text from the registry —
one-directional (registry → tagged Type layers), so you edit text in one place
and push it everywhere. Layout (position / scale / format) is handled separately
through Flame's native **segment connections**, so text and layout stay
independent.

### Tabs

- **Segments** — every matching Type segment in the scope, with its text,
  assignment and sync status. Assign segments to a GFX number, group identical
  text (sort grouped by **In** for appearance order), and capture a segment's
  text into the registry — **Add All** seeds the whole registry from a grouped
  list in one click. (Assigning only *labels* a segment — it never changes the
  text on your timeline; that's what Sync does.)
- **Registry** — add / edit / remove graphic definitions (or **Remove All** to
  start fresh); Renumber with Swap/Overwrite; Sync Text to a scope.
- **Connections** — create / remove the native segment connections that share a
  graphic's layout across aspects. **Auto Connection** queues a connection group
  for every like-aspect / like-GFX set automatically; review, then Execute Queue.
  **Set as Source** marks which segment's layout is the master. After a run, every
  affected sequence is parked at its first frame and you're returned to where you
  started.
- **Settings** — registry folder, default scope, what counts as a target segment
  (match mode + name / track filters), Segments-tab defaults (Grouped Text +
  default sort), and getting-started tips.

## Requirements

- Autodesk Flame **2027** (2027.0.0+).
- PySide6 (ships with Flame 2027; nothing to install).

No third-party Python packages.

## Installation

Copy the single file into its own folder on Flame's shared Python path and
restart Flame:

```
/opt/Autodesk/shared/python/graphic_sync/graphic_sync.py
```

Use its own folder with this exact filename. Flame puts every tool folder on
`sys.path`, so a duplicate `graphic_sync` module elsewhere can shadow this one —
remove any older copies first. A **full Flame restart** is required (not "Reload
Python Hooks").

## Usage

Open it from any of:

- Right-click a timeline segment → **GFX Sync → GFX Sync…**
- Right-click in the Media Panel → **GFX Sync → GFX Sync…**
- Flame main menu → **GFX Sync → Open Manager…**

Typical flow:

1. **Settings** — point at a registry folder and set the scope / match rules.
2. **Segments** — assign segments to `GFX01`, `GFX02`, … (the "Grouped Text"
   toggle folds identical text so you can assign many at once). It auto-scans;
   there's no Scan button.
3. **Registry** — edit a graphic's text once; **Sync Text → Scope** pushes it to
   every tagged segment (with a preview). Use a line of `---` to separate Type
   layers. A segment whose text no longer matches its registry entry shows
   **OUT OF DATE** in the Segments tab.
4. **Connections** — **Auto Connection** → review the queued groups → **Execute
   Queue** to share layout across aspects.

Scopes (top of the window): **Selected · Current Sequence · Current Reel ·
Current Reel Group · All Sequences Reels**. The "Current …" scopes follow what's
open in Flame's **Timeline** tab (the tool switches you there on open).

## Known limitations

- **Flame 2027 only.** Built and tested against 2027.0.x. It may well run on
  2026.1+ (the Type Python API arrived in 2026.1), but that hasn't been tested —
  if you try it on 2026, please report what happens.
- The add-layer path for growing a Type to more layers tries a set of candidate
  API calls, guarded by a layer-count readback — text is only written to a layer
  index after the readback confirms it exists. It works in practice, but it isn't
  pinned to a single documented call, so on an unusual Type setup it may decline
  to add layers and warn instead of silently losing text.
- Aspect ratio is detected from the sequence name first (`_16x9_`, `9x16`, …),
  falling back to the width/height ratio. Sequences whose names carry no aspect
  token and whose ratio isn't one of 16×9 / 9×16 / 1×1 / 4×5 may be mislabelled —
  which matters because Auto Connection groups by aspect. Name your sequences with
  an aspect token and this never comes up.

## Tests

Pure helper logic (timecode, registry renumber/swap, text grouping, layer
math) is covered by off-box tests that need neither Flame nor PySide6:

```
python3 tests/test_graphic_sync.py
```

## Credits

Written by **Jeff Kyle**. Built with Claude (Anthropic).

## License

Provided as-is, without warranty of any kind. Free to use and modify.
