// =====================================================================================================
//  Lanbai/SeaParticles   蓝白 · everything small that moves in the sea, as deterministic functions of the clock
//                        (no ParticleSystem: same picture for every player at the same t, no simulation state)
//    SNOW    海雪 1 200, 25 m sphere around the bus, 0.8–2.5 cm, #697987 α 0.3–0.6, sinking 1.5 cm/s (§6·7a 大气)
//    SEED    播下的光 ~200: born once (0.2 s flash) at F3i..F5, then 12–15 % steady glow FIXED IN THE WATER (§6·7a 播种)
//    TRAIL   船体生物荧光 300/s, life 1.5–3 s, 1–3 cm with a soft glow, along the hull (F4 on; §6·7a, §6·7b)
//    BUBBLE  入水 120 bubbles on the glass (≤ 1.5 s, one-shot at F2h) and 40 bubbles from the seat seams (looping)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//
//  MESH CONTRACT (the Act07 builder generates the four meshes from Act07_Layout.json 'particles'; same idea as
//  lens_tech's Lanbai_PointSprites): every particle = one quad = 4 vertices with the SAME POSITION, UV0 = corner (-1..1)
//    POSITION   SNOW / SEED : position in the WATER frame (m)  (x right, y up from the sea surface (= -depth), z = bus
//                             heading; the bus origin is at _Udon_SeaBus.xyz in that frame)
//               TRAIL / BUBBLE : position in BUS coordinates (the bus sits at the world origin; the object at the origin)
//    UV1        x = seed 0..1, y = radius m
//    UV2        SNOW: unused · SEED: x = birth t (timeline s), y = steady level 0.12..0.15
//               TRAIL: x = phase 0..1 in the pool, y = life s · BUBBLE: x = delay s (one-shot) / phase 0..1 (loop), y = duration s
//    COLOR      rgb = linear colour, a = alpha
//  GLOBALS: _Udon_T (timeline s), _Udon_SeaBus (xyz = bus origin in the water frame), _Udon_SeaBusVel (xyz m/s, same frame)
//  BOUNDS: the vertex shader moves every quad (snow wraps around the bus, seeds are fixed in the water frame), so the
//  generated mesh MUST carry bounds that enclose where it draws (the Act07 builder sets a 4 km box), or Unity culls it.
//  Billboards face the CENTRE eye; never narrower than _MinPx pixels (energy kept: alpha x coverage); nothing inside
//  _NearFade.x of the eye (bible §1.8: nothing within 0.3 m; sparks never within 5 m is the layout's job).
// =====================================================================================================
Shader "Lanbai/SeaParticles"
{
    Properties
    {
        [KeywordEnum(Snow, Seed, Trail, Bubble)] _KIND ("Kind", Float) = 0
        _Gain ("Gain  driver", Float) = 1
        _Tint ("Tint linear", Vector) = (1, 1, 1, 1)
        _MinPx ("Minimum size px", Range(0.5, 3)) = 1.2
        _NearFade ("Near fade m  x start  y full", Vector) = (0.3, 0.8, 0, 0)
        _Box ("Snow wrap box m", Float) = 50
        _Sphere ("Snow sphere radius m", Float) = 25
        _Sink ("Snow sinking m per s", Float) = 0.015
        _FlashGain ("Seed birth flash x steady", Float) = 7.0
        _FlashTime ("Seed flash s", Float) = 0.2
        _PoolRate ("Trail births per s", Float) = 300
        _PoolCount ("Trail pool size", Float) = 900
        _T0 ("Start t  trails and bubbles", Float) = 0
        _Loop ("Bubble loop period s  0 one-shot", Float) = 0
        _Rise ("Bubble rise m", Float) = 0.6
        [Enum(Alpha, 0, Additive, 1)] _Additive ("Blend look  emitters additive  snow bubbles premultiplied", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst", Float) = 10
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-10" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend [_SrcBlend] [_DstBlend]
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma shader_feature_local _KIND_SNOW _KIND_SEED _KIND_TRAIL _KIND_BUBBLE
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "LanbaiSeaGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            float4 _Tint, _NearFade;
            float _Gain, _MinPx, _Box, _Sphere, _Sink, _FlashGain, _FlashTime, _PoolRate, _PoolCount, _T0, _Loop, _Rise, _Additive;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                float4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 col : TEXCOORD1;
                float3 posWS : TEXCOORD2;
                float2 k : TEXCOORD3;          // x = coverage, y = kind-specific (bubble rim)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            inline float Hash11(float x) { return frac(sin(x * 127.1 + 311.7) * 43758.5453); }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float t = _Udon_T > 0.0 ? _Udon_T : _Time.y;
                float seed = v.uv1.x;
                float radius = v.uv1.y;
                float alpha = v.color.a;
                float bright = 1.0;
                float3 rel;                                     // position relative to the bus origin (bus coords)
            #if defined(_KIND_SNOW)
                float3 pw = v.vertex.xyz - float3(0.0, _Sink * t, 0.0);
                float3 d = pw - _Udon_SeaBus.xyz;
                rel = (frac(d / _Box + 0.5) - 0.5) * _Box;      // wrap in a box that rides with the bus
                float r = length(rel);
                alpha *= 1.0 - smoothstep(_Sphere * 0.8, _Sphere, r);
            #elif defined(_KIND_SEED)
                rel = v.vertex.xyz - _Udon_SeaBus.xyz;
                float age = t - v.uv2.x;
                float flash = exp(-max(age, 0.0) / max(_FlashTime * 0.5, 1e-3));
                bright = age < 0.0 ? 0.0 : (v.uv2.y + (_FlashGain * v.uv2.y) * flash);
            #elif defined(_KIND_TRAIL)
                float period = _PoolCount / max(_PoolRate, 1.0);
                float x = (t - _T0) / period - v.uv2.x;
                float cyc = floor(x);
                float age = (x - cyc) * period;
                float life = v.uv2.y;
                float alive = (t >= _T0 + v.uv2.x * period) ? 1.0 : 0.0;
                float h = Hash11(seed * 91.7 + cyc * 1.31);
                float3 jit = (float3(Hash11(h * 13.1), Hash11(h * 17.9), Hash11(h * 23.3)) - 0.5) * 0.25;
                rel = v.vertex.xyz + jit - _Udon_SeaBusVel.xyz * age + float3(0.0, 0.02 * age, 0.0);
                float u = age / max(life, 1e-3);
                bright = alive * (age < life ? smoothstep(0.0, 0.08, u) * (1.0 - smoothstep(0.35, 1.0, u)) : 0.0);
            #else   // _KIND_BUBBLE
                float age, dur = v.uv2.y;
                if (_Loop > 0.0) age = frac((t - _T0) / _Loop + v.uv2.x) * _Loop;
                else age = t - _T0 - v.uv2.x;
                float u = age / max(dur, 1e-3);
                bright = (u >= 0.0 && u <= 1.0) ? smoothstep(0.0, 0.1, u) * (1.0 - smoothstep(0.85, 1.0, u)) : 0.0;
                float climb = u * u * _Rise;                    // clings, then lets go and speeds up
                float wob = 0.01 * sin(age * 19.0 + seed * 40.0);
                rel = v.vertex.xyz + float3(wob, climb, 0.0);
                radius *= 0.85 + 0.3 * u;
                alpha *= bright;                                // premultiplied kinds fade by alpha, not by rgb
                bright = alpha > 0.0 ? 1.0 : 0.0;
            #endif
                float3 C = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;            // the bus origin in the world
                float3 P = C + rel;
                float3 eye = LanbaiCentreEyePos();
                float dist = distance(P, eye);
                float cov;
                float rd = radius + LanbaiInflate(radius, dist, _MinPx, cov);
                float3 fwd = normalize(eye - P);
                float3 rightV = normalize(cross(float3(0.0, 1.0, 0.0), fwd) + float3(1e-5, 0.0, 0.0));
                float3 upV = cross(fwd, rightV);
                float3 Pw = P + (rightV * v.uv0.x + upV * v.uv0.y) * rd;
                o.posWS = P;
                o.pos = UnityWorldToClipPos(Pw);
                o.uv = v.uv0;
                // brightness rides on rgb (emitters are additive: rgb x a); snow / bubbles are premultiplied alpha
                o.col = float4(v.color.rgb * _Tint.rgb * bright, alpha * _Tint.a * cov * cov * (bright > 0.0 ? 1.0 : 0.0));
                o.k = float2(cov, 0.0);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float r2 = dot(i.uv, i.uv);
                if (r2 > 1.0) discard;
            #if defined(_KIND_BUBBLE)
                float r = sqrt(r2);
                float shape = smoothstep(0.62, 0.92, r) * (1.0 - smoothstep(0.92, 1.0, r)) + 0.35 * exp(-((i.uv.x + 0.35) * (i.uv.x + 0.35) + (i.uv.y - 0.4) * (i.uv.y - 0.4)) * 40.0);
            #elif defined(_KIND_SNOW)
                float shape = exp(-r2 * 3.0) * (1.0 - r2);
            #else
                float shape = exp(-r2 * 9.0) + 0.18 * exp(-r2 * 2.0) * (1.0 - r2);       // core + soft glow
            #endif
                float a = i.col.a * shape * _Gain;
                a *= LanbaiNearFade(i.posWS, _NearFade.x, _NearFade.y);
                float fogA = LanbaiFogAmount(i.posWS, LanbaiCentreEyePos());
                float3 rgb = i.col.rgb;
            #if defined(_KIND_SEED) || defined(_KIND_TRAIL)
                // emitters: their light is absorbed on the way, no fog colour added
                return float4(rgb * a * (1.0 - fogA), _Additive > 0.5 ? 0.0 : a * (1.0 - fogA));
            #else
                rgb = lerp(rgb, LanbaiHorizon(normalize(i.posWS - LanbaiCentreEyePos())), fogA);
                return float4(rgb * a, a);
            #endif
            }
            ENDCG
        }
    }
    FallBack Off
}
