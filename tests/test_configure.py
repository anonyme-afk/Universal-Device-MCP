from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from universal_device_mcp.configure import (
    auto_configure_all,
    build_mcp_entry,
    configure_json_client,
    detect_installed_clients,
    get_default_config_paths,
    main,
    resolve_server_command,
)


class ConfigureTests(unittest.TestCase):
    def test_get_default_config_paths_returns_known_clients(self):
        paths = get_default_config_paths()
        self.assertIn("claude-desktop", paths)
        self.assertIn("cursor", paths)
        self.assertIn("antigravity", paths)
        self.assertIn("cline", paths)

    def test_detect_installed_clients(self):
        detected = detect_installed_clients()
        self.assertIsInstance(detected, dict)

    def test_auto_configure_all_dry_run(self):
        configured = auto_configure_all(dry_run=True)
        self.assertIsInstance(configured, list)

    def test_build_mcp_entry(self):
        entry = build_mcp_entry("python", ["-m", "server"], env={"FOO": "BAR"})
        self.assertEqual("python", entry["command"])
        self.assertEqual(["-m", "server"], entry["args"])
        self.assertEqual({"FOO": "BAR"}, entry["env"])

    def test_resolve_server_command_uvx(self):
        cmd, args = resolve_server_command(mode="uvx")
        self.assertEqual("uvx", cmd)
        self.assertTrue(any("universal-device-mcp" in arg for arg in args))

    def test_resolve_server_command_python(self):
        cmd, args = resolve_server_command(python_path="/usr/bin/python3")
        self.assertEqual(str(Path("/usr/bin/python3").resolve()), cmd)
        self.assertEqual(["-m", "universal_device_mcp.server"], args)

    def test_configure_json_client_creates_file_and_preserves_others(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            # Initial file with existing server
            config_file.write_text(
                json.dumps({"mcpServers": {"existing-tool": {"command": "echo"}}}),
                encoding="utf-8",
            )

            entry = build_mcp_entry("dummy", ["run"])
            success = configure_json_client(config_file, entry=entry)
            self.assertTrue(success)

            # Check that file was updated
            with open(config_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIn("existing-tool", data["mcpServers"])
            self.assertIn("universal-device", data["mcpServers"])
            self.assertEqual("dummy", data["mcpServers"]["universal-device"]["command"])

            # Check backup file was created
            backup = Path(tmpdir) / "config.json.bak"
            self.assertTrue(backup.exists())

    def test_configure_json_client_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            entry = build_mcp_entry("dummy", ["run"])
            success = configure_json_client(config_file, entry=entry, dry_run=True)
            self.assertTrue(success)
            self.assertFalse(config_file.exists())

    def test_main_print_json(self):
        with patch("sys.stdout"):
            exit_code = main(["--print-json", "--enable-simulator"])
            self.assertEqual(0, exit_code)

    def test_main_dry_run(self):
        exit_code = main(["--dry-run", "--client", "cursor"])
        self.assertEqual(0, exit_code)


if __name__ == "__main__":
    unittest.main()

