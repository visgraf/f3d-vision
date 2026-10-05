"""Active Bootstrap-1d2: declared constants, pinned sources and configurations (4096-spp observation-quality control).

Contract: docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md.  Standard library only, so both
interpreters (Blender's and the host .venv) can import it.  The checker keeps its own literal copies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "22f538f8eb2dad69d45b7fc3183fbcc2ee861d55"   # accepted main: AB1d accepted + post-AB1d roadmap
CONTRACT_COMMIT = "6f5b757754230429c89fd3d358316a5180b6d623"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "Active Bootstrap-1d2: 4096-spp Observation-Quality Control"
CONTRACT = "docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md"
MARKER = "ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"

# ---- section 4: the one intentional change
SPP = 4096
ACCEPTED_SPP = 256
SEEDS = {"L": 2111, "R": 2112}
DEVICE = "OPTIX"
RAW_SIZE = 640
CORE_SIZE = 256
CORE_ORIGIN = (RAW_SIZE - CORE_SIZE) // 2
CALIBRATION_TOL = 1e-9          # accepted (ab1a / ab1c)
EYE_POSE_TOL = 1e-6             # accepted camera-pose tolerance
GAZES = ("gaze-1", "gaze-2", "gaze-3")
GAZE_TABLE = {"gaze-1": {"row": 191, "col": 322, "yaw_deg": -18.75, "pitch_deg": -5.75},
              "gaze-2": {"row": 166, "col": 373, "yaw_deg": 6.75, "pitch_deg": 6.75},
              "gaze-3": {"row": 190, "col": 397, "yaw_deg": 18.75, "pitch_deg": -5.25}}

# ---- section 3a: the accepted AB1c 256-spp observations (pinned through the accepted ab1d_spec.OBS_PINS)
A1C_RUN = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
A1C_MANIFEST = ("manifest.json", "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a")
A1C_CATALOG = ("observations/evaluation_only/instance-catalog.json",
               "948dd8d4c1824e5acf6a3a179b7a8a6d4b39134dda041861dbb8193fe3d3df4a")
A1C_CALIBRATION = {"gaze-1": "ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
                   "gaze-2": "ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
                   "gaze-3": "085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd"}
A1C_RGB = {"gaze-1": "d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f",
           "gaze-2": "297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d",
           "gaze-3": "5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c"}
A1C_ACQUISITION = {"gaze-1": "d1ca822aa2ca49e32fd59466736d03408e7549cac1a452ded6bc19806d32c27b",
                   "gaze-2": "59443c35284625fca1792b3bfe5cabb22e6635cb27c05bd274ab7501e93beeac",
                   "gaze-3": "68fd96d8d541095ff8623b98dd74e22a8161bf593611739e6ea5cad126a52abd"}
BLEND = "scenes/classroom/classroom_eye.blend"
BLEND_SHA256 = "dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc"
BLENDER = "blender"
HEAD_POSE_SOURCE = (SHARED / "previews/controller-01-full/bootstrap/seeds.json",
                    "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f")

# ---- section 3c: the accepted AB1d products (the paired 256-spp reference)
A1D_RUN = SHARED / "previews/active-bootstrap/ab1d-safe-forward-natural-correspondence"
A1D_VIS = SHARED / "visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence"
A1D_PINS = {
    "manifest.json": "3f6a837d6529b8fc1a6680aeb18446c6c9ecbe0e67e5304a4e4154837161b838",
    "match/correspondence-freeze.json": "006c9116b5127b63efb218d179aef4283d8a0466f631d358a5a2082d72d0c5ab",
    "freeze/geometry-freeze.json": "0c2d7b0a3e847085451279a96431541b4ba8998b35c03e5f099597729cc84730",
    "evaluation/evaluation-summary.json": "692f49d7c6de6b7babec1fd9775102d933a2f3c97f8e545c0fa164029c187345",
    "match/gaze-1/matcher-record.npz": "9a47412712d9e3205df250fdffb2b5e6b4560380269d5b5cab85ff44d292425e",
    "match/gaze-2/matcher-record.npz": "541e3a5c6a4f40314f3b9b46df04b4f8a9c40c92684595a1b770431107cf5fc7",
    "match/gaze-3/matcher-record.npz": "5034fc6f59db5931b9e5c790332736001d94c5d7967d7e6ce61ed842a38477f9",
    "match/gaze-1/natural-correspondences.npz": "bf9382ae4be385d5b926bac039fb75b8e6b09d7e53a508a0be95abd9f7737e35",
    "match/gaze-2/natural-correspondences.npz": "844c60c6db9b4a69416f887b67db10dc0b24c2cd51a66083bf9b57cab7d743d2",
    "match/gaze-3/natural-correspondences.npz": "102e5b04112fafe4d22739e209f50a77f1e2f00a0dec5484d3ede53dbcf0a12a",
    "spherical/gaze-1/epipolar-result.npz": "646e45282a36f2ed31ed0cbf0caa294fea004ea143036ec30e7217a04014c46f",
    "spherical/gaze-2/epipolar-result.npz": "2c8940d97609c5bb5adfd17490c215fb1286ae47996df1431eddd641e3ef2121",
    "spherical/gaze-3/epipolar-result.npz": "5a49085396fc579fc0a269f1e284332b247428e8447f9d50a4b19b787b3e360f",
    "evaluation/gaze-1/evaluation-result.npz": "c849e72d56ca2f30765cd74ac86d7acb63217e2bec2c5920123182db6928142f",
    "evaluation/gaze-2/evaluation-result.npz": "b794127d6fb36af60a126bd9fc7dbbe7aa9dafb80c26377cd52bdadfb4fcfee2",
    "evaluation/gaze-3/evaluation-result.npz": "e8665c2b3e6987d69a3778883136a007cce76f81f38c1c28b4d6ac7179121c59",
}
A1D_VIS_MANIFEST = (A1D_VIS / "visuals-manifest.json", "c7391c7b3516afed4dc728381f8ffaf8fa4fac4697661ff3aa2781c5ac397ecf")

# ---- section 3d: accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
    "tools/active_bootstrap/ab1d_match.py": "dd1ac243d1da09635e12edb87d0d402f169d49e016ac3f35ed5d1572ec255ffd",
    "tools/active_bootstrap/ab1d_spec.py": "fc50a7306ed5e384878c61574c250b3534e1ac4b3a2e6936c153f805aba7b346",
    "tools/active_bootstrap/ab1d_run.py": "9df2981ba55041e7cebdb34061b5cb565d65734b78962318931b4dcb482a7292",
    "tools/active_bootstrap/check_ab1d.py": "600106c06138024a36dc95043aa5d00daf548e0c27ccf728817f6dffc3e12862",
    "tools/active_bootstrap/ab1d_visuals.py": "33a8d9b0cf6c412c3e5c11bfb93f498fea9faca0939422bb7ff1391d912fdf53",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1c_render.py": "a1281a2019dca259c490cba9955cf2b5ed61cca4db167a1a2f7a03dc5f315b87",
    "tools/active_bootstrap/ab1c_spec.py": "53d1b7228b30883db715f3fc33a65893aa7708656c2881f2a31eef1a3ac77b1a",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1b_visuals.py": "6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee",
    "tools/active_bootstrap/ab1c_visuals.py": "28054811eca774883753c2499d135cdabae37b32f6f014432bf1057dcab71a30",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/classroom_oracle/breadth1_visuals.py": "61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c",
}
MATCHER_CODE = ("tools/active_bootstrap/ab1d_match.py", "tools/active_bootstrap/ab1d_spec.py",
                "tools/active_bootstrap/ab1d_run.py", "tools/fsg_geometry.py", "tools/fsg_stereo.py",
                "tools/active_bootstrap/ab1b_geometry.py", "tools/active_bootstrap/ab1b_spec.py",
                "tools/natural_bootstrap/nb1a_guard.py")
RENDER_CODE = ("tools/active_bootstrap/ab1d2_render.py", "tools/active_bootstrap/ab1d2_spec.py",
               "tools/active_bootstrap/ab1a_render.py", "tools/active_bootstrap/ab1a_spec.py",
               "tools/classroom_oracle1_render.py", "tools/render_foveated.py", "tools/bl_common.py",
               "tools/exr_lite.py", "tools/fsg_geometry.py")
# the accepted AB1d matcher constants (section 9): the AB1d2 identity check compares the live matcher with these
MATCHER_CONSTANTS = {"PATCH": 5, "PATCH_HALF": 2, "LUMA": (0.2126, 0.7152, 0.0722), "MIN_LOCAL_STD_U8": 0.5,
                     "SPACING_PX": 1.0, "TIE_EPS": 1e-12, "TOP_K": 8, "PEAK_SEPARATION_PX": 3.0,
                     "REFINE_BOUND_SAMPLES": 0.75, "Z_EPS": 1e-12, "DEN_EPS": 1e-12}

# ---- section 7: render-setting equivalence classes
REC_MUST_EQUAL = ("schema", "truth", "statement", "blender", "gaze_yaw_pitch_deg", "profile", "tangent_frame", "ipd_m",
                  "vergence_distance_m", "device", "render_seeds_lr", "seed_rule", "exr_channels_lr", "settings",
                  "camera_matrix_world_lr", "calibration_sha256", "rgb_observation_arrays", "evaluation_only",
                  "complete", "canonical", "ab1c_gaze", "ab1c_rank", "eye_pose", "calibration_max_abs_diff_from_planned")
REC_EXPECTED = ("spp", "primary_camera_samples", "render_seconds_lr", "rgb_observation_sha256", "created_utc")
REC_LABEL = ("experiment", "action_source", "blend", "observation_quality_control")
EXR_MUST_EQUAL = ("BlenderMultiChannel", "Camera", "Scene", "Software", "Frame", "Time", "channels", "colorInteropID",
                  "compression", "dataWindow", "displayWindow", "lineOrder", "pixelAspectRatio", "screenWindowCenter",
                  "screenWindowWidth", "xDensity")
EXR_LAYER = "interior"          # the Classroom view layer; Cycles names its per-layer attributes cycles.<layer>.<key>
EXR_SAMPLES = f"cycles.{EXR_LAYER}.samples"
EXR_TIMING = ("Date", "RenderTime")
EXR_LAYER_TIMING = ("render_time", "synchronization_time", "total_time")
EXR_LABEL = ("File",)
EXR_HEADER_BYTES = 65536

# ---- section 10: calibration-derived matcher fields that must be identical (bitwise) between 256 and 4096
GEOMETRY_FIELDS = ("left_core_row", "left_core_col", "uv_L", "theta_L", "phi_L", "q_inf", "line_dir", "line_l",
                   "k_first", "k_last", "candidate_count", "valid_left_patch")

# ---- sections 14-17: paired evaluation (declared before any result)
EQUAL_TOL_PX = 1e-9
ZNCC_EQUAL_TOL = 1e-12
METRIC_EQUAL_TOL_M = 1e-12
GOOD_PX = 1.0
ORACLE_PEAK_RADIUS_PX = 1.5        # = ab1d_spec.ORACLE_PEAK_RADIUS_PX (verified by ``source``)
MAD_SCALE = 1.4826
HP_SCALE = 1.25 ** 0.5
QUANTILES = {"min": 0.0, "p05": 0.05, "p10": 0.10, "p25": 0.25, "median": 0.5, "p75": 0.75, "p90": 0.90, "p95": 0.95,
             "p99": 0.99, "max": 1.0}
TRANSITION_KEYS = ("bad_to_good", "good_to_good", "good_to_bad", "bad_to_bad")
RENDER_BUDGET_S = 1800

# ---- section 21: rehearsal (factory-startup synthetic room; never Classroom)
REHEARSAL_GAZE = "gaze-1"
REHEARSAL_SPPS = (ACCEPTED_SPP, SPP)

# ---- section 26: commands, run layout
RUN_DEFAULT = SHARED / "previews/active-bootstrap/ab1d2-4096spp-observation-quality"
VIS_DEFAULT = SHARED / "visuals/active-bootstrap/ab1d2-4096spp-observation-quality"
COMMANDS = ("source", "preflight-tests", "rehearse", "preflight", "render-4096", "freeze-observation", "match",
            "freeze-correspondence", "spherical", "freeze-geometry", "evaluate-paired", "visualize")
CANONICAL = ("source", "preflight", "render-4096", "freeze-observation", "match", "freeze-correspondence", "spherical",
             "freeze-geometry", "evaluate-paired")
ORDER = ("source", "preflight-tests", "rehearse", "preflight", "render-4096", "freeze-observation", "match",
         "freeze-correspondence", "spherical", "freeze-geometry", "evaluate-paired", "visualize")
FIGURES = ("overview.png", "paired-cost-landscapes.png", "correspondence-improvement.png", "observation-comparison.png",
           "metric-comparison.png", "confidence-change.png")


def a1c(rel: str) -> Path:
    return A1C_RUN / rel


def a1d(rel: str) -> Path:
    return A1D_RUN / rel


def a1c_acq(g: str, name: str) -> Path:
    return A1C_RUN / f"observations/{g}/acquisition/{name}"


def obs_rel(g: str, name: str) -> str:
    return f"observations/{g}/acquisition/{name}"


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
