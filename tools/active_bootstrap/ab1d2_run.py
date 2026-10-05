"""Active Bootstrap-1d2: 4096-spp observation-quality control (run order, render control, truth boundary, pairing).

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1d2_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py preflight-tests       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py rehearse              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py preflight             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py render-4096           --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-observation    --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py match                 --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py evaluate-paired       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py visualize             --run RUN --visuals VIS

``render-4096`` re-observes the three accepted AB1c gazes once at 4096 spp (``ab1d2_render.py``) and classifies every
acquisition-record field and EXR header attribute against the accepted AB1c record (section 7); anything unexpected is a
hard stop.  ``match`` and ``spherical`` call the accepted AB1d functions unchanged (``ab1d_run.run_match_gaze``,
``run_spherical_gaze``) on the AB1d2 observation; ``freeze-correspondence`` requires the calibration-derived search
geometry to be bitwise identical to AB1d (section 10).  Only after the geometry freeze does ``evaluate-paired`` open the
accepted AB1c benchmark, score both conditions with the accepted ``ab1d_run.evaluation_core`` against the same oracle,
require the 256-spp evaluation to reproduce the accepted AB1d arrays exactly, and pair them pixel by pixel.  This module
imports neither the matcher nor Blender at load time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
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

import ab1d2_spec as SP  # noqa: E402
import ab1d_run as AD  # noqa: E402  (accepted AB1d run functions, read-only; loads neither cv2 nor the matcher)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1d2]"
RENDER_SCRIPT = HERE / "ab1d2_render.py"
TRUTH_CLASSES = {"ORACLE INPUT": "the rendered RGB observations (AB1c 256 spp and AB1d2 4096 spp)",
                 "DERIVED": "natural matcher records and products, spherical geometry, render-control comparisons",
                 "REFERENCE / EVALUATION": "the AB1c perfect correspondence, perfect spherical reconstruction and Blender "
                                           "Position (benchmark only, after the geometry freeze); the accepted AB1d "
                                           "evaluation; the new AB1d2 truth passes exist but are never opened"}


# ------------------------------------------------------------------ infrastructure
def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


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
    if Path(path).exists():
        raise SystemExit(f"{PREFIX} STOP {what} exists ({path}); it is made once")


def need(path: Path, what: str) -> None:
    if not Path(path).is_file():
        raise SystemExit(f"{PREFIX} STOP {what} comes first ({path} missing)")


def verify_pins(root: Path, pins: dict) -> dict:
    """Files under ``root`` whose sha256 differs from the pin (missing files count as different)."""
    return {p: (sha256(root / p) if (root / p).is_file() else None) for p, h in pins.items()
            if not (root / p).is_file() or sha256(root / p) != h}


def verify_sources() -> None:
    bad = verify_pins(REPO, SP.SOURCE_PINS)
    if bad:
        raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")


def matcher_identity(spec_mod=None, frozen=None) -> dict:
    """The live accepted matcher constants (ab1d_spec + ab1d_match.FROZEN) against the declared AB1d values."""
    if spec_mod is None or frozen is None:
        import ab1d_match as M
        import ab1d_spec as DS
        spec_mod, frozen = spec_mod or DS, frozen or M.FROZEN
    want = SP.MATCHER_CONSTANTS
    live = {k: (tuple(getattr(spec_mod, k)) if k == "LUMA" else getattr(spec_mod, k)) for k in want}
    params = {"PATCH_HALF": frozen.patch_half, "SPACING_PX": frozen.spacing, "MIN_LOCAL_STD_U8": frozen.min_std,
              "TIE_EPS": frozen.tie_eps, "TOP_K": frozen.top_k, "PEAK_SEPARATION_PX": frozen.separation,
              "REFINE_BOUND_SAMPLES": frozen.bound, "LUMA": tuple(frozen.luma)}
    spec_ok = {k: live[k] == v for k, v in want.items()}
    frozen_ok = {k: params[k] == want[k] for k in params}
    return {"spec": spec_ok, "frozen_params": frozen_ok, "ok": all(spec_ok.values()) and all(frozen_ok.values())}


# ------------------------------------------------------------------ section 7: render-setting equivalence
def jsonable(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="backslashreplace")
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    return v


def exr_header(path: Path) -> dict:
    """EXR header attributes only (the first EXR_HEADER_BYTES bytes; no pixel data is decoded)."""
    from exr_lite import read_header
    with open(path, "rb") as f:
        buf = f.read(SP.EXR_HEADER_BYTES)
    return jsonable(read_header(buf)[0])


def same_blend(a: str, b: str) -> bool:
    if not a or not b:
        return a == b
    return os.path.realpath(a) == os.path.realpath(b)


def max_abs_matrix(a, b) -> float:
    return max(abs(float(x) - float(y)) for s in ("L", "R") for ra, rb in zip(a[s], b[s]) for x, y in zip(ra, rb))


def primary_samples(spp: int) -> int:
    return int(2 * SP.RAW_SIZE * SP.RAW_SIZE * spp)


def compare_acquisition(old: dict, new: dict, spp_old: int, spp_new: int) -> dict:
    """Classify every acquisition-record field (contract section 7); ``ok`` only if nothing is unexpected."""
    rows = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if k in SP.REC_MUST_EQUAL:
            cls = "MUST EQUAL"
            if k == "camera_matrix_world_lr":
                ok = a is not None and b is not None and max_abs_matrix(a, b) <= SP.EYE_POSE_TOL
            elif k == "settings":
                ok = (isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b)
                      and all(a[s] == b[s] for s in a if s != "samples")
                      and a.get("samples") == spp_old and b.get("samples") == spp_new)
            else:
                ok = k in old and k in new and a == b
        elif k in SP.REC_EXPECTED:
            cls = "EXPECTED DIFFERENT"
            if k == "spp":
                ok = a == spp_old and b == spp_new
            elif k == "primary_camera_samples":
                ok = a == primary_samples(spp_old) and b == primary_samples(spp_new)
            elif k in ("rgb_observation_sha256", "created_utc"):
                ok = a is not None and b is not None and a != b
            else:
                ok = a is not None and b is not None
        elif k in SP.REC_LABEL:
            cls = "LABEL"
            if k == "blend":
                ok = k in old and k in new and same_blend(a, b)
            elif k == "observation_quality_control":
                ok = b is not None and b.get("spp") == spp_new
            else:
                ok = True
        else:
            cls, ok = "UNEXPECTED", False
        rows.append({"field": k, "class": cls, "accepted": jsonable(a), "new": jsonable(b), "ok": bool(ok)})
    bad = [r["field"] for r in rows if not r["ok"]]
    return {"fields": rows, "failed": bad, "ok": not bad}


def exr_layer(h: dict) -> str | None:
    ch = h.get("channels") or []
    return ch[0][0].split(".")[0] if ch else None


def compare_exr(old: dict, new: dict, spp_old: int, spp_new: int) -> dict:
    """Classify every EXR header attribute (section 7).  Cycles names its per-layer attributes cycles.<layer>.<key>;
    the layer is read from each header's channel list (Classroom: ``interior``)."""
    lo, ln = exr_layer(old), exr_layer(new)
    layers = {x for x in (lo, ln) if x}
    samples = {f"cycles.{x}.samples" for x in layers}
    timing = set(SP.EXR_TIMING) | {f"cycles.{x}.{t}" for x in layers for t in SP.EXR_LAYER_TIMING}
    rows = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        if k in SP.EXR_MUST_EQUAL:
            cls, ok = "MUST EQUAL", k in old and k in new and a == b
        elif k in samples:
            cls, ok = "SAMPLES", a == str(spp_old) and b == str(spp_new)
        elif k in timing:
            cls, ok = "EXPECTED DIFFERENT", True
        elif k in SP.EXR_LABEL:
            cls, ok = "LABEL", same_blend(a or "", b or "")
        else:
            cls, ok = "UNEXPECTED", False
        rows.append({"attribute": k, "class": cls, "accepted": a, "new": b, "ok": bool(ok)})
    required = [(k, k in old and k in new) for k in SP.EXR_MUST_EQUAL]
    required += [(f"cycles.{lo}.samples", f"cycles.{lo}.samples" in old), (f"cycles.{ln}.samples", f"cycles.{ln}.samples" in new)]
    for k, present in required:
        if not present:
            rows.append({"attribute": k, "class": "MISSING", "accepted": old.get(k), "new": new.get(k), "ok": False})
    bad = [r["attribute"] for r in rows if not r["ok"]]
    return {"layers": [lo, ln], "attributes": rows, "failed": sorted(set(bad)), "ok": not bad}


