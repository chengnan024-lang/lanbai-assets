// Lanbai -- grade test-card patch (ART BIBLE v2.1, 1.5). UNCOMPILED on the art side.
// Outputs scene-linear _Emission * _Tint.rgb. Both are a FLOAT / a VECTOR (set with SetFloat / SetVector), so Unity
// never sRGB-converts them (SetColor would); values > 1 survive in the HDR/FP16 camera buffer. Grey patches keep
// _Tint = (1, 1, 1); the colour row sets its linear rgb in _Tint. No lighting, no fog (bible: fog off), no shadows.
// Used by LanbaiGradeTestCard only.
Shader "Lanbai/Debug/TestPatch"
{
    Properties
    {
        _Emission ("Emission (scene-linear, 0.18 x 2^k)", Float) = 0.18
        _Tint ("Tint (linear rgb, set with SetVector)", Vector) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" "IgnoreProjector" = "True" }
        Pass
        {
            Cull Back
            ZWrite On
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

            float _Emission;
            float4 _Tint;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert (appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                return o;
            }

            float4 frag (v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                return float4(_Emission * _Tint.rgb, 1.0);
            }
            ENDCG
        }
    }
    Fallback Off
}
