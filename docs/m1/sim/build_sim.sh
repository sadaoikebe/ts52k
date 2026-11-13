#!/usr/bin/env bash
# Build the host simulation of the TC69 diag firmware.
#   ./build_sim.sh <qmk_firmware> [before|after]   -> ./sim-before or ./sim-after
set -euo pipefail
QMK=${1:?path to qmk_firmware (sadao-master)}; ORDER=${2:-before}
HERE="$(cd "$(dirname "$0")" && pwd)"
DEFS="-DTC69_ADC_DIAG"
[ "$ORDER" = after ] && DEFS="$DEFS -DTC69_DIAG_PURGE_AFTER -DTC69_DIAG_PURGE_US=6"
gcc -O2 -std=gnu11 -Wall -Wno-unused-function -I"$HERE/stub" -I"$QMK/keyboards/tc69" \
    '-DQMK_KEYBOARD_H="tc69_stub.h"' $DEFS \
    "$QMK/keyboards/tc69/matrix.c" "$HERE/sim.c" -lm -o "$HERE/sim-$ORDER"
echo "built $HERE/sim-$ORDER"
