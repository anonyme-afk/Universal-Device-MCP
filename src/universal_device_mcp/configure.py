"""Automatic MCP configuration utility for AI agents and developer tools.

Detects installed AI clients (Claude Desktop, Cursor, Google Antigravity / Gemini CLI,
VS Code / Cline, Roo Code, Windsurf, Codex) and automatically registers
Universal Device MCP into their configuration files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def _get_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "darwin"
    return "linux"


def get_default_config_paths() -> dict[str, Path]:
    """Return dictionary of known client names to their expected config file paths."""
    platform = _get_platform()
    home = Path.home()
    paths: dict[str, Path] = {}

    if platform == "windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))

        paths["claude-desktop"] = appdata / "Claude" / "claude_desktop_config.json"
        paths["cursor"] = home / ".cursor" / "mcp.json"
        paths["antigravity"] = home / ".gemini" / "config" / "mcp_config.json"
        paths["cline"] = (
            appdata
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["roo-code"] = (
            appdata
            / "Code"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["windsurf"] = home / ".codeium" / "windsurf" / "mcp_config.json"
    elif platform == "darwin":
        app_support = home / "Library" / "Application Support"

        paths["claude-desktop"] = app_support / "Claude" / "claude_desktop_config.json"
        paths["cursor"] = home / ".cursor" / "mcp.json"
        paths["antigravity"] = home / ".gemini" / "config" / "mcp_config.json"
        paths["cline"] = (
            app_support
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["roo-code"] = (
            app_support
            / "Code"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["windsurf"] = home / ".codeium" / "windsurf" / "mcp_config.json"
    else:  # Linux
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))

        paths["claude-desktop"] = config_dir / "Claude" / "claude_desktop_config.json"
        paths["cursor"] = home / ".cursor" / "mcp.json"
        paths["antigravity"] = home / ".gemini" / "config" / "mcp_config.json"
        paths["cline"] = (
            config_dir
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["roo-code"] = (
            config_dir
            / "Code"
            / "User"
            / "globalStorage"
            / "rooveterinaryinc.roo-cline"
            / "settings"
            / "cline_mcp_settings.json"
        )
        paths["windsurf"] = home / ".codeium" / "windsurf" / "mcp_config.json"

    return paths


def detect_installed_clients() -> dict[str, Path]:
    """Detect which AI clients exist on the local system."""
    all_paths = get_default_config_paths()
    detected: dict[str, Path] = {}

    for client, path in all_paths.items():
        # Check if the config file exists or parent client directory exists
        if path.exists() or path.parent.exists():
            detected[client] = path

    return detected


def resolve_server_command(
    python_path: str | None = None,
    mode: str = "python",
) -> tuple[str, list[str]]:
    """Determine the command and arguments to launch the server."""
    if mode == "uvx":
        return (
            "uvx",
            [
                "--from",
                "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
                "universal-device-mcp",
            ],
        )

    # Local python invocation
    exe = python_path or sys.executable
    # Check if inside virtualenv or universal-device-mcp executable exists in same directory
    exe_dir = Path(exe).parent
    ud_exe = exe_dir / ("universal-device-mcp.exe" if sys.platform.startswith("win") else "universal-device-mcp")

    if ud_exe.exists():
        return (str(ud_exe.resolve()), [])

    return (str(Path(exe).resolve()), ["-m", "universal_device_mcp.server"])


def build_mcp_entry(
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the JSON entry for an MCP server."""
    entry: dict[str, Any] = {
        "command": command,
        "args": args,
    }
    if env:
        entry["env"] = env
    return entry


