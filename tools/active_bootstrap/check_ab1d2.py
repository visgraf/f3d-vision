"""Active Bootstrap-1d2: fail-capable checker of the 4096-spp observation-quality control.

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md, sections 22-23.

    .venv/bin/python tools/active_bootstrap/check_ab1d2.py --run RUN --visuals VIS [--corruptions] [--write-summary]

The checker keeps its own literal pins and constants.  It re-implements the render-setting classification, reads the
EXR headers itself, recomputes the camera matrices from the calibration, recomputes the search-geometry identity over
the full core, runs the accepted AB1d checker's independent matcher (``check_ab1d.own_match``: fundamental-matrix
line, arccos / complex-argument angles, its own projection, bilinear sampling, moments ZNCC, per-pixel decision) on
the 4096 RGB for core index % 32 == 7 and the example pixels, recomputes the 4096 evaluation, the paired comparison,
the metric consequence and the diagnostics with its own code, audits guard records, freezes and the run order, and
regenerates every figure.  ``--corruptions`` injects genuine defects into mirrors of the run and visuals (and into
overrides of the accepted inputs), after an unmodified-mirror null probe passes every check.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import check_ab1d as CA  # noqa: E402  (the accepted AB1d checker's independent primitives, read-only)

PREFIX = "[ab1d2-check]"

# ------------------------------------------------------------------ the checker's own literals (contract section 29)
BASE = "22f538f8eb2dad69d45b7fc3183fbcc2ee861d55"
CONTRACT = "6f5b757754230429c89fd3d358316a5180b6d623"
BRANCH = "active-bootstrap/ab1d2-4096spp-observation-quality"
SPP, ACC_SPP = 4096, 256
SEEDS = {"L": 2111, "R": 2112}
CORE, ORIGIN, RAW = 256, 192, 640
POSE_TOL = 1e-6
EPS_PX, ZEPS_ZNCC, EPS_M, GOOD = 1e-9, 1e-12, 1e-12, 1.0
PEAK_RADIUS = 1.5
TOPK = 8
SUBSET = (32, 7)
CONSTANTS = {"PATCH": 5, "PATCH_HALF": 2, "LUMA": (0.2126, 0.7152, 0.0722), "MIN_LOCAL_STD_U8": 0.5, "SPACING_PX": 1.0,
             "TIE_EPS": 1e-12, "TOP_K": 8, "PEAK_SEPARATION_PX": 3.0, "REFINE_BOUND_SAMPLES": 0.75, "Z_EPS": 1e-12,
             "DEN_EPS": 1e-12}
GAZES = ("gaze-1", "gaze-2", "gaze-3")
GAZE_TABLE = {"gaze-1": (-18.75, -5.75), "gaze-2": (6.75, 6.75), "gaze-3": (18.75, -5.25)}
SHARED = Path("/home/lvelho/rd/f3d-vision")
A1C = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
A1D = SHARED / "previews/active-bootstrap/ab1d-safe-forward-natural-correspondence"
A1D_VIS_MAN = (SHARED / "visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence/visuals-manifest.json",
               "c7391c7b3516afed4dc728381f8ffaf8fa4fac4697661ff3aa2781c5ac397ecf")
A1C_MANIFEST = "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a"
A1C_OBS = {
    "observations/gaze-1/acquisition/calibration.json": "ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
    "observations/gaze-1/acquisition/rgb-observation.npz": "d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f",
    "observations/gaze-1/acquisition/acquisition.json": "d1ca822aa2ca49e32fd59466736d03408e7549cac1a452ded6bc19806d32c27b",
    "observations/gaze-2/acquisition/calibration.json": "ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
    "observations/gaze-2/acquisition/rgb-observation.npz": "297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d",
    "observations/gaze-2/acquisition/acquisition.json": "59443c35284625fca1792b3bfe5cabb22e6635cb27c05bd274ab7501e93beeac",
    "observations/gaze-3/acquisition/calibration.json": "085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd",
    "observations/gaze-3/acquisition/rgb-observation.npz": "5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c",
    "observations/gaze-3/acquisition/acquisition.json": "68fd96d8d541095ff8623b98dd74e22a8161bf593611739e6ea5cad126a52abd",
    "observations/evaluation_only/instance-catalog.json": "948dd8d4c1824e5acf6a3a179b7a8a6d4b39134dda041861dbb8193fe3d3df4a",
}
A1C_BENCH = dict(CA.BENCH_PINS)          # the accepted AB1d checker's literal benchmark pins (oracle, perfect, Position)
A1D_PINS = {
    "manifest.json": "3f6a837d6529b8fc1a6680aeb18446c6c9ecbe0e67e5304a4e4154837161b838",
    "match/correspondence-freeze.json": "006c9116b5127b63efb218d179aef4283d8a0466f631d358a5a2082d72d0c5ab",
    "freeze/geometry-freeze.json": "0c2d7b0a3e847085451279a96431541b4ba8998b35c03e5f099597729cc84730",
    "evaluation/evaluation-summary.json": "692f49d7c6de6b7babec1fd9775102d933a2f3c97f8e545c0fa164029c187345",
    "match/gaze-1/matcher-record.npz": "9a47412712d9e3205df250fdffb2b5e6b4560380269d5b5cab85ff44d292425e",
    "match/gaze-2/matcher-record.npz": "541e3a5c6a4f40314f3b9b46df04b4f8a9c40c92684595a1b770431107cf5fc7",
    "match/gaze-3/matcher-record.npz": "5034fc6f59db5931b9e5c790332736001d94c5d7967d7e6ce61ed842a38477f9",
    "match/gaze-1/natural-correspondences.npz": "bf9382ae4be385d5b926bac039fb75b8e6b09d7e53a508a0be95abd9f7737e35",
    "match/gaze-2/natural-correspondences.npz": "844c60c6db9b4a69416f887b67db10dc0b24c2cd51a66083bf9b57cab7d743d2",
    "match/gaze-3/natural-correspondences.npz": "102e5b04112fafe4d22739e209f50a77f1e2f00a0dec5484d3ede53dbcf0a12a",
    "spherical/gaze-1/epipolar-result.npz": "646e45282a36f2ed31ed0cbf0caa294fea004ea143036ec30e7217a04014c46f",
    "spherical/gaze-2/epipolar-result.npz": "2c8940d97609c5bb5adfd17490c215fb1286ae47996df1431eddd641e3ef2121",
    "spherical/gaze-3/epipolar-result.npz": "5a49085396fc579fc0a269f1e284332b247428e8447f9d50a4b19b787b3e360f",
    "evaluation/gaze-1/evaluation-result.npz": "c849e72d56ca2f30765cd74ac86d7acb63217e2bec2c5920123182db6928142f",
    "evaluation/gaze-2/evaluation-result.npz": "b794127d6fb36af60a126bd9fc7dbbe7aa9dafb80c26377cd52bdadfb4fcfee2",
    "evaluation/gaze-3/evaluation-result.npz": "e8665c2b3e6987d69a3778883136a007cce76f81f38c1c28b4d6ac7179121c59",
}
CODE_PINS = {
    "tools/active_bootstrap/ab1d_match.py": "dd1ac243d1da09635e12edb87d0d402f169d49e016ac3f35ed5d1572ec255ffd",
    "tools/active_bootstrap/ab1d_spec.py": "fc50a7306ed5e384878c61574c250b3534e1ac4b3a2e6936c153f805aba7b346",
    "tools/active_bootstrap/ab1d_run.py": "9df2981ba55041e7cebdb34061b5cb565d65734b78962318931b4dcb482a7292",
    "tools/active_bootstrap/check_ab1d.py": "600106c06138024a36dc95043aa5d00daf548e0c27ccf728817f6dffc3e12862",
    "tools/active_bootstrap/ab1d_visuals.py": "33a8d9b0cf6c412c3e5c11bfb93f498fea9faca0939422bb7ff1391d912fdf53",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1c_render.py": "a1281a2019dca259c490cba9955cf2b5ed61cca4db167a1a2f7a03dc5f315b87",
    "tools/active_bootstrap/ab1c_spec.py": "53d1b7228b30883db715f3fc33a65893aa7708656c2881f2a31eef1a3ac77b1a",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1b_visuals.py": "6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee",
    "tools/active_bootstrap/ab1c_visuals.py": "28054811eca774883753c2499d135cdabae37b32f6f014432bf1057dcab71a30",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/classroom_oracle/breadth1_visuals.py": "61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c",
}
BLEND_SHA = "dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc"
BLEND_REAL = str(SHARED / "scenes/classroom/classroom_eye.blend")
MUST_EQUAL = ("schema", "truth", "statement", "blender", "gaze_yaw_pitch_deg", "profile", "tangent_frame", "ipd_m",
              "vergence_distance_m", "device", "render_seeds_lr", "seed_rule", "exr_channels_lr", "settings",
              "camera_matrix_world_lr", "calibration_sha256", "rgb_observation_arrays", "evaluation_only", "complete",
              "canonical", "ab1c_gaze", "ab1c_rank", "eye_pose", "calibration_max_abs_diff_from_planned")
EXPECTED = ("spp", "primary_camera_samples", "render_seconds_lr", "rgb_observation_sha256", "created_utc")
LABELS = ("experiment", "action_source", "blend", "observation_quality_control")
EXR_EQUAL = ("BlenderMultiChannel", "Camera", "Scene", "Software", "Frame", "Time", "channels", "colorInteropID",
             "compression", "dataWindow", "displayWindow", "lineOrder", "pixelAspectRatio", "screenWindowCenter",
             "screenWindowWidth", "xDensity")
EXR_TIMING = {"Date", "RenderTime", "cycles.interior.render_time", "cycles.interior.synchronization_time",
              "cycles.interior.total_time"}
GEO_FIELDS = ("left_core_row", "left_core_col", "uv_L", "theta_L", "phi_L", "q_inf", "line_dir", "line_l", "k_first",
              "k_last", "candidate_count", "valid_left_patch")
CANONICAL = ("source", "preflight", "render-4096", "freeze-observation", "match", "freeze-correspondence", "spherical",
             "freeze-geometry", "evaluate-paired")
ORDER = ("source", "preflight-tests", "rehearse", "preflight", "render-4096", "freeze-observation", "match",
         "freeze-correspondence", "spherical", "freeze-geometry", "evaluate-paired", "visualize")
TOOLS = ("ab1d2_spec.py", "ab1d2_render.py", "ab1d2_run.py", "ab1d2_preflight.py", "ab1d2_visuals.py", "check_ab1d2.py")
DECLARED = ({"docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md",
             "docs/active-bootstrap/ab1d2-4096spp-observation-quality-report.md",
             "tools/repository/check_repository_layout.py"} | {f"tools/active_bootstrap/{n}" for n in TOOLS})
FIGURES = ("overview.png", "paired-cost-landscapes.png", "correspondence-improvement.png", "observation-comparison.png",
           "metric-comparison.png", "confidence-change.png")
ORA_B, DER_B, REF_B = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
BADGES = {"overview.png": [ORA_B, DER_B, REF_B], "paired-cost-landscapes.png": [ORA_B, DER_B, REF_B],
          "correspondence-improvement.png": [DER_B, REF_B], "observation-comparison.png": [ORA_B, DER_B, REF_B],
          "metric-comparison.png": [DER_B, REF_B], "confidence-change.png": [DER_B, REF_B]}
FORBIDDEN_IMPORTS = ("torch", "tensorflow", "onnxruntime", "kornia", "sklearn", "fov3d.controller", "controller")
FORBIDDEN_TOKENS = ("StereoSGBM", "StereoBM", "use_denoising = True", "denoiser", "head_recenter", "recenter",
                    "controller_step")
QK = {"median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
CODE_SUFFIXES = (".py", ".pyc", ".so", ".pth", ".typed")
TOKEN_SCAN = ("ab1d2_spec.py", "ab1d2_render.py", "ab1d2_run.py", "ab1d2_visuals.py")


# ------------------------------------------------------------------ infrastructure
_SHA: dict = {}
_REGEN: dict = {}


def sha256(path) -> str:
    """sha256 of a file, cached by (real path, size, mtime); a rewritten or substituted file is re-hashed."""
    st = os.stat(path)
    key = (os.path.realpath(path), st.st_size, st.st_mtime_ns)
    if key not in _SHA:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        _SHA[key] = h.hexdigest()
    return _SHA[key]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def npz(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def jload(path):
    return json.loads(Path(path).read_text())


def qof(a) -> dict | None:
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)].ravel()
    return None if a.size == 0 else {k: float(np.quantile(a, v)) for k, v in QK.items()}


def qmatch(stored: dict | None, own: dict | None, rel=1e-9, ab=1e-12) -> bool:
    if stored is None or own is None:
        return stored is None and own is None
    return all(k in stored and abs(stored[k] - v) <= ab + rel * abs(v) for k, v in own.items())


def exr_header(path) -> dict:
    from exr_lite import read_header
    with open(path, "rb") as f:
        buf = f.read(65536)
    h = read_header(buf)[0]

    def norm(v):
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="backslashreplace")
        if isinstance(v, (list, tuple)):
            return [norm(e) for e in v]
        return v
    return {k: norm(v) for k, v in h.items()}


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

    def a1c(self, rel) -> Path:
        return Path(self.overrides.get("a1c", {}).get(rel, A1C / rel))

    def a1d(self, rel) -> Path:
        return Path(self.overrides.get("a1d", {}).get(rel, A1D / rel))

    def code(self, rel) -> Path:
        return Path(self.overrides.get("code", {}).get(rel, REPO / rel))

    def src(self, name: str) -> str:
        return (HERE / name).read_text() + self.overrides.get("static_extra", {}).get(name, "")

    def rec(self, g):
        return self.n(f"match/{g}/matcher-record.npz")

    def rec256(self, g):
        return self.c(("rec256", g), lambda: npz(self.a1d(f"match/{g}/matcher-record.npz")))

    def evr(self, g):
        return self.n(f"evaluation/{g}/evaluation-result.npz")

    def evr256(self, g):
        return self.c(("evr256", g), lambda: npz(self.a1d(f"evaluation/{g}/evaluation-result.npz")))

    def par(self, g):
        return self.n(f"evaluation/{g}/paired-result.npz")

    def acq(self, g):
        return self.j(f"observations/{g}/acquisition/acquisition.json")

    def acq256(self, g):
        return self.c(("acq256", g), lambda: jload(self.a1c(f"observations/{g}/acquisition/acquisition.json")))

    def calib(self, g):
        return self.j(f"observations/{g}/acquisition/calibration.json")

    def gray(self, g, cond):
        def f():
            p = (self.run / f"observations/{g}/acquisition/rgb-observation.npz" if cond == "4096"
                 else self.a1c(f"observations/{g}/acquisition/rgb-observation.npz"))
            z = npz(p)
            return CA.own_gray(z["rgb_L"]), CA.own_gray(z["rgb_R"])
        return self.c(("gray", g, cond), f)

    def rrel(self, p: str) -> str:
        rp = str(Path(p))
        for root in (str(self.run), str(self.overrides.get("orig_run", self.run))):
            if rp.startswith(root + "/"):
                return "RUN/" + rp[len(root) + 1:]
        return rp

    @property
    def log(self) -> list[dict]:
        return self.c("log", lambda: [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x])

    def live_constants(self) -> tuple[dict, dict]:
        if "live_constants" in self.overrides:
            return self.overrides["live_constants"]
        import ab1d_match as M
        import ab1d_spec as DS
        spec = {k: (tuple(getattr(DS, k)) if k == "LUMA" else getattr(DS, k)) for k in CONSTANTS}
        fz = M.FROZEN
        params = {"PATCH_HALF": fz.patch_half, "SPACING_PX": fz.spacing, "MIN_LOCAL_STD_U8": fz.min_std,
                  "TIE_EPS": fz.tie_eps, "TOP_K": fz.top_k, "PEAK_SEPARATION_PX": fz.separation,
                  "REFINE_BOUND_SAMPLES": fz.bound, "LUMA": tuple(fz.luma)}
        return spec, params


def subset_idx(x: Ctx, g) -> np.ndarray:
    base = np.arange(SUBSET[1], CORE * CORE, SUBSET[0])
    ex = [e["core_index"] for e in jload(A1D_VIS_MAN[0])["examples"][g]]
    return np.unique(np.concatenate([base, np.asarray(ex, np.int64)]))


def eval_idx(e) -> np.ndarray:
    return np.asarray(e["core_index"], np.int64)


# ------------------------------------------------------------------ own render-setting classification (section 7)
def own_classify(old: dict, new: dict) -> list[str]:
    bad = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if k in MUST_EQUAL:
            if k == "camera_matrix_world_lr":
                ok = a is not None and b is not None and max(abs(p - q) for s in "LR" for ra, rb in zip(a[s], b[s])
                                                             for p, q in zip(ra, rb)) <= POSE_TOL
            elif k == "settings":
                ok = (set(a) == set(b) and all(a[s] == b[s] for s in a if s != "samples") and a["samples"] == ACC_SPP
                      and b["samples"] == SPP)
            else:
                ok = k in old and k in new and a == b
        elif k in EXPECTED:
            ok = {"spp": a == ACC_SPP and b == SPP,
                  "primary_camera_samples": a == 2 * RAW * RAW * ACC_SPP and b == 2 * RAW * RAW * SPP,
                  "rgb_observation_sha256": a is not None and b is not None and a != b,
                  "created_utc": a is not None and b is not None and a != b}.get(k, a is not None and b is not None)
        elif k in LABELS:
            ok = (os.path.realpath(a) == os.path.realpath(b) == BLEND_REAL) if k == "blend" else (
                k != "observation_quality_control" or (b or {}).get("spp") == SPP)
        else:
            ok = False
        if not ok:
            bad.append(k)
    return bad


def own_exr(old: dict, new: dict) -> list[str]:
    bad = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if k in EXR_EQUAL:
            ok = k in old and k in new and a == b
        elif k == "cycles.interior.samples":
            ok = a == str(ACC_SPP) and b == str(SPP)
        elif k in EXR_TIMING:
            ok = True
        elif k == "File":
            ok = os.path.realpath(a or "") == os.path.realpath(b or "") == BLEND_REAL
        else:
            ok = False
        if not ok:
            bad.append(k)
    bad += [k for k in EXR_EQUAL + ("cycles.interior.samples",) if k not in old or k not in new]
    return sorted(set(bad))


# ------------------------------------------------------------------ PROVENANCE
def c01(x):
    remote = git("remote", "get-url", "origin")
    ok_remote = remote.rstrip("/").removesuffix(".git").endswith("visgraf/f3d-vision") and "fov-3d-vision" not in remote
    anc = all(subprocess.run(["git", "merge-base", "--is-ancestor", c, "HEAD"], cwd=REPO).returncode == 0
              for c in (BASE, CONTRACT))
    commits = {e["code"]["commit"] for e in x.log if e["command"] in CANONICAL}
    run_anc = all(subprocess.run(["git", "merge-base", "--is-ancestor", CONTRACT, c], cwd=REPO).returncode == 0
                  for c in commits)
    branches = {e["code"]["branch"] for e in x.log}
    return ok_remote and anc and run_anc and branches == {BRANCH}, {"remote": remote, "ancestry": anc,
                                                                     "run_commits_after_contract": run_anc,
                                                                     "branches": sorted(branches)}


def c02(x):
    bad = {p: sha256(x.code(p)) for p, h in CODE_PINS.items() if sha256(x.code(p)) != h}
    return not bad, {"changed": sorted(bad)}


def c03(x):
    man = jload(x.a1c("manifest.json"))["files"]
    files = {k: sha256(x.a1c(k)) == h for k, h in A1C_OBS.items()}
    in_man = all(man.get(k) == h for k, h in A1C_OBS.items() if "instance-catalog" not in k)
    bench = {k: sha256(x.a1c(k)) == h and man.get(k) == h for k, h in A1C_BENCH.items()}
    ok = sha256(x.a1c("manifest.json")) == A1C_MANIFEST and all(files.values()) and in_man and all(bench.values())
    return ok, {"files_bad": [k for k, v in files.items() if not v], "in_manifest": in_man,
                "bench_bad": [k for k, v in bench.items() if not v]}


def c04(x):
    man = jload(x.a1d("manifest.json"))["files"]
    bad = [k for k, h in A1D_PINS.items() if sha256(x.a1d(k)) != h or (k != "manifest.json" and man.get(k) != h)]
    vis = sha256(A1D_VIS_MAN[0]) == A1D_VIS_MAN[1]
    return not bad and vis, {"bad": bad, "visuals_manifest": vis}


def c05(x):
    s = x.j("source/source-manifest.json")
    ok = (all(s["identity"].values()) and s["spp"] == SPP and s["accepted_spp"] == ACC_SPP and s["seeds"] == SEEDS
          and s["base_commit"] == BASE and s["contract_commit"] == CONTRACT and s["blend_sha256"] == BLEND_SHA
          and s["a1d_pins"] == A1D_PINS and s["source_pins"] == CODE_PINS
          and all(s["a1c_observation_pins"].get(k) == h for k, h in A1C_OBS.items() if "instance-catalog" not in k))
    return ok, {"identity_false": [k for k, v in s["identity"].items() if not v]}


# ------------------------------------------------------------------ RENDER CONTROL
def c06(x):
    o = x.run / "observations"
    dirs = sorted(p.name for p in o.iterdir())
    acq = {g: sorted(p.name for p in (o / g / "acquisition").iterdir()) for g in GAZES if (o / g).is_dir()}
    ev = {g: sorted(p.name for p in (o / g / "evaluation_only").iterdir()) for g in GAZES if (o / g).is_dir()}
    exr = sum(1 for g in GAZES for s in "LR" if (o / g / f"evaluation_only/raw_{s}.exr").is_file())
    ok = (dirs == ["evaluation_only", *GAZES, "render-control.json"]
          and all(v == ["acquisition.json", "calibration.json", "rgb-observation.npz"] for v in acq.values())
          and all(v == ["raw_L.exr", "raw_R.exr", "reference-observation.npz"] for v in ev.values())
          and len(acq) == 3 and exr == 6 and x.j("observations/render-control.json")["eye_renders"] == 6)
    return ok, {"dirs": dirs, "eye_renders": exr}


def c07(x):
    out = {}
    for g in GAZES:
        a = x.acq(g)
        hdr = {s: exr_header(x.run / f"observations/{g}/evaluation_only/raw_{s}.exr").get("cycles.interior.samples")
               for s in "LR"}
        old = {s: exr_header(x.a1c(f"observations/{g}/evaluation_only/raw_{s}.exr")).get("cycles.interior.samples")
               for s in "LR"}
        out[g] = {"record": a["spp"] == SPP, "readback": a["settings"]["samples"] == SPP,
                  "primary": a["primary_camera_samples"] == 2 * RAW * RAW * SPP,
                  "exr": hdr == {"L": str(SPP), "R": str(SPP)}, "accepted_exr": old == {"L": "256", "R": "256"}}
    return all(all(v.values()) for v in out.values()), out


def c08(x):
    out = {}
    for g in GAZES:
        a, b = x.acq256(g)["settings"], x.acq(g)["settings"]
        diff = sorted(k for k in set(a) | set(b) if k != "samples" and a.get(k) != b.get(k))
        fixed = (b["denoising"] is False and b["adaptive_sampling"] is False and b["pixel_filter"] == "BOX"
                 and b["filter_width"] == 1.0 and b["resolution_wh"] == [RAW, RAW] and b["resolution_percentage"] == 100
                 and b["motion_blur"] is False and b["engine"] == "CYCLES" and b["cycles_device"] == "GPU"
                 and x.acq(g)["device"] == "OPTIX")
        out[g] = {"differences_except_samples": diff, "fixed_values": fixed}
    return all(not v["differences_except_samples"] and v["fixed_values"] for v in out.values()), out


def c09(x):
    out = {}
    for g in GAZES:
        rel = f"observations/{g}/acquisition/calibration.json"
        b_new, b_old = (x.run / rel).read_bytes(), x.a1c(rel).read_bytes()
        out[g] = {"byte_identical": b_new == b_old and hashlib.sha256(b_new).hexdigest() == A1C_OBS[rel],
                  "record_hash": x.acq(g)["calibration_sha256"] == A1C_OBS[rel],
                  "gaze": tuple(x.acq(g)["gaze_yaw_pitch_deg"]) == GAZE_TABLE[g] == tuple(x.calib(g)["gaze_yaw_pitch_deg"])}
    return all(all(v.values()) for v in out.values()), out


def c10(x):
    out = {}
    flip = np.diag([1.0, -1.0, -1.0])
    for g in GAZES:
        c = x.calib(g)
        rec, acc = x.acq(g)["camera_matrix_world_lr"], x.acq256(g)["camera_matrix_world_lr"]
        rwh, o = np.asarray(c["head_R_wh"], float), np.asarray(c["head_origin_w_m"], float)
        own = {}
        for eye in c["eyes"]:
            m = np.eye(4)
            m[:3, :3] = rwh @ np.asarray(eye["R_hc"], float) @ flip
            m[:3, 3] = o + rwh @ np.asarray(eye["centre_h_m"], float)
            own[eye["name"]] = m
        out[g] = {"vs_accepted": max(abs(p - q) for s in "LR" for ra, rb in zip(rec[s], acc[s]) for p, q in zip(ra, rb)),
                  "vs_own": float(max(np.abs(np.asarray(rec[s]) - own[s]).max() for s in "LR"))}
    return all(v["vs_accepted"] <= POSE_TOL and v["vs_own"] <= POSE_TOL for v in out.values()), out


def c11(x):
    out = {}
    for g in GAZES:
        out[g] = {s: own_exr(exr_header(x.a1c(f"observations/{g}/evaluation_only/raw_{s}.exr")),
                             exr_header(x.run / f"observations/{g}/evaluation_only/raw_{s}.exr")) for s in "LR"}
    return all(not b for v in out.values() for b in v.values()), out


def c12(x):
    out = {g: x.acq(g)["render_seeds_lr"] for g in GAZES}
    return all(v == SEEDS and v["L"] != v["R"] for v in out.values()) and all(
        x.acq256(g)["render_seeds_lr"] == SEEDS for g in GAZES), out


def c13(x):
    ctl = x.j("observations/render-control.json")
    inst = (jload(x.run / "observations/evaluation_only/instance-catalog.json")["instances"]
            == jload(x.a1c("observations/evaluation_only/instance-catalog.json"))["instances"])
    blend = all(os.path.realpath(x.acq(g)["blend"]) == BLEND_REAL for g in GAZES)
    return (ctl["blend_sha256"] == BLEND_SHA and sha256(BLEND_REAL) == BLEND_SHA and inst and blend
            and ctl["scene_object_list_identical"]), {"instances": inst, "blend_realpath": blend}


def c14(x):
    ctl = x.j("observations/render-control.json")
    own = {g: own_classify(x.acq256(g), x.acq(g)) for g in GAZES}
    stored = {g: ctl["gazes"][g]["acquisition"]["failed"] for g in GAZES}
    checks = all(all(ctl["gazes"][g]["checks"].values()) and ctl["gazes"][g]["ok"] for g in GAZES)
    return (ctl["ok"] and checks and all(not v for v in own.values()) and all(not v for v in stored.values())
            and ctl["exactly_three_gazes"]), {"own_failed": own, "stored_failed": stored}


def c15(x):
    renders = [e for e in x.log if e["command"] == "render-4096"]
    blog = (x.run / "logs/render-4096-blender.log").read_text() if (x.run / "logs/render-4096-blender.log").is_file() else ""
    observed = [ln for ln in blog.splitlines() if ln.startswith("[ab1d2-render] observed gaze-")]
    times = sorted(x.acq(g)["created_utc"] for g in GAZES)
    within = bool(renders) and times[-1] <= renders[0]["finished_utc"]
    return (len(renders) == 1 and renders[0]["status"] == "ok" and len(observed) == 3
            and blog.count("[ab1d2-render] COMPLETE canonical") == 1 and within), {
        "render_entries": len(renders), "observed_lines": len(observed), "created_within_render": within}


def c16(x):
    pf = x.j("preflight/preflight.json")
    gz = pf["gazes"]
    ok = (pf["rendered"] is False and pf["spp"] == SPP and set(gz) == set(GAZES) and all(
        v["ok"] and v["calibration_max_abs_diff_built_vs_accepted"] == 0.0 and v["reserialized_calibration_byte_identical"]
        and not v["settings_differences_except_samples"] and v["settings"]["samples"] == SPP
        and max(v["set_camera_matrix_max_abs_diff_vs_accepted"].values()) <= POSE_TOL for v in gz.values()))
    return ok, {g: v["ok"] for g, v in gz.items()}


def c17(x):
    pt, rh = x.j("preflight/preflight-tests.json"), x.j("synthetic/rehearsal/rehearsal-report.json")
    commit = {e["code"]["commit"] for e in x.log if e["command"] in CANONICAL}
    ok = (pt["passed"] and all(c["passed"] for c in pt["cases"]) and len(pt["cases"]) >= 60 and not pt["code"]["dirty"]
          and rh["passed"] and all(rh["cases"].values()) and not rh["code"]["dirty"]
          and {pt["code"]["commit"], rh["code"]["commit"]} == commit
          and "exr_channels_lr" in rh["detail"]["negative_control"]["record_failed"])
    return ok, {"preflight_cases": len(pt["cases"]), "rehearsal": rh["cases"]}


# ------------------------------------------------------------------ MATCHER
def c18(x):
    fz = x.j("match/correspondence-freeze.json")
    a1d_fz = jload(x.a1d("match/correspondence-freeze.json"))
    a1d_man = jload(x.a1d("manifest.json"))["files"]
    out = {"config": fz["matcher_config_sha256"] == a1d_fz["matcher_config_sha256"],
           "code": all(fz["matcher_code"].get(p) == CODE_PINS[p] for p in ("tools/active_bootstrap/ab1d_match.py",
                                                                           "tools/active_bootstrap/ab1d_spec.py",
                                                                           "tools/active_bootstrap/ab1d_run.py",
                                                                           "tools/fsg_stereo.py", "tools/fsg_geometry.py"))}
    for g in GAZES:
        ms = x.j(f"match/{g}/match-summary.json")
        a1d_ms = A1D / f"match/{g}/match-summary.json"
        same_matcher = sha256(a1d_ms) == a1d_man.get(f"match/{g}/match-summary.json") and ms["matcher"] == jload(a1d_ms)["matcher"]
        out[g] = (ms["matcher_config_sha256"] == a1d_fz["matcher_config_sha256"] and same_matcher
                  and ms["threads"] == 16 and ms["batch"] == 128)
    return all(out.values()), out


def static_scan(x) -> dict:
    found = {}
    for name in TOOLS:
        if name == "check_ab1d2.py":
            continue
        src = x.src(name)
        tree = ast.parse(src)
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                if fname == "Params":
                    hits.append("Params(...) override")
                if fname == "setattr" and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in (
                        "M", "DS", "AD", "AR", "CO"):
                    hits.append(f"setattr on module {node.args[0].id}")
                if fname == "run_match_gaze" and (len(node.args) != 3 or node.keywords):
                    hits.append("run_match_gaze with extra arguments")
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in (
                            "M", "DS", "AD", "AR", "CO", "FS"):
                        hits.append(f"assignment to {t.value.id}.{t.attr}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                hits += [f"import {m}" for m in mods if any(m == f or m.startswith(f + ".") for f in FORBIDDEN_IMPORTS)]
        if name in TOKEN_SCAN:
            hits += [f"token {t}" for t in FORBIDDEN_TOKENS if t in src]
        found[name] = hits
    return found


def c19(x):
    spec, params = x.live_constants()
    spec_ok = {k: spec[k] == v for k, v in CONSTANTS.items()}
    par_ok = {k: params[k] == CONSTANTS[k] for k in params}
    scan = static_scan(x)
    hits = {k: [h for h in v if not h.startswith("token") and not h.startswith("import")] for k, v in scan.items()}
    return all(spec_ok.values()) and all(par_ok.values()) and not any(hits.values()), {
        "spec": [k for k, v in spec_ok.items() if not v], "params": [k for k, v in par_ok.items() if not v], "hits": hits}


def c20(x):
    out = {}
    for g in GAZES:
        r = x.j(f"match/{g}/match-opened-files.json")
        want = {f"RUN/observations/{g}/acquisition/calibration.json", f"RUN/observations/{g}/acquisition/rgb-observation.npz"}
        opens = [x.rrel(e["path"]) for e in r["events"] if e.get("event") == "open"
                 and not e["path"].endswith(CODE_SUFFIXES)]
        bad = [p for p in opens if "/evaluation_only/" in p or p.endswith(".exr") or p.startswith(str(A1C) + "/")
               or p.startswith(str(A1D) + "/") or p.startswith("RUN/evaluation/") or "oracle" in p.lower()]
        out[g] = {"reads": {x.rrel(p) for p in r["data_reads"]} == want, "violations": not r["violations"],
                  "modules": not any(r["modules_loaded"].values()), "tripwires": not r["cv2_tripwire_calls"],
                  "no_truth_reads": not bad}
    return all(all(v.values()) for v in out.values()), out


def c21(x):
    out = {}
    for g in GAZES:
        idx = subset_idx(x, g)
        gl, gr = x.gray(g, "4096")
        key = (g, sha256(x.run / f"observations/{g}/acquisition/calibration.json"),
               sha256(x.run / f"observations/{g}/acquisition/rgb-observation.npz"))
        own = CA.own_match(x.calib(g), gl, gr, idx, cache_key=("ab1d2",) + key)
        cmp = CA.compare_records(x.rec(g), own, idx)
        out[g] = {k: v for k, v in cmp.items() if v} | {"rows": int(idx.size)}
    return all(len(v) == 1 for v in out.values()), out


def c22(x):
    out = {}
    for g in GAZES:
        rec, p = x.rec(g), x.n(f"match/{g}/natural-correspondences.npz")
        v = rec["valid_match"]
        out[g] = (set(p) == {"left_core_row", "left_core_col", "uv_L", "uv_R"}
                  and np.array_equal(p["left_core_row"], rec["left_core_row"][v])
                  and np.array_equal(p["left_core_col"], rec["left_core_col"][v])
                  and np.array_equal(p["uv_L"], rec["uv_L"][v]) and np.array_equal(p["uv_R"], rec["uv_R_est"][v]))
    return all(out.values()), out


# ------------------------------------------------------------------ GEOMETRY
def c23(x):
    out = {}
    for g in GAZES:
        a, b = x.rec256(g), x.rec(g)
        diff = {}
        for k in GEO_FIELDS:
            u, v = np.asarray(a[k]), np.asarray(b[k])
            same = u.shape == v.shape and u.dtype == v.dtype and (
                np.array_equal(u, v, equal_nan=True) if u.dtype.kind == "f" else np.array_equal(u, v))
            if not same:
                diff[k] = True
        out[g] = sorted(diff)
    stored = x.j("match/search-geometry-identity.json")
    return stored["ok"] and not any(out.values()), {"own_differing": out, "stored_ok": stored["ok"]}


def c24(x):
    import ab1b_geometry as BG
    out = {}
    for g in GAZES:
        c = x.calib(g)
        p, geo = x.n(f"match/{g}/natural-correspondences.npz"), x.n(f"spherical/{g}/epipolar-result.npz")
        cl, cr = CA.OwnCam(c["eyes"][0]), CA.OwnCam(c["eyes"][1])
        dl, dr = cl.ray(p["uv_L"][:, 0], p["uv_L"][:, 1]), cr.ray(p["uv_R"][:, 0], p["uv_R"][:, 1])
        tl, tr = CA.own_theta(dl), CA.own_theta(dr)
        rho = float(c["ipd_m"]) * np.sin(tl) * np.sin(tr) / np.sin(tr - tl)
        pp = cl.o + (rho / np.sin(tl))[:, None] * dl
        summ = x.j(f"spherical/{g}/spherical-summary.json")
        sr = x.j(f"spherical/{g}/spherical-opened-files.json")
        want = {f"RUN/observations/{g}/acquisition/calibration.json", f"RUN/match/{g}/natural-correspondences.npz"}
        out[g] = {"max_P_diff_m": float(np.abs(pp - geo["P_epi"]).max(initial=0)),
                  "config": summ["geometry_config_sha256"] == BG.SP.config_sha256(BG.SP.GEOMETRY),
                  "reads": {x.rrel(q) for q in sr["data_reads"]} == want and not sr["violations"],
                  "modules": not any(sr["modules_loaded"].values())}
    return all(v["max_P_diff_m"] <= 1e-9 and v["config"] and v["reads"] and v["modules"] for v in out.values()), out


# ------------------------------------------------------------------ FREEZE / TRUTH
def order_of(x, cmd) -> int:
    cmds = [e["command"] for e in x.log if e["status"] == "ok"]
    return cmds.index(cmd) if cmd in cmds else -1


def c25(x):
    fz = x.j("freeze/observation-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    want = {f"observations/{g}/acquisition/{n}" for g in GAZES for n in ("acquisition.json", "calibration.json",
                                                                         "rgb-observation.npz")}
    covers = want <= set(fz["files"]) and "observations/render-control.json" in fz["files"]
    order = 0 <= order_of(x, "render-4096") < order_of(x, "freeze-observation") < order_of(x, "match")
    return (not bad and covers and order and fz["spp"] == SPP and fz["seeds"] == SEEDS
            and fz["calibrations"] == {g: A1C_OBS[f"observations/{g}/acquisition/calibration.json"] for g in GAZES}), {
        "mismatch": bad, "covers": covers, "order": order}


def c26(x):
    fz, ofz = x.j("match/correspondence-freeze.json"), x.j("freeze/observation-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    inputs = all(fz["matcher_inputs"][g]["rgb_observation"]["sha256"] == ofz["rgb_observations"][g]
                 and fz["matcher_inputs"][g]["calibration"]["sha256"] == ofz["calibrations"][g] for g in GAZES)
    used = all(x.j(f"spherical/{g}/spherical-summary.json")["inputs"]["correspondences"]["sha256"]
               == fz["files"][f"match/{g}/natural-correspondences.npz"] for g in GAZES)
    order = 0 <= order_of(x, "match") < order_of(x, "freeze-correspondence") < order_of(x, "spherical")
    return (not bad and inputs and used and order and fz["search_geometry_identical"]
            and fz["observation_freeze_sha256"] == sha256(x.run / "freeze/observation-freeze.json")), {
        "mismatch": bad, "inputs": inputs, "spherical_used_frozen": used, "order": order}


def c27(x):
    fz = x.j("freeze/geometry-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    order = 0 <= order_of(x, "spherical") < order_of(x, "freeze-geometry") < order_of(x, "evaluate-paired")
    pre = all(all(v.values()) for v in fz["preconditions"].values())
    return not bad and order and pre, {"mismatch": bad, "order": order, "preconditions": pre}


def c28(x):
    ev = x.j("evaluation/evaluation-opened-files.json")
    labels = [e["label"] for e in ev["events"] if e.get("event") == "mark"]
    allowed = ({str(x.a1c(k)) for k in A1C_BENCH} | {str(A1C / k) for k in A1C_OBS if "acquisition" in k
                                                    and not k.endswith("acquisition.json")}
               | {str(A1D / k) for k in A1D_PINS})
    reads = [x.rrel(p) for p in ev["data_reads"]]
    outside = [p for p in reads if not p.startswith("RUN/") and p not in allowed]
    run_truth = [p for p in reads if p.startswith("RUN/") and ("/evaluation_only/" in p or p.endswith(".exr"))]
    opens = [x.rrel(e["path"]) for e in ev["events"] if e.get("event") == "open"]
    run_truth += [p for p in opens if p.startswith("RUN/observations/") and "/evaluation_only/" in p]
    s = x.j("evaluation/evaluation-summary.json")
    bench = s["benchmark_files"] == A1C_BENCH
    repro = all(v["ok"] for v in s["reproduction_256"].values())
    ok = (not ev["violations"] and labels == ["freezes_verified", "reference_access_begins"] and not outside
          and not run_truth and bench and len(A1C_BENCH) == 9 and repro)
    return ok, {"labels": labels, "outside": outside[:5], "ab1d2_truth_reads": run_truth[:5], "reproduction": repro}


# ------------------------------------------------------------------ PAIRED EVALUATION
def own_eval(x: Ctx, g) -> dict:
    def f():
        c, rec = x.calib(g), x.rec(g)
        ora = x.c(("ora", g), lambda: npz(x.a1c(f"oracle/{g}/oracle-correspondences.npz")))
        oi = ora["left_core_row"].astype(np.int64) * CORE + ora["left_core_col"]
        ov = np.zeros(CORE * CORE, bool)
        ov[oi] = True
        e_idx = np.nonzero(ov & rec["valid_match"])[0]
        uv = np.full((CORE * CORE, 2), np.nan)
        uv[oi] = ora["uv_R"]
        cl, cr = CA.OwnCam(c["eyes"][0]), CA.OwnCam(c["eyes"][1])
        th_or = CA.own_theta(cr.ray(uv[e_idx, 0], uv[e_idx, 1]))
        e_th = rec["theta_R_est"][e_idx] - th_or
        r, cc = np.divmod(e_idx, CORE)
        ph = CA.own_phi(cl.ray((cc + ORIGIN).astype(float), (r + ORIGIN).astype(float)))
        qu, qv, _ = cr.proj(CA.own_dir(th_or, ph))
        q, t = rec["q_inf"][e_idx], rec["line_dir"][e_idx]
        s_oc = (qu - q[:, 0]) * t[:, 0] + (qv - q[:, 1]) * t[:, 1]

        def lt(s):
            return CA.own_theta(cr.ray(q[:, 0] + s * t[:, 0], q[:, 1] + s * t[:, 1]))
        scale = lt(s_oc + 0.5) - lt(s_oc - 0.5)
        within = np.abs(rec["peak_s"][e_idx] - s_oc[:, None]) <= PEAK_RADIUS
        rank = np.where(within.any(1), np.argmax(within, 1) + 1, TOPK + 1)
        return {"ov": ov, "e_idx": e_idx, "th_or": th_or, "e_th": e_th, "s_oc": s_oc, "scale": scale,
                "e_px": e_th / scale, "rank": rank, "ph": ph}
    return x.c(("own_eval", g), f)


def c29(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["absolute_4096"]
        same = np.array_equal(eval_idx(e), o["e_idx"])
        d = float(np.abs(e["e_theta"] - o["e_th"]).max(initial=0)) if same else math.inf
        cnt = s["counts"]
        out[g] = {"same_set": same, "max_e_theta_diff": d,
                  "counts": cnt["evaluable"] == o["e_idx"].size and cnt["oracle_correspondences"] == int(o["ov"].sum())
                  and cnt["natural_valid"] == int(x.rec(g)["valid_match"].sum()),
                  "summary": qmatch(s["primary"]["e_theta_abs_rad"], qof(np.abs(o["e_th"])), rel=1e-6, ab=1e-12)}
    return all(v["same_set"] and v["max_e_theta_diff"] <= 1e-12 and v["counts"] and v["summary"] for v in out.values()), out


def c30(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["absolute_4096"]["primary"]
        if not np.array_equal(eval_idx(e), o["e_idx"]):
            out[g] = {"same_set": False}
            continue
        rs = float(np.abs(e["local_scale_rad_per_px"] / o["scale"] - 1).max(initial=0))
        rp = float((np.abs(e["e_px"] - o["e_px"]) / np.maximum(np.abs(o["e_px"]), 1e-6)).max(initial=0))
        fr = {f"{b:g}": float((np.abs(o["e_px"]) <= b).mean()) for b in (0.10, 0.25, 0.50, 1.00)}
        out[g] = {"same_set": True, "scale_rel": rs, "epx_rel": rp,
                  "fractions": all(abs(s["px_equivalent_fractions"][k] - v) <= 1e-12 for k, v in fr.items()),
                  "summary": qmatch(s["px_equivalent_abs"], qof(np.abs(o["e_px"])), rel=1e-5, ab=1e-9)}
    return all(v.get("same_set") and v["scale_rel"] <= 1e-6 and v["epx_rel"] <= 1e-5 and v["fractions"] and v["summary"]
               for v in out.values()), out


def c31(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["absolute_4096"]["landscape"]
        if not np.array_equal(eval_idx(e), o["e_idx"]):
            out[g] = {"same_set": False}
            continue
        tops = {f"top{k}": float((o["rank"] <= k).mean()) for k in (1, 3, 5, 8)} | {
            "worse_than_top8": float((o["rank"] > TOPK).mean())}
        idx = subset_idx(x, g)
        pos = np.nonzero(np.isin(o["e_idx"], idx))[0]
        c = x.calib(g)
        gl, gr = x.gray(g, "4096")
        cl, cr = CA.OwnCam(c["eyes"][0]), CA.OwnCam(c["eyes"][1])
        dlt = math.atan(1.0 / cl.fx)
        ii = o["e_idx"][pos]
        r, cc = np.divmod(ii, CORE)
        dl = cl.ray((cc + ORIGIN).astype(float), (r + ORIGIN).astype(float))
        lv, _ = CA.own_patch(cl, gl, CA.own_theta(dl), CA.own_phi(dl), dlt)
        rv, rex = CA.own_patch(cr, gr, o["th_or"][pos], o["ph"][pos], dlt)
        zor = np.where(rex & (np.std(rv, axis=-1) >= 0.5), CA.own_zncc(lv, rv), np.nan)
        out[g] = {"same_set": True, "s_oc": float(np.abs(e["s_oracle_on_curve"] - o["s_oc"]).max(initial=0)),
                  "ranks": bool(np.array_equal(e["oracle_rank"], o["rank"])),
                  "tops": all(abs(s["top_fractions"][k] - v) <= 1e-12 for k, v in tops.items()),
                  "subset_zncc": float(np.nanmax(np.abs(e["zncc_oracle"][pos] - zor), initial=0)),
                  "nan_match": bool(np.array_equal(np.isnan(e["zncc_oracle"][pos]), np.isnan(zor)))}
    return all(v.get("same_set") and v["s_oc"] <= 1e-6 and v["ranks"] and v["tops"] and v["subset_zncc"] <= 1e-8
               and v["nan_match"] for v in out.values()), out


def c32(x):
    """The 256-spp side of the pairing is exactly the accepted AB1d evaluation."""
    out = {}
    acc = jload(x.a1d("evaluation/evaluation-summary.json"))
    for g in GAZES:
        p, a = x.par(g), x.evr256(g)
        ai = eval_idx(a)
        pos = np.searchsorted(ai, p["core_index"].astype(np.int64))
        ok_idx = bool(np.all(ai[np.clip(pos, 0, ai.size - 1)] == p["core_index"]))
        out[g] = {"index": ok_idx,
                  "E256": ok_idx and np.array_equal(p["E256"], np.abs(a["e_px"][pos])),
                  "Z256": ok_idx and np.array_equal(p["Z256"], a["zncc_oracle"][pos], equal_nan=True),
                  "rank256": ok_idx and np.array_equal(p["rank256"], a["oracle_rank"][pos]),
                  "error3d256": ok_idx and np.array_equal(p["error3d256"], a["error_3d_vs_perfect_m"][pos]),
                  "summary": x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["accepted_256"] == acc["per_gaze"][g]}
    return all(all(v.values()) for v in out.values()), out


def own_pair(x: Ctx, g) -> dict:
    def f():
        a, b = x.evr256(g), x.evr(g)
        ia, ib = eval_idx(a), eval_idx(b)
        common = np.intersect1d(ia, ib)
        pa, pb = np.searchsorted(ia, common), np.searchsorted(ib, common)
        E0, E1 = np.abs(a["e_px"][pa]), np.abs(b["e_px"][pb])
        return {"common": common, "E0": E0, "E1": E1, "Z0": a["zncc_oracle"][pa], "Z1": b["zncc_oracle"][pb],
                "r0": a["oracle_rank"][pa], "r1": b["oracle_rank"][pb], "s0": a["s_oracle_on_curve"][pa],
                "s1": b["s_oracle_on_curve"][pb], "x0": a["error_3d_vs_perfect_m"][pa],
                "x1": b["error_3d_vs_perfect_m"][pb], "only256": int(np.setdiff1d(ia, ib).size),
                "only4096": int(np.setdiff1d(ib, ia).size)}
    return x.c(("pair", g), f)


def c33(x):
    out = {}
    for g in GAZES:
        o, p = own_pair(x, g), x.par(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["paired"]
        n = o["common"].size
        dE = o["E1"] - o["E0"]
        g0, g1 = o["E0"] <= GOOD, o["E1"] <= GOOD
        trans = {"bad_to_good": int((~g0 & g1).sum()), "good_to_good": int((g0 & g1).sum()),
                 "good_to_bad": int((g0 & ~g1).sum()), "bad_to_bad": int((~g0 & ~g1).sum())}
        e = s["error"]
        out[g] = {"common": np.array_equal(p["core_index"], o["common"]) and s["counts"]["common"] == n
                  and s["counts"]["only_256"] == o["only256"] and s["counts"]["only_4096"] == o["only4096"],
                  "arrays": np.array_equal(p["delta_E"], dE) and np.array_equal(p["E4096"], o["E1"]),
                  "fractions": n > 0 and abs(e["fraction_improved"] - float((o["E1"] < o["E0"] - EPS_PX).mean())) <= 1e-12
                  and abs(e["fraction_worsened"] - float((o["E1"] > o["E0"] + EPS_PX).mean())) <= 1e-12
                  and abs(e["fraction_equal"] - float((np.abs(dE) <= EPS_PX).mean())) <= 1e-12,
                  "median_delta": abs(e["median_delta_E"] - float(np.median(dE))) <= 1e-12,
                  "quantiles": qmatch(e["delta_E"], qof(dE)) and qmatch(e["E4096"], qof(o["E1"])),
                  "transitions": {k: s["transitions_1px"][k]["count"] for k in trans} == trans}
    return all(all(v.values()) for v in out.values()), out


def own_competing(rec, idx, s_oc):
    ps, pz = rec["peak_s"][idx], rec["peak_zncc"][idx]
    far = np.isfinite(ps) & np.isfinite(pz) & (np.abs(ps - s_oc[:, None]) > PEAK_RADIUS)
    best = np.full(idx.size, np.nan)
    for i in range(idx.size):
        if far[i].any():
            best[i] = pz[i][far[i]].max()
    return best


def c34(x):
    out = {}
    for g in GAZES:
        o, p = own_pair(x, g), x.par(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["paired"]
        n = o["common"].size
        fin = np.isfinite(o["Z0"]) & np.isfinite(o["Z1"])
        dZ = o["Z1"] - o["Z0"]
        ranks = {}
        for k in (1, 3, 8):
            a, b = o["r0"] <= k, o["r1"] <= k
            ranks[k] = {"not_to_in": int((~a & b).sum()), "in_to_in": int((a & b).sum()),
                        "in_to_not": int((a & ~b).sum()), "not_to_not": int((~a & ~b).sum())}
        c0 = own_competing(x.rec256(g), o["common"], o["s0"])
        c1 = own_competing(x.rec(g), o["common"], o["s1"])
        out[g] = {"zncc": qmatch(s["zncc"]["delta_Z"], qof(dZ[fin]))
                  and abs(s["zncc"]["fraction_increased"] - float((fin & (dZ > ZEPS_ZNCC)).sum() / n)) <= 1e-12,
                  "ranks": all({kk: s["ranks"][f"top{k}"][kk]["count"] for kk in ranks[k]} == ranks[k] for k in ranks),
                  "competing": np.array_equal(p["competing256"], c0, equal_nan=True)
                  and np.array_equal(p["competing4096"], c1, equal_nan=True),
                  "margin": np.array_equal(p["margin4096"], x.rec(g)["peak_margin"][o["common"]], equal_nan=True),
                  "oracle_on_curve_same": bool(np.array_equal(o["s0"], o["s1"]))}
    return all(all(v.values()) for v in out.values()), out


def c35(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        c = x.calib(g)
        geo = x.n(f"spherical/{g}/epipolar-result.npz")
        pn = np.full((CORE * CORE, 3), np.nan)
        pn[geo["left_core_row"].astype(np.int64) * CORE + geo["left_core_col"]] = geo["P_epi"]
        perf = x.c(("perf", g), lambda: npz(x.a1c(f"spherical/{g}/epipolar-result.npz")))
        pp = np.full((CORE * CORE, 3), np.nan)
        pp[perf["left_core_row"].astype(np.int64) * CORE + perf["left_core_col"]] = perf["P_epi"]
        pos = x.c(("pos", g), lambda: npz(x.a1c(f"observations/{g}/evaluation_only/reference-observation.npz"))["position_w_L"])
        ei = o["e_idx"]
        r, cc = ei // CORE + ORIGIN, ei % CORE + ORIGIN
        pref = (np.asarray(pos)[r, cc].astype(np.float64) - np.asarray(c["head_origin_w_m"])) @ np.asarray(c["head_R_wh"])
        e3p = np.linalg.norm(pn[ei] - pp[ei], axis=1)
        e3r = np.linalg.norm(pn[ei] - pref, axis=1)
        m = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["absolute_4096"]["metric"]
        pm = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["paired"]["metric"]
        op = own_pair(x, g)
        fr = {f"{b:g}": float((e3p <= b).mean()) for b in (0.012, 0.025, 0.050)}
        out[g] = {"arrays": np.array_equal(eval_idx(e), ei) and bool(np.allclose(e["error_3d_vs_perfect_m"], e3p, rtol=0,
                                                                                  atol=1e-12))
                  and bool(np.allclose(e["error_3d_vs_position_m"], e3r, rtol=0, atol=1e-9)),
                  "summary": qmatch(m["vs_perfect"]["error_3d_m"], qof(e3p)) and qmatch(m["vs_position"]["error_3d_m"], qof(e3r), ab=1e-9)
                  and all(abs(m["vs_perfect"]["fraction_3d_within_m"][k] - v) <= 1e-12 for k, v in fr.items()),
                  "paired": qmatch(pm["delta_m"], qof(op["x1"] - op["x0"]))
                  and abs(pm["fraction_improved"] - float((op["x1"] < op["x0"] - EPS_M).mean())) <= 1e-12}
    return all(all(v.values()) for v in out.values()), out


def c36(x):
    out = {}
    o_, n_ = ORIGIN, CORE
    for g in GAZES:
        d = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["paired"]["diagnostics"]
        g2, g4 = x.gray(g, "256"), x.gray(g, "4096")
        ok_gc = True
        for k, s in enumerate("LR"):
            dd = g4[k] - g2[k]
            dc = dd[o_:o_ + n_, o_:o_ + n_]
            st = d["gray_change"][s]
            ok_gc &= (qmatch(st["raster"]["abs"], qof(np.abs(dd)), ab=1e-9) and qmatch(st["core"]["abs"], qof(np.abs(dc)), ab=1e-9)
                      and abs(st["core"]["signed_mean"] - float(dc.mean())) <= 1e-9)
        ora = x.c(("ora", g), lambda: npz(x.a1c(f"oracle/{g}/oracle-correspondences.npz")))
        u, v = ora["uv_L"][:, 0].astype(np.int64), ora["uv_L"][:, 1].astype(np.int64)
        prox = {}
        for cond, (gl, gr) in (("256", g2), ("4096", g4)):
            rv, _ = CA.own_bilinear(gr, ora["uv_R"][:, 0], ora["uv_R"][:, 1])
            dv = gl[v, u] - rv
            dv = dv[np.isfinite(dv)]
            prox[cond] = 1.4826 * float(np.median(np.abs(dv - np.median(dv))))
        ok_p = all(abs(d["PROXY_LR"][k] - prox[k]) <= 1e-9 for k in prox)
        labels = all("PROXY" in d["labels"][k] for k in ("PROXY_LR", "PROXY_HP")) and "not a noise" in d["labels"]["gray_change"]
        tex = qmatch(d["left_patch_std_all"]["4096"], qof(x.rec(g)["left_patch_std_u8"]), ab=1e-9)
        out[g] = {"gray_change": bool(ok_gc), "proxy_lr": ok_p, "labels": labels, "texture": tex}
    return all(all(v.values()) for v in out.values()), out


# ------------------------------------------------------------------ VISUALS
def c37(x):
    import ab1d2_visuals as V
    man = jload(x.vis / "visuals-manifest.json")
    inputs = ["evaluation/evaluation-summary.json"] + [f"{d}/{g}/{n}" for g in GAZES for d, n in (
        ("evaluation", "evaluation-result.npz"), ("evaluation", "paired-result.npz"), ("match", "matcher-record.npz"))] + [
        f"observations/{g}/acquisition/{n}" for g in GAZES for n in ("calibration.json", "rgb-observation.npz")]
    key = tuple(sha256(x.run / n) for n in inputs)
    if key not in _REGEN:
        _REGEN.clear()
        _REGEN[key] = V.render_all(x.run)[0]
    figs = _REGEN[key]
    out = {}
    for name in FIGURES:
        p = x.vis / name
        out[name] = {"exists": p.is_file(), "hash": p.is_file() and sha256(p) == man["figures"][name]["sha256"],
                     "badges": man["figures"][name]["badges"] == BADGES[name],
                     "regenerated": p.is_file() and V.png_bytes(figs[name]) == p.read_bytes()}
    return set(man["figures"]) == set(FIGURES) and all(all(v.values()) for v in out.values()), out


def c38(x):
    man = jload(x.vis / "visuals-manifest.json")
    acc = jload(A1D_VIS_MAN[0])["examples"]
    same = all(man["examples"][g] == acc[g] for g in GAZES) and len([e for g in GAZES for e in man["examples"][g]]) == 12
    disp = man["displays"]
    st = all(disp["stretch"][g]["applied_to"] == ["256", "4096"] and disp["stretch"][g]["label_drawn"] is True
             and disp["stretch"][g]["label"] == "CONTRAST-STRETCHED" for g in GAZES)
    ident = "identical for 256 and 4096" in disp["images"] and "linear_to_u8" in disp["images"]
    src = man["examples_source"] == {"path": str(A1D_VIS_MAN[0]), "sha256": A1D_VIS_MAN[1]}
    return same and st and ident and src, {"examples_reused": same, "stretch_labelled": st, "transform": ident,
                                           "examples_source": src}


# ------------------------------------------------------------------ PROCESS
def c39(x):
    cmds = [e["command"] for e in x.log]
    unknown = [c for c in cmds if c not in ORDER]
    canon = [c for c in cmds if c in CANONICAL]
    ok_status = all(e["status"] == "ok" for e in x.log if e["command"] in CANONICAL + ("preflight-tests", "rehearse"))
    commits = {e["code"]["commit"] for e in x.log if e["command"] in CANONICAL + ("preflight-tests", "rehearse")}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] for e in x.log if e["command"] in CANONICAL)
    pre = [c for c in cmds if c in ("preflight-tests", "rehearse")]
    first_render = cmds.index("render-4096") if "render-4096" in cmds else -1
    before = set(cmds[:max(first_render, 0)]) >= {"source", "preflight-tests", "rehearse", "preflight"}
    vis = "visualize" in cmds and cmds.index("visualize") > cmds.index("evaluate-paired") if "evaluate-paired" in cmds else False
    ok = (canon == list(CANONICAL) and not unknown and ok_status and len(commits) == 1 and clean
          and pre == ["preflight-tests", "rehearse"] and before and vis)
    return ok, {"canonical": canon, "unknown": unknown, "commits": sorted(commits), "clean": clean, "before_render": before}


def c40(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    listed = set(man["files"])
    present = {str(p.relative_to(x.run)) for p in x.run.rglob("*") if p.is_file()} - {
        "manifest.json", "check-summary.json", "process-log.jsonl"}
    changed = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(changed - DECLARED)
    return not bad and listed == present and not extra, {"mismatch": bad[:5], "unlisted": sorted(present - listed)[:5],
                                                         "undeclared_changes": extra}


def c41(x):
    scan = static_scan(x)
    hits = {k: [h for h in v if h.startswith(("token", "import"))] for k, v in scan.items()}
    pose = all(x.acq(g)["eye_pose"] == x.acq256(g)["eye_pose"] for g in GAZES)
    cmds = {e["command"] for e in x.log}
    scope = not (cmds & {"head-recenter", "recenter", "controller", "controller-step", "denoise", "match-8192"})
    return not any(hits.values()) and pose and scope, {"hits": hits, "eye_pose_unchanged": pose, "scope": scope}


CHECKS = [
    ("01", "canonical repository, branch and ancestry", c01), ("02", "accepted code pins unchanged", c02),
    ("03", "accepted AB1c observation and benchmark pins", c03), ("04", "accepted AB1d product pins", c04),
    ("05", "source manifest identity", c05), ("06", "exactly 3 gazes and 6 eye renders", c06),
    ("07", "spp 4096 in record, readback and EXR header", c07), ("08", "render settings identical except samples", c08),
    ("09", "calibration byte-identical and same gaze", c09), ("10", "camera matrices equal accepted and own", c10),
    ("11", "EXR headers classified (own)", c11), ("12", "seeds 2111 / 2112, independent", c12),
    ("13", "same scene: blend and object list", c13), ("14", "render-control comparison (own classification)", c14),
    ("15", "no rerender", c15), ("16", "Classroom preflight without render", c16),
    ("17", "preflight known answers and rehearsal", c17), ("18", "accepted matcher source and config", c18),
    ("19", "accepted matcher constants, no override", c19), ("20", "match guard: calibration + 4096 RGB only", c20),
    ("21", "independent matcher agrees on the 4096 subset", c21), ("22", "natural product truth-stripped", c22),
    ("23", "search geometry identical to AB1d (full core)", c23), ("24", "accepted spherical geometry only", c24),
    ("25", "observation freeze before matching", c25), ("26", "correspondence freeze before spherical", c26),
    ("27", "geometry freeze before evaluation", c27), ("28", "evaluation truth firewall and benchmark", c28),
    ("29", "4096 angular error (own)", c29), ("30", "4096 local pixel scale and px-equivalent (own)", c30),
    ("31", "4096 ORACLE-ON-CURVE, ranks and oracle ZNCC (own)", c31), ("32", "256 side equals accepted AB1d", c32),
    ("33", "paired error, fractions and transitions (own)", c33), ("34", "paired ZNCC, ranks, competing peak (own)", c34),
    ("35", "metric consequence (own)", c35), ("36", "observation diagnostics and PROXY labels (own)", c36),
    ("37", "figures: hashes, badges, deterministic regeneration", c37),
    ("38", "accepted examples reused; display transforms labelled", c38),
    ("39", "process order, once, one clean commit", c39), ("40", "manifest and declared changes", c40),
    ("41", "scope: no head motion, controller, denoising or other matcher", c41)]


def run_checks(x: Ctx) -> list[dict]:
    out = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(x)
        except Exception as exc:  # a check that cannot run fails
            ok, detail = False, {"error": f"{type(exc).__name__}: {exc}"}
        out.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
    return out


# ------------------------------------------------------------------ corruption suite (contract section 23)
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
    with open(x.run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def mutated_rows(x: Ctx, g: str, mutate) -> None:
    """Rewrite the checked rows of a mirrored record with the output of a mutated matcher (what a mutated run stores)."""
    import ab1d_match as M
    idx = subset_idx(x, g)
    z = npz(x.run / f"observations/{g}/acquisition/rgb-observation.npz")
    names = ("theta_phi", "make_cams", "search_line", "gray", "moments", "zncc", "decide", "chord")
    saved = {k: getattr(M, k) for k in names}
    try:
        params = mutate(M) or M.FROZEN
        ctx = M.Context(x.calib(g), M.gray(z["rgb_L"]), M.gray(z["rgb_R"]), params)
        rec = M.match(ctx, idx)
    finally:
        for k, v in saved.items():
            setattr(M, k, v)

    def put(d):
        for k, v in rec.items():
            a = np.array(d[k])
            a[idx] = v
            d[k] = a
    rewrite_npz(x.run / f"match/{g}/matcher-record.npz", put)


def copy_override(x: Ctx, kind: str, rel: str, src: Path, tmp: Path, fn) -> None:
    dst = tmp / kind / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    fn(dst)
    x.overrides.setdefault(kind, {})[rel] = str(dst)


def corruption_list(tmp: Path):
    G = GAZES[0]
    L = []

    def add(name, expect, fn):
        L.append((name, {f"{e:02d}" for e in expect}, fn))

    def acq_edit(fn, g=G):
        return lambda x: edit_json(x.run / f"observations/{g}/acquisition/acquisition.json", fn)

    def setting(k, v):
        return acq_edit(lambda d: d["settings"].__setitem__(k, v))

    def spp_all(d):
        d["spp"], d["settings"]["samples"], d["primary_camera_samples"] = 2048, 2048, 2 * RAW * RAW * 2048
    # ---- render
    add("render: spp 2048 in the record", (7, 14), acq_edit(spp_all))

    def exr_samples(x):
        """Rewrite the value of the EXR string attribute cycles.interior.samples (name, type, int32 size, value)."""
        p = x.run / f"observations/{G}/evaluation_only/raw_L.exr"
        b = p.read_bytes()
        i = b.find(b"cycles.interior.samples\x00")
        assert 0 < i < 65536
        j = b.index(b"\x00", i + 24) + 1                 # after the type name ("string")
        size = int.from_bytes(b[j:j + 4], "little")
        val = b[j + 4:j + 4 + size]
        new = b"2048" if val != b"2048" else b"8192"
        p.unlink()
        p.write_bytes(b[:j + 4] + new + b[j + 4 + size:] if size == 4 else b[:j] + len(new).to_bytes(4, "little")
                      + new + b[j + 4 + size:])
    add("render: EXR header records 2048 samples", (7, 11), exr_samples)
    add("render: denoising enabled", (8, 14), setting("denoising", True))
    add("render: adaptive sampling enabled", (8, 14), setting("adaptive_sampling", True))
    add("render: L seed changed", (12, 14), acq_edit(lambda d: d.__setitem__("render_seeds_lr", {"L": 2113, "R": 2112})))
    add("render: R seed changed", (12, 14), acq_edit(lambda d: d.__setitem__("render_seeds_lr", {"L": 2111, "R": 2113})))
    add("render: L and R seeds identical", (12, 14), acq_edit(lambda d: d.__setitem__("render_seeds_lr", {"L": 2111, "R": 2111})))
    add("render: pixel filter changed", (8, 14), setting("pixel_filter", "GAUSSIAN"))
    add("render: resolution changed", (8, 14), setting("resolution_wh", [1280, 1280]))

    def pose(d):
        d["camera_matrix_world_lr"]["R"][1][3] += 1e-3
    add("render: camera pose changed", (10, 14), acq_edit(pose))
    add("render: one gaze changed", (9, 14), acq_edit(lambda d: d.__setitem__("gaze_yaw_pitch_deg", [7.0, 6.75]), "gaze-2"))

    def calib_changed(x):
        p = x.run / f"observations/{G}/acquisition/calibration.json"
        d = jload(p)
        d["eyes"][1]["K"][0][0] += 1e-6
        p.unlink()
        p.write_text(json.dumps(d, indent=1, sort_keys=True, allow_nan=False) + "\n")
    add("render: calibration changed", (9, 25), calib_changed)
    # ---- source
    def obs256(x):
        def f(p):
            d = npz(p)
            d["rgb_L"] = (d["rgb_L"] * 1.01).astype(np.float32)
            p.unlink()
            np.savez_compressed(p, **d)
        copy_override(x, "a1c", f"observations/{G}/acquisition/rgb-observation.npz",
                      A1C / f"observations/{G}/acquisition/rgb-observation.npz", tmp / "ov256", f)
    add("source: accepted 256 observation altered", (3, 36), obs256)

    def src_altered(x):
        copy_override(x, "code", "tools/active_bootstrap/ab1d_match.py", REPO / "tools/active_bootstrap/ab1d_match.py",
                      tmp / "ovsrc", lambda p: p.write_text(p.read_text() + "\n# altered\n"))
    add("source: accepted AB1d matcher source altered", (2,), src_altered)

    def bench(x):
        def f(p):
            d = npz(p)
            d["uv_R"] = d["uv_R"] + 0.25
            p.unlink()
            np.savez_compressed(p, **d)
        copy_override(x, "a1c", f"oracle/{G}/oracle-correspondences.npz", A1C / f"oracle/{G}/oracle-correspondences.npz",
                      tmp / "ovbench", f)
    add("source: accepted benchmark altered", (3, 29), bench)
    # ---- matcher (a mutated matcher's output stored for the checked rows)

    def mut(fn):
        return lambda x: mutated_rows(x, G, fn)
    add("matcher: patch size 7 x 7", (21,), mut(lambda M: M.Params(patch_half=3)))
    add("matcher: texture threshold 4.0", (21,), mut(lambda M: M.Params(min_std=4.0)))
    add("matcher: spacing 0.5 px", (21, 23), mut(lambda M: M.Params(spacing=0.5)))

    def trunc(M):
        orig = M.chord

        def ch(q, t, w, h):
            lo, hi = orig(q, t, w, h)
            return lo, np.minimum(hi, 100)
        M.chord = ch
    add("matcher: hidden depth truncation (k <= 100)", (21, 23), mut(trunc))

    def sad(M):
        M.zncc = lambda a, b: -np.abs(a - b).mean(axis=-1) / 50.0
    add("matcher: ZNCC replaced (SAD)", (21,), mut(sad))
    add("matcher: refinement bound 0.3", (21,), mut(lambda M: M.Params(bound=0.3)))

    def consts(x):
        spec, params = x.live_constants()
        spec = dict(spec, MIN_LOCAL_STD_U8=1.0)
        x.overrides["live_constants"] = (spec, params)
    add("matcher: texture threshold constant changed", (19,), consts)
    add("matcher: hidden Params override in the run code", (19,),
        lambda x: x.overrides.setdefault("static_extra", {}).__setitem__("ab1d2_run.py", "\nM.FROZEN = M.Params(min_std=1.0)\n"))
    # ---- geometry
    add("geometry: candidate line shifted", (21, 23),
        lambda x: rewrite_npz(x.run / f"match/{G}/matcher-record.npz",
                              lambda d: d.__setitem__("q_inf", d["q_inf"] + np.array([0.5, 0.0]))))

    def flip(M):
        orig = M.search_line

        def sl(*a):
            r = orig(*a)
            r["t"] = -r["t"]
            return r
        M.search_line = sl
    add("geometry: baseline sign (search toward negative parallax)", (21, 23), mut(flip))
    # ---- freeze
    def rgb_after(x):
        p = x.run / f"observations/{G}/acquisition/rgb-observation.npz"
        rewrite_npz(p, lambda d: d.__setitem__("rgb_R", (d["rgb_R"] * 0.98).astype(np.float32)))
    add("freeze: 4096 RGB modified after the observation freeze", (25, 21), rgb_after)
    add("freeze: correspondence modified after its freeze", (26, 22),
        lambda x: rewrite_npz(x.run / f"match/{G}/natural-correspondences.npz",
                              lambda d: d.__setitem__("uv_R", d["uv_R"] + 0.1)))
    add("freeze: geometry modified after its freeze", (27, 24),
        lambda x: rewrite_npz(x.run / f"spherical/{G}/epipolar-result.npz",
                              lambda d: d.__setitem__("P_epi", d["P_epi"] + 1e-3)))
    # ---- evaluation
    def new_position(x):
        def ed(d):
            p = str(x.overrides.get("orig_run", x.run) / f"observations/{G}/evaluation_only/reference-observation.npz")
            ev = {"event": "open", "path": p, "kind": "data-read", "allowed": True}
            d["events"].insert(5, ev)
            d["data_reads"] = sorted(set(d["data_reads"]) | {p})
        edit_json(x.run / "evaluation/evaluation-opened-files.json", ed)
    add("evaluation: new 4096 Position used instead of the AB1c benchmark", (28,), new_position)
    add("evaluation: paired error corrupted", (33,),
        lambda x: rewrite_npz(x.run / f"evaluation/{G}/paired-result.npz",
                              lambda d: d["delta_E"].__setitem__(0, d["delta_E"][0] - 1.0)))
    add("evaluation: top-1 transition count corrupted", (34,), lambda x: edit_json(
        x.run / "evaluation/evaluation-summary.json",
        lambda d: d["per_gaze"][G]["paired"]["ranks"]["top1"]["not_to_in"].__setitem__(
            "count", d["per_gaze"][G]["paired"]["ranks"]["top1"]["not_to_in"]["count"] + 1)))
    add("evaluation: metric comparison corrupted", (35,), lambda x: edit_json(
        x.run / "evaluation/evaluation-summary.json",
        lambda d: d["per_gaze"][G]["paired"]["metric"].__setitem__(
            "fraction_improved", d["per_gaze"][G]["paired"]["metric"]["fraction_improved"] + 0.01)))
    add("evaluation: 256 reproduction failure hidden", (28,), lambda x: edit_json(
        x.run / "evaluation/evaluation-summary.json",
        lambda d: d["reproduction_256"][G].__setitem__("ok", False)))
    # ---- visual
    add("visual: a different example pixel chosen", (38,), lambda x: edit_json(
        x.vis / "visuals-manifest.json", lambda d: d["examples"][G][0].__setitem__("core_index", 12345)))

    def pixel(x):
        from PIL import Image
        p = x.vis / "overview.png"
        im = Image.open(p).convert("RGB")
        im.putpixel((10, 10), (255, 0, 0))
        p.unlink()
        im.save(p)
    add("visual: canonical figure pixel altered", (37,), pixel)
    add("visual: truth badge altered", (37,), lambda x: edit_json(
        x.vis / "visuals-manifest.json", lambda d: d["figures"]["overview.png"].__setitem__("badges", [ORA_B, DER_B])))
    add("visual: contrast stretch not labelled", (38,), lambda x: edit_json(
        x.vis / "visuals-manifest.json", lambda d: d["displays"]["stretch"][G].__setitem__("label_drawn", False)))
    # ---- process
    def twice(cmd):
        def f(x):
            e = dict(next(e for e in x.log if e["command"] == cmd))
            append_log(x, e)
        return f
    add("process: a gaze rendered twice (second render-4096)", (15, 39), twice("render-4096"))
    add("process: match run twice", (39,), twice("match"))
    add("process: denoising pass inserted", (14,), acq_edit(lambda d: d["exr_channels_lr"]["L"].append(
        "interior.Denoising Normal.X")))
    add("process: head motion inserted", (14, 41), acq_edit(lambda d: d["eye_pose"]["head_origin_w_m"].__setitem__(
        0, d["eye_pose"]["head_origin_w_m"][0] + 0.05)))

    def controller(x):
        e = dict(x.log[-1])
        e["command"] = "controller-step"
        append_log(x, e)
    add("process: controller action inserted", (39, 41), controller)
    add("firewall: Position read during matching", (20,), lambda x: edit_json(
        x.run / f"match/{G}/match-opened-files.json",
        lambda d: d["events"].insert(3, {"event": "open", "path": str(A1C / f"observations/{G}/evaluation_only/"
                                                                             f"reference-observation.npz"),
                                         "kind": "data-read", "allowed": False})))
    add("render-control claims ok with a failed gaze check", (14,), lambda x: edit_json(
        x.run / "observations/render-control.json", lambda d: d["gazes"][G]["checks"].__setitem__("record", False)))
    return L


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list, dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="ab1d2-corrupt-") as tmp:
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
              + ("" if c["ok"] else f" -- {json.dumps(c['detail'], default=str)[:500]}"), flush=True)
    npass = sum(c["ok"] for c in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1D2_CHECKS_PASS")
    out = {"schema": "AB1d2-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD")}
    if a.corruptions:
        caught, total, results, null = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, **null, "results": results}
        probative = ok and null["null_probe_passed"]
        print(f"{PREFIX} NULL PROBE {'PASS' if null['null_probe_passed'] else 'FAIL ' + str(null['null_probe_failed'])}")
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if probative else " (NOT PROBATIVE)"))
        if probative and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1D2_MUTATIONS_CAUGHT")
        ok = ok and probative and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
