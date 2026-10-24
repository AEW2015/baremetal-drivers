/* SOM MAC/PHY management, SD presence, and USB controller identification.
 * No network packets, SD writes, or USB storage commands.
 */
#include "common.h"
#define MAC 0x10830000U
static int phy_read(unsigned addr,unsigned reg,uint32_t *out){
 if(!wait_bits(MAC+0x204,1<<22,0))return 0;
 R(MAC+0x220)=1U<<addr;R(MAC+0x200)=(addr<<16)|reg;
 R(MAC+0x204)=(1<<22)|(3<<16)|(7<<19); /* slow MDC divider */
 if(!wait_bits(MAC+0x204,1<<22,0))return 0;
 *out=R(MAC+0x204)&65535;return 1;
}
void example_main(void){
 text("HPS SOM INTERFACES BEGIN\n");
 R(0x10d11024)&=~0x9494U;barrier();
 value("EMAC2 MDIO pin selection = ",((uint64_t)R(0x10d13018)<<32)|R(0x10d1301c));
 int found=0;
 for(unsigned addr=0;addr<4;addr++){
  uint32_t id1=0,id2=0;
  if(!phy_read(addr,2,&id1)||!phy_read(addr,3,&id2)){text("FAIL SOM_PHY: MDIO transaction timeout\n");break;}
  value("PHY address = ",addr);value("PHY ID1 = ",id1);value("PHY ID2 = ",id2);
  if(id1==0x141&&(id2&0xfff0)==0xdd0){found=1;break;}
 }
 text(found?"PASS SOM_PHY_ID: EMAC2 MDIO reached Marvell 88E1512\n":"FAIL SOM_PHY_ID\n");
 uint32_t magic=R(0x10808074),present=R(0x10808224);
 value("SDMMC HRS29 = ",magic);value("SD present state = ",present);
 text(magic==0x6061?"PASS SDMMC_IDENT: controller revision matches\n":"FAIL SDMMC_IDENT\n");
 text((present&(1<<16))?"INFO SD_CARD: card-detect reports inserted; media not read\n":"INFO SD_CARD: card-detect does not report inserted\n");
 uint32_t id=R(0x1100c120);value("USB1 GSNPSID = ",id);
 text((id>>16)==0x3331?"PASS USB_IDENT: DWC_usb31 controller ID; enumeration not tested\n":"FAIL USB_IDENT\n");
 text("HPS SOM INTERFACES COMPLETE\n");
}
