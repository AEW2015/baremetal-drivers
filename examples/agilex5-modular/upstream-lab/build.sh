#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
target=${1:-agilex5}
[[ $target == agilex5 || $target == qemu ]] || exit 2
sdk=$PWD/../..
build=$PWD/build/upstream26-ddr
[[ -f $build/api/libbm_api.a ]] || { echo 'First run ./simics/build.sh DDR'; exit 1; }
out=$PWD/build/upstream-lab-$target
mkdir -p "$out"
prefix=${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}
base=0x82400000; stack=0x83fff000; scratch=0x85000000
defs=()
if [[ $target == qemu ]]; then
 base=0x40200000; stack=0x41000000; scratch=0x42000000; defs=(-DLAB_QEMU)
fi
cat > "$out/link.ld" <<EOF
ENTRY(_start)
SECTIONS {
 . = $base;
 .text : { *(.text.start) *(.text*) *(.rodata*)
 . = ALIGN(8); __start_example_register = .;
 KEEP(*(SORT_BY_NAME(.example_register*))) __stop_example_register = .; }
 . = ALIGN(16); .data : { *(.data*) }
 . = ALIGN(16); __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } __bss_end = .;
 ASSERT(. < $base + 0x100000, "Lab image exceeds reserved 1 MiB")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
EOF
includes=(-I"$sdk/include" -I"$sdk/lib" -I"$sdk/examples" -I"$sdk/platform/agilex5/include")
for dir in "$sdk"/api/* "$sdk"/drivers/*; do
 [[ ! -d $dir ]] || includes+=(-I"$dir")
done
sources=(upstream-lab/start.S upstream-lab/lab.c "$sdk/examples/example_register.c")
for module in crc perf combophy noc iossm bridge reset_mngr reboot_mngr mailbox; do
 sources+=("$sdk/examples/$module/"*.c)
done
libs=("$build/api/libbm_api.a" "$build/drivers/libsocfpga_drivers.a" "$build/middleware/libbm_middleware.a" "$build/src/libbm_app.a" "$build/platform/libplatform.a")
names=(crc perf combophy noc iossm bridge reset reboot mailbox smc-guard bridge-control perf-zero-clock)
for case in "${!names[@]}"; do
 [[ $target != qemu || $case -lt 2 || $case -eq 9 || $case -eq 11 ]] || continue
 "${prefix}gcc" -Os -g -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -ffreestanding -fno-builtin -fno-pie -no-pie -nostdlib \
  -mstrict-align -mgeneral-regs-only -DPLAT_AGILEX5 -DBUILD_MODE_DDR \
  -DLAB_BRIDGE_ARGS=\""${LAB_BRIDGE_ARGS:-loopback 16}"\" \
  -DLAB_CASE="$case" -DLAB_STACK="$stack" -DLAB_SCRATCH="$scratch" \
  -DLAB_SCRATCH_TEXT=\""$scratch"\" "${defs[@]}" "${includes[@]}" \
  -Wl,-T,"$out/link.ld",-Map,"$out/${names[$case]}.map",--build-id=none \
  -Wl,--wrap=printf,--wrap=puts,--wrap=putchar,--wrap=cli_register_command \
  "${sources[@]}" -Wl,--start-group "${libs[@]}" -Wl,--end-group \
  -o "$out/${names[$case]}.elf"
 "${prefix}objcopy" -O binary "$out/${names[$case]}.elf" "$out/${names[$case]}.bin"
done
python3 - "$out" "$sdk" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out,sdk=map(pathlib.Path,sys.argv[1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={'source_revision':subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip(),
 'adapter_sha256':{p.name:sha(p) for p in pathlib.Path('upstream-lab').iterdir() if p.is_file()},
 'sdk_build':json.loads(pathlib.Path('build/upstream26-ddr/build.json').read_text()),
 'artifacts':{p.name:sha(p) for p in sorted(out.glob('*')) if p.suffix in ('.bin','.elf')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
