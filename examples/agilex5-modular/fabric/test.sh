#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
command -v verilator >/dev/null || { echo 'Install verilator, g++ and make in THIS development environment' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for mode in 1 2; do
  verilator --cc --exe --build --assert -Wall --top-module lab_ip -GMODE="$mode" \
    --Mdir "$work/mode$mode" -CFLAGS "-I$PWD -UNDEBUG" \
    "$PWD/rtl/lab_ip.sv" "$PWD/rtl/lab_persona.sv" \
    "$PWD/tests/test_lab.cpp" "$PWD/lab_driver.c" > "$work/build$mode.log" 2>&1 || { cat "$work/build$mode.log"; exit 1; }
  "$work/mode$mode/Vlab_ip"
done
