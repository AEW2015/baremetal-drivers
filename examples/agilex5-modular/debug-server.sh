#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
# Run inside the configured container after DDR initialization. Cable 1 must
# be the Modular carrier, as checked by the host bootstrap runner.
jtagconfig --setparam 1 JtagClock 6M
exec openocd -f bootstrap/ocram/agilex5.cfg -c 'hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; bindto 127.0.0.1; gdb port 3337; tcl port 6677; telnet port 4457'
