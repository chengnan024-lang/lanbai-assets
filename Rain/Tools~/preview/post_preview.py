"""Grade a preview exactly like the Sign kit's previews (their post.py, loaded unchanged except for the path to
art/): K = 1.76 (enamel calibration), exponential fog 0.009 / #161B27 from the depth pass, PPv2 bloom (Unity-like
source clamp), S1 profile via the bible's PPv2 maths (Neutral tonemap, HDR grading), desktop LENS_CLEAN.
usage: python3 post_preview.py <dir> <name> <out_png> [profile] [K] [fog_density]"""
import sys, os, types
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import rainpaths as RP
LAN = RP.lanbai_root()
SRC = os.path.join(LAN, 'deliver2', 'Sign', 'Tools~', 'src', 'post.py')
ART = os.path.join(LAN, 'art')
code = open(SRC).read()
code = code.replace("ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'art')", "ART = %r" % ART)
post = types.ModuleType('post'); post.__file__ = SRC
exec(compile(code, SRC, 'exec'), post.__dict__)
d, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
prof = sys.argv[4] if len(sys.argv) > 4 else 'S1'
K = float(sys.argv[5]) if len(sys.argv) > 5 else 1.76
fog = float(sys.argv[6]) if len(sys.argv) > 6 else 0.009
post.run(os.path.join(d, name + '.npy'), os.path.join(d, name + '_depth.npy'), None, out, prof=prof, K=K, fog_density=fog)
print('wrote', out)
