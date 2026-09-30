"""Controller-02 on the Classroom-Oracle scene: accepted-evidence replay and the strict final-look gate v1.

Contract: docs/controller/controller-02-residual-closure-contract.md.

    .venv/bin/python -m fov3d.experiments.classroom_oracle.controller02 --repo . \
        --source previews/controller-01-full --out previews/controller-02-classroom-replay

The experiment replays the accepted Controller-01 full run instead of rendering.  The frozen
Controller-01 adapter (``ClassroomController01``) supplies memory, probe and revision; for every
ordinary OBSERVE that Controller-02 selects, the replay requires the accepted action's target,
gaze, source and local step, runs the frozen ``observe`` unchanged in a temporary directory with
its Blender call replaced by a copy of that action's saved controller-time acquisition, and
verifies the step's patch, fused map and measurement record against the saved ones.  No process
may be launched; evaluation truth and the later Controller-01A/01B/01C artifacts are refused.

The strict final-look gate v1 is an admissibility filter over the frozen local proposal: only an
FSG6f proposal exposes traceable unresolved support; each support element's look-ahead target must
lie in both binocular depth cores predicted from the sensor model (no render), be OPEN and
unmapped at 12 mm, and not already have been binocularly interrogated by a prior own look.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Iterator

import numpy as np

import fov3d  # noqa: F401  (puts the sealed engine on sys.path for the facades)
from fov3d.control import controller02 as c2
from fov3d.control import frontier, frontier_config, integrated as ic, object_policy
from fov3d.experiments.classroom_oracle import controller01 as c01
from fov3d.geometry.core import make_calibration
from fov3d.stereo.core import rectification, support_mask

FR = frontier._legacy_impl  # sealed FSG6f frontier helpers, read-only
SF = FR.public.SURFACE_FRONTIER
BUDGET = int(c01.WATCHDOG)  # the unchanged Controller-01 number, now an ordinary-service budget
SCHEMA = "Controller02-classroom-replay-v1"
CONTRACT = "docs/controller/controller-02-residual-closure-contract.md"
ACCEPTED_SOURCE = {"manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
                   "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd"}
LATER_ARTIFACTS = ("controller-01a-terminal-audit", "controller-01b-single-continuation",
                   "controller-01c-frontier-action-correspondence")
SCENE_CLOSED_MARKER = "CONTROLLER02_CLASSROOM_SCENE_CLOSED"
NOT_CLOSED_MARKER = "CONTROLLER02_CLASSROOM_NOT_CLOSED"
RECORD_FIELDS = ("target_valid_points", "all_instance_valid_points", "active_map_size_before", "active_map_size_after",
                 "new_surfels", "nonnew_target_points", "measurement_memory_additions", "initialization", "empty_look",
                 "head_evidence", "prescribed_vergence_distance_m")
MAP_FIELDS = ("xyz_h", "rgb", "instance_id", "support_count", "provenance_mask")


def is_forbidden_during_replay(path: str) -> bool:
    """Evaluation truth, and the later Controller-01A/01B/01C artifacts (validation-only sources)."""
    return c01.is_evaluation_truth(path) or any(part in LATER_ARTIFACTS for part in Path(path).parts)


class ReplayDivergence(RuntimeError):
    """Controller-02 selected an ordinary action that differs from the accepted Controller-01 action."""


class NoAcceptedEvidence(RuntimeError):
    """An action has no accepted sensory evidence to replay; rendering is not authorized here."""


class NoProcessGuard:
    """Refuse every process launch in this process while active (so no Blender can start)."""

    EVENTS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
              "os.forkpty")
    _installed = False
    _active: "NoProcessGuard | None" = None

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def __enter__(self) -> "NoProcessGuard":
        if not NoProcessGuard._installed:
            sys.addaudithook(NoProcessGuard._hook)
            NoProcessGuard._installed = True
        if NoProcessGuard._active is not None:
            raise RuntimeError("a process guard is already active")
        NoProcessGuard._active = self
        return self

    def __exit__(self, *exc: Any) -> None:
        NoProcessGuard._active = None

    @staticmethod
    def _hook(event: str, args: tuple) -> None:
        guard = NoProcessGuard._active
        if guard is None or event not in NoProcessGuard.EVENTS:
            return
        guard.attempts.append(f"{event}: {args[0] if args else ''}")
        raise PermissionError(f"process launch refused during the Controller-02 replay: {event}")


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _equal(a: np.ndarray, b: np.ndarray) -> bool:
    """Exact array equality; NaN equals NaN only in floating-point arrays."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    return bool(np.array_equal(a, b, equal_nan=np.issubdtype(a.dtype, np.floating)))


