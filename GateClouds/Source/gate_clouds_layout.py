"""蓝白 / Lanbai · gate clouds kit · writes GateClouds_Layout.json (what LanbaiGateCloudsBuilder.cs builds).

Inputs: Gate/GateLayout_v2.json (the clouds / towers / shafts / wedges the gate already placed), Textures/gate_cards.json
(the v2 cards' bboxes, bases and channel scales), Textures/deck_tiles.json. Output: ../GateClouds_Layout.json, in a
shape Unity's JsonUtility reads (arrays of objects with float[] fields only).

  python3 gate_clouds_layout.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.environ.get('GC_KIT', os.path.dirname(HERE))
REPO = os.path.dirname(os.path.dirname(HERE))
G = json.load(open(os.path.join(REPO, 'Gate', 'GateLayout_v2.json')))
CARDS = json.load(open(os.path.join(KIT, 'Textures', 'gate_cards.json')))
TILES = json.load(open(os.path.join(KIT, 'Textures', 'deck_tiles.json')))
CUES = G['timeline']['cues']
MOON = G['lights']['moon']['direction_to_light_unity']
EYE = (0.55, 1.7, 2.05)
HERO_T = CUES['U7b']
WINDOW_BEFORE_U6 = 20.0      # GateRoot is activated at U6 - 20 (README_GateLayout §2)
WINDOW_AFTER_U9 = 2.0


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def h_bus(t):
    if t <= CUES['U6']:
        return 40.0
    if t <= 160.5:
        return 40.0 + 20.0 * ss((t - CUES['U6']) / (160.5 - CUES['U6']))
    return 60.0 + 90.0 * ss((t - 160.5) / (CUES['U9'] - 160.5))


def gate_root(t):
    return (0.0, 150.0 - h_bus(t), 59.0164 * (CUES['U9'] - t))


def shape_of(card):
    return card.replace('Cloud_', '').replace('_moon', '')


GROUP = {
    'tower': dict(queue=3000, melt=[-30.0, 150.0], fog_cap=0.5),       # round 2: a 30-60 m mist skirt (art r1 #4)
    'far': dict(queue=2990, melt=[-10.0, 130.0], fog_cap=0.70),        # round 4 (art r2): far banks +13 % fog
    'horizon': dict(queue=2990, melt=[-10.0, 130.0], fog_cap=0.70),
    'mist': dict(queue=3000, melt=[-10.0, 60.0], fog_cap=0.7),
}


PARALLAX_SIDE, PARALLAX_W, PARALLAX_H, PARALLAX_CROP = 0.35, 1.0, 1.3, 0.45
PARALLAX_N, PARALLAX_DEPTH = 2, 0.15     # round 10: the tower back layers (see main)
# only Colossus_2 (left of the tear, its crown clearly seen): with Colossus_3 too (right, mostly behind the near slab
# and arms) the keyart card overdraw is 0.93-0.98 FSE even with the cropped quads (budget <= 0.9)
PARALLAX_IDS = ('Tower_Colossus_2',)


def card_entry(cid, group, src, keys=None):
    shp = shape_of(src['card'])
    m = CARDS[shp]
    bw = m['bbox_uv'][2] - m['bbox_uv'][0]
    qw = src['width_m'] / bw
    qh = qw * m['size'][1] / m['size'][0]
    if src.get('height_m'):          # towers: the JSON height is the CLOUD's height (base -> top of the bbox)
        bh = m['bbox_uv'][3] - m['cloud_base_v']
        qh = src['height_m'] / max(bh, 1e-3)
    # mirror: the bake's moon is on the card's RIGHT; mirror when the gate moon is on its left at the hero time
    gr = gate_root(HERO_T)
    p = [gr[0] + src['position'][0], gr[1] + src['position'][1], gr[2] + src['position'][2]]
    lx, lz = p[0] - EYE[0], p[2] - EYE[2]
    right = (lz, -lx)
    moon_right = MOON[0] * right[0] + MOON[2] * right[1] > 0
    los = math.atan2(lx, lz)
    rel = abs(math.degrees(math.atan2(MOON[0], MOON[2]) - los))
    e = dict(id=cid, group=group, shape=shp, position=[round(v, 2) for v in src['position']],
             size=[round(qw, 1), round(qh, 1)], opacity=src.get('opacity', 1.0), gain=src.get('gain', 1.0),
             mirror=0.0 if moon_right else 1.0, queue=GROUP[group]['queue'], melt=GROUP[group]['melt'], fog_cap=GROUP[group]['fog_cap'],
             moon_rel_deg_U7b=round(rel, 1), sag_keys=[], sink_keys=[], alpha_keys=[])
    if keys:
        for k in ('sag_keys', 'sink_keys', 'alpha_keys'):
            e[k] = [round(v, 3) for kv in keys.get(k, []) for v in kv]    # flattened t0, v0, t1, v1, ...
        e['hides'] = keys.get('hides', '')
    return e


def main():
    cards = []
    for it in G['towers']['items']:
        cards.append(card_entry(it['id'], 'tower', it, it))
    # round 10 (art r3 #5, stranger r2: "flat cardboard"; option A in 给总控 §7, 总导演 D-15): the PARALLAX_N towers nearest the
    # U7b eye get a BACK LAYER: a second card 15 % of their distance further along the line of sight, offset sideways by a
    # quarter of their width (alternating), another silhouette of the same aspect (Puff behind Congestus, Congestus behind Bank), 0.85 x the width (its own aspect), gain 0.8, opacity
    # 0.9, the same sag / sink / alpha keys (it collapses with its tower). As the bus moves, the two layers slide past
    # each other: parallax, and the crown reads layered instead of one flat silhouette
    gr = gate_root(HERO_T)
    def dist(it):
        return math.hypot(gr[0] + it['position'][0] - EYE[0], gr[2] + it['position'][2] - EYE[2])
    near = [it for it in sorted(G['towers']['items'], key=dist)[:PARALLAX_N] if it['id'] in PARALLAX_IDS]
    for k, it in enumerate(near):
        px, pz = gr[0] + it['position'][0] - EYE[0], gr[2] + it['position'][2] - EYE[2]
        d = math.hypot(px, pz)
        fx, fz = px / d, pz / d
        side = (1 if k % 2 == 0 else -1) * PARALLAX_SIDE * it['width_m']
        back = dict(it)
        back['position'] = [it['position'][0] + fx * PARALLAX_DEPTH * d + fz * side, it['position'][1],
                            it['position'][2] + fz * PARALLAX_DEPTH * d - fx * side]
        back['card'] = it['card']                 # only Congestus is tower-shaped (cloud h / w 1.0; Puff 0.41 hides behind)
        back['width_m'] = it['width_m'] * PARALLAX_W
        if it.get('height_m'):
            back['height_m'] = it['height_m'] * PARALLAX_H     # the crown must rise above the front tower's to be seen
        back['gain'] = it.get('gain', 1.0) * 0.8
        back['opacity'] = it.get('opacity', 1.0) * 0.9
        e = card_entry(it['id'] + '_Back', 'tower', back, it)
        e['parallax_of'] = it['id']
        e['crop_bottom'] = PARALLAX_CROP          # its lower part is always behind the front tower and the deck
        # not flipped: the mirror carries the moon side (a flipped back layer has its silver lining away from the moon);
        # 1.3 x the height and the side offset make it read as another crown, not a copy
        cards.append(e)
    for k, it in enumerate(G['clouds']['far']):
        cards.append(card_entry('Far_%02d' % k, 'far', it))
    # round 2 (art r1 #5): the horizon masses were near-symmetric islands of one height: widths x 0.8-1.3, heights
    # x 0.55-1.65 (a 3x spread), seeded, so the far line breaks up at different heights
    import random
    rnd = random.Random(11)
    for k, it in enumerate(G['clouds']['horizon_relief']['items']):
        e = card_entry('Horizon_%02d' % k, 'horizon', it)
        sw, sh = rnd.uniform(0.8, 1.3), rnd.uniform(0.55, 1.65)
        e['size'] = [round(e['size'][0] * sw, 1), round(e['size'][1] * sh, 1)]
        cards.append(e)
    for k, it in enumerate(G['clouds']['mist']):
        cards.append(card_entry('Mist_%02d' % k, 'mist', it))
    shapes = []
    for shp, m in CARDS.items():
        if shp.startswith('_'):
            continue
        cu = 0.5 * (m['bbox_uv'][0] + m['bbox_uv'][2])
        shapes.append(dict(shape=shp, texture='GateCard_%s.png' % shp, size_px=m['size'], scale=m['scale'],
                           pivot_uv=[round(cu, 4), m['cloud_base_v']], bbox_uv=m['bbox_uv']))
    shafts = []
    for it in G['shafts']['items']:
        shafts.append(dict(id=it['id'], parent='Tear_Root', mode=0.0, start=it['start_os'], axis=it['axis_os'],
                           half_width=it['half_width_m'], length=it['length_m'], widen=it['widen'],
                           intensity=round(0.35 * it['gain'], 4)))
    for it in G['shadow_wedges']['items']:
        shafts.append(dict(id=it['id'], parent='GateRoot', mode=1.0, start=it['start'], axis=it['axis'],
                           half_width=it['half_width_m'], length=it['length_m'], widen=it['widen'],
                           intensity=it['alpha']))
    y_bot = -150.0 + TILES['h_macro'][0] + TILES['h_detail'][0] * TILES.get('shader_amp_range', [0.3, 0.8])[1] - 5.0
    out = dict(
        about='蓝白 gate clouds kit v1 (2026-10-22): the cloud deck, the v2 cloud cards (towers, far banks, horizon '
              'masses, mist), the widening shafts and the shadow wedges. Positions in the GateRoot frame (or '
              'Tear_Root object space for the shafts), exactly as GateLayout_v2.json. Built by '
              'Editor/LanbaiGateCloudsBuilder.cs; animated by Runtime/LanbaiGateClouds.cs. Keys are flattened '
              '(t0, v0, t1, v1, ...), timeline seconds, smoothstep between keys.',
        hero_t=HERO_T,
        window=[round(CUES['U6'] - WINDOW_BEFORE_U6, 2), round(CUES['U9'] + WINDOW_AFTER_U9, 2)],
        # act 4's light-fog band colour (= LanbaiGateSky _HazeNear, GateLayout sky_band 'gain') and until when the gate
        # writes it: U9, then the inside driver (chief engineer 10-23, tech r3 #3)
        fog_band=dict(color=[0.1085, 0.1130, 0.1641, 1.0], until=CUES['U9']),
        deck=dict(parent='GateRoot', local_y=round(y_bot, 2), quad_size=40000.0,
                  detail='Deck_Detail_1024.png', macro='Deck_Macro_512.png',
                  note='a flat quad under the deck slab, moving with GateRoot; Lanbai/GateCloudDeck ray-marches '
                       'the billows and writes their depth. Material = the shader defaults (= deck_ref.DEFAULTS).',
                  # the deck's quality switch (总导演 10-23 / D-15: merge first, measure, then cut in bible 1.9 order):
                  # the builder writes the chosen tier's _Adapt / _MarchRange / _Steps onto M_GateCloudDeck
                  quality='default',
                  quality_tiers=[
                      dict(name='default', adapt=[0.004, 0.05, 0.9, 0.6], march_range=[12.0, 2500.0, 8.0, 3.0], steps=128,
                           note='the reference look; mean march steps keyart 24.2 / U7 16.4 / U8 fwd 15.6 / U8 side 20.3'),
                      dict(name='auto_lite', adapt=[0.004, 0.09, 0.9, 0.6], march_range=[12.0, 2500.0, 8.0, 3.0], steps=128,
                           note='bigger steps away from the surface: 9-16 % fewer steps, image change mean <= 0.08 / '
                                'p99 <= 1 code (Docs~/perf_options_crops.png option C)'),
                  ]),
        shapes=shapes, cards=cards, beams=shafts,
        tide_material=dict(note='gate_test §2.2 item 10: Lanbai_TentacleTide_v2.shader is now v2.3 (includes '
                                'LanbaiGateSky.cginc; these are its new defaults). Existing materials M_TentacleTide_A / B '
                                'keep their old values: set these on them (or reset the properties):',
                           _HazeNear=[0.1085, 0.1130, 0.1641, 1.0], _HazeFar=[0.0436, 0.0504, 0.0726, 1.0],
                           _BandEl=[6.0, 22.0, 2.0, 0.0]),
    )
    path = os.path.join(KIT, 'GateClouds_Layout.json')
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)
    print('wrote', path, len(cards), 'cards', len(shafts), 'beams')


if __name__ == '__main__':
    main()
