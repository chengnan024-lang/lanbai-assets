"""Re-map the persistence channel G of RainBeads_*_Data so that rainAmount reads as BEAD AREA (verification round 2:
'wake 0.4' kept 95 % of the bead area). G' = 0.9 x (area-weighted CDF of G): the ORDER of evaporation is unchanged
(big beads last, mist first), only the scale changes, so rainAmount a leaves about (a - 0.04) / 0.9 of the bead area.
Applied by make_beads.py at write time; this script applies it to already-written textures (idempotence guarded by
a marker in beads.json)."""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rainpaths as RP
OUT = RP.out_dir()


def area_cdf_remap(G, cov):
    """G, cov: float arrays 0..1. Returns G' (same shape)."""
    q = np.round(G * 255).astype(int)
    w = np.bincount(q.ravel(), weights=cov.ravel(), minlength=256)
    cdf = np.cumsum(w) / max(w.sum(), 1e-9)
    cdf_mid = cdf - 0.5 * w / max(w.sum(), 1e-9)               # centre of each bin's mass
    return np.clip(0.9 * cdf_mid[q], 0, 1)


if __name__ == '__main__':
    meta_p = os.path.join(OUT, 'beads.json')
    meta = json.load(open(meta_p))
    if meta.get('G_area_remap'):
        print('already remapped'); sys.exit(0)
    for v in ('Vertical', 'Horizontal'):
        p = os.path.join(OUT, 'RainBeads_%s_Data_1024.png' % v)
        d = np.asarray(Image.open(p)).astype(np.float64) / 255
        d[..., 1] = area_cdf_remap(d[..., 1], d[..., 2])
        Image.fromarray(np.clip(np.round(d * 255), 0, 255).astype(np.uint8), 'RGBA').save(p)
        rep = {}
        for a in (0.12, 0.25, 0.4, 0.6, 1.0):
            vis = np.clip((a - d[..., 1]) * 12, 0, 1)
            rep[str(a)] = round(float((d[..., 2] * vis).sum() / d[..., 2].sum()), 3)
        meta['variants'][v]['visible_area_by_amount'] = rep
        print(v, rep)
    meta['G_area_remap'] = True
    json.dump(meta, open(meta_p, 'w'), indent=1)
