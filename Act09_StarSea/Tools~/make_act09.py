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
# ---- the 16 stars of the question (Fonts/strings_all.json poem P09_Tianwen, zh layout): one at each character's centre
S = json.load(open(os.path.join(REPO, 'Fonts', 'strings_all.json')))
P = [p for p in S['poems'] if p.get('id') == 'P09_Tianwen'][0]
lay = P['layout']['zh']['objects'][0]
dist = P['place'][2]; em_m = dist * math.tan(math.radians(P['size_main']))
STROKES = {'遂': 12, '古': 5, '之': 3, '初': 7, '谁': 10, '传': 6, '道': 12, '上': 3, '下': 3, '未': 5, '形': 7, '何': 7, '由': 5, '考': 6}
qstars = []
for c in lay['char_objects']:
    if not c['star']:
        continue
    el_base = math.radians(c['baseline_el']); y = dist * math.tan(el_base) + 0.38 * em_m
    x = c['local_x_m']
    v = np.array([x, y, dist]); v /= np.linalg.norm(v)     # text centred straight ahead (azimuth 0), 50 m
    n = STROKES[c['char']]
    qstars.append(dict(char=c['char'], strokes=n, dir=[round(float(t), 6) for t in v],
                       az=round(math.degrees(math.atan2(v[0], v[2])), 3), el=round(math.degrees(math.asin(v[1])), 3),
                       peak=round(4.0 * (0.4 + 0.6 * n / 12.0), 3)))

out = dict(
    about='蓝白 · 第 9 幕（星海）的天：时间线、银河点燃线 g(t)、星的亮度、第一批星、天问的 16 颗星。由 Act09_StarSea/Tools~/make_act09.py 生成，不要手改。t = 时间轴秒（由 cues.json 的标签算出；Director 绑标签）。',
    labels=LAB,
    window=[round(LAB['blue_hour_start'] - 1.0, 2), LAB['F16']],
    ownership='1001.21（第 9 幕起点）之前 _Udon_SkyBlend / _Udon_SkyFx 归第 8b 幕（云）的驱动；之后归本幕驱动。第一批星的材质参数从 993.06 起由本驱动写（它们不用全局量）。',
    sky=dict(material='Sky/Generated/M_Sky_blue_hour.mat（8b 与 9 同一个材质：程序化蓝时 + 夜层 + 银河辉光）',
             night=dict(t=[LAB['act9_start'], LAB['dark_end']], curve='linear', global_='_Udon_SkyBlend.z 0 -> 1（shader 里按方向延迟：背日与天顶 6 s 黑，前方 ±40° 的地平线带 8 s）'),
             band1_gain=0.85, proc=1.0,
             zenith_floor=dict(night=[0.0015, 0.0, 0.0], floor_add=[round(float(x), 6) for x in np.maximum(G.fill('#0D0F23') - G.fill('#050000'), 0)],
                               note='_Udon_ZenithColor = night + g x floor_add，从 1009.21 起每帧写（镜子读它当星空底）')),
    ignition=dict(t0=LAB['F13'], seconds=T_ign, table_step_s=0.05, g=ign['g_table']['g'], extreme_view=ign['extreme_view'],
                  how=ign['g_table']['how'],
                  recalibrate='Unity 里用两张正前方截图（含车厢）标定：F13 那一帧的平均亮度 C、g = 1 时的 G（L = 显示线性亮度的平均，地板 0.004）。T = max(4.2, log2(G / C) / 0.85)；g(t) 让 L 从 C 按 EV 线性涨到 G（需要 L(g) 曲线：g = 0、0.25、0.5、0.75、1 五张截图插值）。',
                  ramp_law=ign['ramp_law']),
    climax=dict(x='(t - F13) / (F16 - F13)', galaxy_gain='g(t) x (1 + 0.8 x^2.5)', star_boost='4 + 4 x^2.5', bright_count='50 + 150 x^2.5'),
    stars=dict(mesh='Sky/Generated/StarPoints_BSC5.asset', material='Sky/Generated/M_Sky_StarPoints.mat', count=int(len(cat['mag'])),
               params=dict(_StarScale=1.6, _MagRef=0.0, _MagSlope=0.5, _MagFloor=6.5, _FWHM=1.6, _BrightCount=50, _BrightBoost=4, _Distance=20000),
               gain='_Udon_StarGain.x：F13 之前 0，F13 那一帧 1（一帧之内全部出现，+0.00 EV：F13 那一帧各视向的平均亮度都在地板 0.004 以下）',
               F13_check={v: dict(L_F13=round(ign['views'][v]['L_F13'], 5), under_floor=ign['views'][v]['F13_under_floor']) for v in ign['views']}),
    first_stars=dict(stars=first, colour_target='#E8EEF8', appear=[LAB['blue_hour_start'] + 1.0, LAB['blue_hour_start'] + 4.0], peak=0.55,
                     out_s=0.8, note='天顶附近十几颗真实的星（BSC，≤ 4.6 等，仰角 > 62°）。993.06 + 1 起 3 秒出现；1001.21 起按离天顶由远到近一颗颗熄灭（每颗 0.8 s），天顶那一颗在 1009.21 熄灭，同一刻天问开始对焦（圣经 §3.3）。'),
    question_stars=dict(stars=qstars, appear='F13 那一帧（与所有星同时）', colour='#F2F6FF', fwhm_px=1.6,
                        note='每个字心一颗（Fonts/strings_all.json P09_Tianwen 的排版：方位 0°、仰角 +8°、50 m、2.2°）；亮度按笔画数（HDR 峰值 6 × (0.4 + 0.6 × 笔画/12)）；留到第 9 幕结束。字本身由字体套件的诗句系统在 1.2 s 内暗下。'),
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
