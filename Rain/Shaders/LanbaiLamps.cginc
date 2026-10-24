// =====================================================================================================
//  Lanbai / LanbaiLamps.cginc     蓝白 · the 8 analytic lamps (bible §1.6 "解析 GGX 灯 _Udon_Lamp0..7")
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      The implementer compiles it in Unity 2022.3 and checks it in a headset. !!!
//
//  WHAT: the wet road's long light bands, the lamp glints inside every raindrop, and the rain streaks that are
//  "lit only where lit" all come from these 8 lamps, evaluated in the shader. No real-time light is needed for
//  them (bible §1.6: no Mixed lights; the baked lamp gives the diffuse, these give the specular).
//
//  GLOBALS (set by Runtime/LanbaiLamps.cs through VRCShader.SetGlobalVector; names MUST start with _Udon):
//    _Udon_Lamp{i}       xyz = world position of the source centre (m)
//                        w   = intensity I in Unity light units: a surface facing the lamp at distance d
//                              receives E = I / d^2 (same units as a Unity light colour x intensity^2.2,
//                              i.e. the bible's "E"). Stop tube: E 1.0 on the road 3.9 m below -> I ~ 15.
//                              w <= 0 : lamp off (skipped).
//    _Udon_LampColor{i}  rgb = linear colour (0..1), a = source radius (m) (widens the GGX lobe, Karis 2013)
//    _Udon_LampAxis{i}   xyz = half-length vector of a line source (tube: 0.6 m along the tube), 0 for points
//    _Udon_LampDir{i}    xyz = main emission direction (unit), w = cos of the cone half-angle; -1 = omni.
//                              Trough reflector over the stop tube: (0,-1,0), w = 0.05 (lower hemisphere).
//                              Headlight: forward-down, w = cos(17.5 deg) = 0.954.
//  Anything never set reads 0 -> lamp off. Nothing here is per-material.
// =====================================================================================================
#ifndef LANBAI_LAMPS_INCLUDED
#define LANBAI_LAMPS_INCLUDED

#include "UnityCG.cginc"

#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"   // _Udon_Lamp0..7, _Udon_LampColor0..7, _Udon_LampAxis0..7, _Udon_LampDir0..7 (declared once there; D-34 #7)

// cone / reflector term for a direction leaving the lamp (unit, lamp -> point)
inline float LanbaiLampCone(float4 dirW, float3 lampToPoint)
{
    if (dirW.w <= -0.999) return 1.0;
    float c = dot(lampToPoint, dirW.xyz);
    return smoothstep(dirW.w - 0.08, dirW.w + 0.08, c);
}

// closest point of the lamp's segment to a point (for irradiance / particles), relative to P
inline float3 LanbaiLampClosest(float4 lamp, float4 axis, float3 P)
{
    float3 a = lamp.xyz - axis.xyz - P;
    float3 seg = 2.0 * axis.xyz;
    float t = saturate(-dot(a, seg) / max(dot(seg, seg), 1e-6));
    return a + seg * t;
}

