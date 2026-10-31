"""Exercise real HAL/mailbox delayed-response lifetimes and real RNG wrapper."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

def c_function(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  if text[end]=='{':depth+=1
  elif text[end]=='}':depth-=1
  end+=1
 return text[start:end]

class FCSResponseLifetime(unittest.TestCase):
 def test_real_hal_queue_delays_timeout_late_reply_and_actual_status(self):
  with tempfile.TemporaryDirectory() as folder:
   env=os.environ.copy();env['FCS_TRANSPORT_TEST_BUILD']=folder
   result=subprocess.run(['bash',str(ROOT/'service-candidates/tests/test_fcs_transport.sh')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   for marker in ['PASS delayed CHIP_ID copied before HAL returns','PASS delayed JTAG_ID copied before HAL returns','PASS timeout then late old reply cannot overwrite/reuse a returned local buffer or satisfy the next request','PASS detached late response leaves owned canary untouched','PASS actual SDM error propagated instead of false zero-status success','PASS UUID RNG failure closes the newly opened remote session and propagates error','FCS_DELAYED_TRANSPORT_COMPLETE']:
    self.assertIn(marker,result.stdout)
 def test_actual_rng_wrapper_rejects_success_without_output_write(self):
  text=(ROOT/'service-candidates/services.c').read_text()
  wrapper=c_function(text,'int __wrap_fcs_api_get_random_number(')
  nontrivial=c_function(text,'static int nontrivial(')
  # Compile the actual wrapper unchanged; substitute only its external API and
  # logging dependencies. A zero-returning no-write API must not qualify stale
  # nonzero caller memory as a fresh RNG result.
  source='''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define FCS_UUID_SIZE 16
static unsigned char session_uuid[16];
static unsigned rng_calls,checks;
static int __real_fcs_api_get_random_number(char *uuid,uint32_t context,char *rng,uint32_t size){(void)uuid;(void)context;(void)rng;(void)size;return 0;}
static void check(int ok,const char *name){(void)name;assert(!ok);checks++;}
static void bytes(const char *name,const char *data,unsigned count){(void)name;assert(count==16);for(unsigned i=0;i<count;i++)assert(data[i]==0);}
'''+nontrivial+'\n'+wrapper+'''
int main(void){char uuid[16]={0},rng[16];memset(rng,0xab,16);assert(__wrap_fcs_api_get_random_number(uuid,0xc0ffee01,rng,16)==0);assert(checks==1&&rng_calls==1);puts("PASS zero-return no-write RNG API rejected");return 0;}
'''
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'wrapper.c').write_text(source)
   built=subprocess.run(['gcc','-O1',str(p/'wrapper.c'),'-o',str(p/'wrapper')],capture_output=True,text=True,timeout=15)
   self.assertEqual(built.returncode,0,built.stderr)
   run=subprocess.run([str(p/'wrapper')],capture_output=True,text=True,timeout=5)
   self.assertEqual(run.returncode,0,run.stdout+run.stderr)
   self.assertIn('PASS zero-return no-write RNG API rejected',run.stdout)

if __name__=='__main__':unittest.main()
