"""bible acceptance numbers on a display PNG: APL (Rec.709 luma mean), share luma<12, share of strong violet
(C*>30 and h_ab 290-325), share near-black (< #04060B) and near-white (> #F4F7FA)."""
import sys, numpy as np
from PIL import Image
def lab(img):
    c = img / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    X = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(X > 0.008856, np.cbrt(X), 7.787 * X + 16 / 116)
    L = 116 * f[..., 1] - 16; a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b
def run(p):
    im = np.asarray(Image.open(p).convert('RGB')).astype(float)
    luma = im @ np.array([0.2126, 0.7152, 0.0722])
    L, a, b = lab(im)
    C = np.hypot(a, b); h = np.degrees(np.arctan2(b, a)) % 360
    viol = (C > 30) & (h > 290) & (h < 325)
    blk = (im <= np.array([4, 6, 11])).all(-1); wht = (im >= np.array([244, 247, 250])).all(-1)
    return dict(APL=round(luma.mean(), 1), luma_lt12=round((luma < 12).mean() * 100, 1), strong_violet=round(viol.mean() * 100, 2),
                near_black=round(blk.mean() * 100, 2), near_white=round(wht.mean() * 100, 2))
if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, run(p))
