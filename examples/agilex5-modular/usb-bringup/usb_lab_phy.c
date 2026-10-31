// SPDX-License-Identifier: MIT-0
/* SOM USB3320 identification through the DWC3 ULPI register-access viewport.
 * Protocol/bit definitions: Linux drivers/usb/dwc3/{ulpi.c,core.h}.
 * PHY ID: Microchip USB3320 datasheet DS00001792E, ULPI registers 0..3.
 * This command issues only PHY reads; it changes no PHY configuration.
 */
#include <command.h>
#include <asm/io.h>
#include <linux/bitops.h>
#include <linux/delay.h>
#include <linux/errno.h>

#define LAB_USB1_BASE 0x11000000UL
#define LAB_GSNPSID 0xc120
#define LAB_GHWPARAMS3 0xc14c
#define LAB_GDBGLTSSM 0xc164
#define LAB_GUSB2PHYCFG 0xc200
#define LAB_GUSB2PHYACC 0xc280
#define LAB_ULPI_SELECT BIT(4)
#define LAB_ULPI_NEWREQ BIT(25)
#define LAB_ULPI_DONE BIT(24)
#define LAB_ULPI_BUSY BIT(23)

static u32 usb_lab_read(unsigned int offset)
{
	return readl((void __iomem *)(LAB_USB1_BASE + offset));
}

static int usb_lab_ulpi_id_byte(unsigned int address, unsigned char *value)
{
	u32 status = usb_lab_read(LAB_GUSB2PHYACC);
	unsigned int attempt;

	/* Never replace an outstanding transaction left by another user. */
	if ((status & LAB_ULPI_BUSY) ||
	    ((status & LAB_ULPI_NEWREQ) && !(status & LAB_ULPI_DONE))) {
		printf("FAIL USB_ULPI_BUSY reg=%u viewport=%08x\n", address, status);
		return -EBUSY;
	}
	/* WRITE bit22 is deliberately zero. Addresses are restricted to ID0..3. */
	if (address > 3)
		return -EINVAL;
	writel(LAB_ULPI_NEWREQ | (address << 16),
	       (void __iomem *)(LAB_USB1_BASE + LAB_GUSB2PHYACC));
	for (attempt = 0; attempt < 100; attempt++) {
		udelay(1000);
		status = usb_lab_read(LAB_GUSB2PHYACC);
		if ((status & LAB_ULPI_DONE) && !(status & LAB_ULPI_BUSY)) {
			*value = status & 0xff;
			printf("USB_ULPI_ID reg=%u value=%02x viewport=%08x\n",
			       address, *value, status);
			return 0;
		}
	}
	printf("FAIL USB_ULPI_TIMEOUT reg=%u viewport=%08x polls=100\n",
	       address, status);
	return -ETIMEDOUT;
}

static int do_usb_lab_phy(struct cmd_tbl *cmdtp, int flag, int argc,
			  char *const argv[])
{
	u32 id = usb_lab_read(LAB_GSNPSID);
	u32 cfg, params;
	unsigned char bytes[4];
	unsigned int i, vendor, product;

	printf("USB_PHY_SNAPSHOT GSNPSID=%08x\n", id);
	if ((id >> 16) != 0x3331) {
		printf("FAIL USB_PHY_CONTROLLER_ID expected_family=3331\n");
		return CMD_RET_FAILURE;
	}
	cfg = usb_lab_read(LAB_GUSB2PHYCFG);
	params = usb_lab_read(LAB_GHWPARAMS3);
	printf("USB_PHY_SNAPSHOT GHWPARAMS3=%08x GUSB2PHYCFG=%08x GDBGLTSSM=%08x\n",
	       params, cfg, usb_lab_read(LAB_GDBGLTSSM));
	if (!(cfg & LAB_ULPI_SELECT) || ((params >> 2) & 3) < 2) {
		printf("FAIL USB_PHY_NOT_ULPI no_viewport_request_issued\n");
		return CMD_RET_FAILURE;
	}
	for (i = 0; i < 4; i++)
		if (usb_lab_ulpi_id_byte(i, &bytes[i]))
			return CMD_RET_FAILURE;
	vendor = bytes[0] | (bytes[1] << 8);
	product = bytes[2] | (bytes[3] << 8);
	printf("USB_PHY_ID vendor=%04x product=%04x expected=0424:0007\n",
	       vendor, product);
	if (vendor != 0x0424 || product != 0x0007) {
		printf("FAIL USB_PHY_ID does_not_match_SOM_USB3320\n");
		return CMD_RET_FAILURE;
	}
	printf("PASS USB_PHY_ID USB3320 ULPI register reads completed; enumeration not tested\n");
	return CMD_RET_SUCCESS;
}

U_BOOT_CMD(usb_lab_phy, 1, 0, do_usb_lab_phy,
	   "read SOM USB3320 ULPI IDs with bounded viewport transactions",
	   "- PHY identification only; no PHY configuration writes or enumeration");
