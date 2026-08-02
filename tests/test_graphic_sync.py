#!/usr/bin/env python3
"""Off-box tests for graphic_sync.py's pure helpers.

graphic_sync.py imports `flame`, which only exists inside Flame, so this file
ast-extracts the functions under test from the source and execs them into a
plain namespace -- no Flame, no PySide6, no restart loop.

Run:   python3 test_graphic_sync.py

This file lives in the dev folder, NOT in Flame's hook path. It finds
graphic_sync.py beside itself or in the sibling deployed `gfx-sync/` folder.
"""

import ast
import json
import logging
import os
import re
import sys
import tempfile


def _find_src():
    """Locate graphic_sync.py. Handles the repo layout (test in tests/, tool in
    the parent), the test sitting beside the tool, and the author's dev folder
    (kept OUTSIDE Flame's recursively-scanned python/ root)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "graphic_sync.py"),            # side by side
                 os.path.join(here, "..", "graphic_sync.py"),      # repo: tests/
                 os.path.join(here, "..", "gfx-sync", "graphic_sync.py"),
                 os.path.join(here, "..", "python", "gfx-sync", "graphic_sync.py")):
        if os.path.exists(cand):
            return os.path.abspath(cand)
    raise SystemExit("graphic_sync.py not found beside the test, in the parent "
                     "folder, in ../gfx-sync/, or in ../python/gfx-sync/")


SRC = _find_src()

WANTED = {
    # constants
    "LAYER_SEP", "LAYER_ADD_METHODS",
    # pure helpers
    "text_to_layers", "layers_to_text", "attr_text", "_get",
    "_frames", "_fps", "_frames_to_tc", "_native_tc", "_tc",
    "_clean_name", "_safe_name", "_seg_name",
    # type-layer ops
    "get_type_fx", "_add_layer", "push_text", "_in_sync",
    # connections
    "_seg_uid", "_clean_name", "_ancestor", "connection_groups",
    "auto_connection_groups",
    # inventory row model + grouped ordering
    "inv_row_models", "longest_sequence_name", "group_reference",
    # registry renumber / swap
    "renumber_registry",
    # scope: sequences-reel detection
    "_is_sequences_reel", "_get",
    # connection source/master designation
    "resolve_group_source",
    # assign = tag only
    "assign_graphic", "set_graphic_tag", "read_tag", "instance_tag", "_key", "TAG_RE",
    # registry safety
    "_atomic_write_json", "load_registry", "save_registry",
}


def extract_namespace():
    tree = ast.parse(open(SRC).read())
    quiet = logging.getLogger("test_graphic_sync")
    quiet.addHandler(logging.NullHandler())
    quiet.propagate = False
    ns = {"re": re, "ast": ast, "os": os, "json": json, "log": quiet}
    for node in tree.body:
        take = (isinstance(node, ast.FunctionDef) and node.name in WANTED) or (
            isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in WANTED for t in node.targets))
        if take:
            exec(compile(ast.Module([node], []), SRC, "exec"), ns)
    missing = WANTED - set(ns)
    if missing:
        raise SystemExit("extraction failed, missing: %s" % ", ".join(sorted(missing)))
    return ns


G = extract_namespace()
FAILS = []


def check(label, got, want):
    if got != want:
        FAILS.append("%s: got %r, want %r" % (label, got, want))


# ------------------------------------------------------------------ fakes

class Layer:
    def __init__(self, text=""):
        self.text = text


class PyTypeFX:                      # name matters: get_type_fx checks it
    def __init__(self, texts, can_grow=True, grow_method="add_layer"):
        self.layers = [Layer(t) for t in texts]
        self._can_grow = can_grow
        setattr(self, grow_method, self._grow)

    def _grow(self):
        if not self._can_grow:
            raise RuntimeError("not supported")
        self.layers.append(Layer(""))


class LyingTFX:                      # add method "succeeds" but never grows
    def __init__(self):
        self.layers = [Layer("x")]

    def add_layer(self):
        return True


class Seg:
    def __init__(self, tfx, name="'legal_gap'"):
        self.effects = [tfx]
        self.name = name


# ------------------------------------------------------------------ tests

def test_timecode():
    f2tc = G["_frames_to_tc"]
    check("tc 0", f2tc(0, 24), "00:00:00:00")
    check("tc 24", f2tc(24, 24), "00:00:01:00")
    check("tc 36", f2tc(36, 24), "00:00:01:12")
    check("tc 1hr", f2tc(3600 * 24, 24), "01:00:00:00")
    check("tc neg", f2tc(-25, 24), "-00:00:01:01")
    check("tc 23.976 rounds", f2tc(24, 23.976), "00:00:01:00")
    check("tc 30", f2tc(90061 * 30 + 15, 30.0), "25:01:01:15")
    check("tc None", f2tc(None, 24), "")

    class SeqFR:
        def __init__(self, fr):
            self.frame_rate = fr
    check("fps float", G["_fps"](SeqFR(23.976)), 23.976)
    check("fps string", G["_fps"](SeqFR("23.976 fps")), 23.976)
    check("fps int-string", G["_fps"](SeqFR("30")), 30.0)
    check("fps default", G["_fps"](object()), 24.0)

    class T:
        def __init__(self, tc=None, s=""):
            if tc is not None:
                self.timecode = tc
            self._s = s

        def __str__(self):
            return self._s
    check("native attr", G["_native_tc"](T(tc="01:00:00:12")), "01:00:00:12")
    check("native str", G["_native_tc"](T(s="'00:59:58:00'")), "00:59:58:00")
    check("native frames-str", G["_native_tc"](T(s="1440")), None)
    check("native None", G["_native_tc"](None), None)


def test_layer_text_roundtrip():
    t = "LINE ONE\nstill line one\n---\nLINE TWO\n---\nLINE THREE"
    ls = G["text_to_layers"](t)
    check("split", ls, ["LINE ONE\nstill line one", "LINE TWO", "LINE THREE"])
    check("roundtrip", G["text_to_layers"](G["layers_to_text"](ls)), ls)
    check("trailing blanks trimmed", G["text_to_layers"]("A\n---\n\n"), ["A"])
    check("empty", G["text_to_layers"](""), [])


def test_add_layer_guard():
    add = G["_add_layer"]
    tfx = PyTypeFX(["a"])
    check("grows", add(tfx), True)
    check("grew by one", len(tfx.layers), 2)
    tfx = PyTypeFX(["a"], grow_method="append_layer")     # later candidate
    check("later candidate", add(tfx), True)
    tfx = PyTypeFX(["a"], can_grow=False)
    check("raise -> False", add(tfx), False)
    check("raise -> no mutation", len(tfx.layers), 1)
    check("lying method -> False", add(LyingTFX()), False)


def test_push_text():
    push = G["push_text"]

    # creation: 1 existing layer, 3 lines
    tfx = PyTypeFX(["OLD"])
    warns = []
    ch = push(Seg(tfx), ["A", "B", "C"], dry_run=False, warnings=warns)
    check("create texts", [l.text for l in tfx.layers], ["A", "B", "C"])
    check("create changes", len(ch), 3)
    check("create no warns", warns, [])

    # shortfall: cannot grow -> writes what exists, warns
    tfx = PyTypeFX(["OLD"], can_grow=False)
    warns = []
    push(Seg(tfx), ["A", "B", "C"], dry_run=False, warnings=warns)
    check("short texts", [l.text for l in tfx.layers], ["A"])
    check("short warn count", len(warns), 1)
    check("short warn msg", "has 1 layer(s), GFX needs 3" in warns[0], True)

    # shrink: extras are blanked, not left stale
    tfx = PyTypeFX(["A", "B", "STALE LEGAL LINE"])
    ch = push(Seg(tfx), ["A", "B"], dry_run=False)
    check("shrink blanks extra", [l.text for l in tfx.layers], ["A", "B", ""])
    check("shrink change recorded", ch, [(ch[0][0], 2, "STALE LEGAL LINE", "")])

    # dry-run: no mutation; pending creates AND pending blanks counted
    tfx = PyTypeFX(["A", "STALE"])
    ch = push(Seg(tfx), ["A"], dry_run=True)
    check("dry no mutation", [l.text for l in tfx.layers], ["A", "STALE"])
    check("dry pending blank", len(ch), 1)
    tfx = PyTypeFX(["A"])
    ch = push(Seg(tfx), ["A", "B"], dry_run=True)
    check("dry pending create", [(c[1], c[3]) for c in ch], [(1, "B")])

    # fully in sync -> no changes
    tfx = PyTypeFX(["A", "B"])
    check("in-sync noop", push(Seg(tfx), ["A", "B"], dry_run=True), [])


def test_in_sync():
    insync = G["_in_sync"]
    check("match", insync(Seg(PyTypeFX(["A", "B"])), ["A", "B"]), True)
    check("mismatch", insync(Seg(PyTypeFX(["A", "X"])), ["A", "B"]), False)
    check("missing layer", insync(Seg(PyTypeFX(["A"])), ["A", "B"]), False)
    check("stale extra", insync(Seg(PyTypeFX(["A", "B", "OLD"])), ["A", "B"]), False)
    check("blank extra ok", insync(Seg(PyTypeFX(["A", "B", ""])), ["A", "B"]), True)


def test_registry_safety():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "reg", "graphic_registry.json")
        G["registry_path"] = lambda: path
        G["_legacy_registry_candidates"] = lambda: []

        # round trip via atomic write
        reg = {"01": {"lines": ["LEGAL LINE", "SECOND"]}}
        check("save ok", G["save_registry"](reg), True)
        check("no tmp left", os.path.exists(path + ".tmp"), False)
        check("load roundtrip", G["load_registry"](), reg)

        # corruption: load returns {} but QUARANTINES instead of leaving the
        # bad file where the next save would clobber it
        with open(path, "w") as f:
            f.write('{"01": {"lines": ["TRUNCATED')
        check("corrupt -> empty", G["load_registry"](), {})
        check("corrupt quarantined", os.path.exists(path + ".corrupt"), True)
        check("corrupt content kept",
              "TRUNCATED" in open(path + ".corrupt").read(), True)
        check("original gone", os.path.exists(path), False)

        # a save after quarantine starts fresh without touching the backup
        check("save after corrupt", G["save_registry"]({"02": {"lines": ["X"]}}), True)
        check("backup intact", os.path.exists(path + ".corrupt"), True)


class CSeg:
    """Fake segment for connection grouping: identity via uid, plus a
    connected_segments() that returns its wired peers."""
    def __init__(self, uid):
        self.uid = uid
        self._peers = []

    def connected_segments(self, scoping=None):
        return self._peers


def _wire(*segs):
    """Mutually connect fake segments (each lists all the others)."""
    for s in segs:
        s._peers = [o for o in segs if o is not s]


def _inv_row(seg, aspect, num):
    return {"seg": seg, "aspect": aspect, "num": num, "seq": "seq_" + seg.uid}


def test_auto_connection_groups():
    acg = G["auto_connection_groups"]

    # two unconnected like-aspect/like-GFX pairs -> 2 groups
    a1, a2 = CSeg("a1"), CSeg("a2")      # 16x9 GFX01
    b1, b2 = CSeg("b1"), CSeg("b2")      # 16x9 GFX02
    # an already-connected 9x16 GFX01 pair -> skipped as already wired
    c1, c2 = CSeg("c1"), CSeg("c2")
    _wire(c1, c2)
    # a lone 9x16 GFX02 -> single, skipped
    d1 = CSeg("d1")
    # an unassigned segment -> counted, skipped
    u1 = CSeg("u1")

    inv = [
        _inv_row(a1, "16x9", "01"), _inv_row(a2, "16x9", "01"),
        _inv_row(b1, "16x9", "02"), _inv_row(b2, "16x9", "02"),
        _inv_row(c1, "9x16", "01"), _inv_row(c2, "9x16", "01"),
        _inv_row(d1, "9x16", "02"),
        _inv_row(u1, "16x9", None),
    ]
    groups, already, unassigned = acg(inv)
    check("auto group count", len(groups), 2)
    check("auto already-connected skipped", already, 1)
    check("auto unassigned counted", unassigned, 1)
    # each proposed group has exactly its 2 members
    sizes = sorted(len(g) for g in groups)
    check("auto group sizes", sizes, [2, 2])
    # membership maps to the right buckets (by aspect+num of first member)
    keys = sorted((inv[g[0]]["aspect"], inv[g[0]]["num"]) for g in groups)
    check("auto group keys", keys, [("16x9", "01"), ("16x9", "02")])

    # idempotent: once those four are wired, nothing new to propose
    _wire(a1, a2)
    _wire(b1, b2)
    groups2, already2, _ = acg(inv)
    check("auto idempotent groups", len(groups2), 0)
    check("auto idempotent already", already2, 3)   # the two new + the c-pair

    # partial cluster (one member already connected to an outsider) still groups
    e1, e2 = CSeg("e1"), CSeg("e2")
    outsider = CSeg("x1")
    _wire(e1, outsider)                  # e1 wired, but not to e2
    inv3 = [_inv_row(e1, "1x1", "01"), _inv_row(e2, "1x1", "01")]
    groups3, _a, _u = acg(inv3)
    check("auto partial groups", len(groups3), 1)


def test_inv_row_models():
    rm = G["inv_row_models"]
    inv = [
        {"text": "LEGAL A", "num": "01"},
        {"text": "LEGAL A", "num": None},
        {"text": "LEGAL B", "num": None},
        {"text": "LEGAL A", "num": None},
        {"text": "", "num": None},          # blank text -> never folded
        {"text": "", "num": "02"},
    ]
    # plain: one row per entry
    check("plain rows", rm(inv), [[0], [1], [2], [3], [4], [5]])

    # hide assigned: drop num-bearing rows (indices 0 and 5)
    check("hide assigned", rm(inv, hide_assigned=True),
          [[1], [2], [3], [4]])

    # grouped: identical non-blank text folds; blanks stay standalone;
    # first-appearance order preserved
    check("grouped", rm(inv, group_text=True),
          [[0, 1, 3], [2], [4], [5]])

    # grouped + hide assigned: index 0 (assigned) and 5 (assigned) drop first,
    # so the LEGAL A group is just 1 and 3
    check("grouped + hide", rm(inv, hide_assigned=True, group_text=True),
          [[1, 3], [2], [4]])

    check("empty inv", rm([], group_text=True), [])


class Tags:
    """Fake PyAttribute-ish tags list with get_value/set_value."""
    def __init__(self, vals=()):
        self._v = list(vals)

    def get_value(self):
        return list(self._v)

    def set_value(self, v):
        self._v = list(v)


class TagSeg:
    def __init__(self, tfx, tags=()):
        self.effects = [tfx]
        self.tags = Tags(tags)
        self.name = "'seg'"


def test_assign_tags_only():
    """Assign must LABEL the segment and never touch its text."""
    tfx = PyTypeFX(["ORIGINAL LEGAL TEXT"])
    seg = TagSeg(tfx)
    G["assign_graphic"](seg, 1)
    check("assign sets tag", G["read_tag"](seg), "graphic01")
    check("assign leaves text alone", [l.text for l in tfx.layers], ["ORIGINAL LEGAL TEXT"])

    # re-assigning replaces the graphic tag, still writes no text
    G["assign_graphic"](seg, 2)
    check("reassign retags", G["read_tag"](seg), "graphic02")
    check("reassign still no text write", [l.text for l in tfx.layers], ["ORIGINAL LEGAL TEXT"])

    # dry_run does nothing
    seg2 = TagSeg(PyTypeFX(["X"]))
    G["assign_graphic"](seg2, 5, dry_run=True)
    check("assign dry_run no tag", G["read_tag"](seg2), None)


def test_group_ordering():
    lsn = G["longest_sequence_name"]
    gr = G["group_reference"]

    inv = [
        {"seq": "A_16x9", "seq_dur_f": 1440, "in_f": 100},
        {"seq": "B_9x16", "seq_dur_f": 720, "in_f": 50},
        {"seq": "C_1x1", "seq_dur_f": None, "in_f": 10},
    ]
    check("longest sequence", lsn(inv), "A_16x9")
    check("longest ignores unknown durations", lsn([{"seq": "X", "seq_dur_f": None}]), None)
    check("longest empty", lsn([]), None)

    members = [{"seq": "B_9x16", "in_f": 50}, {"seq": "A_16x9", "in_f": 200}]
    check("ref prefers longest-seq member", gr(members, "A_16x9")["seq"], "A_16x9")
    check("ref fallback earliest when absent", gr(members, "Z_none")["in_f"], 50)
    check("ref no-longest -> earliest", gr(members, None)["in_f"], 50)
    check("ref None in_f sorts last",
          gr([{"seq": "A", "in_f": None}, {"seq": "B", "in_f": 5}], None)["in_f"], 5)


def test_resolve_group_source():
    rgs = G["resolve_group_source"]
    uids = ["a", "b", "c", "d"]

    # none marked -> auto-pick (None, no error)
    idx, err = rgs(uids, set())
    check("none marked -> auto", (idx, err), (None, None))

    # exactly one marked -> its index
    idx, err = rgs(uids, {"c"})
    check("one marked -> index", (idx, err), (2, None))

    # marked uid not in this group -> auto-pick (it's another group's source)
    idx, err = rgs(uids, {"z"})
    check("foreign mark ignored", (idx, err), (None, None))

    # two marked in the group -> error, no index
    idx, err = rgs(uids, {"a", "c"})
    check("two marked -> no index", idx, None)
    check("two marked -> error", "mark only one" in (err or ""), True)


def test_is_sequences_reel():
    isr = G["_is_sequences_reel"]

    class Reel:
        def __init__(self, t):
            self.type = t

    check("Sequences", isr(Reel("Sequences")), True)
    check("Sequences Reel label", isr(Reel("Sequences Reel")), True)
    check("case-insensitive", isr(Reel("SEQUENCE")), True)
    check("regular Reel excluded", isr(Reel("Reel")), False)
    check("schematic excluded", isr(Reel("Schematic Reel")), False)
    check("None type -> include (fail open)", isr(Reel(None)), True)

    class NoType:
        pass
    check("no .type -> include (fail open)", isr(NoType()), True)


def test_renumber_registry():
    rr = G["renumber_registry"]
    base = {"01": {"lines": ["A"]}, "03": {"lines": ["C"]}, "05": {"lines": ["E"]}}

    # move to an EMPTY slot -> simple rename, only old remaps
    out, retag, err = rr(base, 3, 4, "overwrite")
    check("move err", err, None)
    check("move reg", out, {"01": {"lines": ["A"]}, "04": {"lines": ["C"]}, "05": {"lines": ["E"]}})
    check("move retag", retag, {"03": "04"})
    check("move no mutate base", "03" in base and "04" not in base, True)

    # overwrite an OCCUPIED slot -> target's text is lost, only old remaps
    out, retag, err = rr(base, 1, 5, "overwrite")
    check("overwrite reg", out, {"05": {"lines": ["A"]}, "03": {"lines": ["C"]}})
    check("overwrite lost E", "01" not in out and out["05"]["lines"], ["A"])
    check("overwrite retag", retag, {"01": "05"})

    # swap an OCCUPIED slot -> both kept, both remap
    out, retag, err = rr(base, 1, 5, "swap")
    check("swap err", err, None)
    check("swap keeps both", (out["05"]["lines"], out["01"]["lines"]), (["A"], ["E"]))
    check("swap retag both", retag, {"01": "05", "05": "01"})

    # swap onto an EMPTY slot behaves like a move (nothing to swap with)
    out, retag, err = rr(base, 3, 9, "swap")
    check("swap-empty reg", out.get("09", {}).get("lines"), ["C"])
    check("swap-empty no 03", "03" not in out, True)
    check("swap-empty retag", retag, {"03": "09"})

    # missing source -> error, reg untouched
    out, retag, err = rr(base, 7, 8, "overwrite")
    check("missing err", "not in the registry" in (err or ""), True)
    check("missing retag", retag, {})


def main():
    tests = [test_timecode, test_layer_text_roundtrip, test_add_layer_guard,
             test_push_text, test_in_sync, test_registry_safety,
             test_auto_connection_groups, test_inv_row_models,
             test_renumber_registry, test_assign_tags_only,
             test_is_sequences_reel, test_group_ordering,
             test_resolve_group_source]
    for t in tests:
        t()
    if FAILS:
        print("FAIL (%d)" % len(FAILS))
        for f in FAILS:
            print("  " + f)
        sys.exit(1)
    print("OK — %d test groups passed" % len(tests))


if __name__ == "__main__":
    main()
