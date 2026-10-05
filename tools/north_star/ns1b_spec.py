"""North Star-1b: declared constants, pinned sources, the frozen NS1a handoff and the run layout.

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md.  Standard library only, so both interpreters
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
BASE_COMMIT = "889373d9c174c1c63ebc8d2f79847dbec281f2e8"      # accepted main: NS1a accepted + post-NS1a roadmap
NS1A_ACCEPTANCE = "37c7e026f2ab514be392cd845d390fab2a2d86fc"
CONTRACT_COMMIT = "1e641e66eac46be551b425d2f14a06e9607d533f"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "North Star-1b: Recentered Local-Controller Handoff - One Action"
CONTRACT = "docs/north-star/ns1b-recentered-controller-handoff-contract.md"
MARKER = "NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
LABEL_CHART = "POLICY CHART C"
LABEL_H0 = "CANONICAL H0"
LABEL_FIXED_HEAD = "PHYSICAL HEAD FIXED - POLICY CHART ONLY"
LABEL_FROZEN = "NS1a FROZEN INPUT"
LABEL_NO_NAME = "no object name used for selection"
LABEL_ORACLE_CORR = "ORACLE CORRESPONDENCE"
LABEL_GEOMETRY = "DERIVED SPHERICAL GEOMETRY"
LABEL_SEGMENTATION = "ORACLE SEGMENTATION AID"

# ---- section 5: the frozen NS1a handoff (accepted at 37c7e02; read-only)
NS1A_RUN = SHARED / "previews/north-star/ns1a-perfect-bootstrap-round"
NS1A_FREEZES = {
    "freeze/observation-freeze.json": "46f0a22eab852b3c5750420ed993a453cd6b1e6c4d0cd0d96ce167883b87576d",
    "freeze/geometry-freeze.json": "7b0ae64dacc1d6e12d893a118e017220a349a4062be6474e9fbf82a58ab0452b",
    "freeze/seed-set-freeze.json": "4ee36a1aa39525a7faa0132877d5cede14df185ae5607dbe73615a3ad2357173",
}
NS1A_SEED_SET = "seeds/seed-set.json"
NS1A_SEED_SET_SHA256 = "e2ff1ba362ab1a1fa69268619a126153a921f26c4139f53ec4b9c9b87cfe2d8a"
NS1A_MAPS = "seeds/entity-maps.npz"
NS1A_MAPS_SHA256 = "621d8902948656221d876f3642c78963b075a0ce5a5ae1227da3e2f65620f605"
NS1A_GAZE_LIST = "source/nb1c-gaze-list.json"
NS1A_GAZE_LIST_SHA256 = "785d02a7485562252eef923c6c9ad4607477efc8b5813db0a22e5cbdf0295062"
NS1A_CATALOG_SEAL = "a0849b21f2888e6dd57cbab8766184db4e5aa1ee3439bbd574be776f65b9c612"
NS1A_ACQ_RUN = "observations/acquisition-run.json"
NS1A_ACQ_RUN_SHA256 = "1bbf03bc15dd5401c7f49d21b4e08492024391a43d0c73bf96d099c84db15dbf"
NS1A_RANK_GAZES = ((1, 76.75, 7.75), (2, -2.75, 75.75), (3, 75.25, -25.75), (4, 38.25, -61.75), (5, 179.75, 34.75),
                   (6, -156.25, 28.75))
EXPECTED_TARGET = 172          # the mandate's expectation; compared AFTER the rule has derived its answer
EXPECTED_RANK = 6
SELECTION_FIELDS = ("temporary_entity_id", "initialized", "initialized_at_rank", "contributing_patches",
                    "final_surfels")   # the ONLY seed-set fields the selection rule may read


def ns1a_rank_dir(rank: int) -> str:
    return f"rank-{int(rank):02d}"


def ns1a_obs(rank: int, domain: str, name: str) -> str:
    return f"observations/{ns1a_rank_dir(rank)}/{domain}/{name}"


def map_key(entity: int, field: str) -> str:
    return f"e{int(entity):05d}_{field}"


MAP_FIELDS = ("xyz_h", "rgb", "instance_id", "support_count", "provenance_mask", "patch_ids")

# ---- section 6: the policy chart
BASELINE_H0 = (1.0, 0.0, 0.0)
CHART_SINGULAR_MIN = 1e-6      # |b - (b.g0) g0| below this is a HARD STOP (no other axis is invented)
ORTHO_TOL = 1e-12
CENTRE_TOL_DEG = 1e-9
ROUNDTRIP_TOL = 1e-12          # m (points) and rad (directions)
GAZE_ROUNDTRIP_TOL_DEG = 1e-9

# ---- section 7: the frame adapter (exactly three substitutions)
ADAPTER_SUBSTITUTIONS = (
    ("P1", "tools/fsg6f_frontier.py", "_project_rectified_core"),
    ("P2", "tools/classroom_oracle1_epistemic.py", "_rectified_core_directions_h"),
    ("P3", "fov3d/experiments/classroom_oracle/controller02.py", "predicted_calibration"),
)

# ---- section 8: covariance known answers
FLOAT_TOL = 1e-9                     # where floating point is unavoidable (discrete fields are exact)
BASELINE_ROTATIONS_DEG = (23.0, -47.0, 131.0)      # synthetic / replay rigid rotations about +X
PROBE_ROTATIONS_DEG = (37.0, -61.0)                # in-probe invariance of the NS1b decision
OFF_AXIS_ROTATIONS = ((0.3, -0.4, 0.5, 0.71), (-0.6, 0.2, 0.7, -1.9))   # (axis xyz, angle rad): chart-only tests
# K3q: the accepted Controller-01 probe of object 112 after global step 21 (its saved summary; QUIET)
K3Q_SUMMARY = {"state": "QUIET", "effective_points": 44632,
               "fsg6f": {"candidates": 0, "consensus_rejected_candidates": 0, "frontier_boundary_resolved_count": 176,
                         "frontier_map_resolved_count": 3, "frontier_open_count": 23, "frontier_raw_count": 202,
                         "next_gaze_deg": None, "reason": "no_frontier", "stop": True},
               "cyclopean": {"eligible_cells": 0, "map_support_cells": 3052, "never_observed_cells": 168843,
                             "next_gaze_deg": None, "reason": "attention_complete", "shoreline_cells": 486,
                             "stop": True}}
C01_RUN = SHARED / "previews/controller-01-full"
C01_ACCEPTED = {"manifest.json": "d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91",
                "actions.json": "12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd"}
# sha256 over "relative-path sha256" lines of the 223 name-free accepted files the K2-K4 replay reads
C01_FIXTURE_DIGEST = "5527778a793fb6c648c416bf2c2b896a675b0abe60a91fe82f5d81413716d6a5"
C02_RUN = SHARED / "previews/controller-02-classroom-replay"
C02_FINAL_RESIDUE = "final-residue.json"
K_FIXTURES = {
    "K2": {"object": 112, "after_global_step": 18, "revision": [1, 26285], "kind": "fsg6f_continue",
           "trajectory_step": 1, "gaze": [9.0, 10.75]},
    "K3": {"object": 112, "after_global_step": 20, "revision": [3, 32438], "kind": "cyclopean_fixation",
           "trajectory_step": 3, "gaze": [20.6, 9.700000000000003]},
    "K3q": {"object": 112, "after_global_step": 21, "revision": [4, 36183], "kind": "quiet"},
    "K4": {"object": 210, "after_global_step": 140, "revision": [24, 1774969], "kind": "controller02_gate",
           "gaze": [7.600000000000001, 18.200000000000003], "verdict": "no_novel_serviceable_support"},
}

# ---- sections 9-10: context and probe
TARGET_PROFILE = "full"
NS1B_SENSOR = "ns1a_core.planned_calibration: full, IPD 0.063 m, vergence 2.10 m, AB1a head pose, baseline_projected"

# ---- section 12: the one observation (the North-Star standard, inherited from NS1a)
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

# ---- section 14: fusion (accepted persistent-map machinery)
MIN_POINTS = 100
ASSOCIATION_RADIUS_M = 0.012
HASH_CELL_M = 0.012
IDEMPOTENCE_ATOL = 1e-10
ACTION_PATCH_ID = "ns1b_action_01"
FUSION_FRAME = "H0"

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
}
# the accepted policy constants, as the sealed code must still hold them (checked at run time and by the checker)
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
NS1B_TOOLS = ("ns1b_spec.py", "ns1b_chart.py", "ns1b_core.py", "ns1b_render.py", "ns1b_run.py", "ns1b_synthetic.py",
              "ns1b_fixtures.py", "ns1b_visuals.py", "check_ns1b.py", "check_ns1b_corruptions.py")

# ---- section 21: run layout and commands
RUN_DEFAULT = SHARED / "previews/north-star/ns1b-recentered-controller-handoff"
VIS_DEFAULT = SHARED / "visuals/north-star/ns1b-recentered-controller-handoff"
ALWAYS = ("source", "synthetic", "select", "chart", "covariance", "context", "probe")
CASE_B = ("preflight", "acquire", "freeze-observation", "perfect-correspondence", "freeze-correspondence",
          "spherical-geometry", "freeze-geometry", "local-oracle-segmentation", "fuse", "post-probe")
COMMANDS = ALWAYS + CASE_B + ("visualize",)
CANONICAL = ALWAYS + CASE_B
FIGURES_ALWAYS = ("overview.png", "chart-covariance.png")
FIGURE_ACTION = "first-controller-action-3d.png"

OBS_ACQ = "observation/acquisition"
OBS_AID = "observation/oracle_aid"
CATALOG_REL = "observation/evaluation_only/instance-catalog.json"
ACQ_RUN_REL = "observation/acquisition-run.json"
OBS_ACQ_FILES = ("calibration.json", "rgb-observation.npz", "acquisition.json")
OBS_AID_FILES = ("raw_L.exr", "raw_R.exr", "reference-observation.npz")
SEGMENTATION_MEMBERS = ("instance_L",)
CORE_SIZE = 256
CORE_ORIGIN = 192
QUANTILES = {"min": 0.0, "median": 0.5, "p95": 0.95, "max": 1.0}
# reads forbidden to every NS1b stage (names, catalogs, Controller-01 bootstrap seeds, evaluation, Breadth-1, NB1a/b)
FORBIDDEN = ("instance-catalog.json", "instance_catalog.json", "seeds.json", "object-stats.json", "evaluation.json",
             "evaluation/", "evaluation_only", "natural-bootstrap-1a-range-connectivity",
             "natural-bootstrap-1b-foveal-serviceability", "breadth-1-classroom-234-spherical-glance",
             "controller-01a-terminal-audit", "controller-01b-single-continuation",
             "controller-01c-frontier-action-correspondence")


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
