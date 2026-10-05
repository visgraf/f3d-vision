#!/usr/bin/env python3
"""North Star-1c checker: fail-capable verification of the first scene switch (read-only).

    .venv/bin/python tools/north_star/check_ns1c.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md, section 23.  The checker keeps its own literal
pins and constants and recomputes independently where an independent formula exists: the coherent seed set (own rule
on the frozen NS1a seed set), the charts (own triple-product construction), the world gazes (own column-form
rotation), the fixed-head calibrations (own construction from the AB1a head pose), the PERFECT correspondence and the
spherical geometry (the accepted NS1a checker's own oracle and law-of-sines triangulation), the 12-mm association (own
brute-force nearest surfel), the service states (own gate / watchdog rule) and the scheduler decisions (the accepted
scheduler re-run on own summaries).  The accepted policy has no independent implementation: every recorded probe is
recomputed from the context reconstructed from its records, the 172 probe is compared with the accepted NS1b
post-action probe, and every untouched entity is re-probed from scratch.  ``--corruptions`` runs the mutation suite
(check_ns1c_corruptions.py) from a passing mirror after a null probe.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
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

PREFIX = "[ns1c-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
BASE = "2815bf166689d68cec421fb119635cafaa718d9a"
NS1B_ACCEPTANCE = "255355108863022f931574dae4b2df8cdd2a772e"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
CONTRACT = "cb2217db82980c3efd0dfd51cf0f944a5d4f7aa2"
CONTRACT_PATH = "docs/north-star/ns1c-coherent-first-scene-switch-contract.md"
REPORT_PATH = "docs/north-star/ns1c-coherent-first-scene-switch-report.md"
PREVIEWS = Path("/home/lvelho/rd/f3d-vision/previews")
NS1A = PREVIEWS / "north-star/ns1a-perfect-bootstrap-round"
NS1B = PREVIEWS / "north-star/ns1b-recentered-controller-handoff"
NS1A_PINS = {"freeze/observation-freeze.json": "46f0a22eab852b3c5750420ed993a453cd6b1e6c4d0cd0d96ce167883b87576d",
             "freeze/geometry-freeze.json": "7b0ae64dacc1d6e12d893a118e017220a349a4062be6474e9fbf82a58ab0452b",
             "freeze/seed-set-freeze.json": "4ee36a1aa39525a7faa0132877d5cede14df185ae5607dbe73615a3ad2357173",
             "seeds/seed-set.json": "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a",
             "seeds/entity-maps.npz": "621d8902948656221d876f3642c78963b075a0ce5a5ae1227da3e2f65620f605",
             "source/nb1c-gaze-list.json": "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062",
             "observations/acquisition-run.json": "1bbf03bc15dd5401c7f49d21b4e08492024391a43d0c73bf96d099c84db15dbf"}
NS1B_PINS = {"manifest.json": "e859fa61489015191f5ef3639ef91766cb26f3f787eb3dd279cfd8516435288c",
             "check-summary.json": "146438bd6b95933b678d49383efdafac201329ce60550bd1d8ca47d7a5c7bed7",
             "fusion/fused-target-map.npz": "bf831ad5d49b226b878c73af80b19330620bfe201e85b7464a8bb63c3b4aad0c",
             "fusion/fusion.json": "6401f0c23554eef5dbb8197342cc75141d496c9603ed2a714f797516ae94c45e",
             "post/evidence.npz": "a96791631906e43d4598b7b6de7db66cdb52303835bdeb1fe533106e8b351f00",
             "post/controller-state.npz": "337c070525131bdbec4c061eaa85b389594cf999b468da399d8535058b1bd7f0",
             "post/post-action-probe.json": "2918e146294dace627acc1b8b097f5b4e5a072ec0c98cf0e2d65718b062f8bac",
             "context/controller-state.npz": "ceebc7250eb046a577bc3b024ab30ac1002141aea0e4ebd17a17571d41bba9cf",
             "context/evidence.npz": "744c91a440100bafe02aa3c9def52e61d965733bdb63df39ab2dca9745f348dd",
             "context/context.json": "8df0124fa8017efafd4234f56a655759671cb7c1ebb0cd2e101c100d8bd23248",
             "context/target-map-H0.npz": "e11c2d08865590da39e813529501b7f5feb9e19baa4b25cfbc30215aa3c10f6b",
             "observation/acquisition/calibration.json":
                 "a4b2ae6732066361ccdd4c9731a3735560e48f7a41392486c214e31db779cb82",
             "observation/acquisition/rgb-observation.npz":
                 "23a1208f2ffbcd51bd25d94530c1202d2bf45242203fcb2c845a816f7cf378b2",
             "observation/oracle_aid/reference-observation.npz":
                 "8764de530c7fa97469f44af86598d0602641bf79f3358341c3e1cc41d7a3ca14",
             "freeze/observation-freeze.json": "0fbd0e8d8326b5599d83c10a4281fda057b6b32e1e9bd6dfdf53aa6890ca8116",
             "chart/policy-chart.json": "8adefe86726fbe95d2e3782d9cf26db120959df5a746f061d87cfe038bcdc5df",
             "probe/decision.json": "0a4148774a7fdbf09ecf0078ee29cb806f97405994eee3fe9470b7a2e6c3cb63"}
NS1A_CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
HEAD_SOURCE = (PREVIEWS / "active-bootstrap/ab1a-first-natural-stereo-look/acquisition/calibration.json",
               "9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913")
AB1D2_ACQ = (PREVIEWS / "active-bootstrap/ab1d2-4096spp-observation-quality/observations/gaze-1/acquisition/"
                        "acquisition.json", "7c023b1f382514716893ca1a4d3009a6ae1102e327b3de00312206e3d9f37eff")
SOURCE_PINS_DIGEST = "cebea7d427795b5db0939bf76a291da03332dea6f32e0f15465e08b57ed67f78"
GAZES = {1: (76.75, 7.75), 2: (-2.75, 75.75), 3: (75.25, -25.75), 4: (38.25, -61.75), 5: (179.75, 34.75),
         6: (-156.25, 28.75)}
COHERENT = [9, 12, 123, 129, 172, 202, 204, 212, 230, 231]
DEFERRED = [10, 110, 178]
CONTINUING = 172
DEFERRED_STATE = "DEFERRED_AMBIGUOUS_ORACLE_IDENTITY"
WATCHDOG = 24
NS1B_POST = {"state": "ACTIONABLE", "source": "fsg6f", "local": [-5.0, -10.0], "admissible": True, "novel": 22}
POLICY = {"component_step_deg": 5.0, "yaw_min_deg": -25.0, "yaw_max_deg": 25.0, "pitch_min_deg": -20.0,
          "pitch_max_deg": 20.0, "edge_band_fraction": 0.04, "edge_object_fraction_min": 0.15, "voxel_m": 0.025,
          "neighbour_radius_m": 0.065, "minimum_neighbours": 6, "tangent_asymmetry_min": 0.18, "lookahead_m": 0.12,
          "current_view_margin_deg": 1.0, "minimum_candidate_frontier_support": 8, "alignment_cos_min": 0.5,
          "map_extent_quantile": 0.01}
FUSION = {"association_radius_m": 0.012, "hash_cell_m": 0.012}
CYC_GRID, CYC_SHAPE, OBJECT_ID, MIN_POINTS = 0.10, [401, 501], 141, 100
RADIUS, CELL = 0.012, 0.012
SPP, SEEDS, IPD, VERGENCE = 4096, {"L": 2111, "R": 2112}, 0.063, 2.10
EYES = np.array([[-0.0315, 0.0, 0.0], [0.0315, 0.0, 0.0]])
ONCE = ["source", "synthetic", "eligibility", "charts", "contexts", "initial-probe"]
STEP = ["schedule", "preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
        "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "fuse", "update"]
TOL, ROUND = 1e-9, 1e-12
NS1C_FILES = ["tools/north_star/" + n for n in ("ns1c_spec.py", "ns1c_core.py", "ns1c_render.py", "ns1c_run.py",
                                                "ns1c_synthetic.py", "ns1c_visuals.py", "check_ns1c.py",
                                                "check_ns1c_corruptions.py")]
DECLARED = set(NS1C_FILES) | {CONTRACT_PATH, REPORT_PATH, "tools/repository/check_repository_layout.py"}
PRODUCTION = ["ns1c_spec.py", "ns1c_core.py", "ns1c_render.py", "ns1c_run.py", "ns1c_visuals.py"]
FORBIDDEN_IDENTIFIERS = {"run_control_loop", "run_controller02", "schedule_normal", "SceneClosed", "catalog_summaries",
                         "StereoSGBM_create", "StereoSGBM", "StereoBM_create", "compute_natural", "run_match_gaze",
                         "head_motion", "move_head", "reactivate"}
FORBIDDEN_MODULES = {"ab1d_match", "ab1d3_sgbm", "ab1a_stereo", "ab1c_planar", "fsg_stereo_sgbm"}
FORBIDDEN_READ = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                  "evaluation.json", "/evaluation/", "evaluation_only", "breadth-1-classroom", "natural-bootstrap-1a",
                  "natural-bootstrap-1b", "controller-01")
TRUTH_STAGES = ("source/source-opened-files.json", "contexts-opened-files.json", "observation-freeze-opened-files.json", "correspondence-opened-files.json",
                "segmentation-opened-files.json", "update-opened-files.json")
CLOSED = "SCENE" + "_CLOSED"
TERMINAL_LABELS = {"COHERENT_SUBSET_QUIESCENT", "COHERENT_SUBSET_INCOMPLETE"}
FIGURES = ["overview.png", "scene-scheduler-timeline.png", "multi-entity-growth-3d.png",
           "controller-vs-northstar-support.png"]
LABELS = {"overview.png": ["NS1a / NS1b FROZEN INPUT", "no object name used", "PHYSICAL HEAD FIXED - POLICY CHART ONLY",
                           "POLICY CHART C_i", "CANONICAL H0", "DEFERRED AMBIGUOUS ORACLE IDENTITY",
                           "integrated.schedule (accepted)", "NOT EXECUTED", "ORACLE CORRESPONDENCE",
                           "DERIVED SPHERICAL GEOMETRY", "ORACLE SEGMENTATION AID"],
          "scene-scheduler-timeline.png": ["integrated.schedule (accepted)", "DEFERRED AMBIGUOUS ORACLE IDENTITY"],
          "multi-entity-growth-3d.png": ["CANONICAL H0", "PHYSICAL HEAD FIXED - POLICY CHART ONLY",
                                         "DERIVED SPHERICAL GEOMETRY"],
          "controller-vs-northstar-support.png": ["ORACLE CORRESPONDENCE", "DERIVED SPHERICAL GEOMETRY"]}
BADGES = {"overview.png": ["ORACLE INPUT", "DERIVED"], "scene-scheduler-timeline.png": ["DERIVED"],
          "multi-entity-growth-3d.png": ["ORACLE INPUT", "DERIVED"],
          "controller-vs-northstar-support.png": ["ORACLE INPUT", "DERIVED"]}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def ancestor(a: str, b: str = "HEAD") -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=REPO).returncode == 0


def load(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def arrays_equal(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.asarray(a[k]).dtype == np.asarray(b[k]).dtype
                                    and np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)


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

    def res(self, ref: str) -> Path:
        scheme, rel = ref.split(":", 1)
        return {"run": self.run, "ns1a": NS1A, "ns1b": NS1B}[scheme] / rel

    def log(self) -> list[dict]:
        return [json.loads(ln) for ln in (self.run / "process-log.jsonl").read_text().splitlines() if ln.strip()]

    def states(self) -> list[dict]:
        out = [self.j("scene/state-initial.json")]
        for p in sorted((self.run / "scene").glob("state-after-step-*.json")):
            out.append(self.j(str(p.relative_to(self.run))))
        return out

    def decisions(self) -> list[tuple[int, dict]]:
        out = []
        for p in sorted((self.run / "steps").glob("step-*/plan/decision.json")) if self.has("steps") else []:
            out.append((int(p.parent.parent.name.split("-")[1]), self.j(str(p.relative_to(self.run)))))
        return out

    def executed(self) -> list[tuple[int, dict]]:
        return [(k, d) for k, d in self.decisions() if d["kind"] == "attend"
                and self.has(f"steps/step-{k:02d}/update/update.json")]

    def sd(self, k: int) -> str:
        return f"steps/step-{k:02d}"

    def charts(self) -> dict:
        return self.j("charts/policy-charts.json")["charts"]

    def ids(self) -> list[int]:
        """The run's own scene ids (c03 / c04 require them to equal the literal coherent set)."""
        return [int(k) for k in self.j("scene/state-initial.json")["scene_ids"]]


