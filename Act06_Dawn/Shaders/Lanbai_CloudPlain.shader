// =====================================================================================================
//  Lanbai / CloudPlain  v1 (act 6 dawn, 2026-10-24; cloud session "云", branch pkg/clouds)   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Checked with Common/Tools~/compile_check (DXC); compile in Unity 2022.3.
//
//  Act 6's whole cloud body as ONE ray-marched field (Source/plain_ref.py is the numpy port; same section names):
//    top  Htop(xz) = _Body.x (the plain's top, -533) + relief (the gate deck's two periodic tiles, re-baked for the
//         dawn sun: Textures/Plain_Detail_1024 / Plain_Macro_512; x _Scale)
//    bottom = _Body.y (the cloud cover's underside, -1134)
//    regions: the deck's soft edge (sunward 4.58 km, elsewhere ~8.2 km), the 1 km slot along az 25 (opens over 6 s at
//    F1, _SlotOpen; its floor is a thin mist layer at -1100), the lip at the slot's end (top -729: the sun sets behind it
//    as the bus leaves the cover and comes back under the sunward edge at F1b1).
//    cloud = { bottom < y < Htop }. A ray from the eye (down OR up) marches between the body's bounds to the first
//    point inside. Shading: sun x N.L (tops: the baked N.L; walls: the field's own normal) x shadow (tops: the baked sun
//    path; walls / slot / lip / underside: 16 steps toward the sun through the mean body) + sky x AO + ground light +
//    a little multiple scattering; the underside: ground light + a glow toward the sunward edge. Then LanbaiFog.
//  The idea, the tiles, the march and the LOD are the gate's Lanbai/GateCloudDeck (GateClouds/, the gate session's
//  work), generalised; the gate's skin / rims / tear pieces are not here (README_Act06 §6).
//
//  Geometry: a big mesh (builder: Act06_PlainProxy) of TWO quads, object y = -1 (below the eye: downward rays) and
//  y = +1 (above: upward rays), pulled to 1.5 m under / over THIS eye. Its object origin = the field's origin (a child
//  of R_Dawn at local 0: the field moves with R_Dawn). Writes conservative depth (cards and the sea sort against it).
//  Colours: the cloud cards' dawn solve (Clouds_v2/Textures/cards_v2.json colours.dawn): one light for cards and plain.
// =====================================================================================================
Shader "Lanbai/CloudPlain"
{
    Properties
    {
        [NoScaleOffset] _DetailTex ("Plain_Detail_1024 - linear data", 2D) = "black" {}
        [NoScaleOffset] _MacroTex ("Plain_Macro_512 - linear data", 2D) = "black" {}
        _Periods ("Periods m - x detail - y macro - z micro scale", Vector) = (3200, 12800, 5, 0)
        _DetailRange ("Height ranges m - x y detail - z w macro", Vector) = (-24, 112, -24, 24)
        _TauMax ("Baked sun path max m - x detail - y macro", Vector) = (320, 800, 0, 0)
        _AmpRange ("Head amplitude - x y - brightness var z w", Vector) = (0.3, 0.8, 0.85, 1.1)
        _Micro ("Micro - x amp m - y envelope - z shade", Vector) = (8, 0.35, 0.6, 0)
        _March ("March - x steps - y step k - z slope - w max t", Vector) = (96, 0.9, 0.35, 16000)
        _MarchK ("March - x min k - y max k - z max dt - w bisections", Vector) = (0.004, 0.06, 250, 4)
        _Light ("Light - x sigma - y shadow - z ms k - w ms tau", Vector) = (0.012, 1.0, 0.004, 0.25)
        _Gains ("Gains - x sun - y sky - z ground - w wall slope", Vector) = (1, 0.35, 0.35, 1.5)
        _Under ("Underside - x glow - y glow length m - z ground k - w sky k", Vector) = (0.9, 900, 0.55, 0.12)
        _Trough ("Trough - x lod - y depth m - z k - w sky k", Vector) = (3.5, 30, 0.35, 0.6)
        _SunColor ("Sun colour x E - linear", Vector) = (6.3706, 2.2827, 0.3400, 0)
        _SkyUpColor ("Upper dome light - linear", Vector) = (1.5103, 1.8199, 2.5691, 0)
        _GroundColor ("Lower dome light - linear", Vector) = (0.3281, 0.4199, 0.6151, 0)
        _SunDirFallback ("Direction to the sun - fallback", Vector) = (0.4983, 0.1011, 0.8611, 0)
        _Body ("Body - x top - y bottom - z sun az deg", Vector) = (-533, -1134, 30, 0)
        _Slot ("Slot - x axis az - y half width - z s0 - w s1", Vector) = (25, 500, -2200, 4000)
        _SlotB ("Slot - x soft - y floor top", Vector) = (60, -1100, 0, 0)
        _Lip ("Lip - x top - y soft", Vector) = (-729, 40, 0, 0)
        _Edge ("Edge - x r0 - y r sun - z lobe deg - w soft", Vector) = (8200, 4583, 45, 180)
        _Wall ("Wall bulge - x period m - y amplitude m", Vector) = (700, 110, 0, 0)
        _SlotOpen ("Slot open 0..1 - driver MPB", Range(0, 1)) = 1
        _FogCap ("Fog Cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog Height Scale m - 0 none", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Geometry+40" "RenderType" = "Opaque" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Cull Off ZWrite On ZTest LEqual

        CGINCLUDE
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            sampler2D _DetailTex;
            sampler2D _MacroTex;
            float4 _DetailTex_TexelSize, _MacroTex_TexelSize;
            float4 _Periods, _DetailRange, _TauMax, _AmpRange, _Micro, _March, _MarchK, _Light, _Gains, _Under, _Trough;
            float4 _SunColor, _SkyUpColor, _GroundColor, _SunDirFallback, _Body, _Slot, _SlotB, _Lip, _Edge, _Wall;
            float _SlotOpen;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                float3 origin : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 w = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
                // the proxy: 1.5 m under (object y < 0) / over (y > 0) THIS eye, xz around it
                w.xz = _WorldSpaceCameraPos.xz + (w.xz - mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xz);
                w.y = _WorldSpaceCameraPos.y + (v.vertex.y < 0.0 ? -1.5 : 1.5);
                o.wpos = w;
                o.origin = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                o.pos = UnityWorldToClipPos(w);
                return o;
            }

            float Sig(float x) { return 1.0 / (1.0 + exp(clamp(x, -60.0, 60.0))); }

            // ---- [Region]: x deck, y slot, z lip (soft 0..1) at local xz; bulge: the slot walls' cauliflower
            // ([WallBulge]: the detail tile over (along the axis, height), +-_Wall.y m, mirrored per side)
            float3 Region(float2 xz, float y, float foot, bool bulge)
            {
                float r = length(xz);
                float az = degrees(atan2(xz.x, xz.y));
                float da = fmod(az - _Body.z + 540.0, 360.0) - 180.0;
                float R = _Edge.x + (_Edge.y - _Edge.x) * exp(-(da / _Edge.z) * (da / _Edge.z));
                float deck = Sig((r - R) / (0.25 * _Edge.w));
                float a = radians(_Slot.x);
                float s = xz.x * sin(a) + xz.y * cos(a);
                float q = xz.x * cos(a) - xz.y * sin(a);
                float hw = _Slot.y * _SlotOpen;
                float aq = abs(q);
                if (bulge)
                {
                    float lodW = log2(max(foot / (_Wall.x * _DetailTex_TexelSize.x), 1e-4));
                    float nz = tex2Dlod(_DetailTex, float4(s / _Wall.x + (q > 0.0 ? 0.31 : 0.0), y / _Wall.x, 0.0, lodW)).r;
                    aq += _Wall.y * (nz - 0.5) * 2.0 * _SlotOpen;
                }
                float inw = (_SlotOpen > 1e-3) ? Sig((aq - hw) / (0.25 * _SlotB.x)) : 0.0;
                float slot = inw * Sig((_Slot.z - s) / (0.25 * _SlotB.x)) * Sig((s - _Slot.w) / (0.25 * _SlotB.x));
                float lip = inw * Sig((_Slot.w - s) / (0.25 * _Lip.y));
                return float3(deck, slot, lip);
            }

            struct PSample { float m; float top; float4 d; float4 mm; float amp; float3 reg; };

            // ---- [Field]: margin (> 0 inside the cloud), the top surface, the texels, at a local point
            PSample Field(float3 p, float foot)
            {
                PSample s;
                float texD = _Periods.x * _DetailTex_TexelSize.x;
                float texM = _Periods.y * _MacroTex_TexelSize.x;
                s.d = tex2Dlod(_DetailTex, float4(p.xz / _Periods.x, 0.0, log2(max(foot / texD, 1e-4))));
                s.mm = tex2Dlod(_MacroTex, float4(p.xz / _Periods.y, 0.0, log2(max(foot / texM, 1e-4))));
                float hd = lerp(_DetailRange.x, _DetailRange.y, s.d.r);
                float hm = lerp(_DetailRange.z, _DetailRange.w, s.mm.r);
                s.amp = lerp(_AmpRange.x, _AmpRange.y, s.mm.b);
                float lodU = log2(max(foot * _Periods.z / texD, 1e-4));
                float mu = 0.45;
                [branch] if (lodU < 3.5)
                    mu = tex2Dlod(_DetailTex, float4(p.xz * _Periods.z / _Periods.x + float2(0.37, 0.61), 0.0, max(lodU, 0.0))).r;
                float fade = 1.0 - smoothstep(1.0, 3.5, lodU);
                float micro = _Micro.x * ((mu - 0.45) * fade + _Micro.y * (1.0 - fade));
                float rel = hm + s.amp * (hd + micro);
                s.reg = Region(p.xz, p.y, foot, true);
                float top = _Body.x + rel;
                top += (_Lip.x + 0.3 * rel - top) * s.reg.z;
                top += (_SlotB.y + 0.15 * rel - top) * s.reg.y;
                top = _Body.y + (top - _Body.y) * smoothstep(0.2, 0.8, s.reg.x);
                s.top = top;
                s.m = min(top - p.y, p.y - _Body.y);
                return s;
            }

            // ---- the march: first point inside the body along ro + V t (local); returns t (or -1)
            float March(float3 ro, float3 V, float pix)
            {
                float yHi = _Body.x + _DetailRange.w + _DetailRange.y * _AmpRange.y + 10.0;
                float yLo = _Body.y - 1.0;
                float t0, t1;
                if (abs(V.y) > 1e-6)
                {
                    float ta = (yHi - ro.y) / V.y, tb = (yLo - ro.y) / V.y;
                    t0 = max(min(ta, tb), 0.0);
                    t1 = max(ta, tb);
                }
                else { t0 = 0.0; t1 = _March.w; }
                if (ro.y < yHi && ro.y > yLo) t0 = 0.5;
                t1 = min(t1, _March.w);
                if (t1 <= t0) return -1.0;
                float tPrev = t0, tCur = t0 + 0.5;
                int N = (int)_March.x;
                [loop]
                for (int i = 0; i < 128; i++)
                {
                    if (i >= N || tPrev >= t1) break;
                    float tm = min(tCur, t1);
                    float foot = max(tm * pix, 1e-3) / sqrt(max(abs(V.y), 0.05));
                    float m = Field(ro + V * tm, foot).m;
                    if (m > 0.0)
                    {
                        float lo = tPrev, hi = tm;
                        int nb = (int)_MarchK.w;
                        [loop]
                        for (int b = 0; b < 6; b++)
                        {
                            if (b >= nb) break;
                            float mid = 0.5 * (lo + hi);
                            if (Field(ro + V * mid, max(mid * pix, 1e-3)).m > 0.0) hi = mid; else lo = mid;
                        }
                        return 0.5 * (lo + hi);
                    }
                    tPrev = tm;
                    tCur = tm + clamp(_March.y * abs(m) / (abs(V.y) + _March.z), _MarchK.x * tm, min(_MarchK.y * tm + 5.0, _MarchK.z));
                }
                return -1.0;
            }

            // coarse sun visibility through the MEAN body (no relief): 16 steps, exponential from 120 m to 6 km
            float SunVis(float3 p, float3 sunD)
            {
                float vis = 1.0, s = 120.0;                               // beyond the wall bulges: no self-speckle
                float k = pow(6000.0 / 120.0, 1.0 / 16.0);
                [loop]
                for (int i = 0; i < 16; i++)
                {
                    float3 q = p + sunD * s;
                    float3 reg = Region(q.xz, q.y, 1.0, false);
                    float top = _Body.x + (_Lip.x - _Body.x) * reg.z;
                    top += (_SlotB.y - top) * reg.y;
                    if (q.y < top && q.y > _Body.y && reg.x > 0.5) vis *= 0.55;   // soft, transmittance-like
                    s *= k;
                }
                return vis;
            }

            #if defined(UNITY_REVERSED_Z)
                #define PLAIN_DEPTH SV_DepthLessEqual
            #else
                #define PLAIN_DEPTH SV_DepthGreaterEqual
            #endif

            float PlainDepth(float3 roW, float3 V, float tHit)
            {
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                float tDepth = min(tHit, 0.99 * _ProjectionParams.z / max(dot(V, camFwd), 1e-3));
                tDepth = max(tDepth, 1.5 / max(abs(V.y), 1e-4) * 1.001);
                float4 clip = UnityWorldToClipPos(roW + V * tDepth);
                return clip.z / clip.w;
            }
        ENDCG

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 5.0
            #pragma multi_compile_fog

            struct FOut { half4 col : SV_Target; float depth : PLAIN_DEPTH; };

            FOut frag(v2f i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 roW = _WorldSpaceCameraPos;
                float3 V = normalize(i.wpos - roW);
                float3 ro = roW - i.origin;
                float pix = 2.0 / (_ScreenParams.y * unity_CameraProjection._m11);
                float tHit = March(ro, V, pix);
                if (tHit < 0.0) discard;
                float3 sunD = LanbaiSunDir(_SunDirFallback.xyz);

                // ---- [Shade]
                float3 p = ro + V * tHit;
                float foot = max(tHit * pix, 1e-3);
                PSample h = Field(p, foot);
                bool under = (abs(p.y - _Body.y) < abs(h.top - p.y)) && (V.y > 0.0);
                float e = max(foot * 2.0, 4.0);
                float tx = Field(p + float3(e, 0, 0), foot).top;
                float tz = Field(p + float3(0, 0, e), foot).top;
                float gx = (tx - h.top) / e, gz = (tz - h.top) / e;
                float3 n = normalize(float3(-gx, 1.0, -gz));
                float wall = smoothstep(_Gains.w * 0.5, _Gains.w, length(float2(gx, gz)));
                float lam = lerp(h.d.a, saturate(dot(n, sunD)), wall);
                float tau = _Light.x * (h.amp * h.d.g * _TauMax.x + h.mm.g * _TauMax.y);
                float sh = exp(-tau * _Light.y);
                if (wall > 0.05 || h.reg.y > 0.05 || h.reg.z > 0.05 || under)
                    sh = min(sh, SunVis(p + n * 2.0, sunD));
                float ms = _Light.z * exp(-tau * _Light.w);
                float ao = lerp(h.d.b, 0.75, wall);
                float up = saturate(n.y);
                float var = lerp(_AmpRange.z, _AmpRange.w, h.mm.a);
                float3 c = (_Gains.x * (lam * sh + ms)) * _SunColor.rgb
                         + (_Gains.y * ao * (0.55 + 0.45 * up)) * _SkyUpColor.rgb + (_Gains.z * 0.25 * (1.0 - up)) * _GroundColor.rgb;
                c *= var;
                if (under)
                {
                    float r = length(p.xz);
                    float az = degrees(atan2(p.x, p.z));
                    float da = fmod(az - _Body.z + 540.0, 360.0) - 180.0;
                    float R = _Edge.x + (_Edge.y - _Edge.x) * exp(-(da / _Edge.z) * (da / _Edge.z));
                    float glow = _Under.x * exp(-max(R - r, 0.0) / _Under.y) * saturate(cos(radians(da)));
                    c = (_Gains.z * _Under.z * var) * _GroundColor.rgb + (glow * var * 0.35) * _SunColor.rgb + (_Under.w * var) * _SkyUpColor.rgb;
                }
                // troughs toward the deep sky light (tops only)
                float texD = _Periods.x * _DetailTex_TexelSize.x;
                float lodT = max(log2(max(foot, 1e-3) / texD) + _Trough.x, _Trough.x);
                float dm = tex2Dlod(_DetailTex, float4(p.xz / _Periods.x, 0.0, lodT)).r;
                float hMean = _Body.x + lerp(_DetailRange.z, _DetailRange.w, h.mm.r) + h.amp * lerp(_DetailRange.x, _DetailRange.y, dm);
                float trough = saturate((hMean - p.y) / _Trough.y) * _Trough.z * (1.0 - wall) * (1.0 - h.reg.y);
                c = lerp(c, (_Gains.y * _Trough.w) * _SkyUpColor.rgb, trough);

                // ---- [Fog]
                float3 pw = roW + V * tHit;
                c = LanbaiApplyFog(c, pw);
                FOut o;
                o.col = half4(c, 1.0);
                o.depth = PlainDepth(roW, V, tHit);
                return o;
            }
            ENDCG
        }

        // the body in _CameraDepthTexture (soft particles of the cards, the sea's depth fades): the same march, no light
        Pass
        {
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual Cull Off ColorMask 0
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragDepth
            #pragma target 5.0

            half4 fragDepth(v2f i, out float depth : PLAIN_DEPTH) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 roW = _WorldSpaceCameraPos;
                float3 V = normalize(i.wpos - roW);
                float pix = 2.0 / (_ScreenParams.y * unity_CameraProjection._m11);
                float tHit = March(roW - i.origin, V, pix);
                if (tHit < 0.0) discard;
                depth = PlainDepth(roW, V, tHit);
                return 0;
            }
            ENDCG
        }
    }
    FallBack Off
}
