# Kernel

The standing rules of this repository, for every surface that works on it. This file
changes rarely: only by Luiz's decision, recorded as a process record.

Three files govern the work. Each holds one kind of content.

| Layer  | File                    | Holds                                                        |
|--------|-------------------------|--------------------------------------------------------------|
| Kernel | `CLAUDE.md`             | rules that hold whatever the surfaces, stage or tools        |
| Shell  | `docs/process/shell.md` | the current dial settings, each with the trigger that set it |
| State  | `docs/chat-handoff.md`  | where the project is now                                     |

**Placement test.** A line that would change with a platform capability, the project
stage, an execution cost or Luiz's bandwidth belongs in the shell. A fact about where
the project is belongs in the handoff. Nothing else belongs here: no commit ids,
dates, branch names, results or write permissions in this file.
`tools/process/lint.py` checks the three files; run it before pushing a change to any
of them.

Read in this order: this file, the shell, the handoff, then the active contract.
Claude Code loads the shell and the handoff through these imports:

@docs/process/shell.md
@docs/chat-handoff.md

## Authority

Luiz sets the scientific and architectural direction, decides when a proposal is
committed, accepts or rejects results, and opens and closes phases. Only Luiz
overrides this file. No AI surface makes an undelegated project decision: when a
decision rule is not met, the surface stops and returns the decision.

Precedence: this file, then the shell, then a step contract. A contract may specialize
the shell; neither may contradict this file. On conflict, stop and report.

## The six kernel rules

1. **Measured, proposed or assumed — never ambiguous.** Every numerical claim is
   PROPOSED (designed or predicted, not yet run where it counts), MEASURED (produced
   by an identified command and recorded in a committed file — say where) or
   ASSUMED / ESTIMATED (say so). Only execution on the surface the shell names for a
   quantity makes it MEASURED. A model of a run does not measure the run.
2. **Every tool ships a check that can fail.** A control, known answer, invariant,
   negative test or behavioral comparator able to expose a wrong implementation. A
   tool that cannot come out wrong has not been tested. Checks are never weakened and
   criteria never moved to make a result pass; when check and implementation
   disagree, diagnose first.
3. **The repository is the memory — of the process as well as its products.**
   Contracts, reports, the handoff and the process records are committed. Something
   learned only in a conversation is promoted into a committed file, or it does not
   exist for the project. A new conversation reconstructs the project from the
   repository; summaries are secondary.
4. **History moves forward only.** Commit, push, revert if wrong. Published history is
   never rewritten. A correction is a new commit that leaves the error visible.
5. **The human decides.** Ambiguity is resolved by asking, not by inference. If the
   working branch is not named by the instruction or the contract, ask.
6. **The contract precedes execution.** Substantial work starts from a committed
   contract that names the branch and head it assumes. A surface that finds another
   head, or a false premise, rejects the contract rather than repairing it silently,
   and commits a `rejected` record.

## Contracts, reports, repairs

A **step contract** states: what changes and what deliberately does not; the branch
and head it assumes; the commands in order, with their cost class; the expected
checks; the acceptance criteria, declared before evaluation whenever tuning against
the result could compromise it; the stop conditions; the scope of permitted fixes
(none if unstated: diagnose, report, stop); and what the report must record.

A **report** records: branch and commit ids; the commands actually run; summary lines
verbatim where useful; every failing gate; measured numbers with the file or run they
came from; repairs and why they were needed; deviations from the contract; whether
acceptance passed; unresolved decisions. Reviews read the committed report and diff,
not a paraphrase.

A **repair** is made only when the contract delegates that class of repair. It is
minimal, outside the acceptance criterion, described, committed, and distinguishable
from the proposed change. A change to architecture, scientific assumptions,
thresholds, evaluation semantics or experiment design is not a repair: stop and
return the decision.

Refactoring must not silently become science: a structural step shows, by a
machine-checkable comparison, that preserved behavior is preserved, unless its
contract declares the behavioral change.

## Project invariants

These change only when the code they describe changes.

- Metres. The head is fixed; eyes rotate about their own centres.
- `EYE` is a Blender camera object: local −Z is gaze, local +Y is head up.
- Equirect `(u, v)` to EYE-frame direction: `lon = (u − 0.5)·2π`,
  `lat = (0.5 − v)·π`, with `v = 0` at the top row.
- Epipolar `(θ, φ)` of a head-frame direction: `θ` from +X (the baseline),
  `φ = atan2(d_y, −d_z)` about X. Corresponding directions share `φ`; parallax
  `θ_R − θ_L > 0`.
- Two interpreters, not interchangeable. `blender -b -P` scripts use Blender's
  bundled Python and only what it ships; host-side scripts use the repository `.venv`.
  An import that works in one is no evidence for the other.
- `blender -b -P` may exit 0 after the script failed. A Blender-side tool that
  produces an artifact makes its own failure observable and exits nonzero.
- Migrate behavior first, redesign structure second.
- Python stays plain, typed where useful; no framework machinery unless it solves a
  demonstrated problem.

## Final principle

Optimize for clear scientific decisions, reproducible behavior, cheap recovery,
explicit authority and minimal human file shuffling. GitHub carries state. The shell
says who does what. Luiz decides.
