"""North Star-1c corruption / mutation suite (contract section 24).

Run from ``check_ns1c.py --corruptions`` after a passing baseline.  A temporary mirror of RUN and VIS is built (small
files copied; large arrays symlinked and unlinked before any write, so nothing writes through to the canonical run).
An unmodified-mirror null probe must pass every check.  Each corruption then mutates a fresh mirror -- an altered record,
a regenerated wrong artifact, an in-process mutation of the code under check, or a figure -- regenerates the mirror's
manifest (so the manifest check is not what catches it) and runs the checks it names; each named check must fail.
Corruptions that do not apply to the executed trajectory are recorded NOT APPLICABLE, never counted as caught.  The
canonical RUN and VIS are hashed before and after the suite.
"""
from __future__ import annotations

import contextlib
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
import check_ns1c as C  # noqa: E402

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
    (m / rel).parent.mkdir(parents=True, exist_ok=True)
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


def log_entries(m: Path) -> list[dict]:
    return [json.loads(ln) for ln in (m / "process-log.jsonl").read_text().splitlines() if ln.strip()]


def log_append(m: Path, entries: list[dict]) -> None:
    unlinked(m / "process-log.jsonl")
    with open(m / "process-log.jsonl", "a") as f:
        for e in entries:
            f.write(json.dumps(e, sort_keys=True) + "\n")


# ------------------------------------------------------------------ trajectory helpers
def executed(m: Path) -> list[tuple[int, dict]]:
    out = []
    for p in sorted((m / "steps").glob("step-*/plan/decision.json")) if (m / "steps").exists() else []:
        k = int(p.parent.parent.name.split("-")[1])
        d = json.loads(p.read_text())
        if d["kind"] == "attend" and (m / f"steps/step-{k:02d}/update/update.json").exists():
            out.append((k, d))
    return out


def switch_step(m: Path) -> int | None:
    return next((k for k, d in executed(m) if int(d["action"]["target"]) != C.CONTINUING), None)


def fused_step(m: Path) -> int | None:
    return next((k for k, _d in executed(m) if jl(m, f"steps/step-{k:02d}/fusion/fusion.json")["action"] == "FUSED"),
                None)


def state_before(k: int) -> str:
    return "scene/state-initial.json" if k == 0 else f"scene/state-after-step-{k - 1:02d}.json"


def first_other(m: Path) -> str:
    return next(str(k) for k in jl(m, "scene/state-initial.json")["scene_ids"] if int(k) != C.CONTINUING)


# ------------------------------------------------------------------ the corruptions
def include(eid: int):
    def f(m):
        def g(d):
            d["coherent_ids"] = sorted(d["coherent_ids"] + [eid])
            d["scene_ids"] = sorted(d["scene_ids"] + [eid])
        edit(m, "eligibility/coherent-seed-set.json", g)

        def h(d):
            d["scheduler_decision"]["summaries"] = sorted(d["scheduler_decision"]["summaries"] + [[eid, "QUIET"]])
        edit(m, "steps/step-00/plan/decision.json", h)
    return f


def drop_seed(m):
    k = int(first_other(m))
    edit(m, "eligibility/coherent-seed-set.json", lambda d: d.update(
        coherent_ids=[i for i in d["coherent_ids"] if i != k], scene_ids=[i for i in d["scene_ids"] if i != k]))

    def g(d):
        d["entities"].pop(str(k))
        d["scene_ids"] = [i for i in d["scene_ids"] if i != k]
        d["table"] = [r for r in d["table"] if int(r["temporary_entity_id"]) != k]
    edit(m, "scene/state-initial.json", g)


def use_names(m):
    def g(d):
        p = str(m / "seeds/instance-catalog.json")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
    edit(m, "eligibility/eligibility-opened-files.json", g)
    edit(m, "eligibility/coherent-seed-set.json", lambda d: d["fields_read"].append("object_name"))