// ---------------------------------------------------------------------------------------------------
// GGX specular of one lamp, Unity Standard conventions (specular = V * D * PI * F * E * NdotL).
//   P world position, N world normal (unit), V unit vector to the eye, alpha = perceptualRoughness^2,
//   F0 specular colour at normal incidence.
//   boost / peak (v2, still water): the reflection is multiplied by min(boost, peak / its own mirror-core value), so a
//   bright lamp's image keeps its SHAPE (no fat clipped blob) with its core at 'peak', dim lamps get the full boost,
//   and no ripple facet can ever exceed the still image's core. boost 1, peak 1e9 = plain physics.
inline float3 LanbaiLampSpecOne(float4 lamp, float4 colR, float4 axis, float4 dirW,
                                float3 P, float3 N, float3 V, float3 R, float alpha, float3 F0, float boost, float peak)
{
    if (lamp.w <= 0.0) return 0;
    float3 toC = lamp.xyz - P;
    float dist2 = max(dot(toC, toC), 1e-4);

    // representative point on a line source (Karis 2013): closest point of the segment to the reflection ray
    float3 Lvec = toC;
    float3 seg = 2.0 * axis.xyz;
    float segLen2 = dot(seg, seg);
    float lineNorm = 1.0;
    if (segLen2 > 1e-6)
    {
        float3 L0 = toC - axis.xyz;
        float RoS = dot(R, seg);
        float t = saturate((dot(R, L0) * RoS - dot(L0, seg)) / max(segLen2 - RoS * RoS, 1e-6));
        Lvec = L0 + seg * t;
        // energy conservation for the stretched lobe (Karis: alpha / saturate(alpha + halfLength / (2 d)))
        lineNorm = alpha / saturate(alpha + 0.5 * sqrt(segLen2) / (2.0 * sqrt(dist2)));
    }
    // sphere widening
    float radius = colR.a;
    float3 centerToRay = dot(Lvec, R) * R - Lvec;
    float3 closest = Lvec + centerToRay * saturate(radius / max(length(centerToRay), 1e-5));
    float3 L = normalize(closest);
    float dL = max(length(Lvec), 1e-3);
    float aPrime = saturate(alpha + radius / (2.0 * dL));
    float sphereNorm = (alpha / aPrime) * (alpha / aPrime);

    float NdotL = saturate(dot(N, L));
    if (NdotL <= 0.0) return 0;
    float NdotV = max(dot(N, V), 1e-4);
    float3 H = normalize(L + V);
    float NdotH = saturate(dot(N, H));
    float VdotH = saturate(dot(V, H));
    float a2 = alpha * alpha;
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    // (v2) the epsilon must stay far below (pi a2^2): with Unity's usual 1e-7 a still puddle (alpha 0.002, a2 4e-6)
    // had its peak capped ~2000x too low and the tube's reflection vanished from smooth water.
    float D = a2 / (UNITY_PI * d * d + 1e-14);
    float Vis = 0.5 / (NdotL * (NdotV * (1.0 - alpha) + alpha) + NdotV * (NdotL * (1.0 - alpha) + alpha) + 1e-5);
    float3 F = F0 + (1.0 - F0) * pow(1.0 - VdotH, 5.0);
    float E = lamp.w / dist2 * LanbaiLampCone(dirW, normalize(-toC));
    float common = E * NdotL * Vis * UNITY_PI * sphereNorm * lineNorm;
    float3 Fc = F0 + (1.0 - F0) * pow(1.0 - NdotV, 5.0);
    float3 core = colR.rgb * (common / (UNITY_PI * a2)) * Fc;               // the same lamp seen in a perfect mirror
    float g = min(boost, peak / max(max(core.r, max(core.g, core.b)), 1e-6));
    return colR.rgb * (common * D * g) * F;
}

// sum of the 8 lamps. smoothness is Unity's (1 - perceptual roughness). boost / peak: see LanbaiLampSpecOne.
inline float3 LanbaiLampSpecularCapped(float3 P, float3 N, float3 V, float smoothness, float3 F0, float boost, float peak)
{
    float pr = 1.0 - smoothness;
    float alpha = max(pr * pr, 0.002);
    float3 R = reflect(-V, N);
    float3 s = 0;
    s += LanbaiLampSpecOne(_Udon_Lamp0, _Udon_LampColor0, _Udon_LampAxis0, _Udon_LampDir0, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp1, _Udon_LampColor1, _Udon_LampAxis1, _Udon_LampDir1, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp2, _Udon_LampColor2, _Udon_LampAxis2, _Udon_LampDir2, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp3, _Udon_LampColor3, _Udon_LampAxis3, _Udon_LampDir3, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp4, _Udon_LampColor4, _Udon_LampAxis4, _Udon_LampDir4, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp5, _Udon_LampColor5, _Udon_LampAxis5, _Udon_LampDir5, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp6, _Udon_LampColor6, _Udon_LampAxis6, _Udon_LampDir6, P, N, V, R, alpha, F0, boost, peak);
    s += LanbaiLampSpecOne(_Udon_Lamp7, _Udon_LampColor7, _Udon_LampAxis7, _Udon_LampDir7, P, N, V, R, alpha, F0, boost, peak);
    return s;
}
inline float3 LanbaiLampSpecular(float3 P, float3 N, float3 V, float smoothness, float3 F0)
{
    return LanbaiLampSpecularCapped(P, N, V, smoothness, F0, 1.0, 1e9);
}

// ---------------------------------------------------------------------------------------------------
// Soft cap of a lamp's reflection (keeps the hue; max channel approaches 'peak'). Still water must show the tube's
// image at the bible's screen target (§6·12 '静水里的灯影 #DDE8EA' = 1.6 x the tube colour, max channel ~1.45
// scene-linear under S12), and rippled water must never flash BRIGHTER than the still image: every facet is capped
// by the same value. tanh argument clamped (exp overflow -> NaN on some GPUs).
inline float3 LanbaiSoftCap(float3 c, float peak)
{
    float m = max(max(c.r, c.g), c.b);
    return m > 1e-6 ? c * (peak * tanh(min(m / peak, 8.0)) / m) : c;
}

