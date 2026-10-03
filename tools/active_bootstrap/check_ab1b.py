"""Active Bootstrap-1b: fail-capable checks of gaze-centered spherical epipolar geometry on the saved AB1a pair.

    .venv/bin/python tools/active_bootstrap/check_ab1b.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md, sections 19-20 (checks 1-46).  The checker
keeps its own literal constants and recomputes independently of the generator:
- the AB1a source identities (pins, the AB1a manifest and measurement freeze, the AB1a process log);
- the raw-core rays (its own K^-1 and R_hc), theta (|b x d| / b . d), phi (complex argument), the wrap (complex
  exponential), the display chart;
- the oracle (its own world-to-head, projection, nearest-pixel and same-instance rule on the raw rasters);
- the epipolar triangulation (law of sines), the ray-ray triangulation (Cramer's rule with cross products), the gap
  (line-line distance), the conditioning (gamma by atan2);
- the truth firewall (guard records, ordered events, static audits), the freezes and the run order;
- the post-freeze evaluation (P_truth, errors, reprojection, the AB1a comparison) and the figures (byte-identical).

``--corruptions`` plants defects in throwaway mirrors (JSON copied, other files linked; edited arrays rewritten), as
regenerations with a deliberately wrong generator function, or as in-process overrides.  They count only when the
uncorrupted baseline passes.  ``--write-summary`` writes only ``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
from functools import cached_property
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOLS = REPO / "tools"
PREFIX = "[ab1b-check]"

# ---- literal copies (contract sections 2-14); deliberately not imported from ab1b_spec
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE = "cbdc4eb4d5cf005805ab26ad5a1863a825ad48a5"
AB1A = SHARED / "previews/active-bootstrap/ab1a-first-natural-stereo-look"
AB1A_PINS = {
    "manifest.json": "74eba4d6112f2de69fd797f9f41ff987e128ce1ecbcb5d48f05f597e9a2731fe",
    "process-log.jsonl": "4ff1056857455329386fb639e79271d0b2678ef9c3d7c29590e10508b58f7ae7",
    "acquisition/calibration.json": "9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913",
    "acquisition/rgb-observation.npz": "eb84831aee9676e011651821197812c81e7d51d76ab2cecfea609d3a8dd4268d",
    "evaluation_only/reference-observation.npz": "f23a7a53cdb7816ee4161337551d90825026a4a25fd8a57ba4981abaa99cdb08",
    "source/nb1c-action-manifest.json": "9fc65ef731601f44c67c141467f613a90c2d742007c79fc8090e9b530f0afe15",
    "measurement/measurement-freeze.json": "53dc5ff2985cfda4ed0ef0ed13f10be12a33e1c7693942dcf9101a2d1448243e",
    "evaluation_only/instance-catalog.json": "3924b5b4bde3e694d99e3c86b351be0b7f23d447ae6eda917619462b92732c1c",
    "measurement/stereo-summary.json": "166955c0e01f0f3e86f221e7e842e33f0162432949d3e05e42370e09bd7dbaf0",
    "evaluation/evaluation-summary.json": "5ed406369a4df597d943a01c8be9c393ef44ec60061bbae461b460643bab8e23",
    "prelook/prelook-geometry.json": "e65a85b433eb74e5d0592cc6236ccede43335966916026d6bc882b80eb783b8a",
}
AB1A_VIS_MANIFEST = (SHARED / "visuals/active-bootstrap/ab1a-first-natural-stereo-look/visuals-manifest.json",
                     "d38bfdc2b9158739cc635f3cbc5ba4a764e6234c5397ba50ca99780987b22da0")
CALIB_REL, REF_REL = "acquisition/calibration.json", "evaluation_only/reference-observation.npz"
COMPARISON = ("measurement/stereo-summary.json", "evaluation/evaluation-summary.json", "prelook/prelook-geometry.json")
NB1C_RUN = SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze"
NB1C_FREEZE_SHA = "87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37"
NB1C_MANIFEST_SHA = "524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e"
NB1C_VIS_MANIFEST = (SHARED / "visuals/natural-bootstrap-1c-rgb-candidate-gaze/visuals-manifest.json",
                     "8f20e7873c4f1d90bf26ed674f91daddc9c4350361aa4abb7e7dab0d2bb62d60")
NB1A_FREEZE = (SHARED / "previews/natural-bootstrap-1a-range-connectivity/discovery/bootstrap-freeze.json",
               "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a")
NB1B_FREEZE = (SHARED / "previews/natural-bootstrap-1b-foveal-serviceability/selection/serviceability-freeze.json",
               "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a")
CODE_PINS = {
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_run.py": "348fdee41b98f52d7b184b97a608a9b9da8b779794f0d8c9d1d198dd13095b0f",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1a_stereo.py": "c0238a7318c4a9c034c4a679104ae46cfd7504bf204935e2af15707b10f07f65",
    "tools/active_bootstrap/ab1a_visuals.py": "a9038c6927f031dcb190082233ce3cf61493356b194abca4b4326c1f60ac1a89",
    "tools/active_bootstrap/check_ab1a.py": "175bd0f94b06c915ffb0e78a0f849183c89238ca4bcb6cf6c40a450ba08dc0e8",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
}
YAW, PITCH, RANK, ROW, COL = 76.75, 7.75, 1, 164, 513
RAW, CORE, ORIGIN = 640, 256, 192
IPD, FOCAL = 0.063, 1217.8386501404907
PRODUCT_KEYS = {"left_core_row", "left_core_col", "uv_L", "uv_R"}
FORBIDDEN_KEY_TOKENS = ("xyz", "position", "range", "depth", "instance", "object", "normal", "semantic", "label", "truth",
                        "world")
QUANT = {"min": 0.0, "p05": 0.05, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
FRACTIONS = (0.001, 0.005, 0.010, 0.025)
MIN_INST = 50
Z_MIN = 1e-9
# recomputation tolerances (independent float64 routes); mutations are planted far above them
TOL_DIR, TOL_ANG, TOL_UV, TOL_XYZ, TOL_RAY, TOL_GAP, TOL_REL = 1e-12, 1e-11, 1e-9, 1e-9, 1e-7, 1e-7, 1e-8
GENERATOR = ["ab1b_spec.py", "ab1b_oracle.py", "ab1b_geometry.py", "ab1b_run.py", "ab1b_visuals.py"]
AB1B_FILES = {f"tools/active_bootstrap/{n}" for n in GENERATOR + ["check_ab1b.py"]} | {
    "docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md",
    "docs/active-bootstrap/ab1b-spherical-epipolar-geometry-report.md"}
DECLARED = AB1B_FILES | {"tools/repository/check_repository_layout.py", "CLAUDE.md", "docs/chat-handoff.md"}
COMMANDS = {"synthetic", "source", "oracle", "freeze-correspondence", "geometry", "freeze-geometry", "evaluate", "visualize"}
CANONICAL = ["source", "oracle", "freeze-correspondence", "geometry", "freeze-geometry", "evaluate"]
FROZEN_CORR = {"source/ab1a-source-manifest.json", "oracle/oracle-correspondences.npz", "oracle/oracle-summary.json",
               "oracle/oracle-opened-files.json"}
FROZEN_GEOM = {"oracle/correspondence-freeze.json", "oracle/oracle-correspondences.npz", "geometry/left-core-rays.npz",
               "geometry/epipolar-result.npz", "geometry/geometry-summary.json", "geometry/geometry-opened-files.json"}
GEOM_FILES = FROZEN_GEOM - {"oracle/correspondence-freeze.json", "oracle/oracle-correspondences.npz"} | {
    "geometry/geometry-freeze.json", "geometry/geometry-freeze-opened-files.json"}
FIGURES = ["overview.png", "raw-foveal-core.png", "spherical-epipolar-core.png", "perfect-correspondences.png",
           "epipolar-residual.png", "angular-disparity.png", "conditioning.png", "reconstructed-point-cloud.png",
           "triangulation-error.png", "planar-vs-spherical.png"]
ORA, DER, REF = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
BADGES = {"overview.png": [ORA, DER, REF], "raw-foveal-core.png": [ORA, DER], "spherical-epipolar-core.png": [DER, ORA],
          "perfect-correspondences.png": [ORA, DER], "epipolar-residual.png": [DER], "angular-disparity.png": [DER],
          "conditioning.png": [DER], "reconstructed-point-cloud.png": [DER], "triangulation-error.png": [REF, DER],
          "planar-vs-spherical.png": [REF, DER]}
FORBIDDEN_IDENTIFIERS = ("sgbm", "stereorectify", "initundistortrectifymap", "fsg_stereo", "ab1a_stereo",
                         "compute_natural", "bpy", "controller", "fsg6f", "fsg3", "surface_map", "multiobject", "fov3d")
FORBIDDEN_IMPORTS = ("cv2", "fsg_stereo", "ab1a_stereo", "bpy", "fov3d", "fsg6f_frontier", "fsg3_surface_map",
                     "multiobject2c_policy", "classroom_oracle1_matcher")
GEOMETRY_TRUTH_IDS = ("load_reference", "reference_rel", "reference_keys", "compute_oracle", "catalog_rel", "rgb_rel",
                      "ab1b_oracle", "position_w_l", "position_w_r", "instance_l", "instance_r")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ independent geometry
def unit(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def own_gaze(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])


def own_rays(eye: dict, uv) -> np.ndarray:
    k, r = np.asarray(eye["K"], np.float64), np.asarray(eye["R_hc"], np.float64)
    uv = np.asarray(uv, np.float64)
    dc = np.stack([(uv[..., 0] - k[0, 2]) / k[0, 0], (uv[..., 1] - k[1, 2]) / k[1, 1], np.ones(uv.shape[:-1])], -1)
    return unit(np.einsum("ij,...j->...i", r, dc))


def own_project(eye: dict, p_h) -> tuple[np.ndarray, np.ndarray]:
    k, r = np.asarray(eye["K"], np.float64), np.asarray(eye["R_hc"], np.float64)
    xc = np.einsum("ji,...j->...i", r, np.asarray(p_h, np.float64) - np.asarray(eye["centre_h_m"], np.float64))
    with np.errstate(divide="ignore", invalid="ignore"):
        u = k[0, 0] * xc[..., 0] / xc[..., 2] + k[0, 2]
        v = k[1, 1] * xc[..., 1] / xc[..., 2] + k[1, 2]
    return np.stack([u, v], -1), xc[..., 2]


def own_w2h(c: dict, p_w) -> np.ndarray:
    r = np.asarray(c["head_R_wh"], np.float64)
    return np.einsum("ji,...j->...i", r, np.asarray(p_w, np.float64) - np.asarray(c["head_origin_w_m"], np.float64))


def own_theta(d):
    d = np.asarray(d, np.float64)
    return np.arctan2(np.linalg.norm(np.cross(np.array([1.0, 0.0, 0.0]), d), axis=-1), d[..., 0])


def own_phi(d):
    d = np.asarray(d, np.float64)
    return np.angle(-d[..., 2] + 1j * d[..., 1])


def own_wrap(a):
    return np.angle(np.exp(1j * np.asarray(a, np.float64)))


def own_epipolar(th_l, th_r, ph_l, ph_r, b=IPD):
    """Law of sines: r_L = B sin(theta_R) / sin(theta_R - theta_L), along the left ray in the mean epipolar plane."""
    with np.errstate(divide="ignore", invalid="ignore"):
        r_l = b * np.sin(th_r) / np.sin(th_r - th_l)
    pb = np.angle(np.exp(1j * ph_l) + np.exp(1j * ph_r))
    p = np.stack([-b / 2 + r_l * np.cos(th_l), r_l * np.sin(th_l) * np.sin(pb), -r_l * np.sin(th_l) * np.cos(pb)], -1)
    return p, pb


def own_ray_ray(o_l, d_l, o_r, d_r):
    """Cramer's rule with cross products: s = ((o_R - o_L) x d_R) . n / |n|^2, t = ((o_R - o_L) x d_L) . n / |n|^2."""
    n = np.cross(d_l, d_r)
    nn = np.sum(n * n, -1)
    w = o_r - o_l
    s = np.sum(np.cross(w, d_r) * n, -1) / nn
    t = np.sum(np.cross(w, d_l) * n, -1) / nn
    p1, p2 = o_l + s[..., None] * d_l, o_r + t[..., None] * d_r
    gap = np.abs(np.sum(w * n, -1)) / np.sqrt(nn)
    return (p1 + p2) / 2, gap, s, t


