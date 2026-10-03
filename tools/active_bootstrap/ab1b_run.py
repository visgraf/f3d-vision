"""Active Bootstrap-1b: gaze-centered spherical epipolar geometry on the saved AB1a pair (run order and truth boundary).

Contract: docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md.

    .venv/bin/python tools/active_bootstrap/ab1b_run.py synthetic             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py oracle                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py geometry              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py evaluate              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1b_run.py visualize             --run RUN --visuals VIS

No new observation: no Blender, no render, no gaze.  ``oracle`` alone reads Position / Object Index and writes a
truth-stripped product, frozen by ``freeze-correspondence``; ``geometry`` reads only the calibration and that product;
``freeze-geometry`` freezes it; only then ``evaluate`` reopens Position (REFERENCE / EVALUATION) and the AB1a summaries.
This module imports neither cv2 nor fsg_stereo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as G  # noqa: E402
import ab1b_oracle as O  # noqa: E402
import ab1b_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

PREFIX = "[ab1b]"
sha256 = O.sha256
write_json = O.write_json


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
    if not path.is_file():
        raise SystemExit(f"{PREFIX} STOP {what} comes first ({path} missing)")


def verify_sources() -> None:
    bad = {p: sha256(SP.REPO / p) for p, h in SP.SOURCE_PINS.items() if sha256(SP.REPO / p) != h}
    if bad:
        raise SystemExit(f"{PREFIX} STOP accepted sources changed: {bad}")


def ab1a(rel: str) -> Path:
    return SP.AB1A_RUN / rel


# ------------------------------------------------------------------ source (section 2)
def source(run: Path) -> dict:
    out = run / "source/ab1a-source-manifest.json"
    once(out, "the source manifest")
    verify_sources()
    got = {rel: sha256(ab1a(rel)) for rel in SP.PRE_FREEZE_HASHED}
    bad = {rel: h for rel, h in got.items() if h != SP.AB1A_PINS[rel]}
    man = read_json(ab1a("manifest.json"))
    listed = {rel: man["files"].get(rel) for rel in SP.AB1A_PINS if rel not in ("manifest.json", "process-log.jsonl")}
    bad_listed = {rel: h for rel, h in listed.items() if h != SP.AB1A_PINS[rel]}
    if bad or bad_listed:
        raise SystemExit(f"{PREFIX} STOP AB1a source identity mismatch: hashed {bad}; manifest {bad_listed}")
    act = read_json(ab1a("source/nb1c-action-manifest.json"))["gaze"]
    want = {"rank": SP.GAZE_RANK, "row": SP.GAZE_ROW, "col": SP.GAZE_COL, "yaw_deg": SP.GAZE_YAW_DEG,
            "pitch_deg": SP.GAZE_PITCH_DEG}
    c = read_json(ab1a(SP.CALIBRATION_REL))
    FG.validate_calibration(c)
    ident = {"gaze": c["gaze_yaw_pitch_deg"] == [SP.GAZE_YAW_DEG, SP.GAZE_PITCH_DEG], "profile": c["profile"] == SP.PROFILE,
             "raster": c["image_size_wh"] == [SP.RAW_SIZE, SP.RAW_SIZE], "core": c["core_size"] == SP.CORE_SIZE,
             "ipd": c["ipd_m"] == SP.IPD_M, "tangent_frame": c.get("tangent_frame") == SP.TANGENT_FRAME,
             "focal": all(e["K"][0][0] == SP.FOCAL_PX and e["K"][1][1] == SP.FOCAL_PX for e in c["eyes"])}
    log = [json.loads(x) for x in ab1a("process-log.jsonl").read_text().splitlines() if x.strip()]
    acquires = [e for e in log if e["command"] == "acquire"]
    if {k: act[k] for k in want} != want or not all(ident.values()) or len(acquires) != 1:
        raise SystemExit(f"{PREFIX} STOP AB1a action / calibration identity: action {act}; {ident}; acquires {len(acquires)}")
    rec = {"schema": "AB1b-source-manifest-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
           "statement": "NO NEW OBSERVATION: the accepted AB1a gaze-#1 pair and its saved evaluation-only Position / Object "
                        "Index are re-analysed in place; no Blender, no render, no gaze. Before the geometry freeze only "
                        "the pre-freeze inputs are hashed; the AB1a results are only checked against the AB1a manifest",
           "ab1a_run": str(SP.AB1A_RUN), "pins": SP.AB1A_PINS, "hashed_before_geometry_freeze": got,
           "listed_in_ab1a_manifest": listed, "action_source": SP.ACTION_SOURCE, "gaze": act,
           "calibration_identity": ident, "ab1a_acquire_entries": len(acquires),
           "accepted_sources": SP.SOURCE_PINS, "base_commit": SP.BASE_COMMIT, "code": code_state(), "created_utc": utc()}
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, rec)
    print(f"{PREFIX} source: AB1a pins verified ({len(got)} hashed, {len(listed)} manifest-listed); gaze "
          f"({act['yaw_deg']:+.2f}, {act['pitch_deg']:+.2f}); one AB1a acquisition; no new observation")
    return rec


# ------------------------------------------------------------------ oracle + correspondence freeze (section 5)
def oracle(run: Path) -> dict:
    once(run / "oracle/oracle-correspondences.npz", "the oracle product")
    need(run / "source/ab1a-source-manifest.json", "source")
    verify_sources()
    summ = O.run_oracle(ab1a(SP.CALIBRATION_REL), ab1a(SP.REFERENCE_REL), run / "oracle")
    rec = read_json(run / "oracle/oracle-opened-files.json")
    if rec["violations"] or any(rec["modules_loaded"].values()):
        raise SystemExit(f"{PREFIX} STOP oracle guard: violations {rec['violations']}; modules {rec['modules_loaded']}")
    a = " -> ".join(f"{x['remaining']:,}" for x in summ["attrition"])
    print(f"{PREFIX} oracle: {summ['correspondences']:,} perfect correspondences ({summ['fraction_of_core']:.4f} of the "
          f"core); attrition {a}; right matches outside the right nominal core "
          f"{summ['right_margin']['outside_right_nominal_core']:,}; data reads {len(rec['data_reads'])}")
    return summ


def freeze_correspondence(run: Path) -> dict:
    path = run / "oracle/correspondence-freeze.json"
    once(path, "the correspondence freeze")
    for n in SP.FROZEN_CORRESPONDENCE:
        need(run / n, n)
    rec = read_json(run / "oracle/oracle-opened-files.json")
    want = {str(ab1a(SP.CALIBRATION_REL)), str(ab1a(SP.REFERENCE_REL))}
    if rec["violations"] or set(rec["data_reads"]) != want:
        raise SystemExit(f"{PREFIX} STOP oracle reads {rec['data_reads']}; violations {rec['violations']}")
    fz = {"schema": "AB1b-correspondence-freeze-v1", "truth": SP.TRUTH_DERIVED,
          "statement": "the truth-stripped perfect-correspondence product, frozen before the spherical geometry stage runs",
          "files": {n: sha256(run / n) for n in SP.FROZEN_CORRESPONDENCE},
          "oracle_inputs": {"calibration": {"path": str(ab1a(SP.CALIBRATION_REL)), "sha256": sha256(ab1a(SP.CALIBRATION_REL))},
                            "reference_observation": {"path": str(ab1a(SP.REFERENCE_REL)),
                                                      "sha256": sha256(ab1a(SP.REFERENCE_REL))}},
          "oracle_code": {n: sha256(REPO / n) for n in SP.ORACLE_CODE},
          "oracle_config_sha256": SP.config_sha256(SP.ORACLE), "oracle_violations": len(rec["violations"]),
          "code": code_state(), "frozen_utc": utc()}
    write_json(path, fz)
    print(f"{PREFIX} freeze-correspondence: {len(fz['files'])} files hashed; product "
          f"{fz['files']['oracle/oracle-correspondences.npz'][:12]}")
    return fz


def verify_correspondence_freeze(run: Path) -> dict:
    fz = read_json(run / "oracle/correspondence-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if bad or set(fz["files"]) != set(SP.FROZEN_CORRESPONDENCE):
        raise SystemExit(f"{PREFIX} STOP the correspondence freeze does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ geometry + geometry freeze (sections 7-12)
def geometry(run: Path) -> dict:
    once(run / "geometry/epipolar-result.npz", "the geometry result")
    need(run / "oracle/correspondence-freeze.json", "freeze-correspondence")
    verify_sources()
    summ = G.run_geometry(ab1a(SP.CALIBRATION_REL), run / "oracle/oracle-correspondences.npz", run / "geometry")
    rec = read_json(run / "geometry/geometry-opened-files.json")
    if (rec["violations"] or any(rec["modules_loaded"].values()) or rec["position_reads"]
            or rec["object_index_reads"] or rec["ab1a_natural_result_reads"]):
        raise SystemExit(f"{PREFIX} STOP geometry guard: {rec['violations']}; modules {rec['modules_loaded']}")
    k, lc, dd = summ["counts"], summ["left_core"], summ["distributions"]
    print(f"{PREFIX} geometry: left-core rays {lc['rays']:,} (finite {lc['finite']:,}, singular {lc['pole_singular']}); "
          f"theta {lc['theta_deg']['min']:.3f}..{lc['theta_deg']['max']:.3f} deg; min angle to pole "
          f"{lc['min_angle_to_baseline_pole_deg']:.3f} deg; triangulated {k['triangulated_epipolar']:,}/"
          f"{k['correspondences']:,}; data reads {len(rec['data_reads'])}; truth reads 0")
    if dd["abs_phi_residual_rad"]:
        print(f"{PREFIX} geometry: |phi residual| median {dd['abs_phi_residual_rad']['median']:.3e} max "
              f"{dd['abs_phi_residual_rad']['max']:.3e} rad; delta_theta median {dd['delta_theta_rad']['median']:.4e} rad; "
              f"kappa median {dd['kappa']['median']:.1f}")
    return summ


def freeze_geometry(run: Path) -> dict:
    path = run / "geometry/geometry-freeze.json"
    once(path, "the geometry freeze")
    for n in SP.FROZEN_GEOMETRY:
        need(run / n, n)
    reads = ([run / n for n in SP.FROZEN_CORRESPONDENCE + SP.FROZEN_GEOMETRY]
             + [ab1a(SP.CALIBRATION_REL)])
    with OpenGuard("ab1b-freeze-geometry", reads, [run / "geometry"]) as g:
        cfz = verify_correspondence_freeze(run)
        summ = read_json(run / "geometry/geometry-summary.json")
        rec = read_json(run / "geometry/geometry-opened-files.json")
        calib_sha = sha256(ab1a(SP.CALIBRATION_REL))
        want_reads = {str(ab1a(SP.CALIBRATION_REL)), str((run / "oracle/oracle-correspondences.npz").resolve())}
        problems = {
            "input_product_hash": summ["inputs"]["correspondences"]["sha256"] == cfz["files"]["oracle/oracle-correspondences.npz"],
            "input_calibration_hash": summ["inputs"]["calibration"]["sha256"] == cfz["oracle_inputs"]["calibration"]["sha256"]
            == calib_sha == SP.AB1A_PINS[SP.CALIBRATION_REL],
            "data_reads_exactly_two": set(rec["data_reads"]) == want_reads,
            "violations_0": not rec["violations"],
            "position_reads_0": rec["position_reads"] == 0, "object_index_reads_0": rec["object_index_reads"] == 0,
            "ab1a_natural_result_reads_0": rec["ab1a_natural_result_reads"] == 0,
            "no_cv2_no_fsg_stereo": not any(rec["modules_loaded"].values())}
        if not all(problems.values()):
            raise SystemExit(f"{PREFIX} STOP geometry freeze preconditions: {problems}")
        fz = {"schema": "AB1b-geometry-freeze-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "GEOMETRY FREEZE: the truth-free spherical epipolar geometry, frozen before any Position truth is "
                           "reopened for evaluation",
              "files": {n: sha256(run / n) for n in SP.FROZEN_GEOMETRY},
              "calibration_source": {"path": str(ab1a(SP.CALIBRATION_REL)), "sha256": calib_sha},
              "correspondence_freeze_sha256": sha256(run / "oracle/correspondence-freeze.json"),
              "geometry_code": {n: sha256(REPO / n) for n in SP.GEOMETRY_CODE},
              "geometry_config_sha256": SP.config_sha256(SP.GEOMETRY), "preconditions": problems,
              "position_reads": rec["position_reads"], "object_index_reads": rec["object_index_reads"],
              "ab1a_natural_result_reads": rec["ab1a_natural_result_reads"],
              "geometry_violations": len(rec["violations"]), "code": code_state(), "frozen_utc": utc()}
        write_json(path, fz)
    grec = g.record()
    grec["truth_firewall_violations"] = len(grec["violations"])
    write_json(run / "geometry/geometry-freeze-opened-files.json", grec)
    print(f"{PREFIX} freeze-geometry: {len(fz['files'])} files hashed; Position reads 0; Object Index reads 0; AB1a "
          f"natural-result reads 0")
    return fz


def verify_geometry_freeze(run: Path) -> dict:
    fz = read_json(run / "geometry/geometry-freeze.json")
    bad = [n for n, h in fz["files"].items() if sha256(run / n) != h]
    if (bad or set(fz["files"]) != set(SP.FROZEN_GEOMETRY)
            or sha256(fz["calibration_source"]["path"]) != fz["calibration_source"]["sha256"]):
        raise SystemExit(f"{PREFIX} STOP the frozen geometry does not verify: {bad}")
    return fz


# ------------------------------------------------------------------ post-freeze evaluation (sections 13-14)
def load_result(run: Path) -> dict:
    with np.load(run / "geometry/epipolar-result.npz", allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def _q(a, mask=None):
    return G.quantiles(a, mask)


def errors(p, p_truth, mask, o_l) -> dict:
    p, t = np.asarray(p, np.float64)[mask], np.asarray(p_truth, np.float64)[mask]
    e3 = np.linalg.norm(p - t, axis=-1)
    rt = np.linalg.norm(t - o_l, axis=-1)
    rad = np.linalg.norm(p - o_l, axis=-1) - rt
    return {"pairs": int(np.asarray(mask).sum()), "error_3d_m": _q(e3), "radial_abs_m": _q(np.abs(rad)),
            "radial_signed_m": _q(rad), "radial_relative_abs": _q(np.abs(rad) / rt),
            "fraction_3d_within_m": ({f"{s:.3f}": float((e3 <= s).mean()) for s in SP.ERROR_FRACTIONS_M} if e3.size else None)}


def evaluation_core(c: dict, res: dict, uv_r: np.ndarray, ref: dict, names: dict) -> tuple[dict, dict]:
    """Post-freeze descriptors: P_truth at the saved left-core indices, errors, reprojection, composition."""
    rows = res["left_core_row"].astype(np.int64) + SP.CORE_ORIGIN
    cols = res["left_core_col"].astype(np.int64) + SP.CORE_ORIGIN
    pos = np.asarray(ref["position_w_L"])[rows, cols].astype(np.float64)
    ids = np.asarray(ref["instance_L"])[rows, cols].astype(np.int64)
    p_truth = FG.world_to_head(c, pos)
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    ve, vr = res["valid_epi"].astype(bool), res["valid_ray"].astype(bool)
    uv_l = np.stack([cols, rows], axis=-1).astype(np.float64)
    with np.errstate(invalid="ignore"):
        uvl_p, _ = FG.project_h(c["eyes"][0], res["P_epi"])
        uvr_p, _ = FG.project_h(c["eyes"][1], res["P_epi"])
    rep_l = np.linalg.norm(uvl_p - uv_l, axis=-1)
    rep_r = np.linalg.norm(uvr_p - np.asarray(uv_r, np.float64), axis=-1)
    e3_epi = np.linalg.norm(res["P_epi"] - p_truth, axis=-1)
    e3_ray = np.linalg.norm(res["P_ray"] - p_truth, axis=-1)
    rad_epi = np.linalg.norm(res["P_epi"] - o_l, axis=-1) - np.linalg.norm(p_truth - o_l, axis=-1)
    rad_ray = np.linalg.norm(res["P_ray"] - o_l, axis=-1) - np.linalg.norm(p_truth - o_l, axis=-1)
    inst, cnt = np.unique(ids, return_counts=True)
    order = sorted(zip(cnt.tolist(), inst.tolist()), key=lambda t: (-t[0], t[1]))
    per_instance = []
    for k, i in order:
        if k >= SP.MIN_INSTANCE_PAIRS:
            m = ve & (ids == i)
            per_instance.append({"instance_id": int(i), "object_name": names.get(int(i), ""), "pairs": int(k),
                                 "error_3d_m": _q(e3_epi, m), "radial_signed_m": _q(rad_epi, m)})
    summary = {
        "truth_range_L_m": _q(np.linalg.norm(p_truth - o_l, axis=-1)),
        "epipolar_vs_truth": errors(res["P_epi"], p_truth, ve, o_l),
        "ray_ray_vs_truth": errors(res["P_ray"], p_truth, vr, o_l),
        "reprojection_px": {"left": _q(rep_l, ve), "right": _q(rep_r, ve)},
        "composition": {"pairs": int(len(rows)), "distinct_instances": int(len(inst)),
                        "instances": [{"instance_id": int(i), "object_name": names.get(int(i), ""), "pairs": int(k)}
                                      for k, i in order]},
        "per_instance_errors": {"minimum_pairs": SP.MIN_INSTANCE_PAIRS, "instances": per_instance},
    }
    arrays = {"left_core_row": res["left_core_row"], "left_core_col": res["left_core_col"],
              "P_truth": p_truth, "left_instance": ids.astype(np.int32), "error_3d_epi_m": e3_epi,
              "error_3d_ray_m": e3_ray, "radial_signed_epi_m": rad_epi, "radial_signed_ray_m": rad_ray,
              "reprojection_L_px": rep_l, "reprojection_R_px": rep_r}
    return summary, arrays


def ab1a_comparison(rays: int, n_pairs: int, n_tri: int) -> dict:
    got = {rel: sha256(ab1a(rel)) for rel in SP.POST_FREEZE_COMPARISON}
    bad = {rel: h for rel, h in got.items() if h != SP.AB1A_PINS[rel]}
    if bad:
        raise SystemExit(f"{PREFIX} STOP AB1a comparison files changed: {bad}")
    st = read_json(ab1a("measurement/stereo-summary.json"))
    ev = read_json(ab1a("evaluation/evaluation-summary.json"))
    pre = read_json(ab1a("prelook/prelook-geometry.json"))["eyes"]["L"]
    return {"statement": "POST-FREEZE, DESCRIPTIVE ONLY: read after the AB1b geometry freeze; it changes nothing in AB1b",
            "sha256": got,
            "ab1a_planar_rectified": {"core_pixels": st["core_pixels"], "natural_valid": st["valid_count"],
                                      "reference_valid": ev["counts"]["reference_valid"],
                                      "rectified_core_raw_source_px_L": pre["raw_source_of_rectified_core_px"],
                                      "rectified_core_pixels_from_nominal_raw_core": pre["rectified_core_pixels_from_nominal_raw_core"],
                                      "rectified_core_centre_from_gaze_deg": pre["rectified_core_centre_from_gaze_deg"],
                                      "rectified_core_centre_from_baseline_deg": pre["rectified_core_centre_from_baseline_deg"]},
            "ab1b_spherical_raw_core": {"core_pixels": SP.CORE_SIZE * SP.CORE_SIZE, "raw_core_rays_represented": rays,
                                        "perfect_correspondences": n_pairs, "triangulated": n_tri}}


def evaluate(run: Path) -> dict:
    out = run / "evaluation"
    once(out / "evaluation-summary.json", "the evaluation")
    need(run / "geometry/geometry-freeze.json", "freeze-geometry")
    out.mkdir(parents=True, exist_ok=True)
    frozen = [run / n for n in SP.FROZEN_GEOMETRY] + [run / "geometry/geometry-freeze.json", ab1a(SP.CALIBRATION_REL)]
    refs = [ab1a(SP.REFERENCE_REL), ab1a(SP.CATALOG_REL)] + [ab1a(r) for r in SP.POST_FREEZE_COMPARISON]
    with OpenGuard("ab1b-evaluation", frozen + refs, [out]) as g:
        fz = verify_geometry_freeze(run)
        g.mark("geometry_freeze_verified")
        c = read_json(ab1a(SP.CALIBRATION_REL))
        res = load_result(run)
        with np.load(run / "oracle/oracle-correspondences.npz", allow_pickle=False) as z:
            uv_r = np.asarray(z["uv_R"])
        with np.load(run / "geometry/left-core-rays.npz", allow_pickle=False) as z:
            n_rays = int(np.isfinite(np.asarray(z["theta"])).sum())
        g.mark("reference_access_begins")
        if sha256(ab1a(SP.REFERENCE_REL)) != SP.AB1A_PINS[SP.REFERENCE_REL]:
            raise SystemExit(f"{PREFIX} STOP reference observation changed")
        ref = O.load_reference(ab1a(SP.REFERENCE_REL))
        cat = read_json(ab1a(SP.CATALOG_REL))["instances"]
        names = {int(e["instance_id"]): e["object_name"] for e in cat}
        summ, arrays = evaluation_core(c, res, uv_r, ref, names)
        g.mark("ab1a_comparison_begins")
        comp = ab1a_comparison(n_rays, int(len(res["valid_epi"])), int(res["valid_epi"].sum()))
        summary = {"schema": "AB1b-evaluation-summary-v1", "truth": SP.TRUTH_REFERENCE, "computed_after_freeze": True,
                   "statement": "POST-FREEZE REFERENCE / EVALUATION: Position (its second role) scores the frozen "
                                "truth-free reconstructions; descriptive, no pass / fail, changes nothing",
                   "geometry_freeze_sha256": sha256(run / "geometry/geometry-freeze.json"),
                   "frozen_geometry_sha256": fz["files"], "reference_sha256": SP.AB1A_PINS[SP.REFERENCE_REL],
                   "quantiles": SP.QUANTILES, "error_fraction_scales_m": list(SP.ERROR_FRACTIONS_M),
                   **summ, "ab1a_comparison": comp}
        np.savez_compressed(out / "evaluation-result.npz", **arrays)
        write_json(out / "evaluation-summary.json", summary)
    rec = g.record()
    rec["ordered_data_events"] = [e.get("label") or e.get("path") for e in rec["events"]
                                  if e.get("event") == "mark" or e.get("kind") == "data-read"]
    rec["truth_firewall_violations"] = len(rec["violations"])
    write_json(out / "evaluation-opened-files.json", rec)
    verify_geometry_freeze(run)
    if rec["violations"]:
        raise SystemExit(f"{PREFIX} STOP evaluation guard violations: {rec['violations']}")
    e, a = summary["epipolar_vs_truth"]["error_3d_m"], summary["ab1a_comparison"]
    err = "none" if e is None else f"median {e['median']:.3e}, p95 {e['p95']:.3e}, max {e['max']:.3e} m"
    print(f"{PREFIX} evaluate: P_epi vs Position over {summary['epipolar_vs_truth']['pairs']:,} pairs: 3-D error {err}; "
          f"AB1a planar {a['ab1a_planar_rectified']['reference_valid']}/{a['ab1a_planar_rectified']['core_pixels']} vs AB1b "
          f"{a['ab1b_spherical_raw_core']['triangulated']:,}; frozen geometry re-verified")
    return summary


# ------------------------------------------------------------------ synthetic known answers (section 11)
B0 = SP.IPD_M
O_L, O_R = np.array([-B0 / 2, 0.0, 0.0]), np.array([B0 / 2, 0.0, 0.0])


def _rays(p):
    p = np.atleast_2d(np.asarray(p, np.float64))
    return FG.unit(p - O_L), FG.unit(p - O_R)


def _tri(d_l, d_r, b=B0):
    th_l, ph_l, _ = G.theta_phi(d_l)
    th_r, ph_r, _ = G.theta_phi(d_r)
    return G.triangulate_epipolar(th_l, th_r, ph_l, ph_r, b), (th_l, th_r, ph_l, ph_r)


def _sph(theta, phi):
    return np.stack([np.cos(theta), np.sin(theta) * np.sin(phi), -np.sin(theta) * np.cos(phi)], axis=-1)


def gaze1_calibration() -> dict:
    return FG.make_calibration(SP.PROFILE, SP.GAZE_YAW_DEG, SP.GAZE_PITCH_DEG, 2.10, ipd=SP.IPD_M,
                               tangent_frame=SP.TANGENT_FRAME)


def analytic_scene(c: dict, occluder: bool = True) -> tuple[dict, list]:
    """Analytic Position / Object Index (float32 Position, like Blender) for a 4 m plane normal to the cyclopean gaze
    (id 1) behind a finite 2 m patch (id 2).  Returns the reference observation and the planes."""
    n = FG.unit(FG.gaze_direction(*c["gaze_yaw_pitch_deg"]))
    a = FG.unit(np.cross(n, [0.0, 1.0, 0.0]))
    b = np.cross(n, a)
    planes = [{"id": 1, "dist": 4.0, "half": None}] + ([{"id": 2, "dist": 2.0, "half": 0.12}] if occluder else [])
    out = {}
    w, h = c["image_size_wh"]
    for i, side in enumerate(("L", "R")):
        eye = c["eyes"][i]
        o = np.asarray(eye["centre_h_m"], np.float64)
        d = FG.rays_h(eye, FG.pixels(w, h))
        pid, pos = cast(o, d, n, a, b, planes)
        out[f"instance_{side}"] = pid.astype(np.int32)
        out[f"position_w_{side}"] = np.where((pid > 0)[..., None], FG.head_to_world(c, pos), 0.0).astype(np.float32)
    return out, (n, a, b, planes)


def cast(o, d, n, a, b, planes):
    best = np.full(d.shape[:-1], np.inf)
    pid = np.zeros(d.shape[:-1], np.int64)
    for p in planes:
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (p["dist"] - o @ n) / (d @ n)
        x = o + d * t[..., None]
        ok = np.isfinite(t) & (t > 0) & (t < best)
        if p["half"] is not None:
            q = x - n * p["dist"]
            ok &= (np.abs(q @ a) <= p["half"]) & (np.abs(q @ b) <= p["half"])
        best = np.where(ok, t, best)
        pid = np.where(ok, p["id"], pid)
    pos = o + d * np.where(np.isfinite(best), best, 0.0)[..., None]
    return pid, pos


def _e2e(td: Path, ref: dict, c: dict) -> tuple[dict, dict, dict]:
    (td / "src").mkdir(parents=True, exist_ok=True)
    write_json(td / "src/calibration.json", c)
    np.savez_compressed(td / "src/reference-observation.npz", **ref)
    O.run_oracle(td / "src/calibration.json", td / "src/reference-observation.npz", td / "oracle")
    write_json(td / "oracle/correspondence-freeze.json",
               {"files": {"oracle/oracle-correspondences.npz": sha256(td / "oracle/oracle-correspondences.npz")}})
    G.run_geometry(td / "src/calibration.json", td / "oracle/oracle-correspondences.npz", td / "geometry")
    with np.load(td / "oracle/oracle-correspondences.npz") as z:
        prod = {k: np.asarray(z[k]) for k in z.files}
    with np.load(td / "geometry/epipolar-result.npz") as z:
        res = {k: np.asarray(z[k]) for k in z.files}
    return prod, res, read_json(td / "geometry/geometry-opened-files.json")


def synthetic_cases() -> list[tuple]:
    cases = []
    P_FWD = np.array([0.10, 0.05, -2.0])

    def forward():
        d_l, d_r = _rays(P_FWD)
        e, (tl, tr, pl, pr) = _tri(d_l, d_r)
        err = float(np.linalg.norm(e["P_epi"][0] - P_FWD))
        ok = abs(float(pl[0] - pr[0])) <= SP.SYN_PHI_EXACT and float(tr[0] - tl[0]) > 0 and err <= SP.SYN_EXACT_M
        return ok, {"phi_residual": float(pr[0] - pl[0]), "delta_theta": float(tr[0] - tl[0]), "error_m": err}
    cases.append(("forward point: phi_L = phi_R, delta_theta > 0, exact reconstruction", forward))

    def planes():
        worst_phi = worst = 0.0
        for phi_deg in (-150.0, -60.0, 0.0, 45.0, 120.0, 179.0):
            for r in (0.5, 2.0, 6.0):
                phi = math.radians(phi_deg)
                p = r * _sph(math.radians(70.0), phi)
                d_l, d_r = _rays(p)
                e, (_tl, _tr, pl, pr) = _tri(d_l, d_r)
                worst_phi = max(worst_phi, abs(float(G.wrap_pi(pl[0] - phi))), abs(float(G.wrap_pi(pr[0] - phi))))
                worst = max(worst, float(np.linalg.norm(e["P_epi"][0] - p)))
        return worst_phi <= SP.SYN_PHI_EXACT and worst <= SP.SYN_EXACT_M, {"max_phi_error": worst_phi, "max_error_m": worst}
    cases.append(("several epipolar planes: correct phi and XYZ", planes))

    def near_pole():
        p = np.array([5.0, 0.01, -0.02])
        d_l, d_r = _rays(p)
        e, (tl, tr, pl, pr) = _tri(d_l, d_r)
        err = float(np.linalg.norm(e["P_epi"][0] - p))
        fin = bool(np.isfinite([tl[0], tr[0], pl[0], pr[0]]).all())
        return fin and bool(e["valid_epi"][0]) and err <= SP.SYN_NEAR_POLE_M, {
            "theta_L_rad": float(tl[0]), "delta_theta": float(tr[0] - tl[0]), "error_m": err}
    cases.append(("point near +X (not singular): finite theta / phi / reconstruction", near_pole))

    def pole():
        d = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
        th, ph, sg = G.theta_phi(d)
        e = G.triangulate_epipolar(th[[0]], th[[1]], ph[[0]], ph[[1]], B0)
        e2 = G.triangulate_epipolar(th[[0]], th[[0]], ph[[0]], ph[[0]], B0)
        ok = bool(sg.all() and np.isnan(ph).all() and not e["valid_epi"].any() and not e2["valid_epi"].any()
                  and np.isnan(e["P_epi"]).all())
        return ok, {"singular": sg.tolist(), "phi": [str(x) for x in ph], "theta": th.tolist()}
    cases.append(("exact +X / -X ray: the pole singularity is flagged, phi undefined, no reconstruction", pole))

    def seam():
        tl, tr = 1.0, 1.001
        pl, pr = math.pi - 1e-6, -math.pi + 1e-6
        th, ph, _ = G.theta_phi(_sph(np.array([tl, tr]), np.array([pl, pr])))
        res = float(G.wrap_pi(ph[1] - ph[0]))
        e = G.triangulate_epipolar(th[[0]], th[[1]], ph[[0]], ph[[1]], B0)
        pb = float(e["phi_bar"][0])
        ok = abs(res - 2e-6) <= 1e-12 and abs(float(G.wrap_pi(pb - math.pi))) <= 1e-9
        return ok, {"wrapped_residual": res, "phi_bar": pb}
    cases.append(("phi seam at -pi / +pi: small wrapped residual, circular mean at pi", seam))

    def swapped():
        d_l, d_r = _rays(P_FWD)
        e, (tl, tr, _pl, _pr) = _tri(d_r, d_l)
        dth = float(tr[0] - tl[0])
        mirror = float(np.linalg.norm(e["P_epi"][0] + P_FWD))
        return dth < 0 and mirror <= SP.SYN_EXACT_M, {"delta_theta": dth, "distance_to_minus_P": mirror,
                                                       "error_m": float(np.linalg.norm(e["P_epi"][0] - P_FWD))}
    cases.append(("swapped eyes: delta_theta < 0 and the reconstruction becomes -P", swapped))

    def sign():
        d_l, d_r = _rays(P_FWD)
        e, _ = _tri(d_l, d_r, -B0)
        mirror = float(np.linalg.norm(e["P_epi"][0] + P_FWD))
        err = float(np.linalg.norm(e["P_epi"][0] - P_FWD))
        return mirror <= SP.SYN_EXACT_M and err > SP.SYN_EXACT_M, {"distance_to_minus_P": mirror, "error_m": err}
    cases.append(("baseline sign flipped: the reconstruction becomes -P (detected)", sign))

    def magnitude():
        d_l, d_r = _rays(P_FWD)
        e, _ = _tri(d_l, d_r, 0.064)
        k = 0.064 / B0
        scaled = float(np.linalg.norm(e["P_epi"][0] - k * P_FWD) / np.linalg.norm(P_FWD))
        err = float(np.linalg.norm(e["P_epi"][0] - P_FWD))
        return scaled <= 1e-9 and err > SP.SYN_EXACT_M, {"relative_distance_to_scaled": scaled, "error_m": err}
    cases.append(("baseline magnitude 0.064 m: the reconstruction scales by 0.064 / 0.063 (detected)", magnitude))

    def sensitivity():
        d_l, d_r = _rays(P_FWD)
        e, (tl, tr, pl, pr) = _tri(d_l, d_r)
        eps = 1e-7
        e2 = G.triangulate_epipolar(tl, tr + eps, pl, pr, B0)
        r1 = float(np.linalg.norm(e["P_epi"][0] - O_L))
        r2 = float(np.linalg.norm(e2["P_epi"][0] - O_L))
        want = -B0 * math.sin(float(tl[0])) / math.sin(float(tr[0] - tl[0])) ** 2 * eps
        rel = abs((r2 - r1) - want) / abs(want)
        return rel <= SP.SYN_SENSITIVITY_REL, {"range_change_m": r2 - r1, "expected_m": want, "relative_difference": rel}
    cases.append(("perturbed theta_R: the expected first-order depth sensitivity", sensitivity))

    def ray_ray():
        rng = np.random.default_rng(20261003)
        r = rng.uniform(0.5, 8.0, 200)
        th = np.radians(rng.uniform(5.0, 175.0, 200))
        ph = rng.uniform(-math.pi, math.pi, 200)
        p = r[:, None] * _sph(th, ph)
        d_l, d_r = _rays(p)
        e, (tl, tr, pl, pr) = _tri(d_l, d_r)
        rr = G.triangulate_rays(O_L, d_l, O_R, d_r)
        diff = float(np.nanmax(np.linalg.norm(e["P_epi"] - rr["P_ray"], axis=-1)))
        gap = float(np.nanmax(rr["ray_gap"]))
        nrm = np.stack([np.zeros_like(ph), np.cos(ph), np.sin(ph)], axis=-1)
        d_r2 = FG.unit(d_r + 1e-4 * nrm)
        e2, _ = _tri(d_l, d_r2)
        rr2 = G.triangulate_rays(O_L, d_l, O_R, d_r2)
        ok = (diff <= SP.SYN_EXACT_M and gap <= SP.SYN_EXACT_M and e["valid_epi"].all() and rr["valid_ray"].all()
              and np.isfinite(e2["P_epi"]).all() and np.isfinite(rr2["P_ray"]).all() and (rr2["ray_gap"] > 0).all())
        return bool(ok), {"max_epi_ray_difference_m": diff, "max_gap_m": gap,
                          "perturbed_min_gap_m": float(rr2["ray_gap"].min()),
                          "perturbed_max_epi_ray_difference_m": float(np.max(np.linalg.norm(e2["P_epi"] - rr2["P_ray"], axis=-1)))}
    cases.append(("generic ray-ray triangulation agrees with the epipolar formula", ray_ray))

    def gaze1():
        c = gaze1_calibration()
        rays = G.left_core_rays(c)
        fin = bool(np.isfinite(rays["theta"]).all() and np.isfinite(rays["phi"]).all())
        th = rays["theta"]
        ok = (fin and rays["theta"].size == SP.CORE_SIZE ** 2 and not rays["singular"].any()
              and "cv2" not in sys.modules and "fsg_stereo" not in sys.modules)
        return ok, {"rays": int(th.size), "finite": fin, "singular": int(rays["singular"].sum()),
                    "theta_min_deg": float(np.degrees(th.min())), "theta_max_deg": float(np.degrees(th.max())),
                    "cv2_loaded": "cv2" in sys.modules, "fsg_stereo_loaded": "fsg_stereo" in sys.modules}
    cases.append(("gaze-#1 calibration: all 65,536 raw-core rays finite; no planar rectification", gaze1))

    def schema():
        rows = np.array([0, 5], np.int32)
        cols = np.array([3, 7], np.int32)
        good = {"left_core_row": rows, "left_core_col": cols,
                "uv_L": np.stack([cols + 192, rows + 192], -1).astype(np.float64),
                "uv_R": np.array([[200.25, 192.5], [205.75, 197.0]])}
        G.validate_product(good)
        refused = {}
        for extra in ("xyz_h", "position_w", "instance_id"):
            try:
                G.validate_product({**good, extra: np.zeros((2, 3))})
                refused[extra] = False
            except ValueError:
                refused[extra] = True
        return all(refused.values()), refused
    cases.append(("a correspondence product carrying xyz / Position / instance is rejected", schema))

    def guard():
        c = gaze1_calibration()
        ref, _ = analytic_scene(c, occluder=False)
        with tempfile.TemporaryDirectory(prefix="ab1b-syn-") as td:
            td = Path(td)
            (td / "src").mkdir()
            write_json(td / "src/calibration.json", c)
            np.savez_compressed(td / "src/reference-observation.npz", **ref)
            O.run_oracle(td / "src/calibration.json", td / "src/reference-observation.npz", td / "oracle")
            write_json(td / "oracle/correspondence-freeze.json", {"files": {}})
            orig = G.left_core_rays

            def peeking(cc):
                np.load(td / "src/reference-observation.npz")
                return orig(cc)
            G.left_core_rays = peeking
            try:
                G.run_geometry(td / "src/calibration.json", td / "oracle/oracle-correspondences.npz", td / "geometry")
                raised = None
            except PermissionError as exc:
                raised = str(exc)
            finally:
                G.left_core_rays = orig
            rec = read_json(td / "geometry/geometry-opened-files.json")
        ok = (raised is not None and len(rec["violations"]) == 1 and rec["position_reads"] >= 1
              and rec["violations"][0]["path"].endswith("reference-observation.npz"))
        return ok, {"raised": raised, "violations": len(rec["violations"]), "position_reads": rec["position_reads"]}
    cases.append(("the geometry stage attempting to open Position: the guard refuses it", guard))

    def end_to_end():
        c = gaze1_calibration()
        ref, (n, a, b, planes) = analytic_scene(c)
        with tempfile.TemporaryDirectory(prefix="ab1b-syn-") as td:
            prod, res, rec = _e2e(Path(td), ref, c)
        exp, pt = expected_set(c, ref, n, a, b, planes)
        got = set(zip(prod["left_core_row"].tolist(), prod["left_core_col"].tolist()))
        idx = prod["left_core_row"].astype(int) * SP.CORE_SIZE + prod["left_core_col"].astype(int)
        e = np.linalg.norm(res["P_epi"] - pt[idx], axis=-1)
        uv = prod["uv_R"]
        outside = int(((uv < 192) | (uv > 447)).any(axis=-1).sum())
        ok = (got == exp and outside > 0 and bool(res["valid_epi"].all()) and float(np.median(e)) <= SP.SYN_E2E_MEDIAN_M
              and float(e.max()) <= SP.SYN_E2E_MAX_M and bool((res["delta_theta"] > 0).all())
              and float(np.abs(res["phi_residual"]).max()) <= SP.SYN_E2E_PHI and not rec["violations"]
              and set(Path(p).name for p in rec["data_reads"]) == {"calibration.json", "oracle-correspondences.npz"})
        return ok, {"correspondences": len(got), "expected": len(exp), "equal_sets": got == exp,
                    "outside_right_nominal_core": outside, "median_error_m": float(np.median(e)),
                    "max_error_m": float(e.max()), "max_abs_phi_residual": float(np.abs(res["phi_residual"]).max()),
                    "min_delta_theta": float(res["delta_theta"].min())}
    cases.append(("end-to-end at gaze #1 (analytic planes, float32 Position): exact binocular-visible set, accurate 3-D",
                  end_to_end))

    def same_instance():
        c = gaze1_calibration()
        ref, _ = analytic_scene(c)
        p14, _ = O.compute_oracle(c, ref)
        alt = dict(ref)
        ids_r = ref["instance_R"].copy()
        ids_r[300:341, 300:341] = 9
        alt["instance_R"] = ids_r
        p15, _ = O.compute_oracle(c, alt)
        orig = O.same_instance
        O.same_instance = lambda ids, vi, ui, left: np.ones_like(left, bool)
        try:
            pno, _ = O.compute_oracle(c, alt)
        finally:
            O.same_instance = orig
        key = lambda p: set(zip(p["left_core_row"].tolist(), p["left_core_col"].tolist()))  # noqa: E731
        vi, ui = np.rint(p14["uv_R"][:, 1]).astype(int), np.rint(p14["uv_R"][:, 0]).astype(int)
        inrect = (vi >= 300) & (vi <= 340) & (ui >= 300) & (ui <= 340)
        rect = set(zip(p14["left_core_row"][inrect].tolist(), p14["left_core_col"][inrect].tolist()))
        ok = len(rect) > 0 and key(p15) == key(p14) - rect and rect <= key(pno) and key(p14) <= key(pno)
        return ok, {"case14": len(key(p14)), "occluded_in_right_only": len(rect), "with_rule": len(key(p15)),
                    "rule_omitted": len(key(pno))}
    cases.append(("same-instance rule: a right-only occluder rejects exactly its pairs; omitting the rule accepts them",
                  same_instance))
    return cases


def expected_set(c, ref, n, a, b, planes):
    """The declared rule applied by the test's own projection, with the right id found by casting the nearest right
    pixel's ray against the analytic planes (not by reading the right raster)."""
    w, h = c["image_size_wh"]
    rows, cols = np.mgrid[:SP.CORE_SIZE, :SP.CORE_SIZE]
    rows, cols = rows.ravel(), cols.ravel()
    pos = ref["position_w_L"][rows + 192, cols + 192].astype(np.float64)
    ids = ref["instance_L"][rows + 192, cols + 192].astype(np.int64)
    pt = FG.world_to_head(c, pos)
    eye = c["eyes"][1]
    r_hc, k = np.asarray(eye["R_hc"]), np.asarray(eye["K"])
    xc = (pt - np.asarray(eye["centre_h_m"])) @ r_hc
    uv = (xc @ k.T)[:, :2] / xc[:, 2:3]
    inside = (xc[:, 2] > 1e-9) & (uv[:, 0] >= 0) & (uv[:, 0] <= w - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= h - 1)
    pix = np.stack([np.rint(np.clip(uv[:, 0], 0, w - 1)), np.rint(np.clip(uv[:, 1], 0, h - 1))], -1)
    d = FG.rays_h(eye, pix)
    rid, _ = cast(np.asarray(eye["centre_h_m"], np.float64), d, n, a, b, planes)
    keep = (ids > 0) & inside & (rid == ids)
    return set(zip(rows[keep].tolist(), cols[keep].tolist())), pt


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return x


