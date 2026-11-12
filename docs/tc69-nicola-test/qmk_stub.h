#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef struct { bool pressed; uint16_t time; } keyevent_t;
typedef struct { keyevent_t event; } keyrecord_t;
#define SAFE_RANGE 0x7E40
enum { KC_NO=0, KC_A=4, KC_W=0x1A, KC_ENT=0x28, KC_ESC=0x29, KC_SPC=0x2C, KC_APP=0x65,
       KC_LCTL=0xE0, KC_LSFT, KC_LALT, KC_LGUI, KC_RCTL, KC_RSFT, KC_RALT, KC_RGUI,
       MO_FUNC=0x5220 };
#define SS_TAP(k) "<" #k ">"
#define SS_LSFT(s) "<S+" s ">"
void send_string(const char *s);
void layer_on(uint8_t l); void layer_off(uint8_t l);
uint8_t get_mods(void); uint8_t bitpop(uint8_t);
uint16_t timer_read(void);
