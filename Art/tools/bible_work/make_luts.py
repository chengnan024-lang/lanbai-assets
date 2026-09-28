import os, numpy as np
from lutlib import *
OUT = '../luts'; os.makedirs(OUT, exist_ok=True); os.makedirs(OUT + '/hdr_external', exist_ok=True)
NAMES = {'S1': '01_stop', 'S2': '02_nightroad', 'S3': '03_liftoff_moon', 'S4': '04_gate', 'S4c': '04c_inside_tear', 'S6': '06_dawn',
         'S7a': '07a_undersea', 'S7b': '07b_deep_palace', 'S8': '08_dusk', 'S8b': '08b_bluehour', 'S9a': '09a_starsea',
         'S9b': '09b_starsea_climax', 'S10': '10_white', 'S11': '11_false_wake', 'S12': '12_wake'}
# neutral
g = np.arange(N) / (N - 1)
B, G, R = np.meshgrid(g, g, g, indexing='ij')
neutral = np.stack([R, G, B], -1)
write_strip(neutral, OUT + '/Lanbai_Neutral_1024x32.png')
write_cube(neutral, OUT + '/Neutral.cube', 'Lanbai Neutral (identity)', comment=['identity LUT: applying it must change nothing'])
# verify neutral strip round trip under PPv2-like sampling
rs = np.random.default_rng(1).random((20000, 3))
back = apply_lut(rs, read_strip(OUT + '/Lanbai_Neutral_1024x32.png'))
print('neutral strip max error (codes):', np.abs(back - rs).max() * 255)
for k, name in NAMES.items():
    lut = lut3d(PROF[k])
    fn = 'Lanbai_%s_%s' % (k, name)
    write_strip(lut, '%s/%s_1024x32.png' % (OUT, fn))
    write_cube(lut, '%s/%s.cube' % (OUT, fn), 'Lanbai %s %s' % (k, name),
               comment=['Lanbai grade %s (%s), 32^3, sRGB display in -> sRGB display out.' % (k, GF['profiles'][k]['name']),
                        'Input = a frame rendered with PPv2 HDR grading + Neutral tonemapper at default settings (profile S10).',
                        'Output = the same frame under profile %s (postExposure, WB, contrast, lift/gamma/gain, saturation). No bloom/vignette/grain.' % k])
    hx = hdr_external(PROF[k])
    write_cube(hx, '%s/hdr_external/%s_HDRext33.cube' % (OUT, fn), 'Lanbai %s HDR External' % k,
               comment=['PPv2 HDR "External" LUT for profile %s. Input domain = ALEXA LogC (PPv2 LUT_SPACE_ENCODE), output = display-LINEAR.' % k,
                        'postExposure %.2f is BAKED IN: set the profile postExposure to 0 when using this LUT.' % ppv2.full(PROF[k])['postExposure']])
    s10 = np.abs(lut - neutral).max() * 255 if k == 'S10' else None
    print(k, fn, 'mid-grey out', ppv2.srgb_to_hex(apply_lut(np.array([[0.46, 0.46, 0.46]]), lut)[0]), 'S10 deviation from identity (codes): %s' % s10)
