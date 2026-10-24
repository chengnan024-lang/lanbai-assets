"""Grade a scene-linear frame the way PPv2 does in Lanbai (Grading kit's engine model + the art bloom layer):
bloom (scene-linear, before the LUT) + the engine grade (grades_engine.json, i.e. the parameters the Grading kit
actually writes into the profiles). Returns sRGB 8-bit codes (float). Also: APL, metrics."""
import copy, json, os, sys
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
ENG = os.path.join(REPO, 'Grading', 'Tools~', 'engine')
sys.path.insert(0, ENG)
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_cine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'bible_work'))
import ppv2_engine as E          # noqa: E402
import ppv2 as LD                # noqa: E402
from lutlib_core import patch_ppv2   # noqa: E402
patch_ppv2(LD)
GE = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json')))
GF = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_final.json')))
_lut = {}


def profile(sid):
    p = copy.deepcopy(GE['profiles'][sid]['ppv2'])
    p['colorFilter'] = GE['common']['colorFilter']
    p['hueShift'] = GE['common']['hueShift']
    return p


def bloom_params(sid):
    p = copy.deepcopy(GF['profiles'][sid]['ppv2'])
    p['colorFilter'] = GF['common']['colorFilter']; p['hueShift'] = GF['common']['hueShift']
    return p


def grade(img, sid, bloom=True, ev=0.0):
    """img: (H, W, 3) scene-linear. ev: extra postExposure (EXPO helper result b + dEV - b ...)."""
    p = profile(sid)
    if ev:
        p['postExposure'] = p.get('postExposure', 0) + ev
    x = img.astype(np.float64)
    if bloom:
        x = x + LD.bloom_layer(x, LD.full(bloom_params(sid)))
    key = (sid, ev)
    if key not in _lut:
        _lut[key] = E.bake_lut(p)
    return E.codes(x, p, _lut[key])


def screen_of_fill(fill_lin, sid):
    return E.codes(np.asarray(fill_lin, np.float64)[None, :], profile(sid), E.bake_lut(profile(sid)))[0]


def apl(codes):
    c = np.clip(codes, 0, 255)
    return float((c @ np.array([0.2126, 0.7152, 0.0722])).mean())


def hexlin(h, ev=0.0):
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4) * 2.0 ** ev


def fill(s):
    """'#FFA26F @ +1.83' -> linear rgb."""
    s = s.strip()
    if '@' in s:
        h, e = s.split('@'); return hexlin(h.strip(), float(e))
    return hexlin(s)


def lab(codes):
    c = np.clip(np.asarray(codes, np.float64) / 255.0, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16; a = 500 * (f[..., 0] - f[..., 1]); b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b


def purple_fraction(codes, h0=290, h1=325, cmin=15):
    L, a, b = lab(codes)
    h = (np.degrees(np.arctan2(b, a)) + 360) % 360
    C = np.hypot(a, b)
    return float(((h >= h0) & (h <= h1) & (C > cmin)).mean())


def to_hex(c):
    return '#%02X%02X%02X' % tuple(int(round(min(max(v, 0), 255))) for v in c)
