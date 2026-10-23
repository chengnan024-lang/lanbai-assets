"""Syntax / type check of the kit's shaders with slangc (no Unity): every Pass's CGPROGRAM, vert + frag entry points.
   python3 slang_check.py <slangc> [shader files...]     (default: ../Shaders/*.shader)
"""
import glob, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
slangc = sys.argv[1]
files = sys.argv[2:] or sorted(glob.glob(os.path.join(KIT, 'Shaders', '*.shader')))
inc = [os.path.join(KIT, 'Shaders'), os.path.join(os.path.dirname(KIT), 'Gate', 'Shaders')]
# project-root includes ("Assets/Lanbai/<folder>/..."): a temp tree Assets/Lanbai -> the repo
_root = tempfile.mkdtemp()
os.makedirs(os.path.join(_root, 'Assets'))
os.symlink(os.path.dirname(KIT), os.path.join(_root, 'Assets', 'Lanbai'))
inc.append(_root)
ok = True
for f in files:
    src = open(f).read()
    shared = ''.join(m.group(1) for m in re.finditer(r'CGINCLUDE(.*?)ENDCG', src, re.S))   # Unity prepends it to every pass
    for k, m in enumerate(re.finditer(r'CGPROGRAM(.*?)ENDCG', src, re.S)):
        body = shared + m.group(1)
        prag = dict(re.findall(r'#pragma\s+(vertex|fragment)\s+(\w+)', body))
        variants = [[]]
        for mc in re.findall(r'#pragma\s+(?:multi_compile|shader_feature)(?:_local)?\s+(.*)', body):
            kws = [w for w in mc.split() if w != '_' and not w.startswith('__')]
            variants = [v + [w] for v in variants for w in ([None] + kws)][:8]
        code = re.sub(r'#include\s+"UnityCG.cginc"', '#include "unity_stub.hlsl"', body)
        code = re.sub(r'#include\s+"(Lighting|AutoLight|UnityPBSLighting).cginc"', '', code)
        code = '#include "unity_stub.hlsl"\n' + code
        for var in variants:
            defs = [d for d in var if d]
            with tempfile.NamedTemporaryFile('w', suffix='.hlsl', delete=False, dir=HERE) as t:
                t.write(''.join('#define %s 1\n' % d for d in defs) + code)
                path = t.name
            for stage, key in (('vertex', 'vertex'), ('fragment', 'fragment')):
                if key not in prag:
                    continue
                cmd = [slangc, path, '-entry', prag[key], '-stage', stage, '-target', 'spirv', '-o', os.devnull,
                       '-I', HERE] + sum([['-I', i] for i in inc], [])
                r = subprocess.run(cmd, capture_output=True, text=True)
                tag = '%s pass %d %s %s' % (os.path.basename(f), k, stage, ','.join(defs) or '-')
                if r.returncode != 0:
                    ok = False
                    print('FAIL', tag)
                    print(r.stdout[-3000:], r.stderr[-3000:])
                else:
                    warn = [l for l in (r.stderr or '').splitlines() if 'warning' in l and '15601' not in l and '30081' not in l and '39019' not in l]
                    print('ok  ', tag, ('(%d warnings)' % len(warn)) if warn else '')
                    for l in warn[:6]:
                        print('     ', l)
            os.unlink(path)
sys.exit(0 if ok else 1)
