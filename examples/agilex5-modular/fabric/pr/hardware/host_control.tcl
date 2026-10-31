# Variables supplied by the bounded host coordinator: pr_stage, pr_expected.
# A success sentinel, not System Console's exit code, qualifies each operation.
proc pr_host_control {} {
    global pr_stage pr_expected
    if {$pr_stage ni {begin done error}} {error "invalid host stage"}
    if {$pr_expected ni {0x41444431 0x584f5231}} {error "invalid persona"}
    set matches {}
    foreach path [get_service_paths master] {
        if {[string first {u_pr_jtag} $path]>=0} {lappend matches $path}
    }
    if {[llength $matches]!=1} {error "need exactly one u_pr_jtag master; discovered: [get_service_paths master]"}
    set master [lindex $matches 0]
    puts "PR_HOST_MASTER $master"
    open_service master $master
    set rc [catch {
        set signature [lindex [master_read_32 $master 0x00020058 1] 0]
        set status [lindex [master_read_32 $master 0x00020040 1] 0]
        set scratch [lindex [master_read_32 $master 0x00020048 1] 0]
        set expected [lindex [master_read_32 $master 0x0002004c 1] 0]
        set heartbeat [lindex [master_read_32 $master 0x00020044 1] 0]
        if {$signature!=0x50525331 || $scratch!=0xcafe1234 || $expected!=$pr_expected} {error "static identity/scratch/expected-persona mismatch"}
        if {($status & 0xf01)!=0x201} {error "region is not isolated in FROZEN state"}
        if {$pr_stage eq {begin}} {
            if {$status & 8} {error "loader already busy"}
            set command 1
        } elseif {$pr_stage eq {done}} {
            if {($status & 9)!=9} {error "loader BUSY phase was not observed"}
            set command 2
        } else {set command 4}
        master_write_32 $master 0x00020060 [list $command]
        set actual [lindex [master_read_32 $master 0x00020060 1] 0]
        if {$actual!=$command} {error "host status write/readback mismatch"}
        puts [format {PR_HOST_READ signature=0x%08x status=0x%08x scratch=0x%08x expected=0x%08x heartbeat=0x%08x} $signature $status $scratch $expected $heartbeat]
    } detail]
    close_service master $master
    if {$rc} {error $detail}
    puts "PR_HOST_STAGE_RESULT stage=$pr_stage PASS"
}
if {[catch {pr_host_control} pr_error_text]} {puts stderr "PR_HOST_STAGE_ERROR $pr_error_text"}
