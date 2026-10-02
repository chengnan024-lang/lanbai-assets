"""final/contact_sheet.png: the key art on top, the eight in-bus frames below in story order (labels = cue + time)."""
import os
from PIL import Image, ImageDraw, ImageFont
from gate_scene_shots import SHOTS

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, 'final')
W = 2560
key = Image.open(os.path.join(F, 'keyart_239.png')).convert('RGB')
names = [('U6', 'U6_approach'), ('U7', 'U7_engelein'), ('U8side', 'U8_side'), ('U8near', 'U8_near'), ('U8fwd', 'U8_forward'),
         ('U8a', 'U8a_ach_nein'), ('U8b', 'U8b_spot'), ('rear', 'rear_window')]
COLS = 3
tw = (W - (COLS + 1) * 16) // COLS
th = int(tw * 9 / 16)
H = key.height + 16 + ((len(names) + COLS - 1) // COLS) * (th + 44) + 8
sheet = Image.new('RGB', (W, H), (8, 10, 16))
sheet.paste(key, (0, 0))
dr = ImageDraw.Draw(sheet)
try:
    fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
except Exception:
    fnt = ImageFont.load_default()
for i, (k, fn) in enumerate(names):
    p = os.path.join(F, fn + '.png')
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert('RGB').resize((tw, th), Image.LANCZOS)
    x = 16 + (i % COLS) * (tw + 16)
    y = key.height + 16 + (i // COLS) * (th + 44)
    sheet.paste(im, (x, y))
    sh = SHOTS[k]
    dr.text((x, y + th + 8), '%s   t = %.2f s   %s' % (fn, sh['t'], sh['cue'].split(' (')[0].split(':')[0]), fill=(200, 205, 215), font=fnt)
sheet.save(os.path.join(F, 'contact_sheet.png'))
print('wrote', os.path.join(F, 'contact_sheet.png'), sheet.size)
