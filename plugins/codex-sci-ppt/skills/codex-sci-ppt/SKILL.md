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

When the user supplies a clean flat scientific schematic and visual similarity matters more than blind tracing, use reference-scene mode.

First run the local analyzer:

`python scripts/analyze_reference.py --input-image <image> --analysis <analysis.json> --scene-draft <draft.json> --debug-overlay <overlay.png>`

Use the analyzer output to seed layout instead of estimating everything from scratch. It provides source aspect ratio, background, dominant palette, frame candidates, connected-component bounding boxes, primitive guesses, rotation estimates, and text-like regions. Treat primitive labels as hints rather than ground truth.

Then refine the draft semantically and render with:

`python scripts/render_reference_scene.py --scene <scene.json> --output <output.pptx>`

Reference-scene mode adds publication-style primitives common in experimental schematics: `uv_lamp`, `fan`, `petri_dish`, `material_block`, `dimension_arrow`, and `control_panel`. Match source-relative coordinates before beautifying. Theme shadows/styles are stripped so output stays close to the reference artwork.

The analyzer deliberately does not invent OCR text. When wording is visible to the model or supplied by the user, replace text-like regions with native editable text boxes. Do not guess unreadable labels.

### Reconstruction mode — approximate local rebuild

Use reconstruction mode when the user explicitly wants an uploaded raster diagram rebuilt and semantic redraw is not practical. Run `scripts/run_from_image.py`. The local vectorizer can recover ordinary paths plus editable rectangles, rotated rectangles, ellipses, and conservative thin stroked lines before the Cell-PPT-compatible SVG/cache/OOXML stages.

Reconstruction works best for flat-color diagrams, cartoons, flowcharts, icons, and simple scientific schematics. For photographs, microscopy images, dense textures, complex gradients, shadows, or transparency-heavy artwork, state that local reconstruction is approximate and prefer semantic scene reconstruction when possible.

If known text is present in the source figure, prefer supplying a text manifest with bounding boxes so raster text can be removed before tracing and restored as native editable text. Thin-line recovery is enabled by default; use `--no-line-recovery` only when a long narrow filled bar is being misclassified as a connector/stroke.

## Scientific drawing workflow

1. Identify the scientific story: input/material -> treatment/process -> structure/mechanism -> outcome.
2. For a reference redraw, run the local analyzer before manually estimating geometry.
3. Identify semantic objects such as substrate, coating, reservoir, particles, cells, vessels, arrows, labels, and callouts.
4. Match the source aspect ratio and source-relative coordinates before polishing style.
5. Use the smallest set of native editable primitives that communicates the science accurately.
6. Keep repeated particles/cells as independent editable objects where practical.
7. Use concise labels and consistent typography.
8. Render the scene and reopen the PPTX to verify integrity.

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

Reference-scene analysis/rendering is an additive extension. It must not replace or distort the Cell-PPT-compatible reconstruction pipeline.

Do not introduce SVG features rejected by the shared geometry-cache contract merely for appearance. In particular, native SVG gradients are not part of the supported cache subset and should be expanded/approximated with ordinary solid geometry instead.

## Commands

Scene mode:

`python scripts/render_scene.py --scene <scene.json> --output <output.pptx>`

Reference analyzer:

`python scripts/analyze_reference.py --input-image <image> --analysis <analysis.json> --scene-draft <draft.json> --debug-overlay <overlay.png>`

Reference-scene renderer:

`python scripts/render_reference_scene.py --scene <scene.json> --output <output.pptx>`

Reconstruction mode:

`python scripts/run_from_image.py --input-image <image> --output <output.pptx>`

Diagnostics:

`python scripts/doctor.py`

End-to-end self-test:

`python scripts/selftest.py`

Reference-scene regression:

`python scripts/reference_scene_selftest.py`

Reference-analyzer regression:

`python scripts/test_reference_analyzer.py`

## Completion check

Before reporting success, confirm that the output PPTX exists, reopens with `python-pptx`, has at least one slide, and contains editable shapes. For scene/reference-scene mode, verify expected text boxes are present. For reference analysis, inspect the debug overlay and treat low-confidence primitive guesses as hints only. For reconstruction mode, inspect the reported primitive counts and geometry diagnostics when useful, and report that reconstruction is approximate rather than claiming pixel-perfect fidelity.
