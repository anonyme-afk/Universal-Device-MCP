"""Expose individual pytest failures as GitHub Actions check annotations."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def escape_property(value: str) -> str:
    return (value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            .replace(":", "%3A").replace(",", "%2C"))


def escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    report = Path(sys.argv[1])
    if not report.is_file():
        print(f"Pytest did not create a report at {report}; inspect the preceding setup step.")
        return 0
    root = ET.parse(report).getroot()
    failures = 0
    for case in root.iter("testcase"):
        failure = case.find("failure")
        if failure is None:
            failure = case.find("error")
        if failure is None:
            continue
        failures += 1
        path = case.get("file", "")
        title = escape_property(case.get("name", "pytest failure"))
        detail = escape_data(failure.get("message", "") + "\n" + (failure.text or ""))
        location = f"file={escape_property(path)}," if path else ""
        print(f"::error {location}title={title}::{detail}")
    print(f"Pytest failure annotations emitted: {failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