def _same_gaze(a, b, eps: float = 1e-9) -> bool:
    return abs(float(a[0]) - float(b[0])) <= eps and abs(float(a[1]) - float(b[1])) <= eps


# ---------------------------------------------------------------- strict final-look gate v1

def reconstruct_support(decision: dict[str, Any], geometry: np.ndarray, gaze: tuple[float, float],
                        calibration: dict[str, Any], state: dict[str, np.ndarray], history: list[dict[str, Any]],
                        target_id: int) -> dict[str, Any]:
    """The selected FSG6f candidate's exact support, recomputed with the accepted formulas.

    Identity is checked against the decision: the candidate counts, the frontier score and the
    candidate's continuation evidence recomputed from the support mask.
    """
    sel = decision["selected"]
    fr = frontier.extract_frontier(geometry, gaze[0], gaze[1], calibration)
    st = frontier.classify_frontier_state(fr, geometry, history)
    step = float(SF["component_step_deg"])
    dx, dy = int(round((sel["yaw_deg"] - gaze[0]) / step)), int(round((sel["pitch_deg"] - gaze[1]) / step))
    if (dx, dy) == (0, 0):
        raise ValueError("the selected candidate is the current gaze")
    u = np.array([dx, dy], float)
    u /= np.linalg.norm(u)
    delta = np.c_[fr["target_yaw_deg"] - fr["yaw_deg"], fr["target_pitch_deg"] - fr["pitch_deg"]]
    dn = np.linalg.norm(delta, axis=1)
    good = dn > 1e-12
    align = np.zeros(len(delta))
    align[good] = (delta[good] / dn[good, None]) @ u
    raw = align >= float(SF["alignment_cos_min"])
    support = raw & st["open"]
    counts = [int(support.sum()), int(raw.sum()), int((raw & st["map_resolved"]).sum()),
              int((raw & st["boundary_resolved"]).sum())]
    score = float(np.sum(fr["strength"][support] * align[support]))
    proj = FR._project_frontier_pairs(calibration, fr["xyz_h"], fr["target_xyz_h"])
    cont = FR._candidate_continuation_from_projected(
        dx, dy, object_policy.relabel_instances(state["ids_left"], target_id), state["raw_support_L"],
        object_policy.relabel_instances(state["ids_right"], target_id), state["raw_support_R"],
        proj, support, FR.public.OBJECT_ID)
    identity = {
        "frontier_counts": [st["raw_count"], st["open_count"], st["map_resolved_count"], st["boundary_resolved_count"]]
        == [decision["frontier_raw_count"], decision["frontier_open_count"], decision["frontier_map_resolved_count"],
            decision["frontier_boundary_resolved_count"]],
        "support_counts": counts == [sel["frontier_support_count"], sel["raw_frontier_support_count"],
                                     sel["map_resolved_support_count"], sel["boundary_resolved_support_count"]],
        "frontier_score": abs(score - float(sel["frontier_score"])) <= 1e-12 * max(1.0, abs(float(sel["frontier_score"]))),
        "continuation": c01._jsonable(cont) == c01._jsonable(sel["continuation"]),
    }
    return {"frontier": fr, "state": st, "support": support, "raw": raw, "align": align, "counts": counts,
            "score": score, "direction": [dx, dy], "identity": identity}


