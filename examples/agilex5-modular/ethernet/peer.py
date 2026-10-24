"""Host sockets for the custom bare-metal benchmark (not the iperf protocol)."""
import json,socket,struct,time
MAGIC=0x4e423031
DATA=0x4e424454
class Peer:
 def __init__(self,board='192.168.50.2',host='192.168.50.1'):
  self.board=board;self.host=host;self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.sock.bind((host,0));self.sock.settimeout(3)
 def close(self):self.sock.close()
 def command(self,op,run=1,size=0,rate=0,ms=0,port=0):
  self.sock.sendto(struct.pack('!7I',MAGIC,op,run,size,rate,ms,port),(self.board,5001))
  body,addr=self.sock.recvfrom(4096)
  if addr[0]!=self.board:raise RuntimeError('Unexpected control peer')
  r=json.loads(body)
  if 'error' in r:raise RuntimeError(r['error'])
  return r
 def stats(self):return self.command(2)
 def reset(self,run):return self.command(1,run)
 @staticmethod
 def payload(run,seq,size):return struct.pack('!4I',DATA,run,seq,size)+bytes((run+seq+i)&255 for i in range(16,size))
 def smoke(self):
  results=[]
  def passed(name,**details):results.append(dict(name=name,status='pass',**details));print('PASS '+name,flush=True)
  before=self.stats();t=time.monotonic();time.sleep(1);after=self.stats();dt=time.monotonic()-t
  hz=(after['ticks']-before['ticks'])/dt
  if abs(hz/after['counter_hz']-1)>.05:raise RuntimeError(f'Counter calibration failed: {hz}')
  passed('counter_calibration',measured_hz=hz,configured_hz=after['counter_hz'])
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.bind((self.host,0));s.settimeout(2)
   for size in [64,256,512,1024,1472]:
    payload=bytes(i&255 for i in range(size));s.sendto(payload,(self.board,5002));actual,_=s.recvfrom(4096)
    if actual!=payload:raise RuntimeError('UDP echo payload mismatch')
  passed('udp_echo',sizes=[64,256,512,1024,1472])
  run=1024;self.reset(run)
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.bind((self.host,0))
   for seq in range(100):s.sendto(self.payload(run,seq,1024),(self.board,5003));time.sleep(.001)
   for seq in [0,1,102,101]:s.sendto(self.payload(run,seq,1024),(self.board,5003));time.sleep(.002)
   bad=bytearray(self.payload(run,103,1024));bad[-1]^=1;s.sendto(bad,(self.board,5003))
  time.sleep(.1);r=self.stats()
  if (r['rx_packets'],r['duplicates'],r['reordered'],r['bad'])!=(102,2,1,1):raise RuntimeError(f'UDP negative controls: {r}')
  passed('udp_sequence_and_corruption_controls',stats=r)
  self.reset(1025);pattern=bytes(range(256))*256
  with socket.create_connection((self.board,5004),timeout=3) as s:
   s.sendall(pattern);s.shutdown(socket.SHUT_WR);s.settimeout(3)
   while s.recv(4096):pass
  time.sleep(.1);r=self.stats()
  if r['tcp_rx_bytes']!=len(pattern) or r['tcp_bad_chunks']:raise RuntimeError(f'TCP receive integrity: {r}')
  passed('tcp_board_receive',bytes=len(pattern))
  self.reset(1026);data=bytearray()
  with socket.create_connection((self.board,5005),timeout=3) as s:
   while len(data)<262144:data.extend(s.recv(min(32768,262144-len(data))))
  if data!=bytes(range(256))*1024:raise RuntimeError('TCP transmit integrity')
  passed('tcp_board_transmit',bytes=len(data))
  return results
 def udp_trial(self,direction,size,rate,seconds,run):
  self.reset(run);start_cpu=time.process_time()
  templates=[bytes((run+j+i)&255 for i in range(16,size)) for j in range(256)]
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.bind((self.host,0));s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024)
   if direction=='pc_to_som':
    s.setblocking(False);seq=0;host_unsent=0;start=time.monotonic();end=start+seconds;next_send=start;interval=size*8/rate
    while time.monotonic()<end:
     now=time.monotonic()
     if now<next_send:
      time.sleep(min(next_send-now,.001));continue
     body=struct.pack('!4I',DATA,run,seq,size)+templates[seq&255]
     try:s.sendto(body,(self.board,5003));seq+=1
     except BlockingIOError:host_unsent+=1
     next_send+=interval
    elapsed=time.monotonic()-start;time.sleep(.15);r=self.stats();sent=seq;received=r['rx_packets'];bad=r['bad'];duplicates=r['duplicates'];reordered=r['reordered'];tx_errors=host_unsent
   else:
    s.settimeout(.2);seen=bytearray(1<<22);received=bad=duplicates=reordered=0;highest=-1
    start=time.monotonic();self.command(3,run,size,rate,int(seconds*1000),s.getsockname()[1]);end=start+seconds+.2
    while time.monotonic()<end:
     try:body,_=s.recvfrom(2048)
     except socket.timeout:continue
     if len(body)!=size:bad+=1;continue
     magic,rid,seq,declared=struct.unpack_from('!4I',body)
     if magic!=DATA or rid!=run or declared!=size or seq>=1<<25 or body[16:]!=templates[seq&255]:bad+=1;continue
     bit=1<<(seq&7)
     if seen[seq>>3]&bit:duplicates+=1;continue
     seen[seq>>3]|=bit
     if seq<highest:reordered+=1
     highest=max(highest,seq);received+=1
    elapsed=seconds;r=self.stats();sent=r['tx_packets'];tx_errors=r['tx_errors']
   loss=max(0,sent-received)/sent if sent else 1
   result=dict(protocol='udp',direction=direction,payload_bytes=size,requested_mbps=rate/1e6,seconds=seconds,measured_seconds=elapsed,sent_packets=sent,received_packets=received,loss_fraction=loss,bad_payloads=bad,duplicates=duplicates,reordered=reordered,source_errors=tx_errors,offered_mbps=sent*size*8/elapsed/1e6,receiver_mbps=received*size*8/elapsed/1e6,host_cpu_seconds=time.process_time()-start_cpu,host_receive_buffer=s.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF),board_stats=r)
   if bad:raise RuntimeError(f'UDP payload corruption: {result}')
   return result
 def tcp_trial(self,direction,seconds,streams=1):
  import concurrent.futures,threading
  barrier=threading.Barrier(streams);pattern=bytes(range(256))*129;self.reset(2000);start_cpu=time.process_time()
  cancel=threading.Event();sockets=[]
  print(f'START TCP {direction} streams={streams} seconds={seconds}',flush=True)
  def worker(index):
   port=5004 if direction=='pc_to_som' else 5005
   with socket.create_connection((self.board,port),timeout=3) as s:
    sockets.append(s)
    s.settimeout(10);s.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    barrier.wait(timeout=10);start=time.monotonic();end=start+seconds;count=0
    if direction=='pc_to_som':
     while time.monotonic()<end and not cancel.is_set():s.sendall(pattern[:16384]);count+=16384
     s.shutdown(socket.SHUT_WR)
     while s.recv(4096):pass
    else:
     while time.monotonic()<end and not cancel.is_set():
      body=s.recv(32768)
      if not body:raise RuntimeError('TCP source closed early')
      if body!=pattern[count&255:(count&255)+len(body)]:raise RuntimeError('TCP payload mismatch')
      count+=len(body)
    elapsed=time.monotonic()-start
    info=s.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,104)
    return dict(bytes=count,seconds=elapsed,local_total_retransmissions=struct.unpack_from('I',info,100)[0])
  with concurrent.futures.ThreadPoolExecutor(max_workers=streams) as pool:
   futures={pool.submit(worker,i):i for i in range(streams)};values=[None]*streams
   try:
    for future in concurrent.futures.as_completed(futures):values[futures[future]]=future.result()
   except BaseException:
    cancel.set();barrier.abort()
    for s in sockets:
     try:s.shutdown(socket.SHUT_RDWR)
     except OSError:pass
    raise
  time.sleep(.2);r=self.stats()
  if r['tcp_bad_chunks']:raise RuntimeError(f'TCP sink corruption: {r}')
  total=sum(x['bytes'] for x in values);elapsed=max(x['seconds'] for x in values)
  if direction=='pc_to_som' and r['tcp_rx_bytes']!=total:raise RuntimeError(f'TCP receiver byte count mismatch: {total} / {r}')
  return dict(protocol='tcp',direction=direction,streams=streams,seconds=seconds,received_bytes=total,receiver_mbps=total*8/elapsed/1e6,host_cpu_seconds=time.process_time()-start_cpu,connections=values,board_stats=r)
 def tcp_bidir(self,seconds):
  import concurrent.futures,threading
  self.reset(3000);pattern=bytes(range(256))*129;barrier=threading.Barrier(2);cancel=threading.Event();sockets=[]
  print(f'START TCP simultaneous seconds={seconds}',flush=True)
  def worker(direction):
   with socket.create_connection((self.board,5004 if direction=='pc_to_som' else 5005),timeout=3) as s:
    sockets.append(s)
    s.settimeout(10);s.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));barrier.wait(timeout=10);start=time.monotonic();end=start+seconds;count=0;report_at=start+30
    while time.monotonic()<end and not cancel.is_set():
     if direction=='pc_to_som':s.sendall(pattern[:16384]);count+=16384
     else:
      body=s.recv(32768)
      if not body or body!=pattern[count&255:(count&255)+len(body)]:raise RuntimeError('Bidirectional TCP payload mismatch')
      count+=len(body)
     if time.monotonic()>=report_at:
      elapsed=time.monotonic()-start
      print(f'PROGRESS tcp_bidir {direction}: {elapsed:.0f}s, {count*8/elapsed/1e6:.3f} Mbps',flush=True)
      report_at+=30
    if direction=='pc_to_som':
     s.shutdown(socket.SHUT_WR)
     while s.recv(4096):pass
    elapsed=time.monotonic()-start
    return dict(direction=direction,bytes=count,seconds=elapsed,receiver_mbps=count*8/elapsed/1e6)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   futures={pool.submit(worker,direction):i for i,direction in enumerate(['pc_to_som','som_to_pc'])};values=[None]*2
   try:
    for future in concurrent.futures.as_completed(futures):values[futures[future]]=future.result()
   except BaseException:
    cancel.set();barrier.abort()
    for s in sockets:
     try:s.shutdown(socket.SHUT_RDWR)
     except OSError:pass
    raise
  time.sleep(.2);r=self.stats()
  if r['tcp_bad_chunks'] or r['tcp_rx_bytes']!=values[0]['bytes']:raise RuntimeError(f'Bidir receiver check failed: {r}')
  return dict(protocol='tcp_bidir',seconds=seconds,directions=values,board_stats=r)
 def bandwidth(self,out,seconds=30,repeats=3,soak=600,quick=False):
  import csv
  results=[];run=5000
  def record(value,stage):
   value['stage']=stage;results.append(value);(out/'bandwidth.json').write_text(json.dumps(results,indent=2)+'\n')
   if 'receiver_mbps' in value:print(f"MEASURE {stage} {value.get('direction','')} {value['receiver_mbps']:.3f} Mbps loss={value.get('loss_fraction',0):.6f}",flush=True)
   else:print(f'MEASURE {stage} completed',flush=True)
  stable={}
  for direction in ['pc_to_som','som_to_pc']:
   candidates=[]
   for mbps in [1,10,50,100,250,500,900]:
    run+=1;r=self.udp_trial(direction,1472,mbps*1000000,3,run);record(r,'udp_ramp')
    if r['loss_fraction']<=.001 and not r['source_errors']:candidates.append(r)
   if not candidates:raise RuntimeError(f'No stable UDP rate found: {direction}')
   best=max(candidates,key=lambda r:r['receiver_mbps']);stable[direction]=int(min(best['requested_mbps'],best['offered_mbps'])*1e6*.8)
   stable[direction]=max(100000,stable[direction])
   for size in [64,256,512,1024,1472]:
    run+=1;record(self.udp_trial(direction,size,min(stable[direction],10000000),3,run),'udp_sizes')
  for direction in ['pc_to_som','som_to_pc']:
   for repetition in range(1 if quick else repeats):
    run+=1;record(self.udp_trial(direction,1472,stable[direction],seconds,run),'udp_repeat')
    record(self.tcp_trial(direction,seconds),'tcp_repeat')
   if not quick:record(self.tcp_trial(direction,seconds,4),'tcp_four_streams')
  record(self.tcp_bidir(seconds),'tcp_bidir')
  if soak:record(self.tcp_bidir(soak),'tcp_soak')
  with (out/'bandwidth.csv').open('w',newline='') as f:
   fields=['stage','protocol','direction','payload_bytes','seconds','streams','requested_mbps','offered_mbps','receiver_mbps','loss_fraction','bad_payloads','duplicates','reordered','source_errors']
   writer=csv.DictWriter(f,fields,extrasaction='ignore');writer.writeheader();writer.writerows(results)
  return results
