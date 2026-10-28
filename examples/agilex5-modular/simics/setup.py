#!/usr/bin/env python3
"""Container: deploy/build the locally installed Agilex 5 Simics platform."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--simics-root',default=os.environ.get('SIMICS_FPGA_ROOT'))
p.add_argument('--project',type=Path,default=ROOT/'build/simics26')
a=p.parse_args()
cli=Path(a.simics_root)/'bin/simics_intelfpga_cli' if a.simics_root else Path(shutil.which('simics_intelfpga_cli') or '/missing/simics_intelfpga_cli')
if not cli.is_file():p.error('Set SIMICS_FPGA_ROOT to the installation directory containing bin/simics_intelfpga_cli')
project=a.project.resolve();project.mkdir(parents=True,exist_ok=True)
if not (project/'simics').exists():
    if any(project.iterdir()):p.error('Use an empty project directory for deployment')
    subprocess.run([str(cli),'--deploy','agilex5e-universal'],cwd=project,check=True)
target=project/'targets/agilex5e-universal/agilex5e-universal.simics'
if not target.is_file():p.error('The project does not contain the 26.3 Agilex 5 target')
subprocess.run(['make','-j4'],cwd=project,check=True)
version=subprocess.check_output([str(project/'simics'),'--version'],text=True)
(project/'agilex-setup.json').write_text(json.dumps({'cli':str(cli.resolve()),'project':str(project),'platform':'agilex5e-universal','version':version},indent=2)+'\n')
print('PASS SIMICS_SETUP: '+str(project))
