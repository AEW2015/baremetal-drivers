#!/usr/bin/env python3
"""Register generated hierarchical QIPs; avoid stale generic child regeneration."""
import argparse,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);a=p.parse_args();root=a.project.resolve()
rtl=(root/'niosv_subsys/synth/niosv_subsys.v').read_text()
assert all(n not in rtl for n in ('u_niosv_m','u_niosv_onchip_memory','u_jtag_uart')),'Unused Nios subsystem logic still present'
qips=[root/n/(n+'.qip') for n in ('baseline_top','fabric_subsys','shell_subsys','hps_subsys','niosv_subsys')]
for qip in sorted(root.glob('ip/*/*/*.qip')):
 if qip.parent.name in ('niosv_m','niosv_onchip_memory','jtag_uart'):continue
 qips.append(qip)
for rel in ('ip/shell_subsys/sys_pll/sys_pll.qip','ip/shell_subsys/user_rst_clkgate/user_rst_clkgate.qip'):
 assert root/rel in qips,'Missing standalone clock/reset IP: '+rel
missing=[str(q) for q in qips if not q.is_file()]
assert not missing,'Missing generated QIPs: '+str(missing)
for name in ('baseline_a55','pr_add','pr_xor'):
 f=root/(name+'.qsf')
 if not f.is_file():continue
 s=f.read_text();sdc=[l for l in s.splitlines() if l.startswith('set_global_assignment -name SDC_FILE ')]
 s='\n'.join(l for l in s.splitlines() if not re.match(r'set_global_assignment -name (IP_FILE|QSYS_FILE|QIP_FILE|SDC_FILE) ',l))+'\n'
 s+=''.join('set_global_assignment -name QIP_FILE '+str(q.relative_to(root))+'\n' for q in qips)
 s+='\n'.join(sdc)+'\n';f.write_text(s)
print('Registered',len(qips),'generated QIPs; no unused CPU; SDC last')
