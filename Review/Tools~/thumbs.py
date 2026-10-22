# -*- coding: utf-8 -*-
"""陌生人测试的 640 px 缩略图：去掉文件名（编号），不带任何背景。用法: python3 thumbs.py OUTDIR img1 img2 ...（打印 编号 → 原图）"""
import os, sys
from PIL import Image
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for i, p in enumerate(sys.argv[2:]):
    im = Image.open(p).convert('RGB')
    im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS).save(os.path.join(out, 'img%02d.png' % i))
    print('img%02d' % i, p)
