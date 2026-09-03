# Codex Sci-PPT scene format

A scene is a JSON object describing one editable PowerPoint slide. Coordinates and dimensions are in inches. Objects are rendered in array order from back to front.

```json
{
  "slide": {"width": 13.333, "height": 7.5},
  "background": "#FFFFFF",
  "objects": [
    {"type": "beaker", "x": 0.8, "y": 1.5, "w": 1.4, "h": 2.0, "liquid_fill": "#D9EAF7", "label": "CS solution"},
    {"type": "arrow", "x1": 2.4, "y1": 2.5, "x2": 3.4, "y2": 2.5, "line_width": 2},
    {"type": "particle_cluster", "x": 3.6, "y": 1.7, "w": 1.6, "h": 1.6, "count": 12, "label": "Nanoparticles"},
    {"type": "text", "x": 0.5, "y": 0.4, "w": 5, "h": 0.5, "text": "Scientific workflow", "font_size": 24, "bold": true}
  ]
}
```

## General primitives

- `rect`, `round_rect`, `ellipse`
- `triangle`, `diamond`, `hexagon`, `chevron`, `cylinder`, `cloud`, `star`
- `line`, `arrow`
- `polygon`
- `droplet`
- `text`

Most shape objects use `x`, `y`, `w`, `h`. Lines and arrows use `x1`, `y1`, `x2`, `y2`.

Common style fields are `fill`, `line`, `line_width`, and `rotation`. Colors use `#RRGGBB`; `null` means no fill/line.

Text supports `text`, `font_size`, `font`, `bold`, `italic`, `align`, `valign`, `color`, `rotation`, and `word_wrap`.

## General scientific primitives

### `particle_cluster`
Creates independent editable circular particles.

### `layered_block`
For substrates, films, multilayer coatings, reservoirs, and cross-sections.

### `cell`
Creates an editable cell body and nucleus with optional internal particles.

### `membrane`
Creates a stylized editable bilayer.

### `beaker`
Creates a simplified vessel, liquid region, and optional editable label.

## High-fidelity reference-scene primitives

Use these with `scripts/render_reference_scene.py` when semantically redrawing a clean flat reference diagram.

### `uv_lamp`
Rounded editable lamp body plus a separate highlight strip. Fields: `x`, `y`, `w`, `h`, `fill`, `line`, `highlight`, `line_width`.

### `fan`
Editable outer ring, independent blades, hub, and optional label. Fields: `x`, `y`, `w`, `h`, `fill`, `line`, `blade_fill`, `blades`, `label`, `font_size`.

### `petri_dish`
Editable top/bottom ellipses, side lines, optional liquid/sample ellipse, and label. Fields: `x`, `y`, `w`, `h`, `fill`, `inner_fill`, `line`, `label`.

### `material_block`
Editable three-face perspective block for wood/bamboo/material samples with optional grain lines and label. Fields: `x`, `y`, `w`, `h`, `depth`, `skew`, `top_fill`, `front_fill`, `side_fill`, `grain_lines`, `label`.

### `dimension_arrow`
Double-ended editable dimension line with a live text label. Fields: `x1`, `y1`, `x2`, `y2`, `label`, `line`, `line_width`, `text_color`.

### `control_panel`
Editable panel body, digital readouts, indicator lamps, and analog clock. Fields: `x`, `y`, `w`, `h`, `fill`, `line`, `displays`, `display_font_size`, `indicators`.

See `examples/uva_chamber_scene.json` for a complete high-fidelity reference-scene example.

## Design guidance

For a supplied reference figure, first match its aspect ratio and relative geometry. Use source-relative coordinates before artistic improvement. Keep typography, line weights, spacing, and flat colors close to the reference. Reference-scene objects strip default theme styling/shadows to avoid PowerPoint adding unintended visual effects.

Prefer multiple semantic editable objects over one complex polygon. Never invent quantitative labels, dimensions, concentrations, scale bars, statistical symbols, or experimental results.
