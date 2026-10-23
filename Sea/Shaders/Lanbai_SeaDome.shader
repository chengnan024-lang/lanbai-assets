// =====================================================================================================
//  Lanbai/SeaDome   蓝白 · the 'sky' under water (bible §6·7: 天空盒不吃雾，必须替换)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//
//  A sphere that follows the centre eye (radius _Radius, default 1800 m) and draws the water's own colour in every
//  direction: exactly LanbaiHorizon(dir) of LanbaiFog.cginc, i.e. the underwater fog colour, so anything that fogs out
//  meets it with no seam. Opaque, ZWrite On (the skybox, drawn after opaques, is then hidden behind it).
//  Only drawn while _Udon_Underwater > 0 (fragments are discarded otherwise; the driver also switches the renderer).
//  Mesh: Sea/Models/Sea_Dome.fbx (r 1800 m, so its bounds cover what it draws; a 0.5 m sphere would be frustum-culled
//  whenever the bus origin is off-screen). The vertex shader re-centres it on the eye, so only its bounds matter.
// =====================================================================================================
Shader "Lanbai/SeaDome"
{
    Properties
    {
        _Radius ("Radius m", Float) = 1800
        _Dither ("Dither LSB", Range(0, 3)) = 1.5
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry+450" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Cull Front
        ZWrite On
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            float _Radius, _Dither;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 d = normalize(v.vertex.xyz);
                o.dir = d;
                o.pos = UnityWorldToClipPos(LanbaiCentreEyePos() + d * _Radius);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Udon_Underwater <= 0.0) discard;
                float3 d = normalize(i.dir);
                float3 c = LanbaiHorizon(d);
                c = LanbaiDitherLinear(c, d * (_Dither / 1.5));
                return float4(c, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
