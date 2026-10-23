// =====================================================================================================
//  Lanbai / LanbaiSkyLayers.cginc   v1 (2026-10-23, cloud sub-session "天空")    the body of Lanbai/Sky
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only. !!!
//  Kept in its own file so the cloud reference renderer runs THIS code on the CPU (Sky/Tools~/compile_check/
//  slang_cpu.py) and the reflection-cube baker can call LanbaiSkyColour() too. Include after LanbaiSky.cginc.
//  Every colour linear. Unity left-handed world: +Y up, +Z ahead, +X right; azimuth clockwise from +Z toward +X.
// =====================================================================================================
#ifndef LANBAI_SKY_LAYERS_INCLUDED
#define LANBAI_SKY_LAYERS_INCLUDED

samplerCUBE _CubeA; half4 _CubeA_HDR;
samplerCUBE _CubeB; half4 _CubeB_HDR;
float _RotationA, _ExposureA, _ClampA;
float _RotationB, _ExposureB, _ClampB;
float4 _ZenithTintA, _MidTintA, _HorizonTintA, _HorizonAntiTintA;
float4 _ZenithTintB, _MidTintB, _HorizonTintB, _HorizonAntiTintB;
float4 _TintElevation;
float _Blend;
float4 _NadirColor, _BelowShape;
float _ProcWeight;
float4 _Band1Color, _Band1Shape, _Band2Color, _Band2Shape;
float _Band1Gain, _Band2Gain;
float _OtherSky, _OtherGain, _OtherSeam, _OtherFromB, _HorizonLift;
float4 _OtherTint;
float _NightBlend;
float4 _NightColor, _StarFloorAdd;
sampler2D _GlowTex;
float _GalaxyGain;
float4 _NightMaskDir, _NightMaskShape;
float4 _SunDir, _SunColor, _SunShape, _SunGlow, _SunGlowColor, _SunRemove;
float _SunGain;
sampler2D _MoonTex; float4 _MoonTex_TexelSize;
float4 _MoonDir, _MoonColor, _MoonGlow, _MoonGlowColor;
float _MoonRadius, _MoonGain;
float _Exposure;
float4 _PurpleGuard;
float _Dither;

#ifndef LANBAI_DECL__Udon_SkyBlend
#define LANBAI_DECL__Udon_SkyBlend
float4 _Udon_SkyBlend;     // x = cube A->B, y = procedural weight, z = night weight; w > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_SkyFx
#define LANBAI_DECL__Udon_SkyFx
float4 _Udon_SkyFx;        // x = other sky, y = band 1 gain, z unused (the sun line is _Udon_SunDisc.z); w > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_GalaxyGain
#define LANBAI_DECL__Udon_GalaxyGain
float4 _Udon_GalaxyGain;   // x = glow + star floor gain g(t); w > 0 = set
#endif


