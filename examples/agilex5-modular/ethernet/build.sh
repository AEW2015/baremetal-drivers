#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
lwip_commit=77dcd25a72509eb83f72b033d219b1d40cd8eb95
if [[ ! -d ethernet/lwip/.git ]]; then git clone --depth 1 --branch STABLE-2_2_1_RELEASE https://github.com/lwip-tcpip/lwip.git ethernet/lwip; fi
[[ $(git -C ethernet/lwip rev-parse HEAD) == "$lwip_commit" ]] || { echo 'lwIP revision mismatch'; exit 1; }
[[ -z $(git -C ethernet/lwip status --porcelain) ]] || { echo 'lwIP checkout has local changes; use the clean pinned dependency'; exit 1; }
mkdir -p build/network
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
"${prefix}gcc" -O2 -g3 -Wall -Wextra -Werror -Wno-unused-parameter -mcpu=cortex-a55 -mgeneral-regs-only -ffreestanding -fno-builtin -fno-pie -no-pie \
 -nostdlib -static -DNET_CACHED=${NET_CACHED:-1} -Iethernet -Iethernet/lwip/src/include -Icore -Wl,--build-id=none,-T,ethernet/link.ld,-Map,build/network.map \
 -o build/network.elf ethernet/start.S core/fault.c ethernet/platform.c ethernet/mac.c ethernet/main.c \
 ethernet/lwip/src/core/*.c ethernet/lwip/src/core/ipv4/*.c ethernet/lwip/src/netif/ethernet.c \
 -Wl,--start-group -lc -lgcc -lnosys -Wl,--end-group
"${prefix}size" build/network.elf

python3 - <<'PYMETA'
from pathlib import Path
import hashlib,json,os,subprocess
root=Path('ethernet')
files=list(root.glob('*.[chS]'))+[root/'link.ld',root/'arch/cc.h',root/'build.sh',Path('core/fault.c')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
Path('build/network.json').write_text(json.dumps({'lwip_commit':'77dcd25a72509eb83f72b033d219b1d40cd8eb95','cpu_cache':int(os.environ.get('NET_CACHED','1')),'dma_memory':'normal noncacheable 0x85000000..0x853fffff','entry':'0x82600000','counter_hz':400000000,'elf_sha256':sha(Path('build/network.elf')),'source_sha256':{str(p):sha(p) for p in files}},indent=2)+'\n')
PYMETA
