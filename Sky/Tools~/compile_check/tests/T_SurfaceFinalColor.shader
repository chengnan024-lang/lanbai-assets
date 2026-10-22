Shader "Hidden/LanbaiCheck/SurfaceFinalColor"
{
    Properties { _Color ("Color", Color) = (1,1,1,1) _FogCap ("Fog Cap", Range(0, 1)) = 1 _FogHeightFalloff ("Fog Height Scale m", Float) = 0 }
    SubShader {
        CGPROGRAM
        #pragma surface surf Standard finalcolor:lbfog nofog
        #pragma multi_compile_fog
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        half4 _Color;
        struct Input { float3 worldPos; };
        void surf(Input IN, inout SurfaceOutputStandard o) { o.Albedo = _Color.rgb; }
        void lbfog(Input IN, SurfaceOutputStandard o, inout fixed4 color) { color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos); }
        ENDCG
    }
}
