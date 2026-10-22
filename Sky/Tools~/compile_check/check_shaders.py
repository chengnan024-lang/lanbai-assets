"""Slang front-end check of every CGPROGRAM block in the given .shader files / folders (see unity_stub.slang for what
this proves and what it does not). Every keyword combination declared with shader_feature / multi_compile is checked
(all off, each on, all on). Includes: "Assets/Lanbai/<Folder>/..." resolve to <repo>/<Folder>/...; plain names
resolve next to the including file. Usage: ~/bpy/bin/python -I check_shaders.py <file-or-folder> ..."""
import os, re, sys, tempfile
import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.environ.get('CHECK_OUT', os.path.join(tempfile.gettempdir(), 'lanbai_sky_check')); os.makedirs(OUT, exist_ok=True)
stub = open(os.path.join(HERE, 'unity_stub.slang')).read()
UNITY = ('UnityCG.cginc', 'UnityPBSLighting.cginc', 'Lighting.cginc', 'UnityStandardBRDF.cginc', 'AutoLight.cginc',
         'UnityStandardUtils.cginc', 'UnityShaderVariables.cginc')


def resolve(name, cur_dir):
    if name.startswith('Assets/Lanbai/'):
        return os.path.join(REPO, name[len('Assets/Lanbai/'):])
    return os.path.join(cur_dir, name)


def expand(text, seen, cur_dir):
    def rep(m):
        name = m.group(1)
        if os.path.basename(name) in UNITY:
            return ''
        p = os.path.normpath(resolve(name, cur_dir))
        if p in seen:
            return '\n'           # the real file has an include guard; the second copy is empty
        seen.add(p)
        return '\n#line 1 "%s"\n' % os.path.relpath(p, REPO) + expand(open(p).read(), seen, os.path.dirname(p)) + '\n'
    return re.sub(r'#include\s+"([^"]+)"', rep, text)


def keywords(block):
    kws = []
    for m in re.finditer(r'#pragma\s+(?:shader_feature_local|shader_feature|multi_compile_local|multi_compile)\s+(.*)', block):
        for k in m.group(1).split():
            if k != '_' and not k.startswith('__'):
                kws.append(k)
    if re.search(r'#pragma\s+multi_compile_fog', block):
        kws.append('FOG_EXP')
    return kws


def files(args):
    for a in args:
        if os.path.isdir(a):
            for r, _, fs in os.walk(a):
                if '~' in os.path.relpath(r, a) and 'tests' not in r:
                    continue
                for f in sorted(fs):
                    if f.endswith('.shader'):
                        yield os.path.join(r, f)
        else:
            yield a


dev = spy.create_device(type=spy.DeviceType.cpu, include_paths=[OUT])
ok = True
n = 0
for path in files(sys.argv[1:]):
    src = open(path).read()
    expect_fail = 'LANBAI_CHECK_EXPECT_FAIL' in src
    for bi, b in enumerate(re.findall(r'CGPROGRAM(.*?)ENDCG', src, re.S)):
        kws = keywords(b)
        surf = re.search(r'#pragma\s+surface\s+(\w+)', b)
        body = '\n'.join(l for l in b.split('\n') if not l.strip().startswith('#pragma'))
        body = expand(body, set(), os.path.dirname(os.path.abspath(path)))
        if surf:
            vfn = re.search(r'#pragma\s+surface\s+\w+.*vertex:(\w+)', b)
            call_v = ('appdata_full vv = (appdata_full)0; Input vi; %s(vv, vi);' % vfn.group(1)) if vfn else ''
            body += '\nfloat4 LBCHECK_surface_entry() { %s Input IN = (Input)0; SurfaceOutputStandard o = (SurfaceOutputStandard)0; %s(IN, o); return float4(o.Albedo + o.Emission, o.Alpha); }\n' % (call_v, surf.group(1))
        variants = [()] + [(k,) for k in kws] + ([tuple(kws)] if len(kws) > 1 else [])
        for var in variants:
            n += 1
            name = '%s_%d_%s' % (os.path.basename(path).replace('.shader', ''), bi, '_'.join(var) or 'base')
            defs = ''.join('#define %s 1\n' % k for k in var)
            fn = os.path.join(OUT, name + '.slang')
            open(fn, 'w').write(stub + '\n' + defs + '#line 1 "' + os.path.basename(path) + '"\n' + body)
            try:
                dev.load_module(fn)
                good = not expect_fail
                print(('OK   ' if good else 'FAIL (expected an error) ') + name)
            except Exception as e:
                good = expect_fail
                msg = str(e)
                print(('OK (failed as expected) ' if good else 'FAIL ') + name)
                if not good or os.environ.get('SHOW_EXPECTED'):
                    print('\n'.join(l for l in msg.split('\n') if 'error' in l.lower() or l.startswith(' '))[:4000])
            ok = ok and good
print('%d variant(s) checked: %s' % (n, 'ALL OK' if ok else 'ERRORS'))
sys.exit(0 if ok else 1)
