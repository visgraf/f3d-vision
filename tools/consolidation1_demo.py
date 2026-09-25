"""Post-hoc migration-baseline demo for a completed Classroom-Oracle-1 run.

Observational only.  It reads saved run artifacts after ``control_complete`` and
never feeds anything back into fixation selection.  It is not part of the golden
runtime closure; it imports only modules that are.

Outputs under RUN/demo/:
  Demo.md, demo_manifest.json, overview.png, last_frame.png
  frames/frame_XXXX.png        one synchronized four-view frame per look
  panoramas/instance_reference.png, coverage_reference.png, rgb_observed.png
  pointclouds/instance_XXXX.ply, scene_final.ply, scene_final_instances.ply
  classroom-oracle-1-demo.mp4  when OpenCV has an MP4 writer

Four panels per frame:
  1. post-hoc dense instance reference, target highlighted, gaze trail;
  2. current saved left + right tangent observation;
  3. Cyclopean evidence for the current object, replayed from the saved pair;
  4. accumulating metric reconstruction (all fused surfels so far).

Check that can fail: the demo recomputes coverage from final maps and the dense
reference with the evaluator's own rule and exits 1 unless it equals
evaluation.json exactly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import classroom_oracle1_epistemic as epistemic
import classroom_oracle1_eval as evaluation
import classroom_oracle1_matcher as oracle_matcher
import classroom_oracle1_public as public

PW, PH = 640, 340          # panel size
FOOT = 40                  # footer height; frame is 1280 x 720
REF_STEP = 0.25            # dense reference grid, degrees


def _json(p: Path) -> Any:
    return json.loads(p.read_text())


def _iid_bgr(iid: int, v: int = 235) -> tuple[int, int, int]:
    hsv = np.array([[[np.uint8((int(iid) * 47) % 180), 200, v]]], np.uint8)
    b, g, r = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
    return int(b), int(g), int(r)


def _put(img, text, xy=(10, 22), scale=0.55, color=(255, 255, 255)):
    cv2.putText(img, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def _fit(img: np.ndarray, title: str) -> np.ndarray:
    out = np.full((PH, PW, 3), 24, np.uint8)
    h, w = img.shape[:2]
    s = min((PW - 8) / w, (PH - 34) / h)
    im = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_NEAREST if s >= 1 else cv2.INTER_AREA)
    y0 = 30 + (PH - 30 - im.shape[0]) // 2
    x0 = (PW - im.shape[1]) // 2
    out[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    _put(out, title)
    return out


class Domain:
    def __init__(self, step: float):
        import fsg6f_public as frozen
        c = frozen.SURFACE_FRONTIER
        self.y0, self.y1 = float(c["yaw_min_deg"]), float(c["yaw_max_deg"])
        self.p0, self.p1 = float(c["pitch_min_deg"]), float(c["pitch_max_deg"])
        self.step = step
        self.w = int(round((self.y1 - self.y0) / step)) + 1
        self.h = int(round((self.p1 - self.p0) / step)) + 1

    def px(self, yaw, pitch):
        x = np.rint((np.asarray(yaw, float) - self.y0) / self.step).astype(int)
        y = np.rint((self.p1 - np.asarray(pitch, float)) / self.step).astype(int)  # pitch up = top
        return x, y


def _instance_reference(ids, angles, dom: Domain) -> np.ndarray:
    img = np.zeros((dom.h, dom.w, 3), np.uint8)
    x, y = dom.px(angles[:, 0], angles[:, 1])
    ok = (x >= 0) & (x < dom.w) & (y >= 0) & (y < dom.h)
    lut = {int(i): _iid_bgr(int(i), 150) for i in np.unique(ids)}
    col = np.array([lut[int(i)] for i in ids], np.uint8)
    img[y[ok], x[ok]] = col[ok]
    return img


def _reference_panel(base, ids, angles, dom, target, trail, gaze, name) -> np.ndarray:
    img = (base.astype(np.float32) * 0.45).astype(np.uint8)
    m = ids == target
    x, y = dom.px(angles[m, 0], angles[m, 1])
    img[y, x] = _iid_bgr(target, 255)
    s = 3
    img = cv2.resize(img, (dom.w * s, dom.h * s), interpolation=cv2.INTER_NEAREST)
    pts = [tuple(int(v * s + s // 2) for v in dom.px(g[0], g[1])) for g in trail]
    for a, b in zip(pts, pts[1:]):
        cv2.line(img, a, b, (255, 255, 255), 1, cv2.LINE_AA)
    for p in pts[:-1]:
        cv2.circle(img, p, 3, (200, 200, 200), -1)
    if pts:
        cv2.drawMarker(img, pts[-1], (0, 255, 255), cv2.MARKER_CROSS, 18, 2)
    return _fit(img, f"1 reference (post-hoc)  target {target} {name}  gaze ({gaze[0]:.2f},{gaze[1]:.2f})")


def _stereo_panel(odir: Path, step: int, src: str) -> np.ndarray:
    L = cv2.imread(str(odir / "benchmark" / f"fix_{step:02d}_L.png"))
    R = cv2.imread(str(odir / "benchmark" / f"fix_{step:02d}_R.png"))
    gap = np.full((L.shape[0], 6, 3), 24, np.uint8)
    return _fit(np.concatenate((L, gap, R), axis=1), f"2 current left | right tangent pair   look via {src}")


def _cyclopean_panel(ev, map_xyz, trail, target) -> np.ndarray:
    support, _, _ = epistemic._map_support(ev, map_xyz)
    img = np.full(ev.shape + (3,), 30, np.uint8)          # NEVER_OBSERVED: dark
    img[ev.seen_nontarget] = (110, 110, 110)               # non-target seen: gray
    img[ev.seen_target & ~ev.target_depth_valid] = (0, 140, 255)  # target, no depth: orange
    img[ev.target_depth_valid] = (60, 200, 60)             # target with depth: green
    edge = support & ~cv2.erode(support.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    img[edge] = (255, 255, 255)                            # metric-map support outline
    img = np.ascontiguousarray(img[::-1])                  # pitch up = top
    h, w = ev.shape
    for g in trail:
        x = int(round((g[0] - ev.yaw_min_deg) / ev.grid_deg)); y = h - 1 - int(round((g[1] - ev.pitch_min_deg) / ev.grid_deg))
        cv2.circle(img, (x, y), 4, (0, 255, 255), 1)
    return _fit(img, f"3 Cyclopean {target}: green depth, orange no-depth, gray other")


class CloudView:
    """Fixed oblique orthographic view of the head-frame cloud."""

    def __init__(self, all_xyz: np.ndarray):
        yaw, pitch = np.radians(35.0), np.radians(-28.0)
        ry = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
        rx = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
        self.R = rx @ ry
        q = all_xyz @ self.R.T
        self.lo = np.percentile(q[:, :2], 0.5, axis=0)
        self.hi = np.percentile(q[:, :2], 99.5, axis=0)
        self.W, self.H = 600, 300

    def render(self, xyz: np.ndarray, bgr: np.ndarray) -> np.ndarray:
        img = np.full((self.H, self.W, 3), 12, np.uint8)
        if len(xyz):
            q = xyz @ self.R.T
            s = min((self.W - 1) / (self.hi[0] - self.lo[0]), (self.H - 1) / (self.hi[1] - self.lo[1]))
            u = ((q[:, 0] - self.lo[0]) * s).astype(int)
            v = (self.H - 1 - (q[:, 1] - self.lo[1]) * s).astype(int)
            ok = (u >= 0) & (u < self.W) & (v >= 0) & (v < self.H)
            order = np.argsort(q[ok, 2])                     # far first, near last (camera looks down -z)
            img[v[ok][order], u[ok][order]] = bgr[ok][order]
        return img


def _write_ply(path: Path, xyz: np.ndarray, rgb_u8: np.ndarray) -> None:
    n = len(xyz)
    dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")])
    a = np.empty(n, dt)
    a["x"], a["y"], a["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    a["red"], a["green"], a["blue"] = rgb_u8[:, 0], rgb_u8[:, 1], rgb_u8[:, 2]
    head = ("ply\nformat binary_little_endian 1.0\ncomment head frame H, metres\n"
            f"element vertex {n}\nproperty float x\nproperty float y\nproperty float z\n"
            "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
    with path.open("wb") as f:
        f.write(head.encode()); f.write(a.tobytes())


def _load_map(p: Path) -> tuple[np.ndarray, np.ndarray]:
    if not p.exists():
        return np.empty((0, 3), np.float32), np.empty((0, 3), np.float32)
    with np.load(p, allow_pickle=False) as z:
        x = np.asarray(z["xyz_h"], np.float32)
        c = np.asarray(z["rgb"], np.float32) if "rgb" in z.files else np.full_like(x, 0.5)
    ok = np.isfinite(x).all(axis=1)
    return x[ok], c[ok]


def _srgb_u8(rgb_lin: np.ndarray) -> np.ndarray:
    return np.rint(np.power(np.clip(rgb_lin, 0, 1), 1 / 2.2) * 255).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    run = args.run.resolve()
    manifest = _json(run / "manifest.json")
    if not manifest.get("control_complete"):
        raise SystemExit("refusing: control run is not complete")
    ev_doc = _json(run / "evaluation.json")
    demo = run / "demo"
    if demo.exists():
        if not args.overwrite:
            raise SystemExit(f"{demo} exists; pass --overwrite")
        shutil.rmtree(demo)
    for d in ("frames", "panoramas", "pointclouds"):
        (demo / d).mkdir(parents=True)

    with np.load(run / "bootstrap/evaluation_only/reachable_samples.npz", allow_pickle=False) as z:
        t_ids = np.asarray(z["instance_id"], np.int32)
        t_xyz = np.asarray(z["xyz_h"], np.float64)
        t_ang = np.asarray(z["yaw_pitch_deg"], np.float64)
    dom = Domain(REF_STEP)
    base = _instance_reference(t_ids, t_ang, dom)
    cv2.imwrite(str(demo / "panoramas/instance_reference.png"), cv2.resize(base, (dom.w * 4, dom.h * 4), interpolation=cv2.INTER_NEAREST))

    # Check: coverage recomputed with the evaluator's rule must equal evaluation.json.
    radius = float(public.FUSION["association_radius_m"])
    covered = np.zeros(len(t_ids), bool)
    finals: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for o in manifest["objects"]:
        iid = int(o["instance_id"])
        finals[iid] = _load_map(run / "objects" / f"instance_{iid:04d}" / "final_map.npz")
        m = t_ids == iid
        covered[m] = evaluation._covered(t_xyz[m], finals[iid][0].astype(np.float64), radius)
    cov_n, ref_n = int(covered.sum()), int(len(t_ids))
    check_ok = (cov_n == ev_doc["covered_samples_total"] and ref_n == ev_doc["reachable_samples_total"]
                and cov_n / ref_n == ev_doc["coverage_fraction_micro"])
    print(f"[consolidation1-demo] {'PASS' if check_ok else 'FAIL'} coverage recompute "
          f"{cov_n}/{ref_n} vs evaluation.json {ev_doc['covered_samples_total']}/{ev_doc['reachable_samples_total']}")

    cov_img = np.zeros((dom.h, dom.w, 3), np.uint8)
    x, y = dom.px(t_ang[:, 0], t_ang[:, 1])
    cov_img[y[covered], x[covered]] = (80, 190, 80)
    cov_img[y[~covered], x[~covered]] = (40, 40, 230)
    cov_img = cv2.resize(cov_img, (dom.w * 4, dom.h * 4), interpolation=cv2.INTER_NEAREST)
    _put(cov_img, f"covered {cov_n}/{ref_n} = {cov_n / ref_n:.6f}  (green covered, red uncovered, black no reachable sample)", (10, 24), 0.6)
    cv2.imwrite(str(demo / "panoramas/coverage_reference.png"), cov_img)

    # Point clouds.
    all_xyz = np.concatenate([v[0] for v in finals.values() if len(v[0])])
    all_rgb = np.concatenate([_srgb_u8(v[1]) for v in finals.values() if len(v[0])])
    all_lab = np.concatenate([np.full(len(v[0]), k, np.int32) for k, v in finals.items() if len(v[0])])
    for iid, (xyz, rgb) in finals.items():
        if len(xyz):
            _write_ply(demo / "pointclouds" / f"instance_{iid:04d}.ply", xyz, _srgb_u8(rgb))
    _write_ply(demo / "pointclouds/scene_final.ply", all_xyz, all_rgb)
    inst_rgb = np.array([_iid_bgr(int(i))[::-1] for i in all_lab], np.uint8)
    _write_ply(demo / "pointclouds/scene_final_instances.ply", all_xyz, inst_rgb)
    view = CloudView(all_xyz.astype(np.float64))

    # Observed-RGB panorama: saved left-eye tangent colour at each fused surfel direction.
    rgb_pan = np.zeros((dom.h, dom.w, 3), np.uint8)
    yaw, pitch = epistemic.angular_coordinates(all_xyz)
    px, py = dom.px(yaw, pitch)
    ok = (px >= 0) & (px < dom.w) & (py >= 0) & (py < dom.h)
    rgb_pan[py[ok], px[ok]] = all_rgb[ok][:, ::-1]
    cv2.imwrite(str(demo / "panoramas/rgb_observed.png"), cv2.resize(rgb_pan, (dom.w * 4, dom.h * 4), interpolation=cv2.INTER_NEAREST))

    # Sequential frames.
    rng = np.random.default_rng(0)
    done_xyz: list[np.ndarray] = []
    done_bgr: list[np.ndarray] = []
    frames: list[Path] = []
    total = sum(int(o["fixation_count"]) for o in manifest["objects"])
    k = 0
    for oi, o in enumerate(manifest["objects"]):
        iid = int(o["instance_id"]); name = str(o["object_name"])
        odir = run / "objects" / f"instance_{iid:04d}"
        ev = epistemic.make_evidence()
        trail: list[list[float]] = []
        for row in o["trajectory"]:
            s = int(row["step"])
            adir = odir / "acquisitions" / f"fix_{s:02d}"
            c = _json(adir / "calibration.json")
            with np.load(adir / "oracle_observation.npz", allow_pickle=False) as z:
                obs = {kk: z[kk] for kk in z.files}
            rec, _meta, state = oracle_matcher.compute(c, obs)
            epistemic.add_observation(ev, c, state["ids_left"], state["raw_support_L"],
                                      state["ids_right"], state["raw_support_R"], rec["valid"], iid)
            trail.append(row["gaze_deg"])
            cur_xyz, _ = _load_map(odir / "maps" / f"fix_{s:02d}.npz")
            p1 = _reference_panel(base, t_ids, t_ang, dom, iid, trail, row["gaze_deg"], name)
            p2 = _stereo_panel(odir, s, row["action_source"])
            p3 = _cyclopean_panel(ev, cur_xyz, trail, iid)
            cx = np.concatenate(done_xyz + [cur_xyz]) if (done_xyz or len(cur_xyz)) else np.empty((0, 3))
            cb = np.concatenate(done_bgr + [np.tile(np.array([[0, 255, 255]], np.uint8), (len(cur_xyz), 1))]) if len(cx) else np.empty((0, 3), np.uint8)
            n_surf = len(cx)
            if len(cx) > 400_000:
                sel = rng.choice(len(cx), 400_000, replace=False); cx, cb = cx[sel], cb[sel]
            p4 = _fit(view.render(cx, cb), f"4 reconstruction: {n_surf:,} surfels (current object yellow)")
            top = np.concatenate((p1, p2), axis=1); bot = np.concatenate((p3, p4), axis=1)
            foot = np.full((FOOT, 2 * PW, 3), 0, np.uint8)
            _put(foot, f"Classroom-Oracle-1 migration baseline | look {k + 1}/{total} | object {oi + 1}/{len(manifest['objects'])} "
                       f"step {s} | new surfels {row['new_surfels']} | map {row['map_size_after']}", (10, 26), 0.6)
            frame = np.concatenate((top, bot, foot), axis=0)
            fp = demo / "frames" / f"frame_{k:04d}.png"
            cv2.imwrite(str(fp), frame); frames.append(fp); k += 1
        fx, fc = finals[iid]
        done_xyz.append(fx.astype(np.float64)); done_bgr.append(np.tile(np.array([_iid_bgr(iid)], np.uint8), (len(fx), 1)))
        print(f"[consolidation1-demo] object {iid} {name}: {len(o['trajectory'])} frames", flush=True)

    shutil.copy(frames[-1], demo / "last_frame.png")
    final_cloud = _fit(view.render(all_xyz.astype(np.float64), inst_rgb[:, ::-1]), f"final scene cloud, {len(all_xyz):,} surfels, by instance")
    ov_top = np.concatenate((_fit(cv2.imread(str(demo / 'panoramas/coverage_reference.png')), "post-hoc reference comparison"),
                             final_cloud), axis=1)
    ov_bot = np.concatenate((_fit(cv2.imread(str(demo / 'panoramas/rgb_observed.png')), "observed RGB at fused surfels"),
                             _fit(cv2.imread(str(demo / 'panoramas/instance_reference.png')), "dense instance reference (evaluation only)")), axis=1)
    cv2.imwrite(str(demo / "overview.png"), np.concatenate((ov_top, ov_bot), axis=0))

    video = demo / "classroom-oracle-1-demo.mp4"
    wr = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (2 * PW, 2 * PH + FOOT))
    video_ok = wr.isOpened()
    if video_ok:
        for fp in frames:
            wr.write(cv2.imread(str(fp)))
        for _ in range(int(args.fps * 3)):
            wr.write(cv2.resize(cv2.imread(str(demo / "overview.png")), (2 * PW, 2 * PH + FOOT)))
    wr.release()

    src_hist: dict[str, int] = {}
    for o in manifest["objects"]:
        for r in o["trajectory"]:
            src_hist[r["action_source"]] = src_hist.get(r["action_source"], 0) + 1
    rel = run.relative_to(Path.cwd()) if run.is_relative_to(Path.cwd()) else run
    summary = {
        "frames": len(frames), "objects": len(manifest["objects"]), "fixations": total,
        "action_sources": src_hist, "termination_counts": manifest["termination_counts"],
        "reachable": ref_n, "covered": cov_n, "coverage": cov_n / ref_n,
        "coverage_check_matches_evaluation": check_ok, "video": str(video.name) if video_ok else None,
        "scene_surfels": int(len(all_xyz)),
    }
    (demo / "demo_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (demo / "Demo.md").write_text(f"""# Classroom-Oracle-1 migration-baseline demo

