// =====================================================================================================
//  Lanbai/ThinCloth   蓝白 · 窗帘（圣经 §4.5；§6·8 窗帘成翼、F10e 松开横杆朝太阳飞走、F10l + 8 s 溶进光）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + Unity 2022.3.22f1
//      CGIncludes), never compiled or looked at in Unity. !!!
//
//  Lighting (bible §4.5): wrap diffuse 0.35 + transmission saturate(dot(-N, L)) x 0.45 x albedo^2. Backlit by the
//  dawn sun it glows pale blue; by the dusk sun the mist-lilac #C3BAD2 comes from albedo^2 x the warm light (bible
//  palette colour: the D-21 guard does not touch it).
//  Plus the cabin terms of Lanbai/Cabin: tubes (constant E, curtains have no uv1) x _Udon_CabinLightmap, cabin
//  ambient, bleach, erosion (same clip and 3 cm rim, LanbaiCabinCommon.cginc), and a dissolve into light.
//  Mesh (Cabin_Curtains): uv0 = (across m, metres below the rail), vertex R = 0 at the rail -> 1 at the hem.
//  Vertex animation, all from material params the driver writes per act (LanbaiCabinDriver, one MPB):
//    _ClothClock   timeline seconds t (deterministic: the same frame for every client)
//    _Sway         x amplitude m, y frequency Hz            (night road 1.5 cm / 0.8 Hz, lift-off 4 cm)
//    _Float        x upward float m, y frequency Hz         (sea: 10-20 cm / 0.2 Hz)
//    _Wing         x spread m, y frequency Hz               (F10 942.26 -> 956: 0.30 -> 0.60 m, 0.3 -> 0.5 Hz)
//    _Release      x seconds since F10e (<= 0 = attached), y acceleration m/s^2, z max speed m/s
//    _Dissolve     x 0..1 (F10l 961.06 -> 969.06)
//  Fly direction: toward the sun, _Udon_SunDir (w > 0 = set; acts 6 / 8 driver), else _FlyDir.
// =====================================================================================================
Shader "Lanbai/ThinCloth"
{
    Properties
    {
        [Header(Cloth  bible 4.5)]
        _Color ("Base colour (sRGB) A9BCCB", Color) = (0.663, 0.737, 0.796, 1)
        _MainTex ("Colour map  fade stripes and hem  uv0 metres (optional)", 2D) = "white" {}
        _Glossiness ("Smoothness", Range(0, 1)) = 0.18
        [NoScaleOffset][Normal] _WeaveNormal ("Weave normal 0.05 m", 2D) = "bump" {}
        _WeaveScale ("Weave normal strength", Range(0, 1)) = 0.3
        _WeaveTile ("Weave tiling  1 per tile metres", Float) = 20
        _HemColor ("Hem colour 8898A8", Color) = (0.533, 0.596, 0.659, 1)
        _HemHeight ("Hem band  fraction of vertex R", Float) = 0.12
        _Wrap ("Wrap diffuse", Range(0, 1)) = 0.35
        _Transmission ("Transmission", Range(0, 1)) = 0.45
        _TubeLMConst ("Tube light E at lm 1  rgb (linear, Vector)", Vector) = (0.55, 0.62, 0.64, 1)
        _SHAmbientK ("Keep Unity SH ambient  0 = cabin ambient only", Range(0, 1)) = 0

        [Header(Motion  driver MPB)]
        _ClothClock ("Clock s", Float) = 0
        _Sway ("Sway  amp m  freq Hz", Vector) = (0, 0.8, 0, 0)
        _Float ("Float up  m  freq Hz", Vector) = (0, 0.2, 0, 0)
        _Wing ("Wing spread  m  freq Hz", Vector) = (0, 0.3, 0, 0)
        _Release ("Release  s since F10e  accel  vmax", Vector) = (0, 1.2, 6, 0)
        _FlyDir ("Fly direction fallback", Vector) = (0.5, 0.15, 0.85, 0)
        _Inward ("Into the cabin  world x sign  0 = auto from the centre line", Float) = 0
        _CentreX ("Body centre line x", Float) = -0.18
        _Dissolve ("Dissolve into light", Range(0, 1)) = 0
        _RoofLine ("Release: x roof line y (m), y clearance above it before turning, z turn radius", Vector) = (2.74, 0.35, 0.6, 0)
        _DissolveGlow ("Dissolve edge glow  linear (Vector)", Vector) = (3.0, 2.2, 1.6, 1)

        [Header(Erosion  same as Lanbai Cabin)]
        _ErodeEnable ("Erosion on", Float) = 1
        [Enum(Prose,0,Literal,1)] _ErodeForm ("Threshold form", Float) = 0
        _ErodeCoef ("Coefficients  height front skylight falloff m", Vector) = (0.45, 0.25, 0.35, 0.8)
        _ErodeNoise ("Noise  patch m  uniform lo  uniform hi  rim m", Vector) = (0.55, 0.30, 0.70, 0.03)
        _ErodeNoiseRange ("Noise range compared with tau", Vector) = (-0.20, 0.25, 0, 0)
        _FadeResist ("Resist", Float) = 0
        _RimGain ("Rim  x CabinAmbient", Float) = 1.5
        _CabinBox ("Cabin box  floor y  crown y  rear z  front z", Vector) = (0.62, 2.62, -3.65, 3.50)
        _SkyRect ("Skylight  centre xyz  half", Vector) = (0.55, 2.62, 2.80, 0.30)
        _SeatSphere ("Local seat sphere  xyz  r", Vector) = (0.55, 1.05, 2.05, 0.9)
        _FloorPatch ("Floor patch  x0 x1 z0 z1", Vector) = (-0.16, 1.04, 0.85, 2.45)
        _HoleFull ("D-26 hole full", Vector) = (0.55, 2.925, 0.45, 0.475)
        _HoleMin ("D-26 hole minimum", Vector) = (0.55, 3.04, 0.30, 0.26)
        _DoorBoxMin ("D-33 #7a door group box min xyz, w soft margin m", Vector) = (0.80, 0.45, 2.38, 0.15)
        _DoorBoxMax ("D-33 #7a door group box max xyz", Vector) = (1.60, 3.00, 3.45, 0)
        [HideInInspector] _DoorBias ("D-33 #7a door bias (driver MPB)", Float) = 0
        _HoleShape ("D-26 hole shape", Vector) = (0.22, 0.10, 0.70, 0)
        _HoleOpen ("D-26 hole open", Range(0, 1)) = 0

        [Header(Fog)]
        _FogCap ("Fog cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog height scale m  0 none", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" }
        LOD 200
        Cull Off

        CGPROGRAM
        #pragma surface surf ThinCloth vertex:vert finalcolor:ClothFinal nofog addshadow exclude_path:deferred exclude_path:prepass nolightmap nodynlightmap nodirlightmap nometa
        #pragma target 3.5
        #pragma multi_compile_fog
        #pragma skip_variants POINT_COOKIE DIRECTIONAL_COOKIE

        #include "UnityPBSLighting.cginc"
        #include "Assets/Lanbai/Cabin/Shaders/LanbaiCabinCommon.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

        sampler2D _MainTex;
        fixed4 _Color, _HemColor;
        half _Glossiness, _WeaveScale, _Wrap, _Transmission, _SHAmbientK, _RimGain;
        sampler2D _WeaveNormal;
        float _WeaveTile, _HemHeight;
        float4 _TubeLMConst;
        float _ClothClock, _Inward, _CentreX, _Dissolve;
        float4 _Sway, _Float, _Wing, _Release, _FlyDir, _DissolveGlow, _RoofLine;

        struct Input
        {
            float2 uv_MainTex;
            float4 clothData;        // x hem weight (vertex R), y metres below the rail (uv0.y), z across (uv0.x)
            float3 worldPos;
            float facing : VFACE;
        };

        // ---------------------------------------------------------------------------------- motion
        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            float w = saturate(v.color.r);                       // 0 at the rail -> 1 at the hem
            float t = _ClothClock;
            float3 posWS = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
            // per-PANEL constants from finish_bus.py: uv1 = rail midpoint (x, z), uv2 = (rail y, panel random). Every
            // vertex of a panel gets the same phase, release spread and eye distance, so panels never tear or shear.
            bool hasPanel = v.texcoord2.x > 0.5;
            float3 rail = hasPanel ? float3(v.texcoord1.x, v.texcoord2.x, v.texcoord1.y) : posWS;
            float prand = hasPanel ? v.texcoord2.y : LanbaiHash13(floor(posWS * 0.8));
            float ph = prand * 6.2832;                                            // per-panel phase
            float along = v.texcoord.x;                                           // across the panel, metres
            float sx = abs(_Inward) > 0.5 ? sign(_Inward) : (posWS.x > _CentreX ? -1.0 : 1.0);
            float3 inward = float3(sx, 0.0, 0.0);                                 // into the cabin (world, the bus never turns)

            float3 d = 0;
            // sway: a pendulum, the hem moves most (w^1.5), a slow travelling wave across the panel
            float sw = sin(6.2832 * _Sway.y * t + ph + along * 2.1);
            d += inward * (_Sway.x * pow(w, 1.5) * sw);
            d.z += _Sway.x * 0.4 * pow(w, 1.5) * sin(6.2832 * _Sway.y * 0.73 * t + ph * 1.7);
            // underwater: the cloth floats up (w^2), breathing at _Float.y
            float fl = _Float.x * w * w * (0.75 + 0.25 * sin(6.2832 * _Float.y * t + ph));
            d.y += fl;
            d += inward * (fl * 0.35);
            // wings: open into the cabin and beat
            float wb = 0.6 + 0.4 * sin(6.2832 * _Wing.y * t + ph * 0.5 + along * 0.8);
            d += inward * (_Wing.x * w * wb);
            d.y += _Wing.x * 0.35 * w * (wb - 0.6);

            // VR comfort (bible §1.8, review r1 #8): the local player's eye is the seat sphere centre + 0.68 m. A panel
            // next to that eye (within 0.4-0.9 m along z) may not swing in closer than 0.35 m to it.
            float3 eye = _SeatSphere.xyz + float3(0.0, 0.68, 0.0);
            float gap = abs(rail.x - eye.x);
            float nearZ = (1.0 - smoothstep(0.4, 0.9, abs(rail.z - eye.z))) * step(gap, 0.9);
            float inAmt = dot(d, inward);
            float inMax = lerp(10.0, max(gap - 0.35, 0.0), nearZ);
            d -= inward * max(inAmt - inMax, 0.0);

            // release (F10e, D-32 #9): the whole panel, rail included, first rises STRAIGHT UP through the open roof
            // until its rail is _RoofLine.y above the roof line _RoofLine.x, then bends toward the sun (a tangent-
            // continuous turn, radius ~ _RoofLine.z) and goes into the light (the driver dissolves it from F10l).
            // Speed: accelerate at _Release.y up to _Release.z, never faster than 0.75 x (distance from the eye at
            // let-go + distance flown) - that is <= 1.05 x the true distance to the eye on any path (sqrt 2 x 0.75),
            // the §1.8 limit for things moving near your head.
            float tr = _Release.x;
            [branch] if (tr > 0.0)
            {
                float3 sd = _Udon_SunDir.w > 0.0 ? _Udon_SunDir.xyz : _FlyDir.xyz;
                float3 sunD = normalize(sd + float3(0.0, 0.15, 0.0));            // toward the sun, a little up
                float a = max(_Release.y, 0.01), vmax = max(_Release.z, 0.1);
                float tA = vmax / a;                                              // time to reach vmax
                float s = tr < tA ? 0.5 * a * tr * tr : 0.5 * a * tA * tA + vmax * (tr - tA);
                float d0 = max(distance(rail, eye), 0.2);                         // one value per panel
                s = min(s, d0 * (exp(0.75 * tr) - 1.0));                          // v = 0.75 (d0 + s)
                s *= 0.85 + 0.3 * prand;                                          // panels do not move as one block
                float railY = hasPanel ? rail.y : posWS.y + v.texcoord.y;         // uv0.y = metres below the rail
                float hUp = max(_RoofLine.x + _RoofLine.y - railY, 0.0);
                float sv = min(s, hUp), sh = max(s - hUp, 0.0);
                float L = max(_RoofLine.z, 0.05);
                float eb = 1.0 - exp(-sh / L);                                    // direction blend up -> sun
                d += float3(0.0, 1.0, 0.0) * (sv + L * eb) + sunD * (sh - L * eb);
                d += inward * (0.25 * w * sin(6.2832 * 0.6 * t + ph) * (1.0 - nearZ));   // still beating while it goes
            }
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, d);
            o.clothData = float4(w, v.texcoord.y, v.texcoord.x, 0.0);
        }

        // ---------------------------------------------------------------------------------- lighting
        inline half4 LightingThinCloth(SurfaceOutput s, half3 viewDir, UnityGI gi)
        {
            float3 N = normalize(s.Normal);
            float3 L = gi.light.dir;
            float3 lc = gi.light.color;
        #if defined(UNITY_PASS_FORWARDADD) && defined(DIRECTIONAL)
            lc = LanbaiWoundLightLimit(lc);                                       // D-08 (wound light), as Lanbai/Cabin
        #endif
            float ndl = dot(N, L);
            float wrap = saturate((ndl + _Wrap) / (1.0 + _Wrap));
            float trans = saturate(-ndl) * _Transmission;
            half4 c;
            c.rgb = lc * (s.Albedo * wrap + s.Albedo * s.Albedo * trans);
        #ifdef UNITY_LIGHT_FUNCTION_APPLY_INDIRECT
            c.rgb += s.Albedo * gi.indirect.diffuse;
        #endif
            c.a = s.Alpha;
            return c;
        }
        inline void LightingThinCloth_GI(SurfaceOutput s, UnityGIInput data, inout UnityGI gi)
        {
            gi = UnityGlobalIllumination(data, 1.0, s.Normal);
            float3 sh = max(ShadeSH9(float4(s.Normal, 1.0)), 0.0);
            gi.indirect.diffuse = max(gi.indirect.diffuse - (1.0 - _SHAmbientK) * sh, 0.0);
        }

        // ---------------------------------------------------------------------------------- surface
        void surf(Input IN, inout SurfaceOutput o)
        {
            float3 P = IN.worldPos;
            float rim = LanbaiCabinErodeClipRim(P);
            // dissolve into light (F10l -> + 8 s): FBM clip, a warm edge
            float dn = LanbaiCabinFBM(P * 1.7, 0.35);
            float dk = _Dissolve * 1.1;
            clip(dn - dk + 0.001 * step(dk, 0.0));
            float dEdge = (1.0 - smoothstep(0.0, 0.06, dn - dk)) * step(0.001, _Dissolve);

            float3 albedo = _Color.rgb * tex2D(_MainTex, IN.uv_MainTex).rgb;
            // hem slightly darker #8898A8: the last _HemHeight metres above the hem (hem weight from vertex R)
            float hemBand = smoothstep(1.0 - _HemHeight, 1.0, saturate(IN.clothData.x));
            albedo = lerp(albedo, _HemColor.rgb, hemBand);
            albedo = LanbaiCabinBleachAlbedo(albedo, _Udon_CabinBleach.x);

            half3 nT = UnpackScaleNormal(tex2D(_WeaveNormal, IN.clothData.zy * _WeaveTile), _WeaveScale);
            nT.z *= IN.facing > 0 ? 1.0 : -1.0;                                    // two-sided
            o.Normal = nT;
            o.Albedo = albedo;
            o.Specular = 0.0;
            o.Gloss = 0.0;
            o.Alpha = 1.0;

        #if !defined(UNITY_PASS_FORWARDADD) && !defined(UNITY_PASS_SHADOWCASTER)
            float3 light = _TubeLMConst.rgb * max(_Udon_CabinLightmap, 0.0) + _Udon_CabinAmbient.rgb;
            o.Emission = albedo * light
                       + max(_Udon_CabinAmbient.rgb, 0.0) * _RimGain * rim
                       + _DissolveGlow.rgb * dEdge;
        #endif
        }

        void ClothFinal(Input IN, SurfaceOutput o, inout fixed4 color)
        {
        #ifdef UNITY_PASS_FORWARDADD
            color.rgb = LanbaiPurpleGuardLin(color.rgb);
            color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);
        #else
            color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
        #endif
        }
        ENDCG
    }
    FallBack Off
}