// ---- one material for the whole film (chief engineer r2 ruling): every per-preset property P above has a global
// _Udon_Sky_P (P without its leading underscore; float4, float properties in x). _Udon_SkyGlobals: x > 0.5 = read ALL of them from the globals (the
// presets / the driver write them; their values cross-fade), y > 0.5 = cube A from the global texture
// _Udon_SkyCubeTexA, z > 0.5 = cube B from _Udon_SkyCubeTexB (BC6H / RGBAHalf cubes: decode (1, 1, 0, 0)).
// The material values stay the defaults when nothing is set (editor preview, test scenes).
#ifndef LANBAI_DECL__Udon_SkyGlobals
#define LANBAI_DECL__Udon_SkyGlobals
float4 _Udon_SkyGlobals;
#endif
#ifndef LANBAI_DECL__Udon_SkyCubeTexA
#define LANBAI_DECL__Udon_SkyCubeTexA
samplerCUBE _Udon_SkyCubeTexA;
#endif
#ifndef LANBAI_DECL__Udon_SkyCubeTexB
#define LANBAI_DECL__Udon_SkyCubeTexB
samplerCUBE _Udon_SkyCubeTexB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ZenithTintA
#define LANBAI_DECL__Udon_Sky_ZenithTintA
float4 _Udon_Sky_ZenithTintA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MidTintA
#define LANBAI_DECL__Udon_Sky_MidTintA
float4 _Udon_Sky_MidTintA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_HorizonTintA
#define LANBAI_DECL__Udon_Sky_HorizonTintA
float4 _Udon_Sky_HorizonTintA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_HorizonAntiTintA
#define LANBAI_DECL__Udon_Sky_HorizonAntiTintA
float4 _Udon_Sky_HorizonAntiTintA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ZenithTintB
#define LANBAI_DECL__Udon_Sky_ZenithTintB
float4 _Udon_Sky_ZenithTintB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MidTintB
#define LANBAI_DECL__Udon_Sky_MidTintB
float4 _Udon_Sky_MidTintB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_HorizonTintB
#define LANBAI_DECL__Udon_Sky_HorizonTintB
float4 _Udon_Sky_HorizonTintB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_HorizonAntiTintB
#define LANBAI_DECL__Udon_Sky_HorizonAntiTintB
float4 _Udon_Sky_HorizonAntiTintB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_TintElevation
#define LANBAI_DECL__Udon_Sky_TintElevation
float4 _Udon_Sky_TintElevation;
#endif
#ifndef LANBAI_DECL__Udon_Sky_NadirColor
#define LANBAI_DECL__Udon_Sky_NadirColor
float4 _Udon_Sky_NadirColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_BelowShape
#define LANBAI_DECL__Udon_Sky_BelowShape
float4 _Udon_Sky_BelowShape;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Band1Color
#define LANBAI_DECL__Udon_Sky_Band1Color
float4 _Udon_Sky_Band1Color;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Band1Shape
#define LANBAI_DECL__Udon_Sky_Band1Shape
float4 _Udon_Sky_Band1Shape;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Band2Color
#define LANBAI_DECL__Udon_Sky_Band2Color
float4 _Udon_Sky_Band2Color;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Band2Shape
#define LANBAI_DECL__Udon_Sky_Band2Shape
float4 _Udon_Sky_Band2Shape;
#endif
#ifndef LANBAI_DECL__Udon_Sky_OtherTint
#define LANBAI_DECL__Udon_Sky_OtherTint
float4 _Udon_Sky_OtherTint;
#endif
#ifndef LANBAI_DECL__Udon_Sky_NightColor
#define LANBAI_DECL__Udon_Sky_NightColor
float4 _Udon_Sky_NightColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_StarFloorAdd
#define LANBAI_DECL__Udon_Sky_StarFloorAdd
float4 _Udon_Sky_StarFloorAdd;
#endif
#ifndef LANBAI_DECL__Udon_Sky_NightMaskDir
#define LANBAI_DECL__Udon_Sky_NightMaskDir
float4 _Udon_Sky_NightMaskDir;
#endif
#ifndef LANBAI_DECL__Udon_Sky_NightMaskShape
#define LANBAI_DECL__Udon_Sky_NightMaskShape
float4 _Udon_Sky_NightMaskShape;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunDir
#define LANBAI_DECL__Udon_Sky_SunDir
float4 _Udon_Sky_SunDir;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunColor
#define LANBAI_DECL__Udon_Sky_SunColor
float4 _Udon_Sky_SunColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunShape
#define LANBAI_DECL__Udon_Sky_SunShape
float4 _Udon_Sky_SunShape;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunGlow
#define LANBAI_DECL__Udon_Sky_SunGlow
float4 _Udon_Sky_SunGlow;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunGlowColor
#define LANBAI_DECL__Udon_Sky_SunGlowColor
float4 _Udon_Sky_SunGlowColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MoonDir
#define LANBAI_DECL__Udon_Sky_MoonDir
float4 _Udon_Sky_MoonDir;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MoonColor
#define LANBAI_DECL__Udon_Sky_MoonColor
float4 _Udon_Sky_MoonColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MoonGlow
#define LANBAI_DECL__Udon_Sky_MoonGlow
float4 _Udon_Sky_MoonGlow;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MoonGlowColor
#define LANBAI_DECL__Udon_Sky_MoonGlowColor
float4 _Udon_Sky_MoonGlowColor;
#endif
#ifndef LANBAI_DECL__Udon_Sky_PurpleGuard
#define LANBAI_DECL__Udon_Sky_PurpleGuard
float4 _Udon_Sky_PurpleGuard;
#endif
#ifndef LANBAI_DECL__Udon_Sky_SunRemove
#define LANBAI_DECL__Udon_Sky_SunRemove
float4 _Udon_Sky_SunRemove;
#endif
#ifndef LANBAI_DECL__Udon_Sky_RotationA
#define LANBAI_DECL__Udon_Sky_RotationA
float4 _Udon_Sky_RotationA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ExposureA
#define LANBAI_DECL__Udon_Sky_ExposureA
float4 _Udon_Sky_ExposureA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ClampA
#define LANBAI_DECL__Udon_Sky_ClampA
float4 _Udon_Sky_ClampA;
#endif
#ifndef LANBAI_DECL__Udon_Sky_RotationB
#define LANBAI_DECL__Udon_Sky_RotationB
float4 _Udon_Sky_RotationB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ExposureB
#define LANBAI_DECL__Udon_Sky_ExposureB
float4 _Udon_Sky_ExposureB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_ClampB
#define LANBAI_DECL__Udon_Sky_ClampB
float4 _Udon_Sky_ClampB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Band2Gain
#define LANBAI_DECL__Udon_Sky_Band2Gain
float4 _Udon_Sky_Band2Gain;
#endif
#ifndef LANBAI_DECL__Udon_Sky_OtherGain
#define LANBAI_DECL__Udon_Sky_OtherGain
float4 _Udon_Sky_OtherGain;
#endif
#ifndef LANBAI_DECL__Udon_Sky_OtherSeam
#define LANBAI_DECL__Udon_Sky_OtherSeam
float4 _Udon_Sky_OtherSeam;
#endif
#ifndef LANBAI_DECL__Udon_Sky_OtherFromB
#define LANBAI_DECL__Udon_Sky_OtherFromB
float4 _Udon_Sky_OtherFromB;
#endif
#ifndef LANBAI_DECL__Udon_Sky_HorizonLift
#define LANBAI_DECL__Udon_Sky_HorizonLift
float4 _Udon_Sky_HorizonLift;
#endif
#ifndef LANBAI_DECL__Udon_Sky_MoonRadius
#define LANBAI_DECL__Udon_Sky_MoonRadius
float4 _Udon_Sky_MoonRadius;
#endif
#ifndef LANBAI_DECL__Udon_Sky_Exposure
#define LANBAI_DECL__Udon_Sky_Exposure
float4 _Udon_Sky_Exposure;
#endif
#ifndef LANBAI_DECL__Udon_Sky_GlowScale
#define LANBAI_DECL__Udon_Sky_GlowScale
float4 _Udon_Sky_GlowScale;
#endif
static float4 p_ZenithTintA;
static float4 p_MidTintA;
static float4 p_HorizonTintA;
static float4 p_HorizonAntiTintA;
static float4 p_ZenithTintB;
static float4 p_MidTintB;
static float4 p_HorizonTintB;
static float4 p_HorizonAntiTintB;
static float4 p_TintElevation;
static float4 p_NadirColor;
static float4 p_BelowShape;
static float4 p_Band1Color;
static float4 p_Band1Shape;
static float4 p_Band2Color;
static float4 p_Band2Shape;
static float4 p_OtherTint;
static float4 p_NightColor;
static float4 p_StarFloorAdd;
static float4 p_NightMaskDir;
static float4 p_NightMaskShape;
static float4 p_SunDir;
static float4 p_SunColor;
static float4 p_SunShape;
static float4 p_SunGlow;
static float4 p_SunGlowColor;
static float4 p_MoonDir;
static float4 p_MoonColor;
static float4 p_MoonGlow;
static float4 p_MoonGlowColor;
static float4 p_PurpleGuard;
static float4 p_SunRemove;
static float p_RotationA;
static float p_ExposureA;
static float p_ClampA;
static float p_RotationB;
static float p_ExposureB;
static float p_ClampB;
static float p_Band2Gain;
static float p_OtherGain;
static float p_OtherSeam;
static float p_OtherFromB;
static float p_HorizonLift;
static float p_MoonRadius;
static float p_Exposure;
static float p_GlowScale;
float _GlowScale;
void LanbaiSkyLoadParams()
{
    bool g = _Udon_SkyGlobals.x > 0.5;
    p_ZenithTintA = g ? _Udon_Sky_ZenithTintA : _ZenithTintA;
    p_MidTintA = g ? _Udon_Sky_MidTintA : _MidTintA;
    p_HorizonTintA = g ? _Udon_Sky_HorizonTintA : _HorizonTintA;
    p_HorizonAntiTintA = g ? _Udon_Sky_HorizonAntiTintA : _HorizonAntiTintA;
    p_ZenithTintB = g ? _Udon_Sky_ZenithTintB : _ZenithTintB;
    p_MidTintB = g ? _Udon_Sky_MidTintB : _MidTintB;
    p_HorizonTintB = g ? _Udon_Sky_HorizonTintB : _HorizonTintB;
    p_HorizonAntiTintB = g ? _Udon_Sky_HorizonAntiTintB : _HorizonAntiTintB;
    p_TintElevation = g ? _Udon_Sky_TintElevation : _TintElevation;
    p_NadirColor = g ? _Udon_Sky_NadirColor : _NadirColor;
    p_BelowShape = g ? _Udon_Sky_BelowShape : _BelowShape;
    p_Band1Color = g ? _Udon_Sky_Band1Color : _Band1Color;
    p_Band1Shape = g ? _Udon_Sky_Band1Shape : _Band1Shape;
    p_Band2Color = g ? _Udon_Sky_Band2Color : _Band2Color;
    p_Band2Shape = g ? _Udon_Sky_Band2Shape : _Band2Shape;
    p_OtherTint = g ? _Udon_Sky_OtherTint : _OtherTint;
    p_NightColor = g ? _Udon_Sky_NightColor : _NightColor;
    p_StarFloorAdd = g ? _Udon_Sky_StarFloorAdd : _StarFloorAdd;
    p_NightMaskDir = g ? _Udon_Sky_NightMaskDir : _NightMaskDir;
    p_NightMaskShape = g ? _Udon_Sky_NightMaskShape : _NightMaskShape;
    p_SunDir = g ? _Udon_Sky_SunDir : _SunDir;
    p_SunColor = g ? _Udon_Sky_SunColor : _SunColor;
    p_SunShape = g ? _Udon_Sky_SunShape : _SunShape;
    p_SunGlow = g ? _Udon_Sky_SunGlow : _SunGlow;
    p_SunGlowColor = g ? _Udon_Sky_SunGlowColor : _SunGlowColor;
    p_MoonDir = g ? _Udon_Sky_MoonDir : _MoonDir;
    p_MoonColor = g ? _Udon_Sky_MoonColor : _MoonColor;
    p_MoonGlow = g ? _Udon_Sky_MoonGlow : _MoonGlow;
    p_MoonGlowColor = g ? _Udon_Sky_MoonGlowColor : _MoonGlowColor;
    p_PurpleGuard = g ? _Udon_Sky_PurpleGuard : _PurpleGuard;
    p_SunRemove = g ? _Udon_Sky_SunRemove : _SunRemove;
    p_RotationA = g ? _Udon_Sky_RotationA.x : _RotationA;
    p_ExposureA = g ? _Udon_Sky_ExposureA.x : _ExposureA;
    p_ClampA = g ? _Udon_Sky_ClampA.x : _ClampA;
    p_RotationB = g ? _Udon_Sky_RotationB.x : _RotationB;
    p_ExposureB = g ? _Udon_Sky_ExposureB.x : _ExposureB;
    p_ClampB = g ? _Udon_Sky_ClampB.x : _ClampB;
    p_Band2Gain = g ? _Udon_Sky_Band2Gain.x : _Band2Gain;
    p_OtherGain = g ? _Udon_Sky_OtherGain.x : _OtherGain;
    p_OtherSeam = g ? _Udon_Sky_OtherSeam.x : _OtherSeam;
    p_OtherFromB = g ? _Udon_Sky_OtherFromB.x : _OtherFromB;
    p_HorizonLift = g ? _Udon_Sky_HorizonLift.x : _HorizonLift;
    p_MoonRadius = g ? _Udon_Sky_MoonRadius.x : _MoonRadius;
    p_Exposure = g ? _Udon_Sky_Exposure.x : _Exposure;
    p_GlowScale = g ? _Udon_Sky_GlowScale.x : _GlowScale;
    if (p_GlowScale <= 0.0) p_GlowScale = 1.0;
}

