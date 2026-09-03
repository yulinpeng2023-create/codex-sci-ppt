#!/usr/bin/env python3
"""End-to-end self-test for Codex Sci-PPT's local, no-API pipeline."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from pptx import Presentation


def run(*args: object) -> str:
    completed = subprocess.run(
        [sys.executable, *map(str, args)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def assert_pptx(path: Path, min_shapes: int = 1, expected_text: str | None = None) -> int:
    prs = Presentation(str(path))
    if not prs.slides:
        raise AssertionError(f"no slides in {path}")
    count = sum(len(slide.shapes) for slide in prs.slides)
    if count < min_shapes:
        raise AssertionError(f"expected >= {min_shapes} shapes, got {count} in {path}")
    if expected_text is not None:
        texts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    texts.append(shape.text)
        if not any(expected_text in text for text in texts):
            raise AssertionError(f"editable text {expected_text!r} not found in {path}")
    return count


def main() -> int:
    scripts = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[5]
    summary: dict[str, object] = {"ok": False}

    with tempfile.TemporaryDirectory(prefix="codex-sci-ppt-selftest-") as td:
        work = Path(td)

        # 1) SVG validation/cache/cull/OOXML path, including transforms,
        # cubic geometry, duplicate paths, and editable text.
        svg = work / "core.svg"
        svg.write_text(
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <g transform="translate(10 5) scale(2 1.5)">
    <rect id="rect-a" x="5" y="5" width="30" height="15" rx="3" fill="#D9EAD3" stroke="#38761D" stroke-width="2"/>
    <rect id="rect-dup" x="5" y="5" width="30" height="15" rx="3" fill="#D9EAD3" stroke="#38761D" stroke-width="2"/>
    <path id="curve" d="M 50 15 C 60 0 75 30 90 15 Z" fill="#F6B26B" stroke="#B45F06"/>
  </g>
  <text id="label" x="120" y="70" font-family="Arial" font-size="16" fill="#222222">Editable label</text>
</svg>\n''',
            encoding="utf-8",
        )
        run(scripts / "validate_vector_svg.py", "--svg", svg, "--strict-ids")
        cache_dir = work / "cache"
        run(scripts / "prepare_geometry_cache.py", "--input", svg, "--output-dir", cache_dir, "--job-id", "selftest")
        before = json.loads((cache_dir / "geometry-cache.json").read_text(encoding="utf-8"))
        if before["total_atoms"] != 4:
            raise AssertionError(f"expected 4 source atoms, got {before['total_atoms']}")
        first_anchor = before["atoms"][0]["subpaths"][0]["points"][0]["a"]
        if first_anchor == [8.0, 5.0] or first_anchor == [5.0, 5.0]:
            raise AssertionError("SVG transform was not applied to cached geometry")
        run(
            scripts / "cull_hidden_geometry.py",
            "--cache", cache_dir / "geometry-cache.json",
            "--state", cache_dir / "drawing-state.json",
        )
        after = json.loads((cache_dir / "geometry-cache.json").read_text(encoding="utf-8"))
        if after.get("culled_atom_count", 0) < 1:
            raise AssertionError("exact duplicate path was not culled")
        core_pptx = work / "core.pptx"
        run(scripts / "run_cell_ppt_ooxml.py", "--geometry-cache", cache_dir / "geometry-cache.json", "--output-pptx", core_pptx)
        core_shapes = assert_pptx(core_pptx, min_shapes=3, expected_text="Editable label")

        # 2) Scene renderer.
        scene_pptx = work / "scene.pptx"
        run(
            scripts / "render_scene.py",
            "--scene", repo_root / "examples" / "simple_scene.json",
            "--output", scene_pptx,
        )
        scene_shapes = assert_pptx(scene_pptx, min_shapes=3)

        # 3) Full local image -> local text cleanup -> SVG -> cache -> PPTX.
        image = np.full((240, 360, 3), 255, dtype=np.uint8)
        cv2.rectangle(image, (30, 50), (150, 190), (230, 200, 120), thickness=-1)
        cv2.circle(image, (250, 120), 55, (90, 160, 235), thickness=-1)
        cv2.line(image, (150, 120), (195, 120), (60, 60, 60), thickness=8)
        cv2.putText(image, "TXT", (88, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (25, 25, 25), 2, cv2.LINE_AA)
        image_path = work / "synthetic.png"
        cv2.imwrite(str(image_path), image)
        manifest = work / "text-manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": "1.0",
            "text_elements": [{
                "id": "live-text-1",
                "content": "TXT",
                "x": 0.245,
                "y": 0.145,
                "bbox": [0.225, 0.025, 0.19, 0.14],
                "coordinate_space": "normalized",
                "font_size": 18,
                "font_family": "Arial",
                "fill": "#191919",
                "paint_order": 999
            }]
        }), encoding="utf-8")
        image_pptx = work / "image.pptx"
        output = run(
            scripts / "run_from_image.py",
            "--input-image", image_path,
            "--text-manifest", manifest,
            "--output", image_pptx,
            "--colors", "5",
            "--max-paths", "100",
        )
        image_shapes = assert_pptx(image_pptx, min_shapes=2, expected_text="TXT")
        result = json.loads(output.splitlines()[-1])
        if int(result.get("text_regions_removed", 0)) != 1:
            raise AssertionError(f"expected one text region removed, got {result.get('text_regions_removed')}")
        master_svg = Path(result["master_svg"])
        master_payload = master_svg.read_text(encoding="utf-8")
        if "<image" in master_payload:
            raise AssertionError("local image pipeline left a raster <image> node in master SVG")
        if ">TXT<" not in master_payload:
            raise AssertionError("live editable text was not merged back into master SVG")

        # 4) Job allocator should produce stable sequential names.
        jobs = work / "jobs"
        first_job = subprocess.check_output(
            [sys.executable, str(scripts / "allocate_job_name.py"), "--root", str(jobs)], text=True
        ).strip()
        (jobs / first_job).mkdir(parents=True)
        second_job = subprocess.check_output(
            [sys.executable, str(scripts / "allocate_job_name.py"), "--root", str(jobs)], text=True
        ).strip()
        if (first_job, second_job) != ("codexscippt1", "codexscippt2"):
            raise AssertionError(f"unexpected job allocation: {first_job}, {second_job}")

        summary.update({
            "ok": True,
            "core_shapes": core_shapes,
            "scene_shapes": scene_shapes,
            "image_shapes": image_shapes,
            "source_atoms": before["total_atoms"],
            "retained_atoms": after["total_atoms"],
            "duplicates_removed": after.get("culled_atom_count", 0),
            "text_regions_removed": result.get("text_regions_removed", 0),
            "raster_nodes": 0,
            "jobs": [first_job, second_job],
        })

    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
