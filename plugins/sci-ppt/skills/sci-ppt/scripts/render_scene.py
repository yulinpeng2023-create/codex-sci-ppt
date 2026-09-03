#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


def rgb(value):
    if value is None:
        return None
    value = value.lstrip('#')
    if len(value) != 6:
        raise ValueError(f'Expected #RRGGBB, got {value!r}')
    return RGBColor.from_string(value.upper())


def apply_style(shape, obj):
    fill = obj.get('fill', '#FFFFFF')
    if hasattr(shape, 'fill'):
        if fill is None:
            shape.fill.background()
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = rgb(fill)
    if hasattr(shape, 'line'):
        line = obj.get('line', '#333333')
        if line is None:
            shape.line.fill.background()
        else:
            shape.line.color.rgb = rgb(line)
            shape.line.width = Pt(float(obj.get('line_width', 1.25)))
    if 'rotation' in obj:
        shape.rotation = float(obj['rotation'])


def add_text(slide, obj):
    shape = slide.shapes.add_textbox(Inches(obj['x']), Inches(obj['y']), Inches(obj['w']), Inches(obj['h']))
    shape.rotation = float(obj.get('rotation', 0))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(obj.get('text', ''))
    align = str(obj.get('align', 'left')).lower()
    p.alignment = {'left': PP_ALIGN.LEFT, 'center': PP_ALIGN.CENTER, 'right': PP_ALIGN.RIGHT}.get(align, PP_ALIGN.LEFT)
    run = p.runs[0]
    run.font.size = Pt(float(obj.get('font_size', 18)))
    run.font.name = obj.get('font', 'Arial')
    run.font.bold = bool(obj.get('bold', False))
    run.font.italic = bool(obj.get('italic', False))
    run.font.color.rgb = rgb(obj.get('color', '#222222'))
    return shape


def add_polygon(slide, obj):
    points = obj['points']
    if len(points) < 3:
        raise ValueError('polygon needs at least 3 points')
    builder = slide.shapes.build_freeform(Inches(points[0][0]), Inches(points[0][1]))
    for x, y in points[1:]:
        builder.add_line_segments([(Inches(x), Inches(y))], close=False)
    shape = builder.convert_to_shape()
    apply_style(shape, obj)
    return shape


def render(scene, output):
    prs = Presentation()
    slide_cfg = scene.get('slide', {})
    prs.slide_width = Inches(float(slide_cfg.get('width', 13.333)))
    prs.slide_height = Inches(float(slide_cfg.get('height', 7.5)))
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb(scene.get('background', '#FFFFFF'))

    for obj in scene.get('objects', []):
        kind = obj['type']
        if kind == 'text':
            add_text(slide, obj)
            continue
        if kind == 'polygon':
            add_polygon(slide, obj)
            continue
        if kind in ('line', 'arrow'):
            shape = slide.shapes.add_connector(
                MSO_CONNECTOR.STRAIGHT,
                Inches(obj['x1']), Inches(obj['y1']), Inches(obj['x2']), Inches(obj['y2'])
            )
            shape.line.color.rgb = rgb(obj.get('line', '#333333'))
            shape.line.width = Pt(float(obj.get('line_width', 1.5)))
            if kind == 'arrow':
                # OOXML arrowhead injection keeps the connector editable.
                ln = shape.line._get_or_add_ln()
                tail = ln.makeelement('{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd')
                tail.set('type', 'none')
                head = ln.makeelement('{http://schemas.openxmlformats.org/drawingml/2006/main}headEnd')
                head.set('type', 'triangle')
                ln.append(tail)
                ln.append(head)
            continue

        shape_type = {
            'rect': MSO_SHAPE.RECTANGLE,
            'round_rect': MSO_SHAPE.ROUNDED_RECTANGLE,
            'ellipse': MSO_SHAPE.OVAL,
        }.get(kind)
        if shape_type is None:
            raise ValueError(f'Unsupported object type: {kind}')
        shape = slide.shapes.add_shape(
            shape_type, Inches(obj['x']), Inches(obj['y']), Inches(obj['w']), Inches(obj['h'])
        )
        apply_style(shape, obj)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)

    # Reopen as a basic integrity check.
    check = Presentation(output)
    if len(check.slides) < 1 or len(check.slides[0].shapes) < 1:
        raise RuntimeError('PPTX verification failed: no editable shapes found')
    return output


def main():
    ap = argparse.ArgumentParser(description='Render a Sci-PPT JSON scene into editable PowerPoint objects.')
    ap.add_argument('--scene', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    with open(args.scene, 'r', encoding='utf-8') as f:
        scene = json.load(f)
    out = render(scene, args.output)
    print(out)


if __name__ == '__main__':
    main()
