"""Active Bootstrap-1c: synthetic known answers (contract section 14).  Analytic data only: no Classroom, no Blender.

Calibrations are built with the accepted ``fsg_geometry.make_calibration``; known points are projected exactly with
``project_h``; analytic planes reuse the accepted AB1b test scene (``ab1b_run.analytic_scene`` / ``expected_set``,
read-only).  Declared tolerances are software / numerical known-answer tolerances, not scientific thresholds.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as BG  # noqa: E402  (accepted, read-only)
import ab1b_run as BR  # noqa: E402  (accepted AB1b analytic test scene, read-only)
import ab1c_planar as PL  # noqa: E402
import ab1c_run as R  # noqa: E402
import ab1c_select as SEL  # noqa: E402
import ab1c_spec as SP  # noqa: E402
import cv2  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import nb1c_attention as NC  # noqa: E402  (accepted reference NMS, read-only)

PIX = (0, 64, 128, 191, 255)          # core rows / cols spanning the nominal 12-degree core (edges, centre, corners)
RANGES = (1.0, 2.5, 6.0)


def calibration(yaw: float, pitch: float) -> dict:
    return SEL.selection_calibration(yaw, pitch)


def known_points(c: dict) -> tuple[dict, np.ndarray]:
    """Exact correspondences of known 3-D points along left core-pixel rays (the product schema), and the points."""
    rows, cols, pts = [], [], []
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    for r in PIX:
        for cc in PIX:
            d = FG.rays_h(c["eyes"][0], np.array([[SP.CORE_ORIGIN + cc, SP.CORE_ORIGIN + r]], np.float64))[0]
            for rng in RANGES:
                rows.append(r)
                cols.append(cc)
                pts.append(o_l + rng * d)
    p = np.asarray(pts)
    uv_r, z = FG.project_h(c["eyes"][1], p)
    assert (z > 0).all()
    rows, cols = np.asarray(rows, np.int32), np.asarray(cols, np.int32)
    prod = {"left_core_row": rows, "left_core_col": cols,
            "uv_L": np.stack([cols + SP.CORE_ORIGIN, rows + SP.CORE_ORIGIN], -1).astype(np.float64),
            "uv_R": uv_r.astype(np.float64)}
    return prod, p


def both(c: dict, prod: dict, variant: dict | None = None) -> tuple[dict, dict]:
    return BG.compute_epipolar(c, prod), PL.triangulate(c, PL.rectify(c), prod, variant)


def err(p, truth) -> float:
    return float(np.nanmax(np.linalg.norm(np.asarray(p) - truth, axis=-1)))


def min_err(p, truth) -> float:
    e = np.linalg.norm(np.asarray(p) - truth, axis=-1)
    return float(np.nanmin(np.where(np.isfinite(e), e, np.inf)))


# ------------------------------------------------------------------ the cases
def exact_case(yaw: float, pitch: float) -> tuple[bool, dict]:
    c = calibration(yaw, pitch)
    prod, p = known_points(c)
    sph, pla = both(c, prod)
    es, ep = err(sph["P_epi"], p), err(pla["P_planar"], p)
    agree = err(pla["P_planar"], sph["P_epi"])
    ok = (bool(sph["valid_epi"].all()) and bool(pla["valid_planar"].all()) and es <= SP.SYN_EXACT_M
          and ep <= SP.SYN_EXACT_M and agree <= SP.SYN_EXACT_M)
    return ok, {"points": int(len(p)), "spherical_max_error_m": es, "planar_max_error_m": ep,
                "planar_vs_spherical_max_m": agree, "max_abs_row_residual_px": float(np.abs(pla["row_residual"]).max())}


def synthetic_cases() -> list[tuple]:
    cases = []

    cases.append(("1 exact forward stereo: planar and spherical reconstruct known points across the 12-degree core",
                  lambda: exact_case(0.0, 0.0)))

    def off_axis():
        det = {}
        ok = True
        for name, (yaw, pitch) in SP.SYN_GAZES.items():
            env = SEL.gaze_envelope(yaw, pitch)
            o, d = exact_case(yaw, pitch)
            det[name] = {"eligible": env["eligible"], "alpha_forward_deg": env["alpha_forward_deg"],
                         "min_core_leverage": env["min_core_leverage"], **d}
            ok &= env["eligible"] and o
        return ok, det
    cases.append(("2 safe-forward off-axis gazes satisfy the envelope and reconstruct exactly", off_axis))

    def identity():
        c = calibration(0.0, 0.0)
        prod, _p = known_points(c)
        sph, pla = both(c, prod)
        same = all(np.array_equal(x[k], prod[k]) for x in (sph, pla) for k in ("left_core_row", "left_core_col"))
        other = {k: v[::-1].copy() for k, v in prod.items()}
        pla_other = PL.triangulate(c, PL.rectify(c), other)
        try:
            R.compare_core(c, sph, pla_other)
            refused = False
        except ValueError:
            refused = True
        return same and refused, {"results_carry_product_identity": same, "different_products_refused": refused}
    cases.append(("3 correspondence identity: both consume the same pairs; different products are refused", identity))

    def eye_order():
        c = calibration(0.0, 0.0)
        prod, p = known_points(c)
        th_l, ph_l, _ = BG.theta_phi(FG.rays_h(c["eyes"][0], prod["uv_L"]))
        th_r, ph_r, _ = BG.theta_phi(FG.rays_h(c["eyes"][1], prod["uv_R"]))
        sw = BG.triangulate_epipolar(th_r, th_l, ph_r, ph_l, SP.IPD_M)
        pla = PL.triangulate(c, PL.rectify(c), prod, {"swap_eyes": True})
        es, ep = min_err(sw["P_epi"], p), min_err(pla["P_planar"], p)
        minus_p = err(sw["P_epi"], -p)
        ok = es > SP.SYN_FAIL_M and ep > SP.SYN_FAIL_M and minus_p <= SP.SYN_EXACT_M
        return ok, {"spherical_min_error_m": es, "planar_min_error_m": ep, "spherical_equals_minus_P_m": minus_p}
    cases.append(("4 wrong eye order: both fail the known answer (spherical gives exactly -P)", eye_order))

    def baseline_sign():
        c = calibration(0.0, 0.0)
        prod, p = known_points(c)
        th_l, ph_l, _ = BG.theta_phi(FG.rays_h(c["eyes"][0], prod["uv_L"]))
        th_r, ph_r, _ = BG.theta_phi(FG.rays_h(c["eyes"][1], prod["uv_R"]))
        sw = BG.triangulate_epipolar(th_l, th_r, ph_l, ph_r, -SP.IPD_M)
        pla = PL.triangulate(c, PL.rectify(c), prod, {"q_sign": -1.0})
        ok = (err(sw["P_epi"], -p) <= SP.SYN_EXACT_M and min_err(sw["P_epi"], p) > SP.SYN_FAIL_M
              and bool((pla["z_rect"] < 0).all()) and min_err(pla["P_planar"], p) > SP.SYN_FAIL_M)
        return ok, {"spherical_equals_minus_P_m": err(sw["P_epi"], -p), "planar_z_rect_max": float(np.max(pla["z_rect"])),
                    "planar_min_error_m": min_err(pla["P_planar"], p)}
    cases.append(("5 wrong baseline sign: spherical gives -P, planar a point behind the camera", baseline_sign))

    def ipd():
        c = calibration(0.0, 0.0)
        prod, p = known_points(c)
        s = 0.064 / SP.IPD_M
        th_l, ph_l, _ = BG.theta_phi(FG.rays_h(c["eyes"][0], prod["uv_L"]))
        th_r, ph_r, _ = BG.theta_phi(FG.rays_h(c["eyes"][1], prod["uv_R"]))
        sw = BG.triangulate_epipolar(th_l, th_r, ph_l, ph_r, 0.064)["P_epi"]
        pla = PL.triangulate(c, PL.rectify(c), prod, {"baseline_scale": s})["P_planar"]
        o_l = np.asarray(c["eyes"][0]["centre_h_m"])
        sph_law, pla_law = err(sw, s * p), err(pla, o_l + s * (p - o_l))
        gap = err(pla - sw, np.broadcast_to(-(s - 1) * o_l, p.shape))
        ok = (sph_law <= SP.SYN_EXACT_M and pla_law <= SP.SYN_EXACT_M and min_err(sw, p) > SP.SYN_FAIL_M
              and min_err(pla, p) > SP.SYN_FAIL_M and gap <= SP.SYN_EXACT_M)
        return ok, {"spherical_scale_law_m": sph_law, "planar_scale_law_m": pla_law,
                    "planar_minus_spherical_expected_x_m": float(-(s - 1) * o_l[0]), "gap_law_m": gap,
                    "spherical_min_error_m": min_err(sw, p), "planar_min_error_m": min_err(pla, p)}
    cases.append(("6 changed IPD: known wrong scales (spherical about the origin, planar about the left eye)", ipd))

    def phi_sign():
        c = calibration(0.0, 0.0)
        prod, p = known_points(c)
        out = {}
        for side, uv, i in (("L", prod["uv_L"], 0), ("R", prod["uv_R"], 1)):
            d = FG.rays_h(c["eyes"][i], uv)
            out[side] = (np.arctan2(np.hypot(d[:, 1], d[:, 2]), d[:, 0]), np.arctan2(-d[:, 1], -d[:, 2]))
        bad = BG.triangulate_epipolar(out["L"][0], out["R"][0], out["L"][1], out["R"][1], SP.IPD_M)["P_epi"]
        m = np.abs(p[:, 1]) > 0.05
        e = np.linalg.norm(bad - p, axis=-1)[m]
        return bool(m.any() and e.min() > SP.SYN_FAIL_M), {"points_with_y": int(m.sum()), "min_error_m": float(e.min())}
    cases.append(("7 spherical phi sign error: points with y != 0 fail", phi_sign))

    def convention():
        c = calibration(0.0, 0.0)
        prod, p = known_points(c)
        rect = PL.rectify(c)
        a = PL.triangulate(c, rect, prod, {"r1_transposed": True})
        w, h = c["image_size_wh"]
        kl, kr = (np.asarray(e["K"], float) for e in c["eyes"])
        r, t = FG.relative_pose(c)
        q0 = cv2.stereoRectify(kl, np.zeros(5), kr, np.zeros(5), (w, h), r, t, flags=0, alpha=-1,
                               newImageSize=(w, h))[4]
        b = PL.triangulate(c, rect, prod, {"q": q0})
        ea, eb = min_err(a["P_planar"], p), min_err(b["P_planar"], p)
        return ea > SP.SYN_FAIL_M and eb > SP.SYN_FAIL_M, {"r1_transposed_min_error_m": ea,
                                                          "no_zero_disparity_q_min_error_m": eb,
                                                          "q0_3_3": float(q0[3, 3])}
    cases.append(("8 planar rectification convention change (R1 transposed; non-zero-disparity Q) fails", convention))

    def schema():
        c = calibration(0.0, 0.0)
        prod, _ = known_points(c)
        res = {}
        for key in ("xyz_h", "position_w", "instance_id", "depth_m"):
            bad = dict(prod, **{key: np.zeros(len(prod["uv_L"]))})
            for name, fn in (("spherical", lambda pr: BG.compute_epipolar(c, pr)),
                             ("planar", lambda pr: PL.triangulate(c, PL.rectify(c), pr))):
                try:
                    fn(bad)
                    res[f"{name}:{key}"] = "accepted"
                except ValueError:
                    res[f"{name}:{key}"] = "rejected"
        return all(v == "rejected" for v in res.values()), res
    cases.append(("9 a truth-bearing correspondence field is rejected by both geometries", schema))

    def guard():
        c = calibration(0.0, 0.0)
        prod, _ = known_points(c)
        out = {}
        with tempfile.TemporaryDirectory(prefix="ab1c-syn-") as td:
            td = Path(td)
            (td / "src").mkdir()
            R.write_json(td / "src/calibration.json", c)
            np.savez_compressed(td / "src/oracle-correspondences.npz", **prod)
            np.savez_compressed(td / "src/reference-observation.npz", position_w_L=np.zeros((2, 2, 3)))
            (td / "src/correspondence-freeze.json").write_text("{}")
            for name in ("spherical", "planar"):
                mod, fn_name = (BG, "left_core_rays") if name == "spherical" else (PL, "support_diagnostic")
                orig = getattr(mod, fn_name)

                def peeking(*a, _orig=orig):
                    np.load(td / "src/reference-observation.npz")
                    return _orig(*a)
                setattr(mod, fn_name, peeking)
                try:
                    if name == "spherical":
                        R.run_spherical_gaze(td / "src/calibration.json", td / "src/oracle-correspondences.npz",
                                             td / name, td / "src/correspondence-freeze.json")
                    else:
                        PL.run_planar(td / "src/calibration.json", td / "src/oracle-correspondences.npz", td / name,
                                      td / "src/correspondence-freeze.json")
                    raised = None
                except PermissionError as exc:
                    raised = str(exc)
                finally:
                    setattr(mod, fn_name, orig)
                rec = R.read_json(td / name / f"{name}-opened-files.json")
                out[name] = {"raised": raised is not None, "violations": len(rec["violations"]),
                             "position_reads": rec["position_reads"]}
        ok = all(v["raised"] and v["violations"] == 1 and v["position_reads"] >= 1 for v in out.values())
        return ok, out
    cases.append(("10 a geometry stage opening Position before the freeze is refused (spherical and planar)", guard))

    def selector():
        want = {(0.0, 0.0): (True, True), (0.0, 19.75): (True, True), (0.0, 20.25): (False, True),
                (0.0, 25.0): (False, True), (19.75, 0.0): (True, False), (15.0, 0.0): (True, True)}
        det, ok = {}, True
        for (yaw, pitch), (cone, lev) in want.items():
            env = SEL.gaze_envelope(yaw, pitch)
            direct_alpha = math.degrees(math.acos(math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))))
            c = calibration(yaw, pitch)
            k_inv = np.linalg.inv(np.asarray(c["eyes"][0]["K"], float))
            uv = SEL.core_uv()
            a = np.concatenate([uv, np.ones((len(uv), 1))], -1) @ k_inv.T
            a /= np.linalg.norm(a, axis=-1, keepdims=True)
            direct_lev = min(float(np.sqrt(1 - (a @ np.asarray(e["R_hc"], float)[0]) ** 2).min()) for e in c["eyes"])
            good = (env["in_cone"] == cone and env["leverage_ok"] == lev and env["eligible"] == (cone and lev)
                    and abs(env["alpha_forward_deg"] - direct_alpha) <= 1e-9
                    and abs(env["min_core_leverage"] - direct_lev) <= 1e-12)
            det[f"{yaw:+.2f},{pitch:+.2f}"] = {"in_cone": env["in_cone"], "leverage_ok": env["leverage_ok"],
                                              "alpha_forward_deg": env["alpha_forward_deg"],
                                              "min_core_leverage": env["min_core_leverage"], "ok": good}
            ok &= good
        return ok, det
    cases.append(("11 safe-forward selector: known directions inside / outside the cone and the leverage bound", selector))

    def nms():
        rng = np.random.default_rng(7)
        dirs, _y, _p = SEL.grid()
        det, ok = {}, True
        for k in (3, 6):
            a = rng.normal(size=(SP.HEIGHT, SP.WIDTH))
            p1, r1 = SEL.select_gazes(a, dirs, np.ones(a.shape, bool), k)
            p2, r2 = NC.select_gazes(a, dirs, k)
            det[f"equals_nb1c_K{k}"] = p1 == p2 and r1 == r2
        a = rng.normal(size=(SP.HEIGHT, SP.WIDTH))
        elig = np.zeros(a.shape, bool)
        elig[150:210, 330:390] = True
        a[0, 0] = 99.0                                             # ineligible maximum
        p, _ = SEL.select_gazes(a, dirs, elig, 3)
        det["ineligible_max_never_chosen"] = 0 not in p and all(elig.ravel()[i] for i in p)
        t = np.zeros((SP.HEIGHT, SP.WIDTH))
        t[200, 400] = t[180, 380] = 5.0                            # exact tie: smaller row wins
        t[181, 300] = 5.0 - 1e-13 * 5.0                            # inside the tie window, larger row
        t[179, 500] = 5.0 - 1e-9                                   # outside the tie window, smaller row
        p, rd = SEL.select_gazes(t, dirs, np.ones(t.shape, bool), 1)
        det["tie_smaller_row_then_col"] = p[0] == 180 * SP.WIDTH + 380   # not 179/500: outside the tie window
        det["tie_set_size"] = rd[0]["tie_set_size"]
        det["tie_window"] = rd[0]["tie_set_size"] == 3
        dd = SP.D_MIN_RAD
        bd = np.array([[0, 0, -1.0], [math.sin(dd), 0, -math.cos(dd)], [math.sin(dd - 1e-9), 0, -math.cos(dd - 1e-9)],
                       [-math.sin(1.0), 0, -math.cos(1.0)]])
        p, rd = SEL.select_gazes(np.array([4.0, 3.0, 3.5, 1.0]), bd, np.ones(4, bool), 3)
        det["dmin_boundary"] = p == [0, 1, 3]
        try:
            SEL.select_gazes(np.array([1.0, 2.0]), bd[:2] * 0 + np.array([0, 0, -1.0]), np.ones(2, bool), 3)
            det["budget_error"] = False
        except SEL.BudgetError:
            det["budget_error"] = True
        ok = all(v for k, v in det.items() if k != "tie_set_size")
        return ok, det
    cases.append(("12 NMS: equals the accepted NB1c rule; eligibility; ties; the exact D_MIN boundary; budget", nms))

    def common_set():
        c = calibration(0.0, 0.0)
        prod, _ = known_points(c)
        sph, pla = both(c, prod)
        base, _ = R.compare_core(c, sph, pla)
        pl2 = {k: v.copy() for k, v in pla.items()}
        pl2["valid_planar"][0] = False
        pl2["P_planar"][0] = [9e9, 9e9, 9e9]
        s2, a2 = R.compare_core(c, sph, pl2)
        sp2 = {k: v.copy() for k, v in sph.items()}
        sp2["valid_epi"][1] = False
        s3, _ = R.compare_core(c, sp2, pla)
        n = len(prod["uv_L"])
        bad = {k: v[1:] for k, v in pla.items()}
        try:
            R.compare_core(c, sph, bad)
            refused = False
        except (ValueError, IndexError):
            refused = True
        ok = (base["counts"]["common_valid"] == n and s2["counts"]["common_valid"] == n - 1
              and s2["counts"]["spherical_only"] == 1 and s3["counts"]["common_valid"] == n - 1
              and s3["counts"]["planar_only"] == 1 and s2["planar_minus_spherical_m"]["max"] < 1e-6
              and s2["planar_minus_spherical_m"]["count"] == n - 1 and not bool(a2["common"][0]) and refused)
        return ok, {"n": n, "after_planar_invalid": s2["counts"], "after_spherical_invalid": s3["counts"],
                    "unequal_identity_refused": refused}
    cases.append(("13 common-valid-set accounting", common_set))

    def support():
        g1 = calibration(76.75, 7.75)
        s1 = PL.support_diagnostic(g1, PL.rectify(g1))["eyes"]["L"]
        f = calibration(0.0, 0.0)
        s0 = PL.support_diagnostic(f, PL.rectify(f))["eyes"]["L"]
        ok = (s1["rectified_core_pixels_from_nominal_raw_core"] == 0
              and abs(s1["rectified_core_centre_from_gaze_deg"] - 14.2628609282284) <= 1e-9
              and abs(s1["rectified_core_centre_from_baseline_deg"] - 1.0521371560080657) <= 1e-9
              and not s1["support_two_dimensional"] and s0["support_finite"] and s0["support_two_dimensional"])
        return ok, {"gaze1": {k: s1[k] for k in ("rectified_core_pixels_from_nominal_raw_core",
                                                 "rectified_core_centre_from_gaze_deg",
                                                 "rectified_core_centre_from_baseline_deg", "raw_source_span_px",
                                                 "support_two_dimensional")},
                    "forward": {k: s0[k] for k in ("rectified_core_pixels_from_nominal_raw_core",
                                                   "rectified_core_centre_from_gaze_deg", "raw_source_span_px",
                                                   "support_finite", "support_two_dimensional")}}
    cases.append(("14 planar support diagnostic: reproduces the accepted AB1a gaze-#1 values; forward is finite 2-D",
                  support))

    def end_to_end():
        c = calibration(*SP.SYN_GAZES["right"])
        ref, (n, a, b, planes) = BR.analytic_scene(c)
        with tempfile.TemporaryDirectory(prefix="ab1c-syn-") as td:
            td = Path(td)
            (td / "src").mkdir()
            R.write_json(td / "src/calibration.json", c)
            np.savez_compressed(td / "src/reference-observation.npz", **ref)
            R.run_oracle_gaze(td / "src/calibration.json", td / "src/reference-observation.npz", td / "oracle")
            fz = td / "oracle/correspondence-freeze.json"
            fz.write_text("{}")
            prod_p = td / "oracle/oracle-correspondences.npz"
            R.run_spherical_gaze(td / "src/calibration.json", prod_p, td / "spherical", fz)
            PL.run_planar(td / "src/calibration.json", prod_p, td / "planar", fz)
            prod = R.load_npz(prod_p)
            sph = R.load_npz(td / "spherical/epipolar-result.npz")
            pla = R.load_npz(td / "planar/planar-result.npz")
            recs = [R.read_json(td / f"{s}/{s}-opened-files.json") for s in ("spherical", "planar")]
        exp, pt = BR.expected_set(c, ref, n, a, b, planes)
        got = set(zip(prod["left_core_row"].tolist(), prod["left_core_col"].tolist()))
        idx = prod["left_core_row"].astype(int) * SP.CORE_SIZE + prod["left_core_col"].astype(int)
        es = np.linalg.norm(sph["P_epi"] - pt[idx], axis=-1)
        ep = np.linalg.norm(pla["P_planar"] - pt[idx], axis=-1)
        cmp_s, _ = R.compare_core(c, sph, pla)
        # exact-data control on the same pairs: the left pixel-centre rays cast against the analytic planes in float64
        # and projected exactly (no float32 Position skew)
        o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
        _pid, p_exact = BR.cast(o_l, FG.rays_h(c["eyes"][0], prod["uv_L"]), n, a, b, planes)
        exact = dict(prod, uv_R=FG.project_h(c["eyes"][1], p_exact)[0].astype(np.float64))
        sx, px = both(c, exact)
        cmp_x, _ = R.compare_core(c, sx, px)
        outside = int(((prod["uv_R"] < 192) | (prod["uv_R"] > 447)).any(axis=-1).sum())
        ok = (got == exp and bool(sph["valid_epi"].all()) and bool(pla["valid_planar"].all())
              and float(np.median(es)) <= SP.SYN_E2E_MEDIAN_M and float(es.max()) <= SP.SYN_E2E_MAX_M
              and float(np.median(ep)) <= SP.SYN_E2E_MEDIAN_M and float(ep.max()) <= SP.SYN_E2E_MAX_M
              and cmp_s["planar_minus_spherical_m"]["max"] <= SP.SYN_FLOAT32_AGREE_M
              and cmp_x["planar_minus_spherical_m"]["max"] <= SP.SYN_EXACT_M
              and all(not r["violations"] for r in recs)
              and all({Path(x).name for x in r["data_reads"]} == {"calibration.json", "oracle-correspondences.npz"}
                      for r in recs))
        return ok, {"correspondences": len(got), "expected": len(exp), "equal_sets": got == exp,
                    "outside_right_nominal_core": outside, "spherical_median_m": float(np.median(es)),
                    "spherical_max_m": float(es.max()), "planar_median_m": float(np.median(ep)),
                    "planar_max_m": float(ep.max()),
                    "planar_vs_spherical_max_m_float32_position": cmp_s["planar_minus_spherical_m"]["max"],
                    "planar_vs_spherical_max_m_exact_control": cmp_x["planar_minus_spherical_m"]["max"],
                    "abs_phi_residual_max_rad": float(np.abs(sph["phi_residual"]).max()),
                    "abs_row_residual_max_px": float(np.abs(pla["row_residual"]).max())}
    cases.append(("15 end-to-end analytic planes at a safe-forward gaze: exact set, accurate, planar = spherical "
                  "(float32 Position 1e-6 m; exact control 1e-8 m)", end_to_end))
    return cases


def synthetic_results() -> list[dict]:
    out = []
    for name, fn in synthetic_cases():
        try:
            ok, detail = fn()
        except Exception as exc:  # a crash is a failed known answer, recorded
            ok, detail = False, {"raised": f"{type(exc).__name__}: {exc}"}
        out.append({"name": name, "ok": bool(ok), "detail": clean(json.loads(json.dumps(detail, default=_jsonable)))})
    return out


def clean(x):
    """Non-finite floats as strings, so the report is strict JSON."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return x


def _jsonable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    return str(x)
