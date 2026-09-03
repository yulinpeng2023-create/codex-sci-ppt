#!/usr/bin/env python3
"""Validate Sci-PPT vector SVG structure before PowerPoint rendering.

The validation contract follows the same core idea as the MIT-licensed
Cell_ppt validator: no raster fallback in the master SVG, valid viewBox,
and stable editable vector/text content. See THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

VECTOR_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text"}
FORBIDDEN_TAGS = {"image", "foreignObject", "script", "filter", "mask", "clipPath"}
NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def audit(svg_path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    counts: Counter[str] = Counter()
    ids: list[str] = []

    try:
        root = ET.fromstring(svg_path.read_bytes())
    except (OSError, ET.ParseError) as exc:
        return {"status": "FAIL", "errors": [str(exc)], "warnings": [], "counts": {}}

    if local_name(root.tag) != "svg":
        errors.append("Root element is not <svg>.")

    raw_viewbox = root.get("viewBox", "")
    values = [float(value) for value in NUMBER_RE.findall(raw_viewbox)]
    if (
        len(values) != 4
        or not all(math.isfinite(value) for value in values)
        or values[2] <= 0
        or values[3] <= 0
    ):
        errors.append("A finite positive four-number viewBox is required.")

    for element in root.iter():
        tag = local_name(element.tag)
        counts[tag] += 1
        if tag in FORBIDDEN_TAGS:
            errors.append(f"Forbidden <{tag}> element.")
        if tag in VECTOR_TAGS:
            element_id = element.get("id")
            if element_id:
                ids.append(element_id)
            else:
                warnings.append(f"<{tag}> lacks stable id")

    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append("Duplicate IDs: " + ", ".join(duplicate_ids[:10]))

    if sum(counts[tag] for tag in VECTOR_TAGS) == 0:
        errors.append("No editable vector/text elements found.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "counts": dict(counts),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.svg.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
