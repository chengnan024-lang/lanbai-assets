// =====================================================================================================
//  Lanbai / CloudCard  v2.0 (cloud cards v2, 2026-10-24; cloud session "云", branch pkg/clouds)   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Checked with Common/Tools~/compile_check (DXC); compile in Unity 2022.3.
//
//  Cloud cards v2 (Clouds_v2/Textures/CloudV2_*): scene-linear, the light stored in WHITE-light channels, the colour
//  given here (same idea as the gate's Lanbai/GateCloudCard, extended to three sun angles + two sky domes):
//      _KeyTex  R = sun 15 deg right of the line of sight (behind the cloud), G = 80 deg, B = 150 deg (behind you),
//               A = coverage (straight alpha)                                  stored sRGB(value / _KScale.x)
//      _SkyTex  R = uniform white upper hemisphere, G = uniform white lower hemisphere   stored sRGB(value / _KScale.y)
//  Per pixel (Source/cardshade.py is the line-by-line numpy port used for every reference image and the solve):
//      rel = horizontal angle between the line of sight (centre eye -> pivot) and the sun; 0 = sun behind the cloud
//      key = piecewise-linear over 15 / 80 / 150 deg (clamped)
//      c   = _SunColor * key + _SkyUpColor * sky.r + _GroundColor * sky.g        (linear; _SunColor includes E)
//      sun on the card's LEFT -> the card is mirrored (_Mirror 0 off / 1 on / 2 auto by the sun's side)
//  then LanbaiFog (direction-dependent fog colour = the sky's horizon), the base melt, the near-eye fade, the soft
//  depth fade (SOFTPARTICLES_ON; hard edge without it), and a sub-pixel calm-down of thin bright rims (D-25).
//
//  Mesh: a quad with its pivot on the card's flat cloud base (cards_v2.json cloud_base_v): x = -0.5..0.5,
//  y = -base..1-base; transform scale = (width m, height m, 1). _Billboard 1 = yaw billboard about the pivot facing the
//  CENTRE eye (both eyes see the same card; vertical stays vertical). _Billboard 0 = the mesh's own orientation
//  (world-fixed panels). Queue Transparent-10; straight alpha.
// =====================================================================================================
Shader "Lanbai/CloudCard"
{
    Properties
    {
        [NoScaleOffset] _KeyTex ("Key - R sun 15 G sun 80 B sun 150 A coverage - sRGB on", 2D) = "black" {}
        [NoScaleOffset] _SkyTex ("Sky - R upper dome G lower dome - sRGB on", 2D) = "black" {}
        _KScale ("Channel scales - x key - y sky", Vector) = (6, 1.5, 0, 0)
        _KeyAngles ("Key angles deg - x R - y G - z B", Vector) = (15, 80, 150, 0)
        _SunColor ("Sun colour x E - linear", Vector) = (6.5733, 2.3553, 0.3508, 0)
        _SkyUpColor ("Upper dome light - linear", Vector) = (0.9995, 1.1493, 1.6336, 0)
        _GroundColor ("Lower dome light - linear", Vector) = (0.8431, 1.0790, 1.5806, 0)
        _SunDirFallback ("Direction to the sun - fallback when _Udon_SunDir is unset", Vector) = (0.5, 0.1045, 0.8597, 0)
        _Gain ("Gain - MPB", Range(0, 4)) = 1
        _Alpha ("Alpha - MPB", Range(0, 1)) = 1
        _Mirror ("Mirror - 0 off 1 on 2 auto - MPB", Float) = 2
        [Toggle] _Billboard ("Yaw billboard to the centre eye", Float) = 1
        _Melt ("Base melt - x from m above the pivot - y over m - z plane y - w 1 uses plane", Vector) = (-10, 60, 0, 0)
        _NearFade ("Near fade - x start m - y full m", Vector) = (30, 120, 0, 0)
        _SoftFade ("Soft depth fade m - needs SOFTPARTICLES_ON", Float) = 40
        _RimTame ("Thin rim calm-down - 0..1", Range(0, 1)) = 0.6
        _FogCap ("Fog Cap", Range(0, 1)) = 1
        _FogHeightFalloff ("Fog Height Scale m - 0 none", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-10" "RenderType" = "Transparent" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off ZTest LEqual Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ SOFTPARTICLES_ON
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"

            sampler2D _KeyTex;
            sampler2D _SkyTex;
            float4 _KeyTex_TexelSize;
            float4 _KScale, _KeyAngles, _SunColor, _SkyUpColor, _GroundColor, _SunDirFallback, _Melt, _NearFade;
            float _Billboard, _SoftFade, _RimTame;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            UNITY_INSTANCING_BUFFER_START(Props)
                UNITY_DEFINE_INSTANCED_PROP(float, _Alpha)
                UNITY_DEFINE_INSTANCED_PROP(float, _Mirror)
                UNITY_DEFINE_INSTANCED_PROP(float, _Gain)
            UNITY_INSTANCING_BUFFER_END(Props)

            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float4 proj : TEXCOORD2;
                float3 pivot : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 pivot = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float3 w;
                if (_Billboard > 0.5)
                {
                    float sx = length(unity_ObjectToWorld._m00_m10_m20);
                    float sy = length(unity_ObjectToWorld._m01_m11_m21);
                    float3 toEye = LanbaiCentreEyePos() - pivot;
                    float2 f = normalize(toEye.xz + float2(1e-5, 0.0));
                    float3 right = float3(f.y, 0.0, -f.x);                // card +x as seen from the eye: to the right
                    w = pivot + right * (v.vertex.x * sx) + float3(0.0, v.vertex.y * sy, 0.0);
                }
                else
                {
                    w = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
                }
                o.wpos = w;
                o.pivot = pivot;
                o.pos = UnityWorldToClipPos(w);
                o.uv = v.uv;
                o.proj = ComputeScreenPos(o.pos);
                o.proj.z = -mul(UNITY_MATRIX_V, float4(w, 1.0)).z;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 eye = LanbaiCentreEyePos();
                float3 sunD = LanbaiSunDir(_SunDirFallback.xyz);

                // the sun's horizontal angle off the card's line of sight, and its side
                float2 los = normalize(i.pivot.xz - eye.xz + float2(1e-5, 0.0));
                float2 sh = normalize(sunD.xz + float2(1e-5, 0.0));
                float rel = degrees(acos(clamp(dot(los, sh), -1.0, 1.0)));
                float sunRight = los.y * sh.x - los.x * sh.y;           // > 0: sun on the right of the view
                float mirMode = UNITY_ACCESS_INSTANCED_PROP(Props, _Mirror);
                float mir = (mirMode > 1.5) ? step(sunRight, 0.0) : mirMode;
                float2 uv = float2(mir > 0.5 ? 1.0 - i.uv.x : i.uv.x, i.uv.y);

                float4 kt = tex2D(_KeyTex, uv);
                float2 st = tex2D(_SkyTex, uv).rg;
                float w1 = saturate((rel - _KeyAngles.x) / max(_KeyAngles.y - _KeyAngles.x, 1e-3));
                float w2 = saturate((rel - _KeyAngles.y) / max(_KeyAngles.z - _KeyAngles.y, 1e-3));
                float key = (kt.r * (1.0 - w1) + kt.g * w1 * (1.0 - w2) + kt.b * w2) * _KScale.x;

                // D-25: thin bright rims (a backlit edge one texel wide) must not crawl when the card is small on
                // screen. Footprint = texels per pixel; at >= 2 the rim's own light is pulled toward the body's.
                float2 fp = fwidth(i.uv * _KeyTex_TexelSize.zw);
                float texPerPx = max(fp.x, fp.y);
                float edge = 1.0 - kt.a;
                key *= 1.0 - _RimTame * edge * saturate(texPerPx - 1.0);

                float3 c = _SunColor.rgb * key + (_SkyUpColor.rgb * st.r + _GroundColor.rgb * st.g) * _KScale.y;
                c *= UNITY_ACCESS_INSTANCED_PROP(Props, _Gain);
                c = LanbaiApplyFog(c, i.wpos);

                float a = kt.a * UNITY_ACCESS_INSTANCED_PROP(Props, _Alpha);
                float baseY = (_Melt.w > 0.5) ? _Melt.z : i.pivot.y;
                a *= smoothstep(baseY + _Melt.x, baseY + _Melt.x + max(_Melt.y, 1e-3), i.wpos.y);
                float d = distance(i.wpos, eye);
                a *= smoothstep(_NearFade.x, max(_NearFade.y, _NearFade.x + 1e-3), d);
            #if defined(SOFTPARTICLES_ON)
                if (_SoftFade > 0.0)
                {
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.proj)));
                    a *= saturate((sceneZ - i.proj.z) / _SoftFade);
                }
            #endif
                return half4(c, a);
            }
            ENDCG
        }
    }
    FallBack Off
}
