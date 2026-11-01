# Contributing

Contributions are welcome, especially fixes that improve safe behavior across operating systems and hardware types.

## Development setup

Use Python 3.11 or newer:

```bash
python -m venv .venv
python -m pip install -e ".[all,dev]"
python -m pytest -q
python -m ruff check src tests
```

For changes to MCP tools or protocol handling, also exercise the server with the official MCP Inspector CLI. For adapter changes, add tests using mocks or the built-in simulator; physical devices must never be required by the ordinary test suite.

## Pull requests

- Explain the behavior change, supported transports/OSes, and any permission or data-retention effects.
- Add or update tests for changed behavior.
- Keep optional transport imports inside the adapter so missing device libraries do not prevent server startup.
- Preserve per-device identity and return per-target failures instead of silently dropping errors.
- Never commit local databases, raw device payloads, credentials, pairing codes, or private device identifiers.
- Update README and CHANGELOG when user-visible behavior changes.

By submitting a contribution, you agree that it may be distributed under the repository's MIT license.