Observational, post-hoc. Generated from the completed run `{rel}` after `control_complete: true`.
Nothing here feeds back into fixation selection. The dense reference is evaluation-only truth.

## Result shown

- objects {summary['objects']}, fixations {total}, action sources {src_hist}
- terminations {manifest['termination_counts']}
- reachable {ref_n}, covered {cov_n}, coverage {cov_n / ref_n!r}
- coverage recomputed here equals evaluation.json: **{check_ok}**

## Frames (one per look, in run order)

1. dense instance reference over the +/-25 yaw, +/-20 pitch controller domain (post-hoc), target highlighted, gaze trail, current gaze crosshair;
2. the saved left | right tangent pair of this look and whether its gaze came from `oracle_seed`, `fsg6f` or `cyclopean_epistemic`;
3. the Cyclopean evidence of the current object replayed from the saved pair with the unchanged epistemic module (green target with depth, orange target without depth, gray other instance, dark never observed; white outline the map support; yellow circles the gazes);
4. the accumulating reconstruction: all completed objects by instance colour, the current object's map in yellow.

## Files

- `frames/frame_XXXX.png`, `last_frame.png`, `overview.png`
- `panoramas/coverage_reference.png` (post-hoc reference comparison), `rgb_observed.png`, `instance_reference.png`
- `pointclouds/instance_XXXX.ply`, `scene_final.ply` (observed colour), `scene_final_instances.ply`
- `{video.name}` {'(mp4v)' if video_ok else '(not written: no MP4 writer)'}

## Reproduce

```bash
.venv/bin/python tools/classroom_oracle1_run.py --repo . --out {rel} --profile full --device OPTIX
.venv/bin/python tools/classroom_oracle1_eval.py --run {rel}
.venv/bin/python tools/consolidation1_demo.py --run {rel}
```
""")
    print("[consolidation1-demo] COMPLETE", json.dumps(summary, sort_keys=True))
    return 0 if check_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
