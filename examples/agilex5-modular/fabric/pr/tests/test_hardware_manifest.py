import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pr_hardware_runner_test',ROOT/'hardware/run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
class ArtifactGuards(unittest.TestCase):
 def test_changed_artifact_or_mismatched_compatibility_fails_before_hardware(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);data={'device_id':'0364F0DD'}
   for key in ('full_sof','bridge_rbf','guest_bin','guest_elf','add','xor'):
    p=root/key;p.write_bytes(key.encode());data[key]={'path':str(p),'sha256':run.sha(p)}
   for key in ('add','xor'):
    p=root/(key+'.compatibility.json');p.write_text('{"offline-test-fixture":true}')
    data[key]['compatibility']={'status':'pass','parent_sha256':data['full_sof']['sha256'],'child_sha256':data[key]['sha256'],'path':str(p),'sha256':run.sha(p)}
   manifest=root/'manifest.json';manifest.write_text(json.dumps(data));self.assertEqual(run.validate_manifest(manifest),data)
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
