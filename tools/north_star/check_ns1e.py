#!/usr/bin/env python3
"""North Star-1e checker: fail-capable verification of the full coherent multi-entity loop with M2 memory (read-only).

    .venv/bin/python tools/north_star/check_ns1e.py --run RUN --visuals VIS [--corruptions] [--write-summary]
                                                    [--rehearsal]

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md, section 29 (and the amendment, section 36).
The checker keeps its own literal pins and recomputes independently wherever an independent formula exists: the
scheduler universe (own rule on the NS1a seed set), the charts (own construction), the memory (the accepted
``InstanceMeasurementMemory`` fed patches the checker builds itself from the frozen products), every revision, every
target-only fusion (the accepted surface map, own target patch), the spherical geometry (the accepted AB1b function on
the frozen product), the identity (own re-attachment), the whole Controller-02 trajectory (an independent re-drive of the
accepted SceneMachine from the handoff with the recorded probe results and own revisions), the hard cap (own formula) and
the post-control coverage (own EXR channel extraction, own frame transform, brute-force 12-mm distances).  The accepted
policy has no independent implementation: every fresh probe is recomputed from its reconstructed context and the
checker's own M2 geometry.  ``--rehearsal`` relaxes ONLY the physical render pins (spp, EXR samples, catalog seal,
rehearsal flag) and the clean-commit pins, for development rehearsal runs; it is never used on the canonical run.
"""
from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap",
           HERE.parent / "classroom_oracle", HERE.parent / "visual_language", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

PREFIX = "[ns1e-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
LEGACY_REMOTE = "fov-3d-vision"
BASE = "5aa223109ec829d41945f19b4c5223928fd0dde9"
NS1D_ACCEPTANCE = "25bb929b4d39e1e73cabf0df582bc3c5d3e45e06"
CONTRACT = "0728857de498e2b560def4e7233fefce2c222dfe"
CONTRACT_PATH = "docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md"
REPORT_PATH = "docs/north-star/ns1e-coherent-full-loop-m2-memory-report.md"
NS1D_REPORT = "docs/north-star/ns1d-cross-target-measurement-memory-report.md"
NS1D_ACCEPTED = "NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED"
NS1E_ACCEPTED = "NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_" + "ACCEPTED"
NS1E_COMPLETE = "NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_COMPLETE"
SHARED = Path("/home/lvelho/rd/f3d-vision")
NS1A = SHARED / "previews/north-star/ns1a-perfect-bootstrap-round"
NS1C2 = SHARED / "previews/north-star/ns1c2-controller02-phase-semantics"
NS1D = SHARED / "previews/north-star/ns1d-cross-target-measurement-memory"
B1_EXR = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr"
B1_SHA = "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8"
NS1D_MANIFEST = "2b5bd1726e291f8234b5ffc33d13b4afe0d930c4e9955da9aff1bf03e8848c6e"
NS1C2_MANIFEST = "0ec6228d96db1bfadc3372c3ce95342ddfa14f7ba2f11d24234c20ed59d2c8c1"
NS1A_SEED_SET = ("seeds/seed-set.json", "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a")
NS1A_GAZES = ("source/nb1c-gaze-list.json", "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062")
KEY_PINS = {"fov3d/control/controller02.py": "21c658a15ecb3f4f41dc73468a32f073df124eefd777c6c5e903bcf567bf8791",
            "fov3d/control/integrated.py": "b4a11fbee78b526726d86ffaeac08ae175818cecb7d7ca73688ab1447167b629",
            "fov3d/reconstruction/measurement_memory.py":
                "27471ebf7076e5a21b8d23be994425993115b5e379a4dd7f32b7fce09e52ab25",
            "fov3d/experiments/classroom_oracle/controller02.py":
                "b3fed8894b1a0fcce1bce097a22cbb69a52d43a145fdda3f19bd683e40d64242",
            "tools/north_star/ns1c2_phase.py": "99f6a3da750abe0654ee95085ff387dfbea961ed853f48e85d96fc2a2f6a8acc"}
COHERENT = [9, 12, 123, 129, 172, 202, 204, 212, 230, 231]
AMBIGUOUS = [10, 110, 178]
RANK1 = [9, 12, 204, 230, 231]
BUDGET = 24
HANDOFF_STEP = 8
NS1D_EVENTS = 9
MAX_NEW = 231
ABS_CAP = 239
OWN_LOOKS0 = {"9": 1, "12": 1, "123": 1, "129": 1, "172": 9, "202": 2, "204": 1, "212": 1, "230": 1, "231": 1}
MEMORY0 = 581882
NEXT0 = {"target": 202, "decision": "retain", "source": "fsg6f", "local_gaze_deg": [-10.899999999999999, 10.5],
         "world_gaze_deg": [-147.62774503449359, 15.922813864915128]}
SPP, SEEDS, DEVICE, IPD = 4096, {"L": 2111, "R": 2112}, "OPTIX", 0.063
EYES = [[-0.0315, 0.0, 0.0], [0.0315, 0.0, 0.0]]
CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
RADIUS = 0.012
STEP_STAGES = ["schedule", "preflight", "acquire", "freeze-observation", "perfect-correspondence",
               "freeze-correspondence", "spherical-geometry", "freeze-geometry", "local-oracle-segmentation",
               "freeze-identity", "fuse", "memory", "update"]
UPDATE_MARKS = ["fusion_freeze_verified", "memory_event_verified", "context_updated", "commit_begins",
                "refresh_complete"]
POLICY_GUARD = "fov3d.experiments.classroom_oracle.controller02.NoProcessGuard"
LIGHT_GUARD = "ns1e_core.ProcessGuard"
LIGHT_STAGES = {"freeze-observation", "perfect-correspondence", "freeze-correspondence", "spherical-geometry",
                "freeze-geometry", "local-oracle-segmentation", "freeze-identity", "fuse", "memory"}
CONTROL_FORBIDDEN = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                     "evaluation.json", "/evaluation/", "evaluation_only", "actions.json", "result.json",
                     "render-metadata.json", "breadth-1-classroom", "natural-bootstrap-1a", "natural-bootstrap-1b",
                     "controller-01-full", "controller-02-classroom-replay")
NAME_KEYS = {"object_name", "object_names", "instance_names", "names", "post_freeze_name", "target_name",
             "entity_name", "catalog"}
NS1E_FILES = ["tools/north_star/" + n for n in ("ns1e_spec.py", "ns1e_core.py", "ns1e_render.py", "ns1e_run.py",
                                                "ns1e_synthetic.py", "ns1e_visuals.py", "check_ns1e.py",
                                                "check_ns1e_corruptions.py")]
DECLARED = set(NS1E_FILES) | {CONTRACT_PATH, REPORT_PATH, "tools/repository/check_repository_layout.py"}
FIGURES_ALWAYS = ["overview.png", "controller-full-timeline.png", "multi-entity-final-geometry.png",
                  "memory-flow-timeline.png", "coverage-by-entity.png", "rank1-diagnostic.png"]
REQUIRED_LABELS = {"overview.png": ["AMBIGUOUS ORACLE ID - EXCLUDED", "ORACLE CORRESPONDENCE", "ORACLE SEGMENTATION AID",
                                    "NON-COMPARABLE HISTORICAL REFERENCE",
                                    "MEASURED EFFECTIVE GEOMETRY - NOT PERSISTENT RECONSTRUCTION",
                                    "INSTANCE MEASUREMENT MEMORY (measured samples, NOT fused surfels)",
                                    "PERSISTENT SURFACE MAP (target-only fusion)",
                                    "PHYSICAL HEAD FIXED - POLICY CHART ONLY"],
                   "coverage-by-entity.png": ["NON-COMPARABLE HISTORICAL REFERENCE",
                                              "MEASURED EFFECTIVE GEOMETRY - NOT PERSISTENT RECONSTRUCTION"]}


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


def jload(path):
    return json.loads(Path(path).read_text())


