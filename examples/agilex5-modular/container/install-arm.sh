#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(uname -m) == x86_64 ]] || { echo 'This pinned archive requires an x86-64 Linux build host' >&2; exit 1; }
archive=arm-gnu-toolchain-13.2.rel1-x86_64-aarch64-none-elf.tar.xz
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
curl -fL --retry 3 "https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/$archive" -o "$scratch/$archive"
printf '%s  %s\n' 7fe7b8548258f079d6ce9be9144d2a10bd2bf93b551dafbf20fe7f2e44e014b8 "$scratch/$archive" | sha256sum -c -
tar -xJf "$scratch/$archive" -C /opt
# The pinned bundled GDB needs older host libraries; use Ubuntu multiarch GDB.
ln -sf /usr/bin/gdb-multiarch /opt/arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf/bin/aarch64-none-elf-gdb
ln -sf /usr/bin/gdb-multiarch /opt/arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf/bin/aarch64-none-elf-gdb-py
