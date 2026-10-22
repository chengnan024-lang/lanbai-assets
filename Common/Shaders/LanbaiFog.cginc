// =====================================================================================================
//  Lanbai / LanbaiFog.cginc   v1 (2026-10-22, cloud sub-session "天空")      蓝白 · 全片的雾
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Sky/Tools~/compile_check). !!!
//
//  ART BIBLE v2.1 §1.6: Exponential fog only; fog colour = the sky's horizon colour in that direction
//  (LanbaiHorizon, LanbaiSky.cginc); _FogCap and a height falloff so far giants never become ghosts brighter than
//  the sky; sky objects (_FogMode 2) do not call this.
//
//  MINIMUM INTERFACE (CONTROL_总控.md §4; names and parameters are fixed):
//      float3 LanbaiHorizon(float3 dirWS);                      // LanbaiSky.cginc
//      float  LanbaiFogAmount(float3 posWS, float3 camPosWS);   // 0..1, with _FogCap and _FogHeightFalloff
//      float3 LanbaiApplyFog(float3 colLinear, float3 posWS);   // uses LanbaiCentreEyePos()
//  Extras: LanbaiFogAmountEx(pos, cam, density, cap, heightScale), LanbaiApplyFogAdditive (additive / premultiplied
//  passes fade to black, not to the horizon), LanbaiFogDensity().
//
//  How to use (any Built-in vert/frag or surface shader):
//      #pragma multi_compile_fog
//      #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
//      Properties: _FogCap ("Fog Cap", Range(0, 1)) = 1      _FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
//      frag:  col.rgb = LanbaiApplyFog(col.rgb, i.worldPos);   (surface shaders: finalcolor:yourFn + nofog)
//  Do not ALSO use UNITY_APPLY_FOG on the same colour.
//
//  Density: global _Udon_FogDensity (> 0) wins, else RenderSettings.fogDensity (unity_FogParams), so with no Udon
//  writes this fog equals Unity's own Exp fog in amount; with no Udon colour writes it equals it in colour too.
//  Fog off = density 0 (RenderSettings.fog is never toggled; bible §1.6). The keywords from multi_compile_fog
//  decide: no FOG_* keyword (scene fog off in the editor) = no fog, unless LANBAI_FOG_ALWAYS is defined.
//
//  Material uniforms _FogCap / _FogHeightFalloff are declared here; a shader that declares them itself defines
//  LANBAI_FOG_OWN_UNIFORMS before the include and must declare them BEFORE it (gate test pitfall 1).
//  Values <= 0 mean "none" (a material without the properties reads 0): cap 1, no height falloff.
// =====================================================================================================
#ifndef LANBAI_FOG_INCLUDED
#define LANBAI_FOG_INCLUDED

#include "Assets/Lanbai/Common/Shaders/LanbaiSky.cginc"

#ifndef LANBAI_FOG_OWN_UNIFORMS
float _FogCap;               // 0..1 maximum fog amount (<= 0 = 1, no cap)
float _FogHeightFalloff;     // metres: density x exp(-(y - base) / this) above the base height (<= 0 = uniform)
float _Udon_FogDensity;      // Exp density per metre; > 0 = set (else RenderSettings)
#endif
float4 _Udon_FogBase;        // x = base world height of the height falloff, w > 0 = set (else the eye's own height)

// Exp density (per metre) this frame
inline float LanbaiFogDensity()
{
    if (_Udon_FogDensity > 0.0)
        return _Udon_FogDensity;
#if defined(FOG_EXP2)
    return unity_FogParams.x * 0.8325546;           // x = density / sqrt(ln 2)
#else
    return unity_FogParams.y * 0.6931472;           // y = density / ln 2 (FOG_EXP)
#endif
}

// optical-depth factor of the height falloff along the segment cam -> pos: (1/D) x integral of
// exp(-max(y - base, 0) / H) ds. Exact for the clamped exponential (constant below the base).
float LanbaiHeightFactor(float yc, float yp, float base, float H)
{
    if (H <= 0.0)
        return 1.0;
    float a = (yc - base) / H;
    float b = (yp - base) / H;
    float lo = min(a, b), hi = max(a, b);
    if (hi <= 0.0)
        return 1.0;                                  // the whole segment is below the base
    float span = hi - lo;
    if (span < 1e-4)
        return exp(-max(hi, 0.0));                   // horizontal segment
    float l0 = max(lo, 0.0);                         // part above the base: integral of e^-x from l0 to hi
    float above = exp(-l0) - exp(-hi);
    float belowPart = max(-lo, 0.0);                 // part below the base: constant 1
    return (above + belowPart) / span;
}

// fog amount with every parameter explicit (heightScale <= 0 = uniform; cap <= 0 = 1)
float LanbaiFogAmountEx(float3 posWS, float3 camPosWS, float density, float cap, float heightScale)
{
    float d = distance(posWS, camPosWS);
    float base = (_Udon_FogBase.w > 0.0) ? _Udon_FogBase.x : camPosWS.y;
    float tau = max(density, 0.0) * d * LanbaiHeightFactor(camPosWS.y, posWS.y, base, heightScale);
    float f = 1.0 - exp(-tau);
#if defined(FOG_LINEAR)
    // linear mode is not used in Lanbai (bible: Exponential only); approximate with Unity's own factor
    f = 1.0 - saturate(d * unity_FogParams.z + unity_FogParams.w);
#endif
    return min(f, (cap > 0.0) ? cap : 1.0);
}

float LanbaiFogAmount(float3 posWS, float3 camPosWS)
{
    return LanbaiFogAmountEx(posWS, camPosWS, LanbaiFogDensity(), _FogCap, _FogHeightFalloff);
}

float3 LanbaiApplyFog(float3 colLinear, float3 posWS)
{
#if defined(FOG_EXP) || defined(FOG_EXP2) || defined(FOG_LINEAR) || defined(LANBAI_FOG_ALWAYS)
    float3 eye = LanbaiCentreEyePos();
    float f = LanbaiFogAmount(posWS, eye);
    float3 V = posWS - eye;
    V = (dot(V, V) > 1e-8) ? normalize(V) : float3(0.0, 0.0, 1.0);
    return lerp(colLinear, LanbaiHorizon(V), f);
#else
    return colLinear;
#endif
}

// additive / premultiplied-alpha passes: fog only removes their light (the fog colour is already behind them)
float3 LanbaiApplyFogAdditive(float3 colLinear, float3 posWS)
{
#if defined(FOG_EXP) || defined(FOG_EXP2) || defined(FOG_LINEAR) || defined(LANBAI_FOG_ALWAYS)
    return colLinear * (1.0 - LanbaiFogAmount(posWS, LanbaiCentreEyePos()));
#else
    return colLinear;
#endif
}

#endif // LANBAI_FOG_INCLUDED
