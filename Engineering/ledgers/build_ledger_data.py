# -*- coding: utf-8 -*-
"""bible_inventory.json（圣经逐条摘出的开销，每条带行号和原文）→ ledger_data.json 的第一版（按幕的模型项）。
规则（v1）：
  GPU：一幕里圣经给了“总代价 / 热点”的，记那个数（世界，含阴影平行光 1.0 ms）；没给的记 null（表里显示“?”），不拿上限冒充估计。
       另加每幕 PPv2 1.2 ms（圣经上限，status bible-cap）。第 4 幕另加一条总工程师按门实测标定的估计（见 README §1.1）。
  FSE：每幕的透明项相加，但“分项上限”不算（那是上限不是估计）；第 4 幕用门实测的 gate_fse 数（已含玻璃和云海的估计）。
  粒子：同一幕里同名 / 同数的重复项只算一次。
以后包交了，在 ledger_data.json 里把对应的项换成 package / measured，这个脚本只在没有 ledger_data.json 时生成第一版
（--force 覆盖）。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
inv = json.load(open(os.path.join(HERE, 'bible_inventory.json'), encoding='utf-8'))
out = os.path.join(HERE, 'ledger_data.json')
if os.path.exists(out) and '--force' not in sys.argv:
    sys.exit('ledger_data.json exists (use --force)')
G = inv['global']['budgets']
items = []
OWNER = {'1': '本地', '1→2': '本地', '2': '本地', '2→3': '本地', '3a': '待定', '3b': '待定', '3c': '待定', '3→4': '门', '4': '门', '4c': '门内',
         '5': '门内', '5→6': '云', '6a': '云', '6b': '云', '6c': '云', '6d': '云', '6→7': '海', '7a': '海', '7b': '海+宫殿', '7c': '海',
         '7→8': '云', '8': '云', '8b': '云', '9a': '天空', '9b': '天空', '9c': '天空+镜与白', '9→10': '镜与白', '10': '镜与白',
         '10→11': '镜与白', '11': '灯与假醒', '11→12': '灯与假醒', '12': '本地'}
for a in inv['acts']:
    t0 = a['t_start'] if a['t_start'] is not None else -90.0
    t1 = a['t_end'] if a['t_end'] is not None else 1729.96
    win = [[t0, t1]]
    if '→' in a['act']:
        # transitions overlap their acts; only the stretches no act covers get the per-act baseline items
        acts = [(x['t_start'] if x['t_start'] is not None else -90.0, x['t_end'] if x['t_end'] is not None else 1729.96)
                for x in inv['acts'] if '→' not in x['act']]
        gaps, cur = [], t0
        for s0, s1 in sorted(acts):
            if s1 <= cur or s0 >= t1:
                continue
            if s0 > cur:
                gaps.append([cur, s0])
            cur = max(cur, s1)
        if cur < t1:
            gaps.append([cur, t1])
        if not gaps:
            continue
        win = gaps
    own = OWNER.get(a['act'], '?')
    tot = [i for i in a['items'] if i.get('cost_ms') and ('总代价' in i['name'] or '热点' in i['name'])]
    if tot:
        i = max(tot, key=lambda x: x['cost_ms'])
        items.append(dict(name='第 %s 幕 世界（圣经估计，含阴影平行光）' % a['act'], owner=own, kind='world', active=win, gpu_ms=i['cost_ms'],
                          status='bible', source=i['source'], quote=i.get('quote', '')))
    else:
        items.append(dict(name='第 %s 幕 世界' % a['act'], owner=own, kind='world', active=win, gpu_ms=None, status='unknown',
                          source='圣经没有给这一幕的总代价', expects=['gpu_ms']))
    items.append(dict(name='PPv2（第 %s 幕）' % a['act'], owner='Grading', kind='post', active=win, gpu_ms=1.2, status='bible-cap',
                      source='bible §1.9 line 262'))
    if a['act'] == '4':
        items.append(dict(name='第 4 幕 透明（门实测 gate_fse，U8）', owner='门', kind='transparent', active=win, fse=3.77, status='package',
                          source='Gate/README_GateLayout.md §9（含车厢玻璃 0.7、云海卡 0.9 两项估计）'))
    else:
        seen = set()
        for i in a['items']:
            if i.get('fse') and '分项上限' not in i['name'] and i['name'] not in seen:
                seen.add(i['name'])
                items.append(dict(name=i['name'] + '（第 %s 幕）' % a['act'], owner=own if '玻璃' not in i['name'] else '车厢', kind='transparent',
                                  active=win, fse=i['fse'], status='bible', source=i['source'], quote=i.get('quote', '')))
    seenp = set()
    for i in a['items']:
        if i.get('particles') and i['particles'] not in seenp:
            seenp.add(i['particles'])
            items.append(dict(name=i['name'] + '（第 %s 幕）' % a['act'], owner=own, kind='particles', active=win, particles=i['particles'],
                              systems=i.get('systems'), status='bible' if not i.get('derived') else 'engineer-estimate', source=i['source'],
                              quote=i.get('quote', '')))
# act 4 calibration estimate (README §1.1) replaces the bible world number for the U7..U9 window
items.append(dict(name='第 4 幕 世界 + PPv2（门实测标定的估计：4060L 8.6 ms → 3060 约 9.5–11 ms，取 10.0；不含云海、车、玻璃）',
                  owner='门', kind='calibration', active=[[150.30, 179.55]], gpu_ms=None, est_total_ms=10.0, status='engineer-estimate',
                  source='Engineering/ledgers/README_账本.md §1.1；FromLocal/gate_test/perf.txt'))
for asset in inv['global'].get('assets', []):
    items.append(dict(name=asset.get('name', '?'), owner=asset.get('owner', asset.get('act', '?')), kind='texture', active=[],
                      vram_mb=asset.get('vram_mb') or asset.get('vram_mb_derived'), download_mb=asset.get('download_mb'),
                      status='bible' if asset.get('vram_mb') else 'engineer-estimate', source=asset.get('source', ''), note=asset.get('derivation', asset.get('note', ''))))
D = dict(
    _about='全片账本的数据。每一项都有 source；status：bible（圣经写的数）/ bible-cap（圣经的上限，不是估计）/ package（包报的）/ measured（本地实测）/ engineer-estimate（总工程师估的，算法写在 source）/ unknown。',
    budgets=dict(world_ms=5.3, world_peak_ms=6.3, ppv2_ms=1.2, fse_sustained=4.0, fse_peak=7.0, layers_per_pixel=8, particles_per_act=5000,
                 systems_per_act=8, udon_ms=0.4, vram_mb=700, download_mb=250,
                 hotspots=[dict(name='第 4 幕', t0=150.30, t1=179.55, world_ms=7.1, source='bible §1.9 line 264'),
                           dict(name='第 7b 宫殿（F5 → 7c 前 40 秒）', t0=644.96, t1=875.16, world_ms=6.4, source='bible §1.9 line 264')],
                 source='bible §1.9 lines 262-264'),
    samples=[dict(label='U7b 门主视觉', t=155.10), dict(label='U8 门透明峰', t=166.15), dict(label='U8+7 天窗', t=173.15),
             dict(label='F1b1 太阳重现', t=318.36), dict(label='F5 宫殿入画', t=645.0), dict(label='F7p 宫殿最近', t=810.0),
             dict(label='F13 银河点燃', t=1018.5), dict(label='第 12 面镜', t=1137.6)],
    items=items)
json.dump(D, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('items', len(items))
