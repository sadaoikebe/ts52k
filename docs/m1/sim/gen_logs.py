#!/usr/bin/env python3
"""Generate synthetic M1 logs by running the host simulation of the real TC69
diag firmware through the same steps as the M1 procedure (README.md).

  python3 gen_logs.py <sim-before> <sim-after> <outdir>

The numbers in these logs are produced by a toy model (sim.c) and are
ARBITRARY: they only exercise the firmware's diagnostic code and m1_analyze.py.
"""
import os
import random
import subprocess
import sys

KEYS = [  # (row, col, name) = keyboards/tc69/keyboard.json
    (0, 5, '`'), (0, 7, '1'), (0, 6, '2'), (0, 4, '3'), (0, 2, '4'), (0, 1, '5'), (0, 0, '6'), (0, 3, '7'), (0, 13, '8'),
    (0, 15, '9'), (0, 14, '0'), (0, 12, '-'), (0, 10, '='), (0, 9, 'BS'), (0, 11, 'Home'),
    (1, 5, 'Tab'), (1, 7, 'Q'), (1, 6, 'W'), (1, 4, 'E'), (1, 2, 'R'), (1, 1, 'T'), (1, 0, 'Y'), (1, 3, 'U'), (1, 13, 'I'),
    (1, 15, 'O'), (1, 14, 'P'), (1, 12, '['), (1, 10, ']'), (1, 8, '\\'), (1, 11, 'PgUp'),
    (2, 5, 'Ctrl'), (2, 7, 'A'), (2, 6, 'S'), (2, 4, 'D'), (2, 2, 'F'), (2, 1, 'G'), (2, 0, 'H'), (2, 3, 'J'), (2, 13, 'K'),
    (2, 15, 'L'), (2, 14, ';'), (2, 12, "'"), (2, 9, 'Enter'), (2, 11, 'PgDn'),
    (3, 5, 'LShift'), (3, 6, 'Z'), (3, 4, 'X'), (3, 2, 'C'), (3, 1, 'V'), (3, 0, 'B'), (3, 3, 'N'), (3, 13, 'M'), (3, 15, ','),
    (3, 14, '.'), (3, 12, '/'), (3, 9, 'RShift'), (3, 8, 'Up'), (3, 11, 'End'),
    (4, 5, 'Fn'), (4, 7, 'LWin'), (4, 4, 'LAlt'), (4, 1, 'LThumb'), (4, 13, 'RThumb'), (4, 14, 'RAlt'), (4, 12, 'RWin'),
    (4, 10, 'Menu'), (4, 9, 'Left'), (4, 8, 'Down'), (4, 11, 'Right'),
]
BY = {n: (r, c) for r, c, n in KEYS}
LEAK_KEYS = ['LThumb', 'RThumb', 'LAlt', 'RAlt', 'Fn', 'Left', 'Down', 'Right']


class Sc:
    def __init__(self, seed):
        self.l = ['seed %d' % seed] + ['key %d %d' % (r, c) for r, c, _ in KEYS]
        self.t = 0.0
        self.rng = random.Random(seed)

    def idle(self, s):
        self.t += s * 1000

    def stroke(self, name, down_ms, hold_ms, up_ms, gap_ms, depth=1.0):
        r, c = BY[name]
        self.l.append('move %d %d %.1f %.3f %.1f' % (r, c, self.t, depth, down_ms))
        self.t += down_ms + hold_ms
        self.l.append('move %d %d %.1f 0 %.1f' % (r, c, self.t, up_ms))
        self.t += up_ms + gap_ms

    def rest(self, name, s, lo, hi):
        r, c = BY[name]
        end = self.t + s * 1000
        while self.t < end:
            self.l.append('move %d %d %.1f %.3f 300' % (r, c, self.t, self.rng.uniform(lo, hi)))
            self.t += 2000
        self.l.append('move %d %d %.1f 0 100' % (r, c, self.t))
        self.t += 500

    def text(self):
        return '\n'.join(self.l + ['end %.0f' % (self.t + 1500)]) + '\n'


def steps():
    s = {}
    a = Sc(1); a.idle(60); s['01-idle'] = a
    a = Sc(2); a.idle(5)
    for _, _, n in KEYS:
        a.stroke(n, 40, 3000, 40, 3000)
    s['02-press'] = a
    a = Sc(3); a.idle(5)
    for _ in range(2):
        for n in LEAK_KEYS:
            a.stroke(n, 40, 5000, 40, 3000)
    s['03-leak'] = a
    a = Sc(4); a.idle(10); a.rest('A', 30, 0.25, 0.55); a.idle(10); a.rest('A', 30, 0.25, 0.55); s['04-pinky'] = a
    a = Sc(5); a.idle(5)
    for n in ('F', 'J', 'A', 'LThumb'):
        for _ in range(10):
            a.stroke(n, 25, 150, 20, 2500)
    s['05-normal'] = a
    a = Sc(6); a.idle(5)
    for _ in range(5):
        a.stroke('F', 2000, 1000, 2000, 5000)
    for _ in range(3):
        a.stroke('A', 2000, 1000, 2000, 5000)
    s['06-slow'] = a
    a = Sc(7); a.idle(5)
    for _ in range(10):
        a.stroke('F', 8, 35, 8, 2000)
    s['07-fast'] = a
    a = Sc(8); a.idle(30); s['08-B-idle'] = a
    a = Sc(10); a.idle(30); s['10-idle-30min'] = a
    a = Sc(9); a.idle(5)
    for _ in range(2):
        for n in LEAK_KEYS:
            a.stroke(n, 40, 5000, 40, 3000)
    s['09-B-leak'] = a
    return s


def main():
    sim_a, sim_b, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    for name, sc in steps().items():
        exe = sim_b if '-B-' in name else sim_a
        res = subprocess.run([exe], input=sc.text(), capture_output=True, text=True, check=True)
        path = os.path.join(out, 'm1-%s-SIM.log' % name)
        with open(path, 'w', newline='\r\n') as f:  # Windows line endings, like a log saved on Windows
            f.write('Ψ Console Connected: Shobon TC69 Oyayubi Shift (FEED:6363:1)\n')
            text = res.stdout
            if name == '05-normal':  # colour codes as `qmk console` may emit them
                text = text.replace('Shobon:TC69 Oyayubi Shift:1: ', '\x1b[32mShobon:TC69 Oyayubi Shift:1\x1b[0m: ')
            f.write(text)
        print('%-40s %8d lines' % (path, res.stdout.count('\n')))


if __name__ == '__main__':
    main()
