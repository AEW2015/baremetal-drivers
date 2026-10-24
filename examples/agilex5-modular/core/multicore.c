/* Direct EL3 core release, adapted from matching ATF bl31_plat_setup.c.
 * Not PSCI: uses reset-vector/power-channel registers under exclusive ownership.
 * Fresh bootstrap required; this test deliberately leaves secondaries parked.
 */
#include "common.h"
extern void secondary_entry(void);
void example_main(void){
 text("HPS MULTICORE EXAMPLE BEGIN\n");
 value("MPIDR = ",SYS(mpidr_el1));value("Boot config = ",R(0x10d14058));
 value("CPU in reset = ",R(0x10d11090));value("PCH control = ",R(0x10d14050));
 volatile uint64_t *records=(volatile uint64_t *)0x85300000;
 for(unsigned i=0;i<16;i++)records[i]=0;
 /* Stable parking instructions outside reloadable example images. */
 R(0x82010000)=0xd503205f;R(0x82010004)=0x17ffffff;barrier();
 uint64_t boot_config=R(0x10d14058)&0xc00;
 if(boot_config){text("FAIL MULTICORE: expects A55 boot configuration\n");return;}
 /* Common ATF boot scratch COLD3 magic: secondary SMP request. */
 uint32_t scratch=R(0x10d1220c);
 R(0x10d1220c)=(scratch&~0x3cU)|8;
 R64(0x10d110a0)=(uintptr_t)secondary_entry>>2;
 R64(0x10d110a8)=(uintptr_t)secondary_entry>>2;
 R64(0x10d110b0)=(uintptr_t)secondary_entry>>2;
 barrier();
 R(0x10d14050)|=(0xe<<1);barrier();R(0x10d11094)=0xe;
 unsigned remaining=0xe;
 for(unsigned n=0;n<10000000&&remaining;n++){
  for(unsigned cpu=1;cpu<4;cpu++)if(records[cpu*4]==0xcafe)remaining&=~(1U<<cpu);
 }
 for(unsigned cpu=1;cpu<4;cpu++){
  if(records[cpu*4]!=0xcafe||((records[cpu*4+1]>>8)&255)!=cpu||
     ((records[cpu*4+2]>>4)&4095)!=(cpu==1?0xd05:0xd0b))remaining|=1U<<cpu;
  value("Secondary record = ",records[cpu*4]);
  value("Secondary MPIDR = ",records[cpu*4+1]);value("Secondary MIDR = ",records[cpu*4+2]);
 }
 text(!remaining?"PASS MULTICORE: three secondary cores executed and published records\n":"FAIL MULTICORE: secondary record timeout\n");
}
