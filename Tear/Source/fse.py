"""full-screen-equivalent overdraw of each kit part at a stage (desktop 16:9, hFOV 90, bible framing)."""
import sys, math, numpy as np
from PIL import Image, ImageDraw
import tear_def as T, kit_mesh as K
def fse(stage, W=480, H=270):
    cfg = T.STAGES[stage]; S = cfg['H'] / T.H; open01 = T.tear_open_param(cfg['open'])
    cam = np.array([0, 0, cfg['cam']]); pitch = math.radians(cfg['pitch'])
    fwd = np.array([0, math.cos(pitch), math.sin(pitch)]); up = np.array([0, -math.sin(pitch), math.cos(pitch)]); rt = np.array([1, 0, 0])
    f = (W / 2) / math.tan(math.radians(45))
    cam_kit = (cam - np.array([0, cfg['D'], 0])) / S
    out = {}
    for p in K.all_parts():
        V = K.deform(p, open01, cam_kit) * S + np.array([0, cfg['D'], 0])
        d = V - cam
        z = d @ fwd; x = d @ rt; y = d @ up
        ok = z > 1
        px = W / 2 + f * x / np.maximum(z, 1); py = H / 2 - f * y / np.maximum(z, 1)
        groups = [range(len(p['F']))]
        if p['name'] in ('Tear_Halo', 'Tear_Shafts'):
            # overlapping cards: count each card separately
            per = 1 if p['name'] == 'Tear_Halo' else 11
            groups = [range(i, min(i + per, len(p['F']))) for i in range(0, len(p['F']), per)]
        tot = 0.0
        for g in groups:
            im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
            for fi in g:
                fc = p['F'][fi]
                if not ok[fc].all():
                    continue
                dr.polygon([(px[k], py[k]) for k in fc], fill=255)
            tot += (np.asarray(im) > 0).mean()
        out[p['name']] = round(tot, 3)
    return out
if __name__ == '__main__':
    for s in sys.argv[1:]:
        r = fse(s); print(s, r, 'sum transparent (excl. flaps, cutout) = %.2f' % sum(v for k, v in r.items() if not k.startswith('Tear_Flap')))
