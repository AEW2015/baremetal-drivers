#ifndef NET_ARCH_CC_H
#define NET_ARCH_CC_H
#include <stdint.h>
#include <sys/types.h>
#include <unistd.h>
#include <limits.h>
#ifndef SSIZE_MAX
#define SSIZE_MAX LONG_MAX
#endif
void net_panic(const char *s);
#define LWIP_PLATFORM_DIAG(x) do { } while(0)
#define LWIP_PLATFORM_ASSERT(x) net_panic(x)
#define LWIP_RAND() net_random()
uint32_t net_random(void);
#ifndef BYTE_ORDER
#define BYTE_ORDER LITTLE_ENDIAN
#endif
#endif
