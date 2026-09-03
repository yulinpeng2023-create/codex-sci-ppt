#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random, math
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Inches, Pt


def rgb(v): return RGBColor.from_string(v.lstrip('#').upper())

def add_polygon(slide, points, fill, line='#9A6300', width=0.65):
    b = slide.shapes.build_freeform(Inches(points[0][0]), Inches(points[0][1]))
    b.add_line_segments([(Inches(x), Inches(y)) for x,y in points[1:]], close=True)
    s=b.convert_to_shape(); s.fill.solid(); s.fill.fore_color.rgb=rgb(fill)
    if line is None: s.line.fill.background()
    else: s.line.color.rgb=rgb(line); s.line.width=Pt(width)
    try: s.shadow.inherit=False
    except Exception: pass
    return s

def add_oval(slide,x,y,w,h,fill,line=None,width=0.25):
    s=slide.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x),Inches(y),Inches(w),Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb=rgb(fill)
    if line is None: s.line.fill.background()
    else: s.line.color.rgb=rgb(line); s.line.width=Pt(width)
    try:s.shadow.inherit=False
    except Exception:pass
    return s

def add_line(slide,a,b,color,width=0.25):
    s=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(a[0]),Inches(a[1]),Inches(b[0]),Inches(b[1]))
    s.line.color.rgb=rgb(color); s.line.width=Pt(width)
    return s

def lerp(a,b,t): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)

def bilerp(A,B,C,D,u,v):
    # quad order top-left/top-right/bottom-right/bottom-left
    top=lerp(A,B,u); bottom=lerp(D,C,u); return lerp(top,bottom,v)

def board_geometry(cfg):
    x=float(cfg.get("x",1.35)); y=float(cfg.get("y",4.25)); sc=float(cfg.get("scale",1.0))
    # Physical dimensions are 5 x 2 x 0.5 cm. The 2 x 0.5 transverse end
    # faces the viewer directly; the 5 cm longitudinal axis recedes to the right.
    W=(2.80*sc,0.0)      # 2 cm transverse width
    L=(6.30*sc,-1.75*sc) # 5 cm longitudinal direction, foreshortened
    T=(0.0,0.70*sc)      # 0.5 cm thickness
    A=(x,y); B=(x+W[0],y+W[1])
    D=(A[0]+L[0],A[1]+L[1]); C=(B[0]+L[0],B[1]+L[1])
    A2=(A[0]+T[0],A[1]+T[1]); B2=(B[0]+T[0],B[1]+T[1]); C2=(C[0]+T[0],C[1]+T[1]); D2=(D[0]+T[0],D[1]+T[1])
    return {"top":[A,B,C,D], "front":[A,B,B2,A2], "side":[B,C,C2,B2]}

def add_bundle(slide,cx,cy,size,dark,gold,rot=0):
    # Stylized vascular bundle matching the reusable bamboo cross-section template.
    # The motif stays fully editable: dark top cap, dark/gold lateral lobes,
    # gold center and dark lower teardrop.
    top=add_oval(slide,cx-size*0.18,cy-size*0.46,size*0.36,size*0.36,dark); top.rotation=rot
    for sign in (-1,1):
        lx=cx+sign*size*0.30; ly=cy-size*0.02
        outer=add_oval(slide,lx-size*0.20,ly-size*0.20,size*0.40,size*0.40,dark); outer.rotation=rot
        inner=add_oval(slide,lx-size*0.12,ly-size*0.12,size*0.24,size*0.24,gold); inner.rotation=rot
    center=add_oval(slide,cx-size*0.18,cy-size*0.13,size*0.36,size*0.36,gold); center.rotation=rot
    lower=slide.shapes.add_shape(MSO_SHAPE.TEAR,Inches(cx-size*0.18),Inches(cy+size*0.10),Inches(size*0.36),Inches(size*0.44))
    lower.rotation=180+rot; lower.fill.solid(); lower.fill.fore_color.rgb=rgb(dark); lower.line.fill.background()
    for dx in (-0.055,0.055):
        add_oval(slide,cx+size*dx-size*0.018,cy-size*0.02,size*0.036,size*0.036,dark)