class X:
    """The run under check (possibly a corruption mirror), with caches."""

    def __init__(self, run: Path, vis: Path, rehearsal: bool = False) -> None:
        self.run, self.vis, self.rehearsal = Path(run), Path(vis), rehearsal
        self._j, self.memo = {}, {}

    def j(self, rel: str):
        if rel not in self._j:
            self._j[rel] = json.loads((self.run / rel).read_text())
        return self._j[rel]

    def has(self, rel: str) -> bool:
        return (self.run / rel).exists()

    def log(self) -> list[dict]:
        return [json.loads(ln) for ln in (self.run / "process-log.jsonl").read_text().splitlines() if ln.strip()]

    def ref(self, ref: str) -> Path:
        scheme, rel = ref.split(":", 1)
        return {"run": self.run, "ns1a": NS1A, "ns1b": SHARED / "previews/north-star/ns1b-recentered-controller-handoff",
                "ns1c": SHARED / "previews/north-star/ns1c-coherent-first-scene-switch", "ns1c2": NS1C2,
                "ns1d": NS1D}[scheme] / rel

    def initial(self) -> dict:
        return self.j("scene/state-initial.json")

    def steps(self) -> list[int]:
        if "steps" not in self.memo:
            out, k = [], HANDOFF_STEP
            while (self.run / f"freeze/checkpoint-step-{k:03d}.json").exists():
                out.append(k)
                k += 1
            self.memo["steps"] = out
        return self.memo["steps"]

    def sd(self, k: int) -> str:
        return f"steps/step-{k:03d}"

    def dec(self, k: int) -> dict:
        return self.j(f"{self.sd(k)}/plan/decision.json")

    def state(self, k: int) -> dict:
        return self.j(f"scene/state-after-step-{k:03d}.json")

    def before(self, k: int) -> dict:
        return self.initial() if k == HANDOFF_STEP else self.state(k - 1)

    def final(self) -> dict:
        st = self.steps()
        return self.state(st[-1]) if st else self.initial()

    def terminal(self) -> dict | None:
        return self.j("scene/terminal.json") if self.has("scene/terminal.json") else None

    def charts(self) -> dict:
        return self.j("handoff/charts.json")["charts"]

    def ns1d_patch(self, e: int) -> dict:
        key = ("ns1d_patch", e)
        if key not in self.memo:
            self.memo[key] = load(NS1D / f"replay/events/event-{e:02d}/memory-patch.npz")
        return self.memo[key]

    def own_patch(self, k: int) -> dict:
        """The memory patch of step k, built here from the frozen products (no NS1e function)."""
        key = ("own_patch", k)
        if key not in self.memo:
            sd = self.run / self.sd(k)
            prod = load(sd / "correspondence/oracle-correspondences.npz")
            geo = load(sd / "geometry/epipolar-result.npz")
            idn = load(sd / "segmentation/local-identity.npz")
            rows, cols = prod["left_core_row"].astype(np.int64), prod["left_core_col"].astype(np.int64)
            p = np.asarray(geo["P_epi"], np.float64)
            meas = np.asarray(geo["valid_epi"], bool) & np.isfinite(p).all(axis=1)
            ids = np.asarray(idn["temporary_entity_id"], np.int64)
            keep = meas & (ids > 0)
            xyz = np.full((256, 256, 3), np.nan, np.float32)
            xyz[rows[meas], cols[meas]] = p[meas].astype(np.float32)
            inst = np.zeros((256, 256), np.int32)
            inst[rows[keep], cols[keep]] = ids[keep].astype(np.int32)
            val = np.zeros((256, 256), bool)
            val[rows[keep], cols[keep]] = True
            self.memo[key] = {"xyz_h": xyz, "instance_id": inst, "valid": val}
        return self.memo[key]

    def ledgers(self) -> dict:
        """Own memory after every event: the accepted class fed the NS1d patches and the checker's own NS1e patches;
        returns {event: (memory, measured_points)} snapshots by reference to one incrementally built memory."""
        if "ledger" not in self.memo:
            from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory
            mem = InstanceMeasurementMemory()
            measured, by_event = {}, {}
            el = jload(NS1D / "events/event-list.json")["events"]
            for e in range(NS1D_EVENTS):
                adds = mem.append_patch(self.ns1d_patch(e), source_global_index=e,
                                        source_active_target_id=int(el[e]["target"]))
                for kk, v in adds.items():
                    measured[kk] = measured.get(kk, 0) + v
                by_event[e] = (dict(measured), adds)
            for k in self.steps():
                e = k + 1
                t = int(self.dec(k)["action"]["target"])
                adds = mem.append_patch(self.own_patch(k), source_global_index=e, source_active_target_id=t)
                for kk, v in adds.items():
                    measured[kk] = measured.get(kk, 0) + v
                by_event[e] = (dict(measured), adds)
            self.memo["ledger"] = (mem, by_event)
        return self.memo["ledger"]


def code_commits(x: X, visualize: bool = False) -> set:
    """The commits of the canonical stages (control + evaluation); ``visualize`` may follow from a later presentation-only
    commit (contract section 32 b)."""
    return {e["code"]["commit"] for e in x.log() if e["status"] == "ok" and not e.get("dev")
            and (e["command"] == "visualize") == visualize}


# ======================================================================== the checks
def c01(x):
    """Provenance."""
    probs = []
    origin = git("remote", "get-url", "origin")
    if CANONICAL_REMOTE not in origin or LEGACY_REMOTE in origin:
        probs.append(f"origin {origin}")
    for name, sha in (("base", BASE), ("ns1d acceptance", NS1D_ACCEPTANCE), ("contract", CONTRACT)):
        if not ancestor(sha):
            probs.append(f"{name} not an ancestor")
    if subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode != 0:
        probs.append("contract changed since its commit")
    t = git("show", f"{BASE}:{NS1D_REPORT}")
    if NS1D_ACCEPTED not in t or "**Status: ACCEPTED.**" not in t:
        probs.append("NS1d not ACCEPTED on the base")
    src = x.j("source/source-manifest.json")
    if src["contract_commit"] != CONTRACT or src["base_commit"] != BASE:
        probs.append("source manifest pins")
    commits = code_commits(x)
    if not x.rehearsal:
        if len(commits) != 1:
            probs.append(f"canonical stages ran from {len(commits)} commits")
        else:
            c = next(iter(commits))
            if not ancestor(CONTRACT, c) or c == CONTRACT or not ancestor(c):
                probs.append("the implementation commit does not follow the contract / is not in the checked tree")
        bad = [e["command"] for e in x.log() if e["status"] == "ok" and (e["code"]["dirty"] or not e["code"]["pushed"])]
        if bad:
            probs.append(f"stages from a dirty / unpushed tree: {bad[:3]}")
        vis = code_commits(x, visualize=True)
        if commits and any(not ancestor(next(iter(commits)), v) or not ancestor(v) for v in vis):
            probs.append("visualize ran from a commit that does not descend from the implementation commit")
    return not probs, {"problems": probs, "commits": sorted(commits)}


def c02(x):
    """Accepted code unchanged; NS1e's light process guard has the accepted audit events."""
    probs = []
    if subprocess.run(["git", "diff", "--quiet", BASE, "--", "fov3d"], cwd=REPO).returncode != 0:
        probs.append("fov3d changed since the base")
    for p, h in KEY_PINS.items():
        if sha256(REPO / p) != h:
            probs.append(f"{p} changed")
    import ns1e_spec as SP
    bad = [p for p, h in SP.SOURCE_PINS.items() if sha256(REPO / p) != h]
    if bad:
        probs.append(f"pinned sources changed: {bad[:3]}")
    import ns1e_core as CORE
    from fov3d.experiments.classroom_oracle.controller02 import NoProcessGuard
    if tuple(CORE.ProcessGuard.EVENTS) != tuple(NoProcessGuard.EVENTS):
        probs.append("ns1e_core.ProcessGuard events differ from the accepted NoProcessGuard")
    return not probs, {"problems": probs}


def c03(x):
    """Synthetic known answers re-run."""
    import ns1e_synthetic as SY
    rep = SY.run_all()
    rec = x.j("synthetic/synthetic-report.json")
    ok = not rep["failed"] and rep["count"] >= 20 and not rec["failed"] and \
        sorted(k for k, v in rec["tests"].items() if v["pass"]) == sorted(k for k, v in rep["tests"].items() if v["pass"])
    return ok, {"failed_now": rep["failed"], "failed_recorded": rec["failed"], "count": rep["count"]}


