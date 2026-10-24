#ifndef NET_PLATFORM_H
#define NET_PLATFORM_H
#include "../core/common.h"
#include "lwip/netif.h"
#define COUNTER_HZ 400000000ULL
uint64_t ticks(void);
void platform_init(void);
int mac_init(struct netif *n);
void mac_poll(struct netif *n);
void mac_stop(void);
void mac_diagnostics(void);
extern uint64_t mac_tx_packets,mac_rx_packets,mac_tx_full,mac_rx_errors;
#endif
