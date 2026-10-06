#!/usr/bin/env python3
"""North Star-1c2 checker: fail-capable verification of the corrected Controller-02 phase semantics (read-only).

    .venv/bin/python tools/north_star/check_ns1c2.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/north-star/ns1c2-controller02-phase-semantics-contract.md, section 24.  The checker keeps its own literal
pins and constants and recomputes independently where an independent formula exists: the coherent set (own rule), the
charts (own triple product), the world gazes (own column form), the fixed-head calibrations, the PERFECT correspondence
and the spherical geometry (the accepted NS1a checker's own implementations), the 12-mm association (own brute force),
the NORMAL classification and the ordinary-budget deferral (own rules) and every scheduler decision (the accepted
``schedule_normal`` on own statuses).  The accepted policy has no independent implementation: every recorded probe is
recomputed from its reconstructed context; the known answers (the differential with ``run_controller02``, the
accepted Controller-02 trace, the residue-gate harness) are re-run; the adapter is re-driven over the recorded probes.
``--corruptions`` runs the mutation suite (check_ns1c2_corruptions.py) from a passing mirror after a null probe.
"""
from __future__ import annotations

import argparse
import ast
import glob
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

PREFIX = "[ns1c2-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
BASE = "e2a7bb65434a0a2ec4d862a4c70918e00a472416"
NS1B_ACCEPTANCE = "255355108863022f931574dae4b2df8cdd2a772e"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
NS1C_REPORT_HEAD = "4107be86228c970f4b82fb6d5343365c551f36b0"
CONTRACT = "fa1da52f03366cb1a781b0ad6bd710e235b478f2"
CONTRACT_PATH = "docs/north-star/ns1c2-controller02-phase-semantics-contract.md"
REPORT_PATH = "docs/north-star/ns1c2-controller02-phase-semantics-report.md"
DECISION_PATH = "docs/north-star/ns1c-review-decision.md"
NS1C_ACCEPTED_MARKER = "NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_" + "ACCEPTED"
PREVIEWS = Path("/home/lvelho/rd/f3d-vision/previews")
NS1A = PREVIEWS / "north-star/ns1a-perfect-bootstrap-round"
NS1B = PREVIEWS / "north-star/ns1b-recentered-controller-handoff"
NS1C = PREVIEWS / "north-star/ns1c-coherent-first-scene-switch"
C01 = PREVIEWS / "controller-01-full"
C02 = PREVIEWS / "controller-02-classroom-replay"
NS1C_MANIFEST = "90e2dd4b8a2d287a47f22b4553903a06e0c1059105fec1f954c13da09d426638"
NS1C_CHECK_SUMMARY = "85cb931fabc596e69e6defee4fd289195b0717e968e858b60014c4ac0ec8952f"
NS1C_DECISIONS = {0: "3b4ea8475a4f9740e777fb9ced1afb73952351ec73ef9418f17bd5572ca421cf",
                  1: "03a04a58e84e7fa8e697f7385ad91b2a8eb077f95b2b21cdce363e74e518156a",
                  2: "c6c3aed41bc1c3c234a4b341594366be685b602b6386424da038dd6adaad00ce",
                  3: "90cd98c64c3974027cb064197a73584e7655598a137c8a5ca0aaddecd77b7a74"}
NS1C_FUSED = {0: "45412505bc1bcabcb663ddb893c4b0ce4a3a5cc0fdaede07f24dbaef0af7dc31",
              1: "250a04dc40ce73af115bb7bf8e72496c9c841a5ba5c7d9e3056b55df9e56e358",
              2: "e9cdd83065c934436ba4e7845c515da8318ee028c114b48896beb57229faa638",
              3: "41aeeb28a898d21563e9a62011daf2471b855305870461af8c50a23e70ad2c65"}
NS1C_PROBES = {0: "1850b4a8ab28f3b510ee6a0e961e8800189fd47d6505d29274da7b1aa8e85272",
               1: "df10044dd8b7244e2d9272f4d9501b04886d0f44df0c2263d8a33785afce21a0",
               2: "aeb16d575532c56d076622248926d67fa177464707f869679bd8c56f5ffe7021",
               3: "190cd2bedaa03ce834b51ca84750b5c2628b0150a4ce8599fac7f0252209941f"}
NS1A_PINS = {"freeze/observation-freeze.json": "46f0a22eab852b3c5750420ed993a453cd6b1e6c4d0cd0d96ce167883b87576d",
             "freeze/seed-set-freeze.json": "4ee36a1aa39525a7faa0132877d5cede14df185ae5607dbe73615a3ad2357173",
             "seeds/seed-set.json": "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a",
             "seeds/entity-maps.npz": "621d8902948656221d876f3642c78963b075a0ce5a5ae1227da3e2f65620f605"}
NS1B_PINS = {"fusion/fused-target-map.npz": "bf831ad5d49b226b878c73af80b19330620bfe201e85b7464a8bb63c3b4aad0c",
             "post/evidence.npz": "a96791631906e43d4598b7b6de7db66cdb52303835bdeb1fe533106e8b351f00",
             "post/controller-state.npz": "337c070525131bdbec4c061eaa85b389594cf999b468da399d8535058b1bd7f0",
             "post/post-action-probe.json": "2918e146294dace627acc1b8b097f5b4e5a072ec0c98cf0e2d65718b062f8bac",
             "context/controller-state.npz": "ceebc7250eb046a577bc3b024ab30ac1002141aea0e4ebd17a17571d41bba9cf",
             "chart/policy-chart.json": "8adefe86726fbe95d2e3782d9cf26db120959df5a746f061d87cfe038bcdc5df"}
C02_PINS = {"events.json": "fae7e64880f82602c8a868d0598bafab2c6d8da8e0c3f4465440c213d848327c",
            "final-residue.json": "a315714f0452621425fe8463e03d1b1c8e4b70d8ec9778e122ad518f90032c00"}
C01_DIGEST = "1f7b86558a5e48bc5c3349cde46c90e8f4cd409cff63b445d41a5bc6f37b85b5"
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
BUDGET = 24
CAP = 19
PREFIX_STEPS = 4
NS1B_POST = {"state": "ACTIONABLE", "source": "fsg6f", "local": [-5.0, -10.0]}
NS1B_GATE = {"admissible": True, "reason": "novel_support_in_predicted_cores", "novel": 22}
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
ONCE = ["source", "synthetic", "known-answer", "eligibility", "charts", "contexts", "initial-probe"]
PREFIX_STAGES = ["schedule", "replay", "fuse", "update"]
STEP = ["schedule", "preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
        "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "fuse", "update"]
DRIVERS = ["prefix", "divergence", "loop"]
NS1C2_FILES = ["tools/north_star/" + n for n in ("ns1c2_spec.py", "ns1c2_phase.py", "ns1c2_core.py", "ns1c2_render.py",
                                                 "ns1c2_run.py", "ns1c2_synthetic.py", "ns1c2_visuals.py",
                                                 "check_ns1c2.py", "check_ns1c2_corruptions.py")]
DECLARED = set(NS1C2_FILES) | {CONTRACT_PATH, REPORT_PATH, "tools/repository/check_repository_layout.py"}
PRODUCTION = ["ns1c2_spec.py", "ns1c2_phase.py", "ns1c2_core.py", "ns1c2_render.py", "ns1c2_run.py", "ns1c2_visuals.py"]
FORBIDDEN_IDENTIFIERS = {"run_control_loop", "catalog_summaries", "StereoSGBM_create", "StereoSGBM", "StereoBM_create",
                         "compute_natural", "run_match_gaze", "head_motion", "move_head", "reactivate"}
FORBIDDEN_MODULES = {"ab1d_match", "ab1d3_sgbm", "ab1a_stereo", "ab1c_planar", "fsg_stereo_sgbm"}
FORBIDDEN_READ = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                  "evaluation.json", "/evaluation/", "evaluation_only", "breadth-1-classroom", "natural-bootstrap-1a",
                  "natural-bootstrap-1b", "controller-01a", "controller-01b", "controller-01c", "actions.json",
                  "controller-02-classroom-replay/result.json", "controller-02-classroom-replay/manifest.json",
                  "controller-01-full/manifest.json")
TRUTH_STAGES = ("source/source-opened-files.json", "known-answer-opened-files.json", "contexts-opened-files.json",
                "observation-freeze-opened-files.json", "correspondence-opened-files.json",
                "segmentation-opened-files.json", "update-opened-files.json", "replay-opened-files.json")
HISTORY_STAGES = ("source/source-opened-files.json", "known-answer/known-answer-opened-files.json")
CLOSED = "SCENE" + "_CLOSED"
FIGURES = ["overview.png", "ns1c-vs-ns1c2-divergence.png", "controller-phase-timeline.png", "multi-entity-growth-3d.png",
           "controller-vs-northstar-support.png"]
TOL, ROUND = 1e-9, 1e-12


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
        return {"run": self.run, "ns1a": NS1A, "ns1b": NS1B, "ns1c": NS1C}[scheme] / rel

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
        return [(k, d) for k, d in self.decisions() if d["kind"] in ("attend", "final_residue")
                and self.has(f"steps/step-{k:02d}/update/update.json")]

    def sd(self, k: int) -> str:
        return f"steps/step-{k:02d}"

    def obs(self, k: int) -> Path:
        return NS1C / self.sd(k) if k < PREFIX_STEPS else self.run / self.sd(k)

    def charts(self) -> dict:
        return self.j("charts/policy-charts.json")["charts"]

    def ids(self) -> list[int]:
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


