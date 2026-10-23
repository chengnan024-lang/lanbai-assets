// =====================================================================================================
//  Lanbai / Sky   v1 (2026-10-23, cloud sub-session "天空")      蓝白 · 全片的天空盒  Skybox, Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Sky/Tools~/compile_check). !!!
//
//  ART BIBLE v2.1 §8.1 #8. One skybox for acts 1-3 and 6-12 (act 4 keeps Gate/Lanbai_GateAirSky, whose band
//  LanbaiHorizon reproduces exactly). Layers, bottom to top (every colour LINEAR; colours are Vectors on purpose, so
//  nothing is converted twice):
//    1. two cubemaps A / B (HDRIs), each with a fixed Y rotation, EV, clamp, and four tints (zenith, mid sky, horizon
//       toward the sun, horizon away from the sun) that pull the HDRI onto the bible's screen targets; mixed by _Blend.
//       The lower hemisphere of a pure-sky HDRI is replaced by a gradient from that azimuth's horizon to _NadirColor.
//    2. the procedural sky = LanbaiHorizon(V) (Common/Shaders/LanbaiSky.cginc: the SAME function the fog uses, so a
//       fully fogged object vanishes into it); weight _ProcWeight. Then two horizon bands pull the result toward a
//       colour (dawn: earth shadow + Venus belt the HDRI lacks; blue hour #2E4F8A; act 12 the waking line).
//    3. the other sky (act 8-ii): below the horizon the cubes are sampled at (-x, -y, z), x _OtherGain, tinted, with
//       a soft seam; weight _OtherSky. Its sun is drawn too (the burning line of two suns).
//    4. night: _NightColor + galaxy glow (StarSky_Glow equirect) x gain + star floor x gain; weight per direction
//       (_NightBlend with the directional delay of act 8b -> 9: back and zenith first, the front horizon band last).
//    5. sun disc / sun line (procedural, never from the HDRI: the HDRI is clamped), moon disc + aureole.
//    6. dither (direction-anchored, both eyes the same; LanbaiVR.cginc).
//  The skybox NEVER rotates at runtime (bible §1.8): _RotationA/B are set once when the act is built.
//
//  Udon globals (all optional; never set = the material values): see Sky/README_Sky.md §4.
//    _Udon_SkyBlend   x = cube A->B, y = procedural weight, z = night weight (directional), w > 0 = set
//    _Udon_SkyFx      x = other sky, y = mid-band gain, z = sun line half length deg, w > 0 = set
//    _Udon_GalaxyGain x = galaxy glow + star floor gain g(t), w > 0 = set
//    _Udon_SunDir / _Udon_SunDisc, _Udon_MoonDir / _Udon_MoonDisc (LanbaiSky.cginc)
// =====================================================================================================
Shader "Lanbai/Sky"
{
    Properties
    {
        [Header(Cube A  the act HDRI)]
        [NoScaleOffset] _CubeA ("Cube A (HDR)", Cube) = "black" {}
        _RotationA ("Cube A Y rotation deg (content azimuth += this)", Float) = 0
        _ExposureA ("Cube A exposure EV", Float) = 0
        _ClampA ("Cube A clamp (linear; the sun is procedural)", Float) = 16
        _ZenithTintA ("Cube A zenith tint, linear", Vector) = (1, 1, 1, 1)
        _MidTintA ("Cube A mid-sky tint, linear", Vector) = (1, 1, 1, 1)
        _HorizonTintA ("Cube A horizon tint toward the sun, linear", Vector) = (1, 1, 1, 1)
        _HorizonAntiTintA ("Cube A horizon tint away from the sun, linear", Vector) = (1, 1, 1, 1)
        [Header(Cube B)]
        [NoScaleOffset] _CubeB ("Cube B (HDR)", Cube) = "black" {}
        _RotationB ("Cube B Y rotation deg", Float) = 0
        _ExposureB ("Cube B exposure EV", Float) = 0
        _ClampB ("Cube B clamp", Float) = 16
        _ZenithTintB ("Cube B zenith tint, linear", Vector) = (1, 1, 1, 1)
        _MidTintB ("Cube B mid-sky tint, linear", Vector) = (1, 1, 1, 1)
        _HorizonTintB ("Cube B horizon tint toward the sun, linear", Vector) = (1, 1, 1, 1)
        _HorizonAntiTintB ("Cube B horizon tint away from the sun, linear", Vector) = (1, 1, 1, 1)
        _TintElevation ("Tints  x horizon full below deg  y mid full at deg  z zenith full above deg  w azimuth power", Vector) = (2, 35, 75, 1)
        _Blend ("Cube A to B (global _Udon_SkyBlend.x wins)", Range(0, 1)) = 0
        _HorizonLift ("Never sample the HDRI below this elevation deg (its own horizon line)", Float) = 0.8
        [Header(Below the horizon)]
        _NadirColor ("Nadir colour, linear; a = desaturation in the middle of the gradient", Vector) = (0.16, 0.27, 0.39, 0)
        _BelowShape ("Below  x gradient end deg (negative)  y power  z horizon sample deg  w horizon sample clamp", Vector) = (-35, 0.8, 0.6, 2)
        [Header(Procedural  LanbaiHorizon  the same function as the fog)]
        _ProcWeight ("Procedural weight (global _Udon_SkyBlend.y wins)", Range(0, 1)) = 0
        [Header(Horizon bands  earth shadow  Venus belt  blue hour  waking line)]
        _Band1Color ("Band 1 colour, linear; a = grey in the middle of its edge", Vector) = (0.050, 0.095, 0.278, 0)
        _Band1Shape ("Band 1  x centre el deg  y el sigma deg  z azimuth from the sun deg  w azimuth sigma deg", Vector) = (14, 8, 0, 60)
        _Band1Gain ("Band 1 gain (global _Udon_SkyFx.y wins)", Range(0, 1)) = 0
        _Band2Color ("Band 2 colour, linear; a = grey in the middle of its edge", Vector) = (1, 1, 1, 0)
        _Band2Shape ("Band 2  x centre el deg  y el sigma deg  z azimuth from the sun deg  w azimuth sigma deg", Vector) = (12, 5, 180, 55)
        _Band2Gain ("Band 2 gain", Range(0, 1)) = 0
        [Header(Other sky  act 8 ii)]
        _OtherSky ("Other sky weight (global _Udon_SkyFx.x wins)", Range(0, 1)) = 0
        _OtherGain ("Other sky gain (bible x0.82 = -0.3 EV)", Float) = 0.82
        _OtherTint ("Other sky tint rgb  a pull toward the nadir colour with depth", Vector) = (0.92, 0.95, 1.05, 0)
        _OtherSeam ("Other sky seam width deg", Float) = 1
        _OtherFromB ("Other sky from cube B (1) instead of the same cubes (0)", Float) = 0
        [Header(Night  stars are Lanbai StarPoints)]
        _NightBlend ("Night weight (global _Udon_SkyBlend.z wins)", Range(0, 1)) = 0
        _NightColor ("Night floor before ignition, linear (fill #050000 under S9a)", Vector) = (0.0015, 0, 0, 1)
        _StarFloorAdd ("Star floor added at gain 1, linear (fill #0D0F23 minus the floor)", Vector) = (0.0025, 0.0048, 0.0170, 1)
        [NoScaleOffset] _GlowTex ("Galaxy glow equirect (StarSky_Glow_8192x4096.png, sRGB, x Glow Scale)", 2D) = "black" {}
        _GalaxyGain ("Galaxy glow gain (global _Udon_GalaxyGain.x wins)", Float) = 0
        _GlowScale ("Galaxy glow scale (the PNG is normalised; Sky/Data/StarSky.json glow_scale)", Float) = 1
        _NightMaskDir ("Night delay  the front direction xyz (sun death azimuth)", Vector) = (0, 0, 1, 0)
        _NightMaskShape ("Night mask ellipse  x az half axis  y its soft  z el half axis  w its soft", Vector) = (30, 45, 6, 22)
        [Header(Sun)]
        _SunDir ("Sun direction fallback (global _Udon_SunDir wins)", Vector) = (0.7, 0.1, 0.7, 0)
        _SunColor ("Sun disc colour, linear HDR (dawn fill #FFCE9E x 2^2.55)", Vector) = (5.86, 3.70, 1.98, 1)
        _SunShape ("Sun  x radius deg  y soft edge deg  z limb darkening  w line half length deg", Vector) = (0.265, 0.04, 0.55, 0)
        _SunGain ("Sun gain (global _Udon_SunDisc.x wins)", Float) = 1
        _SunRemove ("Remove the HDRI sun  x radius deg  y luminance cap  z aureole  w hue to sun", Vector) = (0, 2.5, 0.25, 0.6)
        _SunGlow ("Sun aureole  x gain  y falloff per deg  z wide gain  w wide falloff", Vector) = (0, 1.2, 0, 0.15)
        _SunGlowColor ("Sun aureole colour, linear", Vector) = (1, 0.6, 0.3, 1)
        [Header(Moon)]
        [NoScaleOffset] _MoonTex ("Moon disc (Moon_Disc_1024.png, sRGB, alpha = disc)", 2D) = "black" {}
        _MoonDir ("Moon direction fallback (global _Udon_MoonDir wins)", Vector) = (-0.206, 0.139, 0.969, 0)
        _MoonColor ("Moon disc colour, linear HDR (S3 fill #F0F5FF x 2^1.67)", Vector) = (2.81, 2.97, 3.18, 1)
        _MoonRadius ("Moon radius deg (global _Udon_MoonDisc.y wins)", Float) = 0.6
        _MoonGain ("Moon gain (global _Udon_MoonDisc.x wins)", Float) = 0
        _MoonGlow ("Moon aureole  a1 k1 a2 k2  (gate  1.6 0.9 0.06 0.32)", Vector) = (1.6, 0.9, 0.06, 0.32)
        _MoonGlowColor ("Moon aureole colour, linear (#8FA3C8)", Vector) = (0.275, 0.366, 0.578, 1)
        [Header(Output)]
        _Exposure ("Overall exposure EV", Float) = 0
        _PurpleGuard ("Purple guard  x strength  y max R over G  z where B over G above", Vector) = (0, 0.86, 1.25, 0)
        _Dither ("Dither LSB", Range(0, 3)) = 1.5
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Cull Off ZWrite Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiSky.cginc"
            #include "Assets/Lanbai/Sky/Shaders/LanbaiSkyLayers.cginc"

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dir = v.vertex.xyz;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 V = normalize(i.dir);
                float3 c = LanbaiSkyColour(V);
                c = lerp(c, LanbaiDitherLinear(c, V), _Dither / 1.5);
                return half4(c, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
