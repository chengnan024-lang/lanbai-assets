"""Check that FreeType (what TMP 3.0's FontEngine uses) sees the 'kern' table in the Latin subsets.
Uses the system libfreetype through ctypes: FT_Get_Kerning(FT_KERNING_UNSCALED) for a few pairs."""
import ctypes, ctypes.util, sys, os
from fontTools.ttLib import TTFont
lib = ctypes.CDLL(ctypes.util.find_library('freetype') or 'libfreetype.so.6')
class FT_Vector(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
lib.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
lib.FT_New_Face.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p)]
lib.FT_Get_Char_Index.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
lib.FT_Get_Char_Index.restype = ctypes.c_uint
lib.FT_Get_Kerning.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(FT_Vector)]
maj, mi, pa = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
libp = ctypes.c_void_p()
assert lib.FT_Init_FreeType(ctypes.byref(libp)) == 0
lib.FT_Library_Version(libp, ctypes.byref(maj), ctypes.byref(mi), ctypes.byref(pa))
print('FreeType %d.%d.%d' % (maj.value, mi.value, pa.value))
HERE = os.path.dirname(os.path.abspath(__file__))
fonts = sys.argv[1:] or [os.path.join(HERE, '..', 'Subset', f) for f in
         ('EBGaramond-Regular.Lanbai.ttf', 'EBGaramond-Italic.Lanbai.ttf', 'BarlowSemiCondensed-SemiBold.Lanbai.ttf', 'IMFellEnglish-Roman.Lanbai.ttf')]
for fn in fonts:
    face = ctypes.c_void_p()
    assert lib.FT_New_Face(libp, fn.encode(), 0, ctypes.byref(face)) == 0
    t = TTFont(fn)
    kt = {}
    if 'kern' in t:
        for st in t['kern'].kernTables:
            kt.update(st.kernTable)
    cm = t.getBestCmap()
    out = []
    ok = True
    for a, b in ('AV', 'To', 'Wa', 'Yo', 'Te', 'Fl', 'wa', 'y.'):
        la, lb = lib.FT_Get_Char_Index(face, ord(a)), lib.FT_Get_Char_Index(face, ord(b))
        v = FT_Vector()
        lib.FT_Get_Kerning(face, la, lb, 2, ctypes.byref(v))       # 2 = FT_KERNING_UNSCALED (font units)
        exp = kt.get((cm[ord(a)], cm[ord(b)]), 0)
        ok &= (v.x == exp)
        out.append('%s%s %d/%d' % (a, b, v.x, exp))
    print('%-42s %s   %s' % (os.path.basename(fn), 'FreeType == table' if ok else 'MISMATCH', '  '.join(out)))
