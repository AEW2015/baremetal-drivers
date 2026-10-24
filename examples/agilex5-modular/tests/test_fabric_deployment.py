"""Fabric metadata checks: no Docker, UART or JTAG access."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
from fabric import run as deployment
from bench import BenchError
class FabricDeployment(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'bootstrap/ddr').mkdir(parents=True);(self.root/'build').mkdir()
        self.images={}
        for name in ('ddr_probe.hps.rbf','ddr_recovery.sof'):
            data=name.encode();(self.root/'bootstrap/ddr'/name).write_bytes(data);self.images[name]=hashlib.sha256(data).hexdigest()
        elf=b'fixture';(self.root/'build/fabric_example.elf').write_bytes(elf)
        self.image={'lwh2f_enabled':True,'images':self.images}
        self.build={'cpu_base':0x20020000,'elf_sha256':hashlib.sha256(elf).hexdigest()}
        self.write();patch=mock.patch.object(deployment,'ROOT',self.root);patch.start();self.addCleanup(patch.stop)
    def write(self):
        (self.root/'bootstrap/ddr/build-manifest.json').write_text(json.dumps(self.image))
        (self.root/'build/fabric-build.json').write_text(json.dumps(self.build))
    def test_matching_metadata(self):self.assertEqual(deployment.verify(),0x20020000)
    def test_disabled_bridge_rejected(self):
        self.image['lwh2f_enabled']=False;self.write()
        with self.assertRaisesRegex(BenchError,'AGILEX_ENABLE_LWH2F'):deployment.verify()
    def test_changed_image_rejected(self):
        (self.root/'bootstrap/ddr/ddr_recovery.sof').write_bytes(b'different')
        with self.assertRaisesRegex(BenchError,'image hash'):deployment.verify()
    def test_changed_elf_rejected(self):
        (self.root/'build/fabric_example.elf').write_bytes(b'different')
        with self.assertRaisesRegex(BenchError,'ELF hash'):deployment.verify()
    def test_invalid_base_rejected(self):
        self.build['cpu_base']=0x82100000;self.write()
        with self.assertRaisesRegex(BenchError,'CPU base'):deployment.verify()
    def test_missing_metadata_is_actionable(self):
        (self.root/'build/fabric-build.json').unlink()
        with self.assertRaisesRegex(BenchError,'Missing/invalid'):deployment.verify()
