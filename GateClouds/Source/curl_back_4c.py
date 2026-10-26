"""蓝白 / Lanbai · gate · round 10 C': look back past U9 in the 4c fog: the kept hands as silhouettes (fog only), fog density 0.0006 -> 0.0035 over
SS((t - U9) / 2) (LanbaiInsideDriver.WriteFog), background = the band; cap 'hold' as LanbaiGateDriver (_FogHold).
Prints the hands' median contrast against the background, capped (0.7) and not.

  python3 curl_back_4c.py 180,180.5,... <w> [outdir]   -> c4_{cap,nocap}_<t>.png
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seam_ref as S, deck_ref as D
from PIL import Image, ImageDraw
U9 = 179.55
S.TEX = S.density_tex()
def SS(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/claude-0/cb4'
os.makedirs(out, exist_ok=True)
ts = [float(x) for x in sys.argv[1].split(',')]
w = int(sys.argv[2]); h = int(round(w * 9 / 16))
for t in ts:
    cam = dict(t=t, pos=[0.55, 1.7, 2.05], look_yaw_deg=180.0, look_pitch_deg=0.0, hfov_deg=90.0)
    eye = np.array(cam['pos'], float)
    tear = D.gate_origin(t) + np.array([0.0, -150.0 + 0.4 * 640.0, 19.0])
    V, _ = D.camera_rays(cam, w, h); Vf = V.reshape(-1, 3)
    bg = D.band(Vf, eye, tear) + D.moon_air(Vf)
    arms = S.arm_meshes(t, True)
    dens = 0.0006 + (0.0035 - 0.0006) * SS((t - U9) / 2.0)
    sil = SS((t - (U9 - 0.05)) / 0.3)
    rv = 1.0 - min(max((t - 184.0) / 0.5, 0.0), 1.0)
    res = {}
    if arms:
        P, N, hit = S.render_arm_passes(arms, cam, w, h)
        hf = hit.reshape(-1); ia = np.nonzero(hf)[0]
        dist = np.linalg.norm(P.reshape(-1, 3)[ia] - eye, axis=1)
        c = S.Ctx(t, eye)
        acol, keep, _ = S.shade_arm(P.reshape(-1, 3)[ia], N.reshape(-1, 3)[ia], c, tear, True)
    for name, cap in (('nocap', 1.0), ('cap', 0.7)):
        col = bg.copy()
        if arms:
            f = 1.0 - np.exp(-dist * dens)
            hold = (1.0 - sil) + cap * sil                                  # lerp(1, cap, sil)
            hold = hold + (1.0 - hold) * SS((t - (184.5 - 0.5)) / 0.5)      # let go over the fade
            f = np.minimum(f, hold)
            f = 1.0 - (1.0 - f) * rv
            surf = acol * (1.0 - sil)
            col[ia] = surf * (1 - f)[:, None] + bg[ia] * f[:, None]
        img = D.grade(col.reshape(h, w, 3)).astype(np.uint8)
        L = img.astype(np.float32) @ [0.2126, 0.7152, 0.0722]; Lb = D.grade(bg.reshape(h, w, 3)).astype(np.float32) @ [0.2126, 0.7152, 0.0722]
        con = np.median(((Lb - L) / np.maximum(Lb, 1)).reshape(-1)[ia]) * 100 if arms else 0
        im = Image.fromarray(img); ImageDraw.Draw(im).text((6, 4), 't %.2f look back, 4c fog %.4f, %s  hands %.0f %% contrast' % (t, dens, 'cap 0.7' if cap < 1 else 'no cap', con), fill=(255, 255, 255))
        im.save(os.path.join(out, 'c4_%s_%.2f.png' % (name, t)))
        print('t %.2f %s dens %.4f sil %.2f rv %.2f hands median contrast %.0f %%' % (t, name, dens, sil, rv, con), flush=True)
