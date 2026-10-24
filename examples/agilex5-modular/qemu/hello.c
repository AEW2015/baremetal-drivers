/* Generic QEMU virt exercise. PL011 UART/RAM addresses are NOT Agilex addresses. */
#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
static void text(const char *s){
 while(*s){while(REG(0x09000018)&(1U<<5)){} REG(0x09000000)=(uint8_t)*s++;}
}
volatile uint64_t source[512],destination[512];
uint32_t vector_a[4]={1,2,3,4},vector_b[4]={10,20,30,40},vector_result[4];
volatile unsigned failures;
extern void qemu_neon_add(const uint32_t *,const uint32_t *,uint32_t *);
/* A convenient second breakpoint after all checks; no OS or C runtime used. */
__attribute__((noreturn,noinline)) void qemu_done(unsigned status){
 uint64_t reason[2]={0x20026,status};
 register uint64_t operation __asm__("x0")=0x20; /* SYS_EXIT_EXTENDED */
 register void *arguments __asm__("x1")=reason;
 __asm__ volatile("hlt #0xf000"::"r"(operation),"r"(arguments):"memory");
 for(;;)__asm__ volatile("wfi");
}
int main(void){
 text("QEMU VIRT AARCH64 BEGIN\n");
 uint64_t el;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));
 if((el>>2)!=3){text("FAIL EL3\n");qemu_done(1);}
 text("PASS EL3\n");
 qemu_neon_add(vector_a,vector_b,vector_result);
 for(unsigned i=0;i<4;i++)if(vector_result[i]!=(i+1)*11)failures++;
 text(failures?"FAIL NEON\n":"PASS NEON: 11 22 33 44\n");
 for(unsigned i=0;i<512;i++){source[i]=0x1234567800000000ULL^i;destination[i]=0;}
 for(unsigned i=0;i<512;i++)destination[i]=source[i];
 for(unsigned i=0;i<512;i++)if(destination[i]!=source[i])failures++;
 text(failures?"FAIL MEMORY\n":"PASS MEMORY: 4096-byte CPU copy\n");
 text(failures?"QEMU EXAMPLE FAILED\n":"QEMU EXAMPLE COMPLETE\n");
 qemu_done(failures?1:0);
}
