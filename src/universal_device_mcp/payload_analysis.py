"""Conservative, transport-independent analysis of byte samples."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any


def analyze_payload(data_hex: str, baseline_hex: str | None = None) -> dict[str, Any]:
    """Describe common byte interpretations without asserting a proprietary protocol."""
    data = bytes.fromhex(data_hex)
    if len(data) > 1_048_576:
        raise ValueError("Payload analysis is limited to 1 MiB")
    printable_ratio = (sum(32 <= value < 127 or value in (9, 10, 13) for value in data) / len(data)) if data else 0.0
    result: dict[str, Any] = {
        "length": len(data), "hex": data.hex(), "entropy_bits_per_byte": _entropy(data),
        "ascii_printable_ratio": printable_ratio, "hypotheses": [], "confidence": "hypothesis",
    }
    try:
        result["utf8_text"] = data.decode("utf-8")
    except UnicodeDecodeError:
        result["utf8_text"] = None
    if data:
        result["integer_views"] = {
            "uint8_first_16": list(data[:16]),
            "uint16_le_first_16": [int.from_bytes(data[i:i + 2], "little") for i in range(0, min(len(data), 32) - 1, 2)],
            "uint16_be_first_16": [int.from_bytes(data[i:i + 2], "big") for i in range(0, min(len(data), 32) - 1, 2)],
            "uint32_le_first_16": [int.from_bytes(data[i:i + 4], "little") for i in range(0, min(len(data), 64) - 3, 4)],
            "uint32_be_first_16": [int.from_bytes(data[i:i + 4], "big") for i in range(0, min(len(data), 64) - 3, 4)],
        }
        if printable_ratio >= 0.85:
            result["hypotheses"].append("Mostly printable text; inspect delimiters, line endings and field boundaries.")
        if len(data) >= 4 and data[0] == 0x7E:
            result["hypotheses"].append("Starts with 0x7E, a byte sometimes used as a frame delimiter; this alone does not identify a protocol.")
        if len(data) >= 4 and len(set(data)) <= 2:
            result["hypotheses"].append("Low byte diversity; this may be padding, a repeated status, or a short sample.")
    if baseline_hex is not None:
        baseline = bytes.fromhex(baseline_hex)
        if len(baseline) > 1_048_576:
            raise ValueError("Baseline analysis is limited to 1 MiB")
        shared_prefix = 0
        for left, right in zip(data, baseline):
            if left != right:
                break
            shared_prefix += 1
        shared_suffix = 0
        for left, right in zip(reversed(data[shared_prefix:]), reversed(baseline[shared_prefix:])):
            if left != right:
                break
            shared_suffix += 1
        differences = [{"offset": index, "baseline": baseline[index], "sample": data[index]}
                       for index in range(min(len(data), len(baseline))) if data[index] != baseline[index]]
        result["comparison"] = {
            "baseline_length": len(baseline), "length_delta": len(data) - len(baseline),
            "common_prefix_bytes": shared_prefix, "common_suffix_bytes": shared_suffix,
            "changed_offsets": differences[:256], "truncated_changed_offsets": len(differences) > 256,
        }
    return result


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())