def c04(x):
    """Handoff: own memory from the NS1d patches; the frozen NS1d M2 machine; the next decision; the start state."""
    import ns1c2_phase as PH
    probs = []
    if sha256(NS1D / "manifest.json") != NS1D_MANIFEST:
        probs.append("NS1d manifest")
    man = jload(NS1D / "manifest.json")["files"]
    for e in range(NS1D_EVENTS):
        rel = f"replay/events/event-{e:02d}/memory-patch.npz"
        if sha256(NS1D / rel) != man.get(rel):
            probs.append(f"NS1d patch {e}")
    _mem, by = x.ledgers()
    measured0 = by[NS1D_EVENTS - 1][0]
    s8 = jload(NS1D / "replay/state-after-event-08.json")
    if sum(measured0.values()) != MEMORY0 or {str(k): v for k, v in sorted(measured0.items())} != \
            s8["memory"]["measured_points"]:
        probs.append("own NS1d memory rebuild differs")
    init = x.initial()
    if init["memory"]["measured_points"] != {str(k): v for k, v in sorted(measured0.items())}:
        probs.append("initial-state memory differs from the own rebuild")
    el = jload(NS1D / "events/event-list.json")["events"]
    want_rows = [{"event": e, "target": int(el[e]["target"]), "observation_key": el[e]["observation_freeze_sha256"],
                  "patch": f"ns1d:replay/events/event-{e:02d}/memory-patch.npz",
                  "patch_sha256": man.get(f"replay/events/event-{e:02d}/memory-patch.npz"),
                  "additions": {str(kk): v for kk, v in sorted(by[e][1].items())}} for e in range(NS1D_EVENTS)]
    got_rows = [{kk: r.get(kk) for kk in ("event", "target", "observation_key", "patch", "patch_sha256", "additions")}
                for r in init["memory"]["events"]]
    if got_rows != want_rows:
        probs.append("the initial memory event list is not the nine accepted NS1d events")
    md, mi = s8["machines"]["M2"], init["machine"]
    for f in ("order", "budget", "disposition", "fixations", "statuses", "recorded", "phase", "current", "bout",
              "step", "quiet_since", "reactivated_since_attended", "terminal", "phases"):
        if json.dumps(md[f], sort_keys=True) != json.dumps(mi[f], sort_keys=True):
            probs.append(f"machine field {f}")
    if {k: v["revision"] for k, v in md["cache"].items()} != {k: v["revision"] for k, v in mi["cache"].items()}:
        probs.append("machine cache revisions")
    dry = PH.SceneMachine.from_json(json.loads(json.dumps(mi)))
    plan = dry.decide(lambda i, p: (_ for _ in ()).throw(RuntimeError("gate in NORMAL")))
    a = plan.get("action")
    got = {"target": plan.get("target_id"), "decision": plan.get("decision"), "source": a.source if a else None,
           "local_gaze_deg": list(a.gaze_yaw_pitch_deg) if a else None}
    want = {k: NEXT0[k] for k in got}
    if got != want:
        probs.append(f"next decision {got}")
    fin = jload(NS1D / "replay/final.json")["next_decisions"]["M2"]
    if [fin[k] for k in ("target", "source", "local_gaze_deg", "world_gaze_deg")] != \
            [NEXT0[k] for k in ("target", "source", "local_gaze_deg", "world_gaze_deg")]:
        probs.append("NS1d frozen next decision differs from the literal")
    if (x.steps() and x.dec(HANDOFF_STEP)["kind"] == "attend"
            and x.dec(HANDOFF_STEP)["action"]["world_gaze_deg"] != NEXT0["world_gaze_deg"]):
        probs.append("the first executed action is not the reproduced next decision")
    own = {k: v["own_looks"] for k, v in init["entities"].items()}
    if own != OWN_LOOKS0 or init["current"] != 202 or init["entities"]["172"]["status"]["label"] != "QUIET" or \
            init["next_global_step"] != HANDOFF_STEP or mi["quiet_since"] != {"172": 6}:
        probs.append("start state")
    st7 = jload(NS1C2 / "scene/state-after-step-07.json")
    for kk, rec in init["entities"].items():
        acc = st7["entities"][kk]
        if rec["map"]["sha256"] != acc["map"]["sha256"] or sha256(x.ref(rec["map"]["path"])) != acc["map"]["sha256"]:
            probs.append(f"entity {kk}: initial map is not the accepted NS1c2 final map")
        for f in ("own_looks", "visited", "current_local_gaze"):
            if rec[f] != acc[f] or rec[f] != s8["contexts"][kk][f]:
                probs.append(f"entity {kk}: {f} is not the accepted NS1c2 / NS1d context")
        if [lk["state_sha256"] for lk in rec["looks"]] != [lk["state_sha256"] for lk in acc["looks"]] or \
                rec["evidence"]["sha256"] != acc["evidence"]["sha256"]:
            probs.append(f"entity {kk}: looks / evidence differ from NS1c2")
    h = x.j("handoff/handoff.json")
    if not h["ok"] or h["problems"]:
        probs.append("handoff record not ok")
    return not probs, {"problems": probs[:8], "next": got}


def c05(x):
    """Eligibility (own rule) and no names."""
    probs = []
    if sha256(NS1A / NS1A_SEED_SET[0]) != NS1A_SEED_SET[1]:
        probs.append("NS1a seed set changed")
    ss = jload(NS1A / NS1A_SEED_SET[0])
    coh = sorted(int(e["temporary_entity_id"]) for e in ss["entities"] if e["initialized"]
                 and int(e["contributing_patches"]) == 1)
    amb = sorted(int(e["temporary_entity_id"]) for e in ss["entities"] if e["initialized"]
                 and int(e["contributing_patches"]) > 1)
    if coh != COHERENT or amb != AMBIGUOUS:
        probs.append(f"derived {coh} / {amb}")
    if [int(i) for i in x.initial()["scene_ids"]] != COHERENT:
        probs.append("scene ids")
    machine_ids = sorted(int(i) for i in x.final()["machine"]["order"])
    if machine_ids != COHERENT:
        probs.append("machine order")
    # the checker (post hoc, not control) may open one sealed catalog: no JSON string value of the run is an object name
    cats = sorted(x.run.glob("steps/step-*/observation/evaluation_only/instance-catalog.json"))
    names = {e["object_name"] for e in jload(cats[0])["instances"]} if cats else set()
    named, keyed = [], []
    for p in sorted(x.run.rglob("*.json")):
        if "evaluation_only" in str(p):
            continue

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if str(k).lower() in NAME_KEYS:
                        keyed.append(str(p.relative_to(x.run)))
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str) and o in names:
                named.append(str(p.relative_to(x.run)))
        walk(json.loads(p.read_text()))
    if keyed or named:
        probs.append(f"name keys {sorted(set(keyed))[:2]} / object names {sorted(set(named))[:2]}")
    if not x.rehearsal and len(names) != 234:
        probs.append(f"sealed catalog not available for the name scan ({len(names)})")
    return not probs, {"problems": probs, "catalog_names_scanned": len(names)}


def own_chart(gaze_deg) -> np.ndarray:
    y, p = map(math.radians, gaze_deg)
    g = np.array([math.cos(p) * math.sin(y), math.sin(p), -math.cos(p) * math.cos(y)])
    b = np.array([1.0, 0.0, 0.0])
    xc = b - float(b @ g) * g
    xc /= np.linalg.norm(xc)
    zc = -g
    yc = np.cross(zc, xc)
    yc /= np.linalg.norm(yc)
    return np.stack([xc, yc, zc], 1)


def c06(x):
    """Charts: own construction at the ORIGINAL NS1a gaze; constant everywhere; every probe used its entity chart."""
    probs = []
    gl = {int(g["rank"]): (float(g["yaw_deg"]), float(g["pitch_deg"]))
          for g in jload(NS1A / NS1A_GAZES[0])["gazes"]}
    ranks = {int(e["temporary_entity_id"]): int(e["initialized_at_rank"]) for e in jload(NS1A / NS1A_SEED_SET[0])["entities"]
             if e["initialized"]}
    chs = x.charts()
    c2 = jload(NS1C2 / "charts/policy-charts.json")["charts"]
    for i in COHERENT:
        r = np.asarray(chs[str(i)]["R_HC"], np.float64)
        mine = own_chart(gl[ranks[i]])
        if np.abs(r - mine).max() > 1e-12 or np.abs(r.T @ r - np.eye(3)).max() > 1e-12 or \
                abs(np.linalg.det(r) - 1) > 1e-12 or chs[str(i)]["R_HC_sha256"] != c2[str(i)]["R_HC_sha256"]:
            probs.append(f"chart {i}")
    shas = {str(i): chs[str(i)]["R_HC_sha256"] for i in COHERENT}
    for k in [None] + x.steps():
        st = x.initial() if k is None else x.state(k)
        for kk, rec in st["entities"].items():
            if rec["chart_sha256"] != shas[kk]:
                probs.append(f"entity {kk} chart changed at {k}")
    files = sorted(x.run.glob("handoff/probes/e*.json")) + sorted(x.run.glob("steps/step-*/update/probes/e*.json"))
    for f in files:
        pr = jload(f)
        r = np.asarray(pr["probe"]["adapter"]["R_HC"], np.float64)
        if r.tobytes() != np.asarray(chs[str(pr["entity"])]["R_HC"], np.float64).tobytes():
            probs.append(f"{f.name}: probe adapter chart differs")
            break
    return not probs, {"problems": probs[:6], "probe_files": len(files)}


