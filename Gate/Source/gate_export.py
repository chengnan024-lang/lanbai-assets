"""蓝白 / Lanbai · 触手之门 layout v4 (gate round 3) · export (Unity 2022.3, metres, Y up).

    python3 gate_export.py            -> GateLayout_v2.json, GateLayout_v2.fbx (empties), GateArms_v3.fbx (baked
                                         per-instance arm meshes: empty <id> with children <id>_LOD0/1/2, UV0 UVMap,
                                         UV1 UVSway, UV2 UVRadius), TentacleTide_v2.fbx (tide quads),
                                         Textures/Tear_CloudLanes_1024.png (shadow lanes for Tear_CloudGlow)
    python3 gate_export.py --json     -> the JSON only

CONVENTIONS (also written into the JSON):
  * Unity world: the bus is FIXED at the origin facing +Z; the world moves past it.
  * GateRoot local frame (all gate content is a child of GateRoot): origin = the ENTRY POINT, where the bus origin
    passes through the tear plane at U9 (15 % of the tear's height there, 150 m above the cloud-sea top); x right
    (seen from the bus), y up, z forward = away from the bus; the tear faces -Z (toward the bus).
  * GateRoot.position(t) = (0, gate_y(t), gate_z(t)), rotation 0, scale 1 (formulas below; Udon drives it).
  * Every instance's position / rotation is its FINAL pose (after rise / lean / track; before 'close');
    rotation_U7b_xyzw / position_U7b give the pose at U7b (the key art). Animations are relative to the final pose.
  * Arm meshes: GateArms_v3.fbx: per instance an empty <id> with three children <id>_LOD0 / _LOD1 / _LOD2 (Unity's
    importer builds one LODGroup per <id>). The arm form is BAKED (v4 custom centrelines for the heroes, girth,
    ridges <= 2 %) in the instance's own local space (UV0 'UVMap', UV1 'UVSway' (t, phase), UV2 'UVRadius' (x = the
    baked local radius / root radius: the shader's pixel rim, 1 px inflation and tip thresholds), vertex colour Col
    kept). Instance transform = position / rotation / uniform scale from here. Material = Lanbai/TentacleSway v2.4
    (_UseUVRadius 1, _Girth 1).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_layout as G  # noqa: E402

OUT_JSON = os.path.join(HERE, 'GateLayout_v2.json')
OUT_FBX = os.path.join(HERE, 'GateLayout_v2.fbx')
OUT_ARMS = os.path.join(HERE, 'GateArms_v3.fbx')
OUT_TIDE = os.path.join(HERE, 'TentacleTide_v2.fbx')
OUT_TEX = os.path.join(HERE, 'Textures')
M_W = G.M_W
B2U = G.B2U
C = G.CUE


def r3(v, n=3):
    return [round(float(x), n) for x in v]


def q_xyzw(Ru):
    return [round(float(c), 6) for c in G.BL._quat_from_matrix(Ru)]


def euler(Ru):
    return G.BL._unity_euler(Ru)


def u_pos(p_cf):
    return G.cf_to_unity_local(np.asarray(p_cf, float))


def u_rot(R_cf):
    return G.rot_to_unity(R_cf)


PROFILES = {
    'ss': 'w = s*s*(3 - 2*s), s = saturate((t - t0) / (t1 - t0))   (peak speed 1.5 x mean)',
    'trap': 'trapezoid, ease e: s = saturate((t - t0) / (t1 - t0)), vm = 1 / (1 - e); w = vm s^2 / (2e) (s < e); '
            'vm (s - e/2) (e <= s <= 1 - e); 1 - vm (1 - s)^2 / (2e) (s > 1 - e)',
    'beta': 'fast-then-slow (the bus keeps approaching): s = saturate((t - t0) / (t1 - t0)), b = 3.5; '
            'w = 1 - (1 - s)^b (1 + b s)   (peak at s = 1/b, ~1.9 x mean)',
}


def prof_param(a):
    """the profile's parameter (trap: ease fraction e; beta: exponent b), as gate_layout.prof reads it"""
    k = a.get('prof', 'ss')
    if k == 'trap':
        return dict(ease_e=round(float(a.get('ease', 0.2)), 3))
    if k == 'beta':
        e = a.get('ease', 0.2)
        return dict(beta_b=round(float(e if e > 1.0 else 3.5), 3))
    return {}


