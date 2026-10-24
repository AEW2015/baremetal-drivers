set pagination off
set confirm off
set architecture aarch64
target remote 127.0.0.1:37053
hbreak copy_complete
continue
watch destination[37]
continue
bt
python
import gdb
assert gdb.newest_frame().name() == 'inject_corruption'
assert int(gdb.parse_and_eval('destination[37]')) == 0x1234567800000024
assert int(gdb.parse_and_eval('source[37]')) == 0x1234567800000025
print('GDB PASS WATCHPOINT_CAUGHT_BAD_WRITE')
end
delete breakpoints
hbreak lab_done
continue
python
assert int(gdb.parse_and_eval('status')) == 0
assert int(gdb.parse_and_eval('mismatch_count')) == 1
assert int(gdb.parse_and_eval('first_bad_index')) == 37
src = gdb.parse_and_eval('source')
dst = gdb.parse_and_eval('destination')
assert all(int(src[i]) == int(dst[i]) for i in range(512))
print('GDB PASS ALL_512_WORDS_REPAIRED')
end
detach
quit
