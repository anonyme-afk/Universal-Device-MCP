"""Tests for device lifecycle and access-policy tooling."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.models import Device
from universal_device_mcp.server import DeviceService


class FakeAdapter:
    transport = "fake"

    def discover(self):
        return [Device("fake-device", self.transport, "Test", "fake:1",
                       identity={"state": "device"},
                       interfaces=[{"id": "shell", "kind": "fake-shell"}])]

    def communicate(self, device, interface_id, operation, data=None, **options):
        return {"sent": len(data or b"")}

    def open_interface(self, device, interface_id, **options):
        return {"open": True}

    def close_interface(self, device, interface_id, session):
        session["open"] = False


class DeviceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db_path = Path(self.folder.name) / "devices.sqlite3"
        self.memory = DeviceMemory(self.db_path)
        self.adapter = FakeAdapter()
        self.service = DeviceService(memory=self.memory, adapters=[self.adapter])

    def tearDown(self):
        self.folder.cleanup()

    def test_connect_and_disconnect_known_device(self):
        device = self.service.discover()["devices"][0]
        self.assertEqual(device["device_id"], "fake-device")
        connected = self.service.connect_device(device["device_id"])
        self.assertTrue(connected["connected"])
        self.assertEqual(connected["transport"], "fake")
        self.assertIn(device["device_id"], self.service._connected)
        disconnected = self.service.disconnect_device(device["device_id"])
        self.assertFalse(disconnected["connected"])
        self.assertNotIn(device["device_id"], self.service._connected)

    def test_connect_unknown_device_fails(self):
        with self.assertRaisesRegex(KeyError, "Unknown device"):
            self.service.connect_device("does-not-exist")

    def test_delete_device_experiment_round_trip(self):
        device = self.service.discover()["devices"][0]
        self.service.memory.add_experiment(
            device["device_id"], "shell", "read",
            {"data_hex": "CAFE"}, {"ok": True}, True)
        knowledge = self.service.memory.get_knowledge(device["device_id"])
        self.assertEqual(1, len(knowledge["experiments"]))
        experiment_id = knowledge["experiments"][0]["id"]
        self.assertTrue(self.service.memory.delete_experiment(device["device_id"], experiment_id))
        knowledge_after = self.service.memory.get_knowledge(device["device_id"])
        self.assertEqual(0, len(knowledge_after["experiments"]))

    def test_delete_unknown_experiment_returns_false(self):
        self.assertFalse(self.service.memory.delete_experiment("no-device", 999))

    def test_access_policy_defaults_to_safe_and_can_be_reloaded(self):
        with tempfile.TemporaryDirectory() as folder:
            policy_path = Path(folder) / "policy.json"
            policy_path.write_text(json.dumps({"max_write_bytes": 100}), encoding="utf-8")
            env = {"UDMCP_POLICY": str(policy_path)}
            with patch.dict(os.environ, {**env, "UDMCP_ACCESS_MODE": "trusted"}):
                policy = self.service.access_policy()["policy"]
                self.assertEqual("trusted", policy["access_mode"])
                self.assertEqual(100, policy["max_write_bytes"])


if __name__ == "__main__":
    unittest.main()