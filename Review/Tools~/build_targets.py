# -*- coding: utf-8 -*-
"""Build Review/targets.json from ART_BIBLE v2.1 (§1.3, §2.2, §3, §6 palettes, Appendix B) + Gate README §12 (v2.3).
Every number here is quoted from the bible; the 'src' field says where. Re-run after the bible changes."""
import json, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bible = open(os.path.join(ROOT, 'Art/ART_BIBLE.md'), encoding='utf-8').read().splitlines()

def palette(line_no):
    s = bible[line_no - 1]
    s = s.split('：', 1)[1]
    out = []
    for part in re.split(r' · ', s):
        hs = re.findall(r'#[0-9A-Fa-f]{6}', part)
        if not hs: continue
        name = re.sub(r'[*`（）()]|#[0-9A-Fa-f]{6}', '', part).strip(' 。')
        for h in hs: out.append({'name': name[:24], 'hex': h.upper()})
    return out

PAL_LINES = {'1': 728, '2': 787, '3': 857, '4': 962, '4c': 1027, '5': 1053, '6': 1123, '7a': 1195,
             '7b': 1274, '8': 1380, '9': 1480, '11': 1560, '12': 1624}
EXTRA = {'8b': [{'name': '最纯的蓝带', 'hex': '#2E4F8A'}, {'name': '天缝/地平线', 'hex': '#6F86B0'},
                {'name': '天顶', 'hex': '#16223F'}, {'name': '另一片天天底', 'hex': '#1A2A4E'}, {'name': '第一批星', 'hex': '#E8EEF8'}],
         '10': [{'name': '藍白 桌面', 'hex': '#E8F1F5'}, {'name': '藍白 VR', 'hex': '#D7E3E8'}, {'name': '第二次白', 'hex': '#A3B4BE'}],
         '7c': [{'name': '7c 玫瑰雾 F8b', 'hex': '#2E2228'}, {'name': '7c 末雾', 'hex': '#3A2629'}, {'name': '深水雾', 'hex': '#04121E'},
                {'name': '灯焰', 'hex': '#FFC46A'}, {'name': '暮日弧(窗里)', 'hex': '#F2A56B'}]}

# ---- fixed camera: bible §1.5 / §9 : desktop 1920x1080, hFOV 90, seated hero eye, straight ahead
CAM = {'res': [1920, 1080], 'hfov_deg': 90, 'eye': 'hero seat (Gate/GateLayout_v2.json cameras.U7 ≈ (0.55,1.70,2.05)); README must state which',
       'grade': 'PPv2 HDR + Neutral, the act profile at weight 1, bloom on (APL includes bloom)'}

