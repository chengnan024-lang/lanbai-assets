// =====================================================================================================
//  Lanbai/PalaceGlow   蓝白 · 第 7b 幕大殿开着的门里的暖光（圣经 §6·7b：内部发光 #FFB74D × 3）与门口的锥形光卡（3 张，α 0.06，20 m）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check, never in Unity. !!!
//
//  _Additive 0：门后暗腔的发光内衬（第 4 轮：整腔都发光，门扇读成暗剪影），不透明，竖向渐变 _Grad，颜色 × exp(−d · _Atten)（_FogMode 2：门光从神道起点就是两列灯汇聚的消失点，§6·7b）。
//  _Additive 1：门口的锥形光卡，加色；UV0.y = 沿锥 0（门口）..1（20 m 外），UV0.x = 横向 0..1；侧着看淡出。
//  两种都吃 _Udon_PalaceVeil（门是建筑的一部分：从台地下面看，罩进雾里）。
// =====================================================================================================
Shader "Lanbai/PalaceGlow"
{
    Properties
    {
        _Glow ("Glow linear  FFB74D x 1.6", Vector) = (1.6, 0.76, 0.12, 0)
        _Grad ("Vertical gradient  bottom top multipliers", Vector) = (1.15, 0.7, 0, 0)
        _Alpha ("Cone card alpha", Float) = 0.06
        _Atten ("Attenuation per m  FogMode 2", Float) = 0.004
        [Toggle] _Additive ("Additive cone card", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst blend", Float) = 0
        _ZWrite ("ZWrite", Float) = 1
        _Gain ("Gain  driver", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            Cull Off
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
            #include "LanbaiPalace.cginc"

            float4 _Glow, _Grad;
            float _Alpha, _Atten, _Additive, _Gain;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv0 : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 posWS : TEXCOORD1;
                float3 nWS : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.posWS = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.nWS = UnityObjectToWorldNormal(v.normal);
                o.pos = UnityWorldToClipPos(o.posWS);
                o.uv = v.uv0;
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 eye = LanbaiCentreEyePos();
                float d = length(eye - i.posWS);
                float veil = LanbaiPalaceVeil(i.posWS, eye);
                float3 col = _Glow.rgb * exp(-_Atten * d) * _Gain;
                if (_Additive < 0.5)
                    col *= lerp(_Grad.x, _Grad.y, saturate(i.uv.y));     // 门里的光：下亮上暗（UV0.y = 高度 / 门高）
                if (_Additive > 0.5)
                {
                    float along = saturate(1.0 - i.uv.y);
                    float across = sin(saturate(i.uv.x) * UNITY_PI);
                    float3 V = normalize(eye - i.posWS);
                    float side = abs(dot(normalize(i.nWS), V));
                    float a = _Alpha * along * along * across * smoothstep(0.1, 0.5, side);
                    return float4(col * a * (1.0 - veil), 1.0);
                }
                col = lerp(col, LanbaiHorizon(normalize(i.posWS - eye)), veil);
                return float4(col, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