def instances(path: Path) -> list:
    return read_json(path)["instances"]


def render_control(run: Path) -> dict:
    """Section 7 for every gaze and eye, the scene object list and the blend identity."""
    out = {"schema": "AB1d2-render-control-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "every acquisition-record field and EXR header attribute of the 4096-spp observations classified "
                        "against the accepted AB1c record: MUST EQUAL / EXPECTED DIFFERENT / LABEL; anything else is a "
                        "hard stop.  EXR header metadata only (no pixel data decoded).",
           "spp_accepted": SP.ACCEPTED_SPP, "spp": SP.SPP, "gazes": {}}
    ok_all = True
    for g in SP.GAZES:
        old = read_json(SP.a1c_acq(g, "acquisition.json"))
        new = read_json(run / SP.obs_rel(g, "acquisition.json"))
        rec = compare_acquisition(old, new, SP.ACCEPTED_SPP, SP.SPP)
        exr = {}
        for s in ("L", "R"):
            exr[s] = compare_exr(exr_header(SP.a1c(f"observations/{g}/evaluation_only/raw_{s}.exr")),
                                 exr_header(run / f"observations/{g}/evaluation_only/raw_{s}.exr"), SP.ACCEPTED_SPP, SP.SPP)
        cal = sha256(run / SP.obs_rel(g, "calibration.json"))
        files = sorted(p.name for p in (run / f"observations/{g}/acquisition").iterdir())
        ev_files = sorted(p.name for p in (run / f"observations/{g}/evaluation_only").iterdir())
        with np.load(run / SP.obs_rel(g, "rgb-observation.npz"), allow_pickle=False) as z:
            arrays = {k: [list(z[k].shape), str(z[k].dtype), bool(np.isfinite(z[k]).all())] for k in z.files}
        checks = {"acquisition_files": files == ["acquisition.json", "calibration.json", "rgb-observation.npz"],
                  "evaluation_only_files": ev_files == ["raw_L.exr", "raw_R.exr", "reference-observation.npz"],
                  "calibration_byte_identical": cal == SP.A1C_CALIBRATION[g],
                  "rgb_arrays": arrays == {"rgb_L": [[SP.RAW_SIZE, SP.RAW_SIZE, 3], "float32", True],
                                           "rgb_R": [[SP.RAW_SIZE, SP.RAW_SIZE, 3], "float32", True]},
                  "rgb_hash_recorded": new.get("rgb_observation_sha256") == sha256(run / SP.obs_rel(g, "rgb-observation.npz")),
                  "record": rec["ok"], "exr_L": exr["L"]["ok"], "exr_R": exr["R"]["ok"]}
        ok = all(checks.values())
        ok_all &= ok
        out["gazes"][g] = {"checks": checks, "acquisition": rec, "exr": exr, "calibration_sha256": cal,
                           "accepted_calibration_sha256": SP.A1C_CALIBRATION[g], "rgb_arrays": arrays, "ok": ok}
    a_inst, n_inst = instances(SP.a1c(SP.A1C_CATALOG[0])), instances(run / "observations/evaluation_only/instance-catalog.json")
    out["scene_object_list_identical"] = a_inst == n_inst
    out["scene_objects"] = len(n_inst)
    dirs = sorted(p.name for p in (run / "observations").iterdir())
    out["observation_dirs"] = dirs
    out["exactly_three_gazes"] = dirs == ["evaluation_only", *SP.GAZES]
    out["eye_renders"] = sum(1 for g in SP.GAZES for s in ("L", "R")
                             if (run / f"observations/{g}/evaluation_only/raw_{s}.exr").is_file())
    out["blend_sha256"] = sha256(REPO / SP.BLEND)
    out["blend_identity"] = out["blend_sha256"] == SP.BLEND_SHA256
    out["ok"] = bool(ok_all and out["scene_object_list_identical"] and out["exactly_three_gazes"]
                     and out["eye_renders"] == 6 and out["blend_identity"])
    return out


# ------------------------------------------------------------------ section 10: search-geometry identity
def same_array(a, b) -> bool:
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    if a.dtype.kind == "f":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def geometry_identity(rec_a: dict, rec_b: dict) -> dict:
    fields = {}
    for k in SP.GEOMETRY_FIELDS:
        a, b = np.asarray(rec_a[k]), np.asarray(rec_b[k])
        if a.shape != b.shape or a.dtype != b.dtype:
            fields[k] = {"identical": False, "rows_differing": None, "shape": [list(a.shape), list(b.shape)]}
            continue
        if a.dtype.kind == "f":
            neq = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        else:
            neq = a != b
        rows = neq.reshape(neq.shape[0], -1).any(axis=1) if neq.ndim > 1 else neq
        fields[k] = {"identical": not bool(rows.any()), "rows_differing": int(rows.sum())}
    return {"fields": fields, "ok": all(v["identical"] for v in fields.values())}


# ------------------------------------------------------------------ truth-read audit (AB1d2 additions)
def truth_reads(events: list[dict], run: Path) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    a1c, a1d, r = str(SP.A1C_RUN.resolve()), str(SP.A1D_RUN.resolve()), str(run.resolve())
    return {"evaluation_only_reads": sum(1 for p in paths if "/evaluation_only/" in p or p.endswith(".exr")
                                         or p.endswith("reference-observation.npz")),
            "ab1d2_truth_reads": sum(1 for p in paths if p.startswith(r + "/observations/") and "/evaluation_only/" in p),
            "ab1c_run_reads": sum(1 for p in paths if p.startswith(a1c + "/")),
            "ab1d_run_reads": sum(1 for p in paths if p.startswith(a1d + "/")),
            "ab1d2_evaluation_reads": sum(1 for p in paths if p.startswith(r + "/evaluation/"))}