def timeline_block():
    ts = np.round(np.arange(C['U6'], C['U9'] + 0.01, 0.5), 2)
    samples = [dict(t=float(t), z=round(G.gate_z(t), 2), y=round(G.gate_y(t), 2), h_bus=round(G.h_bus(t), 2),
                    tear_H=round(G.tear_H(t), 1), tear_open=round(G.tear_open(t), 4), rip=round(G.rip_progress(t), 4))
               for t in ts]
    return dict(
        cues=C, v_g_m_per_s=round(G.V_G, 4),
        GateRoot_z='gate_z(t) = %.4f * (%.2f - t)   for t <= U9 (constant world speed, no ease: the arms are '
                   'rooted in the cloud sea and would slide on it if the world eased).' % (G.V_G, C['U9']),
        GateRoot_active='round 3 (tech B1): SetActive(true) at t = U6 - 20 s = %.2f, while the bus is still inside the '
                        'white cloud occluder (bible 1.9 / 6.3); every giant is then already STANDING in its final pose '
                        '(no rise before U6 is ever seen) and hidden by its _Reveal = 0 (renderer off) and its cloud '
                        'tower. Rises that start before activation: start the instance at its pose at activation '
                        '(evaluate the rise at t = %.2f).' % (C['U6'] - 20.0, C['U6'] - 20.0),
        GateRoot_y='gate_y(t) = %.1f - h_bus(t): the cloud-sea top is at world y = -h_bus(t)' % G.ENTRY_H,
        h_bus='h_bus(t) = 40 (U6 - 20 <= t <= U6: GateRoot is only active from U6 - 20, inside the white cloud, where '
              'the act-3 climb has already brought the bus to the cloud-top layer); 40 + 20*smoothstep((t-U6)/(%.2f-U6)) '
              '(U6..%.2f); 60 + 90*smoothstep((t-%.2f)/(U9-%.2f)) (%.2f..U9). Peak vertical acceleration 1.49 m/s^2 '
              '(bible 1.8: <= 1.5).'
              % (G.CLIMB_T0, G.CLIMB_T0, G.CLIMB_T0, G.CLIMB_T0, G.CLIMB_T0),
        tear_H_knots=[dict(t=t, H=h) for t, h in G._H_KNOTS],
        tear_H='monotone PCHIP through the knots; Tear_Root.localScale = H/1000',
        tear_open='_Udon_TearOpen: 0 (U6) -> 0.333 smoothstep (U7) -> 1 smoothstep (U8); width 18 % -> 30 % of H',
        rip='_Udon_RipProgress = smoothstep((t - U7) / 16)',
        globals_every_frame=dict(
            _Udon_CloudTop='(x = -h_bus(t), w = 1): world y of the cloud-sea top (arms fade into it / clip below)',
            _Udon_TearPos='(GateRoot.position + (0, -%.0f + 0.4 H(t), 0), w = 1): the tear core, world (round 2: '
                          'replaces the per-material _TearPos constant)' % G.ENTRY_H,
            _Udon_GateTime='t (timeline seconds): the tide rise',
            _Udon_TearH='(H(t), 0, 0, 1): the tear height (m) -- the fog colour\'s halo term',
            _Udon_MoonDir='(direction TO the moon, world, w = 1): the fog colour\'s moon-air term and the rims'),
        reference_camera='far plane >= 14 000 m (bible 1.4: 45 000; near 0.05): the tide is 5.7-13.3 km away at U7b and '
                         'the background giants 3-8 km during act 3 (the current ReferenceCamera far 7 000 m clips them)',
        samples_every_0_5_s=samples)


def cameras_block():
    import gate_scene_shots as GS
    out = {}
    for k, sh in GS.SHOTS.items():
        if k == 'U8':
            continue
        yaw, pitch = sh['yaw'], sh['pitch']
        a, p = math.radians(yaw), math.radians(pitch)
        fwd = [math.sin(a) * math.cos(p), math.sin(p), math.cos(a) * math.cos(p)]
        out[k] = dict(t=round(sh['t'], 2), cue=sh['cue'], eye_bus_relative=r3(sh['eye']),
                      look_yaw_deg=yaw, look_pitch_deg=pitch, hfov_deg=sh['hfov'], aspect=round(sh['aspect'], 4),
                      unity_euler_deg=[round(-pitch, 3), round(yaw % 360, 3), 0.0], forward=r3(fwd, 4),
                      bus_shell=sh['bus'], gate_z=round(G.gate_z(sh['t']), 2), gate_y=round(G.gate_y(sh['t']), 2),
                      note=sh['note'])
    return out


MATERIAL_KIND = {
    # round 3 (tech B3 / M1 / M7 / M9): exactly the render's per-kind values. LanbaiFog cap / height falloff, rim px /
    # ladder gain, specular far scale and its range (_ReflFarRange), moon rims back-lit only (rear: 0).
    'pillar': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=3.5, _RimGain=0.25, _ReflectionScaleFar=0.08,
                   _ReflFarRange=[150, 450]),
    'mid': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=2.0, _RimGain=0.14, _ReflectionScaleFar=0.30),
    'hero': dict(_FogCap=0.92, _FogCapHeight=5000, _RimPx=1.2, _RimGain=0.06, _ReflectionScaleFar=0.15,
                 _ConvexCrease=0.0, _OcclusionStrength=0.0),
    'colossus': dict(_FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.08, _ReflectionScaleFar=0.20),
    'bg': dict(_FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.05, _ReflectionScaleFar=0.15),
    'surge': dict(_FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.04, _ReflectionScaleFar=0.15),
    'near': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=5.0, _RimGain=1.0, _ReflectionScaleFar=0.60),
    'rear': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=2.5, _RimGain=0.1, _ReflectionScaleFar=1.0, _RimBackOnly=0,
                 _CloudTopColor=[0.10, 0.11, 0.13, 1.0]),      # the front-lit plain behind the bus
}
MATERIAL_COMMON = dict(_CloudTopColor=[0.050, 0.056, 0.068, 1.0], _CloudFade=46.0, _RootDissolve=18.0, _FogExtra=[1.5, 25.0], _FogCapFrom=[1300, 1700], _UseUVRadius=1, _Girth=1.0,
                       _ReflFarRange=[250, 800], _RimBackOnly=1, _MoonGlowFog=0.35, _HaloFog=0.35,
                       _BandEl=list(G.BAND_EL))


def arm_kind(it):
    r = it.get('role')
    if r == 'pillar':
        return 'pillar'
    if r == 'engel':
        return 'hero'
    if it['layer'] == 'near' and it.get('clearance_m', 0) > 25.0:
        return 'mid'            # tech minor: Near_2 never comes within 25 m -> the mid material
    return {'colossus_bg': 'bg'}.get(it['layer'], it['layer'])