def quant(a) -> dict | None:
    a = np.asarray(a, np.float64).ravel()
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, q)) for k, q in QUANT.items()} | {"count": int(a.size)}


def qeq(a: dict | None, b: dict | None, rel=1e-9) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return set(a) == set(b) and all(abs(a[k] - b[k]) <= rel * max(1.0, abs(b[k])) for k in a)


def leaf_eq(a, b, rel=1e-12) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(leaf_eq(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(leaf_eq(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= rel * max(1.0, abs(b))
    return a == b


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path, ab1a: Path | None = None):
        self.run, self.vis, self.ab1a = run, vis, ab1a or AB1A
        self.overrides: dict = {}

    def j(self, rel):
        return json.loads((self.run / rel).read_text())

    def npz(self, rel):
        with np.load(self.run / rel, allow_pickle=False) as z:
            return {k: np.asarray(z[k]) for k in z.files}

    def ov(self, name, default):
        return self.overrides.get(name, default)

    @cached_property
    def c(self):
        return json.loads((self.ab1a / CALIB_REL).read_text())

    @cached_property
    def ref(self):
        with np.load(self.ab1a / REF_REL, allow_pickle=False) as z:
            return {k: np.asarray(z[k]) for k in z.files}

    @cached_property
    def src(self):
        return self.j("source/ab1a-source-manifest.json")

    @cached_property
    def prod(self):
        return self.npz("oracle/oracle-correspondences.npz")

    @cached_property
    def osum(self):
        return self.j("oracle/oracle-summary.json")

    @cached_property
    def oopen(self):
        return self.j("oracle/oracle-opened-files.json")

    @cached_property
    def cfz(self):
        return self.j("oracle/correspondence-freeze.json")

    @cached_property
    def rays(self):
        return self.npz("geometry/left-core-rays.npz")

    @cached_property
    def res(self):
        return self.npz("geometry/epipolar-result.npz")

    @cached_property
    def gsum(self):
        return self.j("geometry/geometry-summary.json")

    @cached_property
    def gopen(self):
        return self.j("geometry/geometry-opened-files.json")

    @cached_property
    def gfz(self):
        return self.j("geometry/geometry-freeze.json")

    @cached_property
    def gfzopen(self):
        return self.j("geometry/geometry-freeze-opened-files.json")

    @cached_property
    def ev(self):
        return self.j("evaluation/evaluation-summary.json")

    @cached_property
    def evr(self):
        return self.npz("evaluation/evaluation-result.npz")

    @cached_property
    def evopen(self):
        return self.j("evaluation/evaluation-opened-files.json")

    @cached_property
    def log(self):
        return [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x.strip()]

    @cached_property
    def changed_files(self):
        ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
        return sorted(ch)

    # ---- the checker's own computations
    @cached_property
    def own_oracle(self) -> dict:
        c, ref = self.c, self.ref
        r, cc = np.mgrid[:CORE, :CORE]
        r, cc = r.ravel(), cc.ravel()
        pos = ref["position_w_L"][r + ORIGIN, cc + ORIGIN].astype(np.float64)
        ids = ref["instance_L"][r + ORIGIN, cc + ORIGIN].astype(np.int64)
        hit = np.isfinite(pos).all(-1) & (np.abs(pos).sum(-1) > 0)
        cat = hit & (ids > 0)
        uv, z = own_project(c["eyes"][1], own_w2h(c, np.where(hit[:, None], pos, 0.0)))
        proj = cat & np.isfinite(uv).all(-1) & np.isfinite(z) & (z > Z_MIN)
        with np.errstate(invalid="ignore"):
            inside = proj & (uv[:, 0] >= 0) & (uv[:, 0] <= RAW - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= RAW - 1)
        ui = np.rint(np.clip(np.nan_to_num(uv[:, 0]), 0, RAW - 1)).astype(int)
        vi = np.rint(np.clip(np.nan_to_num(uv[:, 1]), 0, RAW - 1)).astype(int)
        vis = inside & (ref["instance_R"][vi, ui].astype(np.int64) == ids)
        out_core = vis & ((uv[:, 0] < ORIGIN) | (uv[:, 0] > ORIGIN + CORE - 1) | (uv[:, 1] < ORIGIN)
                          | (uv[:, 1] > ORIGIN + CORE - 1))
        return {"rows": r[vis], "cols": cc[vis], "uv_R": uv[vis], "ids": ids[vis],
                "counts": [len(r), int(hit.sum()), int(cat.sum()), int(proj.sum()), int(inside.sum()), int(vis.sum()),
                           int(vis.sum())],
                "outside_right_core": int(out_core.sum()), "hit_mask": hit, "cat_mask": cat}

    @cached_property
    def own_geom(self) -> dict:
        c, p = self.c, self.prod
        o_l, o_r = np.array([-IPD / 2, 0, 0.0]), np.array([IPD / 2, 0, 0.0])
        d_l, d_r = own_rays(c["eyes"][0], p["uv_L"]), own_rays(c["eyes"][1], p["uv_R"])
        tl, tr, pl, pr = own_theta(d_l), own_theta(d_r), own_phi(d_l), own_phi(d_r)
        pe, pb = own_epipolar(tl, tr, pl, pr)
        pr_, gap, s, t = own_ray_ray(o_l, d_l, o_r, d_r)
        gam = np.arctan2(np.linalg.norm(np.cross(d_l, d_r), axis=-1), np.sum(d_l * d_r, -1))
        g = own_gaze(*c["gaze_yaw_pitch_deg"])
        tg, pg = float(own_theta(g)), float(own_phi(g))
        return {"d_L": d_l, "d_R": d_r, "theta_L": tl, "theta_R": tr, "phi_L": pl, "phi_R": pr, "P_epi": pe,
                "phi_bar": pb, "P_ray": pr_, "gap": gap, "s": s, "t": t, "gamma": gam, "tg": tg, "pg": pg,
                "o_L": o_l, "o_R": o_r,
                "chart": (tl - tg, math.sin(tg) * own_wrap(pl - pg), tr - tg, math.sin(tg) * own_wrap(pr - pg))}

    @cached_property
    def own_core(self) -> dict:
        r, cc = np.mgrid[:CORE, :CORE]
        uv = np.stack([cc + ORIGIN, r + ORIGIN], -1).astype(np.float64)
        d = own_rays(self.c["eyes"][0], uv)
        return {"uv": uv, "d": d, "theta": own_theta(d), "phi": own_phi(d)}

    @cached_property
    def p_truth(self) -> np.ndarray:
        rows = self.res["left_core_row"].astype(int) + ORIGIN
        cols = self.res["left_core_col"].astype(int) + ORIGIN
        return own_w2h(self.c, self.ref["position_w_L"][rows, cols].astype(np.float64))


# ------------------------------------------------------------------ static audits
def _tree(name: str, extra: str = ""):
    return ast.parse((HERE / name).read_text() + "\n" + extra)


def identifiers(tree) -> set[str]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.alias):
            out.add(n.name)
            if n.asname:
                out.add(n.asname)
    return out


def imports(tree) -> set[str]:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.split(".")[0])
    return out


def strings(tree) -> list[str]:
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def static_audit(x) -> dict:
    extra = x.ov("static_extra", {})
    bad_ids, bad_imports, blender = {}, {}, {}
    for name in GENERATOR:
        t = _tree(name, extra.get(name, ""))
        ids = {i.lower() for i in identifiers(t)}
        b = sorted(i for i in ids if any(f in i for f in FORBIDDEN_IDENTIFIERS))
        imps = sorted(i for i in imports(t) if i in FORBIDDEN_IMPORTS)
        bl = [s for s in strings(t) if s.strip().lower() == "blender" or s.strip().lower().startswith("blender ")]
        if b:
            bad_ids[name] = b
        if imps:
            bad_imports[name] = imps
        if bl:
            blender[name] = bl
    g = _tree("ab1b_geometry.py", extra.get("ab1b_geometry.py", ""))
    gid = {i.lower() for i in identifiers(g)}
    truth = sorted(i for i in gid if i in GEOMETRY_TRUTH_IDS)
    truth += [s for s in strings(g) if "position_w" in s or "instance_" in s]
    return {"forbidden_identifiers": bad_ids, "forbidden_imports": bad_imports, "blender_commands": blender,
            "geometry_truth_tokens": truth}


def _argv(e) -> list[str]:
    return [str(a) for a in e.get("argv", [])]


# ------------------------------------------------------------------ checks
def c01(x):
    got = {rel: sha256(x.ab1a / rel) for rel in AB1A_PINS}
    man = json.loads((x.ab1a / "manifest.json").read_text())["files"]
    listed = all(man.get(rel) == h for rel, h in AB1A_PINS.items() if rel not in ("manifest.json", "process-log.jsonl"))
    mfz = json.loads((x.ab1a / "measurement/measurement-freeze.json").read_text())
    mfz_ok = all(sha256(x.ab1a / n) == h for n, h in mfz["files"].items())
    src = x.src["pins"] == AB1A_PINS and all(x.src["hashed_before_geometry_freeze"][k] == AB1A_PINS[k]
                                             for k in x.src["hashed_before_geometry_freeze"])
    bad = [rel for rel, h in got.items() if h != AB1A_PINS[rel]]
    return not bad and listed and mfz_ok and src, {"mismatch": bad, "manifest_lists_pins": listed,
                                                   "ab1a_measurement_freeze_verifies": mfz_ok, "source_manifest": src}


def c02(x):
    calib = str(x.ab1a / CALIB_REL)
    act = json.loads((x.ab1a / "source/nb1c-action-manifest.json").read_text())["gaze"]
    det = {"gaze": x.c["gaze_yaw_pitch_deg"] == [YAW, PITCH],
           "action": (act["rank"], act["row"], act["col"], act["yaw_deg"], act["pitch_deg"]) == (RANK, ROW, COL, YAW, PITCH),
           "oracle_calibration": x.osum["inputs"]["calibration"] == {"path": str(AB1A / CALIB_REL),
                                                                     "sha256": AB1A_PINS[CALIB_REL]},
           "geometry_calibration": x.gsum["inputs"]["calibration"] == {"path": str(AB1A / CALIB_REL),
                                                                       "sha256": AB1A_PINS[CALIB_REL]},
           "freeze_calibration": x.gfz["calibration_source"] == {"path": str(AB1A / CALIB_REL), "sha256": AB1A_PINS[CALIB_REL]},
           "calibration_file": sha256(calib) == AB1A_PINS[CALIB_REL],
           "source_gaze": x.src["gaze"]["yaw_deg"] == YAW and x.src["gaze"]["pitch_deg"] == PITCH}
    return all(det.values()), det


def c03(x):
    log_bl = [e["command"] for e in x.log if "blender" in e or any("blender" in Path(a).name.lower() for a in _argv(e))]
    st = static_audit(x)["blender_commands"]
    return not log_bl and not st, {"log": log_bl, "static": st}


def c04(x):
    m = json.loads((x.ab1a / "manifest.json").read_text())["files"]
    bad = [n for n, h in m.items() if sha256(x.ab1a / n) != h]
    log = [json.loads(s) for s in (x.ab1a / "process-log.jsonl").read_text().splitlines() if s.strip()]
    acquires = sum(e["command"] == "acquire" for e in log)
    renders = [str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.suffix == ".exr" or "rgb-observation" in p.name
               or p.name == "acquisition"]
    ok = (not bad and sha256(x.ab1a / "manifest.json") == AB1A_PINS["manifest.json"]
          and sha256(x.ab1a / "process-log.jsonl") == AB1A_PINS["process-log.jsonl"] and acquires == 1 and not renders)
    return ok, {"ab1a_manifest_mismatch": bad[:5], "ab1a_acquires": acquires, "render_products_in_ab1b": renders}


def c05(x):
    bad = []
    for e in x.log:
        a = _argv(e)
        flags = {t for t in a if t.startswith("--")}
        if e["command"] not in COMMANDS or len(a) < 2 or a[1] != e["command"] or not flags <= {"--run", "--visuals"}:
            bad.append(a)
    once = {cmd: sum(e["command"] == cmd and e["status"] == "ok" for e in x.log) for cmd in CANONICAL}
    calibs = {x.osum["inputs"]["calibration"]["path"], x.gsum["inputs"]["calibration"]["path"],
              x.gfz["calibration_source"]["path"]}
    return not bad and all(v == 1 for v in once.values()) and len(calibs) == 1, {"bad_argv": bad[:3], "ok_counts": once,
                                                                                  "calibrations": sorted(calibs)}


def c06(x):
    toks = ("controller", "fsg6f", "fsg3_surface_map", "surface_map", "fusion", "surfel", "fov3d")
    log = [a for e in x.log for a in _argv(e) if any(t in a.lower() for t in toks)]
    files = [str(p.relative_to(x.run)) for p in x.run.rglob("*") if any(t in p.name.lower() for t in ("surfel", "surface-map",
                                                                                                       "fsg6f", "fused"))]
    st = static_audit(x)
    imp = {k: v for k, v in st["forbidden_imports"].items() if set(v) & {"fov3d", "fsg6f_frontier", "fsg3_surface_map",
                                                                          "multiobject2c_policy"}}
    ids = {k: [i for i in v if any(t in i for t in ("controller", "fsg6f", "fsg3", "surface_map", "fov3d"))]
           for k, v in st["forbidden_identifiers"].items()}
    ids = {k: v for k, v in ids.items() if v}
    return not log and not files and not imp and not ids, {"argv": log, "files": files, "imports": imp, "identifiers": ids}


def c07(x):
    st = static_audit(x)
    ids = {k: [i for i in v if "sgbm" in i or "stereo" in i or "compute_natural" in i]
           for k, v in st["forbidden_identifiers"].items()}
    ids = {k: v for k, v in ids.items() if v}
    log = [a for e in x.log for a in _argv(e) if "sgbm" in a.lower() or "ab1a_stereo" in a.lower()]
    mods = {"oracle": x.oopen["modules_loaded"], "geometry": x.gopen["modules_loaded"]}
    runtime = any(v for m in mods.values() for v in m.values())
    return not ids and not log and not runtime and not st["forbidden_imports"], {
        "identifiers": ids, "argv": log, "modules_loaded": mods, "imports": st["forbidden_imports"]}


def c08(x):
    st = static_audit(x)
    ids = {k: [i for i in v if "rectif" in i or "fsg_stereo" in i] for k, v in st["forbidden_identifiers"].items()}
    ids = {k: v for k, v in ids.items() if v}
    cv = {k: v for k, v in st["forbidden_imports"].items() if "cv2" in v or "fsg_stereo" in v}
    runtime = x.gopen["modules_loaded"].get("cv2") or x.gopen["modules_loaded"].get("fsg_stereo")
    rect_keys = [k for k in list(x.rays) + list(x.res) if k in ("R1", "R2", "P1", "P2", "Q", "Q_full", "Q_core", "crop_xywh")
                 or k.lower().startswith("rect")]
    return not ids and not cv and not runtime and not rect_keys, {"identifiers": ids, "cv2_imports": cv,
                                                                 "runtime_loaded": bool(runtime), "rectified_keys": rect_keys}


def c09(x):
    oc = x.own_core
    p = x.prod
    det = {"raster": x.c["image_size_wh"] == [RAW, RAW] and x.c["core_size"] == CORE and (RAW - CORE) // 2 == ORIGIN,
           "ray_table_uv": np.array_equal(x.rays["uv"], oc["uv"]),
           "ray_table_rowcol": np.array_equal(x.rays["row"], np.mgrid[:CORE, :CORE][0])
           and np.array_equal(x.rays["col"], np.mgrid[:CORE, :CORE][1]),
           "product_rowcol_in_core": bool(p["left_core_row"].min() >= 0 and p["left_core_row"].max() < CORE
                                          and p["left_core_col"].min() >= 0 and p["left_core_col"].max() < CORE)
           if len(p["left_core_row"]) else True,
           "uv_L_is_raw_core_pixel_centre": np.array_equal(p["uv_L"], np.stack([p["left_core_col"] + ORIGIN,
                                                                              p["left_core_row"] + ORIGIN], -1).astype(float))}
    return all(det.values()), det


def c10(x):
    d = x.rays["direction_h"]
    err = float(np.abs(d - x.own_core["d"]).max())
    fin = int(np.isfinite(d).all(-1).sum())
    return err <= TOL_DIR and fin == CORE * CORE, {"max_direction_difference": err, "finite_rays": fin}


def c11(x):
    o, p = x.own_oracle, x.prod
    same = (np.array_equal(p["left_core_row"], o["rows"]) and np.array_equal(p["left_core_col"], o["cols"]))
    inside = bool(((p["uv_R"] >= 0) & (p["uv_R"] <= RAW - 1)).all())
    rec = x.osum["right_margin"]["outside_right_nominal_core"]
    return same and inside and rec == o["outside_right_core"], {"same_set_as_padded_rule": same, "inside_raster": inside,
                                                                "outside_right_core_recorded": rec,
                                                                "outside_right_core_checker": o["outside_right_core"]}


def c12(x):
    o = x.own_oracle
    att = [s["remaining"] for s in x.osum["attrition"]]
    rows, cols = x.prod["left_core_row"].astype(int), x.prod["left_core_col"].astype(int)
    idx = rows * CORE + cols
    ok_px = bool(o["cat_mask"][idx].all()) if len(idx) else True
    return att[1:3] == o["counts"][1:3] and ok_px, {"recorded": att[1:3], "checker": o["counts"][1:3],
                                                    "every_pair_left_hit_with_instance": ok_px}


def c13(x):
    o, p = x.own_oracle, x.prod
    if len(p["uv_R"]) != len(o["uv_R"]):
        return False, {"count": [len(p["uv_R"]), len(o["uv_R"])]}
    err = float(np.abs(p["uv_R"] - o["uv_R"]).max()) if len(o["uv_R"]) else 0.0
    return err <= TOL_UV, {"max_uv_R_difference_px": err}


def c14(x):
    o, p = x.own_oracle, x.prod
    got = set(zip(p["left_core_row"].tolist(), p["left_core_col"].tolist()))
    want = set(zip(o["rows"].tolist(), o["cols"].tolist()))
    att = [s["remaining"] for s in x.osum["attrition"]]
    diff = x.osum["excluded"]["different_right_instance"] == o["counts"][4] - o["counts"][5]
    return got == want and att[5] == o["counts"][5] and diff, {"pairs": len(got), "checker": len(want),
                                                               "missing": len(want - got), "extra": len(got - want)}


def c15(x):
    p, o = x.prod, x.own_oracle
    uv = p["uv_R"]
    integral = float((np.abs(uv - np.rint(uv)) < 1e-9).mean()) if uv.size else 0.0
    err = float(np.abs(uv - o["uv_R"]).max()) if (uv.size and uv.shape == o["uv_R"].shape) else math.inf
    return uv.dtype == np.float64 and integral < 0.5 and err <= TOL_UV, {"dtype": str(uv.dtype),
                                                                         "integral_fraction": integral, "max_difference": err}


def c16(x):
    keys = set(x.prod)
    bad = sorted(k for k in keys if any(t in k.lower() for t in FORBIDDEN_KEY_TOKENS))
    dt = (x.prod["left_core_row"].dtype.kind in "iu" and x.prod["left_core_col"].dtype.kind in "iu"
          and x.prod["uv_L"].dtype == np.float64 and x.prod["uv_R"].dtype == np.float64) if keys >= PRODUCT_KEYS else False
    rec = set(x.osum["product_keys"]) == PRODUCT_KEYS
    return keys == PRODUCT_KEYS and not bad and dt and rec, {"keys": sorted(keys), "forbidden": bad, "dtypes": dt}


def _log_index(x, cmd):
    return next((i for i, e in enumerate(x.log) if e["command"] == cmd and e["status"] == "ok"), None)


def c17(x):
    fz = x.cfz
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    order = (_log_index(x, "freeze-correspondence") is not None and _log_index(x, "geometry") is not None
             and _log_index(x, "freeze-correspondence") < _log_index(x, "geometry"))
    inputs = (x.gsum["inputs"]["correspondences"]["sha256"] == fz["files"]["oracle/oracle-correspondences.npz"]
              and fz["oracle_inputs"]["reference_observation"]["sha256"] == AB1A_PINS[REF_REL]
              and fz["oracle_inputs"]["calibration"]["sha256"] == AB1A_PINS[CALIB_REL])
    return not bad and set(fz["files"]) == FROZEN_CORR and order and inputs, {"mismatch": bad, "order": order,
                                                                               "geometry_consumed_frozen_product": inputs}


def c18(x):
    want = {str(AB1A / CALIB_REL), str(x.run / "oracle/oracle-correspondences.npz")}
    reads = set(x.gopen["data_reads"])
    writes = [w for w in x.gopen["writes"] if not w.startswith(str(x.run / "geometry") + "/")]
    return reads == want and not writes and not x.gopen["violations"], {"data_reads": sorted(reads), "writes_outside": writes,
                                                                         "violations": len(x.gopen["violations"])}


def c19(x):
    ev = [e["path"] for e in x.gopen["events"] if e.get("event") == "open"]
    truth = [p for p in ev if p.endswith("reference-observation.npz") or p.endswith(".exr") or "evaluation_only" in p
             or "/measurement/" in p or p.endswith("stereo-result.npz") or (str(AB1A) in p and "/evaluation/" in p)]
    counts = (x.gopen["position_reads"], x.gopen["object_index_reads"], x.gopen["ab1a_natural_result_reads"])
    fz = (x.gfz["position_reads"], x.gfz["object_index_reads"], x.gfz["ab1a_natural_result_reads"])
    st = static_audit(x)["geometry_truth_tokens"]
    return not truth and counts == (0, 0, 0) and fz == (0, 0, 0) and not st, {"truth_opens": truth, "recorded": counts,
                                                                               "freeze": fz, "static": st}


def c20(x):
    cen = [e["centre_h_m"] for e in x.c["eyes"]]
    ve = x.res["valid_epi"].astype(bool)
    p = x.res["P_epi"][ve]
    o = x.own_geom
    front_l = bool((np.sum((p - o["o_L"]) * o["d_L"][ve], -1) > 0).all()) if len(p) else True
    front_r = bool((np.sum((p - o["o_R"]) * o["d_R"][ve], -1) > 0).all()) if len(p) else True
    det = {"eye_centres": cen == [[-IPD / 2, 0.0, 0.0], [IPD / 2, 0.0, 0.0]], "ipd": x.c["ipd_m"] == IPD,
           "axis": x.gsum["geometry"]["baseline_axis"] == [1.0, 0.0, 0.0], "baseline_m": x.gsum["baseline_m"] == IPD,
           "reconstruction_in_front_of_left_ray": front_l, "reconstruction_in_front_of_right_ray": front_r}
    return all(det.values()), det


def _maxdiff(a, b):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return math.inf
    m = np.isfinite(a) | np.isfinite(b)
    return float(np.abs(a[m] - b[m]).max()) if m.any() else 0.0


def c21(x):
    o = x.own_geom
    d = {"theta_L": _maxdiff(x.res["theta_L"], o["theta_L"]), "theta_R": _maxdiff(x.res["theta_R"], o["theta_R"]),
         "core_theta": _maxdiff(x.rays["theta"], x.own_core["theta"])}
    return all(v <= TOL_ANG for v in d.values()), d


def c22(x):
    o = x.own_geom
    d = {"phi_L": _maxdiff(x.res["phi_L"], o["phi_L"]), "phi_R": _maxdiff(x.res["phi_R"], o["phi_R"]),
         "core_phi": _maxdiff(x.rays["phi"], x.own_core["phi"])}
    return all(v <= TOL_ANG for v in d.values()), d


def c23(x):
    G = _generator("ab1b_geometry")
    seam = np.array([2 * math.pi - 2e-6, -2 * math.pi + 2e-6, math.pi + 1e-3, -math.pi - 1e-3, 3.5 * math.pi, 0.25])
    gen = np.asarray(G.wrap_pi(seam))
    own = own_wrap(seam)
    seam_ok = float(np.abs(gen - own).max()) <= 1e-12
    allphi = np.concatenate([x.res["phi_L"], x.res["phi_R"], x.rays["phi"].ravel()])
    allphi = allphi[np.isfinite(allphi)]
    rng = bool(((allphi > -math.pi - 1e-15) & (allphi <= math.pi + 1e-15)).all())
    o = x.own_geom
    res = _maxdiff(x.res["phi_residual"], own_wrap(o["phi_R"] - o["phi_L"]))
    pb = _maxdiff(own_wrap(x.res["phi_bar"] - o["phi_bar"]), np.zeros_like(o["phi_bar"]))
    return seam_ok and rng and res <= TOL_ANG and pb <= TOL_ANG, {"generator_wrap_on_seam": seam_ok, "phi_range": rng,
                                                                  "residual": res, "phi_bar": pb}


def c24(x):
    o = x.own_geom
    d = {"theta_g": abs(x.gsum["theta_g_rad"] - o["tg"]), "phi_g": abs(x.gsum["phi_g_rad"] - o["pg"])}
    return all(v <= TOL_ANG for v in d.values()), d


def c25(x):
    o, oc = x.own_geom, x.own_core
    cu = oc["theta"] - o["tg"]
    cv = math.sin(o["tg"]) * own_wrap(oc["phi"] - o["pg"])
    ul, vl, ur, vr = o["chart"]
    d = {"core_u": _maxdiff(x.rays["chart_u"], cu), "core_v": _maxdiff(x.rays["chart_v"], cv),
         "u_L": _maxdiff(x.res["chart_u_L"], ul), "v_L": _maxdiff(x.res["chart_v_L"], vl),
         "u_R": _maxdiff(x.res["chart_u_R"], ur), "v_R": _maxdiff(x.res["chart_v_R"], vr)}
    return all(v <= TOL_ANG for v in d.values()), d


def c26(x):
    o = x.own_geom
    d = _maxdiff(x.res["delta_theta"], o["theta_R"] - o["theta_L"])
    return d <= 2 * TOL_ANG, {"max_delta_theta_difference": d}


def c27(x):
    o = x.own_geom
    d = _maxdiff(x.res["phi_residual"], own_wrap(o["phi_R"] - o["phi_L"]))
    q = qeq(x.gsum["distributions"]["abs_phi_residual_rad"], quant(np.abs(x.res["phi_residual"])))
    return d <= TOL_ANG and q, {"max_residual_difference": d, "summary_matches_saved": q}


def c28(x):
    o = x.own_geom
    ve = x.res["valid_epi"].astype(bool)
    own_valid = np.isfinite(o["P_epi"]).all(-1)
    d = _maxdiff(x.res["P_epi"][ve], o["P_epi"][ve]) if ve.any() else 0.0
    rho = _maxdiff(x.res["rho"][ve], (np.linalg.norm(o["P_epi"][:, 1:], axis=-1))[ve]) if ve.any() else 0.0
    return bool(np.array_equal(ve, own_valid)) and d <= TOL_XYZ and rho <= TOL_XYZ, {
        "valid_equal": bool(np.array_equal(ve, own_valid)), "max_P_epi_difference_m": d, "max_rho_difference_m": rho}


def c29(x):
    o = x.own_geom
    vr = x.res["valid_ray"].astype(bool)
    d = _maxdiff(x.res["P_ray"][vr], o["P_ray"][vr]) if vr.any() else 0.0
    s = max(_maxdiff(x.res["s_L"][vr], o["s"][vr]), _maxdiff(x.res["s_R"][vr], o["t"][vr])) if vr.any() else 0.0
    return d <= TOL_RAY and s <= TOL_RAY and bool(vr.all() == np.isfinite(o["P_ray"]).all()), {
        "max_P_ray_difference_m": d, "max_parameter_difference_m": s}


def c30(x):
    o = x.own_geom
    vr = x.res["valid_ray"].astype(bool)
    g = _maxdiff(x.res["ray_gap"][vr], o["gap"][vr]) if vr.any() else 0.0
    diff = _maxdiff(x.res["epi_ray_diff"], np.linalg.norm(x.res["P_epi"] - x.res["P_ray"], axis=-1))
    return g <= TOL_GAP and diff <= 1e-15, {"max_gap_difference_m": g, "epi_ray_difference_recompute": diff}


def c31(x):
    o = x.own_geom
    gam = _maxdiff(x.res["gamma"], o["gamma"])
    kap = float(np.nanmax(np.abs(x.res["kappa"] / (1 / np.abs(np.sin(o["gamma"]))) - 1))) if len(o["gamma"]) else 0.0
    dth = o["theta_R"] - o["theta_L"]
    per = IPD * np.sin(o["theta_L"]) / np.sin(dth) ** 2 / FOCAL
    pp = float(np.nanmax(np.abs(x.res["range_per_px"] / per - 1))) if len(per) else 0.0
    rl = _maxdiff(x.res["range_L"], np.linalg.norm(x.res["P_epi"] - o["o_L"], axis=-1))
    return gam <= TOL_ANG and kap <= TOL_REL and pp <= TOL_REL and rl <= 1e-15, {
        "gamma": gam, "kappa_rel": kap, "range_per_px_rel": pp, "range_L": rl}


def c32(x):
    fz = x.gfz
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    order = (_log_index(x, "freeze-geometry") is not None and _log_index(x, "evaluate") is not None
             and _log_index(x, "freeze-geometry") < _log_index(x, "evaluate"))
    cf = fz["correspondence_freeze_sha256"] == sha256(x.run / "oracle/correspondence-freeze.json")
    ev = x.ev["geometry_freeze_sha256"] == sha256(x.run / "geometry/geometry-freeze.json")
    pre = all(fz["preconditions"].values())
    return not bad and set(fz["files"]) == FROZEN_GEOM and order and cf and ev and pre, {
        "mismatch": bad, "order": order, "correspondence_freeze": cf, "evaluation_cites_freeze": ev, "preconditions": pre}


def c33(x):
    ev = [str(e) for e in x.evopen["ordered_data_events"]]
    mark = ev.index("geometry_freeze_verified") if "geometry_freeze_verified" in ev else None
    ref_mark = ev.index("reference_access_begins") if "reference_access_begins" in ev else None
    first_ref = next((i for i, e in enumerate(ev) if e.endswith("reference-observation.npz")), None)
    frozen = {str(x.run / n) for n in FROZEN_GEOM} | {str(x.run / "geometry/geometry-freeze.json"), str(AB1A / CALIB_REL)}
    before = ev[:mark] if mark is not None else ev
    not_frozen = [e for e in before if e not in frozen]
    ok = (mark is not None and ref_mark is not None and first_ref is not None and mark < ref_mark < first_ref
          and not not_frozen and not x.evopen["violations"])
    return ok, {"freeze_mark_index": mark, "reference_mark_index": ref_mark, "first_reference_read": first_ref,
                "reads_before_freeze_mark_not_frozen_geometry": not_frozen}


def c34(x):
    d = _maxdiff(x.evr["P_truth"], x.p_truth)
    rows = np.array_equal(x.evr["left_core_row"], x.res["left_core_row"]) and np.array_equal(
        x.evr["left_core_col"], x.res["left_core_col"])
    ids = x.ref["instance_L"][x.res["left_core_row"] + ORIGIN, x.res["left_core_col"] + ORIGIN]
    return d <= 1e-12 and rows and np.array_equal(x.evr["left_instance"], ids), {"max_P_truth_difference_m": d,
                                                                                "same_indices": rows}


def _errs(p, t, m, o_l):
    p, t = np.asarray(p, np.float64)[m], np.asarray(t, np.float64)[m]
    e3 = np.linalg.norm(p - t, axis=-1)
    rt = np.linalg.norm(t - o_l, axis=-1)
    rad = np.linalg.norm(p - o_l, axis=-1) - rt
    return {"pairs": int(m.sum()), "error_3d_m": quant(e3), "radial_abs_m": quant(np.abs(rad)), "radial_signed_m": quant(rad),
            "radial_relative_abs": quant(np.abs(rad) / rt),
            "fraction_3d_within_m": ({f"{s:.3f}": float((e3 <= s).mean()) for s in FRACTIONS} if e3.size else None)}


def c35(x):
    o_l = np.array([-IPD / 2, 0, 0.0])
    ve, vr = x.res["valid_epi"].astype(bool), x.res["valid_ray"].astype(bool)
    own_e = _errs(x.res["P_epi"], x.p_truth, ve, o_l)
    own_r = _errs(x.res["P_ray"], x.p_truth, vr, o_l)
    arr = (_maxdiff(x.evr["error_3d_epi_m"], np.linalg.norm(x.res["P_epi"] - x.p_truth, axis=-1)) <= 1e-12
           and _maxdiff(x.evr["error_3d_ray_m"], np.linalg.norm(x.res["P_ray"] - x.p_truth, axis=-1)) <= 1e-12)
    e = leaf_eq(x.ev["epipolar_vs_truth"], own_e, 1e-9)
    r = leaf_eq(x.ev["ray_ray_vs_truth"], own_r, 1e-9)
    return e and r and arr, {"epipolar_stats": e, "ray_ray_stats": r, "arrays": arr}


def c36(x):
    ve = x.res["valid_epi"].astype(bool)
    ul, _ = own_project(x.c["eyes"][0], x.res["P_epi"])
    ur, _ = own_project(x.c["eyes"][1], x.res["P_epi"])
    rl = np.linalg.norm(ul - x.prod["uv_L"], axis=-1)
    rr = np.linalg.norm(ur - x.prod["uv_R"], axis=-1)
    arr = (_maxdiff(x.evr["reprojection_L_px"][ve], rl[ve]) <= TOL_UV
           and _maxdiff(x.evr["reprojection_R_px"][ve], rr[ve]) <= TOL_UV)
    s = (qeq(x.ev["reprojection_px"]["left"], quant(x.evr["reprojection_L_px"][ve]))
         and qeq(x.ev["reprojection_px"]["right"], quant(x.evr["reprojection_R_px"][ve])))
    return arr and s, {"arrays": arr, "summary": s,
                       "max_reprojection_px": [float(rl[ve].max()) if ve.any() else None,
                                               float(rr[ve].max()) if ve.any() else None]}


def c37(x):
    fz = x.gfz
    now = all(sha256(x.run / n) == h for n, h in fz["files"].items())
    writes = [w for w in x.evopen["writes"] if not w.startswith(str(x.run / "evaluation") + "/")]
    fwrites = [w for w in x.gfzopen["writes"] if w != str(x.run / "geometry/geometry-freeze.json")]
    files = {str(p.relative_to(x.run)) for p in (x.run / "geometry").rglob("*") if p.is_file()}
    return now and not writes and not fwrites and files == {n for n in GEOM_FILES if n.startswith("geometry/")}, {
        "freeze_verifies_now": now, "evaluation_writes_outside": writes, "freeze_step_writes": fwrites,
        "geometry_files": sorted(files)}


def c38(x):
    a = x.ev["ab1a_comparison"]
    st = json.loads((x.ab1a / "measurement/stereo-summary.json").read_text())
    ev = json.loads((x.ab1a / "evaluation/evaluation-summary.json").read_text())
    pre = json.loads((x.ab1a / "prelook/prelook-geometry.json").read_text())["eyes"]["L"]
    p, s = a["ab1a_planar_rectified"], a["ab1b_spherical_raw_core"]
    det = {"hashes": a["sha256"] == {k: AB1A_PINS[k] for k in COMPARISON}
           and all(sha256(x.ab1a / k) == AB1A_PINS[k] for k in COMPARISON),
           "ab1a_values": (p["natural_valid"], p["reference_valid"], p["core_pixels"]) == (
               st["valid_count"], ev["counts"]["reference_valid"], st["core_pixels"])
           and p["rectified_core_raw_source_px_L"] == pre["raw_source_of_rectified_core_px"]
           and p["rectified_core_centre_from_gaze_deg"] == pre["rectified_core_centre_from_gaze_deg"]
           and p["rectified_core_centre_from_baseline_deg"] == pre["rectified_core_centre_from_baseline_deg"]
           and p["rectified_core_pixels_from_nominal_raw_core"] == pre["rectified_core_pixels_from_nominal_raw_core"],
           "ab1b_values": (s["raw_core_rays_represented"], s["perfect_correspondences"], s["triangulated"]) == (
               int(np.isfinite(x.rays["theta"]).sum()), len(x.prod["uv_R"]), int(x.res["valid_epi"].sum())),
           "read_after_freeze": "ab1a_comparison_begins" in x.evopen["ordered_data_events"]
           and all(x.evopen["ordered_data_events"].index("ab1a_comparison_begins")
                   < x.evopen["ordered_data_events"].index(str(AB1A / k)) for k in COMPARISON)}
    return all(det.values()), det


def c39(x):
    sys.path.insert(0, str(HERE))
    V = _generator("ab1b_visuals")
    figs, _d = V.render_all(x.run)
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    bad = [n for n in FIGURES if n not in figs or not (x.vis / n).is_file()
           or (x.vis / n).read_bytes() != V.png_bytes(figs[n]) or man["figures"][n]["sha256"] != sha256(x.vis / n)]
    return not bad and sorted(figs) == sorted(FIGURES), {"mismatch": bad}


def c40(x):
    ch = x.changed_files
    acc = [f for f in ch if (f.startswith(("fov3d/", "tools/controller/", "tools/natural_bootstrap/", "tools/classroom_oracle/",
                                           "tools/visual_language/", "tools/baseline/", "scenes/"))
                             or (f.startswith("tools/") and f.count("/") == 1)
                             or (f.startswith("tools/active_bootstrap/ab1a_") or f == "tools/active_bootstrap/check_ab1a.py"))]
    code = {p: sha256(REPO / p) == h for p, h in CODE_PINS.items()}
    nb1c = json.loads((NB1C_RUN / "selection/rgb-gaze-freeze.json").read_text())
    trees = {"NB1c freeze": sha256(NB1C_RUN / "selection/rgb-gaze-freeze.json") == NB1C_FREEZE_SHA
             and all(sha256(NB1C_RUN / "selection" / n) == h for n, h in nb1c["files"].items()),
             "NB1c manifest": sha256(NB1C_RUN / "manifest.json") == NB1C_MANIFEST_SHA,
             "NB1c visuals": sha256(NB1C_VIS_MANIFEST[0]) == NB1C_VIS_MANIFEST[1],
             "NB1a freeze": sha256(NB1A_FREEZE[0]) == NB1A_FREEZE[1], "NB1b freeze": sha256(NB1B_FREEZE[0]) == NB1B_FREEZE[1],
             "AB1a visuals": sha256(AB1A_VIS_MANIFEST[0]) == AB1A_VIS_MANIFEST[1]}
    return not acc and all(code.values()) and all(trees.values()), {"accepted_files_changed": acc,
                                                                    "code_pins": {k: v for k, v in code.items() if not v},
                                                                    "trees": trees}


def c41(x):
    extra = [f for f in x.changed_files if f not in DECLARED]
    return not extra, {"undeclared": extra[:8]}


def c42(x):
    rep = x.j("synthetic/synthetic-report.json")
    gen = rep["passed"] and len(rep["cases"]) == 15 and all(c["ok"] for c in rep["cases"])
    own = indep_synthetic()
    return gen and all(own.values()), {"generator": [c["ok"] for c in rep["cases"]], "checker": own}


def c43(x):
    lc = x.gsum["left_core"]
    th, ph = x.own_core["theta"], x.own_core["phi"]
    o = x.own_geom
    deg = np.degrees
    want = {"theta_min": deg(th.min()), "theta_median": deg(np.median(th)), "theta_max": deg(th.max()),
            "pole": deg(np.minimum(th, math.pi - th).min()), "lev_min": np.sin(th).min(), "lev_med": np.median(np.sin(th)),
            "lev_max": np.sin(th).max(), "u_min": (th - o["tg"]).min(), "u_max": (th - o["tg"]).max(),
            "v_min": (math.sin(o["tg"]) * own_wrap(ph - o["pg"])).min(), "v_max": (math.sin(o["tg"]) * own_wrap(ph - o["pg"])).max()}
    got = {"theta_min": lc["theta_deg"]["min"], "theta_median": lc["theta_deg"]["median"], "theta_max": lc["theta_deg"]["max"],
           "pole": lc["min_angle_to_baseline_pole_deg"], "lev_min": lc["leverage_sin_theta"]["min"],
           "lev_med": lc["leverage_sin_theta"]["median"], "lev_max": lc["leverage_sin_theta"]["max"],
           "u_min": lc["chart_u_rad"]["min"], "u_max": lc["chart_u_rad"]["max"], "v_min": lc["chart_v_rad"]["min"],
           "v_max": lc["chart_v_rad"]["max"]}
    bad = {k: (got[k], float(want[k])) for k in want if abs(got[k] - float(want[k])) > 1e-9 * max(1.0, abs(float(want[k])))}
    counts = lc["rays"] == CORE * CORE and lc["finite"] == CORE * CORE and lc["pole_singular"] == int(
        (np.hypot(x.own_core["d"][..., 1], x.own_core["d"][..., 2]) < 1e-12).sum())
    return not bad and counts, {"mismatch": bad, "counts": counts}


def c44(x):
    att = [s["remaining"] for s in x.osum["attrition"]]
    mono = all(a >= b for a, b in zip(att, att[1:]))
    return (mono and att == x.own_oracle["counts"] and att[-1] == len(x.prod["uv_R"]) == x.osum["correspondences"],
            {"recorded": att, "checker": x.own_oracle["counts"]})


def c45(x):
    r, d = x.res, x.gsum["distributions"]
    ve, vr = r["valid_epi"].astype(bool), r["valid_ray"].astype(bool)
    want = {"abs_phi_residual_rad": quant(np.abs(r["phi_residual"])), "delta_theta_rad": quant(r["delta_theta"]),
            "ray_angle_gamma_rad": quant(r["gamma"]), "kappa": quant(r["kappa"]), "closest_ray_gap_m": quant(r["ray_gap"][vr]),
            "epi_ray_difference_m": quant(r["epi_ray_diff"][ve & vr]), "range_L_m": quant(r["range_L"][ve]),
            "range_per_px_m": quant(r["range_per_px"])}
    bad = [k for k in want if not qeq(d.get(k), want[k], 1e-12)]
    k = x.gsum["counts"]
    dt = r["delta_theta"]
    cnt = (k["correspondences"], k["triangulated_epipolar"], k["triangulated_ray_ray"], k["delta_theta_positive"],
           k["delta_theta_zero"], k["delta_theta_negative"]) == (len(dt), int(ve.sum()), int(vr.sum()), int((dt > 0).sum()),
                                                                 int((dt == 0).sum()), int((dt < 0).sum()))
    return not bad and set(d) == set(want) and cnt, {"mismatch": bad, "counts": cnt}


def c46(x):
    m = x.j("manifest.json")
    vis = json.loads((x.vis / "visuals-manifest.json").read_text())
    det = {"source": x.src["truth"] == DER, "oracle_summary": x.osum["truth"] == DER and "ORACLE" in x.osum["statement"],
           "geometry": x.gsum["truth"] == DER and "TRUTH-FREE" in x.gsum["statement"],
           "evaluation": x.ev["truth"] == REF and x.ev["computed_after_freeze"] is True,
           "manifest": m["truth"].get("evaluation/") == REF and m["truth"].get("geometry/") == DER,
           "figures": all(vis["figures"][n]["badges"] == BADGES[n] for n in FIGURES),
           "no_controller_time": "CONTROLLER-TIME" not in json.dumps(vis) and "CONTROLLER-TIME" not in json.dumps(m)}
    return all(det.values()), det


# ------------------------------------------------------------------ the checker's own synthetic subset
def _generator(name):
    for p in (HERE, TOOLS, TOOLS / "natural_bootstrap", TOOLS / "classroom_oracle", TOOLS / "visual_language"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    return __import__(name)


def indep_synthetic() -> dict:
    G = _generator("ab1b_geometry")
    o_l, o_r = np.array([-IPD / 2, 0, 0.0]), np.array([IPD / 2, 0, 0.0])
    p = np.array([[0.4, -0.3, -3.0], [-1.0, 0.8, -1.5], [2.0, 0.1, 0.5]])
    d_l, d_r = unit(p - o_l), unit(p - o_r)
    tl, pl, _ = G.theta_phi(d_l)
    tr, pr, _ = G.theta_phi(d_r)
    e = G.triangulate_epipolar(tl, tr, pl, pr, IPD)
    own, _ = own_epipolar(own_theta(d_l), own_theta(d_r), own_phi(d_l), own_phi(d_r))
    sw = G.triangulate_epipolar(tr, tl, pr, pl, IPD)
    rr = G.triangulate_rays(o_l, d_l, o_r, d_r)
    sing = G.theta_phi(np.array([[1.0, 0, 0], [-1.0, 0, 0]]))
    seam = float(G.wrap_pi(np.array([-math.pi + 1e-6 - (math.pi - 1e-6)]))[0])
    rejected = []
    good = {"left_core_row": np.array([1], np.int32), "left_core_col": np.array([2], np.int32),
            "uv_L": np.array([[194.0, 193.0]]), "uv_R": np.array([[195.5, 193.25]])}
    for k in ("xyz_h", "position_w", "instance_id", "range_m"):
        try:
            G.validate_product({**good, k: np.zeros((1, 3))})
            rejected.append(False)
        except ValueError:
            rejected.append(True)
    return {"exact_points": float(np.abs(e["P_epi"] - p).max()) <= 1e-9 and float(np.abs(own - p).max()) <= 1e-9,
            "phi_equal": float(np.abs(own_wrap(pr - pl)).max()) <= 1e-12,
            "delta_theta_positive": bool((tr - tl > 0).all()),
            "swapped_is_minus_P": float(np.abs(sw["P_epi"] + p).max()) <= 1e-9,
            "ray_ray_agrees": float(np.abs(rr["P_ray"] - p).max()) <= 1e-9,
            "pole_singular": bool(sing[2].all() and np.isnan(sing[1]).all()),
            "seam_wrap": abs(seam - 2e-6) <= 1e-12, "truth_products_rejected": all(rejected)}


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("accepted AB1a source identities and hashes", c01), ("exact gaze #1 and calibration reused", c02),
    ("no Blender command", c03), ("no new acquisition", c04), ("no second gaze", c05),
    ("no controller / FSG6f / fusion", c06), ("no SGBM invocation", c07),
    ("no cv2.stereoRectify in the AB1b geometry path", c08), ("raw measurement core is the central 256 x 256 of the left raw raster", c09),
    ("all 65,536 raw-core rays independently recompute", c10), ("right matching uses the padded 640 x 640 raster", c11),
    ("oracle left finite-geometry rule recomputes", c12), ("right projection independently recomputes", c13),
    ("same-instance right visibility recomputes", c14), ("exact continuous uv_R retained", c15),
    ("correspondence product contains no XYZ / Position / range / instance", c16),
    ("correspondence freeze verifies and precedes the geometry", c17),
    ("geometry opens only calibration + frozen correspondence product", c18),
    ("geometry opens no Position / Object Index / AB1a natural result", c19), ("baseline axis is +X", c20),
    ("theta formula recomputes", c21), ("phi formula recomputes", c22), ("phi wrapping recomputes", c23),
    ("theta_g / phi_g recompute", c24), ("display chart u / v recompute", c25), ("delta_theta recomputes", c26),
    ("phi residual recomputes", c27), ("epipolar triangulation recomputes (law of sines)", c28),
    ("ray-ray triangulation recomputes (Cramer)", c29), ("closest-ray gap recomputes", c30),
    ("conditioning quantities recompute", c31), ("geometry freeze verifies and precedes evaluation", c32),
    ("evaluation reopens truth only after the geometry freeze", c33), ("P_truth extraction recomputes", c34),
    ("3-D / radial error statistics recompute", c35), ("camera reprojection residuals recompute", c36),
    ("evaluation cannot change the frozen geometry", c37), ("post-freeze AB1a comparison is descriptive and exact", c38),
    ("figures regenerate deterministically", c39), ("accepted AB1a / NB1c / controller / FSG code and products unchanged", c40),
    ("changed tracked files are only the declared ones", c41), ("synthetic known answers pass", c42),
    ("calibration-only raw-core statistics recompute", c43), ("oracle attrition is sequential and recomputes", c44),
    ("geometry-summary distributions recompute", c45), ("truth-class labels", c46)], start=1)]


