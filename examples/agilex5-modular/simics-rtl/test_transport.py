#!/usr/bin/env python3
"""Host-only error/cleanup checks; fake backends are deliberately not RTL claims."""
import json
from pathlib import Path
import tempfile,time
from transport import Backend
ROOT=Path(__file__).resolve().parents[1]

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)
        def fixture(name,body):
            p=folder/name;p.write_text('#!/usr/bin/env python3\nimport sys,time\nprint("READY 1",flush=True)\n'+body+'\n');p.chmod(0o755);return p
        cases=[('disconnect',fixture('disconnect.py','sys.exit(0)'),'exited before response'),
               ('timeout',fixture('timeout.py','input();time.sleep(30)'),'response timeout'),
               ('bad-reply',fixture('bad.py','input();print("nonsense",flush=True);time.sleep(30)'),'rejected transaction')]
        for name,exe,expected in cases:
            backend=Backend(exe,folder/(name+'.log'),timeout=.2);start=time.monotonic()
            try:backend.access(0,False)
            except (OSError,RuntimeError) as exc:
                assert expected in str(exc) or name=='disconnect' and isinstance(exc,BrokenPipeError),(name,exc)
            else:raise AssertionError(name+' should fail')
            assert backend.process.poll() is not None,name+' child not reaped'
            assert backend.trace.closed and time.monotonic()-start<2,name
            checks.append({'name':name,'status':'pass','child_reaped':True})
        for offset in [3,64]:
            backend=Backend(ROOT/'build/simics-rtl/mode1/Vlab_ip',folder/f'offset{offset}.log')
            try:backend.access(offset,False)
            except ValueError:pass
            else:raise AssertionError('Invalid offset accepted')
            assert backend.process.poll() is not None
            checks.append({'name':'invalid-offset-'+str(offset),'status':'pass','child_reaped':True})
    out=ROOT/'runs/simics-rtl-transport.json';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'scope':'Host transport failure injection; separate from real Simics/RTL execution','tests':checks},indent=2)+'\n')
    print('PASS SIMICS_RTL_TRANSPORT: '+str(len(checks))+' timeout/disconnect/protocol/offset checks; owned children reaped')
if __name__=='__main__':main()
