// =====================================================================================================
//  Lanbai/PalaceFish   蓝白 · 第 7b 幕的银鱼（圣经 §6·7b：1 500 条，12–20 cm，背 #34444E、腹侧 #B8C0C4、0.85；
//                      绕大殿的环面运动，半径 35 m、0.03 转/秒；转身穿过灯光时闪；lite 700）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check, never in Unity. !!!
//
//  网格 Palace/Models/Palace_Fish.fbx：1 500 份同一条鱼（≈ 68 三角）合成一张网格，**一次绘制，不用 GPU instancing 的 API**
//  （Udon 不需要调 DrawMeshInstanced）。每份的顶点：POSITION = 鱼自身坐标（鼻子朝 +z，长 1），UV0 = 鱼身贴图坐标，
//  UV1.x = 鱼的编号 i。位置与朝向在这里按时间算，**与 Palace/Source/kit/fish.py 的 state() 逐行对应**（参考图用的同一套数学）。
//  时间 = _Udon_T。坐标：_Centre 等都是宫殿坐标（R_Palace 的局部），乘 unity_ObjectToWorld 进世界 —— 网格挂在 R_Palace 下、局部变换为单位。
//  i ≥ _Count 的鱼（lite 模式）折叠成退化三角（不画）；B 群（i ≥ 1350）只在 |t − 720| ≤ 90 s 画。
//  光：ShadeSH9（鱼不进光照贴图）+ 8 盏解析宫灯的 GGX 高光（“转身穿过灯光时闪”）+ LanbaiFog。不吃 _Udon_PalaceVeil。
// =====================================================================================================
Shader "Lanbai/PalaceFish"
{
    Properties
    {
        _Back ("Back colour", Color) = (0.204, 0.267, 0.306, 1)
        _Belly ("Belly colour", Color) = (0.722, 0.753, 0.769, 1)
        _Smoothness ("Smoothness", Range(0, 1)) = 0.85
        _Centre ("Torus centre  palace frame", Vector) = (-38, 14, 356.6, 0)
        _Torus ("Torus R  tube  rev per s  schools", Vector) = (35, 9, 0.03, 6)
        _PassPoint ("B school crossing point at 720  palace frame", Vector) = (3.2, 5.8, 239, 720)
        _PassVel ("B school velocity m per s", Vector) = (-2.2, 0.1, 0.4, 0)
        _Count ("Fish drawn  1500 or 700 lite", Float) = 1500
        _CountA ("Size of school A", Float) = 1350
        _LampGain ("Lamp glint gain", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry+10" }
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Cull Back
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
            #include "LanbaiPalace.cginc"

            float4 _Back, _Belly, _Centre, _Torus, _PassPoint, _PassVel;
            float _Smoothness, _Count, _CountA, _LampGain;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 posWS : TEXCOORD0;
                float3 nWS : TEXCOORD1;
                float side : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            float hashk(float i, float k)
            {
                return frac(abs(sin(i * (12.9898 + k * 3.17) + 78.233 * (k + 1.0)) * 43758.5453));
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float i = floor(v.uv1.x + 0.5);
                float t = _Udon_T;
                float r1 = hashk(i, 0), r2 = hashk(i, 1), r3 = hashk(i, 2), r4 = hashk(i, 3);
                float L = 0.12 + 0.08 * r2;
                float sch = fmod(i, _Torus.w);
                float th = 6.2831853 * sch / _Torus.w + 0.35 * (r1 - 0.5) + 6.2831853 * _Torus.z * t + 0.02 * sin(0.7 * t + 6.283 * r3);
                float ph = 6.2831853 * sch / _Torus.w * 1.7 + 0.15 * t + 1.2 * (r3 - 0.5);
                float rho = 2.0 + (_Torus.y - 2.0) * sqrt(r4);
                float ring = _Torus.x + rho * cos(ph);
                float3 P = _Centre.xyz + float3(ring * cos(th), rho * sin(ph), ring * sin(th));
                float dth = 6.2831853 * _Torus.z, dph = 0.15;
                float3 vel = float3(-ring * sin(th) * dth - rho * sin(ph) * dph * cos(th),
                                    rho * cos(ph) * dph,
                                    ring * cos(th) * dth - rho * sin(ph) * dph * sin(th));
                float visible = (i < _Count || i >= _CountA) ? 1.0 : 0.0;
                if (i >= _CountA)
                {
                    float3 off = float3((r1 - 0.5) * 6.0, (r2 - 0.5) * 2.4, (r3 - 0.5) * 4.0);
                    P = _PassPoint.xyz + (t - _PassPoint.w) * _PassVel.xyz + off;
                    vel = _PassVel.xyz;
                    visible *= abs(t - _PassPoint.w) <= 90.0 ? 1.0 : 0.0;
                }
                float3 f = normalize(vel);
                float3 r = normalize(cross(float3(0, 1, 0), f) + float3(0, 0, 1e-5));
                float3 u = cross(f, r);
                float3 local = v.vertex.xyz * L * visible;
                float3 posPal = P + r * local.x + u * local.y + f * local.z;
                float3 nPal = normalize(r * v.normal.x + u * v.normal.y + f * v.normal.z);
                o.posWS = mul(unity_ObjectToWorld, float4(posPal, 1.0)).xyz;
                o.nWS = normalize(mul((float3x3)unity_ObjectToWorld, nPal));
                o.side = v.uv0.y;
                o.pos = UnityWorldToClipPos(o.posWS);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 eye = LanbaiCentreEyePos();
                float3 V = normalize(eye - i.posWS);
                float3 N = normalize(i.nWS);
                float3 albedo = lerp(_Belly.rgb, _Back.rgb, smoothstep(0.45, 0.75, i.side));
                float rough = 1.0 - _Smoothness;
                float alpha = max(rough * rough, 0.002);
                float3 spec = LanbaiPalaceLamps(i.posWS, N, V, alpha, float3(0.06, 0.06, 0.065)) * _LampGain;
                float3 col = albedo * ShadeSH9(float4(N, 1.0)) + spec;
                col = LanbaiApplyFog(col, i.posWS);
                return float4(col, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
