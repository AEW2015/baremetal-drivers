#ifndef BOARD_EXAMPLE_COMMON_H
#define BOARD_EXAMPLE_COMMON_H
#include <stdint.h>
#define R(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define R64(a) (*(volatile uint64_t *)(uintptr_t)(a))
#define SYS(name) ({uint64_t v;__asm__ volatile("mrs %0," #name:"=r"(v));v;})
#define MSR(name,value) __asm__ volatile("msr " #name ",%0"::"r"((uint64_t)(value)):"memory")
static inline void barrier(void){__asm__ volatile("dsb sy;isb":::"memory");}
static inline void put(char c){while(!(R(0x10c02014)&32)){}R(0x10c02000)=(uint8_t)c;}
static inline void text(const char*s){while(*s){if(*s=='\n')put('\r');put(*s++);}}
static inline void value(const char*s,uint64_t v){text(s);text("0x");for(int i=60;i>=0;i-=4)put("0123456789abcdef"[(v>>i)&15]);text("\n");}
static inline int wait_bits(uintptr_t addr,uint32_t mask,uint32_t expected){for(unsigned n=0;n<2000000;n++)if((R(addr)&mask)==expected)return 1;return 0;}
#endif