def revert_172(m):
    maps = C.load(C.NS1A / "seeds/entity-maps.npz")
    a = {f: maps[f"e00172_{f}"] for f in ("xyz_h", "rgb", "instance_id", "support_count", "provenance_mask",
                                         "patch_ids")}
    ns(m, "contexts/entities/e00172/map-H0.npz", a)


def drop_ns1b_look(m):
    def g(d):
        r = d["entities"][str(C.CONTINUING)]
        r["looks"] = r["looks"][:1]
        r["own_looks"] = 1
        r["visited"] = [[0.0, 0.0]]
        r["current_local_gaze"] = [0.0, 0.0]
    edit(m, "scene/state-initial.json", g)


def alter_visited(m):
    edit(m, "scene/state-initial.json", lambda d: d["entities"][str(C.CONTINUING)].update(visited=[[0.0, 0.0],
                                                                                                    [0.0, -10.0]]))


def rerender_seed(m):
    k = first_other(m)
    edit(m, "scene/state-initial.json", lambda d: d["entities"][k]["looks"][0].update(calibration_sha256="0" * 64))


def recenter(m):
    k, d = executed(m)[0]
    t = str(d["action"]["target"])
    r = C.own_chart(C.own_dir(*d["action"]["world_gaze_deg"]))
    h = hashlib.sha256(np.ascontiguousarray(r).tobytes()).hexdigest()
    edit(m, f"scene/state-after-step-{k:02d}.json", lambda s: s["entities"][t].update(chart_sha256=h))
    edit(m, f"steps/step-{k:02d}/update/probes/e{int(t):05d}.json", lambda p: p["probe"]["adapter"].update(
        R_HC=r.tolist()))


def chart_edit(fn):
    def f(m):
        k = first_other(m)

        def g(d):
            r = np.asarray(d["charts"][k]["R_HC"], float)
            d["charts"][k]["R_HC"] = fn(r, m, k).tolist()
        edit(m, "charts/policy-charts.json", g)
    return f


def centroid(_r, m, k):
    rec = jl(m, "scene/state-initial.json")["entities"][k]
    xyz = nl(m, rec["map"]["path"].split(":", 1)[1])["xyz_h"]
    c = xyz.mean(0)
    return C.own_chart(c / np.linalg.norm(c))


def current_none(m):
    edit(m, "scene/state-initial.json", lambda d: d.update(current=None))


def manual_target(m):
    k, d = executed(m)[0]
    others = [int(a) for a, b in d["scheduler_decision"]["summaries"] if int(a) != int(d["action"]["target"])]

    def g(dd):
        dd["scheduler_decision"]["target_id"] = others[0]
        dd["action"]["target"] = others[0]
    edit(m, f"steps/step-{k:02d}/plan/decision.json", g)


def has_switch(m):
    return switch_step(m) is not None


def has_alt_switch(m):
    k = switch_step(m)
    if k is None:
        return False
    d = jl(m, f"steps/step-{k:02d}/plan/decision.json")
    return any(b == "ACTIONABLE" and int(a) != int(d["action"]["target"]) and int(a) != C.CONTINUING
               for a, b in d["scheduler_decision"]["summaries"])


def reorder(m):
    k = switch_step(m)
    d = jl(m, f"steps/step-{k:02d}/plan/decision.json")
    alt = next(int(a) for a, b in d["scheduler_decision"]["summaries"]
               if b == "ACTIONABLE" and int(a) != int(d["action"]["target"]) and int(a) != C.CONTINUING)

    def g(dd):
        dd["scheduler_decision"]["target_id"] = alt
        dd["action"]["target"] = alt
    edit(m, f"steps/step-{k:02d}/plan/decision.json", g)


