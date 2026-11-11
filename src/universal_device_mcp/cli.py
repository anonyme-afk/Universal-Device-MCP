"""Command-line interface for Universal Device MCP."""

from __future__ import annotations

import argparse

from .adapters import (
    ADBAdapter,
    BluetoothAdapter,
    HIDAdapter,
    IOSAdapter,
    NetworkAdapter,
    SerialAdapter,
    USBAdapter,
)
from .adapters.base import Adapter

DEFAULT_ADAPTERS: list[type[Adapter]] = [
    USBAdapter,
    HIDAdapter,
    SerialAdapter,
    BluetoothAdapter,
    ADBAdapter,
    NetworkAdapter,
    IOSAdapter,
]
_build_service = ...

_json_print = ...


# All command functions here


def cmd_status(args):
    """Show server status and connected devices."""
    ...


def cmd_discover(args):
    """Discover devices on available adapters."""
    ...


def cmd_list(args):
    """List available devices."""
    ...


def cmd_inspect(args):
    """Inspect a known device's interfaces and capabilities."""
    ...


def cmd_communicate(args):
    """Communicate with a device through one of its interfaces."""
    ...


def cmd_policy(args):
    """Show access policy and mode settings."""
    ...


def cmd_groups(args):
    """Show device groups and their policies."""
    ...


def cmd_version(args):
    """Show version information."""
    ...


def cmd_memory(args):
    """Show memory store statistics."""
    ...


def cmd_approvals(args):
    """Show pending destructive operation approvals."""
    ...


def cmd_remote(args):
    """Show remote node registration status."""
    ...


def cmd_server(args):
    """Start the MCP server."""
    ...


def cmd_configure(args):
    """Configure MCP clients (Claude, Cursor, Cline, etc.)."""
    ...


def _add_common_discover_args(parser):
    """Add common arguments to discover subparsers."""
    ...


def build_parser():
    """Build and return the argument parser."""

    parser = argparse.ArgumentParser(
        prog="universal-device-mcp",
        description="Universal Device MCP - CLI tool for device management",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"universal-device-mcp {__import__('universal_device_mcp').__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    p_status = subparsers.add_parser("status", help="Show server status and connected devices")
    p_status.set_defaults(func=cmd_status)

    # Discover command
    p_discover = subparsers.add_parser("discover", help="Discover devices on available adapters")
    p_discover.add_argument(
        "--adapter",
        choices=["usb", "serial", "bluetooth", "network", "hid", "ios", "adb", "simulator"],
        default="all",
        help="Adapter to use for discovery (default: all)",
    )
    p_discover.add_argument(
        "--filter",
        help="Filter devices by type or identifier",
    )
    p_discover.set_defaults(func=cmd_discover)

    # List command
    p_list = subparsers.add_parser("list", help="List available devices")
    p_list.set_defaults(func=cmd_list)

    # Inspect command
    p_inspect = subparsers.add_parser(
        "inspect", help="Inspect a known device's interfaces and capabilities"
    )
    p_inspect.add_argument("device_id", help="Device identifier")
    p_inspect.add_argument(
        "--interface",
        help="Specific interface to inspect",
    )
    p_inspect.add_argument(
        "--simulator",
        action="store_true",
        help="Include the simulator adapter",
    )
    p_inspect.set_defaults(func=cmd_inspect)

    # Communicate command
    p_comm = subparsers.add_parser(
        "communicate", help="Communicate with a device through one of its interfaces"
    )
    p_comm.add_argument("device_id", help="Device identifier")
    p_comm.add_argument("interface_id", help="Interface identifier")
    p_comm.add_argument(
        "operation",
        choices=["read", "receive", "write", "send", "inspect", "communicate", "control_write", "execute"],
        help="Operation to perform",
    )
    p_comm.add_argument(
        "--data-hex",
        help="Hexadecimal payload to send (for write/send/communicate)",
    )
    p_comm.add_argument(
        "--length",
        type=int,
        help="Number of bytes to read (default adapter-specific)",
    )
    p_comm.add_argument(
        "--timeout",
        type=float,
        help="I/O timeout in seconds",
    )
    p_comm.set_defaults(func=cmd_communicate)

    # Policy command
    p_policy = subparsers.add_parser("policy", help="Show access policy and mode settings")
    p_policy.set_defaults(func=cmd_policy)

    # Groups command
    p_groups = subparsers.add_parser("groups", help="Show device groups and their policies")
    p_groups.set_defaults(func=cmd_groups)

    # Version command
    p_version = subparsers.add_parser("version", help="Show version information")
    p_version.set_defaults(func=cmd_version)

    # Memory command
    p_memory = subparsers.add_parser("memory", help="Show memory store statistics")
    p_memory.add_argument(
        "--detail",
        choices=["summary", "full"],
        default="summary",
        help="Level of detail (default: summary)",
    )
    p_memory.set_defaults(func=cmd_memory)

    # Approvals command
    p_approvals = subparsers.add_parser(
        "approvals", help="Show pending destructive operation approvals"
    )
    p_approvals.set_defaults(func=cmd_approvals)

    # Remote command
    p_remote = subparsers.add_parser("remote", help="Show remote node registration status")
    p_remote.set_defaults(func=cmd_remote)

    # Server command
    p_server = subparsers.add_parser(
        "server", help="Start the MCP server"
    )
    p_server.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host address (default: 127.0.0.1)",
    )
    p_server.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Bind port (default: 9000)",
    )
    p_server.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    p_server.set_defaults(func=cmd_server)

    # Configure command
    p_configure = subparsers.add_parser(
        "configure", help="Configure MCP clients (Claude, Cursor, Cline, etc.)"
    )
    p_configure.set_defaults(func=cmd_configure)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``universal-device-mcp`` command.

    Parses the command line and dispatches to the requested sub-command.
    When no sub-command is given, the MCP server is launched.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from universal_device_mcp import __version__

        print(f"universal-device-mcp {__version__}")
        return 0

    if not getattr(args, "command", None):
        return cmd_server(args)

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1

    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())