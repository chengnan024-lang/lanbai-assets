#!/usr/bin/env python3
"""MirrorSchedule.json -> Mirrors/Editor/LanbaiMirrorsData.cs (static arrays the build menu copies into the driver;
Unity's JsonUtility cannot read nested arrays).  Run after make_schedule.py.  Generated, do not hand-edit."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
MIR = os.path.abspath(os.path.join(HERE, '..', '..'))
S = json.load(open(os.path.join(MIR, 'MirrorSchedule.json'), encoding='utf-8'))
M = S['mirrors']


def arr(name, vals, t='float'):
    if t == 'float':
        body = ', '.join(('%.6g' % v) + 'f' for v in vals)
    else:
        body = ', '.join(str(int(v)) for v in vals)
    return '        public static readonly %s[] %s = new %s[] { %s };\n' % (t, name, t, body)


kt, ky, kv, ks, kc = [], [], [], [], []
vt, vv, vs, vc = [], [], [], []
for m in M:
    ks.append(len(kt)); kc.append(len(m['motion']['knots']))
    for t, y, v in m['motion']['knots']:
        kt.append(t); ky.append(y); kv.append(v)
    vs.append(len(vt)); vc.append(len(m['visibility_knots']))
    for t, v in m['visibility_knots']:
        vt.append(t); vv.append(v)
out = ['// 蓝白 · 十三面镜的数据（由 Mirrors/Tools~/schedule/bake_cs.py 从 MirrorSchedule.json 生成，不要手改）。\n',
       '// Generated %s v%s. %d motion knots, %d visibility knots.\n' % ('MirrorSchedule.json', S['version'], len(kt), len(vt)),
       'namespace Lanbai.Mirrors.EditorTools\n{\n    public static class LanbaiMirrorsData\n    {\n',
       '        public static readonly float[] Eye = new float[] { %s };\n' % ', '.join('%.4gf' % x for x in S['conventions']['eye'])]
out.append(arr('TCross', [m['t_cross'] for m in M]))
out.append(arr('Diameter', [m['diameter_m'] for m in M]))
out.append(arr('CentreX', [m['centre_xz'][0] for m in M]))
out.append(arr('CentreZ', [m['centre_xz'][1] for m in M]))
out.append(arr('EmissionK', [m['emission_k'] for m in M]))
out.append(arr('PulseEV', [m['pulse_EV'] for m in M]))
out.append(arr('ActiveStart', [m['active'][0] for m in M]))
out.append(arr('ActiveEnd', [m['active'][1] for m in M]))
out.append(arr('DissolveEnd', [m['dissolve']['end'] if m['dissolve'] else 0.0 for m in M]))
out.append(arr('CrossSpeed', [m['speed_cross_mps'] for m in M]))
out.append(arr('KnotStart', ks, 'int'))
out.append(arr('KnotCount', kc, 'int'))
out.append(arr('KnotT', kt))
out.append(arr('KnotY', ky))
out.append(arr('KnotV', kv))
out.append(arr('VisStart', vs, 'int'))
out.append(arr('VisCount', vc, 'int'))
out.append(arr('VisT', vt))
out.append(arr('VisV', vv))
rs = M[12].get('rim_soft', dict(sharpen_from=M[12]['t_cross'] - 10.0, seconds=4.0, inner_frac=0.8))
out.append('        public static readonly float RimSoftStart = %.7gf, RimSoftSeconds = %.4gf, RimSoftFrom = %.4gf;\n' % (rs['sharpen_from'], rs['seconds'], rs['inner_frac']))
out.append('        public const string Scheme13 = "%s";\n' % M[12].get('scheme13', 'A'))
out.append('    }\n}\n')
os.makedirs(os.path.join(MIR, 'Editor'), exist_ok=True)
open(os.path.join(MIR, 'Editor', 'LanbaiMirrorsData.cs'), 'w', encoding='utf-8').write(''.join(out))
print('LanbaiMirrorsData.cs:', len(kt), 'knots')