def switch_while_actionable(m):
    k = switch_step(m)
    edit(m, state_before(k), lambda d: d["entities"][str(C.CONTINUING)].update(
        service={"state": "ACTIONABLE", "blocked_reason": None, "label": "ACTIONABLE"}))

    def g(dd):
        dd["scheduler_decision"]["summaries"] = [[a, "ACTIONABLE" if int(a) == C.CONTINUING else b]
                                                 for a, b in dd["scheduler_decision"]["summaries"]]
    edit(m, f"steps/step-{k:02d}/plan/decision.json", g)


def deferred_quiet(m):
    last = sorted((m / "scene").glob("state-*.json"))[-1].name

    def g(d):
        r = json.loads(json.dumps(d["entities"][str(C.CONTINUING)]))
        r.update(temporary_entity_id=10, service={"state": "QUIET", "blocked_reason": None, "label": "QUIET"})
        d["entities"]["10"] = r
    edit(m, f"scene/{last}", g)


def watchdog_limit(m):
    edit(m, "source/source-manifest.json", lambda d: d.update(watchdog=30, global_cap=30))
    for p in sorted((m / "scene").glob("state-*.json")):
        edit(m, f"scene/{p.name}", lambda d: d.update(watchdog=30, cap=30))


def reset_fixations(m):
    k, d = executed(m)[0]
    t = str(d["action"]["target"])
    edit(m, f"scene/state-after-step-{k:02d}.json", lambda s: s["entities"][t].update(own_looks=1))


def local_as_h0(m):
    k, d = executed(m)[0]
    loc = d["action"]["local_gaze_deg"]
    edit(m, f"steps/step-{k:02d}/plan/decision.json", lambda dd: dd["action"].update(world_gaze_deg=list(loc)))
    b = C.cal_bytes(C.own_calibration(*loc))
    unlinked(m / f"steps/step-{k:02d}/plan/planned-calibration.json").write_bytes(b)
    edit(m, f"steps/step-{k:02d}/plan/decision.json", lambda dd: dd["action"].update(
        planned_calibration_sha256=hashlib.sha256(b).hexdigest()))


def calib(fn):
    def f(m):
        k, _d = executed(m)[0]
        edit(m, f"steps/step-{k:02d}/observation/acquisition/calibration.json", fn)
    return f


def rot_head(c):
    cc, s = np.cos(np.radians(5.0)), np.sin(np.radians(5.0))
    c["head_R_wh"] = (np.asarray(c["head_R_wh"]) @ np.array([[cc, 0, s], [0, 1, 0], [-s, 0, cc]])).tolist()


def ipd(c):
    c["ipd_m"] = 0.064
    for e, sgn in zip(c["eyes"], (-1.0, 1.0)):
        e["centre_h_m"] = [sgn * 0.032, 0.0, 0.0]


def spp(m):
    k, _d = executed(m)[0]
    edit(m, f"steps/step-{k:02d}/observation/acquisition/acquisition.json", lambda d: d.update(spp=1024))


def rerender(m):
    k, _d = executed(m)[0]
    e = [x for x in log_entries(m) if x["command"] == "acquire" and x["step"] == k][0]
    log_append(m, [{**e, "finished_utc": "later"}])


def sgbm(m):
    k, _d = executed(m)[0]
    rel = f"steps/step-{k:02d}/correspondence/oracle-correspondences.npz"
    a = nl(m, rel)
    a["uv_R"] = a["uv_R"] + np.random.default_rng(1).normal(scale=0.3, size=a["uv_R"].shape)
    ns(m, rel, a)


def has_corr(m):
    return bool(executed(m)) and len(nl(m, f"steps/step-{executed(m)[0][0]:02d}/correspondence/"
                                          "oracle-correspondences.npz")["uv_R"]) > 0


def planar(m):
    k, _d = executed(m)[0]
    rel = f"steps/step-{k:02d}/geometry/epipolar-result.npz"
    a = nl(m, rel)
    a["P_epi"] = a["P_epi"] * 1.002
    ns(m, rel, a)


