"""Active Bootstrap-1a: fail-capable checks of the first natural stereo look.

    .venv/bin/python tools/active_bootstrap/check_ab1a.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md, sections 16-17 (checks 1-42; 42 is the
literal pass-set clause of section 6, split out of check 40).  The checker
keeps its own literal constants and recomputes independently of the generator:
- the frozen NB1c action (hashes, rank 1, the cell-centre convention);
- the calibration (baseline-projected axes, intrinsics, vergence, IPD, z_rect bounds) and L / B_perp;
- the rectification (its own cv2.stereoRectify call and maps) and the whole natural pipeline (its own SGBM factory,
  refinement copy, LR / texture / z_rect / ROI terms, reprojection);
- the truth firewall (guard records, ordered events, static audit of the matcher);
- the reference: the raw EXRs re-extracted with exr_lite and the accepted Classroom-Oracle-1 oracle re-run;
- the evaluation statistics and the figures (byte-identical regeneration).

``--corruptions`` plants defects in throwaway mirrors (JSON copied, other files linked; edited arrays rewritten) or
as in-process overrides.  They count only when the uncorrupted baseline passes.  ``--write-summary`` writes only
``check-summary.json``.
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
TOOLS = REPO / "tools"
PREFIX = "[ab1a-check]"

# ---- literal copies (contract sections 3-9); deliberately not imported from ab1a_spec
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE = "509c341ff60994ff0bf726b081be1f5c5c107b73"
NB1C_RUN = SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze"
NB1C_FREEZE_SHA = "87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37"
NB1C_CANDIDATES_SHA = "8041b954f7b63d97f060a41aaca5db1ec6e0c2295381523026e98d11f8a5b621"
NB1C_MANIFEST_SHA = "524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e"
NB1C_VIS_MANIFEST = (SHARED / "visuals/natural-bootstrap-1c-rgb-candidate-gaze/visuals-manifest.json",
                     "8f20e7873c4f1d90bf26ed674f91daddc9c4350361aa4abb7e7dab0d2bb62d60")
NB1A_FREEZE = (SHARED / "previews/natural-bootstrap-1a-range-connectivity/discovery/bootstrap-freeze.json",
               "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a")
NB1B_FREEZE = (SHARED / "previews/natural-bootstrap-1b-foveal-serviceability/selection/serviceability-freeze.json",
               "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a")
HEAD_POSE = (SHARED / "previews/controller-01-full/bootstrap/seeds.json",
             "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f")
CATALOG = (SHARED / "previews/controller-01-full/bootstrap/instance_catalog.json",
           "be26594254b03fbda7216ac1a942a5c800cf4bdd8f79751a2b8c22d6bfb4c7ae")
ROW, COL, RANK = 164, 513, 1
YAW, PITCH = 76.75, 7.75
CORE_FOV, CORE, RAW = 12.0, 256, 640
IPD, VERGENCE, Z_RECT = 0.063, 2.10, (0.75, 4.5)
SPP, DEVICE, SEEDS = 256, "OPTIX", {"L": 2111, "R": 2112}
PASSES = {"Combined", "Position", "Object Index"}
FORBIDDEN_PASSES = {"Depth", "Normal"}
# Contract section 23 (post-run clarification authorized by Luiz and Chat): the exact inherited Classroom
# lighting / material pass set recorded from the canonical acquisition; permitted only inside evaluation_only/raw_*.exr.
INHERITED_PASSES = {"Ambient Occlusion", "Diffuse Color", "Diffuse Direct", "Diffuse Indirect", "Emission",
                    "Glossy Color", "Glossy Direct", "Glossy Indirect", "Transmission Color", "Transmission Direct",
                    "Transmission Indirect"}
REQUIRED_CHANNELS = {"Combined": {"R", "G", "B", "A"}, "Position": {"X", "Y", "Z"}, "Object Index": {"X"}}
BLOCK, LR_TOL, UNIQ, MIN_STD = 5, 1.0, 10, 0.5
EYE_TOL, CAL_TOL, CAM_TOL = 1e-6, 1e-9, 0.5 + 1e-3
QUANT = {"median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
FRACTIONS = (0.010, 0.025, 0.050)
MIN_INST = 50
PINS = {
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/classroom_oracle1_matcher.py": "d213c2c7da68a2969b54a095fc7d953d7d16b21f5690cf2fd152197265884afa",
    "tools/classroom_oracle1_public.py": "7b85e59a6e397ed69d3eaec8a6b3790639a6c6ffce596fd0d8d1664c738452bb",
    "tools/fsg6f_public.py": "c79f58c9b51f33d4463f2bcfcaa339d79cf20a962b44de9c6cc721cf157cd2fa",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
}
AB1A_FILES = {f"tools/active_bootstrap/{n}" for n in ("ab1a_spec.py", "ab1a_render.py", "ab1a_stereo.py", "ab1a_run.py",
                                                      "ab1a_visuals.py", "check_ab1a.py")} | {
    "docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md",
    "docs/active-bootstrap/ab1a-first-natural-stereo-look-report.md"}
DECLARED = AB1A_FILES | {"tools/repository/check_repository_layout.py", "CLAUDE.md", "docs/chat-handoff.md"}
COMMANDS = {"synthetic", "rehearse", "prelook", "preflight", "acquire", "measure", "freeze", "evaluate", "visualize"}
RESULT_KEYS = {"R1", "R2", "P1", "P2", "Q_full", "Q_core", "crop_xywh", "roi_L", "roi_R", "min_disparity",
               "num_disparities", "valid_disparity_roi", "disparity_px", "disparity_sgbm_px", "valid", "xyz_h",
               "range_left_m", "z_rect_m", "lr_error_px", "left_gray_std", "rgb_left", "rgb_right", "raw_support_L",
               "term_sgbm_left", "term_right_valid", "term_support_left", "term_inside_raster", "term_lr",
               "term_texture", "term_finite", "term_z_range", "term_roi"}
TERMS = ["term_sgbm_left", "term_right_valid", "term_support_left", "term_inside_raster", "term_lr", "term_texture",
         "term_finite", "term_z_range", "term_roi"]
FORBIDDEN_TOKENS = ("instance", "position", "mask_interior", "object", "evaluation_only", "reference", "oracle")
FORBIDDEN_IMPORTS = ("controller", "fov3d", "fsg6f_frontier", "fsg3_surface_map", "multiobject2c", "classroom_oracle1_eval")
FROZEN = ["source/nb1c-action-manifest.json", "prelook/planned-calibration.json", "prelook/prelook-geometry.json",
          "acquisition/calibration.json", "acquisition/rgb-observation.npz", "acquisition/acquisition.json",
          "measurement/stereo-result.npz", "measurement/stereo-summary.json", "measurement/measurement-opened-files.json"]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def unit(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def gaze(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])


def leaf_diff(a, b) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        return max([leaf_diff(a[k], b[k]) for k in a] or [0.0]) if set(a) == set(b) else math.inf
    if isinstance(a, list) and isinstance(b, list):
        return max([leaf_diff(x, y) for x, y in zip(a, b)] or [0.0]) if len(a) == len(b) else math.inf
    if isinstance(a, bool) or isinstance(b, bool):
        return 0.0 if a == b else math.inf
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
            return 0.0
        return abs(float(a) - float(b))
    return 0.0 if a == b else math.inf


# ------------------------------------------------------------------ the checker's own natural pipeline
def indep_rectification(c: dict) -> dict:
    w, h = c["image_size_wh"]
    kl, kr = (np.asarray(e["K"], np.float64) for e in c["eyes"])
    rl, rr = (np.asarray(e["R_hc"], np.float64) for e in c["eyes"])
    cl, cr = (np.asarray(e["centre_h_m"], np.float64) for e in c["eyes"])
    r, t = rr.T @ rl, rr.T @ (cl - cr)
    r1, r2, p1, p2, q, roi1, roi2 = cv2.stereoRectify(kl, np.zeros(5), kr, np.zeros(5), (w, h), r, t,
                                                      flags=cv2.CALIB_ZERO_DISPARITY, alpha=-1, newImageSize=(w, h))
    maps = {}
    for side, k, rot, p in (("L", kl, r1, p1), ("R", kr, r2, p2)):
        maps[side] = cv2.initUndistortRectifyMap(k, np.zeros(5), rot, p[:, :3], (w, h), cv2.CV_32FC1)
    core = c["core_size"]
    x, y = (w - core) // 2, (h - core) // 2
    a = np.eye(4)
    a[0, 3], a[1, 3] = x, y
    nd = int(math.ceil((int(math.ceil(abs(p2[0, 3]) / c["depth_search_z_rect_m"][0])) + 4) / 16) * 16)
    return {"R1": r1, "R2": r2, "P1": p1, "P2": p2, "Q_full": q, "Q_core": q @ a, "roi_L": np.array(roi1),
            "roi_R": np.array(roi2), "crop": (x, y, core, core), "nd": nd, "maps": maps}


def _u8(rgb):
    a = np.clip(np.asarray(rgb, float), 0., 1.)
    a = np.where(a <= .0031308, 12.92 * a, 1.055 * np.power(a, 1 / 2.4) - .055)
    return np.rint(255 * a).astype(np.uint8)


def _sgbm(min_d, n, block=BLOCK, uniq=UNIQ):
    return cv2.StereoSGBM_create(minDisparity=min_d, numDisparities=n, blockSize=block, P1=8 * block ** 2,
                                 P2=32 * block ** 2, disp12MaxDiff=-1, preFilterCap=31, uniquenessRatio=uniq,
                                 speckleWindowSize=0, speckleRange=1, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)


def _refine(left, right, initial, supported):
    lum = np.array([.2126, .7152, .0722], np.float32)
    lft, rgt = np.asarray(left, np.float32) @ lum, np.asarray(right, np.float32) @ lum
    grad = cv2.Sobel(rgt, cv2.CV_32F, 1, 0, ksize=3, scale=1 / 8)
    h, w = lft.shape
    vv, uu = np.mgrid[:h, :w].astype(np.float32)
    d = initial.copy()

    def mean(a):
        return cv2.boxFilter(a, -1, (5, 5), normalize=True, borderType=cv2.BORDER_REFLECT)
    for _ in range(3):
        x = uu - d
        rw = cv2.remap(rgt, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        gw = cv2.remap(grad, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        res = rw - lft
        gm, rm = mean(gw), mean(res)
        num = mean(gw * res) - gm * rm
        den = np.maximum(mean(gw * gw) - gm * gm, 0.)
        step = np.divide(num, den + 1e-9, out=np.zeros_like(d), where=den > 1e-8)
        d = np.where(supported, np.clip(d + np.clip(step, -.5, .5), initial - .75, initial + .75), initial).astype(np.float32)
    return d


def indep_pipeline(c: dict, rgb: dict) -> dict:
    w, h = c["image_size_wh"]
    r = indep_rectification(c)
    col, gray, sup = {}, {}, {}
    for side in ("L", "R"):
        mx, my = r["maps"][side]
        col[side] = cv2.remap(np.asarray(rgb["rgb_" + side], np.float32), mx, my, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        gray[side] = cv2.cvtColor(_u8(col[side]), cv2.COLOR_RGB2GRAY)
        s = (mx >= 1) & (mx < w - 2) & (my >= 1) & (my < h - 2)
        sup[side] = cv2.erode(s.astype(np.uint8), np.ones((BLOCK, BLOCK), np.uint8)).astype(bool)
    nd = r["nd"]
    dl_raw = _sgbm(0, nd).compute(gray["L"], gray["R"])
    mr = -(nd - 1)
    dr_raw = _sgbm(mr, nd).compute(gray["R"], gray["L"])
    dl, dr = dl_raw.astype(np.float32) / 16., dr_raw.astype(np.float32) / 16.
    vl, vr = dl_raw > -16, dr_raw > (mr - 1) * 16
    d0 = dl.copy()
    dl = _refine(col["L"], col["R"], dl, vl & sup["L"])
    dr = _refine(col["R"], col["L"], dr, vr & sup["R"])
    vv, uu = np.mgrid[:h, :w].astype(np.float64)
    ur = uu - dl
    xr, v32 = ur.astype(np.float32), vv.astype(np.float32)
    dr_at = cv2.remap(dr, xr, v32, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    vr_at = cv2.remap((vr & sup["R"]).astype(np.float32), xr, v32, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                      borderValue=0) > .999
    lr = np.abs(dl + dr_at)
    m = gray["L"].astype(np.float32)
    std = np.sqrt(np.maximum(cv2.boxFilter(m * m, -1, (5, 5)) - cv2.boxFilter(m, -1, (5, 5)) ** 2, 0.))
    a = np.stack([uu, vv, dl, np.ones_like(uu)], -1) @ np.asarray(r["Q_full"]).T
    with np.errstate(divide="ignore", invalid="ignore"):
        rect = a[..., :3] / a[..., 3:4]
    z = rect[..., 2]
    lo, hi = c["depth_search_z_rect_m"]
    gx, gy, gw, gh = cv2.getValidDisparityROI(tuple(r["roi_L"]), tuple(r["roi_R"]), 0, nd, BLOCK)
    roi = np.zeros((h, w), bool)
    roi[gy:gy + gh, gx:gx + gw] = True
    with np.errstate(invalid="ignore"):
        terms = {"term_sgbm_left": vl, "term_right_valid": vr_at, "term_support_left": sup["L"],
                 "term_inside_raster": (ur >= 0) & (ur < w - 1), "term_lr": lr <= LR_TOL, "term_texture": std >= MIN_STD,
                 "term_finite": np.isfinite(rect).all(-1), "term_z_range": (z >= lo) & (z <= hi), "term_roi": roi}
    x, y, cw, ch = r["crop"]
    sl = np.s_[y:y + ch, x:x + cw]
    valid = np.logical_and.reduce([terms[t] for t in TERMS])
    rl = np.asarray(c["eyes"][0]["R_hc"], np.float64)
    cl = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    head = (np.where(np.isfinite(rect), rect, np.nan) @ r["R1"]) @ rl.T + cl
    return {"r": r, "terms": {k: t[sl] for k, t in terms.items()}, "valid": valid[sl], "disparity_px": dl[sl],
            "disparity_sgbm_px": d0[sl], "lr_error_px": lr[sl], "left_gray_std": std[sl], "rgb_left": col["L"][sl],
            "rgb_right": col["R"][sl], "support_L": sup["L"][sl], "head": head[sl], "z": z[sl]}


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = run, vis
        self.overrides: dict = {}

    def j(self, rel):
        return json.loads((self.run / rel).read_text())

    def npz(self, rel):
        with np.load(self.run / rel, allow_pickle=False) as z:
            return {k: np.asarray(z[k]) for k in z.files}

    @cached_property
    def c(self):
        return self.j("acquisition/calibration.json")

    @cached_property
    def acq(self):
        return self.j("acquisition/acquisition.json")

    @cached_property
    def pre(self):
        return self.j("prelook/prelook-geometry.json")

    @cached_property
    def action(self):
        return self.j("source/nb1c-action-manifest.json")

    @cached_property
    def rgb(self):
        return self.npz("acquisition/rgb-observation.npz")

    @cached_property
    def nat(self):
        return self.npz("measurement/stereo-result.npz")

    @cached_property
    def summ(self):
        return self.j("measurement/stereo-summary.json")

    @cached_property
    def opened(self):
        return self.j("measurement/measurement-opened-files.json")

    @cached_property
    def freeze(self):
        return self.j("measurement/measurement-freeze.json")

    @cached_property
    def ev(self):
        return self.j("evaluation/evaluation-summary.json")

    @cached_property
    def evopened(self):
        return self.j("evaluation/evaluation-opened-files.json")

    @cached_property
    def orc(self):
        return self.npz("evaluation/oracle-reference.npz")

    @cached_property
    def ref(self):
        return self.npz("evaluation_only/reference-observation.npz")

    @cached_property
    def log(self):
        return [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x.strip()]

    @cached_property
    def indep(self):
        return indep_pipeline(self.c, self.rgb)

    @cached_property
    def exr(self):
        sys.path.insert(0, str(TOOLS))
        from exr_lite import read_uncompressed_exr
        out = {}
        for side in ("L", "R"):
            ch = read_uncompressed_exr(str(self.run / f"evaluation_only/raw_{side}.exr"))
            pick = lambda suf: np.asarray(ch[[k for k in ch if k.endswith(suf)][0]])  # noqa: E731
            out[side] = {"channels": sorted(ch), "rgb": np.stack([pick(f"Combined.{x}") for x in "RGB"], -1).astype(np.float32),
                         "pos": np.stack([pick(f"Position.{x}") for x in "XYZ"], -1).astype(np.float32),
                         "ids": np.maximum(np.rint(pick("Object Index.X")), 0).astype(np.int32)}
        return out

    @cached_property
    def changed_files(self):
        if "changed_files" in self.overrides:
            return self.overrides["changed_files"]
        ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
        return sorted(ch)

    def ov(self, name, default):
        return self.overrides.get(name, default)


# ------------------------------------------------------------------ checks
def c01(x):
    fz = NB1C_RUN / "selection/rgb-gaze-freeze.json"
    rec = json.loads(fz.read_text())
    bad = [n for n, h in rec["files"].items() if sha256(fz.parent / n) != h]
    src = x.action["nb1c_freeze"]
    return sha256(fz) == NB1C_FREEZE_SHA and not bad and src["sha256"] == NB1C_FREEZE_SHA, f"bad {bad}; recorded {src}"


def c02(x):
    cg = NB1C_RUN / "selection/candidate-gazes.json"
    man = json.loads((NB1C_RUN / "manifest.json").read_text())
    fz = json.loads((NB1C_RUN / "selection/rgb-gaze-freeze.json").read_text())
    ok = (sha256(cg) == NB1C_CANDIDATES_SHA and sha256(NB1C_RUN / "manifest.json") == NB1C_MANIFEST_SHA
          and man["files"]["selection/candidate-gazes.json"] == NB1C_CANDIDATES_SHA
          and fz["files"]["candidate-gazes.json"] == NB1C_CANDIDATES_SHA
          and x.action["nb1c_candidate_gazes"]["sha256"] == NB1C_CANDIDATES_SHA)
    return ok, x.action["nb1c_candidate_gazes"]


def c03(x):
    g = x.action["gaze"]
    first = json.loads((NB1C_RUN / "selection/candidate-gazes.json").read_text())["gazes"][0]
    return (g["rank"], g["row"], g["col"]) == (RANK, ROW, COL) and first["row"] == ROW and first["col"] == COL, g


def c04(x):
    vals = {"action": (x.action["gaze"]["yaw_deg"], x.action["gaze"]["pitch_deg"]),
            "planned": tuple(x.j("prelook/planned-calibration.json")["gaze_yaw_pitch_deg"]),
            "calibration": tuple(x.c["gaze_yaw_pitch_deg"]), "acquisition": tuple(x.acq["gaze_yaw_pitch_deg"]),
            "prelook": tuple(x.pre["gaze_yaw_pitch_deg"])}
    return all(v == (YAW, PITCH) for v in vals.values()), vals


def c05(x):
    first = json.loads((NB1C_RUN / "selection/candidate-gazes.json").read_text())["gazes"][0]
    centre = (-180.0 + 0.5 * (COL + 0.5), 90.0 - 0.5 * (ROW + 0.5))
    ok = (first["yaw_deg"], first["pitch_deg"]) == centre == (YAW, PITCH) == tuple(x.c["gaze_yaw_pitch_deg"])
    d = gaze(*x.c["gaze_yaw_pitch_deg"])
    ok &= bool(np.allclose(np.asarray(x.pre["gaze_direction_h"]), d, atol=1e-15))
    return ok, {"frozen": (first["yaw_deg"], first["pitch_deg"]), "cell_centre": centre, "executed": x.c["gaze_yaw_pitch_deg"]}


def _entries(x, cmd):
    return [e for e in x.log if e.get("command") == cmd]


def c06(x):
    acq = _entries(x, "acquire")
    order = [e["command"] for e in x.log]
    ok = len(acq) == 1 and acq[0]["status"] == "ok" and not acq[0]["code"]["dirty"] and acq[0]["code"]["pushed"]
    if acq:
        i = order.index("acquire")
        ok &= all(c not in order[:i] for c in ("measure", "freeze", "evaluate"))
    files = {"acquisition": sorted(p.name for p in (x.run / "acquisition").iterdir()),
             "evaluation_only": sorted(p.name for p in (x.run / "evaluation_only").iterdir())}
    ok &= files == {"acquisition": ["acquisition.json", "calibration.json", "rgb-observation.npz"],
                    "evaluation_only": ["instance-catalog.json", "raw_L.exr", "raw_R.exr", "reference-observation.npz"]}
    ok &= x.acq.get("canonical") is True and x.acq.get("complete") is True
    return bool(ok), {"acquire_entries": len(acq), "files": files}


def _argv_text(x) -> str:
    """Every logged argv, with the declared accepted data paths removed (the head-pose source lives under
    previews/controller-01-full/: a data file, not a controller command)."""
    text = " ".join(" ".join(map(str, e.get("argv", []))) + " " + " ".join(map(str, e.get("blender", {}).get("argv", [])))
                    for e in x.log)
    for p in (HEAD_POSE[0], CATALOG[0]):
        text = text.replace(str(p), "<accepted-data>")
    return text.lower()


def c07(x):
    cmds = {e.get("command") for e in x.log}
    argv = _argv_text(x)
    bad_imports = static_imports()
    ok = cmds <= COMMANDS and "controller" not in argv and not [i for i in bad_imports if "controller" in i]
    return ok, {"commands": sorted(map(str, cmds)), "bad_imports": bad_imports}


def c08(x):
    gazes = {tuple(x.c["gaze_yaw_pitch_deg"]), tuple(x.acq["gaze_yaw_pitch_deg"]), tuple(x.pre["gaze_yaw_pitch_deg"])}
    pf = x.j("preflight/preflight.json")
    blender_modes = [e["blender"]["mode"] for e in x.log if "blender" in e]
    yaw_args = [a for e in x.log for a in map(str, e.get("argv", [])) if a in ("--yaw", "--pitch", "--gaze")]
    ok = (gazes == {(YAW, PITCH)} and blender_modes.count("canonical") == 1 and not yaw_args
          and pf.get("rendered") is False and len(x.acq["render_seconds_lr"]) == 2)
    return ok, {"gazes": sorted(gazes), "blender_modes": blender_modes, "yaw_args": yaw_args}


def c09(x):
    got = {p: sha256(REPO / p) for p in PINS}
    bad = {p: h for p, h in got.items() if h != PINS[p]}
    return not bad, bad


def c10(x):
    f = CORE / (2 * math.tan(math.radians(CORE_FOV) / 2))
    raw = math.degrees(2 * math.atan(RAW / (2 * f)))
    ok = (x.c["nominal_core_fov_deg"] == CORE_FOV and abs(x.c["raw_fov_deg"] - raw) <= 1e-12
          and all(abs(e["K"][0][0] - f) <= 1e-9 for e in x.c["eyes"]))
    return ok, {"nominal": x.c["nominal_core_fov_deg"], "raw_fov_deg": x.c["raw_fov_deg"], "focal_px": f}


def c11(x):
    return (x.c["profile"] == "full" and x.c["core_size"] == CORE and x.c["image_size_wh"] == [RAW, RAW]
            and x.nat["valid"].shape == (CORE, CORE)), (x.c["profile"], x.c["core_size"], x.c["image_size_wh"])


def c12(x):
    cen = [e["centre_h_m"] for e in x.c["eyes"]]
    return x.c["ipd_m"] == IPD and cen == [[-IPD / 2, 0.0, 0.0], [IPD / 2, 0.0, 0.0]] and x.acq["ipd_m"] == IPD, cen


def c13(x):
    return x.c["prescribed_vergence_distance_m"] == VERGENCE and x.acq["vergence_distance_m"] == VERGENCE, \
        x.c["prescribed_vergence_distance_m"]


def c14(x):
    return x.c.get("tangent_frame") == "baseline_projected" and x.acq["tangent_frame"] == "baseline_projected", \
        x.c.get("tangent_frame")


def c15(x):
    return tuple(x.c["depth_search_z_rect_m"]) == Z_RECT, x.c["depth_search_z_rect_m"]


def c16(x):
    d = gaze(*x.c["gaze_yaw_pitch_deg"])
    f = CORE / (2 * math.tan(math.radians(CORE_FOV) / 2))
    k = np.array([[f, 0, (RAW - 1) / 2], [0, f, (RAW - 1) / 2], [0, 0, 1]])
    worst = 0.0
    for e in x.c["eyes"]:
        z = unit(d * VERGENCE - np.asarray(e["centre_h_m"]))
        xx = unit(np.array([1.0, 0, 0]) - (z[0]) * z)
        rot = np.column_stack((xx, np.cross(z, xx), z))
        worst = max(worst, float(np.abs(rot - np.asarray(e["R_hc"])).max()), float(np.abs(k - np.asarray(e["K"])).max()))
    return worst <= 1e-12, {"max_abs_diff": worst}


def c17(x):
    d = gaze(YAW, PITCH)
    lev = math.sqrt(1 - d[0] ** 2)
    ok = abs(x.pre["L"] - lev) <= 1e-12 and abs(x.pre["B_perp_m"] - IPD * lev) <= 1e-12
    r = x.indep["r"]
    for side in ("L", "R"):
        e = x.pre["eyes"][side]
        rot = r["R1"] if side == "L" else r["R2"]
        ang = math.degrees(math.acos(float(np.clip((np.trace(rot) - 1) / 2, -1, 1))))
        mx, my = r["maps"][side]
        cx, cy, cw, ch = r["crop"]
        mx, my = mx[cy:cy + ch, cx:cx + cw], my[cy:cy + ch, cx:cx + cw]
        ok &= abs(e["rectification_rotation_deg"] - ang) <= 1e-9
        ok &= abs(e["raw_source_of_rectified_core_px"]["x"][0] - float(mx.min())) <= 1e-4
        ok &= abs(e["raw_source_of_rectified_core_px"]["x"][1] - float(mx.max())) <= 1e-4
    order = [e["command"] for e in x.log if e.get("status") == "ok"]
    ok &= "prelook" in order and "acquire" in order and order.index("prelook") < order.index("acquire")
    ok &= sha256(x.run / "prelook/planned-calibration.json") == x.pre["planned_calibration_sha256"]
    ok &= leaf_diff(x.j("prelook/planned-calibration.json"), x.c) <= CAL_TOL
    return bool(ok), {"L": x.pre["L"], "L_indep": lev, "B_perp_m": x.pre["B_perp_m"]}


def c18(x):
    keys = sorted(x.rgb)
    ok = keys == ["rgb_L", "rgb_R"] and all(a.dtype == np.float32 and a.shape == (RAW, RAW, 3) and np.isfinite(a).all()
                                           for a in x.rgb.values())
    return ok, keys


def c19(x):
    """Exactly the two declared inputs, in one acquisition/ directory; writes only in its sibling measurement/
    (independent of where the run tree lives, so the check also holds on a relocated copy)."""
    reads = sorted(set(x.opened["data_reads"]))
    parents = {str(Path(p).parent) for p in reads}
    ok = (sorted(Path(p).name for p in reads) == ["calibration.json", "rgb-observation.npz"] and len(parents) == 1
          and Path(next(iter(parents))).name == "acquisition")
    if ok:
        meas = str(Path(next(iter(parents))).parent / "measurement") + os.sep
        ok = all(p.startswith(meas) for p in x.opened["writes"])
    return bool(ok), {"data_reads": reads}


def c20(x):
    hits = [e["path"] for e in x.opened["events"] if isinstance(e, dict) and "evaluation_only" in str(e.get("path", ""))]
    return not hits and x.opened["violations"] == [] and x.opened.get("truth_firewall_violations") == 0, hits


def c21(x):
    keys = set(x.nat)
    skeys = json.dumps(sorted(_all_keys(x.summ))).lower()
    bad = [t for t in ("instance", "object_id", "position", "normal", "truth_", "ground_truth") if t in skeys]
    return keys == RESULT_KEYS and not bad, {"extra": sorted(keys - RESULT_KEYS), "missing": sorted(RESULT_KEYS - keys),
                                             "summary_tokens": bad}


def _all_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _all_keys(v)


def c22(x):
    r = x.indep["r"]
    worst = max(float(np.abs(np.asarray(x.nat[k], float) - np.asarray(r[k], float)).max())
                for k in ("R1", "R2", "P1", "P2", "Q_full", "Q_core"))
    ok = (worst <= 1e-9 and list(x.nat["crop_xywh"]) == list(r["crop"]) and int(x.nat["num_disparities"]) == r["nd"]
          and int(x.nat["min_disparity"]) == 0 and list(x.nat["roi_L"]) == list(r["roi_L"]))
    return ok, {"max_abs_diff": worst, "nd": int(x.nat["num_disparities"])}


def c23(x):
    m = x.summ["matcher"]
    sys.path.insert(0, str(TOOLS))
    import fsg_stereo as FS
    ok = (m["block_size"] == BLOCK and m["lr_tolerance_px"] == LR_TOL and m["uniqueness_ratio"] == UNIQ
          and m["minimum_local_std_u8"] == MIN_STD and m["block_size_used"] == BLOCK and m["uniqueness_ratio_used"] == UNIQ
          and m["variant"] == {} and m["refinement"]["iterations"] == 3 and m["refinement"]["max_step_px"] == 0.5
          and m["refinement"]["max_total_px"] == 0.75 and m["sgbm"]["mode"] == "SGBM_3WAY"
          and m["sgbm"]["preFilterCap"] == 31 and m["sgbm"]["disp12MaxDiff"] == -1 and m["identity_guard"] is None
          and (FS.BLOCK_SIZE, FS.LR_TOLERANCE_PX, FS.UNIQUENESS_RATIO, FS.MIN_LOCAL_STD_U8) == (BLOCK, LR_TOL, UNIQ, MIN_STD)
          and x.freeze["matcher_config_sha256"] == x.summ["matcher_config_sha256"])
    return bool(ok), {k: m.get(k) for k in ("block_size_used", "uniqueness_ratio_used", "variant")}


def static_audit() -> dict:
    src = (HERE / "ab1a_stereo.py").read_text()
    tree = ast.parse(src)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)}
    tokens, calls = set(), []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            tokens.add(n.id)
        elif isinstance(n, ast.Attribute):
            tokens.add(n.attr)
            if n.attr == "compute" and isinstance(n.value, ast.Name) and n.value.id in ("FS", "fsg_stereo"):
                calls.append("fsg_stereo.compute")
        elif isinstance(n, ast.arg):
            tokens.add(n.arg)
        elif isinstance(n, ast.keyword) and n.arg:
            tokens.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            tokens.add(n.name)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            tokens.add(n.value)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            tokens.update(a.name for a in n.names)
            if isinstance(n, ast.ImportFrom) and n.module:
                tokens.add(n.module)
    bad = sorted(t for t in tokens if any(f in t.lower() for f in FORBIDDEN_TOKENS))
    return {"forbidden_tokens": bad, "truth_assisted_calls": calls}


def static_imports() -> list[str]:
    bad = []
    for f in sorted(HERE.glob("ab1a_*.py")):
        for n in ast.walk(ast.parse(f.read_text())):
            names = []
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                names = [n.module]
            bad += [f"{f.name}:{m}" for m in names if any(t in m for t in FORBIDDEN_IMPORTS)]
    return bad


def c24(x):
    a = x.ov("static_audit", None) or static_audit()
    return not a["forbidden_tokens"] and not a["truth_assisted_calls"], a


def c25(x):
    sup = x.indep["support_L"]
    return (np.array_equal(x.nat["term_support_left"], sup) and np.array_equal(x.nat["raw_support_L"], sup)), \
        {"saved": int(x.nat["term_support_left"].sum()), "independent": int(sup.sum())}


def _term_eq(x, name):
    a, b = x.nat[name].astype(bool), x.indep["terms"][name]
    return bool(np.array_equal(a, b)), {"saved": int(a.sum()), "independent": int(b.sum()), "differ": int((a ^ b).sum())}


def c26(x):
    ok, det = _term_eq(x, "term_lr")
    ok &= bool(np.array_equal(x.nat["lr_error_px"], x.indep["lr_error_px"]))
    return ok, det


def c27(x):
    ok, det = _term_eq(x, "term_texture")
    ok &= bool(np.array_equal(x.nat["left_gray_std"], x.indep["left_gray_std"]))
    return ok, det


def c28(x):
    ok1, d1 = _term_eq(x, "term_z_range")
    ok2, d2 = _term_eq(x, "term_finite")
    return ok1 and ok2, {"z_range": d1, "finite": d2}


def c29(x):
    v = x.nat["valid"].astype(bool)
    anded = np.logical_and.reduce([x.nat[t].astype(bool) for t in TERMS])
    others = all(np.array_equal(x.nat[t].astype(bool), x.indep["terms"][t]) for t in TERMS)
    ok = np.array_equal(v, anded) and np.array_equal(v, x.indep["valid"]) and others
    return bool(ok), {"valid": int(v.sum()), "and_of_terms": int(anded.sum()), "independent": int(x.indep["valid"].sum()),
                      "terms_equal": others}


def c30(x):
    v = x.nat["valid"].astype(bool)
    ok = (np.array_equal(x.nat["disparity_px"], x.indep["disparity_px"])
          and np.array_equal(x.nat["disparity_sgbm_px"], x.indep["disparity_sgbm_px"]))
    xyz = x.nat["xyz_h"].astype(np.float64)
    head = x.indep["head"]
    cl = np.asarray(x.c["eyes"][0]["centre_h_m"], float)
    fin = np.isfinite(xyz).all(-1)
    ok &= bool(np.array_equal(fin, v)) and bool(np.array_equal(np.isfinite(x.nat["range_left_m"]), v))
    worst = 0.0
    if v.any():
        worst = max(float(np.abs(xyz[v] - head[v]).max()),
                    float(np.abs(x.nat["range_left_m"][v] - np.linalg.norm(head[v] - cl, axis=-1)).max()),
                    float(np.abs(x.nat["z_rect_m"][v] - x.indep["z"][v]).max()))
    ok &= worst <= 1e-4
    return bool(ok), {"max_abs_diff": worst, "finite_equals_valid": bool(np.array_equal(fin, v))}


def c31(x):
    ev = x.evopened["ordered_data_events"]
    first_truth = next((i for i, p in enumerate(ev) if "evaluation_only" in str(p)), None)
    fz = ev.index("measurement_freeze_verified") if "measurement_freeze_verified" in ev else None
    rb = ev.index("reference_access_begins") if "reference_access_begins" in ev else None
    order = [e["command"] for e in x.log]
    ok = (first_truth is not None and fz is not None and rb is not None and fz < rb < first_truth
          and x.evopened["violations"] == [] and order.index("freeze") < order.index("evaluate")
          and not any("evaluation_only" in str(e.get("path", "")) for e in x.opened["events"] if isinstance(e, dict)))
    return bool(ok), {"freeze_mark": fz, "reference_mark": rb, "first_truth_read": first_truth}


def c32(x):
    bad = [n for n, h in x.freeze["files"].items() if sha256(x.run / n) != h]
    ok = not bad and set(x.freeze["files"]) == set(FROZEN) and x.ev["frozen_measurement_sha256"] == x.freeze["files"]
    ok &= x.freeze["truth_firewall_violations"] == 0
    return ok, bad


def c33(x):
    e = x.exr
    ok = all(np.array_equal(e[s]["ids"], x.ref[f"instance_{s}"]) and np.array_equal(e[s]["pos"], x.ref[f"position_w_{s}"])
             for s in ("L", "R"))
    sys.path.insert(0, str(TOOLS))
    import classroom_oracle1_matcher as OM
    rec, _meta, _st = OM.compute(x.c, {**x.rgb, **x.ref})
    for k in ("valid", "instance_id", "raw_support_L", "raw_support_R", "instance_id_R", "right_reprojection_instance"):
        ok &= bool(np.array_equal(np.asarray(rec[k]), x.orc[k]))
    ok &= bool(np.array_equal(np.asarray(rec["xyz_h"]), x.orc["xyz_h"], equal_nan=True))
    return bool(ok), {"reference_valid": int(np.asarray(rec["valid"]).sum()), "saved": int(x.orc["valid"].sum())}


def _q(a, qs=None):
    a = np.asarray(a, np.float64).ravel()
    a = a[np.isfinite(a)]
    if not a.size:
        return None
    return {k: float(np.quantile(a, q)) for k, q in (qs or QUANT).items()} | {"count": int(a.size)}


def _err(a, b, m, cl):
    a, b = a[m].astype(np.float64), b[m].astype(np.float64)
    e3 = np.linalg.norm(a - b, axis=-1)
    sg = np.linalg.norm(a - cl, axis=-1) - np.linalg.norm(b - cl, axis=-1)
    return {"pixels": int(m.sum()), "error_3d_m": _q(e3), "radial_abs_m": _q(np.abs(sg)),
            "radial_signed_m": _q(sg, {"min": 0.0, **QUANT}),
            "fraction_3d_within_m": ({f"{t:.3f}": float((e3 <= t).mean()) for t in FRACTIONS} if e3.size else None)}


def c34(x):
    N, R = x.nat["valid"].astype(bool), x.orc["valid"].astype(bool)
    cl = np.asarray(x.c["eyes"][0]["centre_h_m"], float)
    xyz_n, xyz_r = x.nat["xyz_h"].astype(np.float64), x.orc["xyz_h"].astype(np.float64)
    ids, geom = x.orc["instance_id"], x.orc["left_geometry"].astype(bool)
    k = x.ev["counts"]
    want = {"core_pixels": int(N.size), "natural_valid": int(N.sum()), "reference_valid": int(R.sum()),
            "overlap": int((N & R).sum()), "natural_only": int((N & ~R).sum()), "reference_only": int((R & ~N).sum())}
    d = {"counts": k == want,
         "overlap": leaf_diff(x.ev["overlap_errors"], _err(xyz_n, xyz_r, N & R, cl)) <= 1e-9,
         "first_hit": leaf_diff({kk: v for kk, v in x.ev["natural_vs_left_first_hit"].items() if kk != "definition"},
                                _err(xyz_n, x.orc["left_position_h"], N & geom, cl)) <= 1e-6}
    comp = x.ev["composition_of_natural_valid"]
    d["composition"] = (comp["catalog"] == int((N & (ids > 0)).sum()) and comp["no_geometry"] == int((N & ~geom).sum())
                        and comp["O_0_noncatalog_geometry"] == int((N & (ids == 0) & geom).sum())
                        and comp["distinct_catalog_instances"] == len(set(ids[N & (ids > 0)].tolist())))
    d["reasons_total"] = sum(x.ev["natural_only_reasons"].values()) == want["natural_only"]
    # the camera model (Blender Position projected through the calibration)
    worst = 0.0
    beyond = 0
    for i, side in enumerate(("L", "R")):
        p = x.ref[f"position_w_{side}"].astype(np.float64)
        g = np.any(p != 0, axis=-1)
        rwh, ow = np.asarray(x.c["head_R_wh"]), np.asarray(x.c["head_origin_w_m"])
        h = (p - ow) @ rwh
        e = x.c["eyes"][i]
        cam = (h - np.asarray(e["centre_h_m"])) @ np.asarray(e["R_hc"])
        a = cam @ np.asarray(e["K"]).T
        with np.errstate(divide="ignore", invalid="ignore"):
            uv = a[..., :2] / a[..., 2:3]
        vv, uu = np.mgrid[:RAW, :RAW]
        res = np.maximum(np.abs(uv[..., 0] - uu), np.abs(uv[..., 1] - vv))
        m = g & (cam[..., 2] > 0)
        if m.any():
            worst = max(worst, float(res[m].max()))
            beyond += int((res[m] > CAM_TOL).sum())
    cm = x.ev["camera_model"]
    d["camera_model"] = cm["ok"] == (beyond == 0) and abs((max(cm["L"]["max_abs_residual_px"] or 0,
                                                                cm["R"]["max_abs_residual_px"] or 0)) - worst) <= 1e-9
    return all(d.values()), d


def c35(x):
    sys.path.insert(0, str(HERE))
    import ab1a_visuals as V
    figs, _d = V.render_all(x.run)
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    bad = []
    for name in V.FIGURES:
        p = x.vis / name
        if name in figs:
            if not p.is_file() or p.read_bytes() != V.png_bytes(figs[name]) or man["figures"][name].get("sha256") != sha256(p):
                bad.append(name)
        elif p.exists() or "omitted" not in man["figures"][name]:
            bad.append(name)
    return not bad, {"figures": sorted(figs), "mismatch": bad}


def c36(x):
    argv = _argv_text(x)
    toks = [t for t in ("fsg6f", "fsg3_surface_map", "surface_map", "fusion", "surfel") if t in argv]
    files = [str(p.relative_to(x.run)) for p in x.run.rglob("*") if any(t in p.name.lower() for t in ("surfel", "surface-map", "fsg6f"))]
    imps = [i for i in static_imports() if any(t in i for t in ("fsg6f", "fsg3", "multiobject"))]
    return not toks and not files and not imps, {"argv_tokens": toks, "files": files, "imports": imps}


def c37(x):
    ch = x.changed_files
    acc = [f for f in ch if (f.startswith(("fov3d/", "tools/controller/", "tools/natural_bootstrap/", "tools/classroom_oracle/",
                                           "tools/visual_language/", "tools/baseline/", "scenes/"))
                             or (f.startswith("tools/") and f.count("/") == 1))]
    trees = {"NB1c freeze": sha256(NB1C_RUN / "selection/rgb-gaze-freeze.json") == NB1C_FREEZE_SHA
             and all(sha256(NB1C_RUN / "selection" / n) == h
                     for n, h in json.loads((NB1C_RUN / "selection/rgb-gaze-freeze.json").read_text())["files"].items()),
             "NB1c manifest": sha256(NB1C_RUN / "manifest.json") == NB1C_MANIFEST_SHA,
             "NB1c visuals": sha256(NB1C_VIS_MANIFEST[0]) == NB1C_VIS_MANIFEST[1],
             "NB1a freeze": sha256(NB1A_FREEZE[0]) == NB1A_FREEZE[1],
             "NB1b freeze": sha256(NB1B_FREEZE[0]) == NB1B_FREEZE[1]}
    nb = x.ov("nb1c_tree_ok", True)
    return not acc and all(trees.values()) and nb, {"accepted_files_changed": acc, "trees": trees}


def c38(x):
    extra = [f for f in x.changed_files if f not in DECLARED]
    return not extra, {"undeclared": extra[:8]}


def c39(x):
    rep = x.j("synthetic/synthetic-report.json")
    ok = rep["passed"] and len(rep["cases"]) == 12 and all(c["ok"] for c in rep["cases"])
    own = indep_synthetic()
    return ok and all(own.values()), {"generator": [c["ok"] for c in rep["cases"]], "checker": own}


def c40(x):
    a = x.acq
    st = a["settings"]
    passes = {s: {".".join(ch.split(".")[1:-1]) for ch in a["exr_channels_lr"][s]} for s in ("L", "R")}
    exr_passes = {s: {".".join(ch.split(".")[1:-1]) for ch in x.exr[s]["channels"]} for s in ("L", "R")}
    pose = json.loads(HEAD_POSE[0].read_text())
    ep = a["eye_pose"]
    pose_d = max(float(np.abs(np.asarray(ep["head_R_wh"]) - np.asarray(pose["head_R_wh"])).max()),
                 float(np.abs(np.asarray(ep["head_origin_w_m"]) - np.asarray(pose["head_origin_w_m"])).max()))
    det = {"device": a["device"] == DEVICE, "spp": a["spp"] == SPP and st["samples"] == SPP, "seeds": a["render_seeds_lr"] == SEEDS,
           "filter": st["pixel_filter"] == "BOX" and st["filter_width"] == 1.0 and not st["adaptive_sampling"]
           and not st["denoising"],
           "declared_passes_present_no_depth_normal": all(PASSES <= p and not ({"Depth", "Normal"} & p)
                                                          for p in passes.values()) and exr_passes == passes,
           "eye_pose": pose_d <= EYE_TOL and sha256(HEAD_POSE[0]) == HEAD_POSE[1],
           "calibration_pose": leaf_diff(x.c["head_R_wh"], ep["head_R_wh"]) <= CAL_TOL,
           "rgb_equals_exr": all(np.array_equal(x.exr[s]["rgb"], x.rgb[f"rgb_{s}"]) for s in ("L", "R")),
           "rgb_hash": a["rgb_observation_sha256"] == sha256(x.run / "acquisition/rgb-observation.npz"),
           "catalog": json.loads((x.run / "evaluation_only/instance-catalog.json").read_text())["instances"]
           == json.loads(CATALOG[0].read_text())["instances"]}
    return all(det.values()), det


def _pass_set(channels) -> set:
    return {".".join(ch.split(".")[1:-1]) for ch in channels}


def c42(x):
    """Contract sections 6 and 23: the raw EXRs hold the required passes (with their channels), no Depth / Normal, and
    otherwise exactly the recorded inherited Classroom pass set; L and R agree; the record equals the files."""
    chans = x.ov("exr_channels", {s: x.exr[s]["channels"] for s in ("L", "R")})
    passes = {s: _pass_set(chans[s]) for s in ("L", "R")}
    recorded = {s: _pass_set(x.acq["exr_channels_lr"][s]) for s in ("L", "R")}
    det = {"required_present": all(PASSES <= p for p in passes.values()),
           "required_channels": all({ch.split(".")[-1] for ch in chans[s] if ".".join(ch.split(".")[1:-1]) == name} == comp
                                    for s in ("L", "R") for name, comp in REQUIRED_CHANNELS.items()),
           "depth_normal_absent": not any(FORBIDDEN_PASSES & p for p in passes.values()),
           "extras_equal_pinned_inherited_set": all(p - PASSES == INHERITED_PASSES for p in passes.values()),
           "no_undeclared_pass": all(p <= PASSES | INHERITED_PASSES for p in passes.values()),
           "left_right_consistent": passes["L"] == passes["R"] and sorted(chans["L"]) == sorted(chans["R"]),
           "recorded_equals_files": recorded == passes
           and all(sorted(x.acq["exr_channels_lr"][s]) == sorted(chans[s]) for s in ("L", "R"))}
    det["extra_passes_observed"] = sorted(passes["L"] - PASSES)
    return all(v for k, v in det.items() if k != "extra_passes_observed"), det


def c41(x):
    rep = x.j("synthetic/blender-rehearsal/rehearsal-report.json")
    ok = rep["passed"] and rep["classroom_used"] is False and set(rep["cases"]) == {"forward", "gaze1-geometry"}
    ok &= all(all(v["checks"].values()) for v in rep["cases"].values())
    return bool(ok), {k: v["checks"] for k, v in rep["cases"].items()}


# ------------------------------------------------------------------ the checker's own synthetic cases (check 39)
def _plane_pair(c, z, seed=11):
    """A textured plane perpendicular to the rectified axis at rectified depth z (the checker's own renderer)."""
    r = indep_rectification(c)
    rl, cl = np.asarray(c["eyes"][0]["R_hc"]), np.asarray(c["eyes"][0]["centre_h_m"])
    n = unit((np.array([0.0, 0.0, 1.0]) @ r["R1"]) @ rl.T)
    a = unit(np.cross(n, [0.0, 1.0, 0.0]))
    b = np.cross(n, a)
    rng = np.random.default_rng(seed)
    tex = cv2.GaussianBlur(rng.random((900, 900, 3)).astype(np.float32), (0, 0), 1.3)
    tex = 0.05 + 0.9 * (tex - tex.min()) / (tex.max() - tex.min())
    vv, uu = np.mgrid[:RAW, :RAW].astype(np.float64)
    out = {}
    for i, side in enumerate(("L", "R")):
        e = c["eyes"][i]
        o = np.asarray(e["centre_h_m"], float)
        pix = np.stack([uu, vv, np.ones_like(uu)], -1) @ np.linalg.inv(np.asarray(e["K"])).T
        dirs = unit(pix @ np.asarray(e["R_hc"]).T)
        t = (z - (o - cl) @ n) / (dirs @ n)
        X = o + dirs * t[..., None] - (cl + n * z)
        sx = ((X @ a) / 0.006 + 450).astype(np.float32)
        sy = ((X @ b) / 0.006 + 450).astype(np.float32)
        out[f"rgb_{side}"] = cv2.remap(tex, sx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    return out, r


def indep_synthetic() -> dict:
    sys.path.insert(0, str(TOOLS))
    sys.path.insert(0, str(HERE))
    import fsg_geometry as FG
    import fsg_stereo as FS
    import ab1a_stereo as ST
    out = {}
    c = FG.make_calibration("full", 0.0, 0.0, VERGENCE, tangent_frame="baseline_projected")
    rgb, r = _plane_pair(c, 2.5)
    p = indep_pipeline(c, rgb)
    d_true = -float(r["P2"][0, 3]) / 2.5
    e = p["disparity_px"][p["valid"]] - d_true
    out["own pipeline recovers a plane at 2.5 m"] = bool(p["valid"].mean() > 0.9 and abs(float(np.median(e))) < 0.05)
    rec, _ = ST.compute_natural(c, rgb)
    out["generator equals the checker's pipeline"] = bool(np.array_equal(rec["valid"], p["valid"])
                                                          and np.array_equal(rec["disparity_px"], p["disparity_px"]))
    ids = np.ones((RAW, RAW), np.int32)
    acc, _m = FS.compute(c, {**rgb, "instance_L": ids, "instance_R": ids})
    out["with uninformative identity the accepted truth-assisted matcher gives the same result"] = bool(
        np.array_equal(acc["valid"], rec["valid"]) and np.array_equal(acc["disparity_px"], rec["disparity_px"])
        and np.array_equal(np.nan_to_num(acc["xyz_h"]), np.nan_to_num(rec["xyz_h"])))
    rej = []
    for yaw in (-90.0, 90.0):
        try:
            FG.make_calibration("full", yaw, 0.0, VERGENCE, tangent_frame="baseline_projected")
        except ValueError:
            rej.append(yaw)
    out["look along +/- baseline rejected"] = rej == [-90.0, 90.0]
    try:
        ST.compute_natural(c, {**rgb, "position_w_L": np.zeros((RAW, RAW, 3), np.float32)})
        out["an observation with truth is refused"] = False
    except ValueError:
        out["an observation with truth is refused"] = True
    return out


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("accepted NB1c freeze identity", c01), ("candidate-gazes source full hash", c02),
    ("exactly the rank-1 gaze is consumed", c03), ("yaw / pitch exactly +76.75 / +7.75", c04),
    ("no gaze movement or snapping", c05), ("exactly one canonical acquisition", c06), ("no controller command", c07),
    ("no second gaze", c08), ("accepted fsg_geometry / fsg_stereo / CO1 / render sources unchanged", c09),
    ("CORE_FOV = 12 deg", c10), ("full core = 256", c11), ("IPD = 0.063 m", c12), ("vergence = 2.10 m", c13),
    ("tangent_frame = baseline_projected", c14), ("depth-search bounds [0.75, 4.5] m", c15),
    ("baseline-projected local +X recomputes", c16), ("L and B_perp recompute; pre-look precedes acquisition", c17),
    ("RGB observation holds exactly rgb_L / rgb_R", c18), ("matcher opened only calibration + RGB observation", c19),
    ("matcher did not open evaluation_only", c20), ("natural result holds no identity / truth field", c21),
    ("rectification recomputes independently", c22), ("SGBM / gate constants are the frozen instrument", c23),
    ("no instance-equality guard (static audit)", c24), ("support is calibration-only", c25),
    ("LR-consistency validity recomputes", c26), ("texture validity recomputes", c27),
    ("fixed depth-search validity recomputes", c28), ("valid mask recomputes from the natural terms", c29),
    ("XYZ / range / z_rect recompute from disparity and calibration", c30),
    ("measurement freeze verified before reference access", c31), ("evaluation did not alter the frozen measurement", c32),
    ("reference geometry recomputes from evaluation-only truth", c33), ("evaluation statistics recompute", c34),
    ("figures regenerate deterministically", c35), ("no surface map / fusion / FSG6f", c36),
    ("accepted NB1a / NB1b / NB1c / controller / fov3d / FSG files unchanged", c37),
    ("changed tracked files are declared AB1a / layout / handoff files only", c38),
    ("synthetic known answers (generator and independent)", c39),
    ("acquisition settings, EYE pose, declared passes (no Depth / Normal), RGB = EXR Combined", c40),
    ("Blender rehearsal known answers", c41),
    ("raw EXR passes: required present, no Depth / Normal, extras = the pinned inherited set (sections 6, 23)", c42)],
    start=1)]


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


