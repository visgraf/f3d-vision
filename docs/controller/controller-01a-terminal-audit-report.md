# Controller-01A: terminal blocked-state audit — report

**Result.**

    CONTROLLER01A_FINAL_REPROBE_ACTIONABLE

This result is **MEASURED** by the command below, and it awaits review by Luiz and Chat. The
branch is not merged, and `docs/chat-handoff.md` does not record this result. Interpretation
belongs to Luiz and Chat; this report draws no Controller-02 policy conclusion.

**Question** (contract `docs/controller/controller-01a-terminal-audit-contract.md`). At the final
causal scene state, after the other objects' later observations have been incorporated, would
object 210 (`wall.008`) still be ACTIONABLE if only the sticky BLOCKED flag were ignored and the
unchanged accepted local policy were asked again?

**Answer (MEASURED): yes.** The reconstruction was first validated: it reproduces the saved
Controller-01 watchdog-prefix probe exactly. At the terminal state, the unchanged FSG6f → Cyclopean
probe on 210's unchanged 24-look own context still returns ACTIONABLE:
- FSG6f `continue`, proposing the **same gaze** `[7.6, 18.2]` as at the watchdog;
- OPEN frontier 58 → 52, and still one admissible candidate.

The 190,011 causal measurements of 210 added after the watchdog, all from other targets' looks,
changed the frontier counts but did not make the local policy stop.

## Provenance

