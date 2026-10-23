// =====================================================================================================
//  Lanbai / GateCloudCard  v1 (gate clouds kit, 2026-10-22; cloud art team)   蓝白 · 触手之门 · 云卡   Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  The gate's cloud TOWERS, far banks, horizon masses and mist (GateClouds_Layout.json), drawn with the v2 gate cards
//  (Textures/GateCard_*.png, Source/gate_cards.py): scene-linear, the light in separate channels
//      R = moon behind-right 35 deg, G = moon behind-right 70 deg, B = sky, A = coverage
//  so each card is lit for where it stands: the moon's angle off the card's line of sight picks R..G (and the mirror,
//  set per card by the builder: the moon on the card's left = mirrored). Then the gate's fog (LanbaiGateSky.cginc),
//  the base melting into the deck, the soft forward-scatter lining near the moon (GateLayout round 8), and
//  _Alpha (the tower sink / fade, driven per renderer by LanbaiGateClouds).
//
//  Mesh: GateClouds_Card_<shape> (builder): a quad, pivot on the card's flat cloud base (cloud_base_v), x = -0.5..0.5,
//  y = -base..1-base; the transform scale = (width m, height m, 1). Yaw billboard about the pivot (vertical stays
//  vertical), facing the CENTRE eye so both eyes see the same card.
//  Queue: far / horizon 2990, towers / mist 3000 (set on the material by the builder). Blend: straight alpha.
// =====================================================================================================
Shader "Lanbai/GateCloudCard"
{
    Properties
    {
        [NoScaleOffset] _MainTex ("GateCard (R moon 35, G moon 70, B sky, A coverage; sRGB ON)", 2D) = "black" {}
        _Scale ("Channel scales from gate_cards.json (R, G, B)", Vector) = (1, 1, 1, 0)
        _Mirror ("Mirrored (moon on the card's left; MPB)", Float) = 0
        _MoonColor ("Moon colour #D6E4FF, linear", Vector) = (0.6724, 0.7758, 1.0, 1)
        _MoonE ("Moon on the cards (1 = the bake's light)", Range(0, 4)) = 0.146
        _SkyColor ("Sky light colour, linear (the band, desaturated)", Vector) = (0.060, 0.064, 0.088, 1)
        _SkyE ("Sky light on the cards", Range(0, 4)) = 0.89
        _Gain ("Card gain (JSON gain; MPB)", Range(0, 3)) = 1
        _Alpha ("Alpha (JSON opacity x sink fade; MPB)", Range(0, 1)) = 1
        _Lining ("Lining near the moon: gain, width (deg), max angle (deg), -", Vector) = (0.35, 7, 15, 0)
        _Melt ("Base melt: from (m above the cloud top), over (m)", Vector) = (-20, 90, 0, 0)
        _Feather ("Bottom feather over the quad (0..1): alpha, sky channel", Vector) = (0.15, 0.3, 0, 0)
        _FogDensity ("Fog density, scale, moon air, CAP (towers 0.5, far / horizon 0.62, mist 0.7)", Vector) = (0.0006, 1.0, 0.35, 0.5)
        _SoftFade ("Soft depth fade (m; with the SOFTPARTICLES_ON keyword)", Float) = 30
        _CloudTopY ("Cloud top world y (fallback; _Udon_CloudTop wins)", Float) = -57.4
        _RimDir ("Direction to the moon (fallback; _Udon_MoonDir wins)", Vector) = (-0.2059, 0.1392, 0.9686, 0)

        // shared with LanbaiGateSky.cginc (same values as the skybox and the arms)
        _HazeNear ("Haze Band Next To The Tear, linear", Vector) = (0.1085, 0.1130, 0.1641, 1)
        _HazeFar ("Haze Band 50 deg Away, linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _Void ("Void, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation", Vector) = (6, 22, 2, 0)
        _BelowHorizon ("Below the horizon", Vector) = (-25, 0, 0.55, 0)
        _BelowDesat ("Below-horizon desaturation", Range(0, 1)) = 0.6
        _BackBand ("Back band", Range(0, 2)) = 0.55
        _TearPos ("Tear core fallback (world)", Vector) = (0, 297, 1800, 0)
        _MoonGlowColor ("Moon aureole, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole shape", Vector) = (1.6, 0.9, 0.06, 0.32)
        _HaloColor ("Halo (unused here)", Vector) = (0.195, 0.198, 0.332, 1)
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
            #pragma multi_compile _ SOFTPARTICLES_ON
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"

            sampler2D _MainTex;
            float4 _Scale, _MoonColor, _SkyColor, _Lining, _Melt, _Feather, _FogDensity, _RimDir;
            float _MoonE, _SkyE, _SoftFade, _CloudTopY;
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            UNITY_INSTANCING_BUFFER_START(Props)
                UNITY_DEFINE_INSTANCED_PROP(float, _Alpha)
                UNITY_DEFINE_INSTANCED_PROP(float, _Mirror)
                UNITY_DEFINE_INSTANCED_PROP(float, _Gain)
            UNITY_INSTANCING_BUFFER_END(Props)

            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 uv : TEXCOORD0;      // xy = texture, z = 0..1 up the cropped quad (the builder's uv2.y)
                float3 wpos : TEXCOORD1;
                float4 proj : TEXCOORD2;
                float3 pivot : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            float3 CentreEye()
            {
            #if defined(USING_STEREO_MATRICES)
                return 0.5 * (unity_StereoWorldSpaceCameraPos[0] + unity_StereoWorldSpaceCameraPos[1]);
            #else
                return _WorldSpaceCameraPos;
            #endif
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 pivot = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float sx = length(unity_ObjectToWorld._m00_m10_m20);
                float sy = length(unity_ObjectToWorld._m01_m11_m21);
                float3 toEye = CentreEye() - pivot;
                float2 f = normalize(toEye.xz + float2(1e-5, 0.0));
                float3 right = float3(-f.y, 0.0, f.x);                    // card x, seen from the eye: to the right (tech r1 #3)
                float3 w = pivot + right * (v.vertex.x * sx) + float3(0.0, v.vertex.y * sy, 0.0);
                o.wpos = w;
                o.pivot = pivot;
                o.pos = UnityWorldToClipPos(w);
                o.uv = float3(v.uv, v.uv2.y);
                o.proj = ComputeScreenPos(o.pos);
                o.proj.z = -mul(UNITY_MATRIX_V, float4(w, 1.0)).z;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Udon_InsidePortal.y > 0.5 && _WorldSpaceCameraPos.z > _Udon_InsidePortal.x && i.wpos.z > _Udon_InsidePortal.x) discard;   // U9: not into act 4c
                float mir = UNITY_ACCESS_INSTANCED_PROP(Props, _Mirror);
                float alphaK = UNITY_ACCESS_INSTANCED_PROP(Props, _Alpha);
                float2 uv = float2(mir > 0.5 ? 1.0 - i.uv.x : i.uv.x, i.uv.y);
                float4 tx = tex2D(_MainTex, uv);
                // round 4 (art r2): the lowest 15 % of the card feathered, its sky channel over the lowest 30 % (no bright bottom edge)
                tx.b *= smoothstep(0.0, max(_Feather.y, 1e-4), i.uv.z);
                tx.a *= smoothstep(0.0, max(_Feather.x, 1e-4), i.uv.z);

                float3 eye = _WorldSpaceCameraPos;
                float3 V = i.wpos - eye;
                float dist = length(V);
                V /= dist;
                float3 moonD = LanbaiMoonDir(_RimDir.xyz);

                // the moon's horizontal angle off the card's line of sight (from the centre eye to the pivot):
                // 35 deg -> R, 70 deg -> G (clamped beyond)
                float2 los = normalize(i.pivot.xz - CentreEye().xz + float2(1e-5, 0.0));
                float2 mh = normalize(moonD.xz + float2(1e-5, 0.0));
                float rel = degrees(acos(clamp(dot(los, mh), -1.0, 1.0)));
                float wk = saturate((rel - 35.0) / 35.0);
                float moonC = lerp(tx.r * _Scale.x, tx.g * _Scale.y, wk);
                // forward-scatter lining near the moon (round 8: soft, on the blurred alpha edge, <= 15 deg)
                float am = degrees(acos(clamp(dot(V, moonD), -1.0, 1.0)));
                float edge = smoothstep(0.02, 0.35, tx.a) * (1.0 - smoothstep(0.55, 0.95, tx.a));   // the soft alpha border, broad (no drawn line)
                float lining = _Lining.x * exp(-am / _Lining.y) * (1.0 - smoothstep(0.6 * _Lining.z, _Lining.z, am)) * edge;   // no step at the cut-off
                float3 c = (_MoonE * (moonC * (1.0 + lining))) * _MoonColor.rgb + (_SkyE * tx.b * _Scale.z) * _SkyColor.rgb;
                c *= UNITY_ACCESS_INSTANCED_PROP(Props, _Gain);

                // the gate's fog (no cap)
                float3 fogC = LanbaiGateFogColour(V, dist, moonD, (half)_FogDensity.z, 0.0);
                float fog = min(1.0 - exp(-_FogDensity.x * _FogDensity.y * dist), (_FogDensity.w > 0.0) ? _FogDensity.w : 1.0);
                c = lerp(c, fogC, fog);

                // base melting into the deck, + the soft depth fade where the billows cut the card
                float top = (_Udon_CloudTop.w > 0.0) ? _Udon_CloudTop.x : _CloudTopY;
                float a = tx.a * alphaK * smoothstep(top + _Melt.x, top + _Melt.x + _Melt.y, i.wpos.y);
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
