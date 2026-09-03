---
name: sci-ppt
description: Create scientific schematics, mechanism diagrams, workflows, graphical abstracts, and simplified reconstructions of uploaded figures as editable PowerPoint objects. Use when the user wants to draw a scientific figure with PowerPoint, convert a suitable diagram into editable PPTX, or create an editable scientific illustration from a text description.
---

# Sci-PPT

Sci-PPT is a local-first scientific drawing skill. Prefer native editable PowerPoint shapes and text over flattened images.

## Choose a workflow

### 1. Scene mode — preferred

Use scene mode when the user describes an experiment, mechanism, workflow, material structure, graphical abstract, or scientific schematic. Translate the requested figure into the JSON scene format documented in `references/scene-format.md`, then run `scripts/render_scene.py`.

Scene mode is the default because it produces cleaner and more semantically editable figures than blind raster tracing.

### 2. Trace mode

Use trace mode when the user explicitly wants an uploaded raster diagram rebuilt. Run `scripts/run_from_image.py`. It uses only local image processing and creates separate editable polygon objects for retained regions.

Trace mode works best for flat-color diagrams, cartoons, flowcharts, icons, and simple scientific schematics. Warn briefly when the source is a photograph, microscopy image, dense texture, complex gradient, or highly transparent composition because exact reconstruction is not expected.

## Drawing rules

- Keep text as native PowerPoint text boxes whenever the wording is known.
- Keep meaningful objects separate: cells, particles, arrows, substrates, coatings, labels, vessels, membranes, fibers, and legends should not be flattened together.
- Prefer simple PowerPoint primitives when possible: rectangles, rounded rectangles, ellipses, lines, arrows, and freeform polygons.
- Preserve logical layer order from background to foreground.
- Use restrained scientific styling and consistent line widths, typography, spacing, and arrow conventions.
- Do not fabricate measured data, scale bars, statistical significance, concentrations, dimensions, or experimental results.
- If the user supplies scientific values or labels, preserve them exactly unless asked to edit them.
- Save editable `.pptx` as the primary output.

## Local-first policy

Sci-PPT does not require a Xiaomiao API key, paid vectorization credits, or an upload to a third-party vectorization service. Do not request such credentials.

## Commands

Scene mode:

`python scripts/render_scene.py --scene <scene.json> --output <output.pptx>`

Trace mode:

`python scripts/run_from_image.py --input-image <image> --output <output.pptx>`

Diagnostics:

`python scripts/doctor.py`

## Completion check

Before reporting success, confirm that the output PPTX exists, reopens with `python-pptx`, has at least one slide, and contains editable shapes. For scene mode, verify that expected text boxes are present. For trace mode, report that the reconstruction is approximate rather than claiming pixel-perfect fidelity.
