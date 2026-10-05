"""Active Bootstrap-1d3: fail-capable checker of the one-shot SGBM viability test.

Contract: docs/active-bootstrap/ab1d3-sgbm-viability-contract.md, sections 19-20.

    .venv/bin/python tools/active_bootstrap/check_ab1d3.py --run RUN --visuals VIS [--corruptions] [--write-summary]

The checker keeps its own literal pins and constants (here and in ``check_ab1d3_core``).  It re-assembles the whole
frozen matcher from literals and recomputes it on the 4096-spp RGB (own rectification, own SGBM objects, own refinement,
own validity terms), re-implements the raw-core adapter (own raw -> rectified map, footprint, bilinear weights, a linear
solve for the inverse), recomputes the serviceable set, the angular and pixel-equivalent errors (own rays and own
epipolar line), the metric precision and effective coverage, the AB1d2 comparison and the spatial statistics, audits the
recorded OpenCV calls, the guard records, the freezes and the run order, scans the sources, and regenerates every
figure.  ``--corruptions`` injects genuine defects into mirrors of the run and visuals (mutated configurations are
computed inside the temporary mirrors only, to show they are detected; their outputs are discarded and never reported),
after an unmodified-mirror null probe passes every check.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap", HERE.parent / "visual_language"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import check_ab1d3_core as K  # noqa: E402  (the checker's own independent primitives)

PREFIX = "[ab1d3-check]"

# ------------------------------------------------------------------ the checker's own literals (contract section 19)
BASE = "56606b8d4a51361f4fb729306ed73bf23b8ffaf3"
AB1D2_ACCEPTANCE = "f65c6ac8344bfcfb0491888bf8608471d2452f61"
CONTRACT = "492232e810b75099708b466a1f3b603f4f1dbba9"
BRANCH = "active-bootstrap/ab1d3-sgbm-viability"
GAZES = ("gaze-1", "gaze-2", "gaze-3")
CORE, ORIGIN, RAW = 256, 192, 640
SHARED = Path("/home/lvelho/rd/f3d-vision")
A1D2 = SHARED / "previews/active-bootstrap/ab1d2-4096spp-observation-quality"
A1C = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
OBS = {
    "gaze-1": ("ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
               "9d653bd1fa1bb2d1d59847b0a55c1b43603b5628beb3bc70f29975d4e57bf02c"),
    "gaze-2": ("ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
               "3046cc66f67494b5f639380c46f25672c2259684f28511ba5366f872986e4bba"),
    "gaze-3": ("085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd",
               "fd9ecd4ed94b8c6fdc91a1dd7501840da2934b335387515b10098dc69497ce75"),
}
A1D2_OBS_FREEZE = "7c8ed0a3a65189fd8057c980ef9a3c1968e83ade9955dc1625503a6d6df47290"
A1D2_MANIFEST = "5ace0ab7764e40e9ab673271c829cb77363d7787fcc794a79aa63d5c580c6cbd"
A1D2_RENDER_CONTROL = "9b982634395c2f9c99e5964f874a98a620848e80c69b05d0c179bdb6f08e993c"
A1D2_EVAL = {"gaze-1": "ee844c5a2f7666a6be3851a505321b12c04cb147146b49610abfdf5c0038daa0",
             "gaze-2": "8ac6781a053550a5803632c3a37d8a5f0dde829e071d01bf06d5889340e2e25b",
             "gaze-3": "995fc07ee8e76cf00cbfa7f7f7769634e6bf9fd04680f9d00912cc3ae0286eb4"}
A1C_MANIFEST = "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a"
BENCH = {
    "oracle/gaze-1/oracle-correspondences.npz": "e83eaa7b537abaa4def50def64d0d36bf034d270baa3f4e7ce6cfb0a7512b4a6",
    "oracle/gaze-2/oracle-correspondences.npz": "fd4568d59f3b7a40aef6c11442961749e45a8c3b6c1b1fa53c8934dd636b8831",
    "oracle/gaze-3/oracle-correspondences.npz": "67d433311f1f940637573c9135d6947bad8363411cb45e52412f070874c20c73",
    "spherical/gaze-1/epipolar-result.npz": "3e5024f3a75a34819f742c231b3b448ac6b8486a840f17c9c5f780798c52cd98",
    "spherical/gaze-2/epipolar-result.npz": "d2306f9c200a11e749bf59d71b535a2f4c8a32e08850618901b9402412fee4e2",
    "spherical/gaze-3/epipolar-result.npz": "f1de4f1d6be91880067446ad8a104f875dd7e4757c2c5176be2410ed92d0b561",
    "observations/gaze-1/evaluation_only/reference-observation.npz":
        "7c458254960befefbfef160e0904dc8ab9c34bb1d3791d8f59fd55403b323f2e",
    "observations/gaze-2/evaluation_only/reference-observation.npz":
        "c8b1833ef4df720a0252b89c6886ba6788be4d94f877cfd8ba0bc4781b9e47b6",
    "observations/gaze-3/evaluation_only/reference-observation.npz":
        "740d7ad78f9afc7eb867e20df186bf40b964e31a840a5ba2e85dd4bdcd81e5d0",
}
SOURCES = {
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/active_bootstrap/ab1a_stereo.py": "c0238a7318c4a9c034c4a679104ae46cfd7504bf204935e2af15707b10f07f65",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1c_planar.py": "1528ee92af48c5a13b621d300fe0a78dedc57f27181959d40505f2f9b19e6227",
    "tools/active_bootstrap/ab1d_match.py": "dd1ac243d1da09635e12edb87d0d402f169d49e016ac3f35ed5d1572ec255ffd",
    "tools/active_bootstrap/ab1d_run.py": "9df2981ba55041e7cebdb34061b5cb565d65734b78962318931b4dcb482a7292",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
}
TOOLS = ("ab1d3_spec.py", "ab1d3_sgbm.py", "ab1d3_run.py", "ab1d3_synthetic.py", "ab1d3_visuals.py", "check_ab1d3.py",
         "check_ab1d3_core.py")
DECLARED = ({"docs/active-bootstrap/ab1d3-sgbm-viability-contract.md",
             "docs/active-bootstrap/ab1d3-sgbm-viability-report.md",
             "tools/repository/check_repository_layout.py"} | {f"tools/active_bootstrap/{n}" for n in TOOLS})
CANONICAL = ("source", "sgbm", "raw-core-adapter", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate")
COMMANDS = ("source", "preflight", "sgbm", "raw-core-adapter", "freeze-correspondence", "spherical", "freeze-geometry",
            "evaluate", "visualize")
FIGURES = ("overview.png", "sgbm-vs-primitive.png", "disparity-validity.png", "metric-error.png", "attrition.png")
ORA_B, DER_B, REF_B = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
BADGES = {"overview.png": [ORA_B, DER_B, REF_B], "sgbm-vs-primitive.png": [DER_B, REF_B],
          "disparity-validity.png": [ORA_B, DER_B], "metric-error.png": [DER_B, REF_B], "attrition.png": [DER_B, REF_B]}
PX_BINS = (0.10, 0.25, 0.50, 1.00)
CAT_PX = (10.0, 100.0)
METRIC_M = (0.012, 0.025, 0.050, 0.100)
Z_EPS = 1e-12
PREFLIGHT_MIN_CASES = 38
CORR_FILES = ("sgbm-record.npz", "sgbm-summary.json", "sgbm-calls.json", "sgbm-opened-files.json")
ADAPT_FILES = ("adapter-record.npz", "sgbm-correspondences.npz", "adapter-summary.json", "adapter-opened-files.json")
GEOM_FILES = ("left-core-rays.npz", "epipolar-result.npz", "spherical-summary.json", "spherical-opened-files.json")
_CACHE: dict = {}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def npz(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def jload(path):
    return json.loads(Path(path).read_text())


def qof(a, mask=None) -> dict | None:
    a = np.asarray(a, np.float64)
    if mask is not None:
        a = a[np.asarray(mask, bool)]
    a = a[np.isfinite(a)].ravel()
    if a.size == 0:
        return None
    qs = {"min": 0.0, "p05": 0.05, "p10": 0.10, "p25": 0.25, "median": 0.5, "p75": 0.75, "p90": 0.90, "p95": 0.95,
          "p99": 0.99, "max": 1.0}
    return {k: float(np.quantile(a, v)) for k, v in qs.items()} | {"count": int(a.size)}


def qmatch(stored: dict | None, own: dict | None, rel=1e-9, ab=1e-12) -> bool:
    if stored is None or own is None:
        return stored is None and own is None
    return stored.get("count") == own.get("count") and all(
        abs(stored[k] - own[k]) <= ab + rel * abs(own[k]) for k in own if k != "count")


def frac(n, d) -> float | None:
    return float(n / d) if d else None


def close(a, b, tol=1e-12) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)


class Ctx:
    """Lazy access to one run (or a corruption mirror), its visuals and (overridable) accepted inputs."""

    def __init__(self, run: Path, vis: Path, overrides: dict | None = None) -> None:
        self.run, self.vis, self.overrides = run, vis, overrides or {}
        self._m: dict = {}

    def c(self, key, fn):
        if key not in self._m:
            self._m[key] = fn()
        return self._m[key]

    def j(self, rel):
        return self.c(("j", rel), lambda: jload(self.run / rel))

    def n(self, rel):
        return self.c(("n", rel), lambda: npz(self.run / rel))

    def calib_path(self, g) -> Path:
        return Path(self.overrides.get("calib", {}).get(g, A1D2 / f"observations/{g}/acquisition/calibration.json"))

    def rgb_path(self, g) -> Path:
        return Path(self.overrides.get("rgb", {}).get(g, A1D2 / f"observations/{g}/acquisition/rgb-observation.npz"))

    def calib(self, g):
        return self.c(("calib", g), lambda: jload(self.calib_path(g)))

    def rgb(self, g):
        return self.c(("rgb", g), lambda: npz(self.rgb_path(g)))

    def src(self, name: str) -> str:
        return (HERE / name).read_text() + self.overrides.get("static_extra", {}).get(name, "")

    def rrel(self, p: str) -> str:
        rp = str(Path(p))
        for root in (str(self.run), str(self.overrides.get("orig_run", self.run))):
            if rp.startswith(root + "/"):
                return "RUN/" + rp[len(root) + 1:]
        return rp

    @property
    def log(self) -> list[dict]:
        return self.c("log", lambda: [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x])

    def sg(self, g):
        return self.n(f"sgbm/{g}/sgbm-record.npz")

    def ad(self, g):
        return self.n(f"correspondence/{g}/adapter-record.npz")

    def prod(self, g):
        return self.n(f"correspondence/{g}/sgbm-correspondences.npz")

    def geo(self, g):
        return self.n(f"spherical/{g}/epipolar-result.npz")

    def evr(self, g):
        return self.n(f"evaluation/{g}/evaluation-result.npz")

    def bench(self, g, kind):
        if "bench_data" in self.overrides:
            return self.overrides["bench_data"][g][kind]
        rel = {"oracle": f"oracle/{g}/oracle-correspondences.npz", "perfect": f"spherical/{g}/epipolar-result.npz",
               "position": f"observations/{g}/evaluation_only/reference-observation.npz"}[kind]
        return self.c(("bench", g, kind), lambda: npz(A1C / rel))

    def prim(self, g):
        if "prim_data" in self.overrides:
            return self.overrides["prim_data"][g]
        return self.c(("prim", g), lambda: npz(A1D2 / f"evaluation/{g}/evaluation-result.npz"))

    def own_sgbm(self, g):
        def f():
            key = ("own_sgbm", sha256(self.calib_path(g)), sha256(self.rgb_path(g)))
            if key not in _CACHE:
                _CACHE[key] = K.own_sgbm(self.calib(g), self.rgb(g))
            return _CACHE[key]
        return self.c(("own_sgbm", g), f)

    def own_rect(self, g):
        return self.c(("own_rect", g), lambda: K.own_rectify(self.calib(g)))


# ------------------------------------------------------------------ own geometry (independent)
def own_rays(k, r_hc, uv) -> np.ndarray:
    uv = np.asarray(uv, float)
    hom = np.vstack([uv[:, 0], uv[:, 1], np.ones(len(uv))])
    d = (np.asarray(r_hc, float) @ np.linalg.solve(np.asarray(k, float), hom)).T
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def own_theta(d) -> np.ndarray:
    return np.arctan2(np.sqrt(d[:, 1] ** 2 + d[:, 2] ** 2), d[:, 0])


def own_phi(d) -> np.ndarray:
    return np.arctan2(d[:, 1], -d[:, 2])


def own_project(k, r_hc, d) -> np.ndarray:
    x = (np.asarray(k, float) @ (np.asarray(r_hc, float).T @ np.asarray(d, float).T)).T
    return x[:, :2] / x[:, 2:3]


def own_pixel_equivalent(c, idx, uv_sgbm_r, uv_oracle_r) -> dict:
    """Own epipolar line (plane normal b x d_L, l = K_R^-T R^T n, q_inf = proj_R(d_L), t oriented to increasing
    theta_R), ORACLE-ON-CURVE (theta_R oracle at phi_L) and the 1-px theta step there."""
    el, er = c["eyes"]
    kl, kr = np.asarray(el["K"], float), np.asarray(er["K"], float)
    rl, rr = np.asarray(el["R_hc"], float), np.asarray(er["R_hc"], float)
    rows, cols = idx // CORE, idx % CORE
    uv_l = np.stack([cols + ORIGIN, rows + ORIGIN], -1).astype(float)
    dl = own_rays(kl, rl, uv_l)
    ph_l = own_phi(dl)
    n = np.cross(np.array([1.0, 0.0, 0.0]), dl)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    l = np.linalg.solve(kr.T, (rr.T @ n.T)).T
    q_inf = own_project(kr, rr, dl)
    t = np.stack([l[:, 1], -l[:, 0]], -1)
    t /= np.linalg.norm(t, axis=1, keepdims=True)

    def theta_at(q):
        return own_theta(own_rays(kr, rr, q))
    sgn = np.sign(theta_at(q_inf + t) - theta_at(q_inf - t))
    t *= sgn[:, None]
    th_or = theta_at(uv_oracle_r)
    d_oc = np.stack([np.cos(th_or), np.sin(th_or) * np.sin(ph_l), -np.sin(th_or) * np.cos(ph_l)], -1)
    q_oc = own_project(kr, rr, d_oc)
    s_oc = np.sum((q_oc - q_inf) * t, -1)
    scale = theta_at(q_inf + (s_oc + 0.5)[:, None] * t) - theta_at(q_inf + (s_oc - 0.5)[:, None] * t)
    e_th = theta_at(uv_sgbm_r) - th_or
    return {"e_theta": e_th, "scale": scale, "e_px": e_th / scale, "theta_oracle": th_or}


def own_triangulate(c, uv_l, uv_r) -> np.ndarray:
    el, er = c["eyes"]
    dl = own_rays(el["K"], el["R_hc"], uv_l)
    dr = own_rays(er["K"], er["R_hc"], uv_r)
    ol, orr = np.asarray(el["centre_h_m"], float), np.asarray(er["centre_h_m"], float)
    w0 = ol - orr
    b = np.sum(dl * dr, -1)
    dd, ee = dl @ w0, dr @ w0
    den = 1 - b * b
    s, t = (b * ee - dd) / den, (ee - b * dd) / den
    return (ol + s[:, None] * dl + orr + t[:, None] * dr) / 2


def own_world_to_head(c, xyz) -> np.ndarray:
    return (np.asarray(xyz, float) - np.asarray(c["head_origin_w_m"], float)) @ np.asarray(c["head_R_wh"], float)


def own_classify(path: str, run: str) -> dict:
    a1c, a1d2 = str(A1C), str(A1D2)
    return {"position": "/evaluation_only/" in path or path.endswith(".exr") or path.endswith("reference-observation.npz"),
            "oracle": "oracle" in path.rsplit("/", 1)[-1] or path.startswith(a1c + "/oracle/"),
            "evaluation": path.startswith(a1c + "/") or any(path.startswith(a1d2 + "/" + s + "/") for s in
                                                             ("evaluation", "match", "spherical", "freeze"))}


def own_truth_reads(events: list[dict], run: str) -> dict:
    out = {"position": 0, "oracle": 0, "evaluation": 0}
    for e in events:
        if e.get("event") != "open":
            continue
        for k, v in own_classify(e["path"], run).items():
            out[k] += int(v)
    return out


# ------------------------------------------------------------------ checks: provenance (contract section 19)
def c01(x):
    remote = git("remote", "get-url", "origin")
    anc = lambda a: subprocess.run(["git", "merge-base", "--is-ancestor", a, "HEAD"], cwd=REPO).returncode == 0  # noqa
    rep = (REPO / "docs/active-bootstrap/ab1d2-4096spp-observation-quality-report.md").read_text()
    contract_ok = CONTRACT is not None and anc(CONTRACT) and not git("diff", "--name-only", CONTRACT, "HEAD", "--",
                                                                       "docs/active-bootstrap/ab1d3-sgbm-viability-contract.md")
    p = {"canonical_remote": remote.rstrip("/").removesuffix(".git").endswith("visgraf/f3d-vision"),
         "base_ancestor": anc(BASE), "ab1d2_acceptance_ancestor": anc(AB1D2_ACCEPTANCE),
         "ab1d2_accepted": "ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED" in rep and "**Status: ACCEPTED.**" in rep,
         "contract_committed_before_and_unchanged": contract_ok}
    return all(p.values()), p


def c02(x):
    bad = {p: sha256(x.overrides.get("code", {}).get(p, REPO / p)) for p, h in SOURCES.items()
           if sha256(x.overrides.get("code", {}).get(p, REPO / p)) != h}
    changed = set(git("diff", "--name-only", BASE, "--", *SOURCES).split())
    return not bad and not changed, {"mismatch": bad, "changed_since_base": sorted(changed)}


def c03(x):
    p = {}
    for g in GAZES:
        p[g] = {"calibration": sha256(x.calib_path(g)) == OBS[g][0], "rgb": sha256(x.rgb_path(g)) == OBS[g][1]}
    fz = jload(A1D2 / "freeze/observation-freeze.json")
    man = jload(A1D2 / "manifest.json")["files"]
    ctl = jload(A1D2 / "observations/render-control.json")
    p["observation_freeze"] = sha256(A1D2 / "freeze/observation-freeze.json") == A1D2_OBS_FREEZE and all(
        fz["rgb_observations"][g] == OBS[g][1] and fz["calibrations"][g] == OBS[g][0] for g in GAZES) and fz["spp"] == 4096
    p["ab1d2_manifest"] = sha256(A1D2 / "manifest.json") == A1D2_MANIFEST and all(
        man[f"observations/{g}/acquisition/rgb-observation.npz"] == OBS[g][1] for g in GAZES)
    p["render_control"] = sha256(A1D2 / "observations/render-control.json") == A1D2_RENDER_CONTROL and bool(ctl["ok"])
    ok = all(all(v.values()) if isinstance(v, dict) else v for v in p.values())
    return ok, p


def c04(x):
    man = jload(A1C / "manifest.json")["files"]
    a1d2_man = jload(A1D2 / "manifest.json")["files"]
    p = {"ab1c_manifest": sha256(A1C / "manifest.json") == A1C_MANIFEST,
         "bench_in_manifest": all(man.get(k) == h for k, h in BENCH.items()),
         "bench_files": all(sha256(A1C / k) == h for k, h in BENCH.items()),
         "ab1d2_eval": all(sha256(A1D2 / f"evaluation/{g}/evaluation-result.npz") == h
                           and a1d2_man[f"evaluation/{g}/evaluation-result.npz"] == h for g, h in A1D2_EVAL.items())}
    sm = x.j("source/source-manifest.json")
    p["source_manifest_identity"] = all(sm["identity"].values()) and sm["base_commit"] == BASE \
        and sm["ab1d2_acceptance"] == AB1D2_ACCEPTANCE and sm["contract_commit"] == CONTRACT
    p["source_manifest_pins"] = sm["a1c_benchmark_pins"] == {k: v for k, v in BENCH.items()} | {
        k: v for k, v in sm["a1c_benchmark_pins"].items() if k not in BENCH} and all(
        sm["observations"][f"observations/{g}/acquisition/rgb-observation.npz"] == OBS[g][1] for g in GAZES)
    return all(p.values()), p


# ---- no new observation
RENDER_MODULES = ("bpy", "render_foveated", "ab1d2_render", "ab1a_render", "ab1c_render", "classroom_oracle1_render",
                  "bl_common")


def render_scan(src: str) -> list[str]:
    """Imports of render code, and any subprocess call that is not git."""
    out = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            out += [f"import {m}" for m in mods if m.split(".")[0] in RENDER_MODULES]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
            arg = ast.get_source_segment(src, node.args[0]) if node.args else ""
            if not arg.startswith('["git"'):
                out.append(f"subprocess {arg[:40]}")
    return out


def c05(x):
    cmds = [e["command"] for e in x.log]
    files = [str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()]
    new_obs = [f for f in files if f.endswith((".exr", "rgb-observation.npz", ".blend")) and "preflight/guard-probe" not in f]
    scan = {n: render_scan(x.src(n)) for n in ("ab1d3_run.py", "ab1d3_sgbm.py", "ab1d3_spec.py")}
    p = {"commands_known": set(cmds) <= set(COMMANDS), "no_new_observation_files": not new_obs,
         "no_render_code": not any(scan.values()),
         "inputs_are_ab1d2": all(x.j(f"sgbm/{g}/sgbm-summary.json")["inputs"]["rgb_observation"]["sha256"] == OBS[g][1]
                                 for g in GAZES)}
    return all(p.values()), p | {"new": new_obs[:5], "scan": scan}


# ---- SGBM configuration
def c06(x):
    bad = {g: K.audit_calls(x.j(f"sgbm/{g}/sgbm-calls.json")) for g in GAZES}
    return not any(bad.values()), bad


def c07(x):
    bad = {g: K.audit_summary(x.j(f"sgbm/{g}/sgbm-summary.json")["accepted_summary"]) for g in GAZES}
    import ab1d3_spec as SP
    lit = {"mode_value": 2, "blockSize": 5, "P1": 200, "P2": 800, "preFilterCap": 31, "uniquenessRatio": 10,
           "disp12MaxDiff": -1, "speckleWindowSize": 0, "speckleRange": 1, "minDisparity_left": 0, "z_rect_m": [0.75, 4.5],
           "lr_tolerance_px": 1.0, "min_local_std_u8": 0.5,
           "refinement": {"iterations": 3, "max_step_px": 0.5, "max_total_px": 0.75}, "identity_guard": None}
    spec_ok = {k: SP.SGBM.get(k) == v for k, v in lit.items()}
    stored = all(x.j(f"sgbm/{g}/sgbm-summary.json")["sgbm"] == SP.SGBM for g in GAZES)
    return not any(bad.values()) and all(spec_ok.values()) and stored, {"summary": bad, "spec": spec_ok,
                                                                          "stored_config_equals_spec": stored}


def c08(x):
    out, ok = {}, True
    for g in GAZES:
        bad, det = K.audit_record(x.calib(g), x.rgb(g), x.sg(g), x.own_sgbm(g))
        own = x.own_sgbm(g)
        calls = x.j(f"sgbm/{g}/sgbm-calls.json")["calls"]["StereoSGBM_create"]
        own_hash = [hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + np.ascontiguousarray(a).tobytes()
                                   ).hexdigest() for a in (own["gray"]["L"], own["gray"]["R"])]
        inputs = len(calls) == 2 and calls[0]["compute"][0]["left_sha256"] == own_hash[0] \
            and calls[0]["compute"][0]["right_sha256"] == own_hash[1]
        if not inputs:
            bad.append("SGBM inputs are not the own linear_to_u8 gray of the remapped 4096 RGB")
        out[g] = {"failures": bad, "detail": det}
        ok &= not bad
    return ok, out


# ---- truth firewall
def guard_check(x, rel, want) -> dict:
    rec = x.j(rel)
    reads = {x.rrel(p) for p in rec["data_reads"]}
    own = own_truth_reads(rec["events"], str(x.overrides.get("orig_run", x.run)))
    return {"reads_exact": reads == want, "violations_0": not rec["violations"], "own_truth_reads_0": not any(own.values()),
            "stored_truth_reads_0": not any(rec.get(k, 0) for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                                    "evaluation_or_matcher_product_reads")),
            "modules": not any(rec["modules_loaded"].values())}


def c09(x):
    p = {g: guard_check(x, f"sgbm/{g}/sgbm-opened-files.json",
                        {str((A1D2 / f"observations/{g}/acquisition/calibration.json").resolve()),
                         str((A1D2 / f"observations/{g}/acquisition/rgb-observation.npz").resolve())}) for g in GAZES}
    return all(all(v.values()) for v in p.values()), p


def c10(x):
    p = {g: guard_check(x, f"correspondence/{g}/adapter-opened-files.json",
                        {str((A1D2 / f"observations/{g}/acquisition/calibration.json").resolve()),
                         f"RUN/sgbm/{g}/sgbm-record.npz"}) for g in GAZES}
    return all(all(v.values()) for v in p.values()), p


def c11(x):
    p = {}
    for g in GAZES:
        rec = x.j(f"spherical/{g}/spherical-opened-files.json")
        reads = {x.rrel(q) for q in rec["data_reads"]}
        own = own_truth_reads(rec["events"], str(x.run))
        p[g] = {"reads_exact": reads == {str((A1D2 / f"observations/{g}/acquisition/calibration.json").resolve()),
                                         f"RUN/correspondence/{g}/sgbm-correspondences.npz"},
                "violations_0": not rec["violations"], "own_truth_reads_0": not any(own.values()),
                "no_cv2_no_matcher": not any(rec["modules_loaded"].values())}
    return all(all(v.values()) for v in p.values()), p


# ---- rectification
def c12(x):
    p = {}
    for g in GAZES:
        sg, own = x.sg(g), x.own_sgbm(g)
        r = own["rect"]
        p[g] = {"R1": np.allclose(sg["R1"], r["R1"], atol=1e-12, rtol=0), "R2": np.allclose(sg["R2"], r["R2"], atol=1e-12, rtol=0),
                "P1": np.allclose(sg["P1"], r["P1"], atol=1e-9, rtol=0), "P2": np.allclose(sg["P2"], r["P2"], atol=1e-9, rtol=0),
                "Q": np.allclose(sg["Q_full"], r["Q"], atol=1e-9, rtol=0),
                "baseline_sign_positive_disparity": float(sg["P2"][0, 3]) < 0 and abs(float(sg["P2"][1, 3])) < 1e-7,
                "full_window": [int(a) for a in sg["crop_xywh"]] == [0, 0, RAW, RAW] and sg["disparity_px"].shape == (RAW, RAW),
                "num_disparities_112": int(sg["num_disparities"]) == 112 and r["nd"] == 112,
                "support_equal": bool(np.array_equal(sg["term_support_left"], own["term_support_left"])),
                "roi_equal": [int(a) for a in sg["valid_disparity_roi"]] == list(r["roi"])}
    return all(all(v.values()) for v in p.values()), p


# ---- raw adapter
def own_adapter(x, g) -> dict:
    def f():
        r = x.own_rect(g)
        sg = x.sg(g)
        return K.own_adapt(x.calib(g), r["R1"], r["R2"], r["P1"], r["P2"], sg["disparity_px"], sg["valid"])
    return x.c(("own_adapt", g), f)


def c13(x):
    import ab1b_geometry as BG
    p = {}
    for g in GAZES:
        own, prod, ad = own_adapter(x, g), x.prod(g), x.ad(g)
        idx = prod["left_core_row"].astype(np.int64) * CORE + prod["left_core_col"].astype(np.int64)
        want = np.nonzero(own["valid"])[0]
        same_set = np.array_equal(idx, want)
        diff = float(np.max(np.abs(prod["uv_R"] - own["uv_R"][want]))) if same_set and want.size else None
        try:
            BG.validate_product(prod)
            schema = True
        except ValueError:
            schema = False
        uv_l = np.stack([idx % CORE + ORIGIN, idx // CORE + ORIGIN], -1).astype(float)
        p[g] = {"valid_set_equal": same_set, "uv_R_max_diff_px": diff,
                "uv_R_within_1e-9": diff is not None and diff <= 1e-9, "accepted_validator": schema,
                "uv_L_exact": bool(np.array_equal(prod["uv_L"], uv_l)),
                "uv_R_inside": bool(((prod["uv_R"] >= 0) & (prod["uv_R"] <= RAW - 1)).all()),
                "record_valid_equals_product": bool(np.array_equal(np.nonzero(ad["valid_adapter"])[0], idx)),
                "count": int(idx.size)}
    return all(v["valid_set_equal"] and v["uv_R_within_1e-9"] and v["accepted_validator"] and v["uv_L_exact"]
               and v["uv_R_inside"] and v["record_valid_equals_product"] for v in p.values()), p


def c14(x):
    """Strict interpolation validity: every product sample's four footprint pixels are fully SGBM-valid; and the own
    raw -> rectified map agrees with the adapter record."""
    p = {}
    for g in GAZES:
        own, ad, sg, prod = own_adapter(x, g), x.ad(g), x.sg(g), x.prod(g)
        idx = prod["left_core_row"].astype(np.int64) * CORE + prod["left_core_col"].astype(np.int64)
        u = own["uvrect_L"][idx]
        x0, y0 = np.floor(u[:, 0]).astype(int), np.floor(u[:, 1]).astype(int)
        v = sg["valid"]
        ok4 = (x0 >= 0) & (x0 <= RAW - 2) & (y0 >= 0) & (y0 <= RAW - 2)
        xs, ys = np.where(ok4, x0, 0), np.where(ok4, y0, 0)
        allv = ok4 & v[ys, xs] & v[ys, xs + 1] & v[ys + 1, xs] & v[ys + 1, xs + 1]
        p[g] = {"all_footprints_valid": bool(allv.all()), "violations": int((~allv).sum()),
                "uvrect_L_max_diff_px": float(np.max(np.abs(own["uvrect_L"] - ad["uvrect_L"]))),
                "footprint_rule_recorded": bool(np.array_equal(own["footprint_valid"], ad["footprint_full_valid"]))}
    return all(v["all_footprints_valid"] and v["uvrect_L_max_diff_px"] <= 1e-9 and v["footprint_rule_recorded"]
               for v in p.values()), p


TERMS = K.LIT_TERMS


def c15(x):
    """Attrition recomputed from own footprints and the record's own term rasters."""
    p = {}
    for g in GAZES:
        own, sg = own_adapter(x, g), x.sg(g)
        u = own["uvrect_L"]
        x0, y0 = np.floor(u[:, 0]).astype(int), np.floor(u[:, 1]).astype(int)
        ok4 = own["rectifiable"]
        xs, ys = np.where(ok4, x0, 0), np.where(ok4, y0, 0)
        run = ok4.copy()
        want = {"raw_core": CORE * CORE, "rectifiable": int(ok4.sum())}
        for t in TERMS:
            a = np.asarray(sg[t], bool)
            run &= a[ys, xs] & a[ys, xs + 1] & a[ys + 1, xs] & a[ys + 1, xs + 1]
            want["footprint_" + t] = int(run.sum())
        want["raw_inside"] = int(own["valid"].sum())
        stored = {a["stage"]: a["remaining"] for a in x.j(f"correspondence/{g}/adapter-summary.json")["attrition"]}
        diff = {k: (stored.get(k), v) for k, v in want.items() if stored.get(k) != v}
        mono = all(a["remaining"] >= b["remaining"] for a, b in zip(x.j(f"correspondence/{g}/adapter-summary.json")["attrition"],
                                                                    x.j(f"correspondence/{g}/adapter-summary.json")["attrition"][1:]))
        p[g] = {"diff": diff, "monotone": mono}
    return all(not v["diff"] and v["monotone"] for v in p.values()), p


