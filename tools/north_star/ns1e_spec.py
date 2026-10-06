"""North Star-1e: declared constants, pinned sources, the frozen NS1a / NS1c2 / NS1d inputs and the run layout.

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md.  Standard library only, so both interpreters
(Blender's and the host .venv) can import it.  The checker keeps its own literal copies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "5aa223109ec829d41945f19b4c5223928fd0dde9"          # main: post-NS1d roadmap (NS1e next)
NS1D_ACCEPTANCE = "25bb929b4d39e1e73cabf0df582bc3c5d3e45e06"
NS1C2_ACCEPTANCE = "5fe0684bae6ab4bc8a2080b1a93089fdb2a935af"
NS1B_ACCEPTANCE = "255355108863022f931574dae4b2df8cdd2a772e"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
NS1C_REPORT_HEAD = "4107be86228c970f4b82fb6d5343365c551f36b0"     # NS1c: NOT accepted, NOT merged
CONTRACT_COMMIT = "0728857de498e2b560def4e7233fefce2c222dfe"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "North Star-1e: Full Coherent Multi-Entity Loop with Cross-Target Measurement Memory"
CONTRACT = "docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md"
REPORT = "docs/north-star/ns1e-coherent-full-loop-m2-memory-report.md"
MARKER = "NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_COMPLETE"
NS1D_REPORT = "docs/north-star/ns1d-cross-target-measurement-memory-report.md"
NS1D_ACCEPTED_MARKER = "NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED"
NS1E_ACCEPTED_MARKER = "NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_" + "ACCEPTED"      # never written by Claude Code
NS1C_ACCEPTED_MARKER = "NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_" + "ACCEPTED"     # must never appear

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
TRUTH_HISTORICAL = "ACCEPTED HISTORICAL REFERENCE"
LABEL_HISTORICAL = "ACCEPTED HISTORICAL REFERENCE - not an NS1e measurement"
LABEL_MEMORY = "INSTANCE MEASUREMENT MEMORY (measured samples, NOT fused surfels)"
LABEL_MAP = "PERSISTENT SURFACE MAP (target-only fusion)"
LABEL_EFFECTIVE = "EFFECTIVE GEOMETRY = map + memory (no dedup, no fusion)"
LABEL_EFFECTIVE_DIAG = "MEASURED EFFECTIVE GEOMETRY - NOT PERSISTENT RECONSTRUCTION"
LABEL_H0 = "CANONICAL H0"
LABEL_CHART = "POLICY CHART C_i (fixed; NOT head motion)"
LABEL_FIXED_HEAD = "PHYSICAL HEAD FIXED - POLICY CHART ONLY"
LABEL_ORACLE_CORR = "ORACLE CORRESPONDENCE"
LABEL_GEOMETRY = "DERIVED SPHERICAL GEOMETRY"
LABEL_SEGMENTATION = "ORACLE SEGMENTATION AID"
LABEL_AMBIGUOUS = "AMBIGUOUS ORACLE ID - EXCLUDED"
AMBIGUOUS_STATE = "AMBIGUOUS ORACLE ID - EXCLUDED FROM SCHEDULER"
LABEL_SCHEDULER = "controller02.schedule_normal (accepted)"
LABEL_GATE_RESIDUE_ONLY = "final_look_gate_v1: RESIDUE only"
LABEL_BOOTSTRAP = "BOOTSTRAP CROSS-TARGET MEMORY: NOT PART OF NS1e"
LABEL_NO_NAME = "no object name used"
LABEL_NON_COMPARABLE = "NON-COMPARABLE HISTORICAL REFERENCE"
LABEL_NO_REACTIVATION = "NO NATURAL REACTIVATION MEASURED"
LABEL_REFERENCE = "ACCEPTED BREADTH-1 0.5 deg FIRST-HIT REFERENCE (post-freeze evaluation only)"
SCOPE_CLOSED = "COHERENT_SUBSET_CLOSED"
SCOPE_CAP = "INCOMPLETE_CAP"
NO_REFERENCE = "NO_0P5_DEG_FIRST_HIT_REFERENCE"
FORBIDDEN_CLAIMS = ("FULL_CLASSROOM_CLOSED", "GLOBAL_QUIESCENCE")

# ---- scheduler identity (the frozen NS1a single-patch rule; derived and compared, never forced)
EXPECTED_COHERENT = (9, 12, 123, 129, 172, 202, 204, 212, 230, 231)
EXPECTED_AMBIGUOUS = (10, 110, 178)
RANK1 = (9, 12, 204, 230, 231)
BUDGET_EXPECTED = 24

# ---- the accepted upstream runs (read-only)
NS1A_RUN = SHARED / "previews/north-star/ns1a-perfect-bootstrap-round"
NS1B_RUN = SHARED / "previews/north-star/ns1b-recentered-controller-handoff"
NS1C_RUN = SHARED / "previews/north-star/ns1c-coherent-first-scene-switch"
NS1C2_RUN = SHARED / "previews/north-star/ns1c2-controller02-phase-semantics"
NS1D_RUN = SHARED / "previews/north-star/ns1d-cross-target-measurement-memory"
B1_RUN = SHARED / "previews/breadth-1-classroom-234-spherical-glance"
NS1A_PINS = {"seeds/seed-set.json": "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a",
             "source/nb1c-gaze-list.json": "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062"}
NS1C2_MANIFEST_SHA256 = "0ec6228d96db1bfadc3372c3ce95342ddfa14f7ba2f11d24234c20ed59d2c8c1"
NS1C2_PINS = {"scene/state-after-step-07.json": "7e50ecf502daf10bc99aef29456f973da3cdbb04aeb92563a3c80bcc999d03db",
              "scene/final-scene-state.json": "315aed3b2ceff77235dea8a4d2018b6a133492f12ca284e3b07134c4fab96026",
              "charts/policy-charts.json": "058a9253a592c4b9df5171f97ad4c1c331548e4c39c198e1d763fc32b160a077",
              "contexts/contexts.json": "25b3940b0f69ae2b270e6ed7c165efae314d24cdf825c03ed80050077c997f4a",
              "freeze/scene-freeze.json": "ea5d046511e9ff7ad960826e3d3f7ce179a07edcfddc85aa62bbae7e4ff91640"}
NS1D_MANIFEST_SHA256 = "2b5bd1726e291f8234b5ffc33d13b4afe0d930c4e9955da9aff1bf03e8848c6e"
NS1D_PINS = {"check-summary.json": "9320a3d64b687eea14fe9699ae11bf3c050b3b99bd796c267ba2786a1136fa5d",
             "freeze/replay-freeze.json": "95c5106e61a9aa113921daeff68311020cca9f4dd15524e9264e44a18df90597",
             "freeze/event-list-freeze.json": "c39390b7cc17ff5417593569c9b05e671c8c4f8ddd47efa063104e9a890fb5c4",
             "replay/state-after-event-08.json": "7f0c7ce5542e0f4f47ea15bca8a2da6de5093f4bda2a954b921009953bb968e1",
             "replay/final.json": "6dcf21a81e50266ae47d380cc6ea4dfd656db4c6763bc6c238f476b381b48e16",
             "events/event-list.json": "eea5d6f56955872fb22ba1e236641c4bebcef6804d770b36999818fe4dbb2dd3"}
NS1D_EVENTS = 9                       # memory events 0..8 consumed (NS1b action + NS1c2 steps 0..7)
B1_EXR = "render/canonical.exr"
B1_EXR_SHA256 = "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8"
B1_WIDTH, B1_HEIGHT = 720, 360

# ---- the expected start state (contract section 6; derived and compared, never forced)
HANDOFF_EXPECTED = {
    "current": 202, "global_step": 8, "attention_bout": 2,
    "own_looks": {"9": 1, "12": 1, "123": 1, "129": 1, "172": 9, "202": 2, "204": 1, "212": 1, "230": 1, "231": 1},
    "quiet": [172], "quiet_since": {"172": 6},
    "memory_total": 581882, "memory_ids": 11,
    "revisions": {"9": [1, 0], "12": [1, 0], "123": [1, 5779], "129": [1, 777], "172": [9, 131695],
                  "202": [2, 17447], "204": [1, 0], "212": [1, 38197], "230": [1, 0], "231": [1, 0]},
    "next": {"kind": "attend", "target": 202, "decision": "retain", "reason": "retain", "source": "fsg6f",
             "local_gaze_deg": [-10.899999999999999, 10.5],
             "world_gaze_deg": [-147.62774503449359, 15.922813864915128]},
}
MAX_NEW_EXPECTED = 231               # (24 - 9) + (24 - 2) + 8 * (24 - 1) + 10
ABS_CAP_EXPECTED = 239               # 8 + 231

# ---- the action observation (the North-Star standard, inherited unchanged from NS1a / NS1b / NS1c2)
BLEND = "scenes/classroom/classroom_eye.blend"
BLEND_SHA256 = "dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc"
BLENDER = "blender"
PROFILE = "full"
IPD_M = 0.063
VERGENCE_M = 2.10
TANGENT_FRAME = "baseline_projected"
DEVICE = "OPTIX"
SPP = 4096
SEEDS = {"L": 2111, "R": 2112}
RENDER_BUDGET_S = 600.0
EYE_CENTRES_H0 = ((-0.0315, 0.0, 0.0), (0.0315, 0.0, 0.0))
HEAD_TOL = 1e-12
NS1A_CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
GAZE_ROUNDTRIP_TOL_DEG = 1e-9
ASSOCIATION_RADIUS_M = 0.012
HASH_CELL_M = 0.012
COVERAGE_RADIUS_M = 0.012
FUSION_FRAME = "H0"
CORE_SIZE = 256

# ---- the accepted Controller-01 historical evaluation (ACCEPTED HISTORICAL REFERENCE; NOT numerically comparable)
HISTORICAL_98 = {"covered": 28801, "reference": 29288, "fraction": 0.9833720295001366, "percent": "98.34 %",
                 "definition": "dense 0.25-degree cyclopean first-hit samples inside the old controller angular domain "
                               "over the 25 localized objects; covered iff within 12 mm of a final surfel"}

# ---- accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
    "fov3d/__init__.py": "7a514a1b8ea6ba8b61f618f500e15e36a288cede82f942358ce79353df0eb5fc",
    "fov3d/_compat.py": "014d1fb8c9cfc4c80fbf015c698e8fc706a16b79a0eda2b916e8727d9e61a870",
    "fov3d/control/integrated.py": "b4a11fbee78b526726d86ffaeac08ae175818cecb7d7ca73688ab1447167b629",
    "fov3d/control/controller02.py": "21c658a15ecb3f4f41dc73468a32f073df124eefd777c6c5e903bcf567bf8791",
    "fov3d/control/frontier.py": "2223dc1e2131693ef054475160ab55bd3955fab8c7f018bf93ce5da9645895ea",
    "fov3d/control/object_policy.py": "a91159304ca176ee4622135232d5c521cdce60bb0955986f68d8f0f0c79586a4",
    "fov3d/control/frontier_config.py": "c1826ff02b69aa43319fe3b367656fdad84e710b9e47c9e6ce64789afecd1fac",
    "fov3d/experiments/classroom_oracle/controller01.py": "840f728b9c009087b76edb945a835882d607e4a27c568f8be6a164b38599c896",
    "fov3d/experiments/classroom_oracle/controller02.py": "b3fed8894b1a0fcce1bce097a22cbb69a52d43a145fdda3f19bd683e40d64242",
    "fov3d/experiments/classroom_oracle/epistemic.py": "99de9874d9abc971223b13892110deede16b4e8931e1e35b3229ff9101edae63",
    "fov3d/experiments/classroom_oracle/matcher.py": "485b6e4fe999284daa81e71e96633737320af906c869201ef4069a166b8d7848",
    "fov3d/experiments/classroom_oracle/config.py": "8231c7f3b7a1b19108eaeb1fa6294cad0dbcf47f61b12025250e3ef7ac24aa07",
    "fov3d/reconstruction/surface_map.py": "51e5da5262a74db782930562b2a8026513996e5512a178b05600d770a915f983",
    "fov3d/reconstruction/association.py": "fe8cf0e22f2a0b7d252f9110bf42e07f168c6ba85b341ab9cef20853308ef135",
    "fov3d/reconstruction/measurement_memory.py": "27471ebf7076e5a21b8d23be994425993115b5e379a4dd7f32b7fce09e52ab25",
    "fov3d/geometry/core.py": "c9abec21ae7c9d6931836352dc81070948b977edc93ccfdee7ff48eadda098c6",
    "fov3d/stereo/core.py": "381e2db7677a7896c60b9e914cab7de40647e71ab9d635fbe0e86f74222bcd6a",
    "tools/fsg6f_frontier.py": "d636c9405d7199164e245ea48618dd7cebb9504074bd98b9136e2bd6f4ff18a1",
    "tools/fsg6f_public.py": "c79f58c9b51f33d4463f2bcfcaa339d79cf20a962b44de9c6cc721cf157cd2fa",
    "tools/multiobject2c_policy.py": "f4d4a08b0098146691ca66d7bb10aeab097f357e59e9d19e43c7bda47e246f8d",
    "tools/classroom_oracle1_epistemic.py": "20d7a4cb6d85109f7c4b165dcccefdd3faf4be600e00113cb2e604d796fca225",
    "tools/classroom_oracle1_public.py": "7b85e59a6e397ed69d3eaec8a6b3790639a6c6ffce596fd0d8d1664c738452bb",
    "tools/classroom_oracle1_matcher.py": "d213c2c7da68a2969b54a095fc7d953d7d16b21f5690cf2fd152197265884afa",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg3_surface_map.py": "1b9dbeb873105ec9bd9aef9680f67ed18db9a7387d6871d6ed8e6ab58bcb1e01",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/classroom_oracle1_eval.py": "b9f707e6a3a52fb525a9252a581097ced75a6f9d90f3b850d4b0bb783d04053b",
    "tools/classroom_oracle/breadth1_spec.py": "f9b8ceb6c2c8a1d1c10edb7904483332b5f5df0e8905a47269d5ce8da3e6b6da",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/active_bootstrap/ab1b_oracle.py": "51e2ee556a4a3576d00cd99255793212ad5efcb50b1e15ed292740d8c24aa231",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/north_star/ns1a_spec.py": "2b43d8b8112a6d738ae212d49aca03ecfeb4c20361128ca51fee498d1c6795d9",
    "tools/north_star/ns1a_core.py": "f32d0aaa986686630d9cc94916719c252dadd817da00886cf38d4a3accf60233",
    "tools/north_star/ns1a_render.py": "f5848706902d7190d2882f29924784f0350b4aad9ee7edee09e33ed746e5d1aa",
    "tools/north_star/ns1a_visuals.py": "dadf8c116b968383a9b0df1f242a7f6a0e5a0f52c81e339dd959dc8fdc301155",
    "tools/north_star/ns1b_spec.py": "892a965ec4e7649904743f59b83d129aca22654041f786accfa8173f54391e2d",
    "tools/north_star/ns1b_chart.py": "15b212166b6e3575d286e31613bbc2ab82b3be046f8f4fce330b706a7cb364af",
    "tools/north_star/ns1b_core.py": "bd9b4dea82f7514ca62c4a307a23735675c07a3c06726a8101ccf1b6215522e1",
    "tools/north_star/ns1b_visuals.py": "78d60bb0a82fed1375a837484dbe65bbca18dae624222424215d23d4a3930f5e",
    "tools/north_star/ns1c2_spec.py": "1d49e3e140d2dfc7e716d7345bef33bf065eb6e06da53ab4c84db43c00314aac",
    "tools/north_star/ns1c2_core.py": "f0504eda808f5e15eda0b30f0e25805f22594e1424601cef69b9e2cf4e96faba",
    "tools/north_star/ns1c2_phase.py": "99f6a3da750abe0654ee95085ff387dfbea961ed853f48e85d96fc2a2f6a8acc",
    "tools/north_star/ns1c2_run.py": "28c77c4ff2ec7292f70f76d1d65a5c04ec50dbeb6e2f9329799587f5a1210573",
    "tools/north_star/ns1c2_render.py": "9e73b34b3b3bfde0f29b83c680aa5d9e2e991aa4cdc9864f97e8d5bd8f07c30d",
    "tools/north_star/ns1c2_synthetic.py": "11367fd1f3acca1c5712a805559ce8da6575212034ccd97633b1a8e7ac933d31",
    "tools/north_star/ns1d_spec.py": "902f10bc650f556d8ef8475c5ffcde57a6f4a9cecb2bcff8ff5545a8aef409d9",
    "tools/north_star/ns1d_core.py": "f48f43364f736eefac4a4e542f47a3df10862c8291c1da0849cd072a3e713311",
    "tools/north_star/ns1d_visuals.py": "c684002fbb68701ae20e305cd94b4030675c904cf88e4793d8ad14df1625ca5c",
}
NS1E_TOOLS = ("ns1e_spec.py", "ns1e_core.py", "ns1e_render.py", "ns1e_run.py", "ns1e_synthetic.py", "ns1e_visuals.py",
              "check_ns1e.py", "check_ns1e_corruptions.py")

# ---- run layout and commands
RUN_DEFAULT = SHARED / "previews/north-star/ns1e-coherent-full-loop-m2-memory"
VIS_DEFAULT = SHARED / "visuals/north-star/ns1e-coherent-full-loop-m2-memory"
ONCE = ("source", "synthetic", "handoff", "gate-harness")
STEP = ("schedule", "preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
        "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "freeze-identity", "fuse", "memory",
        "update")
RENDER_STAGES = ("preflight", "acquire")
COMMANDS = ONCE + STEP + ("loop", "freeze-control", "evaluate", "visualize")
FIGURES_ALWAYS = ("overview.png", "controller-full-timeline.png", "multi-entity-final-geometry.png",
                  "memory-flow-timeline.png", "coverage-by-entity.png", "rank1-diagnostic.png")
FIGURES_CONDITIONAL = ("natural-reactivation.png", "residue-phase.png")
PLY_PERSISTENT = "final-coherent-persistent-points.ply"
PLY_EFFECTIVE = "final-effective-geometry-diagnostic.ply"

OBS_ACQ = "observation/acquisition"
OBS_AID = "observation/oracle_aid"
CATALOG_REL = "observation/evaluation_only/instance-catalog.json"
ACQ_RUN_REL = "observation/acquisition-run.json"
OBS_ACQ_FILES = ("calibration.json", "rgb-observation.npz", "acquisition.json")
OBS_AID_FILES = ("raw_L.exr", "raw_R.exr", "reference-observation.npz")
SEGMENTATION_MEMBERS = ("instance_L",)
CORR_FILES = ("correspondence/oracle-correspondences.npz", "correspondence/oracle-summary.json",
              "correspondence/core-class-map.npz", "correspondence/correspondence-opened-files.json")
GEOM_FILES = ("geometry/left-core-rays.npz", "geometry/epipolar-result.npz", "geometry/geometry-summary.json",
              "geometry/geometry-opened-files.json")
SEG_FILES = ("segmentation/local-identity.npz", "segmentation/identity-summary.json",
             "segmentation/segmentation-opened-files.json")
FUSION_FILES = ("fusion/fusion.json", "fusion/target-patch.npz", "fusion/fused-target-map.npz")
MEMORY_FILES = ("memory/memory-patch.npz", "memory/event.json")
# one completion file per step stage, in order (a step directory is complete iff every one exists)
STAGE_OUTPUT = {"schedule": "freeze/plan-freeze.json", "preflight": "preflight/preflight.json",
                "acquire": ACQ_RUN_REL, "freeze-observation": "freeze/observation-freeze.json",
                "perfect-correspondence": "correspondence/oracle-summary.json",
                "freeze-correspondence": "freeze/correspondence-freeze.json",
                "spherical-geometry": "geometry/geometry-summary.json", "freeze-geometry": "freeze/geometry-freeze.json",
                "local-oracle-segmentation": "segmentation/identity-summary.json",
                "freeze-identity": "freeze/identity-freeze.json", "fuse": "freeze/fusion-freeze.json",
                "memory": "freeze/memory-event-freeze.json", "update": "update/update.json"}
# reads forbidden to every control stage (names, catalogs, seeds, evaluation truth, Breadth-1, NB1a/b discovery)
FORBIDDEN = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json", "evaluation.json",
             "evaluation/", "evaluation_only", "actions.json", "result.json", "render-metadata.json",
             "breadth-1-classroom-234-spherical-glance", "natural-bootstrap-1a-range-connectivity",
             "natural-bootstrap-1b-foveal-serviceability", "controller-01-full", "controller-02-classroom-replay")


def step_dir(step: int) -> str:
    return f"steps/step-{int(step):03d}"


def patch_id(step: int) -> str:
    return f"ns1e_step_{int(step):03d}"


def scene_state_rel(label: str) -> str:
    return f"scene/state-{label}.json"


def state_after(step: int) -> str:
    return scene_state_rel(f"after-step-{int(step):03d}")


def checkpoint_rel(step: int) -> str:
    return f"freeze/checkpoint-step-{int(step):03d}.json"


def memory_event_of_step(step: int, handoff_step: int = 8, first_event: int = NS1D_EVENTS) -> int:
    """NS1e global step k -> its memory event index (the first new observation is memory event 9)."""
    return int(first_event) + int(step) - int(handoff_step)


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
