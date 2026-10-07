"""The window photograph as a TILT lens would take it (the focal plane lies ON the glass, at 56 deg incidence a normal
lens keeps only a vertical sliver of the pane sharp): the drops come from a render without depth of field (the
headset's view), everything seen through the clear glass between them from a render of the same shot with a flat,
dry pane and depth of field focused on the glass (the bokeh of the tube and the sign), the two blended by the
pane's water coverage as the camera sees it (GLASS_MODE=mask render, registered through the 5 mm slab).
usage: python3 tilt_composite.py <drops_dir> <clear_dir> <mask_dir> <out_dir>"""
import os, sys, json, shutil
import numpy as np
from scipy import ndimage
A, B, Mdir, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
a = np.load(os.path.join(A, 'stop.npy')); b = np.load(os.path.join(B, 'stop.npy')); m = np.load(os.path.join(Mdir, 'stop.npy'))
assert a.shape == b.shape == m.shape, (a.shape, b.shape, m.shape)
M = np.clip(m.mean(-1), 0, 1)
M = ndimage.gaussian_filter(M, 0.6)                 # the drop rims are where the two renders meet: soften by < 1 px
c = a * M[..., None] + b * (1.0 - M[..., None])
np.save(os.path.join(OUT, 'stop.npy'), c.astype(np.float32))
shutil.copy(os.path.join(A, 'stop_depth.npy'), os.path.join(OUT, 'stop_depth.npy'))
json.dump(dict(drops=A, clear=B, mask=Mdir, mask_mean=float(M.mean())), open(os.path.join(OUT, 'tilt.json'), 'w'))
print('composite', c.shape, 'mask mean %.3f' % M.mean())
