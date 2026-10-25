# -*- coding: utf-8 -*-
"""_Udon_ 全局量对账：登记表（Common/UdonGlobals.md，取 origin/main 的版本）对照 main 和每个包分支里实际出现的名字。

  python3 Engineering/ledgers/globals_scan.py [--fetch] [--out Engineering/ledgers/globals_report.md]

报告：每个名字出现在哪些分支 / 文件（写还是读：C# 里 SetGlobal* / VRCShader.SetGlobal* = 写，shader 里声明 = 读）；
没登记的、登记了但是 “预留” 的、同名不同类型的（shader 里 float 对 float4、C# 里 SetGlobalFloat 对 SetGlobalVector）。"""
import argparse
import collections
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NAME = re.compile(r'_Udon_[A-Za-z0-9_]+')
CS_WRITE = re.compile(r'SetGlobal(Float|Vector|Color|Texture|Matrix|Int|FloatArray|VectorArray)\s*\(\s*(?:VRCShader\.PropertyToID\()?\s*"(_Udon_[A-Za-z0-9_]+)"')
CS_ID = re.compile(r'PropertyToID\(\s*"(_Udon_[A-Za-z0-9_]+)"')
HLSL_DECL = re.compile(r'^\s*(?:uniform\s+)?(float[234]?(?:x[234])?|half[234]?|int|uint|sampler2D|samplerCUBE|sampler3D|UNITY_DECLARE_TEXCUBE|UNITY_DECLARE_TEX2D|Texture2D|TextureCube)\s*\(?\s*(_Udon_[A-Za-z0-9_]+)', re.M)
TEXT_EXT = ('.cs', '.shader', '.cginc', '.hlsl', '.compute', '.md', '.json', '.py')


def git(*a):
    return subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True).stdout


def registry():
    md = git('show', 'origin/main:Common/UdonGlobals.md')
    reg, reserved = {}, set()
    section = 'used'
    for line in md.splitlines():
        if line.startswith('## '):
            section = 'reserved' if '预留' in line else 'used'
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not cells or not NAME.search(cells[0]):
            continue
        names = set(NAME.findall(cells[0]))
        # expand shorthands like `_Udon_Lamp0..7`, `_Udon_Drip0..3`, `_Udon_Wiper*`
        for m in re.finditer(r'(_Udon_[A-Za-z_]+?)(\d)\.\.(\d)', cells[0]):
            for i in range(int(m.group(2)), int(m.group(3)) + 1):
                names.add(m.group(1) + str(i))
        if '_Udon_Wiper' in cells[0]:
            names |= {'_Udon_Wiper' + s for s in ('Time', 'Pivot0', 'Pivot1', 'Axis0', 'Axis1', 'Rest0', 'Rest1')}
        for m in re.finditer(r'`(_Udon_[A-Za-z_]+?)(\d)`\s*/\s*`?([A-Z]\b|\d\b)', cells[0]):
            names.add(m.group(1) + m.group(3))      # `_Udon_OneDropA/B`
        if '_Udon_OneDropA/B' in cells[0]:
            names |= {'_Udon_OneDropA', '_Udon_OneDropB'}
        for n in names:
            reg[n] = dict(section=section, row=cells[1] if len(cells) > 1 else '', writer=cells[2] if len(cells) > 2 else '')
            if section == 'reserved':
                reserved.add(n)
    return reg, reserved


def branch_files(ref):
    out = git('ls-tree', '-r', '--name-only', ref)
    return [f for f in out.splitlines() if f.endswith(TEXT_EXT)]


