// =====================================================================================================
//  Lanbai / GateAirSky  v3 (gate round 8, 2026-10-02; cloud art team)   蓝白 · 触手之门 · 天空  Skybox, Built-in RP
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use.
//
//  v3 (tech r4 BT-3): the band, the moon aureole and the disc come from LanbaiGateSky.cginc, the SAME include
//  Lanbai_TentacleSway v2.7 uses for the arms' fog colour, so a fully fogged arm vanishes into this sky (acceptance:
//  screenshot the U7 framing with the arms' fog on / off: an arm at el 10-25 deg differs by <= 1 L*).
//      sky = LanbaiBand (6, 22, 2; fills x 0.80; below-horizon desaturation; BACK band) + aureole x disc weight + disc
//  Put this shader, Lanbai_TentacleSway.shader and LanbaiGateSky.cginc in the SAME folder. The v2 file
//  (deliver/Tentacles/Lanbai_GateAirSky.shader) is retired to deliver/Tentacles/_superseded~ (same shader name: keep
//  only this one in the project).
//  Udon globals (README_GateLayout §2.1): _Udon_TearPos, _Udon_TearH, _Udon_MoonDir, _Udon_MoonDisc (x = disc gain
//  from GateLayout_v2.json moon.disc_gain_keys x the eclipse fade, y = disc radius deg, w = 1).
// =====================================================================================================
Shader "Lanbai/GateAirSky"
{
    Properties
    {
        // every colour is a LINEAR value declared as Vector on purpose
        _HazeNear ("Haze Band Next To The Tear (fill x 0.80), linear", Vector) = (0.1085, 0.1130, 0.1641, 1)
        _HazeFar ("Haze Band 50 deg Away (fill x 0.80), linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _Void ("Void #070A14, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth: full to x deg, gone at y deg", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation: full to x deg, gone at y deg, power z", Vector) = (6, 22, 2, 0)
        _BelowHorizon ("Below the horizon: from x deg to y deg, darkest factor z", Vector) = (-25, 0, 0.55, 0)
        _BelowDesat ("Below-horizon desaturation", Range(0, 1)) = 0.6
        _BackBand ("Back band (|az| 110-150) x HazeFar", Range(0, 2)) = 0.55
        _TearPos ("Tear core fallback (world xyz; global _Udon_TearPos wins)", Vector) = (0, 297, 1800, 0)
        _RimDir ("Direction Toward The Moon (fallback; global _Udon_MoonDir wins)", Vector) = (-0.206, 0.139, 0.969, 0)
        _MoonGlowColor ("Moon aureole #8FA3C8, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole: a1, k1, a2, k2 (a1 e^-k1 deg + a2 e^-k2 deg)", Vector) = (1.6, 0.9, 0.06, 0.32)
        _AureoleGain ("Aureole gain in the sky (the arms' fog uses 0.35)", Range(0, 2)) = 1.0
        _MoonDisc ("Moon Disc #D6E4FF, linear rgb (HDR; x moon_disc_gain 0.6 at U7)", Vector) = (2.6, 2.8, 3.1, 1)
        _HaloColor ("Halo v6 #7A7B9C (unused by the sky; shared include)", Vector) = (0.195, 0.198, 0.332, 1)
        _Stars ("Stars (D-06: act 4 has stars; GateLayout_v2.json stars._Stars = 0.055, the brightest <= 12 L* above its sky)", Range(0, 3)) = 0.055
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
            #include "LanbaiGateSky.cginc"

            float4 _RimDir;
            float4 _MoonDisc;
            half _AureoleGain;
            float _Stars;

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

            float hash13(float3 p)
            {
                p = frac(p * 0.1031);
                p += dot(p, p.zyx + 31.32);
                return frac((p.x + p.y) * p.z);
            }

            half4 frag(v2f i) : SV_Target
            {
                float3 V = normalize(i.dir);
                float3 M = LanbaiMoonDir(_RimDir.xyz);
                half3 c = LanbaiGateSkyColour(V, M, _AureoleGain, (half3)_MoonDisc.rgb);
                // sparse stars (gain 0.12), one EV darker low in the band, none next to the moon (D-06 / D-21: _Stars 0.055)
                float el = degrees(asin(clamp(V.y, -1.0, 1.0)));
                float cm = saturate(dot(V, M));
                float3 cell = floor(V * 420.0);
                float s = hash13(cell);
                float star = step(0.9972, s) * pow(hash13(cell + 17.0), 3.0) * 6.0;
                float inband = lerp(0.5, 1.0, smoothstep(10.0, 35.0, el));          // v3.1 (D-06): one EV darker low in the band
                c += (half3)(star * _Stars * 0.12 * inband * (1.0 - saturate(pow(cm, 30.0) * 3.0)) * float3(0.8, 0.86, 1.0));
                return half4(c, 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
