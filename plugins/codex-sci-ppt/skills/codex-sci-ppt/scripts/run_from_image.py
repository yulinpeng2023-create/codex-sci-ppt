#!/usr/bin/env python3
"""Local image -> SVG -> geometry cache -> editable PPTX pipeline.

This intentionally mirrors Cell-PPT's high-level stages while replacing the
remote vectorization/API step with local OpenCV vectorization.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


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
    parser.add_argument("--colors", type=int, default=10)
    parser.add_argument("--max-paths", type=int, default=600)
    parser.add_argument("--min-area-ratio", type=float, default=0.00015)
    parser.add_argument("--epsilon-ratio", type=float, default=0.003)
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
        expected_pptx = job / f"{base_name}.pptx"
    else:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        base_name = args.job_name or output.stem or "codexscippt"
        work = Path(tempfile.mkdtemp(prefix=".codex-sci-ppt-", dir=output.parent))
        raw_svg = work / "vector.svg"
        master_svg = work / "master.svg"
        expected_pptx = output

    run(
        scripts / "vectorize_local.py",
        "--input-image", args.input_image.resolve(),
        "--output-svg", raw_svg,
        "--colors", args.colors,
        "--max-paths", args.max_paths,
        "--min-area-ratio", args.min_area_ratio,
        "--epsilon-ratio", args.epsilon_ratio,
    )

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
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
