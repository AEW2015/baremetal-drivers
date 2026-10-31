/* SPDX-License-Identifier: MIT-0 */
#ifndef DDR_PROBE_DRIVER_H
#define DDR_PROBE_DRIVER_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { DDR_ID=0, DDR_ABI=4, DDR_CONTROL=8, DDR_STATUS=12, DDR_BASE=16,
       DDR_WORDS=24, DDR_SEED=28, DDR_VERIFIED=32, DDR_FAIL_ADDRESS=36,
       DDR_EXPECTED=44, DDR_OBSERVED=52, DDR_CYCLES=60,
       DDR_ALLOWED_BASE=68, DDR_ALLOWED_END=76, DDR_WATCHDOG=84, DDR_ERROR=88 };
enum { DDR_BUSY=1, DDR_DONE=2, DDR_FAULT=4, DDR_REJECTED=8, DDR_TIMEOUT=16 };
struct ddr_probe {
    void *context;
    uint32_t (*read)(void *, unsigned);
    void (*write)(void *, unsigned, uint32_t);
};
struct ddr_result { uint32_t status, error, verified; uint64_t address, expected, observed, cycles; };
/* 0 success; -1 ABI/config, -2 unsafe range, -3 busy, -4 poll/RTL timeout,
 * -5 bus/data failure. Poll bounds cannot bound a stalled CPU MMIO access. */
int ddr_probe_run(struct ddr_probe *, uint64_t bus_address, uint32_t words,
                  uint32_t seed, unsigned polls, struct ddr_result *);
/* After -4, keep clocks/reset stable and poll for drain; never abandon AXI.
 * Returns 0 when idle, -4 while still busy, -1 for invalid arguments. */
int ddr_probe_drain(struct ddr_probe *, unsigned polls);
uint64_t ddr_probe_pattern(uint32_t seed, uint32_t index);
struct ddr_probe ddr_probe_mmio(uintptr_t base);
#ifdef __cplusplus
}
#endif
#endif
