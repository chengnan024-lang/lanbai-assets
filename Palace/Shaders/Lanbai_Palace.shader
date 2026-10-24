// =====================================================================================================
//  Lanbai/Palace   蓝白 · 第 7b 幕河伯宫殿的不透明材质（漆、黑漆、云气纹带、鎏金、青铜、石、鱼鳞瓦、紫贝、瓦、木、岩、海草）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check, never in Unity. !!!
//
//  光照：全烘焙（圣经 §1.6“地面世界全烘焙”，D-24）。漫反射 = 反照率 × 光照贴图（烘焙时 Environment = 7b 的 Trilight，
//  环境光因此也在光照贴图里）；没有光照贴图时（烘焙前）退回 ShadeSH9。高光 = 8 盏解析宫灯（LanbaiPalace.cginc）
//  + 一点按水色的环境反射。不画 ForwardAdd：实时点光（车下的那盏）不照宫殿。
//  贴图：_MainTex 反照率（sRGB）、_BumpMap 法线、_MaskMap（R 金属 / 磨损 / POM 高度，G 遮蔽，B 细节 / 虹彩膜厚，A 光滑度）。
//  模式（_Mode）：0 一般（R = 磨损：露出 _WearColor 黑漆底）、1 金属掩码（青铜：R = 金属）、2 珍珠母（鱼鳞屋）、3 宝贝（R = POM 高度）。
//  _SwayAmp > 0：海草（UV2.x = 沿草高度 0..1，UV2.y = 相位），0.15 Hz 摆动；时间 = _Udon_T。
//  最后：LanbaiApplyFog（方向水色）→ _Udon_PalaceVeil（从下面看的雾带，海写）。
// =====================================================================================================
Shader "Lanbai/Palace"
{
    Properties
    {
        [Header(Surface)]
        _MainTex ("Albedo sRGB", 2D) = "white" {}
        _Color ("Tint", Color) = (1, 1, 1, 1)
        [Normal] _BumpMap ("Normal", 2D) = "bump" {}
        _BumpScale ("Normal strength", Float) = 1
        _MaskMap ("Mask R metal-wear-height G occlusion B detail A smoothness", 2D) = "white" {}
        _Smoothness ("Smoothness scale", Range(0, 1.2)) = 1
        _SmoothnessConst ("Smoothness when no mask", Range(0, 1)) = 0.5
        _UseMask ("Use mask", Float) = 1
        [Enum(Standard,0,MetalMask,1,Nacre,2,Cowrie,3)] _Mode ("Mode", Float) = 0
        _Metallic ("Metallic in mode 0", Range(0, 1)) = 0
        _WearColor ("Wear underlayer colour  black lacquer", Color) = (0.157, 0.141, 0.149, 1)
        [Header(Silt)]
        _SiltAmount ("Silt coverage 0 to 1", Range(0, 1)) = 0.55
        _SiltColor ("Silt colour", Color) = (0.369, 0.384, 0.349, 1)
        _SiltSmooth ("Silt smoothness", Range(0, 1)) = 0.10
        _SiltScale ("Silt noise scale per m", Float) = 0.35
        [Header(Nacre)]
        _NacreFace ("Nacre face", Color) = (0.906, 0.788, 0.835, 1)
        _NacreMid ("Nacre mid", Color) = (0.765, 0.890, 0.835, 1)
        _NacreGraze ("Nacre grazing", Color) = (0.725, 0.776, 0.918, 1)
        [Header(Cowrie parallax)]
        _POMHeight ("POM height m", Float) = 0.015
        _POMTile ("Texture tile m", Float) = 1
        _POMFade ("POM fade distance m", Float) = 40
        [Header(Lamps and water)]
        _LampGain ("Analytic lamp specular gain", Float) = 1
        _EnvSpec ("Ambient reflection of the water colour", Float) = 0.6
        [Header(Seaweed sway)]
        _SwayAmp ("Sway amplitude m at the tip  0 off", Float) = 0
        _SwayHz ("Sway frequency Hz", Float) = 0.15
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            Cull [_Cull]
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #pragma multi_compile _ LIGHTMAP_ON
            #pragma multi_compile _ DIRLIGHTMAP_COMBINED
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
            #include "LanbaiPalace.cginc"

            sampler2D _MainTex, _BumpMap, _MaskMap;
            float4 _MainTex_ST, _Color, _WearColor, _SiltColor, _NacreFace, _NacreMid, _NacreGraze;
            float _BumpScale, _Smoothness, _SmoothnessConst, _UseMask, _Mode, _Metallic, _SiltAmount, _SiltSmooth, _SiltScale;
            float _POMHeight, _POMTile, _POMFade, _LampGain, _EnvSpec, _SwayAmp, _SwayHz;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 tangent : TANGENT;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float2 lmuv : TEXCOORD1;
                float3 posWS : TEXCOORD2;
                float3 nWS : TEXCOORD3;
                float4 tWS : TEXCOORD4;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 posWS = mul(unity_ObjectToWorld, v.vertex).xyz;
                if (_SwayAmp > 0.0)
                {
                    // 海草：沿草的高度二次方增长的摆动，两个频率叠一点，世界 x / z 两个方向
                    float h = v.uv2.x;
                    float ph = v.uv2.y * 6.2831853;
                    float tt = _Udon_T * _SwayHz * 6.2831853;
                    float s = h * h * _SwayAmp;
                    posWS.x += s * (sin(tt + ph) + 0.35 * sin(2.3 * tt + 1.7 * ph));
                    posWS.z += s * 0.6 * cos(0.8 * tt + ph);
                }
                o.posWS = posWS;
                o.pos = UnityWorldToClipPos(posWS);
                o.uv = TRANSFORM_TEX(v.uv0, _MainTex);
                o.lmuv = v.uv1 * unity_LightmapST.xy + unity_LightmapST.zw;
                o.nWS = UnityObjectToWorldNormal(v.normal);
                o.tWS = float4(UnityObjectToWorldDir(v.tangent.xyz), v.tangent.w * unity_WorldTransformParams.w);
                return o;
            }

            float4 frag(v2f i, float facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 eye = LanbaiCentreEyePos();
                float3 V = normalize(eye - i.posWS);
                float3 Ng = normalize(i.nWS) * (facing >= 0 ? 1.0 : -1.0);
                float3 T = normalize(i.tWS.xyz - Ng * dot(i.tWS.xyz, Ng));
                float3 B = cross(Ng, T) * i.tWS.w;
                float2 uv = i.uv;
                float dist = length(eye - i.posWS);
                if (_Mode > 2.5)
                {
                    // 宝贝：视差（8 步陡峭视差 + 一次线性细化），40 m 外淡掉
                    float fade = saturate(1.0 - dist / max(_POMFade, 1.0));
                    if (fade > 0.0)
                    {
                        float3 Vt = float3(dot(V, T), dot(V, B), dot(V, Ng));
                        float2 stepUV = -Vt.xy / max(Vt.z, 0.2) * (_POMHeight / max(_POMTile, 1e-3)) * fade / 8.0;
                        float layer = 1.0;
                        float2 cur = uv;
                        float hPrev = 1.0;
                        float h = tex2Dlod(_MaskMap, float4(cur, 0, 0)).r;
                        [unroll] for (int k = 0; k < 8; k++)
                        {
                            if (h >= layer) break;
                            hPrev = h;
                            layer -= 0.125;
                            cur += stepUV;
                            h = tex2Dlod(_MaskMap, float4(cur, 0, 0)).r;
                        }
                        uv = cur;
                    }
                }
                float4 alb4 = tex2D(_MainTex, uv) * _Color;
                float3 albedo = alb4.rgb;
                float4 mask = _UseMask > 0.5 ? tex2D(_MaskMap, uv) : float4(0, 1, 0.5, _SmoothnessConst);
                float3 nTS = UnpackNormal(tex2D(_BumpMap, uv));
                nTS.xy *= _BumpScale;
                nTS = normalize(nTS);
                float3 N = normalize(T * nTS.x + B * nTS.y + Ng * nTS.z);
                float smooth = saturate(mask.a * _Smoothness);
                float metal = _Metallic;
                if (_Mode < 0.5)
                    albedo = lerp(albedo, _WearColor.rgb, mask.r);
                else if (_Mode < 1.5)
                    metal = mask.r;
                // 淤泥（朝上的面）
                float silt = LanbaiSilt(i.posWS, Ng, _SiltAmount, _SiltScale);
                albedo = lerp(albedo, _SiltColor.rgb, silt);
                smooth = lerp(smooth, _SiltSmooth, silt);
                metal *= 1.0 - silt;
                // 漫反射：烘焙
                float3 diffLight;
                #if defined(LIGHTMAP_ON)
                    diffLight = DecodeLightmap(UNITY_SAMPLE_TEX2D(unity_Lightmap, i.lmuv));
                    #if defined(DIRLIGHTMAP_COMBINED)
                        float4 dirLM = UNITY_SAMPLE_TEX2D_SAMPLER(unity_LightmapInd, unity_Lightmap, i.lmuv);
                        diffLight = DecodeDirectionalLightmap(diffLight, dirLM, N);
                    #endif
                #else
                    diffLight = ShadeSH9(float4(N, 1.0));
                #endif
                float occ = mask.g;
                float3 diffColor = albedo * (1.0 - metal);
                float3 F0 = lerp(float3(0.04, 0.04, 0.04), albedo, metal);
                float NdotV = saturate(dot(N, V));
                if (_Mode > 1.5 && _Mode < 2.5)
                    F0 = 0.08 * LanbaiNacre(NdotV, _NacreFace.rgb, _NacreMid.rgb, _NacreGraze.rgb, mask.b) / 0.85 * (1.0 - silt) + 0.04 * silt;
                float rough = 1.0 - smooth;
                float alpha = max(rough * rough, 0.002);
                float3 spec = LanbaiPalaceLamps(i.posWS, N, V, alpha, F0) * _LampGain;
                if (_Mode > 1.5 && _Mode < 2.5)
                    spec *= LanbaiNacre(NdotV, _NacreFace.rgb, _NacreMid.rgb, _NacreGraze.rgb, mask.b) * 1.6;
                // 环境反射：反射方向的水色（LanbaiHorizon），按菲涅耳与粗糙度压
                float3 R = reflect(-V, N);
                float3 Fr = F0 + (1.0 - F0) * pow(1.0 - NdotV, 5.0) * (1.0 - rough);
                float3 env = LanbaiHorizon(R) * Fr * _EnvSpec * occ * (1.0 - 0.7 * rough);
                float3 col = diffColor * diffLight * occ + spec + env;
                col = LanbaiApplyFog(col, i.posWS);
                float veil = LanbaiPalaceVeil(i.posWS, eye);
                col = lerp(col, LanbaiHorizon(normalize(i.posWS - eye)), veil);
                return float4(col, 1.0);
            }
            ENDCG
        }

        // 烘焙用：反照率（含淤泥）与自发光 0
        Pass
        {
            Tags { "LightMode" = "Meta" }
            Cull Off
            CGPROGRAM
            #pragma vertex vert_meta
            #pragma fragment frag_meta
            #pragma target 3.5
            #include "UnityCG.cginc"
            #include "UnityMetaPass.cginc"
            #include "LanbaiPalace.cginc"

            sampler2D _MainTex, _MaskMap;
            float4 _MainTex_ST, _Color, _WearColor, _SiltColor;
            float _Mode, _Metallic, _SiltAmount, _SiltScale, _UseMask;

            struct appm
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 texcoord : TEXCOORD0;
                float2 texcoord1 : TEXCOORD1;
                float2 texcoord2 : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2fm
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 posWS : TEXCOORD1;
                float3 nWS : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2fm vert_meta(appm v)
            {
                v2fm o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2fm, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityMetaVertexPosition(v.vertex, v.texcoord1.xy, v.texcoord2.xy, unity_LightmapST, unity_DynamicLightmapST);
                o.uv = TRANSFORM_TEX(v.texcoord, _MainTex);
                o.posWS = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.nWS = UnityObjectToWorldNormal(v.normal);
                return o;
            }

            float4 frag_meta(v2fm i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                UnityMetaInput m;
                UNITY_INITIALIZE_OUTPUT(UnityMetaInput, m);
                float3 albedo = tex2D(_MainTex, i.uv).rgb * _Color.rgb;
                float4 mask = _UseMask > 0.5 ? tex2D(_MaskMap, i.uv) : float4(0, 1, 0.5, 0.5);
                float metal = _Metallic;
                if (_Mode < 0.5) albedo = lerp(albedo, _WearColor.rgb, mask.r);
                else if (_Mode < 1.5) metal = mask.r;
                float silt = LanbaiSilt(i.posWS, normalize(i.nWS), _SiltAmount, _SiltScale);
                albedo = lerp(albedo, _SiltColor.rgb, silt);
                metal *= 1.0 - silt;
                m.Albedo = albedo * (1.0 - metal * 0.5);
                m.Emission = 0;
                return UnityMetaFragment(m);
            }
            ENDCG
        }

        // 主光的阴影图与深度预渲染要它（D-24：宫殿自己不受实时阴影，但要写进深度，软粒子 / 鱼的深度测试用）
        Pass
        {
            Tags { "LightMode" = "ShadowCaster" }
            CGPROGRAM
            #pragma vertex vert_sc
            #pragma fragment frag_sc
            #pragma target 3.5
            #pragma multi_compile_shadowcaster
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            struct apps
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2fs
            {
                V2F_SHADOW_CASTER;
                UNITY_VERTEX_OUTPUT_STEREO
            };
            v2fs vert_sc(apps v)
            {
                v2fs o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2fs, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
                return o;
            }
            float4 frag_sc(v2fs i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                SHADOW_CASTER_FRAGMENT(i)
            }
            ENDCG
        }
    }
    FallBack Off
}
