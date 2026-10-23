// =====================================================================================================
//  Lanbai / StarPoints   v1 (2026-10-23, cloud sub-session "天空")    蓝白 · 真实星表的星（高斯精灵）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only. !!!
//
//  ART BIBLE v2.1 §6·9: stars are geometry, not texture. One mesh (built by 蓝白/Sky/Build Star Mesh from
//  Sky/Data/StarPoints_BSC5.csv), 4 vertices per star:
//     vertex.xyz = the star's Unity-world unit direction (the object transform is ignored: stars are at infinity,
//                  fixed in the earth frame, never rotate), uv0.xy = quad corner (-1..1),
//     uv1 = (V magnitude, rank (0 = brightest), order 0..1 (for scripted appear / fade orders), 0),
//     colour = linear rgb, luminance 1 (B-V blackbody, 45 % toward white).
//  Each star is a Gaussian of constant FWHM in PIXELS (>= 1.4 px; default 1.6), so it neither shimmers nor grows with
//  resolution; it never twinkles. Brightness = _StarScale x 10^(-0.4 _MagSlope (m - _MagRef)) x gain, the brightest
//  _BrightCount ranks x _BrightBoost, blended over 20 ranks so a growing count never steps a star (bible: the
//  brightest 50 x4 at ignition; 200 x4 -> x8 toward the white).
//  Sky objects take no fog (_FogMode 2). Positioned from the centre eye (both eyes see the same star).
//  Global _Udon_StarGain (w > 0): x multiplies everything (at F13 it jumps 0 -> 1 in one frame, bible E18); y = the
//  bright-rank boost and z = how many ranks (bible: 50 x4 at ignition, 200 x4 -> x8 on the x^2.5 curve to the white).
// =====================================================================================================
Shader "Lanbai/StarPoints"
{
    Properties
    {
        _StarScale ("Star scale at the reference magnitude (linear peak)", Float) = 1.6
        _MagRef ("Reference magnitude", Float) = 0
        _MagSlope ("Magnitude slope (1 = physical; < 1 compresses)", Range(0.2, 1)) = 0.5
        _MagFloor ("Faintest magnitude drawn", Float) = 6.5
        _FWHM ("FWHM px (>= 1.4)", Range(1.4, 4)) = 1.6
        _BrightCount ("Bright ranks boosted (count)", Float) = 50
        _BrightBoost ("Boost of the bright ranks", Float) = 4
        _Gain ("Gain (global _Udon_StarGain.x wins when Use Global Gain is 1)", Float) = 1
        _UseGlobalGain ("Use Global Gain (0 = this material only, e.g. the first stars of act 8b)", Float) = 1
        _OrderFade ("Order fade  x threshold  y soft  z 1 = stars with order below x are OFF  0 = ON", Vector) = (0, 0.02, 0, 0)
        _Distance ("Draw distance m (inside the far clip 45 km)", Float) = 40000
        _Tint ("Tint, linear", Vector) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-400" "RenderType" = "Transparent" "IgnoreProjector" = "True" "PreviewType" = "Plane" }
        Blend One One
        ZWrite Off
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            float _StarScale, _MagRef, _MagSlope, _MagFloor, _FWHM, _BrightCount, _BrightBoost, _Gain, _Distance, _UseGlobalGain;
            float4 _OrderFade, _Tint;
            #ifndef LANBAI_DECL__Udon_StarGain
            #define LANBAI_DECL__Udon_StarGain
            float4 _Udon_StarGain;     // x = gain, y = bright-rank boost (> 0 = set), z = bright-rank count (> 0 = set); w > 0 = set
            #endif

            struct appdata
            {
                float4 vertex : POSITION;
                float4 color : COLOR;
                float2 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 q : TEXCOORD0;          // corner in units of FWHM-pixels
                float3 col : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 D = normalize(v.vertex.xyz);
                float3 eye = LanbaiCentreEyePos();
                float3 C = eye + D * _Distance;
                float3 R = normalize(cross(abs(D.y) < 0.99 ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0), D));
                float3 U = cross(D, R);
                float halfPx = 2.0 * _FWHM;                                    // quad half size: 2 FWHM
                float h = halfPx * LanbaiPixelAngle() * _Distance;
                float3 P = C + (R * v.uv0.x + U * v.uv0.y) * h;
                o.pos = UnityWorldToClipPos(P);
                o.q = v.uv0 * halfPx / _FWHM;                                  // distance from the centre in FWHMs
                float m = v.uv1.x;
                float flux = _StarScale * exp2(-1.3287712 * _MagSlope * (m - _MagRef));   // 10^(-0.4 s dm) = 2^(-1.3288 s dm)
                bool useG = (_UseGlobalGain > 0.5) && (_Udon_StarGain.w > 0.0);
                float boost = (useG && _Udon_StarGain.y > 0.0) ? _Udon_StarGain.y : _BrightBoost;
                float count = (useG && _Udon_StarGain.z > 0.0) ? _Udon_StarGain.z : _BrightCount;
                flux *= lerp(1.0, boost, saturate((count - v.uv1.y) / 20.0));   // ranks fade in over 20: no star jumps x4
                flux *= (m <= _MagFloor) ? 1.0 : 0.0;
                float g = useG ? _Udon_StarGain.x : _Gain;
                float ord = smoothstep(_OrderFade.x - _OrderFade.y, _OrderFade.x + _OrderFade.y, v.uv1.z);
                float vis = (_OrderFade.z > 0.5) ? ord : 1.0;
                o.col = v.color.rgb * _Tint.rgb * (flux * g * vis);
                if (flux * g * vis <= 0.0)
                    o.pos = float4(0.0, 0.0, -1.0, 1.0);                       // degenerate: culled
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float r2 = dot(i.q, i.q);
                float k = exp(-2.7725887 * r2);                                // exp(-4 ln2 r^2), r in FWHMs
                return half4(i.col * k, 0.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
