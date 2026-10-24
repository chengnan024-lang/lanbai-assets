"""第 9 幕 · 数据（唯一数据源）：Act09_StarSea/Act09_StarSea.json
Run after act09_calib.py. Everything the driver / build script / local needs is written here (CONTROL §6 item 13)."""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
import stars_cpu as SC, grade as G

cues = json.load(open(os.path.join(REPO, 'FromLocal', 'cues.json')))
F = cues['F']
LAB = dict(F12=F['F12']['t'], F13=F['F13']['t'], F14=F['F14']['t'], F15=F['F15']['t'], F16=F['F16']['t'])
LAB['blue_hour_start'] = round(LAB['F12'] + 6.0, 2)      # 993.06: the sun line has gone
LAB['act9_start'] = 1001.21                               # bible §2.2: 8b ends, act 9 (9a) begins
LAB['dark_end'] = round(LAB['act9_start'] + 8.0, 2)       # 1009.21
ign = json.load(open(os.path.join(REPO, 'Act09_StarSea', 'Data', 'ignition.json')))
T_ign = ign['ignition_s']
LAB['ignition_full'] = round(LAB['F13'] + T_ign, 2)
mir = None
try:
    import subprocess
    mir = json.loads(subprocess.check_output(['git', '-C', REPO, 'show', 'origin/pkg/mirrors:Mirrors/MirrorSchedule.json']))
except Exception:
    pass
first_mirror = mir['labels']['first_mirror'] if mir else 1032.41

cat = SC.catalogue()
SKY = {p['name']: {kv['k']: kv['v'] for kv in p['globalVectors']} for p in json.load(open(os.path.join(REPO, 'Sky', 'SkyPresets.json')))['presets']}
NIGHT = SKY['blue_hour']['_Udon_Sky_NightColor'][:3]              # the sky's own night colour and star floor (not literals)
FLOOR_ADD = SKY['blue_hour']['_Udon_Sky_StarFloorAdd'][:3]
# ---- the first stars of the blue hour: a dozen real stars around the zenith (where the palace lights dispersed);
# they go out one by one in the darkening, the one nearest the zenith last (at 1009.21)
d = cat['dir']; elev = np.degrees(np.arcsin(np.clip(d[:, 1], -1, 1)))
cand = np.nonzero((elev > 62) & (cat['mag'] < 4.6))[0]
cand = cand[np.argsort(cat['mag'][cand])][:12]
cand = cand[np.argsort(-(90 - elev[cand]))]               # farthest from the zenith first
first = []
for k, i in enumerate(cand):
    first.append(dict(hr=int(cat['hr'][i]), dir=[round(float(x), 6) for x in d[i]], mag=float(cat['mag'][i]),
                      el=round(float(elev[i]), 2), order=round(k / (len(cand) - 1), 4),
                      out_t=round(LAB['act9_start'] + 8.0 * (0.25 + 0.75 * k / (len(cand) - 1)), 2)))
# ---- the 16 stars of the question (Fonts/strings_all.json poem P09_Tianwen, zh layout): one where each character was,
# on the character's densest stroke junction (the maximum of its ink blurred by 0.06 em, Source Han Serif), not the
# em-box centre (final review r1 #4: em-box centres made a 2 x 8 lattice, "a dotted line"); the peak by stroke count
# over a magnitude-like range 1.2 .. 6 (x 6 = bible §6·9 9a; 1.75 mag), so the 12- and 10-stroke ones lead
S = json.load(open(os.path.join(REPO, 'Fonts', 'strings_all.json')))
P = [p for p in S['poems'] if p.get('id') == 'P09_Tianwen'][0]
lay = P['layout']['zh']['objects'][0]
dist = P['place'][2]; em_m = dist * math.tan(math.radians(P['size_main']))
STROKES = {'遂': 12, '古': 5, '之': 3, '初': 7, '谁': 10, '传': 6, '道': 12, '上': 3, '下': 3, '未': 5, '形': 7, '何': 7, '由': 5, '考': 6}
Q_PEAK = (1.2, 6.0)
GLYPH_FONT = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')   # the SC face's glyphs