def sample_bundles(rng, end, count):
    A,B,C,D=end
    pts=[]
    # Candidate density is higher near v=0 (outer/top side), sizes smaller there.
    attempts=0
    while len(pts)<count and attempts<10000:
        attempts+=1
        if rng.random()<0.7:
            v=(rng.random()**1.65)*0.46+0.27
        else:
            v=rng.uniform(0.30,0.70)
        # Deliberately nonuniform u: broad random placement mixed with local clusters.
        if rng.random()<0.48:
            u=rng.uniform(0.06,0.94)
        else:
            center=rng.choice([0.14,0.33,0.58,0.80])
            u=min(0.94,max(0.06,rng.gauss(center,0.07)))
        p=bilerp(A,B,C,D,u,v)
        min_d=0.23 + 0.04*v
        if any((p[0]-q[0])**2+(p[1]-q[1])**2 < min_d**2 for q,_,_,_ in pts):
            continue
        size=0.23 + 0.06*v + rng.uniform(-0.010,0.010)
        pts.append((p,size,rng.uniform(-12,12),v))
    return pts

def render(cfg, output):
    prs=Presentation(); prs.slide_width=Inches(float(cfg.get('slide_width',13.333))); prs.slide_height=Inches(float(cfg.get('slide_height',7.5)))
    slide=prs.slides.add_slide(prs.slide_layouts[6]); bg=slide.background.fill; bg.solid(); bg.fore_color.rgb=rgb(cfg.get('background','#FFFFFF'))
    g=board_geometry(cfg); colors=cfg.get('colors',{})
    topc=colors.get('top','#DDA53B'); sidec=colors.get('side','#C68B2A'); endc=colors.get('end','#E2B249'); edge=colors.get('edge','#91600A')
    # Three visible faces: transverse end, top, and one longitudinal side.
    add_polygon(slide,g['side'],sidec,edge,0.7)
    add_polygon(slide,g['front'],endc,edge,0.7)
    add_polygon(slide,g['top'],topc,edge,0.7)
    rng=random.Random(int(cfg.get('seed',20260903)))
    # Restrained longitudinal grain on top: sparse, slightly jittered, not a ruled sheet.
    A,B,C,D=g['top']
    for _ in range(int(cfg.get('top_grain_count',8))):
        t=rng.uniform(0.05,0.95)
        s=lerp(A,B,t); e=lerp(D,C,t)
        j=rng.uniform(-0.02,0.02)
        add_line(slide,(s[0],s[1]+j),(e[0],e[1]+j),colors.get('grain','#B97B20'),rng.uniform(0.10,0.18))
    # Long-side grain: a few subtle lines along length.
    A,B,C,D=g['side']
    for _ in range(int(cfg.get('side_grain_count',3))):
        t=rng.uniform(0.18,0.85); s=lerp(A,D,t); e=lerp(B,C,t)
        add_line(slide,s,e,colors.get('side_grain','#9E6818'),rng.uniform(0.12,0.20))
    # End-face micro-speckles; keep them inside with margins.
    A,B,C,D=g['front']
    for _ in range(int(cfg.get('speckles',72))):
        u=rng.uniform(0.04,0.96); v=rng.uniform(0.12,0.88); p=bilerp(A,B,C,D,u,v)
        r=rng.uniform(0.003,0.0065); add_oval(slide,p[0]-r,p[1]-r,2*r,2*r,colors.get('speckle','#A17423'))
    bundles=sample_bundles(rng,g['front'],int(cfg.get('vascular_bundle_count',9)))
    for (cx,cy),size,rot,v in bundles:
        add_bundle(slide,cx,cy,size,colors.get('bundle_dark','#6C3B05'),colors.get('bundle_gold','#DDAE3E'),rot)
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True); prs.save(output)
    chk=Presentation(output); n=len(chk.slides[0].shapes)
    if len(chk.slides)!=1 or len(bundles)<7 or n<60: raise RuntimeError('verification failed')
    return n,len(bundles)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',type=Path); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    cfg=json.loads(a.config.read_text()) if a.config else {'physical_cm':{'length':5,'width':2,'thickness':0.5},'vascular_bundle_count':9,'seed':20260903}
    n,b=render(cfg,a.output); print(json.dumps({'output':str(a.output),'shapes':n,'bundles':b,'physical_cm':'5 x 2 x 0.5'}))
if __name__=='__main__': main()
