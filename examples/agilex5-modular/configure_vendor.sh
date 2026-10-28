#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
legacy_source=$(python3 legacy_source.py)
cmake -S "$legacy_source" -B build/legacy-vendor -G Ninja -DCMAKE_BUILD_TYPE=Debug "$@"
