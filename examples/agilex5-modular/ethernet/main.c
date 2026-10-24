/* NO_SYS lwIP benchmark endpoints; custom protocol, not iperf-compatible.
 * CPU A55.0 only, noncacheable DDR, software protocol checksums. */
#include "platform.h"
#include "lwip/init.h"
#include "lwip/timeouts.h"
#include "lwip/udp.h"
#include "lwip/tcp.h"
#include "lwip/stats.h"
#include "lwip/memp.h"
#include "netif/ethernet.h"
#include <stdio.h>
#include <string.h>
#define MAGIC 0x4e423031u
#define DATA 0x4e424454u
#define SEQUENCES (1u<<25)
static struct netif iface;
static struct udp_pcb *control_pcb,*source_pcb;
static uint8_t seen[SEQUENCES/8];
static uint32_t run_id,high_seq;
static uint64_t rx_packets,rx_bytes,rx_bad,rx_duplicates,rx_reordered;
static uint64_t tcp_rx_bytes,tcp_tx_acked,tcp_bad_chunks;
static uint8_t pattern[32768+256];
static int stop_requested;
static struct {int active;ip_addr_t peer;uint16_t port,len;uint32_t id,seq;uint64_t end,next,period,sent,errors;} sender;
struct connection {struct tcp_pcb*pcb;int source;uint64_t queued,received;};
static struct connection connections[8];
static void reply(struct udp_pcb*pcb,const ip_addr_t*addr,u16_t port,const char*s){
 struct pbuf*p=pbuf_alloc(PBUF_TRANSPORT,strlen(s),PBUF_RAM);
 if(p){pbuf_take(p,s,strlen(s));udp_sendto(pcb,p,addr,port);pbuf_free(p);}
}
static void stats(char*out,size_t n){
 snprintf(out,n,"{\"run\":%lu,\"ticks\":%llu,\"counter_hz\":%llu,\"rx_packets\":%llu,\"rx_bytes\":%llu,\"bad\":%llu,\"duplicates\":%llu,\"reordered\":%llu,\"tx_packets\":%llu,\"tx_errors\":%llu,\"tx_active\":%d,\"tcp_rx_bytes\":%llu,\"tcp_tx_acked\":%llu,\"tcp_bad_chunks\":%llu,\"mac_tx\":%llu,\"mac_rx\":%llu,\"mac_tx_full\":%llu,\"mac_rx_errors\":%llu,\"dma_status\":%lu,\"pbuf_used\":%lu,\"pbuf_max\":%lu,\"pbuf_errors\":%lu,\"tcp_drops\":%lu,\"tcp_checksum_errors\":%lu}",
 (unsigned long)run_id,(unsigned long long)ticks(),(unsigned long long)COUNTER_HZ,
 (unsigned long long)rx_packets,(unsigned long long)rx_bytes,(unsigned long long)rx_bad,(unsigned long long)rx_duplicates,(unsigned long long)rx_reordered,
 (unsigned long long)sender.sent,(unsigned long long)sender.errors,sender.active,(unsigned long long)tcp_rx_bytes,(unsigned long long)tcp_tx_acked,(unsigned long long)tcp_bad_chunks,
 (unsigned long long)mac_tx_packets,(unsigned long long)mac_rx_packets,(unsigned long long)mac_tx_full,(unsigned long long)mac_rx_errors,(unsigned long)R(0x10833160),(unsigned long)lwip_stats.memp[MEMP_PBUF_POOL]->used,(unsigned long)lwip_stats.memp[MEMP_PBUF_POOL]->max,(unsigned long)lwip_stats.memp[MEMP_PBUF_POOL]->err,(unsigned long)lwip_stats.tcp.drop,(unsigned long)lwip_stats.tcp.chkerr);
}
static void command(void*arg,struct udp_pcb*pcb,struct pbuf*p,const ip_addr_t*addr,u16_t port){
 (void)arg;uint32_t v[7];char out[768];
 if(p->tot_len!=sizeof(v)){pbuf_free(p);return;}
 pbuf_copy_partial(p,v,sizeof(v),0);pbuf_free(p);
 for(unsigned i=0;i<7;i++)v[i]=lwip_ntohl(v[i]);
 if(v[0]!=MAGIC)return;
 switch(v[1]){
 case 1:
  run_id=v[2];high_seq=0;rx_packets=rx_bytes=rx_bad=rx_duplicates=rx_reordered=0;
  tcp_rx_bytes=tcp_tx_acked=tcp_bad_chunks=0;memset(seen,0,sizeof(seen));break;
 case 2:break;
 case 3:
  if(v[3]<16||v[3]>1472||v[4]>1000000000u||!v[5]||v[5]>60000||v[6]<1024||v[6]>65535){reply(pcb,addr,port,"{\"error\":\"invalid parameters\"}");return;}
  sender.active=0;sender.peer=*addr;sender.port=v[6];sender.id=v[2];sender.len=v[3];sender.seq=0;
  sender.sent=sender.errors=0;sender.next=ticks();sender.end=sender.next+(COUNTER_HZ/1000)*v[5];
  sender.period=v[4]?COUNTER_HZ*sender.len*8/v[4]:0;sender.active=1;break;
 case 4:sender.active=0;break;
 case 5:sender.active=0;stop_requested=1;break;
 default:reply(pcb,addr,port,"{\"error\":\"unknown command\"}");return;
 }
 stats(out,sizeof(out));reply(pcb,addr,port,out);
}
static void echo(void*arg,struct udp_pcb*pcb,struct pbuf*p,const ip_addr_t*addr,u16_t port){
 (void)arg;udp_sendto(pcb,p,addr,port);pbuf_free(p);
}
static void sink(void*arg,struct udp_pcb*pcb,struct pbuf*p,const ip_addr_t*addr,u16_t port){
 (void)arg;(void)pcb;(void)addr;(void)port;uint32_t h[4];uint8_t bytes[1472];
 unsigned len=p->tot_len;
 if(len<16||len>sizeof(bytes)){rx_bad++;pbuf_free(p);return;}
 pbuf_copy_partial(p,bytes,len,0);pbuf_free(p);memcpy(h,bytes,16);
 for(unsigned i=0;i<4;i++)h[i]=lwip_ntohl(h[i]);
 if(h[0]!=DATA||h[1]!=run_id||h[3]!=len||h[2]>=SEQUENCES){rx_bad++;return;}
 for(unsigned i=16;i<len;i++)if(bytes[i]!=(uint8_t)(h[1]+h[2]+i)){rx_bad++;return;}
 uint32_t seq=h[2];uint8_t mask=1u<<(seq&7);
 if(seen[seq>>3]&mask){rx_duplicates++;return;}
 seen[seq>>3]|=mask;if(rx_packets&&seq<high_seq)rx_reordered++;if(seq>high_seq)high_seq=seq;
 rx_packets++;rx_bytes+=len;
}
static void pump_udp(void){
 if(!sender.active)return;
 uint64_t now=ticks();if(now>=sender.end){sender.active=0;return;}
 for(unsigned n=0;n<16 && (!sender.period||now>=sender.next);n++){
  uint8_t bytes[1472];uint32_t h[]={lwip_htonl(DATA),lwip_htonl(sender.id),lwip_htonl(sender.seq),lwip_htonl(sender.len)};
  memcpy(bytes,h,16);for(unsigned i=16;i<sender.len;i++)bytes[i]=(uint8_t)(sender.id+sender.seq+i);
  struct pbuf*p=pbuf_alloc(PBUF_TRANSPORT,sender.len,PBUF_RAM);if(!p){sender.errors++;break;}
  pbuf_take(p,bytes,sender.len);err_t e=udp_sendto(source_pcb,p,&sender.peer,sender.port);pbuf_free(p);
  if(e!=ERR_OK){sender.errors++;break;}
  sender.seq++;sender.sent++;sender.next+=sender.period;now=ticks();
  if(now>=sender.end){sender.active=0;break;}
 }
}
static void tcp_error(void*arg,err_t e){(void)e;((struct connection*)arg)->pcb=0;}
static err_t tcp_receive(void*arg,struct tcp_pcb*pcb,struct pbuf*p,err_t e){
 struct connection*c=arg;(void)e;
 if(!p){tcp_arg(pcb,0);tcp_err(pcb,0);c->pcb=0;tcp_close(pcb);return ERR_OK;}
 if(!c->source){for(struct pbuf*q=p;q;q=q->next){if(memcmp(q->payload,pattern+(c->received&255),q->len))tcp_bad_chunks++;tcp_rx_bytes+=q->len;c->received+=q->len;}}
 tcp_recved(pcb,p->tot_len);pbuf_free(p);return ERR_OK;
}
static err_t tcp_ack(void*arg,struct tcp_pcb*pcb,u16_t n){(void)arg;(void)pcb;tcp_tx_acked+=n;return ERR_OK;}
static err_t accept(void*arg,struct tcp_pcb*pcb,err_t e){
 (void)e;struct connection*c=0;for(unsigned i=0;i<8;i++)if(!connections[i].pcb){c=&connections[i];break;}
 if(!c){tcp_abort(pcb);return ERR_ABRT;}
 c->pcb=pcb;c->source=(uintptr_t)arg;c->queued=c->received=0;tcp_arg(pcb,c);tcp_recv(pcb,tcp_receive);tcp_err(pcb,tcp_error);tcp_sent(pcb,tcp_ack);tcp_nagle_disable(pcb);return ERR_OK;
}
static void pump_tcp(void){
 for(unsigned i=0;i<8;i++){struct connection*c=&connections[i];if(!c->pcb||!c->source)continue;
  for(unsigned j=0;j<4;j++){
   unsigned n=tcp_sndbuf(c->pcb);if(n>4*TCP_MSS)n=4*TCP_MSS;if(!n)break;
   err_t e=tcp_write(c->pcb,pattern+(c->queued&255),n,TCP_WRITE_FLAG_COPY);if(e!=ERR_OK)break;c->queued+=n;
  }
  tcp_output(c->pcb);
 }
}
static err_t init_if(struct netif*n){
 static const uint8_t address[]={2,0,0,0xa5,5,2};memcpy(n->hwaddr,address,6);n->hwaddr_len=6;n->mtu=1500;
 n->name[0]='a';n->name[1]='5';n->flags=NETIF_FLAG_BROADCAST|NETIF_FLAG_ETHARP;return ERR_OK;
}
void example_main(void){
 platform_init();text("HPS NETWORK BENCH BEGIN\n");value("Counter frequency",SYS(cntfrq_el0));
 for(unsigned i=0;i<sizeof(pattern);i++)pattern[i]=i&255;
 lwip_init();ip4_addr_t ip,mask,gw;IP4_ADDR(&ip,192,168,50,2);IP4_ADDR(&mask,255,255,255,0);IP4_ADDR(&gw,0,0,0,0);
 if(!netif_add(&iface,&ip,&mask,&gw,0,init_if,ethernet_input))net_panic("netif_add");
 int rc=mac_init(&iface);if(rc){value("MAC init failure",(uint64_t)(int64_t)rc);mac_diagnostics();net_panic("MAC/PHY initialization");}
 netif_set_default(&iface);netif_set_up(&iface);netif_set_link_up(&iface);
 control_pcb=udp_new();udp_bind(control_pcb,IP_ADDR_ANY,5001);udp_recv(control_pcb,command,0);
 struct udp_pcb*u=udp_new();udp_bind(u,IP_ADDR_ANY,5002);udp_recv(u,echo,0);
 u=udp_new();udp_bind(u,IP_ADDR_ANY,5003);udp_recv(u,sink,0);source_pcb=udp_new();
 for(unsigned i=0;i<2;i++){struct tcp_pcb*t=tcp_new();tcp_bind(t,IP_ADDR_ANY,5004+i);t=tcp_listen(t);tcp_arg(t,(void*)(uintptr_t)i);tcp_accept(t,accept);}
 text("READY NETWORK: 192.168.50.2 UDP control=5001 echo=5002 sink=5003 TCP sink=5004 source=5005\n");
 uint64_t end=ticks()+COUNTER_HZ*3600;
 while(!stop_requested&&ticks()<end){mac_poll(&iface);PBUF_CHECK_FREE_OOSEQ();sys_check_timeouts();pump_udp();pump_tcp();
  if(R(0x10c02014)&1){unsigned c=R(0x10c02000)&255;if(c=='D'){char status[768];stats(status,sizeof(status));text(status);text("\n");mac_diagnostics();}if(c=='Q')stop_requested=1;}
 }
 mac_stop();text("NETWORK STOPPED\n");
}
