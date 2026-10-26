// =====================================================================================================
//  Lanbai/TreeBark      蓝白 · 样板树的树干和枝（D-44 #6）
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//  Standard lighting (surface shader), wet bark per bible §1.6 (LanbaiTree.cginc), LanbaiFog, vertex wind.
// =====================================================================================================
Shader "Lanbai/TreeBark"
{
    Properties
    {
        _MainTex ("Albedo sRGB", 2D) = "white" {}
        _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask R unused G smoothness B AO A water path", 2D) = "white" {}
        _Smoothness ("Dry Smoothness x", Range(0, 1)) = 1
        _WetResponse ("Wet Response", Range(0, 1)) = 1
        [Header(Wind)]
        _WindDir ("Wind Direction (world)", Vector) = (1, 0, 0.3, 0)
        _WindStrength ("Wind Sway m", Range(0, 0.2)) = 0.05
        _WindFreq ("Wind Frequency rad per s", Range(0, 3)) = 1.3
        _Flutter ("Flutter m", Range(0, 0.03)) = 0
        _FlutterFreq ("Flutter Frequency rad per s", Range(0, 12)) = 5
        [Header(Fog)]
        _FogCap ("Fog Cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        LOD 300

        CGPROGRAM
        #pragma surface surf Standard vertex:vert finalcolor:fogColor nofog fullforwardshadows addshadow
        #pragma target 3.5
        #pragma multi_compile_fog
        #pragma multi_compile_instancing
        #include "LanbaiTree.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

        sampler2D _MainTex;
        sampler2D _BumpMap;
        sampler2D _MaskTex;
        half _Smoothness;

        struct Input
        {
            float2 uv_MainTex;
            float3 worldPos;
        };

        void vert(inout appdata_full v)
        {
            v.vertex.xyz = LanbaiTreeWind(v.vertex.xyz, v.normal, v.color);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float w = LanbaiTreeWet();
            fixed4 alb = tex2D(_MainTex, IN.uv_MainTex);
            fixed4 m = tex2D(_MaskTex, IN.uv_MainTex);
            float wp = w * lerp(0.6, 1.0, m.a);                              // water paths get fully wet first
            o.Albedo = alb.rgb * m.b * lerp(1.0, 0.60, wp);
            half3 n = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            n.xy *= lerp(1.0, 0.6, wp);
            o.Normal = normalize(n);
            o.Smoothness = lerp(m.g * _Smoothness, 0.45, wp);
            o.Metallic = 0;
            o.Occlusion = 1;
        }

        void fogColor(Input IN, SurfaceOutputStandard o, inout fixed4 color)
        {
        #ifdef UNITY_PASS_FORWARDADD
            color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);
        #else
            color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
        #endif
        }
        ENDCG
    }
    FallBack "Diffuse"
}
