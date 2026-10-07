"""Stop_WetMask_2048x512 + Road_WetMask_2048x512 (bible §6·1, §6·2 '湿路同第 1 幕', §4.9, §5.4, §5.5, §6·12).

v2 (verification round 2, M5): the stop mask no longer ends on a straight line. Both masks are cut from ONE road
surface that repeats every 60 m along the road (the R_Road module length, bible §6·2):
  * Road_WetMask covers one 60 m period (2.93 cm / texel) and TILES along the road (Wrap U = Repeat, V = Clamp);
  * Stop_WetMask covers the 48 m around the stop (2.34 cm / texel) = the same road + the stop's own features (sag
    toward the door, deeper bus-lane ruts, the bus-bay lip, the pull-over tracks, the four hero hollows, the shelter
    under the parked bus) faded out toward its ends; its last 3 m blend exactly into the road mask, so
    Lanbai/WetSurface continues seamlessly with the road mask outside the rect.
Road coordinate s (m along the road) = Z_u + 21 (stop-local); the centre dashes start at s = 0 (Z_u = -21).
Centre dashes: 3 m paint every 60/7 = 8.571 m (7 per module; the bible's 3 m / 6 m rhythm rounded to tile), 60 % worn;
broken edge lines, 40 % left. No yellow.

FRAME. Stage coords of the Sign kit (x_b along the road = bus heading, y_b toward the far side, stop/door side = -y_b).
       R_Stop local Unity frame: X_u = -y_b (right of heading = door side), Y_u = z_b, Z_u = x_b (heading).
MAPPING. Stop:  u = (Z_u + 22) / 48 ;  v = (5 - X_u) / 12.
         Road:  u = (Z_u + 21) / 60  (repeat) or u = UV2.x / 60 on R_Road modules; v = (5 - X_u) / 12 (UV2.y = X_u).
         PNG row 0 = v = 1 (far side on top, heading to the right: a normal plan view from above).
CHANNELS (linear, sRGB OFF):
  R  standing water: R = sqrt(clamp(depth / 8 mm, 0, 1)); 0 = no puddle (flooded depressions of the simulated surface).
  G  film retention 0..1: crown dries first (bible §6·12 0.85 -> crown 0.55); ruts / edges / puddle margins wettest.
  B  shelter (stop only): 1 = under the parked bus (damp: albedo x0.8, smoothness 0.45; bible §4.9).
  A  road paint (worn white).
usage: python3 make_wetmask.py [outdir]
"""
import heapq, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
DX = 48.0 / 2048                    # 2.34 cm, the stop mask's texel (all simulation at this resolution)
PERIOD = 60.0                       # R_Road module length = road mask period
NP = int(round(PERIOD / DX))        # 2560 samples per period
NV = 512
Y0, Y1 = -5.0, 7.0                  # y_b range (= -X_u)
S0 = -21.0                          # Z_u where road coordinate s = 0 (first centre dash starts here)
STOP_X0, STOP_X1 = -22.0, 26.0
DASH_P = PERIOD / 7.0
rng = np.random.default_rng(20260930)
ys = Y0 + (np.arange(NV) + 0.5) * DX

L = dict(
    road_y=(0.0, 6.5), crown_y=3.25, shoulder_y=(-4.2, 0.0), bund_y=(-4.75, -4.2),
    bus_x=(-7.9, 0.1), bus_y=(0.45, 2.75), bus_axles_x=(-1.95, -6.2), tyre_y=(0.72, 2.48),
    door_x=(-1.2, -0.3), hero_eye=(-1.3, 0.85, 2.10),
    sign=(3.40, -3.10, 2.25), sign_normal=(-0.8, 0.6), lamp_pole=(1.72, -3.34), tube=(2.44, -2.38, 3.90),
    tube_axis=(0.6, 0.8), notice_case=(6.65, -3.37), case_normal=(-0.5, 0.87), spawn=(-10.6, -1.8),
)
# drip impact points (stage x, y) and the height of the surface they land on (m above the road datum)
L['drips'] = dict(
    lamp=(2.83, -1.86, 0.0),           # outer end of the enamel trough (lowest point), falls 3.9 m into 'lamp_drip'
    sign=(3.36, -3.06, 0.03),          # sign's lower rim, 5 cm in front of the pole: lands on the footing top (a
                                       # 400 x 400 slab 30 mm proud that holds a skin of water: README §7)
    case=(6.88, -3.07, 0.0),           # notice-case drip cap, front corner, falls ~2.2 m into 'notice_case'
)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fbm_periodic(lam_min, lam_max, seed, beta=2.0):
    """band-limited noise on the PERIODIC road grid (NV x NP), unit std; periodic along x by construction (FFT)."""
    r = np.random.default_rng(seed)
    n = r.normal(size=(NV, NP))
    F = np.fft.rfft2(n)
    ky = np.fft.fftfreq(NV, DX)[:, None]; kx = np.fft.rfftfreq(NP, DX)[None, :]
    k = np.hypot(kx, ky)
    band = (k >= 1 / lam_max) & (k <= 1 / lam_min)
    amp = np.where(band, np.maximum(k, 1e-6) ** (-beta / 2), 0)
    f = np.fft.irfft2(F * amp, s=(NV, NP))
    return f / f.std()