def c07(x):
    """Physical sensor: every executed calibration is the real fixed-head sensor at the world gaze of the local plan."""
    import ns1b_core as B
    probs = []
    c0 = jload(NS1A / "observations/rank-01/acquisition/calibration.json")
    hr, ho = np.asarray(c0["head_R_wh"]), np.asarray(c0["head_origin_w_m"])
    chs = x.charts()
    for k in x.steps():
        d = x.dec(k)
        cal = jload(x.run / x.sd(k) / "observation/acquisition/calibration.json")
        r = np.asarray(chs[str(d["action"]["target"])]["R_HC"], np.float64)
        y, p = map(math.radians, d["action"]["local_gaze_deg"])
        dl = np.array([math.cos(p) * math.sin(y), math.sin(p), -math.cos(p) * math.cos(y)])
        dw = r @ dl
        yw, pw = math.degrees(math.atan2(dw[0], -dw[2])), math.degrees(math.atan2(dw[1], math.hypot(dw[0], dw[2])))
        cent = [e["centre_h_m"] for e in cal["eyes"]]
        if (np.abs(np.asarray(cent) - EYES).max() > 1e-12 or abs(cal["ipd_m"] - IPD) > 1e-12
                or np.abs(np.asarray(cal["head_R_wh"]) - hr).max() or np.abs(np.asarray(cal["head_origin_w_m"]) - ho).max()
                or cal.get("tangent_frame") != "baseline_projected"
                or max(abs(yw - d["action"]["world_gaze_deg"][0]), abs(pw - d["action"]["world_gaze_deg"][1])) > 1e-9
                or list(cal["gaze_yaw_pitch_deg"]) != list(d["action"]["world_gaze_deg"])):
            probs.append(f"step {k}: calibration / world gaze")
        t = B.physical_calibration_test(cal, d["action"]["local_gaze_deg"], r, hr, ho)
        if not t["ok"]:
            probs.append(f"step {k}: physical calibration test")
    return not probs, {"problems": probs[:6], "steps": len(x.steps())}


def verdict_detail(r: dict) -> dict:
    """The verdict detail the run's gate adapter returned ({"record": detail}), from its recorded gate record."""
    return {"record": {k: v for k, v in r.items() if k not in ("object", "phase", "global_step", "revision")}}


def own_revision(x: X, rec: dict, measured: dict) -> list[int]:
    return [int(rec["own_looks"]), int(measured.get(int(rec["temporary_entity_id"]), 0))]


def c08(x):
    """Controller: an independent re-drive of the accepted SceneMachine from the handoff reproduces every decision, every
    event, every checkpoint machine and the terminal; NORMAL gate calls 0."""
    import ns1c2_core as C2
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2, integrated as ic
    probs = []
    m = PH.SceneMachine.from_json(json.loads(json.dumps(x.initial()["machine"])))
    _mem, by = x.ledgers()
    for k in x.steps():
        d = x.dec(k)
        m = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json())))      # the schedule process boundary
        recs = iter(d.get("residue_gate_records") or [])
        calls = []

        def gate(i, proposal):
            r = next(recs)
            calls.append(int(i))
            if int(r["object"]) != int(i) or list(proposal.action.gaze_yaw_pitch_deg) != r["proposal"]["local_gaze_deg"] \
                    or proposal.action.source != r["proposal"]["source"] or m.phase.value != "RESIDUE":
                probs.append(f"step {k}: gate call {i} not as recorded")
            if proposal is not m.last_probe[int(i)]:
                probs.append(f"step {k}: the gate did not receive the unchanged cached proposal")
            return c2.FinalProbeDecision(bool(r["admissible"]), r["reason"], verdict_detail(r))
        plan = m.decide(gate, ABS_CAP)
        if calls != [int(r["object"]) for r in d.get("residue_gate_records") or []]:
            probs.append(f"step {k}: gate calls {calls}")
        a = plan.get("action")
        mine = [plan["kind"], plan.get("target_id"), plan.get("decision"), plan.get("reason"),
                plan.get("attention_bout"), plan.get("phase"), list(a.gaze_yaw_pitch_deg) if a else None,
                a.source if a else None]
        rec = [d["kind"], d["action"]["target"], d["action"]["decision"], d["action"]["reason"], d["attention_bout"],
               d["action"]["phase"], d["action"]["local_gaze_deg"], d["action"]["source"]]
        if mine != rec:
            probs.append(f"step {k}: decision {mine} != {rec}")
            break
        if json.dumps(m.to_json(), sort_keys=True) != json.dumps(d["machine_after_decide"], sort_keys=True):
            probs.append(f"step {k}: machine after decide differs")
            break
        st = x.state(k)
        measured = by[k + 1][0]
        ents = st["entities"]
        called = []

        def probe(i):
            called.append(int(i))
            f = x.run / x.sd(k) / f"update/probes/e{int(i):05d}.json"
            pr = jload(f)
            if pr["revision"] != own_revision(x, ents[str(i)], measured):
                probs.append(f"step {k}: probe {i} revision")
            return C2.probe_result(pr["probe"], int(i), {"probe_path": f"run:{x.sd(k)}/update/probes/e{int(i):05d}.json",
                                                         "revision": pr["revision"]})
        m = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json())))      # the update process boundary
        plan = {**plan, "before": PH.status_from_json(PH.status_to_json(plan["before"]))}
        n_ev = len(m.events)
        m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe,
                 lambda i: own_revision(x, ents[str(i)], measured))
        if sorted(called) != sorted(st["fresh_probes"]):
            probs.append(f"step {k}: fresh probes {sorted(called)} != {st['fresh_probes']}")
        if json.dumps(m.to_json(), sort_keys=True) != json.dumps(st["machine"], sort_keys=True):
            probs.append(f"step {k}: checkpoint machine differs")
            break
        evs = d.get("events_in_decide", []) + m.events[n_ev:]
        if json.dumps(C2.jsonable(evs), sort_keys=True) != json.dumps(st["events"], sort_keys=True):
            probs.append(f"step {k}: events differ")
    term = x.terminal()
    if term is not None and not probs:
        kt = int(term["global_step"])
        if kt != (x.steps()[-1] + 1 if x.steps() else HANDOFF_STEP):
            probs.append("terminal step")
        recs = iter(term.get("residue_gate_records") or [])
        m = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json())))

        def gate_t(i, proposal):
            r = next(recs)
            if int(r["object"]) != int(i) or proposal is not m.last_probe[int(i)] or m.phase.value != "RESIDUE" or \
                    list(proposal.action.gaze_yaw_pitch_deg) != r["proposal"]["local_gaze_deg"] or \
                    proposal.action.source != r["proposal"]["source"]:
                probs.append(f"terminal: gate call {i} not as recorded / not the unchanged proposal")
            return c2.FinalProbeDecision(bool(r["admissible"]), r["reason"], verdict_detail(r))
        plan = m.decide(gate_t, ABS_CAP)
        if plan["kind"] != term["kind"] or json.dumps(m.to_json(), sort_keys=True) != \
                json.dumps(term["machine_after_decide"], sort_keys=True):
            probs.append("terminal decision differs")
    for rel in ["handoff/handoff.json"] + [f"{x.sd(k)}/plan/decision.json" for k in x.steps()] + \
               [f"{x.sd(k)}/update/update.json" for k in x.steps()]:
        gg = x.j(rel)["gate_guard"]
        if gg["normal_calls"] or gg["refused"]:
            probs.append(f"{rel}: a NORMAL gate call")
    return not probs, {"problems": probs[:8], "steps": len(x.steps()), "terminal": None if term is None else term["kind"]}


def c09(x):
    """Every fresh M2 probe recomputed from its reconstructed context and the checker's own M2 geometry (tolerance 0)."""
    import ns1b_chart as CH
    import ns1c2_core as C2
    import ns1e_core as CORE
    from fov3d.reconstruction.measurement_memory import effective_target_geometry
    CH.ensure_policy_modules()
    probs, n = [], 0
    mem_all, by = x.ledgers()
    chs = x.charts()
    # rebuild a memory per checkpoint lazily by replaying patches up to event e (own patches)
    from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory
    el = jload(NS1D / "events/event-list.json")["events"]
    mem = InstanceMeasurementMemory()
    for e in range(NS1D_EVENTS):
        mem.append_patch(x.ns1d_patch(e), source_global_index=e, source_active_target_id=int(el[e]["target"]))
    jobs = [(None, x.initial(), sorted(x.run.glob("handoff/probes/e*.json")))]
    jobs += [(k, x.state(k), sorted((x.run / x.sd(k) / "update/probes").glob("e*.json"))) for k in x.steps()]
    for k, st, files in jobs:
        if k is not None:
            mem.append_patch(x.own_patch(k), source_global_index=k + 1,
                             source_active_target_id=int(x.dec(k)["action"]["target"]))
        for f in files:
            pr = jload(f)
            i = int(pr["entity"])
            rec = st["entities"][str(i)]
            ctx = CORE.context_from_record(rec, x.run)
            mp = load(x.ref(rec["map"]["path"]))["xyz_h"]
            g = effective_target_geometry(np.asarray(mp, np.float64), mem.snapshot(i).xyz_h)
            r = np.asarray(chs[str(i)]["R_HC"], np.float64)
            out = C2.probe_normal_ctx(ctx, CH.to_chart(g, r), r, np.asarray(chs[str(i)]["g0_H0"], np.float64), "check")
            d = C2.policy_comparison(pr["probe"], C2.jsonable(out), 0.0)
            if d or pr["probe"]["geometry_h0_points"] != len(g) or out["adapter"]["calls"]["P3"]:
                probs.append(f"{f.relative_to(x.run)}: {d[:2]}")
            n += 1
    return not probs, {"problems": probs[:6], "probes_recomputed": n}


