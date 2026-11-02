import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pr_hardware_runner_test',ROOT/'hardware/run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
class ArtifactGuards(unittest.TestCase):
 def test_real_configuration_status_distinguishes_phase1_from_user_mode(self):
  run.require_fabric_user_mode('Device has entered user mode\n00000000 STATE=IDLE\nCONF_DONE=1, INIT_DONE=1')
  for text in ('Device has completed phase 1 configuration but has not entered user mode\nSTATE=IDLE\nCONF_DONE=1, INIT_DONE=0','Device has entered user mode\nCONF_DONE=1, INIT_DONE=0','Quartus Prime Programmer was successful'):
   with self.assertRaises(RuntimeError):run.require_fabric_user_mode(text)
 def test_changed_artifact_or_mismatched_compatibility_fails_before_hardware(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);data={'device_id':'0364F0DD'}
   for key in ('full_sof','guest_bin','guest_elf','add','xor'):
    p=root/key;p.write_bytes(key.encode());data[key]={'path':str(p),'sha256':run.sha(p)}
   for key in ('add','xor'):
    p=root/(key+'.compatibility.json');p.write_text('{"offline-test-fixture":true}')
    data[key]['compatibility']={'status':'pass','parent_sha256':data['full_sof']['sha256'],'child_sha256':data[key]['sha256'],'path':str(p),'sha256':run.sha(p)}
   manifest=root/'manifest.json';manifest.write_text(json.dumps(data));self.assertEqual(run.validate_manifest(manifest),data)
   relative=copy.deepcopy(data)
   for key in ('full_sof','guest_bin','guest_elf','add','xor'):
    relative[key]['path']=Path(relative[key]['path']).name
   for key in ('add','xor'):
    relative[key]['compatibility']['path']=Path(relative[key]['compatibility']['path']).name
   manifest.write_text(json.dumps(relative));self.assertEqual(run.validate_manifest(manifest),data)
   for change in ('wrong-device','wrong-parent','failed-check'):
    d=copy.deepcopy(data)
    if change=='wrong-device':d['device_id']='436DB0DD'
    elif change=='wrong-parent':d['xor']['compatibility']['parent_sha256']='0'*64
    else:d['xor']['compatibility']['status']='fail'
    manifest.write_text(json.dumps(d))
    with self.assertRaises(ValueError,msg=change):run.validate_manifest(manifest)
   manifest.write_text(json.dumps(data));(root/'xor').write_bytes(b'rebuilt-bitstream')
   with self.assertRaises(ValueError):run.validate_manifest(manifest)
if __name__=='__main__':unittest.main()

class HpsEvidence(unittest.TestCase):
 def test_hps_pass_requires_sdm_and_continuity_without_host_requests(self):
  text='PR_LAB_BEGIN hps_sdm_loader=1\n'
  for marker in ('INITIAL_ADD_ID','INITIAL_ADD_VECTORS','XOR_VECTORS','RETURN_ADD_VECTORS','TWO_RUNTIME_SWAPS','PR_BAD_CRC_REJECTED','PR_BAD_CRC_REMAINS_ISOLATED'):
   text+='PASS '+marker+'\n'
  for marker in ('SWAP_RESET_AND_ID','STATIC_SCRATCH_CONTINUITY','STATIC_HEARTBEAT_PROGRESS','DDR_GUARD_256_WORDS','ISOLATED_READ_RESPONSE','PR_SDM_BUFFER_CRC32','PR_SDM_RECONFIG_COMPLETE','PR_SDM_OCRAM_READBACK','PR_SDM_OCRAM_RESTORED'):
   text+=('PASS '+marker+'\n')*2
  text+='PR_SDM_ACKNOWLEDGED_BLOCKS=0x1\n'*2+'PR_PERSONA=0x584f5231\nPR_PERSONA=0x41444431\nPR_LAB_COMPLETE status=0\n'
  self.assertEqual(run.hps_completed_loads(text),['xor','add'])
  self.assertEqual(run.hps_completed_loads(text.replace('0x41444431','0x584f5231')),[])
  self.assertTrue(run.assess_guest(text,run.hps_completed_loads(text),'hps'))
  self.assertTrue(run.assess_guest(text,['xor','add'],'hps'))
  for broken in (text.replace('PASS PR_SDM_RECONFIG_COMPLETE','ABSENT'),text.replace('PASS DDR_GUARD_256_WORDS','ABSENT'),text+'PR_HOST_LOAD_REQUEST=0x1\n',text+'FAIL injected\n',text+'PR_LAB_COMPLETE status=0\n'):
   self.assertFalse(run.assess_guest(broken,['xor','add'],'hps'))
  self.assertFalse(run.assess_guest(text,['xor'],'hps'))
  self.assertFalse(run.assess_guest(text,['xor','add'],'jtag'))

class JtagEvidence(unittest.TestCase):
 def test_original_qualified_uart_still_passes_default_mode(self):
  capture=ROOT.parents[1]/'validation/portable-20261102/hardware-pr/guest-uart.txt'
  self.assertTrue(run.assess_guest(capture.read_text(),['xor','add'],'jtag'))
  self.assertEqual(run.hps_completed_loads(capture.read_text()),[])

class QualifiedHpsEvidence(unittest.TestCase):
 def test_real_hps_uart_produces_completed_loads_and_a_pass(self):
  capture=ROOT/'validation/20261102-hps-sdm/guest-uart.txt'
  text=capture.read_text()
  self.assertTrue(run.assess_guest(text,run.hps_completed_loads(text),'hps'))
  self.assertFalse(run.assess_guest(text.replace('PASS RETURN_ADD_VECTORS','ABSENT'),run.hps_completed_loads(text),'hps'))