def predicted_calibration(profile: str, gaze: tuple[float, float], head_r_wh: Any, head_origin_w: Any) -> dict[str, Any]:
    """The calibration of a proposed look from the known sensor model (the renderer's construction)."""
    return make_calibration(profile, float(gaze[0]), float(gaze[1]), float(frontier_config.VERGENCE_DISTANCE_M),
                            head_r_wh=np.asarray(head_r_wh, float), head_origin_w=np.asarray(head_origin_w, float))


def core_observability(calibration: dict[str, Any], xyz: np.ndarray) -> dict[str, Any]:
    """Whether 3-D points would be binocularly observable in a look's rectified depth cores.

    The accepted FSG6f patch test (``_target_patch_eye_evidence``, observable) in each eye, with the
    matcher's geometric rectification support cropped to the core.  It needs no image.
    """
    r = rectification(calibration)
    x, y, w, h = (int(v) for v in r["crop_xywh"])
    pts = np.asarray(xyz, float).reshape(-1, 3)
    out: dict[str, Any] = {}
    for side in ("L", "R"):
        uv, z = FR._project_rectified_core(calibration, pts, side)
        sup = support_mask(calibration, r, side)[y:y + h, x:x + w]
        ev = FR._target_patch_eye_evidence(np.zeros((h, w), np.int32), sup, FR.public.OBJECT_ID, uv, z)
        out[side] = {"observable": np.asarray(ev["observable"], bool), "core_uv": uv, "depth_m": z}
    out["both"] = out["L"]["observable"] & out["R"]["observable"]
    return out


def prior_binocular_interrogation(history: list[dict[str, Any]], xyz: np.ndarray) -> np.ndarray:
    """Whether a prior own look already tested each point binocularly (FSG6f's BOUNDARY test's ``both``)."""
    pts = np.asarray(xyz, float).reshape(-1, 3)
    seen = np.zeros(len(pts), bool)
    for obs in history:
        per = []
        for side in ("L", "R"):
            uv, z = FR._project_rectified_core(obs["calibration"], pts, side)
            per.append(FR._target_patch_eye_evidence(obs[f"instance_{side}"], obs[f"raw_support_{side}"],
                                                     FR.public.OBJECT_ID, uv, z)["observable"])
        seen |= np.asarray(per[0], bool) & np.asarray(per[1], bool)
    return seen


def serviceable_support(targets: np.ndarray, open_mask: np.ndarray, in_both: np.ndarray, prior: np.ndarray,
                        geometry: np.ndarray) -> dict[str, np.ndarray]:
    """Genuinely serviceable, non-redundant final obligations (the v1 counting rule)."""
    t = np.asarray(targets, float).reshape(-1, 3)
    mapped = FR._target_mapped_mask(t, geometry) if len(t) else np.zeros(0, bool)
    unresolved = np.asarray(open_mask, bool) & ~mapped
    serviceable = unresolved & np.asarray(in_both, bool)
    novel = serviceable & ~np.asarray(prior, bool)
    return {"mapped_12mm": mapped, "unresolved": unresolved, "serviceable": serviceable, "novel": novel}


