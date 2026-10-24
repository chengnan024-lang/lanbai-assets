// =====================================================================================================
//  Lanbai/Cabin   蓝白 · 车厢（圣经 §4.2 材质、§4.3 管灯、§4.4 收音机表盘、§4.7 目的地牌、§4.8 光与“慢慢消失”）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + the real Unity 2022.3.22f1
//      CGIncludes, ForwardBase / ForwardAdd / ShadowCaster), never compiled or looked at in Unity. !!!
//
//  Standard-lighting surface shader. One material per surface of bible §4.2 (Cabin/README.md has every value).
//  Light terms (all linear, scene-referred):
//    tubes     albedo x _CabinTubeLM.rgb (uv1, E in Unity units, baked in Blender) x _Udon_CabinLightmap
//    ambient   albedo x _Udon_CabinAmbient.rgb x AO (_CabinTubeLM.a)   -- replaces Unity's SH ambient (no double count:
//              _SHAmbientK = 0 subtracts ShadeSH9 from the indirect diffuse; vertex lights stay)
//    main light  the one shadowed directional (RenderSettings.sun = Gate_Lights/Moon, D-24), Standard BRDF
//    ForwardAdd  real-time Important lights (wound light = the only extra directional, D-08 limited; sodium sweep spot;
//              mirror-rim point). POINT_COOKIE / DIRECTIONAL_COOKIE skipped (none in the film).
//    caustics  LanbaiCabinCaustics (incl. 7c from below via _Udon_Caustics.y), base pass only
//    slice     _Udon_CabinSlice / Color (4c crossing bands), mirror line _Udon_MirrorPlane, rim light _Udon_MirrorRimLight
//    emission  _EmitMode: 1 tube diffuser x _Udon_CabinLightmap, 2 radio dial x _Udon_RadioDial (dial tex A),
//              3 gauges (#5FA89A x 0.3), 4 destination blind letters x _Udon_CabinLightmap
//  Bleach / erosion / 3 cm rim / seat sphere / floor patch / D-26 hole: LanbaiCabinCommon.cginc. The shadow caster
//  (addshadow) runs the same clip.
//  Fog: LanbaiFog (finalcolor + nofog); ForwardAdd attenuates only.
// =====================================================================================================
Shader "Lanbai/Cabin"
{
    Properties
    {
        [Header(Surface  bible 4.2)]
        _Color ("Albedo (sRGB)", Color) = (0.851, 0.831, 0.773, 1)
        _MainTex ("Albedo map (uv0 metric or trim, optional)", 2D) = "white" {}
        _Glossiness ("Smoothness", Range(0, 1)) = 0.45
        _Metallic ("Metallic (0 or 1)", Range(0, 1)) = 0
        _HeightSmooth ("Height smoothness band  y0 y1 smoothness enable", Vector) = (1.62, 2.42, 0.80, 0)

        [Header(Detail normal and mask  uv0 metres)]
        [NoScaleOffset][Normal] _DetailNormal ("Detail normal", 2D) = "bump" {}
        _DetailNormalScale ("Detail normal strength", Range(0, 2)) = 0
        [NoScaleOffset] _DetailMask ("Detail mask RGB (linear)", 2D) = "black" {}
        _DetailTile ("Tiling  1 per tile metres", Float) = 5
        _MaskAlbedoMul ("Mask albedo multiplier at R G B = 1", Vector) = (1, 1, 1, 0)
        _MaskSmoothAdd ("Mask smoothness add at R G B = 1", Vector) = (0, 0, 0, 0)

        [Header(Vertex colour  R grime  G wear  B sun fade and cracks)]
        _GrimeColor ("Grime colour  vertex R", Color) = (0.36, 0.33, 0.27, 1)
        _GrimeAmount ("Grime amount", Range(0, 1)) = 0
        [Toggle] _GrimeAbsolute ("Grime is the colour itself (dust on a dark floor), not albedo x colour x 2", Float) = 0
        _WearColor ("Wear colour  vertex G", Color) = (0.416, 0.204, 0.204, 1)
        _WearSmooth ("Wear smoothness", Range(0, 1)) = 0.66
        _WearAmount ("Wear amount", Range(0, 1)) = 0
        _SunFadeColor ("Sun fade colour  vertex B up to 0.75", Color) = (0.478, 0.290, 0.282, 1)
        _SunFadeSmooth ("Sun fade smoothness", Range(0, 1)) = 0.40
        _SunFadeAmount ("Sun fade amount", Range(0, 1)) = 0
        _CrackColor ("Crack colour  vertex B above 0.75", Color) = (0.541, 0.416, 0.376, 1)
        _CrackSmooth ("Crack smoothness", Range(0, 1)) = 0.20
        _CrackAmount ("Crack amount", Range(0, 1)) = 0

        [Header(Tube light map  uv1)]
        _UseTubeLM ("Use CabinTubeLM  needs uv1  0 or 1", Float) = 1
        [NoScaleOffset] _CabinTubeLM ("CabinTubeLM  RGB E linear HDR  A AO", 2D) = "black" {}
        _TubeLMConst ("Constant E when no uv1  rgb (linear, Vector: no gamma conversion)", Vector) = (0.6, 0.66, 0.68, 1)
        _SHAmbientK ("Keep Unity SH ambient  0 = cabin ambient only", Range(0, 1)) = 0
        _CabinLight ("Cabin light terms  1 cabin  0 exterior", Range(0, 1)) = 1

        [Header(Exterior atlas on uv1)]
        _UseAtlas ("Use uv1 atlas  0 or 1", Float) = 0
        [NoScaleOffset] _AtlasAlbedo ("Atlas albedo  sRGB", 2D) = "white" {}
        [NoScaleOffset] _AtlasMask ("Atlas mask  R metal  G smoothness  B wet  A AO  linear", 2D) = "white" {}

        [Header(Emission)]
        [Enum(None,0,Tube,1,Radio,2,Gauge,3,DestBlind,4)] _EmitMode ("Emission mode", Float) = 0
        _EmissionColor ("Emission colour  linear x gain (Vector: set with SetVector)", Vector) = (0, 0, 0, 1)
        [NoScaleOffset] _EmitTex ("Emission texture  RGB colour  A mask", 2D) = "white" {}
        _BugDots ("Tube  dead insect dots", Range(0, 1)) = 1

        [Header(Lights and fields)]
        _CausticsGain ("Caustics gain", Range(0, 2)) = 1
        _SliceGain ("Light band gain", Range(0, 2)) = 1
        _MirrorLineColor ("Mirror line fill  linear (Vector)", Vector) = (0.99, 1.12, 3.71, 1)
        _MirrorLineWidth ("Mirror line width m", Float) = 0.02
        _MirrorRimColor ("Mirror rim light colour 8000K linear (Vector)", Vector) = (0.77, 0.81, 1.0, 1)
        _WetSmooth ("Wet film smoothness below the sea level", Range(0, 1)) = 0.85
        _WetDarken ("Wet albedo multiplier  porous 0.6  non porous 1", Range(0, 1)) = 1
        _WoundGuard ("D-08 wound light limiter", Range(0, 1)) = 1
        _PurpleGuard ("D-21 band guard on added lights", Range(0, 1)) = 1

        [Header(Erosion  bible 4.8)]
        _ErodeEnable ("Erosion on", Float) = 1
        [Enum(Prose,0,Literal,1)] _ErodeForm ("Threshold form", Float) = 0
        _ErodeCoef ("Coefficients  height front skylight falloff m", Vector) = (0.45, 0.25, 0.35, 0.8)
        _ErodeNoise ("Noise  patch m  uniform lo  uniform hi  rim m", Vector) = (0.55, 0.30, 0.70, 0.03)
        _ErodeNoiseRange ("Noise range compared with tau", Vector) = (-0.20, 0.25, 0, 0)
        _FadeResist ("Resist  stanchions 0.3", Float) = 0
        _RimGain ("Rim  x CabinAmbient", Float) = 1.5
        _CabinBox ("Cabin box  floor y  crown y  rear z  front z", Vector) = (0.62, 2.62, -3.65, 3.50)
        _SkyRect ("Skylight  centre xyz  half", Vector) = (0.55, 2.62, 2.80, 0.30)
        _SeatSphere ("Local seat sphere  xyz  r", Vector) = (0.55, 1.05, 2.05, 0.9)
        _FloorPatch ("Floor patch  x0 x1 z0 z1", Vector) = (-0.16, 1.04, 0.85, 2.45)
        _HoleFull ("D-26 hole full  cx cz hx hz", Vector) = (0.55, 2.925, 0.45, 0.475)
        _HoleMin ("D-26 hole minimum  cx cz hx hz", Vector) = (0.55, 3.04, 0.30, 0.26)
        _HoleShape ("D-26 hole  corner  edge noise  max y", Vector) = (0.22, 0.10, 0.70, 0)
        _HoleOpen ("D-26 hole open  driver MPB", Range(0, 1)) = 0

        [Header(Fog)]
        _FogCap ("Fog cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog height scale m  0 none", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" }
        LOD 300

        CGPROGRAM
        #pragma surface surf Cabin vertex:vert finalcolor:CabinFinal nofog addshadow exclude_path:deferred exclude_path:prepass nolightmap nodynlightmap nodirlightmap nometa
        #pragma target 3.5
        #pragma multi_compile_fog
        #pragma skip_variants POINT_COOKIE DIRECTIONAL_COOKIE

        #include "UnityPBSLighting.cginc"
        #include "Assets/Lanbai/Cabin/Shaders/LanbaiCabinCommon.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiCaustics.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

        sampler2D _MainTex;
        fixed4 _Color;
        half _Glossiness, _Metallic;
        float4 _HeightSmooth;
        sampler2D _DetailNormal, _DetailMask;
        half _DetailNormalScale;
        float _DetailTile;
        float4 _MaskAlbedoMul, _MaskSmoothAdd;
        fixed4 _WearColor, _SunFadeColor, _CrackColor;
        half _WearSmooth, _WearAmount, _SunFadeSmooth, _SunFadeAmount, _CrackSmooth, _CrackAmount;
        half4 _GrimeColor;
        half _GrimeAmount, _GrimeAbsolute;
        float _UseTubeLM;
        sampler2D _CabinTubeLM;
        float4 _TubeLMConst;
        half _SHAmbientK, _CabinLight;
        float _UseAtlas;
        sampler2D _AtlasAlbedo, _AtlasMask;
        float _EmitMode;
        float4 _EmissionColor;
        sampler2D _EmitTex;
        half _BugDots;
        half _CausticsGain, _SliceGain;
        float4 _MirrorLineColor, _MirrorRimColor;
        float _MirrorLineWidth;
        half _WetSmooth, _WetDarken, _WoundGuard, _PurpleGuard, _RimGain;

        struct Input
        {
            float2 uv_MainTex;
            float4 cabinUV;          // xy uv0 (metres), zw uv1 (atlas)
            float4 color : COLOR;
            float3 worldPos;
            float3 worldNormal;
            INTERNAL_DATA
        };

        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            o.cabinUV = float4(v.texcoord.xy, v.texcoord1.xy);
        }

        // ---------------------------------------------------------------------------------- lighting
        inline half4 LightingCabin(SurfaceOutputStandard s, float3 viewDir, UnityGI gi)
        {
        #if defined(UNITY_PASS_FORWARDADD) && defined(DIRECTIONAL)
            // the only extra directional light in the film is the wound light on the cabin layer (GateLayout_v2
            // lights.tear, culling = bus layers): D-08 -> a cold white, C* <= 12, hue pulled out of 290-330
            gi.light.color = lerp(gi.light.color, LanbaiWoundLightLimit(gi.light.color), _WoundGuard);
        #endif
            return LightingStandard(s, viewDir, gi);
        }
        inline void LightingCabin_GI(SurfaceOutputStandard s, UnityGIInput data, inout UnityGI gi)
        {
            LightingStandard_GI(s, data, gi);
            // bible §4.8: the cabin's ambient is _Udon_CabinAmbient x AO (added as emission). Remove Unity's SH
            // ambient (Trilight + Not Important lights folded into SH); per-vertex lights (Shade4PointLights) stay.
            float3 sh = max(ShadeSH9(float4(s.Normal, 1.0)), 0.0);
            gi.indirect.diffuse = max(gi.indirect.diffuse - (1.0 - _SHAmbientK) * sh, 0.0);
        }

        // ---------------------------------------------------------------------------------- surface
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float3 P = IN.worldPos;
            float rim = LanbaiCabinErodeClipRim(P);                  // clip() first: nothing below runs for cut pixels

            float2 uv0 = IN.cabinUV.xy;
            float2 uvd = uv0 * _DetailTile;
            fixed4 tex = tex2D(_MainTex, IN.uv_MainTex);                 // surface shader already applies _MainTex_ST
            float3 albedo = _Color.rgb * tex.rgb;
            float smooth = _Glossiness;
            float metal = _Metallic;
            float occl = 1.0;
            [branch] if (_UseAtlas > 0.5)
            {   // exterior (Bus_Exterior_LOD0/1): albedo + R metal, G smoothness, B wet, A AO on uv1
                float4 am = tex2D(_AtlasMask, IN.cabinUV.zw);
                albedo *= tex2D(_AtlasAlbedo, IN.cabinUV.zw).rgb;
                metal = am.r;
                smooth = lerp(am.g, max(am.g, 0.85), am.b * saturate(_Udon_Wetness));   // bible 4.9 wet facades 0.85
                occl = am.a;
            }

            // detail mask: per-channel albedo multiplier and smoothness add (ceiling holes, floor studs / dirt / mottling)
            float3 m = tex2D(_DetailMask, uvd).rgb;
            albedo *= lerp(1.0, _MaskAlbedoMul.r, m.r) * lerp(1.0, _MaskAlbedoMul.g, m.g) * lerp(1.0, _MaskAlbedoMul.b, m.b);
            smooth += dot(m, _MaskSmoothAdd.rgb);

            // vertex colour: R grime (thirty years: yellowed ceiling round the tubes, dust in the window-frame corners and
            // sills, dirt where the floor meets the walls), G wear / polish, B sun fade (<= 0.75) and crack seeds (> 0.75)
            float grime = saturate(IN.color.r) * _GrimeAmount;
            albedo = lerp(albedo, _GrimeAbsolute > 0.5 ? _GrimeColor.rgb : albedo * _GrimeColor.rgb * 2.0, grime);
            smooth *= 1.0 - 0.5 * grime;
            float wear = saturate(IN.color.g) * _WearAmount;
            albedo = lerp(albedo, _WearColor.rgb, wear);
            smooth = lerp(smooth, _WearSmooth, wear);
            float b = saturate(IN.color.b);
            float sunFade = saturate(b / 0.75) * _SunFadeAmount;
            albedo = lerp(albedo, _SunFadeColor.rgb, sunFade);
            smooth = lerp(smooth, _SunFadeSmooth, sunFade);
            float seed = saturate((b - 0.75) / 0.25);
            float crackN = 1.0 - abs(LanbaiCabinFBM(P * 3.0, 0.08) * 2.0 - 1.0);            // ridged: thin lines
            float crack = smoothstep(1.0 - 0.12 * seed, 1.0 - 0.04 * seed, crackN) * step(0.001, seed) * _CrackAmount;
            albedo = lerp(albedo, _CrackColor.rgb, crack);
            smooth = lerp(smooth, _CrackSmooth, crack);

            // height band (stanchions: 0.80 at hand height 1.0-1.8 m above the floor)
            float hb = smoothstep(_HeightSmooth.x - 0.05, _HeightSmooth.x, P.y) * (1.0 - smoothstep(_HeightSmooth.y, _HeightSmooth.y + 0.05, P.y));
            smooth = lerp(smooth, _HeightSmooth.z, hb * _HeightSmooth.w);

            // wet below the sea level (act 6 entering the water, 7: the flooded cabin, dream logic) - Lagarde
            float below = (_Udon_SeaMode > 0.5 && _Udon_SeaMode < 2.5 && P.y < _Udon_SeaLevel) ? 1.0 : 0.0;
            float wet = max(below, saturate(_Udon_Underwater));
            albedo *= lerp(1.0, _WetDarken, wet);
            smooth = lerp(smooth, max(smooth, _WetSmooth), wet);

            // bleach (bible §4.8 step 1)
            float bleach = _Udon_CabinBleach.x;
            albedo = LanbaiCabinBleachAlbedo(albedo, bleach);
            smooth = LanbaiCabinBleachSmooth(smooth, bleach);

            // detail normal
            half3 nT = UnpackScaleNormal(tex2D(_DetailNormal, uvd), _DetailNormalScale);
            o.Normal = nT;
            float3 nWS = normalize(WorldNormalVector(IN, o.Normal));

            o.Albedo = albedo;
            o.Metallic = metal;
            o.Smoothness = saturate(smooth);
            o.Occlusion = occl;
            o.Alpha = 1.0;

        #if !defined(UNITY_PASS_FORWARDADD) && !defined(UNITY_PASS_SHADOWCASTER)
            // ---- the baked tube light and the cabin ambient (diffuse; metals get them through 1 - metallic)
            float4 lm = _UseTubeLM > 0.5 ? tex2D(_CabinTubeLM, IN.cabinUV.zw) : float4(_TubeLMConst.rgb, 1.0);
            float ao = _UseTubeLM > 0.5 ? lm.a : 1.0;
            float3 diffAlb = albedo * (1.0 - metal * 0.96) * _CabinLight;          // exterior: no cabin light terms
            float3 light = lm.rgb * max(_Udon_CabinLightmap, 0.0) + _Udon_CabinAmbient.rgb * ao;

            // ---- caustics (sea): up-facing from above, down-facing from below in 7c (the include reads .y)
            light += LanbaiCabinCaustics(P, nWS) * _CausticsGain * ao;

            // ---- 4c light bands crossing the cabin (Act04c_Inside 给总控 §3): soft front + exponential tail,
            //      w = coverage (lip 8 stays); w < 0 = retreat (lit where z > front, no tail)
            float3 sliceCol = _Udon_CabinSliceColor.rgb;
            [branch] if (dot(sliceCol, 1.0) > 0.0)
            {
                float soft = max(_Udon_CabinSlice.y, 0.05);
                float d = P.z - _Udon_CabinSlice.x;                              // > 0: already swept (bands move to -z)
                float edge = saturate(d / soft + 0.5);
                float tail = _Udon_CabinSlice.z > 0.0 ? exp(-max(d, 0.0) / _Udon_CabinSlice.z) : saturate(1.0 - max(d, 0.0) / soft);
                float lit = _Udon_CabinSlice.w < 0.0 ? edge : edge * lerp(tail, 1.0, saturate(_Udon_CabinSlice.w));
                // window-shaped weight (no cookie here): light enters through the side windows and the skylight,
                // so up-facing and side-facing surfaces take it, undersides do not
                float win = saturate(0.35 + 0.65 * max(nWS.y, abs(nWS.x)));
                light += sliceCol * lit * lerp(1.0, win, saturate(_Udon_CabinSliceColor.a)) * _SliceGain;
            }

            // ---- act 9 mirror rim light (8000 K, E at 1 m, inverse square inside 1 m clamped)
            [branch] if (_Udon_MirrorRimLight.w > 0.0)
            {
                float3 Lv = _Udon_MirrorRimLight.xyz - P;
                float dd = max(dot(Lv, Lv), 1.0);
                light += _MirrorRimColor.rgb * (_Udon_MirrorRimLight.w * saturate(dot(nWS, Lv * rsqrt(max(dot(Lv, Lv), 1e-6)))) / dd);
            }

            float3 emit = diffAlb * light;

            // ---- emission options
            float lmOn = max(_Udon_CabinLightmap, 0.0);
            [branch] if (_EmitMode > 0.5)
            {
                fixed4 et = tex2D(_EmitTex, uv0);
                if (_EmitMode < 1.5)
                {   // tube diffuser: #E7FEFF @ +1.03 (x T0 1.6) at lm 1; dead insects show only when lit
                    float bug = step(0.93, LanbaiHash13(floor(float3(uv0 * float2(9.0, 33.0), 3.0)))) * _BugDots;
                    emit += _EmissionColor.rgb * lmOn * (1.0 - 0.85 * bug);
                }
                else if (_EmitMode < 2.5)
                {   // radio dial: backlight mask = dial texture A (the face itself is the albedo map)
                    emit += _Udon_RadioDial.rgb * et.a;
                }
                else if (_EmitMode < 3.5)
                {   // gauges: faint teal #5FA89A x 0.3, no numerals
                    emit += _EmissionColor.rgb * et.a;
                }
                else
                {   // destination blind: letters (A) backlit by the tubes, #F2F5F0 x 2.5 at lm 1
                    emit += _EmissionColor.rgb * et.a * lmOn;
                }
            }

            // ---- act 9 mirror line: a 2 cm horizontal line at the mirror plane, sweeping up through the cabin
            [branch] if (_Udon_MirrorPlane.y > 0.0)
            {
                float dy = abs(P.y - _Udon_MirrorPlane.x);
                float aa = max(fwidth(P.y), 1e-4);
                float ln = saturate((_MirrorLineWidth * 0.5 - dy) / aa + 0.5);
                emit += _MirrorLineColor.rgb * ln * _Udon_MirrorPlane.y;
            }

            // ---- the erosion rim: the sky's own colour x 1.5, never orange
            emit += max(_Udon_CabinAmbient.rgb, 0.0) * _RimGain * rim;
            o.Emission = emit;
        #endif
        }

        void CabinFinal(Input IN, SurfaceOutputStandard o, inout fixed4 color)
        {
        #ifdef UNITY_PASS_FORWARDADD
            // D-21 band guard on what the added lights put on the cabin (only h 290-330, C* > 8, L* > 40)
            color.rgb = lerp(color.rgb, LanbaiPurpleGuardLin(color.rgb), _PurpleGuard);
            color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);
        #else
            color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
        #endif
        }
        ENDCG
    }
    FallBack Off
}
