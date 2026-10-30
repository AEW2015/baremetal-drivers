/* Read-only configuration snapshots; UART is the only written peripheral. */
#include "common.h"
#include "socfpga_sys_mngr_reg_plat.h"

struct reg { const char *name; uintptr_t address; };
#if AUDIT_CASE == 0
static const struct reg registers[] = {
    {"SILICONID1", SOCFPGA_SYS_MNGR_BASE_ADDR + SYS_MNGR_SILICONID1},
    {"SILICONID2", SOCFPGA_SYS_MNGR_BASE_ADDR + SYS_MNGR_SILICONID2},
    {"MPU_STATUS", SOCFPGA_SYS_MNGR_BASE_ADDR + SYS_MNGR_MPU_STATUS},
};
#define CASE_NAME "sysmgr"
#else
/* Offsets used by platform/agilex5/platform_setup.c and matching ATF handoff. */
static const struct reg registers[] = {
    {"PIN2SEL", 0x10d13008},
    {"PIN3SEL", 0x10d1300c},
    {"UART0_USEFPGA", 0x10d13338},
};
#define CASE_NAME "pinmux"
#endif

void example_main(void) {
    unsigned failures = 0;
    text("CONFIG_AUDIT_BEGIN " CASE_NAME "\n");
    value("CURRENT_EL=", SYS(CurrentEL) >> 2);
    for (unsigned i = 0; i < sizeof registers / sizeof registers[0]; i++) {
        uint32_t first = R(registers[i].address);
        barrier();
        uint32_t second = R(registers[i].address);
#ifdef AUDIT_INJECT_UNSTABLE
        if (i == 0) second ^= 1;
#endif
        value(registers[i].name, first);
        if (first != second || first == UINT32_MAX) {
            text("FAIL UNSTABLE_OR_UNAVAILABLE ");
            text(registers[i].name);text("\n");
            failures++;
        }
    }
    if (failures) text("CONFIG_AUDIT_COMPLETE status=1\n");
    else text("PASS READ_ONLY_SNAPSHOT registers=3\nCONFIG_AUDIT_COMPLETE status=0\n");
    /* This reports access/read stability, not correctness of every field. The
       host handoff comparator separately checks the observed UART route. */
}
