// =====================================================================================================
//  Lanbai / LanbaiSky.cginc   v1 (2026-10-22, cloud sub-session "天空")      蓝白 · 天的共用函数
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Sky/Tools~/compile_check). !!!
//
//  The ONE definition of the sky's horizon (ART BIBLE v2.1 §1.6: fog colour = the sky's horizon colour in that
//  direction) plus the small helpers Lanbai/Sky and every sky object share: sun / moon direction, the sun disc,
//  the "other sky" mapping (act 8-ii), own distance attenuation for sky objects (_FogMode 2).
//  LanbaiFog.cginc includes this file; most shaders include LanbaiFog.cginc only.
//
//  Every colour here is LINEAR. dirWS / V is a unit vector from the camera toward the pixel.
//
//  ---- LanbaiHorizon(V): three models, picked by which globals are set (Udon, VRCShader.SetGlobal*) ----------
//   none set              -> unity_FogColor (RenderSettings.fogColor): identical to Unity's built-in fog.
//   only _Udon_FogBand*   -> model A with the GATE defaults = Gate/Shaders/LanbaiGateSky.cginc LanbaiBand()
//     set (act 4)            (GateLayout_v2.json 'sky_band', round 8). Same arithmetic, same numbers.
//   _Udon_HorizonColor.a  -> 1: model A "band" (a coloured band toward _Udon_FogBandDir over a void/zenith colour;
//                               acts 3, 4, 4c, night): near -> far over azimuth, gone above an elevation, back band,
//                               below-horizon darkening + desaturation.
//                            2: model B "gradient" (dawn / dusk / blue hour / water): horizon colour lerps from
//                               near (toward _Udon_FogBandDir) to far (away), blends up to the zenith colour and
//                               down to the nadir colour. No azimuth cut-off.
//   _Udon_FogCubeParams.x > 0  -> blend toward a pre-tinted, pre-blurred sky cube (_Udon_FogCube, baked by
//                               蓝白/Sky/Bake Fog Cube from the act's HDRI and its _ZenithTint/_HorizonTint) with
//                               weight x. For the HDRI acts this makes the fog EXACTLY the sky behind the object.
//
//  ---- include order with the gate --------------------------------------------------------------------------
//   Gate/Shaders/LanbaiGateSky.cginc declares _Udon_FogBandDir/_Udon_FogBandColor/_Udon_FogBandWidth,
//   _Udon_TearPos, _Udon_TearH, _Udon_MoonDir, _Udon_MoonDisc with no guard. If a shader needs both files,
//   include LanbaiGateSky.cginc FIRST, then this file (this file then skips those declarations).
//   The other order is a "redefinition" compile error.
//
//  Function names used by LanbaiGateSky.cginc (LanbaiBand, LanbaiMoonDir, LanbaiTearPos, LanbaiMoonAir,
//  HaloProfile, ...) are NOT used here, so both files can live in one shader.
// =====================================================================================================
#ifndef LANBAI_SKY_INCLUDED
#define LANBAI_SKY_INCLUDED

#include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

// ---- globals (declared once; never set = 0 and the defaults win) ---------------------------------------------
#ifndef LANBAI_GATE_SKY_INCLUDED
float4 _Udon_FogBandDir;      // xyz: world direction of the band / near lobe centre (tear, moon, sun); |xyz| < 0.5 = unset
float4 _Udon_FogBandColor;    // rgb: horizon colour toward the band (linear); a > 0 = set
float  _Udon_FogBandWidth;    // degrees: near -> far over 0..width of azimuth; > 0 = set
float4 _Udon_TearPos;         // (gate) xyz = the tear core, w > 0 = set: default band direction in act 4
float4 _Udon_MoonDir;         // xyz = world direction TO the moon, w > 0 = set
float4 _Udon_MoonDisc;        // x = disc gain, y = disc radius deg; w > 0 = set
#endif
float4 _Udon_HorizonColor;    // rgb: horizon colour AWAY from the band (linear); a = model: 1 band, 2 gradient; 0 = unset
float4 _Udon_ZenithColor;     // rgb: void / zenith colour (linear); a > 0 = set
float4 _Udon_NadirColor;      // rgb: nadir colour for model B (linear); a > 0 = set (model A darkens instead)
float4 _Udon_FogShape;        // x = elevation where the band / horizon is full (deg), y = where it is gone (deg, > 0 = set),
                              // z = power of that ramp, w = back band gain (model A only; x far colour, |az| 65..120)
float4 _Udon_FogBelow;        // x = from deg (< 0 = set), y = to deg, z = model A: darkest factor / model B: nadir ramp power,
                              // w = below-horizon desaturation (model A)