def final_look_gate_v1(*, proposal: ic.ProbeResult, decision: dict[str, Any] | None, geometry: np.ndarray,
                       gaze: tuple[float, float], calibration: dict[str, Any], state: dict[str, np.ndarray],
                       history: list[dict[str, Any]], visited: list[tuple[float, float]], profile: str,
                       head_r_wh: Any, head_origin_w: Any, target_id: int) -> c2.FinalProbeDecision:
    """Admit the unchanged local proposal only if it would genuinely service unresolved support."""
    act = proposal.action
    if act is None:
        return c2.FinalProbeDecision(False, "no_local_proposal")
    base = {"proposal_source": act.source, "proposal_gaze_deg": list(act.gaze_yaw_pitch_deg)}
    if act.source != "fsg6f":
        return c2.FinalProbeDecision(False, "untraceable_final_support",
                                     {**base, "note": "v1 exposes traceable unresolved support only for FSG6f proposals"})
    if decision is None or decision.get("selected") is None or decision.get("next_gaze_deg") is None \
            or not _same_gaze(decision["next_gaze_deg"], act.gaze_yaw_pitch_deg, 0.0):
        return c2.FinalProbeDecision(False, "untraceable_final_support",
                                     {**base, "note": "no FSG6f decision matching the proposal"})
    if any(_same_gaze(act.gaze_yaw_pitch_deg, v) for v in visited):
        return c2.FinalProbeDecision(False, "visited_final_gaze", base)
    rec = reconstruct_support(decision, geometry, gaze, calibration, state, history, target_id)
    if not all(rec["identity"].values()):
        return c2.FinalProbeDecision(False, "support_identity_mismatch", {**base, "identity": rec["identity"]})
    idx = np.flatnonzero(rec["support"])
    fr = rec["frontier"]
    targets = fr["target_xyz_h"][idx]
    cal = predicted_calibration(profile, act.gaze_yaw_pitch_deg, head_r_wh, head_origin_w)
    core = core_observability(cal, targets)
    prior = prior_binocular_interrogation(history, targets)
    serv = serviceable_support(targets, rec["state"]["open"][idx], core["both"], prior, geometry)
    novel = int(serv["novel"].sum())
    detail = {
        **base,
        "support_counts_open_raw_map_boundary": rec["counts"], "direction": rec["direction"],
        "frontier_score": rec["score"], "identity": rec["identity"],
        "frontier_counts_raw_open_map_boundary": [int(rec["state"]["raw_count"]), int(rec["state"]["open_count"]),
                                                  int(rec["state"]["map_resolved_count"]),
                                                  int(rec["state"]["boundary_resolved_count"])],
        "current_gaze_deg": [float(gaze[0]), float(gaze[1])],
        "predicted_calibration": cal,
        "counts": {
            "support": int(len(idx)),
            "in_left_core": int(core["L"]["observable"].sum()), "in_right_core": int(core["R"]["observable"].sum()),
            "in_both_cores": int(core["both"].sum()),
            "unresolved_open_unmapped": int(serv["unresolved"].sum()),
            "mapped_within_12mm": int(serv["mapped_12mm"].sum()),
            "previously_interrogated": int(prior.sum()),
            "previously_interrogated_in_both_cores": int((prior & core["both"]).sum()),
            "serviceable": int(serv["serviceable"].sum()),
            "novel_service_count": novel,
        },
        "elements": [{
            "frontier_index": int(j), "x_e": fr["xyz_h"][j].tolist(), "t_e": fr["target_xyz_h"][j].tolist(),
            "x_yaw_pitch_deg": [float(fr["yaw_deg"][j]), float(fr["pitch_deg"][j])],
            "t_yaw_pitch_deg": [float(fr["target_yaw_deg"][j]), float(fr["target_pitch_deg"][j])],
            "core_uv_L": [float(v) for v in core["L"]["core_uv"][n]], "core_uv_R": [float(v) for v in core["R"]["core_uv"][n]],
            "in_left_core": bool(core["L"]["observable"][n]), "in_right_core": bool(core["R"]["observable"][n]),
            "in_both_cores": bool(core["both"][n]), "previously_interrogated": bool(prior[n]),
            "mapped_within_12mm": bool(serv["mapped_12mm"][n]), "novel": bool(serv["novel"][n]),
        } for n, j in enumerate(idx)],
    }
    if novel > 0:
        return c2.FinalProbeDecision(True, "novel_support_in_predicted_cores", detail)
    return c2.FinalProbeDecision(False, "no_novel_serviceable_support", detail)


# ---------------------------------------------------------------- accepted-evidence replay

