"""Simics process control and evidence; never accesses physical board devices."""
import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'build/simics26'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new_run(label):
    out=ROOT/'runs'/('simics-'+label+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True);print('Evidence: '+str(out),flush=True);return out

def execute(project,script,log,timeout):
    project=Path(project).resolve()
    if not (project/'simics').is_file():raise RuntimeError('Deploy the model first: python3 simics/setup.py --simics-root PATH')
    start=time.monotonic()
    with Path(log).open('w') as output:
        proc=subprocess.Popen([str(project/'simics'),'--batch-mode','--no-win',str(Path(script).resolve())],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124
        except BaseException:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
    return code,time.monotonic()-start,Path(log).read_text(errors='replace')

def save(out,data):(out/'results.json').write_text(json.dumps(data,indent=2)+'\n')
