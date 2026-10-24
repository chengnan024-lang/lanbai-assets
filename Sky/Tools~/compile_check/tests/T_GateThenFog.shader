Shader "Hidden/LanbaiCheck/GateThenFog"
{
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma multi_compile_fog
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        struct appdata { float4 vertex : POSITION; };
        struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; };
        v2f vert(appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz; return o; }
        float4 frag(v2f i) : SV_Target {
            float3 V = normalize(i.wpos - _WorldSpaceCameraPos);
            float3 c = LanbaiApplyFog(LanbaiBand(V), i.wpos) + LanbaiGateFogColour(V, 100, LanbaiMoonDir(float3(0,0,1)), 0.35, 0.35);
            return float4(c + LanbaiHorizon(V), 1); }
        ENDCG } }
}
