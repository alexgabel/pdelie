#!/usr/bin/env bash
# The release gate, as one command.
#
# Both the v0.37 close and the v0.38.0b1 cut shipped a lint-failing commit
# because pytest was run and ruff was not. Neither was carelessness in isolation
# -- there was no single-command invariant, so "I ran the tests" was a claim
# about which commands a human remembered, and the memory failed the same way
# twice.
#
# This exits nonzero on the first failure and prints a per-gate status table, so
# the release ritual is "here is the paste of every gate's exit status" rather
# than a recollection.
#
# Usage:   ./scripts/release_gate_local.sh [--skip-build]
# Exit:    0 only if every gate passes.

set -uo pipefail

# Recursion guard.
#
# This script runs the full pytest suite. If anything inside that suite invokes
# the script again, the result is unbounded recursion: pytest -> gate -> pytest
# -> gate, each level loading numpy/scipy/pysindy. That happened -- seven levels
# deep, ~35 minutes, and it exhausted system swap.
#
# The offending test is gone, but the guard stays: it makes the failure mode
# impossible rather than merely absent, and the next caller who reaches for this
# script from a test gets a clear refusal instead of a dead machine.
if [ "${PDELIE_RELEASE_GATE_RUNNING:-}" = "1" ]; then
    echo "release_gate_local.sh is already running in this process tree." >&2
    echo "It runs the full test suite, so invoking it from inside that suite" >&2
    echo "recurses without bound. Refusing to re-enter." >&2
    exit 2
fi
export PDELIE_RELEASE_GATE_RUNNING=1

PYTHON="${PYTHON:-python}"
SKIP_BUILD=0
[ "${1:-}" = "--skip-build" ] && SKIP_BUILD=1

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

declare -a NAMES=() STATUS=()
FAILED=0

run_gate() {
    local name="$1"; shift
    printf '\n\033[1m>>> %s\033[0m\n' "$name"
    if "$@"; then
        NAMES+=("$name"); STATUS+=("PASS")
    else
        local code=$?
        NAMES+=("$name"); STATUS+=("FAIL($code)")
        FAILED=1
        # Keep going rather than aborting: a release engineer needs the whole
        # picture, not the first thing that broke. The exit status still refuses.
    fi
}

run_gate "ruff (lint)"        "$PYTHON" -m ruff check .
# mypy is checked against the RATCHET, not against exit status.
#
# This repo carries a frozen baseline of 147 errors in 29 files, so `mypy`
# always exits 1 and a gate keyed on its exit code would be permanently red --
# and a gate that can never pass gets disabled, which is worse than no gate.
# RELEASE_ENFORCEMENT.md section 7 specified the exit-code form; exercising this
# script is what surfaced that.
#
# The invariant that actually matters is that the fingerprint has not grown.
MYPY_BASELINE_ERRORS=147
MYPY_BASELINE_FILES=29
check_mypy_ratchet() {
    local out
    out="$("$PYTHON" -m mypy src/pdelie 2>&1 | tail -2)"
    printf '%s\n' "$out"
    local errors files
    errors="$(printf '%s' "$out" | sed -nE 's/^Found ([0-9]+) error.*/\1/p' | tail -1)"
    files="$(printf '%s' "$out" | sed -nE 's/.*in ([0-9]+) file.*/\1/p' | tail -1)"
    if [ -z "$errors" ]; then
        echo "  could not parse a mypy fingerprint; treating as failure"
        return 1
    fi
    if [ "$errors" -gt "$MYPY_BASELINE_ERRORS" ] || [ "$files" -gt "$MYPY_BASELINE_FILES" ]; then
        echo "  RATCHET BROKEN: $errors errors in $files files, baseline is ${MYPY_BASELINE_ERRORS}/${MYPY_BASELINE_FILES}"
        return 1
    fi
    if [ "$errors" -lt "$MYPY_BASELINE_ERRORS" ]; then
        echo "  ratchet IMPROVED: $errors < $MYPY_BASELINE_ERRORS -- lower the baseline in this script"
    fi
    echo "  fingerprint $errors in $files files (baseline ${MYPY_BASELINE_ERRORS}/${MYPY_BASELINE_FILES})"
    return 0
}
run_gate "mypy (ratchet <= 147/29)" check_mypy_ratchet
run_gate "pytest (tests)"     "$PYTHON" -m pytest -q
run_gate "sphinx -W (docs)"   "$PYTHON" -m sphinx -W -b html docs "$WORK/sphinx"

if [ "$SKIP_BUILD" -eq 0 ]; then
    run_gate "build (sdist+wheel)" "$PYTHON" -m build --outdir "$WORK/dist" --sdist --wheel
    # Installed into a throwaway venv rather than the working environment: a
    # --force-reinstall into the dev env replaces the editable install, and the
    # next local test run then silently measures the wheel instead of the tree.
    # The installed version is read via importlib.metadata, NOT pdelie.__version__.
    # The package exposes no __version__ attribute -- RELEASE_ENFORCEMENT.md
    # section 7 specified `print(pdelie.__version__)` and it AttributeErrors,
    # which means the documented chain could never have completed. Adding the
    # attribute would widen the frozen root surface to satisfy a check; reading
    # the installed metadata is both canonical and a stronger assertion, because
    # it verifies the WHEEL carries the version pyproject declares.
    run_gate "install (wheel version == pyproject)" bash -c "
        set -e
        $PYTHON -m venv '$WORK/venv' >/dev/null 2>&1
        '$WORK/venv/bin/python' -m pip install -q --disable-pip-version-check '$WORK'/dist/*.whl
        expected=\$($PYTHON -c \"import tomllib,pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])\")
        actual=\$('$WORK/venv/bin/python' -c 'import importlib.metadata as m; print(m.version(\"pdelie\"))')
        echo \"  pyproject=\$expected  installed wheel=\$actual\"
        [ \"\$expected\" = \"\$actual\" ] || { echo '  MISMATCH'; exit 1; }
        '$WORK/venv/bin/python' -c 'import pdelie; print(\"  imported pdelie ok,\", len(pdelie.__all__), \"root exports\")'
    "
else
    NAMES+=("build (sdist+wheel)"); STATUS+=("SKIPPED")
    NAMES+=("install (wheel into a clean venv)"); STATUS+=("SKIPPED")
fi

printf '\n\033[1m=== release gate summary ===\033[0m\n'
for i in "${!NAMES[@]}"; do
    printf '  %-38s %s\n' "${NAMES[$i]}" "${STATUS[$i]}"
done

if [ "$FAILED" -ne 0 ]; then
    printf '\n\033[31mRELEASE GATE FAILED.\033[0m Do not tag.\n'
    exit 1
fi
if [ "$SKIP_BUILD" -eq 1 ]; then
    printf '\n\033[33mPASSED WITH SKIPS.\033[0m --skip-build was used; not sufficient for a release tag.\n'
    exit 0
fi
printf '\n\033[32mRELEASE GATE PASSED.\033[0m\n'
