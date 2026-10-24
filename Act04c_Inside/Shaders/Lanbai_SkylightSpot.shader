// =====================================================================================================================
//  Lanbai / SkylightSpot     蓝白 · 第 4 幕（U8 → U9）：裂口的光从天窗落到过道上的一块光斑、光柱、光柱里的尘
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; slang syntax check only). Compile in Unity 2022.3 + VRChat SDK. !!!
//
//  Bible §4.8 + Gate/GateLayout_v2.json skylight_spot (the gate's final look). The light has no shadows, so the spot is
//  a card: the skylight's four corners are projected along (corner - tear core) onto the floor (y = 0.623). Everything
//  is computed HERE in the vertex stage from the gate's own globals, so no Udon mesh editing is needed:
//      core = _Udon_TearPos.xyz + _CoreOfs.xyz * (_Udon_TearH.x / 1000)      (checked against the gate's 25 samples:
//                                                                               worst corner 0.5 mm, Tools~/skylight_check.py)
//  Parts (material keyword): SPOT (a 4-vertex quad, uv = which corner), BEAM (4 side quads of the prism skylight -> spot,
//  uv.x = side + a, uv.y = 0 floor / 1 ceiling), DUST (300 motes: uv1 = (a, c), uv2.x = height fraction f, uv2.y = size m).
//  Bus space = world (the bus never moves). The renderer bounds are set large by the build (vertices move every frame).
//  Global: _Udon_SkySpot.x = brightness envelope (LanbaiSkylightSpot.cs; 0 outside U8 .. U9).
// =====================================================================================================================
Shader "Lanbai/SkylightSpot"
{
    Properties
    {
        [KeywordEnum(Spot, Beam, Dust)] _Part ("Part", Float) = 0
        _Color ("Light colour (linear, #E2E8F3)", Vector) = (0.761, 0.807, 0.896, 0)
        _Gain ("Spot gain (white card #99A1AD, luma 170-200)", Float) = 1.15
        _BeamGain ("Beam gain", Float) = 0.035
        _DustGain ("Dust gain", Float) = 1.2
        _SkyC ("Skylight centre (bus m), glass plane y", Vector) = (0.55, 2.55, 2.80, 0)
        _SkyHalf ("Skylight half size (m)", Float) = 0.30
        _FloorY ("Floor y (m)", Float) = 0.623
        _CoreOfs ("Tear core offset from the gate tear position, per 1000 m of H", Vector) = (33.383, -0.378, 60.0, 0)
        _Penumbra ("Penumbra (m)", Float) = 0.22
    }
    SubShader
    {
        Tags { "Queue" = "Transparent+10" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
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
            #pragma shader_feature_local _PART_SPOT _PART_BEAM _PART_DUST
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"         // the gate tear position and H, declared once
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            float4 _Color;
            float _Gain, _BeamGain, _DustGain, _SkyHalf, _FloorY, _Penumbra;
            float4 _SkyC, _CoreOfs;

            // registered (D-16) but not yet in the generated LanbaiGlobals.cginc: same guard, so the regenerated file wins
            #ifndef LANBAI_DECL__Udon_SkySpot
            #define LANBAI_DECL__Udon_SkySpot
            float4 _Udon_SkySpot;
            #endif

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float4 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float k : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            float3 Core()
            {
                return _Udon_TearPos.xyz + _CoreOfs.xyz * (_Udon_TearH.x / 1000.0);
            }
            // skylight corner i (0: x-z-, 1: x+z-, 2: x+z+, 3: x-z+) at the glass plane
            float3 TopCorner(float i)
            {
                float sx = (i == 1.0 || i == 2.0) ? 1.0 : -1.0;
                float sz = (i >= 2.0) ? 1.0 : -1.0;
                return float3(_SkyC.x + sx * _SkyHalf, _SkyC.y, _SkyC.z + sz * _SkyHalf);
            }
            float3 FloorCorner(float i, float3 core)
            {
                float3 p = TopCorner(i);
                float3 d = normalize(p - core);
                float k = (_FloorY - p.y) / min(d.y, -1e-4);
                return p + d * k;
            }
            float3 Bilinear(float3 a, float3 b, float3 c, float3 d, float u, float v)
            {
                return lerp(lerp(a, b, u), lerp(d, c, u), v);
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 core = Core();
                float3 f0 = FloorCorner(0.0, core), f1 = FloorCorner(1.0, core), f2 = FloorCorner(2.0, core), f3 = FloorCorner(3.0, core);
                float3 wp = float3(0, 0, 0);
            #if defined(_PART_SPOT)
                // the card is the projected aperture grown by the penumbra; uv0 in 0..1 picks the corner
                float3 c = (f0 + f1 + f2 + f3) * 0.25;
                float3 p = Bilinear(f0, f1, f2, f3, v.uv0.x, v.uv0.y);
                float3 dir = p - c;
                wp = p + normalize(float3(dir.x, 0.0, dir.z) + 1e-6) * _Penumbra;
                o.uv = float4(v.uv0 * 2.0 - 1.0, 0, 0);
                o.k = 1.0;
            #elif defined(_PART_BEAM)
                // side s = floor(uv0.x) (0..3), a = frac(uv0.x) along that side, uv0.y: 0 floor, 1 ceiling
                float s = floor(v.uv0.x + 1e-4);
                float a = v.uv0.x - s;
                float s1 = fmod(s + 1.0, 4.0);
                float3 fa = (s < 0.5) ? f0 : (s < 1.5) ? f1 : (s < 2.5) ? f2 : f3;
                float3 fb = (s1 < 0.5) ? f0 : (s1 < 1.5) ? f1 : (s1 < 2.5) ? f2 : f3;
                float3 lo = lerp(fa, fb, a);
                float3 hi = lerp(TopCorner(s), TopCorner(s1), a) - float3(0, 0.05, 0);
                wp = lerp(lo, hi, v.uv0.y);
                o.uv = float4(a, v.uv0.y, 0, 0);
                o.k = 1.0;
            #else   // _PART_DUST: a mote inside the prism; uv0 = corner of its billboard (-0.5..0.5)
                float3 t0 = TopCorner(0.0), t1 = TopCorner(1.0), t2 = TopCorner(2.0), t3 = TopCorner(3.0);
                float3 lo = Bilinear(f0, f1, f2, f3, v.uv1.x, v.uv1.y);
                float3 hi = Bilinear(t0, t1, t2, t3, v.uv1.x, v.uv1.y) - float3(0, 0.05, 0);
                float3 c = lerp(lo, hi, v.uv2.x);
                float3 eye = LanbaiCentreEyePos();
                float3 fw = normalize(c - eye);
                float3 r = normalize(cross(float3(0, 1, 0), fw));
                float3 u = cross(fw, r);
                float cov;
                float extra = LanbaiInflate(v.uv2.y, distance(c, eye), 1.2, cov);
                float rad = v.uv2.y + extra;
                wp = c + (r * v.uv0.x + u * v.uv0.y) * 2.0 * rad;
                o.uv = float4(v.uv0 * 2.0, 0, 0);
                o.k = cov * LanbaiNearFade(c, 0.3, 1.0);
            #endif
                o.wpos = wp;
                o.pos = mul(UNITY_MATRIX_VP, float4(wp, 1.0));
                // 总导演终审 #8: nobody has written the tear (w <= 0) or the envelope is 0: nothing (never a projection
                // 19 km into the sky)
                if (_Udon_TearPos.w <= 0.0 || _Udon_SkySpot.x <= 0.0)
                    o.pos = float4(2.0, 2.0, 2.0, 1.0);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float env = saturate(_Udon_SkySpot.x);
            #if defined(_PART_SPOT)
                // the gate's final look: a soft box (feather from 55 % of the half size), the aperture convolved with the
                // INVERTED wound (a soft lens 0.35 -> 1.0, longer along the aisle), the floor studs x 0.4
                float du = i.uv.x, dv = i.uv.y;
                float box = smoothstep(1.0, 0.55, abs(du)) * smoothstep(1.0, 0.55, abs(dv));
                float rr = (du / 0.80) * (du / 0.80) + (dv / 1.05) * (dv / 1.05);
                float lens = 0.35 + 0.65 * smoothstep(1.0, 0.25, rr);
                float2 g = frac(i.wpos.xz / 0.05) - 0.5;
                float stud = smoothstep(0.25, 0.18, length(g));
                float e = box * lens * (0.944 + 0.056 * stud);
                return float4(_Color.rgb * _Gain * e * env, 0);
            #elif defined(_PART_BEAM)
                float k = smoothstep(0.0, 0.3, i.uv.x) * smoothstep(1.0, 0.7, i.uv.x) * (0.4 + 0.6 * (1.0 - i.uv.y));
                return float4(_Color.rgb * _BeamGain * k * env, 0);
            #else
                float r = length(i.uv.xy);
                float m = saturate(1.0 - r) * saturate(1.0 - r);
                return float4(_Color.rgb * _DustGain * m * i.k * env, 0);
            #endif
            }
            ENDCG
        }
    }
    Fallback Off
}
