"""Check actual wrapped FCS returns/data or strictly read-only ECC status."""
import re
NAMES=['fcs','ecc-readonly']
PROFILES={'fcs':'resident-BL31-NS-EL2','ecc-readonly':'standalone-EL3'}
def assess(name,body,code):
 if name not in NAMES or code!=0:return 'fail'
 text=body.replace('\r','');lines=text.splitlines();el=2 if name=='fcs' else 3
 if lines.count(f'SERVICE_BEGIN name={name} EL={el}')!=1:return 'fail'
 if lines.count('SERVICE_COMPLETE status=0')!=1 or any(line.startswith('FAIL ') or line.startswith('BLOCKED ') for line in lines) or '[FCS][FAIL]' in text:return 'fail'
 if name=='ecc-readonly':
  raw=re.findall(r'^SERVICE_ECC_READONLY SERR=0x([0-9a-fA-F]+) DERR=0x([0-9a-fA-F]+) RAW_SERR=0x([0-9a-fA-F]+) RAW_DERR=0x([0-9a-fA-F]+)$',text,re.M)
  if len(raw)!=1:return 'fail'
  s,d,rs,rd=map(lambda v:int(v,16),raw[0])
  return 'partial' if s==rs and d==rd and not(s==0xffffffff and d==0xffffffff) and 'PASS ECC_READONLY_API_RAW_AGREE' in lines and 'SERVICE_PARTIAL ECC_STATUS_ONLY_NO_INIT_CLEAR_OR_INJECTION' in lines else 'fail'
 required=['PASS FCS_REAL_INIT','PASS FCS_REAL_CHIP_ID_DATA','PASS FCS_REAL_MODULAR_JTAG_ID','PASS FCS_REAL_DEINIT','PASS FCS_REAL_CALL_SEQUENCE']
 if not all(lines.count(line)==1 for line in required):return 'fail'
 chip=re.findall(r'^SERVICE_FCS_API chip rc=0 hi=0x([0-9a-fA-F]+) lo=0x([0-9a-fA-F]+)$',text,re.M)
 if len(chip)!=1:return 'fail'
 hi,lo=(int(v,16) for v in chip[0])
 if not(hi or lo) or (hi==0xffffffff and lo==0xffffffff):return 'fail'
 jtag=re.findall(r'^SERVICE_FCS_API jtag rc=0 value=0x([0-9a-fA-F]+)$',text,re.M)
 if len(jtag)!=1 or int(jtag[0],16)!=0x0364f0dd or lines.count('SERVICE_FCS_API init rc=0')!=1 or lines.count('SERVICE_FCS_API deinit rc=0')!=1:return 'fail'
 summary=re.findall(r'^SERVICE_FCS_SUMMARY init=(\d+) chip=(\d+) jtag=(\d+) open=(\d+) rng=(\d+) close=(\d+) deinit=(\d+) provision=(\d+) denied=(\d+)$',text,re.M)
 if len(summary)!=1:return 'fail'
 seq=tuple(map(int,summary[0]))
 if seq==(1,1,1,1,0,0,1,1,1):
  provision=re.findall(r'^SERVICE_FCS_API get_provision rc=(-?\d+) bytes=(\d+) \(read-only\)$',text,re.M)
  if len(provision)!=1:return 'fail'
  rc,size=map(int,provision[0])
  ok=(rc==-5 or (rc==0 and 12<=size<=1024))
  return 'partial' if ok and 'SERVICE_FCS_API open rc=-5' in lines and 'SERVICE_PARTIAL FCS_SDM_SECURITY_DENIED_0x85' in lines and 'PASS FCS_READONLY_PROVISION_RESULT' in lines and re.search(r'^=== FCS demo: 4/4 step\(s\) PASS \(1 expected security skip\(s\)\) ===$',text,re.M) else 'fail'
 if seq!=(1,1,1,1,1,1,1,0,0):return 'fail'
 if not all(lines.count(x)==1 for x in ['SERVICE_FCS_API open rc=0','PASS FCS_REAL_SESSION_UUID','PASS FCS_REAL_RNG_DATA','PASS FCS_REAL_SESSION_CLOSED','SERVICE_FCS_API close rc=0 uuid_matches=1']):return 'fail'
 rng_call=re.findall(r'^SERVICE_FCS_API rng rc=0 context=0x([0-9a-fA-F]+) uuid_matches=1 size=16$',text,re.M)
 if len(rng_call)!=1 or int(rng_call[0],16)!=0xc0ffee01:return 'fail'
 for name in ('uuid','rng'):
  values=re.findall(r'^SERVICE_FCS_BYTES '+name+r' count=16 hex=([0-9a-fA-F]{32})$',text,re.M)
  if len(values)!=1:return 'fail'
  data=bytes.fromhex(values[0])
  if data in (bytes(16),b'\xff'*16):return 'fail'
  if name=='uuid':
   payload=bytearray(data);payload[6]&=15;payload[8]&=63
   if not any(payload) or data[6]&0xf0!=0x40 or data[8]&0xc0!=0x80:return 'fail'
 return 'pass' if re.search(r'^=== FCS demo: 7/7 step\(s\) PASS ===$',text,re.M) else 'fail'
