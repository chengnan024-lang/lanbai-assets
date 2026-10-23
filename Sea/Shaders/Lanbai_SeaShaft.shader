// =====================================================================================================
//  Lanbai/SeaShaft   蓝白 · underwater light shafts (bible §6·7a 大气: 光柱 ≤ 16 张, 1–4 m 宽, 20–40 m 长, 动态条纹,
//                    屏幕 #90BFE9 填 #8AB2FF @ +1.30, α 0.04–0.08, 侧视淡出, 25 m 深处消失; F4p 汇成一束; F3e1 最后一道)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//
//  MESH CONTRACT (the Act07 builder generates it from Act07_Layout.json 'shafts'): every shaft = one quad, 4 vertices
//    POSITION  the shaft's centre point (object space; the object sits at the bus origin)
//    NORMAL    the shaft's axis (unit, pointing DOWN along the light)
//    UV0       corner: x = -1 / +1 across, y = 0 (top) .. 1 (bottom)
//    UV1       x = half width m, y = length m, z = seed 0..1, w = alpha 0.04..0.08
//  The quad turns around its own axis to face the CENTRE eye (cylindrical billboard: same in both eyes).
//  Gather (F4p): every centre slides toward _GatherPoint (object space) by _Gather 0..1, keeping its own small offset.
//  BOUNDS: the builder sets the mesh bounds to enclose the full shafts (and the gather point), not just the centres.
//  Additive (One One). No depth write. Fogged like the water (its light is scattered by the same water).
// =====================================================================================================
Shader "Lanbai/SeaShaft"
{
    Properties
    {
        _Color ("Colour linear  fill 8AB2FF at +1.30", Vector) = (0.630, 1.096, 2.462, 0)
        _Gain ("Gain  driver  depth fade and the beats", Range(0, 2)) = 1
        [NoScaleOffset] _Streaks ("Streaks", 2D) = "white" {}
        _StreakScroll ("Streak drift per s  x coarse  y fine", Vector) = (0.020, -0.035, 0, 0)
        _EdgeOnPower ("Edge-on fade power", Range(0.5, 4)) = 1.5
        _NearFade ("Near fade m  x start  y full", Vector) = (0.3, 1.0, 0, 0)
        _GatherPoint ("Gather point  object space", Vector) = (0, 3.2, 0.5, 0)
        _Gather ("Gather 0..1  F4p", Range(0, 1)) = 0
        _FogKeep ("How much of the shaft survives the water fog", Range(0, 1)) = 0.6
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-15" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            float4 _Color, _StreakScroll, _NearFade, _GatherPoint;
            float _Gain, _EdgeOnPower, _Gather, _FogKeep;
            sampler2D _Streaks;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 p : TEXCOORD1;          // x seed, y alpha, z edge-on fade, w length
                float3 posWS : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 c = v.vertex.xyz;
                float3 g = _GatherPoint.xyz + (c - _GatherPoint.xyz) * 0.12;          // keep a little of the spread
                c = lerp(c, g, _Gather);
                float3 cW = mul(unity_ObjectToWorld, float4(c, 1.0)).xyz;
                float3 axis = normalize(mul((float3x3)unity_ObjectToWorld, v.normal));
                float3 toEye = LanbaiCentreEyePos() - cW;
                float3 side = cross(axis, toEye);
                float sl = length(side);
                side = sl > 1e-4 ? side / sl : float3(1.0, 0.0, 0.0);
                float3 P = cW + axis * ((v.uv0.y - 0.5) * v.uv1.y) + side * (v.uv0.x * v.uv1.x);
                o.posWS = P;
                o.pos = UnityWorldToClipPos(P);
                o.uv = v.uv0;
                // looking straight along the axis the quad degenerates: fade it (sin of the angle between eye ray and axis)
                float s = length(cross(axis, normalize(toEye)));
                o.p = float4(v.uv1.z, v.uv1.w, pow(saturate(s * 1.25), _EdgeOnPower), v.uv1.y);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float t = _Udon_SeaClock.w > 0.0 ? _Udon_SeaClock.x : _Time.y;
                float across = i.uv.x;                                     // -1 .. 1
                float prof = (1.0 - across * across);
                prof *= prof;                                              // soft edges, no hard line
                float along = i.uv.y;
                float ends = smoothstep(0.0, 0.18, along) * (1.0 - smoothstep(0.55, 1.0, along));   // fades into the deep
                float2 su = float2(across * 0.5 + 0.5 + i.p.x * 7.13, along * 0.15);
                float st = tex2D(_Streaks, su + float2(_StreakScroll.x * t, 0.0)).r * 0.7
                         + tex2D(_Streaks, su * float2(1.7, 1.0) + float2(_StreakScroll.y * t, 0.0)).g * 0.6;
                float a = i.p.y * prof * ends * (0.35 + st) * i.p.z * _Gain;
                a *= LanbaiNearFade(i.posWS, _NearFade.x, _NearFade.y);
                float fogA = LanbaiFogAmount(i.posWS, LanbaiCentreEyePos());
                a *= lerp(1.0, 1.0 - fogA, _FogKeep);
                return float4(_Color.rgb * a, 0.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
