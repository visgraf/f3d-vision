"""North Star-1a corruption / mutation suite (contract section 17), driven by ``check_ns1a.py --corruptions``.

Each corruption is applied to a fresh temporary MIRROR of the run and the visuals (JSON copied, arrays and images
symlinked; a mutated array is materialized first), never to the run itself.  It names the checks that must catch it
and counts as caught only if one of them fails.  "Regenerated" corruptions recompute a genuinely mutated product,
geometry or seed set inside the mirror (and re-hash the freezes and the manifest, so that only the semantic checks
can catch them); their outputs are never inspected for performance and are discarded with the mirror.  An
unmodified-mirror null probe must reproduce the baseline first.  A corruption that the canonical data make a no-op
is recorded as NOT APPLICABLE with its reason, never counted as caught.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import check_ns1a as C  # noqa: E402

NA = "NOT_APPLICABLE"


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mirror(run: Path, vis: Path, root: Path) -> tuple[Path, Path]:
    m_run, m_vis = root / run.name, root / (vis.name + "-vis")
    for src, dst in ((run, m_run), (vis, m_vis)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            else:
                q.parent.mkdir(parents=True, exist_ok=True)
                if p.suffix in (".json", ".jsonl"):
                    shutil.copy2(p, q)
                else:
                    os.symlink(p.resolve(), q)
    return m_run, m_vis


def writable(p: Path) -> Path:
    if p.is_symlink():
        b = p.read_bytes()
        p.unlink()
        p.write_bytes(b)
    return p


def jload(p: Path):
    return json.loads(p.read_text())


def jsave(p: Path, d) -> None:
    writable(p)
    p.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def nload(p: Path) -> dict:
    with np.load(p, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def nsave(p: Path, d: dict) -> None:
    if p.exists() or p.is_symlink():
        p.unlink()
    np.savez_compressed(p, **d)


def save_maps(p: Path, maps: dict) -> None:
    """Never write through a mirror symlink into the run: unlink first, then write the mutated file."""
    import ns1a_run as R
    if p.exists() or p.is_symlink():
        p.unlink()
    R.save_maps(p, maps)


def mutated_surface_map(threshold: int):
    """A genuinely mutated copy of the sealed fsg3 surface map with another point threshold (mirror-only use)."""
    import types
    src = (C.REPO / "tools/fsg3_surface_map.py").read_text()
    assert src.count("len(q.xyz_h) < 100") == 2
    mod = types.ModuleType(f"mutated_fsg3_surface_map_{threshold}")
    sys.modules[mod.__name__] = mod
    exec(compile(src.replace("len(q.xyz_h) < 100", f"len(q.xyz_h) < {int(threshold)}"), "<mutated>", "exec"),
         mod.__dict__)
    return mod


def snapshot_hashes(*roots: Path) -> dict:
    return {str(f): sha256(f) for r in roots for f in sorted(Path(r).rglob("*")) if f.is_file()}


def refreeze(m: Path) -> None:
    """Re-hash every freeze record and the manifest from the (mutated) mirror files."""
    for name in ("observation", "correspondence", "geometry", "seed-set"):
        f = m / f"freeze/{name}-freeze.json"
        d = jload(f)
        d["files"] = {k: sha256(m / k) for k in d["files"] if (m / k).exists()}
        if name == "geometry":
            d["correspondence_freeze_sha256"] = sha256(m / "freeze/correspondence-freeze.json")
        jsave(f, d)
    man = jload(m / "manifest.json")
    man["files"] = {k: sha256(m / k) for k in man["files"] if (m / k).exists()}
    jsave(m / "manifest.json", man)


def log_append(m: Path, entry: dict) -> None:
    p = writable(m / "process-log.jsonl")
    with open(p, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def biggest_rank(m: Path) -> int:
    return max(C.RANKS, key=lambda r: len(nload(m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz")["uv_L"]))


def regen_product(m: Path, r: int, keep_fn) -> int:
    """Own oracle with a mutated rule (keep_fn over the per-pixel terms); returns the product size change."""
    c = jload(m / f"observations/{C.rd(r)}/acquisition/calibration.json")
    ref = nload(m / f"observations/{C.rd(r)}/oracle_aid/reference-observation.npz")
    sl = slice(C.ORIGIN, C.ORIGIN + C.CORE)
    pw = ref["position_w_L"][sl, sl].reshape(-1, 3).astype(float)
    il = ref["instance_L"][sl, sl].reshape(-1).astype(np.int64)
    hit = np.isfinite(pw).all(1) & (pw != 0).any(1)
    ph = (np.where(hit[:, None], pw, 0.0) - np.asarray(c["head_origin_w_m"])) @ np.asarray(c["head_R_wh"])
    e = c["eyes"][1]
    xc = (ph - np.asarray(e["centre_h_m"])) @ np.asarray(e["R_hc"])
    q = xc @ np.asarray(e["K"]).T
    with np.errstate(divide="ignore", invalid="ignore"):
        u, v = q[:, 0] / q[:, 2], q[:, 1] / q[:, 2]
    ok = np.isfinite(u) & np.isfinite(v) & (xc[:, 2] > 1e-9)
    inside = ok & (u >= 0) & (u <= C.RAW - 1) & (v >= 0) & (v <= C.RAW - 1)
    ui = np.rint(np.clip(np.nan_to_num(u), 0, C.RAW - 1)).astype(int)
    vi = np.rint(np.clip(np.nan_to_num(v), 0, C.RAW - 1)).astype(int)
    same = ref["instance_R"][vi, ui] == il
    keep = keep_fn(hit=hit, il=il, inside=inside, same=same, u=u, v=v)
    old = nload(m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz")
    idx = np.flatnonzero(keep)
    rows, cols = (idx // C.CORE).astype(np.int32), (idx % C.CORE).astype(np.int32)
    prod = {"left_core_row": rows, "left_core_col": cols,
            "uv_L": np.c_[cols + C.ORIGIN, rows + C.ORIGIN].astype(np.float64), "uv_R": np.c_[u, v][keep]}
    nsave(m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz", prod)
    return len(idx) - len(old["uv_L"])


def regen_geometry(m: Path, r: int, theta_pole=1.0, phi_sign=1.0, b_sign=1.0) -> None:
    c = jload(m / f"observations/{C.rd(r)}/acquisition/calibration.json")
    p = nload(m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz")
    g = nload(m / f"geometry/{C.rd(r)}/epipolar-result.npz")
    d = {}
    for s, key in ((0, "uv_L"), (1, "uv_R")):
        e = c["eyes"][s]
        k = np.asarray(e["K"])
        a = np.c_[(p[key][:, 0] - k[0, 2]) / k[0, 0], (p[key][:, 1] - k[1, 2]) / k[1, 1], np.ones(len(p[key]))]
        dd = a @ np.asarray(e["R_hc"]).T
        d[s] = dd / np.linalg.norm(dd, axis=1, keepdims=True)
    th = {s: np.arctan2(np.hypot(d[s][:, 1], d[s][:, 2]), theta_pole * d[s][:, 0]) for s in (0, 1)}
    ph = {s: np.arctan2(phi_sign * d[s][:, 1], -d[s][:, 2]) for s in (0, 1)}
    b = b_sign * float(c["ipd_m"])
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = b / (1 / np.tan(th[0]) - 1 / np.tan(th[1]))
    pb = np.arctan2(np.sin(ph[0]) + np.sin(ph[1]), np.cos(ph[0]) + np.cos(ph[1]))
    g["P_epi"] = np.c_[-b / 2 + rho / np.tan(th[0]), rho * np.sin(pb), -rho * np.cos(pb)]
    g["theta_L"], g["theta_R"], g["phi_L"], g["phi_R"] = th[0], th[1], ph[0], ph[1]
    nsave(m / f"geometry/{C.rd(r)}/epipolar-result.npz", g)


def regen_seeds(m: Path, min_points=C.MIN_POINTS, radius=C.RADIUS, cell=C.CELL, doc_patch: dict | None = None) -> None:
    import ns1a_core as CORE
    import ns1a_run as R
    from fov3d.reconstruction import surface_map as SM
    if min_points < C.MIN_POINTS:
        SM = mutated_surface_map(min_points)
    gz = R.gaze_inputs(m)
    res = CORE.construct_seeds(gz, SM, min_points, radius, cell)
    doc = CORE.seed_set_document(gz, res, R.unassigned_record(m))
    doc["accepted_constants"] = jload(m / "seeds/seed-set.json").get("accepted_constants")
    if doc_patch:
        doc["persistence"] = {**doc["persistence"], **doc_patch}
    save_maps(m / "seeds/entity-maps.npz", res["maps"])
    for r, snap in res["snapshots"].items():
        save_maps(m / f"seeds/snapshot-after-{C.rd(r)}.npz", snap)
    jsave(m / "seeds/construction-history.json", {**jload(m / "seeds/construction-history.json"),
                                                   "history": res["history"]})
    jsave(m / "seeds/seed-set.json", doc)


def edit_cal(m: Path, r: int, fn) -> None:
    p = m / f"observations/{C.rd(r)}/acquisition/calibration.json"
    d = jload(p)
    fn(d)
    writable(p)
    p.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


# ---------------------------------------------------------------- the corruptions: (family, name, targets, fn)
def k_change_gaze(m, v):
    p = m / "source/nb1c-gaze-list.json"
    d = jload(p)
    d["gazes"][3]["col"] += 1
    d["gazes"][3]["yaw_deg"] += 0.5
    jsave(p, d)


def k_change_executed_gaze(m, v):
    edit_cal(m, 4, lambda d: d.__setitem__("gaze_yaw_pitch_deg", [38.75, -61.75]))
    refreeze(m)


def k_swap(m, v):
    a, b, t = m / "observations/rank-02", m / "observations/rank-03", m / "observations/tmp-swap"
    a.rename(t)
    b.rename(a)
    t.rename(b)


def k_drop(m, v):
    shutil.rmtree(m / "observations/rank-06")


def k_seventh(m, v):
    shutil.copytree(m / "observations/rank-06", m / "observations/rank-07", symlinks=True)
    p = m / "observations/acquisition-run.json"
    d = jload(p)
    d["ranks_in_order"].append(7)
    jsave(p, d)


def k_spp(m, v):
    p = m / "observations/rank-03/acquisition/acquisition.json"
    d = jload(p)
    d["spp"], d["settings"]["samples"] = 2048, 2048
    jsave(p, d)


def k_head(m, v):
    edit_cal(m, 2, lambda d: d["head_origin_w_m"].__setitem__(0, d["head_origin_w_m"][0] + 0.01))
    refreeze(m)


def k_ipd(m, v):
    def f(d):
        d["ipd_m"] = 0.064
        d["eyes"][0]["centre_h_m"][0], d["eyes"][1]["centre_h_m"][0] = -0.032, 0.032
    edit_cal(m, 1, f)
    refreeze(m)


def k_vergence(m, v):
    edit_cal(m, 5, lambda d: d.__setitem__("prescribed_vergence_distance_m", 2.2))
    refreeze(m)


def k_rerender(m, v):
    p = m / "observations/rank-04/acquisition/rgb-observation.npz"
    d = nload(p)
    d["rgb_L"] = d["rgb_L"].copy()
    d["rgb_L"][320, 320] += 0.01
    nsave(p, d)
    h = sha256(p)
    a = m / "observations/rank-04/acquisition/acquisition.json"
    jsave(a, {**jload(a), "rgb_observation_sha256": h})
    ar = jload(m / "observations/acquisition-run.json")
    ar["per_rank"][3]["rgb_observation_sha256"] = h
    jsave(m / "observations/acquisition-run.json", ar)
    log = [json.loads(x) for x in (m / "process-log.jsonl").read_text().splitlines()]
    log_append(m, next(e for e in log if e["command"] == "acquire"))
    refreeze(m)


def k_round(m, v):
    r = biggest_rank(m)
    p = m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz"
    d = nload(p)
    d["uv_R"] = np.rint(d["uv_R"])
    nsave(p, d)
    refreeze(m)


def k_nominal(m, v):
    r = biggest_rank(m)
    lo, hi = C.ORIGIN, C.ORIGIN + C.CORE - 1
    dn = regen_product(m, r, lambda hit, il, inside, same, u, v: hit & (il > 0) & inside & same & (u >= lo) & (u <= hi)
                       & (v >= lo) & (v <= hi))
    if dn == 0:
        return "no correspondence lies outside the right nominal core"
    refreeze(m)


def k_no_same(m, v):
    r = biggest_rank(m)
    dn = regen_product(m, r, lambda hit, il, inside, same, u, v: hit & (il > 0) & inside)
    if dn == 0:
        return "no inside pair has a different right instance"
    refreeze(m)


def k_id0(m, v):
    r = max(C.RANKS, key=lambda r: jload(m / f"correspondence/{C.rd(r)}/oracle-summary.json")["excluded"][
        "hit_with_instance_0"])
    dn = regen_product(m, r, lambda hit, il, inside, same, u, v: hit & (il >= 0) & inside & same)
    if dn == 0:
        return "no instance-0 hit is right-visible as instance 0"
    refreeze(m)


def k_xyz(m, v):
    r = biggest_rank(m)
    p = m / f"correspondence/{C.rd(r)}/oracle-correspondences.npz"
    d = nload(p)
    d["xyz_h"] = np.zeros((len(d["uv_L"]), 3))
    nsave(p, d)
    refreeze(m)


def k_theta(m, v):
    regen_geometry(m, biggest_rank(m), theta_pole=-1.0)
    refreeze(m)


def k_phi(m, v):
    regen_geometry(m, biggest_rank(m), phi_sign=-1.0)
    refreeze(m)


def k_baseline(m, v):
    regen_geometry(m, biggest_rank(m), b_sign=-1.0)
    refreeze(m)


def k_geo_position(m, v):
    p = m / "geometry/rank-02/geometry-opened-files.json"
    d = jload(p)
    ref = str(m / "observations/rank-02/oracle_aid/reference-observation.npz")
    d["events"].append({"event": "open", "path": ref, "kind": "data-read", "allowed": True})
    d["data_reads"] = sorted(d["data_reads"] + [ref])
    d["position_reads"] = d["object_index_reads"] = 1
    jsave(p, d)


def k_seg_catalog(m, v):
    p = m / "segmentation/segmentation-opened-files.json"
    d = jload(p)
    cat = str(m / "observations/evaluation_only/instance-catalog.json")
    d["events"].insert(3, {"event": "open", "path": cat, "kind": "data-read", "allowed": True})
    d["data_reads"] = sorted(d["data_reads"] + [cat])
    jsave(p, d)


def _rank_with_two_ids(m) -> int | None:
    for r in C.RANKS:
        ids = nload(m / f"segmentation/{C.rd(r)}/local-identity.npz")["temporary_entity_id"]
        if len(set(int(i) for i in ids if i > 0)) >= 2:
            return r
    return None


def k_wrong_pixel(m, v):
    r = biggest_rank(m)
    p = m / f"segmentation/{C.rd(r)}/local-identity.npz"
    d = nload(p)
    il = nload(m / f"observations/{C.rd(r)}/oracle_aid/reference-observation.npz")["instance_L"]
    shifted = il[d["left_core_row"] + C.ORIGIN, d["left_core_col"] + C.ORIGIN + 1]
    new = np.where(d["valid"], shifted, -1).astype(np.int32)
    if np.array_equal(new, d["temporary_entity_id"]):
        return "a one-pixel shift changes no id"
    d["temporary_entity_id"] = new
    nsave(p, d)
    regen_seeds(m)
    refreeze(m)


def k_merge(m, v):
    r = _rank_with_two_ids(m)
    if r is None:
        return "no gaze observes two positive ids"
    p = m / f"segmentation/{C.rd(r)}/local-identity.npz"
    d = nload(p)
    ids = d["temporary_entity_id"]
    u, n = np.unique(ids[ids > 0], return_counts=True)
    a, b = u[np.argsort(-n)][:2]
    d["temporary_entity_id"] = np.where(ids == b, a, ids).astype(np.int32)
    nsave(p, d)
    regen_seeds(m)
    refreeze(m)


def k_promote0(m, v):
    import ns1a_run as R
    maps = R.load_maps(m / "seeds/entity-maps.npz")
    k = max(maps, key=lambda k: len(maps[k]["xyz_h"]))
    maps[0] = {**maps[k], "instance_id": np.zeros_like(maps[k]["instance_id"])}
    save_maps(m / "seeds/entity-maps.npz", maps)
    h = jload(m / "seeds/construction-history.json")
    h["history"].insert(0, {"rank": 1, "entity": 0, "patch_id": "nb1c_gaze_01", "points": len(maps[0]["xyz_h"]),
                            "action": "INITIALIZED", "map_before": 0, "map_after": len(maps[0]["xyz_h"])})
    jsave(m / "seeds/construction-history.json", h)
    refreeze(m)


def k_threshold(m, v):
    regen_seeds(m, min_points=50, doc_patch={"min_points": 50})
    refreeze(m)


def k_radius(m, v):
    regen_seeds(m, radius=0.024, doc_patch={"association_radius_m": 0.024})
    refreeze(m)


def k_cell(m, v):
    regen_seeds(m, cell=0.024, doc_patch={"hash_cell_m": 0.024})
    refreeze(m)


def k_idempotence(m, v):
    import ns1a_run as R
    from fov3d.reconstruction import surface_map as SM
    maps = R.load_maps(m / "seeds/entity-maps.npz")
    k = max(maps, key=lambda k: len(maps[k]["xyz_h"]))
    a = maps[k]
    sm = SM.SurfaceMap(a["xyz_h"], a["rgb"], a["instance_id"], a["support_count"], a["provenance_mask"],
                       [str(p) for p in a["patch_ids"]])
    r = int(str(a["patch_ids"][0])[-2:])
    g = nload(m / f"geometry/{C.rd(r)}/epipolar-result.npz")
    ids = nload(m / f"segmentation/{C.rd(r)}/local-identity.npz")["temporary_entity_id"]
    keep = np.asarray(g["valid_epi"], bool) & (ids == k)
    out, _ = SM.fuse(sm, SM.Patch("nb1c_gaze_99", g["P_epi"][keep], np.zeros((int(keep.sum()), 3)), ids[keep]), k,
                     C.RADIUS, C.CELL)
    maps[k] = C.arrays(out)
    save_maps(m / "seeds/entity-maps.npz", maps)
    refreeze(m)


def k_undersupported(m, v):
    hist = jload(m / "seeds/construction-history.json")["history"]
    if not any(e["action"] in ("SEEN_BUT_NOT_INITIALIZED", "RETAINED_NOT_FUSED") for e in hist):
        return "no undersupported measurement exists"
    regen_seeds(m, min_points=1)        # the recorded rule still says 100
    refreeze(m)


def k_corr_after(m, v):
    p = m / "correspondence/rank-01/oracle-correspondences.npz"
    d = nload(p)
    if not len(d["uv_R"]):
        return "rank 1 has no correspondence"
    d["uv_R"] = d["uv_R"].copy()
    d["uv_R"][0, 0] += 1e-6
    nsave(p, d)


def k_geo_after(m, v):
    r = biggest_rank(m)
    p = m / f"geometry/{C.rd(r)}/epipolar-result.npz"
    d = nload(p)
    d["P_epi"] = d["P_epi"].copy()
    d["P_epi"][0, 2] += 1e-6
    nsave(p, d)


def k_map_after(m, v):
    p = m / "seeds/entity-maps.npz"
    d = nload(p)
    key = sorted(k for k in d if k.endswith("_xyz_h"))[0]
    d[key] = d[key].copy()
    d[key][0, 0] += 1e-6
    nsave(p, d)


def k_sgbm(m, v):
    log_append(m, {"command": "sgbm", "argv": [str(C.REPO / "tools/active_bootstrap/ab1d3_sgbm.py")], "status": "ok",
                   "dev": False, "code": {"commit": C.CONTRACT, "dirty": False, "pushed": True}})


def k_controller(m, v):
    log_append(m, {"command": "controller", "argv": ["-m", "fov3d.experiments.classroom_oracle.controller01"],
                   "status": "ok", "dev": False, "code": {"commit": C.CONTRACT, "dirty": False, "pushed": True}})


def k_fsg6f(m, v):
    p = m / "seeds/seeds-opened-files.json"
    d = jload(p)
    d["modules_loaded"]["fsg6f_public"] = True
    jsave(p, d)


def k_extra_gaze(m, v):
    log = [json.loads(x) for x in (m / "process-log.jsonl").read_text().splitlines()]
    e = dict(next(e for e in log if e["command"] == "acquire"))
    e["result"] = {"ranks": [7]}
    log_append(m, e)


def k_badge(m, v):
    p = v / "visuals-manifest.json"
    d = jload(p)
    d["figures"]["overview.png"]["badges"] = [b for b in d["figures"]["overview.png"]["badges"] if b != "ORACLE INPUT"]
    jsave(p, d)


def k_panels(m, v):
    p = v / "visuals-manifest.json"
    d = jload(p)
    b = d["figures"]["overview.png"]["panels"]["B"]
    b[0], b[1] = b[1], b[0]
    jsave(p, d)


def k_pixel(m, v):
    from PIL import Image
    p = writable(v / "overview.png")
    im = Image.open(p).convert("RGB")
    px = im.getpixel((10, 10))
    im.putpixel((10, 10), tuple((c + 1) % 256 for c in px))
    im.save(p, format="PNG")


def k_eval_early(m, v):
    p = m / "evaluation/evaluation-opened-files.json"
    d = jload(p)
    ev = d["events"]
    i = next(i for i, e in enumerate(ev) if e.get("label") == "reference_access_begins")
    j = next(j for j, e in enumerate(ev) if e.get("event") == "open" and "instance-catalog" in e["path"])
    ev.insert(i, ev.pop(j))
    jsave(p, d)


def k_eval_number(m, v):
    p = m / "evaluation/evaluation.json"
    d = jload(p)
    d["breadth1"]["touched_fraction_observed"] += 0.01
    jsave(p, d)


CORRUPTIONS = [
    ("SELECTION", "change one gaze in the gaze list", ["03"], k_change_gaze),
    ("SELECTION", "change one executed gaze", ["04", "05"], k_change_executed_gaze),
    ("SELECTION", "swap two gaze ranks", ["04", "05"], k_swap),
    ("SELECTION", "drop one gaze", ["04", "08"], k_drop),
    ("SELECTION", "add a seventh gaze", ["04", "30"], k_seventh),
    ("OBSERVATION", "change spp", ["06"], k_spp),
    ("OBSERVATION", "move the head", ["05", "30"], k_head),
    ("OBSERVATION", "change the IPD", ["05"], k_ipd),
    ("OBSERVATION", "change the vergence", ["05"], k_vergence),
    ("OBSERVATION", "re-render one gaze", ["04", "29"], k_rerender),
    ("CORRESPONDENCE", "round uv_R", ["09", "10"], k_round),
    ("CORRESPONDENCE", "restrict the right match to the nominal core (regenerated)", ["09"], k_nominal),
    ("CORRESPONDENCE", "remove the same-instance test (regenerated)", ["09", "10"], k_no_same),
    ("CORRESPONDENCE", "include instance 0 as an ordinary match (regenerated)", ["09", "10"], k_id0),
    ("CORRESPONDENCE", "add an XYZ field to the truth-stripped product", ["10"], k_xyz),
    ("GEOMETRY", "change the theta pole (regenerated)", ["14"], k_theta),
    ("GEOMETRY", "flip the phi sign (regenerated)", ["14"], k_phi),
    ("GEOMETRY", "read Position in the geometry stage", ["13"], k_geo_position),
    ("GEOMETRY", "flip the baseline sign (regenerated)", ["14"], k_baseline),
    ("IDENTITY", "read the catalog before the freeze", ["16", "26"], k_seg_catalog),
    ("IDENTITY", "assign the id from a wrong pixel (seeds regenerated)", ["17"], k_wrong_pixel),
    ("IDENTITY", "merge two ids (seeds regenerated)", ["17"], k_merge),
    ("IDENTITY", "promote instance 0 to an entity", ["19", "20", "22"], k_promote0),
    ("PERSISTENCE", "initialization threshold 50 (regenerated)", ["18", "19", "20"], k_threshold),
    ("PERSISTENCE", "fusion radius 24 mm (regenerated)", ["18", "19"], k_radius),
    ("PERSISTENCE", "hash cell 24 mm (regenerated)", ["18", "19"], k_cell),
    ("PERSISTENCE", "idempotence disabled (a patch re-fused under a new id)", ["18", "19", "21"], k_idempotence),
    ("PERSISTENCE", "fuse an undersupported patch (regenerated)", ["19", "20"], k_undersupported),
    ("FREEZE", "alter the correspondence after its freeze", ["15"], k_corr_after),
    ("FREEZE", "alter the geometry after its freeze", ["15"], k_geo_after),
    ("FREEZE", "alter a seed map after the seed freeze", ["15", "19", "28"], k_map_after),
    ("PROCESS", "invoke SGBM", ["12", "29"], k_sgbm),
    ("PROCESS", "invoke a controller", ["29", "30"], k_controller),
    ("PROCESS", "invoke FSG6f (module loaded)", ["30"], k_fsg6f),
    ("PROCESS", "execute an extra gaze", ["04", "29"], k_extra_gaze),
    ("VISUAL", "remove the oracle-aid badge", ["33"], k_badge),
    ("VISUAL", "reorder the gaze panels", ["32", "33"], k_panels),
    ("VISUAL", "alter a canonical image pixel", ["32"], k_pixel),
    ("EVALUATION", "open the catalog before the reference-access mark", ["25"], k_eval_early),
    ("EVALUATION", "alter an evaluation number", ["27"], k_eval_number),
]


def _one(args) -> dict:
    i, run, vis, baseline_failed = args
    family, name, targets, fn = CORRUPTIONS[i]
    root = Path(tempfile.mkdtemp(prefix="ns1a-mut-"))
    try:
        m, v = mirror(Path(run), Path(vis), root)
        na = fn(m, v)
        if na:
            return {"family": family, "corruption": name, "targets": targets, "status": NA, "reason": na}
        live = [t for t in targets if t not in baseline_failed]
        if not live:
            return {"family": family, "corruption": name, "targets": targets, "status": "TARGETS_FAIL_AT_BASELINE"}
        res = C.run_checks(m, v, only=set(live), quiet=True)
        failed = sorted(k for k, r in res.items() if not r["pass"])
        return {"family": family, "corruption": name, "targets": targets, "failed_targets": failed,
                "status": "CAUGHT" if failed else "MISSED"}
    except Exception as e:  # a crash inside the mutation is a suite defect, reported
        return {"family": family, "corruption": name, "targets": targets, "status": "ERROR", "error": repr(e)}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_suite(run: Path, vis: Path, baseline_failed: list[str]) -> dict:
    before = snapshot_hashes(run, vis)
    root = Path(tempfile.mkdtemp(prefix="ns1a-null-"))
    try:
        m, v = mirror(Path(run), Path(vis), root)
        null = C.run_checks(m, v, quiet=True)
        null_failed = sorted(k for k, r in null.items() if not r["pass"])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    null_clean = null_failed == sorted(baseline_failed)
    print(f"{C.PREFIX} null probe (unmodified mirror): failed={null_failed} clean={null_clean}", flush=True)
    jobs = [(i, str(run), str(vis), list(baseline_failed)) for i in range(len(CORRUPTIONS))]
    with ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 4)) as ex:
        results = list(ex.map(_one, jobs))
    for r in results:
        print(f"{C.PREFIX} corruption [{r['family']}] {r['corruption']}: {r['status']}"
              + (f" by {r['failed_targets']}" if r.get("failed_targets") else "")
              + (f" ({r.get('reason') or r.get('error')})" if r["status"] in (NA, "ERROR") else ""), flush=True)
    after = snapshot_hashes(run, vis)
    touched = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if touched:
        print(f"{C.PREFIX} SUITE DEFECT: the run or visuals changed during the suite: {touched[:5]}", flush=True)
    caught = [r for r in results if r["status"] == "CAUGHT"]
    missed = [r for r in results if r["status"] in ("MISSED", "ERROR")]
    na = [r for r in results if r["status"] == NA]
    base = [r for r in results if r["status"] == "TARGETS_FAIL_AT_BASELINE"]
    applicable = len(results) - len(na) - len(base)
    marker = ("NORTH_STAR1A_MUTATIONS_CAUGHT" if null_clean and not missed and not base and not touched
              else "NORTH_STAR1A_MUTATIONS_INCOMPLETE")
    print(f"{C.PREFIX} corruptions caught {len(caught)}/{applicable} (not applicable {len(na)}; "
          f"baseline-failing targets {len(base)}); null probe clean {null_clean}; {marker}", flush=True)
    return {"null_probe": {"failed": null_failed, "clean": null_clean}, "results": results,
            "run_unchanged_by_suite": not touched, "run_files_hashed": len(before),
            "caught": len(caught), "applicable": applicable, "not_applicable": [r["corruption"] for r in na],
            "baseline_failing": [r["corruption"] for r in base], "missed": [r["corruption"] for r in missed],
            "marker": marker}