def position_leak(m):
    k, _d = executed(m)[0]

    def g(d):
        p = str(m / f"steps/step-{k:02d}/observation/oracle_aid/reference-observation.npz")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
        d["position_reads"] = 1
    edit(m, f"steps/step-{k:02d}/geometry/geometry-opened-files.json", g)


def fuse_incidental(m):
    k, d = executed(m)[0]
    t = str(d["action"]["target"])
    other = next(kk for kk in jl(m, f"scene/state-after-step-{k:02d}.json")["entities"] if kk != t)
    rel = f"steps/step-{k:02d}/fusion/incidental-{other}.npz"
    src = jl(m, f"scene/state-after-step-{k:02d}.json")["entities"][other]["map"]
    a = nl(m, src["path"].split(":", 1)[1]) if src["path"].startswith("run:") else C.load(C.NS1B / src["path"][5:])
    a["support_count"] = a["support_count"] + 1
    ns(m, rel, a)

    def g(s):
        s["entities"][other]["map"] = {**src, "path": f"run:{rel}", "sha256": C.sha256(m / rel)}
    edit(m, f"scene/state-after-step-{k:02d}.json", g)


def fuse_all(m):
    k, _d = executed(m)[0]
    s = f"steps/step-{k:02d}"
    res = nl(m, f"{s}/geometry/epipolar-result.npz")
    ids = nl(m, f"{s}/segmentation/local-identity.npz")["temporary_entity_id"]
    keep = np.asarray(res["valid_epi"], bool) & (ids > 0)
    ns(m, f"{s}/fusion/target-patch.npz", {"xyz_h": np.asarray(res["P_epi"], float)[keep],
                                           "rgb": np.full((int(keep.sum()), 3), 0.5),
                                           "instance_id": ids[keep].astype(np.int32)})


def has_visible(m):
    if not executed(m):
        return False
    k = executed(m)[0][0]
    ids = nl(m, f"steps/step-{k:02d}/segmentation/local-identity.npz")["temporary_entity_id"]
    return bool((ids > 0).any())


def radius(m):
    import ns1b_core as B
    import ns1c_core as CORE
    k = fused_step(m)
    s = f"steps/step-{k:02d}"
    d = jl(m, f"{s}/plan/decision.json")
    t = int(d["action"]["target"])
    mrec = jl(m, state_before(k))["entities"][str(t)]["map"]
    path = m / mrec["path"].split(":", 1)[1] if mrec["path"].startswith("run:") else C.NS1B / mrec["path"][5:]
    sm = CORE.load_map(path)
    p = nl(m, f"{s}/fusion/target-patch.npz")
    fused, rec = B.fuse_h0(sm, {"frame": "H0", "patch_id": f"ns1c_step_{k:02d}", "xyz_h": p["xyz_h"], "rgb": p["rgb"],
                                "instance_id": p["instance_id"], "points": int(len(p["xyz_h"]))}, t, 0.024, 0.024)
    ns(m, f"{s}/fusion/fused-target-map.npz", B.map_arrays(fused))
    edit(m, f"{s}/fusion/fusion.json", lambda dd: dd.update({kk: rec[kk] for kk in ("matched", "new",
                                                                                   "affected_surfels", "map_after")},
                                                            radius_m=0.024))


def has_fused(m):
    return fused_step(m) is not None


def fuse_in_c(m):
    k, d = executed(m)[0]
    t = str(d["action"]["target"])
    r = np.asarray(jl(m, "charts/policy-charts.json")["charts"][t]["R_HC"], float)
    rel = f"steps/step-{k:02d}/fusion/fused-target-map.npz"
    a = nl(m, rel)
    a["xyz_h"] = a["xyz_h"] @ r
    ns(m, rel, a)


def cross_id(m):
    k, _d = executed(m)[0]
    rel = f"steps/step-{k:02d}/fusion/fused-target-map.npz"
    a = nl(m, rel)
    a["instance_id"] = a["instance_id"].copy()
    a["instance_id"][:5] = 110
    ns(m, rel, a)


