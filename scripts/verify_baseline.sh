#!/usr/bin/env bash
# Structural verification of the sealed Classroom-Oracle-1 baseline.
#
#     scripts/verify_baseline.sh            # from any directory; exit 1 if any step fails
#
# Renders nothing and writes nothing: Python compiles in memory, bytecode writing is
# disabled, and every checker is read-only. Steps:
#   compile tracked .py | check_classroom_oracle1 | tangent-frame check | module self-tests |
#   classroom assets | runtime environment | baseline files unchanged | git diff --check
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 2
export PYTHONDONTWRITEBYTECODE=1
BASELINE_TAG="baseline-classroom-oracle1-2026-09-25"

if [ -x "$REPO/.venv/bin/python" ]; then
  PY="$REPO/.venv/bin/python"
else
  PY="python3"
  echo "[verify] WARNING no $REPO/.venv; using $(command -v python3) (the environment check will judge it)"
fi

PASSED=0
FAILED=0
FAILED_STEPS=()

step() {  # step NAME CMD...
  local name="$1"; shift
  echo "[verify] --- $name"
  if "$@"; then
    PASSED=$((PASSED + 1)); echo "[verify] PASS $name"
  else
    FAILED=$((FAILED + 1)); FAILED_STEPS+=("$name"); echo "[verify] FAIL $name"
  fi
}

compile_tracked() {
  git ls-files -z -- '*.py' | xargs -0 "$PY" -c '
import sys
bad = 0
for f in sys.argv[1:]:
    try:
        compile(open(f, "rb").read(), f, "exec", dont_inherit=True)
    except SyntaxError as exc:
        bad += 1; print("[verify] compile error", f, exc)
print(f"[verify] compiled {len(sys.argv) - 1} tracked .py files in memory, errors={bad}")
sys.exit(1 if bad else 0)'
}

module_self_tests() {
  local rc=0
  "$PY" tools/fsg_geometry.py --self-test || rc=1
  "$PY" tools/warp.py --self-test || rc=1
  "$PY" tools/classroom_oracle1_matcher.py --self-test || rc=1
  "$PY" tools/classroom_oracle1_public.py || rc=1
  (cd tools && "$PY" -c '
import sys
import fsg3_surface_map, fsg6f_frontier, classroom_oracle1_epistemic, classroom_oracle1_run
bad = 0
for m in (fsg3_surface_map, fsg6f_frontier, classroom_oracle1_epistemic, classroom_oracle1_run):
    r = m.self_test()
    print("[verify] self_test", m.__name__, "PASS" if not r else f"FAIL {r}")
    bad += bool(r)
sys.exit(1 if bad else 0)') || rc=1
  return $rc
}

baseline_files_unchanged() {
  if ! git rev-parse -q --verify "refs/tags/$BASELINE_TAG" >/dev/null; then
    echo "[verify] baseline tag $BASELINE_TAG absent"; return 1
  fi
  local n
  n=$(git ls-tree -r --name-only "$BASELINE_TAG" | wc -l)
  if git ls-tree -r -z --name-only "$BASELINE_TAG" | xargs -0 git diff --quiet "$BASELINE_TAG" --; then
    echo "[verify] $n files tracked at $BASELINE_TAG are byte-identical in the working tree"
  else
    echo "[verify] files changed since $BASELINE_TAG:"
    git ls-tree -r -z --name-only "$BASELINE_TAG" | xargs -0 git diff --stat "$BASELINE_TAG" --
    return 1
  fi
  git merge-base --is-ancestor "$BASELINE_TAG" HEAD || { echo "[verify] $BASELINE_TAG is not an ancestor of HEAD"; return 1; }
}

diff_check() {
  git diff --check && git diff --cached --check && git diff --check "$BASELINE_TAG" HEAD --
}

step "compile-tracked-python"        compile_tracked
step "check_classroom_oracle1"       "$PY" tools/dev/check_classroom_oracle1.py
step "check_fsg_tangent_frame"       "$PY" tools/dev/check_fsg_tangent_frame.py
step "module-self-tests"             module_self_tests
step "classroom-assets-self-test"    "$PY" tools/check_classroom_assets.py --self-test
step "classroom-assets"              "$PY" tools/check_classroom_assets.py
step "runtime-environment"           "$PY" tools/check_runtime_environment.py
step "baseline-files-unchanged"      baseline_files_unchanged
step "git-diff-check"                diff_check

echo "[verify] SUMMARY passed=$PASSED failed=$FAILED${FAILED_STEPS[*]:+ failed_steps=${FAILED_STEPS[*]}}"
[ "$FAILED" -eq 0 ]