# ---- §2.2 table: segments with APL (desktop, straight ahead, incl. bloom). tol ±15% (§1.5 step 4)
SEG = [
 # key, act, name, t0, t1, APL start, APL end/key values, profile, main light, note
 ('1',   '1',  '站牌', None, 0, [22], 'S1', '藍白灯管 ≈7000 K', '雨夜里唯一一座光的小岛'),
 ('wait','1',  '静候 U0', 0, 17.5, [22], 'S1→S2', '', '声音先到，车不动'),
 ('2',   '2',  '夜路', 17.5, 39.1, [32, 30], 'S2', '管灯+钠灯扫光 2050 K', '全片颜色最少'),
 ('2d',  '2',  '暗段', 39.1, 50.3, [24, 22], 'S2(S3→0.3)', '只有车头灯', '低谷'),
 ('3a',  '3',  '一次升起', 50.3, 75.8, [24, 27], 'S2→S3 0.3', '城市钠光自下', '大地从脚下落走'),
 ('3b',  '3',  '云底', 75.8, 99.5, [28, 34], 'S3 0.3', '橙色云底', '我欲 / Je lieber'),
 ('3t',  '3',  '触云', 99.5, 107.5, [34, 62], 'S3', '散射', '天窗先白'),
 ('3i',  '3',  '云中', 107.5, 129.1, [62], 'S3 0.3→1', '散射 暖→冷', '云中 APL ≥ 58（E13）'),
 ('3c',  '3',  '月之路', 129.1, 150.3, [50], 'S3→S4', '月 9000 K', 'EV0 基准'),
 ('4',   '4',  '触手之门', 150.3, 179.55, [38, 40], 'S4', '靛紫裂口光 + 月轮廓', '门的 v2.3：主视觉 32–36、U7 透过玻璃 33–38、U8 前方 ≤ 42 不算白'),
 ('4c',  '4c', '门内', 179.55, 248.64, [30, 55], 'S4c', '纤维白→瓶覗 + 表盘', '暗的恩典'),
 ('5',   '5',  '投入', 248.64, 251.64, [4], 'S4c→S6(黑下)', '无', '全片唯一的黑'),
 ('6',   '6',  '晨', 251.64, 281.86, [110], 'S6', '晨日 3200 K', '比门内 +2.2 EV'),
 ('6b',  '6',  '云峡', 281.86, 305.4, [108, 96], 'S6', '晨日沿峡谷', ''),
 ('6c',  '6',  '云盖之下', 305.4, 337.0, [74, 92], 'S6', '云盖下天光→低日', '一次小的呼吸'),
 ('6d',  '6',  '海镜', 337.0, 363.26, [94, 90], 'S6', '晨日+镜面', '坠入天空'),
 ('7a',  '7a', '被海接住', 363.26, 474.36, [85, 60], 'S7a', '透过水面的日光', '群青'),
 ('7aw', '7a', '水柱', 474.36, 558.86, [60, 46, 35, 25], 'S7a→S7b', '最后一道光柱', '越响越暗'),
 ('7as', '7a', '播种', 558.86, 644.96, [25, 16], 'S7a→S7b', '生物光', ''),
 ('7b1', '7b', '近', 644.96, 668.6, [16, 18], 'S7b', '灯列', ''),
 ('7b2', '7b', '行列', 668.6, 735.56, [18, 20], 'S7b', '宫灯 2200 K 自下', '朱与靛'),
 ('7b3', '7b', '门前', 735.56, 796.86, [20], 'S7b', '开着的门', ''),
 ('7b4', '7b', '离开', 796.86, 835.16, [20, 18], 'S7b', '宫灯在上', ''),
 ('7c',  '7c', '海底即天', 835.16, 922.36, [18, 30, 34], 'S7b', '玫瑰光自下', '暗的低谷保持到出海'),
 ('8',   '8',  '暮', 922.36, 987.06, [34, 80, 76, 90], 'S7b→S8', '暮日 2400 K 眼高', '论点之帧 APL≈76；另一片天 90'),
 ('8b',  '8b', '蓝时', 987.06, 1001.21, [88, 50, 40], 'S8→S8b', '只有天', ''),
 ('9a',  '9',  '天问', 1001.21, 1018.21, [40, 6], 'S8b→S9a', '无', '越响越暗'),
 ('9b',  '9',  '一瞬', 1018.21, 1032.41, [6, 30], 'S9a', '星光', ''),
 ('9c',  '9',  '十三面镜', 1032.41, 1149.31, [30, 73], 'S9a→S9b', '镜光+银河', '黑保持黑'),
 ('10',  '10', '白', 1149.31, 1178.46, [239], 'S10', '藍白场', 'VR 224'),
 ('11',  '11', '假醒', 1178.46, 1240.46, [30], 'S11=S2', '= 第 2 幕', ''),
 ('w2',  '11', '第二次白', 1240.46, 1254.96, [30, 176], 'S11→S12', '', ''),
 ('12',  '12', '醒', 1254.96, None, [24, 27], 'S12', '藍白灯管', ''),
]

