"""North Star-1b corruption / mutation suite (contract section 19).

Run from ``check_ns1b.py --corruptions`` after a passing baseline.  A temporary mirror of RUN and VIS is built (small
files copied; large arrays symlinked and unlinked before any write, so nothing writes through to the canonical run).
An unmodified-mirror null probe must pass every check.  Each corruption then mutates a fresh mirror -- a regenerated
wrong artifact, an altered record, an in-process mutation of the code under check, or a figure -- regenerates the
mirror's manifest (so the manifest check is not what catches it) and runs the checks it names; each named check must
fail.  Corruptions that do not apply to the executed case are recorded NOT APPLICABLE, never counted as caught.  The
canonical RUN and VIS are hashed before and after the suite.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ns1b as C  # noqa: E402

BIG = 1 << 20


def tree_hashes(root: Path) -> dict:
    return {str(p.relative_to(root)): C.sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def mirror(run: Path, vis: Path, td: Path) -> tuple[Path, Path]:
    m, mv = td / "run", td / "vis"
    for src, dst in ((run, m), (vis, mv)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.stat().st_size > BIG and src == run:
                os.symlink(p.resolve(), q)
            else:
                shutil.copyfile(p, q)
    return m, mv


def unlinked(p: Path) -> Path:
    if p.is_symlink():
        p.unlink()
    return p


def jl(m: Path, rel: str):
    return json.loads((m / rel).read_text())


def js(m: Path, rel: str, d) -> None:
    unlinked(m / rel).write_text(json.dumps(d, indent=1, sort_keys=True, allow_nan=False) + "\n")


def nl(m: Path, rel: str) -> dict:
    with np.load(m / rel, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def ns(m: Path, rel: str, d: dict) -> None:
    np.savez_compressed(unlinked(m / rel), **d)


def remanifest(m: Path) -> None:
    man = jl(m, "manifest.json")
    files = sorted(str(p.relative_to(m)) for p in m.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    man["files"] = {f: C.sha256(m / f) for f in files}
    js(m, "manifest.json", man)


def edit(m: Path, rel: str, fn) -> None:
    d = jl(m, rel)
    fn(d)
    js(m, rel, d)


def log_append(m: Path, entry: dict) -> None:
    unlinked(m / "process-log.jsonl")
    with open(m / "process-log.jsonl", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def log_entries(m: Path) -> list[dict]:
    return [json.loads(ln) for ln in (m / "process-log.jsonl").read_text().splitlines() if ln.strip()]


# ------------------------------------------------------------------ the corruptions
def sel_regen(m: Path, rule: str) -> None:
    doc = json.loads((C.NS1A / "seeds/seed-set.json").read_text())
    rows = []
    for e in doc["entities"]:
        if not e["initialized"] or (rule != "no_patch_filter" and int(e["contributing_patches"]) != 1):
            continue
        r = int(e["initialized_at_rank"])
        lev = C.own_leverage(C.own_dir(*C.GAZES[r]))
        rows.append({"temporary_entity_id": int(e["temporary_entity_id"]), "initialized_at_rank": r,
                     "initialization_gaze_deg": list(C.GAZES[r]), "leverage": lev,
                     "final_surfels": int(e["final_surfels"]), "contributing_patches": int(e["contributing_patches"])})
    key = (lambda r: (-r["leverage"], r["temporary_entity_id"])) if rule == "id_tie" else \
        (lambda r: (-r["leverage"], -r["final_surfels"], r["temporary_entity_id"]))
    rows.sort(key=key)

    def f(d):
        d["candidates"] = [{**r, "g_H0": C.own_dir(*r["initialization_gaze_deg"]).tolist(),
                            "b_dot_g": float(C.own_dir(*r["initialization_gaze_deg"])[0])} for r in rows]
        d["selected"], d["selected_rank"] = rows[0]["temporary_entity_id"], rows[0]["initialized_at_rank"]
        d["selected_gaze_deg"] = rows[0]["initialization_gaze_deg"]
    edit(m, "selection/target-selection.json", f)


def chart_edit(m: Path, fn) -> None:
    def f(d):
        r = np.asarray(d["R_HC"], float)
        d["R_HC"] = fn(r, np.asarray(d["g0_H0"], float)).tolist()
    edit(m, "chart/policy-chart.json", f)


def centroid_chart(r, g0):
    xyz = np.asarray(np.load(Path(MIRROR[0]) / "context/target-map-H0.npz")["xyz_h"], float)
    c = xyz.mean(0)
    return C.own_chart(c / np.linalg.norm(c))


def predicted(m: Path, fn) -> None:
    def f(d):
        pc = d["probe"]["gate"]["detail"]["predicted_calibration"]
        fn(pc, d)
    edit(m, "probe/pre-action-probe.json", f)


def has_predicted(case: str, m: Path) -> bool:
    return jl(m, "probe/pre-action-probe.json")["probe"]["gate"]["detail"].get("predicted_calibration") is not None


def rot_head(pc, _d):
    c, s = np.cos(np.radians(5.0)), np.sin(np.radians(5.0))
    pc["head_R_wh"] = (np.asarray(pc["head_R_wh"]) @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])).tolist()


def reset_centres(pc, _d):
    r = np.asarray(jl(MIRROR[0], "chart/policy-chart.json")["R_HC"], float)
    for e, sgn in zip(pc["eyes"], (-1.0, 1.0)):
        e["centre_h_m"] = (sgn * 0.0315 * r[:, 0]).tolist()


def ipd(pc, _d):
    pc["ipd_m"] = 0.064
    for e, sgn in zip(pc["eyes"], (-1.0, 1.0)):
        e["centre_h_m"] = [sgn * 0.032, 0.0, 0.0]


def head_pose(pc, _d):
    pc["head_origin_w_m"] = [v + 0.05 for v in pc["head_origin_w_m"]]


def fake_local(pc, d):
    local = d["probe"]["proposal"]["local_gaze_deg"]
    fake = C.own_calibration(*local)
    pc.clear()
    pc.update(fake)
    for p3 in d["probe"]["adapter"]["p3"]:
        p3["calibration_gaze_deg"] = list(local)


def policy_record(key, value):
    def f(m):
        def g(d):
            cfg = d["policy_configuration_used"]
            if key in ("yaw_max_deg", "tangent_asymmetry_min"):
                cfg["SURFACE_FRONTIER"][key] = value
                cfg["SURFACE_FRONTIER_facade"][key] = value
            elif key == "radius":
                cfg["FSG6F_FUSION"]["association_radius_m"] = value
                d["probe"]["decisions"]["fsg6f_decision"]["frontier_state_radius_m"] = value
            elif key == "grid":
                cfg["CYCLOPEAN_GRID_DEG"] = value
                cfg["cyclopean_chart_shape"] = [201, 251]
        edit(m, "probe/pre-action-probe.json", g)
    return f


def consensus(m):
    def g(d):
        d["probe"]["decisions"]["fsg6f_decision"]["candidate_state_rule"] = "any_open_support"
    edit(m, "probe/pre-action-probe.json", g)


@contextlib.contextmanager
def live_step():
    import fsg6f_public as PUB
    old = PUB.SURFACE_FRONTIER["component_step_deg"]
    PUB.SURFACE_FRONTIER["component_step_deg"] = 4.0
    try:
        yield
    finally:
        PUB.SURFACE_FRONTIER["component_step_deg"] = old


@contextlib.contextmanager
def live_p1(mode: str):
    import ns1b_chart as CH
    orig = CH.PolicyChartAdapter._p1

    def broken(self, original):
        r = self.r

        def project_rectified_core(calibration, xyz_h, side):
            self.calls["P1"] += 1
            pts = np.asarray(xyz_h, float).reshape(-1, 3)
            return original(calibration, pts if mode == "no_transform" else pts @ r, side)
        return project_rectified_core
    CH.PolicyChartAdapter._p1 = broken
    try:
        yield
    finally:
        CH.PolicyChartAdapter._p1 = orig


def world_map(m):
    def g(d):
        p = d["probe"]["proposal"]
        r = np.asarray(jl(m, "chart/policy-chart.json")["R_HC"], float)
        p["world_gaze_deg"] = list(C.own_yp(r.T @ C.own_dir(*p["local_gaze_deg"])))   # transpose error
    edit(m, "probe/pre-action-probe.json", g)


def rerender_seed(m):
    def g(d):
        k = [k for k in d["inputs"] if k.endswith("rgb-observation.npz")][0]
        d["inputs"][k] = "0" * 64
    edit(m, "context/context.json", g)


def alter_map(m):
    a = nl(m, "context/target-map-H0.npz")
    a["xyz_h"] = a["xyz_h"].copy()
    a["xyz_h"][0] += 0.01
    ns(m, "context/target-map-H0.npz", a)


def catalog_read(rel):
    def f(m):
        def g(d):
            p = str(m / "observation/evaluation_only/instance-catalog.json")
            d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
            d["data_reads"] = sorted(set(d["data_reads"]) | {p})
        edit(m, rel, g)
    return f


def change_gaze(m):
    def g(d):
        d["actions"][0]["world_gaze_deg"] = [v + 0.5 for v in d["actions"][0]["world_gaze_deg"]]
    edit(m, "probe/decision.json", g)


def second_gaze(m):
    e = [x for x in log_entries(m) if x["command"] == "acquire"][0]
    log_append(m, {**e, "finished_utc": "later"})


def switch_target(m):
    a = nl(m, "fusion/target-patch.npz")
    a["instance_id"] = np.full_like(a["instance_id"], 212)
    ns(m, "fusion/target-patch.npz", a)


def sgbm_like(m):
    a = nl(m, "correspondence/oracle-correspondences.npz")
    a["uv_R"] = a["uv_R"] + np.random.default_rng(1).normal(scale=0.3, size=a["uv_R"].shape)
    ns(m, "correspondence/oracle-correspondences.npz", a)


def planar_geometry(m):
    a = nl(m, "geometry/epipolar-result.npz")
    a["P_epi"] = a["P_epi"] * 1.002
    ns(m, "geometry/epipolar-result.npz", a)


def round_uvr(m):
    a = nl(m, "correspondence/oracle-correspondences.npz")
    a["uv_R"] = np.rint(a["uv_R"])
    ns(m, "correspondence/oracle-correspondences.npz", a)


def position_to_geometry(m):
    def g(d):
        p = str(m / "observation/oracle_aid/reference-observation.npz")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
        d["position_reads"] = 1
    edit(m, "geometry/geometry-opened-files.json", g)


def fuse_in_c(m):
    r = np.asarray(jl(m, "chart/policy-chart.json")["R_HC"], float)
    a = nl(m, "fusion/fused-target-map.npz")
    a["xyz_h"] = a["xyz_h"] @ r
    ns(m, "fusion/fused-target-map.npz", a)


def radius_regen(m):
    from fov3d.reconstruction import surface_map as SMm
    import ns1b_core as COREm
    m0 = nl(m, "context/target-map-H0.npz")
    p = nl(m, "fusion/target-patch.npz")
    sm = SMm.SurfaceMap(m0["xyz_h"].astype(float).copy(), m0["rgb"].astype(float).copy(), m0["instance_id"].copy(),
                        m0["support_count"].copy(), m0["provenance_mask"].copy(), [str(x) for x in m0["patch_ids"]])
    k = int(jl(m, "selection/target-selection.json")["selected"])
    patch = {"frame": "H0", "patch_id": C.PATCH_ID, "xyz_h": p["xyz_h"], "rgb": p["rgb"], "instance_id": p["instance_id"],
             "points": int(len(p["xyz_h"]))}
    fused, rec = COREm.fuse_h0(sm, patch, k, 0.024, 0.024)
    ns(m, "fusion/fused-target-map.npz", COREm.map_arrays(fused))
    edit(m, "fusion/fusion.json", lambda d: d.update({key: rec[key] for key in ("matched", "new", "affected_surfels",
                                                                                "map_after")}, radius_m=0.024))


def cell_record(m):
    edit(m, "fusion/fusion.json", lambda d: d.update(hash_cell_m=0.024))


def no_idempotence(m):
    edit(m, "fusion/fusion.json", lambda d: d["replay"].update(exact=False))


def man_edit(fn):
    def f(m, mv):
        d = json.loads((mv / "visuals-manifest.json").read_text())
        fn(d)
        (mv / "visuals-manifest.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    return f


def pixel(m, mv):
    p = mv / "overview.png"
    im = Image.open(p).convert("RGB")
    x, y = 100, 100
    v = im.getpixel((x, y))
    im.putpixel((x, y), (255 - v[0], v[1], v[2]))
    im.save(p, format="PNG", optimize=False)


def k4_flip(m):
    def g(d):
        d["replay"]["K4"]["verdict"] = [True, "novel_support_in_predicted_cores"]
    edit(m, "covariance/covariance-report.json", g)


def gate_flip(m):
    def g(d):
        d["gate"]["admissible"] = not d["gate"]["admissible"]
    edit(m, "probe/decision.json", g)


ANY = lambda case, m: True  # noqa: E731
CASE_B = lambda case, m: case == "B"  # noqa: E731
PROPOSAL = lambda case, m: jl(m, "probe/pre-action-probe.json")["probe"]["proposal"] is not None  # noqa: E731
FUSED = lambda case, m: case == "B" and jl(m, "fusion/fusion.json")["action"] == "FUSED"  # noqa: E731
PATCH = lambda case, m: case == "B" and len(nl(m, "fusion/target-patch.npz")["xyz_h"]) > 0  # noqa: E731
MIRROR: list = [None]

CORRUPTIONS = [
    # (family, name, applies, mutation, kind, expected catching checks)
    ("TARGET", "multi-patch entity included", ANY, lambda m: sel_regen(m, "no_patch_filter"), "run", ["04", "05"]),
    ("TARGET", "leverage altered", ANY, lambda m: edit(m, "selection/target-selection.json", lambda d: d["candidates"][0]
                                                       .update(leverage=0.99)), "run", ["04"]),
    ("TARGET", "tie rule changed (lowest id before surfels)", ANY, lambda m: sel_regen(m, "id_tie"), "run", ["04", "05"]),
    ("TARGET", "object name / catalog read in the selection", ANY,
     catalog_read("selection/selection-opened-files.json"), "run", ["04", "24"]),
    ("TARGET", "another id selected", ANY, lambda m: edit(m, "selection/target-selection.json",
                                                          lambda d: d.update(selected=212)), "run", ["04", "05"]),
    ("CHART", "one basis axis flipped", ANY, lambda m: chart_edit(m, lambda r, g: r * np.array([1.0, -1.0, 1.0])),
     "run", ["05"]),
    ("CHART", "map centroid instead of the initialization gaze", ANY, lambda m: chart_edit(m, centroid_chart), "run",
     ["05"]),
    ("CHART", "wrong cross-product order", ANY, lambda m: chart_edit(
        m, lambda r, g: np.column_stack((r[:, 0], np.cross(r[:, 0], r[:, 2]), r[:, 2]))), "run", ["05"]),
    ("CHART", "non-orthogonal basis (unprojected baseline as x)", ANY, lambda m: chart_edit(
        m, lambda r, g: np.column_stack((np.array([1.0, 0, 0]), r[:, 1], r[:, 2]))), "run", ["05"]),
    ("CHART", "H0 / C transpose error", ANY, lambda m: chart_edit(m, lambda r, g: r.T), "run", ["05"]),
    ("PHYSICAL SENSOR", "physical head rotated", has_predicted, lambda m: predicted(m, rot_head), "run", ["10"]),
    ("PHYSICAL SENSOR", "local eye centres reset to +/-X of the chart", has_predicted,
     lambda m: predicted(m, reset_centres), "run", ["10"]),
    ("PHYSICAL SENSOR", "IPD changed", has_predicted, lambda m: predicted(m, ipd), "run", ["10"]),
    ("PHYSICAL SENSOR", "head pose changed", has_predicted, lambda m: predicted(m, head_pose), "run", ["10"]),
    ("PHYSICAL SENSOR", "local fake calibration used for observability", has_predicted,
     lambda m: predicted(m, fake_local), "run", ["07", "10", "14"]),
    ("POLICY", "+/-25 / +/-20 domain changed", ANY, policy_record("yaw_max_deg", 20.0), "run", ["06"]),
    ("POLICY", "5 deg step changed (in-process)", ANY, live_step, "live", ["06", "12"]),
    ("POLICY", "frontier threshold changed", ANY, policy_record("tangent_asymmetry_min", 0.10), "run", ["06"]),
    ("POLICY", "consensus changed", ANY, consensus, "run", ["12"]),
    ("POLICY", "12-mm map resolution changed", ANY, policy_record("radius", 0.024), "run", ["06", "12"]),
    ("POLICY", "Cyclopean grid changed", ANY, policy_record("grid", 0.2), "run", ["06"]),
    ("PROJECTION", "C points projected directly with the H0 calibration (in-process)", ANY,
     lambda: live_p1("no_transform"), "live", ["08"]),
    ("PROJECTION", "wrong C -> H0 transform (in-process)", ANY, lambda: live_p1("transpose"), "live", ["08"]),
    ("PROJECTION", "wrong world-gaze mapping", PROPOSAL, world_map, "run", ["15"]),
    ("SOURCE", "initial seed re-rendered", ANY, rerender_seed, "run", ["03"]),
    ("SOURCE", "seed map altered", ANY, alter_map, "run", ["11"]),
    ("SOURCE", "catalog opened by the probe", ANY, catalog_read("probe/probe-opened-files.json"), "run", ["12", "24"]),
    ("ACTION", "controller-selected gaze changed", CASE_B, change_gaze, "run", ["15"]),
    ("ACTION", "a second gaze executed", CASE_B, second_gaze, "run", ["22", "23"]),
    ("ACTION", "target switched", PATCH, switch_target, "run", ["21"]),
    ("MEASUREMENT", "SGBM-like correspondence used", CASE_B, sgbm_like, "run", ["18"]),
    ("MEASUREMENT", "planar / other metric geometry used", CASE_B, planar_geometry, "run", ["19"]),
    ("MEASUREMENT", "perfect uv_R rounded", CASE_B, round_uvr, "run", ["18"]),
    ("MEASUREMENT", "Position exposed to the spherical geometry", CASE_B, position_to_geometry, "run", ["19", "24"]),
    ("FUSION", "fused in C coordinates", CASE_B, fuse_in_c, "run", ["21"]),
    ("FUSION", "radius changed (regenerated)", CASE_B, radius_regen, "run", ["21"]),
    ("FUSION", "hash cell changed", CASE_B, cell_record, "run", ["21"]),
    ("FUSION", "idempotence disabled", FUSED, no_idempotence, "run", ["21"]),
    ("FUSION", "fusion record claims the chart frame", FUSED,
     lambda m: edit(m, "fusion/fusion.json", lambda d: d.update(frame="C")), "run", ["21"]),
    ("COVARIANCE", "K4 verdict altered", ANY, k4_flip, "run", ["08"]),
    ("DECISION", "gate verdict flipped in the decision", ANY, gate_flip, "run", ["14"]),
    ("VISUAL", "local / H0 frame label omitted", ANY, man_edit(lambda d: d["figures"]["overview.png"]["labels"].remove(
        "POLICY CHART C")), "vis", ["25"]),
    ("VISUAL", "head motion implied", ANY, man_edit(lambda d: d.update(fixed_head_statement="HEAD RECENTERED")), "vis",
     ["25"]),
    ("VISUAL", "oracle badge removed", ANY, man_edit(lambda d: d["figures"]["overview.png"]["badges"].remove(
        "ORACLE INPUT")), "vis", ["25"]),
    ("VISUAL", "a canonical pixel altered", ANY, pixel, "vis", ["25"]),
]


def run_suite(run: Path, vis: Path, baseline_failed: list) -> dict:
    run, vis = Path(run), Path(vis)
    before = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out = {"baseline_failed": list(baseline_failed), "results": [], "missed": [], "not_applicable": []}
    if baseline_failed:
        out["error"] = "the suite runs only from a passing baseline"
        out["run_unchanged_by_suite"] = True
        return out
    case = json.loads((run / "probe/decision.json").read_text())["case"]
    with tempfile.TemporaryDirectory(prefix="ns1b-corrupt-") as td:
        m, mv = mirror(run, vis, Path(td) / "null")
        null = C.run_checks(m, mv, quiet=True)
        out["null_probe"] = {"failed": [k for k, v in null.items() if not v["pass"]], "checked": len(null)}
        for family, name, applies, mutate, kind, expect in CORRUPTIONS:
            d = Path(td) / f"c{len(out['results']):02d}"
            m, mv = mirror(run, vis, d)
            MIRROR[0] = m
            if not applies(case, m):
                rec = {"family": family, "corruption": name, "status": "NOT APPLICABLE",
                       "reason": f"Case {case}: the mutated product does not exist or is empty in this run"}
                out["not_applicable"].append(name)
                out["results"].append(rec)
                shutil.rmtree(d)
                continue
            if kind == "live":
                with mutate():
                    res = C.run_checks(m, mv, only=set(expect), quiet=True)
            else:
                if kind == "vis":
                    mutate(m, mv)
                else:
                    mutate(m)
                remanifest(m)
                res = C.run_checks(m, mv, only=set(expect), quiet=True)
            caught = [k for k in expect if not res[k]["pass"]]
            rec = {"family": family, "corruption": name, "expected": expect, "caught_by": caught,
                   "status": "CAUGHT" if caught == expect else "MISSED"}
            if caught != expect:
                out["missed"].append(name)
                rec["details"] = {k: res[k]["detail"] for k in expect if res[k]["pass"]}
            out["results"].append(rec)
            print(f"{C.PREFIX} corruption {rec['status']:<14} {family}: {name} -> {caught}", flush=True)
            shutil.rmtree(d)
    after = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out["run_unchanged_by_suite"] = after == before
    applicable = [r for r in out["results"] if r["status"] != "NOT APPLICABLE"]
    out["caught"] = sum(1 for r in applicable if r["status"] == "CAUGHT")
    out["applicable"] = len(applicable)
    out["marker"] = "NORTH_STAR1B_MUTATIONS_CAUGHT" if not out["missed"] and not out["null_probe"]["failed"] \
        and out["run_unchanged_by_suite"] else "NORTH_STAR1B_MUTATIONS_INCOMPLETE"
    print(f"{C.PREFIX} corruptions caught {out['caught']}/{out['applicable']} (not applicable "
          f"{len(out['not_applicable'])}); null probe failed {out['null_probe']['failed']}; run unchanged "
          f"{out['run_unchanged_by_suite']}; {out['marker']}", flush=True)
    return out
