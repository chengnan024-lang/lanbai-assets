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
float4 _GlowTex_TexelSize;
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
float4 _Udon_GalaxyGain;   // x = glow + star floor gain g(t) (the arms), y = the core's gain, z = 1: y in use; w > 0 = set
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
#ifndef LANBAI_DECL__Udon_Sky_BelowMirror
#define LANBAI_DECL__Udon_Sky_BelowMirror
float4 _Udon_Sky_BelowMirror;
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
static float p_BelowMirror;
float _GlowScale;
float _BelowMirror;
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
    p_BelowMirror = g ? _Udon_Sky_BelowMirror.x : _BelowMirror;
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
    return LanbaiGeoLerp(lerp(hTint, mt, t1), zt, t2);     // mid -> zenith in log space: even on screen, no dark disc overhead
}

// the HDRI as it is (lifted off its own horizon line, rotated, exposed, clamped, tinted), no sun removal
float3 LanbaiCubeRaw(samplerCUBE cube, half4 hdr, float3 Vs, float rot, float ev, float clampV,
                     float3 zt, float3 mt, float3 ht, float3 hat, float3 S, float lod)
{
    // the HDRI's own horizon (a dark haze / ground line in every 'pure sky') is never sampled: lift to p_HorizonLift deg
    float3 Vl = Vs;
    Vl.y = max(Vl.y, sin(radians(p_HorizonLift)));
    float3 d = LanbaiRotY(normalize(Vl), rot);
    half4 raw = texCUBElod(cube, float4(d, lod));
    float3 c = DecodeHDR(raw, hdr);
    c = min(c * exp2(ev), clampV);
    return c * LanbaiCubeTint(Vs, zt, mt, ht, hat, S);
}

inline float LanbaiSq(float x) { return x * x; }

