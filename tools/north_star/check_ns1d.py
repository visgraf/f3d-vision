#!/usr/bin/env python3
"""North Star-1d checker: fail-capable verification of the controller-phase cross-target measurement memory (read-only).

    .venv/bin/python tools/north_star/check_ns1d.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/north-star/ns1d-cross-target-measurement-memory-contract.md, section 20.  The checker keeps its own
literal pins and recomputes independently wherever an independent formula exists: the event list (own derivation from
the accepted records), every memory patch (own construction from the pinned products), the identity attachment (own
re-attachment from ``instance_L`` at ``uv_L``), the memory (own rebuild with the accepted class), the M0 / M1 / M2
geometry sizes and revisions, the probe-cache sets, the map re-fusions, every scheduler decision (the accepted
``schedule_normal`` on own statuses) and the first divergence.  The accepted policy has no independent implementation:
every fresh probe is recomputed from its reconstructed context and own geometry.  The synthetic and historical known
answers are re-run.  ``--corruptions`` runs the mutation suite (check_ns1d_corruptions.py) after a null probe.
"""
from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

PREFIX = "[ns1d-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
BASE = "3720d745558bcbadb1c9edb3ffad5aaf0d86b3bb"
NS1C2_ACCEPTANCE = "5fe0684bae6ab4bc8a2080b1a93089fdb2a935af"
NS1C_REPORT_HEAD = "4107be86228c970f4b82fb6d5343365c551f36b0"
CONTRACT = "93f51d3abea379c0bf05720261dda039dca073d0"
CONTRACT_PATH = "docs/north-star/ns1d-cross-target-measurement-memory-contract.md"
REPORT_PATH = "docs/north-star/ns1d-cross-target-measurement-memory-report.md"
NS1C2_REPORT = "docs/north-star/ns1c2-controller02-phase-semantics-report.md"
NS1C2_ACCEPTED = "NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_ACCEPTED"
NS1C_ACCEPTED = "NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_" + "ACCEPTED"
NS1D_ACCEPTED = "NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_" + "ACCEPTED"
PREVIEWS = Path("/home/lvelho/rd/f3d-vision/previews")
NS1B = PREVIEWS / "north-star/ns1b-recentered-controller-handoff"
NS1C = PREVIEWS / "north-star/ns1c-coherent-first-scene-switch"
NS1C2 = PREVIEWS / "north-star/ns1c2-controller02-phase-semantics"
C01 = PREVIEWS / "controller-01-full"
C02 = PREVIEWS / "controller-02-classroom-replay"
MANIFESTS = {"ns1b": (NS1B, "e859fa61489015191f5ef3639ef91766cb26f3f787eb3dd279cfd8516435288c"),
             "ns1c": (NS1C, "90e2dd4b8a2d287a47f22b4553903a06e0c1059105fec1f954c13da09d426638"),
             "run": (NS1C2, "0ec6228d96db1bfadc3372c3ce95342ddfa14f7ba2f11d24234c20ed59d2c8c1")}
NS1C2_CHECK_SUMMARY = "dae0671d0e9329eff732a08990849c45222d87905fcce75d9cd3d78bfe9243b7"
NS1C2_SCENE_FREEZE = "ea5d046511e9ff7ad960826e3d3f7ce179a07edcfddc85aa62bbae7e4ff91640"
MEMORY_PY = ("fov3d/reconstruction/measurement_memory.py",
             "27471ebf7076e5a21b8d23be994425993115b5e379a4dd7f32b7fce09e52ab25")
C01_DIGEST = "1f7b86558a5e48bc5c3349cde46c90e8f4cd409cff63b445d41a5bc6f37b85b5"
C02_PINS = {"events.json": "fae7e64880f82602c8a868d0598bafab2c6d8da8e0c3f4465440c213d848327c",
            "final-residue.json": "a315714f0452621425fe8463e03d1b1c8e4b70d8ec9778e122ad518f90032c00"}
COHERENT = [9, 12, 123, 129, 172, 202, 204, 212, 230, 231]
AMBIGUOUS = [10, 110, 178]
STEPS = 8
EXPECTED = [(0, 172, "ns1b_action_01", (-155.008, 33.636), "ns1b:"),
            (1, 172, "ns1c_step_00", (-147.585, 37.246), "ns1c:steps/step-00"),
            (2, 172, "ns1c_step_01", (-145.704, 42.032), "ns1c:steps/step-01"),
            (3, 172, "ns1c_step_02", (-143.516, 46.782), "ns1c:steps/step-02"),
            (4, 172, "ns1c_step_03", (-150.152, 48.188), "ns1c:steps/step-03"),
            (5, 172, "ns1c2_step_04", (-163.040, 31.040), "run:steps/step-04"),
            (6, 172, "ns1c2_step_05", (-163.874, 26.094), "run:steps/step-05"),
            (7, 172, "ns1c2_step_06", (-153.654, 39.235), "run:steps/step-06"),
            (8, 202, "ns1c2_step_07", (-151.282, 22.052), "run:steps/step-07")]
HISTORICAL = {"looks": 141, "total_points": 7843577, "observed_instances": 33, "localized_objects": 25,
              "own_target_points": 2274857, "cross_target_points": 5494429, "cross_fraction_pct": 70.7,
              "unlocated_measured_ids": 8, "unlocated_points": 74291}
H109 = {"revision_delta": 4, "trigger": 110, "effective": [6166, 6170], "eligible": [0, 28],
        "proposal": [-7.0, 14.100000000000001], "service_step": 134}
OBS_FILES = ("correspondence/oracle-correspondences.npz", "geometry/epipolar-result.npz",
             "segmentation/local-identity.npz")
STAGES = ["source", "synthetic", "known-answer", "events", "replay"]
GUARDED = ["source/source-opened-files.json", "known-answer/known-answer-opened-files.json",
           "events/events-opened-files.json", "replay/replay-opened-files.json"]
NS1D_FILES = ["tools/north_star/" + n for n in ("ns1d_spec.py", "ns1d_core.py", "ns1d_run.py", "ns1d_synthetic.py",
                                                "ns1d_visuals.py", "check_ns1d.py", "check_ns1d_corruptions.py")]
DECLARED = set(NS1D_FILES) | {CONTRACT_PATH, REPORT_PATH, "tools/repository/check_repository_layout.py"}
RENDER_MODULES = ("ns1c2_render", "ns1a_render", "ns1b_render", "ab1a_stereo", "ab1d_match", "ab1d3_sgbm")
PRODUCTION = ["ns1d_spec.py", "ns1d_core.py", "ns1d_run.py", "ns1d_visuals.py"]
FORBIDDEN_READ = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                  "evaluation.json", "/evaluation/", "evaluation_only", "actions.json", "result.json",
                  "controller-01-full/manifest.json", "controller-02-classroom-replay/manifest.json",
                  "breadth-1-classroom", "natural-bootstrap-1a", "natural-bootstrap-1b")
