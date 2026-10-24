/* Load only while debugging a failed application; does not reinitialize DDR. */
#include "common.h"
void example_main(void){
 text("HPS FAULT PROBE BEGIN\n");
 value("ESR_EL3 = ",SYS(esr_el3));value("ELR_EL3 = ",SYS(elr_el3));value("FAR_EL3 = ",SYS(far_el3));
 value("SCTLR_EL3 = ",SYS(sctlr_el3));value("CPTR_EL3 = ",SYS(cptr_el3));
 text("HPS FAULT PROBE COMPLETE\n");
}
