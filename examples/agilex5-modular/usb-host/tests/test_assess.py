import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("usb_host_assess", HERE / "assess.py")
assess = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(assess)
collect_spec = importlib.util.spec_from_file_location("usb_host_collect", HERE / "collect.py")
collector = importlib.util.module_from_spec(collect_spec)
assert collect_spec.loader is not None
collect_spec.loader.exec_module(collector)


def fixture():
    usb3_hub = {"topology_id": "3-1", "device_class": "09", "speed_mbps": 5000,
                "vendor_id": "1234", "product_id": "5678", "product": "Fixture USB 3 Hub", "drivers": ["hub"]}
    usb2_hub = {"topology_id": "2-1", "device_class": "09", "speed_mbps": 480,
                "vendor_id": "1234", "product_id": "5678", "product": "Fixture USB 2 Hub", "drivers": ["hub"]}
    nic = {"topology_id": "3-1.1", "speed_mbps": 5000, "product": "Fixture Ethernet Adapter"}
    mouse = {"topology_id": "2-1.2", "speed_mbps": 12, "product": "Fixture Mouse"}
    disk = {"topology_id": "3-1.3", "speed_mbps": 5000, "product": "Fixture Flash Drive"}
    return {
        "schema": assess.SCHEMA,
        "scope": "fixture-only",
        "board": {"compatible": ["fixture,agilex5"]},
        "usb_hubs": [usb3_hub, usb2_hub],
        "usb_companion_hub_pairs": [{
            "usb3_hub_id": "3-1", "usb2_hub_id": "2-1", "evidence": "sysfs-port-peer",
            "peer_ports": [{"port": "3-1/3-1:1.0/3-1-port1",
                            "peer_port": "devices/usb2/2-1/2-1:1.0/2-1-port1"}],
        }],
        "usb_network_interfaces": [{"interface": "eth-fixture", "mac": "02:00:00:00:00:01",
                                     "operstate": "up", "carrier": "1", "usb_ancestry": [usb3_hub, nic]}],
        "usb_input_events": [{"event": "event-fixture", "name": "Fixture USB Mouse",
                               "usb_ancestry": [usb2_hub, mouse]}],
        "usb_storage_disks": [{"block_device": "sd-fixture", "capacity_bytes": 16000000000,
                                "removable": "1", "usb_ancestry": [usb3_hub, disk]}],
        "access_scope": {"read_only": True, "storage_contents_read": False,
                         "storage_mounted_or_written": False,
                         "network_configured_or_traffic_generated": False},
    }


class AssessFixtures(unittest.TestCase):
    def test_split_usb2_mouse_confirms_only_with_peer_link_pair(self):
        result = assess.assess_capture(fixture())
        self.assertTrue(result["criteria"]["usb2_mouse_detected"])
        self.assertEqual(result["usb2_mouse_topology"], "confirmed")
        self.assertEqual(result["inventory_status"], "inventory_pass")
        self.assertEqual(result["status"], "fixture_not_hardware")
        self.assertFalse(result["hardware_qualification"])

    def test_mouse_on_unrelated_usb2_hub_is_topology_unconfirmed(self):
        capture = fixture()
        capture["usb_companion_hub_pairs"] = []
        # Similar bus/port numbering and identical VID/PID do not establish a
        # companion relationship. Only the explicit kernel peer link does.
        result = assess.assess_capture(capture)
        self.assertTrue(result["criteria"]["usb2_mouse_detected"])
        self.assertEqual(result["usb2_mouse_topology"], "topology_unconfirmed")
        self.assertEqual(result["inventory_status"], "topology_unconfirmed")
        self.assertEqual(result["status"], "fixture_not_hardware")

    def test_port_number_or_vid_pid_similarity_is_not_peer_evidence(self):
        capture = fixture()
        capture["usb_companion_hub_pairs"] = [{
            "usb3_hub_id": "3-1", "usb2_hub_id": "2-1",
            "evidence": "same-port-number-and-vid-pid",
        }]
        result = assess.assess_capture(capture)
        self.assertEqual(result["usb2_mouse_topology"], "topology_unconfirmed")
        self.assertEqual(result["inventory_status"], "topology_unconfirmed")

    def test_usb2_mouse_speed_is_required(self):
        capture = fixture()
        capture["usb_input_events"][0]["usb_ancestry"][-1]["speed_mbps"] = 5000
        result = assess.assess_capture(capture)
        self.assertFalse(result["criteria"]["usb2_mouse_detected"])
        self.assertEqual(result["status"], "fixture_not_hardware")

    def test_downstream_storage_must_share_usb3_hub_ancestry(self):
        capture = fixture()
        capture["usb_storage_disks"][0]["usb_ancestry"] = [
            {"topology_id": "4-1", "device_class": "09", "speed_mbps": 480},
            {"topology_id": "4-1.1", "speed_mbps": 480},
        ]
        result = assess.assess_capture(capture)
        self.assertFalse(result["criteria"]["usb_storage_disk_below_hub"])

    def test_non_agilex_identity_is_rejected_by_collector_guard(self):
        with self.assertRaisesRegex(RuntimeError, "board guard rejected"):
            collector.require_agilex5(["generic,linux-host"])

    def test_collector_derives_root_hub_companion_pair_only_from_peer_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            sys_root = Path(temporary) / "sys"
            usb_bus = sys_root / "bus/usb/devices"
            devices_root = sys_root / "devices"
            usb_bus.mkdir(parents=True)
            devices_root.mkdir()

            root3 = devices_root / "usb3"
            root2 = devices_root / "usb2"
            hub3 = devices_root / "3-1"
            hub2 = devices_root / "2-1"
            for path in (root3, root2, hub3, hub2):
                path.mkdir()
            for name, target in (("usb3", root3), ("usb2", root2),
                                 ("3-1", hub3), ("2-1", hub2)):
                (usb_bus / name).symlink_to(target, target_is_directory=True)

            port3 = root3 / "3-0:1.0/3-0-port1"
            port2 = root2 / "2-0:1.0/2-0-port1"
            port3.mkdir(parents=True)
            port2.mkdir(parents=True)
            (port3 / "peer").symlink_to(os.path.relpath(port2, port3), target_is_directory=True)
            (port2 / "peer").symlink_to(os.path.relpath(port3, port2), target_is_directory=True)
            (port3 / "device").symlink_to(hub3, target_is_directory=True)
            (port2 / "device").symlink_to(hub2, target_is_directory=True)

            usb_devices = {
                "3-1": {"topology_id": "3-1", "device_class": "09", "speed_mbps": 5000},
                "2-1": {"topology_id": "2-1", "device_class": "09", "speed_mbps": 480},
            }
            links, pairs = collector.collect_usb_peer_links(sys_root, usb_devices)
            self.assertEqual(len(links), 2)
            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0]["usb3_hub_id"], "3-1")
            self.assertEqual(pairs[0]["usb2_hub_id"], "2-1")

    def test_network_or_storage_side_effects_are_rejected(self):
        capture = fixture()
        capture["access_scope"]["network_configured_or_traffic_generated"] = True
        with self.assertRaisesRegex(assess.InvalidCapture, "not accessed"):
            assess.assess_capture(capture)


if __name__ == "__main__":
    unittest.main()
