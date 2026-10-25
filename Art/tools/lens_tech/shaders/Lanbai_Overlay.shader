// =====================================================================================================
//  Lanbai / Overlay        蓝白 · full-field fade sphere (black of the plunge, the 藍白 white, spawn fade)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Compile and check in Unity 2022.3 + VRChat SDK. !!!
//
//  Use: Unity's built-in Sphere mesh, scaled to radius 4 m (scale 8), parented to the (static) bus,
//  centred on the player's seat eye point. The head is always inside it, so no per-frame head tracking is
//  needed, and it cannot lag. Cull Front = we see the inside. ZTest Always + queue Overlay+100 = it covers
//  every world object. It renders BEFORE post-processing, so its colour is graded and tonemapped like the
//  world (lens_cine 5.10 gives the value to enter for each target display colour).
//
//  Udon drives _Color (rgb = HDR colour, a = opacity) every frame from the ramp law (lens_tech.md 3.2):
//    alpha = EvRampAlpha(x, L_scene, L_overlay, L_floor)     never a linear alpha ramp for a brightening.
//  Keep the renderer DISABLED when alpha = 0 (saves a full-screen pass per eye).
// =====================================================================================================
Shader "Lanbai/Legacy/Overlay_v1"   // v1 (lens_tech). Renamed so it never shadows Overlay/ v2 "Lanbai/Overlay" (D-44 #7; 阿白 did the same locally, GUID kept)
{
    Properties
    {
        [HDR] _Color ("Colour (HDR rgb, a = opacity)", Color) = (0, 0, 0, 0)
        _Breath ("Breathing amount (0.02 = +-2 %)", Range(0, 0.05)) = 0
        _BreathHz ("Breathing frequency (Hz, <= 0.2)", Range(0, 0.2)) = 0.1
    }
    SubShader
    {
        Tags { "Queue" = "Overlay+100" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Cull Front
        ZTest Always
        ZWrite Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "LanbaiVR.cginc"

            half4 _Color;
            half _Breath;
            half _BreathHz;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 dirWS : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(wp);
                o.dirWS = wp - _WorldSpaceCameraPos;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                half b = 1.0 + _Breath * sin(6.2831853 * _BreathHz * _Time.y);
                float3 c = _Color.rgb * b;
                // direction-anchored dither: a full field of one colour bands visibly in 8-bit headsets
                c = LanbaiDitherLinear(c, i.dirWS);
                return half4(c, _Color.a);
            }
            ENDCG
        }
    }
    Fallback Off
}
