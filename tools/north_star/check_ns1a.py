#!/usr/bin/env python3
"""North Star-1a checker: fail-capable verification of the bootstrap round (read-only).

    .venv/bin/python tools/north_star/check_ns1a.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/north-star/ns1a-perfect-bootstrap-round-contract.md, sections 16-17.  The checker keeps its own literal
pins and constants and recomputes independently: the oracle correspondence (own projection and visibility), the
spherical geometry (own baseline-polar angles, law-of-sines triangulation), the local identity (own pixel lookup), the
persistent seed construction (own loop over the accepted surface-map functions) and the seed-set document.  It audits
every guard record, the freeze order, the process log, the code scope and the figures.  ``--corruptions`` runs the
mutation suite (check_ns1a_corruptions.py) from a passing mirror after an unmodified-mirror null probe.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

PREFIX = "[ns1a-check]"
# ---------------------------------------------------------------- own literal pins and constants
CANONICAL_REMOTE = "visgraf/f3d-vision"
BASE = "dfe16269eb4fcf71ee6a97bab0e8e6126970f1b0"
AB1D3_ACCEPTANCE = "9e0bae487012164921343925b04569111bdc9296"
CONTRACT = "748411c01daaef010905104cf40ed82c917e5f3d"
CONTRACT_PATH = "docs/north-star/ns1a-perfect-bootstrap-round-contract.md"
SHARED = Path("/home/lvelho/rd/f3d-vision/previews")
NB1C_FREEZE = (SHARED / "natural-bootstrap-1c-rgb-candidate-gaze/selection/rgb-gaze-freeze.json",
               "87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37")
NB1C_CANDIDATES = (SHARED / "natural-bootstrap-1c-rgb-candidate-gaze/selection/candidate-gazes.json",
                   "8041b954f7b63d97f060a41aaca5db1ec6e0c2295381523026e98d11f8a5b621")
GAZES = [(1, 164, 513, 76.75, 7.75), (2, 28, 354, -2.75, 75.75), (3, 231, 510, 75.25, -25.75),
         (4, 303, 436, 38.25, -61.75), (5, 110, 719, 179.75, 34.75), (6, 122, 47, -156.25, 28.75)]
RANKS = [g[0] for g in GAZES]
HEAD_SOURCE = (SHARED / "active-bootstrap/ab1a-first-natural-stereo-look/acquisition/calibration.json",
               "9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913")
AB1A_ACQ = (SHARED / "active-bootstrap/ab1a-first-natural-stereo-look/acquisition/acquisition.json",
            "ba316b11edc400b47a4cab467312ecf717551c11b8cb75b27a6fe7c997a16a41")
AB1D2_ACQ = (SHARED / "active-bootstrap/ab1d2-4096spp-observation-quality/observations/gaze-1/acquisition/"
                      "acquisition.json", "7c023b1f382514716893ca1a4d3009a6ae1102e327b3de00312206e3d9f37eff")
ACC_CATALOG = (SHARED / "controller-01-full/bootstrap/instance_catalog.json",
               "be26594254b03fbda7216ac1a942a5c800cf4bdd8f79751a2b8c22d6bfb4c7ae")
C01_SEEDS = (SHARED / "controller-01-full/bootstrap/seeds.json",
             "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f")
BREADTH1 = (SHARED / "breadth-1-classroom-234-spherical-glance/object-stats.json",
            "2f8aa7bee3abf88bd4a93316ad13babd6419f551536d99e71db6b63dce175a02")
AB1B_PRODUCT = (SHARED / "active-bootstrap/ab1b-spherical-epipolar-geometry/oracle/oracle-correspondences.npz",
                "4d26ff328cafb9ff1b9f54e3a1a7309528de87de1e26f41884516d52465e8fc0")
SPP, SEEDS, DEVICE, IPD, VERGENCE, FOCAL = 4096, {"L": 2111, "R": 2112}, "OPTIX", 0.063, 2.10, 128 / math.tan(math.radians(6))
RAW, CORE, ORIGIN = 640, 256, 192
MIN_POINTS, RADIUS, CELL = 100, 0.012, 0.012
PHI_TOL, EPI_RAY_TOL, OWN_GEO_TOL, OWN_UV_TOL = 1e-4, 1e-6, 1e-9, 1e-9
PRODUCT_KEYS = ["left_core_row", "left_core_col", "uv_L", "uv_R"]
REFERENCE_KEYS = ["instance_L", "instance_R", "position_w_L", "position_w_R"]
SOURCE_PINS = {
    "tools/active_bootstrap/ab1b_oracle.py": "51e2ee556a4a3576d00cd99255793212ad5efcb50b1e15ed292740d8c24aa231",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/fsg3_surface_map.py": "1b9dbeb873105ec9bd9aef9680f67ed18db9a7387d6871d6ed8e6ab58bcb1e01",
    "fov3d/reconstruction/surface_map.py": "51e5da5262a74db782930562b2a8026513996e5512a178b05600d770a915f983",
    "fov3d/reconstruction/association.py": "fe8cf0e22f2a0b7d252f9110bf42e07f168c6ba85b341ab9cef20853308ef135",
    "fov3d/_compat.py": "014d1fb8c9cfc4c80fbf015c698e8fc706a16b79a0eda2b916e8727d9e61a870",
    "tools/classroom_oracle1_public.py": "7b85e59a6e397ed69d3eaec8a6b3790639a6c6ffce596fd0d8d1664c738452bb",
    "fov3d/experiments/classroom_oracle/config.py": "8231c7f3b7a1b19108eaeb1fa6294cad0dbcf47f61b12025250e3ef7ac24aa07",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
}
NS1A_FILES = ["tools/north_star/" + n for n in ("ns1a_spec.py", "ns1a_render.py", "ns1a_core.py", "ns1a_run.py",
                                                "ns1a_synthetic.py", "ns1a_visuals.py", "check_ns1a.py",
                                                "check_ns1a_corruptions.py")]
DECLARED = set(NS1A_FILES) | {CONTRACT_PATH, "docs/north-star/ns1a-perfect-bootstrap-round-report.md",
                              "tools/repository/check_repository_layout.py"}
GENERATORS = [n for n in NS1A_FILES if "check_" not in n]
CANONICAL = ["source", "synthetic", "preflight", "acquire", "freeze-observations", "perfect-correspondence",
             "freeze-correspondence", "spherical-geometry", "freeze-geometry", "local-oracle-segmentation",
             "persistent-seed-construction", "freeze-seed-set", "evaluate"]
FORBIDDEN_IMPORTS = {"cv2", "fsg_stereo", "ab1a_stereo", "ab1d_match", "ab1d3_sgbm", "ab1c_planar", "integrated",
                     "controller01", "controller02", "fsg6f_public", "object_policy", "epistemic",
                     "classroom_oracle1_matcher", "multiobject2c_policy"}
FORBIDDEN_IDENTIFIERS = {"StereoSGBM_create", "StereoSGBM", "StereoBM_create", "stereoRectify", "compute_natural",
                         "run_match_gaze", "choose_next", "run_control_loop", "run_controller02", "probe_local_policy",
                         "cyclopean_epistemic", "rectification"}
FORBIDDEN_STRINGS = {"depth_search_z_rect_m"}       # the planar matcher's depth-search interval key
FORBIDDEN_PATHS = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                   "breadth-1-classroom", "controller-01-full", "natural-bootstrap-1b", "range-connectivity/discovery")
BADGES = {"overview.png": ["ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"],
          "bootstrap-progression.png": ["ORACLE INPUT", "DERIVED"], "entity-seeds-3d.png": ["ORACLE INPUT", "DERIVED"]}
LABELS = {"overview.png": ["RGB-ONLY SELECTION", "ORACLE CORRESPONDENCE", "DERIVED SPHERICAL GEOMETRY",
                           "ORACLE SEGMENTATION AID", "UNASSIGNED / NON-CATALOG ORACLE GEOMETRY"],
          "bootstrap-progression.png": ["ORACLE SEGMENTATION AID", "DERIVED SPHERICAL GEOMETRY"],
          "entity-seeds-3d.png": ["ORACLE SEGMENTATION AID", "DERIVED SPHERICAL GEOMETRY"]}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def rd(r: int) -> str:
    return f"rank-{r:02d}"


class X:
    """The run under check, with caches."""

    def __init__(self, run: Path, vis: Path) -> None:
        self.run, self.vis = Path(run), Path(vis)
        self._j, self._n = {}, {}
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

    def rel(self, p: str) -> str:
        for r in self.roots:
            if p == r or p.startswith(r + "/"):
                return p[len(r) + 1:]
        return p

    def log(self) -> list[dict]:
        return [json.loads(ln) for ln in (self.run / "process-log.jsonl").read_text().splitlines() if ln.strip()]

    def cal(self, r: int) -> dict:
        return self.j(f"observations/{rd(r)}/acquisition/calibration.json")

    def ref(self, r: int) -> dict:
        return self.n(f"observations/{rd(r)}/oracle_aid/reference-observation.npz")

    def prod(self, r: int) -> dict:
        return self.n(f"correspondence/{rd(r)}/oracle-correspondences.npz")

    def geo(self, r: int) -> dict:
        return self.n(f"geometry/{rd(r)}/epipolar-result.npz")

    def ids(self, r: int) -> dict:
        return self.n(f"segmentation/{rd(r)}/local-identity.npz")

    def maps(self, rel: str) -> dict:
        out: dict[int, dict] = {}
        for key, v in self.n(rel).items():
            e, f = key.split("_", 1)
            out.setdefault(int(e[1:]), {})[f] = v
        return out


# ---------------------------------------------------------------- own independent implementations
def own_calibration(yaw: float, pitch: float, head: dict) -> dict:
    import fsg_geometry as FG     # the accepted builder is the reference definition of camera construction
    return FG.make_calibration("full", yaw, pitch, VERGENCE, ipd=IPD, head_r_wh=np.asarray(head["head_R_wh"]),
                               head_origin_w=np.asarray(head["head_origin_w_m"]), tangent_frame="baseline_projected")


def cal_bytes(c: dict) -> bytes:
    return (json.dumps(c, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


def own_oracle(c: dict, ref: dict) -> dict:
    """Own oracle: left core Position -> head -> right camera; nearest-pixel same-instance visibility."""
    sl = slice(ORIGIN, ORIGIN + CORE)
    pw = np.asarray(ref["position_w_L"])[sl, sl].reshape(-1, 3).astype(np.float64)
    il = np.asarray(ref["instance_L"])[sl, sl].reshape(-1).astype(np.int64)
    hit = np.isfinite(pw).all(1) & (pw != 0).any(1)
    ph = (np.where(hit[:, None], pw, 0.0) - np.asarray(c["head_origin_w_m"], float)) @ np.asarray(c["head_R_wh"], float)
    e = c["eyes"][1]
    xc = (ph - np.asarray(e["centre_h_m"], float)) @ np.asarray(e["R_hc"], float)
    k = np.asarray(e["K"], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        q = xc @ k.T
        u, v = q[:, 0] / q[:, 2], q[:, 1] / q[:, 2]
    pos = hit & (il > 0)
    proj = pos & np.isfinite(u) & np.isfinite(v) & (xc[:, 2] > 1e-9)
    inside = proj & (u >= 0) & (u <= RAW - 1) & (v >= 0) & (v <= RAW - 1)
    ui = np.rint(np.clip(np.nan_to_num(u), 0, RAW - 1)).astype(int)
    vi = np.rint(np.clip(np.nan_to_num(v), 0, RAW - 1)).astype(int)
    vis = inside & (np.asarray(ref["instance_R"])[vi, ui] == il)
    keep = np.flatnonzero(vis)
    return {"keep": keep, "uv_R": np.stack([u, v], -1)[vis], "counts": {
        "finite": int(hit.sum()), "positive": int(pos.sum()), "projectable": int(proj.sum()),
        "inside": int(inside.sum()), "visible": int(vis.sum()), "id0": int((hit & (il <= 0)).sum())},
        "class": np.where(vis, 3, np.where(pos, 2, np.where(hit, 1, 0))).astype(np.int8).reshape(CORE, CORE)}


def own_geometry(c: dict, prod: dict) -> dict:
    """Own rays (K^-1, R_hc), own baseline-polar angles and law-of-sines triangulation."""
    out = {}
    for s, key in ((0, "uv_L"), (1, "uv_R")):
        e = c["eyes"][s]
        k = np.asarray(e["K"], float)
        uv = np.asarray(prod[key], float)
        a = np.c_[(uv[:, 0] - k[0, 2]) / k[0, 0], (uv[:, 1] - k[1, 2]) / k[1, 1], np.ones(len(uv))]
        d = a @ np.asarray(e["R_hc"], float).T
        out[s] = d / np.linalg.norm(d, axis=1, keepdims=True)
    b = float(c["ipd_m"])
    xh = np.array([1.0, 0.0, 0.0])
    th = {s: np.arctan2(np.linalg.norm(np.cross(xh, out[s]), axis=1), out[s] @ xh) for s in (0, 1)}
    ph = {s: np.angle(-out[s][:, 2] + 1j * out[s][:, 1]) for s in (0, 1)}
    with np.errstate(divide="ignore", invalid="ignore"):
        rl = b * np.sin(th[1]) / np.sin(th[1] - th[0])            # law of sines: |O_L P|
    phb = np.angle(np.exp(1j * ph[0]) + np.exp(1j * ph[1]))
    pl = np.array([-b / 2, 0.0, 0.0]) + rl[:, None] * np.c_[np.cos(th[0]), np.sin(th[0]) * np.sin(phb),
                                                            -np.sin(th[0]) * np.cos(phb)]
    return {"theta_L": th[0], "theta_R": th[1], "phi_L": ph[0], "phi_R": ph[1], "P": pl}


def own_construction(x: X, min_points=MIN_POINTS, radius=RADIUS, cell=CELL, gaze_override=None) -> dict:
    """Own loop over the accepted surface-map functions, from the frozen inputs, in frozen rank order."""
    from fov3d.reconstruction import surface_map as SM
    maps, snaps, hist = {}, {}, []
    for r in RANKS:
        if gaze_override is not None and r in gaze_override:
            xyz, valid, ids, rgb = gaze_override[r]
        else:
            g, idn, prod = x.geo(r), x.ids(r), x.prod(r)
            xyz, valid, ids = g["P_epi"], np.asarray(g["valid_epi"], bool), idn["temporary_entity_id"]
            uv = prod["uv_L"].astype(int)
            rgb = x.n(f"observations/{rd(r)}/acquisition/rgb-observation.npz")["rgb_L"][uv[:, 1], uv[:, 0]].astype(float)
        keep = valid & (ids > 0)
        patch = SM.Patch(f"nb1c_gaze_{r:02d}", np.asarray(xyz, float)[keep], np.asarray(rgb, float)[keep],
                         np.asarray(ids, np.int32)[keep])
        for k in sorted(set(int(i) for i in ids[keep])):
            n = int((keep & (ids == k)).sum())
            if k not in maps:
                if n >= min_points:
                    maps[k] = SM.initialize(patch, k)
                    hist.append((r, k, n, "INITIALIZED"))
                else:
                    hist.append((r, k, n, "SEEN_BUT_NOT_INITIALIZED"))
            elif n >= min_points:
                maps[k], _ = SM.fuse(maps[k], patch, k, radius, cell)
                hist.append((r, k, n, "FUSED"))
            else:
                hist.append((r, k, n, "RETAINED_NOT_FUSED"))
        snaps[r] = {k: arrays(m) for k, m in maps.items()}
    return {"maps": {k: arrays(m) for k, m in maps.items()}, "snaps": snaps, "hist": hist}


def arrays(m) -> dict:
    return {"xyz_h": np.asarray(m.xyz_h, np.float64), "rgb": np.asarray(m.rgb, np.float64),
            "instance_id": np.asarray(m.instance_id), "support_count": np.asarray(m.support_count),
            "provenance_mask": np.asarray(m.provenance_mask), "patch_ids": np.array(list(m.patch_ids), dtype="U64")}


def same_maps(a: dict, b: dict) -> bool:
    if sorted(a) != sorted(b):
        return False
    for k in a:
        if set(a[k]) != set(b[k]):
            return False
        for f in a[k]:
            if a[k][f].dtype != b[k][f].dtype or not np.array_equal(a[k][f], b[k][f]):
                return False
    return True


def popcount(v: np.ndarray) -> np.ndarray:
    return np.array([bin(int(i)).count("1") for i in np.asarray(v, np.uint64)], np.int64)


def guard_files(x: X) -> list[str]:
    return sorted(str(p.relative_to(x.run)) for p in x.run.rglob("*opened-files.json"))


def opens(rec: dict) -> list[dict]:
    return [e for e in rec["events"] if e.get("event") == "open"]


# ---------------------------------------------------------------- the checks
def c01(x):
    origin = git("remote", "get-url", "origin")
    anc = {n: subprocess.run(["git", "merge-base", "--is-ancestor", s, "HEAD"], cwd=REPO).returncode == 0
           for n, s in (("base", BASE), ("ab1d3", AB1D3_ACCEPTANCE), ("contract", CONTRACT))}
    unchanged = subprocess.run(["git", "diff", "--quiet", CONTRACT, "--", CONTRACT_PATH], cwd=REPO).returncode == 0
    contract_added = git("log", "--diff-filter=A", "--format=%H", "--", CONTRACT_PATH).split()[-1:] == [CONTRACT]
    impl = {e["code"]["commit"] for e in x.log() if e["command"] in CANONICAL and e["status"] == "ok"}
    later = all(c != CONTRACT and subprocess.run(["git", "merge-base", "--is-ancestor", CONTRACT, c],
                                                 cwd=REPO).returncode == 0 for c in impl)
    import ns1a_spec as SPm
    spec_ok = SPm.CONTRACT_COMMIT == CONTRACT and SPm.BASE_COMMIT == BASE
    src = x.j("source/source-manifest.json")
    ok = (CANONICAL_REMOTE in origin and all(anc.values()) and unchanged and contract_added and later and spec_ok
          and src["contract_commit"] == CONTRACT and src["contract_unchanged"] and CANONICAL_REMOTE in src["origin"])
    return ok, {"origin": origin, "ancestors": anc, "contract_unchanged": unchanged, "contract_added_at": contract_added,
                "canonical_commits": sorted(impl), "after_contract": later, "spec": spec_ok}


def c02(x):
    now = {p: sha256(REPO / p) for p in SOURCE_PINS}
    bad = sorted(p for p in SOURCE_PINS if now[p] != SOURCE_PINS[p])
    rec = x.j("source/source-manifest.json")["source_pins"]
    return not bad and rec == SOURCE_PINS, {"changed": bad, "record_equal": rec == SOURCE_PINS}


def c03(x):
    fz = json.loads(Path(NB1C_FREEZE[0]).read_text())
    cand = json.loads(Path(NB1C_CANDIDATES[0]).read_text())
    hashes = sha256(NB1C_FREEZE[0]) == NB1C_FREEZE[1] and sha256(NB1C_CANDIDATES[0]) == NB1C_CANDIDATES[1]
    fz_ok = [(g["rank"], g["row"], g["col"]) for g in fz["gazes"]] == [g[:3] for g in GAZES]
    conv = all((-180 + 0.5 * (col + 0.5), 90 - 0.5 * (row + 0.5)) == (yaw, pitch) for _r, row, col, yaw, pitch in GAZES)
    cand_ok = [(g["rank"], g["row"], g["col"], g["yaw_deg"], g["pitch_deg"]) for g in cand["gazes"]] == GAZES
    gl = x.j("source/nb1c-gaze-list.json")["gazes"]
    rec_ok = [(g["rank"], g["row"], g["col"], g["yaw_deg"], g["pitch_deg"]) for g in gl] == GAZES
    rec_ok &= [g["patch_id"] for g in gl] == [f"nb1c_gaze_{r:02d}" for r in RANKS]
    src = x.j("source/source-manifest.json")["nb1c"]
    return hashes and fz_ok and conv and cand_ok and rec_ok and src["freeze"]["sha256"] == NB1C_FREEZE[1], {
        "hashes": hashes, "freeze_order": fz_ok, "convention": conv, "candidates": cand_ok, "gaze_list_record": rec_ok}


def c04(x):
    obs = sorted(p.name for p in (x.run / "observations").iterdir())
    want = sorted([rd(r) for r in RANKS] + ["acquisition-run.json", "evaluation_only"])
    ar = x.j("observations/acquisition-run.json")
    per = []
    for r, _row, _col, yaw, pitch in GAZES:
        a = x.j(f"observations/{rd(r)}/acquisition/acquisition.json")
        per.append(a["nb1c_rank"] == r and list(a["gaze_yaw_pitch_deg"]) == [yaw, pitch]
                   and list(x.cal(r)["gaze_yaw_pitch_deg"]) == [yaw, pitch])
    acq = [e for e in x.log() if e["command"] == "acquire" and e["status"] != "refused"]
    ok = obs == want and ar["ranks_in_order"] == RANKS and [p["rank"] for p in ar["per_rank"]] == RANKS and all(per)
    return ok and len(acq) == 1 and acq[0]["status"] == "ok", {"observations": obs, "ranks": ar["ranks_in_order"],
                                                               "per_rank_gaze": per, "acquire_entries": len(acq)}


def c05(x):
    head_b = Path(HEAD_SOURCE[0]).read_bytes()
    head = json.loads(head_b)
    res = {}
    for r, _row, _col, yaw, pitch in GAZES:
        b = (x.run / f"observations/{rd(r)}/acquisition/calibration.json").read_bytes()
        c = json.loads(b)
        own = cal_bytes(own_calibration(yaw, pitch, head))
        eyes = [e["centre_h_m"] for e in c["eyes"]]
        res[r] = (b == own and b == (x.run / f"plan/{rd(r)}/planned-calibration.json").read_bytes()
                  and c["ipd_m"] == IPD and eyes == [[-IPD / 2, 0.0, 0.0], [IPD / 2, 0.0, 0.0]]
                  and c["prescribed_vergence_distance_m"] == VERGENCE and c.get("tangent_frame") == "baseline_projected"
                  and c["profile"] == "full" and c["image_size_wh"] == [RAW, RAW] and c["core_size"] == CORE
                  and abs(c["eyes"][0]["K"][0][0] - FOCAL) < 1e-9
                  and c["head_R_wh"] == head["head_R_wh"] and c["head_origin_w_m"] == head["head_origin_w_m"])
    r1 = (x.run / "observations/rank-01/acquisition/calibration.json").read_bytes() == head_b
    return all(res.values()) and r1 and sha256(HEAD_SOURCE[0]) == HEAD_SOURCE[1], {"per_rank": res,
                                                                                   "rank1_byte_identical_ab1a": r1}


def c06(x):
    from exr_lite import read_header
    acc = json.loads(Path(AB1D2_ACQ[0]).read_text())["settings"]
    res = {}
    for r in RANKS:
        a = x.j(f"observations/{rd(r)}/acquisition/acquisition.json")
        hdr = {}
        for s in ("L", "R"):
            with open(x.run / f"observations/{rd(r)}/oracle_aid/raw_{s}.exr", "rb") as f:
                v = read_header(f.read(65536))[0].get("cycles.interior.samples")
            hdr[s] = v.decode() if isinstance(v, bytes) else v
        res[r] = (a["spp"] == SPP and a["settings"] == acc and a["settings"]["samples"] == SPP
                  and a["render_seeds_lr"] == SEEDS and a["device"] == DEVICE and not a["settings"]["denoising"]
                  and not a["settings"]["adaptive_sampling"] and a["settings"]["pixel_filter"] == "BOX"
                  and a["settings"]["filter_width"] == 1.0 and hdr == {"L": str(SPP), "R": str(SPP)}
                  and a["canonical"] is True)
    pf = x.j("preflight/preflight.json")
    ar = x.j("observations/acquisition-run.json")
    ok_pf = (pf["rendered"] is False and pf["spp"] == SPP and all(g["ok"] and not g["settings_differences_from_accepted_4096"]
                                                                  for g in pf["gazes"]))
    return all(res.values()) and ok_pf and ar["spp"] == SPP and sha256(AB1D2_ACQ[0]) == AB1D2_ACQ[1], {
        "per_rank": res, "preflight": ok_pf}


def c07(x):
    cvb = np.diag([1.0, -1.0, -1.0])
    m1 = json.loads(Path(AB1A_ACQ[0]).read_text())["camera_matrix_world_lr"]
    res = {}
    for r in RANKS:
        c, a = x.cal(r), x.j(f"observations/{rd(r)}/acquisition/acquisition.json")
        rwh = np.asarray(c["head_R_wh"], float)
        diffs = []
        for e in c["eyes"]:
            m = np.eye(4)
            m[:3, :3] = rwh @ np.asarray(e["R_hc"], float) @ cvb
            m[:3, 3] = np.asarray(c["head_origin_w_m"], float) + np.asarray(e["centre_h_m"], float) @ rwh.T
            diffs.append(float(np.abs(m - np.asarray(a["camera_matrix_world_lr"][e["name"]])).max()))
        res[r] = max(diffs)
    r1 = max(float(np.abs(np.asarray(x.j("observations/rank-01/acquisition/acquisition.json")["camera_matrix_world_lr"][s])
                          - np.asarray(m1[s])).max()) for s in ("L", "R"))
    return max(res.values()) <= 1e-6 and r1 <= 1e-6, {"max_matrix_diff": res, "rank1_vs_ab1a": r1}


def c08(x):
    fz = x.j("freeze/observation-freeze.json")
    bad = [f for f, h in fz["files"].items() if sha256(x.run / f) != h]
    ar = x.j("observations/acquisition-run.json")
    dom, keys, hashes = {}, {}, {}
    for r in RANKS:
        acq = sorted(p.name for p in (x.run / f"observations/{rd(r)}/acquisition").iterdir())
        aid = sorted(p.name for p in (x.run / f"observations/{rd(r)}/oracle_aid").iterdir())
        dom[r] = acq == ["acquisition.json", "calibration.json", "rgb-observation.npz"] and aid == [
            "raw_L.exr", "raw_R.exr", "reference-observation.npz"]
        keys[r] = (sorted(x.n(f"observations/{rd(r)}/acquisition/rgb-observation.npz")) == ["rgb_L", "rgb_R"]
                   and sorted(x.ref(r)) == REFERENCE_KEYS)
        a = x.j(f"observations/{rd(r)}/acquisition/acquisition.json")
        p = ar["per_rank"][r - 1]
        hashes[r] = (a["rgb_observation_sha256"] == sha256(x.run / f"observations/{rd(r)}/acquisition/rgb-observation.npz")
                     == p["rgb_observation_sha256"]
                     and p["reference_observation_sha256"] == sha256(
                         x.run / f"observations/{rd(r)}/oracle_aid/reference-observation.npz"))
    cat_not_frozen = not any("evaluation_only" in f for f in fz["files"])
    n_pf = sum(e["command"] == "preflight" and e["status"] != "refused" for e in x.log())
    return (not bad and all(dom.values()) and all(keys.values()) and all(hashes.values()) and cat_not_frozen
            and n_pf == 1 and fz["spp"] == SPP), {"changed_after_freeze": bad[:5], "domains": dom, "keys": keys,
                                                  "hashes": hashes, "catalog_not_opened_by_freeze": cat_not_frozen}


def c09(x):
    res = {}
    for r in RANKS:
        o = own_oracle(x.cal(r), x.ref(r))
        p = x.prod(r)
        k = p["left_core_row"].astype(np.int64) * CORE + p["left_core_col"]
        same = np.array_equal(k, o["keep"])
        duv = float(np.abs(p["uv_R"] - o["uv_R"]).max()) if same and len(k) else (0.0 if same else math.inf)
        s = x.j(f"correspondence/{rd(r)}/oracle-summary.json")
        att = [a["remaining"] for a in s["attrition"]]
        want = [CORE * CORE, o["counts"]["finite"], o["counts"]["positive"], o["counts"]["projectable"],
                o["counts"]["inside"], o["counts"]["visible"], o["counts"]["visible"]]
        res[r] = {"set": same, "max_uv_R_diff_px": duv, "attrition": att == want,
                  "id0": s["excluded"]["hit_with_instance_0"] == o["counts"]["id0"] == s["instance_0"]["id_0_hits"]}
    ok = all(v["set"] and v["max_uv_R_diff_px"] <= OWN_UV_TOL and v["attrition"] and v["id0"] for v in res.values())
    return ok, res


def c10(x):
    import ab1b_geometry as BG
    res = {}
    for r in RANKS:
        p = x.prod(r)
        ref = x.ref(r)
        try:
            BG.validate_product(p)
            valid = True
        except ValueError:
            valid = False
        uvl = np.c_[p["left_core_col"] + ORIGIN, p["left_core_row"] + ORIGIN].astype(float)
        il = ref["instance_L"][p["left_core_row"] + ORIGIN, p["left_core_col"] + ORIGIN]
        ui = np.rint(p["uv_R"][:, 0]).astype(int) if len(p["uv_R"]) else np.zeros(0, int)
        vi = np.rint(p["uv_R"][:, 1]).astype(int) if len(p["uv_R"]) else np.zeros(0, int)
        inside = bool(((p["uv_R"] >= 0) & (p["uv_R"] <= RAW - 1)).all())
        same = bool(inside and np.all(ref["instance_R"][np.clip(vi, 0, RAW - 1), np.clip(ui, 0, RAW - 1)] == il))
        nonint = float(np.mean(p["uv_R"] != np.rint(p["uv_R"]))) if p["uv_R"].size else 1.0
        res[r] = {"keys": sorted(p) == sorted(PRODUCT_KEYS), "validator": valid, "uv_L_exact": bool(np.array_equal(p["uv_L"], uvl)),
                  "positive_left_ids": bool(np.all(il > 0)), "same_instance": same, "inside_raster": inside,
                  "uv_R_continuous": nonint >= 0.99,
                  "outside_right_nominal_core": int(((p["uv_R"] < ORIGIN) | (p["uv_R"] > ORIGIN + CORE - 1)).any(1).sum())}
    ok = all(all(v for k, v in d.items() if k != "outside_right_nominal_core") for d in res.values())
    return ok, res


def c11(x):
    res = {}
    for r in RANKS:
        rec = x.j(f"correspondence/{rd(r)}/correspondence-opened-files.json")
        reads = sorted(x.rel(p) for p in rec["data_reads"])
        want = sorted([f"observations/{rd(r)}/acquisition/calibration.json",
                       f"observations/{rd(r)}/oracle_aid/reference-observation.npz", "freeze/observation-freeze.json"])
        cls = x.n(f"correspondence/{rd(r)}/core-class-map.npz")["core_class"]
        own = own_oracle(x.cal(r), x.ref(r))["class"]
        res[r] = {"reads": reads == want, "violations": len(rec["violations"]),
                  "modules": not (rec["modules_loaded"]["cv2"] or rec["modules_loaded"]["fsg_stereo"]),
                  "forbidden": rec["forbidden_before_freeze_reads"], "class_map": bool(np.array_equal(cls, own))}
    return all(v["reads"] and not v["violations"] and v["modules"] and not v["forbidden"] and v["class_map"]
               for v in res.values()), res


def code_scan() -> dict:
    out = {}
    for f in GENERATORS:
        src = (REPO / f).read_text()
        tree = ast.parse(src)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[-1] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods |= {node.module.split(".")[-1]} | {a.name for a in node.names}
        idents = set()
        strings = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                idents.add(node.id)
            elif isinstance(node, ast.Attribute):
                idents.add(node.attr)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                idents.add(node.name)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.add(node.value)
        out[f] = {"imports": sorted(mods & FORBIDDEN_IMPORTS),
                  "words": sorted((idents & FORBIDDEN_IDENTIFIERS) | (strings & FORBIDDEN_STRINGS))}
    return out


def c12(x):
    scan = code_scan()
    argv = " ".join(" ".join(e["argv"]) for e in x.log())
    bad_argv = [w for w in ("sgbm", "SGBM", "controller0", "fsg6f", "FSG6f", "cyclopean", "ab1d_match")
                if w in argv]
    return all(not v["imports"] and not v["words"] for v in scan.values()) and not bad_argv, {
        "scan": {k: v for k, v in scan.items() if v["imports"] or v["words"]}, "argv": bad_argv}


def c13(x):
    res = {}
    for r in RANKS:
        rec = x.j(f"geometry/{rd(r)}/geometry-opened-files.json")
        reads = sorted(x.rel(p) for p in rec["data_reads"])
        want = sorted([f"observations/{rd(r)}/acquisition/calibration.json",
                       f"correspondence/{rd(r)}/oracle-correspondences.npz"])
        refs = [x.rel(e["path"]) for e in opens(rec) if "oracle_aid" in e["path"] or "evaluation_only" in e["path"]
                or e["path"].endswith(".exr")]
        res[r] = {"reads": reads == want, "violations": len(rec["violations"]), "truth_opens": refs,
                  "counts": [rec["position_reads"], rec["object_index_reads"], rec["catalog_reads"]],
                  "modules": [m for m in ("cv2", "fsg_stereo", "ab1b_oracle") if rec["modules_loaded"][m]]}
    return all(v["reads"] and not v["violations"] and not v["truth_opens"] and v["counts"] == [0, 0, 0]
               and not v["modules"] for v in res.values()), res


def c14(x):
    res = {}
    for r in RANKS:
        p, g = x.prod(r), x.geo(r)
        if not len(p["uv_L"]):
            res[r] = {"pairs": 0, "ok": int(np.asarray(g["P_epi"]).size) == 0}
            continue
        o = own_geometry(x.cal(r), p)
        v = np.asarray(g["valid_epi"], bool)
        dp = float(np.abs(g["P_epi"][v] - o["P"][v]).max())
        dth = float(max(np.abs(g["theta_L"] - o["theta_L"]).max(), np.abs(g["theta_R"] - o["theta_R"]).max()))
        dph = float(np.abs(np.angle(np.exp(1j * (g["phi_L"] - o["phi_L"])))).max())
        phi_res = float(np.abs(np.angle(np.exp(1j * (o["phi_R"] - o["phi_L"])))).max())
        er = float(np.nanmax(np.linalg.norm(g["P_epi"] - g["P_ray"], axis=1)[v & np.asarray(g["valid_ray"], bool)]))
        dtp = bool(np.all(o["theta_R"] - o["theta_L"] > 0))
        res[r] = {"pairs": int(len(v)), "valid": int(v.sum()), "own_P_max_diff_m": dp, "theta_diff": dth,
                  "phi_diff": dph, "phi_residual_max": phi_res, "epi_ray_max_m": er, "delta_theta_positive": dtp,
                  "ok": bool(v.all() and dp <= OWN_GEO_TOL and dth <= 1e-12 and dph <= 1e-12 and phi_res <= PHI_TOL
                             and er <= EPI_RAY_TOL and dtp)}
    return all(v["ok"] for v in res.values()), res


def c15(x):
    out = {}
    for f in ("observation", "correspondence", "geometry", "seed-set"):
        fz = x.j(f"freeze/{f}-freeze.json")
        out[f] = [k for k, h in fz["files"].items() if sha256(x.run / k) != h]
    cfz = x.j("freeze/correspondence-freeze.json")["files"]
    inputs_ok = all(x.j(f"geometry/{rd(r)}/geometry-summary.json")["inputs"]["correspondences"]["sha256"]
                    == cfz[f"correspondence/{rd(r)}/oracle-correspondences.npz"] for r in RANKS)
    gfz = x.j("freeze/geometry-freeze.json")
    chain = gfz["correspondence_freeze_sha256"] == sha256(x.run / "freeze/correspondence-freeze.json")
    order = [e["command"] for e in x.log() if e["command"] in CANONICAL and e["status"] == "ok"]
    seq = order == CANONICAL
    seg = x.j("segmentation/segmentation-opened-files.json")
    ev = seg["events"]
    marks = [i for i, e in enumerate(ev) if e.get("event") == "mark"]
    labels = [ev[i]["label"] for i in marks]
    first_ref = min([i for i, e in enumerate(ev) if e.get("event") == "open" and "oracle_aid" in e["path"]], default=-1)
    seg_order = labels == ["geometry_freeze_verified", "identity_access_begins"] and first_ref > marks[-1]
    return (not any(out.values()) and inputs_ok and chain and seq and seg_order), {
        "changed_after_freeze": {k: v[:3] for k, v in out.items()}, "geometry_inputs_frozen": inputs_ok,
        "freeze_chain": chain, "stage_order": seq, "identity_after_geometry_freeze": seg_order}


def c16(x):
    rec = x.j("segmentation/segmentation-opened-files.json")
    allowed = set()
    for r in RANKS:
        allowed |= {f"geometry/{rd(r)}/{n}" for n in ("left-core-rays.npz", "epipolar-result.npz",
                                                      "geometry-summary.json", "geometry-opened-files.json")}
        allowed |= {f"correspondence/{rd(r)}/oracle-correspondences.npz",
                    f"observations/{rd(r)}/oracle_aid/reference-observation.npz"}
    allowed.add("freeze/geometry-freeze.json")
    reads = {x.rel(p) for p in rec["data_reads"]}
    members = rec["reference_members_read"]
    forb = [x.rel(e["path"]) for e in opens(rec) if any(t in e["path"] for t in FORBIDDEN_PATHS)]
    return (reads <= allowed and not rec["violations"] and not forb and not rec["forbidden_before_freeze_reads"]
            and members == {str(r): ["instance_L"] for r in RANKS}
            and all(x.j(f"segmentation/{rd(r)}/identity-summary.json")["reference_members_read"] == ["instance_L"]
                    for r in RANKS)), {"unexpected_reads": sorted(reads - allowed), "members": members,
                                       "forbidden_opens": forb, "violations": len(rec["violations"])}


def c17(x):
    res = {}
    for r in RANKS:
        p, idn, g = x.prod(r), x.ids(r), x.geo(r)
        il = x.ref(r)["instance_L"]
        own = il[p["left_core_row"] + ORIGIN, p["left_core_col"] + ORIGIN].astype(np.int32)
        v = np.asarray(g["valid_epi"], bool)
        want = np.where(v, own, -1)
        res[r] = {"equal": bool(np.array_equal(idn["temporary_entity_id"], want)),
                  "aligned": bool(np.array_equal(idn["left_core_row"], p["left_core_row"])
                                  and np.array_equal(idn["left_core_col"], p["left_core_col"])
                                  and np.array_equal(idn["valid"], v)),
                  "positive": bool(np.all(idn["temporary_entity_id"][v] > 0))}
    return all(all(d.values()) for d in res.values()), res


def c18(x):
    import ns1a_spec as SPm
    from fov3d.experiments.classroom_oracle import config as public
    src = x.j("source/source-manifest.json")["accepted_constants"]
    doc = x.j("seeds/seed-set.json")["persistence"]
    lit = (REPO / "tools/fsg3_surface_map.py").read_text().count("len(q.xyz_h) < 100") == 2
    pids = set()
    for m in x.maps("seeds/entity-maps.npz").values():
        pids |= set(str(p) for p in m["patch_ids"])
    ok = (public.MIN_INITIAL_TARGET_POINTS == MIN_POINTS and public.FUSION == {"association_radius_m": RADIUS,
                                                                               "hash_cell_m": CELL}
          and src["MIN_INITIAL_TARGET_POINTS"] == MIN_POINTS and src["FUSION"] == public.FUSION and lit
          and SPm.MIN_INITIAL_TARGET_POINTS == MIN_POINTS and SPm.ASSOCIATION_RADIUS_M == RADIUS
          and SPm.HASH_CELL_M == CELL and doc["min_points"] == MIN_POINTS and doc["association_radius_m"] == RADIUS
          and doc["hash_cell_m"] == CELL and pids <= {f"nb1c_gaze_{r:02d}" for r in RANKS})
    return ok, {"source_record": src, "document": {k: doc[k] for k in ("min_points", "association_radius_m",
                                                                      "hash_cell_m")}, "patch_ids": sorted(pids)}


def c19(x):
    own = x._own if hasattr(x, "_own") else own_construction(x)
    x._own = own
    final = same_maps(own["maps"], x.maps("seeds/entity-maps.npz"))
    snaps = all(same_maps(own["snaps"][r], x.maps(f"seeds/snapshot-after-{rd(r)}.npz")) for r in RANKS)
    hist = [(e["rank"], e["entity"], e["points"], e["action"]) for e in x.j("seeds/construction-history.json")["history"]]
    return final and snaps and hist == own["hist"], {"final_maps_equal": final, "snapshots_equal": snaps,
                                                      "history_equal": hist == own["hist"], "events": len(hist)}


def c20(x):
    hist = x.j("seeds/construction-history.json")["history"]
    bad, by = [], {}
    for e in hist:
        by.setdefault(e["entity"], []).append(e)
    for k, evs in by.items():
        if k <= 0:
            bad.append((k, "non-positive entity"))
        init = None
        for e in evs:
            if init is None:
                want = "INITIALIZED" if e["points"] >= MIN_POINTS else "SEEN_BUT_NOT_INITIALIZED"
                init = e["rank"] if want == "INITIALIZED" else None
            else:
                want = "FUSED" if e["points"] >= MIN_POINTS else "RETAINED_NOT_FUSED"
            if e["action"] != want:
                bad.append((k, e["rank"], e["action"], want))
    maps = x.maps("seeds/entity-maps.npz")
    for k, evs in by.items():
        contrib = [f"nb1c_gaze_{e['rank']:02d}" for e in evs if e["action"] in ("INITIALIZED", "FUSED")]
        have = [str(p) for p in maps[k]["patch_ids"]] if k in maps else []
        if contrib != have:
            bad.append((k, "patch ids", contrib, have))
    if set(maps) - set(by) or any(k <= 0 for k in maps):
        bad.append(("maps without history or non-positive", sorted(maps)))
    return not bad, {"violations": bad[:6], "entities": len(by)}


def c21(x):
    from fov3d.reconstruction import surface_map as SM
    hist = x.j("seeds/construction-history.json")["history"]
    rec = all(e["replay"]["exact"] and e["replay"]["allclose_1e-10"] and e["replay"]["duplicate_patch"]
              for e in hist if e["action"] == "FUSED")
    maps = x.maps("seeds/entity-maps.npz")
    bad = []
    for k, m in maps.items():
        sm = SM.SurfaceMap(m["xyz_h"].copy(), m["rgb"].copy(), m["instance_id"].copy(), m["support_count"].copy(),
                           m["provenance_mask"].copy(), [str(p) for p in m["patch_ids"]])
        for pid in sm.patch_ids:
            r = int(pid[-2:])
            g, idn = x.geo(r), x.ids(r)
            keep = np.asarray(g["valid_epi"], bool) & (idn["temporary_entity_id"] == k)
            patch = SM.Patch(pid, g["P_epi"][keep], np.zeros((int(keep.sum()), 3)), idn["temporary_entity_id"][keep])
            out, meta = SM.fuse(sm, patch, k, RADIUS, CELL)
            if not (meta["duplicate_patch"] and same_maps({0: arrays(out)}, {0: arrays(sm)})):
                bad.append((k, pid))
    return rec and not bad, {"recorded_replays_exact": rec, "non_idempotent": bad[:5]}


def c22(x):
    maps = x.maps("seeds/entity-maps.npz")
    hist = x.j("seeds/construction-history.json")["history"]
    bad = []
    for k, m in maps.items():
        if not np.all(m["instance_id"] == k):
            bad.append((k, "foreign id"))
        if not np.array_equal(popcount(m["provenance_mask"]), m["support_count"].astype(np.int64)):
            bad.append((k, "support != provenance"))
        evs = [e for e in hist if e["entity"] == k]
        size = sum(e["map_after"] - e["map_before"] for e in evs)
        if size != len(m["xyz_h"]):
            bad.append((k, "size history", size, len(m["xyz_h"])))
        for e in evs:
            if e["action"] == "FUSED" and e["new"] != e["map_after"] - e["map_before"]:
                bad.append((k, "new != growth"))
    return not bad, {"violations": bad[:6], "maps": len(maps)}


def own_document(x) -> dict:
    hist = x.j("seeds/construction-history.json")["history"]
    maps = x.maps("seeds/entity-maps.npz")
    by = {}
    for e in hist:
        by.setdefault(e["entity"], []).append(e)
    ents = []
    for k in sorted(by):
        evs = by[k]
        init = [e for e in evs if e["action"] == "INITIALIZED"]
        m = maps.get(k)
        ents.append({"temporary_entity_id": k, "first_seen_rank": evs[0]["rank"],
                     "gaze_ranks_seen": [e["rank"] for e in evs],
                     "points_per_gaze": {str(r): next((e["points"] for e in evs if e["rank"] == r), 0) for r in RANKS},
                     "initialized": bool(init), "initialized_at_rank": init[0]["rank"] if init else None,
                     "initial_point_count": init[0]["points"] if init else None,
                     "map_size_after_contributing_gaze": {str(e["rank"]): e["map_after"] for e in evs
                                                          if e["action"] in ("INITIALIZED", "FUSED")},
                     "final_surfels": 0 if m is None else len(m["xyz_h"]),
                     "contributing_patches": 0 if m is None else len(m["patch_ids"]),
                     "total_raw_measured_points": sum(e["points"] for e in evs)})
    return {"entities": ents, "initialized": sum(e["initialized"] for e in ents)}


def c23(x):
    doc = x.j("seeds/seed-set.json")
    own = own_document(x)
    fields = ["temporary_entity_id", "first_seen_rank", "gaze_ranks_seen", "points_per_gaze", "initialized",
              "initialized_at_rank", "initial_point_count", "map_size_after_contributing_gaze", "final_surfels",
              "contributing_patches", "total_raw_measured_points"]
    got = [{f: e[f] for f in fields} for e in doc["entities"]]
    counts = (doc["counts"]["initialized"] == own["initialized"]
              and doc["counts"]["observed_positive_entities"] == len(own["entities"])
              and doc["counts"]["seen_but_not_initialized"] == len(own["entities"]) - own["initialized"])
    un = all(doc["unassigned_instance_0"]["per_rank"][str(r)]["id_0_hits"]
             == x.j(f"correspondence/{rd(r)}/oracle-summary.json")["excluded"]["hit_with_instance_0"] for r in RANKS)
    names = set(json.loads(Path(ACC_CATALOG[0]).read_text())["instances"][i]["object_name"]
                for i in range(len(json.loads(Path(ACC_CATALOG[0]).read_text())["instances"])))
    leaks = []
    for p in x.run.rglob("*.json"):
        rel = str(p.relative_to(x.run))
        if rel.startswith(("evaluation/", "observations/evaluation_only/")) or rel in ("manifest.json", "check-summary.json"):
            continue
        txt = p.read_text()
        if '"object_name"' in txt:
            leaks.append(rel)
            continue
        strings = set()

        def walk(o):
            if isinstance(o, str):
                strings.add(o)
            elif isinstance(o, dict):
                for kk, v in o.items():
                    strings.add(kk)
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(txt))
        if strings & names:
            leaks.append((rel, sorted(strings & names)[:3]))
    return got == own["entities"] and counts and un and not leaks, {"entities_equal": got == own["entities"],
                                                                    "counts": counts, "unassigned": un,
                                                                    "name_leaks": leaks[:5]}


def c24(x):
    fz = x.j("freeze/seed-set-freeze.json")
    must = {f"seeds/{n}" for n in ("entity-maps.npz", "construction-history.json", "seed-set.json")}
    must |= {f"segmentation/{rd(r)}/local-identity.npz" for r in RANKS}
    must |= {f"geometry/{rd(r)}/epipolar-result.npz" for r in RANKS}
    rec = x.j("seeds/seeds-opened-files.json")
    clean = not rec["violations"] and not rec["forbidden_before_freeze_reads"] and not [
        e for e in opens(rec) if any(t in e["path"] for t in FORBIDDEN_PATHS)]
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    before = order.index("freeze-seed-set") < order.index("evaluate") if "evaluate" in order else False
    return must <= set(fz["files"]) and clean and before, {"missing": sorted(must - set(fz["files"])),
                                                           "seed_guard_clean": clean, "before_evaluate": before}


def c25(x):
    rec = x.j("evaluation/evaluation-opened-files.json")
    ev = rec["events"]
    marks = [(i, e["label"]) for i, e in enumerate(ev) if e.get("event") == "mark"]
    labels = [m[1] for m in marks]
    begin = next((i for i, l in marks if l == "reference_access_begins"), None)
    ref_open = [i for i, e in enumerate(ev) if e.get("event") == "open" and any(
        t in e["path"] for t in ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json",
                                 "ab1b-spherical", "reference-observation.npz"))]
    writes = {x.rel(p) for p in rec["writes"]}
    ok = (labels == ["seed_freeze_verified", "reference_access_begins", "seed_freeze_reverified"] and begin is not None
          and all(i > begin for i in ref_open) and not rec["violations"] and all(w.startswith("evaluation/") for w in writes))
    return ok, {"marks": labels, "reference_opens": len(ref_open), "violations": len(rec["violations"]),
                "writes": sorted(writes)}


def c26(x):
    bad = {}
    for f in guard_files(x):
        if f.startswith("evaluation/"):
            continue
        rec = x.j(f)
        hits = [x.rel(e["path"]) for e in opens(rec) if any(t in e["path"] for t in FORBIDDEN_PATHS)]
        if hits or rec["violations"] or rec.get("forbidden_before_freeze_reads"):
            bad[f] = {"forbidden": hits[:3], "violations": len(rec["violations"])}
    return not bad and len(guard_files(x)) >= 19, {"guard_records": len(guard_files(x)), "problems": bad}


def c27(x):
    ev = x.j("evaluation/evaluation.json")
    cat = {int(e["instance_id"]): e["object_name"] for e in x.j("observations/evaluation_only/instance-catalog.json")["instances"]}
    acc = {int(e["instance_id"]): e["object_name"] for e in json.loads(Path(ACC_CATALOG[0]).read_text())["instances"]}
    b1 = json.loads(Path(BREADTH1[0]).read_text())["objects"]
    vis = {int(o["instance_id"]) for o in b1 if o["status"] == "VISIBLE_AT_0P5_DEG"}
    loc = sorted(int(s["instance_id"]) for s in json.loads(Path(C01_SEEDS[0]).read_text())["instances"])
    doc = x.j("seeds/seed-set.json")
    obs = [e["temporary_entity_id"] for e in doc["entities"]]
    init = [e["temporary_entity_id"] for e in doc["entities"] if e["initialized"]]
    seal = x.j("observations/acquisition-run.json")["catalog_seal"]["sha256"] == sha256(
        x.run / "observations/evaluation_only/instance-catalog.json")
    pins = all(sha256(p) == h for p, h in (ACC_CATALOG, C01_SEEDS, BREADTH1, AB1B_PRODUCT))
    import fsg_geometry as FG
    cons = {}
    for r in RANKS:
        p, g = x.prod(r), x.geo(r)
        pw = x.ref(r)["position_w_L"][p["left_core_row"] + ORIGIN, p["left_core_col"] + ORIGIN].astype(float)
        e = np.linalg.norm(g["P_epi"] - FG.world_to_head(x.cal(r), pw), axis=1)[np.asarray(g["valid_epi"], bool)]
        rec = ev["per_rank"][str(r)]["oracle_consistency"]["error_m"]
        cons[r] = (rec is None and e.size == 0) or (rec is not None and abs(rec["median"] - float(np.median(e))) < 1e-12
                                                    and abs(rec["max"] - float(e.max())) < 1e-12)
    want = {"touched_fraction_observed": len(set(obs) & vis) / len(vis),
            "touched_fraction_initialized": len(set(init) & vis) / len(vis)}
    ok = (seal and pins and ev["catalog"]["equal_to_accepted_controller01"] == (cat == acc) and cat == acc
          and all(ev["breadth1"][k] == v for k, v in want.items())
          and ev["controller01"]["observed_and_localized"] == sorted(set(obs) & set(loc))
          and ev["controller01"]["initialized_and_localized"] == sorted(set(init) & set(loc))
          and [t["post_freeze_name"] for t in ev["entities"]] == [cat.get(k) for k in obs]
          and ev["counts"]["initialized"] == len(init) and ev["counts"]["unique_positive_entities_observed"] == len(obs)
          and all(cons.values()))
    return ok, {"seal": seal, "pins": pins, "catalog_equal_accepted": cat == acc, "oracle_consistency": cons,
                "breadth1": want}


def c28(x):
    fz = x.j("freeze/seed-set-freeze.json")
    bad = [f for f, h in fz["files"].items() if sha256(x.run / f) != h]
    ev = x.j("evaluation/evaluation.json")
    doc = x.j("seeds/seed-set.json")
    same = [(t["temporary_entity_id"], t["initialized_at_rank"], t["final_surfels"]) for t in ev["entities"]] == [
        (e["temporary_entity_id"], e["initialized_at_rank"], e["final_surfels"]) for e in doc["entities"]]
    return not bad and same, {"changed_after_freeze": bad[:5], "evaluation_matches_seed_set": same}


def c29(x):
    log = x.log()
    refused = [e["command"] for e in log if e["status"] == "refused"]       # nothing ran; reported, allowed
    canon = [e for e in log if e["command"] in CANONICAL and e["status"] != "refused"]
    once = all(sum(e["command"] == c and e["status"] == "ok" for e in canon) == 1 for c in CANONICAL)
    no_fail = all(e["status"] == "ok" for e in canon)
    order = [e["command"] for e in canon] == CANONICAL
    commits = {e["code"]["commit"] for e in canon}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] and not e["dev"] for e in canon)
    scripts = all(any(a.endswith("tools/north_star/ns1a_run.py") for a in e["argv"][:1]) for e in log)
    vis = all(e["command"] == "visualize" for e in log if e["command"] not in CANONICAL and e["status"] != "refused")
    return once and no_fail and order and len(commits) == 1 and clean and scripts and vis, {
        "once": once, "no_failed_canonical": no_fail, "order": order, "commits": sorted(commits), "clean": clean,
        "refused_entries": refused,
        "only_ns1a_run": scripts, "others_visualize": vis}


def c30(x):
    head = json.loads(Path(HEAD_SOURCE[0]).read_text())
    heads = all(x.cal(r)["head_R_wh"] == head["head_R_wh"] and x.cal(r)["head_origin_w_m"] == head["head_origin_w_m"]
                for r in RANKS)
    seven = not any((x.run / f"observations/rank-{r:02d}").exists() for r in range(7, 13))
    mods = {}
    for f in guard_files(x):
        rec = x.j(f)
        loaded = [m for m, v in rec.get("modules_loaded", {}).items()
                  if v and not (m == "ab1b_oracle" and f.startswith("correspondence/"))]
        if loaded:
            mods[f] = loaded
    argv = " ".join(" ".join(e["argv"]) for e in x.log())
    words = [w for w in ("controller01", "controller02", "fsg6f", "cyclopean", "sgbm", "integrated") if w in argv.lower()]
    return heads and seven and not mods and not words, {"fixed_head": heads, "no_seventh": seven,
                                                        "forbidden_modules_loaded": mods, "argv_words": words}


def c31(x):
    rep = x.j("synthetic/synthetic-report.json")
    names = [c["case"][:2] for c in rep["cases"]]
    need = {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "12", "13", "14", "15", "16", "17"}
    order = [e["command"] for e in x.log() if e["status"] == "ok"]
    first = order.index("synthetic") < order.index("preflight") < order.index("acquire")
    return (rep["marker"] == "NS1A_SYNTHETIC_PASS" and not rep["failed"] and all(c["pass"] for c in rep["cases"])
            and need <= set(names) and first), {"passed": len(rep["passed"]), "failed": rep["failed"],
                                                "before_render": first}


def c32(x):
    import ns1a_visuals as V
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    figs, _ = V.render_all(x.run)
    res = {}
    for name, (img, meta) in figs.items():
        b = io.BytesIO()
        img.save(b, format="PNG", optimize=False)
        res[name] = (hashlib.sha256(b.getvalue()).hexdigest() == sha256(x.vis / name) == man["figures"][name]["sha256"]
                     and meta["panels"] == man["figures"][name]["panels"])
    return all(res.values()) and sorted(res) == sorted(BADGES), res


def c33(x):
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    f = man["figures"]
    badges = all(f[n]["badges"] == BADGES[n] for n in BADGES)
    labels = all(f[n]["labels"] == LABELS[n] for n in LABELS)
    order = (man["frozen_gaze_order"] == RANKS and all(f["overview.png"]["panels"][p] == RANKS for p in "ABC")
             and f["bootstrap-progression.png"]["panels"]["columns"] == RANKS)
    hidden = "never hidden" in man["displays"]["no_hit"] and "UNASSIGNED" in man["displays"]["instance_0"]
    return badges and labels and order and hidden, {"badges": badges, "labels": labels, "gaze_order": order,
                                                    "never_hidden": hidden}


def c34(x):
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
    ("01", "provenance: canonical repo, base, AB1d3 acceptance, contract first and unchanged", c01),
    ("02", "accepted sources pinned and unchanged", c02),
    ("03", "the accepted NB1c freeze: exact six gazes in frozen order", c03),
    ("04", "selection executed: exactly six gazes, frozen order, no replacement, no seventh, one acquisition", c04),
    ("05", "calibrations: accepted construction, fixed AB1a head, IPD, vergence, rank 1 byte-identical to AB1a", c05),
    ("06", "observation quality: 4096 spp (record, readback, EXR header), seeds, OPTIX, no denoise / adaptive, BOX", c06),
    ("07", "camera geometry: own eye matrices; rank 1 equal to the AB1a record", c07),
    ("08", "observation freeze, product domains, no rerender", c08),
    ("09", "PERFECT matcher: own oracle reproduces every product and its attrition", c09),
    ("10", "truth-stripped schema, raw left core, full padded right raster, continuous uv_R, same instance", c10),
    ("11", "oracle guard records and the oracle-aid class map", c11),
    ("12", "no SGBM / rectification / depth bound / natural matcher / controller in the NS1a code or commands", c12),
    ("13", "geometry guard records: truth-free (calibration + frozen product only)", c13),
    ("14", "spherical geometry reproduced independently (theta from +X, phi = atan2(dy, -dz), ray-ray)", c14),
    ("15", "freezes verify; geometry from the frozen product; identity attached after the geometry freeze", c15),
    ("16", "oracle segmentation aid: only instance_L read; no catalog; no forbidden read", c16),
    ("17", "local ids reproduced at the exact left raw-core pixels; positive only", c17),
    ("18", "persistent-map constants pinned (100 points, 0.012 m radius, 0.012 m cell) and patch ids", c18),
    ("19", "seed construction replayed independently from the frozen inputs: maps, snapshots, history", c19),
    ("20", "initialization and undersupported-fusion rules", c20),
    ("21", "fusion idempotence: recorded and replayed for every map and patch", c21),
    ("22", "no cross-id fusion; support / provenance and size bookkeeping", c22),
    ("23", "seed-set document recomputed; instance-0 record; no names before the freeze", c23),
    ("24", "seed-set freeze before evaluation; seed guard clean", c24),
    ("25", "evaluation: reference access only after the seed freeze verified; writes only evaluation/", c25),
    ("26", "no pre-freeze stage opened the catalog, seeds, Breadth-1 or any forbidden path", c26),
    ("27", "evaluation numbers recomputed (catalog seal, names, Breadth-1, Controller-01, oracle consistency)", c27),
    ("28", "evaluation changed nothing (seed freeze verifies now)", c28),
    ("29", "process: each canonical stage once, in order, one clean pushed commit, no dev entry", c29),
    ("30", "no controller / FSG6f / Cyclopean / SGBM / head motion / seventh gaze", c30),
    ("31", "synthetic known answers passed before the render", c31),
    ("32", "figures regenerate byte-identically", c32),
    ("33", "badges, labels, gaze order, never-hidden displays", c33),
    ("34", "run manifest and declared changes", c34),
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
    a = ap.parse_args(argv)
    res = run_checks(a.run, a.visuals)
    failed = [k for k, v in res.items() if not v["pass"]]
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(failed)}")
    summary = {"schema": "NS1a-check-summary-v1", "checks": res, "failed": failed,
               "marker": "NORTH_STAR1A_CHECKS_PASS" if not failed else "NORTH_STAR1A_CHECKS_FAIL"}
    if not failed:
        print(f"{PREFIX} NORTH_STAR1A_CHECKS_PASS")
    if a.corruptions:
        import check_ns1a_corruptions as CC
        summary["corruptions"] = CC.run_suite(a.run, a.visuals, baseline_failed=failed)
    if a.write_summary:
        (a.run / "check-summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + "\n")
    bad = failed or (a.corruptions and (summary["corruptions"]["missed"]
                                        or not summary["corruptions"]["run_unchanged_by_suite"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
