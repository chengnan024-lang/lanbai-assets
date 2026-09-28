# -*- coding: utf-8 -*-
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from scene_data import PHASES, CUES, KEY_COLOUR, KEY_LABEL
import sys; sys.path.insert(0, '../lens_cine'); import ppv2
from lutlib_core import patch_ppv2; patch_ppv2(ppv2)
fm.fontManager.addfont('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc')
plt.rcParams['font.family'] = ['WenQuanYi Zen Hei']; plt.rcParams['axes.unicode_minus'] = False
BG, INK, MUTED, GRID = '#0C0E13', '#E8F1F5', '#8092A4', '#1C222C'
def ev(apl): return 2.2 * np.log2(max(apl, 4) / 50.0)
fig = plt.figure(figsize=(19, 11.2), dpi=110, facecolor=BG)
gs = fig.add_gridspec(5, 1, height_ratios=[4.3, 2.0, 0.5, 0.5, 2.0], hspace=0.10, left=0.06, right=0.985, top=0.93, bottom=0.05)
ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax3 = fig.add_subplot(gs[2], sharex=ax1); ax4 = fig.add_subplot(gs[3], sharex=ax1); ax5 = fig.add_subplot(gs[4], sharex=ax1)
for a in (ax1, ax2, ax3, ax4, ax5):
    a.set_facecolor(BG)
    for s in a.spines.values(): s.set_color(GRID)
    a.tick_params(colors=MUTED, labelsize=10)
    a.set_axisbelow(True)
X0, X1 = -1.6, 23.0
fig.text(0.055, 0.962, '蓝白 / Lanbai · 全程节奏 v2：亮度与色温随音乐走（横轴为约略分钟，一切绑定乐句，不绑时钟）', color=INK, fontsize=17)
fig.text(0.055, 0.940, '上：桌面画面平均亮度 APL（sRGB luma 0–255，含 bloom），填色 = 该段画面平均色；标注 EV = 2.2·log2(APL/50)，相对第 3 幕月海（基准 0）。  中：主光色温（对数）。  下：胶片条码 · 靛蓝阶梯 · 乐句。',
         color=MUTED, fontsize=10.5)
# ---- panel 1: APL
for (t0, t1, lab, (a0, a1), K, mean, rung, gr) in PHASES:
    ax1.fill_between([t0, t1], [a0, a1], color=mean, alpha=1.0, lw=0, zorder=2)
    ax1.plot([t0, t1], [a0, a1], color=INK, lw=1.6, zorder=3)
for i in range(len(PHASES) - 1):
    t = PHASES[i][1]; ax1.plot([t, t], [PHASES[i][3][1], PHASES[i + 1][3][0]], color=INK, lw=1.6)
ax1.axhline(150, color='#6F86B0', lw=1, ls=(0, (4, 4)))
ax1.text(7.0, 153, 'VR 满屏亮度上限 luma 150（白光除外）', color='#6F86B0', fontsize=9.5, ha='left', va='bottom')
ax1.text(19.62, 205, '← VR 白 #D7E3E8 = luma 224\n   桌面 #E8F1F5 = luma 239', color=MUTED, fontsize=9, ha='left', va='center')
ax1.set_ylim(0, 255); ax1.set_xlim(X0, X1); ax1.set_ylabel('APL', color=MUTED, fontsize=11)
ax1.grid(axis='y', color=GRID, lw=0.8)
scenes = [(-1.5, '1 站牌'), (0.0, '2 夜路'), (1.08, '3 离地'), (3.0, '4 门'), (3.5, '4c'), (5.05, '6 晨'), (7.67, '7 海'),
          (11.75, '河伯'), (14.5, '8 暮'), (16.25, '蓝时'), (16.67, '9 星海'), (19.08, '10 白'), (19.5, '11 假醒'), (20.75, '12 醒')]
for t, lab in scenes:
    ax1.axvline(t, color=GRID, lw=1)
    yl = {'蓝时': 232, '11 假醒': 232}.get(lab, 246)
    ax1.text(t + 0.06, yl, lab, color=INK, fontsize=11.5, va='top', zorder=5)
