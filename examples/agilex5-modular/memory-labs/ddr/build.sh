#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
target=${1:-qemu}
[[ $target == qemu || $target == agilex5 ]] || { echo 'Target must be qemu or agilex5' >&2; exit 2; }
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
out="build/memory-ddr-$target"
mkdir -p "$out"
python3 - "$out/link.ld" "$target" <<'PY'
import pathlib,sys
s=pathlib.Path('qemu/labs/link.ld').read_text()
if sys.argv[2]=='agilex5':
 for old,new in [('0x40200000','0x82400000'),('0x40300000','0x82500000'),('0x40400000','0x82600000'),('0x40500000','0x82700000'),('0x41000000','0x83fff000')]:s=s.replace(old,new)
pathlib.Path(sys.argv[1]).write_text(s)
PY
flags=()
[[ $target == qemu ]] || flags+=(-DLAB_AGILEX5)
variants=(ddr-path ddr-copy-fault ddr-clock-fault)
[[ $target == qemu ]] || variants+=(ddr-calibrated)
# Add the hardware wrapper without touching already qualified normal images.
case ${DDR_CALIBRATED_ONLY:-0} in
 0) ;;
 1) [[ $target == agilex5 ]] || { echo 'DDR_CALIBRATED_ONLY requires agilex5' >&2; exit 2; }; variants=(ddr-calibrated) ;;
 *) echo 'DDR_CALIBRATED_ONLY must be 0 or 1' >&2; exit 2 ;;
esac
for variant in "${variants[@]}"; do
 extras=()
 source=memory-labs/ddr/ddr.c
 [[ $variant != ddr-calibrated ]] || source=memory-labs/ddr/calibrated.c
 [[ $variant != ddr-copy-fault ]] || extras+=(-DINJECT_COPY_FAULT)
 [[ $variant != ddr-clock-fault ]] || extras+=(-DINJECT_CLOCK_FAULT)
 "${prefix}gcc" -O2 -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 -mgeneral-regs-only \
  -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie -nostdlib -static \
  -Wl,--build-id=none,-T,"$out/link.ld",-Map,"$out/$variant.map" \
  -Iqemu/labs "${flags[@]}" "${extras[@]}" qemu/labs/start.S qemu/labs/runtime.c \
  "$source" -o "$out/$variant.elf"
 "${prefix}objcopy" -O binary "$out/$variant.elf" "$out/$variant.bin"
done
python3 - "$out" "$target" <<'PY'
import pathlib,json,hashlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[pathlib.Path(p) for p in ['memory-labs/ddr/ddr.c','memory-labs/ddr/build.sh','qemu/labs/start.S','qemu/labs/runtime.c','qemu/labs/link.ld','qemu/labs/lab.h']]
if sys.argv[2]=='agilex5':sources.append(pathlib.Path('memory-labs/ddr/calibrated.c'))
record={'scope':'Compile only; hardware timing not qualified','target':sys.argv[2],'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':{str(p):sha(p) for p in sources},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ('.bin','.elf')}}
if sys.argv[2]=='agilex5':record['calibration']={'variant':'ddr-calibrated','declared_frequency_hz':400000000,'nominal_interval_ticks':400000000,'host_interval_grade_seconds':[0.9,1.1],'scope':'Compile only; independent host coarse interval required; not fine timing accuracy'}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
