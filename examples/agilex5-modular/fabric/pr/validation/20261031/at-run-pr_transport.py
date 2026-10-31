"""Bounded PR MMIO transport; reuse process lifecycle from the RTL lesson."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'simics-rtl'))
from transport import Backend as BaseBackend
class Backend(BaseBackend):
 def _access(self,offset,write,value,initiator):
  if offset%4 or not 0<=offset<=0x80 or not 0<=value<=0xffffffff:raise ValueError('Invalid PR MMIO access')
  command=('W %x %x\n'%(offset,value)) if write else ('R %x\n'%offset)
  self.process.stdin.write(command.encode('ascii'));self.process.stdin.flush()
  fields=self.line().split()
  if len(fields)!=3 or fields[0]!='OK':raise RuntimeError('PR backend rejected request: '+' '.join(fields))
  result,cycles=int(fields[1],16),int(fields[2],16)
  if not 0<=result<=0xffffffff or cycles!=self.cycles+2+(2 if not self.transactions else 0):raise RuntimeError('Invalid PR backend value/cycle sequence')
  self.cycles=cycles;self.transactions+=1
  self.trace.write(json.dumps({'index':self.transactions,'initiator':initiator,'op':'write' if write else 'read','offset':offset,'write_value':value if write else None,'guest_read_value':result if not write else None,'rtl_cycles':cycles})+'\n');self.trace.flush()
  return result
