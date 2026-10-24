/* On-chip tests; no external peer or persistent storage writes. */
#include "common.h"
static void timer(void){
 const uintptr_t b=0x10c03000;
 R(0x10d11028)&=~0x40U;barrier();
 R(b+8)=0;R(b)=100000;R(b+8)=3;
 int ok=wait_bits(b+0xa8,1,1);R(b+8)=0;(void)R(b+0xc);
 text(ok?"PASS HPS_TIMER: periodic timer expiry and clear\n":"FAIL HPS_TIMER: no expiry\n");
}
static void watchdog(void){
 const uintptr_t b=0x10d00300;
 R(0x10d11028)|=2;barrier();R(0x10d11028)&=~2U;barrier();
 R(b+4)=0;R(b)=3; /* watchdog 1, IRQ first, shortest period */
 int ok=wait_bits(b+0x10,1,1);
 R(0x10d11028)|=2;barrier(); /* assert peripheral reset before second timeout */
 text(ok?"PASS WATCHDOG_IRQ: watchdog 1 expiry observed, peripheral reset\n":"FAIL WATCHDOG_IRQ: no expiry\n");
}
static void spi(void){
 const uintptr_t b=0x10da4000;
 R(0x10d11024)&=~0x20000U;barrier();
 value("SPI version = ",R(b+0x5c));
 R(b+8)=0;R(b+0x2c)=0;R(b)=(7<<16)|(1<<11); /* 8-bit, SRL loopback */
 R(b+0x14)=256;R(b+0x10)=1;R(b+8)=1;
 const uint8_t bytes[4]={0xa5,0x5a,0x12,0xed};int ok=1;
 for(unsigned i=0;i<4;i++)R(b+0x60)=bytes[i];
 for(unsigned i=0;i<4;i++){
  if(!wait_bits(b+0x28,8,8)){ok=0;break;}
  if((R(b+0x60)&255)!=bytes[i])ok=0;
 }
 R(b+8)=0;R(b+0x10)=0;
 text(ok?"PASS SPI_LOOPBACK: four bytes through internal loopback\n":"FAIL SPI_LOOPBACK\n");
}
static void led(void){
 uint32_t mux=R(0x10d13000),dr=R(0x10c03200),ddr=R(0x10c03204);
 R(0x10d11028)&=~(1U<<24);R(0x10d13000)=8;R(0x10c03204)|=1;barrier();
 int ok=1;
 for(unsigned i=0;i<3;i++){
  R(0x10c03200)|=1;barrier();
  for(volatile unsigned n=0;n<1000000;n++){}
  if(!(R(0x10c03250)&1))ok=0;
  R(0x10c03200)&=~1U;barrier();
  for(volatile unsigned n=0;n<1000000;n++){}
  if(R(0x10c03250)&1)ok=0;
 }
 R(0x10c03200)=dr;R(0x10c03204)=ddr;R(0x10d13000)=mux;barrier();
 text(ok?"PASS GPIO_LED_PAD: SOM heartbeat output high/low readback\n":"FAIL GPIO_LED_PAD\n");
}
static void identities(void){
 R(0x10d11028)&=~0x6300U;barrier();
 uint32_t a=R(0x10c028fc),b=R(0x10c029fc);
 value("I2C0 component type = ",a);value("I2C1 component type = ",b);
 text(a==0x44570140&&b==0x44570140?"PASS I2C_IDENT: two controller IDs; no bus transfer\n":"FAIL I2C_IDENT\n");
 value("I3C0 version = ",R(0x10da00e0));value("I3C1 version = ",R(0x10da10e0));
 value("I3C1 pin 8 selection = ",R(0x10d13020));value("I3C1 pin 9 selection = ",R(0x10d13024));
}
void example_main(void){
 text("HPS SOM PERIPHERALS BEGIN\n");timer();watchdog();spi();led();identities();text("HPS SOM PERIPHERALS COMPLETE\n");
}
