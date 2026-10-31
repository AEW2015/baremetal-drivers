#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
out=${SERVICE_CANDIDATE_BUILD:-$PWD/build/service-candidates}
sdk=$PWD/../..
libdir=${FCS_SDK_BUILD:-$PWD/build/upstream26-ddr}
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
mkdir -p "$out"
cat > "$out/link.ld" <<'LINK'
ENTRY(_start)
SECTIONS {
 . = 0x82400000;
 .text : { *(.text.start) *(.text*) *(.rodata*)
 . = ALIGN(8); __start_example_register = .;
 KEEP(*(SORT_BY_NAME(.example_register*))) __stop_example_register = .; }
 . = ALIGN(16); .data : { *(.data*) }
 . = ALIGN(16); __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } __bss_end = .;
 ASSERT(. < 0x82700000, "Service image exceeds owned region")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
LINK
includes=(-I"$sdk/include" -I"$sdk/lib" -I"$sdk/examples" -I"$sdk/platform/agilex5/include")
for dir in "$sdk"/api/* "$sdk"/drivers/*; do [[ ! -d $dir ]] || includes+=(-I"$dir"); done
libs=("$libdir/api/libbm_api.a" "$libdir/drivers/libsocfpga_drivers.a" "$libdir/middleware/libbm_middleware.a" "$libdir/src/libbm_app.a" "$libdir/platform/libplatform.a")
wrap=(-Wl,--wrap=printf,--wrap=putchar,--wrap=puts,--wrap=cli_register_command)
for op in init deinit get_chip_id get_jtag_idcode open_session close_session get_random_number get_provision_data; do wrap+=(-Wl,--wrap=fcs_api_$op); done
names=(fcs ecc-readonly)
for index in 0 1; do
 sources=(service-candidates/start.S service-candidates/services.c "$sdk/examples/example_register.c")
 [[ $index != 0 ]] || sources+=("$sdk/examples/fcs/fcs_selftest.c")
 "$prefix"gcc -Os -g3 -Wall -Wextra -Wno-format -ffunction-sections -fdata-sections -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
  -ffreestanding -fno-builtin -fno-pie -no-pie -nostdlib -mgeneral-regs-only -mstrict-align \
  -DPLAT_AGILEX5 -DBUILD_MODE_DDR -DLAB_STACK=0x83fff000 -DSERVICE_CASE="$index" -DSERVICE_NAME=\""${names[$index]}"\" \
  "${includes[@]}" "${sources[@]}" "${wrap[@]}" -Wl,--gc-sections,-T,"$out/link.ld",-Map,"$out/${names[$index]}.map",--build-id=none \
  -Wl,--start-group "${libs[@]}" -Wl,--end-group -o "$out/${names[$index]}.elf"
 "$prefix"objcopy -O binary "$out/${names[$index]}.elf" "$out/${names[$index]}.bin"
done
python3 - "$out" "$sdk" "$prefix" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
out,sdk=map(Path,sys.argv[1:3]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
metadata=json.loads(Path(__import__('os').environ.get('FCS_SDK_BUILD','build/upstream26-ddr')).joinpath('build.json').read_text())
wrong=[p for p,h in metadata['source_sha256'].items() if not (sdk/p).is_file() or sha(sdk/p)!=h]
if wrong:raise SystemExit('SDK sources no longer match library manifest: '+str(wrong))
record={'target':'agilex5','scope':'Guarded current FCS CLI or strictly read-only ECC API subset; no provision/key/fuse write or ECC initialization/injection','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'compiler':subprocess.check_output([sys.argv[3]+'gcc','--version'],text=True).splitlines()[0],'profiles':{'fcs':'resident-BL31-NS-EL2','ecc-readonly':'standalone-EL3'},'scratch_ranges':['0x83000000..0x83800000 FCS operation buffers','0x83800000 provisioning-status read buffer','0x83fff000 initial stack'],'source_sha256':{str(p):sha(p) for p in Path('service-candidates').iterdir() if p.is_file()},'sdk_build':metadata,'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ('.elf','.bin')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS service candidate build; execution unqualified')
PY
