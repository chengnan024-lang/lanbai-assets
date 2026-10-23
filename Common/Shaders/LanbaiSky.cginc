// =====================================================================================================
//  Lanbai / LanbaiSky.cginc   v1.1 (2026-10-23; v1 2026-10-22, cloud sub-session "天空")      蓝白 · 天的共用函数
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
//   none set              -> unity_FogColor (RenderSettings.fogColor): the built-in fog's colour.
//   only _Udon_FogBand* or _Udon_TearPos set (act 4) -> model A with the GATE defaults = Gate/Shaders/LanbaiGateSky.cginc
//                            LanbaiBand() (GateLayout_v2.json 'sky_band', round 8). Same arithmetic, same numbers.
//   _Udon_FogModel.x      -> the mix of model A (0) and model B (1), continuous (cross-fade the fog in 2-6 s, bible §1.6);
//                            unset: _Udon_HorizonColor.a = 2 picks B (v1 behaviour).
//   _Udon_HorizonColor.a  -> 1: model A "band" (a coloured band toward _Udon_FogBandDir over a void/zenith colour;
//                               acts 3, 4, 4c, night): near -> far over azimuth, gone above an elevation, back band,
//                               below-horizon darkening + desaturation.
//                            2: model B "gradient" (dawn / dusk / blue hour / water): horizon colour lerps from
//                               near (toward _Udon_FogBandDir) to far (away), blends up to the zenith colour and
//                               down to the nadir colour. No azimuth cut-off.
//   _Udon_FogCubeParams.x > 0  -> blend toward a pre-tinted, pre-blurred sky cube (_Udon_FogCube, baked by
//                               蓝白/Sky/Bake Fog Cube from the act's HDRI and its _ZenithTint/_HorizonTint) with
//                               weight x. For the HDRI acts this makes the fog EXACTLY the sky behind the object.
//   _Udon_Underwater > 0  -> the sea's under-water colours (up / level / down) take over with that weight.
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

// ---- globals. Never set = 0 and the defaults win. EVERY name has its own guard LANBAI_DECL_<name>: a shader that
// declares one of them itself defines that macro before including this file (and declares it BEFORE the include).
// Names also declared by Gate/Shaders/LanbaiGateSky.cginc are skipped when it was included first. Udon writes them
// with VRCShader.SetGlobalVector / SetGlobalFloat (linear values as they are; never SetGlobalColor).
// Fading: move only rgb / x toward the target; leave the a / w 'set' flags at 1 for the whole window.
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_FogBandDir)
#define LANBAI_DECL__Udon_FogBandDir
float4 _Udon_FogBandDir;    // xyz: world direction of the band / near lobe centre (tear, moon, sun); |xyz| < 0.5 = unset
#endif
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_FogBandColor)
#define LANBAI_DECL__Udon_FogBandColor
float4 _Udon_FogBandColor;    // rgb: horizon colour toward the band (linear); a > 0 = set
#endif
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_FogBandWidth)
#define LANBAI_DECL__Udon_FogBandWidth
float _Udon_FogBandWidth;    // degrees: near -> far over 0..width of azimuth; > 0 = set
#endif
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_TearPos)
#define LANBAI_DECL__Udon_TearPos
float4 _Udon_TearPos;    // (gate) xyz = the tear core, w > 0 = set: act 4 is recognised by it
#endif
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_MoonDir)
#define LANBAI_DECL__Udon_MoonDir
float4 _Udon_MoonDir;    // xyz = world direction TO the moon, w > 0 = set
#endif
#if !defined(LANBAI_GATE_SKY_INCLUDED) && !defined(LANBAI_DECL__Udon_MoonDisc)
#define LANBAI_DECL__Udon_MoonDisc
float4 _Udon_MoonDisc;    // x = disc gain, y = disc radius deg; w > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_HorizonColor
#define LANBAI_DECL__Udon_HorizonColor
float4 _Udon_HorizonColor;    // rgb: horizon colour AWAY from the band (linear); a > 0 = set (a = 1 / 2: legacy model pick, see _Udon_FogModel)
#endif
#ifndef LANBAI_DECL__Udon_ZenithColor
#define LANBAI_DECL__Udon_ZenithColor
float4 _Udon_ZenithColor;    // rgb: void / zenith colour (linear); a > 0 = set. Act 9: the current star floor (the mirrors read it)
#endif
#ifndef LANBAI_DECL__Udon_NadirColor
#define LANBAI_DECL__Udon_NadirColor
float4 _Udon_NadirColor;    // rgb: nadir colour for model B (linear); a > 0 = set (model A darkens instead)
#endif
#ifndef LANBAI_DECL__Udon_FogShape
#define LANBAI_DECL__Udon_FogShape
float4 _Udon_FogShape;    // x = el where the band / horizon is full (deg), y = where it is gone (deg, > 0 = set), z = power, w = back band gain (A)
#endif
#ifndef LANBAI_DECL__Udon_FogBelow
#define LANBAI_DECL__Udon_FogBelow
float4 _Udon_FogBelow;    // x = from deg (< 0 = set), y = to deg, z = A: darkest factor / B: nadir ramp power, w = desaturation (A)
#endif
#ifndef LANBAI_DECL__Udon_FogModel
#define LANBAI_DECL__Udon_FogModel
float4 _Udon_FogModel;    // x = model mix 0 = A band .. 1 = B gradient (continuous: cross-fade models in 2-6 s); w > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_FogCubeParams
#define LANBAI_DECL__Udon_FogCubeParams
float4 _Udon_FogCubeParams;    // x = fog cube weight 0..1 (> 0 = used), y = mip, z = max elevation deg of the lookup, w = exposure (0 = 1)
#endif
#ifndef LANBAI_DECL__Udon_SunDir
#define LANBAI_DECL__Udon_SunDir
float4 _Udon_SunDir;    // xyz = world direction TO the sun, w > 0 = set (the sea's ABOVE mode reads it too)
#endif
#ifndef LANBAI_DECL__Udon_SunDisc
#define LANBAI_DECL__Udon_SunDisc
float4 _Udon_SunDisc;    // x = disc gain, y = disc radius deg, z = sun line half length deg (act 8); w > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_Underwater
#define LANBAI_DECL__Udon_Underwater
float _Udon_Underwater;    // 0..1 the eye is under water (the sea driver)
#endif
#ifndef LANBAI_DECL__Udon_WaterFogUp
#define LANBAI_DECL__Udon_WaterFogUp
float4 _Udon_WaterFogUp;    // rgb: under-water fog colour looking up (linear)
#endif
#ifndef LANBAI_DECL__Udon_WaterFogMid
#define LANBAI_DECL__Udon_WaterFogMid
float4 _Udon_WaterFogMid;    // rgb: ... looking level
#endif
#ifndef LANBAI_DECL__Udon_WaterFogDown
#define LANBAI_DECL__Udon_WaterFogDown
float4 _Udon_WaterFogDown;    // rgb: ... looking down
#endif
#ifndef LANBAI_DECL__Udon_FogCube
#define LANBAI_DECL__Udon_FogCube
samplerCUBE _Udon_FogCube;    // pre-tinted, pre-blurred sky (linear HDR: RGBAHalf / BC6H)
#endif

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
    // + (1e-5, 0): looking straight up (V.xz = 0) the azimuth is defined (and equals the gate's LanbaiBand)
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
    return tear - LanbaiCentreEyePos();                 // both eyes the same band
}