# ------------------------------------------------------------------ source (section 3)
def source(run: Path) -> dict:
    out = run / "source/source-manifest.json"
    once(out, "the source manifest")
    verify_sources()
    import ab1a_spec as AS
    import ab1c_spec as CS
    import ab1d_spec as DS
    remote = git("remote", "get-url", "origin")
    a1c_man = read_json(SP.a1c(SP.A1C_MANIFEST[0]))["files"]
    a1d_man = read_json(SP.a1d("manifest.json"))["files"]
    a1d_direct = {k: h for k, h in SP.A1D_PINS.items() if k != "manifest.json" and not k.startswith("evaluation/")}
    acq_ok = {}
    for g in SP.GAZES:
        a = read_json(SP.a1c_acq(g, "acquisition.json"))
        t = SP.GAZE_TABLE[g]
        acq_ok[g] = (a["spp"] == SP.ACCEPTED_SPP and a["render_seeds_lr"] == SP.SEEDS and a["device"] == SP.DEVICE
                     and a["settings"]["samples"] == SP.ACCEPTED_SPP and a["calibration_sha256"] == SP.A1C_CALIBRATION[g]
                     and a["rgb_observation_sha256"] == SP.A1C_RGB[g]
                     and list(a["gaze_yaw_pitch_deg"]) == [t["yaw_deg"], t["pitch_deg"]])
    obs_pins = {SP.obs_rel(g, n): h for g in SP.GAZES for n, h in (("calibration.json", SP.A1C_CALIBRATION[g]),
                                                                    ("rgb-observation.npz", SP.A1C_RGB[g]),
                                                                    ("acquisition.json", SP.A1C_ACQUISITION[g]))}
    cfz = read_json(SP.a1d("match/correspondence-freeze.json"))
    ident = {
        "canonical_remote": remote.rstrip("/").removesuffix(".git").endswith(SP.CANONICAL_REMOTE),
        "a1c_manifest": sha256(SP.a1c(SP.A1C_MANIFEST[0])) == SP.A1C_MANIFEST[1],
        "a1c_observations_equal_ab1d_pins": all(DS.OBS_PINS.get(k) == h for k, h in obs_pins.items()),
        "a1c_observation_files": not verify_pins(SP.A1C_RUN, obs_pins),
        "a1c_observations_in_manifest": all(a1c_man.get(k) == h for k, h in obs_pins.items()),
        "a1c_benchmark_in_manifest": all(a1c_man.get(k) == h for k, h in DS.BENCH_PINS.items()),
        "a1c_acquisition_records": all(acq_ok.values()),
        "a1c_instance_catalog": sha256(SP.a1c(SP.A1C_CATALOG[0])) == SP.A1C_CATALOG[1],
        "a1d_manifest": sha256(SP.a1d("manifest.json")) == SP.A1D_PINS["manifest.json"],
        "a1d_pins_in_manifest": all(a1d_man.get(k) == h for k, h in SP.A1D_PINS.items() if k != "manifest.json"),
        "a1d_derived_files": not verify_pins(SP.A1D_RUN, a1d_direct),
        "a1d_visuals_manifest": sha256(SP.A1D_VIS_MANIFEST[0]) == SP.A1D_VIS_MANIFEST[1],
        "a1d_matcher_config": cfz["matcher_config_sha256"] == DS.config_sha256(DS.MATCHER),
        "blend": sha256(REPO / SP.BLEND) == SP.BLEND_SHA256,
        "head_pose": sha256(SP.HEAD_POSE_SOURCE[0]) == SP.HEAD_POSE_SOURCE[1],
        "ab1a_seeds_device": AS.SEEDS == SP.SEEDS and AS.DEVICE == SP.DEVICE,
        "ab1c_accepted_spp": CS.SPP == SP.ACCEPTED_SPP and CS.SEEDS == SP.SEEDS and CS.BLEND_SHA256 == SP.BLEND_SHA256,
        "oracle_peak_radius": DS.ORACLE_PEAK_RADIUS_PX == SP.ORACLE_PEAK_RADIUS_PX,
        "matcher_constants": matcher_identity()["ok"],
    }
    if not all(ident.values()):
        raise SystemExit(f"{PREFIX} STOP source identity: {ident}")
    rec = {"schema": "AB1d2-source-manifest-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
           "statement": "pinned sources verified; the accepted AB1c observations, calibrations and acquisition records "
                        "and the accepted AB1d derived products are hashed; the AB1c benchmark and the AB1d evaluation "
                        "are verified here only through their manifests and are hashed again, then opened, only after "
                        "the geometry freeze",
           "remote": remote, "identity": ident, "a1c_run": str(SP.A1C_RUN), "a1d_run": str(SP.A1D_RUN),
           "a1c_observation_pins": obs_pins, "a1c_benchmark_pins": DS.BENCH_PINS, "a1d_pins": SP.A1D_PINS,
           "source_pins": SP.SOURCE_PINS, "matcher_constants": SP.MATCHER_CONSTANTS,
           "matcher_config_sha256": DS.config_sha256(DS.MATCHER), "spp": SP.SPP, "accepted_spp": SP.ACCEPTED_SPP,
           "seeds": SP.SEEDS, "blend_sha256": SP.BLEND_SHA256, "base_commit": SP.BASE_COMMIT,
           "contract_commit": SP.CONTRACT_COMMIT, "code": code_state(), "created_utc": utc()}
    write_json(out, rec)
    print(f"{PREFIX} source: {len(SP.SOURCE_PINS)} code pins, {len(obs_pins)} AB1c observation pins, "
          f"{len(SP.A1D_PINS)} AB1d pins, matcher constants identical, canonical remote verified")
    return rec


# ------------------------------------------------------------------ preflight tests (section 21, host)
def preflight_tests(run: Path) -> dict:
    out = run / "preflight/preflight-tests.json"
    once(out, "the preflight tests")
    import ab1d2_preflight as PF
    rep = PF.run_tests(run / "preflight")
    rep["code"] = code_state()
    write_json(out, rep)
    for x in rep["cases"]:
        print(f"{PREFIX} preflight {'PASS' if x['passed'] else 'FAIL'} {x['case']:2d} {x['name']}")
    print(f"{PREFIX} {'AB1D2_PREFLIGHT_PASS' if rep['passed'] else 'PREFLIGHT TESTS FAILED'} "
          f"{sum(x['passed'] for x in rep['cases'])}/{len(rep['cases'])}")
    return rep


