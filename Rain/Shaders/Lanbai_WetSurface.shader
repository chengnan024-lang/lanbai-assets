// =====================================================================================================
//  Lanbai / WetSurface        蓝白 · wet asphalt, puddles, the dry rectangle under the bus (bible §1.6, §6·1, §6·2, §4.9)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3 (Built-in RP), look at it in a headset with one eye closed, then the other. !!!
//
//  Standard surface shader (lightmaps, probes, fog, shadows for free) + Lagarde wetness:
//    film      albedo x _Porosity (asphalt 0.5), smoothness lerp(dry, 0.74..0.84 by mask G), normal x0.6
//    puddles   albedo x0.25 of dry, smoothness 0.97, asphalt normal x0.05 + rain rings + drip rings,
//              a still-water mirror of the probe at _PuddleMirror, the analytic lamps' image at the bible's target
//    shelter   (mask B, under the parked bus) damp: albedo x0.8, smoothness 0.45
//    paint     (mask A) worn white lines: linear 0.45, wet smoothness 0.70
//  + the 8 analytic lamps' GGX specular (LanbaiLamps.cginc) added as emission: the long light bands.
//  Wet masks (README_Rain.md §4): _WetMaskMode 1 = R_Stop (Stop_WetMask inside its 48 x 12 m rect, Road_WetMask
//  continuing seamlessly outside), 2 = R_Road modules (Road_WetMask by mesh UV2 = metres along / across the road),
//  0 = off (_WetMaskDefault). No shader keywords for the default path (scripted materials just work).
// =====================================================================================================
Shader "Lanbai/WetSurface"
{
    Properties
    {
        [Header(Base (dry) material  e.g. Poly Haven asphalt 2K  3 m per tile)]
        _MainTex ("Albedo (sRGB)", 2D) = "white" {}
        _Color ("Albedo tint", Color) = (1, 1, 1, 1)
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _BumpScale ("Normal strength (dry)", Range(0, 2)) = 1
        _RoughnessMap ("Roughness (linear, R)", 2D) = "white" {}
        _UseRoughnessMap ("Use roughness map (0 = use Smoothness)", Range(0, 1)) = 0
        _Smoothness ("Dry smoothness (asphalt 0.15-0.25)", Range(0, 1)) = 0.2
        _HeightMap ("Height (linear, R) - puddle shorelines follow it", 2D) = "gray" {}
        _OcclusionMap ("Occlusion (linear, R)", 2D) = "white" {}

        [Header(Wetness  Lagarde)]
        _WetnessOverride ("Wetness override (-1 = use _Udon_Wetness)", Range(-1, 1)) = -1
        _Porosity ("Porous albedo multiplier when soaked (asphalt 0.5, concrete 0.55, wood 0.6, soil 0.55)", Range(0.2, 1)) = 0.5
        _FilmSmoothMin ("Film smoothness at mask G = 0", Range(0, 1)) = 0.74
        _FilmSmoothMax ("Film smoothness at mask G = 1", Range(0, 1)) = 0.84
        _WetNormalMul ("Normal strength under the film", Range(0, 1)) = 0.6
        _DryBias ("Drying order (crown dries first): wLocal = 1 - (1 - wet) * DryBias * (1 - G)", Range(0, 6)) = 3.5

        [Header(Wet masks  R puddle depth  G film retention  B shelter  A paint)]
        [Enum(Off, 0, Stop, 1, Road, 2)] _WetMaskMode ("Wet mask: Off / Stop (R_Stop) / Road (R_Road modules, UV2)", Float) = 1
        _WetMask ("Stop_WetMask_2048x512 (linear, Clamp)", 2D) = "black" {}
        _RoadMask ("Road_WetMask_2048x512 (linear, Repeat U / Clamp V)", 2D) = "black" {}
        _StopOrigin ("R_Stop origin at home: world xyz, w = yaw of R_Stop (deg)", Vector) = (0, 0, 0, 0)
        _WetMaskDefault ("Mask value when Off (R,G,B,A); footing top pool (0.3, 0.9, 0, 0)", Vector) = (0, 0.5, 0, 0)
        _AnchorToStop ("Rings and drips move with R_Stop (1 for R_Stop surfaces)", Range(0, 1)) = 1

        [Header(Puddles)]
        _PuddleAlbedoMul ("Puddle albedo x dry", Range(0, 1)) = 0.25
        _PuddleSmoothness ("Puddle smoothness", Range(0.8, 1)) = 0.97
        _PuddleNormalMul ("Asphalt normal left under water", Range(0, 0.3)) = 0.05
        _PuddleEdge ("Shoreline softness", Range(0.005, 0.2)) = 0.05
        _PuddleDetail ("Shoreline follows the height map", Range(0, 1)) = 0.5
        _PuddleMirror ("Still-water reflectance seen head-on (Schlick to 1 at grazing; = PuddleOverlay)", Range(0, 0.6)) = 0.30
        _LampPeak ("Still-water lamp image core (max channel, linear; bible #DDE8EA -> 1.45)", Range(0.2, 4)) = 1.45

        [Header(Shelter and paint)]
        _ShelterAlbedoMul ("Under the bus: albedo x", Range(0.5, 1)) = 0.8
        _ShelterSmooth ("Under the bus: smoothness", Range(0, 1)) = 0.45
        _PaintColor ("Paint albedo (sRGB 0.70 = linear 0.45)", Color) = (0.70, 0.70, 0.69, 1)
        _PaintSmoothWet ("Paint smoothness when wet", Range(0, 1)) = 0.70

        [Header(Rain rings)]
        [Toggle(_RIPPLE_FLIPBOOK)] _RippleFlipbook ("Use the denser RainRipple flipbook (~20 / m^2 / s) instead of the procedural rings", Float) = 0
        _RippleTex ("RainRipple_Flip8x8 as Texture2DArray (64 slices)", 2DArray) = "" {}
        _RippleStrength ("Ring strength (1 = physical)", Range(0, 3)) = 1
        _RippleLayer2 ("Flipbook second layer (density x(1+this))", Range(0, 1)) = 0.6
        _RippleRingLUT ("RippleRing_LUT_256x128 (linear)", 2D) = "gray" {}
        _RippleDensity ("Procedural density (rings / m^2 / s; bible 3-5)", Range(0, 4.4)) = 4
        _DripRippleLUT ("DripRipple_LUT_512x256 (linear)", 2D) = "gray" {}
        _DripStrength ("Drip ring strength", Range(0, 3)) = 1
        _DripOnFilm ("Drip ring on film (not puddle)", Range(0, 1)) = 0.3

        [Header(Analytic lamps)]
        _LampSpecular ("Lamp specular gain (keep 1; stencil-window puddles are covered by PuddleOverlay)", Range(0, 2)) = 1
        _DryLampFloor ("Lamp specular left on a DRY surface (0 for R_Road: scene 11 has no light bands)", Range(0, 0.3)) = 0.15
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        LOD 300

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows vertex:vert
        #pragma target 3.5
        #pragma require 2darray
        #pragma shader_feature_local _RIPPLE_FLIPBOOK

        #include "LanbaiRain.cginc"
        #include "LanbaiVR.cginc"

        sampler2D _MainTex, _BumpMap, _RoughnessMap, _HeightMap, _OcclusionMap, _WetMask, _RoadMask;
        half4 _Color, _PaintColor;
        half _BumpScale, _UseRoughnessMap, _Smoothness;
        half _WetnessOverride, _Porosity, _FilmSmoothMin, _FilmSmoothMax, _WetNormalMul, _DryBias;
        float4 _StopOrigin, _WetMaskDefault;
        float _WetMaskMode, _AnchorToStop;
        half _PuddleAlbedoMul, _PuddleSmoothness, _PuddleNormalMul, _PuddleEdge, _PuddleDetail, _PuddleMirror, _LampPeak;
        half _ShelterAlbedoMul, _ShelterSmooth, _PaintSmoothWet;
        half _RippleStrength, _RippleLayer2, _RippleDensity, _DripStrength, _DripOnFilm, _LampSpecular, _DryLampFloor;
        float _Udon_RainFall;        // 0..1 rain still FALLING (scene 1: 1, scene 12: 0 -> only drips ring)

        struct Input
        {
            float2 uv_MainTex;
            float3 worldPos;
            float3 worldNormal;
            float2 roadUV;           // mesh UV2 (Unity uv3 / TEXCOORD2): metres along the road, metres across (= X_u)
            INTERNAL_DATA
        };

        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            o.roadUV = v.texcoord2.xy;
        }

        // world -> R_Stop local (X across, + = door side; Z along, + = bus heading) at its home position
        inline float2 StopLocalXZ(float3 P)
        {
            float3 q = P - _Udon_StopOffset.xyz - _StopOrigin.xyz;
            float yaw = radians(_StopOrigin.w);
            float s = sin(yaw), c = cos(yaw);
            return float2(c * q.x - s * q.z, s * q.x + c * q.z);
        }

        // reflection probe 0 along R, box-projected when the probe has a box (the stop's 512 probe does)
        inline float3 ProbeRefl(float3 R, float3 P, float mip)
        {
            float3 dir = R;
            if (unity_SpecCube0_ProbePosition.w > 0.0)
            {
                float3 rbmax = (unity_SpecCube0_BoxMax.xyz - P) / R;
                float3 rbmin = (unity_SpecCube0_BoxMin.xyz - P) / R;
                float3 rb = lerp(rbmin, rbmax, step(0.0, R));
                float fa = min(min(rb.x, rb.y), rb.z);
                dir = P + R * fa - unity_SpecCube0_ProbePosition.xyz;
            }
            return DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(unity_SpecCube0, dir, mip), unity_SpecCube0_HDR);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float3 P = IN.worldPos;
            float t = _Time.y;

            // ---- dry base
            half3 albDry = tex2D(_MainTex, IN.uv_MainTex).rgb * _Color.rgb;
            half3 nBase = UnpackScaleNormal(tex2D(_BumpMap, IN.uv_MainTex), _BumpScale);
            half sDry = lerp(_Smoothness, 1.0 - tex2D(_RoughnessMap, IN.uv_MainTex).r, _UseRoughnessMap);
            half hgt = tex2D(_HeightMap, IN.uv_MainTex).r;
            half ao = tex2D(_OcclusionMap, IN.uv_MainTex).r;

            // ---- mask (explicit gradients: no implicit-derivative sample inside the mode branches)
            float2 lxz = StopLocalXZ(P);
            float2 suv = float2((lxz.y + 22.0) / 48.0, (5.0 - lxz.x) / 12.0);
            float2 ruvS = float2((lxz.y + 21.0) / 60.0, (5.0 - lxz.x) / 12.0);           // road mask around the stop
            float2 ruvR = float2(IN.roadUV.x / 60.0, (5.0 - IN.roadUV.y) / 12.0);        // road mask on R_Road
            float2 dsx = ddx(suv), dsy = ddy(suv), drsx = ddx(ruvS), drsy = ddy(ruvS), drrx = ddx(ruvR), drry = ddy(ruvR);
            float4 m = _WetMaskDefault;
            if (_WetMaskMode > 1.5)
                m = tex2Dgrad(_RoadMask, ruvR, drrx, drry);
            else if (_WetMaskMode > 0.5)
            {
                if (suv.x >= 0.0 && suv.x <= 1.0 && suv.y >= 0.0 && suv.y <= 1.0)
                    m = tex2Dgrad(_WetMask, suv, dsx, dsy);
                else if (suv.y >= 0.0 && suv.y <= 1.0)
                    m = tex2Dgrad(_RoadMask, ruvS, drsx, drsy);                         // the road goes on
            }

            // ---- wetness
            float wet = _WetnessOverride >= 0.0 ? _WetnessOverride : _Udon_Wetness;
            float wLocal = saturate(1.0 - (1.0 - wet) * _DryBias * (1.0 - m.g));
            float shelter = m.b;
            float wFilm = wLocal * (1.0 - shelter);

            // world -> tangent basis of this pixel (surface-shader INTERNAL_DATA rows)
            float3 T = normalize(float3(IN.internalSurfaceTtoW0.x, IN.internalSurfaceTtoW1.x, IN.internalSurfaceTtoW2.x));
            float3 B = normalize(float3(IN.internalSurfaceTtoW0.y, IN.internalSurfaceTtoW1.y, IN.internalSurfaceTtoW2.y));
            float3 Ng = normalize(float3(IN.internalSurfaceTtoW0.z, IN.internalSurfaceTtoW1.z, IN.internalSurfaceTtoW2.z));

            // puddles: stored depth (R = sqrt(depth / 8 mm)); the water level drops as the road dries; only on
            // surfaces facing up (a footing's sides never 'hold' water)
            float depthN = m.r * m.r;
            float level = (1.0 - wet) * 0.45;
            float shore = depthN + (hgt - 0.5) * _PuddleDetail * 0.12 - level;
            float puddle = smoothstep(0.0, _PuddleEdge, shore) * step(0.004, m.r) * (1.0 - shelter) * step(0.01, wet)
                         * smoothstep(0.85, 0.97, Ng.y);

            // ---- film / shelter / paint
            float3 albedo = albDry * lerp(lerp(1.0, _Porosity, wFilm), lerp(1.0, _ShelterAlbedoMul, wet), shelter);
            float filmS = lerp(_FilmSmoothMin, _FilmSmoothMax, m.g);
            float smooth = lerp(lerp(sDry, max(sDry, filmS), wFilm), lerp(sDry, _ShelterSmooth, wet), shelter);
            half3 nFilm = normalize(half3(nBase.xy * lerp(1.0, _WetNormalMul, wFilm), nBase.z));
            albedo = lerp(albedo, _PaintColor.rgb, m.a);
            smooth = lerp(smooth, lerp(0.35, _PaintSmoothWet, wFilm), m.a);

            // ---- rings (slopes in the surface's own frame: R_Stop-local world XZ, or road metres on R_Road)
            float3 Pl = LanbaiStopLocal(P, _AnchorToStop);
            float2 pr = _WetMaskMode > 1.5 ? float2(IN.roadUV.y, IN.roadUV.x) : Pl.xz;
            float bl = LanbaiRingBand(LanbaiFootprint(P));
            #if defined(_RIPPLE_FLIPBOOK)
                float2 rs = LanbaiRippleFlipbook(pr, t, _RippleLayer2) * _Udon_RainFall;
            #else
                float2 rs = LanbaiRippleCells(pr, t, _RippleDensity * _Udon_RainFall, bl);
            #endif
            rs *= _RippleStrength;
            float2 ds = LanbaiDripRipples(Pl, t, bl) * _DripStrength * lerp(_DripOnFilm * wFilm, 1.0, puddle);

            float2 sPud = rs * puddle + ds;                        // rings on the water
            float3 dW = float3(-sPud.x, 0.0, -sPud.y);             // perturbation of an up-facing normal
            float2 ringTs = float2(dot(dW, T), dot(dW, B));

            half3 nPud = normalize(half3(nBase.xy * _PuddleNormalMul + ringTs, 1.0));
            half3 nFilmR = normalize(half3(nFilm.xy + ringTs * (1.0 - puddle), nFilm.z));
            o.Normal = normalize(lerp(nFilmR, nPud, puddle));

            albedo = lerp(albedo, albDry * _PuddleAlbedoMul, puddle);
            smooth = lerp(smooth, _PuddleSmoothness, puddle);

            // ---- specular anti-aliasing (VR) on the final world normal
            float3 Nw = normalize(T * o.Normal.x + B * o.Normal.y + Ng * o.Normal.z);
            smooth = LanbaiSpecAA(Nw, smooth);

            o.Albedo = albedo;
            o.Metallic = 0;
            o.Smoothness = smooth;
            o.Occlusion = ao;

            #if !defined(UNITY_PASS_META)
            // ---- analytic lamps: the long bands on the wet film (physical); in still water the lamps' image at the
            //      same effective reflectance as the mirror, its core at the bible's target, never brighter rippled
            float3 V = normalize(_WorldSpaceCameraPos - P);
            float NdotV = saturate(dot(Nw, V));
            float fres = pow(1.0 - NdotV, 5.0);
            float Fphys = 0.02 + 0.98 * fres;
            float Rmir = _PuddleMirror + (1.0 - _PuddleMirror) * fres;
            float3 F0 = lerp(0.04, 0.02, puddle);
            float boost = lerp(1.0, Rmir / Fphys, puddle);
            float peak = lerp(1e9, _LampPeak, puddle);
            float3 lamp = LanbaiLampSpecularCapped(P, Nw, V, smooth, F0, boost, peak);
            o.Emission = lamp * _LampSpecular * lerp(1.0, ao, 0.5) * saturate(wet * 2.0 + _DryLampFloor);
            // ---- still water as a dark mirror (bible §6·12 '成双的站牌'): the probe at Rmir instead of ~2 %
            float3 Rv = reflect(-V, Nw);
            float pr2 = 1.0 - smooth;
            o.Emission += ProbeRefl(Rv, P, pr2 * (1.7 - 0.7 * pr2) * 6.0) * (max(Rmir - Fphys, 0.0) * puddle * ao);
            #endif
        }
        ENDCG
    }
    FallBack "Standard"
}
