"""Translation units: one program block of a .shader (or one .cginc) + its includes, inlined, for one keyword variant.

Include resolution follows Unity:  "Assets/Lanbai/<X>/..." -> <repo>/<X>/...;  a plain name -> next to the including
file;  then Unity's built-in CGIncludes (the real 2022.3.22f1 files from setup.sh, or stubs/unity_stub.hlsl).
Extra -I folders are searched last and reported (they stand for 'copy that file next to the shader').
Everything is inlined with #line markers, so slang, DXC and pcpp all see one source and report real file:line.
"""
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
STUB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stubs', 'unity_stub.hlsl'))
UNITY_PREFIX = 'Unity/CGIncludes/'

# Graphics-tier and platform symbols Unity defines when it compiles for PC / d3d11, tier 3 (Built-in pipeline).
PLATFORM_DEFINES = [
    ('SHADER_API_D3D11', '1'), ('SHADER_API_DESKTOP', '1'), ('UNITY_VERSION', '202230'),
    ('UNITY_COMPILER_DXC', '1'),             # selects Unity's sampler2D/tex2D emulation (HLSLSupport.cginc) for slang + DXC
    ('UNITY_PBS_USE_BRDF1', '1'), ('UNITY_SPECCUBE_BOX_PROJECTION', '1'), ('UNITY_SPECCUBE_BLENDING', '1'),
    ('UNITY_ENABLE_DETAIL_NORMALMAP', '1'), ('UNITY_LIGHT_PROBE_PROXY_VOLUME', '1'), ('UNITY_LIGHTMAP_RGBM_ENCODING', '1'),
    ('UNITY_ENABLE_REFLECTION_BUFFERS', '1'), ('UNITY_USE_DITHER_MASK_FOR_ALPHABLENDED_SHADOWS', '1'),
    ('UNITY_ENABLE_NATIVE_SHADOW_LOOKUPS', '1'), ('UNITY_HARDWARE_TIER3', '1'),
]
LIGHTMODE_PASS = {'ForwardBase': 'UNITY_PASS_FORWARDBASE', 'ForwardAdd': 'UNITY_PASS_FORWARDADD',
                  'ShadowCaster': 'UNITY_PASS_SHADOWCASTER', 'Deferred': 'UNITY_PASS_DEFERRED', 'Meta': 'UNITY_PASS_META',
                  'PrepassBase': 'UNITY_PASS_PREPASSBASE', 'PrepassFinal': 'UNITY_PASS_PREPASSFINAL'}
CG_AUTO_INCLUDES = ['HLSLSupport.cginc', 'UnityShaderVariables.cginc', 'UnityShaderUtilities.cginc']
STUB_NAMES = {'HLSLSupport.cginc', 'UnityShaderVariables.cginc', 'UnityShaderUtilities.cginc', 'UnityInstancing.cginc',
              'UnityCG.cginc', 'AutoLight.cginc', 'Lighting.cginc', 'UnityPBSLighting.cginc', 'UnityStandardUtils.cginc',
              'UnityStandardBRDF.cginc', 'UnityLightingCommon.cginc', 'UnityShadowLibrary.cginc', 'UnityGlobalIllumination.cginc',
              'UnityImageBasedLighting.cginc', 'UnityStandardConfig.cginc', 'UnityMetaPass.cginc'}

INCLUDE_RE = re.compile(r'^[ \t]*#[ \t]*include[ \t]+[<"]([^>"]+)[>"]', re.M)


def rel(p):
    p = os.path.abspath(p)
    return os.path.relpath(p, REPO) if p.startswith(REPO + os.sep) else p


def display(path):
    """Name a file for #line markers and messages."""
    return rel(path)


