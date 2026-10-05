"""Active Bootstrap-1c: safe-forward planar vs spherical geometry (run order and truth boundary).

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1c_run.py synthetic             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py rehearse              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py select                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-selection      --run RUN
    (check_ab1c.py --stage selection --run RUN --visuals VIS --write-summary)
    .venv/bin/python tools/active_bootstrap/ab1c_run.py plan                  --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py preflight             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py acquire               --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py oracle                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py planar                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py compare               --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py evaluate              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1c_run.py visualize             --run RUN --visuals VIS

``select`` reads only the frozen NB1c attention raster; ``acquire`` renders exactly one binocular pair per frozen gaze;
``oracle`` alone reads Position / Object Index and writes one truth-stripped product per gaze, frozen by
``freeze-correspondence``; ``spherical`` and ``planar`` read only the calibration and that product; ``freeze-geometry``
freezes both; ``compare`` (truth-free) measures their direct agreement; only then ``evaluate`` reopens Position
(REFERENCE / EVALUATION).  This module does not import cv2: the planar module is imported only by ``planar``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as BG  # noqa: E402  (accepted spherical geometry, read-only)
import ab1b_oracle as BO  # noqa: E402  (accepted oracle, read-only)
import ab1c_select as SEL  # noqa: E402
import ab1c_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1c]"
RENDER_SCRIPT = HERE / "ab1c_render.py"
sha256 = SEL.sha256
write_json = SEL.write_json


def read_json(path):
    return json.loads(Path(path).read_text())


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def code_state() -> dict:
    head = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no")
                 or git("status", "--porcelain", "--", "tools", "docs", "fov3d", "scripts"))
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    try:
        pushed = git("rev-parse", f"origin/{branch}") == head
    except subprocess.CalledProcessError:
        pushed = False
    return {"commit": head, "dirty": dirty, "branch": branch, "pushed": pushed}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def log_process(run: Path, command: str, t0: float, status: str, extra: dict | None = None) -> None:
    run.mkdir(parents=True, exist_ok=True)
    entry = {"command": command, "argv": sys.argv, "executable": sys.executable, "code": code_state(),
             "finished_utc": utc(), "seconds": round(time.time() - t0, 3), "status": status, **(extra or {})}
    with open(run / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def require_committed(what: str) -> dict:
    cs = code_state()
    if cs["dirty"] or not cs["pushed"]:
        raise SystemExit(f"{PREFIX} STOP {what} runs only from a clean, pushed implementation commit: {cs}")
    return cs


def once(path: Path, what: str) -> None:
    if path.exists():
        raise SystemExit(f"{PREFIX} STOP {what} exists ({path}); it is made once")


def need(path: Path, what: str) -> None:
    if not Path(path).is_file():
        raise SystemExit(f"{PREFIX} STOP {what} comes first ({path} missing)")


def verify_sources() -> None:
    bad = {p: sha256(REPO / p) for p, h in SP.SOURCE_PINS.items() if sha256(REPO / p) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")


def obs(run: Path, g: str, rel: str) -> Path:
    return run / "observations" / g / rel


def calib(run: Path, g: str) -> Path:
    return obs(run, g, "acquisition/calibration.json")


def reference(run: Path, g: str) -> Path:
    return obs(run, g, "evaluation_only/reference-observation.npz")


def product(run: Path, g: str) -> Path:
    return run / "oracle" / g / "oracle-correspondences.npz"


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


# ------------------------------------------------------------------ source (section 2)
def source(run: Path) -> dict:
    out = run / "source/source-manifest.json"
    once(out, "the source manifest")
    verify_sources()
    import ab1a_spec as AS
    import nb1a_spec as NA
    import nb1c_spec as NS
    remote = git("remote", "get-url", "origin")
    fz, man = read_json(SP.NB1C_FREEZE[0]), read_json(SP.NB1C_MANIFEST[0])
    d = np.ascontiguousarray(NA.cell_directions_h(), np.float64)
    ident = {
        "canonical_remote": remote.rstrip("/").removesuffix(".git").endswith(SP.CANONICAL_REMOTE),
        "nb1c_freeze": sha256(SP.NB1C_FREEZE[0]) == SP.NB1C_FREEZE[1],
        "nb1c_manifest": sha256(SP.NB1C_MANIFEST[0]) == SP.NB1C_MANIFEST[1],
        "attention": sha256(SP.ATTENTION[0]) == SP.ATTENTION[1],
        "attention_in_freeze": fz["files"].get("attention-score.npz") == SP.ATTENTION[1],
        "attention_in_manifest": man["files"].get("selection/attention-score.npz") == SP.ATTENTION[1],
        "grid_in_freeze": fz["grid"]["directions_sha256"] == SP.GRID_DIRECTIONS_SHA256,
        "grid_recomputed": hashlib.sha256(d.tobytes()).hexdigest() == SP.GRID_DIRECTIONS_SHA256,
        "head_pose": sha256(SP.HEAD_POSE_SOURCE[0]) == SP.HEAD_POSE_SOURCE[1],
        "blend": sha256(REPO / SP.BLEND) == SP.BLEND_SHA256,
        "accepted_products": all(sha256(p) == h for p, h in SP.ACCEPTED_PRODUCTS.values()),
        "nb1c_constants": (NS.D_MIN_RAD == SP.D_MIN_RAD and NS.ANGLE_EPS_RAD == SP.ANGLE_EPS_RAD
                           and NS.SCORE_TIE_REL == SP.SCORE_TIE_REL and NS.WIDTH == SP.WIDTH and NS.HEIGHT == SP.HEIGHT),
        "instrument": (AS.PROFILE == SP.PROFILE and AS.RAW_SIZE == SP.RAW_SIZE and AS.CORE_SIZE == SP.CORE_SIZE
                       and AS.IPD_M == SP.IPD_M and AS.VERGENCE_M == SP.VERGENCE_M and AS.TANGENT_FRAME == SP.TANGENT_FRAME
                       and AS.DEVICE == SP.DEVICE and AS.SPP == SP.SPP and AS.SEEDS == SP.SEEDS
                       and AS.HEAD_POSE_SOURCE == SP.HEAD_POSE_SOURCE and AS.BLEND_SHA256 == SP.BLEND_SHA256
                       and FG.CORE_FOV_DEG == 12.0 and FG.CORE_SIZE[SP.PROFILE] == SP.CORE_SIZE),
    }
    if not all(ident.values()):
        raise SystemExit(f"{PREFIX} STOP source identity: {ident}")
    rec = {"schema": "AB1c-source-manifest-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
           "statement": "pinned sources verified; the only selection input is the frozen NB1c attention raster",
           "remote": remote, "identity": ident, "attention": {"path": str(SP.ATTENTION[0]), "sha256": SP.ATTENTION[1]},
           "nb1c_freeze": {"path": str(SP.NB1C_FREEZE[0]), "sha256": SP.NB1C_FREEZE[1]},
           "nb1c_manifest": {"path": str(SP.NB1C_MANIFEST[0]), "sha256": SP.NB1C_MANIFEST[1]},
           "grid_directions_sha256": SP.GRID_DIRECTIONS_SHA256,
           "head_pose_source": {"path": str(SP.HEAD_POSE_SOURCE[0]), "sha256": SP.HEAD_POSE_SOURCE[1]},
           "blend": {"path": SP.BLEND, "sha256": SP.BLEND_SHA256}, "source_pins": SP.SOURCE_PINS,
           "accepted_products": {k: {"path": str(p), "sha256": h} for k, (p, h) in SP.ACCEPTED_PRODUCTS.items()},
           "base_commit": SP.BASE_COMMIT, "code": code_state(), "created_utc": utc()}
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, rec)
    print(f"{PREFIX} source: {len(SP.SOURCE_PINS)} code pins, NB1c attention {SP.ATTENTION[1][:12]}, accepted products "
          f"and canonical remote verified")
    return rec


# ------------------------------------------------------------------ selection (sections 4-5)
def select(run: Path) -> dict:
    once(run / "selection/selected-gazes.json", "the selection")
    need(run / "source/source-manifest.json", "source")
    verify_sources()
    summ = SEL.run_select(SP.ATTENTION[0], run / "selection")
    rec = read_json(run / "selection/selection-opened-files.json")
    if rec["violations"] or rec["data_reads"] != [str(SP.ATTENTION[0])] or any(rec["modules_loaded"].values()):
        raise SystemExit(f"{PREFIX} STOP selection guard: reads {rec['data_reads']}; violations {rec['violations']}; "
                         f"modules {rec['modules_loaded']}")
    print(f"{PREFIX} select: cone {summ['cells_in_cone']:,} cells, eligible {summ['cells_eligible']:,} "
          f"(leverage removed {summ['cone_cells_failing_leverage']:,}); boundary margins {summ['boundary_margins']}")
    for g in read_json(run / "selection/selected-gazes.json")["gazes"]:
        print(f"{PREFIX} select: #{g['rank']} row {g['row']} col {g['col']} ({g['yaw_deg']:+.2f}, {g['pitch_deg']:+.2f}) "
              f"A {g['A']:.6f}; alpha_forward {g['alpha_forward_deg']:.3f} deg; L_center {g['L_center']:.4f}; "
              f"min-core L {g['min_core_leverage_L']:.4f} / {g['min_core_leverage_R']:.4f}; eligible before "
              f"{g['eligible_before']:,}; ties {g['tie_set_size']}; suppressed {g['nms_suppressed']:,}")
    return summ


def freeze_selection(run: Path) -> dict:
    path = run / "selection/safe-forward-freeze.json"
    once(path, "the selection freeze")
    for n in SP.SELECTION_FILES:
        need(run / n, n)
    rec = read_json(run / "selection/selection-opened-files.json")
    if rec["violations"] or rec["data_reads"] != [str(SP.ATTENTION[0])]:
        raise SystemExit(f"{PREFIX} STOP selection reads {rec['data_reads']}; violations {rec['violations']}")
    gz = read_json(run / "selection/selected-gazes.json")["gazes"]
    if len(gz) != SP.K:
        raise SystemExit(f"{PREFIX} STOP {len(gz)} gazes, not K = {SP.K}")
    fz = {"schema": "AB1c-safe-forward-freeze-v1", "truth": SP.TRUTH_DERIVED, "label": SP.SELECTION_LABEL,
          "statement": "the three SAFE-FORWARD gazes are frozen here, before any render; no replacement later",
          "files": {n: sha256(run / n) for n in SP.SELECTION_FILES},
          "source_manifest_sha256": sha256(run / "source/source-manifest.json"),
          "attention": {"path": str(SP.ATTENTION[0]), "sha256": sha256(SP.ATTENTION[0])},
          "selection_config_sha256": SP.config_sha256(SP.SELECTION),
          "selection_code": {n: sha256(REPO / n) for n in SP.SELECT_CODE},
          "gazes": [{k: g[k] for k in ("rank", "row", "col", "yaw_deg", "pitch_deg")} for g in gz],
          "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-selection: {len(fz['files'])} files hashed; gazes "
          + ", ".join(f"#{g['rank']} ({g['yaw_deg']:+.2f}, {g['pitch_deg']:+.2f})" for g in fz["gazes"]))
    return fz


def verify_selection_freeze(run: Path) -> dict:
    fz = read_json(run / "selection/safe-forward-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != set(SP.SELECTION_FILES) or sha256(SP.ATTENTION[0]) != SP.ATTENTION[1]:
        raise SystemExit(f"{PREFIX} STOP the selection freeze does not verify: {bad}")
    return fz


def frozen_gazes(run: Path) -> list[dict]:
    return verify_selection_freeze(run)["gazes"]


def plan(run: Path) -> dict:
    once(run / "plan/plan-record.json", "the plan")
    fz = verify_selection_freeze(run)
    chk = run / "selection/selection-check.json"
    need(chk, "check_ab1c.py --stage selection --write-summary")
    cr = read_json(chk)
    if not cr.get("passed") or cr.get("selection_freeze_sha256") != sha256(run / "selection/safe-forward-freeze.json"):
        raise SystemExit(f"{PREFIX} STOP the independent selection check did not pass on this freeze")
    if sha256(SP.HEAD_POSE_SOURCE[0]) != SP.HEAD_POSE_SOURCE[1]:
        raise SystemExit(f"{PREFIX} STOP accepted head-pose record changed")
    pose = read_json(SP.HEAD_POSE_SOURCE[0])
    rows = []
    for g, gz in zip(SP.GAZES, fz["gazes"]):
        c = FG.make_calibration(SP.PROFILE, gz["yaw_deg"], gz["pitch_deg"], SP.VERGENCE_M, ipd=SP.IPD_M,
                                head_r_wh=np.asarray(pose["head_R_wh"]), head_origin_w=np.asarray(pose["head_origin_w_m"]),
                                tangent_frame=SP.TANGENT_FRAME)
        s = SEL.selection_calibration(gz["yaw_deg"], gz["pitch_deg"])
        same = json.dumps(c["eyes"], sort_keys=True) == json.dumps(s["eyes"], sort_keys=True)
        if not same:
            raise SystemExit(f"{PREFIX} STOP {g}: the planned head-frame eye geometry differs from the selection's")
        out = run / "plan" / g
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / "planned-calibration.json", c)
        rows.append({"gaze": g, **gz, "planned_calibration_sha256": sha256(out / "planned-calibration.json"),
                     "head_frame_eyes_equal_selection": same})
    rec = {"schema": "AB1c-plan-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "planned calibrations of the three frozen gazes with the accepted head pose; the head-frame eye "
                        "geometry equals the selection's exactly",
           "selection_freeze_sha256": sha256(run / "selection/safe-forward-freeze.json"),
           "selection_check_sha256": sha256(chk), "head_pose_source": {"path": str(SP.HEAD_POSE_SOURCE[0]),
                                                                       "sha256": SP.HEAD_POSE_SOURCE[1]},
           "gazes": rows, "code": code_state(), "created_utc": utc()}
    write_json(run / "plan/plan-record.json", rec)
    print(f"{PREFIX} plan: 3 planned calibrations; head-frame eyes equal the selection's")
    return rec


# ------------------------------------------------------------------ Blender (section 6)
def blender(run: Path, mode: str, blend: Path | None, log: Path) -> dict:
    argv = [SP.BLENDER, "-b"] + ([str(blend)] if blend else ["--factory-startup"]) + [
        "--python-exit-code", "1", "-P", str(RENDER_SCRIPT), "--", "--mode", mode, "--run", str(run),
        "--head-pose", str(SP.HEAD_POSE_SOURCE[0])]
    t0 = time.time()
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout + proc.stderr)
    ok = proc.returncode == 0 and f"[ab1c-render] COMPLETE {mode}" in proc.stdout
    return {"blender": {"mode": mode, "argv": argv, "returncode": proc.returncode, "seconds": round(time.time() - t0, 3),
                        "complete_marker": ok, "log": str(log)}}


def preflight(run: Path) -> dict:
    once(run / "preflight/preflight.json", "the preflight")
    need(run / "plan/plan-record.json", "plan")
    verify_selection_freeze(run)
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "preflight", REPO / SP.BLEND, run / "logs/preflight-blender.log")
    if not res["blender"]["complete_marker"]:
        raise SystemExit(f"{PREFIX} STOP preflight failed; see {res['blender']['log']}")
    pf = read_json(run / "preflight/preflight.json")
    print(f"{PREFIX} preflight: no render; EYE pose diff {pf['eye_pose']['max_abs_diff_from_accepted']}; calibration "
          f"diffs {[v['calibration_max_abs_diff_from_planned'] for v in pf['gazes'].values()]}")
    return res


def exr_passes(channels: list[str]) -> set:
    """Pass names of 'viewlayer.pass.channel' EXR channel names (the accepted AB1a rule)."""
    return {".".join(ch.split(".")[1:-1]) for ch in channels}


def verify_observations(run: Path) -> list[str]:
    problems = []
    for g in SP.GAZES:
        acq = obs(run, g, "acquisition")
        with np.load(acq / "rgb-observation.npz") as z:
            names = sorted(z.files)
        a = read_json(acq / "acquisition.json")
        diff = _calib_diff(read_json(run / "plan" / g / "planned-calibration.json"), read_json(acq / "calibration.json"))
        if names != ["rgb_L", "rgb_R"]:
            problems.append(f"{g} rgb arrays {names}")
        if not diff <= SP.CALIBRATION_TOL:
            problems.append(f"{g} calibration differs from planned by {diff}")
        if (a["device"], a["spp"], a["render_seeds_lr"]) != (SP.DEVICE, SP.SPP, SP.SEEDS):
            problems.append(f"{g} settings {a['device']} {a['spp']} {a['render_seeds_lr']}")
        if a["rgb_observation_sha256"] != sha256(acq / "rgb-observation.npz"):
            problems.append(f"{g} rgb observation hash")
        pl, pr = exr_passes(a["exr_channels_lr"]["L"]), exr_passes(a["exr_channels_lr"]["R"])
        want = set(SP.REQUIRED_PASSES) | set(SP.INHERITED_PASSES)
        if pl != pr or pl != want:
            problems.append(f"{g} EXR passes L {sorted(pl)} R {sorted(pr)}")
    return problems


def acquire(run: Path) -> dict:
    require_committed("acquire")
    o = run / "observations"
    if o.exists() and any(o.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {o} exists: each frozen gaze is observed once")
    need(run / "preflight/preflight.json", "preflight")
    need(run / "plan/plan-record.json", "plan")
    verify_selection_freeze(run)
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "canonical", REPO / SP.BLEND, run / "logs/acquire-blender.log")
    if not res["blender"]["complete_marker"]:
        print(f"{PREFIX} STOP the canonical acquisition failed; see {res['blender']['log']}. It is NOT retried: a second "
              f"acquisition is a decision for Luiz and Chat.")
        return res
    problems = verify_observations(run)
    if problems:
        raise SystemExit(f"{PREFIX} STOP acquisition verification: {problems}")
    for g in SP.GAZES:
        a = read_json(obs(run, g, "acquisition/acquisition.json"))
        print(f"{PREFIX} acquire {g}: gaze {a['gaze_yaw_pitch_deg']}; {a['device']} {a['spp']} spp; seeds "
              f"{a['render_seeds_lr']}; render seconds {a['render_seconds_lr']}; rgb {a['rgb_observation_sha256'][:12]}")
    return res


def _calib_diff(a, b) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        return max([_calib_diff(a[k], b[k]) for k in a] or [0.0]) if set(a) == set(b) else math.inf
    if isinstance(a, list) and isinstance(b, list):
        return max([_calib_diff(x, y) for x, y in zip(a, b)] or [0.0]) if len(a) == len(b) else math.inf
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b))
    return 0.0 if a == b else math.inf


# ------------------------------------------------------------------ oracle + correspondence freeze (section 7)
def run_oracle_gaze(calib_path: Path, ref_path: Path, out_dir: Path) -> dict:
    """The accepted AB1b oracle (``compute_oracle``, read-only) under an AB1c guard: exactly two data reads."""
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1c-oracle", [calib_path, ref_path], [out_dir])
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "reference_observation": {"path": str(ref_path), "sha256": sha256(ref_path)}}
            c = read_json(calib_path)
            ref = BO.load_reference(ref_path)
            prod, summ = BO.compute_oracle(c, ref)
            np.savez_compressed(out_dir / "oracle-correspondences.npz", **prod)
            summary = {"schema": "AB1c-oracle-summary-v1", "truth": SP.TRUTH_DERIVED,
                       "statement": "PERFECT / ORACLE CORRESPONDENCE (accepted AB1b oracle): Position and Object Index "
                                    "were used here, and only here; the ONE shared product holds core row / col and "
                                    "continuous uv_L / uv_R only, and feeds BOTH the planar and the spherical geometry",
                       "oracle": BO.SP.ORACLE, "oracle_config_sha256": BO.SP.config_sha256(BO.SP.ORACLE),
                       "inputs": inputs, "product_keys": sorted(prod), **summ}
            write_json(out_dir / "oracle-summary.json", summary)
    finally:
        rec = g.record()
        rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1c_planar")}
        rec["truth_firewall_violations"] = len(rec["violations"])
        write_json(out_dir / "oracle-opened-files.json", rec)
    return summary


def oracle(run: Path) -> dict:
    once(run / "oracle" / SP.GAZES[0] / "oracle-correspondences.npz", "the oracle products")
    need(run / "preflight/preflight.json", "preflight")
    for g in SP.GAZES:
        need(calib(run, g), f"the {g} observation")
    verify_sources()
    out = {}
    for g in SP.GAZES:
        summ = run_oracle_gaze(calib(run, g), reference(run, g), run / "oracle" / g)
        rec = read_json(run / "oracle" / g / "oracle-opened-files.json")
        if rec["violations"] or any(rec["modules_loaded"].values()):
            raise SystemExit(f"{PREFIX} STOP {g} oracle guard: {rec['violations']}; modules {rec['modules_loaded']}")
        a = " -> ".join(f"{x['remaining']:,}" for x in summ["attrition"])
        print(f"{PREFIX} oracle {g}: {summ['correspondences']:,} perfect correspondences ({summ['fraction_of_core']:.4f}); "
              f"attrition {a}; outside right nominal core {summ['right_margin']['outside_right_nominal_core']:,}")
        out[g] = summ
    return out


def corr_files(g: str) -> list[str]:
    return [f"oracle/{g}/oracle-correspondences.npz", f"oracle/{g}/oracle-summary.json",
            f"oracle/{g}/oracle-opened-files.json"]


def freeze_correspondence(run: Path) -> dict:
    path = run / "oracle/correspondence-freeze.json"
    once(path, "the correspondence freeze")
    files, inputs = {}, {}
    for g in SP.GAZES:
        for n in corr_files(g):
            need(run / n, n)
        rec = read_json(run / "oracle" / g / "oracle-opened-files.json")
        want = {str(calib(run, g).resolve()), str(reference(run, g).resolve())}
        if rec["violations"] or set(rec["data_reads"]) != want:
            raise SystemExit(f"{PREFIX} STOP {g} oracle reads {rec['data_reads']}; violations {rec['violations']}")
        files.update({n: sha256(run / n) for n in corr_files(g)})
        inputs[g] = {"calibration": {"path": str(calib(run, g)), "sha256": sha256(calib(run, g))},
                     "reference_observation": {"path": str(reference(run, g)), "sha256": sha256(reference(run, g))}}
    fz = {"schema": "AB1c-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "the three truth-stripped shared correspondence products, frozen before either geometry runs",
          "files": files, "oracle_inputs": inputs, "oracle_code": {n: sha256(REPO / n) for n in SP.ORACLE_CODE},
          "oracle_config_sha256": BO.SP.config_sha256(BO.SP.ORACLE), "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-correspondence: {len(files)} files hashed")
    return fz


def verify_correspondence_freeze(run: Path) -> dict:
    fz = read_json(run / "oracle/correspondence-freeze.json")
    want = {n for g in SP.GAZES for n in corr_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the correspondence freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ spherical geometry (section 8)
def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref)}


def run_spherical_gaze(calib_path: Path, product_path: Path, out_dir: Path, freeze_path: Path) -> dict:
    """The accepted AB1b spherical geometry (read-only) under an AB1c guard: exactly two data reads, no cv2."""
    if not Path(freeze_path).exists():
        raise RuntimeError("the correspondence product is not frozen")
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1c-spherical", [calib_path, product_path], [out_dir])
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "correspondences": {"path": str(product_path), "sha256": sha256(product_path)}}
            c = read_json(calib_path)
            FG.validate_calibration(c)
            prod = BG.load_product(product_path)
            rays = BG.left_core_rays(c)
            res = BG.compute_epipolar(c, prod)
            np.savez_compressed(out_dir / "left-core-rays.npz", **rays)
            np.savez_compressed(out_dir / "epipolar-result.npz", **res)
            summary = {"schema": "AB1c-spherical-summary-v1", "truth": SP.TRUTH_DERIVED,
                       "statement": "TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (accepted AB1b geometry): the "
                                    "calibration and the frozen shared product only; no Position, Object Index or truth "
                                    "XYZ; no planar rectification",
                       "geometry": BG.SP.GEOMETRY, "geometry_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
                       "inputs": inputs, "baseline_m": float(c["ipd_m"]), "focal_px": float(c["eyes"][0]["K"][0][0]),
                       **BG.summarize(c, rays, res)}
            write_json(out_dir / "spherical-summary.json", summary)
    finally:
        rec = g.record()
        rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1c_planar")}
        rec.update(truth_reads(rec["events"]))
        rec["truth_firewall_violations"] = len(rec["violations"])
        write_json(out_dir / "spherical-opened-files.json", rec)
    return summary


def spherical(run: Path) -> dict:
    once(run / "spherical" / SP.GAZES[0] / "epipolar-result.npz", "the spherical geometry")
    need(run / "oracle/correspondence-freeze.json", "freeze-correspondence")
    verify_sources()
    out = {}
    for g in SP.GAZES:
        summ = run_spherical_gaze(calib(run, g), product(run, g), run / "spherical" / g,
                                  run / "oracle/correspondence-freeze.json")
        rec = read_json(run / "spherical" / g / "spherical-opened-files.json")
        if rec["violations"] or any(rec["modules_loaded"].values()) or rec["position_reads"]:
            raise SystemExit(f"{PREFIX} STOP {g} spherical guard: {rec['violations']}; modules {rec['modules_loaded']}")
        k, dd = summ["counts"], summ["distributions"]
        ph = dd["abs_phi_residual_rad"]
        print(f"{PREFIX} spherical {g}: triangulated {k['triangulated_epipolar']:,}/{k['correspondences']:,}; |phi res| "
              f"max {ph['max'] if ph else float('nan'):.3e}; kappa median "
              f"{dd['kappa']['median'] if dd['kappa'] else float('nan'):.1f}; truth reads 0")
        out[g] = summ
    return out


# ------------------------------------------------------------------ planar geometry (section 9)
def planar(run: Path) -> dict:
    once(run / "planar" / SP.GAZES[0] / "planar-result.npz", "the planar geometry")
    need(run / "oracle/correspondence-freeze.json", "freeze-correspondence")
    verify_sources()
    import ab1c_planar as PL
    out = {}
    for g in SP.GAZES:
        summ = PL.run_planar(calib(run, g), product(run, g), run / "planar" / g, run / "oracle/correspondence-freeze.json")
        rec = read_json(run / "planar" / g / "planar-opened-files.json")
        if rec["violations"] or rec["position_reads"]:
            raise SystemExit(f"{PREFIX} STOP {g} planar guard: {rec['violations']}")
        sup = read_json(run / "planar" / g / "planar-support.json")["eyes"]["L"]
        k = summ["counts"]
        print(f"{PREFIX} planar {g}: valid {k['valid_planar']:,}/{k['correspondences']:,}; R1 rotation "
              f"{summ['rectification']['R1_rotation_deg']:.3f} deg; rectified core from nominal "
              f"{sup['rectified_core_pixels_from_nominal_raw_core']:,}; centre {sup['rectified_core_centre_from_gaze_deg']:.3f} "
              f"deg from gaze, {sup['rectified_core_centre_from_baseline_deg']:.3f} deg from baseline")
        out[g] = summ
    return out


# ------------------------------------------------------------------ geometry freeze (section 10)
def geom_files(g: str) -> list[str]:
    return [f"spherical/{g}/left-core-rays.npz", f"spherical/{g}/epipolar-result.npz",
            f"spherical/{g}/spherical-summary.json", f"spherical/{g}/spherical-opened-files.json",
            f"planar/{g}/planar-result.npz", f"planar/{g}/planar-support.json", f"planar/{g}/planar-summary.json",
            f"planar/{g}/planar-opened-files.json"]


def freeze_geometry(run: Path) -> dict:
    path = run / "freeze/geometry-freeze.json"
    once(path, "the geometry freeze")
    for g in SP.GAZES:
        for n in geom_files(g):
            need(run / n, n)
    (run / "freeze").mkdir(parents=True, exist_ok=True)
    reads = ([run / "oracle/correspondence-freeze.json"] + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
             + [calib(run, g) for g in SP.GAZES])
    with OpenGuard("ab1c-freeze-geometry", reads, [run / "freeze"]) as gd:
        cfz = verify_correspondence_freeze(run)
        pre, files = {}, {}
        for g in SP.GAZES:
            cs = sha256(calib(run, g))
            ps = cfz["files"][f"oracle/{g}/oracle-correspondences.npz"]
            want = {str(calib(run, g).resolve()), str(product(run, g).resolve())}
            sr, pr = (read_json(run / f"{s}/{g}/{s}-opened-files.json") for s in ("spherical", "planar"))
            ss, psm = (read_json(run / f"{s}/{g}/{s}-summary.json") for s in ("spherical", "planar"))
            p = {"spherical_reads_exactly_two": set(sr["data_reads"]) == want,
                 "planar_reads_exactly_two": set(pr["data_reads"]) == want,
                 "violations_0": not sr["violations"] and not pr["violations"],
                 "position_reads_0": sr["position_reads"] == 0 and pr["position_reads"] == 0,
                 "object_index_reads_0": sr["object_index_reads"] == 0 and pr["object_index_reads"] == 0,
                 "spherical_no_cv2_no_planar": not any(sr["modules_loaded"].values()),
                 "same_product": ss["inputs"]["correspondences"]["sha256"] == psm["inputs"]["correspondences"]["sha256"] == ps,
                 "same_calibration": (ss["inputs"]["calibration"]["sha256"] == psm["inputs"]["calibration"]["sha256"] == cs
                                      == cfz["oracle_inputs"][g]["calibration"]["sha256"])}
            if not all(p.values()):
                raise SystemExit(f"{PREFIX} STOP {g} geometry freeze preconditions: {p}")
            pre[g] = p
            files.update({n: sha256(run / n) for n in [f"oracle/{g}/oracle-correspondences.npz"] + geom_files(g)})
        fz = {"schema": "AB1c-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "GEOMETRY FREEZE: both truth-free geometries (planar and spherical) of all three gazes, frozen "
                           "before the comparison and before any Position truth is reopened",
              "files": files, "calibrations": {g: {"path": str(calib(run, g)), "sha256": sha256(calib(run, g))}
                                               for g in SP.GAZES},
              "correspondence_freeze_sha256": sha256(run / "oracle/correspondence-freeze.json"),
              "spherical_code": {n: sha256(REPO / n) for n in SP.SPHERICAL_CODE},
              "planar_code": {n: sha256(REPO / n) for n in SP.PLANAR_CODE},
              "spherical_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY),
              "planar_config_sha256": SP.config_sha256(SP.PLANAR), "preconditions": pre,
              "code": code_state(), "frozen_utc": utc()}
        write_json(path, fz)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(run / "freeze/geometry-freeze-opened-files.json", rec)
    print(f"{PREFIX} freeze-geometry: {len(files)} files hashed; both geometries read exactly the calibration and the "
          f"shared product; Position / Object Index reads 0")
    return fz


def verify_geometry_freeze(run: Path) -> dict:
    fz = read_json(run / "freeze/geometry-freeze.json")
    want = {n for g in SP.GAZES for n in [f"oracle/{g}/oracle-correspondences.npz"] + geom_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    bad += [g for g, v in fz["calibrations"].items() if sha256(v["path"]) != v["sha256"]]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the frozen geometry does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ comparison (section 11, PRIMARY; truth-free)
def q(a, mask=None):
    return BG.quantiles(a, mask)


def compare_core(c: dict, sph: dict, pla: dict) -> tuple[dict, dict]:
    """Direct planar vs spherical agreement over the common valid set of ONE shared product."""
    for k in ("left_core_row", "left_core_col"):
        if not np.array_equal(np.asarray(sph[k]), np.asarray(pla[k])):
            raise ValueError("planar and spherical results do not carry the same pair identity")
    ve, vp = np.asarray(sph["valid_epi"], bool), np.asarray(pla["valid_planar"], bool)
    common = ve & vp
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    ps, pp = np.asarray(sph["P_epi"], np.float64), np.asarray(pla["P_planar"], np.float64)
    with np.errstate(invalid="ignore"):
        dvec = np.where(common[:, None], pp - ps, np.nan)
        diff = np.linalg.norm(dvec, axis=-1)
        rs = np.linalg.norm(ps - o_l, axis=-1)
        rad = np.where(common, np.linalg.norm(pp - o_l, axis=-1) - rs, np.nan)
        rel = np.where(common, diff / rs, np.nan)
    summary = {"counts": {"raw_core_pixels": SP.CORE_SIZE * SP.CORE_SIZE, "correspondences": int(common.size),
                          "planar_valid": int(vp.sum()), "spherical_valid": int(ve.sum()),
                          "common_valid": int(common.sum()), "planar_only": int((vp & ~ve).sum()),
                          "spherical_only": int((ve & ~vp).sum())},
               "planar_minus_spherical_m": q(diff, common), "radial_signed_planar_minus_spherical_m": q(rad, common),
               "relative_difference": q(rel, common)}
    arrays = {"left_core_row": np.asarray(sph["left_core_row"], np.int32),
              "left_core_col": np.asarray(sph["left_core_col"], np.int32), "common": common,
              "delta_planar_minus_spherical_m": dvec, "difference_m": diff, "radial_signed_m": rad,
              "relative_difference": rel}
    return summary, arrays


def consistency_control(c: dict, sph: dict, prod: dict) -> dict | None:
    """Truth-free descriptive control (contract section 23): the point on the LEFT ray at the spherical range, projected
    into the right camera (an exactly consistent pair), re-triangulated by both geometries."""
    import ab1c_planar as PL
    ve = np.asarray(sph["valid_epi"], bool)
    if not ve.any():
        return None
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    rng = np.linalg.norm(np.asarray(sph["P_epi"], np.float64)[ve] - o_l, axis=-1)
    p_c = o_l + rng[:, None] * np.asarray(sph["d_L"], np.float64)[ve]
    uv_c, _ = FG.project_h(c["eyes"][1], p_c)
    cons = {"left_core_row": np.asarray(prod["left_core_row"])[ve], "left_core_col": np.asarray(prod["left_core_col"])[ve],
            "uv_L": np.asarray(prod["uv_L"], np.float64)[ve], "uv_R": np.asarray(uv_c, np.float64)}
    s, _ = compare_core(c, BG.compute_epipolar(c, cons), PL.triangulate(c, PL.rectify(c), cons))
    return {"statement": "consistency-restored control: left-ray point at the spherical range, projected into the right "
                         "camera, re-triangulated by both; isolates the oracle's epipolar skew", **s}


def pooled_compare(arrs: list[dict]) -> dict:
    cat = lambda k: np.concatenate([a[k][a["common"]] for a in arrs]) if arrs else np.zeros(0)  # noqa: E731
    return {"common_valid": int(sum(int(a["common"].sum()) for a in arrs)),
            "planar_minus_spherical_m": q(cat("difference_m")),
            "radial_signed_planar_minus_spherical_m": q(cat("radial_signed_m")),
            "relative_difference": q(cat("relative_difference"))}


def compare(run: Path) -> dict:
    out = run / "comparison"
    once(out / "comparison-summary.json", "the comparison")
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    out.mkdir(parents=True, exist_ok=True)
    reads = ([run / "freeze/geometry-freeze.json", run / "oracle/correspondence-freeze.json"]
             + [run / n for g in SP.GAZES for n in [f"oracle/{g}/oracle-correspondences.npz"] + geom_files(g)]
             + [calib(run, g) for g in SP.GAZES])
    with OpenGuard("ab1c-compare", reads, [out]) as gd:
        fz = verify_geometry_freeze(run)
        per, arrs = {}, []
        for g in SP.GAZES:
            c = read_json(calib(run, g))
            sph = load_npz(run / "spherical" / g / "epipolar-result.npz")
            pla = load_npz(run / "planar" / g / "planar-result.npz")
            prod = load_npz(product(run, g))
            summ, arr = compare_core(c, sph, pla)
            summ["oracle_skew"] = {"abs_phi_residual_rad": q(np.abs(sph["phi_residual"]), arr["common"]),
                                   "abs_row_residual_px": q(np.abs(pla["row_residual"]), arr["common"])}
            summ["consistency_restored_control"] = consistency_control(c, sph, prod)
            (out / g).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out / g / "comparison-result.npz", **arr)
            per[g] = summ
            arrs.append(arr)
        summary = {"schema": "AB1c-comparison-summary-v1", "truth": SP.TRUTH_DERIVED,
                   "statement": "PRIMARY, TRUTH-FREE: direct planar vs spherical agreement on the common valid set of "
                                "the one shared perfect-correspondence product per gaze; computed after the geometry "
                                "freeze and before any Position is reopened; no threshold",
                   "geometry_freeze_sha256": sha256(run / "freeze/geometry-freeze.json"), "quantiles": SP.QUANTILES,
                   "per_gaze": per, "pooled": pooled_compare(arrs), "frozen_files": fz["files"]}
        write_json(out / "comparison-summary.json", summary)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec.update(truth_reads(rec["events"]))
    write_json(out / "comparison-opened-files.json", rec)
    for g in SP.GAZES:
        k, d = per[g]["counts"], per[g]["planar_minus_spherical_m"]
        dd = "none" if d is None else f"median {d['median']:.3e}, p95 {d['p95']:.3e}, max {d['max']:.3e} m"
        print(f"{PREFIX} compare {g}: correspondences {k['correspondences']:,}; planar {k['planar_valid']:,}; spherical "
              f"{k['spherical_valid']:,}; common {k['common_valid']:,}; |P_planar - P_spherical| {dd}")
    return summary


def comparison_files() -> list[str]:
    return ["comparison/comparison-summary.json", "comparison/comparison-opened-files.json"] + [
        f"comparison/{g}/comparison-result.npz" for g in SP.GAZES]


# ------------------------------------------------------------------ post-freeze evaluation (section 11, SECONDARY)
def errors(p, p_truth, mask, o_l) -> dict:
    mask = np.asarray(mask, bool)
    p, t = np.asarray(p, np.float64)[mask], np.asarray(p_truth, np.float64)[mask]
    e3 = np.linalg.norm(p - t, axis=-1)
    rt = np.linalg.norm(t - o_l, axis=-1)
    rad = np.linalg.norm(p - o_l, axis=-1) - rt
    return {"pairs": int(mask.sum()), "error_3d_m": q(e3), "radial_abs_m": q(np.abs(rad)), "radial_signed_m": q(rad),
            "radial_relative_abs": q(np.abs(rad) / rt) if rt.size else None,
            "fraction_3d_within_m": ({f"{s:.3f}": float((e3 <= s).mean()) for s in SP.ERROR_FRACTIONS_M}
                                     if e3.size else None)}


def evaluation_core(c: dict, sph: dict, pla: dict, prod: dict, ref: dict, names: dict) -> tuple[dict, dict]:
    rows = np.asarray(sph["left_core_row"], np.int64) + SP.CORE_ORIGIN
    cols = np.asarray(sph["left_core_col"], np.int64) + SP.CORE_ORIGIN
    pos = np.asarray(ref["position_w_L"])[rows, cols].astype(np.float64)
    ids = np.asarray(ref["instance_L"])[rows, cols].astype(np.int64)
    p_truth = FG.world_to_head(c, pos)
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    ve, vp = np.asarray(sph["valid_epi"], bool), np.asarray(pla["valid_planar"], bool)
    common = ve & vp
    uv_l, uv_r = np.asarray(prod["uv_L"], np.float64), np.asarray(prod["uv_R"], np.float64)
    out_arr = {"left_core_row": np.asarray(sph["left_core_row"], np.int32),
               "left_core_col": np.asarray(sph["left_core_col"], np.int32), "P_truth": p_truth,
               "left_instance": ids.astype(np.int32)}
    summ = {"truth_range_L_m": q(np.linalg.norm(p_truth - o_l, axis=-1))}
    for name, p, v in (("planar", pla["P_planar"], vp), ("spherical", sph["P_epi"], ve)):
        p = np.asarray(p, np.float64)
        with np.errstate(invalid="ignore"):
            uvl_p, _ = FG.project_h(c["eyes"][0], p)
            uvr_p, _ = FG.project_h(c["eyes"][1], p)
            e3 = np.linalg.norm(p - p_truth, axis=-1)
            rad = np.linalg.norm(p - o_l, axis=-1) - np.linalg.norm(p_truth - o_l, axis=-1)
        rep_l, rep_r = np.linalg.norm(uvl_p - uv_l, axis=-1), np.linalg.norm(uvr_p - uv_r, axis=-1)
        summ[f"{name}_vs_truth"] = errors(p, p_truth, v, o_l)
        summ[f"{name}_vs_truth_common"] = errors(p, p_truth, common, o_l)
        summ[f"{name}_reprojection_px"] = {"left": q(rep_l, v), "right": q(rep_r, v)}
        out_arr.update({f"error_3d_{name}_m": e3, f"radial_signed_{name}_m": rad,
                        f"reprojection_L_{name}_px": rep_l, f"reprojection_R_{name}_px": rep_r})
    inst, cnt = np.unique(ids, return_counts=True)
    order = sorted(zip(cnt.tolist(), inst.tolist()), key=lambda t: (-t[0], t[1]))
    summ["composition"] = {"pairs": int(len(rows)), "distinct_instances": int(len(inst)),
                           "instances": [{"instance_id": int(i), "object_name": names.get(int(i), ""), "pairs": int(k)}
                                         for k, i in order]}
    return summ, out_arr


def pooled_eval(arrs: list[tuple[dict, dict, dict]]) -> dict:
    out = {}
    for name, vk in (("planar", "valid_planar"), ("spherical", "valid_epi")):
        e3 = np.concatenate([a[f"error_3d_{name}_m"][np.asarray(src[vk], bool)] for a, src, _ in arrs])
        rad = np.concatenate([a[f"radial_signed_{name}_m"][np.asarray(src[vk], bool)] for a, src, _ in arrs])
        out[f"{name}_vs_truth"] = {"pairs": int(e3.size), "error_3d_m": q(e3), "radial_signed_m": q(rad),
                                   "radial_abs_m": q(np.abs(rad)),
                                   "fraction_3d_within_m": ({f"{s:.3f}": float((e3 <= s).mean())
                                                             for s in SP.ERROR_FRACTIONS_M} if e3.size else None)}
    return out


def evaluate(run: Path) -> dict:
    out = run / "evaluation"
    once(out / "evaluation-summary.json", "the evaluation")
    need(run / "comparison/comparison-summary.json", "compare")
    out.mkdir(parents=True, exist_ok=True)
    frozen = ([run / "freeze/geometry-freeze.json", run / "oracle/correspondence-freeze.json"]
              + [run / n for g in SP.GAZES for n in [f"oracle/{g}/oracle-correspondences.npz"] + geom_files(g)]
              + [run / n for n in comparison_files()] + [calib(run, g) for g in SP.GAZES])
    cat_path = run / "observations/evaluation_only/instance-catalog.json"
    refs = [reference(run, g) for g in SP.GAZES] + [cat_path]
    cmp_hash = {n: sha256(run / n) for n in comparison_files()}
    with OpenGuard("ab1c-evaluation", frozen + refs, [out]) as gd:
        fz = verify_geometry_freeze(run)
        if {n: sha256(run / n) for n in comparison_files()} != cmp_hash:
            raise SystemExit(f"{PREFIX} STOP the comparison changed")
        gd.mark("geometry_freeze_verified")
        data = {}
        for g in SP.GAZES:
            data[g] = (read_json(calib(run, g)), load_npz(run / "spherical" / g / "epipolar-result.npz"),
                       load_npz(run / "planar" / g / "planar-result.npz"), load_npz(product(run, g)))
        gd.mark("reference_access_begins")
        names = {int(e["instance_id"]): e["object_name"] for e in read_json(cat_path)["instances"]}
        per, arrs = {}, []
        for g in SP.GAZES:
            c, sph, pla, prod = data[g]
            ref = BO.load_reference(reference(run, g))
            summ, arr = evaluation_core(c, sph, pla, prod, ref, names)
            (out / g).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out / g / "evaluation-result.npz", **arr)
            per[g] = summ
            arrs.append((arr, sph | pla, g))
        summary = {"schema": "AB1c-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE, "computed_after_freeze": True,
                   "statement": "POST-FREEZE REFERENCE / EVALUATION (secondary): Position scores the frozen truth-free "
                                "planar and spherical reconstructions; descriptive, no pass / fail, changes nothing",
                   "geometry_freeze_sha256": sha256(run / "freeze/geometry-freeze.json"),
                   "comparison_sha256": cmp_hash, "frozen_geometry_sha256": fz["files"],
                   "reference_sha256": {g: sha256(reference(run, g)) for g in SP.GAZES},
                   "quantiles": SP.QUANTILES, "error_fraction_scales_m": list(SP.ERROR_FRACTIONS_M),
                   "per_gaze": per, "pooled": pooled_eval(arrs)}
        write_json(out / "evaluation-summary.json", summary)
    rec = gd.record()
    rec["ordered_data_events"] = [e.get("label") or e.get("path") for e in rec["events"]
                                  if e.get("event") == "mark" or e.get("kind") == "data-read"]
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "evaluation-opened-files.json", rec)
    verify_geometry_freeze(run)
    if {n: sha256(run / n) for n in comparison_files()} != cmp_hash or rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation altered the comparison or violated the guard")
    for g in SP.GAZES:
        for name in ("planar", "spherical"):
            e = per[g][f"{name}_vs_truth"]["error_3d_m"]
            err = "none" if e is None else f"median {e['median']:.3e}, p95 {e['p95']:.3e}, max {e['max']:.3e} m"
            print(f"{PREFIX} evaluate {g} {name} vs Position: {err}")
    return summary


# ------------------------------------------------------------------ synthetic and rehearsal (section 14)
def synthetic(run: Path) -> dict:
    import ab1c_synthetic as SY
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = SY.synthetic_results()
    for x in results:
        print(f"{PREFIX} synthetic {'PASS' if x['ok'] else 'FAIL'} {x['name']}")
    rep = {"schema": "AB1c-synthetic-report-v1", "code": code_state(), "cases": results,
           "passed": all(x["ok"] for x in results),
           "tolerances": {k: getattr(SP, k) for k in dir(SP) if k.startswith("SYN_")},
           "note": "analytic calibrations, rays, scores and planes only; no Classroom data, no Blender"}
    write_json(out / "synthetic-report.json", rep)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'AB1C_SYNTHETIC_PASS' if rep['passed'] else 'FAILED'}")
    return rep


def rehearse(run: Path) -> dict:
    """The AB1c Blender driver in the accepted synthetic room (never Classroom), then the whole host pipeline."""
    root = run / "synthetic/blender-rehearsal"
    once(root / "rehearsal-report.json", "the rehearsal")
    res = blender(run, "rehearsal", None, run / "logs/rehearsal-blender.log")
    cases = []
    if res["blender"]["complete_marker"]:
        names = {int(e["instance_id"]): e["object_name"] for e in read_json(root / "instance-catalog.json")["instances"]}
        host = root / "host"
        prepared = {}
        for case in SP.SYN_GAZES:
            cal, ref = root / case / "acquisition/calibration.json", root / case / "evaluation_only/reference-observation.npz"
            run_oracle_gaze(cal, ref, host / case / "oracle")
            fzp = host / case / "oracle/correspondence-freeze.json"
            write_json(fzp, {"files": {"oracle-correspondences.npz": sha256(host / case / "oracle/oracle-correspondences.npz")}})
            prepared[case] = (cal, ref, fzp)
        for case, (cal, ref, fzp) in prepared.items():            # spherical first: cv2 not yet loaded
            run_spherical_gaze(cal, host / case / "oracle/oracle-correspondences.npz", host / case / "spherical", fzp)
        import ab1c_planar as PL
        for case, (cal, ref, fzp) in prepared.items():
            PL.run_planar(cal, host / case / "oracle/oracle-correspondences.npz", host / case / "planar", fzp)
        for case, (cal, ref, fzp) in prepared.items():
            c = read_json(cal)
            a = read_json(root / case / "acquisition/acquisition.json")
            sph = load_npz(host / case / "spherical/epipolar-result.npz")
            pla = load_npz(host / case / "planar/planar-result.npz")
            prod = load_npz(host / case / "oracle/oracle-correspondences.npz")
            cmp_s, _cmp_a = compare_core(c, sph, pla)
            ev_s, _ev_a = evaluation_core(c, sph, pla, prod, BO.load_reference(ref), names)
            refo = BO.load_reference(ref)
            # camera model: Position projects onto its pixel centre
            proj = []
            for i, side in enumerate(("L", "R")):
                pos = np.asarray(refo[f"position_w_{side}"], np.float64)
                hit = np.isfinite(pos).all(-1) & np.any(pos != 0, axis=-1)
                uv, _ = FG.project_h(c["eyes"][i], FG.world_to_head(c, pos[hit]))
                v, u = np.nonzero(hit)
                proj.append(float(np.abs(uv - np.stack([u, v], -1)).max()) if hit.any() else math.inf)
            sp_reads = read_json(host / case / "spherical/spherical-opened-files.json")
            cons_s = consistency_control(c, sph, prod)
            dc = cons_s["planar_minus_spherical_m"] if cons_s else None
            d, es = cmp_s["planar_minus_spherical_m"], ev_s["spherical_vs_truth"]["error_3d_m"]
            ep = ev_s["planar_vs_truth"]["error_3d_m"]
            passes = exr_passes(a["exr_channels_lr"]["L"])
            k = cmp_s["counts"]
            ok = (passes == set(SP.REQUIRED_PASSES) and exr_passes(a["exr_channels_lr"]["R"]) == passes
                  and max(proj) <= SP.REHEARSAL_PROJECTION_PX and k["correspondences"] > 0
                  and k["common_valid"] == k["correspondences"] == k["planar_valid"] == k["spherical_valid"]
                  and d is not None and d["max"] <= SP.REHEARSAL_AGREE_M and dc is not None
                  and dc["max"] <= SP.SYN_EXACT_M and es is not None and ep is not None
                  and es["median"] <= SP.REHEARSAL_MEDIAN_M and ep["median"] <= SP.REHEARSAL_MEDIAN_M
                  and not any(sp_reads["modules_loaded"].values()) and not sp_reads["violations"])
            cases.append({"case": case, "gaze": SP.SYN_GAZES[case], "ok": bool(ok), "exr_passes": sorted(passes),
                          "max_position_projection_px": proj, "counts": k, "planar_minus_spherical_m": d,
                          "planar_minus_spherical_m_consistency_restored": dc,
                          "abs_phi_residual_max_rad": float(np.nanmax(np.abs(sph["phi_residual"]))),
                          "abs_row_residual_max_px": float(np.nanmax(np.abs(pla["row_residual"]))),
                          "spherical_error_3d_m": es, "planar_error_3d_m": ep,
                          "render_seconds_lr": a["render_seconds_lr"]})
            print(f"{PREFIX} rehearsal {case} {'PASS' if ok else 'FAIL'}: pairs {k['correspondences']:,}; common "
                  f"{k['common_valid']:,}; |P_planar - P_spherical| max {d['max'] if d else float('nan'):.3e} m; "
                  f"error median planar {ep['median'] if ep else float('nan'):.3e} / spherical "
                  f"{es['median'] if es else float('nan'):.3e} m; projection {max(proj):.2e} px")
    rep = {"schema": "AB1c-rehearsal-report-v1", "code": code_state(), "blender": res["blender"],
           "scene": "accepted synthetic factory-startup room (ab1a_render.build_rehearsal_scene); never Classroom",
           "spp": SP.REHEARSAL_SPP, "cases": cases,
           "passed": bool(res["blender"]["complete_marker"] and cases and all(x["ok"] for x in cases))}
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "rehearsal-report.json", rep)
    print(f"{PREFIX} rehearsal {'AB1C_REHEARSAL_PASS' if rep['passed'] else 'FAILED'}")
    return rep


# ------------------------------------------------------------------ manifest
TRUTH_CLASSES = {"source/": SP.TRUTH_DERIVED, "selection/": SP.TRUTH_DERIVED + " (" + SP.SELECTION_LABEL + ")",
                 "plan/": SP.TRUTH_DERIVED, "preflight/": "configuration record (no render)",
                 "observations/*/acquisition/": SP.TRUTH_ORACLE + " (sensory observation: RGB + calibration)",
                 "observations/*/evaluation_only/": SP.TRUTH_ORACLE + " (oracle source) / " + SP.TRUTH_REFERENCE,
                 "oracle/": SP.TRUTH_DERIVED + " (truth-stripped; produced by the ORACLE INPUT stage)",
                 "spherical/": SP.TRUTH_DERIVED, "planar/": SP.TRUTH_DERIVED, "freeze/": SP.TRUTH_DERIVED,
                 "comparison/": SP.TRUTH_DERIVED, "evaluation/": SP.TRUTH_REFERENCE, "synthetic/": "known answers",
                 "logs/": "process logs"}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "AB1c-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
    write_json(run / "manifest.json", m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in SP.COMMANDS:
        p = sub.add_parser(name)
        p.add_argument("--run", required=True, type=Path)
        if name == "visualize":
            p.add_argument("--visuals", required=True, type=Path)
    a = ap.parse_args(argv)
    run = a.run.resolve()
    t0 = time.time()
    status, extra = "failed", None
    try:
        if a.cmd == "synthetic":
            ok = synthetic(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd == "rehearse":
            rep = rehearse(run)
            extra = {"blender": rep["blender"]}
            status = "ok" if rep["passed"] else "failed"
            return 0 if rep["passed"] else 1
        if a.cmd in SP.CANONICAL:
            require_committed(a.cmd)
        if a.cmd in ("preflight", "acquire"):
            res = {"preflight": preflight, "acquire": acquire}[a.cmd](run)
            extra = res
            ok = res["blender"]["complete_marker"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        {"source": source, "select": select, "freeze-selection": freeze_selection, "plan": plan, "oracle": oracle,
         "freeze-correspondence": freeze_correspondence, "spherical": spherical, "planar": planar,
         "freeze-geometry": freeze_geometry, "compare": compare, "evaluate": evaluate}.get(a.cmd, lambda r: None)(run)
        if a.cmd == "visualize":
            import ab1c_visuals
            ab1c_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status, extra)


if __name__ == "__main__":
    raise SystemExit(main())