def c10(x):
    """Gate: no call outside RESIDUE anywhere; residue gate calls use the real fixed-head sensor at the mapped gaze."""
    probs = []
    recs = [g for k in x.steps() for g in x.dec(k).get("residue_gate_records") or []]
    term = x.terminal()
    recs += list((term or {}).get("residue_gate_records") or [])
    for g in recs:
        if g["phase"] != "RESIDUE":
            probs.append(f"gate record outside RESIDUE ({g['object']})")
        for p3 in g["adapter"]["p3"]:
            if max(abs(a - b) for a, b in zip(p3["world_gaze_deg"], g["proposal"]["world_gaze_deg"])) > 1e-12 or \
                    p3["tangent_frame"] != "baseline_projected":
                probs.append(f"gate {g['object']}: P3 not the real sensor at the mapped gaze")
        if g["proposal"]["source"] == "fsg6f" and not g["adapter"]["p3"] and g["reason"] != "untraceable_final_support":
            probs.append(f"gate {g['object']}: FSG6f proposal not traced")
        if g["adapter"]["sensor"] != "north_star_sensor":
            probs.append(f"gate {g['object']}: sensor {g['adapter']['sensor']}")
    gh = x.j("gate-harness/gate-harness.json")
    if not gh["ok"] or any(r["gate_guard_residue"]["normal_calls"] for r in gh["entities"]):
        probs.append("gate harness")
    return not probs, {"problems": probs[:6], "residue_gate_calls": len(recs)}


def c11(x):
    """Budget 24 live; deferral only for ACTIONABLE NORMAL at 24 own looks; never BLOCKED."""
    from fov3d.experiments.classroom_oracle import controller02 as x2
    probs = []
    if int(x2.BUDGET) != BUDGET or int(x.initial()["machine"]["budget"]) != BUDGET:
        probs.append("budget")
    for k in x.steps():
        for e in x.state(k)["events"]:
            if e["event"] == "deferred" and (e["fixations"] != BUDGET or e["local_state"] != "ACTIONABLE"):
                probs.append(f"step {k}: deferral {e}")
        if "BLOCKED" in json.dumps(x.state(k)["machine"]["statuses"]):
            probs.append(f"step {k}: BLOCKED")
    return not probs, {"problems": probs[:6]}


def c12(x):
    """Revision = (own looks, measured points of the observed id) at every checkpoint; never the map surfel count."""
    probs = []
    _m, by = x.ledgers()
    for k in [None] + x.steps():
        st = x.initial() if k is None else x.state(k)
        measured = by[NS1D_EVENTS - 1 if k is None else k + 1][0]
        for kk, rec in st["entities"].items():
            if rec["revision"] != own_revision(x, rec, measured):
                probs.append(f"{k}: entity {kk} revision {rec['revision']}")
            cache = st["machine"]["cache"].get(kk)
            if cache is not None and cache["revision"] != rec["revision"]:
                probs.append(f"{k}: entity {kk} cache key {cache['revision']} != revision")
    return not probs, {"problems": probs[:6]}


def c13(x):
    """Observation: one plan freeze before each render; one render per step; the North-Star render standard."""
    probs = []
    log = [e for e in x.log() if e.get("step") is not None and e["status"] == "ok"]
    for k in x.steps():
        sd = x.run / x.sd(k)
        fz = jload(sd / "freeze/plan-freeze.json")
        if any(sha256(sd / f) != h for f, h in fz["files"].items()):
            probs.append(f"step {k}: plan freeze")
        acq = [e for e in log if e["step"] == k and e["command"] == "acquire"]
        sch = [e for e in log if e["step"] == k and e["command"] == "schedule"]
        if len(acq) != 1 or len(sch) != 1 or sch[0]["finished_utc"] > acq[0]["started_utc"]:
            probs.append(f"step {k}: acquire {len(acq)} / plan order")
        ar = jload(sd / "observation/acquisition-run.json")
        rec = jload(sd / "observation/acquisition/acquisition.json")
        s = rec["settings"]
        if (rec["render_seeds_lr"] != SEEDS or rec["device"] != DEVICE or s["denoising"] is not False
                or s["adaptive_sampling"] is not False or s["pixel_filter"] != "BOX" or s["filter_width"] != 1.0):
            probs.append(f"step {k}: render settings")
        if not x.rehearsal and (ar["spp"] != SPP or ar["exr_samples_lr"] != {"L": str(SPP), "R": str(SPP)}
                                or ar["catalog_seal"]["sha256"] != CATALOG_SEAL or rec.get("rehearsal")):
            probs.append(f"step {k}: spp / EXR samples / catalog seal")
        if (sd / "observation/acquisition/calibration.json").read_bytes() != (sd / "plan/planned-calibration.json").read_bytes():
            probs.append(f"step {k}: executed calibration != planned")
    return not probs, {"problems": probs[:6]}


def c14(x):
    """Measurement: freeze order; geometry recomputed (accepted AB1b on the frozen product); identity re-attached here."""
    import ab1b_geometry as BG
    probs = []
    for k in x.steps():
        sd = x.run / x.sd(k)
        cal = jload(sd / "observation/acquisition/calibration.json")
        prod = BG.load_product(sd / "correspondence/oracle-correspondences.npz")
        r_ = BG.compute_epipolar(cal, prod)
        saved = load(sd / "geometry/epipolar-result.npz")
        if set(r_) != set(saved) or any(not np.array_equal(np.asarray(r_[q]), saved[q], equal_nan=saved[q].dtype.kind == "f")
                                         for q in saved):
            probs.append(f"step {k}: geometry not reproduced")
        ref = load(sd / "observation/oracle_aid/reference-observation.npz")
        uv = np.asarray(prod["uv_L"], np.float64).astype(np.int64)
        ids = np.where(saved["valid_epi"], ref["instance_L"][uv[:, 1], uv[:, 0]], -1) if len(uv) else np.zeros(0, int)
        idn = load(sd / "segmentation/local-identity.npz")
        if not np.array_equal(ids.astype(np.int32), idn["temporary_entity_id"]):
            probs.append(f"step {k}: identity re-attachment differs")
        gr = jload(sd / "geometry/geometry-opened-files.json")
        if gr["position_reads"] or gr["object_index_reads"] or len(gr["data_reads"]) != 2 or gr["violations"]:
            probs.append(f"step {k}: geometry read truth")
        sr = jload(sd / "segmentation/segmentation-opened-files.json")
        marks = [e["label"] for e in sr["events"] if e.get("event") == "mark"]
        if marks[:2] != ["geometry_freeze_verified", "identity_access_begins"] or \
                sr["reference_members_read"] != ["instance_L"]:
            probs.append(f"step {k}: identity order / members")
        for stage, rel in (("fuse", "fusion/fusion-opened-files.json"), ("memory", "memory/memory-opened-files.json")):
            rr = jload(sd / rel)
            if any(p.endswith(("reference-observation.npz", ".exr")) for p in rr["data_reads"]):
                probs.append(f"step {k}: {stage} read the oracle aid")
        for rel in ("correspondence/correspondence-opened-files.json", "geometry/geometry-opened-files.json"):
            ml = jload(sd / rel)["modules_loaded"]
            if ml["cv2"] or ml["fsg_stereo"] or ml["ab1d3_sgbm"] or ml["ab1d_match"] or ml["ab1a_stereo"]:
                probs.append(f"step {k}: stereo / SGBM module loaded in {rel}")
    return not probs, {"problems": probs[:6]}


