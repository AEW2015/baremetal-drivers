#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
./build_core.sh
./build_dma.sh
./build_gic.sh
./build_vendor.sh

./build_board.sh
