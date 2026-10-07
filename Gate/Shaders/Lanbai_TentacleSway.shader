//  v2.7c (gate round 9, 2026-10-02; UNCOMPILED): _RimLadderFloor (the far-rim ladder exp(-rho d) x (900/d)^1.2 was
//    x 0.01-0.02 at 3-5 km, so the multitude's tier A / B moon rims (awe r4 B2.3) were invisible): ladder = max(.., floor);
//    tier A 0.5 / B 0.3 with _RimGain 2.4 (GateLayout_v2.json multitude.tiers). _RimGain range 0..4. Nothing else changed.
//  v2.7 (gate round 8, 2026-10-02; cloud art team; UNCOMPILED - compile in Unity 2022.3 and check every pass):
//    * the sky / band / halo / moon air now come from the SHARED include LanbaiGateSky.cginc (same folder), which the
//      skybox Lanbai_GateAirSky v3 includes too (tech r4 BT-3). Incl. the BACK band (|az| 110-150) and the v6 halo cards
//      (centred on the hot spot, lip-weighted, #7A7B9C) with the distance fade smoothstep(250, 1200, D) (tech M4, m5, m6).
//    * THIN PARTS (tech r4 B2: evenly spaced rings / beads = one texture tile per circumference on the whips):
//      thinK = smoothstep(0.12, 0.40, b): main normal x thinK, smoothness -> 0.84, albedo -> _ThinAlbedo; the moon rim's
//      wet term uses that smoothness. The detail normal (non-integer tiling, fine) stays.
//    * WOUND SPECULAR (tech r4 M1, awe B3.1: the Engel's L* 100 streak): x farK = lerp(1, _WoundSpecFar,
//      smoothstep(_ReflFarRange)), x (0.4 + 0.6 wet streaks), none above el +25 deg from the eye, min(.., _WoundSpecMax
//      0.35; near arms 0.6); the source radius capped (min(hw / d, 0.6): no leak onto faces turned away from the white).
//    * OVER THE WHITE (awe r4 B3.2: arms in front of the wound read as grey rubber): OverWhite() = the point is in front
//      of the tear plane and ON SCREEN over the white or within _OverWhiteRamp deg of it (angle to the nearest axis
//      point minus the lens half width there, _TearHW0/1 = the half-width curve along the axis, 8 knots x the global
//      half width). Then albedo, emission and specular x _OverWhiteDim (0.12), the fog density x (1 - 0.6 ovr), the
//      wound's air x (1 - 0.85 ovr), and both silhouette edges carry a 0.9 px WRAP of the white (_WrapGain 1.2).
//    * the wound terms are OFF until Udon sets _Udon_TearFoot (w > 0) or the material's _TearFootM.w > 0 (tech m4;
//      default _TearFootM.w = 0: no fixed-world-point wound light while GateRoot moves).
//    * v2.7b _StreakKeep: the far specular scale spares the long wet streaks by this much (the renders did this since round
//      3 and the shader did not: the Engel's L* 100 streak in the r4 key was the MOON glint on a kept streak); per kind.
//    * the multitude's reveal: _Reveal x (_UseGlobalReveal ? _Udon_MultReveal[_RevealGroup] : 1) (tech r4 BT-4: one
//      global per group instead of 150 per-frame MaterialPropertyBlock writes). Groups: x = hold to U9 - 1, y = fade
//      at U8 + 1 (members that would stand by the white in the U8 forward view).
//    * fog tiers of the multitude: instanced _FogCapI 0.39 / 0.50 / 0.60 (round 8: tiers 0.45 / 0.58 / 0.70 x 0.86; the v2.6
//      header said 0.64 / 0.72 / 0.80 while the JSON had 0.72 / 0.80 / 0.86).
// =====================================================================================================
//  v2.6 (gate round 4, 2026-10-02; cloud art team; UNCOMPILED - compile in Unity 2022.3 and check every pass):
//    * THE WOUND IS THE KEY LIGHT (AD round 3 item 2). The tear is a LINE LIGHT on the segment _TearFoot -> _TearTop
//      (globals _Udon_TearFoot / _Udon_TearTop, xyz world, w = half width m; Udon writes them every frame from GateRoot
//      and H(t), README_GateLayout §2.1; material fallbacks _TearFootM / _TearTopM):
//        - diffuse: albedo x _TearLight x _TearDiffuse x (_TearDiffuseRef / d)^2 x saturate((N.L + w) / (1 + w))^2,
//          L / d to the closest point of the segment (the renders: two ellipse area lights the size of the white);
//        - specular (wet skin mirrors the white): representative point of the segment closest to the reflection ray
//          (Karis 2013 tube light), lobe exp(-(theta / sigma)^2), sigma^2 = sigma_r^2 + (halfWidth / d)^2,
//          sigma_r = 1.5 (1 - smoothness)^2 + 0.02, x min(1, sigma_s / sigma) x F_schlick(N.V, 0.04) x
//          _TearSpecRadiance x _TearSpec; NOT scaled by _ReflectionScaleFar (only the sky probe is);
//        - _RimWound: the edges that face the white ON SCREEN (N and L projected perpendicular to V) get a thin
//          violet -> violet-white wrap, x (1 - N.V)^3 x the _RimWoundPx band x (0.25 + 0.75 nearW),
//          nearW = exp(-angle(camera->P, camera->Q) / _RimWoundDeg); NOT on the far-rim ladder; the thin-tip
//          transmission uses the same screen-space facing (v2.5's facingT was ~0 on every silhouette).
//    * every world noise (root dissolve, ragged cloud-top fade) is sampled in the CLOUD-SEA frame:
//      pN = worldPos - _Udon_GateOrigin.xyz (global, GateRoot.position each frame). v2.5 sampled worldPos while GateRoot
//      moves at 59 m/s, so the dissolve holes streamed across every root at ~10 cells/s (tech BT-1).
//    * the moon rim's facing uses the global moon direction (moonD) like backM (tech m15).
//    * instanced _FogCapI (> 0: per-instance fog cap; the multitude's three tiers 0.64 / 0.72 / 0.80).
//    * _BandEl default (6, 22, 2) and the band fills x 0.80 (AD round 3 item 3: void by ~+20 deg).
// =====================================================================================================
//  v2.5 (gate round 3 run 6, 2026-10-01; UNCOMPILED): _RootDissolve (m, default 18; 0 = off). In the lowest
//    _RootDissolve m of the cloud-top fade zone the arm DISSOLVES: clip(smoothstep(-2, _RootDissolve, zf) - n), n = a
//    world-space value noise at 6 m (stable, no screen dither), zf = the same ragged height above _Udon_CloudTop as the
//    fade. Replaces the retired root 'sleeve' cards (their streaks read as a striped band with a straight top). Runs in
//    surf, so the generated shadow caster dissolves too.
// =====================================================================================================
//  v2.4 (gate round 3, 2026-10-01; cloud art team; UNCOMPILED - compile in Unity 2022.3 and check every pass):
//    * _Reveal (instanced, 0..1, default 1): applied AFTER the fog cap, f = 1 - (1 - f) x _Reveal (tech B1). Udon
//      writes it per instance from GateLayout_v2.json instances[*].reveal (smoothstep between keys) through the same
//      MaterialPropertyBlock as _Phase, and turns the renderer OFF while it is 0.
//    * the cloud-top extra fog is now ADDED to the instance's density scale, as in the renders (tech B3):
//      rho = dens x (_FogDensityScale + _FogExtra.x exp(-h / _FogExtra.y)), _FogExtra default (1.5, 25).
//      _FogDensityScale range 0..4.
//    * the fog COLOUR = LanbaiHorizon / LanbaiBand + the moon's air (#8FA3C8 x (1.6 e^-0.9a + 0.06 e^-0.32a) x
//      _MoonGlowFog 0.35, a = degrees from the moon, global _Udon_MoonDir) + the wound's air (the three halo cards'
//      radial profile around _Udon_TearPos at the ray's crossing of the tear plane, x _HaloFog 0.35, only for points
//      IN FRONT of that plane; size from the global _Udon_TearH). Exactly the renders' fog colour (tech B3).
//    * _ReflFarRange (x, y): the specular fades to _ReflectionScaleFar between x and y metres (was hard-coded
//      250..800; pillars 150..450, tech M1).
//    * UVRadius (TEXCOORD2.x = the BAKED local radius / root radius, girth included; GateArms_v3.fbx): the pixel rim,
//      the 1 px inflation and the tip thresholds use it when _UseUVRadius = 1 (tech M7). Library meshes: 0.
//    * _RimBackOnly (default 1): 0 = moon rims on every moon-facing edge (the rear-window material, tech M9).
//    * Engel (variant K): _ConvexCrease 0 and _OcclusionStrength 0 on its material (it borrows H's crease map).
// =====================================================================================================
//  v2.3 (gate round 2, 2026-10-01; cloud art team; UNCOMPILED - compile in Unity 2022.3 and check every pass):
//    * per-instance phase: instanced _Phase (GateLayout_v2.json instances[*].phase; Udon sets it with a
//      MaterialPropertyBlock in Start(), MPBs are not serialized). The v2.2 world-position term is GONE: GateRoot moves
//      59 m/s, so frac(dot(worldPos, k)) spun every arm at ~0.7 Hz and popped every ~1.5 s (critique BLOCKER 3).
//    * global _Udon_TearPos (w = 1 when set; Udon each frame: GateRoot.position + (0, -150 + 0.4 H(t), 0)) replaces
//      the per-material _TearPos for the band azimuth, tear rims, transmission (critique M11).
//    * #pragma target 4.0 (PC world; the surface Input needs > 10 interpolators with instancing + shadows).
//    * the arm form v3 is BAKED in GateArms_v2.fbx (keep _Girth = 1; the v2.2 inflation stays only for old meshes).
//    * cloud top: the last _CloudFade (25) m above _Udon_CloudTop fade (with world noise) toward _CloudTopColor under
//      the same fog; clip only below cloudTop - 5 m (critique M13: no hard cut on a shelf).
//    * rim ladder: every rim x exp(-rho d) x clamp((900 / d)^1.2, 0.12, 1) x (0.6 + 0.8 wet) x _RimGain, the moon
//      rims only when the moon is IN FRONT of the view (back-lit), the wound rim only facing it and it in front;
//      _RimPx per layer (critique B3).
//    * _ReflectionScaleFar: the direct + indirect specular is scaled by lerp(1, k, smoothstep(250, 800, d)) through a
//      custom lighting function LightingLanbai (lerp(diffuse-only, LightingStandard, k)): F0 alone cannot tame the
//      grazing moon glint (it was the neon pillar rim).
//    * band: _BandEl = (12, 35, 1) (the bible); below the horizon lerp(band, cold grey, _BelowDesat x
//      smoothstep(0, -4, el)).
//  Lanbai / TentacleSway  v2.2 (gate run 2)   蓝白 · 触手之门 · 触手 shader (Built-in RP surface shader)
//  v2.2 = v2.1 + what the gate key art needs (GateLayout_v2.json gives every value per instance):
//    * _Girth / _GirthFalloff (instanced): the arm is inflated along its normal by
//      (_Girth - 1) x (1 - t)^_GirthFalloff x B x root radius (object space, BEFORE the sway; also in the shadow
//      pass): a massive root tapering to the library's own neck and thread. Run 2: at 1-2 km the library's
//      girth read as kelp / grass blades. Bounds: see README_GateLayout (renderer bounds must be enlarged).
//    * cloud-sea clip: clip(worldPos.y - cloudTop + 2) -- the arm ends IN the cloud (cloudTop = the global
//      _Udon_CloudTop.x when _Udon_CloudTop.w > 0, else _CloudTopY); the in-shader height fog uses the same top.
//    * pixel rim: the continuous 1-3 px (far) / 3-8 px (near) outline the bible asks for on every silhouette, as
//      in the renders: rim band = N.V < sqrt(2 N px / r) with px = pixel footprint at this distance, r = local
//      radius; moon side (#9DB8FF x _RimPxMoon x moon-facing) + tear side (#A99DE1 x _RimPxTear x tear-facing x
//      proximity 200 m .. 1.6 km). _RimPx = N (pixels): 2.2 (far), 5 (near arms).
//    * _ReflectionScale: x Occlusion (indirect specular); near arms 0.45 (they mirrored the cabin as pale sheens).
//    * haze band elevation profile v2.1: w_el = (1 - smoothstep(_BandEl.x, _BandEl.y, el))^_BandEl.z,
//      defaults (4, 30, 1.5): full to +4 deg, ~half at +15, void by +30.
//  ORIGINAL v2.1 HEADER FOLLOWS.
//  ART BIBLE v2 §6·4 触手 shader: moon rim, tear rim, thin-tip transmission, in-shader height fog,
//  _FogCap + height falloff, LanbaiFog colour hook; skin 「生」 v2 (creases only on the concave side).
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!
//  This file was written in the cloud Blender workshop, which has no Unity. It has NOT been compiled.
//  The main session must compile and check it in Unity 2022.3 (Built-in RP, VRChat SDK) before use:
//    - Console: no errors and no warnings after import (forward base, forward add, and the shadow
//      caster that `addshadow` generates from vert()).
//    - Play mode: roots stay still, tips sway smoothly (no stair-steps on the thread-thin whips); two
//      instances of the same variant do NOT move in lockstep; shadows follow the sway; the thread tips
//      stay at least ~1 px wide far away (no sparkling dotted lines); nothing flickers in VR
//      (Single Pass Stereo: close one eye, then the other).
//    - The fogged arms sit IN the sky behind them: the fog band below must equal the skybox's haze band
//      (Lanbai/Sky haze-band mode, or Lanbai_GateAirSky.shader), or use the LanbaiFog hook.
//    - If anything fails, fall back to the plain Standard shader with the same textures
//      (the property names below are Standard's on purpose; README 5.1).
//
//  Mesh contract (Tentacle_A..H FBX):
//    UV0 (TEXCOORD0)  'UVMap'   U around (seam on the local +Z side), V along, conformal, centred on 0
//    UV1 (TEXCOORD1)  'UVSway'  x = t along the length (0 root -> 1 tip), y = per-variant phase 0..1
//                               FLOAT precision: this drives the sway (vertex colours import as UNorm8,
//                               a colour-driven sway turns the whips into a staircase) and it addresses
//                               the per-variant _OcclusionMap at (U, t).
//                               -> keep "Generate Lightmap UVs" OFF (it would overwrite UV1).
//    Vertex colour (LINEAR) R = t, G = phase (8-bit copies), B = radius / root radius (0 at the tip apex,
//                           ~1.07 max at the root swell -- 8 bits are enough for everything B does), A = 1.
//  Object space: origin at the root centre, the tentacle grows along +Y (Blender +Z).
//
//  Textures:
//    _MainTex          T_Tentacle_Albedo.png             (sRGB)       tiling (1, 1); colossi G/H (3, 3)   albedo sRGB 30-44, blue-plum mottling
//    _MetallicGlossMap T_Tentacle_MetallicSmoothness.png (sRGB OFF)   A = smoothness: base ~0.66, wet/dry patches,
//                                                                     longitudinal mucus streaks to 0.90
//    _BumpMap          T_Tentacle_Normal.png             (Normal map) OpenGL (+Y): compression wrinkles + taut hide
//    _DetailNormalMap  T_Tentacle_DetailNormal.png       (Normal map) tiling (4, 4.6); colossi (12, 13.8) <- set on the material
//    _OcclusionMap     T_Tentacle_<X>_Occlusion.png      (sRGB OFF, U Repeat / V Clamp, NOT tiled; ONE PER VARIANT)
//                      sampled at (UV0.x, UV1.x) = (U, t):  B = curvature-baked crease mask (1 = concave side),
//                      R = macro height (colossi G/H: 2-8 m scar grooves; 0.5 = flat), G = crease occlusion.
//
//  What the extras do (the Blender previews render exactly these lines, except the 1 px inflation):
//    * creases only on the concave side of a bend: the MAIN tangent normal (wrinkles + muscle bundles) is kept
//      at full strength where B = 1 and at _ConvexCrease where B = 0 (the convex side stays smooth and taut
//      with the long mucus streaks -- the long bright lines are what sell scale); the DETAIL normal (the hide's
//      fine relief) is applied everywhere, so the taut side reads as skin, not polished rubber;
//    * normals flattened at grazing angles (no stair-stepped rims);
//    * colossi (_Colossus = 1): macro undulation from R (4 taps, metric from _VariantDims) and NO fine
//      creases beyond 1.5 km (fade 1.0 -> 1.5 km);
//    * moon rim   #9DB8FF x pow(1 - N.V, 5) x saturate(0.3 - N.L_moon) x _RimMoon, beaded by the wet
//      streaks (x lerp(_RimWet, 1, saturate((smoothness - 0.58) / 0.30))): the continuous 1-3 px cold outline the bible asks for on every
//      near / mid silhouette, but broken like a grazing reflection on wet skin, not a sticker line;
//    * tear rim   #A99DE1 x pow(1 - N.V, 4) x tear-facing x proximity (1 < 200 m, 0 > 1.2 km) x _RimTear;
//    * thin-tip transmission (1 - B)^2 x tear light x #5B57A1 x _TipGlow, on the tear-facing side, when the
//      tear is behind the tip (thin whips glow faintly like a back-lit ear);
//    * tip indigo drift (albedo x _TipTint where B < 0.22);
//    * thin tips never thinner than _MinWidthPx pixels (vertex inflation along the normal; not in the
//      shadow pass) -- bible "细尖最小宽度膨胀 1 px";
//    * LanbaiFog (own fog, `nofog`), see lanbaiFog() and the hook below.
//  Keep the tentacles OUT of static batching (object-space vertex animation). GPU instancing is fine
//  (the per-instance phase: v2.3+ the instanced _Phase from GateLayout_v2.json; NOT the world position, GateRoot moves).
// =====================================================================================================
Shader "Lanbai/TentacleSway"
{
    Properties
    {
        [Header(Surface  same textures as a Standard material)]
        _MainTex ("Albedo (sRGB)", 2D) = "white" {}
        _Color ("Albedo Tint", Color) = (1, 1, 1, 1)
        [NoScaleOffset] _MetallicGlossMap ("Metallic (R) Smoothness (A)", 2D) = "black" {}
        _Glossiness ("Smoothness Scale (set 1 after switching from Standard)", Range(0, 1)) = 1
        [NoScaleOffset][Normal] _BumpMap ("Normal Map (OpenGL)", 2D) = "bump" {}
        _BumpScale ("Normal Scale", Range(0, 2)) = 1
        [Normal] _DetailNormalMap ("Detail Normal (set tiling 4, 4.6)", 2D) = "bump" {}
        _DetailNormalMapScale ("Detail Normal Scale", Range(0, 2)) = 1
        _GrazingFlatten ("Flatten Normals At Silhouettes", Range(0, 1)) = 0.5

        [Header(Per variant crease mask and macro height  sampled at U and t)]
        [NoScaleOffset] _OcclusionMap ("T_Tentacle_X_Occlusion (B crease mask, R macro height, G occlusion)", 2D) = "black" {}
        _ConvexCrease ("Crease Strength On The Convex Side", Range(0, 1)) = 0.06
        _OcclusionStrength ("Crease Occlusion", Range(0, 1)) = 1
        [Toggle] _Colossus ("Colossus (G, H): macro undulation, no fine creases beyond 1.5 km", Float) = 0
        _MacroStrength ("Macro Undulation Strength (colossi 0.35)", Range(0, 2)) = 0.35
        _VariantDims ("Root radius m, length m (object space; README table)", Vector) = (10, 300, 0, 0)

        [Header(Sway  UV1 x is t and UV1 y is phase)]
        _SwayAmplitude ("Amplitude (radians of bend at the tip)", Range(0, 0.3)) = 0.05
        _SwayFrequency ("Frequency (Hz)", Range(0, 1)) = 0.06
        _SwayWavelength ("Wavelength (fraction of the length)", Range(0.1, 4)) = 0.9
        _SwayStiffness ("Root Stiffness (power of t)", Range(1, 4)) = 2
        _SwaySecondary ("Second Plane Amount", Range(0, 1)) = 0.6
        _MinWidthPx ("Thin Tips Never Thinner Than (pixels, 0 = off)", Range(0, 3)) = 1

        [Header(Gate v2.2  girth  cloud clip  pixel rim  per instance from GateLayout_v2.json)]
        _Phase ("Per-instance sway phase (instanced; GateLayout instances[*].phase)", Range(0, 1)) = 0
        _RimGain ("Rim ladder gain (pillar .25, mid .14, colossus .08, hero .06, bg .05, near 1; multitude tier A / B 2.4)", Range(0, 4)) = 1
        _RimLadderFloor ("v2.7c: the far-rim ladder never drops below this (multitude tier A .5, B .3; others 0)", Range(0, 1)) = 0
        _ReflectionScaleFar ("Specular scale beyond _ReflFarRange.y (lerp from 1 at .x)", Range(0, 1)) = 1
        _ReflFarRange ("Specular fade range m: from x to y (pillars 150, 450)", Vector) = (250, 800, 0, 0)
        _StreakKeep ("v2.7b: wet streaks keep this much specular at distance (near/rear .8, mid/pillar .5, colossus .15, Engel/bg/multitude 0)", Range(0, 1)) = 0.8
        [Toggle] _RimBackOnly ("Moon rims only when the moon is in front of the view (rear window: 0)", Float) = 1
        [Toggle] _UseUVRadius ("Use UV2.x = baked radius / root radius (GateArms_v3.fbx: 1; library meshes: 0)", Float) = 0
        _Reveal ("Reveal 0..1 (instanced; 0 = all haze, renderer off)", Range(0, 1)) = 1
        _MoonGlowFog ("Moon air in the fog colour", Range(0, 2)) = 0.35
        _MoonGlowColor ("Moon aureole #8FA3C8, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole: a1, k1, a2, k2 (a1 e^-k1 deg + a2 e^-k2 deg)", Vector) = (1.6, 0.9, 0.06, 0.32)
        _HaloFog ("Wound air (halo cards) in the fog colour", Range(0, 2)) = 0.35
        _HaloColor ("Halo v6 #7A7B9C fill, linear", Vector) = (0.195, 0.198, 0.332, 1)
        _CloudTopColor ("Cloud-top colour the roots fade into (linear fill)", Vector) = (0.026, 0.030, 0.038, 1)
        _CloudFade ("Cloud-top fade height (m)", Float) = 25
        _RootDissolve ("Root dissolve height in the fade zone (m, 0 = off)", Float) = 18
        _BelowDesat ("Below-horizon desaturation of the band", Range(0, 1)) = 0.6
        _Girth ("Girth (root radius multiplier, 1 = library; GateArms_v2 meshes have it baked: keep 1)", Range(1, 4)) = 1
        _GirthFalloff ("Girth Falloff (power of 1 - t)", Range(0.5, 4)) = 1.5
        [Toggle] _ClipBelowCloud ("Clip Below The Cloud-Sea Top", Float) = 1
        _RimPx ("Pixel Rim Width N (px): far 2.2, near 5", Range(0, 10)) = 2.2
        _RimPxMoon ("Pixel Rim Moon Side Strength", Range(0, 4)) = 1.3
        _RimPxTear ("Pixel Rim Tear Side Strength", Range(0, 4)) = 2.2
        _ReflectionScale ("Reflection Scale (x occlusion; near arms 0.45)", Range(0, 1)) = 1

        // NOTE: every colour below is a LINEAR value declared as Vector on purpose. A Color property is treated
        // as sRGB and converted in a Linear-space project (the fog would no longer match the sky).
        [Header(Rims  ART BIBLE v2)]
        _RimMoonColor ("Moon Rim #9DB8FF, linear rgb", Vector) = (0.337, 0.479, 1.0, 1)
        _RimMoon ("Moon Rim Strength", Range(0, 3)) = 0.8
        _RimWet ("Moon Rim On Dry Skin (x, wet streaks = 1)", Range(0, 1)) = 0.25
        _RimDir ("Direction Toward The Moon (world xyz, GateLayout.json)", Vector) = (-0.206, 0.139, 0.969, 0)
        _RimTearColor ("Tear Rim #A99DE1, linear rgb", Vector) = (0.397, 0.337, 0.753, 1)
        _RimTear ("Tear Rim Strength (v2.6: the wound light below does the work)", Range(0, 2)) = 0.08
        [Header(v2.6 the wound as a line light)]
        _TearFootM ("Tear segment foot (world xyz, w = half width; 0 = no wound light until Udon sets the global)", Vector) = (0, 0, 1800, 0)
        _TearTopM ("Tear segment top (world xyz; global _Udon_TearTop wins)", Vector) = (-20, 600, 1830, 0)
        _TearDiffuse ("Wound diffuse E at the reference distance", Range(0, 8)) = 2.0
        _TearDiffuseRef ("Wound diffuse reference distance (m)", Float) = 600
        _TearWrap ("Wound diffuse wrap", Range(0, 1)) = 0.4
        _TearSpec ("Wound specular (wet skin mirrors the white)", Range(0, 4)) = 1.0
        _TearSpecRadiance ("Radiance of the white (linear)", Float) = 2.2
        _RimWound ("Wound rim (screen-space facing), not laddered", Range(0, 12)) = 5.0
        _RimWoundPx ("Wound rim width (px)", Range(0, 8)) = 2.5
        _RimWoundDeg ("Wound rim falloff (deg on screen from the white)", Float) = 6.0
        _RimWoundNear ("Wound rim colour next to the white (linear)", Vector) = (0.76, 0.80, 0.90, 1)
        _TearProximity ("Tear Rim: full below x m, none beyond y m", Vector) = (200, 1200, 0, 0)
        _TearPos ("Tear Centre (world xyz, GateLayout.json)", Vector) = (0, 297, 1800, 0)

        [Header(v2.7 thin parts  wound spec clamp  over the white  multitude reveal)]
        _ThinK ("Thin parts lose the main maps: b from x to y", Vector) = (0.12, 0.40, 0, 0)
        _ThinSmooth ("Thin parts smoothness", Range(0, 1)) = 0.84
        _ThinAlbedo ("Thin parts albedo (the map mean, linear)", Vector) = (0.017, 0.017, 0.022, 1)
        _WoundSpecMax ("Wound specular clamp (linear; near arms 0.6)", Range(0, 2)) = 0.35
        _WoundSpecFar ("Wound specular far scale (hands 1, pillars .5, colossi .3, Engel / bg / multitude .15)", Range(0, 1)) = 0.3
        _WoundSpecEl ("No wound specular above x deg (fade from y deg)", Vector) = (25, 18, 0, 0)
        _TearHW0 ("Lens half width along the axis, knots 0-3 (x the global half width)", Vector) = (0.234, 0.525, 0.739, 1.0)
        _TearHW1 ("Lens half width along the axis, knots 4-7", Vector) = (0.924, 0.622, 0.325, 0.089)
        _OverWhiteRamp ("Over the white: ramp beyond the lens edge (deg)", Float) = 1.5
        _OverWhiteDim ("Over the white: surface multiplier", Range(0, 1)) = 0.12
        _OverWhiteFog ("Over the white: fog density x (1 - this)", Range(0, 1)) = 0.6
        _OverWhiteAir ("Over the white: wound air x (1 - this)", Range(0, 1)) = 0.85
        _WrapGain ("Over the white: edge wrap gain", Range(0, 4)) = 1.2
        _WrapPx ("Over the white: edge wrap width (px)", Range(0, 4)) = 0.9
        _WrapColor ("Over the white: wrap colour (linear)", Vector) = (0.80, 0.80, 0.92, 1)
        [Toggle] _UseGlobalReveal ("Multitude: x the global _Udon_MultReveal of its group", Float) = 0
        _BackBand ("Back band (|az| 110-150) x HazeFar", Range(0, 2)) = 0.55

        [Header(Tip)]
        _TipTint ("Tip Indigo Drift (albedo multiplier)", Vector) = (0.86, 0.80, 1.10, 0)
        _Translucent ("Thin-Tip Transmission #5B57A1, linear rgb", Vector) = (0.105, 0.095, 0.356, 1)
        _TearLight ("Tear Light Colour x Intensity #A99DE1, linear rgb", Vector) = (0.397, 0.337, 0.753, 1)
        _TipGlow ("Thin Tip Transmission Gain", Range(0, 30)) = 2.2

        [Header(LanbaiFog  must equal the skybox haze band)]
        _FogDensity ("Exp Fog Density (per metre; global _Udon_FogDensity wins when set)", Float) = 0.0006
        _FogDensityScale ("Density Scale (per instance, GateLayout material)", Range(0, 4)) = 1
        _FogExtra ("Extra density over the cloud tops: x amount (ADDED to the scale), y height m", Vector) = (1.5, 25, 0, 0)
        _CloudTopY ("Cloud-Sea Top (world y)", Float) = 0
        _FogCap ("Fog Cap Beyond 1.5 km", Range(0, 1)) = 0.6
        _FogCapFrom ("Cap blends in from x to y metres", Vector) = (1300, 1700, 0, 0)
        _FogCapHeight ("Cap Height Falloff m (colossi 1600; 0 = none)", Float) = 500
        _HazeNear ("Haze Band Next To The Tear (v2.6: fill x 0.80), linear", Vector) = (0.1085, 0.1130, 0.1641, 1)
        _HazeFar ("Haze Band 50 deg Away (v2.6: fill x 0.80), linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _Void ("Void #070A14, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth: full to x deg, gone at y deg", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation: full to x deg, gone at y deg, power z (v2.6: 6, 22, 2)", Vector) = (6, 22, 2, 0)
        _BelowHorizon ("Below the horizon: from x deg to y deg, darkest factor z", Vector) = (-25, 0, 0.55, 0)
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "DisableBatching" = "True" }
        LOD 300

        CGPROGRAM
        #pragma surface surf Lanbai fullforwardshadows vertex:vert addshadow finalcolor:lanbaiFog nofog
        #pragma target 4.0
        #pragma multi_compile_instancing
        #include "UnityStandardUtils.cginc"
        #include "UnityPBSLighting.cginc"

        // ---- LanbaiFog hook (ART BIBLE §1.6) ------------------------------------------------------------
        // When LanbaiFog.cginc exists (§8.1 #8), put it next to this file and UNCOMMENT the next line. It must
        // #define LANBAI_FOG_INCLUDED and provide  half3 LanbaiHorizon(float3 viewDirWS)  (the horizon function
        // Lanbai/Sky shares). Until then this shader uses its own copy of the gate's haze band (LanbaiBand).
        // #include "LanbaiFog.cginc"
        // v2.7: the gate's band / moon air / wound air -- SHARED with the skybox Lanbai_GateAirSky v3 (same folder)
        #include "LanbaiGateSky.cginc"

        sampler2D _MainTex;
        sampler2D _MetallicGlossMap;
        sampler2D _BumpMap;
        sampler2D _DetailNormalMap;
        sampler2D _OcclusionMap;
        float4 _OcclusionMap_TexelSize;
        half4 _Color;
        half _Glossiness;
        half _BumpScale;
        half _DetailNormalMapScale;
        half _GrazingFlatten;
        half _ConvexCrease;
        half _OcclusionStrength;
        float _Colossus;
        half _MacroStrength;
        float4 _VariantDims;

        float _SwayAmplitude;
        float _SwayFrequency;
        float _SwayWavelength;
        float _SwayStiffness;
        float _SwaySecondary;
        float _MinWidthPx;

        float _ClipBelowCloud;
        half _RimPx;
        half _RimPxMoon;
        half _RimPxTear;
        half _ReflectionScale;
        float4 _Udon_CloudTop;        // global: x = cloud-sea top (world y) this frame; w > 0 = set (else _CloudTopY)

        half _RimGain;
        half _RimLadderFloor;
        half _ReflectionScaleFar;
        half _StreakKeep;
        float4 _CloudTopColor;
        float _CloudFade;
        float _RootDissolve;
        float4 _ReflFarRange;
        float _RimBackOnly;
        float _UseUVRadius;
        half _MoonGlowFog;
        half _HaloFog;

        UNITY_INSTANCING_BUFFER_START(LanbaiGate)
            UNITY_DEFINE_INSTANCED_PROP(float, _Phase)
            UNITY_DEFINE_INSTANCED_PROP(float, _Girth)
            UNITY_DEFINE_INSTANCED_PROP(float, _GirthFalloff)
            UNITY_DEFINE_INSTANCED_PROP(float, _Reveal)
            UNITY_DEFINE_INSTANCED_PROP(float, _FogCapI)
            UNITY_DEFINE_INSTANCED_PROP(float, _RevealGroup)
        UNITY_INSTANCING_BUFFER_END(LanbaiGate)

        float4 _ThinK; half _ThinSmooth; float4 _ThinAlbedo;
        half _WoundSpecMax, _WoundSpecFar; float4 _WoundSpecEl;
        float4 _TearHW0, _TearHW1;
        float _OverWhiteRamp; half _OverWhiteDim, _OverWhiteFog, _OverWhiteAir, _WrapGain, _WrapPx; float4 _WrapColor;
        float _UseGlobalReveal;
        float4 _Udon_MultReveal;      // v2.7 global: x = the multitude's reveal (group 0: hold to U9 - 1), y = group 1

        float4 _Udon_GateOrigin;      // v2.6 global: xyz = GateRoot.position this frame (the cloud-sea frame for noise)
        float4 _Udon_TearFoot;        // v2.6 global: xyz = the tear axis foot (world), w = half width m; w > 0 = set
        float4 _Udon_TearTop;         // v2.6 global: xyz = the tear axis top (world)
        float4 _TearFootM, _TearTopM;
        half _TearDiffuse, _TearDiffuseRef, _TearWrap, _TearSpec, _TearSpecRadiance;
        half _RimWound, _RimWoundPx, _RimWoundDeg;
        float4 _RimWoundNear;

        float3 NoisePos(float3 w)  { return w - _Udon_GateOrigin.xyz; }
        void TearSegment(out float3 A, out float3 B, out float hw)
        {
            bool g = _Udon_TearFoot.w > 0.0;
            A = g ? _Udon_TearFoot.xyz : _TearFootM.xyz;
            B = g ? _Udon_TearTop.xyz : _TearTopM.xyz;
            hw = g ? _Udon_TearFoot.w : _TearFootM.w;
        }

        // v2.7: 1 when the wound light is defined (Udon global set, or the material fallback w > 0)
        half WoundOn() { return (_Udon_TearFoot.w > 0.0 || _TearFootM.w > 0.0) ? 1.0 : 0.0; }

        // v2.7: the lens half width (m) at axis fraction u (8 knots, piecewise linear) x the global half width
        float TearHalfWidthAt(float u, float hwMax)
        {
            float x = saturate(u) * 7.0;
            float k[8] = { _TearHW0.x, _TearHW0.y, _TearHW0.z, _TearHW0.w, _TearHW1.x, _TearHW1.y, _TearHW1.z, _TearHW1.w };
            int i = (int)min(floor(x), 6.0);
            return lerp(k[i], k[i + 1], x - i) * hwMax;
        }

        // v2.7 (awe r4 B3.2): 0..1, the point is in front of the tear plane and on screen over the white or within
        // _OverWhiteRamp deg of its edge
        half OverWhite(float3 Pw)
        {
            if (WoundOn() < 0.5) return 0.0;
            float3 tA, tB; float thw;
            TearSegment(tA, tB, thw);
            float3 tAB = tB - tA;
            float uq = saturate(dot(Pw - tA, tAB) / max(dot(tAB, tAB), 1.0));
            float3 Qw = tA + tAB * uq;
            float3 Vc = normalize(Pw - _WorldSpaceCameraPos);
            float3 dQ = Qw - _WorldSpaceCameraPos;
            float angW = degrees(acos(clamp(dot(Vc, normalize(dQ)), -1.0, 1.0)));
            float angHW = degrees(atan(TearHalfWidthAt(uq, thw) / max(length(dQ), 1.0)));
            float r = max(_OverWhiteRamp, 0.05);
            half ovr = smoothstep(r, -0.15 * r, angW - angHW);
            half front = smoothstep(-40.0, 0.0, tA.z - Pw.z);                 // world z: the tear plane faces -Z
            return ovr * front;
        }

        float _CloudTopY;     // declared before CloudTop() uses it (Unity gate_test 2026-10-08: D3D "undeclared identifier")
        float CloudTop()
        {
            return (_Udon_CloudTop.w > 0.0) ? _Udon_CloudTop.x : _CloudTopY;
        }

        float4 _RimMoonColor;
        half _RimMoon;
        half _RimWet;
        float4 _RimDir;
        float4 _RimTearColor;
        half _RimTear;
        float4 _TearProximity;

        float3 TearPos()
        {
            return LanbaiTearPos();
        }

        // the specular scale rides in s.Alpha (opaque shader: Alpha is free): lerp(diffuse only, full Standard, k)
        inline half4 LightingLanbai(SurfaceOutputStandard s, float3 viewDir, UnityGI gi)
        {
            half k = s.Alpha;
            half4 full = LightingStandard(s, viewDir, gi);
            half ndl = saturate(dot(s.Normal, gi.light.dir));
            half3 diff = s.Albedo * (1.0 - s.Metallic) * (gi.light.color * ndl + gi.indirect.diffuse);
            half4 c = half4(lerp(diff, full.rgb, k), 1.0);
            return c;
        }

        inline void LightingLanbai_GI(SurfaceOutputStandard s, UnityGIInput data, inout UnityGI gi)
        {
            LightingStandard_GI(s, data, gi);
        }

        // cheap world-space value noise (the ragged cloud-top line)
        float Hash3(float3 p)
        {
            p = frac(p * 0.3183099 + 0.1);
            p *= 17.0;
            return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
        }

        float VNoise(float3 x)
        {
            float3 i = floor(x);
            float3 f = frac(x);
            f = f * f * (3.0 - 2.0 * f);
            return lerp(lerp(lerp(Hash3(i + float3(0, 0, 0)), Hash3(i + float3(1, 0, 0)), f.x),
                             lerp(Hash3(i + float3(0, 1, 0)), Hash3(i + float3(1, 1, 0)), f.x), f.y),
                        lerp(lerp(Hash3(i + float3(0, 0, 1)), Hash3(i + float3(1, 0, 1)), f.x),
                             lerp(Hash3(i + float3(0, 1, 1)), Hash3(i + float3(1, 1, 1)), f.x), f.y), f.z);
        }

        float4 _TipTint;
        float4 _Translucent;
        float4 _TearLight;
        half _TipGlow;

        float _FogDensity;
        float _FogDensityScale;
        float4 _FogExtra;
        float _FogCap;
        float4 _FogCapFrom;
        float _FogCapHeight;

        // Optional Udon globals (VRCShader.SetGlobal*). Never set = 0, and then the material values above win.
        float _Udon_FogDensity;       // Exp density; > 0 = set

        struct Input
        {
            float2 uv_MainTex;
            float2 uv_DetailNormalMap;
            float4 color : COLOR;
            float3 viewDir;          // tangent space (o.Normal is written)
            float3 worldPos;
            float3 worldNormal;
            float swayT;             // t along the length, from UV1 (float)
            float girthT;            // the girth multiplier at this ring (for the pixel rim's radius)
            float rawU;              // UV0.x without _MainTex tiling (the per-variant maps are addressed at (U, t))
            float radR;              // local radius / root radius (UV2.x baked, or vertex colour B x girth)
            INTERNAL_DATA
        };

        // rotations about the object X and Z axes (the tentacle grows along +Y, root at the origin)
        float3 RotX(float3 p, float a)
        {
            float s, c;
            sincos(a, s, c);
            return float3(p.x, c * p.y - s * p.z, s * p.y + c * p.z);
        }

        float3 RotZ(float3 p, float a)
        {
            float s, c;
            sincos(a, s, c);
            return float3(c * p.x - s * p.y, s * p.x + c * p.y, p.z);
        }

        // Undulation without skinning: every ring bends about the root by an angle that grows with
        // t^stiffness and travels up the body as a slow wave. Object space, so instance scale scales it.
        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            float t = saturate(v.texcoord1.x);
            // v2.3: the per-instance phase is a property (GateRoot moves: no world-position term)
            float ph = v.texcoord1.y + UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _Phase);

            // v2.2 girth: inflate along the normal by (g - 1) (1 - t)^p x B x R_root (object space; the tip apex has
            // B = 0 and does not move); before the sway and in every pass (the shadow follows the silhouette)
            float gG = UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _Girth);
            float gP = UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _GirthFalloff);
            float gk = (gG - 1.0) * pow(saturate(1.0 - t), max(gP, 0.01));
            v.vertex.xyz += v.normal * (gk * v.color.b * _VariantDims.x);
            o.girthT = 1.0 + gk;
            // v2.4: the baked radius (UVRadius) when the mesh carries it (GateArms_v3.fbx), else B x girth
            o.radR = (_UseUVRadius > 0.5) ? v.texcoord2.x : v.color.b * (1.0 + gk);

        #if !defined(UNITY_PASS_SHADOWCASTER)
            // thin tips never thinner than _MinWidthPx pixels: push the surface out along the normal by the
            // missing half-width (world units per pixel at this distance from unity_CameraProjection).
            float3 wposI = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
            float objScale = max(length(unity_ObjectToWorld._m00_m10_m20), 1e-4);
            float pxW = 2.0 * distance(_WorldSpaceCameraPos, wposI) / max(unity_CameraProjection._m11 * _ScreenParams.y, 1e-4);
            float rW = ((_UseUVRadius > 0.5) ? v.texcoord2.x : v.color.b * (1.0 + gk)) * _VariantDims.x * objScale;
            float infl = max(0.0, 0.5 * _MinWidthPx * pxW - rW);
            v.vertex.xyz += v.normal * (infl / objScale);
        #endif

            float w = pow(t, _SwayStiffness);
            float tt = _Time.y * _SwayFrequency;
            const float TAU = 6.2831853;
            float wl = max(_SwayWavelength, 0.05);
            float a1 = _SwayAmplitude * w * sin(TAU * (tt + ph - t / wl));
            float a2 = _SwayAmplitude * _SwaySecondary * w * sin(TAU * (0.73 * tt + 1.7 * ph - t / (0.8 * wl)) + 1.3);
            v.vertex.xyz = RotZ(RotX(v.vertex.xyz, a1), a2);
            v.normal = RotZ(RotX(v.normal, a1), a2);
            v.tangent.xyz = RotZ(RotX(v.tangent.xyz, a1), a2);
            o.swayT = t;
            o.rawU = v.texcoord.x;
        }

        // v2.7: LanbaiBand / HaloProfile / the wound's air live in LanbaiGateSky.cginc (shared with the skybox)
        half3 LanbaiFogColour(float3 V, float dist, half ovr)
        {
            float3 md = LanbaiMoonDir(_RimDir.xyz);
            return LanbaiGateFogColour(V, dist, md, _MoonGlowFog, _HaloFog * (1.0 - _OverWhiteAir * ovr));
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            // v2.2: the arm ends inside the cloud sea (also in the generated shadow caster, which runs surf for clip)
            if (_ClipBelowCloud > 0.5)
                clip(IN.worldPos.y - CloudTop() + 5.0);
            // v2.5: the root dissolves in the lowest _RootDissolve m of the (ragged) cloud-top fade zone
            if (_RootDissolve > 0.0)
            {
                float3 pN = NoisePos(IN.worldPos);           // v2.6: the cloud-sea frame (GateRoot moves)
                float zd = IN.worldPos.y - CloudTop() + (VNoise(pN / 18.0) - 0.5) * 30.0;
                clip(smoothstep(-2.0, _RootDissolve, zd) - VNoise(pN / 6.0 + 17.3));
            }
            half4 alb = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            half4 ms = tex2D(_MetallicGlossMap, IN.uv_MainTex);
            half3 n = UnpackScaleNormal(tex2D(_BumpMap, IN.uv_MainTex), _BumpScale);
            half3 nd = UnpackScaleNormal(tex2D(_DetailNormalMap, IN.uv_DetailNormalMap), _DetailNormalMapScale);

            // per-variant maps at (U, t) -- raw UV0.x, so the colossi's (3, 3) main tiling does not move them
            float2 ut = float2(frac(IN.rawU), IN.swayT);
            half4 oc = tex2D(_OcclusionMap, ut);

            float3 Vw = normalize(_WorldSpaceCameraPos - IN.worldPos);
            float dist = length(_WorldSpaceCameraPos - IN.worldPos);

            // normal strengths: the MAIN map (compression wrinkles + muscle bundles) x grazing flatten x crease
            // mask (concave side only) x far fade (colossi); the DETAIL map (the hide: fine relief, papillae,
            // pores) x grazing flatten only -- NOT masked, so the taut convex side is smooth skin, not rubber
            half ndvT = saturate(normalize(IN.viewDir).z);
            half graze = lerp(1.0, smoothstep(0.05, 0.5, ndvT), _GrazingFlatten);
            // v2.7 (tech r4 B2): thin parts lose the tile-periodic main maps (no evenly spaced rings / beads)
            half bT = (_UseUVRadius > 0.5) ? IN.radR : IN.color.b;
            half thinK = smoothstep(_ThinK.x, _ThinK.y, bT);
            half keep = graze * lerp(_ConvexCrease, 1.0, oc.b) * thinK;
            keep *= lerp(1.0, 1.0 - smoothstep(1000.0, 1500.0, dist), _Colossus);
            n = normalize(lerp(half3(0, 0, 1), n, keep));
            nd = normalize(lerp(half3(0, 0, 1), nd, graze));
            n = BlendNormals(n, nd);

            // colossi: 2-8 m macro undulation, height in R (texel metric: U around = 2 pi r, t = length)
            if (_Colossus > 0.5)
            {
                float2 e = _OcclusionMap_TexelSize.xy;
                float hu = tex2D(_OcclusionMap, ut + float2(e.x, 0)).r - tex2D(_OcclusionMap, ut - float2(e.x, 0)).r;
                float ht = tex2D(_OcclusionMap, ut + float2(0, e.y)).r - tex2D(_OcclusionMap, ut - float2(0, e.y)).r;
                float r = max(_VariantDims.x * IN.color.b, 0.05);
                float du = 2.0 * e.x * 6.2831853 * r;                     // metres across 2 texels around
                float dt = 2.0 * e.y * max(_VariantDims.y, 1.0);           // metres across 2 texels along
                half3 nm = normalize(half3(-_MacroStrength * hu / du, -_MacroStrength * ht / dt, 1.0));
                n = BlendNormals(n, nm);
            }
            o.Normal = n;

            // tip: the albedo drifts to indigo where the arm is thin (vertex colour B = r / r_root)
            half b = (_UseUVRadius > 0.5) ? IN.radR : IN.color.b;
            half tint = 1.0 - smoothstep(0.02, 0.22, b);
            o.Albedo = lerp((half3)_ThinAlbedo.rgb, alb.rgb, thinK) * lerp(half3(1, 1, 1), (half3)_TipTint.rgb, tint);
            o.Metallic = ms.r;
            half smoothV = lerp(_ThinSmooth, ms.a * _Glossiness, thinK);      // v2.7: one continuous wet sheen on the whips
            o.Smoothness = smoothV;
            o.Occlusion = lerp(1.0, oc.g, _OcclusionStrength) * _ReflectionScale;

            float3 Nw = normalize(WorldNormalVector(IN, float3(0, 0, 1)));      // smooth geometric normal
            half ndv = saturate(abs(dot(Nw, Vw)));

            // moon rim: #9DB8FF x pow(1 - N.V, 5) x saturate(0.3 - N.L_moon), beaded by the wet streaks
            float3 moonD = (_Udon_MoonDir.w > 0.0) ? normalize(_Udon_MoonDir.xyz) : normalize(_RimDir.xyz);
            half nlm = dot(Nw, moonD);                                          // v2.6 (m15): the global moon direction
            half wet = lerp(_RimWet, 1.0, saturate((smoothV - 0.58) / 0.30));
            // v2.3 rim ladder + back-lit only (the moon in front of the view)
            float densL = (_Udon_FogDensity > 0.0) ? _Udon_FogDensity : _FogDensity;
            half ladder = max(exp(-densL * dist) * clamp(pow(900.0 / max(dist, 1.0), 1.2), 0.12, 1.0), _RimLadderFloor) * _RimGain;   // v2.7c floor
            half backM = lerp(1.0, smoothstep(-0.15, 0.45, dot(-Vw, moonD)), _RimBackOnly);
            half wetL = 0.6 + 0.8 * smoothstep(0.55, 0.9, smoothV);
            half3 rimM = _RimMoonColor.rgb * (_RimMoon * pow(saturate(1.0 - ndv), 5.0) * saturate(0.3 - nlm) * wet * ladder * backM);

            // tear rim: #A99DE1 x pow(1 - N.V, 4) x tear-facing x proximity
            float3 tv = TearPos() - IN.worldPos;
            float tdist = length(tv);
            float3 Lt = tv / max(tdist, 1e-3);
            half facingT = smoothstep(-0.1, 0.6, dot(Nw, Lt));
            half prox = 1.0 - smoothstep(_TearProximity.x, _TearProximity.y, tdist);
            half backT = smoothstep(-0.2, 0.4, dot(-Vw, Lt));
            half3 rimT = _RimTearColor.rgb * (_RimTear * pow(saturate(1.0 - ndv), 4.0) * facingT * prox * ladder * backT);   // v2.3: wound in front only

            // thin-tip transmission: (1 - B)^2 x tear light x #5B57A1, only on thin tissue (B < 0.1-0.35),
            // on the tear-facing side, when the tear is behind the tip as seen from the camera
            half ib = saturate(1.0 - b);
            half thin = ib * ib * (1.0 - smoothstep(0.10, 0.35, b));
            half back = saturate(dot(-Vw, Lt));
            // ---- v2.6: the wound as a line light ------------------------------------------------------------
            float3 tA, tB; float thw;
            TearSegment(tA, tB, thw);
            float3 tAB = tB - tA;
            float3 Pw = IN.worldPos;
            float uq = saturate(dot(Pw - tA, tAB) / max(dot(tAB, tAB), 1.0));
            float3 Qw = tA + tAB * uq;                                           // nearest point of the white's axis
            float3 Lq = Qw - Pw;
            float dq = max(length(Lq), 1.0);
            Lq /= dq;
            float3 Nn = normalize(WorldNormalVector(IN, o.Normal));             // normal-mapped
            half wrapD = pow(saturate((dot(Nn, Lq) + _TearWrap) / (1.0 + _TearWrap)), 2.0);
            half Et = _TearDiffuse * min(pow(_TearDiffuseRef / dq, 2.0), 16.0);
            half3 woundDiff = o.Albedo * _TearLight.rgb / max(max(_TearLight.r, _TearLight.g), _TearLight.b) * (Et * wrapD * WoundOn());
            // specular: the point of the segment closest to the reflection ray (tube light)
            half ndvN = max(dot(Nn, Vw), 1e-3);
            float3 Rw = 2.0 * ndvN * Nn - Vw;
            float3 L0 = tA - Pw;
            float rl0 = dot(Rw, L0), rld = dot(Rw, tAB), l0ld = dot(L0, tAB);
            float tr = saturate((rl0 * rld - l0ld) / max(dot(tAB, tAB) - rld * rld, 1e-3));
            float3 Lc = L0 + tAB * tr;
            float dc = max(length(Lc), 1.0);
            float th = acos(clamp(dot(Rw, Lc / dc), -1.0, 1.0));
            half rough = 1.0 - smoothV;
            half sigR = 1.5 * rough * rough + 0.02;
            half sigS = min(thw / dc, 0.6);                                   // v2.7: capped source radius (no back leak)
            half sig = sqrt(sigR * sigR + sigS * sigS);
            half fres = 0.04 + 0.96 * pow(1.0 - ndvN, 5.0);
            half inFront = smoothstep(-60.0, 20.0, tA.z - Pw.z);              // nothing mirrored behind the tear plane
            half wOn = WoundOn();
            // v2.7 (tech r4 M1 / awe B3.1): far scale, wet-streak break, no wound glint above el +25, clamp
            half farK = lerp(1.0, _WoundSpecFar, smoothstep(_ReflFarRange.x, max(_ReflFarRange.y, _ReflFarRange.x + 1.0), dist));
            half brk = 0.4 + 0.6 * smoothstep(0.70, 0.88, smoothV);
            half elP = degrees(asin(clamp(-Vw.y, -1.0, 1.0)));
            half elK = smoothstep(_WoundSpecEl.x, _WoundSpecEl.y, elP);
            half wsAmt = _TearSpec * _TearSpecRadiance * fres * exp(-(th / sig) * (th / sig)) * min(sigS / sig, 1.0) * inFront;
            half3 woundSpec = half3(0.93, 0.92, 1.0) * (min(wsAmt * farK * brk * elK, _WoundSpecMax) * wOn);
            // _RimWound: the edges that face the white on screen
            float3 Np = normalize(Nw - Vw * dot(Nw, Vw) + 1e-5);
            float3 Lp = normalize(Lq - Vw * dot(Lq, Vw) + 1e-5);
            half facingS = saturate(dot(Np, Lp));
            float3 Vc = normalize(Pw - _WorldSpaceCameraPos);
            float3 Vq = normalize(Qw - _WorldSpaceCameraPos);
            half angW = degrees(acos(clamp(dot(Vc, Vq), -1.0, 1.0)));
            half nearW = exp(-angW / max(_RimWoundDeg, 0.5));

            half3 trans = _Translucent.rgb * _TearLight.rgb * (_TipGlow * thin * facingS * (0.3 + 0.7 * nearW));

            // v2.2 pixel rim (as rendered): band N.V < thr = sqrt(2 N px / r), px = pixel footprint, r = local radius
            float objScale = max(length(unity_ObjectToWorld._m00_m10_m20), 1e-4);
            float pxW = 2.0 * dist / max(unity_CameraProjection._m11 * _ScreenParams.y, 1e-4);
            float rLoc = max(IN.radR, 0.02) * _VariantDims.x * objScale;
            half thr = min(sqrt(2.0 * _RimPx * pxW / rLoc), 0.75);
            half band = pow(1.0 - min(ndv / max(thr, 1e-4), 1.0), 1.5);
            half moonK = smoothstep(-0.05, 0.55, nlm) * backM;
            half facingPx = smoothstep(0.0, 0.6, dot(Nw, Lt)) * backT;
            half proxPx = 1.0 - smoothstep(200.0, 1600.0, tdist);
            half3 rimPx = band * ladder * wetL * (_RimMoonColor.rgb * (_RimPxMoon * moonK) + _RimTearColor.rgb * (_RimPxTear * facingPx * proxPx));

            half thrW = min(sqrt(2.0 * _RimWoundPx * pxW / rLoc), 0.85);
            half bandW = pow(1.0 - min(ndv / max(thrW, 1e-4), 1.0), 1.2);
            half3 cW = lerp((half3)_RimTearColor.rgb, (half3)_RimWoundNear.rgb, nearW);
            // v2.7 (awe r4 B3.2): an arm IN FRONT of the white shows its shadow side: everything x _OverWhiteDim, the wound
            // rim off there, and a thin WRAP of the white on both silhouette edges instead
            half ovr = OverWhite(Pw);
            half3 rimW = cW * (_RimWound * pow(saturate(1.0 - ndv), 3.0) * facingS * (0.25 + 0.75 * nearW) * bandW * (1.0 - ovr) * WoundOn());
            half thrV = min(sqrt(2.0 * _WrapPx * pxW / rLoc), 0.85);
            half bandV = pow(1.0 - min(ndv / max(thrV, 1e-4), 1.0), 2.0);
            half3 wrapV = (half3)_WrapColor.rgb * (_WrapGain * bandV * ovr);
            half dimK = lerp(1.0, _OverWhiteDim, ovr);
            o.Albedo *= dimK;

            o.Emission = (rimM + rimT + trans * WoundOn() + rimPx + woundDiff + woundSpec) * dimK + rimW + wrapV;
            // the specular scale for LightingLanbai (opaque: Alpha is free)
            // v2.7b: the long wet streaks keep _StreakKeep of their specular at distance (they sell scale on the pillars and
            // hands); the far giants 0. v2.7c note: the Engel's L* 100 streak was the GRAZING MOON GLINT of the whole
            // specular (10 linear even at _ReflectionScaleFar 0.15), not only the kept streak: its material has 0.01
            half farS = lerp(_ReflectionScaleFar, 1.0, _StreakKeep * smoothstep(0.80, 0.90, smoothV));
            o.Alpha = lerp(1.0, farS, smoothstep(_ReflFarRange.x, max(_ReflFarRange.y, _ReflFarRange.x + 1.0), dist)) * dimK;
        }

        // LanbaiFog (ART BIBLE v2 §6·4): f = 1 - exp(-d rho (1 + extra exp(-h / 60 m))), h above the cloud tops
        // (the in-shader height fog that dissolves the roots into the cloud sea); beyond ~1.5 km
        // f = min(f, _FogCap) x exp(-h / _FogCapHeight) (never a ghost brighter than the sky).
        // Rims, speculars and transmission sit inside the fogged colour. Additive passes only lose light.
        void lanbaiFog(Input IN, SurfaceOutputStandard o, inout fixed4 color)
        {
            float3 d = IN.worldPos - _WorldSpaceCameraPos;
            float dist = length(d);
            float3 V = d / max(dist, 1e-4);
            float h = max(IN.worldPos.y - CloudTop(), 0.0);
            float dens = (_Udon_FogDensity > 0.0) ? _Udon_FogDensity : _FogDensity;
            // v2.4 (tech B3): the cloud-top extra is ADDED to the density scale (as in the renders)
            half ovr = OverWhite(IN.worldPos);                                // v2.7: the air in front of a silhouette over the white
            float rho = dens * (_FogDensityScale + _FogExtra.x * exp(-h / max(_FogExtra.y, 1.0))) * (1.0 - _OverWhiteFog * ovr);
            float f = 1.0 - exp(-dist * rho);
            float capI = UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _FogCapI);
            float fc = min(f, (capI > 0.0) ? capI : _FogCap) * (_FogCapHeight > 0.0 ? exp(-h / _FogCapHeight) : 1.0);
            f = lerp(f, fc, smoothstep(_FogCapFrom.x, _FogCapFrom.y, dist));
            // v2.4 (tech B1): the reveal comes AFTER the cap: at 0 the arm is all haze (and Udon turns it off)
            float rv = UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _Reveal);
            if (_UseGlobalReveal > 0.5)                                       // v2.7: the multitude's group reveal (one global)
                rv *= (UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _RevealGroup) > 0.5) ? _Udon_MultReveal.y : _Udon_MultReveal.x;
            f = 1.0 - (1.0 - f) * rv;
            // v2.3: the last _CloudFade m above the cloud top fade (ragged) toward the lit cloud-top colour
            float zf = IN.worldPos.y - CloudTop() + (VNoise(NoisePos(IN.worldPos) / 18.0) - 0.5) * 30.0;   // v2.6: sea frame
            half cf = smoothstep(_CloudFade + 3.0, -2.0, zf);
        #ifdef UNITY_PASS_FORWARDADD
            color.rgb *= (1.0 - f) * (1.0 - cf);
        #else
            color.rgb = lerp(color.rgb, (half3)_CloudTopColor.rgb, cf);
            color.rgb = lerp(color.rgb, LanbaiFogColour(V, dist, ovr), f);
        #endif
            color.a = 1.0;
        }
        ENDCG
    }
    FallBack "Standard"
}
