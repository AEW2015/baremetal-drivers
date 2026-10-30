"""Bounded subprocess transport shared by the Simics adapter and host fault tests."""
import json
import os
from pathlib import Path
import select
import subprocess
import time

class Backend:
    def __init__(self, executable, trace, missing_done=False, timeout=2.0):
        self.trace=Path(trace).open('w');self.missing_done=missing_done
        self.timeout=timeout;self.buffer=b'';self.transactions=0;self.cycles=0
        self.process=None
        try:
            self.process=subprocess.Popen([str(executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.trace)
            os.set_blocking(self.process.stdout.fileno(),False)
            if self.line()!='READY 1':raise RuntimeError('RTL backend protocol handshake failed')
        except BaseException:
            self.abort();raise

    def abort(self):
        """Close/reap the owned child even after malformed replies or timeout."""
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=.5)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=.5)
            for pipe in (self.process.stdin,self.process.stdout):
                if pipe is not None:
                    try:pipe.close()
                    except OSError:pass
        if not self.trace.closed:self.trace.close()

    def line(self):
        deadline=time.monotonic()+self.timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise RuntimeError('RTL backend response timeout')
            if not select.select([self.process.stdout],[],[],remaining)[0]:continue
            chunk=os.read(self.process.stdout.fileno(),128)
            if not chunk:raise RuntimeError('RTL backend exited before response')
            self.buffer+=chunk
            if len(self.buffer)>512:raise RuntimeError('RTL backend response exceeds 512 bytes')
        line,self.buffer=self.buffer.split(b'\n',1)
        return line.decode('ascii')

    def access(self, offset, write, value=0, initiator=None):
        try:return self._access(offset,write,value,initiator)
        except BaseException:
            self.abort();raise

    def _access(self, offset, write, value, initiator):
        if not 0<=offset<64 or offset%4 or not 0<=value<=0xffffffff:
            raise ValueError('Unsupported RTL register offset/value')
        command=('W %x %x\n'%(offset,value)) if write else ('R %x\n'%offset)
        self.process.stdin.write(command.encode('ascii'));self.process.stdin.flush()
        fields=self.line().split()
        if len(fields)!=3 or fields[0]!='OK':raise RuntimeError('RTL backend rejected transaction: '+' '.join(fields))
        result,cycles=int(fields[1],16),int(fields[2],16)
        if not 0<=result<=0xffffffff or cycles!=self.cycles+2+(2 if self.transactions==0 else 0):raise RuntimeError('RTL backend invalid value/cycle sequence')
        self.cycles=cycles;self.transactions+=1
        # Adapter fault injection: RTL still runs, but the guest sees no DONE.
        delivered=result & ~1 if self.missing_done and not write and offset==0x10 else result
        self.trace.write(json.dumps({'index':self.transactions,'initiator':initiator,'op':'write' if write else 'read','offset':offset,'write_value':value if write else None,'rtl_read_value':result if not write else None,'guest_read_value':delivered if not write else None,'rtl_cycles':cycles,'masked_done':self.missing_done and not write and offset==0x10})+'\n');self.trace.flush()
        return delivered

    def close(self):
        try:
            if self.process.poll() is not None:raise RuntimeError('RTL backend exited unexpectedly')
            self.process.stdin.write(b'Q\n');self.process.stdin.flush()
            if self.line()!='BYE':raise RuntimeError('RTL backend invalid shutdown')
            try:code=self.process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:raise RuntimeError('RTL backend shutdown timeout')
            if code:raise RuntimeError('RTL backend nonzero shutdown')
        finally:self.abort()
        summary={'transactions':self.transactions,'rtl_cycles':self.cycles,'missing_done_injection':self.missing_done}
        print('SIMICS_RTL_BACKEND_SUMMARY '+json.dumps(summary,sort_keys=True))
        return summary