// the source direction to sample so that the content appears rotated by +deg in azimuth (clockwise from above)
inline float3 LanbaiRotY(float3 V, float deg)
{
    float r = radians(deg);
    float s = sin(r), c = cos(r);
    return float3(V.x * c - V.z * s, V.y, V.x * s + V.z * c);
}

inline float LanbaiSunward(float3 V, float3 S, float p)
{
    float2 a = normalize(V.xz + float2(1e-5, 0.0));
    float2 b = normalize(S.xz + float2(1e-5, 0.0));
    return pow(saturate(0.5 + 0.5 * dot(a, b)), max(p, 0.01));
}

// one HDRI layer for a direction in the UPPER hemisphere (Vs.y >= 0). Tints: horizon (toward / away from the sun,
// azimuth weight ^ p_TintElevation.w) -> mid over [0, p_TintElevation.y], mid -> zenith over [p_TintElevation.y,
// p_TintElevation.z]; the horizon tint is full below p_TintElevation.x.
float3 LanbaiCubeTint(float3 Vs, float3 zt, float3 mt, float3 ht, float3 hat, float3 S)
{
    float el = LanbaiElevationDeg(Vs);
    float3 hTint = lerp(hat, ht, LanbaiSunward(Vs, S, p_TintElevation.w));
    float t1 = LanbaiUpStep(p_TintElevation.x, max(p_TintElevation.y, p_TintElevation.x + 0.1), el);
    float t2 = LanbaiUpStep(p_TintElevation.y, max(p_TintElevation.z, p_TintElevation.y + 0.1), el);
    return lerp(lerp(hTint, mt, t1), zt, t2);
}