def inst_block(it):
    R_u = u_rot(it['R'])
    p_u = u_pos(it['root'])
    root7, R7 = G.pose_at(it, G.T_HERO)
    kind = arm_kind(it)
    d = dict(id=it['id'], layer=it['layer'], role=it.get('role', ''), variant=it['variant'],
             texture_variant=G.TEX_KEY.get(it['variant'], it['variant']),
             mesh='GateArms_v3.fbx: %s (LODGroup: %s_LOD0 / _LOD1 / _LOD2)' % (it['id'], it['id']),
             position=r3(p_u, 2), rotation_xyzw=q_xyzw(R_u), rotation_euler_deg=euler(R_u),
             position_U7b=r3(u_pos(root7), 2), rotation_U7b_xyzw=q_xyzw(u_rot(R7)),
             scale=round(it['scale'], 4), phase=round(it['phase'], 4),
             form=dict(girth=round(it.get('girth', 1.0), 3), **{k: round(v, 4) for k, v in it.get('form', {}).items()}),
             length_m=round(G.BL.VARIANTS[it['variant']]['L'] * it['scale'], 1),
             max_diameter_to_length='1:%.1f' % (1.0 / G.diameter_ratio(it)),
             top_above_cloud_m=round(float(G.height_of(it['variant'], it['R'], it['scale']) + it['root'][2]), 1),
             note=it.get('note', ''), material_kind=kind,
             material=dict(MATERIAL_COMMON, **dict(MATERIAL_KIND[kind],
                           _FogDensityScale=round(float(G.fog_scale_at(it, C['U9'])), 3), _Phase=round(it['phase'], 4),
                           _SwayAmplitude=G.sway_of(it)[0], _SwayFrequency=G.sway_of(it)[1],
                           _SwaySecondary=G.sway_of(it)[2], _SwayStiffness=2.0)))
    if it.get('reveal'):
        d['reveal'] = dict(keys=[dict(t=round(float(k_), 2), value=float(v)) for k_, v in it['reveal']],
                           how='_Reveal (instanced, MaterialPropertyBlock) = smoothstep between keys; renderer.enabled = '
                               '(_Reveal > 0). Applied after the fog cap: f = 1 - (1 - f) x _Reveal.')
    if 'moon_cover_hero' in it:
        d['moon_cover_U7b'] = it['moon_cover_hero']
    for k in ('clearance_m', 'clearance_t', 'speed_ratio', 'rise_vmax'):
        if k in it:
            d[k] = it[k]
    anims = []
    for a in it['anim']:
        if a['type'] == 'rise':
            start = it['root'].copy()
            start[2] -= a['depth']
            anims.append(dict(type='rise', t0=round(a['t0'], 2), t1=round(a['t1'], 2), depth_m=round(a['depth'], 1),
                              position_start=r3(u_pos(start), 2), profile=a.get('prof', 'ss'),
                              ease=PROFILES[a.get('prof', 'ss')], **prof_param(a)))
        elif a['type'] == 'lean':
            R0 = G.rodrigues(a['axis'], -math.radians(a['deg'])) @ it['R']
            anims.append(dict(type='lean', t0=round(a['t0'], 2), t1=round(a['t1'], 2), deg=round(a['deg'], 2),
                              rotation_start_xyzw=q_xyzw(u_rot(R0)),
                              how='localRotation = Slerp(rotation_start, rotation, w) (about the root)',
                              ease=PROFILES['ss']))
        elif a['type'] == 'track':
            keys = []
            for (tk, rv) in a['keys']:
                rv = np.asarray(rv, float)
                ang = float(np.linalg.norm(rv))
                Rk = (G.rodrigues(rv / ang, ang) if ang > 1e-9 else np.eye(3))
                keys.append(dict(t=round(tk, 2), rotation_xyzw=q_xyzw(u_rot(Rk @ it['R']))))
            anims.append(dict(type='track', keys=keys, how='after rise / lean: localRotation = Slerp between the keys '
                              '(smoothstep between consecutive keys); keeps colossus 2 on the moon ray against the '
                              'parallax within 0.35 deg/s'))
        elif a['type'] == 'fog':
            anims.append(dict(type='fog', keys=[dict(t=round(k_, 2), _FogDensityScale=round(v, 3)) for k_, v in a['keys']],
                              how="the haze reveal: the layer material's _FogDensityScale, smoothstep between keys"))
        elif a['type'] == 'drift':
            anims.append(dict(type='drift', v_rel_m_per_s=a['v'], t_ref=round(a['t_ref'], 2)))
        elif a['type'] == 'close':
            R1 = G.rodrigues(a['axis'], math.radians(a['deg'])) @ it['R']
            anims.append(dict(type='close', t0=round(a['t0'], 2), t1=round(a['t1'], 2), deg=round(a['deg'], 2),
                              axis_unity=r3(M_W @ np.asarray(a['axis']), 4), rotation_end_xyzw=q_xyzw(u_rot(R1)),
                              how='after the bus has passed: localRotation = Slerp(rotation, rotation_end, w)',
                              profile=a.get('prof', 'ss'), ease=PROFILES[a.get('prof', 'ss')], **prof_param(a)))
    d['anim'] = anims
    if it['frame'] == 'bus':
        p = np.asarray(it['root'])
        d['frame'] = 'bus'
        d['position'] = r3([p[0], p[2], p[1]], 2)
        d['how'] = ('NOT under GateRoot: world position = (x, -h_bus(t) + y, z + v_rel * (t - t_ref)) (moves with the '
                    'bus along z, rooted in the cloud vertically); rotation as given (world). Rise: y from '
                    'position_start.y to position.y. Nearest skin to the 8 x 2.5 x 3.2 m shell box %.1f m at t = %.2f; '
                    'worst |v_rel| / (1.05 d) = %.2f (bible <= 1).' % (it.get('clearance_m', -1), it.get('clearance_t', -1),
                                                                     it.get('speed_ratio', -1)))
        for a in d['anim']:
            if a['type'] == 'rise':
                s = np.asarray(it['root']).copy()
                s[2] -= [x for x in it['anim'] if x['type'] == 'rise'][0]['depth']
                a['position_start'] = r3([s[0], s[2], s[1]], 2)
    else:
        d['frame'] = 'GateRoot'
    return d