def glyph_point(ch, n=1000):
    """(x from the em-box centre, y above the baseline) in em of the densest stroke junction."""
    from PIL import Image, ImageDraw, ImageFont
    from scipy.ndimage import gaussian_filter
    f = ImageFont.truetype(GLYPH_FONT, n)
    asc = f.getmetrics()[0]
    im = Image.new('L', (n, int(n * 1.3)), 0)
    ImageDraw.Draw(im).text((0, 0), ch, font=f, fill=255)           # baseline at y = asc
    b = gaussian_filter(np.asarray(im, float) / 255.0, 0.06 * n)
    py, px = np.unravel_index(b.argmax(), b.shape)
    return (px - f.getlength(ch) / 2) / n, (asc - py) / n


qstars = []
for c in lay['char_objects']:
    if not c['star']:
        continue
    gx, gy = glyph_point(c['char'])
    el_base = math.radians(c['baseline_el']); y = dist * math.tan(el_base) + gy * em_m
    x = c['local_x_m'] + gx * em_m
    v = np.array([x, y, dist]); v /= np.linalg.norm(v)     # text centred straight ahead (azimuth 0), 50 m
    n = STROKES[c['char']]
    qstars.append(dict(char=c['char'], strokes=n, dir=[round(float(t), 6) for t in v], glyph_em=[round(gx, 3), round(gy, 3)],
                       az=round(math.degrees(math.atan2(v[0], v[2])), 3), el=round(math.degrees(math.asin(v[1])), 3),
                       peak=round(Q_PEAK[0] * (Q_PEAK[1] / Q_PEAK[0]) ** ((n - 3) / 9.0), 3)))