float3 LanbaiCubeUpper(samplerCUBE cube, half4 hdr, float3 Vs, float rot, float ev, float clampV,
                       float3 zt, float3 mt, float3 ht, float3 hat, float3 S, float lod)
{
    // the HDRI's own horizon (a dark haze / ground line in every 'pure sky') is never sampled: lift to p_HorizonLift deg
    float3 Vl = Vs;
    Vl.y = max(Vl.y, sin(radians(p_HorizonLift)));
    float3 d = LanbaiRotY(normalize(Vl), rot);
    half4 raw = texCUBElod(cube, float4(d, lod));
    float3 c = DecodeHDR(raw, hdr);
    c = min(c * exp2(ev), clampV);
    c *= LanbaiCubeTint(Vs, zt, mt, ht, hat, S);
    // the HDRI's own sun (a flat blob ~3 deg wide where the HDRI clipped; the mips blur it further) is taken out
    // (director r2 #3): within p_SunRemove.x deg of the sun the luminance is soft-capped (knee 4, hue kept) at
    //   cap(a) = p_SunRemove.y x (max(a, 1.5) / x)^-z     (linear, after the tints; y ~ the sky at radius x; z = a gentle
    //                                                       aureole so the cap is a glow, not a flat disc)
    // and the clipped (whitish) blob's hue pulled toward the sun colour by w. 1.5x radius fade: monotone, no ring.
    // The crisp procedural disc + the bloom are the sun.
    [branch] if (p_SunRemove.x > 0.0)
    {
        float as = LanbaiAngleDeg(Vs, S);
        float w = 1.0 - smoothstep(p_SunRemove.x, 1.5 * p_SunRemove.x, as);
        float L = max(dot(c, float3(0.2126, 0.7152, 0.0722)), 1e-6);
        float cap = max(p_SunRemove.y, 1e-4) * pow(max(as, 1.5) / p_SunRemove.x, -p_SunRemove.z);
        float q = L / cap;
        float3 capped = c * rsqrt(sqrt(1.0 + q * q * q * q));
        float3 sunHue = p_SunColor.rgb / max(dot(p_SunColor.rgb, float3(0.2126, 0.7152, 0.0722)), 1e-4);
        float k = p_SunRemove.w * saturate(q - 1.0);          // only where the cap actually bit
        capped = lerp(capped, sunHue * dot(capped, float3(0.2126, 0.7152, 0.0722)), k);
        c = lerp(c, capped, w);
    }
    return c;
}