class AcceptedReplay:
    """The frozen Controller-01 adapter driven by the accepted run's saved acquisitions."""

    def __init__(self, repo: Path, source: Path, work: Path) -> None:
        self.repo, self.source, self.work = Path(repo), Path(source), Path(work)
        self.manifest = json.loads((self.source / "manifest.json").read_text())
        self.accepted = json.loads((self.source / "actions.json").read_text())["actions"]
        self.seeds_doc = json.loads((self.source / "bootstrap/seeds.json").read_text())
        catalog_doc = json.loads((self.source / "bootstrap/instance_catalog.json").read_text())
        scene = self.repo / self.manifest["scene"]
        args = argparse.Namespace(blender="replay-never-launched", profile=self.manifest["profile"],
                                  device=self.manifest["device"], spp=self.manifest["spp_override"])
        self.run = c01.ClassroomController01(self.repo, self.work, scene, args, self.seeds_doc, catalog_doc)
        self.profile = str(self.seeds_doc["profile"])
        self.head_r_wh = self.seeds_doc["head_R_wh"]
        self.head_origin_w = self.seeds_doc["head_origin_w_m"]
        self.verified_steps = 0
        self.max_gaze_deviation = 0.0

    @contextmanager
    def _acquisition(self, src: Path, action: ic.Observe, local: int) -> Iterator[None]:
        original = c01._run

        def replay(cmd: list[str], log: Path, cwd: Path) -> None:
            arg = {cmd[k]: cmd[k + 1] for k in range(len(cmd) - 1) if cmd[k].startswith("--")}
            want = {"--mode": "fixation", "--yaw": str(action.gaze_yaw_pitch_deg[0]),
                    "--pitch": str(action.gaze_yaw_pitch_deg[1]), "--object-id": str(action.target_id),
                    "--step": str(local)}
            bad = {k: arg.get(k) for k, v in want.items() if arg.get(k) != v}
            if bad:
                raise ReplayDivergence(f"acquisition command differs from the replayed action: {bad}")
            out = Path(arg["--out"])
            for name in ("calibration.json", "oracle_observation.npz"):
                shutil.copyfile(src / name, out / name)
            Path(log).write_text(f"replayed accepted acquisition {src} (no render)\n")

        c01._run = replay
        try:
            yield
        finally:
            c01._run = original

    def observe(self, step: int, action: ic.Observe, local: int) -> ic.ObservationOutcome:
        if step >= len(self.accepted):
            raise NoAcceptedEvidence(f"action {step} ({action.source} {action.target_id} {list(action.gaze_yaw_pitch_deg)}) "
                                     "has no accepted sensory evidence; rendering is not authorized in this replay")
        acc = self.accepted[step]
        dev = max(abs(float(acc["gaze_deg"][k]) - float(action.gaze_yaw_pitch_deg[k])) for k in (0, 1))
        mismatch = {k: (a, b) for k, a, b in (
            ("target_id", int(acc["target_id"]), int(action.target_id)),
            ("action_source", acc["action_source"], action.source),
            ("object_local_step", int(acc["object_local_step"]), int(local)),
            ("global_step", int(acc["global_step"]), int(step))) if a != b}
        if dev > 1e-9:
            mismatch["gaze_deg"] = (acc["gaze_deg"], list(action.gaze_yaw_pitch_deg))
        if mismatch:
            raise ReplayDivergence(f"ordinary action {step} diverges from the accepted Controller-01 action: {mismatch}")
        self.max_gaze_deviation = max(self.max_gaze_deviation, dev)
        i = int(action.target_id)
        odir = f"objects/instance_{i:04d}"
        src = self.source / odir / "acquisitions" / f"fix_{local:02d}"
        with self._acquisition(src, action, local):
            outcome = self.run.observe(step, action, local)
        self._verify(step, i, local, outcome, acc)
        self._cleanup(i, local)
        self.verified_steps += 1
        return outcome

    def _verify(self, step: int, i: int, local: int, outcome: ic.ObservationOutcome, acc: dict[str, Any]) -> None:
        odir = f"objects/instance_{i:04d}"
        bad = [k for k in RECORD_FIELDS if c01._jsonable(outcome.record.get(k)) != acc.get(k)]
        mine = c01._load_npz(self.work / odir / "patches" / f"fix_{local:02d}.npz")
        saved = c01._load_npz(self.source / odir / "patches" / f"fix_{local:02d}.npz")
        if set(mine) != set(saved) or not all(_equal(mine[k], saved[k]) for k in saved):
            bad.append("patch")
        smap = self.source / odir / "maps" / f"fix_{local:02d}.npz"
        wmap = self.work / odir / "maps" / f"fix_{local:02d}.npz"
        if smap.exists() != wmap.exists():
            bad.append("map presence")
        elif smap.exists():
            a, b = c01._load_npz(wmap), c01._load_npz(smap)
            if set(a) != set(b) or not all(_equal(a[k], b[k]) for k in MAP_FIELDS):
                bad.append("map")
        if bad:
            raise ReplayDivergence(f"replayed step {step} (object {i}, local {local}) differs from the accepted run: {bad}")

    def _cleanup(self, i: int, local: int) -> None:
        odir = self.work / "objects" / f"instance_{i:04d}"
        shutil.rmtree(odir / "acquisitions" / f"fix_{local:02d}", ignore_errors=True)
        for p in (odir / "patches" / f"fix_{local:02d}.npz", odir / "maps" / f"fix_{local:02d}.npz",
                  odir / "benchmark" / f"fix_{local:02d}_L.png", odir / "benchmark" / f"fix_{local:02d}_R.png"):
            p.unlink(missing_ok=True)

    def final_gate(self, i: int, proposal: ic.ProbeResult) -> c2.FinalProbeDecision:
        """The strict final-look gate v1 over the object's current state (no later artifacts)."""
        run, ctx = self.run, self.run.ctx[i]
        decision = (run.decisions.get(i) or {}).get("fsg6f_decision")
        verdict = final_look_gate_v1(
            proposal=proposal, decision=decision, geometry=np.asarray(run.geometry(i), float), gaze=ctx.gaze,
            calibration=ctx.calibration, state=ctx.state, history=ctx.history, visited=list(ctx.visited),
            profile=self.profile, head_r_wh=self.head_r_wh, head_origin_w=self.head_origin_w, target_id=i)
        detail = {**dict(verdict.detail), "revision": list(run.revision(i)), "probe_summary": dict(proposal.detail)}
        return c2.FinalProbeDecision(verdict.admissible, verdict.reason, detail)


