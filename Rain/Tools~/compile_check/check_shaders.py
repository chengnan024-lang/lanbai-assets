"""Slang front-end check of every CGPROGRAM block in ../../Shaders (see unity_stub.slang for what this proves).
Every keyword combination declared with shader_feature / multi_compile is checked (all off, each on, all on)."""
import itertools, os, re, sys, tempfile
import slangpy as spy

HERE = os.path.dirname(os.path.abspath(__file__))
SH = os.path.abspath(os.path.join(HERE, '..', '..', 'Shaders'))
OUT = os.environ.get('CHECK_OUT', os.path.join(tempfile.gettempdir(), 'lanbai_rain_check')); os.makedirs(OUT, exist_ok=True)   # never inside the kit
stub = open(os.path.join(HERE, 'unity_stub.slang')).read()
UNITY = ('UnityCG.cginc', 'UnityPBSLighting.cginc', 'Lighting.cginc', 'UnityStandardBRDF.cginc', 'AutoLight.cginc')


def expand(text, seen):
    def rep(m):
        name = m.group(1)
        if name in UNITY or name in seen:
            return ''
        seen.add(name)
        return '\n#line 1 "%s"\n' % name + expand(open(os.path.join(SH, name)).read(), seen) + '\n'
    return re.sub(r'#include\s+"([^"]+)"', rep, text)


def keywords(block):
    kws = []
    for m in re.finditer(r'#pragma\s+(?:shader_feature_local|shader_feature|multi_compile_local|multi_compile)\s+(.*)', block):
        for k in m.group(1).split():
            if k != '_' and not k.startswith('__'):
                kws.append(k)
    return kws


dev = spy.create_device(type=spy.DeviceType.cpu, include_paths=[OUT])
ok = True
n = 0
for path in sorted(os.listdir(SH)):
    if not path.endswith('.shader'):
        continue
    src = open(os.path.join(SH, path)).read()
    for bi, b in enumerate(re.findall(r'CGPROGRAM(.*?)ENDCG', src, re.S)):
        kws = keywords(b)
        surf = re.search(r'#pragma\s+surface\s+(\w+)', b)
        body = '\n'.join(l for l in b.split('\n') if not l.strip().startswith('#pragma'))
        body = expand(body, set())
        if surf:
            vfn = re.search(r'#pragma\s+surface\s+\w+.*vertex:(\w+)', b)
            call_v = ('appdata_full vv = (appdata_full)0; Input vi; %s(vv, vi);' % vfn.group(1)) if vfn else ''
            body += '\nfloat4 LBCHECK_surface_entry() { %s Input IN = (Input)0; SurfaceOutputStandard o = (SurfaceOutputStandard)0; %s(IN, o); return float4(o.Albedo + o.Emission, o.Alpha); }\n' % (call_v, surf.group(1))
        variants = [()] + [(k,) for k in kws] + ([tuple(kws)] if len(kws) > 1 else [])
        for var in variants:
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
sys.exit(0 if ok else 1)