// ---------------------------------------------------------------------------------------------------
// Light scattered by rain (streaks, splashes, falling drips) toward the eye from one lamp.
// Raindrops scatter strongly FORWARD: rain between you and the lamp glows, rain beside it is faint, rain
// behind you is nearly invisible (Garg & Nayar). phase(cos) with cos = dot(lamp->drop, drop->eye).
inline float LanbaiRainPhase(float c)
{
    float f = saturate(0.5 + 0.5 * c);
    return 0.30 + 2.6 * pow(f, 6.0) + 6.0 * pow(f, 40.0);
}
inline float3 LanbaiRainLightOne(float4 lamp, float4 colR, float4 axis, float4 dirW, float3 P, float3 toEye)
{
    if (lamp.w <= 0.0) return 0;
    float3 l = LanbaiLampClosest(lamp, axis, P);           // P -> nearest point of the source
    float d2 = max(dot(l, l), 0.09);                        // clamp at 0.3 m: no singularity at the tube
    float3 lampToP = normalize(-l);
    float cone = LanbaiLampCone(dirW, normalize(P - lamp.xyz));
    return colR.rgb * (lamp.w / d2 * cone * LanbaiRainPhase(dot(lampToP, toEye)));
}
inline float3 LanbaiRainLight(float3 P, float3 toEye)
{
    float3 s = 0;
    s += LanbaiRainLightOne(_Udon_Lamp0, _Udon_LampColor0, _Udon_LampAxis0, _Udon_LampDir0, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp1, _Udon_LampColor1, _Udon_LampAxis1, _Udon_LampDir1, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp2, _Udon_LampColor2, _Udon_LampAxis2, _Udon_LampDir2, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp3, _Udon_LampColor3, _Udon_LampAxis3, _Udon_LampDir3, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp4, _Udon_LampColor4, _Udon_LampAxis4, _Udon_LampDir4, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp5, _Udon_LampColor5, _Udon_LampAxis5, _Udon_LampDir5, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp6, _Udon_LampColor6, _Udon_LampAxis6, _Udon_LampDir6, P, toEye);
    s += LanbaiRainLightOne(_Udon_Lamp7, _Udon_LampColor7, _Udon_LampAxis7, _Udon_LampDir7, P, toEye);
    return s;
}

// ---------------------------------------------------------------------------------------------------
// A small bright image of each lamp seen THROUGH a drop (the refracted view direction t leaving the drop):
// "夜里倒立的小灯点" (bible §4.6). Wide normalised lobe so it survives MSAA and head motion.
inline float3 LanbaiLampGlintOne(float4 lamp, float4 colR, float4 axis, float4 dirW, float3 P, float3 t, float lobe)
{
    if (lamp.w <= 0.0) return 0;
    float3 toC = lamp.xyz - P;
    float d2 = max(dot(toC, toC), 0.04);
    // nearest point of the line source to the ray t (so a tube reads as a short bar, not a dot)
    float3 Lvec = toC;
    float3 seg = 2.0 * axis.xyz;
    float segLen2 = dot(seg, seg);
    if (segLen2 > 1e-6)
    {
        float3 L0 = toC - axis.xyz;
        float ToS = dot(t, seg);
        float s = saturate((dot(t, L0) * ToS - dot(L0, seg)) / max(segLen2 - ToS * ToS, 1e-6));
        Lvec = L0 + seg * s;
    }
    float c = saturate(dot(t, normalize(Lvec)));
    float cone = LanbaiLampCone(dirW, normalize(-toC));
    return colR.rgb * (lamp.w / d2 * cone * (lobe + 2.0) / (2.0 * UNITY_PI) * pow(c, lobe));
}
inline float3 LanbaiLampGlints(float3 P, float3 t, float lobe)
{
    float3 s = 0;
    s += LanbaiLampGlintOne(_Udon_Lamp0, _Udon_LampColor0, _Udon_LampAxis0, _Udon_LampDir0, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp1, _Udon_LampColor1, _Udon_LampAxis1, _Udon_LampDir1, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp2, _Udon_LampColor2, _Udon_LampAxis2, _Udon_LampDir2, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp3, _Udon_LampColor3, _Udon_LampAxis3, _Udon_LampDir3, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp4, _Udon_LampColor4, _Udon_LampAxis4, _Udon_LampDir4, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp5, _Udon_LampColor5, _Udon_LampAxis5, _Udon_LampDir5, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp6, _Udon_LampColor6, _Udon_LampAxis6, _Udon_LampDir6, P, t, lobe);
    s += LanbaiLampGlintOne(_Udon_Lamp7, _Udon_LampColor7, _Udon_LampAxis7, _Udon_LampDir7, P, t, lobe);
    return s;
}

#endif
