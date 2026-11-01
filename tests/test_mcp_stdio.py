import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from universal_device_mcp.memory import DeviceMemory
from universal_device_mcp.models import Device


class MCPStdioTests(unittest.TestCase):
    def test_initialize_list_and_call_over_stdio(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as data_dir:
            database_path = Path(data_dir) / "devices.sqlite3"
            DeviceMemory(database_path).save_device(
                Device("profile-test", "fake", "Test profile", "fake:profile-test"))
            env = os.environ.copy()
            source_path = str(root / "src")
            env["PYTHONPATH"] = source_path + os.pathsep + env.get("PYTHONPATH", "")
            env["UDMCP_DATABASE"] = str(database_path)
            env["UDMCP_AUTO_MONITOR"] = "false"
            env["UDMCP_FORCE_STDIO_FALLBACK"] = "true"
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "2025-03-26", "capabilities": {},
                    "clientInfo": {"name": "udmcp-test", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                    "name": "list_known_devices", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                    "name": "discover_devices", "arguments": {"transports": ["usb", "hid"]}}},
                {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                    "name": "get_runtime_status", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {}},
                {"jsonrpc": "2.0", "id": 7, "method": "resources/read", "params": {
                    "uri": "udmcp://devices"}},
                {"jsonrpc": "2.0", "id": 8, "method": "resources/templates/list", "params": {}},
                {"jsonrpc": "2.0", "id": 9, "method": "resources/read", "params": {
                    "uri": "udmcp://devices/profile-test/profile"}},
                {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {
                    "name": "get_device_events", "arguments": {"after_id": "bad"}}},
                {"jsonrpc": "2.0", "id": 11, "method": "resources/read", "params": {
                    "uri": "udmcp://devices/missing-profile/profile"}},
            ]
            completed = subprocess.run(
                [sys.executable, "-m", "universal_device_mcp.server"], cwd=root, env=env,
                input="".join(json.dumps(item) + "\n" for item in messages),
                text=True, capture_output=True, timeout=20, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        replies = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        by_id = {reply["id"]: reply for reply in replies if "id" in reply}
        self.assertEqual("2024-11-05", by_id[1]["result"]["protocolVersion"])
        names = {tool["name"] for tool in by_id[2]["result"]["tools"]}
        self.assertIn("discover_devices", names)
        self.assertIn("communicate", names)
        self.assertIn("get_runtime_status", names)
        self.assertIn("list_known_devices", names)
        listed = json.loads(by_id[3]["result"]["content"][0]["text"])
        self.assertEqual("profile-test", listed["devices"][0]["device_id"])
        discovery = json.loads(by_id[4]["result"]["content"][0]["text"])
        self.assertIn("devices", discovery)
        self.assertIn("errors", discovery)
        runtime = json.loads(by_id[5]["result"]["content"][0]["text"])
        self.assertIn("adapters", runtime)
        self.assertIn("database_path", runtime)
        resource_uris = {item["uri"] for item in by_id[6]["result"]["resources"]}
        self.assertIn("udmcp://devices", resource_uris)
        inventory = json.loads(by_id[7]["result"]["contents"][0]["text"])
        self.assertEqual("profile-test", inventory["devices"][0]["device_id"])
        templates = by_id[8]["result"]["resourceTemplates"]
        self.assertIn("udmcp://devices/{device_id}/profile", {item["uriTemplate"] for item in templates})
        profile = json.loads(by_id[9]["result"]["contents"][0]["text"])
        self.assertEqual("profile-test", profile["device_id"])
        self.assertTrue(by_id[10]["result"]["isError"])
        self.assertEqual(-32603, by_id[11]["error"]["code"])
        tools = by_id[2]["result"]["tools"]
        runtime_tool = next(tool for tool in tools if tool["name"] == "get_runtime_status")
        self.assertTrue(runtime_tool["annotations"]["readOnlyHint"])


if __name__ == "__main__":
    unittest.main()
