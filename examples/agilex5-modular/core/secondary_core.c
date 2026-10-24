/* Callable example for nonsecure EL1/EL2 under a PSCI-capable resident BL31.
 * Do not call from the current EL3 diagnostic bootstrap. Discover the target
 * MPIDR from the board's CPU topology. The entry must be physical executable
 * memory with its own startup/stack and cache maintenance completed.
 */
#include <stdint.h>
int64_t example_psci_cpu_on(uint64_t target_mpidr,uintptr_t entry,uint64_t context){
 register uint64_t x0 __asm__("x0")=0xc4000003;
 register uint64_t x1 __asm__("x1")=target_mpidr;
 register uint64_t x2 __asm__("x2")=entry;
 register uint64_t x3 __asm__("x3")=context;
 __asm__ volatile("smc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3):"memory","x4","x5","x6","x7");
 return (int64_t)x0;
}
