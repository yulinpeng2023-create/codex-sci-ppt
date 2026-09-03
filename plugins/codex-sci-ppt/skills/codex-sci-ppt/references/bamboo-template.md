# Bamboo cross-section template

This reusable template is derived from a user-supplied PowerPoint bamboo transverse-section schematic. It preserves the visual idea of a warm golden parenchyma matrix populated with repeated stylized vascular bundles, while making the bundle symbols native editable PowerPoint shapes.

## When to use it

Use the template when a figure needs a schematic bamboo transverse section, bamboo wall matrix, vascular-bundle field, coating-on-bamboo cross section, penetration/release diagram, or a zoomed bamboo anatomy panel.

Do not use it as quantitative anatomy. The bundle count, spacing, size, and density are schematic unless the user supplies measured anatomical data.

## Render

```bash
python scripts/render_bamboo_template.py \
  --config templates/bamboo_cross_section.json \
  --output bamboo-cross-section.pptx
```

The default output contains one raster matrix-texture background and editable vascular-bundle symbols made from native PowerPoint shapes. The random seed is fixed, so repeated rendering is deterministic.

## Main parameters

- `region`: x/y/w/h of the bamboo cross-section field in inches.
- `matrix_color`: base color of the parenchyma matrix.
- `vascular_bundle_count`: number of schematic bundles.
- `bundle_size_min` / `bundle_size_max`: bundle size range in inches.
- `min_distance`: minimum bundle-center spacing.
- `outer_density_bias`: optional mild density increase toward the outer side of the wall.
- `bundle_dark` / `bundle_gold`: stylized bundle colors.
- `seed`: deterministic layout seed.

## Editing guidance

After rendering, reuse the bamboo field as a background/structural layer and add experimental overlays such as coatings, arrows, diffusion paths, nanoparticles, fungal hyphae, bacteria, labels, callouts, or zoom boxes. Keep any experimental measurements, scale bars, concentrations, or anatomical statistics tied to user-supplied values rather than the schematic template.
