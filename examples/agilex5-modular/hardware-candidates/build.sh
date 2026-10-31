#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
sdk=$PWD/../..
out=$PWD/build/hardware-candidates
libdir=$PWD/build/upstream26-ddr
[[ -f $libdir/api/libbm_api.a ]] || { echo 'Build current DDR SDK libraries first'; exit 1; }
mkdir -p "$out"
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
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
 ASSERT(. < 0x82700000, "Candidate image exceeds reserved region")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
LINK
includes=(-I"$sdk/include" -I"$sdk/lib" -I"$sdk/examples" -I"$sdk/platform/agilex5/include")
for dir in "$sdk"/api/* "$sdk"/drivers/*; do [[ ! -d $dir ]] || includes+=(-I"$dir"); done
sources=(hardware-candidates/start.S hardware-candidates/vectors.S hardware-candidates/candidates.c "$sdk/examples/example_register.c")
modules=(hello ccu clk_mngr dma gic mmu smmu spi timer)
libs=("$libdir/api/libbm_api.a" "$libdir/drivers/libsocfpga_drivers.a" "$libdir/middleware/libbm_middleware.a" "$libdir/src/libbm_app.a" "$libdir/platform/libplatform.a")
names=(hello ccu-readonly clkmgr-readonly dma gic mmu smmu spi timer)
for case in "${!names[@]}"; do
 module=${modules[$case]}
 extra=()
 [[ $module != smmu ]] || extra+=("$sdk/api/smmu/smmu_api.c")
 "$prefix"gcc -Os -g3 -ffunction-sections -fdata-sections -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -ffreestanding -fno-builtin -fno-pie -no-pie -nostdlib \
  -mstrict-align -mgeneral-regs-only -DPLAT_AGILEX5 -DBUILD_MODE_DDR \
  -DCANDIDATE_CASE="$case" -DCANDIDATE_NAME=\""${names[$case]}"\" -DLAB_STACK=0x83fff000 \
  "${includes[@]}" -Wl,-T,"$out/link.ld",-Map,"$out/${names[$case]}.map",--build-id=none \
  -Wl,--gc-sections,--wrap=printf,--wrap=puts,--wrap=putchar,--wrap=cli_register_command,--wrap=gic_api_init \
  "${sources[@]}" "$sdk/examples/$module/"*.c "${extra[@]}" -Wl,--start-group "${libs[@]}" -Wl,--end-group -o "$out/${names[$case]}.elf"
 "$prefix"objcopy -O binary "$out/${names[$case]}.elf" "$out/${names[$case]}.bin"
done
python3 - "$out" "$sdk" "$prefix" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out,sdk=map(pathlib.Path,sys.argv[1:3]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
metadata=json.loads(pathlib.Path('build/upstream26-ddr/build.json').read_text())
mismatches=[p for p,h in metadata['source_sha256'].items() if not (sdk/p).is_file() or sha(sdk/p)!=h]
if mismatches:raise SystemExit('Current SDK source no longer matches static libraries: '+str(mismatches))
record={'target':'agilex5','scope':'Isolated safe current-upstream board candidates; detailed oracle/scope required, build success is not execution','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'compiler':subprocess.check_output([sys.argv[3]+'gcc','--version'],text=True).splitlines()[0],'adapter_sha256':{p.name:sha(p) for p in pathlib.Path('hardware-candidates').iterdir() if p.is_file()},'sdk_build':metadata,'artifacts':{p.name:sha(p) for p in sorted(out.glob('*')) if p.suffix in ('.bin','.elf')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS hardware candidate build: nine isolated EL3 images, no board execution')
PY
