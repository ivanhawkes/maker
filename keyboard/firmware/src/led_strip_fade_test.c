/*
 * Checks the fade's arithmetic on the computer, with the keyboard's own times:
 *
 *     cc -o /tmp/fade_test firmware/src/led_strip_fade_test.c && /tmp/fade_test
 */

#include <assert.h>
#include <stdio.h>

#include "led_strip_fade_level.h"

#define LEVEL(shown, since, idle) fade_level(shown, since, idle, 65000, 50, 5000)

int main(void) {
    /* Lighting up: black on the first frame, then about a fifth more every 10 ms, full at 50 ms. */
    int level = LEVEL(0, 0, 0), last = 0;
    assert(level == 0);
    for (int ms = 10; ms <= 50; ms += 10) {
        level = LEVEL(level, 10, ms);
        assert(level > last && level - ms * 256 / 50 >= 0 && level - ms * 256 / 50 <= 5);
        last = level;
    }
    assert(level == 256 && LEVEL(256, 10, 60) == 256);

    /* Full for 60 s after the last key, half-way at 62.5 s, black from 65 s on. */
    assert(LEVEL(256, 50, 59999) == 256 && LEVEL(256, 50, 60000) == 256);
    assert(LEVEL(256, 50, 62500) == 128);
    assert(LEVEL(256, 50, 64999) == 0 && LEVEL(256, 50, 65000) == 0);
    assert(LEVEL(256, 50, 4000000000LL) == 0); /* idle for weeks: no overflow */
    for (int idle = 60000; idle < 65000; idle += 50) {
        assert(LEVEL(256, 50, idle + 50) <= LEVEL(256, 50, idle));
    }

    /* A key pressed half-way through the fade-out: back to full within 25 ms, not at once. */
    assert(LEVEL(128, 10, 0) == 180 && LEVEL(128, 25, 0) == 256);

    /* The fade-in never passes what the idle time allows. */
    assert(LEVEL(0, 1000, 62500) == 128);
    puts("fade levels: ok");
    return 0;
}
