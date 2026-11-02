"""Portable launcher/configuration checks; these tests never access a board."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portable_lab',ROOT/'lab.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class Launcher(unittest.TestCase):
    def test_default_paths_follow_the_checkout_not_the_working_directory(self):
        with tempfile.TemporaryDirectory(prefix='student lab ') as temporary:
            clone=Path(temporary)/'renamed clone';clone.mkdir()
            shutil.copy2(ROOT/'lab.py',clone/'lab.py')
            result=subprocess.run([sys.executable,str(clone/'lab.py'),'paths'],cwd=temporary,
                                  capture_output=True,text=True,check=True)
            data=json.loads(result.stdout)
            self.assertEqual(Path(data['repo']),clone.resolve())
            self.assertEqual(Path(data['bootstrap']),(clone/'examples/agilex5-modular/build/boot').resolve())

    def test_docker_mount_keeps_a_space_containing_path_in_one_argument(self):
        with patch.object(lab,'REPO',Path('student workspace/repo')):
            args=lab.tool_command(lab.DEFAULTS,['python3','qemu/run.py','--check'])
        self.assertIn(f'type=bind,src={Path("student workspace/repo")},dst=/work',args)
        self.assertNotIn('bash',args)

    def test_native_python_is_the_running_interpreter(self):
        config=dict(lab.DEFAULTS,backend='native')
        self.assertEqual(lab.tool_command(config,['python3','qemu/build.py']),
                         [sys.executable,'qemu/build.py'])

    def test_existing_container_is_configurable(self):
        config=dict(lab.DEFAULTS,container='my-tools',container_root='/src/labs')
        self.assertEqual(lab.tool_command(config,['python3','qemu/run.py']),
            ['docker','exec','-i','-u','dev','-w','/src/labs','my-tools','python3','qemu/run.py'])

    def test_relative_build_paths_are_relative_to_examples(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(lab,'LAB',Path(temporary)):
            self.assertEqual(lab.local_path('build/boot'),(Path(temporary)/'build/boot').resolve())

    def test_unknown_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'config.json';path.write_text('{"private_bench":"wrong"}')
            with self.assertRaisesRegex(ValueError,'Unknown'):lab.load_config(path)

    def test_hardware_cannot_use_an_ephemeral_learning_image(self):
        with patch.object(lab.platform,'system',return_value='Linux'):
            with self.assertRaisesRegex(ValueError,'existing hardware'):lab.hardware_environment(lab.DEFAULTS)

    def test_native_hardware_does_not_select_a_private_container(self):
        with patch.object(lab.platform,'system',return_value='Linux'):
            environment=lab.hardware_environment(dict(lab.DEFAULTS,backend='native',uart='/dev/ttyACM0'))
        self.assertEqual(environment['AGILEX_EXECUTION'],'native')
        self.assertEqual(environment['AGILEX_MCP_CLIENT'],str(lab.LAB/'mcp_client.py'))
        self.assertEqual(environment['AGILEX_BOOTSTRAP_DIR'],str(lab.LAB/'build/boot'))

    def test_windows_hardware_uses_a_clear_wsl_route(self):
        with patch.object(lab.platform,'system',return_value='Windows'):
            with self.assertRaisesRegex(ValueError,'Linux/WSL2'):lab.hardware_environment(lab.DEFAULTS)

    def test_dry_run_never_executes_a_tool(self):
        with patch.object(lab,'load_config',return_value=dict(lab.DEFAULTS)), \
             patch.object(lab.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(lab.main(['--dry-run','qemu']),0)
            data=json.loads(stream.getvalue())
            self.assertEqual(len(data['commands']),2)
            run.assert_not_called()

    def test_windows_wsl_backend_replaces_equals_form_option(self):
        completed=subprocess.CompletedProcess([],0)
        with patch.object(lab,'load_config',return_value=dict(lab.DEFAULTS)), \
             patch.object(lab.platform,'system',return_value='Windows'), \
             patch.object(lab.subprocess,'check_output',return_value='/mnt/c/student repo\n'), \
             patch.object(lab.subprocess,'run',return_value=completed) as run:
            self.assertEqual(lab.main(['--backend=wsl','qemu']),0)
            args=run.call_args.args[0]
            self.assertIn('/mnt/c/student repo',args)
            self.assertNotIn('--backend=wsl',args)
            self.assertEqual(args[-3:],['--backend','native','qemu'])

    def test_container_comma_path_is_rejected_before_docker(self):
        with patch.object(lab,'REPO',Path('bad,path')):
            with self.assertRaisesRegex(ValueError,'comma'):lab.tool_command(lab.DEFAULTS,['python3'])


if __name__=='__main__':unittest.main()
