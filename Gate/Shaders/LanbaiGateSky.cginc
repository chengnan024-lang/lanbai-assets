// LanbaiGateSky.cginc  v1 (gate round 8, 2026-10-02; cloud art team)  -- UNCOMPILED: compile in Unity 2022.3 and check.
// 蓝白 · 触手之门 · the ONE definition of the gate's sky and air, shared by
//     Lanbai_TentacleSway.shader (v2.7; the arms' fog colour)  and  Lanbai_GateAirSky.shader (v3; the skybox).
// (tech r4 BT-3: the delivered skybox still drew the v2 band while the arms fogged toward the v2.6 band, so every far
//  crown would have been a dark cut-out and the void above +20 deg would have come back as lit grey.)
//
//   sky  = LanbaiBand(V) + 1.0  x moon aureole x disc weight + moon disc        (LanbaiGateSkyColour, the skybox)
//   fog  = LanbaiBand(V) + 0.35 x moon aureole + the wound's air x halo fade     (LanbaiGateFogColour, the arms)
//
// Defaults = GateLayout_v2.json 'sky_band' (round 8): band elevation (6, 22, 2), fills x 0.80, below-horizon
// desaturation 0.6, BACK band (|az| 65..120 ramp: HazeFar x 0.80 x 0.55, so the side / rear windows hold a horizon).
// Put this file next to both shaders (same folder). Every colour is a LINEAR Vector (no sRGB conversion).
#ifndef LANBAI_GATE_SKY_INCLUDED
#define LANBAI_GATE_SKY_INCLUDED

// ---- material / global inputs (declared once here; both shaders expose them as Properties) -------------------------
float4 _HazeNear;            // band next to the tear (fill x 0.80)  default (0.1085, 0.1130, 0.1641)
float4 _HazeFar;             // band 50 deg away (fill x 0.80)        default (0.0436, 0.0504, 0.0726)
float4 _Void;                // #070A14                               default (0.0021, 0.0030, 0.0070)
float4 _BandAz;              // full to x deg, gone at y deg          default (50, 60)
float4 _BandEl;              // full to x deg, gone at y deg, power z default (6, 22, 2)
float4 _BelowHorizon;        // from x deg to y deg, darkest factor z default (-25, 0, 0.55)
half   _BelowDesat;          // default 0.6
half   _BackBand;            // default 0.55 (x HazeFar, |az| 110..150 deg)
float4 _MoonGlowColor;       // #8FA3C8 linear                        default (0.275, 0.366, 0.578)
float4 _MoonGlowShape;       // a1, k1, a2, k2                        default (1.6, 0.9, 0.06, 0.32)
float4 _HaloColor;           // v6 #7A7B9C fill, linear               default (0.195, 0.199, 0.335)
float4 _TearPos;             // fallback tear core (world)

// Udon globals (VRCShader.SetGlobal*), declared once in the shared registry (no X3003 when two includes meet).
// Never set = 0 and the material values win.
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

float3 LanbaiTearPos()
{
    return (_Udon_TearPos.w > 0.0) ? _Udon_TearPos.xyz : _TearPos.xyz;
}

float3 LanbaiMoonDir(float3 fallback)
{
    return (_Udon_MoonDir.w > 0.0) ? normalize(_Udon_MoonDir.xyz) : normalize(fallback);
}

// LanbaiBand: the haze-band sky in world direction V (camera -> point); azimuth from the horizontal direction
// camera -> tear (or _Udon_FogBandDir). Mirrors gate_scene.horizon_nodes() exactly (round 8: incl. the back band).
half3 LanbaiBand(float3 V)
{
    float el = degrees(asin(clamp(V.y, -1.0, 1.0)));
    float3 T = (dot(_Udon_FogBandDir.xyz, _Udon_FogBandDir.xyz) > 0.25) ? _Udon_FogBandDir.xyz
                                                                       : (LanbaiTearPos() - _WorldSpaceCameraPos);
    float2 th = normalize(T.xz + float2(1e-5, 0.0));
    float2 vh = normalize(V.xz + float2(1e-5, 0.0));
    float az = degrees(acos(clamp(dot(th, vh), -1.0, 1.0)));
    float bw = (_Udon_FogBandWidth > 0.0) ? _Udon_FogBandWidth : _BandAz.x;
    float bg = (_Udon_FogBandWidth > 0.0) ? _Udon_FogBandWidth + (_BandAz.y - _BandAz.x) : _BandAz.y;
    half3 nearC = (_Udon_FogBandColor.a > 0.0) ? (half3)_Udon_FogBandColor.rgb : (half3)_HazeNear.rgb;
    half3 band = lerp(nearC, (half3)_HazeFar.rgb, smoothstep(0.0, bw, az));
    float wel = 1.0 - smoothstep(_BandEl.x, _BandEl.y, el);
    wel = pow(saturate(wel), (_BandEl.z > 0.0) ? _BandEl.z : 1.0);
    float w = (1.0 - smoothstep(bw, bg, az)) * wel;
    half3 sky = lerp((half3)_Void.rgb, band, w);
    sky += (half3)_HazeFar.rgb * (_BackBand * smoothstep(65.0, 120.0, az) * wel);        // round 8: the back band (side + rear windows)
    half lum = dot(sky, half3(0.2126, 0.7152, 0.0722));
    sky = lerp(sky, lum * half3(0.92, 0.98, 1.12), _BelowDesat * smoothstep(0.0, -4.0, el));
    float below = lerp(_BelowHorizon.z, 1.0, smoothstep(_BelowHorizon.x, _BelowHorizon.y, el));
    return sky * below;
}

