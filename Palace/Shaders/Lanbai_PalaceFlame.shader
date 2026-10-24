// =====================================================================================================
//  Lanbai/PalaceFlame   蓝白 · 第 7b 幕宫灯的火（8 帧序列帧）与灯晕卡（r 1.5 m：#FFC46A → #2A557B → 0）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check, never in Unity. !!!
//
//  网格（Palace/Models/Palace_Flames.fbx，搭建脚本另建）：每盏灯两张四边形，四个顶点都在灯焰中心；
//    UV0 = 角（−1..1），UV1.x = 0 火 / 1 晕，UV1.y = 每盏的相位 0..1。顶点 shader 把它们展开成朝两眼中点的公告板：
//    火 = 竖直的柱状公告板（只绕 y 转），晕 = 球状公告板。**深度测试，ZWrite Off，加色**。
//  _FogMode 2（圣经 §1.6“天上的东西不吃雾”，§6·7b 灯焰用无雾衰减）：颜色 × exp(−d · _Atten)，_Atten 0.004；不吃 _Udon_PalaceVeil
//  （从下面看它们就是头顶的星座，D-17 / D-29）。远处的火小于 1.5 像素时按面积守恒放大（亮度 / 面积），
//  所以 30 盏灯在任何距离都是稳定、分得清的点，不会闪烁（D-29 第 4 条）。
//  火的呼吸：8 帧之间交叉淡化，每秒 _FPS 帧，每盏错开相位；时间 = _Udon_T。亮度本身不闪（只有形状变），§1.8。
// =====================================================================================================
Shader "Lanbai/PalaceFlame"
{
    Properties
    {
        _FlipTex ("Flame flipbook 4x2", 2D) = "black" {}
        _FlameColor ("Flame colour linear  fill FF5E2A at plus 3.11", Vector) = (8.65, 1.00, 0.20, 0)
        _FlameSize ("Flame half size m  x y", Vector) = (0.09, 0.19, 0, 0)
        _HaloRadius ("Halo radius m", Float) = 1.5
        _HaloWarm ("Halo warm core gain", Float) = 0.06
        _HaloMid ("Halo indigo mid linear  fill 446282", Vector) = (0.0578, 0.1221, 0.2232, 0)
        _Atten ("Attenuation per m  FogMode 2", Float) = 0.004
        _FPS ("Flipbook frames per second", Float) = 6
        _MinPixels ("Minimum flame half size px", Float) = 1.2
        _Gain ("Gain  driver", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent+10" "IgnoreProjector" = "True" }
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Blend One One
            ZWrite Off
            ZTest LEqual
            Cull Off
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

            sampler2D _FlipTex;
            float4 _FlameColor, _FlameSize, _HaloMid;
            float _HaloRadius, _HaloWarm, _Atten, _FPS, _MinPixels, _Gain;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 corner : TEXCOORD0;
                float4 info : TEXCOORD1;     // x 种类, y 相位, z 衰减 × 面积补偿, w —
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 c = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
                float3 eye = LanbaiCentreEyePos();
                float3 toEye = eye - c;
                float d = max(length(toEye), 0.05);
                float3 fwd = toEye / d;
                bool halo = v.uv1.x > 0.5;
                float3 up = float3(0, 1, 0);
                float3 right = normalize(cross(up, fwd) + float3(1e-5, 0, 0));
                float3 upB = halo ? normalize(cross(fwd, right)) : up;
                float2 size = halo ? float2(_HaloRadius, _HaloRadius) : _FlameSize.xy;
                // 最小像素：一个像素在 d 处的米数 = 2d / (P11 · 屏高)
                float pix = 2.0 * d / (abs(unity_CameraProjection._m11) * _ScreenParams.y);
                float s = halo ? 1.0 : max(1.0, _MinPixels * pix / max(size.x, 1e-4));
                size *= s;
                float3 p = c + right * v.uv0.x * size.x + upB * v.uv0.y * size.y;
                o.pos = UnityWorldToClipPos(p);
                o.corner = v.uv0;
                o.info = float4(v.uv1.x, v.uv1.y, exp(-_Atten * d) / (s * s), 0);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 col;
                if (i.info.x > 0.5)
                {
                    float r = length(i.corner);
                    float warm = exp(-(r / 0.10) * (r / 0.10));
                    float ind = saturate(1.0 - r);
                    ind *= ind;
                    col = warm * _FlameColor.rgb * _HaloWarm + ind * _HaloMid.rgb;
                }
                else
                {
                    float f = (_Udon_T * _FPS + i.info.y * 8.0);
                    float k0 = fmod(floor(f), 8.0);
                    float k1 = fmod(k0 + 1.0, 8.0);
                    float w = frac(f);
                    float2 uvl = float2(i.corner.x * 0.5 + 0.5, i.corner.y * 0.5 + 0.5);
                    // 图集 4×2：帧 0–3 在图的上半（Unity 的 v 从下往上，所以 v 在 0.5..1），帧 4–7 在下半
                    float2 a0 = float2((fmod(k0, 4.0) + uvl.x) / 4.0, (uvl.y + (k0 < 4.0 ? 1.0 : 0.0)) * 0.5);
                    float2 a1 = float2((fmod(k1, 4.0) + uvl.x) / 4.0, (uvl.y + (k1 < 4.0 ? 1.0 : 0.0)) * 0.5);
                    float m = lerp(tex2D(_FlipTex, a0).r, tex2D(_FlipTex, a1).r, w);
                    col = m * _FlameColor.rgb;
                }
                return float4(col * i.info.z * _Gain, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
