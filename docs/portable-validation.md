# Portable workflow validation

The root launcher was exercised with repository/build paths and without an
external bench checkout. These focused checks supplement the
[all-example 26.3 report](validation-26.3.md); they do not rerun every example
or renew every historical artifact's qualification.

| Route | Observed result |
|---|---|
| Public learning Dockerfile → root launcher → QEMU Hello | PASS |
| QEMU deliberate NEON/final-word corruption and recovery | PASS; failed guests correctly rejected |
| Configured tool container → Simics Hello | PASS |
| Repository DDR builder → merged image under `build/boot/` | PASS |
| Root launcher → hardware Hello → DDR Hello restoration | PASS |
| Root launcher → real ADD–XOR–ADD PR using a relative input manifest | PASS; static-state and DDR guards passed; restoration passed |
| Native/container/WSL launcher path and command tests | 12 local tests passed; CI repeats on Linux and Windows |
| Linux unit suite with real QEMU enabled | 114 tests passed |
| PR artifact/configuration tests | 6 passed |

The hardware runs used the Modular ES board, its SOM UART and the shared mutex.
No flash, SD contents, EEPROM array, clock NVM or fuse was written. The first
optional MCP transport preflight failed before programming because Docker stdin
was closed; the corrected adapter uses `docker exec -i` and has a regression test.
That failed preflight is retained with the successful runs.

Captured hardware output includes:

```text
CANDIDATE_COMMAND hello_selftest
Hello, Baremetal World!
CANDIDATE_COMPLETE status=0
```

The PR guest includes:

```text
PASS XOR_VECTORS
PASS RETURN_ADD_VECTORS
PASS TWO_RUNTIME_SWAPS
PR_LAB_COMPLETE status=0
```

[Evidence, exact ELF/image hashes and restoration logs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/portable-20261102)
retain source/capture provenance. Old absolute paths in recorded logs are not
setup requirements. Current entry points use paths derived from this checkout;
local configuration and generated products are ignored under `build/`.

## Host support versus execution evidence

The [vendor host matrix and repository routes](host-support.md) cover Windows
11/Server and the listed Linux distributions. The
[portable workflow](https://github.com/AEW2015/baremetal-drivers/actions/workflows/portable.yml)
checks launcher behavior on Ubuntu and Windows Server 2022/2025. These CI checks
do not run proprietary tools, attach a kit, validate WSL USB forwarding or
qualify native Windows hardware debugging. Physical evidence remains Linux
execution; Simics uses the vendor's WSL2 route on Windows.

## Movable reference

The [lab-ready release](https://github.com/AEW2015/baremetal-drivers/releases/tag/lab-ready)
identifies the promoted commit, CI runs and remaining limits. The tag may move.
Source commit IDs and captured artifact hashes identify an exact repeat; main
remains editable. Maintainers update this one reference after checks pass,
rather than freezing a branch or creating separate presentation materials.
