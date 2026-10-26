// =====================================================================================================
//  Lanbai/TreeLeaf      蓝白 · 样板树的叶簇卡与远处的剪影卡（D-44 #6）
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//
//  * keepalpha + LightingTreeLeaf returns s.Alpha: without them Unity writes alpha 1 and A2C shows whole cards
//    (local check FromLocal/tree_sample/20261025-101954, patch adopted).
//  * Alpha-to-coverage (bible §6·1 "树用 alpha-to-coverage"): AlphaToMask On, and the alpha is SHARPENED around
//    _Cutoff by its own screen derivative (alpha' = (a - cutoff) / fwidth(a) + 0.5), so with MSAA the leaf edge
//    gets 2-8 coverage steps instead of a hard alpha-test stair, and without MSAA it degrades to a plain cutout.
//    Import the albedo with "Mip Maps Preserve Coverage" (alpha cutoff 0.5) so far mips keep the same leaf area
//    (no thinning / shimmering crown at a distance; director note 2).
//  * Two-sided: Cull Off, the back face flips its normal (VFACE).
//  * Translucency: thin blades pass light from behind: + _TransColor * thin(Mask.R) * lightColor * atten *
//    pow(saturate(dot(V, -L)), 2) * saturate(dot(-N, L) * 0.5 + 0.5)  (forward base and add).
//  * Wet: smoothness lerp(s, 0.60, w); albedo unchanged (bible §1.6). Fog: LanbaiFog. Wind: LanbaiTree.cginc.
//  * _Impostor = 1 (LOD2 cards): no flutter, no normal map, normal bent toward a sphere around the crown so the
//    two crossed cards shade like a mass, not like two flat planes.
// =====================================================================================================
Shader "Lanbai/TreeLeaf"
{
    Properties
    {
        _MainTex ("Albedo sRGB A coverage", 2D) = "white" {}
        _BumpMap ("Normal", 2D) = "bump" {}
        _MaskTex ("Mask R thin G smoothness B AO", 2D) = "white" {}
        _Cutoff ("Coverage Cutoff", Range(0.05, 0.95)) = 0.5
        _TransColor ("Translucency Colour", Color) = (0.55, 0.60, 0.25, 1)
        _TransStrength ("Translucency", Range(0, 1)) = 0.22
        _WetResponse ("Wet Response", Range(0, 1)) = 1
        [Toggle(_LANBAI_IMPOSTOR)] _Impostor ("Impostor Card (LOD2)", Float) = 0
        _ImpostorCentre ("Impostor Crown Centre (object m)", Vector) = (0, 7, 0, 5)
        [Header(Wind)]
        _WindDir ("Wind Direction (world)", Vector) = (1, 0, 0.3, 0)
        _WindStrength ("Wind Sway m", Range(0, 0.2)) = 0.05
        _WindFreq ("Wind Frequency rad per s", Range(0, 3)) = 1.3
        _Flutter ("Flutter m", Range(0, 0.03)) = 0.012
        _FlutterFreq ("Flutter Frequency rad per s", Range(0, 12)) = 5
        [Header(Fog)]
        _FogCap ("Fog Cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "IgnoreProjector" = "True" }
        LOD 300
        Cull Off
        AlphaToMask On

        CGPROGRAM
        #pragma surface surf TreeLeaf vertex:vert finalcolor:fogColor nofog fullforwardshadows keepalpha
        #pragma target 3.5
        #pragma multi_compile_fog
        #pragma multi_compile_instancing
        #pragma shader_feature_local _LANBAI_IMPOSTOR
        #include "LanbaiTree.cginc"
        #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
        #include "UnityPBSLighting.cginc"

        sampler2D _MainTex;
        float4 _MainTex_TexelSize;
        sampler2D _BumpMap;
        sampler2D _MaskTex;
        half _Cutoff;
        half4 _TransColor;
        half _TransStrength;
        float4 _ImpostorCentre;

        struct Input
        {
            float2 uv_MainTex;
            float3 worldPos;
            float3 objPos;
            float facing : VFACE;
        };

        struct SurfaceOutputTree
        {
            fixed3 Albedo;
            fixed3 Normal;
            half3 Emission;
            half Metallic;
            half Smoothness;
            half Occlusion;
            fixed Alpha;
            half Thin;
        };

        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
        #ifdef _LANBAI_IMPOSTOR
            v.color.b = 0;
        #endif
            v.vertex.xyz = LanbaiTreeWind(v.vertex.xyz, v.normal, v.color);
            o.objPos = v.vertex.xyz;
        }

        inline SurfaceOutputStandard LanbaiToStandard(SurfaceOutputTree s)
        {
            SurfaceOutputStandard r;
            r.Albedo = s.Albedo; r.Normal = s.Normal; r.Emission = s.Emission; r.Metallic = s.Metallic;
            r.Smoothness = s.Smoothness; r.Occlusion = s.Occlusion; r.Alpha = s.Alpha;
            return r;
        }

        inline half4 LightingTreeLeaf(SurfaceOutputTree s, half3 viewDir, UnityGI gi)
        {
            half4 c = LightingStandard(LanbaiToStandard(s), viewDir, gi);
            half3 L = gi.light.dir;
            half back = saturate(dot(-s.Normal, L) * 0.5 + 0.5);
            half through = pow(saturate(dot(viewDir, -L)), 2.0);
            c.rgb += _TransColor.rgb * _TransStrength * s.Thin * gi.light.color * back * (0.35 + 0.65 * through);
            c.a = s.Alpha;          // keepalpha: an opaque-queue surface shader otherwise forces alpha 1 (local test 10-25)
            return c;
        }

        inline void LightingTreeLeaf_GI(SurfaceOutputTree s, UnityGIInput data, inout UnityGI gi)
        {
            SurfaceOutputStandard t = LanbaiToStandard(s);
            LightingStandard_GI(t, data, gi);
        }

        void surf(Input IN, inout SurfaceOutputTree o)
        {
            float w = LanbaiTreeWet();
            fixed4 alb = tex2D(_MainTex, IN.uv_MainTex);
            fixed4 m = tex2D(_MaskTex, IN.uv_MainTex);
            // sharpened coverage for alpha-to-coverage (Golus): crisp at any distance, smooth at the edge
            float a = (alb.a - _Cutoff) / max(fwidth(alb.a), 1e-4) + 0.5;
            o.Alpha = saturate(a);
            o.Albedo = alb.rgb * m.b;
        #ifdef _LANBAI_IMPOSTOR
            // bent normal: the card's own normal blended toward the direction from the crown centre
            float3 sph = normalize(IN.objPos - _ImpostorCentre.xyz + float3(0, 0, 1e-4));
            o.Normal = float3(0, 0, 1);
            o.Thin = 0.5;
            o.Occlusion = 1;
            o.Smoothness = lerp(0.30, 0.45, w);
            o.Albedo *= 1.0 - 0.25 * saturate(-sph.y);           // the underside of the mass is darker
        #else
            half3 n = UnpackNormal(tex2D(_BumpMap, IN.uv_MainTex));
            n.z *= IN.facing > 0 ? 1.0 : -1.0;
            o.Normal = n;
            o.Thin = m.r;
            o.Occlusion = 1;
            o.Smoothness = lerp(m.g, 0.60, w);
        #endif
            o.Metallic = 0;
            o.Emission = 0;
        }

        void fogColor(Input IN, SurfaceOutputTree o, inout fixed4 color)
        {
        #ifdef UNITY_PASS_FORWARDADD
            color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);
        #else
            color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
        #endif
        }
        ENDCG

        // shadows: a plain alpha-tested caster (A2C has no meaning in the shadow map)
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            AlphaToMask Off
            Cull Off
            CGPROGRAM
            #pragma vertex vertShadow
            #pragma fragment fragShadow
            #pragma target 3.5
            #pragma multi_compile_shadowcaster
            #pragma multi_compile_instancing
            #include "LanbaiTree.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;
            half _Cutoff;

            struct appS
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 texcoord : TEXCOORD0;
                float4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2fS
            {
                V2F_SHADOW_CASTER;
                float2 uv : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2fS vertShadow(appS v)
            {
                v2fS o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2fS, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                v.vertex.xyz = LanbaiTreeWind(v.vertex.xyz, v.normal, v.color);
                TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
                o.uv = TRANSFORM_TEX(v.texcoord.xy, _MainTex);
                return o;
            }

            float4 fragShadow(v2fS i) : SV_Target
            {
                clip(tex2D(_MainTex, i.uv).a - _Cutoff);
                SHADOW_CASTER_FRAGMENT(i)
            }
            ENDCG
        }
    }
    FallBack Off
}
