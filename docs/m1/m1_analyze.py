#!/usr/bin/env python3
"""TC69 M1 diagnostic-log analyser (Python 3.8+, standard library only).

Reads logs written by `qmk console` (or QMK Toolbox / hid_listen) from the TC69
diagnostic firmware (keyboards/tc69, TC69_ADC_DIAG=yes, output fmt=2) and writes
CSV files plus a short Japanese summary.

  python m1_analyze.py all     LOGDIR [--out DIR]          # everything, by file name (see README)
  python m1_analyze.py baseline LOG... [--out DIR]
  python m1_analyze.py press   LOG... [--baseline LOG] [--out DIR]   # full-press delta, S/N, leakage
  python m1_analyze.py pinky   LOG    [--key r2c7] [--out DIR]
  python m1_analyze.py trace   LOG... [--out DIR]                    # transition traces (+ envelope)
  python m1_analyze.py scan    LOG... [--out DIR]
  python m1_analyze.py ab      LOG_A LOG_B [--out DIR]               # purge order A (current) vs B (sense.ino)

Units: 10-bit ADC counts, one sample (the same unit as the TC69 thresholds
+120 / +30, A key +220 / +80). "delta" = value - idle baseline mean.

Only checked against synthetic logs (docs/m1/sim) so far; never against a real TC69.
"""
import argparse
import csv
import glob
import math
import os
import re
import sys

# ---------------------------------------------------------------- layout (keyboards/tc69/keyboard.json)
KEYS = [
    (0, 5, '`', 0, 0, 1), (0, 7, '1', 1, 0, 1), (0, 6, '2', 2, 0, 1), (0, 4, '3', 3, 0, 1),
    (0, 2, '4', 4, 0, 1), (0, 1, '5', 5, 0, 1), (0, 0, '6', 6, 0, 1), (0, 3, '7', 7, 0, 1),
    (0, 13, '8', 8, 0, 1), (0, 15, '9', 9, 0, 1), (0, 14, '0', 10, 0, 1), (0, 12, '-', 11, 0, 1),
    (0, 10, '=', 12, 0, 1), (0, 9, 'BS', 13, 0, 2), (0, 11, 'Home', 15, 0, 1),
    (1, 5, 'Tab', 0, 1, 1.5), (1, 7, 'Q', 1.5, 1, 1), (1, 6, 'W', 2.5, 1, 1), (1, 4, 'E', 3.5, 1, 1),
    (1, 2, 'R', 4.5, 1, 1), (1, 1, 'T', 5.5, 1, 1), (1, 0, 'Y', 6.5, 1, 1), (1, 3, 'U', 7.5, 1, 1),
    (1, 13, 'I', 8.5, 1, 1), (1, 15, 'O', 9.5, 1, 1), (1, 14, 'P', 10.5, 1, 1), (1, 12, '[', 11.5, 1, 1),
    (1, 10, ']', 12.5, 1, 1), (1, 8, '\\', 13.5, 1, 1.5), (1, 11, 'PgUp', 15, 1, 1),
    (2, 5, 'Ctrl', 0, 2, 1.75), (2, 7, 'A', 1.75, 2, 1), (2, 6, 'S', 2.75, 2, 1), (2, 4, 'D', 3.75, 2, 1),
    (2, 2, 'F', 4.75, 2, 1), (2, 1, 'G', 5.75, 2, 1), (2, 0, 'H', 6.75, 2, 1), (2, 3, 'J', 7.75, 2, 1),
    (2, 13, 'K', 8.75, 2, 1), (2, 15, 'L', 9.75, 2, 1), (2, 14, ';', 10.75, 2, 1), (2, 12, "'", 11.75, 2, 1),
    (2, 9, 'Enter', 12.75, 2, 2.25), (2, 11, 'PgDn', 15, 2, 1),
    (3, 5, 'LShift', 0, 3, 2.25), (3, 6, 'Z', 2.25, 3, 1), (3, 4, 'X', 3.25, 3, 1), (3, 2, 'C', 4.25, 3, 1),
    (3, 1, 'V', 5.25, 3, 1), (3, 0, 'B', 6.25, 3, 1), (3, 3, 'N', 7.25, 3, 1), (3, 13, 'M', 8.25, 3, 1),
    (3, 15, ',', 9.25, 3, 1), (3, 14, '.', 10.25, 3, 1), (3, 12, '/', 11.25, 3, 1),
    (3, 9, 'RShift', 12.25, 3, 1.75), (3, 8, 'Up', 14, 3, 1), (3, 11, 'End', 15, 3, 1),
    (4, 5, 'Fn', 0, 4, 1.25), (4, 7, 'LWin', 1.25, 4, 1.25), (4, 4, 'LAlt', 2.5, 4, 1.25),
    (4, 1, 'LThumb', 3.75, 4, 3), (4, 13, 'RThumb', 6.75, 4, 3), (4, 14, 'RAlt', 9.75, 4, 1.25),
    (4, 12, 'RWin', 11, 4, 1), (4, 10, 'Menu', 12, 4, 1), (4, 9, 'Left', 13, 4, 1),
    (4, 8, 'Down', 14, 4, 1), (4, 11, 'Right', 15, 4, 1),
]
ROWS, COLS = 5, 16
KEYINFO = {(r, c): (n, x + w / 2.0, y) for r, c, n, x, y, w in KEYS}
A_KEY = (2, 7)
ADC_MAX = 1023
# tc52-sim.md (model, S1_pad spring): full-press delta of TC52 full-GND relative to the TC69-equivalent
# model (275.6 counts). Used ONLY to project measured TC69 deltas onto TC52 (estimate, not a measurement).
TC52_RATIO = {'c2_330': 248.9 / 275.6, 'c2_300': 264.5 / 275.6}


def is_key(rc):
    return rc in KEYINFO


def kname(rc):
    return KEYINFO[rc][0] if rc in KEYINFO else '-'


def kid(rc):
    return 'r%dc%d' % rc


def parse_kid(s):
    m = re.fullmatch(r'r(\d)c(\d+)', s.strip())
    if not m:
        raise SystemExit('key must look like r2c7, got %r' % s)
    return int(m.group(1)), int(m.group(2))


# ---------------------------------------------------------------- parsing
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
PAYLOAD = re.compile(r'(?:^|: )((?:#ADC |#SCN |#HST |#CFG |#WARN |#TRC |ENV t=|T [PR] -?\d|(?:CAL|RAW|MIN|MAX|D3 |PRS|AVG|SDV) r\d:).*)$')
GRID = ('CAL', 'RAW', 'MIN', 'MAX', 'D3', 'AVG', 'SDV')


def kv(s):
    return dict(re.findall(r'(\w+)=(\S+)', s))


