"""Visual Language 1: controller-time sources, the truth boundary and the derived cache.

Contract: docs/methodology/visual-language-1-contract.md (sections 2-4).  The extraction
replays the causal state of the accepted Controller-01 run step by step from its saved
per-step artifacts, through accepted ``fov3d`` functions only (no controller rerun), and
compares every quantity that has a controller-time record exactly with that record.  Any
mismatch raises ``ExtractionMismatch``: the extraction stops and nothing is forced.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from fov3d.control import frontier, integrated as ic, object_policy  # noqa: E402
from fov3d.epistemic.head_memory import HeadEvidence, add_head_patch  # noqa: E402
from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic, matcher  # noqa: E402
from fov3d.geometry.head_chart import chart_grid  # noqa: E402
from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry  # noqa: E402

CYC = epistemic._legacy_impl  # sealed Cyclopean helpers, read-only (as in the accepted Controller-01 visual)
PREVIEWS = Path("/home/lvelho/rd/f3d-vision/previews")
VISUALS = Path("/home/lvelho/rd/f3d-vision/visuals")
GRID_DEG = c01.GRID_DEG
C01_ACCEPTED = {"manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
                "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd"}
C02_ACCEPTED = {"actions.json": "7fb86aba9bfdc6da0a67828be233b72893cec31b6c02609c5b883b1a1b66f047",
                "events.json": "fae7e64880f82602c8a868d0598bafab2c6d8da8e0c3f4465440c213d848327c",
                "final-residue.json": "a315714f0452621425fe8463e03d1b1c8e4b70d8ec9778e122ad518f90032c00",
                "manifest.json": "ad49e835c2efbbead7732b97dc140733bb5d947ef1808ff86325e85c5da4014f",
                "result.json": "a6dc4879f70216f99d098841f9d2c33dda0ceb71f01a4ab76320b0d08212dc55"}
C02_MARKER = "CONTROLLER02_CLASSROOM_SCENE_CLOSED"
# The accepted, report-recorded event numbers; recomputed and compared, never assumed.
EXPECTED = {
    "catalog": 234, "localized": 25, "unlocated": 209, "actions": 141,
    109: {"quiet": 4, "react": 7, "trigger": 110, "added": 4, "eff": (6166, 6170), "elig": (0, 28), "served": 134},
    178: {"quiet": 67, "react": 114, "trigger": 224, "added": 36748, "eff": (215125, 251873), "elig": (0, 189),
          "served": 136, "by_source": {"201": 8506, "224": 28242}},
    210: {"deferred_step": 101, "looks": 24, "state": "ACTIONABLE", "reason": "ordinary_budget"},
    "gate": {"object": 210, "gaze": (7.6, 18.2), "source": "fsg6f", "support": 30, "in_both_cores": 0,
             "previously_interrogated": 30, "novel_service_count": 0, "admissible": False,
             "reason": "no_novel_serviceable_support"},
    "closure": {"type": "SCENE_CLOSED", "quiet": 24, "residual": [[210, "ACTIONABLE", "final_probe_rejected"]],
                "unlocated": 209, "final_residue_observations": 0},
}
# Panel-1 chart: the controller domain at a fixed scale (stable, head-centred).
CHART_PPD = 12.5
EARLIER_AUDITS = ("controller-01a-terminal-audit", "controller-01b-single-continuation",
                  "controller-01c-frontier-action-correspondence")
REFERENCE_DIRS = ("reference-render", "reference")


class ExtractionMismatch(RuntimeError):
    """A derived quantity differs from its controller-time record: stop, do not force."""


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def is_reference_path(path: str) -> bool:
    """This step's reference / evaluation products (never a controller-time input)."""
    p = Path(path)
    parts = p.parts
    for i, part in enumerate(parts[:-1]):
        if part == "visual-language-1-classroom" and parts[i + 1] in REFERENCE_DIRS:
            return True
        if part == "visual-language-1" and parts[i + 1] == "reference":
            return True
    return p.name == "reachable_samples.npz"


