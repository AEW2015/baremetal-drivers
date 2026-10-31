#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
out=$PWD/build/reference-psci
mkdir -p "$out"
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
sdk=$PWD/../..
cat > "$out/link.ld" <<'LINK'
ENTRY(_start)
SECTIONS {
 . = 0x82400000;
 .text : { *(.text.start) *(.text*) *(.rodata*) }
 . = ALIGN(16); .data : { *(.data*) }
 . = ALIGN(16); __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } __bss_end = .;
 ASSERT(. < 0x82700000, "PSCI harness exceeds reserved region")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
LINK
"$prefix"gcc -Os -g3 -Wall -Wextra -Werror -Wno-format -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
 -ffreestanding -fno-builtin -fno-pie -no-pie -nostdlib -mgeneral-regs-only -mstrict-align \
 -I"$sdk/lib" -Wl,-T,"$out/link.ld",-Map,"$out/psci.map",--build-id=none \
 -Wl,--wrap=printf,--wrap=putchar,--wrap=puts \
 reference/psci/start.S reference/psci/psci.c core/secondary_core.c "$sdk/lib/lib_printf.c" -o "$out/psci.elf"
"$prefix"objcopy -O binary "$out/psci.elf" "$out/psci.bin"
python3 - "$out" "$prefix" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[Path('core/secondary_core.c'),Path('../../lib/lib_printf.c')]+[p for p in Path('reference/psci').iterdir() if p.is_file()]
record={'target':'agilex5','scope':'Physical PSCI CPU_ON using unchanged callable helper, one declared A55.1 target from recorded board topology; resident BL31 -> NS EL2 required; CPU_OFF and affinity OFF proof mandatory','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],'entry':'0x82400000','secondary_target_mpidr':'0x100','primary_stack':'0x83fff000','secondary_stack':'0x83ffb000','shared_record':'0x85000000','expected_context':'0x5053434943545854','sources_sha256':{str(p):sha(p) for p in files},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ('.elf','.bin')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS physical PSCI harness compiled; no execution claim')
PY