float4 _Udon_FogCubeParams;   // x = weight of the fog cube 0..1 (> 0 = used), y = mip, z = max elevation deg for the lookup,
                              // w = exposure multiplier (0 = 1)
samplerCUBE _Udon_FogCube;    // pre-tinted, pre-blurred sky (linear HDR; RGBM/dLDR decoded by the importer: use RGBAHalf / BC6H)
float4 _Udon_SunDir;          // xyz = world direction TO the sun, w > 0 = set
float4 _Udon_SunDisc;         // x = disc gain, y = disc radius deg, z = soft edge deg; w > 0 = set

// ---- gate defaults (GateLayout_v2.json 'sky_band', round 8; = Lanbai_GateAirSky v3 material defaults) ---------
#define LANBAI_GATE_NEAR    float3(0.1085, 0.1130, 0.1641)
#define LANBAI_GATE_FAR     float3(0.0436, 0.0504, 0.0726)
#define LANBAI_GATE_VOID    float3(0.0021, 0.0030, 0.0070)
#define LANBAI_GATE_TEARPOS float3(0.0, 297.0, 1800.0)

// ---------------------------------------------------------------------------------------------------------------
inline float LanbaiElevationDeg(float3 V)
{
    return degrees(asin(clamp(V.y, -1.0, 1.0)));
}

// horizontal azimuth (deg, 0..180) between V and T, exactly as LanbaiBand computes it
inline float LanbaiAzimuthDeg(float3 V, float3 T)
{
    float2 th = normalize(T.xz + float2(1e-5, 0.0));
    float2 vh = normalize(V.xz + float2(1e-5, 0.0));
    return degrees(acos(clamp(dot(th, vh), -1.0, 1.0)));
}

// the band / near-lobe direction: the global, else the tear (act 4), else +Z (straight ahead of the bus)
inline float3 LanbaiBandDir()
{
    if (dot(_Udon_FogBandDir.xyz, _Udon_FogBandDir.xyz) > 0.25)
        return _Udon_FogBandDir.xyz;
    float3 tear = (_Udon_TearPos.w > 0.0) ? _Udon_TearPos.xyz : LANBAI_GATE_TEARPOS;
    return tear - _WorldSpaceCameraPos;
}

// model A: the gate's haze band, generalised (the arithmetic of LanbaiGateSky.cginc LanbaiBand(), line for line)
float3 LanbaiHorizonBand(float3 V, float3 nearC, float3 farC, float3 voidC, float bw, float bg,
                         float4 shape, float4 below)
{
    float el = LanbaiElevationDeg(V);
    float az = LanbaiAzimuthDeg(V, LanbaiBandDir());
    float3 band = lerp(nearC, farC, smoothstep(0.0, bw, az));
    float wel = 1.0 - smoothstep(shape.x, shape.y, el);
    wel = pow(saturate(wel), (shape.z > 0.0) ? shape.z : 1.0);
    float w = (1.0 - smoothstep(bw, bg, az)) * wel;
    float3 sky = lerp(voidC, band, w);
    sky += farC * (shape.w * smoothstep(65.0, 120.0, az) * wel);
    float lum = dot(sky, float3(0.2126, 0.7152, 0.0722));
    sky = lerp(sky, lum * float3(0.92, 0.98, 1.12), below.w * smoothstep(0.0, -4.0, el));
    float dark = lerp(below.z, 1.0, smoothstep(below.x, below.y, el));
    return sky * dark;
}

// model B: a smooth sky gradient (no azimuth cut-off): near (toward the band dir) -> far over 0..bw deg of azimuth,
// horizon -> zenith above, horizon -> nadir below
float3 LanbaiHorizonGradient(float3 V, float3 nearC, float3 farC, float3 zenC, float3 nadC, float bw,
                             float4 shape, float4 below)
{
    float el = LanbaiElevationDeg(V);
    float az = LanbaiAzimuthDeg(V, LanbaiBandDir());
    float3 hz = lerp(nearC, farC, smoothstep(0.0, max(bw, 1.0), az));
    float up = smoothstep(shape.x, max(shape.y, shape.x + 0.1), el);
    up = pow(saturate(up), (shape.z > 0.0) ? shape.z : 1.0);
    float dn = smoothstep(below.y, min(below.x, below.y - 0.1), el);           // 0 at below.y .. 1 at below.x (both <= 0)
    dn = pow(saturate(dn), (below.z > 0.0) ? below.z : 1.0);
    float3 c = lerp(hz, zenC, up);
    return lerp(c, nadC, dn);
}

