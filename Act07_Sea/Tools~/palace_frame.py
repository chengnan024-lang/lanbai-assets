# -*- coding: utf-8 -*-
"""Writes Act07_Sea/PalaceFrame_约定.json: the SEA side's placement contract for the 7b palace (the Palace session
(pkg/palace) owns Palace/PalaceLayout.json and the models; this file says where the bus passes, when, and the composition
the bus path was solved for, so the palace can be built around it). Was: the 7b palace layout (bible v2.1 §6·7b, §8.1 #10, #9b).

PALACE FRAME (all positions below): metres, Y up, Unity-handed (x right as seen from the bus, z = the bus's heading).
  x = 0  : the bus path (bus origin x).   The terrace edge face is at x = EDGE_X (left of the bus); the abyss is x > EDGE_X.
  y = 0  : the terrace top.               The bus origin glides at y = BUS_Y_STOP above it (floor + 0.62, eye + 1.70).
  z = 0  : the bus origin z at F5 (644.96).
The driver places R_Palace so that this frame moves past the fixed bus: R_Palace.position = -busPos(t) (+ the bus's
world origin). busPos(t) = (0, BUS_Y_STOP + (depth(F7) - depth(t)), fwd(t)), see act07_motion.py.

Composition the layout is solved for (bible §6·7b 构图):
  * avenue (神道) axis at x = -19.75: right lamp column x = -10.75, left column x = -28.75 (round 10, 10-26: the whole
    avenue moved 1.75 m left so it runs between the two que again, Que_R -12 / Que_L -27.5; it was -18 / -9 / -27);
  * the 12 lamp pairs are abreast of the bus at 672.0, 677.1, ... 728.6 (5.1 s apart) -> z_k = fwd(t_k);
  * the hall's open door is ON the avenue axis (x = -19.75) and the bus stops 35.3 m short of it at F7, so the door is at
    azimuth -6.7 deg (706), -16.7 deg (F6), -29.2 deg (F7) from the bus heading (was -6 / -15 / -27 with the axis at -18;
    STOP_GAP kept, so the hall stays at the same z);
  * the hall (60 m, 9 bays) runs from 1.75 m inside the terrace edge leftwards (moved with the avenue): the open door is bay 8 of 9 (counted from the left),
    so from the stopped bus the hall fills the windshield LEFT of the door and the right of the frame is the dark open
    abyss (bible: '右边是暗的空旷').  [decision: a Han hall's door is normally central; this asymmetry is the price of
    '门在神道轴线上、车左约 18 m' + '右边是暗的空旷' + a 60 m hall that does not hang over the cliff.]
  * the right que (紫贝阙, 40 m, x -12, unchanged) is passed at 9 m at 668.6; the left que at x -27.5.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(KIT)
sys.path.insert(0, os.path.join(REPO, 'Act07_Sea', 'Tools~'))
import act07_motion as M  # noqa: E402

EDGE_X = -8.0              # terrace edge face (vertical lip), seaweed-hung
LIP_BOTTOM_Y = -13.0       # lower edge of the lip: the bus eye passes it at ~F7p (bible: 'about 17 m below the stop')
BUS_Y_STOP = 2.5           # bus origin above the terrace top while gliding / stopped (lamp flames are BELOW the floor)
# palace round 10 (总导演 10-26, option c): the whole avenue 1.75 m left so it runs exactly between the two que again
# after the left que moved out (room for the waist eaves: 4-5 m between them); the right que stays put
AVENUE_SHIFT = -1.75
AXIS_X = -18.0 + AVENUE_SHIFT                       # -19.75
COL_R, COL_L = -9.0 + AVENUE_SHIFT, -27.0 + AVENUE_SHIFT   # -10.75, -28.75
QUE_R_X, QUE_L_X = -12.0, -27.5                     # centres; the avenue axis is their midpoint
PAIR_T = [672.0, 677.1, 682.3, 687.4, 692.6, 697.7, 702.8, 708.0, 713.1, 718.3, 723.4, 728.6]
STOP_GAP = 35.3            # bus origin -> door plane at F7 (18 / tan 27 deg)
HALL_W, HALL_BAYS, HALL_H, HALL_D = 60.0, 9, 30.0, 28.0
PLATFORM_H = 6.0
QUE_H = 40.0


def r3(v):
    return [round(float(x), 3) for x in v]


def bus_pos(t):
    """bus origin in the palace frame"""
    y = BUS_Y_STOP + (M.depth(M.L['F7']) - M.depth(t))
    return (0.0, y, M.fwd(t))


def main():
    L = M.L
    z_stop = M.fwd(L['F7'])
    z_door = z_stop + STOP_GAP
    pairs = [M.fwd(t) for t in PAIR_T]
    hall_x1 = EDGE_X + AVENUE_SHIFT      # hall (and platform) moved with the avenue so the open door stays ON its axis
    hall_x0 = hall_x1 - HALL_W
    bay = HALL_W / HALL_BAYS
    door_bay = int(round((AXIS_X - hall_x0) / bay - 0.5))          # 0-based
    door_x = hall_x0 + (door_bay + 0.5) * bay

    lamps = []
    for k, (t, z) in enumerate(zip(PAIR_T, pairs)):
        for side, x in (('R', COL_R), ('L', COL_L)):
            lamps.append(dict(id='Lamp_%s%02d' % (side, k + 1), group='avenue', pos=r3((x, 0.0, z)), yaw_deg=90.0 if side == 'R' else -90.0,
                              height_m=1.85 if k % 2 == 0 else 1.7, flame_pos=r3((x, 1.62 if k % 2 == 0 else 1.5, z)), pair=k + 1,
                              abreast_t=t))
    plat_front = z_door - 8.5           # the platform front edge (the hall stands 8.5 m back on its 6 m platform)
    for i, x in enumerate([door_x + 5.0, door_x - 5.0, door_x - 16.0, door_x - 27.0, door_x - 38.0, door_x - 48.0]):
        lamps.append(dict(id='Lamp_P%02d' % (i + 1), group='platform', pos=r3((x, PLATFORM_H, plat_front + 1.2)), yaw_deg=180.0,
                          height_m=1.9, flame_pos=r3((x, PLATFORM_H + 1.66, plat_front + 1.2))))

    # the two baked lights of every lamp (bible §6·7b 光; VRChat: Inspector value = E, CONTROL §3;
    # Unity baked point lights fall off as 1/d^2: intensity = E * d^2)
    baked = []
    for lp in lamps:
        f = lp['flame_pos']
        baked.append(dict(lamp=lp['id'], kind='warm', pos=f, color='#FF9C2F', range_m=4.0, E_at=[1.2, 2.0],
                          intensity=round(1.2 * 2.0 ** 2, 3), mode='Baked', shadows='soft', bounce=1.0))
        baked.append(dict(lamp=lp['id'], kind='indigo', pos=r3((f[0], f[1] + 0.3, f[2])), color='#2A557B', range_m=12.0, E_at=[0.6, 8.0],
                          intensity=round(0.6 * 8.0 ** 2, 3), mode='Baked', shadows='none', bounce=1.0))

    # fish-scale houses (鱼鳞屋): the other side of the avenue, two loose rows, 26 houses
    houses = []
    zs = [70 + 18.5 * i for i in range(14)]
    for i, z in enumerate(zs):
        for row, x in enumerate((-36.0, -52.0)):
            if row == 1 and i % 2 == 1 and i > 2:
                continue
            w = 9.0 + (i * 7 % 5) * 0.6
            houses.append(dict(id='FishHouse_%02d' % (len(houses) + 1), pos=r3((x - (i % 3) * 1.5, 0.0, z + (row * 6.0))),
                               yaw_deg=90.0 if row == 0 else 90.0 + (i % 2) * 4.0, size=r3((w, 4.8 + (i % 3) * 0.4, 7.0 + (i % 4) * 0.5))))
    houses = houses[:26]

    seaweed = []
    for i in range(30):
        if i < 18:      # on the lip face, hanging / standing along the edge
            z = -20 + i * 21.0 + (i * 37 % 11)
            seaweed.append(dict(id='Weed_%02d' % (i + 1), pos=r3((EDGE_X - 0.4, -2.0 - (i * 5 % 9), z)), height_m=2.0 + (i * 13 % 30) / 10.0))
        else:           # at the platform foot and the que bases
            z = plat_front - 1.0 if i < 26 else 40.0
            x = door_x + 3 - (i - 18) * 7.0 if i < 26 else (QUE_R_X if i % 2 else QUE_L_X)
            seaweed.append(dict(id='Weed_%02d' % (i + 1), pos=r3((x, 0.0, z)), height_m=2.0 + (i * 7 % 30) / 10.0))

    specks = dict(file='PalaceSpecks_Points.fbx', count=240, note='far lights of the drowned city beyond the fog: '
                  'points 140-650 m away on the terrace (left and ahead), fog-free with own attenuation (_FogMode 2, _Atten 0.004); '
                  'the same mesh hangs in the act-8 ceiling (Sea README §4)', region=dict(x=[-650, -60], y=[0.5, 30], z=[-150, 900]))

    J = dict(
        about='蓝白 · 第 7b 幕：海一侧的约定（宫殿系、车的路径、海要的灯位与时刻、_Udon_PalaceVeil）。由 Act07_Sea/Tools~/palace_frame.py 生成。'
              '宫殿布局的数据源是宫殿会话的 Palace/PalaceLayout.json；两者冲突时以 PalaceLayout.json 为准，海这边跟着改。',
        version=2,
        frame=dict(origin='x = bus path, y = terrace top, z = bus origin at F5 (644.96)', axes='Unity: x right (seen from the bus), y up, z = bus heading',
                   bus_origin_y_stop=BUS_Y_STOP, terrace_top_depth_m=round(M.depth(L['F7']) + BUS_Y_STOP, 3),
                   placement='R_Palace.localPosition = -busPos(t) (relative to the bus origin; bus at the world origin)'),
        labels_used={k: L[k] for k in ('F5', 'F5p', 'F5q', 'F5r', 'F6', 'F7', 'F7s', 'F7p', 'F8')},
        bus_samples=[dict(t=round(t, 2), pos=r3(bus_pos(t))) for t in [L['F5'] + 0.5 * i for i in range(int((M.EXIT - L['F5']) / 0.5) + 2)]],
        terrace=dict(top_y=0.0, edge_x=EDGE_X, lip_bottom_y=LIP_BOTTOM_Y, extent_x=[-260.0, EDGE_X], extent_z=[-120.0, 520.0],
                     note='the lip face (x = edge_x, y lip_bottom..0) is solid rock with seaweed; BELOW the lip the terrace has NO underside '
                          '(dream decision, README): from below, the palace lamps read as a constellation overhead (F7p); the buildings '
                          'are veiled by fog from below (global _Udon_PalaceVeil, see palace_veil)'),
        avenue=dict(axis_x=AXIS_X, columns_x=[COL_R, COL_L], pair_spacing_m=round(pairs[1] - pairs[0], 3), paving=dict(x=[COL_L - 1.5, COL_R + 0.5], z=[pairs[0] - 12.0, plat_front])),
        que=[dict(id='Que_R', pos=r3((QUE_R_X, 0.0, pairs[0] - 13.0)), footprint=r3((6.0, 10.0)), height_m=QUE_H, passed_at=668.6),
             dict(id='Que_L', pos=r3((QUE_L_X, 0.0, pairs[0] - 13.0)), footprint=r3((6.0, 10.0)), height_m=QUE_H)],
        hall=dict(id='Hall', x=[hall_x0, hall_x1], front_z=round(z_door, 3), depth_m=HALL_D, height_m=HALL_H, bays=HALL_BAYS, bay_m=round(bay, 4),
                  open_door_bay=door_bay + 1, door_x=round(door_x, 3), door_size=[4.2, 7.5], platform=dict(height_m=PLATFORM_H, front_z=round(plat_front, 3),
                  x=[hall_x0 - 4.0, EDGE_X + AVENUE_SHIFT], back_z=round(z_door + HALL_D + 6.0, 3), stair=dict(x=[door_x - 4.0, door_x + 4.0], z=[round(plat_front - 9.0, 3), round(plat_front, 3)])),
                  interior_emission=dict(color='#FFB74D', gain=3.0), door_cone_cards=dict(count=3, length_m=20.0, alpha=0.06)),
        door_azimuth_check={k: round(-math.degrees(math.atan2(-AXIS_X, z_door - M.fwd(t))), 2) for k, t in (('706', 706.0), ('F6', L['F6']), ('F7', L['F7']))},
        lamps=lamps,
        baked_lights=baked,
        palace_veil=dict(
            name='_Udon_PalaceVeil', type='float4',
            components=dict(x='density per m inside the veil band (0 = none)', y='WORLD y of the band top (= R_Palace world y + top_offset_palace_y)',
                            z='band thickness m (the band is y - z .. y)', w='> 0 = set (never set = no veil)'),
            meaning='the fog that veils the palace buildings when seen from BELOW the terrace (the terrace has no underside, F7p). '
                    'A fragment is veiled by the part of the eye->fragment segment that lies inside the horizontal band: '
                    'veil = 1 - exp(-x * L_band), L_band = |segment| * clamp-overlap of [y_eye, y_frag] with [y - z, y] / |y_frag - y_eye|. '
                    'From above the terrace (before F7s) the segment never crosses the band: no veil, automatically.',
            shader='col = lerp(col, LanbaiHorizon(normalize(posWS - eye)), veil)   (the water fog colour of that direction; after LanbaiApplyFog). '
                   'The lamp flames (_FogMode 2) do NOT take the veil: from below they are the constellation.',
            top_offset_palace_y=0.0, thickness_m=13.0,
            curve=[dict(t=L['F5'], x=0.0, note='7b-i: the bus is above the terrace'), dict(t=L['F7s'], x=0.0, note='descent past the lip begins'),
                   dict(t=L['F7p'], x=0.25, note='F7p: from below, 13 m of band -> 96 % veiled'), dict(t=L['F8'], x=0.25, note='held through 7c')],
            writer='the act-7 driver (sea), every frame from F5 to the exit 922.36; w = 1'),
        under_bus_light=dict(color='#FF5A2E', E_at_bus=0.15, follows='nearest avenue pair (by z), from below the floor', culling='Player, PlayerLocal + bus',
                             render_mode='Not Important (CONTROL: pixel-light budget; it is the only moving light under the floor)', window=[L['F5'], L['F7s'] + 8.0], then='7c rose light (Act07c)'),
        fish_houses=houses,
        seaweed=seaweed,
        fish=dict(count=1500, lite=700, centre=r3((-38.0, 14.0, z_door + 14.0)), torus_radius_m=35.0, tube_radius_m=9.0, rev_per_s=0.03,
                  length_cm=[12, 20], back='#34444E', belly='#B8C0C4', smoothness=0.85),
        specks=specks,
    )
    out = os.path.join(KIT, 'PalaceFrame_约定.json')
    json.dump(J, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', out)
    print('door x', door_x, 'bay', door_bay + 1, 'z_door', z_door, 'pairs', [round(p, 1) for p in pairs])
    print('door azimuths', J['door_azimuth_check'])


if __name__ == '__main__':
    main()