class Includes:
    def __init__(self, cginc_dir, extra_dirs=()):
        self.cginc = cginc_dir if cginc_dir and os.path.isdir(cginc_dir) else None
        self.extra = [os.path.abspath(d) for d in extra_dirs]
        self.notes = []             # (level, where, message), de-duplicated by the caller

    def resolve(self, name, from_path):
        """-> (kind, path) with kind in user / unity / stub / extra, or (None, reason)."""
        n = name.replace('\\', '/')
        if n.startswith('Assets/'):
            m = re.match(r'Assets/Lanbai/(.+)', n)
            if m:
                p = os.path.join(REPO, m.group(1))
                if os.path.isfile(p):
                    return 'user', p
            return None, 'project path %s does not exist in the repo (Assets/Lanbai/<X>/ = <repo>/<X>/)' % n
        if n.startswith('Packages/'):
            return None, 'package include %s is not available offline' % n
        if from_path and not from_path.startswith('<'):
            p = os.path.normpath(os.path.join(os.path.dirname(from_path), n))
            if os.path.isfile(p) and not (self.cginc and os.path.dirname(from_path) == self.cginc):
                return 'user', p
        base = os.path.basename(n)
        if self.cginc:
            p = os.path.join(self.cginc, n)
            if os.path.isfile(p):
                return 'unity', p
        elif base in STUB_NAMES:
            return 'stub', STUB
        for d in self.extra:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return 'extra', p
        if self.cginc is None and base.startswith('Unity'):
            return None, 'Unity include %s is not covered by stubs/unity_stub.hlsl (run setup.sh to get the real CGIncludes)' % n
        return None, 'include file not found: "%s" (Unity looks next to the including file, then in its CGIncludes)' % n

    def expand(self, text, path, label, seen_unity, depth=0):
        """Inline every #include of `text` (which belongs to `path`, shown as `label`)."""
        if depth > 40:
            raise RuntimeError('include depth > 40 at ' + label)
        out = []
        lines = text.split('\n')
        for i, line in enumerate(lines):
            m = INCLUDE_RE.match(line)
            if not m:
                out.append(line)
                continue
            kind, p = self.resolve(m.group(1), path)
            if kind is None:
                self.notes.append(('ERROR', '%s:%d' % (label, i + 1), p))
                out.append('#error "%s"' % p.replace('"', "'"))
                continue
            if kind == 'extra':
                self.notes.append(('WARN', '%s:%d' % (label, i + 1), '"%s" resolved only through -I %s (in Unity it must sit next to the shader, or use the Assets/Lanbai/... path)' % (m.group(1), rel(os.path.dirname(p)))))
            if kind in ('unity', 'stub'):
                if p in seen_unity:          # Unity's includes are all guarded: skipping a repeat is equivalent
                    out.append('')
                    continue
                seen_unity.add(p)
                sub_label = UNITY_PREFIX + os.path.basename(p) if kind == 'unity' else 'stubs/unity_stub.hlsl'
            else:
                sub_label = display(p)
            body = open(p, encoding='utf-8-sig', errors='replace').read()
            out.append('#line 1 "%s"' % sub_label)
            out.append(self.expand(body, p, sub_label, seen_unity, depth + 1))
            out.append('#line %d "%s"' % (i + 2, label))
        return '\n'.join(out)


def strip_pragmas(text):
    """Blank '#pragma' lines (Unity consumes them; keeps line numbers)."""
    return re.sub(r'^[ \t]*#[ \t]*pragma\b.*$', '', text, flags=re.M)


def build(includes, *, defines, prefix_includes, pieces, kind_is_cg):
    """Assemble one translation unit.
    defines          [(name, value)]: platform + pass + keyword + stage symbols
    prefix_includes  Unity include names to put first (CGPROGRAM's automatic ones, surface-shader generator ones)
    pieces           [(text, path, label, first_line)]: CGINCLUDE blocks, the program, generated code, in order
    """
    seen = set()
    parts = ['#line 1 "<defines>"']
    parts += ['#define %s %s' % (k, v) for k, v in defines]
    for inc in prefix_includes if kind_is_cg or prefix_includes else []:
        parts.append(includes.expand('#include "%s"' % inc, '<auto>', '<auto>', seen))
    for text, path, label, first in pieces:
        parts.append('#line %d "%s"' % (first, label))
        parts.append(includes.expand(strip_pragmas(text), path, label, seen))
    return '\n'.join(parts) + '\n'


# ------------------------------------------------------------------------------------------- slang compatibility
SLANG_PRELUDE = ''.join('#define %s%s float%s\n' % (t, s, s) for t in ('half', 'min16float', 'min10float', 'fixed')
                        for s in ('', '1', '2', '3', '4', '2x2', '3x3', '4x4', '2x3', '3x2', '2x4', '4x2', '3x4', '4x3', '1x1')) + \
    ''.join('#define min16%s%s %s%s\n' % (t, s, t, s) for t in ('int', 'uint') for s in ('', '2', '3', '4'))


def slang_compat(tu):
    """Two source-level shims so slang's front end accepts Unity's (valid HLSL) code:
      * half / fixed / min16float -> float: FXC (Unity d3d11) also compiles half as 32-bit float, slang would not.
      * UNITY_INSTANCING_BUFFER_END(arr) expands to '} arr##Array[...]': slang rejects a declarator produced by
        token pasting (slang bug); spell the pasted name out before the macro runs."""
    tu = re.sub(r'^([ \t]*)#define UNITY_INSTANCING_BUFFER_END\(arr\)([ \t]*)(.*)$',
                lambda m: m.group(0) + '\n' + m.group(1) + '#define UNITY_INSTANCING_BUFFER_END_LBARR(arrname) ' +
                m.group(3).replace('arr##Array', 'arrname'), tu, flags=re.M)
    tu = re.sub(r'^(?![ \t]*#)(.*?)\bUNITY_INSTANCING_BUFFER_END\(\s*(\w+)\s*\)',
                lambda m: m.group(1) + 'UNITY_INSTANCING_BUFFER_END_LBARR(%sArray)' % m.group(2), tu, flags=re.M)
    return '#line 1 "<slang-compat>"\n' + SLANG_PRELUDE + tu


