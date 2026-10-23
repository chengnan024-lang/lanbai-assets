"""Slang front-end check of every CGPROGRAM block in the given shader folders (default: the 门内 session's packages),
every keyword combination (all off, each on, all on; for KeywordEnum-style shader_feature lists: each one), plus a
lint for the Unity pitfalls the gate test found (CONTROL §6): a [Header()] with ':' '(' ')' or ',', and a uniform used
in a function body above its declaration (slang accepts that, d3d11 does not).

Includes written as "Assets/Lanbai/<Folder>/..." resolve to the repository's <Folder>/...  If the sky session has not
pushed Common/Shaders/LanbaiFog.cginc yet, a stub of the CONTROL §4 minimum interface is generated in the temp dir
(never in the repository). Proves well-formed, well-typed HLSL only - NOT that Unity's compiler accepts it.
usage: python3 check_shaders.py [folder ...]
"""
import os
import re
import sys
import tempfile

import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.environ.get('CHECK_OUT', os.path.join(tempfile.gettempdir(), 'lanbai_inside_check'))
os.makedirs(OUT, exist_ok=True)
STUB = open(os.path.join(HERE, 'unity_stub.slang')).read()
UNITY = ('UnityCG.cginc', 'UnityPBSLighting.cginc', 'Lighting.cginc', 'UnityStandardBRDF.cginc', 'AutoLight.cginc')
FOG_STUB = '''// LOCAL STUB of the CONTROL §4 minimum interface (the sky session owns the real file)
#ifndef LANBAI_FOG_INCLUDED
#define LANBAI_FOG_INCLUDED
float _FogCap;
float _FogHeightFalloff;
float3 LanbaiHorizon(float3 dirWS) { return unity_FogColor.rgb; }
float LanbaiFogAmount(float3 posWS, float3 camPosWS)
{
    float d = distance(posWS, camPosWS);
    float f = 1.0 - exp2(-unity_FogParams.y * d);
    if (_FogHeightFalloff > 0) f *= exp(-max(0, posWS.y - camPosWS.y) / _FogHeightFalloff);
    return min(f, _FogCap);
}
float3 LanbaiApplyFog(float3 colLinear, float3 posWS)
{
    float3 cam = LanbaiCentreEyePos();
    return lerp(colLinear, LanbaiHorizon(normalize(posWS - cam)), LanbaiFogAmount(posWS, cam));
}
#endif
'''


def resolve(name, here):
    if name.startswith('Assets/Lanbai/'):
        p = os.path.join(REPO, name[len('Assets/Lanbai/'):])
        if os.path.exists(p):
            return p
        rel = name[len('Assets/Lanbai/'):]
        import subprocess
        for br in ('origin/main', 'origin/pkg/sky'):          # not merged yet: take the owner's pushed version
            r = subprocess.run(['git', '-C', REPO, 'show', '%s:%s' % (br, rel)], capture_output=True, text=True)
            if r.returncode == 0:
                q = os.path.join(OUT, br.replace('/', '_') + '_' + os.path.basename(rel))
                open(q, 'w').write(r.stdout)
                print('  (%s from %s)' % (rel, br))
                return q
        if name.endswith('LanbaiFog.cginc'):
            p = os.path.join(OUT, 'LanbaiFog_stub.cginc')
            open(p, 'w').write(FOG_STUB)
            print('  (LanbaiFog.cginc not in the repository yet: using the local stub of the §4 interface)')
            return p
        raise FileNotFoundError(name)
    return os.path.join(here, name)


def expand(text, here, seen):
    def rep(m):
        name = m.group(1)
        if name in UNITY or name in seen:
            return ''
        seen.add(name)
        p = resolve(name, here)
        return '\n#line 1 "%s"\n' % os.path.basename(p) + expand(open(p).read(), os.path.dirname(p), seen) + '\n'
    return re.sub(r'#include\s+"([^"]+)"', rep, text)


