"""迭代用的构图帧：python render_sheet.py <round> [w h]  -> Mirrors/Docs~/iterations/r<round>_*.png + r<round>_sheet.png + r<round>.json
视向见 lookdev_brief §6（正前方偏下 / 向下看 / 银心方向）。"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_port as MP

REPO = MP.REPO
OUT = os.path.join(REPO, 'Mirrors', 'Docs~', 'iterations')
SHOTS = [
    (1030.4, 0, -12, '1030.4 第 1 面穿越前 2 s · 正前方偏下'),
    (1030.4, -20, -60, '1030.4 第 1 面 · 向下看'),
    (1068.6, 0, -12, '1068.6 第 3 面前 2 s（下方的柱）'),
    (1113.4, 0, -12, '1113.4 第 10 面前 2 s（加速的尾）'),
    (1116.0, 0, 30, '1116.0 第 10 面穿过后 · 抬头（溶解 + 星尘）'),
    (1123.5, 0, -12, '1123.5 第 11 面（尾声的第一声钟）'),
    (1136.6, 0, -12, '1136.6 第 12 面前 1 s'),
    (1142.0, 0, -60, '1142.0 第 13 面 · 向下看（白的膨胀里）'),
]


def main():
    rnd = sys.argv[1] if len(sys.argv) > 1 else '1'
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 960
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 540
    only = sys.argv[4] if len(sys.argv) > 4 else None
    os.makedirs(OUT, exist_ok=True)
    meas = []
    for i, (t, yaw, pitch, label) in enumerate(SHOTS):
        if only is not None and str(i) not in only.split(','):
            continue
        codes, info = MP.frame(t, yaw, pitch, w, h)
        im = Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8))
        name = 'r%s_%02d_%.1f_%d_%d.png' % (rnd, i, t, yaw, pitch)
        im.save(os.path.join(OUT, name))
        own = info.pop('owner')
        face = codes[(own % 10 == 0) & (own > 0)]
        info.update(label=label, file=name, face_mean=[round(float(x), 1) for x in face.mean(0)] if len(face) else None,
                    face_p90=[round(float(x), 1) for x in np.percentile(face, 90, axis=0)] if len(face) else None,
                    face_frac=round(float(len(face)) / own.size, 3))
        meas.append(info)
        print(json.dumps(info, ensure_ascii=False), flush=True)
    json.dump(meas, open(os.path.join(OUT, 'r%s%s.json' % (rnd, '' if only is None else '_' + only.replace(',', '-'))), 'w'), ensure_ascii=False, indent=1)


def sheet(rnd):
    files = sorted(f for f in os.listdir(OUT) if f.startswith('r%s_' % rnd) and f.endswith('.png') and 'sheet' not in f)
    meas = {}
    for f in os.listdir(OUT):
        if f.startswith('r%s' % rnd) and f.endswith('.json'):
            for m in json.load(open(os.path.join(OUT, f))):
                meas[m['file']] = m
    tw, th = 480, 270
    sh = Image.new('RGB', (tw * 2, (th + 28) * ((len(files) + 1) // 2)), (14, 14, 18))
    d = ImageDraw.Draw(sh)
    fnt = ImageFont.truetype(os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), 15)
    for k, f in enumerate(files):
        x, y = (k % 2) * tw, (k // 2) * (th + 28)
        sh.paste(Image.open(os.path.join(OUT, f)).resize((tw, th), Image.LANCZOS), (x, y + 28))
        m = meas.get(f, {})
        d.text((x + 6, y + 5), '%s  APL %s  镜面 %s' % (m.get('label', f), m.get('APL'), m.get('face_p90')), fill=(220, 220, 220), font=fnt)
    sh.save(os.path.join(OUT, 'r%s_sheet.png' % rnd))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        sheet(sys.argv[2])
    else:
        main()
