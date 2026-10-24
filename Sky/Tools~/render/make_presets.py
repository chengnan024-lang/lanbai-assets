"""蓝白 · 每一幕的天空预设（Sky/SkyPresets.json）+ 预览图与量数（Sky/Docs~/presets/）。
Run: ~/bpy/bin/python -I make_presets.py            (after fit_hdri_tints.py dawn / dusk)

One preset = the Lanbai/Sky material values + the fog / sky globals the act's driver writes. The fog's horizon
colours of the HDRI acts are SAMPLED from this very sky at elevation 1 deg (so the fog meets the sky by construction),
the procedural acts use LanbaiHorizon directly (the sky and the fog are the same function).
All colours are linear; 'fills' quoted in comments are calib_engine.json values for the act's profile.
Every preview runs the real LanbaiSky.cginc + LanbaiSkyLayers.cginc on the CPU and grades with the Grading kit's
engine (grades_engine.json) + bloom. HDRIs: the local's 1024 x 512 Poly Haven files (the real ones are 16K, so the
previews are soft; colours and layout are what to compare)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_cpu as S, grade as G
from shader_cpu import camera_dirs
from fit_hdri_tints import inv_screen

REPO = G.REPO
OUT = os.path.join(REPO, 'Sky', 'Docs~', 'presets'); os.makedirs(OUT, exist_ok=True)
HDRI = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')
F = G.fill


def v4(c, a=1.0):
    c = list(map(float, c))
    return c + [a] if len(c) == 3 else c


def dir_az_el(az, el):
    a, e = np.radians(az), np.radians(el)
    return [float(np.sin(a) * np.cos(e)), float(np.sin(e)), float(np.cos(a) * np.cos(e))]


fit = {k: json.load(open(os.path.join(REPO, 'Sky', 'Data', 'fit_%s.json' % k))) for k in ('dawn', 'dusk')}


def tints(name):
    t = fit[name]['tints']
    return {k: v4(v) if len(v) == 3 else list(map(float, v)) for k, v in t.items()}


# ---------------------------------------------------------------------------------------------------------------
# presets: material (Lanbai/Sky properties), globals (written by the act driver), meta
# the rose -> indigo transitions keep C* <= 8 in h 285-330 (director 10-23, D-17's reasoning; sea's final review measured
# #A69AA4 h 330 in the act-8 ceiling melt): the guard pulls R below 0.55 G wherever B > G
LAV_GUARD = [1.0, 0.75, 0.95, -1.0]   # two-sided: strong blues R <= 0.55 G (stay blue); the rose -> blue transition (B / G 0.95..1.25, R / G > 0.6..0.75) toward a cool grey (no teal)
SUN6 = dir_az_el(30.0, 5.8)      # dawn: D-12 az +30 (in the bus door); el = the HDRI sun 5.8 (D-12: +6); the real-time light aligns to it
SUN8 = dir_az_el(0.0, 0.5)       # dusk: azimuth 0, elevation +0.5 deg, in the windscreen (bible §6·8)
P = {}

P['overcast_rain_night'] = dict(acts='1 · 2（×0.6）· 11（= 2）· 12 的开头', profile='S1',
    cubeA='Sky_Overcast_Night_2048x1024', hdri_file=os.path.join(REPO, 'Sky', 'Textures', 'Sky_Overcast_Night_2048x1024.hdr'),
    material=dict(_RotationA=0.0, _ExposureA=0.0, _SunGain=0.0, _NadirColor=v4(F('#161B27'), 0.0), _BelowShape=[-30, 0.8, 0.6, 2.0]),
    globals=dict(_Udon_HorizonColor=v4(F('#161B27'), 2.0), _Udon_FogBandColor=v4(F('#161B27')), _Udon_ZenithColor=v4(F('#09080D')),
                 _Udon_NadirColor=v4(F('#161B27')), _Udon_FogShape=[0, 50, 0.6, 0], _Udon_FogBelow=[-30, 0, 1, 0],
                 _Udon_FogDensity=0.009),
    notes='天顶 #070B14（填 #09080D）、雾 = 地平线 #121A28（填 #161B27）。第 2 / 11 幕：_ExposureA −0.7 EV（S2 天 #05080F 填 #060405），雾填 #0D0F15，密度 0.008。偏航只在这种没有特征的天下允许。')

P['overcast_rain_night_town'] = dict(acts='1（站牌：朝镇方向的地平线是钠光照亮的云底）', profile='S1',
    cubeA='Sky_Overcast_Night_TownGlow_2048x1024', hdri_file=os.path.join(REPO, 'Sky', 'Textures', 'Sky_Overcast_Night_TownGlow_2048x1024.hdr'),
    material=dict(_RotationA=-70.0, _ExposureA=0.0, _SunGain=0.0, _NadirColor=v4(F('#161B27'), 0.0), _BelowShape=[-30, 0.8, 0.6, 2.0]),
    globals=dict(_Udon_HorizonColor=v4(F('#161B27'), 2.0), _Udon_FogBandColor=v4(F('#1E1C22')), _Udon_FogBandDir=v4(dir_az_el(-70, 0), 0), _Udon_FogBandWidth=60.0,
                 _Udon_ZenithColor=v4(F('#09080D')), _Udon_NadirColor=v4(F('#161B27')), _Udon_FogShape=[0, 50, 0.6, 0], _Udon_FogBelow=[-30, 0, 1, 0],
                 _Udon_FogDensity=0.009),
    notes='= 阴云夜 + 镇子方向钠光照亮的云底 #241E22（填 #2A1F1E）。_RotationA = 镇子的方位（这里按 −70° 放，本地按车站布局改；雾的朝向 _Udon_FogBandDir 跟着改）。')

# D-06: acts 3 and 4 share the star set and the gain; only stars brighter than magnitude 3; L* <= 12 at 1080p
# (check_stars.py --solve gives the largest passing gain; check_stars.py checks it)
STAR_GAIN_MOON = 0.015   # check_stars.py --solve, 10-23: the largest gain with every star <= 12 L* above its sky
P['moon_night'] = dict(acts='3（离地、月下云海）', profile='S3', cubeA=None,
    material=dict(_ProcWeight=1.0, _SunGain=0.0, _MoonGain=1.0, _MoonRadius=0.6, _MoonDir=v4(dir_az_el(-12, 8), 0),
                  _MoonColor=v4(F('#F0F5FF @ +2.17')), _MoonGlow=[20.0, 1.5, 13.2, 0.43], _MoonGlowColor=[0.19, 0.21, 0.35, 1.0]),
    globals=dict(_Udon_HorizonColor=v4(F('#242A40'), 2.0), _Udon_FogBandColor=v4(F('#2E3753')), _Udon_FogBandDir=v4(dir_az_el(-12, 0), 0),
                 _Udon_FogBandWidth=120.0, _Udon_ZenithColor=v4(F('#151928')), _Udon_NadirColor=v4(F('#1A2034')), _Udon_FogShape=[0, 40, 1.5, 0.0], _Udon_FogBelow=[-40, 0, 1.0, 0],
                 _Udon_MoonDir=v4(dir_az_el(-12, 8), 1), _Udon_MoonDisc=[1.0, 0.6, 0, 1], _Udon_StarGain=[STAR_GAIN_MOON, 1.0, 1, 1], _Udon_StarShape=[3.0, 0.0, 0.0, 1.0], _Udon_GalaxyGain=[0.0, 0, 0, 1],
                 _Udon_FogDensity=0.00035),
    notes='天顶 #08101F（填 #151928）、背月地平线 = 云上雾色 #111B30（填 #242A40）、月面 #EAEEF4（填 #F0F5FF @ +1.67）、月晕按 calib S3 拟合（6° #5A6A88、10° #26344F）。月在 −12° / +8°、直径 1.2°。破云（U6k）起有星（D-06）：只留 3 等以上的亮星（_Udon_StarShape.x），1080p 下最亮的星 L* ≤ 12（check_stars.py），没有银河；第 4 幕用同一套星、同一个增益。')

P['dawn'] = dict(acts='6（晨，F0 → F2h）', profile='S6', sunAz=30.0, cubeA='syferfontein_6d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_6d_clear_puresky_1k.hdr'),
    material=dict(_RotationA=fit['dawn']['rotation'], _ExposureA=0.0, _ClampA=16.0, **tints('dawn'),
                  _SunDir=v4(SUN6, 0), _SunColor=v4(F('#FFCE9E @ +3.05')), _SunShape=[0.265, 0.04, 0.55, 0], _SunGain=1.0,
                  _SunGlow=[0.35, 1.6, 0.0, 0.0], _SunGlowColor=v4(F('#FFCE9E')),   # D-18: 0.53 deg disc, the rest of the sun's weight in a tight aureole (+ bloom)
                  _Band1Color=v4(F('#B8C4F7'), 0.3), _Band1Shape=[2.0, 2.5, 180, 55], _Band1Gain=0.6,
                  _Band2Color=v4(F('#FFCFCB @ +0.61'), 0.3), _Band2Shape=[10.0, 4.0, 180, 50], _Band2Gain=0.3,
                  _NadirColor=v4(F('#6F8FA8'), 0.5), _BelowShape=[-75, 1.0, 0.6, 2.0], _PurpleGuard=LAV_GUARD,
                  _SunRemove=[10.0, 0.0, 0.15, 0.0]),
    globals=dict(_Udon_SunDir=v4(SUN6, 1), _Udon_SunDisc=[1.0, 0.265, 0, 1], _Udon_FogDensity=0.00012),
    fog_from_sky=dict(near_az=30.0, width=70.0, zen_el=60.0, nadir=F('#6F8FA8')),
    notes='天顶 #3E64A6、背日 45° #AFC4E0、日侧地平线 #F2C79A、地影带 #8C98B8 + 很淡的金星带 #CFB7B7（HDRI 里没有，由两条地平线带给）、日盘直径 0.53°（D-18）#FFF3DE（填 #FFCE9E @ +2.55）+ 小光晕；HDRI 自己的日斑由 _SunRemove 软封顶。太阳 方位 +30°（D-12，车门里）、仰角 5.8°（HDRI 的太阳）。')

dusk_common = dict(_RotationA=fit['dusk']['rotation'], _ExposureA=0.0, _ClampA=16.0, **tints('dusk'),
                   _SunDir=v4(SUN8, 0), _SunColor=v4(F('#FF9167 @ +2.74')), _SunShape=[0.265, 0.04, 0.4, 0], _SunGain=1.0,
                   _SunGlow=[0.25, 0.9, 0.06, 0.12], _SunGlowColor=v4(F('#FF855C')),
                   _Band2Color=v4(F('#FF9396 @ +0.92'), 0.25), _Band2Shape=[4.0, 3.0, 180, 55], _Band2Gain=0.6,
                   _NadirColor=v4(F('#3B4A78'), 0.6), _BelowShape=[-60, 0.7, 0.6, 0.8], _PurpleGuard=LAV_GUARD,
                   _OtherGain=0.82, _OtherTint=[0.92, 0.95, 1.05, 0.85], _OtherSeam=1.0)   # .a: the lower half darkens to the nadir (art r0 #1)
P['dusk_8i'] = dict(acts='8-i（出海 → F10e）', profile='S8', sunAz=0.0, cubeA='syferfontein_0d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_0d_clear_puresky_1k.hdr'),
    material=dict(dusk_common, _OtherSky=0.0, _BelowMirror=1.0, _BelowShape=[-45, 1.0, 0.6, 2.0], _NadirColor=v4(F('#3B4A78'), 0.0)),   # the sky continues below (mirrored elevation, log-darkened to the nadir): no 'ground' under the sunset (art r0 #3, r2 #1)
    globals=dict(_Udon_SunDir=v4(SUN8, 1), _Udon_SunDisc=[1.0, 0.265, 0, 1], _Udon_SkyFx=[0, 0, 0, 1], _Udon_FogDensity=0.00015),
    fog_from_sky=dict(near_az=0.0, width=80.0, zen_el=60.0, nadir=F('#3B4A78')),
    notes='日带 #FFB070、玫瑰带 #E7A0A0（填 #FF9396 @ +0.92）、中天 #808AB2、天顶 #3D4A80、日盘 #FFE2B0（填 #FF9167 @ +2.74）、天缝 #F2A56B（日晕）。太阳 方位 0°、仰角 +0.5°。紫护栏把 HDRI 背日的藍紫在 S8 的暖调色下拉回靛灰。')
P['dusk_8ii'] = dict(blend_skip=['_Udon_SunDisc'],   # F12 -> 8b: the clouds' driver writes the sun line (one writer, tech r2 #2b)
    acts='8-ii（另一片天，F10e → F12）', profile='S8', sunAz=0.0, cubeA='syferfontein_0d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_0d_clear_puresky_1k.hdr'),
    material=dict(dusk_common, _OtherSky=1.0),
    globals=dict(_Udon_SunDir=v4(SUN8, 1), _Udon_SunDisc=[1.0, 0.265, 0, 1], _Udon_SkyFx=[1.0, 0, 0, 1], _Udon_FogDensity=0.00025),
    fog_from_sky=dict(near_az=0.0, width=80.0, zen_el=60.0, nadir=F('#3B4A78')),
    notes='_OtherSky 0 → 1（956.36 → 964.36，8 秒 smoothstep）：下半球按 (−x, −y, z) 取样，×0.82、染 (0.92, 0.95, 1.05)，1° 软接缝；两个太阳在接缝上熔成一条线。F12 起日线：_Udon_SunDisc.z（线的半长）10° → 0、增益 → 0（987.06 → 993.06）。')

bh_zen = inv_screen('#16223F', 'S8b')
P['blue_hour'] = dict(acts='8b（蓝时，993.06 → 1001.21）+ 第 9 幕同一个材质', profile='S8b', cubeA=None, glow=True,
    material=dict(_ProcWeight=1.0, _SunGain=0.0, _SunDir=v4(SUN8, 0), _Band1Color=v4(F('#3F5790'), 0.0), _Band1Shape=[14.0, -10.0, 0, 110], _Band1Gain=0.85,
                  _NightMaskDir=v4(dir_az_el(0, 0), 0), _NightMaskShape=[40, 45, 6, 22], _NightColor=v4(F('#050000')),
                  _StarFloorAdd=v4(np.maximum(F('#0D0F23') - F('#050000'), 0)), _GalaxyGain=0.0, _PurpleGuard=LAV_GUARD),
    globals=dict(_Udon_SunDir=v4(SUN8, 1), _Udon_HorizonColor=v4(F('#8093C2') * 0.80, 2.0), _Udon_FogBandColor=v4(F('#8093C2')), _Udon_FogBandDir=v4(dir_az_el(0, 0), 0),
                 _Udon_FogBandWidth=90.0, _Udon_ZenithColor=v4(bh_zen), _Udon_NadirColor=v4(F('#1A2A4E') * 1.3),
                 _Udon_FogShape=[1.0, 90.0, 0.8, 0], _Udon_FogBelow=[-60, 0, 1.0, 0], _Udon_SkyBlend=[0, 1, 0, 1], _Udon_SkyFx=[0, 0.85, 0, 1],
                 _Udon_FogDensity=0.0),
    notes='天缝 / 地平线 #6F86B0（填 #8093C2）、最纯的蓝带 #2E4F8A（填 #3F5790）、天顶 #16223F、另一片天的天底 #1A2A4E。程序化（LanbaiHorizon 模型 B + 地平线带 1），上下对称。987.06 → 993.06 由暮的立方图 6 秒过渡到这里（_Udon_SkyBlend.y 0 → 1，与日线收缩同步）。1001.21 → 1009.21：_Udon_SkyBlend.z 0 → 1（夜的定向遮罩：前方 ±40° 的地平线带最后暗）。')

night = F('#050000'); floor = F('#0D0F23')   # (star_sea = the end state of the blue_hour material: night 1, glow 1)
P['star_sea'] = dict(acts='9（星海，F13 起）', profile='S9a', cubeA=None, glow=True,
    material=dict(_ProcWeight=1.0, _NightBlend=1.0, _NightColor=v4(night), _StarFloorAdd=v4(np.maximum(floor - night, 0)),
                  _GalaxyGain=1.0, _SunGain=0.0),
    # the act-9 driver owns the stars and the galaxy (x = 0 until F13 / the ignition): the preset writes them OFF;
    # the preview sheet shows the lit state (preview_globals)
    preview_globals=dict(_Udon_GalaxyGain=[1.0, 0, 0, 1], _Udon_StarGain=[1.0, 4.0, 50, 1]),
    globals=dict(_Udon_SkyBlend=[0, 1, 1, 1], _Udon_GalaxyGain=[0.0, 0, 0, 1], _Udon_StarGain=[0.0, 4.0, 50, 1], _Udon_StarShape=[6.5, 0.0, 0.0, 1.0],
                 _Udon_HorizonColor=v4(floor, 2.0), _Udon_FogBandColor=v4(floor), _Udon_ZenithColor=v4(floor), _Udon_NadirColor=v4(floor),
                 _Udon_FogDensity=0.0),
    notes='点燃前的黑 #04060E（填 #050000，S9a）；F13 一帧所有星点出现（_Udon_StarGain.x 0 → 1）；银河辉光与星空底 #08112A（填 #0D0F23）走 g(t)，4.2 秒涨满（_Udon_GalaxyGain.x）；之后 x^2.5 曲线上 1.0 → 1.8、最亮 200 颗 ×4 → ×8。雾关。_Udon_ZenithColor = 当前的星空底（镜子用）。')


# ---------------------------------------------------------------------------------------------------------------
def fog_group(p):
    """Sample this sky at el 1 deg around the horizon and at el zen_el: near / far horizon colours, zenith; model B."""
    f = p['fog_from_sky']
    mat = dict(p['material'])
    mat['_SunGain'] = 0.0
    az = np.arange(-180, 180, 5.0)
    d = np.array([dir_az_el(a, 1.0) for a in az], np.float32)
    c = S.render(d, mat)
    rel = np.abs((az - f['near_az'] + 180) % 360 - 180)
    near = c[rel <= 15].mean(0); far = c[rel >= 150].mean(0)
    dz = np.array([dir_az_el(a, f['zen_el']) for a in az], np.float32)
    zen = S.render(dz, mat).mean(0)
    sundir = dir_az_el(f['near_az'], 0.0)
    return dict(_Udon_HorizonColor=v4(far, 2.0), _Udon_FogBandColor=v4(near), _Udon_FogBandDir=v4(sundir, 0),
                _Udon_FogBandWidth=float(f['width']), _Udon_ZenithColor=v4(zen), _Udon_NadirColor=v4(f['nadir']),
                _Udon_FogShape=[1.0, float(f['zen_el']), 0.7, 0], _Udon_FogBelow=[-35, 0, 0.8, 0])


VIEWS = [('前方', 0, 0), ('车门 +45°', 45, 0), ('天窗（仰 70°）', 20, 70), ('背后', 180, 8), ('左 −90°', -90, 5), ('向下 −35°', 0, -35)]
FONT = None
for fp in ('/home/user/lanbai-assets/Fonts/SourceHanSansSC/SourceHanSansSC-Regular.otf',):
    if os.path.exists(fp):
        FONT = fp


def font(px):
    for c in ('Fonts/Originals~/SourceHanSerifCN-Regular.otf', 'Fonts/Originals~/SourceHanSansCN-Heavy.otf'):
        try:
            return ImageFont.truetype(os.path.join(REPO, c), px)
        except Exception:
            pass
    return ImageFont.load_default()


def grad_codes(c, d, masks):
    """|neighbour difference| of display luminance (0..255 codes) per pixel of a 480-wide 90-degree tile; pixels
    within the masks (intended edges: the sun and moon discs) left out"""
    L = c @ np.array([0.2126, 0.7152, 0.0722])
    g = np.zeros_like(L)
    g[:, :-1] = np.maximum(g[:, :-1], np.abs(np.diff(L, axis=1)))
    g[:-1, :] = np.maximum(g[:-1, :], np.abs(np.diff(L, axis=0)))
    keep = np.ones(L.shape, bool)
    dd = d.reshape(L.shape + (3,))
    for axis, deg in masks:
        keep &= np.degrees(np.arccos(np.clip(dd @ axis, -1, 1))) > deg
    return g[keep]


GRAD_REF = {}


def grad_reference():
    """director r2 #2: no hard-edged shapes. Reference = the raw dawn / dusk HDRIs (no tints, no bands, no sun disc,
    graded S6 / S8) in the six views: their p99.9 neighbour gradient. A preset's p99.9 must not exceed it; its max
    may not exceed the HDRIs' max."""
    if GRAD_REF:
        return GRAD_REF
    allg = []
    for nm, prof in (('dawn', 'S6'), ('dusk_8i', 'S8')):
        p = P[nm]
        S.renderer().tex.clear(); S.set_cube('_CubeA', S.load_hdr(p['hdri_file']))
        mat = dict(_RotationA=p['material']['_RotationA'], _SunGain=0.0, _HorizonLift=0.0, _BelowShape=[-35, 0.0, 0.0, 0.0])
        for _, yaw, pitch in VIEWS:
            d = camera_dirs(480, 270, 90, yaw, pitch).astype(np.float32)
            c = np.clip(G.grade(S.render(d, mat).reshape(270, 480, 3), prof), 0, 255)
            sun = np.array(p['material']['_SunDir'][:3]); sun /= np.linalg.norm(sun)
            allg.append(grad_codes(c, d, [(sun, 8.0)]))
    a = np.concatenate(allg)
    GRAD_REF.update(p999=float(np.percentile(a, 99.9)), max=float(a.max()))
    S.renderer().tex.clear()
    print('gradient reference (raw HDRIs): p99.9 %.2f  max %.2f codes/px' % (GRAD_REF['p999'], GRAD_REF['max']))
    return GRAD_REF


