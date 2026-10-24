#include "lab_driver.h"
static uint32_t mmio_read(void *context,unsigned offset) {
    uint32_t value=*(volatile uint32_t *)((uintptr_t)context+offset);
    __asm__ volatile("dsb sy":::"memory");return value;
}
static void mmio_write(void *context,unsigned offset,uint32_t value) {
    __asm__ volatile("dsb sy":::"memory");
    *(volatile uint32_t *)((uintptr_t)context+offset)=value;
    __asm__ volatile("dsb sy":::"memory");
}
struct lab_device lab_mmio(uintptr_t base) {
    return (struct lab_device){(void *)base,mmio_read,mmio_write};
}
