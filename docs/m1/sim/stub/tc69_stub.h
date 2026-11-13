/* Host stub standing in for QMK_KEYBOARD_H when matrix.c is compiled by docs/m1/sim. */
#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#define MATRIX_ROWS 5
#define MATRIX_COLS 16
typedef uint16_t matrix_row_t;
typedef int pin_t;
enum { GP0, GP1, GP2, GP3, GP4, GP5, GP6, GP7, GP8, GP9, GP10, GP11, GP12, GP13, GP14, GP15,
       GP16, GP17, GP18, GP19, GP20, GP21, GP22, GP23, GP24, GP25, GP26, GP27, GP28, GP29 };
void gpio_set_pin_output(pin_t p);
void gpio_set_pin_input(pin_t p);
void gpio_write_pin(pin_t p, bool v);
void gpio_write_pin_high(pin_t p);
void gpio_write_pin_low(pin_t p);
void wait_us(uint32_t us);
void matrix_init_user(void);
void matrix_scan_user(void);
void matrix_init_kb(void);
void matrix_scan_kb(void);