def c16(x):
    """Epipolar consistency of the adapted correspondences and the secondary planar-Q diagnostic (truth-free)."""
    p = {}
    for g in GAZES:
        geo, prod, sg = x.geo(g), x.prod(g), x.sg(g)
        c = x.calib(g)
        el, er = c["eyes"]
        dl, dr = own_rays(el["K"], el["R_hc"], prod["uv_L"]), own_rays(er["K"], er["R_hc"], prod["uv_R"])
        phr = np.abs(np.angle(np.exp(1j * (own_phi(dr) - own_phi(dl)))))
        p[g] = {"phi_residual_max_rad": float(phr.max()) if phr.size else None,
                "stored_phi_residual_max": float(np.nanmax(np.abs(geo["phi_residual"]))) if phr.size else None,
                "secondary_planar_q_max_m": x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["secondary"][
                    "planar_q_vs_spherical_m"]["max"]}
    ok = all(v["phi_residual_max_rad"] is not None and v["phi_residual_max_rad"] <= 1e-9
             and v["secondary_planar_q_max_m"] <= 1e-6 for v in p.values())
    return ok, p


# ---- freeze
def c17(x):
    fz = x.j("correspondence/correspondence-freeze.json")
    want = {f"sgbm/{g}/{n}" for g in GAZES for n in CORR_FILES} | {f"correspondence/{g}/{n}" for g in GAZES
                                                                    for n in ADAPT_FILES}
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    order = [e["command"] for e in x.log if e["status"] == "ok"]
    o = lambda c: order.index(c) if c in order else 10 ** 6  # noqa: E731
    pre = all(not any(own_truth_reads(x.j(rel)["events"], str(x.run)).values()) for rel in
              [f"sgbm/{g}/sgbm-opened-files.json" for g in GAZES] + [f"correspondence/{g}/adapter-opened-files.json" for g in GAZES])
    p = {"files_complete": set(fz["files"]) == want, "hashes": not bad,
         "before_spherical_and_evaluation": o("freeze-correspondence") < o("spherical") < o("evaluate"),
         "no_truth_before_freeze": pre}
    return all(p.values()), p | {"mismatch": bad[:5]}


