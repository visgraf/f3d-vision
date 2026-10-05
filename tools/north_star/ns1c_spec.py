"""North Star-1c: declared constants, pinned sources, the frozen NS1a / NS1b handoffs and the run layout.

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md.  Standard library only, so both interpreters
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
BASE_COMMIT = "2815bf166689d68cec421fb119635cafaa718d9a"      # accepted main: NS1b accepted + post-NS1b roadmap
NS1B_ACCEPTANCE = "255355108863022f931574dae4b2df8cdd2a772e"
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
CONTRACT_COMMIT = "cb2217db82980c3efd0dfd51cf0f944a5d4f7aa2"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "North Star-1c: Coherent Multi-Entity Control - First Scene Switch"
CONTRACT = "docs/north-star/ns1c-coherent-first-scene-switch-contract.md"
MARKER = "NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
LABEL_CHART = "POLICY CHART C_i"
LABEL_H0 = "CANONICAL H0"
LABEL_FIXED_HEAD = "PHYSICAL HEAD FIXED - POLICY CHART ONLY"
LABEL_FROZEN = "NS1a / NS1b FROZEN INPUT"
LABEL_NO_NAME = "no object name used"
LABEL_ORACLE_CORR = "ORACLE CORRESPONDENCE"
LABEL_GEOMETRY = "DERIVED SPHERICAL GEOMETRY"
LABEL_SEGMENTATION = "ORACLE SEGMENTATION AID"
LABEL_DEFERRED = "DEFERRED AMBIGUOUS ORACLE IDENTITY"
LABEL_NOT_EXECUTED = "NOT EXECUTED"
LABEL_SCHEDULER = "integrated.schedule (accepted)"

# ---- section 5: the coherent seed set (derived; the expectation is compared only AFTER derivation)
EXPECTED_COHERENT = (9, 12, 123, 129, 172, 202, 204, 212, 230, 231)
EXPECTED_DEFERRED = (10, 110, 178)
ELIGIBILITY_FIELDS = ("temporary_entity_id", "initialized", "contributing_patches")
CONTEXT_FIELDS = ("initialized_at_rank", "final_surfels")
DEFERRED_STATE = "DEFERRED_AMBIGUOUS_ORACLE_IDENTITY"
OUTSIDE_STATE = "NOT_INITIALIZED_IN_NS1A"
CONTINUING = 172                      # the current object of the accepted NS1b sequence

# ---- the frozen NS1a handoff (accepted at 37c7e02; read-only)
NS1A_RUN = SHARED / "previews/north-star/ns1a-perfect-bootstrap-round"
NS1A_PINS = {
    "freeze/observation-freeze.json": "46f0a22eab852b3c5750420ed993a453cd6b1e6c4d0cd0d96ce167883b87576d",
    "freeze/geometry-freeze.json": "7b0ae64dacc1d6e12d893a118e017220a349a4062be6474e9fbf82a58ab0452b",
    "freeze/seed-set-freeze.json": "4ee36a1aa39525a7faa0132877d5cede14df185ae5607dbe73615a3ad2357173",
    "seeds/seed-set.json": "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a",
    "seeds/entity-maps.npz": "621d8902948656221d876f3642c78963b075a0ce5a5ae1227da3e2f65620f605",
    "source/nb1c-gaze-list.json": "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062",
    "observations/acquisition-run.json": "1bbf03bc15dd5401c7f49d21b4e08492024391a43d0c73bf96d099c84db15dbf",
}
NS1A_SEED_SET = "seeds/seed-set.json"
NS1A_MAPS = "seeds/entity-maps.npz"
NS1A_GAZE_LIST = "source/nb1c-gaze-list.json"
NS1A_CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
NS1A_RANK_GAZES = ((1, 76.75, 7.75), (2, -2.75, 75.75), (3, 75.25, -25.75), (4, 38.25, -61.75), (5, 179.75, 34.75),
                   (6, -156.25, 28.75))

# ---- the accepted NS1b run (accepted at 2553551; read-only): the post-action state of entity 172
NS1B_RUN = SHARED / "previews/north-star/ns1b-recentered-controller-handoff"
NS1B_PINS = {
    "manifest.json": "e859fa61489015191f5ef3639ef91766cb26f3f787eb3dd279cfd8516435288c",
    "check-summary.json": "146438bd6b95933b678d49383efdafac201329ce60550bd1d8ca47d7a5c7bed7",
    "fusion/fused-target-map.npz": "bf831ad5d49b226b878c73af80b19330620bfe201e85b7464a8bb63c3b4aad0c",
    "fusion/fusion.json": "6401f0c23554eef5dbb8197342cc75141d496c9603ed2a714f797516ae94c45e",
    "post/evidence.npz": "a96791631906e43d4598b7b6de7db66cdb52303835bdeb1fe533106e8b351f00",
    "post/controller-state.npz": "337c070525131bdbec4c061eaa85b389594cf999b468da399d8535058b1bd7f0",
    "post/post-action-probe.json": "2918e146294dace627acc1b8b097f5b4e5a072ec0c98cf0e2d65718b062f8bac",
    "context/controller-state.npz": "ceebc7250eb046a577bc3b024ab30ac1002141aea0e4ebd17a17571d41bba9cf",
    "context/evidence.npz": "744c91a440100bafe02aa3c9def52e61d965733bdb63df39ab2dca9745f348dd",
    "context/context.json": "8df0124fa8017efafd4234f56a655759671cb7c1ebb0cd2e101c100d8bd23248",
    "context/target-map-H0.npz": "e11c2d08865590da39e813529501b7f5feb9e19baa4b25cfbc30215aa3c10f6b",
    "observation/acquisition/calibration.json": "a4b2ae6732066361ccdd4c9731a3735560e48f7a41392486c214e31db779cb82",
    "observation/acquisition/rgb-observation.npz": "23a1208f2ffbcd51bd25d94530c1202d2bf45242203fcb2c845a816f7cf378b2",
    "observation/oracle_aid/reference-observation.npz":
        "8764de530c7fa97469f44af86598d0602641bf79f3358341c3e1cc41d7a3ca14",
    "freeze/observation-freeze.json": "0fbd0e8d8326b5599d83c10a4281fda057b6b32e1e9bd6dfdf53aa6890ca8116",
    "chart/policy-chart.json": "8adefe86726fbe95d2e3782d9cf26db120959df5a746f061d87cfe038bcdc5df",
    "probe/decision.json": "0a4148774a7fdbf09ecf0078ee29cb806f97405994eee3fe9470b7a2e6c3cb63",
}
NS1B_172 = {"map_surfels": 21243, "own_looks": 2, "visited": [[0.0, 0.0], [0.0, -5.0]], "gaze": [0.0, -5.0],
            "patch_ids": ["nb1c_gaze_06", "ns1b_action_01"], "rank": 6}
NS1B_POST_EXPECTED = {"state": "ACTIONABLE", "source": "fsg6f", "local_gaze_deg": [-5.0, -10.0], "admissible": True,
                      "reason": "novel_support_in_predicted_cores", "novel_service_count": 22}


def ns1a_rank_dir(rank: int) -> str:
    return f"rank-{int(rank):02d}"


def ns1a_obs(rank: int, domain: str, name: str) -> str:
    return f"observations/{ns1a_rank_dir(rank)}/{domain}/{name}"


def map_key(entity: int, field: str) -> str:
    return f"e{int(entity):05d}_{field}"


MAP_FIELDS = ("xyz_h", "rgb", "instance_id", "support_count", "provenance_mask", "patch_ids")

# ---- sections 7-8: charts and the adapter (the accepted NS1b construction and tolerances)
CHART_SINGULAR_MIN = 1e-6
ORTHO_TOL = 1e-12
CENTRE_TOL_DEG = 1e-9
ROUNDTRIP_TOL = 1e-12
GAZE_ROUNDTRIP_TOL_DEG = 1e-9
PROBE_ROTATIONS_DEG = (37.0, -61.0)                # the NS1b in-probe baseline-rotation invariance, per entity

# ---- sections 12-13: service states, watchdog, scheduler
WATCHDOG_EXPECTED = 24                              # read live from controller01.WATCHDOG; this is the expectation
SERVICE_ACTIONABLE, SERVICE_QUIET, SERVICE_BLOCKED = "ACTIONABLE", "QUIET", "BLOCKED"
TERMINAL_LABELS = {"Stop": "COHERENT_SUBSET_QUIESCENT", "Incomplete": "COHERENT_SUBSET_INCOMPLETE"}
FORBIDDEN_MARKER = "SCENE" + "_CLOSED"              # never emitted by NS1c (built so the literal is not in the source)

# ---- section 15: the action observation (the North-Star standard, inherited from NS1a / NS1b)
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
STEP_BUDGET_PROJECTION_S = 1800.0

# ---- section 16: fusion (accepted persistent-map machinery)
MIN_POINTS = 100
ASSOCIATION_RADIUS_M = 0.012
HASH_CELL_M = 0.012
FUSION_FRAME = "H0"


def patch_id(step: int) -> str:
    return f"ns1c_step_{int(step):02d}"


def step_dir(step: int) -> str:
    return f"steps/step-{int(step):02d}"


def scene_state_rel(label: str) -> str:
    return f"scene/state-{label}.json"


# ---- accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
    "tools/fsg6f_frontier.py": "d636c9405d7199164e245ea48618dd7cebb9504074bd98b9136e2bd6f4ff18a1",
    "tools/fsg6f_public.py": "c79f58c9b51f33d4463f2bcfcaa339d79cf20a962b44de9c6cc721cf157cd2fa",
    "tools/multiobject2c_policy.py": "f4d4a08b0098146691ca66d7bb10aeab097f357e59e9d19e43c7bda47e246f8d",
    "tools/classroom_oracle1_epistemic.py": "20d7a4cb6d85109f7c4b165dcccefdd3faf4be600e00113cb2e604d796fca225",
    "tools/classroom_oracle1_public.py": "7b85e59a6e397ed69d3eaec8a6b3790639a6c6ffce596fd0d8d1664c738452bb",
    "tools/classroom_oracle1_matcher.py": "d213c2c7da68a2969b54a095fc7d953d7d16b21f5690cf2fd152197265884afa",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg3_surface_map.py": "1b9dbeb873105ec9bd9aef9680f67ed18db9a7387d6871d6ed8e6ab58bcb1e01",
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
    "fov3d/_compat.py": "014d1fb8c9cfc4c80fbf015c698e8fc706a16b79a0eda2b916e8727d9e61a870",
    "fov3d/__init__.py": "7a514a1b8ea6ba8b61f618f500e15e36a288cede82f942358ce79353df0eb5fc",
    "tools/active_bootstrap/ab1b_oracle.py": "51e2ee556a4a3576d00cd99255793212ad5efcb50b1e15ed292740d8c24aa231",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/north_star/ns1a_spec.py": "2b43d8b8112a6d738ae212d49aca03ecfeb4c20361128ca51fee498d1c6795d9",
    "tools/north_star/ns1a_core.py": "f32d0aaa986686630d9cc94916719c252dadd817da00886cf38d4a3accf60233",
    "tools/north_star/ns1a_render.py": "f5848706902d7190d2882f29924784f0350b4aad9ee7edee09e33ed746e5d1aa",
    "tools/north_star/ns1a_visuals.py": "dadf8c116b968383a9b0df1f242a7f6a0e5a0f52c81e339dd959dc8fdc301155",
    "tools/north_star/check_ns1a.py": "5a8f1c26a7b19b60581c6b2fb982830318512c09cac0ef9d0787e777b18304f1",
    "tools/north_star/ns1b_spec.py": "892a965ec4e7649904743f59b83d129aca22654041f786accfa8173f54391e2d",
    "tools/north_star/ns1b_chart.py": "15b212166b6e3575d286e31613bbc2ab82b3be046f8f4fce330b706a7cb364af",
    "tools/north_star/ns1b_core.py": "bd9b4dea82f7514ca62c4a307a23735675c07a3c06726a8101ccf1b6215522e1",
    "tools/north_star/ns1b_visuals.py": "78d60bb0a82fed1375a837484dbe65bbca18dae624222424215d23d4a3930f5e",
}
# the coarse 360 RGB backdrop of overview panel A (RGB only; read by `visualize` alone, as the accepted NS1a figures do)
NB1A_RGB = (SHARED / "previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz",
            "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e")
SURFACE_FRONTIER = {
    "component_step_deg": 5.0, "yaw_min_deg": -25.0, "yaw_max_deg": 25.0, "pitch_min_deg": -20.0,
    "pitch_max_deg": 20.0, "edge_band_fraction": 0.04, "edge_object_fraction_min": 0.15, "voxel_m": 0.025,
    "neighbour_radius_m": 0.065, "minimum_neighbours": 6, "tangent_asymmetry_min": 0.18, "lookahead_m": 0.12,
    "current_view_margin_deg": 1.0, "minimum_candidate_frontier_support": 8, "alignment_cos_min": 0.5,
    "map_extent_quantile": 0.01,
}
FSG6F_FUSION = {"association_radius_m": 0.012, "hash_cell_m": 0.012}
CYCLOPEAN_GRID_DEG = 0.10
FSG6F_OBJECT_ID = 141
FSG6F_VERGENCE_M = 2.10
NS1C_TOOLS = ("ns1c_spec.py", "ns1c_core.py", "ns1c_render.py", "ns1c_run.py", "ns1c_synthetic.py", "ns1c_visuals.py",
              "check_ns1c.py", "check_ns1c_corruptions.py")

# ---- section 26: run layout and commands
RUN_DEFAULT = SHARED / "previews/north-star/ns1c-coherent-first-scene-switch"
VIS_DEFAULT = SHARED / "visuals/north-star/ns1c-coherent-first-scene-switch"
ONCE = ("source", "synthetic", "eligibility", "charts", "contexts", "initial-probe")
STEP = ("schedule", "preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
        "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "fuse", "update")
COMMANDS = ONCE + STEP + ("loop", "visualize")
FIGURES = ("overview.png", "scene-scheduler-timeline.png", "multi-entity-growth-3d.png",
           "controller-vs-northstar-support.png")

OBS_ACQ = "observation/acquisition"
OBS_AID = "observation/oracle_aid"
CATALOG_REL = "observation/evaluation_only/instance-catalog.json"
ACQ_RUN_REL = "observation/acquisition-run.json"
OBS_ACQ_FILES = ("calibration.json", "rgb-observation.npz", "acquisition.json")
OBS_AID_FILES = ("raw_L.exr", "raw_R.exr", "reference-observation.npz")
SEGMENTATION_MEMBERS = ("instance_L",)
CORE_SIZE = 256
CORE_ORIGIN = 192
# reads forbidden to every NS1c stage (names, catalogs, Controller-01 bootstrap seeds, evaluation, Breadth-1, NB1a/b)
FORBIDDEN = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json", "evaluation.json",
             "evaluation/", "evaluation_only", "natural-bootstrap-1a-range-connectivity",
             "natural-bootstrap-1b-foveal-serviceability", "breadth-1-classroom-234-spherical-glance",
             "controller-01a-terminal-audit", "controller-01b-single-continuation",
             "controller-01c-frontier-action-correspondence", "controller-01-full")


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