NORTH_STAR_TRUTH = ("reference-observation.npz", ".exr", "/oracle_aid/")
NAME_KEYS = ("object_name", "target_name", "name")
FIGURES_ALWAYS = ["overview.png", "memory-causal-timeline.png", "effective-geometry-before-after.png"]
REQUIRED_LABELS = {"overview.png": ["ACCEPTED HISTORICAL REFERENCE - not an NS1d measurement",
                                    "INSTANCE MEASUREMENT MEMORY (measured samples, NOT fused surfels)",
                                    "PERSISTENT SURFACE MAP (target-only fusion)", "AMBIGUOUS ORACLE ID - EXCLUDED",
                                    "NOT EXECUTED", "BOOTSTRAP CROSS-TARGET MEMORY: NOT DECIDED BY NS1d",
                                    "ORACLE CORRESPONDENCE", "ORACLE SEGMENTATION AID"],
                   "effective-geometry-before-after.png": ["EFFECTIVE GEOMETRY = map + memory (no dedup, no fusion)"],
                   "memory-causal-timeline.png": ["AMBIGUOUS ORACLE ID - EXCLUDED"]}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def ancestor(a: str, b: str = "HEAD") -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=REPO, capture_output=True).returncode == 0


def load(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def members(path, keys) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in keys}


def digest(a: np.ndarray) -> str:
    a = np.ascontiguousarray(a)
    return hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def root_of(ref: str) -> Path:
    scheme, rel = ref.split(":", 1)
    base = {"ns1b": NS1B, "ns1c": NS1C, "run": NS1C2}[scheme]
    return base / rel if rel.strip("/") else base


def resolve(ref: str) -> Path:
    return root_of(ref)


class X:
    """The run under check (possibly a corruption mirror), with caches."""

    def __init__(self, run: Path, vis: Path) -> None:
        self.run, self.vis = Path(run), Path(vis)
        self._j, self.memo = {}, {}
        self.roots = sorted({str(self.run), str(self.run.resolve())} | self._orig(), key=len, reverse=True)

    def _orig(self) -> set:
        try:
            rec = json.loads((self.run / "source/source-opened-files.json").read_text())
            w = [d for d in rec["allow_write_dirs"] if d.endswith("/source")]
            return {w[0][: -len("/source")]} if w else set()
        except FileNotFoundError:
            return set()

    def j(self, rel: str):
        if rel not in self._j:
            self._j[rel] = json.loads((self.run / rel).read_text())
        return self._j[rel]

    def has(self, rel: str) -> bool:
        return (self.run / rel).exists()

    def rel(self, p: str) -> str:
        for r in self.roots:
            if p == r or p.startswith(r + "/"):
                return p[len(r) + 1:]
        return p

    def log(self) -> list[dict]:
        return [json.loads(ln) for ln in (self.run / "process-log.jsonl").read_text().splitlines() if ln.strip()]

    def replay(self) -> dict:
        return self.j("replay/replay.json")

    def consumed(self) -> list[int]:
        return [int(e) for e in self.replay()["consumed_events"]]

    def state(self, e: int) -> dict:
        return self.j(f"replay/state-after-event-{e:02d}.json")

    def event(self, e: int) -> dict:
        return self.j(f"replay/events/event-{e:02d}/event.json")

    def decision(self, k: int) -> dict:
        return self.j(f"replay/decisions/before-step-{k:02d}.json")

    def decisions(self) -> list[int]:
        return sorted(int(p.stem.split("-")[-1]) for p in (self.run / "replay/decisions").glob("before-step-*.json"))

    def el(self) -> dict:
        return self.j("events/event-list.json")


def memo(x: X, key: str, fn):
    if key not in x.memo:
        x.memo[key] = fn()
    return x.memo[key]


# ---------------------------------------------------------------- own independent implementations
def own_events(x: X) -> list[dict]:
    """The controller-phase observations derived from the accepted records (independent of the run's list)."""
    def build():
        out = [{"event": 0, "target": int(json.loads((NS1B / "fusion/fusion.json").read_text())["target"]),
                "root": "ns1b:", "patch_id": json.loads((NS1B / "fusion/fusion.json").read_text())["patch_id"],
                "gaze": json.loads((NS1B / "observation/acquisition/calibration.json").read_text())["gaze_yaw_pitch_deg"],
                "step": None}]
        final = json.loads((NS1C2 / "scene/final-scene-state.json").read_text())
        for k in range(int(final["executed_actions"])):
            fu = json.loads((NS1C2 / f"steps/step-{k:02d}/fusion/fusion.json").read_text())
            d = json.loads((NS1C2 / f"steps/step-{k:02d}/plan/decision.json").read_text())
            cal = json.loads((root_of(fu["observation_source"]) / "observation/acquisition/calibration.json").read_text())
            out.append({"event": k + 1, "target": int(d["action"]["target"]), "root": fu["observation_source"],
                        "patch_id": fu["patch_id"], "gaze": cal["gaze_yaw_pitch_deg"], "step": k,
                        "decision_gaze": d["action"]["world_gaze_deg"]})
        return out
    return memo(x, "own_events", build)


def own_patch(root: Path) -> tuple[dict, dict]:
    prod = load(root / OBS_FILES[0])
    geom = members(root / OBS_FILES[1], ("P_epi", "valid_epi", "left_core_row", "left_core_col"))
    ident = load(root / OBS_FILES[2])
    r = prod["left_core_row"].astype(int)
    c = prod["left_core_col"].astype(int)
    p = geom["P_epi"]
    ids = ident["temporary_entity_id"].astype(int)
    meas = geom["valid_epi"].astype(bool) & np.all(np.isfinite(p), axis=1)
    pos = meas & (ids > 0)
    xyz = np.full((256, 256, 3), np.nan, np.float32)
    inst = np.zeros((256, 256), np.int32)
    val = np.zeros((256, 256), bool)
    xyz[r[meas], c[meas]] = p[meas].astype(np.float32)
    inst[r[pos], c[pos]] = ids[pos]
    val[r[pos], c[pos]] = True
    u, n = np.unique(ids[pos], return_counts=True)
    return {"xyz_h": xyz, "valid": val, "instance_id": inst}, {"counts": {str(int(a)): int(b) for a, b in zip(u, n)},
                                                             "valid": int(pos.sum()), "cells": int(r.size),
                                                             "unique_cells": int(np.unique(r * 256 + c).size),
                                                             "aligned": bool(np.array_equal(geom["left_core_row"], prod[
                                                                 "left_core_row"]) and np.array_equal(
                                                                 ident["left_core_col"], prod["left_core_col"]))}


def own_patches(x: X) -> dict:
    def build():
        return {ev["event"]: own_patch(root_of(ev["root"])) for ev in own_events(x) if ev["event"] in x.consumed()}
    return memo(x, "own_patches", build)


def own_memory(x: X, upto: int):
    def build():
        from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory
        mem = InstanceMeasurementMemory()
        adds = {}
        for ev in own_events(x):
            if ev["event"] > upto:
                break
            adds[ev["event"]] = mem.append_patch(own_patches(x)[ev["event"]][0], source_global_index=ev["event"],
                                                 source_active_target_id=ev["target"])
        return mem, adds
    return memo(x, f"own_memory_{upto}", build)


def own_counts(x: X, upto: int, i: int) -> tuple[int, int]:
    mem, _ = own_memory(x, upto)
    s = mem.snapshot(i)
    own = int((s.source_active_target_id == i).sum())
    return own, int(len(s.xyz_h)) - own


def map_len(path_ref: str) -> int:
    return int(len(members(resolve(path_ref), ("xyz_h",))["xyz_h"]))


def latest_probes(x: X, mode: str, e: int) -> dict:
    out = {}
    for k in range(e + 1):
        for i, rel in x.state(k)["fresh_probes"][mode].items():
            out[int(i)] = rel
    return out


def probe_rec(x: X, rel: str) -> dict:
    return x.j(rel)


def own_status(probe: dict) -> str:
    return "ACTIONABLE" if probe.get("proposal") is not None else "QUIET"


