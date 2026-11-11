# Client Setup Guide

## 1-Prompt Agentic Setup (Recommended — Zero Scripts, 100% Transparent)

If you are using an AI coding assistant (Claude Code, Cursor, Google Antigravity, VS Code / Cline, Roo Code, Windsurf, Codex), you do not need to run any local scripts or manually edit configuration files.

Simply copy and paste this prompt directly into your agent:

```text
Please set up and connect Universal Device MCP in this workspace:
1. Ensure Python 3.11+ is available, create a local virtual environment (.venv), and install this repository with hardware extras (pip install -e ".[all]").
2. Register the MCP server as "universal-device" in your MCP client configuration so you can use its tools.
3. Test the connection by discovering all connected hardware devices and displaying their available interfaces.
```

Your agent will inspect the environment, set up the server transparently with full user visibility, register the MCP entry, and immediately discover your connected devices.

---

## Alternative: Fast 1-Step Setup (CLI / Scripts)

If you prefer to run a local setup script:

```bash
git clone https://github.com/anonyme-afk/Universal-Device-MCP.git
cd Universal-Device-MCP
python quickstart.py
```

- **Windows:** Double-click `setup.bat` or run `.\setup.bat` in a terminal.
- **macOS / Linux:** Run `chmod +x setup.sh && ./setup.sh` in a terminal.

**What the script does automatically:**
1. Verifies Python 3.11+ and creates a dedicated `.venv` virtual environment.
2. Installs `universal-device-mcp` with all hardware adapters (USB, Serial, Bluetooth, mDNS, ADB, iOS).
3. Automatically scans your computer for installed AI clients (**Claude Desktop**, **Cursor**, **Google Antigravity**, **VS Code / Cline**, **Roo Code**, **Windsurf**) and registers Universal Device MCP into their configuration files with safe backups.

---

## Alternative: Zero-Install via `uvx` (No git clone needed)

Use the same local server command with any client that supports MCP over `stdio`:

```text
command: uvx
args: --from universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main universal-device-mcp
```

Install `uv` once from its [official installer](https://docs.astral.sh/uv/getting-started/installation/). It installs the supported Python runtime and project dependencies on first launch. You do not need to install Python, Git, or clone this repository. Leave `UDMCP_POLICY` unset for discovery and read operations; hardware-changing operations stay blocked until explicitly authorized in the local policy.

## Claude Code

In a terminal, add the local server for all projects:

```bash
claude mcp add --scope user universal-device -- uvx --from "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main" universal-device-mcp
```

Then run `/mcp` in Claude Code and confirm `universal-device` is connected. You can also import the JSON entry used by Claude Desktop with `claude mcp add-json`.

## Codex

In a terminal, add the server to the Codex CLI/IDE configuration:

```bash
codex mcp add universal-device -- uvx --from "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main" universal-device-mcp
```

Or add this to `~/.codex/config.toml`:

```toml
[mcp_servers.universal_device]
command = "uvx"
args = [
  "--from",
  "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
  "universal-device-mcp"
]
```

Restart the Codex extension/app and check `/mcp` in the Codex TUI.

## Cline

Open Cline's **MCP Servers → Configure MCP Servers** page. Add this entry inside the existing `mcpServers` object:

```json
"universal-device": {
  "command": "uvx",
  "args": [
    "--from",
    "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
    "universal-device-mcp"
  ]
}
```

If you want a local model, choose **Ollama** or **LM Studio** separately in Cline's model settings. Ollama/LM Studio run the model; Cline launches Universal Device MCP and passes it tool calls. See Cline's [local models guide](https://docs.cline.bot/running-models-locally/overview).

## LM Studio

LM Studio can act as the MCP host for local models. Open **Program → Install → Edit mcp.json** and add the same `universal-device` JSON entry above under `mcpServers`. Then enable the server and select a model that supports tool calling. The model and host must both support tool use for MCP calls to work.

## Ollama

Ollama provides local models and function/tool calling, but its model server is not itself the place to add an MCP server configuration. Connect Ollama through an MCP host such as Cline configured to use Ollama, or another MCP-compatible client. LM Studio can host MCP servers directly while running supported local models. Tool-use reliability depends on the model selected.

## Google Antigravity

In Antigravity, open **Agent panel → MCP Servers → Manage MCP Servers → View raw config**. Add the following under the existing `mcpServers` object:

```json
"universal-device": {
  "command": "uvx",
  "args": [
    "--from",
    "universal-device-mcp[all] @ https://github.com/anonyme-afk/Universal-Device-MCP/archive/refs/heads/main.zip#subdirectory=Universal-Device-MCP-main",
    "universal-device-mcp"
  ]
}
```

Save the file, then refresh the MCP server list. Antigravity's global config is `~/.gemini/config/mcp_config.json`; its interface can open the correct file on Windows.

## First use

After restarting the client, ask your agent:

> Find the devices connected to this computer and show me their available interfaces. Do not send any data or change device settings.

If no physical device is connected, temporarily add `"env": { "UDMCP_ENABLE_SIMULATOR": "true" }` to the server entry and restart the client. Ask it to discover the simulator devices. They are virtual examples, not hardware.

To use a real device, first ask for an inspection and a read-only operation. Writes, pairing and command execution require an exact local policy rule; discovery in the app does not grant those permissions. See [the security guide](../SECURITY.md) before allowing device-changing operations.

## Official client guides

- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Codex MCP](https://developers.openai.com/codex/mcp/)
- [Cline MCP](https://github.com/cline/cline/blob/main/docs/mcp/mcp-overview.mdx)
- [Cline local models (Ollama and LM Studio)](https://docs.cline.bot/running-models-locally/overview)
- [LM Studio MCP](https://lmstudio.ai/docs/app/mcp)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Google Antigravity MCP](https://antigravity.google/docs/mcp?tab=ide)
- [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
- [Claude Desktop local MCP](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
- [Cursor MCP](https://docs.cursor.com/context/model-context-protocol)
