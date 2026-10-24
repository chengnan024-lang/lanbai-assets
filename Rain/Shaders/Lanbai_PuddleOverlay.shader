// =====================================================================================================
//  Lanbai / PuddleOverlay        蓝白 · the water SURFACE over a stencil-mirror puddle (bible §1.6, §5.5, §6·12)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  The four hero puddles show the sign, the pole, the lamp housing and the notice case as MIRRORED COPIES drawn
//  through a stencil window (Lanbai/StencilWindow + Lanbai/MirrorCopy; README §2.4). This overlay is the water itself,
//  drawn AFTER them on the same outline mesh at the water level, premultiplied: out = src.rgb + dst * (1 - src.a).
//    calm water   keeps R(theta) of the mirror: _MirrorReflectance head-on, Schlick to 1 at grazing (a dark mirror:
//                 physical water is 2 %, but the bible's still puddle doubles the sign: '成双的「蓝白」站牌');
//                 the TUBE is not a copy: its image is the analytic lamp at the same reflectance, its core held at
//                 the bible's screen target (§6·12 '静水里的灯影 #DDE8EA' -> 1.45 linear max channel under S12);
//    broken water where a ring passes (slope >= _BreakSlope) the crisp mirror is REPLACED by the cube + the analytic
//                 lamps along the rippled normal - the image breaks into facets, each capped at the still image's
//                 core, so disturbed water is dimmer and scattered, never brighter - and comes back as the ring
//                 decays (tau 0.7 s): "倒影每次都在 2.5 秒内完全复原" (§5.5).
//  Writes depth (the stencil window pushed it to the far plane for the copies) so later transparents are occluded
//  correctly, and clears stencil bit 128.
//  v2: stereo eye index (M8), reflectance tuned to the target (M1), rings anchored to R_Stop, band-limited rings,
//  spec AA, colours as picked (sRGB).
// =====================================================================================================
Shader "Lanbai/PuddleOverlay"
{
    Properties
    {
        _BottomColour ("What lies under the water, lit (sRGB as picked; wet asphalt x0.25 in the lamp pool ~ #1D1D1D)", Color) = (0.11, 0.11, 0.11, 1)
        _MirrorReflectance ("Still-water reflectance head-on (Schlick to 1 at grazing; = WetSurface _PuddleMirror)", Range(0.02, 0.6)) = 0.30
        _LampPeak ("Lamp image core in still water (max channel, linear; bible #DDE8EA -> 1.45)", Range(0.2, 4)) = 1.45
        _BreakSlope ("Slope at which the mirror is fully broken", Range(0.005, 0.2)) = 0.04
        _RainRings ("Rain rings too (scene 1 = 1; scene 12 = 0, only drips)", Range(0, 1)) = 1
        [Toggle(_RIPPLE_FLIPBOOK)] _RippleFlipbook ("Rain rings from the denser flipbook (off = procedural, the bible's 3-5 / m^2 / s)", Float) = 0
        _RippleTex ("RainRipple_Flip8x8 (Texture2DArray)", 2DArray) = "" {}
        _RippleStrength ("Rain ring strength", Range(0, 3)) = 1
        _RippleRingLUT ("RippleRing_LUT_256x128 (linear)", 2D) = "gray" {}
        _RippleDensity ("Procedural density (rings / m^2 / s; bible 3-5)", Range(0, 4.4)) = 4
        _DripRippleLUT ("DripRipple_LUT_512x256 (linear)", 2D) = "gray" {}
        _DripStrength ("Drip ring strength", Range(0, 3)) = 1
        _AnchorToStop ("Rings move with R_Stop (1 for the hero puddles)", Range(0, 1)) = 1
        _LampSpecular ("Analytic lamps in the water (1)", Range(0, 2)) = 1
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-20" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One OneMinusSrcAlpha
        ZWrite On
        Offset -1, -1
        Stencil { Ref 0 WriteMask 128 Comp Always Pass Zero }

        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma require 2darray
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma shader_feature_local _RIPPLE_FLIPBOOK
            #include "UnityCG.cginc"
            #include "LanbaiRain.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            half4 _BottomColour;
            float _MirrorReflectance, _LampPeak, _BreakSlope, _RainRings, _RippleStrength, _DripStrength, _LampSpecular, _RippleDensity, _AnchorToStop;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                UNITY_FOG_COORDS(1)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // SPS-I: _WorldSpaceCameraPos is per eye only after this
                float3 P = i.wpos;
                float t = _Time.y;
                float3 Pl = LanbaiStopLocal(P, _AnchorToStop);
                float bl = LanbaiRingBand(LanbaiFootprint(P));
                float2 s = LanbaiDripRipples(Pl, t, bl) * _DripStrength;
                #if defined(_RIPPLE_FLIPBOOK)
                    s += LanbaiRippleFlipbook(Pl.xz, t, 0.6) * (_RippleStrength * _Udon_RainFall * _RainRings);
                #else
                    s += LanbaiRippleCells(Pl.xz, t, _RippleDensity * _Udon_RainFall * _RainRings, bl) * _RippleStrength;
                #endif
                float3 Nup = float3(0, 1, 0);
                float3 N = normalize(float3(-s.x, 1.0, -s.y));
                float3 V = normalize(_WorldSpaceCameraPos - P);
                float smooth = LanbaiSpecAA(N, 0.97);
                float cosV = saturate(dot(Nup, V));
                float cosR = saturate(dot(N, V));
                float fC = pow(1.0 - cosV, 5.0), fR = pow(1.0 - cosR, 5.0);
                float Rcalm = _MirrorReflectance + (1.0 - _MirrorReflectance) * fC;
                float Rrip = _MirrorReflectance + (1.0 - _MirrorReflectance) * fR;
                float brk = saturate(length(s) / _BreakSlope);
                // calm: keep Rcalm of the mirrored copies; broken: hide them, draw the rippled reflection instead
                float keepMirror = Rcalm * (1.0 - brk);
                float3 R = reflect(-V, N);
                // the analytic lamps (the tube's image): calm and rippled share one cap - the still image's core
                float3 lampCalm = LanbaiLampSpecularCapped(P, Nup, V, 0.97, 0.02, Rcalm / (0.02 + 0.98 * fC), _LampPeak);
                float3 lampRip = LanbaiLampSpecularCapped(P, N, V, smooth, 0.02, Rrip / (0.02 + 0.98 * fR), _LampPeak);
                float3 lamp = lerp(lampCalm, lampRip, brk) * _LampSpecular;
                float3 broken = LanbaiReflCube(R, 0.0) * (Rrip * 0.8 * brk);
                float3 under = _BottomColour.rgb * (1.0 - lerp(Rcalm, Rrip, brk));
                fixed4 c = fixed4(broken + lamp + under, 1.0 - keepMirror);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(unity_FogColor.rgb * c.a, c.a));
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
