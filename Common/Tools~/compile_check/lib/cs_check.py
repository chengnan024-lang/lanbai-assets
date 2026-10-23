"""Roslyn type-check of every *.cs under the given folders, in Unity's assembly layout (called by ../check_cs.sh).

Assembly layout (as Unity 2022.3 builds it):
  * a folder with an .asmdef (or under one) -> that assembly; "references" by name; includePlatforms ["Editor"] -> editor only
  * otherwise files under any 'Editor' folder -> Assembly-CSharp-Editor (sees UnityEditor + Assembly-CSharp)
  * otherwise -> Assembly-CSharp (runtime)
  * folders ending in '~' or starting with '.' are ignored (Unity ignores them too)
Two passes:
  editor  Unity 2021.1.14.1 UnityEngine.dll + UnityEditor.dll (newest UnityEditor reference on nuget.org), UNITY_EDITOR
          defined, every assembly (runtime ones too, as in the editor), stubs for UdonSharp / VRChat / PPv2 / TMP.
  player  runtime assemblies only, NO UnityEditor reference, UNITY_EDITOR undefined (= a player build: catches editor
          API leaking into runtime code). Against UnityEngine 2022.3.62 modules + the real Unity.Postprocessing.Runtime
          and Unity.TextMeshPro DLLs when setup.sh could fetch them (else 2021.1 + stubs, and the report says so).
Plus two lints that a C# compiler cannot do: _Udon_ global names (VRCShader.PropertyToID literals) against
Common/UdonGlobals.md, and a few C# features UdonSharp 1.x rejects (in UdonSharpBehaviour files).
C# 9, warnings are errors except Unity's own suppressions (0169 0649 0282 1701 1702) and CS0414.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(TOOL, '..', '..', '..'))
STUBS = os.path.join(TOOL, 'stubs')
CACHE = os.environ.get('LANBAI_CHECK_CACHE', os.path.expanduser('~/.cache/lanbai_check'))

UNITY_NOWARN = ['0169', '0649', '0282', '1701', '1702']        # what Unity's own csc response file suppresses
LANBAI_NOWARN = ['0414']                                        # private field assigned but never read (U# inspector fields)

# Scripting define symbols of a VRChat Worlds project on Unity 2022.3.22f1, Windows standalone target, .NET Framework API.
# (The VRChat / U# / PPv2 symbols are the ones those packages add to Player Settings; check yours once.)
_VER = ['UNITY_5_3_OR_NEWER', 'UNITY_5_4_OR_NEWER', 'UNITY_5_5_OR_NEWER', 'UNITY_5_6_OR_NEWER']
_VER += ['UNITY_%d_%d_OR_NEWER' % (y, m) for y in range(2017, 2022) for m in (1, 2, 3, 4) if not (y >= 2020 and m == 4)]
_VER += ['UNITY_2021_1_OR_NEWER', 'UNITY_2021_2_OR_NEWER', 'UNITY_2021_3_OR_NEWER',
         'UNITY_2022_1_OR_NEWER', 'UNITY_2022_2_OR_NEWER', 'UNITY_2022_3_OR_NEWER', 'UNITY_2022_3_22', 'UNITY_2022_3', 'UNITY_2022']
COMMON_DEFINES = _VER + [
    'PLATFORM_ARCH_64', 'UNITY_64', 'UNITY_STANDALONE_WIN', 'UNITY_STANDALONE', 'PLATFORM_STANDALONE_WIN', 'PLATFORM_STANDALONE',
    'ENABLE_AUDIO', 'ENABLE_CACHING', 'ENABLE_CLOTH', 'ENABLE_MICROPHONE', 'ENABLE_MULTIPLE_DISPLAYS', 'ENABLE_PHYSICS',
    'ENABLE_TEXTURE_STREAMING', 'ENABLE_VIRTUALTEXTURING', 'ENABLE_LZMA', 'ENABLE_UNITYEVENTS', 'ENABLE_VR', 'ENABLE_WEBCAM',
    'ENABLE_UNITYWEBREQUEST', 'ENABLE_WWW', 'ENABLE_CUSTOM_RENDER_TEXTURE', 'ENABLE_DIRECTOR', 'ENABLE_LOCALIZATION',
    'ENABLE_SPRITES', 'ENABLE_TERRAIN', 'ENABLE_TILEMAP', 'ENABLE_TIMELINE', 'ENABLE_LEGACY_INPUT_MANAGER', 'ENABLE_MONO',
    'NET_4_6', 'NET_UNITY_4_8', 'CSHARP_7_OR_LATER', 'CSHARP_7_3_OR_NEWER', 'UNITY_ASSERTIONS',
    'UNITY_POST_PROCESSING_STACK_V2', 'VRC_SDK_VRCSDK3', 'UDON', 'UDONSHARP']
EDITOR_DEFINES = ['UNITY_EDITOR', 'UNITY_EDITOR_64', 'UNITY_EDITOR_WIN', 'UNITY_INCLUDE_TESTS', 'ENABLE_PROFILER', 'DEBUG', 'TRACE']

NET472_LIBS = ['mscorlib', 'System', 'System.Core', 'System.Xml', 'System.Xml.Linq', 'System.Numerics',
               'System.Runtime.Serialization', 'System.Data', 'System.Drawing', 'Microsoft.CSharp']

# Known external assemblies -> stub source (name: (stub file, precompiled?)). Precompiled DLLs (VRChat SDK) are
# auto-referenced by every assembly; package asmdefs (UdonSharp.Runtime, PPv2, TMP) must be listed in an asmdef's
# "references" (Assembly-CSharp sees all of them).
EXTERNAL = {
    'VRCSDKStub': ('VRCSDKStub.cs', True, []),
    'UdonSharp.Runtime': ('UdonSharpStub.cs', False, ['VRCSDKStub']),
    'Unity.Postprocessing.Runtime': ('PPv2Stub.cs', False, []),
    'Unity.TextMeshPro': ('TMPStub.cs', False, []),
}
EXTERNAL_ALIASES = {'VRCSDKBase': 'VRCSDKStub', 'VRC.Udon': 'VRCSDKStub', 'VRCSDK3': 'VRCSDKStub',
                    'VRC.SDKBase': 'VRCSDKStub', 'VRC.SDK3': 'VRCSDKStub'}


def rel(p):
    p = os.path.abspath(p)
    return os.path.relpath(p, REPO) if p.startswith(REPO + os.sep) else p


def load_env():
    f = os.path.join(CACHE, 'env.json')
    if not os.path.exists(f):
        sys.exit('no %s: run %s first' % (f, os.path.join(TOOL, 'setup.sh')))
    return json.load(open(f))


# ------------------------------------------------------------------------------------------------- layout
def ignored_dir(name):
    return name.endswith('~') or name.startswith('.')


def collect(folders):
    files = []
    for f in folders:
        f = os.path.abspath(f)
        if os.path.isfile(f) and f.endswith('.cs'):
            files.append(f)
            continue
        for root, dirs, names in os.walk(f):
            dirs[:] = sorted(d for d in dirs if not ignored_dir(d))
            files += [os.path.join(root, n) for n in sorted(names) if n.endswith('.cs')]
    return sorted(set(files))


def find_asmdef(path, top):
    d = os.path.dirname(path)
    while True:
        defs = sorted(glob.glob(os.path.join(d, '*.asmdef')))
        if defs:
            return defs[0]
        if d == top or os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def layout(files):
    asm = {}

    def get(name, **kw):
        if name not in asm:
            asm[name] = dict(name=name, files=[], editor=False, refs=[], auto=True, override=False, unsafe=False,
                             constraints=[], asmdef=None, noengine=False)
            asm[name].update(kw)
        return asm[name]

    notes = []
    for f in files:
        top = REPO if f.startswith(REPO + os.sep) else os.path.dirname(f)
        ad = find_asmdef(f, top)
        if ad:
            try:
                j = json.load(open(ad, encoding='utf-8-sig'))
            except Exception as e:
                notes.append('ERROR %s: unreadable asmdef (%s)' % (rel(ad), e))
                continue
            plats = j.get('includePlatforms') or []
            a = get(j.get('name') or os.path.splitext(os.path.basename(ad))[0], asmdef=ad,
                    editor=(plats == ['Editor']), refs=list(j.get('references') or []),
                    auto=j.get('autoReferenced', True), override=j.get('overrideReferences', False),
                    unsafe=j.get('allowUnsafeCode', False), constraints=list(j.get('defineConstraints') or []),
                    noengine=j.get('noEngineReferences', False))
            if plats and plats != ['Editor']:
                notes.append('note %s: includePlatforms %s treated as runtime' % (rel(ad), plats))
            if j.get('precompiledReferences'):
                notes.append('note %s: precompiledReferences %s not modelled' % (rel(ad), j['precompiledReferences']))
            if j.get('versionDefines'):
                notes.append('note %s: versionDefines not modelled' % rel(ad))
        else:
            parts = os.path.relpath(f, top).split(os.sep)[:-1]
            a = get('Assembly-CSharp-Editor', editor=True) if 'Editor' in parts else get('Assembly-CSharp')
        a['files'].append(f)
    for a in asm.values():
        for r in a['refs']:
            if r.startswith('GUID:'):
                notes.append('WARN %s: GUID reference %s cannot be resolved here (use name references)' % (a['name'], r))
    return asm, notes


# ------------------------------------------------------------------------------------------------- compile
def run_csc(env, out_dll, sources, refs, defines, nowarn, unsafe=False):
    args = ['-nologo', '-nostdlib+', '-langversion:9', '-target:library', '-deterministic', '-utf8output',
            '-warn:4', '-warnaserror+', '-nowarn:' + ','.join(nowarn), '-out:' + out_dll]
    if defines:
        args.append('-define:' + ';'.join(defines))
    if unsafe:
        args.append('-unsafe+')
    args += ['-r:' + r for r in refs] + sources
    rsp = out_dll + '.rsp'
    open(rsp, 'w').write('\n'.join('"%s"' % a if ' ' in a else a for a in args))
    r = subprocess.run([env['dotnet'], env['csc'], '-noconfig', '@' + rsp], capture_output=True, text=True)
    diags = []
    for line in (r.stdout + r.stderr).splitlines():
        m = re.match(r'(.*?)\((\d+),(\d+)\): (error|warning) (\w+): (.*)', line)
        if m:
            diags.append((m.group(4), '%s:%s:%s: %s %s: %s' % (rel(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6))))
        elif re.match(r'(error|warning) \w+:', line.strip()):
            diags.append(('error' if line.strip().startswith('error') else 'warning', line.strip()))
    ok = r.returncode == 0 and os.path.exists(out_dll)
    if not ok and not diags:
        diags.append(('error', (r.stdout + r.stderr).strip()[:2000] or 'csc failed'))
    return ok, diags


def csc_version(env):
    r = subprocess.run([env['dotnet'], env['csc'], '-version'], capture_output=True, text=True)
    return (r.stdout.strip().split() or ['?'])[0]


def topo(asm, names):
    order, seen = [], set()

    def visit(n, stack):
        if n in seen or n not in asm:
            return
        if n in stack:
            return
        stack.add(n)
        for r in asm[n]['refs']:
            visit(r, stack)
        stack.discard(n)
        seen.add(n)
        order.append(n)
    for n in names:
        visit(n, set())
    return order


def profile_refs(env, profile):
    net = env['net472']
    base = [os.path.join(net, l + '.dll') for l in NET472_LIBS] + sorted(glob.glob(os.path.join(net, 'Facades', '*.dll')))
    real = {}
    if profile == 'editor':
        engine = [os.path.join(env['unity2021'], 'UnityEngine.dll')]
        editor = [os.path.join(env['unity2021'], 'UnityEditor.dll')]
        label = 'Unity 2021.1.14.1 UnityEngine.dll + UnityEditor.dll'
    else:
        u = env.get('unity2022') or ''
        mods = sorted(glob.glob(os.path.join(u, 'UnityEngine*.dll'))) if u else []
        if mods:
            engine = mods
            label = 'UnityEngine 2022.3.62 modules (player build)'
            for n in ('Unity.Postprocessing.Runtime', 'Unity.TextMeshPro'):
                p = os.path.join(u, n + '.dll')
                if os.path.exists(p):
                    real[n] = p
            if real:
                label += ' + real ' + ', '.join(sorted(real))
        else:
            engine = [os.path.join(env['unity2021'], 'UnityEngine.dll')]
            label = 'Unity 2021.1.14.1 UnityEngine.dll (2022.3 modules not available)'
        editor = []
    return base, engine, editor, real, label


def build_externals(env, profile, base, engine, real, out):
    """Compile the stubs for this profile (cached by content hash). Returns {name: dll}."""
    dlls = dict(real)
    for name in ['VRCSDKStub', 'UdonSharp.Runtime', 'Unity.Postprocessing.Runtime', 'Unity.TextMeshPro']:
        if name in dlls:
            continue
        src, _, deps = EXTERNAL[name]
        srcp = os.path.join(STUBS, src)
        h = hashlib.sha256((open(srcp, 'rb').read() + '|'.join(engine + [dlls[d] for d in deps]).encode())).hexdigest()[:16]
        d = os.path.join(CACHE, 'stub_build', profile, name + '_' + h)
        dll = os.path.join(d, name + '.dll')
        if not os.path.exists(dll):
            os.makedirs(d, exist_ok=True)
            ok, diags = run_csc(env, dll, [srcp], base + engine + [dlls[x] for x in deps], [], UNITY_NOWARN)
            if not ok:
                sys.exit('stub %s does not compile:\n  ' % src + '\n  '.join(m for _, m in diags))
        dlls[name] = dll
    return dlls


def check_profile(env, profile, asm, out, nowarn, extra_defines):
    base, engine, editor_ref, real, label = profile_refs(env, profile)
    ext = build_externals(env, profile, base, engine, real, out)
    defines = COMMON_DEFINES + (EDITOR_DEFINES if profile == 'editor' else []) + extra_defines
    names = [n for n in asm if profile == 'editor' or not asm[n]['editor']]
    runtime = [n for n in names if not asm[n]['editor'] and n != 'Assembly-CSharp']
    editors = [n for n in names if asm[n]['editor'] and n != 'Assembly-CSharp-Editor']
    order = topo(asm, runtime) + (['Assembly-CSharp'] if 'Assembly-CSharp' in asm else []) + topo(asm, editors)
    order += [n for n in names if n not in order and n != 'Assembly-CSharp-Editor']
    if 'Assembly-CSharp-Editor' in names:
        order.append('Assembly-CSharp-Editor')
    built, results = {}, []
    for n in order:
        a = asm[n]
        refs = list(base) + ([] if a['noengine'] else list(engine))
        if profile == 'editor' and not a['noengine']:
            refs += editor_ref                       # in the editor every assembly sees UnityEditor (player pass checks the rest)
        if not a['override']:
            refs.append(ext['VRCSDKStub'])           # precompiled SDK DLLs are auto-referenced
        missing, failed_dep = [], []
        if a['asmdef'] is None:                      # predefined assemblies see every auto-referenced assembly
            refs += [ext[x] for x in ('UdonSharp.Runtime', 'Unity.Postprocessing.Runtime', 'Unity.TextMeshPro')]
            for m, b in asm.items():
                if m == n or not b['auto'] or b['asmdef'] is None or (b['editor'] and not a['editor']):
                    continue
                if m in built:
                    refs.append(built[m])
                elif m in names:
                    failed_dep.append(m)
            if n == 'Assembly-CSharp-Editor' and 'Assembly-CSharp' in asm:
                if 'Assembly-CSharp' in built:
                    refs.append(built['Assembly-CSharp'])
                else:
                    failed_dep.append('Assembly-CSharp')
        else:
            for r in a['refs']:
                r2 = EXTERNAL_ALIASES.get(r, r)
                if r2 in ext:
                    refs.append(ext[r2])
                elif r2 in built:
                    refs.append(built[r2])
                elif r2 in asm:
                    failed_dep.append(r2)
                else:
                    missing.append(r)
        if missing:
            results.append((n, 'error', [('error', 'asmdef reference(s) %s: not in the checked folders and no stub for them' % missing)]))
            continue
        if failed_dep:
            results.append((n, 'skipped', [('note', 'not checked: depends on %s which did not compile' % failed_dep)]))
            continue
        if a['constraints'] and not all(c.lstrip('!') in defines if not c.startswith('!') else c[1:] not in defines for c in a['constraints']):
            results.append((n, 'skipped', [('note', 'defineConstraints %s not met in this pass' % a['constraints'])]))
            continue
        dll = os.path.join(out, profile, n + '.dll')
        os.makedirs(os.path.dirname(dll), exist_ok=True)
        ok, diags = run_csc(env, dll, a['files'], list(dict.fromkeys(refs)), defines, nowarn, a['unsafe'])
        if ok:
            built[n] = dll
        results.append((n, 'ok' if ok else 'error', diags))
    return label, order, results


# ------------------------------------------------------------------------------------------------- lints
def udon_registry():
    """Names registered in Common/UdonGlobals.md -> (exact set, prefix list)."""
    f = os.path.join(REPO, 'Common', 'UdonGlobals.md')
    exact, prefix = set(), []
    if not os.path.exists(f):
        return None
    for line in open(f, encoding='utf-8'):
        if not line.startswith('|'):
            continue
        cell = line.split('|')[1]
        for tok in re.findall(r'`([^`]+)`', cell):
            tok = tok.strip()
            m = re.match(r'(_Udon_\w*?)(\d+)\.\.(\d+)$', tok)               # _Udon_Lamp0..7
            if m:
                exact.update('%s%d' % (m.group(1), i) for i in range(int(m.group(2)), int(m.group(3)) + 1))
                continue
            m = re.match(r'(_Udon_\w*?)(\w)/(\w)$', tok)                      # _Udon_OneDropA/B
            if m:
                exact.update([m.group(1) + m.group(2), m.group(1) + m.group(3)])
                continue
            m = re.match(r'(_Udon_\w*)\*', tok)                               # _Udon_Wiper*
            if m:
                prefix.append(m.group(1))
                continue
            if re.match(r'_Udon_\w+$', tok):
                exact.add(tok)
    return exact, prefix


def udon_name_ok(name, reg, is_prefix=False):
    exact, prefix = reg
    if name in exact or any(name.startswith(p) for p in prefix):
        return True
    if is_prefix:   # "_Udon_Lamp" + i : fine if some registered name continues it
        return any(e.startswith(name) for e in exact) or any(p.startswith(name) or name.startswith(p) for p in prefix)
    return False


USHARP_RULES = [
    (r'\btry\s*\{', 'try/catch/finally is not supported by UdonSharp'),
    (r'\bthrow\b', 'throw is not supported by UdonSharp'),
    (r'\binterface\s+\w+', 'interfaces are not supported by UdonSharp'),
    (r'\bstruct\s+\w+\s*[:{]', 'user structs are not supported by UdonSharp'),
    (r'\b(?:async|await)\b', 'async/await is not supported by UdonSharp'),
    (r'\byield\s+(?:return|break)\b', 'iterators (yield) are not supported by UdonSharp'),
    (r'\bSystem\.Linq\b|\busing\s+System\.Linq\s*;', 'LINQ is not exposed to Udon'),
    (r'\b(?:List|Dictionary|HashSet|Queue|Stack)\s*<', 'System.Collections.Generic collections are not exposed to Udon (use arrays / VRC DataList)'),
    (r'\bclass\s+\w+\s*<', 'generic classes are not supported by UdonSharp'),
]


def strip_cs(text):
    """Blank comments and string/char literals (keeps line numbers), for the lints."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', text[i:j])); i = j
        elif c == '"' or (c == '@' and i + 1 < n and text[i + 1] == '"') or (c == '$' and i + 1 < n and text[i + 1] == '"'):
            j = i + (2 if c in '@$' else 1)
            verb = c == '@'
            while j < n:
                if not verb and text[j] == '\\':
                    j += 2; continue
                if text[j] == '"':
                    if verb and j + 1 < n and text[j + 1] == '"':
                        j += 2; continue
                    j += 1; break
                j += 1
            out.append('"' + re.sub(r'[^\n]', ' ', text[i + 1:j - 1]) + '"' if j - i >= 2 else text[i:j]); i = j
        elif c == "'":
            j = i + 1
            while j < n and text[j] != "'":
                j += 2 if text[j] == '\\' else 1
            out.append(' ' * (j + 1 - i)); i = j + 1
        else:
            out.append(c); i += 1
    return ''.join(out)


