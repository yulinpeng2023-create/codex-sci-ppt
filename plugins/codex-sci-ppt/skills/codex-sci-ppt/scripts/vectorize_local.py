#!/usr/bin/env python3
"""Local raster-to-SVG vectorization for Codex Sci-PPT.

The output deliberately stays inside the downstream Cell-PPT-compatible SVG
subset. No remote API, key, upload, credit, or quota system is used.

Vectorizer v3 keeps the v2 palette/contour pipeline and adds conservative
semantic recovery for thin strokes and rotated rectangles plus geometry-level
quality diagnostics. Native SVG gradients are intentionally not emitted because
the Cell-PPT-compatible geometry cache forbids gradient nodes; smooth gradients
remain approximated by ordinary solid-color regions.
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
) -> tuple[str | None, np.ndarray | None, list[np.ndarray]]:
    outer_points = contour_points(contours[index], epsilon_ratio)
    outer = points_to_subpath(outer_points)
    if not outer:
        return None, None, []
    parts = [outer]
    holes: list[np.ndarray] = []
    child = int(hierarchy[index][2])
    while child >= 0:
        hole_points = contour_points(contours[child], epsilon_ratio)
        hole = points_to_subpath(hole_points)
        if hole:
            parts.append(hole)
            holes.append(hole_points)
        child = int(hierarchy[child][0])
    return " ".join(parts), outer_points, holes


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
        return cv2.bilateralFilter(source, d=5, sigmaColor=28, sigmaSpace=28)
    raise ValueError(f"unsupported preprocess mode: {mode}")


def sample_rows(pixels: np.ndarray, maximum: int, seed: int = 0) -> np.ndarray:
    if len(pixels) <= maximum:
        return pixels
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(pixels), size=maximum, replace=False)
    return pixels[indices]


def assign_nearest_centers(
    pixels: np.ndarray,
    centers: np.ndarray,
    chunk_size: int = 150_000,
) -> np.ndarray:
    result = np.empty(len(pixels), dtype=np.int32)
    for start in range(0, len(pixels), chunk_size):
        chunk = pixels[start:start + chunk_size].astype(np.float32)
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


def quantization_metrics(
    source_bgr: np.ndarray,
    labels: np.ndarray,
    palette_bgr: np.ndarray,
) -> dict:
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


def fit_line_stroke(
    contour: np.ndarray,
    hierarchy_row: np.ndarray,
    area: float,
    canvas_shape: tuple[int, int],
    aspect_threshold: float = 5.0,
    max_width_ratio: float = 0.035,
):
    """Recover a long thin filled component as an editable SVG stroke."""
    if int(hierarchy_row[2]) >= 0 or len(contour) < 4:
        return None
    (_, _), (side_one, side_two), _ = cv2.minAreaRect(contour)
    long_side = max(float(side_one), float(side_two))
    short_side = min(float(side_one), float(side_two))
    if long_side <= 2 or short_side <= 0:
        return None
    if long_side / short_side < aspect_threshold:
        return None
    height, width = canvas_shape
    max_width = max(6.0, min(height, width) * max_width_ratio)
    if short_side > max_width:
        return None
    extent = area / max(long_side * short_side, 1e-6)
    if extent < 0.58:
        return None

    vx, vy, x0, y0 = [float(value) for value in cv2.fitLine(
        contour, cv2.DIST_L2, 0, 0.01, 0.01
    ).reshape(-1)]
    norm = math.hypot(vx, vy)
    if norm <= 1e-9:
        return None
    vx /= norm
    vy /= norm
    points = contour.reshape(-1, 2).astype(np.float64)
    projection = (points[:, 0] - x0) * vx + (points[:, 1] - y0) * vy
    start = float(projection.min())
    end = float(projection.max())
    if end - start < long_side * 0.70:
        return None
    stroke_width = max(1.0, min(short_side * 1.10, area / max(end - start, 1.0) * 1.15))
    return {
        "kind": "line",
        "x1": x0 + vx * start,
        "y1": y0 + vy * start,
        "x2": x0 + vx * end,
        "y2": y0 + vy * end,
        "stroke_width": float(stroke_width),
        "linecap": "round",
    }


def fit_rectangle(
    contour: np.ndarray,
    hierarchy_row: np.ndarray,
    area: float,
    epsilon_ratio: float,
):
    if int(hierarchy_row[2]) >= 0:
        return None
    approx = contour_points(contour, epsilon_ratio)
    if len(approx) > 8:
        return None

    x, y, width, height = cv2.boundingRect(contour)
    if width > 1 and height > 1:
        extent = area / float(width * height)
        if extent >= 0.94:
            return {
                "kind": "rect",
                "cx": x + width / 2.0,
                "cy": y + height / 2.0,
                "width": float(width),
                "height": float(height),
                "rotation": 0.0,
            }

    (cx, cy), (rot_width, rot_height), angle = cv2.minAreaRect(contour)
    rot_width = float(rot_width)
    rot_height = float(rot_height)
    if rot_width <= 1 or rot_height <= 1:
        return None
    rotated_extent = area / max(rot_width * rot_height, 1e-6)
    if rotated_extent < 0.90:
        return None
    return {
        "kind": "rect",
        "cx": float(cx),
        "cy": float(cy),
        "width": rot_width,
        "height": rot_height,
        "rotation": float(angle),
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
    canvas_shape: tuple[int, int],
    recover_lines: bool,
) -> dict | None:
    contour = contours[index]

    if recover_lines:
        line = fit_line_stroke(contour, hierarchy[index], area, canvas_shape)
        if line is not None:
            line.update({"area": float(area), "stroke": fill})
            return line

    rectangle = fit_rectangle(contour, hierarchy[index], area, epsilon_ratio)
    if rectangle is not None:
        rectangle.update({"area": float(area), "fill": fill})
        return rectangle

    ellipse = fit_simple_ellipse(contour, hierarchy[index], area)
    if ellipse is not None:
        ellipse.update({"area": float(area), "fill": fill})
        return ellipse

    path_data, outer, holes = contour_path_with_holes(
        contours, hierarchy, index, epsilon_ratio
    )
    if not path_data or outer is None:
        return None
    return {
        "kind": "path",
        "area": float(area),
        "fill": fill,
        "d": path_data,
        "holes": child_count(hierarchy, index),
        "_outer": outer,
        "_hole_points": holes,
    }


def draw_item_mask(mask: np.ndarray, item: dict) -> None:
    kind = item["kind"]
    if kind == "line":
        cv2.line(
            mask,
            (round(item["x1"]), round(item["y1"])),
            (round(item["x2"]), round(item["y2"])),
            255,
            thickness=max(1, round(item["stroke_width"])),
            lineType=cv2.LINE_8,
        )
        return
    if kind == "rect":
        rect = (
            (float(item["cx"]), float(item["cy"])),
            (float(item["width"]), float(item["height"])),
            float(item.get("rotation", 0.0)),
        )
        box = np.rint(cv2.boxPoints(rect)).astype(np.int32)
        cv2.fillPoly(mask, [box], 255)
        return
    if kind == "ellipse":
        cv2.ellipse(
            mask,
            (round(item["cx"]), round(item["cy"])),
            (max(1, round(item["rx"])), max(1, round(item["ry"]))),
            float(item.get("rotation", 0.0)),
            0,
            360,
            255,
            thickness=-1,
            lineType=cv2.LINE_8,
        )
        return
    outer = np.asarray(item.get("_outer"), dtype=np.int32)
    if outer.size:
        cv2.fillPoly(mask, [outer], 255)
    for hole in item.get("_hole_points", []):
        hole_array = np.asarray(hole, dtype=np.int32)
        if hole_array.size:
            cv2.fillPoly(mask, [hole_array], 0)


def geometry_metrics(
    labels: np.ndarray,
    found: list[dict],
    background_index: int,
    include_background: bool,
    had_alpha: bool,
) -> dict:
    reconstructed = np.full(labels.shape, -1, dtype=np.int32)
    if include_background and not had_alpha:
        reconstructed[:, :] = int(background_index)

    for item in found:
        mask = np.zeros(labels.shape, dtype=np.uint8)
        draw_item_mask(mask, item)
        reconstructed[mask > 0] = int(item["color_index"])

    active = labels >= 0
    if not active.any():
        return {
            "geometry_pixel_accuracy": 0.0,
            "geometry_foreground_accuracy": 0.0,
            "geometry_foreground_iou": 0.0,
        }
    pixel_accuracy = float(np.mean(reconstructed[active] == labels[active]))
    actual_foreground = active & (labels != background_index)
    if actual_foreground.any():
        foreground_accuracy = float(np.mean(
            reconstructed[actual_foreground] == labels[actual_foreground]
        ))
    else:
        foreground_accuracy = 1.0
    predicted_foreground = (reconstructed >= 0) & (reconstructed != background_index)
    union = actual_foreground | predicted_foreground
    intersection = actual_foreground & predicted_foreground
    iou = float(intersection.sum() / union.sum()) if union.any() else 1.0
    return {
        "geometry_pixel_accuracy": round(pixel_accuracy, 4),
        "geometry_foreground_accuracy": round(foreground_accuracy, 4),
        "geometry_foreground_iou": round(iou, 4),
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
    recover_lines: bool = True,
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
            if color_index == background_index and area > height * width * 0.70:
                continue
            item = component_item(
                contours,
                hierarchy,
                index,
                area,
                fill,
                epsilon_ratio,
                (height, width),
                recover_lines,
            )
            if item is not None:
                item["color_index"] = int(color_index)
                found.append(item)

    found.sort(key=lambda item: (item["area"], -item["color_index"]), reverse=True)
    found = found[:max_paths]

    bg_b, bg_g, bg_r = [int(v) for v in palette_bgr[background_index]]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
    ]
    created = 0
    primitive_counts = {"rect": 0, "ellipse": 0, "line": 0, "path": 0}

    if include_background and not had_alpha:
        lines.append(
            f'<rect id="local_background" x="0" y="0" width="{width}" height="{height}" '
            f'fill="#{bg_r:02X}{bg_g:02X}{bg_b:02X}" stroke="none"/>'
        )
        created += 1
        primitive_counts["rect"] += 1

    for index, item in enumerate(found):
        element_id = f"local_path_{index:05d}"
        if item["kind"] == "line":
            lines.append(
                f'<line id="{element_id}" x1="{item["x1"]:.4f}" y1="{item["y1"]:.4f}" '
                f'x2="{item["x2"]:.4f}" y2="{item["y2"]:.4f}" fill="none" '
                f'stroke="{item["stroke"]}" stroke-width="{item["stroke_width"]:.4f}" '
                f'stroke-linecap="{item["linecap"]}"/>'
            )
        elif item["kind"] == "rect":
            x = item["cx"] - item["width"] / 2.0
            y = item["cy"] - item["height"] / 2.0
            transform = ""
            if abs(item.get("rotation", 0.0)) > 0.5:
                transform = (
                    f' transform="rotate({item["rotation"]:.4f} '
                    f'{item["cx"]:.4f} {item["cy"]:.4f})"'
                )
            lines.append(
                f'<rect id="{element_id}" x="{x:.4f}" y="{y:.4f}" '
                f'width="{item["width"]:.4f}" height="{item["height"]:.4f}" '
                f'fill="{item["fill"]}" stroke="none"{transform}/>'
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

    palette_metrics = quantization_metrics(source, labels, palette_bgr)
    shape_metrics = geometry_metrics(
        labels, found, background_index, include_background, had_alpha
    )
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
        "line_recovery": bool(recover_lines),
        "primitives": primitive_counts,
        **palette_metrics,
        **shape_metrics,
        "output_svg": str(output_svg),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Local raster-to-SVG vectorizer for Codex Sci-PPT."
    )
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    parser.add_argument("--colors", type=int, default=12)
    parser.add_argument("--max-paths", type=int, default=700)
    parser.add_argument("--min-area-ratio", type=float, default=0.00010)
    parser.add_argument("--epsilon-ratio", type=float, default=0.0025)
    parser.add_argument("--preprocess", choices=("none", "bilateral"), default="bilateral")
    parser.add_argument("--palette-merge-distance", type=float, default=6.0)
    parser.add_argument("--sample-limit", type=int, default=250000)
    parser.add_argument("--no-line-recovery", action="store_true")
    parser.add_argument("--no-background", action="store_true")
    args = parser.parse_args()
    print(json.dumps(vectorize(
        args.input_image.resolve(),
        args.output_svg.resolve(),
        args.colors,
        args.max_paths,
        args.min_area_ratio,
        args.epsilon_ratio,
        include_background=not args.no_background,
        preprocess_mode=args.preprocess,
        palette_merge_distance=args.palette_merge_distance,
        sample_limit=args.sample_limit,
        recover_lines=not args.no_line_recovery,
    ), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
