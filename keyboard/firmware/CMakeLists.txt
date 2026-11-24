# The fade driver goes into the ZMK app of the parts whose devicetree has it: the two halves.
if(CONFIG_DT_HAS_LED_STRIP_FADE_ENABLED)
  target_sources(app PRIVATE src/led_strip_fade.c)
endif()
