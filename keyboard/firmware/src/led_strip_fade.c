/*
 * A led strip that passes its frames on to another one, dimmed. ZMK has no fade, so the
 * halves' lighting goes through this: black to full over fade-in-ms whenever it lights, and
 * full to black over the last fade-out-ms before ZMK's idle timeout, when ZMK itself switches
 * the lighting and its supply off. It only ever dims, so the shield's brightness cap holds.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT led_strip_fade

#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/led_strip.h>
#include <zephyr/kernel.h>

#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/rgb_underglow.h>
#include <zmk/workqueue.h>

#include "led_strip_fade_level.h"

#define STRIP DEVICE_DT_GET(DT_INST_PHANDLE(0, led_strip))
#define LENGTH DT_INST_PROP(0, chain_length)
#define FADE_IN_MS DT_INST_PROP(0, fade_in_ms)
#define FADE_OUT_MS DT_INST_PROP(0, fade_out_ms)
#define STEP_MS 10     /* between frames while lighting up; ZMK's own are 50 ms apart */
#define RESTART_MS 200 /* no frame for this long: the lighting was off, so it lights from black */

BUILD_ASSERT(FADE_OUT_MS < CONFIG_ZMK_IDLE_TIMEOUT, "the fade-out must fit before the idle timeout");
/* firmware/config/ is merged after the shield's settings and could raise the cap: stop the build. */
BUILD_ASSERT(CONFIG_ZMK_RGB_UNDERGLOW_BRT_MAX <= 20,
             "the board's power switch limits the LEDs to a 20 % brightness cap (docs/pcb.md)");

static struct led_rgb frame[LENGTH]; /* the last frame from ZMK, as given */
static uint32_t last_press;          /* one word, so the key listener's write cannot tear */
static uint32_t last_shown;
static int shown; /* the level of the last frame sent, 0 to 256 */

static void refresh(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(refresh_work, refresh);

/* Runs only on ZMK's low priority queue (its frames, and refresh), so nothing here races. */
static int show(void) {
    static struct led_rgb out[LENGTH];
    uint32_t now = k_uptime_get_32();
    uint32_t idle = now - last_press;

    if (now - last_shown > RESTART_MS) {
        shown = 0;
        last_shown = now;
    }
    shown = fade_level(shown, now - last_shown, idle, CONFIG_ZMK_IDLE_TIMEOUT, FADE_IN_MS,
                       FADE_OUT_MS);
    last_shown = now;

    for (int i = 0; i < LENGTH; i++) {
        out[i].r = frame[i].r * shown / 256;
        out[i].g = frame[i].g * shown / 256;
        out[i].b = frame[i].b * shown / 256;
    }
    if (shown < fade_level(256, 0, idle, CONFIG_ZMK_IDLE_TIMEOUT, FADE_IN_MS, FADE_OUT_MS)) {
        k_work_reschedule_for_queue(zmk_workqueue_lowprio_work_q(), &refresh_work,
                                    K_MSEC(STEP_MS));
    }
    return led_strip_update_rgb(STRIP, out, LENGTH);
}

static void refresh(struct k_work *work) {
    bool on;

    /* Nothing is sent once ZMK has the lighting off: its supply is off too. */
    if (zmk_rgb_underglow_get_state(&on) == 0 && on) {
        show();
    }
}

static int fade_update_rgb(const struct device *dev, struct led_rgb *pixels, size_t count) {
    memcpy(frame, pixels, count * sizeof(*pixels)); /* count is at most LENGTH: fade_length */
    return show();
}

static size_t fade_length(const struct device *dev) { return LENGTH; }

static int fade_init(const struct device *dev) { return device_is_ready(STRIP) ? 0 : -ENODEV; }

static int fade_key_listener(const zmk_event_t *eh) {
    last_press = k_uptime_get_32();
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(led_strip_fade, fade_key_listener);
ZMK_SUBSCRIPTION(led_strip_fade, zmk_position_state_changed);

static DEVICE_API(led_strip, fade_api) = {
    .update_rgb = fade_update_rgb,
    .length = fade_length,
};

DEVICE_DT_INST_DEFINE(0, fade_init, NULL, NULL, NULL, POST_KERNEL, CONFIG_LED_STRIP_INIT_PRIORITY,
                      &fade_api);
