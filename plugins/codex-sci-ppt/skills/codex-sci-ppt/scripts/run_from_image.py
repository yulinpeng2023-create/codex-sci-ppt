#!/usr/bin/env python3
"""Local image -> text cleanup -> SVG -> cache -> editable PPTX pipeline.

This intentionally mirrors Cell-PPT's high-level stages while replacing the
remote vectorization/API step with deterministic local vectorization.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args):
    completed = subprocess.run(
        [sys.executable, *map(str, args)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def allocate_name(scripts: Path, output_root: Path) -> str:
    return subprocess.check_output(
        [sys.executable, str(scripts / "allocate_job_name.py"), "--root", str(output_root.resolve())],
        text=True,
    ).strip().splitlines()[-1]


def main():
    parser = argparse.ArgumentParser(
        description="Local image to editable PowerPoint. No API key or credits required."
    )
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--text-manifest", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input-pptx", type=Path)
    parser.add_argument("--slide-index", type=int, default=0)
    parser.add_argument("--job-name")
    parser.add_argument("--colors", type=int, default=12)
    parser.add_argument("--max-paths", type=int, default=700)
    parser.add_argument("--min-area-ratio", type=float, default=0.00010)
    parser.add_argument("--epsilon-ratio", type=float, default=0.0025)
    parser.add_argument("--preprocess", choices=("none", "bilateral"), default="bilateral")
    parser.add_argument("--palette-merge-distance", type=float, default=6.0)
    parser.add_argument("--sample-limit", type=int, default=250000)
    parser.add_argument("--no-line-recovery", action="store_true")
    parser.add_argument("--text-padding", type=int, default=3)
    args = parser.parse_args()

    if bool(args.output_root) == bool(args.output):
        parser.error("provide exactly one of --output-root or --output")

    scripts = Path(__file__).resolve().parent

    if args.output_root:
        output_root = args.output_root.expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        base_name = args.job_name or allocate_name(scripts, output_root)
        job = output_root / base_name
        job.mkdir(parents=True, exist_ok=True)
        raw_svg = job / f"{base_name}-vector.svg"
        master_svg = job / f"{base_name}.svg"
        cleaned_image = job / f"{base_name}-cleaned.png"
        expected_pptx = job / f"{base_name}.pptx"
    else:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        base_name = args.job_name or output.stem or "codexscippt"
        work = Path(tempfile.mkdtemp(prefix=".codex-sci-ppt-", dir=output.parent))
        raw_svg = work / "vector.svg"
        master_svg = work / "master.svg"
        cleaned_image = work / "cleaned.png"
        expected_pptx = output

    source_for_vectorization = args.input_image.resolve()
    text_cleanup = {"regions_removed": 0}
    if args.text_manifest:
        cleanup_output = run(
            scripts / "remove_text_regions.py",
            "--input-image", args.input_image.resolve(),
            "--text-manifest", args.text_manifest.resolve(),
            "--output-image", cleaned_image,
            "--padding", max(0, args.text_padding),
        )
        if cleanup_output:
            text_cleanup = json.loads(cleanup_output.splitlines()[-1])
        source_for_vectorization = cleaned_image

    vector_command = [
        scripts / "vectorize_local.py",
        "--input-image", source_for_vectorization,
        "--output-svg", raw_svg,
        "--colors", args.colors,
        "--max-paths", args.max_paths,
        "--min-area-ratio", args.min_area_ratio,
        "--epsilon-ratio", args.epsilon_ratio,
        "--preprocess", args.preprocess,
        "--palette-merge-distance", args.palette_merge_distance,
        "--sample-limit", args.sample_limit,
    ]
    if args.no_line_recovery:
        vector_command.append("--no-line-recovery")
    vector_output = run(*vector_command)
    vector_summary = json.loads(vector_output.splitlines()[-1]) if vector_output else {}

    if args.text_manifest:
        run(
            scripts / "merge_live_text.py",
            "--input-svg", raw_svg,
            "--text-manifest", args.text_manifest.resolve(),
            "--output-svg", master_svg,
        )
    else:
        master_svg.write_bytes(raw_svg.read_bytes())

    if args.output_root:
        command = [
            scripts / "run_from_svg.py",
            "--input-svg", master_svg,
            "--output-root", output_root,
            "--job-name", base_name,
            "--slide-index", args.slide_index,
        ]
    else:
        command = [
            scripts / "run_from_svg.py",
            "--input-svg", master_svg,
            "--output-pptx", expected_pptx,
            "--job-name", base_name,
            "--slide-index", args.slide_index,
        ]
    if args.input_pptx:
        command += ["--input-pptx", args.input_pptx.resolve()]
    run(*command)

    print(json.dumps({
        "ok": True,
        "base_name": base_name,
        "master_svg": str(master_svg),
        "pptx": str(expected_pptx),
        "local_only": True,
        "text_regions_removed": int(text_cleanup.get("regions_removed", 0)),
        "vector_elements": int(vector_summary.get("vector_elements", 0)),
        "palette_colors": int(vector_summary.get("palette_colors", 0)),
        "palette_psnr_db": float(vector_summary.get("palette_psnr_db", 0.0)),
        "palette_mae": float(vector_summary.get("palette_mae", 0.0)),
        "geometry_pixel_accuracy": float(vector_summary.get("geometry_pixel_accuracy", 0.0)),
        "geometry_foreground_accuracy": float(vector_summary.get("geometry_foreground_accuracy", 0.0)),
        "geometry_foreground_iou": float(vector_summary.get("geometry_foreground_iou", 0.0)),
        "primitives": vector_summary.get("primitives", {}),
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
