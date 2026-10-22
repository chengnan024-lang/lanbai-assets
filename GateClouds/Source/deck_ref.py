"""蓝白 / Lanbai · gate clouds kit · a line-by-line numpy port of Lanbai_GateCloudDeck.shader (the reference render).

Renders the deck exactly as the shader does (same march, same mip choice, same lighting, same fog), from any camera in
GateLayout_v2.json, then grades it with the engine model of PPv2 S4 (Grading/Tools~/engine/ppv2_engine.py), so the
result can be compared with the Blender finals (Gate/Renders/*.png) and with the Unity screenshots in FromLocal/.

  /tmp/claude-0/venv/bin/python deck_ref.py key  --w 960 [--tex ../Textures] [--set k=v,...] [--out x.png]

If you change a number here, change it in the shader (DEFAULTS below = the shader's Properties defaults).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(KIT)
sys.path.insert(0, os.path.join(REPO, 'Grading', 'Tools~', 'engine'))
import ppv2_engine as PE  # noqa: E402

LAYOUT = json.load(open(os.path.join(REPO, 'Gate', 'GateLayout_v2.json')))
CUES = LAYOUT['timeline']['cues']

# ---- the shader's Properties defaults (keep in sync with Lanbai_GateCloudDeck.shader) -------------------------------
DEFAULTS = dict(
    # march: exponential steps t_i = t_s (1 + k)^(i + jitter), t_s = max(slab entry, MarchMin, half the way to the
    # cloud top); k = max(StepK, what reaches MarchMax in Steps); then 5 bisections at the crossing
    Steps=120, StepK=0.02, MarchMin=12.0, MarchMax=1600.0, LodBias=0.0, AnisoMax=16.0,
    # the soft skin over the heads (the silver rims): column density SkinSigma x exp(-clearance / edge),
    # edge = SkinEdge + 0.35 x footprint; skin met while sinking onto a surface counts SkinApproach
    SkinSigma=0.8, SkinEdge=0.5, SkinApproach=0.0, SkinSigmaL=0.12,
    # the opaque surface: moon through the head (baked path x SigmaL) x a softened lobe, + sky x AO
    SigmaL=0.14, SurfMoon=0.015, SurfPhase=0.35, SurfLambert=0.8, SurfShadow=0.35,
    G1=0.8, G2=-0.18, GMix=0.62,    # two-lobe HG
    MoonE=0.38,                     # moon radiance on the deck (x _MoonColor)
    MsK=0.01, MsTau=0.28,           # multiple scattering: E x MsK x exp(-tau x MsTau)
    AmbK=0.35,                      # sky ambient (x _AmbColor) x AO
    FarRim=0.12, FarMeanH=12.0,     # rays not hit by MarchMax: the mean-height plane, + the average rim
    FogDensity=0.0006, FogScale=1.8, MoonAirFog=0.35,
    DetailMin=-12.0, DetailMax=44.0, MacroMin=-12.0, MacroMax=12.0, TauMaxD=160.0, TauMaxM=400.0,
    AmpMin=0.3, AmpMax=0.8, VarMin=0.75, VarMax=1.15,     # macro B (a 0..1 field) -> AmpMin..AmpMax
    PeriodD=960.0, PeriodM=6400.0, MicroScale=7.0, MicroAmp=5.0, MicroEnv=0.35,
    Clearance=6.0, Gain=1.0,
    CrevLen=230.0, CrevW=0.4, CrevDepth=25.0, CrevLip=5.0, CrevGlow=(0.184, 0.170, 0.272),
    TearH=640.0, TearOpen=0.48,     # reference only (Unity: _Udon_TearH / _Udon_TearFoot)
)
MOON_COL = np.array([0.6724, 0.7758, 1.0])                  # #D6E4FF linear
MOON_DIR = np.array(LAYOUT['lights']['moon']['direction_to_light_unity'], float)
MOON_DIR /= np.linalg.norm(MOON_DIR)
SKY = dict(HazeNear=np.array([0.1085, 0.1130, 0.1641]), HazeFar=np.array([0.0436, 0.0504, 0.0726]),
           Void=np.array([0.0021, 0.0030, 0.0070]), BandAz=(50.0, 60.0), BandEl=(6.0, 22.0, 2.0),
           BelowHorizon=(-25.0, 0.0, 0.55), BelowDesat=0.6, BackBand=float(os.environ.get('BACKBAND', 0.55)),
           MoonGlowColor=np.array([0.275, 0.366, 0.578]), MoonGlowShape=(1.6, 0.9, 0.06, 0.32))
AMB_COL = np.array([0.0436, 0.0504, 0.0726]) * 1.0         # = HazeFar: the sky the deck sees overhead (shader default)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def h_bus(t):
    U6, U9 = CUES['U6'], CUES['U9']
    if t <= U6:
        return 40.0
    if t <= 160.5:
        return 40.0 + 20.0 * float(ss(0, 1, (t - U6) / (160.5 - U6)))
    return 60.0 + 90.0 * float(ss(0, 1, (t - 160.5) / (U9 - 160.5)))


def gate_origin(t):
    return np.array([0.0, 150.0 - h_bus(t), 59.0164 * (CUES['U9'] - t)])


# ---- sky (port of LanbaiGateSky.cginc LanbaiBand + LanbaiMoonAir) ---------------------------------------------------
def band(V, cam, tear):
    el = np.degrees(np.arcsin(np.clip(V[..., 1], -1, 1)))
    T = tear - cam
    th = T[[0, 2]] / np.linalg.norm(T[[0, 2]])
    vh = V[..., [0, 2]] / np.maximum(np.linalg.norm(V[..., [0, 2]], axis=-1, keepdims=True), 1e-6)
    az = np.degrees(np.arccos(np.clip(vh @ th, -1, 1)))
    bw, bg = SKY['BandAz']
    b = SKY['HazeNear'] + (SKY['HazeFar'] - SKY['HazeNear']) * ss(0, bw, az)[..., None]
    wel = np.clip(1 - ss(SKY['BandEl'][0], SKY['BandEl'][1], el), 0, 1) ** SKY['BandEl'][2]
    w = (1 - ss(bw, bg, az)) * wel
    sky = SKY['Void'] + (b - SKY['Void']) * w[..., None]
    sky = sky + SKY['HazeFar'] * (SKY['BackBand'] * ss(65, 120, az) * wel)[..., None]
    lum = sky @ np.array([0.2126, 0.7152, 0.0722])
    grey = lum[..., None] * np.array([0.92, 0.98, 1.12])
    k = (SKY['BelowDesat'] * ss(0, -4, el))[..., None]
    sky = sky + (grey - sky) * k
    bh = SKY['BelowHorizon']
    below = bh[2] + (1 - bh[2]) * ss(bh[0], bh[1], el)
    return sky * below[..., None]


def moon_air(V):
    am = np.degrees(np.arccos(np.clip(V @ MOON_DIR, -1, 1)))
    a1, k1, a2, k2 = SKY['MoonGlowShape']
    return SKY['MoonGlowColor'] * (a1 * np.exp(-k1 * am) + a2 * np.exp(-k2 * am))[..., None]


# ---- textures with mips (wrap), trilinear like tex2Dlod -------------------------------------------------------------
class MipTex:
    def __init__(self, path):
        a = np.asarray(Image.open(path)).astype(np.float32) / 255.0
        self.levels = [a]
        while a.shape[0] > 1:
            a = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
            self.levels.append(a)
        self.n = self.levels[0].shape[0]

    def _bilinear(self, lvl, u, v):
        A = self.levels[lvl]
        n = A.shape[0]
        x = u * n - 0.5
        y = v * n - 0.5
        x0 = np.floor(x).astype(np.int64)
        y0 = np.floor(y).astype(np.int64)
        fx = (x - x0)[..., None]
        fy = (y - y0)[..., None]
        x0 %= n
        y0 %= n
        x1 = (x0 + 1) % n
        y1 = (y0 + 1) % n
        return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x1] * fx * (1 - fy) + A[y1, x0] * (1 - fx) * fy
                + A[y1, x1] * fx * fy)

    def sample(self, u, v, lod):
        lod = np.clip(lod, 0, len(self.levels) - 1)
        l0 = np.floor(lod).astype(np.int64)
        f = (lod - l0)[..., None]
        out = np.zeros(u.shape + (4,), np.float32)
        for L in np.unique(l0):
            m = l0 == L
            a = self._bilinear(L, u[m], v[m])
            b = self._bilinear(min(L + 1, len(self.levels) - 1), u[m], v[m])
            out[m] = a * (1 - f[m]) + b * f[m]
        return out


def hg(c, g):
    return (1 - g * g) / np.power(1 + g * g - 2 * g * c, 1.5)


def ign(px, py):
    """interleaved gradient noise (Jimenez 2014), as in the shader"""
    return np.mod(52.9829189 * np.mod(0.06711056 * px + 0.00583715 * py, 1.0), 1.0)


def camera_rays(cam, w, h):
    yaw, pitch = math.radians(cam['look_yaw_deg']), math.radians(cam['look_pitch_deg'])
    hf = math.radians(cam['hfov_deg'])
    tx = math.tan(hf / 2)
    ty = tx * h / w
    xs = (np.arange(w) + 0.5) / w * 2 - 1
    ys = 1 - (np.arange(h) + 0.5) / h * 2
    X, Y = np.meshgrid(xs * tx, ys * ty)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    # Unity: pitch about x (up = negative euler x), then yaw about y
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]])     # look up by +pitch
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    d = d @ Rx.T @ Ry.T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return d, 2 * ty / h


def render_deck(cam, t, w, h, tex_dir, P, pool=True):
    det = MipTex(os.path.join(tex_dir, 'Deck_Detail_1024.png'))
    mac = MipTex(os.path.join(tex_dir, 'Deck_Macro_512.png'))
    V, pix_ang = camera_rays(cam, w, h)
    ro = np.array(cam['eye_bus_relative'], float)
    O = gate_origin(t)
    cloud_top = -h_bus(t)
    tear = O + np.array([20.0, 147.0, 0.0])        # hot spot ~ (TearPos): only steers the band azimuth here
    y_top = cloud_top + P['MacroMax'] + P['DetailMax'] * P['AmpMax']
    y_bot = cloud_top + P['MacroMin'] + P['DetailMin'] * P['AmpMax']
    vy = V[..., 1]
    hit = vy < -1e-4
    col = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    dist = np.full((h, w), np.inf)
    Vh = V[hit]
    vyh = -Vh[:, 1]
    t0 = np.maximum((ro[1] - y_top) / vyh, 0.0)
    t1 = np.minimum((ro[1] - y_bot) / vyh, 16000.0)
    L = t1 - t0
    yy, xx = np.nonzero(hit)
    jit = ign(xx.astype(float), yy.astype(float))
    N = int(P['Steps'])
    cos_m = Vh @ MOON_DIR
    phase = P['GMix'] * hg(cos_m, P['G1']) + (1 - P['GMix']) * hg(cos_m, P['G2'])
    texel_d = P['PeriodD'] / det.n
    texel_m = P['PeriodM'] / mac.n

    def field(tm, sel):
        """the height field at distance tm along the rays sel (LOD from the pixel footprint only)"""
        p = ro + Vh[sel] * tm[:, None]
        cx, cz = p[:, 0] - O[0], p[:, 2] - O[2]
        # pixel footprint on the deck: across = t x pixel angle, along = across / |V.y| (grazing elongation).
        # The shader hands both axes to tex2Dgrad (hardware anisotropic filtering); here: their geometric mean.
        across = np.maximum(tm * pix_ang, 1e-3)
        along = across / np.maximum(vyh[sel], 0.02)
        foot = np.sqrt(across * np.minimum(along, across * P['AnisoMax']))
        dd = det.sample(cx / P['PeriodD'], cz / P['PeriodD'], np.log2(foot / texel_d) + P['LodBias'])
        mm = mac.sample(cx / P['PeriodM'], cz / P['PeriodM'], np.log2(foot / texel_m) + P['LodBias'])
        hd = P['DetailMin'] + dd[:, 0] * (P['DetailMax'] - P['DetailMin'])
        hm = P['MacroMin'] + mm[:, 0] * (P['MacroMax'] - P['MacroMin'])
        amp = P['AmpMin'] + mm[:, 2] * (P['AmpMax'] - P['AmpMin'])
        lod_u = np.log2(foot * P['MicroScale'] / texel_d) + P['LodBias']
        mu = det.sample(cx * P['MicroScale'] / P['PeriodD'] + 0.37, cz * P['MicroScale'] / P['PeriodD'] + 0.61, lod_u)
        fade = 1 - ss(1.0, 3.5, lod_u)
        # unresolved cauliflower still stops a skimming ray: where the lumps are below a pixel, the surface sits at
        # their upper envelope (MicroEnv x amplitude) instead of their mean
        micro = P['MicroAmp'] * ((mu[:, 0] - 0.45) * fade + P['MicroEnv'] * (1 - fade))
        H = cloud_top + hm + amp * (hd + micro)
        # never a head into the bus: within ~300 m the heads stop Clearance below the eye
        dxz = np.hypot(p[:, 0] - ro[0], p[:, 2] - ro[2])
        H = H + (np.minimum(H, ro[1] - P['Clearance']) - H) * (1 - ss(150.0, 400.0, dxz))
        # the crevasse (shader: the same lines)
        al = (foot_w[2] - p[:, 2]) / max(P['CrevLen'] * S_t, 1.0)
        hwc = np.maximum(P['CrevW'] * foot_w[3] * (1 - al), 0.5)
        ac = np.abs(p[:, 0] - foot_w[0]) / hwc
        inl = ss(-0.04, 0.02, al) * (1 - ss(0.7, 1.0, al))
        kc = (1 - ss(0.55, 1.0, ac)) * inl
        lip = np.exp(-(ac - 1.2) ** 2 / 0.18) * inl * (1 - al)
        H = H - P['CrevDepth'] * kc + P['CrevLip'] * lip
        crev_last[0] = kc * np.clip(1 - al, 0, 1)
        return p[:, 1] - H, dd, mm, amp, foot

    # the tear's foot (README_GateLayout §2.1: Tear_Root.TransformPoint([0.5, 0, -30]), w = white half width)
    S_t = P['TearH'] / 1000.0
    foot_w = np.array([O[0] - 0.5 * S_t, cloud_top, O[2] + 30.0 * S_t,
                       0.5 * (0.18 + 0.12 * P['TearOpen']) * P['TearH']])
    crev_last = [None]

    def moon_tau(dd, mm, amp):
        return P['SigmaL'] * (amp * dd[:, 1] * P['TauMaxD'] + mm[:, 1] * P['TauMaxM'])

    n = len(Vh)
    allr = np.arange(n)
    T = np.ones(n)
    acc = np.zeros((n, 3))
    thit = t1.copy()
    got = np.zeros(n, bool)
    t_prev = t0.copy()
    t_end = np.minimum(t1, P['MarchMax'])
    t_s = np.maximum(np.maximum(t0, P['MarchMin']), 0.5 * (ro[1] - cloud_top) / vyh)
    k = np.maximum(P['StepK'], (np.maximum(t_end / t_s, 1.0)) ** (1.0 / max(N - 1, 1)) - 1.0)     # reach t_end by step N-1
    # 1) coarse march, EXPONENTIAL steps t_i = t0 (1 + k)^(i + jitter): the vertical step ~ k x eye height everywhere;
    #    the soft skin above the heads (silver edges where a ray grazes a crest), until the ray dips under the field
    steps_used = np.zeros(n)
    c_prev = field(t_s, allr)[0]
    pend_od = np.zeros(n)
    pend_L = np.zeros((n, 3))
    for i in range(N):
        live = (~got) & (t_prev < t_end)
        steps_used[live] += 1
        if not live.any():
            break
        idx = allr[live]
        tm = np.minimum(t_s[idx] * (1 + k[idx]) ** (i + jit[idx]), t_end[idx])
        c, dd, mm, amp, foot = field(tm, idx)
        dt = np.maximum(tm - t_prev[idx], 0.0)
        ca = c_prev[idx]
        cb = np.maximum(c, 0.0)
        ca = np.maximum(ca, 0.0)
        edge0 = np.full(len(idx), P['SkinEdge'])
        edge = edge0 + 0.35 * foot
        # the skin's column over the segment, EXACT for a clearance varying linearly from ca to cb:
        #   integral exp(-c/e) ds = dt x e (exp(-ca/e) - exp(-cb/e)) / (cb - ca)
        dc = cb - ca
        ea, eb = np.exp(-ca / edge), np.exp(-cb / edge)
        col_ = np.where(np.abs(dc) > 1e-3, dt * edge * (ea - eb) / np.where(np.abs(dc) > 1e-3, dc, 1.0), dt * eb)
        od = P['SkinSigma'] * (edge0 / edge) * col_
        tau = moon_tau(dd, mm, amp) * (P['SkinSigmaL'] / P['SigmaL'])
        moon = P['MoonE'] * (phase[idx] * np.exp(-tau) + P['MsK'] * np.exp(-tau * P['MsTau']))
        S = moon[:, None] * MOON_COL + (P['AmbK'] * dd[:, 2])[:, None] * AMB_COL
        # rims, not lids (the finals: dark tops, bright silhouettes): skin met while the clearance SHRINKS is held as
        # pending; it is committed when the ray passes over the crest (clearance grows again), and only SkinApproach of
        # it counts if the ray sinks onto the surface instead
        pend_od[idx] += od
        pend_L[idx] += od[:, None] * S
        rising = c > c_prev[idx]
        ci = idx[rising]
        po = pend_od[ci]
        a = 1 - np.exp(-po)
        acc[ci] += (T[ci] * a / np.maximum(po, 1e-9))[:, None] * pend_L[ci]
        T[ci] *= 1 - a
        pend_od[ci] = 0.0
        pend_L[ci] = 0.0
        c_prev[idx] = c
        under = c < 0
        hit_i = idx[under]
        po = pend_od[hit_i] * P['SkinApproach']
        a = 1 - np.exp(-po)
        acc[hit_i] += (T[hit_i] * a / np.maximum(pend_od[hit_i], 1e-9))[:, None] * pend_L[hit_i]
        T[hit_i] *= 1 - a
        # 2) refine the crossing between the previous and this sample (5 bisections)
        lo, hi = t_prev[hit_i], tm[under]
        for _ in range(5):
            mid = 0.5 * (lo + hi)
            cmid = field(mid, hit_i)[0]
            below = cmid < 0
            hi = np.where(below, mid, hi)
            lo = np.where(below, lo, mid)
        thit[hit_i] = hi
        got[hit_i] = True
        t_prev[idx] = tm
    # rays that leave the march range (or the slab) unhit: the far deck = the field at the mean-height plane, shaded
    # as a surface at its (heavily filtered) LOD
    print('mean march steps %.1f (p90 %.0f), unhit %.0f%%' % (steps_used.mean(), np.percentile(steps_used, 90),
                                                           100 * (~got).mean()))
    far = ~got
    y_mean = cloud_top + P['FarMeanH']
    thit[far] = np.clip((ro[1] - y_mean) / vyh[far], t_end[far], 16000.0)
    got[:] = True
    farw = np.zeros(n)
    farw[far] = 1.0
    # 3) the surface at the hit: moon through the head (baked path), a softened forward lobe, sky x AO
    gi = allr[got]
    c, dd, mm, amp, foot = field(thit[gi], gi)
    tau = moon_tau(dd, mm, amp)
    ph_s = 1.0 + (phase[gi] - 1.0) * P['SurfPhase']
    # the dense surface: Lambert toward the moon (baked N.L, the moon-facing flanks silver when seen from behind or
    # the side) x the cast shadow of the heads in front (the baked path, self-path excluded by the Lambert term)
    lam = dd[:, 3]
    moon = P['MoonE'] * (P['SurfLambert'] * lam * np.exp(-tau * P['SurfShadow'])
                         + P['SurfMoon'] * ph_s * np.exp(-tau) + P['MsK'] * np.exp(-tau * P['MsTau']))
    var = P['VarMin'] + mm[:, 3] * (P['VarMax'] - P['VarMin'])
    # far (unmarched) rays: the crest rims that the march would have found, on average
    rim = P['FarRim'] * P['MoonE'] * phase[gi] * np.exp(-tau * P['SkinSigmaL'] / P['SigmaL']) * farw[gi]
    surf = ((moon + rim)[:, None] * MOON_COL + (P['AmbK'] * dd[:, 2])[:, None] * AMB_COL) * var[:, None] \
        + np.array(P['CrevGlow'])[None, :] * crev_last[0][:, None]
    acc[gi] += T[gi, None] * surf
    T[gi] = 0.0
    # fog at the hit distance (the half-transmittance point)
    fogC = band(Vh, ro, tear) + moon_air(Vh) * P['MoonAirFog']
    f = 1 - np.exp(-P['FogDensity'] * P['FogScale'] * thit)
    out = acc * P['Gain'] * (1 - f)[:, None] + fogC * f[:, None]
    if pool:   # approximate Tear_CloudGlow_Lit: dst x (1 + tint x weight) (not part of the deck shader)
        ph = ro + Vh * thit[:, None]
        S_ = 640.0 / 1000.0
        r = np.hypot(ph[:, 0] - O[0], ph[:, 2] - (O[2] - 150.0 * S_))
        wgt = 0.75 * np.exp(-(r / 420.0) ** 2) + 0.25 * np.exp(-r / 900.0)
        out = out * (1 + np.array([0.607, 0.683, 1.144])[None, :] * wgt[:, None])
    col[hit] = out
    alpha[hit] = 1.0
    dist[hit] = thit
    sky = band(V[~hit], ro, tear) + moon_air(V[~hit])
    col[~hit] = sky
    return col, alpha, dist


def grade(lin):
    G = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json')))
    P = G['profiles']['S4']['ppv2']
    p = {k: P[k] for k in ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain',
                           'mixer') if k in P}
    p.update(colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
    return np.clip(PE.codes(lin, p), 0, 255)


def main():
    a = sys.argv[1:]
    camname = a[0]
    w = int(a[a.index('--w') + 1]) if '--w' in a else 960
    tex = os.path.abspath(a[a.index('--tex') + 1]) if '--tex' in a else os.path.join(KIT, 'Textures')
    out = a[a.index('--out') + 1] if '--out' in a else '/tmp/claude-0/gc/deck_%s.png' % camname
    P = dict(DEFAULTS)
    if '--set' in a:
        for kv in a[a.index('--set') + 1].split(','):
            k, v = kv.split('=')
            P[k] = float(v)
    cam = LAYOUT['cameras'][camname]
    t = float(a[a.index('--t') + 1]) if '--t' in a else cam['t']
    h = int(round(w / cam['aspect']))
    col, alpha, dist = render_deck(cam, t, w, h, tex, P, pool='--nopool' not in a)
    img = grade(col)
    Image.fromarray(img.astype(np.uint8)).save(out)
    np.save(out.replace('.png', '_lin.npy'), col.astype(np.float32))
    print('wrote', out, 'APL bottom 20%%: %.1f' % (img[int(h * 0.8):] @ [0.2126, 0.7152, 0.0722]).mean())


if __name__ == '__main__':
    main()
