#include "../../core/common.h"
#include "pr_driver.h"
#ifdef PR_HPS_SDM
#include "sdm_loader.h"
#endif
#ifndef EXPECT_FAILURE
#define EXPECT_FAILURE 0
#endif
static volatile unsigned failures;
static void check(int yes,const char *s){text(yes?"PASS ":"FAIL ");text(s);text("\n");if(!yes)failures++;}
static int vectors(struct lab_device *d,uint32_t persona){
 const uint32_t a[]={7,0xffffffff,0x12345678,0},b[]={5,1,0x87654321,0xffffffff};
 for(unsigned i=0;i<4;i++){uint32_t result=0;uint32_t expected=persona==LAB_ADD?a[i]+b[i]:a[i]^b[i];if(lab_execute(d,a[i],b[i],&result,1000)||result!=expected)return 0;}
 return 1;
}
void example_main(void){
 #ifdef PR_HPS_SDM
 text("PR_LAB_BEGIN hps_sdm_loader=1\n");
#elif defined(PR_PHYSICAL)
 text("PR_LAB_BEGIN jtag_loader=1\n");
#else
 text("PR_LAB_BEGIN simulation_loader=1\n");
#endif
 struct lab_device d=lab_mmio(0x20020000);uint32_t id=0;
 check(!lab_probe(&d,&id)&&id==LAB_ADD,"INITIAL_ADD_ID");check(vectors(&d,LAB_ADD),"INITIAL_ADD_VECTORS");
 d.write(d.context,PR_SCRATCH,0xcafe1234);uint32_t heartbeat=d.read(d.context,PR_HEARTBEAT);
 volatile uint32_t *guard=(volatile uint32_t *)0x85000000;
 for(unsigned i=0;i<256;i++)guard[i]=0xa5a50000^i;
 for(unsigned swap=0;swap<2 && !failures;swap++){
  uint32_t persona=swap?LAB_ADD:LAB_XOR;
  if(pr_prepare(&d,persona,1000)){check(0,"FREEZE_AND_DRAIN");break;}
  check(d.read(d.context,LAB_ID)==0xdec0f001,"ISOLATED_READ_RESPONSE");
  // The physical loader must replace this explicit simulation-only operation.
  int rc;
#ifdef PR_HPS_SDM
  const volatile struct pr_images *images=(const volatile struct pr_images *)PR_DESCRIPTOR_ADDRESS;
  const volatile struct pr_image *entry=swap?&images->add:&images->xor;
  /* Scalar volatile reads: ADD's descriptor starts at +4, not 8-byte aligned.
   * MMU-off Device accesses must not become a 64-bit structure copy.
   */
  struct pr_image image={entry->address,entry->bytes,entry->crc32};
  if(images->magic!=0x50524431U){check(0,"PR_IMAGE_DESCRIPTOR");break;}
  if(!swap) {
   struct pr_image corrupt=image;corrupt.crc32^=1;
   check(pr_sdm_load(&corrupt)==-12,"PR_BAD_CRC_REJECTED");
   check(d.read(d.context,PR_CONTROL)&1,"PR_BAD_CRC_REMAINS_ISOLATED");
   if(failures)break;
  }
  d.write(d.context,0x60,1); /* Loader BUSY; partition stays isolated. */
  rc=pr_sdm_load(&image);
  if(rc){value("PR_SDM_LOADER_ERROR=",(uint64_t)(int64_t)rc);d.write(d.context,0x60,4);check(0,"PR_HPS_LOAD");break;}
  d.write(d.context,0x60,2); /* DONE only after the SDM's positive completion. */
  rc=pr_finish(&d,persona,1000000);
#elif defined(PR_PHYSICAL)
  uint64_t timer_hz=SYS(cntfrq_el0);
  value("PR_TIMER_HZ=",timer_hz);
  value("PR_HOST_LOAD_REQUEST=",persona);
  // The diagnostic boot may leave CNTFRQ_EL0 zero. The host coordinator
  // enforces the wall-clock bound; keep the isolated guest waiting in that case.
  uint64_t deadline=SYS(cntpct_el0)+600*timer_hz;
  do {rc=pr_finish(&d,persona,1000);}while(rc==-7 && (!timer_hz || SYS(cntpct_el0)<deadline));
#else
  d.write(d.context,PR_SIM_LOAD,swap?1:2);
  rc=pr_finish(&d,persona,1000);
#endif
  if(EXPECT_FAILURE){check(rc<0,"NEGATIVE_LOAD_REJECTED");check(d.read(d.context,PR_CONTROL)&1,"NEGATIVE_REMAINS_ISOLATED");break;}
  value("PR_PERSONA=",persona);if(rc)value("PR_DRIVER_ERROR=",(uint64_t)(int64_t)rc);check(rc==0,"SWAP_RESET_AND_ID");if(rc)break;
  check(vectors(&d,persona),swap?"RETURN_ADD_VECTORS":"XOR_VECTORS");
  check(d.read(d.context,PR_SCRATCH)==0xcafe1234,"STATIC_SCRATCH_CONTINUITY");
  uint32_t next_heartbeat=d.read(d.context,PR_HEARTBEAT);
  check((uint32_t)(next_heartbeat-heartbeat)!=0,"STATIC_HEARTBEAT_PROGRESS");heartbeat=next_heartbeat;
  unsigned mismatches=0;for(unsigned i=0;i<256;i++)if(guard[i]!=(0xa5a50000^i))mismatches++;
  check(!mismatches,"DDR_GUARD_256_WORDS");
 }
 if(!EXPECT_FAILURE)check(d.read(d.context,PR_SWAPS)==2,"TWO_RUNTIME_SWAPS");
 text(failures?"PR_LAB_COMPLETE status=1\n":"PR_LAB_COMPLETE status=0\n");
 for(;;)__asm__ volatile("wfi");
}
