/* Board service probes: guarded FCS CLI and read-only ECC getter subset. */
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "lib_printf.h"
#include "console_api.h"
#include "example_register.h"
#include "fcs_api.h"
#include "socfpga_fcs.h"
#include "ecc_api.h"
#include "socfpga_sys_mngr_reg_plat.h"
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
static unsigned failures;
static cli_cmd_t commands[8];static unsigned command_count;
static unsigned init_calls,chip_calls,jtag_calls,open_calls,rng_calls,close_calls,deinit_calls,provision_calls,denied;
static unsigned char session_uuid[FCS_UUID_SIZE];
static void emit(char c,void *unused){(void)unused;while(!(REG(0x10c02014)&32U)){}REG(0x10c02000)=(uint8_t)c;}
int __wrap_printf(const char *fmt,...){va_list ap;va_start(ap,fmt);int n=lib_vprintf(emit,0,fmt,ap);va_end(ap);return n;}
int __wrap_puts(const char *s){while(*s)emit(*s++,0);emit('\n',0);return 0;}
int __wrap_putchar(int c){emit((char)c,0);return c;}
int __wrap_cli_register_command(const char *name,cmd_func_t fn){if(command_count>=8)return -1;commands[command_count++]=(cli_cmd_t){name,fn};return 0;}
static void check(int ok,const char *name){printf("%s %s\n",ok?"PASS":"FAIL",name);if(!ok)failures++;}
static void bytes(const char *name,const char *data,unsigned count){printf("SERVICE_FCS_BYTES %s count=%u hex=",name,count);for(unsigned i=0;i<count;i++)printf("%02x",(unsigned char)data[i]);puts("");}
static int nontrivial(const char *data,unsigned count){unsigned nz=0,nf=0;for(unsigned i=0;i<count;i++){nz|=(unsigned char)data[i];nf|=(unsigned char)data[i]^255U;}return nz&&nf;}
static int valid_uuid(const char *data){unsigned nz=0,nf=0;for(unsigned i=0;i<16;i++){unsigned mask=i==6?15U:(i==8?63U:255U);unsigned byte=(unsigned char)data[i]&mask;nz|=byte;nf|=byte^mask;}return nz&&nf&&((unsigned char)data[6]&0xf0U)==0x40U&&((unsigned char)data[8]&0xc0U)==0x80U;}
extern int __real_fcs_api_init(void),__real_fcs_api_deinit(void);
extern int __real_fcs_api_get_chip_id(uint32_t*,uint32_t*),__real_fcs_api_get_jtag_idcode(uint32_t*);
extern int __real_fcs_api_open_session(char*),__real_fcs_api_close_session(char*);
extern int __real_fcs_api_get_random_number(char*,uint32_t,char*,uint32_t);
extern int __real_fcs_api_get_provision_data(char*,uint32_t*);
int __wrap_fcs_api_init(void){int rc=__real_fcs_api_init();init_calls++;printf("\nSERVICE_FCS_API init rc=%d\n",rc);check(rc==0,"FCS_REAL_INIT");return rc;}
int __wrap_fcs_api_deinit(void){int rc=__real_fcs_api_deinit();deinit_calls++;printf("\nSERVICE_FCS_API deinit rc=%d\n",rc);check(rc==0,"FCS_REAL_DEINIT");return rc;}
int __wrap_fcs_api_get_chip_id(uint32_t *lo,uint32_t *hi){int rc=__real_fcs_api_get_chip_id(lo,hi);chip_calls++;printf("\nSERVICE_FCS_API chip rc=%d hi=0x%08x lo=0x%08x\n",rc,*hi,*lo);check(rc==0&&(*hi||*lo)&&!(*hi==0xffffffffU&&*lo==0xffffffffU),"FCS_REAL_CHIP_ID_DATA");return rc;}
int __wrap_fcs_api_get_jtag_idcode(uint32_t *value){int rc=__real_fcs_api_get_jtag_idcode(value);jtag_calls++;printf("\nSERVICE_FCS_API jtag rc=%d value=0x%08x\n",rc,*value);check(rc==0&&*value==0x0364f0ddU,"FCS_REAL_MODULAR_JTAG_ID");return rc;}
int __wrap_fcs_api_open_session(char *uuid){int rc=__real_fcs_api_open_session(uuid);open_calls++;printf("\nSERVICE_FCS_API open rc=%d\n",rc);if(rc==FCS_API_SECURITY_DENIED){denied++;puts("SERVICE_PARTIAL FCS_SDM_SECURITY_DENIED_0x85");}else{bytes("uuid",uuid,FCS_UUID_SIZE);check(rc==0&&valid_uuid(uuid),"FCS_REAL_SESSION_UUID");if(rc==0)memcpy(session_uuid,uuid,FCS_UUID_SIZE);}return rc;}
int __wrap_fcs_api_close_session(char *uuid){int same=memcmp(session_uuid,uuid,FCS_UUID_SIZE)==0;int rc=__real_fcs_api_close_session(uuid);close_calls++;printf("\nSERVICE_FCS_API close rc=%d uuid_matches=%u\n",rc,(unsigned)same);check(rc==0&&same,"FCS_REAL_SESSION_CLOSED");return rc;}
int __wrap_fcs_api_get_random_number(char *uuid,uint32_t context,char *rng,uint32_t size){int same=memcmp(session_uuid,uuid,FCS_UUID_SIZE)==0;if(rng!=NULL&&size==16)memset(rng,0,16);int rc=__real_fcs_api_get_random_number(uuid,context,rng,size);rng_calls++;printf("\nSERVICE_FCS_API rng rc=%d context=0x%08x uuid_matches=%u size=%u\n",rc,context,(unsigned)same,size);if(size<=16)bytes("rng",rng,size);check(rc==0&&same&&context==0xc0ffee01U&&size==16&&nontrivial(rng,size),"FCS_REAL_RNG_DATA");return rc;}
int __wrap_fcs_api_get_provision_data(char *data,uint32_t *size){int rc=__real_fcs_api_get_provision_data(data,size);provision_calls++;printf("\nSERVICE_FCS_API get_provision rc=%d bytes=%u (read-only)\n",rc,*size);check(rc==FCS_API_SECURITY_DENIED||(rc==0&&*size>=12&&*size<=FCS_PROV_DATA_MAX_SIZE),"FCS_READONLY_PROVISION_RESULT");return rc;}
static void dispatch(const char *name){for(unsigned i=0;i<command_count;i++){const char *a=commands[i].name,*b=name;while(*a&&*a==*b){a++;b++;}if(!*a&&!*b){commands[i].func("");return;}}check(0,"SERVICE_COMMAND_REGISTERED");}
__attribute__((noreturn)) static void finish(unsigned status){printf("SERVICE_COMPLETE status=%u\n",status);for(;;)__asm__ volatile("wfi");}
void fault(void){uint64_t el,esr=0,pc=0;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));if(el==12){__asm__ volatile("mrs %0,esr_el3":"=r"(esr));__asm__ volatile("mrs %0,elr_el3":"=r"(pc));}else if(el==8){__asm__ volatile("mrs %0,esr_el2":"=r"(esr));__asm__ volatile("mrs %0,elr_el2":"=r"(pc));}printf("FAIL SERVICE_EXCEPTION EL=%llu ESR=0x%llx PC=0x%llx\n",el>>2,esr,pc);finish(1);}
void main(void){uint64_t el;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));el>>=2;printf("SERVICE_BEGIN name=%s EL=%llu\n",SERVICE_NAME,el);
 if(SERVICE_CASE==0){if(el!=2){puts("BLOCKED SERVICE FCS_REQUIRES_RESIDENT_BL31_NS_EL2");finish(2);}app_register();dispatch("fcs_selftest");printf("SERVICE_FCS_SUMMARY init=%u chip=%u jtag=%u open=%u rng=%u close=%u deinit=%u provision=%u denied=%u\n",init_calls,chip_calls,jtag_calls,open_calls,rng_calls,close_calls,deinit_calls,provision_calls,denied);check(init_calls==1&&chip_calls==1&&jtag_calls==1&&open_calls==1&&deinit_calls==1&&((denied==1&&rng_calls==0&&close_calls==0&&provision_calls==1)||(denied==0&&rng_calls==1&&close_calls==1&&provision_calls==0)),"FCS_REAL_CALL_SEQUENCE");}
 else{if(el!=3){puts("BLOCKED SERVICE ECC_REQUIRES_STANDALONE_EL3");finish(2);}uint32_t serr=ecc_api_get_serr_status(),derr=ecc_api_get_derr_status();uint32_t raw_s=REG(SYS_MNGR_BASE_ADDR+SYS_MNGR_ECC_INTSTATUS_SERR),raw_d=REG(SYS_MNGR_BASE_ADDR+SYS_MNGR_ECC_INTSTATUS_DERR);printf("SERVICE_ECC_READONLY SERR=0x%08x DERR=0x%08x RAW_SERR=0x%08x RAW_DERR=0x%08x\n",serr,derr,raw_s,raw_d);check(serr==raw_s&&derr==raw_d&&!(serr==0xffffffffU&&derr==0xffffffffU),"ECC_READONLY_API_RAW_AGREE");puts("SERVICE_PARTIAL ECC_STATUS_ONLY_NO_INIT_CLEAR_OR_INJECTION");}
 finish(failures?1:0);
}
