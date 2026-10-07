"""蓝白 / Lanbai · 触手之门 layout v6 (gate round 8 = refine round 4) · export (Unity 2022.3, metres, Y up).

    python3 gate_export.py            -> GateLayout_v2.json, GateLayout_v2.fbx (empties), GateArms_v4.fbx (baked
                                         per-instance arm meshes: empty <id> with children <id>_LOD0/1/2, UV0 UVMap,
                                         UV1 UVSway, UV2 UVRadius), GateMultitude_v2.fbx (round 8: the 12 canonical
                                         multitude poses MU0..MU5 + their MIRRORS MU0m..MU5m, one LODGroup each),
                                         TentacleTide_v2.fbx (tide quads),
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
    kept). Instance transform = position / rotation / uniform scale from here. Material = Lanbai/TentacleSway v2.7
    (_UseUVRadius 1, _Girth 1). The MULTITUDE (layer 'surge', variants MU0..MU5 and the mirrored MU0m..MU5m) is NOT
    baked per instance: GateMultitude_v2.fbx holds the 12 pose meshes once; every instance = that mesh + its position /
    rotation / scale, material = the one of its fog TIER (3 materials), per-instance _Phase / _FogCapI / _RevealGroup
    written ONCE in Start() into every LOD renderer's own MaterialPropertyBlock; the reveal is the global
    _Udon_MultReveal (x = group 0, y = group 1) -- see README_GateLayout §2.1 (round 8, tech r4 BT-4).
  * Arm meshes: GateArms_v4.fbx (round 8; v3 superseded).
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
OUT_ARMS = os.path.join(HERE, 'GateArms_v4.fbx')
OUT_MULT = os.path.join(HERE, 'GateMultitude_v2.fbx')
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
            _Udon_MoonDir='(direction TO the moon, world, w = 1): the fog colour\'s moon-air term and the rims',
            _Udon_GateOrigin='round 4 (tech BT-1): (GateRoot.position, 1): every world noise in TentacleSway v2.6 and '
                             'Lanbai/Tear v5 (root dissolve, ragged cloud-top fade, the tear\'s foot) is sampled at '
                             'worldPos - _Udon_GateOrigin.xyz, the cloud-sea frame (GateRoot moves at 59 m/s)',
            _Udon_TearFoot='round 4: (tear axis foot, world, w = half width of the white m): TentacleSway v2.6 line '
                           'light = Tear_Root.TransformPoint(%s) (kit units x H/1000), w = 0.5 x (0.18 + 0.12 '
                           '_Udon_TearOpen) x H(t)' % r3(G.B2U @ (np.array([0.5 * float(G.TD.path(np.array([0.0]))[0]), 30.0, 0.0])), 2),
            _Udon_TearTop='round 4: (tear axis top, world): Tear_Root.TransformPoint(%s)' %
                          r3(G.B2U @ np.asarray(G.TD.P(G.TD.T_TOP * 0.92, float(G.TD.path(np.array([G.TD.T_TOP * 0.92]))[0]), 30.0)[()]), 2),
            _Udon_MultReveal='round 8 (tech r4 BT-4): (group 0 reveal, group 1 reveal, 0, 0) from multitude.reveal_groups '
                             '(smoothstep between keys): ONE global for the 36 multitude members',
            _Udon_FogBandDir='optional (LanbaiGateSky.cginc): horizontal direction of the band centre; unset = toward '
                             '_Udon_TearPos',
            _Udon_MoonDisc='(disc gain = moon.disc_gain_keys x the U7b + 1.5 fade, disc radius 0.6 deg, 0, 1): the skybox '
                           'disc (GateAirSky v3)',
            halo_fade='not a global: Tear_Halo _Intensity x smoothstep(250, 1200, |tear z - eye z|), renderer off at 0 '
                      '(the arms compute the same fade themselves from _Udon_TearPos)'),
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
    # round 8 (v2.7, tech r4 M1): _WoundSpecFar per kind (gate_scene.TSPEC_FAR) and the clamp _WoundSpecMax (near 0.6).
    'pillar': dict(_StreakKeep=0.5, _FogCap=1.0, _FogCapHeight=0, _RimPx=3.5, _RimGain=0.25, _ReflectionScaleFar=0.08,
                   _ReflFarRange=[150, 450], _WoundSpecFar=0.5),
    'mid': dict(_StreakKeep=0.5, _FogCap=1.0, _FogCapHeight=0, _RimPx=2.0, _RimGain=0.45, _ReflectionScaleFar=0.30, _WoundSpecFar=1.0),
    'hero': dict(_StreakKeep=0.0, _FogCap=0.92, _FogCapHeight=5000, _RimPx=1.2, _RimGain=0.15, _ReflectionScaleFar=0.01,
                 _ConvexCrease=0.0, _OcclusionStrength=0.0, _WoundSpecFar=0.15),
    'colossus': dict(_StreakKeep=0.15, _FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.08, _ReflectionScaleFar=0.20, _RimWound=3.0,
                     _WoundSpecFar=0.3),
    'bg': dict(_StreakKeep=0.0, _FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.05, _ReflectionScaleFar=0.15, _RimWound=1.5,
               _WoundSpecFar=0.15),
    'surge': dict(_StreakKeep=0.0, _FogCap=0.92, _FogCapHeight=5000, _RimPx=1.0, _RimGain=0.04, _ReflectionScaleFar=0.15, _RimWound=0.6,
                  _WoundSpecFar=0.15, _UseGlobalReveal=1),
    'near': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=5.0, _RimGain=1.0, _ReflectionScaleFar=0.60, _WoundSpecFar=1.0,
                 _WoundSpecMax=0.6),
    # round 8 (tech r4 M3): the rear arms are FRONT-lit (the moon is behind the viewer): albedo x 0.5 (_Color, an sRGB
    # Color: 0.735 = 0.5 linear), fog 0.35, moon-side pixel rims 1.5 on the moon-facing silhouettes, no wound rim
    'rear': dict(_FogCap=1.0, _FogCapHeight=0, _RimPx=2.5, _RimGain=0.5, _ReflectionScaleFar=1.0, _RimBackOnly=0,
                 _RimWound=0.0, _RimPxMoon=1.5, _Color=[0.735, 0.735, 0.735, 1.0], _WoundSpecFar=1.0,
                 _CloudTopColor=[0.10, 0.11, 0.13, 1.0]),      # the front-lit plain behind the bus
}
# round 8 (awe r4 B2.4): the multitude's three fog tiers and their rims (gate_scene.MULT_TIER_RIMS; _RimWound = 5 x rimw):
# ONE MATERIAL PER TIER (the 36 members are 36 draws anyway; _RimGain is not instanced)
# round 9: tier A / B _RimGain x LOOK mult_rim_k (6) = 2.4 with _RimLadderFloor (TentacleSway v2.7c) 0.5 / 0.3: the far
# ladder had taken the rims to x 0.01-0.02 at 3-5 km (gate_scene place_tentacles: mult_rim_floor_a / _b, mult_rim_k)
MULT_TIER_MAT = {0.45: dict(name='M_Multitude_TierA_near', _RimGain=2.40, _RimWound=1.75, _RimLadderFloor=0.5),
                 0.58: dict(name='M_Multitude_TierB_mid', _RimGain=2.40, _RimWound=0.75, _RimLadderFloor=0.3),
                 0.70: dict(name='M_Multitude_TierC_far', _RimGain=0.08, _RimWound=0.60, _RimLadderFloor=0.0)}
# round 8 (tech r4 M2 'a field, not a surge'): the multitude sways as a ROLLING surge toward the wound
MULT_SWAY = dict(_SwayAmplitude=0.05, _SwayFrequency=round(1.0 / 6.0, 4), _SwayWavelength=1.2, _SwaySecondary=0.6)


def tear_hw_knots():
    """v2.7 _TearHW0 / _TearHW1: the lens half width at 8 points along the axis A..B (u = k / 7), as a fraction of the
    global half width (_Udon_TearFoot.w): (aR - aL) / W_TOT at t = u x 0.92 T_TOP (independent of the opening and H)."""
    uu = np.arange(8) / 7.0
    aL, aR = G.TD.lips(uu * G.TD.T_TOP * 0.92)
    k = np.clip((np.asarray(aR) - np.asarray(aL)) / G.TD.W_TOT, 0.0, 2.0)
    return [round(float(x), 3) for x in k[:4]], [round(float(x), 3) for x in k[4:]]
MATERIAL_COMMON = dict(_CloudTopColor=[0.050, 0.056, 0.068, 1.0], _CloudFade=46.0, _RootDissolve=18.0, _FogExtra=[1.5, 25.0], _FogCapFrom=[1300, 1700], _UseUVRadius=1, _Girth=1.0,
                       _ReflFarRange=[250, 800], _RimBackOnly=1, _MoonGlowFog=0.35, _HaloFog=0.35,
                       _BandEl=list(G.BAND_EL), _HazeNear=r3(np.asarray([0.1356, 0.1413, 0.2051]) * G.BAND_GAIN, 4) + [1.0],
                       _HazeFar=r3(np.asarray([0.0545, 0.0630, 0.0908]) * G.BAND_GAIN, 4) + [1.0],
                       # round 4 (TentacleSway v2.6): the wound as the key light
                       _TearDiffuse=2.0, _TearDiffuseRef=600.0, _TearWrap=0.4, _TearSpec=1.0, _TearSpecRadiance=2.2,
                       _RimWound=5.0, _RimWoundPx=2.5, _RimWoundDeg=6.0, _RimWoundNear=[0.76, 0.80, 0.90, 1.0],
                       # round 8 (TentacleSway v2.7): thin parts, wound-spec clamp, over the white, back band, halo v6
                       _ThinK=[0.12, 0.40, 0, 0], _ThinSmooth=0.84, _ThinAlbedo=[0.017, 0.017, 0.022, 1.0],
                       _WoundSpecMax=0.35, _WoundSpecFar=0.3, _WoundSpecEl=[25.0, 18.0, 0, 0],
                       _OverWhiteRamp=1.5, _OverWhiteDim=0.12, _OverWhiteFog=0.6, _OverWhiteAir=0.85,
                       _WrapGain=1.2, _WrapPx=0.9, _WrapColor=[0.80, 0.80, 0.92, 1.0], _UseGlobalReveal=0,
                       _BackBand=0.55, _HaloColor=[0.195, 0.198, 0.332, 1.0], _TearFootM=[0, 0, 1800, 0], _StreakKeep=0.8)


def arm_kind(it):
    r = it.get('role')
    if r == 'pillar':
        return 'pillar'
    if r == 'engel':
        return 'hero'
    if it['layer'] == 'near' and it.get('clearance_m', 0) > 25.0:
        return 'mid'            # tech minor: Near_2 never comes within 25 m -> the mid material
    return {'colossus_bg': 'bg'}.get(it['layer'], it['layer'])


def mat_of(it, kind):
    m = dict(MATERIAL_COMMON)
    hw0, hw1 = tear_hw_knots()
    m.update(_TearHW0=hw0, _TearHW1=hw1)
    m.update(MATERIAL_KIND[kind])
    m.update(_FogDensityScale=round(float(G.fog_scale_at(it, C['U9'])), 3), _Phase=round(it['phase'], 4),
             _SwayAmplitude=G.sway_of(it)[0], _SwayFrequency=G.sway_of(it)[1], _SwaySecondary=G.sway_of(it)[2],
             _SwayStiffness=2.0, _SwayWavelength=0.9)
    if it.get('fog_tier'):        # the multitude: per-instance fog cap tier (instanced _FogCapI), tier material, surge sway
        tm = MULT_TIER_MAT[round(float(it['fog_tier']), 2)]
        m.update(_FogCapI=round(float(it['fog_tier']) * G.MULT_CAP_K, 3), _FogDensityScale=1.0, _RimGain=tm['_RimGain'], _RimWound=tm['_RimWound'],
                 _RimLadderFloor=tm['_RimLadderFloor'], _RevealGroup=1.0 if it.get('near_white_U8') else 0.0, **MULT_SWAY)
        m['material_name'] = tm['name']
    if it.get('role') == 'moon':  # round 8 (awe r4 M1.4): colossus 2 backlit by the moon right behind it: 2-4 px moon rim
        m.update(_RimGain=0.9, _RimPx=2.2)
    return m


def inst_block(it):
    R_u = u_rot(it['R'])
    p_u = u_pos(it['root'])
    root7, R7 = G.pose_at(it, G.T_HERO)
    kind = arm_kind(it)
    d = dict(id=it['id'], layer=it['layer'], role=it.get('role', ''), variant=it['variant'],
             texture_variant=G.TEX_KEY.get(it['variant'], it['variant']),
             mesh=(('GateMultitude_v2.fbx: %s (LODGroup: %s_LOD0 / _LOD1 / _LOD2; material by fog tier)' % (it['variant'], it['variant']))
                   if it['variant'].startswith('MU') else
                   ('GateArms_v4.fbx: %s (LODGroup: %s_LOD0 / _LOD1 / _LOD2)' % (it['id'], it['id']))),
             position=r3(p_u, 2), rotation_xyzw=q_xyzw(R_u), rotation_euler_deg=euler(R_u),
             position_U7b=r3(u_pos(root7), 2), rotation_U7b_xyzw=q_xyzw(u_rot(R7)),
             scale=round(it['scale'], 4), phase=round(it['phase'], 4),
             form=dict(girth=round(it.get('girth', 1.0), 3), **{k: round(v, 4) for k, v in it.get('form', {}).items()}),
             length_m=round(G.BL.VARIANTS[it['variant']]['L'] * it['scale'], 1),
             max_diameter_to_length='1:%.1f' % (1.0 / G.diameter_ratio(it)),
             top_above_cloud_m=round(float(G.height_of(it['variant'], it['R'], it['scale']) + it['root'][2]), 1),
             note=it.get('note', ''), material_kind=kind,
             material=mat_of(it, kind))
    if it.get('reveal'):
        if it.get('fog_tier'):
            g = 1 if it.get('near_white_U8') else 0
            d['reveal'] = dict(group=g, keys=[dict(t=round(float(k_), 2), value=float(v)) for k_, v in it['reveal']],
                               how='round 8 (tech r4 BT-4): NOT per instance: the global _Udon_MultReveal.%s (group %d; '
                                   'multitude.reveal_groups) x the material _Reveal 1; renderer.enabled toggled only at the '
                                   'two crossings of 0' % ('xy'[g], g))
        else:
            d['reveal'] = dict(keys=[dict(t=round(float(k_), 2), value=float(v)) for k_, v in it['reveal']],
                               how='_Reveal (instanced) = smoothstep between keys, written per frame only for these single '
                                   'arms (GetPropertyBlock -> SetFloat -> SetPropertyBlock on EVERY LOD renderer); '
                                   'renderer.enabled = (_Reveal > 0). Applied after the fog cap: f = 1 - (1 - f) x _Reveal.')
    if it.get('fog_tier'):
        d['cluster'] = it.get('cluster')
        d['dominant'] = bool(it.get('dominant'))
        d['fog_tier'] = float(it['fog_tier'])
        d['_FogCapI'] = round(float(it['fog_tier']) * G.MULT_CAP_K, 3)
        d['mirrored_pose'] = it['variant'].endswith('m')
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
            what = ('keeps colossus 2 on the moon ray against the parallax within 0.30 deg/s' if it.get('role') == 'moon' else
                    'keeps the fingertip (a whip on the far lip / a coil on its own hem) on its point of the cloth as '
                    'the tear opens and the bus approaches, within 0.5-0.6 deg/s')
            anims.append(dict(type='track', keys=keys, how='after rise / lean: localRotation = Slerp between the keys '
                              '(smoothstep between consecutive keys); ' + what))
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
                'disc centre in degrees (L* ~55 at 1 deg, the band by ~8 deg); LanbaiFog adds 0.35 x the same term. '
                'Round 4 (tech m1): once the disc has faded, scale the 1.6 core term by 0.35 + 0.65 x disc weight '
                '(halo only, #5A6A88-ish), keep the 0.06 tail',
        disc_gain_keys=[dict(t=round(C['U7'], 2), gain=1.0), dict(t=round(C['U7b'] - 1.0, 2), gain=0.6)],
        disc_gain_note='round 4 (AD round 3 item 3 \'one brightest point\'): the disc dims to x 0.6 over U7 .. U7b - 1 '
                       '(the wound outshines it; the sliver <= L* 82 at the key frame), then the U7b + 1.5 fade')


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


def retire_textures(lay):
    """round 8 (tech r4 m11): textures nothing uses any more go to Textures/_retired~/ (Unity ignores '~' folders):
    the retired surge ring's occlusion maps (T_Gate_SG*), the retired root sleeves, and the occlusion map of any custom
    variant not in the current layout. The '.png.<hash>' files next to the maps are the render's bake tags (ignore)."""
    import shutil
    occ = os.path.join(OUT_TEX, 'Occlusion')
    ret = os.path.join(OUT_TEX, '_retired~')
    used = {it['variant'] for it in lay} | {k for k in G.A4.CUSTOM if k.startswith('MU')}      # all 12 multitude poses ship (GateMultitude_v2)
    moved = []
    if os.path.isdir(occ):
        for f in sorted(os.listdir(occ)):
            if not f.startswith('T_Gate_') or '_Occlusion.png' not in f:
                continue
            key = f[len('T_Gate_'):f.index('_Occlusion.png')]
            if key not in used:
                os.makedirs(os.path.join(ret, 'Occlusion'), exist_ok=True)
                shutil.move(os.path.join(occ, f), os.path.join(ret, 'Occlusion', f))
                moved.append(f)
    for f in ('Gate_RootSleeve_512.png',):
        if os.path.exists(os.path.join(OUT_TEX, f)):
            os.makedirs(ret, exist_ok=True)
            shutil.move(os.path.join(OUT_TEX, f), os.path.join(ret, f))
            moved.append(f)
    print('retired %d textures -> Textures/_retired~' % len(moved))
    return moved


