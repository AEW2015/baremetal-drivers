#include "common.h"
void board_exception(void){
 text("FAIL EXCEPTION: EL3 ESR, ELR and FAR follow\n");
 value("ESR_EL3 = ",SYS(esr_el3));value("ELR_EL3 = ",SYS(elr_el3));value("FAR_EL3 = ",SYS(far_el3));
 for(;;)__asm__ volatile("wfi");
}
