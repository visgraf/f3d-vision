"""Integrated Foveal Controller 01 on the Classroom-Oracle scene.

Contract: docs/controller/controller-01-state-action-contract.md.

    .venv/bin/python -m fov3d.experiments.classroom_oracle.controller01 \
        --repo . --out previews/controller-01-full --profile full --device OPTIX

The experiment adapter behind ``fov3d.control.integrated``.  It runs the accepted
Classroom-Oracle bootstrap unchanged, then closes the scene-level loop over every
bootstrap-localized object: the deterministic scheduler chooses the object, and the
accepted local controller (FSG6f, then the Cyclopean handoff) chooses each post-seed gaze
from the object's own-look context and its effective causal target geometry.

The controller reads only the known catalog, one seed direction per localized object, the
current rendered tangent pair and its own accumulated memory.  A process-wide truth firewall
refuses dense evaluation truth for the whole control run.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

import cv2
import numpy as np

import fov3d
from fov3d.control import frontier_config, integrated as ic, object_policy
from fov3d.epistemic.head_memory import HeadEvidence, add_head_patch
from fov3d.experiments.classroom_oracle import config as public
from fov3d.experiments.classroom_oracle import epistemic, matcher
from fov3d.geometry.head_chart import chart_grid
from fov3d.reconstruction import surface_map
from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry

SCHEMA = "Controller01-run-v1"
SPEC_ID = "Integrated-Foveal-Controller-01-v1"
GRID_DEG = 0.10
SMOKE_ACTION_CAP = 8  # smoke cost bound only; never a controller policy
WATCHDOG = int(public.MAX_OBJECT_FIXATIONS)
# The unchanged Blender acquisition, launched exactly as the accepted runner launches it.
BLENDER_SCRIPT = Path(fov3d.ENGINE_DIR) / "classroom_oracle1_render.py"
VERGENCE = {"policy": "fixed", "distance_m": float(frontier_config.VERGENCE_DISTANCE_M),
            "source": "FSG6f VERGENCE_DISTANCE_M, written by the unchanged renderer"}
FOCUS = {"policy": "fixed", "depth_of_field": False,
         "source": "unchanged Classroom-Oracle renderer (depth of field disabled)"}


def is_evaluation_truth(path: str) -> bool:
    """Dense evaluation truth, which the controller must never open."""
    parts = Path(path).parts
    if parts and parts[-1] == "evaluation.json":
        return True
    return any(a == "bootstrap" and b == "evaluation_only" for a, b in zip(parts, parts[1:]))


def _jsonable(x: Any) -> Any:
    if x is None or isinstance(x, (str, bool, int, float)):
        return x
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_jsonable(v) for v in x]
    return repr(x)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(_jsonable(data), indent=1, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _run(cmd: list[str], log: Path, cwd: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, text=True)
    if p.returncode:
        tail = log.read_text(errors="replace").splitlines()[-80:]
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n" + "\n".join(tail))


def _save_rgb(path: Path, rgb: np.ndarray) -> None:
    x = np.clip(np.asarray(rgb, np.float32), 0.0, 1.0)
    u8 = np.rint(np.power(x, 1.0 / 2.2) * 255.0).astype(np.uint8)
    if not cv2.imwrite(str(path), u8[..., ::-1]):
        raise RuntimeError(f"failed to write {path}")


def _same_gaze(a: tuple[float, float], b: tuple[float, float], eps: float = 1e-8) -> bool:
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps


def _map_arrays(sm: Any) -> dict[str, np.ndarray]:
    return {
        "xyz_h": np.asarray(sm.xyz_h).astype(np.float32),
        "rgb": np.asarray(sm.rgb),
        "instance_id": np.asarray(sm.instance_id),
        "support_count": np.asarray(sm.support_count),
        "provenance_mask": np.asarray(sm.provenance_mask),
    }


def _fsg6f_summary(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "stop": bool(d["stop"]),
        "reason": str(d["reason"]),
        "next_gaze_deg": d.get("next_gaze_deg"),
        "frontier_raw_count": int(d["frontier_raw_count"]),
        "frontier_open_count": int(d["frontier_open_count"]),
        "frontier_map_resolved_count": int(d["frontier_map_resolved_count"]),
        "frontier_boundary_resolved_count": int(d["frontier_boundary_resolved_count"]),
        "candidates": len(d["candidates"]),
        "consensus_rejected_candidates": int(d["consensus_rejected_candidate_count"]),
    }


def _cyclopean_summary(e: dict[str, Any]) -> dict[str, Any]:
    a = e["audit"]
    return {
        "stop": bool(e["stop"]),
        "reason": str(e["reason"]),
        "next_gaze_deg": e.get("next_gaze_deg"),
        "eligible_cells": int(a["eligible_never_observed_exterior_shoreline_cells"]),
        "map_support_cells": int(a["map_support_cells"]),
        "shoreline_cells": int(a["shoreline_cells"]),
        "never_observed_cells": int(a["epistemic_state_counts"]["NEVER_OBSERVED"]),
    }


@dataclass
class LocalPolicyContext:
    """The accepted local controller's own-target inputs for one object."""

    target_id: int
    gaze: tuple[float, float] | None = None
    calibration: dict[str, Any] | None = None
    state: dict[str, np.ndarray] | None = None
    visited: list[tuple[float, float]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    evidence: Any = field(default_factory=epistemic.make_evidence)
    surface_map: Any = None


def probe_local_policy(ctx: LocalPolicyContext, geometry: np.ndarray, *,
                       fsg6f=object_policy.choose_next,
                       cyclopean=epistemic.choose_next) -> tuple[ic.ProbeResult, dict[str, Any]]:
    """Service probe: the accepted FSG6f -> Cyclopean sequence, read-only.

    Returns the ProbeResult (with a compact summary as its detail) and the full decisions.
    """
    if ctx.gaze is None or ctx.calibration is None or ctx.state is None:
        raise ValueError(f"object {ctx.target_id} has no completed own look to probe from")
    st = ctx.state
    d = fsg6f(
        current_yaw_deg=float(ctx.gaze[0]),
        current_pitch_deg=float(ctx.gaze[1]),
        calibration=ctx.calibration,
        instance_L=st["ids_left"],
        raw_support_L=st["raw_support_L"],
        instance_R=st["ids_right"],
        raw_support_R=st["raw_support_R"],
        map_xyz_h=np.asarray(geometry, float),
        visited_gazes_deg=[[float(y), float(p)] for y, p in ctx.visited],
        observation_history=ctx.history,
        target_object_id=int(ctx.target_id),
    )
    summary: dict[str, Any] = {"fsg6f": _fsg6f_summary(d), "cyclopean": None, "effective_points": int(len(geometry))}
    if not bool(d["stop"]):
        gaze = (float(d["next_gaze_deg"][0]), float(d["next_gaze_deg"][1]))
        return ic.ProbeResult(ic.Observe(ctx.target_id, gaze, VERGENCE, FOCUS, "fsg6f"), summary), {"fsg6f_decision": d}
    e = cyclopean(ctx.evidence, geometry, ctx.visited)
    summary["cyclopean"] = _cyclopean_summary(e)
    decisions = {"fsg6f_decision": d, "cyclopean_decision": e}
    if not bool(e["stop"]):
        gaze = (float(e["next_gaze_deg"][0]), float(e["next_gaze_deg"][1]))
        return ic.ProbeResult(ic.Observe(ctx.target_id, gaze, VERGENCE, FOCUS, "cyclopean_epistemic"), summary), decisions
    return ic.ProbeResult(None, summary), decisions


class ClassroomController01:
    """Causal memory M_t plus the observe/probe/revision callbacks of the control loop."""

    def __init__(self, repo: Path, root: Path, scene: Path, args: argparse.Namespace,
                 seeds_doc: dict[str, Any], catalog_doc: dict[str, Any]) -> None:
        self.repo, self.root, self.scene, self.args = repo, root, scene, args
        self.domain = dict(seeds_doc["controller_domain_deg"])
        _y0, _y1, _p0, _p1, h, w = chart_grid(self.domain, GRID_DEG)
        self.seeds = {int(s["instance_id"]): tuple(map(float, s["seed_gaze_deg"])) for s in seeds_doc["instances"]}
        self.names = {int(o["instance_id"]): str(o["object_name"]) for o in catalog_doc["instances"]}
        self.memory = InstanceMeasurementMemory()
        self.measured_points: dict[int, int] = {}
        self.head = HeadEvidence.empty((h, w))
        self.seen = epistemic.make_evidence()
        if self.seen.shape != (h, w):
            raise RuntimeError(f"seen_any chart {self.seen.shape} differs from the head chart {(h, w)}")
        self.ctx = {i: LocalPolicyContext(i) for i in self.seeds}
        self.trajectory: dict[int, list[dict[str, Any]]] = {i: [] for i in self.seeds}
        self.probes: dict[int, list[dict[str, Any]]] = {i: [] for i in self.seeds}
        self.decisions: dict[int, dict[str, Any]] = {}
        self.incidental: dict[int, set[int]] = {i: set() for i in self.seeds}
        self.layer_cache: dict[int, tuple[Any, Any]] = {}
        self.quiet_view: dict[int, str] = {}
        self.current_step = -1
        self.timing = {"render_s": 0.0, "probe_s": 0.0, "view_s": 0.0}

    # -- memory views
    def map_xyz(self, i: int) -> np.ndarray:
        sm = self.ctx[i].surface_map if i in self.ctx else None
        return np.empty((0, 3), np.float64) if sm is None else np.asarray(sm.xyz_h, np.float64)

    def geometry(self, i: int) -> np.ndarray:
        return effective_target_geometry(self.map_xyz(i), self.memory.snapshot(i).xyz_h)

    def revision(self, i: int) -> tuple[int, int]:
        own = len(self.ctx[i].visited) if i in self.ctx else 0
        return own, int(self.measured_points.get(i, 0))

    # -- loop callbacks
    def probe(self, i: int) -> ic.ProbeResult:
        t0 = time.perf_counter()
        result, decisions = probe_local_policy(self.ctx[i], self.geometry(i))
        dt = time.perf_counter() - t0
        self.timing["probe_s"] += dt
        self.decisions[i] = decisions
        self.probes[i].append({"after_global_step": self.current_step, "revision": list(self.revision(i)),
                               "state": result.state.value, "seconds": round(dt, 3), **dict(result.detail)})
        return result

    def observe(self, step: int, action: ic.Observe, local: int) -> ic.ObservationOutcome:
        i = int(action.target_id)
        ctx = self.ctx[i]
        gaze = action.gaze_yaw_pitch_deg
        if any(_same_gaze(gaze, old) for old in ctx.visited):
            raise RuntimeError(f"controller inconsistency: already visited gaze {gaze} for instance {i}")
        odir = self.root / "objects" / f"instance_{i:04d}"
        for sub in ("acquisitions", "maps", "patches", "benchmark"):
            (odir / sub).mkdir(parents=True, exist_ok=True)
        adir = odir / "acquisitions" / f"fix_{local:02d}"
        adir.mkdir()
        t0 = time.perf_counter()
        cmd = [
            self.args.blender, "-b", str(self.scene), "--python-exit-code", "1",
            "-P", str(BLENDER_SCRIPT), "--",
            "--mode", "fixation", "--out", str(adir), "--profile", self.args.profile,
            "--device", self.args.device, "--yaw", str(gaze[0]), "--pitch", str(gaze[1]),
            "--object-id", str(i), "--step", str(local),
        ]
        if self.args.spp is not None:
            cmd += ["--spp", str(self.args.spp)]
        _run(cmd, adir.parent / f"fix_{local:02d}.blender.log", self.repo)
        render_s = time.perf_counter() - t0
        self.timing["render_s"] += render_s

        c = json.loads((adir / "calibration.json").read_text())
        obs = _load_npz(adir / "oracle_observation.npz")
        rec, matcher_meta, st = matcher.compute(c, obs)
        valid = np.asarray(rec["valid"], bool)
        ids = np.asarray(rec["instance_id"])
        target_points = int((valid & (ids == i)).sum())
        seen_ids = set(np.unique(np.concatenate((st["ids_left"].ravel(), st["ids_right"].ravel()))).tolist())
        self.incidental[i].update(int(k) for k in seen_ids if int(k) not in (0, i))

        patch = {
            "xyz_h": np.asarray(rec["xyz_h"], np.float32),
            "valid": valid,
            "instance_id": np.asarray(rec["instance_id"], np.int32),
            "range_left_m": np.asarray(rec["range_left_m"], np.float32),
        }
        np.savez_compressed(odir / "patches" / f"fix_{local:02d}.npz", **patch)
        _save_rgb(odir / "benchmark" / f"fix_{local:02d}_L.png", rec["rgb_left"])
        _save_rgb(odir / "benchmark" / f"fix_{local:02d}_R.png", rec["rgb_right"])

        additions = self.memory.append_patch(patch, source_global_index=step, source_active_target_id=i)
        for k, n in additions.items():
            self.measured_points[int(k)] = self.measured_points.get(int(k), 0) + int(n)
        head_stats = add_head_patch(self.head, patch, i, self.domain, GRID_DEG)
        epistemic.add_observation(self.seen, c, st["ids_left"], st["raw_support_L"],
                                  st["ids_right"], st["raw_support_R"], rec["valid"], i)

        p = surface_map.Patch(patch_id=f"fix_{local:02d}", xyz_h=rec["xyz_h"],
                              rgb=rec["rgb_left"], instance_id=rec["instance_id"])
        before = len(self.map_xyz(i))
        initialized: bool | None = None
        new_count = duplicate_count = 0
        fusion: dict[str, Any] = {}
        if ctx.surface_map is None:
            if target_points >= public.MIN_INITIAL_TARGET_POINTS:
                ctx.surface_map = surface_map.initialize(p, i)
                new_count = len(ctx.surface_map.xyz_h)
                initialized = True
                fusion = {"initialized": True}
            else:
                initialized = False
                fusion = {"initialized": False, "reason": "seed_below_initialisation_precondition"}
        elif target_points >= public.MIN_INITIAL_TARGET_POINTS:
            radius = float(public.FUSION["association_radius_m"])
            cell = float(public.FUSION["hash_cell_m"])
            sm2, meta = surface_map.fuse(ctx.surface_map, p, i, radius, cell)
            new_count = max(0, len(sm2.xyz_h) - before)
            duplicate_count = max(0, target_points - new_count)
            replay, _ = surface_map.fuse(sm2, p, i, radius, cell)
            x1, x2 = np.asarray(sm2.xyz_h), np.asarray(replay.xyz_h)
            if x1.shape != x2.shape or not np.allclose(x1, x2, rtol=0.0, atol=1e-10, equal_nan=True):
                raise RuntimeError(f"12 mm fusion lost idempotence at instance {i}, local step {local}")
            ctx.surface_map = sm2
            dist = np.asarray(meta.get("distances_m", np.empty(0)), float)
            fusion = {k: v for k, v in meta.items() if k != "distances_m"}
            fusion["matched_distance_m"] = None if not len(dist) else {
                "median": float(np.median(dist)), "p95": float(np.quantile(dist, 0.95)), "max": float(dist.max())}
        else:
            fusion = {"empty_look": True, "reason": "target_points_below_initialisation_precondition"}
        if ctx.surface_map is not None:
            np.savez_compressed(odir / "maps" / f"fix_{local:02d}.npz", **_map_arrays(ctx.surface_map))

        # The accepted local controller's own-target context, in the accepted runner's order.
        epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"],
                                  st["ids_right"], st["raw_support_R"], rec["valid"], i)
        ctx.history.append(object_policy.history_entry(
            calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"],
            instance_R=st["ids_right"], raw_support_R=st["raw_support_R"], target_object_id=i))
        ctx.visited.append(gaze)
        ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
        self.current_step = step

        after = len(self.map_xyz(i))
        record = {
            "target_name": self.names.get(i, str(i)),
            "target_valid_points": target_points,
            "all_instance_valid_points": int(valid.sum()),
            "active_map_size_before": before,
            "active_map_size_after": after,
            "new_surfels": int(new_count),
            "nonnew_target_points": int(duplicate_count),
            "measurement_memory_additions": {str(k): int(v) for k, v in sorted(additions.items())},
            "initialization": None if initialized is None else ("initialized" if initialized else "seed_uninitializable"),
            "empty_look": bool(fusion.get("empty_look", False)),
            "prescribed_vergence_distance_m": float(c["prescribed_vergence_distance_m"]),
            "head_evidence": head_stats,
            "render_seconds": round(render_s, 3),
        }
        row = {
            "step": local,
            "global_step": step,
            "gaze_deg": list(gaze),
            "action_source": action.source,
            "target_points": target_points,
            "oracle_valid_points_all_instances": int(valid.sum()),
            "map_size_before": before,
            "map_size_after": after,
            "new_surfels": int(new_count),
            "nonnew_target_points": int(duplicate_count),
            "measurement_memory_additions": record["measurement_memory_additions"],
            "matcher": matcher_meta,
            "fusion": fusion,
            "proposal_decisions": None if action.source == ic.SEED_SOURCE else self.decisions.get(i),
            "raw_left_exr": str((adir / "raw_L.exr").relative_to(self.root)),
            "raw_right_exr": str((adir / "raw_R.exr").relative_to(self.root)),
            "oracle_patch": str((odir / "patches" / f"fix_{local:02d}.npz").relative_to(self.root)),
        }
        self.trajectory[i].append(row)
        _write_json(odir / "trajectory.partial.json", self.trajectory[i])
        return ic.ObservationOutcome(initialized=initialized, record=record)

    # -- target-relative intrinsic views E_t(i)
    def measured_geometries(self) -> tuple[dict[int, np.ndarray], dict[int, tuple[int, int]]]:
        ids = sorted({i for i in self.ctx if self.ctx[i].surface_map is not None} | set(self.memory.instance_ids()))
        return {i: self.geometry(i) for i in ids}, {i: self.revision(i) for i in ids}

    def save_view(self, i: int, step: int, label: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        geometries, revisions = self.measured_geometries()
        layers = ic.support_layers(geometries, self.domain, GRID_DEG, cache=self.layer_cache, revisions=revisions)
        arrays, rows, edges, diag = ic.target_epistemic_view(
            target_id=i, target_name=self.names.get(i, str(i)), layers=layers,
            head_view=ic.target_neutral_head_view(self.head), seen_any=self.seen.seen_any,
            domain=self.domain, grid_deg=GRID_DEG)
        summary = ic.view_summary(rows, edges, diag)
        vdir = self.root / "objects" / f"instance_{i:04d}" / "epistemic"
        vdir.mkdir(parents=True, exist_ok=True)
        stem = f"global_{step:04d}_{label}" if step >= 0 else f"final_{label}"
        np.savez_compressed(vdir / f"{stem}.npz", class_code=arrays["class_code"], region_code=arrays["region_code"])
        _write_json(vdir / f"{stem}.json", {"target_id": i, "global_step": step, "label": label,
                                            "revision": list(self.revision(i)), "summary": summary, "diag": diag})
        self.timing["view_s"] += time.perf_counter() - t0
        return {"path": str((vdir / f"{stem}.npz").relative_to(self.root)), "summary": summary}

    def memory_provenance(self, i: int, after_step: int | None = None) -> dict[str, Any]:
        snap = self.memory.snapshot(i)
        mask = np.ones(len(snap.source_global_index), bool) if after_step is None \
            else snap.source_global_index > int(after_step)
        src = snap.source_active_target_id[mask]
        return {
            "points": int(mask.sum()),
            "own_target_points": int((src == i).sum()),
            "cross_target_points": int((src != i).sum()),
            "by_source_target": {str(int(k)): int((src == k).sum()) for k in np.unique(src)},
            "source_global_steps": sorted(int(k) for k in np.unique(snap.source_global_index[mask])),
        }

    def on_event(self, ev: dict[str, Any]) -> None:
        i, kind, step = int(ev["object"]), str(ev["event"]), int(ev["global_step"])
        ev["revision"] = list(self.revision(i))
        if kind in ("seed_initialized", "quiet", "natural_reactivation", "blocked"):
            ev["epistemic_view"] = self.save_view(i, step, kind)
        if kind == "quiet":
            self.quiet_view[i] = ev["epistemic_view"]["path"]
        if kind == "natural_reactivation":
            ev["epistemic_view_before"] = self.quiet_view.pop(i, None)
            ev["memory_added_since_quiet"] = self.memory_provenance(i, ev.get("quiet_since_step"))

    # -- final per-object artifacts
    def finish_object(self, i: int, state: ic.ObjectSummary, fixations: int) -> dict[str, Any]:
        odir = self.root / "objects" / f"instance_{i:04d}"
        sm = self.ctx[i].surface_map
        if sm is not None:
            np.savez_compressed(odir / "final_map.npz", **_map_arrays(sm))
        snap = self.memory.snapshot(i)
        eff = self.geometry(i)
        np.savez_compressed(
            odir / "final_effective_geometry.npz",
            xyz_h=eff.astype(np.float32),
            active_map_points=np.int64(len(self.map_xyz(i))),
            measured_source_global_index=snap.source_global_index,
            measured_source_active_target_id=snap.source_active_target_id,
        )
        result = {
            "instance_id": i,
            "object_name": self.names.get(i, str(i)),
            "seed_gaze_deg": list(self.seeds[i]),
            "fixation_count": int(fixations),
            "termination": state.label,
            "final_service_state": state.state.value,
            "blocked_reason": state.blocked_reason,
            "final_map_surfels": int(len(self.map_xyz(i))),
            "final_effective_geometry_points": int(len(eff)),
            "measurement_provenance": self.memory_provenance(i),
            "incidental_instance_ids": sorted(self.incidental[i]),
            "trajectory": self.trajectory[i],
            "probes": self.probes[i],
        }
        _write_json(odir / "result.json", result)
        return result


def manifest_row(result: dict[str, Any]) -> dict[str, Any]:
    """The accepted Classroom-Oracle manifest row, read by the existing offline evaluator."""
    keep = ("step", "global_step", "gaze_deg", "action_source", "target_points",
            "map_size_before", "map_size_after", "new_surfels", "nonnew_target_points")
    row = {k: result[k] for k in ("instance_id", "object_name", "seed_gaze_deg", "fixation_count",
                                  "termination", "final_service_state", "blocked_reason",
                                  "final_map_surfels", "final_effective_geometry_points",
                                  "incidental_instance_ids")}
    row["trajectory"] = [{k: t[k] for k in keep} for t in result["trajectory"]]
    return row


def _counts(loop: ic.LoopResult, catalog: dict[int, str], seeds: dict[int, Any]) -> dict[str, Any]:
    final = {i: loop.final[i] for i in seeds}

    def n(state: ic.ServiceState, reason: str | None = None) -> int:
        return sum(1 for s in final.values() if s.state is state and (reason is None or s.blocked_reason == reason))

    return {
        "known_catalog_objects": len(catalog),
        "localized_objects": len(seeds),
        "unlocated_objects": len(set(catalog) - set(seeds)),
        "successfully_initialized_objects": len(loop.initialized),
        "blocked_initialization_objects": n(ic.ServiceState.BLOCKED, "seed_uninitializable"),
        "watchdog_blocked_objects": n(ic.ServiceState.BLOCKED, "watchdog"),
        "quiet_objects": n(ic.ServiceState.QUIET),
        "actionable_objects_at_termination": n(ic.ServiceState.ACTIONABLE),
        "seedable_objects_at_termination": n(ic.ServiceState.SEEDABLE),
        "total_actions": len(loop.actions),
        "total_switches": sum(1 for a in loop.actions if a["scheduler_decision"] == "switch"),
        "attention_bouts": max((int(a["attention_bout"]) for a in loop.actions), default=0),
        "quiet_episodes": sum(1 for e in loop.events if e["event"] == "quiet"),
        "natural_reactivations": sum(1 for e in loop.events if e["event"] == "natural_reactivation"),
        "watchdog_hits": sum(1 for e in loop.events if e["event"] == "blocked" and e["reason"] == "watchdog"),
        "initialization_failures": sum(1 for e in loop.events
                                       if e["event"] == "blocked" and e["reason"] == "seed_uninitializable"),
    }


def _terminal(t: Any) -> dict[str, Any]:
    if isinstance(t, ic.Stop):
        return {"type": "STOP", "reason": t.reason}
    if isinstance(t, ic.Incomplete):
        return {"type": "INCOMPLETE", "reason": t.reason, "blocked": [list(b) for b in t.blocked]}
    return {"type": "CAP", "reason": t.reason, "cap": t.cap}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--scene", default=public.SCENE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blender", default="blender")
    ap.add_argument("--profile", choices=("small", "full"), default=public.DEFAULT_PROFILE)
    ap.add_argument("--device", choices=("OPTIX", "CUDA", "CPU"), default=public.DEFAULT_DEVICE)
    ap.add_argument("--spp", type=int, default=None)
    ap.add_argument("--smoke", action="store_true",
                    help=f"plumbing/integration only: stop after {SMOKE_ACTION_CAP} executed actions (not a scientific run)")
    return ap.parse_args(argv)