// model A: the gate's haze band, generalised (the arithmetic of LanbaiGateSky.cginc LanbaiBand(), line for line)
float3 LanbaiHorizonBand(float3 V, float3 nearC, float3 farC, float3 voidC, float bw, float bg,
                         float4 shape, float4 below)
{
    float el = LanbaiElevationDeg(V);
    float az = LanbaiAzimuthDeg(V, LanbaiBandDir());
    float3 band = lerp(nearC, farC, smoothstep(0.0, bw, az));
    float wel = 1.0 - smoothstep(shape.x, max(shape.y, shape.x + 0.1), el);
    wel = pow(saturate(wel), (shape.z > 0.0) ? shape.z : 1.0);
    float w = (1.0 - smoothstep(bw, max(bg, bw + 0.1), az)) * wel;
    float3 sky = lerp(voidC, band, w);
    sky += farC * (shape.w * smoothstep(65.0, 120.0, az) * wel);
    float lum = dot(sky, float3(0.2126, 0.7152, 0.0722));
    sky = lerp(sky, lum * float3(0.92, 0.98, 1.12), below.w * smoothstep(0.0, -4.0, el));
    float dark = lerp(below.z, 1.0, smoothstep(below.x, max(below.y, below.x + 0.1), el));
    return sky * dark;
}

// model B: a smooth sky gradient (no azimuth cut-off): near (toward the band dir) -> far over 0..bw deg of azimuth,
// horizon -> zenith above, horizon -> nadir below
// a transition toward the zenith with no point at the top (director r2 #2: "no hard shapes in the sky"): the upper end
// is clamped to 90. A step still moving at the zenith (the dawn fit had its end at 94.5) makes a cone = a bullseye; one
// ending AT 90 is a smooth paraboloid there. Presets whose gradient reaches the zenith end it at 90, not below (a step
// ending at 85 leaves a flat disc with a curvature edge round it).
// geometric (log-space) blend: a linear-light lerp between a bright horizon and a dark zenith stays bright on screen to
// ~60 deg and then plunges = a dark disc overhead; the log blend darkens evenly in display terms (director r2 #2)
inline float3 LanbaiGeoLerp(float3 a, float3 b, float t)
{
    return exp2(lerp(log2(max(a, 1e-6)), log2(max(b, 1e-6)), t));
}

