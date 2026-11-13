#pragma once
#include <stdint.h>
uint32_t timer_read32(void);
#define TIMER_DIFF_32(a, b) ((uint32_t)((a) - (b)))
static inline uint32_t timer_elapsed32(uint32_t t) { return TIMER_DIFF_32(timer_read32(), t); }
