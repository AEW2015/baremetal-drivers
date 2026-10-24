"""Host/container path mapping shared by the physical-board runners."""
import os
import re
from pathlib import Path, PurePosixPath
ROOT = Path(__file__).resolve().parent

def container_path(path):
    base = os.environ.get('AGILEX_CONTAINER_ROOT')
    if not base or not re.fullmatch(r'/[A-Za-z0-9_./-]+', base):
        raise RuntimeError('Set AGILEX_CONTAINER_ROOT to the absolute container path of examples/agilex5-modular (no whitespace/Tcl metacharacters)')
    return str(PurePosixPath(base) / Path(path).resolve().relative_to(ROOT))

def container_command(args):
    return ['docker', 'exec', '-u', os.environ.get('AGILEX_CONTAINER_USER', 'dev'),
            os.environ.get('AGILEX_CONTAINER', 'agilex-xrdp'), *args]
