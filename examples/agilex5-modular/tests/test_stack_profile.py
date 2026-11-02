import os,unittest,tempfile,contextlib,fcntl,json
from pathlib import Path
from unittest.mock import patch
from stack_bench import StackBench
from bench import ROOT,bootstrap_image_path,bootstrap_requires_full_image
from release_pins import PINS
from hardware_lock import HardwareLock,enter_hardware_locks
from bench import BenchError
class CurrentStack(unittest.TestCase):
 def test_current_profile_uses_mapped_payloads_and_inherits_the_actual_lock(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
   boot=Path(tmp);(boot/'build-manifest.json').write_text(json.dumps({'boot_order':'hps-first'}))
   env={'AGILEX_BOOTSTRAP_DIR':str(boot),'AGILEX_CONTAINER':'agilex26-mcp-demos','AGILEX_CONTAINER_ROOT':'/workspace/pack'}
   with patch.dict(os.environ,env,clear=True):
    b=StackBench('/legacy-bench');self.assertEqual(b.image,boot/'ddr_probe.hps.rbf')
    p=ROOT/'build/bench-transfers/probe.bin';self.assertEqual(b.remote(p),'/workspace/pack/build/bench-transfers/probe.bin')
    self.assertIn('agilex26-mcp-demos',b.command(['openocd']))
    with patch('stack_bench.subprocess.run') as run:
     b.bootstrap('/dev/ttyUSB3',73,full=True);args,kw=run.call_args
     self.assertIn('--full-recovery',args[0]);self.assertEqual(kw['pass_fds'],(73,));self.assertEqual(kw['env']['AGILEX_LOCK_FD'],'73')
 def test_fpga_first_profile_hashes_the_actual_full_image(self):
  with patch.dict(os.environ,{'AGILEX_BOOTSTRAP_DIR':str(ROOT/'build/platform26.3/boot'),'AGILEX_FORCE_FULL_BOOT':'1'},clear=True):
   self.assertEqual(StackBench('/unused').image,ROOT/'build/platform26.3/boot/ddr_recovery.sof')
 def test_external_shared_lock_still_checks_checkout_process_records(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);checkout=root/'checkout';checkout.mkdir()
   (checkout/'.agilex-process-owned').write_text('{}')
   with patch('hardware_lock.ROOT',checkout),patch.dict(os.environ,{'AGILEX_HARDWARE_LOCK':str(root/'shared.lock')},clear=True):
    with self.assertRaisesRegex(BenchError,'Unresolved hardware process'):
     with HardwareLock():pass
 def test_coordination_aliases_do_not_acquire_the_same_inode_twice(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);primary=root/'primary.lock';primary.touch()
   alias=root/'alias.lock';alias.symlink_to(primary)
   hardlink=root/'hardlink.lock';os.link(primary,hardlink)
   with patch('hardware_lock.ROOT',root),patch.dict(os.environ,{'AGILEX_HARDWARE_LOCK':str(primary)},clear=True):
    with contextlib.ExitStack() as stack:
     lock=enter_hardware_locks(stack,[str(alias),str(hardlink)])
     with primary.open('r+') as outsider:
      with self.assertRaises(BlockingIOError):fcntl.flock(outsider,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with primary.open('r+') as outsider:fcntl.flock(outsider,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def test_bootstrap_outside_the_shared_tree_has_a_configuration_error(self):
  with patch.dict(os.environ,{'AGILEX_BOOTSTRAP_DIR':'/outside-the-shared-example-tree'},clear=True):
   with self.assertRaisesRegex(BenchError,'inside the bind-mounted example directory'):
    bootstrap_image_path('ddr_recovery.sof')
 def test_fpga_first_manifest_cannot_select_a_stale_hps_only_image(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);boot=root/'boot';boot.mkdir()
   (boot/'ddr_probe.hps.rbf').write_bytes(b'old hps-first image')
   (boot/'ddr_recovery.sof').write_bytes(b'new full image')
   (boot/'build-manifest.json').write_text(json.dumps({'boot_order':'fpga-first'}))
   with patch('bench.ROOT',root),patch.dict(os.environ,{'AGILEX_BOOTSTRAP_DIR':str(boot)},clear=True):
    self.assertTrue(bootstrap_requires_full_image())
    self.assertEqual(bootstrap_image_path('ddr_probe.hps.rbf'),boot/'ddr_recovery.sof')
 def test_legacy_profile_keeps_recorded_bench_paths(self):
  with patch.dict(os.environ,{},clear=True):
   b=StackBench('/legacy-bench');self.assertFalse(b.current);self.assertEqual(str(b.image),'/legacy-bench/ddr-bringup/ddr_probe.hps.rbf')
   self.assertIn('agilex-xrdp',b.command(['openocd']))
   self.assertEqual(bootstrap_image_path('ddr_recovery.sof'),ROOT/'bootstrap/ddr/ddr_recovery.sof')
 def test_active_firmware_pins_match_the_26_3_release_not_legacy_fixtures(self):
  self.assertEqual(PINS['atf']['commit'],'09c4dc6628810d8570af69db43918d344f9e80e9')
  self.assertEqual(PINS['uboot']['commit'],'5ba74aeda63ed07e98670f8c2f0135de06543ba0')
  self.assertEqual(PINS['quartus']['hps_ip'],'14.1.0');self.assertEqual(PINS['quartus']['hps_emif_ip'],'5.1.0')
if __name__=='__main__':unittest.main()
