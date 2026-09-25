#!/usr/bin/env bash
# Compare a Classroom-Oracle-1 run with the committed golden behavior signature.
#
#     scripts/compare_golden.sh RUN_DIR            # full run (evaluate it first; run_golden.sh does)
#     scripts/compare_golden.sh --smoke RUN_DIR    # repaired smoke run
#
# Works from any directory: the repo is located from this script's path, and RUN_DIR is
# resolved against the caller's directory. Exit 0 only with 0 behavioral mismatches.
# RGB content is excluded by design (docs/baseline-contract.md); all logic lives in
# tools/compare_golden.py.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIG="$REPO/tests/golden/classroom-oracle1-signature.json"
RUN=""
for arg in "$@"; do
  case "$arg" in
    --smoke) SIG="$REPO/tests/golden/classroom-oracle1-smoke-signature.json" ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) echo "compare_golden: unknown option $arg" >&2; exit 2 ;;
    *) if [ -n "$RUN" ]; then echo "compare_golden: one RUN_DIR only" >&2; exit 2; fi; RUN="$arg" ;;
  esac
done
if [ -z "$RUN" ]; then
  echo "usage: scripts/compare_golden.sh [--smoke] RUN_DIR" >&2
  exit 2
fi
RUN="$(realpath -m -- "$RUN")"
if [ -x "$REPO/.venv/bin/python" ]; then PY="$REPO/.venv/bin/python"; else PY="python3"; fi

exec "$PY" "$REPO/tools/compare_golden.py" compare "$SIG" "$RUN"
