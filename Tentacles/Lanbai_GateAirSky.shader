// =====================================================================================================
//  Lanbai / GateAirSky  v2      蓝白 · 触手之门 · 天空（可选）  Skybox material shader, Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  OPTIONAL. The tentacles fade into LanbaiBand(view direction) (Lanbai_TentacleSway.shader, lanbaiFog).
//  Far arms only "dissolve into the sky" if the sky behind them has that same colour. This skybox
//  draws exactly the ART BIBLE v2 haze band (#484D63 next to the tear -> #2A3041 50 deg away, void
//  #070A14 above +35 deg or beyond 60 deg), the moon disc (1.2 deg) with its silver halo #5A6A88 and
//  sparse stars (gain 0.12 in the bible's NASA map; one EV darker inside the band) -- the sky of the
//  gate renders. If the project's Lanbai/Sky already has a haze-band mode, use that instead and copy
//  its numbers into the tentacle materials. Keep every band value and _TearPos / _RimDir identical on
//  the sky and on every M_Tentacle_* material.
// =====================================================================================================
Shader "Lanbai/GateAirSky"
{
    Properties
    {
        // every colour is a LINEAR value declared as Vector on purpose (a Color property would be treated as sRGB
        // and converted in a Linear-space project: the sky would no longer match the tentacles' fog)
        _HazeNear ("Haze Band Next To The Tear #484D63, linear", Vector) = (0.0648, 0.0742, 0.1248, 1)
        _HazeFar ("Haze Band 50 deg Away #2A3041, linear", Vector) = (0.0232, 0.0296, 0.0512, 1)
        _Void ("Void #070A14, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth: full to x deg, gone at y deg", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation: full to x deg, gone at y deg", Vector) = (15, 35, 0, 0)
        _BelowHorizon ("Below the horizon: from x deg to y deg, darkest factor z", Vector) = (-25, 0, 0.55, 0)
        _Exposure ("Fill multiplier (bible fill / screen, e.g. #67697D / #484D63 = 1.9)", Float) = 1
        _TearPos ("Tear Centre (world xyz, GateLayout.json)", Vector) = (0, 297, 1800, 0)
        _RimDir ("Direction Toward The Moon (world xyz, GateLayout.json)", Vector) = (-0.206, 0.139, 0.969, 0)
        _MoonDisc ("Moon Disc #D6E4FF, linear rgb (HDR)", Vector) = (2.6, 2.8, 3.1, 1)
        _MoonSize ("Moon Diameter (deg)", Range(0.3, 4)) = 1.2
        _MoonHalo ("Moon Halo #5A6A88, linear rgb", Vector) = (0.102, 0.144, 0.246, 1)
        _MoonHaloAmt ("Halo: wide (pow 300), tight (pow 3000)", Vector) = (0.25, 1.2, 0, 0)
        _Stars ("Stars", Range(0, 3)) = 1
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Cull Off ZWrite Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"

            float4 _HazeNear, _HazeFar, _Void, _BandAz, _BandEl, _BelowHorizon;
            float _Exposure;
            float4 _TearPos, _RimDir;
            float4 _MoonDisc, _MoonHalo, _MoonHaloAmt;
            float _MoonSize, _Stars;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dir = v.vertex.xyz;
                return o;
            }

            // identical to LanbaiBand() in Lanbai_TentacleSway.shader
            float3 LanbaiBand(float3 V, out float el)
            {
                el = degrees(asin(clamp(V.y, -1.0, 1.0)));
                float3 T = _TearPos.xyz - _WorldSpaceCameraPos;
                float2 th = normalize(T.xz + float2(1e-5, 0.0));
                float2 vh = normalize(V.xz + float2(1e-5, 0.0));
                float az = degrees(acos(clamp(dot(th, vh), -1.0, 1.0)));
                float3 band = lerp(_HazeNear.rgb, _HazeFar.rgb, smoothstep(0.0, _BandAz.x, az));
                float w = (1.0 - smoothstep(_BandAz.x, _BandAz.y, az)) * (1.0 - smoothstep(_BandEl.x, _BandEl.y, el));
                float3 sky = lerp(_Void.rgb, band, w);
                return sky * lerp(_BelowHorizon.z, 1.0, smoothstep(_BelowHorizon.x, _BelowHorizon.y, el));
            }

            float hash13(float3 p)
            {
                p = frac(p * 0.1031);
                p += dot(p, p.zyx + 31.32);
                return frac((p.x + p.y) * p.z);
            }

            half4 frag(v2f i) : SV_Target
            {
                float3 V = normalize(i.dir);
                float el;
                float3 c = LanbaiBand(V, el) * _Exposure;
                float3 M = normalize(_RimDir.xyz);
                float cm = saturate(dot(V, M));
                c += _MoonHalo.rgb * (pow(cm, 300.0) * _MoonHaloAmt.x + pow(cm, 3000.0) * _MoonHaloAmt.y);
                float r = radians(_MoonSize * 0.5);
                c += _MoonDisc.rgb * smoothstep(cos(r), cos(r * 0.86), dot(V, M));
                // sparse stars, one EV darker inside the haze band, none next to the moon
                float3 cell = floor(V * 420.0);
                float s = hash13(cell);
                float star = step(0.9972, s) * pow(hash13(cell + 17.0), 3.0) * 6.0;
                float inband = lerp(0.15, 1.0, smoothstep(10.0, 35.0, el));
                c += star * _Stars * 0.12 * inband * (1.0 - saturate(pow(cm, 30.0) * 3.0)) * float3(0.8, 0.86, 1.0);
                return half4(c, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