# ------------------------------------------------------------------ Blender (sections 6, 21)
def blender(run: Path, mode: str, blend: Path | None, log: Path, spp: int | None = None) -> dict:
    """One Blender process; the render budget (section 25) stops it rather than letting it run on unreported."""
    argv = [SP.BLENDER, "-b"] + ([str(blend)] if blend else ["--factory-startup"]) + [
        "--python-exit-code", "1", "-P", str(RENDER_SCRIPT), "--", "--mode", mode, "--run", str(run),
        "--head-pose", str(SP.HEAD_POSE_SOURCE[0])] + (["--spp", str(spp)] if spp is not None else [])
    t0 = time.time()
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=SP.RENDER_BUDGET_S)
        out, rc, timeout = proc.stdout + proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        out = ((exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")) + \
              ((exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
        rc, timeout = None, True
    log.write_text(out)
    marker = f"[ab1d2-render] COMPLETE {mode}" + (f" spp {spp}" if spp is not None else "")
    ok = rc == 0 and marker in out
    return {"mode": mode, "argv": argv, "returncode": rc, "seconds": round(time.time() - t0, 3), "timeout": timeout,
            "complete_marker": ok, "log": str(log)}


def rehearse(run: Path) -> dict:
    out = run / "synthetic/rehearsal/rehearsal-report.json"
    once(out, "the rehearsal")
    root = run / "synthetic/rehearsal"
    res = {spp: blender(run, "rehearsal", None, run / f"logs/rehearsal-{spp}-blender.log", spp)
           for spp in SP.REHEARSAL_SPPS}
    g = SP.REHEARSAL_GAZE
    cases = {}
    if all(r["complete_marker"] for r in res.values()):
        lo, hi = (root / f"spp-{s}" / g for s in SP.REHEARSAL_SPPS)
        rl, rh = read_json(lo / "acquisition/acquisition.json"), read_json(hi / "acquisition/acquisition.json")
        ctl = compare_acquisition(rl, rh, *SP.REHEARSAL_SPPS)
        exr = {s: compare_exr(exr_header(lo / f"evaluation_only/raw_{s}.exr"), exr_header(hi / f"evaluation_only/raw_{s}.exr"),
                              *SP.REHEARSAL_SPPS) for s in ("L", "R")}
        neg = compare_acquisition(read_json(SP.a1c_acq(g, "acquisition.json")), rh, *SP.REHEARSAL_SPPS)
        neg_exr = compare_exr(exr_header(SP.a1c(f"observations/{g}/evaluation_only/raw_L.exr")),
                              exr_header(hi / "evaluation_only/raw_L.exr"), *SP.REHEARSAL_SPPS)
        za, zb = load_npz(lo / "acquisition/rgb-observation.npz"), load_npz(hi / "acquisition/rgb-observation.npz")
        dmax = {k: float(np.abs(zb[k].astype(np.float64) - za[k]).max()) for k in ("rgb_L", "rgb_R")}
        ident = {s: read_json(root / f"spp-{s}" / "rehearsal-identity.json") for s in SP.REHEARSAL_SPPS}
        cases = {
            "calibration_byte_identical": sha256(lo / "acquisition/calibration.json") == sha256(hi / "acquisition/calibration.json"),
            "camera_matrices_identical": rl["camera_matrix_world_lr"] == rh["camera_matrix_world_lr"],
            "readback_samples": rl["settings"]["samples"] == SP.ACCEPTED_SPP and rh["settings"]["samples"] == SP.SPP,
            "control_256_to_4096_passes": ctl["ok"],
            "exr_256_to_4096_passes": exr["L"]["ok"] and exr["R"]["ok"],
            "exr_samples_attribute": all(sum(1 for r in e["attributes"] if r["class"] == "SAMPLES"
                                             and r["accepted"] == str(SP.ACCEPTED_SPP) and r["new"] == str(SP.SPP)) == 1
                                         for e in exr.values()),
            "rgb_changed": min(dmax.values()) > 0.0,
            "negative_control_vs_ab1c_fails": not neg["ok"],
            "negative_control_scene_fields": {"exr_channels_lr"} <= set(neg["failed"]),
            "negative_control_exr_scene": "Scene" in neg_exr["failed"],
        }
        detail = {"control": ctl, "exr": exr, "negative_control": {"record_failed": neg["failed"],
                                                                     "exr_failed": neg_exr["failed"]},
                  "rgb_max_abs_change": dmax, "identity_vs_ab1c_gaze1": {
                      s: {k: v for k, v in ident[s].items() if k != "camera_matrix_world_lr"} for s in SP.REHEARSAL_SPPS},
                  "render_seconds": {s: read_json(root / f"spp-{s}" / g / "acquisition/acquisition.json")["render_seconds_lr"]
                                     for s in SP.REHEARSAL_SPPS}}
    else:
        detail = {}
    rep = {"schema": "AB1d2-rehearsal-report-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "non-Classroom rehearsal (accepted AB1a synthetic factory-startup room): the same acquisition at "
                        "256 and 4096 spp; never Classroom", "blender": {str(k): v for k, v in res.items()},
           "cases": cases, "detail": detail, "code": code_state(),
           "passed": bool(cases and all(cases.values()))}
    write_json(out, rep)
    for k, v in cases.items():
        print(f"{PREFIX} rehearsal {'PASS' if v else 'FAIL'} {k}")
    print(f"{PREFIX} {'AB1D2_REHEARSAL_PASS' if rep['passed'] else 'REHEARSAL FAILED'}")
    return rep


def preflight(run: Path) -> dict:
    once(run / "preflight/preflight.json", "the Classroom preflight")
    need(run / "source/source-manifest.json", "source")
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "preflight", REPO / SP.BLEND, run / "logs/preflight-blender.log")
    if not res["complete_marker"]:
        raise SystemExit(f"{PREFIX} STOP preflight failed; see {res['log']}")
    pf = read_json(run / "preflight/preflight.json")
    if pf["rendered"] or not all(v["ok"] for v in pf["gazes"].values()):
        raise SystemExit(f"{PREFIX} STOP preflight record not ok")
    for g, v in pf["gazes"].items():
        print(f"{PREFIX} preflight {g}: calibration diff {v['calibration_max_abs_diff_built_vs_accepted']}; byte-identical "
              f"{v['reserialized_calibration_byte_identical']}; camera matrix diff {v['camera_matrix_max_abs_diff_vs_accepted']} "
              f"/ set {v['set_camera_matrix_max_abs_diff_vs_accepted']}; settings differences except samples "
              f"{v['settings_differences_except_samples']}; samples {v['settings']['samples']}; NO render")
    return res


def same_commit_report(path: Path, what: str, cs: dict) -> dict:
    need(path, what)
    rep = read_json(path)
    if not rep["passed"] or rep["code"]["commit"] != cs["commit"] or rep["code"]["dirty"]:
        raise SystemExit(f"{PREFIX} STOP {what} must have passed from this exact clean commit")
    return rep


def render_4096(run: Path) -> dict:
    cs = require_committed("render-4096")
    o = run / "observations"
    if o.exists() and any(o.iterdir()):
        raise SystemExit(f"{PREFIX} STOP {o} exists: each accepted gaze is re-observed once")
    need(run / "source/source-manifest.json", "source")
    same_commit_report(run / "preflight/preflight-tests.json", "preflight-tests", cs)
    same_commit_report(run / "synthetic/rehearsal/rehearsal-report.json", "rehearse", cs)
    need(run / "preflight/preflight.json", "preflight")
    pf = read_json(run / "preflight/preflight.json")
    for g in SP.GAZES:
        acc = read_json(SP.a1c_acq(g, "acquisition.json"))["calibration_max_abs_diff_from_planned"]
        if pf["gazes"][g]["calibration_max_abs_diff_built_vs_accepted"] != acc or not pf["gazes"][g]["ok"]:
            raise SystemExit(f"{PREFIX} STOP {g}: the preflight calibration identity would not reproduce the accepted "
                             f"record ({pf['gazes'][g]['calibration_max_abs_diff_built_vs_accepted']} vs {acc})")
    verify_sources()
    if sha256(REPO / SP.BLEND) != SP.BLEND_SHA256:
        raise SystemExit(f"{PREFIX} STOP Classroom blend changed")
    res = blender(run, "canonical", REPO / SP.BLEND, run / "logs/render-4096-blender.log")
    if not res["complete_marker"]:
        print(f"{PREFIX} STOP the canonical 4096-spp acquisition failed{' (render budget exceeded)' if res['timeout'] else ''}; "
              f"see {res['log']}. It is NOT retried and no setting is changed: a second acquisition is a decision for "
              f"Luiz and Chat.")
        raise SystemExit(1)
    ctl = render_control(run)
    ctl["blender"] = res
    write_json(run / "observations/render-control.json", ctl)
    for g in SP.GAZES:
        a = read_json(run / SP.obs_rel(g, "acquisition.json"))
        print(f"{PREFIX} render-4096 {g}: gaze {a['gaze_yaw_pitch_deg']}; {a['device']} {a['spp']} spp; seeds "
              f"{a['render_seeds_lr']}; render seconds {a['render_seconds_lr']}; rgb {a['rgb_observation_sha256'][:12]}; "
              f"control {'ok' if ctl['gazes'][g]['ok'] else 'FAILED ' + str(ctl['gazes'][g]['checks'])}")
    if not ctl["ok"]:
        raise SystemExit(f"{PREFIX} HARD STOP render-setting equivalence failed (observations/render-control.json)")
    print(f"{PREFIX} render-4096: 6 eye renders; only spp changed (256 -> 4096); Blender {res['seconds']} s")
    return res


# ------------------------------------------------------------------ section 8: observation freeze
def obs_files(g: str) -> list[str]:
    return [SP.obs_rel(g, n) for n in ("acquisition.json", "calibration.json", "rgb-observation.npz")]


def truth_files(g: str) -> list[str]:
    return [f"observations/{g}/evaluation_only/{n}" for n in ("raw_L.exr", "raw_R.exr", "reference-observation.npz")]


def freeze_observation(run: Path) -> dict:
    path = run / "freeze/observation-freeze.json"
    once(path, "the observation freeze")
    need(run / "observations/render-control.json", "render-4096")
    ctl = read_json(run / "observations/render-control.json")
    if not ctl["ok"]:
        raise SystemExit(f"{PREFIX} STOP render control is not ok; nothing is frozen")
    files = {n: sha256(run / n) for g in SP.GAZES for n in obs_files(g)}
    files.update({n: sha256(run / n) for n in ("observations/render-control.json", "preflight/preflight.json")})
    never = {n: sha256(run / n) for g in SP.GAZES for n in truth_files(g)}
    never["observations/evaluation_only/instance-catalog.json"] = sha256(run / "observations/evaluation_only/instance-catalog.json")
    fz = {"schema": "AB1d2-observation-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "OBSERVATION FREEZE: the three 4096-spp binocular observations, their acquisition records and the "
                       "render-control comparison, frozen before any matching; never rerendered",
          "files": files, "evaluation_only_hashes_never_decoded": never,
          "calibrations": {g: files[SP.obs_rel(g, "calibration.json")] for g in SP.GAZES},
          "accepted_calibrations": SP.A1C_CALIBRATION,
          "rgb_observations": {g: files[SP.obs_rel(g, "rgb-observation.npz")] for g in SP.GAZES},
          "render_code": {n: sha256(REPO / n) for n in SP.RENDER_CODE}, "blend_sha256": sha256(REPO / SP.BLEND),
          "seeds": SP.SEEDS, "spp": SP.SPP, "accepted_spp": SP.ACCEPTED_SPP, "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-observation: {len(files)} files hashed; spp {SP.SPP}; calibrations equal the AB1c pins")
    return fz


def verify_observation_freeze(run: Path) -> dict:
    fz = read_json(run / "freeze/observation-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad:
        raise SystemExit(f"{PREFIX} STOP the observation freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ section 9: the frozen AB1d matcher, unchanged
def calib(run: Path, g: str) -> Path:
    return run / SP.obs_rel(g, "calibration.json")


def rgb(run: Path, g: str) -> Path:
    return run / SP.obs_rel(g, "rgb-observation.npz")


def match_guard_ok(run: Path, g: str) -> tuple[bool, dict]:
    rec = read_json(run / "match" / g / "match-opened-files.json")
    want = {str(calib(run, g).resolve()), str(rgb(run, g).resolve())}
    own = truth_reads(rec["events"], run)
    p = {"reads_exactly_calibration_and_rgb": set(rec["data_reads"]) == want, "violations_0": not rec["violations"],
         "modules_not_loaded": not any(rec["modules_loaded"].values()), "tripwires_0": not rec["cv2_tripwire_calls"],
         "ab1d_truth_reads_0": not any(rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                         "evaluation_reads")),
         "ab1d2_truth_reads_0": not any(own.values())}
    return all(p.values()), p | {"own_truth_reads": own}


def match(run: Path) -> dict:
    cs = code_state()
    once(run / "match" / SP.GAZES[0] / "matcher-record.npz", "the natural match")
    need(run / "freeze/observation-freeze.json", "freeze-observation")
    same_commit_report(run / "preflight/preflight-tests.json", "preflight-tests", cs)
    verify_observation_freeze(run)
    verify_sources()
    out = {}
    for g in SP.GAZES:
        summ = AD.run_match_gaze(calib(run, g), rgb(run, g), run / "match" / g)
        ok, p = match_guard_ok(run, g)
        loaded = {m: m in sys.modules for m in ("ab1d2_render", "bpy", "ab1d2_visuals")}
        if not ok or any(loaded.values()):
            raise SystemExit(f"{PREFIX} STOP {g} match guard: {p}; modules {loaded}")
        k = summ["counts"]
        print(f"{PREFIX} match {g}: textured {k['left_textured']:,}, natural valid {k['natural_valid']:,} / "
              f"{k['left_core']:,}; candidates median {summ['candidates']['admissible']['median']:.0f}; "
              f"{summ['seconds']:.1f} s; reads exactly calibration + 4096 RGB; truth reads 0")
        out[g] = summ
    return out


def corr_files(g: str) -> list[str]:
    return AD.corr_files(g)


def freeze_correspondence(run: Path) -> dict:
    path = run / "match/correspondence-freeze.json"
    once(path, "the natural correspondence freeze")
    ofz = verify_observation_freeze(run)
    files, inputs, guards = {}, {}, {}
    for g in SP.GAZES:
        for n in corr_files(g):
            need(run / n, n)
        ok, p = match_guard_ok(run, g)
        if not ok:
            raise SystemExit(f"{PREFIX} STOP {g} match guard: {p}")
        guards[g] = p
        files.update({n: sha256(run / n) for n in corr_files(g)})
        inputs[g] = {"calibration": {"path": str(calib(run, g)), "sha256": sha256(calib(run, g))},
                     "rgb_observation": {"path": str(rgb(run, g)), "sha256": sha256(rgb(run, g))}}
    # section 10: calibration-derived search geometry, bitwise identical to the accepted AB1d record (hard stop)
    ident = {}
    for g in SP.GAZES:
        a1d_rec = SP.a1d(f"match/{g}/matcher-record.npz")
        if sha256(a1d_rec) != SP.A1D_PINS[f"match/{g}/matcher-record.npz"]:
            raise SystemExit(f"{PREFIX} STOP the accepted AB1d record of {g} changed")
        ident[g] = geometry_identity(load_npz(a1d_rec), load_npz(run / f"match/{g}/matcher-record.npz"))
    gi = {"schema": "AB1d2-search-geometry-identity-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "calibration-derived matcher fields, 256 (accepted AB1d) vs 4096 (AB1d2), full core, bitwise",
          "fields": list(SP.GEOMETRY_FIELDS), "gazes": ident, "ok": all(v["ok"] for v in ident.values())}
    write_json(run / "match/search-geometry-identity.json", gi)
    if not gi["ok"]:
        raise SystemExit(f"{PREFIX} HARD STOP the search geometry differs between 256 and 4096: the experiment is "
                         f"confounded (match/search-geometry-identity.json)")
    import ab1d_spec as DS
    fz = {"schema": "AB1d2-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "NATURAL CORRESPONDENCE FREEZE (4096 spp): the three full-core matcher records and truth-stripped "
                       "natural products of the unchanged accepted AB1d matcher, frozen before any geometry and before "
                       "any oracle or Position product is opened",
          "files": files, "matcher_inputs": inputs, "guards": guards,
          "matcher_code": {n: sha256(REPO / n) for n in SP.MATCHER_CODE},
          "matcher_config_sha256": DS.config_sha256(DS.MATCHER),
          "observation_freeze_sha256": sha256(run / "freeze/observation-freeze.json"),
          "observation_freeze_rgb": ofz["rgb_observations"],
          "search_geometry_identity_sha256": sha256(run / "match/search-geometry-identity.json"),
          "search_geometry_identical": True, "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-correspondence: {len(files)} files hashed; search geometry bitwise identical to AB1d for "
          f"{len(SP.GEOMETRY_FIELDS)} fields x 3 gazes")
    return fz


def verify_correspondence_freeze(run: Path) -> dict:
    fz = read_json(run / "match/correspondence-freeze.json")
    want = {n for g in SP.GAZES for n in corr_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the natural correspondence freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ section 11: spherical geometry (accepted, unchanged)
def spherical(run: Path) -> dict:
    once(run / "spherical" / SP.GAZES[0] / "epipolar-result.npz", "the spherical geometry")
    need(run / "match/correspondence-freeze.json", "freeze-correspondence")
    verify_correspondence_freeze(run)
    verify_sources()
    out = {}
    for g in SP.GAZES:
        summ = AD.run_spherical_gaze(calib(run, g), run / "match" / g / "natural-correspondences.npz",
                                     run / "spherical" / g, run / "match/correspondence-freeze.json")
        rec = read_json(run / "spherical" / g / "spherical-opened-files.json")
        own = truth_reads(rec["events"], run)
        want = {str(calib(run, g).resolve()), str((run / "match" / g / "natural-correspondences.npz").resolve())}
        if (rec["violations"] or set(rec["data_reads"]) != want or any(rec["modules_loaded"].values())
                or any(own.values()) or any(rec[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                             "evaluation_reads"))):
            raise SystemExit(f"{PREFIX} STOP {g} spherical guard: {rec['violations']}; modules {rec['modules_loaded']}")
        k, dd = summ["counts"], summ["distributions"]
        print(f"{PREFIX} spherical {g}: triangulated {k['triangulated_epipolar']:,}/{k['correspondences']:,}; kappa "
              f"median {dd['kappa']['median']:.1f}; truth reads 0")
        out[g] = summ
    return out


def geom_files(g: str) -> list[str]:
    return AD.geom_files(g)


def freeze_geometry(run: Path) -> dict:
    import ab1b_geometry as BG
    path = run / "freeze/geometry-freeze.json"
    once(path, "the geometry freeze")
    for g in SP.GAZES:
        for n in geom_files(g):
            need(run / n, n)
    reads = ([run / "match/correspondence-freeze.json"] + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g)]
             + [calib(run, g) for g in SP.GAZES])
    with OpenGuard("ab1d2-freeze-geometry", reads, [run / "freeze"]) as gd:
        cfz = verify_correspondence_freeze(run)
        pre, files = {}, {}
        for g in SP.GAZES:
            prod = run / "match" / g / "natural-correspondences.npz"
            want = {str(calib(run, g).resolve()), str(prod.resolve())}
            sr = read_json(run / f"spherical/{g}/spherical-opened-files.json")
            ss = read_json(run / f"spherical/{g}/spherical-summary.json")
            p = {"spherical_reads_exactly_two": set(sr["data_reads"]) == want, "violations_0": not sr["violations"],
                 "truth_reads_0": not any(sr[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                          "evaluation_reads")) and not any(truth_reads(sr["events"], run).values()),
                 "no_cv2_no_matcher_no_planar": not any(sr["modules_loaded"].values()),
                 "frozen_product": ss["inputs"]["correspondences"]["sha256"] == cfz["files"][
                     f"match/{g}/natural-correspondences.npz"],
                 "same_calibration": ss["inputs"]["calibration"]["sha256"] == cfz["matcher_inputs"][g]["calibration"]["sha256"]
                 == SP.A1C_CALIBRATION[g]}
            if not all(p.values()):
                raise SystemExit(f"{PREFIX} STOP {g} geometry freeze preconditions: {p}")
            pre[g] = p
            files.update({n: sha256(run / n) for n in [f"match/{g}/natural-correspondences.npz"] + geom_files(g)})
        fz = {"schema": "AB1d2-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "GEOMETRY FREEZE: the truth-free spherical reconstruction (accepted AB1b geometry) of the "
                           "4096-spp natural correspondence of all three gazes, frozen before any benchmark, Position or "
                           "accepted AB1d evaluation product is opened",
              "files": files, "calibrations": {g: {"path": str(calib(run, g)), "sha256": sha256(calib(run, g))}
                                               for g in SP.GAZES},
              "correspondence_freeze_sha256": sha256(run / "match/correspondence-freeze.json"),
              "spherical_code": {n: sha256(REPO / n) for n in AD.SP.SPHERICAL_CODE},
              "spherical_config_sha256": BG.SP.config_sha256(BG.SP.GEOMETRY), "preconditions": pre,
              "code": code_state(), "frozen_utc": utc()}
        write_json(path, fz)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec.update(truth_reads(rec["events"], run))
    write_json(run / "freeze/geometry-freeze-opened-files.json", rec)
    print(f"{PREFIX} freeze-geometry: {len(files)} files hashed; spherical read exactly the calibration and the frozen "
          f"natural product; truth reads 0")
    return fz


def verify_geometry_freeze(run: Path) -> dict:
    fz = read_json(run / "freeze/geometry-freeze.json")
    want = {n for g in SP.GAZES for n in [f"match/{g}/natural-correspondences.npz"] + geom_files(g)}
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    bad += [g for g, v in fz["calibrations"].items() if sha256(v["path"]) != v["sha256"]]
    if bad or set(fz["files"]) != want:
        raise SystemExit(f"{PREFIX} STOP the frozen geometry does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ sections 13-17: paired evaluation (post-freeze)
def qd(a, mask=None) -> dict | None:
    a = np.asarray(a, np.float64)
    if mask is not None:
        a = a[np.asarray(mask, bool)]
    a = a[np.isfinite(a)].ravel()
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, v)) for k, v in SP.QUANTILES.items()} | {"count": int(a.size),
                                                                             "mean": float(a.mean())}