out = dict(
    about='蓝白 · 第 9 幕（星海）的天：时间线、银河点燃线 g(t)、星的亮度、第一批星、天问的 16 颗星。由 Act09_StarSea/Tools~/make_act09.py 生成，不要手改。t = 时间轴秒（由 cues.json 的标签算出；Director 绑标签）。',
    labels=LAB,
    window=[round(LAB['blue_hour_start'] - 1.0, 2), LAB['F16']],
    ownership=('两个边界。1001.21（第 9 幕起点）起本驱动每帧写 _Udon_SkyBlend、_Udon_SkyFx、_Udon_Fog、_Udon_GalaxyGain、_Udon_StarGain；'
               '1009.21（变暗结束）起再加 _Udon_ZenithColor、_Udon_HorizonColor、_Udon_FogBandColor、_Udon_NadirColor（= 星空底）。'
               '在这之前这些名字归第 8b 幕（云）的驱动；8b 的驱动在 t ≥ 1001.21 时不再调用 LanbaiSkyPreset 的 Apply / ApplyBlend（Apply 一次写全部 68 个名字，会成第二个写的人，D-22）。'
               '第一批星的材质参数从 993.06 起由本驱动写（MaterialPropertyBlock，不用全局量）。1149.31（F16）起归 Lanbai_SkyDriver_Acts11to12。'),
    sky=dict(material='Sky/Generated/M_Sky.mat（全片一个天空材质；8b 与 9 都是蓝时预设 blue_hour 的全局量 + 本驱动的覆盖）',
             night=dict(t=[LAB['act9_start'], LAB['dark_end']], curve='linear', global_='_Udon_SkyBlend.z 0 -> 1（shader 里按方向延迟，_Udon_Sky_NightMaskShape = (40, 45, 6, 22)：背日与天顶 6 s 黑；前方 ±40° 的地平线带 1007.2 仍 ≥ 50%，最后一抹贴着地平线、几度高、顶边平，8 s 黑）'),
             band1_gain=0.85, proc=1.0,
             zenith_floor=dict(night=[round(float(x), 6) for x in NIGHT], floor_add=[round(float(x), 6) for x in FLOOR_ADD],
                               note='星空底 = night + g x floor_add（从 SkyPresets.json 的 blue_hour 读，和天空一致），从 1009.21 起每帧写进 _Udon_ZenithColor（镜子读它当星空底）、_Udon_HorizonColor、_Udon_FogBandColor、_Udon_NadirColor（和 star_sea 预设一样，LanbaiHorizon / LanbaiApplyFog 也落在星空底上）')),
    ignition=dict(t0=LAB['F13'], seconds=T_ign, table_step_s=0.05, g=ign['g_table']['g'], extreme_view=ign['extreme_view'],
                  g_core=ign['g_table'].get('g_core', ign['g_table']['g']), ease_s=ign['g_table']['ease_s'], core_lead_s=ign['core_lead_s'],
                  core='_Udon_GalaxyGain = (旋臂 g, 银心 g_core, 1, 1)：g_core 是同一口气提前 core_lead_s 秒（地板以下的缓起短 core_lead_s，之后的 EV 线性段整体提前，涨的速度和旋臂一样），按银经从银心 15° 内到 60° 外软过渡（LanbaiGalaxyCoreWeight，Common/Shaders/LanbaiSky.cginc），光沿银河带铺开',
                  how=ign['g_table']['how'],
                  recalibrate='Unity 里用两张正前方截图（含车厢）标定：F13 那一帧的平均亮度 C、g = 1 时的 G（L = 显示线性亮度的平均，地板 0.004）。T = max(4.2, log2(G / C) / 0.85)；g(t) 让 L 从 C 按 EV 线性涨到 G（需要 L(g) 曲线：g = 0、0.25、0.5、0.75、1 五张截图插值）。',
                  ramp_law=ign['ramp_law']),
    climax=dict(x='(t - F13) / (F16 - F13)', galaxy_gain='g(t) x (1 + 0.8 x^2.5)（旋臂和银心各乘）', star_boost='4 + 4 x^2.5', bright_count='50 + 150 x^2.5'),
    stars=dict(mesh='Sky/Generated/StarPoints_BSC5.asset', material='Sky/Generated/M_Sky_StarPoints.mat', count=int(len(cat['mag'])),
               params=dict(_StarScale=1.6, _MagRef=0.0, _MagSlope=0.5, _MagFloor=6.5, _FWHM=1.6, _BrightCount=50, _BrightBoost=4, _Distance=20000),
               gain='_Udon_StarGain.x：F13 之前 0，F13 那一帧 1（一帧之内全部出现，+0.00 EV：F13 那一帧各视向的平均亮度都在地板 0.004 以下）',
               F13_check={v: dict(L_F13=round(ign['views'][v]['L_F13'], 5), under_floor=ign['views'][v]['F13_under_floor']) for v in ign['views']}),
    first_stars=dict(stars=first, colour_target='#E8EEF8', appear=[LAB['blue_hour_start'] + 1.0, LAB['blue_hour_start'] + 4.0], peak=0.55,
                     out_s=0.8, note='天顶附近十几颗真实的星（BSC，≤ 4.6 等，仰角 > 62°）。993.06 + 1 起 3 秒出现；1001.21 起按离天顶由远到近一颗颗熄灭（每颗 0.8 s），天顶那一颗在 1009.21 熄灭，同一刻天问开始对焦（圣经 §3.3）。'),
    question_stars=dict(stars=qstars, appear='F13 那一帧（与所有星同时）', colour='#F2F6FF', fwhm_px=1.6,
                        note='每个字原来的位置一颗（Fonts/strings_all.json P09_Tianwen 的排版：方位 0°、仰角 +8°、50 m、2.2°），落在这个字笔画最密的交点（思源宋体墨迹按 0.06 em 模糊后的最大值，glyph_em = 相对字框中心的 x、基线以上的 y），不是字框中心；HDR 峰值按笔画数 1.2 × 5^((笔画 − 3) / 9)，即 1.2 … 6（×6，圣经 §6·9 9a；1.75 等），12 画和 10 画的三颗最亮；留到第 9 幕结束。字本身由字体套件的诗句系统在 1.2 s 内暗下。'),
    mirrors=dict(schedule='Mirrors/MirrorSchedule.json（pkg/mirrors，「镜与白」）', first_mirror=first_mirror,
                 hold_after_ignition=round(first_mirror - LAB['ignition_full'], 2),
                 note='镜子的网格 / shader / 驱动由「镜与白」交；本幕的搭建脚本在套件到了以后把它挂进 R_StarSea。'),
    grades=dict(before='S8b', blend=[LAB['act9_start'], LAB['dark_end'], 'S8b -> S9a'], climax='S9a -> S9b on x^2.5（调色套件 / Director 管 weight）'),
    fog='关（_Udon_Fog = (0, 0, 0, 1)）',
)
json.dump(out, open(os.path.join(REPO, 'Act09_StarSea', 'Act09_StarSea.json'), 'w'), indent=1, ensure_ascii=False)
print('first stars', [(f['hr'], f['el'], f['mag']) for f in first])
print('question stars', [(q['char'], q['az'], q['el']) for q in qstars][:4], '...')
print('labels', LAB)
