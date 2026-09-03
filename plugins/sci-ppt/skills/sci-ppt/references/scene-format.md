# Sci-PPT scene format

A scene is a JSON object describing one editable PowerPoint slide. Coordinates and dimensions are in inches. Objects are rendered in array order from back to front.

```json
{
  "slide": {"width": 13.333, "height": 7.5},
  "background": "#FFFFFF",
  "objects": [
    {"type": "beaker", "x": 0.8, "y": 1.5, "w": 1.4, "h": 2.0, "liquid_fill": "#D9EAF7", "label": "CS solution"},
    {"type": "arrow", "x1": 2.4, "y1": 2.5, "x2": 3.4, "y2": 2.5, "line_width": 2},
    {"type": "particle_cluster", "x": 3.6, "y": 1.7, "w": 1.6, "h": 1.6, "count": 12, "label": "Nanoparticles"},
    {"type": "layered_block", "x": 6.0, "y": 1.7, "w": 2.5, "h": 1.4, "layers": [
      {"label": "top coating", "ratio": 0.3, "fill": "#D9D2E9"},
      {"label": "reservoir", "ratio": 0.3, "fill": "#FFF2CC"},
      {"label": "substrate", "ratio": 1.0, "fill": "#D9EAD3"}
    ]},
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

## Scientific primitives

### `particle_cluster`

Creates independent editable circular particles. Fields: `x`, `y`, `w`, `h`, `count`, `diameter`, `fill`, `line`, and optional `label`.

### `layered_block`

For substrates, films, multilayer coatings, reservoirs, and cross-sections. `layers` is an array. Each layer can contain `label`, `ratio`, `fill`, `line`, `line_width`, `font_size`, and `text_color`.

### `cell`

Creates an editable cell body and nucleus with optional internal particles. Fields include `x`, `y`, `w`, `h`, `fill`, `line`, `nucleus_fill`, `nucleus_line`, `particles`, `particle_fill`, and `label`.

### `membrane`

Creates a stylized editable bilayer. Fields: `x`, `y`, `w`, `spacing`, `head`, `tail`, `head_fill`, `line`, and `tail_line`.

### `beaker`

Creates a simplified vessel, liquid region, and optional editable label. Fields include `x`, `y`, `w`, `h`, `liquid_fraction`, `liquid_fill`, `line`, and `label`.

## Design guidance

Prefer multiple semantic editable objects over one complex polygon. Use primitives for meaning, not photorealism. A coating should normally be a `layered_block`; dispersed material can be a `particle_cluster`; biological mechanisms can combine `cell`, `membrane`, particles, arrows, droplets, and text.

Never invent quantitative labels, dimensions, concentrations, scale bars, statistical symbols, or experimental results.