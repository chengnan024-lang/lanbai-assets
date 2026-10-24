"""Slang front-end check of every CGPROGRAM block of the sea / palace / act-7 shaders (method of
Rain/Tools~/compile_check: see unity_stub.slang for what this proves and what it does not).
Every keyword combination declared with shader_feature / multi_compile is checked (all off, each on, all on;
a KeywordEnum group is checked one keyword at a time).
#include "Assets/Lanbai/<Folder>/..." resolves to <repo>/<Folder>/...; a file that is not in the repo (the Sky session's
LanbaiFog.cginc before pkg/sky lands) is taken from $LANBAI_STUB/<Folder>/... (a local stub, never committed).
usage: python3 check_shaders.py [shader dirs ...]   (default: Sea/Shaders Palace/Shaders Act07_Sea/Shaders)
"""
import os
import re
import sys
import tempfile

import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
STUB = os.environ.get('LANBAI_STUB', '')
OUT = os.environ.get('CHECK_OUT', os.path.join(tempfile.gettempdir(), 'lanbai_sea_check'))
os.makedirs(OUT, exist_ok=True)
stub = open(os.path.join(HERE, 'unity_stub.slang')).read()
UNITY = ('UnityCustomRenderTexture.cginc', 'UnityCG.cginc', 'UnityPBSLighting.cginc', 'Lighting.cginc', 'UnityStandardBRDF.cginc', 'AutoLight.cginc',
         'UnityStandardUtils.cginc', 'UnityShaderVariables.cginc')


def resolve(name, base):
    if name.startswith('Assets/Lanbai/'):
        rel = name[len('Assets/Lanbai/'):]
        p = os.path.join(REPO, rel)
        if os.path.exists(p):
            return p
        if STUB and os.path.exists(os.path.join(STUB, rel)):
            return os.path.join(STUB, rel)
        raise FileNotFoundError(name)
    return os.path.join(base, name)


def expand(text, base, seen):
    def rep(m):
        name = m.group(1)
        if name in UNITY:
            return ''
        p = resolve(name, base)
        if p in seen:
            return ''
        seen.add(p)
        return '\n#line 1 "%s"\n' % os.path.basename(p) + expand(open(p).read(), os.path.dirname(p), seen) + '\n'
    return re.sub(r'#include\s+"([^"]+)"', rep, text)


def keyword_groups(block):
    groups = []
    for m in re.finditer(r'#pragma\s+(?:shader_feature_local|shader_feature|multi_compile_local|multi_compile)\s+(.*)', block):
        ks = [k for k in m.group(1).split() if k != '_' and not k.startswith('__')]
        if ks:
            groups.append(ks)
    return groups


def variants(groups):
    out = [()]
    for g in groups:
        out += [(k,) for k in g]
    allon = tuple(g[-1] for g in groups)
    if len(groups) > 1 and allon not in out:
        out.append(allon)
    return out


def main(dirs):
    dev = spy.create_device(type=spy.DeviceType.cpu, include_paths=[OUT])
    ok, n = True, 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for path in sorted(os.listdir(d)):
            if not path.endswith('.shader'):
                continue
            src = open(os.path.join(d, path)).read()
            # pitfall 2 (CONTROL §6): no ':', '(' ')' or ',' inside [Header(...)]
            for h in re.findall(r'\[Header\((.*?)\)\]', src):
                if re.search(r'[:(),]', h):
                    ok = False
                    print('FAIL  %s: [Header(%s)] contains : ( ) or ,' % (path, h))
            for bi, b in enumerate(re.findall(r'CGPROGRAM(.*?)ENDCG', src, re.S)):
                groups = keyword_groups(b)
                body = '\n'.join(l for l in b.split('\n') if not l.strip().startswith('#pragma'))
                body = expand(body, d, set())
                for var in variants(groups):
                    n += 1
                    name = '%s_%d_%s' % (path.replace('.shader', ''), bi, '_'.join(var) or 'base')
                    defs = ''.join('#define %s 1\n' % k for k in var)
                    fn = os.path.join(OUT, name + '.slang')
                    open(fn, 'w').write(stub + '\n' + defs + '#line 1 "' + path + '"\n' + body)
                    try:
                        dev.load_module(fn)
                        print('OK   ', name)
                    except Exception as e:
                        ok = False
                        print('FAIL ', name)
                        msg = str(e)
                        print('\n'.join(l for l in msg.split('\n') if 'error' in l.lower() or l.startswith(' '))[:5000])
    print('%d variant(s) checked: %s' % (n, 'ALL OK' if ok else 'ERRORS'))
    return ok


if __name__ == '__main__':
    dirs = sys.argv[1:] or [os.path.join(REPO, x, 'Shaders') for x in ('Sea', 'Palace', 'Act07_Sea')]
    sys.exit(0 if main(dirs) else 1)
