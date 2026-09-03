#!/usr/bin/env python3
"""Local raster-to-SVG vectorization for Sci-PPT.

No remote API, key, upload, or credit system is used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def contour_to_path(contour, epsilon_ratio: float) -> str | None:
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, max(0.5, epsilon_ratio * perimeter), True).reshape(-1, 2)
    if len(approx) < 3:
        return None
    parts = [f"M {int(approx[0][0])} {int(approx[0][1])}"]
    parts += [f"L {int(x)} {int(y)}" for x, y in approx[1:]]
    parts.append("Z")
    return " ".join(parts)


def vectorize(
    input_image: Path,
    output_svg: Path,
    colors: int = 10,
    max_paths: int = 600,
    min_area_ratio: float = 0.00015,
    epsilon_ratio: float = 0.003,
):
    image = cv2.imread(str(input_image), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(input_image)

    height, width = image.shape[:2]
    pixels = image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.8)
    _, labels, centers = cv2.kmeans(
        pixels,
        int(colors),
        None,
        criteria,
        3,
        cv2.KMEANS_PP_CENTERS,
    )
    labels = labels.reshape(height, width)
    minimum_area = height * width * float(min_area_ratio)
    found = []

    for color_index in range(len(centers)):
        mask = (labels == color_index).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = abs(cv2.contourArea(contour))
            if area < minimum_area or area > height * width * 0.995:
                continue
            path_data = contour_to_path(contour, epsilon_ratio)
            if path_data:
                found.append((area, color_index, path_data))

    # Large regions first gives a useful background-to-foreground approximation.
    found.sort(key=lambda item: item[0], reverse=True)
    found = found[: int(max_paths)]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
    ]
    for index, (area, color_index, path_data) in enumerate(found):
        b, g, r = [int(v) for v in centers[color_index]]
        lines.append(
            f'<path id="sci_path_{index:05d}" d="{path_data}" '
            f'fill="#{r:02X}{g:02X}{b:02X}" stroke="none" data-area="{area:.3f}"/>'
        )
    lines.append("</svg>")

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    output_svg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not found:
        raise RuntimeError("Local vectorizer produced no paths")

    return {
        "ok": True,
        "paths": len(found),
        "width": width,
        "height": height,
        "output_svg": str(output_svg),
    }


def main():
    parser = argparse.ArgumentParser(description="Local raster-to-SVG vectorizer for Sci-PPT.")
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--colors", type=int, default=10)
    parser.add_argument("--max-paths", type=int, default=600)
    parser.add_argument("--min-area-ratio", type=float, default=0.00015)
    parser.add_argument("--epsilon-ratio", type=float, default=0.003)
    args = parser.parse_args()
    print(
        json.dumps(
            vectorize(
                args.input_image.resolve(),
                args.output_svg.resolve(),
                args.colors,
                args.max_paths,
                args.min_area_ratio,
                args.epsilon_ratio,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
