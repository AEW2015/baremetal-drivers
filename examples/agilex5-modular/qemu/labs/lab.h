#ifndef QEMU_LAB_H
#define QEMU_LAB_H
#include <stdint.h>
#include <stddef.h>

#define SYS(name) ({ uint64_t v; __asm__ volatile("mrs %0," #name : "=r"(v)); v; })
#define MSR(name, value) __asm__ volatile("msr " #name ",%0" :: "r"((uint64_t)(value)) : "memory")
#define MMIO32(address) (*(volatile uint32_t *)(uintptr_t)(address))
static inline void barrier(void) { __asm__ volatile("dsb sy; isb" ::: "memory"); }

struct exception_record { uint64_t kind, esr, elr, far; };
extern volatile struct exception_record last_exception;
typedef void (*exception_handler_t)(unsigned kind);
extern exception_handler_t exception_handler;
void uart_init(void);
void putchar_uart(char c);
int getchar_uart(void);
void text(const char *s);
void hex(uint64_t value);
void value(const char *name, uint64_t v);
void check(int condition, const char *message);
void lab_begin(const char *name);
__attribute__((noreturn)) void lab_done(unsigned status);
__attribute__((noreturn)) void fail(const char *message);
void exception_dispatch(unsigned kind);
int main(void);
#endif
