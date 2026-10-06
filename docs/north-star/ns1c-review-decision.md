# North Star-1c — review decision

**Status: DECISION (Luiz and Chat), recorded by Claude Code. Not an experiment.**

    NS1c:  REVIEWED · NOT ACCEPTED · NOT MERGED

- Branch `north-star/ns1c-coherent-first-scene-switch` stays at its report head
  `4107be86228c970f4b82fb6d5343365c551f36b0`. It is preserved unchanged. It is not rewritten and not merged into `main`.
- NS1c has no ACCEPTED marker. Its completion marker `NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_COMPLETE` records only
  that the run completed.
- The NS1c run `previews/north-star/ns1c-coherent-first-scene-switch/` is retained as **diagnostic evidence**.
- NS1c is **not** a failed implementation. Its tools faithfully implemented its committed contract. The error was in the
  experiment design / mandate that the contract encoded.

## 1. What NS1c measured correctly (retained)

MEASURED in the NS1c run (contract `cb2217d`, implementation `f339598`, report `4107be8`; source: the NS1c report and its
run records). These measurements stay valid:

- The coherent seed set was derived correctly: {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}; 10, 110 and 178 were
  deferred by the single-patch rule.
- The policy charts were valid (two numeric charts; the rank-6 chart is bitwise the accepted NS1b chart).
- The NS1b state was imported exactly. The initial probe of 172 reproduced the accepted NS1b post-action probe with
  0 differences.
- The first four post-NS1b actions on 172 (global steps 0–3) were valid fixed-head North-Star observations: 4096 spp,
  PERFECT correspondence, spherical geometry, target-only 12-mm fusion in canonical H0. Each was an accepted ordinary
  FSG6f proposal, and the final-look gate v1 admitted each of them.
- 172 grew from 21,243 to 45,267 surfels.
- The scheduler mechanics switched to 123 under the service states NS1c supplied (global step 4).
- One action on 123 grew its map from 1,672 to 6,194 surfels.
- The fixed-head, perfect-correspondence, spherical-geometry and H0-fusion invariants held. The checks passed
  (27/27; corruptions 45/45).

## 2. Why NS1c is not accepted as Outcome 1

**Review finding.** The NS1c contract (section 12, from the mandate's B8) applied `final_look_gate_v1` to **every**
ordinary local probe. That is not the accepted Controller-02 semantics.

Accepted Controller-02 (`fov3d/control/controller02.py`; `docs/controller/controller-02-residual-closure-report.md`):

- **NORMAL phase.** The local states and the retain/switch order are Controller-01's. An object is ACTIONABLE whenever
  its ProbeResult carries an action, whether the source is `fsg6f` or `cyclopean_epistemic`. `final_look_gate_v1` is
  **not** called.
- An ACTIONABLE object at the ordinary budget becomes **DEFERRED** (`ordinary_budget`).
- **RESIDUE phase.** It begins only when no NORMAL object needs service. For an ACTIONABLE DEFERRED object, the
  unchanged proposal goes to `final_look_gate_v1`. At most one final residue observation may execute.

Consequences in NS1c:

- Eight coherent seeds were labelled QUIET because the gate rejected their valid Cyclopean proposals as
  `untraceable_final_support`. Under NORMAL semantics those proposals mean **ACTIONABLE**.
- After NS1c step 3, 172 had FSG6f `no_frontier` and a valid Cyclopean proposal. NS1c gated that ordinary proposal,
  labelled 172 QUIET and switched to 123. Under accepted Controller-02 NORMAL semantics, **172 remained ACTIONABLE**.

Therefore the measured 172 → 123 switch is mechanically real, but it is **not** accepted evidence of the intended
Controller-02 scene-switch semantics.

## 3. Historical known answer (accepted reference)

ACCEPTED HISTORICAL REFERENCE, not a North-Star measurement. Sources: `docs/controller/controller-01-state-action-report.md`
and `docs/controller/controller-02-residual-closure-report.md`.

Accepted Controller-01, with the ideal / oracle matcher:

| quantity | value |
|---|---|
| localized objects | 25 |
| ordinary observations | 141 |
| scene switches | 26 |
| natural reactivations | 2 |
| final active-map surfels | 1,059,349 |
| reachable evaluation samples | 29,288 |
| samples covered within 12 mm | 28,801 |
| micro coverage | 0.9833720295001366 (≈ 98.34 %) |
| objects with per-object coverage 1.0 | 16 of 25 |
| terminal | 24 QUIET, 1 watchdog-blocked (210) |

Accepted Controller-02 then replayed all 141 / 141 ordinary Controller-01 actions exactly and preserved the 2 natural
reactivations. It changed only the treatment at the ordinary budget: Controller-01's BLOCKED watchdog became
DEFERRED → RESIDUE. `final_look_gate_v1` was invoked **only** after NORMAL work was exhausted, once, for the one DEFERRED
object (210), which it rejected.

Project interpretation: **the local controller is already proven with an ideal matcher.** The North-Star task is to
transport that proven behavior into RGB bootstrap, arbitrary spherical seed directions, recentered policy charts and
canonical H0, without changing the controller unnecessarily.

## 4. Next

**North Star-1c2 — Correct Controller-02 NORMAL / RESIDUE Semantics** (branch
`north-star/ns1c2-controller02-phase-semantics`, contract `docs/north-star/ns1c2-controller02-phase-semantics-contract.md`,
committed before canonical replay or execution).

Its one causal question: starting from the accepted NS1b North-Star state, does the first scene-level attention switch
occur under the ACTUAL ACCEPTED Controller-02 NORMAL / RESIDUE semantics? Relative to NS1c, the only independent
variable is the placement of `final_look_gate_v1`: in NS1c it gated every local proposal; in NS1c2 it is called only in
Controller-02 RESIDUE.

- NS1c's first four actions on 172 were ordinary FSG6f proposals selected before the semantic difference could affect
  action selection. NS1c2 reuses them read-only as a measured replay source (no re-render), after proving that the
  corrected NORMAL decisions select exactly the same actions.
- The first true divergence is the post-step-3 Cyclopean proposal of 172.
- Everything else stays frozen: FSG6f, Cyclopean, the scheduler, the 24-look budget, `final_look_gate_v1`, target-only
  fusion, the charts, the fixed head and the oracle aids. 10 / 110 / 178 remain deferred.
