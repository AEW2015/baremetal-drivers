# Host operating systems and execution routes

Use a host listed for your installed tool release. The authoritative
[Altera OS support matrix](https://www.altera.com/developers/software/os-support)
currently lists Quartus Pro 26.3 on Windows 11, Windows Server 2022/2025 and the
Linux versions below. Per-tool support differs; installing Quartus does not
establish that every other tool is native on the same OS.

| Vendor host for Quartus 26.3 | Repository route |
|---|---|
| Windows 11; Windows Server 2022/2025 | Native Quartus GUI/Programmer; learning container or WSL2 for the shell-based labs; Simics in WSL2 |
| Ubuntu 20.04/22.04/24.04 | Native tools on PATH or the Ubuntu learning container |
| RHEL 9.0/9.4/9.6/9.8; RHEL 10.0/10.2 | Native vendor tools or a compatible Linux container engine; the container supplies learning dependencies |
| SUSE SLE 15 SP4/SP5/SP6/SP7 | Native vendor tools or a compatible Linux container engine |

Some older Linux versions are deprecated in 26.3. Confirm the current vendor
matrix before installing; [26.3 OS changes](https://docs.altera.com/r/docs/683706/26.3/quartus-prime-pro-edition-version-26.3-software-and-device-support-release-notes/operating-system-support-changes?contentId=CJH8K8z247FTeZa48kBpCw)
record additions and deprecations. Windows 10 and macOS are not Quartus 26.3
hosts in that matrix. The HTML tutorials work in a browser on other OSes, but
that does not make the FPGA tools supported there.

Use Python 3.10+ for the native lab automation. Older distro Python versions
may need a separate Python installation; the learning container supplies Python
and build dependencies. Clone into a simple Linux path for hardware Tcl tools.
A container mapping at `/work` supports host checkout paths containing spaces
without passing those spaces to Quartus/OpenOCD.

## Windows

Install native Windows Quartus when using its GUI and Programmer. For the full
command-line learning flow, use WSL2 or a Linux-container engine available on
your Windows edition. Windows Server users must enable a supported WSL2 or
container configuration; Docker Desktop availability is a separate product
requirement. The repository does not assume Docker Desktop exists on Server.

Altera explicitly documents [Simics installation in WSL2](https://docs.altera.com/r/docs/784383/26.3/intel-simics-simulator-for-altera-fpgas-user-guide/installing-the-intel-simics-simulator-for-altera-fpgas-on-linux-systems?contentId=8PPQer0Oc8ctGvxRGpHbLg).
Use VS Code Remote WSL for these Linux binaries. Repository attributes keep
shell/build scripts in LF format for Windows checkouts used by WSL/containers. A Windows `.exe` compiler is
not interchangeable with a Linux compiler inside WSL.

In PowerShell, for the learning-container route:

```powershell
git clone https://github.com/AEW2015/baremetal-drivers.git
cd baremetal-drivers
py -3 lab.py image
py -3 lab.py qemu
```

For WSL, clone into its Linux filesystem and use the same repository-relative
commands from the WSL terminal:

```sh
git clone https://github.com/AEW2015/baremetal-drivers.git
cd baremetal-drivers
python3 lab.py --backend native qemu
```

Install the Linux compiler/QEMU dependencies first, following [setup](setup.md).
For an existing Windows checkout, `py -3 lab.py --backend wsl qemu` translates
its path using `wslpath` and delegates to Linux Python; the compiler and emulator
must be installed in that WSL distribution.

The first QEMU build also has a shell-free Python entry point for a native
Windows Arm AArch64 compiler and native QEMU on PATH:

```powershell
py -3 lab.py --backend native qemu
```

Vendor-provided Arm toolchain packages differ by host/release. Select an
AArch64 bare-metal toolchain, rather than the AArch32 `arm-none-eabi` compiler.
Only the first lesson has this shell-free build path; use WSL for the broader
Bash/Make labs.

## Hardware device ownership on Windows

The automated hardware runners use POSIX UART, locking and process ownership.
Run them in Linux, including a deliberately configured WSL2 environment, rather
than invoking their Python files in native PowerShell. Native Windows Quartus
and RiscFree remain available independently; that vendor support is distinct
from this automation's Linux execution backend.

Choose one JTAG owner and one UART owner. To give USB devices to WSL, follow
[Microsoft's USB/WSL instructions](https://learn.microsoft.com/windows/wsl/connect-usb),
identify the actual JTAG and SOM UART devices, and attach those devices. A USB
controller attached to WSL cannot simultaneously be used by a native Windows
debugger. Do not copy Linux `/dev/serial` names into PowerShell or Windows COM
names into the Linux runner. Confirm `jtagconfig` and the SOM UART **inside the
chosen execution environment** before running [hardware onboarding](hardware-inputs.md).

WSL/USB and vendor installations must be configured on the user's machine; the
launcher does not silently change drivers, attach devices or create licenses.
For a native Windows-only hardware session, use the vendor GUI/manual loading
workflow with the matched generated SOF and ELF; the automated pass/restoration
record requires the Linux runner.

## What has actually been tested

Physical execution is recorded on the existing x86-64 Linux Modular ES bench.
Windows CI checks the portable launcher, path mapping and command construction;
it does not have the kit or proprietary vendor software. Container/native Linux
QEMU checks, simulator evidence and hardware evidence are linked separately.
The routes above cover vendor-listed host families; they are not a claim that
we physically tested every OS, WSL/USB setup or native Windows debugger.
