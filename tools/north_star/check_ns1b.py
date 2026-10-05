#!/usr/bin/env python3
"""North Star-1b checker: fail-capable verification of the recentered local-controller handoff (read-only).

    .venv/bin/python tools/north_star/check_ns1b.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md, section 19.  The checker keeps its own literal
pins and constants and recomputes independently where an independent formula exists: the target selection (own
leverage |b x g|), the chart (own triple-product construction), the world-gaze mapping (own column-form rotation), the
fixed-head calibrations (own construction from the AB1a head pose), the perfect correspondence and the spherical
geometry (the accepted NS1a checker's own oracle and law-of-sines triangulation), the 12-mm association (own brute-force
nearest surfel).  The accepted policy itself has no independent implementation: its reproduction under the frame
adapter is established by the covariance known answers (identity on accepted states, rigid rotations), which the checker
re-runs (K4 once per process).  It audits every guard record, the process log, the code scope and the figures.
``--corruptions`` runs the mutation suite (check_ns1b_corruptions.py) from a passing mirror after a null probe.
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

PREFIX = "[ns1b-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
BASE = "889373d9c174c1c63ebc8d2f79847dbec281f2e8"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
CONTRACT = "1e641e66eac46be551b425d2f14a06e9607d533f"
CONTRACT_PATH = "docs/north-star/ns1b-recentered-controller-handoff-contract.md"
REPORT_PATH = "docs/north-star/ns1b-recentered-controller-handoff-report.md"
PREVIEWS = Path("/home/lvelho/rd/f3d-vision/previews")
NS1A = PREVIEWS / "north-star/ns1a-perfect-bootstrap-round"
NS1A_PINS = {"freeze/observation-freeze.json": "46f0a22eab852b3c5750420ed993a453cd6b1e6c4d0cd0d96ce167883b87576d",
             "freeze/geometry-freeze.json": "7b0ae64dacc1d6e12d893a118e017220a349a4062be6474e9fbf82a58ab0452b",
             "freeze/seed-set-freeze.json": "4ee36a1aa39525a7faa0132877d5cede14df185ae5607dbe73615a3ad2357173",
             "seeds/seed-set.json": "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a",
             "seeds/entity-maps.npz": "621d8902948656221d876f3642c78963b075a0ce5a5ae1227da3e2f65620f605",
             "source/nb1c-gaze-list.json": "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062",
             "observations/acquisition-run.json": "1bbf03bc15dd5401c7f49d21b4e08492024391a43d0c73bf96d099c84db15dbf"}
NS1A_CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
HEAD_SOURCE = (PREVIEWS / "active-bootstrap/ab1a-first-natural-stereo-look/acquisition/calibration.json",
               "9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913")
AB1D2_ACQ = (PREVIEWS / "active-bootstrap/ab1d2-4096spp-observation-quality/observations/gaze-1/acquisition/"
                        "acquisition.json", "7c023b1f382514716893ca1a4d3009a6ae1102e327b3de00312206e3d9f37eff")
C02_RESIDUE = (PREVIEWS / "controller-02-classroom-replay/final-residue.json")
SOURCE_PINS_DIGEST = "8cdf70dfd91d9d1483c93b69fc8799f6081786506ca9d8f27366ed2f302c0cc0"
C01_FIXTURE_DIGEST = "5527778a793fb6c648c416bf2c2b896a675b0abe60a91fe82f5d81413716d6a5"
GAZES = {1: (76.75, 7.75), 2: (-2.75, 75.75), 3: (75.25, -25.75), 4: (38.25, -61.75), 5: (179.75, 34.75),
         6: (-156.25, 28.75)}
EXPECTED_TARGET, EXPECTED_RANK = 172, 6
POLICY = {"component_step_deg": 5.0, "yaw_min_deg": -25.0, "yaw_max_deg": 25.0, "pitch_min_deg": -20.0,
          "pitch_max_deg": 20.0, "edge_band_fraction": 0.04, "edge_object_fraction_min": 0.15, "voxel_m": 0.025,
          "neighbour_radius_m": 0.065, "minimum_neighbours": 6, "tangent_asymmetry_min": 0.18, "lookahead_m": 0.12,
          "current_view_margin_deg": 1.0, "minimum_candidate_frontier_support": 8, "alignment_cos_min": 0.5,
          "map_extent_quantile": 0.01}
FUSION = {"association_radius_m": 0.012, "hash_cell_m": 0.012}
CYC_GRID, CYC_SHAPE, OBJECT_ID, MIN_POINTS = 0.10, [401, 501], 141, 100
RADIUS, CELL, PATCH_ID = 0.012, 0.012, "ns1b_action_01"
SPP, SEEDS, IPD, VERGENCE = 4096, {"L": 2111, "R": 2112}, 0.063, 2.10
EYES = np.array([[-0.0315, 0.0, 0.0], [0.0315, 0.0, 0.0]])
SUBSTITUTIONS = [["P1", "tools/fsg6f_frontier.py", "_project_rectified_core"],
                 ["P2", "tools/classroom_oracle1_epistemic.py", "_rectified_core_directions_h"],
                 ["P3", "fov3d/experiments/classroom_oracle/controller02.py", "predicted_calibration"]]
ALWAYS = ["source", "synthetic", "select", "chart", "covariance", "context", "probe"]
CASE_B = ["preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
          "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "fuse", "post-probe"]
TOL, ROUND = 1e-9, 1e-12
NS1B_FILES = ["tools/north_star/" + n for n in ("ns1b_spec.py", "ns1b_chart.py", "ns1b_core.py", "ns1b_render.py",
                                                "ns1b_run.py", "ns1b_synthetic.py", "ns1b_fixtures.py",
                                                "ns1b_visuals.py", "check_ns1b.py", "check_ns1b_corruptions.py")]
DECLARED = set(NS1B_FILES) | {CONTRACT_PATH, REPORT_PATH, "tools/repository/check_repository_layout.py"}
PRODUCTION = ["ns1b_spec.py", "ns1b_chart.py", "ns1b_core.py", "ns1b_render.py", "ns1b_run.py", "ns1b_visuals.py"]
FORBIDDEN_IDENTIFIERS = {"run_control_loop", "run_controller02", "schedule", "schedule_normal", "Stop", "SceneClosed",
                         "catalog_summaries", "StereoSGBM_create", "StereoSGBM", "StereoBM_create", "compute_natural",
                         "run_match_gaze", "head_motion", "move_head"}
FORBIDDEN_MODULES = {"ab1d_match", "ab1d3_sgbm", "ab1a_stereo", "ab1c_planar", "fsg_stereo_sgbm"}
FORBIDDEN_READ = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                  "evaluation.json", "/evaluation/", "evaluation_only", "breadth-1-classroom", "natural-bootstrap-1a",
                  "natural-bootstrap-1b", "controller-01a-terminal", "controller-01b-single", "controller-01c-frontier")
LABELS = {"overview.png": ["NS1a FROZEN INPUT", "no object name used for selection",
                           "PHYSICAL HEAD FIXED - POLICY CHART ONLY", "POLICY CHART C", "CANONICAL H0",
                           "ORACLE CORRESPONDENCE", "DERIVED SPHERICAL GEOMETRY", "ORACLE SEGMENTATION AID"],
          "chart-covariance.png": ["POLICY CHART C", "CANONICAL H0", "PHYSICAL HEAD FIXED - POLICY CHART ONLY"],
          "first-controller-action-3d.png": ["CANONICAL H0", "PHYSICAL HEAD FIXED - POLICY CHART ONLY",
                                             "DERIVED SPHERICAL GEOMETRY"]}
BADGES = {"overview.png": ["ORACLE INPUT", "DERIVED"], "chart-covariance.png": ["ORACLE INPUT", "DERIVED"],
          "first-controller-action-3d.png": ["ORACLE INPUT", "DERIVED"]}


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


class X:
    """The run under check (possibly a corruption mirror), with caches.  ``ns1a`` and ``patches`` let the corruption
    suite point at mirrored NS1a data or substitute in-process mutations."""

    def __init__(self, run: Path, vis: Path, ns1a: Path = NS1A) -> None:
        self.run, self.vis, self.ns1a = Path(run), Path(vis), Path(ns1a)
        self._j, self._n, self.memo = {}, {}, {}
        rec = self.j("source/source-opened-files.json")
        w = [d for d in rec["allow_write_dirs"] if d.endswith("/source")]
        self.orig = w[0][: -len("/source")] if w else str(self.run.resolve())
        self.roots = sorted({str(self.run), str(self.run.resolve()), self.orig}, key=len, reverse=True)

    def j(self, rel: str):
        if rel not in self._j:
            self._j[rel] = json.loads((self.run / rel).read_text())
        return self._j[rel]

    def n(self, rel: str) -> dict:
        if rel not in self._n:
            with np.load(self.run / rel, allow_pickle=False) as z:
                self._n[rel] = {k: np.asarray(z[k]) for k in z.files}
        return self._n[rel]

    def a(self, rel: str):
        return json.loads((self.ns1a / rel).read_text())

    def an(self, rel: str) -> dict:
        with np.load(self.ns1a / rel, allow_pickle=False) as z:
            return {k: np.asarray(z[k]) for k in z.files}

    def rel(self, p: str) -> str:
        for r in self.roots:
            if p == r or p.startswith(r + "/"):
                return p[len(r) + 1:]
        return p

    def log(self) -> list[dict]:
        return [json.loads(ln) for ln in (self.run / "process-log.jsonl").read_text().splitlines() if ln.strip()]

    def case(self) -> str:
        return self.j("probe/decision.json")["case"]

    def has(self, rel: str) -> bool:
        return (self.run / rel).exists()


# ---------------------------------------------------------------- own independent implementations
def own_dir(yaw: float, pitch: float) -> np.ndarray:
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.cos(p) * math.sin(y), math.sin(p), -math.cos(p) * math.cos(y)])


def own_yp(d) -> tuple[float, float]:
    d = np.asarray(d, float) / np.linalg.norm(d)
    return math.degrees(math.atan2(d[0], -d[2])), math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))


def own_chart(g0: np.ndarray) -> np.ndarray:
    """Triple-product form: x = (g x b) x g / |.| (= b - (b.g)g), z = -g, y = z x x."""
    b = np.array([1.0, 0.0, 0.0])
    g = np.asarray(g0, float) / np.linalg.norm(g0)
    x = np.cross(np.cross(g, b), g)
    x = x / np.linalg.norm(x)
    z = -g
    return np.column_stack((x, np.cross(z, x), z))


def own_leverage(g: np.ndarray) -> float:
    return float(np.linalg.norm(np.cross([1.0, 0.0, 0.0], np.asarray(g, float) / np.linalg.norm(g))))


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


def fixed_head(c: dict) -> dict:
    h = head()
    centres = np.array([e["centre_h_m"] for e in c["eyes"]], float)
    out = {"eyes": float(np.abs(centres - EYES).max()), "ipd": abs(float(c["ipd_m"]) - IPD),
           "head_R": float(np.abs(np.asarray(c["head_R_wh"], float) - np.asarray(h["head_R_wh"], float)).max()),
           "head_o": float(np.abs(np.asarray(c["head_origin_w_m"], float) - np.asarray(h["head_origin_w_m"], float)).max()),
           "tangent": c.get("tangent_frame")}
    out["ok"] = (out["eyes"] <= ROUND and out["ipd"] <= ROUND and out["head_R"] <= ROUND and out["head_o"] <= ROUND
                 and out["tangent"] == "baseline_projected")
    return out


def own_association(m: np.ndarray, p: np.ndarray, radius: float = RADIUS) -> np.ndarray:
    """Own brute-force nearest surfel within the strict radius (independent of the accepted hash grid)."""
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
        k = np.argmin(d, axis=1)
        ok = d[np.arange(len(q)), k] < radius
        out[s:s + len(q)][ok] = sel[k[ok]]
    return out


def guard_files(x: X) -> list[str]:
    return sorted(str(p.relative_to(x.run)) for p in x.run.rglob("*opened-files.json"))


def opens(rec: dict) -> list[dict]:
    return [e for e in rec["events"] if e.get("event") == "open"]


def forbidden(p: str) -> bool:
    return any(t in p for t in FORBIDDEN_READ) or ("controller-01-full" in p and p.endswith(
        ("actions.json", "result.json", "manifest.json")))


def ok_stages(x: X) -> list[str]:
    return [e["command"] for e in x.log() if e["status"] == "ok" and e["command"] in ALWAYS + CASE_B]


def memo(x: X, key: str, fn):
    if key not in x.memo:
        x.memo[key] = fn()
    return x.memo[key]


# ---------------------------------------------------------------- the checks
def c01(x):
    origin = git("remote", "get-url", "origin")
    anc = {n: ancestor(s) for n, s in (("base", BASE), ("ns1a_acceptance", NS1A_ACCEPTANCE), ("contract", CONTRACT))}
    unchanged = subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode == 0
    added = git("log", "--diff-filter=A", "--format=%H", "--", CONTRACT_PATH).split()[-1:] == [CONTRACT]
    impl = {e["code"]["commit"] for e in x.log() if e["command"] in ALWAYS + CASE_B and e["status"] == "ok"}
    later = all(c != CONTRACT and ancestor(CONTRACT, c) for c in impl)
    import ns1b_spec as SPm
    spec = SPm.CONTRACT_COMMIT == CONTRACT and SPm.BASE_COMMIT == BASE and SPm.NS1A_ACCEPTANCE == NS1A_ACCEPTANCE
    src = x.j("source/source-manifest.json")
    ok = (CANONICAL_REMOTE in origin and all(anc.values()) and unchanged and added and later and spec
          and src["contract_commit"] == CONTRACT and src["contract_unchanged"] and CANONICAL_REMOTE in src["origin"]
          and src["base_commit"] == BASE and src["ns1a_acceptance"] == NS1A_ACCEPTANCE)
    return ok, {"origin": origin, "ancestors": anc, "contract_unchanged": unchanged, "contract_added_at": added,
                "canonical_commits": sorted(impl), "after_contract": later, "spec": spec}


def c02(x):
    import ns1b_spec as SPm
    digest = hashlib.sha256(json.dumps(SPm.SOURCE_PINS, sort_keys=True).encode()).hexdigest()
    now = {p: sha256(REPO / p) for p in SPm.SOURCE_PINS}
    bad = sorted(p for p in SPm.SOURCE_PINS if now[p] != SPm.SOURCE_PINS[p])
    rec = x.j("source/source-manifest.json")["source_pins"]
    names = all(f"def {fn}(" in (REPO / f).read_text() for _i, f, fn in SUBSTITUTIONS)
    subs = x.j("source/source-manifest.json")["adapter_substitutions"] == SUBSTITUTIONS
    return (digest == SOURCE_PINS_DIGEST and not bad and rec == SPm.SOURCE_PINS and names and subs and
            all(p in SPm.SOURCE_PINS for _i, p, _f in SUBSTITUTIONS)), {
        "pins_digest": digest, "changed": bad, "record_equal": rec == SPm.SOURCE_PINS, "substituted_names_exist": names,
        "substitutions_declared": subs}


def c03(x):
    now = {rel: sha256(x.ns1a / rel) for rel in NS1A_PINS}
    bad = sorted(r for r in NS1A_PINS if now[r] != NS1A_PINS[r])
    sfz = x.a("freeze/seed-set-freeze.json")
    carried = sfz["files"].get("seeds/seed-set.json") == NS1A_PINS["seeds/seed-set.json"] and \
        sfz["files"].get("seeds/entity-maps.npz") == NS1A_PINS["seeds/entity-maps.npz"]
    ofz = x.a("freeze/observation-freeze.json")
    ctx = x.j("context/context.json")
    look = {rel: sha256(x.ns1a / rel) == ofz["files"][rel] == h for rel, h in ctx["inputs"].items()}
    seal = x.a("observations/acquisition-run.json")["catalog_seal"]["sha256"] == NS1A_CATALOG_SEAL
    src = x.j("source/source-manifest.json")["ns1a_handoff"]
    return (not bad and carried and all(look.values()) and len(look) == 3 and seal
            and ctx["ns1a_maps_sha256"] == NS1A_PINS["seeds/entity-maps.npz"] and src == {k: v for k, v in
                                                                                          NS1A_PINS.items()}), {
        "changed": bad, "seed_freeze_carries": carried, "initialization_look": look, "catalog_seal": seal}


def c04(x):
    sel = x.j("selection/target-selection.json")
    doc = x.a("seeds/seed-set.json")
    rows = []
    for e in doc["entities"]:
        if e["initialized"] and int(e["contributing_patches"]) == 1:
            r = int(e["initialized_at_rank"])
            rows.append((-own_leverage(own_dir(*GAZES[r])), -int(e["final_surfels"]), int(e["temporary_entity_id"]), r))
    rows.sort()
    k, r = rows[0][2], rows[0][3]
    order = [t[2] for t in rows]
    rec_order = [c["temporary_entity_id"] for c in sel["candidates"]]
    lev_ok = all(abs(c["leverage"] - own_leverage(own_dir(*GAZES[c["initialized_at_rank"]]))) <= 1e-12
                 for c in sel["candidates"])
    guard = x.j("selection/selection-opened-files.json")
    reads = {x.rel(p) if not p.startswith(str(NS1A)) else p for p in guard["data_reads"]}
    want = {str((NS1A / f).resolve()) for f in ("seeds/seed-set.json", "freeze/seed-set-freeze.json",
                                                "source/nb1c-gaze-list.json")}
    names = any(("name" in kk.lower()) for kk in sel.get("fields_read", []))
    ok = (k == sel["selected"] == EXPECTED_TARGET and r == sel["selected_rank"] == EXPECTED_RANK and order == rec_order
          and lev_ok and not sel.get("DEV_OVERRIDE") and sel["matches_expectation"] and reads == want
          and not guard["violations"] and not names
          and sel["fields_read"] == ["temporary_entity_id", "initialized", "initialized_at_rank",
                                     "contributing_patches", "final_surfels"])
    return ok, {"derived": [k, r], "record": [sel["selected"], sel["selected_rank"]], "order_equal": order == rec_order,
                "leverage_equal": lev_ok, "reads": sorted(reads), "dev_override": bool(sel.get("DEV_OVERRIDE"))}


def c05(x):
    ch = x.j("chart/policy-chart.json")
    sel = x.j("selection/target-selection.json")
    g0 = own_dir(*sel["selected_gaze_deg"])
    r = np.asarray(ch["R_HC"], float)
    mine = own_chart(g0)
    perp = float(np.linalg.norm(np.cross(np.cross(g0, [1.0, 0, 0]), g0)))
    centre = own_yp(r.T @ g0)
    p = np.random.default_rng(3).normal(size=(30, 3))
    ok = (float(np.abs(mine - r).max()) <= 1e-15 and float(np.abs(r.T @ r - np.eye(3)).max()) <= ROUND
          and abs(float(np.linalg.det(r)) - 1.0) <= ROUND and max(abs(centre[0]), abs(centre[1])) <= 1e-9
          and float(np.abs((p @ r) @ r.T - p).max()) <= ROUND and perp >= 1e-6
          and float(np.abs(np.asarray(ch["g0_H0"]) - g0).max()) <= 1e-15 and ch["checks"]["ok"]
          and ch["local_domain_deg"] == {"yaw": [-25.0, 25.0], "pitch": [-20.0, 20.0], "step": 5.0}
          and int(ch["target"]) == int(sel["selected"]))
    return ok, {"max_diff_own_chart": float(np.abs(mine - r).max()), "perp": perp, "centre_local": centre,
                "det": float(np.linalg.det(r))}


def c06(x):
    import fsg6f_public as PUB
    from fov3d.control import frontier_config
    from fov3d.experiments.classroom_oracle import config as public
    import tools.classroom_oracle1_epistemic as EPL
    used = x.j("probe/pre-action-probe.json")["policy_configuration_used"]
    live = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "facade": dict(frontier_config.SURFACE_FRONTIER),
            "FUSION": dict(PUB.FUSION), "OBJECT_ID": int(PUB.OBJECT_ID), "grid": float(public.CYCLOPEAN_GRID_DEG),
            "c_fusion": dict(public.FUSION), "shape": list(EPL.make_evidence().shape)}
    rec = {"SURFACE_FRONTIER": used["SURFACE_FRONTIER"], "facade": used["SURFACE_FRONTIER_facade"],
           "FUSION": used["FSG6F_FUSION"], "OBJECT_ID": used["OBJECT_ID"], "grid": used["CYCLOPEAN_GRID_DEG"],
           "c_fusion": used["FUSION"], "shape": used["cyclopean_chart_shape"]}
    want = {"SURFACE_FRONTIER": POLICY, "facade": POLICY, "FUSION": FUSION, "OBJECT_ID": OBJECT_ID, "grid": CYC_GRID,
            "c_fusion": FUSION, "shape": CYC_SHAPE}
    dom = used["cyclopean_domain_deg"] == [-25.0, 25.0, -20.0, 20.0]
    src = x.j("source/source-manifest.json")["accepted_constants"]
    ok = live == want and rec == want and dom and src["SURFACE_FRONTIER"] == POLICY and src["FUSION"] == FUSION \
        and src["CYCLOPEAN_GRID_DEG"] == CYC_GRID and src["MIN_INITIAL_TARGET_POINTS"] == MIN_POINTS
    return ok, {"live_equal": live == want, "recorded_equal": rec == want, "domain": dom,
                "recorded_diff": {k: rec[k] for k in rec if rec[k] != want[k]}}


def adapter_records(x: X) -> list[dict]:
    recs = [("context", x.j("context/context.json")["adapter"]), ("probe", x.j("probe/pre-action-probe.json")["probe"]
                                                                   ["adapter"])]
    if x.case() == "B":
        p = x.j("post/post-action-probe.json")
        recs += [("post-evidence", p["evidence_adapter"]), ("post", p["probe"]["adapter"])]
    return recs


def c07(x):
    bad = []
    for name, a in adapter_records(x):
        subs = [[s["id"], s["file"], s["function"]] for s in a["substitutions"]]
        if subs != SUBSTITUTIONS or not a["restored"] or not a["module_copies_stable"]:
            bad.append(f"{name}: substitutions / restore")
        mods = {s["id"]: s["modules"] for s in a["substitutions"]}
        if not ({"fsg6f_frontier", "tools.fsg6f_frontier"} <= set(mods.get("P1", []))):
            bad.append(f"{name}: P1 did not cover both module copies")
        r = np.asarray(a["R_HC"], float)
        if float(np.abs(r - np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)).max()) > 0.0:
            bad.append(f"{name}: adapter chart is not the policy chart")
        for p3 in a["p3"]:
            w = own_world(p3["local_gaze_deg"], r)
            if max(abs(w[0] - p3["world_gaze_deg"][0]), abs(w[1] - p3["world_gaze_deg"][1])) > 1e-9 or \
                    p3["calibration_gaze_deg"] != p3["world_gaze_deg"] or p3["tangent_frame"] != "baseline_projected":
                bad.append(f"{name}: P3 calibration is not the real sensor at the world gaze")
            if max(abs(p3["calibration_gaze_deg"][0] - p3["local_gaze_deg"][0]),
                   abs(p3["calibration_gaze_deg"][1] - p3["local_gaze_deg"][1])) < 1e-6:
                bad.append(f"{name}: P3 used the LOCAL gaze (fake local calibration)")
    pr = x.j("probe/pre-action-probe.json")["probe"]["adapter"]
    if pr["calls"]["P1"] <= 0:
        bad.append("probe: no physical projection went through P1")
    if x.j("context/context.json")["adapter"]["calls"]["P2"] != 2:
        bad.append("context: the evidence was not marked through P2 (2 eyes)")
    # live: the adapter substitutes and restores exactly the declared functions
    import ns1b_chart as CHm
    before = CHm.original_functions()
    with CHm.PolicyChartAdapter(np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)):
        during = CHm.original_functions()
    after = CHm.original_functions()
    live = all(a is not d for s in before for (_n, a), (_m, d) in zip(before[s], during[s])) and \
        all(a is b for s in before for (_n, a), (_m, b) in zip(before[s], after[s]))
    return not bad and live, {"problems": bad, "live_substitute_restore": live}


def c08(x):
    rep = x.j("covariance/covariance-report.json")
    parts_ok = all(rep["parts"].values()) and not rep["failed"] and rep["marker"] == "NS1B_COVARIANCE_PASS"
    import ns1b_fixtures as FXm
    import ns1b_core as COREm
    an = memo(x, "analytic", FXm.analytic_suite)
    an_ok = all(v["pass"] for v in an.values())
    rows = memo(x, "rows", lambda: FXm.c01_rows(FXm.trajectory_files()))
    rec = rep["replay"]
    kres = {k: memo(x, k, lambda k=k: FXm.k_replay(k, rows)) for k in ("K2", "K3", "K3q")}
    k_ok = all(kres[k]["pass"] and not COREm.compare(COREm.jsonable(kres[k]), rec[k], TOL) for k in kres)
    k4 = K4_CACHE.get("k4") or K4_CACHE.setdefault("k4", FXm.k4_gate(rows))
    acc = next(r for r in json.loads(C02_RESIDUE.read_text())["residue_decisions"] if int(r["object"]) == 210)
    k4_ok = (k4["pass"] and k4["verdict"] == [acc["admissible"], acc["reason"]] == rec["K4"]["verdict"]
             and k4["counts"] == acc["detail"]["counts"] == rec["K4"]["counts"])
    dig = rep["fixture_files_digest"] == rep["fixture_files_digest_pinned"] == C01_FIXTURE_DIGEST
    pc = rep["projection_invariance_canonical_chart"]
    pc_ok = pc["pass"] and max(r_["uv_difference_px"] for r_ in pc["rows"]) <= TOL and \
        min(r_["negative_control_px"] for r_ in pc["rows"]) > 1.0
    order = ok_stages(x)
    before = "covariance" in order and "context" in order and order.index("covariance") < order.index("context")
    return parts_ok and an_ok and k_ok and k4_ok and dig and pc_ok and before, {
        "parts": rep["parts"], "analytic_recomputed": {k: v["pass"] for k, v in an.items()},
        "replay_recomputed_equal": k_ok, "K4": [k4["verdict"], k4["counts"]], "digest": dig,
        "projection": pc_ok, "covariance_before_context": before}


K4_CACHE: dict = {}


def c09(x):
    rep = x.j("synthetic/synthetic-report.json")
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    ok = (not rep["failed"] and rep["count"] == 23 and rep["marker"] == "NS1B_SYNTHETIC_PASS"
          and all(v["pass"] for v in rep["tests"].values()) and "synthetic" in order and "select" in order
          and order.index("synthetic") < order.index("select"))
    return ok, {"count": rep["count"], "failed": rep["failed"]}


def c10(x):
    rows = {}
    ctx = x.j("context/context.json")
    rank = int(ctx["initialization_rank"])
    c0 = x.a(f"observations/rank-{rank:02d}/acquisition/calibration.json")
    rows["initialization"] = {**fixed_head(c0), "gaze": c0["gaze_yaw_pitch_deg"] == list(GAZES[rank])}
    pre = x.j("probe/pre-action-probe.json")["probe"]
    r = np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)

    def predicted(probe, label):
        pc = probe["gate"]["detail"].get("predicted_calibration")
        if pc is None:
            return
        prop = probe["proposal"]
        w = own_world(prop["local_gaze_deg"], r)
        real, fake = own_calibration(*w), own_calibration(*prop["local_gaze_deg"])
        rows[label] = {**fixed_head(pc), "is_real_world_sensor": cal_close(pc, real), "is_fake_local": cal_close(pc, fake)}
    predicted(pre, "pre_gate_predicted")
    if x.case() == "B":
        act = x.j("probe/decision.json")["actions"][0]
        plan = json.loads((x.run / "probe/planned-calibration.json").read_text())
        real = own_calibration(*own_world(act["local_gaze_deg"], r))
        rows["planned"] = {**fixed_head(plan), "is_real_world_sensor": cal_close(plan, real),
                           "is_fake_local": cal_close(plan, own_calibration(*act["local_gaze_deg"]))}
        exe = x.j("observation/acquisition/calibration.json")
        rows["executed"] = {**fixed_head(exe), "is_real_world_sensor": cal_close(exe, real),
                            "is_fake_local": cal_close(exe, own_calibration(*act["local_gaze_deg"]))}
        predicted(x.j("post/post-action-probe.json")["probe"], "post_gate_predicted")
    ok = all(v["ok"] and v.get("gaze", True) and v.get("is_real_world_sensor", True) and not v.get("is_fake_local", False)
             for v in rows.values())
    return ok, rows


def own_context(x: X):
    import ns1b_core as COREm
    sel = x.j("selection/target-selection.json")
    k, rank = int(sel["selected"]), int(sel["selected_rank"])
    cal = x.a(f"observations/rank-{rank:02d}/acquisition/calibration.json")
    rgb = x.an(f"observations/rank-{rank:02d}/acquisition/rgb-observation.npz")
    ref = x.an(f"observations/rank-{rank:02d}/oracle_aid/reference-observation.npz")
    rec, _meta, st = COREm.matcher_state(cal, rgb, ref)
    r = np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)
    ctx, _ad = COREm.build_context(k, cal, st, rec["valid"], r, (0.0, 0.0))
    return ctx, rec, st, COREm.load_surface_map(x.an("seeds/entity-maps.npz"), k)


def c11(x):
    import ns1b_core as COREm
    ctx, rec, st, sm = memo(x, "context", lambda: own_context(x))
    saved_st, saved_ev, saved_m = x.n("context/controller-state.npz"), x.n("context/evidence.npz"), \
        x.n("context/target-map-H0.npz")
    st_eq = all(np.array_equal(st[k], saved_st[k]) for k in ("ids_left", "ids_right", "raw_support_L",
                                                             "raw_support_R")) and \
        np.array_equal(np.asarray(rec["valid"], bool), saved_st["matcher_valid"])
    ev = COREm.evidence_arrays(ctx)
    ev_eq = set(ev) == set(saved_ev) and all(np.array_equal(ev[k], saved_ev[k]) for k in ev)
    m = COREm.map_arrays(sm)
    m_eq = set(m) == set(saved_m) and all(np.array_equal(m[k], saved_m[k]) for k in m)
    cj = x.j("context/context.json")
    k = int(x.j("selection/target-selection.json")["selected"])
    guard = x.j("context/context-opened-files.json")
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    no_render_before = "acquire" not in order or order.index("acquire") > order.index("probe")
    ok = (st_eq and ev_eq and m_eq and cj["own_looks"] == 1 and cj["visited"] == [[0.0, 0.0]]
          and cj["current_gaze_deg"] == [0.0, 0.0] and max(map(abs, cj["seed_local_yaw_pitch_deg"])) <= 1e-9
          and cj["map"]["all_ids_target"] and int(cj["target"]) == k
          and cj["map"]["patch_ids"] == [f"nb1c_gaze_{int(x.j('selection/target-selection.json')['selected_rank']):02d}"]
          and not guard["violations"] and no_render_before and cj["fixed_head"]["ok"]
          and cj["map"]["surfels"] == len(m["xyz_h"]))
    return ok, {"state_equal": st_eq, "evidence_equal": ev_eq, "map_equal": m_eq, "own_looks": cj["own_looks"],
                "surfels": cj["map"]["surfels"], "no_render_before_probe": no_render_before}


def own_probe(x: X):
    import ns1b_chart as CHm
    import ns1b_core as COREm
    import ns1b_run as RUNm
    ctx, _cj, cal, _st, _v, m = RUNm.load_context(x.run)
    ch = x.j("chart/policy-chart.json")
    r = np.asarray(ch["R_HC"], float)
    h = head()
    return COREm.probe(ctx, CHm.to_chart(np.asarray(m["xyz_h"], float), r), r, CHm.north_star_sensor,
                       np.asarray(h["head_R_wh"]), np.asarray(h["head_origin_w_m"]), "full",
                       np.asarray(ch["g0_H0"], float), "pre-action probe")


def c12(x):
    import ns1b_core as COREm
    mine = memo(x, "probe", lambda: own_probe(x))
    saved = x.j("probe/pre-action-probe.json")["probe"]
    diffs = COREm.probe_comparison(saved, COREm.jsonable(mine), 0.0)
    extra = ("planned_calibration_test", "gate_predicted_equals_planned")
    prop_eq = COREm.compare(saved["proposal"], COREm.jsonable(mine["proposal"]), 0.0, skip=extra) if saved["proposal"] \
        else ([] if mine["proposal"] is None else ["proposal"])
    if saved["proposal"] is not None and not (saved["proposal"]["planned_calibration_test"]["ok"]
                                              and saved["proposal"]["gate_predicted_equals_planned"]):
        prop_eq.append("planned calibration test")
    n = [e["command"] for e in x.log() if e["command"] == "probe" and e["status"] == "ok"]
    guard = x.j("probe/probe-opened-files.json")
    reads = sorted(x.rel(p) if not p.startswith(str(NS1A)) else p for p in guard["data_reads"])
    no_truth = not any(p.endswith(("reference-observation.npz", ".exr")) for p in guard["data_reads"])
    no_forbidden = not any(forbidden(e["path"]) for e in opens(guard))
    ok = not diffs and not prop_eq and len(n) == 1 and not guard["violations"] and no_truth and no_forbidden
    return ok, {"differences": diffs[:5], "proposal_differences": prop_eq[:3], "probe_runs": len(n),
                "reads": reads, "no_position_or_object_index": no_truth, "no_forbidden_read": no_forbidden}


def c13(x):
    import ns1b_chart as CHm
    import ns1b_core as COREm
    import ns1b_run as RUNm
    pre = x.j("probe/pre-action-probe.json")
    recs = pre["baseline_rotation_invariance"]
    rec_ok = len(recs) == 2 and all(r_["pass"] and not r_["differences"] and r_["evidence_equal"] for r_ in recs)
    ctx, cj, cal, st, valid, m = RUNm.load_context(x.run)
    ch = x.j("chart/policy-chart.json")
    r, g0 = np.asarray(ch["R_HC"], float), np.asarray(ch["g0_H0"], float)
    h = head()
    q = CHm.rot_x(-23.0)                      # an angle of the checker's own, not one of the probe's
    w = COREm.rotate_world(q, cal, np.asarray(m["xyz_h"], float), g0)
    rq = own_chart(w["g0"])
    cq, _ = COREm.build_context(int(cj["target"]), w["calibration"], st, valid, rq, (0.0, 0.0))
    oq = COREm.probe(cq, CHm.to_chart(w["map_h0"], rq), rq, CHm.north_star_sensor, np.asarray(h["head_R_wh"]),
                     np.asarray(h["head_origin_w_m"]), "full", w["g0"], "checker invariance")
    diffs, flip = COREm.explain_voxel_flip(COREm.probe_comparison(pre["probe"], COREm.jsonable(oq)),
                                           CHm.to_chart(np.asarray(m["xyz_h"], float), r))
    world = 0.0
    if pre["probe"]["proposal"] is not None:
        world = float(np.abs(np.asarray(oq["proposal"]["d_H0"]) - q @ np.asarray(pre["probe"]["proposal"]["d_H0"])).max())
    eu = pre["euclidean_invariance"]
    ok = rec_ok and not diffs and world <= ROUND and eu["equal"] and float(np.abs(rq - q @ r).max()) <= ROUND
    return ok, {"recorded": [[r_["beta_deg"], r_["pass"]] for r_ in recs], "checker_beta_-23_differences": diffs[:3],
                "voxel_flip": flip, "world_error": world, "euclidean": eu}


def c14(x):
    pre = x.j("probe/pre-action-probe.json")["probe"]
    dec = x.j("probe/decision.json")
    g = pre["gate"]
    prop = pre["proposal"]
    cnt = g["detail"].get("counts") or {}
    if prop is None:
        consistent = g["reason"] == "no_local_proposal" and not g["admissible"]
    elif prop["source"] != "fsg6f":
        consistent = g["reason"] == "untraceable_final_support" and not g["admissible"]
    elif g["admissible"]:
        consistent = g["reason"] == "novel_support_in_predicted_cores" and cnt.get("novel_service_count", 0) > 0
    else:
        consistent = (g["reason"] in ("visited_final_gaze", "support_identity_mismatch")
                      or (g["reason"] == "no_novel_serviceable_support" and cnt.get("novel_service_count", 1) == 0))
    pc = g["detail"].get("predicted_calibration")
    p3 = pre["adapter"]["p3"]
    calib_ok = True
    if pc is not None:
        w = own_world(prop["local_gaze_deg"], np.asarray(x.j("chart/policy-chart.json")["R_HC"], float))
        calib_ok = cal_close(pc, own_calibration(*w)) and len(p3) == 1
    ok = consistent and calib_ok and dec["gate"] == {"admissible": g["admissible"], "reason": g["reason"]}
    return ok, {"admissible": g["admissible"], "reason": g["reason"], "counts": cnt, "predicted_is_real": calib_ok}


def c15(x):
    pre = x.j("probe/pre-action-probe.json")["probe"]
    prop = pre["proposal"]
    if prop is None:
        return x.j("probe/decision.json")["actions"] == [], {"proposal": None}
    r = np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)
    w = own_world(prop["local_gaze_deg"], r)
    d = r @ own_dir(*prop["local_gaze_deg"])
    back = own_yp(r.T @ own_dir(*w))
    g0 = np.asarray(x.j("chart/policy-chart.json")["g0_H0"], float)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(d @ g0)))))
    ok = (max(abs(w[0] - prop["world_gaze_deg"][0]), abs(w[1] - prop["world_gaze_deg"][1])) <= 1e-9
          and max(abs(back[0] - prop["local_gaze_deg"][0]), abs(back[1] - prop["local_gaze_deg"][1])) <= 1e-9
          and abs(own_leverage(d) - prop["leverage"]) <= 1e-12 and abs(ang - prop["angle_from_seed_deg"]) <= 1e-9
          and float(np.abs(d - np.asarray(prop["d_H0"])).max()) <= ROUND)
    if x.case() == "B":
        act = x.j("probe/decision.json")["actions"][0]
        exe = x.j("observation/acquisition/calibration.json")
        ar = x.j("observation/acquisition-run.json")
        ok &= (act["world_gaze_deg"] == prop["world_gaze_deg"] and act["local_gaze_deg"] == prop["local_gaze_deg"]
               and exe["gaze_yaw_pitch_deg"] == prop["world_gaze_deg"] and ar["gaze_H0_deg"] == prop["world_gaze_deg"])
    return ok, {"local": prop["local_gaze_deg"], "world_own": list(w), "world_record": prop["world_gaze_deg"],
                "roundtrip": list(back), "angle_from_seed": ang}


def c16(x):
    pre = x.j("probe/pre-action-probe.json")
    dec = x.j("probe/decision.json")
    p = pre["probe"]
    want = "A" if p["proposal"] is None else ("B" if p["gate"]["admissible"] else "3")
    stages = ok_stages(x)
    b_ran = [s for s in CASE_B if s in stages]
    if want == "B":
        process = b_ran == CASE_B and len(dec["actions"]) == 1
    else:
        process = not b_ran and dec["actions"] == []
    ok = dec["case"] == pre["case"] == want and not pre["outcome_4"] and process and \
        dec["probe_sha256"] == sha256(x.run / "probe/pre-action-probe.json")
    return ok, {"case": dec["case"], "expected": want, "case_b_stages_run": b_ran, "actions": len(dec["actions"])}


def c17(x):
    if x.case() != "B":
        return not x.has("observation") and not x.has("preflight"), {"not_applicable": "no action; no observation"}
    ar = x.j("observation/acquisition-run.json")
    rec = x.j("observation/acquisition/acquisition.json")
    acc = json.loads(Path(AB1D2_ACQ[0]).read_text())["settings"] if sha256(AB1D2_ACQ[0]) == AB1D2_ACQ[1] else None
    fz = x.j("freeze/observation-freeze.json")
    files_ok = all(sha256(x.run / f) == h for f, h in fz["files"].items())
    plan_b = (x.run / "probe/planned-calibration.json").read_bytes()
    seal_file = sha256(x.run / "observation/evaluation_only/instance-catalog.json")
    n_acq = sum(1 for e in x.log() if e["command"] == "acquire" and e["status"] == "ok")
    pre = x.j("preflight/preflight.json")
    ok = (ar["spp"] == rec["spp"] == rec["settings"]["samples"] == SPP and rec["render_seeds_lr"] == SEEDS
          and rec["device"] == "OPTIX" and acc is not None and rec["settings"] == acc
          and ar["exr_samples_lr"] == {"L": str(SPP), "R": str(SPP)} and files_ok
          and (x.run / "observation/acquisition/calibration.json").read_bytes() == plan_b
          and ar["catalog_seal"]["sha256"] == seal_file == NS1A_CATALOG_SEAL and n_acq == 1
          and pre["rendered"] is False and pre["calibration_identity"]["byte_identical_to_planned"]
          and fixed_head(x.j("observation/acquisition/calibration.json"))["ok"]
          and rec["settings"]["denoising"] is False and rec["settings"]["adaptive_sampling"] is False
          and rec["settings"]["pixel_filter"] == "BOX" and rec["settings"]["filter_width"] == 1.0)
    return ok, {"spp": ar["spp"], "exr": ar["exr_samples_lr"], "settings_equal_ab1d2": acc is not None and
                rec["settings"] == acc, "freeze_files_ok": files_ok, "seal": seal_file == NS1A_CATALOG_SEAL,
                "acquisitions": n_acq}


def c18(x):
    if x.case() != "B":
        return not x.has("correspondence"), {"not_applicable": True}
    import check_ns1a as A
    c = x.j("observation/acquisition/calibration.json")
    ref = x.n("observation/oracle_aid/reference-observation.npz")
    prod = x.n("correspondence/oracle-correspondences.npz")
    o = A.own_oracle(c, ref)
    idx = prod["left_core_row"].astype(np.int64) * 256 + prod["left_core_col"]
    same = np.array_equal(np.sort(idx), o["keep"]) and np.array_equal(idx, np.sort(idx))
    du = float(np.abs(prod["uv_R"] - o["uv_R"]).max()) if same and len(idx) else math.inf
    keys = sorted(prod) == ["left_core_col", "left_core_row", "uv_L", "uv_R"]
    cont = bool(len(prod["uv_R"]) and not np.array_equal(prod["uv_R"], np.rint(prod["uv_R"])))
    cls = x.n("correspondence/core-class-map.npz")["core_class"]
    rec = x.j("correspondence/correspondence-opened-files.json")
    reads = {x.rel(p) for p in rec["data_reads"]}
    ok = (same and du <= 1e-9 and keys and cont and np.array_equal(cls, o["class"]) and not rec["violations"]
          and reads == {"observation/acquisition/calibration.json", "observation/oracle_aid/reference-observation.npz",
                        "freeze/observation-freeze.json"} and not rec["modules_loaded"]["cv2"])
    return ok, {"correspondences": int(len(idx)), "same_pixels": same, "uv_R_max_diff_px": du, "schema": keys,
                "continuous_uv_R": cont}


def c19(x):
    if x.case() != "B":
        return not x.has("geometry"), {"not_applicable": True}
    import check_ns1a as A
    c = x.j("observation/acquisition/calibration.json")
    prod = x.n("correspondence/oracle-correspondences.npz")
    res = x.n("geometry/epipolar-result.npz")
    g = A.own_geometry(c, prod)
    v = np.asarray(res["valid_epi"], bool)
    dp = float(np.abs(g["P"][v] - res["P_epi"][v]).max()) if v.any() else 0.0
    rec = x.j("geometry/geometry-opened-files.json")
    reads = {x.rel(p) for p in rec["data_reads"]}
    mods = rec["modules_loaded"]
    fz = x.j("freeze/geometry-freeze.json")
    cfz = x.j("freeze/correspondence-freeze.json")
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    ok = (dp <= 1e-9 and reads == {"observation/acquisition/calibration.json",
                                   "correspondence/oracle-correspondences.npz"}
          and not any(mods[m] for m in ("cv2", "fsg_stereo", "ab1b_oracle", "ab1d3_sgbm", "ab1d_match", "fsg6f_frontier"))
          and rec["position_reads"] == rec["object_index_reads"] == rec["catalog_reads"] == 0 and not rec["violations"]
          and all(sha256(x.run / f) == h for f, h in fz["files"].items())
          and all(sha256(x.run / f) == h for f, h in cfz["files"].items())
          and order.index("freeze-geometry") < order.index("local-oracle-segmentation"))
    return ok, {"P_epi_max_diff_m": dp, "reads": sorted(reads), "valid": int(v.sum())}


def c20(x):
    if x.case() != "B":
        return not x.has("segmentation"), {"not_applicable": True}
    prod = x.n("correspondence/oracle-correspondences.npz")
    res = x.n("geometry/epipolar-result.npz")
    ref = x.n("observation/oracle_aid/reference-observation.npz")
    idn = x.n("segmentation/local-identity.npz")
    uv = prod["uv_L"].astype(np.int64)
    mine = np.where(np.asarray(res["valid_epi"], bool), ref["instance_L"][uv[:, 1], uv[:, 0]], -1)
    rec = x.j("segmentation/segmentation-opened-files.json")
    marks = [e["label"] for e in rec["events"] if e.get("event") == "mark"]
    ok = (np.array_equal(mine, idn["temporary_entity_id"]) and rec["reference_members_read"] == ["instance_L"]
          and marks == ["geometry_freeze_verified", "identity_access_begins"] and not rec["violations"])
    return ok, {"ids_equal": bool(np.array_equal(mine, idn["temporary_entity_id"])), "marks": marks}


def c21(x):
    if x.case() != "B":
        return not x.has("fusion"), {"not_applicable": True}
    import ns1b_core as COREm
    from fov3d.reconstruction import surface_map as SMm
    fu = x.j("fusion/fusion.json")
    k = int(x.j("selection/target-selection.json")["selected"])
    res = x.n("geometry/epipolar-result.npz")
    ids = x.n("segmentation/local-identity.npz")["temporary_entity_id"]
    keep = np.asarray(res["valid_epi"], bool) & (ids == k)
    patch = x.n("fusion/target-patch.npz")
    patch_ok = np.array_equal(patch["xyz_h"], np.asarray(res["P_epi"], np.float64)[keep]) and \
        np.all(patch["instance_id"] == k)
    m0 = x.n("context/target-map-H0.npz")
    sm = SMm.SurfaceMap(np.asarray(m0["xyz_h"], float).copy(), np.asarray(m0["rgb"], float).copy(),
                        m0["instance_id"].copy(), m0["support_count"].copy(), m0["provenance_mask"].copy(),
                        [str(p) for p in m0["patch_ids"]])
    p = {"frame": "H0", "patch_id": PATCH_ID, "xyz_h": patch["xyz_h"], "rgb": patch["rgb"],
         "instance_id": patch["instance_id"], "points": int(len(patch["xyz_h"]))}
    fused, rec = COREm.fuse_h0(sm, p, k, RADIUS, CELL)
    saved = x.n("fusion/fused-target-map.npz")
    same = COREm.maps_equal(COREm.map_arrays(fused), saved)
    own = own_association(m0["xyz_h"], patch["xyz_h"]) if len(patch["xyz_h"]) >= MIN_POINTS else np.zeros(0)
    own_matched = int((own >= 0).sum())
    counts = (fu["action"] == "FUSED" and own_matched == fu["matched"] and len(own) - own_matched == fu["new"]
              and len(np.unique(own[own >= 0])) == fu["affected_surfels"]) or \
        (fu["action"] == "RETAINED_NOT_FUSED" and fu["measured_points"] < MIN_POINTS)
    # the record's frame tag: a FUSED record carries the tag written by the H0-only fusion entry point ("H0", the only
    # frame it accepts); a not-fused record carries the stage's canonical-H0 label
    frame_ok = fu["frame"] == ("H0" if fu["action"] == "FUSED" else "CANONICAL H0")
    ok = (patch_ok and same and counts and frame_ok and fu.get("radius_m", RADIUS) == RADIUS
          and fu.get("hash_cell_m", CELL) == CELL and fu["patch_id"] == PATCH_ID
          and (fu["action"] != "FUSED" or (fu["replay"]["exact"] and fu["replay"]["duplicate_patch"]))
          and np.all(saved["instance_id"] == k) and fu["measured_points"] == int(keep.sum())
          and rec["action"] == fu["action"] and rec.get("matched") == fu["matched"])
    return ok, {"patch_is_frozen_P_epi": bool(patch_ok), "accepted_fuse_reproduced": same, "own_matched": own_matched,
                "own_counts_equal": bool(counts), "frame_tag": fu["frame"], "frame_ok": frame_ok,
                "record": {k_: fu[k_] for k_ in ("action", "matched", "new", "affected_surfels", "map_before",
                                                 "map_after")}}


def c22(x):
    if x.case() != "B":
        return not x.has("post"), {"not_applicable": True}
    import ns1b_chart as CHm
    import ns1b_core as COREm
    import ns1b_run as RUNm
    post = x.j("post/post-action-probe.json")
    ctx, _cj, _cal0, _st, _v, _m = RUNm.load_context(x.run)
    act = x.j("probe/decision.json")["actions"][0]
    cal1 = x.j("observation/acquisition/calibration.json")
    rec1, _meta, st1 = COREm.matcher_state(cal1, x.n("observation/acquisition/rgb-observation.npz"),
                                           x.n("observation/oracle_aid/reference-observation.npz"))
    r = np.asarray(x.j("chart/policy-chart.json")["R_HC"], float)
    COREm.add_look(ctx, cal1, st1, rec1["valid"], r, tuple(act["local_gaze_deg"]))
    h = head()
    mine = COREm.probe(ctx, CHm.to_chart(np.asarray(x.n("fusion/fused-target-map.npz")["xyz_h"], float), r), r,
                       CHm.north_star_sensor, np.asarray(h["head_R_wh"]), np.asarray(h["head_origin_w_m"]), "full",
                       np.asarray(x.j("chart/policy-chart.json")["g0_H0"], float), "post-action probe")
    diffs = COREm.probe_comparison(post["probe"], COREm.jsonable(mine), 0.0)
    n_post = sum(1 for e in x.log() if e["command"] == "post-probe" and e["status"] == "ok")
    n_acq = sum(1 for e in x.log() if e["command"] == "acquire" and e["status"] == "ok")
    ok = (not diffs and post["executed"] is False and n_post == 1 and n_acq == 1 and post["own_looks"] == 2
          and post["visited"] == [[0.0, 0.0], act["local_gaze_deg"]])
    return ok, {"differences": diffs[:3], "state": post["probe"]["state"], "post_probes": n_post, "acquisitions": n_acq}


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
    return {"hits": hits}


def c23(x):
    log = x.log()
    canon = [e for e in log if e["command"] in ALWAYS + CASE_B]
    ok_cmds = [e["command"] for e in canon if e["status"] == "ok"]
    want = ALWAYS + (CASE_B if x.case() == "B" else [])
    once = ok_cmds == want
    commits = {e["code"]["commit"] for e in canon if e["status"] == "ok"}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] and not e["dev"] for e in canon if e["status"] == "ok")
    failed = [e["command"] for e in canon if e["status"] == "failed"]
    scan = code_scan()
    acq = [e for e in log if e["command"] == "acquire" and e["status"] == "ok"]
    ok = once and len(commits) == 1 and clean and not failed and not scan["hits"] and len(acq) <= 1
    return ok, {"order": ok_cmds, "commits": sorted(commits), "clean_pushed": clean, "failed": failed,
                "code_scan": scan["hits"]}


def c24(x):
    bad, truth = [], {}
    for f in guard_files(x):
        rec = x.j(f)
        if rec["violations"]:
            bad.append(f"{f}: violations")
        for e in opens(rec):
            if forbidden(e["path"]):
                bad.append(f"{f}: forbidden read {e['path']}")
            if e.get("kind") == "data-read" and e["path"].endswith(("reference-observation.npz", ".exr",
                                                                    "oracle_observation.npz")):
                truth.setdefault(f, set()).add(Path(e["path"]).name)
    allowed = {"context/context-opened-files.json", "correspondence/correspondence-opened-files.json",
               "freeze/observation-freeze-opened-files.json",
               "segmentation/segmentation-opened-files.json", "post/post-opened-files.json",
               "covariance/covariance-opened-files.json"}
    extra = sorted(set(truth) - allowed)
    seg = x.j("segmentation/segmentation-opened-files.json")["reference_members_read"] if x.case() == "B" else \
        ["instance_L"]
    return not bad and not extra and seg == ["instance_L"], {"problems": bad[:5], "truth_reads_outside_allowed": extra,
                                                             "truth_reading_stages": sorted(truth)}


def c25(x):
    import ns1b_visuals as V
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    want = ["overview.png", "chart-covariance.png"] + (["first-controller-action-3d.png"] if x.case() == "B" else [])
    with tempfile.TemporaryDirectory() as td:
        figs, _dd = V.render_all(x.run)
        regen = {}
        for name, (im, _meta) in figs.items():
            p = Path(td) / name
            im.save(p, format="PNG", optimize=False)
            regen[name] = sha256(p)
    on_disk = {n: sha256(x.vis / n) for n in want if (x.vis / n).exists()}
    same = sorted(regen) == sorted(want) and all(regen[n] == on_disk.get(n) == man["figures"][n]["sha256"]
                                                 for n in want)
    lab = all(man["figures"][n]["labels"] == LABELS[n] and man["figures"][n]["badges"] == BADGES[n] for n in want)
    stmt = man.get("fixed_head_statement") == "PHYSICAL HEAD FIXED - POLICY CHART ONLY" and \
        man.get("frames") == {"chart": "POLICY CHART C", "h0": "CANONICAL H0"}
    return same and lab and stmt and sorted(man["figures"]) == sorted(want), {
        "regenerated_equal": same, "labels_badges": lab, "frame_statement": stmt}


def c26(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
        "manifest.json", "check-summary.json", "process-log.jsonl"}
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    return not bad and set(man["files"]) == present and not extra, {"mismatch": bad[:5],
                                                                    "unlisted": sorted(present - set(man["files"]))[:5],
                                                                    "undeclared_changes": extra}


CHECKS = [
    ("01", "provenance: canonical repo, base, NS1a acceptance, contract first and unchanged", c01),
    ("02", "accepted sources pinned and unchanged; the substituted functions declared", c02),
    ("03", "the frozen NS1a handoff: freezes, seed set, maps, gaze list, initialization look, catalog seal", c03),
    ("04", "target selection recomputed independently (rule, leverage |b x g|, ties); derived, not hard-coded", c04),
    ("05", "policy chart recomputed independently; orthonormal, det +1, seed -> (0, 0), round trips, domain", c05),
    ("06", "accepted policy constants unchanged, live and as recorded by the probe", c06),
    ("07", "frame adapter: exactly P1-P3, every copy, restored; P3 = real sensor at the world gaze", c07),
    ("08", "coordinate covariance re-verified (K1 analytic, K2/K3/K3q replay, K4 Controller-02 verdict)", c08),
    ("09", "synthetic known answers passed before the selection", c09),
    ("10", "fixed head: every physical calibration; no fake local-baseline calibration", c10),
    ("11", "initial context recomputed from the frozen NS1a look and map (no rerender)", c11),
    ("12", "the ONE pre-action probe recomputed bitwise; truth-free (no Position read)", c12),
    ("13", "baseline-rotation invariance (recorded and the checker's own angle); Euclidean invariance", c13),
    ("14", "the adapted Controller-02 gate verdict, counts and real predicted calibration", c14),
    ("15", "world-gaze mapping recomputed; round trip, leverage, distance; equals planned and executed", c15),
    ("16", "decision case and process: Case-B stages ran iff Case B; zero or one action", c16),
    ("17", "observation: one pair, 4096 spp (record, readback, EXR), seeds, settings, planned calibration, seal", c17),
    ("18", "PERFECT correspondence reproduced by an own oracle; truth-stripped schema; continuous uv_R", c18),
    ("19", "spherical geometry reproduced by own triangulation; truth-free guard; frozen before identity", c19),
    ("20", "local oracle identity at the exact pixels; only instance_L read; after the geometry freeze", c20),
    ("21", "H0 fusion: frozen P_epi target patch, 12 mm / 12 mm, accepted fuse and own association, idempotent", c21),
    ("22", "the ONE post-action probe recomputed; not executed; no second action", c22),
    ("23", "process: each canonical stage once, in order, one clean pushed commit; no scheduler / SGBM / head motion",
     c23),
    ("24", "truth boundary: no catalog / name / seeds / evaluation read; truth only in the declared stages", c24),
    ("25", "figures regenerate byte-identically; frame labels, fixed-head statement, badges", c25),
    ("26", "run manifest and declared changes", c26),
]


def run_checks(run: Path, vis: Path, only=None, quiet=False, ns1a: Path = NS1A) -> dict:
    x = X(run, vis, ns1a)
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
    a = ap.parse_args(argv)
    res = run_checks(a.run, a.visuals)
    failed = [k for k, v in res.items() if not v["pass"]]
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(failed)}")
    summary = {"schema": "NS1b-check-summary-v1", "checks": res, "failed": failed,
               "marker": "NORTH_STAR1B_CHECKS_PASS" if not failed else "NORTH_STAR1B_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1B_CHECKS_PASS")
    if a.corruptions:
        import check_ns1b_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