# ---- per-act rules (§1.3, §6)
ACT = {
 '1':  dict(profile='S1', warm_ok=['站灯/车头灯/尾灯/远钠'], violet='global', floor='#04060B', lens='LENS_CLEAN',
           brightest='站灯（灯管与站牌）', avoid='暖色灯泡；候车亭；天空结构/星/月；到处均匀的雨；黄线；品牌/车牌/可读时刻表；复古滤镜'),
 '2':  dict(profile='S2', violet='global', floor='#04060B', lens='LENS_CLEAN+ARCHIVE', brightest='车灯隧道 / 钠灯',
           avoid='发动机声；扫光对拍子；可读的仪表数字；任何人；天空结构；暖黄车厢灯；离车窗 4–5 m 的亮杆'),
 '3':  dict(profile='S3', violet='global', floor='#04060B', brightest='月（与远处的裂口线）',
           avoid='U6k 前出现月亮；137.10 前出现触手；云中 APL < 58；网格状城市；冷色为主的灯海；月面裁成白饼；雾色与地平线不一致；紫色的远处裂口'),
 '4':  dict(profile='S4', violet='act4', floor='#04060B', brightest='裂口',
           accept={'APL': [36, 42], 'APL_v23_keyart': [32, 36], 'APL_v23_U7_through_glass': [33, 38], 'APL_v23_U8fwd_excl_white_max': 42,
                   'luma_lt12_max_pct': 40, 'violet_C30_max_pct': 10, 'depth_ladder_Lstar_v23': {'near': [3, 6], 'colossus': [9, 14], 'lit_mid_crowns': [16, 22], 'haze_band': [22, 28]}},
           avoid='平行边的发光条；饱和兰花紫；黑压黑；比天还亮的远处剪影；等距环节；两个等亮圆盘同在挡风玻璃 >15 s；触手碰车；红色；一排一样的卷尖；清漆感；鳞片；紫溢出到本幕以外'),
 '4c': dict(profile='S4c', violet='act4', floor='#04060B', brightest='门内的暖白点',
           avoid='前方触手；星；文字；满屏白；同心的椭圆/杏仁形隧道；大面积的紫'),
 '5':  dict(profile='S4c/S6', violet='global', floor='#030409', brightest='（黑）', avoid='尖叫；音效；bloom 覆盖；下落尘粒；立刻切到晨光'),
 '6':  dict(profile='S6', violet='act6', floor='#04060B', brightest='太阳（车门里）；6c 云盖下被斜光照亮的远处海面；太阳重现；海镜（倒影太阳比日盘低 ≥ 1.3 EV）',
           avoid='发褐/发灰/发紫的云影；粉色的天；太阳正对挡风玻璃中央；天空裁切；镜头光斑；画出来的鸟；车厢亮起来；晨里放字；F1 之前露出海；海镜里第二个日盘'),
 '7a': dict(profile='S7a', violet='global', floor='#030B0F', brightest='斯涅尔之窗',
           avoid='水下滤波；青绿/水族箱色（群青，不是青绿）；鲸/神灵；水下满屏发白；焦散永远均匀；水柱与播种里只有变暗；播下的光闪烁或一起熄灭'),
 '7b': dict(profile='S7b', violet='global_except_cowrie', floor='#04060B', brightest='宫灯 / 门光',
           avoid='青橙配色；紫禁城/明清样式；龙雕像、神灵、人、字；满画面的朱红；宫殿内部有东西；第二个物种'),
 '7c': dict(profile='S7b', violet='global', floor='#04060B', brightest='7c 窗里的日弧',
           avoid='紫色的雾（h 290–325 且 C* > 15）；窗里第二个日盘；出海前整片亮起来（预付只到 APL 34）'),
 '8':  dict(profile='S8', violet='global', floor='#04060B', brightest='日刃与日盘 → 日线',
           avoid='天空之镜（表面、波纹、完全对称的倒影云）；紫色中天；阴影发暖；东西穿过日线；鸟；两个焦点；天花与天空不接；VRChat 镜子；天花硬边；变形不止一次'),
 '8b': dict(profile='S8b', violet='global', floor='#04060B', brightest='天本身（最纯的蓝）', avoid=''),
 '9':  dict(profile='S9a/S9b', violet='global', floor='#04060E', brightest='天问 → 上升的镜线',
           avoid='奶灰的深空；流星；闪烁；NASA 图以外的星云颜色；镜子碰车；镜子穿过后继续挡天；第 13 面之前带走座位；文字粒子化'),
 '10': dict(profile='S10', violet='global', floor=None, brightest='白本身', avoid='#FFFFFF；线性 alpha 淡到白；白里有任何形状或字；遮罩下慢慢换 grade'),
 '11': dict(profile='S11', violet='global', floor='#04060B', brightest='倒挂的灯', lens='LENS_CLEAN+ARCHIVE',
           avoid='雨；湿路；门开着；管灯闪烁；任何提示；海一开始就很显眼'),
 '12': dict(profile='S12', violet='global', floor='#04060B', brightest='站灯', lens='LENS_CLEAN',
           avoid='音乐；淡到黑；完；UI 提示；自动重开；强加镜头；济慈之后的字；车开走；同步闪烁萤火虫；荧光绿 Lichtchen；藍白带亮到像日出'),
}
for k in PAL_LINES: ACT[k]['palette'] = palette(PAL_LINES[k])
for k, v in EXTRA.items(): ACT[k]['palette'] = v