def configure_json_client(
    config_path: Path,
    server_key: str = "universal-device",
    entry: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> bool:
    """Safely inject or update the MCP server entry in a JSON config file."""
    if entry is None:
        cmd, args = resolve_server_command()
        entry = build_mcp_entry(cmd, args)

    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}

    if not isinstance(data, dict):
        data = {}

    mcp_servers = data.setdefault("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}
        data["mcpServers"] = mcp_servers

    mcp_servers[server_key] = entry

    if dry_run:
        return True

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        try:
            shutil.copy2(config_path, backup_path)
        except OSError:
            pass

    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")

    return True


def auto_configure_all(
    python_path: str | None = None,
    mode: str = "python",
    env: dict[str, str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Auto-detect all installed clients and configure them."""
    detected = detect_installed_clients()
    cmd, args = resolve_server_command(python_path=python_path, mode=mode)
    entry = build_mcp_entry(cmd, args, env=env)
    configured: list[str] = []

    for client_name, path in detected.items():
        try:
            if configure_json_client(path, server_key="universal-device", entry=entry, dry_run=dry_run):
                configured.append(f"{client_name} ({path})")
        except Exception as exc:
            print(f"[!] Warning: failed to configure {client_name}: {exc}", file=sys.stderr)

    return configured


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="universal-device-configure",
        description="Auto-configure Universal Device MCP in AI agent clients (Claude Desktop, Cursor, Antigravity, Cline, etc.)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        default=True,
        help="Auto-detect all installed AI clients and configure them (default: True)",
    )
    parser.add_argument(
        "--client",
        choices=["claude-desktop", "cursor", "antigravity", "cline", "roo-code", "windsurf", "all"],
        default="all",
        help="Specify which client to configure (default: all detected)",
    )
    parser.add_argument(
        "--mode",
        choices=["python", "uvx"],
        default="python",
        help="Execution mode: local python venv or uvx (default: python)",
    )
    parser.add_argument(
        "--python",
        dest="python_path",
        default=None,
        help="Explicit path to python executable to use in MCP config",
    )
    parser.add_argument(
        "--enable-simulator",
        action="store_true",
        help="Set UDMCP_ENABLE_SIMULATOR=true in the agent's MCP config",
    )
    parser.add_argument(
        "--access-mode",
        choices=["safe", "trusted", "full", "unrestricted"],
        default=None,
        help="Set UDMCP_ACCESS_MODE environment variable",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the JSON configuration snippet to stdout instead of writing files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test detection and configuration without modifying files",
    )

    args = parser.parse_args(argv)

    env: dict[str, str] = {}
    if args.enable_simulator:
        env["UDMCP_ENABLE_SIMULATOR"] = "true"
    if args.access_mode:
        env["UDMCP_ACCESS_MODE"] = args.access_mode

    cmd, cmd_args = resolve_server_command(python_path=args.python_path, mode=args.mode)
    entry = build_mcp_entry(cmd, cmd_args, env=env if env else None)

    if args.print_json:
        snippet = {
            "mcpServers": {
                "universal-device": entry
            }
        }
        print(json.dumps(snippet, indent=2))
        return 0

    print("================================================================")
    print("  Universal Device MCP — Agent Auto-Configurator")
    print("================================================================")
    print(f"Server command: {cmd} {' '.join(cmd_args)}".strip())
    if env:
        print(f"Environment: {env}")
    print("----------------------------------------------------------------")

    all_paths = get_default_config_paths()
    targets: dict[str, Path] = {}

    if args.client == "all":
        detected = detect_installed_clients()
        if not detected:
            print("[i] No existing AI client config directories found automatically.")
            print("[i] Here is the JSON snippet to add to your client's MCP configuration:")
            print()
            print(json.dumps({"mcpServers": {"universal-device": entry}}, indent=2))
            print()
            return 0
        targets = detected
    else:
        if args.client in all_paths:
            targets[args.client] = all_paths[args.client]

    configured_count = 0
    for name, path in targets.items():
        try:
            configure_json_client(path, server_key="universal-device", entry=entry, dry_run=args.dry_run)
            status_tag = "[DRY-RUN]" if args.dry_run else "[✓ CONFIGURED]"
            print(f"{status_tag} {name} -> {path}")
            configured_count += 1
        except Exception as exc:
            print(f"[x] Error configuring {name} ({path}): {exc}")

    print("----------------------------------------------------------------")
    if configured_count > 0:
        print(f"Success! {configured_count} client(s) configured.")
        print("Restart your AI client, plug in any hardware, and ask your agent:")
        print("  \"Discover connected devices and show me their interfaces.\"")
    print("================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
