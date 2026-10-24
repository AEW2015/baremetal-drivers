set pagination off
set confirm off
set architecture aarch64
target remote 127.0.0.1:51561
python
import gdb
assert int(gdb.parse_and_eval('initialized')) == 0
load = int(gdb.parse_and_eval('(unsigned long)__data_load'))
assert int.from_bytes(bytes(gdb.selected_inferior().read_memory(load, 8)), 'little') == 0x123456789abcdef0
print('GDB PASS DATA_BEFORE_RELOCATION')
end
hbreak main
continue
python
assert int(gdb.parse_and_eval('initialized')) == 0x123456789abcdef0
begin = int(gdb.parse_and_eval('(unsigned long)__bss_start'))
end = int(gdb.parse_and_eval('(unsigned long)__bss_end'))
assert not any(bytes(gdb.selected_inferior().read_memory(begin, end-begin)))
assert int(gdb.parse_and_eval('$sp')) & 15 == 0
print('GDB PASS STARTUP_MEMORY_AND_STACK')
end
detach
quit