GLOBAL = {
 'violet_rule': {'src': '§1.3.4', 'global': 'outside acts 4/4c: no region > 2% of frame with h_ab 290–325 AND C* > 15 (CIE Lab, D65)',
                 'act4': 'U7–U8 straight-ahead: C* > 30 violet (h 290–325) ≤ 10%; violet only near the wound',
                 'act6': 'stricter: no region > 2% with h_ab 285–330 AND C* > 12 (no lavender in dawn)',
                 'global_except_cowrie': 'as global; the cowrie gate #7A4A6E is the only allowed violet echo, small, only beside its lamp',
                 'measure': 'both whole-frame pixel fraction and largest 8-connected component (2% = 41 472 px at 1920x1080)'},
 'black_white_rule': {'src': '§1.3.5', 'rule': 'no region > 2% of frame below #030409 or above #F4F7FA; night floor #04060B; only act 5 may reach #030409; small emitters may clip',
                      'luma_floor_night': 'night lift lands input 0 at ≈ #02060C; never red = 0'},
 'one_brightest': {'src': '§1.3.1', 'rule': 'one brightest point per frame and it is where the eye should go; measure: the brightest 2000 px (and L*>85 px) sit in ONE connected cluster on the act\'s named focus'},
 'shadows_blue': {'src': '§1.3.2', 'rule': 'no warm hue in shadows (L* < 25 px: h_ab outside 20–100 or C* < 6) — even in warm scenes'},
 'warm_rationed': {'src': '§1.3.3', 'rule': 'warm only: sodium, headlights, tail lights, radio dial, warm-white point in 4c, two suns, palace lamps, Lichtchen; distant warm always small'},
 'horizon_level': {'src': '§1.3.6', 'rule': 'horizon perfectly level: fitted horizon line slope ≤ 0.1° (≈ 1.7 px over 1920 at 90° hFOV); bus never pitches/rolls'},
 'nothing_touches': {'src': '§1.3.8', 'rule': 'tentacles, mirror rims, waves never touch the bus; only light bands cross it. ≥ 8 m for tentacles, nothing within 0.3 m of the eye'},
 'top25_Lstar': {'src': 'Gate acceptance (README §10) / local metrics', 'rule': 'upper 25% of frame L* p90 — night acts ≤ 5–10 except where the act\'s light is up there (wound, sun, skylight)'},
 'palette_dE': {'src': '§1.5 law 1 (screen targets are law)', 'rule': 'for every palette swatch: nearest pixel cluster ΔE2000 ≤ 5 = on target, 5–10 = drift (minor), > 10 or swatch absent where the act needs it = blocking if it is a named role (sky, shadow, focus)'},
 'APL_tol': {'src': '§1.5 step 4', 'rule': 'APL within ±15% of §2.2 at the segment midpoint t; desktop 1920x1080 hFOV 90, straight ahead, incl. bloom'},
 'VR_peak': {'src': '§1.8', 'rule': 'VR full-frame APL ≤ 150 except the white; white desktop #E8F1F5 (239) / VR #D7E3E8 (224); held ≤ 30 s'},
 'ramp_law': {'src': '§1.8', 'rule': 'any brightening: ≤ 0.5 EV / 0.25 s, ≤ 1.0 EV / 1 s, ≤ 1.8 EV / 2 s (L floor 0.004); ≤ 2 flashes / any 1 s in any 4.4° tile; red flash rule; run Art/tools/lens_tech/flashcheck.py <dir> --fps 60 --hfov 90'},
 'poem_luma': {'src': '§1.6 / §7.2', 'rule': 'poem text screen ≤ luma 224, no glow, no outline, no shadow'},
 'albedo': {'src': '§1.6', 'rule': 'non-metal sRGB 48–231 (exceptions: black rubber/paint/linen ≥ 38; tentacles 30–44; wet asphalt/mud Lagarde); nothing > 235; bus white ≤ 218; metal albedo ≥ 150; metallic 0 or 1'},
 'text_share': {'src': '§7.4', 'rule': 'text on screen ≤ 40% of the act; no text in the first 8 s of any act, dawn F0–F1, first 8 s after leaving the sea, dusk transform, F13–F16, the white'},
 'motion': {'src': '§1.8', 'rule': 'objects passing within 20 m: ≤ 60°/s at the eye (v ≤ 1.05 d); colossi self-motion ≤ 0.5°/s; roll = pitch = 0; yaw only acts 2/11 ≤ 3°/s'},
}

out = {'_about': 'Lanbai art-review targets, generated by Review/Tools~/build_targets.py from Art/ART_BIBLE.md v2.1 (+ Gate README §12 v2.3 for act 4). '
                 'Screen targets are law (bible law 1). APL = mean Rec.709 luma of the sRGB 8-bit screenshot (0–255).',
       'camera': CAM, 'global': GLOBAL,
       'segments': [dict(key=k, act=a, name=n, t0=t0, t1=t1, APL=apl, APL_tol_pct=15, profile=p, main_light=ml, note=note,
                         t_mid=(None if t0 is None or t1 is None else round((t0 + t1) / 2, 2))) for (k, a, n, t0, t1, apl, p, ml, note) in SEG],
       'acts': ACT}
json.dump(out, open(os.path.join(ROOT, 'Review/targets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('acts', len(ACT), 'segments', len(SEG), {k: len(v.get('palette', [])) for k, v in ACT.items()})