| item | value |
|---|---|
| accepted Controller-01 | report commit `e3bf5e08f579104024036d94a2d97a9221ca82dd`; docs-only acceptance commit `e659ff1053f6fb0702f2d34224a5da2cec7f9ae9` (`INTEGRATED_FOVEAL_CONTROLLER01_ACCEPTED`), which `origin/main` now points to |
| source run | `/home/lvelho/temp/previews-2026.09.28/controller-01-full` (preserved; 1,678 files) |
| source hashes | `manifest.json` `d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91`; `actions.json` `12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd`; `evaluation.json` `76cb1e5df88ea401aed6409327bd51fc149fa05b174a1e67b014e671b34512b6` (hashed only; never opened by the audit) |
| audit branch | `controller/controller-01a-terminal-audit`, created from `e659ff1` in an isolated worktree; the shared checkout was not touched |
| contract | `e53c59fbb6468a2366f3965c64e6b985e89e3781` *Specify Controller-01A terminal blocked-state audit* (with the layout checker's declaration of the two 01A documents), committed before any audit code |
| audit implementation | `474ee21354783127d721d24dfc9422c305f4c6a5` *Implement the Controller-01A terminal re-probe audit*; `8d9be3f2687587156f29dde081415f85af2ac192` *Gate the Controller-01A prefix memory against the saved provenance* |
| measured at | `8d9be3f`, with a clean tracked tree |
| report | the commit that adds this file |

Changed files (`e659ff1..8d9be3f`, plus this report):

    A  docs/controller/controller-01a-terminal-audit-contract.md
    M  tools/controller/check_controller01.py         (audit mode only; unit suite unchanged, 56/0)
    M  tools/repository/check_repository_layout.py    (declares the two 01A documents)

No `fov3d/` file changed (0 diff lines). No sealed module, threshold, watchdog, scheduler, local
policy or accepted artifact changed. No Blender, render, fixation, measurement or map fusion
happened.

## Command

    .venv/bin/python tools/controller/check_controller01.py \
        --terminal-reprobe /home/lvelho/temp/previews-2026.09.28/controller-01-full \
        --object 210 --audit-out previews/controller-01a-terminal-audit/audit.json

- 9.00 s wall (interactive), rc 0; `SUMMARY checked=12 failed=0`.
- The audit record `audit.json` (sha256 `f4735a6d035f8aeb8ef553dacfc0acd97899070ed0225bfc90ee9525f5c08dfd`)
  is a regenerable preview in the audit worktree. It is not committed and not written into the
  preserved run.
- An earlier identical run at `474ee21`, before the extra prefix gate, gave the same probes and
  measurements.

## Files opened and the truth firewall

The audit runs inside the Controller-01 truth firewall (`fov3d.control.integrated.TruthFirewall`
with `controller01.is_evaluation_truth`). **Violations: 0.** It opened 195 run files, all
controller-time:

| files | count |
|---|---|
| `manifest.json`, `actions.json` | 2 |
| `objects/*/patches/fix_kk.npz` (every action's saved patch) | 141 |
| `objects/instance_0210/acquisitions/fix_kk/calibration.json` | 24 |
| `objects/instance_0210/acquisitions/fix_kk/oracle_observation.npz` | 24 |
| `objects/instance_0210/{result.json, final_map.npz, maps/fix_23.npz, final_effective_geometry.npz}` | 4 |

No file under `bootstrap/evaluation_only/` and no `evaluation.json` was opened. The preserved run's
per-file sha256 manifest (1,678 files) was identical before the audit, after the harness, and after
the final audit.

## Reconstruction and validation gates (all MEASURED pass)

| # | gate | result |
|---|---|---|
| 1 | action order: contiguous ascending global steps 0…140; 210's own actions at local steps 0…23 in global order; 24 = manifest fixations | pass; watchdog step = 101 |
| 2 | memory replay through step 101 reproduces every logged per-action addition | pass |
| 3 | the prefix memory of 210 (XYZ, source step, source target) equals the head of the saved terminal provenance (append-only) | pass (1,584,958 points) |
| 4 | own-look identity: 24/24 calibration gazes equal the logged gazes; 24/24 matcher-recreated patches equal the saved patches | pass |
| 5 | the own context holds exactly 210's own looks (visited = the 24 logged own gazes in order; 24 history entries) | pass |
| 6 | active map: `final_map.npz` equals `maps/fix_23.npz`, 163,944 surfels = the logged map size | pass |
| 7 | the saved Controller-01 probe record after step 101 exists | pass |
| 8 | **watchdog-prefix reproduction** (the stop gate) | **pass**, exact (next table) |
| 9 | memory replay of steps 102…140 reproduces every logged addition | pass |
| 10 | the terminal effective geometry (XYZ and per-point provenance) equals the saved `final_effective_geometry.npz` | pass (1,938,913 points) |
| 11 | truth firewall | pass (0 violations) |
| 12 | a result was reached (no reconstruction failure) | pass |

## Watchdog-prefix reproduction (step 101)

| field | saved Controller-01 record | audit re-probe |
|---|---|---|
| revision (own looks, measured points of 210) | [24, 1,584,958] | [24, 1,584,958] |
| effective points | 1,748,902 | 1,748,902 |
| state / source | ACTIONABLE / fsg6f | ACTIONABLE / fsg6f |
| FSG6f reason | `continue` | `continue` |
| frontier raw / OPEN / map-resolved / boundary-resolved | 354 / 58 / 26 / 270 | 354 / 58 / 26 / 270 |
| candidates / consensus-rejected | 1 / 3 | 1 / 3 |
| proposed gaze | [7.600000000000001, 18.200000000000003] | [7.600000000000001, 18.200000000000003] |
| Cyclopean | not reached | not reached |

The whole saved probe summary is equal (exact integers; gaze within 1e-9, in fact identical).

## Measurements of 210 added after the watchdog

| quantity | value |
|---|---|
| measured points of 210 at the watchdog (step 101) | 1,584,958 |
| measured points of 210 at the terminal state (step 140) | 1,774,969 |
| causal measurements of 210 added after the watchdog | **190,011** |
| by source (active) target | 234 `worldMap`: 94,431; 109 `alphabet`: 76,308; 224 `woodBase`: 19,272 |
| by source global step | 106: 7,453 · 107: 4,550 · 110: 4,657 · 117: 2,612 · 128: 2,912 · 129: 20,422 · 130: 17,044 · 131: 28,892 · 132: 4,472 · 133: 20,689 · 134: 40,494 · 135: 35,814 |
| active map of 210 | 163,944 surfels, unchanged (no own look after step 101; nothing fused) |
| effective geometry of 210 | **1,748,902 → 1,938,913** (+190,011) |

## Terminal re-probe

210's own context is unchanged: 24 looks and the last gaze `[2.6, 18.2]`. Only the effective
geometry differs. The probe ignores only the sticky BLOCKED flag.

| field | watchdog prefix (step 101) | terminal (step 140) |
|---|---|---|
| state / source | ACTIONABLE / fsg6f | **ACTIONABLE / fsg6f** |
| FSG6f reason | `continue` | `continue` |
| proposed gaze | [7.6, 18.2] | **[7.6, 18.2]** (the same) |
| frontier raw / OPEN / map-resolved / boundary-resolved | 354 / 58 / 26 / 270 | 350 / 52 / 28 / 270 |
| candidates / consensus-rejected | 1 / 3 | 1 / 2 |
| selected candidate: OPEN / raw aligned support | 35 / 46 | 30 / 43 |
| selected candidate: map-resolved / boundary-resolved support | 2 / 9 | 3 / 10 |
| selected candidate: predicted new angular area (deg²) | 45.198 | 45.669 |
| selected candidate: frontier score | 7.2215 | 6.1351 |
| Cyclopean eligible cells | not reached (FSG6f continued) | not reached (FSG6f continued) |

Outcome: `FINAL_REPROBE_ACTIONABLE`.

## Fail-capability evidence

Harness: scratch `audit_mutants.py`.
- Data corruptions acted on fresh real copies of a subset copy of the needed run files, with
  *placeholder* `evaluation.json` and `bootstrap/evaluation_only` files, not truth.
- Code mutants acted on throwaway repository copies.
- The unmutated subset copy gives rc 0 and the same ACTIONABLE result.
- Every corruption gives rc 1, a named FAIL and **no result marker**.

| # | deliberate corruption / mutant | caught by |
|---|---|---|
| 1 | global action ordering corrupted (actions 101 ↔ 102, steps renumbered) | gate 3, the prefix memory provenance |
| 2 | a missing saved patch (instance 224 `fix_05`) | explicit reconstruction failure (`FileNotFoundError`) |
| 3 | a patch attributed to the wrong active target (111 `fix_03` ↔ 224 `fix_03`) | gate 2 (the step-11 addition mismatch) |
| 3b | (code) the wrong active target written as memory provenance | gate 3 |
| 4 | 210's own-look order changed (acquisitions `fix_05` ↔ `fix_06`) | gate 4, own-look identity |
| 5 | (code) another target's gaze added to 210's local history | gate 5, own-context identity |
| 6 | (code) the active map alone instead of the effective geometry | gate 8, prefix reproduction |
| 7a | (code) an attempted open of `evaluation.json` | the firewall (`PermissionError`; violation recorded) |
| 7b | (code) an attempted open of `bootstrap/evaluation_only/…` | the firewall |
| 8 | (code) the replay one step short, so step 101 is not reproduced | gate 8 (stops before any terminal probe) |

Result: **10/10 caught.** Eight were required.

The layout accommodation was mutation-tested with the Controller-01 layout suite plus two new
mutants, a misspelled undeclared 01A report and the contract untracked: **33/33 caught**. The
checker reports 495/0 before and after.

## Gates at `8d9be3f`

| gate | result |
|---|---|
| `tools/controller/check_controller01.py` (unit and architecture) | `SUMMARY checked=56 failed=0` |
| `tools/repository/check_repository_layout.py` | `SUMMARY checked=495 failed=0` |
| `tools/conceptual_core/check_conceptual_core14.py` | `SUMMARY checked=64 failed=0` |
| `tools/classroom_oracle/check_classroom_oracle1.py` | `SUMMARY passed=12 failed=0` |
| `tools/consolidation/check_fov3d_facade.py` | `SUMMARY checked=16 failed=0` |
| `scripts/verify_baseline.sh` | `[verify] SUMMARY passed=9 failed=0` |
| `git diff --check` (worktree; `e659ff1..HEAD`) | clean |

## Deviations from the contract

1. **One additional gate (3)**, stricter than the contract list: the prefix memory must equal the
   head of the saved terminal provenance. It was added after the harness showed that a global
   reordering was otherwise caught only at the terminal-geometry gate, after the prefix probe. It
   is committed separately (`8d9be3f`), and the official run is at that commit.
2. **Two extra mutants** (3b, 7b) beyond the eight required.
3. **Harness fix, scratch only.** The first harness invocation failed before running any mutant: its
   work directory was not created. That was fixed and re-run.

No repair was needed to reproduce the watchdog prefix. The saved float32 `final_map.npz` reproduces
the runtime probe exactly.

## Unresolved (for Luiz and Chat)

- The interpretation of `FINAL_REPROBE_ACTIONABLE`, relative to sticky-BLOCKED semantics versus
  genuinely unresolved local continuation, and any consequence for the next step. This report
  deliberately draws none.
