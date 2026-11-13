/*
 * Host simulation harness for the TC69 diagnostic firmware (M1 toolkit).
 *
 * Compiles the REAL keyboards/tc69/matrix.c (with its diag code) against the
 * stubs in ./stub and a toy electrical model, and prints what `qmk console`
 * would print. Its only purpose is to exercise the firmware's diagnostic code
 * paths and the host-side analyser (m1_analyze.py) end to end. The analogue
 * numbers it produces (baselines, deltas, noise, leakage, residuals) are
 * ARBITRARY and say nothing about the real TC69.
 *
 * Scenario on stdin, one command per line, times in ms, sorted by time:
 *   key  <row> <col>                      declare a physical key
 *   seed <n>
 *   move <row> <col> <t_ms> <depth 0..1> <ramp_ms>   key travel -> depth, linear ramp
 *   end  <t_ms>
 */
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include "tc69_stub.h"
#include "analog.h"
#include "print.h"
#include "timer.h"
#include "ch.h"

extern uint8_t matrix_scan(void);
extern void    matrix_init(void);

/* ---- simulated time (us) ---- */
static double sim_us;
uint32_t      timer_read32(void) { return (uint32_t)(sim_us / 1000.0); }
uint32_t      chVTGetSystemTimeX(void) { return (uint32_t)sim_us; }

/* ---- console: printing costs time like a 32 B / 1 ms HID endpoint ---- */
static char linebuf[4096];
static int  linelen;
int         uprintf(const char *fmt, ...) {
    char    tmp[2048];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(tmp, sizeof tmp, fmt, ap);
    va_end(ap);
    for (int i = 0; i < n; ++i) {
        if (tmp[i] == '\n') {
            linebuf[linelen] = 0;
            printf("Shobon:TC69 Oyayubi Shift:1: %s\n", linebuf);
            linelen = 0;
        } else if (linelen < (int)sizeof linebuf - 1) {
            linebuf[linelen++] = tmp[i];
        }
    }
    sim_us += n * 31.25; /* ~32 kB/s */
    return n;
}

/* ---- toy electrical model ---- */
static const pin_t ROWP[5] = {GP2, GP4, GP1, GP0, GP7};
static const pin_t COLP[4] = {GP3, GP6, GP27, GP26};
#define PURGE GP28
static bool   pin_level[30], pin_out[30];
static bool   haskey[16][5];
static double base[16][5], full[16][5];
static double res_v[16], res_t[16]; /* residual on an unselected column (counts, time set) */
#define RES_AMP 1200.0              /* arbitrary */
#define RES_TAU 2.0                 /* us */

typedef struct {
    double from, to, t0, ramp;
} travel_t;
static travel_t trv[16][5];

static double amount(int c, int r) {
    travel_t *k = &trv[c][r];
    double    t = sim_us / 1000.0;
    if (t <= k->t0) return k->from;
    if (k->ramp <= 0 || t >= k->t0 + k->ramp) return k->to;
    return k->from + (k->to - k->from) * (t - k->t0) / k->ramp;
}

static int sel_col(void) {
    int j = 0;
    for (int b = 0; b < 4; ++b)
        if (pin_level[COLP[b]]) j |= 1 << b;
    return j;
}

static double gauss(void) {
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0), u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2 * log(u1)) * cos(6.283185307 * u2);
}

void gpio_set_pin_output(pin_t p) {
    pin_out[p] = true;
}
void gpio_set_pin_input(pin_t p) {
    pin_out[p] = false;
}
void gpio_write_pin(pin_t p, bool v) {
    if (p == PURGE && pin_out[p] && !v) res_v[sel_col()] = 0; /* purge drains the selected column */
    /* row falling edge: unselected columns with a pressed key on that row keep a negative charge */
    for (int r = 0; r < 5; ++r) {
        if (ROWP[r] == p && pin_level[p] && !v) {
            int j = sel_col();
            for (int c = 0; c < 16; ++c) {
                if (c == j || !haskey[c][r]) continue;
                double a = amount(c, r);
                if (a > 0.01) {
                    res_v[c] = -RES_AMP * a;
                    res_t[c] = sim_us;
                }
            }
        }
    }
    pin_level[p] = v;
}
void gpio_write_pin_high(pin_t p) {
    gpio_write_pin(p, true);
}
void gpio_write_pin_low(pin_t p) {
    gpio_write_pin(p, false);
}
void wait_us(uint32_t us) {
    sim_us += us;
}

int16_t analogReadPin(int pin) {
    (void)pin;
    sim_us += 2.0; /* driver overhead before the sample */
    int j = sel_col(), i = -1;
    for (int r = 0; r < 5; ++r)
        if (pin_level[ROWP[r]]) i = r;
    double v = 0;
    if (i >= 0) {
        v = base[j][i] + full[j][i] * amount(j, i) + 1.0 * gauss();
        for (int r = 0; r < 5; ++r) /* arbitrary static coupling */
            if (r != i && haskey[j][r]) v += 2.0 * amount(j, r);
        for (int c = 0; c < 16; ++c)
            if (c != j && haskey[c][i]) v -= 1.0 * amount(c, i);
    }
    if (res_v[j] != 0) v += res_v[j] * exp(-(sim_us - res_t[j]) / RES_TAU);
    sim_us += 3.0;
    if (v < 0) v = 0;
    if (v > 1023) v = 1023;
    return (int16_t)lround(v);
}


int main(void) {
    char   line[256];
    double end_ms = 0;
    struct ev {
        int    r, c;
        double t, depth, ramp;
    } *ev = NULL;
    int nev = 0, cap = 0;
    while (fgets(line, sizeof line, stdin)) {
        int    r, c, s;
        double t, d, rp;
        if (sscanf(line, "key %d %d", &r, &c) == 2) haskey[c][r] = true;
        else if (sscanf(line, "seed %d", &s) == 1) srand(s);
        else if (sscanf(line, "move %d %d %lf %lf %lf", &r, &c, &t, &d, &rp) == 5) {
            if (nev == cap) ev = realloc(ev, sizeof *ev * (cap = cap ? cap * 2 : 256));
            ev[nev++] = (struct ev){r, c, t, d, rp};
        } else if (sscanf(line, "end %lf", &t) == 1) end_ms = t;
    }
    for (int c = 0; c < 16; ++c)
        for (int r = 0; r < 5; ++r) {
            base[c][r] = 70 + 8 * r + 3 * c + 10 * (rand() / (double)RAND_MAX);
            full[c][r] = haskey[c][r] ? 250 + 80 * (rand() / (double)RAND_MAX) : 0;
        }
    matrix_init();
    int k = 0;
    while (sim_us / 1000.0 < end_ms) {
        while (k < nev && ev[k].t <= sim_us / 1000.0) {
            travel_t *tv = &trv[ev[k].c][ev[k].r];
            tv->from     = amount(ev[k].c, ev[k].r);
            tv->to       = ev[k].depth;
            tv->t0       = ev[k].t;
            tv->ramp     = ev[k].ramp;
            ++k;
        }
        matrix_scan();
        /* rest of the QMK main loop (USB, keymap, NICOLA): arbitrary 300..500 us, rare 2 ms stalls */
        sim_us += 300 + 200 * (rand() / (double)RAND_MAX) + ((rand() % 500) == 0 ? 2000 : 0);
    }
    return 0;
}