def edit_npz(path: Path, fn) -> None:
    with np.load(path, allow_pickle=False) as z:
        d = {k: np.asarray(z[k]).copy() for k in z.files}
    fn(d)
    path.unlink()
    np.savez_compressed(path, **d)


def refreeze(m: Path, names) -> None:
    edit_json(m / "measurement/measurement-freeze.json",
              lambda d: d["files"].update({n: sha256(m / n) for n in names}))


def regenerate(m: Path, variant: dict, scrub: bool = False) -> None:
    """Rebuild the mirror's natural measurement with a deliberately wrong matcher variant (refrozen).  ``scrub`` also
    hides the variant in the recorded configuration, so only the independent recomputation can expose it."""
    sys.path.insert(0, str(HERE))
    import ab1a_stereo as ST
    c = json.loads((m / "acquisition/calibration.json").read_text())
    obs = ST.load_observation(m / "acquisition/rgb-observation.npz")
    rec, summ = ST.compute_natural(c, obs, variant)
    if scrub:
        summ["matcher"]["variant"] = {}
    summ["inputs_sha256"] = json.loads((m / "measurement/stereo-summary.json").read_text())["inputs_sha256"]
    (m / "measurement/stereo-result.npz").unlink()
    np.savez_compressed(m / "measurement/stereo-result.npz", **rec)
    (m / "measurement/stereo-summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    edit_json(m / "measurement/measurement-freeze.json", lambda d: d.update(matcher_config_sha256=summ["matcher_config_sha256"]))
    refreeze(m, ["measurement/stereo-result.npz", "measurement/stereo-summary.json"])


def corruptions():
    def calib(fn):
        def f(m, v, c):
            edit_json(m / "acquisition/calibration.json", fn)
            refreeze(m, ["acquisition/calibration.json"])
        return f

    def legacy(m, v, c):
        sys.path.insert(0, str(TOOLS))
        import fsg_geometry as FG
        cal = json.loads((m / "acquisition/calibration.json").read_text())
        new = FG.make_calibration("full", YAW, PITCH, VERGENCE, head_r_wh=np.asarray(cal["head_R_wh"]),
                                  head_origin_w=np.asarray(cal["head_origin_w_m"]))
        new["tangent_frame"] = "legacy_upright"
        (m / "acquisition/calibration.json").write_text(json.dumps(new, indent=1, sort_keys=True) + "\n")
        refreeze(m, ["acquisition/calibration.json"])

    def nat(fn, names=("measurement/stereo-result.npz",)):
        def f(m, v, c):
            edit_npz(m / "measurement/stereo-result.npz", lambda z: fn(z, c))
            refreeze(m, list(names))
        return f

    def flip_valid(z, c):
        z["valid"][128, 128] = ~z["valid"][128, 128]

    def flip_support(z, c):
        z["term_support_left"][0, 0] = ~z["term_support_left"][0, 0]

    def bump_disp(z, c):
        z["disparity_px"][128, 128] += 0.5

    def bump_xyz(z, c):
        z["xyz_h"][128, 128] = np.nan_to_num(z["xyz_h"][128, 128]) + np.float32(0.01)

    def p2(z, c):
        z["P2"][0, 3] *= 1.01

    def identity_field(z, c):
        z["instance_id"] = c.orc["instance_id"].copy()

    def identity_mask(kind):
        def f(m, v, c):
            def fn(z):
                ids = c.orc["instance_id"]
                if kind == "interior":
                    k = np.ones((7, 7), np.uint8)
                    a = ids.astype(np.float32)
                    mask = (ids > 0) & (cv2.erode(a, k) == a) & (cv2.dilate(a, k) == a)
                else:
                    mask = c.orc["right_reprojection_instance"] == ids
                z["valid"] &= mask
                z[f"term_{kind}_identity"] = mask
            edit_npz(m / "measurement/stereo-result.npz", fn)
            edit_json(m / "measurement/measurement-opened-files.json", lambda d: d["data_reads"].append(
                str((m / "evaluation_only/reference-observation.npz").resolve())))
            refreeze(m, ["measurement/stereo-result.npz", "measurement/measurement-opened-files.json"])
        return f

    def opened(path_rel):
        def f(m, v, c):
            p = str(c.run / path_rel)
            edit_json(m / "measurement/measurement-opened-files.json", lambda d: (
                d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True}),
                d["data_reads"].append(p)))
            refreeze(m, ["measurement/measurement-opened-files.json"])
        return f

    def position_geometry(m, v, c):
        """A matcher that takes its geometry from Position must open it; the probe records that read too."""
        edit_json(m / "measurement/measurement-opened-files.json", lambda d: d["data_reads"].append(
            str((m / "evaluation_only/reference-observation.npz").resolve())))

        def fn(z):
            geom = c.orc["left_geometry"].astype(bool)
            z["valid"] = geom.copy()
            xyz = c.orc["left_position_h"].astype(np.float32).copy()
            xyz[~geom] = np.nan
            z["xyz_h"] = xyz
        edit_npz(m / "measurement/stereo-result.npz", fn)
        refreeze(m, ["measurement/stereo-result.npz", "measurement/measurement-opened-files.json"])

    def after_eval(m, v, c):
        edit_json(m / "measurement/stereo-summary.json", lambda d: d.update(valid_count=d["valid_count"] + 1))

    def early_ref(m, v, c):
        def fn(d):
            ev = d["ordered_data_events"]
            t = next(p for p in ev if "evaluation_only" in str(p))
            ev.remove(t)
            ev.insert(0, t)
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

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

    def action_gaze3(m, v, c):
        edit_json(m / "source/nb1c-action-manifest.json", lambda d: d["gaze"].update(rank=3, row=231, col=510,
                                                                                      yaw_deg=75.25, pitch_deg=-25.75))

    def rgb_extra(m, v, c):
        edit_npz(m / "acquisition/rgb-observation.npz", lambda z: z.update(instance_L=c.ref["instance_L"]))

    def seeds(m, v, c):
        edit_json(m / "acquisition/acquisition.json", lambda d: d["render_seeds_lr"].update(L=104729 * 141, R=104729 * 141 + 1))

    def pose(m, v, c):
        edit_json(m / "acquisition/acquisition.json", lambda d: d["eye_pose"]["head_origin_w_m"].__setitem__(0, d["eye_pose"]["head_origin_w_m"][0] + 1e-3))

    def ev_stat(m, v, c):
        edit_json(m / "evaluation/evaluation-summary.json", lambda d: d["counts"].update(reference_valid=d["counts"]["reference_valid"] + 1))

    def ref_geom(m, v, c):
        edit_npz(m / "evaluation/oracle-reference.npz", lambda z: z["valid"].__setitem__((128, 128), ~z["valid"][128, 128]))

    def synth(m, v, c):
        edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))

    def lever(m, v, c):
        edit_json(m / "prelook/prelook-geometry.json", lambda d: d.update(L=d["L"] * 1.01))
        refreeze(m, ["prelook/prelook-geometry.json"])

    def rgb_pixel(m, v, c):
        edit_npz(m / "acquisition/rgb-observation.npz", lambda z: z["rgb_L"].__setitem__((320, 320, 0), z["rgb_L"][320, 320, 0] + 0.25))
        refreeze(m, ["acquisition/rgb-observation.npz"])

    def changed(extra):
        return lambda m, v, c: {"changed_files": c.changed_files + [extra]}

    def reg(**variant):
        return lambda m, v, c: regenerate(m, variant)

    def gate_off(term, key):
        def f(m, v, c):
            if c.nat[term].all():
                return {"not_applicable": f"{term} already passes on every core pixel: disabling it changes nothing"}
            regenerate(m, {key: False}, scrub=True)
        return f

    def audit(tok):
        return lambda m, v, c: {"static_audit": {"forbidden_tokens": [tok], "truth_assisted_calls": []}}

    def exr_chans(fn):
        """Checker-only, in-process: the raw EXR channel lists as read from the files, then altered."""
        def f(m, v, c):
            ch = {s: list(c.exr[s]["channels"]) for s in ("L", "R")}
            fn(ch)
            return {"exr_channels": ch}
        return f

    def drop(name):
        return lambda ch: [ch.__setitem__(s, [k for k in ch[s] if ".".join(k.split(".")[1:-1]) != name]) for s in ch]

    def add(chan, sides=("L", "R")):
        return lambda ch: [ch[s].append(chan) for s in sides]

    def recorded_set(m, v, c):
        edit_json(m / "acquisition/acquisition.json", lambda d: d["exr_channels_lr"].__setitem__(
            "L", [k for k in d["exr_channels_lr"]["L"] if ".Emission." not in k]))

    second = {"command": "acquire", "status": "ok", "argv": ["ab1a_run.py", "acquire"], "code": {"dirty": False, "pushed": True},
              "blender": {"mode": "canonical", "argv": ["blender", "-b", "x.blend", "--mode", "canonical"]}}
    return [
        ("gaze #1 moved (+0.5 deg yaw)", ("04", "05"), calib(lambda d: d["gaze_yaw_pitch_deg"].__setitem__(0, YAW + 0.5))),
        ("gaze #3 substituted in the action", ("03", "04"), action_gaze3),
        ("legacy_upright tangent frame", ("14", "16"), legacy),
        ("IPD altered (0.064 m)", ("12",), calib(lambda d: d.update(ipd_m=0.064))),
        ("vergence altered (2.20 m)", ("13",), calib(lambda d: d.update(prescribed_vergence_distance_m=2.2))),
        ("depth-search range altered ([0.5, 4.5] m)", ("15", "28"), calib(lambda d: d.update(depth_search_z_rect_m=[0.5, 4.5]))),
        ("SGBM block size altered (regenerated, 7)", ("23", "29"), reg(block_size=7)),
        ("uniqueness ratio altered (regenerated, 5)", ("23", "29"), reg(uniqueness_ratio=5)),
        ("LR check disabled (regenerated; configuration record scrubbed)", ("26", "29"), gate_off("term_lr", "use_lr")),
        ("texture check disabled (regenerated; record scrubbed)", ("27", "29"), gate_off("term_texture", "use_texture")),
        ("instance-interior masking added", ("19", "21", "29"), identity_mask("interior")),
        ("same-instance equality added", ("19", "21", "29"), identity_mask("same")),
        ("Object Index opened during measurement", ("19", "20"), opened("evaluation_only/reference-observation.npz")),
        ("Position opened during measurement", ("19", "20"), opened("evaluation_only/raw_L.exr")),
        ("disparity geometry replaced by Position truth", ("19", "29", "30"), position_geometry),
        ("support mask altered", ("25", "29"), nat(flip_support)),
        ("one valid pixel altered", ("29",), nat(flip_valid)),
        ("one disparity altered", ("30",), nat(bump_disp)),
        ("one XYZ point altered", ("30",), nat(bump_xyz)),
        ("frozen measurement modified after evaluation", ("32",), after_eval),
        ("reference access before the measurement freeze", ("31",), early_ref),
        ("controller command in the process log", ("07",), log({"command": "controller02", "status": "ok",
                                                                "argv": ["fov3d/experiments/classroom_oracle/controller02.py"]})),
        ("FSG6f run in the process log", ("36",), log({"command": "measure", "status": "ok", "argv": ["tools/fsg6f_frontier.py"]})),
        ("a second gaze executed", ("06", "08"), log({**second, "argv": ["ab1a_run.py", "acquire", "--yaw", "75.25"]})),
        ("gaze 1 re-rendered after evaluation", ("06",), log(second)),
        ("a visual pixel altered", ("35",), pixel),
        ("accepted FSG code modified", ("37",), changed("tools/fsg_stereo.py")),
        ("controller code modified", ("37",), changed("tools/controller/check_controller02.py")),
        ("NB1a code modified", ("37",), changed("tools/natural_bootstrap/nb1a_discovery.py")),
        ("NB1b code modified", ("37",), changed("tools/natural_bootstrap/nb1b_serviceability.py")),
        ("NB1c code modified", ("37",), changed("tools/natural_bootstrap/nb1c_attention.py")),
        ("an undeclared tracked file changed", ("38",), changed("README.md")),
        ("an extra array in the RGB observation", ("18",), rgb_extra),
        ("an identity field in the natural result", ("21",), nat(identity_field)),
        ("identity token in the natural matcher (static)", ("24",), audit("instance_L")),
        ("render seed taken from an object id", ("40",), seeds),
        ("EYE pose altered", ("40",), pose),
        ("an evaluation statistic altered", ("34",), ev_stat),
        ("reference geometry altered", ("33",), ref_geom),
        ("a synthetic known-answer case failed", ("39",), synth),
        ("stereo leverage L altered in the pre-look record", ("17",), lever),
        ("rectification P2 altered in the natural result", ("22",), nat(p2)),
        ("one RGB observation pixel altered", ("40",), rgb_pixel),
        ("raw EXR gains a Depth pass", ("42",), exr_chans(add("interior.Depth.Z"))),
        ("raw EXR gains a Normal pass", ("42",), exr_chans(add("interior.Normal.X"))),
        ("raw EXR loses the Position pass", ("42",), exr_chans(drop("Position"))),
        ("raw EXR loses the Object Index pass", ("42",), exr_chans(drop("Object Index"))),
        ("raw EXR gains an unknown, unrecorded pass", ("42",), exr_chans(add("interior.Mist.Z"))),
        ("raw EXR lacks one pinned inherited pass", ("42",), exr_chans(drop("Emission"))),
        ("left / right EXR pass sets differ", ("42",), exr_chans(add("interior.Volume Direct.R", ("R",)))),
        ("the recorded inherited-pass set altered (acquisition.json)", ("42",), recorded_set),
    ]


def corruption_suite(run: Path, vis: Path, base: Ctx) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    for name, targets, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="ab1a-corrupt-") as td:
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
            ctx.overrides = overrides
            with contextlib.redirect_stdout(io.StringIO()):
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
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1A_CHECKS_PASS")
    out = {"schema": "AB1a-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis, base)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1A_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
