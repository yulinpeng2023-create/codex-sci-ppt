#!/usr/bin/env python3
"""Local raster-to-SVG vectorization for Codex Sci-PPT.

The output deliberately stays inside the downstream Cell-PPT-compatible SVG
subset. No remote API, key, upload, credit, or quota system is used.

This v2 tracer is still a deterministic local reconstruction backend, but it
improves the first-generation color-quantization tracer with:
- edge-preserving preprocessing for diagram-like artwork;
- sampled LAB k-means for large inputs;
- merging of near-duplicate palette clusters caused by anti-aliasing;
- transparent-pixel exclusion rather than treating transparency as white art;
- primitive recovery for rectangles and ellipses;
- hole-aware paths and deterministic source ordering;
- reconstruction diagnostics such as palette PSNR and primitive counts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def contour_points(contour: np.ndarray, epsilon_ratio: float) -> np.ndarray:
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


def contour_path_with_holes(
    contours: tuple[np.ndarray, ...] | list[np.ndarray],
    hierarchy: np.ndarray,
    index: int,
    epsilon_ratio: float,
) -> str | None:
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


def active_border_cluster(labels: np.ndarray) -> int:
    border = np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    border = border[border >= 0]
    if border.size:
        values, counts = np.unique(border, return_counts=True)
        return int(values[int(np.argmax(counts))])
    active = labels[labels >= 0]
    if not active.size:
        return 0
    values, counts = np.unique(active, return_counts=True)
    return int(values[int(np.argmax(counts))])


def preprocess(source: np.ndarray, mode: str) -> np.ndarray:
    if mode == "none":
        return source
    if mode == "bilateral":
        # Mild edge-preserving denoising reduces anti-alias palette fragmentation
        # without erasing the hard boundaries typical of scientific diagrams.
        return cv2.bilateralFilter(source, d=5, sigmaColor=28, sigmaSpace=28)
    raise ValueError(f"unsupported preprocess mode: {mode}")


def sample_rows(pixels: np.ndarray, maximum: int, seed: int = 0) -> np.ndarray:
    if len(pixels) <= maximum:
        return pixels
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(pixels), size=maximum, replace=False)
    return pixels[indices]


def assign_nearest_centers(pixels: np.ndarray, centers: np.ndarray, chunk_size: int = 150_000) -> np.ndarray:
    result = np.empty(len(pixels), dtype=np.int32)
    for start in range(0, len(pixels), chunk_size):
        chunk = pixels[start:start + chunk_size].astype(np.float32)
        # Squared Euclidean distance in LAB. The array stays bounded by chunking.
        distances = ((chunk[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        result[start:start + len(chunk)] = np.argmin(distances, axis=1)
    return result


def cluster_lab(
    lab: np.ndarray,
    active_mask: np.ndarray,
    colors: int,
    sample_limit: int,
) -> tuple[np.ndarray, np.ndarray]:
    active_pixels = lab[active_mask].reshape(-1, 3).astype(np.float32)
    if not len(active_pixels):
        raise ValueError("image contains no visible pixels")

    unique_count = len(np.unique(active_pixels.astype(np.uint8), axis=0))
    k = max(1, min(int(colors), unique_count))
    training = sample_rows(active_pixels, max(1_000, int(sample_limit)))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.45)
    cv2.setRNGSeed(0)
    _, _, centers = cv2.kmeans(training, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    active_labels = assign_nearest_centers(active_pixels, centers)

    labels = np.full(active_mask.shape, -1, dtype=np.int32)
    labels[active_mask] = active_labels
    return labels, centers.astype(np.float32)


def merge_close_palette(
    labels: np.ndarray,
    centers_lab: np.ndarray,
    source_bgr: np.ndarray,
    distance_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    count = len(centers_lab)
    if count <= 1 or distance_threshold <= 0:
        palette = np.zeros((count, 3), dtype=np.uint8)
        for index in range(count):
            pixels = source_bgr[labels == index]
            if len(pixels):
                palette[index] = np.rint(pixels.mean(axis=0)).astype(np.uint8)
        return labels, palette

    parent = list(range(count))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first: int, second: int) -> None:
        a, b = find(first), find(second)
        if a != b:
            parent[max(a, b)] = min(a, b)

    threshold_sq = float(distance_threshold) ** 2
    for first in range(count):
        for second in range(first + 1, count):
            distance_sq = float(((centers_lab[first] - centers_lab[second]) ** 2).sum())
            if distance_sq <= threshold_sq:
                union(first, second)

    roots = [find(index) for index in range(count)]
    ordered_roots: list[int] = []
    for root in roots:
        if root not in ordered_roots:
            ordered_roots.append(root)
    root_to_new = {root: index for index, root in enumerate(ordered_roots)}
    old_to_new = np.array([root_to_new[find(index)] for index in range(count)], dtype=np.int32)

    merged = labels.copy()
    active = merged >= 0
    merged[active] = old_to_new[merged[active]]

    palette = np.zeros((len(ordered_roots), 3), dtype=np.uint8)
    for index in range(len(ordered_roots)):
        pixels = source_bgr[merged == index]
        if len(pixels):
            palette[index] = np.rint(pixels.mean(axis=0)).astype(np.uint8)
    return merged, palette


def quantization_metrics(source_bgr: np.ndarray, labels: np.ndarray, palette_bgr: np.ndarray) -> dict:
    active = labels >= 0
    if not active.any():
        return {"palette_psnr_db": 0.0, "palette_mae": 0.0}
    reconstructed = palette_bgr[labels[active]].astype(np.float32)
    original = source_bgr[active].astype(np.float32)
    error = original - reconstructed
    mse = float(np.mean(error * error))
    mae = float(np.mean(np.abs(error)))
    psnr = 99.0 if mse <= 1e-12 else 10.0 * math.log10((255.0 ** 2) / mse)
    return {
        "palette_psnr_db": round(psnr, 3),
        "palette_mae": round(mae, 3),
    }


def child_count(hierarchy: np.ndarray, index: int) -> int:
    count = 0
    child = int(hierarchy[index][2])
    while child >= 0:
        count += 1
        child = int(hierarchy[child][0])
    return count


def fit_axis_rect(contour: np.ndarray, hierarchy_row: np.ndarray, area: float, epsilon_ratio: float):
    if int(hierarchy_row[2]) >= 0:
        return None
    x, y, width, height = cv2.boundingRect(contour)
    if width <= 1 or height <= 1:
        return None
    extent = area / float(width * height)
    if extent < 0.94:
        return None
    approx = contour_points(contour, epsilon_ratio)
    if len(approx) > 6:
        return None
    return {
        "kind": "rect",
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
    }


def fit_simple_ellipse(contour: np.ndarray, hierarchy_row: np.ndarray, area: float):
    if int(hierarchy_row[2]) >= 0 or len(contour) < 5:
        return None
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return None
    circularity = 4.0 * math.pi * area / (perimeter * perimeter)
    if circularity < 0.68:
        return None
    (cx, cy), (axis_one, axis_two), angle = cv2.fitEllipse(contour)
    if axis_one <= 0 or axis_two <= 0:
        return None
    fitted_area = math.pi * axis_one * axis_two / 4.0
    if fitted_area <= 0:
        return None
    area_ratio = area / fitted_area
    if not 0.80 <= area_ratio <= 1.20:
        return None
    return {
        "kind": "ellipse",
        "cx": float(cx),
        "cy": float(cy),
        "rx": float(axis_one) / 2.0,
        "ry": float(axis_two) / 2.0,
        "rotation": float(angle),
    }


def component_item(
    contours,
    hierarchy: np.ndarray,
    index: int,
    area: float,
    fill: str,
    epsilon_ratio: float,
) -> dict | None:
    contour = contours[index]
    rectangle = fit_axis_rect(contour, hierarchy[index], area, epsilon_ratio)
    if rectangle is not None:
        rectangle.update({"area": float(area), "fill": fill})
        return rectangle

    ellipse = fit_simple_ellipse(contour, hierarchy[index], area)
    if ellipse is not None:
        ellipse.update({"area": float(area), "fill": fill})
        return ellipse

    path_data = contour_path_with_holes(contours, hierarchy, index, epsilon_ratio)
    if not path_data:
        return None
    return {
        "kind": "path",
        "area": float(area),
        "fill": fill,
        "d": path_data,
        "holes": child_count(hierarchy, index),
    }


def vectorize(
    input_image: Path,
    output_svg: Path,
    colors: int = 12,
    max_paths: int = 700,
    min_area_ratio: float = 0.00010,
    epsilon_ratio: float = 0.0025,
    include_background: bool = True,
    preprocess_mode: str = "bilateral",
    palette_merge_distance: float = 6.0,
    sample_limit: int = 250_000,
):
    raw = cv2.imread(str(input_image), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FileNotFoundError(input_image)

    had_alpha = raw.ndim == 3 and raw.shape[2] == 4
    if had_alpha:
        alpha_channel = raw[:, :, 3]
        active_mask = alpha_channel > 8
        alpha = alpha_channel[:, :, None].astype(np.float32) / 255.0
        bgr = raw[:, :, :3].astype(np.float32)
        source = np.rint(bgr * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)
    elif raw.ndim == 2:
        source = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
        active_mask = np.ones(raw.shape[:2], dtype=bool)
    elif raw.ndim == 3 and raw.shape[2] == 3:
        source = raw
        active_mask = np.ones(raw.shape[:2], dtype=bool)
    else:
        raise ValueError("unsupported image channel layout")

    height, width = source.shape[:2]
    if height < 2 or width < 2:
        raise ValueError("input image is too small")
    if not active_mask.any():
        raise ValueError("input image is fully transparent")

    colors = max(2, min(32, int(colors)))
    max_paths = max(1, int(max_paths))
    sample_limit = max(10_000, int(sample_limit))

    working = preprocess(source, preprocess_mode)
    lab = cv2.cvtColor(working, cv2.COLOR_BGR2LAB)
    labels, centers_lab = cluster_lab(lab, active_mask, colors, sample_limit)
    labels, palette_bgr = merge_close_palette(
        labels, centers_lab, source, float(palette_merge_distance)
    )

    minimum_area = height * width * float(min_area_ratio)
    background_index = active_border_cluster(labels)
    found: list[dict] = []

    for color_index in range(len(palette_bgr)):
        mask = (labels == color_index).astype(np.uint8) * 255
        contours, raw_hierarchy = cv2.findContours(
            mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS
        )
        if raw_hierarchy is None:
            continue
        hierarchy = raw_hierarchy[0]
        b, g, r = [int(v) for v in palette_bgr[color_index]]
        fill = f"#{r:02X}{g:02X}{b:02X}"

        for index, contour in enumerate(contours):
            if int(hierarchy[index][3]) >= 0:
                continue
            area = abs(cv2.contourArea(contour))
            if area < minimum_area:
                continue
            # A dominant border cluster is emitted once as a clean canvas rect.
            if color_index == background_index and area > height * width * 0.70:
                continue
            item = component_item(contours, hierarchy, index, area, fill, epsilon_ratio)
            if item is not None:
                item["color_index"] = int(color_index)
                found.append(item)

    # Raster segmentation is disjoint. Painting larger components first gives a
    # stable background-to-foreground approximation and minimizes approximation
    # seams when fitted primitives slightly overlap neighboring regions.
    found.sort(key=lambda item: (item["area"], -item["color_index"]), reverse=True)
    found = found[:max_paths]

    bg_b, bg_g, bg_r = [int(v) for v in palette_bgr[background_index]]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
    ]
    created = 0
    primitive_counts = {"rect": 0, "ellipse": 0, "path": 0}

    if include_background and not had_alpha:
        lines.append(
            f'<rect id="local_background" x="0" y="0" width="{width}" height="{height}" '
            f'fill="#{bg_r:02X}{bg_g:02X}{bg_b:02X}" stroke="none"/>'
        )
        created += 1
        primitive_counts["rect"] += 1

    for index, item in enumerate(found):
        element_id = f"local_path_{index:05d}"
        if item["kind"] == "rect":
            lines.append(
                f'<rect id="{element_id}" x="{item["x"]:.4f}" y="{item["y"]:.4f}" '
                f'width="{item["width"]:.4f}" height="{item["height"]:.4f}" '
                f'fill="{item["fill"]}" stroke="none"/>'
            )
        elif item["kind"] == "ellipse":
            transform = ""
            if abs(item["rotation"]) > 0.5:
                transform = (
                    f' transform="rotate({item["rotation"]:.4f} '
                    f'{item["cx"]:.4f} {item["cy"]:.4f})"'
                )
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
        primitive_counts[item["kind"]] += 1
        created += 1

    lines.append("</svg>")
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    output_svg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if created == 0:
        raise RuntimeError("Local vectorizer produced no vector elements")

    metrics = quantization_metrics(source, labels, palette_bgr)
    return {
        "ok": True,
        "paths": len(found),
        "vector_elements": created,
        "width": width,
        "height": height,
        "requested_colors": colors,
        "palette_colors": int(len(palette_bgr)),
        "background_cluster": int(background_index),
        "preprocess": preprocess_mode,
        "palette_merge_distance": float(palette_merge_distance),
        "primitives": primitive_counts,
        **metrics,
        "output_svg": str(output_svg),
    }


def main():
    parser = argparse.ArgumentParser(description="Local raster-to-SVG vectorizer for Codex Sci-PPT.")
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--colors", type=int, default=12)
    parser.add_argument("--max-paths", type=int, default=700)
    parser.add_argument("--min-area-ratio", type=float, default=0.00010)
    parser.add_argument("--epsilon-ratio", type=float, default=0.0025)
    parser.add_argument("--preprocess", choices=("none", "bilateral"), default="bilateral")
    parser.add_argument("--palette-merge-distance", type=float, default=6.0)
    parser.add_argument("--sample-limit", type=int, default=250000)
    parser.add_argument("--no-background", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vectorize(
        args.input_image.resolve(), args.output_svg.resolve(), args.colors,
        args.max_paths, args.min_area_ratio, args.epsilon_ratio,
        include_background=not args.no_background,
        preprocess_mode=args.preprocess,
        palette_merge_distance=args.palette_merge_distance,
        sample_limit=args.sample_limit,
    ), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