def scan(ref):
    uses = collections.defaultdict(list)    # name -> [(file, kind, type)]
    for f in branch_files(ref):
        if f.startswith('Common/UdonGlobals.md') or f.startswith('Engineering/ledgers/'):
            continue
        txt = git('show', '%s:%s' % (ref, f))
        if '_Udon_' not in txt:
            continue
        ext = os.path.splitext(f)[1]
        seen = set()
        if ext == '.cs':
            for m in CS_WRITE.finditer(txt):
                uses[m.group(2)].append((f, 'write', m.group(1)))
                seen.add(m.group(2))
            for m in CS_ID.finditer(txt):
                if m.group(1) not in seen:
                    uses[m.group(1)].append((f, 'id', ''))
                    seen.add(m.group(1))
        elif ext in ('.shader', '.cginc', '.hlsl', '.compute'):
            for m in HLSL_DECL.finditer(txt):
                uses[m.group(2)].append((f, 'decl', m.group(1)))
                seen.add(m.group(2))
                # 'float4 _Udon_A, _Udon_B, _Udon_C;' : the rest of the declaration list has the same type
                tail = txt[m.end():txt.find(';', m.end())] if txt.find(';', m.end()) > 0 else ''
                for n2 in re.findall(r',\s*(_Udon_[A-Za-z0-9_]+)', tail):
                    uses[n2].append((f, 'decl', m.group(1)))
                    seen.add(n2)
        for n in set(NAME.findall(txt)) - seen:
            if ext in ('.cs', '.shader', '.cginc', '.hlsl', '.compute'):
                uses[n].append((f, 'ref', ''))
            else:
                uses[n].append((f, 'doc', ''))
    return uses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--out', default=os.path.join(REPO, 'Engineering', 'ledgers', 'globals_report.md'))
    a = ap.parse_args()
    if a.fetch:
        git('fetch', '-q', 'origin')
    refs = ['origin/main'] + sorted(r.strip() for r in git('branch', '-r').splitlines() if 'origin/pkg/' in r)
    reg, reserved = registry()
    allu = {}
    for r in refs:
        allu[r] = scan(r)
    # "_Udon_Lamp" + i : a prefix used in string concatenation -> not a name of its own
    for r in refs:
        for n in list(allu[r]):
            if n not in reg and any(k.startswith(n) and re.fullmatch(r'\d+', k[len(n):] or 'x') for k in reg):
                del allu[r][n]
    names = sorted(set(reg) | {n for u in allu.values() for n in u})
    L = ['# `_Udon_` 全局量对账（自动生成：`Engineering/ledgers/globals_scan.py`）', '',
         '登记表 = `origin/main:Common/UdonGlobals.md`。扫的分支：' + '、'.join('`%s` (%s)' % (r, git('rev-parse', '--short', r).strip()) for r in refs) + '。',
         'write = C# 里 `SetGlobal*`；decl = shader 里声明；id / ref = 其他引用；doc = 只在文档里。', '']
    problems = []
    for n in names:
        where = []
        types = set()
        for r in refs:
            for f, kind, ty in allu[r].get(n, []):
                if kind in ('decl', 'write') and ty:
                    types.add((kind, ty))
                where.append((r.replace('origin/', ''), f, kind, ty))
        code_use = [w for w in where if w[2] != 'doc']
        st = reg.get(n)
        flag = []
        if st is None and code_use:
            flag.append('**没登记**')
        elif st is None:
            flag.append('只在文档里、没登记')
        elif n in reserved and code_use:
            flag.append('预留名已在代码里用（请把登记从“预留”挪到“已经在用”）')
        decl_types = {t for k, t in types if k == 'decl'}
        norm = {('float4' if t in ('float4', 'half4') else 'float' if t in ('float', 'half') else t) for t in decl_types}
        if len(norm) > 1:
            flag.append('**shader 里类型不一致**：' + ' / '.join(sorted(decl_types)))
        wr = {t for k, t in types if k == 'write'}
        if len(wr) > 1:
            flag.append('**C# 写入类型不一致**：' + ' / '.join(sorted(wr)))
        if flag:
            problems.append((n, flag, where))
    L.append('## 要处理的（%d）' % len(problems))
    L.append('')
    if not problems:
        L.append('没有。')
    for n, flag, where in problems:
        L.append('- `%s`：%s' % (n, '；'.join(flag)))
        for b, f, kind, ty in where[:8]:
            L.append('  - `%s` `%s` %s %s' % (b, f, kind, ty))
        if len(where) > 8:
            L.append('  - ……另 %d 处' % (len(where) - 8))
    L += ['', '## 全表', '', '| 全局量 | 登记 | 出现在 |', '|---|---|---|']
    for n in names:
        st = reg.get(n)
        tag = '—' if st is None else ('预留' if n in reserved else '在用')
        occ = collections.OrderedDict()
        for r in refs:
            for f, kind, ty in allu[r].get(n, []):
                if kind != 'doc':
                    occ.setdefault(r.replace('origin/', ''), set()).add(kind + (':' + ty if ty else ''))
        L.append('| `%s` | %s | %s |' % (n, tag, '；'.join('%s（%s）' % (b, ','.join(sorted(k))) for b, k in occ.items()) or '（只在文档）'))
    open(a.out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('%d names, %d problems -> %s' % (len(names), len(problems), a.out))
    for n, flag, _ in problems:
        print(' ', n, '; '.join(flag))


if __name__ == '__main__':
    main()
