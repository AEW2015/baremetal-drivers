/* Secure EL3 diagnostic loader; not a replacement for a resident TF-A SMC service. */
#ifndef PR_SDM_LOADER_H
#define PR_SDM_LOADER_H
#include <stdint.h>
#define PR_DESCRIPTOR_ADDRESS 0x88200000U
struct pr_image { uint32_t address, bytes, crc32; };
struct pr_images { uint32_t magic; struct pr_image add, xor; };
int pr_sdm_load(const struct pr_image *image);
#endif
