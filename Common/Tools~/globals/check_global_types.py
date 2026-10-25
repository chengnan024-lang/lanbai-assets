# -*- coding: utf-8 -*-
"""Check that every C# read / write of an _Udon_ global uses the call that matches the global's HLSL type (D-44 #2).

  python3 Common/Tools~/globals/check_global_types.py [--branches]      exit 1 if a mismatch is found

The HLSL type of each name comes from Common/Shaders/LanbaiGlobals.cginc (generated from the registry: float / float4 /
sampler). A C# call is matched when its first argument is the literal name, or an id variable assigned from
PropertyToID("<name>") in the same file:
    float, int            <-> SetGlobalFloat / GetGlobalFloat / SetGlobalInt / GetGlobalInt
    float2 / float3 / float4 <-> SetGlobalVector / GetGlobalVector / SetGlobalColor / GetGlobalColor
    sampler*              <-> SetGlobalTexture / GetGlobalTexture
Why it matters: GetGlobalFloat on a float4 global returns only one component (the 1025 s diagnosis read
_Udon_StarGain that way and printed "stars = 0", which proved nothing). A SetGlobalFloat on a float4 leaves y, z, w
whatever they were; a SetGlobalVector on a float declares a different property type for the same name.
Scans the working tree (*.cs, and *.cs.txt snapshots under FromLocal/, reported as LOCAL) and, with --branches, every
origin/pkg/* branch. Calls whose name it cannot resolve (arrays of ids, ids passed in) are counted, not judged.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CGINC = os.path.join(REPO, 'Common', 'Shaders', 'LanbaiGlobals.cginc')

DECL = re.compile(r'^\s*(float[234]?|half[234]?|int|uint|sampler2D|samplerCUBE|sampler3D)\s+(_Udon_[A-Za-z0-9_]+)\s*;', re.M)
ID = re.compile(r'(\w+)\s*=\s*(?:VRCShader|Shader)\.PropertyToID\(\s*"(_Udon_[A-Za-z0-9_]+)"\s*\)')
CALL = re.compile(r'(?:VRCShader|Shader)\.(Set|Get)Global(Float|Int|Integer|Vector|Color|Texture|Matrix)\s*\(\s*("(?:_Udon_[A-Za-z0-9_]+)"|[A-Za-z_][\w.]*)\s*[,)]')

KIND = {'Float': 'scalar', 'Int': 'scalar', 'Integer': 'scalar', 'Vector': 'vector', 'Color': 'vector',
        'Texture': 'texture', 'Matrix': 'matrix'}


def decl_kind(t):
    t = t.replace('half', 'float')
    if t in ('float', 'int', 'uint'):
        return 'scalar'
    if t.startswith('float'):
        return 'vector'
    return 'texture'


def types():
    src = open(CGINC, encoding='utf-8').read()
    return {m.group(2): (m.group(1), decl_kind(m.group(1))) for m in DECL.finditer(src)}


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s, flags=re.S)
    return re.sub(r'//[^\n]*', '', s)


def scan_text(path, text, T, out, unresolved):
    code = strip_comments(text)
    ids = {m.group(1).split('.')[-1]: m.group(2) for m in ID.finditer(code)}
    for m in CALL.finditer(code):
        op, fn, arg = m.group(1), m.group(2), m.group(3)
        name = arg.strip('"') if arg.startswith('"') else ids.get(arg.split('.')[-1])
        if name is None or not name.startswith('_Udon_'):
            if arg.startswith('"') or arg.split('.')[-1] in ids or 'Udon' in arg or arg.startswith('_id') or arg.startswith('id'):
                unresolved.append((path, code.count('\n', 0, m.start()) + 1, op + 'Global' + fn, arg))
            continue
        line = code.count('\n', 0, m.start()) + 1
        if name not in T:
            out.append((path, line, op + 'Global' + fn, name, 'not declared in LanbaiGlobals.cginc (not registered?)'))
            continue
        decl, dk = T[name]
        ck = KIND[fn]
        if ck != dk:
            fix = {'scalar': 'Get/SetGlobalFloat', 'vector': 'Get/SetGlobalVector', 'texture': 'Get/SetGlobalTexture'}[dk]
            out.append((path, line, op + 'Global' + fn, name, 'HLSL %s: use %s' % (decl, fix)))


def git(*a):
    return subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--branches', action='store_true', help='also scan every origin/pkg/* branch')
    a = ap.parse_args()
    T = types()
    found, unresolved, n = [], [], 0
    for f in git('ls-files').splitlines():
        if not (f.endswith('.cs') or f.endswith('.cs.txt')) or '/compile_check/stubs/' in f:
            continue
        p = os.path.join(REPO, f)
        if not os.path.exists(p):
            continue
        n += 1
        tag = ('LOCAL ' if f.startswith('FromLocal/') else '') + f
        scan_text(tag, open(p, encoding='utf-8', errors='replace').read(), T, found, unresolved)
    if a.branches:
        for ref in sorted(r.strip() for r in git('branch', '-r').splitlines() if 'origin/pkg/' in r):
            for f in git('ls-tree', '-r', '--name-only', ref).splitlines():
                if not f.endswith('.cs') or f.startswith('FromLocal/'):
                    continue
                n += 1
                scan_text(ref + ':' + f, git('show', ref + ':' + f), T, found, unresolved)
    seen = set()
    rows = []
    for r in found:
        key = (r[0].split(':', 1)[-1] if ':' in r[0] else r[0], r[2], r[3], r[4])
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)
    print('scanned %d C# files, %d _Udon_ globals declared' % (n, len(T)))
    for p, line, call, name, why in rows:
        print('MISMATCH %s:%d  %s(%s)  %s' % (p, line, call, name, why))
    print('%d mismatch(es); %d call(s) with a name that could not be resolved statically (not judged)' % (len(rows), len(unresolved)))
    return 1 if any('use ' in r[4] for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
