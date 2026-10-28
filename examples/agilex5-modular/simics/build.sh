#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mode=${1:-OCRAM}
[[ $mode == OCRAM || $mode == DDR ]] || { echo 'Choose OCRAM or DDR' >&2; exit 1; }
prefix=${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}
if ! printf '#include <stdio.h>\n#include <inttypes.h>\n#ifndef PRIu64\n#error Missing_64bit_format_macros\n#endif\n' | "${prefix}gcc" -ffreestanding -fsyntax-only -x c -; then
 echo 'Current upstream needs matching AArch64 C headers and inttypes macros. On Ubuntu install gcc-aarch64-linux-gnu libc6-dev-arm64-cross, or set UPSTREAM_CROSS_COMPILE to a complete supported toolchain.' >&2
 exit 1
fi
cmake --fresh -S ../.. -B "build/upstream26-${mode,,}" -G Ninja \
 -DCMAKE_TOOLCHAIN_FILE="$PWD/simics/toolchain.cmake" \
 -DPLAT=agilex5 -DBUILD_MODE="$mode" -DDEBUG=1 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "build/upstream26-${mode,,}" -j4
python3 - "$mode" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
mode=sys.argv[1];root=Path('../..').resolve();out=Path('build')/('upstream26-'+mode.lower())
revision=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True)
prefix=__import__('os').environ.get('UPSTREAM_CROSS_COMPILE','aarch64-linux-gnu-')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[]
for directory in ('api','drivers','include','lib','middleware','platform','src','examples'):
    inputs += [p for p in (root/directory).rglob('*') if p.is_file() and p.suffix in ('.c','.h','.S','.s','.ld') and 'agilex5-modular' not in p.parts]
inputs += list(root.glob('*.ld'))+[root/'CMakeLists.txt',root/'examples/CMakeLists.txt']
source_hashes={str(p.relative_to(root)):sha(p) for p in sorted(set(inputs))}
upstream=json.loads((root/'UPSTREAM-REVISION.json').read_text())
(out/'build.json').write_text(json.dumps({'profile':mode,'upstream':upstream,'source_sha256':source_hashes,'source_revision':revision.stdout.strip() if revision.returncode==0 else None,'compiler':subprocess.check_output([prefix+'gcc','--version'],text=True).splitlines()[0],'elf_sha256':sha(out/'baremetal.elf'),'binary_sha256':sha(out/'baremetal.bin')},indent=2)+'\n')
PY
