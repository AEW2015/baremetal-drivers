"""Memory payload safety and physical-console outcome checks, without board access."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('memory_hw_oracle',ROOT/'memory-labs/hardware_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

class MemoryHardware(unittest.TestCase):
    def test_qemu_addressed_payload_rejected_before_hardware_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);build=path/'build';build.mkdir()
            (build/'build.json').write_text(json.dumps({'target':'qemu'}))
            process=subprocess.run([sys.executable,str(ROOT/'upstream-lab/hardware.py'),
                '--suite','memory-ddr','--bench',str(path/'missing-bench'),
                '--artifacts',str(build),'--mcp-client',str(path/'missing-mcp.py')],capture_output=True,text=True)
            self.assertEqual(process.returncode,2,process.stderr)
            self.assertIn('never load QEMU-addressed artifacts',process.stderr)
            self.assertFalse((path/'missing-bench').exists())

    def test_recorded_ddr_outcomes_require_completion_and_clean_debugger(self):
        folder=ROOT/'memory-labs/ddr/validation/qemu-final'
        for name in ('ddr-path','ddr-copy-fault','ddr-clock-fault'):
            with self.subTest(name=name):
                body=(folder/(name+'.log')).read_text().replace('\r','')
                self.assertEqual(oracle.assess('ddr',name,body,0),'pass')
                self.assertEqual(oracle.assess('ddr',name,body,1),'fail')
                stripped=body.replace('LAB COMPLETE','MISSING').replace('LAB FAILED','MISSING')
                self.assertEqual(oracle.assess('ddr',name,stripped,0),'fail')
                if name!='ddr-path':self.assertEqual(oracle.assess('ddr',name,body+'\nLAB COMPLETE\n',0),'fail')

    def test_calibrated_variant_requires_one_ordered_interval_before_guest(self):
        body=(ROOT/'memory-labs/ddr/validation/qemu-final/ddr-path.log').read_text()
        self.assertEqual(oracle.assess('ddr','ddr-calibrated',body,0),'fail')
        prefix=('DDR_CALIBRATION_BEGIN nominal_seconds=1 host_interval_required\n'
                'PASS DDR_CALIBRATION_EL3_CACHE_OFF\nPASS DDR_CALIBRATION_DECLARED_400MHZ\n'
                'PASS DDR_COUNTER_ADVANCES_BEFORE_CALIBRATION\n'
                'DDR_CALIBRATION_DECLARED_HZ=0x0000000017d78400\n'
                'COUNTER_INTERVAL_START\nCOUNTER_INTERVAL_END\n'
                'DDR_CALIBRATION ticks=400000001 polls=10000000\n'
                'PASS DDR_CALIBRATION_INTERVAL_COMPLETE\n')
        self.assertEqual(oracle.assess('ddr','ddr-calibrated',prefix+body,0),'pass')
        self.assertEqual(oracle.assess('ddr','ddr-calibrated',prefix+prefix+body,0),'fail')
        self.assertEqual(oracle.assess('ddr','ddr-calibrated','COUNTER_INTERVAL_START\nCOUNTER_INTERVAL_END\n'+body,0),'fail')
        for broken in ('FAIL DDR_CALIBRATION_DECLARED_400MHZ\n'+prefix,
                       'LAB FAILED\n'+prefix,
                       prefix.replace('PASS DDR_CALIBRATION_INTERVAL_COMPLETE','MISSING'),
                       prefix.replace('ticks=400000001','ticks=399999999'),
                       prefix.replace('polls=10000000','polls=268435456')):
            self.assertEqual(oracle.assess('ddr','ddr-calibrated',broken+body,0),'fail')

    def test_recorded_dsu_outcomes_require_quiescence_and_integrity(self):
        folder=ROOT/'memory-labs/dsu/validation'
        for name in ('normal','corrupt','stalled','contention'):
            with self.subTest(name=name):
                body=(folder/(name+'.log')).read_text().replace('\r','')
                self.assertEqual(oracle.assess('dsu',name,body,0),'pass')
                self.assertEqual(oracle.assess('dsu',name,body,124),'fail')
                if name in ('normal','contention'):
                    body=body.replace('PASS SECONDARIES_CLEANED_AND_QUIESCENT','MISSING')
                    self.assertEqual(oracle.assess('dsu',name,body,0),'fail')

if __name__=='__main__':unittest.main()
