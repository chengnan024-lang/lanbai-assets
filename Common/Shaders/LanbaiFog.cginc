// =====================================================================================================
//  Lanbai / LanbaiFog.cginc   v1.1 (2026-10-23; v1 2026-10-22, cloud sub-session "天空")      蓝白 · 全片的雾
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
//  passes fade to black, not to the horizon), LanbaiApplyFogEx(col, pos, extraAir), LanbaiFogVertex(pos) (per vertex),
//  LanbaiFogDensity().
//
//  How to use (any Built-in vert/frag or surface shader):
//      #pragma multi_compile_fog
//      #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
//      Properties: _FogCap ("Fog Cap", Range(0, 1)) = 1      _FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
//      frag:  col.rgb = LanbaiApplyFog(col.rgb, i.worldPos);
//  Surface shaders: finalcolor:yourFn + nofog, and in yourFn
//      #ifdef UNITY_PASS_FORWARDADD
//          color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);   // per-light additive pass: attenuate only
//      #else
//          color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
//      #endif
//  Do not ALSO use UNITY_APPLY_FOG on the same colour. After the include do NOT declare _FogCap / _FogHeightFalloff /
//  _Udon_Fog* yourself (redefinition, FXC X3003).
//  Distance is RADIAL (eye -> point), Unity's built-in fog uses view depth: same density and colour, but this fog does
//  not change when you turn your head (right for VR); toward the corners of a 90 deg view it is up to ~1.7x the depth.
//
//  Density: global _Udon_Fog (x, w > 0 = set; x = 0 is a real 'no fog') wins, then the legacy _Udon_FogDensity (> 0),
//  else RenderSettings.fogDensity (unity_FogParams).
//  Fog off = density 0 (RenderSettings.fog is never toggled; bible §1.6). The keywords from multi_compile_fog
//  decide: no FOG_* keyword (scene fog off in the editor) = no fog, unless LANBAI_FOG_ALWAYS is defined.
//
//  Material uniforms _FogCap / _FogHeightFalloff and the legacy _Udon_FogDensity are declared here; a shader that
//  declares one itself defines LANBAI_FOG_OWN_CAP / _HEIGHT / _DENSITY (or LANBAI_FOG_OWN_UNIFORMS = all three) before
//  the include and declares it BEFORE it (gate test pitfall 1). Values <= 0 mean "none": cap 1, no height falloff.
//  Height falloff base: _Udon_FogBase.x (drivers write it: ground height, act 4 the cloud top); unset = the eye.
// =====================================================================================================
#ifndef LANBAI_FOG_INCLUDED
#define LANBAI_FOG_INCLUDED

#include "Assets/Lanbai/Common/Shaders/LanbaiSky.cginc"

// one guard per name (a shader that declares one itself defines the guard and declares it BEFORE this include);
// LANBAI_FOG_OWN_UNIFORMS = all three at once
#ifdef LANBAI_FOG_OWN_UNIFORMS
    #define LANBAI_FOG_OWN_CAP
    #define LANBAI_FOG_OWN_HEIGHT
    #define LANBAI_FOG_OWN_DENSITY
#endif
#ifndef LANBAI_FOG_OWN_CAP
float _FogCap;               // 0..1 maximum fog amount (<= 0 = 1, no cap)
#endif
#ifndef LANBAI_FOG_OWN_HEIGHT
float _FogHeightFalloff;     // metres: density x exp(-(y - base) / this) above the base height (<= 0 = uniform)
#endif
#ifndef LANBAI_FOG_OWN_DENSITY
float _Udon_FogDensity;      // (legacy, registered) Exp density per metre; > 0 = set
#endif
#ifndef LANBAI_DECL__Udon_Fog
#define LANBAI_DECL__Udon_Fog
float4 _Udon_Fog;            // x = Exp density per metre, w > 0 = set: x = 0 really means NO fog (fade to 0 without a jump)
#endif
#ifndef LANBAI_DECL__Udon_FogBase
#define LANBAI_DECL__Udon_FogBase
float4 _Udon_FogBase;        // x = base world height of the height falloff, w > 0 = set (else the eye's own height)
#endif

// Exp density (per metre) this frame: _Udon_Fog (w > 0) wins, then the legacy _Udon_FogDensity (> 0), then
// RenderSettings.fogDensity
inline float LanbaiFogDensity()
{
    if (_Udon_Fog.w > 0.0)
        return max(_Udon_Fog.x, 0.0);
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
    float uw = saturate(_Udon_Underwater);
    float tau = max(density, 0.0) * d * lerp(LanbaiHeightFactor(camPosWS.y, posWS.y, base, heightScale), 1.0, uw);
    float f = 1.0 - exp(-tau);
#if defined(FOG_LINEAR)
    // linear mode is not used in Lanbai (bible: Exponential only); approximate with Unity's own factor
    f = 1.0 - saturate(d * unity_FogParams.z + unity_FogParams.w);
#endif
    return lerp(min(f, (cap > 0.0) ? cap : 1.0), f, uw);     // water is uniform: no cap, no height falloff
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

// the same with an extra 'air' term added to the fog colour (act 4: the gate's moon aureole / wound air, so a cloud
// card next to the moon fogs like the tentacles do: LanbaiApplyFogEx(c, p, LanbaiGateFogColour(...) - LanbaiBand(V)))
float3 LanbaiApplyFogEx(float3 colLinear, float3 posWS, float3 extraAir)
{
#if defined(FOG_EXP) || defined(FOG_EXP2) || defined(FOG_LINEAR) || defined(LANBAI_FOG_ALWAYS)
    float3 eye = LanbaiCentreEyePos();
    float f = LanbaiFogAmount(posWS, eye);
    float3 V = posWS - eye;
    V = (dot(V, V) > 1e-8) ? normalize(V) : float3(0.0, 0.0, 1.0);
    return lerp(colLinear, LanbaiHorizon(V) + extraAir, f);
#else
    return colLinear;
#endif
}

// per-vertex version for particles / cards: rgb = fog colour, a = amount; in the fragment col = lerp(col, f.rgb, f.a)
// (additive: col *= 1 - f.a). ~200 ALU and ~10 transcendentals per call: per vertex it is free.
float4 LanbaiFogVertex(float3 posWS)
{
#if defined(FOG_EXP) || defined(FOG_EXP2) || defined(FOG_LINEAR) || defined(LANBAI_FOG_ALWAYS)
    float3 eye = LanbaiCentreEyePos();
    float3 V = posWS - eye;
    V = (dot(V, V) > 1e-8) ? normalize(V) : float3(0.0, 0.0, 1.0);
    return float4(LanbaiHorizon(V), LanbaiFogAmount(posWS, eye));
#else
    return float4(0.0, 0.0, 0.0, 0.0);
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
