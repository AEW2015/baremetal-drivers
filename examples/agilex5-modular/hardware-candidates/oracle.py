"""Strict host oracle for isolated physical-board candidates, no board access."""
import re
NAMES=['hello','ccu-readonly','clkmgr-readonly','dma','gic','mmu','smmu','spi','timer']
SCOPES={
 'hello':'Unchanged current hello CLI command under board DDR startup',
 'ccu-readonly':'Current CCU ID/error APIs only; no original all-DMI cache-flush test',
 'clkmgr-readonly':'Current clock getter APIs only; no initialization/divisor writes or physical frequency measurement',
 'dma':'Unchanged sync256/async1024 demo plus4096-byte current API copy and full readback; polling fallback can invoke callback, no hardware DMA IRQ proof',
 'gic':'Masked/enabled Group0 SGI ISR demo with board GIC-600 power preflight, Group1 CPU interfaces disabled/read back, and EL3 IRQ/FIQ vector shim',
 'mmu':'Unchanged MMU EL3 status command only; no translation exercise',
 'smmu':'Unchanged SMMU enable-status command only; no DMA translation qualification',
 'spi':'SPI32-byte and current API256-byte internal loopbacks; original status phase is partial when API has auto-closed, no external peer',
 'timer':'Unchanged timer polling command, advancing samples and stopped state; no timing calibration',
}
def assess(name,body,code):
 if name not in NAMES or code!=0:return 'fail'
 text=body.replace('\r','')
 marker='CANDIDATE_BEGIN name='+name
 # UART can contain an unfinished DDR Hello line immediately before entry.
 # Exactly one fresh candidate marker is mandatory, including across names.
 if text.count('CANDIDATE_BEGIN name=')!=1 or text.count(marker)!=1:return 'fail'
 text=text[text.index(marker):]
 # These exact upstream logging prefixes omit their trailing newline.
 # Remove only known prefixes; retain every result/value/failure check.
 if name=='dma':text=text.replace('Starting the DMA transfer on channel 0','')
 if name=='gic':text=re.sub(r'(?m)^Initializing GIC environment \.{2,}[ \t]+(?=GIC_GROUP1_CPU_CONTROL=)','',text)
 lines=text.splitlines()
 if lines.count('CANDIDATE_BEGIN name='+name)!=1 or lines.count('CANDIDATE_COMPLETE status=0')!=1:return 'fail'
 if 'PASS STANDALONE_EL3_MMU_DCACHE_OFF' not in lines:return 'fail'
 if re.search(r'^FAIL |\[FAIL\]|\[MISMATCH\]|SELF-TEST FAILED|timed out|base is not defined|EXCEPTION|FAIL \(',text,re.M|re.I):return 'fail'
 if name=='hello':ok=lines.count('Hello, Baremetal World!')==1
 elif name=='ccu-readonly':
  match=re.search(r'^CCU_READONLY ID=0x([0-9a-fA-F]+) ERROR=0x([0-9a-fA-F]+) rc_id=0 rc_error=0$',text,re.M)
  ok=bool(match and int(match[1],16) not in (0,0xffffffff) and 'PASS CCU_READONLY_API_RAW_AGREE' in lines)
 elif name=='clkmgr-readonly':
  rates=re.findall(r'^CLK_READONLY block=(\d+) rc=(-?\d+) frequency_hz=(\d+)$',text,re.M)
  ok=(len(rates)==8 and {int(r[0]) for r in rates}=={0,3,4,5,6,7,8,9} and all(int(rc)==0 and int(hz)>0 for _,rc,hz in rates)
      and 'PASS CLK_READONLY_ALL_RATES_NONZERO' in lines and 'PASS CLK_READONLY_REGISTER_UNCHANGED' in lines)
 elif name=='dma':
  required=['  [PASS] dma_init','  [PASS] dma_memcpy (sync)','  [PASS] Sync data verification',
   '  [PASS] dma_memcpy_async (start)','  [PASS] dma_wait (async timeout = 2000 ms)','  Callback fired : yes',
   '  [PASS] Async data verification (1024 bytes matched)','PASS DMA_STRICT_INIT','DMA_STRICT_COPY rc=0',
   'DMA_STRICT_READBACK bytes=4096 mismatches=0','PASS DMA_STRICT_4096_READBACK','PASS DMA_STRICT_CHANNEL_IDLE']
  fill=re.findall(r'^  All 256 bytes match 0x([0-9a-fA-F]+)$',text,re.M)
  ok=(all(lines.count(x)==1 for x in required) and len(fill)==1 and int(fill[0],16)==0xa5)
 elif name=='gic':
  hit=re.search(r'PASS \(IRQ=(\d+), count=(\d+)\)',text)
  group1=re.findall(r'^GIC_GROUP1_CPU_CONTROL=0x([0-9a-fA-F]+)$',text,re.M)
  ok=('PASS GIC_REDISTRIBUTOR_POWER_READY' in lines and lines.count('PASS GIC_GROUP1_CPU_DISABLED')==1
      and len(group1)==1 and int(group1[0],16)&3==0
      and 'RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED' in lines
      and hit is not None and int(hit[1])==1 and int(hit[2])>=1)
 elif name=='mmu':ok='MMU EL3: disabled' in lines and 'PASS MMU_EL3_STATUS_DISABLED' in lines
 elif name=='smmu':ok=bool(re.search(r'^SMMU: (enabled|disabled)$',text,re.M)) and 'PASS SMMU_STATUS_API_RAW_AGREE' in lines
 elif name=='spi':
  version=re.search(r'^SPI0 version: 0x([0-9a-fA-F]+)$',text,re.M)
  ok=bool(version and int(version[1],16) not in (0,0xffffffff) and 'SPI0 loopback PASS (32 bytes, CS1)' in lines and 'SPI_API_256 rc=0' in lines and 'PASS SPI_API_256_LOOPBACK' in lines)
  if not ok:return 'fail'
  if 'SPI API is not open. Use spi_selftest for a self-contained test.' in lines:return 'partial'
  status=re.findall(r'^SPI0 CS1 speed=(\d+)Hz mode=(\d+)$',text,re.M)
  ok=len(status)==1 and int(status[0][0])>0 and int(status[0][1])==0
 elif name=='timer':
  first=re.search(r'OK \((\d+) us -> (\d+) us\)',text)
  samples=re.findall(r'Sample (\d) of 5[ \t]+\.{2,}[ \t]+(?:clk_hz now = \d+\n)?(\d+) us(?:\n|$)',text)
  ok=(first is not None and int(first[1])!=int(first[2]) and len(samples)==5 and {int(i) for i,_ in samples}=={1,2,3,4,5}
      and len({int(value) for _,value in samples})>=2 and 'RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED' in lines)
 return 'pass' if ok else 'fail'
