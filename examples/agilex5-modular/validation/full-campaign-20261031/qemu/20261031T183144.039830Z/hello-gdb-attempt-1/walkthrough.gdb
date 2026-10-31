target remote /tmp/agx5-hello-cj118ozw/gdb
break main
break qemu_done
continue
step
continue
print status
print failures
print vector_result
print source[511] == destination[511]
if status != 0 || failures != 0 || vector_result[0] != 11 || vector_result[1] != 22 || vector_result[2] != 33 || vector_result[3] != 44 || source[511] != destination[511]
quit 2
end
printf "PASS HELLO_GDB_CHECKED_RESULTS
"
continue
