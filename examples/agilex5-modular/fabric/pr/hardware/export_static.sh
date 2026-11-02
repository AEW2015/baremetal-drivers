#!/usr/bin/env bash
# Export IP-owned timing constraints together with the fitted static partition.
set -Eeuo pipefail
cd "${1:?Pass the compiled platform directory}"
quartus_cdb baseline_a55 -c baseline_a55 --export_partition root_partition \
  --snapshot final --file pr_static-with-sdc.qdb --include_sdc_entity_in_partition
