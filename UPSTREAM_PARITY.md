# Cell-PPT parity notes

Codex Sci-PPT is intentionally designed as a local/no-API variant of the public MIT-licensed `yrui-cmd/cell-ppt` architecture rather than as an unrelated PowerPoint drawing project.

## Pipeline comparison

| Stage | Cell-PPT | Codex Sci-PPT | Status |
| --- | --- | --- | --- |
| Raster input | PNG/JPEG/WebP | PNG/JPEG/WebP | aligned |
| Text manifest | live-text manifest merged into SVG | same schema and merge model | aligned |
| Vectorization | Xiaomiao remote API / credits | local OpenCV vectorization | intentionally replaced |
| Master SVG | required vector-only SVG | required vector-only SVG | aligned |
| SVG validation | raster/external-reference/ID audit | same validation contract | aligned |
| SVG parse | single parse into schema-v3 cache | schema-v3 cache with transforms/styles | aligned |
| Geometry | line + cubic Bézier anchors/handles | same cache representation | aligned |
| Paint order | literal source order | literal source order | aligned |
| Duplicate filtering | exact duplicate drawing paths only | exact duplicate drawing paths only | aligned |
| Batch planning | ordinary 20-50, complex singleton | same planning contract | aligned |
| macOS/headless renderer | editable OOXML custom geometry | editable OOXML custom geometry | aligned |
| Existing PPTX append | supported | supported | aligned |
| Direct local output | not the primary upstream CLI | supported as convenience | extension |
| Structured scientific scene mode | not the core upstream path | native editable scientific primitives | extension |
| Windows live COM drawing | supported upstream | not yet routed in v0.1.x | remaining gap |
| WPS COM | experimental upstream | not yet routed | remaining gap |
| API key / quota / credit gate | required for vectorization | absent | intentionally removed |

## Design rule

When upstream behavior concerns SVG geometry, paint order, text, duplicate removal, caching, or editable OOXML, Codex Sci-PPT should stay compatible unless there is a documented reason to improve it. The main intentional substitution is:

`remote Xiaomiao vectorizer -> local vectorizer`

Enhancements such as scene mode should sit beside the reconstruction pipeline, not replace or distort the compatible pipeline.

## Current largest technical difference

The quality ceiling is now the local raster-to-vector stage. Cell-PPT can receive a higher-quality path-return SVG from its remote service; Codex Sci-PPT currently uses deterministic local color quantization and contour tracing. For clean diagrams this is useful, but complex gradients, shadows, anti-aliased text, photographs, microscopy panels, and dense textured illustrations remain harder to reconstruct faithfully.

Future optimization should therefore prioritize local vectorization quality and optional local text-region cleanup while preserving the downstream SVG/cache/OOXML contract.