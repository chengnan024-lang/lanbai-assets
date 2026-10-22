// LANBAI_CHECK_EXPECT_FAIL : Fog before GateSky redeclares _Udon_FogBand* (document: include GateSky first)
Shader "Hidden/LanbaiCheck/FogThenGate"
{
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"
        struct appdata { float4 vertex : POSITION; };
        struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; };
        v2f vert(appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz; return o; }
        float4 frag(v2f i) : SV_Target { float3 V = normalize(i.wpos - _WorldSpaceCameraPos); return float4(LanbaiBand(V) + LanbaiHorizon(V), 1); }
        ENDCG } }
}