def own_local(probe: dict) -> str:
    """Accepted Controller-02 NORMAL classification: ACTIONABLE iff the probe carries a proposal (any source)."""
    return "ACTIONABLE" if probe.get("proposal") is not None else "QUIET"


def own_label(local: str, disposition: str, reason) -> str:
    return local if disposition == "NORMAL" else f"{local}/{disposition}:{reason}"


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
    return [e for e in x.log() if e["status"] == "ok" and e["command"] in ONCE + STEP + PREFIX_STAGES + DRIVERS]


def probe_file(x: X, rec: dict) -> dict:
    return json.loads(x.res(rec["probe"]["path"]).read_text())


def probe_paths(x: X) -> list[Path]:
    out = sorted((x.run / "initial-probe/probes").glob("e*.json"))
    if x.has("steps"):
        out += sorted((x.run / "steps").glob("step-*/update/probes/e*.json"))
    return out


def own_probe(x: X, rec: dict, k: str):
    import ns1c2_core as CORE
    return CORE.probe_entity(rec, x.run, x.charts()[k], f"checker probe {k}")


def probe_key(rec: dict, k: str) -> str:
    return "probe-" + k + hashlib.sha256(json.dumps({f: rec[f] for f in ("looks", "evidence", "map", "visited",
                                                                          "current_local_gaze")},
                                                     sort_keys=True).encode()).hexdigest()


def policy_diffs(saved: dict, mine: dict) -> list[str]:
    import ns1c2_core as CORE
    return CORE.policy_comparison(saved, CORE.jsonable(mine))


def ns1c_manifest_ok() -> tuple[bool, dict]:
    if sha256(NS1C / "manifest.json") != NS1C_MANIFEST:
        return False, {}
    return True, json.loads((NS1C / "manifest.json").read_text())


# ---------------------------------------------------------------- the checks
def c01(x):
    origin = git("remote", "get-url", "origin")
    anc = {n: ancestor(s) for n, s in (("base", BASE), ("ns1b_acceptance", NS1B_ACCEPTANCE),
                                       ("ns1a_acceptance", NS1A_ACCEPTANCE), ("contract", CONTRACT))}
    unchanged = subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode == 0
    added = git("log", "--diff-filter=A", "--format=%H", "--", CONTRACT_PATH).split()[-1:] == [CONTRACT]
    impl = {e["code"]["commit"] for e in ok_entries(x)}
    later = bool(impl) and all(c != CONTRACT and ancestor(CONTRACT, c) for c in impl)
    import ns1c2_spec as SPm
    spec = (SPm.CONTRACT_COMMIT == CONTRACT and SPm.BASE_COMMIT == BASE and SPm.NS1B_ACCEPTANCE == NS1B_ACCEPTANCE
            and SPm.NS1A_ACCEPTANCE == NS1A_ACCEPTANCE and SPm.NS1C_REPORT_HEAD == NS1C_REPORT_HEAD)
    src = x.j("source/source-manifest.json")
    ok = (CANONICAL_REMOTE in origin and all(anc.values()) and unchanged and added and later and spec
          and src["contract_commit"] == CONTRACT and src["contract_unchanged"] and CANONICAL_REMOTE in src["origin"]
          and src["base_commit"] == BASE and src["ns1b_acceptance"] == NS1B_ACCEPTANCE
          and src["ns1a_acceptance"] == NS1A_ACCEPTANCE
          and src["ns1c_diagnostic_source"]["report_head"] == NS1C_REPORT_HEAD)
    return ok, {"origin": origin, "ancestors": anc, "contract_unchanged": unchanged, "contract_added_at": added,
                "canonical_commits": sorted(impl), "after_contract": later, "spec": spec}


def c02(x):
    import ns1c2_spec as SPm
    digest = hashlib.sha256(json.dumps(SPm.SOURCE_PINS, sort_keys=True).encode()).hexdigest()
    bad = sorted(p for p, h in SPm.SOURCE_PINS.items() if sha256(REPO / p) != h)
    src = x.j("source/source-manifest.json")
    a = {r: sha256(NS1A / r) for r in NS1A_PINS}
    b = {r: sha256(NS1B / r) for r in NS1B_PINS}
    man_ok, man = ns1c_manifest_ok()
    c_ok = man_ok and sha256(NS1C / "check-summary.json") == NS1C_CHECK_SUMMARY and all(
        man["files"].get(f"steps/step-{k:02d}/{rel}") == h and sha256(NS1C / f"steps/step-{k:02d}/{rel}") == h
        for pins in ((NS1C_DECISIONS, "plan/decision.json"), (NS1C_FUSED, "fusion/fused-target-map.npz"),
                     (NS1C_PROBES, "update/probes/e00172.json")) for k, h in pins[0].items() for rel in (pins[1],))
    c02_ = {f: sha256(C02 / f) for f in C02_PINS}
    files = sorted(glob.glob(str(C01 / "objects/instance_*/trajectory.partial.json")))
    c01d = hashlib.sha256("".join(f"{Path(f).relative_to(C01)} {sha256(f)}\n" for f in files).encode()).hexdigest()
    ok = (digest == SOURCE_PINS_DIGEST and not bad and src["source_pins"] == SPm.SOURCE_PINS
          and a == NS1A_PINS and b == NS1B_PINS and c_ok and c02_ == C02_PINS and c01d == C01_DIGEST
          and src["ordinary_budget"] == BUDGET and src["ns1c_diagnostic_source"]["manifest_sha256"] == NS1C_MANIFEST
          and src["history"]["controller02"] == C02_PINS and src["history"]["controller01_trajectory_digest"] == C01_DIGEST
          and src["ns1b_check_marker"] == "NORTH_STAR1B_CHECKS_PASS" and sha256(HEAD_SOURCE[0]) == HEAD_SOURCE[1])
    return ok, {"pins_digest": digest, "changed": bad, "ns1c_pins": c_ok, "history": [c02_ == C02_PINS,
                                                                                       c01d == C01_DIGEST]}


def c03(x):
    md = [f for f in git("ls-files").split("\n") if f.endswith(".md") and (REPO / f).is_file()]
    hits = [f for f in md if NS1C_ACCEPTED_MARKER in (REPO / f).read_text(errors="replace")]
    anc = {ref: ancestor(NS1C_REPORT_HEAD, ref) for ref in ("HEAD", "origin/main", BASE)}
    note = REPO / DECISION_PATH
    note_ok = note.is_file() and "NS1c:  REVIEWED · NOT ACCEPTED · NOT MERGED" in note.read_text()
    at_base = "NS1c:  REVIEWED · NOT ACCEPTED · NOT MERGED" in git("show", f"{BASE}:{DECISION_PATH}")
    src = x.j("source/source-manifest.json")["ns1c_decision"]
    ok = not hits and not any(anc.values()) and note_ok and at_base and src["ok"] and not src["accepted_marker_files"]
    return ok, {"accepted_marker_files": hits, "ns1c_report_head_ancestor_of": anc, "decision_note": note_ok,
                "decision_at_base": at_base}


def c04(x):
    rows = own_seed_rows()
    coh = sorted(k for k, e in rows.items() if e["initialized"] and int(e["contributing_patches"]) == 1)
    dfr = sorted(k for k, e in rows.items() if e["initialized"] and int(e["contributing_patches"]) > 1)
    el = x.j("eligibility/coherent-seed-set.json")
    bad = []
    if not (coh == COHERENT and dfr == DEFERRED and el["coherent_ids"] == COHERENT and el["deferred_ids"] == DEFERRED
            and el["scene_ids"] == COHERENT and not el.get("DEV_OVERRIDE") and el["matches_expectation"]
            and el["fields_read"] == ["temporary_entity_id", "initialized", "contributing_patches",
                                      "initialized_at_rank", "final_surfels"]):
        bad.append("eligibility record")
    for st in x.states():
        if sorted(int(k) for k in st["entities"]) != COHERENT or st["scene_ids"] != COHERENT:
            bad.append(f"{st['label']}: scene entities")
        if sorted(r["temporary_entity_id"] for r in st["deferred"]) != DEFERRED or any(
                r["state"] != DEFERRED_STATE or r["in_scheduler"] for r in st["deferred"]):
            bad.append(f"{st['label']}: deferred rows")
        if sorted(int(i) for i in st["machine"]["order"]) != COHERENT:
            bad.append(f"{st['label']}: adapter order")
    for k, d in x.decisions():
        if [int(a) for a, _b in d["scheduler_decision"]["statuses"]] != COHERENT:
            bad.append(f"step {k}: scheduler input")
        if d.get("action") and int(d["action"]["target"]) in DEFERRED:
            bad.append(f"step {k}: deferred target")
    guard = x.j("eligibility/eligibility-opened-files.json")
    want = {str((NS1A / f).resolve()) for f in ("seeds/seed-set.json", "freeze/seed-set-freeze.json",
                                                "source/nb1c-gaze-list.json")}
    if set(guard["data_reads"]) != want or guard["violations"]:
        bad.append("eligibility reads")
    return not bad, {"own_coherent": coh, "own_deferred": dfr, "problems": bad[:6]}


