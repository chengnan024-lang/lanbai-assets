"""Compose the hero window's outer-surface normal map for the window preview, with the kit's own maths (v2):
static beads (RainBeads_Vertical) + two runner layers (GlassRunners_Flow + the v2 LanbaiRunners port: distance clock,
stopped drops become beads, channels refill by time since the head passed) + 'that one raindrop' (OneDrop head frame 0
at its 2 cm pause + its trail, and the strip it swept through the beads) - exactly Lanbai/BusGlass + Lanbai/OneDrop.
Pane coordinates = world (x along the bus, z up) in metres on the window plane; the map covers REGION.
usage: python3 glass_normals.py <outdir> [t]      (bpy only to write the EXR)"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))   # inside the kit: Tools~/src
from glass_ref import Glass, load

_H = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('RAIN_PREVIEW') or os.path.join(_H, '..', 'preview_cache' if os.path.basename(_H) == 'preview' else 'preview'), 'glassN')
os.makedirs(OUT, exist_ok=True)
T = float(sys.argv[2]) if len(sys.argv) > 2 else float(os.environ.get('TGLASS', '215.0'))
REGION = tuple(float(v) for v in os.environ.get('REGION', '-1.92,-1.28,1.88,2.36').split(','))   # x0, x1, z0, z1
PX = float(os.environ.get('GPX', '0.0001'))
DENS = float(os.environ.get('GDENS', '0.05'))
HERO = tuple(float(v) for v in os.environ.get('HERO', '-1.712,2.072').split(','))   # head anchor at the pause (x, z)
x0, x1, z0, z1 = REGION
NX, NY = int(round((x1 - x0) / PX)), int(round((z1 - z0) / PX))
G = Glass('Vertical')
xs = x0 + (np.arange(NX) + 0.5) * PX; zs = z0 + (np.arange(NY) + 0.5) * PX
hx, hz = HERO
top = hz + 0.028                                           # (head anchor = 8 + 20 mm below the top edge)
trail = load('OneDrop_Trail_128x1024.png')                 # rows: 0 = top of the decal
head = load('OneDrop_Head_Flip4x4_512.png')[0:128, 0:128]  # frame 0 = at rest
cl = (trail[int((0.008 + 0.020) / 0.096 * 1023), 64, 0] - 0.5) * 0.008   # path x offset at the pause (m)

su = np.zeros((NY, NX), np.float32); sv = np.zeros_like(su); cov = np.zeros_like(su)
B = 128
for j0 in range(0, NY, B):
    Z = zs[j0:j0 + B][:, None] * np.ones((1, NX)); X = np.ones((Z.shape[0], 1)) * xs[None, :]
    P = np.stack([X, Z], -1).astype(np.float32)
    # the hero drop's swept strip (LanbaiOneDropSwept): from its start down to 2.5 mm above its head, 2.2 mm half-width,
    # evaluated by G.slopes at each bead's centre (whole beads are taken)
    def swept(Q):
        za, zb = top - 0.008, hz + 0.0025
        t_ = np.clip((Q[..., 1] - za) / (zb - za), 0, 1)
        dd = np.hypot(Q[..., 0] - (hx - cl), Q[..., 1] - (za + (zb - za) * t_))
        w_ = 0.0022
        ec = np.clip((w_ - dd) / (0.4 * w_), 0, 1)
        return ec * ec * (3 - 2 * ec)
    a, b, th, hh = G.slopes(P, T, amount=1.0, flow_dir=(0.0, -1.0), speed=0.03, density=DENS, size=0.0030, extra_clear=swept)
    su[j0:j0 + B] = a; sv[j0:j0 + B] = b
    cov[j0:j0 + B] = np.clip(np.maximum(th / 0.00015, hh / 0.00015), 0, 1)
    print('band', j0, '/', NY, flush=True)

# ---- the one drop: trail (residue pearls) above it, head at rest - vectorised (decal 12 x 96 mm)
dx_ = xs[None, :] - (hx - cl); dz_ = top - zs[:, None]              # m from the decal centre line, below its top
inside = (np.abs(dx_) < 0.006) & (dz_ >= 0) & (dz_ < 0.096)
ty = np.clip((dz_ / 0.096 * 1024).astype(int), 0, 1023); tx = np.clip(((dx_ + 0.006) / 0.012 * 128).astype(int), 0, 127)
tyb = np.broadcast_to(ty, inside.shape); txb = np.broadcast_to(tx, inside.shape)
g = trail[tyb, txb, 1]
gxp = trail[tyb, np.minimum(127, txb + 1), 1]; gxm = trail[tyb, np.maximum(0, txb - 1), 1]
gyp = trail[np.minimum(1023, tyb + 1), txb, 1]; gym = trail[np.maximum(0, tyb - 1), txb, 1]
passed = inside & (np.broadcast_to(dz_, inside.shape) >= 0.0075) & (np.broadcast_to(dz_, inside.shape) <= 0.008 + 0.020 - 0.0025) & (g > 0.01)
gx = (gxp - gxm) * 0.00025 / (2 * 0.012 / 128); gy = -(gyp - gym) * 0.00025 / (2 * 0.096 / 1024)
su = np.where(passed, gx, su); sv = np.where(passed, gy, sv); cov = np.where(passed, np.maximum(cov, np.minimum(1, g * 6)), cov)
fx = (xs[None, :] - (hx - 0.006)) / 0.012; fy = (zs[:, None] - (hz - 0.40 * 0.012)) / 0.012
inh = (fx >= 0) & (fx < 1) & (fy >= 0) & (fy < 1)
hi = np.clip((fx * 128).astype(int), 0, 127); hj = np.clip(127 - (fy * 128).astype(int), 0, 127)
h4 = head[np.broadcast_to(hj, inh.shape), np.broadcast_to(hi, inh.shape)]
m = inh & (h4[..., 3] > 0.02)
n2 = h4[..., :2] * 2 - 1; nz = np.sqrt(np.maximum(1e-4, 1 - (n2 ** 2).sum(-1)))
w = np.minimum(1, h4[..., 3] * 1.5)
su = np.where(m, su * (1 - w) + (-n2[..., 0] / nz) * w, su)
sv = np.where(m, sv * (1 - w) + (-n2[..., 1] / nz) * w, sv)
cov = np.where(m, np.maximum(cov, h4[..., 3]), cov)

n = np.stack([-su, -sv, np.ones_like(su)], -1)
n /= np.linalg.norm(n, axis=-1, keepdims=True)
import bpy
im = bpy.data.images.new('glassN', NX, NY, alpha=False, float_buffer=True)
im.colorspace_settings.name = 'Non-Color'          # else Image.save() writes the Standard view transform into the EXR
rgba = np.concatenate([np.clip(n * 0.5 + 0.5, 0, 1), np.ones((NY, NX, 1))], -1).astype(np.float32)
im.pixels.foreach_set(rgba.ravel())                # Blender rows bottom-up = our z-up rows
im.filepath_raw = os.path.join(OUT, 'glass_normal.exr'); im.file_format = 'OPEN_EXR'; im.save()
chk = bpy.data.images.load(os.path.join(OUT, 'glass_normal.exr'), check_existing=False); chk.colorspace_settings.name = 'Non-Color'
med = float(np.median(np.array(chk.pixels[:], np.float32).reshape(-1, 4)[::97, 0]))
assert abs(med - 0.5) < 0.01, 'normal map written with a colour transform: median R %.4f' % med
sh = np.clip((n * np.array([-0.4, 0.5, 0.77])).sum(-1), 0, 1)
Image.fromarray((sh[::-1] * 255).astype(np.uint8)).resize((NX // 4, NY // 4)).save(os.path.join(OUT, 'look_glass_normals.png'))
json.dump(dict(region=REGION, px=PX, t=T, density=DENS, hero=HERO, nx=NX, ny=NY), open(os.path.join(OUT, 'glass_normal.json'), 'w'))
print('pane', NX, NY)
