// =====================================================================================================
//  Lanbai / BronzeMirror   v1 (2026-10-22, cloud session 「镜与白」)   蓝白 · 十三面白铜镜（第 9 幕 9c）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Mirrors/Tools~/compile_check). !!!
//
//  One mesh (Mirrors/Models/BronzeMirror.fbx, unit diameter, LOD0/1/2) scaled by the diameter; one material per
//  mirror (13), so each mirror has its own stencil reference for the reflected-star copy (Lanbai/MirrorStars).
//  Regions by vertex colour R (spec_conventions.md §1): 0 face · 0.25 face-side rim band · 0.5 outer wall ·
//  0.75 back · 1.0 knob.
//
//  The reflected sky IS the act 9 sky (LanbaiSky.cginc: _Udon_ZenithColor star floor + LanbaiGalaxyGainAt x the shared
//  galaxy map), so a mirror never shows a different Milky Way from the one around it (README_Act09 §4, ruling D-29).
//  FACE   = reflected sky x Schlick(white bronze F0 #D6CCB4) + reflected sky x _EmissionK x _Visibility x 2^_EmitExtraEV
//           (bible §6·9: 'face emission = reflected sky x (0.2 + 0.08 k)'; mirror 13 adds +3 EV over the white's swell).
//           Convex 1.5 % (analytic sphere-cap normal), circular polish ripple +-0.02 smoothness, face texture.
//  RIM    = reflected sky x F0 #C9A873, smoothness 0.75, rim beads every 1.5 m (absolute) with footprint AA.
//  BACK   = patina #4F7A66 (dielectric, smoothness 0.35) lit only by the ambient SH (Trilight), 40 m 博局 cells
//           (absolute tiling), polar bands with absolute periods: a dark silhouette against the stars (<= #1E3B34).
//  DISSOLVE (rim -> centre, FBM in metres, clip) and APPEAR (centre -> rim) share one breakup; the front glows #CDBF9C.
//  Pass 2 writes the stencil (64 + slot) only where the FACE is visible, for the reflected stars.
//
//  No lights are read (act 9 has none but the ambient); no ForwardAdd pass (CONTROL §6 pitfall 3).
//  Fog through LanbaiFog.cginc (act 9 has fog density 0; kept for the rule in CONTROL §3).
// =====================================================================================================
Shader "Lanbai/BronzeMirror"
{
    Properties
    {
        [Header(Mirror)]
        _RadiusM ("Radius in metres (driver)", Float) = 20
        _MirrorK ("Mirror index k 1 to 13", Float) = 1
        _EmissionK ("Face emission 0.2 plus 0.08 k", Float) = 0.28
        _Visibility ("Face emission visibility 0 to 1", Range(0, 1)) = 1
        _EmitExtraEV ("Extra face emission EV (mirror 13)", Range(0, 4)) = 0
        _Appear ("Appear 0 to 1 (centre to rim)", Range(0, 1)) = 1
        _Dissolve ("Dissolve 0 to 1 (rim to centre)", Range(0, 1)) = 0
        _BreakAmp ("Breakup amplitude m", Float) = 5
        _EdgeWidth ("Glowing front width m", Float) = 0.3
        _EdgeColor ("Front glow linear rgb (#CDBF9C x 0.8)", Vector) = (0.488, 0.417, 0.266, 0)
        _RimSoft ("Far soft rim 0 to 1 (mirror 13 far)", Range(0, 1)) = 0

        [Header(Face)]
        _FaceF0 ("Face F0 linear (#D6CCB4)", Vector) = (0.672, 0.604, 0.456, 0)
        _FaceSmooth ("Face smoothness", Range(0, 1)) = 0.94
        _PolishAmt ("Polish ripple smoothness amplitude", Range(0, 0.05)) = 0.02
        _PolishPeriodM ("Polish ripple period m", Float) = 0.35
        _BronzeTone ("White bronze tone toward #CDBF9C 0 to 1", Range(0, 1)) = 1
        _ToneColor ("Tone colour linear luminance 1 (solved so S9a and S9b show #CDBF9C)", Vector) = (1.262, 0.974, 0.484, 0)
        _FaceTex ("Face texture (R smooth, G tint, B scratches, A tin bloom)", 2D) = "gray" {}

        [Header(Rim)]
        _RimF0 ("Rim F0 linear (#C9A873)", Vector) = (0.584, 0.392, 0.184, 0)
        _RimSmooth ("Rim smoothness", Range(0, 1)) = 0.75

        [Header(Back)]
        _BackAlbedo ("Back albedo linear (#4F7A66)", Vector) = (0.078, 0.195, 0.133, 0)
        _BackSmooth ("Back smoothness", Range(0, 1)) = 0.35
        _BackNormal ("Back 40 m cell normal", 2D) = "bump" {}
        _BackMask ("Back 40 m cell mask (R height, G AO, B worn, A patina)", 2D) = "white" {}
        _BackCentreNormal ("Back centre cell normal (no boss)", 2D) = "bump" {}
        _BackCentreMask ("Back centre cell mask", 2D) = "white" {}
        _Glyphs ("Inscription glyph atlas 8 x 8", 2D) = "black" {}
        _BackBump ("Back band bump strength", Range(0, 2)) = 1
        _BackAmbientGain ("Back ambient gain", Range(0, 4)) = 1
        _BackFill ("Back silhouette radiance linear (S9a/S9b show #16302A; bible max #1E3B34)", Vector) = (0.0105, 0.027, 0.0164, 0)

        [Header(Sky reflected)]
        _GlowTex ("Galaxy glow map (Sky StarSky_Glow lat-long sRGB with mips)", 2D) = "black" {}
        _SkyFloor ("Star floor if ZenithColor is not set (linear)", Vector) = (0.0027, 0.0055, 0.0205, 0)
        _GalaxyGainDefault ("Galaxy gain if the global is not set", Float) = 1

        [Header(Stencil)]
        [IntRange] _StencilRef ("Stencil ref 64 plus slot", Range(64, 127)) = 64
    }
    SubShader
    {
        Tags { "Queue" = "Geometry+20" "RenderType" = "Opaque" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Cull Off             // the eye passes THROUGH the slab at every crossing: back faces are shaded as the bronze underside (review r1 #1)
        ZWrite On
        ZTest LEqual

        CGINCLUDE
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        #include "LanbaiMirror.cginc"

        float _RadiusM, _MirrorK, _EmissionK, _Visibility, _EmitExtraEV, _Appear, _Dissolve, _BreakAmp, _EdgeWidth, _RimSoft;
        float4 _EdgeColor, _FaceF0, _RimF0, _BackAlbedo, _SkyFloor, _BackFill;
        float _BronzeTone; float4 _ToneColor;
        float _FaceSmooth, _PolishAmt, _PolishPeriodM, _RimSmooth, _BackSmooth, _BackBump, _BackAmbientGain, _GalaxyGainDefault;
        sampler2D _FaceTex, _BackNormal, _BackMask, _BackCentreNormal, _BackCentreMask, _Glyphs;
        sampler2D _GlowTex;
        float4 _GlowTex_TexelSize;

        struct appdata
        {
            float4 vertex : POSITION;
            float3 normal : NORMAL;
            float2 uv0 : TEXCOORD0;
            half4 color : COLOR;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };
        struct v2f
        {
            float4 pos : SV_POSITION;
            float3 posOS : TEXCOORD0;
            float3 posWS : TEXCOORD1;
            float3 nrmWS : TEXCOORD2;
            float2 uv0 : TEXCOORD3;
            half region : TEXCOORD4;
            UNITY_VERTEX_OUTPUT_STEREO
        };

        v2f vert(appdata v)
        {
            v2f o;
            UNITY_SETUP_INSTANCE_ID(v);
            UNITY_INITIALIZE_OUTPUT(v2f, o);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            o.posOS = v.vertex.xyz;
            o.posWS = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
            o.nrmWS = UnityObjectToWorldNormal(v.normal);
            o.pos = UnityWorldToClipPos(o.posWS);
            o.uv0 = v.uv0;
            o.region = v.color.r;
            return o;
        }

        // the reflected sky (no stars: those come from Lanbai/MirrorStars through the stencil)
        float3 MirrorSky(float3 dir, float smoothness)
        {
            float g = LanbaiMirrorGainAt(dir, _GalaxyGainDefault);
            return LanbaiMirrorSkyFloor(_SkyFloor.rgb) + g * LanbaiMirrorGalaxy(_GlowTex, _GlowTex_TexelSize, dir, smoothness);
        }

        // breakup shared by both passes: signed distance (m) to the dissolve / appear front, + kept
        float MirrorFront(float3 posOS, out float glowEdge)
        {
            float D = 2.0 * _RadiusM;
            float rM = length(posOS.xz) * D;
            float3 pM = posOS * D;
            float sdD = LanbaiMirrorDissolveSD(rM, _RadiusM, LanbaiMirrorFBM(pM), _Dissolve, _BreakAmp);
            float sdA = LanbaiMirrorAppearSD(rM, _RadiusM, LanbaiMirrorFBM(pM + 71.3), _Appear, _BreakAmp);
            float sd = min(sdD, sdA);
            float active = step(0.0005, _Dissolve) + step(_Appear, 0.9995);
            glowEdge = saturate(1.0 - sd / max(_EdgeWidth, 1e-3)) * saturate(active);
            return sd;
        }
        ENDCG

        Pass
        {
            Name "MIRROR"
            Tags { "LightMode" = "ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog

            float4 frag(v2f i, float facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float glowEdge;
                float sd = MirrorFront(i.posOS, glowEdge);
                clip(sd);

                float D = 2.0 * _RadiusM;
                float rOS = length(i.posOS.xz);
                float rM = rOS * D;
                float th = atan2(i.posOS.z, i.posOS.x);
                float3 V = normalize(i.posWS - _WorldSpaceCameraPos);     // camera -> pixel
                float footprint = max(length(fwidth(i.posOS * D)), 1e-4); // metres per pixel here
                float3x3 o2w = (float3x3)unity_ObjectToWorld;
                float3 col;

                bool under = facing < 0.0;                                // seen from inside the slab / from below
                if (i.region < 0.125 && !under)                           // ---- FACE
                {
                    float3 n = normalize(mul(o2w, LanbaiMirrorFaceNormalOS(i.posOS)));
                    half4 ft = tex2D(_FaceTex, i.uv0);
                    float ripple = sin(6.2831853 * rM / max(_PolishPeriodM, 0.01)) * saturate(1.5 - footprint / _PolishPeriodM);
                    float s = _FaceSmooth + (ft.r - 0.5) * 0.04 + _PolishAmt * ripple + ft.a * 0.01;
                    s = LanbaiSpecAA(n, saturate(s));
                    float3 r = reflect(V, n);
                    float3 sky = MirrorSky(r, s);
                    float3 f0 = _FaceF0.rgb * (1.0 + (ft.g - 0.5) * float3(0.06, 0.0, -0.06)) * (1.0 - 0.25 * ft.b);
                    f0 = lerp(f0, f0 * float3(0.97, 1.0, 1.04), ft.a * 0.5);  // tin bloom: a touch cooler
                    float3 F = LanbaiSchlick(f0, dot(n, -V));
                    col = sky * F + sky * (_EmissionK * _Visibility * exp2(_EmitExtraEV));
                    // the Milky Way in white bronze reads #CDBF9C (bible palette 09), warmer than any physical F0 makes it
                    col = dot(col, float3(0.2126, 0.7152, 0.0722)) * lerp(float3(1.0, 1.0, 1.0), _ToneColor.rgb, _BronzeTone);   // chroma from the tone only: a blue / warm mix went lavender (r3, D-21)
                }
                else if (i.region < 0.375 && !under)                      // ---- RIM BAND (beads)
                {
                    float cover;
                    float3 nOS = LanbaiMirrorBeadNormalOS(i.posOS, D, footprint, cover);
                    float3 n = normalize(mul(o2w, nOS));
                    float s = LanbaiSpecAA(n, lerp(_RimSmooth, _RimSmooth + 0.1, cover));
                    float3 sky = MirrorSky(reflect(V, n), s);
                    col = sky * LanbaiSchlick(_RimF0.rgb, dot(n, -V));
                }
                else if (i.region < 0.625 && !under)                      // ---- OUTER WALL
                {
                    float3 n = normalize(i.nrmWS);
                    float s = LanbaiSpecAA(n, _RimSmooth);
                    col = MirrorSky(reflect(V, n), s) * LanbaiSchlick(_RimF0.rgb * 0.8, dot(n, -V));
                }
                else                                                      // ---- BACK and KNOB
                {
                    // 40 m 博局 cells, absolute; the centre cell has no boss (the knob is mesh)
                    float2 cellF = i.posOS.xz * (D / LM_TLV_TILE) + 0.5;
                    float2 cuv = frac(cellF);
                    bool centre = all(floor(cellF) == float2(0.0, 0.0));
                    half4 m = centre ? tex2D(_BackCentreMask, cuv) : tex2D(_BackMask, cuv);
                    float3 tn = UnpackNormal(centre ? tex2D(_BackCentreNormal, cuv) : tex2D(_BackNormal, cuv));
                    // the cell is drawn looking at the back from below: tangent = object +X, bitangent = object +Z, normal -Y
                    float3 nOS = normalize(float3(tn.x, -tn.z, tn.y));
                    // outer polar bands: comb + rim teeth (absolute periods), and the inscription ring
                    float bandId;
                    float hb = LanbaiMirrorBandHeight(rM, _RadiusM, th, footprint, bandId);
                    float q = rM / _RadiusM;
                    float glyph = 0.0;
                    if (q >= 0.72 && q < 0.80)
                    {
                        float rowsF = floor((0.08 * _RadiusM) / 2.6);
                        float rows = max(rowsF, 1.0);
                        float rowH = (0.08 * _RadiusM) / rows;
                        float row = floor((rM - 0.72 * _RadiusM) / rowH);
                        float vIn = frac((rM - 0.72 * _RadiusM) / rowH);
                        float arc = (th + 3.14159265) * rM;
                        float idxF = floor(arc / 2.4);
                        float uIn = frac(arc / 2.4);
                        float idx = fmod(idxF + row * 7.0, 35.0);
                        float2 gcell = float2(fmod(idx, 8.0), 7.0 - floor(idx / 8.0));
                        float2 guv = (gcell + float2(uIn, vIn) * 0.84 + 0.08) / 8.0;
                        glyph = tex2D(_Glyphs, guv).r * saturate(1.5 - footprint / 0.6);
                        hb = max(hb, glyph);
                    }
                    if (q > 0.72) { m.r = hb * 0.4; m.g = lerp(1.0, 0.75, hb); m.b = hb; nOS = float3(0, -1, 0); }
                    if (i.region > 0.875) nOS = normalize(i.posOS - float3(0.0, -0.015, 0.0)); // knob: dome normal
                    if (under && i.region < 0.625) nOS = float3(0.0, -1.0, 0.0);               // the face / rim seen from inside: bronze interior, dark
                    // screen-space bump of the band heights (detail that is not in the cell texture)
                    float3 n = normalize(mul(o2w, nOS));
                    float3 dpx = ddx(i.posWS), dpy = ddy(i.posWS);
                    float dhx = ddx(hb), dhy = ddy(hb);
                    float3 rx = cross(dpy, n), ry = cross(n, dpx);
                    float det = dot(dpx, rx);
                    float3 grad = (dhx * rx + dhy * ry) / (abs(det) > 1e-12 ? det : 1e-12);
                    n = normalize(n - _BackBump * 0.02 * D * grad * saturate(1.5 - footprint / 0.5));
                    float3 amb = max(ShadeSH9(float4(n, 1.0)), 0.0) * _BackAmbientGain;
                    float3 alb = _BackAlbedo.rgb * lerp(float3(0.85, 1.0, 1.05), float3(1.15, 0.92, 0.8), m.a)   // patina patches
                                 * lerp(1.0, 0.55, m.b);                                                         // worn ridges: dark bronze
                    float s = LanbaiSpecAA(n, lerp(_BackSmooth, 0.55, m.b));
                    float3 spec = MirrorSky(reflect(V, n), s) * LanbaiSchlick(lerp(float3(0.04, 0.04, 0.04), _RimF0.rgb * 0.35, m.b), dot(n, -V));
                    // the silhouette is not black: a near-black underside overhead that dissolves into the sky would be a
                    // +3 EV brightening in under a second (flash sequence m10, r3). Held at #16302A (bible: at most #1E3B34),
                    // close to the star sky's own level, so the 2-s dissolve is nearly luminance-neutral.
                    float3 rel = alb / max(_BackAlbedo.rgb, 1e-4);
                    col = (_BackFill.rgb * rel + alb * amb) * m.g + spec * m.g;
                }

                // far soft rim (mirror 13 waiting 5-6 km below: 'a blurred giant disc'): fake transparency toward the
                // sky behind the pixel over the outer part of the disc
                if (_RimSoft > 0.0)
                {
                    float soft = smoothstep(0.80, 1.0, rOS / 0.5) * _RimSoft;
                    col = lerp(col, MirrorSky(V, 0.6), soft);
                }
                // the glowing front fades out near the eye: a dissolving mirror just overhead is seen at grazing, where a
                // 0.3 m front would smear into a wide bright ribbon (iteration r2)
                col += _EdgeColor.rgb * glowEdge * saturate((distance(i.posWS, _WorldSpaceCameraPos) - 5.0) / 20.0);
                col = LanbaiApplyFog(col, i.posWS);
                return float4(col, 1.0);
            }
            ENDCG
        }

        // ---- the stencil for the reflected stars: face only, where the face is the visible surface -------------
        Pass
        {
            Name "FACESTENCIL"
            Tags { "LightMode" = "ForwardBase" }
            ZWrite Off
            ZTest LEqual
            ColorMask 0
            Offset -1, -1
            Stencil { Ref [_StencilRef] WriteMask 127 Comp Always Pass Replace }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment fragStencil
            #pragma target 3.5
            #pragma multi_compile_instancing

            float4 fragStencil(v2f i, float facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float glowEdge;
                clip(MirrorFront(i.posOS, glowEdge));
                clip(0.125 - i.region);
                clip(facing);                                             // front of the face only
                return 0;
            }
            ENDCG
        }
    }
    Fallback Off
}
