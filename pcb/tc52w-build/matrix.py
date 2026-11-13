"""TC52 matrix definition shared by the schematic generator, the board builder and the firmware table.

Source: design-spec.md section 3 (14 columns x 4 rows, 52 crossings).
MUX_INPUT gives, for each column, (mux, input number X0..X7). It is free to choose
(spec 2.1) and was fixed from the board routing (see tc52-build-log.md).
"""

COLUMNS = [
    ["MX2", "MX3", "MX4", "MX5"],
    ["MX7", "MX8", "MX13", "MX9"],
    ["MX11", "MX12", "MX18", "MX14"],
    ["MX16", "MX17", "MX22", "MX23"],
    ["MX20", "MX21", "MX27", None],
    ["MX25", "MX26", "MX31", None],
    ["MX29", "MX30", "MX35", "MX60"],
    ["MX33", "MX34", "MX39", None],
    ["MX37", "MX38", "MX44", "MX81"],
    ["MX42", "MX43", "MX48", "MX82"],
    ["MX46", "MX47", "MX52", "MX58"],
    ["MX51", "MX56", "MX75", "MX61"],
    ["MX55", "MX65", "MX66", "MX67"],
    ["MX64", "MX74", None, "MX71"],
]

# column index (1-based) -> (mux 'A'|'B', X input)
MUX_INPUT = {
    1: ('A', 4), 2: ('A', 6), 3: ('A', 7), 4: ('A', 0), 5: ('A', 1), 6: ('A', 2),
    7: ('B', 4), 8: ('B', 6), 9: ('B', 7), 10: ('B', 5),
    11: ('B', 3), 12: ('B', 0), 13: ('B', 1), 14: ('B', 2),
}

# CD4051B: X input number -> package pin (checked against KiCad Analog_Switch:CD4051B
# and the TC69 netlist)
X_PIN = {0: 13, 1: 14, 2: 15, 3: 12, 4: 1, 5: 5, 6: 2, 7: 4}


def key_net():
    """MXn -> (row net, col net)"""
    out = {}
    for ci, col in enumerate(COLUMNS, 1):
        for ri, k in enumerate(col, 1):
            if k:
                out[k] = (f"ROW{ri}", f"COL{ci}")
    return out
