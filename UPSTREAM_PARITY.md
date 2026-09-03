# Cell-PPT parity notes

Codex Sci-PPT is intentionally designed as a local/no-API variant of the public MIT-licensed `yrui-cmd/cell-ppt` architecture rather than as an unrelated PowerPoint drawing project.

## Pipeline comparison

| Stage | Cell-PPT | Codex Sci-PPT | Status |
| --- | --- | --- | --- |
| Raster input | PNG/JPEG/WebP | PNG/JPEG/WebP | aligned |
| Text manifest | live-text manifest merged into SVG | same schema and merge model | aligned |
| Vectorization | Xiaomiao remote API / credits | deterministic local vectorizer | intentionally replaced |
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

## Local vectorizer status

The v0.1.2 local vectorizer uses LAB clustering, deterministic pixel sampling for large images, mild edge-preserving preprocessing, anti-alias palette merging, transparent-pixel exclusion, hole-aware paths, and confident rectangle/ellipse recovery. It reports palette reconstruction diagnostics and is covered by deterministic end-to-end tests.

This is still not equivalent to the remote Xiaomiao service. The upstream wrapper receives a finished path-return SVG from the remote service; therefore the service's internal image understanding and tracing quality are outside the public Cell-PPT repository and cannot simply be reproduced by copying its visible code. Codex Sci-PPT keeps the public downstream contracts and replaces only that unavailable remote stage with local processing.

## Current largest technical differences

1. **Raster-to-vector fidelity.** Clean flat-color diagrams now work substantially better than the first local tracer, but complex gradients, shadows, dense textures, photography, microscopy panels, and decorative anti-aliasing remain harder than a dedicated vectorization model/service.
2. **Windows live drawing.** Cell-PPT can route drawing through live PowerPoint COM on Windows. Codex Sci-PPT v0.1.x currently uses editable saved OOXML on all platforms.
3. **WPS live backend.** Upstream has an experimental WPS COM route; this has not yet been ported.

Future optimization should improve the local vectorization backend and Windows live-host integration without changing the already-aligned SVG/cache/OOXML contracts.