def forbidden_controller_time(path: str) -> bool:
    """The controller-time firewall predicate: evaluation truth, reference products, earlier audits."""
    if c01.is_evaluation_truth(path) or is_reference_path(path):
        return True
    parts = Path(path).parts
    return any(a == "previews" and b in EARLIER_AUDITS for a, b in zip(parts, parts[1:]))


def firewall() -> ic.TruthFirewall:
    return ic.TruthFirewall(PREVIEWS, forbidden_controller_time)


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def angles(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(xyz, np.float64).reshape(-1, 3)
    return np.degrees(np.arctan2(p[:, 0], -p[:, 2])), np.degrees(np.arctan2(p[:, 1], np.hypot(p[:, 0], p[:, 2])))


def gamma_u8(rgb_linear: np.ndarray) -> np.ndarray:
    return np.rint(np.power(np.clip(np.asarray(rgb_linear, np.float64), 0, 1), 1 / 2.2) * 255).astype(np.uint8)


def jsonable(x: Any) -> Any:
    return c01._jsonable(x)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(data), indent=1, sort_keys=True) + "\n")


def fingerprint(root: Path) -> dict[str, str]:
    """Per-file sha256 of a source tree (for the byte-identity check)."""
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            p = Path(dirpath) / f
            out[str(p.relative_to(root))] = sha(p)
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- sources

class Sources:
    """The two accepted controller-time sources (read under the controller-time firewall)."""

    def __init__(self, source: Path, replay: Path):
        self.source, self.replay = Path(source).resolve(), Path(replay).resolve()
        s, r = self.source, self.replay
        self.manifest = json.loads((s / "manifest.json").read_text())
        doc = json.loads((s / "actions.json").read_text())
        self.actions, self.events01 = doc["actions"], doc["events"]
        self.catalog = {int(o["instance_id"]): o["object_name"]
                        for o in json.loads((s / "bootstrap/instance_catalog.json").read_text())["instances"]}
        self.seeds_doc = json.loads((s / "bootstrap/seeds.json").read_text())
        self.seeds = {int(x["instance_id"]): tuple(map(float, x["seed_gaze_deg"])) for x in self.seeds_doc["instances"]}
        self.domain = dict(self.seeds_doc["controller_domain_deg"])
        self.c02_actions = json.loads((r / "actions.json").read_text())["actions"]
        self.c02_events = json.loads((r / "events.json").read_text())["events"]
        self.c02_residue = json.loads((r / "final-residue.json").read_text())["residue_decisions"]
        self.c02_result = json.loads((r / "result.json").read_text())
        self.c02_manifest = json.loads((r / "manifest.json").read_text())
        self._results: dict[int, dict] = {}

    def names(self, i: int) -> str:
        return self.catalog[int(i)]

    def result(self, i: int) -> dict:
        if i not in self._results:
            self._results[i] = json.loads((self.source / f"objects/instance_{i:04d}/result.json").read_text())
        return self._results[i]

    def probe_after(self, i: int, step: int) -> dict:
        rows = [p for p in self.result(i)["probes"] if int(p["after_global_step"]) == int(step)]
        if len(rows) != 1:
            raise ExtractionMismatch(f"probe record of {i} after step {step}: {len(rows)} rows")
        return rows[0]

    def obj_dir(self, i: int) -> Path:
        return self.source / f"objects/instance_{int(i):04d}"

    def acquisition(self, i: int, k: int) -> tuple[dict, dict]:
        adir = self.obj_dir(i) / f"acquisitions/fix_{k:02d}"
        return json.loads((adir / "calibration.json").read_text()), load_npz(adir / "oracle_observation.npz")

    def patch(self, i: int, k: int) -> dict:
        return load_npz(self.obj_dir(i) / f"patches/fix_{k:02d}.npz")

    def map_file(self, i: int, k: int) -> Path:
        return self.obj_dir(i) / f"maps/fix_{k:02d}.npz"

    def benchmark(self, i: int, k: int) -> tuple[np.ndarray, np.ndarray]:
        b = self.obj_dir(i) / "benchmark"
        return (cv2.imread(str(b / f"fix_{k:02d}_L.png"))[..., ::-1].copy(),
                cv2.imread(str(b / f"fix_{k:02d}_R.png"))[..., ::-1].copy())

    def saved_view(self, i: int, stem: str) -> dict | None:
        p = self.obj_dir(i) / f"epistemic/{stem}.npz"
        return load_npz(p) if p.exists() else None


