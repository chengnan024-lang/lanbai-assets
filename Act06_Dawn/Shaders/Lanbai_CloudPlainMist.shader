// =====================================================================================================
//  Lanbai / CloudPlainMist  v2 (act 6 dawn, 2026-10-24 r3; cloud session "云", branch pkg/clouds)   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Checked with Common/Tools~/compile_check (DXC); compile in Unity 2022.3.
//
//  The mist in the lower part of act 6's slot (review r1 B1: a hard 34 m "mist" floor made the frame jump +0.77 EV in
//  0.25 s; r3, director D-35 #1 / #4). The slot is open to the cover's underside; this fills its lower part.
//  A 16-sample march (quadratic spacing: fine where the mist starts) over the part of eye -> scene depth inside the
//  mist's height band (_CameraDepthTexture: the plain's ShadowCaster pass, the sea, the cabin). Density:
//      the tent in y (0 at the rolling top, _Mist.w at _Mist.y, 0 at the cover bottom _Mist.z)
//      x the slot region x (1 - the clear wedge toward the sun) x a slow low-contrast undulation
//    + wisps: a thin layer above it (_MistWisp), cut by a drifting noise.
//  The clear wedge (D-35 #1): seen from the bus, az 30 +-8 clear .. +-40 full; only for rays at / above the horizon
//  and only while the eye is above the cover bottom: the sun stays in view until it sets behind the lip (305.4), the
//  sea stays hidden below, and from under the cover the slot overhead is mist, not sky (312 APL).
//  Colour: the bible's shadow blue-grey #8593AA (ungraded), darker downward, +-22 % with the undulation, brighter toward
//  the sun; wisps a little lighter. Noise = the plain's detail tile (R), filtered to the sample spacing.
//  _MistClock = t (driver MPB): the undulation and the wisps drift along the slot with the timeline (D-33 #6).
//  Source/plain_ref.py mist() is the numpy port (same names). Same proxy mesh as Lanbai/CloudPlain (a second renderer).
//  Queue Transparent-5: after the skybox and the cards, before the cabin glass (3000). Premultiplied alpha.
// =====================================================================================================
Shader "Lanbai/CloudPlainMist"
{
    Properties
    {
        [NoScaleOffset] _DetailTex ("Plain_Detail_1024 - linear data", 2D) = "black" {}
        _Mist ("Mist - x y top - y y peak - z y bottom - w peak density 1/m", Vector) = (-960, -1080, -1134, 0.045)
        _MistColor ("Mist colour - linear", Vector) = (0.42478, 0.50423, 0.72167, 0)
        _MistPhase ("Toward the sun - x k0 - y k1 - z sharpness", Vector) = (0.85, 0.7, 6, 0)
        _MistWedge ("Clear wedge - x full deg - y zero deg - z w ray y gate", Vector) = (8, 40, -0.03, 0.02)
        _MistShade ("Shade - x dark - y pow - z depth m - w roll amp m", Vector) = (0.45, 0.7, 80, 40)
        _MistUnd ("Undulation - x period m - y amp - z colour - w drift m/s", Vector) = (2600, 0.45, 0.22, 1)
        _MistRoll ("Roll - x period m", Vector) = (1800, 0, 0, 0)
        _MistWisp ("Wisps - x y lo - y y mid - z y hi - w density", Vector) = (-1000, -945, -880, 0.004)
        _MistWispB ("Wisps - x period m - y drift m/s - z w noise cut", Vector) = (900, 4, 0.55, 0.8)
        _MistSteps ("March - x steps - y max length m", Vector) = (16, 6000, 0, 0)
        _Slot ("Slot - x axis az - y half width - z s0 - w s1", Vector) = (18, 750, -2200, 4000)
        _SlotB ("Slot - x soft - y floor top - z centre q", Vector) = (60, -1134, 350, 0)
        _SunDirFallback ("Direction to the sun - fallback", Vector) = (0.4983, 0.1011, 0.8611, 0)
        _SlotOpen ("Slot open 0..1 - driver MPB", Range(0, 1)) = 1
        _MistClock ("Clock s - driver MPB", Float) = 0
        _MarchMax ("Max distance m", Float) = 16000
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-5" "RenderType" = "Transparent" "IgnoreProjector" = "True" "DisableBatching" = "True" "ForceNoShadowCasting" = "True" }
        Cull Off ZWrite Off ZTest LEqual
        Blend One OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 5.0
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
            sampler2D _DetailTex;
            float4 _DetailTex_TexelSize;
            float4 _Mist, _MistColor, _MistPhase, _MistWedge, _MistShade, _MistUnd, _MistRoll, _MistWisp, _MistWispB, _MistSteps;
            float4 _Slot, _SlotB, _SunDirFallback;
            float _SlotOpen, _MistClock, _MarchMax;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                float3 origin : TEXCOORD1;
                float4 screen : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 w = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
                // the same proxy as Lanbai/CloudPlain: 1.5 m under / over THIS eye
                w.xz = _WorldSpaceCameraPos.xz + (w.xz - mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xz);
                w.y = _WorldSpaceCameraPos.y + (v.vertex.y < 0.0 ? -1.5 : 1.5);
                o.wpos = w;
                o.origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                o.pos = UnityWorldToClipPos(w);
                o.screen = ComputeScreenPos(o.pos);
                return o;
            }

            float Sig(float x) { return 1.0 / (1.0 + exp(clamp(x, -60.0, 60.0))); }

            // the slot region (no bulges), as Lanbai/CloudPlain Region().y
            float SlotW(float2 xz)
            {
                float a = radians(_Slot.x);
                float s = xz.x * sin(a) + xz.y * cos(a);
                float q = xz.x * cos(a) - xz.y * sin(a) - _SlotB.z;
                float hw = _Slot.y * _SlotOpen;
                float inw = (_SlotOpen > 1e-3) ? Sig((abs(q) - hw) / (0.25 * _SlotB.x)) : 0.0;
                return inw * Sig((_Slot.z - s) / (0.25 * _SlotB.x)) * Sig((s - _Slot.w) / (0.25 * _SlotB.x));
            }

            // the clear wedge toward the sun, seen from the bus (the field's origin): 1 = clear
            float Wedge(float2 xz, float2 sunH)
            {
                float r = length(xz);
                float c = dot(xz, sunH) / max(r * length(sunH), 1e-6);
                float w = smoothstep(cos(radians(_MistWedge.y)), cos(radians(_MistWedge.x)), c);
                return (r >= 1.0) ? w : 0.0;
            }

            // the detail tile's R, low-passed, at (xz - axis * drift) / period, mapped ~0..1
            float Noise(float2 xz, float period, float drift, float off, float lod)
            {
                float a = radians(_Slot.x);
                float2 uv = (xz - float2(sin(a), cos(a)) * drift) / period + float2(off, off * 0.7);
                float n = tex2Dlod(_DetailTex, float4(uv, 0.0, lod)).r;
                return saturate((n - 0.1) / 0.45);
            }

            // the tent with a rolling top yt
            float SigmaTop(float y, float yt)
            {
                float up = _Mist.w * (yt - y) / max(yt - _Mist.y, 1.0);
                float dn = _Mist.w * (y - _Mist.z) / (_Mist.y - _Mist.z);
                return (y < yt && y > _Mist.z) ? max(y > _Mist.y ? up : dn, 0.0) : 0.0;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 roW = _WorldSpaceCameraPos;
                float3 V = normalize(i.wpos - roW);
                float3 ro = roW - i.origin;
                float yLo = _Mist.z, yHi = max(_Mist.x + _MistShade.w, _MistWisp.z);
                if (ro.y > yHi && V.y >= 0.0) discard;
                if (ro.y < yLo && V.y <= 0.0) discard;
                // the segment: eye -> the scene depth, clipped to the band
                float2 uv = UnityStereoTransformScreenSpaceTex(i.screen.xy / i.screen.w);
                float zEye = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, uv));
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                float te = min(zEye / max(dot(V, camFwd), 1e-3), _MarchMax);
                float tIn, tOut;
                if (abs(V.y) < 1e-6)
                {
                    bool inBand = ro.y > yLo && ro.y < yHi;
                    tIn = 0.0; tOut = inBand ? te : 0.0;
                }
                else
                {
                    float ta = (yLo - ro.y) / V.y, tb = (yHi - ro.y) / V.y;
                    tIn = max(min(ta, tb), 0.0); tOut = max(ta, tb);
                }
                tOut = min(min(tOut, te), tIn + _MistSteps.y);
                float L = tOut - tIn;
                if (L <= 0.0) discard;

                float3 sunD = LanbaiSunDir(_SunDirFallback.xyz);
                float ph = _MistPhase.x + _MistPhase.y * exp((dot(V, sunD) - 1.0) * _MistPhase.z);
                // the clear lane: rays at / above the horizon, and only while the eye is above the cover bottom
                float gateV = smoothstep(_MistWedge.z, _MistWedge.w, V.y) * smoothstep(_Mist.z - 30.0, _Mist.z, ro.y);
                float texel = _DetailTex_TexelSize.x;
                float T = 1.0;
                float3 C = 0.0;
                int N = (int)_MistSteps.x;
                [loop]
                for (int k = 0; k < 32; k++)
                {
                    if (k >= N) break;
                    float u = (k + 0.5) / N;
                    float t = tIn + L * u * u;                              // quadratic: fine where the mist starts
                    float ds = L * 2.0 * u / N;
                    float3 p = ro + V * t;
                    float w = SlotW(p.xz) * (1.0 - Wedge(p.xz, sunD.xz) * gateV);
                    [branch] if (w < 1e-3) continue;
                    float lodU = max(4.0, log2(max(ds, 1e-3) / (_MistUnd.x * texel)));
                    float lodR = max(3.0, log2(max(ds, 1e-3) / (_MistRoll.x * texel)));
                    float lodW = max(3.0, log2(max(ds, 1e-3) / (_MistWispB.x * texel)));
                    float und = 1.0 + _MistUnd.y * (2.0 * Noise(p.xz, _MistUnd.x, _MistUnd.w * _MistClock, 0.13, lodU) - 1.0);
                    float roll = _MistShade.w * (2.0 * Noise(p.xz, _MistRoll.x, _MistUnd.w * _MistClock, 0.71, lodR) - 1.0);
                    float sg = SigmaTop(p.y, _Mist.x + roll) * und;
                    float wn = smoothstep(_MistWispB.z, _MistWispB.w, Noise(p.xz, _MistWispB.x, _MistWispB.y * _MistClock, 0.41, lodW));
                    float wt = saturate(p.y < _MistWisp.y ? (p.y - _MistWisp.x) / (_MistWisp.y - _MistWisp.x)
                                                          : (_MistWisp.z - p.y) / (_MistWisp.z - _MistWisp.y));
                    float sw = _MistWisp.w * wt * wn;
                    float a = 1.0 - exp(-(sg + sw) * w * ds);
                    float f = saturate((_Mist.x + _MistShade.w - p.y) / _MistShade.z);
                    float shade = 1.0 - _MistShade.x * pow(f, _MistShade.y);
                    float cm = shade * (1.0 + _MistUnd.z * (und - 1.0) / _MistUnd.y);
                    float c = (cm * sg + 1.12 * sw) / max(sg + sw, 1e-9);
                    C += (T * a * c * ph) * _MistColor.rgb;
                    T *= 1.0 - a;
                    if (T < 0.004) break;
                }
                float alpha = 1.0 - T;
                if (alpha < 1.0 / 512.0) discard;
                return half4(C, alpha);
            }
            ENDCG
        }
    }
    FallBack Off
}
