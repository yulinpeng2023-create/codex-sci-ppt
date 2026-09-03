---
name: codex-sci-ppt
description: Create scientific schematics, mechanism diagrams, experimental workflows, material structures, graphical abstracts, and simplified reconstructions of uploaded figures as editable PowerPoint objects. Use when the user wants to draw a scientific figure with PowerPoint, convert a suitable diagram into editable PPTX, or create an editable scientific illustration from a text description.
---

# Codex Sci-PPT

Codex Sci-PPT is a local-first scientific drawing skill. Prefer native editable PowerPoint shapes and text over flattened images.

Read `references/scene-format.md` before creating a scene.

## Choose a workflow

### Scene mode — default for new figures

Use scene mode for experiments, mechanisms, workflows, material structures, graphical abstracts, coatings, nanoparticles, biological diagrams, and other scientific schematics. Translate the request into a JSON scene and run `scripts/render_scene.py`.

Use semantic scientific primitives when they fit: `particle_cluster`, `layered_block`, `cell`, `membrane`, `beaker`, and `droplet`. Combine them with ordinary editable shapes, arrows, polygons, and text. Prefer several meaningful objects over one monolithic shape.

### Reference-scene mode — high-fidelity semantic redraw

When the user supplies a clean flat scientific schematic and visual similarity matters more than automatic tracing, use `scripts/render_reference_scene.py`. Rebuild the reference semantically with native editable PowerPoint objects instead of raster tracing.

Reference-scene mode adds publication-style primitives that are common in experimental schematics: `uv_lamp`, `fan`, `petri_dish`, `material_block`, `dimension_arrow`, and `control_panel`. Use exact reference proportions, small line widths, matching typography, and restrained flat fills. Theme shadows/styles are stripped so the output remains closer to the source artwork.

### Reconstruction mode — approximate local rebuild

Use reconstruction mode when the user explicitly wants an uploaded raster diagram rebuilt and semantic redraw is not practical. Run `scripts/run_from_image.py`. The local vectorizer can recover ordinary paths plus editable rectangles, rotated rectangles, ellipses, and conservative thin stroked lines before the Cell-PPT-compatible SVG/cache/OOXML stages.

Reconstruction works best for flat-color diagrams, cartoons, flowcharts, icons, and simple scientific schematics. For photographs, microscopy images, dense textures, complex gradients, shadows, or transparency-heavy artwork, state that local reconstruction is approximate and prefer semantic scene reconstruction when possible.

If known text is present in the source figure, prefer supplying a text manifest with bounding boxes so raster text can be removed before tracing and restored as native editable text. Thin-line recovery is enabled by default; use `--no-line-recovery` only when a long narrow filled bar is being misclassified as a connector/stroke.

## Scientific drawing workflow

1. Identify the scientific story: input/material -> treatment/process -> structure/mechanism -> outcome.
2. Identify semantic objects such as substrate, coating, reservoir, particles, cells, vessels, arrows, labels, and callouts.
3. For reference redraws, match the source aspect ratio and place objects by source-relative coordinates before beautifying.
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

Reference-scene mode is an additive extension. It must not replace or distort the Cell-PPT-compatible reconstruction pipeline.

Do not introduce SVG features rejected by the shared geometry-cache contract merely for appearance. In particular, native SVG gradients are not part of the supported cache subset and should be expanded/approximated with ordinary solid geometry instead.

## Commands

Scene mode:

`python scripts/render_scene.py --scene <scene.json> --output <output.pptx>`

Reference-scene mode:

`python scripts/render_reference_scene.py --scene <scene.json> --output <output.pptx>`

Reconstruction mode:

`python scripts/run_from_image.py --input-image <image> --output <output.pptx>`

Diagnostics:

`python scripts/doctor.py`

End-to-end self-test:

`python scripts/selftest.py`

Reference-scene regression:

`python scripts/reference_scene_selftest.py`

## Completion check

Before reporting success, confirm that the output PPTX exists, reopens with `python-pptx`, has at least one slide, and contains editable shapes. For scene/reference-scene mode, verify expected text boxes are present. For reconstruction mode, inspect the reported primitive counts and geometry diagnostics when useful, and report that reconstruction is approximate rather than claiming pixel-perfect fidelity.
