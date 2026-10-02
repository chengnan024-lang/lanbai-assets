# -*- coding: utf-8 -*-
"""v2.1 value score on the MEASURED timeline (seconds from departure; cues.json). Writes v21/score.png.
Same panels as bible_work/make_score.py (APL, key-light temperature, barcode, indigo ladder, cues) plus a text lane
(poems on screen) and the three cuts."""
import os, sys, numpy as np, matplotlib
HERE = os.path.dirname(os.path.abspath(__file__))
BW = os.path.join(HERE, '../../bible_work')
sys.path.insert(0, HERE); sys.path.insert(0, BW); sys.path.insert(0, os.path.join(BW, '../lens_cine'))
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from scene_data_v21 import PHASES, CUES, KEY_COLOUR, KEY_LABEL, TEXT, CUTS, SCENE_HDR
from cues_v21 import MIRRORS
import ppv2
from lutlib_core import patch_ppv2; patch_ppv2(ppv2)
fm.fontManager.addfont('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
plt.rcParams['font.family'] = ['WenQuanYi Zen Hei']; plt.rcParams['axes.unicode_minus'] = False
BG, INK, MUTED, GRID = '#0C0E13', '#E8F1F5', '#8092A4', '#1C222C'
X0, X1 = -95, 1352
def ev(apl): return 2.2 * np.log2(max(apl, 4) / 50.0)
def seg(p):
    t0, t1, lab, (a0, a1) = p[:4]; sh = p[8] if len(p) > 8 else 1.0
    x = np.linspace(0, 1, 60); return t0 + (t1 - t0) * x, a0 + (a1 - a0) * x ** sh
fig = plt.figure(figsize=(26, 12.6), dpi=110, facecolor=BG)
gs = fig.add_gridspec(7, 1, height_ratios=[4.4, 1.8, 0.42, 0.42, 0.55, 1.35, 1.25], hspace=0.08, left=0.045, right=0.99, top=0.935, bottom=0.05)
ax1 = fig.add_subplot(gs[0]); axs = [ax1] + [fig.add_subplot(gs[i], sharex=ax1) for i in range(1, 7)]
ax2, ax3, ax4, axT, ax5, ax6 = axs[1:]
for a in axs:
    a.set_facecolor(BG)
    for s in a.spines.values(): s.set_color(GRID)
    a.tick_params(colors=MUTED, labelsize=10); a.set_axisbelow(True)
fig.text(0.045, 0.966, '蓝白 / Lanbai · 全程节奏 v2.1（定稿）：亮度与色温随实测的乐句走（横轴 = 时间轴秒，出发 = 0；Urlicht t = 文件秒 + 3.0，末乐章 t = 文件秒 + 240.36）',
         color=INK, fontsize=17)
fig.text(0.045, 0.946, '上：桌面画面平均亮度 APL（sRGB luma，含 bloom），填色 = 该段画面平均色；EV = 2.2·log2(APL/50)，相对第 3 幕月海。  中：主光色温。  下：条码 · 靛蓝阶梯 · 屏幕上的字 · 乐句（实测 cues.json + v2.1 子标签）。竖线 = 三次剪。',
         color=MUTED, fontsize=10.5)
# ---- panel 1: APL
for p in PHASES:
    xs, ys = seg(p)
    ax1.fill_between(xs, ys, color=p[5], lw=0, zorder=2); ax1.plot(xs, ys, color=INK, lw=1.4, zorder=3)
for i in range(len(PHASES) - 1):
    t = PHASES[i][1]; ax1.plot([t, t], [PHASES[i][3][1], PHASES[i + 1][3][0]], color=INK, lw=1.4, zorder=3)
ax1.axhline(150, color='#6F86B0', lw=1, ls=(0, (4, 4)))
ax1.text(372, 153, 'VR 满屏亮度上限 luma 150（白除外）', color='#6F86B0', fontsize=9.5, va='bottom')
ax1.text(1182, 214, '← 10 白：峰值保持 29.15 s（≤ 30 s）\n   VR #D7E3E8 = luma 224\n   桌面 #E8F1F5 = luma 239', color=MUTED, fontsize=9, va='center')
ax1.set_ylim(0, 255); ax1.set_xlim(X0, X1); ax1.set_ylabel('APL', color=MUTED, fontsize=11); ax1.grid(axis='y', color=GRID, lw=0.8)
for t, lab in SCENE_HDR:
    ax1.axvline(t, color=GRID, lw=1, zorder=1)
    ax1.text(t + 3, {'4c': 232, '7c': 232, '8b': 232, '10 白': 232, '9 星海': 246}.get(lab, 246), lab, color=INK, fontsize=11.5, va='top', zorder=5)
for t, lab in CUTS:
    for a in axs: a.axvline(t, color='#C9D6DF', lw=1.1, ls=(0, (1, 2)), zorder=6)
    ax1.text(t - 3, 128, lab, color='#C9D6DF', fontsize=9.5, ha='right', rotation=90, va='center', zorder=6)
for t, apl, txt in [(-45, 22, '-2.6'), (140, 50, '0 基准'), (165, 40, '-0.8'), (231, 55, '+0.3 暗的恩典'), (250.1, 4, '-8.0 唯一的黑'),
                    (273, 110, '+2.5（比门内 +2.2）'), (312, 74, '+1.2 一次呼吸'), (420, 72, '+1.2'), (600, 22, '-2.8'), (700, 20, '-3.0'),
                    (905, 34, '-1.2 玫瑰预付'), (929, 80, '+1.5 F9 峰'), (975, 90, '+1.9'), (997, 46, '-0.5 蓝时'), (1013, 6, '-6.7'),
                    (1052, 122, '光源积累 x^2.5 · 镜 1–10 加速到 F15，11–13 是钟'), (1300, 26, '-2.1')]:
    ax1.annotate(txt, (t, apl), xytext=(0, 9), textcoords='offset points', color=INK, fontsize=9, ha='center',
                 bbox=dict(boxstyle='round,pad=0.2', fc=BG, ec='none', alpha=0.75), zorder=7)
# mirror crossings (two phases): ticks on the APL line
def apl_at(t):
    for p in PHASES:
        if p[0] <= t <= p[1]:
            sh = p[8] if len(p) > 8 else 1.0; x = (t - p[0]) / (p[1] - p[0]); return p[3][0] + (p[3][1] - p[3][0]) * x ** sh
    return 0.0
for k, t in enumerate(MIRRORS, 1):
    y = apl_at(t - 1e-6) if k == 13 else apl_at(t)
    ax1.plot([t, t], [y - 8, y + 8], color='#CDBF9C', lw=1.3, zorder=8)
for k, txt, dy in ((1, '镜 1', 14), (10, '镜 10 = F15 tragen!', 22), (11, '11', 14), (12, '12 · 白起', 22), (13, '13', 14)):
    t = MIRRORS[k - 1]; y = apl_at(t - 1e-6) if k == 13 else apl_at(t)
    ax1.text(t, y + dy, txt, color='#CDBF9C', fontsize=8.2, ha='center' if k not in (10, 12) else 'right', va='bottom', zorder=8)
ax1.tick_params(labelbottom=False)
# ---- panel 2: key light temperature (log), in the light's own colour
for p in PHASES:
    t0, t1, lab, apl, K = p[:5]
    if K is None: continue
    col = KEY_COLOUR.get(lab, ppv2.kelvin_hex(K))
    ax2.plot([t0, t1], [K, K], color=col, lw=3.2, solid_capstyle='butt')
    if lab in KEY_LABEL:
        ax2.text((t0 + t1) / 2 if not lab.startswith('1 ') else t0 + 3, K * 1.14, KEY_LABEL[lab], color=col, fontsize=8.8,
                 ha='center' if not lab.startswith('1 ') else 'left')
ax2.set_yscale('log'); ax2.set_ylim(1700, 21000); ax2.minorticks_off()
ax2.set_yticks([2000, 3000, 5000, 8000, 15000]); ax2.set_yticklabels(['2000 K', '3000', '5000', '8000', '15000'])
ax2.axhline(6500, color=GRID, lw=1, ls=(0, (2, 3))); ax2.text(520, 5900, '6500 K 中性', color=MUTED, fontsize=9)
ax2.text(380, 1880, '暖 = 大地 / 人间（钠灯、晨日、宫灯、暮日）', color='#E8B878', fontsize=9.5)
ax2.text(X1 - 5, 20000, '冷 = 梦（月、水下、蓝时、星）；藍白灯管 ≈7000 K 是“别处”的光', color='#9DB8FF', fontsize=9.5, va='top', ha='right')
ax2.grid(axis='y', color=GRID, lw=0.6); ax2.tick_params(labelbottom=False); ax2.set_ylabel('主光色温', color=MUTED, fontsize=11)
# ---- panel 3/4: barcode, ladder
for p in PHASES:
    t0, t1 = p[0], p[1]
    ax3.add_patch(Rectangle((t0, 0), t1 - t0, 1, color=p[5], lw=0)); ax4.add_patch(Rectangle((t0, 0), t1 - t0, 1, color=p[6], lw=0))
for a, lab in ((ax3, '条码'), (ax4, '靛蓝阶梯'), (axT, '屏幕上的字')):
    a.set_ylim(0, 1); a.set_yticks([]); a.tick_params(labelbottom=False)
    a.text(X0 - 4, 0.5, lab, color=MUTED, fontsize=10, ha='right', va='center')
# ---- text lane
for i, (a, b, lab) in enumerate(TEXT):
    axT.add_patch(Rectangle((a, 0.18), b - a, 0.5, color='#D9E2E7', alpha=0.85, lw=0))
    axT.text((a + b) / 2, 0.93 if i % 2 == 0 else -0.02, lab, color=INK, fontsize=8.2, ha='center', va='top' if i % 2 == 0 else 'bottom')
axT.text(1085, 0.43, 'F13 → F16 与白里没有字', color=MUTED, fontsize=8.5, ha='center', va='center')
axT.text(266, 0.43, '晨里无字', color=MUTED, fontsize=8.5, ha='center', va='center')
# ---- cue lanes (de-overlapped rotated labels with leader lines)
def lane(ax, items, fs, colour, min_gap):
    items = sorted(items); xs = [t for t, *_ in items]
    pos = list(xs)
    for _ in range(200):                     # relax: push neighbours apart to >= min_gap, keep order
        moved = False
        for i in range(1, len(pos)):
            if pos[i] - pos[i - 1] < min_gap:
                d = (min_gap - (pos[i] - pos[i - 1])) / 2; pos[i - 1] -= d; pos[i] += d; moved = True
        if not moved: break
    for (t, key, txt, _), x in zip(items, pos):
        ax.plot([t, t], [0.97, 1.0], color=MUTED, lw=1)
        ax.plot([t, x], [0.97, 0.88], color=GRID if abs(x - t) < 0.5 else '#3A4454', lw=0.8)
        s = '%s %.2f' % (key, t) + ('  ' + txt if txt else '')
        ax.text(x, 0.86, s, rotation=90, color=colour, fontsize=fs, ha='center', va='top')
for ax, lab in ((ax5, '乐句（实测）'), (ax6, 'v2.1 子标签')):
    ax.set_ylim(0, 1); ax.set_yticks([]); ax.text(X0 - 4, 0.5, lab, color=MUTED, fontsize=10, ha='right', va='center')
lane(ax5, [c for c in CUES if c[3] in (0, 2)], 7.4, INK, 7.6)
lane(ax6, [c for c in CUES if c[3] == 1], 7.2, '#AFC0D0', 7.0)
ax5.tick_params(labelbottom=False)
ax6.set_xlabel('时间轴秒（出发 = 0；站牌在 0 之前，由玩家决定多久）', color=MUTED, fontsize=10.5)
ax6.set_xticks(range(0, 1351, 60)); ax6.set_xticklabels(['%d\n%d:%02d' % (s, s // 60, s % 60) for s in range(0, 1351, 60)])
ax1.axvspan(3.0, 248.64, ymin=0.0, ymax=0.012, color='#8A6A90', zorder=8); ax1.axvspan(251.54, 1173.46, ymin=0.0, ymax=0.012, color='#6F8FB8', zorder=8)
ax1.text(125, 7, 'Urlicht · Ferrier / Klemperer 1951 单声道（收音机）3.0 → 248.64', color=MUTED, fontsize=8.5, ha='center')
ax1.text(700, 3, '第五乐章 · Walter / NYP 1958（文件 11.18 s 起）251.54 → 1173.46，之后 5 s 白里的静默', color=MUTED, fontsize=8.5, ha='center')
out = os.path.join(HERE, '../score.png'); fig.savefig(out, facecolor=BG); print('wrote', os.path.abspath(out))
