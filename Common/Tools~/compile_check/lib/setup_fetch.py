"""Download + unpack the compile-check dependencies into the cache. Called by ../setup.sh, not by hand.

Everything lands OUTSIDE the repo (in $LANBAI_CHECK_CACHE). Archives are treated as data: they are unpacked with
zipfile (no code from them runs here), every member path is checked to stay inside the destination.

  setup_fetch.py nupkg <id> <version> <dest> [prefix ...]   NuGet package -> <dest> (only members under the prefixes)
  setup_fetch.py cginc <tag> <dest>                          Unity built-in CGIncludes of one Unity version -> <dest>
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

NUGET = 'https://api.nuget.org/v3-flatcontainer/%s/%s/%s.%s.nupkg'
# Unity's built-in shader source (MIT, Unity Technologies), mirrored per release by github.com/chsxf/unity-built-in-shaders.
# download.unity3d.com (the official builtin_shaders-<ver>.zip) is not reachable from the cloud containers.
CGINC = 'https://raw.githubusercontent.com/chsxf/unity-built-in-shaders/%s/Shaders/CGIncludes/%s'
CGINC_LICENSE = 'https://raw.githubusercontent.com/chsxf/unity-built-in-shaders/%s/license.txt'
# Seed list: every include a Lanbai shader is likely to name; the closure of their own #includes is fetched too.
CGINC_SEED = [
    'HLSLSupport.cginc', 'UnityShaderVariables.cginc', 'UnityShaderUtilities.cginc', 'UnityInstancing.cginc',
    'UnityCG.cginc', 'AutoLight.cginc', 'Lighting.cginc', 'UnityPBSLighting.cginc', 'UnityStandardUtils.cginc',
    'UnityStandardBRDF.cginc', 'UnityStandardCore.cginc', 'UnityStandardInput.cginc', 'UnityStandardConfig.cginc',
    'UnityShadowLibrary.cginc', 'UnityStandardShadow.cginc', 'UnityMetaPass.cginc', 'UnityStandardMeta.cginc',
    'UnityStandardParticles.cginc', 'UnityStandardParticleInstancing.cginc', 'UnityGBuffer.cginc',
    'UnityDeferredLibrary.cginc', 'UnityImageBasedLighting.cginc', 'UnityGlobalIllumination.cginc',
    'UnityLightingCommon.cginc', 'UnityUI.cginc', 'UnitySprites.cginc', 'UnityCustomRenderTexture.cginc',
    'UnityStandardCoreForward.cginc', 'UnityStandardCoreForwardSimple.cginc', 'TerrainEngine.cginc',
    'Tessellation.cginc', 'UnityColorGamut.cginc', 'UnityDeprecated.cginc', 'UnityIndirect.cginc',
]


def curl(url, dest):
    r = subprocess.run(['curl', '-sSfL', '--retry', '3', '--max-time', '600', '-o', dest, url])
    return r.returncode == 0 and os.path.getsize(dest) > 0


def safe_extract(z, dest, prefixes):
    root = os.path.realpath(dest)
    n = 0
    for info in z.infolist():
        name = info.filename
        if name.endswith('/') or (prefixes and not any(name.startswith(p) for p in prefixes)):
            continue
        target = os.path.realpath(os.path.join(root, name))
        if not target.startswith(root + os.sep):
            raise SystemExit('refusing archive member outside the destination: ' + name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with z.open(info) as src, open(target, 'wb') as out:
            shutil.copyfileobj(src, out)
        n += 1
    return n


def nupkg(pid, ver, dest, prefixes):
    stamp = os.path.join(dest, '.lanbai_ok')
    if os.path.exists(stamp):
        print('  cached  %s %s' % (pid, ver))
        return 0
    os.makedirs(dest, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, 'p.nupkg')
        url = NUGET % (pid.lower(), ver.lower(), pid.lower(), ver.lower())
        if not curl(url, f):
            print('  FAILED  download %s' % url)
            return 1
        sha = hashlib.sha256(open(f, 'rb').read()).hexdigest()
        with zipfile.ZipFile(f) as z:
            n = safe_extract(z, dest, prefixes)
    open(stamp, 'w').write('%s %s sha256=%s files=%d\n' % (pid, ver, sha, n))
    print('  fetched %s %s (%d files, sha256 %s...)' % (pid, ver, n, sha[:16]))
    return 0


def cginc(tag, dest):
    stamp = os.path.join(dest, '.lanbai_ok')
    if os.path.exists(stamp):
        print('  cached  Unity CGIncludes %s' % tag)
        return 0
    os.makedirs(dest, exist_ok=True)
    todo, got, missing = list(CGINC_SEED), set(), []
    while todo:
        name = todo.pop(0)
        if name in got or name in missing:
            continue
        f = os.path.join(dest, name)
        if not curl(CGINC % (tag, name), f):
            missing.append(name)
            if os.path.exists(f):
                os.remove(f)
            continue
        text = open(f, 'rb').read()
        if b'Unity Technologies' not in text[:400]:
            raise SystemExit('unexpected content in %s (not a Unity built-in include?)' % name)
        got.add(name)
        for m in re.finditer(rb'#\s*include\s+"([^"/]+)"', text):
            inc = m.group(1).decode()
            if inc not in got and inc not in todo and inc not in missing:
                todo.append(inc)
    if not curl(CGINC_LICENSE % tag, os.path.join(dest, 'license.txt')):
        print('  (license.txt not fetched; the files carry their MIT header)')
    core = {'HLSLSupport.cginc', 'UnityShaderVariables.cginc', 'UnityCG.cginc', 'UnityInstancing.cginc',
            'AutoLight.cginc', 'Lighting.cginc', 'UnityPBSLighting.cginc'}
    if not core <= got:
        print('  FAILED  Unity CGIncludes %s: missing %s' % (tag, sorted(core - got)))
        return 1
    open(stamp, 'w').write('%s files=%d not-in-this-version=%s\n' % (tag, len(got), ','.join(missing)))
    print('  fetched Unity CGIncludes %s (%d files)' % (tag, len(got)))
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'nupkg' and len(a) >= 4:
        sys.exit(nupkg(a[1], a[2], a[3], a[4:]))
    if a and a[0] == 'cginc' and len(a) == 3:
        sys.exit(cginc(a[1], a[2]))
    print(__doc__)
    sys.exit(2)
