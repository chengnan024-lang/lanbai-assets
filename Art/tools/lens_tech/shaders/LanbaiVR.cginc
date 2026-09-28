// =====================================================================================================
//  Lanbai / LanbaiVR.cginc      蓝白 · shared VR helpers for every hand-written Lanbai shader
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). The implementer compiles and checks it. !!!
//
//  1. STEREO. VRChat PC renders VR with Single Pass Stereo Instanced (verify in your SDK's release notes;
//     write for it regardless: the macros compile to nothing in mono / multi-pass). Every vert/frag shader must:
//       appdata:  UNITY_VERTEX_INPUT_INSTANCE_ID
//       v2f:      UNITY_VERTEX_OUTPUT_STEREO
//       vert:     UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_OUTPUT(v2f, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
//       frag:     UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   (only needed if the fragment reads
//                 _CameraDepthTexture / a screen-space texture: declare it with UNITY_DECLARE_DEPTH_TEXTURE
//                 and sample with SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(screenPos)))
//     Symptom of a missing macro: the object renders in ONE EYE ONLY. Test in a headset, not only ClientSim.
//     Surface shaders (#pragma surface) get all of this for free.
//  2. Everything here is world- or object-anchored: nothing screen-locked (screen-locked patterns fuse at the
//     screen plane in stereo and read as dirt on the lenses).
// =====================================================================================================
#ifndef LANBAI_VR_INCLUDED
#define LANBAI_VR_INCLUDED

#include "UnityCG.cginc"

// ---------------------------------------------------------------------------------------------------
// Angular size of one pixel (radians) for the eye being rendered. Works in mono, SPS and SPS-I because
// UNITY_MATRIX_P and _ScreenParams are per eye.
inline float LanbaiPixelAngle()
{
    return 2.0 / (abs(UNITY_MATRIX_P[1][1]) * _ScreenParams.y);
}

// ---------------------------------------------------------------------------------------------------
// Geometric specular anti-aliasing (Kaplanyan & Hoffman 2016 / Tokuyoshi 2019, simplified).
// Thin wet highlights on far tentacles, chrome rails and wave normals otherwise crawl in VR: MSAA does not
// fix shading aliasing. Call with the FINAL (normal-mapped) world normal. Returns a (lower) smoothness.
inline half LanbaiSpecAA(float3 worldNormal, half smoothness)
{
    float3 dndu = ddx(worldNormal);
    float3 dndv = ddy(worldNormal);
    float variance = 0.25 * (dot(dndu, dndu) + dot(dndv, dndv));
    float kernelRoughness2 = min(2.0 * variance, 0.18);           // sigma^2 in GGX alpha^2 units, clamped
    float r = 1.0 - smoothness;                                   // perceptual roughness
    float a2 = saturate(r * r * r * r + kernelRoughness2);        // alpha^2 = r^4
    return (half)(1.0 - sqrt(sqrt(a2)));
}

// ---------------------------------------------------------------------------------------------------
// Minimum on-screen width for thin geometry (tentacle tips, tear fibres, wires, stanchions far away).
// Sub-pixel geometry breaks into dashes and sparkles in VR. Inflate the radius to >= minPx pixels and
// return the coverage factor (true radius / drawn radius) to scale emission / rim / alpha so the thread
// keeps its energy instead of getting brighter as it gets fatter.
//   radiusWorld : true radius of this vertex's ring in metres
//   distWorld   : distance from the camera in metres
inline float LanbaiMinRadius(float distWorld, float minPx)
{
    return 0.5 * minPx * LanbaiPixelAngle() * distWorld;
}
inline float LanbaiInflate(float radiusWorld, float distWorld, float minPx, out float coverage)
{
    float rMin = LanbaiMinRadius(distWorld, minPx);
    float rDraw = max(radiusWorld, rMin);
    coverage = radiusWorld / max(rDraw, 1e-5);
    return rDraw - radiusWorld;                                   // push along the normal by this much
}

// ---------------------------------------------------------------------------------------------------
// Direction-anchored dither for skies and large dark gradients. Same value in both eyes for a direction
// at infinity (stereo-consistent, unlike screen-space grain). Triangular PDF, amplitude in display LSBs.
// Apply before the colour leaves the shader: col += LanbaiSkyDither(dir) * col_lsb_scale.
inline float LanbaiHash13(float3 p)
{
    p = frac(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return frac((p.x + p.y) * p.z);
}
inline float LanbaiSkyDither(float3 dirWS)
{
    // ~0.04 deg cells: finer than a VR pixel (0.05-0.07 deg), so it reads as fine noise, not blocks
    float3 q = floor(normalize(dirWS) * 1400.0);
    return LanbaiHash13(q) + LanbaiHash13(q + 17.0) - 1.0;       // -1..1, triangular
}
// Add ~1.5 LSB of 8-bit display noise to a LINEAR colour c (the tonemapper is ~identity in the darks).
inline float3 LanbaiDitherLinear(float3 c, float3 dirWS)
{
    float n = LanbaiSkyDither(dirWS) * (1.5 / 255.0);
    float3 s = LinearToGammaSpace(max(c, 0));
    return GammaToLinearSpace(max(s + n, 0));
}

// ---------------------------------------------------------------------------------------------------
// PPv2 Neutral tonemapper inverse (from lens_cine.md 3.4): lets display-referred cards display as authored.
inline float3 InverseNeutralPPv2(float3 y)
{
    const float a = 0.2, b = 0.29, c = 0.24, d = 0.272, e = 0.02, f = 0.3, whiteLevel = 5.3;
    float ws = 1.0 / (((whiteLevel * (a * whiteLevel + c * b) + d * e) / (whiteLevel * (a * whiteLevel + b) + d * f)) - e / f);
    y = min(y, 0.97);
    float3 v = y / ws + e / f;
    float3 A = a * v - a, B = b * v - c * b, C = d * f * v - d * e;
    float3 u = (-B - sqrt(max(B * B - 4 * A * C, 0))) / (2 * A);
    return max(u / ws, 0);
}

// ---------------------------------------------------------------------------------------------------
// Fade a card by how edge-on it is (god-ray cards, beam slabs, wisps): stops flat cards turning into
// hard lines when the head moves past them.
inline half LanbaiEdgeOnFade(float3 normalWS, float3 posWS, half power)
{
    float3 V = normalize(_WorldSpaceCameraPos - posWS);
    return (half)pow(saturate(abs(dot(normalize(normalWS), V)) * 1.4), power);
}

// Near-eye fade: nothing (particles, cards, glows) may sit inside the stereo-uncomfortable zone.
inline half LanbaiNearFade(float3 posWS, float nearM, float farM)
{
    float d = distance(posWS, _WorldSpaceCameraPos);
    return (half)saturate((d - nearM) / max(farM - nearM, 1e-3));
}

#endif