def c18(x):
    fz = x.j("freeze/geometry-freeze.json")
    want = {f"correspondence/{g}/sgbm-correspondences.npz" for g in GAZES} | {f"spherical/{g}/{n}" for g in GAZES
                                                                             for n in GEOM_FILES}
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    cfz_h = sha256(x.run / "correspondence/correspondence-freeze.json")
    order = [e["command"] for e in x.log if e["status"] == "ok"]
    o = lambda c: order.index(c) if c in order else 10 ** 6  # noqa: E731
    p = {"files_complete": set(fz["files"]) == want, "hashes": not bad,
         "chained_to_correspondence_freeze": fz["correspondence_freeze_sha256"] == cfz_h,
         "preconditions": all(all(v.values()) for v in fz["preconditions"].values()),
         "before_evaluation": o("freeze-geometry") < o("evaluate")}
    return all(p.values()), p | {"mismatch": bad[:5]}


def c19(x):
    rec = x.j("evaluation/evaluation-opened-files.json")
    ev = rec["events"]
    marks = [i for i, e in enumerate(ev) if e.get("event") == "mark"]
    labels = [ev[i]["label"] for i in marks]
    first_ref = next((i for i, e in enumerate(ev) if e.get("event") == "open"
                      and (str(A1C) in e["path"] or "/evaluation/" in e["path"] and str(A1D2) in e["path"])), None)
    ref_mark = next((i for i in marks if ev[i]["label"] == "reference_access_begins"), None)
    p = {"marks_in_order": labels == ["freezes_verified", "reference_access_begins"],
         "no_reference_before_mark": first_ref is not None and ref_mark is not None and first_ref > ref_mark,
         "violations_0": not rec["violations"]}
    return all(p.values()), p


