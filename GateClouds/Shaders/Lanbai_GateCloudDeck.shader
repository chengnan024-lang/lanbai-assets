// =====================================================================================================
//  Lanbai / GateCloudDeck  v2 (gate clouds kit, 2026-10-23; cloud art team)   蓝白 · 触手之门 · 云海   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  The gate's cloud sea, seen from 40-150 m above it, out to the horizon. One big quad (GateClouds_DeckQuad, built by
//  LanbaiGateCloudsBuilder) is pulled by the vertex shader to 1.5 m under the eye (a proxy ABOVE every head, so the
//  real hit is always farther: conservative depth keeps early-Z); every pixel of it ray-marches a HEIGHT FIELD of
//  cumulus heads (two periodic tiles baked for the gate's moon by Source/deck_tiles.py) and shades it:
//    * the dense surface: Lambert toward the moon (baked N.L) x the heads' cast shadow (baked moon path) + sky x AO,
//      the cauliflower as shading (the detail tile 5x smaller), troughs darker and filled with the haze
//    * the SOFT SKIN over the heads: where a ray passes over a crest it crosses a thin lit skin -> the silver rims
//      (forward-scattered moonlight, two-lobe HG); full strength only in the MOON PATH (+-7 deg under the moon,
//      0.3-2.5 km, x 0.9) and near the tear's FOOT, 16 % elsewhere (art r1 B2, r2); skin met while the ray sinks onto a top
//      it then hits does not count (dark tops, bright silhouettes, like the Blender finals)
//    * the tear's light POOL x (1 + tint x weight x Tear_CloudLanes) (it was Tear_CloudGlow on the flat cloud-top
//      plane, which the real billows would cut to pieces: the builder turns Tear_CloudGlow / _Additive / Tear_LightLane
//      off)
//    * the crevasse: the foot of the white splits the deck (GateLayout tear.crevasse)
//    * the gate's fog (LanbaiGateSky.cginc: band + 0.35 moon aureole) at the hit distance x _FogDensity.y
//  VR comfort (bible 1.8): heads within ~56 m sideways of the bus path stay 57 m under the eye (scaled down, not cut);
//  no head rises above the eye. Steps adapt to the clearance (relaxed height-field tracing), the jitter is a hash of
//  the WORLD ray direction (both eyes agree, nothing locked to the screen), sub-pixel rims fade (no 1-px shimmer).
//
//  The numpy port Source/deck_ref.py (render_deck) is the reference: the same march, LOD, lighting, fog, defaults.
//  Cloud-sea frame: samples at (worldPos - _Udon_GateOrigin).xz, so the deck travels with GateRoot (v_g).
//  Globals (registered): _Udon_CloudTop, _Udon_GateOrigin, _Udon_MoonDir, _Udon_TearPos, _Udon_TearH, _Udon_TearFoot,
//  _Udon_InsidePortal (act 4c). Unset -> the material fallbacks.
//  Cost (deck_ref.py, key / U7 / U8): mean 15.6-24.2 march steps per pixel (p90 30-47), 2-3 fetches each, 3 bisections.
//  Includes Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc (project-root path, CONTROL_总控 §3).
// =====================================================================================================
Shader "Lanbai/GateCloudDeck"
{
    Properties
    {
        [Header(Tiles  deck_tiles.py)]
        [NoScaleOffset] _DetailTex ("Deck_Detail_1024 (R height, G moon path, B sky AO, A moon N.L); linear", 2D) = "gray" {}
        [NoScaleOffset] _MacroTex ("Deck_Macro_512 (R swell, G moon path, B amplitude, A brightness); linear", 2D) = "gray" {}
        [NoScaleOffset] _LanesTex ("Tear_CloudLanes_1024 (R 1 = lit, 0.15 = root shadow); linear", 2D) = "white" {}
        _Periods ("Periods m: detail, macro, micro scale, anisotropy max", Vector) = (1600, 6400, 5, 4)
        _DetailRange ("Detail height min, max (m); macro min, max (m)", Vector) = (-12, 56, -12, 12)
        _TauMax ("Moon path max (m): detail, macro", Vector) = (160, 400, 0, 0)
        _AmpRange ("Detail amplitude: macro B 0..1 maps to min..max; brightness min, max", Vector) = (0.3, 0.8, 0.75, 1.15)
        _Micro ("Micro: amplitude m, envelope, shading, -", Vector) = (4, 0.35, 0.9, 0)

        [Header(March)]
        _Steps ("Max steps (mean use 16-24)", Range(16, 160)) = 128
        _Adapt ("Adaptive steps: k min, k max (x t), clearance factor, slope", Vector) = (0.004, 0.05, 0.9, 0.6)
        _MarchRange ("March from (m), to (m); far mean height above the top (m); bisections", Vector) = (12, 2500, 8, 3)
        _Comfort ("Comfort: clearance under the eye (m), lane depth under the eye (m), lane half width full, gone (m)", Vector) = (2, 57, 45, 140)
        _LodBias ("LOD bias", Range(-2, 2)) = 0

        [Header(Light)]
        _MoonColor ("Moon colour #D6E4FF, linear", Vector) = (0.6724, 0.7758, 1.0, 1)
        _MoonE ("Moon radiance on the deck", Range(0, 2)) = 0.38
        _AmbColor ("Sky ambient (HazeFar), linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _AmbK ("Sky ambient x AO (round 4: 0.35, deeper troughs)", Range(0, 2)) = 0.35
        _Phase ("HG g1, g2, mix, surface lobe softening", Vector) = (0.8, -0.18, 0.62, 0.35)
        _Skin ("Skin: sigma (1/m), edge (m), approach weight, sigma toward the moon", Vector) = (0.8, 0.5, 0.0, 0.12)
        _Skin2 ("Skin: silhouette gap (x t), sub-pixel fade (x edge / footprint), commit rise (x edge), crest cover (px)", Vector) = (0.04, 3, 1, 1.5)
        _Skin3 ("Skin: silhouette ramp from, to (x gap); per-head rim min, max", Vector) = (0.5, 3, 0.4, 1.6)
        _RimVarScale ("Per-head rim noise scale (x detail period)", Float) = 0.37
        _RimWedge ("Rim wedges: moon path half angle (deg), moon path gain, foot radius (m), outside", Vector) = (7, 0.9, 600, 0.16)
        _Surf ("Surface: sigma toward the moon, forward lobe, Lambert, cast-shadow scale", Vector) = (0.14, 0.015, 0.8, 0.35)
        _Ms ("Multiple scattering: k, tau scale; far rim, -", Vector) = (0.01, 0.28, 0, 0)
        _Trough ("Troughs: coarse LOD offset, depth (m), strength, fog fraction", Vector) = (3.5, 18, 0.7, 0.4)
        _Gain ("Gain", Range(0, 3)) = 0.9

        [Header(Pool and crevasse  GateLayout clouds.pool  tear.crevasse)]
        _PoolTint ("Pool tint (dst x (1 + tint x weight)), linear; w = strength", Vector) = (0.607, 0.683, 1.144, 1.5)
        _LanesRect ("Tear_CloudLanes rect in the tear frame: x0, x1, y0 (bus side), y1 (far) m", Vector) = (-2000, 2000, -2400, 1600)
        _Crev ("Crevasse: length x S (m), half width / white half width, depth (m), lip height (m)", Vector) = (230, 0.4, 25, 5)
        _CrevGlow ("Crevasse floor glow #C0B9E4 x 0.35, linear", Vector) = (0.184, 0.170, 0.272, 1)
        _FootPool ("Foot light: radius (m), offset toward the bus (m, < 0 = beyond the foot), strength, floor under the tops  (x S / 0.64)", Vector) = (160, -100, 6.0, 0.1)
        _FootPoolColor ("Foot pool colour #E2E8F3, linear", Vector) = (0.7605, 0.8070, 0.8963, 1)
        _TearFootW ("Tear foot fallback: world xyz, w = white half width (global _Udon_TearFoot wins)", Vector) = (-0.3, -57.4, 1497.6, 76)

        [Header(Fog  LanbaiGateSky)]
        _FogDensity ("Fog density (gate 0.0006), scale, moon air", Vector) = (0.0006, 1.3, 0.35, 0)
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
        // opaque, after the arms; conservative depth (the proxy lies above every hit), so early-Z still culls it
        Tags { "Queue" = "Geometry+40" "RenderType" = "Opaque" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Cull Off ZWrite On ZTest LEqual

        CGINCLUDE
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"

            sampler2D _DetailTex;
            sampler2D _MacroTex;
            sampler2D _LanesTex;
            float4 _DetailTex_TexelSize;
            float4 _MacroTex_TexelSize;
            float4 _Periods, _DetailRange, _TauMax, _AmpRange, _Micro;
            float _Steps, _LodBias;
            float4 _Adapt, _MarchRange, _Comfort;
            float4 _MoonColor, _AmbColor, _Phase, _Skin, _Skin2, _Skin3, _RimWedge, _Surf, _Ms, _Trough;
            float _MoonE, _AmbK, _Gain, _RimVarScale;
            float4 _PoolTint, _LanesRect, _Crev, _CrevGlow, _TearFootW, _FootPool, _FootPoolColor;
            float4 _FogDensity;
            float _CloudTopY;
            float4 _GateOrigin, _RimDir;
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

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
                float3 w = mul(unity_ObjectToWorld, v.vertex).xyz;
                // the proxy: 1.5 m under THIS eye (no head rises above eye - _Comfort.x = 2 m, so every hit is farther)
                w.y = _WorldSpaceCameraPos.y - 1.5;
                o.wpos = w;
                o.pos = UnityWorldToClipPos(w);
                return o;
            }

            float CloudTop() { return (_Udon_CloudTop.w > 0.0) ? _Udon_CloudTop.x : _CloudTopY; }
            float3 GateOrigin() { return (_Udon_GateOrigin.w > 0.0) ? _Udon_GateOrigin.xyz : _GateOrigin.xyz; }

            float HG(float c, float g) { return (1.0 - g * g) / pow(max(1.0 + g * g - 2.0 * g * c, 1e-4), 1.5); }

            struct DeckRay
            {
                float3 ro, V, O;
                float top, vy, pix;
                float2 acrossDir, alongDir;    // unit horizontal axes of the pixel footprint
                float4 foot;                   // the tear's foot (world xyz, w = white half width)
                float S;                       // tear scale H / 1000
            };

            struct DeckSample
            {
                float c;          // clearance above the height field (m)
                float4 d;         // detail texel
                float4 m;         // macro texel
                float amp;
                float foot;       // footprint (m)
                float crev;       // crevasse depth x its fade toward the bus: the floor glow
            };

            // the height field at distance t (deck_ref.field). aniso = false (the march, the bisection, the depth pass):
            // tex2Dlod at the footprint's geometric-mean LOD, exactly the reference; aniso = true (the one shading sample):
            // tex2Dgrad with both footprint axes (hardware anisotropic filtering). Called with literals: no runtime branch.
            DeckSample Field(DeckRay r, float t, bool aniso)
            {
                DeckSample s;
                float3 p = r.ro + r.V * t;
                float2 cs = p.xz - r.O.xz;
                float across = max(t * r.pix, 1e-3);
                float along = min(across / max(r.vy, 0.02), across * _Periods.w);
                s.foot = sqrt(across * along);
                float lb = exp2(_LodBias);
                float2 gA = r.acrossDir * (across * lb);
                float2 gB = r.alongDir * (along * lb);
                float texD = _Periods.x * _DetailTex_TexelSize.x;
                float texM = _Periods.y * _MacroTex_TexelSize.x;
                if (aniso)
                {
                    s.d = tex2Dgrad(_DetailTex, cs / _Periods.x, gA / _Periods.x, gB / _Periods.x);
                    s.m = tex2Dgrad(_MacroTex, cs / _Periods.y, gA / _Periods.y, gB / _Periods.y);
                }
                else
                {
                    s.d = tex2Dlod(_DetailTex, float4(cs / _Periods.x, 0.0, log2(max(s.foot / texD, 1e-4)) + _LodBias));
                    s.m = tex2Dlod(_MacroTex, float4(cs / _Periods.y, 0.0, log2(max(s.foot / texM, 1e-4)) + _LodBias));
                }
                float hd = lerp(_DetailRange.x, _DetailRange.y, s.d.r);
                float hm = lerp(_DetailRange.z, _DetailRange.w, s.m.r);
                s.amp = lerp(_AmpRange.x, _AmpRange.y, s.m.b);
                // micro cauliflower: the detail tile again, _Periods.z times smaller; only near (it is gone by LOD 3.5);
                // beyond, the surface sits at the lumps' upper envelope (a skimming ray is still stopped)
                float sc = _Periods.z;
                float lodU = log2(max(s.foot * sc / (_Periods.x * _DetailTex_TexelSize.x), 1e-4)) + _LodBias;
                float mu = 0.45;
                [branch] if (lodU < 3.5)
                    mu = tex2Dlod(_DetailTex, float4(cs * sc / _Periods.x + float2(0.37, 0.61), 0.0, max(lodU, 0.0))).r;
                float fade = 1.0 - smoothstep(1.0, 3.5, lodU);
                float micro = _Micro.x * ((mu - 0.45) * fade + _Micro.y * (1.0 - fade));
                float H = r.top + hm + s.amp * (hd + micro);
                // VR comfort (bible 1.8, v <= 1.05 d): only heads within ~56 m sideways of the bus path pass close; in
                // that lane the relief is scaled down to _Comfort.y under the eye; nowhere above eye - _Comfort.x
                float lane = 1.0 - smoothstep(_Comfort.z, _Comfort.w, abs(p.x - r.ro.x));
                float cap = r.ro.y - _Comfort.x - (_Comfort.y - _Comfort.x) * lane;
                float hLow = r.top + _DetailRange.z + _DetailRange.x * _AmpRange.y;
                float hPk = r.top + _DetailRange.w + _DetailRange.y * _AmpRange.y;
                float sL = saturate((cap - hLow) / (hPk - hLow));
                if (H > hLow) H = hLow + (H - hLow) * (1.0 + (sL - 1.0) * lane);
                // the crevasse: the foot of the white splits the deck along -Z (toward the bus); before the cap (tech r2 #1)
                float al = (r.foot.z - p.z) / max(_Crev.x * r.S, 1.0);
                float hwc = max(_Crev.y * r.foot.w * (1.0 - al), 0.5);
                float ac = abs(p.x - r.foot.x) / hwc;
                float inLen = smoothstep(-0.04, 0.02, al) * (1.0 - smoothstep(0.7, 1.0, al));
                float k = (1.0 - smoothstep(0.55, 1.0, ac)) * inLen;
                float lip = exp(-(ac - 1.2) * (ac - 1.2) / 0.18) * inLen * (1.0 - al);
                H += -_Crev.z * k + _Crev.w * lip;
                H = min(H, cap);
                s.crev = k * saturate(1.0 - al);
                s.c = p.y - H;
                return s;
            }

            float MoonTauRaw(DeckSample s) { return s.amp * s.d.g * _TauMax.x + s.m.g * _TauMax.y; }   // metres of cloud

            // per-head rim factor (round 4, art r2): the detail tile's height at _RimVarScale, another offset, mip 2
            float RimVar(DeckRay r, float t)
            {
                float2 cs = (r.ro.xz + r.V.xz * t - r.O.xz) * (_RimVarScale / _Periods.x);
                float nz = tex2Dlod(_DetailTex, float4(cs + float2(0.71, 0.29), 0.0, 2.0)).r;
                return lerp(_Skin3.z, _Skin3.w, smoothstep(0.25, 0.75, nz));
            }

            // the tear's light on the deck at its foot (round 4, art r2 / r3): additive, mostly on the tops (AO^2), a radial
            // gaussian about _FootPool.y m toward the bus from the foot; also in the crest-cover shade (no dark outlines)
            float3 FootLight(DeckRay r, float3 p, float ao)
            {
                float2 dp = p.xz - float2(r.foot.x, r.foot.z - _FootPool.y * r.S / 0.64);
                float q = length(dp) / max(_FootPool.x * r.S / 0.64, 1e-3);
                return (_FootPool.z * exp(-q * q) * lerp(_FootPool.w, 1.0, ao * ao)) * _FootPoolColor.rgb;
            }

            float Hash3(float3 q) { return frac(sin(dot(q, float3(12.9898, 78.233, 37.719))) * 43758.5453); }

            #if defined(UNITY_REVERSED_Z)
                #define DECK_DEPTH SV_DepthLessEqual
            #else
                #define DECK_DEPTH SV_DepthGreaterEqual
            #endif
            struct FOut { half4 col : SV_Target; float depth : DECK_DEPTH; };


            DeckRay MakeRay(float3 wpos)
            {
                DeckRay r;
                r.ro = _WorldSpaceCameraPos;
                r.V = normalize(wpos - r.ro);
                r.vy = -r.V.y;
                r.O = GateOrigin();
                r.top = CloudTop();
                r.pix = 2.0 / (_ScreenParams.y * unity_CameraProjection._m11);
                float2 vh = r.V.xz;
                float lvh = length(vh);
                r.alongDir = (lvh > 1e-5) ? vh / lvh : float2(0.0, 1.0);
                r.acrossDir = float2(-r.alongDir.y, r.alongDir.x);
                r.foot = (_Udon_TearFoot.w > 0.0) ? _Udon_TearFoot : _TearFootW;
                r.S = ((_Udon_TearH.w > 0.0) ? _Udon_TearH.x : 640.0) / 1000.0;
                return r;
            }

            float DeckDepth(float3 ro, float3 V, float tHit)
            {
                // the hit, never beyond the far plane (a far-fallback point up to 16 km out would clamp and the skybox
                // would paint over it); always farther than the proxy (conservative depth)
                float3 camFwd = -UNITY_MATRIX_V[2].xyz;
                float tDepth = min(tHit, 0.99 * _ProjectionParams.z / max(dot(V, camFwd), 1e-3));
                // never nearer than the proxy 1.5 m under the eye (tech r2 #1: also covers a far plane < ~15 km)
                tDepth = max(tDepth, 1.5 / max(-V.y, 1e-4) * 1.001);
                float4 clip = UnityWorldToClipPos(ro + V * tDepth);
                return clip.z / clip.w;
            }
        ENDCG

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 5.0

            FOut frag(v2f i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                DeckRay r = MakeRay(i.wpos);
                if (r.vy < 1e-4) discard;                                  // only rays going down

                float3 moonD = LanbaiMoonDir(_RimDir.xyz);
                float yTop = r.top + _DetailRange.w + _DetailRange.y * _AmpRange.y;
                float yBot = r.top + _DetailRange.z + _DetailRange.x * _AmpRange.y;
                float t0 = max((r.ro.y - yTop) / r.vy, 0.0);
                float t1 = min((r.ro.y - yBot) / r.vy, 16000.0);
                float tEnd = min(t1, _MarchRange.y);
                // where a head could first be met (tech r3 #1): inside the full comfort lane (|dx| < _Comfort.z) every head
                // is _Comfort.y under the eye; outside it the march starts at _MarchRange.x (no near head skipped or cut flat)
                float ts = max(max(t0, _MarchRange.x), min(0.98 * _Comfort.y / r.vy, _Comfort.z / max(abs(r.V.x), 1e-4)));
                int N = (int)_Steps;
                // jitter: a hash of the WORLD ray direction quantised at ~1.5 pixels (stereo-consistent, world-locked)
                float jit = Hash3(floor(r.V / (r.pix * 1.5)));

                float cm = dot(r.V, moonD);
                float phase = _Phase.z * HG(cm, _Phase.x) + (1.0 - _Phase.z) * HG(cm, _Phase.y);
                float2 mh = normalize(moonD.xz + float2(1e-5, 0.0));
                float dazMoon = degrees(acos(clamp(dot(r.alongDir, mh), -1.0, 1.0)));

                float T = 1.0;
                float3 acc = 0.0;
                float3 pendL = 0.0;
                float pendOd = 0.0;
                float pendCmin = 1e9, pendTmin = 0.0;
                float3 pendBody = 0.0;
                float pendRise = 0.0;                                      // rise of the clearance since its minimum
                float tPrev = ts;                                          // cPrev is taken at ts (tech r2 #1)
                float tHit = t1;
                bool hit = false;
                float cPrev = Field(r, ts, false).c;
                float tCur = ts * (1.0 + _Adapt.x * (1.0 + 4.0 * jit)) + max(cPrev, 0.0) * _Adapt.z / (r.vy + _Adapt.w) * jit;

                // 1) adaptive march + the skin (rims), until the ray dips under the field
                [loop]
                for (int s = 0; s < 160; s++)
                {
                    if (s >= N || tPrev >= tEnd) break;
                    float tm = min(tCur, tEnd);
                    DeckSample f = Field(r, tm, false);
                    float dt = max(tm - tPrev, 0.0);
                    float ca = max(cPrev, 0.0);
                    float cb = max(f.c, 0.0);
                    float edge0 = _Skin.y;
                    float edge = edge0 + 0.35 * f.foot;
                    // exact skin column for a clearance varying linearly from ca to cb; sub-pixel rims fade
                    float dc = cb - ca;
                    float ea = exp(-ca / edge), eb = exp(-cb / edge);
                    float colm = (abs(dc) > 1e-3) ? dt * edge * (ea - eb) / dc : dt * eb;
                    float od = _Skin.x * (edge0 / edge) * colm * saturate(_Skin2.y * edge0 / f.foot);
                    float tauS = _Skin.w * MoonTauRaw(f);
                    // the rim's wedges: the moon path and the tear's foot
                    float3 pz = r.ro + r.V * tm;
                    float dh = length(pz.xz - r.ro.xz);
                    float wMoon = exp(-(dazMoon / _RimWedge.x) * (dazMoon / _RimWedge.x)) * smoothstep(200.0, 300.0, dh)
                                * (1.0 - smoothstep(2500.0, 3200.0, dh));
                    float2 df = pz.xz - r.foot.xz;
                    float wFoot = exp(-dot(df, df) / (_RimWedge.z * _RimWedge.z));
                    float gw = max(_RimWedge.w + (_RimWedge.y - _RimWedge.w) * wMoon, _RimWedge.w + (1.0 - _RimWedge.w) * wFoot);
                    float moon = _MoonE * gw * (phase * exp(-tauS) + _Ms.x * exp(-tauS * _Ms.y));
                    float3 S = moon * _MoonColor.rgb + (_AmbK * f.d.b) * _AmbColor.rgb;
                    pendOd += od;
                    pendL += od * S;
                    pendRise = max(pendRise, f.c - pendCmin);
                    if (cb < pendCmin)
                    {
                        pendCmin = cb; pendTmin = tm; pendRise = 0.0;
                        // the head's body shade here (for the part of the pixel the crest covers)
                        pendBody = (_MoonE * _Surf.z * f.d.a * exp(-_Surf.x * MoonTauRaw(f) * _Surf.w)) * _MoonColor.rgb
                                 + (_AmbK * f.d.b) * _AmbColor.rgb + FootLight(r, r.ro + r.V * tm, f.d.b);
                    }
                    // passed over a crest (the clearance has risen _Skin2.z skins above its minimum): commit the rim
                    if (f.c > pendCmin + _Skin2.z * edge)
                    {
                        float a = 1.0 - exp(-pendOd * RimVar(r, pendTmin));
                        acc += T * a / max(pendOd, 1e-9) * pendL;
                        T *= 1.0 - a;
                        // a crest closer than _Skin2.w pixels covers that part of the pixel (no stair-step)
                        float hid = 1.0 - saturate(pendCmin / max(_Skin2.w * pendTmin * r.pix, 1e-3));
                        acc += T * hid * pendBody;
                        T *= 1.0 - hid;
                        pendOd = 0.0;
                        pendL = 0.0;
                        pendCmin = 1e9;
                        pendRise = 0.0;
                    }
                    cPrev = f.c;
                    if (f.c < 0.0)                                     // sank onto a surface
                    {
                        // a silhouette if the ray came closest well before the hit; a lid if right at it
                        float rel = (tm - pendTmin) / (_Skin2.x * max(pendTmin, 1e-3));
                        // ... or one that had almost passed over (risen most of the commit height): no square-ended rims
                        float sil = max(smoothstep(_Skin3.x, _Skin3.y, rel), smoothstep(0.0, _Skin2.z * edge, pendRise));
                        float w = lerp(_Skin.z, 1.0, sil) * RimVar(r, pendTmin);
                        float a = 1.0 - exp(-pendOd * w);
                        acc += T * a / max(pendOd, 1e-9) * pendL;
                        T *= 1.0 - a;
                        // 2) refine the crossing
                        float lo = tPrev, hi = tm, clo = ca, chi = f.c;
                        int nb = (int)_MarchRange.w;
                        [loop]
                        for (int b = 0; b < 6; b++)
                        {
                            if (b >= nb) break;
                            float mid = 0.5 * (lo + hi);
                            float cm2 = Field(r, mid, false).c;
                            if (cm2 < 0.0) { hi = mid; chi = cm2; } else { lo = mid; clo = cm2; }
                        }
                        // the crossing by linear interpolation in the last interval (art review P1: no comb)
                        tHit = lo + (hi - lo) * clo / max(clo - chi, 1e-6);
                        hit = true;
                        break;
                    }
                    tPrev = tm;
                    // clearance-relaxed step, capped at _Adapt.y t except while > 4 skins above the field (no skin there)
                    float dFree = _Adapt.z * cb / (r.vy + _Adapt.w);
                    tCur = tm + clamp(dFree, _Adapt.x * tm, (f.c > 4.0 * edge) ? max(_Adapt.y * tm, dFree) : _Adapt.y * tm);
                }
                float farW = 0.0;
                if (!hit)
                {
                    // the far deck: the field at the mean-height plane
                    tHit = clamp((r.ro.y - (r.top + _MarchRange.z)) / r.vy, tEnd, 16000.0);
                    farW = 1.0;
                }

                // 3) the surface at the hit
                DeckSample h = Field(r, tHit, true);
                float tau = _Surf.x * MoonTauRaw(h);
                float phS = 1.0 + (phase - 1.0) * _Phase.w;
                float moonS = _MoonE * (_Surf.z * h.d.a * exp(-tau * _Surf.w) + _Surf.y * phS * exp(-tau)
                                        + _Ms.x * exp(-tau * _Ms.y));
                float var = lerp(_AmpRange.z, _AmpRange.w, h.m.a);
                float3 ph = r.ro + r.V * tHit;
                float2 cs = ph.xz - r.O.xz;
                // the cauliflower as shading: the detail tile's AO at the micro scale, faded with its LOD
                float lodS = log2(max(h.foot, 1e-3) * _Periods.z / (_Periods.x * _DetailTex_TexelSize.x));
                float msh = 0.75;
                [branch] if (lodS < 4.0)
                    msh = tex2Dlod(_DetailTex, float4(cs * _Periods.z / _Periods.x + float2(0.37, 0.61), 0.0, max(lodS, 0.0))).b;
                var *= 1.0 + _Micro.z * (msh - 0.75) * (1.0 - smoothstep(1.5, 4.0, lodS));
                float rim = _Ms.z * _MoonE * phase * exp(-_Skin.w * MoonTauRaw(h)) * farW;
                float3 surf = ((moonS + rim) * _MoonColor.rgb + (_AmbK * h.d.b) * _AmbColor.rgb) * var
                            + _CrevGlow.rgb * h.crev;                  // the white's own mist on the crevasse floor
                surf += FootLight(r, ph, h.d.b);
                // troughs: how far the hit lies under the local mean surface (a coarse mip) -> toward the haze
                float3 fogC = LanbaiGateFogColour(r.V, tHit, moonD, (half)_FogDensity.z, 0.0);
                float lodT = max(log2(max(h.foot, 1e-3) / (_Periods.x * _DetailTex_TexelSize.x)) + _Trough.x, _Trough.x);
                float dm = tex2Dlod(_DetailTex, float4(cs / _Periods.x, 0.0, lodT)).r;
                float hMean = r.top + lerp(_DetailRange.z, _DetailRange.w, h.m.r) + h.amp * lerp(_DetailRange.x, _DetailRange.y, dm);
                float trough = saturate((hMean - ph.y) / _Trough.y) * _Trough.z;
                surf = lerp(surf, fogC * _Trough.w, trough);
                acc += T * surf;

                // fog at the hit distance
                float fog = 1.0 - exp(-LanbaiGateDensity(_FogDensity.x) * _FogDensity.y * tHit);   // v1.6: D-22
                float3 c = acc * _Gain * (1.0 - fog) + fogC * fog;

                // the tear's light pool (GateLayout clouds.pool) in the TEAR FRAME: origin = Tear_Root (the foot is its local
                // (0.5, 0, -30), i.e. 30 S toward the bus), +y = away from the bus. Centre (0, 150 S) = BEYOND the root;
                // x Tear_CloudLanes over _LanesRect (x0, x1, y0, y1), v = (y - y0) / (y1 - y0) exactly as Lanbai_Tear (v1.5,
                // 总导演 A2: v1.4 had the centre on the bus side and the lanes ~800 m off)
                float2 root = float2(r.foot.x + 0.5 * r.S, r.foot.z - 30.0 * r.S);
                float2 cf = ph.xz - root;
                float2 pcd = cf - float2(0.0, 150.0 * r.S);
                float rr = length(pcd) / max(r.S / 0.64, 1e-3);
                float wgt = 0.75 * exp(-(rr / 420.0) * (rr / 420.0)) + 0.25 * exp(-rr / 900.0);
                float2 luv = float2((cf.x - _LanesRect.x) / (_LanesRect.y - _LanesRect.x), (cf.y - _LanesRect.z) / (_LanesRect.w - _LanesRect.z));
                if (all(luv >= 0.0) && all(luv <= 1.0))
                    wgt *= tex2Dlod(_LanesTex, float4(luv, 0.0, 0.0)).r;
                c *= 1.0 + _PoolTint.rgb * (_PoolTint.w * wgt);

                // U9: the bus is through the tear: the deck beyond the tear plane is not drawn into act 4c
                if (_Udon_InsidePortal.y > 0.5 && _WorldSpaceCameraPos.z > _Udon_InsidePortal.x && ph.z > _Udon_InsidePortal.x) discard;
                FOut o;
                o.col = half4(c, 1.0);
                o.depth = DeckDepth(r.ro, r.V, tHit);
                return o;
            }
            ENDCG
        }

        // the deck in _CameraDepthTexture (tech r1 #5 / chief engineer #5): the same height field and adaptive march, no
        // skin, light or fog; <= 48 steps, 2 bisections + the linear crossing. Soft particles, the Tear shafts / folds and
        // the cards' depth fades then see the billows. Cast Shadows stays Off on the renderer (camera depth only).
        Pass
        {
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual Cull Off ColorMask 0
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragDepth
            #pragma target 5.0

            half4 fragDepth(v2f i, out float depth : DECK_DEPTH) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                DeckRay r = MakeRay(i.wpos);
                if (r.vy < 1e-4) discard;
                float yTop = r.top + _DetailRange.w + _DetailRange.y * _AmpRange.y;
                float yBot = r.top + _DetailRange.z + _DetailRange.x * _AmpRange.y;
                float t0 = max((r.ro.y - yTop) / r.vy, 0.0);
                float t1 = min((r.ro.y - yBot) / r.vy, 16000.0);
                float tEnd = min(t1, _MarchRange.y);
                // where a head could first be met (tech r3 #1): inside the full comfort lane (|dx| < _Comfort.z) every head
                // is _Comfort.y under the eye; outside it the march starts at _MarchRange.x (no near head skipped or cut flat)
                float ts = max(max(t0, _MarchRange.x), min(0.98 * _Comfort.y / r.vy, _Comfort.z / max(abs(r.V.x), 1e-4)));
                float jit = Hash3(floor(r.V / (r.pix * 1.5)));
                float cPrev = Field(r, ts, false).c;
                float tPrev = ts;
                float tCur = ts * (1.0 + _Adapt.x * (1.0 + 4.0 * jit)) + max(cPrev, 0.0) * _Adapt.z / (r.vy + _Adapt.w) * jit;
                float tHit = 0.0;
                bool hit = false;
                int N = (int)_Steps;                                     // the same cap as the colour pass (v1.5, 总导演 A3)
                [loop]
                for (int s = 0; s < 160; s++)
                {
                    if (s >= N || tPrev >= tEnd) break;
                    float tm = min(tCur, tEnd);
                    DeckSample fs = Field(r, tm, false);
                    float c = fs.c;
                    if (c < 0.0)
                    {
                        float lo = tPrev, hi = tm, clo = max(cPrev, 0.0), chi = c;
                        [unroll]
                        for (int b = 0; b < 2; b++)
                        {
                            float mid = 0.5 * (lo + hi);
                            float cm2 = Field(r, mid, false).c;
                            if (cm2 < 0.0) { hi = mid; chi = cm2; } else { lo = mid; clo = cm2; }
                        }
                        tHit = lo + (hi - lo) * clo / max(clo - chi, 1e-6);
                        hit = true;
                        break;
                    }
                    cPrev = c;
                    tPrev = tm;
                    float dFree = _Adapt.z * max(c, 0.0) / (r.vy + _Adapt.w);
                    tCur = tm + clamp(dFree, _Adapt.x * tm, (c > 4.0 * (_Skin.y + 0.35 * fs.foot)) ? max(_Adapt.y * tm, dFree) : _Adapt.y * tm);
                }
                // out of steps before tEnd (grazing rays use all 48): the last point marched, not the far plane (tech r3 #2)
                if (!hit) tHit = (tPrev < tEnd) ? tPrev : clamp((r.ro.y - (r.top + _MarchRange.z)) / r.vy, tEnd, 16000.0);
                if (_Udon_InsidePortal.y > 0.5 && _WorldSpaceCameraPos.z > _Udon_InsidePortal.x && r.ro.z + r.V.z * tHit > _Udon_InsidePortal.x) discard;
                depth = DeckDepth(r.ro, r.V, tHit);
                return 0;
            }
            ENDCG
        }
    }
    FallBack Off
}
