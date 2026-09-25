#!/usr/bin/env python3
"""Read-only check of the Classroom scene payload against scenes/classroom/ASSET_MANIFEST.json.

    .venv/bin/python tools/check_classroom_assets.py            # exit 1 on a required failure
    .venv/bin/python tools/check_classroom_assets.py --self-test

Never generates, edits, copies or downloads an asset; it only reads bytes and sizes.
Exit is nonzero only when a REQUIRED golden-run asset is absent, has the wrong size or
the wrong sha256, or when classroom_eye.blend is not the accepted digest.  Optional
files (generator source, unreferenced payload), missing legacy references, and files
present but not in the manifest are reported separately and never fail the check.

Standard library only; runs in either interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "scenes/classroom/ASSET_MANIFEST.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def evaluate(manifest: dict, stat: Callable[[str], int | None], digest: Callable[[str], str],
             listing: list[str]) -> dict:
    """Pure evaluation.  stat(path) -> size or None if absent; digest(path) -> sha256."""
    required_fail: list[str] = []
    optional_issue: list[str] = []
    ok_required = ok_optional = 0
    for e in manifest["files"]:
        size = stat(e["path"])
        req = bool(e["required"])
        if size is None:
            (required_fail if req else optional_issue).append(f"ABSENT {e['path']} ({e['role']})")
            continue
        if size != int(e["bytes"]):
            (required_fail if req else optional_issue).append(f"SIZE {e['path']}: {size} != {e['bytes']}")
            continue
        got = digest(e["path"])
        if got != e["sha256"]:
            (required_fail if req else optional_issue).append(f"SHA256 {e['path']}: {got} != {e['sha256']}")
            continue
        if req:
            ok_required += 1
        else:
            ok_optional += 1
    eye = manifest["golden_run_input"].split("scenes/classroom/", 1)[-1]
    eye_entry = next((e for e in manifest["files"] if e["path"] == eye), None)
    if eye_entry is None or not eye_entry["required"] or eye_entry["sha256"] != manifest["accepted_classroom_eye_blend_sha256"]:
        required_fail.append("MANIFEST golden_run_input is not a required entry carrying the accepted digest")
    listed = {e["path"] for e in manifest["files"]}
    unlisted = sorted(p for p in listing if p not in listed and p != "ASSET_MANIFEST.json")
    missing_refs = [m["path"] for m in manifest.get("missing_legacy_reference", [])]
    missing_refs_present = [p for p in missing_refs if stat(p) is not None]
    return {
        "required_ok": ok_required, "optional_ok": ok_optional,
        "required_failures": required_fail, "optional_issues": optional_issue,
        "unlisted_files": unlisted, "missing_legacy_reference": missing_refs,
        "missing_legacy_reference_now_present": missing_refs_present,
        "nominal_unused": [m["path"] for m in manifest.get("nominal_unused", [])],
    }


def self_test() -> list[str]:
    """In-memory negatives: every failure class must be detected; nothing touches disk."""
    fails: list[str] = []
    good = {
        "golden_run_input": "scenes/classroom/eye.blend", "accepted_classroom_eye_blend_sha256": "aa",
        "files": [
            {"path": "eye.blend", "bytes": 3, "sha256": "aa", "required": True, "role": "direct_input"},
            {"path": "lib.blend", "bytes": 2, "sha256": "bb", "required": True, "role": "linked_library"},
            {"path": "readme.txt", "bytes": 1, "sha256": "cc", "required": False, "role": "unreferenced_payload"},
        ],
        "missing_legacy_reference": [{"path": "gone.png"}], "nominal_unused": [],
    }
    disk = {"eye.blend": (3, "aa"), "lib.blend": (2, "bb"), "readme.txt": (1, "cc")}

    def run(d, m=good):
        return evaluate(m, lambda p: d[p][0] if p in d else None, lambda p: d[p][1], sorted(d))

    r = run(disk)
    if r["required_failures"] or r["required_ok"] != 2 or r["optional_ok"] != 1:
        fails.append(f"clean payload not accepted: {r}")
    r = run({k: v for k, v in disk.items() if k != "lib.blend"})
    if not any(x.startswith("ABSENT lib.blend") for x in r["required_failures"]):
        fails.append("absent required asset not detected")
    r = run({**disk, "lib.blend": (2, "xx")})
    if not any(x.startswith("SHA256 lib.blend") for x in r["required_failures"]):
        fails.append("wrong required digest not detected")
    r = run({**disk, "eye.blend": (4, "aa")})
    if not any(x.startswith("SIZE eye.blend") for x in r["required_failures"]):
        fails.append("wrong required size not detected")
    r = run({k: v for k, v in disk.items() if k != "readme.txt"})
    if r["required_failures"] or not r["optional_issues"]:
        fails.append("absent optional file must be reported but must not fail")
    r = run({**disk, "extra.png": (1, "dd")})
    if r["required_failures"] or r["unlisted_files"] != ["extra.png"]:
        fails.append("unlisted file must be reported but must not fail")
    bad = json.loads(json.dumps(good)); bad["accepted_classroom_eye_blend_sha256"] = "zz"
    if not run(disk, bad)["required_failures"]:
        fails.append("golden input not carrying the accepted digest was not detected")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        bad = self_test()
        for b in bad:
            print("[classroom-assets] SELF-TEST FAIL", b)
        print("[classroom-assets] self-test", "FAILED" if bad else "PASS")
        return 1 if bad else 0

    if not args.manifest.exists():
        print(f"[classroom-assets] FAIL manifest absent: {args.manifest}")
        return 1
    manifest = json.loads(args.manifest.read_text())
    root = args.manifest.parent

    def stat(p: str) -> int | None:
        q = root / p
        return q.stat().st_size if q.is_file() else None

    listing = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()) if root.is_dir() else []
    r = evaluate(manifest, stat, lambda p: sha256_file(root / p), listing)
    for x in r["required_failures"]:
        print("[classroom-assets] FAIL required", x)
    for x in r["optional_issues"]:
        print("[classroom-assets] INFO optional", x)
    for x in r["unlisted_files"]:
        print("[classroom-assets] INFO unlisted file", x)
    for x in r["missing_legacy_reference"]:
        print("[classroom-assets] INFO missing_legacy_reference", x)
    for x in r["nominal_unused"]:
        print("[classroom-assets] INFO nominal_unused", x)
    n_req = sum(1 for e in manifest["files"] if e["required"])
    n_opt = len(manifest["files"]) - n_req
    print(f"[classroom-assets] SUMMARY required_ok={r['required_ok']}/{n_req} optional_ok={r['optional_ok']}/{n_opt} "
          f"required_failures={len(r['required_failures'])} missing_legacy_reference={len(r['missing_legacy_reference'])} "
          f"unlisted={len(r['unlisted_files'])} eye_sha256={manifest['accepted_classroom_eye_blend_sha256']}")
    return 1 if r["required_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
