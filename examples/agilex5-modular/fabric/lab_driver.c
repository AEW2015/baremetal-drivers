#include "lab_driver.h"
int lab_probe(struct lab_device *d, uint32_t *persona) {
    if (d->read(d->context,LAB_ID)!=LAB_MAGIC || d->read(d->context,LAB_ABI)!=LAB_VERSION) return -1;
    *persona=d->read(d->context,LAB_PERSONA);
    return (*persona==LAB_ADD || *persona==LAB_XOR) ? 0 : -2;
}
static int wait_state(struct lab_device *d,uint32_t mask,uint32_t value,unsigned polls) {
    while(polls--) if ((d->read(d->context,LAB_STATUS)&mask)==value) return 0;
    return -3;
}
int lab_execute(struct lab_device *d,uint32_t a,uint32_t b,uint32_t *result,unsigned polls) {
    uint32_t persona;
    if (lab_probe(d,&persona)) return -1;
    if (d->read(d->context,LAB_STATUS)&LAB_QUIESCE) return -2;
    uint32_t sequence=d->read(d->context,LAB_SEQUENCE);
    d->write(d->context,LAB_STATUS,LAB_DONE|LAB_REJECTED);
    d->write(d->context,LAB_A,a);d->write(d->context,LAB_B,b);
    d->write(d->context,LAB_CONTROL,LAB_START);
    if(wait_state(d,LAB_DONE|LAB_REJECTED,LAB_DONE,polls))return -3;
    if(d->read(d->context,LAB_SEQUENCE)!=(uint32_t)(sequence+1))return -4;
    *result=d->read(d->context,LAB_RESULT);
    return 0;
}
int lab_quiesce(struct lab_device *d,unsigned polls) {
    d->write(d->context,LAB_CONTROL,LAB_QUIESCE);
    return wait_state(d,LAB_QUIESCE,LAB_QUIESCE,polls);
}
int lab_resume(struct lab_device *d,unsigned polls) {
    d->write(d->context,LAB_CONTROL,0);
    return wait_state(d,LAB_QUIESCE,0,polls);
}
