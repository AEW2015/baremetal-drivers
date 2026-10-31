/* SPDX-License-Identifier: MIT-0 */
#include "driver.h"
static void barrier(void) {
#if defined(__aarch64__)
    __asm__ volatile("dsb sy" ::: "memory");
#else
    __asm__ volatile("" ::: "memory");
#endif
}
static uint32_t rd(void *p,unsigned off) { barrier();uint32_t v=*(volatile uint32_t *)((uintptr_t)p+off);barrier();return v; }
static void wr(void *p,unsigned off,uint32_t v) { barrier();*(volatile uint32_t *)((uintptr_t)p+off)=v;barrier(); }
struct ddr_probe ddr_probe_mmio(uintptr_t base) { return (struct ddr_probe){(void *)base,rd,wr}; }