def frac(mask, n: int) -> float | None:
    return float(np.sum(mask) / n) if n else None


def two_by_two(before: np.ndarray, after: np.ndarray, names=("not_to_in", "in_to_in", "in_to_not", "not_to_not")) -> dict:
    before, after = np.asarray(before, bool), np.asarray(after, bool)
    n = before.size
    cnt = [int((~before & after).sum()), int((before & after).sum()), int((before & ~after).sum()),
           int((~before & ~after).sum())]
    return {k: {"count": c, "fraction": frac(c, n)} for k, c in zip(names, cnt)} | {"n": n}


def competing_score(rec: dict, idx: np.ndarray, s_oc: np.ndarray) -> np.ndarray:
    """Section 15: the best recorded distinct peak farther than ORACLE_PEAK_RADIUS_PX from ORACLE-ON-CURVE (NaN if none)."""
    ps, pz = np.asarray(rec["peak_s"])[idx], np.asarray(rec["peak_zncc"])[idx]
    far = np.isfinite(ps) & np.isfinite(pz) & (np.abs(ps - s_oc[:, None]) > SP.ORACLE_PEAK_RADIUS_PX)
    z = np.where(far, pz, -np.inf).max(axis=1)
    return np.where(np.isfinite(z), z, np.nan)


def paired_core(e256: dict, e4096: dict, rec256: dict, rec4096: dict) -> tuple[dict, dict]:
    """Sections 14-16 on the common evaluable set C."""
    i256, i4096 = np.asarray(e256["core_index"], np.int64), np.asarray(e4096["core_index"], np.int64)
    common = np.intersect1d(i256, i4096)
    a, b = np.searchsorted(i256, common), np.searchsorted(i4096, common)
    E0, E1 = np.abs(e256["e_px"][a]), np.abs(e4096["e_px"][b])
    dE = E1 - E0
    n = int(common.size)
    eps = SP.EQUAL_TOL_PX
    g0, g1 = E0 <= SP.GOOD_PX, E1 <= SP.GOOD_PX
    trans = two_by_two(g0, g1, ("bad_to_good", "good_to_good", "good_to_bad", "bad_to_bad"))
    Z0, Z1 = e256["zncc_oracle"][a], e4096["zncc_oracle"][b]
    dZ = Z1 - Z0
    fin = np.isfinite(Z0) & np.isfinite(Z1)
    r0, r1 = e256["oracle_rank"][a], e4096["oracle_rank"][b]
    s0, s1 = e256["s_oracle_on_curve"][a], e4096["s_oracle_on_curve"][b]
    c0, c1 = competing_score(rec256, common, s0), competing_score(rec4096, common, s1)
    m0, m1 = np.asarray(rec256["peak_margin"])[common], np.asarray(rec4096["peak_margin"])[common]
    b0, b1 = np.asarray(rec256["best_zncc"])[common], np.asarray(rec4096["best_zncc"])[common]
    x0, x1 = e256["error_3d_vs_perfect_m"][a], e4096["error_3d_vs_perfect_m"][b]
    dX = x1 - x0
    t0, t1 = np.asarray(rec256["left_patch_std_u8"])[common], np.asarray(rec4096["left_patch_std_u8"])[common]
    o0, o1 = e256["oracle_patch_std"][a], e4096["oracle_patch_std"][b]
    summ = {
        "counts": {"common": n, "evaluable_256": int(i256.size), "evaluable_4096": int(i4096.size),
                   "only_256": int(np.setdiff1d(i256, i4096).size), "only_4096": int(np.setdiff1d(i4096, i256).size),
                   "oracle_on_curve_identical": bool(np.array_equal(s0, s1))},
        "error": {"E256": qd(E0), "E4096": qd(E1), "delta_E": qd(dE), "median_E256": float(np.median(E0)) if n else None,
                  "median_E4096": float(np.median(E1)) if n else None,
                  "median_delta_E": float(np.median(dE)) if n else None,
                  "fraction_improved": frac(E1 < E0 - eps, n), "fraction_equal": frac(np.abs(E1 - E0) <= eps, n),
                  "fraction_worsened": frac(E1 > E0 + eps, n), "equal_tol_px": eps,
                  "improved_by_more_than_1px": frac(dE < -1.0, n), "worsened_by_more_than_1px": frac(dE > 1.0, n),
                  "within_1px_256": frac(g0, n), "within_1px_4096": frac(g1, n)},
        "transitions_1px": trans | {"good_px": SP.GOOD_PX},
        "zncc": {"Z256": qd(Z0), "Z4096": qd(Z1), "delta_Z": qd(dZ, fin), "fraction_increased": frac(fin & (dZ > SP.ZNCC_EQUAL_TOL), n),
                 "fraction_decreased": frac(fin & (dZ < -SP.ZNCC_EQUAL_TOL), n),
                 "fraction_equal": frac(fin & (np.abs(dZ) <= SP.ZNCC_EQUAL_TOL), n),
                 "unscorable_256": int((~np.isfinite(Z0)).sum()), "unscorable_4096": int((~np.isfinite(Z1)).sum()),
                 "oracle_minus_best_256": qd(Z0 - b0), "oracle_minus_best_4096": qd(Z1 - b1),
                 "best_256": qd(b0), "best_4096": qd(b1)},
        "ranks": {f"top{k}": two_by_two(r0 <= k, r1 <= k) for k in (1, 3, 8)}
        | {"top_fractions_256": {f"top{k}": frac(r0 <= k, n) for k in (1, 3, 5, 8)},
           "top_fractions_4096": {f"top{k}": frac(r1 <= k, n) for k in (1, 3, 5, 8)}},
        "competing_peak": {"C256": qd(c0), "C4096": qd(c1), "delta": qd(c1 - c0),
                           "none_256": int(np.isnan(c0).sum()), "none_4096": int(np.isnan(c1).sum())},
        "peak_margin": {"M256": qd(m0), "M4096": qd(m1), "delta": qd(m1 - m0)},
        "metric": {"error_3d_vs_perfect_256_m": qd(x0), "error_3d_vs_perfect_4096_m": qd(x1), "delta_m": qd(dX),
                   "fraction_improved": frac(x1 < x0 - SP.METRIC_EQUAL_TOL_M, n),
                   "fraction_worsened": frac(x1 > x0 + SP.METRIC_EQUAL_TOL_M, n)},
        "texture": {"left_patch_std_256_on_C": qd(t0), "left_patch_std_4096_on_C": qd(t1),
                    "oracle_patch_std_256_on_C": qd(o0), "oracle_patch_std_4096_on_C": qd(o1)},
        "strata_256_texture": strata_256(t0, E0, E1, r0, r1, Z0, Z1),
    }
    arrs = {"core_index": common.astype(np.int32), "E256": E0, "E4096": E1, "delta_E": dE, "Z256": Z0, "Z4096": Z1,
            "rank256": r0, "rank4096": r1, "competing256": c0, "competing4096": c1, "margin256": m0, "margin4096": m1,
            "best256": b0, "best4096": b1, "error3d256": x0, "error3d4096": x1, "texture256": t0, "texture4096": t1}
    return summ, arrs


