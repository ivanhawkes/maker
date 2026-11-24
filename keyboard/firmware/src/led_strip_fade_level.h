/*
 * The fade's arithmetic, apart from the driver so that led_strip_fade_test.c can run it on the
 * computer. A level is 0 (black) to 256 (the frame as ZMK gave it).
 */

#pragma once

#include <stdint.h>

/*
 * The level to show now. It is at most what the idle time allows: full until fade_out_ms
 * before the idle timeout, then falling in a straight line to black at the timeout. And it
 * rises no faster than black to full in fade_in_ms, from the level shown since_shown_ms ago.
 */
static inline int fade_level(int shown, int64_t since_shown_ms, int64_t idle_ms, int timeout_ms,
                             int fade_in_ms, int fade_out_ms) {
    int64_t out = (timeout_ms - idle_ms) * 256 / fade_out_ms;
    /* rounded up, so that steps which each lose a fraction still reach full on time */
    int64_t in = shown + (since_shown_ms * 256 + fade_in_ms - 1) / fade_in_ms;
    int64_t level = out < in ? out : in;
    return level < 0 ? 0 : level > 256 ? 256 : (int)level;
}
