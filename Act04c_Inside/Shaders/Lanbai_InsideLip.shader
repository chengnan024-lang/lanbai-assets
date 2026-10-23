// =====================================================================================================================
//  Lanbai / InsideLip        蓝白 · 第 4c 幕（门内）：撕开的布、光唇的毛边、横纱、穹、前方的暖白点、松散的丝线
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; slang syntax check only). Compile in Unity 2022.3 + VRChat SDK. !!!
//
//  One shader, the part is picked by the material's Part enum (keyword _PART_*):
//    SHEET   opaque cloth with the opening (ZWrite On, Cull Off). The inner face of the torn cloth #1A2030 with vertical
//            fibre streaks (world-scaled weave texture); a "lip glow" along the torn edge (UV1.x = metres to the edge).
//    FRINGE  the torn weft ends round the opening (additive, ZWrite Off). UV0.x = metres along the edge / tile, UV0.y = 0 at the
//            cloth .. 1 at the longest fibre tip. Mip-mapped texture: far fibres average to a soft line, never sparkle.
//    THREAD  the unbroken dark weft threads across the narrow ends (premultiplied alpha): dark core, lit rim.
//    DOME    the 2.4 km sphere round the bus (inside faces, ZWrite On): the colour of the fog at infinity.
//    DOT     the warm white point ahead (a sky object: no fog; billboard to the eyes' midpoint; additive).
//    LOOSE   the 90 loose threads drifting toward the path axis round the bus (bus-anchored, vertex animated).
//
//  Globals (Udon, `_Udon_` prefix; see Act04c_Inside/给总控.md for the registration request):
//    _Udon_InsidePortal   x = world z of the tear plane, y = 1 while the portal is armed. While the eye is still in front
//                         of the plane every vertex of this shader is collapsed: the gate looks exactly as before U9.
//    _Udon_InsideFog      rgb = the fog colour (linear fill) of the current zone (the dome draws it), a = density
//    _Udon_InsideDot      x = core diameter (deg), y = glow diameter (deg), z = gain (0..1), w = 0
//    _Udon_InsideFibre    rgb = the current fibre colour (linear fill) for the loose threads, a = gain
//    _Udon_InsideClock    x = clock (s) for the loose threads (the driver freezes it at U12 - 2.25)
//  Fog: LanbaiFog.cginc (sky session; minimum interface CONTROL §4). In act 4c the driver keeps the fog band off, so
//  LanbaiHorizon() = the zone colour and RenderSettings.fogColor = the same colour.
// =====================================================================================================================
Shader "Lanbai/InsideLip"
{
    Properties
    {
        [KeywordEnum(Sheet, Fringe, Thread, Dome, Dot, Loose)] _Part ("Part", Float) = 0
        [Header(Colours are linear fills)]
        _ClothColor ("Cloth inner face (linear)", Vector) = (0.0101, 0.0133, 0.0244, 0)
        _FibreColor ("Fibre and lip colour (linear HDR)", Vector) = (2.7, 2.2, 3.9, 0)
        _Gain ("Gain", Float) = 1
        [Header(Sheet)]
        _WeaveTex ("Weave (R warp streaks, G fine weave, B blotches)", 2D) = "grey" {}
        _WeaveScale ("Weave tile size (m)", Float) = 40
        _WeaveAmount ("Weave contrast", Range(0, 1)) = 0.06
        _LipGlow ("Lip glow on the cloth (x fibre colour)", Float) = 3.15
        _LipGlowWidth ("Lip glow width (m)", Float) = 2.5
        _LipGlowFar ("Translucency band (x gain, y width m)", Vector) = (0.08, 40, 0, 0)
        _GrainRoll ("Fibre grain roll (deg, = the lip's roll)", Float) = 0
        _Folds ("Tension folds (x period along the edge m, y period away m, z amount, w falloff m)", Vector) = (48, 300, 0.25, 200)
        [Header(Fringe)]
        _FringeTex ("Fringe (R fibres, G coverage, B clump)", 2D) = "black" {}
        _FringeGain ("Fringe gain", Float) = 2.75
        [Header(Thread)]
        _ThreadRim ("Thread rim (x fibre colour)", Float) = 0.6
        _ThreadCore ("Thread core lit by the fibres (0 = dark weft, 1 = fibre lit)", Range(0, 1)) = 0
        [Header(Dot)]
        _DotCore ("Dot core (linear HDR)", Vector) = (6.92, 3.66, 1.63, 0)
        _DotGlow ("Dot glow (x core)", Float) = 0.32
        _DotHalo ("Dot halo colour (linear, less orange than the core)", Vector) = (6.92, 5.95, 4.84, 0)
        _DotDist ("Dot distance (m)", Float) = 2300
        [Header(Loose threads)]
        _LooseGain ("Loose threads (x fibre colour)", Float) = 0.25
        _LooseWidth ("Width (m)", Float) = 0.008
        [Header(Fog)]
        _FogCap ("Fog cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog height falloff (m, 0 = off)", Float) = 0
        [Header(Blend set by the build script)]
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst", Float) = 0
        [Enum(Off, 0, On, 1)] _ZWrite ("ZWrite", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            Cull [_Cull]

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma shader_feature_local _PART_SHEET _PART_FRINGE _PART_THREAD _PART_DOME _PART_DOT _PART_LOOSE
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"         // every _Udon_ global, declared once (chief engineer r1 #5)
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            float4 _ClothColor, _FibreColor;
            float _Gain;
            sampler2D _WeaveTex;
            float _WeaveScale, _WeaveAmount, _LipGlow, _LipGlowWidth;
            float4 _LipGlowFar;
            float _GrainRoll;
            float4 _Folds;
            float _ThreadCore;
            float4 _DotHalo;
            sampler2D _FringeTex;
            float _FringeGain, _ThreadRim;
            float4 _DotCore;
            float _DotGlow, _DotDist, _LooseGain, _LooseWidth;

            // registered (D-16) but not yet in the generated LanbaiGlobals.cginc: same guard, so the regenerated file wins
            #ifndef LANBAI_DECL__Udon_InsideGrade
            #define LANBAI_DECL__Udon_InsideGrade
            float4 _Udon_InsideGrade;
            #endif


            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 color : COLOR;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                float2 uv3 : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float4 uv : TEXCOORD0;        // xy = uv0, zw = uv1
                float3 wpos : TEXCOORD1;
                float4 col : TEXCOORD2;
                float4 aux : TEXCOORD3;       // part-specific
                UNITY_VERTEX_OUTPUT_STEREO
            };

            // ---------------------------------------------------------------------------------- helpers
            float3 FacingRight(float3 c, float3 eye)
            {
                float3 f = normalize(c - eye);
                float3 r = cross(float3(0, 1, 0), f);
                return normalize(r);
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.uv = float4(v.uv0, v.uv1);
                o.col = v.color;
                o.aux = float4(v.uv2, v.uv3);
            #if defined(_PART_DOT)
                // billboard about the object origin. r07 (art review r06 S1): _Udon_InsideDot.y is the glow RADIUS (brief:
                // 4 deg at LIP4 -> 12 deg), the core x stays a diameter; the halo is an exp tail with no hard edge
                float3 c = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float3 eye = LanbaiCentreEyePos();
                float3 f = normalize(c - eye);
                float3 r = normalize(cross(float3(0, 1, 0), f));
                float3 u = cross(f, r);
                // r07: the halo is glare, never cut by the cloth in front of the dot: the billboard is drawn 40 m out along
                // the dot's direction at the same angular size (in front of every sheet, whose openings keep >= 40 m
                // clear of the path; behind the cabin, so the bus still hides it). The core's sightline through every
                // opening is checked by the layout (Tools~/inside_layout.py, from LIP4 + 2 s).
                float d = 40.0;
                c = eye + f * d;
                float halfG = d * tan(radians(max(_Udon_InsideDot.y, 0.01)));
                wp = c + (r * v.uv0.x + u * v.uv0.y) * 2.0 * halfG;          // uv0 in -0.5 .. 0.5
                o.aux = float4(v.uv0 * 2.0, 0.5 * _Udon_InsideDot.x / max(_Udon_InsideDot.y, 0.01), 0);
            #elif defined(_PART_LOOSE)
                // uv0 = (along 0..1, side -1/1); uv1 = (phase s, radial speed m/s); uv2 = (r0 m, angle rad); uv3 = (z0 m, length m)
                // color = (axis dir xyz * 0.5 + 0.5, brightness). Round the path axis (the bus's z axis), bus-anchored:
                // review r1: "drift toward the centre" = toward the far centre ahead (the Lichtchen): each thread drifts
                // forward and only slightly in toward the axis, fades in behind and out ahead, then is reborn behind.
                // The driver slows the clock to a stop by U12 - 2.25 (the drift eases to 0, it does not freeze).
                float period = 40.0;
                float age = frac((_Udon_InsideClock.x + v.uv1.x) / period);
                float r = v.uv2.x * (1.0 - 0.25 * age);
                float len = v.uv3.y;
                float ang = v.uv2.y + 0.15 * sin(_Udon_InsideClock.x * 0.21 + v.uv1.x);
                float3 base = float3(cos(ang) * r, 1.6 + sin(ang) * r * 0.75, v.uv3.x + v.uv1.y * (age - 0.5) * period);
                float3 axis = normalize(v.color.xyz * 2.0 - 1.0);
                float3 along = axis * (v.uv0.x - 0.5) * len;
                along.y += 0.25 * len * sin(v.uv0.x * 3.14159) * sin(_Udon_InsideClock.x * 0.4 + v.uv1.x);
                float3 owp = base + along;
                wp = mul(unity_ObjectToWorld, float4(owp, 1)).xyz;
                float3 eye = LanbaiCentreEyePos();
                float3 side = normalize(cross(mul((float3x3)unity_ObjectToWorld, axis), wp - eye));
                float dist = distance(wp, eye);
                float cov;
                float extra = LanbaiInflate(_LooseWidth * 0.5, dist, 1.0, cov);
                wp += side * v.uv0.y * (_LooseWidth * 0.5 + extra);
                float life = smoothstep(0.0, 0.15, age) * (1.0 - smoothstep(0.80, 1.0, age)) * smoothstep(3.0, 5.0, r);
                o.aux = float4(cov * life * v.color.w, 0, 0, 0);
            #endif
                o.wpos = wp;
                o.pos = mul(UNITY_MATRIX_VP, float4(wp, 1.0));
                // the portal: nothing of the inside exists until the eyes have passed the tear plane. Collapsed in the
                // vertex stage (no discard: Early-Z stays on); the centre eye so both eyes switch in the same frame.
                if (_Udon_InsidePortal.y > 0.5 && LanbaiCentreEyePos().z < _Udon_InsidePortal.x - 0.7)
                    o.pos = float4(2.0, 2.0, 2.0, 1.0);
                return o;
            }

            float3 Fogged(float3 c, float3 wp)
            {
                return LanbaiApplyFog(c, wp);
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float g = _Gain * i.col.r;          // per-object gain baked into vertex colour R (sleeve plies)
                float3 gradeK = (_Udon_InsideGrade.a > 0.0) ? _Udon_InsideGrade.rgb : float3(1, 1, 1);

            #if defined(_PART_SHEET)
                float dEdge = i.uv.z;
                float uEdge = i.uv.w;
                // world-scaled weave; the grain turns with the lip (warp and weft follow the cloth, not world vertical)
                float cr = cos(radians(_GrainRoll)), sr = sin(radians(_GrainRoll));
                float2 lp = float2(cr * i.wpos.x + sr * i.wpos.y, -sr * i.wpos.x + cr * i.wpos.y);
                float4 w = tex2D(_WeaveTex, lp / _WeaveScale);
                float4 w2 = tex2D(_WeaveTex, float2(lp.x * 3.1 + 0.37, lp.y * 0.9) / _WeaveScale);
                float streak = (w.r - 0.5) * 1.6 + (w2.r - 0.5) * 0.6 + (w.g - 0.5) * 0.35;
                // r04: tension folds radiating from the torn edge (cloth pulled apart wrinkles along the pull):
                // the weave's warp streaks re-sampled along (edge, away from the edge), fading with the distance
                float fold = tex2D(_WeaveTex, float2(uEdge / _Folds.x, dEdge / _Folds.y)).r - 0.5;
                float foldK = 1.0 + 2.0 * _Folds.z * fold * exp(-dEdge / max(_Folds.w, 1.0));
                float3 cloth = _ClothColor.rgb * saturate(1.0 + _WeaveAmount * streak + 0.25 * (w.b - 0.5)) * foldK;
                // the light lives in the line: a tight glow on the cloth at the torn edge + a faint far tail
                float comb = tex2D(_FringeTex, float2(uEdge / 64.0, 0.02)).r;
                // + a faint wide band where the torn cloth thins and glows from inside (review r1: not a neon outline on
                //   a black cut-out), broken up by the weave's blotches
                float band = _LipGlowFar.x * exp(-dEdge / max(_LipGlowFar.y, 1.0)) * saturate(0.5 + 1.6 * (w.r - 0.5) + 0.3 * (w.g - 0.5));   // r02: along the warp, not blotches
                float glow = _LipGlow * exp(-dEdge / _LipGlowWidth) * (0.55 + 0.45 * comb) + band * foldK;
                float3 c = (cloth + _FibreColor.rgb * glow * g) * gradeK;
                // r07: a hidden / fading lip (the driver's _Gain = visibility, bible "<= 3 lips at once") blends into the
                // fog at infinity in this direction (the dome's colour): no pop when it appears, no ghost while hidden
                float3 dirV = normalize(i.wpos - LanbaiCentreEyePos());
                float3 res = Fogged(c, i.wpos);
                // r09 (art review r08 B2): cloth-only cues AFTER the fog (the texture fold above was averaged away by
                // mips and fog): procedural tension folds radiating from the torn edge (+-_Folds.z) and, on ~15-20 % of
                // the edge, the curled-back face: a darker band just behind the glowing rim. H from _Folds.x = 0.08 H.
                float Hm = _Folds.x / 0.08;
                // r10 (art review r09 B2): the ridges run ACROSS the tear (phase from u only; a d term drew iso-lines =
                // strata), each fold 0.05-0.12 H long and tapering
                float ph = uEdge * 6.2831853 / _Folds.x + 1.7 * sin(uEdge * 6.2831853 / (2.7 * _Folds.x));
                float fold2 = 0.65 * sin(ph) + 0.35 * sin(2.3 * ph + 1.1);
                float flen = 0.085 * Hm + 0.035 * Hm * sin(uEdge * 6.2831853 / (0.31 * Hm) + 0.7);
                float fk = 1.0 + _Folds.z * fold2 * (1.0 - smoothstep(0.0, 1.0, dEdge / flen));
                float lw = _LipGlowWidth;
                float bandIn = smoothstep(lw, lw * 1.6, dEdge) * (1.0 - smoothstep(lw + 0.005 * Hm, lw + 0.009 * Hm, dEdge));
                float cm = sin(uEdge * 6.2831853 / (0.05 * Hm)) + 0.8 * sin(uEdge * 6.2831853 / (0.017 * Hm));
                float curl = smoothstep(0.9, 1.3, cm) * bandIn;
                res *= fk * (1.0 - 0.40 * curl);
                // the hidden / fading blend comes last, so a hidden lip carries no folds (r09)
                return float4(lerp(LanbaiHorizon(dirV) * gradeK, res, saturate(_Gain)), 1.0);
            #elif defined(_PART_FRINGE)
                float4 f = tex2D(_FringeTex, i.uv.xy);
                float3 c = _FibreColor.rgb * f.r * (0.7 + 0.6 * f.b) * _FringeGain * g * i.col.g * gradeK;   // col.g: bundle gaps
                return float4(LanbaiApplyFogAdditive(c, i.wpos), 0.0);     // additive: the fog only removes light
            #elif defined(_PART_THREAD)
                float v = i.uv.y;                    // 0 .. 1 across the thread
                float edge = pow(saturate(abs(v * 2.0 - 1.0)), 6.0);
                float a = smoothstep(1.0, 0.82, abs(v * 2.0 - 1.0));
                float3 core = lerp(_ClothColor.rgb * 0.8, _FibreColor.rgb * g, _ThreadCore);
                float3 c = (core + _FibreColor.rgb * _ThreadRim * edge * g) * gradeK;
                c = Fogged(c, i.wpos);
                return float4(c * a, a);
            #elif defined(_PART_DOME)
                // the fog at infinity in this direction = LanbaiHorizon (sky session's "gradient" model in act 4c: lighter
                // ahead toward the next lips, darker behind and below)
                float3 dir = normalize(i.wpos - LanbaiCentreEyePos());
                return float4(LanbaiDitherLinear(LanbaiHorizon(dir), dir), 1.0);
            #elif defined(_PART_DOT)
                float r = length(i.aux.xy);                                     // 0 at the centre, 1 at the glow's edge
                float rc = max(i.aux.z, 1e-3);                                  // core radius as a fraction of the glow radius
                float px = fwidth(r);
                float core = 1.0 - smoothstep(rc - px, rc + px, r);
                float halo = exp(-4.5 * r) * smoothstep(1.0, 0.6, r) * (1.0 - core);   // r07: exp tail, no visible rim
                float3 c = (_DotCore.rgb * core + _DotHalo.rgb * _DotGlow * halo) * _Udon_InsideDot.z;
                return float4(c, 0.0);
            #else   // _PART_LOOSE
                float3 c = _Udon_InsideFibre.rgb * _Udon_InsideFibre.a * _LooseGain * i.aux.x;
                c *= LanbaiNearFade(i.wpos, 0.3, 1.0);
                return float4(LanbaiApplyFogAdditive(c, i.wpos), 0.0);
            #endif
            }
            ENDCG
        }
    }
    Fallback Off
}