def memo(x: X, key: str, fn):
    if key not in x.memo:
        x.memo[key] = fn()
    return x.memo[key]


# ---------------------------------------------------------------- own independent implementations
def own_dir(yaw: float, pitch: float) -> np.ndarray:
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.cos(p) * math.sin(y), math.sin(p), -math.cos(p) * math.cos(y)])


def own_yp(d) -> tuple[float, float]:
    d = np.asarray(d, float) / np.linalg.norm(d)
    return math.degrees(math.atan2(d[0], -d[2])), math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))


def own_chart(g0: np.ndarray) -> np.ndarray:
    b = np.array([1.0, 0.0, 0.0])
    g = np.asarray(g0, float) / np.linalg.norm(g0)
    x = np.cross(np.cross(g, b), g)
    x = x / np.linalg.norm(x)
    z = -g
    return np.column_stack((x, np.cross(z, x), z))


def own_world(local, r_hc: np.ndarray) -> tuple[float, float]:
    return own_yp(np.asarray(r_hc, float) @ own_dir(*local))


def head() -> dict:
    return json.loads(Path(HEAD_SOURCE[0]).read_text())


def own_calibration(yaw: float, pitch: float, tangent: str = "baseline_projected") -> dict:
    import fsg_geometry as FG     # the accepted builder is the reference definition of camera construction
    h = head()
    return FG.make_calibration("full", float(yaw), float(pitch), VERGENCE, ipd=IPD, head_r_wh=np.asarray(h["head_R_wh"]),
                               head_origin_w=np.asarray(h["head_origin_w_m"]), tangent_frame=tangent)


