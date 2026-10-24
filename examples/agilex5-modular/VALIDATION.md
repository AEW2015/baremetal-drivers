# Hardware validation record

All 15 suite entries passed on the original Modular ES bench, across several targeted runs. The preserved SHA-256 values identify the original tested ELFs. Source/log paths, line endings and trailing whitespace were normalized while exporting this record. The fork was rebuilt separately; the packaged paths and runners have not been rerun on hardware.

| Entry | Original result | Evidence |
|---|---|---|
| core | PASS | [UART](validation/20261023T230642.472989Z/core-uart.txt), [debug](validation/20261023T230642.472989Z/core-debug.log) |
| dma | PASS | [UART](validation/20261023T230642.472989Z/dma-uart.txt), [debug](validation/20261023T230642.472989Z/dma-debug.log) |
| gic | PASS | [UART](validation/20261023T230642.472989Z/gic-uart.txt), [debug](validation/20261023T230642.472989Z/gic-debug.log) |
| interfaces | PASS | [UART](validation/20261023T231719.793441Z/interfaces-uart.txt), [debug](validation/20261023T231719.793441Z/interfaces-debug.log) |
| mailbox | PASS | [UART](validation/20261023T230642.472989Z/mailbox-uart.txt), [debug](validation/20261023T230642.472989Z/mailbox-debug.log) |
| mmu | PASS | [UART](validation/20261023T230642.472989Z/mmu-uart.txt), [debug](validation/20261023T230642.472989Z/mmu-debug.log) |
| multicore | PASS | [UART](validation/20261023T230642.472989Z/multicore-uart.txt), [debug](validation/20261023T230642.472989Z/multicore-debug.log) |
| som | PASS | [UART](validation/20261023T230642.472989Z/som-uart.txt), [debug](validation/20261023T230642.472989Z/som-debug.log) |
| som-i2c | PASS | [UART](validation/20261023T230642.472989Z/som-i2c-uart.txt), [debug](validation/20261023T230642.472989Z/som-i2c-debug.log) |
| som-i3c | PASS | [UART](validation/20261023T230642.472989Z/som-i3c-uart.txt), [debug](validation/20261023T230642.472989Z/som-i3c-debug.log) |
| vendor-ccu | PASS | [UART](validation/20261023T232734.166542Z/vendor-ccu-uart.txt), [debug](validation/20261023T232734.166542Z/vendor-ccu-debug.log) |
| vendor-clkmgr | PASS | [UART](validation/20261023T232734.166542Z/vendor-clkmgr-uart.txt), [debug](validation/20261023T232734.166542Z/vendor-clkmgr-debug.log) |
| vendor-ecc | PASS | [UART](validation/20261023T232734.166542Z/vendor-ecc-uart.txt), [debug](validation/20261023T232734.166542Z/vendor-ecc-debug.log) |
| vendor-smmu | PASS | [UART](validation/20261023T233101.494937Z/vendor-smmu-uart.txt), [debug](validation/20261023T233101.494937Z/vendor-smmu-debug.log) |
| vendor-uart | PASS | [UART](validation/20261023T232734.166542Z/vendor-uart-uart.txt), [debug](validation/20261023T232734.166542Z/vendor-uart-debug.log) |

Original vendor baseline: `1419101568f1a9034630b632634fe9fe71773266`. Toolchain: Arm GNU 13.2.Rel1. Initialization: ATF 26.1.1 with the included post-DDR/pre-storage hook. Quartus 26.1.1, OpenOCD ADIv6/aji_client, JTAG 6 MHz, UART 115200 8N1.

CCU and clock-manager completion includes nonfatal version/default-value warnings, retained in the UART logs. The SMMU wrapper prints and checks the exact SOM revision-2 IIDR; the original sample's revision-1 print remains visible as context. EEPROM offset-zero reads returned 16 bytes of 0xff. SD card detect reported inserted, without reading media.

Every selected run restored DDR Hello successfully. The final restoration tested four 64 MiB DDR patterns, checked payload readback and confirmed PC at 0x82000014. This does not qualify the full 8 GiB bank. A configured-2-GiB versus detected-8-GiB warning remains documented.

This campaign did not test Ethernet packet traffic, USB enumeration, SD media reads/writes, native I3C target protocols, SMMU translation, multicore cache coherency, ECC fault injection/recovery or button input transitions. No populated NAND/eMMC was established. The U-Boot/Linux recipes are unexecuted setup references.

See [structured results and original ELF hashes](validation/results.json), [hardware mapping](HARDWARE.md), and [porting lessons](PORTING.md).

The fork's full source build, OCRAM build and pinned ATF/Quartus image packaging passed separately; see [packaging build record](validation/packaging-build.json). No board programming was performed during this packaging step.

Tutorial follow-up: QEMU EL3/NEON/memory checks, QEMU GDB breakpoints/stepping,
and physical HPS source breakpoints/stepping/finish plus core UART checks passed.
DDR Hello was restored. See [follow-up evidence](validation/tutorial/results.json).
The desktop VS Code UI was not exercised; its supplied configuration mirrors
the checked debugger operations.