def c05(x):
    rows = own_seed_rows()
    chs = x.charts()
    bad = []
    for k in x.ids():
        ch = chs[str(k)]
        r = int(rows[k]["initialized_at_rank"])
        g0 = own_dir(*GAZES[r])
        mine = own_chart(g0)
        rr = np.asarray(ch["R_HC"], float)
        perp = float(np.linalg.norm(np.cross(np.cross(g0, [1.0, 0, 0]), g0)))
        if not (float(np.abs(mine - rr).max()) <= 1e-15 and float(np.abs(rr.T @ rr - np.eye(3)).max()) <= ROUND
                and abs(float(np.linalg.det(rr)) - 1.0) <= ROUND and max(map(abs, own_yp(rr.T @ g0))) <= 1e-9
                and perp >= 1e-6 and ch["seed_gaze_H0_deg"] == list(GAZES[r]) and ch["chart_id"] == f"C_{k}"
                and ch["R_HC_sha256"] == hashlib.sha256(np.ascontiguousarray(rr).tobytes()).hexdigest()):
            bad.append(f"chart {k}")
    nb = json.loads((NS1B / "chart/policy-chart.json").read_text())
    same172 = np.array_equal(np.asarray(chs[str(CONTINUING)]["R_HC"]), np.asarray(nb["R_HC"]))
    for st in x.states():
        for k, rec in st["entities"].items():
            if rec["chart_sha256"] != chs[k]["R_HC_sha256"] or rec["chart_id"] != chs[k]["chart_id"]:
                bad.append(f"{st['label']}: entity {k} chart changed")
    for p in probe_paths(x):
        pf = json.loads(p.read_text())
        if np.asarray(pf["probe"]["adapter"]["R_HC"]).tolist() != chs[str(pf["entity"])]["R_HC"]:
            bad.append(f"{p.name}: probe chart is not the entity's fixed chart")
    return not bad and same172, {"problems": bad[:6], "c172_equals_ns1b": same172}


def c06(x):
    import fsg6f_public as PUB
    from fov3d.control import frontier_config
    from fov3d.experiments.classroom_oracle import config as public, controller01 as c01m, controller02 as x2
    import tools.classroom_oracle1_epistemic as EPL
    used = x.j("initial-probe/initial-service-table.json")["policy_configuration_used"]
    live = {"SURFACE_FRONTIER": dict(PUB.SURFACE_FRONTIER), "facade": dict(frontier_config.SURFACE_FRONTIER),
            "FUSION": dict(PUB.FUSION), "OBJECT_ID": int(PUB.OBJECT_ID), "grid": float(public.CYCLOPEAN_GRID_DEG),
            "c_fusion": dict(public.FUSION), "shape": list(EPL.make_evidence().shape), "budget": int(x2.BUDGET),
            "watchdog": int(c01m.WATCHDOG)}
    rec = {"SURFACE_FRONTIER": used["SURFACE_FRONTIER"], "facade": used["SURFACE_FRONTIER_facade"],
           "FUSION": used["FSG6F_FUSION"], "OBJECT_ID": used["OBJECT_ID"], "grid": used["CYCLOPEAN_GRID_DEG"],
           "c_fusion": used["FUSION"], "shape": used["cyclopean_chart_shape"],
           "budget": x.j("source/source-manifest.json")["accepted_constants"]["ORDINARY_BUDGET"],
           "watchdog": x.j("source/source-manifest.json")["accepted_constants"]["CONTROLLER01_WATCHDOG"]}
    want = {"SURFACE_FRONTIER": POLICY, "facade": POLICY, "FUSION": FUSION, "OBJECT_ID": OBJECT_ID, "grid": CYC_GRID,
            "c_fusion": FUSION, "shape": CYC_SHAPE, "budget": BUDGET, "watchdog": BUDGET}
    budgets = {st["budget"] for st in x.states()} | {st["machine"]["budget"] for st in x.states()}
    caps = {st.get("cap") for st in x.states()}
    div = x.j("divergence/divergence.json") if x.has("divergence/divergence.json") else None
    cap_ok = div is None or (div["cap"] == (BUDGET - div["own_looks_172"]) + 1 == CAP)
    ok = live == want and rec == want and budgets == {BUDGET} and cap_ok and caps <= {None}
    return ok, {"live_equal": live == want, "recorded_equal": rec == want, "budgets": sorted(budgets),
                "cap_ok": cap_ok}


def c07(x):
    bad, seen = [], set()
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
        if not d.get("action"):
            continue
        r = np.asarray(chs[str(d["action"]["target"])]["R_HC"], float)
        w = own_world(d["action"]["local_gaze_deg"], r)
        real, fake = own_calibration(*w), own_calibration(*d["action"]["local_gaze_deg"])
        plan = json.loads((x.run / x.sd(k) / "plan/planned-calibration.json").read_text())
        if not (fixed_head(plan) and cal_close(plan, real) and not cal_close(plan, fake)):
            bad.append(f"step {k}: planned calibration is not the real sensor at the world gaze")
        cal = x.obs(k) / "observation/acquisition/calibration.json"
        if cal.exists():
            exe = json.loads(cal.read_text())
            if not (fixed_head(exe) and cal_close(exe, real) and not cal_close(exe, fake)):
                bad.append(f"step {k}: executed calibration")
    return not bad, {"problems": bad[:6], "looks_checked": len(seen)}


def c08(x):
    s0 = x.j("scene/state-initial.json")
    bad = []
    r = s0["entities"].get(str(CONTINUING))
    if r is None:
        return False, {"problems": ["172 is not in the scene"]}
    if [lk["calibration"] for lk in r["looks"]] != ["ns1a:observations/rank-06/acquisition/calibration.json",
                                                     "ns1b:observation/acquisition/calibration.json"]:
        bad.append("172 looks")
    if not arrays_equal(load(x.res(r["looks"][0]["state"])), load(NS1B / "context/controller-state.npz")) or \
            not arrays_equal(load(x.res(r["looks"][1]["state"])), load(NS1B / "post/controller-state.npz")):
        bad.append("172 look states != NS1b")
    if not arrays_equal(load(x.res(r["evidence"]["path"])), load(NS1B / "post/evidence.npz")):
        bad.append("172 evidence != NS1b")
    m = load(x.res(r["map"]["path"]))
    if not arrays_equal(m, load(NS1B / "fusion/fused-target-map.npz")) or len(m["xyz_h"]) != 21243:
        bad.append("172 map != NS1b post-action map")
    if r["own_looks"] != 2 or r["visited"] != [[0.0, 0.0], [0.0, -5.0]] or r["current_local_gaze"] != [0.0, -5.0]:
        bad.append("172 own looks / visited / gaze")
    import ns1c2_core as CORE
    maps = load(NS1A / "seeds/entity-maps.npz")
    ofz = json.loads((NS1A / "freeze/observation-freeze.json").read_text())
    for k in x.ids():
        if k == CONTINUING:
            continue
        rec = s0["entities"][str(k)]
        rank = int(rec["initialization_rank"])
        cal_rel = f"observations/rank-{rank:02d}/acquisition/calibration.json"
        if rec["looks"][0]["calibration"] != f"ns1a:{cal_rel}" or rec["looks"][0]["calibration_sha256"] != \
                ofz["files"][cal_rel] or sha256(NS1A / cal_rel) != ofz["files"][cal_rel]:
            bad.append(f"{k}: initialization look")
        mk = {f: np.asarray(maps[f"e{k:05d}_{f}"]) for f in ("xyz_h", "rgb", "instance_id", "support_count",
                                                            "provenance_mask")}
        mm = load(x.res(rec["map"]["path"]))
        if not all(np.array_equal(np.asarray(mm[f]), mk[f]) for f in mk) or rec["own_looks"] != 1 or \
                rec["visited"] != [[0.0, 0.0]]:
            bad.append(f"{k}: map / own looks / visited")
        ev = CORE.evidence_arrays(CORE.rebuild_context(rec, x.run, np.asarray(x.charts()[str(k)]["R_HC"], float)))
        if not arrays_equal(ev, load(x.res(rec["evidence"]["path"]))):
            bad.append(f"{k}: evidence does not recompute")
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    no_render = "acquire" not in order or order.index("acquire") > order.index("initial-probe")
    return not bad and no_render, {"problems": bad[:6], "no_render_before_initial_probe": no_render}


def c09(x):
    import ns1c2_core as CORE
    s0 = x.j("scene/state-initial.json")
    tab = x.j("initial-probe/initial-service-table.json")
    nbp = json.loads((NS1B / "post/post-action-probe.json").read_text())["probe"]
    bad, inv = [], {}
    for k in map(str, x.ids()):
        rec = s0["entities"][k]
        saved = json.loads((x.run / f"initial-probe/probes/e{int(k):05d}.json").read_text())
        mine = memo(x, probe_key(rec, k), lambda rec=rec, k=k: own_probe(x, rec, k))
        d = policy_diffs(saved["probe"], mine)
        if d or saved["gate_called"] is not False or saved["probe"]["adapter"]["calls"]["P3"] != 0 or \
                "gate" in saved["probe"]:
            bad.append(f"{k}: recomputed / ungated probe {d[:2]}")
        nc = NS1C / f"initial-probe/probes/e{int(k):05d}.json"
        dn = policy_diffs(json.loads(nc.read_text())["probe"], mine) if nc.exists() else ["no NS1c probe"]
        if dn:
            bad.append(f"{k}: differs from NS1c's initial probe {dn[:2]}")
        rot = CORE.rotation_invariance(rec, x.run, x.charts()[k], mine, betas=(-23.0,))
        inv[k] = rot[0]["pass"]
        if not rot[0]["pass"] or not all(r_["pass"] for r_ in saved["baseline_rotation_invariance"]):
            bad.append(f"{k}: rotation invariance")
    d172 = policy_diffs(nbp, memo(x, probe_key(s0["entities"][str(CONTINUING)], str(CONTINUING)),
                                  lambda: own_probe(x, s0["entities"][str(CONTINUING)], str(CONTINUING))))
    p = json.loads((x.run / f"initial-probe/probes/e{CONTINUING:05d}.json").read_text())["probe"]["proposal"] or {}
    got = {"state": "ACTIONABLE" if p else "QUIET", "source": p.get("source"), "local": p.get("local_gaze_deg")}
    n = [e for e in x.log() if e["command"] == "initial-probe" and e["status"] == "ok"]
    guard = x.j("initial-probe/initial-probe-opened-files.json")
    no_truth = not any(q.endswith(("reference-observation.npz", ".exr")) for q in guard["data_reads"])
    ok = (not bad and not d172 and got == NS1B_POST and tab["ns1b_reproduction"]["reproduced"] and len(n) == 1
          and not guard["violations"] and no_truth and tab["gate_guard"]["calls"] == 0)
    return ok, {"problems": bad[:6], "own_rotation": inv, "ns1b": got, "ns1b_diffs": d172[:3], "runs": len(n)}


