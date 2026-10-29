#!/usr/bin/env python3
"""Host-only Modular ES bench runner with fresh DDR per image."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,os,select,subprocess,sys,termios,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('new_examples',Path(__file__).with_name('run.py'))
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',type=Path,required=True,help='Established baremetal-guide-validation directory')
    p.add_argument('--artifacts',type=Path,required=True,help='Host directory containing upstream-lab-agilex5 binaries/build.json')
    p.add_argument('--mcp-client',type=Path,required=True,help='Existing quartus26-mcp-demos/mcp_client.py')
    p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
    p.add_argument('--wait-for-hardware',action='store_true',help='Queue on the shared bench mutex instead of failing busy')
    p.add_argument('--bl31',type=Path,help='Verified pinned RESET_TO_BL31 image')
    p.add_argument('--only',default='crc,perf,combophy,noc,reset')
    a=p.parse_args();names=a.only.split(',')
    if any(n not in ('crc','perf','combophy','noc','reset','mailbox','bridge-control') for n in names):p.error('Hardware qualification supports crc,perf,combophy,noc,reset only')
    sys.path.insert(0,str(a.mcp_client.parent));from mcp_client import MCP
    out=ROOT/'runs'/('upstream26-hardware-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));out.mkdir(parents=True)
    def write_mutex(data):
        temporary=out/'mutex.json.tmp'
        temporary.write_text(json.dumps(data,indent=2)+'\n')
        temporary.replace(out/'mutex.json')
    lock=(a.bench/'examples/hardware.lock').open('a')
    queued=time.monotonic()
    while True:
        if (out/'CANCEL').exists():
            write_mutex({'state':'cancelled','pid':os.getpid()})
            lock.close();print('Cancelled before hardware access',flush=True);return 2
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:
            if not a.wait_for_hardware:lock.close();raise RuntimeError('Bench mutex busy; use --wait-for-hardware to queue without interrupting its owner')
            write_mutex({'state':'waiting','pid':os.getpid(),'lock':str(a.bench/'examples/hardware.lock'),'wait_seconds':round(time.monotonic()-queued)})
            print('WAITING_FOR_HARDWARE_MUTEX '+str(out),flush=True)
            time.sleep(5)
    if (out/'CANCEL').exists():
        write_mutex({'state':'cancelled','pid':os.getpid()})
        lock.close();print('Cancelled before hardware access',flush=True);return 2
    write_mutex({'state':'acquired','pid':os.getpid(),'wait_seconds':round(time.monotonic()-queued)})
    record={'environment':'physical Modular ES','requested_tests':names,'runner_sha256':lab.digest(Path(__file__)),'tests':[],'build':json.loads((a.artifacts/'build.json').read_text()),'restoration':'pending',
            'bl31_sha256':lab.digest(a.bl31) if a.bl31 else None,'bootstrap_image_sha256':lab.digest(a.bench/'ddr-bringup/ddr_probe.hps.rbf')}
    def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Evidence: '+str(out),flush=True);save()
    mcp=MCP('programmer');bootstrap_failed=False
    def bootstrap(label):
        nonlocal bootstrap_failed
        chain=mcp.call('read_jtag_config',{});(out/(label+'-chain.json')).write_text(json.dumps(chain,indent=2))
        text=json.dumps(chain).lower()
        if '364f0dd' not in text:raise RuntimeError('Modular ES silicon not present')
        r=subprocess.run(['python3',str(a.bench/'ddr-bringup/run_ddr.py'),'--port',a.port]+(['--full-recovery'] if '4ba06477' not in text else []),capture_output=True,timeout=230)
        (out/(label+'-bootstrap.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:
            bootstrap_failed=True
            raise RuntimeError('DDR bootstrap failed; stop board operations')
    try:
        for name in names:
            image=a.artifacts/(name+'.bin');elf=a.artifacts/(name+'.elf')
            for path in (image,elf):
                if lab.digest(path)!=record['build']['artifacts'][path.name]:raise RuntimeError('Artifact hash mismatch')
            bootstrap(name)
            destination=a.bench/'examples/build'/('upstream26-'+image.name)
            destination.write_bytes(image.read_bytes())
            container_image='/home/dev/baremetal-guide-validation/examples/build/'+destination.name
            cfg='/home/dev/baremetal-guide-validation/ocram/agilex5.cfg'
            fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
            body=b''
            try:
                attrs=termios.tcgetattr(fd);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL
                attrs[4]=attrs[5]=termios.B115200;attrs[6][termios.VMIN]=attrs[6][termios.VTIME]=0
                termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
                readback=container_image+'.readback'
                prefix='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; '
                command=prefix+f'targets hps.sys_bus; load_image {container_image} 0x82400000 bin; dump_image {readback} 0x82400000 {image.stat().st_size}; shutdown'
                loaded=subprocess.run(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-c',command],capture_output=True,timeout=40)
                (out/(name+'-load.log')).write_bytes(loaded.stdout+loaded.stderr)
                actual=Path(str(destination)+'.readback')
                if loaded.returncode or not actual.is_file() or actual.read_bytes()!=image.read_bytes():
                    raise RuntimeError('Payload load/readback failed; CPU was not resumed')
                (out/(name+'-readback.json')).write_text(json.dumps({'status':'pass','bytes':image.stat().st_size,'sha256':lab.digest(actual)},indent=2)+'\n')
                if a.bl31:
                    monitor=a.bench/'examples/build/upstream26-bl31.bin'
                    monitor.write_bytes(a.bl31.read_bytes())
                    remote='/home/dev/baremetal-guide-validation/examples/build/upstream26-bl31.bin'
                    load=prefix+f'targets hps.sys_bus; load_image {remote} 0x80000000 bin; dump_image {remote}.readback 0x80000000 {monitor.stat().st_size}; shutdown'
                    result=subprocess.run(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-c',load],capture_output=True,timeout=40)
                    (out/(name+'-bl31-load.log')).write_bytes(result.stdout+result.stderr)
                    if result.returncode or Path(str(monitor)+'.readback').read_bytes()!=monitor.read_bytes():raise RuntimeError('BL31 load/readback failed')
                    command=prefix+'reg x0 0; reg x1 0; reg x2 0; reg x3 0; resume 0x80000000; shutdown'
                else:
                    command=prefix+'resume 0x82400000; shutdown'
                observations={}

                # OpenOCD is bounded; the existing bootstrap leaves secondaries parked.
                with (out/(name+'-debug.log')).open('wb') as log:
                    proc=subprocess.Popen(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-c',command],stdout=log,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+35;done_at=None
                    while time.monotonic()<deadline:
                        if select.select([fd],[],[],.1)[0]:
                            try:chunk=os.read(fd,65536)
                            except BlockingIOError:continue
                            if not chunk:raise RuntimeError('UART disconnected')
                            body+=chunk
                            for marker in (b'COUNTER_INTERVAL_START',b'COUNTER_INTERVAL_END'):
                                if marker in body and marker.decode() not in observations:observations[marker.decode()]=time.monotonic()

                        if proc.poll() is not None and proc.returncode:break
                        if b'UPSTREAM_LAB_COMPLETE' in body and proc.poll() is not None:
                            if done_at is None:done_at=time.monotonic()
                            if time.monotonic()-done_at>.5:break
                    if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
                uart=body.decode(errors='replace').replace('\r','')
                (out/(name+'-uart.txt')).write_text(uart)
                status=lab.assess(name,uart,proc.returncode)
                if name=='perf':
                    interval=observations.get('COUNTER_INTERVAL_END',0)-observations.get('COUNTER_INTERVAL_START',0)
                    (out/'perf-clock-observation.json').write_text(json.dumps({'interval_seconds':interval,'expected_seconds':1.0,'acceptance':[0.9,1.1]},indent=2)+'\n')
                    if not .9<=interval<=1.1:status='fail'

                item={'name':name,'status':status,'debug_exit':proc.returncode,'elf_sha256':lab.digest(elf),'timing_valid':name=='perf' and status=='pass' and 'TIMING_UNAVAILABLE' not in uart,'uart_path':a.port,'entry':'0x82400000'}
                record['tests'].append(item);save();print(name+': '+status+'\n'+uart[-2600:],flush=True)
                if proc.returncode:raise RuntimeError('Debugger failed; stop before the next payload')
            finally:os.close(fd)
    except BaseException as exc:
        record['error']=repr(exc);save();raise
    finally:
        try:
            if bootstrap_failed:record['restoration']='not attempted after bootstrap failure'
            else:bootstrap('restore');record['restoration']='pass'
        except Exception as exc:record['restoration']='fail';record['restore_error']=repr(exc)
        save();mcp.close();lock.close();write_mutex({'state':'released','pid':os.getpid(),'restoration':record['restoration']});print('DDR Hello restoration: '+record['restoration'],flush=True)
    return int(record['restoration']!='pass' or any(t['status'] not in ('pass','unsupported') for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