def own_decision(current: int, probes: dict, fix: dict) -> dict:
    from fov3d.control import controller02 as c2, integrated as ic
    sts = []
    for i in sorted(probes):
        loc = ic.ServiceState.ACTIONABLE if probes[i].get("proposal") is not None else ic.ServiceState.QUIET
        if loc is ic.ServiceState.ACTIONABLE and int(fix[i]) >= 24:
            sts.append(c2.ObjectStatus(i, loc, c2.Disposition.DEFERRED, "ordinary_budget"))
        else:
            sts.append(c2.ObjectStatus(i, loc))
    d = c2.schedule_normal(int(current), sts)
    if d is None:
        return {"kind": "none"}
    p = probes[int(d.target_id)]["proposal"]
    return {"kind": "attend", "target": int(d.target_id), "decision": str(d.reason), "source": p["source"],
            "local_gaze_deg": [float(v) for v in p["local_gaze_deg"]],
            "world_gaze_deg": [float(v) for v in p["world_gaze_deg"]]}


def act_diff(a: dict, b: dict) -> list[str]:
    out = []
    for f in ("kind", "target", "decision", "source", "local_gaze_deg", "world_gaze_deg"):
        u, v = a.get(f), b.get(f)
        if f.endswith("gaze_deg") and u is not None and v is not None:
            if [float(t) for t in u] != [float(t) for t in v]:
                out.append(f)
        elif u != v:
            out.append(f)
    return out


def accepted(k: int) -> dict:
    d = json.loads((NS1C2 / f"steps/step-{k:02d}/plan/decision.json").read_text())
    a = d["action"]
    return {"kind": d["kind"], "target": int(a["target"]), "decision": d["scheduler_decision"]["result"]["reason"],
            "source": a["source"], "local_gaze_deg": [float(v) for v in a["local_gaze_deg"]],
            "world_gaze_deg": [float(v) for v in a["world_gaze_deg"]]}


def current_at(x: X, e: int) -> int:
    return 172 if e == 0 else int(own_events(x)[e]["target"])


def fix_at(x: X, e: int) -> dict:
    return {int(i): int(c["own_looks"]) for i, c in x.state(e)["contexts"].items()}


def has_name(o) -> bool:
    if isinstance(o, dict):
        return any(k in NAME_KEYS or has_name(v) for k, v in o.items())
    if isinstance(o, list):
        return any(has_name(v) for v in o)
    return False


def guard(x: X, rel: str) -> dict:
    return x.j(rel)


def ok_entries(x: X) -> list[dict]:
    return [e for e in x.log() if e["status"] == "ok"]


# ---------------------------------------------------------------- the checks
def c01(x):
    origin = git("remote", "get-url", "origin")
    anc = {n: ancestor(s) for n, s in (("base", BASE), ("ns1c2_acceptance", NS1C2_ACCEPTANCE), ("contract", CONTRACT))}
    unchanged = subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode == 0
    added = git("log", "--diff-filter=A", "--format=%H", "--", CONTRACT_PATH).split()[-1:] == [CONTRACT]
    impl = {e["code"]["commit"] for e in ok_entries(x) if e["command"] in STAGES}
    later = bool(impl) and all(c != CONTRACT and ancestor(CONTRACT, c) for c in impl)
    rep = git("show", f"{BASE}:{NS1C2_REPORT}")
    acc = NS1C2_ACCEPTED in rep and "**Status: ACCEPTED.**" in rep
    import ns1d_spec as SPm
    spec = (SPm.CONTRACT_COMMIT == CONTRACT and SPm.BASE_COMMIT == BASE and SPm.NS1C2_ACCEPTANCE == NS1C2_ACCEPTANCE
            and SPm.NS1C_REPORT_HEAD == NS1C_REPORT_HEAD and list(SPm.COHERENT) == COHERENT)
    src = x.j("source/source-manifest.json")
    ok = (CANONICAL_REMOTE in origin and all(anc.values()) and unchanged and added and later and len(impl) == 1 and acc
          and spec and src["contract_commit"] == CONTRACT and src["base_commit"] == BASE and src["ns1c2_accepted_on_base"]
          and CANONICAL_REMOTE in src["origin"])
    return ok, {"origin": origin, "ancestors": anc, "contract_unchanged": unchanged, "contract_added_at": added,
                "implementation_commits": sorted(impl), "after_contract": later, "ns1c2_accepted_on_base": acc,
                "spec": spec}


def _pins_digest(pins: dict) -> str:
    return hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()


OWN_SOURCE_PINS_DIGEST = "5654ef07776dcaf13130207e59cecea7ede9701e4364af61d63f5fa7564eeb39"   # sha256 of the sorted SOURCE_PINS json


def c02(x):
    import ns1d_spec as SPm
    dg = _pins_digest(SPm.SOURCE_PINS)
    bad = sorted(p for p, h in SPm.SOURCE_PINS.items() if sha256(REPO / p) != h)
    mem_ok = SPm.SOURCE_PINS.get(MEMORY_PY[0]) == MEMORY_PY[1] and sha256(REPO / MEMORY_PY[0]) == MEMORY_PY[1]
    mem_diff = subprocess.run(["git", "diff", "--quiet", BASE, "--", MEMORY_PY[0]], cwd=REPO).returncode == 0
    fov_diff = subprocess.run(["git", "diff", "--quiet", BASE, "--", "fov3d"], cwd=REPO).returncode == 0
    mans = {k: sha256(v[0] / "manifest.json") == v[1] for k, v in MANIFESTS.items()}
    cs = sha256(NS1C2 / "check-summary.json") == NS1C2_CHECK_SUMMARY
    sf = sha256(NS1C2 / "freeze/scene-freeze.json") == NS1C2_SCENE_FREEZE
    files = sorted(glob.glob(str(C01 / "objects/instance_*/trajectory.partial.json")))
    c01d = hashlib.sha256("".join(f"{Path(f).relative_to(C01)} {sha256(f)}\n" for f in files).encode()).hexdigest()
    c02 = {f: sha256(C02 / f) for f in C02_PINS}
    src = x.j("source/source-manifest.json")
    ok = (dg == OWN_SOURCE_PINS_DIGEST and not bad and mem_ok and mem_diff and fov_diff and all(mans.values()) and cs
          and sf and c01d == C01_DIGEST and c02 == C02_PINS and src["source_pins"] == SPm.SOURCE_PINS
          and src["measurement_memory_unchanged_since_base"] and src["fov3d_unchanged_since_base"])
    return ok, {"pins_digest": dg, "changed": bad, "memory_class": [mem_ok, mem_diff], "fov3d_unchanged": fov_diff,
                "manifests": mans, "ns1c2_check_summary": cs, "scene_freeze": sf, "history": [c01d == C01_DIGEST,
                                                                                            c02 == C02_PINS]}


def c03(x):
    md = [f for f in git("ls-files").split("\n") if f.endswith(".md") and (REPO / f).is_file()]
    hits = [f for f in md if NS1C_ACCEPTED in (REPO / f).read_text(errors="replace")]
    anc = {ref: ancestor(NS1C_REPORT_HEAD, ref) for ref in ("HEAD", "origin/main", BASE)}
    src = x.j("source/source-manifest.json")["ns1c_decision"]
    return not hits and not any(anc.values()) and src["ok"], {"ns1c_marker_files": hits, "ancestor_of": anc}


