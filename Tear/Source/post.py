import json, math, os, shutil
from PIL import Image
import metrics, tear_def as T
SRC = 'final'; DST = '../../deliver/Tear/Renders'
os.makedirs(DST, exist_ok=True)
out = {}
for s in ('U6', 'U7', 'U8'):
    cfg = T.STAGES[s]
    p = os.path.join(SRC, 'Tear_%s.png' % s)
    im = Image.open(p)
    W, H = im.size; f = (W / 2) / math.tan(math.radians(45))
    def yel(el):   # elevation -> pixel row (camera pitch)
        return H / 2 - f * math.tan(math.radians(el - cfg['pitch']))
    top = math.degrees(math.atan((cfg['H'] - cfg['cam']) / cfg['D']))
    y0, y1 = yel(top + 3), yel(-2)
    hgt = y1 - y0; wid = hgt * 16 / 9
    box = (int(W / 2 - wid / 2), int(y0), int(W / 2 + wid / 2), int(y1))
    crop = im.crop(box)
    k = min(2.0, W / crop.size[0])            # never upscale more than 2x (it only adds mush)
    if k > 1.0:
        crop = crop.resize((int(crop.size[0] * k), int(crop.size[1] * k)), Image.LANCZOS)
    crop.save(os.path.join(DST, 'Tear_%s_crop.png' % s))
    shutil.copy(p, os.path.join(DST, 'Tear_%s.png' % s))
    out[s] = metrics.run(p)
    out[s]['crop_box_px'] = box
for d in ('U6', 'U7'):
    p = os.path.join(SRC, 'Tear_%s_detail.png' % d)
    if os.path.exists(p):
        shutil.copy(p, os.path.join(DST, 'Tear_%s_detail.png' % d))
json.dump(out, open(os.path.join(DST, 'metrics.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
