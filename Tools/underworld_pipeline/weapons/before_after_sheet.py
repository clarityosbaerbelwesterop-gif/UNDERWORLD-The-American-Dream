#!/usr/bin/env python3
"""Before/after contact sheet for the WPN_Pistol_01 T-ART-05 review (system Python + Pillow, run from the repo root)."""
import sys
from PIL import Image, ImageDraw, ImageFont
D="Docs/ArtDirection/Reviews/WPN_Pistol_01/"
views=["left","right","top","q3","q3back","muzzle","port","guard"]
W,H=640,427; P=10; HD=60; LB=26
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",22); fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
S=Image.new("RGB",(2*W+3*P, HD+len(views)*(H+LB+P)+P),(28,28,30)); d=ImageDraw.Draw(S)
d.text((P,8),"WPN_Pistol_01  T-ART-05  BEFORE v0 (main) vs AFTER v1 (bot2/dev) - same Cycles CPU rig, 48 spp",font=f,fill=(240,240,240))
d.text((P,36),"left: v0 blockout as on main (re-rendered from its .blend)   right: v1 (black nitride + stippled polymer, 2048 HP->LP bake)",font=fs,fill=(180,180,180))
for r,v in enumerate(views):
    y=HD+r*(H+LB+P)
    for c,(sub,lab) in enumerate((("before_v0_newrig","BEFORE v0"),("after_v1","AFTER v1"))):
        x=P+c*(W+P)
        im=Image.open(D+sub+"/"+v+".jpg").convert("RGB").resize((W,H))
        d.rectangle([x,y,x+W,y+LB],fill=(110,40,30) if c==0 else (30,90,50)); d.text((x+6,y+3),f"{lab} - {v}",font=fs,fill=(255,255,255))
        S.paste(im,(x,y+LB))
S.save("Docs/Reviews/sheets/WPN_Pistol_01_before_after.png",optimize=True)
print(S.size)
