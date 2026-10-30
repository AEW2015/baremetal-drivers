#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
compiler_prefix=${CROSS_COMPILE:-aarch64-none-elf-}
target=${1:-qemu}
[[ $target == qemu || $target == agilex5 ]] || { echo 'Target must be qemu or agilex5'; exit 2; }
out=build/qemu-labs
linker=qemu/labs/link.ld
flags=()
if [[ $target == agilex5 ]]; then
 out=build/practice-agilex5
 mkdir -p "$out"
 python3 - "$out/link.ld" <<'PY'
import pathlib,sys
s=pathlib.Path('qemu/labs/link.ld').read_text()
for old,new in [('0x40200000','0x82400000'),('0x40300000','0x82500000'),('0x40400000','0x82600000'),('0x40500000','0x82700000'),('0x41000000','0x83fff000')]:s=s.replace(old,new)
pathlib.Path(sys.argv[1]).write_text(s)
PY
 linker=$out/link.ld
 flags=(-DLAB_AGILEX5)
fi
mkdir -p "$out"
build_one() {
 local name=$1 output=$2
 shift 2
 "${compiler_prefix}gcc" -Og -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 \
  -mgeneral-regs-only -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie \
  -nostdlib -static -Wl,--build-id=none,-T,"$linker",-Map,"$out/$output.map" \
  "${flags[@]}" "$@" -o "$out/$output.elf" qemu/labs/start.S qemu/labs/runtime.c "qemu/labs/$name.c"
 "${compiler_prefix}objcopy" -O binary "$out/$output.elf" "$out/$output.bin"
}
for name in startup corruption exception timer mmu uart; do build_one "$name" "$name"; done
build_one multicore multicore -DLAB_MULTICORE
# Negative controls: the host checker must reject each broken exercise.
build_one startup startup-no-bss -DSKIP_BSS_CLEAR
build_one startup startup-no-data -DSKIP_DATA_COPY
build_one corruption corruption-no-injection -DOMIT_CORRUPTION
build_one exception exception-wrong-brk -DWRONG_BRK
build_one timer timer-wrong-ppi -DEXPECT_TIMER_PPI=28
build_one mmu mmu-writable-ro -DWRITABLE_RO
python3 - "$out" "$target" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={'target':sys.argv[2],'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_sha256':{str(p):sha(p) for p in sorted(pathlib.Path('qemu/labs').iterdir()) if p.is_file()},
 'artifacts':{p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ('.bin','.elf')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
