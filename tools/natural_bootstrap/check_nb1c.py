"""Natural Bootstrap-1c: fail-capable checks of the RGB candidate gaze.

    .venv/bin/python tools/natural_bootstrap/check_nb1c.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Contract: docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md, section 18 (checks 1-36).  The checker
keeps its own literal constants and recomputes independently of the generator:
- its own grid directions (yaw / pitch formulas) and solid-angle row weights;
- the sRGB -> linear table (Python math, per code);
- the CENTER / SURROUND membership of EVERY candidate by the chord formula ||d_i - d_g|| <= 2 sin((R + eps) / 2)
  over a provable superset box (rows within R in latitude; |d lambda| <= asin(sin R / cos phi) + 1 column, or the
  whole row near a pole), derived per candidate (process pool);
- solid-angle weighted means and the TWO-PASS variance; D_RGB and A;
- its own greedy NMS (chord-threshold suppression, its own tie rule);
- the post-freeze evaluation descriptors from the pinned NB1a / NB1b products.

``--corruptions`` plants defects in throwaway mirrors (JSON copied, other files linked) or as in-process
mutants.  They count only when the uncorrupted baseline passes.  ``--write-summary`` writes only
``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ProcessPoolExecutor
import contextlib
import hashlib
import io
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREFIX = "[nb1c-check]"

# ---- literal copies (contract sections 2-11); deliberately not imported from nb1c_spec
W, H = 720, 360
N = W * H
CORE_FOV = 12.0
R_C = math.radians(6.0)
R_S = math.radians(12.0)
R_FULL = math.atan(math.sqrt(2.0) * math.tan(math.radians(6.0)))
D_MIN = 2.0 * R_FULL
EPS = 1e-12
TIE = 1e-12
VAR_EPS = 1e-12
K = 6
TOL = {"W_rel": 1e-12, "mu": 1e-12, "D": 1e-12, "V": 1e-11, "A_abs": 1e-6, "A_rel": 1e-9}
BASE = "7d1c1b97e1e29be4bd5e45066507f9c12be006bc"
NB1B_ACCEPTED = "0238f007a505f38087c9e40442243003cd3716cc"
SHARED = Path("/home/lvelho/rd/f3d-vision")
NB1A_RUN = SHARED / "previews/natural-bootstrap-1a-range-connectivity"
NB1B_RUN = SHARED / "previews/natural-bootstrap-1b-foveal-serviceability"
NB1A_VIS = SHARED / "visuals/natural-bootstrap-1a-range-connectivity"
NB1B_VIS = SHARED / "visuals/natural-bootstrap-1b-foveal-serviceability"
RGB_PATH = NB1A_RUN / "input/rgb-sensory.npz"
RGB_SHA = "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e"
NB1A_MANIFEST_SHA = "69021c636ef735edf425dab82504473d973735ddeb8109d06ca1e6ebb12fe12e"
NB1A_INPUT_MANIFEST_SHA = "6d2547021a2abf71916118b3780a5e97b78e5687539cfd96f4d32de3b345dfaa"
SENSOR_SHA = "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54"
EVAL_INPUTS = {   # name -> (run root, relative path, sha256)
    "nb1a/input/range-sensory.npz": ("nb1a", "input/range-sensory.npz",
                                     "02bdf22472ab542545102ec5c3c7f092953a1f89ee2f61ebe62225545ed0883b"),
    "nb1a/discovery/hypothesis-raster.npz": ("nb1a", "discovery/hypothesis-raster.npz",
                                             "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88"),
    "nb1a/discovery/hypotheses.json": ("nb1a", "discovery/hypotheses.json",
                                       "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b"),
    "nb1a/evaluation/reference-cells.npz": ("nb1a", "evaluation/reference-cells.npz",
                                            "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76"),
    "nb1a/evaluation/overlap-summary.json": ("nb1a", "evaluation/overlap-summary.json",
                                             "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb"),
    "nb1b/selection/serviceability.json": ("nb1b", "selection/serviceability.json",
                                           "2c83d76cd4c61bea3218b24893effe6e83a2965c9aabd300da7843150e53c1b1"),
    "nb1b/selection/primary-look-queue.json": ("nb1b", "selection/primary-look-queue.json",
                                               "1cc867b1a3fb69ed6be6487625b42ae8912f61536ae2e15bb7986a126795dc10"),
    "nb1b/selection/secondary-look-queue.json": ("nb1b", "selection/secondary-look-queue.json",
                                                 "5481497c62f9c0f154fc2d9eb774103e70e1dd61d8ceb5c84181522e7b9b5875"),
    "nb1b/selection/environment-candidate.json": ("nb1b", "selection/environment-candidate.json",
                                                  "427346e91483fd74caf0afefe518fd2700a3c9cfe5ab27a93aae104dbea59759"),
    "nb1b/selection/serviceability-freeze.json": ("nb1b", "selection/serviceability-freeze.json",
                                                  "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a"),
}
NB1A_RUN_FILES = {   # the whole accepted NB1a run tree
    "check-summary.json": "7eee407a66a75c928537c4ea7e06c74014732a06b70dfa60621aaf880018f74b",
    "discovery/bootstrap-freeze.json": "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a",
    "discovery/continuity-edges.npz": "149ce63dbae20789c502f1116f032221ea19e2d4151bdef3f03fe6dda8389511",
    "discovery/discovery-opened-files.json": "9de6577423da18c819d563bf1296b0775113b4dd71b0117964a2ec37a8ddb669",
    "discovery/discovery-summary.json": "fac0adb39331d9ff2a3305791b2aff3f0edbd2a43503d3d3572437a74cf2e4ec",
    "discovery/hypotheses.csv": "ca45849740863fbf1b4d80bf34e432da26e4501dbf2fbfeb7922a16ddf0fa9e9",
    "discovery/hypotheses.json": "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b",
    "discovery/hypothesis-raster.npz": "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88",
    "discovery/seeds.json": "c0362d9c898303869117bdd3bb303dadaf15c2d19b94733467fe2ade7c1fb556",
    "evaluation/evaluation-opened-files.json": "92ec643716b324d4648b30f7e1b5a0e8b8e32ff7fcd163ca2bd77eb90c502d08",
    "evaluation/overlap-matrix.npz": "e4f4bde03d2bfb82cc8a44ab6cbc3b74afec624677051da6fc882c96e502462d",
    "evaluation/overlap-summary.json": "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb",
    "evaluation/reference-cells.npz": "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76",
    "evaluation/rgb-edge-contrast.npz": "a065901f7ff1d069bfa660614d2761e71c3dcde272f17e93c78d0c54ca81829d",
    "evaluation/rgb-edge-diagnostics.json": "7ea56745ff2894526406b57e0786c74ff67920b162fb0031a02c93259e276d25",
    "input/input-manifest.json": "6d2547021a2abf71916118b3780a5e97b78e5687539cfd96f4d32de3b345dfaa",
    "input/input-opened-files.json": "a2138087173781c8a74c18de5dfc662a55eec34fff59a85ff1789c2a3416f4b7",
    "input/range-sensory.npz": "02bdf22472ab542545102ec5c3c7f092953a1f89ee2f61ebe62225545ed0883b",
    "input/rgb-sensory.npz": "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e",
    "manifest.json": "69021c636ef735edf425dab82504473d973735ddeb8109d06ca1e6ebb12fe12e",
    "process-log.jsonl": "fcd7288cdec4f17fd1578c4aa0bb4c2b2fd509c957c745fb7475d81ef4f7a3cf",
    "synthetic/synthetic-report.json": "df3036492e29536a2d5f9183535de61bcead971605e02bacb06038aa2f4616fc",
}
NB1A_VIS_FILES = {
    "overview.png": "eb3348767ce0bbb80c6edd623f051bd1e98aac4172eb4d687318a66dc2e19140",
    "hypothesis-panorama.png": "c0471cf98e02dd3f97c9486a32073c0c3722faaf80f25324456ded1e887f7b28",
    "seed-panorama.png": "f4b853a900f0be0f0eefe78d55b71634bdc03c30370886cc10e505cb35492fd7",
    "rgb-edge-contrast.png": "2ed52df43cdf16a14639534b1842e80d657fe22fd8c77e9f70529d8f276c4ecc",
    "visuals-manifest.json": "78d9d96c6002f571a85f5adac20cf3ed3aabe9270ab068e4541c1ffec78ceecc",
}
NB1B_RUN_FILES = {   # the whole accepted NB1b run tree
    "check-summary.json": "f65169319400a6ec3c889433727802748cae85279da688440e14f831d70b9a30",
    "evaluation/candidate-reference-summary.json": "11e74b9a77163679f37122999a4f4ed7b49fe7487155d8183456a37a427845b1",
    "evaluation/evaluation-opened-files.json": "20c9d48a110b3ca5c5532b9899b7aa75c3ce7018e1e182b001d95b18b3d68649",
    "manifest.json": "c7caa630ea34165dab5470dcfa1ec12a075413d852e44d9a6b80030075978cb4",
    "process-log.jsonl": "8347ff2658818e0403e61cbb13f1041027d44dc99a54d0f9cd5e91be0c4018b5",
    "selection/environment-candidate.json": "427346e91483fd74caf0afefe518fd2700a3c9cfe5ab27a93aae104dbea59759",
    "selection/footprints.npz": "8c00fa5a824beff65124108019e5d112419cad7c7d0c6681e49500a40390c77a",
    "selection/footprint-stats.json": "ca60a3fa27e14dc16efc75ffa492978e28a125394fe7bf7507f57725ba63681d",
    "selection/primary-look-queue.json": "1cc867b1a3fb69ed6be6487625b42ae8912f61536ae2e15bb7986a126795dc10",
    "selection/secondary-look-queue.json": "5481497c62f9c0f154fc2d9eb774103e70e1dd61d8ceb5c84181522e7b9b5875",
    "selection/selection-opened-files.json": "391890cda405f65657da80046942d1f1f8a15f573f29f98ab7b76c7637a9fd95",
    "selection/selection-summary.json": "da815b9a903f1c6e717a1e3d05328e95019b383f22afc72da29aad0194cc16ad",
    "selection/serviceability.csv": "d00862063c8795c3ee3cb2c34f689bc79bb4f0b4253cda157b2f086ead6fbd81",
    "selection/serviceability-freeze.json": "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a",
    "selection/serviceability.json": "2c83d76cd4c61bea3218b24893effe6e83a2965c9aabd300da7843150e53c1b1",
    "source/nb1a-source-manifest.json": "ef91920009ff43b65b678a21c268041109d923f4c093dffbe1b48c330baf42de",
    "synthetic/synthetic-report.json": "7fd35509a2cb237a8c411ac4fc7a8ff63d70f310c609a2fa51e87e8254c80b8e",
}
NB1B_VIS_FILES = {
    "class-counts.png": "4bf194e6d3da13b53ed4a8deb607f12318892ce4065b87b8b1ffd41032a48c53",
    "environment-candidate.png": "30a579380cda014df98b5ca184289055c5878e8ab5f980ae73cf81e6afaaa1fa",
    "footprint-examples.png": "bab8bb95177e5dc62d9e6d53205e430cb072a87a399b0b5beb1e7b67a02c201b",
    "overview.png": "417084b6542c3a474c6f9cef463c65e18b480769da9d5f9aa18624fb70e7abb5",
    "primary-look-panorama.png": "56771f2f2868181c9b7fb1c461877cc93c528b91a45a0ad3a31155d455161e65",
    "secondary-look-panorama.png": "f54cc38a6184cff4e89b10c1d9b636fee10aa45c03f8fb08a16a78f40c1477bf",
    "serviceability-panorama.png": "f6a25f5da37611a23a2fffa94d60673515372b1629c74bd32a0640cffd602ee1",
    "visuals-manifest.json": "1d7e2a7c822e2e57192e4a64ce3e4af5e6a6f4a0ceb5631ed2e1e7a60a53398e",
}
RENDER_PATH = SHARED / "previews/breadth-1-classroom-234-spherical-glance/render"
RENDER_DIR = {"canonical.exr": "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8",
              "render-metadata.json": "7c05b80d2d0291f8e12c0886008957b2579e27561b78a766e156b29ec2282157"}
FROZEN = ["../source/rgb-source-manifest.json", "attention-score.npz", "attention-diagnostics.npz",
          "candidate-gazes.json", "nms-rounds.json", "selection-summary.json", "selection-opened-files.json"]
SELECTION_CODE = ["nb1c_spec.py", "nb1c_attention.py", "nb1a_spec.py", "nb1a_guard.py", "fsg_geometry.py"]
NB1C_FILES = {"docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md",
              "docs/natural-bootstrap/nb1c-rgb-candidate-gaze-report.md",
              "tools/repository/check_repository_layout.py"} | {
    f"tools/natural_bootstrap/{n}" for n in ("nb1c_spec.py", "nb1c_attention.py", "nb1c_run.py", "nb1c_visuals.py",
                                             "check_nb1c.py")}
COMMANDS = {"synthetic", "select", "freeze", "evaluate", "visualize"}
FORBIDDEN_IMPORTS = re.compile(r"^(fov3d\.control|fov3d\.experiments\.classroom_oracle\.controller|classroom_oracle1_run|"
                               r"classroom_oracle1_matcher|classroom_oracle1_epistemic|classroom_oracle1_eval|"
                               r"multiobject2c_policy|fsg6f|fsg3_surface_map|fsg_stereo|controller0|bpy|exr_lite|OpenEXR)")
SELECTION_IMPORTS = {"__future__", "math", "json", "numpy", "pathlib", "sys", "hashlib", "nb1a_spec", "nb1c_spec",
                     "fsg_geometry"}
SELECTION_ROUTINES = ("select", "verify_rgb_source", "verify_sensor", "write_selection")
FORBIDDEN_TOKENS = ("range-sensory", "range_m", "valid_mask", "hypothes", "seeds", "serviceab", "reference-cells",
                    "object_index", "Object Index", "overlap", "catalog", "Position", ".exr", "controller", "nb1b",
                    "NB1B", "EVALUATION_INPUTS", "NB1A_RUN", "NB1B_RUN", "discovery")
EVAL_KEYS = re.compile(r"o0|catalog|authored|object.?index|composition|dominant|reference|hypothes|valid_range|range_m|"
                       r"nb1b|serviceab|gaze_class|point_h", re.IGNORECASE)
FIGURES = ["overview.png", "rgb-input.png", "attention-map.png", "candidate-gazes.png", "center-surround-examples.png",
           "candidate-crops.png", "candidate-evaluation.png", "attention-score-distribution.png",
           "nb1b-reference-comparison.png"]
NB1B_CLASSES = ["ENVIRONMENT_CANDIDATE", "PRIMARY_LOOK", "SECONDARY_LOOK", "MARGINAL", "EDGE_ONLY"]
_CACHE: dict = {}
_G: dict = {}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ independent geometry, colour and statistics
def lat_lon() -> tuple[np.ndarray, np.ndarray]:
    return np.radians(90.0 - 0.5 * (np.arange(H) + 0.5)), np.radians(-180.0 + 0.5 * (np.arange(W) + 0.5))


def directions() -> np.ndarray:
    if "dirs" not in _CACHE:
        lat, lon = lat_lon()
        x = np.outer(np.cos(lat), np.sin(lon))
        y = np.repeat(np.sin(lat)[:, None], W, 1)
        z = -np.outer(np.cos(lat), np.cos(lon))
        _CACHE["dirs"] = np.stack([x, y, z], -1)          # (H, W, 3)
    return _CACHE["dirs"]


def weights() -> np.ndarray:
    lat_edges = [math.pi / 2 - j * math.pi / H for j in range(H + 1)]
    return np.array([(2 * math.pi / W) * (math.sin(lat_edges[j]) - math.sin(lat_edges[j + 1])) for j in range(H)])


def lin_table() -> np.ndarray:
    out = []
    for code in range(256):
        s = code / 255.0
        out.append(s / 12.92 if s <= 0.04045 else math.pow((s + 0.055) / 1.055, 2.4))
    return np.array(out)


def chord2(radius: float) -> float:
    return (2.0 * math.sin((radius + EPS) / 2.0)) ** 2


def _circ(off: np.ndarray) -> np.ndarray:
    a = np.abs(off) % W
    return np.minimum(a, W - a)


def _box(j0: int) -> np.ndarray:
    """Column offsets of a provable superset box for the 12-degree disk around a candidate in row j0."""
    lat, _ = lat_lon()
    c = math.cos(lat[j0])
    if c <= math.sin(R_S) + 1e-12:
        return np.arange(-(W // 2 - 1), W // 2 + 1)
    kk = int(math.ceil(math.degrees(math.asin(math.sin(R_S) / c)) / 0.5)) + 1
    return np.arange(-kk, kk + 1)


def _row_job(j0: int) -> dict:
    """Brute-force membership, counts, weighted means and two-pass variances for the 720 candidates of row j0."""
    lin, w, dirs = _G["lin"], _G["w"], _G["dirs"]
    lat, _ = lat_lon()
    off = _box(j0)
    full_box = off.size == W
    circ = _circ(off)
    c0 = np.arange(W)
    idx = (c0[:, None] + off[None, :]) % W
    gd = dirs[j0][:, None, :]
    cC, cS = chord2(R_C), chord2(R_S)
    band = np.flatnonzero(np.abs(lat - lat[j0]) <= R_S + 1e-9)
    kc, kd = np.full(H, -1, np.int64), np.full(H, -1, np.int64)
    acc = {r: {"n": np.zeros(W), "W": np.zeros(W), "S": np.zeros((W, 3))} for r in "CS"}
    masks, bad_interval, bad_edge = [], 0, 0
    for j in band:
        d2 = ((dirs[j][idx] - gd) ** 2).sum(-1)
        mC = d2 <= cC
        mD = d2 <= cS
        for m, kout in ((mC, kc), (mD, kd)):
            kcand = np.where(m.any(1), np.where(m, circ[None, :], -1).max(1), -1)
            interval = (m == (circ[None, :] <= kcand[:, None])).all(1)
            if not full_box and (m[:, 0].any() or m[:, -1].any()):
                bad_edge += 1
            if not interval.all() or (kcand != kcand[0]).any():
                bad_interval += 1
                kout[j] = -2
            else:
                kout[j] = kcand[0]
        mS = mD & ~mC
        x = lin[j][idx]
        for r, m in (("C", mC), ("S", mS)):
            acc[r]["n"] += m.sum(1)
            acc[r]["W"] += w[j] * m.sum(1)
            acc[r]["S"] += w[j] * (m[..., None] * x).sum(1)
        masks.append((j, mC, mS))
    out = {"j0": j0, "kc": kc, "kd": kd, "bad_interval": bad_interval, "bad_edge": bad_edge}
    for r in "CS":
        Wr = acc[r]["W"]
        mu = acc[r]["S"] / Wr[:, None]
        V = np.zeros(W)
        for j, mC, mS in masks:
            m = mC if r == "C" else mS
            V += w[j] * (m * ((lin[j][idx] - mu[:, None, :]) ** 2).sum(-1)).sum(1)
        out[r] = {"n": acc[r]["n"], "W": Wr, "mu": mu, "V": V / Wr}
    return out


def brute(srgb8: np.ndarray) -> dict:
    """The independent recomputation of every candidate (cached by the RGB bytes)."""
    key = ("brute", hashlib.sha256(np.ascontiguousarray(srgb8).tobytes()).hexdigest())
    if key in _CACHE:
        return _CACHE[key]
    _G.update(lin=lin_table()[srgb8], w=weights(), dirs=directions())
    order = sorted(range(H), key=lambda j: -_box(j).size)
    res = {}
    ctx = multiprocessing.get_context("fork")
    with ProcessPoolExecutor(max_workers=min(32, os.cpu_count() or 1), mp_context=ctx) as ex:
        for r in ex.map(_row_job, order, chunksize=1):
            res[r["j0"]] = r
    out = {"k_center": np.stack([res[j]["kc"] for j in range(H)]), "k_disk": np.stack([res[j]["kd"] for j in range(H)]),
           "bad_interval": sum(res[j]["bad_interval"] for j in range(H)), "bad_edge": sum(res[j]["bad_edge"] for j in range(H))}
    for r in "CS":
        out[f"n_{r}"] = np.stack([res[j][r]["n"] for j in range(H)]).round().astype(np.int64)
        out[f"W_{r}"] = np.stack([res[j][r]["W"] for j in range(H)])
        out[f"mu_{r}"] = np.stack([res[j][r]["mu"] for j in range(H)])
        out[f"V_{r}"] = np.stack([res[j][r]["V"] for j in range(H)])
    out["D_RGB"] = np.sqrt(((out["mu_C"] - out["mu_S"]) ** 2).sum(-1))
    out["A"] = out["D_RGB"] / np.sqrt(out["V_C"] + out["V_S"] + VAR_EPS)
    _CACHE[key] = out
    return out


def brute_at(srgb8: np.ndarray, row: int, col: int) -> dict:
    """The definitions at one candidate (chord membership over the whole sphere, two-pass variance)."""
    lin = lin_table()[srgb8].reshape(-1, 3)
    w = np.repeat(weights(), W)
    d = directions().reshape(-1, 3)
    d2 = ((d - d[row * W + col]) ** 2).sum(1)
    out = {}
    for r, m in (("C", d2 <= chord2(R_C)), ("S", (d2 > chord2(R_C)) & (d2 <= chord2(R_S)))):
        Wr = float(w[m].sum())
        mu = (w[m, None] * lin[m]).sum(0) / Wr
        out[r] = {"n": int(m.sum()), "mu": mu, "V": float((w[m] * ((lin[m] - mu) ** 2).sum(1)).sum() / Wr),
                  "cells": np.flatnonzero(m)}
    out["D"] = float(np.linalg.norm(out["C"]["mu"] - out["S"]["mu"]))
    out["A"] = out["D"] / math.sqrt(out["C"]["V"] + out["S"]["V"] + VAR_EPS)
    return out


def nms(scores: np.ndarray, cand: np.ndarray, k: int = K, d_min: float = D_MIN) -> tuple[list[int], list[dict]]:
    """Independent greedy NMS: suppress chord < 2 sin((D_MIN - eps) / 2), i.e. alpha + eps < D_MIN."""
    a = np.asarray(scores, np.float64).reshape(-1)
    c = np.asarray(cand, np.float64).reshape(-1, 3)
    elig = np.ones(a.size, bool)
    thr = (2.0 * math.sin((d_min - EPS) / 2.0)) ** 2
    picks, rounds = [], []
    for rnd in range(1, k + 1):
        e = np.flatnonzero(elig)
        if not e.size:
            raise RuntimeError("budget")
        amax = a[e].max()
        tie = e[(amax - a[e]) <= TIE * max(1.0, abs(amax))]
        g = int(tie[0])
        sup = elig & (((c - c[g]) ** 2).sum(1) < thr)
        rest = np.setdiff1d(e, tie)
        rounds.append({"round": rnd, "index": g, "score": float(a[g]), "tie_set_size": int(tie.size),
                       "eligible_before": int(e.size), "newly_suppressed": int(sup.sum()),
                       "remaining": int(e.size - sup.sum()),
                       "margin": float(a[g] - a[rest].max()) if rest.size else None})
        elig &= ~sup
        picks.append(g)
    return picks, rounds


def alpha_chord(d_g: np.ndarray, d: np.ndarray) -> np.ndarray:
    return 2.0 * np.arcsin(np.minimum(np.linalg.norm(d - d_g, axis=-1) / 2.0, 1.0))


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = Path(run), Path(vis)
        j = lambda p: json.loads((self.run / p).read_text())  # noqa: E731
        self.source = j("source/rgb-source-manifest.json")
        self.gz = j("selection/candidate-gazes.json")
        self.gazes = self.gz["gazes"]
        self.rounds_doc = j("selection/nms-rounds.json")
        self.summ = j("selection/selection-summary.json")
        self.sopen = j("selection/selection-opened-files.json")
        self.freeze = j("selection/rgb-gaze-freeze.json")
        self.ev = j("evaluation/candidate-evaluation.json")
        self.nb = j("evaluation/nb1b-comparison.json")
        self.eopen = j("evaluation/evaluation-opened-files.json")
        self.synthetic = j("synthetic/synthetic-report.json")
        self.processes = [json.loads(l) for l in (self.run / "process-log.jsonl").read_text().splitlines() if l.strip()]
        self.vman = json.loads((self.vis / "visuals-manifest.json").read_text())
        with np.load(self.run / "selection/attention-score.npz") as z:
            self.score_files = list(z.files)
            self.A = np.asarray(z["A"])
        with np.load(self.run / "selection/attention-diagnostics.npz") as z:
            self.diag = {k: np.asarray(z[k]) for k in z.files}
        self.rgb_path = RGB_PATH
        self.nb1a_run, self.nb1b_run = NB1A_RUN, NB1B_RUN
        self.sensor_path = REPO / "tools/fsg_geometry.py"
        self.changed_files = None
        self.fov3d_changed = None
        with np.load(self.rgb_path) as z:
            self.rgb_files = list(z.files)
            self.srgb8 = np.asarray(z["srgb8"])

    def bf(self) -> dict:
        return brute(self.srgb8)

    def eval_path(self, name: str) -> Path:
        root, rel, _h = EVAL_INPUTS[name]
        return (self.nb1a_run if root == "nb1a" else self.nb1b_run) / rel


def changed_files(ctx) -> list[str]:
    if ctx.changed_files is not None:
        return ctx.changed_files
    ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    ch |= {p for p in git("ls-files", "--others", "--exclude-standard").split() if p.startswith(("tools/", "docs/", "fov3d/"))}
    return sorted(ch)


def fov3d_changed(ctx) -> bool:
    if ctx.fov3d_changed is not None:
        return ctx.fov3d_changed
    return (subprocess.run(["git", "diff", "--quiet", BASE, "--", "fov3d"], cwd=REPO).returncode != 0
            or bool(git("ls-files", "--others", "--exclude-standard", "--", "fov3d").strip()))


def _imports(src: str) -> list[str]:
    mods = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods.append(node.module or "")
    return mods


def _run_root(rec, leaves) -> Path | None:
    dirs = [Path(p) for p in rec.get("allow_write_dirs", [])]
    roots = {p.parent for p in dirs}
    return roots.pop() if len(roots) == 1 and sorted(p.name for p in dirs) == sorted(leaves) else None


def _paths(rec) -> list[str]:
    return [e.get("path", "") for e in rec.get("events", [])]


def _close(a, b, atol=0.0, rtol=0.0) -> tuple[bool, float]:
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return False, float("inf")
    d = np.abs(a - b)
    return bool((d <= atol + rtol * np.abs(b)).all()), float(d.max()) if d.size else 0.0


# ------------------------------------------------------------------ checks
def c01(ctx):
    h = sha256(ctx.rgb_path)
    man = NB1A_RUN / "manifest.json"
    inp = NB1A_RUN / "input/input-manifest.json"
    pins = sha256(man) == NB1A_MANIFEST_SHA and sha256(inp) == NB1A_INPUT_MANIFEST_SHA
    rec = (json.loads(man.read_text())["files"].get("input/rgb-sensory.npz") == RGB_SHA
           and json.loads(inp.read_text())["files"]["rgb-sensory.npz"]["sha256"] == RGB_SHA)
    src = (ctx.source["rgb_source"]["sha256"] == RGB_SHA and ctx.source["rgb_source"]["path"] == str(RGB_PATH)
           and ctx.freeze["rgb_source"]["sha256"] == RGB_SHA)
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", NB1B_ACCEPTED, "HEAD"], cwd=REPO).returncode == 0
    ok = h == RGB_SHA and pins and rec and src and anc
    return ok, (f"RGB sha256 {h[:12]} (pin {RGB_SHA[:12]}); NB1a manifests verify {pins}; they record the pin {rec}; "
                f"source / freeze records {src}; NB1b acceptance ancestor {anc}")


def c02(ctx):
    ok = ctx.rgb_files == ["srgb8"] and ctx.srgb8.dtype == np.uint8 and ctx.source["rgb_source"]["arrays"] == ["srgb8"]
    return ok, f"arrays {ctx.rgb_files}, dtype {ctx.srgb8.dtype}"


def c03(ctx):
    shapes = {"input": ctx.srgb8.shape, "A": ctx.A.shape}
    shapes.update({k: v.shape for k, v in ctx.diag.items() if v.ndim >= 2 and not k.startswith("k_")})
    ok = ctx.srgb8.shape == (H, W, 3) and all(s[:2] == (H, W) for s in shapes.values()) and ctx.score_files == ["A"] \
        and ctx.diag["k_center"].shape == (H, H) and ctx.summ["resolution"] == {"width": W, "height": H, "cell_deg": 0.5} \
        and ctx.summ["candidate_directions"] == N
    return ok, f"shapes {sorted(set(map(str, shapes.values())))}; candidates {ctx.summ['candidate_directions']}"


def c04(ctx):
    bad = [p["command"] for p in ctx.processes if any("blender" in str(a).lower() for a in p["argv"])]
    files = sorted(p.name for p in RENDER_PATH.iterdir())
    same = files == ["blender.log", "canonical.exr", "render-metadata.json"] and all(
        sha256(RENDER_PATH / n) == h for n, h in RENDER_DIR.items())
    return not bad and same, f"Blender in process log: {bad}; Breadth-1 render directory unchanged: {same}"


def c05(ctx):
    bad = [p for p in ctx.processes if p["command"] not in COMMANDS
           or not any(str(a).endswith("nb1c_run.py") for a in p["argv"][:1])
           or any(re.search(r"controller0|classroom_oracle1_run|blender", str(a)) for a in p["argv"])]
    imp = []
    for f in sorted(n for n in NB1C_FILES if n.endswith(".py") and "natural_bootstrap" in n):
        imp += [f"{f}:{m}" for m in _imports((REPO / f).read_text()) if FORBIDDEN_IMPORTS.match(m)]
    return not bad and not imp, f"non-NB1c processes {[p['command'] for p in bad][:3]}; forbidden imports {imp}"


def _sel_hits(ctx, pattern: str) -> list[str]:
    return [p for p in _paths(ctx.sopen) if re.search(pattern, p)]


def c06(ctx):
    hit = _sel_hits(ctx, r"range-sensory|Position|\.exr|depth")
    return not hit, f"range / depth / Position opens during selection: {hit}"


def c07(ctx):
    hit = _sel_hits(ctx, r"hypothes|seeds|/discovery/|bootstrap-freeze")
    return not hit, f"NB1a hypothesis / seed opens during selection: {hit}"


def c08(ctx):
    hit = _sel_hits(ctx, r"natural-bootstrap-1b|serviceab|look-queue|environment-candidate")
    return not hit, f"NB1b opens during selection: {hit}"


def c09(ctx):
    rec = ctx.sopen
    root = _run_root(rec, ["source", "selection"])
    if root is None or root.name != ctx.run.name:
        return False, f"selection guard write directories {rec.get('allow_write_dirs')}"
    allowed = {str(ctx.rgb_path)}
    dreads = {e["path"] for e in rec["events"] if e.get("kind") == "data-read"}
    writes = {e["path"] for e in rec["events"] if e.get("kind") == "write"}
    forb = _sel_hits(ctx, r"reference-cells|instance_catalog|catalog|overlap|Object|/evaluation/|controller-0|breadth-1")
    ok_rec = (dreads == allowed and set(rec.get("allow_read", [])) == allowed and not forb and not rec["violations"]
              and rec.get("truth_firewall_violations") == 0 and all(e.get("allowed", True) for e in rec["events"])
              and all(p.startswith((str(root / "source") + "/", str(root / "selection") + "/")) for p in writes))
    bad_imp, bad_tok = [], []
    for f in ("nb1c_spec.py", "nb1c_attention.py"):
        src = (HERE / f).read_text()
        bad_imp += [f"{f}:{m}" for m in _imports(src) if m.split(".")[0] not in SELECTION_IMPORTS]
        bad_tok += [f"{f}:{t}" for t in FORBIDDEN_TOKENS if t in src]
    run_src = (HERE / "nb1c_run.py").read_text()
    tree = ast.parse(run_src)
    found = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in SELECTION_ROUTINES:
            found.add(node.name)
            seg = ast.get_source_segment(run_src, node)
            bad_tok += [f"nb1c_run.{node.name}:{t}" for t in FORBIDDEN_TOKENS if t in seg]
    sys.path.insert(0, str(HERE))
    from nb1a_guard import OpenGuard
    blocked = False
    with tempfile.TemporaryDirectory() as td:
        try:
            with OpenGuard("self-test", sorted(allowed), [td]):
                open(NB1A_RUN / "evaluation/reference-cells.npz", "rb").close()
        except PermissionError:
            blocked = True
    ok = ok_rec and not bad_imp and not bad_tok and found == set(SELECTION_ROUTINES) and blocked
    return ok, (f"data reads {sorted(Path(p).name for p in dreads)}; forbidden {forb[:2]}; violations {len(rec['violations'])}; "
                f"undeclared imports {bad_imp}; forbidden tokens {bad_tok[:4]}; routines {sorted(found)}; guard self-test "
                f"blocks Object Index {blocked}")


def c10(ctx):
    mine = lin_table()
    known = {0: 0.0, 10: 0.003035269835488375, 11: 0.003346535763899161, 128: 0.21586050011389926, 255: 1.0}
    stored = ctx.diag["lut"]
    ok = (stored.shape == (256,) and np.array_equal(stored, mine) and all(mine[k] == v for k, v in known.items())
          and ctx.summ["params_used"]["linear"] is True)
    return ok, f"stored table equals the Python-math formula bit-for-bit {np.array_equal(stored, mine)}; known values hold"


def c11(ctx):
    sys.path.insert(0, str(HERE))
    import nb1a_spec
    mine = directions()
    gen = nb1a_spec.cell_directions_h()
    d1 = float(np.abs(mine - gen).max())
    unit = float(np.abs(np.linalg.norm(mine, axis=-1) - 1).max())
    gid = hashlib.sha256(np.ascontiguousarray(gen, np.float64).tobytes()).hexdigest()
    ids = ctx.source["grid"]["directions_sha256"] == gid == ctx.freeze["grid"]["directions_sha256"]
    gd = max(float(np.abs(np.array(g["direction_h"]) - mine[g["row"], g["col"]]).max()) for g in ctx.gazes)
    return d1 <= 1e-15 and unit <= 1e-15 and ids and gd <= 1e-15, (f"max |own - NB1a convention| {d1:.2g}; unit {unit:.2g}; "
                                                                     f"grid identity {ids}; gaze directions {gd:.2g}")


def c12(ctx):
    w = weights()
    s = math.fsum(np.repeat(w, W).tolist()) - 4 * math.pi
    ok_w, dw = _close(ctx.diag["row_weights"], w, rtol=1e-15)
    ok = ok_w and abs(s) <= 1e-12 and ctx.summ["params_used"]["weighted"] is True
    return ok, f"stored row weights vs own max diff {dw:.2g}; sum - 4 pi = {s:.2g}"


def _cfgs(ctx):
    return [ctx.gz["config"], ctx.freeze["selection_config"], ctx.freeze["sensor_constants"], ctx.summ["constants"]]


def c13(ctx):
    val = None
    for node in ast.walk(ast.parse(ctx.sensor_path.read_text())):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CORE_FOV_DEG" for t in node.targets):
            val = ast.literal_eval(node.value)
    s = sha256(ctx.sensor_path)
    used = [ctx.summ["params_used"]["r_center"], ctx.gz["params_used"]["r_center"]]
    ok = (val == CORE_FOV and s == SENSOR_SHA and ctx.source["sensor"]["sha256"] == SENSOR_SHA
          and ctx.freeze["sensor_source"]["sha256"] == SENSOR_SHA
          and all(c["R_CENTER_RAD"] == R_C and c["R_CENTER_DEG"] == 6.0 and c["CORE_FOV_DEG"] == CORE_FOV for c in _cfgs(ctx))
          and all(u == R_C for u in used))
    return ok, f"CORE_FOV_DEG {val!r}, sha256 {s[:12]}; R_CENTER used {used} (6 deg = {R_C!r})"


def c14(ctx):
    used = [ctx.summ["params_used"]["r_surround"], ctx.gz["params_used"]["r_surround"]]
    ok = all(c["R_SURROUND_RAD"] == R_S and c["R_SURROUND_DEG"] == 12.0 for c in _cfgs(ctx)) and all(u == R_S for u in used)
    return ok, f"R_SURROUND used {used} (12 deg = {R_S!r})"


def c15(ctx):
    a = math.tan(math.radians(6.0))
    v = np.array([a, a, 1.0])
    corner = math.atan2(float(np.linalg.norm(np.cross(v, [0.0, 0.0, 1.0]))), float(v @ [0.0, 0.0, 1.0]))
    used = [ctx.summ["params_used"]["r_full"], ctx.gz["params_used"]["r_full"]]
    ok = (abs(corner - R_FULL) <= 1e-15 and all(c["R_FULL_RAD"] == R_FULL for c in _cfgs(ctx)) and all(u == R_FULL for u in used)
          and abs(R_FULL - math.radians(math.sqrt(2) * 6.0)) > 1e-4)
    return ok, f"R_FULL {math.degrees(R_FULL):.6f} deg; corner diff {abs(corner - R_FULL):.2g}; used {used}"


def c16(ctx):
    used = [ctx.summ["params_used"]["d_min"], ctx.gz["params_used"]["d_min"], ctx.rounds_doc["d_min_rad"]]
    ok = all(c["D_MIN_RAD"] == D_MIN for c in _cfgs(ctx)) and all(u == D_MIN for u in used) and D_MIN == 2 * R_FULL
    return ok, f"D_MIN {math.degrees(D_MIN):.6f} deg; used {used}"


def _membership(ctx, key: str, n_key: str, n_name: str):
    b = ctx.bf()
    stored = ctx.diag[key].astype(np.int64)
    same_k = stored.shape == b[key].shape and np.array_equal(stored, b[key])
    same_n = np.array_equal(ctx.diag[n_key].astype(np.int64), b[n_name])
    ok = same_k and same_n and b["bad_interval"] == 0 and b["bad_edge"] == 0 and int(ctx.diag["reference_column"]) == 0
    diff = int((stored != b[key]).sum()) if stored.shape == b[key].shape else -1
    return ok, (f"stored pattern equals the per-candidate brute-force membership of all {N:,} candidates {same_k} "
                f"({diff} (row, row) entries differ); counts {same_n}; non-uniform / non-interval {b['bad_interval']}; "
                f"box edge hits {b['bad_edge']}")


def c17(ctx):
    return _membership(ctx, "k_center", "n_C", "n_C")


def c18(ctx):
    ok, det = _membership(ctx, "k_disk", "n_S", "n_S")
    return ok, det.replace("pattern", "12-degree disk pattern (SURROUND = disk - CENTER)")


def c19(ctx):
    b = ctx.bf()
    r = [_close(ctx.diag["W_C"], b["W_C"], rtol=TOL["W_rel"]), _close(ctx.diag["W_S"], b["W_S"], rtol=TOL["W_rel"]),
         _close(ctx.diag["mu_C"], b["mu_C"], atol=TOL["mu"]), _close(ctx.diag["mu_S"], b["mu_S"], atol=TOL["mu"])]
    return all(x[0] for x in r), f"W_C, W_S, mu_C, mu_S max diff {[f'{x[1]:.2g}' for x in r]}"


def c20(ctx):
    b = ctx.bf()
    r = [_close(ctx.diag["V_C"], b["V_C"], atol=TOL["V"]), _close(ctx.diag["V_S"], b["V_S"], atol=TOL["V"])]
    return all(x[0] for x in r), f"V_C, V_S (two-pass) max diff {[f'{x[1]:.2g}' for x in r]}"


def c21(ctx):
    b = ctx.bf()
    okd, dd = _close(ctx.diag["D_RGB"], b["D_RGB"], atol=TOL["D"])
    formula = ctx.diag["D_RGB"] / np.sqrt(ctx.diag["V_C"] + ctx.diag["V_S"] + VAR_EPS)
    oka, da = _close(ctx.A, formula, rtol=1e-14)
    ok = okd and oka and ctx.summ["params_used"]["denominator"] is True
    return ok, f"D_RGB vs independent {dd:.2g}; stored A vs D / sqrt(V_C + V_S + 1e-12) of the stored terms {da:.2g}"


def c22(ctx):
    b = ctx.bf()
    ok, dmax = _close(ctx.A, b["A"], atol=TOL["A_abs"], rtol=TOL["A_rel"])
    fin = bool(np.isfinite(ctx.A).all())
    return ok and fin, f"entire raster vs independent: max |dA| {dmax:.2g} (tolerance 1e-6 + 1e-9 |A|); finite {fin}"


def c23(ctx):
    a = ctx.A.reshape(-1)
    d = directions().reshape(-1, 3)
    elig = np.ones(N, bool)
    thr = (2.0 * math.sin((D_MIN - EPS) / 2.0)) ** 2
    bad = []
    for g in ctx.gazes:
        e = np.flatnonzero(elig)
        amax = a[e].max()
        tie = e[(amax - a[e]) <= TIE * max(1.0, abs(amax))]
        idx = g["row"] * W + g["col"]
        if idx != int(tie[0]):
            bad.append(g["rank"])
        elig &= ~(((d - d[idx]) ** 2).sum(1) < thr)
    return not bad, f"rounds whose pick is not the smallest (row, col) of its tie set: {bad}"


def c24(ctx):
    picks, rounds = nms(ctx.A, directions())
    stored = [g["row"] * W + g["col"] for g in ctx.gazes]
    rr = ctx.rounds_doc["rounds"]
    same_rounds = len(rr) == len(rounds) and all(
        (s["index"], s["tie_set_size"], s["eligible_before"], s["newly_suppressed"], s["remaining"])
        == (m["index"], m["tie_set_size"], m["eligible_before"], m["newly_suppressed"], m["remaining"])
        and s["score"] == m["score"] for s, m in zip(rr, rounds))
    return picks == stored and same_rounds, f"own NMS on the stored raster {picks} vs stored {stored}; rounds equal {same_rounds}"


def c25(ctx):
    n = [len(ctx.gazes), ctx.gz["K"], ctx.summ["K"], len(ctx.rounds_doc["rounds"]), len(ctx.freeze["gazes"]),
         ctx.summ["params_used"]["K"]]
    ok = all(x == K for x in n) and [g["rank"] for g in ctx.gazes] == list(range(1, K + 1)) and all(
        c["K"] == K for c in (ctx.gz["config"], ctx.freeze["selection_config"]))
    return ok, f"gaze counts {n} (K = {K})"


def c26(ctx):
    d = directions()
    sel = np.array([d[g["row"], g["col"]] for g in ctx.gazes])
    mine = np.degrees(np.array([alpha_chord(x, sel) for x in sel]))
    stored = np.array(ctx.summ["pairwise_angular_distance_deg"])
    off = ~np.eye(len(sel), dtype=bool)
    ok_m = stored.shape == mine.shape and float(np.abs(stored - mine).max()) <= 1e-9
    ok_d = bool((np.radians(mine[off]) >= D_MIN - EPS).all()) and ctx.summ["all_pairs_at_least_D_MIN"] is True
    return ok_m and ok_d, (f"min pairwise {mine[off].min():.6f} deg vs D_MIN {math.degrees(D_MIN):.6f}; stored matrix "
                           f"recomputes {ok_m}")


def c27(ctx):
    b = ctx.bf()
    picks, rounds = nms(b["A"], directions())
    lat, lon = lat_lon()
    stored = [g["row"] * W + g["col"] for g in ctx.gazes]
    yp = all(abs(g["yaw_deg"] - math.degrees(lon[g["col"]])) <= 1e-12 and abs(g["pitch_deg"] - math.degrees(lat[g["row"]]))
             <= 1e-12 for g in ctx.gazes)
    tol = [TOL["A_abs"] + TOL["A_rel"] * abs(r["score"]) for r in rounds]
    amb = [r["round"] for r, t in zip(rounds, tol) if r["margin"] is not None and r["margin"] <= 2 * t]
    return picks == stored and yp and not amb, (f"own NMS on the independent raster {picks} vs stored {stored}; yaw / "
                                                f"pitch {yp}; rounds with a margin inside the agreement tolerance {amb}")


def c28(ctx):
    sel = ctx.run / "selection"
    hashes_ok = set(ctx.freeze["files"]) == set(FROZEN) and all(sha256(sel / n) == h for n, h in ctx.freeze["files"].items())
    code = {n: (HERE / n if n != "fsg_geometry.py" else ctx.sensor_path) for n in SELECTION_CODE}
    code_ok = set(ctx.freeze["selection_code"]) == set(SELECTION_CODE) and all(
        sha256(p) == ctx.freeze["selection_code"][n] for n, p in code.items())
    cfg_ok = ctx.freeze["selection_config_sha256"] == hashlib.sha256(
        json.dumps(ctx.freeze["selection_config"], sort_keys=True).encode()).hexdigest() \
        and ctx.freeze["selection_config"] == ctx.gz["config"]
    gz_ok = ctx.freeze["gazes"] == [{k: g[k] for k in ("rank", "row", "col")} for g in ctx.gazes]
    order = ctx.eopen.get("ordered_data_events", [])
    refs = {str(ctx.eval_path(n)) for n in EVAL_INPUTS}
    try:
        k = order.index("freeze_verified")
        ok_order = order.index("reference_access_begins") > k and not any(o in refs for o in order[:k])
    except ValueError:
        ok_order = False
    return hashes_ok and code_ok and cfg_ok and gz_ok and ok_order, (f"freeze hashes {hashes_ok}; selection code {code_ok}; "
                                                                     f"config {cfg_ok}; gazes {gz_ok}; verified before "
                                                                     f"any evaluation read {ok_order}")


def c29(ctx):
    root = _run_root(ctx.eopen, ["evaluation"])
    writes = {e["path"] for e in ctx.eopen["events"] if e.get("kind") == "write"}
    out = str(root / "evaluation") if root else "\0"
    ok = root is not None and root.name == ctx.run.name and bool(writes) and all(p.startswith(out + "/") for p in writes) \
        and not ctx.eopen["violations"]
    still = all(sha256(ctx.run / "selection" / n) == h for n, h in ctx.freeze["files"].items())
    rf = all(d.get("frozen_selection_sha256") == ctx.freeze["files"] and d.get("computed_after_freeze") is True
             for d in (ctx.ev, ctx.nb))
    same = [(e["rank"], e["row"], e["col"]) for e in ctx.ev["gazes"]] == [(g["rank"], g["row"], g["col"]) for g in ctx.gazes]
    return ok and still and rf and same, (f"evaluation writes only under evaluation/ {ok}; frozen outputs unchanged {still}; "
                                          f"recorded the frozen hashes {rf}; evaluated the frozen gazes {same}")


def c30(ctx):
    refs = {str(ctx.eval_path(n)) for n in EVAL_INPUTS}
    order = ctx.eopen.get("ordered_data_events", [])
    try:
        k = order.index("freeze_verified")
        ok = not any(o in refs for o in order[:k]) and refs <= set(order[k:])
    except ValueError:
        ok = False
    sel = [p for p in _paths(ctx.sopen) if p in refs]
    return ok and not sel, f"reference / range / NB1a / NB1b only after the freeze verification {ok}; in selection {sel[:2]}"


def _eval_data(ctx) -> dict:
    p = ctx.eval_path
    with np.load(p("nb1a/input/range-sensory.npz")) as z:
        rng, valid = np.asarray(z["range_m"]).reshape(-1), np.asarray(z["valid_mask"]).reshape(-1)
    with np.load(p("nb1a/discovery/hypothesis-raster.npz")) as z:
        lab = np.asarray(z["labels"]).reshape(-1).astype(np.int64)
    with np.load(p("nb1a/evaluation/reference-cells.npz")) as z:
        oid, o0 = np.asarray(z["object_index"]).reshape(-1), np.asarray(z["o0_mask"]).reshape(-1)
    ov = json.loads(p("nb1a/evaluation/overlap-summary.json").read_text())
    return {"range": rng, "valid": valid, "labels": lab, "oid": oid, "o0": o0,
            "names": {int(r["o"]): r["name"] for r in ov["per_reference_id"] if int(r["o"]) > 0},
            "hyps": {h["label"]: h["id"] for h in json.loads(p("nb1a/discovery/hypotheses.json").read_text())["hypotheses"]},
            "cls": {r["id"]: r["class"] for r in json.loads(p("nb1b/selection/serviceability.json").read_text())["hypotheses"]},
            "pq": json.loads(p("nb1b/selection/primary-look-queue.json").read_text())["queue"],
            "sq": json.loads(p("nb1b/selection/secondary-look-queue.json").read_text())["queue"]}


def c31(ctx):
    pins = all(sha256(ctx.eval_path(n)) == h for n, (_r, _p, h) in EVAL_INPUTS.items())
    e = _eval_data(ctx)
    d = directions().reshape(-1, 3)
    bad = []
    pts = {}
    for g, s in zip(ctx.gazes, ctx.ev["gazes"]):
        i = g["row"] * W + g["col"]
        a = alpha_chord(d[i], d)
        own = int(e["labels"][i])
        fp = {}
        for name, rad in (("center", R_C), ("full", R_FULL)):
            cells = np.flatnonzero(a <= rad + EPS)
            lab = e["labels"][cells]
            own_n = int((lab == own).sum()) if own > 0 else 0
            fp[name] = {"total_cells": int(cells.size), "own_cells": own_n, "invalid_cells": int((lab == 0).sum()),
                        "safe": own > 0 and own_n == cells.size}
        cls = ("GAZE_NO_RANGE" if own == 0 else "GAZE_FULL_SAFE" if fp["full"]["safe"] else
               "GAZE_CENTER_ONLY_SAFE" if fp["center"]["safe"] else "GAZE_UNSAFE")
        hid = e["hyps"].get(own)
        v = bool(e["valid"][i])
        ref = ("no geometry" if not v else "O_0" if e["o0"][i] else "authored")
        if (s["valid_range"] != v or (v and s["range_m"] != float(e["range"][i])) or s["nb1a_hypothesis"] != hid
                or s["nb1b_class"] != (e["cls"].get(hid) if hid else None) or s["gaze_class"] != cls
                or s["reference_at_gaze"]["kind"] != ref
                or any(s[n][k] != fp[n][k] for n in fp for k in fp[n])):
            bad.append(g["rank"])
        if v:
            pts[g["rank"]] = float(e["range"][i]) * d[i]
    agg = ctx.ev["aggregate"]
    hits = [s["nb1a_hypothesis"] for s in ctx.ev["gazes"] if s["nb1a_hypothesis"]]
    agg_ok = (agg["valid_range"] == len(pts) and agg["distinct_nb1a_hypotheses"] == len(set(hits))
              and agg["duplicate_gazes_into_same_hypothesis"] == len(hits) - len(set(hits))
              and agg["gaze_class_counts"] == {c: sum(s["gaze_class"] == c for s in ctx.ev["gazes"])
                                               for c in agg["gaze_class_counts"]})
    sep = ctx.ev["pairwise_3d_separation_m"]
    sep_ok = all((sep[a - 1][b - 1] is None) == (a not in pts or b not in pts) and (
        sep[a - 1][b - 1] is None or abs(sep[a - 1][b - 1] - float(np.linalg.norm(pts[a] - pts[b]))) <= 1e-12)
        for a in range(1, K + 1) for b in range(1, K + 1))
    a_flat = ctx.A.reshape(-1)
    seeds = [(f"P{q['rank']}", q) for q in e["pq"]] + [(f"S{q['rank']}", q) for q in e["sq"]]
    gd = np.array([d[g["row"] * W + g["col"]] for g in ctx.gazes])
    nb_ok = len(ctx.nb["seeds"]) == len(seeds)
    for (tag, q), s in zip(seeds, ctx.nb["seeds"]):
        i = q["seed"]["row"] * W + q["seed"]["col"]
        rank = int(np.count_nonzero(a_flat > a_flat[i]) + np.count_nonzero(a_flat[:i] == a_flat[i]) + 1)
        dd = np.degrees(alpha_chord(d[i], gd))
        k = int(np.argmin(dd))
        if (s["seed"], s["id"], s["A"], s["rank_in_full_raster"], s["nearest_gaze"]) != (tag, q["id"], float(a_flat[i]), rank,
                                                                                         k + 1) \
                or abs(s["nearest_gaze_deg"] - dd[k]) > 1e-9:
            nb_ok = False
    return pins and not bad and agg_ok and sep_ok and nb_ok, (f"pins {pins}; per-gaze mismatches {bad}; aggregate {agg_ok}; "
                                                              f"3-D separations {sep_ok}; NB1b comparison {nb_ok}")


def c32(ctx):
    bad_keys = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if EVAL_KEYS.search(str(k)):
                    bad_keys.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for v in x[:50]:
                walk(v, path)
    for name, doc in (("gazes", ctx.gz), ("rounds", ctx.rounds_doc), ("summary", ctx.summ)):
        walk(doc, name)
    diag_keys = [k for k in ctx.diag if EVAL_KEYS.search(k) and k != "reference_column"]
    ok27, _ = c27(ctx)
    return not bad_keys and not diag_keys and ok27, (f"evaluation-derived fields in selection products {bad_keys[:3]} "
                                                     f"{diag_keys}; frozen gazes equal the pure-RGB recomputation {ok27}")


def c33(ctx):
    sys.path.insert(0, str(HERE))
    import nb1c_visuals as V
    cur = {n: sha256(ctx.run / n) for n in V.Data.SOURCES}
    cur.update({str(p): sha256(p) for p in V.Data.EXTERNAL.values()})
    if cur != ctx.vman.get("sources"):
        return False, "figure sources changed since the figures were drawn"
    key = ("vis", tuple(sorted(cur.items())))
    if key not in _CACHE:
        figs, _d = V.render_all(ctx.run)
        _CACHE[key] = {n: hashlib.sha256(V.png_bytes(figs[n])).hexdigest() for n in FIGURES}
    want = _CACHE[key]
    bad = [n for n in FIGURES if not (ctx.vis / n).is_file() or sha256(ctx.vis / n) != want[n]
           or ctx.vman["products"][n]["sha256"] != want[n]]
    return not bad, f"{len(FIGURES) - len(bad)}/{len(FIGURES)} figures regenerate byte-identically; differ {bad}"


def _tree_ok(root: Path, files: dict) -> bool:
    return all(sha256(root / n) == h for n, h in files.items()) and sorted(
        str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()) == sorted(files)


def c34(ctx):
    ch = fov3d_changed(ctx)
    files = changed_files(ctx)
    ctrl = [f for f in files if f.startswith(("tools/controller/", "fov3d/")) or f in (
        "tools/classroom_oracle1_render.py", "tools/classroom_oracle1_run.py", "tools/fsg6f_frontier.py",
        "tools/fsg_geometry.py")]
    acc = [f for f in files if Path(f).name.startswith(("nb1a_", "nb1b_", "check_nb1a", "check_nb1b", "nb1a-", "nb1b-"))]
    trees = {"NB1a run": _tree_ok(ctx.nb1a_run, NB1A_RUN_FILES), "NB1b run": _tree_ok(ctx.nb1b_run, NB1B_RUN_FILES),
             "NB1a visuals": all(sha256(NB1A_VIS / n) == h for n, h in NB1A_VIS_FILES.items()),
             "NB1b visuals": _tree_ok(NB1B_VIS, NB1B_VIS_FILES)}
    ok = not ch and not ctrl and not acc and all(trees.values())
    return ok, f"fov3d changed {ch}; controller / sensor files {ctrl}; NB1a / NB1b files {acc}; unchanged {trees}"


def c35(ctx):
    extra = [f for f in changed_files(ctx) if f not in NB1C_FILES]
    return not extra, f"undeclared changes vs {BASE[:7]}: {extra[:6]}"


# ------------------------------------------------------------------ independent synthetic known answers (check 36)
def _blank(color) -> np.ndarray:
    img = np.empty((H, W, 3), np.uint8)
    img[:] = color
    return img


def _disk(img, row, col, deg, color, pattern=None):
    d = directions().reshape(-1, 3)
    m = (((d - d[row * W + col]) ** 2).sum(1) <= chord2(math.radians(deg))).reshape(H, W)
    if pattern is None:
        img[m] = color
    else:
        rr, cc = np.nonzero(m)
        par = (rr + cc) % 2 == 0
        img[rr[par], cc[par]] = pattern[0]
        img[rr[~par], cc[~par]] = pattern[1]
    return img


def own_synthetic() -> list[tuple[str, bool]]:
    if "own_synth" in _CACHE:
        return _CACHE["own_synth"]
    out = []
    d = directions().reshape(-1, 3)
    bg, red = (60, 90, 70), (200, 40, 40)
    u = _blank((77, 120, 200))
    out.append(("uniform: own A ~ 0 at poles, seam, equator",
                all(abs(brute_at(u, r, c)["A"]) <= 1e-6 for r, c in ((0, 0), (180, 719), (359, 360)))))
    coh = _disk(_blank(bg), 180, 360, 6.0, red)
    a0 = brute_at(coh, 180, 360)
    out.append(("coherent centre: A >= 1e5 at the centre, far below at neighbours",
                a0["A"] >= 1e5 and all(brute_at(coh, r, c)["A"] < 1e3 for r, c in ((180, 361), (179, 360), (181, 359)))))
    t = lin_table()
    c1, c2 = (240, 20, 60), (150, 60, 20)
    mix = tuple(int(np.argmin(np.abs(t - m))) for m in (t[list(c1)] + t[list(c2)]) / 2)
    a = brute_at(_disk(_blank(bg), 180, 360, 6.0, mix), 180, 360)
    b = brute_at(_disk(_blank(bg), 180, 360, 6.0, None, pattern=(c1, c2)), 180, 360)
    out.append(("heterogeneous centre: V_C up, A down, D within 5 %",
                b["C"]["V"] > a["C"]["V"] + 1e-3 and b["A"] < a["A"] and abs(b["D"] - a["D"]) <= 0.05 * a["D"]))
    rr, cc = np.mgrid[0:H, 0:W]
    chk = np.empty((H, W, 3), np.uint8)
    chk[(rr + cc) % 2 == 0] = (30, 120, 60)
    chk[(rr + cc) % 2 == 1] = (95, 60, 85)
    b = brute_at(_disk(chk, 180, 360, 6.0, red), 180, 360)
    out.append(("heterogeneous surround: V_S up, A down", b["S"]["V"] > a0["S"]["V"] + 1e-3 and b["A"] < a0["A"]))
    known = {0: 0.0, 10: 0.003035269835488375, 11: 0.003346535763899161, 128: 0.21586050011389926, 255: 1.0}
    out.append(("sRGB known values", all(t[k] == v for k, v in known.items())))
    img = _disk(_blank(bg), 150, 100, 6.0, (230, 30, 30))
    s1, s2 = brute_at(img, 150, 100), brute_at(np.roll(img, W - 100, axis=1), 150, 0)
    out.append(("seam: same score for the feature at column 100 and straddling the seam",
                abs(s1["A"] - s2["A"]) <= 1e-9 * abs(s1["A"]) and s1["C"]["n"] == s2["C"]["n"]))
    cap = brute_at(_blank(bg), 0, 77)
    rows = set((cap["C"]["cells"] // W).tolist())
    whole = all(np.count_nonzero(cap["C"]["cells"] // W == j) == W for j in range(12))
    out.append(("near pole: rows 0-11 wholly inside the CENTER of a row-0 candidate", whole and 11 in rows))
    img = _disk(_blank(bg), 60, 360, 6.0, (255, 0, 0))
    upper = img[:61].copy()
    img = _disk(img, 60, 360, 6.0, (0, 0, 255))
    img[:61] = upper
    wb = brute_at(img, 60, 360)
    raw = t[img].reshape(-1, 3)[wb["C"]["cells"]].mean(0)
    out.append(("weighting: weighted and raw centre means differ by > 1e-3", float(np.abs(wb["C"]["mu"] - raw).max()) > 1e-3))
    z = np.zeros((H, W))
    z[130, 400] = z[130, 20] = 7.0
    z[140, 0] = 7.0 - 1e-6
    p1 = nms(z, d)[0][0]
    z = np.zeros((H, W))
    z[120, 10], z[100, 600], z[90, 300] = 5.0, 5.0 - 4e-12, 5.0 - 6e-12
    p2 = nms(z, d)[0][0]
    out.append(("ties: smaller row, then column; outside the window excluded", p1 == 130 * W + 20 and p2 == 100 * W + 600))
    g0, q, p2i, p3 = 180 * W + 360, 155 * W + 383, 180 * W + 393, 180 * W + 300
    z = np.zeros(N)
    z[[g0, p2i, q, p3]] = [10.0, 9.5, 9.0, 8.0]
    picks = nms(z, d)[0]
    out.append(("NMS: inside D_MIN suppressed; beyond D_MIN and at 30 deg kept", picks[:3] == [g0, q, p3] and p2i not in picks))

    def rot(v, axis, ang):
        v, k = np.asarray(v, float), np.asarray(axis, float) / np.linalg.norm(axis)
        return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * (k @ v) * (1 - math.cos(ang))
    gv = np.array([0.0, 0.0, -1.0])
    cand = np.array([gv, rot(gv, [0, 1, 0], -(D_MIN - 1e-9)), rot(gv, [0, 1, 0], D_MIN), rot(gv, [1, 0, 0], D_MIN - 5e-13)]
                    + [rot(gv, [1, 0, 0], -math.radians(x)) for x in (60.0, 100.0, 140.0)])
    out.append(("D_MIN boundary: exactly D_MIN and within eps eligible; D_MIN - 1e-9 suppressed",
                nms(np.array([10, 9, 8, 7.5, 7, 6, 5.0]), cand)[0] == [0, 2, 3, 4, 5, 6]))
    try:
        nms(np.array([3.0, 2.0, 1.0]), np.eye(3))
        out.append(("budget: fewer than K directions raises", False))
    except RuntimeError:
        out.append(("budget: fewer than K directions raises", True))
    _CACHE["own_synth"] = out
    return out


def c36(ctx):
    gen = ctx.synthetic
    gen_ok = gen["passed"] and len(gen["cases"]) == 13 and all(c["ok"] for c in gen["cases"])
    own = own_synthetic()
    bad = [n for n, ok in own if not ok]
    return gen_ok and not bad, f"generator report {gen_ok} ({len(gen['cases'])} cases); independent failures {bad}"


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("accepted RGB source full hash", c01), ("input contains RGB only", c02), ("exact 720 x 360 resolution", c03),
    ("no Blender invocation", c04), ("no controller invocation", c05), ("selection opened no range / depth / Position", c06),
    ("selection opened no NB1a hypothesis / seed data", c07), ("selection opened no NB1b data", c08),
    ("selection opened no Object Index / catalog / reference (guard, imports, static audit)", c09),
    ("sRGB -> linear recomputes exactly", c10), ("spherical cell directions recompute", c11),
    ("solid-angle weights recompute and sum to 4 pi", c12), ("R_CENTER = 6 deg from the 12 deg sensor core", c13),
    ("R_SURROUND = 12 deg", c14), ("R_FULL = atan(sqrt(2) tan 6 deg), independently", c15), ("D_MIN = 2 R_FULL", c16),
    ("CENTER cell sets recompute for every candidate", c17), ("SURROUND cell sets recompute for every candidate", c18),
    ("weighted center / surround means recompute", c19), ("V_C / V_S recompute (two-pass)", c20),
    ("D_RGB and A recompute", c21), ("entire score raster matches", c22), ("score-tie rule obeyed", c23),
    ("greedy spherical NMS recomputes exactly", c24), ("exactly K = 6 gazes", c25),
    ("selected pair separations satisfy D_MIN", c26), ("selected rows / cols / directions / order match recomputation", c27),
    ("freeze verified before any evaluation read", c28), ("evaluation did not alter frozen products", c29),
    ("reference / range / NB1a / NB1b reads only after the freeze", c30), ("evaluation descriptors recompute", c31),
    ("no evaluation datum changes selection / order", c32), ("figures regenerate deterministically", c33),
    ("fov3d / controllers / sensor / NB1a / NB1b accepted files unchanged", c34),
    ("changed files are declared NB1c files only", c35), ("synthetic known answers (generator and independent)", c36)],
    start=1)]


def run_checks(ctx, quiet=False) -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(ctx)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}" + ("" if ok else f" -- {detail}"))
    return res


# ------------------------------------------------------------------ corruption suite
def mirror(run: Path, vis: Path, tmp: Path) -> tuple[Path, Path]:
    def copy_tree(src, dst):
        for p in src.rglob("*"):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            elif p.suffix in (".json", ".jsonl", ".csv"):
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
    z = dict(np.load(path))
    fn(z)
    path.unlink()
    np.savez_compressed(path, **z)


def refreeze(m: Path, names=None) -> None:
    def fn(d):
        for n in (names or d["files"]):
            d["files"][n] = sha256(m / "selection" / n)
    edit_json(m / "selection/rgb-gaze-freeze.json", fn)


def regenerate(m: Path, ctx, **variant):
    """Rebuild the mirror's selection products (and synthetic report) with a deliberately wrong variant."""
    sys.path.insert(0, str(HERE))
    import nb1c_attention as AT
    import nb1c_run as R
    res = AT.run(ctx.srgb8, **variant)
    sel = m / "selection"
    for n in ("attention-score.npz", "attention-diagnostics.npz", "candidate-gazes.json", "nms-rounds.json",
              "selection-summary.json"):
        (sel / n).unlink()
    R.write_selection(sel, res)
    R.write_json(sel / "selection-summary.json", AT.summary(res))
    gz = [{k: g[k] for k in ("rank", "row", "col")} for g in AT.gaze_records(res)]
    edit_json(sel / "rgb-gaze-freeze.json", lambda d: d.update(gazes=gz))
    results = R._jsonable(R.synthetic_results(**variant))
    edit_json(m / "synthetic/synthetic-report.json", lambda d: d.update(cases=results, passed=all(x["ok"] for x in results)))
    refreeze(m)


