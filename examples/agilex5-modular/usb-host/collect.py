#!/usr/bin/env python3
"""Collect a read-only USB/network/input/storage inventory from Agilex 5 Linux."""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


PROC_COMPATIBLE = Path("/proc/device-tree/compatible")
SYS_ROOT = Path("/sys")
USB_DEVICE = re.compile(r"^\d+-\d+(?:\.\d+)*$")
USB_ROOT_HUB = re.compile(r"^usb\d+$")
USB_HUB_PORT = re.compile(r"^.+-port\d+$")


def text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, UnicodeError):
        return None
    return value or None


def resolved(path: Path) -> Path | None:
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def device_tree_compatible(path: Path = PROC_COMPATIBLE) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    return [entry.decode("ascii", errors="replace") for entry in raw.split(b"\0") if entry]


def require_agilex5(compatible: list[str]) -> None:
    if not any("agilex5" in item.lower() for item in compatible):
        raise RuntimeError("board guard rejected target: device-tree compatible does not contain 'agilex5'")


def usb_device_ancestors(path: Path, usb_devices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return USB device ancestors from root-most to nearest."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for parent in (path, *path.parents):
        name = parent.name
        if name in usb_devices and name not in seen:
            found.append(usb_devices[name])
            seen.add(name)
    found.reverse()
    return found


def usb_driver_names(device_dir: Path) -> list[str]:
    candidates = [device_dir]
    try:
        candidates.extend(p for p in device_dir.iterdir() if ":" in p.name and p.is_dir())
    except OSError:
        pass
    names: set[str] = set()
    for candidate in candidates:
        driver = resolved(candidate / "driver")
        if driver is not None:
            names.add(driver.name)
    return sorted(names)


def collect_usb_devices(sys_root: Path = SYS_ROOT) -> dict[str, dict[str, Any]]:
    devices: dict[str, dict[str, Any]] = {}
    usb_dir = sys_root / "bus/usb/devices"
    try:
        entries = sorted(usb_dir.iterdir(), key=lambda path: path.name)
    except OSError:
        return devices
    for entry in entries:
        if not USB_DEVICE.fullmatch(entry.name):
            continue
        device_dir = resolved(entry)
        if device_dir is None:
            continue
        speed_text = text(entry / "speed")
        try:
            speed = float(speed_text) if speed_text is not None else None
        except ValueError:
            speed = None
        devices[entry.name] = {
            "topology_id": entry.name,
            "vendor_id": text(entry / "idVendor"),
            "product_id": text(entry / "idProduct"),
            "manufacturer": text(entry / "manufacturer"),
            "product": text(entry / "product"),
            "device_class": text(entry / "bDeviceClass"),
            "speed_mbps": speed,
            "drivers": usb_driver_names(device_dir),
        }
    return devices


def collect_hubs(usb_devices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [device for device in usb_devices.values()
            if str(device.get("device_class") or "").lower() == "09"]


def _nearest_usb_id(path: Path, usb_devices: dict[str, dict[str, Any]]) -> str | None:
    ancestors = usb_device_ancestors(path, usb_devices)
    return ancestors[-1]["topology_id"] if ancestors else None


def _is_hub(device_id: str | None, usb_devices: dict[str, dict[str, Any]]) -> bool:
    return bool(device_id and device_id in usb_devices
                and str(usb_devices[device_id].get("device_class") or "").lower() == "09")


def collect_usb_peer_links(sys_root: Path, usb_devices: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read kernel USB hub-port peer symlinks and derive confirmed hub pairs.

    Linux exposes `peer` links between USB2 high-speed and USB3 SuperSpeed
    ports that share one physical connector. Hub pairs are derived only from
    these explicit links, never from similar bus/port names or VID/PID values.
    """
    usb_dir = sys_root / "bus/usb/devices"
    try:
        entries = sorted(usb_dir.iterdir(), key=lambda path: path.name)
    except OSError:
        return [], []

    seen_hub_paths: set[Path] = set()
    links: list[dict[str, Any]] = []
    pairs: dict[tuple[str, str], list[dict[str, str]]] = {}
    try:
        root = sys_root.resolve()
    except OSError:
        root = sys_root

    for entry in entries:
        if not (USB_DEVICE.fullmatch(entry.name) or USB_ROOT_HUB.fullmatch(entry.name)):
            continue
        hub_path = resolved(entry)
        if hub_path is None or hub_path in seen_hub_paths:
            continue
        seen_hub_paths.add(hub_path)
        try:
            interfaces = sorted((path for path in hub_path.iterdir()
                                 if ":" in path.name and path.is_dir()), key=lambda path: path.name)
        except OSError:
            continue
        for interface in interfaces:
            try:
                ports = sorted((path for path in interface.iterdir()
                                if USB_HUB_PORT.fullmatch(path.name)), key=lambda path: path.name)
            except OSError:
                continue
            for port in ports:
                peer = resolved(port / "peer")
                if peer is None:
                    continue
                try:
                    peer_relative = str(peer.relative_to(root))
                except ValueError:
                    continue
                owner_id = entry.name if USB_DEVICE.fullmatch(entry.name) else None
                peer_owner_id = _nearest_usb_id(peer, usb_devices)
                attached_id = _nearest_usb_id(resolved(port / "device") or port, usb_devices)
                peer_attached_id = _nearest_usb_id(resolved(peer / "device") or peer, usb_devices)
                link = {
                    "port": f"{entry.name}/{interface.name}/{port.name}",
                    "peer_port": peer_relative,
                    "owner_hub_id": owner_id,
                    "peer_owner_hub_id": peer_owner_id,
                    "attached_device_id": attached_id,
                    "peer_attached_device_id": peer_attached_id,
                }
                links.append(link)

                # For ports on hub devices, the port-owning devices are the
                # two logical halves. For paired root-hub ports, the attached
                # USB hub devices are the two logical halves.
                left = owner_id if _is_hub(owner_id, usb_devices) else None
                right = peer_owner_id if _is_hub(peer_owner_id, usb_devices) else None
                if left is None and right is None:
                    if _is_hub(attached_id, usb_devices) and _is_hub(peer_attached_id, usb_devices):
                        left, right = attached_id, peer_attached_id
                if left and right and left != right:
                    pair = tuple(sorted((left, right)))
                    pairs.setdefault(pair, []).append({
                        "port": link["port"],
                        "peer_port": link["peer_port"],
                    })

    hub_pairs = []
    for (left, right), peer_ports in sorted(pairs.items()):
        speeds = {left: usb_devices[left].get("speed_mbps"),
                  right: usb_devices[right].get("speed_mbps")}
        usb3_id = next((name for name, speed in speeds.items()
                        if isinstance(speed, (int, float)) and speed >= 5000), None)
        usb2_id = next((name for name, speed in speeds.items()
                        if isinstance(speed, (int, float)) and 0 < speed <= 480), None)
        if usb3_id and usb2_id and _is_hub(usb3_id, usb_devices) and _is_hub(usb2_id, usb_devices):
            hub_pairs.append({"usb3_hub_id": usb3_id, "usb2_hub_id": usb2_id,
                              "evidence": "sysfs-port-peer", "peer_ports": peer_ports})
    return links, hub_pairs


def collect_usb_network(sys_root: Path, usb_devices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    net_dir = sys_root / "class/net"
    try:
        entries = sorted(net_dir.iterdir(), key=lambda path: path.name)
    except OSError:
        return result
    for entry in entries:
        path = resolved(entry / "device")
        if path is None:
            continue
        ancestry = usb_device_ancestors(path, usb_devices)
        if not ancestry:
            continue
        result.append({
            "interface": entry.name,
            "mac": text(entry / "address"),
            "operstate": text(entry / "operstate"),
            "carrier": text(entry / "carrier"),
            "usb_ancestry": ancestry,
        })
    return result


def input_name(event_path: Path, resolved_path: Path) -> str | None:
    for candidate in (event_path / "device/name", resolved_path.parent / "name", resolved_path / "name"):
        value = text(candidate)
        if value:
            return value
    return None


def collect_usb_inputs(sys_root: Path, usb_devices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    input_dir = sys_root / "class/input"
    try:
        entries = sorted(input_dir.glob("event*"), key=lambda path: path.name)
    except OSError:
        return result
    for entry in entries:
        path = resolved(entry / "device")
        if path is None:
            continue
        ancestry = usb_device_ancestors(path, usb_devices)
        if not ancestry:
            continue
        result.append({
            "event": entry.name,
            "name": input_name(entry, path),
            "usb_ancestry": ancestry,
        })
    return result


def collect_usb_storage(sys_root: Path, usb_devices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    block_dir = sys_root / "class/block"
    try:
        entries = sorted(block_dir.iterdir(), key=lambda path: path.name)
    except OSError:
        return result
    for entry in entries:
        # Partition nodes have this attribute; capacity is reported per whole disk.
        if (entry / "partition").exists():
            continue
        path = resolved(entry / "device")
        if path is None:
            continue
        ancestry = usb_device_ancestors(path, usb_devices)
        if not ancestry:
            continue
        sectors_text = text(entry / "size")
        try:
            capacity_bytes = int(sectors_text) * 512 if sectors_text is not None else None
        except ValueError:
            capacity_bytes = None
        result.append({
            "block_device": entry.name,
            "capacity_bytes": capacity_bytes,
            "removable": text(entry / "removable"),
            "usb_ancestry": ancestry,
        })
    return result


def collect() -> dict[str, Any]:
    compatible = device_tree_compatible()
    require_agilex5(compatible)
    usb_devices = collect_usb_devices()
    port_peer_links, companion_hub_pairs = collect_usb_peer_links(SYS_ROOT, usb_devices)
    return {
        "schema": "agilex5-usb-host-inventory-v1",
        "scope": "board-live-read-only-inventory",
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "board": {"compatible": compatible},
        "usb_devices": list(usb_devices.values()),
        "usb_hubs": collect_hubs(usb_devices),
        "usb_port_peer_links": port_peer_links,
        "usb_companion_hub_pairs": companion_hub_pairs,
        "usb_network_interfaces": collect_usb_network(SYS_ROOT, usb_devices),
        "usb_input_events": collect_usb_inputs(SYS_ROOT, usb_devices),
        "usb_storage_disks": collect_usb_storage(SYS_ROOT, usb_devices),
        "access_scope": {
            "read_only": True,
            "storage_contents_read": False,
            "storage_mounted_or_written": False,
            "network_configured_or_traffic_generated": False,
        },
    }


def main() -> int:
    try:
        document = collect()
    except RuntimeError as exc:
        print(json.dumps({"schema": "agilex5-usb-host-inventory-v1", "scope": "rejected", "error": str(exc)}))
        return 2
    json.dump(document, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
