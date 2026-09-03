#!/usr/bin/env python3
"""Merge a text manifest into a Sci-PPT master SVG as live editable text.

Compatible in spirit with the MIT-licensed Cell_ppt live-text stage.
See THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def finite(value, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def parse_viewbox(root: ET.Element):
    parts = [float(item) for item in re.split(r"[\s,]+", root.get("viewBox", "").strip()) if item]
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise ValueError("valid SVG viewBox required")
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-svg", required=True, type=Path)
    parser.add_argument("--text-manifest", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    args = parser.parse_args()

    tree = ET.parse(args.input_svg)
    root = tree.getroot()
    view_x, view_y, view_w, view_h = parse_viewbox(root)
    manifest = json.loads(args.text_manifest.read_text(encoding="utf-8-sig"))
    items = manifest.get("text_elements", [])
    if not isinstance(items, list):
        raise ValueError("text_elements must be an array")

    existing_ids = {node.get("id") for node in root.iter() if node.get("id")}
    additions = []
    for index, item in enumerate(items):
        content = str(item.get("content", item.get("text", "")))
        element_id = str(item.get("id", f"text_{index:04d}"))
        if element_id in existing_ids:
            raise ValueError(f"duplicate SVG id: {element_id}")

        normalized = item.get("coordinate_space", "normalized") == "normalized"
        x = finite(item.get("x", 0), "x")
        y = finite(item.get("y", 0), "y")
        if normalized:
            x = view_x + x * view_w
            y = view_y + y * view_h

        font_size = finite(item.get("font_size", 12), "font_size")
        if normalized and item.get("font_size_space") == "normalized":
            font_size *= view_h

        attrs = {
            "id": element_id,
            "x": f"{x:g}",
            "y": f"{y:g}",
            "fill": str(item.get("fill", "#000000")),
            "font-family": str(item.get("font_family", "Arial")),
            "font-size": f"{font_size:g}",
            "font-weight": str(item.get("font_weight", "normal")),
            "font-style": str(item.get("font_style", "normal")),
            "text-anchor": str(item.get("text_anchor", "start")),
        }
        rotation = finite(item.get("rotation", 0), "rotation")
        if rotation:
            attrs["transform"] = f"rotate({rotation:g} {x:g} {y:g})"

        element = ET.Element(f"{{{SVG_NS}}}text", attrs)
        element.text = content
        additions.append((int(item.get("paint_order", len(root))), element))

    for paint_order, element in sorted(additions, key=lambda pair: pair[0]):
        root.insert(max(0, min(paint_order, len(root))), element)

    args.output_svg.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output_svg, encoding="utf-8", xml_declaration=True)
    print(
        json.dumps(
            {
                "ok": True,
                "live_text_count": len(additions),
                "output_svg": str(args.output_svg.resolve()),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