def self_test() -> list[str]:
    fails = list(public.self_test())
    if public.FUSION != {"association_radius_m": 0.012, "hash_cell_m": 0.012}:
        fails.append("fusion rule is not the frozen 12 mm rule")
    if WATCHDOG != 24:
        fails.append("watchdog changed")
    if abs(float(frontier_config.VERGENCE_DISTANCE_M) - 2.10) > 1e-12:
        fails.append("fixed vergence changed")
    if not BLENDER_SCRIPT.is_file():
        fails.append(f"Blender acquisition script missing: {BLENDER_SCRIPT}")
    return fails


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve()
    root = Path(args.out).resolve()
    scene = Path(args.scene) if Path(args.scene).is_absolute() else repo / args.scene
    scene = scene.resolve()
    if not scene.exists():
        raise FileNotFoundError(scene)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"output must be new or empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir()
    bad = self_test()
    if bad:
        raise RuntimeError("controller01 self-test failed: " + "; ".join(bad))

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "spec_id": SPEC_ID,
        "contract": "docs/controller/controller-01-state-action-contract.md",
        "classroom_oracle_spec_id": public.SPEC_ID,
        "classroom_oracle_public_digest": public.public_digest(),
        "scene": str(scene.relative_to(repo) if scene.is_relative_to(repo) else scene),
        "profile": args.profile,
        "device": args.device,
        "spp_override": args.spp,
        "smoke": bool(args.smoke),
        "smoke_action_cap": SMOKE_ACTION_CAP if args.smoke else None,
        "watchdog_target_fixations": WATCHDOG,
        "vergence": VERGENCE,
        "focus": FOCUS,
        "controller_truth_scope": "instance catalog + one seed per localized instance + current tangent pair only",
        "control_complete": False,
    }
    _write_json(root / "manifest.json", manifest)

    firewall = ic.TruthFirewall(root, is_evaluation_truth)
    t_start = time.perf_counter()
    with firewall:
        try:
            boot = root / "bootstrap"
            boot.mkdir()
            t0 = time.perf_counter()
            _run([
                args.blender, "-b", str(scene), "--python-exit-code", "1",
                "-P", str(BLENDER_SCRIPT), "--",
                "--mode", "seeds", "--out", str(boot), "--profile", args.profile,
                "--device", args.device, "--seed-step", str(public.SEED_SCAN_STEP_DEG),
            ], root / "logs" / "bootstrap.blender.log", repo)
            bootstrap_s = time.perf_counter() - t0
            seeds_doc = json.loads((boot / "seeds.json").read_text())
            catalog_doc = json.loads((boot / "instance_catalog.json").read_text())
            run = ClassroomController01(repo, root, scene, args, seeds_doc, catalog_doc)
            catalog = run.names
            initial = ic.catalog_summaries(catalog, run.seeds)
            unlocated = sorted(i for i, s in initial.items() if s.state is ic.ServiceState.UNLOCATED)
            manifest.update({
                "controller_domain_deg": run.domain,
                "known_catalog_object_ids": sorted(catalog),
                "localized_object_ids": sorted(run.seeds),
                "unlocated_object_ids": unlocated,
            })
            actions: list[dict[str, Any]] = []

            def on_action(record: dict[str, Any]) -> None:
                actions.append(record)
                _write_json(root / "actions.partial.json", {"schema": SCHEMA, "actions": actions})

            t1 = time.perf_counter()
            loop = ic.run_control_loop(
                run.seeds, observe=run.observe, probe=run.probe, revision=run.revision,
                vergence=VERGENCE, focus=FOCUS, watchdog=WATCHDOG, unlocated=unlocated,
                action_cap=SMOKE_ACTION_CAP if args.smoke else None,
                on_event=run.on_event, on_action=on_action,
            )
            control_s = time.perf_counter() - t1
            final_views = {}
            for i in sorted(loop.initialized):
                final_views[str(i)] = run.save_view(i, -1, "terminal")
            results = {i: run.finish_object(i, loop.final[i], loop.fixations[i])
                       for i in sorted(run.seeds) if loop.fixations[i] > 0}
        except BaseException as exc:
            manifest["terminal"] = {"type": "RUNTIME_FAILURE", "error": f"{type(exc).__name__}: {exc}"}
            manifest["truth_firewall"] = {"violations": list(firewall.violations)}
            manifest["dense_evaluation_truth_opened_during_control"] = bool(firewall.violations)
            _write_json(root / "manifest.json", manifest)
            raise

    counts = _counts(loop, catalog, run.seeds)
    terminal = _terminal(loop.terminal)
    unlocated_measured = {str(i): int(run.measured_points[i]) for i in sorted(run.measured_points) if i in unlocated}
    _write_json(root / "actions.json", {"schema": SCHEMA, "actions": loop.actions, "events": loop.events})
    (root / "actions.partial.json").unlink(missing_ok=True)
    manifest.update({
        **counts,
        "terminal": terminal,
        "terminal_reason": terminal["reason"],
        "global_quiescence": terminal["type"] == "STOP",
        "final_service_states": {
            str(i): {"object_name": run.names.get(i, str(i)), "state": loop.final[i].state.value,
                     "blocked_reason": loop.final[i].blocked_reason, "fixations": int(loop.fixations[i])}
            for i in sorted(run.seeds)
        },
        "final_epistemic_views": final_views,
        "cross_target_provenance": {str(i): run.memory_provenance(i) for i in sorted(run.seeds)},
        "unlocated_instances_measured_incidentally": unlocated_measured,
        "measured_instance_ids": list(run.memory.instance_ids()),
        "probe_calls": loop.probe_calls,
        "probe_cache_hits": loop.probe_cache_hits,
        "truth_firewall": {
            "mechanism": "sys.addaudithook on open/os.listdir/os.scandir, active for the whole control run",
            "violations": list(firewall.violations),
            "opened_run_files": sorted(firewall.opened),
        },
        "dense_evaluation_truth_opened_during_control": bool(firewall.violations),
        "timing_s": {"bootstrap": round(bootstrap_s, 2), "control": round(control_s, 2),
                     "total": round(time.perf_counter() - t_start, 2),
                     **{k: round(v, 2) for k, v in run.timing.items()}},
        "objects": [manifest_row(results[i]) for i in sorted(results)],
        "total_fixations": len(loop.actions),
        "control_complete": True,
    })
    _write_json(root / "manifest.json", manifest)
    print("[controller01] COMPLETE", json.dumps({
        "terminal": terminal, "actions": counts["total_actions"], "switches": counts["total_switches"],
        "bouts": counts["attention_bouts"], "reactivations": counts["natural_reactivations"],
        "localized": counts["localized_objects"], "smoke": bool(args.smoke),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