// a full-sphere HDRI layer: upper = the tinted HDRI; lower = its horizon (clamped to p_BelowShape.w so the sun does
// not leak a column below it) -> p_NadirColor
float3 LanbaiCubeLayer(samplerCUBE cube, half4 hdr, float3 V, float rot, float ev, float clampV,
                       float3 zt, float3 mt, float3 ht, float3 hat, float3 S)
{
    if (V.y >= 0.0)
        return LanbaiCubeUpper(cube, hdr, V, rot, ev, clampV, zt, mt, ht, hat, S, 0.0);
    float el = LanbaiElevationDeg(V);
    float3 H = normalize(float3(V.x, sin(radians(p_BelowShape.z * smoothstep(0.0, 3.0, -el))), V.z));   // no step at 0
    float hc = (p_BelowShape.w > 0.0) ? p_BelowShape.w : clampV;
    float3 hzSharp = LanbaiCubeUpper(cube, hdr, H, rot, ev, clampV, zt, mt, ht, hat, S, 0.0);
    float3 hzSoft = LanbaiCubeUpper(cube, hdr, H, rot, ev, hc, zt, mt, ht, hat, S, 3.0);
    float3 hz = lerp(hzSharp, hzSoft, smoothstep(0.0, 3.0, -el));          // continuous at the horizon, no streaks below
    float t = LanbaiUpStep(0.0, max(-p_BelowShape.x, 0.1), -el);         // = the zenith rule at the nadir: no point, no ring
    t = pow(t, max(p_BelowShape.y, 0.01));
    float3 c = lerp(hz, p_NadirColor.rgb, t);
    // the middle of a warm -> indigo gradient passes through mauve: desaturate it toward a cold grey (p_NadirColor.a)
    float lum = dot(c, float3(0.2126, 0.7152, 0.0722));
    return lerp(c, lum * float3(0.90, 0.97, 1.13), saturate(p_NadirColor.a * 4.0 * t * (1.0 - t)));
}

