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
//  (the per-instance phase comes from the object's world position, instancing-safe).
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
        _RimGain ("Rim ladder gain (pillar .25, mid .14, colossus .08, hero .06, bg .05, near 1)", Range(0, 2)) = 1
        _ReflectionScaleFar ("Specular scale beyond _ReflFarRange.y (lerp from 1 at .x)", Range(0, 1)) = 1
        _ReflFarRange ("Specular fade range m: from x to y (pillars 150, 450)", Vector) = (250, 800, 0, 0)
        [Toggle] _RimBackOnly ("Moon rims only when the moon is in front of the view (rear window: 0)", Float) = 1
        [Toggle] _UseUVRadius ("Use UV2.x = baked radius / root radius (GateArms_v3.fbx: 1; library meshes: 0)", Float) = 0
        _Reveal ("Reveal 0..1 (instanced; 0 = all haze, renderer off)", Range(0, 1)) = 1
        _MoonGlowFog ("Moon air in the fog colour", Range(0, 2)) = 0.35
        _MoonGlowColor ("Moon aureole #8FA3C8, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole: a1, k1, a2, k2 (a1 e^-k1 deg + a2 e^-k2 deg)", Vector) = (1.6, 0.9, 0.06, 0.32)
        _HaloFog ("Wound air (halo cards) in the fog colour", Range(0, 2)) = 0.35
        _HaloColor ("Halo #8275D0 fill, linear", Vector) = (0.205, 0.178, 0.630, 1)
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
        _RimTear ("Tear Rim Strength", Range(0, 2)) = 0.08
        _TearProximity ("Tear Rim: full below x m, none beyond y m", Vector) = (200, 1200, 0, 0)
        _TearPos ("Tear Centre (world xyz, GateLayout.json)", Vector) = (0, 297, 1800, 0)

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
        _HazeNear ("Haze Band Next To The Tear #484D63, linear", Vector) = (0.0648, 0.0742, 0.1248, 1)
        _HazeFar ("Haze Band 50 deg Away #2A3041, linear", Vector) = (0.0232, 0.0296, 0.0512, 1)
        _Void ("Void #070A14, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth: full to x deg, gone at y deg", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation: full to x deg, gone at y deg, power z (v2.3: the bible 12, 35, 1)", Vector) = (12, 35, 1, 0)
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
        half _ReflectionScaleFar;
        float4 _CloudTopColor;
        float _CloudFade;
        float _RootDissolve;
        half _BelowDesat;
        float4 _Udon_TearPos;         // global: the tear core (world) this frame; w > 0 = set (else _TearPos)
        float4 _Udon_TearH;           // global: x = tear height H(t) m; w > 0 = set (else 640)
        float4 _Udon_MoonDir;         // global: xyz = world direction TO the moon; w > 0 = set (else _RimDir)
        float4 _ReflFarRange;
        float _RimBackOnly;
        float _UseUVRadius;
        half _MoonGlowFog;
        float4 _MoonGlowColor;
        float4 _MoonGlowShape;
        half _HaloFog;
        float4 _HaloColor;

        UNITY_INSTANCING_BUFFER_START(LanbaiGate)
            UNITY_DEFINE_INSTANCED_PROP(float, _Phase)
            UNITY_DEFINE_INSTANCED_PROP(float, _Girth)
            UNITY_DEFINE_INSTANCED_PROP(float, _GirthFalloff)
            UNITY_DEFINE_INSTANCED_PROP(float, _Reveal)
        UNITY_INSTANCING_BUFFER_END(LanbaiGate)

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
        float4 _TearPos;

        float3 TearPos()
        {
            return (_Udon_TearPos.w > 0.0) ? _Udon_TearPos.xyz : _TearPos.xyz;
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
        float _CloudTopY;
        float _FogCap;
        float4 _FogCapFrom;
        float _FogCapHeight;
        float4 _HazeNear;
        float4 _HazeFar;
        float4 _Void;
        float4 _BandAz;
        float4 _BandEl;
        float4 _BelowHorizon;

        // Optional Udon globals (VRCShader.SetGlobal*). Never set = 0, and then the material values above win.
        float4 _Udon_FogBandDir;      // xyz: world direction of the band centre (the tear); length < 0.5 = unset
        float4 _Udon_FogBandColor;    // rgb: band colour next to the tear (linear); a > 0 = set
        float _Udon_FogBandWidth;     // azimuth (deg) where the band is fully the far colour; > 0 = set
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

        // LanbaiBand: the haze-band sky colour in world direction V (camera -> point). Azimuth is measured from
        // the horizontal direction camera -> tear (or _Udon_FogBandDir when set). Identical to the preview
        // (_band_colour in build_library.py) and to lib/preview_rig.py's world.
        half3 LanbaiBand(float3 V)
        {
            float el = degrees(asin(clamp(V.y, -1.0, 1.0)));
            float3 T = (dot(_Udon_FogBandDir.xyz, _Udon_FogBandDir.xyz) > 0.25) ? _Udon_FogBandDir.xyz
                                                                               : (TearPos() - _WorldSpaceCameraPos);
            float2 th = normalize(T.xz + float2(1e-5, 0.0));
            float2 vh = normalize(V.xz + float2(1e-5, 0.0));
            float az = degrees(acos(clamp(dot(th, vh), -1.0, 1.0)));
            float bw = (_Udon_FogBandWidth > 0.0) ? _Udon_FogBandWidth : _BandAz.x;
            float bg = (_Udon_FogBandWidth > 0.0) ? _Udon_FogBandWidth + (_BandAz.y - _BandAz.x) : _BandAz.y;
            half3 nearC = (_Udon_FogBandColor.a > 0.0) ? (half3)_Udon_FogBandColor.rgb : (half3)_HazeNear.rgb;
            half3 band = lerp(nearC, (half3)_HazeFar.rgb, smoothstep(0.0, bw, az));
            float wel = 1.0 - smoothstep(_BandEl.x, _BandEl.y, el);
            wel = pow(saturate(wel), (_BandEl.z > 0.0) ? _BandEl.z : 1.0);
            float w = (1.0 - smoothstep(bw, bg, az)) * wel;
            half3 sky = lerp((half3)_Void.rgb, band, w);
            float below = lerp(_BelowHorizon.z, 1.0, smoothstep(_BelowHorizon.x, _BelowHorizon.y, el));
            half lum = dot(sky, half3(0.2126, 0.7152, 0.0722));
            sky = lerp(sky, lum * half3(0.92, 0.98, 1.12), _BelowDesat * smoothstep(0.0, -4.0, el));
            return sky * below;
        }

        // the halo cards' radial profile (Halo_512: soft core + long tail, 0 at q = 1)
        half HaloProfile(float q)
        {
            float f = 0.62 / pow(1.0 + (q / 0.16) * (q / 0.16), 1.15) + 0.38 * exp(-(q / 0.55) * (q / 0.55));
            return (half)(saturate((f - 0.0296) / 0.9704) * smoothstep(1.0, 0.72, q));
        }

        // v2.4: the air's colour = the band + the moon's air + the wound's air (as in the renders)
        half3 LanbaiFogColour(float3 V, float dist)
        {
        #if defined(LANBAI_FOG_INCLUDED)
            half3 c = LanbaiHorizon(V);
        #else
            half3 c = LanbaiBand(V);
        #endif
            float3 md = (_Udon_MoonDir.w > 0.0) ? normalize(_Udon_MoonDir.xyz) : normalize(_RimDir.xyz);
            float am = degrees(acos(clamp(dot(V, md), -1.0, 1.0)));
            c += _MoonGlowColor.rgb * (_MoonGlowFog * (_MoonGlowShape.x * exp(-_MoonGlowShape.y * am) + _MoonGlowShape.z * exp(-_MoonGlowShape.w * am)));
            // the wound's air: the three halo cards (w, h at H = 1000 m: 330 x 620 gain 2.8, 360 x 880, 640 x 1000)
            // on the tear plane (world z = tear z; the kit faces -Z), seen along V, only in front of that plane
            float3 T = TearPos();
            float tpl = (T.z - _WorldSpaceCameraPos.z) / max(V.z, 1e-4);
            if (_HaloFog > 0.0 && V.z > 1e-3 && dist < tpl)
            {
                float k = ((_Udon_TearH.w > 0.0) ? _Udon_TearH.x : 640.0) / 1000.0;
                float2 r = (_WorldSpaceCameraPos.xy + V.xy * tpl) - T.xy;
                half acc = 2.8 * HaloProfile(length(r / (0.5 * k * float2(330.0, 620.0))))
                         + HaloProfile(length(r / (0.5 * k * float2(360.0, 880.0))))
                         + HaloProfile(length(r / (0.5 * k * float2(640.0, 1000.0))));
                c += _HaloColor.rgb * (acc * _HaloFog);
            }
            return c;
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            // v2.2: the arm ends inside the cloud sea (also in the generated shadow caster, which runs surf for clip)
            if (_ClipBelowCloud > 0.5)
                clip(IN.worldPos.y - CloudTop() + 5.0);
            // v2.5: the root dissolves in the lowest _RootDissolve m of the (ragged) cloud-top fade zone
            if (_RootDissolve > 0.0)
            {
                float zd = IN.worldPos.y - CloudTop() + (VNoise(IN.worldPos / 18.0) - 0.5) * 30.0;
                clip(smoothstep(-2.0, _RootDissolve, zd) - VNoise(IN.worldPos / 6.0 + 17.3));
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
            half keep = graze * lerp(_ConvexCrease, 1.0, oc.b);
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
            o.Albedo = alb.rgb * lerp(half3(1, 1, 1), (half3)_TipTint.rgb, tint);
            o.Metallic = ms.r;
            half smoothV = ms.a * _Glossiness;
            o.Smoothness = smoothV;
            o.Occlusion = lerp(1.0, oc.g, _OcclusionStrength) * _ReflectionScale;

            float3 Nw = normalize(WorldNormalVector(IN, float3(0, 0, 1)));      // smooth geometric normal
            half ndv = saturate(abs(dot(Nw, Vw)));

            // moon rim: #9DB8FF x pow(1 - N.V, 5) x saturate(0.3 - N.L_moon), beaded by the wet streaks
            half nlm = dot(Nw, normalize(_RimDir.xyz));
            half wet = lerp(_RimWet, 1.0, saturate((smoothV - 0.58) / 0.30));
            // v2.3 rim ladder + back-lit only (the moon in front of the view)
            float densL = (_Udon_FogDensity > 0.0) ? _Udon_FogDensity : _FogDensity;
            half ladder = exp(-densL * dist) * clamp(pow(900.0 / max(dist, 1.0), 1.2), 0.12, 1.0) * _RimGain;
            float3 moonD = (_Udon_MoonDir.w > 0.0) ? normalize(_Udon_MoonDir.xyz) : normalize(_RimDir.xyz);
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
            half3 trans = _Translucent.rgb * _TearLight.rgb * (_TipGlow * thin * facingT * back * back);

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

            o.Emission = rimM + rimT + trans + rimPx;
            // the specular scale for LightingLanbai (opaque: Alpha is free)
            o.Alpha = lerp(1.0, _ReflectionScaleFar, smoothstep(_ReflFarRange.x, max(_ReflFarRange.y, _ReflFarRange.x + 1.0), dist));
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
            float rho = dens * (_FogDensityScale + _FogExtra.x * exp(-h / max(_FogExtra.y, 1.0)));
            float f = 1.0 - exp(-dist * rho);
            float fc = min(f, _FogCap) * (_FogCapHeight > 0.0 ? exp(-h / _FogCapHeight) : 1.0);
            f = lerp(f, fc, smoothstep(_FogCapFrom.x, _FogCapFrom.y, dist));
            // v2.4 (tech B1): the reveal comes AFTER the cap: at 0 the arm is all haze (and Udon turns it off)
            f = 1.0 - (1.0 - f) * UNITY_ACCESS_INSTANCED_PROP(LanbaiGate, _Reveal);
            // v2.3: the last _CloudFade m above the cloud top fade (ragged) toward the lit cloud-top colour
            float zf = IN.worldPos.y - CloudTop() + (VNoise(IN.worldPos / 18.0) - 0.5) * 30.0;
            half cf = smoothstep(_CloudFade + 3.0, -2.0, zf);
        #ifdef UNITY_PASS_FORWARDADD
            color.rgb *= (1.0 - f) * (1.0 - cf);
        #else
            color.rgb = lerp(color.rgb, (half3)_CloudTopColor.rgb, cf);
            color.rgb = lerp(color.rgb, LanbaiFogColour(V, dist), f);
        #endif
            color.a = 1.0;
        }
        ENDCG
    }
    FallBack "Standard"
}
