#!/usr/bin/env python3
"""Copy source inputs from the qualified bench baseline; never modify it or fit."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline',required=True,type=Path,help='Matching Modular ES HPS baseline vendor directory')
p.add_argument('--output',required=True,type=Path,help='New empty project directory')
a=p.parse_args();src=a.baseline.resolve();out=a.output.resolve()
if not (src/'baseline_a55.qsf').is_file():p.error('Missing baseline_a55.qsf')
if 'A5ED065BB32AE6SR0' not in (src/'baseline_a55.qsf').read_text():p.error('Baseline must target the actual Modular ES part')
if out.exists():p.error('Output must not exist; preserve prior attempts')
# Parse QSF source dependencies, plus the declarative IP/Qsys and custom RTL inputs.
keep={'.qsys','.ip','.qsf','.sdc','.sv','.v','.tcl','.hex','.mif','.dawf','.qpf'}
files=[]
for f in src.rglob('*'):
 rel=f.relative_to(src)
 if not f.is_file() or f.suffix not in keep:continue
 if any(x in ('synth','sim','simulation','submodules','qdb','dni','output_files') for x in rel.parts):continue
 # Generated IP products may contain copies; source .ip files are at ip/<system>/<name>.ip.
 if rel.parts[0]=='ip' and (len(rel.parts)!=3 or f.suffix!='.ip'):continue
 if rel.parts[0] in ('baseline_top','fabric_subsys','hps_subsys','shell_subsys','niosv_subsys'):continue
 files.append(f)
out.mkdir(parents=True)
for f in files:
 d=out/f.relative_to(src);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
root=Path(__file__).resolve().parents[1]
# Retain component file paths relative to fabric/pr and fabric/rtl.
shutil.copytree(root,out/'custom_ip/baremetal/fabric/pr',ignore=shutil.ignore_patterns('__pycache__','validation','hardware'))
shutil.copytree(root.parent/'rtl',out/'custom_ip/baremetal/fabric/rtl')
shutil.copy2(Path(__file__).with_name('overlay.tcl'),out/'overlay.tcl')
# The bench's integrated wrapper owned Reset Release. This standalone top must own it.
clock_source=out/'src/clocks_and_resets.sv'
clock_text=clock_source.read_text()
old="wire ninit_done = 1'b0; // Reset release comes from the existing Nios system via fpga_reset_n."
if old in clock_text:
 clock_text=clock_text.replace(old,'wire ninit_done;\n    user_rst_clkgate u_reset_release (.ninit_done(ninit_done));')
assert re.search(r'\buser_rst_clkgate\s+\w+\s*\(',clock_text),'No reviewed standalone Reset Release instance'
clock_source.write_text(clock_text)
s=(out/'baseline_a55.qsf').read_text()
s=re.sub(r'^set_global_assignment -name FLOW_DISABLE_ASSEMBLER .*$', 'set_global_assignment -name FLOW_DISABLE_ASSEMBLER OFF',s,flags=re.M)
s=re.sub(r'^set_global_assignment -name IP_FILE ip/niosv_subsys/(?:niosv_m|niosv_onchip_memory)\.ip\n', '', s, flags=re.M)
# This JTAG-only lab loads the whole fabric before HPS, not a later HPS-loaded core.
s=re.sub(r'^set_global_assignment -name HPS_INITIALIZATION .*$', 'set_global_assignment -name HPS_INITIALIZATION \"AFTER INIT_DONE\"', s, flags=re.M)
s+='\nset_global_assignment -name IP_SEARCH_PATHS "custom_ip/**/*"\n'
(out/'baseline_a55.qsf').write_text(s)
(out/'baseline_a55.qpf').write_text('PROJECT_REVISION = \"baseline_a55\"\n')
manifest={'scope':'Source-only staged baseline and PR overlay; no generation, compilation or hardware qualification yet','baseline':str(src),'target':'A5ED065BB32AE6SR0','source_sha256':{str(f.relative_to(src)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'cpu_base':'0x20020000','slot_path_expected':'u_baseline_top|u_fabric_subsys|u_lab_pr|u_lab_pr|slot','next':'Apply overlay with qsys-script; regenerate Qsys/IP; verify actual slot hierarchy and legal PR floorplan; compile base and both implementation revisions; check timing and bitstream compatibility before programming.'}
(out/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('STAGED SOURCE ONLY:',out)
