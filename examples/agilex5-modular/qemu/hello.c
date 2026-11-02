/*
 * First lab: observe EL3, add four NEON lanes, and verify a 4096-byte RAM copy.
 * Run: ./qemu/build.sh && python3 qemu/run.py --check
 * Platform: QEMU virt, Cortex-A53, EL3; start.S clears BSS and enables SIMD.
 * PL011 at 0x09000000 is a QEMU address, not an Agilex hardware address.
 * The copy is performed by the CPU; it does not demonstrate a DMA controller.
 */
#include <stdint.h>

#define PL011_DATA_ADDRESS 0x09000000UL
#define PL011_FLAGS_ADDRESS 0x09000018UL
#define PL011_TX_FIFO_FULL (1U << 5)
#define UART_POLL_BUDGET 1000000U
#define MEMORY_WORD_COUNT 512U
#define VECTOR_LANE_COUNT 4U
#define MEMORY_PATTERN 0x1234567800000000ULL
#define SEMIHOSTING_SYS_EXIT_EXTENDED 0x20U
#define SEMIHOSTING_APPLICATION_EXIT 0x20026U

/* Keep these names visible to the debugger's Watch and GDB exercises. */
volatile uint64_t source[MEMORY_WORD_COUNT];
volatile uint64_t destination[MEMORY_WORD_COUNT];
uint32_t vector_a[4] = {1, 2, 3, 4};
uint32_t vector_b[4] = {10, 20, 30, 40};
uint32_t vector_result[VECTOR_LANE_COUNT];
volatile unsigned failures;

extern void qemu_neon_add(const uint32_t *, const uint32_t *, uint32_t *);
__attribute__((noreturn, noinline)) void qemu_done(unsigned status);

static void uart_write_text(const char *text)
{
    volatile uint32_t *flags = (volatile uint32_t *)(uintptr_t)PL011_FLAGS_ADDRESS;
    volatile uint32_t *data = (volatile uint32_t *)(uintptr_t)PL011_DATA_ADDRESS;

    while (*text != '\0') {
        unsigned remaining = UART_POLL_BUDGET;

        while ((*flags & PL011_TX_FIFO_FULL) != 0U) {
            if (--remaining == 0U) {
                /* A stuck UART cannot print its own error; exit nonzero. */
                qemu_done(1);
            }
        }
        *data = (uint8_t)*text++;
    }
}

/* Break here after all checks. Semihosting returns status to the host runner. */
__attribute__((noreturn, noinline)) void qemu_done(unsigned status)
{
    uint64_t reason[2] = {SEMIHOSTING_APPLICATION_EXIT, status};
    register uint64_t operation __asm__("x0") = SEMIHOSTING_SYS_EXIT_EXTENDED;
    register void *arguments __asm__("x1") = reason;

    __asm__ volatile("hlt #0xf000" : : "r"(operation), "r"(arguments) : "memory");
    for (;;) {
        __asm__ volatile("wfi");
    }
}

int main(void)
{
    uint64_t current_el;
    unsigned neon_failures = 0;
    unsigned memory_failures = 0;

    uart_write_text("QEMU VIRT AARCH64 BEGIN\n");
    __asm__ volatile("mrs %0, CurrentEL" : "=r"(current_el));
    if ((current_el >> 2) != 3U) {
        uart_write_text("FAIL EL3\n");
        qemu_done(1);
    }
    uart_write_text("PASS EL3\n");

    /* Compute first, then compare every lane with an independent expectation. */
    qemu_neon_add(vector_a, vector_b, vector_result);
    /* LAB_FAULT_INJECTION: neon */
    for (unsigned i = 0; i < VECTOR_LANE_COUNT; i++) {
        if (vector_result[i] != (i + 1U) * 11U) {
            neon_failures++;
        }
    }
    failures += neon_failures;
    uart_write_text(neon_failures ? "FAIL NEON\n" : "PASS NEON: 11 22 33 44\n");

    /* Separate initialization, transfer and full readback for single-stepping. */
    for (unsigned i = 0; i < MEMORY_WORD_COUNT; i++) {
        source[i] = MEMORY_PATTERN ^ i;
        destination[i] = 0;
    }
    for (unsigned i = 0; i < MEMORY_WORD_COUNT; i++) {
        destination[i] = source[i];
    }
    /* LAB_FAULT_INJECTION: memory */
    for (unsigned i = 0; i < MEMORY_WORD_COUNT; i++) {
        if (destination[i] != source[i]) {
            memory_failures++;
        }
    }
    failures += memory_failures;
    uart_write_text(memory_failures ? "FAIL MEMORY\n" : "PASS MEMORY: 4096-byte CPU copy\n");

    uart_write_text(failures ? "QEMU EXAMPLE FAILED\n" : "QEMU EXAMPLE COMPLETE\n");
    qemu_done(failures ? 1U : 0U);
}
