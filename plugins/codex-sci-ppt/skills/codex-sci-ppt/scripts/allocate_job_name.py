#!/usr/bin/env python3
"""Allocate the next codexscipptN job name under an output root."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERN = re.compile(r"^codexscippt(\d+)$")


def allocate(root: Path) -> str:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    highest = 0
    for child in root.iterdir():
        if not child.is_dir():
            continue
        match = PATTERN.match(child.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"codexscippt{highest + 1}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(allocate(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
