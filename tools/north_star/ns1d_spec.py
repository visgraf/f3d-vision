"""North Star-1d: declared constants, pinned sources, the frozen NS1b / NS1c / NS1c2 inputs and the run layout.

Contract: docs/north-star/ns1d-cross-target-measurement-memory-contract.md.  Standard library only.  The checker keeps
its own literal copies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "3720d745558bcbadb1c9edb3ffad5aaf0d86b3bb"          # main: post-NS1c2 roadmap (NS1d next)
NS1C2_ACCEPTANCE = "5fe0684bae6ab4bc8a2080b1a93089fdb2a935af"
NS1B_ACCEPTANCE = "255355108863022f931574dae4b2df8cdd2a772e"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
NS1C_REPORT_HEAD = "4107be86228c970f4b82fb6d5343365c551f36b0"     # NS1c: NOT accepted, NOT merged
CONTRACT_COMMIT = "93f51d3abea379c0bf05720261dda039dca073d0"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "North Star-1d: Controller-Phase Cross-Target Measurement Memory"
CONTRACT = "docs/north-star/ns1d-cross-target-measurement-memory-contract.md"
REPORT = "docs/north-star/ns1d-cross-target-measurement-memory-report.md"
MARKER = "NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_COMPLETE"
NS1C2_ACCEPTED_MARKER = "NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_ACCEPTED"
NS1C_ACCEPTED_MARKER = "NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_" + "ACCEPTED"   # must never appear

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_HISTORICAL = "ORACLE INPUT", "DERIVED", "ACCEPTED HISTORICAL REFERENCE"
LABEL_HISTORICAL = "ACCEPTED HISTORICAL REFERENCE - not an NS1d measurement"
LABEL_MEMORY = "INSTANCE MEASUREMENT MEMORY (measured samples, NOT fused surfels)"
LABEL_MAP = "PERSISTENT SURFACE MAP (target-only fusion)"
LABEL_EFFECTIVE = "EFFECTIVE GEOMETRY = map + memory (no dedup, no fusion)"
LABEL_H0 = "CANONICAL H0"
LABEL_FIXED_HEAD = "PHYSICAL HEAD FIXED - NO NEW OBSERVATION"
LABEL_NO_RENDER = "NO-NEW-RENDER CAUSAL REPLAY"
LABEL_ORACLE_CORR = "ORACLE CORRESPONDENCE"
LABEL_GEOMETRY = "DERIVED SPHERICAL GEOMETRY"
LABEL_SEGMENTATION = "ORACLE SEGMENTATION AID"
LABEL_AMBIGUOUS = "AMBIGUOUS ORACLE ID - EXCLUDED"
LABEL_NOT_EXECUTED = "NOT EXECUTED"
LABEL_SCHEDULER = "controller02.schedule_normal (accepted)"
LABEL_M0, LABEL_M1, LABEL_M2 = "M0 accepted NS1c2 (map only)", "M1 own-memory control", "M2 full memory"
LABEL_BOOTSTRAP = "BOOTSTRAP CROSS-TARGET MEMORY: NOT DECIDED BY NS1d"
LABEL_NO_NAME = "no object name used"

# ---- scheduler identity (frozen NS1c / NS1c2 rule) vs memory identity (every positive observed id)
COHERENT = (9, 12, 123, 129, 172, 202, 204, 212, 230, 231)
AMBIGUOUS = (10, 110, 178)
RANK1 = (9, 12, 204, 230, 231)
CONTINUING = 172
BUDGET_EXPECTED = 24
MODES = ("M0", "M1", "M2")

# ---- the accepted upstream runs (read-only)
NS1A_RUN = SHARED / "previews/north-star/ns1a-perfect-bootstrap-round"
NS1B_RUN = SHARED / "previews/north-star/ns1b-recentered-controller-handoff"
NS1C_RUN = SHARED / "previews/north-star/ns1c-coherent-first-scene-switch"
NS1C2_RUN = SHARED / "previews/north-star/ns1c2-controller02-phase-semantics"
NS1B_MANIFEST_SHA256 = "e859fa61489015191f5ef3639ef91766cb26f3f787eb3dd279cfd8516435288c"
NS1C_MANIFEST_SHA256 = "90e2dd4b8a2d287a47f22b4553903a06e0c1059105fec1f954c13da09d426638"
NS1C2_MANIFEST_SHA256 = "0ec6228d96db1bfadc3372c3ce95342ddfa14f7ba2f11d24234c20ed59d2c8c1"
NS1C2_CHECK_SUMMARY_SHA256 = "dae0671d0e9329eff732a08990849c45222d87905fcce75d9cd3d78bfe9243b7"
NS1C2_SCENE_FREEZE_SHA256 = "ea5d046511e9ff7ad960826e3d3f7ce179a07edcfddc85aa62bbae7e4ff91640"
NS1C2_STEPS = 8                       # accepted NS1c2 global steps 0..7 (4 replayed NS1c + 4 new)
NS1C2_PREFIX_STEPS = 4                # steps 0..3: NS1c's measured observations (NS1c run)

# ---- the expected event list (section 6; derived and compared, never forced)
EXPECTED_EVENTS = (
    {"event": 0, "source": "NS1b action 1", "ns1c2_step": None, "target": 172, "patch_id": "ns1b_action_01",
     "world_gaze_deg": (-155.008, 33.636), "observation": "ns1b:"},
    {"event": 1, "source": "NS1c2 step 0", "ns1c2_step": 0, "target": 172, "patch_id": "ns1c_step_00",
     "world_gaze_deg": (-147.585, 37.246), "observation": "ns1c:steps/step-00"},
    {"event": 2, "source": "NS1c2 step 1", "ns1c2_step": 1, "target": 172, "patch_id": "ns1c_step_01",
     "world_gaze_deg": (-145.704, 42.032), "observation": "ns1c:steps/step-01"},
    {"event": 3, "source": "NS1c2 step 2", "ns1c2_step": 2, "target": 172, "patch_id": "ns1c_step_02",
     "world_gaze_deg": (-143.516, 46.782), "observation": "ns1c:steps/step-02"},
    {"event": 4, "source": "NS1c2 step 3", "ns1c2_step": 3, "target": 172, "patch_id": "ns1c_step_03",
     "world_gaze_deg": (-150.152, 48.188), "observation": "ns1c:steps/step-03"},
    {"event": 5, "source": "NS1c2 step 4", "ns1c2_step": 4, "target": 172, "patch_id": "ns1c2_step_04",
     "world_gaze_deg": (-163.040, 31.040), "observation": "run:steps/step-04"},
    {"event": 6, "source": "NS1c2 step 5", "ns1c2_step": 5, "target": 172, "patch_id": "ns1c2_step_05",
     "world_gaze_deg": (-163.874, 26.094), "observation": "run:steps/step-05"},
    {"event": 7, "source": "NS1c2 step 6", "ns1c2_step": 6, "target": 172, "patch_id": "ns1c2_step_06",
     "world_gaze_deg": (-153.654, 39.235), "observation": "run:steps/step-06"},
    {"event": 8, "source": "NS1c2 step 7", "ns1c2_step": 7, "target": 202, "patch_id": "ns1c2_step_07",
     "world_gaze_deg": (-151.282, 22.052), "observation": "run:steps/step-07"},
)
GAZE_EXPECTATION_TOL_DEG = 5e-4       # the expected gazes above are rounded to 3 decimals (the records are exact)
OBS_FILES = ("correspondence/oracle-correspondences.npz", "geometry/epipolar-result.npz",
             "segmentation/local-identity.npz")
FREEZE_FILES = ("freeze/observation-freeze.json", "freeze/correspondence-freeze.json", "freeze/geometry-freeze.json")
CORE_SIZE = 256

# ---- the accepted Controller-01 / Controller-02 history (ACCEPTED HISTORICAL REFERENCE; name-free files only)
C01_RUN = SHARED / "previews/controller-01-full"
C02_RUN = SHARED / "previews/controller-02-classroom-replay"
C01_TRAJECTORY_GLOB = "objects/instance_*/trajectory.partial.json"
C01_TRAJECTORY_DIGEST = "1f7b86558a5e48bc5c3349cde46c90e8f4cd409cff63b445d41a5bc6f37b85b5"   # "rel sha256\n" lines
C01_TRAJECTORY_COUNT = 25
C02_PINS = {"events.json": "fae7e64880f82602c8a868d0598bafab2c6d8da8e0c3f4465440c213d848327c",
            "final-residue.json": "a315714f0452621425fe8463e03d1b1c8e4b70d8ec9778e122ad518f90032c00"}
HISTORICAL_MEMORY = {"looks": 141, "total_points": 7843577, "observed_instances": 33, "localized_objects": 25,
                     "own_target_points": 2274857, "cross_target_points": 5494429, "cross_fraction_pct": 70.7,
                     "unlocated_measured_ids": 8, "unlocated_points": 74291, "natural_reactivations": 2}
HISTORICAL_109 = {"object": 109, "quiet_step": 4, "reactivated_after_step": 7, "trigger": 110, "own_looks": 3,
                  "cross_points_added": 4, "effective_points": (6166, 6170), "cyclopean_eligible": (0, 28),
                  "proposal_after_deg": (-7.0, 14.100000000000001), "serviced_at_step": 134,
                  "service_reason": "natural_reactivation"}

# ---- accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
    "fov3d/reconstruction/measurement_memory.py": "27471ebf7076e5a21b8d23be994425993115b5e379a4dd7f32b7fce09e52ab25",
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
    "tools/fsg6f_frontier.py": "d636c9405d7199164e245ea48618dd7cebb9504074bd98b9136e2bd6f4ff18a1",
    "tools/fsg6f_public.py": "c79f58c9b51f33d4463f2bcfcaa339d79cf20a962b44de9c6cc721cf157cd2fa",
    "tools/multiobject2c_policy.py": "f4d4a08b0098146691ca66d7bb10aeab097f357e59e9d19e43c7bda47e246f8d",
    "tools/classroom_oracle1_epistemic.py": "20d7a4cb6d85109f7c4b165dcccefdd3faf4be600e00113cb2e604d796fca225",
    "tools/classroom_oracle1_public.py": "7b85e59a6e397ed69d3eaec8a6b3790639a6c6ffce596fd0d8d1664c738452bb",
    "tools/classroom_oracle1_matcher.py": "d213c2c7da68a2969b54a095fc7d953d7d16b21f5690cf2fd152197265884afa",
    "tools/fsg3_surface_map.py": "1b9dbeb873105ec9bd9aef9680f67ed18db9a7387d6871d6ed8e6ab58bcb1e01",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/north_star/ns1a_spec.py": "2b43d8b8112a6d738ae212d49aca03ecfeb4c20361128ca51fee498d1c6795d9",
    "tools/north_star/ns1a_core.py": "f32d0aaa986686630d9cc94916719c252dadd817da00886cf38d4a3accf60233",
    "tools/north_star/ns1a_visuals.py": "dadf8c116b968383a9b0df1f242a7f6a0e5a0f52c81e339dd959dc8fdc301155",
    "tools/north_star/ns1b_spec.py": "892a965ec4e7649904743f59b83d129aca22654041f786accfa8173f54391e2d",
    "tools/north_star/ns1b_chart.py": "15b212166b6e3575d286e31613bbc2ab82b3be046f8f4fce330b706a7cb364af",
    "tools/north_star/ns1b_core.py": "bd9b4dea82f7514ca62c4a307a23735675c07a3c06726a8101ccf1b6215522e1",
    "tools/north_star/ns1b_fixtures.py": "8e4eb4007ddb2d956ca5f0290c2dae37f9c68dcbaa6f8edd2ca839f0621b8108",
    "tools/north_star/ns1b_visuals.py": "78d60bb0a82fed1375a837484dbe65bbca18dae624222424215d23d4a3930f5e",
    "tools/north_star/ns1c2_spec.py": "1d49e3e140d2dfc7e716d7345bef33bf065eb6e06da53ab4c84db43c00314aac",
    "tools/north_star/ns1c2_core.py": "f0504eda808f5e15eda0b30f0e25805f22594e1424601cef69b9e2cf4e96faba",
    "tools/north_star/ns1c2_phase.py": "99f6a3da750abe0654ee95085ff387dfbea961ed853f48e85d96fc2a2f6a8acc",
    "tools/north_star/ns1c2_synthetic.py": "11367fd1f3acca1c5712a805559ce8da6575212034ccd97633b1a8e7ac933d31",
}
NS1D_TOOLS = ("ns1d_spec.py", "ns1d_core.py", "ns1d_run.py", "ns1d_synthetic.py", "ns1d_visuals.py", "check_ns1d.py",
              "check_ns1d_corruptions.py")

# ---- run layout and commands
RUN_DEFAULT = SHARED / "previews/north-star/ns1d-cross-target-measurement-memory"
VIS_DEFAULT = SHARED / "visuals/north-star/ns1d-cross-target-measurement-memory"
STAGES = ("source", "synthetic", "known-answer", "events", "replay")
COMMANDS = STAGES + ("visualize",)
FIGURES = ("overview.png", "memory-causal-timeline.png", "effective-geometry-before-after.png",
           "decision-divergence.png", "reactivation.png")
# reads forbidden to every NS1d stage (names, catalogs, seeds, evaluation truth, North-Star reference observations)
FORBIDDEN = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json", "evaluation.json",
             "evaluation/", "evaluation_only", "actions.json", "result.json", "controller-01-full/manifest.json",
             "controller-02-classroom-replay/manifest.json", "breadth-1-classroom-234-spherical-glance",
             "natural-bootstrap-1a-range-connectivity", "natural-bootstrap-1b-foveal-serviceability")
NORTH_STAR_TRUTH = ("reference-observation.npz", "raw_L.exr", "raw_R.exr", "/oracle_aid/")


def event_rel(e: int) -> str:
    return f"replay/events/event-{int(e):02d}"


def probe_rel(mode: str, after_event: int, entity: int) -> str:
    return f"replay/probes/{mode}/after-event-{int(after_event):02d}/e{int(entity):05d}.json"


def state_rel(after_event: int) -> str:
    return f"replay/state-after-event-{int(after_event):02d}.json"


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
