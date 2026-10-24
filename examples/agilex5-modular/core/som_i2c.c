/* SOM management bus: legacy I2C via GPIO open drain on HPS IOA9/10.
 * Schematic sheets 7/12/45/47: TMP464 at 0x48, 24AA64 at 0x57.
 * Only register-pointer writes followed by reads; no EEPROM data writes.
 * Do not call this native I3C transfer validation.
 */
#include "common.h"
#define SDA (1U<<8)
#define SCL (1U<<9)
#define DR R(0x10c03200)
#define DDR R(0x10c03204)
#define INPUT R(0x10c03250)
static void pause_bus(void){for(volatile unsigned i=0;i<1500;i++){} }
static void low(uint32_t bits){DR&=~bits;DDR|=bits;pause_bus();}
static int release(uint32_t bits){DDR&=~bits;pause_bus();return wait_bits(0x10c03250,bits,bits);}
static int start(void){if(!release(SDA))return 0;if(!release(SCL))return 0;low(SDA);low(SCL);return 1;}
static void stop(void){low(SDA);if(release(SCL))release(SDA);}
static int write_byte(uint8_t byte){
 for(unsigned i=0;i<8;i++){
  if(byte&128){if(!release(SDA))return 0;}else low(SDA);
  if(!release(SCL)){return 0;}
 low(SCL);byte<<=1;
 }
 DDR&=~SDA;pause_bus();if(!release(SCL))return 0;
 int ack=!(INPUT&SDA);low(SCL);return ack;
}
static int read_byte(uint8_t *out,int ack){
 uint8_t value8=0;DDR&=~SDA;
 for(unsigned i=0;i<8;i++){if(!release(SCL))return 0;value8=(value8<<1)|!!(INPUT&SDA);low(SCL);}
 if(ack)low(SDA);else {DDR&=~SDA;pause_bus();}
 if(!release(SCL)){return 0;}
 low(SCL);DDR&=~SDA;*out=value8;return 1;
}
static unsigned nack_stage;
static int read_register(uint8_t addr,uint16_t pointer,unsigned ptrlen,uint8_t *out,unsigned len){
 nack_stage=1;int ok=start()&&write_byte(addr<<1);
 if(!ok)goto done_read;
 nack_stage=2;
 if(ok&&ptrlen==2)ok=write_byte(pointer>>8);
 if(!ok)goto done_read;
 nack_stage=3;if(ok)ok=write_byte(pointer);
 if(!ok)goto done_read;
 nack_stage=4;if(ok)ok=start()&&write_byte((addr<<1)|1);
 for(unsigned i=0;ok&&i<len;i++)ok=read_byte(&out[i],i+1<len);
done_read:
 stop();if(ok)nack_stage=0;return ok;
}
void example_main(void){
 text("HPS SOM I2C EXAMPLE BEGIN\n");
 uint32_t saved8=R(0x10d13020),saved9=R(0x10d13024),dr=DR,ddr=DDR;
 value("Original SDA/SCL pin selection = ",((uint64_t)saved8<<32)|saved9);
 R(0x10d13020)=8;R(0x10d13024)=8;DDR&=~(SDA|SCL);barrier();
 uint8_t bytes[16]={0};
 if(!release(SDA|SCL)){text("FAIL SOM_I2C: bus not idle; no transfer attempted\n");goto done;}
 int ok=read_register(0x48,0xfe,1,bytes,2);
 uint32_t id=((uint32_t)bytes[0]<<8)|bytes[1];value("TMP464 manufacturer = ",id);
 text(ok&&id==0x5449?"PASS SOM_TEMP_ID: TMP464 manufacturer read\n":"FAIL SOM_TEMP_ID\n");
 if(ok&&read_register(0x48,0x00,1,bytes,2))value("TMP464 local temperature raw = ",((uint32_t)bytes[0]<<8)|bytes[1]);
 ok=read_register(0x57,0,2,bytes,16);
 text(ok?"PASS SOM_EEPROM_READ: 16 bytes received; no data written\n":"FAIL SOM_EEPROM_READ\n");
 if(ok){for(unsigned i=0;i<16;i++)value("EEPROM byte = ",bytes[i]);}
 else {
  value("EEPROM failure stage (1 address, 2 high pointer, 3 low pointer, 4 read) = ",nack_stage);
  for(unsigned addr=0x50;addr<=0x57;addr++){
   int ack=start()&&write_byte((addr<<1)|1);
   uint8_t unused=0;if(ack)ack=read_byte(&unused,0);stop();
   if(ack)value("Read-address ACK in EEPROM range = ",addr);
  }
 }
done:
 DDR&=~(SDA|SCL);DR=dr;DDR=ddr;R(0x10d13020)=saved8;R(0x10d13024)=saved9;barrier();
 text("HPS SOM I2C EXAMPLE COMPLETE\n");
}