def c10(x):
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    import ns1c2_synthetic as SY
    from fov3d.control import controller02 as c2
    rep = x.j("synthetic/synthetic-report.json")
    mine = memo(x, "synthetic", SY.run_all)
    ka = x.j("known-answer/known-answer.json")
    files = sorted(glob.glob(str(C01 / "objects/instance_*/trajectory.partial.json")))
    traj = {int(Path(f).parent.name.split("_")[1]): json.loads(Path(f).read_text()) for f in files}
    hist = memo(x, "historical", lambda: SY.historical_trace(traj, json.loads((C02 / "events.json").read_text())["events"],
                                                             json.loads((C02 / "final-residue.json").read_text()), BUDGET))
    h_ok, h_checks = SY.historical_ok(hist)
    rec_h = ka["historical_controller02_trace"]
    same_h = all(rec_h.get(k) == CORE.jsonable(hist[k]) for k in ("actions", "events", "switches", "bouts", "phases",
                                                                  "deferred", "gate_calls", "residue_decisions"))
    hh = ka["residue_gate_harness"]
    # the residue-gate wiring re-run: 172 at its NS1b post-action state, the production residue path, phase RESIDUE
    import ns1c2_run as R
    rec172 = R.ns1b_172_record(x.run)
    ch = CORE.chart_record(CONTINUING, 6, GAZES[6])
    cal0 = json.loads((NS1A / "observations/rank-06/acquisition/calibration.json").read_text())

    def harness():
        out = CORE.probe_entity(rec172, x.run, ch, "checker harness probe")
        with PH.GateGuard(c2.ScenePhase.RESIDUE.value, "checker residue harness"):
            _v, det = CORE.residue_gate(rec172, x.run, ch, out, CORE.probe_result(out, CONTINUING),
                                        np.asarray(cal0["head_R_wh"]), np.asarray(cal0["head_origin_w_m"]))
        return det
    det = memo(x, "harness", harness)
    harness_ok = (det["admissible"] is True and det["reason"] == NS1B_GATE["reason"]
                  and det["detail"]["counts"]["novel_service_count"] == NS1B_GATE["novel"]
                  and hh["ok"] and hh["phase_at_gate"] == "RESIDUE" and hh["executed"] is False
                  and hh["gate_guard"]["normal_calls"] == 0 and hh["verdict"] == {"admissible": True,
                                                                                    "reason": NS1B_GATE["reason"]})
    ok = (rep["failed"] == [] and mine["failed"] == [] and rep["count"] == mine["count"] and h_ok and rec_h["ok"]
          and same_h and harness_ok and ka["ok"])
    return ok, {"synthetic_failed": mine["failed"], "historical": h_checks, "recorded_equal": same_h,
                "harness": harness_ok}


def own_statuses(x: X) -> list[dict]:
    """Own NORMAL classification and deferral over every scene state: local from the probe alone; DEFERRED sticky
    once an ACTIONABLE NORMAL entity's own fixations (own looks) reach the budget; FINALIZED only by residue records."""
    out, disp = [], {}
    for st in x.states():
        row = {}
        fin = {int(r["object"]): r["outcome"] for r in st["machine"]["residue_decisions"]}
        for k, rec in st["entities"].items():
            local = own_local(probe_file(x, rec)["probe"])
            d, why = disp.get(k, ("NORMAL", None))
            if d == "NORMAL" and local == "ACTIONABLE" and int(rec["own_looks"]) >= BUDGET:
                d, why = "DEFERRED", "ordinary_budget"
            if int(k) in fin:
                d, why = "FINALIZED", fin[int(k)]
            disp[k] = (d, why)
            row[k] = own_label(local, d, why)
        out.append(row)
    return out


def c11(x):
    sts = x.states()
    own = own_statuses(x)
    bad, cyc = [], 0
    for st, mine in zip(sts, own):
        for k, rec in st["entities"].items():
            if rec["status"]["label"] != mine[k]:
                bad.append(f"{st['label']} {k}: {rec['status']['label']} != own {mine[k]}")
            m = st["machine"]["statuses"][k]
            if own_label(m[1], m[2], m[3]) != mine[k]:
                bad.append(f"{st['label']} {k}: adapter status")
            pf = probe_file(x, rec)
            if sha256(x.res(rec["probe"]["path"])) != rec["probe"]["sha256"] or pf["revision"] != rec["probe"]["revision"]:
                bad.append(f"{st['label']} {k}: probe record")
            p = pf["probe"]["proposal"]
            if p is not None and p["source"] == "cyclopean_epistemic" and mine[k].startswith("ACTIONABLE"):
                cyc += 1
    tab = {r["temporary_entity_id"]: r for r in x.j("initial-probe/initial-service-table.json")["rows"]}
    for k, rec in sts[0]["entities"].items():
        if tab[int(k)]["label"] != rec["status"]["label"]:
            bad.append(f"initial table {k}")
    return not bad, {"problems": bad[:6], "cyclopean_actionable_rows": cyc}


def c12(x):
    from fov3d.control import controller02 as c2
    sts = x.states()
    own = own_statuses(x)
    bad = []
    if sts[0]["current"] != CONTINUING or sts[0]["attention_bout"] != 1 or sts[0]["phase"] != "NORMAL":
        bad.append("the initial current object is not 172 (bout 1, NORMAL)")
    for i, (k, d) in enumerate(x.decisions()):
        prev = sts[i] if i < len(sts) else None
        if prev is None or prev["global_step"] != k - 1:
            bad.append(f"step {k}: no preceding scene state")
            break
        rows = []
        for kk in sorted(prev["entities"], key=int):
            lab = own[i][kk]
            local, _, rest = lab.partition("/")
            dsp, _, why = rest.partition(":")
            rows.append(c2.ObjectStatus(int(kk), c2.ic.ServiceState(local), c2.Disposition(dsp or "NORMAL"), why or None))
        mine = c2.schedule_normal(prev["current"], rows)
        rec = d["scheduler_decision"]["result"]
        got = None if mine is None else {"kind": mine.kind, "target_id": mine.target_id, "reason": mine.reason}
        if got != rec or d["scheduler_decision"]["current_before"] != prev["current"]:
            bad.append(f"step {k}: own schedule_normal {got} != recorded {rec}")
            continue
        if d["kind"] == "attend":
            t = str(mine.target_id)
            pf = probe_file(x, prev["entities"][t])["probe"]
            a = d["action"]
            reason = "natural_reactivation" if mine.reason == "switch" and int(t) in \
                prev["machine"]["reactivated_since_attended"] else mine.reason
            if (int(a["target"]) != mine.target_id or pf["proposal"] is None
                    or a["local_gaze_deg"] != pf["proposal"]["local_gaze_deg"] or a["source"] != pf["proposal"]["source"]
                    or d["scheduler_reason"] != reason or a["phase"] != "NORMAL"
                    or d["target_transition"] != ("retain" if prev["current"] == int(t) else f"{prev['current']}->{t}")):
                bad.append(f"step {k}: the action is not the selected entity's unchanged current proposal")
            if mine.reason == "switch" and own[i][str(prev["current"])] == "ACTIONABLE":
                bad.append(f"step {k}: switch while the current entity is NORMAL ACTIONABLE")
        elif d["kind"] == "final_residue" and mine is not None:
            bad.append(f"step {k}: a residue action while NORMAL work exists")
    src = (HERE / "ns1c2_phase.py").read_text()
    uses = "decision = c2.schedule_normal(self.current, self.statuses.values())" in src
    prod = "".join((HERE / n).read_text() for n in PRODUCTION)
    no_old = "ic.schedule(" not in prod and "integrated.schedule(" not in prod
    return not bad and uses and no_old, {"problems": bad[:6], "uses_schedule_normal": uses, "no_integrated_schedule": no_old}


