#!/usr/bin/env python3
"""Local image -> SVG -> geometry cache -> editable PPTX pipeline.

This replaces Cell_ppt's remote vectorization call with local OpenCV tracing
while preserving the important intermediate SVG/cache/render stages.
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


def main():
    parser = argparse.ArgumentParser(
        description="Local image to editable PowerPoint. No API key or credits required."
    )
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--text-manifest", type=Path)
    parser.add_argument("--input-pptx", type=Path)
    parser.add_argument("--slide-index", type=int, default=0)
    parser.add_argument("--colors", type=int, default=10)
    parser.add_argument("--max-paths", type=int, default=600)
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    args.output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".sci-ppt-", dir=args.output.parent))
    raw_svg = work / "vector.svg"
    master_svg = work / "master.svg"

    run(
        scripts / "vectorize_local.py",
        "--input-image", args.input_image.resolve(),
        "--output-svg", raw_svg,
        "--colors", args.colors,
        "--max-paths", args.max_paths,
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

    command = [
        scripts / "run_from_svg.py",
        "--input-svg", master_svg,
        "--output-pptx", args.output.resolve(),
        "--slide-index", args.slide_index,
    ]
    if args.input_pptx:
        command += ["--input-pptx", args.input_pptx.resolve()]
    run(*command)

    print(
        json.dumps(
            {
                "ok": True,
                "master_svg": str(master_svg),
                "pptx": str(args.output.resolve()),
                "local_only": True,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
