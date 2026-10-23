// =====================================================================================================
//  Lanbai / LanbaiCaustics.cginc   蓝白 · underwater caustics (bible §4.8 '水下焦散', §6·7a, 7c '焦散从下往上')
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//
//  For the CABIN shader (Control's Lanbai/Cabin) and anything else that wants the sea's caustics:
//      #include "Assets/Lanbai/Common/Shaders/LanbaiCaustics.cginc"
//      color += LanbaiCabinCaustics(posWS, normalWS) * albedo;       // linear light, already x E and x depth fade
//  GLOBALS (written by LanbaiAct07Driver; never set = 0 = no caustics):
//    _Udon_Caustics       x = strength 0..1 (depth fade already in: 1 at the surface, 0 at 15 m; 7c 0 -> 1 F8c -> 921.4)
//                         y = direction: +1 light from above (lights up-facing faces), -1 from below (7c: the undersides)
//                         z = caustics clock (s),  w = tiling scale (1 = the bible's 0.6 m / 1.1 m)
//    _Udon_CausticsColor  rgb = linear colour x illuminance of the bright net (S7a: seat caustic #ACD4ED <- fill #9FCBFF @ +1.46)
//    _Udon_CausticsTex    Sea/Textures/Caustics_8x8_2048.png (R8, sRGB OFF, wrap repeat, bilinear, mips on)
//  Projection: world XZ (both directions). Two layers (0.6 m and 1.1 m tiles, different frames and drift, the second
//  rotated 37 deg), MIN of the two (bible), renormalised so the mean is 1. Animation: 64-frame loop at 0.3 Hz,
//  frames blended. World-anchored: identical in both eyes.
// =====================================================================================================
#ifndef LANBAI_CAUSTICS_INCLUDED
#define LANBAI_CAUSTICS_INCLUDED

#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
#ifndef LANBAI_DECL__Udon_Caustics
#define LANBAI_DECL__Udon_Caustics
float4 _Udon_Caustics;            // (not yet in LanbaiGlobals.cginc: Sea/给总控.md)
#endif

#define LANBAI_CAUSTICS_FRAMES 64.0
#define LANBAI_CAUSTICS_GRID 8.0
#define LANBAI_CAUSTICS_HZ 0.3
#define LANBAI_CAUSTICS_MIN_NORM 2.45          // 1 / mean(min(A, B)) of two independent frames (measured: 0.408)

// one frame of the atlas at continuous uv (tiling), decoded to mean-1 irradiance
inline float LanbaiCausticsFrame(float2 uv, float frame)
{
    float f = fmod(frame, LANBAI_CAUSTICS_FRAMES);
    float col = fmod(f, LANBAI_CAUSTICS_GRID);
    float row = floor(f / LANBAI_CAUSTICS_GRID);
    float2 cell = float2(col, LANBAI_CAUSTICS_GRID - 1.0 - row) / LANBAI_CAUSTICS_GRID;
    float2 auv = cell + frac(uv) / LANBAI_CAUSTICS_GRID;
    // gradients of the CONTINUOUS uv: no mip seam where frac() wraps
    float2 dx = ddx(uv) / LANBAI_CAUSTICS_GRID, dy = ddy(uv) / LANBAI_CAUSTICS_GRID;
    float s = tex2Dgrad(_Udon_CausticsTex, auv, dx, dy).r;
    s = min(s, 0.999);
    return 2.0 * log((1.0 + s) / (1.0 - s));                 // 4 atanh(s): HLSL has no atanh
}
inline float LanbaiCausticsLayer(float2 uv, float phase)
{
    float f = phase * LANBAI_CAUSTICS_FRAMES;
    float f0 = floor(f);
    return lerp(LanbaiCausticsFrame(uv, f0), LanbaiCausticsFrame(uv, f0 + 1.0), f - f0);
}

// mean-1 caustic irradiance on the plane through posWS (world XZ projection)
inline float LanbaiCaustics(float3 posWS, float clock, float tileScale)
{
    float sc = tileScale > 0.0 ? tileScale : 1.0;
    float ph = frac(clock * LANBAI_CAUSTICS_HZ);
    float2 a = posWS.xz / (0.6 * sc) + float2(0.013, 0.021) * clock;
    float2 xz = float2(posWS.x * 0.7986 - posWS.z * 0.6018, posWS.x * 0.6018 + posWS.z * 0.7986);     // 37 deg
    float2 b = xz / (1.1 * sc) - float2(0.017, 0.006) * clock;
    float A = LanbaiCausticsLayer(a, ph);
    float B = LanbaiCausticsLayer(b, frac(ph + 0.37));
    return min(A, B) * LANBAI_CAUSTICS_MIN_NORM;
}

// what the cabin adds (linear, before x albedo)
inline float3 LanbaiCabinCaustics(float3 posWS, float3 normalWS)
{
    [branch] if (_Udon_Caustics.x <= 0.0) return float3(0.0, 0.0, 0.0);      // every cabin pixel of acts 1-6, 8-12 stops here
    float facing = _Udon_Caustics.y >= 0.0 ? saturate(normalWS.y) : saturate(-normalWS.y);
    facing = facing * sqrt(facing);                                                 // ^1.5
    return _Udon_CausticsColor.rgb * (_Udon_Caustics.x * facing * LanbaiCaustics(posWS, _Udon_Caustics.z, _Udon_Caustics.w));
}

#endif // LANBAI_CAUSTICS_INCLUDED
