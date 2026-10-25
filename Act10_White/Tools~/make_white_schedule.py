#!/usr/bin/env python3
"""
蓝白 · 第 12 面 → 白 → 第 10 幕 → 白收缩进灯里：全部曲线（唯一的数据源 -> Act10_White/WhiteSchedule.json）

依据：圣经 v2.1 §6·9 → 10（冲击 1.2 s + 膨胀 6 s + 保持 1.53 s + 遮罩 3 s，结束在 F16），§6·10（白 29.15 s，±2 % 0.1 Hz 呼吸），
§6·10 → 11（白收缩进灯里，8 s），§1.4（桌面镜头层），§1.8（峰值、爬升律、遮罩填值补偿），calib_final.md §D（遮罩填值），
grades_final.json helpers（EXPO_UP、WHITE_SAT、WHITE_BLOOM、LENS_*）。

所有时刻从标签算：第 12 面的穿越来自 Mirrors/MirrorSchedule.json（它从 cues.json 算），F16 / F16r / F_end 来自 cues.json。
用法：~/bpy/bin/python make_white_schedule.py
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
cues = json.load(open(os.path.join(ROOT, 'FromLocal', 'cues.json'), encoding='utf-8'))
F = {k: v['t'] for k, v in list(cues['F'].items()) + list(cues['F_sub'].items())}
mir = json.load(open(os.path.join(ROOT, 'Mirrors', 'MirrorSchedule.json'), encoding='utf-8'))
M12 = mir['mirrors'][11]['t_cross']
F16 = F['F16']; F16r = F['F16r']; FEND = F['F_end']
B_S9B = 0.30                                   # postExposure of S9a / S9b (both +0.30): the base b for EXPO_UP
T_IMP, T_SW = 1.2, 6.0
t_imp_end = round(M12 + T_IMP, 2)              # 1138.78
t_sw_end = round(t_imp_end + T_SW, 2)          # 1144.78 = the hush begins
t_mask0 = round(F16 - 3.0, 2)                  # 1146.31
t_hold = round(t_mask0 - t_sw_end, 2)          # 1.53
SILENCE = 5.0
t_sil_end = round(FEND + SILENCE, 2)           # 1178.46
t_shrink_end = round(t_sil_end + 8.0, 2)       # 1186.46
assert abs(t_imp_end - 1138.78) < 0.011 and abs(t_sw_end - 1144.78) < 0.011 and abs(t_mask0 - 1146.31) < 0.011, (t_imp_end, t_sw_end, t_mask0)
assert abs(t_sil_end - 1178.46) < 0.011

def w_up(dev, b): return dev / (4.0 - b)

def hexlin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [round(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4, 6) for x in c]
def fill(hexev):
    h, ev = hexev.split('@') if '@' in hexev else (hexev, '+0')
    lin = hexlin(h.strip()); s = 2 ** float(ev)
    return dict(set=hexev.strip(), linear_rgb=[round(x * s, 6) for x in lin])

FILL = {
    'S9b_WHITESAT': dict(desktop=fill('#D6F5FF @ +0.57'), vr=fill('#D5F6FF @ +0.06'), screen=dict(desktop='#E8F1F5', vr='#D7E3E8')),
    'S10': dict(desktop=fill('#D5F0FF @ +1.42'), vr=fill('#D3F0FF @ +0.83'), screen=dict(desktop='#E8F1F5', vr='#D7E3E8')),
    'S11': dict(desktop=fill('#D5F4FF @ +1.20'), vr=fill('#D4F5FF @ +0.66'), screen=dict(desktop='#E8F1F5', vr='#D7E3E8')),
}

out = dict(
    about='蓝白 · 白（第 12 面 → F16 → 第 10 幕 → 收缩进灯里）的全部曲线。圣经 v2.1 §6·9→10、§6·10、§6·10→11、§1.8、calib_final §D。'
          '由 Act10_White/Tools~/make_white_schedule.py 生成，不要手改。时刻都由标签算（第 12 面来自 Mirrors/MirrorSchedule.json）。',
    version='1.0',
    labels=dict(mirror12=M12, impact_end=t_imp_end, swell_end_hush=t_sw_end, mask_start=t_mask0, F16_cut2=F16, F16r=F16r,
                playback_fade=[round(F16r + 0.2, 2), FEND], file_end=FEND, silence_end=t_sil_end, shrink_end=t_shrink_end),
    curve_rules=dict(knots='[t, value]，相邻节点之间线性插值（EV 线性的量直接给 EV；权重给 weight）；第一个节点之前取第一个值、最后一个之后取最后一个值',
                     ev_linear='EXPO_UP 的 ΔEV 在节点之间线性 → w = ΔEV / (4 − b) 也线性：EV 线性的包络保持 EV 线性（§1.4）'),
    exposure=dict(helper='EXPO_UP', base_b=B_S9B, formula='w = ΔEV / (4 − b)',
                  dEV_knots=[[M12, 0.0], [t_imp_end, 1.0], [t_sw_end, 2.4], [t_mask0, 2.4], [F16, 2.4]],
                  weight_check=dict(impact_end=round(w_up(1.0, B_S9B), 3), swell_end=round(w_up(2.4, B_S9B), 3)),
                  at_F16='同一帧：EXPO_UP → 0（ΔEV 归零），场景 S9a/S9b → 0、S10 → 1；遮罩此刻全满，填值同帧换成 S10 那一行，屏幕一码不动',
                  after_silence=dict(t=t_sil_end, dEV=1.0, weight=round(w_up(1.0, -0.15), 3), decay_s=4.0, base_b=-0.15,
                                     note='10 → 11：遮罩全满时同帧硬切 S10 → S11，EXPO_UP +1.0（w 0.241，S11 的 b = −0.15）且填值同时 × 2^−1.0；之后 4 s 线性衰减（变暗，免费）')),
    white_sat=dict(knots=[[M12, 0.0], [t_imp_end, 0.42], [t_sw_end, 1.0], [F16 - 1e-3, 1.0], [F16, 0.0]], note='F16 遮罩全满同帧硬切到 0'),
    white_bloom=dict(knots=[[M12, 0.0], [t_imp_end, 0.5], [t_sw_end, 1.0], [t_mask0, 1.0], [F16, 0.0]],
                     mask_rule='遮罩的 3 s 里随遮罩 EV 线性 1 → 0（= 1 − x，x = 遮罩的归一化时间；遮罩本身永远不 bloom）'),
    lens_desktop=dict(LENS_CLEAN=[[t_imp_end, 1.0], [t_sw_end, 0.0], [t_sil_end - 1e-3, 0.0], [t_sil_end, 1.0]],
                      LENS_ARCHIVE=[[t_sil_end - 1e-3, 0.0], [t_sil_end, 1.0]],
                      note='白不是被拍下来的，没有暗角：两层在膨胀的 6 s 里降到 0（LENS_ARCHIVE 此时本来就是 0）。10 → 11 在遮罩全满下同帧回到 1（假醒是档案）。'
                           'LENS_CLEAN 回到 1 的时刻圣经没写（§1.4 只说桌面恒为 1、白的膨胀里降到 0），这里取遮罩下的 1178.46。VR 里两层不存在。'),
    mirror13_face_extra=dict(EV_knots=[[t_imp_end, 0.0], [t_mask0, 2.7]], shape='EV 线性 0.36 EV/s（r3 C3：+3 → +2.7，含 WHITE_BLOOM 的向下看 ≤ 220）；冲击的 1.2 s 里不升',
                             multiplier='镜面自发光 × 2^EV（只乘第 13 面的自发光项，不乘反射项）', see='Mirrors/MirrorSchedule.json mirrors[12].face_emission_extra'),
    overlay=dict(
        shader='Lanbai_Overlay v2（会话「门内」，Overlay/；没推之前照圣经 §1.8 的接口：_Color rgb = HDR 填色、a = 不透明度；球跟头部位置；物体空间抖动）',
        mask_in=dict(t=[1144.11, F16], ruling='C1 = B（总导演 10-25），10-25 再放软：侧上方 1 s ≤ 0.95 EV',
                     curve='EvOverlayAlpha(clamp01((t − 1144.11 − lead(dir)) / 5.2), Lscene, Lwhite, Lscene, Lwhite)',
                     Lscene=0.06, Lscene_note='最暗的视向实测：侧上方 +30°（yaw 90°）L 0.058（384 px）/ 0.060（1920×1080），Mirrors/Docs~/flashcheck/c1_views_1146.31.json',
                     lobes=[dict(dir=[0.0, 0.1, 1.0], half_angle_deg=25, lead_s=1.00, note='正前方：1146.32 才看得出变白（卡在白的那一拍）；F16 时还差 0.31 EV，剪 2 一步补齐')],
                     lead_else_s=0.0, soft_edge_deg=30, T_s=5.2,
                     fill_row='S9b_WHITESAT', fill_times_2pow_minus_dEV=True),
        hold=dict(t=[F16, t_sil_end], alpha=1.0, fill_row='S10', breath=dict(amount=0.02, hz=0.1, note='±2 %、0.1 Hz；乘在填色上'),
                  peak_hold_s=round(t_sil_end - F16, 2), rule='峰值保持 ≤ 30 s（只算 F16 → 静默结束）；本地若延长播放淡出，必须同步缩短 5 s 静默'),
        shrink=dict(t=[t_sil_end, t_shrink_end], fill_row='S11', fill_times_2pow_minus_dEV=True,
                    alpha='按世界方向错开的 EV 线性遮罩（亮的东西先出现）：alpha(dir, t) = EvOverlayAlpha(clamp01((t − t0 − lead(dir)) / T), Lwhite, Lscene11, Lscene11, Lwhite)',
                    lead_order=['车厢管灯（车厢顶棚的两排灯管方向）', '路灯（侧窗、地平线上方 0–25°）', '头顶的海（天顶）'],
                    lead_s=[0.0, 1.5, 3.0], T_s=5.0,
                    lobes_note='方向由第 11 幕（灯与假醒）给：管灯在车里是固定的（相对车），路灯与海在第 11 幕的布局里。v2 遮罩若不支持按方向的 alpha，退路 = 全方向同一条 8 s 曲线（变暗免费，爬升律无关）'),
        fills=FILL,
        vr_select='Networking.LocalPlayer.IsUserInVR() → vr 那一列；否则 desktop',
    ),
    renderers=dict(off_at_F16='遮罩全满时（F16）遮罩后面的一切关闭：第 9 幕的星、镜、尘、车厢（第 13 面带走座位 = 同一帧）',
                   on_at_F16_note='R_Road（干燥版）与 R_False 在第 10 幕的白里激活（归第 11 幕 / Director；这里只写时刻）',
                   activate_next=[F16, t_sil_end]),
    audio_note='音乐 F16r 和弦收，播放淡出 1170.96 → 1173.46（本地），之后 5 s 数字静默；电台噪音 1178.46 起 −40 → −30 dB（第 11 幕）',
)
json.dump(out, open(os.path.join(ROOT, 'Act10_White', 'WhiteSchedule.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote WhiteSchedule.json', t_imp_end, t_sw_end, t_mask0, F16, t_sil_end, t_shrink_end, 'w', round(w_up(1.0, B_S9B), 3), round(w_up(2.4, B_S9B), 3))
