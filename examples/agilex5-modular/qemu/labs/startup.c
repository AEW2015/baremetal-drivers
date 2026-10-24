#include "lab.h"
volatile uint64_t initialized=0x123456789abcdef0ULL;
volatile uint8_t zero_bytes[257];
extern uint8_t __data_load[],__data_start[],__data_end[],__bss_start[],__bss_end[],__stack_top[];
int main(void) {
 lab_begin("startup");
 check(initialized==0x123456789abcdef0ULL,"DATA_RELOCATED");
 check((uintptr_t)__data_load!=(uintptr_t)__data_start,"DISTINCT_LOAD_AND_RUNTIME_ADDRESSES");
 for (uintptr_t p=(uintptr_t)__bss_start;p<(uintptr_t)__bss_end;p++)
  if (*(volatile uint8_t *)p) fail("BSS_ZERO");
 check(1,"BSS_ZERO");
 uint64_t sp; __asm__ volatile("mov %0,sp":"=r"(sp));
 check(!(sp&15) && sp<(uintptr_t)__stack_top && sp>(uintptr_t)__stack_top-4096,"STACK_ALIGNED_IN_RANGE");
 value("DATA_LOAD=",(uintptr_t)__data_load);
 value("DATA_RUNTIME=",(uintptr_t)__data_start);
 value("BSS_START=",(uintptr_t)__bss_start);
 value("BSS_END=",(uintptr_t)__bss_end);
 value("SP=",sp);
 lab_done(0);
}
