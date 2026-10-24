#ifndef LAB_DRIVER_H
#define LAB_DRIVER_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { LAB_ID=0x00, LAB_ABI=0x04, LAB_PERSONA=0x08, LAB_CONTROL=0x0c,
       LAB_STATUS=0x10, LAB_A=0x14, LAB_B=0x18, LAB_RESULT=0x1c, LAB_SEQUENCE=0x20 };
enum { LAB_MAGIC=0x4c414231, LAB_VERSION=0x00010000,
       LAB_ADD=0x41444431, LAB_XOR=0x584f5231 };
enum { LAB_START=1, LAB_QUIESCE=2, LAB_DONE=1, LAB_REJECTED=4 };
typedef uint32_t (*lab_read_fn)(void *, unsigned);
typedef void (*lab_write_fn)(void *, unsigned, uint32_t);
struct lab_device { void *context; lab_read_fn read; lab_write_fn write; };
/* Bounds polling iterations, not a stalled physical bus transaction. */
int lab_probe(struct lab_device *, uint32_t *persona);
int lab_execute(struct lab_device *, uint32_t a, uint32_t b, uint32_t *result, unsigned polls);
int lab_quiesce(struct lab_device *, unsigned polls);
int lab_resume(struct lab_device *, unsigned polls);
struct lab_device lab_mmio(uintptr_t base);
#ifdef __cplusplus
}
#endif
#endif
