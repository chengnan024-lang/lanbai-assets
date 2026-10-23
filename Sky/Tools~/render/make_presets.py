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
SUN6 = dir_az_el(45.0, 5.8)      # dawn: the HDRI sun is at 5.8 deg; the real-time light aligns to it (bible §6·6)
SUN8 = dir_az_el(0.0, 0.5)       # dusk: azimuth 0, elevation +0.5 deg, in the windscreen (bible §6·8)
P = {}

P['overcast_rain_night'] = dict(acts='1 · 2（×0.6）· 11（= 2）· 12 的开头', profile='S1',
    cubeA='Sky_Overcast_Night_2048x1024', hdri_file=os.path.join(REPO, 'Sky', 'Textures', 'Sky_Overcast_Night_2048x1024.hdr'),
    material=dict(_RotationA=0.0, _ExposureA=0.0, _SunGain=0.0, _NadirColor=v4(F('#161B27'), 0.0), _BelowShape=[-30, 0.8, 0.6, 2.0]),
    globals=dict(_Udon_HorizonColor=v4(F('#161B27'), 2.0), _Udon_FogBandColor=v4(F('#161B27')), _Udon_ZenithColor=v4(F('#09080D')),
                 _Udon_NadirColor=v4(F('#161B27')), _Udon_FogShape=[0, 50, 0.6, 0], _Udon_FogBelow=[-30, 0, 1, 0],
                 _Udon_FogDensity=0.009),
    notes='天顶 #070B14（填 #09080D）、雾 = 地平线 #121A28（填 #161B27）。第 2 / 11 幕：_ExposureA −0.7 EV（S2 天 #05080F 填 #060405），雾填 #0D0F15，密度 0.008。偏航只在这种没有特征的天下允许。')

P['moon_night'] = dict(acts='3（离地、月下云海）', profile='S3', cubeA=None,
    material=dict(_ProcWeight=1.0, _SunGain=0.0, _MoonGain=1.0, _MoonRadius=0.6, _MoonDir=v4(dir_az_el(-12, 8), 0),
                  _MoonColor=v4(F('#F0F5FF @ +1.67')), _MoonGlow=[1.6, 0.9, 0.06, 0.32], _MoonGlowColor=v4(F('#8FA3C8'))),
    globals=dict(_Udon_HorizonColor=v4(F('#242A40'), 2.0), _Udon_FogBandColor=v4(F('#2E3753')), _Udon_FogBandDir=v4(dir_az_el(-12, 0), 0),
                 _Udon_FogBandWidth=120.0, _Udon_ZenithColor=v4(F('#151928')), _Udon_NadirColor=v4(F('#1A2034')), _Udon_FogShape=[0, 40, 1.5, 0.0], _Udon_FogBelow=[-40, 0, 1.0, 0],
                 _Udon_MoonDir=v4(dir_az_el(-12, 8), 1), _Udon_MoonDisc=[1.0, 0.6, 0, 1], _Udon_FogDensity=0.00035),
    notes='天顶 #08101F（填 #151928）、背月地平线 = 云上雾色 #111B30（填 #242A40）、月面 #EAEEF4（填 #F0F5FF @ +1.67）、月晕（门的公式）。月在 −12° / +8°、直径 1.2°。')

P['dawn'] = dict(acts='6（晨，F0 → F2h）', profile='S6', sunAz=45.0, cubeA='syferfontein_6d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_6d_clear_puresky_1k.hdr'),
    material=dict(_RotationA=fit['dawn']['rotation'], _ExposureA=0.0, _ClampA=16.0, **tints('dawn'),
                  _SunDir=v4(SUN6, 0), _SunColor=v4(F('#FFCE9E @ +2.55')), _SunShape=[0.45, 0.04, 0.55, 0], _SunGain=1.0,
                  _Band1Color=v4(F('#B8C4F7'), 0.3), _Band1Shape=[2.0, 2.5, 180, 55], _Band1Gain=0.6,
                  _Band2Color=v4(F('#FFCFCB @ +0.61'), 0.3), _Band2Shape=[10.0, 4.0, 180, 50], _Band2Gain=0.3,
                  _NadirColor=v4(F('#6F8FA8'), 0.5), _BelowShape=[-75, 1.0, 0.6, 2.0], _PurpleGuard=[1.0, 0.86, 1.25, 0]),
    globals=dict(_Udon_SunDir=v4(SUN6, 1), _Udon_SunDisc=[1.0, 0.45, 0, 1], _Udon_FogDensity=0.00012),
    fog_from_sky=dict(near_az=45.0, width=70.0, zen_el=60.0, nadir=F('#6F8FA8')),
    notes='天顶 #3E64A6、背日 45° #AFC4E0、日侧地平线 #F2C79A、地影带 #8C98B8 + 很淡的金星带 #CFB7B7（HDRI 里没有，由两条地平线带给）、日盘 0.9° #FFF3DE（填 #FFCE9E @ +2.55）。太阳 方位 +45°、仰角 5.8°（HDRI 的太阳）。')

