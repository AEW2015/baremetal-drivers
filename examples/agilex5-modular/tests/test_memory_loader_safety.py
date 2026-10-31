"""Offline ELF rejection and ownership-limited debugger cleanup."""
import importlib.util
import hashlib
import json
import sys
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import contextlib
import io
import shutil
import types
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('memory_loader',ROOT/'upstream-lab/hardware.py')
hardware=importlib.util.module_from_spec(spec);spec.loader.exec_module(hardware)

def image(**changes):
    data=bytearray(256);data[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI',data,16,2,183,1)
    struct.pack_into('<QQ',data,24,0x82400000,64)
    struct.pack_into('<HHH',data,52,64,56,1)
    fields=dict(kind=1,flags=5,start=240,vma=0x82400000,lma=0x82400000,length=4,memory=4,align=1)
    fields.update(changes)
    struct.pack_into('<IIQQQQQQ',data,64,*fields.values());data[240:244]=b'code'
    return data

class LoaderSafety(unittest.TestCase):
    def check_image(self,data):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'image.elf';path.write_bytes(data)
            return hardware.practice_segments(path)

    def test_rejects_unsafe_headers_ranges_permissions_and_bss(self):
        cases=[image(flags=6),image(vma=0x10000000),image(memory=0x10000000),
               image(length=4,memory=1),image(start=255),image(align=3),
               image(length=0,memory=0x10000000)]
        truncated=image();struct.pack_into('<Q',truncated,32,240);cases.append(truncated)
        dynamic=image();struct.pack_into('<H',dynamic,16,3);cases.append(dynamic)
        for data in cases:
            with self.subTest(header=bytes(data[16:120])):
                with self.assertRaises(RuntimeError):self.check_image(data)

    def test_rwx_remains_supported(self):
        self.assertEqual(self.check_image(image(flags=7)),[(0x82400000,b'code')])

    def test_rejects_overlapping_runtime_and_load_ranges(self):
        for vma,lma in [(0x82400000,0x82500000),(0x82500000,0x82400000)]:
            data=image();struct.pack_into('<H',data,56,2)
            struct.pack_into('<IIQQQQQQ',data,120,1,6,244,vma,lma,4,4,1)
            with self.assertRaisesRegex(RuntimeError,'Overlapping'):self.check_image(data)

    def test_bss_only_segment_validated_but_not_transferred(self):
        data=image();struct.pack_into('<H',data,56,2)
        struct.pack_into('<IIQQQQQQ',data,120,1,6,244,0x82600000,0x82500000,0,4096,1)
        self.assertEqual(self.check_image(data),[(0x82400000,b'code')])
        struct.pack_into('<Q',data,120+40,0x400000)
        with self.assertRaisesRegex(RuntimeError,'outside owned RAM'):self.check_image(data)

    def test_all_artifact_hashes_checked_before_preflight_returns(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);metadata={'artifacts':{}}
            for name in ('good','bad'):
                for suffix,data in [('.elf',image()),('.bin',b'code')]:
                    path=folder/(name+suffix);path.write_bytes(data)
                    metadata['artifacts'][path.name]=hashlib.sha256(data).hexdigest()
            (folder/'bad.bin').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError,'hash mismatch: bad.bin'):
                hardware.preflight_payloads(folder,['good','bad'],metadata)

    def test_bad_elf_rejected_before_mcp_import_and_bench_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);metadata={'target':'agilex5','artifacts':{}}
            for suffix,data in [('.elf',image(flags=6)),('.bin',b'code')]:
                path=folder/('ddr-path'+suffix);path.write_bytes(data)
                metadata['artifacts'][path.name]=hashlib.sha256(data).hexdigest()
            (folder/'build.json').write_text(json.dumps(metadata))
            process=subprocess.run([sys.executable,str(ROOT/'upstream-lab/hardware.py'),
                '--suite','memory-ddr','--bench',str(folder/'missing-bench'),
                '--artifacts',str(folder),'--mcp-client',str(folder/'missing-mcp.py')],capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0)
            self.assertIn('ELF entry is not backed by executable',process.stderr)
            self.assertNotIn('No module named',process.stderr)
            self.assertFalse((folder/'missing-bench').exists())

    def test_payload_changed_during_bootstrap_never_reaches_uart_or_debugger(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);artifacts=folder/'artifacts';artifacts.mkdir()
            metadata={'target':'agilex5','artifacts':{}}
            for suffix,data in [('.elf',image()),('.bin',b'code')]:
                p=artifacts/('ddr-path'+suffix);p.write_bytes(data)
                metadata['artifacts'][p.name]=hashlib.sha256(data).hexdigest()
            (artifacts/'build.json').write_text(json.dumps(metadata))
            fake_root=folder/'lab';(fake_root/'memory-labs').mkdir(parents=True)
            shutil.copy2(ROOT/'memory-labs/hardware_oracle.py',fake_root/'memory-labs/hardware_oracle.py')
            bench=folder/'bench';(bench/'examples').mkdir(parents=True)
            (bench/'ddr-bringup').mkdir();(bench/'ddr-bringup/ddr_probe.hps.rbf').write_bytes(b'bootstrap-fixture')
            client=Mock();client.call.return_value={'ids':['0364f0dd','4ba06477']}
            module=types.ModuleType('mcp_client');module.MCP=Mock(return_value=client)
            calls=[]
            def bootstrap_only(command,**kwargs):
                self.assertEqual(Path(command[1]).name,'run_ddr.py')
                calls.append(command)
                (artifacts/'ddr-path.bin').write_bytes(b'changed while DDR initialized')
                return subprocess.CompletedProcess(command,0,b'fixture bootstrap',b'')
            argv=['hardware.py','--suite','memory-ddr','--bench',str(bench),
                  '--artifacts',str(artifacts),'--mcp-client',str(folder/'mcp_client.py'),
                  '--port',str(folder/'never-a-real-uart')]
            with patch.object(hardware,'ROOT',fake_root),patch.object(sys,'argv',argv),\
                 patch.object(sys,'path',list(sys.path)),patch.dict(sys.modules,{'mcp_client':module}),\
                 patch.object(hardware.subprocess,'run',side_effect=bootstrap_only),\
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'Payload changed during bootstrap'):
                    hardware.main()
            self.assertEqual(len(calls),2) # Initial fixture + restoration fixture.
            self.assertFalse((bench/'examples/build/upstream26-ddr-path.bin').exists())
            records=list((fake_root/'runs').glob('*/results.json'))
            self.assertEqual(json.loads(records[0].read_text())['tests'],[])

    def test_cleanup_waits_for_remote_timeout_without_killing_completed_remote(self):
        child=Mock();child.poll.return_value=None;child.wait.return_value=124
        with self.assertRaises(OSError):
            try:raise OSError('UART disconnected')
            finally:hardware.reap_debugger(child)
        child.wait.assert_called_once_with(timeout=40)
        child.terminate.assert_not_called();child.kill.assert_not_called()

    def test_cleanup_during_base_exception(self):
        child=Mock();child.poll.return_value=None
        child.wait.side_effect=[subprocess.TimeoutExpired('docker',40),subprocess.TimeoutExpired('docker',5),-9]
        with self.assertRaises(KeyboardInterrupt):
            try:raise KeyboardInterrupt()
            finally:hardware.reap_debugger(child)
        self.assertEqual([call.kwargs['timeout'] for call in child.wait.call_args_list],[40,5,5])
        child.terminate.assert_called_once_with();child.kill.assert_called_once_with()

    def test_cleanup_leaves_already_completed_child_alone(self):
        child=Mock();child.poll.return_value=0;hardware.reap_debugger(child)
        child.wait.assert_not_called();child.terminate.assert_not_called();child.kill.assert_not_called()

    def test_stopping_local_docker_does_not_confirm_remote_exit(self):
        child=Mock();child.poll.return_value=None
        child.wait.side_effect=[subprocess.TimeoutExpired('docker',40),0]
        self.assertFalse(hardware.reap_debugger(child))
        child.terminate.assert_called_once_with()

if __name__=='__main__':unittest.main()
