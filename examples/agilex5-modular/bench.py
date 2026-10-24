"""Host/container verification shared by the physical-board runners."""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
ROOT = Path(__file__).resolve().parent
HELP = 'https://aew2015.github.io/baremetal-drivers/troubleshooting/'

class BenchError(RuntimeError):
    """A configuration or bench failure with a useful student-facing message."""

def container_path(path):
    base = os.environ.get('AGILEX_CONTAINER_ROOT')
    if not base or not re.fullmatch(r'/[A-Za-z0-9_./-]+', base) or '..' in PurePosixPath(base).parts:
        raise BenchError('Set AGILEX_CONTAINER_ROOT to this example directory inside the container (absolute, no spaces or Tcl metacharacters). See the host/container mapping section of the hardware tutorial.')
    return str(PurePosixPath(base) / Path(path).resolve().relative_to(ROOT))

def container_command(args):
    return ['docker', 'exec', '-u', os.environ.get('AGILEX_CONTAINER_USER', 'dev'),
            os.environ.get('AGILEX_CONTAINER', 'agilex-xrdp'), *args]

def checked_container(args, timeout=30, include_stderr=False):
    try:
        result = subprocess.run(container_command(args), capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise BenchError('Docker CLI is missing. Run hardware automation on the Linux host, with Docker installed; do not run it inside the attached container.') from exc
    except subprocess.TimeoutExpired as exc:
        raise BenchError(f'Container command timed out: {args[0]}. Check the running container and Docker access.') from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1200:]
        raise BenchError(f'Container command failed ({args[0]}): {detail}. Check AGILEX_CONTAINER, AGILEX_CONTAINER_USER, docker ps, and Docker permissions.')
    return result.stdout + (result.stderr if include_stderr else "")

def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()

def validate_uart(port):
    if not port:
        raise BenchError('Set AGILEX_UART or pass --port with the verified host SOM J2 UART device.')
    path = Path(port)
    if not path.exists():
        raise BenchError(f'UART device not found: {port}. Re-identify SOM J2 under /dev/serial/by-path on the host after reconnecting.')
    target = path.resolve()
    if not stat.S_ISCHR(target.stat().st_mode) or not (target.name.startswith('tty') or '/pts/' in str(target)):
        raise BenchError(f'{port} is not a serial TTY device. Select the actual SOM J2 UART, not a regular file or /dev/null.')
    if not os.access(path, os.R_OK | os.W_OK):
        raise BenchError(f'No read/write access to UART {port}. Inspect id and ls -l on the host; use the serial-device group and log in again after a group change.')

def verify_container_tools(tools):
    # No shell interpolation: executable names are passed as ordinary arguments.
    code = 'import shutil,sys; missing=[x for x in sys.argv[1:] if not shutil.which(x)]; print(", ".join(missing)); sys.exit(bool(missing))'
    try:
        checked_container(['python3', '-c', code, *tools])
    except BenchError as exc:
        raise BenchError(f'Required container tools: {", ".join(tools)}. {exc}') from exc

def verify_mount():
    """Prove this checkout is bind-mounted, not merely an identical second clone.

    Writes/removes a temporary workspace nonce; never opens hardware devices.
    """
    container_path(ROOT)
    if shutil.which('docker') is None:
        raise BenchError('Docker CLI is missing. Run hardware automation on the Linux host, not inside the development container.')
    try:
        with tempfile.NamedTemporaryFile(mode='w', prefix='.agilex-mount-', dir=ROOT) as stream:
            nonce = os.urandom(24).hex()
            stream.write(nonce); stream.flush()
            output = checked_container(['python3', '-c', 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())', container_path(stream.name)])
            if output.strip() != nonce:
                raise BenchError('Host/container mount verification returned different content.')
    except BenchError as exc:
        raise BenchError(f'Host/container mapping is not verified. AGILEX_CONTAINER_ROOT must name this same bind-mounted checkout. Inspect docker inspect .Mounts before programming. {exc}') from exc

def verify_mapped_files(paths, expected=None):
    """Verify the exact bytes the container will use, optionally against an earlier hash."""
    paths = [Path(p).resolve() for p in paths]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise BenchError('Missing build artifact(s): ' + ', '.join(missing) + '. Build the selected ELF/DDR images first.')
    host = {container_path(p): digest(p) for p in paths}
    if expected is not None:
        for p in paths:
            if host[container_path(p)] != expected[str(p)]:
                raise BenchError(f'Artifact changed during the run: {p.name}. Stop rebuilding while the board runner is active, then start a fresh run.')
    code = 'import hashlib,json,pathlib,sys; print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in sys.argv[1:]}))'
    try:
        remote = json.loads(checked_container(['python3', '-c', code, *host]))
    except (ValueError, BenchError) as exc:
        raise BenchError(f'Could not verify mapped artifact hashes: {exc}') from exc
    if remote != host:
        raise BenchError('Host and container artifact hashes differ. Correct the bind mount/path before programming.')
    return {str(p): host[container_path(p)] for p in paths}
