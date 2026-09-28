"""The value score of Lanbai: brightness (APL), light colour temperature and music dynamics over the journey,
plus a 'film barcode' (the mean colour of the forward view over time). Writes value_score.png + value_score.json."""
import json, os, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib import font_manager
import ppv2

HERE = os.path.dirname(os.path.abspath(__file__))
for f in ['/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name()

# (id, start_min, end_min, label, APL target (0-255, full 16:9 forward view from the seat), mean frame colour,
#  key light K (None = non-Planckian: see note), music dynamic 0..6, music note)
PH = [
 ('S1', -1.5, 0.00, '1 站牌', 22, '#0F1520', 5600, 0.0, 'insects, a distant truck'),
 ('S2', 0.00, 1.75, '2 夜路', 30, '#15151A', 4300, 1.0, 'Urlicht pp, radio mono'),
 ('S3r', 1.75, 2.42, '3 离地 rise', 24, '#15151C', 2100, 1.3, 'the sound opens'),
 ('S3w', 2.42, 2.53, 'cloud', 62, '#444E60', 7000, 1.6, ''),
 ('S3', 2.53, 3.25, '3 moon', 50, '#2E3A52', 9000, 1.8, 'Je lieber moecht ich im Himmel sein'),
 ('S4', 3.25, 5.00, '4 触手之门', 36, '#16152E', 16000, 2.4, 'Engelein ... Ich bin von Gott'),
 ('S5', 5.00, 5.05, '5', 4, '#05050D', None, 0.0, 'silence 3 s'),
 ('S6', 5.05, 8.00, '6 天空 I 晨', 110, '#8E8FA6', 3200, 1.6, 'Grosser Appell: horns offstage, birds'),
 ('S7a', 8.00, 9.00, '7 海面', 85, '#3A7E9C', 12000, 0.6, 'chorus ppp: Aufersteh\'n'),
 ('S7b', 9.00, 12.00, '7 深海', 16, '#08192C', 1800, 1.6, 'O glaube, mein Herz'),
 ('S8', 12.00, 14.50, '8 天空 II 暮', 75, '#7A5C6C', 2400, 3.2, 'Mit Fluegeln'),
 ('S8b', 14.50, 15.25, 'blue hour', 50, '#2C4A80', 15000, 3.6, ''),
 ('S9a', 15.25, 17.50, '9 天空 III 星海', 30, '#0C1830', 10000, 4.2, 'Sterben werd ich, um zu leben'),
 ('S9b', 17.50, 18.75, '星海 climax', 80, '#3E5478', 9000, 6.0, 'organ, bells fff'),
 ('S10', 18.75, 19.15, '10 白', 239, '#E8F1F5', 8000, 5.2, 'final chord'),
 ('S11', 19.15, 20.00, '11 假醒', 30, '#141820', 4300, 0.2, 'silence, radio static'),
 ('S12', 20.00, 21.50, '12 醒', 24, '#10161F', 5600, 0.0, 'insects'),
]

RAMP = {'S7a': (95, 70, 1.0), 'S7b': (60, 14, 0.5), 'S9a': (28, 38, 2.0), 'S9b': (38, 80, 2.0), 'S8': (82, 70, 1.0), 'S8b': (62, 40, 1.0)}
LABEL_Y = {'S3w': 222, 'S3': 234, 'S3r': 246, 'S9b': 234, 'S10': 222, 'S11': 246}

def apl_to_ev(apl, ref=50):
    return math.log2(ppv2.srgb_to_lin(apl / 255) / ppv2.srgb_to_lin(ref / 255))

def main():
    t = np.linspace(-1.5, 21.5, 2300)
    def interp(key, smooth=0.12):
        vals = np.zeros_like(t)
        for i, p in enumerate(PH):
            m = (t >= p[1]) & (t < p[2])
            vals[m] = key(p)
        vals[t >= PH[-1][2] - 1e-9] = key(PH[-1])
        # soft transitions (seconds-scale crossfades) via box smoothing
        k = max(1, int(smooth / (t[1] - t[0])))
        return np.convolve(np.pad(vals, k, mode='edge'), np.ones(k) / k, mode='same')[k:-k]
    apl = np.zeros_like(t)
    for p in PH:
        m = (t >= p[1]) & (t < p[2])
        if p[0] in RAMP:
            a0, a1, ex = RAMP[p[0]]
            x = (t[m] - p[1]) / (p[2] - p[1])
            apl[m] = a0 + (a1 - a0) * x ** ex
        else:
            apl[m] = p[4]
    apl[t >= PH[-1][2] - 1e-9] = PH[-1][4]
    k = 5
    apl = np.convolve(np.pad(apl, k, mode='edge'), np.ones(k) / k, mode='same')[k:-k]
    dyn = interp(lambda p: p[7], 0.2)
    cols = []
    for tt in t:
        p = next((q for q in PH if q[1] <= tt < q[2]), PH[-1])
        cols.append(ppv2.hex_to_lin(p[5]))
    cols = np.array(cols)
    k = 8
    cols = np.stack([np.convolve(np.pad(cols[:, c], k, mode='edge'), np.ones(k) / k, mode='same')[k:-k] for c in range(3)], 1)
    bar = np.clip(ppv2.lin_to_srgb(cols), 0, 1)

    fig = plt.figure(figsize=(16, 8.6), dpi=130, facecolor='#0B0E14')
    gs = fig.add_gridspec(4, 1, height_ratios=[3.2, 1.5, 0.55, 0.45], hspace=0.08)
    ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1], sharex=ax); axb = fig.add_subplot(gs[2], sharex=ax); axl = fig.add_subplot(gs[3], sharex=ax)
    for a in (ax, ax2, axb, axl):
        a.set_facecolor('#0B0E14')
        for s in a.spines.values():
            s.set_color('#3A4150')
        a.tick_params(colors='#AEB6C4', labelsize=9)
    # brightness
    for i in range(len(t) - 1):
        ax.fill_between(t[i:i + 2], 0, apl[i:i + 2], color=bar[i], linewidth=0)
    ax.plot(t, apl, color='#E8F1F5', lw=1.6)
    ax.set_ylim(0, 255); ax.set_ylabel('APL (mean sRGB luma, 0-255)', color='#AEB6C4')
    evs = [-4, -2, 0, 2, 4]
    ax_r = ax.twinx()
    ax_r.set_ylim(0, 255)
    ticks = [255 * float(ppv2.lin_to_srgb(ppv2.srgb_to_lin(50 / 255) * 2 ** e)) for e in evs]
    ax_r.set_yticks(ticks); ax_r.set_yticklabels([f'{e:+d} EV' for e in evs]); ax_r.tick_params(colors='#7F8898', labelsize=8)
    for s in ax_r.spines.values():
        s.set_color('#3A4150')
    for p in PH:
        ax.axvline(p[1], color='#2A3140', lw=0.6)
        ax.text((p[1] + p[2]) / 2, LABEL_Y.get(p[0], 246), p[3], color='#1B2E52' if p[0] == 'S10' else '#DCE3EC', ha='center', va='top', fontsize=9 if p[2] - p[1] > 0.5 else 7.5)
        if p[8]:
            ax.text(p[1] + 0.03, 8 + (hash(p[0]) % 3) * 0, p[8], color='#8E98A8', fontsize=7, rotation=90, va='bottom')
    ax.set_title('蓝白 / Lanbai: the value score (brightness follows the music; EV relative to scene 3, the moonlit cloud sea)',
                 color='#E8F1F5', fontsize=12, loc='left')
    # temperature + dynamics
    ks = []
    for tt in t:
        p = next((q for q in PH if q[1] <= tt < q[2]), PH[-1])
        ks.append(p[6] if p[6] else np.nan)
    ks = np.array(ks, float)
    ax2.plot(t, ks, color='#F2C79A', lw=1.6, drawstyle='steps-post', label='key light colour temperature (K)')
    ax2.set_yscale('log'); ax2.set_ylim(1500, 20000)
    ax2.set_yticks([2000, 3000, 5000, 8000, 15000]); ax2.set_yticklabels(['2000 K', '3000', '5000', '8000', '15000'])
    ax2.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax2.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax2.axhline(6500, color='#3A4150', lw=0.6, ls='--')
    ax2.text(-1.45, 3600, 'warm = earth / human', color='#C79A6A', fontsize=7.5)
    ax2.text(-1.45, 11000, 'cool = dream', color='#8FB0D8', fontsize=7.5)
    ax2.text(3.3, 17000, 'violet tear (non-Planckian)', color='#B59BFF', fontsize=7.5)
    ax3 = ax2.twinx()
    ax3.fill_between(t, 0, dyn, color='#8E98A8', alpha=0.18, lw=0)
    ax3.plot(t, dyn, color='#8E98A8', lw=0.9)
    ax3.set_ylim(0, 6.5); ax3.set_yticks([0, 1, 2, 4, 6]); ax3.set_yticklabels(['-', 'pp', 'p', 'f', 'fff'])
    ax3.tick_params(colors='#7F8898', labelsize=8)
    for s in ax3.spines.values():
        s.set_color('#3A4150')
    ax2.legend(loc='upper right', fontsize=7.5, facecolor='#0B0E14', edgecolor='#3A4150', labelcolor='#AEB6C4')
    # barcode
    axb.imshow(bar[None, :, :], aspect='auto', extent=(t[0], t[-1], 0, 1))
    axb.set_yticks([]); axb.set_ylabel('film\nbarcode', color='#AEB6C4', fontsize=8, rotation=0, labelpad=26, va='center')
    # indigo ladder rung per phase
    ladder = {'S1': 0, 'S2': 0, 'S3r': 1, 'S3w': 4, 'S3': 2, 'S4': 1, 'S5': 0, 'S6': 5, 'S7a': 4, 'S7b': 1, 'S8': 3, 'S8b': 3, 'S9a': 2, 'S9b': 4, 'S10': 7, 'S11': 1, 'S12': 0}
    LAD = ['#070B14', '#0E1A2F', '#1B2E52', '#1F4E79', '#3A7CA8', '#7FB2CC', '#B4D6E3', '#E8F1F5']
    for p in PH:
        axl.axvspan(p[1], p[2], color=LAD[ladder[p[0]]], lw=0)
    axl.set_yticks([]); axl.set_ylabel('蓝 rung', color='#AEB6C4', fontsize=8, rotation=0, labelpad=26, va='center')
    axl.set_xlabel('minutes from boarding (approximate: bind to the musical cues, not the clock)', color='#AEB6C4')
    axl.set_xlim(-1.5, 21.5)
    plt.setp(ax.get_xticklabels(), visible=False); plt.setp(ax2.get_xticklabels(), visible=False); plt.setp(axb.get_xticklabels(), visible=False)
    fig.savefig(os.path.join(HERE, 'value_score.png'), facecolor=fig.get_facecolor(), bbox_inches='tight')
    rows = [dict(id=p[0], start=p[1], end=p[2], label=p[3], apl=p[4], ev_rel_S3=round(apl_to_ev(p[4]), 2), mean=p[5], keyK=p[6], dyn=p[7], music=p[8]) for p in PH]
    json.dump(rows, open(os.path.join(HERE, 'value_score.json'), 'w'), indent=1, ensure_ascii=False)
    for r in rows:
        print(r['id'], r['apl'], r['ev_rel_S3'])

if __name__ == '__main__':
    main()
