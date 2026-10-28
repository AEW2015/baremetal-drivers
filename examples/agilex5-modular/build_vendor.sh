#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ ! -f build/legacy-vendor/build.ninja ]]; then ./configure_vendor.sh; fi
cmake --build build/legacy-vendor --target dma_test.elf uart_test.elf timer_test.elf watchdog_test.elf i2c_test.elf i3c_test.elf spi_test.elf sdmmc_test.elf xgmac_test.elf mmu_el3_test.elf smmu_test.elf ccu_test.elf clkmgr_test.elf ecc_test.elf hps_mailbox_test.elf -j4
