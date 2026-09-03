#!/usr/bin/env python3
"""Codex Sci-PPT master SVG -> geometry cache -> editable PPTX wrapper.

Supports both a Cell-PPT-like output-root/job workflow and a direct
--output-pptx convenience mode.
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-svg", required=True, type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--output-pptx", type=Path)
    parser.add_argument("--input-pptx", type=Path)
    parser.add_argument("--slide-index", type=int, default=0)
    parser.add_argument("--job-name")
    args = parser.parse_args()

    if bool(args.output_root) == bool(args.output_pptx):
        parser.error("provide exactly one of --output-root or --output-pptx")

    scripts = Path(__file__).resolve().parent
    input_svg = args.input_svg.resolve()

    if args.output_root:
        output_root = args.output_root.expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        base_name = args.job_name or allocate_name(scripts, output_root)
        if not base_name:
            raise SystemExit("empty job name")
        job = output_root / base_name
        cache_dir = job / ".codex-sci-ppt-cache"
        output = job / f"{base_name}.pptx"
        job.mkdir(parents=True, exist_ok=True)
    else:
        output = args.output_pptx.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        base_name = args.job_name or output.stem or "codexscippt"
        cache_dir = Path(tempfile.mkdtemp(prefix=".codex-sci-ppt-cache-", dir=output.parent))

    run(scripts / "validate_vector_svg.py", "--svg", input_svg)
    run(
        scripts / "prepare_geometry_cache.py",
        "--input", input_svg,
        "--output-dir", cache_dir,
        "--job-id", base_name,
    )
    run(
        scripts / "cull_hidden_geometry.py",
        "--cache", cache_dir / "geometry-cache.json",
        "--state", cache_dir / "drawing-state.json",
    )

    command = [
        scripts / "run_cell_ppt_ooxml.py",
        "--geometry-cache", cache_dir / "geometry-cache.json",
        "--output-pptx", output,
        "--slide-index", args.slide_index,
    ]
    if args.input_pptx:
        command += ["--input-pptx", args.input_pptx.resolve()]
    run(*command)

    print(json.dumps({
        "ok": True,
        "base_name": base_name,
        "pptx": str(output),
        "cache": str(cache_dir),
        "backend": "editable-ooxml",
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