# ---- spherical downstream
def c20(x):
    import ab1b_geometry as BG
    p = {}
    for g in GAZES:
        c, prod, geo, evr = x.calib(g), x.prod(g), x.geo(g), x.evr(g)
        res = BG.compute_epipolar(c, prod)
        same = all(np.array_equal(res[k], geo[k], equal_nan=True) for k in ("P_epi", "theta_R", "phi_R", "theta_L"))
        own_p = own_triangulate(c, prod["uv_L"], prod["uv_R"])
        tri = float(np.nanmax(np.linalg.norm(own_p - geo["P_epi"], axis=1))) if len(own_p) else None
        gi = prod["left_core_row"].astype(np.int64) * CORE + prod["left_core_col"].astype(np.int64)
        pos = {int(i): k for k, i in enumerate(gi)}
        ei = evr["core_index"].astype(np.int64)
        primary_is_spherical = bool(np.array_equal(evr["P_sgbm"], geo["P_epi"][[pos[int(i)] for i in ei]]))
        p[g] = {"accepted_geometry_reproduced": same, "own_ray_ray_max_m": tri,
                "primary_metric_is_spherical_P_epi": primary_is_spherical}
    return all(v["accepted_geometry_reproduced"] and v["own_ray_ray_max_m"] is not None and v["own_ray_ray_max_m"] <= 1e-6
               and v["primary_metric_is_spherical_P_epi"] for v in p.values()), p


