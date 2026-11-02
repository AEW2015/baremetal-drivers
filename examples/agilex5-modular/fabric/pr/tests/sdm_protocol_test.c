/* Run the actual loader transport against bounded mailbox-register emulation. */
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define BOARD_EXAMPLE_COMMON_H
#define POLLS 100
static uint32_t regs[0x500/4], wire[8], argument[4];
static unsigned wire_len, suppress, last_cmd;
static uint64_t el=12, sctlr;
static uint32_t *reg(uintptr_t address) {
 assert(address>=0x10a30000U && address<0x10a30500U);
 if(regs[0x400/4]) {
  regs[0x400/4]=0;
  unsigned out=regs[0x20/4]&31;
  last_cmd=regs[0x40/4+out];
  for(unsigned i=0;i<3;i++)argument[i]=regs[0x40/4+((out+i+1)&31)];
  regs[0x20/4]=regs[0];
  if(!suppress)for(unsigned i=0;i<wire_len;i++) {
   unsigned in=regs[0x24/4]&15;
   regs[0xc0/4+in]=wire[i];regs[0x24/4]=(in+1)&15;
  }
 }
 return &regs[(address-0x10a30000U)/4];
}
#define R(address) (*reg(address))
#define SYS(name) (!strcmp(#name,"CurrentEL")?el:sctlr)
static void barrier(void) {}
static void text(const char *s) {(void)s;}
static void value(const char *s,uint64_t v) {(void)s;(void)v;}
#include "../sdm_loader.c"
static void reset(void) {
 memset(regs,0,sizeof(regs));memset(wire,0,sizeof(wire));
 wire[0]=0x1e000000;wire_len=1;suppress=0;
}
int main(void) {
 uint32_t response[6],args[3]={256,0x08000000,128};unsigned n;
 reset();regs[0]=regs[0x20/4]=30;regs[4/4]=regs[0x24/4]=15;
 wire[0]=0x1e002000;wire[1]=2;wire[2]=128;wire_len=3;n=6;
 assert(!command(6,0,0,0,response,&n));assert(n==2&&response[0]==2&&response[1]==128);
 assert(regs[4/4]==2); /* Response ring wrapped. */
 reset();regs[0]=regs[0x20/4]=30;n=0;
 assert(!command(8,args,3,1,response,&n));assert(last_cmd==0x1e003808);
 assert(argument[0]==256&&argument[1]==0x08000000&&argument[2]==128);
 assert(regs[0]==2); /* Command + descriptor wrapped. */
 reset();regs[0]=1;n=6;assert(command(6,0,0,0,response,&n)==-2);
 assert(!regs[0x400/4]); /* Busy mailbox untouched. */
 reset();wire[0]=0x2e000000;n=6;assert(command(6,0,0,0,response,&n)==-4);
 assert(regs[4/4]==0); /* Other client's response left intact. */
 reset();wire[0]=0x1e000005;n=6;assert(command(6,0,0,0,response,&n)==-6);
 reset();wire[0]=0x1e002000;wire[1]=1;wire[2]=2;wire_len=3;n=1;
 assert(command(6,0,0,0,response,&n)==-7);assert(regs[4/4]==3);
 reset();suppress=1;n=6;assert(command(6,0,0,0,response,&n)==-3);
 struct pr_image invalid={0,4,0};el=8;assert(pr_sdm_load(&invalid)==-10);
 el=12;sctlr=4;assert(pr_sdm_load(&invalid)==-10);
 sctlr=0;assert(pr_sdm_load(&invalid)==-11);
 return 0;
}