def c13(x):
    """Re-drive the adapter from the initial state over the recorded probes: every recorded decision, event, phase,
    current object, bout and status must be reproduced."""
    import ns1c2_core as CORE
    import ns1c2_phase as PH
    from fov3d.control import controller02 as c2, integrated as ic
    sts = x.states()
    m = PH.SceneMachine.from_json(sts[0]["machine"])
    bad = []
    for i, (k, d) in enumerate(x.executed(), start=1):
        st = sts[i]
        refs = {kk: rec["probe"]["path"] for kk, rec in st["entities"].items()}
        revs = {kk: rec["revision"] for kk, rec in st["entities"].items()}

        def probe(e, refs=refs, revs=revs):
            pf = json.loads(x.res(refs[str(e)]).read_text())
            return CORE.probe_result(pf["probe"], e, {"probe_path": refs[str(e)], "revision": revs[str(e)]})

        def gate(e, proposal, d=d):
            rr = [r for r in d.get("residue_gate_records", []) if int(r["object"]) == e]
            return c2.FinalProbeDecision(bool(rr[0]["admissible"]), rr[0]["reason"]) if rr else \
                c2.FinalProbeDecision(False, "no recorded verdict")
        n0 = len(m.events)
        plan = m.decide(gate)
        if plan["kind"] != d["kind"] or int(plan.get("target_id", -1)) != int(d["action"]["target"]) or \
                plan.get("reason") != d["scheduler_reason"]:
            bad.append(f"step {k}: re-driven {plan['kind']} {plan.get('target_id')} {plan.get('reason')}")
            break
        m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, lambda e, revs=revs: revs[str(e)])
        ev = [[e["event"], int(e["object"]), int(e["global_step"])] for e in m.events[n0:]]
        rec_ev = [[e["event"], int(e["object"]), int(e["global_step"])] for e in st["events"]]
        labels = {str(kk): s_.label for kk, s_ in m.statuses.items()}
        if labels != {kk: rec["status"]["label"] for kk, rec in st["entities"].items()} or m.phase.value != st["phase"] \
                or m.current != st["current"] or m.bout != st["attention_bout"] or ev != rec_ev:
            bad.append(f"step {k}: re-driven state / events differ ({ev} vs {rec_ev})")
    return not bad, {"problems": bad[:4], "steps": len(x.executed())}


def c14(x):
    bad = []
    recs = []
    for st in x.states():
        recs.append((st["label"], st.get("gate_guard") or {}))
    for k, d in x.decisions():
        recs.append((f"decision {k}", d.get("gate_guard") or {}))
        for r in d.get("residue_gate_records", []):
            if r["phase"] != "RESIDUE":
                bad.append(f"step {k}: a residue gate record outside RESIDUE")
        if x.has(f"{x.sd(k)}/update/update.json"):
            recs.append((f"update {k}", x.j(f"{x.sd(k)}/update/update.json").get("gate_guard") or {}))
    recs.append(("initial-probe", x.j("initial-probe/initial-service-table.json")["gate_guard"]))
    if x.has("divergence/divergence.json"):
        recs.append(("divergence", x.j("divergence/divergence.json")["gate_guard"]))
    normal_total = 0
    for lab, g in recs:
        if not g:
            bad.append(f"{lab}: no gate-guard record")
            continue
        normal_total += int(g["normal_calls"])
        if g["normal_calls"] or g["refused"]:
            bad.append(f"{lab}: gate called outside RESIDUE")
    for p in probe_paths(x):
        pf = json.loads(p.read_text())
        if pf["gate_called"] is not False or pf["probe"]["adapter"]["calls"]["P3"] != 0 or "gate" in pf["probe"] or \
                pf["phase_at_probe"] != "NORMAL":
            bad.append(f"{p.name}: a NORMAL probe consulted the gate")
    for st in x.states():
        for g in st["machine"]["gate_log"]:
            if g["phase"] != "RESIDUE":
                bad.append(f"{st['label']}: adapter gate log outside RESIDUE")
    return not bad and normal_total == 0, {"problems": bad[:6], "normal_gate_calls": normal_total,
                                           "guard_records": len(recs)}


def c15(x):
    sts = x.states()
    by_step = {st["global_step"]: st for st in sts}
    bad = []
    for st in sts:
        for k, rec in st["entities"].items():
            if "BLOCKED" in rec["status"]["label"] or rec["status"]["disposition"] not in ("NORMAL", "DEFERRED",
                                                                                           "FINALIZED"):
                bad.append(f"{st['label']} {k}: {rec['status']['label']}")
            if int(st["machine"]["fixations"][k]) != int(rec["own_looks"]):
                bad.append(f"{st['label']} {k}: adapter fixations != own looks")
            if rec["status"]["disposition"] == "DEFERRED" and int(rec["own_looks"]) < BUDGET:
                bad.append(f"{st['label']} {k}: deferred below the budget")
        for e in st.get("events", []):
            if e["event"] == "deferred" and (int(e["fixations"]) != BUDGET or e["reason"] != "ordinary_budget"):
                bad.append(f"{st['label']}: deferral not exactly at the budget")
        for g in st["machine"]["gate_log"]:           # a gate decision at step s used the state after step s - 1
            before = by_step.get(int(g["global_step"]) - 1)
            if before is None or any(r["status"]["serviceable"] for r in before["entities"].values()):
                bad.append(f"{st['label']}: gate decision while NORMAL work remains")
    return not bad, {"problems": bad[:6]}


def c16(x):
    man_ok, man = ns1c_manifest_ok()
    bad = [] if man_ok else ["NS1c manifest"]
    pref = [(k, d) for k, d in x.decisions() if k < PREFIX_STEPS]
    if [k for k, _ in pref] != list(range(PREFIX_STEPS)):
        bad.append(f"prefix steps {[k for k, _ in pref]}")
    for k, d in pref:
        s = x.sd(k)
        nd_rel = f"steps/step-{k:02d}/plan/decision.json"
        if sha256(NS1C / nd_rel) != NS1C_DECISIONS[k]:
            bad.append(f"step {k}: NS1c decision pin")
            continue
        nd = json.loads((NS1C / nd_rel).read_text())["action"]
        a = d["action"]
        if not (int(a["target"]) == CONTINUING == int(nd["target"]) and d["scheduler_decision"]["result"]["reason"] ==
                "retain" and a["source"] == nd["source"] == "fsg6f" and a["local_gaze_deg"] == nd["local_gaze_deg"]
                and a["world_gaze_deg"] == nd["world_gaze_deg"]
                and a["planned_calibration_sha256"] == nd["planned_calibration_sha256"]
                and (x.run / s / "plan/planned-calibration.json").read_bytes() ==
                (NS1C / f"steps/step-{k:02d}/plan/planned-calibration.json").read_bytes()):
            bad.append(f"step {k}: the corrected decision is not NS1c's action")
        if x.has(f"{s}/observation") or x.has(f"{s}/preflight") or x.has(f"{s}/correspondence") or \
                x.has(f"{s}/geometry"):
            bad.append(f"step {k}: a prefix step holds its own observation products")
        if any(e["command"] in ("preflight", "acquire") and e["step"] == k for e in x.log()):
            bad.append(f"step {k}: Blender stage logged in the prefix")
        for f in ("plan/plan-opened-files.json", "replay/replay-opened-files.json", "fusion/fusion-opened-files.json",
                  "update/update-opened-files.json"):
            pg = x.j(f"{s}/{f}").get("process_guard") or {}
            if pg.get("attempts") != [] or "NoProcessGuard" not in str(pg.get("guard")):
                bad.append(f"step {k}: {f} process guard")
        rp = x.j(f"{s}/replay/replay.json")
        if not rp["ok"] or any(man["files"].get(r) != h for r, h in rp["verified_files"].items()):
            bad.append(f"step {k}: replay record")
        fused = load(x.run / s / "fusion/fused-target-map.npz")
        if sha256(NS1C / f"steps/step-{k:02d}/fusion/fused-target-map.npz") != NS1C_FUSED[k] or not arrays_equal(
                fused, load(NS1C / f"steps/step-{k:02d}/fusion/fused-target-map.npz")):
            bad.append(f"step {k}: fused map != NS1c's")
        if not arrays_equal(load(x.run / s / "update/controller-state.npz"),
                            load(NS1C / f"steps/step-{k:02d}/update/controller-state.npz")) or not arrays_equal(
                load(x.run / s / "update/evidence.npz"), load(NS1C / f"steps/step-{k:02d}/update/evidence.npz")):
            bad.append(f"step {k}: controller state / evidence != NS1c's")
        np_rel = f"steps/step-{k:02d}/update/probes/e00172.json"
        if sha256(NS1C / np_rel) != NS1C_PROBES[k] or policy_diffs(
                json.loads((NS1C / np_rel).read_text())["probe"],
                json.loads((x.run / s / "update/probes/e00172.json").read_text())["probe"]):
            bad.append(f"step {k}: probe policy part != NS1c's")
        mine = x.j(f"scene/state-after-step-{k:02d}.json")["entities"][str(CONTINUING)]
        theirs = json.loads((NS1C / f"scene/state-after-step-{k:02d}.json").read_text())["entities"][str(CONTINUING)]
        if [mine[f] for f in ("own_looks", "visited", "current_local_gaze", "revision")] != \
                [theirs[f] for f in ("own_looks", "visited", "current_local_gaze", "revision")] or \
                [lk["calibration_sha256"] for lk in mine["looks"]] != [lk["calibration_sha256"] for lk in theirs["looks"]]:
            bad.append(f"step {k}: history / revision != NS1c's")
    return not bad, {"problems": bad[:6], "prefix_steps": [k for k, _ in pref]}