# ---- evaluation (own recomputation)
def own_eval(x, g) -> dict:
    def f():
        c, prod, geo = x.calib(g), x.prod(g), x.geo(g)
        ora, perf = x.bench(g, "oracle"), x.bench(g, "perfect")
        pos_l = x.bench(g, "position")["position_w_L"]
        n = CORE * CORE
        oi = ora["left_core_row"].astype(np.int64) * CORE + ora["left_core_col"].astype(np.int64)
        O = np.zeros(n, bool)
        O[oi] = True
        gi = prod["left_core_row"].astype(np.int64) * CORE + prod["left_core_col"].astype(np.int64)
        V = np.zeros(n, bool)
        V[gi] = True
        uvr = np.full((n, 2), np.nan)
        uvr[gi] = prod["uv_R"]
        uvo = np.full((n, 2), np.nan)
        uvo[oi] = ora["uv_R"]
        # serviceable (own planar map, own support, own ROI, own Q)
        r = x.own_rect(g)
        kl, kr = (np.asarray(e["K"], float) for e in c["eyes"])
        ul, wl = K.own_raw_to_rect(kl, r["R1"], r["P1"], np.stack([oi % CORE + ORIGIN, oi // CORE + ORIGIN], -1))
        ur, wr = K.own_raw_to_rect(kr, r["R2"], r["P2"], ora["uv_R"])
        sl = K.own_support(*r["maps"]["L"], RAW, RAW)
        sr = K.own_support(*r["maps"]["R"], RAW, RAW)
        gx, gy, gw, gh = r["roi"]

        def foot(u, w, masks):
            x0, y0 = np.floor(u[:, 0]).astype(int), np.floor(u[:, 1]).astype(int)
            ok = np.isfinite(u).all(-1) & (w > Z_EPS) & (x0 >= 0) & (x0 <= RAW - 2) & (y0 >= 0) & (y0 <= RAW - 2)
            xs, ys = np.where(ok, x0, 0), np.where(ok, y0, 0)
            for m in masks:
                ok &= m[ys, xs] & m[ys, xs + 1] & m[ys + 1, xs] & m[ys + 1, xs + 1]
            return ok
        roi = np.zeros((RAW, RAW), bool)
        roi[gy:gy + gh, gx:gx + gw] = True
        d = ul[:, 0] - ur[:, 0]
        q = np.asarray(r["Q"], float)
        hom = np.stack([ul[:, 0], ul[:, 1], d, np.ones(len(d))], -1) @ q.T
        z = hom[:, 2] / hom[:, 3]
        srv = foot(ul, wl, (sl, roi)) & foot(ur, wr, (sr,)) & (d >= 0) & (d <= r["nd"] - 1) & np.isfinite(z) \
            & (z >= K.LIT_Z[0]) & (z <= K.LIT_Z[1])
        S = np.zeros(n, bool)
        S[oi] = srv
        E = O & V
        e_idx = np.nonzero(E)[0]
        pe = own_pixel_equivalent(c, e_idx, uvr[e_idx], uvo[e_idx])
        pp = np.full((n, 3), np.nan)
        pp[gi] = geo["P_epi"]
        pf = np.full((n, 3), np.nan)
        pf[perf["left_core_row"].astype(np.int64) * CORE + perf["left_core_col"].astype(np.int64)] = perf["P_epi"]
        rows, cols = e_idx // CORE + ORIGIN, e_idx % CORE + ORIGIN
        pref = own_world_to_head(c, pos_l[rows, cols].astype(float))
        e3p = np.linalg.norm(pp[e_idx] - pf[e_idx], axis=1)
        e3r = np.linalg.norm(pp[e_idx] - pref, axis=1)
        prim = x.prim(g)
        pidx = prim["core_index"].astype(np.int64)
        pe_core = np.full(n, np.nan)
        pe_core[pidx] = prim["e_px"]
        p3_core = np.full(n, np.nan)
        p3_core[pidx] = prim["error_3d_vs_perfect_m"]
        se_core = np.full(n, np.nan)
        se_core[e_idx] = pe["e_px"]
        s3_core = np.full(n, np.nan)
        s3_core[e_idx] = e3p
        gp = np.isfinite(pe_core) & (np.abs(np.nan_to_num(pe_core, nan=np.inf)) <= 1.0)
        gs = np.isfinite(se_core) & (np.abs(np.nan_to_num(se_core, nan=np.inf)) <= 1.0)
        cat = np.full(n, -1, np.int8)
        for k, m in enumerate((gp & gs, gp & ~gs, ~gp & gs, ~gp & ~gs)):
            cat[O & m] = k
        pvalid = int(np.isin(prim["class_map"], (0, 2)).sum())
        return {"O": O, "V": V, "S": S, "E": E, "e_idx": e_idx, "pe": pe, "e3p": e3p, "e3r": e3r, "cat": cat,
                "pe_core": pe_core, "p3_core": p3_core, "se_core": se_core, "s3_core": s3_core, "pvalid": pvalid,
                "pidx": pidx}
    return x.c(("own_eval", g), f)


def c21(x):
    """Reference sets: full oracle, SGBM-serviceable oracle (own planar recomputation), valid, evaluable."""
    p = {}
    for g in GAZES:
        o, evr = own_eval(x, g), x.evr(g)
        k = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["counts"]
        want = {"full_oracle": int(o["O"].sum()), "serviceable_oracle": int(o["S"].sum()), "sgbm_valid": int(o["V"].sum()),
                "sgbm_valid_and_oracle": int(o["E"].sum()), "sgbm_valid_and_serviceable": int((o["E"] & o["S"]).sum()),
                "sgbm_valid_non_oracle": int((o["V"] & ~o["O"]).sum())}
        p[g] = {"masks": all(np.array_equal(evr[m], o[w]) for m, w in (("oracle_mask", "O"), ("serviceable_mask", "S"),
                                                                       ("sgbm_valid_mask", "V"))),
                "core_index": bool(np.array_equal(evr["core_index"].astype(np.int64), o["e_idx"])),
                "counts_diff": {kk: (k.get(kk), v) for kk, v in want.items() if k.get(kk) != v},
                "coverages": close(k["serviceable_coverage"], frac(want["sgbm_valid_and_serviceable"], want["serviceable_oracle"]))
                and close(k["full_oracle_coverage"], frac(want["sgbm_valid_and_oracle"], want["full_oracle"]))}
    return all(v["masks"] and v["core_index"] and not v["counts_diff"] and v["coverages"] for v in p.values()), p


def c22(x):
    """Angular and pixel-equivalent errors (own rays, own epipolar line); the local scale equals AB1d2's."""
    p = {}
    for g in GAZES:
        o, evr = own_eval(x, g), x.evr(g)
        pe = o["pe"]
        tol = lambda a, b: float(np.max(np.abs(a - b) / (1e-9 + np.abs(b)))) if len(b) else 0.0  # noqa: E731
        prim = x.prim(g)
        common = np.intersect1d(o["e_idx"], o["pidx"])
        a_pos = np.searchsorted(o["e_idx"], common)
        b_pos = np.searchsorted(o["pidx"], common)
        sc = float(np.max(np.abs(evr["local_scale_rad_per_px"][a_pos] - prim["local_scale_rad_per_px"][b_pos])
                          / np.abs(prim["local_scale_rad_per_px"][b_pos]))) if common.size else 0.0
        p[g] = {"e_theta_abs": float(np.max(np.abs(evr["e_theta"] - pe["e_theta"]))) if len(pe["e_theta"]) else 0.0,
                "scale_rel": tol(evr["local_scale_rad_per_px"], pe["scale"]),
                "e_px_abs": float(np.max(np.abs(evr["e_px"] - pe["e_px"]) / (1 + np.abs(pe["e_px"])))) if len(pe["e_px"]) else 0.0,
                "scale_vs_ab1d2_rel": sc, "common_with_ab1d2": int(common.size)}
    return all(v["e_theta_abs"] <= 1e-12 and v["scale_rel"] <= 1e-7 and v["e_px_abs"] <= 1e-6
               and v["scale_vs_ab1d2_rel"] <= 1e-12 for v in p.values()), p


def c23(x):
    """Primary correspondence statistics: px fractions (precision and effective coverage), catastrophic counts."""
    p = {}
    for g in GAZES:
        o = own_eval(x, g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["primary"]
        ae = np.abs(o["pe"]["e_px"])
        n_o, n_e, n_s = int(o["O"].sum()), int(o["E"].sum()), int(o["S"].sum())
        ins = o["S"][o["e_idx"]]
        bad = []
        for b in PX_BINS:
            st = s["px_within"][f"{b:g}"]
            m = ae <= b
            if st["count"] != int(m.sum()) or not close(st["precision"], frac(m.sum(), n_e)) \
                    or not close(st["effective_oracle_coverage"], frac(m.sum(), n_o)) \
                    or not close(st["effective_serviceable_coverage"], frac((m & ins).sum(), n_s)):
                bad.append(f"px {b}")
        for b in CAT_PX:
            st = s["catastrophic"][f">{b:g}px"]
            if st["count"] != int((ae > b).sum()) or not close(st["fraction_of_oracle"], frac((ae > b).sum(), n_o)):
                bad.append(f"catastrophic {b}")
        if not qmatch(s["px_equivalent_abs"], qof(ae), rel=1e-6, ab=1e-9):
            bad.append("px quantiles")
        if not qmatch(s["px_equivalent_signed"], qof(o["pe"]["e_px"]), rel=1e-6, ab=1e-9):
            bad.append("signed px quantiles")
        p[g] = bad
    return not any(p.values()), p


def c24(x):
    """Metric: 3-D error vs perfect and vs Position; precision AND effective coverage at 12 / 25 / 50 / 100 mm."""
    p = {}
    for g in GAZES:
        o, evr = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["metric"]
        n_o, n_e, n_s = int(o["O"].sum()), int(o["E"].sum()), int(o["S"].sum())
        ins = o["S"][o["e_idx"]]
        bad = []
        for name, e3 in (("vs_perfect", o["e3p"]), ("vs_position", o["e3r"])):
            if float(np.max(np.abs(evr[f"error_3d_{name}_m"] - e3))) > 1e-9:
                bad.append(f"{name} array")
            if not qmatch(s[name]["error_3d_m"], qof(e3), rel=1e-6, ab=1e-9):
                bad.append(f"{name} quantiles")
            for t in METRIC_M:
                st = s[name]["within_m"][f"{t:g}"]
                m = e3 <= t
                if st["count"] != int(m.sum()) or not close(st["precision"], frac(m.sum(), n_e)) \
                        or not close(st["effective_oracle_coverage"], frac(m.sum(), n_o)) \
                        or not close(st["effective_serviceable_coverage"], frac((m & ins).sum(), n_s)):
                    bad.append(f"{name} {t}")
        p[g] = bad
    return not any(p.values()), p


def c25(x):
    """The AB1d2 comparison: categories (own), side-by-side numbers, common evaluable."""
    p = {}
    for g in GAZES:
        o, evr = own_eval(x, g), x.evr(g)
        c = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["comparison_ab1d2"]
        bad = []
        if not np.array_equal(evr["category_map"], o["cat"]):
            bad.append("category map")
        names = ("both_correct", "primitive_only", "sgbm_only", "neither")
        cnt = {nm: int((o["cat"] == k).sum()) for k, nm in enumerate(names)}
        if {k: v["count"] for k, v in c["categories_on_full_oracle"].items()} != cnt or sum(cnt.values()) != int(o["O"].sum()):
            bad.append("category counts")
        n_o = int(o["O"].sum())
        for side, ev_core, e3_core, valid in (("primitive_ab1d2", o["pe_core"], o["p3_core"], o["pvalid"]),
                                              ("sgbm", o["se_core"], o["s3_core"], int(o["V"].sum()))):
            m = np.isfinite(ev_core)
            a, e3 = np.abs(ev_core[m]), e3_core[m]
            st = c[side]
            if st["valid_count"] != valid or st["evaluable"] != int(m.sum()) or not close(st["oracle_coverage"], frac(m.sum(), n_o)):
                bad.append(f"{side} counts")
            if m.any() and (not close(st["median_px"], float(np.median(a)), 1e-9) or not close(st["median_3d_m"],
                                                                                                float(np.median(e3)), 1e-12)):
                bad.append(f"{side} medians")
            for b in PX_BINS:
                if not close(st["within_px_precision"][f"{b:g}"], frac((a <= b).sum(), m.sum())):
                    bad.append(f"{side} px {b}")
            for t in METRIC_M:
                if not close(st["within_m_precision"][f"{t:g}"], frac((e3 <= t).sum(), m.sum())) or not close(
                        st["within_m_effective_oracle_coverage"][f"{t:g}"], frac((e3 <= t).sum(), n_o)):
                    bad.append(f"{side} metric {t}")
            for b in CAT_PX:
                if not close(st["catastrophic_fraction_of_evaluable"][f">{b:g}px"], frac((a > b).sum(), m.sum())):
                    bad.append(f"{side} catastrophic {b}")
        both = np.isfinite(o["pe_core"]) & np.isfinite(o["se_core"])
        if c["common_evaluable"]["count"] != int(both.sum()):
            bad.append("common evaluable")
        p[g] = bad
    return not any(p.values()), p


def c26(x):
    """Spatial statistics (own connected components) and the attrition stored with the evaluation."""
    p = {}
    for g in GAZES:
        o = own_eval(x, g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]

        def comp(mask):
            m = np.asarray(mask, np.uint8).reshape(CORE, CORE)
            nlab, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
            sizes = np.sort(stats[1:, cv2.CC_STAT_AREA])[::-1] if nlab > 1 else np.zeros(0, int)
            return {"pixels": int(m.sum()), "components": int(nlab - 1), "largest": int(sizes[0]) if sizes.size else 0}
        ae = np.abs(o["pe"]["e_px"])
        c10m = np.zeros(CORE * CORE, bool)
        c10m[o["e_idx"][ae > CAT_PX[0]]] = True
        bad = []
        for key, mask in (("sgbm_valid", o["V"]), ("catastrophic_gt10px", c10m)):
            own = comp(mask)
            if any(s["spatial"][key][k] != v for k, v in own.items()):
                bad.append(key)
        if s["attrition"] != x.j(f"correspondence/{g}/adapter-summary.json")["attrition"]:
            bad.append("attrition")
        p[g] = bad
    return not any(p.values()), p


def c27(x):
    """Pooled summary recomputed."""
    s = x.j("evaluation/evaluation-summary.json")["pooled"]
    e = np.concatenate([np.abs(own_eval(x, g)["pe"]["e_px"]) for g in GAZES])
    e3 = np.concatenate([own_eval(x, g)["e3p"] for g in GAZES])
    n_o = sum(int(own_eval(x, g)["O"].sum()) for g in GAZES)
    bad = []
    if s["evaluable"] != e.size or s["full_oracle"] != n_o:
        bad.append("counts")
    for t in METRIC_M:
        if not close(s["within_m_precision"][f"{t:g}"], frac((e3 <= t).sum(), e3.size)) or not close(
                s["within_m_effective_oracle_coverage"][f"{t:g}"], frac((e3 <= t).sum(), n_o)):
            bad.append(f"metric {t}")
    for b in PX_BINS:
        if not close(s["px_within_precision"][f"{b:g}"], frac((e <= b).sum(), e.size)):
            bad.append(f"px {b}")
    return not bad, {"bad": bad}


# ---- process
def c28(x):
    log = x.log
    cmds = [e["command"] for e in log]
    canon = [e["command"] for e in log if e["command"] in CANONICAL and e["status"] == "ok"]
    commits = {e["code"]["commit"] for e in log if e["command"] in CANONICAL}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] for e in log if e["command"] in CANONICAL)
    sgbm_runs = [e for e in log if e["command"] == "sgbm"]
    pre = [e for e in log if e["command"] == "preflight" and e["status"] == "ok"]
    first_sgbm = cmds.index("sgbm") if "sgbm" in cmds else -1
    pre_before = "preflight" in cmds and 0 <= cmds.index("preflight") < first_sgbm
    pre_same = bool(pre) and any(e["code"]["commit"] in commits for e in pre)
    vis = "visualize" in cmds and cmds.index("visualize") > cmds.index("evaluate") if "evaluate" in cmds else False
    p = {"canonical_once_in_order": canon == list(CANONICAL), "one_sgbm_execution": len(sgbm_runs) == 1,
         "one_clean_pushed_commit": len(commits) == 1 and clean, "no_unknown_commands": set(cmds) <= set(COMMANDS),
         "preflight_before_sgbm_same_commit": pre_before and pre_same, "visualize_after_evaluate": vis,
         "on_branch": all(e["code"]["branch"] in (BRANCH, "HEAD") for e in log if e["command"] in CANONICAL)}
    return all(p.values()), p | {"commands": cmds, "commits": sorted(commits)}


def static_scan(x) -> dict:
    hits = {}
    forbidden = {"import": ("ab1b_oracle", "controller", "head_recenter", "torch", "tensorflow", "onnxruntime", "bpy",
                            "ab1d_match"),
                 "call": ("StereoBM_create", "filterSpeckles", "createDisparityWLSFilter", "ximgproc")}
    for name in ("ab1d3_sgbm.py", "ab1d3_run.py", "ab1d3_spec.py"):
        src = x.src(name)
        found = []
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            hits[name] = [f"syntax {e}"]
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                for m in mods:
                    if any(m.split(".")[0] == f for f in forbidden["import"]) and not (
                            name == "ab1d3_run.py" and m == "ab1d_match"):
                        found.append(f"import {m}")
            if isinstance(node, (ast.For, ast.comprehension)):
                seg = ast.get_source_segment(src, node) or ""
                if "StereoSGBM_create" in seg or "compute_sgbm" in seg or "blockSize" in seg or "uniqueness" in seg:
                    found.append("loop over the matcher (parameter sweep)")
            if isinstance(node, ast.Call):
                fn = ast.get_source_segment(src, node.func) or ""
                if any(fn.endswith(f) for f in forbidden["call"]):
                    found.append(f"call {fn}")
                if fn.endswith("compute_sgbm") and name != "ab1d3_sgbm.py" and (len(node.args) > 2 or node.keywords):
                    found.append("compute_sgbm called with a variant in the run")
                if fn.endswith("compute_sgbm") and name == "ab1d3_sgbm.py":
                    seg = ast.get_source_segment(src, node) or ""
                    if seg.replace(" ", "") != "compute_sgbm(c,obs)":
                        found.append(f"compute_sgbm canonical call is {seg}")
                if fn.endswith("adapt") and name == "ab1d3_sgbm.py":
                    seg = ast.get_source_segment(src, node) or ""
                    if seg.replace(" ", "") not in ("adapt(c,rec)",):
                        found.append(f"adapt canonical call is {seg}")
        hits[name] = found
    return hits


def c29(x):
    scan = static_scan(x)
    cmds = {e["command"] for e in x.log}
    scope = not (cmds & {"head-recenter", "recenter", "controller", "controller-step", "sweep", "sgbm-alt", "perfect-matcher"})
    return not any(scan.values()) and scope, {"scan": scan, "scope": scope}


def c30(x):
    recs = sorted(str(p.relative_to(x.run)) for p in x.run.rglob("*sgbm-record.npz") if "preflight" not in str(p))
    want = [f"sgbm/{g}/sgbm-record.npz" for g in GAZES]
    creates = sum(len(x.j(f"sgbm/{g}/sgbm-calls.json")["calls"]["StereoSGBM_create"]) for g in GAZES)
    prods = sorted(str(p.relative_to(x.run)) for p in x.run.rglob("*correspondences.npz") if "preflight" not in str(p))
    return recs == want and creates == 6 and prods == [f"correspondence/{g}/sgbm-correspondences.npz" for g in GAZES], {
        "sgbm_records": recs, "sgbm_objects": creates, "products": prods}


def c31(x):
    rep = x.j("preflight/preflight-report.json")
    canon = {e["code"]["commit"] for e in x.log if e["command"] in CANONICAL}
    names = [c["name"] for c in rep["cases"]]
    need = ("R2 transposed", "disparity sign", "invalid SGBM source pixel", "uv_L moved", "periodic band",
            "sub-pixel", "wrong eye order", "block size", "uniquenessRatio", "P1 / P2", "SGBM mode", "disparity range",
            "z interval", "LR consistency", "texture threshold", "speckle", "refinement", "truth-bearing", "Position read",
            "oracle read", "unfrozen", "round trip", "perfect correspondence", "evaluation:")
    missing = [w for w in need if not any(w in n for n in names)]
    p = {"passed": rep["passed"] and all(c["passed"] for c in rep["cases"]),
         "cases": len(rep["cases"]) >= PREFLIGHT_MIN_CASES, "same_commit": rep["code"]["commit"] in canon,
         "clean": not rep["code"]["dirty"], "required_cases": not missing}
    return all(p.values()), p | {"missing": missing}


def c32(x):
    man = jload(x.vis / "visuals-manifest.json")
    import ab1d3_visuals as V
    key = ("figs", tuple(sorted((k, v) for k, v in man["sources"].items())))
    srcs_ok = all(sha256(x.run / k if not k.startswith("/") else k) == v for k, v in man["sources"].items())
    if key not in _CACHE:
        figs, _ = V.render_all(x.run, x.overrides.get("rgb"))
        _CACHE[key] = {n: V.png_bytes(figs[n]) for n in FIGURES}
    regen = _CACHE[key]
    p = {}
    for n in FIGURES:
        disk = (x.vis / n).read_bytes()
        p[n] = {"manifest_hash": man["figures"][n]["sha256"] == hashlib.sha256(disk).hexdigest(),
                "regenerated_identical": regen[n] == disk}
    return srcs_ok and all(all(v.values()) for v in p.values()), {"sources_verified": srcs_ok, "figures": p}


def c33(x):
    """Truth badges and the never-hidden invalid rule (the hatch masks equal the non-evaluable sets)."""
    man = jload(x.vis / "visuals-manifest.json")
    import ab1d3_visuals as V
    badges = all(man["figures"][n]["badges"] == BADGES[n] for n in FIGURES)
    masks = {}
    for g in GAZES:
        evr = x.evr(g)
        _, m_s = V.err_layer(evr["sgbm_e_px_core"])
        _, m_c = V.cat_layer(evr["category_map"])
        o = own_eval(x, g)
        masks[g] = {"sgbm_err_hatch": int(m_s.sum()) == CORE * CORE - int(o["E"].sum()),
                    "category_hatch": int(m_c.sum()) == CORE * CORE - int(o["O"].sum())}
    invalid_rule = "never hidden" in man["displays"]["invalid"]
    return badges and invalid_rule and all(all(v.values()) for v in masks.values()), {
        "badges": badges, "invalid_rule": invalid_rule, "masks": masks}


def c34(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    listed = set(man["files"])
    present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
        "manifest.json", "check-summary.json", "process-log.jsonl"}
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    return not bad and listed == present and not extra, {"mismatch": bad[:5], "unlisted": sorted(present - listed)[:5],
                                                         "undeclared_changes": extra}


CHECKS = [
    ("01", "provenance: canonical repo, base, AB1d2 acceptance, contract committed first", c01),
    ("02", "accepted sources pinned and unchanged", c02),
    ("03", "the exact accepted 4096-spp observations (pins, AB1d2 freeze, manifest, render control)", c03),
    ("04", "AB1c benchmark and AB1d2 evaluation pins; source manifest", c04),
    ("05", "no new observation: no Blender, no render, no new RGB", c05),
    ("06", "SGBM config: recorded OpenCV calls (getters, 640 x 640 uint8, LR pair, rectify flags, no tripwire)", c06),
    ("07", "SGBM config: accepted summary and the spec's frozen configuration", c07),
    ("08", "the whole matcher recomputed from literals on the 4096 RGB equals the record", c08),
    ("09", "truth firewall: SGBM reads exactly calibration + RGB", c09),
    ("10", "truth firewall: adapter reads exactly calibration + SGBM record", c10),
    ("11", "truth firewall: spherical reads exactly calibration + frozen product; no cv2 / matcher", c11),
    ("12", "rectification: accepted convention, full 640 x 640 window, 112 disparities, support, ROI", c12),
    ("13", "raw adapter recomputed independently: product, exact uv_L, uv_R inside, accepted validator", c13),
    ("14", "strict interpolation validity; own raw -> rectified map", c14),
    ("15", "attrition recomputed", c15),
    ("16", "epipolar consistency of the adapted pairs; secondary planar Q", c16),
    ("17", "correspondence freeze before any truth", c17),
    ("18", "geometry freeze before evaluation", c18),
    ("19", "evaluation opened references only after the freezes were verified", c19),
    ("20", "spherical downstream: accepted AB1b geometry reproduced; primary metric is spherical", c20),
    ("21", "reference sets: full oracle, serviceable (own), valid, evaluable, coverages", c21),
    ("22", "angular and pixel-equivalent errors (own line); scale equals AB1d2's", c22),
    ("23", "primary statistics: px precision / effective coverage, catastrophic", c23),
    ("24", "metric: precision AND effective coverage at 12 / 25 / 50 / 100 mm", c24),
    ("25", "comparison with AB1d2: categories and side-by-side", c25),
    ("26", "spatial statistics and attrition in the evaluation", c26),
    ("27", "pooled summary", c27),
    ("28", "process: canonical once, in order, one clean pushed commit, exactly one SGBM execution", c28),
    ("29", "scope: no sweep, no other matcher, no PERFECT matcher, no controller / head motion", c29),
    ("30", "exactly three SGBM records (six SGBM objects) and three products", c30),
    ("31", "preflight known answers passed from the canonical commit", c31),
    ("32", "figures: hashes and deterministic regeneration", c32),
    ("33", "truth badges; invalid pixels hatched, never hidden", c33),
    ("34", "manifest and declared changes", c34),
]


def run_checks(x: Ctx) -> list[dict]:
    out = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(x)
        except Exception as exc:  # a check that cannot run fails
            ok, detail = False, {"error": f"{type(exc).__name__}: {exc}"}
        out.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
    return out


# ------------------------------------------------------------------ corruption suite (contract section 20)
def mirror(run: Path, vis: Path, root: Path) -> tuple[Path, Path]:
    r, v = root / "run", root / "vis"
    for src, dst in ((run, r), (vis, v)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix in (".json", ".jsonl", ".log"):
                shutil.copyfile(p, q)
            else:
                os.symlink(p, q)
    return r, v


def rewrite_npz(path: Path, fn) -> None:
    d = npz(path)
    fn(d)
    path.unlink()
    np.savez_compressed(path, **d)


def edit_json(path: Path, fn) -> None:
    d = jload(path)
    fn(d)
    path.unlink()
    path.write_text(json.dumps(d, indent=1, sort_keys=True))


def append_log(x: Ctx, entry: dict) -> None:
    ok = [e for e in x.log if e["command"] == "evaluate"][0]
    with open(x.run / "process-log.jsonl", "a") as f:
        f.write(json.dumps({**ok, **entry}, sort_keys=True) + "\n")


def mutated_sgbm(x: Ctx, g: str, ctx_fn=contextlib.nullcontext, variant=None, calib=None, swap=False) -> None:
    """Replace one gaze's canonical SGBM stage output (record, calls, summary) in the MIRROR with a mutated computation."""
    import ab1d3_sgbm as SG
    c = calib if calib is not None else x.calib(g)
    obs = x.rgb(g)
    if swap:
        obs = {"rgb_L": obs["rgb_R"], "rgb_R": obs["rgb_L"]}
    with ctx_fn():
        rec, summ, calls = SG.compute_sgbm(c, obs, variant)
    d = x.run / f"sgbm/{g}"
    (d / "sgbm-record.npz").unlink()
    np.savez_compressed(d / "sgbm-record.npz", **rec)
    edit_json(d / "sgbm-calls.json", lambda j: j.update(calls))
    edit_json(d / "sgbm-summary.json", lambda j: j.update({"accepted_summary": json.loads(json.dumps(summ, default=float))}))


def mutated_adapter(x: Ctx, g: str, variant: dict) -> None:
    import ab1d3_sgbm as SG
    out, prod = SG.adapt(x.calib(g), x.sg(g), variant)
    d = x.run / f"correspondence/{g}"
    for n, data in (("adapter-record.npz", out), ("sgbm-correspondences.npz", prod)):
        (d / n).unlink()
        np.savez_compressed(d / n, **data)


@contextlib.contextmanager
def cv2_override(**kw):
    orig = cv2.StereoSGBM_create

    def f(*a, **k):
        k = dict(k)
        k.update(kw)
        return orig(*a, **k)
    cv2.StereoSGBM_create = f
    try:
        yield
    finally:
        cv2.StereoSGBM_create = orig


@contextlib.contextmanager
def fs_patch(name, value):
    import fsg_stereo as FS
    saved = getattr(FS, name)
    setattr(FS, name, value)
    try:
        yield
    finally:
        setattr(FS, name, saved)


def refine_bound_2(left, right, initial, supported):
    """A mutated refinement (corruption suite only): 5 updates and a 2.0 px total bound."""
    return K.own_refine(left, right, initial, supported, params=(5, 0.5, 2.0))


def corruption_list(root: Path) -> list:
    g = "gaze-1"
    L = []

    def add(name, expect, fn):
        L.append((name, set(expect), fn))

    def alt_file(x, kind, fn):
        src = x.calib_path(g) if kind == "calib" else x.rgb_path(g)
        dst = root / f"alt-{kind}{src.suffix}"
        if kind == "calib":
            c = jload(src)
            fn(c)
            dst.write_text(json.dumps(c))
        else:
            d = npz(src)
            fn(d)
            np.savez_compressed(dst, **d)
        x.overrides.setdefault(kind, {})[g] = str(dst)
    # SOURCE
    add("one 4096 RGB pixel changed", {"03", "08"},
        lambda x: alt_file(x, "rgb", lambda d: d["rgb_L"].__setitem__((320, 320, 0), d["rgb_L"][320, 320, 0] + 0.05)))
    add("calibration changed (right eye x + 1e-4 m)", {"03", "08"},
        lambda x: alt_file(x, "calib", lambda c: c["eyes"][1]["centre_h_m"].__setitem__(0, c["eyes"][1]["centre_h_m"][0] + 1e-4)))

    def read_event(x, rel, path):
        def f(j):
            j["events"].append({"event": "open", "path": path, "kind": "data-read", "allowed": True})
            j["data_reads"] = sorted(set(j["data_reads"]) | {path})
        edit_json(x.run / rel, f)
    add("oracle read during matching", {"09"}, lambda x: read_event(x, f"sgbm/{g}/sgbm-opened-files.json",
                                                                   str(A1C / f"oracle/{g}/oracle-correspondences.npz")))
    add("Position read during matching", {"09"}, lambda x: read_event(
        x, f"sgbm/{g}/sgbm-opened-files.json", str(A1D2 / f"observations/{g}/evaluation_only/reference-observation.npz")))
    add("Position read in the adapter", {"10"}, lambda x: read_event(
        x, f"correspondence/{g}/adapter-opened-files.json", str(A1C / f"observations/{g}/evaluation_only/reference-observation.npz")))
    # SGBM configuration (mutated stage outputs, computed in the mirror only)
    cfg = {"06", "07", "08"}
    add("block size 7", cfg, lambda x: mutated_sgbm(x, g, variant={"block_size": 7}))
    add("P1 400", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(P1=400)))
    add("P2 1600", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(P2=1600)))
    add("uniquenessRatio 15", cfg, lambda x: mutated_sgbm(x, g, variant={"uniqueness_ratio": 15}))
    add("mode SGBM (not 3WAY)", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(mode=0)))
    add("preFilterCap 63", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(preFilterCap=63)))
    add("disparity support: numDisparities 128", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(numDisparities=128)))

    def zc(x):
        c = json.loads(json.dumps(x.calib(g)))
        c["depth_search_z_rect_m"] = [0.75, 8.0]
        mutated_sgbm(x, g, calib=c)
    add("z interval 0.75 .. 8 m", cfg, zc)
    add("LR tolerance 2 px", cfg, lambda x: mutated_sgbm(x, g, lambda: fs_patch("LR_TOLERANCE_PX", 2.0)))
    add("speckle filtering enabled", cfg, lambda x: mutated_sgbm(x, g, lambda: cv2_override(speckleWindowSize=100,
                                                                                           speckleRange=2)))
    add("texture threshold 2.0 u8", cfg, lambda x: mutated_sgbm(x, g, lambda: fs_patch("MIN_LOCAL_STD_U8", 2.0)))
    add("refinement bound 2.0 px", cfg, lambda x: mutated_sgbm(x, g, lambda: fs_patch("refine_disparity", refine_bound_2)))
    # RECTIFICATION
    add("eye swap", {"08"}, lambda x: mutated_sgbm(x, g, swap=True))
    add("baseline sign (P2[0,3] and Q flipped in the record)", {"12"},
        lambda x: rewrite_npz(x.run / f"sgbm/{g}/sgbm-record.npz", lambda d: (d["P2"].__setitem__((0, 3), -d["P2"][0, 3]),
                                                                              d["Q_full"].__setitem__((3, 2), -d["Q_full"][3, 2]))))
    add("R2 transposed in the record", {"12"}, lambda x: rewrite_npz(x.run / f"sgbm/{g}/sgbm-record.npz",
                                                                     lambda d: d.__setitem__("R2", d["R2"].T.copy())))
    add("crop: central 256 window instead of the full raster", {"12"}, lambda x: rewrite_npz(
        x.run / f"sgbm/{g}/sgbm-record.npz", lambda d: d.__setitem__("crop_xywh", np.array([192, 192, 256, 256], np.int32))))
    add("map change: refined disparity shifted one column", {"08"}, lambda x: rewrite_npz(
        x.run / f"sgbm/{g}/sgbm-record.npz", lambda d: d.__setitem__("disparity_px", np.roll(d["disparity_px"], 1, axis=1))))
    # ADAPTER
    add("adapter: wrong disparity sign", {"13"}, lambda x: mutated_adapter(x, g, {"disparity_sign": -1.0}))
    add("adapter: wrong inverse rectification (R2^T)", {"13"}, lambda x: mutated_adapter(x, g, {"r2_transposed": True}))
    add("adapter: bilinear interpolation across invalid source pixels", {"13", "14"},
        lambda x: mutated_adapter(x, g, {"ignore_footprint_validity": True}))
    add("product: non-raw uv_L", {"13"}, lambda x: rewrite_npz(x.run / f"correspondence/{g}/sgbm-correspondences.npz",
                                                              lambda d: d["uv_L"].__setitem__((0, 0), d["uv_L"][0, 0] + 0.5)))
    add("product: uv_R outside the raster", {"13"}, lambda x: rewrite_npz(
        x.run / f"correspondence/{g}/sgbm-correspondences.npz", lambda d: d["uv_R"].__setitem__((0, 0), 700.0)))
    # FREEZE
    add("correspondence mutated after the freeze", {"17", "13"}, lambda x: rewrite_npz(
        x.run / f"correspondence/{g}/sgbm-correspondences.npz", lambda d: d["uv_R"].__setitem__((5, 0), d["uv_R"][5, 0] + 0.01)))
    add("geometry mutated after the freeze", {"18", "20"}, lambda x: rewrite_npz(
        x.run / f"spherical/{g}/epipolar-result.npz", lambda d: d["P_epi"].__setitem__((0, 2), d["P_epi"][0, 2] + 0.001)))

    def early(x):
        def f(j):
            ev = j["events"]
            ref = next(i for i, e in enumerate(ev) if e.get("event") == "open" and str(A1C) in e["path"])
            e = ev.pop(ref)
            ev.insert(0, e)
        edit_json(x.run / "evaluation/evaluation-opened-files.json", f)
    add("benchmark opened before the freezes were verified", {"19"}, early)
    # EVALUATION
    add("serviceable count corrupted", {"21"}, lambda x: edit_json(x.run / "evaluation/evaluation-summary.json", lambda j: j[
        "per_gaze"][g]["counts"].__setitem__("serviceable_oracle", j["per_gaze"][g]["counts"]["serviceable_oracle"] + 1)))
    add("serviceable mask corrupted", {"21"}, lambda x: rewrite_npz(x.run / f"evaluation/{g}/evaluation-result.npz",
                                                                   lambda d: d["serviceable_mask"].__setitem__(
                                                                       int(np.argmax(d["oracle_mask"])), ~d["serviceable_mask"][
                                                                           int(np.argmax(d["oracle_mask"]))])))
    add("<= 1 px count corrupted", {"23"}, lambda x: edit_json(x.run / "evaluation/evaluation-summary.json", lambda j: j[
        "per_gaze"][g]["primary"]["px_within"]["1"].__setitem__("count", j["per_gaze"][g]["primary"]["px_within"]["1"]["count"] + 5)))
    add("12-mm precision corrupted", {"24"}, lambda x: edit_json(x.run / "evaluation/evaluation-summary.json", lambda j: j[
        "per_gaze"][g]["metric"]["vs_perfect"]["within_m"]["0.012"].__setitem__(
        "precision", j["per_gaze"][g]["metric"]["vs_perfect"]["within_m"]["0.012"]["precision"] + 0.01)))
    add("effective coverage corrupted", {"24"}, lambda x: edit_json(x.run / "evaluation/evaluation-summary.json", lambda j: j[
        "per_gaze"][g]["metric"]["vs_perfect"]["within_m"]["0.025"].__setitem__(
        "effective_oracle_coverage", j["per_gaze"][g]["metric"]["vs_perfect"]["within_m"]["0.025"]["effective_oracle_coverage"] - 0.01)))
    add("pixel-equivalent error array corrupted", {"22", "23"}, lambda x: rewrite_npz(
        x.run / f"evaluation/{g}/evaluation-result.npz", lambda d: d["e_px"].__setitem__(0, d["e_px"][0] + 3.0)))
    add("category map corrupted", {"25"}, lambda x: rewrite_npz(
        x.run / f"evaluation/{g}/evaluation-result.npz",
        lambda d: d["category_map"].__setitem__(int(np.argmax(d["category_map"] == 3)), 2)))
    add("primary metric replaced by planar Q", {"20"}, lambda x: rewrite_npz(
        x.run / f"evaluation/{g}/evaluation-result.npz", lambda d: d["P_sgbm"].__setitem__(0, d["P_sgbm"][0] + 1e-9)))
    # PROCESS
    add("a second SGBM configuration run", {"28", "30"}, lambda x: (
        append_log(x, {"command": "sgbm", "argv": ["ab1d3_run.py", "sgbm", "--blockSize", "7"]}),
        (x.run / "sgbm-alt/gaze-1").mkdir(parents=True), os.symlink(x.run / f"sgbm/{g}/sgbm-record.npz",
                                                                     x.run / "sgbm-alt/gaze-1/sgbm-record.npz")))
    add("parameter sweep injected into the run code", {"29"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d3_run.py", "\n\ndef sweep(c, obs):\n    for block in (3, 5, 7):\n        compute_sgbm(c, obs, {'block_size': block})\n"))
    add("PERFECT matcher injected into inference", {"29"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d3_sgbm.py", "\nimport ab1b_oracle\n"))
    add("head motion / controller injected", {"28", "29"}, lambda x: append_log(x, {"command": "head-recenter"}))
    add("hidden variant in the canonical SGBM call", {"29"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d3_sgbm.py", "\n\ndef _x(c, obs):\n    return compute_sgbm(c, obs, {'use_lr': False})\n"))
    # VISUAL
    add("canonical figure pixel altered", {"32"}, lambda x: _fig_edit(x, "overview.png", lambda a: a.__setitem__(
        (900, 900), (255 - a[900, 900]).astype(np.uint8))))
    add("invalid region hidden in the overview (hatch painted over)", {"32"}, lambda x: _fig_edit(
        x, "overview.png", lambda a: a.__setitem__((slice(1310, 1400), slice(330, 400)), np.array([232, 230, 225], np.uint8))))
    add("truth badge altered", {"33"}, lambda x: edit_json(x.vis / "visuals-manifest.json", lambda j: j["figures"][
        "metric-error.png"].__setitem__("badges", ["DERIVED"])))
    return L


def _fig_edit(x: Ctx, name: str, fn) -> None:
    from PIL import Image
    p = x.vis / name
    a = np.asarray(Image.open(p).convert("RGB")).copy()
    fn(a)
    p.unlink()
    Image.fromarray(a).save(p)


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list, dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="ab1d3-corrupt-") as tmp:
        root = Path(tmp)
        r, v = mirror(run, vis, root / "null")
        null = run_checks(Ctx(r, v, {"orig_run": run}))
        null_ok = all(c["ok"] for c in null)
        null_fail = [c["check"] for c in null if not c["ok"]]
        shutil.rmtree(root / "null")
        for k, (name, expect, fn) in enumerate(corruption_list(root)):
            r, v = mirror(run, vis, root / f"c{k:02d}")
            x = Ctx(r, v, {"orig_run": run})
            fn(x)
            x._m.clear()          # never check a value cached before the corruption was written
            res = run_checks(x)
            failed = sorted(c["check"] for c in res if not c["ok"])
            caught = bool(set(failed) & expect)
            results.append({"corruption": name, "expected_any_of": sorted(expect), "failed_checks": failed,
                            "caught": caught})
            print(f"{PREFIX} corruption {'CAUGHT' if caught else 'MISSED'} {name}: failed {failed}", flush=True)
            shutil.rmtree(root / f"c{k:02d}")
            for p in root.glob("alt-*"):
                p.unlink()
    caught = sum(r["caught"] for r in results)
    return caught, len(results), results, {"null_probe_passed": null_ok, "null_probe_failed": null_fail}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    res = run_checks(Ctx(run, vis))
    for c in res:
        print(f"{PREFIX} {'PASS' if c['ok'] else 'FAIL'} {c['check']} {c['name']}"
              + ("" if c["ok"] else f" -- {json.dumps(c['detail'], default=str)[:600]}"), flush=True)
    npass = sum(c["ok"] for c in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1D3_CHECKS_PASS")
    out = {"schema": "AB1d3-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD")}
    if a.corruptions:
        caught, total, results, null = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, **null, "results": results}
        probative = ok and null["null_probe_passed"]
        print(f"{PREFIX} NULL PROBE {'PASS' if null['null_probe_passed'] else 'FAIL ' + str(null['null_probe_failed'])}")
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if probative else " (NOT PROBATIVE)"))
        if probative and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1D3_MUTATIONS_CAUGHT")
        ok = ok and probative and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
