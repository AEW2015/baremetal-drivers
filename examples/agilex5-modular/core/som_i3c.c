/* Native I3C1 controller in legacy I2C mode, reading SOM TMP464/EEPROM.
 * Timing and queue fields follow Linux drivers/i3c/master/dw-i3c-master.c.
 * IOA9/10 selector 0 = I3C1, verified in Quartus sm/hps/sm_handoff.tcl.
 * No DAA/CCC or EEPROM data writes are issued on the shared management bus.
 */
#include "common.h"
#define B 0x10da1000U
static int response(uint32_t *out){
 unsigned n=2000000;
 while(!((R(B+0x4c)>>8)&255)&&--n){}
 if(!n){value("I3C interrupt status = ",R(B+0x3c));value("I3C present state = ",R(B+0x54));return 0;}
 *out=R(B+0x10);value("I3C response = ",*out);return !(*out>>28);
}
static int read_pointer(uint8_t address,uint16_t pointer,unsigned plen,unsigned len,uint8_t *bytes){
 uint32_t dat=R(B+0x5c)&0xffff;
 R(B+dat)=(1U<<31)|address;
 R(B+0x14)=plen==2?((pointer>>8)|((pointer&255)<<8)):pointer;
 R(B+0xc)=(plen<<16)|1;R(B+0xc)=1U<<26;
 R(B+0xc)=(len<<16)|1;R(B+0xc)=(1U<<30)|(1U<<28)|(1U<<26)|(1U<<3);
 uint32_t a=0,b=0;
 if(!response(&a)||!response(&b))return 0;
 if(((b>>24)&15)!=1||(b&65535)!=len)return 0;
 for(unsigned i=0;i<len;i+=4){uint32_t word=R(B+0x14);for(unsigned j=0;j<4&&i+j<len;j++)bytes[i+j]=word>>(j*8);}
 return 1;
}
void example_main(void){
 text("HPS NATIVE I3C EXAMPLE BEGIN\n");
 value("I3C1 pin selection = ",((uint64_t)R(0x10d13020)<<32)|R(0x10d13024));
 uint32_t saved8=R(0x10d13020),saved9=R(0x10d13024);
 R(0x10d13020)=0;R(0x10d13024)=0;barrier();
 R(0x10d11028)&=~0x4000U;barrier();R(B)=0;
 R(B+0x34)=31;if(!wait_bits(B+0x34,31,0)){text("FAIL NATIVE_I3C: reset timeout\n");return;}
 value("I3C1 version = ",R(B+0xe0));value("I3C1 DAT pointer = ",R(B+0x5c));
 R(B+0x40)=0x3f;R(B+0x44)=0;R(B+0x3c)=~0U;R(B+0x1c)=0;R(B+0x20)=0;
 R(B+0xb4)=(1000<<16)|1000;R(B+0xb8)=(1000<<16)|1000;
 R(B+0xbc)=(1000<<16)|1000;R(B+0xc0)=(1000<<16)|1000;R(B+0xd4)=1000;
 R(B+4)=(1U<<31)|(8<<16);R(B)=(1U<<31)|(1<<7);barrier();
 uint8_t bytes[16]={0};int ok=read_pointer(0x48,0xfe,1,2,bytes);
 uint32_t id=((uint32_t)bytes[0]<<8)|bytes[1];value("TMP464 manufacturer = ",id);
 text(ok&&id==0x5449?"PASS NATIVE_I3C_TEMP: legacy I2C read via I3C1\n":"FAIL NATIVE_I3C_TEMP\n");
 if(!ok){R(B)=0;R(0x10d13020)=saved8;R(0x10d13024)=saved9;return;}
 ok=read_pointer(0x57,0,2,16,bytes);
 text(ok?"PASS NATIVE_I3C_EEPROM: 16-byte read, no data writes\n":"FAIL NATIVE_I3C_EEPROM\n");
 if(ok)for(unsigned i=0;i<16;i++)value("EEPROM byte = ",bytes[i]);
 R(B)=0;R(0x10d13020)=saved8;R(0x10d13024)=saved9;barrier();text("HPS NATIVE I3C EXAMPLE COMPLETE\n");
}
