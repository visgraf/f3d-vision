# fov-3d-vision — core staging (compatibility extraction)

This is a **local staging extraction**, not a new architecture. It contains only the
files needed to reproduce **Classroom-Oracle-1 full**, copied byte-for-byte from the
frozen legacy repository, plus a small number of new documentation files and a
post-hoc demo. Nothing has been refactored, renamed, or moved.

- Legacy repository: https://github.com/visgraf/fov-3d-vision
- Freeze tag: `legacy-classroom-oracle3b-2026-09-25` → `48a3139020e87bfaf1255df1585390f7e9094ec8`
- Provenance and the inherited contracts: [docs/legacy-provenance.md](docs/legacy-provenance.md)
- What was migrated and what was not: [docs/migration-manifest.md](docs/migration-manifest.md), [migration-manifest.json](migration-manifest.json)
- The experiment itself: [docs/classroom-oracle-1.md](docs/classroom-oracle-1.md) (verbatim from the legacy repo)

## Requirements

- Linux workstation, NVIDIA GPU with OptiX (the golden record was produced on an RTX 4090).
- Blender 5.2.1 LTS on `PATH` as `blender`.
- Host Python 3.12 venv built from the **system** interpreter (not a conda `python3`):

```bash
/usr/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-fsg.txt
```

## Scene

`scenes/classroom/` is gitignored and must be rebuilt (see `scenes/manifest.json`, entry `classroom`):

```bash
# 1. download https://download.blender.org/demo/test/classroom.zip (md5 3adbb7114b514bfc6fc724ce20f86b4e)
#    and unzip it so that scenes/classroom/classroom.blend, assets/ and textures/ exist
# 2. place the eye
blender -b scenes/classroom/classroom.blend -P tools/place_eye.py -- \
        --location -0.6 -1.0 1.2 --yaw 0 --out scenes/classroom/classroom_eye.blend
```

The acceptance run used a byte-identical copy of the legacy checkout's `scenes/classroom/`
(`classroom_eye.blend` sha256 `dca66a32…6953cc`).

## Run

```bash
.venv/bin/python tools/dev/check_classroom_oracle1.py            # expect SUMMARY passed=12 failed=0
.venv/bin/python tools/classroom_oracle1_run.py --repo . --out previews/classroom-oracle-1-smoke --profile small --device OPTIX --smoke
.venv/bin/python tools/classroom_oracle1_run.py --repo . --out previews/classroom-oracle-1-full  --profile full  --device OPTIX
.venv/bin/python tools/classroom_oracle1_eval.py --run previews/classroom-oracle-1-full
.venv/bin/python tools/consolidation1_demo.py   --run previews/classroom-oracle-1-full
```

Expected golden result: 25 instances, 104 fixations (25 `oracle_seed` / 53 `fsg6f` /
26 `cyclopean_epistemic`), 25 `attention_complete`, 29,288 reachable samples, 25,618
covered, coverage 0.8746927069106801.

## Status

Consolidation 1: compatibility extraction. No remote. See the migration report in `docs/`.
