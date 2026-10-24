/* Read-only SDM GET_IDCODE request. Uses current ring pointers, not Simics offsets. */
#include "common.h"
#define B 0x10a30000U
static int read_response_word(uint32_t *word){
 unsigned n=2000000;
 while((R(B+4)&15)==(R(B+0x24)&15)&&--n){}
 if(!n)return 0;
 unsigned pos=R(B+4)&15;*word=R(B+0xc0+pos*4);barrier();R(B+4)=(pos+1)&15;return 1;
}
void example_main(void){
 text("HPS MAILBOX EXAMPLE BEGIN\n");
 unsigned cin=R(B)&31,cout=R(B+0x20)&31;
 if(cin!=cout||(R(B+4)&15)!=(R(B+0x24)&15)){
  text("FAIL MAILBOX: rings not idle; pending messages left intact\n");return;
 }
 R(B+0x40+cin*4)=0x1e000010;barrier();R(B)=(cin+1)&31;barrier();R(B+0x400)=1;
 uint32_t header=0,id=0;
 if(!read_response_word(&header)){text("FAIL MAILBOX: no response\n");return;}
 value("SDM response header = ",header);
 unsigned len=(header>>12)&0x7ff;
 if((header>>24)!=0x1e||(header&0x7ff)!=0||len!=1){text("FAIL MAILBOX: unexpected response header\n");return;}
 if(!read_response_word(&id)){text("FAIL MAILBOX: incomplete response\n");return;}
 value("SDM device IDCODE = ",id);R(B+0x480)=0;
 text((id&0x0fffffff)==0x0364f0dd?"PASS MAILBOX_IDCODE: SDM returned matching Agilex 5 device ID\n":"FAIL MAILBOX_IDCODE\n");
}
