#!/usr/bin/env bash
# UNDERWORLD - full headless regression suite (T-QA-01 seed): pipeline smoke + gameplay tests.
# Must pass before a branch is merged to main (HANDOFF_PROTOCOL §3).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/run_pipeline_smoke.sh" || { echo "RUN_ALL: FAIL (pipeline smoke)"; exit 1; }
"$DIR/run_gameplay_tests.sh" || { echo "RUN_ALL: FAIL (gameplay)"; exit 1; }
echo "RUN_ALL: PASS"
