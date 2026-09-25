#!/usr/bin/env python3
"""Read-only probe of the runtime the Classroom-Oracle-1 baseline was sealed on.

    .venv/bin/python tools/check_runtime_environment.py            # exit 1 on a REQUIRED failure
    .venv/bin/python tools/check_runtime_environment.py --no-blender

Installs nothing and writes nothing (bytecode writing is disabled; project modules are
located with importlib.util.find_spec, never executed).  External programs are only asked
for their version / device list.  Blender is started with --factory-startup so user
preferences are neither read nor saved.

REQUIRED checks decide the exit code:
  * this interpreter is Python 3.12 and not a conda interpreter;
  * numpy / opencv-python-headless / pillow match the pins in requirements*.txt;
  * `blender` is Blender 5.2.1;
  * Cycles in that Blender lists an OPTIX device (the golden contract runs --device OPTIX);
  * every project module of the golden runtime closure resolves inside this repository,
    both for the host interpreter and inside Blender, and none resolves to the legacy repo.
INFORMATIONAL checks are reported only: interpreter paths, OpenEXR, nvidia-smi, ffmpeg.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
LEGACY_MARKERS = ("/fov-3d-vision/", "/fov-3d-vision-core-stage/")

# The 17-file golden runtime closure (docs/current-architecture-map.md).
HOST_MODULES = [
    "classroom_oracle1_public", "classroom_oracle1_run", "classroom_oracle1_matcher",
    "classroom_oracle1_epistemic", "classroom_oracle1_eval", "fsg3_surface_map",
    "fsg6f_public", "fsg6f_frontier", "multiobject2c_policy", "fsg_geometry", "fsg_stereo",
    "exr_lite", "warp",
]
BLENDER_MODULES = [
    "classroom_oracle1_render", "classroom_oracle1_public", "fsg_geometry", "fsg6f_public",
    "bl_common", "exr_lite", "render_foveated", "warp",
]
DEV_CHECK = REPO / "tools/dev/check_classroom_oracle1.py"
PINS = {"numpy": "numpy", "opencv-python-headless": "opencv-python-headless", "pillow": "pillow"}
BLENDER_VERSION = "5.2.1"

results: list[tuple[str, str, bool, str]] = []  # (level, name, ok, detail)


def record(level: str, name: str, ok: bool, detail: str) -> None:
    results.append((level, name, ok, detail))


def run(cmd: list[str], timeout: float = 120.0) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"{type(exc).__name__}: {exc}"


def pinned_versions() -> dict[str, str]:
    pins: dict[str, str] = {}
    for req in ("requirements.txt", "requirements-fsg.txt"):
        for line in (REPO / req).read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "==" in line:
                name, ver = line.split("==", 1)
                pins[name.strip().lower()] = ver.strip()
    return pins


def probe_python() -> None:
    v = sys.version_info
    record("REQUIRED", "python-3.12", (v.major, v.minor) == (3, 12), f"{sys.version.split()[0]} at {sys.executable}")
    conda = "conda" in sys.base_prefix or "conda" in os.path.realpath(sys.executable)
    record("REQUIRED", "python-not-conda", not conda, f"base_prefix={sys.base_prefix}")
    record("INFO", "python-venv", sys.prefix != sys.base_prefix, f"prefix={sys.prefix}")
    path_py = shutil.which("python3")
    record("INFO", "python3-on-PATH", True, f"{path_py} -> {os.path.realpath(path_py) if path_py else None}")
    record("INFO", "PYTHONPATH", True, repr(os.environ.get("PYTHONPATH", "")))

    pins = pinned_versions()
    for dist in PINS:
        want = pins.get(dist)
        try:
            got = md.version(dist)
        except md.PackageNotFoundError:
            got = None
        record("REQUIRED", f"pin-{dist}", got is not None and got == want, f"installed={got} pinned={want}")
    try:
        record("INFO", "OpenEXR", True, md.version("OpenEXR"))
    except md.PackageNotFoundError:
        record("INFO", "OpenEXR", True, "not installed (not used by the golden runtime)")


def probe_host_modules() -> None:
    saved = list(sys.path)
    sys.path.insert(0, str(TOOLS))
    try:
        bad = []
        for name in HOST_MODULES + ["bl_common", "render_foveated", "classroom_oracle1_render"]:
            spec = importlib.util.find_spec(name)
            origin = spec.origin if spec else None
            if origin is None or not origin.startswith(str(TOOLS) + os.sep) or any(m in origin for m in LEGACY_MARKERS):
                bad.append(f"{name}={origin}")
        record("REQUIRED", "host-modules-resolve-in-repo", not bad,
               "; ".join(bad) if bad else f"{len(HOST_MODULES) + 3} modules under {TOOLS}")
    finally:
        sys.path[:] = saved
    record("REQUIRED", "dev-check-present", DEV_CHECK.is_file(), str(DEV_CHECK))
    leaked = [p for p in sys.path if any(m in p + "/" for m in LEGACY_MARKERS)]
    record("REQUIRED", "no-legacy-on-sys-path", not leaked, repr(leaked))


BLENDER_EXPR = r"""
import sys, json, importlib.util
sys.dont_write_bytecode = True
sys.path.insert(0, TOOLS)
out = {"python": sys.version.split()[0], "modules": {}, "optix": [], "cuda": []}
for n in MODS:
    s = importlib.util.find_spec(n)
    out["modules"][n] = s.origin if s else None