def strata_256(t0, E0, E1, r0, r1, Z0, Z1) -> dict:
    """Section 17.5: quartiles of the 256-spp left patch std (edges from the 256 condition, applied to both)."""
    fin = np.isfinite(t0)
    out = {"edges": None, "bins": []}
    if fin.sum() < 4:
        return out
    q = [float(np.quantile(t0[fin], x)) for x in (0.25, 0.5, 0.75)]
    out["edges"] = q
    masks = [("Q1", fin & (t0 <= q[0])), ("Q2", fin & (t0 > q[0]) & (t0 <= q[1])), ("Q3", fin & (t0 > q[1]) & (t0 <= q[2])),
             ("Q4", fin & (t0 > q[2]))]
    for name, m in masks:
        k = int(m.sum())
        out["bins"].append({"stratum": name, "count": k,
                            "median_E256": float(np.median(E0[m])) if k else None,
                            "median_E4096": float(np.median(E1[m])) if k else None,
                            "within_1px_256": float((E0[m] <= SP.GOOD_PX).mean()) if k else None,
                            "within_1px_4096": float((E1[m] <= SP.GOOD_PX).mean()) if k else None,
                            "top1_256": float((r0[m] == 1).mean()) if k else None,
                            "top1_4096": float((r1[m] == 1).mean()) if k else None,
                            "median_Z256": float(np.nanmedian(Z0[m])) if k and np.isfinite(Z0[m]).any() else None,
                            "median_Z4096": float(np.nanmedian(Z1[m])) if k and np.isfinite(Z1[m]).any() else None})
    return out