def main(write_tex=True):
    import gate_scene_shots as GS  # noqa: F401
    lay = G.build_layout()
    cells = None      # round 4: build_tide always uses the v3 cells (the v2.1 atlas json is in deliver/Tentacles/_superseded~)
    tide = G.build_tide(cells)
    beams, wedges = G.build_shafts()
    S_hero = G.tear_H(G.T_HERO) / G.TD.H
    if write_tex:
        os.makedirs(OUT_TEX, exist_ok=True)
        retire_textures(lay)
        from PIL import Image
        M = G.lane_mask(lay)
        Image.fromarray((np.clip(M, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
            os.path.join(OUT_TEX, 'Tear_CloudLanes_1024.png'))
    lo, hi, pw = G.BAND_EL
    doc = dict(
        about='Lanbai / 蓝白 · Tentacle gate layout v6 (gate round 8 = refine round 4 of the key art). Cloud art team -> '
              'Unity. Replaces the four tentacle groups of LB_Builder_Gate.cs (README_GateLayout.md). Shaders / C# '
              'UNCOMPILED (cloud side has no Unity): compile and check.',
        shaders=dict(arms='gate/Shaders/Lanbai_TentacleSway.shader v2.7 + LanbaiGateSky.cginc (same folder)',
                     sky='gate/Shaders/Lanbai_GateAirSky.shader v3 (the skybox, on the same include: the arms\' fog and '
                         'the sky are ONE definition; tech r4 BT-3)',
                     tear='deliver/Tear/Lanbai_Tear.shader v6 (+ Tear_Kit.fbx v6.1: Tear_FootSkyline, Tear_FootSkylineIn, Tear_LightLane; rip texture v7)',
                     tide='gate/Shaders/Lanbai_TentacleTide_v2.shader'),
        convention=__doc__.split('CONVENTIONS (also written into the JSON):')[1].strip(),
        units='metres, seconds (timeline t, 0 = departure), degrees',
        timeline=timeline_block(),
        cameras=cameras_block(),
        lights=dict(
            moon=dict(type='Directional', color='#D6E4FF', E=1.0, inspector=1.0, shadows='soft',
                      direction_to_light_unity=r3(M_W @ G.L_MOON, 4), azimuth_deg=G.MOON_AZ, elevation_deg=G.MOON_EL),
            tear=dict(type='Directional (CABIN ONLY: culling mask = the bus layers, NOT the tentacles)', color='#A99DE1',
                      E=0.8, inspector=0.8, shadows='none', direction='from _Udon_TearPos toward the bus each frame',
                      round4='the tentacles get the wound from TentacleSway v2.7 itself (v2.6 + the far scale / clamp '
                             '_WoundSpecFar / _WoundSpecMax, none above el +25 deg, OVER-THE-WHITE dimming): a LINE LIGHT on _Udon_TearFoot -> '
                             '_Udon_TearTop (wrap diffuse E = _TearDiffuse x (_TearDiffuseRef / d)^2, the tube-light '
                             'specular of the white on the wet skin, and the screen-space _RimWound). The renders: two '
                             'ellipse area lights the size of the white at the lens (front E 2.0 @ 600 m, back x 0.35, '
                             'diffuse only) + the analytical specular. Do not let the directional also light the arms '
                             '(double light)'),
            fill=dict(type='Directional', color='#5A6488', E=0.24, inspector=0.24, from_below=True)),
        sky_band=dict(
            near='#484D63 (fill #67697D) next to the tear', far='#2A3041 (fill #424755) at 50 deg', void='#070A14',
            azimuth='smoothstep(0, 50, |az|) near->far; x (1 - smoothstep(50, 60, |az|))',
            elevation='w_el = (1 - smoothstep(%g, %g, el))^%g  (_BandEl = (%g, %g, %g); round 4, AD round 3 item 3: '
                      'full to ~+7, 0.71 at +10, 0.32 at +13, 0.09 at +16, void by ~+20 -- the AD amendment to the '
                      'bible\'s +35)' % (lo, hi, pw, lo, hi, pw),
            gain='round 4: both band fills x %.2f (band peak next to the wound L* ~27; the bible\'s #484D63 / #2A3041 '
                 'become (0.1085, 0.1130, 0.1641) / (0.0436, 0.0504, 0.0726) linear)' % G.BAND_GAIN,
            back_band='round 8: + HazeFar x 0.80 x _BackBand x w_el x smoothstep(65, 120, |az|) (r4: 110..150; the SIDE '
                      'windows hold a horizon too). _BackBand 0.55 everywhere; the rear-window view uses 1.25 (renders: '
                      'look back_band; tech r4 M3 \'a silver horizon the rear arms cut dark against\'): put 1.25 on the '
                      'GateAirSky material and the rear arms\' material while the rear camera is the active view, or keep '
                      '0.55 and accept a dimmer rear horizon (L* ~9 instead of 12-16)',
            include='LanbaiGateSky.cginc LanbaiBand(): the ONE implementation (skybox and arm fog)',
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
                 cloud_top='arms: the last _CloudFade = 46 m (+-15 m noise in the cloud-sea frame) above '
                           '_Udon_CloudTop.x fade toward _CloudTopColor = (0.050, 0.056, 0.068) (rear: (0.10, 0.11, 0.13)) '
                           'under the same fog; the lowest _RootDissolve = 18 m dissolve; clip below cloudTop - 5 m',
                 multitude='round 8: per instance _FogCapI = its tier (0.45 / 0.58 / 0.70) x %.2f = %s (body = band -10 / '
                           '-8 / -5 L*) with _FogDensityScale 1; the tier also picks the material (rims)'
                           % (G.MULT_CAP_K, [round(c * G.MULT_CAP_K, 2) for c in (0.45, 0.58, 0.70)]),
                 over_white='round 8 (v2.7 OverWhite): an arm in front of the tear plane and on screen over the white '
                            '(or within 1.5 deg of its edge) is its own SHADOW SIDE: surface x 0.12, fog x (1 - 0.6), the '
                            'wound air x (1 - 0.85), and a 0.9 px wrap of the white on both silhouette edges'),
        rim_ladder='rim x exp(-0.0006 d) x clamp((900/d)^1.2, 0.12, 1) x (0.6 + 0.8 wet) x _RimGain; only on '
                   'light-facing edges of a BACK-LIT arm (moon: saturate(N.L) and the moon in front of the view; '
                   'wound: facing it and it in front); width _RimPx. Round 4: + _RimWound (NOT laddered): the edges '
                   'that face the white ON SCREEN, x (1 - N.V)^3 x the _RimWoundPx band x (0.25 + 0.75 exp(-angle on '
                   'screen from the white / 6 deg)), #A99DE1 -> (0.76, 0.80, 0.90) next to the white',
        instances=[inst_block(it) for it in lay],
        multitude=dict(
            note='round 8 (awe r4 B2 \'a reed bed that cost the frame its towers\'): FEWER, BIGGER, LAYERED. %d members in '
                 '%d CLUSTERS standing between / behind the giants\' cumulus towers with >= 6 deg of clear band between '
                 'them (>= 35 %% of az +-50 free): (az from the U7b eye, sigma deg, members, distance m, dominant height m) '
                 '= %s. One DOMINANT per cluster (500-650 m, height ratio ~3:1 to the others), the rest 30-68 %% of it. '
                 'Poses: reach (a straight thread, slight droop, no hook), curl (a REAL curl: radius 0.07 L, 170-230 deg, '
                 '>= 12 px at 4 km), fall (recoils with a half curl); every pose also MIRRORED (MU<n>m: its own mesh). Yaw '
                 'toward the wound +-22 deg.' % (len([it for it in lay if it['variant'].startswith('MU')]), len(G.MULT_CLUSTERS),
                                                [list(x) for x in G.MULT_CLUSTERS]),
            clusters=[dict(index=i, az_deg=c[0], sigma_deg=c[1], members=c[2], distance_m=c[3], dominant_height_m=c[4])
                      for i, c in enumerate(G.MULT_CLUSTERS)],
            tiers=[dict(tier=c, fog_cap=round(c * G.MULT_CAP_K, 3), max_distance_m=(None if dm > 1e8 else dm), material=MULT_TIER_MAT[round(c, 2)]['name'],
                        _RimGain=MULT_TIER_MAT[round(c, 2)]['_RimGain'], _RimWound=MULT_TIER_MAT[round(c, 2)]['_RimWound'],
                        _RimLadderFloor=MULT_TIER_MAT[round(c, 2)]['_RimLadderFloor'])
                   for (dm, c) in G.MULT_TIERS],
            lod_rule='round 9: LODGroup screen-relative heights LOD0 > 0.25, LOD1 > 0.06, LOD2 > 0.005 (README section 9); '
                     'the renders now use the LOD this rule picks (the cluster dominants are LOD0 in the key / U7: at '
                     'LOD2 they showed 25 m facets)',
            mesh='GateMultitude_v2.fbx: MU0..MU5 and MU0m..MU5m (12 poses; v1 had 6, no mirrors), each an empty with '
                 '_LOD0 / _LOD1 / _LOD2 (16 x 64 / 10 x 36 / 8 x 20 segments). Material = the instance\'s TIER material '
                 '(3, GPU instancing on). In Start(), per instance, on EVERY LOD renderer: GetPropertyBlock -> _Phase, '
                 '_FogCapI, _RevealGroup -> SetPropertyBlock (once; never per frame)',
            sway=dict(MULT_SWAY, how='a ROLLING surge (tech r4 M2): sin(TAU (tt + _Phase - t / wavelength-scaled)) with '
                                     '_Phase = frac(distance to the wound / 600 m): the crest runs INWARD; tip +-25 m at '
                                     '3-5 km = ~0.38 deg/s'),
            phase='instances[*].phase = frac(distance from the root to the tear axis / 600 m)',
            rise='each: instances[*].anim rise (straight up, trap), mostly HIDDEN: t0 >= U6 + 2 while the reveal is 0 '
                 '(reveal from U6 + 14); the dominants are up by U7b - 1, the others still surge through U7 .. U7b + 6 '
                 '(mid-surge at the hero moment); visible own speed <= 0.6 deg/s (instances[*].rise_vmax)',
            reveal_groups=dict(
                group0=dict(keys=[dict(t=round(C['U6'] + 14.0, 2), value=0.0), dict(t=round(C['U6'] + 18.0, 2), value=1.0),
                                  dict(t=round(C['U9'] - 2.0, 2), value=1.0), dict(t=round(C['U9'] - 1.0, 2), value=0.0)],
                            note='HOLD to U9 - 1 (tech r4 M2: the bible\'s U8 \'60 + tide\'): _Udon_MultReveal.x'),
                group1=dict(keys=[dict(t=round(C['U6'] + 14.0, 2), value=0.0), dict(t=round(C['U6'] + 18.0, 2), value=1.0),
                                  dict(t=round(C['U8'] - 4.0, 2), value=1.0), dict(t=round(C['U8'] + 1.0, 2), value=0.0)],
                            note='members that would stand within 6 deg of the white in the U8 forward view fade at U8 + 1: '
                                 '_Udon_MultReveal.y'),
                how='Udon: ONE VRCShader.SetGlobalVector(_Udon_MultReveal, (group0(t), group1(t), 0, 0)) per frame; the '
                    'tier materials have _UseGlobalReveal 1; renderer.enabled only when a group crosses 0'),
            count=len([it for it in lay if it['variant'].startswith('MU')]),
            count_group1=len([it for it in lay if it['variant'].startswith('MU') and it.get('near_white_U8')])),
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
                              how='material _Reveal (all blades): round 4: the wave recedes into the haze U7b + 2 .. '
                                  'U8 - 2 (the multitude holds the hero window; overdraw budget); disable the renderer at 0'),
                  rise='(tech r3 m2: text = code) each blade rises only its visible part (size x cos(lean) + 40 m); '
                       't0 = U6 + 4 + 6.5 x (12 km - distance) / 7.2 km (the outermost first, U6 + 4 .. U6 + 10.5), '
                       'duration clip(1.5 x angular depth / 0.45 deg/s, 12, 48) s (items[*].anim): crest speed median '
                       '0.45 deg/s, max 0.85 (final/motion_check.json tide_crest_deg_s). The hero window\'s "many '
                       'small" is the multitude (block multitude); the tide is the layer behind it.',
                  items=tide_block(tide)),
        shafts=dict(parent='Tear_Root', mesh='Tear_ShaftCard.fbx (deliver/Tear)',
                    note='round 4 (AD round 3 item 3): TWO beams (unequal 1.0 / 0.6), LOW and LATERAL through the arm '
                         'gaps, from the lens at 30-36 % of its height, ending at el +7.5 / +9 (never up into the void); '
                         'one soft lobe across; widen x3.2; material _Intensity 0.35 (r3: 0.8); depth-tested',
                    items=[dict(id=s['id'], start_os=r3(B2U @ np.asarray(s['start']), 2),
                                axis_os=r3(B2U @ np.asarray(s['axis']), 4), half_width_m=round(s['half_width'], 1),
                                length_m=round(s['length'], 1), gain=s['gain'], widen=s['widen'],
                                seen_at_azel_U7b=s['end_azel']) for s in beams]),
        shadow_wedges=dict(parent='GateRoot', blend='multiplicative (Blend Zero OneMinusSrcAlpha), queue 2990',
                           note='round 8 (awe r4 B3.4 \'shadows INSIDE the luminous fog\'): 4 wedges radiating from the '
                                'wound behind the arms that block it (Hand_L, Hand_R\'s forearm and its low finger, the '
                                'Engel\'s hand), alpha 0.30-0.42 (-6..-10 L* in the band), soft edges ~1.5 deg; '
                                'camera-facing about the axis',
                           items=[dict(id=w['id'], start=r3(u_pos(w['start']), 1), axis=r3(M_W @ w['axis'], 4),
                                       half_width_m=w['half_width'], length_m=w['length'], alpha=round(w['alpha'], 3),
                                       widen=w['widen']) for w in wedges]),
        tear=dict(
            Tear_Root=dict(parent='GateRoot', localPosition=r3(u_pos([0, 0, 0]), 2), localEulerAngles=[0, 180, 0],
                           localScale='H(t)/1000 (uniform; timeline.tear_H)'),
            kit='deliver/Tear kit v6 (round 8 = refine round 4; awe r4 B1 / B4, tech r4 B1 / M4 / M5 / M8): a POINTED lens '
                'foot (0.24 of the max width at the cloud top) that runs down into a V SLOT in the cloud sea\'s own billows '
                '(Tear_FootSkyline: two parted lips, backlit rim), lit mist over its lowest 50 m and a deep ragged cut; '
                'tilted veils, a far-lip band, a BROKEN fibre band (<= ~50 %% lit), snapped threads from one lip, tapered '
                'drooping fray clusters; bigger ASYMMETRIC flaps (a small high left flap whose lip the left hand coils, '
                'the right flap peeled toward the bus); tension folds as 3 sagging creases per grip (shade-dominant); '
                'halo v6 (#7A7B9C, centred on the hot spot, lip-weighted) with a DISTANCE FADE; the light lane on the '
                'cloud tops (Tear_LightLane). The v5 FootCloud cards are retired (README_Tear v6)',
            gate_overrides=dict(halo_intensity=1.0, skyfolds=1.0, shaft=0.35,
                                note='round 8: skyfolds 0.55 -> 1.0 (tech r4 M8); halo x the distance fade below'),
            fades=dict(note='round 8 (bible 1.9 overdraw <= 4.0 FSE over U8 .. U9: final/fse_U8.json). Every key list is '
                            'smoothstep between keys; renderer_off_at_zero: Udon sets renderer.enabled = false while the '
                            'value is 0 (tech r4 M5: a faded part still rasterises)',
                       cloudglow_additive_intensity_keys=[dict(t=round(k, 2), x=v) for k, v in G.CLOUDGLOW_ADD],
                       cloudglow_additive_renderer_off_at_zero=True,
                       skyfolds_intensity_keys=[dict(t=round(k, 2), x=v) for k, v in G.SKYFOLDS_FADE],
                       skyfolds_renderer_off_at_zero=True,
                       skyfolds_note='round 8: the creases come WITH the grips (0.15 at U6 + 13.5 -> 1 at U7: alone, '
                                     'before the hands, they read as whiskers), gone U8 + 2 .. U8 + 6',
                       halo_distance_fade='Tear_Halo _Intensity x k, k = saturate((smoothstep(250, 1200, D) - 0.25) / '
                                          '0.75), D = |tear plane z - eye z| (world, every frame; = LanbaiHaloFade() in '
                                          'LanbaiGateSky.cginc, which fades the arms\' wound air the same way): 1 beyond '
                                          '1.2 km, 0.47 at U8, 0 from D ~ 575 m (~U8 + 3.5); renderer OFF below 0.05 (tech r4 '
                                          'M4 + the overdraw budget: the faint cards still cost 1.3 FSE at U8 + 7)',
                       halo_renderer_off_at_zero=True,
                       lane_intensity_keys=[dict(t=round(k, 2), x=v) for k, v in G.LANE_FADE],
                       skyline_sink_keys='none: Tear_FootSkyline STAYS to U9 (it hides the lens / cloud junction; tech r4 '
                                         'B1 \'keep the foot to U9 - 1\')',
                       pool_fade_keys=[dict(t=round(k, 2), x=v) for k, v in G.POOL_FADE],
                       pool_fade_how='Tear_CloudGlow_Lit _Intensity x k and _FootGlow x k on BOTH CloudGlow materials (the '
                                     'lit pool and the foot lobe dim as the wound fills the windscreen); round 8: the '
                                     'ADDITIVE CloudGlow material has _NearFootCut 1 (0 within 1.5 half widths of the foot: '
                                     'the pool only multiplies the cloud\'s own relief there) and _FootAddK 0.25'),
            foot_skyline=dict(parent='Tear_Root', mesh='Tear_FootSkyline (Tear_Kit.fbx v6)', part='Lanbai/Tear Part=Skyline '
                              '(premultiplied, queue 2989)', texture='deliver/Tear/Textures/Tear_FootSkyline_1024x160.png',
                              _SkyCloud='the CloudSea cards\' moonlit colour behind it, LINEAR (renders: the deck impostor '
                                        'itself, (0.060, 0.066, 0.082) at U7)', _SkyRim=1.2, _SkyNear=0.27,
                              note='awe r4 B1.1 / tech r4 B1: the sea\'s billows in front of the foot, parted round the V '
                                   'slot the white runs into; the rim glows brightest beside the slot. Replaces the 5 v5 '
                                   'foot clouds (a front-lit pedestal at U7, white crumbs at U8)'),
            foot_skyline_inner=dict(parent='Tear_Root', mesh='Tear_FootSkylineIn (Tear_Kit.fbx v6.1)', part='Lanbai/Tear '
                                    'Part=Skyline (premultiplied, queue 2989): a COPY of the Tear_FootSkyline material with '
                                    'texture deliver/Tear/Textures/Tear_FootSkylineIn_512x160.png',
                                    _SkyCloud='as Tear_FootSkyline', _SkyRim=1.2, _SkyNear=0.27,
                                    placement='kit: 11 kit m in front of the lens foot (~8 m at S 0.7), 2 x 1.5 lens half '
                                              'widths wide, billows 3-8 m (x 0.35 of the outer row\'s heights)',
                                    note='round 9 (tech r4 B1 / awe r4 B4 acceptance): at U8 forward the white still ended on '
                                         'a 40-px straight line inside the V slot: the lens meeting the flat cloud-top plane, '
                                         'seen from ~120 m up (the slot\'s point projects 0.9 deg below it). This low backlit '
                                         'billow row stands in front of that line. In Unity the CloudSea cards are alpha '
                                         'billows already; keep the card anyway wherever the lens meets a flat cloud top'),
            light_lane=dict(parent='Tear_Root', mesh='Tear_LightLane (Tear_Kit.fbx v6)', part='Lanbai/Tear Part=Lane '
                            '(Blend DstColor One, queue 2989)', _LaneW=[1.6, 5.0, 1400.0, 0.0],
                            udon_scale_x='localScale.x = clamp(%.2f x D / (S x 420), 0.15, 1), D = eye -> foot (m), S = '
                                         'H / 1000: the quad only covers the lane (overdraw: 0.38 FSE at U8 unscaled, 0.13 '
                                         'scaled)' % G.LANE_HALF_K,
                            _LaneFoot=[0.527, 0.485, 0.776, 1.0], _LaneNear=[0.275, 0.323, 0.527, 1.0],
                            note='awe r4 B3.4: the glitter path of the wound on the cloud tops from the foot toward the '
                                 'eye (x (1 + lane) on the cards below it: crests brighten, troughs stay dark), w 1.6 -> 5 '
                                 'deg over 1.4 km, half fogged; dims with lane_intensity_keys'),
            foot_clouds_retired='v5 Tear_FootCloud_0..4: out of the kit (Tear_FootSkyline replaces them)',
            grips='the fingertips of Hand_L0/L2 and Hand_R0/R2 end on tear_def.GRIPS (kit space, moved with the '
                  'opening like the flaps): they hold the cloth through the approach (track keys to U9 - 1). Run 6: '
                  'Hand_L1 and Hand_R1 are WHIPS that cross the white in front of the lens (y -30 m in the tear frame) '
                  'and hook the OPPOSITE lip (run 6: L1 -> right lip at 24 %% H, R1 -> left lip at 36 %% H; gate_layout.CROSS), '
                  'tracked to that lip point (u 0.93) until U9 - 1: the fingertips interlace over the wound as if '
                  'closing it, and it keeps opening. Round 4: the whips are DIAGONALS that cross as an X at ~30 %% H, '
                  '~10 %% of the width left of the axis (L1: left lip 42 %% -> right lip 16 %%, behind, y -22; R1: right '
                  'lip 38 %% -> left lip 24 %%, in front, y -42); the grip fingers L0/L2/R0/R2 end in 1.25-turn COILS '
                  'round the hem (axis = the lip tangent); the Engel (Colossus_3) coils the right lip at %d %% H '
                  '(radius %g m): the third and biggest grip' % (round(100 * G.ENGEL_GRIP_ZF), G.ENGEL_COIL_R),
            crevasse=dict(round8='ON again as the short CANYON FLOOR of the foot (look crevasse 0.9, seam_lip 0.5; awe r4 '
                                 'B1.1): 230 m x S toward the bus, its walls end with it (r4 had a hairline to the camera)',
                          length_m=G.CREVASSE['length'], width_at_foot='%d %% of the lens width -> 0' % round(100 * G.CREVASSE['w0_frac']),
                          floor='#C0B9E4 (Glow fill x 0.35, fading with distance)', walls='x 0.30 darker (run 6: the foot\'s own '
                          'split, 240 m; the 700 m crevasse read as a crack / river drawn to the camera)',
                          unity='Tear_Foot: 3 alpha cards on the cloud top along -Z from the foot (or a decal-like '
                                'additive strip at cloud-top height) + Tear_CloudGlow')),
        clouds=dict(
            note='Renders use one volumetric impostor of the cloud deck to 9 km (cloud_deck.py gate3 / rear3); in '
                 'Unity the cloud sea is the Clouds kit (CloudSea strips + cards) moving at v_g.',
            cloud_top_world_y='-h_bus(t)',
            round4_grade='AD round 3 item 3: deck gain 0.44 (r3 0.52), far cloud gain 0.50; the MOONWARD half (az < -5) '
                         'keeps its billows (detail keep 0.6 near -> 0.30 far), a 1.35 gamma about the deck median within '
                         '2-4 km (silver crests, deep troughs), desaturated x 0.7 (cold silver) and a MOON PATH: '
                         'forward-scattered moonlight on the (blurred) crests in a +-7 deg wedge under the moon, 0.3-2.5 km. '
                         'Unity: the moon-side CloudSea cards with crest-weighted moon rim gain 1.6 inside that wedge.',
            silver_lining='round 4: tower / far-cloud cards within ~15 deg of the moon: the soft alpha border (0.03..0.85) '
                          'glows (0.82, 0.88, 1.0) x 0.9 x exp(-angle to the moon / 7 deg): 2-6 px silver linings. Round 8 '
                          '(awe r4 M1.3): FORWARD-SCATTER linings on the BLURRED alpha (soft, not a drawn outline), only '
                          '<= 15 deg from the moon, the tower body x 0.85',
            round8_deck='awe r4 B3.4 / M2: (1) the LIGHT LANE (tear.light_lane, Tear_LightLane); (2) the near-RIGHT deck '
                        '(az 10..45, 150-700 m) keeps 62 % of its billow detail and x 1.15 (it was a flat grey slab); (3) the '
                        'far deck quieting 0.12 -> 0.45 keep (billows read to the horizon); (4) towers RESTORED where the '
                        'r4 multitude had covered them (the clusters now stand between / behind them). Unity: CloudSea '
                        'card gains in those sectors (README_GateLayout §8)',
            foot_glow='round 4: Tear_CloudGlow foot lobe: the cloud under the white glows L* 55-70 within +-1.5 half widths '
                      '(_FootGlow 2.2, _FootLobe in kit metres)',
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
                 '1 -> 0.72, pivot at its base) over 25 s: the arm has dragged cloud down with it. Round 4 (tech M3): '
                 'from reveal + 6 s the tower SINKS into the sea (localPosition.y by sink_keys, 0.75 x its height over '
                 '25 s, <= 0.3 deg/s), alpha 1 -> 0 only in the last 2 s (all under the cloud line) -- no 6 s vanishing.',
            items=[dict(id=w['id'], hides=w['hides'], card=w['card'], position=r3(u_pos(w['loc']), 1),
                        width_m=round(w['width'], 1), height_m=round(w['height'], 1), opacity=w['opacity'],
                        mirror=w['mirror'], sag_keys=w['sag'], sink_keys=w.get('sink'), alpha_keys=w['alpha'])
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
            round4='REMOVED (AD round 3 item 5: the ring read as a lens smudge / an eye): ring_gain 0, core_gain 0, '
                   'shadow_mul 1 -- do not build it',
            note='round 3 (awe rear): the rear window\'s scale anchor. An ADDITIVE card lying on the cloud top at the '
                 'anti-moon point, a child of NearRoot (it travels with the bus): position = (-Lm.x d, -h_bus(t), -Lm.z d) '
                 'with Lm = the horizontal direction to the moon (Unity), d = h_bus(t) / tan(8 deg) (~1.07 km at U9). '
                 'Seen from the bus: a colourless ring of radius 3.2 deg (+0.75 x the cloud luminance, width 0.75 deg) + '
                 'a 1.7 deg core (+0.40) and, at the centre, a 0.3 deg dark spot (x 0.45): the bus\'s own shadow. '
                 'C* <= 6, queue 3001, unlit; size the card so 3.2 deg at distance d spans its ring.',
            moon_dir_unity=r3(M_W @ G.L_MOON, 4), ring_deg=3.2, ring_width_deg=0.75, ring_gain=0.0, core_deg=1.7,
            core_gain=0.0, shadow_deg=0.30, shadow_mul=1.0),
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
    mult_keys = []
    for it in lay:
        if it['variant'].startswith('MU'):           # round 4: the multitude poses go to GateMultitude_v1.fbx once
            if it['variant'] not in mult_keys:
                mult_keys.append(it['variant'])
            continue
        kind = arm_kind(it)
        par = bpy.data.objects.new(it['id'], None)
        bpy.context.scene.collection.objects.link(par)
        objs.append(par)
        near_lib = kind == 'near' and not G.A4.is_custom(it['variant'])
        for lod in (0, 1, 2):
            # round 4 (tech m13): near arms LOD0 = library LOD0 + one subsurf (~24 k), LOD1 = library LOD0 (~6 k),
            # LOD2 = library LOD1 (~2 k): x4 / x3 steps instead of the x12 pop
            src_lod = (0, 0, 1)[lod] if near_lib else lod
            me = GSc.variant_mesh(it['variant'], src_lod, it.get('girth', 1.0), it.get('form'))
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
            if lod == 0 and near_lib:
                m = ob.modifiers.new('Smooth', 'SUBSURF')
                m.levels = m.render_levels = 1
            ob.data.materials.append(bpy.data.materials.new('M_Tentacle_%s' % G.TEX_KEY.get(it['variant'], it['variant'])))
            objs.append(ob)
            me2.calc_loop_triangles()
            tris += len(me2.loop_triangles) * (4 if ob.modifiers else 1)
    export_unity.export_fbx(OUT_ARMS, objs)
    # round 4: GateMultitude_v1.fbx -- the 6 canonical multitude poses (root at the origin, leaning toward +Z in Unity
    # terms after the FBX axis conversion = +y in the gate frame), each an empty with _LOD0/1/2
    mobjs = []
    for key in sorted(set(mult_keys) | {k for k in G.A4.CUSTOM if k.startswith('MU')}):       # round 8: all 12 poses (MU0..MU5 + mirrors), used or not
        par = bpy.data.objects.new(key, None)
        bpy.context.scene.collection.objects.link(par)
        mobjs.append(par)
        for lod in (0, 1, 2):
            me = GSc.variant_mesh(key, lod, 1.0, None)
            me2 = me.copy()
            me2.name = '%s_LOD%d' % (key, lod)
            gr = np.zeros(len(me2.vertices), np.float32)
            me2.attributes['GR'].data.foreach_get('value', gr)
            lv = np.zeros(len(me2.loops), np.int32)
            me2.loops.foreach_get('vertex_index', lv)
            uvr = me2.uv_layers.new(name='UVRadius')
            uvr.data.foreach_set('uv', np.stack([gr[lv], np.zeros(len(lv), np.float32)], 1).ravel())
            ob = bpy.data.objects.new('%s_LOD%d' % (key, lod), me2)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = par
            ob.data.materials.append(bpy.data.materials.new('M_Tentacle_Multitude'))
            mobjs.append(ob)
    if mobjs:
        for o in objs:
            o.select_set(False)
        export_unity.export_fbx(OUT_MULT, mobjs)
        print('wrote', OUT_MULT, len(mobjs), 'objects')
    import shutil
    for nm in ('GateArms_v2.fbx', 'GateArms_v3.fbx', 'GateMultitude_v1.fbx'):      # superseded (round 8: v4 / v2)
        old = os.path.join(HERE, nm)
        if os.path.exists(old):
            os.makedirs(os.path.join(HERE, '_r4'), exist_ok=True)
            shutil.move(old, os.path.join(HERE, '_r4', nm))
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
