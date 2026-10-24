Shader "Hidden/LanbaiCheck/FogOnly"
{
    Properties { _FogCap ("Fog Cap", Range(0, 1)) = 1  _FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0 }
    SubShader { Pass {
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma multi_compile_fog
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct v2f { float4 pos : SV_POSITION; float3 wpos : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
        v2f vert(appdata v) { v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_OUTPUT(v2f, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            o.pos = UnityObjectToClipPos(v.vertex); o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz; return o; }
        float4 frag(v2f i) : SV_Target { UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
            float3 c = LanbaiApplyFog(float3(0.2, 0.3, 0.4), i.wpos);
            c += LanbaiApplyFogAdditive(float3(0.1, 0.1, 0.1), i.wpos);
            float3 V = normalize(i.wpos - _WorldSpaceCameraPos);
            c += LanbaiDisc(V, LanbaiSunDir(float3(0, 0.1, 1)), 0.45, 0.05, 0.6) * LanbaiSkyObjectAtten(1000, 1e-4);
            c += LanbaiOtherSkyWeight(V, 1.0) * LanbaiOtherSkyDir(V);
            return float4(c, 1); }
        ENDCG } }
}