for t, apl, txt in [(-0.75, 22, '-2.6'), (2.86, 50, '0 基准'), (3.25, 39, '-0.8'), (4.5, 50, '+0.0 暗的恩典'), (5.02, 4, '-8.0 唯一的黑'),
                    (5.9, 110, '+2.5（比门内高 +2.2）'), (10.6, 30, '-1.6'), (12.5, 18, '-3.2'), (15.8, 90, '+1.9'), (21.8, 26, '-2.1')]:
    ax1.annotate(txt, (t, apl), xytext=(0, 9), textcoords='offset points', color=INK, fontsize=9.5, ha='center',
                 bbox=dict(boxstyle='round,pad=0.2', fc=BG, ec='none', alpha=0.7))
ax1.tick_params(labelbottom=False)
# ---- panel 2: colour temperature (log), step line in the light's own colour
for (t0, t1, lab, apl, K, mean, rung, gr) in PHASES:
    if K is None: continue
    col = KEY_COLOUR.get(lab, ppv2.kelvin_hex(K))
    ax2.plot([t0, t1], [K, K], color=col, lw=3.2, solid_capstyle='butt')
    if lab in KEY_LABEL:
        ax2.text(((t0 + t1) / 2 if not lab.startswith('1 ') else t0 + 0.05) + (0.6 if lab.startswith('4c') else 0), K * 1.13, KEY_LABEL[lab], color=col, fontsize=9, ha='center' if not lab.startswith('1 ') else 'left')
ax2.set_yscale('log'); ax2.set_ylim(1700, 21000); ax2.minorticks_off()
ax2.set_yticks([2000, 3000, 5000, 8000, 15000]); ax2.set_yticklabels(['2000 K', '3000', '5000', '8000', '15000'])
ax2.axhline(6500, color=GRID, lw=1, ls=(0, (2, 3)))
ax2.text(12.0, 6000, '6500 K 中性', color=MUTED, fontsize=9)
ax2.text(X0 + 0.05, 1900, '暖 = 大地 / 人间（钠灯、晨日、宫灯、暮日）', color='#E8B878', fontsize=9.5)
ax2.text(X1 - 0.1, 20000, '冷 = 梦（月、水下、蓝时、星）；藍白灯管 ≈7000 K 是“别处”的光', color='#9DB8FF', fontsize=9.5, va='top', ha='right')
ax2.grid(axis='y', color=GRID, lw=0.6); ax2.tick_params(labelbottom=False)
ax2.set_ylabel('主光色温', color=MUTED, fontsize=11)
# ---- panel 3: barcode, panel 4: indigo ladder
for (t0, t1, lab, apl, K, mean, rung, gr) in PHASES:
    ax3.add_patch(Rectangle((t0, 0), t1 - t0, 1, color=mean, lw=0))
    ax4.add_patch(Rectangle((t0, 0), t1 - t0, 1, color=rung, lw=0))
for a, lab in ((ax3, '条码'), (ax4, '靛蓝阶梯')):
    a.set_ylim(0, 1); a.set_yticks([]); a.tick_params(labelbottom=False)
    a.text(X0 - 0.08, 0.5, lab, color=MUTED, fontsize=10, ha='right', va='center')
# ---- panel 5: music cues
ax5.set_ylim(0, 1); ax5.set_yticks([])
ax5.text(X0 - 0.08, 0.5, '乐句', color=MUTED, fontsize=10, ha='right', va='center')
for i, (t, lab) in enumerate(CUES):
    ax5.axvline(t, ymin=0.86, ymax=0.9, color=MUTED, lw=1)
    ax5.text(t, 0.84, lab, rotation=90, color=INK if lab[:1] in 'UF' else MUTED, fontsize=8.4, ha='center', va='top')
ax5.set_xlabel('分钟（从收音机第一个音 U0 算起；站牌在 0 之前，由玩家决定多久）', color=MUTED, fontsize=10.5)
ax5.set_xticks(range(0, 24, 1))
ax5.axvspan(0, 5.0, ymin=0.9, ymax=1.0, color='#2A2230')
ax5.axvspan(5.05, 19.1, ymin=0.9, ymax=1.0, color='#1F2A3C')
ax5.text(2.5, 0.95, 'Urlicht · Ferrier/Klemperer 1951 单声道（收音机）', color=MUTED, fontsize=8.5, ha='center', va='center')
ax5.text(12.0, 0.95, '第五乐章 · Walter/NYP 1958 立体声（整个天空在唱）', color=MUTED, fontsize=8.5, ha='center', va='center')
ax1.text(19.29, 200, '+5.0', color='#1B2431', fontsize=9.5, ha='center', zorder=6)
fig.savefig('../score.png', facecolor=BG)
print('ok')
