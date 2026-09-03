# sci-ppt

**Sci-PPT — Scientific figure drawing with editable PowerPoint graphics.**

`sci-ppt` is a local-first Codex skill for creating, rebuilding, and exporting scientific figures as editable PowerPoint (`.pptx`) graphics.

## Goals

- Create scientific schematics from a text description.
- Rebuild raster scientific figures into editable vector-like PowerPoint objects.
- Keep text editable as native PowerPoint text boxes.
- Work without a third-party API key or credit/quota system.
- Support Windows and macOS through ordinary `.pptx` generation.

## Current v0.1 scope

The first release focuses on a reliable local workflow:

`image / scene specification -> local geometry extraction -> editable PowerPoint`

Two workflows are provided:

1. **Scene mode** — recommended for high-quality scientific drawings. Codex turns the user's description into a small JSON scene specification, and `render_scene.py` creates native PowerPoint shapes and text.
2. **Trace mode** — converts a raster image into simplified editable polygon/freeform-like objects using local OpenCV contour extraction. It works best for diagrams with flat colors, clear boundaries, flowcharts, cartoons, and scientific schematics. It is not intended to perfectly reproduce photographs or complex gradients.

## Install

Python 3.11+ is recommended.

```bash
git clone https://github.com/yulinpeng2023-create/sci-ppt.git
cd sci-ppt
python -m pip install -r requirements.txt
```

On Windows you may also run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

On macOS/Linux:

```bash
bash setup.sh
```

## Codex usage

After installing the skill, you can ask:

```text
使用 $sci-ppt，根据我的实验方法绘制一张科研示意图，输出可编辑 PPTX。
```

or:

```text
使用 $sci-ppt，把我上传的科研图片重绘成可编辑 PowerPoint 图形。
```

## Command-line examples

Create an editable PPTX from a scene JSON file:

```bash
python plugins/sci-ppt/skills/sci-ppt/scripts/render_scene.py \
  --scene examples/simple_scene.json \
  --output output.pptx
```

Trace a raster image locally:

```bash
python plugins/sci-ppt/skills/sci-ppt/scripts/run_from_image.py \
  --input-image figure.png \
  --output output.pptx
```

Run diagnostics:

```bash
python plugins/sci-ppt/skills/sci-ppt/scripts/doctor.py
```

## Editing model

Objects created by Sci-PPT are intended to remain editable in PowerPoint. Text is stored as text boxes; rectangles, ellipses, arrows, lines, and polygons are created as separate PowerPoint shapes whenever possible.

## Limitations

Raster-to-vector reconstruction is inherently approximate. Complex gradients, textures, microscopy images, photographs, shadows, and overlapping semi-transparent objects may require manual cleanup. For publication-quality scientific schematics, **scene mode is preferred over blind tracing**.

## License

MIT License.

## Acknowledgements

Sci-PPT is an independent local-first implementation. The project was inspired by the general idea of reconstructing scientific figures as editable PowerPoint objects, but its local tracing and scene-rendering code are implemented independently.