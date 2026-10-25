// =====================================================================================================
//  Lanbai / CloudVolume   (蓝白 · 共用体积云；第 6 幕先用。D-44 #2，2026-10-25)
//  !!! WRITTEN WITHOUT A UNITY COMPILER; checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//
//  Starting point: 阿白's Lanbai/Local/VolumeCloudDeck (FromLocal/full_preview/20261025-0103/review_sources, 2026-10-25):
//  a 128^3 periodic density, wind on the timeline clock, density x a layer envelope, self-shadow toward the light.
//  This version (README_Volume.md §1, §3, §5; the maths = Source/vol_ref.py, the act 6 scene = Act06_Dawn/Source/act06_vol.py):
//    * looks every way: a camera-centred proxy (inside-out box, depth-tested so the cabin hides it); the march runs between
//      the cloud slab's bounds both ways, stops at the sea plane and at the scene depth;
//    * two horizontal layers (A, B) with a baked 2-D coverage (Act06_CloudCoverage: A closed / open, B c0 / gap; mirror
//      wrapped -> the deck goes to the horizon, no edge), a height profile with a wandering base and top (no flat base,
//      review 4), Perlin-Worley shape NORMALISED to its p10..p90 (raw it barely moves in 3-D and the 2-D coverage alone
//      draws extruded blocks: review 2), Worley erosion (wispy base, crisp heads);
//    * towers from blobs (up to 3 x 40 spheres, review 1: cauliflower, no vertical plane) + up to 3 drifting puffs the
//      bus really goes through;
//    * light: one near sun sample every 2nd step + the upper layer's coverage along the sun ray (its long shadow) and
//      over the sample (sky occlusion under the cover, review 3), dual HG, ambient sky / ground by height;
//    * the fog per sample (LanbaiFog amount, LanbaiHorizon colour once per pixel) x _UnderFogK (the haze under the cover);
//    * cost: steps grow with distance (1.5 % of it, 10 .. 450 m), at most _MaxSteps, out at transmittance < 0.03; the
//      2-D coverage is read first and an empty column costs one 2-D fetch. Budget: README_Volume §3 (<= 20 3-D fetches /
//      pixel on average; 1.8 ms at 9 MP on the bible's reference machine). Not measured: 阿白's act06_test + profiler.
//  Globals: only the clock _Udon_CloudClock (x = timeline seconds, w > 0 set; written by the act's driver; README_Volume §4).
//  The gate's _Udon_CloudVolume* are for density readers (its arms); act 6 has none and does not write them (§5).
// =====================================================================================================
Shader "Lanbai/CloudVolume"
{
    Properties
    {
        _DensityTex ("Density 128^3 (R Perlin-Worley, G Worley detail, B gaps) - linear", 3D) = "gray" {}
        _NoiseLo ("Noise p10 per channel (vol_density.py)", Vector) = (0.549, 0.331, 0.251, 0)
        _NoiseHi ("Noise p90 per channel", Vector) = (0.791, 0.635, 0.711, 1)
        _CovTex ("Coverage RGBA (A closed, A open, B c0, B gap) - linear, mirror", 2D) = "black" {}
        _CovExtent ("Coverage half extent (m)", Float) = 24000
        _CovOpen ("x A open 0..1, y B open 0..1 - MPB / driver", Vector) = (0, 0, 0, 0)
        _Origin ("World origin of the act's layout (the act's R_ root moves; xyz)", Vector) = (0, 0, 0, 0)

        _A_Y ("Layer A: y0, y1 (layout), sigma (1/m), noise scale (m)", Vector) = (-1134, -533, 0.05, 1700)
        _A_Shape ("Layer A: erode, height wander, soft power, base soft", Vector) = (0.25, 0.15, 1, 0.06)
        _A_Wind ("Layer A wind m/s (xyz)", Vector) = (4, 0, 1.5, 0)
        _B_Y ("Layer B: y0, y1, sigma, scale", Vector) = (-1950, -1700, 0.04, 600)
        _B_Shape ("Layer B: erode, wander, soft power, base soft", Vector) = (0.42, 0.3, 2, 0.1)
        _B_Wind ("Layer B wind", Vector) = (3, 0, 2.5, 0)
        _B_Strato ("Layer B profile: 1 stratiform (soft both ends), 0 cumulus", Float) = 1

        _SunColor ("Sun x E in the volume (linear; act 6: the bible's shaft gold #FFD9A8)", Vector) = (3.5, 2.6, 1.7, 0)
        _SkyColor ("Ambient from above (linear)", Vector) = (0.45, 0.55, 0.77, 0)
        _GndColor ("Ambient from below (linear)", Vector) = (0.05, 0.06, 0.09, 0)
        _Phase ("HG g1, g2, mix, multiple scattering", Vector) = (0.6, -0.25, 0.7, 0.3)
        _Shadow ("x deck cast k, y sky occlusion k, z near sun sample (m), w -", Vector) = (0.6, 1.0, 120, 0)
        _UnderFogK ("Haze colour under the cover - MPB / driver", Float) = 1
        _SunDirFallback ("Sun direction when _Udon_SunDir is not set", Vector) = (0.4974, 0.1011, 0.8616, 0)
        _SeaY ("Sea plane y (layout); the march stops there", Float) = -2604.59

        _MaxSteps ("Max steps", Range(16, 160)) = 96
        _StepK ("Step = distance x this (clamped 10 .. 450 m)", Float) = 0.015
        _MaxDist ("Max distance (m)", Float) = 60000
        _NearClear ("Comfort: density x smoothstep(x, y, distance) (no billow in the face)", Vector) = (2, 18, 0, 0)
        _TowerCount ("Towers (0..3)", Float) = 0
        _PuffCount ("Drifting puffs (0..3)", Float) = 0
    }

    SubShader
    {
        Tags { "Queue" = "Transparent-20" "RenderType" = "Transparent" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Pass
        {
            Blend One OneMinusSrcAlpha
            Cull Front
            ZWrite Off
            ZTest LEqual

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 4.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #define LANBAI_FOG_ALWAYS
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            // the gate's _Udon_CloudVolume* (GateClouds/Shaders/LanbaiCloudVolume.cginc) are for things that read the cloud's
            // density (the gate's arms); act 6 has none, so this material carries its own volume and act 6 does not write them
            // (no second writer). The clock is the shared one (README_Volume §4; to be registered in Common/UdonGlobals.md).
            #ifndef LANBAI_DECL__Udon_CloudClock
            #define LANBAI_DECL__Udon_CloudClock
            float4 _Udon_CloudClock;    // x = timeline seconds, w > 0 = set (README_Volume §4)
            #endif

            sampler3D _DensityTex;
            sampler2D _CovTex;
            float4 _NoiseLo, _NoiseHi, _CovOpen, _Origin;
            float _CovExtent;
            float4 _A_Y, _A_Shape, _A_Wind, _B_Y, _B_Shape, _B_Wind;
            float _B_Strato;
            float4 _SunColor, _SkyColor, _GndColor, _Phase, _Shadow, _SunDirFallback, _NearClear;
            float _UnderFogK, _SeaY, _MaxSteps, _StepK, _MaxDist, _TowerCount, _PuffCount;
            // set from the builder with Material.SetVectorArray (not in Properties)
            float4 _TowerBox[3];      // x, z (layout), R (bounding half size), y0 (flat base)
            float4 _Blobs[120];       // 40 per tower: xyz (layout), radius; radius 0 = unused
            float4 _Puff[3];          // t_c, y_c (layout), radius, thickness
            float4 _PuffWind[3];      // xyz m/s (the puff crosses the bus column at t_c)
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 wpos : TEXCOORD0;
                float4 screen : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                // the proxy is a unit cube; it follows the eye (30 m half size: outside the cabin, inside everything else)
                float3 w = _WorldSpaceCameraPos + v.vertex.xyz * 60.0;
                o.wpos = w;
                o.pos = UnityWorldToClipPos(w);
                o.screen = ComputeScreenPos(o.pos);
                return o;
            }

            float Clock() { return _Udon_CloudClock.w > 0.0 ? _Udon_CloudClock.x : _Time.y; }

            float SS(float a, float b, float x) { float t = saturate((x - a) / (b - a)); return t * t * (3.0 - 2.0 * t); }

            float4 Cov(float2 xz)
            {
                // mirror-wrapped coverage: u, v = 0..1 over +-_CovExtent (row 0 = +z far)
                float2 uv = xz / (2.0 * _CovExtent) + 0.5;
                return tex2Dlod(_CovTex, float4(uv, 0, 0));
            }

            float CovA(float4 c) { return lerp(c.r, c.g, _CovOpen.x); }
            float CovB(float4 c) { return saturate(max(c.b, 0.97 * (1.0 - _CovOpen.y)) * (1.0 - _CovOpen.y * c.a)); }

            float NormN(float v, int ch) { return saturate((v - _NoiseLo[ch]) / max(_NoiseHi[ch] - _NoiseLo[ch], 1e-3)); }

            // one layer's density at p (layout space); y4 = (y0, y1, sigma, scale); sh = (erode, wander, soft power, base soft)
            float LayerDensity(float3 p, float c, float4 y4, float4 sh, float3 wind, float strato, float t, bool detail)
            {
                if (c <= 0.01) return 0.0;
                float k = 1.0 / y4.w;
                float h = (p.y - y4.x) / (y4.y - y4.x);
                if (sh.y > 0.0)
                {
                    float wv = NormN(tex3Dlod(_DensityTex, float4(p.x * k * 0.35, 40.0 / 128.0, p.z * k * 0.35, 0)).r, 0);
                    h += sh.y * 2.0 * (wv - 0.5);
                }
                if (h <= 0.0 || h >= 1.0) return 0.0;
                float prof = strato > 0.5 ? SS(0.0, 0.25, h) * (1.0 - SS(0.6, 1.0, h))
                                          : SS(0.0, sh.w, h) * (1.0 - SS((0.35 + 0.65 * c) * 0.6, 0.35 + 0.65 * c, h));
                float3 q = (p - wind * t) * k;
                float n0 = NormN(tex3Dlod(_DensityTex, float4(q, 0)).r, 0);
                float base = saturate((n0 * prof - (1.0 - c)) / max(c, 1e-3));
                if (detail && base > 0.0)
                {
                    float3 q2 = (p - wind * t * 1.6) * (k * 4.0);
                    float g = NormN(tex3Dlod(_DensityTex, float4(q2, 0)).g, 1);
                    float er = sh.x * (0.35 + 0.65 * (1.0 - h));
                    base = saturate((base - g * er) / max(1.0 - g * er, 1e-3));
                }
                return (sh.z != 1.0 ? pow(base, sh.z) : base) * y4.z;
            }

            float TowerDensity(float3 p, float t)
            {
                float s = 0.0;
                [loop] for (int ti = 0; ti < 3; ti++)
                {
                    if (ti >= (int)_TowerCount) break;
                    float4 b = _TowerBox[ti];
                    if (abs(p.x - b.x) > b.z || abs(p.z - b.y) > b.z) continue;
                    float f = 0.0;
                    [loop] for (int bi = 0; bi < 40; bi++)
                    {
                        float4 sp = _Blobs[ti * 40 + bi];
                        if (sp.w <= 0.0) break;
                        f = max(f, 1.0 - length(p - sp.xyz) / sp.w);
                    }
                    float shape = SS(0.0, 0.5, f) * SS(b.w, b.w + 80.0, p.y);
                    if (shape <= 0.01) continue;
                    float3 wq = p - float3(2.0, 0.0, 1.0) * t;
                    float e1 = 1.0 - tex3Dlod(_DensityTex, float4(wq / 700.0, 0)).g;     // Worley distance: high at cell borders
                    float e2 = 1.0 - tex3Dlod(_DensityTex, float4(wq / 190.0 + 31.0 / 128.0, 0)).g;
                    float base = saturate((shape - 0.55 * e1 * (1.0 - 0.4 * f) - 0.22 * e2) / 0.45);
                    s = max(s, base * 0.05);
                }
                return s;
            }

            float PuffDensity(float3 p, float t)
            {
                float s = 0.0;
                [loop] for (int i = 0; i < 3; i++)
                {
                    if (i >= (int)_PuffCount) break;
                    float4 pf = _Puff[i];
                    if (abs(p.y - pf.y) > pf.w * 0.5) continue;
                    float2 c = _PuffWind[i].xz * (t - pf.x);          // crosses the bus column (0, 0) at t_c
                    float n = NormN(tex3Dlod(_DensityTex, float4(p.x / 600.0, (91.0 + pf.x) / 128.0, p.z / 600.0, 0)).r, 0);
                    float dd = length(p.xz - c) + 0.35 * pf.z * 2.0 * (n - 0.5);
                    float cv = SS(pf.z, pf.z * 0.3, dd) * 0.75;      // = act06_vol covP_for
                    s += LayerDensity(p, cv, float4(pf.y - pf.w * 0.5, pf.y + pf.w * 0.5, 0.012, 900.0),
                                      float4(0.45, 0.0, 1.0, 0.2), _PuffWind[i].xyz, 0.0, t, true);
                }
                return s;
            }

            // total density + the height in its layer (for the ambient)
            float Density(float3 p, float t, bool detail, out float hOut)
            {
                hOut = 0.5;
                float4 c = Cov(p.xz);
                float s = 0.0;
                if (p.y >= _A_Y.x && p.y <= _A_Y.y)
                {
                    s += LayerDensity(p, CovA(c), _A_Y, _A_Shape, _A_Wind.xyz, 0.0, t, detail);
                    hOut = (p.y - _A_Y.x) / (_A_Y.y - _A_Y.x);
                }
                if (p.y >= _B_Y.x && p.y <= _B_Y.y)
                {
                    s += LayerDensity(p, CovB(c), _B_Y, _B_Shape, _B_Wind.xyz, _B_Strato, t, detail);
                    hOut = (p.y - _B_Y.x) / (_B_Y.y - _B_Y.x);
                }
                if (_TowerCount > 0.0) s += TowerDensity(p, t);
                if (_PuffCount > 0.0) s += PuffDensity(p, t);
                return s;
            }

            // the upper layer (A) over p: its long shadow along the sun ray (3 coverage reads) and the sky it hides
            float DeckT(float3 p, float3 sunD)
            {
                if (p.y >= _A_Y.y) return 1.0;
                float sy = max(sunD.y, 1e-3);
                float a = max((_A_Y.x - p.y) / sy, _Shadow.z);
                float b = (_A_Y.y - p.y) / sy;
                if (b <= a) return 1.0;
                float seg = (b - a) / 3.0, tau = 0.0;
                [unroll] for (int i = 0; i < 3; i++)
                {
                    float3 q = p + sunD * (a + (i + 0.5) * seg);
                    tau += CovA(Cov(q.xz)) * _A_Y.z * _Shadow.x * seg;
                }
                return exp(-tau);
            }

            float HG(float c, float g) { return (1.0 - g * g) / (12.566 * pow(max(1.0 + g * g - 2.0 * g * c, 1e-4), 1.5)); }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 eyeW = _WorldSpaceCameraPos;
                float3 V = normalize(i.wpos - eyeW);
                float3 eye = eyeW - _Origin.xyz;                       // layout space (the act's root moves)
                float t = Clock();

                // the slab: A, B, towers and puffs all inside [ymin, ymax]
                float ymin = min(_B_Y.x, _A_Y.x), ymax = max(_A_Y.y, _A_Y.y + 2600.0 * step(0.5, _TowerCount));
                float t0, t1;
                if (abs(V.y) < 1e-5) { t0 = (eye.y >= ymin && eye.y <= ymax) ? 0.0 : 1e9; t1 = _MaxDist; }
                else
                {
                    float ta = (ymin - eye.y) / V.y, tb = (ymax - eye.y) / V.y;
                    t0 = max(min(ta, tb), 0.5); t1 = min(max(ta, tb), _MaxDist);
                }
                if (V.y < 0.0) t1 = min(t1, (_SeaY - eye.y) / V.y);    // the sea stops it
                // the scene depth (the sea surface, anything opaque beyond the proxy)
                float2 suv = UnityStereoTransformScreenSpaceTex(i.screen.xy / i.screen.w);
                float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, suv));
                float eyeRate = max(1e-4, -mul((float3x3)UNITY_MATRIX_V, V).z);
                t1 = min(t1, sceneZ / eyeRate);
                if (t1 <= t0) discard;

                float3 sunD = LanbaiSunDir(_SunDirFallback.xyz);
                float cosv = dot(V, sunD);
                float ph = (_Phase.z * HG(cosv, _Phase.x) + (1.0 - _Phase.z) * HG(cosv, _Phase.y)) * 12.566;
                float3 fogC = LanbaiHorizon(V) * _UnderFogK;
                // interleaved gradient noise (screen; no TAA in VRChat): the start jitter does not swim with the eye
                float2 px = i.screen.xy / i.screen.w * _ScreenParams.xy;
                float ign = frac(52.9829189 * frac(dot(px, float2(0.06711056, 0.00583715))));

                float3 Lo = 0.0;
                float T = 1.0;
                float d = t0 + ign * clamp(t0 * 0.01, 4.0, 60.0);
                float sunT = 1.0;
                [loop] for (int s = 0; s < 160; s++)
                {
                    if (s >= (int)_MaxSteps || d >= t1 || T < 0.03) break;
                    float dt = clamp(d * _StepK, 10.0, 450.0);
                    float3 p = eye + V * (d + 0.5 * dt);
                    float h;
                    float sig = Density(p, t, true, h) * SS(_NearClear.x, _NearClear.y, d);
                    if (sig > 1e-5)
                    {
                        if ((s & 1) == 0)                              // the near sun sample every 2nd step
                        {
                            float hs;
                            sunT = exp(-Density(p + sunD * _Shadow.z, t, false, hs) * _Shadow.z) * DeckT(p, sunD);
                        }
                        float occ = (p.y < _A_Y.x) ? CovA(Cov(p.xz)) : 0.0;
                        float3 amb = lerp(_GndColor.rgb, _SkyColor.rgb, h) * (1.0 - _Shadow.y * occ);
                        float ms = 1.0 + _Phase.w * (1.0 - exp(-sig * 200.0));
                        float3 src = _SunColor.rgb * (sunT * ph * ms * 0.25) + amb;
                        float fa = LanbaiFogAmount(eyeW + V * d, eyeW);
                        src = lerp(src, fogC, fa);
                        float a = 1.0 - exp(-sig * dt);
                        Lo += T * a * src;
                        T *= 1.0 - a;
                    }
                    d += dt;
                }
                if (T > 0.999) discard;
                return half4(Lo, 1.0 - T);
            }
            ENDCG
        }
    }
    FallBack Off
}
