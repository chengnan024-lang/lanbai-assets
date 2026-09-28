# -*- coding: utf-8 -*-
import json, numpy as np
from scipy.optimize import minimize, least_squares
from lutlib import ppv2, PROF
def disp_hex(lin, prof): return ppv2.srgb_to_hex(ppv2.display_of(np.asarray(lin, float), PROF[prof]))
def solve(target_hex, prof):
    t_s = np.array([int(target_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    t = ppv2.srgb_to_lin(t_s)
    f = lambda x: (ppv2.display_of(np.exp(x), PROF[prof]) - t_s) * 255
    cost = lambda x: float((f(x) ** 2).sum())
    starts = [np.log(np.maximum((t * (1 - m) + t.mean() * m) * sc, 1e-6)) for m in (0, .3, .6) for sc in (.5, 1, 2, 4)]
    x0 = min(starts, key=cost)
    r = minimize(cost, x0, method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-5, maxiter=5000))
    r2 = least_squares(f, np.clip(r.x, np.log(1e-7) + 1e-6, np.log(80) - 1e-6), bounds=(np.log(1e-7), np.log(80)))
    x = np.exp(r2.x); return x, np.abs(f(r2.x)).max()
def set_str(x):
    m = x.max()
    return ppv2.lin_to_hex(x) if m <= 1.0 else '%s @ +%.2f' % (ppv2.lin_to_hex(x / m), np.log2(m))
K = lambda k: ppv2.kelvin_hex(k)
TUBE = '#E4F1F3'
LIGHTS = [
 ('S1', '主光：站牌灯管，路面灯池中心（灰卡朝上）', TUBE, 1.00),
 ('S1', '主光：站牌灯管照在站牌面上（白卡贴站牌；站牌珐琅新反照率 #DDE9EA → E 1.47）', TUBE, 1.47),
 ('S1', '补光：开着的车门漏光（冷，R_Stop 里的烘焙面光），路肩', TUBE, 0.35),
 ('S1', '车头灯（卤素 3200 K，实时双瓣聚光，只此一份）前方 10 m 路面', K(3200), 0.90),
 ('S1', '仅环境光 Trilight sky #1A2438（灰卡朝上）', '#1A2438', 1.00),
 ('S2', '车厢灯管（_CabinTubeLM），座垫上；头像补光按同一读数', TUBE, 0.80),
 ('S2', '钠灯扫光峰值（2050 K），座椅顶', K(2050), 0.90),
 ('S3', '主光：月光 9000 K，平行光（全片亮度基准 E=1；方位 -12° 仰角 +8°）', K(9000), 1.00),
 ('S3', '白卡（0.80）朝月：必须等于最亮云卡顶部 ±10', K(9000), 1.00),
 ('S4', '月光（轮廓光源），灰卡朝月', K(9000), 1.00),
 ('S4', '裂口光 #A99DE1，平行光，灰卡朝裂口', '#A99DE1', 0.80),
 ('S4', '云海反光（自下而上 #5A6488），灰卡朝下', '#5A6488', 0.24),
 ('S4', '灯管熄灭前基准', TUBE, 0.25),
 ('S4', '天窗光斑（U8–U9，叠加卡；白卡读数）', '#E2E8F3', 1.00),
 ('S4c', '门内环境 _Udon_CabinAmbient #B5C3DB ×0.30（灰卡朝前）', '#B5C3DB', 0.30),
 ('S6', '主光：晨日 3200 K，仰角 6°', K(3200), 3.00),
 ('S6', '白卡（0.80）朝日', K(3200), 3.00),
 ('S6', '天光环境 Trilight sky #5A78B8（灰卡朝上）', '#5A78B8', 1.00),
 ('S6', '车厢环境 #98A4B8 ×0.5（灰卡朝前）', '#98A4B8', 0.50),
 ('S7a', '透过水面的日光 #B0D9F2（灰卡朝上）', '#B0D9F2', 1.60),
 ('S7a', '浅水车厢环境 #6186A7 ×0.6', '#6186A7', 0.60),
 ('S7b', '青铜灯焰暖光 2200 K，距灯 2 m', K(2200), 1.20),
 ('S7b', '同一盏灯的靛色远光 #2A557B，距灯 8 m', '#2A557B', 0.60),
 ('S8', '主/逆光：暮日 2400 K 在地平线，灰卡朝日', K(2400), 2.20),
 ('S8', '白卡（0.80）朝暮日', K(2400), 2.20),
 ('S8', '车厢环境 #828BAA ×0.45', '#828BAA', 0.45),
 ('S9a', '星光环境 Trilight sky #1A2A4A（灰卡朝上）', '#1A2A4A', 1.00),
 ('S9a', '镜线扫过时的点光 8000 K 峰值', K(8000), 0.30),
 ('S12', '主光：站牌灯管（同 S1）', TUBE, 1.00),
]
UNLIT = [
 ('S1', '雾色（Exp）= 地平线', '#121A28'), ('S1', '天顶（阴云夜）', '#070B14'), ('S1', '朝镇方向的地平线（钠光照亮的云底）', '#241E22'),
 ('S1', '灯管发光体核心', '#EEF5F7'), ('S1', '远镇钠灯点', '#DC8F51'), ('S1', '灯锥内的雨丝', '#9AA8B4'), ('S1', '尾灯', '#B2252C'),
 ('S2', '雾色', '#0A0F18'), ('S2', '天', '#05080F'), ('S2', '收音机表盘', '#E19867'), ('S2', '钠灯灯头经过', '#EDAD77'),
 ('S3', '光之海 钠灯', '#E8A050'), ('S3', '天顶', '#08101F'), ('S3', '地平线（背月）= 云上雾色', '#111B30'), ('S3', '月旁天光（10°）', '#26344F'),
 ('S3', '月面（不裁切，可见月海）', '#EAEEF4'), ('S3', '月晕（6°）', '#5A6A88'), ('S3', '月光之路核心', '#DDE7F5'), ('S3', '入云白雾', '#4A5568'),
 ('S3', '橙色云底（城市照亮）', '#7A4A2A'), ('S3', '远处裂口（一笔白线，极淡紫晕）', '#D2CEE4'),
 ('S4', '虚空天色（>60° 或 >+35°）', '#070A14'), ('S4', '光雾带 裂口旁 = 该方位雾色', '#484D63'), ('S4', '光雾带 50° 外', '#2A3041'),
 ('S4', '全局雾色 RenderSettings（光雾带 30° 处）', '#353B4F'),
 ('S4', '紫晕（呼吸中值）', '#5B57A1'), ('S4', '光束（两束叠加处）', '#31335A'),
 ('S4', '裂口下云海（叠加卡）', '#495270'), ('S4', '裂口边缘辉光', '#C0B9E4'), ('S4', '裂口纤维', '#E2E8F3'), ('S4', '裂口核心：未染的白', '#F5F2EC'),
 ('S4c', '第 1 重光唇之间的雾', '#1D2336'), ('S4c', '第 8 重光唇之间的雾', '#53606E'),
 ('S4c', '光唇纤维 第 1 重', '#E6E1F2'), ('S4c', '光唇纤维 第 4 重', '#D9DFEE'), ('S4c', '光唇纤维 第 8 重（瓶覗）', '#C2D8E2'),
 ('S4c', 'Lichtchen 表盘（提亮一档后；S4c 下可达的最饱和值）', '#F2B169'), ('S4c', '前方暖白光点', '#FFF1DC'),
 ('S6', '天顶', '#3E64A6'), ('S6', '地影带', '#8C98B8'), ('S6', '金星带（珍珠）', '#CFB7B7'), ('S6', '日侧地平线', '#F2C79A'), ('S6', '雾色', '#C4B8C0'),
 ('S6', '云影（v2 云卡目标）', '#8593AA'), ('S6', '脚下远海', '#1C3D63'), ('S6', '日盘（小面积，可裁切）', '#FFF3DE'),
 ('S7a', '斯涅尔窗核心', '#E6F3F8'), ('S7a', '浅水雾 0–15 m', '#507DA6'), ('S7a', '光柱（叠加结果）', '#90BFE9'), ('S7a', '全反射暗镜', '#11395E'),
 ('S7a', '水下天空渐变 上', '#94CAE9'), ('S7a', '水下天空渐变 中', '#3E6486'), ('S7a', '焦散（座椅上）', '#ACD4ED'), ('S7a', '生物荧光', '#8AC6FF'), ('S7a', '海雪', '#697987'),
 ('S7b', '水雾 15–60 m', '#1A4163'), ('S7b', '深水雾（宫殿）', '#04121E'), ('S7b', '深渊', '#02070F'), ('S7b', '灯焰', '#FFC46A'),
 ('S7b', '灯晕卡中段（靛）', '#2A557B'), ('S7b', '船体生物光', '#8AC6FF'), ('S7b', '海底玫瑰光（7c 末）', '#2A1E30'),
 ('S8', '头顶海水', '#10263F'), ('S8', '天花近地平镜光', '#C98A7A'), ('S8', '天缝', '#F2A56B'), ('S8', '日线', '#FFE2B0'), ('S8', '玫瑰带', '#E7A0A0'),
 ('S8', '中天 靛灰', '#808AB2'), ('S8', '天顶', '#3D4A80'), ('S8', '云影（v2 云卡目标）', '#363D59'), ('S8', '雾色 8-i', '#B77F78'),
 ('S8', '雾色 8-ii（另一片天，地平线处）', '#B98A86'), ('S8', '另一片天 天底', '#2E3C66'),
 ('S8b', '蓝时 最纯的蓝', '#2E4F8A'), ('S8b', '蓝时 地平线', '#6F86B0'),
 ('S9a', '点燃前的黑（可达值）', '#04060E'), ('S9a', '星空底', '#08112A'), ('S9a', '银河漫射最亮处', '#6F82A0'), ('S9a', '银心暖尘', '#C8B79A'), ('S9a', '镜线', '#DCE8FF'),
 ('S9b', '第 13 面镜的远缘（F14 起）', '#4E545E'), ('S9b', '星尘', '#CDBF9C'),
 ('S10', '藍白遮罩球（桌面）', '#E8F1F5'), ('S10', '藍白遮罩球（VR）', '#D7E3E8'), ('S10', '第二次白', '#A3B4BE'),
 ('S11', '头顶的海', '#0F2438'), ('S11', '海面钠光闪烁', '#D08A59'), ('S11', '雾色', '#0A0F18'),
 ('S12', '天顶（云开）', '#070B14'), ('S12', '藍白带 起', '#1B2431'), ('S12', '藍白带 8 分钟后', '#33465B'), ('S12', '雾色', '#111B2A'),
 ('S12', 'Lichtchen 核心', '#FCF5DA'), ('S12', 'Lichtchen 光晕（α 0.30）', '#EBECA6'), ('S12', '田上萤火虫', '#DEEA88'), ('S12', '远镇灯', '#E0914A'),
]
# overlay fills under the LIVE grade (critique_feasibility B-3). fill_live = value below x 2^(-dEV of the exposure helpers), every frame.
import copy
def _mix(base, **kw):
    p = copy.deepcopy(PROF[base]); p.update(kw); return p
LIVE = [
 ('9→10 遮罩阶段', 'S9b + WHITE_SAT(1)', _mix('S9b', saturation=-30), '#E8F1F5', '藍白（桌面）'),
 ('9→10 遮罩阶段', 'S9b + WHITE_SAT(1)', _mix('S9b', saturation=-30), '#D7E3E8', '藍白（VR）'),
 ('10 保持', 'S10', PROF['S10'], '#E8F1F5', '藍白（桌面）'),
 ('10 保持', 'S10', PROF['S10'], '#D7E3E8', '藍白（VR）'),
 ('10→11 收缩', 'S11', PROF['S11'], '#E8F1F5', '藍白（桌面），遮罩在 S11 下收缩'),
 ('10→11 收缩', 'S11', PROF['S11'], '#D7E3E8', '藍白（VR），遮罩在 S11 下收缩'),
 ('11→12 升起', 'S11', PROF['S11'], '#A3B4BE', '第二次白（升起与保持）'),
 ('11→12 收缩', 'S12', PROF['S12'], '#A3B4BE', '第二次白（硬切到 S12 之后收缩）'),
 ('4c→5 黑', 'S4c', PROF['S4c'], '#030409', '投入之黑'),
 ('5→6 黑', 'S6', PROF['S6'], '#030409', '投入之黑（硬切到 S6 之后）'),
]
def main():
    out = {'lights': [], 'unlit': [], 'ramp': {}}
    md = ['### A. 灰卡 / 白卡目标（灰卡 = Standard, albedo #767676 = 0.18 linear, smoothness 0；白卡 albedo #E6E6E6 ≈ 0.80）', '',
          '| 幕 | 光的角色 | 光色（Unity Light.color） | E（线性照度） | Inspector 强度（平行光，gamma 规则 E^(1/2.2)） | 截图应读到 |', '|---|---|---|---|---|---|']
    for sc, role, col, E in LIGHTS:
        alb = 0.80 if '白卡' in role else 0.18
        r = disp_hex(alb * ppv2.hex_to_lin(col) * E, sc)
        md.append('| %s | %s | `%s` | %.2f | %.2f | `%s` |' % (sc, role, col, E, E ** (1 / 2.2), r))
        out['lights'].append(dict(scene=sc, role=role, colour=col, E=E, inspector=round(E ** (1 / 2.2), 3), reads=r))
    md += ['', '### B. 无光照 / 自发光 / 雾：屏幕目标 → Unity 里要填的值（在该幕 grade 下）', '',
           '`#RRGGBB @ +n` = HDR 颜色：基色 + HDR 取色器 Intensity +n（×2^n）。无 @ 的是普通取色器 hex。', '',
           '“×T0” = 填值最大通道 ÷ 该 profile 的 bloom 起点 T0：< 1 不 bloom，1–2 微晕，> 2 明显发光。', '',
           '| 幕 | 元素 | 屏幕必须显示 | Unity 里填 | ×T0 | 误差 |', '|---|---|---|---|---|---|']
    from lutlib import GF
    for sc, el, tgt in UNLIT:
        x, err = solve(tgt, sc)
        note = '%.1f' % err if err < 3 else '%.1f（最接近可达：%s）' % (err, disp_hex(x, sc))
        r = x.max() / GF['profiles'][sc]['bloom_T0_scene_linear']
        md.append('| %s | %s | `%s` | `%s` | %.2f | %s |' % (sc, el, tgt, set_str(x), r, note))
        out['unlit'].append(dict(scene=sc, element=el, display=tgt, set=set_str(x), xT0=round(float(r), 2), err=round(float(err), 1)))
    md += ['', '### C. 调色测试卡：11 块无光照灰片 0.18 × 2^k（k = -6..+4），截图须 ±3 以内', '',
           '| Profile | -6 | -5 | -4 | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4 |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for k in [k for k in PROF if not k.startswith('_')]:
        row = [disp_hex(np.full(3, 0.18 * 2.0 ** e), k) for e in range(-6, 5)]
        out['ramp'][k] = row
        md.append('| %s | %s |' % (k, ' | '.join('`%s`' % h for h in row)))
    md += ['', '### D. 全屏遮罩球的填色：按“当时正在起作用的 grade”求解（v2 新增）', '',
           '遮罩球在 PPv2 之前渲染，会被调色。遮罩可见期间，Udon 每帧设 `overlay.rgb = 下表填值 × 2^(-ΔEV)`（ΔEV = EXPO_UP/DOWN 当前加上的曝光）；'
           '遮罩全满时换 grade 一律“同一帧硬切”，并在同一帧把填值换成新 profile 那一行。', '',
           '| 时刻 | 起作用的 grade | 屏幕必须显示 | 填（ΔEV = 0 时） | 误差 |', '|---|---|---|---|---|']
    out['overlay'] = []
    for when, gname, p, tgt, role in LIVE:
        PROF['_live'] = p
        x, err = solve(tgt, '_live')
        note = '%.1f' % err if err < 3 else '%.1f（最接近可达：%s）' % (err, disp_hex(x, '_live'))
        md.append('| %s | %s | `%s` %s | `%s` | %s |' % (when, gname, tgt, role, set_str(x), note))
        out['overlay'].append(dict(when=when, grade=gname, display=tgt, role=role, set=set_str(x), err=round(float(err), 1)))
    PROF.pop('_live', None)
    open('../calib_final.md', 'w').write('\n'.join(md) + '\n')
    json.dump(out, open('../calib_final.json', 'w'), ensure_ascii=False, indent=1)
    print('\n'.join(md))

if __name__ == '__main__':
    main()
