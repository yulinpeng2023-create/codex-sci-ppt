# Sci-PPT scene format

A scene is a JSON object describing a single PowerPoint slide.

```json
{
  "slide": {"width": 13.333, "height": 7.5},
  "background": "#FFFFFF",
  "objects": [
    {"type": "rect", "x": 1, "y": 2, "w": 3, "h": 1, "fill": "#E8F1F8", "line": "#333333", "line_width": 1.5},
    {"type": "ellipse", "x": 5, "y": 2, "w": 1.2, "h": 1.2, "fill": "#F7D9A8", "line": "#333333"},
    {"type": "arrow", "x1": 4.1, "y1": 2.6, "x2": 4.9, "y2": 2.6, "line": "#333333", "line_width": 2},
    {"type": "text", "x": 1, "y": 3.2, "w": 3, "h": 0.5, "text": "Sample", "font_size": 18, "bold": false, "align": "center"}
  ]
}
```

Coordinates and dimensions are in inches.

Supported object types in v0.1:

- `rect`
- `round_rect`
- `ellipse`
- `line`
- `arrow`
- `polygon`
- `text`

Common style fields:

- `fill`: `#RRGGBB` or `null`
- `line`: `#RRGGBB` or `null`
- `line_width`: points
- `rotation`: degrees

Polygon objects use `points`, for example `[[1,1],[2,1],[2.5,2],[1,2]]`.

Text objects support `text`, `font_size`, `font`, `bold`, `italic`, `align`, `color`, and `rotation`.

The renderer intentionally keeps the schema small. Prefer several simple editable objects over one complicated object.