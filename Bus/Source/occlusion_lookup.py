# -*- coding: utf-8 -*-
"""给别的包用的遮挡查询（D-33）：不需要 Blender。读 `Bus/Docs~/viewcheck/<name>_occlusion.npz`（viewcheck.py --export-grid 写的，
从眼位按 0.25° 网格对真车网格打射线，记第一个碰到的不透明件；玻璃不算遮挡），回答“这个方位 / 仰角矩形被挡掉多少、被什么挡”。

    from occlusion_lookup import Occlusion
    occ = Occlusion('Bus/Docs~/viewcheck/hero_occlusion.npz')
    occ.rect(az0, az1, el0, el1)       # -> dict(blocked=0..1, by={'Body': 0.12, ...}, window={'WindscreenR': 0.9, ...})
    occ.point(az, el)                  # -> ('WindscreenR' | 'open' | 不透明件名, opaque bool)

命令行：python3 Bus/Source/occlusion_lookup.py --rect 2.0,13.0,-8.0,-2.5 [--grid ...]
方位 0 = 车头、+ = 右（车门一侧）；仰角 + = 上；度。眼位见 npz 里的 eye。网格 0.25°：比这更细的东西（< 0.25° 的细件）可能漏掉，
要精确就用 viewcheck.py 直接对网格打（见 README）。
"""
import argparse
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


class Occlusion:
    def __init__(self, path=os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'hero_occlusion.npz')):
        d = np.load(path, allow_pickle=False)
        self.az = d['az']                    # ascending
        self.el = d['el']                    # ascending
        self.ids = d['ids']                  # [len(el), len(az)] int16: >= 0 opaque part id, -1 open air, <= -2 window (-2 - k)
        self.parts = json.loads(str(d['parts']))
        self.windows = json.loads(str(d['windows']))
        self.eye = d['eye'].tolist()

    def _cells(self, az0, az1, el0, el1):
        ia = np.where((self.az >= min(az0, az1)) & (self.az <= max(az0, az1)))[0]
        ie = np.where((self.el >= min(el0, el1)) & (self.el <= max(el0, el1)))[0]
        return self.ids[np.ix_(ie, ia)]

    def rect(self, az0, az1, el0, el1):
        c = self._cells(az0, az1, el0, el1)
        n = c.size
        if n == 0:
            return dict(blocked=0.0, by={}, window={}, cells=0)
        by, win = {}, {}
        for v, k in zip(*np.unique(c, return_counts=True)):
            if v >= 0:
                by[self.parts[v]] = round(k / n, 4)
            elif v == -1:
                win['open'] = round(k / n, 4)
            else:
                win[self.windows[-2 - v]] = round(k / n, 4)
        return dict(blocked=round(float((c >= 0).sum()) / n, 4), by=by, window=win, cells=int(n))

    def point(self, az, el):
        i = int(np.argmin(np.abs(self.el - el)))
        j = int(np.argmin(np.abs(self.az - az)))
        v = int(self.ids[i, j])
        if v >= 0:
            return self.parts[v], True
        return ('open' if v == -1 else self.windows[-2 - v]), False


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--grid', default=os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'hero_occlusion.npz'))
    ap.add_argument('--rect', required=True, help='az0,az1,el0,el1 (degrees)')
    a = ap.parse_args()
    r = [float(v) for v in a.rect.split(',')]
    print(json.dumps(Occlusion(a.grid).rect(*r), ensure_ascii=False, indent=1))
