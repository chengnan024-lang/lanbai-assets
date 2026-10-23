# -*- coding: utf-8 -*-
"""Lanbai shared shader check: every .shader / .cginc under the given folders.

  python3 Common/Tools~/compile_check/check_shaders.py <folder or file> [...]   [--exhaustive] [--max-variants N] [-v]

What it does, per .shader file:
  1. ShaderLab lints (lib/shaderlab.py): [Header(...)] with ':' '(' ')' ',' (CONTROL §6 item 2), unparseable property
     lines, [KeywordEnum]/[Toggle] keywords no #pragma declares, ZTest Always outside the overlay.
  2. For every program block (CGPROGRAM / HLSLPROGRAM, with the CGINCLUDE / HLSLINCLUDE blocks of its SubShader and of
     the Shader in front, as Unity does) and every keyword variant picked by lib/hlsl_tu.variants():
       one translation unit = platform defines (PC d3d11, tier 3) + the pass define from its LightMode tag + the keywords
       + Unity's automatic includes + the code, everything inlined with #line markers (lib/hlsl_tu.py), then
       DXC (a real HLSL compiler; lib/dxc.py) compiles the vertex entry (vs_6_0) and the fragment entry (ps_6_0).
       Surface shaders (#pragma surface): Unity generates the passes; here the user code is compiled after the includes
       the generator puts first (UnityCG, Lighting, UnityPBSLighting, AutoLight), with a dummy entry point, so every
       function body is type-checked (HLSL semantic analysis covers unused functions too), once per pass flavour
       (FORWARDBASE, FORWARDADD unless noforwardadd, SHADOWCASTER when addshadow).
  3. Lanbai lints DXC cannot do:
       * SPS-I (bible §1.8, Common/Shaders/LanbaiVR.cginc): a vert/frag program needs UNITY_VERTEX_INPUT_INSTANCE_ID,
         UNITY_VERTEX_OUTPUT_STEREO, UNITY_SETUP_INSTANCE_ID, UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO; a fragment that reads
         _WorldSpaceCameraPos / UNITY_MATRIX_V|P|VP / unity_CameraToWorld / _CameraDepthTexture / LanbaiCentreEyePos
         needs UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX.
       * fog: a program calling LanbaiApplyFog* needs '#pragma multi_compile_fog' (else the FOG_* keywords never exist
         and LanbaiApplyFog compiles to nothing); UNITY_APPLY_FOG and LanbaiApplyFog on the same program = fog twice.
       * _Udon_ names declared in HLSL vs Common/UdonGlobals.md.
       * include paths: Common/ files must be included as "Assets/Lanbai/Common/Shaders/..." (CONTROL §3).
Per .cginc file (not reached through a .shader in the same run): compiled alone with a dummy entry (declare-before-use,
redefinitions inside the file).

What it does NOT prove: that FXC (Unity's d3d11 compiler) accepts it — DXC is stricter in a few corners and misses
FXC-only diagnostics (X4008 constant-folded division by zero, some X3570 gradient-in-loop cases); surface-shader
generator code is not reproduced; nothing about how it looks. 'Not compiled in Unity' stays true.
Run ./setup.sh once first (real Unity 2022.3.22f1 CGIncludes + DXC). Exit code 1 if any ERROR."""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import hlsl_tu as TU  # noqa: E402
import shaderlab as SL  # noqa: E402

CACHE = os.environ.get('LANBAI_CHECK_CACHE', os.path.expanduser('~/.cache/lanbai_check'))
REPO = TU.REPO
SURF_PREFIX = ['UnityCG.cginc', 'Lighting.cginc', 'UnityPBSLighting.cginc', 'AutoLight.cginc']
# what Unity's surface-shader generator defines before the user code (the parts user code can see)
SURF_GENERATED = ('#define INTERNAL_DATA half3 internalSurfaceTtoW0; half3 internalSurfaceTtoW1; half3 internalSurfaceTtoW2;\n'
                  '#define WorldReflectionVector(data,normal) reflect (data.worldRefl, half3(dot(data.internalSurfaceTtoW0,normal), dot(data.internalSurfaceTtoW1,normal), dot(data.internalSurfaceTtoW2,normal)))\n'
                  '#define WorldNormalVector(data,normal) fixed3(dot(data.internalSurfaceTtoW0,normal), dot(data.internalSurfaceTtoW1,normal), dot(data.internalSurfaceTtoW2,normal))\n')
DXC_ARGS = ['-HV', '2018', '-Vd', '-Wno-ignored-attributes', '-Wno-conversion', '-Wno-parentheses-equality',
            '-Wno-unused-value', '-Wno-for-redefinition', '-Wno-comma-in-init']
