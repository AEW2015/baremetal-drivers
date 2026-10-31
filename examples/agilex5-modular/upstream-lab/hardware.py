#!/usr/bin/env python3
"""Host-only Modular ES bench runner with fresh DDR per image."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,os,select,struct,subprocess,sys,termios,time
from types import SimpleNamespace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('new_examples',Path(__file__).with_name('run.py'))
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

def practice_segments(elf):
    """Validate the owned ELF runtime/load regions; return sparse file bytes."""
    data=elf.read_bytes()
    if len(data)<64 or data[:7]!=b'\x7fELF\x02\x01\x01':
        raise RuntimeError('Expected little-endian ELF64 AArch64 executable')
    kind,machine,version=struct.unpack_from('<HHI',data,16)
    entry,offset=struct.unpack_from('<QQ',data,24)
    header,size,count=struct.unpack_from('<HHH',data,52)
    if (kind,machine,version)!=(2,183,1) or header!=64 or size!=56 or not count or offset<64 or offset+size*count>len(data):
        raise RuntimeError('Invalid AArch64 executable/program-header layout')
    if entry!=0x82400000:raise RuntimeError('Unexpected practice ELF entry')
    segments=[];runtime=[];physical=[];entry_covered=False
    def owned(address,length):return 0x82400000<=address<address+length<=0x82700000
    def append_range(ranges,address,length):
        if any(address<end and begin<address+length for begin,end in ranges):
            raise RuntimeError('Overlapping ELF load segments')
        ranges.append((address,address+length))
    for i in range(count):
        segment,flags,start,vma,lma,length,memory,align=struct.unpack_from('<IIQQQQQQ',data,offset+i*size)
        if segment!=1:continue
        if length>memory or start+length>len(data):raise RuntimeError('Invalid ELF segment file/memory sizes')
        if not memory:continue
        if not owned(vma,memory) or not owned(lma,memory):raise RuntimeError('Practice load segment outside owned RAM/file')
        if align not in (0,1) and (align&(align-1) or (vma-start)%align):raise RuntimeError('Invalid ELF segment alignment')
        append_range(runtime,vma,memory);append_range(physical,lma,memory)
        if flags&1 and vma<=entry<vma+length and lma+(entry-vma)==entry:entry_covered=True
        if length:segments.append((lma,data[start:start+length]))
    if not segments or not entry_covered:raise RuntimeError('ELF entry is not backed by executable load bytes')
    return segments

def preflight_payloads(artifacts,names,metadata):
    """Reject every requested image before opening the bench or MCP connection."""
    result={}
    for name in names:
        for suffix in ('.bin','.elf'):
            path=artifacts/(name+suffix)
            if lab.digest(path)!=metadata['artifacts'].get(path.name):raise RuntimeError('Artifact hash mismatch: '+path.name)
        result[name]=practice_segments(artifacts/(name+'.elf'))
    return result

def reap_debugger(proc):
    """Wait out our remote timeout before reaping only the local docker child.

    Killing docker exec alone can leave OpenOCD running inside the container.
    Its remote timeout is 30s + 5s kill grace; allow it to expire first.
    """
    if proc.poll() is not None:return True
    try:proc.wait(timeout=40);return True
    except subprocess.TimeoutExpired:pass
    proc.terminate()
    try:proc.wait(timeout=5);return False
    except subprocess.TimeoutExpired:pass
    proc.kill()
    proc.wait(timeout=5)
    # Reaping a forcibly stopped docker client does not confirm remote exit.
    return False

def bl31_load_script(prefix, remote, size):
    """Generate file-based secure load with restoration of the numeric CSW."""
    return prefix.replace('; ', '\n')+f'''hps.dap apsel 0x4000
set csw_report [hps.dap apcsw]
if {{![regexp {{csw (0x[0-9a-fA-F]+)}} $csw_report -> old_csw]}} {{error "CSW decode failed"}}
hps.dap apcsw 0x10000000 0x30000000
set load_status [catch {{
targets hps.sys_bus
load_image {remote} 0x80000000 bin
dump_image {remote}.readback 0x80000000 {size}
}} load_message]
hps.dap apcsw $old_csw
if {{$load_status}} {{error $load_message}}
puts "BL31_LOAD_READBACK_COMPLETE"
shutdown
'''

def bl31_readback_valid(result, readback, expected):
    body=result.stdout+result.stderr
    return (result.returncode==0 and b'Error:' not in body
            and b'BL31_LOAD_READBACK_COMPLETE' in body
            and readback.is_file() and readback.read_bytes()==expected)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',type=Path,required=True,help='Established baremetal-guide-validation directory')
    p.add_argument('--artifacts',type=Path,required=True,help='Host directory containing upstream-lab-agilex5 binaries/build.json')
    p.add_argument('--mcp-client',type=Path,required=True,help='Existing quartus26-mcp-demos/mcp_client.py')
    p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
    p.add_argument('--wait-for-hardware',action='store_true',help='Queue on the shared bench mutex instead of failing busy')
    p.add_argument('--bl31',type=Path,help='Verified pinned RESET_TO_BL31 image')
    p.add_argument('--suite',choices=['upstream','practice','config','memory-ddr','memory-dsu','candidates','psci','services'],default='upstream')
    p.add_argument('--capture-seconds',type=int,help='UART deadline, 5..300; default 180 for memory labs, 35 otherwise')
    p.add_argument('--only')
    a=p.parse_args()
    checker=lab
    allowed=('crc','perf','combophy','noc','reset','mailbox','bridge-control','smc-guard','perf-zero-clock')
    default='crc,perf,combophy,noc,reset'
    if a.suite=='practice':
        spec=importlib.util.spec_from_file_location('practice_runner',ROOT/'practice/run.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        allowed=checker.NAMES+list(checker.oracle.NEGATIVES)
        default=','.join(checker.NAMES)
        if a.bl31:p.error('Practice labs require the standalone EL3 bootstrap; omit --bl31')
    if a.suite=='config':
        spec=importlib.util.spec_from_file_location('config_audit',ROOT/'config-audit/run.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        allowed=checker.NAMES
        default=','.join(allowed)
        if a.bl31:p.error('Configuration snapshots require the standalone EL3 bootstrap; omit --bl31')
    if a.suite=='services':
        spec=importlib.util.spec_from_file_location('service_oracle',ROOT/'service-candidates/oracle.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        allowed=checker.NAMES
        default='fcs' if a.bl31 else 'ecc-readonly'
    if a.suite=='psci':
        spec=importlib.util.spec_from_file_location('psci_oracle',ROOT/'reference/psci/oracle.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        allowed=checker.NAMES
        default='psci'
        if not a.bl31:p.error('PSCI requires resident BL31 and NS EL2; provide --bl31')
    if a.suite=='candidates':
        spec=importlib.util.spec_from_file_location('hardware_candidates',ROOT/'hardware-candidates/oracle.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        allowed=checker.NAMES
        default=','.join(allowed)
        if a.bl31:p.error('Hardware candidates require standalone EL3; omit --bl31')
    if a.suite.startswith('memory-'):
        kind=a.suite.split('-',1)[1]
        spec=importlib.util.spec_from_file_location('memory_oracle',ROOT/'memory-labs/hardware_oracle.py')
        memory=importlib.util.module_from_spec(spec);spec.loader.exec_module(memory)
        checker=SimpleNamespace(assess=lambda name,body,code:memory.assess(kind,name,body,code))
        allowed=memory.DDR_NAMES if kind=='ddr' else memory.DSU_NAMES
        default='ddr-path' if kind=='ddr' else 'normal'
        if a.bl31:p.error('Memory labs require standalone EL3; omit --bl31')
    capture_seconds=a.capture_seconds if a.capture_seconds is not None else (180 if a.suite.startswith('memory-') else 35)
    if not 5<=capture_seconds<=300:p.error('capture-seconds must be 5..300')
    names=(a.only or default).split(',')
    if any(n not in allowed for n in names):p.error('Choose '+','.join(allowed))
    if a.suite=='services':
        if 'fcs' in names and not a.bl31:p.error('FCS services require resident BL31; provide --bl31')
        if 'ecc-readonly' in names and a.bl31:p.error('ECC read-only snapshot requires standalone EL3; omit --bl31')
    if a.suite=='upstream' and a.bl31 and any(n in ('smc-guard','perf-zero-clock') for n in names):p.error('Diagnostic controls require standalone EL3; omit --bl31')
    build_metadata=None;validated_segments={}
    if a.suite.startswith('memory-') or a.suite in ('candidates','psci','services'):
        build_metadata=json.loads((a.artifacts/'build.json').read_text())
        if build_metadata.get('target')!='agilex5':
            p.error('Memory hardware runs require an Agilex5 build; never load QEMU-addressed artifacts')
    if a.suite=='practice' or a.suite.startswith('memory-') or a.suite in ('candidates','psci','services'):
        if build_metadata is None:build_metadata=json.loads((a.artifacts/'build.json').read_text())
        validated_segments=preflight_payloads(a.artifacts,names,build_metadata)
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
    record={'environment':'physical Modular ES','suite':a.suite,'requested_tests':names,'capture_seconds':capture_seconds,'runner_sha256':lab.digest(Path(__file__)),'tests':[],'build':build_metadata if build_metadata is not None else json.loads((a.artifacts/'build.json').read_text()),'restoration':'pending',
            'bl31_sha256':lab.digest(a.bl31) if a.bl31 else None,'bootstrap_image_sha256':lab.digest(a.bench/'ddr-bringup/ddr_probe.hps.rbf')}
    def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Evidence: '+str(out),flush=True);save()
    mcp=MCP('programmer');bootstrap_failed=False;debugger_cleanup_failed=False
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
            image_bytes=image.read_bytes()
            if hashlib.sha256(image_bytes).hexdigest()!=record['build']['artifacts'][image.name]:
                raise RuntimeError('Payload changed during bootstrap; CPU was not resumed')
            destination.write_bytes(image_bytes)
            container_image='/home/dev/baremetal-guide-validation/examples/build/'+destination.name
            cfg='/home/dev/baremetal-guide-validation/ocram/agilex5.cfg'
            fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
            body=b''
            try:
                attrs=termios.tcgetattr(fd);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL
                attrs[4]=attrs[5]=termios.B115200;attrs[6][termios.VMIN]=attrs[6][termios.VTIME]=0
                termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
                readback=container_image+'.readback'
                Path(str(destination)+'.readback').unlink(missing_ok=True)
                prefix='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; '
                command=prefix+f'targets hps.sys_bus; load_image {container_image} 0x82400000 bin; dump_image {readback} 0x82400000 {image.stat().st_size}; shutdown'
                transfers=[(destination,image.read_bytes())]
                if a.suite=='practice' or a.suite.startswith('memory-') or a.suite in ('candidates','psci','services'):
                    command=prefix+'targets hps.sys_bus; '
                    transfers=[]
                    for index,(address,data) in enumerate(validated_segments[name]):
                        segment=destination.with_suffix(f'.segment{index}.bin');segment.write_bytes(data)
                        Path(str(segment)+'.readback').unlink(missing_ok=True)
                        remote_segment='/home/dev/baremetal-guide-validation/examples/build/'+segment.name
                        command+=f'load_image {remote_segment} {address:#x} bin; dump_image {remote_segment}.readback {address:#x} {len(data)}; '
                        transfers.append((segment,data))
                    command+='shutdown'
                loaded=subprocess.run(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-c',command],capture_output=True,timeout=40)
                (out/(name+'-load.log')).write_bytes(loaded.stdout+loaded.stderr)
                if loaded.returncode or any(not Path(str(path)+'.readback').is_file() or Path(str(path)+'.readback').read_bytes()!=expected for path,expected in transfers):
                    raise RuntimeError('Payload load/readback failed; CPU was not resumed')
                (out/(name+'-readback.json')).write_text(json.dumps({'status':'pass','bytes':sum(len(data) for _,data in transfers),'segments':[{'file':path.name,'bytes':len(data),'sha256':lab.digest(Path(str(path)+'.readback'))} for path,data in transfers]},indent=2)+'\n')
                if a.bl31:
                    monitor=a.bench/'examples/build/upstream26-bl31.bin'
                    monitor.write_bytes(a.bl31.read_bytes())
                    remote='/home/dev/baremetal-guide-validation/examples/build/upstream26-bl31.bin'
                    # AXI5 AP bit29 is Non-secure, bit28 Privileged. BL2 protects
                    # the first DDR MiB; BL31 must be loaded with secure debug
                    # transactions. Preserve every other CSW pattern bit and
                    # restore the original pattern before closing the session.
                    Path(str(monitor)+'.readback').unlink(missing_ok=True)
                    # The vendor launcher reparses -c and can lose Tcl quoting.
                    # apcsw returns descriptive text, not just a numeric value.
                    # Run a file and decode the old value before restoring it.
                    load=bl31_load_script(prefix,remote,monitor.stat().st_size)
                    load_script=a.bench/'examples/build'/(out.name+'-'+name+'-bl31-load.tcl')
                    load_script.write_text(load)
                    (out/(name+'-bl31-load.tcl')).write_text(load)
                    remote_script='/home/dev/baremetal-guide-validation/examples/build/'+load_script.name
                    result=subprocess.run(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-f',remote_script],capture_output=True,timeout=40)
                    (out/(name+'-bl31-load.log')).write_bytes(result.stdout+result.stderr)
                    if not bl31_readback_valid(result,Path(str(monitor)+'.readback'),monitor.read_bytes()):
                        raise RuntimeError('BL31 load/readback failed')
                    (out/(name+'-bl31-readback.json')).write_text(json.dumps({'status':'pass','bytes':monitor.stat().st_size,'sha256':lab.digest(monitor),'debug_access':'secure privileged AXI5; original CSW pattern restored'},indent=2)+'\n')
                    command=prefix+'reg x0 0; reg x1 0; reg x2 0; reg x3 0; resume 0x80000000; shutdown'
                else:
                    command=prefix+'resume 0x82400000; shutdown'
                observations={}

                # OpenOCD is bounded; the existing bootstrap leaves secondaries parked.
                with (out/(name+'-debug.log')).open('wb') as log:
                    proc=subprocess.Popen(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f',cfg,'-c',command],stdout=log,stderr=subprocess.STDOUT)
                    try:
                        deadline=time.monotonic()+capture_seconds;done_at=None;input_index=0
                        while time.monotonic()<deadline:
                            if select.select([fd],[],[],.1)[0]:
                                try:chunk=os.read(fd,65536)
                                except BlockingIOError:continue
                                if not chunk:raise RuntimeError('UART disconnected')
                                body+=chunk
                                if a.suite=='practice' and name=='uart' and body.count(b'lab> ')>input_index and input_index<len(checker.UART_CASES):
                                    os.write(fd,checker.UART_CASES[input_index][1]);input_index+=1
                                for marker in (b'COUNTER_INTERVAL_START',b'COUNTER_INTERVAL_END'):
                                    if marker in body and marker.decode() not in observations:observations[marker.decode()]=time.monotonic()

                            if proc.poll() is not None and proc.returncode:break
                            if a.suite=='services':complete=b'SERVICE_COMPLETE' in body
                            elif a.suite=='psci':complete=b'PSCI_COMPLETE' in body
                            elif a.suite=='candidates':complete=b'CANDIDATE_COMPLETE' in body
                            elif a.suite=='config':complete=b'CONFIG_AUDIT_COMPLETE' in body
                            else:complete=(b'LAB COMPLETE' in body or b'LAB FAILED' in body) if a.suite=='practice' or a.suite.startswith('memory-') else b'UPSTREAM_LAB_COMPLETE' in body
                            if complete and proc.poll() is not None:
                                if done_at is None:done_at=time.monotonic()
                                if time.monotonic()-done_at>.5:break
                    finally:
                        try:
                            if not reap_debugger(proc):debugger_cleanup_failed=True
                        except BaseException:
                            debugger_cleanup_failed=True
                            raise
                if debugger_cleanup_failed:raise RuntimeError('Remote debugger exit could not be confirmed; restoration and further programming disabled')
                uart=body.decode(errors='replace').replace('\r','')
                (out/(name+'-uart.txt')).write_text(uart)
                status=checker.assess(name,uart,proc.returncode)
                if a.suite=='config' and status=='pass':
                    (out/(name+'-snapshot.json')).write_text(json.dumps(checker.snapshot(name,uart),indent=2)+'\n')
                calibrated=name=='perf' or (a.suite=='memory-ddr' and name=='ddr-calibrated')
                if calibrated:
                    interval=observations.get('COUNTER_INTERVAL_END',0)-observations.get('COUNTER_INTERVAL_START',0)
                    (out/(name+'-clock-observation.json')).write_text(json.dumps({'interval_seconds':interval,'expected_seconds':1.0,'acceptance':[0.9,1.1],'scope':'Coarse independent host wall-clock rate check; UART/scheduling uncertainty, not precision calibration'},indent=2)+'\n')
                    if not .9<=interval<=1.1:status='fail'

                item={'name':name,'status':status,'debug_exit':proc.returncode,'elf_sha256':record['build']['artifacts'][elf.name],'timing_valid':calibrated and status=='pass' and 'TIMING_UNAVAILABLE' not in uart,'uart_path':a.port,'entry':'0x82400000'}
                record['tests'].append(item);save();print(name+': '+status+'\n'+uart[-2600:],flush=True)
                if proc.returncode:raise RuntimeError('Debugger failed; stop before the next payload')
            finally:os.close(fd)
    except BaseException as exc:
        record['error']=repr(exc);save();raise
    finally:
        try:
            if debugger_cleanup_failed:record['restoration']='not attempted after debugger cleanup failure'
            elif bootstrap_failed:record['restoration']='not attempted after bootstrap failure'
            else:bootstrap('restore');record['restoration']='pass'
        except Exception as exc:record['restoration']='fail';record['restore_error']=repr(exc)
        save();mcp.close();lock.close();write_mutex({'state':'released','pid':os.getpid(),'restoration':record['restoration']});print('DDR Hello restoration: '+record['restoration'],flush=True)
    return int(record['restoration']!='pass' or any(t['status'] not in ('pass','unsupported') for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
