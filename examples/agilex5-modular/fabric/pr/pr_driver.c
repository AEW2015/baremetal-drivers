#include "pr_driver.h"
int pr_prepare(struct lab_device *d,uint32_t persona,unsigned polls){
 if(persona!=LAB_ADD && persona!=LAB_XOR)return -1;
 if(d->read(d->context,PR_SIGNATURE)!=0x50525331)return -2;
 if(d->read(d->context,PR_CONTROL)&1)return -3;
 if(lab_quiesce(d,polls))return -4;
 d->write(d->context,PR_EXPECTED,persona);d->write(d->context,PR_CONTROL,1);
 while(polls--){uint32_t s=d->read(d->context,PR_CONTROL);if((s&0xf01)==0x201)return 0;}
 return -5;
}
int pr_finish(struct lab_device *d,uint32_t persona,unsigned polls){
 uint32_t state=0;
 while(polls--){state=d->read(d->context,PR_CONTROL);if(state&4)return -6;if(state&2)break;}
 if(!(state&2) || !(state&1))return -7;
 if(d->read(d->context,PR_OBSERVED)!=persona)return -8;
 d->write(d->context,PR_CONTROL,0);
 if(d->read(d->context,PR_CONTROL)&1)return -9;
 uint32_t id=0;
 if(lab_probe(d,&id)||id!=persona){d->write(d->context,PR_CONTROL,1);return -10;}
 if(d->read(d->context,LAB_SEQUENCE)||d->read(d->context,LAB_A)||d->read(d->context,LAB_B)||d->read(d->context,LAB_STATUS)){d->write(d->context,PR_CONTROL,1);return -11;}
 return 0;
}
