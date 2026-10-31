// SPDX-License-Identifier: MIT-0
/* Bounded boot-protocol mouse demo using U-Boot's maintained USB host stack. */
#include <command.h>
#include <console.h>
#include <dm.h>
#include <dm/uclass-internal.h>
#include <malloc.h>
#include <usb.h>
#include <asm/byteorder.h>
#include <linux/errno.h>

static struct usb_device *mouse_on_device(struct udevice *device, int *interface)
{
	struct usb_device *usb;
	int i;
	if (!device_active(device))
		return NULL;
	usb = dev_get_parent_priv(device);
	if (!usb)
		return NULL;
	for (i = 0; i < usb->config.no_of_if && i < USB_MAXINTERFACES; i++) {
		struct usb_interface_descriptor *desc = &usb->config.if_desc[i].desc;
		if (desc->bInterfaceClass == USB_CLASS_HID &&
		    desc->bInterfaceSubClass == 1 && desc->bInterfaceProtocol == 2) {
			*interface = i;
			return usb;
		}
	}
	return NULL;
}

static struct usb_device *find_mouse(int *interface)
{
	struct uclass *hubs;
	struct udevice *hub, *child;
	struct usb_device *usb;
	if (uclass_get(UCLASS_USB_HUB, &hubs))
		return NULL;
	uclass_foreach_dev(hub, hubs) {
		if (!device_active(hub))
			continue;
		for (device_find_first_child(hub, &child); child;
		     device_find_next_child(&child)) {
			usb = mouse_on_device(child, interface);
			if (usb)
				return usb;
		}
	}
	return NULL;
}

static int do_usb_lab_mouse(struct cmd_tbl *cmdtp, int flag, int argc,
			    char *const argv[])
{
	struct usb_device *usb;
	struct usb_interface *iface;
	struct usb_endpoint_descriptor *endpoint = NULL;
	unsigned int attempts = 4, i, received = 0, events = 0;
	unsigned char *report;
	int interface = -1, length, rc;
	if (argc > 1) {
		char *end;
		attempts = simple_strtoul(argv[1], &end, 10);
		if (*end || attempts < 1 || attempts > 8)
			return CMD_RET_USAGE;
	}
	if (!usb_started) {
		printf("FAIL USB_MOUSE: run usb start first\n");
		return CMD_RET_FAILURE;
	}
	usb = find_mouse(&interface);
	if (!usb) {
		printf("FAIL USB_MOUSE: no HID boot-protocol mouse enumerated\n");
		return CMD_RET_FAILURE;
	}
	iface = &usb->config.if_desc[interface];
	for (i = 0; i < iface->no_of_ep && i < USB_MAXENDPOINTS; i++) {
		struct usb_endpoint_descriptor *ep = &iface->ep_desc[i];
		if ((ep->bEndpointAddress & USB_DIR_IN) &&
		    (ep->bmAttributes & USB_ENDPOINT_XFERTYPE_MASK) == USB_ENDPOINT_XFER_INT) {
			endpoint = ep;
			break;
		}
	}
	if (!endpoint) {
		printf("FAIL USB_MOUSE: no interrupt-IN endpoint\n");
		return CMD_RET_FAILURE;
	}
	length = le16_to_cpu(endpoint->wMaxPacketSize) & 0x7ff;
	if (length < 3 || length > 64) {
		printf("FAIL USB_MOUSE: unsupported packet size %d\n", length);
		return CMD_RET_FAILURE;
	}
	if (usb_set_protocol(usb, iface->desc.bInterfaceNumber, 0)) {
		printf("FAIL USB_MOUSE: boot-protocol selection failed\n");
		return CMD_RET_FAILURE;
	}
	report = memalign(ARCH_DMA_MINALIGN, 64);
	if (!report)
		return CMD_RET_FAILURE;
	printf("USB_MOUSE_BEGIN vid=%04x pid=%04x address=%d interface=%d attempts=%u\n",
	       usb->descriptor.idVendor, usb->descriptor.idProduct,
	       usb->devnum, iface->desc.bInterfaceNumber, attempts);
	printf("Move or click the mouse now; interrupt attempts are bounded.\n");
	for (i = 0; i < attempts; i++) {
		if (ctrlc())
			break;
		memset(report, 0, 64);
		usb->act_len = 0;
		usb->status = USB_ST_NOT_PROC;
		rc = usb_int_msg(usb, usb_rcvintpipe(usb, endpoint->bEndpointAddress & 0xf),
				report, length, endpoint->bInterval, false);
		if (rc || usb->status || usb->act_len < 3 || usb->act_len > length) {
			printf("USB_MOUSE_WAIT attempt=%u rc=%d status=%lx length=%d\n",
			       i + 1, rc, usb->status, usb->act_len);
			continue;
		}
		received++;
		if ((report[0] & 7) || report[1] || report[2])
			events++;
		printf("USB_MOUSE_REPORT length=%d buttons=%u dx=%d dy=%d bytes=",
		       usb->act_len, report[0] & 7, (signed char)report[1], (signed char)report[2]);
		for (int j = 0; j < usb->act_len; j++)
			printf("%02x", report[j]);
		printf("\n");
	}
	free(report);
	if (!received) {
		printf("FAIL USB_MOUSE: no interrupt reports received\n");
		return CMD_RET_FAILURE;
	}
	printf("PASS USB_MOUSE_REPORTS count=%u\n", received);
	if (!events) {
		printf("INCOMPLETE USB_MOUSE_EVENTS: no nonzero motion/button reports; move or click and retry\n");
		return CMD_RET_FAILURE;
	}
	printf("PASS USB_MOUSE_EVENTS count=%u\n", events);
	return CMD_RET_SUCCESS;
}

U_BOOT_CMD(usb_lab_mouse, 2, 0, do_usb_lab_mouse,
	   "capture bounded HID boot-mouse interrupt reports",
	   "[attempts 1..8] - run usb start first, then move/click the mouse");