# ---------------------------------------------------------------- the periodic road (grid over s in [0, 60))
s_p = (np.arange(NP) + 0.5) * DX
Sg, Yp = np.meshgrid(s_p, ys)
road_p = (Yp >= 0) & (Yp <= 6.5)
shoulder_p = (Yp < 0) & (Yp >= -4.2)
N = {k: fbm_periodic(*a) for k, a in dict(und=(0.5, 4.0, 1), agg=(0.08, 0.5, 2), edge=(0.1, 1.5, 3), along=(2.0, 10.0, 15),
                                           sh=(0.4, 3.0, 4), sh2=(0.04, 0.4, 5), bund=(0.3, 3, 7), verge=(0.2, 2, 8),
                                           g1=(0.3, 3.0, 9), g2=(0.05, 0.3, 10), wear1=(0.05, 1.2, 12), wear2=(0.01, 0.05, 13),
                                           seg0=(2.0, 12.0, 14), seg6=(2.0, 12.0, 20), wob=(1.0, 6.0, 6), ins=(0.2, 1.5, 11)).items()}
z_p = np.zeros((NV, NP))
z_p += np.where(road_p, -0.020 * np.abs(Yp - 3.25), 0)                     # 2 % crown
for yw in (0.75, 2.45):                                                      # wheel ruts, bus lane
    z_p -= np.where(road_p, 0.006 * np.exp(-((Yp - yw) / 0.24) ** 2) - 0.0015 * np.exp(-((np.abs(Yp - yw) - 0.48) / 0.12) ** 2), 0)
for yw in (4.05, 5.75):
    z_p -= np.where(road_p, 0.0065 * np.exp(-((Yp - yw) / 0.22) ** 2), 0)
z_p += np.where(road_p, 0.0090 * N['und'] + 0.0012 * N['agg'], 0)
along_var = 0.5 + 0.5 * np.clip(N['along'], -1, 1)
z_p -= np.where(road_p, 0.0055 * along_var * sstep(0.45 + 0.12 * N['edge'], 0.0, Yp), 0)
z_p -= np.where(road_p, 0.0030 * (1 - along_var) * sstep(6.1, 6.5, Yp), 0)


def ell(Xs, Ys, cx, cy, rx, ry, ang=0.0):
    ca, sa = np.cos(ang), np.sin(ang)
    u = (Xs - cx) * ca + (Ys - cy) * sa; v = -(Xs - cx) * sa + (Ys - cy) * ca
    return np.hypot(u / rx, v / ry)


def wrapd(a, b):                     # periodic difference a - b on the 60 m road
    return (a - b + PERIOD / 2) % PERIOD - PERIOD / 2


# road-wide patches and potholes (in road coordinates s) - outside the stop's interior they repeat every module
for (s0, s1, y0, y1) in [(14.2, 16.4, 0.35, 2.2), (33.6, 35.4, 3.7, 6.2), (52.0, 53.8, 0.6, 2.4)]:
    m = (Sg > s0) & (Sg < s1) & (Yp > y0) & (Yp < y1)
    z_p -= np.where(m, 0.003, 0)
    edge = np.abs(ndimage.binary_dilation(m, iterations=2).astype(float) - ndimage.binary_erosion(m, iterations=2).astype(float))
    z_p -= 0.002 * edge
for (sc, cy, rx, ry, d, ang) in [(29.6, 1.35, 0.38, 0.30, 0.024, 0.3), (6.8, 4.6, 0.55, 0.28, 0.016, -0.2), (38.5, 2.1, 0.26, 0.22, 0.020, 0.0),
                                 (46.2, 5.2, 0.42, 0.25, 0.014, 0.5)]:
    e = ell(wrapd(Sg, sc), Yp, 0.0, cy, rx, ry, ang) * (1 + 0.12 * N['edge'])
    z_p -= d * sstep(1.0, 0.55, e)