def synthetic_results() -> list[dict]:
    out = []
    for name, fn in synthetic_cases():
        try:
            ok, detail = fn()
        except Exception as exc:  # a crash is a failed known answer, recorded
            ok, detail = False, {"raised": f"{type(exc).__name__}: {exc}"}
        out.append({"name": name, "ok": bool(ok), "detail": _jsonable(detail)})
    return out


def synthetic(run: Path) -> dict:
    out = run / "synthetic"
    out.mkdir(parents=True, exist_ok=True)
    results = synthetic_results()
    for x in results:
        print(f"{PREFIX} synthetic {'PASS' if x['ok'] else 'FAIL'} {x['name']}")
    rep = {"schema": "AB1b-synthetic-report-v1", "code": code_state(), "cases": results,
           "passed": all(x["ok"] for x in results),
           "tolerances": {k: getattr(SP, k) for k in dir(SP) if k.startswith("SYN_")},
           "note": "analytic rays, analytic gaze-#1 calibration and analytic planes only; no Classroom data, no Blender"}
    write_json(out / "synthetic-report.json", rep)
    print(f"{PREFIX} synthetic {sum(x['ok'] for x in results)}/{len(results)} "
          f"{'AB1B_SYNTHETIC_PASS' if rep['passed'] else 'FAILED'}")
    return rep


