/* Real FCS HAL/API + real mailbox queue, only SiP firmware responses modeled.
 * No dangling-stack write is needed to detect the old bug: direct HAL calls
 * must return actual delayed data with their jobs completed, not zero/queued.
 */
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <sys/mman.h>
#include "socfpga_mbox_client.h"
#include "socfpga_fcs.h"
#include "socfpga_fcs_ll.h"
#include "fcs_api.h"
#include "socfpga_sip_handler.h"
#define TRANS 0x420000c9U
#define RESPONSE 0x420000c8U
struct job {bool live;uint64_t fid,args[10];unsigned ready,serial;};
static struct job jobs[256];
static unsigned now,serial,delay=3,forced_error,pending,completed,polls;
static bool deny_open,deny_uuid_rng;
static uint64_t last_fid;
static uint32_t low(unsigned n){return 0xc1556500U+n;}
static uint32_t high(unsigned n){return 0x42199600U+n;}
static unsigned live_count(void){unsigned n=0;for(unsigned i=0;i<256;i++)n+=jobs[i].live;return n;}
void cache_force_invalidate(void *p,size_t n){(void)p;(void)n;}
void cache_force_write_back(void *p,size_t n){(void)p;(void)n;}
int smc_call(uint64_t fid,uint64_t *values){
 if(fid==0xc200000eU)return 0; /* volatile HPS-stage notification */
 if(fid==TRANS){memset(values,0,SMC_CALL_REG_COUNT*8);now++;polls++;for(unsigned i=0;i<256;i++)if(jobs[i].live&&jobs[i].ready<=now)values[i/64]|=UINT64_C(1)<<(i%64);return 0;}
 if(fid==RESPONSE){unsigned id=(unsigned)values[0];assert(id<256&&jobs[id].live&&jobs[id].ready<=now);struct job *j=&jobs[id];memset(values,0,SMC_CALL_REG_COUNT*8);values[0]=forced_error;
  if(j->fid==FCS_GET_CHIP_ID){values[1]=low(j->serial);values[2]=high(j->serial);}
  if(j->fid==FCS_GET_IDCODE)values[1]=0x0364f0dd;
  if(j->fid==FCS_OPEN_SESSION){values[0]=deny_open?0x85:0;values[1]=7;}
  if(j->fid==FCS_RANDOM_NUMBER){values[0]=deny_uuid_rng&&j->args[1]==1?0x85:forced_error;uint32_t *out=(void*)(uintptr_t)j->args[2];unsigned char *data=(void*)&out[FCS_RESP_DATA];for(unsigned i=0;i<j->args[3];i++)data[i]=(unsigned char)(j->serial+i+1);values[1]=j->args[3];}
  if(j->fid==FCS_GET_PROVISION_DATA){uint32_t *out=(void*)(uintptr_t)j->args[0];out[0]=1;out[1]=2;out[2]=3;values[1]=12;}
  j->live=false;pending--;completed++;last_fid=j->fid;return 0;
 }
 unsigned id=(unsigned)values[0];assert(id<256&&!jobs[id].live);struct job *j=&jobs[id];j->live=true;j->fid=fid;j->serial=++serial;j->ready=now+delay;memcpy(j->args,&values[1],sizeof(j->args));pending++;return 0;
}
int main(void){
 void *memory=mmap((void*)0x83000000,0x900000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);assert(memory==(void*)0x83000000);
 assert(fcs_api_init()==0);
 uint32_t lo=0,hi=0;unsigned before=serial;
 assert(run_fcs_get_chip_id(&lo,&hi)==0);assert(lo==low(before+1)&&hi==high(before+1));assert(!live_count());assert(polls>=3);puts("PASS delayed CHIP_ID copied before HAL returns");
 uint32_t id=0;assert(run_fcs_get_jtag_idcode(&id)==0&&id==0x0364f0dd);assert(!live_count());puts("PASS delayed JTAG_ID copied before HAL returns");
 /* Timeout must detach the local response buffer, not just stop polling. */
 delay=100000;lo=hi=0;assert(run_fcs_get_chip_id(&lo,&hi)==-110);assert(live_count()==1);unsigned old_id=0;while(!jobs[old_id].live)old_id++;unsigned old_serial=jobs[old_id].serial;
 assert(fcs_api_deinit()==0);assert(fcs_api_init()==0);assert(live_count()==1);
 jobs[old_id].ready=now+1;delay=6;before=serial;lo=hi=0;
 assert(run_fcs_get_chip_id(&lo,&hi)==0);assert(lo==low(before+1)&&hi==high(before+1)&&lo!=low(old_serial));assert(!live_count());puts("PASS timeout then late old reply cannot overwrite/reuse a returned local buffer or satisfy the next request");
 /* Explicit detach keeps an owned canary unchanged on a late response. */
 sdm_client_handle client=mbox_client_acquire();uint64_t canary[3]={0x1111,0x2222,0x3333};delay=3;assert(sip_svc_send(client,FCS_GET_CHIP_ID,NULL,0,canary,sizeof(canary))==0);assert(mbox_detach_response_buffer(client,canary)==1);
 for(unsigned i=0;i<4;i++)(void)mbox_poll_once();assert(canary[0]==0x1111&&canary[1]==0x2222&&canary[2]==0x3333);assert(!live_count());mbox_client_release();puts("PASS detached late response leaves owned canary untouched");
 delay=3;forced_error=0x85;lo=0xabc;hi=0xdef;assert(run_fcs_get_chip_id(&lo,&hi)==0x85&&lo==0xabc&&hi==0xdef);assert(!live_count());forced_error=0;puts("PASS actual SDM error propagated instead of false zero-status success");
 char uuid[FCS_UUID_SIZE]={0},rng[16]={0};assert(run_fcs_open_service_session(uuid)==0);assert(!live_count());assert(((unsigned char)uuid[6]&0xf0)==0x40);assert(((unsigned char)uuid[8]&0xc0)==0x80);
 assert(run_fcs_random_number_ext(rng,uuid,0xc0ffee01,16)==0&&rng[0]!=0);assert(!live_count());
 forced_error=9;assert(run_fcs_random_number_ext(rng,uuid,0xc0ffee01,16)==9);forced_error=0;
 assert(run_fcs_close_service_session(uuid)==0);assert(!live_count());puts("PASS delayed session UUID/RNG/close lifecycle and RNG error status");
 deny_open=true;memset(uuid,0,sizeof(uuid));assert(run_fcs_open_service_session(uuid)==0x85);assert(!live_count());deny_open=false;puts("PASS actual security denial preserved");
 deny_uuid_rng=true;assert(run_fcs_open_service_session(uuid)==0x85);assert(last_fid==FCS_CLOSE_SESSION&&!live_count());deny_uuid_rng=false;puts("PASS UUID RNG failure closes the newly opened remote session and propagates error");
 char *provision=(void*)0x83800000;uint32_t bytes=1024;assert(run_fcs_service_get_provision_data(provision,&bytes)==0&&bytes==12&&((uint32_t*)provision)[2]==3);assert(!live_count());
 lo=hi=0;assert(fcs_api_get_chip_id(&lo,&hi)==0&&lo&&hi);assert(!live_count());assert(fcs_api_deinit()==0);assert(!pending&&completed>10);puts("PASS API drain sees no expired HAL response mappings");
 assert(munmap(memory,0x900000)==0);puts("FCS_DELAYED_TRANSPORT_COMPLETE");return 0;
}
