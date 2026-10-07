// =====================================================================================================
//  Lanbai / StencilWindow        蓝白 · the window a hero puddle opens into its mirror world (lens_tech §2.6, bible §1.6)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  Mesh: the puddle outline (Docs~/Stop_Layout.json -> hero_puddles, Unity local XZ of R_Stop) as a flat mesh at the
//  water level, 1-2 mm above the road (the SAME mesh the Lanbai/PuddleOverlay renderer uses; give it both materials
//  on two renderers, or two sub-meshes). Order (queues): road and everything opaque (<= 2450 AlphaTest)
//    -> this window (AlphaTest+10 = 2460)  -> the mirrored copies, Lanbai/MirrorCopy (AlphaTest+20 = 2470)
//    -> the skybox -> the water, Lanbai/PuddleOverlay (Transparent-20).
//  Pass 1 marks the VISIBLE puddle pixels with stencil bit 128 (normal depth test, so a pole or a person in front
//  still hides the puddle). Pass 2, only on those pixels, paints the mirror's background (the sky straight up, as the
//  water sees it) and pushes depth to just short of the far plane: the copies BELOW the road can then pass the depth
//  test, and the skybox (drawn later, at the far plane) cannot overwrite the window. Bit 128 stays clear of the low
//  stencil values avatar shaders use. PuddleOverlay restores the water plane's depth and clears the bit.
// =====================================================================================================
Shader "Lanbai/StencilWindow"
{
    Properties
    {
        _MirrorSky ("The sky the puddle sees (zenith, sRGB as picked; scene 1/12 #070B14)", Color) = (0.027, 0.043, 0.078, 1)
        _SkyFromCube ("0 = flat _MirrorSky, 1 = _Udon_ReflCube straight up (only if the cube has no lamp in it)", Range(0, 1)) = 0
    }
    SubShader
    {
        Tags { "Queue" = "AlphaTest+10" "RenderType" = "Opaque" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }

        // ------------------------------------------------------------------ 1: mark the visible puddle pixels
        Pass
        {
            Name "MARK"
            Tags { "LightMode" = "Always" }
            ColorMask 0
            ZWrite Off
            ZTest LEqual
            Cull Back
            Stencil { Ref 128 WriteMask 128 Comp Always Pass Replace }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                return o;
            }
            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                return 0;
            }
            ENDCG
        }

        // ------------------------------------------------------------------ 2: mirror background + depth to ~far
        Pass
        {
            Name "OPEN"
            Tags { "LightMode" = "Always" }
            ZWrite On
            ZTest Always
            Cull Back
            Stencil { Ref 128 ReadMask 128 Comp Equal }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "LanbaiRain.cginc"
            half4 _MirrorSky;
            half _SkyFromCube;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            struct fout { fixed4 col : SV_Target; float depth : SV_Depth; };
            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                return o;
            }
            fout frag(v2f i)
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                fout o;
                float3 V = normalize(_WorldSpaceCameraPos - i.wpos);
                float3 R = reflect(-V, float3(0, 1, 0));
                float3 sky = lerp(_MirrorSky.rgb, LanbaiReflCube(R, 0.0), _SkyFromCube);
                o.col = fixed4(sky, 1);
            #if defined(UNITY_REVERSED_Z)
                o.depth = 1e-6;            // just short of the far plane (reversed Z: far = 0); ~0.05 / 1e-6 = 50 km
            #else
                o.depth = 1.0 - 1e-6;
            #endif
                return o;
            }
            ENDCG
        }
    }
    FallBack Off
}
