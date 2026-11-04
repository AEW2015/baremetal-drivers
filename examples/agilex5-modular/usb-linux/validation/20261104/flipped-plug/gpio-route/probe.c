/* Read-only target transactions. GPIO v2 open-drain values: 1 releases line. */
#include <linux/gpio.h>
#define SDA 1
#define SCL 2
static int busfd=-1;
static unsigned state=3, operations;
static void delay_us(unsigned usecs) {
 struct timespec now,start;clock_gettime(CLOCK_MONOTONIC,&start);
 unsigned long long begin=(unsigned long long)start.tv_sec*1000000000+start.tv_nsec;
 do {clock_gettime(CLOCK_MONOTONIC,&now);} while((unsigned long long)now.tv_sec*1000000000+now.tv_nsec-begin < (unsigned long long)usecs*1000);
}
static void fail(const char *message) {
 printf("CC_READ_FAIL %s errno=%d\n",message,errno);
 if(busfd>=0) {struct gpio_v2_line_values v={.mask=3,.bits=3};ioctl(busfd,GPIO_V2_LINE_SET_VALUES_IOCTL,&v);close(busfd);}
 exit(1);
}
static unsigned sample(void) {
 struct gpio_v2_line_values v={.mask=3};
 if(ioctl(busfd,GPIO_V2_LINE_GET_VALUES_IOCTL,&v)<0)fail("get values");
 return v.bits;
}
static void setbits(unsigned mask,unsigned value) {
 struct gpio_v2_line_values v={.mask=3};
 if(++operations>3000)fail("operation bound");
 state=(state&~mask)|(value&mask);v.bits=state;
 if(ioctl(busfd,GPIO_V2_LINE_SET_VALUES_IOCTL,&v)<0)fail("set values");
 delay_us(10);
}
static void high_clock(void) {
 setbits(SCL,SCL);
 for(unsigned i=0;i<100;i++){if(sample()&SCL)return;delay_us(10);}
 fail("clock stretch timeout");
}
static void start_bus(void) {
 setbits(SDA,SDA);high_clock();if(!(sample()&SDA))fail("bus busy");
 setbits(SDA,0);setbits(SCL,0);
}
static void stop_bus(void) {setbits(SDA,0);high_clock();setbits(SDA,SDA);}
static int send_byte(unsigned byte) {
 for(unsigned mask=128;mask;mask>>=1){
  setbits(SDA,(byte&mask)?SDA:0);high_clock();
  if((byte&mask)&&!(sample()&SDA))fail("arbitration lost");
  setbits(SCL,0);
 }
 setbits(SDA,SDA);high_clock();int ack=!(sample()&SDA);setbits(SCL,0);return ack;
}
static unsigned receive_byte(int ack) {
 unsigned byte=0;setbits(SDA,SDA);
 for(unsigned i=0;i<8;i++){high_clock();byte=(byte<<1)|!!(sample()&SDA);setbits(SCL,0);}
 setbits(SDA,ack?0:SDA);high_clock();setbits(SCL,0);setbits(SDA,SDA);return byte;
}
static int read_register(unsigned address,unsigned pointer,unsigned count,unsigned char *data) {
 start_bus();
 if(!send_byte(address<<1)){stop_bus();printf("I2C_NACK address=0x%02x stage=address\n",address);return 0;}
 if(!send_byte(pointer)){stop_bus();printf("I2C_NACK address=0x%02x stage=pointer\n",address);return 0;}
 start_bus();
 if(!send_byte((address<<1)|1)){stop_bus();printf("I2C_NACK address=0x%02x stage=read\n",address);return 0;}
 for(unsigned i=0;i<count;i++)data[i]=receive_byte(i+1<count);
 stop_bus();printf("I2C_READ address=0x%02x pointer=0x%02x bytes=",address,pointer);
 for(unsigned i=0;i<count;i++)printf("%02x ",data[i]);puts("");return 1;
}
int main(int argc,char **argv) {
 int fd=open("/dev/gpiochip0",O_RDONLY);if(fd<0)fail("open chip");
 struct gpiochip_info info={0};if(ioctl(fd,GPIO_GET_CHIPINFO_IOCTL,&info)<0)fail("chip info");
 printf("GPIO_CHIP name=%s label=%s lines=%u\n",info.name,info.label,info.lines);
 if(argc==1){close(fd);return 0;}
 if(strcmp(info.label,"10c03200.gpio") || info.lines!=24)fail("chip identity mismatch");
 struct gpio_v2_line_request req={0};
 req.offsets[0]=8;req.offsets[1]=9;req.num_lines=2;
 strcpy(req.consumer,"usb-cc-read-only");
 req.config.flags=GPIO_V2_LINE_FLAG_OUTPUT|GPIO_V2_LINE_FLAG_OPEN_DRAIN;
 req.config.num_attrs=1;req.config.attrs[0].mask=3;
 req.config.attrs[0].attr.id=GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES;
 req.config.attrs[0].attr.values=3;
 if(ioctl(fd,GPIO_V2_GET_LINE_IOCTL,&req)<0)fail("request lines");
 busfd=req.fd;close(fd);
 for(unsigned i=0;i<8;i++){if(sample()!=3)fail("bus not idle");delay_us(100);}
 unsigned char bytes[11]={0};
 if(!read_register(0x48,0xfe,2,bytes)||bytes[0]!=0x54||bytes[1]!=0x49)fail("TMP464 control identity");
 int got=read_register(0x47,0,11,bytes);
 setbits(3,3);close(busfd);busfd=-1;
 if(!got){puts("CC_CONTROLLER_NOT_REACHED_ON_THIS_ROUTE");return 2;}
 puts("CC_READ_COMPLETE");return 0;
}
