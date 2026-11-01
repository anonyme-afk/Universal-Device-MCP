import asyncio
import importlib.metadata
import os
import sys
import tempfile
import unittest
from pathlib import Path


class OfficialSDKClientTests(unittest.TestCase):
    def test_current_sdk_client_can_launch_stdio_server(self):
        try:
            sdk_version = importlib.metadata.version("mcp")
        except importlib.metadata.PackageNotFoundError:
            self.skipTest("official MCP SDK is not installed in this environment")
        if int(sdk_version.split(".", 1)[0]) < 2:
            self.skipTest("current SDK Client integration requires MCP SDK v2")

        from mcp import Client
        from mcp.client.stdio import StdioServerParameters

        root = Path(__file__).resolve().parents[1]

        async def exercise_client(data_dir: str) -> None:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "universal_device_mcp.server"],
                cwd=root,
                env={
                    "PYTHONPATH": str(root / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
                    "UDMCP_DATABASE": str(Path(data_dir) / "devices.sqlite3"),
                    "UDMCP_AUTO_MONITOR": "false",
                },
            )
            async with Client(parameters) as client:
                tools = await client.list_tools()
                names = {tool.name for tool in tools.tools}
                self.assertIn("discover_devices", names)
                self.assertIn("open_interface", names)
                self.assertIn("analyze_payload", names)
                result = await client.call_tool("list_known_devices", {})
                self.assertFalse(result.is_error)
                self.assertEqual([], result.structured_content["devices"])
                resources = await client.list_resources()
                self.assertIn("udmcp://devices", {resource.uri for resource in resources.resources})

        with tempfile.TemporaryDirectory() as data_dir:
            asyncio.run(exercise_client(data_dir))


if __name__ == "__main__":
    unittest.main()
