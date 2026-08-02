# Graphic Sync — How to use it

A Flame 2027 tool for syncing the text of Type (Timeline FX) graphics across many
sequences and aspect ratios, and for sharing their layout via segment
connections.

---

## The idea in 20 seconds

- The **Registry** is your master list of graphic text — `GFX01`, `GFX02`, … each
  holds the words for one graphic.
- You **tag** timeline graphics to a GFX number.
- **Sync** pushes the registry text out to every tagged graphic at once.
- Separately, you **connect** matching graphics across aspects so they share
  layout (position / scale / format).

Text and layout are managed independently — change one without disturbing the
other.

---

## Install

1. Copy the single file to its own folder on Flame's shared Python path:
   ```
   /opt/Autodesk/shared/python/graphic_sync/graphic_sync.py
   ```
2. **Fully restart Flame** (not "Reload Python Hooks").
3. Open it from any of:
   - Right-click a timeline segment → **GFX Sync → GFX Sync…**
   - Right-click in the Media Panel → **GFX Sync → GFX Sync…**
   - Main menu → **GFX Sync → Open Manager…**

---

## Step 1 — Settings (do this once per project)

On the **Settings** tab:

- **Registry folder** — where the JSON lives (defaults to the project setups
  folder; leave blank for the default).
- **Default scope** — how much of the project to look at: Selected, Current
  Sequence, Current Reel, Current Reel Group, or All Sequences Reels (the reel
  group's sequences reels only — skips regular/scratch reels). The "Current …"
  scopes follow what's open in Flame's **Timeline** tab; the tool switches you
  there when it opens so they resolve correctly.
- **Treat as GFX** — what counts as a target. Default "Gap segments with Type"
  matches the usual legal/disclaimer gap graphics; "Any segment with Type" is
  broader.
- **Segment name filter / Track name prefix** — optional, to narrow things down.
- **Default Grouped Text** — start the Segments tab with Grouped Text already on.
- **Default Segments sort** — the column the Segments tab sorts by on open
  (ascending); pick **In** to land on appearance order automatically.
- Click **Save Settings**.

---

## Step 2 — Build your registry (Registry tab)

Two ways to get text into the registry:

**A. Type it in**
1. Set the **GFX #**.
2. Type the text. Use a line containing only `---` to split the graphic into
   multiple Type layers.
3. Click **Save / Add**.

**B. Capture it from a segment** — see Step 3 (Add to Registry).

To renumber: select a saved GFX → **Renumber…**. If the target number is already
taken you'll be asked to **Swap** (exchange the two, both kept), **Overwrite**
(replace it), or **Cancel**.

To start over: **Remove All** clears every entry from this project's registry
(segments keep their tags; only the definitions go).

---

## Step 3 — Assign & sync (Segments tab)

1. Set the **Scope** (top of the window). The list auto-scans — there's no Scan
   button — and the blue summary beside the Scope dropdown shows what it found.
2. You'll see every matching graphic: sequence, name, In/Dur, text, GFX #, sync
   status, and how many connections it has. Drag the header dividers to resize
   columns.
3. **Assign:** select one or more rows → pick a number from **Assign to** (it
   shows a text preview so you know which is which) → **Assign**.
   - Assigning only **labels** the segment — it does NOT change the text on your
     timeline. If the segment's current text differs from the registry it shows
     **OUT OF DATE** until you Sync (see step 4). Nothing is written without a
     preview.
   - Turn on **Grouped Text** to fold every graphic with identical text into a
     single row — select it once and assign (or Add to Registry) them all at once.
     Sorting a grouped list by **In** orders the groups by appearance in the
     longest sequence.
   - Turn on **Hide Assigned** to see only what still needs a number.
   - Use **Add to Registry** to capture a selected graphic's text into the
     registry (defaults to the next free slot; if the segment is already
     assigned it asks whether to add new or update the existing one). When you
     add a **grouped** row, all its segments are assigned to that new number
     automatically — capture and assign in one step.
   - With Grouped Text on, **Add All to Registry** appears: it adds *every*
     grouped row at once, in the current table order, each to the next free GFX
     number, assigning its segments. Tip: sort by **In** first, and you get
     GFX01, GFX02, … in order of appearance.
4. To push updated text out: go to the **Registry** tab, edit the text, and click
   **Sync Text → Scope**. It previews what will change, then updates every tagged
   segment in scope.

Columns can be shown/hidden via **Columns ▾**, and In/Dur can switch between
**Timecode** and **Frames** via the **Units** dropdown.

---

## Step 4 — Connect layout across aspects (Connections tab)

1. The fast path: **Auto Connection** — it queues a connection group for every
   set of like-aspect, like-GFX graphics across your scope (already-connected
   sets are skipped). Review the queued **Q** rows, then **Execute Queue**.
2. The manual path: select the matching rows yourself → **Multi Segment
   Connection** → choose **Yes** (run now), **Queue** (stack it), or **No**.
3. Other tools here:
   - **Break Selected** — remove a connection.
   - **Set as Source** — mark a segment (★) as its group's master so *its* layout
     is the one that propagates. One per group; none = auto-pick.
   - **Sync Connected Segments** — push the selected segment's layout out to
     everything connected to it.
   - **Clear Queue** — drop everything you've stacked without running it.

Rows packed together with no gap are connected to each other; a blank row
separates one group from the next.

After a connection run, every affected sequence's playhead is parked at the
first frame and you're returned to the sequence you started on (rather than the
last one processed).

---

## Tips

- Connections share **layout**; the registry + Sync share **text**. They're
  independent on purpose.
- Everything is undoable in Flame.
- A full Flame restart is only needed when you install/update the script itself —
  not for day-to-day use.