float3 LanbaiCubes(float3 V, float3 S, float blend)
{
    float3 c = 0;
    half4 hdrA = (_Udon_SkyGlobals.y > 0.5) ? half4(1, 1, 0, 0) : _CubeA_HDR;
    half4 hdrB = (_Udon_SkyGlobals.z > 0.5) ? half4(1, 1, 0, 0) : _CubeB_HDR;
    [branch] if (blend < 0.999 && _Udon_SkyGlobals.y > 0.5)
        c = LanbaiCubeLayer(_Udon_SkyCubeTexA, hdrA, V, p_RotationA, p_ExposureA, p_ClampA,
                            p_ZenithTintA.rgb, p_MidTintA.rgb, p_HorizonTintA.rgb, p_HorizonAntiTintA.rgb, S) * (1.0 - blend);
    else if (blend < 0.999)
        c = LanbaiCubeLayer(_CubeA, hdrA, V, p_RotationA, p_ExposureA, p_ClampA,
                            p_ZenithTintA.rgb, p_MidTintA.rgb, p_HorizonTintA.rgb, p_HorizonAntiTintA.rgb, S) * (1.0 - blend);
    [branch] if (blend > 0.001 && _Udon_SkyGlobals.z > 0.5)
        c += LanbaiCubeLayer(_Udon_SkyCubeTexB, hdrB, V, p_RotationB, p_ExposureB, p_ClampB,
                             p_ZenithTintB.rgb, p_MidTintB.rgb, p_HorizonTintB.rgb, p_HorizonAntiTintB.rgb, S) * blend;
    else if (blend > 0.001)
        c += LanbaiCubeLayer(_CubeB, hdrB, V, p_RotationB, p_ExposureB, p_ClampB,
                             p_ZenithTintB.rgb, p_MidTintB.rgb, p_HorizonTintB.rgb, p_HorizonAntiTintB.rgb, S) * blend;
    return c;
}

// sun disc or (sunLine > 0) the horizontal sun line of act 8; returns HDR colour
float3 LanbaiSunTerm(float3 V, float3 S, float gain, float radius, float sunLine)
{
    float a;
    if (sunLine > 0.0)
    {
        float dE = LanbaiElevationDeg(V) - LanbaiElevationDeg(S);
        float2 vh = normalize(V.xz + float2(1e-5, 0.0)), sh = normalize(S.xz + float2(1e-5, 0.0));
        float dA = degrees(acos(clamp(dot(vh, sh), -1.0, 1.0))) * cos(radians(LanbaiElevationDeg(S)));
        float dx = max(dA - sunLine, 0.0);
        a = sqrt(dx * dx + dE * dE);
    }
    else
    {
        a = LanbaiAngleDeg(V, S);
    }
    // the edge never narrower than 2 VR pixels; a disc much brighter than 1 clips to white far inside its soft edge,
    // so the coverage is sharpened by the peak (otherwise the visible edge is ~0.1 px and crawls) (tech r2 #7)
    float soft = max(p_SunShape.y, 2.0 * degrees(LanbaiPixelAngle()));
    float edge = smoothstep(radius + 0.5 * soft, radius - 0.5 * soft, a);
    float peak = max(max(p_SunColor.r, p_SunColor.g), p_SunColor.b) * gain;
    edge = (peak > 1.0) ? pow(edge, log2(peak) + 1.0) : edge;
    float r = saturate(a / max(radius, 1e-3));
    float limb = 1.0 - p_SunShape.z * (1.0 - sqrt(saturate(1.0 - r * r)));
    float3 c = p_SunColor.rgb * (edge * limb);
    c += p_SunGlowColor.rgb * (p_SunGlow.x * exp(-p_SunGlow.y * a) + p_SunGlow.z * exp(-p_SunGlow.w * a));
    return c * gain;
}

