"""蓝白 · 星海的星与银河辉光（ART BIBLE v2.1 §6·9、§8.1 #8 extract_stars）。
Run:  ~/bpy/bin/python -I make_starsky.py            (numpy, scipy, pillow, OpenEXR)

Inputs (Sky/Source~/data/, all downloaded 2026-10-22; NASA SVS Deep Star Maps is not reachable from the cloud):
  bsc5.json                              Yale Bright Star Catalogue 5th ed. (Hoffleit & Warren 1991, NASA ADC; public
                                         domain), JSON by github.com/brettonw/YaleBrightStarCatalog. -> the ~9 000 star points
  hipparcos_d3celestial_stars14.json     Hipparcos (ESA 1997) 118 216 stars, packaged by d3-celestial (BSD-3, O. Frohn).
                                         -> only the unresolved light of the stars fainter than 6.5 mag (glow structure)
  mw_vieira_d3celestial.json             Milky Way Outline Catalog, J. R. Vieira (skymap.com), 5 brightness steps, as
                                         packaged by d3-celestial (BSD-3). -> the band, the star clouds, the Great Rift
Outputs:
  Sky/Textures/StarSky_Glow_4096x2048.exr   world-frame equirect, linear half float (see GLOW MAPPING); no stars in it
  Sky/Data/StarPoints_BSC5.csv              one row per star: Unity world direction, V mag, B-V, linear colour, rank
  Sky/Data/StarSky.json                     the orientation (equatorial -> Unity world), targets, counts
  Sky/Docs~/starsky_*.png                   previews

ORIENTATION (bible §6·9): galactic centre at azimuth -30 deg (left of straight ahead), elevation +12 deg; the band
arches over the zenith to the right-rear and passes under the bus (the lower half is the other half of the same sky:
space, not a reflection). Computed in ENU (x east = Unity +X, y north = Unity +Z, z up = Unity +Y), a proper rotation
from J2000 equatorial, so the constellations keep their real handedness; then (x, y, z)_ENU -> (x, z, y)_Unity.
Azimuth = clockwise from +Z (ahead) toward +X (right).

GLOW MAPPING (what Lanbai/Sky samples, tex2Dlod, no mips): az = atan2(V.x, V.z) in (-180, 180], el = asin(V.y);
u = 0.5 + az / 360, v = 0.5 + el / 180 (v = 1 at the zenith; Unity's texture v = 0 is the bottom row of the PNG/EXR
as stored top-down, so row 0 of the file is el = +90).
Values: linear fill values at galaxy gain 1 (bible S9a fills: the brightest diffuse band #6A758A, the warm dust near
the galactic centre #CBAE82; the star floor #0D0F23 is NOT in the texture, Lanbai/Sky adds it).
"""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SKY = os.path.dirname(HERE)
D = os.path.join(HERE, 'data')
W, H = 4096, 2048           # glow map
RW, RH = 8192, 4096         # equatorial raster for the outlines

GC_AZ, GC_EL = -30.0, 12.0
GLOW_DIFFUSE_FILL = '#6A758A'   # S9a fill, the brightest diffuse part of the band
GLOW_DUST_FILL = '#CBAE82'      # S9a fill, warm dust at the galactic centre
MAG_LIMIT = 6.5


def srgb_to_lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def hexlin(h):
    return srgb_to_lin([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def radec_vec(ra_deg, dec_deg):
    ra, dec = np.radians(ra_deg), np.radians(dec_deg)
    return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1)


def enu_dir(az, el):
    az, el = math.radians(az), math.radians(el)
    return np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])


# ---- orientation ------------------------------------------------------------------------------------------------
G_EQ = np.array([-0.0548755604, -0.8734370902, -0.4838350155])     # galactic centre (J2000)
N_EQ = np.array([-0.8676661490, -0.1980763734, 0.4559837762])      # north galactic pole
Y_EQ = np.cross(N_EQ, G_EQ)                                         # l = 90 deg
g_w = enu_dir(GC_AZ, GC_EL)
up = np.array([0.0, 0.0, 1.0])
n_w = np.cross(g_w, up); n_w /= np.linalg.norm(n_w)
y_w = np.cross(n_w, g_w)
if y_w[2] < 0:                       # l = 90 (Cygnus) climbs toward the zenith from the centre
    n_w = -n_w; y_w = np.cross(n_w, g_w)