def cal_bytes(c: dict) -> bytes:
    return (json.dumps(c, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


def cal_close(a: dict, b: dict, tol: float = ROUND) -> bool:
    return (max(abs(float(u) - float(v)) for u, v in zip(a["gaze_yaw_pitch_deg"], b["gaze_yaw_pitch_deg"])) <= 1e-9
            and all(np.abs(np.asarray(e["R_hc"], float) - np.asarray(f["R_hc"], float)).max() <= tol
                    and np.abs(np.asarray(e["centre_h_m"], float) - np.asarray(f["centre_h_m"], float)).max() <= tol
                    for e, f in zip(a["eyes"], b["eyes"])))


def fixed_head(c: dict) -> bool:
    h = head()
    centres = np.array([e["centre_h_m"] for e in c["eyes"]], float)
    return bool(float(np.abs(centres - EYES).max()) <= ROUND and abs(float(c["ipd_m"]) - IPD) <= ROUND
                and float(np.abs(np.asarray(c["head_R_wh"], float) - np.asarray(h["head_R_wh"], float)).max()) <= ROUND
                and float(np.abs(np.asarray(c["head_origin_w_m"], float)
                                 - np.asarray(h["head_origin_w_m"], float)).max()) <= ROUND
                and c.get("tangent_frame") == "baseline_projected")


def own_association(m: np.ndarray, p: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    m = np.asarray(m, float)
    p = np.asarray(p, float)
    out = np.full(len(p), -1, np.int64)
    for s in range(0, len(p), 2048):
        q = p[s:s + 2048]
        lo, hi = q.min(0) - radius, q.max(0) + radius
        sel = np.flatnonzero(np.all((m >= lo) & (m <= hi), axis=1))
        if not len(sel):
            continue
        d = np.linalg.norm(q[:, None, :] - m[sel][None, :, :], axis=2)
        kk = np.argmin(d, axis=1)
        ok = d[np.arange(len(q)), kk] < radius
        out[s:s + len(q)][ok] = sel[kk[ok]]
    return out


def own_service(probe: dict, own_looks: int, blocked_before: str | None) -> str:
    if blocked_before:
        return f"BLOCKED:{blocked_before}"
    act = probe.get("proposal") is not None and bool(probe["gate"]["admissible"])
    if act and int(own_looks) >= WATCHDOG:
        return "BLOCKED:watchdog"
    return "ACTIONABLE" if act else "QUIET"


def own_seed_rows() -> dict:
    doc = json.loads((NS1A / "seeds/seed-set.json").read_text())
    return {int(e["temporary_entity_id"]): e for e in doc["entities"]}


def guard_files(x: X) -> list[str]:
    return sorted(str(p.relative_to(x.run)) for p in x.run.rglob("*opened-files.json"))


def opens(rec: dict) -> list[dict]:
    return [e for e in rec["events"] if e.get("event") == "open"]


def forbidden(p: str) -> bool:
    return any(t in p for t in FORBIDDEN_READ)


def ok_entries(x: X) -> list[dict]:
    return [e for e in x.log() if e["status"] == "ok" and e["command"] in ONCE + STEP + ["loop"]]


def probe_file(x: X, rec: dict) -> dict:
    return json.loads(x.res(rec["probe"]["path"]).read_text())


# ---------------------------------------------------------------- the checks
def c01(x):
    origin = git("remote", "get-url", "origin")
    anc = {n: ancestor(s) for n, s in (("base", BASE), ("ns1b_acceptance", NS1B_ACCEPTANCE),
                                       ("ns1a_acceptance", NS1A_ACCEPTANCE), ("contract", CONTRACT))}
    unchanged = subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode == 0
    added = git("log", "--diff-filter=A", "--format=%H", "--", CONTRACT_PATH).split()[-1:] == [CONTRACT]
    impl = {e["code"]["commit"] for e in ok_entries(x)}
    later = bool(impl) and all(c != CONTRACT and ancestor(CONTRACT, c) for c in impl)
    import ns1c_spec as SPm
    spec = (SPm.CONTRACT_COMMIT == CONTRACT and SPm.BASE_COMMIT == BASE and SPm.NS1B_ACCEPTANCE == NS1B_ACCEPTANCE
            and SPm.NS1A_ACCEPTANCE == NS1A_ACCEPTANCE)
    src = x.j("source/source-manifest.json")
    ok = (CANONICAL_REMOTE in origin and all(anc.values()) and unchanged and added and later and spec
          and src["contract_commit"] == CONTRACT and src["contract_unchanged"] and CANONICAL_REMOTE in src["origin"]
          and src["base_commit"] == BASE and src["ns1b_acceptance"] == NS1B_ACCEPTANCE
          and src["ns1a_acceptance"] == NS1A_ACCEPTANCE)
    return ok, {"origin": origin, "ancestors": anc, "contract_unchanged": unchanged, "contract_added_at": added,
                "canonical_commits": sorted(impl), "after_contract": later, "spec": spec}


def c02(x):
    import ns1c_spec as SPm
    digest = hashlib.sha256(json.dumps(SPm.SOURCE_PINS, sort_keys=True).encode()).hexdigest()
    bad = sorted(p for p, h in SPm.SOURCE_PINS.items() if sha256(REPO / p) != h)
    src = x.j("source/source-manifest.json")
    a = {r: sha256(NS1A / r) for r in NS1A_PINS}
    b = {r: sha256(NS1B / r) for r in NS1B_PINS}
    ok = (digest == SOURCE_PINS_DIGEST and not bad and src["source_pins"] == SPm.SOURCE_PINS and a == NS1A_PINS
          and b == NS1B_PINS and src["ns1a_handoff"] == NS1A_PINS and src["ns1b_handoff"] == NS1B_PINS
          and SPm.NS1A_PINS == NS1A_PINS and SPm.NS1B_PINS == NS1B_PINS and src["watchdog"] == WATCHDOG
          and src["global_cap"] == WATCHDOG and src["ns1b_check_marker"] == "NORTH_STAR1B_CHECKS_PASS"
          and sha256(HEAD_SOURCE[0]) == HEAD_SOURCE[1])
    return ok, {"pins_digest": digest, "changed": bad, "ns1a_equal": a == NS1A_PINS, "ns1b_equal": b == NS1B_PINS,
                "watchdog": src.get("watchdog")}


def c03(x):
    rows = own_seed_rows()
    coh = sorted(k for k, e in rows.items() if e["initialized"] and int(e["contributing_patches"]) == 1)
    dfr = sorted(k for k, e in rows.items() if e["initialized"] and int(e["contributing_patches"]) > 1)
    el = x.j("eligibility/coherent-seed-set.json")
    guard = x.j("eligibility/eligibility-opened-files.json")
    reads = set(guard["data_reads"])
    want = {str((NS1A / f).resolve()) for f in ("seeds/seed-set.json", "freeze/seed-set-freeze.json",
                                                "source/nb1c-gaze-list.json")}
    ok = (coh == COHERENT and dfr == DEFERRED and el["coherent_ids"] == COHERENT and el["deferred_ids"] == DEFERRED
          and el["scene_ids"] == COHERENT and not el.get("DEV_OVERRIDE") and el["matches_expectation"]
          and reads == want and not guard["violations"]
          and el["fields_read"] == ["temporary_entity_id", "initialized", "contributing_patches", "initialized_at_rank",
                                    "final_surfels"]
          and all(r["state"] == DEFERRED_STATE for r in el["deferred"])
          and [r["temporary_entity_id"] for r in el["coherent"]] == COHERENT
          and all(r["initialized_at_rank"] == rows[r["temporary_entity_id"]]["initialized_at_rank"]
                  and r["initialization_gaze_deg"] == list(GAZES[r["initialized_at_rank"]]) for r in el["coherent"]))
    return ok, {"own_coherent": coh, "own_deferred": dfr, "record": [el["coherent_ids"], el["deferred_ids"]],
                "reads": sorted(reads), "dev_override": bool(el.get("DEV_OVERRIDE"))}


def c04(x):
    bad = []
    for st in x.states():
        if sorted(int(k) for k in st["entities"]) != COHERENT or st["scene_ids"] != COHERENT:
            bad.append(f"{st['label']}: scene entities {sorted(st['entities'])}")
        if sorted(r["temporary_entity_id"] for r in st["deferred"]) != DEFERRED or any(
                r["state"] != DEFERRED_STATE or r["in_scheduler"] for r in st["deferred"]):
            bad.append(f"{st['label']}: deferred rows")
        if any(int(r["temporary_entity_id"]) in DEFERRED for r in st["table"]):
            bad.append(f"{st['label']}: a deferred id in the service table")
    for k, d in x.decisions():
        ids = [int(a) for a, _b in d["scheduler_decision"]["summaries"]]
        if ids != COHERENT:
            bad.append(f"step {k}: scheduler input ids {ids}")
        if d.get("action") and int(d["action"]["target"]) in DEFERRED:
            bad.append(f"step {k}: a deferred target")
    tab = x.j("initial-probe/initial-service-table.json")
    if sorted(r["temporary_entity_id"] for r in tab["rows"]) != COHERENT or \
            sorted(r["temporary_entity_id"] for r in tab["deferred"]) != DEFERRED or \
            any(r["state"] != DEFERRED_STATE for r in tab["deferred"]):
        bad.append("initial table")
    if sorted(int(k) for k in x.j("contexts/contexts.json")["entities"]) != COHERENT or \
            sorted(int(k) for k in x.charts()) != COHERENT:
        bad.append("contexts / charts entity sets")
    return not bad, {"problems": bad[:6]}


def c05(x):
    rows = own_seed_rows()
    chs = x.charts()
    bad, worst = [], 0.0
    for k in x.ids():
        ch = chs[str(k)]
        r = int(rows[k]["initialized_at_rank"])
        g0 = own_dir(*GAZES[r])
        mine = own_chart(g0)
        rr = np.asarray(ch["R_HC"], float)
        perp = float(np.linalg.norm(np.cross(np.cross(g0, [1.0, 0, 0]), g0)))
        centre = own_yp(rr.T @ g0)
        p = np.random.default_rng(k).normal(size=(20, 3))
        worst = max(worst, float(np.abs(mine - rr).max()))
        if not (float(np.abs(mine - rr).max()) <= 1e-15 and float(np.abs(rr.T @ rr - np.eye(3)).max()) <= ROUND
                and abs(float(np.linalg.det(rr)) - 1.0) <= ROUND and max(map(abs, centre)) <= 1e-9 and perp >= 1e-6
                and float(np.abs((p @ rr) @ rr.T - p).max()) <= ROUND and ch["seed_gaze_H0_deg"] == list(GAZES[r])
                and ch["initialization_rank"] == r and ch["chart_id"] == f"C_{k}"
                and ch["R_HC_sha256"] == hashlib.sha256(np.ascontiguousarray(rr).tobytes()).hexdigest()):
            bad.append(f"chart {k}")
    nb = json.loads((NS1B / "chart/policy-chart.json").read_text())
    same172 = np.array_equal(np.asarray(chs[str(CONTINUING)]["R_HC"]), np.asarray(nb["R_HC"]))
    for st in x.states():                                     # fixed for the whole experiment
        for k, rec in st["entities"].items():
            if rec["chart_sha256"] != chs[k]["R_HC_sha256"] or rec["chart_id"] != chs[k]["chart_id"]:
                bad.append(f"{st['label']}: entity {k} chart changed")
    for p in probe_paths(x):                                  # every policy computation used the entity's own chart
        pf = json.loads(p.read_text())
        if np.asarray(pf["probe"]["adapter"]["R_HC"]).tolist() != chs[str(pf["entity"])]["R_HC"]:
            bad.append(f"{p.name}: probe chart is not the entity's fixed chart")
    return not bad and same172, {"problems": bad[:6], "max_diff_own_chart": worst, "c172_equals_ns1b": same172}


def probe_paths(x: X) -> list[Path]:
    out = sorted((x.run / "initial-probe/probes").glob("e*.json"))
    if x.has("steps"):
        out += sorted((x.run / "steps").glob("step-*/update/probes/e*.json"))
    return out


def c06(x):
    import fsg6f_public as PUB
    from fov3d.control import frontier_config
    from fov3d.experiments.classroom_oracle import config as public, controller01 as c01m
    import tools.classroom_oracle1_epistemic as EPL
    used = x.j("initial-probe/initial-service-table.json")["policy_configuration_used"]
    live = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "facade": dict(frontier_config.SURFACE_FRONTIER),
            "FUSION": dict(PUB.FUSION), "OBJECT_ID": int(PUB.OBJECT_ID), "grid": float(public.CYCLOPEAN_GRID_DEG),
            "c_fusion": dict(public.FUSION), "shape": list(EPL.make_evidence().shape), "watchdog": int(c01m.WATCHDOG)}
    rec = {"SURFACE_FRONTIER": used["SURFACE_FRONTIER"], "facade": used["SURFACE_FRONTIER_facade"],
           "FUSION": used["FSG6F_FUSION"], "OBJECT_ID": used["OBJECT_ID"], "grid": used["CYCLOPEAN_GRID_DEG"],
           "c_fusion": used["FUSION"], "shape": used["cyclopean_chart_shape"],
           "watchdog": x.j("source/source-manifest.json")["accepted_constants"]["WATCHDOG"]}
    want = {"SURFACE_FRONTIER": POLICY, "facade": POLICY, "FUSION": FUSION, "OBJECT_ID": OBJECT_ID, "grid": CYC_GRID,
            "c_fusion": FUSION, "shape": CYC_SHAPE, "watchdog": WATCHDOG}
    dom = used["cyclopean_domain_deg"] == [-25.0, 25.0, -20.0, 20.0]
    return live == want and rec == want and dom, {"live_equal": live == want, "recorded_equal": rec == want,
                                                  "recorded_diff": {k: rec[k] for k in rec if rec[k] != want[k]}}


def c07(x):
    bad = []
    seen = set()
    for st in x.states():
        for k, rec in st["entities"].items():
            for look in rec["looks"]:
                if look["calibration"] in seen:
                    continue
                seen.add(look["calibration"])
                if not fixed_head(json.loads(x.res(look["calibration"]).read_text())):
                    bad.append(f"look {look['calibration']} is not the fixed head")
    chs = x.charts()
    for k, d in x.decisions():
        if d["kind"] != "attend":
            continue
        t = str(d["action"]["target"])
        r = np.asarray(chs[t]["R_HC"], float)
        w = own_world(d["action"]["local_gaze_deg"], r)
        real = own_calibration(*w)
        fake = own_calibration(*d["action"]["local_gaze_deg"])
        plan = json.loads((x.run / x.sd(k) / "plan/planned-calibration.json").read_text())
        if not (fixed_head(plan) and cal_close(plan, real) and not cal_close(plan, fake)):
            bad.append(f"step {k}: planned calibration is not the real sensor at the world gaze")
        if x.has(f"{x.sd(k)}/observation/acquisition/calibration.json"):
            exe = x.j(f"{x.sd(k)}/observation/acquisition/calibration.json")
            if not (fixed_head(exe) and cal_close(exe, real) and not cal_close(exe, fake)):
                bad.append(f"step {k}: executed calibration")
    for p in probe_paths(x):
        pf = json.loads(p.read_text())
        pr = pf["probe"]
        r = np.asarray(chs[str(pf["entity"])]["R_HC"], float)
        for p3 in pr["adapter"]["p3"]:
            w = own_world(p3["local_gaze_deg"], r)
            if (max(abs(w[0] - p3["world_gaze_deg"][0]), abs(w[1] - p3["world_gaze_deg"][1])) > 1e-9
                    or p3["calibration_gaze_deg"] != p3["world_gaze_deg"] or p3["tangent_frame"] != "baseline_projected"
                    or max(abs(p3["calibration_gaze_deg"][0] - p3["local_gaze_deg"][0]),
                           abs(p3["calibration_gaze_deg"][1] - p3["local_gaze_deg"][1])) < 1e-6):
                bad.append(f"{p.name}: P3 is not the real sensor at the world gaze")
        pc = pr["gate"]["detail"].get("predicted_calibration")
        if pc is not None and pr["proposal"] is not None:
            w = own_world(pr["proposal"]["local_gaze_deg"], r)
            if not (fixed_head(pc) and cal_close(pc, own_calibration(*w))
                    and not cal_close(pc, own_calibration(*pr["proposal"]["local_gaze_deg"]))):
                bad.append(f"{p.name}: gate predicted calibration")
    return not bad, {"problems": bad[:6], "looks_checked": len(seen)}


def c08(x):
    s0 = x.j("scene/state-initial.json")
    bad = []
    if str(CONTINUING) not in s0["entities"]:
        return False, {"problems": ["172 is not in the scene"]}
    r = s0["entities"][str(CONTINUING)]
    if [lk["calibration"] for lk in r["looks"]] != ["ns1a:observations/rank-06/acquisition/calibration.json",
                                                     "ns1b:observation/acquisition/calibration.json"]:
        bad.append("172 looks")
    if not arrays_equal(load(x.res(r["looks"][0]["state"])), load(NS1B / "context/controller-state.npz")) or \
            not arrays_equal(load(x.res(r["looks"][1]["state"])), load(NS1B / "post/controller-state.npz")):
        bad.append("172 look states != NS1b")
    if not arrays_equal(load(x.res(r["evidence"]["path"])), load(NS1B / "post/evidence.npz")):
        bad.append("172 evidence != NS1b post-action evidence")
    m = load(x.res(r["map"]["path"]))
    if not arrays_equal(m, load(NS1B / "fusion/fused-target-map.npz")) or len(m["xyz_h"]) != 21243 or \
            r["map"]["surfels"] != 21243:
        bad.append("172 map != the NS1b post-action map (21,243)")
    if r["own_looks"] != 2 or r["visited"] != [[0.0, 0.0], [0.0, -5.0]] or r["current_local_gaze"] != [0.0, -5.0]:
        bad.append("172 own looks / visited / gaze")
    import ns1b_core as B
    import ns1c_core as CORE
    maps = load(NS1A / "seeds/entity-maps.npz")
    ofz = json.loads((NS1A / "freeze/observation-freeze.json").read_text())
    states = {}
    for k in x.ids():
        rec = s0["entities"][str(k)]
        rank = int(rec["initialization_rank"])
        cal_rel = f"observations/rank-{rank:02d}/acquisition/calibration.json"
        if sha256(NS1A / cal_rel) != ofz["files"][cal_rel] or rec["looks"][0]["calibration"] != f"ns1a:{cal_rel}" or \
                rec["looks"][0]["calibration_sha256"] != ofz["files"][cal_rel]:
            bad.append(f"{k}: initialization look is not the frozen NS1a look")
        if rank not in states:
            obs = {n: sha256(NS1A / f"observations/rank-{rank:02d}/{d}/{n}") == ofz["files"][
                f"observations/rank-{rank:02d}/{d}/{n}"] for d, n in (("acquisition", "rgb-observation.npz"),
                                                                     ("oracle_aid", "reference-observation.npz"))}
            rec_m, _meta, st = B.matcher_state(json.loads((NS1A / cal_rel).read_text()),
                                               load(NS1A / f"observations/rank-{rank:02d}/acquisition/rgb-observation.npz"),
                                               load(NS1A / f"observations/rank-{rank:02d}/oracle_aid/reference-observation.npz"))
            states[rank] = ({**{kk: st[kk] for kk in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")},
                             "matcher_valid": np.asarray(rec_m["valid"], bool)}, all(obs.values()))
        own_st, frozen = states[rank]
        if not frozen or not arrays_equal(load(x.res(rec["looks"][0]["state"])), own_st):
            bad.append(f"{k}: the initialization controller state is not the accepted matcher on the frozen look")
        if k == CONTINUING:
            continue
        mk = {f: np.asarray(maps[f"e{k:05d}_{f}"]) for f in ("xyz_h", "rgb", "instance_id", "support_count",
                                                            "provenance_mask")}
        mm = load(x.res(rec["map"]["path"]))
        if not all(np.array_equal(np.asarray(mm[f]), mk[f]) for f in mk) or len(rec["looks"]) != 1 or \
                rec["own_looks"] != 1 or rec["visited"] != [[0.0, 0.0]] or rec["current_local_gaze"] != [0.0, 0.0]:
            bad.append(f"{k}: map / own looks / visited")
        ev = CORE.evidence_arrays(CORE.rebuild_context(rec, x.run, np.asarray(x.charts()[str(k)]["R_HC"], float)))
        if not arrays_equal(ev, load(x.res(rec["evidence"]["path"]))):
            bad.append(f"{k}: evidence does not recompute")
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    no_render = "acquire" not in order or order.index("acquire") > order.index("initial-probe")
    return not bad and no_render, {"problems": bad[:6], "no_render_before_initial_probe": no_render}


def own_probe(x: X, rec: dict, k: str):
    import ns1c_core as CORE
    cal0 = json.loads(x.res(rec["looks"][0]["calibration"]).read_text())
    return CORE.probe_entity(rec, x.run, x.charts()[k], np.asarray(cal0["head_R_wh"]),
                             np.asarray(cal0["head_origin_w_m"]), f"checker probe {k}")


def probe_key(rec: dict, k: str) -> str:
    """Cache key of a recomputed probe: everything the probe reads from the record."""
    return "probe-" + k + hashlib.sha256(json.dumps({f: rec[f] for f in ("looks", "evidence", "map", "visited",
                                                                          "current_local_gaze")},
                                                     sort_keys=True).encode()).hexdigest()


def probe_diffs(saved: dict, mine: dict) -> list[str]:
    import ns1b_core as B
    d = B.probe_comparison(saved, B.jsonable(mine), 0.0)
    if (saved["proposal"] is None) != (mine["proposal"] is None):
        d.append("proposal presence")
    elif saved["proposal"] is not None:
        d += B.compare(saved["proposal"], B.jsonable(mine["proposal"]), 0.0, "proposal",
                       skip=("physical_calibration_test", "planned_calibration_test", "gate_predicted_equals_planned"))
    return d


def c09(x):
    import ns1c_core as CORE
    s0 = x.j("scene/state-initial.json")
    bad, inv = [], {}
    for k in map(str, x.ids()):
        rec = s0["entities"][k]
        saved = json.loads((x.run / f"initial-probe/probes/e{int(k):05d}.json").read_text())
        if rec["probe"]["path"] != f"run:initial-probe/probes/e{int(k):05d}.json" or \
                rec["probe"]["sha256"] != sha256(x.res(rec["probe"]["path"])):
            bad.append(f"{k}: probe record")
        mine = memo(x, probe_key(rec, k), lambda rec=rec, k=k: own_probe(x, rec, k))
        d = probe_diffs(saved["probe"], mine)
        if d:
            bad.append(f"{k}: recomputed probe differs {d[:2]}")
        if not all(r["pass"] for r in saved["baseline_rotation_invariance"]) or \
                [r["beta_deg"] for r in saved["baseline_rotation_invariance"]] != [37.0, -61.0]:
            bad.append(f"{k}: recorded rotation invariance")
        cal0 = json.loads(x.res(rec["looks"][0]["calibration"]).read_text())
        rot = CORE.rotation_invariance(rec, x.run, x.charts()[k], mine, np.asarray(cal0["head_R_wh"]),
                                       np.asarray(cal0["head_origin_w_m"]), betas=(-23.0,))
        inv[k] = rot[0]["pass"]
        if not rot[0]["pass"]:
            bad.append(f"{k}: the checker's own rotation (-23 deg) differs {rot[0]['differences'][:2]}")
    n = [e for e in x.log() if e["command"] == "initial-probe" and e["status"] == "ok"]
    guard = x.j("initial-probe/initial-probe-opened-files.json")
    no_truth = not any(p.endswith(("reference-observation.npz", ".exr")) for p in guard["data_reads"])
    ok = not bad and len(n) == 1 and not guard["violations"] and no_truth
    return ok, {"problems": bad[:6], "own_rotation": inv, "runs": len(n), "no_position_read": no_truth}


def c10(x):
    saved = json.loads((x.run / f"initial-probe/probes/e{CONTINUING:05d}.json").read_text())["probe"]
    acc = json.loads((NS1B / "post/post-action-probe.json").read_text())
    d = probe_diffs(acc["probe"], saved) if sha256(NS1B / "post/post-action-probe.json") == \
        NS1B_PINS["post/post-action-probe.json"] else ["accepted record changed"]
    p = saved["proposal"] or {}
    got = {"state": "ACTIONABLE" if p and saved["gate"]["admissible"] else "QUIET", "source": p.get("source"),
           "local": p.get("local_gaze_deg"), "admissible": saved["gate"]["admissible"],
           "novel": ((saved["gate"]["detail"] or {}).get("counts") or {}).get("novel_service_count")}
    rep = x.j("initial-probe/initial-service-table.json")["ns1b_reproduction"]
    ok = not d and got == NS1B_POST and rep["reproduced"] and rep["difference_count"] == 0
    return ok, {"differences": d[:4], "got": got}


def c11(x):
    bad = []
    blocked: dict[str, str | None] = {}
    tab = {r["temporary_entity_id"]: r for r in x.j("initial-probe/initial-service-table.json")["rows"]}
    for st in x.states():
        for k, rec in st["entities"].items():
            pf = probe_file(x, rec)
            if sha256(x.res(rec["probe"]["path"])) != rec["probe"]["sha256"]:
                bad.append(f"{st['label']} {k}: probe file changed")
            mine = own_service(pf["probe"], rec["own_looks"], blocked.get(k))
            if rec["service"]["label"] != mine:
                bad.append(f"{st['label']} {k}: service {rec['service']['label']} != own {mine}")
            if mine.startswith("BLOCKED"):
                blocked[k] = mine.split(":")[1]
            if pf["revision"] != rec["probe"]["revision"]:
                bad.append(f"{st['label']} {k}: probe revision")
        if st["label"] == "initial":
            for k, rec in st["entities"].items():
                if tab[int(k)]["service_state"] != rec["service"]["label"]:
                    bad.append(f"initial table {k}")
    return not bad, {"problems": bad[:6]}


def c12(x):
    from fov3d.control import integrated as ic
    sts = x.states()
    bad = []
    if sts[0]["current"] != CONTINUING or sts[0]["attention_bout"] != 1:
        bad.append("the initial current object is not 172 (bout 1)")
    bout, reac = 1, set()
    for i, (k, d) in enumerate(x.decisions()):
        prev = sts[i] if i < len(sts) else None
        if prev is None or prev["global_step"] != k - 1:
            bad.append(f"step {k}: no preceding scene state")
            break
        rows = [ic.ObjectSummary(int(kk), ic.ServiceState(r["service"]["label"].split(":")[0]),
                                 r["service"]["label"].split(":")[1] if ":" in r["service"]["label"] else None)
                for kk, r in sorted(prev["entities"].items(), key=lambda t: int(t[0]))]
        mine = ic.schedule(prev["current"], rows)
        rec = d["scheduler_decision"]
        if [mine.kind, mine.target_id, mine.reason] != [rec["kind"], rec["target_id"], rec["reason"]] or \
                d["kind"] not in (mine.kind, "cap") or rec["current_before"] != prev["current"] or \
                [[int(s.instance_id), s.label] for s in rows] != rec["summaries"]:
            bad.append(f"step {k}: recomputed {mine.kind}/{mine.target_id}/{mine.reason} != recorded "
                       f"{rec['kind']}/{rec['target_id']}/{rec['reason']}")
            continue
        if mine.kind == "terminal":
            continue
        reason = mine.reason
        if reason == "switch" and mine.target_id in set(prev["reactivated_since_attended"]):
            reason = "natural_reactivation"
        bout += 1 if mine.reason in ("initial", "switch") else 0
        if d["scheduler_reason"] != reason or d["attention_bout"] != bout:
            bad.append(f"step {k}: reason / bout")
        if d["kind"] == "attend":
            t = str(mine.target_id)
            pf = probe_file(x, prev["entities"][t])["probe"]
            a = d["action"]
            if (int(a["target"]) != mine.target_id or pf["proposal"] is None or a["local_gaze_deg"] !=
                    pf["proposal"]["local_gaze_deg"] or a["source"] != pf["proposal"]["source"]
                    or a["proposal_probe"]["path"] != prev["entities"][t]["probe"]["path"]
                    or d["target_transition"] != ("retain" if prev["current"] == int(t) else f"{prev['current']}->{t}")
                    or a["patch_id"] != f"ns1c_step_{k:02d}"):
                bad.append(f"step {k}: the action is not the selected entity's frozen admissible proposal")
    import ns1c_core  # noqa: F401
    src = (HERE / "ns1c_core.py").read_text()
    uses = "from fov3d.control import integrated as ic" in src and "d = ic.schedule(current, rows)" in src
    return not bad and uses, {"problems": bad[:6], "uses_accepted_schedule": uses}


def c13(x):
    chs = x.charts()
    bad = []
    for k, d in x.decisions():
        if d["kind"] != "attend":
            continue
        a = d["action"]
        r = np.asarray(chs[str(a["target"])]["R_HC"], float)
        w = own_world(a["local_gaze_deg"], r)
        back = own_yp(r.T @ own_dir(*w))
        plan = (x.run / x.sd(k) / "plan/planned-calibration.json").read_bytes()
        if (max(abs(w[0] - a["world_gaze_deg"][0]), abs(w[1] - a["world_gaze_deg"][1])) > 1e-9
                or max(abs(back[0] - a["local_gaze_deg"][0]), abs(back[1] - a["local_gaze_deg"][1])) > 1e-9
                or cal_bytes(own_calibration(*a["world_gaze_deg"])) != plan
                or hashlib.sha256(plan).hexdigest() != a["planned_calibration_sha256"]):
            bad.append(f"step {k}: world gaze / planned calibration")
        if x.has(f"{x.sd(k)}/observation/acquisition/calibration.json") and \
                (x.run / x.sd(k) / "observation/acquisition/calibration.json").read_bytes() != plan:
            bad.append(f"step {k}: executed calibration != planned")
        ar = x.j(f"{x.sd(k)}/observation/acquisition-run.json") if x.has(f"{x.sd(k)}/observation/acquisition-run.json") \
            else None
        if ar is not None and (ar["gaze_H0_deg"] != a["world_gaze_deg"] or int(ar["target"]) != int(a["target"])):
            bad.append(f"step {k}: acquisition gaze / target")
    return not bad, {"problems": bad[:6]}


def c14(x):
    sts = x.states()
    bad = []
    src = x.j("source/source-manifest.json")
    if src["watchdog"] != WATCHDOG or any(st["watchdog"] != WATCHDOG or st["cap"] != WATCHDOG for st in sts):
        bad.append("watchdog / cap")
    s0 = sts[0]
    if {k: r["own_looks"] for k, r in s0["entities"].items()} != {str(k): (2 if k == CONTINUING else 1)
                                                                  for k in x.ids()}:
        bad.append("initial own looks")
    for i, st in enumerate(sts[1:], start=1):
        prev = sts[i - 1]
        t = str(st["last_action"]["target"])
        for k, rec in st["entities"].items():
            want = prev["entities"][k]["own_looks"] + (1 if k == t else 0)
            vis = prev["entities"][k]["visited"] + ([st["last_action"]["local_gaze_deg"]] if k == t else [])
            if rec["own_looks"] != want or rec["visited"] != vis or len(rec["looks"]) != want:
                bad.append(f"{st['label']} {k}: own looks / visited")
        if st["executed_actions"] != i or st["executed_actions"] > WATCHDOG:
            bad.append(f"{st['label']}: executed actions")
    if len(x.executed()) > WATCHDOG:
        bad.append("more actions than the cap")
    return not bad, {"problems": bad[:6], "actions": len(x.executed())}


def c15(x):
    acc = json.loads(Path(AB1D2_ACQ[0]).read_text())["settings"] if sha256(AB1D2_ACQ[0]) == AB1D2_ACQ[1] else None
    bad = []
    for k, d in x.executed():
        s = x.sd(k)
        ar = x.j(f"{s}/observation/acquisition-run.json")
        rec = x.j(f"{s}/observation/acquisition/acquisition.json")
        fz = x.j(f"{s}/freeze/observation-freeze.json")
        pre = x.j(f"{s}/preflight/preflight.json")
        files_ok = all(sha256(x.run / s / f) == h for f, h in fz["files"].items())
        seal = sha256(x.run / s / "observation/evaluation_only/instance-catalog.json")
        n_acq = sum(1 for e in x.log() if e["command"] == "acquire" and e["step"] == k and e["status"] == "ok")
        if not (ar["spp"] == rec["spp"] == rec["settings"]["samples"] == SPP and rec["render_seeds_lr"] == SEEDS
                and rec["device"] == "OPTIX" and acc is not None and rec["settings"] == acc
                and ar["exr_samples_lr"] == {"L": str(SPP), "R": str(SPP)} and files_ok
                and ar["catalog_seal"]["sha256"] == seal == NS1A_CATALOG_SEAL and n_acq == 1
                and pre["rendered"] is False and pre["calibration_identity"]["byte_identical_to_planned"]
                and rec["settings"]["denoising"] is False and rec["settings"]["adaptive_sampling"] is False
                and rec["settings"]["pixel_filter"] == "BOX" and rec["settings"]["filter_width"] == 1.0
                and not rec.get("rehearsal")):
            bad.append(f"step {k}: observation")
    return not bad, {"problems": bad[:6], "steps": [k for k, _ in x.executed()]}


def c16(x):
    import check_ns1a as A
    bad, counts = [], {}
    for k, _d in x.executed():
        s = x.sd(k)
        c = x.j(f"{s}/observation/acquisition/calibration.json")
        ref = load(x.run / s / "observation/oracle_aid/reference-observation.npz")
        prod = load(x.run / s / "correspondence/oracle-correspondences.npz")
        o = A.own_oracle(c, ref)
        idx = prod["left_core_row"].astype(np.int64) * 256 + prod["left_core_col"]
        same = np.array_equal(np.sort(idx), o["keep"]) and np.array_equal(idx, np.sort(idx))
        du = float(np.abs(prod["uv_R"] - o["uv_R"]).max()) if same and len(idx) else (0.0 if same else math.inf)
        keys = sorted(prod) == ["left_core_col", "left_core_row", "uv_L", "uv_R"]
        cont = bool(len(prod["uv_R"]) == 0 or not np.array_equal(prod["uv_R"], np.rint(prod["uv_R"])))
        cls = load(x.run / s / "correspondence/core-class-map.npz")["core_class"]
        rec = x.j(f"{s}/correspondence/correspondence-opened-files.json")
        reads = {x.rel(p) for p in rec["data_reads"]}
        counts[k] = int(len(idx))
        if not (same and du <= 1e-9 and keys and cont and np.array_equal(cls, o["class"]) and not rec["violations"]
                and reads == {f"{s}/observation/acquisition/calibration.json",
                              f"{s}/observation/oracle_aid/reference-observation.npz",
                              f"{s}/freeze/observation-freeze.json"} and not rec["modules_loaded"]["cv2"]):
            bad.append(f"step {k}: correspondence (same {same}, du {du}, reads {sorted(reads)[:3]})")
    return not bad, {"problems": bad[:4], "correspondences": counts}


def c17(x):
    import check_ns1a as A
    bad = []
    order = [(e["command"], e["step"]) for e in x.log() if e["status"] == "ok"]
    for k, _d in x.executed():
        s = x.sd(k)
        c = x.j(f"{s}/observation/acquisition/calibration.json")
        prod = load(x.run / s / "correspondence/oracle-correspondences.npz")
        res = load(x.run / s / "geometry/epipolar-result.npz")
        g = A.own_geometry(c, prod)
        v = np.asarray(res["valid_epi"], bool)
        dp = float(np.abs(g["P"][v] - res["P_epi"][v]).max()) if v.any() else 0.0
        rec = x.j(f"{s}/geometry/geometry-opened-files.json")
        reads = {x.rel(p) for p in rec["data_reads"]}
        mods = rec["modules_loaded"]
        fz, cfz = x.j(f"{s}/freeze/geometry-freeze.json"), x.j(f"{s}/freeze/correspondence-freeze.json")
        if not (dp <= 1e-9 and reads == {f"{s}/observation/acquisition/calibration.json",
                                         f"{s}/correspondence/oracle-correspondences.npz"}
                and not any(mods[m] for m in ("cv2", "fsg_stereo", "ab1b_oracle", "ab1d3_sgbm", "ab1d_match",
                                              "fsg6f_frontier"))
                and rec["position_reads"] == rec["object_index_reads"] == rec["catalog_reads"] == 0
                and not rec["violations"] and all(sha256(x.run / s / f) == h for f, h in fz["files"].items())
                and all(sha256(x.run / s / f) == h for f, h in cfz["files"].items())
                and order.index(("freeze-geometry", k)) < order.index(("local-oracle-segmentation", k))):
            bad.append(f"step {k}: geometry (dp {dp})")
    return not bad, {"problems": bad[:4]}


def c18(x):
    bad = []
    for k, _d in x.executed():
        s = x.sd(k)
        prod = load(x.run / s / "correspondence/oracle-correspondences.npz")
        res = load(x.run / s / "geometry/epipolar-result.npz")
        ref = load(x.run / s / "observation/oracle_aid/reference-observation.npz")
        idn = load(x.run / s / "segmentation/local-identity.npz")
        uv = prod["uv_L"].astype(np.int64)
        mine = np.where(np.asarray(res["valid_epi"], bool), ref["instance_L"][uv[:, 1], uv[:, 0]], -1) if len(uv) else \
            np.zeros(0, np.int32)
        rec = x.j(f"{s}/segmentation/segmentation-opened-files.json")
        marks = [e["label"] for e in rec["events"] if e.get("event") == "mark"]
        if not (np.array_equal(mine, idn["temporary_entity_id"]) and rec["reference_members_read"] == ["instance_L"]
                and marks == ["geometry_freeze_verified", "identity_access_begins"] and not rec["violations"]):
            bad.append(f"step {k}: identity")
    return not bad, {"problems": bad[:4]}


def c19(x):
    import ns1b_core as B
    import ns1c_core as CORE
    sts = x.states()
    bad, rows = [], {}
    pids = set()
    for i, (k, d) in enumerate(x.executed(), start=1):
        s = x.sd(k)
        fu = x.j(f"{s}/fusion/fusion.json")
        t = int(d["action"]["target"])
        prev, after = sts[i - 1], sts[i]
        res = load(x.run / s / "geometry/epipolar-result.npz")
        ids = load(x.run / s / "segmentation/local-identity.npz")["temporary_entity_id"]
        keep = np.asarray(res["valid_epi"], bool) & (ids == t)
        patch = load(x.run / s / "fusion/target-patch.npz")
        patch_ok = np.array_equal(patch["xyz_h"], np.asarray(res["P_epi"], np.float64)[keep]) and \
            np.all(patch["instance_id"] == t)
        mrec = prev["entities"][str(t)]["map"]
        sm = CORE.load_map(x.res(mrec["path"]))
        p = {"frame": "H0", "patch_id": f"ns1c_step_{k:02d}", "xyz_h": patch["xyz_h"], "rgb": patch["rgb"],
             "instance_id": patch["instance_id"], "points": int(len(patch["xyz_h"]))}
        fused, rec = B.fuse_h0(sm, p, t, RADIUS, CELL)
        saved = load(x.run / s / "fusion/fused-target-map.npz")
        same = B.maps_equal(B.map_arrays(fused), saved)
        m0 = load(x.res(mrec["path"]))
        own = own_association(m0["xyz_h"], patch["xyz_h"]) if len(patch["xyz_h"]) >= MIN_POINTS else np.zeros(0)
        own_m = int((own >= 0).sum())
        counts = (fu["action"] == "FUSED" and own_m == fu["matched"] and len(own) - own_m == fu["new"]
                  and len(np.unique(own[own >= 0])) == fu["affected_surfels"]) or \
            (fu["action"] == "RETAINED_NOT_FUSED" and fu["measured_points"] < MIN_POINTS)
        frame_ok = fu["frame"] == "H0" if fu["action"] == "FUSED" else True
        untouched = all(after["entities"][kk]["map"] == prev["entities"][kk]["map"] for kk in after["entities"]
                        if int(kk) != t)
        new_map_ok = (after["entities"][str(t)]["map"]["path"] == f"run:{s}/fusion/fused-target-map.npz"
                      if fu["action"] == "FUSED" else after["entities"][str(t)]["map"] == mrec)
        pid_ok = fu["patch_id"] == f"ns1c_step_{k:02d}" and fu["patch_id"] not in pids and \
            fu["patch_id"] not in [str(v) for v in m0["patch_ids"]]
        pids.add(fu["patch_id"])
        if not (patch_ok and same and counts and frame_ok and untouched and new_map_ok and pid_ok
                and fu.get("radius_m", RADIUS) == RADIUS and fu.get("hash_cell_m", CELL) == CELL
                and (fu["action"] != "FUSED" or (fu["replay"]["exact"] and fu["replay"]["duplicate_patch"]))
                and np.all(saved["instance_id"] == t) and fu["measured_points"] == int(keep.sum())
                and rec["action"] == fu["action"] and int(fu["target"]) == t
                and fu["map_before_sha256"] == mrec["sha256"] == sha256(x.res(mrec["path"]))):
            bad.append(f"step {k}: fusion (patch {patch_ok}, fuse {same}, counts {counts}, untouched {untouched}, "
                       f"new map {new_map_ok}, pid {pid_ok}, frame {frame_ok})")
        rows[k] = {kk: fu[kk] for kk in ("target", "action", "map_before", "measured_points", "matched", "new",
                                          "map_after")}
    return not bad, {"problems": bad[:4], "fusions": rows}


def c20(x):
    import ns1b_core as B
    import ns1c_core as CORE
    sts = x.states()
    bad = []
    for i, (k, d) in enumerate(x.executed(), start=1):
        s = x.sd(k)
        t = str(d["action"]["target"])
        prev, after = sts[i - 1], sts[i]
        new = after["entities"][t]
        cal1 = x.j(f"{s}/observation/acquisition/calibration.json")
        rec1, _m, st1 = B.matcher_state(cal1, load(x.run / s / "observation/acquisition/rgb-observation.npz"),
                                        load(x.run / s / "observation/oracle_aid/reference-observation.npz"))
        own_st = {**{kk: st1[kk] for kk in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")},
                  "matcher_valid": np.asarray(rec1["valid"], bool)}
        if not arrays_equal(load(x.run / s / "update/controller-state.npz"), own_st):
            bad.append(f"step {k}: controller state does not recompute")
        r = np.asarray(x.charts()[t]["R_HC"], float)
        ev = CORE.evidence_arrays(CORE.rebuild_context(new, x.run, r))
        if not arrays_equal(ev, load(x.res(new["evidence"]["path"]))):
            bad.append(f"step {k}: evidence does not recompute from the looks")
        mine = memo(x, probe_key(new, t), lambda new=new, t=t: own_probe(x, new, t))
        saved = probe_file(x, new)
        dd = probe_diffs(saved["probe"], mine)
        if dd or new["probe"]["provenance"] != "fresh" or new["probe"]["path"] != f"run:{s}/update/probes/e{int(t):05d}.json" \
                or saved["executed"] is not False:
            bad.append(f"step {k}: target re-probe {dd[:2]}")
        if new["revision"] != [new["own_looks"], new["map"]["surfels"]] or \
                new["revision"] == prev["entities"][t]["revision"]:
            bad.append(f"step {k}: target revision")
        for kk, rec in after["entities"].items():
            if kk == t:
                continue
            if rec["probe"]["path"] != prev["entities"][kk]["probe"]["path"] or rec["probe"]["provenance"] != "cached" \
                    or rec["revision"] != prev["entities"][kk]["revision"] or rec["service"] != prev["entities"][kk]["service"]:
                bad.append(f"step {k}: untouched entity {kk} changed")
        upd = x.j(f"{s}/update/update.json")
        if upd["probe_calls"] != 1 or upd["probe_cache_hits"] != len(x.ids()) - 1 or \
                upd["north_star_target_points"] != x.j(f"{s}/fusion/fusion.json")["measured_points"] or \
                upd["controller_state_target_support"] != int((np.asarray(rec1["valid"], bool)
                                                               & (np.asarray(rec1["instance_id"]) == int(t))).sum()):
            bad.append(f"step {k}: update record")
    return not bad, {"problems": bad[:6], "steps": len(x.executed())}


def c21(x):
    sts = x.states()
    touched = {str(d["action"]["target"]) for _k, d in x.executed()}
    bad, checked = [], []
    for k in map(str, x.ids()):
        if k in touched:
            continue
        labs = {st["entities"][k]["service"]["label"] for st in sts}
        if len(labs) != 1:
            bad.append(f"{k}: an untouched entity changed service state {labs}")
        rec = sts[-1]["entities"][k]
        mine = memo(x, probe_key(rec, k), lambda rec=rec, k=k: own_probe(x, rec, k))
        d = probe_diffs(json.loads((x.run / f"initial-probe/probes/e{int(k):05d}.json").read_text())["probe"], mine)
        if d:
            bad.append(f"{k}: the untouched entity's probe from scratch differs from its initial probe {d[:2]}")
        checked.append(int(k))
        if any(e["object"] == int(k) for st in sts for e in st.get("events", [])):
            bad.append(f"{k}: an event on an untouched entity")
    return not bad, {"problems": bad[:6], "untouched_checked": checked}


def c22(x):
    ex = x.executed()
    targets = [int(d["action"]["target"]) for _k, d in ex]
    first = next((i for i, t in enumerate(targets) if t != CONTINUING), None)
    final = x.has("scene/final-scene-state.json")
    term = x.has("scene/terminal.json")
    bad = []
    later = sorted(int(p.name.split("-")[1]) for p in (x.run / "steps").glob("step-*")) if x.has("steps") else []
    if first is not None:
        k, d = ex[first]
        st = x.j(f"scene/state-after-step-{k:02d}.json")
        fz = x.j("freeze/scene-freeze.json") if x.has("freeze/scene-freeze.json") else {"files": {}}
        fin = x.j("scene/final-scene-state.json") if final else {}
        post = st["stop"]["post_action_probe_of_new_target"] if st.get("stop") else {}
        if (first != len(targets) - 1 or not final or term or later[-1] != k or not st["stopped"]
                or st["stop"]["to"] != targets[first] or st["stop"]["from"] != CONTINUING
                or {kk: v for kk, v in fin.items() if kk != "label"} != {kk: v for kk, v in st.items() if kk != "label"}
                or not fz["files"] or any(sha256(x.run / f) != h for f, h in fz["files"].items())
                or post.get("executed") is not False
                or post.get("path") != f"run:{x.sd(k)}/update/probes/e{targets[first]:05d}.json"
                or len(set(targets)) > 2 or any(t != CONTINUING for t in targets[:first])
                or x.j(f"{x.sd(k)}/fusion/fusion.json")["action"] not in ("FUSED", "RETAINED_NOT_FUSED")):
            bad.append("the canonical stop is not exactly after the first successful action on a target != 172")
        sched_after = [e for e in x.log() if e["command"] == "schedule" and e["status"] == "ok" and e["step"] > k]
        if sched_after:
            bad.append("an action was scheduled after the stop")
    else:
        if final or any(st.get("stopped") for st in x.states()):
            bad.append("a stop is recorded without a cross-entity action")
        if term:
            t = x.j("scene/terminal.json")
            lab = (t.get("terminal") or {}).get("label")
            if t["kind"] == "terminal" and lab not in TERMINAL_LABELS:
                bad.append(f"terminal label {lab}")
    return not bad, {"targets": targets, "first_cross_entity_step": None if first is None else ex[first][0],
                     "final": final, "terminal": term, "problems": bad}


def code_scan() -> dict:
    hits = []
    for name in PRODUCTION:
        tree = ast.parse((HERE / name).read_text())
        for node in ast.walk(tree):
            ident = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
            if ident in FORBIDDEN_IDENTIFIERS:
                hits.append(f"{name}: {ident}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                                                       else [])
                hits += [f"{name}: import {m}" for m in mods if m.split(".")[-1] in FORBIDDEN_MODULES]
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and CLOSED in node.value:
                hits.append(f"{name}: the closure marker literal")
    return {"hits": hits}


def c23(x):
    log = x.log()
    ok_e = ok_entries(x)
    once = [e["command"] for e in ok_e if e["command"] in ONCE]
    bad = []
    if once != ONCE:
        bad.append(f"once stages {once}")
    steps = sorted({e["step"] for e in ok_e if e["command"] in STEP})
    for k in steps:
        cmds = [e["command"] for e in ok_e if e["command"] in STEP and e["step"] == k]
        d = x.j(f"{x.sd(k)}/plan/decision.json")
        want = STEP if d["kind"] == "attend" else ["schedule"]
        if cmds != want:
            bad.append(f"step {k}: {cmds}")
    if steps != list(range(len(steps))):
        bad.append(f"steps {steps}")
    n_loop = sum(1 for e in ok_e if e["command"] == "loop")
    commits = {e["code"]["commit"] for e in ok_e}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] and not e["dev"] for e in ok_e)
    failed = [e["command"] for e in log if e["status"] == "failed" and e["command"] in ONCE + STEP + ["loop"]]
    scan = code_scan()
    ok = not bad and n_loop == 1 and len(commits) == 1 and clean and not failed and not scan["hits"]
    return ok, {"problems": bad[:4], "loops": n_loop, "commits": sorted(commits), "clean_pushed": clean,
                "failed": failed, "code_scan": scan["hits"]}


def c24(x):
    bad, truth = [], {}
    for f in guard_files(x):
        rec = x.j(f)
        if rec["violations"]:
            bad.append(f"{f}: violations")
        for e in opens(rec):
            if forbidden(e["path"]):
                bad.append(f"{f}: forbidden read {e['path']}")
            if e.get("kind") == "data-read" and e["path"].endswith(("reference-observation.npz", ".exr")):
                truth.setdefault(f, set()).add(Path(e["path"]).name)
    extra = sorted(f for f in truth if not f.endswith(TRUTH_STAGES))
    src = x.j("source/source-opened-files.json")          # the source stage only hashes the pinned files
    pinned = {str((NS1A / r).resolve()) for r in NS1A_PINS} | {str((NS1B / r).resolve()) for r in NS1B_PINS}
    if set(src["data_reads"]) - pinned:
        bad.append(f"source: reads beyond the pinned handoff files {sorted(set(src['data_reads']) - pinned)[:3]}")
    segs = [x.j(f)["reference_members_read"] for f in guard_files(x) if f.endswith("segmentation-opened-files.json")]
    return not bad and not extra and all(s == ["instance_L"] for s in segs), {
        "problems": bad[:5], "truth_reads_outside_allowed": extra, "truth_reading_stages": sorted(truth)[:8]}


def c25(x):
    hits = []
    for p in sorted(x.run.rglob("*.json")):
        if CLOSED in p.read_text():
            hits.append(str(p.relative_to(x.run)))
    if (x.vis / "visuals-manifest.json").exists() and CLOSED in (x.vis / "visuals-manifest.json").read_text():
        hits.append("visuals-manifest.json")
    labels = [(x.j("scene/terminal.json").get("terminal") or {}).get("label")] if x.has("scene/terminal.json") else []
    bad_lab = [lab for lab in labels if lab is not None and lab not in TERMINAL_LABELS]
    return not hits and not bad_lab, {"hits": hits[:5], "terminal_labels": labels}


def c26(x):
    import ns1c_visuals as V
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        figs, _dd = V.render_all(x.run)
        regen, metas = {}, {}
        for name, (im, meta) in figs.items():
            p = Path(td) / name
            im.save(p, format="PNG", optimize=False)
            regen[name] = sha256(p)
            metas[name] = meta
    on_disk = {n: sha256(x.vis / n) for n in FIGURES if (x.vis / n).exists()}
    same = sorted(regen) == sorted(FIGURES) and all(regen[n] == on_disk.get(n) == man["figures"][n]["sha256"]
                                                     for n in FIGURES)
    lab = all(man["figures"][n]["labels"] == LABELS[n] and man["figures"][n]["badges"] == BADGES[n] for n in FIGURES)
    stmt = man.get("fixed_head_statement") == "PHYSICAL HEAD FIXED - POLICY CHART ONLY" and \
        man.get("frames") == {"chart": "POLICY CHART C_i", "h0": "CANONICAL H0"}
    reasons = [d["scheduler_reason"] for _k, d in x.executed()]
    meta_ok = all(all(man["figures"][n].get(kk) == v for kk, v in metas[n].items()) for n in FIGURES)
    shown = (man["figures"]["overview.png"].get("deferred_shown") == DEFERRED
             and man["figures"]["scene-scheduler-timeline.png"].get("deferred_shown") == DEFERRED
             and man["figures"]["overview.png"].get("scheduler_reasons_shown") == reasons
             and man["figures"]["scene-scheduler-timeline.png"].get("scheduler_reasons_shown") == reasons)
    return same and lab and stmt and meta_ok and shown and sorted(man["figures"]) == sorted(FIGURES), {
        "regenerated_equal": same, "labels_badges": lab, "frame_statement": stmt, "meta_equal": meta_ok,
        "deferred_and_reasons_shown": shown}


def c27(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
        "manifest.json", "check-summary.json", "process-log.jsonl"}
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    return not bad and set(man["files"]) == present and not extra, {
        "mismatch": bad[:5], "unlisted": sorted(present - set(man["files"]))[:5], "undeclared_changes": extra}


CHECKS = [
    ("01", "provenance: canonical repo, base, NS1b / NS1a acceptance, contract first and unchanged", c01),
    ("02", "accepted sources and the frozen NS1a / NS1b handoffs pinned and unchanged; watchdog recorded", c02),
    ("03", "COHERENT_SEED_SET derived by own rule from the frozen NS1a seed set; expected ten; no names", c03),
    ("04", "deferred identities 10 / 110 / 178 absent from every scheduler input, summary, table and target", c04),
    ("05", "one fixed chart per entity: own construction, non-singular, never recentered; C_172 = NS1b chart", c05),
    ("06", "accepted policy constants and the watchdog unchanged, live and as recorded", c06),
    ("07", "fixed head: every physical calibration; P3 / planned / executed = real sensor at the world gaze", c07),
    ("08", "initial state: 172 = the NS1b post-action context and map; others = NS1a; no rerender", c08),
    ("09", "every coherent entity probed exactly once before any render; recomputed; own rotation invariance", c09),
    ("10", "the 172 initial probe reproduces the accepted NS1b post-action probe exactly", c10),
    ("11", "service states recomputed from the probes (gate, watchdog, sticky BLOCKED)", c11),
    ("12", "every scheduler decision = the accepted integrated.schedule on own summaries; current starts at 172", c12),
    ("13", "world gazes recomputed (own column form); planned = executed calibration bytes", c13),
    ("14", "watchdog / cap: accepted constant; own-look counts; only the target advances", c14),
    ("15", "observations: one pair per step, 4096 spp (record, readback, EXR), seeds, settings, seal", c15),
    ("16", "PERFECT correspondence reproduced by an own oracle per step; truth-stripped schema", c16),
    ("17", "spherical geometry reproduced by own triangulation per step; truth-free guard; frozen first", c17),
    ("18", "local oracle identity at the exact pixels; only instance_L read; after the geometry freeze", c18),
    ("19", "target-only H0 fusion: frozen P_epi, 12 / 12, accepted fuse + own association, idempotent", c19),
    ("20", "update: controller state, evidence and the target re-probe recomputed; cache semantics", c20),
    ("21", "reactivation: untouched entities unchanged; their probes recomputed from scratch equal", c21),
    ("22", "the canonical stop right after the first successful action with target != 172; no third entity", c22),
    ("23", "process: each stage once per step, in order, one clean pushed commit; no forbidden code", c23),
    ("24", "truth boundary: no catalog / name / evaluation read; truth only in the declared stages", c24),
    ("25", "terminology: no scene-closure marker anywhere", c25),
    ("26", "figures regenerate byte-identically; labels, badges, fixed-head statement, deferred, reasons", c26),
    ("27", "run manifest and declared changes", c27),
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
                detail, default=str)[:600]), flush=True)
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
    summary = {"schema": "NS1c-check-summary-v1", "checks": res, "failed": failed,
               "marker": "NORTH_STAR1C_CHECKS_PASS" if not failed else "NORTH_STAR1C_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1C_CHECKS_PASS")
    if a.corruptions:
        import check_ns1c_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