float3 LanbaiMoonTerm(float3 V, float gain)
{
    float3 M = LanbaiSkyMoonDir(p_MoonDir.xyz);
    float radius = (_Udon_MoonDisc.w > 0.0) ? _Udon_MoonDisc.y : p_MoonRadius;
    float am = LanbaiAngleDeg(V, M);
    float3 c = p_MoonGlowColor.rgb * (p_MoonGlow.x * exp(-p_MoonGlow.y * am) + p_MoonGlow.z * exp(-p_MoonGlow.w * am));
    if (am < radius * 1.2 && dot(V, M) > 0.0)
    {
        float3 up = (abs(M.y) < 0.999) ? float3(0.0, 1.0, 0.0) : float3(0.0, 0.0, 1.0);   // the moon at the zenith
        float3 R = normalize(cross(up, M));
        float3 U = cross(M, R);
        float k = 0.5 / tan(radians(radius));
        float2 uv = 0.5 + float2(dot(V, R), dot(V, U)) / max(dot(V, M), 1e-4) * k;
        // the 1024 px disc covers ~20 screen px: pick the mip that matches one texel to one pixel (no shimmer in VR)
        float texPerPix = LanbaiPixelAngle() * k * max(_MoonTex_TexelSize.z, 1.0);
        float4 t = tex2Dlod(_MoonTex, float4(uv, 0.0, max(log2(max(texPerPix, 1e-4)), 0.0)));
        c = lerp(c, t.rgb * p_MoonColor.rgb, t.a);
    }
    return c * gain;
}

float3 LanbaiGalaxy(float3 V)
{
    return tex2Dlod(_GlowTex, float4(LanbaiGalaxyUV(V), 0.0, 0.0)).rgb * p_GlowScale;     // the PNG is normalised
}

// two horizon bands (earth shadow / Venus belt at dawn; the blue-hour band; the waking line of act 12): the sky is
// pulled toward the band colour with a Gaussian weight in elevation and in azimuth measured from the sun
// (shape: x centre el deg, y el sigma deg, z azimuth centre from the sun deg (0 = sunward, 180 = anti-sun),
// w azimuth sigma deg). Band 1's gain can come from the global _Udon_SkyFx.y.
float LanbaiBandWeight(float3 V, float3 S, float4 shape)
{
    float el = LanbaiElevationDeg(V);
    float az = LanbaiAzimuthDeg(V, S);
    float de = (el - shape.x) / max(shape.y, 0.1);
    float da = (az - shape.z) / max(shape.w, 0.1);
    float we = exp(-0.5 * de * de);
    float wa = exp(-0.5 * da * da);
    return we * wa;
}
// colour.a of a band = how much the middle of its transition is pulled to a cold grey: a warm band over an indigo sky
// otherwise passes through mauve on its edge (the purple rule, bible §1.3.4)
float3 LanbaiBandBlend(float3 c, float4 bandColor, float w)
{
    float3 o = lerp(c, bandColor.rgb, w);
    float lum = dot(o, float3(0.2126, 0.7152, 0.0722));
    return lerp(o, lum * float3(0.90, 0.97, 1.13), saturate(bandColor.a * 4.0 * w * (1.0 - w)));
}
// shape.y < 0 = a MONOTONIC band (the blue hour): below its centre a Gaussian of |y|, above it the band holds until
// the sky itself is darker than the band (so the brightness only falls from the horizon to the zenith: no strip)
float3 LanbaiMonotonicBand(float3 c, float3 V, float3 S, float4 bandColor, float4 shape, float gain)
{
    float el = LanbaiElevationDeg(V);
    float4 sh = shape; sh.y = -shape.y;
    float w = (el < shape.x) ? LanbaiBandWeight(V, S, sh) : LanbaiBandWeight(V, S, float4(el, 1.0, shape.z, shape.w));
    float3 o = LanbaiBandBlend(c, bandColor, saturate(gain * w));
    float lc = dot(c, float3(0.2126, 0.7152, 0.0722)), lo = dot(o, float3(0.2126, 0.7152, 0.0722));
    // a soft minimum (over a 30 % luminance difference): a hard min() leaves a visible kink where the two cross
    float k = saturate((lo - lc) / max(0.3 * lo, 1e-5));
    return (el > shape.x) ? lerp(o, c, k * k * (3.0 - 2.0 * k)) : o;
}
float3 LanbaiApplyBands(float3 c, float3 V, float3 S, float band1Gain)
{
    [branch] if (band1Gain > 0.0 && p_Band1Shape.y < 0.0)
        c = LanbaiMonotonicBand(c, V, S, p_Band1Color, p_Band1Shape, band1Gain);
    else if (band1Gain > 0.0)
        c = LanbaiBandBlend(c, p_Band1Color, saturate(band1Gain * LanbaiBandWeight(V, S, p_Band1Shape)));
    [branch] if (p_Band2Gain > 0.0)
        c = LanbaiBandBlend(c, p_Band2Color, saturate(p_Band2Gain * LanbaiBandWeight(V, S, p_Band2Shape)));
    return c;
}

