    if (intel_mailbox_is_fpga_not_ready()) { ERROR("LOCAL FABRIC: FPGA not ready\n"); panic(); }
    if (socfpga_bridges_enable(LWHPS2FPGA_MASK)) { ERROR("LOCAL FABRIC: bridge enable failed\n"); panic(); }
    NOTICE("LOCAL FABRIC: LWH2F enabled\n");
