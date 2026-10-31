#!/usr/bin/env bash
# Board-free check for the public learning image. Builds QEMU targets only.
set -Eeuo pipefail

pack_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$pack_dir"

: "${CROSS_COMPILE:=aarch64-none-elf-}"
export CROSS_COMPILE

for tool in "${CROSS_COMPILE}gcc" "${CROSS_COMPILE}objcopy" qemu-system-aarch64 gdb-multiarch verilator; do
    command -v "$tool" >/dev/null || { echo "Required tool is missing in this environment: $tool" >&2; exit 1; }
done

stamp=$(date -u +%Y%m%dT%H%M%S%NZ)
out="runs/learning-check-$stamp"
mkdir -p "$out"

run_step() {
    local name=$1
    shift
    printf '\n== %s ==\n' "$name"
    printf 'COMMAND:'
    printf ' %q' "$@"
    printf '\n'
    "$@" 2>&1 | tee "$out/$name.log"
}

printf 'Board-free validation output: %s/%s\n' "$pack_dir" "$out"
printf 'Compiler: %s\n' "$CROSS_COMPILE"

# The root hello check plus its mutation/recovery exercise.
run_step qemu-hello-build bash qemu/build.sh
run_step qemu-hello-check python3 qemu/run.py --check
run_step qemu-hello-experiment python3 qemu/experiment.py

# Seven QEMU practice programs, all deliberate negative controls, and batch GDB checks.
run_step qemu-labs-build bash qemu/labs/build.sh qemu
run_step qemu-labs-check python3 qemu/labs/run.py --negative --gdb --output "$out/qemu-labs"

# QEMU-only memory builds. Do not replace these commands with build_all.sh,
# which also builds the Agilex-target artifacts.
run_step dsu-qemu-build bash memory-labs/dsu/build.sh qemu
run_step dsu-qemu-check python3 memory-labs/dsu/run.py --build build/dsu-qemu --output "$out/dsu-qemu"
run_step ddr-qemu-build bash memory-labs/ddr/build.sh qemu
run_step ddr-qemu-check python3 memory-labs/ddr/run.py --artifacts build/memory-ddr-qemu --output "$out/ddr-qemu"
run_step smmu-qemu-build bash memory-labs/smmu/build.sh
run_step smmu-qemu-check python3 memory-labs/smmu/run.py --out "$out/smmu-qemu"

# Host-side RTL tests use Verilator only; they do not configure or access a board.
run_step fabric-test bash fabric/test.sh
run_step fabric-ddr-test bash memory-labs/fabric-ddr/test.sh

printf '\nPASS BOARD_FREE_LEARNING_CHECK\nEvidence: %s/%s\n' "$pack_dir" "$out"
