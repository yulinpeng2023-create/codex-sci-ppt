#!/usr/bin/env python3
"""Analyze a flat scientific reference image locally.

The analyzer is intentionally API-free. It estimates canvas/background,
dominant colors, large frame candidates, connected visual components,
primitive geometry, and text-like regions. The output is designed to seed
Codex Sci-PPT's reference-scene mode; it does not modify the Cell-PPT-
compatible SVG/cache/OOXML reconstruction pipeline.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


def _hex(rgb: Iterable[float]) -> str:
    vals = [int(max(0, min(255, round(float(v))))) for v in rgb]
    return "#" + "".join(f"{v:02X}" for v in vals)


def _rgb_image(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        alpha = np.full(image.shape, 255, np.uint8)
        return rgb, alpha
    if image.shape[2] == 4:
        rgba = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        return rgba[:, :, :3], rgba[:, :, 3]
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB), np.full(image.shape[:2], 255, np.uint8)


def _border_pixels(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    band = max(2, int(round(min(h, w) * 0.035)))
    mask = np.zeros((h, w), np.uint8)
    mask[:band, :] = 1
    mask[-band:, :] = 1
    mask[:, :band] = 1
    mask[:, -band:] = 1
    select = (mask > 0) & (alpha > 0)
    pixels = rgb[select]
    if len(pixels) == 0:
        pixels = rgb.reshape(-1, 3)
    return pixels


def estimate_background(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    pixels = _border_pixels(rgb, alpha)
    # Median resists colored frame lines crossing the border band.
    return np.median(pixels, axis=0).astype(np.uint8)


def _foreground_mask(rgb: np.ndarray, alpha: np.ndarray, bg_rgb: np.ndarray, threshold: float) -> np.ndarray:
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    bg_lab = cv2.cvtColor(bg_rgb.reshape(1, 1, 3), cv2.COLOR_RGB2LAB).astype(np.float32)[0, 0]
    distance = np.linalg.norm(lab - bg_lab, axis=2)
    mask = ((distance >= threshold) & (alpha >= 16)).astype(np.uint8) * 255
    # Preserve thin scientific lines while removing isolated compression speckles.
    k = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)
    return mask


def _palette(rgb: np.ndarray, alpha: np.ndarray, fg_mask: np.ndarray, k: int) -> list[dict]:
    select = (fg_mask > 0) & (alpha > 0)
    pixels = rgb[select]
    if len(pixels) == 0:
        return []
    if len(pixels) > 30000:
        rng = np.random.default_rng(0)
        pixels = pixels[rng.choice(len(pixels), size=30000, replace=False)]
    k = max(1, min(int(k), len(pixels), 12))
    lab = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(0)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 35, 0.3)
    _, labels, centers_lab = cv2.kmeans(lab, k, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    centers_rgb = cv2.cvtColor(np.clip(centers_lab, 0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    counts = np.bincount(labels.ravel(), minlength=k)
    order = np.argsort(-counts)
    return [
        {"color": _hex(centers_rgb[i]), "count": int(counts[i]), "fraction": round(float(counts[i] / counts.sum()), 4)}
        for i in order
    ]


def _sample_component_color(rgb: np.ndarray, component_mask: np.ndarray) -> str:
    pixels = rgb[component_mask > 0]
    if len(pixels) == 0:
        return "#000000"
    return _hex(np.median(pixels, axis=0))


def _contour_features(contour: np.ndarray, bbox: tuple[int, int, int, int]) -> dict:
    x, y, w, h = bbox
    area = float(abs(cv2.contourArea(contour)))
    perimeter = float(cv2.arcLength(contour, True))
    bbox_area = max(1.0, float(w * h))
    circularity = 0.0 if perimeter <= 1e-6 else float(4.0 * math.pi * area / (perimeter * perimeter))
    rect = cv2.minAreaRect(contour)
    rw, rh = rect[1]
    short = max(1e-6, min(rw, rh))
    long = max(rw, rh)
    angle = float(rect[2])
    if rw < rh:
        angle += 90.0
    return {
        "contour_area": round(area, 2),
        "extent": round(area / bbox_area, 4),
        "circularity": round(max(0.0, min(1.0, circularity)), 4),
        "rotated_aspect": round(float(long / short), 4),
        "angle_deg": round(angle, 2),
    }


def _classify_component(bbox: tuple[int, int, int, int], features: dict, image_shape: tuple[int, int]) -> tuple[str, float]:
    x, y, w, h = bbox
    ih, iw = image_shape
    aspect = max(w / max(1, h), h / max(1, w))
    short = min(w, h)
    long = max(w, h)
    extent = float(features["extent"])
    circ = float(features["circularity"])
    area_fraction = (w * h) / float(iw * ih)

    if area_fraction >= 0.24 and extent < 0.55:
        return "frame", 0.78
    if short <= max(3, int(round(min(iw, ih) * 0.025))) and aspect >= 4.0:
        return "line", 0.9
    if circ >= 0.73 and 0.65 <= (w / max(1, h)) <= 1.55:
        return "ellipse", min(0.96, 0.72 + circ * 0.25)
    if extent >= 0.72 and aspect >= 2.5:
        return "round_rect", min(0.94, 0.72 + extent * 0.2)
    if extent >= 0.72:
        return "rect", min(0.92, 0.7 + extent * 0.2)
    if long >= 12 and short <= 8 and aspect >= 2.0:
        return "line", 0.7
    return "component", 0.45


def _component_candidates(rgb: np.ndarray, fg_mask: np.ndarray, min_area: int) -> list[dict]:
    h, w = fg_mask.shape
    count, labels, stats, _ = cv2.connectedComponentsWithStats((fg_mask > 0).astype(np.uint8), 8)
    candidates: list[dict] = []
    for label in range(1, count):
        x, y, cw, ch, area = [int(v) for v in stats[label]]
        if area < min_area or cw <= 1 or ch <= 1:
            continue
        comp = np.where(labels == label, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        features = _contour_features(contour, (x, y, cw, ch))
        kind, confidence = _classify_component((x, y, cw, ch), features, (h, w))
        box = cv2.boxPoints(cv2.minAreaRect(contour))
        box = [[round(float(px), 2), round(float(py), 2)] for px, py in box]
        candidates.append({
            "id": f"component_{len(candidates)+1}",
            "kind": kind,
            "confidence": round(float(confidence), 3),
            "bbox_px": [x, y, cw, ch],
            "bbox_norm": [round(x / w, 5), round(y / h, 5), round(cw / w, 5), round(ch / h, 5)],
            "pixel_area": area,
            "area_fraction": round(area / float(w * h), 6),
            "color": _sample_component_color(rgb, comp),
            "rotated_box_px": box,
            **features,
        })
    candidates.sort(key=lambda c: (-c["pixel_area"], c["bbox_px"][1], c["bbox_px"][0]))
    return candidates


def _frame_candidates(fg_mask: np.ndarray, rgb: np.ndarray) -> list[dict]:
    h, w = fg_mask.shape
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    frames = []
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        bbox_fraction = (cw * ch) / float(w * h)
        if bbox_fraction < 0.22:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) < 4 or len(approx) > 8:
            continue
        area = abs(cv2.contourArea(contour))
        if area / max(1.0, cw * ch) < 0.65:
            # Thin rectangular outlines can have a large contour area due to the
            # outer traced boundary, but very fragmented contours are rejected.
            continue
        mask = np.zeros_like(fg_mask)
        cv2.drawContours(mask, [contour], -1, 255, 1)
        frames.append({
            "bbox_px": [x, y, cw, ch],
            "bbox_norm": [round(x / w, 5), round(y / h, 5), round(cw / w, 5), round(ch / h, 5)],
            "coverage": round(bbox_fraction, 4),
            "color": _sample_component_color(rgb, mask),
        })
    frames.sort(key=lambda item: -item["coverage"])
    dedup = []
    for frame in frames:
        if not dedup:
            dedup.append(frame)
            continue
        x, y, cw, ch = frame["bbox_px"]
        if any(abs(x-d["bbox_px"][0]) <= 3 and abs(y-d["bbox_px"][1]) <= 3 and abs(cw-d["bbox_px"][2]) <= 5 and abs(ch-d["bbox_px"][3]) <= 5 for d in dedup):
            continue
        dedup.append(frame)
    return dedup[:5]


def _text_like_regions(rgb: np.ndarray, bg_rgb: np.ndarray) -> list[dict]:
    h, w = rgb.shape[:2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Conservative text heuristic: relatively dark and low-saturation pixels.
    mask = ((gray < 175) & (hsv[:, :, 1] < 105)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    mask = cv2.dilate(mask, np.ones((2, 5), np.uint8), iterations=1)
    n, _, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    regions = []
    for i in range(1, n):
        x, y, cw, ch, area = [int(v) for v in stats[i]]
        if area < 8 or cw < 5 or ch < 3:
            continue
        if ch > max(28, int(h * 0.16)) or cw > int(w * 0.55):
            continue
        aspect = cw / max(1, ch)
        if aspect < 0.45:
            continue
        regions.append({
            "bbox_px": [x, y, cw, ch],
            "bbox_norm": [round(x / w, 5), round(y / h, 5), round(cw / w, 5), round(ch / h, 5)],
            "area": area,
        })
    regions.sort(key=lambda r: (r["bbox_px"][1], r["bbox_px"][0]))
    return regions[:80]


def _scene_object_from_component(component: dict, slide_w: float, slide_h: float) -> dict | None:
    kind = component["kind"]
    if component["confidence"] < 0.7 or kind not in {"rect", "round_rect", "ellipse", "line"}:
        return None
    nx, ny, nw, nh = component["bbox_norm"]
    color = component["color"]
    x, y, w, h = nx * slide_w, ny * slide_h, nw * slide_w, nh * slide_h
    if kind == "line":
        angle = math.radians(component.get("angle_deg", 0.0))
        cx, cy = x + w / 2, y + h / 2
        length = max(w, h)
        dx = math.cos(angle) * length / 2
        dy = math.sin(angle) * length / 2
        return {
            "type": "line", "x1": round(cx - dx, 4), "y1": round(cy - dy, 4),
            "x2": round(cx + dx, 4), "y2": round(cy + dy, 4),
            "line": color, "line_width": 1.0,
            "_source_component": component["id"],
        }
    return {
        "type": kind,
        "x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4),
        "fill": color, "line": color, "line_width": 0.8,
        "rotation": round(component.get("angle_deg", 0.0), 2) if abs(component.get("angle_deg", 0.0)) > 1.0 else 0,
        "_source_component": component["id"],
    }


def build_scene_draft(analysis: dict, slide_width: float) -> dict:
    iw, ih = analysis["image"]["width"], analysis["image"]["height"]
    slide_height = slide_width * ih / iw
    objects = []
    if analysis["frames"]:
        frame = analysis["frames"][0]
        nx, ny, nw, nh = frame["bbox_norm"]
        objects.append({
            "type": "rect", "x": round(nx * slide_width, 4), "y": round(ny * slide_height, 4),
            "w": round(nw * slide_width, 4), "h": round(nh * slide_height, 4),
            "fill": None, "line": frame["color"], "line_width": 1.0,
            "_source": "auto_frame_candidate",
        })
    for component in analysis["components"]:
        obj = _scene_object_from_component(component, slide_width, slide_height)
        if obj is not None:
            # Avoid duplicating the selected outer frame.
            if component["kind"] == "frame":
                continue
            objects.append(obj)
    return {
        "slide": {"width": round(slide_width, 4), "height": round(slide_height, 4)},
        "background": analysis["background"],
        "objects": objects,
        "_analysis_note": "Draft only. Review semantic object types, text, layer order, and outlines before publication use.",
    }


def _debug_overlay(rgb: np.ndarray, analysis: dict) -> np.ndarray:
    out = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    palette = {
        "frame": (0, 170, 255), "line": (0, 190, 0), "ellipse": (200, 0, 200),
        "rect": (255, 120, 0), "round_rect": (255, 120, 0), "component": (100, 100, 255),
    }
    for comp in analysis["components"][:120]:
        x, y, w, h = comp["bbox_px"]
        color = palette.get(comp["kind"], (120, 120, 120))
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 1)
        label = f"{comp['kind']} {comp['confidence']:.2f}"
        cv2.putText(out, label, (x, max(9, y - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.28, color, 1, cv2.LINE_AA)
    for region in analysis["text_like_regions"]:
        x, y, w, h = region["bbox_px"]
        cv2.rectangle(out, (x, y), (x + w, y + h), (70, 70, 70), 1)
    return out


def analyze(image_path: str | Path, threshold: float = 14.0, palette_colors: int = 8, min_area: int | None = None) -> tuple[dict, np.ndarray]:
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    rgb, alpha = _rgb_image(image)
    h, w = rgb.shape[:2]
    bg = estimate_background(rgb, alpha)
    fg = _foreground_mask(rgb, alpha, bg, float(threshold))
    if min_area is None:
        min_area = max(4, int(round(w * h * 0.00005)))
    analysis = {
        "schema": "codex-sci-ppt-reference-analysis-v1",
        "image": {"width": w, "height": h, "aspect_ratio": round(w / h, 6)},
        "background": _hex(bg),
        "foreground_fraction": round(float(np.mean(fg > 0)), 6),
        "palette": _palette(rgb, alpha, fg, palette_colors),
        "frames": _frame_candidates(fg, rgb),
        "components": _component_candidates(rgb, fg, int(min_area)),
        "text_like_regions": _text_like_regions(rgb, bg),
    }
    analysis["summary"] = {
        "component_count": len(analysis["components"]),
        "high_confidence_primitive_count": sum(1 for c in analysis["components"] if c["confidence"] >= 0.7 and c["kind"] in {"rect", "round_rect", "ellipse", "line"}),
        "frame_candidate_count": len(analysis["frames"]),
        "text_like_region_count": len(analysis["text_like_regions"]),
    }
    return analysis, rgb


def main() -> None:
    ap = argparse.ArgumentParser(description="Locally estimate layout/style primitives from a flat scientific reference image.")
    ap.add_argument("--input-image", required=True)
    ap.add_argument("--analysis", required=True, help="Output analysis JSON")
    ap.add_argument("--scene-draft", help="Optional draft scene JSON using high-confidence primitives")
    ap.add_argument("--debug-overlay", help="Optional PNG showing detected components/text-like regions")
    ap.add_argument("--slide-width", type=float, default=10.0)
    ap.add_argument("--background-distance", type=float, default=14.0)
    ap.add_argument("--palette-colors", type=int, default=8)
    ap.add_argument("--min-area", type=int)
    args = ap.parse_args()

    analysis, rgb = analyze(args.input_image, args.background_distance, args.palette_colors, args.min_area)
    analysis_path = Path(args.analysis)
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.scene_draft:
        scene = build_scene_draft(analysis, float(args.slide_width))
        scene_path = Path(args.scene_draft)
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        scene_path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.debug_overlay:
        overlay = _debug_overlay(rgb, analysis)
        overlay_path = Path(args.debug_overlay)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(overlay_path), overlay):
            raise RuntimeError(f"Failed to write overlay: {overlay_path}")

    print(json.dumps(analysis["summary"], separators=(",", ":")))


if __name__ == "__main__":
    main()