def verify_sources(src: Sources) -> list[dict]:
    """Identity of both sources, and Controller-02 actions equal to Controller-01 actions."""
    rows = []

    def rec(name, ok, detail=""):
        rows.append({"check": name, "ok": bool(ok), "detail": str(detail)})
        if not ok:
            raise ExtractionMismatch(f"{name}: {detail}")
    for n, d in C01_ACCEPTED.items():
        rec(f"Controller-01 {n} is the accepted artifact", sha(src.source / n) == d, sha(src.source / n))
    for n, d in C02_ACCEPTED.items():
        rec(f"Controller-02 {n} is the accepted artifact", sha(src.replay / n) == d, sha(src.replay / n))
    rec("Controller-02 marker CONTROLLER02_CLASSROOM_SCENE_CLOSED; source hashes are Controller-01's",
        src.c02_result.get("marker") == C02_MARKER and src.c02_manifest.get("source_hashes") == C01_ACCEPTED)
    same = len(src.actions) == len(src.c02_actions) == EXPECTED["actions"] and all(
        a["global_step"] == b["global_step"] == n and a["target_id"] == b["target_id"]
        and a["action_source"] == b["action_source"] and a["gaze_deg"] == b["gaze_deg"]
        and a["object_local_step"] == b["object_local_step"]
        for n, (a, b) in enumerate(zip(src.actions, src.c02_actions)))
    rec("141 Controller-02 actions equal the Controller-01 actions (step, target, local step, source, gaze)", same)
    return rows


# ---------------------------------------------------------------- the chart raster (panel 1)

class ChartRaster:
    """Incremental nearest-surface raster of the measurement memory in the head chart."""

    def __init__(self, domain: dict, ppd: float = CHART_PPD):
        self.y0, self.y1 = map(float, domain["yaw"])
        self.p0, self.p1 = map(float, domain["pitch"])
        self.ppd = float(ppd)
        self.w, self.h = int(round((self.y1 - self.y0) * ppd)), int(round((self.p1 - self.p0) * ppd))
        self.rng = np.full(self.h * self.w, np.inf, np.float32)
        self.rgb = np.zeros((self.h * self.w, 3), np.uint8)
        self.inst = np.zeros(self.h * self.w, np.int32)

    def px(self, yaw, pitch):
        return (np.asarray(yaw, float) - self.y0) * self.ppd, (self.p1 - np.asarray(pitch, float)) * self.ppd

    def add(self, xyz: np.ndarray, rgb: np.ndarray, inst: np.ndarray) -> None:
        if not len(xyz):
            return
        yaw, pit = angles(xyz)
        x, y = self.px(yaw, pit)
        xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        ok = (xi >= 0) & (xi < self.w) & (yi >= 0) & (yi < self.h)
        flat = yi[ok] * self.w + xi[ok]
        r = np.linalg.norm(np.asarray(xyz, np.float64)[ok], axis=1).astype(np.float32)
        order = np.lexsort((r, flat))
        first = np.r_[True, flat[order][1:] != flat[order][:-1]]
        sel = order[first]
        f, rr = flat[sel], r[sel]
        better = rr < self.rng[f]
        f, sel = f[better], sel[better]
        self.rng[f] = r[sel]
        self.rgb[f] = np.asarray(rgb)[ok][sel]
        self.inst[f] = np.asarray(inst)[ok][sel]

    def image(self) -> np.ndarray:
        return self.rgb.reshape(self.h, self.w, 3).copy()

    def instances(self) -> np.ndarray:
        return self.inst.reshape(self.h, self.w).copy()

    def covered(self) -> np.ndarray:
        return np.isfinite(self.rng).reshape(self.h, self.w)


# ---------------------------------------------------------------- extraction

def _row_keys(xyz: np.ndarray) -> np.ndarray:
    a = np.ascontiguousarray(np.asarray(xyz, np.float32).reshape(-1, 3))
    return a.view(np.dtype((np.void, a.dtype.itemsize * 3))).ravel()