# ---------------------------------------------------------------- the experiment

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--source", required=True, help="the accepted Controller-01 full run")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    repo, source, out = Path(a.repo).resolve(), Path(a.source).resolve(), Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"output must be new or empty: {out}")
    hashes = {n: _sha(source / n) for n in ACCEPTED_SOURCE}
    if hashes != ACCEPTED_SOURCE:
        raise RuntimeError(f"the source is not the accepted Controller-01 run: {hashes}")
    firewall = ic.TruthFirewall(source, is_forbidden_during_replay)
    guard = NoProcessGuard()
    failure: str | None = None
    result: c2.Controller02Result | None = None
    t0 = time.perf_counter()
    with firewall, guard, tempfile.TemporaryDirectory(prefix="controller02-replay-") as work:
        replay = AcceptedReplay(repo, source, Path(work))
        run = replay.run
        unlocated = sorted(set(run.names) - set(run.seeds))
        try:
            result = c2.run_controller02(
                run.seeds, observe=replay.observe, probe=run.probe, revision=run.revision,
                final_gate=replay.final_gate, vergence=c01.VERGENCE, focus=c01.FOCUS, budget=BUDGET,
                unlocated=unlocated)
        except (ReplayDivergence, NoAcceptedEvidence) as exc:
            failure = f"{type(exc).__name__}: {exc}"
        except BaseException as exc:  # noqa: BLE001
            failure = f"{type(exc).__name__}: {exc}"
        names = dict(run.names)
        verified, max_dev = replay.verified_steps, replay.max_gaze_deviation
        timing = dict(run.timing)
    elapsed = time.perf_counter() - t0
    closed = result is not None and isinstance(result.terminal, c2.SceneClosed)
    ok = failure is None and not firewall.violations and not guard.attempts and result is not None
    marker = (SCENE_CLOSED_MARKER if closed else NOT_CLOSED_MARKER) if ok else None
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": SCHEMA, "contract": CONTRACT,
        "source_run": str(source), "source_hashes": hashes,
        "ordinary_service_budget": BUDGET, "vergence": c01.VERGENCE, "focus": c01.FOCUS,
        "replay": {"method": "frozen ClassroomController01.observe; Blender call replaced by the accepted acquisition",
                   "steps_verified": verified, "max_gaze_deviation_deg": max_dev,
                   "verified_fields": ["patch", "fused map", *RECORD_FIELDS]},
        "truth_firewall": {"forbidden": "evaluation.json, bootstrap/evaluation_only/*, " + ", ".join(LATER_ARTIFACTS),
                           "violations": list(firewall.violations), "opened_source_files": sorted(firewall.opened)},
        "process_guard": {"events": list(NoProcessGuard.EVENTS), "attempts": list(guard.attempts)},
        "failure": failure, "marker": marker, "global_quiescence_claimed": False,
        "timing_s": {"total": round(elapsed, 2), **{k: round(v, 2) for k, v in timing.items()}},
    }
    if result is not None:
        terminal = result.terminal
        final_states = {str(i): {"object_name": names.get(i, str(i)), "local_state": s.local.value,
                                 "disposition": s.disposition.value, "reason": s.reason,
                                 "fixations": int(result.fixations[i])} for i, s in sorted(result.final.items())}
        summary: dict[str, Any] = {
            "terminal": {"type": "SCENE_CLOSED", **c01._jsonable(terminal.__dict__)} if closed
            else {"type": "CAP", **c01._jsonable(terminal.__dict__)},
            "localized_objects": len(result.final), "initialized_objects": len(result.initialized),
            "unlocated_objects": len(unlocated), "ordinary_observations": sum(1 for x in result.actions if x["phase"] == "NORMAL"),
            "final_residue_observations": sum(1 for x in result.actions if x["phase"] == "RESIDUE"),
            "probe_calls": result.probe_calls, "probe_cache_hits": result.probe_cache_hits,
            "phases": result.phases, "final_states": final_states,
        }
        if closed:
            summary.update({"quiet": list(terminal.quiet), "residual": [list(r) for r in terminal.residual],
                            "seed_residues": list(terminal.seed_residues), "unlocated": list(terminal.unlocated),
                            "final_observations": list(terminal.final_observations),
                            "final_rejections": list(terminal.final_rejections)})
        manifest["summary"] = summary
        c01._write_json(out / "actions.json", {"schema": SCHEMA, "actions": result.actions})
        c01._write_json(out / "events.json", {"schema": SCHEMA, "events": result.events})
        c01._write_json(out / "final-residue.json", {"schema": SCHEMA, "residue_decisions": result.residue_decisions,
                                                     "phases": result.phases})
        c01._write_json(out / "result.json", {"schema": SCHEMA, "marker": marker, **summary})
    c01._write_json(out / "manifest.json", manifest)
    if marker is None:
        print(f"[controller02] STOPPED: {failure or firewall.violations or guard.attempts} (no scientific marker)")
        return 1
    s = manifest["summary"]
    print(f"[controller02] ordinary observations {s['ordinary_observations']} (verified {verified}); final residue "
          f"observations {s['final_residue_observations']}; terminal {s['terminal']['type']}")
    if closed:
        print(f"[controller02] quiet {len(s['quiet'])}, residual {s['residual']}, seed residues {s['seed_residues']}, "
              f"unlocated {len(s['unlocated'])}, final rejections {s['final_rejections']}")
    print(f"[controller02] RESULT {marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
