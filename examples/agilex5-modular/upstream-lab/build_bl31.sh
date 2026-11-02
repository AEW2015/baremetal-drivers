#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
atf=${AGILEX_RUNTIME_ATF:-$PWD/.deps/runtime-atf-26.3}
pin=$(python3 release_pins.py atf.commit)
if [[ ! -d $atf/.git ]]; then
 git init "$atf"
 git -C "$atf" remote add origin https://github.com/altera-fpga/arm-trusted-firmware.git
 git -C "$atf" fetch --depth=1 origin "$pin"
 git -C "$atf" checkout --detach FETCH_HEAD
fi
[[ $(git -C "$atf" rev-parse HEAD) == "$pin" ]] || { echo 'TF-A revision differs from the qualified runtime pin' >&2; exit 1; }
[[ -z $(git -C "$atf" status --porcelain --untracked-files=no) ]] || { echo 'TF-A has tracked changes; use a clean runtime checkout' >&2; exit 1; }
runtime_out=${AGILEX_RUNTIME_BUILD_DIR:-$PWD/build/runtime-atf-26.3}
bl33_base=${AGILEX_BL33_BASE:-0x82400000}
case "$bl33_base" in 0x82400000|0x80200000) ;; *) echo 'Unsupported lab BL33 entry' >&2; exit 1;; esac
export AGILEX_BL33_BASE="$bl33_base"
make -C "$atf" BUILD_BASE="$runtime_out" bl31 PLAT=agilex5 RESET_TO_BL31=1 \
 PRELOADED_BL33_BASE="$bl33_base" DEBUG=1 LOG_LEVEL=40 SPD=none \
 CROSS_COMPILE="${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}" -j4
python3 - "$atf" "$runtime_out" <<'PY'
import hashlib,json,pathlib,sys,os
root=pathlib.Path(sys.argv[2])/'agilex5/debug';source=pathlib.Path(sys.argv[1])
image=root/'bl31.bin'
(root/'runtime.json').write_text(json.dumps({'atf_commit':json.loads(pathlib.Path('stack-versions.json').read_text())['atf']['commit'],'reset_to_bl31':True,'bl31_base':'0x80000000','bl33_entry':os.environ['AGILEX_BL33_BASE'],'counter_hz':400000000,'counter_source':'plat/intel/soc/agilex5/include/socfpga_plat_def.h','bl31_sha256':hashlib.sha256(image.read_bytes()).hexdigest()},indent=2)+'\n')
PY
