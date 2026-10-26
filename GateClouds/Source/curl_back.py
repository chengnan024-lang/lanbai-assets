"""蓝白 / Lanbai · gate · round 10 C: the fingertip curl seen looking back from the main seat (yaw 180), the gate's sky and
deck (seam_ref.render after-column). No 4c fog, no lips / dome of the inside.

  python3 curl_back.py 180,180.5,... [w 640] [outdir /tmp/claude-0/cb]   -> cb_<t>.png
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seam_ref as S
from PIL import Image, ImageDraw
out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/claude-0/cb'
ts = [float(x) for x in sys.argv[1].split(',')]
for t in ts:
    S.SHOTS['_cb'] = dict(t=t, pos=[0.55, 1.7, 2.05], look_yaw_deg=180.0, look_pitch_deg=0.0, hfov_deg=90.0)
    A, B = S.render('_cb', int(sys.argv[2]) if len(sys.argv) > 2 else 640, out)
    im = Image.fromarray(B); ImageDraw.Draw(im).text((6, 4), 't %.2f yaw 180' % t, fill=(255, 255, 255))
    im.save(os.path.join(out, 'cb_%.2f.png' % t))
