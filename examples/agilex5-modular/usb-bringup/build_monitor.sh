#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
atf=${AGILEX_RUNTIME_ATF:-$PWD/.deps/runtime-atf-26.1.1}
pin=2ea5afda7f34774ddcc677fb3a728fa57f780a1e
[[ -d "$atf/.git" ]] || { echo 'Build/fetch the existing pinned runtime checkout with upstream-lab/build_bl31.sh first' >&2; exit 1; }
[[ $(git -C "$atf" rev-parse HEAD) == "$pin" ]] || { echo 'TF-A revision differs from the qualified runtime pin' >&2; exit 1; }
[[ -z $(git -C "$atf" status --porcelain --untracked-files=no) ]] || { echo 'TF-A tracked sources have changes; use the clean runtime checkout' >&2; exit 1; }
# An isolated local checkout protects the shared qualified DDR/runtime sources.
spl_reset=${USB_SPL_RESET_PULSE:-0}
patch_args=()
case "$spl_reset" in
  0) usb_atf="$PWD/.deps/usb-atf-source"; out="$PWD/build/usb-bringup-atf" ;;
  1) usb_atf="$PWD/.deps/usb-atf-source-spl-reset"; out="$PWD/build/usb-bringup-atf-spl-reset"; patch_args+=(--spl-reset-pulse) ;;
  *) echo 'USB_SPL_RESET_PULSE must be 0 or 1' >&2; exit 1 ;;
esac
if [[ ! -d "$usb_atf/.git" ]]; then
  git clone --shared --no-hardlinks "$atf" "$usb_atf"
fi
[[ $(git -C "$usb_atf" rev-parse HEAD) == "$pin" ]] || { echo 'USB TF-A pin mismatch' >&2; exit 1; }
python3 - "$usb_atf" <<'CHECK'
import subprocess,sys
changes=subprocess.check_output(['git','-C',sys.argv[1],'diff','--name-only'],text=True).splitlines()
if any(p!='plat/intel/soc/agilex5/bl31_plat_setup.c' for p in changes):raise SystemExit('Unexpected tracked USB TF-A source changes')
CHECK
python3 usb-bringup/patch_monitor.py "$usb_atf" "${patch_args[@]}"
atf="$usb_atf"
make -C "$atf" BUILD_BASE="$out" bl31 PLAT=agilex5 RESET_TO_BL31=1 \
 PRELOADED_BL33_BASE=0x80200000 DEBUG=1 LOG_LEVEL=40 SPD=none \
 CROSS_COMPILE="${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}" -j4
python3 - "$atf" "$out" "${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}" "$spl_reset" <<'PY'
import hashlib,json,pathlib,subprocess,sys
source=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])/'agilex5/debug';image=out/'bl31.bin'
data={'scope':'Isolated monitor compile only; no hardware execution claimed','atf_commit':'2ea5afda7f34774ddcc677fb3a728fa57f780a1e','reset_to_bl31':True,'usb_platform_init':'Normal vendor BL2 USB3 PIPE power-present BIT14 RMW, restored in isolated RESET_TO_BL31 monitor','patch_sha256':hashlib.sha256(pathlib.Path('usb-bringup/patch_monitor.py').read_bytes()).hexdigest(),'patched_source_sha256':hashlib.sha256((source/'plat/intel/soc/agilex5/bl31_plat_setup.c').read_bytes()).hexdigest(),'bl31_base':'0x80000000','bl33_entry':'0x80200000','nonsecure_entry_el':2,'initial_el3_args':[0,0,0,0],'counter_hz':400000000,'bl31_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'bl31_bytes':image.stat().st_size,'compiler':subprocess.check_output([sys.argv[3]+'gcc','--version'],text=True).splitlines()[0]}
data['spl_reset_pulse_experiment']=sys.argv[4]=='1'
data['usb_misc_set_mask']='0x5000' if data['spl_reset_pulse_experiment'] else '0x4000'
if data['spl_reset_pulse_experiment']:
 data['usb_platform_init']='EXPERIMENT: pinned U-Boot SPL BIT12 reset override + BIT14, bypassed by direct monitor entry; not a universal fix'
 data['compatibility_limit']='TF-A commit e655389 reverted BIT12 after adverse FreeRTOS USB enumeration effects'
 data['compatibility_source']='https://github.com/ARM-software/arm-trusted-firmware/commit/e655389'
(out/'usb-monitor.json').write_text(json.dumps(data,indent=2)+'\n');print('PASS USB_UBOOT_MONITOR_BUILD: BL31=0x80000000 -> NS_EL2 U-Boot=0x80200000; COMPILE ONLY')
PY