def cyclopean_layers(ctx, geometry: np.ndarray) -> dict[str, np.ndarray]:
    """The Cyclopean handoff's eligible cells from the sealed helpers (as the accepted Controller-01 visual)."""
    ev = ctx.evidence
    support, _fp, _med = CYC._map_support(ev, geometry)
    complement = ~support
    exterior, _dist = CYC._exterior_and_distance(complement)
    shoreline = complement & cv2.dilate(support.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    eligible = shoreline & exterior & ~ev.seen_any
    for yaw, pitch in ctx.visited:
        yy, xx, ok = CYC._cells(ev, np.array([yaw]), np.array([pitch]))
        if bool(ok[0]):
            eligible[int(yy[0]), int(xx[0])] = False
    return {"support": support, "eligible": eligible}


class Replay:
    """Step-by-step causal state of the accepted run, from saved artifacts only."""

    def __init__(self, src: Sources):
        self.src = src
        _y0, _y1, _p0, _p1, h, w = chart_grid(src.domain, GRID_DEG)
        self.shape = (h, w)
        self.memory = InstanceMeasurementMemory()
        self.measured: dict[int, int] = {}
        self.head = HeadEvidence.empty((h, w))
        self.seen = epistemic.make_evidence()
        self.ctx: dict[int, c01.LocalPolicyContext] = {}
        self.maps: dict[int, np.ndarray] = {}
        self.geoms: dict[int, np.ndarray] = {}
        self.revs: dict[int, tuple[int, int]] = {}
        self.layer_cache: dict = {}
        self.raster = ChartRaster(src.domain)

    def revision(self, i: int) -> tuple[int, int]:
        return (len(self.ctx[i].visited) if i in self.ctx else 0, int(self.measured.get(i, 0)))

    def geometry(self, i: int) -> np.ndarray:
        rev = self.revision(i)
        if self.revs.get(i) != rev or i not in self.geoms:
            self.geoms[i] = effective_target_geometry(self.maps.get(i, np.empty((0, 3))), self.memory.snapshot(i).xyz_h)
            self.revs[i] = rev
        return self.geoms[i]

    def view(self, i: int):
        ids = sorted(set(self.maps) | set(self.memory.instance_ids()))
        geoms = {j: self.geometry(j) for j in ids}
        revisions = {j: self.revision(j) for j in ids}
        layers = ic.support_layers(geoms, self.src.domain, GRID_DEG, cache=self.layer_cache, revisions=revisions)
        arrays, rows, edges, diag = ic.target_epistemic_view(
            target_id=i, target_name=self.src.names(i), layers=layers, head_view=ic.target_neutral_head_view(self.head),
            seen_any=self.seen.seen_any, domain=self.src.domain, grid_deg=GRID_DEG)
        return arrays, ic.view_summary(rows, edges, diag)

    def step(self, a: dict) -> dict:
        """Apply one saved action; return its per-step products (compared with its records)."""
        src = self.src
        s, i, k = int(a["global_step"]), int(a["target_id"]), int(a["object_local_step"])
        c, obs = src.acquisition(i, k)
        rec, _meta, st = matcher.compute(c, obs)
        patch = src.patch(i, k)
        if not (np.array_equal(patch["valid"], rec["valid"]) and np.array_equal(patch["instance_id"], rec["instance_id"])):
            raise ExtractionMismatch(f"step {s}: matcher recomputation differs from the saved patch")
        add = self.memory.append_patch(patch, source_global_index=s, source_active_target_id=i)
        if {str(x): int(v) for x, v in sorted(add.items())} != a["measurement_memory_additions"]:
            raise ExtractionMismatch(f"step {s}: measurement memory additions differ from the record")
        for x, v in add.items():
            self.measured[int(x)] = self.measured.get(int(x), 0) + int(v)
        hs = add_head_patch(self.head, patch, i, src.domain, GRID_DEG)
        if hs != a["head_evidence"]:
            raise ExtractionMismatch(f"step {s}: head evidence {hs} differs from the record {a['head_evidence']}")
        epistemic.add_observation(self.seen, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                  st["raw_support_R"], rec["valid"], i)
        ctx = self.ctx.setdefault(i, c01.LocalPolicyContext(i))
        epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                  st["raw_support_R"], rec["valid"], i)
        ctx.history.append(object_policy.history_entry(
            calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"],
            instance_R=st["ids_right"], raw_support_R=st["raw_support_R"], target_object_id=i))
        gaze = (float(a["gaze_deg"][0]), float(a["gaze_deg"][1]))
        ctx.visited.append(gaze)
        ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
        before = int(a["active_map_size_before"])
        mf = src.map_file(i, k)
        new_xyz = np.empty((0, 3), np.float32)
        if mf.exists():
            amap = load_npz(mf)
            self.maps[i] = np.asarray(amap["xyz_h"], np.float64)
            new_xyz = np.asarray(amap["xyz_h"], np.float32)[before:]
            if len(amap["xyz_h"]) != int(a["active_map_size_after"]):
                raise ExtractionMismatch(f"step {s}: saved map size differs from the record")
        elif int(a["active_map_size_after"]) != before:
            raise ExtractionMismatch(f"step {s}: map grew but no map file")
        if len(new_xyz) != int(a["new_surfels"]):
            raise ExtractionMismatch(f"step {s}: new surfels {len(new_xyz)} != record {a['new_surfels']}")
        # this look's target measurements: new surfels vs repeated measurements (pixel masks and points)
        valid, ids, xyz = patch["valid"], patch["instance_id"], patch["xyz_h"]
        tmask = valid & (ids == i)
        if int(tmask.sum()) != int(a["target_valid_points"]):
            raise ExtractionMismatch(f"step {s}: target-valid points differ from the record")
        new_px = np.zeros_like(tmask)
        if len(new_xyz):
            keys = set(_row_keys(new_xyz).tolist())
            tk = _row_keys(xyz[tmask])
            hit = np.fromiter((kk in keys for kk in tk.tolist()), bool, count=len(tk))
            new_px[tmask] = hit
            if int(hit.sum()) != len(new_xyz):
                raise ExtractionMismatch(f"step {s}: {int(hit.sum())} new-surfel pixels for {len(new_xyz)} new surfels")
        fused = a["initialization"] == "initialized" or (not a["empty_look"] and a["initialization"] is None)
        rep_px = tmask & ~new_px if fused else np.zeros_like(tmask)
        if int(rep_px.sum()) != int(a["nonnew_target_points"]):
            raise ExtractionMismatch(f"step {s}: repeated measurements {int(rep_px.sum())} != record {a['nonnew_target_points']}")
        cross = valid & (ids > 0) & (ids != i)
        # panel-1 raster: measurement memory up to and including this step (look RGB)
        left_rgb, _right_rgb = src.benchmark(i, k)
        m = valid & (ids > 0)
        self.raster.add(xyz[m], left_rgb[m], ids[m])
        # epistemic view E_t(i) and the local probe's layers after the step
        arrays, summary = self.view(i)
        probe = src.probe_after(i, s)
        if probe["state"] != src.c02_actions[s]["service_states_after"][str(i)].split("/")[0]:
            raise ExtractionMismatch(f"step {s}: probe state differs from the recorded service state")
        geo = self.geometry(i)
        if len(geo) != int(probe["effective_points"]):
            raise ExtractionMismatch(f"step {s}: effective geometry {len(geo)} != probe record {probe['effective_points']}")
        fr = frontier.extract_frontier(geo, gaze[0], gaze[1], c)
        stt = frontier.classify_frontier_state(fr, geo, ctx.history)
        counts = (int(stt["raw_count"]), int(stt["open_count"]), int(stt["map_resolved_count"]),
                  int(stt["boundary_resolved_count"]))
        f6 = probe["fsg6f"]
        if counts != (f6["frontier_raw_count"], f6["frontier_open_count"], f6["frontier_map_resolved_count"],
                      f6["frontier_boundary_resolved_count"]):
            raise ExtractionMismatch(f"step {s}: frontier counts {counts} differ from the probe record")
        eligible = None
        if probe["cyclopean"] is not None:
            eligible = cyclopean_layers(ctx, geo)["eligible"]
            if int(eligible.sum()) != int(probe["cyclopean"]["eligible_cells"]):
                raise ExtractionMismatch(f"step {s}: Cyclopean eligible {int(eligible.sum())} != probe record")
        code = np.zeros(len(fr["xyz_h"]), np.uint8)  # 0 OPEN, 1 MAP_RESOLVED, 2 BOUNDARY_RESOLVED
        code[np.asarray(stt["map_resolved"], bool)] = 1
        code[np.asarray(stt["boundary_resolved"], bool)] = 2
        fy, fp = angles(fr["xyz_h"]) if len(fr["xyz_h"]) else (np.empty(0), np.empty(0))
        return {
            "arrays": {"class_code": arrays["class_code"], "region_code": arrays["region_code"],
                       "frontier_yaw_pitch": np.c_[fy, fp].astype(np.float32), "frontier_state": code,
                       "eligible": np.zeros(self.shape, bool) if eligible is None else eligible,
                       "new_px": new_px, "repeated_px": rep_px, "target_px": (ids == i),
                       "new_xyz": new_xyz, "repeated_xyz": xyz[rep_px].astype(np.float32),
                       "cross_xyz": xyz[cross].astype(np.float32), "cross_id": ids[cross].astype(np.int32)},
            "summary": {"global_step": s, "target_id": i, "target_name": src.names(i), "object_local_step": k,
                        "gaze_deg": list(gaze), "action_source": a["action_source"],
                        "target_valid_points": int(tmask.sum()), "all_valid_points": int(valid.sum()),
                        "target_pixels": int((ids == i).sum()), "target_pixels_without_depth": int(((ids == i) & ~valid).sum()),
                        "new_surfels": int(new_px.sum()), "repeated_measurements": int(rep_px.sum()),
                        "cross_target_points": int(cross.sum()),
                        "cross_target_by_object": {str(int(x)): int((ids[cross] == x).sum()) for x in np.unique(ids[cross])},
                        "active_map_before": before, "active_map_after": int(a["active_map_size_after"]),
                        "effective_points_after": len(geo), "frontier_counts": list(counts),
                        "cyclopean_eligible": None if eligible is None else int(eligible.sum()),
                        "probe_after": probe, "view_summary": summary,
                        "memory_additions": a["measurement_memory_additions"], "head_evidence": hs,
                        "fused": bool(fused)},
        }


