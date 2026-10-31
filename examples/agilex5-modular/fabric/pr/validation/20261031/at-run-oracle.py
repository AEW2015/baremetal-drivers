"""Strict evidence checks for the simulated loader; never qualify physical PR."""
def assess(name,uart,transactions,code,backend,body):
 negative=name!='swap'
 if code or not backend or not transactions:return False
 if uart.count('PR_LAB_BEGIN simulation_loader=1')!=1 or uart.count('PR_LAB_COMPLETE status=0')!=1:return False
 guest=uart.split('PR_LAB_BEGIN simulation_loader=1',1)[1]
 if 'FAIL ' in guest or 'status=1' in guest or 'SIMICS_RTL_ADAPTER_ERROR' in body:return False
 if 'SIMICS_RTL_DDR_BOOTSTRAP_COMPLETE' not in body or 'DDR stage skipped' in uart:return False
 if len(transactions)!=backend.get('transactions'):return False
 if any(not (t.get('initiator') or '').endswith('.core[0]') for t in transactions):return False
 loads=[t.get('write_value') for t in transactions if t.get('op')=='write' and t.get('offset')==0x80]
 if loads!=([2] if negative else [2,1]):return False
 if not all(guest.count('PASS '+m)==1 for m in ('INITIAL_ADD_ID','INITIAL_ADD_VECTORS')):return False
 markers=('NEGATIVE_LOAD_REJECTED','NEGATIVE_REMAINS_ISOLATED') if negative else ('TWO_RUNTIME_SWAPS','XOR_VECTORS','RETURN_ADD_VECTORS')
 if not all(guest.count('PASS '+m)==1 for m in markers):return False
 if not negative and not all(guest.count('PASS '+m)==2 for m in ('SWAP_RESET_AND_ID','STATIC_SCRATCH_CONTINUITY','STATIC_HEARTBEAT_PROGRESS','DDR_GUARD_256_WORDS','ISOLATED_READ_RESPONSE')):return False
 return True
