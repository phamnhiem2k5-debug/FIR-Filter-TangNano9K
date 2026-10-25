"""Compare a captured FIR output against a software reference, sample by sample.

Added during repository packaging. Each nonempty line must be one hexadecimal word.
Both 41-bit words and the RTL's zero-padded six-byte words are accepted.
This utility reads files; it does not communicate with UART hardware.
"""

import argparse
from pathlib import Path
import sys


def read_signed41(path):
    values = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        word = line.strip()
        if not word:
            continue
        try:
            raw = int(word, 16)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: expected one hexadecimal word") from exc
        if not 0 <= raw < (1 << 48):
            raise ValueError(f"{path}:{line_number}: word must fit in 48 unsigned bits")
        v = raw & ((1 << 41) - 1)
        values.append(v - (1 << 41) if v & (1 << 40) else v)
    if not values:
        raise ValueError(f"{path}: no samples found")
    return values


def compare(captured, reference):
    actual = read_signed41(captured)
    expected = read_signed41(reference)
    if len(actual) != len(expected):
        print(f"FAIL: sample count differs: captured={len(actual)}, reference={len(expected)}")
        return 1
    differences = [a - b for a, b in zip(actual, expected)]
    mismatch = sum(d != 0 for d in differences)
    maximum = max(abs(d) for d in differences)
    # Keep integer arithmetic until the final normalized display.
    mse_raw = sum(d * d for d in differences) / len(differences)
    print(f"Samples: {len(actual)}")
    print(f"Mismatches: {mismatch}")
    print(f"Max absolute error (raw integer units): {maximum}")
    print(f"MSE (raw integer units squared): {mse_raw:.12g}")
    print(f"MSE (normalized by 2^30 before comparison): {mse_raw / (1 << 60):.12g}")
    print("PASS" if mismatch == 0 else "FAIL")
    return int(mismatch != 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captured", type=Path)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    try:
        return compare(args.captured, args.reference)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