def has_final(m):
    return (m / "scene/final-scene-state.json").exists()


def extra_step(third: bool):
    def f(m):
        k = switch_step(m)
        src, dst = m / f"steps/step-{k:02d}", m / f"steps/step-{k + 1:02d}"
        for p in ("plan/decision.json", "update/update.json"):
            (dst / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / p, dst / p)
        d = jl(m, f"steps/step-{k + 1:02d}/plan/decision.json")
        d["global_step"] = k + 1
        if third:
            used = {C.CONTINUING, int(d["action"]["target"])}
            d["action"]["target"] = next(i for i in C.COHERENT if i not in used)
        js(m, f"steps/step-{k + 1:02d}/plan/decision.json", d)
        e = [x for x in log_entries(m) if x["command"] == "schedule" and x["step"] == k][0]
        log_append(m, [{**e, "step": k + 1, "finished_utc": "later"}])
    return f


def emit_closed(m):
    edit(m, "scene/final-scene-state.json" if has_final(m) else "scene/state-initial.json",
         lambda d: d.update(marker="SCENE" + "_CLOSED"))


def man_edit(fn):
    def f(m, mv):
        d = json.loads((mv / "visuals-manifest.json").read_text())
        fn(d)
        (mv / "visuals-manifest.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    return f


def pixel(m, mv):
    p = mv / "overview.png"
    im = Image.open(p).convert("RGB")
    v = im.getpixel((100, 100))
    im.putpixel((100, 100), (255 - v[0], v[1], v[2]))
    im.save(p, format="PNG", optimize=False)


def ns1b_post_altered(m):
    edit(m, f"initial-probe/probes/e{C.CONTINUING:05d}.json",
         lambda d: d["probe"]["proposal"].update(local_gaze_deg=[0.0, -10.0]))


def policy_record(m):
    def g(d):
        d["policy_configuration_used"]["SURFACE_FRONTIER"]["yaw_max_deg"] = 20.0
        d["policy_configuration_used"]["SURFACE_FRONTIER_facade"]["yaw_max_deg"] = 20.0
    edit(m, "initial-probe/initial-service-table.json", g)


@contextlib.contextmanager
def live_watchdog():
    from fov3d.experiments.classroom_oracle import controller01 as c01m
    old = c01m.WATCHDOG
    c01m.WATCHDOG = 30
    try:
        yield
    finally:
        c01m.WATCHDOG = old


def untouched_changed(m):
    k, _d = executed(m)[0]
    targets = {str(dd["action"]["target"]) for _kk, dd in executed(m)}
    other = next(kk for kk in jl(m, f"scene/state-after-step-{k:02d}.json")["entities"] if kk not in targets)

    def g(s):
        lab = s["entities"][other]["service"]["label"]
        new = "QUIET" if lab == "ACTIONABLE" else "ACTIONABLE"
        s["entities"][other]["service"] = {"state": new, "blocked_reason": None, "label": new}
    edit(m, f"scene/state-after-step-{k:02d}.json", g)


def truth_in_probe(m):
    def g(d):
        p = str(C.NS1A / "observations/rank-06/oracle_aid/reference-observation.npz")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
    edit(m, "initial-probe/initial-probe-opened-files.json", g)


ANY = lambda m: True  # noqa: E731
ACTION = lambda m: bool(executed(m))  # noqa: E731
MIRROR: list = [None]

CORRUPTIONS = [
    # (family, name, applies, mutation, kind, expected catching checks)
    ("ELIGIBILITY", "include 10", ACTION, include(10), "run", ["03", "04", "12"]),
    ("ELIGIBILITY", "include 110", ACTION, include(110), "run", ["03", "04", "12"]),
    ("ELIGIBILITY", "include 178", ACTION, include(178), "run", ["03", "04", "12"]),
    ("ELIGIBILITY", "drop a valid coherent seed", ANY, drop_seed, "run", ["03", "04"]),
    ("ELIGIBILITY", "use names / catalog in the eligibility", ANY, use_names, "run", ["03", "24"]),
    ("INITIAL STATE", "revert 172 to its NS1a map", ANY, revert_172, "run", ["08"]),
    ("INITIAL STATE", "remove the NS1b action from 172's history", ANY, drop_ns1b_look, "run", ["08", "14"]),
    ("INITIAL STATE", "alter 172's visited gaze", ANY, alter_visited, "run", ["08"]),
    ("INITIAL STATE", "re-render another seed's initialization look", ANY, rerender_seed, "run", ["08"]),
    ("CHART", "recenter a chart after an action", ACTION, recenter, "run", ["05"]),
    ("CHART", "map centroid instead of the initialization gaze", ANY, chart_edit(centroid), "run", ["05"]),
    ("CHART", "one basis axis flipped", ANY, chart_edit(lambda r, m, k: r * np.array([1.0, -1.0, 1.0])), "run",
     ["05"]),
    ("CHART", "transposed transform", ANY, chart_edit(lambda r, m, k: r.T), "run", ["05"]),
    ("SCHEDULER", "start with current = None", ANY, current_none, "run", ["12"]),
    ("SCHEDULER", "target chosen manually", ACTION, manual_target, "run", ["12"]),
    ("SCHEDULER", "scheduler ordering changed", has_alt_switch, reorder, "run", ["12"]),
    ("SCHEDULER", "switch while the current entity is still actionable", has_switch, switch_while_actionable, "run",
     ["11", "12"]),
    ("SCHEDULER", "deferred ids marked QUIET", ANY, deferred_quiet, "run", ["04"]),
    ("WATCHDOG", "watchdog limit changed", ANY, watchdog_limit, "run", ["02", "14"]),
    ("WATCHDOG", "172 own-look count reset", ACTION, reset_fixations, "run", ["14"]),
    ("WATCHDOG", "watchdog changed in-process", ANY, live_watchdog, "live", ["06"]),
    ("PHYSICAL ACTION", "local gaze used as the H0 gaze", ACTION, local_as_h0, "run", ["07", "13"]),
    ("PHYSICAL ACTION", "head moved", ACTION, calib(rot_head), "run", ["07", "13"]),
    ("PHYSICAL ACTION", "IPD changed", ACTION, calib(ipd), "run", ["07", "13"]),
    ("PHYSICAL ACTION", "spp changed", ACTION, spp, "run", ["15"]),
    ("PHYSICAL ACTION", "observation re-rendered", ACTION, rerender, "run", ["15", "23"]),
    ("MEASUREMENT", "SGBM-like correspondence", has_corr, sgbm, "run", ["16"]),
    ("MEASUREMENT", "planar / other persistent geometry", has_corr, planar, "run", ["17"]),
    ("MEASUREMENT", "Position leak into the spherical stage", ACTION, position_leak, "run", ["17", "24"]),
    ("FUSION", "an incidental entity fused", ACTION, fuse_incidental, "run", ["19"]),
    ("FUSION", "all visible ids fused", has_visible, fuse_all, "run", ["19"]),
    ("FUSION", "radius changed (regenerated)", has_fused, radius, "run", ["19"]),
    ("FUSION", "fused in chart coordinates", ACTION, fuse_in_c, "run", ["19"]),
    ("FUSION", "cross-id fusion", ACTION, cross_id, "run", ["19"]),
    ("STOP", "a second action on the new target", has_final, extra_step(False), "run", ["22"]),
    ("STOP", "a third entity", has_final, extra_step(True), "run", ["22"]),
    ("STOP", "the scene-closure marker emitted", ANY, emit_closed, "run", ["25"]),
    ("PROBE", "the NS1b post-probe reproduction altered", ANY, ns1b_post_altered, "run", ["09", "10"]),
    ("PROBE", "a policy constant changed in the record", ANY, policy_record, "run", ["06"]),
    ("PROBE", "an untouched entity's state changed silently", ACTION, untouched_changed, "run", ["20", "21"]),
    ("PROBE", "truth read by the initial probe", ANY, truth_in_probe, "run", ["09", "24"]),
    ("VISUAL", "deferred identities hidden", ANY, man_edit(lambda d: d["figures"]["overview.png"].update(
        deferred_shown=[])), "vis", ["26"]),
    ("VISUAL", "scheduler reason hidden", ANY, man_edit(lambda d: d["figures"]["scene-scheduler-timeline.png"].update(
        scheduler_reasons_shown=[])), "vis", ["26"]),
    ("VISUAL", "fixed-head statement omitted", ANY, man_edit(lambda d: d.pop("fixed_head_statement")), "vis", ["26"]),
    ("VISUAL", "oracle label removed", ANY, man_edit(lambda d: d["figures"]["overview.png"]["labels"].remove(
        "ORACLE CORRESPONDENCE")), "vis", ["26"]),
    ("VISUAL", "a canonical pixel altered", ANY, pixel, "vis", ["26"]),
]


def run_suite(run: Path, vis: Path, baseline_failed: list, ignore_baseline: tuple = ()) -> dict:
    """``ignore_baseline`` is a development aid only: corruptions naming a check that already fails on the baseline
    are recorded BASELINE FAILING; the canonical suite runs with an empty tuple and a fully passing baseline."""
    run, vis = Path(run), Path(vis)
    before = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out = {"baseline_failed": list(baseline_failed), "results": [], "missed": [], "not_applicable": [],
           "baseline_failing": []}
    if set(baseline_failed) - set(ignore_baseline):
        out["error"] = "the suite runs only from a passing baseline"
        out["run_unchanged_by_suite"] = True
        out["marker"] = "NORTH_STAR1C_MUTATIONS_INCOMPLETE"
        return out
    with tempfile.TemporaryDirectory(prefix="ns1c-corrupt-") as td:
        m, mv = mirror(run, vis, Path(td) / "null")
        null = C.run_checks(m, mv, quiet=True)
        out["null_probe"] = {"failed": [k for k, v in null.items() if not v["pass"] and k not in ignore_baseline],
                             "checked": len(null)}
        shutil.rmtree(Path(td) / "null")
        for family, name, applies, mutate, kind, expect in CORRUPTIONS:
            d = Path(td) / f"c{len(out['results']):02d}"
            m, mv = mirror(run, vis, d)
            MIRROR[0] = m
            if set(expect) & set(ignore_baseline):
                out["baseline_failing"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "BASELINE FAILING (dev)"})
                shutil.rmtree(d)
                continue
            if not applies(m):
                out["not_applicable"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "NOT APPLICABLE",
                                       "reason": "the mutated product does not exist in the executed trajectory"})
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
    applicable = [r for r in out["results"] if r["status"] in ("CAUGHT", "MISSED")]
    out["caught"] = sum(1 for r in applicable if r["status"] == "CAUGHT")
    out["applicable"] = len(applicable)
    out["marker"] = "NORTH_STAR1C_MUTATIONS_CAUGHT" if not out["missed"] and not out["null_probe"]["failed"] \
        and out["run_unchanged_by_suite"] and not out["baseline_failing"] else "NORTH_STAR1C_MUTATIONS_INCOMPLETE"
    print(f"{C.PREFIX} corruptions caught {out['caught']}/{out['applicable']} (not applicable "
          f"{len(out['not_applicable'])}; baseline-failing {len(out['baseline_failing'])}); null probe failed "
          f"{out['null_probe']['failed']}; run unchanged {out['run_unchanged_by_suite']}; {out['marker']}", flush=True)
    return out
