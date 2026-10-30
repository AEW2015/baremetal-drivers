/* Simics model PIO read/write lesson; does not claim physical I/O. */
#include <stdint.h>
#include "common.h"

#define LWHPS2FPGA_BASE 0x20000000ULL
#define SYSID_ADDR      (LWHPS2FPGA_BASE + 0x00010000ULL)
#define BUTTON_DATA     (LWHPS2FPGA_BASE + 0x00010060ULL)
#define DIPSW_DATA      (LWHPS2FPGA_BASE + 0x00010070ULL)
#define LED_DATA        (LWHPS2FPGA_BASE + 0x00010080ULL)
#define INPUT_MASK      0x00000001U
#define LED_MASK        0xffffffffU
#define PATTERN_A       0xa55aa55bU
#define PATTERN_B       0x5aa55aa5U

#ifndef PIO_NEGATIVE
#define PIO_NEGATIVE 0
#endif

static unsigned failures;

static void check(int ok, const char *label)
{
    if (ok) {
        text("PASS ");
    } else {
        text("FAIL ");
        failures++;
    }
    text(label);
    text("\n");
}

#if PIO_NEGATIVE
static __attribute__((noinline)) int masked_equal(uint32_t actual,
                                                  uint32_t expected,
                                                  uint32_t mask)
{
    return (actual & mask) == expected;
}
#endif

void example_main(void)
{
    uint32_t button0, button1, dipsw0, dipsw1;
    uint64_t sysid0, sysid1;
    uint32_t led_saved, led_read;
    const uint32_t patterns[] = {PATTERN_A, PATTERN_B};
    text("PIO_AUDIT_BEGIN\n");

    button0 = R(BUTTON_DATA);
    barrier();
    button1 = R(BUTTON_DATA);
    dipsw0 = R(DIPSW_DATA);
    barrier();
    dipsw1 = R(DIPSW_DATA);
    sysid0 = R64(SYSID_ADDR);
    barrier();
    sysid1 = R64(SYSID_ADDR);

    value("BUTTON_DATA=", button0);
    value("DIPSW_DATA=", dipsw0);
    value("SYSID_DATA=", sysid0);
    check(button0 == button1 && (button0 & ~INPUT_MASK) == 0U,
          "BUTTON_INPUT stable, field=bit0");
    check(dipsw0 == dipsw1 && (dipsw0 & ~INPUT_MASK) == 0U,
          "DIPSW_INPUT stable, field=bit0");
    check(sysid0 == sysid1, "SYSID 64-bit read stable");

    led_saved = R(LED_DATA);
    value("LED_DATA_SAVED=", led_saved);

    for (unsigned i = 0; i < sizeof(patterns) / sizeof(patterns[0]); i++) {
        R(LED_DATA) = patterns[i] & LED_MASK;
        barrier();
        led_read = R(LED_DATA);
        value(i == 0 ? "LED_READBACK_A=" : "LED_READBACK_B=", led_read);
        check(led_read == patterns[i], i == 0 ? "LED pattern A readback" : "LED pattern B readback");
    }

#if PIO_NEGATIVE
    /* Deliberately omit the modeled MSB from the expected mask. This control
       verifies that an invalid expectation rejects the known-good readback. */
    R(LED_DATA) = 0x80000001U;
    barrier();
    led_read = R(LED_DATA);
    check(led_read == 0x80000001U, "negative control known-good LED write");
    check(!masked_equal(led_read, 0x80000001U, 0x7fffffffU),
          "PIO_NEGATIVE bad expected mask rejected");
#endif

    R(LED_DATA) = led_saved & LED_MASK;
    barrier();
    check(R(LED_DATA) == led_saved, "LED original value restored");
    if (failures == 0U) {
        text("PIO_AUDIT_COMPLETE status=0\n");
    } else {
        text("PIO_AUDIT_COMPLETE status=1\n");
    }
}