z_edge_p = -0.020 * 3.25
z_p += np.where(shoulder_p, z_edge_p - 0.006 - 0.016 * (-Yp / 4.2) + 0.006 * N['sh'] + 0.0012 * N['sh2'], 0)
z_p = np.where((Yp < -4.2) & (Yp >= -4.75), 0.02 + 0.01 * N['bund'], z_p)
z_p = np.where(Yp < -4.75, -0.18, z_p)
z_p = np.where(Yp > 6.5, z_edge_p - 0.008 + 0.004 * N['verge'] - 0.03 * sstep(6.5, 7.0, Yp), z_p)

# paint (periodic)
wear_p = N['wear1'] * 0.7 + N['wear2'] * 0.3
A_p = np.zeros((NV, NP))
dash = (Sg % DASH_P) < 3.0
cl = (np.abs(Yp - 3.25) < 0.06) & dash
A_p[cl & (wear_p > np.quantile(wear_p[cl], 0.60))] = 1.0                       # 60 % worn
for ye, segn in ((0.16, 'seg0'), (6.34, 'seg6')):
    el = (np.abs(Yp - ye) < 0.05) & (N[segn] > 0.0)
    keep = wear_p > np.quantile(wear_p[np.abs(Yp - ye) < 0.05], 0.60)            # 40 % of the full line left
    A_p[el & keep] = 1.0
A_p = ndimage.gaussian_filter(A_p, 0.6, mode=('nearest', 'wrap'))


def take(field, x0, n):
    """columns of a periodic field for stage x = x0 + (i + 0.5) DX, i < n (x in Z_u, s = x - S0)"""
    i0 = int(round((x0 - S0) / DX))
    idx = (i0 + np.arange(n)) % NP
    return field[:, idx]


# ---------------------------------------------------------------- priority-flood depression filling
def priority_flood(z, sink, periodic=False):
    H, W = z.shape
    filled = z.copy()
    closed = np.zeros_like(sink)
    pq = []
    border = np.zeros_like(sink); border[0, :] = border[-1, :] = True
    if not periodic:
        border[:, 0] = border[:, -1] = True
    seeds = border | sink
    for j, i in zip(*np.nonzero(seeds)):
        heapq.heappush(pq, (z[j, i], j, i)); closed[j, i] = True
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while pq:
        h, j, i = heapq.heappop(pq)
        for dj, di in nb:
            jj, ii = j + dj, i + di
            if periodic:
                ii %= W
            if 0 <= jj < H and 0 <= ii < W and not closed[jj, ii]:
                closed[jj, ii] = True
                filled[jj, ii] = max(filled[jj, ii], h)
                heapq.heappush(pq, (filled[jj, ii], jj, ii))
    return filled


def flood_depth(z, Ys, periodic):
    sink = (Ys < -4.2) | (Ys > 6.9)
    zf = np.where(sink, -1.0, z)
    filled = priority_flood(zf, sink, periodic)
    return np.where(sink, 0.0, filled - zf)


def solve_level(depth_full, mask, target):
    lo, hi = 0.0, 0.03
    for _ in range(40):
        h = 0.5 * (lo + hi)
        frac = ((depth_full - h) > 0.0002)[mask].mean()
        lo, hi = (h, hi) if frac > target else (lo, h)
    return 0.5 * (lo + hi)


def film_G(z, depth, Ys, road, shoulder, g1, g2):
    rel = z - ndimage.uniform_filter(z, size=int(1.0 / DX), mode='nearest')
    G = 0.55 - rel / 0.004 * 0.18
    dist_p = ndimage.distance_transform_edt(depth <= 0.0002) * DX
    G += 0.35 * np.exp(-dist_p / 0.25)
    G -= np.where(road, 0.35 * np.exp(-((Ys - 3.25) / 0.9) ** 2), 0)
    for yw in (0.75, 2.45, 4.05, 5.75):
        G += np.where(road, 0.12 * np.exp(-((Ys - yw) / 0.25) ** 2), 0)
    G += 0.10 * g1 + 0.05 * g2
    G = np.where(shoulder, G * 0.85 + 0.1, G)
    return np.clip(G, 0, 1)


