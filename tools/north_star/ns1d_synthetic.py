"""North Star-1d: synthetic known answers for the measurement-memory mechanism (contract section 10).

Exact fixtures, each with a negative control showing the assertion can fail: the accepted ``InstanceMeasurementMemory``
routing, snapshots, duplicates and ``effective_target_geometry`` order; the M0 / M1 / M2 revisions and geometries; map
and own-look context separation; cache invalidation and natural reactivation through the accepted adapter (no manual
call); the sparse spherical raster; memory identity vs scheduler identity; append-once; provenance; the process guard;
the causal replay driver stopping before a counterfactual observation.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1d_core as K  # noqa: E402
import ns1d_spec as SP  # noqa: E402
from fov3d.reconstruction.measurement_memory import (  # noqa: E402  (accepted, unchanged)
    InstanceMeasurementMemory, MeasurementSnapshot, effective_target_geometry)

NAN = np.nan


def raster(cells: dict, size: int = 4) -> dict:
    """{(r, c): (xyz, id, valid)} -> an accepted-format patch."""
    xyz = np.full((size, size, 3), NAN, np.float32)
    ids = np.zeros((size, size), np.int32)
    val = np.zeros((size, size), bool)
    for (r, c), (p, i, v) in cells.items():
        xyz[r, c] = p
        ids[r, c] = i
        val[r, c] = v
    return {"xyz_h": xyz, "instance_id": ids, "valid": val}


def P(x):
    return np.array([x, 0.0, -1.0], np.float32)


BASE_PATCH = {(0, 0): (P(0.1), 3, True), (0, 1): (P(0.2), 3, True), (1, 0): (P(0.3), 3, True),
              (1, 1): (P(0.4), 3, True), (2, 0): (P(0.5), 5, True), (2, 1): (P(0.6), 5, True),
              (3, 0): (P(0.7), 0, True), (3, 1): (P(NAN), 3, True), (3, 3): (P(0.9), 7, False)}


class Fixture:
    """A tiny scene: entity records with H0 maps on disk (``run:`` refs), as the replay uses them."""

    def __init__(self) -> None:
        self.td = tempfile.TemporaryDirectory(prefix="ns1d-synthetic-")
        self.run = Path(self.td.name)
        self.recs = {}
        for i, n in ((3, 5), (5, 3), (9, 2)):
            xyz = np.column_stack([np.linspace(0, 1, n), np.full(n, float(i)), np.full(n, -2.0)]).astype(np.float64)
            np.savez_compressed(self.run / f"map-{i}.npz", xyz_h=xyz)
            self.recs[i] = {"temporary_entity_id": i, "own_looks": 1, "map": {"path": f"run:map-{i}.npz",
                                                                              "surfels": n},
                            "looks": [{"calibration": "run:c.json", "state": "run:s.npz"}], "visited": [[0.0, 0.0]],
                            "current_local_gaze": [0.0, 0.0], "evidence": {"path": "run:e.npz"},
                            "initialization_rank": 1, "chart_id": f"C_{i}", "chart_sha256": "x"}

    def close(self) -> None:
        self.td.cleanup()


def cross_patch(target: int, cells: dict) -> dict:
    return raster(cells)


# ------------------------------------------------------------------ tests
def t01_multi_id_counts():
    led = K.MemoryLedger()
    add = led.append(0, "obs-0", raster(BASE_PATCH), 3)
    neg = {3: 6}            # routing every sample by the ACTIVE target would give this
    return add == {3: 4, 5: 2} and add != neg and led.measured_points == {3: 4, 5: 2}, {"additions": add}


def t02_snapshot_aligned():
    led = K.MemoryLedger()
    led.append(0, "obs-0", raster(BASE_PATCH), 3)
    led.append(1, "obs-1", raster({(0, 0): (P(1.0), 5, True), (0, 1): (P(1.1), 3, True)}), 9)
    s = led.snapshot(5)
    aligned = len(s.xyz_h) == len(s.source_global_index) == len(s.source_active_target_id) == 3
    vals = s.source_global_index.tolist() == [0, 0, 1] and s.source_active_target_id.tolist() == [3, 3, 9]
    try:
        MeasurementSnapshot(np.zeros((3, 3), np.float32), np.zeros(2, np.int32), np.zeros(3, np.int32))
        neg = False
    except ValueError:
        neg = True
    return aligned and vals and neg, {"gi": s.source_global_index.tolist(), "at": s.source_active_target_id.tolist()}


def t03_duplicates_retained():
    led = K.MemoryLedger()
    p = raster(BASE_PATCH)
    led.append(0, "obs-0", p, 3)
    led.append(1, "obs-1", p, 3)          # the same content, a different physical observation
    s = led.snapshot(3)
    dedup = np.unique(s.xyz_h, axis=0)
    return len(s.xyz_h) == 8 and len(dedup) == 4, {"points": int(len(s.xyz_h)), "unique": int(len(dedup))}


def t04_effective_order():
    m = np.array([[0.0, 0.0, -1.0], [1.0, 0.0, -1.0]])
    q = np.array([[5.0, 5.0, -5.0]], np.float32)
    eff = effective_target_geometry(m, q)
    ok = np.array_equal(eff[:2], m) and np.array_equal(eff[2:], q.astype(np.float64)) and len(eff) == 3
    neg = np.array_equal(np.vstack((q, m))[:2], m)
    return ok and not neg, {"rows": int(len(eff))}


def _cross_setup():
    fx = Fixture()
    led = K.MemoryLedger()
    before = {m: K.revision(m, fx.recs[5], led) for m in SP.MODES}
    geo_before = {m: len(K.geometry(m, fx.recs[5], fx.run, led)) for m in SP.MODES}
    map_sha = K.sha256_bytes((fx.run / "map-5.npz").read_bytes())
    ctx_before = copy.deepcopy(fx.recs[5])
    # an observation whose ACTIVE target is 3 also measures entity 5 (cross-target)
    led.append(0, "obs-0", raster(BASE_PATCH), 3)
    return fx, led, before, geo_before, map_sha, ctx_before


def t05_cross_changes_m2_revision():
    fx, led, before, _g, _s, _c = _cross_setup()
    after = {m: K.revision(m, fx.recs[5], led) for m in SP.MODES}
    fx.close()
    return after["M2"] != before["M2"] and after["M2"] == [1, 2] and after["M0"] == before["M0"], \
        {"before": before, "after": after}


def t06_cross_not_in_map():
    fx, led, _b, _g, map_sha, _c = _cross_setup()
    same = K.sha256_bytes((fx.run / "map-5.npz").read_bytes()) == map_sha
    m0 = len(K.geometry("M0", fx.recs[5], fx.run, led))
    # negative control: fusing the cross-target samples into the map would change it
    xyz = np.load(fx.run / "map-5.npz")["xyz_h"]
    fused = np.vstack((xyz, led.snapshot(5).xyz_h.astype(np.float64)))
    fx.close()
    return same and m0 == 3 and len(fused) != 3, {"map_points": m0}


def t07_cross_not_in_context():
    fx, _led, _b, _g, _s, ctx_before = _cross_setup()
    same = fx.recs[5] == ctx_before
    mutant = copy.deepcopy(fx.recs[5])
    mutant["visited"].append([1.0, 2.0])
    fx.close()
    return same and mutant != ctx_before, {}


def t08_m1_ignores_cross():
    fx, led, before, geo_before, _s, _c = _cross_setup()
    r1 = K.revision("M1", fx.recs[5], led)
    g1 = len(K.geometry("M1", fx.recs[5], fx.run, led))
    g2 = len(K.geometry("M2", fx.recs[5], fx.run, led))
    fx.close()
    return r1 == before["M1"] and g1 == geo_before["M1"] and g2 != g1, {"M1": [r1, g1], "M2_points": g2}


def t09_m2_includes_cross():
    fx, led, _b, geo_before, _s, _c = _cross_setup()
    g2 = K.geometry("M2", fx.recs[5], fx.run, led)
    m = np.load(fx.run / "map-5.npz")["xyz_h"]
    fx.close()
    ok = len(g2) == geo_before["M2"] + 2 and np.array_equal(g2[:3], m)
    return ok and len(g2) != geo_before["M1"], {"M2_points": int(len(g2))}


def _stub_machine(fx, led, mode, calls, threshold=None):
    """The accepted adapter over entities {3, 5} with stub probes: entity i is ACTIONABLE iff its mode geometry has
    at least ``threshold[i]`` points (otherwise QUIET); every probe call is counted."""
    import ns1c2_phase as PH
    from fov3d.control import integrated as ic
    from fov3d.experiments.classroom_oracle import controller01 as c01
    v, f = c01.VERGENCE, c01.FOCUS
    threshold = threshold or {3: 0, 5: 0}

    def probe(i):
        calls[i] = calls.get(i, 0) + 1
        n = len(K.geometry(mode, fx.recs[i], fx.run, led))
        if n >= threshold[i]:
            return ic.ProbeResult(ic.Observe(i, (float(i), 0.0), v, f, "cyclopean_epistemic"), {"points": n})
        return ic.ProbeResult(None, {"points": n})
    rev = lambda i: K.revision(mode, fx.recs[i], led)  # noqa: E731
    m = PH.SceneMachine([3, 5], budget=24, vergence=v, focus=f)
    quiet = K.resume_scene(m, {3: 1, 5: 1}, current=3, bout=1, step=0, probe=probe, revision=rev)
    return m, probe, rev, quiet


def t10_cache_invalidation():
    from fov3d.control import integrated as ic
    fx = Fixture()
    led = K.MemoryLedger()
    res = {}
    for mode in ("M1", "M2"):
        fx2 = Fixture()
        led2 = K.MemoryLedger()
        calls = {}
        m, probe, rev, _q = _stub_machine(fx2, led2, mode, calls)
        plan = m.decide(K.refuse_gate)
        led2.append(0, "obs-0", raster(BASE_PATCH), 3)       # target 3's look also measures 5
        fx2.recs[3]["own_looks"] += 1
        before = dict(calls)
        m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, rev)
        res[mode] = {"probe_calls_5": [before.get(5, 0), calls.get(5, 0)], "hits": m.hits}
        fx2.close()
    fx.close()
    ok = res["M2"]["probe_calls_5"][1] == res["M2"]["probe_calls_5"][0] + 1 and \
        res["M1"]["probe_calls_5"][1] == res["M1"]["probe_calls_5"][0]
    return ok, res


def t11_reactivation_through_refresh_only():
    from fov3d.control import integrated as ic
    out = {}
    for label, append in (("with_cross", True), ("without_cross", False)):
        fx = Fixture()
        led = K.MemoryLedger()
        calls = {}
        m, probe, rev, quiet = _stub_machine(fx, led, "M2", calls, threshold={3: 0, 5: 5})
        events = []
        m.on_event = events.append
        plan = m.decide(K.refuse_gate)
        if append:
            led.append(0, "obs-0", raster(BASE_PATCH), 3)
        fx.recs[3]["own_looks"] += 1
        m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, rev)
        out[label] = {"quiet_at_resume": quiet, "events": [[e["event"], e["object"], e.get("trigger_target")]
                                                           for e in events]}
        fx.close()
    import re
    scan = []
    for name in ("ns1d_core.py", "ns1d_run.py"):
        src = (HERE / name).read_text()
        for pat in (r"\breactivate\(", r"reactivated_since_attended\.add\(",
                    r"\.(statuses|recorded|last_probe|disposition)\[[^\]]*\]\s*=(?!=)"):
            scan += [f"{name}: {m.group(0)}" for m in re.finditer(pat, src)]
    ok = (out["with_cross"]["quiet_at_resume"] == [5] and out["with_cross"]["events"] == [["natural_reactivation", 5, 3]]
          and out["without_cross"]["events"] == [] and not scan)
    return ok, {**out, "code_scan": scan}


def t12_historical_109_pattern():
    """The accepted 109 pattern at its literal numbers: own looks 3 unchanged, 4 samples of 109 measured while 110 was
    active at global step 7 change the M2 revision only (the real replay runs in ``known-answer``)."""
    led = K.MemoryLedger()
    h = SP.HISTORICAL_109
    own = {(r, c): (P(0.01 * (r * 4 + c)), 109, True) for r in range(2) for c in range(4)}
    for e in range(7):
        led.append(e, f"obs-{e}", raster(own if e in (2, 3, 4) else {}), 109 if e in (2, 3, 4) else 108)
    rec = {"temporary_entity_id": 109, "own_looks": h["own_looks"], "map": {"surfels": 10}}
    before = K.revision("M2", rec, led), K.revision("M1", rec, led)
    cross = {(0, c): (P(0.5 + 0.01 * c), 109, True) for c in range(4)}
    cross[(1, 0)] = (P(0.9), 110, True)
    led.append(7, "obs-7", raster(cross), h["trigger"])
    after = K.revision("M2", rec, led), K.revision("M1", rec, led)
    prov = led.provenance(109)
    ok = (after[0][1] - before[0][1] == h["cross_points_added"] and after[1] == before[1]
          and prov["by_source_target"].get(str(h["trigger"])) == h["cross_points_added"]
          and prov["by_source_event"].get("7") == h["cross_points_added"])
    return ok, {"before": before, "after": after, "provenance": prov}


def _product(cells, size=4):
    """A synthetic truth-stripped product + geometry + identity (left_core_row/col, P_epi, valid_epi, ids)."""
    rows = np.array([c[0] for c in cells], np.int32)
    cols = np.array([c[1] for c in cells], np.int32)
    p = np.array([c[2] for c in cells], np.float64)
    valid = np.array([c[3] for c in cells], bool)
    ids = np.array([c[4] for c in cells], np.int32)
    prod = {"left_core_row": rows, "left_core_col": cols}
    geom = {"left_core_row": rows, "left_core_col": cols, "P_epi": p, "valid_epi": valid}
    ident = {"left_core_row": rows, "left_core_col": cols, "temporary_entity_id": ids, "valid": valid}
    return prod, geom, ident


CELLS = [(0, 0, [0.1, 0, -1], True, 172), (0, 1, [0.2, 0, -1], True, 110), (1, 0, [0.3, 0, -1], True, 999),
         (1, 1, [NAN, 0, -1], True, 172), (2, 2, [0.5, 0, -1], False, -1), (3, 3, [0.6, 0, -1], True, 0)]


def t13_raster_valid_count():
    prod, geom, ident = _product(CELLS)
    patch, info = K.memory_patch(prod, geom, ident, size=4)
    neg = []
    for mut in ("duplicate_cell", "misaligned", "bad_identity"):
        p2, g2, i2 = _product(CELLS)
        if mut == "duplicate_cell":
            for d in (p2, g2, i2):
                d["left_core_row"] = d["left_core_row"].copy()
                d["left_core_col"] = d["left_core_col"].copy()
                d["left_core_row"][1], d["left_core_col"][1] = 0, 0
        elif mut == "misaligned":
            i2["left_core_col"] = i2["left_core_col"][::-1].copy()
        else:
            i2["temporary_entity_id"] = i2["temporary_entity_id"].copy()
            i2["temporary_entity_id"][4] = 7          # an id where the geometry is invalid
        try:
            K.memory_patch(p2, g2, i2, size=4)
            neg.append(False)
        except K.PatchRefused:
            neg.append(True)
    ok = int(patch["valid"].sum()) == 3 == info["valid_samples"] and all(neg)
    return ok, {"info": {k: v for k, v in info.items() if k != "digest"}, "refusals": neg}


def t14_zero_and_minus_one_excluded():
    prod, geom, ident = _product(CELLS)
    patch, info = K.memory_patch(prod, geom, ident, size=4)
    led = K.MemoryLedger()
    add = led.append(0, "obs-0", patch, 172)
    ok = (0 not in add and -1 not in add and not patch["valid"][3, 3] and not patch["valid"][2, 2]
          and patch["instance_id"][2, 2] == 0 and info["instance_zero"] == 1 and info["invalid_minus_one"] == 1)
    neg = int((np.asarray(ident["temporary_entity_id"]) >= 0).sum()) != int(patch["valid"].sum())
    return ok and neg, {"additions": add}


def t15_all_positive_ids_retained():
    prod, geom, ident = _product(CELLS)
    patch, _ = K.memory_patch(prod, geom, ident, size=4)
    led = K.MemoryLedger()
    led.append(0, "obs-0", patch, 172)
    ids = list(led.memory.instance_ids())
    filtered = [i for i in ids if i in SP.COHERENT]
    return ids == [110, 172, 999] and filtered != ids, {"memory_ids": ids}


def t16_ambiguous_never_scheduled():
    from fov3d.experiments.classroom_oracle import controller01 as c01  # noqa: F401
    led = K.MemoryLedger()
    prod, geom, ident = _product(CELLS)
    led.append(0, "obs-0", K.memory_patch(prod, geom, ident, size=4)[0], 172)
    act = {"source": "cyclopean_epistemic", "local_gaze_deg": [1.0, 2.0], "world_gaze_deg": [3.0, 4.0]}
    probes = {172: {"proposal": None}, 202: {"proposal": act}, 110: {"proposal": act}}
    d, labels = K.stateless_decision(172, [172, 202], probes, {172: 2, 202: 1}, 24)
    d_bad, _ = K.stateless_decision(172, [110, 172, 202], probes, {110: 1, 172: 2, 202: 1}, 24)
    neg_probes = {172: {"proposal": None}, 202: {"proposal": None}, 110: {"proposal": act}}
    d_neg, _ = K.stateless_decision(172, [110, 172, 202], neg_probes, {110: 1, 172: 2, 202: 1}, 24)
    ok = 110 in led.memory.instance_ids() and d["target"] == 202 and all(r[0] != 110 for r in labels) \
        and d_bad["target"] == 202 and d_neg["target"] == 110      # an id in the scheduler input could be selected
    return ok, {"decision": d, "labels": labels}


def t17_append_once():
    led = K.MemoryLedger()
    p = raster(BASE_PATCH)
    led.append(0, "obs-0", p, 3)
    refusals = []
    for args in ((1, "obs-0", p, 3), (3, "obs-3", p, 3), (1, "obs-1", p, 0)):
        try:
            led.append(*args)
            refusals.append(False)
        except K.LedgerRefused:
            refusals.append(True)
    led.append(1, "obs-1", p, 3)
    return all(refusals) and len(led.events) == 2, {"refusals": refusals}


def t18_provenance_target():
    led = K.MemoryLedger()
    led.append(0, "obs-0", raster(BASE_PATCH), 3)
    led.append(1, "obs-1", raster({(0, 0): (P(1.0), 5, True)}), 9)
    s = led.snapshot(5)
    ok = s.source_active_target_id.tolist() == [3, 3, 9] and s.source_global_index.tolist() == [0, 0, 1]
    neg = s.source_active_target_id.tolist() != [5, 5, 5]      # routing provenance by the observed id would give this
    return ok and neg, {"at": s.source_active_target_id.tolist()}


def t19_process_guard():
    from fov3d.experiments.classroom_oracle.controller02 import NoProcessGuard
    active = NoProcessGuard._active
    guard = active if active is not None else NoProcessGuard()
    n0 = len(guard.attempts)
    refused = False
    try:
        if active is None:
            with guard:
                subprocess.run(["blender", "-b", "--version"], capture_output=True)
        else:
            subprocess.run(["blender", "-b", "--version"], capture_output=True)
    except PermissionError:
        refused = True
    return refused and len(guard.attempts) == n0 + 1, {"attempt": guard.attempts[-1:] if guard.attempts else []}


def t20_drive_stops_before_counterfactual():
    acc = {k: {"kind": "attend", "target": 172, "decision": "retain", "source": "fsg6f",
               "local_gaze_deg": [float(k), 0.0], "world_gaze_deg": [10.0 + k, 0.0]} for k in range(5)}
    consumed, finals = [], []

    def run(div_at):
        consumed.clear()
        finals.clear()
        mine = {k: (dict(acc[k], local_gaze_deg=[float(k) + 1e-12, 0.0]) if k == div_at else acc[k]) for k in acc}
        return K.drive(5, lambda k: mine[k], lambda k: acc[k], consumed.append, lambda: finals.append(1))
    r = run(2)
    stop_ok = r["divergence"] and r["step"] == 2 and consumed == [0, 1] and not finals \
        and r["differences"] == ["local_gaze_deg"]
    r2 = run(None)
    full_ok = not r2["divergence"] and consumed == [0, 1, 2, 3, 4] and finals == [1]
    return stop_ok and full_ok, {"stop": {k: r[k] for k in ("step", "differences", "consumed_steps")}}


TESTS = {"01_multi_id_counts": t01_multi_id_counts, "02_snapshot_aligned": t02_snapshot_aligned,
         "03_duplicates_retained": t03_duplicates_retained, "04_effective_order_map_first": t04_effective_order,
         "05_cross_changes_m2_revision": t05_cross_changes_m2_revision, "06_cross_not_in_map": t06_cross_not_in_map,
         "07_cross_not_in_own_look_context": t07_cross_not_in_context, "08_m1_ignores_cross": t08_m1_ignores_cross,
         "09_m2_includes_cross": t09_m2_includes_cross, "10_cache_invalidation": t10_cache_invalidation,
         "11_reactivation_through_refresh_only": t11_reactivation_through_refresh_only,
         "12_historical_109_pattern": t12_historical_109_pattern, "13_raster_valid_count": t13_raster_valid_count,
         "14_zero_and_minus_one_excluded": t14_zero_and_minus_one_excluded,
         "15_all_positive_ids_retained": t15_all_positive_ids_retained,
         "16_ambiguous_never_scheduled": t16_ambiguous_never_scheduled, "17_append_once": t17_append_once,
         "18_provenance_active_target": t18_provenance_target, "19_process_guard_refuses_blender": t19_process_guard,
         "20_drive_stops_before_counterfactual": t20_drive_stops_before_counterfactual}


def run_all() -> dict:
    res = {}
    for k, fn in TESTS.items():
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001  (a crash is a failure of that test)
            ok, detail = False, {"error": repr(exc)}
        res[k] = {"pass": bool(ok), "detail": K.jsonable(detail)}
    failed = [k for k, v in res.items() if not v["pass"]]
    return {"schema": "NS1d-synthetic-v1", "truth": SP.TRUTH_DERIVED, "tests": res, "failed": failed,
            "count": len(res), "marker": "NS1D_SYNTHETIC_PASS" if not failed else "NS1D_SYNTHETIC_FAIL"}


if __name__ == "__main__":
    r = run_all()
    for k, v in r["tests"].items():
        print(f"[ns1d-synthetic] {'PASS' if v['pass'] else 'FAIL'} {k}")
    print(f"[ns1d-synthetic] {r['marker']} {r['count'] - len(r['failed'])}/{r['count']}")
    print(json.dumps({k: v["detail"] for k, v in r["tests"].items() if not v["pass"]}, default=str)[:4000])
