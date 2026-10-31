// =====================================================================================================================
//  Lanbai / SubtitleHalo  v1    蓝白 · 字幕的行晕（D-45 B.4 #4，字体套件第 5 版，总工程师）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; Common/Tools~/compile_check only). Compile in Unity 2022.3 + VRChat
//      SDK 3.10.5, and look at it in a headset with one eye, then the other (bible §1.8). !!!
//
//  An edgeless dark band behind each subtitle line: a SpriteRenderer with Textures/Lanbai_Scrim_Line.png (Hann window
//  vertically, long feathered ends; RGB white, the shape in alpha). Colour = _Color (MaterialPropertyBlock from the
//  driver: rgb = the poem's solved linear halo fill x 2^(-dEV), a = halo alpha x the line's alpha). One alpha per poem,
//  never switched by view direction (B.4 #4).
//  Queue Overlay+9 (one before the text), ZTest Always (D-45 #10), ZWrite Off; not in mirrors / the photo camera.
// =====================================================================================================================
Shader "Lanbai/SubtitleHalo"
{
    Properties
    {
        [PerRendererData] _MainTex ("Halo shape (alpha)", 2D) = "white" {}
        _Color ("Colour (linear fill, alpha)", Color) = (0.0055, 0.0103, 0.0284, 0)
    }
    SubShader
    {
        Tags { "Queue" = "Overlay+9" "IgnoreProjector" = "True" "RenderType" = "Transparent" "ForceNoShadowCasting" = "True" "PreviewType" = "Plane" "CanUseSpriteAtlas" = "True" }
        Cull Off
        ZWrite Off
        ZTest Always
        Lighting Off
        Blend One OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            sampler2D _MainTex;
            float4 _Color;
            float _VRChatMirrorMode;
            float _VRChatCameraMode;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_VRChatMirrorMode != 0 || _VRChatCameraMode != 0) discard;
                float a = tex2D(_MainTex, i.uv).a * _Color.a;
                return float4(_Color.rgb * a, a);                    // premultiplied
            }
            ENDCG
        }
    }
}
