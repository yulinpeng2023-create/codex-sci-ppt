---
name: codex-sci-ppt
description: Create scientific schematics, mechanism diagrams, experimental workflows, material structures, graphical abstracts, and simplified reconstructions of uploaded figures as editable PowerPoint objects. Use when the user wants to draw a scientific figure with PowerPoint, convert a suitable diagram into editable PPTX, or create an editable scientific illustration from a text description.
---

# Codex Sci-PPT

Codex Sci-PPT is a local-first scientific drawing skill. Prefer native editable PowerPoint shapes and text over flattened images.

Read `references/scene-format.md` before creating a scene.

## Choose a workflow

### Scene mode — default and preferred

Use scene mode for experiments, mechanisms, workflows, material structures, graphical abstracts, coatings, nanoparticles, biological diagrams, and other scientific schematics. Translate the request into a JSON scene and run `scripts/render_scene.py`.

Use semantic scientific primitives when they fit: `particle_cluster`, `layered_block`, `cell`, `membrane`, `beaker`, and `droplet`. Combine them with ordinary editable shapes, arrows, polygons, and text. Prefer several meaningful objects over one monolithic shape.

### Trace mode — approximate reconstruction

Use trace mode when the user explicitly wants an uploaded raster diagram rebuilt and semantic redraw is not practical. Run `scripts/run_from_image.py`. It uses local image processing and creates separate editable polygon objects for retained regions.

Trace mode works best for flat-color diagrams, cartoons, flowcharts, icons, and simple scientific schematics. For photographs, microscopy images, dense textures, complex gradients, or transparency-heavy figures, state that blind tracing is approximate and prefer semantic scene reconstruction when possible.

## Scientific drawing workflow

1. Identify the scientific story: input/material -> treatment/process -> structure/mechanism -> outcome.
2. Identify semantic objects such as substrate, coating, reservoir, particles, cells, vessels, arrows, labels, and callouts.
3. Lay out the figure left-to-right or top-to-bottom with a clear visual hierarchy.
4. Use the smallest set of native editable primitives that communicates the science accurately.
5. Keep repeated particles/cells as independent editable objects where practical.
6. Use concise labels and consistent typography.
7. Render the scene and reopen the PPTX to verify integrity.

## Drawing rules

- Keep text as native PowerPoint text boxes whenever wording is known.
- Keep meaningful objects separate: cells, particles, arrows, substrates, coatings, labels, vessels, membranes, fibers, and legends should not be flattened together.
- Prefer simple PowerPoint primitives when possible.
- Preserve logical layer order from background to foreground.
- Use restrained scientific styling, consistent line widths, typography, spacing, and arrow conventions.
- Do not fabricate measured data, scale bars, statistical significance, concentrations, dimensions, experimental results, or molecular structures not supplied by the user.
- If the user supplies scientific values or labels, preserve them exactly unless asked to edit them.
- Save editable `.pptx` as the primary output.
- Do not claim pixel-perfect reconstruction for local raster tracing.

## Local-first policy

Codex Sci-PPT does not require a Xiaomiao API key, paid vectorization credits, or an upload to a third-party vectorization service. Do not request such credentials.

The reconstruction architecture should stay close to the public MIT-licensed Cell-PPT pipeline where practical: vector master -> live text -> geometry cache -> exact duplicate-path filtering -> native editable PowerPoint objects. The Xiaomiao vectorization stage is replaced by local processing rather than bypassed.

## Commands

Scene mode:

`python scripts/render_scene.py --scene <scene.json> --output <output.pptx>`

Trace mode:

`python scripts/run_from_image.py --input-image <image> --output <output.pptx>`

Diagnostics:

`python scripts/doctor.py`

## Completion check

Before reporting success, confirm that the output PPTX exists, reopens with `python-pptx`, has at least one slide, and contains editable shapes. For scene mode, verify expected text boxes are present. For trace mode, report that reconstruction is approximate rather than claiming pixel-perfect fidelity.
