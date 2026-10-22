# -*- coding: utf-8 -*-
"""联系表、迭代对照总览、陌生人测试缩略图、并排对照。

  python3 lbh_sheet.py contact  --out sheet.png --cols 3  dirA dirB ...      # 每个目录里的 graded.png + metrics.json
  python3 lbh_sheet.py iters    --out overview.png <包>/Docs~/iterations    # NN_<名>/ 子目录按编号排
  python3 lbh_sheet.py stranger --out <目录> frame.png                       # 640 px 匿名缩略图 + 提问
  python3 lbh_sheet.py pair     --out pair.png a.png b.png --labels "Unity" "参考"   # 并排 + 亮度差热图"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lbh import sheets as SH  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['contact', 'iters', 'stranger', 'pair'])
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--title', default=None)
    ap.add_argument('--labels', nargs=2, default=('A', 'B'))
    a = ap.parse_args()
    if a.mode == 'contact':
        items = []
        for d in a.inputs:
            png = os.path.join(d, 'graded.png') if os.path.isdir(d) else d
            cap = os.path.basename(os.path.normpath(d))
            mp = os.path.join(d, 'metrics.json') if os.path.isdir(d) else None
            if mp and os.path.exists(mp):
                m = json.load(open(mp, encoding='utf-8'))
                cap += '\n' + SH.metrics_caption(m['metrics'], m.get('target'))
            items.append((png, cap))
        print(SH.contact_sheet(items, a.out, cols=a.cols, title=a.title))
    elif a.mode == 'iters':
        print(SH.iteration_overview(a.inputs[0], a.out, cols=a.cols))
    elif a.mode == 'stranger':
        print(SH.stranger_thumb(a.inputs[0], a.out))
    else:
        SH.side_by_side(a.inputs[0], a.inputs[1], a.out, labels=a.labels)
        root, ext = os.path.splitext(a.out)
        print(SH.diff_heat(a.inputs[0], a.inputs[1], root + '_diff' + ext))


if __name__ == '__main__':
    main()
