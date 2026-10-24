// a shader that declares _FogCap itself (one guard)
Shader "Hidden/LanbaiCheck/OwnCapOnly"
{
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma multi_compile_fog
        #include "UnityCG.cginc"
        float _FogCap;
        #define LANBAI_FOG_OWN_CAP
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        struct appdata { float4 vertex : POSITION; };
        struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; };
        v2f vert(appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz; return o; }
        float4 frag(v2f i) : SV_Target { return float4(LanbaiApplyFog(float3(0.2, 0.3, 0.4), i.wpos), 1); }
        ENDCG } }
}