def check_views(src: Sources, i: int, stem: str, arrays: dict) -> bool | None:
    z = src.saved_view(i, stem)
    if z is None:
        return None
    ok = np.array_equal(z["class_code"], arrays["class_code"]) and np.array_equal(z["region_code"], arrays["region_code"])
    if not ok:
        raise ExtractionMismatch(f"recomputed view {i}/{stem} differs from the saved controller-time view")
    return True


def extract(source: Path, replay: Path, cache: Path, log=print) -> dict:
    """Controller-time extraction into ``cache`` (under the controller-time firewall)."""
    cache = Path(cache).resolve()
    t0 = time.perf_counter()
    fw = firewall()
    views_checked: list[str] = []
    events_out: dict[str, Any] = {}
    # byte-identity fingerprints are taken outside the firewall (hashing only; nothing is interpreted)
    source, replay = Path(source).resolve(), Path(replay).resolve()
    fp_before = {"controller-01-full": fingerprint(source), "controller-02-classroom-replay": fingerprint(replay)}
    with fw:
        src = Sources(source, replay)
        checks = verify_sources(src)
        log(f"[vl1-extract] sources verified: {len(checks)} identity checks")
        rp = Replay(src)
        steps_dir = cache / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)
        (cache / "raster").mkdir(exist_ok=True)
        summaries = []
        cv2.imwrite(str(cache / "raster/after_-001.png"), rp.raster.image()[..., ::-1])
        np.savez_compressed(cache / "raster/after_-001.npz", inst=rp.raster.instances())
        quiet_state: dict[int, dict] = {}
        for a in src.actions:
            s, i = int(a["global_step"]), int(a["target_id"])
            out = rp.step(a)
            for e in a["events"]:
                j, kind = int(e["object"]), e["event"]
                if kind in ("seed_initialized", "quiet", "blocked") and j == i:
                    if check_views(src, i, f"global_{s:04d}_{kind}", out["arrays"]):
                        views_checked.append(f"{i}/global_{s:04d}_{kind}")
                if kind == "quiet":
                    quiet_state[j] = {"step": s, "class_code": out["arrays"]["class_code"],
                                      "geometry": rp.geometry(j).copy()}
                if kind == "natural_reactivation":
                    arr, summ = rp.view(j)
                    if check_views(src, j, f"global_{s:04d}_natural_reactivation", arr):
                        views_checked.append(f"{j}/global_{s:04d}_natural_reactivation")
                    events_out[str(j)] = reactivation_data(src, rp, j, s, i, quiet_state[j], arr, summ, cache)
            np.savez_compressed(steps_dir / f"step_{s:03d}.npz", **out["arrays"])
            summaries.append(out["summary"])
            cv2.imwrite(str(cache / f"raster/after_{s:03d}.png"), rp.raster.image()[..., ::-1])
            np.savez_compressed(cache / f"raster/after_{s:03d}.npz", inst=rp.raster.instances())
            log(f"[vl1-extract] step {s:3d} target {i} {a['action_source']:<19} new {out['summary']['new_surfels']:>6} "
                f"repeated {out['summary']['repeated_measurements']:>6} ({time.perf_counter() - t0:6.1f} s)")
        # final state: every object's final view equals the saved controller-time terminal view
        final_dir = cache / "final"
        final_dir.mkdir(exist_ok=True)
        for i in sorted(src.seeds):
            arr, summ = rp.view(i)
            if check_views(src, i, "final_terminal", arr):
                views_checked.append(f"{i}/final_terminal")
            np.savez_compressed(final_dir / f"view_{i:04d}.npz", class_code=arr["class_code"])
        np.savez_compressed(final_dir / "footprint.npz", seen_any=rp.seen.seen_any,
                            depth_seen=np.asarray(rp.head.depth_seen, bool))
        g210 = rp.geometry(210)
        saved210 = load_npz(src.obj_dir(210) / "final_effective_geometry.npz")["xyz_h"]
        if len(g210) != len(saved210) or not np.array_equal(np.asarray(saved210, np.float32), g210.astype(np.float32)):
            raise ExtractionMismatch("210's final effective geometry differs from the saved controller-time geometry")
        ctx210 = rp.ctx[210]
        fr = frontier.extract_frontier(g210, ctx210.gaze[0], ctx210.gaze[1], ctx210.calibration)
        stt = frontier.classify_frontier_state(fr, g210, ctx210.history)
        gate = src.c02_residue[0]["detail"]
        if [int(stt["raw_count"]), int(stt["open_count"]), int(stt["map_resolved_count"]),
                int(stt["boundary_resolved_count"])] != gate["frontier_counts_raw_open_map_boundary"]:
            raise ExtractionMismatch("210's final frontier counts differ from the Controller-02 gate record")
        fy, fpp = angles(fr["xyz_h"])
        code = np.zeros(len(fy), np.uint8)
        code[np.asarray(stt["map_resolved"], bool)] = 1
        code[np.asarray(stt["boundary_resolved"], bool)] = 2
        np.savez_compressed(final_dir / "frontier_0210.npz", yaw_pitch=np.c_[fy, fpp].astype(np.float32), state=code)
        events_out["final_210"] = {"frontier_counts": gate["frontier_counts_raw_open_map_boundary"],
                                   "effective_points": len(g210)}
        write_json(cache / "steps.json", summaries)
        write_json(cache / "events.json", events_out)
    fp_after = {"controller-01-full": fingerprint(source), "controller-02-classroom-replay": fingerprint(replay)}
    if fp_after != fp_before:
        raise ExtractionMismatch("a source file changed during the extraction")
    manifest = {
        "schema": "VisualLanguage1-cache-v1",
        "contract": "docs/methodology/visual-language-1-contract.md",
        "truth": "CONTROLLER-TIME sources only; derived by accepted fov3d functions; no evaluation truth, no reference",
        "source": str(src.source), "replay": str(src.replay),
        "source_checks": checks,
        "views_checked_equal_to_saved": views_checked,
        "steps": len(summaries),
        "opened_source_files": sorted(fw.opened),
        "firewall_violations": fw.violations,
        "source_fingerprint_before": fp_before, "source_fingerprint_after": fp_after,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_json(cache / "extract-manifest.json", manifest)
    log(f"[vl1-extract] {len(summaries)} steps; {len(views_checked)} views equal to saved controller-time views; "
        f"opened {len(fw.opened)} files; violations {len(fw.violations)}; {manifest['seconds']} s")
    return manifest


def reactivation_data(src: Sources, rp: Replay, j: int, s: int, trig: int, quiet: dict, arr: dict, summ: dict,
                      cache: Path) -> dict:
    """Natural reactivation of object j after step s: recomputed and compared with the event record."""
    e = [x for x in src.events01 if x["event"] == "natural_reactivation" and x["object"] == j]
    exp = EXPECTED[j]
    if len(e) != 1 or e[0]["global_step"] != s or e[0]["trigger_target"] != trig or e[0]["quiet_since_step"] != quiet["step"]:
        raise ExtractionMismatch(f"reactivation of {j}: event record differs")
    e = e[0]
    ctx = rp.ctx[j]
    before, after = quiet["geometry"], rp.geometry(j)
    cb, ca = cyclopean_layers(ctx, before), cyclopean_layers(ctx, after)
    eb, ea = int(cb["eligible"].sum()), int(ca["eligible"].sum())
    snap = rp.memory.snapshot(j)
    new = snap.source_global_index > quiet["step"]
    by = {str(int(t)): int((snap.source_active_target_id[new] == t).sum()) for t in np.unique(snap.source_active_target_id[new])}
    got = {"eff": (len(before), len(after)), "elig": (eb, ea), "added": int(new.sum())}
    want = {"eff": (e["probe_before"]["effective_points"], e["probe_after"]["effective_points"]),
            "elig": (e["probe_before"]["cyclopean"]["eligible_cells"], e["probe_after"]["cyclopean"]["eligible_cells"]),
            "added": e["memory_added_since_quiet"]["points"]}
    if got != want or got["eff"] != exp["eff"] or got["elig"] != exp["elig"] or got["added"] != exp["added"] \
            or by != e["memory_added_since_quiet"]["by_source_target"] or any(snap.source_active_target_id[new] == j):
        raise ExtractionMismatch(f"reactivation of {j}: recomputed {got} {by} differs from the record {want}")
    served = [a for a in src.actions if a["target_id"] == j and a["scheduler_reason"] == "natural_reactivation"]
    if len(served) != 1 or served[0]["global_step"] != exp["served"]:
        raise ExtractionMismatch(f"reactivation of {j}: service step differs")
    ta = src.actions[s]
    patch = src.patch(trig, int(ta["object_local_step"]))
    px = np.argwhere(patch["valid"] & (patch["instance_id"] == j))
    np.savez_compressed(cache / f"events_reactivation_{j:04d}.npz", before_class=quiet["class_code"],
                        after_class=arr["class_code"], eligible_before=cb["eligible"], eligible_after=ca["eligible"],
                        support_after=ca["support"], added_xyz=np.asarray(snap.xyz_h)[new].astype(np.float32),
                        added_step=snap.source_global_index[new], added_source=snap.source_active_target_id[new],
                        before_xyz=before.astype(np.float32), trigger_pixels=px.astype(np.int32))
    return {"object": j, "quiet_since": quiet["step"], "reactivated_after": s, "trigger": trig,
            "effective": list(got["eff"]), "eligible": list(got["elig"]), "added": got["added"], "added_by_source": by,
            "added_steps": sorted(int(x) for x in np.unique(snap.source_global_index[new])),
            "trigger_look_points": int(len(px)), "served": exp["served"],
            "proposal_after": e["probe_after"]["cyclopean"]["next_gaze_deg"], "view_summary_after": summ}
