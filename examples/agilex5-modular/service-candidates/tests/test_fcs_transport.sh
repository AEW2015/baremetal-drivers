#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
sdk=$PWD/../..
out=${FCS_TRANSPORT_TEST_BUILD:-$PWD/build/fcs-transport-regression}
mkdir -p "$out"
includes=(-I"$sdk/include" -I"$sdk/lib" -I"$sdk/platform/agilex5/include")
for dir in "$sdk"/api/* "$sdk"/drivers/*; do [[ ! -d $dir ]] || includes+=(-I"$dir"); done
gcc -O1 -g -ffunction-sections -fdata-sections -DPLAT_AGILEX5 -DBUILD_MODE_DDR \
 "${includes[@]}" service-candidates/tests/test_fcs_transport.c "$sdk/api/fcs/fcs_api.c" \
 "$sdk/drivers/fcs/socfpga_fcs.c" "$sdk/drivers/sdm_mailbox/socfpga_mbox_client.c" \
 -Wl,--gc-sections -o "$out/test_fcs_transport"
"$out/test_fcs_transport"
