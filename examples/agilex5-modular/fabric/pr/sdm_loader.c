/* Agilex 5 SDM indirect RECONFIG protocol, based on QPDS26.3 TF-A.
 * One in-flight block: never reuse an OCRAM buffer before its SDM acknowledgement.
 * Caller must freeze the PR partition, keep IRQs masked, and own the mailbox.
 */
#include "../../core/common.h"
#include "sdm_loader.h"
#define MBOX 0x10a30000U
#define OCRAM_BASE 0x1000U
#define OCRAM_CAPACITY 0x76000U
#define OCRAM_BACKUP 0x88400000U
#ifndef POLLS
#define POLLS 2000000U
#endif
static int response_word(uint32_t *word) {
 for (unsigned n=0;n<POLLS;n++) {
  unsigned out=R(MBOX+4)&15;
  if(out!=(R(MBOX+0x24)&15)) {
   *word=R(MBOX+0xc0+4*out);barrier();R(MBOX+4)=(out+1)&15;return 0;
  }
 }
 return -1;
}
/* No queue reset/cancel: refuse a mailbox belonging to another client. */
static int command(unsigned cmd, const uint32_t *args, unsigned count,
                   unsigned indirect, uint32_t *response, unsigned *length) {
 if(cmd!=9)value("PR_SDM_COMMAND=",cmd);
 unsigned in=R(MBOX)&31;
 if(in!=(R(MBOX+0x20)&31)||(R(MBOX+4)&15)!=(R(MBOX+0x24)&15))return -2;
 R(MBOX+0x40+4*in)=0x1e000000U|(count<<12)|(indirect<<11)|cmd;
 in=(in+1)&31;
 for(unsigned i=0;i<count;i++){R(MBOX+0x40+4*in)=args[i];in=(in+1)&31;}
 barrier();R(MBOX)=in;barrier();R(MBOX+0x400)=1;
 /* Peek before consuming to preserve a response for a different transaction. */
 unsigned n;
 for(n=0;n<POLLS;n++)if((R(MBOX+4)&15)!=(R(MBOX+0x24)&15))break;
 if(n==POLLS)return -3;
 uint32_t header=R(MBOX+0xc0+4*(R(MBOX+4)&15));
 if((header>>24)!=0x1e)return -4;
 if(response_word(&header))return -5;
 unsigned words=(header>>12)&0x7ff,capacity=*length;
 for(unsigned i=0;i<words;i++) {
  uint32_t v;if(response_word(&v))return -5;
  if(i<capacity)response[i]=v;
 }
 R(MBOX+0x480)=0;*length=words;
 if(header&0x7ff){value("PR_SDM_RESPONSE_ERROR=",header);return -6;}
 return words>capacity?-7:0;
}
static uint32_t crc32(const struct pr_image *image) {
 const volatile uint8_t *p=(const volatile uint8_t *)(uintptr_t)image->address;
 uint32_t crc=~0U;
 for(unsigned i=0;i<image->bytes;i++) {
  crc^=p[i];for(unsigned b=0;b<8;b++)crc=(crc>>1)^(0xedb88320U&-(crc&1));
 }
 return ~crc;
}
int pr_sdm_load(const struct pr_image *image) {
 /* The source slots are in DDR; the SDM reads a preserved OCRAM bounce area.
  * Fail before RECONFIG if the boot environment has enabled caching/MMU.
  */
 if(SYS(CurrentEL)!=12 || (SYS(sctlr_el3)&5))return -10;
 if((image->address!=0x88000000U && image->address!=0x88100000U) ||
    !image->bytes || image->bytes>OCRAM_CAPACITY || (image->bytes&3))return -11;
 if(crc32(image)!=image->crc32)return -12;
 text("PASS PR_SDM_BUFFER_CRC32\n");
 /* Accept only this lab's Quartus PR container, including its MAIN section.
  * Submit the complete compatible RBF, including its transport envelope.
  */
 const volatile uint32_t *words=(const volatile uint32_t *)(uintptr_t)image->address;
 if(image->bytes<64 || words[0]!=0x97566593U || words[2]!=image->bytes ||
    words[3]!=0x5250U || words[9]!=0x4e49414dU)return -21;
 uint32_t response[6];unsigned len=6;
 int rc=command(0x10,0,0,0,response,&len);
 if(rc || len!=1 || (response[0]&0x0fffffff)!=0x0364f0dd)return -13;
 /* BL2 has handed execution to DDR; its OCRAM workspace is now scratch.
  * Preserve the handoff area at 0x7f000 and save the overwritten bytes in DDR.
  * SDM's direct low-address window can access OCRAM without a DDR remapper.
  */
 volatile uint32_t *bounce=(volatile uint32_t *)OCRAM_BASE;
 volatile uint32_t *saved=(volatile uint32_t *)OCRAM_BACKUP;
 for(unsigned i=0;i<image->bytes/4;i++){saved[i]=bounce[i];bounce[i]=words[i];}
 barrier();
 struct pr_image bounced={OCRAM_BASE,image->bytes,image->crc32};
 if(crc32(&bounced)!=image->crc32)return -24;
 text("PASS PR_SDM_OCRAM_READBACK\n");
 /* Agilex 5 TF-A invokes FPGA_CONFIG_COMP before each configuration start. */
 len=0;rc=command(0x45,0,0,0,response,&len);
 if(rc)return -22;
 len=6;rc=command(6,0,0,0,response,&len);
 if(rc || len!=2 || !response[0] || !response[1] || (response[1]&3))return -14;
 uint32_t block=response[1];value("PR_SDM_CREDITS=",response[0]);value("PR_SDM_BLOCK_BYTES=",block);
 unsigned offset=0,blocks=0;
 while(offset<image->bytes) {
  uint32_t bytes=image->bytes-offset;if(bytes>block)bytes=block;
  uint32_t args[3]={1U<<8,OCRAM_BASE+offset,bytes};
  value("PR_SDM_DMA_ADDRESS=",args[1]);value("PR_SDM_DMA_BYTES=",args[2]);
  len=0;rc=command(8,args,3,1,response,&len);
  if(rc) {
   /* Read-only detail distinguishes bitstream rejection from a DMA timeout. */
   unsigned detail_len=6;
   if(!command(9,0,0,0,response,&detail_len))
    for(unsigned i=0;i<detail_len;i++)value("PR_SDM_FAILURE_DETAIL=",response[i]);
   return -15; /* Leave the DMA buffer intact on uncertain DMA completion. */
  }
  offset+=bytes;blocks++;
 }
 value("PR_SDM_ACKNOWLEDGED_BLOCKS=",blocks);
 for(unsigned attempt=0;attempt<1000;attempt++) {
  len=6;rc=command(9,0,0,0,response,&len);
  if(rc || len<4)return -16;
  if(response[0]!=0 && response[0]!=0x10000000U){value("PR_SDM_STATE=",response[0]);return -17;}
  if(!(response[2]&0x80000000U)||(response[3]&8))return -18;
  if(response[0]==0 && (response[3]&3)==3) {
   for(unsigned i=0;i<image->bytes/4;i++)bounce[i]=saved[i];
   barrier();
   for(unsigned i=0;i<image->bytes/4;i++)if(bounce[i]!=saved[i])return -25;
   text("PASS PR_SDM_OCRAM_RESTORED\n");
   text("PASS PR_SDM_RECONFIG_COMPLETE\n");return 0;
  }
 }
 return -19;
}
