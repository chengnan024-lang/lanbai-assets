# -*- coding: utf-8 -*-
"""写 Palace/PalaceLayout.json（唯一的数据源 = 海的约定 + 宫殿自己的东西）和 Palace/Editor/LanbaiPalaceData.cs（搭建脚本用的静态数据，生成的，不要手改）。
python3 gen_layout.py"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_layout as L  # noqa: E402
from grade import srgb_to_lin  # noqa: E402

REPO = L.REPO
TUNE = json.load(open(os.path.join(HERE, 'tuning.json')))


def lin(h):
    return [round(float(x), 5) for x in srgb_to_lin(h)]


def main():
    F = L.FRAME
    T = TUNE
    terrace_depth = F['frame']['terrace_top_depth_m']
    lamps = []
    for l in F['lamps']:
        fp = l['flame_pos']
        lamps.append(dict(id=l['id'], group=l['group'], pos=l['pos'], height_m=l['height_m'], flame_pos=fp,
                          abreast_t=l.get('abreast_t'),
                          baked=[dict(kind='warm', pos=fp, color='#FF9C2F', range_m=T['warm_range'], intensity=T['warm_I'],
                                      shadows='soft', mode='Baked'),
                                 dict(kind='indigo', pos=[fp[0], round(fp[1] + 0.3, 3), fp[2]], color='#2A557B', range_m=T['indigo_range'],
                                      intensity=T['indigo_I'], shadows='none', mode='Baked')]))
    H = F['hall']
    door_spill = dict(type='Area (Baked)', shape='rectangle', size=[round(H['door_size'][0] * 0.95, 2), round(H['door_size'][1] * 0.95, 2)],
                      pos=[H['door_x'], round(L.PLAT['height_m'] + H['door_size'][1] / 2, 3), round(L.DOOR_Z + 0.6, 3)],
                      facing=[0, 0, -1], color='#FFB74D', intensity=T['door_area_I'],
                      note='Unity 面光的 Intensity：面光发出的辐亮度 = color × intensity（Inspector = E 的约定下按灰卡校：门前 6 m 灰卡读数见 README）')
    J = dict(
        about='蓝白 · 第 7b 幕河伯宫殿布局（宫殿出；内容与海的 Act07_Sea/PalaceFrame_约定.json 一致，那份是车路与构图的合同）。'
              '宫殿坐标：米，Unity 轴；x = 0 车路，y = 0 台地顶，z = 0 F5 时的车根。由 Palace/Source/gen_layout.py 生成。',
        version=2,
        frame=dict(F['frame'], parent='R_Sea', local_position_in_R_Sea=[0.0, -terrace_depth, 0.0],
                   note='R_Palace 挂在 R_Sea 下（海的驱动让 R_Sea = (0, depth, −fwd)），局部位置是常数 → R_Palace 世界位置 = −busPos(t)。'),
        labels_used=F['labels_used'],
        sources=dict(sea_contract='Act07_Sea/PalaceFrame_约定.json', rulings='Art/总导演裁决.md D-17 D-24 D-27 D-28 D-29'),
        terrace=F['terrace'], avenue=F['avenue'], que=F['que'], hall=F['hall'], fish_houses=F['fish_houses'],
        seaweed=F['seaweed'], fish=dict(F['fish'], shader='Lanbai/PalaceFish', b_school=dict(pass_t=720.0, note='河伯诗那一刻从诗前面游过一次')),
        specks=F['specks'], palace_veil=dict(name='_Udon_PalaceVeil', writer='海（第 7 幕驱动）', readers=['Lanbai/Palace', 'Lanbai/PalaceGlow'],
                                              not_readers=['Lanbai/PalaceFlame（灯焰从下面看就是星座）', 'Lanbai/PalaceFish']),
        lamps=lamps, door_spill=door_spill,
        door_glow=dict(color='#FFB74D', gain=3.0, atten=0.004, plane_z=round(L.DOOR_Z + 5.0, 2), cones=dict(count=3, length_m=20.0, alpha=0.06)),
        flames=dict(shader='Lanbai/PalaceFlame', flame_fill='#FF5E2A @ +3.11', flame_linear=[round(c * 2 ** 3.11, 4) for c in lin('#FF5E2A')],
                    screen='#FFC46A', halo_radius_m=1.5, halo_mid_fill='#446282', atten=0.004, fps=6, min_pixels=1.2),
        analytic_lamps=dict(globals='_Udon_Lamp0..7 / LampColor / LampDir / LampAxis', writer='LanbaiPalaceDriver（离主座位眼睛最近的 8 盏）',
                            intensity=T['warm_I'], color='#FF9C2F', radius_m=0.10),
        ambient_for_bake=dict(mode='Trilight', sky='#0E3050', equator='#0A2238', ground='#1A1422',
                              note='圣经 §6·7b 的 Trilight；烘焙时设成这样（光照贴图里带着环境光），Udon 之后改环境色不影响宫殿'),
        tuning=T,
        render=dict(fog_density=0.018, fog_up_fill='#182930', fog_mid_fill='#0C171E', fog_down_fill='#020302',
                    note='参考渲染的水色（屏幕 #06202C / #04121E / #02070F，按 S7b 引擎反解）；Unity 里由海的 LanbaiFog 水下参数组给'),
        motion_samples=[dict(t=round(t, 2), bus=[round(float(x), 3) for x in L.car(t)]) for t in [644.96, 655.86, 668.6, 672.0, 690.0, 706.0, 714.0,
                                                                                         728.6, 735.56, 740.26, 748.26, 796.86, 812.36, 835.16, 875.16]],
    )
    json.dump(J, open(os.path.join(REPO, 'Palace', 'PalaceLayout.json'), 'w'), ensure_ascii=False, indent=1)
    # ---- C# 数据
    def arr(a):
        return '{ ' + ', '.join('%.5ff' % x for x in a) + ' }'
    flames = [c for l in F['lamps'] for c in l['flame_pos']]
    cs = []
    cs.append('// 生成的（Palace/Source/gen_layout.py），不要手改。数据源 = Palace/PalaceLayout.json')
    cs.append('public static class LanbaiPalaceData')
    cs.append('{')
    cs.append('    public const float TerraceDepth = %.4ff;' % terrace_depth)
    cs.append('    public static readonly float[] Flames = %s;' % arr(flames))
    cs.append('    public static readonly string[] LampIds = { %s };' % ', '.join('"%s"' % l['id'] for l in F['lamps']))
    cs.append('    public const float WarmI = %.4ff, WarmRange = %.3ff, IndigoI = %.4ff, IndigoRange = %.3ff, IndigoLift = 0.3f;' % (T['warm_I'], T['warm_range'], T['indigo_I'], T['indigo_range']))
    cs.append('    public static readonly float[] WarmColor = %s;   // 线性 #FF9C2F' % arr(lin('#FF9C2F')))
    cs.append('    public static readonly float[] IndigoColor = %s;   // 线性 #2A557B' % arr(lin('#2A557B')))
    cs.append('    public static readonly float[] DoorSpillPos = %s;' % arr(door_spill['pos']))
    cs.append('    public static readonly float[] DoorSpillSize = %s;' % arr(door_spill['size']))
    cs.append('    public static readonly float[] DoorColor = %s;   // 线性 #FFB74D' % arr(lin('#FFB74D')))
    cs.append('    public const float DoorAreaI = %.4ff;' % T['door_area_I'])
    cs.append('    public static readonly float[] AmbSky = %s, AmbEquator = %s, AmbGround = %s;' % (arr(lin('#0E3050')), arr(lin('#0A2238')), arr(lin('#1A1422'))))
    cs.append('    public static readonly float[] FlameLinear = %s;' % arr(J['flames']['flame_linear']))
    cs.append('    public static readonly float[] HaloMid = %s;' % arr(lin('#446282')))
    cs.append('    public static readonly float[] FishCentre = %s;' % arr(F['fish']['centre']))
    cs.append('    public const float FishR = %.2ff, FishTube = %.2ff, FishRev = %.4ff;' % (F['fish']['torus_radius_m'], F['fish']['tube_radius_m'], F['fish']['rev_per_s']))
    import scene_math
    pp = scene_math.poem_point()
    cs.append('    public static readonly float[] FishPassPoint = %s;' % arr(list(pp) + [720.0]))
    cs.append('    public static readonly float[] FishPassVel = { -2.2f, 0.1f, 0.4f, 0f };')
    cs.append('}')
    open(os.path.join(REPO, 'Palace', 'Editor', 'LanbaiPalaceData.cs'), 'w').write('\n'.join(cs) + '\n')
    print('wrote PalaceLayout.json, LanbaiPalaceData.cs')


if __name__ == '__main__':
    main()