# ------------------------------------------------------------------------------------------- variants
BUILTIN_MULTI = {
    'multi_compile_instancing': [['_', 'INSTANCING_ON']],
    'multi_compile_fog': [['_', 'FOG_LINEAR', 'FOG_EXP', 'FOG_EXP2']],
    'multi_compile_particles': [['_', 'SOFTPARTICLES_ON']],
    'multi_compile_shadowcaster': [['SHADOWS_DEPTH', 'SHADOWS_CUBE']],
    'multi_compile_fwdbase': [['DIRECTIONAL'], ['_', 'LIGHTPROBE_SH'], ['_', 'SHADOWS_SCREEN'], ['_', 'VERTEXLIGHT_ON'],
                              ['_', 'LIGHTMAP_ON'], ['_', 'DIRLIGHTMAP_COMBINED'], ['_', 'DYNAMICLIGHTMAP_ON'],
                              ['_', 'LIGHTMAP_SHADOW_MIXING'], ['_', 'SHADOWS_SHADOWMASK']],
    'multi_compile_fwdbasealpha': [['DIRECTIONAL'], ['_', 'LIGHTPROBE_SH'], ['_', 'VERTEXLIGHT_ON'], ['_', 'LIGHTMAP_ON'],
                                   ['_', 'DIRLIGHTMAP_COMBINED'], ['_', 'DYNAMICLIGHTMAP_ON']],
    'multi_compile_fwdadd': [['POINT', 'DIRECTIONAL', 'SPOT', 'POINT_COOKIE', 'DIRECTIONAL_COOKIE']],
    'multi_compile_fwdadd_fullshadows': [['POINT', 'DIRECTIONAL', 'SPOT', 'POINT_COOKIE', 'DIRECTIONAL_COOKIE'],
                                         ['_', 'SHADOWS_DEPTH', 'SHADOWS_SCREEN', 'SHADOWS_CUBE'], ['_', 'SHADOWS_SOFT'],
                                         ['_', 'LIGHTMAP_SHADOW_MIXING'], ['_', 'SHADOWS_SHADOWMASK']],
    'multi_compile_lightpass': [['POINT', 'DIRECTIONAL', 'SPOT', 'POINT_COOKIE', 'DIRECTIONAL_COOKIE'], ['_', 'SHADOWS_DEPTH', 'SHADOWS_SCREEN', 'SHADOWS_CUBE'], ['_', 'SHADOWS_SOFT']],
    'multi_compile_prepassfinal': [['_', 'LIGHTMAP_ON'], ['_', 'DIRLIGHTMAP_COMBINED'], ['_', 'DYNAMICLIGHTMAP_ON'], ['_', 'UNITY_HDR_ON'], ['_', 'LIGHTPROBE_SH']],
}
KW_PRAGMA_RE = re.compile(r'^[ \t]*#[ \t]*pragma[ \t]+(multi_compile|shader_feature|dynamic_branch)(_local)?'
                          r'(_vertex|_fragment|_geometry|_hull|_domain|_raytracing)?(\w*)[ \t]*(.*)$', re.M)


def keyword_lines(text):
    """-> (list of option lists, all declared keywords). '_' = none. Built-in shortcuts are expanded."""
    lines, declared = [], set()
    for m in KW_PRAGMA_RE.finditer(text):
        kind, suffix, rest = m.group(1), m.group(4), m.group(5).split('//')[0].split()
        if kind == 'dynamic_branch':
            continue                                  # a uniform branch, not a variant
        if suffix:                                    # multi_compile_fog, _instancing, ...
            key = 'multi_compile' + suffix if kind == 'multi_compile' else None
            for opts in BUILTIN_MULTI.get(key, []):
                lines.append(list(opts))
                declared.update(o for o in opts if o != '_')
            continue
        opts = [o for o in rest if o]
        if not opts:
            continue
        opts = ['_' if re.fullmatch(r'_+', o) else o for o in opts]
        if kind == 'shader_feature' and len(opts) == 1:
            opts = ['_'] + opts
        lines.append(opts)
        declared.update(o for o in opts if o != '_')
    return lines, declared


def variants(lines, full_limit=32, exhaustive=False):
    """all off (first option of every line), each option on, all on (last option of every line);
    the full product instead when it is small (<= full_limit) or --exhaustive."""
    lines = [l for l in lines if l]
    total = 1
    for l in lines:
        total *= len(l)
    if exhaustive or total <= full_limit:
        out = [[]]
        for l in lines:
            out = [v + [o] for v in out for o in l]
    else:
        base = [l[0] for l in lines]
        out = [base]
        for i, l in enumerate(lines):
            for o in l[1:]:
                v = list(base)
                v[i] = o
                out.append(v)
        out.append([l[-1] for l in lines])
    res, seen = [], set()
    for v in out:
        kws = tuple(o for o in v if o != '_')
        if kws not in seen:
            seen.add(kws)
            res.append(kws)
    return res, total