R = np.stack([g_w, y_w, n_w], 1) @ np.stack([G_EQ, Y_EQ, N_EQ], 0)  # equatorial -> ENU
assert abs(np.linalg.det(R) - 1) < 1e-9


def eq_to_unity(v_eq):
    e = v_eq @ R.T
    return np.stack([e[..., 0], e[..., 2], e[..., 1]], -1)


def unity_to_eq(v_u):
    e = np.stack([v_u[..., 0], v_u[..., 2], v_u[..., 1]], -1)
    return e @ R


def parse_ra(s):
    h, m, sec = s.replace('h', '').replace('m', '').replace('s', '').split()
    return 15.0 * (float(h) + float(m) / 60 + float(sec) / 3600)


def parse_dec(s):
    s = s.replace('°', ' ').replace('′', ' ').replace('″', ' ')
    sign = -1 if s.strip().startswith('-') else 1
    d, m, sec = [abs(float(x)) for x in s.split()]
    return sign * (d + m / 60 + sec / 3600)


def bv_to_rgb(bv):
    """B-V -> linear sRGB of the blackbody (Ballesteros 2012 temperature), normalised to luminance 1, then 45 %
    toward white: the bible's star colour is #F2F6FF, not a planetarium rainbow."""
    bv = np.clip(bv, -0.4, 2.0)
    T = 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62))
    lam = np.linspace(380e-9, 780e-9, 81)
    # CIE 1931 2-deg CMF, analytic multi-lobe fit (Wyman, Sloan, Shirley 2013)
    l = lam * 1e9
    def g(x, mu, s1, s2):
        return np.exp(-0.5 * ((x - mu) / np.where(x < mu, s1, s2)) ** 2)
    xb = 1.056 * g(l, 599.8, 37.9, 31.0) + 0.362 * g(l, 442.0, 16.0, 26.7) - 0.065 * g(l, 501.1, 20.4, 26.2)
    yb = 0.821 * g(l, 568.8, 46.9, 40.5) + 0.286 * g(l, 530.9, 16.3, 31.1)
    zb = 1.217 * g(l, 437.0, 11.8, 36.0) + 0.681 * g(l, 459.0, 26.0, 13.8)
    hc_k = 1.4388e-2
    B = 1.0 / (lam[None, :] ** 5 * (np.exp(hc_k / (lam[None, :] * T[:, None])) - 1.0))
    XYZ = np.stack([(B * xb).sum(1), (B * yb).sum(1), (B * zb).sum(1)], 1)
    M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    rgb = np.maximum(XYZ @ M.T, 0)
    rgb /= (rgb @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
    return 0.55 * rgb + 0.45


# ---- 1. star points (BSC5) --------------------------------------------------------------------------------------
bsc = json.load(open(os.path.join(D, 'bsc5.json')))
rows = []
for s in bsc:
    if 'RA' not in s or 'Dec' not in s or 'Vmag' not in s:
        continue
    try:
        v = float(s['Vmag']); bv = float(s.get('B-V', '0.6') or 0.6)
    except ValueError:
        continue
    if v > MAG_LIMIT:
        continue
    rows.append((int(s['HR']), parse_ra(s['RA']), parse_dec(s['Dec']), v, bv, s.get('Name', '')))
rows.sort(key=lambda r: r[3])
hr = np.array([r[0] for r in rows]); ra = np.array([r[1] for r in rows]); dec = np.array([r[2] for r in rows])
vm = np.array([r[3] for r in rows]); bv = np.array([r[4] for r in rows])
dirs = eq_to_unity(radec_vec(ra, dec))
cols = bv_to_rgb(bv)
os.makedirs(os.path.join(SKY, 'Data'), exist_ok=True)
with open(os.path.join(SKY, 'Data', 'StarPoints_BSC5.csv'), 'w') as f:
    f.write('# Yale Bright Star Catalogue 5 (public domain) to V %.1f, oriented by Sky/Source~/make_starsky.py; '
            'dir = Unity world unit vector; colour = linear sRGB, luminance 1; rank 0 = brightest\n' % MAG_LIMIT)
    f.write('hr,dir_x,dir_y,dir_z,vmag,bv,r,g,b,rank\n')
    for i in range(len(rows)):
        f.write('%d,%.6f,%.6f,%.6f,%.2f,%.2f,%.4f,%.4f,%.4f,%d\n' % (hr[i], *dirs[i], vm[i], bv[i], *cols[i], i))
print('stars <= %.1f mag: %d' % (MAG_LIMIT, len(rows)))

# ---- 2. Milky Way outlines -> 5-step brightness in the equatorial raster ---------------------------------------
mw = json.load(open(os.path.join(D, 'mw_vieira_d3celestial.json')))


def ring_pixels(ring):
    a = np.array(ring, np.float64)
    lon = a[:, 0]; lat = a[:, 1]
    jumps = np.where(np.abs(np.diff(lon)) > 180)[0]
    if len(jumps) % 2 == 1:
        # a ring that goes once around the sphere (a band edge): open it at the jump, close it over the north pole
        k = jumps[0] + 1
        lon = np.concatenate([lon[k:], lon[:k]]); lat = np.concatenate([lat[k:], lat[:k]])
        lon = np.unwrap(np.radians(lon)) * 180 / np.pi
        lon = np.concatenate([lon, [lon[-1], lon[0]]]); lat = np.concatenate([lat, [90.0, 90.0]])
    elif len(jumps):
        lon = np.unwrap(np.radians(lon)) * 180 / np.pi
    x = (lon + 180.0) / 360.0 * RW
    y = (90.0 - lat) / 180.0 * RH
    return x, y


def level_mask(feature):
    acc = np.zeros((RH, RW), np.uint8)
    for poly in feature['geometry']['coordinates']:
        for ring in poly:
            x, y = ring_pixels(ring)
            img = Image.new('L', (RW, RH), 0)
            d = ImageDraw.Draw(img)
            for sh in (-RW, 0, RW):
                d.polygon(list(zip(x + sh, y)), fill=1)
            acc ^= np.asarray(img, np.uint8)
    # even-odd filling leaves 1-3 px slivers where rings touch (they read as long straight lines on the sky)
    return ndimage.binary_opening(acc.astype(bool), iterations=3).astype(np.uint8)


levels = np.zeros((RH, RW), np.float32)
for f in mw['features']:
    m = level_mask(f)
    levels += m
    print('outline', f['id'], 'sky fraction %.3f' % (m.mean()))

# ---- 3. faint Hipparcos stars (6.5 .. 11 mag) -> unresolved light in the same raster -----------------------------
hip = json.load(open(os.path.join(D, 'hipparcos_d3celestial_stars14.json')))['features']
hl = np.array([f['geometry']['coordinates'] for f in hip]); hm = np.array([float(f['properties']['mag']) for f in hip])
sel = (hm > MAG_LIMIT) & (hm < 11.0)
fx = ((hl[sel, 0] + 180.0) / 360.0 * RW).astype(int) % RW
fy = np.clip(((90.0 - hl[sel, 1]) / 180.0 * RH).astype(int), 0, RH - 1)
faint = np.zeros((RH, RW), np.float64)
np.add.at(faint, (fy, fx), 10 ** (-0.4 * (hm[sel] - MAG_LIMIT)))
lat_c = 90.0 - (np.arange(RH) + 0.5) / RH * 180.0
faint /= np.maximum(np.cos(np.radians(lat_c)), 0.02)[:, None]       # per steradian


def sphere_blur(img, sigma_deg):
    """Gaussian of sigma_deg on the sphere, approximated on the equirect: vertical sigma constant, horizontal sigma
    grows as 1/cos(lat) (rows near the poles are averaged wide)."""
    sy = sigma_deg / 180.0 * img.shape[0]
    out = ndimage.gaussian_filter1d(img.astype(np.float64), sy, axis=0, mode='nearest')
    res = np.empty_like(out)
    for r in range(img.shape[0]):
        lat = 90.0 - (r + 0.5) / img.shape[0] * 180.0
        sx = min(sigma_deg / max(math.cos(math.radians(lat)), 1e-3) / 360.0 * img.shape[1], img.shape[1] / 3.0)
        res[r] = ndimage.gaussian_filter1d(out[r], sx, mode='wrap')
    return res


lv_soft = sphere_blur(levels, 3.0) / 5.0             # the wide glow: no edge anywhere
lv_mid = sphere_blur(levels, 1.0) / 5.0              # the star clouds and the rift
fa_grain = sphere_blur(faint, 0.25)                  # granular light of the unresolved stars
fa_grain /= np.percentile(fa_grain, 99.5)
fa_wide = sphere_blur(faint, 2.0); fa_wide /= np.percentile(fa_wide, 99.7)


def tone(x, k=2.4):
    return (1.0 - np.exp(-k * x)) / (1.0 - np.exp(-k))


band = np.clip(lv_soft * 2.5, 0, 1)
glow_eq = (0.33 * tone(lv_soft) + 0.44 * tone(lv_mid, 1.6) + 0.05 * np.clip(fa_wide, 0, 1.5)
           + 0.18 * np.clip(fa_grain, 0, 2.0) * (0.04 + 0.96 * band))
lv = lv_mid
# ---- 4. resample to the world equirect and colour -----------------------------------------------------------------
u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
az = (u - 0.5) * 2 * np.pi; el = (0.5 - v) * np.pi            # row 0 = el +90
AZ, EL = np.meshgrid(az, el)
Vu = np.stack([np.sin(AZ) * np.cos(EL), np.sin(EL), np.cos(AZ) * np.cos(EL)], -1)
Ve = unity_to_eq(Vu)
ra_w = np.degrees(np.arctan2(Ve[..., 1], Ve[..., 0])); dec_w = np.degrees(np.arcsin(np.clip(Ve[..., 2], -1, 1)))
px = ((((ra_w + 180.0) % 360.0) / 360.0) * RW - 0.5) % RW
py = np.clip((90.0 - dec_w) / 180.0 * RH - 0.5, 0, RH - 1)
g = ndimage.map_coordinates(glow_eq, [py, px], order=1, mode='grid-wrap')
g0 = np.percentile(g, 35.0)                                   # the sky away from the band: the star floor only
g = np.clip((g - g0) / (np.percentile(g, 99.5) - g0), 0, None)
g = np.where(g < 0.8, g, 0.8 + 0.2 * np.tanh((g - 0.8) / 0.2))      # soft knee: the brightest 0.5 % roll off to 1.0
gc_ang = np.degrees(np.arccos(np.clip(Vu @ np.array([g_w[0], g_w[2], g_w[1]]), -1, 1)))
warm = 0.75 * np.exp(-(gc_ang / 15.0) ** 2) * np.clip(g * 1.6, 0, 1)   # the bulge's warm dust: only where the band is bright, ~ +-15 deg
cdiff = hexlin(GLOW_DIFFUSE_FILL); cdust = hexlin(GLOW_DUST_FILL)
col = (1 - warm[..., None]) * cdiff + warm[..., None] * cdust
bulge = 1.0 + 0.35 * warm                                 # the centre is the brightest part of the band
glow = (g * bulge)[..., None] * col / bulge.max()
glow = glow.astype(np.float32)

os.makedirs(os.path.join(SKY, 'Textures'), exist_ok=True)
try:
    import OpenEXR, Imath
    hdr = OpenEXR.Header(W, H)
    hdr['compression'] = Imath.Compression(Imath.Compression.ZIP_COMPRESSION)
    hdr['channels'] = {c: Imath.Channel(Imath.PixelType(Imath.PixelType.HALF)) for c in 'RGB'}
    o = OpenEXR.OutputFile(os.path.join(SKY, 'Textures', 'StarSky_Glow_4096x2048.exr'), hdr)
    o.writePixels({c: glow[..., i].astype(np.float16).tobytes() for i, c in enumerate('RGB')})
    o.close()
except ImportError:
    raise SystemExit('pip install OpenEXR')

# ---- 5. json + previews ----------------------------------------------------------------------------------------
stats = dict(
    stars=len(rows), mag_limit=MAG_LIMIT,
    in_band_density_ratio=None,
)
b_gal = np.degrees(np.arcsin(np.clip(radec_vec(ra, dec) @ N_EQ, -1, 1)))
area_in = math.sin(math.radians(15)) ; area_out = 1 - area_in
stats['in_band_density_ratio'] = round(float(((np.abs(b_gal) < 15).sum() / area_in) / ((np.abs(b_gal) >= 15).sum() / area_out)), 2)
gc_u = eq_to_unity(G_EQ)
json.dump(dict(
    about='蓝白 · 星海的朝向与数据（Sky/Source~/make_starsky.py 生成）。Unity 世界坐标，方位 = 从 +Z 顺时针到 +X。',
    equatorial_to_enu=R.round(9).tolist(),
    enu_to_unity='(x, y, z)_ENU -> (x, z, y)_Unity',
    galactic_centre_unity=gc_u.round(6).tolist(), galactic_centre_az_el=[GC_AZ, GC_EL],
    north_galactic_pole_unity=eq_to_unity(N_EQ).round(6).tolist(),
    glow_texture='Textures/StarSky_Glow_4096x2048.exr', glow_mapping='u = 0.5 + atan2(V.x, V.z)/2pi, v = 0.5 + asin(V.y)/pi',
    glow_fill_max={'diffuse': GLOW_DIFFUSE_FILL, 'dust': GLOW_DUST_FILL},
    stars_csv='Data/StarPoints_BSC5.csv', **stats,
    sources={'stars': 'Yale Bright Star Catalogue 5th rev. ed. (Hoffleit & Warren 1991), NASA ADC, public domain; JSON github.com/brettonw/YaleBrightStarCatalog',
             'faint_stars': 'Hipparcos main catalogue (ESA 1997) via d3-celestial stars.14.json (BSD-3-Clause)',
             'milky_way_outline': 'Milky Way Outline Catalog, Jose R. Vieira (skymap.com), via d3-celestial mw.json (BSD-3-Clause)'},
), open(os.path.join(SKY, 'Data', 'StarSky.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(stats))

os.makedirs(os.path.join(SKY, 'Docs~'), exist_ok=True)


def to8(x):
    x = np.clip(x, 0, None)
    return (np.clip(np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055), 0, 1) * 255).astype(np.uint8)


prev = glow + hexlin('#0D0F23')                       # + the star floor
img = to8(prev)
im = Image.fromarray(img).resize((2048, 1024), Image.LANCZOS)
d = ImageDraw.Draw(im)
for i in range(len(rows)):
    x = (0.5 + math.degrees(math.atan2(dirs[i, 0], dirs[i, 2])) / 360.0) * 2048
    y = (0.5 - math.degrees(math.asin(dirs[i, 1])) / 180.0) * 1024
    r = max(0.6, 2.6 - 0.35 * vm[i])
    c = tuple(int(255 * min(1, cc ** (1 / 2.2))) for cc in cols[i] / cols[i].max())
    d.ellipse([x - r, y - r, x + r, y + r], fill=c)
for azl in range(-180, 181, 45):
    xx = (0.5 + azl / 360) * 2048
    d.line([xx, 506, xx, 518], fill=(255, 80, 80))
d.line([0, 512, 2048, 512], fill=(90, 90, 120))
im.save(os.path.join(SKY, 'Docs~', 'starsky_world_equirect.png'))
print('wrote', os.path.join(SKY, 'Docs~', 'starsky_world_equirect.png'))
