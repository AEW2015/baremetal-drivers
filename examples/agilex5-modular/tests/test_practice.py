"""Cross-platform completion and deliberate-failure acceptance checks."""
import importlib.util,struct,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('practice',ROOT/'practice/run.py')
practice=importlib.util.module_from_spec(spec);spec.loader.exec_module(practice)
spec=importlib.util.spec_from_file_location('practice_hardware',ROOT/'upstream-lab/hardware.py')
hardware=importlib.util.module_from_spec(spec);spec.loader.exec_module(hardware)

class Practice(unittest.TestCase):
    def test_sparse_elf_uses_physical_load_address_and_file_bytes_only(self):
        image=bytearray(256);image[:6]=b'\x7fELF\x02\x01'
        struct.pack_into('<H',image,18,183)
        struct.pack_into('<QQ',image,24,0x82400000,64)
        struct.pack_into('<HH',image,54,56,2)
        struct.pack_into('<IIQQQQQQ',image,64,1,5,240,0x82400000,0x82400000,4,4,4096)
        struct.pack_into('<IIQQQQQQ',image,120,1,6,244,0x82600000,0x82500000,8,4096,4096)
        image[240:252]=b'codeDATA1234'
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'sparse.elf';path.write_bytes(image)
            self.assertEqual(hardware.practice_segments(path),[(0x82400000,b'code'),(0x82500000,b'DATA1234')])
            struct.pack_into('<Q',image,120+24,0x80000000);path.write_bytes(image)
            with self.assertRaisesRegex(RuntimeError,'outside owned RAM'):hardware.practice_segments(path)

    def test_console_prompt_before_begin_is_accepted_but_checks_required(self):
        body='SoCFPGA Bare-Metal > LAB BEGIN exception\nPASS BRK_SYNDROME_AND_RETURN\nPASS FAULT_PC_CAPTURED\nLAB COMPLETE\n'
        self.assertEqual(practice.assess('exception',body,0),'pass')
        self.assertEqual(practice.assess('exception',body.replace('PASS FAULT_PC_CAPTURED',''),0),'fail')
        self.assertEqual(practice.assess('exception',body,124),'fail')

    def test_expected_failure_needs_matching_reason_and_no_success(self):
        body='LAB BEGIN exception\nFAIL unexpected BRK syndrome\nLAB FAILED\n'
        self.assertEqual(practice.assess('exception-wrong-brk',body,0),'pass')
        self.assertEqual(practice.assess('exception-wrong-brk',body+'LAB COMPLETE\n',0),'fail')
        self.assertEqual(practice.assess('exception-wrong-brk',body.replace('unexpected BRK syndrome','another failure'),0),'fail')

    def test_uart_requires_each_boundary_and_recovery_response(self):
        body='LAB BEGIN uart\nlab> '
        for label,payload,expected in practice.UART_CASES:
            body+=payload.decode().replace('\r','\n')+'\n'
            if label=='exit':body+='PASS UART_SESSION\n'
            if expected!=b'lab> ':body+=expected.decode()
            if label!='exit':body+='lab> '
        self.assertEqual(practice.assess('uart',body,0),'pass')
        self.assertEqual(practice.assess('uart',body.replace('ERROR line too long','ERROR unknown command',1),0),'fail')
        self.assertEqual(practice.assess('uart',body.replace('STATUS EL3 READY','',1),0),'fail')