def active_lines(code, defines):
    """Blank the lines a C# compile with these symbols would not see (#if / #elif / #else / #endif)."""
    lines = code.split('\n')
    stack = []          # (this branch active, some branch taken, parent active)

    def ev(expr):
        expr = expr.split('//')[0].strip()
        toks = re.findall(r'\w+|&&|\|\||!=|==|!|\(|\)', expr)
        py = []
        for t in toks:
            py.append({'&&': ' and ', '||': ' or ', '!': ' not ', '(': '(', ')': ')', '==': '==', '!=': '!=',
                       'true': 'True', 'false': 'False'}.get(t, 'True' if t in defines else 'False'))
        try:
            return bool(eval(''.join(py), {'__builtins__': {}}))
        except Exception:
            return True
    active = True
    for i, line in enumerate(lines):
        m = re.match(r'\s*#\s*(if|elif|else|endif)\b(.*)', line)
        if m:
            kw, rest = m.group(1), m.group(2)
            if kw == 'if':
                c = active and ev(rest)
                stack.append([c, c, active])
            elif kw == 'elif' and stack:
                top = stack[-1]
                c = top[2] and not top[1] and ev(rest)
                top[0] = c
                top[1] = top[1] or c
            elif kw == 'else' and stack:
                top = stack[-1]
                top[0] = top[2] and not top[1]
                top[1] = True
            elif kw == 'endif' and stack:
                stack.pop()
            active = stack[-1][0] if stack else True
            lines[i] = ''
        elif not active:
            lines[i] = ''
    return '\n'.join(lines)