// THE horizon function (= fog colour in that direction; Lanbai/Sky's horizon in the procedural modes)
float3 LanbaiHorizon(float3 dirWS)
{
    float3 V = normalize(dirWS);
    float3 c;
    bool anySet = (_Udon_HorizonColor.a > 0.0) || (_Udon_FogBandColor.a > 0.0);
    if (!anySet)
    {
        c = unity_FogColor.rgb;
    }
    else
    {
        float3 nearC = (_Udon_FogBandColor.a > 0.0) ? _Udon_FogBandColor.rgb : LANBAI_GATE_NEAR;
        float3 farC  = (_Udon_HorizonColor.a > 0.0) ? _Udon_HorizonColor.rgb : LANBAI_GATE_FAR;
        float3 zenC  = (_Udon_ZenithColor.a > 0.0) ? _Udon_ZenithColor.rgb : LANBAI_GATE_VOID;
        float bw = (_Udon_FogBandWidth > 0.0) ? _Udon_FogBandWidth : 50.0;
        float bg = bw + 10.0;                                                    // gate: _BandAz (50, 60)
        float4 shape = (_Udon_FogShape.y > 0.0) ? _Udon_FogShape : float4(6.0, 22.0, 2.0, 0.55);
        float4 below = (_Udon_FogBelow.x < 0.0) ? _Udon_FogBelow : float4(-25.0, 0.0, 0.55, 0.6);
        if (_Udon_HorizonColor.a > 1.5)
        {
            float3 nadC = (_Udon_NadirColor.a > 0.0) ? _Udon_NadirColor.rgb : farC;
            c = LanbaiHorizonGradient(V, nearC, farC, zenC, nadC, bw, shape, below);
        }
        else
        {
            c = LanbaiHorizonBand(V, nearC, farC, zenC, bw, bg, shape, below);
        }
    }
    if (_Udon_FogCubeParams.x > 0.0)
    {
        float3 L = V;
        float maxEl = sin(radians((_Udon_FogCubeParams.z > 0.0) ? _Udon_FogCubeParams.z : 90.0));
        L.y = min(L.y, maxEl);
        L = normalize(L);
        float3 cube = texCUBElod(_Udon_FogCube, float4(L, _Udon_FogCubeParams.y)).rgb;
        cube *= (_Udon_FogCubeParams.w > 0.0) ? _Udon_FogCubeParams.w : 1.0;
        c = lerp(c, cube, saturate(_Udon_FogCubeParams.x));
    }
    return c;
}

// ---- sun, moon -------------------------------------------------------------------------------------------------
inline float3 LanbaiSunDir(float3 fallback)
{
    return (_Udon_SunDir.w > 0.0) ? normalize(_Udon_SunDir.xyz) : normalize(fallback);
}

inline float3 LanbaiSkyMoonDir(float3 fallback)
{
    return (_Udon_MoonDir.w > 0.0) ? normalize(_Udon_MoonDir.xyz) : normalize(fallback);
}

// angle (deg) between two unit vectors, precise near 0 (the 0.9 deg sun disc needs it: acos loses ~0.05 deg in float)
inline float LanbaiAngleDeg(float3 a, float3 b)
{
    return degrees(2.0 * atan2(length(a - b), length(a + b)));
}

// sun / moon disc: 1 inside radius, soft edge 'soft' deg wide, limb darkening u (0 = flat; sun ~0.6).
// Returns the disc's intensity factor (multiply by the disc colour). Squash: x = vertical scale (act 8 horizon
// line: the disc is squashed into a line by > 1 values; 1 = round).
float LanbaiDisc(float3 V, float3 D, float radiusDeg, float softDeg, float limbU)
{
    float a = LanbaiAngleDeg(V, D);
    float edge = smoothstep(radiusDeg + 0.5 * softDeg, radiusDeg - 0.5 * softDeg, a);
    float r = saturate(a / max(radiusDeg, 1e-3));
    float mu = sqrt(saturate(1.0 - r * r));
    float limb = 1.0 - limbU * (1.0 - mu);
    return edge * limb;
}

// ---- act 8-ii: the other sky. The lower hemisphere samples the sky rotated 180 deg about the forward (+Z) axis:
// (x, y, z) -> (-x, -y, z). Sun and gradient still meet at the seam; the clouds below are other clouds. -----------
inline float3 LanbaiOtherSkyDir(float3 V)
{
    return float3(-V.x, -V.y, V.z);
}
// weight of the other sky for direction V: 0 above, 1 below, a soft band of 'seamDeg' degrees centred on 0
inline float LanbaiOtherSkyWeight(float3 V, float seamDeg)
{
    float el = LanbaiElevationDeg(V);
    return smoothstep(0.5 * seamDeg, -0.5 * seamDeg, el);
}

// ---- sky objects do not take fog (_FogMode 2): own distance attenuation exp(-d x atten) -------------------------
inline float LanbaiSkyObjectAtten(float dist, float atten)
{
    return exp(-max(dist, 0.0) * max(atten, 0.0));
}

#endif // LANBAI_SKY_INCLUDED
