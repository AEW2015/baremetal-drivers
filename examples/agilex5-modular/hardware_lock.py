"""One checkout's hardware ownership, including inherited suite bootstrap locks."""
import fcntl
import os
from pathlib import Path
from bench import BenchError, ROOT

class HardwareLock:
    def __init__(self, path=None):
        self.path = Path(path) if path else ROOT / 'hardware.lock'
        self.fd = None

    def __enter__(self):
        inherited = os.environ.get('AGILEX_LOCK_FD')
        try:
            if inherited is not None:
                original = int(inherited)
                owned, target = os.fstat(original), self.path.stat()
                if (owned.st_dev, owned.st_ino) != (target.st_dev, target.st_ino):
                    raise ValueError('inherited descriptor names a different lock file')
                self.fd = os.dup(original)
            else:
                self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o664)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.close()
            raise BenchError('Hardware is busy in this checkout. Stop your own VS Code/OpenOCD/suite session and retry. Do not delete hardware.lock; deleting it does not release the active owner.') from exc
        except (OSError, ValueError) as exc:
            self.close()
            raise BenchError(f'Cannot establish hardware ownership: {exc}. Clear a stale AGILEX_LOCK_FD environment value if you set one manually.') from exc
        records = list(self.path.parent.glob('.agilex-process-*'))
        if records:
            self.close()
            raise BenchError(f'Unresolved hardware process record: {records[0]}. Investigate the exact owned PID before another operation; do not delete the record to bypass this check.')
        return self

    def child_options(self):
        return {'env': dict(os.environ, AGILEX_LOCK_FD=str(self.fd)), 'pass_fds': (self.fd,)}

    def close(self):
        if self.fd is not None:
            # Do not explicitly LOCK_UN: an inherited descriptor shares the
            # parent's open-file description and must not unlock that owner.
            os.close(self.fd)
            self.fd = None

    def __exit__(self, *_):
        self.close()