def c17(x):
    if not x.has("divergence/divergence.json"):
        return False, {"problems": ["no divergence record"]}
    from fov3d.control import controller02 as c2
    div = x.j("divergence/divergence.json")
    fz = x.j("freeze/divergence-freeze.json")
    st3 = x.j(f"scene/state-after-step-{PREFIX_STEPS - 1:02d}.json")
    rec = st3["entities"][str(CONTINUING)]
    mine = memo(x, probe_key(rec, str(CONTINUING)), lambda: own_probe(x, rec, str(CONTINUING)))
    nprobe = json.loads((NS1C / f"steps/step-{PREFIX_STEPS - 1:02d}/update/probes/e00172.json").read_text())["probe"]
    n4 = json.loads((NS1C / "steps/step-04/plan/decision.json").read_text())
    own = own_statuses(x)[PREFIX_STEPS]
    rows = []
    for kk in sorted(own, key=int):
        local, _, rest = own[kk].partition("/")
        dsp, _, why = rest.partition(":")
        rows.append(c2.ObjectStatus(int(kk), c2.ic.ServiceState(local), c2.Disposition(dsp or "NORMAL"), why or None))
    sched = c2.schedule_normal(st3["current"], rows)
    order = [(e["command"], e["step"]) for e in x.log() if e["status"] == "ok"]
    frozen_first = ("divergence", None) in order and all(order.index(("divergence", None)) < i for i, o in
                                                         enumerate(order) if o[1] is not None and o[1] >= PREFIX_STEPS)
    c = div["comparison"]
    ok = (sha256(x.run / "divergence/divergence.json") == fz["files"]["divergence/divergence.json"] and div["ok"]
          and not policy_diffs(nprobe, mine) and own[str(CONTINUING)] == "ACTIONABLE" and mine["proposal"] is not None
          and mine["proposal"]["source"] == "cyclopean_epistemic" and mine["summary"]["fsg6f"]["reason"] == "no_frontier"
          and sched is not None and sched.reason == "retain" and int(sched.target_id) == CONTINUING
          and div["cap"] == (BUDGET - rec["own_looks"]) + 1 == CAP and rec["own_looks"] == 6
          and rec["map"]["surfels"] == 45267 and div["gate_guard"]["calls"] == 0 and frozen_first
          and c["NS1c"]["gate_verdict"] == {"admissible": nprobe["gate"]["admissible"], "reason": nprobe["gate"]["reason"]}
          and nprobe["gate"]["reason"] == "untraceable_final_support" and c["NS1c"]["scheduler"]["target"] ==
          n4["scheduler_decision"]["target_id"] == 123 and c["NS1c2"]["final_gate"] == "NOT CALLED")
    return ok, {"own_status": own[str(CONTINUING)], "scheduler": None if sched is None else [sched.reason,
                                                                                               sched.target_id],
                "cap": div.get("cap"), "frozen_first": frozen_first}


def c18(x):
    chs = x.charts()
    bad = []
    for k, d in x.decisions():
        if not d.get("action"):
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
        cal = x.obs(k) / "observation/acquisition/calibration.json"
        if cal.exists() and cal.read_bytes() != plan:
            bad.append(f"step {k}: executed calibration != planned")
    return not bad, {"problems": bad[:6]}