STEREO_FRAG_READS = re.compile(r'_WorldSpaceCameraPos|UNITY_MATRIX_(?:V|P|VP|I_V)\b|unity_CameraToWorld|unity_WorldToCamera|'
                               r'_CameraDepthTexture|LanbaiCentreEyePos|ComputeScreenPos|_ScreenParams|UnityWorldSpaceViewDir|WorldSpaceViewDir')


def load_env():
    p = os.path.join(CACHE, 'env.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def udon_registry():
    sys.path.insert(0, os.path.join(HERE, 'lib'))
    import cs_check
    return cs_check.udon_registry(), cs_check.udon_name_ok


class Report:
    def __init__(self):
        self.items = []
        self.var = {}

    def add(self, level, where, msg):
        key = (level, where, msg)
        if key not in self.items:
            self.items.append(key)

    def add_var(self, level, where, msg, variant):
        """the same error in many variants is one line: '[n variants: first ...]'."""
        self.var.setdefault((level, where, msg), []).append(variant)

    def flush(self):
        for (level, where, msg), vs in self.var.items():
            tag = vs[0] if len(vs) == 1 else '%d variants, e.g. %s' % (len(vs), vs[0])
            self.add(level, where, '[%s] %s' % (tag, msg))
        self.var = {}

    def count(self, level):
        return sum(1 for i in self.items if i[0] == level)


def collect(paths):
    out = []
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            out.append(p)
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.endswith(('.shader', '.cginc', '.hlsl')):
                    out.append(os.path.join(root, f))
    return sorted(set(out))


def pragmas(text):
    d = {}
    for m in re.finditer(r'^[ \t]*#[ \t]*pragma[ \t]+(\w+)[ \t]*(.*)$', SL.blank_comments(text), re.M):
        d.setdefault(m.group(1), []).append(m.group(2).strip())
    return d


def dxc_errors(text, max_lines=6):
    """keep 'file:line:col: error: ...' lines (+ the first note), drop warnings."""
    out, skipped = [], False
    for line in text.splitlines():
        if 'include file not found' in line or 'does not exist in the repo' in line:
            skipped = True
            continue
        if ': error:' in line or ': fatal error:' in line:
            out.append(line.strip())
    if out or skipped:
        return out[:max_lines]
    return [text.strip().splitlines()[0]] if text.strip() else []


def compile_tu(dxc, tu, stage, entry):
    prof = {'vs': 'vs_6_0', 'ps': 'ps_6_0'}[stage]
    ok, text = dxc.compile(tu, ['-T', prof, '-E', entry] + DXC_ARGS)
    return ok, text


def lint_program(rep, where, code, is_surface, frag_entry, vert_entry, prag, reg):
    clean = SL.blank_comments(code)
    if not is_surface and vert_entry and frag_entry:
        for macro in ('UNITY_VERTEX_INPUT_INSTANCE_ID', 'UNITY_VERTEX_OUTPUT_STEREO', 'UNITY_SETUP_INSTANCE_ID',
                      'UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO'):
            if macro not in clean and macro not in _includes_text(code):
                rep.add('ERROR', where, 'SPS-I: %s is missing (LanbaiVR.cginc header; without it the object renders in one eye only under SPS-I)' % macro)
        body = _function_body(clean, frag_entry)
        if body and STEREO_FRAG_READS.search(body) and 'UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX' not in body:
            rep.add('ERROR', where, 'SPS-I: fragment %s reads a per-eye value (%s) without UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX as its first line: '
                    'both eyes would shade with the left eye' % (frag_entry, STEREO_FRAG_READS.search(body).group(0)))
    uses_lf = re.search(r'\bLanbaiApplyFog\w*\s*\(', clean)
    if uses_lf and not any('multi_compile_fog' in k for k in prag):
        rep.add('ERROR', where, "calls LanbaiApplyFog but has no '#pragma multi_compile_fog': the FOG_* keywords never exist, so the fog compiles to nothing (LanbaiFog.cginc)")
    if uses_lf and re.search(r'\bUNITY_APPLY_FOG\w*\s*\(', clean):
        rep.add('WARN', where, 'both UNITY_APPLY_FOG and LanbaiApplyFog: fog applied twice unless they touch different colours')
    for m in re.finditer(r'#[ \t]*include[ \t]+"([^"]+)"', clean):
        inc = m.group(1)
        if re.search(r'(^|/)Lanbai(VR|Fog|Sky|Caustics|Globals)\.cginc$', inc) and not inc.startswith('Assets/Lanbai/Common/Shaders/'):
            rep.add('WARN', where, '#include "%s": Common files are included as "Assets/Lanbai/Common/Shaders/%s" (CONTROL §3)' % (inc, os.path.basename(inc)))
    if reg:
        (registry, ok_fn) = reg
        if registry:
            for m in re.finditer(r'^[ \t]*(?:uniform[ \t]+)?\w+[ \t]+(_Udon_\w+)', clean, re.M):
                if not ok_fn(m.group(1), registry):
                    rep.add('WARN', where, '%s is not in Common/UdonGlobals.md (register it before use)' % m.group(1))


_INC_CACHE = {}


def _includes_text(code):
    """the user include files' text (for macros a shared include might provide)"""
    acc = []
    for m in re.finditer(r'#[ \t]*include[ \t]+"(Assets/Lanbai/[^"]+)"', code):
        p = os.path.join(REPO, m.group(1)[len('Assets/Lanbai/'):])
        if p not in _INC_CACHE:
            _INC_CACHE[p] = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
        acc.append(_INC_CACHE[p])
    return '\n'.join(acc)


def _function_body(clean, name):
    m = re.search(r'\b%s\s*\([^;{]*\)\s*(?::\s*\w+\s*)?\{' % re.escape(name), clean)
    if not m:
        return None
    i, depth = m.end() - 1, 0
    for j in range(i, len(clean)):
        if clean[j] == '{':
            depth += 1
        elif clean[j] == '}':
            depth -= 1
            if depth == 0:
                return clean[i:j + 1]
    return clean[i:]


def check_shader(path, env, dxc, includes, rep, args, reg):
    sf = SL.ShaderFile(path)
    label = TU.display(path)
    all_prag_text = '\n'.join(b.text for b in sf.blocks)
    _, declared = TU.keyword_lines(all_prag_text)
    for level, ln, msg in sf.lint(declared):
        rep.add(level, '%s:%d' % (label, ln), msg)
    n_tu = 0
    shader_inc = [b for b in sf.blocks if b.kind.endswith('INCLUDE') and b.pass_index is None and b.subshader is None]
    for bi, b in enumerate(sf.blocks):
        if b.kind.endswith('INCLUDE'):
            continue
        is_cg = b.kind == 'CGPROGRAM'
        prag = pragmas(b.text)
        surf = prag.get('surface', [None])[0]
        vert = (prag.get('vertex') or [None])[0]
        frag = (prag.get('fragment') or [None])[0]
        where = '%s:%d (%s%s)' % (label, b.line, b.pass_name or ('pass %s' % b.pass_index if b.pass_index is not None else 'subshader'),
                                  ', ' + b.tags.get('LightMode') if b.tags.get('LightMode') else '')
        incs = [x for x in sf.blocks if x.kind.endswith('INCLUDE') and x.start < b.start and
                (x.subshader == b.subshader or x.pass_index is None)]
        pieces = [(x.text, path, label, x.line) for x in incs] + [(b.text, path, label, b.line)]
        lint_program(rep, where, '\n'.join(p[0] for p in pieces), bool(surf), frag, vert, prag, reg)
        klines, _ = TU.keyword_lines(b.text + '\n' + '\n'.join(x.text for x in incs))
        vlist, total = TU.variants(klines, full_limit=args.max_variants, exhaustive=args.exhaustive)
        if total > len(vlist):
            rep.add('INFO', where, '%d keyword variants in total; checked %d (all off, each on, all on)' % (total, len(vlist)))
        if surf:
            words = surf.split()
            flavours = [('UNITY_PASS_FORWARDBASE', 'FORWARDBASE')]
            if 'noforwardadd' not in words:
                flavours.append(('UNITY_PASS_FORWARDADD', 'FORWARDADD'))
            if 'addshadow' in words:
                flavours.append(('UNITY_PASS_SHADOWCASTER', 'SHADOWCASTER'))
            if dxc is None:
                continue
            for kws in vlist:
                for pdef, pname in flavours:
                    extra = [('POINT', '1')] if pname == 'FORWARDADD' else ([('SHADOWS_DEPTH', '1')] if pname == 'SHADOWCASTER' else [('DIRECTIONAL', '1')])
                    defines = TU.PLATFORM_DEFINES + [(pdef, '1'), ('SHADER_TARGET', '40'), ('SHADER_STAGE_FRAGMENT', '1')] + extra + [(k, '1') for k in kws]
                    tu = TU.build(includes, defines=defines, prefix_includes=TU.CG_AUTO_INCLUDES + SURF_PREFIX,
                                  pieces=[(SURF_GENERATED, '<surface-generator>', '<surface-generator>', 1)] + pieces + [('float4 lanbai_check_entry() : SV_Target { return 0; }\n', '<check>', '<check>', 1)], kind_is_cg=True)
                    ok, text = compile_tu(dxc, tu, 'ps', 'lanbai_check_entry')
                    n_tu += 1
                    if not ok:
                        for e in dxc_errors(text):
                            rep.add_var('ERROR', where, e, 'surface %s %s' % (pname, ' '.join(kws) or '-'))
            continue
        if not (vert and frag):
            rep.add('WARN', where, 'no #pragma vertex / fragment and no #pragma surface: not compiled')
            continue
        lm = b.tags.get('LightMode', 'ForwardBase')
        pdef = TU.LIGHTMODE_PASS.get(lm)
        if dxc is None:
            continue
        for kws in vlist:
            for stage, entry, sdef in (('vs', vert, 'SHADER_STAGE_VERTEX'), ('ps', frag, 'SHADER_STAGE_FRAGMENT')):
                defines = TU.PLATFORM_DEFINES + ([(pdef, '1')] if pdef else []) + [('SHADER_TARGET', '45'), (sdef, '1')] + [(k, '1') for k in kws]
                tu = TU.build(includes, defines=defines, prefix_includes=TU.CG_AUTO_INCLUDES if is_cg else [], pieces=pieces, kind_is_cg=is_cg)
                ok, text = compile_tu(dxc, tu, stage, entry)
                n_tu += 1
                if not ok:
                    for e in dxc_errors(text):
                        rep.add_var('ERROR', where, e, '%s %s' % (stage, ' '.join(kws) or '-'))
    return n_tu


def check_cginc(path, dxc, includes, rep):
    label = TU.display(path)
    code = open(path, encoding='utf-8-sig', errors='replace').read()
    tu = TU.build(includes, defines=TU.PLATFORM_DEFINES + [('SHADER_STAGE_FRAGMENT', '1'), ('SHADER_TARGET', '45')],
                  prefix_includes=TU.CG_AUTO_INCLUDES, pieces=[(code, path, label, 1),
                  ('float4 lanbai_check_entry() : SV_Target { return 0; }\n', '<check>', '<check>', 1)], kind_is_cg=True)
    ok, text = compile_tu(dxc, tu, 'ps', 'lanbai_check_entry')
    if not ok:
        for e in dxc_errors(text):
            rep.add('ERROR', label, '[alone] ' + e)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--exhaustive', action='store_true', help='every keyword combination')
    ap.add_argument('--max-variants', type=int, default=32, help='full product when it is at most this many')
    ap.add_argument('-I', dest='inc', action='append', default=[], help='extra include folder (reported: in Unity the file must sit next to the shader)')
    ap.add_argument('--json', default=None, help='also write the report as JSON here (outside the repo)')
    args = ap.parse_args()
    # 'Assets/Lanbai/<X>/...' resolves against the repo (or git worktree) that holds the files being checked
    import subprocess
    first = os.path.abspath(args.paths[0])
    top = subprocess.run(['git', '-C', first if os.path.isdir(first) else os.path.dirname(first), 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True).stdout.strip()
    if top:
        TU.REPO = top
        globals()['REPO'] = top
    env = load_env()
    rep = Report()
    dxc = None
    if env.get('dxc'):
        import dxc as DX
        dxc = DX.Dxc(env['dxc'], env.get('dxc_base'))
    else:
        rep.add('WARN', 'setup', 'no DXC (run setup.sh): only the ShaderLab and Lanbai lints ran')
    if not env.get('cginc'):
        rep.add('WARN', 'setup', 'no Unity CGIncludes (run setup.sh): stubs used')
    includes = TU.Includes(env.get('cginc'), args.inc)
    try:
        reg = udon_registry()
    except Exception:
        reg = None
    files = collect(args.paths)
    shaders = [f for f in files if f.endswith('.shader')]
    reached = set()
    for s in shaders:
        for m in re.finditer(r'#[ \t]*include[ \t]+"([^"]+)"', open(s, encoding='utf-8-sig', errors='replace').read()):
            k, p = includes.resolve(m.group(1), s)
            if k == 'user':
                reached.add(os.path.abspath(p))
    n = 0
    for f in files:
        if f.endswith('.shader'):
            n += check_shader(f, env, dxc, includes, rep, args, reg)
        elif dxc is not None and os.path.abspath(f) not in reached:
            n += check_cginc(f, dxc, includes, rep)
    rep.flush()
    for level, where, msg in includes.notes:
        rep.add(level, where, msg)
    order = {'ERROR': 0, 'WARN': 1, 'INFO': 2}
    for level, where, msg in sorted(rep.items, key=lambda x: (order.get(x[0], 3), x[1])):
        print('%-5s %s: %s' % (level, where, msg))
    print('---- %d files, %d translation units (DXC %s, CGIncludes %s): %d errors, %d warnings. NOT a Unity compile.' % (
        len(files), n, 'on' if dxc else 'off', env.get('cginc_version', 'stub') if env.get('cginc') else 'stub',
        rep.count('ERROR'), rep.count('WARN')))
    if args.json:
        json.dump([dict(level=l, where=w, msg=m) for l, w, m in rep.items], open(args.json, 'w'), ensure_ascii=False, indent=1)
    sys.exit(1 if rep.count('ERROR') else 0)


if __name__ == '__main__':
    main()