print('flooding the periodic road ...', flush=True)
zt = np.tile(z_p, (1, 3)); Yt = np.tile(Yp, (1, 3))
dfull_t = flood_depth(zt, Yt, periodic=True)
dfull_p = dfull_t[:, NP:2 * NP]
H0 = solve_level(dfull_p, road_p, 0.18)                    # an ordinary stretch of old road: 18 % under water
H1 = solve_level(dfull_p, shoulder_p, 0.08)                # the gravel shoulder is porous: ~8 %
depth_p = np.maximum(dfull_p - np.where(shoulder_p, H1, H0), 0)
depth_p[(Yp < -4.2) | (Yp > 6.5)] = 0.0
# G on a 3x tile (filters see across the period), keep the middle
Gt = film_G(zt, np.tile(depth_p, (1, 3)), Yt, np.tile(road_p, (1, 3)), np.tile(shoulder_p, (1, 3)),
            np.tile(N['g1'], (1, 3)), np.tile(N['g2'], (1, 3)))
G_p = Gt[:, NP:2 * NP]
R_p = np.sqrt(np.clip(depth_p / 0.008, 0, 1))

# ---------------------------------------------------------------- the stop: an extended window of the same road
EXT = 24.0
xa = STOP_X0 - EXT
NE = int(round((STOP_X1 + EXT - xa) / DX))
xs_e = xa + (np.arange(NE) + 0.5) * DX
X, Y = np.meshgrid(xs_e, ys)
road = (Y >= 0) & (Y <= 6.5)
shoulder = (Y < 0) & (Y >= -4.2)
win = sstep(STOP_X0, STOP_X0 + 6.0, X) * sstep(STOP_X1, STOP_X1 - 6.0, X)       # stop features fade to 0 at its ends
z = take(z_p, xa, NE).copy()
edge_noise = take(N['edge'], xa, NE)
# the stop sits in a low point: water gathers at the door
z += win * 0.028 * (1 - np.exp(-((X + 0.8) / 13.0) ** 2)) - win * 0.028 * (1 - np.exp(-(25.0 / 13.0) ** 2))
for yw in (0.75, 2.45):                                                          # buses brake and stand here: deeper ruts
    z -= win * np.where(road, 0.007 * np.exp(-((X + 4.0) / 7.0) ** 2) * np.exp(-((Y - yw) / 0.24) ** 2), 0)
lip = sstep(-13.5, -11.5, X) * sstep(-1.0, -2.0, X) * np.exp(-((Y + 0.35) / 0.16) ** 2)
z += np.where(shoulder, 0.016 * lip * (1 + 0.2 * edge_noise), 0)                 # gravel lip along the bus bay
wob_e = take(N['wob'], xa, NE)
for yt, x_a, x_b in [(-0.40, -16.0, 1.0), (-2.15, -15.0, -0.5)]:                  # pull-over tyre tracks
    alongm = sstep(x_a, x_a + 3.0, X) * sstep(x_b, x_b - 3.0, X)
    z -= np.where(shoulder, 0.014 * alongm * np.exp(-((Y - yt - 0.10 * wob_e) / 0.17) ** 2), 0)
HERO = [
    dict(name='door', desc='seen from the hero seat through the open door: the tube (analytic) and the sign (mirror copy)',
         c=(0.45, -0.70), r=(1.15, 0.42), ang=np.radians(-35), depth=0.026),
    dict(name='lamp_drip', desc='under the lamp-arm drip (bible §5.4), brightest part of the lamp pool',
         c=(2.80, -1.80), r=(0.52, 0.36), ang=np.radians(20), depth=0.020),
    dict(name='notice_case', desc='at the case foot, under the drip-cap drip (bible §5.5); mirrors the lit credits at 12 +95 s',
         c=(6.48, -2.98), r=(0.90, 0.46), ang=np.radians(28), depth=0.022),
    dict(name='spawn_walk', desc='in the pull-over tyre track: mirrors the tube in the first frame from the spawn',
         c=(-6.8, -2.05), r=(1.05, 0.30), ang=np.radians(3), depth=0.014),
]
for h in HERO:
    e = ell(X, Y, *h['c'], *h['r'], h['ang']) * (1 + 0.10 * edge_noise)
    z -= h['depth'] * sstep(1.05, 0.35, e)