def variants(block):
    groups = []
    for m in re.finditer(r'#pragma\s+(shader_feature_local|shader_feature|multi_compile_local|multi_compile)\s+(.*)', block):
        kws = [k for k in m.group(2).split() if k != '_' and not k.startswith('__')]
        if kws:
            groups.append((m.group(2).split()[0] != '_' and len(kws) > 1, kws))
    out = [()]
    for exclusive, kws in groups:
        if exclusive:      # an enum list: exactly one is on
            out = [v + (k,) for v in out for k in kws]
        else:
            out = out + [v + (k,) for v in out for k in kws]
    return out[:64]


def lint(path, src):
    bad = []
    for m in re.finditer(r'\[Header\(([^)]*)\)\]', src):
        if re.search(r'[:(),]', m.group(1)):
            bad.append('Header with : ( ) or , -> %s' % m.group(0))
    for m in re.finditer(r'\[Header\(([^\]]*)\)\]', src):
        if '(' in m.group(1):
            bad.append('Header with nested parentheses -> %s' % m.group(0))
    for b in re.findall(r'CGPROGRAM(.*?)ENDCG', src, re.S):
        decl = {}
        for i, line in enumerate(b.split('\n')):
            for mm in re.finditer(r'^\s*(?:uniform\s+)?(?:float|half|fixed|int|sampler2D|samplerCUBE)[234]?(?:x[234])?\s+([^;(]+);', line):
                for nm in mm.group(1).split(','):
                    nm = nm.strip().split('[')[0].split('=')[0].strip()
                    if nm.startswith('_') and nm not in decl:
                        decl[nm] = i
        for nm, di in decl.items():
            for i, line in enumerate(b.split('\n')):
                if i >= di:
                    break
                if re.search(r'\b%s\b' % re.escape(nm), line) and not line.strip().startswith('//'):
                    bad.append('%s used on block line %d before its declaration (line %d)' % (nm, i + 1, di + 1))
                    break
    return bad


def main(folders):
    dev = spy.create_device(type=spy.DeviceType.cpu, include_paths=[OUT])
    ok, n = True, 0
    for folder in folders:
        for root, _, files in os.walk(folder):
            if '~' in os.path.relpath(root, folder):
                continue
            for fn in sorted(files):
                if not fn.endswith('.shader'):
                    continue
                path = os.path.join(root, fn)
                src = open(path).read()
                for issue in lint(path, src):
                    ok = False
                    print('LINT ', fn, issue)
                for bi, b in enumerate(re.findall(r'CGPROGRAM(.*?)ENDCG', src, re.S)):
                    body = '\n'.join(l for l in b.split('\n') if not l.strip().startswith('#pragma'))
                    body = expand(body, root, set())
                    ents = re.findall(r'#pragma\s+(vertex|fragment)\s+(\w+)', b)
                    for var in variants(b):
                        n += 1
                        name = '%s_%d_%s' % (fn.replace('.shader', ''), bi, '_'.join(var) or 'base')
                        defs = ''.join('#define %s 1\n' % k for k in var)
                        f = os.path.join(OUT, name + '.slang')
                        open(f, 'w').write(STUB + '\n' + defs + '#line 1 "' + fn + '"\n' + body)
                        try:
                            dev.load_module(f)
                            print('OK   ', name)
                        except Exception as e:
                            ok = False
                            print('FAIL ', name)
                            print('\n'.join(l for l in str(e).split('\n') if 'error' in l.lower())[:3000])
    print('%d variant(s) checked: %s' % (n, 'ALL OK' if ok else 'ERRORS'))
    return ok


if __name__ == '__main__':
    kits = sys.argv[1:] or [os.path.join(REPO, k) for k in ('Act04c_Inside', 'Overlay', 'Mirrors', 'Act10_White', 'Lamps', 'Act11_FalseWake') if os.path.isdir(os.path.join(REPO, k))]
    sys.exit(0 if main(kits) else 1)
