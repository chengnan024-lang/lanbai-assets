"""quick: npy -> png (clay: plain sRGB; night: S2 grade with fog)"""
import sys, numpy as np
sys.path.insert(0, '..'); sys.path.insert(0, '.')
import lk_post as P
from PIL import Image
for f in sys.argv[1:]:
    x = np.load(f)
    if 'night' in f:
        c = P.to_codes(x, 'S2')
    else:
        c = np.clip(x, 0, 1) ** (1 / 2.2) * 255
    Image.fromarray(np.clip(np.round(c), 0, 255).astype(np.uint8)).save(f.replace('.npy', '.png'))
