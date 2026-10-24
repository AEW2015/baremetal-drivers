#include "lab.h"
extern void trigger_break(void),break_instruction(void),break_resume(void);
volatile unsigned exceptions_seen;
static void handle_break(unsigned kind) {
 if (kind!=0 || last_exception.esr>>26!=0x3c || (last_exception.esr&0xffff)!=0x123 ||
     last_exception.elr!=(uintptr_t)break_instruction) fail("unexpected BRK syndrome");
 value("ESR_EL3=",last_exception.esr);
 value("ELR_EL3=",last_exception.elr);
 text("FAR_EL3 is not meaningful for BRK\n");
 exceptions_seen++;
 MSR(elr_el3,(uintptr_t)break_resume);
}
int main(void) {
 lab_begin("exception");
 exception_handler=handle_break;
 trigger_break();
 check(exceptions_seen==1,"BRK_SYNDROME_AND_RETURN");
 check(last_exception.elr==(uintptr_t)break_instruction,"FAULT_PC_CAPTURED");
 lab_done(0);
}