def class_bodies(code, base):
    """(start, end) offsets of the bodies of classes deriving from `base`."""
    out = []
    for m in re.finditer(r'\bclass\s+\w+\s*:\s*(?:[\w.]+\.)?' + base + r'\b[^{]*\{', code):
        depth, j = 1, m.end()
        while j < len(code) and depth:
            depth += {'{': 1, '}': -1}.get(code[j], 0)
            j += 1
        out.append((m.start(), j))
    return out


def lint(files):
    reg = udon_registry()
    msgs = []
    usharp_view = set(COMMON_DEFINES + EDITOR_DEFINES + ['COMPILER_UDONSHARP'])
    for f in files:
        text = open(f, encoding='utf-8-sig').read()
        code = strip_cs(text)
        lineof = lambda pos: text.count('\n', 0, pos) + 1
        if reg is not None:
            for m in re.finditer(r'VRCShader\s*\.\s*PropertyToID\s*\(\s*"([^"]*)"\s*(\+)?', text):
                name, concat = m.group(1), bool(m.group(2))
                if code[m.start():m.start() + 9] != 'VRCShader':
                    continue                                    # inside a comment
                if not name.startswith('_Udon_'):
                    msgs.append(('WARN', '%s:%d: VRCShader global "%s" lacks the _Udon_ prefix (VRChat rejects it; CONTROL §3)' % (rel(f), lineof(m.start()), name)))
                elif not udon_name_ok(name, reg, concat):
                    msgs.append(('WARN', '%s:%d: global "%s%s" is not registered in Common/UdonGlobals.md' % (rel(f), lineof(m.start()), name, '...' if concat else '')))
        # UdonSharp rules: only inside classes deriving from UdonSharpBehaviour, as U# sees them (COMPILER_UDONSHARP defined)
        view = active_lines(code, usharp_view)
        for a, b in class_bodies(view, 'UdonSharpBehaviour'):
            body = view[a:b]
            for pat, why in USHARP_RULES:
                for m in re.finditer(pat, body):
                    msgs.append(('WARN', '%s:%d: %s (U# lint: %s)' % (rel(f), lineof(a + m.start()), why, m.group(0).strip())))
    return msgs


