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

Use reconstruction mode when the user explicitly wants an uploaded raster diagram rebuilt and semantic redraw is not practical. Run `scripts/run_from_image.py`. The local vectorizer can recover ordinary paths plus editable rectangles, rotated rectangles, ellipses, and conservative thin stroked lines before the SVG/cache/OOXML rendering stages.

Reconstruction works best for flat-color diagrams, cartoons, flowcharts, icons, and simple scientific schematics. For photographs, microscopy images, dense textures, complex gradients, shadows, or transparency-heavy artwork, state that local reconstruction is approximate and prefer semantic scene reconstruction when possible.

If known text is present in the source figure, prefer supplying a text manifest with bounding boxes so raster text can be removed before tracing and restored as native editable text. Thin-line recovery is enabled by default; use `--no-line-recovery` only when a long narrow filled bar is being misclassified as a connector/stroke.

## Reusable bamboo cross-section template

When a figure needs a bamboo transverse-section field, bamboo wall matrix, vascular bundles, coating-on-bamboo cross section, penetration/release schematic, or bamboo anatomy zoom panel, read `references/bamboo-template.md` and start from:

`templates/bamboo_cross_section.json`

Render it with:

`python scripts/render_bamboo_template.py --config templates/bamboo_cross_section.json --output <output.pptx>`

The template is based on a user-supplied bamboo cross-section PowerPoint visual. It creates a deterministic warm golden matrix texture and stylized bamboo vascular bundles. The matrix is a raster texture layer; every vascular bundle is built from separate native editable PowerPoint shapes so it can be moved, recolored, resized, deleted, or reused in later figures.

Treat the template as schematic anatomy only. Do not infer quantitative vascular-bundle density, size, dimensions, or scale from it unless the user supplies measured data.

## Reusable bamboo board — 5 × 2 × 0.5 cm

When the user needs the standard bamboo specimen block used in experiments, prefer the reusable board renderer rather than inventing a generic cuboid. The physical dimensions are fixed by default to **5 cm longitudinal × 2 cm transverse × 0.5 cm thickness** (`10:4:1`). The 2 × 0.5 cm transverse end faces the viewer so the vascular-bundle field is visible; the 5 cm direction recedes longitudinally.

Start from:

`templates/bamboo_board_5x2x05.json`

Render it with:

`python scripts/render_bamboo_board.py --config templates/bamboo_board_5x2x05.json --output <output.pptx>`

Important drawing rules for this board:

- keep the 5:2:0.5 physical dimensions and do not visually turn it into a thick block;
- put vascular bundles only on the transverse 2 × 0.5 cm end face;
- distribute vascular bundles irregularly, with mixed spacing and slight size variation rather than a grid;
- use smaller/denser bundles toward the outer side and somewhat larger/sparser bundles inward when a schematic gradient is helpful;
- keep top and long-side grain sparse and longitudinal, never as dense evenly spaced ruled lines;
- keep all visible faces geometrically connected so the result reads as one solid board;
- keep vascular bundles as separate editable PowerPoint objects.

## Scientific drawing workflow

1. Identify the scientific story: input/material -> treatment/process -> structure/mechanism -> outcome.
2. For a reference redraw, run the local analyzer before manually estimating geometry.
3. If the figure contains a bamboo cross section or the standard 5 × 2 × 0.5 cm bamboo specimen, check the reusable bamboo templates before drawing from scratch.
4. Identify semantic objects such as substrate, coating, reservoir, particles, cells, vessels, arrows, labels, and callouts.
5. Match the source aspect ratio and source-relative coordinates before polishing style.
6. Use the smallest set of native editable primitives that communicates the science accurately.
7. Keep repeated particles/cells/vascular bundles as independent editable objects where practical.
8. Use concise labels and consistent typography.
9. Render the scene and reopen the PPTX to verify integrity.

## Drawing rules

- Keep text as native PowerPoint text boxes whenever wording is known.
- Keep meaningful objects separate: cells, particles, arrows, substrates, coatings, labels, vessels, membranes, fibers, vascular bundles, and legends should not be flattened together.
- Prefer simple PowerPoint primitives when possible.
- Preserve logical layer order from background to foreground.
- Use restrained scientific styling, consistent line widths, typography, spacing, and arrow conventions.
- Do not fabricate measured data, scale bars, statistical significance, concentrations, dimensions, experimental results, or molecular structures not supplied by the user.
- If the user supplies scientific values or labels, preserve them exactly unless asked to edit them.
- Save editable `.pptx` as the primary output.
- Do not claim pixel-perfect reconstruction for local raster tracing.

## Local-first policy

Codex Sci-PPT does not require a Xiaomiao API key, paid vectorization credits, or an upload to a third-party vectorization service. Do not request such credentials.

Keep reconstruction stages modular: vector master -> live text -> geometry cache -> exact duplicate-path filtering -> native editable PowerPoint objects. Reference analysis, semantic redraws, and reusable scientific templates are additive layers and should not break the reconstruction path.

Do not introduce SVG features rejected by the current geometry-cache contract merely for appearance. In particular, native SVG gradients are not part of the supported cache subset and should be expanded or approximated with ordinary solid geometry instead.

## Commands

Scene mode:

`python scripts/render_scene.py --scene <scene.json> --output <output.pptx>`

Bamboo cross-section template:

`python scripts/render_bamboo_template.py --config templates/bamboo_cross_section.json --output <output.pptx>`

Bamboo board 5 × 2 × 0.5 cm:

`python scripts/render_bamboo_board.py --config templates/bamboo_board_5x2x05.json --output <output.pptx>`

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

Bamboo-template regression:

`python scripts/bamboo_template_selftest.py`

Bamboo-board regression:

`python scripts/bamboo_board_selftest.py`

## Completion check

Before reporting success, confirm that the output PPTX exists, reopens with `python-pptx`, has at least one slide, and contains editable shapes. For scene/reference-scene mode, verify expected text boxes are present. For bamboo-template output, verify the vascular bundles remain separate editable shapes. For the 5 × 2 × 0.5 cm bamboo board, verify that the front transverse end retains a 4:1 width-to-thickness aspect, the board reads as a closed solid prism, vascular bundles remain on that end face, and their spacing is visibly nonuniform. For reference analysis, inspect the debug overlay and treat low-confidence primitive guesses as hints only. For reconstruction mode, inspect the reported primitive counts and geometry diagnostics when useful, and report that reconstruction is approximate rather than claiming pixel-perfect fidelity.
