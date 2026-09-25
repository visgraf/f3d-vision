#!/usr/bin/env bash
# Thin wrapper around the unchanged Classroom-Oracle-1 runner and evaluator.
#
#     scripts/run_golden.sh OUT_DIR            # full profile, OPTIX, then evaluation
#     scripts/run_golden.sh --smoke OUT_DIR    # repaired smoke gate, small profile, no evaluation
#
# OUT_DIR is required, resolved against the caller's directory, and must be new or empty
# (the runner refuses otherwise). No controller logic lives here: profile, device, spp,
# domain, fusion and watchdog are the runner's own defaults (full / OPTIX / 256 spp),
# except that --smoke selects the documented smoke command (--profile small --smoke).
# Evaluation runs only after the runner exits 0; the evaluator itself also refuses to run
# before manifest.json records control_complete: true.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE=0
OUT=""
for arg in "$@"; do
  case "$arg" in
    --smoke) SMOKE=1 ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) echo "run_golden: unknown option $arg" >&2; exit 2 ;;
    *) if [ -n "$OUT" ]; then echo "run_golden: one OUT_DIR only" >&2; exit 2; fi; OUT="$arg" ;;
  esac
done
if [ -z "$OUT" ]; then
  echo "usage: scripts/run_golden.sh [--smoke] OUT_DIR" >&2
  exit 2
fi
OUT="$(realpath -m -- "$OUT")"

if [ -x "$REPO/.venv/bin/python" ]; then PY="$REPO/.venv/bin/python"; else PY="python3"; fi

cd "$REPO"
if [ "$SMOKE" -eq 1 ]; then
  "$PY" tools/classroom_oracle1_run.py --repo "$REPO" --out "$OUT" --profile small --device OPTIX --smoke
  echo "[run_golden] smoke complete: $OUT (smoke output is not evaluated)"
else
  "$PY" tools/classroom_oracle1_run.py --repo "$REPO" --out "$OUT"
  "$PY" tools/classroom_oracle1_eval.py --run "$OUT"
  echo "[run_golden] full run and evaluation complete: $OUT"
fi