def c15(x):
    """Fusion: re-fused here (accepted surface map, own target patch, 12 / 12 mm) bitwise; target only; other maps fixed."""
    from fov3d.reconstruction import surface_map as SM
    probs = []
    for k in x.steps():
        sd = x.run / x.sd(k)
        d = x.dec(k)
        t = int(d["action"]["target"])
        prev, st = x.before(k), x.state(k)
        prod = load(sd / "correspondence/oracle-correspondences.npz")
        geo = load(sd / "geometry/epipolar-result.npz")
        ids = load(sd / "segmentation/local-identity.npz")["temporary_entity_id"]
        rgb_l = load(sd / "observation/acquisition/rgb-observation.npz")["rgb_L"]
        keep = np.asarray(geo["valid_epi"], bool) & (ids == t)
        uv = prod["uv_L"].astype(np.int64)
        rgb = rgb_l[uv[:, 1], uv[:, 0]].astype(np.float64) if len(uv) else np.zeros((0, 3))
        m0 = load(x.ref(prev["entities"][str(t)]["map"]["path"]))
        sm = SM.SurfaceMap(np.asarray(m0["xyz_h"], np.float64).copy(), np.asarray(m0["rgb"], np.float64).copy(),
                           m0["instance_id"].copy(), m0["support_count"].copy(), m0["provenance_mask"].copy(),
                           [str(p) for p in m0["patch_ids"]])
        fu = jload(sd / "fusion/fusion.json")
        saved = load(sd / "fusion/fused-target-map.npz")
        if int(keep.sum()) >= 100:
            p = SM.Patch(patch_id=f"ns1e_step_{k:03d}", xyz_h=np.asarray(geo["P_epi"], np.float64)[keep], rgb=rgb[keep],
                         instance_id=np.asarray(ids, np.int32)[keep])
            fused, _meta = SM.fuse(sm, p, t, RADIUS, RADIUS)
            want = {"xyz_h": fused.xyz_h, "rgb": fused.rgb, "instance_id": fused.instance_id,
                    "support_count": fused.support_count, "provenance_mask": fused.provenance_mask,
                    "patch_ids": np.array(list(fused.patch_ids), dtype="U64")}
            if fu["action"] != "FUSED" or fu["radius_m"] != RADIUS or fu["hash_cell_m"] != RADIUS or \
                    not fu["replay"]["exact"]:
                probs.append(f"step {k}: fusion record")
        else:
            want = {k_: m0[k_] for k_ in m0}
            if fu["action"] != "RETAINED_NOT_FUSED":
                probs.append(f"step {k}: < 100 points but {fu['action']}")
        if set(want) != set(saved) or any(not np.array_equal(np.asarray(want[q]), saved[q]) for q in saved):
            probs.append(f"step {k}: fused map not reproduced")
        if not np.all(saved["instance_id"] == t):
            probs.append(f"step {k}: foreign id in the map")
        for kk, rec in st["entities"].items():
            if int(kk) != t and rec["map"]["sha256"] != prev["entities"][kk]["map"]["sha256"]:
                probs.append(f"step {k}: non-target map {kk} changed")
        if fu["measured_points"] != int(keep.sum()):
            probs.append(f"step {k}: target points")
    return not probs, {"problems": probs[:6]}


def c16(x):
    """Memory: every patch rebuilt here bitwise; appended once; event = step + 1; provenance; all positive ids; no id 0."""
    probs = []
    mem, by = x.ledgers()
    prev_ev = x.initial()["memory"]["events"]
    for k in x.steps():
        ev_k = x.state(k)["memory"]["events"]
        if ev_k[:len(prev_ev)] != prev_ev or len(ev_k) != len(prev_ev) + 1:
            probs.append(f"step {k}: the memory event list is not the previous one plus one event")
            break
        prev_ev = ev_k
    keys = [r["observation_key"] for r in x.final()["memory"]["events"]]
    if len(keys) != len(set(keys)):
        probs.append("an observation appended twice")
    evs = x.final()["memory"]["events"]
    if [int(r["event"]) for r in evs] != list(range(len(evs))) or len(evs) != NS1D_EVENTS + len(x.steps()):
        probs.append("memory event list")
    for k in x.steps():
        sd = x.run / x.sd(k)
        me = jload(sd / "memory/event.json")
        e = int(me["memory_event"])
        if e != k + 1 or int(me["global_step"]) != k or e == k:
            probs.append(f"step {k}: memory event {e}")
        saved = load(sd / "memory/memory-patch.npz")
        own = x.own_patch(k)
        if not (np.array_equal(saved["xyz_h"], own["xyz_h"], equal_nan=True)
                and np.array_equal(saved["instance_id"], own["instance_id"]) and np.array_equal(saved["valid"], own["valid"])):
            probs.append(f"step {k}: memory patch not reproduced")
        adds = by[e][1]
        if {str(kk): v for kk, v in sorted(adds.items())} != me["row"]["additions"] or 0 in adds:
            probs.append(f"step {k}: additions")
        if me["observation_key"] != sha256(sd / "freeze/observation-freeze.json"):
            probs.append(f"step {k}: observation key")
        if me["measured_points_after"] != {str(i): int(by[e][0].get(i, 0)) for i in COHERENT}:
            probs.append(f"step {k}: measured points")
    for i in mem.instance_ids():
        s = mem.snapshot(i)
        if len(s.xyz_h) != len(s.source_global_index) or i <= 0:
            probs.append(f"id {i}: provenance alignment")
    fin = x.final()["memory"]["measured_points"]
    if fin != {str(k): v for k, v in sorted(by[max(by)][0].items())}:
        probs.append("final measured points")
    return not probs, {"problems": probs[:6], "events": len(evs)}


CTX = ("looks", "visited", "current_local_gaze", "own_looks", "evidence", "map")
SOURCE_OVERRIDE: dict | None = None      # corruption suite only: scanned source texts substituted in-process


def c17(x):
    """Own-look context: only the active target gains a look (with this step's calibration and state)."""
    probs = []
    for k in x.steps():
        t = int(x.dec(k)["action"]["target"])
        prev, st = x.before(k), x.state(k)
        for kk, rec in st["entities"].items():
            a, b = {f: prev["entities"][kk][f] for f in CTX}, {f: rec[f] for f in CTX}
            if int(kk) != t:
                if a != b:
                    probs.append(f"step {k}: non-target {kk} context changed")
                continue
            lk = rec["looks"][-1]
            if (rec["own_looks"] != a["own_looks"] + 1 or rec["looks"][:-1] != a["looks"]
                    or lk["calibration"] != f"run:{x.sd(k)}/observation/acquisition/calibration.json"
                    or rec["visited"][:-1] != a["visited"] or rec["visited"][-1] != x.dec(k)["action"]["local_gaze_deg"]):
                probs.append(f"step {k}: target context update")
    return not probs, {"problems": probs[:6]}


def c18(x):
    """Ordering: stages in the declared order per step; update marks 8 -> 11; the checkpoint after the update."""
    probs = []
    log = [e for e in x.log() if e.get("step") is not None and e["status"] == "ok"]
    for k in x.steps():
        order = [e["command"] for e in log if e["step"] == k]
        if order != STEP_STAGES:
            probs.append(f"step {k}: stage order {order}")
        up = jload(x.run / x.sd(k) / "update/update-opened-files.json")
        marks = [e["label"] for e in up["events"] if e.get("event") == "mark"]
        if marks != UPDATE_MARKS:
            probs.append(f"step {k}: marks {marks}")
        ck = x.j(f"freeze/checkpoint-step-{k:03d}.json")
        if any(sha256(x.run / f) != h for f, h in ck["files"].items()) or \
                any(sha256(x.run / x.sd(k) / f) != h for f, h in ck["step_freezes"].items()):
            probs.append(f"step {k}: checkpoint")
    return not probs, {"problems": probs[:6]}


