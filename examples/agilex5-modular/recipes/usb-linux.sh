#!/usr/bin/env bash
# Run on the BOARD after booting a matching Linux image, not in the host container.
# Basic enumeration checks; no filesystem writes.
lsusb
lsusb -t
dmesg | tail -40
