# -*- coding: utf-8 -*-
"""全片账本：按时刻把每个包报上来的开销加起来，对照圣经 §1.9。

  ~/bpy/bin/python Engineering/ledgers/ledger.py            # 读 ledger_data.json → 写 README_账本.md 的自动部分 + ledger_timeline.png

数据：ledger_data.json
  budgets      圣经 §1.9 的上限（带出处）
  calibration  实测标定点（第一个：门的 gate_test）→ 把“桌面 / 两遍 VR”的实测换算成“9 MP、SPS-I、RTX 3060 级”的估计
  items[]      每一项开销：name、owner（包）、active [[t0, t1], ...]（时间轴秒）、gpu_ms（9 MP VR 的估计）、fse、
               particles、systems、udon_ms、vram_mb、download_mb、realtime_lights、status（bible / package / measured /
               engineer-estimate）、source（出处）、note
  samples[]    要查的时刻（标签 + t）；另外自动加每一段（scene_data_v21.PHASES）的中点
每一个数都要有 source。没有数的项写 null，表里显示“?”，不当 0 算进合计里（合计旁边标出缺了几项）。"""
import json
sys.dont_write_bytecode = True   # importing Art/tools/v21 must not leave __pycache__ in other folders
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'v21'))

KEYS = ('gpu_ms', 'fse', 'particles', 'systems', 'udon_ms', 'realtime_lights')


def load():
    return json.load(open(os.path.join(HERE, 'ledger_data.json'), encoding='utf-8'))


def active(it, t):
    return any(a <= t < b for a, b in it['active'])


def k_is_component(it):
    return it.get('kind') not in ('world', 'post', 'calibration') and it.get('gpu_ms') is not None and \
        it.get('status') in ('engineer-estimate', 'package', 'measured')


def at(D, t):
    s = {k: 0.0 for k in KEYS}
    missing = {k: [] for k in KEYS}
    items = [it for it in D['items'] if active(it, t)]
    has_world = any(it.get('kind') == 'world' and it.get('gpu_ms') is not None for it in items)
    for it in items:
        if has_world and k_is_component(it):
            continue                     # the bible's act total already contains this component (shown in the estimate column)
        for k in KEYS:
            v = it.get(k)
            if v is None:
                if k in it.get('expects', ()):
                    missing[k].append(it['name'])
            else:
                s[k] += v
    return s, missing, items


def sample_times(D):
    import scene_data_v21 as SD
    out = [(x['label'], x['t']) for x in D.get('samples', [])]
    for ph in SD.PHASES:
        t0, t1, name = ph[0], ph[1], ph[2]
        if t1 <= 0:
            continue
        out.append((name + '（中点）', round((max(t0, 0.0) + t1) / 2.0, 2)))
    out.sort(key=lambda x: x[1])
    return out


def verdict(v, cap, peak=None):
    if v is None:
        return ''
    if v <= cap:
        return '✅'
    if peak is not None and v <= peak:
        return '⚠️ 超持续上限（≤ 峰值）'
    return '❌'


def table(D):
    B = D['budgets']
    rows = ['| 时刻 | t | GPU 世界 + PPv2（ms；上限 %.1f，热点按圣经） | ' % (D['budgets']['world_ms'] + D['budgets']['ppv2_ms']) + '透明 FSE | 粒子 | Udon ms | 实时灯 | 缺数的项 |', '|---|---|---|---|---|---|---|---|']
    series = []
    for label, t in sample_times(D):
        s, miss, items = at(D, t)
        cap_ms = B['world_ms'] + B['ppv2_ms']
        hot = [h for h in B.get('hotspots', []) if h['t0'] <= t < h['t1']]
        if hot:
            cap_ms = hot[0]['world_ms'] + B['ppv2_ms']
        nmiss = sorted({n for k in ('gpu_ms', 'fse') for n in miss[k]})
        est = [it['est_total_ms'] for it in items if it.get('est_total_ms')]
        if est:   # the calibration estimate covers the measured scene; package items measured / estimated on top of it add
            est = [max(est) + sum(it['gpu_ms'] for it in items if it.get('gpu_ms') and it.get('status') in ('engineer-estimate', 'package', 'measured') and it.get('kind') != 'world')]
        if miss['gpu_ms']:
            gtxt = '? + %.1f（世界未知）' % s['gpu_ms']
        else:
            gtxt = '%.2f %s' % (s['gpu_ms'], verdict(s['gpu_ms'], cap_ms, B['world_peak_ms'] + B['ppv2_ms'] if not hot else None))
        if est:
            gtxt += '；**标定估计 %.1f** %s' % (max(est), verdict(max(est), cap_ms))
        rows.append('| %s | %.2f | %s | %.2f %s | %d %s | %.2f | %d | %s |' % (
            label, t, gtxt,
            s['fse'], verdict(s['fse'], B['fse_sustained'], B['fse_peak']), s['particles'],
            verdict(s['particles'], B['particles_per_act']), s['udon_ms'], s['realtime_lights'],
            ('%d：' % len(nmiss) + '、'.join(nmiss[:4]) + ('…' if len(nmiss) > 4 else '')) if nmiss else ''))
        series.append((t, max(est) if est else (s['gpu_ms'] if not miss['gpu_ms'] else float('nan')), s['fse'], s['particles'], cap_ms))
    return rows, series


