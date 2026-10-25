# -*- coding: utf-8 -*-
"""（第 8 幕：从 Act06_Dawn/Tools~ 拷来，加了覆盖全局量：8-ii 的日线 `_Udon_SunDisc.z` 10°）
天空会话的正式预设（Sky/SkyPresets），用它自己的 CPU 版 Lanbai/Sky（真的 LanbaiSky.cginc + LanbaiSkyLayers.cginc，
slangpy）渲成一张等距柱状图（Unity 世界方向，列 u = az/360 + 0.5，行 v = (90 − el)/180），给参考渲染当天、当世界光。
python sky_equirect.py dusk_8ii [W] [--line 10] -> $LB_WORK/sky_<preset>[_line10]_<W>.hdr"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Source'))
import lb_common as C  # noqa: E402

WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')


def _lerp_dict(a, b, w):
    """the preset's ApplyBlend in parameter space: numbers / vectors interpolated, a name on one side only is kept"""
    out = {}
    for k in set(a) | set(b):
        if k in a and k in b:
            va, vb = np.asarray(a[k], float), np.asarray(b[k], float)
            out[k] = (va * (1 - w) + vb * w).tolist() if va.shape == vb.shape else (b[k] if w >= 0.5 else a[k])
        else:
            out[k] = a[k] if k in a else b[k]
    return out


def render_blend(na, nb, w, W=1024, over=None, tag=''):
    """a.ApplyBlend(b, w): material and globals interpolated, the cube stays a's (blue_hour has none: its
    _Udon_SkyBlend.y = 1 = procedural takes over as w -> 1), as LanbaiSkyPreset.ApplyBlend does"""
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'Sky', 'Tools~', 'render'))
    try:
        import make_presets as MP
        import sky_cpu as S
    finally:
        os.chdir(cwd)
    pa, pb = MP.P[na], MP.P[nb]
    S.renderer().tex.clear()
    S.set_cube('_CubeA', S.load_hdr(pa['hdri_file']))
    ga, gb = dict(pa['globals']), dict(pb['globals'])
    if pa.get('fog_from_sky'):
        ga.update(MP.fog_group(pa))
    if pb.get('fog_from_sky'):
        gb.update(MP.fog_group(pb))
    ga.setdefault('_Udon_SkyBlend', [0.0, 0.0, 0.0, 1.0])
    globs = _lerp_dict(ga, gb, w)
    if over:
        globs.update(over)
    mat = _lerp_dict(pa['material'], pb['material'], w)
    H = W // 2
    d = C.equirect_dirs(H, W, 0.0).reshape(-1, 3).astype(np.float32)
    out = np.zeros((d.shape[0], 3), np.float32)
    n = 1 << 18
    for i in range(0, d.shape[0], n):
        out[i:i + n] = np.asarray(S.render(d[i:i + n], mat, globs)).reshape(-1, 3)
    img = out.reshape(H, W, 3)
    path = os.path.join(WORK, f'sky_{na}_to_{nb}_{w:.2f}{tag}_{W}.hdr')
    C.write_hdr(path, img)
    return path, img


def render(name, W=1024, over=None, tag=''):
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'Sky', 'Tools~', 'render'))
    try:
        import make_presets as MP
        import sky_cpu as S
    finally:
        os.chdir(cwd)
    p = MP.P[name]
    S.renderer().tex.clear()
    if p.get('hdri_file'):
        S.set_cube('_CubeA', S.load_hdr(p['hdri_file']))
    if p.get('glow'):
        S.set_tex('_GlowTex', S.load_glow(1))
    globs = dict(p['globals'])
    if p.get('fog_from_sky'):
        globs.update(MP.fog_group(p))
    if over:
        globs.update(over)
    H = W // 2
    d = C.equirect_dirs(H, W, 0.0).reshape(-1, 3).astype(np.float32)
    out = np.zeros((d.shape[0], 3), np.float32)
    n = 1 << 18
    for i in range(0, d.shape[0], n):
        out[i:i + n] = np.asarray(S.render(d[i:i + n], p['material'], globs)).reshape(-1, 3)
    img = out.reshape(H, W, 3)
    path = os.path.join(WORK, f'sky_{name}{tag}_{W}.hdr')
    os.makedirs(WORK, exist_ok=True)
    C.write_hdr(path, img)
    return path, img, p


def render_at(t, W=1024):
    """the sky at time t exactly as the act 8 driver writes it: the sky session's own act8_sky_frames.state(t) (the real
    LanbaiSkyPreset.ApplyBlend, TS.blend, + this driver's sun line / sun direction; pkg/sky d69940e). -> sky_at<t>_<W>.hdr"""
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'Sky', 'Tools~', 'render'))
    try:
        import make_presets as MP
        import sky_cpu as S
        import test_sequence as TS
        import act8_sky_frames as AF
    finally:
        os.chdir(cwd)
    P, _ = TS.load()
    S.renderer().tex.clear()
    S.set_cube('_CubeA', S.load_hdr(MP.P['dusk_8i']['hdri_file']))
    S.set_tex('_GlowTex', S.load_glow(4))
    g, _ = AF.state(t, P)
    H = W // 2
    d = C.equirect_dirs(H, W, 0.0).reshape(-1, 3).astype(np.float32)
    out = np.zeros((d.shape[0], 3), np.float32)
    n = 1 << 18
    for i in range(0, d.shape[0], n):
        out[i:i + n] = np.asarray(S.render(d[i:i + n], {}, g)).reshape(-1, 3)
    path = os.path.join(WORK, f'sky_at{t:.2f}_{W}.hdr')
    os.makedirs(WORK, exist_ok=True)
    C.write_hdr(path, out.reshape(H, W, 3))
    return path


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('W', nargs='?', type=int, default=1024)
    ap.add_argument('--line', type=float, default=None)
    ap.add_argument('--blend', nargs=2, default=None, metavar=('TO', 'W'))
    ap.add_argument('--at', type=float, nargs='+', default=None)
    a = ap.parse_args()
    if a.at:
        for t in a.at:
            print(render_at(t, a.W), flush=True)
        sys.exit(0)
    if a.blend:
        over = {'_Udon_SunDisc': [1.0 - float(a.blend[1]), 0.265, a.line * (1.0 - float(a.blend[1])), 1.0]} if a.line else None
        print(render_blend(a.name, a.blend[0], float(a.blend[1]), a.W, over)[0])
        sys.exit(0)
    over, tag = None, ''
    if a.line is not None:
        over = {'_Udon_SunDisc': [1.0, 0.265, a.line, 1.0]}
        tag = '_line%g' % a.line
    path, img, p = render(a.name, a.W, over, tag)
    print(path, img.shape, float(img.max()), 'sunAz', p.get('sunAz'))