// the moon's air: #8FA3C8 x (a1 e^-k1 deg + a2 e^-k2 deg), deg = angle from the moon
half3 LanbaiMoonAir(float3 V, float3 moonD)
{
    float am = degrees(acos(clamp(dot(V, moonD), -1.0, 1.0)));
    return (half3)_MoonGlowColor.rgb * (half)(_MoonGlowShape.x * exp(-_MoonGlowShape.y * am) + _MoonGlowShape.z * exp(-_MoonGlowShape.w * am));
}

// the halo cards' radial profile (Halo_512: soft core + long tail, 0 at q = 1)
half HaloProfile(float q)
{
    float f = 0.62 / pow(1.0 + (q / 0.16) * (q / 0.16), 1.15) + 0.38 * exp(-(q / 0.55) * (q / 0.55));
    return (half)(saturate((f - 0.0296) / 0.9704) * smoothstep(1.0, 0.72, q));
}

// round 8 (tech r4 M4 + the overdraw budget): the halo cards fade as the bus closes in, D = eye -> tear plane:
// k = saturate((smoothstep(250, 1200, D) - 0.25) / 0.75) (1 beyond 1.2 km, 0.47 at U8, 0 from D ~ 575 m, ~U8 + 3.5);
// Udon writes the same k into Tear_Halo's _Intensity and turns its renderer off below 0.05
half LanbaiHaloFade()
{
    float D = abs(LanbaiTearPos().z - _WorldSpaceCameraPos.z);
    return (half)saturate((smoothstep(250.0, 1200.0, D) - 0.25) / 0.75);
}

// the wound's air: the three v6 halo cards (kit units at H = 1000 m, centred on the HOT SPOT 49 m right of the tear
// path, the wider two shifted LEFT: lip-weighted), seen along V where they lie BEHIND the shaded point.
// (w, h, gain, across offset of the card centre from the hot spot):  (440, 760, 1.3, 0)  (360, 860, 0.9, -55)
// (620, 980, 0.9, -90).  TearPos = the hot spot height; x offset of the hot spot +49 m x k.
half3 LanbaiWoundAir(float3 V, float dist)
{
    float3 T = LanbaiTearPos();
    float tpl = (T.z - _WorldSpaceCameraPos.z) / max(V.z, 1e-4);
    half acc = 0.0;
    if (V.z > 1e-3 && dist < tpl)
    {
        float k = ((_Udon_TearH.w > 0.0) ? _Udon_TearH.x : 640.0) / 1000.0;
        float2 r = (_WorldSpaceCameraPos.xy + V.xy * tpl) - (T.xy + float2(49.0 * k, 0.0));
        acc = 1.3 * HaloProfile(length(r / (0.5 * k * float2(440.0, 760.0))))
            + 0.9 * HaloProfile(length((r - float2(-55.0 * k, 0.0)) / (0.5 * k * float2(360.0, 860.0))))
            + 0.9 * HaloProfile(length((r - float2(-90.0 * k, 0.0)) / (0.5 * k * float2(620.0, 980.0))));
    }
    return (half3)_HaloColor.rgb * (acc * LanbaiHaloFade());
}

// the arms' fog colour. glowAir = _HaloFog x (1 - _OverWhiteAir x overWhite) (TentacleSway), moonAir = _MoonGlowFog.
half3 LanbaiGateFogColour(float3 V, float dist, float3 moonD, half moonAir, half glowAir)
{
#if defined(LANBAI_FOG_INCLUDED)
    half3 c = LanbaiHorizon(V);
#else
    half3 c = LanbaiBand(V);
#endif
    c += LanbaiMoonAir(V, moonD) * moonAir;
    if (glowAir > 0.0)
        c += LanbaiWoundAir(V, dist) * glowAir;
    return c;
}

// the skybox: band + the full aureole (x the disc weight) + the disc (soft 0.05 deg edge)
half3 LanbaiGateSkyColour(float3 V, float3 moonD, half aureoleGain, half3 discColor)
{
    half3 c = LanbaiBand(V);
    half discGain = (_Udon_MoonDisc.w > 0.0) ? (half)_Udon_MoonDisc.x : 1.0;
    float discR = (_Udon_MoonDisc.w > 0.0) ? _Udon_MoonDisc.y : 0.6;
    float am = degrees(acos(clamp(dot(V, moonD), -1.0, 1.0)));
    // the core term x (0.35 + 0.65 disc weight): once the disc has faded only the halo stays (renders: world())
    half core = (half)(_MoonGlowShape.x * exp(-_MoonGlowShape.y * am)) * lerp(0.35, 1.0, discGain);
    half tail = (half)(_MoonGlowShape.z * exp(-_MoonGlowShape.w * am));
    c += (half3)_MoonGlowColor.rgb * ((core + tail) * aureoleGain);
    c += discColor * (discGain * smoothstep(discR + 0.03, discR - 0.03, am));
    return c;
}

#endif // LANBAI_GATE_SKY_INCLUDED
