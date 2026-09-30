#!/usr/bin/env python3
"""Visual Language 1: fail-capable checks of the canonical Classroom demo package.

    .venv/bin/python tools/visual_language/check_visual_language1.py --source RUN01 --replay RUN02 \
        --cache CACHE --package PACKAGE [--corruptions]

Contract: docs/methodology/visual-language-1-contract.md, section 9 (checks 1-25).  With
``--corruptions`` it also runs the corruption / mutation suite: every planted defect (on throwaway
copies or in-process mutants; the sources and the package are never modified) must make its
targeted check fail.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import style as S  # noqa: E402
import vl1_data as D  # noqa: E402

PREFIX = "[vl1-check]"
ACCEPTED_MAIN = "1e0584b670a1de9a5e577e57804c1ab694734745"
FROZEN_FOV3D_CHECK = "fov3d"
_CACHE: dict = {}


class Paths:
    def __init__(self, source, replay, cache, package):
        self.source, self.replay, self.cache, self.package = (Path(p).resolve() for p in (source, replay, cache, package))

    def j(self, base, rel):
        return json.loads((getattr(self, base) / rel).read_text())


# ---------------------------------------------------------------- loading

def load(p: Paths) -> dict:
    ctx = {"lfm": p.j("package", "demo/logical-frame-manifest.json"), "vlm": p.j("package", "visual-language-manifest.json"),
           "render": p.j("cache", "render-manifest.json"), "extract": p.j("cache", "extract-manifest.json"),
           "events_cache": p.j("cache", "events.json"), "steps_cache": p.j("cache", "steps.json"),
           "overview": p.j("package", "overview.json"), "legend": p.j("package", "legend/visual-language-1.json")}
    ref = p.cache / "reference/reference-manifest.json"
    ctx["reference"] = json.loads(ref.read_text()) if ref.exists() else None
    fw = D.firewall()
    with fw:
        ctx["src"] = D.Sources(p.source, p.replay)
    ctx["frames"] = ctx["lfm"]["logical_frames"]
    ctx["by_id"] = {}
    for f in ctx["frames"]:
        ctx["by_id"].setdefault(f["id"], []).append(f)
    return ctx


def one(ctx, fid):
    rows = ctx["by_id"].get(fid, [])
    if len(rows) != 1:
        raise AssertionError(f"logical frame {fid}: {len(rows)} entries")
    return rows[0]


# ---------------------------------------------------------------- the checks

def c01_sources(p, ctx):
    bad = {n: D.sha(p.source / n) for n, h in D.C01_ACCEPTED.items() if D.sha(p.source / n) != h}
    return not bad, str(bad)


def c02_replay(p, ctx):
    src = ctx["src"]
    bad = {n: D.sha(p.replay / n) for n, h in D.C02_ACCEPTED.items() if D.sha(p.replay / n) != h}
    ok = not bad and src.c02_result.get("marker") == D.C02_MARKER and src.c02_manifest.get("source_hashes") == D.C01_ACCEPTED \
        and not src.c02_manifest.get("global_quiescence_claimed", True)
    return ok, f"hash mismatches {bad}; marker {src.c02_result.get('marker')}"


def c03_coverage(p, ctx):
    steps = [f for f in ctx["frames"] if f.get("kind") == "step"]
    ids = [f["global_step"] for f in steps]
    names = [f["id"] for f in steps]
    ok = ids == list(range(141)) and names == [f"step_{t:03d}" for t in range(141)] and all(
        len(ctx["by_id"][f"step_{t:03d}"]) == 1 for t in range(141))
    return ok, f"{len(ids)} step frames; first gaps {sorted(set(range(141)) - set(ids))[:5]}"


def c04_actions(p, ctx):
    src = ctx["src"]
    bad = []
    for t in range(141):
        f = one(ctx, f"step_{t:03d}")
        for a in (src.actions[t], src.c02_actions[t]):
            if (f["target_id"], f["gaze_deg"], f["action_source"]) != (a["target_id"], a["gaze_deg"], a["action_source"]):
                bad.append(t)
        if f["service_state_after"] != src.c02_actions[t]["service_states_after"][str(f["target_id"])]:
            bad.append(t)
    return not bad, f"mismatching steps {sorted(set(bad))[:8]}"


def c05_events(p, ctx):
    order = [f["id"] for f in ctx["frames"]]
    pos = {k: order.index(k) for k in order}
    need = {"bootstrap", "event_reactivation_0109", "event_defer_0210", "event_reactivation_0178", "residue",
            "event_final_residue_gate_0210", "closure"}
    if not need <= set(pos):
        return False, f"missing {sorted(need - set(pos))}"
    place = (pos["bootstrap"] < pos["step_000"] and pos["event_reactivation_0109"] == pos["step_007"] + 1
             and pos["event_defer_0210"] == pos["step_101"] + 1 and pos["event_reactivation_0178"] == pos["step_114"] + 1
             and pos["step_140"] < pos["residue"] < pos["event_final_residue_gate_0210"] < pos["closure"])
    src = ctx["src"]
    r = {e["object"]: e for e in src.c02_events if e["event"] == "natural_reactivation"}
    d = [e for e in src.c02_events if e["event"] == "deferred"]
    f109, f178, fd = one(ctx, "event_reactivation_0109"), one(ctx, "event_reactivation_0178"), one(ctx, "event_defer_0210")
    ok = place and set(r) == {109, 178} and len(d) == 1 and all(
        (f["object"], f["reactivated_after"], f["trigger"], f["quiet_since"]) ==
        (o, r[o]["global_step"], r[o]["trigger_target"], r[o]["quiet_since_step"]) for f, o in ((f109, 109), (f178, 178))) \
        and (fd["object"], fd["global_step"]) == (d[0]["object"], d[0]["global_step"]) \
        and one(ctx, "event_final_residue_gate_0210")["object"] == 210
    return ok, f"placement {place}"


def _react(ctx, obj):
    f = one(ctx, f"event_reactivation_{obj:04d}")
    e = [x for x in ctx["src"].events01 if x["event"] == "natural_reactivation" and x["object"] == obj][0]
    exp = D.EXPECTED[obj]
    cache = ctx["events_cache"][str(obj)]
    want = {"added": exp["added"], "eligible": list(exp["elig"]), "effective": list(exp["eff"]), "served": exp["served"],
            "quiet_since": exp["quiet"], "reactivated_after": exp["react"], "trigger": exp["trigger"]}
    rec = {"added": e["memory_added_since_quiet"]["points"],
           "eligible": [e["probe_before"]["cyclopean"]["eligible_cells"], e["probe_after"]["cyclopean"]["eligible_cells"]],
           "effective": [e["probe_before"]["effective_points"], e["probe_after"]["effective_points"]]}
    got = {k: f[k] for k in want}
    ok = got == want == {**want, **{k: cache[k] for k in want}} and all(rec[k] == want[k] for k in rec) \
        and f["added_by_source"] == e["memory_added_since_quiet"]["by_source_target"] == cache["added_by_source"]
    return ok, f"frame {got} vs expected {want}"


def c06_r109(p, ctx):
    return _react(ctx, 109)


def c07_r178(p, ctx):
    return _react(ctx, 178)


def c08_defer(p, ctx):
    f = one(ctx, "event_defer_0210")
    d = [e for e in ctx["src"].c02_events if e["event"] == "deferred"][0]
    s101 = one(ctx, "step_101")
    later = all("DEFERRED" in ctx["src"].c02_actions[t]["service_states_after"]["210"] for t in range(101, 141))
    ok = (f["global_step"], f["fixations"], f["local_state"], f["reason"]) == \
        (d["global_step"], d["fixations"], d["local_state"], d["reason"]) == (101, 24, "ACTIONABLE", "ordinary_budget") \
        and s101["service_state_after"] == "ACTIONABLE/DEFERRED:ordinary_budget" and later \
        and s101["panels"]["3"]["deferred_here"]
    return ok, f"{(f['global_step'], f['fixations'], f['local_state'], f['reason'])}"


def c09_gate(p, ctx):
    f = one(ctx, "event_final_residue_gate_0210")
    r0 = ctx["src"].c02_residue[0]
    c, els = r0["detail"]["counts"], r0["detail"]["elements"]
    g = D.EXPECTED["gate"]
    sums = (len(els), sum(e["in_both_cores"] for e in els), sum(e["previously_interrogated"] for e in els),
            sum(e["novel"] for e in els))
    got = (f["support"], f["in_both_cores"], f["previously_interrogated"], f["novel_service_count"])
    ok = got == sums == (c["support"], c["in_both_cores"], c["previously_interrogated"], c["novel_service_count"]) \
        == (g["support"], g["in_both_cores"], g["previously_interrogated"], g["novel_service_count"]) \
        and f["admissible"] is False and f["reason"] == r0["reason"] == g["reason"] \
        and all(abs(a - b) < 1e-9 for a, b in zip(f["gaze"], g["gaze"])) and f["final_residue_observations"] == 0
    return ok, f"frame {got}, elements {sums}"


def c10_closure(p, ctx):
    f = one(ctx, "closure")
    t = ctx["src"].c02_result["terminal"]
    g = D.EXPECTED["closure"]
    ok = (f["terminal"], f["quiet"], f["residual"], f["unlocated"], f["final_residue_observations"]) == \
        (t["type"], len(t["quiet"]), t["residual"], len(t["unlocated"]), ctx["src"].c02_result["final_residue_observations"]) \
        == (g["type"], g["quiet"], g["residual"], g["unlocated"], g["final_residue_observations"])
    return ok, f"{(f['terminal'], f['quiet'], f['residual'], f['unlocated'])}"


def _ct_opened(ctx):
    return list(ctx["extract"]["opened_source_files"]) + list(ctx["render"]["opened_source_files"])


def c11_truth(p, ctx):
    opened = _ct_opened(ctx)
    bad = [o for o in opened if D.forbidden_controller_time(str(D.PREVIEWS / o))]
    viol = ctx["extract"]["firewall_violations"] + ctx["render"]["firewall_violations"]
    live = []
    for target in (p.source / "evaluation.json", p.source / "bootstrap/evaluation_only/reachable_samples.npz",
                   D.PREVIEWS / "controller-01c-frontier-action-correspondence/audit.json"):
        fw = D.firewall()
        try:
            with fw:
                with open(target, "rb"):
                    pass
            live.append(f"not refused: {target}")
        except PermissionError:
            pass
    fw = D.firewall()
    with fw:
        with open(p.source / "manifest.json", "rb"):
            pass
    return not bad and not viol and not live, f"forbidden opened {bad[:3]}; violations {viol[:3]}; live {live}"


def c12_reference_isolated(p, ctx):
    probs = []
    # the reference product itself (resolved: a corruption mirror links binaries and copies only JSON)
    ref_file = Path(os.path.realpath(p.cache / "reference-render/reference.npz"))
    fw = D.firewall()
    try:
        with fw:
            with open(ref_file, "rb"):
                pass
        probs.append("controller-time firewall allowed a reference product")
    except (PermissionError, FileNotFoundError) as exc:
        if isinstance(exc, FileNotFoundError):
            probs.append("no reference product to test against")
    ref_opened = [o for o in _ct_opened(ctx) if D.is_reference_path(str(D.PREVIEWS / o))]
    if ref_opened:
        probs.append(f"controller-time path opened {ref_opened[:3]}")
    for f in ctx["frames"]:
        imgs = [s["image"] for s in f["stages"]]
        refimg = any(D.is_reference_path(i) for i in imgs)
        if refimg != ("REFERENCE / EVALUATION" in f.get("truth", [])):
            probs.append(f"{f['id']}: reference imagery / badge mismatch")
    for name, meta in ctx["render"]["specials"].items():
        if any(D.is_reference_path(s) for s in meta["stages"]):
            probs.append(f"controller-time special {name} uses a reference stage")
    return not probs, "; ".join(probs[:4])


def c13_badges(p, ctx):
    probs = []
    names = set(S.BADGES)
    for f in ctx["frames"]:
        truth = set(f.get("truth", []))
        if not truth <= names:
            probs.append(f"{f['id']}: undeclared badge {truth - names}")
        if f.get("kind") == "step":
            pn = f["panels"]
            if set(pn["2"]["badges"]) != {"CONTROLLER-TIME", "ORACLE INPUT"}:
                probs.append(f"{f['id']}: panel 2 badges {pn['2']['badges']}")
            if pn["3"]["badges"] != ["DERIVED"] or pn["4"]["badges"] != ["CONTROLLER-TIME"]:
                probs.append(f"{f['id']}: panel 3/4 badges")
            if ("ORACLE INPUT" in pn["1"]["badges"]) != (f["action_source"] == "oracle_seed"):
                probs.append(f"{f['id']}: panel 1 ORACLE INPUT iff seed look")
            used = set(pn["1"]["badges"]) | set(pn["2"]["badges"]) | set(pn["3"]["badges"]) | set(pn["4"]["badges"])
            if used != truth:
                probs.append(f"{f['id']}: frame truth {sorted(truth)} != panel badges {sorted(used)}")
        if "REFERENCE / EVALUATION" in truth and f.get("kind") != "reference":
            probs.append(f"{f['id']}: REFERENCE badge on a controller-time frame")
    if "ORACLE INPUT" not in one(ctx, "bootstrap")["truth"]:
        probs.append("bootstrap is not tagged ORACLE INPUT")
    return not probs, "; ".join(probs[:4])


def c14_measurements(p, ctx):
    bad = []
    for t in range(141):
        f, a = one(ctx, f"step_{t:03d}"), ctx["src"].actions[t]
        z = D.load_npz(p.cache / f"steps/step_{t:03d}.npz")
        if not (f["new_surfels"] == a["new_surfels"] == int(z["new_px"].sum()) == len(z["new_xyz"])
                == f["panels"]["4"]["new_surfels"] and f["repeated_target_measurements"] == a["nonnew_target_points"]
                == int(z["repeated_px"].sum()) == len(z["repeated_xyz"]) == f["panels"]["4"]["repeated_measurements"]
                and f["target_valid_points"] == a["target_valid_points"] == f["panels"]["2"]["target_valid_points"]):
            bad.append(t)
    return not bad, f"mismatching steps {bad[:8]}"


def _gray_distinct(keys, level=24.0, frac=0.02):
    """Pairwise: at least ``frac`` of the swatch pixels differ visibly (> ``level`` gray levels) in grayscale.

    (A mean difference over the swatch is dominated by empty background: it would pass two
    near-identical large fills and fail a clear solid-vs-dashed glyph pair.)
    """
    draw = {r[1]: r[5] for r in S.ROLES}  # the declared renderers (not a cached copy)
    arrs = {}
    for k in keys:
        img = Image.new("RGB", (120, 44), S.PANEL)
        draw[k](img, (1, 1, 118, 42))
        arrs[k] = np.asarray(img.convert("L"), np.float32)
    worst = (None, 1e9)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            dv = float(np.mean(np.abs(arrs[a] - arrs[b]) > level))
            if dv < worst[1]:
                worst = ((a, b), round(dv, 4))
    return worst[1] >= frac, worst


def c15_noncolor(p, ctx):
    probs = []
    color_words = {"blue", "green", "red", "orange", "purple", "sky", "yellow", "vermillion", "slate", "gray", "grey"}
    for g, keys in S.REQUIRED_ROLES.items():
        missing = keys - {r[1] for r in S.ROLES if r[0] == g}
        if missing:
            probs.append(f"{g}: missing roles {sorted(missing)}")
    for r in S.ROLES:
        cue = r[4].strip().lower()
        if not cue or set(cue.replace("+", " ").split()) <= color_words:
            probs.append(f"{r[1]}: no non-color cue")
    for g in S.GROUPS:
        keys = [r[1] for r in S.ROLES if r[0] == g]
        cues = [r[4] for r in S.ROLES if r[0] == g]
        if len(set(cues)) != len(cues):
            probs.append(f"{g}: two roles share a cue")
        ok, worst = _gray_distinct(keys)
        if not ok:
            probs.append(f"{g}: grayscale-indistinct swatches {worst}")
    return not probs, "; ".join(probs[:4])


def _img_ok(path, size=(2560, 1440)):
    try:
        with Image.open(path) as im:
            return im.size == size
    except (FileNotFoundError, OSError):
        return False


def c16_frames(p, ctx):
    need = ["frames/bootstrap.png", "frames/residue.png", "frames/closure.png"] + [f"frames/step_{t:03d}.png" for t in range(141)]
    bad = [n for n in need if not _img_ok(p.package / n)]
    return not bad, f"missing / wrong size {bad[:5]}"


def c17_events(p, ctx):
    need = ["events/reactivation-0109.png", "events/reactivation-0178.png", "events/defer-0210.png",
            "events/final-residue-gate-0210.png"]
    bad = [n for n in need if not _img_ok(p.package / n)]
    return not bad, f"missing / wrong size {bad}"


def _decode_small(video: Path, w=160, h=90):
    key = ("decode", D.sha(video))
    if key not in _CACHE:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
        _CACHE[key] = np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3)
    return _CACHE[key]


def _stage_small(path, package, w=160, h=90):
    full = path if os.path.isabs(path) else str(package / path)
    with Image.open(full) as im:
        return np.asarray(im.convert("RGB").resize((w, h), Image.BOX), np.float32)


def c18_timing(p, ctx):
    lfm = ctx["lfm"]
    frames = lfm["logical_frames"]
    cur, probs = 0, []
    for f in frames:
        n = sum(s["frames"] for s in f["stages"])
        if f["start_frame"] != cur or f["end_frame"] != cur + n or abs(f["start_s"] - cur / 30) > 1e-3 \
                or abs(f["end_s"] - (cur + n) / 30) > 1e-3:
            probs.append(f"{f['id']} not contiguous")
        cur += n
    if cur != lfm["total_frames"]:
        probs.append(f"total {cur} != {lfm['total_frames']}")
    vid = p.package / "demo/controller-02-classroom-full-1440p.mp4"
    dec = _decode_small(vid)
    if len(dec) != cur:
        probs.append(f"decoded {len(dec)} frames != manifest {cur}")
    stages = [(f["id"], s) for f in frames for s in f["stages"]]
    starts = np.cumsum([0] + [s["frames"] for _i, s in stages])
    imgs = [_stage_small(s["image"], p.package) for _i, s in stages]
    mism = []
    for k, ((fid, s), img) in enumerate(zip(stages, imgs)):
        mid = int(starts[k] + s["frames"] // 2)
        if mid >= len(dec):
            mism.append(fid)
            continue
        fr = dec[mid].astype(np.float32)
        own = float(np.mean((fr - img) ** 2))
        others = [float(np.mean((fr - imgs[j]) ** 2)) for j in (k - 1, k + 1) if 0 <= j < len(imgs)
                  and float(np.mean((imgs[j] - img) ** 2)) > 1.0]
        psnr = 10 * np.log10(255 ** 2 / max(own, 1e-9))
        if psnr < 28 or any(o <= own for o in others):
            mism.append(f"{fid} (psnr {psnr:.1f})")
    if mism:
        probs.append(f"video content != manifest at {mism[:4]}")
    return not probs, "; ".join(probs[:4])


def c19_videos(p, ctx):
    probs = []
    total = ctx["lfm"]["total_frames"]
    for name, size in (("controller-02-classroom-full-1440p.mp4", (2560, 1440)),
                       ("controller-02-classroom-full-1080p.mp4", (1920, 1080))):
        v = p.package / "demo" / name
        key = ("probe", D.sha(v)) if v.exists() else None
        if key is None:
            probs.append(f"{name} missing")
            continue
        if key not in _CACHE:
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-f", "null", "-"], capture_output=True, text=True)
            q = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                                "stream=width,height,r_frame_rate,nb_read_frames,codec_name", "-of", "json", str(v)],
                               capture_output=True, text=True)
            _CACHE[key] = (r.returncode, r.stderr, q.returncode, q.stdout)
        rc, err, qrc, out = _CACHE[key]
        if rc != 0 or err.strip() or qrc != 0:
            probs.append(f"{name} does not decode cleanly: {err.strip()[:100]}")
            continue
        s = json.loads(out)["streams"][0]
        if (s["width"], s["height"]) != size or s["r_frame_rate"] != "30/1" or int(s["nb_read_frames"]) != total \
                or s["codec_name"] != "h264":
            probs.append(f"{name}: {s}")
        rec = ctx["vlm"]["videos"].get(name, {})
        if rec.get("sha256") != D.sha(v):
            probs.append(f"{name}: sha256 differs from the package manifest")
    return not probs, "; ".join(probs)


def c20_legend(p, ctx):
    leg = ctx["legend"]
    ok = leg["roles"] == S.declaration() and sorted(leg["drawn_order"]) == sorted(r[1] for r in S.ROLES) \
        and leg["distinctions"] == S.DISTINCTIONS and leg["sources"] == {k: v[0] for k, v in S.SOURCES.items()}
    return ok, "legend sidecar differs from style.py"


def c21_overview(p, ctx):
    src = ctx["src"]
    n = ctx["overview"]["numbers"]
    acts = src.actions
    want = {"catalog": len(src.catalog), "localized": len(src.seeds), "unlocated": len(src.c02_result["terminal"]["unlocated"]),
            "looks": len(acts), "sources": {k: sum(1 for a in acts if a["action_source"] == k) for k in S.SOURCES},
            "switches": sum(1 for a, b in zip(acts[:-1], acts[1:]) if a["target_id"] != b["target_id"]),
            "new_surfels": sum(a["new_surfels"] for a in acts), "repeated": sum(a["nonnew_target_points"] for a in acts)}
    probs = [k for k, v in want.items() if n.get(k) != v]
    if n["catalog"] != D.EXPECTED["catalog"] or n["localized"] != D.EXPECTED["localized"] or n["unlocated"] != D.EXPECTED["unlocated"]:
        probs.append("bootstrap counts")
    for key, fid, fields in (("r109", "event_reactivation_0109", ("added", "eligible", "served")),
                             ("r178", "event_reactivation_0178", ("added", "eligible", "served")),
                             ("defer", "event_defer_0210", ("global_step", "fixations", "local_state")),
                             ("gate", "event_final_residue_gate_0210", ("gaze", "support", "in_both_cores",
                                                                         "previously_interrogated", "novel_service_count")),
                             ("closure", "closure", ("terminal", "quiet", "residual", "unlocated"))):
        f = one(ctx, fid)
        if any(n[key][k] != f[k] for k in fields):
            probs.append(key)
    if n != ctx["render"]["overview_numbers"]:
        probs.append("overview.json != render manifest")
    return not probs, f"differing {probs}"


def _ply_count(path):
    with open(path, "rb") as fh:
        head = b""
        while not head.endswith(b"end_header\n"):
            c = fh.read(1)
            if not c:
                return None
            head += c
    for line in head.decode().splitlines():
        if line.startswith("element vertex"):
            return int(line.split()[-1])
    return None


def c22_ply(p, ctx):
    probs = []
    rec = ctx["vlm"]["pointclouds"]
    src = ctx["src"]
    want = {"scene-active-maps.ply": sum(int(o["final_map_surfels"]) for o in src.manifest["objects"]),
            "scene-measurement-memory.ply": sum(sum(a["measurement_memory_additions"].values()) for a in src.actions)}
    for name, n in want.items():
        path = p.package / "pointclouds" / name
        if not path.exists():
            probs.append(f"{name} missing")
            continue
        cnt = _ply_count(path)
        key = ("sha", str(path), path.stat().st_size, path.stat().st_mtime_ns)
        if key not in _CACHE:
            _CACHE[key] = D.sha(path)
        if not (cnt == rec[name]["points"] == n == ctx["render"]["pointclouds"][name]["points"]):
            probs.append(f"{name}: count {cnt} / recorded {rec[name]['points']} / expected {n}")
        if _CACHE[key] != rec[name]["sha256"]:
            probs.append(f"{name}: sha256 differs from recorded provenance")
    return not probs, "; ".join(probs)


def c23_determinism(p, ctx):
    import generate_visual_language1 as G
    key = ("regen", D.sha(p.cache / "render-manifest.json"), *(D.sha(HERE / f) for f in
                                                                 ("style.py", "vl1_draw.py", "generate_visual_language1.py")))
    if key not in _CACHE:
        out = {}
        tmp = Path(tempfile.mkdtemp(prefix="vl1-regen-"))
        try:
            fw = D.firewall()
            with fw:
                gctx = G.Ctx(p.source, p.replay, p.cache)
                leg, _m = G.legend_image()
                leg.save(tmp / "legend.png")
                for name, fn in (("reactivation-0109", lambda: G.reactivation_stages(gctx, 109)),
                                 ("reactivation-0178", lambda: G.reactivation_stages(gctx, 178)),
                                 ("defer-0210", lambda: G.defer_stages(gctx)),
                                 ("final-residue-gate-0210", lambda: G.gate_stages(gctx))):
                    st, _m = fn()
                    st[-1].save(tmp / f"{name}.png")
            numbers = ctx["render"]["overview_numbers"]
            thumbs = {k: Image.open(p.package / v) for k, v in ctx["overview"]["thumbnails"].items()}
            G.overview_poster(gctx, thumbs, numbers).save(tmp / "overview.png")
            out = {n: D.sha(tmp / n) for n in os.listdir(tmp)}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        _CACHE[key] = out
    regen = _CACHE[key]
    pairs = {"legend.png": "legend/visual-language-1.png", "overview.png": "overview.png",
             **{f"{n}.png": f"events/{n}.png" for n in ("reactivation-0109", "reactivation-0178", "defer-0210",
                                                          "final-residue-gate-0210")}}
    bad = [pk for gk, pk in pairs.items() if not (p.package / pk).exists() or regen.get(gk) != D.sha(p.package / pk)]
    return not bad, f"not byte-identical on regeneration: {bad}"


def c24_sources_unchanged(p, ctx):
    key = ("fingerprint", str(p.source), str(p.replay))
    if key not in _CACHE:
        _CACHE[key] = {"controller-01-full": D.fingerprint(p.source), "controller-02-classroom-replay": D.fingerprint(p.replay)}
    now = _CACHE[key]
    rec = ctx["extract"]["source_fingerprint_before"]
    diff = [f"{run}/{f}" for run in now for f in set(now[run]) | set(rec.get(run, {})) if now[run].get(f) != rec.get(run, {}).get(f)]
    ok = not diff and rec == ctx["extract"]["source_fingerprint_after"] and len(now["controller-01-full"]) == 1678
    return ok, f"changed {diff[:4]}; files {len(now['controller-01-full'])}"


def c25_fov3d(p, ctx):
    r = subprocess.run(["git", "diff", "--stat", ACCEPTED_MAIN, "--", FROZEN_FOV3D_CHECK], cwd=REPO, capture_output=True, text=True)
    u = subprocess.run(["git", "status", "--porcelain", "--", FROZEN_FOV3D_CHECK], cwd=REPO, capture_output=True, text=True)
    return r.returncode == 0 and not r.stdout.strip() and not u.stdout.strip(), (r.stdout + u.stdout).strip()[:200]


CHECKS = [
    ("01", "accepted Controller-01 source hashes", c01_sources),
    ("02", "accepted Controller-02 replay marker and source identity", c02_replay),
    ("03", "141/141 actions represented exactly once", c03_coverage),
    ("04", "target / gaze / source / service state of every action equal the accepted runs", c04_actions),
    ("05", "event steps, objects and placement are correct", c05_events),
    ("06", "109 reactivation numbers", c06_r109),
    ("07", "178 reactivation numbers", c07_r178),
    ("08", "210 deferral step and state", c08_defer),
    ("09", "final-gate numbers", c09_gate),
    ("10", "closure counts", c10_closure),
    ("11", "controller-time paths opened no evaluation truth (records + live firewall control)", c11_truth),
    ("12", "reference / evaluation assets cannot feed controller-time generation", c12_reference_isolated),
    ("13", "truth badges match their data provenance", c13_badges),
    ("14", "new-surfel / repeated-measurement annotations equal the source records", c14_measurements),
    ("15", "no semantic role uses color as its only cue", c15_noncolor),
    ("16", "all required logical frames exist at 2560x1440", c16_frames),
    ("17", "all required event figures exist", c17_events),
    ("18", "MP4 logical-frame timing covers the manifest; decoded frames match their stages", c18_timing),
    ("19", "both videos decode fully with the expected size, frame rate and frame count", c19_videos),
    ("20", "legend semantics equal the style definition", c20_legend),
    ("21", "overview annotations equal the manifest and the records", c21_overview),
    ("22", "PLY point counts and hashes equal the recorded provenance", c22_ply),
    ("23", "overview, legend and event PNGs regenerate byte-identically", c23_determinism),
    ("24", "the source runs are byte-identical", c24_sources_unchanged),
    ("25", "no controller / fov3d scientific behavior changed", c25_fov3d),
]


def run_checks(p: Paths, only=None, quiet=False) -> list[dict]:
    try:
        ctx = load(p)
    except Exception as exc:  # a broken package fails every check rather than crashing
        ctx = exc
    results = []
    for num, name, fn in CHECKS:
        if only is not None and num not in only:
            continue
        try:
            if isinstance(ctx, Exception):
                raise ctx
            ok, detail = fn(p, ctx)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append({"check": num, "name": name, "ok": bool(ok), "detail": "" if ok else str(detail)})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}{'' if ok else ': ' + str(detail)}", flush=True)
    return results


# ---------------------------------------------------------------- corruption / mutation suite

def mirror(p: Paths, work: Path) -> Paths:
    """Throwaway mirror: JSON files copied, everything else symlinked (the originals are never touched)."""
    if work.exists():
        shutil.rmtree(work)
    for base in ("replay", "cache", "package"):
        root = getattr(p, base)
        dst = work / base
        for dirpath, _dirs, files in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            (dst / rel).mkdir(parents=True, exist_ok=True)
            for f in files:
                s = Path(dirpath) / f
                if f.endswith(".json"):
                    shutil.copyfile(s, dst / rel / f)
                else:
                    os.symlink(s, dst / rel / f)
    return Paths(p.source, work / "replay", work / "cache", work / "package")


def edit_json(path: Path, fn):
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def _lf(d, fid):
    return next(f for f in d["logical_frames"] if f["id"] == fid)


def _replace_file(path: Path, data: bytes):
    path.unlink()
    path.write_bytes(data)


@contextlib.contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def corruption_suite(p: Paths, base: Path) -> tuple[int, int, list]:
    lfm = "package/demo/logical-frame-manifest.json"
    C = []

    def add(label, target, prep=None, ctxmgr=None):
        C.append((label, target, prep, ctxmgr))
    add("Controller-01 accepted hash constant wrong (mutant)", "01",
        ctxmgr=lambda: patched(D, "C01_ACCEPTED", {**D.C01_ACCEPTED, "manifest.json": "0" * 64}))
    add("Controller-02 result marker NOT_CLOSED (copy)", "02",
        lambda m: edit_json(m / "replay/result.json", lambda d: d.update(marker="CONTROLLER02_CLASSROOM_NOT_CLOSED")))
    add("step_050 missing from the logical frames", "03",
        lambda m: edit_json(m / lfm, lambda d: d.update(logical_frames=[f for f in d["logical_frames"] if f["id"] != "step_050"])))
    add("step_060 duplicated", "03",
        lambda m: edit_json(m / lfm, lambda d: d["logical_frames"].insert(5, copy.deepcopy(_lf(d, "step_060")))))
    add("a step's gaze altered", "04", lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_033").update(gaze_deg=[0.0, 0.0])))
    add("a step's target altered", "04", lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_090").update(target_id=111)))
    add("210 deferral placed after step 102", "05", lambda m: edit_json(m / lfm, lambda d: _move(d, "event_defer_0210", "step_102")))
    add("109 cross-target points 4 -> 5", "06", lambda m: edit_json(m / lfm, lambda d: _lf(d, "event_reactivation_0109").update(added=5)))
    add("178 eligible after 189 -> 190", "07",
        lambda m: edit_json(m / lfm, lambda d: _lf(d, "event_reactivation_0178").update(eligible=[0, 190])))
    add("210 deferral step 101 -> 100", "08", lambda m: edit_json(m / lfm, lambda d: _lf(d, "event_defer_0210").update(global_step=100)))
    add("gate: support in both cores 0 -> 1", "09",
        lambda m: edit_json(m / lfm, lambda d: _lf(d, "event_final_residue_gate_0210").update(in_both_cores=1)))
    add("closure: quiet 24 -> 25", "10", lambda m: edit_json(m / lfm, lambda d: _lf(d, "closure").update(quiet=25)))
    add("evaluation truth in the extraction's opened files", "11",
        lambda m: edit_json(m / "cache/extract-manifest.json",
                            lambda d: d["opened_source_files"].append("controller-01-full/evaluation.json")))
    add("firewall predicate no longer refuses evaluation truth (mutant)", "11",
        ctxmgr=lambda: patched(D.c01, "is_evaluation_truth", lambda path: False))
    add("firewall predicate no longer refuses reference products (mutant)", "12",
        ctxmgr=lambda: patched(D, "is_reference_path", lambda path: False))
    add("a reference stage inside a controller-time special", "12",
        lambda m: edit_json(m / "cache/render-manifest.json", lambda d: d["specials"]["closure"]["stages"].append(
            str(p.cache / "reference/outro_reference_0.png"))))
    add("panel 2 of a step loses ORACLE INPUT", "13",
        lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_012")["panels"]["2"].update(badges=["CONTROLLER-TIME"])))
    add("REFERENCE badge on a controller-time step", "13",
        lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_070")["truth"].append("REFERENCE / EVALUATION")))
    add("a step's new surfels altered", "14", lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_044").update(new_surfels=1)))
    add("a role loses its non-color cue (mutant)", "15",
        ctxmgr=lambda: patched(S, "ROLES", [r if r[1] != "deferred" else r[:4] + ("",) + r[5:] for r in S.ROLES]))
    add("DEFERRED drawn exactly like QUIET (mutant)", "15",
        ctxmgr=lambda: patched(S, "ROLES", [r if r[1] != "deferred" else r[:5] + (S.ROLE["quiet"]["swatch"],) for r in S.ROLES]))
    add("frame step_099 missing", "16", lambda m: (m / "package/frames/step_099.png").unlink())
    add("event figure defer-0210 missing", "17", lambda m: (m / "package/events/defer-0210.png").unlink())
    add("a logical frame's start shifted by one frame", "18",
        lambda m: edit_json(m / lfm, lambda d: _lf(d, "step_080").update(start_frame=_lf(d, "step_080")["start_frame"] + 1)))
    add("two frame images swapped", "18", lambda m: _swap(m / "package/frames/step_010.png", m / "package/frames/step_011.png"))
    add("1080p video truncated", "19", lambda m: _truncate(m / "package/demo/controller-02-classroom-full-1080p.mp4"))
    add("legend sidecar role label altered", "20",
        lambda m: edit_json(m / "package/legend/visual-language-1.json", lambda d: d["roles"][0].update(label="x")))
    add("overview number altered", "21", lambda m: edit_json(m / "package/overview.json",
                                                              lambda d: d["numbers"].update(switches=25)))
    add("PLY recorded count wrong", "22", lambda m: edit_json(m / "package/visual-language-manifest.json",
                                                               lambda d: d["pointclouds"]["scene-active-maps.ply"].update(points=1)))
    add("PLY byte flipped", "22", lambda m: _flip(m / "package/pointclouds/scene-active-maps.ply"))
    add("legend PNG pixel altered", "23", lambda m: _png_pixel(m / "package/legend/visual-language-1.png"))
    add("recorded source fingerprint differs", "24",
        lambda m: edit_json(m / "cache/extract-manifest.json", lambda d: d["source_fingerprint_before"]["controller-01-full"].update(
            {"manifest.json": "0" * 64})))
    add("a fov3d file edited (worktree; restored)", "25", ctxmgr=lambda: _fov3d_edit())
    caught, rows = 0, []
    for label, target, prep, cm in C:
        m = mirror(p, base / "mirror")
        if prep:
            prep(base / "mirror")
        with (cm() if cm else contextlib.nullcontext()):
            res = run_checks(m, only=None, quiet=True)
        fails = [r["check"] for r in res if not r["ok"]]
        ok = target in fails
        caught += ok
        rows.append({"corruption": label, "target": target, "caught": ok, "failed_checks": fails})
        print(f"{PREFIX} {'CAUGHT' if ok else 'MISSED'} [{target}] {label}: failed {fails}", flush=True)
    shutil.rmtree(base / "mirror", ignore_errors=True)
    return caught, len(C), rows


def _move(d, fid, after):
    fr = d["logical_frames"]
    item = next(f for f in fr if f["id"] == fid)
    fr.remove(item)
    fr.insert(next(k for k, f in enumerate(fr) if f["id"] == after) + 1, item)


def _swap(a: Path, b: Path):
    ta, tb = os.readlink(a), os.readlink(b)
    a.unlink(); b.unlink()
    os.symlink(tb, a); os.symlink(ta, b)


def _truncate(v: Path):
    data = Path(os.readlink(v)).read_bytes()
    _replace_file(v, data[: len(data) // 2])


def _flip(path: Path):
    data = bytearray(Path(os.readlink(path)).read_bytes())
    data[len(data) // 2] ^= 1
    _replace_file(path, bytes(data))


def _png_pixel(path: Path):
    im = Image.open(os.readlink(path)).convert("RGB")
    px = im.load()
    r, g, b = px[5, 5]
    px[5, 5] = (255 - r, g, b)
    path.unlink()
    im.save(path)


@contextlib.contextmanager
def _fov3d_edit():
    f = REPO / "fov3d/scene/sphere.py"
    old = f.read_bytes()
    f.write_bytes(old + b"\n# mutant\n")
    try:
        yield
    finally:
        f.write_bytes(old)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("source", "replay", "cache", "package"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--report", type=Path, default=None, help="write the results as JSON here")
    a = ap.parse_args()
    p = Paths(a.source, a.replay, a.cache, a.package)
    res = run_checks(p)
    failed = [r for r in res if not r["ok"]]
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(failed)}")
    out = {"checks": res}
    rc = 0 if not failed else 1
    if not failed:
        print(f"{PREFIX} VISUAL_LANGUAGE_1_CHECKS_PASS")
    if a.corruptions:
        with tempfile.TemporaryDirectory(prefix="vl1-corrupt-") as tmp:
            caught, n, rows = corruption_suite(p, Path(tmp))
        print(f"{PREFIX} corruptions caught {caught}/{n}")
        out["corruptions"] = {"caught": caught, "total": n, "rows": rows}
        rc = rc or (0 if caught == n else 1)
    if a.report:
        a.report.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