try:
    import bpy
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            devs = prefs.get_devices_for_type(kind)
            out[kind.lower()] = [d.name for d in devs if d.type == kind]
        except Exception as exc:
            out[kind.lower() + "_error"] = repr(exc)
except Exception as exc:
    out["cycles_error"] = repr(exc)
print("ENVPROBE" + json.dumps(out))
"""


def probe_blender(blender: str) -> None:
    exe = shutil.which(blender)
    record("INFO", "blender-path", exe is not None, f"{exe} -> {os.path.realpath(exe) if exe else None}")
    if exe is None:
        record("REQUIRED", "blender-5.2.1", False, f"`{blender}` not on PATH")
        return
    code, text = run([exe, "--version"])
    first = text.strip().splitlines()[0] if text.strip() else ""
    record("REQUIRED", "blender-5.2.1", code == 0 and first.startswith(f"Blender {BLENDER_VERSION}"), first)
    expr = f"TOOLS={str(TOOLS)!r}\nMODS={BLENDER_MODULES!r}\n" + BLENDER_EXPR
    code, text = run([exe, "-b", "--factory-startup", "--python-exit-code", "1", "--python-expr", expr], timeout=180)
    line = next((l for l in text.splitlines() if l.startswith("ENVPROBE")), None)
    if line is None:
        record("REQUIRED", "blender-probe", False, f"exit {code}; no probe output")
        return
    d = json.loads(line[len("ENVPROBE"):])
    record("INFO", "blender-python", True, d["python"])
    bad = [f"{n}={o}" for n, o in d["modules"].items()
           if o is None or not o.startswith(str(TOOLS) + os.sep) or any(m in o for m in LEGACY_MARKERS)]
    record("REQUIRED", "blender-modules-resolve-in-repo", not bad,
           "; ".join(bad) if bad else f"{len(d['modules'])} modules under {TOOLS}")
    record("REQUIRED", "cycles-optix-device", bool(d.get("optix")), f"optix={d.get('optix')} {d.get('optix_error', '')}".strip())
    record("INFO", "cycles-cuda-device", True, f"cuda={d.get('cuda')}")


def probe_informational() -> None:
    smi = shutil.which("nvidia-smi")
    if smi:
        code, text = run([smi, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"])
        record("INFO", "nvidia-smi", code == 0, text.strip().replace("\n", " | "))
    else:
        record("INFO", "nvidia-smi", False, "not on PATH")
    ff = shutil.which("ffmpeg")
    detail = "not on PATH"
    if ff:
        code, text = run([ff, "-hide_banner", "-version"])
        detail = f"{ff} -> {os.path.realpath(ff)}: {text.splitlines()[0] if text else code}"
    for extra in ("/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if Path(extra).exists() and extra != ff:
            detail += f"; also {extra}"
    record("INFO", "ffmpeg", ff is not None, detail + " (the demo writes MP4 through OpenCV mp4v, not ffmpeg)")
    try:
        import cv2
        record("INFO", "opencv-build", True, cv2.__version__)
    except Exception as exc:  # pragma: no cover - reported, not fatal here
        record("INFO", "opencv-build", False, repr(exc))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default="blender")
    ap.add_argument("--no-blender", action="store_true", help="skip the Blender probes (reported as not run)")
    args = ap.parse_args()
    probe_python()
    probe_host_modules()
    if args.no_blender:
        record("INFO", "blender", False, "skipped by --no-blender; Blender REQUIRED checks not run")
    else:
        probe_blender(args.blender)
    probe_informational()
    req_fail = 0
    for level, name, ok, detail in results:
        tag = "PASS" if ok else ("FAIL" if level == "REQUIRED" else "note")
        req_fail += level == "REQUIRED" and not ok
        print(f"[runtime-env] {level:8s} {tag:4s} {name}: {detail}")
    n_req = sum(1 for r in results if r[0] == "REQUIRED")
    print(f"[runtime-env] SUMMARY required_passed={n_req - req_fail}/{n_req} required_failed={req_fail}")
    return 1 if req_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