# ------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Lanbai shared C# compile check (Roslyn, Unity assembly layout).')
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--pass', dest='passes', default='editor,player', help='editor,player (default both)')
    ap.add_argument('--strict', action='store_true', help='also report CS0169/CS0649 (Unity suppresses them)')
    ap.add_argument('-D', '--define', action='append', default=[], help='extra scripting define symbol')
    ap.add_argument('--out', default=os.environ.get('LANBAI_CHECK_OUT', os.path.join(tempfile.gettempdir(), 'lanbai_check_out', 'cs')))
    a = ap.parse_args()
    env = load_env()
    for k in ('dotnet', 'csc', 'net472', 'unity2021'):
        if not env.get(k):
            sys.exit('setup incomplete (%s missing): run %s' % (k, os.path.join(TOOL, 'setup.sh')))
    out = os.path.abspath(a.out)
    if out.startswith(REPO + os.sep):
        sys.exit('--out must be outside the repo')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    files = collect(a.folders)
    if not files:
        sys.exit('no .cs files under %s' % a.folders)
    asm, notes = layout(files)
    nowarn = LANBAI_NOWARN + ([x for x in UNITY_NOWARN if x not in ('0169', '0649')] if a.strict else UNITY_NOWARN)
    print('C# compile check (Roslyn %s, C# 9, warnings as errors except CS%s)' % (csc_version(env), ',CS'.join(nowarn)))
    for n in sorted(asm):
        print('  %-28s %s %2d file(s)%s' % (n, 'editor ' if asm[n]['editor'] else 'runtime', len(asm[n]['files']),
                                           ('  [' + rel(asm[n]['asmdef']) + ']') if asm[n]['asmdef'] else ''))
    for n in notes:
        print('  ' + n)
    errors = sum(1 for n in notes if n.startswith('ERROR'))
    for profile in [p.strip() for p in a.passes.split(',') if p.strip()]:
        label, order, results = check_profile(env, profile, asm, out, nowarn, a.define)
        print('\n[%s] %s' % (profile, label))
        if not results:
            print('  (no assemblies in this pass)')
        for n, status, diags in results:
            print('  %-7s %s' % ({'ok': 'OK', 'error': 'FAIL', 'skipped': 'SKIP'}[status], n))
            for kind, m in diags:
                print('          ' + m)
            errors += status == 'error'
    lints = lint(files)
    print('\n[lint] _Udon_ globals vs Common/UdonGlobals.md, UdonSharp feature rules')
    for kind, m in lints:
        print('  %s %s' % (kind, m))
    if not lints:
        print('  clean')
    print('\nC# CHECK %s (%d assembly error(s), %d lint warning(s)). Not a Unity compile: see README_compile_check.md.' % (
        'OK' if errors == 0 else 'FAILED', errors, len(lints)))
    print('outputs: ' + out)
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
