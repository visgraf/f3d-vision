# Partition-Graph Phase 6 — Causal Epistemic Regions and Truth-Only Challenge Benchmark

## Why Phase 6 exists

Phase 5 unified valid local 3-D evidence with the head-centred spherical chart and found that the accepted Classroom trajectory is a poor benchmark for a graph-attention policy **when the challenge is defined only by gaps between already-discovered components**. Most such gaps were already explained by mapped or incidental non-target geometry; the remaining unresolved cells were mostly boundary quantization or thin eye-ray/head-origin bands. Only two transient episodes contained substantial unresolved territory, and the historical controller later resolved both.

That result does **not** mean the final reconstructed objects are complete. The accepted Oracle-1 run still covers only 25,618 of 29,288 dense reachable samples. The earlier Oracle audits showed that the dominant residual was often angularly disconnected from the currently reconstructed support, so a pairwise known-component gap is the wrong unit for the next benchmark.

Phase 6 therefore changes the question from

> Which gap between two known target components is unresolved?

to

> **At the moment the historical controller stops on a target, how is the entire causal spherical field partitioned into known target support, measured other surfaces, ambiguous boundaries, and regions with no head-centred depth; and where do the final missed target samples fall relative to those truth-free regions?**

Phase 6 still defines **no attention score and no gaze policy**. It creates a benchmark on which a later policy could be evaluated.

## 1. Two-stage truth firewall

Phase 6 is deliberately split into two programs.

### A. Causal proposer — no dense truth

`partition_graph6_propose.py` reads only:

- source `manifest.json` and `bootstrap/seeds.json`;
- the accepted Phase-4 joint lift summary;
- Phase-5 causal-final head-evidence products.

It does **not** open `evaluation_only`, `reachable_samples.npz`, `evaluation.json`, `oracle_observation.npz`, EXR, benchmark RGB, or Blender data.

The proposer writes a separate proposal tree containing region rasters, region attributes, graph adjacency, and the complete unranked candidate set.

### B. Offline evaluator — dense truth allowed

`partition_graph6_evaluate.py` is the only Phase-6 program allowed to open `bootstrap/evaluation_only/reachable_samples.npz`. It also reads each target's final map solely to reproduce the accepted 12 mm coverage test. It writes evaluation results to a different directory and never mutates the proposal tree.

For the accepted golden source the evaluator must reproduce exactly:

- reachable = 29,288;
- covered = 25,618;
- missed = 3,670.

Truth-positive labels, recall, and missed-sample counts are evaluator-only fields and are never available to the proposer.

## 2. Causal epistemic partition at target termination

For each of the 25 targets, use its causal-final state — the last fixation before the historical `attention_complete` termination.

The chart is the frozen 0.10-degree head-centred chart. Every cell receives exactly one representation class, with this precedence:

1. `TARGET_SUPPORT` — the target's own 12 mm persistent-map support;
2. `AMBIGUOUS_BOUNDARY` — multiple inherited instance identities accumulated at one head-centred cell; diagnostic only;
3. `OTHER_SURFACE` — a non-target surface is known either from a mapped owner or from Phase-5 incidental head-centred 3-D;
4. `TARGET_EVIDENCE_UNMAPPED` — target-labelled head-centred depth exists outside persistent target support; expected to be empty on the accepted run, but preserved as a diagnostic rather than silently folded into another class;
5. `UNKNOWN` — no head-centred surface evidence explains the cell.

`seen_any` is retained only as a descriptive region attribute. Because it is an eye-ray raster, it does not define region identity in Phase 6.

## 3. Region topology

The region partition uses the digital-topology convention already established by the project:

- target and measured-surface components: 8-connected;
- complement-like `UNKNOWN` and `AMBIGUOUS_BOUNDARY`: 4-connected.

`OTHER_SURFACE` is additionally separated by inherited instance id, so two measured objects cannot silently become one region.