inline float LanbaiUpStep(float lo, float hi, float el)
{
    float x = saturate((el - lo) / max(min(hi, 90.0) - lo, 1e-4));
    return x * x * (3.0 - 2.0 * x);
}

float3 LanbaiHorizonGradient(float3 V, float3 nearC, float3 farC, float3 zenC, float3 nadC, float bw,
                             float4 shape, float4 below)
{
    float el = LanbaiElevationDeg(V);
    float az = LanbaiAzimuthDeg(V, LanbaiBandDir());
    float3 hz = lerp(nearC, farC, smoothstep(0.0, max(bw, 1.0), az));
    float up = LanbaiUpStep(shape.x, max(shape.y, shape.x + 0.1), el);
    up = pow(saturate(up), (shape.z > 0.0) ? shape.z : 1.0);
    float dn = smoothstep(below.y, min(below.x, below.y - 0.1), el);           // 0 at below.y .. 1 at below.x (both <= 0)
    dn = pow(saturate(dn), (below.z > 0.0) ? below.z : 1.0);
    float3 c = LanbaiGeoLerp(hz, zenC, up);
    return lerp(c, nadC, dn);
}

// THE horizon function (= fog colour in that direction; Lanbai/Sky's horizon in the procedural modes)
float3 LanbaiHorizon(float3 dirWS)
{
    float3 V = normalize(dirWS);
    float3 c;
    // act 4 is recognised by the band colour OR by the gate driver's tear position (it always writes _Udon_TearPos)
    bool anySet = (_Udon_HorizonColor.a > 0.0) || (_Udon_FogBandColor.a > 0.0) || (_Udon_TearPos.w > 0.0);
    [branch] if (!anySet)
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
        float mixB = (_Udon_FogModel.w > 0.0) ? saturate(_Udon_FogModel.x) : ((_Udon_HorizonColor.a > 1.5) ? 1.0 : 0.0);
        float3 a = 0, b = 0;
        [branch] if (mixB < 0.999)
            a = LanbaiHorizonBand(V, nearC, farC, zenC, bw, bg, shape, below);
        [branch] if (mixB > 0.001)
        {
            float3 nadC = (_Udon_NadirColor.a > 0.0) ? _Udon_NadirColor.rgb : farC;
            b = LanbaiHorizonGradient(V, nearC, farC, zenC, nadC, bw, shape, below);
        }
        c = lerp(a, b, mixB);
    }
    [branch] if (_Udon_FogCubeParams.x > 0.0)
    {
        float3 L = V;
        float maxEl = sin(radians((_Udon_FogCubeParams.z > 0.0) ? _Udon_FogCubeParams.z : 90.0));
        L.y = min(L.y, maxEl);
        L = normalize(L);
        float3 cube = texCUBElod(_Udon_FogCube, float4(L, _Udon_FogCubeParams.y)).rgb;
        cube *= (_Udon_FogCubeParams.w > 0.0) ? _Udon_FogCubeParams.w : 1.0;
        c = lerp(c, cube, saturate(_Udon_FogCubeParams.x));
    }
    // the sea's under-water group (Sea/README_Sea接口.md): bright up, dark down, uniform density
    [branch] if (_Udon_Underwater > 0.0)
    {
        float y = V.y;
        float3 w = (y >= 0.0) ? lerp(_Udon_WaterFogMid.rgb, _Udon_WaterFogUp.rgb, smoothstep(0.0, 1.0, y))
                              : lerp(_Udon_WaterFogMid.rgb, _Udon_WaterFogDown.rgb, smoothstep(0.0, 1.0, -y));
        c = lerp(c, w, saturate(_Udon_Underwater));
    }
    return c;
}

// ---- act 9: the galaxy glow (Sky/Textures/StarSky_Glow_8192x4096.png x _GlowScale, a 2D lat-long in the WORLD frame, no mips):
// u = 0.5 + atan2(V.x, V.z) / 2pi, v = 0.5 + asin(V.y) / pi. Shared by Lanbai/Sky and the mirrors' reflection.
inline float2 LanbaiGalaxyUV(float3 V)
{
    float zz = (abs(V.x) + abs(V.z) < 1e-6) ? 1.0 : V.z;          // straight up / down: atan2(0, 0) is undefined on some GPUs
    return float2(0.5 + atan2(V.x, zz) * (0.5 / UNITY_PI), 0.5 + asin(clamp(V.y, -1.0, 1.0)) * (1.0 / UNITY_PI));
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