def c19(x):
    sts = x.states()
    bad = []
    if {k: r["own_looks"] for k, r in sts[0]["entities"].items()} != {str(k): (2 if k == CONTINUING else 1)
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
        if st["executed_actions"] != i or st["new_actions"] != max(0, i - PREFIX_STEPS):
            bad.append(f"{st['label']}: action counts")
    new = [k for k, _d in x.executed() if k >= PREFIX_STEPS]
    if len(new) > CAP:
        bad.append("more new actions than the cap")
    return not bad, {"problems": bad[:6], "new_actions": len(new)}


def c20(x):
    acc = json.loads(Path(AB1D2_ACQ[0]).read_text())["settings"] if sha256(AB1D2_ACQ[0]) == AB1D2_ACQ[1] else None
    bad = []
    for k, _d in x.executed():
        if k < PREFIX_STEPS:
            continue
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
    return not bad, {"problems": bad[:6], "new_steps": [k for k, _ in x.executed() if k >= PREFIX_STEPS]}


def c21(x):
    import check_ns1a as A
    bad, counts = [], {}
    for k, _d in x.executed():
        o = x.obs(k)
        c = json.loads((o / "observation/acquisition/calibration.json").read_text())
        ref = load(o / "observation/oracle_aid/reference-observation.npz")
        prod = load(o / "correspondence/oracle-correspondences.npz")
        own = memo(x, f"oracle-{o}", lambda c=c, ref=ref: A.own_oracle(c, ref))
        idx = prod["left_core_row"].astype(np.int64) * 256 + prod["left_core_col"]
        same = np.array_equal(np.sort(idx), own["keep"]) and np.array_equal(idx, np.sort(idx))
        du = float(np.abs(prod["uv_R"] - own["uv_R"]).max()) if same and len(idx) else (0.0 if same else math.inf)
        keys = sorted(prod) == ["left_core_col", "left_core_row", "uv_L", "uv_R"]
        cls = load(o / "correspondence/core-class-map.npz")["core_class"]
        counts[k] = int(len(idx))
        if not (same and du <= 1e-9 and keys and np.array_equal(cls, own["class"])):
            bad.append(f"step {k}: correspondence (same {same}, du {du})")
        if k >= PREFIX_STEPS:
            rec = x.j(f"{x.sd(k)}/correspondence/correspondence-opened-files.json")
            reads = {x.rel(p) for p in rec["data_reads"]}
            s = x.sd(k)
            if rec["violations"] or reads != {f"{s}/observation/acquisition/calibration.json",
                                              f"{s}/observation/oracle_aid/reference-observation.npz",
                                              f"{s}/freeze/observation-freeze.json"} or rec["modules_loaded"]["cv2"]:
                bad.append(f"step {k}: correspondence guard")
    return not bad, {"problems": bad[:4], "correspondences": counts}


def c22(x):
    import check_ns1a as A
    bad = []
    order = [(e["command"], e["step"]) for e in x.log() if e["status"] == "ok"]
    for k, _d in x.executed():
        o = x.obs(k)
        c = json.loads((o / "observation/acquisition/calibration.json").read_text())
        prod = load(o / "correspondence/oracle-correspondences.npz")
        res = load(o / "geometry/epipolar-result.npz")
        g = memo(x, f"geometry-{o}", lambda c=c, prod=prod: A.own_geometry(c, prod))
        v = np.asarray(res["valid_epi"], bool)
        dp = float(np.abs(g["P"][v] - res["P_epi"][v]).max()) if v.any() else 0.0
        fz = json.loads((o / "freeze/geometry-freeze.json").read_text())
        if dp > 1e-9 or not all(sha256(o / f) == h for f, h in fz["files"].items()):
            bad.append(f"step {k}: geometry (dp {dp})")
        if k >= PREFIX_STEPS:
            rec = x.j(f"{x.sd(k)}/geometry/geometry-opened-files.json")
            mods = rec["modules_loaded"]
            if (rec["violations"] or any(mods[m] for m in ("cv2", "fsg_stereo", "ab1b_oracle", "ab1d3_sgbm",
                                                            "ab1d_match", "fsg6f_frontier"))
                    or rec["position_reads"] or rec["object_index_reads"] or rec["catalog_reads"]
                    or order.index(("freeze-geometry", k)) > order.index(("local-oracle-segmentation", k))):
                bad.append(f"step {k}: geometry guard / order")
    return not bad, {"problems": bad[:4]}


def c23(x):
    bad = []
    for k, _d in x.executed():
        o = x.obs(k)
        prod = load(o / "correspondence/oracle-correspondences.npz")
        res = load(o / "geometry/epipolar-result.npz")
        ref = load(o / "observation/oracle_aid/reference-observation.npz")
        idn = load(o / "segmentation/local-identity.npz")
        uv = prod["uv_L"].astype(np.int64)
        mine = np.where(np.asarray(res["valid_epi"], bool), ref["instance_L"][uv[:, 1], uv[:, 0]], -1) if len(uv) else \
            np.zeros(0, np.int32)
        rec = json.loads((o / "segmentation/segmentation-opened-files.json").read_text())
        marks = [e["label"] for e in rec["events"] if e.get("event") == "mark"]
        if not (np.array_equal(mine, idn["temporary_entity_id"]) and rec["reference_members_read"] == ["instance_L"]
                and marks == ["geometry_freeze_verified", "identity_access_begins"] and not rec["violations"]):
            bad.append(f"step {k}: identity")
    return not bad, {"problems": bad[:4]}


def c24(x):
    import ns1b_core as B
    import ns1c2_core as CORE
    sts = x.states()
    bad, rows, pids = [], {}, set()
    for i, (k, d) in enumerate(x.executed(), start=1):
        s, o = x.sd(k), x.obs(k)
        fu = x.j(f"{s}/fusion/fusion.json")
        t = int(d["action"]["target"])
        prev, after = sts[i - 1], sts[i]
        res = load(o / "geometry/epipolar-result.npz")
        ids = load(o / "segmentation/local-identity.npz")["temporary_entity_id"]
        keep = np.asarray(res["valid_epi"], bool) & (ids == t)
        patch = load(x.run / s / "fusion/target-patch.npz")
        patch_ok = np.array_equal(patch["xyz_h"], np.asarray(res["P_epi"], np.float64)[keep]) and \
            np.all(patch["instance_id"] == t)
        mrec = prev["entities"][str(t)]["map"]
        sm = CORE.load_map(x.res(mrec["path"]))
        want_pid = f"ns1c_step_{k:02d}" if k < PREFIX_STEPS else f"ns1c2_step_{k:02d}"
        p = {"frame": "H0", "patch_id": want_pid, "xyz_h": patch["xyz_h"], "rgb": patch["rgb"],
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
        untouched = all(after["entities"][kk]["map"] == prev["entities"][kk]["map"] for kk in after["entities"]
                        if int(kk) != t)
        new_map_ok = (after["entities"][str(t)]["map"]["path"] == f"run:{s}/fusion/fused-target-map.npz"
                      if fu["action"] == "FUSED" else after["entities"][str(t)]["map"] == mrec)
        pid_ok = fu["patch_id"] == want_pid and fu["patch_id"] not in pids and \
            fu["patch_id"] not in [str(v) for v in m0["patch_ids"]]
        pids.add(fu["patch_id"])
        if not (patch_ok and same and counts and untouched and new_map_ok and pid_ok
                and fu.get("radius_m", RADIUS) == RADIUS and fu.get("hash_cell_m", CELL) == CELL
                and (fu["action"] != "FUSED" or (fu["frame"] == "H0" and fu["replay"]["exact"]
                                                 and fu["replay"]["duplicate_patch"]))
                and np.all(saved["instance_id"] == t) and fu["measured_points"] == int(keep.sum())
                and rec["action"] == fu["action"] and fu["map_before_sha256"] == mrec["sha256"]
                == sha256(x.res(mrec["path"]))):
            bad.append(f"step {k}: fusion (patch {patch_ok}, fuse {same}, counts {counts}, untouched {untouched}, "
                       f"new map {new_map_ok}, pid {pid_ok})")
        rows[k] = {kk: fu[kk] for kk in ("target", "action", "map_before", "measured_points", "matched", "new",
                                          "map_after")}
    return not bad, {"problems": bad[:4], "fusions": rows}


def c25(x):
    import ns1b_core as B
    import ns1c2_core as CORE
    sts = x.states()
    bad = []
    for i, (k, d) in enumerate(x.executed(), start=1):
        s, o = x.sd(k), x.obs(k)
        t = str(d["action"]["target"])
        prev, after = sts[i - 1], sts[i]
        new = after["entities"][t]
        cal1 = json.loads((o / "observation/acquisition/calibration.json").read_text())
        rec1, _m, st1 = B.matcher_state(cal1, load(o / "observation/acquisition/rgb-observation.npz"),
                                        load(o / "observation/oracle_aid/reference-observation.npz"))
        own_st = {**{kk: st1[kk] for kk in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")},
                  "matcher_valid": np.asarray(rec1["valid"], bool)}
        if not arrays_equal(load(x.run / s / "update/controller-state.npz"), own_st):
            bad.append(f"step {k}: controller state does not recompute")
        r = np.asarray(x.charts()[t]["R_HC"], float)
        if not arrays_equal(CORE.evidence_arrays(CORE.rebuild_context(new, x.run, r)), load(x.res(new["evidence"]["path"]))):
            bad.append(f"step {k}: evidence does not recompute from the looks")
        mine = memo(x, probe_key(new, t), lambda new=new, t=t: own_probe(x, new, t))
        saved = probe_file(x, new)
        if policy_diffs(saved["probe"], mine) or new["probe"]["provenance"] != "fresh" or \
                new["probe"]["path"] != f"run:{s}/update/probes/e{int(t):05d}.json" or saved["executed"] is not False:
            bad.append(f"step {k}: target re-probe")
        if new["revision"] != [new["own_looks"], new["map"]["surfels"]] or \
                new["revision"] == prev["entities"][t]["revision"]:
            bad.append(f"step {k}: target revision")
        for kk, rec in after["entities"].items():
            if kk == t:
                continue
            if rec["revision"] == prev["entities"][kk]["revision"] and (
                    rec["probe"]["path"] != prev["entities"][kk]["probe"]["path"] or rec["probe"]["provenance"] != "cached"):
                bad.append(f"step {k}: untouched entity {kk} not served from the cache")
        upd = x.j(f"{s}/update/update.json")
        if upd["north_star_target_points"] != x.j(f"{s}/fusion/fusion.json")["measured_points"] or \
                upd["controller_state_target_support"] != int((np.asarray(rec1["valid"], bool)
                                                               & (np.asarray(rec1["instance_id"]) == int(t))).sum()):
            bad.append(f"step {k}: update record")
    return not bad, {"problems": bad[:6], "steps": len(x.executed())}


def c26(x):
    sts = x.states()
    touched = {str(d["action"]["target"]) for _k, d in x.executed()}
    bad, checked = [], []
    for k in map(str, x.ids()):
        if k in touched:
            continue
        labs = {st["entities"][k]["status"]["label"] for st in sts}
        if len(labs) != 1:
            bad.append(f"{k}: an untouched entity changed state {labs}")
        rec = sts[-1]["entities"][k]
        mine = memo(x, probe_key(rec, k), lambda rec=rec, k=k: own_probe(x, rec, k))
        d = policy_diffs(json.loads((x.run / f"initial-probe/probes/e{int(k):05d}.json").read_text())["probe"], mine)
        if d:
            bad.append(f"{k}: the untouched entity's probe from scratch differs from its initial probe {d[:2]}")
        checked.append(int(k))
        if any(e["object"] == int(k) for st in sts for e in st.get("events", [])):
            bad.append(f"{k}: an event on an untouched entity")
    return not bad, {"problems": bad[:6], "untouched_checked": checked}


def c27(x):
    ex = x.executed()
    new = [(k, d) for k, d in ex if k >= PREFIX_STEPS]
    targets = [int(d["action"]["target"]) for _k, d in new]
    first = next((i for i, (k, d) in enumerate(new) if int(d["action"]["target"]) != CONTINUING
                  and d["kind"] == "attend"), None)
    final = x.has("scene/final-scene-state.json")
    term = x.has("scene/terminal.json")
    bad = []
    later = sorted(int(p.name.split("-")[1]) for p in (x.run / "steps").glob("step-*")) if x.has("steps") else []
    if first is not None:
        k, d = new[first]
        st = x.j(f"scene/state-after-step-{k:02d}.json")
        fz = x.j("freeze/scene-freeze.json") if x.has("freeze/scene-freeze.json") else {"files": {}}
        fin = x.j("scene/final-scene-state.json") if final else {}
        post = (st.get("stop") or {}).get("post_action_probe_of_new_target") or {}
        if (first != len(new) - 1 or not final or term or later[-1] != k or not st["stopped"]
                or st["stop"]["to"] != targets[first] or st["stop"]["from"] != CONTINUING
                or {kk: v for kk, v in fin.items() if kk != "label"} != {kk: v for kk, v in st.items() if kk != "label"}
                or not fz["files"] or any(sha256(x.run / f) != h for f, h in fz["files"].items())
                or post.get("executed") is not False
                or post.get("path") != f"run:{x.sd(k)}/update/probes/e{targets[first]:05d}.json"
                or len(set(targets)) > 2 or any(t != CONTINUING for t in targets[:first])
                or x.j(f"{x.sd(k)}/fusion/fusion.json")["action"] not in ("FUSED", "RETAINED_NOT_FUSED")):
            bad.append("the stop is not exactly after the first executed NORMAL action on a target other than 172")
        if [e for e in x.log() if e["command"] == "schedule" and e["status"] == "ok" and e["step"] > k]:
            bad.append("an action was scheduled after the stop")
    else:
        if final or any(st.get("stopped") for st in x.states()):
            bad.append("a stop is recorded without a cross-entity action")
    return not bad, {"targets": targets, "first_cross_entity_step": None if first is None else new[first][0],
                     "final": final, "terminal": term, "problems": bad}


def code_scan() -> dict:
    hits = []
    for name in PRODUCTION:
        tree = ast.parse((HERE / name).read_text())
        for node in ast.walk(tree):
            ident = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
            if ident in FORBIDDEN_IDENTIFIERS:
                hits.append(f"{name}: {ident}")
            if ident == "probe" and isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and \
                    node.value.id == "B":
                hits.append(f"{name}: ns1b_core.probe (the gated probe)")
            if ident == "final_look_gate_v1" and name != "ns1c2_core.py":
                hits.append(f"{name}: final_look_gate_v1 outside the residue gate")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                                                       else [])
                hits += [f"{name}: import {m}" for m in mods if m.split(".")[-1] in FORBIDDEN_MODULES]
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and CLOSED in node.value:
                hits.append(f"{name}: the closure marker literal")
    core = ast.parse((HERE / "ns1c2_core.py").read_text())
    gate_fns = [n.name for n in ast.walk(core) if isinstance(n, ast.FunctionDef)
                and any(isinstance(a, ast.Attribute) and a.attr == "final_look_gate_v1" for a in ast.walk(n))]
    if gate_fns != ["residue_gate"]:
        hits.append(f"ns1c2_core.py: final_look_gate_v1 referenced by {gate_fns}")
    return {"hits": hits}


def c28(x):
    log = x.log()
    ok_e = ok_entries(x)
    bad = []
    once = [e["command"] for e in ok_e if e["command"] in ONCE]
    if once != ONCE:
        bad.append(f"once stages {once}")
    stage_set = set(STEP) | set(PREFIX_STAGES)
    steps = sorted({e["step"] for e in ok_e if e["command"] in stage_set and e["step"] is not None})
    for k in steps:
        cmds = [e["command"] for e in ok_e if e["command"] in stage_set and e["step"] == k]
        d = x.j(f"{x.sd(k)}/plan/decision.json")
        want = (PREFIX_STAGES if k < PREFIX_STEPS else STEP) if d["kind"] in ("attend", "final_residue") else ["schedule"]
        if cmds != want:
            bad.append(f"step {k}: {cmds}")
    if steps != list(range(len(steps))):
        bad.append(f"steps {steps}")
    drivers = [e["command"] for e in ok_e if e["command"] in DRIVERS]
    if drivers != DRIVERS:
        bad.append(f"drivers {drivers}")
    commits = {e["code"]["commit"] for e in ok_e}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] and not e["dev"] for e in ok_e)
    failed = [e["command"] for e in log if e["status"] == "failed" and e["command"] in ONCE + STEP + PREFIX_STAGES
              + DRIVERS]
    scan = code_scan()
    ok = not bad and len(commits) == 1 and clean and not failed and not scan["hits"]
    return ok, {"problems": bad[:4], "commits": sorted(commits), "clean_pushed": clean, "failed": failed,
                "code_scan": scan["hits"]}


