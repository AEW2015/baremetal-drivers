#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
cmake -S ../.. -B build/vendor -G Ninja -DCMAKE_BUILD_TYPE=Debug "$@"
