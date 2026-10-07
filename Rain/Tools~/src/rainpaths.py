"""Where the tools find the kit's textures and data, so they run both from a working folder and from inside the
kit (Tools~/src, Tools~/preview). Generators WRITE to out_dir(); readers look, in order, in:
  $RAIN_OUT, <tools>/../out, <kit>/Textures/*/, <kit>/Docs~/, <kit>/Tools~/meta/
where <kit> is found by walking up from this file to the folder that holds README_Rain.md (or $RAIN_KIT)."""
import glob, os

HERE = os.path.dirname(os.path.abspath(__file__))


def kit_dir():
    k = os.environ.get('RAIN_KIT')
    if k:
        return os.path.abspath(k)
    d = HERE
    for _ in range(4):
        if os.path.exists(os.path.join(d, 'README_Rain.md')):
            return d
        d = os.path.dirname(d)
    return None


def out_dir():
    """where generators write (created on demand)"""
    o = os.environ.get('RAIN_OUT', os.path.join(HERE, '..', 'out'))
    os.makedirs(o, exist_ok=True)
    return os.path.abspath(o)


def find(name):
    """absolute path of a texture / data file by its file name"""
    cands = []
    if os.environ.get('RAIN_OUT'):
        cands.append(os.path.join(os.environ['RAIN_OUT'], name))
    cands.append(os.path.join(HERE, '..', 'out', name))
    k = kit_dir()
    if k:
        cands += sorted(glob.glob(os.path.join(k, 'Textures', '*', name)))
        cands += [os.path.join(k, 'Docs~', name), os.path.join(k, 'Tools~', 'meta', name)]
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise FileNotFoundError('%s (looked in: %s)' % (name, ', '.join(os.path.abspath(c) for c in cands)))


def lanbai_root():
    """the project root (holds deliver2/ and art/): $LANBAI_ROOT, else found by walking up from this file
    (inside the kit: <root>/deliver2/Rain/Tools~/src), else a sibling 'lanbai' folder of the working tools."""
    r = os.environ.get('LANBAI_ROOT')
    if r:
        return os.path.abspath(r)
    d = HERE
    for _ in range(6):
        if os.path.isdir(os.path.join(d, 'deliver2')) and os.path.isdir(os.path.join(d, 'art')):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(os.path.join(HERE, '..', '..', 'lanbai'))
