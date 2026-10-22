// =====================================================================================================
//  Lanbai / GateCloudDeck  v1 (gate clouds kit, 2026-10-22; cloud art team)   蓝白 · 触手之门 · 云海   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  The gate's cloud sea, seen from 40-150 m above it, out to the horizon. One big quad (GateClouds_DeckQuad, built by
//  LanbaiGateCloudsBuilder) lies flat under everything; every pixel of it ray-marches a HEIGHT FIELD of cumulus heads
//  (two periodic tiles baked for the gate's moon by Source/deck_tiles.py) and shades it:
//    * the dense surface: Lambert toward the moon (baked N.L) x the heads' cast shadow (baked moon path) + sky x AO;
//      looking toward the moon you see the heads' dark flanks, from the side / rear windows their silver moon side
//    * the SOFT SKIN over the heads: where a ray passes over a crest it crosses a thin lit skin -> the silver rims
//      (forward-scattered moonlight, two-lobe HG). Skin met while the ray sinks onto a top it then hits does not
//      count (_SkinApproach): dark tops, bright silhouettes, like the Blender finals.
//    * the gate's fog (LanbaiGateSky.cginc: band + 0.35 moon aureole), at the hit distance x _FogScale.
//  It writes the hit depth (SV_Depth), so the arms' roots, the tear's foot and the cloud cards meet the billows
//  where they really are. Tear_CloudGlow(_Lit) then multiplies the pool onto it exactly as before.
//
//  The numpy port Source/deck_ref.py is the reference: the same march, LOD, lighting, fog. Same defaults.
//  Cloud-sea frame: samples at (worldPos - _Udon_GateOrigin).xz, so the deck travels with GateRoot (v_g).
//  Globals (README_GateLayout §2.1, unchanged): _Udon_CloudTop (x = cloud top world y, w = 1), _Udon_GateOrigin,
//  _Udon_MoonDir, _Udon_TearPos (band azimuth). Unset -> the material fallbacks.
//  Cost: mean ~20-30 march steps per pixel (each 3 fetches), 5 bisections, early out (Source/deck_ref.py prints it).
//  Includes Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc (project-root path, CONTROL_总控 §3).
// =====================================================================================================
Shader "Lanbai/GateCloudDeck"
{
    Properties
    {
        [Header(Tiles  deck_tiles.py)]
        [NoScaleOffset] _DetailTex ("Deck_Detail_1024 (R height, G moon path, B sky AO, A moon N.L); linear", 2D) = "gray" {}
        [NoScaleOffset] _MacroTex ("Deck_Macro_512 (R swell, G moon path, B amplitude, A brightness); linear", 2D) = "gray" {}
        _Periods ("Periods m: detail, macro, micro scale, -", Vector) = (960, 6400, 7, 0)
        _DetailRange ("Detail height min, max (m); macro min, max (m)", Vector) = (-12, 44, -12, 12)
        _TauMax ("Moon path max (m): detail, macro", Vector) = (160, 400, 0, 0)
        _AmpRange ("Detail amplitude: macro B 0..1 maps to min..max; brightness min, max", Vector) = (0.3, 0.8, 0.75, 1.15)
        _Micro ("Micro: amplitude m, envelope, -, -", Vector) = (5, 0.35, 0, 0)

        [Header(March)]
        _Steps ("Max steps (mean use ~20-30)", Range(16, 160)) = 120
        _StepK ("Min step growth per step", Range(0.005, 0.1)) = 0.02
        _MarchRange ("March from (m), to (m); far mean height above the top (m); clearance under the eye (m)", Vector) = (12, 1600, 12, 6)
        _LodBias ("LOD bias", Range(-2, 2)) = 0

        [Header(Light)]
        _MoonColor ("Moon colour #D6E4FF, linear", Vector) = (0.6724, 0.7758, 1.0, 1)
        _MoonE ("Moon radiance on the deck", Range(0, 2)) = 0.38
        _AmbColor ("Sky ambient (HazeFar), linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _AmbK ("Sky ambient x AO", Range(0, 2)) = 0.35
        _Phase ("HG g1, g2, mix, surface lobe softening", Vector) = (0.8, -0.18, 0.62, 0.35)
        _Skin ("Skin: sigma (1/m), edge (m), approach weight, sigma toward the moon", Vector) = (0.8, 0.5, 0.0, 0.12)
        _Surf ("Surface: sigma toward the moon, forward lobe, Lambert, cast-shadow scale", Vector) = (0.14, 0.015, 0.8, 0.35)
        _Ms ("Multiple scattering: k, tau scale; far rim, -", Vector) = (0.01, 0.28, 0.12, 0)
        _Gain ("Gain", Range(0, 3)) = 1

        [Header(Crevasse  the foot splits the deck  GateLayout tear.crevasse)]
        _Crev ("Crevasse: length x S (m), half width / white half width, depth (m), lip height (m)", Vector) = (230, 0.4, 25, 5)
        _CrevGlow ("Crevasse floor glow #C0B9E4 x 0.35, linear", Vector) = (0.184, 0.170, 0.272, 1)
        _TearFootW ("Tear foot fallback: world xyz, w = white half width (global _Udon_TearFoot wins)", Vector) = (-0.3, -57.4, 1497.6, 76)

        [Header(Fog  LanbaiGateSky)]
        _FogDensity ("Fog density (gate: 0.0006) x scale", Vector) = (0.0006, 1.8, 0.35, 0)
        _CloudTopY ("Cloud top world y (fallback; _Udon_CloudTop wins)", Float) = -57.4
        _GateOrigin ("GateRoot position (fallback; _Udon_GateOrigin wins)", Vector) = (0, 92.6, 1478.4, 0)
        _RimDir ("Direction to the moon (fallback; _Udon_MoonDir wins)", Vector) = (-0.2059, 0.1392, 0.9686, 0)

        // shared with LanbaiGateSky.cginc (same values as the skybox and the arms)
        _HazeNear ("Haze Band Next To The Tear, linear", Vector) = (0.1085, 0.1130, 0.1641, 1)
        _HazeFar ("Haze Band 50 deg Away, linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _Void ("Void, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation", Vector) = (6, 22, 2, 0)
        _BelowHorizon ("Below the horizon", Vector) = (-25, 0, 0.55, 0)
        _BelowDesat ("Below-horizon desaturation", Range(0, 1)) = 0.6
        _BackBand ("Back band (rear view 1.25)", Range(0, 2)) = 0.55
        _TearPos ("Tear core fallback (world)", Vector) = (0, 297, 1800, 0)
        _MoonGlowColor ("Moon aureole, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole shape", Vector) = (1.6, 0.9, 0.06, 0.32)
        _HaloColor ("Halo (unused here)", Vector) = (0.195, 0.198, 0.332, 1)
    }
    SubShader
    {
        // opaque, after the arms (it writes its own depth, so the order only matters for overdraw)
        Tags { "Queue" = "Geometry+40" "RenderType" = "Opaque" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Cull Off ZWrite On ZTest LEqual

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"

            sampler2D _DetailTex;
            sampler2D _MacroTex;
            float4 _DetailTex_TexelSize;
            float4 _MacroTex_TexelSize;
            float4 _Periods, _DetailRange, _TauMax, _AmpRange, _Micro;
            float _Steps, _StepK, _LodBias;
            float4 _MarchRange;
            float4 _MoonColor, _AmbColor, _Phase, _Skin, _Surf, _Ms;
            float _MoonE, _AmbK, _Gain;
            float4 _FogDensity;
            float _CloudTopY;
            float4 _GateOrigin, _RimDir;
            float4 _Udon_CloudTop;
            float4 _Udon_GateOrigin;
            float4 _Udon_TearFoot;     // xyz = the tear's foot (world), w = half width of the white (m)
            float4 _Crev, _CrevGlow, _TearFootW;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                return o;
            }

            float CloudTop() { return (_Udon_CloudTop.w > 0.0) ? _Udon_CloudTop.x : _CloudTopY; }
            float3 GateOrigin() { return (_Udon_GateOrigin.w > 0.0) ? _Udon_GateOrigin.xyz : _GateOrigin.xyz; }

            float HG(float c, float g) { return (1.0 - g * g) / pow(max(1.0 + g * g - 2.0 * g * c, 1e-4), 1.5); }

            // the ray context the field needs
            struct DeckRay
            {
                float3 ro, V, O;
                float top, vy, pix;
                float2 acrossDir, alongDir;    // unit horizontal axes of the pixel footprint
            };

            struct DeckSample
            {
                float c;          // clearance above the height field (m)
                float4 d;         // detail texel
                float4 m;         // macro texel
                float amp;
                float foot;       // footprint (m), for the skin
                float crev;       // how deep in the crevasse (0..1) x its fade toward the bus: the floor glow
            };

            // the height field at distance t (exactly deck_ref.field): anisotropic footprint through tex2Dgrad
            DeckSample Field(DeckRay r, float t)
            {
                DeckSample s;
                float3 p = r.ro + r.V * t;
                float2 cs = p.xz - r.O.xz;
                float across = max(t * r.pix, 1e-3);
                float along = min(across / max(r.vy, 0.02), across * 16.0);
                s.foot = sqrt(across * along);
                float lb = exp2(_LodBias);
                float2 gA = r.acrossDir * (across * lb);
                float2 gB = r.alongDir * (along * lb);
                s.d = tex2Dgrad(_DetailTex, cs / _Periods.x, gA / _Periods.x, gB / _Periods.x);
                s.m = tex2Dgrad(_MacroTex, cs / _Periods.y, gA / _Periods.y, gB / _Periods.y);
                float hd = lerp(_DetailRange.x, _DetailRange.y, s.d.r);
                float hm = lerp(_DetailRange.z, _DetailRange.w, s.m.r);
                s.amp = lerp(_AmpRange.x, _AmpRange.y, s.m.b);
                // micro cauliflower: the detail tile again, _Periods.z times smaller; where its lumps are below a pixel the
                // surface sits at their upper envelope (a skimming ray is still stopped)
                float sc = _Periods.z;
                float lodU = log2(max(s.foot * sc / (_Periods.x * _DetailTex_TexelSize.x), 1e-4)) + _LodBias;
                float mu = tex2Dgrad(_DetailTex, cs * sc / _Periods.x + float2(0.37, 0.61), gA * sc / _Periods.x, gB * sc / _Periods.x).r;
                float fade = 1.0 - smoothstep(1.0, 3.5, lodU);
                float micro = _Micro.x * ((mu - 0.45) * fade + _Micro.y * (1.0 - fade));
                float H = r.top + hm + s.amp * (hd + micro);
                // never a head into the bus: within ~300 m the heads stop _MarchRange.w below the eye
                float dxz = length(p.xz - r.ro.xz);
                H = lerp(min(H, r.ro.y - _MarchRange.w), H, smoothstep(150.0, 400.0, dxz));
                // the crevasse: the foot of the white splits the deck along -Z (toward the bus), length _Crev.x x S,
                // half width _Crev.y x the white's half width -> 0, _Crev.z deep, the lips raised _Crev.w
                float4 ft = (_Udon_TearFoot.w > 0.0) ? _Udon_TearFoot : _TearFootW;
                float S = ((_Udon_TearH.w > 0.0) ? _Udon_TearH.x : 640.0) / 1000.0;
                float al = (ft.z - p.z) / max(_Crev.x * S, 1.0);
                float hwc = max(_Crev.y * ft.w * (1.0 - al), 0.5);
                float ac = abs(p.x - ft.x) / hwc;
                float inLen = smoothstep(-0.04, 0.02, al) * (1.0 - smoothstep(0.7, 1.0, al));
                float k = (1.0 - smoothstep(0.55, 1.0, ac)) * inLen;
                float lip = exp(-(ac - 1.2) * (ac - 1.2) / 0.18) * inLen * (1.0 - al);
                H += -_Crev.z * k + _Crev.w * lip;
                s.crev = k * saturate(1.0 - al);
                s.c = p.y - H;
                return s;
            }

            float MoonTau(DeckSample s)
            {
                return _Surf.x * (s.amp * s.d.g * _TauMax.x + s.m.g * _TauMax.y);
            }

            // interleaved gradient noise (Jimenez 2014)
            float IGN(float2 px) { return frac(52.9829189 * frac(dot(px, float2(0.06711056, 0.00583715)))); }

            struct FOut { half4 col : SV_Target; float depth : SV_Depth; };

            FOut frag(v2f i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                DeckRay r;
                r.ro = _WorldSpaceCameraPos;
                r.V = normalize(i.wpos - r.ro);
                r.vy = -r.V.y;
                if (r.vy < 1e-4) discard;                                  // only rays going down
                r.O = GateOrigin();
                r.top = CloudTop();
                r.pix = 2.0 / (_ScreenParams.y * unity_CameraProjection._m11);
                float2 vh = r.V.xz;
                float lvh = length(vh);
                r.alongDir = (lvh > 1e-5) ? vh / lvh : float2(0.0, 1.0);
                r.acrossDir = float2(-r.alongDir.y, r.alongDir.x);

                float3 moonD = LanbaiMoonDir(_RimDir.xyz);
                float yTop = r.top + _DetailRange.w + _DetailRange.y * _AmpRange.y;
                float yBot = r.top + _DetailRange.z + _DetailRange.x * _AmpRange.y;
                float t0 = max((r.ro.y - yTop) / r.vy, 0.0);
                float t1 = min((r.ro.y - yBot) / r.vy, 16000.0);
                float tEnd = min(t1, _MarchRange.y);
                float ts = max(max(t0, _MarchRange.x), 0.5 * (r.ro.y - r.top) / r.vy);
                int N = (int)_Steps;
                float k = max(_StepK, pow(max(tEnd / ts, 1.0), 1.0 / max(N - 1, 1)) - 1.0);   // the last sample (s = N-1, jit -> 0) reaches tEnd
                float jit = IGN(i.pos.xy);

                float cm = dot(r.V, moonD);
                float phase = _Phase.z * HG(cm, _Phase.x) + (1.0 - _Phase.z) * HG(cm, _Phase.y);

                float T = 1.0;
                float3 acc = 0.0;
                float3 pendL = 0.0;
                float pendOd = 0.0;
                float tPrev = t0;
                float tHit = t1;
                bool hit = false;
                float cPrev = Field(r, ts).c;

                // 1) exponential march + the skin (rims), until the ray dips under the field
                [loop]
                for (int s = 0; s < 160; s++)
                {
                    if (s >= N || tPrev >= tEnd) break;
                    float tm = min(ts * pow(1.0 + k, s + jit), tEnd);
                    DeckSample f = Field(r, tm);
                    float dt = max(tm - tPrev, 0.0);
                    float ca = max(cPrev, 0.0);
                    float cb = max(f.c, 0.0);
                    float edge0 = _Skin.y;
                    float edge = edge0 + 0.35 * f.foot;
                    // exact skin column for a clearance varying linearly from ca to cb
                    float dc = cb - ca;
                    float ea = exp(-ca / edge), eb = exp(-cb / edge);
                    float colm = (abs(dc) > 1e-3) ? dt * edge * (ea - eb) / dc : dt * eb;
                    float od = _Skin.x * (edge0 / edge) * colm;
                    float tauS = _Skin.w * (f.amp * f.d.g * _TauMax.x + f.m.g * _TauMax.y);
                    float moon = _MoonE * (phase * exp(-tauS) + _Ms.x * exp(-tauS * _Ms.y));
                    float3 S = moon * _MoonColor.rgb + (_AmbK * f.d.b) * _AmbColor.rgb;
                    pendOd += od;
                    pendL += od * S;
                    if (f.c > cPrev)                                   // passed over a crest: commit the rim
                    {
                        float a = 1.0 - exp(-pendOd);
                        acc += T * a / max(pendOd, 1e-9) * pendL;
                        T *= 1.0 - a;
                        pendOd = 0.0;
                        pendL = 0.0;
                    }
                    cPrev = f.c;
                    if (f.c < 0.0)                                     // sank onto a surface
                    {
                        float po = pendOd * _Skin.z;
                        float a = 1.0 - exp(-po);
                        acc += T * a / max(pendOd, 1e-9) * pendL;
                        T *= 1.0 - a;
                        // 2) refine the crossing (5 bisections)
                        float lo = tPrev, hi = tm;
                        [unroll]
                        for (int b = 0; b < 5; b++)
                        {
                            float mid = 0.5 * (lo + hi);
                            if (Field(r, mid).c < 0.0) hi = mid; else lo = mid;
                        }
                        tHit = hi;
                        hit = true;
                        break;
                    }
                    tPrev = tm;
                }
                float farW = 0.0;
                if (!hit)
                {
                    // the far deck: the field at the mean-height plane, + the average rim
                    tHit = clamp((r.ro.y - (r.top + _MarchRange.z)) / r.vy, tEnd, 16000.0);
                    farW = 1.0;
                }

                // 3) the surface at the hit
                DeckSample h = Field(r, tHit);
                float tau = MoonTau(h);
                float phS = 1.0 + (phase - 1.0) * _Phase.w;
                float moonS = _MoonE * (_Surf.z * h.d.a * exp(-tau * _Surf.w) + _Surf.y * phS * exp(-tau)
                                        + _Ms.x * exp(-tau * _Ms.y));
                float rim = _Ms.z * _MoonE * phase * exp(-_Skin.w * (h.amp * h.d.g * _TauMax.x + h.m.g * _TauMax.y)) * farW;
                float var = lerp(_AmpRange.z, _AmpRange.w, h.m.a);
                float3 surf = ((moonS + rim) * _MoonColor.rgb + (_AmbK * h.d.b) * _AmbColor.rgb) * var
                            + _CrevGlow.rgb * h.crev;                  // the white's own mist on the crevasse floor
                acc += T * surf;

                // fog at the hit distance
                float3 fogC = LanbaiGateFogColour(r.V, tHit, moonD, (half)_FogDensity.z, 0.0);
                float fog = 1.0 - exp(-_FogDensity.x * _FogDensity.y * tHit);
                float3 c = acc * _Gain * (1.0 - fog) + fogC * fog;

                FOut o;
                o.col = half4(c, 1.0);
                // depth: the hit, but never beyond the far plane (a far-fallback point up to 16 km out would clamp to the
                // far value and the skybox, drawn after the opaques, would paint over it)
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                float tDepth = min(tHit, 0.99 * _ProjectionParams.z / max(dot(r.V, camFwd), 1e-3));
                float4 clip = UnityWorldToClipPos(r.ro + r.V * tDepth);
                o.depth = clip.z / clip.w;
                return o;
            }
            ENDCG
        }
    }
    FallBack Off
}
