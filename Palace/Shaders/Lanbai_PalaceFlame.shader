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
        _HaloPull ("Halo depth pulled toward eye m  max, also <= d/2", Float) = 1.0
        _FlamePull ("Flame pulled toward eye m when seen steeply from below", Float) = 1.5
        _BelowPull ("Flame depth pull m when the eye is below the lip", Float) = 2.5
        _LipY ("Terrace lip bottom y  palace frame, from Sea", Float) = -13
        [Header(Cliff occlusion fade  director 10-26)]
        _CliffEdge ("Cliff: edge x, lowest lip y, lip x, slope bump m", Vector) = (-8, -14.2, -8.6, 0.52)
        _CliffSlope ("Cliff: slope width m, depth m, pad m, sink rate m per s", Vector) = (3.6, 9.0, 0.08, 1.5)
        _CliffSlopeZ ("Cliff: slope z start, full start, full end, end", Vector) = (48, 54, 296, 306)
        _CliffFadeS ("Cliff: fade takes at least this many s while the bus sinks", Float) = 1.0
        _CliffEyeF8 ("Cliff: main eye at F8 in palace coords  lamps hidden then stay hidden through F8", Vector) = (1.4025, -47.25, 309.2917, 0)
        _CliffHaloK ("Cliff: halo radius <= this x margin / tL  halo never overlaps the brink", Float) = 0.6
        _SoftFade ("Soft particle fade m", Float) = 1.0
        _HaloMid ("Halo indigo mid linear  fill 446282", Vector) = (0.0578, 0.1221, 0.2232, 0)
        _Atten ("Attenuation per m  FogMode 2", Float) = 0.004
        _FPS ("Flipbook frames per second", Float) = 6
        _MinPixels ("Minimum flame half size px", Float) = 2.0
        _RingFar ("Halo indigo ring fades out by this distance m", Float) = 150
        _Gain ("Gain  driver", Float) = 1
        _FadeStart ("F8: first lamp starts dimming at t", Float) = 835.16
        _FadeSpan ("F8: lamps start dimming over this many s  staggered by phase", Float) = 36
        _FadeLen ("F8: each lamp dims over this many s", Float) = 4
    }
    SubShader
    {
        Tags { "DisableBatching"="True" "RenderType" = "Transparent" "Queue" = "Transparent+10" "IgnoreProjector" = "True" }
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
            float4 _CliffEdge, _CliffSlope, _CliffSlopeZ, _CliffEyeF8;
            float _CliffFadeS, _CliffHaloK;
            float _HaloRadius, _HaloWarm, _HaloWarmR, _RingGain, _HaloPull, _FlamePull, _BelowPull, _LipY, _Atten, _FPS, _MinPixels, _Gain, _SoftFade, _RingFar, _FadeStart, _FadeSpan, _FadeLen;
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

            // 总导演 10-26：被崖口挡住多半的灯，车下沉时按几何遮挡在 >= _CliffFadeS 秒里淡掉——只往“藏”的方向
            // （一盏灯要么读得出，要么不在；不留被切成小残点的灯，也不透过岩体露出来）。
            // 遮挡体是保守的近似（= palace_layout.cliff_vis）：崖口顶边的斜坡（不带起伏的下限 + 起伏的上包络）、
            // 坡底往下 4.4 m 内外凸到 0.9 m 的石壁、最低处的参差下唇。视线从坡上越过，或从下唇下面穿过（下缘以下台地没有底面），才算看得见。
            // 物体空间 = 宫殿坐标（灯焰网格挂在 R_Palace 下、局部变换为单位），所以 R_Palace 的平移和 F7 的转角都不用管。
            float LanbaiCliffSmooth(float a, float b, float x) { float u = saturate((x - a) / (b - a)); return u * u * (3.0 - 2.0 * u); }

            // 返回（余量 m、视线在崖口处的参数 tL、可见度）；没有崖口挡时 (1e9, 0, 1)
            float3 LanbaiCliffMargin(float3 e, float3 c)
            {
                float edgeX = _CliffEdge.x;
                if (e.x <= edgeX + 0.9 || c.x >= edgeX) return float3(1e9, 0.0, 1.0);
                float invDx = 1.0 / (c.x - e.x);
                float3 dir = c - e;
                // 坡在视线穿过崖口处的 z 上的宽、深
                float zE = e.z + dir.z * (edgeX - e.x) * invDx;
                bool big = _CliffSlope.x > 1.0;
                float w = big ? LanbaiCliffSmooth(_CliffSlopeZ.x, _CliffSlopeZ.y, zE) * (1.0 - LanbaiCliffSmooth(_CliffSlopeZ.z, _CliffSlopeZ.w, zE)) : 0.0;
                float W = 0.8 + w * (_CliffSlope.x - 0.8);
                float D = 1.6 + w * (_CliffSlope.y - 1.6);
                float mOver = 1e9;
                const float ks[11] = { 0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0 };
                [unroll] for (int j = 0; j < 11; j++)
                {
                    float k = ks[j];
                    float x = edgeX - W * (1.0 - k);
                    float sP = big ? ((k < 0.15 ? k * k / 0.3 : k - 0.075) / 0.925) : pow(k, 1.5);
                    float yr = e.y + dir.y * (x - e.x) * invDx;
                    mOver = min(mOver, yr - (-D * sP + _CliffEdge.w * w * sin(3.14159265 * k)));
                }
                [unroll] for (int q = 1; q <= 4; q++)
                {
                    float jq = q * 0.25;
                    float yw = e.y + dir.y * (edgeX + 0.9 * jq - e.x) * invDx;
                    mOver = min(mOver, yw - (-D - 4.4 * jq));
                }
                mOver -= _CliffSlope.z;
                float tL = (_CliffEdge.z - e.x) * invDx;
                float mUnder = _CliffEdge.y - (e.y + dir.y * tL) - _CliffSlope.z;
                float m = max(mOver, mUnder);
                float width = max(0.1, _CliffFadeS * _CliffSlope.w * (1.0 - tL));
                return float3(m, tL, saturate(m / width));
            }

            // 复核 r10d #2：F8（_FadeStart）起，一盏灯不会比 F8 开始那一刻更亮——那时被崖口藏着的灯，F8 里不再回来（只看 _Udon_T，没有跨帧状态）
            float LanbaiCliffVis(float3 e, float3 c)
            {
                float v = LanbaiCliffMargin(e, c).z;
                if (_Udon_T >= _FadeStart) v = min(v, LanbaiCliffMargin(_CliffEyeF8.xyz, c).z);
                return v;
            }

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
                float eyeY = mul(unity_WorldToObject, float4(eye, 1.0)).y;     // 物体空间 = 宫殿坐标（y = 0 台地顶）
                // 终审 10-25 #3：触发条件 = 眼睛低于台地下唇（_LipY，海的约定；D-34 #4 以后约 −9 m），不再是“低于台面”
                float below = saturate((_LipY - eyeY - 0.5) / 2.0);
                float sph = halo ? 1.0 : max(saturate((abs(fwd.y) - 0.34) * 3.0), below);   // 20° 起变圆；从下唇以下看一律是圆点
                float3 upB = normalize(lerp(up, upS, sph));
                float2 size = halo ? float2(_HaloRadius, _HaloRadius) : _FlameSize.xy;
                float3 eyeO = mul(unity_WorldToObject, float4(eye, 1.0)).xyz;
                if (halo)
                {
                    // 复核 r10d #1：晕的半径 ≤ _CliffHaloK × 余量 / tL——晕碰不到崖口的剪影，就不会被深度测试切成一条直边
                    float3 cm = LanbaiCliffMargin(eyeO, v.vertex.xyz);
                    if (cm.y > 0.0) size *= saturate(_CliffHaloK * max(cm.x, 0.0) / (cm.y * _HaloRadius));
                }
                // 最小像素：一个像素在 d 处的米数 = 2d / (P11 · 屏高)
                float pix = 2.0 * d / (abs(unity_CameraProjection._m11) * _ScreenParams.y);
                float s = halo ? 1.0 : max(1.0, _MinPixels * pix / max(size.x, 1e-4));
                size *= s;
                // 终审 10-25 #3：深度往眼睛挪，但**只挪 clip z**——公告板按真位置、每只眼各自投影（双眼视差对），
                // 所以头顶的星座仍在 60–270 m 外，不会缩成近处的萤火虫。挪多少：
                //   晕 ≤ min(_HaloPull 1 m, d/2)（晕是灯和眼睛之间那段水的散射，不该被栏杆、柱子切成半月）；
                //   火：从下面陡着看（仰角 15–25° 起）_FlamePull 1.5 m；眼睛低于下唇时 _BelowPull 2.5 m（贴着崖边的灯焰不被几十厘米的边沿吃掉）。
                //   远在台地后面的灯（挡住它的岩体比这厚）照样被挡；F7p 之前不会透过台地露出来。
                float pull = halo ? min(_HaloPull, 0.5 * d)
                                  : max(_FlamePull * saturate((-fwd.y - 0.26) / 0.16), below * _BelowPull);
                float3 p = c + right * v.uv0.x * size.x + upB * v.uv0.y * size.y;
                float4 cT = UnityWorldToClipPos(p);
                float3 pP = p + fwd * pull;
                float4 cP = UnityWorldToClipPos(pP);
                o.pos = cT;
                o.pos.z = cP.z / cP.w * cT.w;
                o.projPos = ComputeScreenPos(cT);
                o.projPos.z = -mul(UNITY_MATRIX_V, float4(pP, 1.0)).z;          // 软粒子按挪过以后的深度
                o.corner = v.uv0;
                float cliffVis = LanbaiCliffVis(eyeO, v.vertex.xyz);
                o.info = float4(v.uv1.x, v.uv1.y, exp(-_Atten * d) * cliffVis, saturate(1.25 - d / max(_RingFar * 0.8, 1.0)) * (1.0 - below));   // 第 6 轮（D-34 #4）：远处的灯焰放大到 ≥ 2 px 且不压暗——稳定、分得清的暖点；w = 靛环的距离淡出；眼睛在台地以下时没有靛环（第 8 轮：被崖边切开的靛环读成半月）
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
                // 终审 10-25：F8 → 7c 前的 40 秒，星座一盏盏暗下去（每盏按相位错开、4 秒淡出，只看 _Udon_T，D-33 #6）；
                // 875.16 全灭，比时间窗的末尾（876.16）早一秒，所以不会在窗口结束那一帧整片消失
                float s0 = _FadeStart + i.info.y * _FadeSpan;
                float fadeF8 = 1.0 - smoothstep(s0, s0 + _FadeLen, _Udon_T);
                return float4(col * i.info.z * _Gain * fadeF8, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
