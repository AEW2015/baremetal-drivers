#include "lab.h"
volatile uint64_t source[512],destination[512];
volatile unsigned mismatch_count,first_bad_index;
/* Separate functions make the unwanted write easy to catch with a watchpoint. */
__attribute__((noinline)) void inject_corruption(void) { destination[37]^=1; }
__attribute__((noinline)) void copy_complete(void) { __asm__ volatile("" ::: "memory"); }
int main(void) {
 lab_begin("corruption");
 for (unsigned i=0;i<512;i++) { source[i]=0x1234567800000000ULL^i; destination[i]=source[i]; }
 copy_complete();
#ifndef OMIT_CORRUPTION
 inject_corruption();
#endif
 first_bad_index=512;
 for (unsigned i=0;i<512;i++) if (destination[i]!=source[i]) {
  if (!mismatch_count) first_bad_index=i;
  mismatch_count++;
 }
 check(mismatch_count==1 && first_bad_index==37,"EXPECTED_CORRUPTION_INDEX_37");
 value("EXPECTED=",source[first_bad_index]);
 value("ACTUAL=",destination[first_bad_index]);
 destination[first_bad_index]=source[first_bad_index];
 for (unsigned i=0;i<512;i++) if (destination[i]!=source[i]) fail("REPAIRED_COPY");
 check(1,"REPAIRED_COPY_512_WORDS");
 lab_done(0);
}