dusk_common = dict(_RotationA=fit['dusk']['rotation'], _ExposureA=0.0, _ClampA=16.0, **tints('dusk'),
                   _SunDir=v4(SUN8, 0), _SunColor=v4(F('#FF9167 @ +2.74')), _SunShape=[0.45, 0.04, 0.4, 0], _SunGain=1.0,
                   _SunGlow=[0.35, 0.9, 0.12, 0.12], _SunGlowColor=v4(F('#FF855C')),
                   _Band2Color=v4(F('#FF9396 @ +0.92'), 0.25), _Band2Shape=[4.0, 3.0, 180, 55], _Band2Gain=0.6,
                   _NadirColor=v4(F('#3B4A78'), 0.5), _BelowShape=[-75, 1.0, 0.6, 2.0], _PurpleGuard=[1.0, 0.82, 1.25, 0],
                   _OtherGain=0.82, _OtherTint=[0.92, 0.95, 1.05, 1], _OtherSeam=1.0)
P['dusk_8i'] = dict(acts='8-i（出海 → F10e）', profile='S8', sunAz=0.0, cubeA='syferfontein_0d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_0d_clear_puresky_1k.hdr'),
    material=dict(dusk_common, _OtherSky=0.0),
    globals=dict(_Udon_SunDir=v4(SUN8, 1), _Udon_SunDisc=[1.0, 0.45, 0, 1], _Udon_SkyFx=[0, 0, 0, 1], _Udon_FogDensity=0.00015),
    fog_from_sky=dict(near_az=0.0, width=80.0, zen_el=60.0, nadir=F('#3B4A78')),
    notes='日带 #FFB070、玫瑰带 #E7A0A0（填 #FF9396 @ +0.92）、中天 #808AB2、天顶 #3D4A80、日盘 #FFE2B0（填 #FF9167 @ +2.74）、天缝 #F2A56B（日晕）。太阳 方位 0°、仰角 +0.5°。紫护栏把 HDRI 背日的藍紫在 S8 的暖调色下拉回靛灰。')
P['dusk_8ii'] = dict(acts='8-ii（另一片天，F10e → F12）', profile='S8', sunAz=0.0, cubeA='syferfontein_0d_clear_puresky',
    hdri_file=os.path.join(HDRI, 'syferfontein_0d_clear_puresky_1k.hdr'),
    material=dict(dusk_common, _OtherSky=1.0),
    globals=dict(_Udon_SunDir=v4(SUN8, 1), _Udon_SunDisc=[1.0, 0.45, 0, 1], _Udon_SkyFx=[1.0, 0, 0, 1], _Udon_FogDensity=0.00025),
    fog_from_sky=dict(near_az=0.0, width=80.0, zen_el=60.0, nadir=F('#3B4A78')),
    notes='_OtherSky 0 → 1（956.36 → 964.36，8 秒 smoothstep）：下半球按 (−x, −y, z) 取样，×0.82、染 (0.92, 0.95, 1.05)，1° 软接缝；两个太阳在接缝上熔成一条线。F12 起日线：_Udon_SunDisc.z（线的半长）10° → 0、增益 → 0（987.06 → 993.06）。')

bh_zen = inv_screen('#16223F', 'S8b')
P['blue_hour'] = dict(acts='8b（蓝时，993.06 → 1001.21）', profile='S8b', cubeA=None,
    material=dict(_ProcWeight=1.0, _SunGain=0.0, _Band1Color=v4(F('#3F5790'), 0.0), _Band1Shape=[12.0, 7.0, 0, 100], _Band1Gain=0.9,
                  _NightMaskDir=v4(dir_az_el(0, 0), 0), _NightMaskShape=[40, 15, 12, 10], _NightColor=v4(F('#050000')),
                  _PurpleGuard=[1.0, 0.86, 1.25, 0]),
    globals=dict(_Udon_HorizonColor=v4(F('#8093C2') * 0.80, 2.0), _Udon_FogBandColor=v4(F('#8093C2')), _Udon_FogBandDir=v4(dir_az_el(0, 0), 0),
                 _Udon_FogBandWidth=90.0, _Udon_ZenithColor=v4(bh_zen), _Udon_NadirColor=v4(F('#1A2A4E') * 1.3),
                 _Udon_FogShape=[1.0, 70.0, 0.7, 0], _Udon_FogBelow=[-60, 0, 0.8, 0], _Udon_SkyBlend=[0, 1, 0, 1], _Udon_SkyFx=[0, 0.9, 0, 1],
                 _Udon_FogDensity=0.0),
    notes='天缝 / 地平线 #6F86B0（填 #8093C2）、最纯的蓝带 #2E4F8A（填 #3F5790）、天顶 #16223F、另一片天的天底 #1A2A4E。程序化（LanbaiHorizon 模型 B + 地平线带 1），上下对称。987.06 → 993.06 由暮的立方图 6 秒过渡到这里（_Udon_SkyBlend.y 0 → 1，与日线收缩同步）。1001.21 → 1009.21：_Udon_SkyBlend.z 0 → 1（夜的定向遮罩：前方 ±40° 的地平线带最后暗）。')

