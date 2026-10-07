"""Figures for the technical report "Active Foveal 3-D Vision" (presentation only).

    .venv/bin/python docs/technical-report/make_figures.py [--shared /home/lvelho/rd/f3d-vision]

Reads the official Engineering-1 run (``previews/greedy-foveal-official-baseline/``), the accepted frozen demo products
(``visuals/greedy-foveal-explorer-v0-demo/`` and the demo's eye cache) and writes report figures to ``figures/``.
It renders no scene, runs no experiment and never opens the Breadth-1 reference EXR: the reference panoramas and the
3-D map view are the frozen demo's own images.  The run's freeze is verified before any run product is read, and
``figures/figure-sources.json`` records the sha256 of every input and output.  Diagrams (Figures 1 and 7) and the
growth curve (Figure 5, from the CSVs written here) are drawn by LaTeX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (REPO / "tools" / "greedy_foveal", REPO / "tools" / "visual_language", REPO / "tools"):
    sys.path.insert(0, str(_p))

import demo as DM  # noqa: E402  (accepted demo helpers, read-only)
import explorer as X  # noqa: E402
import fsg_geometry as FG  # noqa: E402
import style as S  # noqa: E402  (Visual Language 1)
import visuals as VS  # noqa: E402

OUT = HERE / "figures"
FIX = 179                                    # the demo poster's fixation (chosen there for legibility)
STAGES = (50, 200, 450, 542)
DEMO_FINAL_SHA256 = "9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65"   # closure record
MAP3D_BOX = (1241, 253, 1879, 1011)          # the "FINAL 3-D RECONSTRUCTION" panel inside demo-final.png
C_NEW = S.OI_GREEN                           # VL1: new spatial support
C_MATCH = S.OI_ORANGE


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Sources:
    def __init__(self) -> None:
        self.inputs: dict[str, str] = {}
        self.outputs: dict[str, str] = {}

    def read(self, path: Path) -> Path:
        self.inputs[str(path)] = sha256(path)
        return path

    def save(self, img: Image.Image, name: str, **kw) -> None:
        p = OUT / name
        img.save(p, **kw)
        self.outputs[name] = sha256(p)
        print(f"[report-figures] {name} {img.size}", flush=True)

    def text(self, name: str, text: str) -> None:
        p = OUT / name
        p.write_text(text)
        self.outputs[name] = sha256(p)
        print(f"[report-figures] {name}", flush=True)


def verify_freeze(run: Path) -> dict:
    fz = json.loads((run / "freeze.json").read_text())
    for f, h in fz["files"].items():
        if f in ("trajectory.json", "coverage.npz") and sha256(run / f) != h:
            raise SystemExit(f"STOP {run / f} differs from the run's freeze")
    return fz


def upscale(a: np.ndarray, k: int) -> Image.Image:
    return Image.fromarray(np.asarray(a, np.uint8)).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


# ------------------------------------------------------------------ Figure 2: one fixation
def figure2(src: Sources, run: Path, cache: Path, T: list[dict]) -> dict:
    fd = run / f"fixations/fix-{FIX:04d}"
    cal = json.loads(src.read(fd / "calibration.json").read_text())
    with np.load(src.read(fd / "points.npz")) as z:
        xyz, rgb = z["xyz_h"].astype(np.float64), np.array(z["rgb"])
    with np.load(src.read(cache / f"eyes/fix-{FIX:04d}.npz")) as z:
        left, right = np.array(z["left"]), np.array(z["right"])
    k, gap = 2, 56
    n = X.CORE_SIZE
    # (a) the binocular foveal pair with a sparse set of corresponding pixels (reprojected triangulated points)
    uv_l, _ = FG.project_h(cal["eyes"][0], xyz)
    uv_r, _ = FG.project_h(cal["eyes"][1], xyz)
    cl = np.rint(uv_l).astype(np.int64) - X.CORE_ORIGIN
    cr = uv_r - X.CORE_ORIGIN
    pair = Image.new("RGB", (2 * n * k + gap, n * k), (255, 255, 255))
    pair.paste(upscale(left, k), (0, 0))
    pair.paste(upscale(right, k), (n * k + gap, 0))
    d = ImageDraw.Draw(pair)
    index = {(int(r), int(c)): i for i, (c, r) in enumerate(cl)}
    picks = []                                     # one match per row (rows are shared by corresponding points)
    for j, r in enumerate(range(16, n, 32)):
        for c in [16 + 64 * ((j + m) % 4) + 32 * (j % 2) for m in range(4)]:
            i = index.get((r, min(c, n - 8)))
            if i is not None and 0 <= cr[i, 0] < n and 0 <= cr[i, 1] < n:
                picks.append(i)
                break
    for i in picks:
        x0, y0 = (cl[i, 0] + 0.5) * k, (cl[i, 1] + 0.5) * k
        x1, y1 = (cr[i, 0] + 0.5) * k + n * k + gap, (cr[i, 1] + 0.5) * k
        d.line([x0, y0, x1, y1], fill=(255, 255, 255), width=4)
        d.line([x0, y0, x1, y1], fill=C_MATCH, width=2)
    for i in picks:
        for x, y in (((cl[i, 0] + 0.5) * k, (cl[i, 1] + 0.5) * k),
                     ((cr[i, 0] + 0.5) * k + n * k + gap, (cr[i, 1] + 0.5) * k)):
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=C_MATCH, outline=(255, 255, 255), width=2)
    src.save(pair, "fig2-pair.png", optimize=True)
    # (b) metric depth on the left foveal grid (range from the left eye)
    src.save(upscale(DM.depth_patch(cal, xyz), k), "fig2-depth.png", optimize=True)
    # (c) the local metric patch in 3-D, seen obliquely, with the head and the gaze ray
    w, h = 900, 700
    gaze = X.direction(*cal["gaze_yaw_pitch_deg"])
    centre = np.median(xyz, axis=0)
    away = -gaze[[0, 2]] / np.linalg.norm(gaze[[0, 2]])
    azim = math.degrees(math.atan2(away[0], away[1])) + 48.0
    head_w = np.zeros((max(1, len(xyz) // 40), 3))                 # weight the head into the fitted view
    cam = DM.Camera.fitted(np.vstack([xyz, head_w]), w, h, azim, 28.0, 7.5, margin=0.07, target=centre * 0.55)
    img = DM.render_points(xyz, VS.display_rgb(rgb), cam, w, h, bg=(255, 255, 255))
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    hx, hy, _ = cam.project(np.zeros(3))
    reach = float(np.quantile(np.linalg.norm(xyz, axis=1), 0.9))
    fr = X.frame(*cal["gaze_yaw_pitch_deg"])
    t6 = math.tan(math.radians(X.CORE_FOV_DEG / 2))
    for a_, b_ in ((1, 1), (1, -1), (-1, 1), (-1, -1)):             # the nominal 12-degree core as a frustum
        cdir = fr[:, 2] + t6 * (a_ * fr[:, 0] + b_ * fr[:, 1])
        cx_, cy_, _ = cam.project(cdir / np.linalg.norm(cdir) * reach)
        dr.line([float(hx), float(hy), float(cx_), float(cy_)], fill=S.FAINT, width=2)
    tip = gaze * reach
    tx, ty, _ = cam.project(tip)
    VS.dashed_polyline(dr, [(float(hx), float(hy)), (float(tx), float(ty))], S.INK2, width=3, dash=12.0, gap=8.0)
    S.crosshair(dr, float(hx), float(hy), r=16)
    ink = np.asarray(im).min(axis=2) < 250                          # crop the white margin (keep a small pad)
    ys_, xs_ = np.nonzero(ink)
    pad = 18
    im = im.crop((max(0, xs_.min() - pad), max(0, ys_.min() - pad), min(w, xs_.max() + pad), min(h, ys_.max() + pad)))
    src.save(im, "fig2-patch3d.png", optimize=True)
    # (d) the cyclopean coverage after this fixation; the cells this fixation added in green
    with np.load(src.read(run / f"policy/state-{FIX:04d}.npz")) as z:
        after = np.array(z["state"])
    with np.load(src.read(run / f"policy/state-{FIX - 1:04d}.npz")) as z:
        before = np.array(z["state"])
    cw, chh = 1440, 720
    cov = DM.state_image(after, cw, chh)
    new = after != before
    rr, cc = (np.arange(chh) * X.H) // chh, (np.arange(cw) * X.W) // cw
    cov[new[rr][:, cc]] = C_NEW
    ci = Image.fromarray(cov)
    dc = ImageDraw.Draw(ci)
    fr = X.frame(*cal["gaze_yaw_pitch_deg"])
    t6 = math.tan(math.radians(X.CORE_FOV_DEG / 2))
    edge = np.linspace(-1.0, 1.0, 25)
    loop = np.concatenate([np.stack([edge, -np.ones_like(edge)], 1), np.stack([np.ones_like(edge), edge], 1),
                           np.stack([edge[::-1], np.ones_like(edge)], 1), np.stack([-np.ones_like(edge), edge[::-1]], 1)])
    dirs = fr[:, 2][None] + t6 * (loop[:, :1] * fr[:, 0][None] + loop[:, 1:] * fr[:, 1][None])
    fy, fp = X.yaw_pitch(dirs)
    fx, fyy = VS.to_xy(fy, fp, (0, 0, cw, chh))
    outline = [(float(a_), float(b_)) for a_, b_ in zip(fx, fyy)]
    dc.line(outline + outline[:1], fill=(255, 255, 255), width=7)
    dc.line(outline + outline[:1], fill=S.INK, width=3)
    src.save(ci, "fig2-coverage.png", optimize=True)
    e = T[FIX - 1]
    return {"fixation": FIX, "gaze_deg": cal["gaze_yaw_pitch_deg"], "points": int(len(xyz)),
            "match_lines": len(picks), "fusion_matched": e["fusion"]["matched"], "fusion_new": e["fusion"]["new"],
            "map_after": e["fusion"]["map_after"], "new_cells": int(new.sum()), "kind": e["kind"]}


# ------------------------------------------------------------------ Figure 3: coverage at four stages
def figure3(src: Sources, run: Path, sh: np.ndarray, dh: np.ndarray, n_fix: int) -> dict:
    out = {}
    for k in STAGES:
        if k == n_fix:
            with np.load(src.read(run / "coverage.npz")) as z:
                st = np.array(z["state"])
        else:
            with np.load(src.read(run / f"policy/state-{k:04d}.npz")) as z:
                st = np.array(z["state"])
        src.save(Image.fromarray(DM.state_image(st, 1080, 540)), f"fig3-coverage-{k:04d}.png", optimize=True)
        out[k] = {"seen_pct": round(100 * float(sh[k - 1]), 2), "depth_pct": round(100 * float(dh[k - 1]), 2)}
    return out


# ------------------------------------------------------------------ Figure 4: the whole gaze trajectory
def figure4(src: Sources, demo: Path, T: list[dict]) -> dict:
    """(a) the local walks with the landing point of every global jump; (b) the global jumps alone."""
    w, h = 2000, 1000
    base = Image.open(src.read(demo / "final-rgb-panorama.png")).convert("RGB").resize((w, h), Image.BILINEAR)
    base = Image.blend(base, Image.new("RGB", (w, h), (255, 255, 255)), 0.62)
    box = (0, 0, w, h)
    dirs = X.direction(np.array([e["yaw_deg"] for e in T]), np.array([e["pitch_deg"] for e in T]))
    xs, ys = VS.to_xy([e["yaw_deg"] for e in T], [e["pitch_deg"] for e in T], box)
    for panel in ("local", "global"):
        img = base.copy()
        d = ImageDraw.Draw(img)
        for yaw in range(-180, 181, 45):
            x, _ = VS.to_xy(yaw, 0, box)
            d.line([x, 0, x, h], fill=S.FAINT, width=1)
        for pitch in range(-90, 91, 30):
            _, y = VS.to_xy(0, pitch, box)
            d.line([0, y, w, y], fill=S.FAINT, width=1)
        for k in range(1, len(T)):
            if T[k]["kind"] == panel:
                VS.draw_path(d, box, VS.arc(dirs[k - 1], dirs[k]), S.OI_BLUE if panel == "local" else S.OI_VERM,
                             panel == "global", width=4 if panel == "local" else 3)
        for k, e in enumerate(T):
            if panel == "local":
                col, r = (S.OI_VERM, 7) if e["kind"] == "global" else (S.OI_BLUE, 5)
            else:
                col, r = (S.OI_VERM, 6) if e["kind"] == "global" else (S.MUTED, 3)
            d.ellipse([xs[k] - r - 2, ys[k] - r - 2, xs[k] + r + 2, ys[k] + r + 2], fill=(255, 255, 255))
            d.ellipse([xs[k] - r, ys[k] - r, xs[k] + r, ys[k] + r], fill=col)
        S.crosshair(d, float(xs[0]), float(ys[0]), r=20)
        S.square(d, float(xs[-1]), float(ys[-1]), r=10, color=S.INK)
        src.save(img, f"fig4-{panel}.jpg", quality=88, optimize=True)
    return {"start_deg": [T[0]["yaw_deg"], T[0]["pitch_deg"]], "end_deg": [T[-1]["yaw_deg"], T[-1]["pitch_deg"]]}


# ------------------------------------------------------------------ Figure 5 data: SEEN / DEPTH growth
def figure5(src: Sources, sh: np.ndarray, dh: np.ndarray, T: list[dict]) -> None:
    rows = ["fixation,seen,depth"] + [f"{i + 1},{100 * s:.4f},{100 * dd:.4f}" for i, (s, dd) in enumerate(zip(sh, dh))]
    src.text("fig5-growth.csv", "\n".join(rows) + "\n")
    glob = ["fixation"] + [str(e["n"]) for e in T if e["kind"] == "global"]
    src.text("fig5-global.csv", "\n".join(glob) + "\n")


# ------------------------------------------------------------------ Figure 6: final reconstruction and reference
def figure6(src: Sources, run: Path, demo: Path) -> None:
    for kind in ("final", "reference"):
        for what in ("rgb", "depth", "instance"):
            im = Image.open(src.read(demo / f"{kind}-{what}-panorama.png")).convert("RGB")
            if im.size != (1440, 720):
                im = im.resize((1440, 720), Image.NEAREST if what != "rgb" else Image.BICUBIC)
            if what == "rgb":
                src.save(im, f"fig6-{kind}-{what}.jpg", quality=90, optimize=True)
            else:
                src.save(im, f"fig6-{kind}-{what}.png", optimize=True)
    final = demo / "demo-final.png"
    if sha256(final) != DEMO_FINAL_SHA256:
        raise SystemExit("STOP demo-final.png is not the frozen demo still")
    src.read(final)
    src.save(Image.open(final).convert("RGB").crop(MAP3D_BOX), "fig6-map3d.jpg", quality=92, optimize=True)
    with np.load(src.read(run / "evaluation.npz")) as z:
        rc, covered = z["cells_rc"], z["covered"]
    st = np.zeros((360, 720), np.int8)
    st[rc[:, 0], rc[:, 1]] = np.where(covered, 2, 1)
    rgb = np.empty((360, 720, 3), np.uint8)
    rgb[st == 0], rgb[st == 1], rgb[st == 2] = (255, 255, 255), S.INK, (178, 214, 196)   # no hit / missed / covered
    src.save(upscale(rgb, 2), "fig6-evaluation.png", optimize=True)


# ------------------------------------------------------------------ numbers quoted in the text (DERIVED from the run)
def text_facts(src: Sources, run: Path, T: list[dict], sh: np.ndarray) -> dict:
    kinds = [e["kind"] for e in T]
    pts = np.array([e["correspondence"]["valid"] for e in T])
    fu = np.array([e["seconds"]["fusion"] for e in T])
    with np.load(src.read(run / "coverage.npz")) as z:
        st = np.array(z["state"])
    _, sizes = X.unseen_components(st)
    ev = json.loads(src.read(run / "evaluation.json").read_text())
    gain = np.diff(sh[449:])
    phases = {f"{a}-{b}": {"local": kinds[a - 1:b].count("local"), "global": kinds[a - 1:b].count("global")}
              for a, b in ((1, 200), (201, 450), (451, len(T)))}
    return {"points_per_fixation": {"median": float(np.median(pts)), "min": int(pts.min()), "max": int(pts.max())},
            "fusion_seconds": {"max": round(float(fu.max()), 2), "max_at": int(fu.argmax() + 1),
                               "mean_first_100": round(float(fu[:100].mean()), 2),
                               "mean_last_92": round(float(fu[-92:].mean()), 2)},
            "render_seconds_mean": round(float(np.mean([e["seconds"]["render"] for e in T])), 2),
            "first_global": kinds.index("global") + 1, "seen_pct_before_first_global": round(100 * float(sh[kinds.index("global") - 1]), 2),
            "phases": phases, "tail_seen_gain_pct": {"mean": round(100 * float(gain.mean()), 4),
                                                     "min": round(100 * float(gain.min()), 4)},
            "unseen_holes": {"count": len(sizes), "max_sr": round(float(max(sizes)), 5)},
            "seen_without_depth_pct": round(100 * float(X.CELL_W[st == X.SEEN].sum() / X.SPHERE_SR), 3),
            "reference_no_hit_cells": ev["reference"]["no_hit_cells"],
            "final_map_npz_bytes": (run / "final-map.npz").stat().st_size}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shared", default="/home/lvelho/rd/f3d-vision")
    a = ap.parse_args()
    shared = Path(a.shared)
    run = shared / "previews/greedy-foveal-official-baseline"
    demo = shared / "visuals/greedy-foveal-explorer-v0-demo"
    cache = shared / "previews/greedy-foveal-explorer-v0-demo-cache"
    OUT.mkdir(exist_ok=True)
    src = Sources()
    fz = verify_freeze(run)
    traj = json.loads(src.read(run / "trajectory.json").read_text())
    T = traj["trajectory"]
    with np.load(src.read(run / "coverage.npz")) as z:
        sh, dh = np.array(z["seen_history"]), np.array(z["depth_history"])
    facts = {"run": str(run), "run_freeze_sha256": sha256(run / "freeze.json"), "run_code": fz["code"],
             "fig2": figure2(src, run, cache, T), "fig3": figure3(src, run, sh, dh, len(T)),
             "fig4": figure4(src, demo, T)}
    facts["text"] = text_facts(src, run, T, sh)
    figure5(src, sh, dh, T)
    figure6(src, run, demo)
    (OUT / "figure-sources.json").write_text(json.dumps({"schema": "active-foveal-report-figures", "facts": facts,
                                                         "inputs": src.inputs, "outputs": src.outputs},
                                                        indent=1, sort_keys=True) + "\n")
    print(f"[report-figures] wrote {len(src.outputs)} files; facts {json.dumps(facts['fig2'])}", flush=True)


if __name__ == "__main__":
    main()
