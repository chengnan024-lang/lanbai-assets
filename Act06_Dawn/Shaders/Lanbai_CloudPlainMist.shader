// =====================================================================================================
//  Lanbai / CloudPlainMist  v1 (act 6 dawn, 2026-10-24 r2; cloud session "云", branch pkg/clouds)   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Checked with Common/Tools~/compile_check (DXC); compile in Unity 2022.3.
//
//  The mist in the lower part of act 6's slot (review r1 B1: the slot had a hard 34 m "mist" floor, and the frame
//  jumped +0.77 EV in 0.25 s when the eye went into it). Now the slot is open to the cover's underside and this mist
//  fills its lower part. Analytic, no march: the density depends on height only, a tent
//      sigma(y) = 0 at _Mist.x (y top), _Mist.w (peak density) at _Mist.y, 0 at _Mist.z (the cover bottom)
//  integrated along eye -> the scene depth (_CameraDepthTexture: the plain's ShadowCaster pass, the sea, the cabin).
//  It exists only in the open slot (weight: the slot region where the segment is nearest the peak height).
//  Colour: _MistColor (the bible's shadow blue-grey #8593AA, ungraded), a little brighter toward the sun.
//  Source/plain_ref.py mist() is the numpy port. Same proxy mesh as Lanbai/CloudPlain (a second renderer).
//  Queue Transparent-5: after the skybox and the cards, before the cabin glass (3000). Premultiplied alpha.
// =====================================================================================================
Shader "Lanbai/CloudPlainMist"
{
    Properties
    {
        _Mist ("Mist - x y top - y y peak - z y bottom - w peak density 1/m", Vector) = (-960, -1080, -1134, 0.045)
        _MistColor ("Mist colour - linear", Vector) = (0.42478, 0.50423, 0.72167, 0)
        _MistPhase ("Toward the sun - x k0 - y k1 - z sharpness", Vector) = (0.85, 0.7, 6, 0)
        _Slot ("Slot - x axis az - y half width - z s0 - w s1", Vector) = (18, 750, -2200, 4000)
        _SlotB ("Slot - x soft - y floor top - z centre q", Vector) = (60, -1134, 350, 0)
        _SunDirFallback ("Direction to the sun - fallback", Vector) = (0.4983, 0.1011, 0.8611, 0)
        _SlotOpen ("Slot open 0..1 - driver MPB", Range(0, 1)) = 1
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
            float4 _Mist, _MistColor, _MistPhase, _Slot, _SlotB, _SunDirFallback;
            float _SlotOpen, _MarchMax;

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

            // integral of the density from the bottom up to y
            float MistCum(float y)
            {
                float yt = _Mist.x, yp = _Mist.y, yb = _Mist.z, sg = _Mist.w;
                y = clamp(y, yb, yt);
                float lo = min(y, yp) - yb;
                float hi = max(y - yp, 0.0);
                return 0.5 * sg * lo * lo / (yp - yb) + sg * hi - 0.5 * sg * hi * hi / (yt - yp);
            }

            float MistSigma(float y)
            {
                float up = _Mist.w * (_Mist.x - y) / (_Mist.x - _Mist.y);
                float dn = _Mist.w * (y - _Mist.z) / (_Mist.y - _Mist.z);
                return (y < _Mist.x && y > _Mist.z) ? max(y > _Mist.y ? up : dn, 0.0) : 0.0;
            }

            struct FOut { half4 col : SV_Target; };

            FOut frag(v2f i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 roW = _WorldSpaceCameraPos;
                float3 V = normalize(i.wpos - roW);
                float3 ro = roW - i.origin;
                // quick out: the eye's ray never meets the mist's height band
                float y0 = ro.y;
                if (y0 > _Mist.x && V.y >= 0.0) discard;
                if (y0 < _Mist.z && V.y <= 0.0) discard;
                // the segment: eye -> the scene depth (the plain's hit, the sea, ...)
                float2 uv = UnityStereoTransformScreenSpaceTex(i.screen.xy / i.screen.w);
                float zEye = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, uv));
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                float tEnd = min(zEye / max(dot(V, camFwd), 1e-3), _MarchMax);
                float tau;
                if (abs(V.y) < 1e-3) tau = MistSigma(y0) * tEnd;
                else tau = abs(MistCum(y0 + V.y * tEnd) - MistCum(y0)) / abs(V.y);
                // the weight where the segment is nearest the peak height (the eye, the peak crossing, or its end)
                float y1 = y0 + V.y * tEnd;
                float yq = clamp(_Mist.y, min(y0, y1), max(y0, y1));
                float tp = (abs(V.y) > 1e-6) ? clamp((yq - y0) / V.y, 0.0, tEnd) : 0.0;
                float3 pp = ro + V * tp;
                tau *= SlotW(pp.xz);
                float a = 1.0 - exp(-tau);
                if (a < 1.0 / 512.0) discard;
                float3 sunD = LanbaiSunDir(_SunDirFallback.xyz);
                float ph = _MistPhase.x + _MistPhase.y * exp((dot(V, sunD) - 1.0) * _MistPhase.z);
                FOut o;
                o.col = half4(_MistColor.rgb * ph * a, a);
                return o;
            }
            ENDCG
        }
    }
    FallBack Off
}
