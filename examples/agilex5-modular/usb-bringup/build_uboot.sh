#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source_dir=${USB_UBOOT_SOURCE:-$PWD/.deps/usb-uboot-source}
pin=e09d6fcc95f33b8a60377103f6e37e635660a3ee
out="$PWD/build/usb-uboot-source"
if [[ ! -d "$source_dir/.git" ]]; then
  git init "$source_dir"
  git -C "$source_dir" remote add origin https://github.com/altera-fpga/u-boot-socfpga.git
  git -C "$source_dir" fetch --depth=1 origin "$pin"
  git -C "$source_dir" checkout --detach FETCH_HEAD
fi
[[ $(git -C "$source_dir" rev-parse HEAD) == "$pin" ]] || { echo 'Unexpected U-Boot source revision' >&2; exit 1; }
# Only the known command registration and exact diagnostic patches are allowed.
python3 - "$source_dir" "$PWD/usb-bringup/usb_lab_mouse.c" "$PWD/usb-bringup/usb_lab_phy.c" <<'PY'
import pathlib,subprocess,sys
root=pathlib.Path(sys.argv[1]);source=pathlib.Path(sys.argv[2]);line=b'\n# Bare-metal USB lab command (local, reproducible addition).\nobj-y += usb_lab_mouse.o\n'
original=subprocess.check_output(['git','-C',str(root),'show','HEAD:cmd/Makefile'])
legacy_line=line
line+=b'obj-y += usb_lab_phy.o\n'
actual=(root/'cmd/Makefile').read_bytes()
if actual not in [original,original+legacy_line,original+line]:raise SystemExit('Unexpected local cmd/Makefile changes')
changes=subprocess.check_output(['git','-C',str(root),'diff','--name-only'],text=True).splitlines()
if any(x not in ['cmd/Makefile','drivers/usb/host/xhci-dwc3.c','drivers/usb/host/xhci.c'] for x in changes):raise SystemExit('Unexpected tracked U-Boot source changes')
(root/'cmd/Makefile').write_bytes(original+line);(root/'cmd/usb_lab_mouse.c').write_bytes(source.read_bytes())
(root/'cmd/usb_lab_phy.c').write_bytes(pathlib.Path(sys.argv[3]).read_bytes())
PY
python3 usb-bringup/patch_diagnostics.py "$source_dir"
mkdir -p "$out"
prefix=${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}
make -C "$source_dir" O="$out" CROSS_COMPILE="$prefix" socfpga_agilex5_a0_modular_defconfig
config="$source_dir/scripts/config"
"$config" --file "$out/.config" --enable ENV_IS_NOWHERE --disable ENV_IS_IN_FAT --disable ENV_IS_IN_UBI \
 --disable ENV_IS_IN_FLASH --disable ENV_IS_IN_NAND --disable ENV_IS_IN_MMC --disable ENV_IS_IN_SPI_FLASH \
 --disable HANDOFF --disable SPL_HANDOFF --disable BLOBLIST --disable USE_PREBOOT --disable USE_BOOTCOMMAND --set-val BOOTDELAY -1 --set-val CUSTOM_SYS_INIT_SP_ADDR 0x80600000 --disable CMD_SAVEENV --disable CMD_FPGA \
 --enable USB --enable USB_XHCI_HCD --enable USB_XHCI_DWC3 --enable USB_DWC3 --enable CMD_USB \
 --enable USB_STORAGE --enable USB_KEYBOARD --enable USB_HOST_ETHER --enable USB_ETHER_RTL8152 \
 --enable USB_ETHER_ASIX --enable USB_ETHER_ASIX88179 --enable USB_ETHER_LAN75XX --enable USB_ETHER_LAN78XX \
 --enable USB_ETHER_SMSC95XX --enable USB_ETHER_MCS7830
make -C "$source_dir" O="$out" CROSS_COMPILE="$prefix" olddefconfig
python3 - "$out/.config" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();yes={line.split('=')[0] for line in s.splitlines() if line.endswith('=y')}
required=['ENV_IS_NOWHERE','USB_XHCI_HCD','USB_XHCI_DWC3','USB_DWC3','CMD_USB','USB_STORAGE','USB_HOST_ETHER','USB_ETHER_RTL8152','USB_ETHER_ASIX','USB_ETHER_ASIX88179','USB_ETHER_LAN75XX','USB_ETHER_LAN78XX','USB_ETHER_SMSC95XX','USB_ETHER_MCS7830']
for name in required:
 if 'CONFIG_'+name not in yes:raise SystemExit('Missing required config: '+name)
for name in ['HANDOFF','SPL_HANDOFF','BLOBLIST','USE_PREBOOT','USE_BOOTCOMMAND','CMD_SAVEENV','CMD_FPGA']:
 if 'CONFIG_'+name in yes:raise SystemExit('Unsafe lab config remains enabled: '+name)