def render_sheet(name, p, out_json):
    S.renderer().tex.clear()
    if p.get('hdri_file'):
        S.set_cube('_CubeA', S.load_hdr(p['hdri_file']))
    if p.get('glow'):
        S.set_tex('_GlowTex', S.load_glow(1))
    if p['material'].get('_MoonGain', 0) > 0:
        from PIL import Image as _I
        m = np.asarray(_I.open(os.path.join(REPO, 'Sky', 'Textures', 'Moon_Disc_1024.png')).convert('RGBA')).astype(np.float32) / 255.0
        m[..., :3] = np.where(m[..., :3] <= 0.04045, m[..., :3] / 12.92, ((m[..., :3] + 0.055) / 1.055) ** 2.4)
        S.renderer().set_texture(S.SLOTS['_MoonTex'], m)
    globs = dict(p['globals'])
    if p.get('fog_from_sky'):
        globs.update(fog_group(p))
        p['globals'] = globs
    globs = dict(globs, **p.get('preview_globals', {}))
    W, H = 480, 270
    tiles, meas = [], {}
    for label, yaw, pitch in VIEWS:
        d = camera_dirs(W, H, 90, yaw, pitch).astype(np.float32)
        if p.get('glow'):   # the 8K glow has 0.044 deg texels: 4x4 supersampled (a pixel integrates; no preview aliasing)
            img = S.render(camera_dirs(W * 4, H * 4, 90, yaw, pitch).astype(np.float32), p['material'], globs).reshape(H, 4, W, 4, 3).mean(axis=(1, 3))
        else:
            img = S.render(d, p['material'], globs).reshape(H, W, 3)
        masks = []
        mat_all = dict(S.DEFAULTS); mat_all.update(p['material'])
        if mat_all['_SunGain'] > 0:
            sd = np.array((globs.get('_Udon_SunDir') or mat_all['_SunDir'])[:3], float); masks.append((sd / np.linalg.norm(sd), mat_all['_SunShape'][0] + 1.5))
        if mat_all['_MoonGain'] > 0:
            md = np.array((globs.get('_Udon_MoonDir') or mat_all['_MoonDir'])[:3], float); masks.append((md / np.linalg.norm(md), mat_all['_MoonRadius'] + 1.5))
        gr = grad_codes(np.clip(G.grade(img, p['profile']), 0, 255), d, masks)
        gr_photo = None
        if p.get('glow'):   # the galaxy's own structure is the Gaia photograph (recorded); the rule applies to the sky without it
            gr_photo = gr
            gr = grad_codes(np.clip(G.grade(S.render(d, p['material'], dict(globs, _Udon_GalaxyGain=[0.0, 0, 0, 1])).reshape(H, W, 3), p['profile']), 0, 255), d, masks)
        sg = globs.get('_Udon_StarGain', [0, 0, 0, 0])
        if sg[3] > 0 and sg[0] > 0:
            import stars_cpu as SC
            cat = SC.catalogue()
            pk = SC.flux(cat['mag'], cat['rank'], 1.6, 0.0, 0.5, sg[2] or 50, sg[1] or 4) * sg[0]
            SC.splat(img, W, H, 90, yaw, pitch, cat['dir'], pk * (1.6 * W / 1920.0 / 1.5) ** 2, cat['col'], 1.5)   # preview: 1.5 px Gaussians, same total flux as 1.6 px at 1920
        c = np.clip(G.grade(img, p['profile']), 0, 255)
        meas[label] = dict(APL=round(G.apl(c), 1), purple=round(G.purple_fraction(c), 4),
                           lavender_6=round(G.purple_fraction(c, 285, 330, 12), 4),
                           p995=G.to_hex(np.percentile(c.reshape(-1, 3), 99.5, axis=0)), p50=G.to_hex(np.median(c.reshape(-1, 3), axis=0)),
                           grad_p999=round(float(np.percentile(gr, 99.9)), 2), grad_max=round(float(gr.max()), 2))
        Lc, ac, bc = G.lab(c); hc = np.degrees(np.arctan2(bc, ac)) % 360; Cc = np.hypot(ac, bc)
        # the lavender band (director 10-23): h 285-330, C* > 8, lighter than the bible's own indigos (L* > 40; the
        # zenith #3D4A80 / nadir #2E3C66 / blue-hour zenith #16223F sit at h 285-289, L* 14-33, and are bible targets)
        meas[label]['lavender_band'] = round(float(((hc >= 290) & (hc <= 330) & (Cc > 8) & (Lc > 40)).mean()), 4)
        if gr_photo is not None:
            meas[label]['grad_p999_with_galaxy_photo'] = round(float(np.percentile(gr_photo, 99.9)), 2)
        ref = grad_reference()
        meas[label]['grad_ok'] = bool(meas[label]['grad_p999'] <= ref['p999'] and meas[label]['grad_max'] <= ref['max'])
        t = Image.fromarray(c.astype(np.uint8))
        dr = ImageDraw.Draw(t)
        dr.text((8, 6), '%s  APL %.0f  紫 %.1f%%' % (label, meas[label]['APL'], 100 * meas[label]['purple']), fill=(255, 255, 255), font=font(15))
        tiles.append(t)
    sheet = Image.new('RGB', (W * 3, H * 2 + 40), (20, 20, 24))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * W, 40 + (i // 3) * H))
    ImageDraw.Draw(sheet).text((10, 8), '%s · %s · %s 调色（引擎参数 + bloom）· 水平 90°' % (name, p['acts'], p['profile']), fill=(230, 230, 230), font=font(18))
    sheet.save(os.path.join(OUT, 'preset_%s.png' % name))
    out_json[name] = meas
    print(name, json.dumps(meas, ensure_ascii=False))


# one material for the whole film (chief engineer r2 #0): every preset carries the Lanbai/Sky values as globals
# _Udon_Sky_<Prop> (floats in .x) + _Udon_SkyGlobals = (1, global cube A, global cube B, 1). Must match
# LanbaiSkyLayers.cginc LanbaiSkyLoadParams(); the per-preset gains go to the existing act globals.
SKY_V4 = ['_ZenithTintA', '_MidTintA', '_HorizonTintA', '_HorizonAntiTintA', '_ZenithTintB', '_MidTintB', '_HorizonTintB', '_HorizonAntiTintB',
          '_TintElevation', '_NadirColor', '_BelowShape', '_Band1Color', '_Band1Shape', '_Band2Color', '_Band2Shape', '_OtherTint',
          '_NightColor', '_StarFloorAdd', '_NightMaskDir', '_NightMaskShape', '_SunDir', '_SunColor', '_SunShape', '_SunGlow', '_SunGlowColor',
          '_MoonDir', '_MoonColor', '_MoonGlow', '_MoonGlowColor', '_PurpleGuard', '_SunRemove']
SKY_F1 = ['_RotationA', '_ExposureA', '_ClampA', '_RotationB', '_ExposureB', '_ClampB', '_Band2Gain', '_OtherGain', '_OtherSeam', '_OtherFromB',
          '_HorizonLift', '_MoonRadius', '_Exposure', '_GlowScale', '_BelowMirror']


def sky_globals(p):
    mat = dict(S.DEFAULTS); mat.update(p['material'])
    g = {}
    for k in SKY_V4:
        g['_Udon_Sky' + k] = [float(x) for x in mat[k]]
    for k in SKY_F1:
        g['_Udon_Sky' + k] = [float(mat[k]), 0.0, 0.0, 0.0]
    g['_Udon_SkyGlobals'] = [1.0, 1.0 if p.get('cubeA') else 0.0, 1.0 if p.get('cubeB') else 0.0, 1.0]
    derived = dict(_Udon_SkyBlend=[float(mat['_Blend']), float(mat['_ProcWeight']), float(mat['_NightBlend']), 1.0],
                   _Udon_SkyFx=[float(mat['_OtherSky']), float(mat['_Band1Gain']), 0.0, 1.0],
                   _Udon_SunDisc=[float(mat['_SunGain']), float(mat['_SunShape'][0]), float(mat['_SunShape'][3]), 1.0],
                   _Udon_MoonDisc=[float(mat['_MoonGain']), float(mat['_MoonRadius']), 0.0, 1.0],
                   _Udon_GalaxyGain=[float(mat['_GalaxyGain']), 0.0, 0.0, 1.0])
    for k, v in derived.items():
        g.setdefault(k, v)
    return g


def add_sky_globals(p):
    sg = sky_globals(p)
    for k, v in sg.items():
        if k.startswith('_Udon_Sky_') or k == '_Udon_SkyGlobals' or k not in p['globals']:
            p['globals'][k] = v


def normalise_globals(p):
    """v1.1: density -> _Udon_Fog (x, w = 1: x = 0 is a real 'no fog'); the model -> _Udon_FogModel (continuous mix)."""
    g = p['globals']
    if '_Udon_FogDensity' in g:
        g['_Udon_Fog'] = [float(g.pop('_Udon_FogDensity')), 0.0, 0.0, 1.0]
    if '_Udon_HorizonColor' in g:
        g['_Udon_FogModel'] = [1.0 if g['_Udon_HorizonColor'][3] > 1.5 else 0.0, 0.0, 0.0, 1.0]
        g['_Udon_HorizonColor'][3] = 1.0


GATE_ACT4 = dict(act='4（触手之门，U6 → U9）', model=0.0, near=[0.1085, 0.1130, 0.1641], far=[0.0436, 0.0504, 0.0726], zenith=[0.0021, 0.0030, 0.0070],
                 nadir=None, band_dir='朝裂口（门的驱动写 _Udon_FogBandDir，或只写 _Udon_TearPos）', width=50.0, shape=[6, 22, 2, 0.55], below=[-25, 0, 0.55, 0.6],
                 density=0.0006,
                 stars=dict(_Udon_StarGain=[STAR_GAIN_MOON, 1.0, 1.0, 1.0], _Udon_StarShape=[3.0, -1.0, 0.0, 1.0], _Udon_GalaxyGain=[0.0, 0.0, 0.0, 1.0],
                            note='D-06：第 4 幕的星 = 第 3 幕的同一套星、同一个增益，只留 3 等以上，光雾带（_Udon_FogBandDir ± _Udon_FogBandWidth、仰角 10° 以下）里再暗 1 EV（StarShape.y = −1），没有银河。门用自己的星时按同样四条。'),
                 note='= Gate/Shaders/LanbaiGateSky.cginc 的 LanbaiBand（GateLayout_v2.json sky_band 第 8 轮），逐方向相等。门的触手另外加 0.35 × 月晕 + 伤口空气（LanbaiApplyFogEx 可以加）。门的驱动至少写 _Udon_FogBandColor = (0.1085, 0.1130, 0.1641, 1) 或 _Udon_TearPos（w = 1）。')
TRANSITIONS = [   # bible §6.x; t = timeline seconds computed from the labels (Director binds the labels)
    dict(label='U1', t=[17.50, 37.50], what='雾 0.009 → 0.008（开车）', curve='smoothstep'),
    dict(label='U2b', t=[39.10, 79.10], what='雾 0.008 → 0.0025（灯尽 → 离地）', curve='smoothstep'),
    dict(label='U4h', t=[99.50, 107.50], what='雾 0 → 0.067（触云，云中雾色暖 #3A3530 → 冷 #4A5568 到 U5r）', curve='EV 线性'),
    dict(label='U6k', t=[129.10, 131.60], what='雾 0.067 → 0.00035（破云）；月夜预设', curve='ease-out'),
    dict(label='U6', t=[133.80, 163.80], what='→ 第 4 幕光带 0.0006；_Udon_FogModel 1 → 0（月夜的渐变 → 门的光带，同一段 smoothstep）', curve='smoothstep'),
    dict(label='U9 → U12', t=[179.55, 248.64], what='门内（门内会话定）', curve='—'),
    dict(label='剪 1', t=[248.64, 248.64], what='黑遮罩下硬切到晨：dawn 预设，0.00012，模型 B（A → B 在遮挡下）', curve='硬切'),
    dict(label='F2h', t=[363.26, 365.40], what='入水：海的水下组（_Udon_Underwater 0 → 1），密度 0.040（海写）', curve='水线遮挡下'),
    dict(label='出海 F9s+0.5', t=[922.36, 930.36], what='水 → 空气 0.00015、dusk_8i（_Udon_Underwater → 0）', curve='smoothstep 8 s'),
    dict(label='F10e', t=[956.36, 964.36], what='0.00015 → 0.00025、雾色 → 8-ii（dusk_8ii）', curve='smoothstep 8 s'),
    dict(label='F12', t=[987.06, 1017.06], what='雾 → 0（30 秒）；蓝时预设（雾色无所谓）', curve='线性（_Udon_Fog.x → 0，w 保持 1）'),
]


def write_fog_presets():
    out = {'about': '蓝白 · 每一幕的雾（Sky/Tools~/render/make_presets.py 生成）。颜色线性。驱动在自己的时间窗开头把这一组全部写一遍（含 .a / .w 开关），淡变只动 rgb / x。',
           'globals_order': ['_Udon_FogModel.x', '_Udon_FogBandColor (near)', '_Udon_HorizonColor (far)', '_Udon_ZenithColor', '_Udon_NadirColor',
                             '_Udon_FogBandDir', '_Udon_FogBandWidth', '_Udon_FogShape', '_Udon_FogBelow', '_Udon_Fog.x (density)'],
           'acts': [], 'transitions': TRANSITIONS}
    order = ['overcast_rain_night', 'moon_night', None, 'dawn', 'dusk_8i', 'dusk_8ii', 'blue_hour', 'star_sea']
    for name in order:
        if name is None:
            out['acts'].append(dict(preset='act4_gate', **GATE_ACT4)); continue
        g = P[name]['globals']
        out['acts'].append(dict(preset=name, act=P[name]['acts'], model=g.get('_Udon_FogModel', [None])[0],
                                near=g.get('_Udon_FogBandColor', [None] * 4)[:3], far=g.get('_Udon_HorizonColor', [None] * 4)[:3],
                                zenith=g.get('_Udon_ZenithColor', [None] * 4)[:3], nadir=g.get('_Udon_NadirColor', [None] * 4)[:3],
                                band_dir=g.get('_Udon_FogBandDir'), width=g.get('_Udon_FogBandWidth'), shape=g.get('_Udon_FogShape'),
                                below=g.get('_Udon_FogBelow'), density=g.get('_Udon_Fog', [None])[0],
                                cap='材质 _FogCap（远处巨物用；默认 1 = 不封顶）', height='材质 _FogHeightFalloff + _Udon_FogBase（地面世界 = 地面高度；云上 = 云顶）'))
    json.dump(out, open(os.path.join(REPO, 'Sky', 'FogPresets.json'), 'w'), indent=1, ensure_ascii=False, default=float)


CUBE_A = ['ZenithTintA', 'MidTintA', 'HorizonTintA', 'HorizonAntiTintA', 'RotationA', 'ExposureA', 'ClampA']
CUBE_SHARED = ['TintElevation', 'NadirColor', 'BelowShape', 'SunRemove', 'HorizonLift', 'OtherTint', 'BelowMirror']
DIRS = ['_Udon_FogBandDir', '_Udon_SunDir', '_Udon_MoonDir', '_Udon_Sky_SunDir', '_Udon_Sky_MoonDir', '_Udon_Sky_NightMaskDir']


# D-09: the act-8 frames with the cabin, in VR (Engineering/render_harness vr_left_fwd + the bible_v2 shell, S8, this
# preset as the world; measured by the sky session, the numbers are re-measured whenever the dusk presets change)
D09 = {'dusk_8i': dict(t=940.0, cam='vr_left_fwd', bus='bible_v2', APL=79.6, purple_pct=0.001, bible_target=78.4),
       'dusk_8ii': dict(t=960.0, cam='vr_left_fwd', bus='bible_v2', APL=81.55, purple_pct=0.01, bible_target=81.6)}


def blend_group(n):
    """LanbaiSkyPreset.ApplyBlend groups: 0 lerp, 1 cube-A parameter, 2 cube-B parameter, 3 flags (max),
    4 a parameter of the cube layer shared by A and B (from the side that has a cube), 5 a direction (w-aware)"""
    if n == '_Udon_SkyGlobals':
        return 3
    if n in DIRS:
        return 5
    if n.startswith('_Udon_Sky_'):
        b = n[len('_Udon_Sky_'):]
        if b in CUBE_A:
            return 1
        if b[:-1] + 'A' in CUBE_A and b.endswith('B'):
            return 2
        if b in CUBE_SHARED:
            return 4
    return 0


def cue_t(label):
    c = json.load(open(os.path.join(REPO, 'FromLocal', 'cues.json')))
    for grp in ('U', 'U_sub', 'F', 'F_sub'):
        if label in c.get(grp, {}):
            return float(c[grp][label]['t'])
    raise KeyError(label)


def driver_tables():
    """README_Sky §3.1: LanbaiSkyDriver instances, one per continuous window (tech r2 #3). t from FromLocal/cues.json."""
    return [
        dict(name='Lanbai_SkyDriver_Acts1to3', entries=[
            dict(preset='overcast_rain_night_town', t0=0.0, t1=cue_t('U1'), fade=0.0, label='0 → U1'),
            dict(preset='overcast_rain_night', t0=cue_t('U1'), t1=cue_t('U6k'), fade=10.0, label='U1 → U6k（钠光 10 秒淡掉）'),
            dict(preset='moon_night', t0=cue_t('U6k'), t1=cue_t('U6'), fade=0.0, label='U6k 破云（云里，遮挡下）→ U6（门接手雾）')]),
        dict(name='Lanbai_SkyDriver_Acts11to12', entries=[
            dict(preset='overcast_rain_night', t0=cue_t('F16'), t1=100000.0, fade=0.0, label='F16 白遮罩下 → 片尾')]),
    ]


def check_one_material(name, p):
    """the preset through the material (old path) vs the same preset through the globals on a DEFAULT material
    (one-material path): must be the same picture"""
    d = np.concatenate([camera_dirs(96, 54, 90, yaw, pitch) for _, yaw, pitch in VIEWS]).astype(np.float32)
    a = S.render(d, p['material'], {k: v for k, v in p['globals'].items() if k in p['_own_globals']})
    b = S.render(d, {}, p['globals'])
    err = float(np.max(np.abs(a - b) / (np.abs(a) + 1e-3)))
    print('one-material check %-26s max rel diff %.2e %s' % (name, err, 'OK' if err < 1e-4 else 'MISMATCH'))
    if err >= 1e-4:
        raise SystemExit('one-material mismatch in ' + name)


def main():
    meas = {}
    grad_reference()
    gs = S.glow_scale()
    for name, p in P.items():
        if p.get('glow'):
            p['material']['_GlowScale'] = gs
        # every preset says what the stars do (tech r2 #5): off unless the preset turns them on
        p['globals'].setdefault('_Udon_StarGain', [0.0, 1.0, 1.0, 1.0])
        p['globals'].setdefault('_Udon_StarShape', [6.5, 0.0, 0.0, 1.0])
        p['globals'].setdefault('_Udon_GalaxyGain', [0.0, 0.0, 0.0, 1.0])
        render_sheet(name, p, meas)
        p['_own_globals'] = set(p['globals'].keys())
        add_sky_globals(p)
        check_one_material(name, p)
        normalise_globals(p)
    write_fog_presets()
    # JsonUtility-friendly export for the C# builder (flat lists)
    out = {'about': '蓝白 · 每一幕的天空预设（Sky/Tools~/render/make_presets.py 生成，别手改）。颜色全是线性值。material = Lanbai/Sky 的属性；globals = 这一幕的驱动写的全局量。',
           'presets': []}
    # every preset lists EVERY sky / fog global any preset uses (absent = 0 = 'not set'), so Apply() never leaves a
    # previous act's value behind (tech review r1 must-fix 1: the act-3 moon would follow into dawn, the dusk sun disc
    # into the blue hour)
    allv = sorted({k for p in P.values() for k, v in p['globals'].items() if np.ndim(v) > 0})
    allf = sorted({k for p in P.values() for k, v in p['globals'].items() if np.ndim(v) == 0})
    allv = sorted(set(allv) | {'_Udon_FogCubeParams', '_Udon_FogBase'})   # the sky's own, written 0 = off (tech r2 #12)
    for p in P.values():
        for k in allv:
            p['globals'].setdefault(k, [0.0, 0.0, 0.0, 0.0])
        for k in allf:
            p['globals'].setdefault(k, 0.0)
    for name, p in P.items():
        e = {'name': name, 'acts': p['acts'], 'profile': p['profile'], 'cubeA': p.get('cubeA') or '', 'glow': bool(p.get('glow')),
             'moon': bool(p['material'].get('_MoonGain', 0) > 0), 'sunAz': float(p.get('sunAz', -999.0)),
             'notes': p['notes'], 'floats': [], 'vectors': [], 'globalFloats': [], 'globalVectors': []}
        for k, v in p['material'].items():
            if np.ndim(v) == 0:
                e['floats'].append({'k': k, 'v': round(float(v), 6)})
            else:
                e['vectors'].append({'k': k, 'v': [round(float(x), 6) for x in v]})
        for k, v in sorted(p['globals'].items()):     # one fixed order in every preset: ApplyBlend's map is the identity
            if np.ndim(v) == 0:
                e['globalFloats'].append({'k': k, 'v': round(float(v), 6)})
            else:
                e['globalVectors'].append({'k': k, 'v': [round(float(x), 6) for x in v]})
        # how ApplyBlend treats each vector (tech r2 #2c: explicit, not guessed from the name in Udon)
        names = [kv['k'] for kv in e['globalVectors']]
        e['vecGroups'] = [blend_group(n) for n in names]
        e['vecPartner'] = [names.index(n[:-1] + 'A') if blend_group(n) == 2 else -1 for n in names]
        e['blendSkip'] = list(p.get('blend_skip', []))
        e['measured_views'] = dict(meas[name])
        if name in D09:
            e['measured_views']['vr_cabin_bible_v2'] = D09[name]
        out['presets'].append(e)
    out['drivers'] = driver_tables()
    json.dump(out, open(os.path.join(REPO, 'Sky', 'SkyPresets.json'), 'w'), indent=1, ensure_ascii=False)
    print('wrote Sky/SkyPresets.json')


if __name__ == '__main__':
    main()
