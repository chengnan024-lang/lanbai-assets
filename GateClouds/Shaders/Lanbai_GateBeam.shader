// =====================================================================================================
//  Lanbai / GateBeam  v1 (gate clouds kit, 2026-10-22; cloud art team)   蓝白 · 触手之门 · 光束 / 阴影楔   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  One shader for the two things GateLayout_v2.json describes as "a soft lobe from the wound, WIDENING with
//  distance" and that the Tear kit's constant-width ShaftCard could not draw (gate_test §2.2 item 6):
//    _Mode 0  SHAFT  (shafts.items, 2 beams, under Tear_Root): additive, Blend One One
//    _Mode 1  WEDGE  (shadow_wedges.items, 4, under GateRoot): multiplicative shadow in the luminous fog,
//                    Blend Zero OneMinusSrcAlpha (dst x (1 - a))
//  Set _SrcBlend / _DstBlend with the mode (the builder does: 1/1 for shafts, 0/10 for wedges).
//
//  Mesh: GateClouds_BeamStrip (builder): a strip along +Z, z = 0..1 (32 rows), x = -1 / +1, uv = (x01, z).
//  The object sits at the beam's start with local +Z = its axis (scale 1). The vertex shader turns the strip to face
//  the eye about the axis and widens it: half width(z) = _Beam.x x (1 + (_Beam.z - 1) z), length = _Beam.y; all in
//  the PARENT's units (Tear_Root kit units for the shafts, GateRoot metres for the wedges), like the JSON.
//  Across: one soft lobe; along: a short fade-in at the wound, (1 - z)^1.3 out; fades when seen along the axis and
//  near the eye; the gate fog dims what lies far behind.
// =====================================================================================================
Shader "Lanbai/GateBeam"
{
    Properties
    {
        _Mode ("Mode: 0 shaft (add), 1 wedge (shadow)", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src blend (shaft One, wedge Zero)", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst blend (shaft One, wedge OneMinusSrcAlpha)", Float) = 1
        _Beam ("Beam: half width at the start, length, widen (end / start width), -", Vector) = (46.9, 3437.5, 3.2, 0)
        _Tint ("Shaft fill, LINEAR (Tear kit 0.0362 0.0343 0.0873)", Vector) = (0.0362, 0.0343, 0.0873, 1)
        _Intensity ("Shaft: 0.35 x gain (1.0 / 0.6); wedge: alpha (0.30-0.42)", Range(0, 2)) = 0.35
        _Lobe ("Lobe: sharpness, edge power; fade-in (z), fade-out power", Vector) = (2.6, 1.0, 0.04, 1.3)
        _EdgeFadePow ("Side-view fade power", Float) = 3
        _NearFadeM ("Near fade from .. to (m)", Vector) = (60, 460, 0, 0)
        _FogDensity ("Fog density x scale (dims the far end)", Vector) = (0.0006, 0.5, 0, 0)
        _SoftFade ("Soft depth fade (m; with the SOFTPARTICLES_ON keyword)", Float) = 40
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-2" "RenderType" = "Transparent" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Blend [_SrcBlend] [_DstBlend]
        ZWrite Off ZTest LEqual Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile _ SOFTPARTICLES_ON
            #include "UnityCG.cginc"

            float _Mode, _Intensity, _EdgeFadePow, _SoftFade;
            float3 CentreEye()
            {
            #if defined(USING_STEREO_MATRICES)
                return 0.5 * (unity_StereoWorldSpaceCameraPos[0] + unity_StereoWorldSpaceCameraPos[1]);
            #else
                return _WorldSpaceCameraPos;
            #endif
            }
            float4 _Beam, _Tint, _Lobe, _NearFadeM, _FogDensity;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
            float4 _Udon_InsidePortal;   // x = the tear plane's world z, y = 1 once the bus is through (act 4c)

            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float fade : TEXCOORD1;
                float4 proj : TEXCOORD2;
                float wz : TEXCOORD3;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float z = v.uv.y;
                float3 c = float3(0.0, 0.0, z * _Beam.y);                 // on the axis (object space)
                float3 eyeW = CentreEye();                                  // both eyes see the same strip (CONTROL §3)
                float3 camOS = mul(unity_WorldToObject, float4(eyeW, 1.0)).xyz;
                float3 side = normalize(cross(float3(0.0, 0.0, 1.0), camOS - c) + float3(1e-6, 0.0, 0.0));
                float hw = _Beam.x * (1.0 + (_Beam.z - 1.0) * z);
                float3 p = c + side * ((v.uv.x * 2.0 - 1.0) * hw);
                float3 pw = mul(unity_ObjectToWorld, float4(p, 1.0)).xyz;
                float3 axisW = normalize(mul((float3x3)unity_ObjectToWorld, float3(0.0, 0.0, 1.0)));
                float3 Vw = eyeW - pw;
                float d = length(Vw);
                float perp = length(cross(axisW, Vw / max(d, 1e-4)));
                o.fade = pow(saturate(perp * 1.4), _EdgeFadePow) * smoothstep(_NearFadeM.x, _NearFadeM.y, d)
                       * exp(-_FogDensity.x * _FogDensity.y * d);
                // the whole strip invisible (seen along its axis, or all of it inside the near fade): collapse it, no raster
                // (VR r1: the wedges cost 1.85 FSE at U8side while showing nothing). One decision for every vertex.
                float3 aW = mul(unity_ObjectToWorld, float4(0.0, 0.0, 0.0, 1.0)).xyz;
                float3 bW = mul(unity_ObjectToWorld, float4(0.0, 0.0, _Beam.y, 1.0)).xyz;
                float3 mW = 0.5 * (aW + bW);
                float3 ab = bW - aW;
                float perpM = length(cross(axisW, normalize(eyeW - mW)));
                float whole = pow(saturate(perpM * 1.4), _EdgeFadePow) * smoothstep(_NearFadeM.x, _NearFadeM.y, max(length(aW - eyeW), length(bW - eyeW)));   // all of it near -> gone
                o.pos = (whole < 0.003) ? float4(0.0, 0.0, 0.0, 0.0) : UnityWorldToClipPos(pw);
                o.wz = pw.z;
                o.uv = v.uv;
                o.proj = ComputeScreenPos(o.pos);
                o.proj.z = -mul(UNITY_MATRIX_V, float4(pw, 1.0)).z;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Udon_InsidePortal.y > 0.5 && i.wz > _Udon_InsidePortal.x) discard;   // U9: not into act 4c
                float x = i.uv.x * 2.0 - 1.0;
                float z = i.uv.y;
                float lobe = exp(-_Lobe.x * x * x) * pow(saturate(1.0 - x * x), _Lobe.y);
                float along = smoothstep(0.0, _Lobe.z, z) * pow(saturate(1.0 - z), _Lobe.w);
                float k = lobe * along * i.fade * _Intensity;
            #if defined(SOFTPARTICLES_ON)
                if (_SoftFade > 0.0)
                {
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.proj)));
                    k *= saturate((sceneZ - i.proj.z) / _SoftFade);
                }
            #endif
                return (_Mode < 0.5) ? half4(_Tint.rgb * k, 0.0) : half4(0.0, 0.0, 0.0, saturate(k));
            }
            ENDCG
        }
    }
    FallBack Off
}
