import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('pr_oracle',ROOT/'oracle.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Evidence(unittest.TestCase):
 def test_requires_real_load_sequence_continuity_and_one_completion(self):
  uart='PR_LAB_BEGIN simulation_loader=1\n'
  for key in ('INITIAL_ADD_ID','INITIAL_ADD_VECTORS','TWO_RUNTIME_SWAPS','XOR_VECTORS','RETURN_ADD_VECTORS'):uart+='PASS '+key+'\n'
  for key in ('SWAP_RESET_AND_ID','STATIC_SCRATCH_CONTINUITY','STATIC_HEARTBEAT_PROGRESS','DDR_GUARD_256_WORDS','ISOLATED_READ_RESPONSE'):uart+=('PASS '+key+'\n')*2
  uart+='PR_LAB_COMPLETE status=0\n'
  ts=[{'op':'write','offset':128,'write_value':v,'initiator':'machine.core[0]'} for v in (2,1)]
  args=(ts,0,{'transactions':2},'SIMICS_RTL_DDR_BOOTSTRAP_COMPLETE')
  self.assertTrue(m.assess('swap',uart,*args))
  for broken in (uart.replace('PASS DDR_GUARD_256_WORDS','ABSENT'),uart+'PR_LAB_COMPLETE status=0',uart+'FAIL injected',uart.replace('PASS RETURN_ADD_VECTORS','ABSENT')):self.assertFalse(m.assess('swap',broken,*args))
  self.assertFalse(m.assess('swap',uart,ts[:1],0,{'transactions':1},args[-1]))
  self.assertFalse(m.assess('swap',uart,ts,124,{'transactions':2},args[-1]))
  bad=[dict(t,initiator='host') for t in ts];self.assertFalse(m.assess('swap',uart,bad,0,{'transactions':2},args[-1]))
if __name__=='__main__':unittest.main()