class Dump:
    def __init__(self, hdr, lineno):
        self.hdr = {k: int(v) for k, v in kv(hdr).items() if re.fullmatch(r'-?\d+', v)}
        self.seq, self.t = self.hdr.get('seq', -1), self.hdr.get('t', 0)
        self.scans = self.hdr.get('scans', 0)
        self.g = {k: [None] * ROWS for k in GRID}
        self.prs = [None] * ROWS
        self.scn, self.hst, self.cfg, self.warn = None, None, None, False
        self.lineno = lineno
        self.session = None

    def complete(self):
        return all(self.g[k][r] is not None for k in ('CAL', 'MIN', 'MAX') for r in range(ROWS)) and all(p is not None for p in self.prs)

    def has_avg(self):
        return all(self.g['AVG'][r] is not None and self.g['SDV'][r] is not None for r in range(ROWS))

    def v(self, kind, rc):
        r, c = rc
        x = self.g[kind][r][c]
        return x / 10.0 if kind in ('AVG', 'SDV') else x

    def pressed(self, rc):
        return (self.prs[rc[0]] >> rc[1]) & 1


class Log:
    def __init__(self, path):
        self.path, self.name = path, os.path.basename(path)
        self.dumps, self.envs, self.traces = [], [], []
        self.cfg, self.warn, self.bad = {}, False, 0
        self._parse()

    def _parse(self):
        cur, trc = None, None
        with open(self.path, encoding='utf-8', errors='replace') as f:
            for n, line in enumerate(f, 1):
                line = ANSI.sub('', line).rstrip('\r\n')
                m = PAYLOAD.search(line)
                if not m:
                    continue
                p = m.group(1).rstrip()
                try:
                    if p.startswith('#ADC '):
                        cur = Dump(p, n)
                        self.dumps.append(cur)
                    elif p.startswith('#SCN ') and cur:
                        cur.scn = {k: int(v) for k, v in kv(p).items()}
                    elif p.startswith('#HST ') and cur:
                        parts = p.split()
                        cur.hst = (int(parts[1].split('=')[1]), [int(x) for x in parts[2:]])
                    elif p.startswith('#CFG '):
                        self.cfg = kv(p)
                        if cur:
                            cur.cfg = self.cfg
                    elif p.startswith('#WARN '):
                        self.warn = True
                        if cur:
                            cur.warn = True
                    elif p.startswith('#TRC begin'):
                        h = kv(p)
                        trc = {'h': h, 'rows': [], 'key': parse_kid(h['key']), 'lineno': n}
                    elif p.startswith('#TRC end'):
                        if trc:
                            trc['dump_index'] = len(self.dumps) - 1
                            self.traces.append(trc)
                        trc = None
                    elif p.startswith('T '):
                        x = p.split()
                        if trc and x[1] == trc['h']['seg']:
                            trc['rows'].append((int(x[2]), int(x[3]), int(x[4]), int(x[5]), int(x[6]), [int(v) for v in x[7:]]))
                    elif p.startswith('ENV '):
                        h = kv(p)
                        ent = {}
                        for k, v in re.findall(r'(r\dc\d+)=(-?\d+,-?\d+,-?\d+)', p):
                            ent[parse_kid(k)] = tuple(int(z) for z in v.split(','))
                        self.envs.append({'t': int(h['t']), 'n': int(h['n']), 'keys': ent, 'more': int(h.get('more', 0)), 'dump_index': len(self.dumps) - 1})
                    else:
                        kind, r = p[:3].strip(), int(p[5])
                        vals = p.split(':', 1)[1].split()
                        if cur is None:
                            continue
                        if kind == 'PRS':
                            cur.prs[r] = int(vals[0], 16)
                        elif len(vals) == COLS:
                            cur.g[kind][r] = [int(v) for v in vals]
                        else:
                            self.bad += 1
                except (ValueError, IndexError, KeyError):
                    self.bad += 1
        self.dumps = [d for d in self.dumps if d.complete()]
        # sessions: a new one whenever the calibration changes (re-plug / reset) or seq goes back
        sess, prev = 0, None
        for d in self.dumps:
            if prev is not None and (d.g['CAL'] != prev.g['CAL'] or d.seq <= prev.seq):
                sess += 1
            d.session, prev = sess, d
        for e in self.envs:
            i = e['dump_index']
            e['dump'] = self.dumps[min(max(i, 0), len(self.dumps) - 1)] if self.dumps else None
        if not self.cfg and self.dumps:
            self.cfg = {}
        self.purge = self.cfg.get('purge', '?')

    def thr(self, rc):
        if rc == A_KEY:
            return int(self.cfg.get('thr_a', '220/80').split('/')[0]), int(self.cfg.get('thr_a', '220/80').split('/')[1])
        return int(self.cfg.get('thr', '120/30').split('/')[0]), int(self.cfg.get('thr', '120/30').split('/')[1])


ALL_RC = [(r, c) for r in range(ROWS) for c in range(COLS)]


def load(paths):
    logs = []
    for p in paths:
        lg = Log(p)
        if not lg.dumps:
            print('WARNING: %s: no complete diagnostic dump found (is this a TC69 diag log?)' % p, file=sys.stderr)
        if lg.warn:
            print('NOTE: %s comes from the EXPERIMENTAL purge-order build (purge=%s)' % (p, lg.purge), file=sys.stderr)
        logs.append(lg)
    return logs


# ---------------------------------------------------------------- statistics helpers
class Pool:
    """Pooled mean / variance from per-interval (n, mean, sd)."""

    def __init__(self):
        self.n = 0
        self.s1 = 0.0
        self.s2 = 0.0
        self.k = 0

    def add(self, n, mean, sd):
        if n <= 0:
            return
        self.n += n
        self.s1 += n * mean
        self.s2 += n * (sd * sd + mean * mean)
        self.k += 1

    @property
    def mean(self):
        return self.s1 / self.n if self.n else float('nan')

    @property
    def sd(self):
        if not self.n:
            return float('nan')
        return math.sqrt(max(self.s2 / self.n - self.mean ** 2, 0.0))


def pct(xs, q):
    if not xs:
        return float('nan')
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def f1(x):
    return '' if x is None or (isinstance(x, float) and math.isnan(x)) else ('%.1f' % x if isinstance(x, float) else str(x))


def f2(x):
    return '' if x is None or (isinstance(x, float) and math.isnan(x)) else ('%.2f' % x if isinstance(x, float) else str(x))


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print('wrote', path)


# ---------------------------------------------------------------- interval classification
IDLE_GUARD = 40  # single-frame excursion above CAL that still counts as "untouched"


def is_idle(d, lg):
    if any(d.prs):
        return False
    for rc in ALL_RC:
        if d.v('MAX', rc) - d.v('CAL', rc) >= IDLE_GUARD:
            return False
    return True


def held_key(d, lg):
    """The single key held down for the whole interval, else None."""
    held = [rc for rc in ALL_RC if d.v('MIN', rc) - d.v('CAL', rc) >= lg.thr(rc)[0]]
    if len(held) != 1:
        return None
    k = held[0]
    for rc in ALL_RC:
        if rc != k and d.v('MAX', rc) - d.v('CAL', rc) >= lg.thr(rc)[0]:
            return None  # another key was (also) pressed at some point
    return k


