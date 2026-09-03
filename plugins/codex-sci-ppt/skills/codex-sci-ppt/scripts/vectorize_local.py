#!/usr/bin/env python3
"""Local raster-to-SVG vectorization for Codex Sci-PPT.

No remote API, key, upload, or credit system is used. The output deliberately
stays within the downstream Cell-PPT-compatible SVG subset.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def contour_points(contour, epsilon_ratio: float) -> np.ndarray:
    perimeter = cv2.arcLength(contour, True)
    return cv2.approxPolyDP(
        contour,
        max(0.5, epsilon_ratio * perimeter),
        True,
    ).reshape(-1, 2)


def points_to_subpath(points: np.ndarray) -> str | None:
    if len(points) < 3:
        return None
    parts = [f"M {int(points[0][0])} {int(points[0][1])}"]
    parts += [f"L {int(x)} {int(y)}" for x, y in points[1:]]
    parts.append("Z")
    return " ".join(parts)


def contour_path_with_holes(contours, hierarchy, index: int, epsilon_ratio: float) -> str | None:
    outer = points_to_subpath(contour_points(contours[index], epsilon_ratio))
    if not outer:
        return None
    parts = [outer]
    child = int(hierarchy[index][2])
    while child >= 0:
        hole = points_to_subpath(contour_points(contours[child], epsilon_ratio))
        if hole:
            parts.append(hole)
        child = int(hierarchy[child][0])
    return " ".join(parts)


def is_simple_ellipse(contour, hierarchy_row, area: float) -> bool:
    if int(hierarchy_row[2]) >= 0 or len(contour) < 5:
        return False
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return False
    circularity = 4.0 * math.pi * area / (perimeter * perimeter)
    return circularity >= 0.78


def border_cluster(labels: np.ndarray) -> int:
    border = np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    values, counts = np.unique(border, return_counts=True)
    return int(values[int(np.argmax(counts))])


def vectorize(
    input_image: Path,
    output_svg: Path,
    colors: int = 10,
    max_paths: int = 600,
    min_area_ratio: float = 0.00015,
    epsilon_ratio: float = 0.003,
    include_background: bool = True,
):
    source = cv2.imread(str(input_image), cv2.IMREAD_UNCHANGED)
    if source is None:
        raise FileNotFoundError(input_image)

    had_alpha = source.ndim == 3 and source.shape[2] == 4
    if had_alpha:
        alpha = source[:, :, 3:4].astype(np.float32) / 255.0
        bgr = source[:, :, :3].astype(np.float32)
        source = (bgr * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)
    elif source.ndim == 2:
        source = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
    elif source.shape[2] != 3:
        raise ValueError("unsupported image channel layout")

    height, width = source.shape[:2]
    if height < 2 or width < 2:
        raise ValueError("input image is too small")
    colors = max(2, min(32, int(colors)))
    max_paths = max(1, int(max_paths))

    # LAB clustering is more perceptually stable than raw BGR clustering for
    # flat scientific diagrams. The center colors written to SVG are still
    # reconstructed in ordinary sRGB/BGR space.
    lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.6)
    cv2.setRNGSeed(0)
    _, labels_flat, centers_lab = cv2.kmeans(
        pixels, colors, None, criteria, 5, cv2.KMEANS_PP_CENTERS
    )
    labels = labels_flat.reshape(height, width)
    centers_lab_u8 = np.clip(centers_lab, 0, 255).astype(np.uint8).reshape(1, -1, 3)
    centers_bgr = cv2.cvtColor(centers_lab_u8, cv2.COLOR_LAB2BGR).reshape(-1, 3)

    minimum_area = height * width * float(min_area_ratio)
    background_index = border_cluster(labels)
    found: list[dict] = []

    for color_index in range(len(centers_bgr)):
        mask = (labels == color_index).astype(np.uint8) * 255
        # Remove isolated 1-pixel quantization noise without erasing meaningful
        # boundaries. This is intentionally mild.
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        contours, raw_hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS)
        if raw_hierarchy is None:
            continue
        hierarchy = raw_hierarchy[0]
        for index, contour in enumerate(contours):
            if int(hierarchy[index][3]) >= 0:
                continue
            area = abs(cv2.contourArea(contour))
            if area < minimum_area:
                continue
            # Background is emitted once as an explicit full-canvas rectangle.
            if color_index == background_index and area > height * width * 0.70:
                continue

            b, g, r = [int(v) for v in centers_bgr[color_index]]
            item = {
                "area": float(area),
                "color_index": int(color_index),
                "fill": f"#{r:02X}{g:02X}{b:02X}",
            }
            if is_simple_ellipse(contour, hierarchy[index], area):
                (cx, cy), (major, minor), angle = cv2.fitEllipse(contour)
                # SVG ellipse cannot carry a rotation without transform; the
                # geometry cache supports transforms, so keep the fitted angle.
                item.update({
                    "kind": "ellipse",
                    "cx": float(cx), "cy": float(cy),
                    "rx": float(major) / 2.0, "ry": float(minor) / 2.0,
                    "rotation": float(angle),
                })
            else:
                path_data = contour_path_with_holes(contours, hierarchy, index, epsilon_ratio)
                if not path_data:
                    continue
                item.update({"kind": "path", "d": path_data})
            found.append(item)

    # Large regions first approximates the source's background-to-foreground
    # paint order, matching the downstream literal-order contract.
    found.sort(key=lambda item: item["area"], reverse=True)
    found = found[:max_paths]

    bg_b, bg_g, bg_r = [int(v) for v in centers_bgr[background_index]]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
    ]
    created = 0
    if include_background and not had_alpha:
        lines.append(
            f'<rect id="local_background" x="0" y="0" width="{width}" height="{height}" '
            f'fill="#{bg_r:02X}{bg_g:02X}{bg_b:02X}" stroke="none"/>'
        )
        created += 1

    for index, item in enumerate(found):
        element_id = f"local_path_{index:05d}"
        if item["kind"] == "ellipse":
            transform = ""
            if abs(item["rotation"]) > 0.5:
                transform = f' transform="rotate({item["rotation"]:.4f} {item["cx"]:.4f} {item["cy"]:.4f})"'
            lines.append(
                f'<ellipse id="{element_id}" cx="{item["cx"]:.4f}" cy="{item["cy"]:.4f}" '
                f'rx="{item["rx"]:.4f}" ry="{item["ry"]:.4f}" fill="{item["fill"]}" '
                f'stroke="none"{transform}/>'
            )
        else:
            lines.append(
                f'<path id="{element_id}" d="{item["d"]}" fill="{item["fill"]}" '
                f'fill-rule="evenodd" stroke="none"/>'
            )
        created += 1
    lines.append("</svg>")

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    output_svg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if created == 0:
        raise RuntimeError("Local vectorizer produced no vector elements")

    return {
        "ok": True,
        "paths": len(found),
        "vector_elements": created,
        "width": width,
        "height": height,
        "colors": colors,
        "background_cluster": background_index,
        "output_svg": str(output_svg),
    }


def main():
    parser = argparse.ArgumentParser(description="Local raster-to-SVG vectorizer for Codex Sci-PPT.")
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--colors", type=int, default=10)
    parser.add_argument("--max-paths", type=int, default=600)
    parser.add_argument("--min-area-ratio", type=float, default=0.00015)
    parser.add_argument("--epsilon-ratio", type=float, default=0.003)
    parser.add_argument("--no-background", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vectorize(
        args.input_image.resolve(), args.output_svg.resolve(), args.colors,
        args.max_paths, args.min_area_ratio, args.epsilon_ratio,
        include_background=not args.no_background,
    ), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