float3 LanbaiCubeUpper(samplerCUBE cube, half4 hdr, float3 Vs, float rot, float ev, float clampV,
                       float3 zt, float3 mt, float3 ht, float3 hat, float3 S, float lod)
{
    float3 c = LanbaiCubeRaw(cube, hdr, Vs, rot, ev, clampV, zt, mt, ht, hat, S, lod);
    // the HDRI's own sun (a clipped blob ~3 deg wide, blurred further by the mips) is taken out (director r2 #3,
    // final review 1: the 0.53 deg disc must read at 1080p). Within p_SunRemove.x deg of the sun:
    //  y <= 0 (inpaint mode, v1.2 final): the circle is rebuilt row by row from its own left and right edge at the same
    //     elevation (the sky's warm-below / pale-above gradient stays; the same colour on the circle: no disc, no ring;
    //     no rays, a radial rebuild drew a starburst), x (x / a)^z = a gentle aureole; weight 1 inside 0.6 x, 0 at x.
    //     The procedural disc + the bloom are the sun.
    //  y > 0 (cap mode, v1.2): luminance soft-capped at y (knee 8), hue pulled toward the sun colour by w.
    [branch] if (p_SunRemove.x > 0.0)
    {
        float as = LanbaiAngleDeg(Vs, S);
        // w > 0: an ELLIPSE, x = its azimuth half-width, w = its elevation half-height (deg on the sky; act 8 final
        // review: the dusk HDRI's vertical brightness step 2.5 deg right of the sun, in the middle of the thesis frame,
        // is rebuilt the same way, so the row runs smoothly across it). w = 0: the circle of radius x (dawn).
        float Ra = p_SunRemove.x, Re = (p_SunRemove.w > 0.0) ? p_SunRemove.w : p_SunRemove.x;
        float elS = LanbaiElevationDeg(S), el = LanbaiElevationDeg(Vs);
        float dEl = el - elS;
        [branch] if (p_SunRemove.y <= 0.0 && abs(dEl) < Re && as < max(Ra, Re))
        {
            // inpaint the ellipse row by row: each elevation is interpolated between the ellipse's left and right edge
            // at that same elevation (the sky's vertical gradient stays, no rays, the same colour across)
            float azS = degrees(atan2(S.x, S.z)), az = degrees(atan2(Vs.x, Vs.z + 1e-6));
            float cosS = max(cos(radians(elS)), 0.05);
            float dAz = (frac((az - azS) / 360.0 + 0.5) - 0.5) * 360.0 * cosS;     // on the sky, deg
            float hw = Ra * sqrt(max(1.0 - LanbaiSq(dEl / Re), 1e-4));
            float q = (p_SunRemove.w > 0.0) ? sqrt(LanbaiSq(dAz / Ra) + LanbaiSq(dEl / Re)) : as / Ra;   // 1 on the rim
            float ce = cos(radians(el)), se = sin(radians(el));
            float azL = radians(azS - hw / cosS), azR = radians(azS + hw / cosS);
            float3 VL = float3(sin(azL) * ce, se, cos(azL) * ce);
            float3 VR = float3(sin(azR) * ce, se, cos(azR) * ce);
            float3 fill = lerp(LanbaiCubeRaw(cube, hdr, VL, rot, ev, clampV, zt, mt, ht, hat, S, lod),
                               LanbaiCubeRaw(cube, hdr, VR, rot, ev, clampV, zt, mt, ht, hat, S, lod),
                               saturate((dAz + hw) / (2.0 * hw)))
                        * pow(Ra / max(as, 0.5), p_SunRemove.z);
            float w = 1.0 - smoothstep(0.6, 1.0, q);
            c = lerp(c, fill, w);
        }
        else if (p_SunRemove.y > 0.0)
        {
            float w = 1.0 - smoothstep(p_SunRemove.x, 1.5 * p_SunRemove.x, as);
            float L = max(dot(c, float3(0.2126, 0.7152, 0.0722)), 1e-6);
            float cap = p_SunRemove.y * pow(max(as, 1.5) / p_SunRemove.x, -p_SunRemove.z);
            float q = min(L / cap, 1e4);   // q^8 stays finite
            float q4 = q * q * q * q;
            float3 capped = c * rsqrt(sqrt(sqrt(1.0 + q4 * q4)));
            float3 sunHue = p_SunColor.rgb / max(dot(p_SunColor.rgb, float3(0.2126, 0.7152, 0.0722)), 1e-4);
            float k = p_SunRemove.w * saturate(q - 1.0);
            capped = lerp(capped, sunHue * dot(capped, float3(0.2126, 0.7152, 0.0722)), k);
            c = lerp(c, capped, w);
        }
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
    // p_BelowMirror = 1: below the horizon the sky continues (8-i, art r2 #1): sampled at the mirrored elevation
    // (amber -> rose -> mid sky going down), darkened toward the nadir; 0: the horizon colour carried down (v1.1)
    float sEl = lerp(p_BelowShape.z * smoothstep(0.0, 3.0, -el), max(-el, p_BelowShape.z), saturate(p_BelowMirror));
    float3 H = normalize(float3(V.x, sin(radians(sEl)), V.z));   // no step at 0
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
// a fixed ripple along the horizon (azimuth degrees -> about -1 .. 1): the sun line's core width and its burning-out
// pattern. Fixed in the sky (not in time, not in the line's own length), so a shrinking line burns down through it
// instead of sliding like a bar.
inline float LanbaiLineRipple(float x)
{
    return 0.55 * sin(x * 1.37 + 0.6) + 0.30 * sin(x * 3.11 + 2.1) + 0.15 * sin(x * 7.3 + 4.4);
}

float3 LanbaiSunTerm(float3 V, float3 S, float gain, float radius, float sunLine)
{
    float soft = max(p_SunShape.y, 2.0 * degrees(LanbaiPixelAngle()));   // >= 2 VR pixels (tech r2 #7)
    float peakHdr = max(max(p_SunColor.r, p_SunColor.g), p_SunColor.b) * gain;
    if (sunLine > 0.0)
    {
        // THE SUN LINE (act 8 / D-39: the sun and its other self lie on one line). Not a tube of one brightness with
        // cut ends (act 8 final review): brightest at the sun, dimming toward both ends, feathered pointed tips; the
        // core's width tapers and varies a little; a wide halo for bloom. gain < 1 (the collapse after F12, driven by
        // _Udon_SunDisc.x together with the length) = burning out: the core thins and goes out unevenly along the
        // fixed ripple, the halo lingers.
        float elS = LanbaiElevationDeg(S);
        float dE = LanbaiElevationDeg(V) - elS;
        float2 vh = normalize(V.xz + float2(1e-5, 0.0)), sh = normalize(S.xz + float2(1e-5, 0.0));
        float azV = degrees(atan2(vh.x, vh.y));
        float dA = degrees(acos(clamp(dot(vh, sh), -1.0, 1.0))) * cos(radians(elS));
        float burn = 1.0 - saturate(gain);
        float u = dA / (sunLine + radius);                         // 0 at the sun, 1 at the tip
        float along = pow(saturate(1.0 - u), 2.5);                 // the core's brightness along the line
        float rip = LanbaiLineRipple(azV);                         // in world azimuth: fixed in the sky
        float rip2 = LanbaiLineRipple(azV * 2.3 + 17.0);
        along *= saturate(1.0 - burn * (0.55 + 0.45 * rip2));      // burning out unevenly
        float hw = radius * (0.30 + 0.70 * pow(saturate(1.0 - u), 0.6)) * (1.0 + (0.18 + 0.30 * burn) * rip) * (1.0 - 0.45 * burn);
        hw = max(hw, 0.25 * radius);
        float core = smoothstep(hw + 0.5 * soft, hw - 0.5 * soft, abs(dE)) * step(u, 1.0);
        float pk = peakHdr * along;
        core = (pk > 1.0) ? pow(core, log2(pk) + 1.0) : core;     // a clipped core keeps a ~pixel edge (no crawl)
        // the halo: wider and longer than the core, same dimming along, outlasts the core while it burns
        float uh = dA / (1.25 * sunLine + 1.5);
        float alongH = pow(saturate(1.0 - uh), 1.6) * (1.0 - 0.5 * burn);
        float halo = alongH * (0.10 * exp(-0.5 * LanbaiSq(dE / 0.35)) + 0.035 * exp(-0.5 * LanbaiSq(dE / 1.2)));
        float3 c = p_SunColor.rgb * (core * along + halo);
        float ag = sqrt(LanbaiSq(max(dA - sunLine, 0.0)) + dE * dE);   // the sun's own glow, as the disc's
        c += p_SunGlowColor.rgb * (p_SunGlow.x * exp(-p_SunGlow.y * ag) + p_SunGlow.z * exp(-p_SunGlow.w * ag)) * (0.6 + 0.4 * alongH);
        return c * gain;
    }
    float a = LanbaiAngleDeg(V, S);
    // a disc much brighter than 1 clips to white far inside its soft edge, so the coverage is sharpened by the peak
    // (otherwise the visible edge is ~0.1 px and crawls) (tech r2 #7)
    float edge = smoothstep(radius + 0.5 * soft, radius - 0.5 * soft, a);
    edge = (peakHdr > 1.0) ? pow(edge, log2(peakHdr) + 1.0) : edge;
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
    return LanbaiGalaxySample(_GlowTex, _GlowTex_TexelSize, V, p_GlowScale);   // the shared sample (LanbaiSky.cginc)
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
// the two-sided guard's crossing (act 8 final review: the khaki band C* 3-5 between the blue and the rose, and the
// 'lotus-purple' rose at F12): MID = where in the crossing (ts 0 blue .. 1 pink) the colour is sent to a lifted pale
// tint, COOL / WARM = that tint on the blue / the pink side (a pale silver-blue / a peach-cream: the rose pales out
// into the blue instead of passing a grey-khaki band), TW = where it turns from one to the other; PINK = a rose keeps
// green >= z x blue once red leads green by x .. y (no mauve, also not under the cooler blue-hour grade)
#ifndef LANBAI_GUARD_MID
#define LANBAI_GUARD_MID float4(0.28, 0.45, 0.65, 0.88)
#endif
#ifndef LANBAI_GUARD_COOL
#define LANBAI_GUARD_COOL float3(0.90, 1.16, 1.40)
#endif
#ifndef LANBAI_GUARD_WARM
#define LANBAI_GUARD_WARM float3(1.34, 1.14, 1.02)
#endif
#ifndef LANBAI_GUARD_TW
#define LANBAI_GUARD_TW float2(0.40, 0.62)
#endif
#ifndef LANBAI_GUARD_PINK
#define LANBAI_GUARD_PINK float3(1.15, 1.45, 1.08)
#endif
float3 LanbaiPurpleGuard(float3 c, float4 g)
{
    if (g.x <= 0.0 || c.g <= 1e-6)
        return c;
    float bg = c.b / c.g;
    float w = g.x * smoothstep(g.z, g.z + 0.3, bg);
    if (g.w < 0.0)
    {
        // two-sided mode (D-21 rev.: after the grade nothing at h_ab 290-330 with C* > 8 and L* > 40; the bible's own
        // colours, e.g. the mid sky #808AB2 at h 285, stay as they are):
        //  * a strong blue (B / G >= 1.3) whose red would grade into lavender: R held at 0.64 G
        //    (mild: it stays the bible's blue, not cyan);
        //  * the weak-blue transition where the rose meets the blue (B / G 0.95 .. 1.25, R near G): its middle toward
        //    a lifted pale tint, silver-blue on the blue side and peach-cream on the rose side (LANBAI_GUARD_*), by -g.w;
        //  * a rose keeps G >= 1.08 B (not mauve)
        float rg = c.r / c.g;
        // a lavender has red ~ blue (R / B ~0.7 .. 1.1); a pink (red clearly above blue: h 330-360 / 0-20, not in the
        // band) is left alone, so the anti-sun rose belt stays pink (and the strong cut must not pull a magenta-pink
        // down INTO lavender: it only touches colours where blue leads red)
        float rb = c.r / max(c.b, 1e-6);
        float strong = smoothstep(1.10, 1.30, bg) * (1.0 - smoothstep(0.9, 1.1, rb));
        float3 o = c;
        o.r = lerp(c.r, min(c.r, c.g * 0.64), g.x * strong);
        // ... and a lavender is also not a true blue: R / B above ~0.65 (the bible's mid sky #808AB2 is R / B ~0.5 and
        // stays exactly as it is)
        // where the rose meets the blue: the red / blue ratio pushed toward the ends, only the middle sent to the pale
        // tint (a soft ~1.5 deg crossing; a narrower one drew a crisp contour line along the HDRI's waves)
        float cap = g.x * smoothstep(g.z, g.z + 0.1, bg) * smoothstep(g.y - 0.08, g.y, rg)
                  * smoothstep(0.5, 0.62, rb) * (1.0 - smoothstep(1.35, 1.5, rb));   // only inside the crossing (to 1.35: a magenta-pink
                                                                            // grades to lavender under the cooler blue-hour grade)
        float tr = saturate((rb - 0.6) / 0.8);
        float ts = tr;
        float tgt = o.b * lerp(0.5, 1.6, ts);                  // the ends graded: a true blue (h < 290) / a pink (h > 330)
        tgt = lerp(min(o.r, tgt), max(o.r, tgt), smoothstep(0.3, 0.7, ts));   // the blue side only loses red, the pink side
                                                                              // only gains it; blended across the middle (no step)
        o.r = lerp(o.r, tgt, cap);
        float mid = cap * smoothstep(LANBAI_GUARD_MID.x, LANBAI_GUARD_MID.y, ts) * (1.0 - smoothstep(LANBAI_GUARD_MID.z, LANBAI_GUARD_MID.w, ts));   // the middle, never the blue end (it would grey a blue into lavender)
        float lum = dot(o, float3(0.2126, 0.7152, 0.0722));
        // a pale, slightly lifted white: warm (gold) toward the pink side, cool toward the blue side, so the blue half of the
        // seam is never warmed into lavender
        float3 tint = lerp(LANBAI_GUARD_COOL, LANBAI_GUARD_WARM, smoothstep(LANBAI_GUARD_TW.x, LANBAI_GUARD_TW.y, ts));
        o = lerp(o, lum * tint, saturate(-g.w * mid));
        // a rose, not a mauve (act 8 final review: the 'lotus-purple' band at F12, a rose with blue above green, and the
        // magenta a rose and a blue make while they cross-fade): where red clearly leads, green is kept at least
        // LANBAI_GUARD_PINK.z x blue (h_ab ~350 -> ~10..20); the bible's roses have G = B and stay as they are
        float pinkness = smoothstep(LANBAI_GUARD_PINK.x, LANBAI_GUARD_PINK.y, o.r / max(o.g, 1e-6));
        o.g = lerp(o.g, max(o.g, o.b * LANBAI_GUARD_PINK.z), g.x * pinkness);
        return o;
    }
    c.r = lerp(c.r, min(c.r, c.g * g.y), w);                 // v1: R <= y G where blue leads
    return c;
}

// act 8b -> 9: per-direction night weight. x = 0..1 over the 8 s darkening; the back and the zenith reach 1 at
// x = 0.75 (6 s), the front horizon band (|az| <= p_NightMaskShape.x = 40 deg of p_NightMaskDir, below ~6 deg) is still
// 50 % at 0.75 and reaches 1 at x = 1. (bible §6·8b: front ±40° band >= 50 % at 1007.2, black at 1009.21; elsewhere
// black in 6 s)

float LanbaiNightWeight(float3 V, float x)
{
    float az = abs(LanbaiAzimuthDeg(V, p_NightMaskDir.xyz));
    float el = LanbaiElevationDeg(V);
    // the last light is a BAND lying on the horizon, not a shape (act 9 reviews: two windows multiplied drew a glowing
    // rounded rectangle, an ellipse floated, then stood as a 15 deg dome / "flying saucer"):
    //  - azimuth: full to x, gone at x + y (soft ends);
    //  - its top is a superellipse in azimuth (exponent 4): flat across the plateau, pinching only at the ends;
    //  - elevation: full to z, gone at z + w; the elevation axes close toward the horizon in the last part of the
    //    darkening (x 0.7 -> 0.95: to a quarter), so the last light is a sliver a few degrees high;
    //  - below the horizon the elevation counts 4x: the sky under the horizon goes dark first.
    // f only ever falls as x rises, and a lower f only ever darkens (d(w)/d(f) < 0 for x < 1.5): monotone per direction.
    float elq = (el >= 0.0) ? el : -4.0 * el;
    float ao = max(p_NightMaskShape.x + p_NightMaskShape.y, 0.2);
    float aw = 1.0 - smoothstep(p_NightMaskShape.x, ao, az);
    float top = sqrt(saturate(1.0 - LanbaiSq(LanbaiSq(az / ao))));
    float k = top * (1.0 - 0.75 * smoothstep(0.7, 0.95, x));
    float f = aw * (1.0 - smoothstep(p_NightMaskShape.z * k, max((p_NightMaskShape.z + p_NightMaskShape.w) * k, p_NightMaskShape.z * k + 1e-3), elq));
    float d = 0.5 * f;
    float w = saturate((x - d) / (0.75 - 0.25 * f));
    return w * w * (3.0 - 2.0 * w);                       // eased: no visible edge where neighbouring directions differ
}

// a fade between a cube sky and the procedural one (dusk 8-ii -> blue hour, 987.06 -> 993.06) goes DOWN the sky: the zenith
// and the nadir turn first, the horizon (where the sun line burns out) last; each direction fades over a quarter of the
// fade (act 8 final review: a uniform cross-fade left the whole rose band half blue at mid-fade, a dusty grey-mauve
// band C* 3-8). proc 0 and 1 (every preset) are untouched.
float LanbaiProcWeight(float3 V, float proc)
{
    [branch] if (proc <= 0.001 || proc >= 0.999)
        return proc;
    float e = saturate(abs(LanbaiElevationDeg(V)) / 50.0);
    float t = saturate(proc * 4.0 - (1.0 - e) * 3.0);
    return t * t * (3.0 - 2.0 * t);
}

float3 LanbaiSkyColour(float3 V)
{
    LanbaiSkyLoadParams();
    float blend = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.x : _Blend;
    float procIn = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.y : _ProcWeight;
    float proc  = LanbaiProcWeight(V, procIn);
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
    // a cube <-> procedural fade: the procedural sky's bands come and go with it, per direction (act 8 final review: the
    // blue hour's deep band faded in uniformly painted blue over the dusk rose = a grey-mauve band at mid-fade). Both
    // gains are lerped by the same t, so bandG / proc is the target gain.
    [branch] if (procIn > 0.001 && procIn < 0.999)
    {
        bandG *= proc / procIn;
        p_Band2Gain *= (1.0 - proc) / (1.0 - procIn);     // band 2 (dusk's rose belt) is the cube sky's: it leaves with it
    }
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
        // the other sky darkens toward the nadir colour with depth (p_OtherTint.a = how far; the depth = p_BelowShape.x):
        // the upper sky's near-white afterglow is not copied as it is into the lower half (art pre-review r0 #1)
        o = LanbaiGeoLerp(o, p_NadirColor.rgb, p_OtherTint.a * LanbaiUpStep(0.0, max(-p_BelowShape.x, 0.1), -LanbaiElevationDeg(V)));
        c = lerp(c, o * p_OtherGain * p_OtherTint.rgb, w);
    }

    c = LanbaiPurpleGuard(c, p_PurpleGuard);

    // 4. night
    [branch] if (night > 0.001)
    {
        float galV = (_Udon_GalaxyGain.w > 0.0) ? LanbaiGalaxyGainAt(_Udon_GalaxyGain, V) : gal;   // the core may lead (act 9)
        float3 n = p_NightColor.rgb + galV * (p_StarFloorAdd.rgb + LanbaiGalaxy(V));
        c = lerp(c, n, LanbaiNightWeight(V, night));
    }

    // 5. moon
    [branch] if (moonG > 0.0)
        c += LanbaiMoonTerm(V, moonG);

    return max(c, 0.0) * exp2(p_Exposure);
}

#endif // LANBAI_SKY_LAYERS_INCLUDED
