"""Runtime/caller preconditions and queued mutex regression checks."""
import contextlib,fcntl,importlib.util,io,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runtime_lab',ROOT/'upstream-lab/run.py')
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

class RuntimeFixes(unittest.TestCase):
    def test_reboot_requires_fresh_boot_after_request(self):
        body='UPSTREAM_LAB_BEGIN case=7\nInititating Warm Reboot\nWelcome to SoCFPGA Baremetal World\n'
        self.assertEqual(lab.assess('reboot',body,0),'pass')
        self.assertEqual(lab.assess('reboot',body.split('Welcome')[0],0),'fail')
        self.assertEqual(lab.assess('reboot',body+'FAIL EXCEPTION',0),'fail')

    def test_runtime_transfer_zeros_arguments_and_enters_bl31(self):
        script=lab.simics_script(Path('/payload.bin'),Path('/boot.bin'),Path('/bl31.bin'),'reboot')
        self.assertIn('write-reg x0 0',script)
        self.assertIn('set-pc 0x80000000',script)
        self.assertIn('SIMICS_WARM_RESET_OBSERVED',script)
        self.assertIn('bp.wait-for-breakpoint $ready',script)

    def test_mailbox_completion_does_not_hide_rejected_command(self):
        body='UPSTREAM_LAB_BEGIN case=8\n[MBOX][FAIL] GET_IDCODE\n[MBOX] done\nUPSTREAM_LAB_COMPLETE status=0'
        self.assertEqual(lab.assess('mailbox',body,0),'fail')

    def test_queued_mutex_cancels_without_accessing_hardware(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);bench=temp/'bench';(bench/'examples').mkdir(parents=True)
            lock=(bench/'examples/hardware.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            (temp/'mcp_client.py').write_text('class MCP:\n def __init__(self,*a): raise RuntimeError("Hardware must not be touched while waiting")\n')
            code='import importlib.util,pathlib; s=importlib.util.spec_from_file_location("hw",'+repr(str(ROOT/'upstream-lab/hardware.py'))+'); m=importlib.util.module_from_spec(s);s.loader.exec_module(m); m.ROOT=pathlib.Path('+repr(str(temp/'lab'))+');raise SystemExit(m.main())'
            cmd=[sys.executable,'-c',code,'--bench',str(bench),'--artifacts',str(temp/'not-read'),'--mcp-client',str(temp/'mcp_client.py'),'--wait-for-hardware','--only','perf']
            process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                end=time.monotonic()+5;records=[]
                while time.monotonic()<end:
                    records=list((temp/'lab/runs').glob('*/mutex.json'))
                    if records:break
                    time.sleep(.05)
                self.assertTrue(records)
                self.assertEqual(json.loads(records[0].read_text())['state'],'waiting')
                (records[0].parent/'CANCEL').touch()
                stdout,stderr=process.communicate(timeout=7)
                self.assertEqual(process.returncode,2,stderr)
                self.assertIn('Cancelled before hardware access',stdout)
                self.assertFalse((records[0].parent/'results.json').exists())
            finally:
                if process.poll() is None:process.kill();process.wait()
                lock.close()
