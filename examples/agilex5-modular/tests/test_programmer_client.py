"""The built-in programmer adapter does not depend on an external checkout."""
import os
import unittest
from unittest.mock import patch
from mcp_client import MCP, describe_chain
from bench import container_command,container_path,ROOT

class PortableProgrammer(unittest.TestCase):
    def test_chain_keeps_device_positions_and_other_cables_distinct(self):
        text=describe_chain('1) Agilex_5E MDK Carrier [1-4.2.1]\n  4BA06477 ARM DAP\n  0364F0DD A5ED065\n2) Other kit\n  436DB0DD A3\n')
        self.assertIn('  1: Agilex_5E MDK Carrier',text)
        self.assertIn('Device 2: JTAG ID 0x0364F0DD',text)
        self.assertIn('  2: Other kit',text)
        self.assertIn('Device 1: JTAG ID 0x436DB0DD',text)

    def test_cli_discovery_is_labelled_and_never_programs(self):
        with patch.dict(os.environ,{},clear=True), \
             patch('mcp_client.checked_container',return_value='1) Agilex_5E MDK Carrier\n  0364F0DD FPGA\n') as call:
            client=MCP('programmer')
            result=client.call('read_jtag_config',{})
            self.assertEqual(result['backend'],'quartus-cli')
            call.assert_called_once_with(['jtagconfig'],timeout=30)
            client.close()

    def test_native_mode_does_not_require_docker_or_container_mounts(self):
        with patch.dict(os.environ,{'AGILEX_EXECUTION':'native'},clear=True):
            self.assertEqual(container_command(['jtagconfig']),['jtagconfig'])
            self.assertEqual(container_path(ROOT/'build/boot'),str(ROOT/'build/boot'))

    def test_container_mcp_keeps_stdin_open_for_the_protocol(self):
        with patch.dict(os.environ,{'AGILEX_PROGRAMMER_MCP_COMMAND':'["node","server.js"]'},clear=True), \
             patch('mcp_client.subprocess.Popen') as launch, patch.object(MCP,'request',return_value={}):
            launch.return_value.stdout=[]
            client=MCP('programmer')
            self.assertIn('-i',launch.call_args.args[0])
            client.close()

    def test_completed_cli_job_reports_exit_and_reaps_its_owned_process(self):
        from unittest.mock import MagicMock
        with patch.dict(os.environ,{},clear=True):
            client=MCP('programmer')
            process=MagicMock();process.poll.return_value=0
            log=MagicMock();client.jobs['owned']=(process,log)
            result=client.call('get_job_status',{'jobId':'owned'})
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['exitCode'],0)
            process.close.assert_called_once()
            log.close.assert_called_once()
            client.close()
