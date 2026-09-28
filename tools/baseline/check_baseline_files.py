#!/usr/bin/env python3
"""Relocation-aware accounting of the files sealed by the historical baseline tag.

    .venv/bin/python tools/baseline/check_baseline_files.py              # exit 1 on any unaccounted change
    .venv/bin/python tools/baseline/check_baseline_files.py --self-test  # the accounting catches mutations

The tag ``baseline-classroom-oracle1-2026-09-25`` records the Classroom-Oracle-1 baseline by
path.  Repository Transition 1 relocated some of those paths with an explicit move map
(docs/repository/repository-transition-1-moves.json), so the historical baseline's byte/path
identity is no longer the current repository layout.  Every path tracked at the tag must be
accounted for by exactly one rule:

  unchanged  same path, byte-identical to the tag blob;
  pure       relocated by the move map, byte-identical to the tag blob at the new path;
  repaired   relocated by the move map, equal at the new path to the tag blob with exactly
             the declared literal edits applied (each 'before' occurring once);
  replaced   declared replaced by the move map (README.md).

A relocated file's old path must be gone.  The tag must still name its original commit and
be an ancestor of HEAD.  Sealed scientific behavior is guarded separately, by the checkers
and the golden comparator.  Read-only: it reads git objects and working-tree files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
MOVE_MAP = REPO / "docs/repository/repository-transition-1-moves.json"
BASELINE_TAG = "baseline-classroom-oracle1-2026-09-25"
BASELINE_COMMIT = "a980e59dfc453c590190f842c47c4588bc99989d"
PREFIX = "[baseline-files]"


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True).stdout


def apply_edits(blob: bytes, edits: list[list[str]]) -> bytes | None:
    """The tag blob with every declared literal edit applied; None if an edit does not fit."""
    text = blob.decode("utf-8")
    for before, after in edits:
        if text.count(before) != 1:
            return None
        text = text.replace(before, after)
    return text.encode("utf-8")


def account(tag_files: dict[str, bytes], tree: dict[str, bytes | None], moves: dict[str, dict],
            replaced: set[str]) -> tuple[dict[str, int], list[str]]:
    """Classify every tag path; `tree` maps a path to its working-tree bytes, or None if absent."""
    counts = {"unchanged": 0, "pure": 0, "repaired": 0, "replaced": 0}
    failures: list[str] = []
    for path, blob in sorted(tag_files.items()):
        if path in replaced:
            counts["replaced"] += 1
            continue
        move = moves.get(path)
        if move is None:
            if tree.get(path) != blob:
                failures.append(f"{path}: not byte-identical at its baseline path and not declared moved or replaced")
            else:
                counts["unchanged"] += 1
            continue
        new, kind = move["new"], move["kind"]
        if tree.get(path) is not None:
            failures.append(f"{path}: relocated to {new} but the old path still exists")
        current = tree.get(new)
        if current is None:
            failures.append(f"{path}: relocated file {new} is missing")
            continue
        if kind == "pure":
            expected = blob
        elif kind == "repaired":
            expected = apply_edits(blob, move["edits"])
            if expected is None:
                failures.append(f"{path}: a declared edit does not occur exactly once in the tag blob")
                continue
        else:
            failures.append(f"{path}: move kind {kind!r} is not allowed for a baseline file")
            continue
        if current != expected:
            failures.append(f"{path}: {new} differs from the tag blob{' + declared edits' if kind == 'repaired' else ''}")
        else:
            counts[kind] += 1
    return counts, failures


def load() -> tuple[dict[str, bytes], dict[str, bytes | None], dict[str, dict], set[str], list[str]]:
    problems: list[str] = []
    spec = json.loads(MOVE_MAP.read_text(encoding="utf-8"))
    tag_commit = git("rev-parse", f"{BASELINE_TAG}^{{commit}}").decode().strip()
    if tag_commit != BASELINE_COMMIT or spec.get("baseline_commit") != BASELINE_COMMIT:
        problems.append(f"tag {BASELINE_TAG} resolves to {tag_commit}, expected {BASELINE_COMMIT} "
                        f"(move map records {spec.get('baseline_commit')})")
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE_TAG, "HEAD"], cwd=REPO).returncode:
        problems.append(f"{BASELINE_TAG} is not an ancestor of HEAD")
    tag_files = {}
    for entry in git("ls-tree", "-r", "-z", BASELINE_TAG).split(b"\0"):
        if entry:
            meta, path = entry.split(b"\t", 1)
            tag_files[path.decode()] = git("cat-file", "blob", meta.split()[2].decode())
    moves = {m["old"]: m for m in spec["moves"]}
    wanted = set(tag_files) | {m["new"] for m in spec["moves"] if m["old"] in tag_files}
    tree = {p: (REPO / p).read_bytes() if (REPO / p).is_file() else None for p in wanted}
    return tag_files, tree, moves, set(spec.get("replaced", {})), problems


def self_test() -> list[str]:
    """Each in-memory mutation of the real tag/tree/map must be caught; the real state must pass."""
    tag_files, tree, moves, replaced, problems = load()
    bad: list[str] = []
    counts, fails = account(tag_files, tree, moves, replaced)
    if fails or problems:
        bad.append("unmutated state already fails; fix that before trusting the self-test")
    base_moved = [p for p in sorted(moves) if p in tag_files]
    pure = next(p for p in base_moved if moves[p]["kind"] == "pure")
    rep = next(p for p in base_moved if moves[p]["kind"] == "repaired")
    same = next(p for p in sorted(tag_files) if p not in moves and p not in replaced and p.endswith(".py"))

    def flip(b: bytes) -> bytes:
        return b[:-1] + bytes([b[-1] ^ 1])

    def mutant(label, t=None, m=None, r=None):
        _, f = account(tag_files, t if t is not None else tree, m if m is not None else moves,
                       r if r is not None else replaced)
        if not f:
            bad.append(f"mutation not caught: {label}")

    mutant(f"byte flip in unchanged {same}", t={**tree, same: flip(tree[same])})
    mutant(f"byte flip in pure relocation {moves[pure]['new']}", t={**tree, moves[pure]["new"]: flip(tree[moves[pure]["new"]])})
    mutant(f"undeclared change in repaired relocation {moves[rep]['new']}",
           t={**tree, moves[rep]["new"]: tree[moves[rep]["new"]] + b"\n# unapproved\n"})
    mutant(f"old path {pure} reappears", t={**tree, pure: tag_files[pure]})
    mutant(f"relocated file {moves[pure]['new']} missing", t={**tree, moves[pure]["new"]: None})
    mutant(f"relocation {pure} removed from the move map", m={k: v for k, v in moves.items() if k != pure})
    mutant("README.md no longer declared replaced", r=set())
    wrong = {**moves, rep: {**moves[rep], "edits": moves[rep]["edits"] + [["no such text", "x"]]}}
    mutant(f"declared edit absent from the tag blob of {rep}", m=wrong)
    mutant(f"pure relocation {pure} declared 'active'", m={**moves, pure: {**moves[pure], "kind": "active"}})
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ns = ap.parse_args()
    if ns.self_test:
        bad = self_test()
        for b in bad:
            print(f"{PREFIX} self-test FAIL {b}")
        print(f"{PREFIX} self-test {'FAILED' if bad else 'PASS'} (9 mutations)")
        return 1 if bad else 0
    tag_files, tree, moves, replaced, problems = load()
    counts, failures = account(tag_files, tree, moves, replaced)
    for f in problems + failures:
        print(f"{PREFIX} FAIL {f}")
    print(f"{PREFIX} {len(tag_files)} files tracked at {BASELINE_TAG} ({BASELINE_COMMIT[:7]}): "
          + " ".join(f"{k}={v}" for k, v in counts.items()) + f" failed={len(problems) + len(failures)}")
    print(f"{PREFIX} historical baseline byte/path identity is not the current layout; "
          f"every baseline file is accounted for by the relocation rule above")
    return 1 if problems or failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
