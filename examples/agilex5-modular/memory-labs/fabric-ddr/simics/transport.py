"""Transaction-stepped Verilator CSR/AXI protocol; no memory/translation model here."""
import json
import os
from pathlib import Path
import select
import subprocess
import time

class Backend:
    def __init__(self,executable,trace,memory,timeout=3,injection='none'):
        self.process=None;self.trace=Path(trace).open('w');self.memory=memory
        self.timeout=timeout;self.buffer=b'';self.cycles=0;self.csrs=0;self.reads=0;self.writes=0;self.faults=0
        try:
            self.process=subprocess.Popen([str(executable)]+(['--aw-stall'] if injection=='aw-stall' else []),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.trace)
            os.set_blocking(self.process.stdout.fileno(),False)
            if self.line()!='READY DDR2':raise RuntimeError('Bad RTL protocol handshake')
        except BaseException:self.abort();raise
    def abort(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=.5)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=.5)
            for p in (self.process.stdin,self.process.stdout):
                if p:
                    try:p.close()
                    except OSError:pass
        if not self.trace.closed:self.trace.close()
    def send(self,line):
        self.process.stdin.write((line+'\n').encode('ascii'));self.process.stdin.flush()
    def line(self):
        deadline=time.monotonic()+self.timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise RuntimeError('RTL protocol response timeout')
            if not select.select([self.process.stdout],[],[],remaining)[0]:continue
            chunk=os.read(self.process.stdout.fileno(),256)
            if not chunk:raise RuntimeError('RTL protocol EOF')
            self.buffer+=chunk
            if len(self.buffer)>1024:raise RuntimeError('RTL protocol line exceeds bound')
        line,self.buffer=self.buffer.split(b'\n',1)
        return line.decode('ascii')
    def log(self,item):self.trace.write(json.dumps(item,sort_keys=True)+'\n');self.trace.flush()
    def access(self,offset,write,value,initiator):
        try:
            if offset%4 or not 0<=offset<256 or not 0<=value<=0xffffffff:raise ValueError('Invalid CSR access')
            self.send(f'W {offset:x} {value:x}' if write else f'R {offset:x}')
            for _ in range(8):
                fields=self.line().split()
                if fields and fields[0] in ('MEM_R','MEM_W'):
                    op=fields[0];expected=5 if op=='MEM_W' else 4
                    if len(fields)!=expected:raise RuntimeError('Invalid RTL memory request shape')
                    address=int(fields[1],16);data=int(fields[2],16) if op=='MEM_W' else 0
                    prot,user=map(lambda v:int(v,16),fields[-2:])
                    if prot not in (0,2) or user!=0:raise RuntimeError('Unsupported actual AXI sideband attributes')
                    if address%8 or not 0x85000000<=address<0x85010000 or not 0<=data<=0xffffffffffffffff:raise RuntimeError('RTL memory address/data outside owned bus range')
                    response,result=self.memory(op=='MEM_W',address,data,prot,user)
                    if response not in (0,2,3) or not 0<=result<=0xffffffffffffffff:raise RuntimeError('Invalid native memory response')
                    self.writes+=op=='MEM_W';self.reads+=op=='MEM_R';self.faults+=response!=0
                    self.log({'kind':'axi','op':op,'address':address,'data':data if op=='MEM_W' else result,'response':response,'axprot':prot,'axuser':user})
                    self.send(f'MW {response:x}' if op=='MEM_W' else f'MR {response:x} {result:x}')
                    continue
                if len(fields)!=3 or fields[0]!='OK':raise RuntimeError('Invalid CSR response')
                result,cycles=int(fields[1],16),int(fields[2],16)
                if not 0<=result<=0xffffffff or cycles!=self.cycles+2+(3 if self.csrs==0 else 0):raise RuntimeError('Invalid RTL cycle/value progression')
                self.cycles=cycles;self.csrs+=1
                self.log({'kind':'csr','initiator':initiator,'write':write,'offset':offset,'value':value if write else result,'rtl_cycles':cycles})
                return result
            raise RuntimeError('Too many AXI requests within one CSR transaction')
        except BaseException:self.abort();raise
    def close(self):
        try:
            self.send('Q')
            if self.line()!='BYE':raise RuntimeError('Bad RTL shutdown')
            if self.process.wait(timeout=self.timeout)!=0:raise RuntimeError('RTL backend failed')
        finally:self.abort()
        result={'csrs':self.csrs,'axi_reads':self.reads,'axi_writes':self.writes,'axi_faults':self.faults,'rtl_cycles':self.cycles}
        print('FABRIC_DDR_BACKEND_SUMMARY '+json.dumps(result,sort_keys=True))
        return result