Every region records only causal descriptors:

- kind, instance id when applicable, cell count, domain-edge contact;
- centroid direction;
- minimum/median angular distance to target support;
- minimum angular distance to a historical target fixation;
- fraction intersecting historical `seen_any`;
- mapped versus incidental cell counts;
- reconstruction status (`mapped_now`, `targeted_later`, `never_targeted`);
- dual adjacency and interface-edge counts.

No truth-derived quantity is written here.

## 4. Candidate set

Phase 6 emits **all** regions of these two kinds as future attention candidates:

- `UNKNOWN`;
- `OTHER_SURFACE`.

This is deliberately broad. `UNKNOWN` may hide an unseen continuation. `OTHER_SURFACE` may indicate an occluder or a surface that separates disconnected views of the same object. Neither is a continuation or occlusion verdict.

`AMBIGUOUS_BOUNDARY` is excluded from the candidate set because Phase 5 established that the observed ambiguity is dominated by chart quantization at instance boundaries. `TARGET_SUPPORT` is already reconstructed. `TARGET_EVIDENCE_UNMAPPED` is diagnostic.

**No ranking, score, threshold, winner, or next gaze is defined in Phase 6.**

## 5. Offline benchmark evaluation

For each target, the evaluator reproduces the sealed 12 mm coverage test against dense reachable first-hit truth and maps every missed target sample into the causal-final Phase-6 region partition.

It reports:

- missed samples by representation class;
- candidate recall: fraction of missed target samples falling in `UNKNOWN` or `OTHER_SURFACE` regions;
- number of truth-positive candidate regions;
- evaluator-only per-region counts of dense first-hit samples and missed target samples;
- connected components of missed target samples on the 0.25-degree truth lattice and which proposal regions each component intersects.

This is a **benchmark characterization**, not a policy metric. No scientific pass/fail threshold is imposed.

## 6. Scientific questions

Phase 6 should answer:

1. Does the causal epistemic partition capture most of the 3,670 residual target samples inside a manageable set of `UNKNOWN` / `OTHER_SURFACE` regions?
2. Are misses mostly in genuinely depth-unknown regions, or behind already measured other surfaces?
3. Does incidental 3-D materially subdivide the enormous complement into useful causal regions?
4. Do the known Oracle-3b detached miss components become localized by these regions even though they were not pairwise gaps between already-known target components?
5. Is the accepted Classroom run now a suitable benchmark for a *region-selection* attention experiment, or do we still need another scene/seed/budget?

The answer may be negative. Do not manufacture a policy if the candidate partition remains saturated or uninformative.

## 7. Acceptance gates

Phase 6 is accepted only if:

- checkers 1–6 pass;
- facade checker and baseline verifier pass;
- a fresh golden smoke remains `MISMATCHES 0`;
- the accepted full source remains `MISMATCHES 0`;
- proposer output covers all 25 causal-final targets and is truth-free;
- every chart cell has exactly one class and one region code;
- proposal candidates are exactly `UNKNOWN` plus `OTHER_SURFACE` regions;
- evaluator reproduces 29,288 / 25,618 / 3,670 exactly;
- proposal files remain byte-identical before and after truth evaluation;
- no gaze/controller/matcher/fusion/rendering/termination behavior changes;
- no policy or candidate ranking is introduced.

## 8. Demo contract

The evaluation-only demo has one final-state frame per target:

1. causal evidence classes;
2. causal epistemic regions;
3. dense reachable target truth overlaid for evaluation only;
4. per-target missed-sample / candidate-recall summary.

The demo must state explicitly that dense truth never participates in proposal construction.

## 9. Decision after Phase 6

If the causal regions localize substantial residual target truth in a non-saturated candidate set, the next phase may finally test **graph-level region selection** while keeping gaze generation separate.

If not, move to a new challenge setting (scene, seed, or controlled budget) rather than tuning a policy on an unsuitable benchmark.