bus = (X > L['bus_x'][0]) & (X < L['bus_x'][1]) & (Y > L['bus_y'][0]) & (Y < L['bus_y'][1])
print('flooding the stop ...', flush=True)
dfull = flood_depth(z, Y, periodic=False)
dfull[bus] = 0.0                                          # no rain under the bus
depth = np.maximum(dfull - np.where(shoulder, H1, H0), 0)
for h in HERO:                                            # hero puddles hold water whatever the global level
    e = ell(X, Y, *h['c'], *h['r'], h['ang']) * (1 + 0.10 * edge_noise)
    depth = np.maximum(depth, (h['depth'] * 0.8) * sstep(1.0, 0.45, e))
depth[(Y < -4.2) | (Y > 6.5)] = 0.0
G = film_G(z, depth, Y, road, shoulder, take(N['g1'], xa, NE), take(N['g2'], xa, NE))

# shelter under the parked bus
bx0, bx1 = L['bus_x']; by0, by1 = L['bus_y']
inset = 0.12 + 0.05 * take(N['ins'], xa, NE)
dxin = np.minimum(X - (bx0 + 0.07), bx1 - X); dyin = np.minimum(Y - by0, by1 - Y)
din = np.minimum(dxin, dyin)
B = sstep(inset - 0.03, inset + 0.10, din)
flow_w = np.zeros_like(z)
gy, gx = np.gradient(ndimage.gaussian_filter(z, 2))
for s_ in range(90):
    px = rng.uniform(bx0 + 0.2, bx1 - 0.2); py = by1 + 0.05
    for step in range(400):
        i = int((px - xa) / DX); j = int((py - Y0) / DX)
        if not (0 <= i < NE and 0 <= j < NV) or py < by0 - 0.1:
            break
        flow_w[j, i] += 1
        g = np.array([gx[j, i], gy[j, i]]); n = np.hypot(*g)
        dirv = -g / n if n > 1e-9 else np.array([0, -1.0])
        dirv = 0.6 * dirv + 0.4 * np.array([0, -1.0]) + rng.normal(0, 0.25, 2)
        dirv /= np.hypot(*dirv)
        px += dirv[0] * DX; py += dirv[1] * DX
        if rng.random() < 0.004 * step:
            break
riv = ndimage.gaussian_filter(np.minimum(flow_w, 2), 1.0)
riv = riv / max(riv.max(), 1e-9)
B = np.clip(B - 2.2 * riv * sstep(by1 + 0.05, by1 - 1.3, Y), 0, 1)
dl = np.exp(-((din + 0.06) / 0.035) ** 2) * ((X > bx0 - 0.2) & (X < bx1 + 0.2) & (Y > by0 - 0.2) & (Y < by1 + 0.2))
G = np.clip(np.maximum(G, 0.95 * dl), 0, 1)
G = np.where(B > 0.5, G * (1 - B) + 0.05, G)
R = np.sqrt(np.clip(depth / 0.008, 0, 1))
A = take(A_p, xa, NE)

# crop the 48 m and blend the last 3 m into the road mask exactly
c0 = int(round((STOP_X0 - xa) / DX)); NU = 2048
sl = slice(c0, c0 + NU)
Xs, Ys_ = X[:, sl], Y[:, sl]
R, G, B, A = R[:, sl], G[:, sl], B[:, sl], A[:, sl]
depth = depth[:, sl]; z = z[:, sl]
roadR, roadG, roadA = take(R_p, STOP_X0, NU), take(G_p, STOP_X0, NU), take(A_p, STOP_X0, NU)
fe = 1 - sstep(STOP_X0, STOP_X0 + 3.0, Xs) * sstep(STOP_X1, STOP_X1 - 3.0, Xs)     # 1 at the ends
R = R * (1 - fe) + roadR * fe; G = G * (1 - fe) + roadG * fe; A = A * (1 - fe) + roadA * fe; B = B * (1 - fe)
road_s = (Ys_ >= 0) & (Ys_ <= 6.5); shoulder_s = (Ys_ < 0) & (Ys_ >= -4.2); bus_s = bus[:, sl]
road_frac = float((R > np.sqrt(0.0002 / 0.008))[road_s & ~bus_s].mean())
sh_frac = float((R > np.sqrt(0.0002 / 0.008))[shoulder_s].mean())

# ---------------------------------------------------------------- write
img = np.stack([R, G, B, A], -1)[::-1]
Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'Stop_WetMask_2048x512.png'))
# road mask: resample the 2560-sample period to 2048 texels (box over 1.25 samples, periodic)
def resample_periodic(f, n_out):
    xin = (np.arange(NP) + 0.5) / NP; xo = (np.arange(n_out) + 0.5) / n_out
    fs = ndimage.uniform_filter1d(f, size=2, axis=1, mode='wrap')
    xx = np.concatenate([xin - 1, xin, xin + 1])
    return np.stack([np.interp(xo, xx, np.tile(row, 3)) for row in fs])
