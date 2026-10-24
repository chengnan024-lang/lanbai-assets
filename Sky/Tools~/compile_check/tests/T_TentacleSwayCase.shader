// TentacleSway's case: it declares _FogCap and _Udon_FogDensity itself, not _FogHeightFalloff; GateSky first
Shader "Hidden/LanbaiCheck/TentacleSwayCase"
{
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma multi_compile_fog
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"
        float _FogCap;
        float _Udon_FogDensity;
        #define LANBAI_FOG_OWN_CAP
        #define LANBAI_FOG_OWN_DENSITY
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        struct appdata { float4 vertex : POSITION; };
        struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; };
        v2f vert(appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz; return o; }
        float4 frag(v2f i) : SV_Target { float3 V = normalize(i.wpos - _WorldSpaceCameraPos);
            return float4(LanbaiApplyFogEx(LanbaiBand(V), i.wpos, LanbaiMoonAir(V, LanbaiMoonDir(float3(0,0,1))) * 0.35), 1); }
        ENDCG } }
}
