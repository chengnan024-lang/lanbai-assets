Shader "Hidden/LanbaiCheck/OwnAllThree"
{
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma multi_compile_fog
        #include "UnityCG.cginc"
        float _FogCap; float _FogHeightFalloff; float _Udon_FogDensity;
        float4 _Udon_TearPos;
        #define LANBAI_DECL__Udon_TearPos
        #define LANBAI_FOG_OWN_UNIFORMS
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        struct appdata { float4 vertex : POSITION; };
        struct v2f { float4 pos : SV_POSITION; float4 fog : TEXCOORD0; };
        v2f vert(appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.fog = LanbaiFogVertex(mul(unity_ObjectToWorld, v.vertex).xyz); return o; }
        float4 frag(v2f i) : SV_Target { return float4(lerp(float3(0.2, 0.3, 0.4), i.fog.rgb, i.fog.a), 1); }
        ENDCG } }
}