def corruptions():
    def diag(m, fn):
        edit_npz(m / "selection/attention-diagnostics.npz", fn)
        refreeze(m, ["attention-diagnostics.npz"])

    def gazes(m, fn):
        edit_json(m / "selection/candidate-gazes.json", lambda d: fn(d["gazes"]))
        refreeze(m, ["candidate-gazes.json"])

    def first_valid_cell(c):
        g = c.gazes[0]
        return g["row"], g["col"]

    def membership(m, v, c, key):
        def fn(z):
            k = z[key].copy()
            j0 = 180
            j = int(np.flatnonzero(k[j0] >= 0)[0])
            k[j0, j] += 1
            z[key] = k
        diag(m, fn)

    def bump(m, v, c, key, delta):
        r, col = first_valid_cell(c)

        def fn(z):
            a = z[key].copy()
            if a.ndim == 3:
                a[r, col, 0] += delta
            else:
                a[r, col] += delta
            z[key] = a
        diag(m, fn)

    def alter_score(m, v, c):
        r, col = first_valid_cell(c)
        edit_npz(m / "selection/attention-score.npz", lambda z: z["A"].__setitem__((r, col), z["A"][r, col] * 1.001))
        refreeze(m, ["attention-score.npz"])

    def tie_break(m, v, c):
        g = c.gazes[0]
        idx = g["row"] * W + g["col"]
        a = c.A.reshape(-1)
        cand = [i for i in range(idx) if a[i] < a[idx]]
        if not cand:
            return {"not_applicable": "no cell before the first gaze"}
        t = cand[0]

        def fn(z):
            arr = z["A"].reshape(-1).copy()
            arr[t] = arr[idx]
            z["A"] = arr.reshape(H, W)
        edit_npz(m / "selection/attention-score.npz", fn)
        refreeze(m, ["attention-score.npz"])
        return {"note": f"cell {divmod(t, W)} tied with gaze 1"}

    def move(m, v, c):
        def fn(gs):
            gs[1]["col"] = (gs[1]["col"] + 1) % W
        gazes(m, fn)

    def reorder(m, v, c):
        def fn(gs):
            gs[0], gs[1] = gs[1], gs[0]
            gs[0]["rank"], gs[1]["rank"] = 1, 2
        gazes(m, fn)

    def too_close(m, v, c):
        def fn(gs):
            gs[2]["row"], gs[2]["col"] = gs[0]["row"], (gs[0]["col"] + 10) % W
        gazes(m, fn)

    def sel_open(path):
        def fn(m, v, c):
            edit_json(m / "selection/selection-opened-files.json", lambda d: d["events"].append(
                {"event": "open", "path": str(path), "kind": "data-read", "allowed": True}))
            refreeze(m, ["selection-opened-files.json"])
        return fn

    def eval_modifies(m, v, c):
        edit_json(m / "selection/candidate-gazes.json", lambda d: d["gazes"][3].update(row=d["gazes"][3]["row"] + 1))

    def eval_before(m, v, c):
        ref = str(NB1A_RUN / "input/range-sensory.npz")

        def fn(d):
            o = [x for x in d["ordered_data_events"] if x != ref]
            o.insert(0, ref)
            d["ordered_data_events"] = o
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

    def proc(cmd, argv):
        def fn(m, v, c):
            with open(m / "process-log.jsonl", "a") as f:
                f.write(json.dumps({"command": cmd, "argv": argv, "status": "ok"}) + "\n")
        return fn

    def pixel(m, v, c):
        from PIL import Image
        p = v / "overview.png"
        img = Image.open(p.resolve()).convert("RGB")
        img.putpixel((3, 3), (255, 0, 0))
        p.unlink()
        img.save(p)

    def nb1b_product(m, v, c):
        nb = m / "nb1b" / NB1B_RUN.name
        for p in NB1B_RUN.rglob("*"):
            q = nb / p.relative_to(NB1B_RUN)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            else:
                q.parent.mkdir(parents=True, exist_ok=True)
                q.symlink_to(p.resolve())
        q = nb / "selection/selection-summary.json"
        txt = q.read_text()
        q.unlink()
        q.write_text(txt + "\n")
        return {"nb1b_run": nb}

    def eval_value(m, v, c):
        k = next((i for i, e in enumerate(c.ev["gazes"]) if e["valid_range"]), None)
        if k is None:
            return {"not_applicable": "no gaze with valid range"}
        edit_json(m / "evaluation/candidate-evaluation.json", lambda d: d["gazes"][k].update(range_m=d["gazes"][k]["range_m"] + 0.01))

    def synth(m, v, c):
        edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))

    def reg(**variant):
        return lambda m, v, c: regenerate(m, c, **variant)

    return [
        ("K altered from 6 (regenerated, K = 7)", ("25",), reg(k_budget=7)),
        ("R_CENTER altered (regenerated, 5.5 deg)", ("13", "17"), reg(r_center=math.radians(5.5))),
        ("R_SURROUND altered (regenerated, 13 deg)", ("14", "18"), reg(r_surround=math.radians(13.0))),
        ("R_FULL formula altered (regenerated, sqrt(2) * 6 deg)", ("15", "16"), reg(r_full=math.radians(math.sqrt(2) * 6.0))),
        ("D_MIN altered (regenerated, 15 deg)", ("16",), reg(d_min=math.radians(15.0))),
        ("gamma-space sRGB used directly (regenerated)", ("10", "19"), reg(linear=False)),
        ("solid-angle weights omitted (regenerated)", ("12", "19"), reg(weighted=False)),
        ("equirectangular pixel distance (regenerated)", ("17", "18"), reg(metric="pixel")),
        ("one CENTER membership changed", ("17",), lambda m, v, c: membership(m, v, c, "k_center")),
        ("one SURROUND membership changed", ("18",), lambda m, v, c: membership(m, v, c, "k_disk")),
        ("one center mean altered", ("19",), lambda m, v, c: bump(m, v, c, "mu_C", 1e-6)),
        ("one variance altered", ("20",), lambda m, v, c: bump(m, v, c, "V_C", 1e-6)),
        ("variance denominator removed (regenerated)", ("21", "22"), reg(denominator=False)),
        ("one attention score altered", ("21", "22"), alter_score),
        ("score tie-break violated", ("23",), tie_break),
        ("one selected gaze moved", ("24", "27"), move),
        ("two selected gazes reordered", ("24", "27"), reorder),
        ("two selected gazes closer than D_MIN", ("26",), too_close),
        ("longitude seam behaviour broken (regenerated)", ("17", "18"), reg(seam_wrap=False)),
        ("selection opened range-sensory.npz", ("06",), sel_open(NB1A_RUN / "input/range-sensory.npz")),
        ("selection opened NB1a hypothesis data", ("07",), sel_open(NB1A_RUN / "discovery/hypothesis-raster.npz")),
        ("selection opened NB1b serviceability", ("08",), sel_open(NB1B_RUN / "selection/serviceability.json")),
        ("selection opened Object Index / catalog", ("09",), sel_open(NB1A_RUN / "evaluation/reference-cells.npz")),
        ("evaluation modified a gaze", ("29",), eval_modifies),
        ("evaluation read range before the freeze verification", ("28", "30"), eval_before),
        ("Blender command in the process log", ("04",), proc("select", ["blender", "-b", "x.blend"])),
        ("controller command in the process log", ("05",), proc("controller02", ["fov3d/experiments/classroom_oracle/controller02.py"])),
        ("a visual pixel altered", ("33",), pixel),
        ("fov3d modified", ("34",), lambda m, v, c: {"fov3d_changed": True}),
        ("controller code modified", ("34",), lambda m, v, c: {"changed_files": changed_files(c) + ["tools/controller/check_controller02.py"]}),
        ("NB1a code modified", ("34",), lambda m, v, c: {"changed_files": changed_files(c) + ["tools/natural_bootstrap/nb1a_discovery.py"]}),
        ("NB1b code modified", ("34",), lambda m, v, c: {"changed_files": changed_files(c) + ["tools/natural_bootstrap/nb1b_serviceability.py"]}),
        ("an accepted NB1b run product altered", ("34",), nb1b_product),
        ("an evaluation descriptor altered", ("31",), eval_value),
        ("a synthetic known-answer case failed", ("36",), synth),
        ("tie-break reversed (regenerated)", ("36",), reg(tie_break=False)),
    ]


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    for name, targets, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="nb1c-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            with contextlib.redirect_stdout(io.StringIO()):
                overrides = fn(m, v, Ctx(m, v)) or {}
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A {list(targets)} {name}: {overrides['not_applicable']}")
                results.append({"name": name, "targets": list(targets), "not_applicable": overrides["not_applicable"]})
                continue
            total += 1
            note = overrides.pop("note", "")
            ctx = Ctx(m, v)
            for k, val in overrides.items():
                setattr(ctx, k, val)
            with contextlib.redirect_stdout(io.StringIO()):
                res = run_checks(ctx, quiet=True)
            failed = sorted(r["check"] for r in res if not r["ok"])
            hit = any(t in failed for t in targets)
            caught += hit
            results.append({"name": name, "targets": list(targets), "caught": hit, "failed": failed, "note": note})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} {list(targets)} {name}"
                  + (f" ({note})" if note else "") + f" (failed: {failed})")
    return caught, total, results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    res = run_checks(Ctx(run, vis))
    npass = sum(r["ok"] for r in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} NATURAL_BOOTSTRAP1C_CHECKS_PASS")
    out = {"schema": "NB1c-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip(),
           "tolerances": TOL}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} NATURAL_BOOTSTRAP1C_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
