#!/usr/bin/env python3
"""Locally remove known text regions before raster-to-vector tracing.

The text manifest remains the source of live editable text. When bounding boxes
are present, this script inpaints those raster regions so the traced SVG does
not also contain text-shaped geometry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def resolve_box(item: dict, width: int, height: int):
    normalized = item.get("coordinate_space", "normalized") == "normalized"
    box = item.get("bbox")
    if isinstance(box, (list, tuple)) and len(box) == 4:
        x, y, w, h = map(float, box)
    elif all(key in item for key in ("x", "y", "width", "height")):
        x, y, w, h = map(float, (item["x"], item["y"], item["width"], item["height"]))
    else:
        return None
    if normalized:
        x, w = x * width, w * width
        y, h = y * height, h * height
    return x, y, w, h


def clean(input_image: Path, manifest_path: Path, output_image: Path, padding: int = 3):
    image = cv2.imread(str(input_image), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(input_image)
    height, width = image.shape[:2]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != "1.0":
        raise ValueError("text manifest schema_version must be 1.0")
    items = manifest.get("text_elements")
    if not isinstance(items, list):
        raise ValueError("text_elements must be an array")

    mask = np.zeros((height, width), dtype=np.uint8)
    used = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        box = resolve_box(item, width, height)
        if box is None:
            continue
        x, y, w, h = box
        x1 = max(0, int(round(x)) - padding)
        y1 = max(0, int(round(y)) - padding)
        x2 = min(width, int(round(x + w)) + padding)
        y2 = min(height, int(round(y + h)) + padding)
        if x2 <= x1 or y2 <= y1:
            continue
        mask[y1:y2, x1:x2] = 255
        used += 1

    if used:
        cleaned = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
    else:
        cleaned = image
    output_image.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_image), cleaned):
        raise RuntimeError(f"failed to write {output_image}")
    return {"ok": True, "regions_removed": used, "output_image": str(output_image)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--text-manifest", required=True, type=Path)
    parser.add_argument("--output-image", required=True, type=Path)
    parser.add_argument("--padding", type=int, default=3)
    args = parser.parse_args()
    result = clean(
        args.input_image.resolve(), args.text_manifest.resolve(),
        args.output_image.resolve(), max(0, args.padding),
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
