#!/usr/bin/env python3
"""Apply exact, read-only diagnostic prints to the pinned U-Boot host driver."""
from pathlib import Path
import argparse,subprocess

def replace(text,old,new):
    if text.count(old)!=1:raise RuntimeError('Pinned diagnostic hook changed: '+old[:70])
    return text.replace(old,new,1)

def dwc3(text, u3_quirk=True):
    marker='static int xhci_dwc3_probe(struct udevice *dev)'
    helper='''/* Local USB lab diagnostics: reads only; normal driver sequencing is unchanged. */
static void usb_lab_dwc3_state(const char *stage, struct xhci_hccr *hccr,
                              struct xhci_hcor *hcor, struct dwc3 *dwc)
{
	printf("USB_LAB stage=%s CAPBASE=%08x GSNPSID=%08x GCTL=%08x U2CFG=%08x U3PIPE=%08x USBCMD=%08x USBSTS=%08x\\n",
	       stage, xhci_readl(&hccr->cr_capbase), readl(&dwc->g_snpsid),
	       readl(&dwc->g_ctl), readl(&dwc->g_usb2phycfg[0]),
	       readl(&dwc->g_usb3pipectl[0]), xhci_readl(&hcor->or_usbcmd),
	       xhci_readl(&hcor->or_usbsts));
}

'''
    text=replace(text,marker,helper+marker)
    text=replace(text,'\tret = xhci_dwc3_reset_init(dev, plat);\n\tif (ret)', '\tprintf("USB_LAB stage=reset-enter device=%s\\n", dev->name);\n\tret = xhci_dwc3_reset_init(dev, plat);\n\tprintf("USB_LAB stage=reset-return rc=%d\\n", ret);\n\tif (ret)')
    text=replace(text,'\tret = xhci_dwc3_clk_init(dev, plat);\n\tif (ret)', '\tprintf("USB_LAB stage=clock-enter\\n");\n\tret = xhci_dwc3_clk_init(dev, plat);\n\tprintf("USB_LAB stage=clock-return rc=%d\\n", ret);\n\tif (ret)')
    text=replace(text,'\tret = dwc3_setup_phy(dev, &plat->phys);\n\tif (ret && (ret != -ENOTSUPP))', '\tdwc3_reg = (struct dwc3 *)((char *)(hccr) + DWC3_REG_OFFSET);\n\tusb_lab_dwc3_state("before-phy", hccr, hcor, dwc3_reg);\n\tret = dwc3_setup_phy(dev, &plat->phys);\n\tprintf("USB_LAB stage=phy-return rc=%d\\n", ret);\n\tif (ret && (ret != -ENOTSUPP))')
    text=replace(text,'\tdwc3_core_init(dwc3_reg);', '\tusb_lab_dwc3_state("before-core-init", hccr, hcor, dwc3_reg);\n\tdwc3_core_init(dwc3_reg);\n\tusb_lab_dwc3_state("after-core-init", hccr, hcor, dwc3_reg);')
    text=replace(text,'\treturn xhci_register(dev, hccr, hcor);', '\tusb_lab_dwc3_state("before-xhci-register", hccr, hcor, dwc3_reg);\n\tret = xhci_register(dev, hccr, hcor);\n\tprintf("USB_LAB stage=xhci-register-return rc=%d\\n", ret);\n\tusb_lab_dwc3_state("after-xhci-register", hccr, hcor, dwc3_reg);\n\treturn ret;')
    if u3_quirk:
        text=replace(text,'\twritel(reg, &dwc3_reg->g_usb2phycfg[0]);', '\twritel(reg, &dwc3_reg->g_usb2phycfg[0]);\n\n\t/* Match the maintained DWC3 core dis_u3_susphy quirk semantics. */\n\tif (dev_read_bool(dev, "snps,dis_u3_susphy_quirk")) {\n\t\tclrbits_le32(&dwc3_reg->g_usb3pipectl[0], DWC3_GUSB3PIPECTL_SUSPHY);\n\t\tprintf("USB_LAB stage=u3-no-suspend-quirk U3PIPE=%08x\\n",\n\t\t       readl(&dwc3_reg->g_usb3pipectl[0]));\n\t}')
    return text

def xhci(text):
    text=replace(text,'\t/* Halting the Host first */', '\tprintf("USB_LAB_RESET stage=enter USBCMD=%08x USBSTS=%08x\\n",\n\t       xhci_readl(&hcor->or_usbcmd), xhci_readl(&hcor->or_usbsts));\n\t/* Halting the Host first */')
    text=replace(text,'\tret = handshake(&hcor->or_usbsts,\n\t\t\tSTS_HALT, STS_HALT, XHCI_MAX_HALT_USEC);', '\tret = handshake(&hcor->or_usbsts,\n\t\t\tSTS_HALT, STS_HALT, XHCI_MAX_HALT_USEC);\n\tprintf("USB_LAB_RESET stage=halt-return rc=%d USBCMD=%08x USBSTS=%08x\\n",\n\t       ret, xhci_readl(&hcor->or_usbcmd), xhci_readl(&hcor->or_usbsts));')
    text=replace(text,'\tret = handshake(&hcor->or_usbcmd, CMD_RESET, 0, XHCI_MAX_RESET_USEC);', '\tret = handshake(&hcor->or_usbcmd, CMD_RESET, 0, XHCI_MAX_RESET_USEC);\n\tprintf("USB_LAB_RESET stage=hcrst-return rc=%d USBCMD=%08x USBSTS=%08x\\n",\n\t       ret, xhci_readl(&hcor->or_usbcmd), xhci_readl(&hcor->or_usbsts));')
    text=replace(text,'\treturn handshake(&hcor->or_usbsts, STS_CNR, 0, XHCI_MAX_RESET_USEC);', '\tret = handshake(&hcor->or_usbsts, STS_CNR, 0, XHCI_MAX_RESET_USEC);\n\tprintf("USB_LAB_RESET stage=cnr-return rc=%d USBCMD=%08x USBSTS=%08x\\n",\n\t       ret, xhci_readl(&hcor->or_usbcmd), xhci_readl(&hcor->or_usbsts));\n\treturn ret;')
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args()
    for name,transform in [('drivers/usb/host/xhci-dwc3.c',dwc3),('drivers/usb/host/xhci.c',xhci)]:
        path=a.source/name
        pristine=subprocess.check_output(['git','-C',str(a.source),'show','HEAD:'+name]).decode()
        modified=transform(pristine)
        accepted=(pristine,modified,dwc3(pristine,False)) if transform is dwc3 else (pristine,modified)
        if path.read_text() not in accepted:raise RuntimeError('Unexpected local source change: '+name)
        path.write_text(modified)
    print('PASS USB_DIAGNOSTIC_PATCH: stage prints plus DT-gated standard U3 no-suspend quirk')
if __name__=='__main__':main()