def c04(x):
    import ns1d_synthetic as SY
    rep = memo(x, "synthetic", SY.run_all)
    saved = x.j("synthetic/synthetic-report.json")
    same = {k: v["pass"] for k, v in rep["tests"].items()} == {k: v["pass"] for k, v in saved["tests"].items()}
    ok = not rep["failed"] and rep["count"] == 20 and not saved["failed"] and same \
        and saved["marker"] == "NS1D_SYNTHETIC_PASS"
    return ok, {"failed": rep["failed"], "count": rep["count"], "saved_equal": same}


def c05(x):
    """The historical known answer, recomputed: the accepted memory over the 141 saved patches; the 109 replay."""
    def build():
        import ns1b_fixtures as FX
        import ns1b_core as B
        from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory
        files = FX.trajectory_files()
        rows = FX.c01_rows(files)
        objs = sorted(int(f.parent.name.split("_")[1]) for f in files)
        mem = InstanceMeasurementMemory()
        bad = 0
        for r in rows:
            i, k = int(r["target_id"]), int(r["step"])
            add = mem.append_patch(load(C01 / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz"),
                                   source_global_index=int(r["global_step"]), source_active_target_id=i)
            bad += add != {int(a): int(b) for a, b in r["measurement_memory_additions"].items()}
        tot = own = cross = unl = 0
        unl_ids = 0
        for iid in mem.instance_ids():
            s = mem.snapshot(iid)
            tot += len(s.xyz_h)
            if iid in objs:
                o = int((s.source_active_target_id == iid).sum())
                own += o
                cross += len(s.xyz_h) - o
            else:
                unl += len(s.xyz_h)
                unl_ids += 1
        got = {"looks": len(rows), "total_points": tot, "observed_instances": len(mem.instance_ids()),
               "localized_objects": len(objs), "own_target_points": own, "cross_target_points": cross,
               "cross_fraction_pct": round(100.0 * cross / (own + cross), 1), "unlocated_measured_ids": unl_ids,
               "unlocated_points": unl}
        del mem
        _f, _p, c01m, _c, _e = FX._modules()
        b4, a7 = FX.rebuild(109, 4, rows), FX.rebuild(109, 7, rows)
        rb, _ = c01m.probe_local_policy(b4["ctx"], b4["geometry"])
        ra, _ = c01m.probe_local_policy(a7["ctx"], a7["geometry"])
        ev = json.loads((C02 / "events.json").read_text())["events"]
        re_ = next(e for e in ev if e["event"] == "natural_reactivation" and int(e["object"]) == 109)
        diffs = (B.compare(re_["probe_before"], B.jsonable(dict(rb.detail)), 0.0)
                 + B.compare(re_["probe_after"], B.jsonable(dict(ra.detail)), 0.0))
        r109 = {"delta": a7["revision"][1] - b4["revision"][1], "own": [b4["revision"][0], a7["revision"][0]],
                "effective": [len(b4["geometry"]), len(a7["geometry"])], "states": [rb.state.value, ra.state.value],
                "proposal": None if ra.action is None else list(ra.action.gaze_yaw_pitch_deg), "diffs": diffs[:5],
                "trigger": re_["trigger_target"]}
        return got, bad, r109
    got, bad, r109 = memo(x, "historical", build)
    ka = x.j("known-answer/known-answer.json")
    ok = (got == HISTORICAL and bad == 0 and r109["delta"] == H109["revision_delta"] and r109["own"] == [3, 3]
          and r109["effective"] == H109["effective"] and r109["states"] == ["QUIET", "ACTIONABLE"]
          and r109["proposal"] == H109["proposal"] and not r109["diffs"] and r109["trigger"] == H109["trigger"]
          and ka["ok"] and ka["memory_rebuild"]["total_points"] == got["total_points"]
          and ka["reactivation_109"]["adapter_redrive"]["ok"] and ka["scheduler"]["ok"]
          and ka["scheduler"]["service_of_109"][0][4] == "natural_reactivation")
    return ok, {"own": got, "addition_mismatches": bad, "109": r109}


def c06(x):
    el = x.el()
    own = own_events(x)
    rows = el["events"]
    fz = x.j("freeze/event-list-freeze.json")
    mans = {k: json.loads((v[0] / "manifest.json").read_text()) for k, v in MANIFESTS.items()}
    probs = []
    if len(rows) != len(own) or len(own) != len(EXPECTED):
        probs.append(f"count {len(rows)} / own {len(own)} / expected {len(EXPECTED)}")
    for r, o, (e, t, pid, g, root) in zip(rows, own, EXPECTED):
        if not (r["event"] == o["event"] == e and r["target"] == o["target"] == t and r["patch_id"] == o["patch_id"] == pid
                and r["observation_root"] == o["root"] and o["root"].rstrip("/") == root.rstrip("/")
                and [float(v) for v in r["world_gaze_deg"]] == [float(v) for v in o["gaze"]]
                and max(abs(a - b) for a, b in zip(o["gaze"], g)) <= 5e-4):
            probs.append(f"event {e} differs from own derivation / expectation")
        if o.get("decision_gaze") is not None and [float(v) for v in o["decision_gaze"]] != [float(v) for v in o["gaze"]]:
            probs.append(f"event {e}: decision gaze != physical calibration gaze")
        scheme = o["root"].split(":", 1)[0]
        pre = o["root"].split(":", 1)[1].strip("/")
        pre = pre + "/" if pre else ""
        for f in OBS_FILES:
            if r["products"].get(f) != mans[scheme]["files"].get(pre + f):
                probs.append(f"event {e}: {f} pin != manifest")
        if r["observation_freeze_sha256"] != mans[scheme]["files"].get(pre + "freeze/observation-freeze.json"):
            probs.append(f"event {e}: observation freeze pin")
    keys = [r["observation_freeze_sha256"] for r in rows]
    cal = [r["calibration_sha256"] for r in rows]
    unique = len(set(keys)) == len(keys) and len(set(cal)) == len(cal)
    frozen = sha256(x.run / "events/event-list.json") == fz["files"]["events/event-list.json"]
    no_arrays = not [p for p in guard(x, "events/events-opened-files.json")["data_reads"] if p.endswith(".npz")]
    ok = not probs and unique and frozen and no_arrays and el["count"] == 9 and el["unique_observations"]
    return ok, {"problems": probs[:6], "unique": unique, "frozen": frozen, "no_array_opened": no_arrays}


def c07(x):
    probs = []
    for e in x.consumed():
        mine, info = own_patches(x)[e]
        saved = load(x.run / f"replay/events/event-{e:02d}/memory-patch.npz")
        ev = x.event(e)
        if set(saved) != set(mine) or not all(saved[k].dtype == mine[k].dtype and np.array_equal(
                saved[k], mine[k], equal_nan=saved[k].dtype.kind == "f") for k in mine):
            probs.append(f"event {e}: saved patch != own construction")
        if not (info["aligned"] and info["unique_cells"] == info["cells"]):
            probs.append(f"event {e}: products misaligned / repeated cells")
        if int(saved["valid"].sum()) != info["valid"] or ev["patch"]["valid_samples"] != info["valid"]:
            probs.append(f"event {e}: valid count")
        if ev["additions"] != info["counts"] or ev["patch"]["by_observed_id"] != info["counts"]:
            probs.append(f"event {e}: additions by id")
        if np.any(saved["instance_id"][saved["valid"]] <= 0) or np.any(saved["valid"] & ~np.isfinite(
                saved["xyz_h"]).all(axis=2)):
            probs.append(f"event {e}: an instance <= 0 or a non-finite sample is valid")
        if not ev["target_subset_equals_accepted_target_patch"]:
            probs.append(f"event {e}: target subset != accepted target patch")
    return not probs, {"problems": probs[:6], "events": x.consumed()}


def c08(x):
    """Identity attached after the geometry freeze, re-attached independently from instance_L at uv_L; no Position."""
    probs = []
    for ev in own_events(x):
        e = ev["event"]
        if e not in x.consumed():
            continue
        root = root_of(ev["root"])
        prod = load(root / OBS_FILES[0])
        valid = members(root / OBS_FILES[1], ("valid_epi",))["valid_epi"].astype(bool)
        inst = members(root / "observation/oracle_aid/reference-observation.npz", ("instance_L",))["instance_L"]
        uv = prod["uv_L"].astype(np.int64)
        mine = np.where(valid, inst[uv[:, 1], uv[:, 0]], -1)
        ident = load(root / OBS_FILES[2])["temporary_entity_id"]
        if not np.array_equal(mine, ident):
            probs.append(f"event {e}: identity != instance_L at uv_L")
        seg = json.loads((root / "segmentation/segmentation-opened-files.json").read_text())
        labels = [m.get("label") for m in seg["events"] if m.get("event") == "mark"]
        if labels[:2] != ["geometry_freeze_verified", "identity_access_begins"]:
            probs.append(f"event {e}: identity not attached after the geometry freeze")
        if seg.get("reference_members_read", ["instance_L"]) != ["instance_L"]:
            probs.append(f"event {e}: more than instance_L read")
    reads = guard(x, "replay/replay-opened-files.json")["data_reads"]
    truth = [p for p in reads if any(t in p for t in NORTH_STAR_TRUTH)]
    return not probs and not truth, {"problems": probs[:5], "replay_truth_reads": truth[:5]}


def c09(x):
    probs = []
    last = max(x.consumed())
    mem, adds = own_memory(x, last)
    for e in x.consumed():
        ev = x.event(e)
        if {str(k): int(v) for k, v in sorted(adds[e].items())} != ev["additions"]:
            probs.append(f"event {e}: own additions differ")
        if int(ev["active_target"]) != own_events(x)[e]["target"]:
            probs.append(f"event {e}: active target")
    summ = x.replay()["memory"]
    ids = list(mem.instance_ids())
    if summ["instance_ids"] != ids:
        probs.append("memory ids differ")
    for i in ids:
        s = mem.snapshot(i)
        d = summ["snapshot_digest"].get(str(i), {})
        if d != {"xyz_h": digest(s.xyz_h), "source_global_index": digest(s.source_global_index),
                 "source_active_target_id": digest(s.source_active_target_id)}:
            probs.append(f"id {i}: snapshot digest")
        if not (len(s.xyz_h) == len(s.source_global_index) == len(s.source_active_target_id)):
            probs.append(f"id {i}: misaligned")
        if int(summ["measured_points"].get(str(i), -1)) != len(s.xyz_h):
            probs.append(f"id {i}: measured points")
    mem2, _ = memo(x, "own_memory_again", lambda: own_memory_fresh(x, last))
    det = all(digest(mem2.snapshot(i).xyz_h) == digest(mem.snapshot(i).xyz_h) for i in ids)
    union = sorted({int(k) for e in x.consumed() for k in x.event(e)["additions"]})
    if ids != union:
        probs.append("memory does not hold every positive observed id")
    if summ["total_points"] != sum(len(mem.snapshot(i).xyz_h) for i in ids):
        probs.append("total")
    return not probs and det, {"problems": probs[:6], "deterministic": det, "ids": ids}


def own_memory_fresh(x: X, upto: int):
    from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory
    mem = InstanceMeasurementMemory()
    for ev in own_events(x):
        if ev["event"] <= upto:
            mem.append_patch(own_patches(x)[ev["event"]][0], source_global_index=ev["event"],
                             source_active_target_id=ev["target"])
    return mem, None


def c10(x):
    """M0 = accepted NS1c2: fresh probes equal NS1c2's (policy part, tolerance 0) and the same fresh sets; decisions."""
    import ns1c2_core as C2
    probs = []
    for e in x.consumed():
        fresh = {int(i): rel for i, rel in x.state(e)["fresh_probes"]["M0"].items()}
        d = NS1C2 / ("initial-probe/probes" if e == 0 else f"steps/step-{e - 1:02d}/update/probes")
        acc = {int(p.stem[1:]): p for p in d.glob("e*.json")}
        if set(fresh) != set(acc):
            probs.append(f"event {e}: M0 fresh {sorted(fresh)} != NS1c2 {sorted(acc)}")
        for i, rel in fresh.items():
            if i in acc:
                a = json.loads(acc[i].read_text())
                m = probe_rec(x, rel)
                if C2.policy_comparison(a["probe"], m["probe"]) or list(a["revision"]) != list(m["revision"]):
                    probs.append(f"event {e}: M0 probe of {i} differs from NS1c2")
    for k in x.decisions():
        if act_diff(x.decision(k)["actions"]["M0"], accepted(k)):
            probs.append(f"step {k}: M0 action != accepted")
    last = max(x.consumed())
    evs = [[v["event"], v["object"], v["global_step"]] for v in x.state(last)["events_emitted"]["M0"]]
    acc_ev = []
    for k in range(min(last, STEPS)):
        for v in json.loads((NS1C2 / f"scene/state-after-step-{k:02d}.json").read_text())["events"]:
            acc_ev.append([v["event"], v["object"], v["global_step"]])
    if evs != acc_ev:
        probs.append(f"M0 events {evs} != accepted {acc_ev}")
    return not probs, {"problems": probs[:6]}


def c11(x):
    """Own geometry sizes and revisions per mode, entity and event."""
    probs = []
    for e in x.consumed():
        st = x.state(e)
        for mode in ("M0", "M1", "M2"):
            rows = {int(r["temporary_entity_id"]): r for r in st["tables"][mode]}
            if sorted(rows) != COHERENT:
                probs.append(f"event {e} {mode}: table ids {sorted(rows)}")
                continue
            for i in COHERENT:
                ctx = st["contexts"][str(i)]
                n = memo(x, "map:" + ctx["map"]["path"], lambda: map_len(ctx["map"]["path"]))
                own, cross = own_counts(x, e, i)
                want_rev = {"M0": [ctx["own_looks"], n], "M1": [ctx["own_looks"], own],
                            "M2": [ctx["own_looks"], own + cross]}[mode]
                want_pts = {"M0": n, "M1": n + own, "M2": n + own + cross}[mode]
                r = rows[i]
                if r["revision"] != want_rev or r["geometry_points"] != want_pts or r["map_surfels"] != n or \
                        ctx["map"]["surfels"] != n or (r["own_memory_points"], r["cross_memory_points"]) != (own, cross):
                    probs.append(f"event {e} {mode} entity {i}: revision {r['revision']} vs {want_rev}, points "
                                 f"{r['geometry_points']} vs {want_pts}")
    return not probs, {"problems": probs[:6]}


def c12(x):
    """Every fresh M1 / M2 probe recomputed from its reconstructed context and the own geometry (tolerance 0)."""
    import ns1b_chart as CH
    import ns1c2_core as C2
    from fov3d.reconstruction.measurement_memory import effective_target_geometry
    CH.ensure_policy_modules()
    import ns1a_core  # noqa: F401
    import fsg6f_frontier  # noqa: F401
    charts = json.loads((NS1C2 / "charts/policy-charts.json").read_text())["charts"]
    probs, n = [], 0
    for e in x.consumed():
        st = x.state(e)
        mem, _ = own_memory(x, e)
        for mode in ("M1", "M2"):
            for i, rel in st["fresh_probes"][mode].items():
                i = int(i)
                ctx_rec = st["contexts"][str(i)]
                ctx = C2.context_from_record(ctx_rec, NS1C2)
                m = np.asarray(members(resolve(ctx_rec["map"]["path"]), ("xyz_h",))["xyz_h"], np.float64)
                s = mem.snapshot(i)
                q = s.xyz_h if mode == "M2" else s.xyz_h[s.source_active_target_id == i]
                g = effective_target_geometry(m, q)
                r = np.asarray(charts[str(i)]["R_HC"], np.float64)
                out = C2.probe_normal_ctx(ctx, CH.to_chart(g, r), r, np.asarray(charts[str(i)]["g0_H0"]), "checker")
                rec = probe_rec(x, rel)
                d = C2.policy_comparison(rec["probe"], C2.jsonable(out))
                if d or rec["probe"]["geometry_h0_points"] != len(g) or rec["probe"]["gate_called"]:
                    probs.append(f"event {e} {mode} entity {i}: {d[:2]}")
                n += 1
    return not probs, {"problems": probs[:6], "probes_recomputed": n}


def c13(x):
    """Revision / cache: fresh probes exactly where the mode's revision changed; cross additions never change M1 or maps."""
    probs = []
    for e in x.consumed():
        st = x.state(e)
        fresh = {m: sorted(int(i) for i in st["fresh_probes"][m]) for m in ("M0", "M1", "M2")}
        if e == 0:
            want = {m: COHERENT for m in ("M0", "M1", "M2")}
        else:
            t = own_events(x)[e]["target"]
            cross = sorted(int(k) for k in x.event(e)["additions"] if int(k) in COHERENT and int(k) != t)
            want = {"M0": [t], "M1": [t], "M2": sorted({t} | set(cross))}
            prev = x.state(e - 1)
            for i in cross:
                p1 = {int(r["temporary_entity_id"]): r for r in prev["tables"]["M1"]}[i]
                n1 = {int(r["temporary_entity_id"]): r for r in st["tables"]["M1"]}[i]
                p2 = {int(r["temporary_entity_id"]): r for r in prev["tables"]["M2"]}[i]
                n2 = {int(r["temporary_entity_id"]): r for r in st["tables"]["M2"]}[i]
                if p1["revision"] != n1["revision"] or p2["revision"] == n2["revision"] or \
                        n2["map_surfels"] != p2["map_surfels"]:
                    probs.append(f"event {e}: cross-target revision semantics wrong for {i}")
        if fresh != {m: sorted(v) for m, v in want.items()}:
            probs.append(f"event {e}: fresh {fresh} != expected {want}")
        cache = st["machines"]["M2"]["cache"]
        rows = {int(r["temporary_entity_id"]): r for r in st["tables"]["M2"]}
        if any(list(cache[str(i)]["revision"]) != rows[i]["revision"] for i in COHERENT):
            probs.append(f"event {e}: M2 cache keys != M2 revisions")
    return not probs, {"problems": probs[:6]}


CTX_KEYS = ("looks", "visited", "current_local_gaze", "own_looks", "evidence", "map")


def c14(x):
    """Own-look contexts: only the active target gains a look (the accepted NS1c2 record); others untouched."""
    probs = []
    s0 = json.loads((NS1C2 / "scene/state-initial.json").read_text())["entities"]
    for e in x.consumed():
        ctx = x.state(e)["contexts"]
        if e == 0:
            ref = s0
            t = None
        else:
            ref = json.loads((NS1C2 / f"scene/state-after-step-{e - 1:02d}.json").read_text())["entities"]
            t = own_events(x)[e]["target"]
            prev = x.state(e - 1)["contexts"]
            for i in COHERENT:
                if i != t and {k: ctx[str(i)][k] for k in CTX_KEYS} != {k: prev[str(i)][k] for k in CTX_KEYS}:
                    probs.append(f"event {e}: non-target {i} context changed")
            if ctx[str(t)]["own_looks"] != prev[str(t)]["own_looks"] + 1:
                probs.append(f"event {e}: target own looks")
        for i in COHERENT:
            if {k: ctx[str(i)][k] for k in CTX_KEYS} != {k: ref[str(i)][k] for k in CTX_KEYS}:
                probs.append(f"event {e}: context of {i} != the accepted NS1c2 record")
        fx = x.state(e)["fixations"]
        if {int(k): v for k, v in fx.items()} != {i: ctx[str(i)]["own_looks"] for i in COHERENT}:
            probs.append(f"event {e}: fixations != own looks")
    return not probs, {"problems": probs[:6]}


def c15(x):
    """Persistent maps: the accepted target-only re-fusion reproduced bitwise; untouched maps unchanged; never fused."""
    import ns1b_core as B
    import ns1c2_core as C2
    probs = []
    s0 = x.state(0)["contexts"]
    for e in x.consumed():
        ev = x.event(e)
        o = own_events(x)[e]
        t = o["target"]
        if e == 0:
            prev = C2.load_map(NS1B / "context/target-map-H0.npz")
            acc = NS1B / "fusion/fused-target-map.npz"
            tp = load(NS1B / "fusion/target-patch.npz")
        else:
            prev = C2.load_map(resolve(x.state(e - 1)["contexts"][str(t)]["map"]["path"]))
            acc = NS1C2 / f"steps/step-{e - 1:02d}/fusion/fused-target-map.npz"
            tp = load(NS1C2 / f"steps/step-{e - 1:02d}/fusion/target-patch.npz")
        fused, _r = B.fuse_h0(prev, {"frame": "H0", "patch_id": o["patch_id"], "xyz_h": tp["xyz_h"], "rgb": tp["rgb"],
                                     "instance_id": tp["instance_id"], "points": int(len(tp["xyz_h"]))}, t)
        if not C2.maps_equal(B.map_arrays(fused), load(acc)):
            probs.append(f"event {e}: own re-fusion != accepted map")
        if not ev["accepted_map_update"]["refused_equal"]:
            probs.append(f"event {e}: recorded re-fusion not equal")
        ctx = x.state(e)["contexts"]
        if e > 0 and resolve(ctx[str(t)]["map"]["path"]).resolve() != acc.resolve():
            probs.append(f"event {e}: target map is not the accepted fused map")
    last = x.state(max(x.consumed()))["contexts"]
    targets = {own_events(x)[e]["target"] for e in x.consumed() if e > 0}
    for i in COHERENT:
        m = load(resolve(last[str(i)]["map"]["path"]))
        if not np.all(m["instance_id"] == i):
            probs.append(f"map {i} holds another id")
        if i not in targets and last[str(i)]["map"] != s0[str(i)]["map"]:
            probs.append(f"untouched map {i} changed")
        own_pids = {"nb1c_gaze_06", "ns1b_action_01"} | {own_events(x)[e]["patch_id"] for e in x.consumed()
                                                        if own_events(x)[e]["target"] == i}
        if not {str(p) for p in m["patch_ids"]} <= own_pids | {f"nb1c_gaze_{r:02d}" for r in range(1, 7)}:
            probs.append(f"map {i} holds a foreign patch id")
    if not all(x.replay()["maps_equal_accepted_state"].values()) or not all(x.replay()["untouched_maps_unchanged"].values()):
        probs.append("replay record map flags")
    return not probs, {"problems": probs[:6]}


def c16(x):
    """Scheduler: own statuses -> the accepted schedule_normal; scheduler identity = the coherent set only."""
    probs = []
    for k in x.decisions():
        e = k
        rec = x.decision(k)
        for mode in ("M1", "M2", "M0"):
            probes = {i: probe_rec(x, rel)["probe"] for i, rel in latest_probes(x, mode, e).items()}
            if sorted(probes) != COHERENT:
                probs.append(f"step {k} {mode}: probe ids {sorted(probes)}")
                continue
            mine = own_decision(current_at(x, e), probes, fix_at(x, e))
            if act_diff(mine, rec["actions"][mode]):
                probs.append(f"step {k} {mode}: decision != own schedule_normal")
        if [r[0] for r in rec["m1_statuses"]] != COHERENT:
            probs.append(f"step {k}: M1 status ids")
    for e in x.consumed():
        st = x.state(e)
        for mode in ("M0", "M2"):
            if st["machines"][mode]["order"] != COHERENT:
                probs.append(f"event {e} {mode}: machine order")
        if any(int(i) not in COHERENT for m in ("M0", "M1", "M2") for i in st["fresh_probes"][m]):
            probs.append(f"event {e}: a non-scheduler id was probed")
    named = [rel for rel in ("events/event-list.json", "replay/replay.json") if has_name(x.j(rel))]
    named += [f"state {e}" for e in x.consumed() if has_name(x.state(e)["contexts"])]
    return not probs and not named, {"problems": probs[:6], "names": named}


def c17(x):
    """The first load-bearing divergence located by the checker; the replay stopped there; nothing later opened."""
    first = None
    for k in x.decisions():
        if act_diff(x.decision(k)["actions"]["M2"], accepted(k)):
            first = k
            break
    rp = x.replay()
    cons = x.consumed()
    probs = []
    if first is None:
        if rp["divergence"] or cons != list(range(STEPS + 1)) or x.decisions() != list(range(STEPS)) \
                or not x.has("replay/final.json") or x.has("replay/divergence.json"):
            probs.append("no divergence, but the replay did not consume exactly events 0..8 with a final record")
    else:
        dv = x.j("replay/divergence.json") if x.has("replay/divergence.json") else {}
        if not rp["divergence"] or dv.get("before_ns1c2_step") != first or cons != list(range(first + 1)) \
                or x.decisions() != list(range(first + 1)) or x.has("replay/final.json"):
            probs.append(f"divergence at step {first}, but the replay record / consumed events disagree")
    for k in x.decisions():
        if bool(x.decision(k)["differences"]["M2"]) != bool(act_diff(x.decision(k)["actions"]["M2"], accepted(k))):
            probs.append(f"step {k}: recorded differences inconsistent")
    reads = set(guard(x, "replay/replay-opened-files.json")["data_reads"])
    later = []
    for o in own_events(x):
        if o["event"] in cons:
            continue
        for f in OBS_FILES:
            if str((root_of(o["root"]) / f).resolve()) in reads:
                later.append(f"event {o['event']}: {f}")
    for e in cons:
        o = own_events(x)[e]
        if not all(str((root_of(o["root"]) / f).resolve()) in reads for f in OBS_FILES):
            probs.append(f"event {e} consumed without its products")
    written = sorted(int(p.name.split("-")[1]) for p in (x.run / "replay/events").glob("event-*"))
    if written != cons:
        probs.append(f"event records {written} != consumed {cons}")
    return not probs and not later, {"first_divergence": first, "problems": probs[:5], "later_opened": later[:5]}


def c18(x):
    """Natural reactivations come only from the adapter's refresh after a memory revision change; no manual call."""
    probs = []
    last = x.state(max(x.consumed()))
    react = [v for v in last["events_emitted"]["M2"] if v["event"] == "natural_reactivation"]
    if react != x.replay()["natural_reactivations"]:
        probs.append("replay reactivation list != the M2 adapter events")
    for v in react:
        e = int(v["global_step"]) + 1
        if str(v["object"]) not in x.event(e)["additions"] or int(v["trigger_target"]) != own_events(x)[e]["target"]:
            probs.append(f"reactivation of {v['object']} without a memory addition from the trigger")
    if any(v["event"] == "natural_reactivation" for v in last["events_emitted"]["M0"]):
        probs.append("M0 reactivation (target-only memory cannot reactivate)")
    scan = []
    for name in PRODUCTION:
        src = (HERE / name).read_text()
        for pat in (r"\breactivate\(", r"reactivated_since_attended\.add\(",
                    r"\.(statuses|recorded|last_probe|disposition)\[[^\]]*\]\s*=(?!=)"):
            scan += [f"{name}: {m.group(0)}" for m in re.finditer(pat, src)]
    return not probs and not scan, {"problems": probs, "code_scan": scan, "reactivations": len(react)}


def c19(x):
    rp = x.replay()
    first = c17(x)[1]["first_divergence"]
    if first is None:
        want = "Outcome 2"
    else:
        dv = x.j("replay/divergence.json")
        m1d = bool(act_diff(dv["m1_action"], accepted(first)))
        want = "Outcome 3" if m1d else "Outcome 1"
    ok = rp["outcome_reading"].startswith(want)
    return ok, {"reading": rp["outcome_reading"], "expected_prefix": want}


def c20(x):
    """Process: stages once in order from one clean pushed commit; zero renders; zero Blender processes."""
    log = ok_entries(x)
    cmds = [e["command"] for e in log if e["command"] in STAGES]
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] for e in log if e["command"] in STAGES)
    bad_cmds = [e["command"] for e in x.log() if e["command"] not in STAGES + ["visualize"]]
    attempts = {}
    for rel in GUARDED:
        pg = guard(x, rel).get("process_guard") or {}
        attempts[rel] = pg.get("attempts", None)
    syn = x.j("synthetic/synthetic-report.json")["process_guard"]["attempts"]
    renders = [str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.suffix.lower() in (".exr", ".blend", ".log")
               or (p.suffix.lower() == ".png")]
    mods = {}
    for rel in GUARDED:     # render / natural-stereo / SGBM modules (cv2 and fsg_stereo are accepted policy dependencies)
        mods.update({k: v for k, v in guard(x, rel)["modules_loaded"].items() if v and k in RENDER_MODULES})
    code = []
    for name in PRODUCTION:
        tree = ast.parse((HERE / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.lower() == "blender":
                code.append(f"{name}: blender literal")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and
                                                        node.module else [])
                code += [f"{name}: imports {n}" for n in names if any(t in n for t in ("render", "sgbm", "stereo"))]
    ok = (cmds == STAGES and clean and not bad_cmds and all(a == [] for a in attempts.values())
          and len(syn) == 1 and "blender" in syn[0] and not renders and not mods and not code)
    return ok, {"stages": cmds, "clean_pushed": clean, "unexpected_commands": bad_cmds, "attempts": attempts,
                "synthetic_self_test_attempts": syn, "render_files": renders[:5], "render_modules": mods,
                "code_scan": code}


def c21(x):
    """Truth boundary: no forbidden read; no North-Star truth read; historical truth only in known-answer (109)."""
    probs = []
    for rel in GUARDED:
        g = guard(x, rel)
        if g["violations"] or g["violations_count"]:
            probs.append(f"{rel}: violations")
        reads = g["data_reads"]
        fb = [p for p in reads if any(t in p for t in FORBIDDEN_READ)]
        if fb:
            probs.append(f"{rel}: forbidden {fb[:2]}")
        ns = [p for p in reads if "north-star" in p and any(t in p for t in NORTH_STAR_TRUTH)]
        if ns:
            probs.append(f"{rel}: North-Star truth {ns[:2]}")
        hist = [p for p in reads if "oracle_observation.npz" in p]
        if hist and (rel != "known-answer/known-answer-opened-files.json" or
                     any("instance_0109/acquisitions" not in p for p in hist)):
            probs.append(f"{rel}: historical oracle observations outside the 109 replay")
    return not probs, {"problems": probs[:6]}


def c22(x):
    """Terminology: memory != map; cross-target measured != fused; no ACCEPTED marker; divergent action NOT EXECUTED."""
    probs = []
    rep = REPO / REPORT_PATH
    if rep.exists():
        t = rep.read_text()
        if NS1D_ACCEPTED in t or NS1C_ACCEPTED in t:
            probs.append("an ACCEPTED marker in the report")
        if re.search(r"cross-target (memory|samples?|points?|measurements?) (is|are|were) fused", t, re.I):
            probs.append("cross-target memory called fused")
    rp = x.replay()
    if "memory" not in rp["statement"]:
        probs.append("replay statement")
    if x.has("replay/divergence.json") and x.j("replay/divergence.json")["m2_divergent_action"]["executed"]:
        probs.append("the divergent action claimed executed")
    if x.has("replay/final.json") and any(v.get("executed") for v in x.j("replay/final.json")["next_decisions"].values()):
        probs.append("a post-trace decision claimed executed")
    if any("deferred id" in str(lab).lower() for f in x.vis.glob("visuals-manifest.json")
           for lab in json.loads(f.read_text())["figures"].get("overview.png", {}).get("labels", [])):
        probs.append("'deferred id' wording")
    if "SCENE" + "_CLOSED" in json.dumps(rp):
        probs.append("scene-closure claim")
    return not probs, {"problems": probs}


def c23(x):
    import ns1d_visuals as V
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    probs = []
    with tempfile.TemporaryDirectory() as td:
        figs, dd = V.render_all(x.run)
        for name, (im, meta) in figs.items():
            p = Path(td) / name
            im.save(p, format="PNG", optimize=False)
            rec = man["figures"].get(name)
            if rec is None or sha256(p) != rec["sha256"] or sha256(x.vis / name) != rec["sha256"]:
                probs.append(f"{name}: not byte-identical")
            elif any(rec.get(k) != v for k, v in meta.items()):
                probs.append(f"{name}: meta differs")
    for name in FIGURES_ALWAYS:
        if name not in man["figures"]:
            probs.append(f"{name} missing")
    for name, labs in REQUIRED_LABELS.items():
        if name in man["figures"] and not set(labs) <= set(man["figures"][name]["labels"]):
            probs.append(f"{name}: required labels missing")
    ov = man["figures"].get("overview.png", {})
    if ov.get("panels") != ["A", "B", "C", "D", "E"] or not ov.get("source_active_target_shown") or \
            "NOT fused" not in man.get("memory_vs_map", "") and "never as fused" not in man.get("memory_vs_map", ""):
        probs.append("overview panels / source target / memory drawing")
    div = x.replay()["divergence"]
    if ov.get("divergence_shown") != div or ("decision-divergence.png" in man["figures"]) != div:
        probs.append("divergence presentation inconsistent")
    if ("reactivation.png" in man["figures"]) != bool(x.replay()["natural_reactivations"]):
        probs.append("reactivation figure inconsistent")
    return not probs, {"problems": probs[:6]}


def c24(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
        "manifest.json", "check-summary.json", "process-log.jsonl"}
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    fz = x.j("freeze/replay-freeze.json")
    fz_bad = [f for f, h in fz["files"].items() if sha256(x.run / f) != h]
    return not bad and set(man["files"]) == present and not extra and not fz_bad, {
        "mismatch": bad[:5], "unlisted": sorted(present - set(man["files"]))[:5], "undeclared_changes": extra,
        "replay_freeze_mismatch": fz_bad[:5]}


CHECKS = [
    ("01", "provenance: canonical repo, base, NS1c2 accepted on the base, contract first and unchanged, one commit", c01),
    ("02", "accepted code (measurement_memory.py, fov3d) unchanged; upstream manifests and history pinned", c02),
    ("03", "NS1c not accepted, not merged", c03),
    ("04", "synthetic known answers re-run: 20/20", c04),
    ("05", "historical known answer recomputed: 141-patch memory, 70.7 % cross-target, the 109 reactivation", c05),
    ("06", "event list: own derivation; 9 unique physical observations; targets, gazes, pins; no array opened", c06),
    ("07", "memory patches: own construction from the pinned products; exact valid counts; ids > 0 only", c07),
    ("08", "identity re-attached from instance_L at uv_L; attached after the geometry freeze; no Position in NS1d", c08),
    ("09", "memory: own rebuild with the accepted class; additions, provenance, digests; deterministic; all ids", c09),
    ("10", "M0 = accepted NS1c2: probes, fresh sets, decisions and events", c10),
    ("11", "M0 / M1 / M2 geometry sizes and revisions recomputed per entity and event", c11),
    ("12", "every fresh M1 / M2 probe recomputed from its context and own geometry (tolerance 0)", c12),
    ("13", "revision / cache: fresh probes exactly where the revision changed; cross additions never touch M1 / maps",
     c13),
    ("14", "own-look contexts: only the target gains a look; non-targets untouched; = accepted NS1c2 records", c14),
    ("15", "persistent maps: own re-fusion bitwise; untouched maps unchanged; no foreign id or patch", c15),
    ("16", "scheduler: the accepted schedule_normal on own statuses; coherent identity only; no names", c16),
    ("17", "divergence: located independently; the replay stopped there; no later observation opened", c17),
    ("18", "natural reactivation only through the adapter after a memory addition; no manual call", c18),
    ("19", "outcome reading consistent with the decisions", c19),
    ("20", "process: stages once in order, one clean pushed commit; zero renders / Blender processes", c20),
    ("21", "truth boundary: no forbidden or North-Star truth read; historical truth only for the 109 replay", c21),
    ("22", "terminology: memory != map; no ACCEPTED marker; nothing claimed executed", c22),
    ("23", "figures regenerate byte-identically; required labels; divergence / reactivation figures consistent", c23),
    ("24", "run manifest, replay freeze and declared changes", c24),
]


def run_checks(run: Path, vis: Path, only=None, quiet=False) -> dict:
    x = X(run, vis)
    out = {}
    for cid, title, fn in CHECKS:
        if only is not None and cid not in only:
            continue
        try:
            ok, detail = fn(x)
        except Exception as e:  # a crash is a failure of that check
            ok, detail = False, {"error": repr(e)}
        out[cid] = {"title": title, "pass": bool(ok), "detail": detail}
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {cid} {title}" + ("" if ok else " -- " + json.dumps(
                detail, default=str)[:700]), flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    res = run_checks(a.run, a.visuals, only=set(a.only.split(",")) if a.only else None)
    failed = [k for k, v in res.items() if not v["pass"]]
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(failed)}")
    summary = {"schema": "NS1d-check-summary-v1", "checks": res, "failed": failed,
               "marker": "NORTH_STAR1D_CHECKS_PASS" if not failed else "NORTH_STAR1D_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1D_CHECKS_PASS")
    if a.corruptions:
        import check_ns1d_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
