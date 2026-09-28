import numpy as np
from lutlib import *
d = np.load('../lens_cine/mock/frames.npz')
for key, prof in [('S3','S3'),('S4','S4'),('S6','S6'),('S8','S8'),('S9','S9a')]:
    fr = d[key][::2, ::2]
    neutral = ppv2.render(fr, {}, with_bloom=False)
    true = ppv2.render(fr, PROF[prof], with_bloom=False)
    lut = read_strip('../luts/Lanbai_%s_%s_1024x32.png' % (prof, dict(S3='03_liftoff_moon',S4='04_gate',S6='06_dawn',S8='08_dusk',S9a='09a_starsea')[prof]))
    got = apply_lut(np.round(neutral*255)/255, lut)
    e = np.abs(got - true) * 255
    print(key, prof, 'LUT vs HDR path: mean %.2f  p99 %.2f  max %.1f codes' % (e.mean(), np.percentile(e, 99), e.max()))