night = F('#050000'); floor = F('#0D0F23')
P['star_sea'] = dict(acts='9（星海，F13 起）', profile='S9a', cubeA=None, glow=True,
    material=dict(_ProcWeight=1.0, _NightBlend=1.0, _NightColor=v4(night), _StarFloorAdd=v4(np.maximum(floor - night, 0)),
                  _GalaxyGain=1.0, _SunGain=0.0),
    globals=dict(_Udon_SkyBlend=[0, 1, 1, 1], _Udon_GalaxyGain=[1.0, 0, 0, 1], _Udon_StarGain=[1.0, 4.0, 50, 1],
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


def render_sheet(name, p, out_json):
    S.renderer().tex.clear()
    if p.get('hdri_file'):
        S.set_cube('_CubeA', S.load_hdr(p['hdri_file']))
    if p.get('glow'):
        import OpenEXR, Imath
        ex = OpenEXR.InputFile(os.path.join(REPO, 'Sky', 'Textures', 'StarSky_Glow_4096x2048.exr'))
        dw = ex.header()['dataWindow']; w, h = dw.max.x + 1, dw.max.y + 1
        img = np.stack([np.frombuffer(ex.channel(ch, Imath.PixelType(Imath.PixelType.FLOAT)), np.float32).reshape(h, w) for ch in 'RGB'], -1)
        S.set_tex('_GlowTex', img[:, ::2][::2].copy())
    globs = dict(p['globals'])
    if p.get('fog_from_sky'):
        globs.update(fog_group(p))
        p['globals'] = globs
    W, H = 480, 270
    tiles, meas = [], {}
    for label, yaw, pitch in VIEWS:
        d = camera_dirs(W, H, 90, yaw, pitch).astype(np.float32)
        img = S.render(d, p['material'], globs).reshape(H, W, 3)
        c = np.clip(G.grade(img, p['profile']), 0, 255)
        meas[label] = dict(APL=round(G.apl(c), 1), purple=round(G.purple_fraction(c), 4),
                           lavender_6=round(G.purple_fraction(c, 285, 330, 12), 4),
                           p995=G.to_hex(np.percentile(c.reshape(-1, 3), 99.5, axis=0)), p50=G.to_hex(np.median(c.reshape(-1, 3), axis=0)))
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


def main():
    meas = {}
    for name, p in P.items():
        render_sheet(name, p, meas)
    # JsonUtility-friendly export for the C# builder (flat lists)
    out = {'about': '蓝白 · 每一幕的天空预设（Sky/Tools~/render/make_presets.py 生成，别手改）。颜色全是线性值。material = Lanbai/Sky 的属性；globals = 这一幕的驱动写的全局量。',
           'presets': []}
    for name, p in P.items():
        e = {'name': name, 'acts': p['acts'], 'profile': p['profile'], 'cubeA': p.get('cubeA') or '', 'glow': bool(p.get('glow')),
             'moon': bool(p['material'].get('_MoonGain', 0) > 0), 'sunAz': float(p.get('sunAz', -999.0)),
             'notes': p['notes'], 'floats': [], 'vectors': [], 'globalFloats': [], 'globalVectors': []}
        for k, v in p['material'].items():
            if np.ndim(v) == 0:
                e['floats'].append({'k': k, 'v': round(float(v), 6)})
            else:
                e['vectors'].append({'k': k, 'v': [round(float(x), 6) for x in v]})
        for k, v in p['globals'].items():
            if np.ndim(v) == 0:
                e['globalFloats'].append({'k': k, 'v': round(float(v), 6)})
            else:
                e['globalVectors'].append({'k': k, 'v': [round(float(x), 6) for x in v]})
        e['measured_views'] = meas[name]
        out['presets'].append(e)
    json.dump(out, open(os.path.join(REPO, 'Sky', 'SkyPresets.json'), 'w'), indent=1, ensure_ascii=False)
    print('wrote Sky/SkyPresets.json')


if __name__ == '__main__':
    main()