roadimg = np.stack([resample_periodic(R_p, 2048), resample_periodic(G_p, 2048), np.zeros((NV, 2048)), resample_periodic(A_p, 2048)], -1)[::-1]
Image.fromarray(np.clip(np.round(roadimg * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'Road_WetMask_2048x512.png'))
np.save(os.path.join(OUT, 'wetmask_depth.npy'), depth.astype(np.float32))
np.save(os.path.join(OUT, 'wetmask_z.npy'), z.astype(np.float32))
road_mask_frac = float((R_p > np.sqrt(0.0002 / 0.008))[road_p].mean())
road_mask_sh = float((R_p > np.sqrt(0.0002 / 0.008))[shoulder_p].mean())


def to_unity(p):
    return dict(X=round(-p[1], 3), Z=round(p[0], 3))


outlines = {}
lab, n = ndimage.label(depth > 0.001)
for h in HERO:
    ci = int((h['c'][0] - STOP_X0) / DX); cj = int((h['c'][1] - Y0) / DX)
    k = lab[cj, ci]
    m = lab == k
    edge = m & ~ndimage.binary_erosion(m)
    jj, ii = np.nonzero(edge)
    ang = np.arctan2(Ys_[jj, ii] - h['c'][1], Xs[jj, ii] - h['c'][0])
    o = np.argsort(ang)
    pts = [(round(float(Xs[jj[q], ii[q]]), 3), round(float(Ys_[jj[q], ii[q]]), 3)) for q in o[::max(1, len(o) // 48)]]
    outlines[h['name']] = dict(desc=h['desc'], area_m2=round(float(m.sum() * DX * DX), 3),
                               max_depth_mm=round(float(depth[m].max() * 1e3), 1),
                               outline_stage_xy=pts, outline_unity_XZ=[(-p[1], p[0]) for p in pts])
# check: every ringing drip lands in water
drip_check = {}
for k, (dx_, dy_, dz_) in L['drips'].items():
    i = int((dx_ - STOP_X0) / DX); j = int((dy_ - Y0) / DX)
    drip_check[k] = dict(depth_mm=round(float(depth[j, i] * 1e3), 1), lands_on='footing top (WetSurface pool)' if k == 'sign' else 'puddle')
meta = dict(doc=__doc__, texel_m=DX, period_m=PERIOD, dash_period_m=DASH_P, road_s0_Zu=S0,
            rect_stage=dict(x=(STOP_X0, STOP_X1), y=(Y0, Y1)), rect_unity_local=dict(Z=(STOP_X0, STOP_X1), X=(-Y1, -Y0)),
            uv_stop='u = (Z_u + 22) / 48 ; v = (5 - X_u) / 12', uv_road='u = frac((Z_u + 21) / 60) (or UV2.x / 60) ; v = (5 - X_u) / 12',
            water_level_below_spill_mm=round(H0 * 1e3, 2), shoulder_level_mm=round(H1 * 1e3, 2),
            stop_road_puddle_fraction=round(road_frac, 3), stop_shoulder_puddle_fraction=round(sh_frac, 3),
            road_mask_road_puddle_fraction=round(road_mask_frac, 3), road_mask_shoulder_puddle_fraction=round(road_mask_sh, 3),
            layout_stage=L, layout_unity={k: to_unity(v) for k, v in L.items() if isinstance(v, tuple) and len(v) >= 2 and not k.endswith(('_y', '_x', 'normal', 'axis'))},
            drips_unity={k: dict(X=round(-v[1], 3), Z=round(v[0], 3), Y_surface=v[2]) for k, v in L['drips'].items()},
            drip_check=drip_check, hero_puddles=outlines)
json.dump(meta, open(os.path.join(OUT, 'Stop_Layout.json'), 'w'), indent=1, default=float)
print('levels %.2f / %.2f mm; stop road %.3f shoulder %.3f; road mask road %.3f shoulder %.3f' % (H0 * 1e3, H1 * 1e3, road_frac, sh_frac, road_mask_frac, road_mask_sh))
print('drips', drip_check)
for k, v in outlines.items():
    print(k, v['area_m2'], 'm2, max depth', v['max_depth_mm'], 'mm')