def robust_std(x) -> float | None:
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return None
    return float(SP.MAD_SCALE * np.median(np.abs(x - np.median(x))))


def diagnostics(M, g256: tuple, g4096: tuple, ora: dict) -> dict:
    """Section 17: paired gray change; PROXY quantities (never a sensor-noise variance)."""
    o, n = SP.CORE_ORIGIN, SP.CORE_SIZE
    out = {"gray_change": {}, "PROXY_LR": {}, "PROXY_HP": {}}
    for s, a, b in (("L", g256[0], g4096[0]), ("R", g256[1], g4096[1])):
        d = b - a
        dc = d[o:o + n, o:o + n]
        out["gray_change"][s] = {"raster": {"abs": qd(np.abs(d)), "signed_mean": float(d.mean())},
                                 "core": {"abs": qd(np.abs(dc)), "signed_mean": float(dc.mean())}}
    u, v = np.asarray(ora["uv_L"])[:, 0].astype(np.int64), np.asarray(ora["uv_L"])[:, 1].astype(np.int64)
    for name, (gl, gr) in (("256", g256), ("4096", g4096)):
        rv, _ = M.bilinear(gr, np.asarray(ora["uv_R"])[:, 0], np.asarray(ora["uv_R"])[:, 1])
        out["PROXY_LR"][name] = robust_std(gl[v, u] - rv)
        cc = gl[o:o + n, o:o + n]
        nb = (gl[o - 1:o + n - 1, o:o + n] + gl[o + 1:o + n + 1, o:o + n] + gl[o:o + n, o - 1:o + n - 1]
              + gl[o:o + n, o + 1:o + n + 1]) / 4.0
        rs = robust_std(cc - nb)
        out["PROXY_HP"][name] = None if rs is None else rs / SP.HP_SCALE
    out["labels"] = {"gray_change": "DESCRIPTIVE paired change between two renders; not a noise estimate",
                     "PROXY_LR": "PROXY: robust std of G_L(oracle left pixel) - G_R(oracle right point); includes noise, "
                                 "view-dependent shading and sampling; REFERENCE / EVALUATION (uses the oracle)",
                     "PROXY_HP": "PROXY: robust std of the left-core 4-neighbour high-pass residual / sqrt(1.25); "
                                 "includes texture"}
    return out


def same_eval(a: dict, b: dict) -> dict:
    keys = sorted(set(a) | set(b))
    return {k: (k in a and k in b and same_array(a[k], b[k])) for k in keys}


def evaluation_files() -> list[str]:
    return (["evaluation/evaluation-summary.json", "evaluation/evaluation-opened-files.json"]
            + [f"evaluation/{g}/{n}" for g in SP.GAZES for n in ("evaluation-result.npz", "paired-result.npz")])


def a1d_paths() -> list[Path]:
    return [SP.a1d(k) for k in SP.A1D_PINS]


def pooled(per: dict, parr: list[dict]) -> dict:
    cat = {k: np.concatenate([p[k] for p in parr]) for k in ("E256", "E4096", "delta_E", "Z256", "Z4096", "rank256",
                                                             "rank4096", "error3d256", "error3d4096")}
    n = int(cat["E256"].size)
    fin = np.isfinite(cat["Z256"]) & np.isfinite(cat["Z4096"])
    dZ = cat["Z4096"] - cat["Z256"]
    return {"common": n, "E256": qd(cat["E256"]), "E4096": qd(cat["E4096"]), "delta_E": qd(cat["delta_E"]),
            "fraction_improved": frac(cat["E4096"] < cat["E256"] - SP.EQUAL_TOL_PX, n),
            "fraction_worsened": frac(cat["E4096"] > cat["E256"] + SP.EQUAL_TOL_PX, n),
            "transitions_1px": two_by_two(cat["E256"] <= SP.GOOD_PX, cat["E4096"] <= SP.GOOD_PX,
                                          ("bad_to_good", "good_to_good", "good_to_bad", "bad_to_bad")),
            "zncc": {"Z256": qd(cat["Z256"]), "Z4096": qd(cat["Z4096"]), "delta_Z": qd(dZ, fin),
                     "fraction_increased": frac(fin & (dZ > SP.ZNCC_EQUAL_TOL), n)},
            "top1": two_by_two(cat["rank256"] == 1, cat["rank4096"] == 1),
            "metric": {"error_3d_vs_perfect_256_m": qd(cat["error3d256"]),
                       "error_3d_vs_perfect_4096_m": qd(cat["error3d4096"])}}


