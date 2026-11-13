#!/usr/bin/env bash
# Record one M1 step from the TC69 diagnostic firmware (QMK MSYS on Windows).
#   ./m1-log.sh 01-idle        -> logs/m1-01-idle-<date>-<time>.log
# Stop with Ctrl+C when the step is done. The step names are listed in README.md.
set -u
step=${1:?usage: ./m1-log.sh <step, e.g. 01-idle>}
mkdir -p logs
f="logs/m1-${step}-$(date +%Y%m%d-%H%M%S).log"
echo "recording to $f  (Ctrl+C to stop)"
PYTHONUNBUFFERED=1 qmk console 2>&1 | tee "$f"
