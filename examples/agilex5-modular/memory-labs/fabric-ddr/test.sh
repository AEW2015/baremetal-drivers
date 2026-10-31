#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
out="${FABRIC_DDR_BUILD:-../../build/fabric-ddr}"
mkdir -p "$out"
out=$(realpath "$out")
verilator --cc --exe --build --assert -Wall --top-module ddr_probe \
 --Mdir "$out" "-GALLOWED_BASE=64'h10000000" "-GALLOWED_END=64'h10008000" \
 -GMAX_WORDS=4096 -GWATCHDOG_CYCLES=16 \
 -CFLAGS "-I$PWD -UNDEBUG" "$PWD/rtl/ddr_probe.sv" \
 "$PWD/tests/test_probe.cpp" "$PWD/driver.c" > "$out/build.log" 2>&1 || { cat "$out/build.log"; exit 1; }
"$out/Vddr_probe" | tee "$out/results.log"
