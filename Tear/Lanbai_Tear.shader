// v4 (gate round 3, 2026-10-01, UNCOMPILED): flaps = sky-coloured outer face (_OuterSky), dim inner face
// (0.15 + 0.6 R), sheen 0.5, fold bleed 0.15, rim only on the rolled edge; depth prepass x CloudFootFade; halo
// per-card gain UV2.x. Lens / rips / folds / fibres textures regenerated (README_Tear v4).
// =====================================================================================================
//  v3 (gate round 2, 2026-10-01; UNCOMPILED): the foot fades into the cloud top (Lens / Folds / Halo: global
//  _Udon_CloudTop, 40 m ragged fade, nothing below it: no ruler-straight foot over the cloud sea in front);
//  Halo / Folds: card-edge fade smoothstep(1, 0.75, 2 max(|u-.5|, |v-.5|)) (no visible rectangle); Flap: the moon
//  outline only on the LEFT flaps (uv.y < 0.5: the moon side), desaturated (C* <= 20), inner face 0.45 + 1.35 R;
//  CloudGlow x the shadow lanes of the ring roots (_LanesTex = Tear_CloudLanes_1024.png, _LanesRect).
//  Lanbai / Tear      蓝白 · 裂口套件 v2 (art bible §6·4, §8.1 #6)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). UNCOMPILED. The implementer compiles and checks it. !!!
//
//  ONE shader for every part of the tear kit; each material picks its part with the "Part" dropdown
//  (keyword _PART_*) and sets the blend state + render queue from the table in README_Tear.md §4:
//
//    part        mesh (Tear_Kit.fbx)        texture                        blend (Src/Dst)        ZWrite  queue
//    Lens        Tear_Lens                  Tear_Emission_2048x512         One / OneMinusSrcAlpha  Off    2994  (+ depth prepass)
//    Rip         Tear_Rip_Branch_A, Tear_Rip_Branch_B     Tear_Rip_1024x128              One / OneMinusSrcAlpha  Off    2995
//    Flap        Tear_Flap_L1..R2           Tear_Flaps_1024 (linear)       One / Zero (cutout+A2C) On     2450
//    Fibre       Tear_Fibres                Tear_Fibres_1024 (linear)      One / One               Off    2996
//    Halo        Tear_Halo                  Halo_512                       One / One               Off    2992
//    Shaft       Tear_Shafts / ShaftCard    Shaft_Gradient_256x1024 (lin.) One / One               Off    2998
//    Folds       Tear_SkyFolds              Tear_SkyFolds_1024             One / OneMinusSrcAlpha  Off    2990
//    CloudGlow   Tear_CloudGlow             Halo_512                       One / One               Off    2988
//
//  Colours are bible FILLS (scene-linear values that land on the bible's screen targets under the S4 grade).
//  Every part is a sky object: no Unity fog (bible §1.6 "天上的东西不吃雾"); optional own attenuation _Atten.
//
//  Udon-facing globals (VRCShader.SetGlobalFloat; the _Udon_ prefix is required for globals in VRChat):
//    _Udon_TearOpen     0..1   lens width 18 % -> 30 % of H (U6 0, U7 0.33, U8+ 1). Moves flaps/fibres/rips with the lips.
//    _Udon_RipProgress  0..1   the two branch rips open along their length (rip A over 0..0.75, rip B over 0.25..1:
//                              baked per mesh in UV2). Drive 0 -> 1 over ~16 s from U7 (bible: each 10-16 s, <= 0.5 deg/s).
//    _Udon_TearHide     0..1   0 = visible (default: an unset global reads 0), 1 = gone. Fade-in at U6 = 1 -> 0.
//    _Udon_TearBreath   -1..1  OPTIONAL phase override for the halo breathing. Leave unset: the shader breathes on
//                              its own (±0.25 EV, 8 s sine, bible). If set non-zero it REPLACES the internal sine.
//
//  Per-vertex data contract (Tear_Kit.fbx; keep Mesh Compression Off and Generate Lightmap UVs OFF - it would
//  overwrite UV2 = TEXCOORD1):
//    TEXCOORD0  texture UV
//    TEXCOORD1  x = a_hinge: across offset (m, at full opening) of the point the vertex hangs from; y = phase 0..1
//    TEXCOORD2  rips: x/y = _Udon_RipProgress window; shafts: x = half-width (m), y = length (m)
//    COLOR      flaps: R = tear light on the inner face, G = on the outer face, B = fold -> torn edge, A = flutter
//               shafts: RGB = beam axis in object space * 0.5 + 0.5
//    NORMAL     flaps: the OUTER face normal (import Normals = Import); others: unused
// =====================================================================================================
Shader "Lanbai/Tear"
{
    Properties
    {
        [KeywordEnum(Lens, Rip, Flap, Fibre, Halo, Shaft, Folds, CloudGlow)] _Part ("Part", Float) = 0
        _MainTex ("Texture (see header table)", 2D) = "black" {}
        [HDR] _Tint ("Tint (Halo/Folds: white; Shaft: beam fill; CloudGlow: #696F8D)", Color) = (1, 1, 1, 1)
        _Intensity ("Intensity", Float) = 1
        _EmissionScale ("Emission scale (Lens/Rip PNG = fill / 4)", Float) = 4

        [Header(Tear frame (object space of Tear_Root))]
        _TearAcrossOS ("Across axis (+ = right as seen from the bus)", Vector) = (-0.99756, -0.06976, 0, 0)
        _TearAxisOS ("Lens axis (up, tilted 4 deg)", Vector) = (-0.06976, 0.99756, 0, 0)
        _OpenMin ("Width at _Udon_TearOpen = 0 (fraction of full)", Float) = 0.6

        [Header(Own attenuation (sky object, optional))]
        _Atten ("Attenuation per m (0 = off)", Float) = 0
        _HazeColor ("Haze fill (band next to the tear)", Color) = (0.1356, 0.1413, 0.2051, 1)

        [Header(Rip)]
        _RipFront ("Running-front length (0..1 of the rip)", Float) = 0.1

        [Header(Flap: indigo silk)]
        _FlapOuterNear ("Outer face at the fold (#141726 screen)", Color) = (0.0181, 0.0198, 0.0342, 1)
        _FlapOuterFar ("Outer face at the torn edge (#0C0E18 screen)", Color) = (0.0090, 0.0098, 0.0135, 1)
        _FlapInner ("Inner face, tear-lit (#3E3C66 screen)", Color) = (0.1076, 0.0908, 0.2238, 1)
        [HDR] _MoonRim ("Moon outline (#A9C2FF screen)", Color) = (0.9355, 1.1194, 4.7848, 1)
        _MoonRimMul ("Moon outline strength", Range(0, 1)) = 0.5
        _OutlinePx ("Moon outline width (px)", Range(0.5, 3)) = 1.5
        [HDR] _LipGlow ("Lip glow (#C0B9E4 screen)", Color) = (1.1612, 0.9385, 2.0562, 1)
        _SheenMul ("Silk sheen (x inner)", Float) = 0.5
        _OuterSky ("v4: outer face = the sky colour (LanbaiBand / _HazeColor) x this", Range(0, 1.5)) = 0.94
        _FoldBleed ("v4: lip glow bleeding through the fold", Range(0, 1)) = 0.15
        _FlutterAmp ("Flutter amplitude (m)", Float) = 2.0
        _Cutoff ("Cutout", Range(0, 1)) = 0.5

        [Header(Fibre)]
        [HDR] _FibreRoot ("Fibre root (#E2E8F3 screen)", Color) = (2.1758, 2.3332, 2.9485, 1)
        [HDR] _FibreTip ("Fibre tip (lip glow x0.75)", Color) = (0.8709, 0.7039, 1.5422, 1)
        _SwayAmp ("Sway amplitude (m at the tip)", Float) = 0.8
        _SwayHz ("Sway frequency (Hz)", Float) = 0.3

        [Header(Halo breathing)]
        _BreathEV ("Breathing (+- EV)", Float) = 0.25
        _BreathPeriod ("Breathing period (s)", Float) = 8

        [Header(Shaft)]
        _SoftFade ("Soft depth fade (m)", Float) = 40
        _EdgeFadePow ("Side-view fade power", Float) = 2
        _NearFadeM ("Near fade from .. to (m)", Vector) = (60, 460, 0, 0)

        [Header(v3 cloud top and lanes)]
        _CloudFadeM ("Foot fade above the cloud top (m)", Float) = 40
        _LanesTex ("CloudGlow: shadow lanes (Tear_CloudLanes_1024, linear)", 2D) = "white" {}
        _LanesRect ("Lanes rect, tear frame m: x0, x1, y0 (toward the bus), y1", Vector) = (-2000, 2000, -2400, 1600)
        _RimDesat ("Flap moon outline desaturation", Range(0, 1)) = 0.55

        [Header(Depth prepass: Lens only)]
        [Toggle] _DepthPrepass ("Write depth where the white is opaque", Float) = 0

        [Header(Render state)]
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 10
        [Enum(Off, 0, On, 1)] _ZWrite ("ZWrite", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
        [Enum(Off, 0, On, 1)] _AlphaToMask ("Alpha to coverage (Flap: On)", Float) = 0
    }

    CGINCLUDE
    #include "UnityCG.cginc"
    #include "LanbaiVR.cginc"

    sampler2D _MainTex; float4 _MainTex_ST;
    float4 _Tint; float _Intensity, _EmissionScale;
    float4 _TearAcrossOS, _TearAxisOS; float _OpenMin;
    float _Atten; float4 _HazeColor;
    float _RipFront;
    float4 _FlapOuterNear, _FlapOuterFar, _FlapInner, _MoonRim, _LipGlow;
    float _MoonRimMul, _OutlinePx, _SheenMul, _FlutterAmp, _Cutoff, _OuterSky, _FoldBleed;
    float4 _FibreRoot, _FibreTip; float _SwayAmp, _SwayHz;
    float _BreathEV, _BreathPeriod;
    float _SoftFade, _EdgeFadePow; float4 _NearFadeM;
    float _DepthPrepass;
    float _CloudFadeM, _RimDesat; float4 _LanesRect; sampler2D _LanesTex;
    float4 _Udon_CloudTop;     // global: x = world y of the cloud-sea top this frame; w > 0 = set

    float Hash3(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
    float VNoise(float3 x)
    {
        float3 i = floor(x); float3 f = frac(x); f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(Hash3(i), Hash3(i + float3(1, 0, 0)), f.x), lerp(Hash3(i + float3(0, 1, 0)), Hash3(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(Hash3(i + float3(0, 0, 1)), Hash3(i + float3(1, 0, 1)), f.x), lerp(Hash3(i + float3(0, 1, 1)), Hash3(i + float3(1, 1, 1)), f.x), f.y), f.z);
    }
    // 0 below the cloud top, ragged 40 m ramp above it (the white tears INTO the cloud sea)
    float CloudFootFade(float3 posWS)
    {
        if (_Udon_CloudTop.w <= 0.0) return 1.0;
        float z = posWS.y - _Udon_CloudTop.x + (VNoise(posWS / 22.0) - 0.5) * 36.0;
        return smoothstep(4.0, 4.0 + _CloudFadeM, z);
    }
    float CardEdge(float2 uv)
    {
        float e = 2.0 * max(abs(uv.x - 0.5), abs(uv.y - 0.5));
        return 1.0 - smoothstep(0.75, 1.0, e);
    }

    // Udon globals (never set = 0)
    float _Udon_TearOpen, _Udon_RipProgress, _Udon_TearHide, _Udon_TearBreath;

    struct appdata
    {
        float4 vertex : POSITION;
        float3 normal : NORMAL;
        float4 color : COLOR;
        float2 uv0 : TEXCOORD0;
        float2 uv1 : TEXCOORD1;
        float2 uv2 : TEXCOORD2;
        UNITY_VERTEX_INPUT_INSTANCE_ID
    };

    // bible: width 18 % -> 30 % of H. Meshes are modelled at 30 %; every vertex moves with the point it hangs from.
    float3 TearOpenOffset(appdata v)
    {
        float w = lerp(_OpenMin, 1.0, saturate(_Udon_TearOpen));
        return _TearAcrossOS.xyz * (v.uv1.x * (w - 1.0));
    }
    ENDCG

    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" "PreviewType" = "Plane" }

        // ------------------------------------------------------------------ depth prepass (Lens: _DepthPrepass = 1)
        // Writes depth only where the undyed white is opaque, so cloud cards BEHIND the tear cannot paint over it.
        Pass
        {
            Name "TEARDEPTH"
            ColorMask 0
            ZWrite On
            Cull Off
            CGPROGRAM
            #pragma vertex vertD
            #pragma fragment fragD
            #pragma target 3.5
            #pragma multi_compile_instancing
            struct v2fD { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float3 posWS : TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };
            v2fD vertD(appdata v)
            {
                v2fD o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2fD, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 p = v.vertex.xyz + TearOpenOffset(v);
                o.pos = UnityObjectToClipPos(float4(p, 1));
                o.posWS = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                o.uv = v.uv0;
                return o;
            }
            fixed4 fragD(v2fD i) : SV_Target
            {
                // v4 (tech minor): no depth below the cloud top where nothing is drawn (it cut later cards away)
                float a = tex2D(_MainTex, i.uv).a * _DepthPrepass * (1.0 - saturate(_Udon_TearHide)) * CloudFootFade(i.posWS);
                clip(a - 0.5);
                return 0;
            }
            ENDCG
        }

        // ------------------------------------------------------------------ colour
        Pass
        {
            Name "TEAR"
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            ZTest LEqual
            Cull [_Cull]
            AlphaToMask [_AlphaToMask]

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile _ SOFTPARTICLES_ON
            #pragma shader_feature_local _PART_LENS _PART_RIP _PART_FLAP _PART_FIBRE _PART_HALO _PART_SHAFT _PART_FOLDS _PART_CLOUDGLOW

            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 data : TEXCOORD1;      // uv1.xy, uv2.xy
                float4 color : TEXCOORD2;
                float3 posWS : TEXCOORD3;
                float3 nrmWS : TEXCOORD4;
                float4 projPos : TEXCOORD5;
                float4 fade : TEXCOORD6;      // x = shaft fades, y = breathing gain
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 p = v.vertex.xyz + TearOpenOffset(v);
                float t = _Time.y;
                o.fade = float4(1, 1, 1, 1);

            #if defined(_PART_FLAP)
                // slow flutter, growing toward the torn edge (bible: giants move <= 0.5 deg/s; 2 m at >= 0.5 km is tiny)
                float ph = v.uv1.y * 6.2832 + v.uv0.x * 4.0;
                p += normalize(v.normal) * (_FlutterAmp * v.color.a * sin(t * 0.5236 + ph));    // 12 s period
            #endif
            #if defined(_PART_FIBRE)
                // 0.3 Hz sway (bible), bending more toward the tip; fibres run across, so sway along the axis
                float s = v.uv0.y * v.uv0.y;
                p += _TearAxisOS.xyz * (_SwayAmp * s * sin(6.2832 * (_SwayHz * t + v.uv1.y)));
            #endif
            #if defined(_PART_SHAFT)
                // beam billboard: each cross-section's two centre-line vertices are pushed apart across the view.
                // The beam axis rides in COLOR.rgb (object space, *0.5+0.5): normals cannot carry it through FBX.
                float3 axisOS = normalize(v.color.rgb * 2.0 - 1.0);
                float3 camOS = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1)).xyz;
                float3 toCam = camOS - p;
                float3 side = normalize(cross(axisOS, toCam) + 1e-6);
                p += side * ((v.uv0.x - 0.5) * 2.0 * v.uv2.x);
                // side-view fade (LanbaiEdgeOnFade for an axial billboard) and near-eye fade
                float3 axisWS = normalize(mul((float3x3)unity_ObjectToWorld, axisOS));
                float3 pw = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                float3 V = normalize(_WorldSpaceCameraPos - pw);
                float perp = length(cross(axisWS, V));
                o.fade.x = pow(saturate(perp * 1.4), _EdgeFadePow) * LanbaiNearFade(pw, _NearFadeM.x, _NearFadeM.y);
            #endif
            #if defined(_PART_HALO)
                // breathing +-0.25 EV, 8 s sine; the outer cards lag a little (uv1.y) like a breath spreading
                float sn = (_Udon_TearBreath != 0) ? _Udon_TearBreath : sin(6.2832 * (t / _BreathPeriod - v.uv1.y));
                o.fade.y = exp2(_BreathEV * sn);
            #endif

                o.pos = UnityObjectToClipPos(float4(p, 1));
                o.posWS = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                o.nrmWS = UnityObjectToWorldNormal(v.normal);
                o.uv = v.uv0;
                o.data = float4(v.uv1, v.uv2);
                o.color = v.color;
                o.projPos = ComputeScreenPos(o.pos);
                o.projPos.z = -UnityObjectToViewPos(p).z;         // eye depth of the DEFORMED vertex (not v.vertex)
                return o;
            }

            // own distance attenuation (sky objects): premultiplied colour toward the haze
            float3 Atten(float3 rgb, float a, float3 posWS)
            {
                float T = exp(-distance(posWS, _WorldSpaceCameraPos) * _Atten);
                return rgb * T + _HazeColor.rgb * a * (1 - T);
            }

            float4 frag(v2f i, fixed facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float show = 1.0 - saturate(_Udon_TearHide);
                float2 uv = i.uv;

            #if defined(_PART_LENS)
                // premultiplied: the undyed white covers the sky (A = 1), the lip glow only adds light (A = 0)
                float4 tx = tex2D(_MainTex, uv);
                float cf = CloudFootFade(i.posWS);
                float3 rgb = tx.rgb * (_EmissionScale * _Intensity) * cf;
                return float4(Atten(rgb, tx.a * cf, i.posWS), tx.a * cf) * show;

            #elif defined(_PART_RIP)
                // the crack runs along its length: a pointed front sweeps from u = 0 to 1 as its window fills
                float ws = i.data.z, we = i.data.w;
                float prog = saturate((_Udon_RipProgress - ws) / max(we - ws, 1e-3));
                float front = prog * (1.0 + 2.0 * _RipFront) - _RipFront;
                float wm = pow(saturate((front - uv.x) / _RipFront), 0.7);
                float2 uvr = float2(uv.x, 0.5 + (uv.y - 0.5) / max(wm, 1e-3));
                float4 tx = tex2D(_MainTex, uvr);
                float vis = step(0.0005, wm);
                float3 rgb = tx.rgb * (_EmissionScale * _Intensity) * vis;
                float a = tx.a * vis;
                return float4(Atten(rgb, a, i.posWS), a) * show;

            #elif defined(_PART_FLAP)
                // indigo silk, two-sided. Texture: R = distance inside the torn edge / 24 m, G = silk, B = loose threads,
                // A = cloth coverage. Vertex colour: R/G = tear light on inner/outer face, B = fold -> torn edge.
                // v4 (gate round 3): TWO thin welded flaps = the sky's own cloth peeling back. OUTER face = the sky colour
                // behind it (no halo: the cloth occludes the glow), so it vanishes against the sky and reads only where
                // it covers the white; INNER face (seen only on the rolled lip, vertex B > 0.6) wound-lit x (0.15 + 0.6 R).
                float4 tx = tex2D(_MainTex, uv);
                float silk = 0.94 + (tx.g - 0.5) * 0.5;
                float3 Vd = normalize(i.posWS - _WorldSpaceCameraPos);
            #if defined(LANBAI_FOG_INCLUDED)
                float3 skyC = LanbaiHorizon(Vd);
            #else
                float3 skyC = _HazeColor.rgb;
            #endif
                float3 outer = skyC * (_OuterSky * silk);
                float3 inner = lerp(_FlapInner.rgb, _FlapInner.rgb * 1.55, i.color.b) * ((0.15 + 0.6 * i.color.r) * silk);
                float3 col = (facing > 0) ? outer : inner;       // normals = OUTER face
                float3 V = -Vd;
                float ndv = abs(dot(normalize(i.nrmWS), V));
                col += _FlapInner.rgb * (_SheenMul * pow(1.0 - ndv, 3.0) * (0.1 + i.color.r));
                float fold = pow(saturate(1.0 - i.color.b / 0.06), 2.0);
                col += _LipGlow.rgb * (_FoldBleed * fold);
                // a 1-2 px desaturated rim ONLY along the rolled torn edge (B 0.70 -> 0.85), C* <= 20
                float distM = tx.r * 24.0;
                float px = distM / max(fwidth(distM), 1e-5);
                float ol = 1.0 - smoothstep(_OutlinePx * 0.5, _OutlinePx * 1.5, px);
                ol *= smoothstep(0.70, 0.85, i.color.b);
                float3 rimC = _MoonRim.rgb * (_MoonRimMul * 0.7);
                rimC = lerp(rimC, dot(rimC, float3(0.2126, 0.7152, 0.0722)).xxx, _RimDesat);   // C* <= 20
                col = lerp(col, rimC, ol);
                col *= _Intensity;
                // cutout + alpha-to-coverage (MSAA); the sharpened alpha keeps frayed threads from shimmering in VR
                float cov = tx.a * show * CloudFootFade(i.posWS);   // v3b: the low flaps dissolve into the cloud top too
                clip(cov - _Cutoff);
                float a2c = saturate((cov - _Cutoff) / max(fwidth(cov), 1e-4) + 0.5);
                float T = exp(-distance(i.posWS, _WorldSpaceCameraPos) * _Atten);
                return float4(lerp(_HazeColor.rgb, col, T), a2c);

            #elif defined(_PART_FIBRE)
                float4 tx = tex2D(_MainTex, uv);
                float3 col = lerp(_FibreRoot.rgb, _FibreTip.rgb, pow(saturate(uv.y), 0.8));
                float k = tx.a * 0.95 * _Intensity;
                return float4(Atten(col * k, 0, i.posWS), 0) * show;

            #elif defined(_PART_HALO)
                float4 tx = tex2D(_MainTex, uv);                  // RGB = halo fill (#8275D0) x falloff
                // v4: per-card gain in UV2.x (the inner card x 2.8: the breathing #5B57A1 1-3 deg from the lips)
                float gk = (i.data.z > 0.0) ? i.data.z : 1.0;
                float3 rgb = tx.rgb * _Tint.rgb * (_Intensity * i.fade.y * gk) * CardEdge(uv) * CloudFootFade(i.posWS);
                return float4(Atten(rgb, 0, i.posWS), 0) * show;

            #elif defined(_PART_SHAFT)
                float4 tx = tex2D(_MainTex, uv);
                float k = tx.a * i.fade.x * _Intensity;
                #if defined(SOFTPARTICLES_ON)
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.projPos)));
                    k *= saturate((sceneZ - i.projPos.z) / _SoftFade);
                #endif
                return float4(_Tint.rgb * k, 0) * show;           // _Tint = one beam's fill (#4C4A74 x 0.5)

            #elif defined(_PART_FOLDS)
                // premultiplied: RGB = tear light raking the ridges, A = the valleys shading the sky
                float4 tx = tex2D(_MainTex, uv);
                float ke = CardEdge(uv) * CloudFootFade(i.posWS);
                float3 rgb = tx.rgb * _Tint.rgb * _Intensity * ke;
                float a = tx.a * _Intensity * ke;
                return float4(Atten(rgb, 0, i.posWS), a) * show;

            #else // _PART_CLOUDGLOW
                float4 tx = tex2D(_MainTex, uv);                  // Halo_512: A = radial falloff
                // v3: the ring roots' shadow lanes. Object space (Unity) -> tear frame metres: x = -os.x S, y = -os.z S
                float S = length(unity_ObjectToWorld._m00_m10_m20);
                float3 os = mul(unity_WorldToObject, float4(i.posWS, 1)).xyz;
                float2 cf = float2(-os.x, -os.z) * S;
                float2 luv = float2((cf.x - _LanesRect.x) / (_LanesRect.y - _LanesRect.x), (cf.y - _LanesRect.z) / (_LanesRect.w - _LanesRect.z));
                float k = tx.a * _Intensity * tex2D(_LanesTex, luv).r;
                #if defined(SOFTPARTICLES_ON)
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.projPos)));
                    k *= saturate((sceneZ - i.projPos.z) / _SoftFade);
                #endif
                return float4(_Tint.rgb * k, 0) * show;
            #endif
            }
            ENDCG
        }
    }
    Fallback Off
}