# ------------------------------------------------------------------ manifest
TRUTH_CLASSES = {"source/": SP.TRUTH_DERIVED, "oracle/": SP.TRUTH_DERIVED + " (truth-stripped; produced by the ORACLE INPUT stage)",
                 "geometry/": SP.TRUTH_DERIVED, "evaluation/": SP.TRUTH_REFERENCE, "synthetic/": "known answers"}


def write_manifest(run: Path) -> dict:
    files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    m = {"schema": "AB1b-manifest-v1", "experiment": SP.EXPERIMENT, "contract": SP.CONTRACT, "code": code_state(),
         "base_commit": SP.BASE_COMMIT, "ab1a_run": str(SP.AB1A_RUN), "ab1a_pins": SP.AB1A_PINS,
         "truth": TRUTH_CLASSES, "files": {f: sha256(run / f) for f in files}}
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
        if a.cmd == "synthetic":
            ok = synthetic(run)["passed"]
            status = "ok" if ok else "failed"
            return 0 if ok else 1
        if a.cmd in ("source", "oracle", "freeze-correspondence", "geometry", "freeze-geometry", "evaluate"):
            require_committed(a.cmd)
        {"source": source, "oracle": oracle, "freeze-correspondence": freeze_correspondence, "geometry": geometry,
         "freeze-geometry": freeze_geometry, "evaluate": evaluate}.get(a.cmd, lambda r: None)(run)
        if a.cmd == "visualize":
            import ab1b_visuals
            ab1b_visuals.visualize(run, a.visuals.resolve())
            write_manifest(run)
        status = "ok"
        return 0
    finally:
        log_process(run, a.cmd, t0, status)


if __name__ == "__main__":
    raise SystemExit(main())
