#!/usr/bin/env python3
"""Universal Device MCP — One-Command Quickstart & Auto-Configuration.

Usage:
    python quickstart.py [options]

Options:
    --simulator       Enable virtual simulated devices (ideal for testing without hardware)
    --print-json      Only output the MCP JSON snippet (no config files modified)
    --client <name>   Configure a specific client (claude-desktop, cursor, antigravity, cline...)
    --dry-run         Simulate setup without writing files
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def print_banner() -> None:
    print(r"""
========================================================================
   _   _       _                            _   ____             _          
  | | | |_ __ (_)_   _____ _ __ ___  __ _  | | |  _ \  _____   _(_) ___ ___ 
  | | | | '_ \| \ \ / / _ \ '__/ __|/ _` | | | | | | |/ _ \ \ / / |/ __/ _ \
  | |_| | | | | |\ V /  __/ |  \__ \ (_| | | | | |_| |  __/\ V /| | (_|  __/
   \___/|_| |_|_| \_/ \___|_|  |___/\__,_| |_| |____/ \___| \_/ |_|\___\___|
                            UNIVERSAL DEVICE MCP
========================================================================
""")


def check_python_version() -> None:
    if sys.version_info < (3, 11):
        print(f"[x] Error: Python 3.11 or newer is required. Found: Python {sys.version.split()[0]}", file=sys.stderr)
        print("    Please install Python 3.11+ from https://www.python.org/downloads/", file=sys.stderr)
        sys.exit(1)


def get_venv_python(project_root: Path) -> Path:
    """Return the path to the python binary inside .venv."""
    if sys.platform.startswith("win"):
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def setup_virtualenv(project_root: Path) -> Path:
    """Create .venv if not already running in one, and return python path."""
    in_venv = sys.prefix != sys.base_prefix
    venv_python = get_venv_python(project_root)

    if in_venv:
        print(f"[✓] Using current active environment: {sys.prefix}")
        return Path(sys.executable)

    if not venv_python.exists():
        print(f"[+] Creating virtual environment in {project_root / '.venv'}...")
        subprocess.run([sys.executable, "-m", "venv", str(project_root / ".venv")], check=True)
        print("[✓] Virtual environment created successfully.")
    else:
        print(f"[✓] Found existing virtual environment: {venv_python}")

    return venv_python


def install_dependencies(venv_python: Path, project_root: Path) -> None:
    """Install the universal-device-mcp package and hardware adapters."""
    print("[+] Installing dependencies and hardware adapters...")

    # Upgrade pip quietly
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        check=False,
    )

    # Try full install with all hardware extras
    cmd_all = [str(venv_python), "-m", "pip", "install", "-e", ".[all]"]
    proc = subprocess.run(cmd_all, cwd=project_root)

    if proc.returncode != 0:
        print("[!] Note: Installing some C-compiled extras failed (likely missing build tools).")
        print("[+] Falling back to core package and pre-compiled pure-Python adapters...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-e", "."], cwd=project_root, check=True)
        # Attempt individual standard wheels that don't need compilation
        for extra_pkg in ["pyusb", "pyserial", "bleak", "zeroconf"]:
            subprocess.run([str(venv_python), "-m", "pip", "install", extra_pkg, "--quiet"], check=False)

    print("[✓] Universal Device MCP installed successfully.")


def run_configuration(venv_python: Path, project_root: Path, extra_args: list[str]) -> None:
    """Invoke the auto-configurator."""
    config_cmd = [
        str(venv_python),
        "-m",
        "universal_device_mcp.configure",
        "--python",
        str(venv_python.resolve()),
    ] + extra_args

    # Add src to PYTHONPATH so module is always importable even before install
    env = os.environ.copy()
    src_dir = str((project_root / "src").resolve())
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{env.get('PYTHONPATH', '')}"

    subprocess.run(config_cmd, cwd=project_root, env=env, check=True)


def main() -> None:
    if "--print-json" not in sys.argv:
        print_banner()
    check_python_version()

    project_root = Path(__file__).resolve().parent

    extra_args: list[str] = []
    if "--simulator" in sys.argv:
        extra_args.append("--enable-simulator")
    if "--print-json" in sys.argv:
        extra_args.append("--print-json")
    if "--dry-run" in sys.argv:
        extra_args.append("--dry-run")
    if "--client" in sys.argv:
        idx = sys.argv.index("--client")
        if idx + 1 < len(sys.argv):
            extra_args.extend(["--client", sys.argv[idx + 1]])

    # If --print-json or --dry-run is requested, avoid installing packages
    if "--print-json" in sys.argv:
        venv_python = get_venv_python(project_root)
        python_to_use = venv_python if venv_python.exists() else Path(sys.executable)
        run_configuration(python_to_use, project_root, extra_args)
        return

    # 1. Setup virtual environment
    venv_python = setup_virtualenv(project_root)

    # 2. Install dependencies (unless dry-run or skip-install)
    if "--dry-run" not in sys.argv and "--skip-install" not in sys.argv:
        install_dependencies(venv_python, project_root)
    else:
        print("[i] Skipping installation (--dry-run / --skip-install active).")

    # 3. Configure AI clients automatically
    print("\n[+] Configuring AI Agent clients...")
    run_configuration(venv_python, project_root, extra_args)

    print("\n========================================================================")
    print("   READY TO DISCOVER HARDWARE!")
    print("========================================================================")
    print("1. Plug any device into your computer (USB, Serial, Bluetooth, Phone...).")
    print("2. Open your configured AI client (Claude, Cursor, Antigravity, Cline...).")
    print("3. In chat, simply ask:")
    print('     "Discover connected devices and show me their interfaces."')
    print("========================================================================\n")


if __name__ == "__main__":
    main()
