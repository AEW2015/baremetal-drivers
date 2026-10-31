/* SPDX-License-Identifier: MIT-0 */
#include "driver.h"
static uint64_t read64(struct ddr_probe *d, unsigned off)
{ uint32_t lo=d->read(d->context,off); return lo | ((uint64_t)d->read(d->context,off+4)<<32); }
uint64_t ddr_probe_pattern(uint32_t s,uint32_t i)
{ return ((uint64_t)(s^i)<<32) | (uint32_t)(s+i); }
int ddr_probe_drain(struct ddr_probe *d,unsigned polls)
{
    if (!d || !d->read || !polls) return -1;
    while (polls--) if (!(d->read(d->context,DDR_STATUS)&DDR_BUSY)) return 0;
    return -4;
}
int ddr_probe_run(struct ddr_probe *d,uint64_t address,uint32_t words,
                  uint32_t seed,unsigned polls,struct ddr_result *out)
{
    uint64_t lo,hi,bytes=(uint64_t)words*8;
    if (!d || !d->read || !d->write || !out || !polls) return -1;
    *out=(struct ddr_result){0};
    if (d->read(d->context,DDR_ID)!=0x44445231 || d->read(d->context,DDR_ABI)!=0x10000) return -1;
    if (d->read(d->context,DDR_STATUS)&DDR_BUSY) return -3;
    lo=read64(d,DDR_ALLOWED_BASE);hi=read64(d,DDR_ALLOWED_END);
    if (!words || address%8 || lo>=hi || address<lo || address>=hi || bytes>hi-address || address+bytes>=(1ULL<<40)) return -2;
    d->write(d->context,DDR_BASE,(uint32_t)address);
    d->write(d->context,DDR_BASE+4,(uint32_t)(address>>32));
    d->write(d->context,DDR_WORDS,words); d->write(d->context,DDR_SEED,seed);
    d->write(d->context,DDR_CONTROL,1);
    while (polls--) {
        out->status=d->read(d->context,DDR_STATUS);
        if (out->status&DDR_DONE) break;
        if (out->status&DDR_TIMEOUT) return -4;
    }
    if (!(out->status&DDR_DONE)) return -4;
    out->error=d->read(d->context,DDR_ERROR);
    out->verified=d->read(d->context,DDR_VERIFIED);
    out->address=read64(d,DDR_FAIL_ADDRESS);out->expected=read64(d,DDR_EXPECTED);
    out->observed=read64(d,DDR_OBSERVED);out->cycles=read64(d,DDR_CYCLES);
    if (out->status&DDR_TIMEOUT) return -4;
    return !(out->status&(DDR_FAULT|DDR_REJECTED|DDR_BUSY)) && out->verified==words ? 0 : -5;
}