def tide_block(tide):
    out = []
    for td in tide:
        c = td['cell']
        start = td['root'].copy()
        ra = td['anim'][0]
        start[2] -= ra['depth']
        out.append(dict(id=td['id'], position=r3(u_pos(td['root']), 1), size_m=round(td['size'], 1),
                        atlas=c['atlas'], cell=c.get('index', c.get('cell')), variant=c.get('variant'),
                        phase=round(td['phase'], 4), distance_to_tear_m=round(td['dist_tear'], 1),
                        lean_deg=round(td['lean'], 1), kind=c.get('kind'), mist_height_m=round(td.get('mist_h', 0.0), 1),
                        sink_m=round(td.get('sink', 0.0), 1),
                        rise=dict(t0=round(ra['t0'], 2), t1=round(ra['t1'], 2), depth_m=round(ra['depth'], 1),
                                  position_start=r3(u_pos(start), 1))))
    return out


def moon_block(lay):
    c2 = [it for it in lay if it['id'] == 'Colossus_2'][0]
    ts = [C['U7b'] + d for d in (-3.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 3.5, 5.0, 8.0, 11.0)]
    return dict(
        beat="'...und wollt' mich abweisen': colossus 2's upper body (u 0.2-0.4, ~1.6 deg wide at 2.6 km) comes "
             "down across the 1.2 deg disc",
        coverage=[dict(t=round(t, 2), covered=round(G.moon_coverage(c2, t), 2)) for t in ts],
        udon_rule='the disc is >= 90 % covered over [U7b, U7b + 1.5] (run 6 table: 0.96 at U7b, 1.00 at U7b + 0.5, '
                  '0.93 at U7b + 1.5, 0.89 at U7b + 2.0): START the fade of the skybox moon DISC at U7b + 1.5 and '
                  'take it out over 2 s (EV-linear), leaving the halo '
                  '#5A6A88 (Lanbai/Sky halo term) on: the moon is TAKEN. The track keys keep the body near the halo '
                  'for a few more seconds; then parallax carries it left of the empty halo.',
        aureole='Lanbai/Sky moon halo: fill = #8FA3C8 x (1.6 exp(-0.9 a) + 0.06 exp(-0.32 a)), a = angle from the '
                'disc centre in degrees (L* ~55 at 1 deg, the band by ~8 deg); LanbaiFog adds 0.35 x the same term')


def spot_block():
    import gate_bus as GB
    rows = []
    for t in np.arange(C['U8'], C['U9'] - 1.0, 0.5):
        q = GB.skylight_spot_quad(float(t))
        rows.append(dict(t=round(float(t), 2), corners_bus=[r3(p, 3) for p in q]))
    return dict(note='bible 4.8: the skylight corners projected along (corner - tear core) onto the floor (y = 0.623);'
                     ' additive UnlitCardHDR #E2E8F3, display luma 170-200. Round 3 (awe B9.3): the card is drawn 0.22 m '
                     'larger on every side (penumbra) and shaded as the aperture convolved with the INVERTED wound: a soft '
                     'lens longer along the aisle (box feather from 55 % of the half size, lens 0.35 -> 1.0 inside '
                     '(du/0.80)^2 + (dv/1.05)^2 < 1, v = along the aisle), x (0.86 + 0.14 floor studs 25 mm / 50 mm); '
                     'beam = the prism skylight -> spot (additive, ~4 % at the floor), 300 dust motes inside it',
                samples=rows)