def c19(x):
    """Natural reactivation only through the accepted refresh: no manual reactivation or quiet-bookkeeping edit."""
    probs = []
    for n in ("ns1e_run.py", "ns1e_core.py"):
        tree = ast.parse((SOURCE_OVERRIDE or {}).get(n) or (HERE / n).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and "reactivat" in node.func.attr:
                probs.append(f"{n}: {node.func.attr}() call")
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                tg = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in tg:
                    for sub in ast.walk(t):
                        if isinstance(sub, ast.Attribute) and sub.attr in ("quiet_probe", "quiet_since", "recorded",
                                                                           "statuses", "reactivated_since_attended",
                                                                           "disposition", "fixations", "cache"):
                            probs.append(f"{n}: assigns machine.{sub.attr}")
    for k in x.steps():
        for r in x.j(f"{x.sd(k)}/update/update.json")["natural_reactivations"]:
            ev = [e for e in x.state(k)["events"] if e["event"] == "natural_reactivation" and e["object"] == r["object"]]
            if not ev or r["revision_before"] == r["revision_after"]:
                probs.append(f"step {k}: reactivation record {r['object']}")
    return not probs, {"problems": probs[:6]}


def c20(x):
    """RESIDUE: only after NORMAL exhaustion; at most one final residue observation per entity."""
    probs = []
    finals = [int(x.dec(k)["action"]["target"]) for k in x.steps() if x.dec(k)["kind"] == "final_residue"]
    if len(finals) != len(set(finals)):
        probs.append(f"two final residue observations for one entity: {finals}")
    for k in x.steps():
        d = x.dec(k)
        if d["kind"] == "final_residue" or d.get("residue_gate_records"):
            if d["scheduler_decision"]["result"] is not None:
                probs.append(f"step {k}: RESIDUE work while schedule_normal returned {d['scheduler_decision']['result']}")
        if d["kind"] == "final_residue" and d["action"]["phase"] != "RESIDUE":
            probs.append(f"step {k}: final residue outside RESIDUE")
    term = x.terminal()
    if term and term.get("residue_gate_records") and term["scheduler_decision"]["result"] is not None:
        probs.append("terminal: RESIDUE while NORMAL service existed")
    return not probs, {"problems": probs, "final_residue_observations": finals}


def c21(x):
    """The hard cap: own formula on the handoff machine; never exceeded; never raised."""
    probs = []
    m = x.initial()["machine"]
    fix = {int(k): int(v) for k, v in m["fixations"].items()}
    mx = sum(BUDGET - f for f in fix.values()) + len(fix)
    if mx != MAX_NEW or int(m["step"]) + mx != ABS_CAP:
        probs.append(f"own cap {mx}")
    cap = x.j("handoff/cap.json")
    if cap["max_new_physical_actions"] != MAX_NEW or cap["absolute_action_cap"] != ABS_CAP:
        probs.append("recorded cap")
    for k in x.steps():
        if x.dec(k)["cap"] != {"absolute": ABS_CAP, "max_new": MAX_NEW}:
            probs.append(f"step {k}: cap")
    if len(x.steps()) > MAX_NEW:
        probs.append("more new actions than the cap")
    term = x.terminal()
    if term and term["kind"] == "cap" and (x.steps()[-1] + 1 if x.steps() else HANDOFF_STEP) != ABS_CAP:
        probs.append("cap terminal at the wrong step")
    return not probs, {"problems": probs, "new_actions": len(x.steps())}


def c22(x):
    """Checkpointing: contiguous complete steps; no partial step; no stage run twice; no re-render."""
    probs = []
    dirs = sorted(int(p.name.split("-")[1]) for p in (x.run / "steps").glob("step-*"))
    st = x.steps()
    extra = [k for k in dirs if k not in st]
    term = x.terminal()
    allowed_extra = [int(term["global_step"])] if term else []
    if extra != allowed_extra:
        probs.append(f"incomplete / extra step directories {extra}")
    if st != list(range(HANDOFF_STEP, HANDOFF_STEP + len(st))):
        probs.append("steps not contiguous")
    seen = {}
    for e in x.log():
        if e["status"] == "ok" and e.get("step") is not None:
            key = (e["command"], e["step"])
            seen[key] = seen.get(key, 0) + 1
    twice = [k for k, n in seen.items() if n > 1]
    if twice:
        probs.append(f"stages run twice {twice[:3]}")
    for k in st:
        if x.state(k)["new_actions"] != k - HANDOFF_STEP + 1:
            probs.append(f"step {k}: new action count")
    return not probs, {"problems": probs[:6]}


def c23(x):
    """Truth firewall: no control stage opened Breadth-1 / evaluation / catalog truth; evaluation after the freeze."""
    probs = []
    recs = [p for p in x.run.rglob("*opened-files.json") if "evaluation" not in p.parts]
    catalog_hashed = 0
    for p in recs:
        r = jload(p)
        reads = [e["path"] for e in r["events"] if e.get("event") == "open"]
        if p.relative_to(x.run).as_posix() == "control/control-freeze-opened-files.json":
            # after the terminal decision the control freeze hashed every control file, including the Blender-written
            # sealed catalogs (bytes hashed, never parsed): reported (deviation D1), not a control-time read
            cat = [q for q in reads if q.endswith("observation/evaluation_only/instance-catalog.json")]
            catalog_hashed = len(cat)
            reads = [q for q in reads if q not in cat]
        bad = [q for q in reads if any(f in q for f in CONTROL_FORBIDDEN)]
        if bad or r["violations"]:
            probs.append(f"{p.relative_to(x.run)}: {bad[:2]} {len(r['violations'])}")
        pg = r.get("process_guard") or {}
        if pg.get("attempts"):
            probs.append(f"{p.relative_to(x.run)}: process attempts")
        stage = p.parent.name
        if stage in ("plan", "update") and pg.get("guard") != POLICY_GUARD:
            probs.append(f"{p.relative_to(x.run)}: guard {pg.get('guard')}")
    log = x.log()
    fc = [n for n, e in enumerate(log) if e["command"] == "freeze-control" and e["status"] == "ok"]
    ev = [n for n, e in enumerate(log) if e["command"] == "evaluate" and e["status"] == "ok"]
    if ev and (not fc or ev[0] < fc[0] or log[ev[0]]["started_utc"] < log[fc[0]]["finished_utc"]):
        probs.append("evaluate ran before the control freeze")
    if x.has("freeze/control-freeze.json"):
        cf = x.j("freeze/control-freeze.json")
        if any(f.startswith("evaluation/") for f in cf["files"]):
            probs.append("the control freeze lists evaluation files")
    if x.has("evaluation/evaluation-opened-files.json"):
        r = jload(x.run / "evaluation/evaluation-opened-files.json")
        seq = [(e.get("label") or e.get("path")) for e in r["events"]]
        exr = next((n for n, s in enumerate(seq) if str(s).endswith("canonical.exr")), None)
        mk = next((n for n, s in enumerate(seq) if s == "reference_access_begins"), None)
        mk0 = next((n for n, s in enumerate(seq) if s == "control_freeze_verified"), None)
        if exr is None or mk is None or mk0 is None or not (mk0 < mk < exr):
            probs.append("evaluation reference access order")
        wd = r["allow_write_dirs"]
        if len(wd) != 1 or not wd[0].endswith("/evaluation") or any(not w.startswith(wd[0] + "/") for w in r["writes"]):
            probs.append("evaluation wrote outside evaluation/")
    return not probs, {"problems": probs[:6], "records": len(recs),
                       "control_freeze_hashed_sealed_catalogs_as_bytes": catalog_hashed}


def c24(x):
    """Evaluation recomputed independently: own EXR channels, own H0 transform, own weights, brute-force 12 mm."""
    from exr_lite import read_uncompressed_exr
    from fov3d.reconstruction.measurement_memory import effective_target_geometry
    probs = []
    if not x.has("evaluation/evaluation.json"):
        return False, {"problems": ["no evaluation"]}
    ev = x.j("evaluation/evaluation.json")
    if sha256(B1_EXR) != B1_SHA or ev["reference"]["sha256"] != B1_SHA:
        probs.append("reference EXR pin")
    ch = read_uncompressed_exr(str(B1_EXR))
    oi = [k for k in ch if k.endswith("Object Index.X")]
    inst = np.rint(np.asarray(ch[oi[0]], np.float64)).astype(np.int64)
    pos = np.stack([np.asarray(ch[[k for k in ch if k.endswith(f"Position.{c}")][0]], np.float64) for c in "XYZ"], -1)
    c0 = jload(NS1A / "observations/rank-06/acquisition/calibration.json")
    hr, ho = np.asarray(c0["head_R_wh"], np.float64), np.asarray(c0["head_origin_w_m"], np.float64)
    h, w = inst.shape
    j_ = np.arange(h, dtype=np.float64)
    wrow = (2 * math.pi / w) * (np.sin(math.pi / 2 - j_ * math.pi / h) - np.sin(math.pi / 2 - (j_ + 1) * math.pi / h))
    if abs(wrow.sum() * w - 4 * math.pi) > 1e-12 or (h, w) != (360, 720):
        probs.append("reference raster / weights")
    fin = x.final()["entities"]
    mem, _by = x.ledgers()
    tot = [0, 0, 0.0, 0.0, 0]
    for i in COHERENT:
        r = ev["per_entity"][str(i)]
        m = (inst == i) & np.isfinite(pos).all(-1) & ~np.all(pos == 0, -1)
        ref = (pos[m] - ho) @ hr
        surf = np.asarray(load(x.ref(fin[str(i)]["map"]["path"]))["xyz_h"], np.float64)
        surf = surf[np.isfinite(surf).all(1)]
        eff = effective_target_geometry(surf, mem.snapshot(i).xyz_h)

        def covered(pts):
            out = np.zeros(len(ref), bool)
            for s in range(0, len(ref), 64):
                q = ref[s:s + 64]
                best = np.full(len(q), np.inf)
                for t in range(0, len(pts), 200000):
                    dd = ((q[:, None, :] - pts[None, t:t + 200000, :]) ** 2).sum(-1)
                    best = np.minimum(best, dd.min(1)) if dd.size else best
                out[s:s + 64] = best <= RADIUS * RADIUS
            return out
        if not m.any():
            if r["status"] != "NO_0P5_DEG_FIRST_HIT_REFERENCE" or r["coverage_fraction"] is not None:
                probs.append(f"{i}: no-reference status")
            continue
        cv, ce = covered(surf), covered(eff)
        rows = np.nonzero(m)[0]
        om = float(wrow[rows].sum())
        omc = float(wrow[rows[cv]].sum())
        if (r["reference_cells"] != int(m.sum()) or r["covered_cells"] != int(cv.sum())
                or r["effective_covered_cells"] != int(ce.sum()) or abs(r["reference_solid_angle_sr"] - om) > 1e-12
                or abs(r["coverage_fraction_weighted"] - omc / om) > 1e-12 or r["final_persistent_surfels"] != len(surf)):
            probs.append(f"{i}: coverage {r['covered_cells']} vs {int(cv.sum())} / eff {r['effective_covered_cells']} vs "
                         f"{int(ce.sum())}")
        tot[0] += int(m.sum())
        tot[1] += int(cv.sum())
        tot[2] += om
        tot[3] += omc
        tot[4] += int(ce.sum())
    a = ev["aggregate"]
    if tot[0] and (a["reference_cells"] != tot[0] or a["covered_cells"] != tot[1]
                   or abs(a["micro_coverage_weighted"] - tot[3] / tot[2]) > 1e-12
                   or ev["effective_geometry_diagnostic"]["covered_cells"] != tot[4]):
        probs.append("aggregate")
    if ev["radius_m"] != RADIUS or ev["historical_reference"]["comparable"] is not False or \
            "memory excluded" not in ev["primary"]:
        probs.append("definition / non-comparability")
    return not probs, {"problems": probs[:6], "reference_cells": tot[0], "covered": tot[1]}


def c25(x):
    """Terminology: COHERENT_SUBSET_CLOSED; never full-Classroom closure / global quiescence; 98.34 % never comparable;
    no ACCEPTED marker; REVIEW PENDING."""
    probs = []
    term = x.terminal()
    if term is not None:
        oc = term["outcome"]
        if term["kind"] == "closed" and oc["scope"] != "COHERENT_SUBSET_CLOSED":
            probs.append("closure not labelled COHERENT_SUBSET_CLOSED")
        if term["kind"] == "cap" and oc["scope"] != "INCOMPLETE_CAP":
            probs.append("cap not labelled INCOMPLETE_CAP")
        resid = (term.get("terminal") or {}).get("closure", {}).get("residual") or []
        if (oc["outcome"] == "1Q") != (term["kind"] == "closed" and not resid):
            probs.append("1Q / 1R inconsistent")
    texts = []
    rep = REPO / REPORT_PATH
    if rep.exists():
        t = rep.read_text()
        texts.append(t)
        if NS1E_ACCEPTED in t:
            probs.append("ACCEPTED marker in the report")
        if "**Status: REVIEW PENDING.**" not in t or NS1E_COMPLETE not in t:
            probs.append("report status / marker")
    for p in x.run.rglob("*.json"):
        if p.stat().st_size < 3_000_000:
            texts.append(p.read_text())
    for t in texts:
        for claim in ("FULL_CLASSROOM_CLOSED", "GLOBAL_QUIESCENCE"):
            for mt in re.finditer(claim, t):
                ctx = t[max(0, mt.start() - 80): mt.start()].lower()
                if not any(n in ctx for n in ("not", "never", "no ")):
                    probs.append(f"claim {claim}")
        if re.search(r"(better|worse|higher|lower|exceed\w*|improv\w*) (than|on|over) (the )?(historical )?98\.34", t, re.I):
            probs.append("98.34 % compared numerically")
    return not probs, {"problems": sorted(set(probs))[:6]}


def c26(x):
    """Figures regenerate byte-identically; required labels; PLYs: persistent maps only / labelled diagnostic."""
    import ns1e_visuals as V
    probs = []
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        figs, dd = V.render_all(x.run)
        for name, (im, meta) in figs.items():
            p = Path(td) / name
            im.save(p, format="PNG", optimize=False)
            rec = man["figures"].get(name)
            if rec is None or sha256(p) != rec["sha256"] or sha256(x.vis / name) != rec["sha256"]:
                probs.append(f"{name}: not byte-identical")
        plys = V.plys(dd)
    for name in FIGURES_ALWAYS:
        if name not in man["figures"]:
            probs.append(f"{name} missing")
    for name, labs in REQUIRED_LABELS.items():
        if name in man["figures"] and not set(labs) <= set(man["figures"][name]["labels"]):
            probs.append(f"{name}: labels")
    import ns1e_core as CORE
    fin = x.final()["entities"]
    pers = CORE.ply_read((x.vis / "final-coherent-persistent-points.ply").read_bytes())
    n_map = sum(int(len(load(x.ref(fin[str(i)]["map"]["path"]))["xyz_h"])) for i in COHERENT)
    if len(pers["xyz"]) != n_map or sorted(set(pers["entity_id"].tolist())) != COHERENT or \
            plys["final-coherent-persistent-points.ply"] != (x.vis / "final-coherent-persistent-points.ply").read_bytes():
        probs.append("persistent PLY")
    eff = CORE.ply_read((x.vis / "final-effective-geometry-diagnostic.ply").read_bytes())
    mem, _ = x.ledgers()
    n_eff = n_map + sum(len(mem.snapshot(i).xyz_h) for i in COHERENT)
    if len(eff["xyz"]) != n_eff or not any("NOT PERSISTENT RECONSTRUCTION" in c for c in eff["comments"]):
        probs.append("effective PLY")
    reacts = any(x.j(f"{x.sd(k)}/update/update.json")["natural_reactivations"] for k in x.steps())
    if ("natural-reactivation.png" in man["figures"]) != reacts:
        probs.append("reactivation figure inconsistent")
    return not probs, {"problems": probs[:6]}


def c27(x):
    """Run manifest and declared changes."""
    probs = []
    if x.has("manifest.json"):
        man = x.j("manifest.json")
        bad = [f for f, h in list(man["files"].items()) if sha256(x.run / f) != h]
        present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
            "manifest.json", "check-summary.json", "process-log.jsonl"}
        if bad or set(man["files"]) != present:
            probs.append(f"manifest {bad[:3]} / unlisted {sorted(present - set(man['files']))[:3]}")
    else:
        probs.append("no manifest")
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    if extra:
        probs.append(f"undeclared changes {extra}")
    return not probs, {"problems": probs}


