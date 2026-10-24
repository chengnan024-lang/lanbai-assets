// =====================================================================================================
//  Lanbai/PalaceFlame   蓝白 · 第 7b 幕宫灯的火（8 帧序列帧）与灯晕卡（r 1.5 m：#FFC46A → #2A557B → 0）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check, never in Unity. !!!
//
//  网格（Palace/Models/Palace_Flames.fbx，搭建脚本另建）：每盏灯两张四边形，四个顶点都在灯焰中心；
//    UV0 = 角（−1..1），UV1.x = 0 火 / 1 晕，UV1.y = 每盏的相位 0..1。顶点 shader 把它们展开成朝两眼中点的公告板：
//    火 = 竖直的柱状公告板（只绕 y 转），晕 = 球状公告板。**深度测试，ZWrite Off，加色**。
//  颜色（第 4 轮）：焰身 = 金 #E0A860 在 S7b 下的线性值 × 2.2，芯 = 白热；不用 #FF5E2A @ +3.11（它远了、暗了会露出粉红）。
//  _FogMode 2（圣经 §1.6“天上的东西不吃雾”，§6·7b 灯焰用无雾衰减）：颜色 × exp(−d · _Atten)，_Atten 0.004；不吃 _Udon_PalaceVeil
//  （从下面看它们就是头顶的星座，D-17 / D-29）。远处的火小于 1.5 像素时按面积守恒放大（亮度 / 面积），
//  不压暗（远处的灯焰要读成星），所以 30 盏灯在任何距离都是稳定、分得清的点，不会闪烁（D-29 第 4 条）。
//  火的呼吸：8 帧之间交叉淡化，每秒 _FPS 帧，每盏错开相位；时间 = _Udon_T。亮度本身不闪（只有形状变），§1.8。
// =====================================================================================================
Shader "Lanbai/PalaceFlame"
{
    Properties
    {
        _FlipTex ("Flame flipbook 4x2", 2D) = "black" {}
        _FlameColor ("Flame body linear  gold E0A860 in S7b x 2.2", Vector) = (3.07, 1.18, 0.31, 0)
        _FlameCore ("Flame core linear  white hot", Vector) = (2.6, 2.13, 1.43, 0)
        _FlameSize ("Flame half size m  x y", Vector) = (0.09, 0.19, 0, 0)
        _HaloRadius ("Halo radius m", Float) = 1.5
        _HaloWarm ("Halo warm core gain", Float) = 0.08
        _HaloWarmR ("Halo warm core radius  fraction of r", Float) = 0.14
        _RingGain ("Halo indigo ring gain", Float) = 0.9
        _HaloPull ("Halo pulled toward eye m  max, also <= d/2", Float) = 4.0
        _FlamePull ("Flame pulled toward eye m when seen steeply from below", Float) = 1.5
        _BelowPull ("Max pull m when the eye is below the terrace top", Float) = 40.0
        _SoftFade ("Soft particle fade m", Float) = 1.0
        _HaloMid ("Halo indigo mid linear  fill 446282", Vector) = (0.0578, 0.1221, 0.2232, 0)
        _Atten ("Attenuation per m  FogMode 2", Float) = 0.004
        _FPS ("Flipbook frames per second", Float) = 6
        _MinPixels ("Minimum flame half size px", Float) = 2.0
        _RingFar ("Halo indigo ring fades out by this distance m", Float) = 150
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
            #pragma multi_compile _ SOFTPARTICLES_ON
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

            sampler2D _FlipTex;
            float4 _FlameColor, _FlameCore, _FlameSize, _HaloMid;
            float _HaloRadius, _HaloWarm, _HaloWarmR, _RingGain, _HaloPull, _FlamePull, _BelowPull, _Atten, _FPS, _MinPixels, _Gain, _SoftFade, _RingFar;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

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
                float4 projPos : TEXCOORD2;
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
                // 火：竖直的柱状公告板；从很低 / 很高的角度看（|fwd.y| > 0.5）渐变成球状公告板，免得从下面看成一条细线
                float3 upS = normalize(cross(fwd, right));
                float sph = halo ? 1.0 : saturate((abs(fwd.y) - 0.34) * 3.0);     // 第 8 轮：20° 起就变圆（评审 r5 #2：斜的细条）
                float3 upB = normalize(lerp(up, upS, sph));
                float2 size = halo ? float2(_HaloRadius, _HaloRadius) : _FlameSize.xy;
                // 最小像素：一个像素在 d 处的米数 = 2d / (P11 · 屏高)
                float pix = 2.0 * d / (abs(unity_CameraProjection._m11) * _ScreenParams.y);
                float s = halo ? 1.0 : max(1.0, _MinPixels * pix / max(size.x, 1e-4));
                size *= s;
                // 第 8 轮（评审 r5 #2）：晕是灯和眼睛之间那段水的散射，不是灯焰处的一张卡——往眼睛方向挪 min(_HaloPull, d/2)，
                // 角大小不变；这样台地的崖边、栏杆不会把它切成半月。火只在从下面陡着看（仰角 15–25° 以上）时往前挪 _FlamePull，
                // 让贴着崖边的灯焰不被几十厘米的边沿吃掉（平视时不挪，不会透过柱子看见火）。
                float pull = halo ? min(_HaloPull, 0.5 * d) : _FlamePull * saturate((-fwd.y - 0.26) / 0.16);
                // 眼睛在台地顶面以下（F7p 之后，D-17 / D-29“宫殿成了头顶的星座”）：灯排正好压在崖顶的剪影线上，几十厘米的
                // 边沿会把火吃成断续的虚线。这时火和晕都往眼睛挪 min(0.25 d, _BelowPull)，沿崖边一串稳定的暖点；
                // 远在台地后面的灯（挡住它的岩体比这更厚）照样被挡。物体空间 = 宫殿坐标（y = 0 台地顶）。
                float eyeY = mul(unity_WorldToObject, float4(eye, 1.0)).y;
                float below = saturate((-eyeY - 1.0) / 3.0);
                pull = max(pull, below * min(0.25 * d, _BelowPull));
                size *= (d - pull) / d;
                float3 p = c + fwd * pull + right * v.uv0.x * size.x + upB * v.uv0.y * size.y;
                o.pos = UnityWorldToClipPos(p);
                o.projPos = ComputeScreenPos(o.pos);
                COMPUTE_EYEDEPTH(o.projPos.z);
                o.corner = v.uv0;
                o.info = float4(v.uv1.x, v.uv1.y, exp(-_Atten * d), saturate(1.25 - d / max(_RingFar * 0.8, 1.0)) * (1.0 - below));   // 第 6 轮（D-34 #4）：远处的灯焰放大到 ≥ 2 px 且不压暗——稳定、分得清的暖点；w = 靛环的距离淡出；眼睛在台地以下时没有靛环（第 8 轮：被崖边切开的靛环读成半月）
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 col;
                if (i.info.x > 0.5)
                {
                    float r = length(i.corner);
                    // 第 4 轮：暖芯很小，靛环从 0.12 r 才起，两者不重叠（加色混出丁香紫，美术评审 r3 #4）
                    // 第 8 轮（评审 r5 #2、D-34 #4）：暖芯放大（0.14 r），靛环往外挪（0.25 r 起）、减到 0.9——晕以暖为主，两者仍不重叠
                    float wr = r / _HaloWarmR;
                    float warm = exp(-wr * wr);
                    float ring = smoothstep(0.25, 0.50, r) * saturate(1.0 - r) * saturate(1.0 - r);
                    col = warm * _FlameColor.rgb * _HaloWarm + ring * _HaloMid.rgb * _RingGain * i.info.w;     // 靛环远了淡出：远处只剩暖点，不读成雾里的蓝虚线
                    #if defined(SOFTPARTICLES_ON)
                        // 软粒子：靠近别的面淡出，不在地面上切成半月（关掉时退回硬边，圣经 §1.6）
                        float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.projPos)));
                        col *= saturate((sceneZ - i.projPos.z) / max(_SoftFade, 1e-3) + 0.6);
                    #endif
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
                    float m = lerp(tex2D(_FlipTex, a0).r, tex2D(_FlipTex, a1).r, w) * 0.6;
                    float m2 = m * m;
                    col = m * _FlameColor.rgb + m2 * m2 * 4.0 * _FlameCore.rgb;     // 金的焰身 + 白热的芯（不靠色调映射的肩部变金）
                }
                return float4(col * i.info.z * _Gain, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