def static(D):
    by = {}
    for it in D['items']:
        o = it.get('owner', '?')
        b = by.setdefault(o, dict(vram_mb=0.0, download_mb=0.0, n=0, nmiss=0))
        for k in ('vram_mb', 'download_mb'):
            if it.get(k) is not None:
                b[k] += it[k]
        b['n'] += 1
        if it.get('vram_mb') is None and it.get('kind') in ('texture', 'mesh', 'audio'):
            b['nmiss'] += 1
    B = D['budgets']
    rows = ['| 包 | 显存 MB | 下载 MB | 项数 | 缺显存数的资产项 |', '|---|---|---|---|---|']
    tv = td = 0.0
    for o, b in sorted(by.items()):
        rows.append('| %s | %.0f | %.0f | %d | %d |' % (o, b['vram_mb'], b['download_mb'], b['n'], b['nmiss']))
        tv += b['vram_mb']
        td += b['download_mb']
    rows.append('| **合计** | **%.0f** / %d %s | **%.0f** / %d %s | | |' % (tv, B['vram_mb'], verdict(tv, B['vram_mb']), td, B['download_mb'], verdict(td, B['download_mb'])))
    return rows


def chart(series, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    t = [s[0] for s in series]
    try:
        from matplotlib import font_manager
        fp = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')
        font_manager.fontManager.addfont(fp)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
    except Exception:
        pass
    fig, ax = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    ax[0].step(t, [s[1] for s in series], where='post', color='#2E4F8A', label='GPU 估计（ms，9 MP）')
    ax[0].step(t, [s[4] for s in series], where='post', color='#B52A1E', ls='--', label='上限（世界 + PPv2；热点按圣经）')
    ax[0].set_ylabel('ms')
    ax[0].legend(loc='upper right', fontsize=8)
    ax[1].step(t, [s[2] for s in series], where='post', color='#3876AB', label='透明 FSE')
    ax[1].axhline(4, color='#B52A1E', ls='--', lw=1)
    ax[1].axhline(7, color='#B52A1E', ls=':', lw=1)
    ax[1].set_ylabel('FSE')
    ax[1].set_xlabel('时间轴 t（秒）')
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=110)


def main():
    D = load()
    rows, series = table(D)
    srows = static(D)
    auto = ['<!-- AUTO:BEGIN（ledger.py 生成，别手改这一段） -->', '', '### 按时刻（9 MP、SPS-I、RTX 3060 级的估计）', ''] + rows + \
           ['', '### 显存 / 下载（按包）', ''] + srows + ['', '![时间线](ledger_timeline.png)', '', '<!-- AUTO:END -->']
    p = os.path.join(HERE, 'README_账本.md')
    txt = open(p, encoding='utf-8').read() if os.path.exists(p) else '# 全片账本\n\n<!-- AUTO:BEGIN --><!-- AUTO:END -->\n'
    a = txt.index('<!-- AUTO:BEGIN')
    b = txt.index('<!-- AUTO:END -->') + len('<!-- AUTO:END -->')
    open(p, 'w', encoding='utf-8').write(txt[:a] + '\n'.join(auto) + txt[b:])
    chart(series, os.path.join(HERE, 'ledger_timeline.png'))
    print('rows %d -> %s' % (len(rows) - 2, p))


if __name__ == '__main__':
    main()
