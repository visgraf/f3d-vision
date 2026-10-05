"""Active Bootstrap-1d2: preflight known answers for what is NEW in AB1d2 (before the canonical render).

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md, section 21.  The matcher is accepted and
frozen and is not re-tested here.  These cases exercise the render-setting comparison, the EXR-header comparison, the
calibration identity, the search-geometry identity, the source / constant / benchmark verification and the paired
statistics, on the accepted AB1c 256-spp records (header metadata only for EXR), the accepted AB1d record and synthetic
arrays.  No Classroom render and no 4096-spp Classroom image is used.  Each wrong input must fail; each unmodified or
null input must pass.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import types

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1d2_run as R  # noqa: E402
import ab1d2_spec as SP  # noqa: E402


def expected_record(old: dict, spp: int = SP.SPP) -> dict:
    """The AB1c record with exactly the declared expected differences and labels of a 4096-spp re-observation."""
    new = copy.deepcopy(old)
    new["spp"] = spp
    new["settings"]["samples"] = spp
    new["primary_camera_samples"] = R.primary_samples(spp)
    new["render_seconds_lr"] = {s: v * 16 for s, v in old["render_seconds_lr"].items()}
    new["rgb_observation_sha256"] = hashlib.sha256(b"synthetic 4096-spp observation").hexdigest()
    new["created_utc"] = "2026-10-05T12:00:00+00:00"
    new["experiment"] = SP.EXPERIMENT
    new["action_source"] = "synthetic expected record"
    new["blend"] = str(REPO / SP.BLEND)
    new["observation_quality_control"] = {"accepted_spp": SP.ACCEPTED_SPP, "spp": spp}
    return new


def expected_header(old: dict, spp: int = SP.SPP) -> dict:
    new = copy.deepcopy(old)
    new[SP.EXR_SAMPLES] = str(spp)
    for k in list(SP.EXR_TIMING) + [f"cycles.{SP.EXR_LAYER}.{t}" for t in SP.EXR_LAYER_TIMING]:
        if k in new:
            new[k] = "changed"
    new["File"] = str(REPO / SP.BLEND)
    return new


def record_mutations(old: dict) -> list[tuple[str, str, object]]:
    """(name, the field that must fail, mutator) for the setting comparison."""
    def spp_all(v):
        def f(r):
            r["spp"], r["settings"]["samples"], r["primary_camera_samples"] = v, v, R.primary_samples(v)
        return f

    def setting(k, v):
        def f(r):
            r["settings"][k] = v
        return f

    def cam(k, v):
        def f(r):
            r["settings"]["camera"][k] = v
        return f

    def passes(k, v):
        def f(r):
            r["settings"]["passes"][k] = v
        return f

    def field(k, v):
        def f(r):
            r[k] = v
        return f

    def matrix(r):
        r["camera_matrix_world_lr"]["L"][0][3] += 1e-3

    def exr_denoise(r):
        r["exr_channels_lr"]["L"] = r["exr_channels_lr"]["L"] + ["interior.Denoising Albedo.R"]

    def head_motion(r):
        r["eye_pose"]["head_origin_w_m"][0] += 0.01

    return [("spp 256", "spp", spp_all(256)), ("spp 2048", "spp", spp_all(2048)), ("spp 8192", "spp", spp_all(8192)),
            ("readback samples differ from spp", "settings", setting("samples", 2048)),
            ("denoising enabled", "settings", setting("denoising", True)),
            ("adaptive sampling enabled", "settings", setting("adaptive_sampling", True)),
            ("L seed changed", "render_seeds_lr", field("render_seeds_lr", {"L": 2113, "R": 2112})),
            ("R seed changed", "render_seeds_lr", field("render_seeds_lr", {"L": 2111, "R": 2113})),
            ("same seed both eyes", "render_seeds_lr", field("render_seeds_lr", {"L": 2111, "R": 2111})),
            ("pixel filter type changed", "settings", setting("pixel_filter", "GAUSSIAN")),
            ("filter width changed", "settings", setting("filter_width", 1.5)),
            ("resolution changed", "settings", setting("resolution_wh", [1280, 1280])),
            ("resolution percentage changed", "settings", setting("resolution_percentage", 50)),
            ("motion blur enabled", "settings", setting("motion_blur", True)),
            ("lens changed", "settings", cam("lens_mm", 50.0)),
            ("Z pass enabled", "settings", passes("z", True)),
            ("camera matrix changed", "camera_matrix_world_lr", matrix),
            ("gaze changed", "gaze_yaw_pitch_deg", field("gaze_yaw_pitch_deg", [-18.0, -5.75])),
            ("calibration changed", "calibration_sha256", field("calibration_sha256", "0" * 64)),
            ("device changed", "device", field("device", "CUDA")),
            ("Blender version changed", "blender", field("blender", "4.2.0")),
            ("denoising pass in EXR", "exr_channels_lr", exr_denoise),
            ("head moved", "eye_pose", head_motion),
            ("unknown extra field", "denoiser", field("denoiser", "OIDN")),
            ("RGB unchanged (same hash)", "rgb_observation_sha256", field("rgb_observation_sha256", old["rgb_observation_sha256"])),
            ("different blend file", "blend", field("blend", "/nonexistent/other.blend"))]


def header_mutations() -> list[tuple[str, str, object]]:
    def set_(k, v):
        def f(h):
            h[k] = v
        return f

    def drop(k):
        def f(h):
            h.pop(k, None)
        return f

    def denoise(h):
        h["channels"] = h["channels"] + [["interior.Denoising Albedo.R", 2, 1, 1]]

    return [("EXR samples 256", SP.EXR_SAMPLES, set_(SP.EXR_SAMPLES, "256")),
            ("EXR samples 2048", SP.EXR_SAMPLES, set_(SP.EXR_SAMPLES, "2048")),
            ("EXR scene changed", "Scene", set_("Scene", "Scene")),
            ("EXR camera changed", "Camera", set_("Camera", "CLASSROOM_ORACLE1.003")),
            ("EXR denoising channel", "channels", denoise),
            ("EXR samples attribute missing", SP.EXR_SAMPLES, drop(SP.EXR_SAMPLES)),
            ("EXR unknown attribute", "cycles.interior.denoiser", set_("cycles.interior.denoiser", "OIDN")),
            ("EXR different blend file", "File", set_("File", "/nonexistent/other.blend"))]


def synthetic_eval(n: int, seed: int) -> tuple[dict, dict]:
    rng = np.random.default_rng(seed)
    idx = np.arange(0, 2 * n, 2, dtype=np.int32)
    e = {"core_index": idx, "e_px": rng.normal(0, 20, n), "zncc_oracle": rng.uniform(-0.5, 1.0, n),
         "oracle_rank": rng.integers(1, 10, n).astype(np.int8), "s_oracle_on_curve": rng.uniform(5, 200, n),
         "error_3d_vs_perfect_m": rng.uniform(0, 5, n), "oracle_patch_std": rng.uniform(0, 10, n)}
    m = 2 * n
    rec = {"peak_s": np.full((m, 8), np.nan), "peak_zncc": np.full((m, 8), np.nan), "peak_margin": rng.uniform(0, 0.2, m),
           "best_zncc": rng.uniform(0.3, 1.0, m), "left_patch_std_u8": rng.uniform(0.5, 12, m)}
    rec["peak_s"][:, :3] = rng.uniform(5, 200, (m, 3))
    rec["peak_zncc"][:, :3] = rng.uniform(0, 1, (m, 3))
    return e, rec


def run_tests(workdir: Path) -> dict:
    t0 = time.time()
    cases: list[dict] = []

    def case(name: str, passed, **detail) -> None:
        cases.append({"case": len(cases) + 1, "name": name, "passed": bool(passed), "detail": R.jsonable(detail)})

    # 1. the driver selects exactly spp = 4096 (declared constant; the canonical call passes it)
    tree = ast.parse((HERE / "ab1d2_render.py").read_text())
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    def calls(fn, name):
        return [c for c in ast.walk(fns[fn]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == name]
    acq = calls("canonical", "acquire_pair")
    cfg = calls("preflight", "configure")
    is_spp = (lambda a: isinstance(a, ast.Attribute) and a.attr == "SPP" and isinstance(a.value, ast.Name)
              and a.value.id == "SP")
    literals = sorted({c.value for c in ast.walk(tree) if isinstance(c, ast.Constant) and c.value in (256, 2048, 4096, 8192)
                       and not isinstance(c.value, bool)})
    case("driver selects exactly spp = 4096", SP.SPP == 4096 and SP.ACCEPTED_SPP == 256 and len(acq) == 1
         and is_spp(acq[0].args[3]) and len(cfg) == 1 and is_spp(cfg[0].args[1]) and not literals,
         canonical_acquire_calls=len(acq), preflight_configure_calls=len(cfg), spp_literals=literals)

    # 2. the unmodified expected record passes; 3-10. every wrong setting fails, naming the field
    for g in SP.GAZES:
        old = R.read_json(SP.a1c_acq(g, "acquisition.json"))
        res = R.compare_acquisition(old, expected_record(old), SP.ACCEPTED_SPP, SP.SPP)
        case(f"expected 4096 record passes ({g})", res["ok"], failed=res["failed"])
    old = R.read_json(SP.a1c_acq("gaze-1", "acquisition.json"))
    for name, want, mut in record_mutations(old):
        new = expected_record(old)
        mut(new)
        res = R.compare_acquisition(old, new, SP.ACCEPTED_SPP, SP.SPP)
        case(f"record: {name} fails", not res["ok"] and want in res["failed"], failed=res["failed"])
    res = R.compare_acquisition(old, copy.deepcopy(old), SP.ACCEPTED_SPP, SP.SPP)
    case("record: the accepted 256-spp record itself fails as a 4096 observation", not res["ok"] and "spp" in res["failed"],
         failed=res["failed"])

    # EXR header (accepted AB1c headers; metadata only)
    for s in ("L", "R"):
        hdr = R.exr_header(SP.a1c(f"observations/gaze-1/evaluation_only/raw_{s}.exr"))
        res = R.compare_exr(hdr, expected_header(hdr), SP.ACCEPTED_SPP, SP.SPP)
        case(f"expected 4096 EXR header passes ({s})", res["ok"], failed=res["failed"])
    hdr = R.exr_header(SP.a1c("observations/gaze-1/evaluation_only/raw_L.exr"))
    case("accepted EXR header records 256 samples", hdr.get(SP.EXR_SAMPLES) == str(SP.ACCEPTED_SPP),
         samples=hdr.get(SP.EXR_SAMPLES))
    for name, want, mut in header_mutations():
        new = expected_header(hdr)
        mut(new)
        res = R.compare_exr(hdr, new, SP.ACCEPTED_SPP, SP.SPP)
        case(f"header: {name} fails", not res["ok"] and want in res["failed"], failed=res["failed"])

    # calibration identity (byte-exact re-serialization; a changed calibration is detected)
    for g in SP.GAZES:
        b = SP.a1c_acq(g, "calibration.json").read_bytes()
        c = json.loads(b)
        reser = (json.dumps(c, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
        c2 = copy.deepcopy(c)
        c2["eyes"][0]["K"][0][0] += 1e-9
        bad = (json.dumps(c2, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
        case(f"calibration re-serializes byte-identically; a changed one is detected ({g})",
             reser == b and hashlib.sha256(reser).hexdigest() == SP.A1C_CALIBRATION[g]
             and hashlib.sha256(bad).hexdigest() != SP.A1C_CALIBRATION[g])

    # search-geometry identity (section 10)
    rec = R.load_npz(SP.a1d("match/gaze-1/matcher-record.npz"))
    res = R.geometry_identity(rec, {k: v.copy() for k, v in rec.items()})
    case("search geometry: accepted record vs itself passes", res["ok"])
    case("search geometry fields exist in the accepted record", set(SP.GEOMETRY_FIELDS) <= set(rec))

    def geo_mut(name, key, fn):
        r2 = {k: v.copy() for k, v in rec.items()}
        fn(r2[key])
        res = R.geometry_identity(rec, r2)
        case(f"search geometry: {name} fails", not res["ok"] and not res["fields"][key]["identical"],
             rows=res["fields"][key]["rows_differing"])
    geo_mut("q_inf + 1e-12", "q_inf", lambda a: a.__setitem__((100, 0), a[100, 0] + 1e-12))
    geo_mut("k_last + 1 (shortened / extended search)", "k_last", lambda a: a.__setitem__(200, a[200] + 1))
    geo_mut("candidate_count + 1", "candidate_count", lambda a: a.__setitem__(300, a[300] + 1))
    geo_mut("theta_L one ulp", "theta_L", lambda a: a.__setitem__(400, np.nextafter(a[400], 4.0)))
    geo_mut("baseline sign (line_l negated)", "line_l", lambda a: a.__setitem__(slice(None), -a))
    geo_mut("line direction reversed", "line_dir", lambda a: a.__setitem__(slice(None), -a))

    # source / constants / benchmark verification on mirrors
    tmp = Path(tempfile.mkdtemp(prefix="ab1d2-preflight-", dir=workdir if workdir.is_dir() else None))
    try:
        for p in SP.SOURCE_PINS:
            (tmp / "src" / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / p, tmp / "src" / p)
        clean = R.verify_pins(tmp / "src", SP.SOURCE_PINS)
        with open(tmp / "src/tools/active_bootstrap/ab1d_match.py", "a") as f:
            f.write("\n# altered\n")
        dirty = R.verify_pins(tmp / "src", SP.SOURCE_PINS)
        case("matcher source: unmodified mirror passes; an altered ab1d_match.py fails",
             not clean and list(dirty) == ["tools/active_bootstrap/ab1d_match.py"], changed=list(dirty))
        import ab1d_match as M
        import ab1d_spec as DS
        live = R.matcher_identity()
        case("matcher constants: the live accepted matcher is identical", live["ok"], identity=live)
        spec_names = list(SP.MATCHER_CONSTANTS)
        for k, v in (("MIN_LOCAL_STD_U8", 1.0), ("PATCH", 7), ("SPACING_PX", 0.5), ("TOP_K", 4),
                     ("REFINE_BOUND_SAMPLES", 1.0)):
            fake = types.SimpleNamespace(**{n: getattr(DS, n) for n in spec_names})
            setattr(fake, k, v)
            res = R.matcher_identity(fake, M.FROZEN)
            case(f"matcher constants: {k} = {v} fails", not res["ok"] and not res["spec"][k])
        for k, v in (("min_std", 1.0), ("patch_half", 3), ("separation", 1.0), ("bound", 2.0)):
            fp = types.SimpleNamespace(**{f: getattr(M.FROZEN, f) for f in ("patch_half", "spacing", "min_std",
                                                                            "tie_eps", "top_k", "separation", "bound",
                                                                            "luma")})
            setattr(fp, k, v)
            res = R.matcher_identity(DS, fp)
            case(f"matcher parameters: FROZEN.{k} = {v} fails", not res["ok"])
        bench = {k: h for k, h in DS.BENCH_PINS.items() if k.startswith(("oracle/gaze-1/", "spherical/gaze-1/"))}
        for p in bench:
            (tmp / "a1c" / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SP.a1c(p), tmp / "a1c" / p)
        clean = R.verify_pins(tmp / "a1c", bench)
        tgt = tmp / "a1c" / "oracle/gaze-1/oracle-correspondences.npz"
        b = bytearray(tgt.read_bytes())
        b[len(b) // 2] ^= 0x01
        tgt.write_bytes(bytes(b))
        dirty = R.verify_pins(tmp / "a1c", bench)
        case("benchmark: unmodified mirror passes; an altered oracle file fails",
             not clean and list(dirty) == ["oracle/gaze-1/oracle-correspondences.npz"], changed=list(dirty))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # paired statistics known answers (synthetic)
    e, r = synthetic_eval(4000, 20261005)
    s, a = R.paired_core(e, e, r, r)
    t = s["transitions_1px"]
    case("paired: a record paired with itself gives delta E = 0, all equal, diagonal transitions",
         np.all(a["delta_E"] == 0) and s["error"]["fraction_equal"] == 1.0 and t["bad_to_good"]["count"] == 0
         and t["good_to_bad"]["count"] == 0 and s["zncc"]["fraction_equal"] == 1.0
         and all(s["ranks"][f"top{k}"]["not_to_in"]["count"] == 0 and s["ranks"][f"top{k}"]["in_to_not"]["count"] == 0
                 for k in (1, 3, 8)))
    e2 = {k: v.copy() for k, v in e.items()}
    e2["e_px"] = e["e_px"] / 4.0
    s, a = R.paired_core(e, e2, r, r)
    E0 = np.abs(e["e_px"])
    want = {"bad_to_good": int(((E0 > 1) & (E0 / 4 <= 1)).sum()), "good_to_good": int((E0 <= 1).sum()),
            "good_to_bad": 0, "bad_to_bad": int((E0 / 4 > 1).sum())}
    case("paired: errors divided by 4 -> all improved, known transition counts",
         s["error"]["fraction_improved"] == 1.0 and {k: s["transitions_1px"][k]["count"] for k in want} == want,
         got={k: s["transitions_1px"][k]["count"] for k in want}, want=want)
    e3 = {k: v[: 3000].copy() for k, v in e.items()}
    s, _ = R.paired_core(e, e3, r, r)
    case("paired: different evaluable sets -> common = intersection",
         s["counts"]["common"] == 3000 and s["counts"]["only_256"] == 1000 and s["counts"]["only_4096"] == 0)
    rr = {k: v.copy() for k, v in r.items()}
    rr["peak_s"][0, :3] = [10.0, 50.0, 12.0]
    rr["peak_zncc"][0, :3] = [0.9, 0.8, 0.95]
    cs = R.competing_score(rr, np.array([0]), np.array([10.5]))
    case("paired: competing peak excludes peaks within 1.5 px of ORACLE-ON-CURVE", cs[0] == 0.8, got=float(cs[0]))
    return {"schema": "AB1d2-preflight-tests-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "known answers for what is new in AB1d2 (render-setting and EXR-header comparison, calibration "
                         "and search-geometry identity, source / constant / benchmark verification, paired statistics); "
                         "no Classroom render; no 4096-spp Classroom image",
            "cases": cases, "seconds": round(time.time() - t0, 3), "passed": all(c["passed"] for c in cases)}