def c29(x):
    bad, truth, hist = [], {}, {}
    for f in guard_files(x):
        rec = x.j(f)
        if rec["violations"]:
            bad.append(f"{f}: violations")
        for e in opens(rec):
            if forbidden(e["path"]):
                bad.append(f"{f}: forbidden read {e['path']}")
            if e.get("kind") == "data-read" and e["path"].endswith(("reference-observation.npz", ".exr")):
                truth.setdefault(f, set()).add(Path(e["path"]).name)
            if e.get("kind") == "data-read" and ("controller-01-full" in e["path"] or
                                                 "controller-02-classroom-replay" in e["path"]):
                hist.setdefault(f, set()).add(Path(e["path"]).name)
    extra = sorted(f for f in truth if not f.endswith(TRUTH_STAGES))
    hist_extra = sorted(f for f in hist if f not in HISTORY_STAGES)
    segs = [x.j(f)["reference_members_read"] for f in guard_files(x) if f.endswith("segmentation-opened-files.json")]
    return not bad and not extra and not hist_extra and all(s == ["instance_L"] for s in segs), {
        "problems": bad[:5], "truth_reads_outside_allowed": extra, "history_reads_outside_known_answer": hist_extra}


def c30(x):
    hits = [str(p.relative_to(x.run)) for p in sorted(x.run.rglob("*.json")) if CLOSED in p.read_text()]
    if (x.vis / "visuals-manifest.json").exists() and CLOSED in (x.vis / "visuals-manifest.json").read_text():
        hits.append("visuals-manifest.json")
    rep = REPO / REPORT_PATH
    rep_bad = []
    if rep.exists():
        t = rep.read_text()
        if NS1C_ACCEPTED_MARKER in t:
            rep_bad.append("NS1c accepted marker in the report")
        if "NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_" + "ACCEPTED" in t:
            rep_bad.append("NS1c2 accepted marker in the report")
    term = x.j("scene/terminal.json") if x.has("scene/terminal.json") else None
    t_ok = term is None or CLOSED not in json.dumps(term)
    man = json.loads((x.vis / "visuals-manifest.json").read_text()) if (x.vis / "visuals-manifest.json").exists() else {}
    outcome_ok = "accepted" not in str(man.get("outcome_reading", "")).lower().replace("not accepted", "")
    return not hits and not rep_bad and t_ok and outcome_ok, {"hits": hits[:5], "report": rep_bad}


def c31(x):
    import ns1c2_visuals as V
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
    lab = all(man["figures"][n]["labels"] == V.LABELS[n] and man["figures"][n]["badges"] == V.BADGES[n] for n in FIGURES)
    must = {"overview.png": ["ACCEPTED HISTORICAL REFERENCE - not an NS1c2 measurement",
                             "NS1c: REVIEWED - NOT ACCEPTED - NOT MERGED", "final_look_gate_v1: RESIDUE only",
                             "ORACLE CORRESPONDENCE", "PHYSICAL HEAD FIXED - POLICY CHART ONLY"],
            "ns1c-vs-ns1c2-divergence.png": ["NS1c: REVIEWED - NOT ACCEPTED - NOT MERGED",
                                             "final_look_gate_v1: RESIDUE only"],
            "controller-phase-timeline.png": ["final_look_gate_v1: RESIDUE only"]}
    lab_must = all(all(m_ in man["figures"][n]["labels"] for m_ in v) for n, v in must.items())
    stmt = man.get("fixed_head_statement") == "PHYSICAL HEAD FIXED - POLICY CHART ONLY" and \
        man.get("frames") == {"chart": "POLICY CHART C_i", "h0": "CANONICAL H0"}
    meta_ok = all(all(man["figures"][n].get(kk) == v for kk, v in metas[n].items()) for n in FIGURES)
    ov = man["figures"]["overview.png"]
    tl = man["figures"]["controller-phase-timeline.png"]
    phases = [st["phase"] for st in x.states()]
    residue_steps = [st["global_step"] for st in x.states() if st["phase"] == "RESIDUE"]
    gates = [k for k, _d in x.decisions() for r in _d.get("residue_gate_records", [])]
    shown = (ov.get("phases_shown") == phases and tl.get("phases_shown") == phases
             and all(p_ == "RESIDUE" for p_ in ov.get("gate_marker_phases", ["?"]) or [])
             and all(g in residue_steps for g in ov.get("gate_markers", [])) and ov.get("gate_markers", []) == tl.get(
                 "gate_markers", []) == [g for g in gates if g in residue_steps]
             and ov.get("divergence_shown") is True and ov.get("historical_reference_shown") is True
             and man["figures"]["ns1c-vs-ns1c2-divergence.png"].get("divergence_shown") is True
             and tl.get("deferred_shown") == DEFERRED
             and ov.get("scheduler_reasons_shown") == [d["scheduler_reason"] for _k, d in x.executed()])
    return same and lab and lab_must and stmt and meta_ok and shown, {
        "regenerated_equal": same, "labels_badges": lab, "required_labels": lab_must, "frame_statement": stmt,
        "meta_equal": meta_ok, "phases_gates_divergence_shown": shown}


def c32(x):
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
    ("02", "accepted sources, NS1a / NS1b handoffs, NS1c replay source and Controller history pinned", c02),
    ("03", "NS1c decision: no NS1c ACCEPTED marker; NS1c not merged; review decision on the base", c03),
    ("04", "COHERENT_SEED_SET by own rule; 10 / 110 / 178 absent from every status, input and target", c04),
    ("05", "one fixed chart per entity: own construction; never recentered; C_172 = NS1b chart", c05),
    ("06", "accepted constants; the live ordinary budget 24; the derived cap 19", c06),
    ("07", "fixed head: every look; planned / executed calibrations = real sensor at the world gaze", c07),
    ("08", "initial state: 172 = NS1b post-action context and map; others = NS1a; no render first", c08),
    ("09", "initial NORMAL probes once, ungated, recomputed, = NS1c's policy part; NS1b reproduced; rotation", c09),
    ("10", "known answers re-run: synthetic + differential, the accepted Controller-02 trace, the residue harness", c10),
    ("11", "NORMAL classification from the probe alone (Cyclopean counts); own deferral; adapter statuses", c11),
    ("12", "every decision = the accepted schedule_normal on own statuses; unchanged proposal; no switch while ACTIONABLE",
     c12),
    ("13", "the adapter re-driven over the recorded probes reproduces every decision, state and event", c13),
    ("14", "gate accounting: final-gate calls in NORMAL = 0 in every stage and probe; gate only in RESIDUE", c14),
    ("15", "ordinary budget: deferral exactly at 24 own looks; never BLOCKED; not gated while NORMAL work remains", c15),
    ("16", "prefix replay: four NS1c actions selected by the corrected decisions; no Blender; all equal to NS1c", c16),
    ("17", "the divergence: frozen first; = NS1c's probe; ACTIONABLE; schedule_normal retains 172; cap 19", c17),
    ("18", "world gazes recomputed (own column form); planned = executed calibration bytes", c18),
    ("19", "own looks / visited: only the target advances; action counts; new actions <= cap", c19),
    ("20", "new observations: one pair per step, 4096 spp, seeds, settings, seal; no re-render", c20),
    ("21", "PERFECT correspondence reproduced by an own oracle for every executed step (prefix included)", c21),
    ("22", "spherical geometry reproduced by own triangulation; truth-free; frozen before identity", c22),
    ("23", "local oracle identity at the exact pixels; only instance_L; after the geometry freeze", c23),
    ("24", "target-only H0 fusion: 12 / 12, own association, idempotent, untouched maps unchanged, patch ids", c24),
    ("25", "update: controller state, evidence and target re-probe recomputed; cache semantics", c25),
    ("26", "reactivation / untouched: unchanged; probes from scratch equal their initial probes", c26),
    ("27", "the stop exactly after the first executed NORMAL action on a target other than 172", c27),
    ("28", "process: stages once per step in order; drivers; one clean pushed commit; code scan", c28),
    ("29", "truth boundary: no catalog / name / evaluation read; truth and history only in declared stages", c29),
    ("30", "terminology: no scene-closure claim; NS1c never accepted; no accepted marker", c30),
    ("31", "figures regenerate byte-identically; NORMAL / RESIDUE shown; gate markers only in RESIDUE; divergence", c31),
    ("32", "run manifest and declared changes", c32),
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
    summary = {"schema": "NS1c2-check-summary-v1", "checks": res, "failed": failed,
               "marker": "NORTH_STAR1C2_CHECKS_PASS" if not failed else "NORTH_STAR1C2_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1C2_CHECKS_PASS")
    if a.corruptions:
        import check_ns1c2_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