def main(write_tex=True):
    import gate_scene_shots as GS  # noqa: F401
    lay = G.build_layout()
    cells = json.load(open(os.path.join(G.LAN, 'deliver', 'Tentacles', 'Textures', 'TentacleTide_Atlas.json')))['cells']
    tide = G.build_tide(cells)
    beams, wedges = G.build_shafts()
    S_hero = G.tear_H(G.T_HERO) / G.TD.H
    if write_tex:
        os.makedirs(OUT_TEX, exist_ok=True)
        from PIL import Image
        M = G.lane_mask(lay)
        Image.fromarray((np.clip(M, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
            os.path.join(OUT_TEX, 'Tear_CloudLanes_1024.png'))
    lo, hi, pw = G.BAND_EL
    doc = dict(
        about='Lanbai / 蓝白 · Tentacle gate layout v4 (round 3 of the gate key art). Cloud art team -> Unity. Replaces '
              'the four tentacle groups of LB_Builder_Gate.cs (README_GateLayout.md). Shaders / C# uncompiled.',
        convention=__doc__.split('CONVENTIONS (also written into the JSON):')[1].strip(),
        units='metres, seconds (timeline t, 0 = departure), degrees',
        timeline=timeline_block(),
        cameras=cameras_block(),
        lights=dict(
            moon=dict(type='Directional', color='#D6E4FF', E=1.0, inspector=1.0, shadows='soft',
                      direction_to_light_unity=r3(M_W @ G.L_MOON, 4), azimuth_deg=G.MOON_AZ, elevation_deg=G.MOON_EL),
            tear=dict(type='Directional', color='#A99DE1', E=0.8, inspector=0.9, shadows='none',
                      direction='from _Udon_TearPos toward the bus each frame'),
            fill=dict(type='Directional', color='#5A6488', E=0.24, inspector=0.52, from_below=True)),
        sky_band=dict(
            near='#484D63 (fill #67697D) next to the tear', far='#2A3041 (fill #424755) at 50 deg', void='#070A14',
            azimuth='smoothstep(0, 50, |az|) near->far; x (1 - smoothstep(50, 60, |az|))',
            elevation='w_el = (1 - smoothstep(%g, %g, el))^%g  (_BandEl = (%g, %g, %g); round 3, awe B7.2: full to '
                      '~+13, 0.17 at +20, ~0 by +26, void from +34: the top of the frame is night)' % (lo, hi, pw, lo, hi, pw),
            below_horizon='x lerp(0.55, 1, smoothstep(-25, 0, el)); and toward a cold grey: lerp(band, '
                          'luminance x (0.92, 0.98, 1.12), 0.6 x smoothstep(0, -4, el)) (_BelowDesat 0.6: the air over '
                          'the cloud sea is moonlit silver, not lavender)'),
        fog=dict(mode='Exponential', density=0.0006, global_color='#505466',
                 height_extra='density x (_FogDensityScale + _FogExtra.x exp(-(y - y_cloud) / _FogExtra.y)), _FogExtra = '
                              '(1.5, 25) on every material (shader v2.4 adds it; v2.3 multiplied it: tech B3)',
                 per_instance='instances[*].material._FogDensityScale; the reveal is instances[*].reveal (after the cap)',
                 cap='hero / colossus / bg / surge: beyond 1.3-1.7 km min(f, 0.92) x exp(-(y - y_cloud) / 5000 m); then '
                     'the reveal: f = 1 - (1 - f) x _Reveal',
                 color='LanbaiHorizon(view dir) + 0.35 x the moon aureole (#8FA3C8 x (1.6 e^-0.9a + 0.06 e^-0.32a)) + '
                       '0.35 x the three halo cards\' profile at the ray\'s crossing of the tear plane (points in front '
                       'of it only): shader v2.4 LanbaiFogColour, globals _Udon_MoonDir / _Udon_TearPos / _Udon_TearH',
                 cloud_top='arms: the last 25 m (+-15 m noise) above _Udon_CloudTop.x fade toward _CloudTopColor = '
                           'fill (0.026, 0.030, 0.038) under the same fog; clip below cloudTop - 5 m'),
        rim_ladder='rim x exp(-0.0006 d) x clamp((900/d)^1.2, 0.12, 1) x (0.6 + 0.8 wet) x _RimGain; only on '
                   'light-facing edges of a BACK-LIT arm (moon: saturate(N.L) and the moon in front of the view; '
                   'wound: facing it and it in front); width _RimPx',
        instances=[inst_block(it) for it in lay],
        tide=dict(count=len(tide), mesh='TentacleTide_v2.fbx', shader='Lanbai/TentacleTide v2 (gate/Shaders)',
                  atlas='run 6: gate/Textures/TentacleTide_v3_Atlas_A/B.png + TentacleTide_v3_Atlas.json (v4 arm form: '
                        'swan necks curling over in the top third; 8 single arms + 8 clusters of 3-5 arms; alpha feathered '
                        'over the bottom 7 %). The v2 atlases (deliver/Tentacles/Textures) are superseded for the gate: '
                        'their thin blades in a row read as grass.',
                  placement='run 6: 360 quads 4.8-12 km from the tear, |az| 24-70 (clear of the wound foot and the hands), '
                            'grouped in surges along the azimuth (haze gaps between masses) and crest rows 600 m apart; '
                            'taller toward the wound; roots sunk 40-160 m (sink_m); each base dissolves over its own '
                            'mist_height_m (60-180 m): alpha x saturate((y_above_cloud_top + 8) / mist)^1.6 (UV6 '
                            '"TideMist" x = mist height, y = sink)',
                  phase='(distance to tear / 600 m) - (t / 6 s)', lean='each blade leans lean_deg toward the wound',
                  fog='round 3: 58 % at the base, 48 % at the tips (min(fog, lerp(0.58, 0.48, smoothstep(0, 400, height)))): '
                      'a contrast of -4..-6 L* against the band (the 80-92 % of the bible left the tide invisible); the '
                      'atlas colour x 0.3 (the painted rim never brighter than the sky); clip below _Udon_CloudTop.x - 2',
                  reveal=dict(keys=[dict(t=round(k_, 2), value=v) for k_, v in G.TIDE_REVEAL],
                              how='material _Reveal (all blades): the wave recedes into the haze U8 - 5 .. U8 + 1; '
                                  'disable the renderer at 0'),
                  rise='each blade rises only its visible part (size x cos(lean) + 40 m) over 14 s, the outermost first '
                       '(U6 + 10 .. U7): the tide is on screen at U7b; crest speed in motion_check.json',
                  items=tide_block(tide)),
        shafts=dict(parent='Tear_Root', mesh='Tear_ShaftCard.fbx (deliver/Tear)',
                    note='round 3: TWO beams (one per gap, unequal 1.0 / 0.6), each one soft lobe across (no striation '
                         'finer than 1.5 deg: Shaft_Gradient v4), from the lens at 38-44 % of its height up and out into '
                         'the void, ending by el +21; widen x3.2 by 1.5 km; depth-tested',
                    items=[dict(id=s['id'], start_os=r3(B2U @ np.asarray(s['start']), 2),
                                axis_os=r3(B2U @ np.asarray(s['axis']), 4), half_width_m=round(s['half_width'], 1),
                                length_m=round(s['length'], 1), gain=s['gain'], widen=s['widen'],
                                seen_at_azel_U7b=s['end_azel']) for s in beams]),
        shadow_wedges=dict(parent='GateRoot', blend='multiplicative (Blend Zero OneMinusSrcAlpha), queue 2990',
                           note='dark wedges in the haze band behind each bundle (alpha 0.15-0.25): the band alternates '
                                'lit and shadowed like crepuscular rays in fog; camera-facing about the axis',
                           items=[dict(id=w['id'], start=r3(u_pos(w['start']), 1), axis=r3(M_W @ w['axis'], 4),
                                       half_width_m=w['half_width'], length_m=w['length'], alpha=round(w['alpha'], 3),
                                       widen=w['widen']) for w in wedges]),
        tear=dict(
            Tear_Root=dict(parent='GateRoot', localPosition=r3(u_pos([0, 0, 0]), 2), localEulerAngles=[0, 180, 0],
                           localScale='H(t)/1000 (uniform; timeline.tear_H)'),
            kit='deliver/Tear kit v4 (round 3: no nested lips; the bible falloff + a cloth thickness on the right edge + '
                '4 inner veils; left edge clean, right ragged; TWO thin welded flaps (outer face = the sky colour) whose '
                'rolled lips the hands grip (tented); a zipper of 9 bridging threads across the top 16 % (2 snapped) '
                'and a hairline running on into the dark; tension folds (Tear_SkyFolds v4); dark-lipped branch rips; an '
                'inner halo card x 2.8; README_Tear.md)',
            gate_overrides=dict(halo_intensity=1.0, skyfolds=0.55),
            grips='the fingertips of Hand_L0/L2 and Hand_R0/R2 end on tear_def.GRIPS (kit space, moved with the '
                  'opening like the flaps): they hold the cloth through the approach (track keys to U9 - 1). Run 6: '
                  'Hand_L1 and Hand_R1 are WHIPS that cross the white in front of the lens (y -30 m in the tear frame) '
                  'and hook the OPPOSITE lip (L1 -> right lip at 24 % H, R1 -> left lip at 36 % H; gate_layout.CROSS), '
                  'tracked to that lip point (u 0.93) until U9 - 1: the fingertips interlace over the wound as if '
                  'closing it, and it keeps opening',
            crevasse=dict(length_m=G.CREVASSE['length'], width_at_foot='%d %% of the lens width -> 0' % round(100 * G.CREVASSE['w0_frac']),
                          floor='#C0B9E4 (Glow fill x 0.35, fading with distance)', walls='x 0.30 darker (run 6: the foot\'s own '
                          'split, 240 m; the 700 m crevasse read as a crack / river drawn to the camera)',
                          unity='Tear_Foot: 3 alpha cards on the cloud top along -Z from the foot (or a decal-like '
                                'additive strip at cloud-top height) + Tear_CloudGlow')),
        clouds=dict(
            note='Renders use one volumetric impostor of the cloud deck to 9 km (cloud_deck.py gate3 / rear3); in '
                 'Unity the cloud sea is the Clouds kit (CloudSea strips + cards) moving at v_g.',
            cloud_top_world_y='-h_bus(t)',
            pool='the pool LIGHTS the cloud (v3b): Tear_CloudGlow_Lit (Blend DstColor One: dst x (1 + glow), _Tint linear '
                 '(0.607, 0.683, 1.144) = the #495270 hue at luminance 0.7) + Tear_CloudGlow additive at _Intensity 0.25, '
                 'at cloud-top height, #495270 target: weight = 0.75 exp(-(r/420)^2) + '
                 '0.25 exp(-r/900) (r = distance from (0, 150 x S) in the tear frame) x Tear_CloudLanes_1024.png '
                 '(x0..x1 = %g..%g m across, y0..y1 = %g..%g m along, GateRoot frame shifted by -z of the foot)'
                 % G.LANES_RECT,
            lanes_png='Textures/Tear_CloudLanes_1024.png (R: 1 = lit, 0.15 = in a root shadow; row 0 = far)',
            root_dissolve='run 6: the arms\' roots dissolve in the lowest ~18 m of their _CloudFade zone (noisy alpha: '
                          'Unity = dithered clip / alpha-to-coverage on the same noise, over the cloud cards); the root '
                          'sleeve cards below are RETIRED (at the hand roots their streaks read as a striped band with a '
                          'straight top)',
            sleeves_retired='round 3 (awe B6.1): no crisp collars. Per arm beyond 400 m a SLEEVE (Textures/Gate_RootSleeve_512.png, '
                    'a soft dome 1.2-1.8 x the root diameter, 30-60 m high, with mist 60-150 m up the body, ragged top, '
                    'edges >= 6 px soft), tinted from the deck: gate_scene.sleeve_specs / root_sleeves',
            collars_retired='root collars: 2-3 Cloud_Puff / Cloud_Cumulus cards per arm where it leaves the cloud (1.5-2.2 x '
                    'its diameter wide, >= 50 m, yaw billboards, queue 3000, colour = card luminance x (0.92, 0.98, '
                    '1.12) x 1.3 in LanbaiFog, the card\'s cloud base on the cloud-sea top); not on the 3 near arms '
                    '(at 10-50 m a puff card reads as rocks); alpha x smoothstep(8, 5, depression angle from the eye in deg): seen '
                    'from above (U8, eye 80-150 m up) a vertical puff card reads as a heap of rocks: gate_scene.collar_specs',
            mist=[dict(card=m['card'], role=m['role'], position=r3(u_pos(m['loc']), 1), width_m=m['width'],
                       opacity=m['opacity'], mirror=m['mirror'], kind='mist') for m in G.mist_positions(G.MIST)],
            far=[dict(card=m['card'], role=m['role'], position=r3(u_pos(m['loc']), 1), width_m=m['width'],
                      opacity=m['opacity'], mirror=m['mirror'], kind='far', gain=0.6)
                 for m in G.mist_positions(G.FAR_CLOUDS)],
            horizon_relief=dict(
                note='run 6: 22 low moonlit cloud masses 4.2-9.5 km out (|az| 14-70, 90-230 m showing above the deck), '
                     'interleaved with the tide rows so the far arms rise from behind cloud heads at different heights '
                     '(a flat far deck made a ruler-straight horizon on which every base sat). Same material as "far" '
                     '(yaw billboard, card colour in LanbaiFog, no cap, base melting over its lowest 130 m), queue 2990.',
                items=[dict(card=m['card'], position=r3(u_pos(m['loc']), 1), width_m=round(m['width'], 1),
                            opacity=m['opacity'], mirror=m['mirror'], kind='far', gain=0.6)
                       for m in G.mist_positions(G.horizon_relief())])),
        towers=dict(
            note='round 3 (awe B8): every colossus is born inside a towering cumulus card standing on the deck at its '
                 'root, a little in front of it (deliver/Clouds; yaw billboard, queue 3000, colour = the card in '
                 'LanbaiFog with no cap, opacity 0.92). After the instance\'s reveal starts, the tower SAGS (localScale.y '
                 '1 -> 0.72, pivot at its base) and thins (alpha 1 -> 0.8) over 25 s: the arm has dragged cloud down '
                 'with it. Pour-off sheets (2-3 Cloud_Wisp cards sliding down the body over 10-15 s) are optional.',
            items=[dict(id=w['id'], hides=w['hides'], card=w['card'], position=r3(u_pos(w['loc']), 1),
                        width_m=round(w['width'], 1), height_m=round(w['height'], 1), opacity=w['opacity'],
                        mirror=w['mirror'], sag_keys=w['sag'], alpha_keys=w['alpha'])
                   for w in G.tower_specs(lay)]),
        near_wake=dict(
            note='round 3 (tech M10): the near arms move with the bus, so their roots travel through the cloud at '
                 '52-66 m/s. Per near arm: a BOW PUFF (Cloud_Puff_moon, 1.5 x the root diameter wide) riding with the '
                 'root at the cloud top, plus a trail: every 0.6 s emit a Cloud_Wisp_moon / Cloud_Puff_moon card at the '
                 'root (width 1.2-2 x the root diameter), left behind at WORLD speed (it moves with GateRoot), fading '
                 'alpha 0.8 -> 0 over 4 s (6-7 alive per arm), queue 3000, unlit, LanbaiFog colour.',
            arms=[it['id'] for it in lay if it['layer'] == 'near']),
        moon=moon_block(lay),
        glory=dict(
            note='round 3 (awe rear): the rear window\'s scale anchor. An ADDITIVE card lying on the cloud top at the '
                 'anti-moon point, a child of NearRoot (it travels with the bus): position = (-Lm.x d, -h_bus(t), -Lm.z d) '
                 'with Lm = the horizontal direction to the moon (Unity), d = h_bus(t) / tan(8 deg) (~1.07 km at U9). '
                 'Seen from the bus: a colourless ring of radius 3.2 deg (+0.75 x the cloud luminance, width 0.75 deg) + '
                 'a 1.7 deg core (+0.40) and, at the centre, a 0.3 deg dark spot (x 0.45): the bus\'s own shadow. '
                 'C* <= 6, queue 3001, unlit; size the card so 3.2 deg at distance d spans its ring.',
            moon_dir_unity=r3(M_W @ G.L_MOON, 4), ring_deg=3.2, ring_width_deg=0.75, ring_gain=0.75, core_deg=1.7,
            core_gain=0.40, shadow_deg=0.30, shadow_mul=0.45),
        skylight_spot=spot_block(),
        near_root='near arms (frame bus) are fixed to the bus, not to GateRoot; see instances[*].how',
        hero_time=G.T_HERO, hero_tear_scale=round(S_hero, 4),
    )
    json.dump(doc, open(OUT_JSON, 'w'), indent=1, ensure_ascii=False)
    print('wrote', OUT_JSON, '%d instances, %d tide' % (len(lay), len(tide)))
    return doc, lay, tide


def _empty(col, name, parent=None, p_u=(0, 0, 0), R_u=np.eye(3), s=1.0, kind='ARROWS'):
    import bpy
    from mathutils import Matrix
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = kind
    col.objects.link(ob)
    M = np.eye(4)
    M[:3, :3] = (B2U.T @ np.asarray(R_u) @ B2U) * s
    M[:3, 3] = B2U.T @ np.asarray(p_u, float)
    if parent is not None:
        ob.parent = parent
    ob.matrix_world = Matrix(M.tolist())
    return ob


def export_layout_fbx(lay, tide):
    """GateRoot -> one empty per instance (final pose, uniform scale; named by id), Tear_Root, TideRoot (440),
    NearRoot (bus-relative). Blender scene = Unity space pulled back through B2U, so each empty imports exactly as
    the JSON says."""
    import bpy
    sys.path.insert(0, os.path.join(G.LAN, 'lib'))
    import export_unity
    bpy.ops.wm.read_factory_settings(use_empty=True)
    col = bpy.context.scene.collection
    objs = []
    root = _empty(col, 'GateRoot')
    objs.append(root)
    objs.append(_empty(col, 'Tear_Root', root, u_pos([0, 0, 0]), np.diag([-1.0, 1.0, -1.0]), G.tear_H(G.T_HERO) / 1000.0))
    near = _empty(col, 'NearRoot_busRelative')
    objs.append(near)
    for it in lay:
        R_u = u_rot(it['R'])
        if it['frame'] == 'bus':
            p = np.asarray(it['root'])
            objs.append(_empty(col, it['id'], near, [p[0], p[2], p[1]], R_u, it['scale']))
        else:
            objs.append(_empty(col, it['id'], root, u_pos(it['root']), R_u, it['scale']))
    tr2 = _empty(col, 'TideRoot', root)
    objs.append(tr2)
    for td in tide:
        objs.append(_empty(col, td['id'], tr2, u_pos(td['root']), np.eye(3), td['size'] / 100.0, 'SINGLE_ARROW'))
    export_unity.export_fbx(OUT_FBX, objs)
    print('wrote', OUT_FBX, len(objs), 'empties')


def export_arms_fbx(lay):
    """GateArms_v3.fbx (round 3, tech M6 / M7): per instance an EMPTY <id> (identity; the JSON transform goes on the
    instantiated prefab) with three children <id>_LOD0 / _LOD1 / _LOD2, so Unity's importer builds one LODGroup per
    arm. UV layers in order UVMap (TEXCOORD0), UVSway (TEXCOORD1), UVRadius (TEXCOORD2: x = the baked local radius /
    root radius, the 'GR' attribute). Custom (v4) arms are dense already (LOD0 40 x 210 ~16.8 k tris, LOD1 ~5.8 k,
    LOD2 ~1.2 k: no x12 pop); library-variant arms keep the subsurf LOD0 only for the near arms."""
    import bpy
    sys.path.insert(0, os.path.join(G.LAN, 'lib'))
    import export_unity
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import gate_scene as GSc
    GSc._MESH.clear()
    objs = []
    tris = 0
    for it in lay:
        kind = arm_kind(it)
        par = bpy.data.objects.new(it['id'], None)
        bpy.context.scene.collection.objects.link(par)
        objs.append(par)
        for lod in (0, 1, 2):
            me = GSc.variant_mesh(it['variant'], lod, it.get('girth', 1.0), it.get('form'))
            me2 = me.copy()
            me2.name = '%s_LOD%d' % (it['id'], lod)
            # UVRadius = the GR attribute (per vertex) as the third UV layer
            gr = np.zeros(len(me2.vertices), np.float32)
            me2.attributes['GR'].data.foreach_get('value', gr)
            lv = np.zeros(len(me2.loops), np.int32)
            me2.loops.foreach_get('vertex_index', lv)
            uvr = me2.uv_layers.new(name='UVRadius')
            uvr.data.foreach_set('uv', np.stack([gr[lv], np.zeros(len(lv), np.float32)], 1).ravel())
            ob = bpy.data.objects.new('%s_LOD%d' % (it['id'], lod), me2)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = par
            if lod == 0 and kind == 'near' and not G.A4.is_custom(it['variant']):
                m = ob.modifiers.new('Smooth', 'SUBSURF')
                m.levels = m.render_levels = 1
            ob.data.materials.append(bpy.data.materials.new('M_Tentacle_%s' % G.TEX_KEY.get(it['variant'], it['variant'])))
            objs.append(ob)
            me2.calc_loop_triangles()
            tris += len(me2.loop_triangles) * (4 if ob.modifiers else 1)
    export_unity.export_fbx(OUT_ARMS, objs)
    old = os.path.join(HERE, 'GateArms_v2.fbx')
    if os.path.exists(old):
        os.remove(old)             # superseded (flat, no LOD parents, no UVRadius)
    print('wrote', OUT_ARMS, len(objs), 'objects, ~%d triangles' % tris)


def export_tide_fbx(tide):
    """TentacleTide_v2.fbx: 440 quads (3 sub-meshes = atlases) in GateRoot space, the library's UV contract
    (UV0 atlas, UV1 'TideSway' (height fraction, phase), UV2 'TideRootXZ', UV3 'TideRootYOffset') + UV4
    'TideRise' (x = rise t0, y = lean deg toward the wound) + UV5 'TideRiseDepth' (x = depth m, y = duration s)."""
    import bpy
    sys.path.insert(0, os.path.join(G.LAN, 'lib'))
    import export_unity
    bpy.ops.wm.read_factory_settings(use_empty=True)
    atl = sorted({td['cell']['atlas'] for td in tide})
    verts, faces, uv = [], [], {k: [] for k in ('UVMap', 'TideSway', 'TideRootXZ', 'TideRootYOffset', 'TideRise', 'TideRiseDepth',
                                                'TideMist')}
    mats = []
    eye_u = u_pos(G.E_HERO)
    for td in tide:
        c = td['cell']
        base = u_pos(td['root'])
        Hq = c['cell_height_in_lengths'] * td['size']
        Wq = Hq * 0.5
        d = base[[0, 2]] - eye_u[[0, 2]]
        d /= np.linalg.norm(d)
        r = np.array([d[1], 0.0, -d[0]])
        mirror = td['root'][0] > 0
        u0, v0, u1, v1 = c['uv_rect']
        ru = c['root_u']
        offs = (-(1 - ru) * Wq, ru * Wq) if mirror else (-ru * Wq, (1 - ru) * Wq)
        us = (u1, u0) if mirror else (u0, u1)
        k0 = len(verts)
        ra = td['anim'][0]
        for (o, uu), (hy, vv) in (((offs[0], us[0]), (0.0, v0)), ((offs[1], us[1]), (0.0, v0)),
                                  ((offs[1], us[1]), (Hq, v1)), ((offs[0], us[0]), (Hq, v1))):
            p = base + r * o + np.array([0.0, hy, 0.0])
            verts.append(B2U.T @ p)
            uv['UVMap'].append((uu, vv))
            uv['TideSway'].append((hy / Hq, td['phase']))
            uv['TideRootXZ'].append((base[0], base[2]))
            uv['TideRootYOffset'].append((base[1], o))
            uv['TideRise'].append((ra['t0'], td['lean']))
            uv['TideRiseDepth'].append((ra['depth'], ra['t1'] - ra['t0']))
            uv['TideMist'].append((td.get('mist_h', 12.0), td.get('sink', 0.0)))      # run 6: UV6
        faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
        mats.append(atl.index(c['atlas']))
    me = bpy.data.meshes.new('TentacleTide_v2')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    lv = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    for nm, data in uv.items():
        lay_ = me.uv_layers.new(name=nm)
        lay_.data.foreach_set('uv', np.array(data, np.float32)[lv].ravel())
    me.uv_layers.active = me.uv_layers['UVMap']
    for a_ in atl:
        me.materials.append(bpy.data.materials.new('M_TentacleTide_%s' % a_[-1]))
    me.polygons.foreach_set('material_index', mats)
    me.validate()
    ob = bpy.data.objects.new('TentacleTide_v2', me)
    bpy.context.scene.collection.objects.link(ob)
    export_unity.export_fbx(OUT_TIDE, [ob])
    print('wrote', OUT_TIDE, len(tide), 'quads')


if __name__ == '__main__':
    doc, lay, tide = main()
    if '--json' not in sys.argv:
        export_layout_fbx(lay, tide)
        export_tide_fbx(tide)
        export_arms_fbx(lay)