// the purple rule (bible §1.3.4: outside act 4 no > 2 % area with h_ab 290..325, C* > 15). A bluish sky whose red is
// close to its green turns mauve under a warm grade (S8: temperature +3, tint +1). Where B/G > g.z, keep R/G <= g.y
// (strength g.x, ramping in over 0.3 of B/G). Warm colours, rose / pink (B ~ G) and true blues (R << G) are untouched.
float3 LanbaiPurpleGuard(float3 c, float4 g)
{
    if (g.x <= 0.0 || c.g <= 1e-6)
        return c;
    float bg = c.b / c.g;
    float w = g.x * smoothstep(g.z, g.z + 0.3, bg);
    c.r = lerp(c.r, min(c.r, c.g * g.y), w);
    return c;
}

// act 8b -> 9: per-direction night weight. x = 0..1 over the 8 s darkening; the back and the zenith reach 1 at
// x = 0.75 (6 s), the front horizon band (|az| < 40 deg of p_NightMaskDir, below ~12 deg) is still 50 % at 0.75 and
// reaches 1 at x = 1. (bible §6·8b: front band >= 50 % at 1007.2, black at 1009.21; elsewhere black in 6 s)
float LanbaiNightWeight(float3 V, float x)
{
    float az = LanbaiAzimuthDeg(V, p_NightMaskDir.xyz);
    float el = LanbaiElevationDeg(V);
    float f = (1.0 - smoothstep(p_NightMaskShape.x, p_NightMaskShape.x + p_NightMaskShape.y, az))
            * (1.0 - smoothstep(p_NightMaskShape.z, p_NightMaskShape.z + p_NightMaskShape.w, abs(el)));
    float d = 0.5 * f;
    float w = saturate((x - d) / (0.75 - 0.25 * f));
    return w * w * (3.0 - 2.0 * w);                       // eased: no visible edge where neighbouring directions differ
}

float3 LanbaiSkyColour(float3 V)
{
    LanbaiSkyLoadParams();
    float blend = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.x : _Blend;
    float proc  = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.y : _ProcWeight;
    float night = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.z : _NightBlend;
    float other = (_Udon_SkyFx.w > 0.0) ? _Udon_SkyFx.x : _OtherSky;
    float bandG = (_Udon_SkyFx.w > 0.0) ? _Udon_SkyFx.y : _Band1Gain;
    float sunLine  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.z : p_SunShape.w;
    float gal   = (_Udon_GalaxyGain.w > 0.0) ? _Udon_GalaxyGain.x : _GalaxyGain;
    float sunG  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.x : _SunGain;
    float sunR  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.y : p_SunShape.x;
    float moonG = (_Udon_MoonDisc.w > 0.0) ? _Udon_MoonDisc.x : _MoonGain;
    float3 S = LanbaiSunDir(p_SunDir.xyz);

    // 1-2. cubes, procedural
    float3 c = 0;
    [branch] if (proc < 0.999)
        c = LanbaiCubes(V, S, blend) * (1.0 - proc);
    [branch] if (proc > 0.001)
        c += LanbaiHorizon(V) * proc;
    c = LanbaiApplyBands(c, V, S, bandG);
    [branch] if (sunG > 0.0)
        c += LanbaiSunTerm(V, S, sunG, sunR, sunLine);

    // 3. the other sky below the horizon (its own sun included: the burning line of two suns)
    [branch] if (other > 0.001 && V.y < 0.02)
    {
        float w = other * LanbaiOtherSkyWeight(V, p_OtherSeam);
        float3 Vo = LanbaiOtherSkyDir(V);
        Vo.y = abs(Vo.y);
        // the other sky: the same cubes rotated 180 deg about +Z, or (p_OtherFromB = 1) cube B: other air, other light
        float3 o = (p_OtherFromB > 0.5) ? LanbaiCubes(Vo, S, 1.0) : LanbaiCubes(Vo, S, blend);
        if (sunG > 0.0)
            o += LanbaiSunTerm(Vo, S, sunG, sunR, sunLine);
        c = lerp(c, o * p_OtherGain * p_OtherTint.rgb, w);
    }

    c = LanbaiPurpleGuard(c, p_PurpleGuard);

    // 4. night
    [branch] if (night > 0.001)
    {
        float3 n = p_NightColor.rgb + gal * (p_StarFloorAdd.rgb + LanbaiGalaxy(V));
        c = lerp(c, n, LanbaiNightWeight(V, night));
    }

    // 5. moon
    [branch] if (moonG > 0.0)
        c += LanbaiMoonTerm(V, moonG);

    return max(c, 0.0) * exp2(p_Exposure);
}

#endif // LANBAI_SKY_LAYERS_INCLUDED