def run_checks(ctx, quiet=False) -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": json.loads(json.dumps(detail, default=str))})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}" + ("" if ok else f" -- {str(detail)[:300]}"))
    return res


# ------------------------------------------------------------------ corruption suite
def mirror(run: Path, vis: Path, tmp: Path) -> tuple[Path, Path]:
    def copy_tree(src, dst):
        for p in src.rglob("*"):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            elif p.suffix in (".json", ".jsonl"):
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, q)
            else:
                q.parent.mkdir(parents=True, exist_ok=True)
                q.symlink_to(p.resolve())
    r, v = tmp / "r" / run.name, tmp / "v" / vis.name
    copy_tree(run, r)
    copy_tree(vis, v)
    return r, v


def edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]).copy() for k in z.files}


def save_npz(path: Path, d: dict) -> None:
    if path.exists() or path.is_symlink():
        path.unlink()
    np.savez_compressed(path, **d)


def edit_npz(path: Path, fn) -> None:
    d = load_npz(path)
    fn(d)
    save_npz(path, d)


def refreeze_corr(m: Path) -> None:
    edit_json(m / "oracle/correspondence-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))
    if (m / "geometry/geometry-freeze.json").exists():
        refreeze_geom(m)


def refreeze_geom(m: Path) -> None:
    def fn(d):
        d["files"].update({n: sha256(m / n) for n in d["files"]})
        d["correspondence_freeze_sha256"] = sha256(m / "oracle/correspondence-freeze.json")
    edit_json(m / "geometry/geometry-freeze.json", fn)
    edit_json(m / "evaluation/evaluation-summary.json", lambda d: d.update(
        geometry_freeze_sha256=sha256(m / "geometry/geometry-freeze.json")))


@contextlib.contextmanager
def patched(patches):
    saved = []
    for mod, name, fn in patches:
        M = _generator(mod)
        saved.append((M, name, getattr(M, name)))
        setattr(M, name, fn(getattr(M, name)))
    try:
        yield
    finally:
        for M, name, orig in reversed(saved):
            setattr(M, name, orig)


def regen_geometry(m: Path, ctx: Ctx, patches=(), c=None, calib_sha=None) -> None:
    """Rebuild the mirror's geometry with a (deliberately wrong) generator, self-consistently refrozen."""
    G = _generator("ab1b_geometry")
    c = c or ctx.c
    prod = load_npz(m / "oracle/oracle-correspondences.npz")
    with patched(patches):
        rays = G.left_core_rays(c)
        res = G.compute_epipolar(c, prod)
        summ = G.summarize(c, rays, res)
    save_npz(m / "geometry/left-core-rays.npz", rays)
    save_npz(m / "geometry/epipolar-result.npz", res)

    def fn(d):
        d.update(summ)
        d["inputs"]["correspondences"]["sha256"] = sha256(m / "oracle/oracle-correspondences.npz")
        if calib_sha:
            d["inputs"]["calibration"]["sha256"] = calib_sha
    edit_json(m / "geometry/geometry-summary.json", fn)
    refreeze_geom(m)


def regen_oracle(m: Path, ctx: Ctx, patches=(), c=None, calib_sha=None) -> bool:
    """Rebuild the mirror's product with a wrong oracle, refreeze, rebuild the geometry.  False when unchanged."""
    O = _generator("ab1b_oracle")
    with patched(patches):
        prod, summ = O.compute_oracle(c or ctx.c, ctx.ref)
    old = load_npz(m / "oracle/oracle-correspondences.npz")
    if all(np.array_equal(old[k], prod[k]) for k in prod) and c is None:
        return False
    save_npz(m / "oracle/oracle-correspondences.npz", prod)

    def fn(d):
        d.update(summ)
        if calib_sha:
            d["inputs"]["calibration"]["sha256"] = calib_sha
    edit_json(m / "oracle/oracle-summary.json", fn)
    refreeze_corr(m)
    regen_geometry(m, ctx, c=c, calib_sha=calib_sha)
    return True


def corruptions():
    def res_edit(fn, freeze=True):
        def f(m, v, c):
            edit_npz(m / "geometry/epipolar-result.npz", lambda z: fn(z, c))
            if freeze:
                refreeze_geom(m)
        return f

    def k_valid(c):
        return int(np.flatnonzero(c.res["valid_epi"])[len(np.flatnonzero(c.res["valid_epi"])) // 2])

    def bump(key, delta, col=None):
        def fn(z, c):
            k = k_valid(c)
            if col is None:
                z[key][k] = z[key][k] + delta
            else:
                z[key][k, col] = z[key][k, col] + delta
        return fn

    def rays_edit(fn):
        def f(m, v, c):
            edit_npz(m / "geometry/left-core-rays.npz", lambda z: fn(z, c))
            refreeze_geom(m)
        return f

    def gsum_edit(fn):
        def f(m, v, c):
            edit_json(m / "geometry/geometry-summary.json", fn)
            refreeze_geom(m)
        return f

    def prod_edit(fn, regen=False):
        def f(m, v, c):
            edit_npz(m / "oracle/oracle-correspondences.npz", lambda z: fn(z, c))
            refreeze_corr(m)
            if regen:
                regen_geometry(m, c)
            else:
                edit_json(m / "geometry/geometry-summary.json", lambda d: d["inputs"]["correspondences"].update(
                    sha256=sha256(m / "oracle/oracle-correspondences.npz")))
                refreeze_geom(m)
        return f

    def oracle_patch(mod_name, fn):
        def f(m, v, c):
            if not regen_oracle(m, c, [("ab1b_oracle", mod_name, fn)]):
                return {"not_applicable": f"the patched oracle rule {mod_name} leaves the canonical product unchanged"}
        return f

    def geom_patch(name, fn, during_checks=False):
        def f(m, v, c):
            regen_geometry(m, c, [("ab1b_geometry", name, fn)])
            if during_checks:
                return {"patch": [("ab1b_geometry", name, fn)]}
        return f

    def bad_theta(orig):
        def fn(d):
            t, p, s = orig(d)
            d = np.asarray(d, np.float64)
            return np.arctan2(np.hypot(d[..., 0], d[..., 1]), -d[..., 2]), p, s
        return fn

    def bad_phi(orig):
        def fn(d):
            t, p, s = orig(d)
            return t, -p, s
        return fn

    def calib_variant(kind):
        def f(m, v, c):
            G = _generator("fsg_geometry")
            cal = json.loads(json.dumps(c.c))
            if kind == "gaze":
                cal = G.make_calibration("full", YAW + 0.5, PITCH, cal["prescribed_vergence_distance_m"], ipd=cal["ipd_m"],
                                         head_r_wh=np.asarray(cal["head_R_wh"]), head_origin_w=np.asarray(cal["head_origin_w_m"]),
                                         tangent_frame="baseline_projected")
            else:
                a = 1e-4
                rot = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
                cal["eyes"][1]["R_hc"] = (rot @ np.asarray(cal["eyes"][1]["R_hc"])).tolist()
            sh = hashlib.sha256((json.dumps(cal, indent=1, sort_keys=True) + "\n").encode()).hexdigest()
            regen_oracle(m, c, c=cal, calib_sha=sh)
            edit_json(m / "geometry/geometry-freeze.json", lambda d: d["calibration_source"].update(sha256=sh))
            refreeze_geom(m)
        return f

    def rectified_core(m, v, c):
        sys.path.insert(0, str(TOOLS))
        import fsg_stereo as FS   # the corruption itself uses the planar rectification; the checked path must not
        G = _generator("ab1b_geometry")
        r = FS.rectification(c.c)
        x0, y0, cw, ch = map(int, r["crop_xywh"])
        uv = np.stack([r["map_Lx"][y0:y0 + ch, x0:x0 + cw], r["map_Ly"][y0:y0 + ch, x0:x0 + cw]], -1).astype(np.float64)

        def fn(z, cc):
            d = _generator("fsg_geometry").rays_h(c.c["eyes"][0], uv)
            th, ph, sg = G.theta_phi(d)
            _dg, tg, pg = G.gaze_angles(c.c)
            cu, cv = G.chart(th, ph, tg, pg)
            z.update(uv=uv, direction_h=d, theta=th, phi=ph, singular=sg, chart_u=cu, chart_v=cv, leverage=np.sin(th))
        edit_npz(m / "geometry/left-core-rays.npz", lambda z: fn(z, c))
        refreeze_geom(m)

    def static(name, text):
        return lambda m, v, c: {"static_extra": {name: text}}

    def gopen_edit(fn):
        def f(m, v, c):
            edit_json(m / "geometry/geometry-opened-files.json", fn)
            refreeze_geom(m)
        return f

    def reads_reference(d):
        p = str(AB1A / REF_REL)
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"].append(p)

    def truth_as_pepi(m, v, c):
        ve = c.res["valid_epi"].astype(bool)
        edit_npz(m / "geometry/epipolar-result.npz", lambda z: z["P_epi"].__setitem__(ve, c.evr["P_truth"][ve]))
        edit_json(m / "geometry/geometry-opened-files.json", reads_reference)
        refreeze_geom(m)

    def after_eval(m, v, c):
        edit_npz(m / "geometry/epipolar-result.npz", lambda z: bump("P_epi", 1e-3, 0)(z, c))

    def early_ref(m, v, c):
        def fn(d):
            ev = d["ordered_data_events"]
            t = next(p for p in ev if str(p).endswith("reference-observation.npz"))
            ev.remove(t)
            ev.insert(0, t)
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

    def ev_edit(fn):
        return lambda m, v, c: edit_json(m / "evaluation/evaluation-summary.json", fn)

    def evr_edit(key, delta):
        def f(m, v, c):
            k = k_valid(c)
            edit_npz(m / "evaluation/evaluation-result.npz", lambda z: z[key].__setitem__(k, z[key][k] + delta))
        return f

    def log(entry):
        def f(m, v, c):
            with open(m / "process-log.jsonl", "a") as fh:
                fh.write(json.dumps(entry) + "\n")
        return f

    def pixel(m, v, c):
        from PIL import Image
        p = v / "overview.png"
        img = Image.open(p.resolve()).convert("RGB")
        img.putpixel((3, 3), (255, 0, 0))
        p.unlink()
        img.save(p)

    def changed(extra):
        return lambda m, v, c: {"changed_files": c.changed_files + [extra]}

    def osum_edit(fn):
        def f(m, v, c):
            edit_json(m / "oracle/oracle-summary.json", fn)
            refreeze_corr(m)
        return f

    def k_corr(c):
        return len(c.prod["uv_R"]) // 2

    def prod_unfrozen(m, v, c):
        k = k_corr(c)
        edit_npz(m / "oracle/oracle-correspondences.npz", lambda z: z["uv_R"].__setitem__((k, 0), z["uv_R"][k, 0] + 1e-3))

    def swap(orig):
        return lambda cc, prod: tuple(reversed(orig(cc, prod)))

    def baseline_scale(s):
        def wrap(orig):
            def fn(cc):
                b, o_l, o_r = orig(cc)
                return (s * b if s < 0 else s, o_l, o_r)
            return fn
        return wrap

    run_cmd = ["tools/active_bootstrap/ab1b_run.py"]
    return [
        ("rectified core used instead of the raw core", ("09", "10"), rectified_core),
        ("cv2.stereoRectify invoked in the geometry module", ("08",),
         lambda m, v, c: (gopen_edit(lambda d: d["modules_loaded"].update(cv2=True))(m, v, c),
                          {"static_extra": {"ab1b_geometry.py": "import cv2\n_r = cv2.stereoRectify\n"}})[1]),
        ("SGBM invoked", ("07",), lambda m, v, c: (log({"command": "geometry", "status": "ok", "argv": run_cmd + [
            "geometry", "--run", "x"], "matcher": "sgbm"})(m, v, c),
            {"static_extra": {"ab1b_geometry.py": "import cv2\n_m = cv2.StereoSGBM_create\n"}})[1]),
        ("gaze moved (+0.5 deg yaw calibration, regenerated)", ("02", "10", "24"), calib_variant("gaze")),
        ("calibration changed (right camera rotated 1e-4 rad, regenerated)", ("02", "13"), calib_variant("rotate")),
        ("only the right nominal 256 core searched", ("11",),
         oracle_patch("inside_raster", lambda orig: lambda cc, uv: (uv[..., 0] >= ORIGIN) & (uv[..., 0] <= ORIGIN + CORE - 1)
                      & (uv[..., 1] >= ORIGIN) & (uv[..., 1] <= ORIGIN + CORE - 1))),
        ("same-instance visibility omitted", ("14",),
         oracle_patch("same_instance", lambda orig: lambda ids, vi, ui, left: np.ones_like(left, bool))),
        ("positive left instance rule dropped (instance 0 admitted)", ("12",),
         oracle_patch("left_catalog", lambda orig: lambda ids: np.ones_like(np.asarray(ids), bool))),
        ("uv_R rounded before the geometry stage", ("15", "13"),
         prod_edit(lambda z, c: z.__setitem__("uv_R", np.rint(z["uv_R"])), regen=True)),
        ("Position put into the correspondence product", ("16",),
         prod_edit(lambda z, c: z.__setitem__("xyz_h", c.evr["P_truth"]))),
        ("instance id put into the correspondence product", ("16",),
         prod_edit(lambda z, c: z.__setitem__("instance_id", c.evr["left_instance"]))),
        ("geometry opened reference-observation.npz", ("18", "19"), gopen_edit(reads_reference)),
        ("theta defined from -Z instead of +X (regenerated)", ("21",), geom_patch("theta_phi", bad_theta)),
        ("phi sign flipped (regenerated)", ("22",), geom_patch("theta_phi", bad_phi)),
        ("phi seam wrapping broken (regenerated; generator wrap)", ("23",),
         geom_patch("wrap_pi", lambda orig: lambda a: np.asarray(a, np.float64), during_checks=True)),
        ("left / right swapped (regenerated)", ("26", "28"), geom_patch("pair_rays", swap)),
        ("baseline direction flipped (regenerated)", ("20", "28"), geom_patch("baseline", baseline_scale(-1.0))),
        ("baseline length altered to 0.064 m (regenerated)", ("28",), geom_patch("baseline", baseline_scale(0.064))),
        ("one uv_L altered", ("09",), prod_edit(lambda z, c: z["uv_L"].__setitem__((k_corr(c), 0), z["uv_L"][k_corr(c), 0] + 1))),
        ("one uv_R altered (regenerated)", ("13",),
         prod_edit(lambda z, c: z["uv_R"].__setitem__((k_corr(c), 0), z["uv_R"][k_corr(c), 0] + 0.25), regen=True)),
        ("one theta altered", ("21",), res_edit(bump("theta_L", 1e-6))),
        ("one phi altered", ("22",), res_edit(bump("phi_R", 1e-6))),
        ("one delta_theta altered", ("26",), res_edit(bump("delta_theta", 1e-6))),
        ("one reconstructed XYZ point altered", ("28",), res_edit(bump("P_epi", 1e-3, 2))),
        ("P_epi replaced by Position truth", ("19", "28"), truth_as_pepi),
        ("ray-ray triangulation altered", ("29",), res_edit(bump("P_ray", 1e-3, 1))),
        ("geometry altered after evaluation (not refrozen)", ("32", "37"), after_eval),
        ("reference read before the geometry freeze", ("33",), early_ref),
        ("one error statistic altered", ("35",), ev_edit(lambda d: d["epipolar_vs_truth"]["error_3d_m"].update(
            median=d["epipolar_vs_truth"]["error_3d_m"]["median"] * 1.01 + 1e-9))),
        ("Blender command in the process log", ("03",), log({"command": "acquire", "status": "ok",
                                                             "argv": ["blender", "-b", "x.blend", "-P", "render.py"]})),
        ("controller command in the process log", ("06",), log({"command": "controller02", "status": "ok",
                                                                "argv": ["fov3d/experiments/classroom_oracle/controller02.py"]})),
        ("a second gaze executed", ("05",), log({"command": "oracle", "status": "ok",
                                                 "argv": run_cmd + ["oracle", "--run", "x", "--yaw", "75.25"]})),
        ("a visual pixel altered", ("39",), pixel),
        ("accepted FSG source modified", ("40",), changed("tools/fsg_geometry.py")),
        ("accepted AB1a source modified", ("40",), changed("tools/active_bootstrap/ab1a_stereo.py")),
        ("accepted NB1c source modified", ("40",), changed("tools/natural_bootstrap/nb1c_attention.py")),
        ("an undeclared tracked file changed", ("41",), changed("README.md")),
        ("kappa altered", ("31",), res_edit(lambda z, c: z["kappa"].__setitem__(k_valid(c), z["kappa"][k_valid(c)] * 1.01))),
        ("closest-ray gap altered", ("30",), res_edit(bump("ray_gap", 1e-6))),
        ("display chart altered", ("25",), rays_edit(lambda z, c: z["chart_u"].__setitem__((0, 0), z["chart_u"][0, 0] + 1e-6))),
        ("one raw-core ray direction altered", ("10",), rays_edit(lambda z, c: z["direction_h"].__setitem__(
            (0, 0), unit(z["direction_h"][0, 0] + np.array([0.0, 1e-6, 0.0]))))),
        ("theta_g altered", ("24",), gsum_edit(lambda d: d.update(theta_g_rad=d["theta_g_rad"] + 1e-6))),
        ("a raw-core statistic altered", ("43",), gsum_edit(lambda d: d["left_core"].update(
            min_angle_to_baseline_pole_deg=d["left_core"]["min_angle_to_baseline_pole_deg"] + 0.01))),
        ("a geometry distribution altered", ("45",), gsum_edit(lambda d: d["distributions"]["kappa"].update(
            median=d["distributions"]["kappa"]["median"] * 1.01))),
        ("a truth-class label altered", ("46",), gsum_edit(lambda d: d.update(truth=ORA))),
        ("oracle attrition altered", ("44",), osum_edit(lambda d: d["attrition"][1].update(remaining=d["attrition"][1]["remaining"] + 1))),
        ("correspondence product modified after its freeze", ("17",), prod_unfrozen),
        ("P_truth altered in the evaluation", ("34",), evr_edit("P_truth", 1e-3)),
        ("a reprojection residual altered", ("36",), evr_edit("reprojection_R_px", 0.1)),
        ("the AB1a comparison altered", ("38",), ev_edit(lambda d: d["ab1a_comparison"]["ab1a_planar_rectified"].update(
            reference_valid=7))),
        ("a synthetic known-answer case failed", ("42",),
         lambda m, v, c: edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))),
        ("an AB1a pin altered in the source manifest", ("01",),
         lambda m, v, c: edit_json(m / "source/ab1a-source-manifest.json", lambda d: d["pins"].update(
             {CALIB_REL: "0" * 64}))),
    ]


def corruption_suite(run: Path, vis: Path, base: Ctx) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    for name, targets, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="ab1b-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            probe = Ctx(m, v)
            probe.__dict__["changed_files"] = base.changed_files
            with contextlib.redirect_stdout(io.StringIO()):
                overrides = fn(m, v, probe) or {}
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A {list(targets)} {name}: {overrides['not_applicable']}")
                results.append({"name": name, "targets": list(targets), "not_applicable": overrides["not_applicable"]})
                continue
            total += 1
            ctx = Ctx(m, v)
            ctx.__dict__["changed_files"] = overrides.pop("changed_files", base.changed_files)
            patches = overrides.pop("patch", [])
            ctx.overrides = overrides
            with contextlib.redirect_stdout(io.StringIO()), patched(patches):
                res = run_checks(ctx, quiet=True)
            failed = sorted(r["check"] for r in res if not r["ok"])
            hit = any(t in failed for t in targets)
            caught += hit
            results.append({"name": name, "targets": list(targets), "caught": hit, "failed": failed})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} {list(targets)} {name} (failed: {failed})")
    return caught, total, results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    base = Ctx(run, vis)
    res = run_checks(base)
    npass = sum(r["ok"] for r in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1B_CHECKS_PASS")
    out = {"schema": "AB1b-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis, base)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1B_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
