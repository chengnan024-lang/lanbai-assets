"""Docs~/Preview_BusGlass_Detail_1to1.png: a 1:1 crop of the window photograph around the tube's bokeh, clean on the
left and annotated on the right (where 'that one raindrop' and the running drops are: they are drops among drops, and
the eye finds them only by their motion in the game). Screen positions come from the kit's maths (glass_ref at the
preview's t, projected through the 5 mm slab), see README §11.
usage: python3 detail_glass.py <tilt_png> <out_png>"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import rainpaths as RP
FONTS = os.path.join(RP.lanbai_root(), 'deliver2', 'Sign', 'Fonts')
F = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Regular.otf'), s)
FB = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Medium.otf'), s)
src, out = sys.argv[1], sys.argv[2]
X0, Y0, X1, Y1 = 260, 200, 620, 630                  # crop of the 900 x 1350 photograph (1:1)
HERO = (438, 392); HERO_TOP = 262                    # the one drop's head and the top of its 2 cm path
HEADS = [(368, 382), (314, 589), (566, 274)]         # running drops at t = 1067.5 s (glass_ref, density 0.3)
CHANNELS = [(368, 160, 372), (314, 160, 583)]        # x, from y, to y (the clear channel above each head)
im = Image.open(src).convert('RGB')
c = im.crop((X0, Y0, X1, Y1)); W, H = c.size
a = c.copy(); d = ImageDraw.Draw(a)
col = (127, 211, 230); col2 = (230, 196, 127)
def P(p): return (p[0] - X0, p[1] - Y0)
def tag(xy, txt, colr, to):
    d.line((xy[0], xy[1], to[0], to[1]), fill=colr, width=1)
    d.ellipse((to[0] - 9, to[1] - 9, to[0] + 9, to[1] + 9), fill=(14, 17, 24), outline=colr, width=1)
    d.text((to[0] - 4, to[1] - 9), txt, font=FB(13), fill=colr)
hx, hy = P(HERO)
d.ellipse((hx - 14, hy - 21, hx + 14, hy + 21), outline=col, width=1)
for y in range(HERO_TOP - Y0, hy - 24, 6):
    d.line((hx + 19, y, hx + 19, y + 3), fill=col, width=1)
tag((hx + 10, hy - 18), '1', col, (hx + 48, 40))
for k, (x, y) in enumerate(HEADS):
    px, py = P((x, y))
    d.ellipse((px - 12, py - 18, px + 12, py + 18), outline=col2, width=1)
for (x, ya, yb) in CHANNELS:
    px = x - X0
    for y in range(max(0, ya - Y0), min(H, yb - Y0 - 20), 6):
        d.line((px - 16, y, px - 16, y + 3), fill=col2, width=1)
h0, h1, h2 = [P(h) for h in HEADS]
tag((h0[0] - 8, h0[1] - 16), '2', col2, (h0[0] - 40, 40))
tag((h1[0] + 10, h1[1] - 10), '3', col2, (h1[0] + 50, h1[1] - 40))
tag((h2[0] - 10, h2[1] + 12), '4', col2, (h2[0] - 30, h2[1] + 60))
LEG = 300; CAP = 70
sheet = Image.new('RGB', (W * 2 + LEG + 40, H + CAP), (14, 17, 24))
sheet.paste(c, (10, 10)); sheet.paste(a, (W + 20, 10))
ds = ImageDraw.Draw(sheet)
lx = 2 * W + 34; y = 14
ds.text((lx, y), '1:1 像素：左原图，右标注', font=FB(16), fill=(222, 230, 234)); y += 34
for (txt, colr) in (('① 那一滴雨（4 mm）。第 1 幕坐下时\n   它滑 2 cm 停住——这就是停住的\n   样子；虚线 = 它走过的路：大水珠\n   被带走，只剩雾状小珠与残珠', col),
                    ('② 一颗流滴停在灯管的光斑上，\n   上方是它刷出的通道', col2),
                    ('③ 一颗流滴刚穿过光斑，通道从\n   光斑里竖着穿过', col2),
                    ('④ 光斑上方的另一颗流滴', col2)):
    ds.multiline_text((lx, y), txt, font=F(14), fill=colr, spacing=4); y += 24 * (txt.count('\n') + 1) + 10
ds.multiline_text((lx, y + 6), '光斑前的每一颗水珠都是一个暗的小\n透镜，里面有一根倒立的小灯管\n（圣经 §4.6、§3.3）。', font=F(14), fill=(140, 150, 160), spacing=4)
ds.text((12, H + 20), '它们是水滴中的水滴：游戏里眼睛靠“动”认出它们。流滴密度为了静止的图调到 0.3（站台默认 0.05，“偶尔慢流”）。', font=F(14), fill=(140, 150, 160))
ds.text((12, H + 42), '位置由套件的数学（glass_ref，t = 1067.5 s）算出，并穿过 5 mm 玻璃的折射投到画面上。', font=F(14), fill=(140, 150, 160))
sheet.save(out)
print('wrote', out, sheet.size)