CHECKS = [
    ("01", "provenance: canonical repo, base, NS1d accepted, contract first and unchanged, one clean pushed commit", c01),
    ("02", "accepted code unchanged (fov3d, pins); NS1e process guard = accepted audit events", c02),
    ("03", "synthetic known answers re-run", c03),
    ("04", "handoff: own NS1d memory; frozen M2 machine; next decision; start state", c04),
    ("05", "eligibility: own rule; ten coherent ids; 10 / 110 / 178 excluded; no names", c05),
    ("06", "charts: own construction at the ORIGINAL NS1a gaze; fixed; every probe used its chart", c06),
    ("07", "physical sensor: fixed head, real world sensor at the mapped gaze, no fake local sensor", c07),
    ("08", "controller: independent SceneMachine re-drive reproduces decisions, events, checkpoints, terminal", c08),
    ("09", "every fresh M2 probe recomputed (tolerance 0)", c09),
    ("10", "gate only in RESIDUE; real H0 sensor; harness", c10),
    ("11", "budget 24; deferral rule; never BLOCKED", c11),
    ("12", "revision = (own looks, measured points) everywhere", c12),
    ("13", "observation: plan frozen before one 4096-spp render per step; render standard", c13),
    ("14", "measurement: geometry recomputed; identity re-attached; freeze order; no truth / stereo leakage", c14),
    ("15", "fusion re-fused bitwise; target only; 12 / 12 mm; other maps fixed", c15),
    ("16", "memory: patches rebuilt bitwise; append once; event = step + 1; provenance; all positive ids", c16),
    ("17", "own-look context: only the active target gains a look", c17),
    ("18", "ordering: stage order; update marks; checkpoints", c18),
    ("19", "natural reactivation only through the refresh; no manual edit", c19),
    ("20", "RESIDUE only after NORMAL exhaustion; at most one final residue observation per entity", c20),
    ("21", "hard cap derived (231 / 239), never exceeded or raised", c21),
    ("22", "checkpointing: contiguous, no partial step, no stage twice", c22),
    ("23", "truth firewall: no control-stage truth read; evaluation after the control freeze", c23),
    ("24", "evaluation recomputed independently (12 mm, persistent map primary, effective diagnostic)", c24),
    ("25", "terminology: COHERENT_SUBSET_CLOSED; no full-Classroom / global claims; 98.34 % non-comparable", c25),
    ("26", "figures byte-identical; labels; PLYs", c26),
    ("27", "run manifest and declared changes", c27),
]


def run_checks(run: Path, vis: Path, only=None, quiet=False, rehearsal=False) -> dict:
    x = X(run, vis, rehearsal)
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
    ap.add_argument("--rehearsal", action="store_true", help="development rehearsal runs only")
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    res = run_checks(a.run, a.visuals, only=set(a.only.split(",")) if a.only else None, rehearsal=a.rehearsal)
    failed = [k for k, v in res.items() if not v["pass"]]
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(failed)}")
    summary = {"schema": "NS1e-check-summary-v1", "checks": res, "failed": failed, "rehearsal": a.rehearsal,
               "marker": "NORTH_STAR1E_CHECKS_PASS" if not failed else "NORTH_STAR1E_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1E_CHECKS_PASS")
    if a.corruptions:
        import check_ns1e_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed, rehearsal=a.rehearsal)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