def baselines(logs):
    """Per (session-key, rc): pooled idle stats. Returns {(logname, session): {rc: dict}}."""
    out = {}
    for lg in logs:
        for d in lg.dumps:
            if not d.has_avg() or not is_idle(d, lg):
                continue
            key = (lg.name, d.session)
            b = out.setdefault(key, {rc: {'pool': Pool(), 'min': 10 ** 9, 'max': -10 ** 9, 'pp': [], 'avgs': [], 'cal': d.v('CAL', rc)} for rc in ALL_RC})
            for rc in ALL_RC:
                e = b[rc]
                e['pool'].add(d.scans, d.v('AVG', rc), d.v('SDV', rc))
                e['min'] = min(e['min'], d.v('MIN', rc))
                e['max'] = max(e['max'], d.v('MAX', rc))
                e['pp'].append(d.v('MAX', rc) - d.v('MIN', rc))
                e['avgs'].append(d.v('AVG', rc))
    return out


def base_for(bases, lg, d, rc):
    b = bases.get((lg.name, d.session))
    if b and b[rc]['pool'].n:
        return b[rc]['pool'].mean, 'idle'
    return float(d.v('CAL', rc)), 'cal'


# ---------------------------------------------------------------- baseline
def cmd_baseline(logs, out, quiet=False):
    bases = baselines(logs)
    if not bases:
        print('baseline: no idle interval found (all keys untouched for a whole dump interval)')
        return None
    # merge all sessions: per-key statistics are reported per session; the summary uses the largest session
    rows, per_key = [], {}
    for (name, sess), b in sorted(bases.items()):
        for rc in ALL_RC:
            e = b[rc]
            p = e['pool']
            if not p.n:
                continue
            avgs = e['avgs']
            k = 5 if len(avgs) >= 10 else max(1, len(avgs) // 2)
            drift = (sum(avgs[-k:]) / k - sum(avgs[:k]) / k) if len(avgs) >= 2 else float('nan')
            row = [name, sess, kid(rc), rc[0], rc[1], kname(rc), int(is_key(rc)), e['cal'], f2(p.mean), f2(p.sd), e['min'], e['max'], e['max'] - e['min'], f1(pct(e['pp'], 0.5)), f1(drift), p.k, p.n]
            rows.append(row)
            if is_key(rc):
                per_key.setdefault(rc, []).append((p.n, p.mean, p.sd, e['max'] - e['min'], e['cal'], pct(e['pp'], 0.5), drift))
    write_csv(os.path.join(out, 'baseline.csv'),
              ['log', 'session', 'key', 'row', 'col', 'name', 'is_key', 'cal', 'mean', 'sigma', 'min', 'max', 'pp_total', 'pp_interval_median', 'drift_last_minus_first', 'intervals', 'frames'], rows)
    # summary over real keys, using each key's largest session
    best = {rc: max(v, key=lambda t: t[0]) for rc, v in per_key.items()}
    summ = []
    for label, sel in [('all', lambda rc: True)] + [('row%d' % r, (lambda r: lambda rc: rc[0] == r)(r)) for r in range(ROWS)] + [('col%d' % c, (lambda c: lambda rc: rc[1] == c)(c)) for c in range(COLS)]:
        ks = [rc for rc in best if sel(rc)]
        if not ks:
            continue
        sig = [best[rc][2] for rc in ks]
        pp = [best[rc][3] for rc in ks]
        mean = [best[rc][1] for rc in ks]
        worst = max(ks, key=lambda rc: best[rc][3])
        summ.append([label, len(ks), f1(sum(mean) / len(mean)), f1(min(mean)), f1(max(mean)), f2(sum(sig) / len(sig)), f2(max(sig)), max(pp), '%s(%s)' % (kid(worst), kname(worst))])
    write_csv(os.path.join(out, 'baseline_summary.csv'), ['group', 'keys', 'mean_avg', 'mean_min', 'mean_max', 'sigma_avg', 'sigma_max', 'pp_max', 'pp_worst_key'], summ)
    res = {'best': best, 'summary': summ}
    if not quiet:
        s = summ[0]
        print('baseline: %d keys, mean %s (min %s, max %s), sigma avg %s max %s, worst p-p %s at %s' % tuple(s[1:]))
    return res


# ---------------------------------------------------------------- full press, S/N, leakage
def categorize(k, v):
    cats = []
    if v[1] == k[1]:
        cats.append('same_col')
        if v[0] == 0 and k[0] != 0:
            cats.append('first_read_of_col')
    if v[0] == k[0]:
        cats.append('same_row')
    if v[1] == k[1] + 1:
        cats.append('next_col_scan')
    if v[1] == k[1] - 1:
        cats.append('prev_col_scan')
    if is_key(k) and is_key(v):
        (_, xk, yk), (_, xv, yv) = KEYINFO[k], KEYINFO[v]
        if abs(yk - yv) <= 1 and abs(xk - xv) <= 1.6:
            cats.append('physical_neighbour')
    return cats or ['other']


def press_analysis(logs, ref_base=None):
    bases = baselines(logs)
    press, leak = {}, {}
    for lg in logs:
        for d in lg.dumps:
            if not d.has_avg():
                continue
            k = held_key(d, lg)
            if k is None:
                continue
            bk, src = base_for(bases, lg, d, k)
            e = press.setdefault(k, {'deltas': [], 'pool': Pool(), 'src': set(), 'peak': -10 ** 9, 'minv': 10 ** 9, 'base': bk, 'logs': set(), 'thr': lg.thr(k)})
            e['deltas'].append(d.v('AVG', k) - bk)
            e['pool'].add(d.scans, d.v('AVG', k) - bk, d.v('SDV', k))
            e['src'].add(src)
            e['peak'] = max(e['peak'], d.v('MAX', k) - bk)
            e['minv'] = min(e['minv'], d.v('MIN', k) - bk)
            e['logs'].add(lg.name)
            for v in ALL_RC:
                if v == k:
                    continue
                bv, srcv = base_for(bases, lg, d, v)
                if srcv != 'idle':
                    continue
                le = leak.setdefault((k, v), {'pool': Pool(), 'lo': 10 ** 9, 'hi': -10 ** 9, 'idle_sd': bases[(lg.name, d.session)][v]['pool'].sd})
                le['pool'].add(d.scans, d.v('AVG', v) - bv, d.v('SDV', v))
                le['lo'] = min(le['lo'], d.v('MIN', v) - bv)
                le['hi'] = max(le['hi'], d.v('MAX', v) - bv)
    return press, leak, bases


def cmd_press(logs, out, baseline_logs=None, tag='press', quiet=False):
    press, leak, bases = press_analysis(logs)
    if not press:
        print('%s: no interval with exactly one key held for a whole dump interval' % tag)
        return None
    # noise reference: separate idle log if given, else the idle parts of these logs
    ref = baselines(baseline_logs) if baseline_logs else bases
    noise = {}
    for (_, _), b in ref.items():
        for rc in ALL_RC:
            p = b[rc]['pool']
            if p.n and (rc not in noise or p.n > noise[rc][0]):
                noise[rc] = (p.n, p.sd, b[rc]['max'] - b[rc]['min'])
    rows = []
    for k in sorted(press):
        e = press[k]
        ds = e['deltas']
        dmean = sum(ds) / len(ds)
        sd = noise.get(k, (0, float('nan'), float('nan')))
        thr = e['thr'][0]
        full_level = e['base'] + dmean
        rows.append([kid(k), k[0], k[1], kname(k), len(ds), f1(dmean), f1(min(ds)), f1(max(ds)), f2(e['pool'].sd), f1(e['minv']), f1(e['peak']),
                     f1(e['base']), f1(full_level), f1(100.0 * full_level / ADC_MAX), thr, f1(dmean - thr), f2(dmean / thr),
                     f2(sd[1]), sd[2] if sd[0] else '', f1(dmean / sd[1]) if sd[0] and sd[1] > 0 else '', f1(dmean / sd[2]) if sd[0] and sd[2] > 0 else '',
                     int(dmean >= 300), '+'.join(sorted(e['src'])),
                     f1(dmean * TC52_RATIO['c2_330']), f1(dmean * TC52_RATIO['c2_300']), f1(dmean * TC52_RATIO['c2_330'] - 120),
                     f1((dmean * TC52_RATIO['c2_330'] - 120) / sd[1]) if sd[0] and sd[1] > 0 else ''])
    write_csv(os.path.join(out, '%s.csv' % tag),
              ['key', 'row', 'col', 'name', 'intervals', 'delta_mean', 'delta_min_interval', 'delta_max_interval', 'sigma_while_held', 'min_frame_delta', 'max_frame_delta',
               'baseline', 'full_level', 'full_pct_of_1023', 'press_thr', 'margin_over_thr', 'delta_over_thr', 'idle_sigma', 'idle_pp', 'snr_delta_over_sigma', 'snr_delta_over_pp', 'meets_300', 'baseline_source',
               'tc52_est_delta_c2_330', 'tc52_est_delta_c2_300', 'tc52_est_margin_over_120_c2_330', 'tc52_est_margin_in_sigma_c2_330'], rows)
    # leakage
    lrows, summ = [], {}
    for (k, v), le in sorted(leak.items()):
        p = le['pool']
        if not p.n:
            continue
        se = le['idle_sd'] / math.sqrt(p.n) if p.n and le['idle_sd'] == le['idle_sd'] and le['idle_sd'] > 0 else float('nan')
        z = p.mean / se if se == se and se > 0 else float('nan')
        cats = categorize(k, v)
        lrows.append([kid(k), kname(k), kid(v), kname(v), int(is_key(v)), ' '.join(cats), p.k, f2(p.mean), f1(le['lo']), f1(le['hi']), f1(z)])
        for c in cats + ['any']:
            s = summ.setdefault((k, c), None)
            if is_key(v) or c == 'first_read_of_col':
                if s is None or abs(p.mean) > abs(s[1]):
                    summ[(k, c)] = (v, p.mean, le['lo'], le['hi'], z)
    write_csv(os.path.join(out, '%s_leak.csv' % tag), ['pressed', 'pressed_name', 'victim', 'victim_name', 'victim_is_key', 'categories', 'intervals', 'shift_mean', 'frame_min', 'frame_max', 'z'], lrows)
    srows = []
    for (k, c), s in sorted(summ.items()):
        if s is None:
            continue
        v, m, lo, hi, z = s
        srows.append([kid(k), kname(k), c, kid(v), kname(v), f2(m), f1(lo), f1(hi), f1(z)])
    write_csv(os.path.join(out, '%s_leak_summary.csv' % tag), ['pressed', 'pressed_name', 'category', 'worst_victim', 'victim_name', 'shift_mean', 'frame_min', 'frame_max', 'z'], srows)
    real = [r for r in lrows if r[4] == 1]
    worst = max(real, key=lambda r: abs(float(r[7]))) if real else None
    worst_frame = max(real, key=lambda r: max(abs(float(r[8])), abs(float(r[9])))) if real else None
    res = {'press': press, 'rows': rows, 'leak': leak, 'leak_rows': lrows, 'worst': worst, 'worst_frame': worst_frame, 'noise': noise}
    if not quiet:
        dm = [float(r[5]) for r in rows]
        print('%s: %d keys; delta min %.1f median %.1f max %.1f; keys >= 300: %d/%d' % (tag, len(rows), min(dm), pct(dm, 0.5), max(dm), sum(r[21] for r in rows), len(rows)))
        if worst:
            print('%s: largest mean shift on another key: %s (%s) while %s (%s) held: %s' % (tag, worst[2], worst[3], worst[0], worst[1], worst[7]))
    return res


# ---------------------------------------------------------------- pinky on A
def cmd_pinky(logs, out, key=A_KEY, quiet=False):
    bases = baselines(logs)
    rows, avgd, maxd, prs = [], [], [], []
    for lg in logs:
        thr, rel = lg.thr(key)
        for d in lg.dumps:
            if not d.has_avg():
                continue
            b, src = base_for(bases, lg, d, key)
            idle = is_idle(d, lg)
            a, mx, mn = d.v('AVG', key) - b, d.v('MAX', key) - b, d.v('MIN', key) - b
            rows.append([lg.name, d.session, d.seq, d.t, int(idle), f1(a), f1(mn), f1(mx), d.v('D3', key), d.pressed(key), src])
            if not idle:
                avgd.append(a)
                maxd.append(mx)
                prs.append(d.pressed(key))
    write_csv(os.path.join(out, 'pinky_%s_series.csv' % kid(key)), ['log', 'session', 'seq', 't_ms', 'idle', 'avg_delta', 'min_frame_delta', 'max_frame_delta', 'd3_last', 'judged_pressed_at_dump', 'baseline_source'], rows)
    env = []
    for lg in logs:
        for e in lg.envs:
            if key in e['keys'] and e['dump'] is not None:
                b, _ = base_for(bases, lg, e['dump'], key)
                mn, mx, last = e['keys'][key]
                env.append((e['t'], mn - b, mx - b, last - b))
    write_csv(os.path.join(out, 'pinky_%s_env.csv' % kid(key)), ['t_ms', 'min_delta', 'max_delta', 'last_delta'], [[t, f1(a), f1(b_), f1(c)] for t, a, b_, c in env])
    thr_n, thr_a = 120, 220
    summ = {
        'intervals_touched': len(avgd),
        'avg_delta_p5': pct(avgd, 0.05), 'avg_delta_p50': pct(avgd, 0.5), 'avg_delta_p95': pct(avgd, 0.95), 'avg_delta_max': max(avgd) if avgd else float('nan'),
        'max_frame_delta_max': max(maxd) if maxd else float('nan'),
        'share_avg_over_120': (sum(1 for x in avgd if x > thr_n) / len(avgd)) if avgd else float('nan'),
        'share_avg_over_220': (sum(1 for x in avgd if x > thr_a) / len(avgd)) if avgd else float('nan'),
        'share_judged_pressed_at_dump': (sum(prs) / len(prs)) if prs else float('nan'),
        'env_windows': len(env),
        'env_share_max_over_120': (sum(1 for x in env if x[2] > thr_n) / len(env)) if env else float('nan'),
        'env_share_max_over_220': (sum(1 for x in env if x[2] > thr_a) / len(env)) if env else float('nan'),
    }
    write_csv(os.path.join(out, 'pinky_%s_summary.csv' % kid(key)), ['item', 'value'], [[k, f2(v) if isinstance(v, float) else v] for k, v in summ.items()])
    if not quiet:
        print('pinky %s: %d touched intervals, mean delta p50 %s p95 %s max %s; share > 120: %s, > 220: %s' % (kid(key), summ['intervals_touched'], f1(summ['avg_delta_p50']), f1(summ['avg_delta_p95']), f1(summ['avg_delta_max']), f2(summ['share_avg_over_120']), f2(summ['share_avg_over_220'])))
    return summ


# ---------------------------------------------------------------- transition traces and envelopes
MAX_INTERP_MS = 20.0  # a crossing that falls into a recording gap longer than this is reported as unknown


def first_cross(pts, level, up=True, after=None):
    """Interpolated time (ms) where delta first crosses level (upwards or downwards).
    None if it never does, or if the first crossing lies inside a gap in the recording
    (between the P and R segments, or across a console dump)."""
    prev = None
    for t, dl in pts:
        if after is not None and t < after:
            prev = (t, dl)
            continue
        if prev is not None:
            a, b = prev[1], dl
            if (up and a < level <= b) or (not up and a > level >= b):
                if t - prev[0] > MAX_INTERP_MS:
                    return None
                return prev[0] + (t - prev[0]) * (level - a) / (b - a) if b != a else t
        prev = (t, dl)
    return None


def cmd_trace(logs, out, tag='trace', quiet=False):
    rows, summ = [], []
    for lg in logs:
        by = {}
        for tr in lg.traces:
            by.setdefault(int(tr['h']['id']), {})[tr['h']['seg']] = tr
        for tid in sorted(by):
            segs = by[tid]
            any_tr = next(iter(segs.values()))
            k = any_tr['key']
            h = any_tr['h']
            cal = int(h['cal'])
            thr = int(h['thr3']) // 3
            rel = int(h['rel3']) // 3
            frames = {}
            for s, tr in segs.items():
                t0 = int(tr['h'].get('t0_us', 0))
                for i, dt, raw, d3, p, rowv in tr['rows']:
                    rows.append([lg.name, tid, s, kid(k), kname(k), i, '%.3f' % (dt / 1000.0), raw, raw - cal, d3, '%.1f' % (d3 / 3.0), p] + rowv)
                    frames[(t0 + dt) & 0xFFFFFFFF] = (raw - cal, d3 / 3.0, p)
            ts = sorted(frames)
            if not ts:
                continue
            tabs = [(t / 1000.0, frames[t][0]) for t in ts]
            d3s = [(t / 1000.0, frames[t][1]) for t in ts]
            prs = [frames[t][2] for t in ts]
            trans = sum(1 for a, b in zip(prs, prs[1:]) if a != b)
            vals = [x[1] for x in tabs]
            plateau = max(sum(vals[i:i + 3]) / 3.0 for i in range(max(1, len(vals) - 2)))  # max of a 3-frame moving average
            tP = int(segs['P']['h'].get('t0_us', 0)) / 1000.0 if 'P' in segs else None
            tR = int(segs['R']['h'].get('t0_us', 0)) / 1000.0 if 'R' in segs else None
            rel_t = lambda x, ref: None if x is None or ref is None else x - ref
            c10 = first_cross(tabs, 0.1 * plateau)
            c90 = first_cross(tabs, 0.9 * plateau, after=c10)
            c_rel = first_cross(tabs, rel)
            c_thr = first_cross(tabs, thr, after=c_rel)
            d_thr = first_cross(d3s, thr, after=c_rel)
            peak_t = None
            ipk = max(range(max(1, len(vals) - 2)), key=lambda i: sum(vals[i:i + 3]))
            t_peak = tabs[min(ipk + 1, len(tabs) - 1)][0]
            if tR is not None:
                after = max(t_peak, tR - 2000.0)
                f90 = first_cross(tabs, 0.9 * plateau, up=False, after=after)
                f10 = first_cross(tabs, 0.1 * plateau, up=False, after=f90)
                r_thr = first_cross(tabs, thr, up=False, after=after)
                r_rel = first_cross(tabs, rel, up=False, after=r_thr)
            else:
                f90 = f10 = r_thr = r_rel = None
            gaps = []
            for tr in segs.values():  # frame gaps inside each recorded segment (not between P and R)
                dts = [x[1] for x in tr['rows']]
                gaps += [b - a for a, b in zip(dts, dts[1:])]
            med = pct(gaps, 0.5) if gaps else float('nan')
            hold = (tR - tP) if (tR is not None and tP is not None) else None
            fmt = lambda x: '' if x is None else '%.1f' % x
            summ.append([lg.name, tid, kid(k), kname(k), cal, thr, rel, f1(plateau), f1(plateau - thr), fmt(hold),
                         fmt(rel_t(c10, tP)), fmt(rel_t(c90, tP)), fmt(None if c10 is None or c90 is None else c90 - c10),
                         fmt(rel_t(c_rel, tP)), fmt(rel_t(c_thr, tP)), fmt(None if c_rel is None or c_thr is None else c_thr - c_rel), fmt(rel_t(d_thr, tP)),
                         fmt(rel_t(f90, tR)), fmt(rel_t(f10, tR)), fmt(None if f90 is None or f10 is None else f10 - f90),
                         fmt(rel_t(r_thr, tR)), fmt(rel_t(r_rel, tR)), fmt(None if r_thr is None or r_rel is None else r_rel - r_thr),
                         trans, max(0, trans - 2), '%.3f' % (med / 1000.0) if med == med else '', '%.3f' % (max(gaps) / 1000.0) if gaps else '',
                         int(segs['P']['h'].get('other', '0')) + int(segs.get('R', segs['P'])['h'].get('other', '0')) if 'P' in segs else '',
                         int(any_tr['h'].get('r_restarts', '0'))])
    if rows:
        width = max(len(r) for r in rows) - 12
        write_csv(os.path.join(out, '%s_curves.csv' % tag), ['log', 'id', 'seg', 'key', 'name', 'i', 'dt_ms', 'raw', 'delta', 'd3', 'd3_per_sample', 'judged'] + ['row_c%d' % c for c in range(width)], rows)
    write_csv(os.path.join(out, '%s_summary.csv' % tag),
              ['log', 'id', 'key', 'name', 'cal', 'press_thr', 'release_thr', 'plateau_delta', 'plateau_margin_over_thr', 'hold_ms',
               'press_t10_ms', 'press_t90_ms', 'rise_10_90_ms', 'press_cross_release_thr_ms', 'press_cross_press_thr_ms', 'press_band_ms', 'press_d3_cross_ms',
               'release_t90_ms', 'release_t10_ms', 'fall_90_10_ms', 'release_below_press_thr_ms', 'release_below_release_thr_ms', 'release_band_ms',
               'judged_transitions', 'chatter_extra_transitions', 'frame_period_median_ms', 'max_gap_ms', 'frames_with_other_key', 'release_restarts'], summ)
    env_rows = []
    for lg in logs:
        bases = baselines([lg])
        for e in lg.envs:
            if e['dump'] is None:
                continue
            for rc, (mn, mx, last) in sorted(e['keys'].items()):
                b, _ = base_for(bases, lg, e['dump'], rc)
                env_rows.append([lg.name, e['t'], e['n'], kid(rc), kname(rc), f1(mn - b), f1(mx - b), f1(last - b)])
    if env_rows:
        write_csv(os.path.join(out, '%s_envelope.csv' % tag), ['log', 't_ms', 'scans', 'key', 'name', 'min_delta', 'max_delta', 'last_delta'], env_rows)
    ep_rows = envelope_episodes(logs)
    if ep_rows:
        write_csv(os.path.join(out, '%s_envelope_episodes.csv' % tag),
                  ['log', 'key', 'name', 'start_t_ms', 'end_t_ms', 'windows', 'peak_delta', 'press_30_to_thr_ms', 'press_thr_to_90pct_ms', 'press_30_to_90pct_ms',
                   'release_90pct_to_below_thr_ms', 'release_below_thr_to_below_30_ms', 'judged_window_ms'], ep_rows)
    if not quiet:
        ch = sum(s[24] for s in summ)
        rs = sum(s[28] for s in summ)
        print('%s: %d transitions captured, extra judged transitions (chatter) %d, re-press before final release %d' % (tag, len(summ), ch, rs))
    return summ


def envelope_episodes(logs, gap_ms=160):
    """Group ENV windows of each key into press episodes (50 ms resolution)."""
    out = []
    for lg in logs:
        bases = baselines([lg])
        per = {}
        for e in lg.envs:
            if e['dump'] is None:
                continue
            for rc, (mn, mx, last) in e['keys'].items():
                b, _ = base_for(bases, lg, e['dump'], rc)
                per.setdefault(rc, []).append((e['t'], mn - b, mx - b))
        for rc, ws in per.items():
            thr = lg.thr(rc)[0]
            eps, cur = [], [ws[0]]
            for w in ws[1:]:
                if w[0] - cur[-1][0] > gap_ms:
                    eps.append(cur)
                    cur = []
                cur.append(w)
            eps.append(cur)
            for ep in eps:
                peak = max(w[2] for w in ep)
                if peak < thr:
                    continue  # touches that never reached the press threshold are not press episodes
                first = lambda pred: next((w[0] for w in ep if pred(w)), None)
                ipk = max(range(len(ep)), key=lambda i: ep[i][2])
                t30, tthr, t90 = first(lambda w: w[2] >= 30), first(lambda w: w[2] >= thr), first(lambda w: w[2] >= 0.9 * peak)
                tail = ep[ipk:]
                last90 = max((w[0] for w in tail if w[1] >= 0.9 * peak), default=None)
                below_thr = next((w[0] for w in tail if w[1] < thr), None)
                below_30 = next((w[0] for w in tail if w[1] < 30), None)
                d = lambda a, b: '' if a is None or b is None else b - a
                above = [w[0] for w in ep if w[1] >= thr]
                out.append([lg.name, kid(rc), kname(rc), ep[0][0], ep[-1][0], len(ep), f1(peak), d(t30, tthr), d(tthr, t90), d(t30, t90),
                            d(last90, below_thr), d(below_thr, below_30), (above[-1] - above[0]) if above else ''])
    return out


# ---------------------------------------------------------------- scan rate
def cmd_scan(logs, out, tag='scan', quiet=False):
    rows, hz, pavg, pmin, pmax, aavg, hist, binw = [], [], [], [], [], [], None, None
    for lg in logs:
        for d in lg.dumps:
            if not d.scn:
                continue
            s = d.scn
            rows.append([lg.name, d.seq, d.t, d.scans, d.hdr.get('scan_hz'), s['n'], s['per_min'], s['per_avg'], s['per_max'], s['acq_min'], s['acq_avg'], s['acq_max']] + (d.hst[1] if d.hst else []))
            if s['n'] > 0:
                pavg.append(s['per_avg'])
                pmin.append(s['per_min'])
                pmax.append(s['per_max'])
                aavg.append(s['acq_avg'])
            if d.hst:
                binw = d.hst[0]
                hist = [a + b for a, b in zip(hist, d.hst[1])] if hist else list(d.hst[1])
    nb = len(hist) if hist else 16
    write_csv(os.path.join(out, '%s.csv' % tag), ['log', 'seq', 't_ms', 'scans', 'scan_hz', 'periods', 'per_min_us', 'per_avg_us', 'per_max_us', 'acq_min_us', 'acq_avg_us', 'acq_max_us'] + ['hist_%d' % i for i in range(nb)], rows)
    if not pavg:
        print('%s: no #SCN lines (fmt=2 firmware needed)' % tag)
        return None
    total = sum(hist) if hist else 0
    summ = {'dumps': len(pavg), 'period_avg_us': sum(pavg) / len(pavg), 'scan_rate_hz': 1e6 / (sum(pavg) / len(pavg)),
            'period_min_us': min(pmin), 'period_max_us': max(pmax), 'period_avg_spread_us': max(pavg) - min(pavg),
            'acquire_avg_us': sum(aavg) / len(aavg), 'acquire_per_crosspoint_us': sum(aavg) / len(aavg) / (ROWS * COLS),
            'hist_bin_us': binw, 'hist_total': total}
    if hist:
        cum, p50, p99 = 0, None, None
        for i, n in enumerate(hist):
            cum += n
            if p50 is None and cum >= 0.5 * total:
                p50 = (i + 1) * binw
            if p99 is None and cum >= 0.99 * total:
                p99 = (i + 1) * binw
        summ['period_p50_upper_us'] = p50
        summ['period_p99_upper_us'] = p99
        summ['share_in_overflow_bin'] = hist[-1] / total if total else 0
    write_csv(os.path.join(out, '%s_summary.csv' % tag), ['item', 'value'], [[k, f2(v) if isinstance(v, float) else v] for k, v in summ.items()])
    if not quiet:
        print('%s: %.0f Hz (period avg %.0f us, min %d, max %d us), acquire %.0f us (%.1f us per crosspoint)' % (tag, summ['scan_rate_hz'], summ['period_avg_us'], summ['period_min_us'], summ['period_max_us'], summ['acquire_avg_us'], summ['acquire_per_crosspoint_us']))
    return summ


# ---------------------------------------------------------------- purge order A/B
PREDICTED = (-18.0, -6.0)  # fable-analog-report.md §6-1 (TC69, sense.ino order)


def cmd_ab(logs_a, logs_b, out, quiet=False):
    for lg in logs_a:
        if lg.purge != 'before':
            print('WARNING: A log %s has purge=%s (expected "before")' % (lg.name, lg.purge))
    for lg in logs_b:
        if lg.purge != 'after':
            print('WARNING: B log %s has purge=%s (expected "after" = experimental build)' % (lg.name, lg.purge))
    pa, la, _ = press_analysis(logs_a)
    pb, lb, _ = press_analysis(logs_b)
    rows, focus = [], []
    for (k, v) in sorted(set(la) & set(lb)):
        a, b = la[(k, v)]['pool'], lb[(k, v)]['pool']
        if not a.n or not b.n:
            continue
        cats = categorize(k, v)
        rows.append([kid(k), kname(k), kid(v), kname(v), int(is_key(v)), ' '.join(cats), f2(a.mean), f2(b.mean), f2(b.mean - a.mean), a.k, b.k])
        if 'first_read_of_col' in cats and k[0] == ROWS - 1:
            focus.append((k, v, a.mean, b.mean))
    write_csv(os.path.join(out, 'ab_leak.csv'), ['pressed', 'pressed_name', 'victim', 'victim_name', 'victim_is_key', 'categories', 'shift_A', 'shift_B', 'B_minus_A', 'intervals_A', 'intervals_B'], rows)
    frows = [[kid(k), kname(k), kid(v), kname(v), f2(a), f2(b), f2(b - a), int(PREDICTED[0] <= b - a <= PREDICTED[1])] for k, v, a, b in focus]
    write_csv(os.path.join(out, 'ab_focus.csv'), ['pressed(bottom row)', 'pressed_name', 'victim(row0 same col)', 'victim_name', 'shift_A', 'shift_B', 'B_minus_A', 'within_predicted_-18..-6'], frows)
    worst_any = None
    for r in rows:
        if r[4] and (worst_any is None or abs(float(r[8])) > abs(float(worst_any[8]))):
            worst_any = r
    if not quiet:
        if focus:
            dif = [b - a for _, _, a, b in focus]
            print('ab: bottom-row key -> row-0 key of the same column: B-A median %.1f (min %.1f, max %.1f) over %d pairs; prediction %g..%g' % (pct(dif, 0.5), min(dif), max(dif), len(dif), PREDICTED[0], PREDICTED[1]))
        else:
            print('ab: no bottom-row key held in both logs; cannot evaluate the predicted pair')
    return {'focus': focus, 'rows': rows, 'worst': worst_any}


def cmd_drift(logs_a, logs_b, out):
    """Per-key change of the idle mean between two idle logs (e.g. right after plug-in and 30 min later)."""
    ba, bb = baselines(logs_a), baselines(logs_b)
    if not ba or not bb:
        print('drift: an idle log without idle intervals')
        return None
    ka, kb = max(ba, key=lambda k: next(iter(ba[k].values()))['pool'].n), max(bb, key=lambda k: next(iter(bb[k].values()))['pool'].n)
    A, B = ba[ka], bb[kb]
    same_cal = all(A[rc]['cal'] == B[rc]['cal'] for rc in ALL_RC)
    rows, worst = [], None
    for rc in ALL_RC:
        if not is_key(rc) or not A[rc]['pool'].n or not B[rc]['pool'].n:
            continue
        # if the keyboard was re-plugged the calibration differs; compare against each log's own CAL then
        da = A[rc]['pool'].mean - (0 if same_cal else A[rc]['cal'])
        db = B[rc]['pool'].mean - (0 if same_cal else B[rc]['cal'])
        d = db - da
        rows.append([kid(rc), kname(rc), f2(A[rc]['pool'].mean), f2(B[rc]['pool'].mean), A[rc]['cal'], B[rc]['cal'], f2(d)])
        if worst is None or abs(d) > abs(worst[1]):
            worst = ('%s(%s)' % (kid(rc), kname(rc)), d)
    write_csv(os.path.join(out, 'drift.csv'), ['key', 'name', 'mean_first', 'mean_second', 'cal_first', 'cal_second', 'change'], rows)
    print('drift: largest change %.1f at %s%s' % (worst[1], worst[0], '' if same_cal else ' (calibration differs: re-plugged)'))
    return {'worst': worst, 'same_cal': same_cal}


# ---------------------------------------------------------------- all
STEPS = [
    ('01', 'idle'), ('02', 'press'), ('03', 'leak'), ('04', 'pinky'),
    ('05', 'normal'), ('06', 'slow'), ('07', 'fast'), ('08', 'B-idle'), ('09', 'B-leak'), ('10', 'idle-30min'),
]


def find(logdir, prefix):
    return sorted(glob.glob(os.path.join(logdir, 'm1-%s-*.log' % prefix)) + glob.glob(os.path.join(logdir, 'm1-%s-*.txt' % prefix)))


def cmd_all(logdir, out):
    os.makedirs(out, exist_ok=True)
    got = {p: find(logdir, p) for p, _ in STEPS}
    for p, n in STEPS:
        print('step %s (%s): %s' % (p, n, ', '.join(os.path.basename(x) for x in got[p]) or '— none —'))
    L = {p: load(v) for p, v in got.items()}
    md = ['# M1 解析結果（m1_analyze.py all）', '', '入力: `%s`。単位は 10 bit・1 サンプルのカウント。' % logdir, '']
    base = cmd_baseline(L['01'], out) if L['01'] else None
    if base:
        s = base['summary'][0]
        md += ['## ベースラインとノイズ（01-idle）', '',
               '- キー %s 個。平均 %s（最小 %s、最大 %s）' % (s[1], s[2], s[3], s[4]),
               '- σ（1 サンプル）平均 %s、最大 %s' % (s[5], s[6]),
               '- 最大振幅 p-p（全区間）最悪 %s、%s　→ §7 基準「10 以下」: %s' % (s[7], s[8], '満たす' if s[7] <= 10 else '満たさない'),
               '- 0 張り付き（平均 < 5）: %s' % (', '.join(kid(rc) for rc, v in base['best'].items() if v[1] < 5) or 'なし'), '']
    pr = cmd_press(L['02'], out, baseline_logs=L['01'] or None) if L['02'] else None
    if pr:
        rows = pr['rows']
        dm = [float(r[5]) for r in rows]
        low = sorted(rows, key=lambda r: float(r[5]))[:5]
        hi_pct = max(float(r[13]) for r in rows)
        md += ['## 全押下 Δ と S/N（02-press）', '',
               '- 測れたキー %d 個（%d 個中）。Δ 最小 %.1f／中央 %.1f／最大 %.1f' % (len(rows), len(KEYS), min(dm), pct(dm, 0.5), max(dm)),
               '- Δ ≥ 300（§7 暫定基準）を満たすキー: %d/%d' % (sum(r[21] for r in rows), len(rows)),
               '- Δ の小さい順: ' + '、'.join('%s(%s) %s' % (r[0], r[3], r[5]) for r in low),
               '- ベースライン＋全押下の最大: ADC 上限の %.1f%%（§7 基準 85%% 以下）' % hi_pct,
               '- S/N（Δ/σ）最小: %s　（Δ/p-p）最小: %s' % (min((r[19] for r in rows if r[19] != ''), key=float, default='—'), min((r[20] for r in rows if r[20] != ''), key=float, default='—')),
               '- TC52 への投影（tc52-sim.md のモデル比 ×%.3f／×%.3f を掛けた推定、測定ではない）: Δ 最小 %.1f（C2=330 pF）／%.1f（300 pF）、閾値 120 に対する余裕の最小 %.1f' % (
                   TC52_RATIO['c2_330'], TC52_RATIO['c2_300'], min(dm) * TC52_RATIO['c2_330'], min(dm) * TC52_RATIO['c2_300'], min(dm) * TC52_RATIO['c2_330'] - 120), '']
        if pr['worst']:
            w = pr['worst']
            md += ['- 押していないキーの平均の動き（02 の全組合せ）最大: %s が %s(%s) 押下中に %s(%s)' % (w[7], w[0], w[1], w[2], w[3]), '']
    lk = cmd_press(L['03'], out, baseline_logs=L['01'] or None, tag='bottomrow') if L['03'] else None
    if lk and lk['worst']:
        w, wf = lk['worst'], lk['worst_frame']
        md += ['## 漏れ込み（03-leak、現行のパージ順）', '',
               '- 平均の動きの最大: %s（%s(%s) 押下中の %s(%s)、分類 %s）' % (w[7], w[0], w[1], w[2], w[3], w[5]),
               '- 1 フレームの最大振れ（ノイズ込み）: %s〜%s（%s(%s) 押下中の %s(%s)）　→ §7 基準「30 以下」の判定はこちらで見る' % (wf[8], wf[9], wf[0], wf[1], wf[2], wf[3]), '']
    pk = cmd_pinky(L['04'], out) if L['04'] else None
    if pk:
        md += ['## A キーに小指を載せた状態（04-pinky）', '',
               '- 触れている区間 %d。平均 Δ：中央 %s、95%% 点 %s、最大 %s' % (pk['intervals_touched'], f1(pk['avg_delta_p50']), f1(pk['avg_delta_p95']), f1(pk['avg_delta_max'])),
               '- 区間平均が 120 を超えた割合 %s、220 を超えた割合 %s（50 ms 窓の最大値では 120 超 %s、220 超 %s）' % (f2(pk['share_avg_over_120']), f2(pk['share_avg_over_220']), f2(pk['env_share_max_over_120']), f2(pk['env_share_max_over_220'])), '']
    for p, label in (('05', '普通の速さ'), ('06', 'ゆっくり'), ('07', '速い打鍵')):
        if L[p]:
            ts = cmd_trace(L[p], out, tag='trace_%s' % {'05': 'normal', '06': 'slow', '07': 'fast'}[p])
            if ts:
                rise = [float(s[12]) for s in ts if s[12] != '']
                band = [float(s[15]) for s in ts if s[15] != '']
                rband = [float(s[22]) for s in ts if s[22] != '']
                md += ['## 遷移（%s-%s、%s）' % (p, dict(STEPS)[p], label), '',
                       '- 捕まえた押下 %d 回。立ち上がり 10→90%%：中央 %s ms' % (len(ts), f1(pct(rise, 0.5))),
                       '- 押下時に 30→閾値を通過する時間：中央 %s ms／解放時に閾値→30：中央 %s ms' % (f1(pct(band, 0.5)), f1(pct(rband, 0.5))),
                       '- 判定の余分な反転（チャタリング）: 記録区間内で合計 %d、解放の記録中に再び押下判定になった回数 %d' % (sum(s[24] for s in ts), sum(s[28] for s in ts)), '']
    scans = [lg for p in ('01', '02', '03', '04', '05', '06', '07') for lg in L[p]]
    sc = cmd_scan(scans, out) if scans else None
    if sc:
        md += ['## 走査（A 版の全ログ）', '',
               '- 平均 %.0f Hz（周期 平均 %.0f µs、最小 %d、最大 %d µs、99%% は %s µs 以下）' % (sc['scan_rate_hz'], sc['period_avg_us'], sc['period_min_us'], sc['period_max_us'], sc.get('period_p99_upper_us')),
               '- acquire_adc（80 交点）平均 %.0f µs = 1 交点 %.1f µs' % (sc['acquire_avg_us'], sc['acquire_per_crosspoint_us']), '']
    if L['09']:
        cmd_scan(L['08'] + L['09'], out, tag='scan_B', quiet=False)
        if L['03']:
            ab = cmd_ab(L['03'], L['09'], out)
            if ab['focus']:
                dif = [b - a for _, _, a, b in ab['focus']]
                md += ['## パージ順序 A/B（03-leak と 09-B-leak）', '',
                       '- 最下段キー → 同じ列の行 0：B−A 中央 %.1f（%.1f〜%.1f、%d 組）。報告書の推定 −18〜−6' % (pct(dif, 0.5), min(dif), max(dif), len(dif)), '']
            if ab['worst']:
                w = ab['worst']
                md += ['- 全組合せで B−A の最大: %s（%s(%s) 押下中の %s(%s)）' % (w[8], w[0], w[1], w[2], w[3]), '']
    if L['01'] and L['10']:
        dr = cmd_drift(L['01'], L['10'], out)
        if dr:
            md += ['## 30 分後のドリフト（01-idle と 10-idle-30min、任意）', '',
                   '- 平均の差の最大 %s（%s）。§9 基準「30 以下」: %s%s' % (f1(dr['worst'][1]), dr['worst'][0], '満たす' if abs(dr['worst'][1]) <= 30 else '満たさない',
                                                                    '' if dr['same_cal'] else '（注意：途中で挿し直したため校正値が違う。差は CAL 基準で出した）'), '']
    md += ['---', '', '数字の読み方と、各 CSV の列の意味は docs/m1/README.md を参照。']
    path = os.path.join(out, 'summary.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print('wrote', path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('all')
    a.add_argument('logdir')
    a.add_argument('--out', default=None)
    for name in ('baseline', 'press', 'trace', 'scan'):
        s = sub.add_parser(name)
        s.add_argument('logs', nargs='+')
        s.add_argument('--out', default='m1-out')
        if name == 'press':
            s.add_argument('--baseline', nargs='*', default=None, help='idle log(s) for sigma / p-p (default: idle parts of the press logs)')
    s = sub.add_parser('pinky')
    s.add_argument('logs', nargs='+')
    s.add_argument('--key', default='r2c7')
    s.add_argument('--out', default='m1-out')
    s = sub.add_parser('ab')
    s.add_argument('log_a')
    s.add_argument('log_b')
    s.add_argument('--out', default='m1-out')
    args = ap.parse_args(argv)
    if args.cmd == 'all':
        cmd_all(args.logdir, args.out or os.path.join(args.logdir, 'm1-out'))
    elif args.cmd == 'baseline':
        cmd_baseline(load(args.logs), args.out)
    elif args.cmd == 'press':
        cmd_press(load(args.logs), args.out, baseline_logs=load(args.baseline) if args.baseline else None)
    elif args.cmd == 'pinky':
        cmd_pinky(load(args.logs), args.out, key=parse_kid(args.key))
    elif args.cmd == 'trace':
        cmd_trace(load(args.logs), args.out)
    elif args.cmd == 'scan':
        cmd_scan(load(args.logs), args.out)
    elif args.cmd == 'ab':
        cmd_ab(load([args.log_a]), load([args.log_b]), args.out)


if __name__ == '__main__':
    main()
