#!/usr/bin/env bash
# Run in the Linux compiler environment, from any working directory.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
root=$PWD
out="$root/build/usb-linux"
prefix=${LINUX_CROSS_COMPILE:-aarch64-linux-gnu-}
jobs=${USB_LINUX_JOBS:-4}
linux_source="$root/.deps/usb-linux-source-26.3"
linux_pin=0c0e456cdde08783d0a56ef593af45899f5d11af
archive="$root/.deps/downloads/busybox-1.37.0.tar.bz2"
archive_sha=3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4
mkdir -p "$out" "$root/.deps/downloads"
if [[ ! -d "$linux_source/.git" ]]; then
 git init "$linux_source"
 git -C "$linux_source" remote add origin https://github.com/altera-fpga/linux-socfpga.git
 git -C "$linux_source" fetch --depth=1 origin "$linux_pin"
 git -C "$linux_source" checkout --detach FETCH_HEAD
fi
[[ $(git -C "$linux_source" rev-parse HEAD) == "$linux_pin" ]] || { echo 'Linux source pin mismatch' >&2; exit 1; }
git -C "$linux_source" diff --quiet HEAD -- || { echo 'Linux vendor source has local changes; use a clean pinned checkout' >&2; exit 1; }
if [[ ! -f "$archive" ]]; then
 curl --fail --location --output "$archive.part" https://busybox.net/downloads/busybox-1.37.0.tar.bz2
 mv "$archive.part" "$archive"
fi
printf '%s  %s\n' "$archive_sha" "$archive" | sha256sum --check -
if [[ ! -d "$root/.deps/busybox-1.37.0" ]]; then tar -xjf "$archive" -C "$root/.deps"; fi
make -C "$linux_source" O="$out/kernel" ARCH=arm64 CROSS_COMPILE="$prefix" tinyconfig
KCONFIG_CONFIG="$out/kernel/.config" "$linux_source/scripts/kconfig/merge_config.sh" \
 -m -O "$out/kernel" "$out/kernel/.config" "$root/usb-linux/kernel.config"
make -C "$linux_source" O="$out/kernel" ARCH=arm64 CROSS_COMPILE="$prefix" olddefconfig
make -C "$linux_source" O="$out/kernel" ARCH=arm64 CROSS_COMPILE="$prefix" -j"$jobs" \
 Image intel/socfpga_agilex5_socdk_a0_modular.dtb
make -C "$root/.deps/busybox-1.37.0" O="$out/busybox" CROSS_COMPILE="$prefix" defconfig
# Defconfig's x86 SHA intrinsics are not suitable for this AArch64 target.
sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/; s/CONFIG_TC=y/# CONFIG_TC is not set/; s/CONFIG_SHA1_HWACCEL=y/# CONFIG_SHA1_HWACCEL is not set/; s/CONFIG_SHA256_HWACCEL=y/# CONFIG_SHA256_HWACCEL is not set/' "$out/busybox/.config"
make -C "$root/.deps/busybox-1.37.0" O="$out/busybox" CROSS_COMPILE="$prefix" -j"$jobs" busybox
USB_UBOOT_BUILD_DIR="$out/uboot" UPSTREAM_CROSS_COMPILE="$prefix" bash usb-bringup/build_uboot.sh
# Keep the repository's existing matching 26.3 BL31 service/USB setup.
UPSTREAM_CROSS_COMPILE="$prefix" bash upstream-lab/build_bl31.sh
UPSTREAM_CROSS_COMPILE="$prefix" bash usb-bringup/build_monitor.sh
python3 usb-linux/prepare.py
