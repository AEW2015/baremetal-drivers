/* Board-specific single-queue XGMAC2 adapter. Register offsets agree with
 * inc/xgmac/xgmac_regs.h and the upstream U-Boot v2025.10 XGMAC register layout.
 * No upstream send/recv stubs or simulation/loopback PHY setup is used. */
#include "platform.h"
#include "lwip/pbuf.h"
#include "lwip/etharp.h"
#include <string.h>
#define MAC 0x10830000u
#define M(off) R(MAC+(off))
#define N 64u
#define OWN (1u<<31)
#define FD (1u<<29)
#define LD (1u<<28)
#define TX ((volatile struct desc*)0x85000000u)
#define RX ((volatile struct desc*)0x85001000u)
#define TB(i) ((uint8_t*)(uintptr_t)(0x85100000u+2048u*(i)))
#define RB(i) ((uint8_t*)(uintptr_t)(0x85200000u+2048u*(i)))
struct desc {uint32_t a,b,c,d;};
static unsigned ti,ri;
uint64_t mac_tx_packets,mac_rx_packets,mac_tx_full,mac_rx_errors;
static int wait_reg(unsigned off,uint32_t mask,uint32_t value){
 uint64_t until=ticks()+COUNTER_HZ/10;
 do {if((M(off)&mask)==value)return 1;}while(ticks()<until);
 return 0;
}
static int phy(unsigned reg,uint16_t*out){
 if(!wait_reg(0x204,1<<22,0))return 0;
 M(0x220)=1;M(0x200)=reg;M(0x204)=(1<<22)|(3<<16)|(7<<19);
 if(!wait_reg(0x204,1<<22,0))return 0;
 *out=M(0x204)&65535;return 1;
}
static uint16_t phy_delay_before;
static int phy_changed;
static int phy_write(unsigned reg,uint16_t value){
 if(!wait_reg(0x204,1<<22,0))return 0;
 M(0x220)=1;M(0x200)=reg;M(0x204)=(1<<22)|(1<<16)|(7<<19)|value;
 return wait_reg(0x204,1<<22,0);
}
void mac_diagnostics(void){
 static const unsigned offsets[]={0,4,8,0x110,0x11c,0x120,0x140,0x1000,0x1100,0x1140,0x3000,0x3004,0x3100,0x3104,0x3108,0x3124,0x312c,0x3160,0x3144,0x314c,0x3164,0x316c,0x800,0x900,0x928};
 for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++){value("MAC offset",offsets[i]);value("MAC value",M(offsets[i]));}
 value("TX descriptor0",TX[0].d);value("RX descriptor0",RX[0].d);
}
static err_t output(struct netif*n,struct pbuf*p){
 (void)n;if(p->tot_len>1514)return ERR_IF;
 if(TX[ti].d&OWN){mac_tx_full++;return ERR_MEM;}
 unsigned len=p->tot_len;
 pbuf_copy_partial(p,TB(ti),len,0);
 if(len<60){memset(TB(ti)+len,0,60-len);len=60;}
 TX[ti].a=(uintptr_t)TB(ti);TX[ti].b=0;TX[ti].c=len;
 barrier();TX[ti].d=OWN|FD|LD|len;barrier();
 ti=(ti+1)%N;M(0x3124)=(uintptr_t)&TX[ti];mac_tx_packets++;return ERR_OK;
}
int mac_init(struct netif*n){
 value("PER0MODRST",R(0x10d11024));value("SYSMGR_EMAC2",R(0x10d1204c));
 value("EMAC2_USEFPGA",R(0x10d13308));
 R(0x10d11024)&=~0x404u;barrier();
 uint16_t id1,id2,status,control,link;
 if(!phy(2,&id1)||!phy(3,&id2)||id1!=0x141||(id2&0xfff0)!=0xdd0)return -1;
 phy(0,&control);phy(1,&status);phy(1,&status);phy(17,&link);
 value("PHY control",control);value("PHY status",status);value("PHY resolved",link);
 if(!(link&(1<<10)))return -2;
 if(((link>>14)&3)!=2 || !(link&(1<<13)))return -3;
 if(!phy_write(22,2)||!phy(21,&phy_delay_before)||!phy_write(22,0))return -6;
 value("PHY RGMII timing before",phy_delay_before);
 /* 88E1512 page 2 register 21: RX delay bit 5, TX delay bit 4.
  * This handoff uses RGMII (not RGMII-ID); do not add PHY clock delays. */
 if(phy_delay_before&0x30){
  if(!phy_write(22,2)||!phy_write(21,phy_delay_before&~0x30u)||!phy_write(22,0)||!phy_write(0,control|0x8000))return -7;
  phy_changed=1;uint64_t deadline=ticks()+10*COUNTER_HZ;
  do {if(phy(17,&link)&&(link&(1<<10))&&((link>>14)&3)==2)break;}while(ticks()<deadline);
  if(!(link&(1<<10)))return -8;
 }
 text("PASS NETWORK_LINK: 1000 Mbps full duplex\n");
 M(0x3000)|=1;
 if(!wait_reg(0x3000,1,0))return -4;
 /* RGMII mode established by matching ATF/handoff before the DDR hook. */
 M(0)=(3u<<29);M(4)=6;M(8)=0;
 uint32_t feature=M(0x120);unsigned tf=(feature>>6)&31,rf=feature&31;
 if(tf>10||rf>10)return -5;
 unsigned tq=(128u<<tf)/256-1,rq=(128u<<rf)/256-1;
 M(0x1100)=(tq<<16)|10;M(0x1118)=16;M(0x1140)=(rq<<16)|32;
 M(0x1030)=0;M(0xa0)=2;M(0xa4)=1<<15;M(0xa8)=0;
 M(0x70)=0;M(0x90)=0;
 M(0x300)=(n->hwaddr[5]<<8)|n->hwaddr[4];
 M(0x304)=(n->hwaddr[3]<<24)|(n->hwaddr[2]<<16)|(n->hwaddr[1]<<8)|n->hwaddr[0];
 M(0x3004)=0x1f1f081e;M(0x3100)=1<<16;
 M(0x3104)=(16<<16)|16;M(0x3108)=(8<<16)|(1536<<4);
 for(unsigned i=0;i<N;i++){
  TX[i]=(struct desc){0,0,0,0};RX[i]=(struct desc){(uintptr_t)RB(i),0,0,OWN};
 }
 barrier();M(0x3110)=M(0x3118)=0;M(0x3114)=(uintptr_t)TX;M(0x311c)=(uintptr_t)RX;
 M(0x3130)=M(0x3134)=N-1;M(0x3138)=0;
 M(0x3104)|=1;M(0x3108)|=1;M(0)|=1;M(4)|=1;
 M(0x312c)=(uintptr_t)&RX[N-1];barrier();
 n->linkoutput=output;n->output=etharp_output;
 return 0;
}
void mac_poll(struct netif*n){
 for(unsigned k=0;k<N;k++){
  uint32_t s=RX[ri].d;if(s&OWN)break;barrier();
  unsigned len=s&0x3fff;
  if((s&(FD|LD))==(FD|LD) && !(s&((1u<<30)|(1<<15))) && len>=14&&len<=1536){
   struct pbuf*p=pbuf_alloc(PBUF_RAW,len,PBUF_POOL);
   if(p){pbuf_take(p,RB(ri),len);mac_rx_packets++;if(n->input(p,n)!=ERR_OK)pbuf_free(p);}else mac_rx_errors++;
  }else mac_rx_errors++;
  RX[ri].a=(uintptr_t)RB(ri);RX[ri].b=RX[ri].c=0;barrier();RX[ri].d=OWN;barrier();
  M(0x312c)=(uintptr_t)&RX[ri];ri=(ri+1)%N;
 }
}
void mac_stop(void){if(phy_changed){phy_write(22,2);phy_write(21,phy_delay_before);phy_write(22,0);uint16_t ctrl;if(phy(0,&ctrl))phy_write(0,ctrl|0x8000);phy_changed=0;}M(0x3104)&=~1u;M(0x3108)&=~1u;M(0)&=~1u;M(4)&=~1u;barrier();}
