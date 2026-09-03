#!/usr/bin/env python3
"""Parse a Sci-PPT master SVG once into a geometry cache.

The cache contract deliberately follows the useful parts of the MIT-licensed
Cell_ppt architecture: literal SVG paint order, path/text atoms, cubic Bézier
geometry, and batched native drawing. See THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path

NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
NAMED_COLORS = {
    "black": [0, 0, 0],
    "white": [255, 255, 255],
    "red": [255, 0, 0],
    "green": [0, 128, 0],
    "blue": [0, 0, 255],
    "gray": [128, 128, 128],
    "orange": [255, 165, 0],
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def number(value, default=0.0):
    if value is None:
        return default
    match = NUMBER_RE.search(str(value))
    return float(match.group(0)) if match else default


def parse_color(value):
    text = str(value or "black").strip().lower()
    if text in ("none", "transparent"):
        return None
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        if len(digits) >= 6:
            return [int(digits[index:index + 2], 16) for index in (0, 2, 4)]
    if text in NAMED_COLORS:
        return NAMED_COLORS[text]
    match = re.fullmatch(r"rgb\(([^)]+)\)", text)
    if match:
        parts = [int(float(item.strip())) for item in match.group(1).split(",")[:3]]
        return [max(0, min(255, item)) for item in parts]
    raise ValueError(f"unsupported solid color: {value}")


def merged_style(element, parent):
    result = dict(parent)
    for key in (
        "fill", "stroke", "stroke-width", "font-family", "font-size",
        "font-weight", "font-style", "text-anchor", "opacity",
        "fill-opacity", "stroke-opacity",
    ):
        if element.get(key) is not None:
            result[key] = element.get(key)
    raw = element.get("style", "")
    for declaration in raw.split(";"):
        if ":" in declaration:
            key, value = declaration.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def element_path_data(element):
    kind = local_name(element.tag)
    if kind == "path":
        return re.sub(r"[\t\r\n ]+", " ", element.get("d", "").strip())
    if kind == "line":
        return (
            f'M {number(element.get("x1"))} {number(element.get("y1"))} '
            f'L {number(element.get("x2"))} {number(element.get("y2"))}'
        )
    if kind in ("polyline", "polygon"):
        values = [float(item) for item in NUMBER_RE.findall(element.get("points", ""))]
        if len(values) < 4 or len(values) % 2:
            raise ValueError(f"invalid <{kind}> points")
        result = f"M {values[0]} {values[1]} " + " ".join(
            f"L {values[index]} {values[index + 1]}" for index in range(2, len(values), 2)
        )
        return result + (" Z" if kind == "polygon" else "")
    if kind == "rect":
        x, y = number(element.get("x")), number(element.get("y"))
        width, height = number(element.get("width")), number(element.get("height"))
        return f"M {x} {y} H {x + width} V {y + height} H {x} Z"
    if kind in ("circle", "ellipse"):
        cx, cy = number(element.get("cx")), number(element.get("cy"))
        rx = number(element.get("r")) if kind == "circle" else number(element.get("rx"))
        ry = rx if kind == "circle" else number(element.get("ry"))
        return (
            f"M {cx + rx} {cy} A {rx} {ry} 0 1 1 {cx - rx} {cy} "
            f"A {rx} {ry} 0 1 1 {cx + rx} {cy} Z"
        )
    raise ValueError(f"unsupported vector atom <{kind}>")


def recording_to_subpaths(recording):
    subpaths = []
    points = []

    def new_point(anchor):
        value = [round(float(anchor[0]), 6), round(float(anchor[1]), 6)]
        return {"a": value[:], "l": value[:], "r": value[:], "t": "corner"}

    def flush(closed=False):
        nonlocal points
        if len(points) >= 2:
            subpaths.append({"closed": closed, "points": points})
        points = []

    for operation, arguments in recording:
        if operation == "moveTo":
            flush(False)
            points = [new_point(arguments[0])]
        elif operation == "lineTo":
            for endpoint in arguments:
                points[-1]["r"] = points[-1]["a"][:]
                points.append(new_point(endpoint))
        elif operation == "curveTo":
            for index in range(0, len(arguments), 3):
                control_one, control_two, endpoint = arguments[index:index + 3]
                points[-1]["r"] = [round(control_one[0], 6), round(control_one[1], 6)]
                created = new_point(endpoint)
                created["l"] = [round(control_two[0], 6), round(control_two[1], 6)]
                points.append(created)
        elif operation == "closePath":
            flush(True)
        elif operation == "endPath":
            flush(False)
    flush(False)
    return subpaths


def parse_path_atom(element, presentation, index):
    recording = RecordingPen()
    cubic_pen = Qu2CuPen(recording, max_err=0.001, all_cubic=True)
    parse_path(element_path_data(element), cubic_pen)
    subpaths = recording_to_subpaths(recording.value)
    if not subpaths:
        raise ValueError("vector atom produced no drawable subpaths")

    fill_color = parse_color(presentation.get("fill", "black"))
    stroke_color = parse_color(presentation.get("stroke", "none"))
    opacity = max(0.0, min(1.0, number(presentation.get("opacity"), 1.0)))
    paint = {
        "filled": fill_color is not None,
        "fillColor": fill_color,
        "stroked": stroke_color is not None,
        "strokeColor": stroke_color,
        "strokeWidth": number(presentation.get("stroke-width"), 1.0),
        "opacity": opacity * 100.0,
    }
    return {
        "kind": "path",
        "index": index,
        "sourceId": element.get("id") or f"source_{index:06d}",
        "objectName": f"SCI_PPT_ATOM_{index:06d}",
        "subpaths": subpaths,
        "paintParts": [paint],
        "complexity": sum(len(subpath["points"]) for subpath in subpaths),
    }


def parse_text_atom(element, presentation, index):
    contents = "".join(element.itertext())
    if not contents:
        return None
    fill_color = parse_color(presentation.get("fill", "black")) or [0, 0, 0]
    return {
        "kind": "text",
        "index": index,
        "sourceId": element.get("id") or f"source_{index:06d}",
        "objectName": f"SCI_PPT_ATOM_{index:06d}",
        "text": {
            "contents": contents,
            "position": [number(element.get("x")), number(element.get("y"))],
            "fontSize": number(presentation.get("font-size"), 16.0),
            "fontFamily": presentation.get("font-family", "Arial").split(",", 1)[0].strip(" '\""),
            "fontWeight": presentation.get("font-weight", "normal"),
            "fontStyle": presentation.get("font-style", "normal"),
            "textAnchor": presentation.get("text-anchor", "start"),
            "rotationDegrees": 0,
            "fillColor": fill_color,
            "opacity": 100,
        },
        "paintParts": [],
        "complexity": 1,
    }


def build_batches(atoms, size=40):
    return [
        {
            "index": start // size,
            "kind": "normal",
            "group_name": f"SCI_PPT_CACHE_{start // size:04d}",
            "atom_indices": list(range(start, min(start + size, len(atoms)))),
            "atomic_count": min(size, len(atoms) - start),
            "complexity": sum(atom["complexity"] for atom in atoms[start:start + size]),
        }
        for start in range(0, len(atoms), size)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--job-id", default="scippt")
    args = parser.parse_args()

    root = ET.parse(args.input).getroot()
    view_box = [float(item) for item in re.split(r"[\s,]+", root.get("viewBox", "").strip()) if item]
    if len(view_box) != 4:
        raise ValueError("valid SVG viewBox required")

    atoms = []
    defaults = {
        "fill": "black",
        "stroke": "none",
        "stroke-width": "1",
        "font-family": "Arial",
        "font-size": "16",
        "font-weight": "normal",
        "font-style": "normal",
        "text-anchor": "start",
    }

    def walk(node, inherited):
        for element in list(node):
            kind = local_name(element.tag)
            presentation = merged_style(element, inherited)
            if kind in ("g", "svg", "a", "switch"):
                walk(element, presentation)
            elif kind == "text":
                atom = parse_text_atom(element, presentation, len(atoms))
                if atom:
                    atoms.append(atom)
            elif kind in ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon"):
                atoms.append(parse_path_atom(element, presentation, len(atoms)))
            elif kind in ("title", "desc", "metadata", "defs"):
                continue
            else:
                raise ValueError(f"unsupported rendered SVG element <{kind}>")

    walk(root, merged_style(root, defaults))
    if not atoms:
        raise ValueError("SVG contains no supported vector atoms")

    payload = {
        "schema_version": 3,
        "job_id": args.job_id,
        "view_box": view_box,
        "atoms": atoms,
        "total_atoms": len(atoms),
        "batches": build_batches(atoms),
        "min_batch_size": 20,
        "max_batch_size": 50,
        "complex_point_threshold": 1200,
        "max_batch_points": 12000,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.output_dir / "geometry-cache.json"
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (args.output_dir / "drawing-state.json").write_text(
        json.dumps({"job_id": args.job_id, "total_atoms": len(atoms)}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "atoms": len(atoms), "cache": str(cache_path.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
