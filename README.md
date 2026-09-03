# codex-sci-ppt

**Codex Sci-PPT — Scientific figure drawing and reconstruction with editable PowerPoint graphics.**

`codex-sci-ppt` is a local-first Codex skill for creating, rebuilding, and exporting scientific figures as editable PowerPoint (`.pptx`) graphics.

The reconstruction path intentionally stays close to the public MIT-licensed `yrui-cmd/cell-ppt` architecture. The main deliberate substitution is the paid/remote vectorization stage:

`text manifest -> local text-region cleanup -> local vectorization -> master SVG -> geometry cache -> exact duplicate removal -> editable native PowerPoint`

No Xiaomiao API key, upload, credit, or quota is required.

## Two workflows

1. **Reconstruction mode** — for uploaded raster scientific diagrams. The local pipeline creates a vector-only master SVG, parses it once into the same style of schema-v3 geometry cache used by Cell-PPT, keeps literal paint order, removes exact duplicate drawing paths only, and writes editable native PowerPoint custom geometry.
2. **Scene mode** — for new scientific drawings from a description. Codex generates a structured scene specification and `render_scene.py` creates separate editable shapes, arrows, labels, particles, cells, membranes, vessels, droplets, and layered structures.

Scene mode is usually cleaner for a brand-new publication schematic. Reconstruction mode is the closer replacement for Cell-PPT's image-to-editable-PPT workflow.

## What is aligned with Cell-PPT

The downstream reconstruction core now follows the same important contracts: vector-only master SVG, live-text merge, schema-v3 geometry cache, SVG transforms and style inheritance, cubic Bézier geometry, literal source order, ordinary 20–50 atom batches, exact duplicate-path filtering, and editable OOXML custom geometry. See `UPSTREAM_PARITY.md` and `THIRD_PARTY_NOTICES.md`.

The main remaining parity gap is Windows live PowerPoint COM drawing; v0.1.x currently routes reconstruction through saved editable OOXML on all platforms.

## Install

Python 3.11+ is recommended.

```bash
git clone https://github.com/yulinpeng2023-create/codex-sci-ppt.git
cd codex-sci-ppt
python -m pip install -r requirements.txt
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

macOS/Linux:

```bash
bash setup.sh
```

## Codex usage

```text
使用 $codex-sci-ppt，根据我的实验方法绘制一张科研示意图，输出可编辑 PPTX。
```

```text
使用 $codex-sci-ppt，把我上传的科研图片重绘成可编辑 PowerPoint 图形。
```

## Command-line examples

Create a new editable scientific scene:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/render_scene.py \
  --scene examples/simple_scene.json \
  --output output.pptx
```

Reconstruct an image directly to a PPTX:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/run_from_image.py \
  --input-image figure.png \
  --output output.pptx
```

Cell-PPT-like job-folder output is also supported:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/run_from_image.py \
  --input-image figure.png \
  --output-root outputs
```

If a text manifest includes optional `bbox` fields, the corresponding raster text regions are locally inpainted before vectorization and then restored as live editable text.

## Diagnostics and self-test

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/doctor.py
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/selftest.py
```

The self-test exercises SVG validation, transformed/cubic geometry caching, duplicate-path removal, editable OOXML reopening, scene rendering, local raster vectorization, raster-text cleanup, live-text restoration, and job allocation.

## Limitations

The local vectorizer is deterministic and has no API cost, but its fidelity ceiling is still lower than a strong dedicated vectorization model/service. Flat-color scientific diagrams, flowcharts, cartoons, and mechanism figures work best. Complex gradients, textured microscopy panels, photographs, heavy transparency, shadows, and anti-aliased decorative artwork may require cleanup or semantic redraw.

## License

MIT License.

## Acknowledgements

Codex Sci-PPT is a local-first implementation built around the public MIT-licensed Cell-PPT architecture. Substantial adapted portions and their license notice are documented in `THIRD_PARTY_NOTICES.md`.