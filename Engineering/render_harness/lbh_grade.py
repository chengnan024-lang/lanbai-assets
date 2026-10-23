# -*- coding: utf-8 -*-
"""重新调色 / 量数（不用 Blender，只要 numpy）。

  python3 Engineering/render_harness/lbh_grade.py --in <linear.npy 或 .exr 目录> --grade S6 --act 06 --out <目录>
  python3 Engineering/render_harness/lbh_grade.py --png <已经是显示码的 PNG，例如本地的 Unity 截图> --act 04 --cam hero --out <目录>

第一种：拿 lbh_render 存下的 linear.npy，换一个调色状态（例如交叉淡化中的 S3+S4=0.4、加 --dev 0.5 的曝光事件）重出。
第二种：只量数（Unity 截图已经过了 PPv2），和参考渲染用同一套定义，方便逐项对照。"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import lbh_render as R  # noqa: E402
from lbh import measure as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--in', dest='inp', default=None, help='linear.npy（或含它的目录）')
    ap.add_argument('--png', default=None, help='只量数：一张显示码 PNG')
    ap.add_argument('--cam', default='hero', help='机位名（量最亮点的方位 / 仰角用）')
    R.common_args(ap)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    cams = json.load(open(os.path.join(HERE, 'cameras.json'), encoding='utf-8'))['cameras']
    cam = dict(cams[args.cam]) if args.cam in cams else None
    if args.png:
        u8 = np.asarray(Image.open(args.png).convert('RGB'))
        m = M.measure(u8, act=args.act, cam=cam)
        rec = dict(metrics=m, source=args.png, cam=cam)
        if args.t is not None:
            rec['target'] = M.apl_target(args.t)
        json.dump(rec, open(os.path.join(args.out, 'metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps(m, ensure_ascii=False)[:600])
        return
    p = args.inp
    if os.path.isdir(p):
        p = os.path.join(p, 'linear.npy')
    lin = np.load(p).astype(np.float32)
    rec = R.finish(lin, args, cam, args.out)
    print('[lbh_grade] APL %.1f  purple %.2f%%' % (rec['metrics']['APL'], rec['metrics']['purple_pct']))


if __name__ == '__main__':
    main()