if 'CONFIG_BOOTDELAY=-1' not in s:raise SystemExit('Autoboot delay not disabled')
if any(name.startswith('CONFIG_ENV_IS_IN_') for name in yes):raise SystemExit('Persistent environment backend remains enabled')
PY
make -C "$source_dir" O="$out" CROSS_COMPILE="$prefix" -j4 u-boot-nodtb.bin u-boot.dtb
python3 - "$source_dir" "$out" "$prefix" <<'PY'
import hashlib,json,pathlib,struct,subprocess,sys
source=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);binary=out/'u-boot-nodtb.bin';dtb=out/'u-boot.dtb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=binary.read_bytes();base,end=struct.unpack_from('<QQ',b,8)
if base!=0x80200000 or end!=len(b):raise SystemExit('Unexpected U-Boot append boundary/load')
patched=out/'u-boot-no-autoboot.dtb';patched.write_bytes(dtb.read_bytes())
subprocess.run(['fdtput','-c',str(patched),'/config'],check=True)
subprocess.run(['fdtput','-t','x',str(patched),'/config','bootdelay','ffffffff'],check=True)
# The bare-metal DDR bootstrap is not U-Boot SPL and supplies no SPL handoff.
# Use the platform's existing FDT fallback over an explicit, bounded DDR window.
for node in subprocess.check_output(['fdtget','-l',str(patched),'/'],text=True).splitlines():
 if node=='memory':continue
 probe=subprocess.run(['fdtget',str(patched),'/'+node,'device_type'],capture_output=True,text=True)
 if probe.returncode==0 and probe.stdout.strip()=='memory':
  subprocess.run(['fdtput','-r',str(patched),'/'+node],check=True)
subprocess.run(['fdtput','-t','x',str(patched),'/memory','reg','0','80000000','0','08000000'],check=True)
# Controlled experiment: keep USB3 PIPE PHY awake during xHCI reset readiness.
subprocess.run(['fdtput',str(patched),'/soc/usb31@11000000','snps,dis_u3_susphy_quirk'],check=True)
subprocess.run(['fdtput','-c',str(patched),'/reserved-memory/tfa@80000000'],check=True)
subprocess.run(['fdtput','-t','x',str(patched),'/reserved-memory/tfa@80000000','reg','0','80000000','0','00100000'],check=True)
subprocess.run(['fdtput',str(patched),'/reserved-memory/tfa@80000000','no-map'],check=True)

combined=out/'u-boot-usb-standalone.bin';combined.write_bytes(b+patched.read_bytes())
if base+combined.stat().st_size>=0x80500000:raise SystemExit('U-Boot image too close to reserved initial stack at0x80600000')
meta={'scope':'Compiled maintained U-Boot host-stack demo; no hardware execution claimed','u_boot_commit':'e09d6fcc95f33b8a60377103f6e37e635660a3ee','defconfig':'socfpga_agilex5_a0_modular_defconfig','compiler':subprocess.check_output([sys.argv[3]+'gcc','--version'],text=True).splitlines()[0],'entry':'0x80200000','initial_stack':'0x80600000','appended_fdt_address':hex(base+end),'command_sha256':sha(source/'cmd/usb_lab_mouse.c'),'phy_command_sha256':sha(source/'cmd/usb_lab_phy.c'),'phy_command_scope':'Bounded USB3320 ULPI ID0..3 reads; no PHY configuration writes or enumeration proof','diagnostics_patch_sha256':sha(pathlib.Path('usb-bringup/patch_diagnostics.py')),'diagnostics':'Stage/register prints retained; DT-gated USB3 SUSPHY-clear experiment added', 'usb3_quirk_experiment':'snps,dis_u3_susphy_quirk on derived USB31 node only; HCRST/CNR checks retained','misc_init_r_a0_sdm_workaround':'retained unchanged','config_sha256':sha(out/'.config'),'dram_init_mode':'preinitialized HPS DDR; platform FDT fallback with CONFIG_HANDOFF disabled','memory_base':'0x80000000','memory_bytes':134217728,'spl_handoff':False,'bloblist':False,'persistent_environment_backend':False,'saveenv_command':False,'preboot':False,'autoboot':False,'usb_nic_classes':['ASIX','ASIX88179','RTL8152/RTL8153','LAN75XX','LAN78XX','SMSC95XX','MCS7830'],'usb_mouse_scope':'HID boot-protocol mouse, bounded interrupt reports; no generic HID report-descriptor parser','artifacts':{p.name:sha(p) for p in [binary,dtb,patched,combined,out/'u-boot']}}
(out/'usb-uboot-build.json').write_text(json.dumps(meta,indent=2)+'\n');print('PASS USB_UBOOT_SOURCE_BUILD: class drivers and bounded mouse command; compile only')
PY
