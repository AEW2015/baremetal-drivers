#!/usr/bin/env python3
"""Assess a saved Agilex 5 USB inventory without accessing devices."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "agilex5-usb-host-inventory-v1"
LIVE_SCOPE = "board-live-read-only-inventory"


class InvalidCapture(ValueError):
    pass


def _dict_list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise InvalidCapture(f"{field} must be a list of objects")
    return value


def _ancestry_ids(item: dict[str, Any]) -> set[str]:
    ancestry = item.get("usb_ancestry", [])
    if not isinstance(ancestry, list):
        return set()
    return {device["topology_id"] for device in ancestry
            if isinstance(device, dict) and isinstance(device.get("topology_id"), str)}


def _speed(device: dict[str, Any]) -> float | None:
    value = device.get("speed_mbps")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _usb3_hubs(hubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [hub for hub in hubs
            if str(hub.get("device_class", "")).lower() == "09"
            and (_speed(hub) or 0) >= 5000]


def _behind_hub(item: dict[str, Any], hub_ids: set[str]) -> bool:
    return bool(hub_ids & _ancestry_ids(item))


def assess_capture(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise InvalidCapture(f"capture schema must be {SCHEMA}")
    fixture = document.get("scope") != LIVE_SCOPE

    board = document.get("board")
    if not isinstance(board, dict) or not isinstance(board.get("compatible"), list):
        raise InvalidCapture("board.compatible must be a list")
    compatible = [v for v in board["compatible"] if isinstance(v, str)]
    if not fixture and not any("agilex5" in value.lower() for value in compatible):
        return {
            "schema": "agilex5-usb-host-assessment-v1",
            "scope": "rejected-host-capture",
            "status": "not_agilex5",
            "hardware_qualification": False,
            "message": "device-tree compatible does not identify Agilex 5.",
        }

    access = document.get("access_scope")
    if not isinstance(access, dict) or access.get("read_only") is not True:
        raise InvalidCapture("access_scope.read_only must be true")
    if any(access.get(key) is not False for key in (
        "storage_contents_read", "storage_mounted_or_written", "network_configured_or_traffic_generated"
    )):
        raise InvalidCapture("capture must explicitly record that storage and network were not accessed")

    hubs = _dict_list(document.get("usb_hubs"), "usb_hubs")
    peer_pairs = _dict_list(document.get("usb_companion_hub_pairs"), "usb_companion_hub_pairs")
    network = _dict_list(document.get("usb_network_interfaces"), "usb_network_interfaces")
    inputs = _dict_list(document.get("usb_input_events"), "usb_input_events")
    storage = _dict_list(document.get("usb_storage_disks"), "usb_storage_disks")

    high_speed_hubs = _usb3_hubs(hubs)
    hub_ids = {str(hub["topology_id"]) for hub in high_speed_hubs if hub.get("topology_id") is not None}
    usb_nics = [interface for interface in network if _behind_hub(interface, hub_ids)]
    usb2_mouse_candidates = []
    for event in inputs:
        name = event.get("name")
        ancestry = event.get("usb_ancestry", [])
        nearest_speed = _speed(ancestry[-1]) if isinstance(ancestry, list) and ancestry and isinstance(ancestry[-1], dict) else None
        if (isinstance(name, str) and re.search(r"\bmouse\b", name, re.IGNORECASE)
                and nearest_speed is not None and 0 < nearest_speed <= 480):
            usb2_mouse_candidates.append(event)
    usb2_mice = []
    unconfirmed_mice = []
    for event in usb2_mouse_candidates:
        ancestry = event.get("usb_ancestry", [])
        ancestor_hubs = {
            device.get("topology_id") for device in ancestry
            if isinstance(device, dict) and str(device.get("device_class") or "").lower() == "09"
        } if isinstance(ancestry, list) else set()
        direct = bool(ancestor_hubs & hub_ids)
        paired = any(
            pair.get("evidence") == "sysfs-port-peer"
            and pair.get("usb2_hub_id") in ancestor_hubs
            and pair.get("usb3_hub_id") in hub_ids
            and any(hub.get("topology_id") == pair.get("usb2_hub_id")
                    and str(hub.get("device_class") or "").lower() == "09"
                    and 0 < (_speed(hub) or 0) <= 480 for hub in hubs)
            for pair in peer_pairs
        )
        if direct or paired:
            usb2_mice.append(event)
        else:
            unconfirmed_mice.append(event)
    usb_disks = []
    for disk in storage:
        capacity = disk.get("capacity_bytes")
        if (isinstance(capacity, int) and not isinstance(capacity, bool) and capacity > 0
                and _behind_hub(disk, hub_ids)):
            usb_disks.append(disk)

    checks = {
        "usb3_hub_link": bool(high_speed_hubs),
        "usb_ethernet_interface_below_hub": bool(usb_nics),
        "usb2_mouse_detected": bool(usb2_mouse_candidates),
        "usb_storage_disk_below_hub": bool(usb_disks),
    }
    mouse_topology = ("confirmed" if usb2_mice else
                      "topology_unconfirmed" if unconfirmed_mice else "missing")
    status = ("inventory_pass" if all(checks.values()) and mouse_topology == "confirmed"
              else "topology_unconfirmed" if all(checks.values()) and mouse_topology == "topology_unconfirmed"
              else "inventory_incomplete")
    if fixture:
        # Synthetic inputs exercise the classifier but are never promoted to
        # an observed board status, even if every fixture criterion is true.
        return {
            "schema": "agilex5-usb-host-assessment-v1",
            "scope": "fixture-only",
            "status": "fixture_not_hardware",
            "inventory_status": status,
            "hardware_qualification": False,
            "criteria": checks,
            "usb2_mouse_topology": mouse_topology,
            "message": "Fixture input; no board result can be claimed.",
        }
    return {
        "schema": "agilex5-usb-host-assessment-v1",
        "scope": "board-live-read-only-inventory",
        "status": status,
        "inventory_status": status,
        "hardware_qualification": False,
        "compatible": compatible,
        "checks": checks,
        "usb2_mouse_topology": mouse_topology,
        "observed": {
            "usb3_hubs": high_speed_hubs,
            "usb_ethernet_interfaces": usb_nics,
            "usb2_mice": usb2_mice,
            "usb2_mice_topology_unconfirmed": unconfirmed_mice,
            "usb_storage_disks": usb_disks,
        },
        "limits": {
            "usb_ethernet": "enumerated and link state recorded; packet test required separately",
            "usb2_mouse": "enumerated; input movement not tested",
            "usb_storage": "whole-disk identity and capacity only; no contents read, mount, or write",
            "usb3_hub": "enumerated hub link speed observed; downstream protocol performance not measured",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON emitted by collect.py on the board")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        result = assess_capture(document)
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidCapture) as exc:
        print(json.dumps({"schema": "agilex5-usb-host-assessment-v1", "status": "invalid_capture", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "inventory_pass":
        return 0
    if result["status"] == "inventory_incomplete":
        return 1
    if result["status"] == "topology_unconfirmed":
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
