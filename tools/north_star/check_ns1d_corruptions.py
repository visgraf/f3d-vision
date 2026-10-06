"""North Star-1d corruption / mutation suite (contract section 21).

Run from ``check_ns1d.py --corruptions`` after a passing baseline.  A temporary mirror of RUN and VIS is built (small
files copied; large files symlinked and unlinked before any write).  An unmodified-mirror null probe must pass every
check.  Each corruption then mutates a fresh mirror (an altered record, a regenerated wrong artifact, a figure) or the
code under check in-process, regenerates the mirror's manifest and replay freeze, and runs the checks it names; each
named check must fail.  Corruptions that do not apply to the executed trace are recorded NOT APPLICABLE, never counted as
caught.  RUN and VIS are hashed before and after.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ns1d as C  # noqa: E402

BIG = 1 << 20


def tree_hashes(root: Path) -> dict:
    return {str(p.relative_to(root)): C.sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def mirror(run: Path, vis: Path, td: Path) -> tuple[Path, Path]:
    m, mv = td / "run", td / "vis"
    for src, dst in ((run, m), (vis, mv)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.stat().st_size > BIG and src == run:
                os.symlink(p.resolve(), q)
            else:
                shutil.copyfile(p, q)
    return m, mv


def unlinked(p: Path) -> Path:
    if p.is_symlink():
        p.unlink()
    return p


def jl(m: Path, rel: str):
    return json.loads((m / rel).read_text())


def js(m: Path, rel: str, d) -> None:
    (m / rel).parent.mkdir(parents=True, exist_ok=True)
    unlinked(m / rel).write_text(json.dumps(d, indent=1, sort_keys=True, allow_nan=False) + "\n")


def nl(m: Path, rel: str) -> dict:
    with np.load(m / rel, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def ns(m: Path, rel: str, d: dict) -> None:
    np.savez_compressed(unlinked(m / rel), **d)


def edit(m: Path, rel: str, fn) -> None:
    d = jl(m, rel)
    fn(d)
    js(m, rel, d)


def refreeze(m: Path) -> None:
    """Regenerate the mirror's replay freeze and manifest (a corruption that also re-signs its records)."""
    fz = jl(m, "freeze/replay-freeze.json")
    files = sorted(str(p.relative_to(m)) for p in (m / "replay").rglob("*") if p.is_file()
                   and p.name != "replay-opened-files.json")
    fz["files"] = {f: C.sha256(m / f) for f in files}
    js(m, "freeze/replay-freeze.json", fz)
    man = jl(m, "manifest.json")
    files = sorted(str(p.relative_to(m)) for p in m.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    man["files"] = {f: C.sha256(m / f) for f in files}
    js(m, "manifest.json", man)


def consumed(m: Path) -> list[int]:
    return [int(e) for e in jl(m, "replay/replay.json")["consumed_events"]]


def states_from(m: Path, e0: int) -> list[str]:
    return [f"replay/state-after-event-{e:02d}.json" for e in consumed(m) if e >= e0]


def cross_event(m: Path) -> int | None:
    """The first consumed event that adds coherent cross-target samples."""
    for e in consumed(m):
        if jl(m, f"replay/events/event-{e:02d}/event.json")["coherent_cross_target_additions"]:
            return e
    return None


def cross_id(m: Path) -> int | None:
    e = cross_event(m)
    if e is None:
        return None
    return int(sorted(jl(m, f"replay/events/event-{e:02d}/event.json")["coherent_cross_target_additions"])[0])


def patch_rel(e: int) -> str:
    return f"replay/events/event-{e:02d}/memory-patch.npz"


def rows_edit(m: Path, e0: int, mode: str, i: int, fn) -> None:
    for rel in states_from(m, e0):
        def f(d):
            for r in d["tables"][mode]:
                if int(r["temporary_entity_id"]) == i:
                    fn(r)
        edit(m, rel, f)


def ctx_edit(m: Path, e0: int, i: int, fn) -> None:
    for rel in states_from(m, e0):
        edit(m, rel, lambda d: fn(d["contexts"][str(i)]))


# ------------------------------------------------------------------ MEMORY ROUTING
def route_by_target(m):
    e = cross_event(m)
    p = nl(m, patch_rel(e))
    t = jl(m, f"replay/events/event-{e:02d}/event.json")["active_target"]
    p["instance_id"] = np.where(p["valid"], t, 0).astype(np.int32)
    ns(m, patch_rel(e), p)
    edit(m, f"replay/events/event-{e:02d}/event.json",
         lambda d: d.update(additions={str(t): int(p["valid"].sum())}))


def discard_cross(m):
    e = cross_event(m)
    p = nl(m, patch_rel(e))
    t = jl(m, f"replay/events/event-{e:02d}/event.json")["active_target"]
    keep = p["valid"] & (p["instance_id"] == t)
    p["valid"], p["instance_id"] = keep, np.where(keep, p["instance_id"], 0).astype(np.int32)
    ns(m, patch_rel(e), p)
    edit(m, f"replay/events/event-{e:02d}/event.json", lambda d: d.update(additions={str(t): int(keep.sum())}))


def include_zero(m):
    e = consumed(m)[0]
    p = nl(m, patch_rel(e))
    rr, cc = np.nonzero(p["valid"])
    p["instance_id"][rr[:10], cc[:10]] = 0
    ns(m, patch_rel(e), p)


def append_twice(m):
    def f(d):
        a, b = d["events"][6], d["events"][7]
        for k in ("observation_root", "observation_freeze_sha256", "correspondence_freeze_sha256",
                  "geometry_freeze_sha256", "calibration_sha256", "products"):
            b[k] = a[k]
    edit(m, "events/event-list.json", f)
    edit(m, "freeze/event-list-freeze.json",
         lambda d: d["files"].update({"events/event-list.json": C.sha256(m / "events/event-list.json")}))


def provenance_target(m):
    e = cross_event(m)
    edit(m, f"replay/events/event-{e:02d}/event.json", lambda d: d.update(active_target=202 if d["active_target"] != 202
                                                                           else 172))


# ------------------------------------------------------------------ GEOMETRY
def xyz_edit(fn):
    def mut(m):
        e = cross_event(m) or consumed(m)[0]
        p = nl(m, patch_rel(e))
        p["xyz_h"] = fn(p["xyz_h"]).astype(np.float32)
        ns(m, patch_rel(e), p)
    return mut


def position_direct(m):
    def f(d):
        d["data_reads"] = sorted(d["data_reads"] + [str(C.NS1C2 / "steps/step-05/observation/oracle_aid/"
                                                                 "reference-observation.npz")])
    edit(m, "replay/replay-opened-files.json", f)


# ------------------------------------------------------------------ MAP
def fuse_cross(m):
    e, i = cross_event(m), cross_id(m)
    t = jl(m, f"replay/events/event-{e:02d}/event.json")["active_target"]
    tgt = jl(m, f"replay/state-after-event-{e:02d}.json")["contexts"][str(t)]["map"]

    def f(c):
        c["map"] = dict(tgt)
    ctx_edit(m, e, i, f)


def other_map(m):
    ids = [9, 12]
    def f(c):
        c["map"] = dict(jl(m, "replay/state-after-event-00.json")["contexts"]["12"]["map"])
    ctx_edit(m, 0, ids[0], f)


def dedup(m):
    e, i = cross_event(m), cross_id(m)
    rows_edit(m, e, "M2", i, lambda r: r.update(geometry_points=r["geometry_points"] - 100))


# ------------------------------------------------------------------ REVISION
def m2_surfels(m):
    for rel in states_from(m, 0):
        def f(d):
            for r in d["tables"]["M2"]:
                r["revision"] = [r["own_looks"], r["map_surfels"]]
        edit(m, rel, f)


def no_cross_increment(m):
    e, i = cross_event(m), cross_id(m)
    prev = {int(r["temporary_entity_id"]): r for r in jl(m, f"replay/state-after-event-{e - 1:02d}.json")["tables"]["M2"]}
    rows_edit(m, e, "M2", i, lambda r: r.update(revision=prev[i]["revision"]))
    edit(m, f"replay/state-after-event-{e:02d}.json", lambda d: d["fresh_probes"]["M2"].pop(str(i), None))


def m1_cross(m):
    e, i = cross_event(m), cross_id(m)
    rows_edit(m, e, "M1", i, lambda r: r.update(revision=[r["own_looks"], r["revision"][1] + 777]))


# ------------------------------------------------------------------ CONTEXT
def visited_cross(m):
    e, i = cross_event(m), cross_id(m)
    ctx_edit(m, e, i, lambda c: c["visited"].append([1.0, 2.0]))


def evidence_other(m):
    e, i = cross_event(m), cross_id(m)
    ctx_edit(m, e, i, lambda c: c["evidence"].update(sha256="0" * 64))


def own_looks_other(m):
    e, i = cross_event(m), cross_id(m)
    ctx_edit(m, e, i, lambda c: c.update(own_looks=c["own_looks"] + 1))


# ------------------------------------------------------------------ SCHEDULER
def ineligible(m):
    edit(m, "replay/state-after-event-03.json", lambda d: d["machines"]["M2"]["order"].append(110))


def names(m):
    edit(m, "events/event-list.json", lambda d: d["events"][0].update(object_name="desk"))
    edit(m, "freeze/event-list-freeze.json",
         lambda d: d["files"].update({"events/event-list.json": C.sha256(m / "events/event-list.json")}))


def order_changed(m):
    k = max(int(p.stem.split("-")[-1]) for p in (m / "replay/decisions").glob("before-step-*.json"))
    edit(m, f"replay/decisions/before-step-{k:02d}.json",
         lambda d: d["actions"]["M2"].update(target=212 if d["actions"]["M2"]["target"] != 212 else 123))


# ------------------------------------------------------------------ CAUSAL REPLAY
def past_divergence(m):
    edit(m, "replay/decisions/before-step-03.json",
         lambda d: d["actions"]["M2"].update(local_gaze_deg=[d["actions"]["M2"]["local_gaze_deg"][0] + 5.0,
                                                             d["actions"]["M2"]["local_gaze_deg"][1]]))


def counterfactual(m):
    js(m, "replay/divergence.json", {"before_ns1c2_step": 5, "m1_action": {}, "m2_divergent_action": {"executed": False}})
    edit(m, "replay/replay.json", lambda d: d.update(divergence=True))


def skip_event(m):
    shutil.rmtree(m / "replay/events/event-03")
    edit(m, "replay/replay.json", lambda d: d["consumed_events"].remove(3))


# ------------------------------------------------------------------ PROCESS
def blender(m):
    edit(m, "replay/replay-opened-files.json",
         lambda d: d["process_guard"]["attempts"].append("subprocess.Popen: blender -b classroom_eye.blend"))


def rerender(m):
    (m / "replay/events/event-06/raw_L.exr").write_bytes(b"\x76\x2f\x31\x01")
    with open(unlinked(m / "process-log.jsonl"), "a") as f:
        f.write(json.dumps({"command": "acquire", "status": "ok", "code": {"commit": "x", "dirty": False,
                                                                         "pushed": True}}) + "\n")


# ------------------------------------------------------------------ VISUAL
def man_edit(fn):
    def mut(m, mv):
        d = json.loads((mv / "visuals-manifest.json").read_text())
        fn(d)
        (mv / "visuals-manifest.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    return mut


def pixel(m, mv):
    p = mv / "overview.png"
    im = Image.open(p).convert("RGB")
    v = im.getpixel((100, 100))
    im.putpixel((100, 100), (255 - v[0], v[1], v[2]))
    im.save(p, format="PNG", optimize=False)


def fused_drawing(d):
    d["memory_vs_map"] = "memory fused into the persistent map"
    d["figures"]["overview.png"]["labels"] = [x for x in d["figures"]["overview.png"]["labels"]
                                              if not x.startswith("INSTANCE MEASUREMENT MEMORY")]


# ------------------------------------------------------------------ others
def m0_altered(m):
    rel = jl(m, "replay/state-after-event-01.json")["fresh_probes"]["M0"]["172"]
    edit(m, rel, lambda d: d["probe"]["summary"]["fsg6f"].update(frontier_open_count=-1))


def synthetic_altered(m):
    def f(d):
        d["tests"]["05_cross_changes_m2_revision"]["pass"] = False
        d["failed"] = ["05_cross_changes_m2_revision"]
        d["marker"] = "NS1D_SYNTHETIC_FAIL"
    edit(m, "synthetic/synthetic-report.json", f)


def historical_altered(m):
    edit(m, "known-answer/known-answer.json", lambda d: d["memory_rebuild"].update(total_points=7843576))


def order_swapped(m):
    def f(d):
        d["events"][3], d["events"][4] = d["events"][4], d["events"][3]
    edit(m, "events/event-list.json", f)
    edit(m, "freeze/event-list-freeze.json",
         lambda d: d["files"].update({"events/event-list.json": C.sha256(m / "events/event-list.json")}))


def manual_reactivation(m):
    last = f"replay/state-after-event-{max(consumed(m)):02d}.json"
    ev = {"event": "natural_reactivation", "object": 9, "global_step": 2, "trigger_target": 172,
          "probe_before": {}, "probe_after": {}}
    edit(m, last, lambda d: d["events_emitted"]["M2"].append(ev))
    edit(m, "replay/replay.json", lambda d: d["natural_reactivations"].append(ev))


def wrong_outcome(m):
    edit(m, "replay/replay.json", lambda d: d.update(outcome_reading="Outcome 1 - cross-target divergence"))


def claimed_executed(m):
    if (m / "replay/final.json").exists():
        edit(m, "replay/final.json", lambda d: d["next_decisions"]["M2"].update(executed=True))
    else:
        edit(m, "replay/divergence.json", lambda d: d["m2_divergent_action"].update(executed=True))


def probe_altered(m):
    e = cross_event(m) or 0
    st = jl(m, f"replay/state-after-event-{e:02d}.json")
    i = sorted(st["fresh_probes"]["M2"])[0]
    edit(m, st["fresh_probes"]["M2"][i], lambda d: d["probe"]["summary"].update(effective_points=1))


def catalog_read(m):
    edit(m, "events/events-opened-files.json",
         lambda d: d["data_reads"].append(str(C.NS1C2 / "steps/step-04/observation/evaluation_only/instance-catalog.json")))


@contextlib.contextmanager
def class_routes_by_target():
    """In-process: the memory class routes by the ACTIVE target (a wrong mechanism the recorded memory must expose)."""
    from fov3d.reconstruction import measurement_memory as MM
    orig = MM.InstanceMeasurementMemory.append_patch

    def wrong(self, patch, *, source_global_index, source_active_target_id):
        p = {k: np.asarray(v) for k, v in patch.items()}
        p["instance_id"] = np.where(np.asarray(p["valid"], bool), int(source_active_target_id), 0).astype(np.int32)
        return orig(self, p, source_global_index=source_global_index, source_active_target_id=source_active_target_id)
    MM.InstanceMeasurementMemory.append_patch = wrong
    try:
        yield
    finally:
        MM.InstanceMeasurementMemory.append_patch = orig


@contextlib.contextmanager
def report_marker():
    """In-process: the report under check carries an NS1d ACCEPTED marker."""
    td = tempfile.TemporaryDirectory()
    p = Path(td.name) / "report.md"
    p.write_text("**Status: ACCEPTED.**\n" + C.NS1D_ACCEPTED + "\n")
    orig_repo, orig_path = C.REPO, C.REPORT_PATH
    C.REPORT_PATH = str(p)
    try:
        yield
    finally:
        C.REPORT_PATH = orig_path
        C.REPO = orig_repo
        td.cleanup()


ANY = lambda m: True  # noqa: E731
CROSS = lambda m: cross_event(m) is not None and cross_event(m) > 0  # noqa: E731
ALL8 = lambda m: consumed(m) == list(range(9))  # noqa: E731
EV3 = lambda m: (m / "replay/state-after-event-03.json").exists() and (m / "replay/decisions/before-step-03.json").exists()  # noqa: E731,E501

CORRUPTIONS = [
    # (family, name, applies, mutation, kind, expected catching checks)
    ("MEMORY ROUTING", "route samples by the active target instead of the observed id", CROSS, route_by_target, "run",
     ["07", "09"]),
    ("MEMORY ROUTING", "discard the cross-target ids", CROSS, discard_cross, "run", ["07", "09"]),
    ("MEMORY ROUTING", "include instance 0 in the memory patch", ANY, include_zero, "run", ["07"]),
    ("MEMORY ROUTING", "the same physical observation appended twice (event list)", ALL8, append_twice, "run", ["06"]),
    ("MEMORY ROUTING", "provenance target changed", CROSS, provenance_target, "run", ["09"]),
    ("MEMORY ROUTING", "the accepted class routes by active target (in-process)", CROSS, class_routes_by_target,
     "live", ["09"]),
    ("GEOMETRY", "planar-like geometry instead of spherical H0 (range scaled)", ANY, xyz_edit(lambda a: a * 0.98), "run",
     ["07"]),
    ("GEOMETRY", "Position read directly by the replay", ANY, position_direct, "run", ["08", "21"]),
    ("GEOMETRY", "rounded correspondence / geometry", ANY, xyz_edit(lambda a: np.round(a, 2)), "run", ["07"]),
    ("MAP", "cross-target samples fused into the observed entity's map", CROSS, fuse_cross, "run", ["11", "14", "15"]),
    ("MAP", "a frozen map altered (another entity's map)", ANY, other_map, "run", ["14", "15"]),
    ("MAP", "memory deduplicated against the map", CROSS, dedup, "run", ["11"]),
    ("REVISION", "map surfels used as the M2 revision", ANY, m2_surfels, "run", ["11", "13"]),
    ("REVISION", "no M2 increment on cross-target evidence", CROSS, no_cross_increment, "run", ["11", "13"]),
    ("REVISION", "M1 incremented by cross-target evidence", CROSS, m1_cross, "run", ["11", "13"]),
    ("CONTEXT", "a cross-target gaze appended to visited", CROSS, visited_cross, "run", ["14"]),
    ("CONTEXT", "another entity's evidence altered", CROSS, evidence_other, "run", ["14"]),
    ("CONTEXT", "a cross-target observation counted as an own look", CROSS, own_looks_other, "run", ["14"]),
    ("SCHEDULER", "an observed but ineligible id (110) added to the scheduler", EV3, ineligible, "run", ["16"]),
    ("SCHEDULER", "an object name used", ANY, names, "run", ["16"]),
    ("SCHEDULER", "the scheduler order changed (another target selected)", ANY, order_changed, "run", ["16", "17"]),
    ("CAUSAL REPLAY", "continue past the first divergence", ALL8, past_divergence, "run", ["17"]),
    ("CAUSAL REPLAY", "a counterfactual later observation consumed", ALL8, counterfactual, "run", ["17"]),
    ("CAUSAL REPLAY", "a memory event skipped", EV3, skip_event, "run", ["17"]),
    ("PROCESS", "Blender launched", ANY, blender, "run", ["20"]),
    ("PROCESS", "a re-render", ANY, rerender, "run", ["20"]),
    ("VISUAL", "memory drawn as fused surfels", ANY, man_edit(fused_drawing), "vis", ["23"]),
    ("VISUAL", "the source active target hidden", ANY,
     man_edit(lambda d: d["figures"]["overview.png"].update(source_active_target_shown=False)), "vis", ["23"]),
    ("VISUAL", "the divergence / no-divergence panel omitted", ANY,
     man_edit(lambda d: d["figures"]["overview.png"].update(panels=["A", "B", "C", "D"])), "vis", ["23"]),
    ("VISUAL", "a canonical pixel altered", ANY, pixel, "vis", ["23"]),
    ("BASELINE", "an M0 probe differs from accepted NS1c2", ANY, m0_altered, "run", ["10"]),
    ("BASELINE", "the synthetic report altered", ANY, synthetic_altered, "run", ["04"]),
    ("BASELINE", "a historical known-answer value altered", ANY, historical_altered, "run", ["05"]),
    ("EVENTS", "event order swapped", ANY, order_swapped, "run", ["06"]),
    ("REACTIVATION", "a manual reactivation without a memory addition", ANY, manual_reactivation, "run", ["18"]),
    ("OUTCOME", "a wrong outcome reading", ANY, wrong_outcome, "run", ["19"]),
    ("TERMINOLOGY", "an ACCEPTED marker in the report (in-process)", ANY, report_marker, "live", ["22"]),
    ("TERMINOLOGY", "a descriptive decision claimed executed", ANY, claimed_executed, "run", ["22"]),
    ("PROBE", "a recorded M2 probe altered", ANY, probe_altered, "run", ["12"]),
    ("TRUTH", "a catalog read in the events stage", ANY, catalog_read, "run", ["21"]),
]


def run_suite(run: Path, vis: Path, baseline_failed: list, ignore_baseline: tuple = ()) -> dict:
    """``ignore_baseline`` is a development aid only; the canonical suite uses an empty tuple."""
    run, vis = Path(run), Path(vis)
    before = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out = {"baseline_failed": list(baseline_failed), "results": [], "missed": [], "not_applicable": [],
           "baseline_failing": []}
    if set(baseline_failed) - set(ignore_baseline):
        out.update(error="the suite runs only from a passing baseline", run_unchanged_by_suite=True,
                   marker="NORTH_STAR1D_MUTATIONS_INCOMPLETE")
        return out
    with tempfile.TemporaryDirectory(prefix="ns1d-corrupt-") as td:
        m, mv = mirror(run, vis, Path(td) / "null")
        null = C.run_checks(m, mv, quiet=True)
        out["null_probe"] = {"failed": [k for k, v in null.items() if not v["pass"] and k not in ignore_baseline],
                             "checked": len(null)}
        shutil.rmtree(Path(td) / "null")
        for family, name, applies, mutate, kind, expect in CORRUPTIONS:
            d = Path(td) / f"c{len(out['results']):02d}"
            m, mv = mirror(run, vis, d)
            if set(expect) & set(ignore_baseline):
                out["baseline_failing"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "BASELINE FAILING (dev)"})
                shutil.rmtree(d)
                continue
            if not applies(m):
                out["not_applicable"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "NOT APPLICABLE",
                                       "reason": "the mutated product does not exist in the executed trace"})
                shutil.rmtree(d)
                continue
            if kind == "live":
                with mutate():
                    res = C.run_checks(m, mv, only=set(expect), quiet=True)
            else:
                if kind == "vis":
                    mutate(m, mv)
                else:
                    mutate(m)
                refreeze(m)
                res = C.run_checks(m, mv, only=set(expect), quiet=True)
            caught = [k for k in expect if not res[k]["pass"]]
            rec = {"family": family, "corruption": name, "expected": expect, "caught_by": caught,
                   "status": "CAUGHT" if caught == expect else "MISSED"}
            if caught != expect:
                out["missed"].append(name)
                rec["details"] = {k: res[k]["detail"] for k in expect if res[k]["pass"]}
            out["results"].append(rec)
            print(f"{C.PREFIX} corruption {rec['status']:<14} {family}: {name} -> {caught}", flush=True)
            shutil.rmtree(d)
    after = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out["run_unchanged_by_suite"] = after == before
    applicable = [r for r in out["results"] if r["status"] in ("CAUGHT", "MISSED")]
    out["caught"] = sum(1 for r in applicable if r["status"] == "CAUGHT")
    out["applicable"] = len(applicable)
    out["marker"] = "NORTH_STAR1D_MUTATIONS_CAUGHT" if not out["missed"] and not out["null_probe"]["failed"] \
        and out["run_unchanged_by_suite"] and not out["baseline_failing"] else "NORTH_STAR1D_MUTATIONS_INCOMPLETE"
    print(f"{C.PREFIX} corruptions caught {out['caught']}/{out['applicable']} (not applicable "
          f"{len(out['not_applicable'])}; baseline-failing {len(out['baseline_failing'])}); null probe failed "
          f"{out['null_probe']['failed']}; run unchanged {out['run_unchanged_by_suite']}; {out['marker']}", flush=True)
    return out
