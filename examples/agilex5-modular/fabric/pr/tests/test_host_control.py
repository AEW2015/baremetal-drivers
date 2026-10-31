"""Board-free checks for register guards and truthful System Console sentinels."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'hardware/host_control.tcl'
class HostControl(unittest.TestCase):
 def run_case(self,stage='begin',paths='{carrier/u_pr_jtag/master}',signature='0x50525331',status='0x201',scratch='0xcafe1234',bind=False):
  stub=f'''set pr_stage {stage}
set pr_expected 0x584f5231
set writes 0
set host 0
proc get_service_paths {{type}} {{return {{{paths}}}}}
proc open_service {{type path}} {{if {{$path eq {{}}}} {{error {{empty service}}}}}}
proc close_service {{type path}} {{}}
proc master_read_32 {{path address count}} {{
 if {{$count!=1}} {{error {{bad read count}}}}
 switch $address {{
  0x00020058 {{return {signature}}}
  0x00020040 {{return {status}}}
  0x00020048 {{return {scratch}}}
  0x0002004c {{return 0x584f5231}}
  0x00020044 {{return 0xfffffff0}}
  0x00020060 {{return $::host}}
  default {{error {{unexpected address}}}}
 }}
}}
proc master_write_32 {{path address values}} {{
 if {{$address ne {{0x00020060}} || [llength $values]!=1}} {{error {{unsafe write}}}}
 incr ::writes;set ::host [lindex $values 0]
}}
source {{{SCRIPT}}}
puts "STUB_WRITES=$writes HOST=$host"
'''
  if bind:
   prefix="""set pr_sof /fixture/base.sof
set pr_cable {Agilex_5E MDK Carrier [1-4.2.1]}
set pr_index 2
proc design_load {path} {return /design/fixture}
proc design_link {design device} {puts "BOUND $device"}
proc get_service_paths {type} {
 if {$type eq {device}} {return {{/devices/A5E(C065BB32AR0|D065BB32AR0)@2#1-4.2.1#Agilex_5E MDK Carrier} {/devices/VTAP10@3#1-4.2.1#Agilex_5E MDK Carrier}}}
 return {{/devices/A5E(C065BB32AR0|D065BB32AR0)@2#1-4.2.1#Agilex_5E MDK Carrier/(link)/JTAG/(110:132 v1 #1)/phy_1/u_pr_jtag.master}}
}
proc marker_node_info {path} {return {}}
"""
   stub=stub.replace('source {',prefix+'source {',1)
  return subprocess.run(['tclsh'],input=stub,text=True,capture_output=True,timeout=5)
 def test_binds_real_cable_path_then_selects_master_by_hierarchy(self):
  r=self.run_case(bind=True);self.assertIn('PR_HOST_STAGE_RESULT stage=begin PASS',r.stdout,r.stdout+r.stderr);self.assertIn('BOUND /devices/A5E',r.stdout);self.assertNotIn('BOUND /devices/VTAP',r.stdout)
 def test_begin_and_done_require_true_readback_and_busy_phase(self):
  for stage,status,command in [('begin','0x201',1),('done','0x209',2)]:
   r=self.run_case(stage=stage,status=status);self.assertIn('PR_HOST_STAGE_RESULT stage='+stage+' PASS',r.stdout,r.stdout+r.stderr);self.assertIn('STUB_WRITES=1 HOST='+str(command),r.stdout)
 def test_invalid_service_identity_or_state_cannot_write_or_report_success(self):
  for kw in ({'paths':''},{'paths':'carrier/u_pr_jtag/a carrier/u_pr_jtag/b'},{'signature':'0'},{'scratch':'0'},{'status':'0'},{'stage':'done','status':'0x201'},{'stage':'begin','status':'0x209'}):
   with self.subTest(kw=kw):
    r=self.run_case(**kw);self.assertNotIn('PR_HOST_STAGE_RESULT',r.stdout);self.assertIn('PR_HOST_STAGE_ERROR',r.stderr);self.assertIn('STUB_WRITES=0 HOST=0',r.stdout)
if __name__=='__main__':unittest.main()
