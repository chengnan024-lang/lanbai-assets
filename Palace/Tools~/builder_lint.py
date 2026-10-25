# -*- coding: utf-8 -*-
"""搭建脚本的静态自查（不是 Unity 运行）：材质字典 d["X"] 的每一次读，都要在建 X 的那一行（Std(d, pal, "X", ...) 或 d["X"] = ...）之后。
终审 10-25：LanbaiPalaceBuilder.cs 曾在 Std(“Cowrie”) 之前 SetFloat，一开始就抛 KeyNotFoundException。
用法：python3 Palace/Tools~/builder_lint.py   （退出码 0 = 没查出问题）"""
import os
import re
import sys

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Editor', 'LanbaiPalaceBuilder.cs')
made, bad = {}, []
for n, line in enumerate(open(p, encoding='utf-8'), 1):
    for m in re.finditer(r'Std\(d, pal, "(\w+)"', line):
        made.setdefault(m.group(1), n)
    for m in re.finditer(r'd\["(\w+)"\]\s*=(?!=)', line):
        made.setdefault(m.group(1), n)
    for m in re.finditer(r'd\["(\w+)"\](?!\s*=(?!=))', line):
        k = m.group(1)
        if k not in made:
            bad.append('%d: d["%s"] 在它被建出来之前就读了' % (n, k))
for b in bad:
    print(b)
print('builder_lint: %s（%d 个槽）' % ('OK' if not bad else 'FAIL', len(made)))
sys.exit(1 if bad else 0)