def evaluate_paired(run: Path) -> dict:
    out = run / "evaluation"
    once(out / "evaluation-summary.json", "the paired evaluation")
    need(run / "freeze/geometry-freeze.json", "freeze-geometry")
    out.mkdir(parents=True, exist_ok=True)
    import ab1d_match as M
    import ab1d_spec as DS
    frozen = ([run / "freeze/geometry-freeze.json", run / "match/correspondence-freeze.json",
               run / "freeze/observation-freeze.json", run / "match/search-geometry-identity.json"]
              + [run / n for g in SP.GAZES for n in corr_files(g) + geom_files(g) + obs_files(g)]
              + [run / n for n in ("observations/render-control.json", "preflight/preflight.json")])
    accepted_obs = [SP.a1c_acq(g, n) for g in SP.GAZES for n in ("calibration.json", "rgb-observation.npz")]
    bench = [DS.oracle_path(g) for g in SP.GAZES] + [DS.perfect_path(g) for g in SP.GAZES] + [DS.reference_path(g)
                                                                                              for g in SP.GAZES]
    with OpenGuard("ab1d2-evaluation", frozen + accepted_obs + a1d_paths() + bench, [out]) as gd:
        verify_observation_freeze(run)
        verify_correspondence_freeze(run)
        verify_geometry_freeze(run)
        bad = verify_pins(SP.A1D_RUN, {k: h for k, h in SP.A1D_PINS.items() if not k.startswith("evaluation/")})
        if bad:
            raise SystemExit(f"{PREFIX} STOP accepted AB1d derived products changed: {bad}")
        gd.mark("freezes_verified")
        data = {}
        for g in SP.GAZES:
            c = read_json(calib(run, g))
            data[g] = {"c": c, "rec4096": load_npz(run / f"match/{g}/matcher-record.npz"),
                       "geo4096": load_npz(run / f"spherical/{g}/epipolar-result.npz"), "obs4096": load_npz(rgb(run, g)),
                       "rec256": load_npz(SP.a1d(f"match/{g}/matcher-record.npz")),
                       "geo256": load_npz(SP.a1d(f"spherical/{g}/epipolar-result.npz")),
                       "obs256": load_npz(SP.a1c_acq(g, "rgb-observation.npz"))}
            if sha256(SP.a1c_acq(g, "calibration.json")) != SP.A1C_CALIBRATION[g] or sha256(SP.a1c_acq(g, "rgb-observation.npz")) != SP.A1C_RGB[g]:
                raise SystemExit(f"{PREFIX} STOP accepted AB1c observation of {g} changed")
        gd.mark("reference_access_begins")
        bench_h = {}
        for p in bench:
            rel = str(p.relative_to(DS.A1C_RUN))
            h = sha256(p)
            if h != DS.BENCH_PINS[rel]:
                raise SystemExit(f"{PREFIX} STOP benchmark file changed: {rel}")
            bench_h[rel] = h
        bad = verify_pins(SP.A1D_RUN, {k: h for k, h in SP.A1D_PINS.items() if k.startswith("evaluation/")})
        if bad:
            raise SystemExit(f"{PREFIX} STOP accepted AB1d evaluation changed: {bad}")
        a1d_summary = read_json(SP.a1d("evaluation/evaluation-summary.json"))
        per, parr, repro = {}, [], {}
        for g in SP.GAZES:
            d = data[g]
            ora, perf = load_npz(DS.oracle_path(g)), load_npz(DS.perfect_path(g))
            with np.load(DS.reference_path(g), allow_pickle=False) as z:
                pos_l = np.asarray(z["position_w_L"])
            g256 = (M.gray(d["obs256"]["rgb_L"]), M.gray(d["obs256"]["rgb_R"]))
            g4096 = (M.gray(d["obs4096"]["rgb_L"]), M.gray(d["obs4096"]["rgb_R"]))
            ctx256, ctx4096 = M.Context(d["c"], *g256), M.Context(d["c"], *g4096)
            s4096, a4096 = AD.evaluation_core(d["c"], d["rec4096"], d["geo4096"], ora, perf, pos_l, ctx4096, M)
            s256, a256 = AD.evaluation_core(d["c"], d["rec256"], d["geo256"], ora, perf, pos_l, ctx256, M)
            acc_arr = load_npz(SP.a1d(f"evaluation/{g}/evaluation-result.npz"))
            arr_eq = same_eval(acc_arr, a256)
            sum_eq = json.loads(json.dumps(s256)) == a1d_summary["per_gaze"][g]
            repro[g] = {"arrays_equal": arr_eq, "summary_equal": sum_eq, "ok": all(arr_eq.values()) and sum_eq}
            if not repro[g]["ok"]:
                write_json(out / "reproduction-failure.json", repro)
                raise SystemExit(f"{PREFIX} HARD STOP the 256-spp evaluation does not reproduce the accepted AB1d result "
                                 f"for {g} (Outcome 4): {[k for k, v in arr_eq.items() if not v]} summary {sum_eq}")
            psumm, parrs = paired_core(a256, a4096, d["rec256"], d["rec4096"])
            psumm["diagnostics"] = diagnostics(M, g256, g4096, ora)
            psumm["diagnostics"]["left_patch_std_all"] = {"256": qd(d["rec256"]["left_patch_std_u8"]),
                                                          "4096": qd(d["rec4096"]["left_patch_std_u8"])}
            (out / g).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out / g / "evaluation-result.npz", **a4096)
            np.savez_compressed(out / g / "paired-result.npz", **parrs)
            per[g] = {"absolute_4096": s4096, "accepted_256": a1d_summary["per_gaze"][g], "paired": psumm}
            parr.append(parrs)
            p4, e = s4096["primary"], psumm["error"]
            print(f"{PREFIX} evaluate {g}: 4096 evaluable {s4096['counts']['evaluable']:,}; |px-eq| median "
                  f"{p4['px_equivalent_abs']['median']:.3f} p95 {p4['px_equivalent_abs']['p95']:.2f}; <=1px "
                  f"{p4['px_equivalent_fractions']['1']:.3f}; top1 {s4096['landscape']['top_fractions']['top1']:.3f} | paired "
                  f"C {psumm['counts']['common']:,}: median E {e['median_E256']:.2f} -> {e['median_E4096']:.2f}; improved "
                  f"{e['fraction_improved']:.3f}; bad->good {psumm['transitions_1px']['bad_to_good']['count']:,}, "
                  f"good->bad {psumm['transitions_1px']['good_to_bad']['count']:,}; 256 reproduction exact")
        summary = {"schema": "AB1d2-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE,
                   "statement": "REFERENCE / EVALUATION: after all freezes, the 4096-spp natural correspondence and the "
                                "accepted 256-spp AB1d correspondence are scored with the accepted AB1d evaluation "
                                "against the SAME AB1c benchmark and paired pixel by pixel; descriptive only; the new "
                                "4096 truth passes are not opened",
                   "benchmark_files": bench_h, "reproduction_256": repro, "per_gaze": per,
                   "pooled": pooled(per, parr),
                   "constants": {"equal_tol_px": SP.EQUAL_TOL_PX, "zncc_equal_tol": SP.ZNCC_EQUAL_TOL,
                                 "metric_equal_tol_m": SP.METRIC_EQUAL_TOL_M, "good_px": SP.GOOD_PX,
                                 "oracle_peak_radius_px": SP.ORACLE_PEAK_RADIUS_PX, "mad_scale": SP.MAD_SCALE,
                                 "hp_scale": SP.HP_SCALE, "quantiles": SP.QUANTILES},
                   "code": code_state()}
        write_json(out / "evaluation-summary.json", summary)
    rec = gd.record()
    rec["truth_firewall_violations"] = len(rec["violations"])
    rec.update(truth_reads(rec["events"], run))
    write_json(out / "evaluation-opened-files.json", rec)
    if rec["violations"] or rec["ab1d2_truth_reads"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard: {rec['violations'][:3]}; AB1d2 truth reads {rec['ab1d2_truth_reads']}")
    return summary


# ------------------------------------------------------------------ manifest / CLI
def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "AB1d2-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "a1c_run": str(SP.A1C_RUN), "a1d_run": str(SP.A1D_RUN), "truth": TRUTH_CLASSES,
         "files": {f: sha256(run / f) for f in files}}
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
    status = "failed"
    try:
        if a.cmd == "preflight-tests":
            ok = preflight_tests(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd == "rehearse":
            ok = rehearse(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd in SP.CANONICAL:
            require_committed(a.cmd)
        {"source": source, "preflight": preflight, "render-4096": render_4096, "freeze-observation": freeze_observation,
         "match": match, "freeze-correspondence": freeze_correspondence, "spherical": spherical,
         "freeze-geometry": freeze_geometry, "evaluate-paired": evaluate_paired}.get(a.cmd, lambda r: None)(run)
        if a.cmd == "visualize":
            import ab1d2_visuals
            ab1d2_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
