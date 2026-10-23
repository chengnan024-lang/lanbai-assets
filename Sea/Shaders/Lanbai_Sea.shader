// =====================================================================================================
//  Lanbai/Sea   蓝白 · the sea (ABOVE: act 6 mirror · BELOW: act 7 Snell's window / 7c inverted · CEILING: act 8-i)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//  Interface (properties, modes, globals, who drives what): Sea/README_Sea接口.md. Maths: LanbaiSea.cginc.
//
//  Render state is per material (the builder sets it; see README_Sea §材质):
//    ABOVE / BELOW : Queue Geometry (2000), Blend One Zero, ZWrite On
//    CEILING       : Queue Transparent-10 (2990), Blend SrcAlpha OneMinusSrcAlpha, ZWrite Off
//  The disc mesh follows the bus in xz (the bus is at the world origin); waves move by _Udon_SeaClock.yz.
// =====================================================================================================
Shader "Lanbai/Sea"
{
    Properties
    {
        [KeywordEnum(Above, Below, Ceiling)] _SEA ("Mode", Float) = 0

        [Header(Waves)]
        [NoScaleOffset][Normal] _NormalLarge ("Normal large FFT 64 m", 2D) = "bump" {}
        [NoScaleOffset][Normal] _NormalSmall ("Normal small FFT 9 m", 2D) = "bump" {}
        _LargeTile ("Large tile m", Float) = 64
        _SmallTile ("Small tile m", Float) = 9
        _LargeScroll ("Large drift m per s xz", Vector) = (0.9, 0.35, 0, 0)
        _SmallScroll ("Small drift m per s xz", Vector) = (-0.4, 0.7, 0, 0)
        _NormalStrength ("Normal strength", Range(0, 3)) = 1
        _WaveAmp ("Wave amplitude  7c decays to 0.3", Range(0, 1)) = 1
        [NoScaleOffset] _Macro ("Macro mask  R rippled  G gust", 2D) = "white" {}
        _MacroTile ("Macro tile m", Float) = 1500
        _CalmStrength ("Normal factor in calm slicks", Range(0, 1)) = 0.15
        _CalmAll ("Calm everything  act 6 mirror", Range(0, 1)) = 0
        _CalmPatch ("Calm patch  xy centre world xz  z radius m  w strength", Vector) = (0, 0, 0, 0)
        _IOR ("Index of refraction", Float) = 1.333
        _Smoothness ("Water smoothness", Range(0.8, 1)) = 0.97

        [Header(Reflection and body)]
        _ReflGain ("Cube reflection gain", Float) = 1
        _ReflClamp ("Cube sample max channel  linear  act 6 = disc x 0.41", Float) = 2.4
        _WaterColor ("Water body colour  linear", Vector) = (0.0156, 0.0484, 0.0954, 0)
        _DiscCenter ("Disc  xy centre world xz  z radius m  w fade band m", Vector) = (0, 0, 0, 0)
        [Enum(None, 0, LanbaiFog, 1)] _FogMode ("Fog  bible numbering  0 none  1 LanbaiFog", Float) = 1

        [Header(Above  sun glitter)]
        _SunColor ("Sun disc radiance  linear", Vector) = (0, 0, 0, 0)
        _SunDir ("Sun direction  fallback for _Udon_SunDir", Vector) = (0.703, 0.105, 0.703, 0)
        _SunGlitterRough ("Glitter extra GGX alpha", Range(0, 0.5)) = 0.12
        _SunReflPeakEV ("Glint at least this many EV under the disc", Float) = 1.3
        _SunDiscDeg ("Sun disc diameter deg", Float) = 0.9

        [Header(Below  Snell window)]
        _AirSide ("Air side  1 above  -1 below", Float) = 1
        [NoScaleOffset] _WindowCube ("Window cube  the sky on the other side", Cube) = "black" {}
        _WindowGain ("Window gain", Float) = 1
        _WindowTint ("Window tint  linear", Vector) = (1, 1, 1, 0)
        _Dispersion ("Dispersion  x n red  y n blue", Vector) = (1.331, 1.337, 0, 0)
        _TIRColor ("Total internal reflection colour  linear", Vector) = (0.0222, 0.0685, 0.1651, 0)
        _TIRCubeGain ("TIR plus reflection cube", Float) = 0
        _WindowEdgeSoft ("Window edge softness deg", Float) = 0.6
        _WindowSunDir ("Window sun  xyz direction air side  w arc half height deg", Vector) = (0, -0.0087, 1, 1.2)
        _WindowSunSpread ("Window sun arc half width deg", Float) = 14
        _WindowSunColor ("Window sun radiance linear  0 off", Vector) = (0, 0, 0, 0)
        _WindowSunFloor ("Window sun transmission floor", Range(0, 1)) = 0.35
        _WindowRadial ("Window radial  x factor at the edge  y power  1 2 off", Vector) = (1, 2, 0, 0)

        [Header(Ceiling  act 8)]
        [NoScaleOffset] _SkyBehindCube ("Sky behind the ceiling", Cube) = "black" {}
        _DissolveTime ("Dissolve clock  t minus 956.36  negative whole", Float) = -1
        _DissolveFront ("Dissolve front s", Float) = 4
        _DissolvePixel ("Dissolve per pixel s", Float) = 5

        [Header(Act 11 hanging sea  Gerstner and lamp glints)]
        _GerstnerLength ("Gerstner wavelengths m xyz  w Hz", Vector) = (60, 37, 23, 0.08)
        _GerstnerAmp ("Gerstner amplitudes m  0 off", Vector) = (0, 0, 0, 0)
        _GerstnerDir ("Gerstner directions  xy wave 1  zw wave 2", Vector) = (0.94, 0.34, 0.5, 0.866)
        _LampGlints ("Lamp glints 0..1  udon lamps", Range(0, 1)) = 0

        [Header(Render state  set by the builder)]
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst blend", Float) = 0
        [Enum(Off, 0, On, 1)] _ZWrite ("ZWrite", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        LOD 200
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
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #pragma shader_feature_local _SEA_ABOVE _SEA_BELOW _SEA_CEILING

            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
            #include "LanbaiSea.cginc"

            float _FogMode;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 posWS : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.posWS = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.posWS);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 P = i.posWS;
                float3 eye = _WorldSpaceCameraPos;
                float3 toP = P - eye;
                float dist = length(toP);
                float3 I = toP / max(dist, 1e-4);                     // eye -> point
                float2 q = P.xz + LanbaiSeaOffset();
                float slopeVar;
                float3 N = LanbaiSeaNormal(q, P.xz, slopeVar);
                float4 col = float4(0, 0, 0, 1);
            #if defined(_SEA_BELOW)
                col.rgb = LanbaiSeaBelow(N, I, slopeVar);
            #elif defined(_SEA_CEILING)
                col = LanbaiSeaCeiling(N, I, slopeVar, P.xz, P);
            #else
                col.rgb = LanbaiSeaAbove(N, -I, slopeVar);
                col.a = LanbaiSeaDiscAlpha(P.xz);
            #endif
                if (_FogMode > 0.5)
                    col.rgb = LanbaiApplyFog(col.rgb, P);
                return col;
            }
            ENDCG
        }
    }
    FallBack Off
}
