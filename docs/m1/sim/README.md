# sim/ — host simulation of the TC69 diagnostic firmware

Exercises the real `keyboards/tc69/matrix.c` (+ `adc_diag_impl.h`) of the
qmk_firmware fork on a PC, against stub QMK headers (`stub/`) and a toy
electrical model (`sim.c`), and generates synthetic logs that follow the M1
procedure step by step (`gen_logs.py`). Used to check the diagnostic code paths
and `../m1_analyze.py` end to end. **The analogue numbers are arbitrary** (base
70..150, full-press delta 250..330, noise sigma 1, small fixed couplings, and a
residual-charge term for the purge-order experiment tuned to land near -13).

    ./build_sim.sh ~/workspace/ts52k-ec/work-tc69-diag before   # -> sim-before
    ./build_sim.sh ~/workspace/ts52k-ec/work-tc69-diag after    # -> sim-after (TC69_DIAG_PURGE_AFTER)
    python3 gen_logs.py ./sim-before ./sim-after /tmp/m1sim
    python3 ../m1_analyze.py all /tmp/m1sim --out /tmp/m1sim/out

Console output costs simulated time like a 32-byte / 1 ms HID endpoint, so the
blocking effect of the dumps on the scan period is visible in #SCN and in the
trace timestamps.
