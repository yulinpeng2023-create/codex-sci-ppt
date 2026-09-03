#!/usr/bin/env python3
"""Sci-PPT master SVG -> geometry cache -> editable PPTX wrapper."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-svg", required=True, type=Path)
    parser.add_argument("--output-pptx", required=True, type=Path)
    parser.add_argument("--input-pptx", type=Path)
    parser.add_argument("--slide-index", type=int, default=0)
    parser.add_argument("--job-name", default="scippt")
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    args.output_pptx.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".sci-ppt-cache-", dir=args.output_pptx.parent))

    run(scripts / "validate_vector_svg.py", "--svg", args.input_svg.resolve())
    run(
        scripts / "prepare_geometry_cache.py",
        "--input", args.input_svg.resolve(),
        "--output-dir", work,
        "--job-id", args.job_name,
    )
    run(scripts / "cull_duplicate_geometry.py", "--cache", work / "geometry-cache.json")

    command = [
        scripts / "run_cell_ppt_ooxml.py",
        "--geometry-cache", work / "geometry-cache.json",
        "--output-pptx", args.output_pptx.resolve(),
        "--slide-index", args.slide_index,
    ]
    if args.input_pptx:
        command += ["--input-pptx", args.input_pptx.resolve()]
    run(*command)

    print(
        json.dumps(
            {
                "ok": True,
                "pptx": str(args.output_pptx.resolve()),
                "cache": str(work),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
