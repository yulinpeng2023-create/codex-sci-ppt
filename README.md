# codex-sci-ppt

**Codex Sci-PPT — Scientific figure drawing and reconstruction with editable PowerPoint graphics.**

`codex-sci-ppt` is a local-first Codex skill for creating, rebuilding, and exporting scientific figures as editable PowerPoint (`.pptx`) graphics.

The reconstruction pipeline runs locally:

`text manifest -> local text-region cleanup -> local vectorization -> master SVG -> geometry cache -> exact duplicate removal -> editable native PowerPoint`

No Xiaomiao API key, upload, credit, or quota is required.

## Three workflows

1. **Reconstruction mode** — for uploaded raster scientific diagrams. A local vectorizer converts suitable artwork into editable PowerPoint geometry through the SVG/cache/OOXML pipeline.
2. **Reference-scene mode** — for clean flat scientific schematics where visual similarity matters. A local reference analyzer estimates layout/style from the image, then semantic PowerPoint primitives are used for a cleaner editable redraw.
3. **Scene mode** — for brand-new figures from a description. Structured scene JSON creates separate editable scientific shapes, arrows, labels, particles, cells, membranes, vessels, droplets, and layered structures.

## Reusable scientific templates

Version 0.1.6 adds the first reusable material template: a **bamboo cross-section field** based on a user-supplied PowerPoint schematic. It generates a warm golden parenchyma matrix and repeated stylized vascular bundles. The matrix texture is generated locally; vascular bundles are separate native PowerPoint shapes and remain editable.

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/render_bamboo_template.py \
  --config plugins/codex-sci-ppt/skills/codex-sci-ppt/templates/bamboo_cross_section.json \
  --output bamboo-cross-section.pptx
```

Use it as a starting layer for bamboo anatomy panels, coating cross sections, penetration/release figures, zoom callouts, or other bamboo-material schematics. It is a schematic template, not a source of quantitative anatomical data.

## Local vectorizer v3

The no-API vectorizer uses a deterministic LAB/contour pipeline with PowerPoint-friendly geometry recovery:

- deterministic LAB clustering with large-image sampling;
- edge-preserving bilateral preprocessing and anti-alias palette merging;
- transparent-pixel exclusion for PNG artwork with alpha;
- native SVG rectangle and ellipse recovery;
- thin line recovery as real stroked SVG lines;
- rotated rectangle recovery using transformed native SVG rectangles;
- hole-aware vector paths for compound regions;
- palette diagnostics plus geometry-level metrics: `geometry_pixel_accuracy`, `geometry_foreground_accuracy`, and `geometry_foreground_iou`.

The current geometry-cache contract does not use native SVG `linearGradient` or `radialGradient` nodes. Smooth gradients are approximated with ordinary solid-color regions to keep reconstruction predictable and editable.

## Reference analyzer v1 — new in 0.1.5

`analyze_reference.py` is an API-free first pass for flat scientific reference figures. It estimates:

- source image size and aspect ratio;
- background color and dominant foreground palette;
- large frame candidates;
- connected-component bounding boxes and relative coordinates;
- high-confidence primitive guesses (`rect`, `round_rect`, `ellipse`, `line`);
- rotation estimates from minimum-area rectangles;
- text-like regions without inventing OCR content;
- a draft reference-scene JSON and optional debug overlay.

This reduces manual coordinate guessing. The analyzer is deliberately conservative: its labels are layout hints, not semantic truth. Codex or the user should still confirm whether a detected bar is a lamp, connector, sample, panel, etc.

Reference-scene mode also includes editable primitives such as `uv_lamp`, `fan`, `petri_dish`, `material_block`, `dimension_arrow`, and `control_panel`. The UVA chamber example in `examples/uva_chamber_scene.json` is a regression case for this workflow.

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
使用 $codex-sci-ppt，把我上传的科研图片按原图布局高保真重绘成可编辑 PowerPoint 图形。
```

## Command-line examples

Analyze a reference image locally and create a layout scaffold:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/analyze_reference.py \
  --input-image figure.png \
  --analysis reference-analysis.json \
  --scene-draft reference-draft.json \
  --debug-overlay reference-overlay.png
```

Render a refined high-fidelity reference scene:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/render_reference_scene.py \
  --scene examples/uva_chamber_scene.json \
  --output output.pptx
```

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

Job-folder output is also supported:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/run_from_image.py \
  --input-image figure.png \
  --output-root outputs
```

Optional reconstruction tuning:

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/run_from_image.py \
  --input-image figure.png \
  --output output.pptx \
  --colors 12 \
  --preprocess bilateral \
  --palette-merge-distance 6
```

If a text manifest includes optional `bbox` fields, the corresponding raster text regions are locally inpainted before vectorization and then restored as live editable text.

## Diagnostics and self-test

```bash
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/doctor.py
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/selftest.py
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/reference_scene_selftest.py
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/test_reference_analyzer.py
python plugins/codex-sci-ppt/skills/codex-sci-ppt/scripts/bamboo_template_selftest.py
```

CI runs the core pipeline, reference-scene renderer, reference analyzer, and bamboo-template regressions on Python 3.11 and 3.12.

## Limitations

The local vectorizer is deterministic and has no API cost, but its fidelity ceiling is still lower than a strong dedicated vectorization model/service. Flat-color scientific diagrams, flowcharts, cartoons, and mechanism figures work best. Complex gradients, textured microscopy panels, photographs, heavy transparency, shadows, and decorative anti-aliased artwork may require cleanup or semantic redraw.

The reference analyzer does not perform semantic understanding or guaranteed OCR by itself. Its job is to reduce layout/style estimation work, not to guess scientific meaning.

## License

MIT License.

## Third-party notices

Required attribution and license notices for any adapted third-party code are kept in `THIRD_PARTY_NOTICES.md`.
