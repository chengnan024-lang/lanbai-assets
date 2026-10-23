// =====================================================================================================
//  Lanbai / LanbaiMirror.cginc   v1 (2026-10-22, cloud session 「镜与白」)   蓝白 · 白铜镜的共用数学
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Mirrors/Tools~/compile_check). !!!
//
//  One definition of the mirror's geometry and ornament, shared by Lanbai/BronzeMirror, Lanbai/MirrorStars and
//  Lanbai/MirrorDust, and ported 1:1 to numpy in Mirrors/Tools~/port/mirror_port.py (same names, same numbers).
//  Contract: Mirrors/Docs~/spec_conventions.md.  Every colour is LINEAR.
//
//  Units: object space is the unit-diameter mesh (D = 1, Y up, face on +Y, y = 0 at the face edge r = 0.48);
//  the renderer is scaled uniformly by D = 2 * _RadiusM, so "metres" below = object units * D.
//
//  Include order: UnityCG.cginc -> LanbaiVR.cginc -> (LanbaiFog.cginc) -> this file.
//  Uniforms that the sky also owns (_Udon_GalaxyGain, _Udon_StarGain) are declared here unless the sky's
//  include says it declares them (#define LANBAI_SKY_DECLARES_STARSEA).
// =====================================================================================================
#ifndef LANBAI_MIRROR_INCLUDED
#define LANBAI_MIRROR_INCLUDED

// ---- profile (spec §1) ---------------------------------------------------------------------------------------
#define LM_FACE_R      0.48        // face radius (object units)
#define LM_SAG         0.015       // face sagitta (1.5 % of D)
#define LM_RHO         7.6875      // face sphere radius = (0.48^2 + 0.015^2) / (2 * 0.015)
#define LM_RIM_TOP     0.002
#define LM_BACK_RIM    -0.037
#define LM_BACK_FIELD  -0.015
#define LM_BOSS_PITCH  1.5         // metres (absolute): rim beads
#define LM_BOSS_RAD    0.30        // metres
#define LM_TLV_TILE    40.0        // metres (absolute): one 博局 cell

// ---- globals ---------------------------------------------------------------------------------------------------
#ifndef LANBAI_SKY_DECLARES_STARSEA
float4 _Udon_GalaxyGain;           // x = Milky Way glow gain (ignition g(t), then 1.0 -> 1.8); w > 0 = set
float4 _Udon_StarGain;             // x = star point gain; w > 0 = set
#endif
float4 _Udon_MirrorPlane;          // x = face height at the car (world y), y = line, z = index, w = phase (spec / 给总控)

// ---------------------------------------------------------------------------------------------------------------
// Face (spherical cap) height and normal in object space.  Same numbers as make_mesh.py.
inline float LanbaiMirrorFaceY(float r)
{
    return sqrt(max(LM_RHO * LM_RHO - r * r, 0.0)) - (LM_RHO - LM_SAG);
}
inline float3 LanbaiMirrorFaceNormalOS(float3 posOS)
{
    // sphere centre at (0, LM_SAG - LM_RHO, 0)
    return normalize(float3(posOS.x, posOS.y - (LM_SAG - LM_RHO), posOS.z));
}

// ---- Fresnel (Schlick, coloured F0 for metals) -------------------------------------------------------------------
inline float3 LanbaiSchlick(float3 f0, float cosT)
{
    float m = 1.0 - saturate(cosT);
    float m2 = m * m;
    return f0 + (1.0 - f0) * (m2 * m2 * m);
}

// ---- perceptual smoothness -> cube mip (Unity's own mapping, UNITY_SPECCUBE_LOD_STEPS = 6) ------------------------
inline float LanbaiMirrorMip(float smoothness)
{
    float pr = 1.0 - smoothness;
    return pr * (1.7 - 0.7 * pr) * 6.0;
}

// ---- value noise / FBM (object-anchored, in metres) --------------------------------------------------------------
inline float LanbaiMirrorHash(float3 p)
{
    p = frac(p * 0.1031);
    p += dot(p, p.yzx + 33.33);
    return frac((p.x + p.y) * p.z);
}
inline float LanbaiMirrorNoise(float3 x)
{
    float3 i = floor(x);
    float3 f = frac(x);
    float3 u = f * f * (3.0 - 2.0 * f);
    float n000 = LanbaiMirrorHash(i);
    float n100 = LanbaiMirrorHash(i + float3(1, 0, 0));
    float n010 = LanbaiMirrorHash(i + float3(0, 1, 0));
    float n110 = LanbaiMirrorHash(i + float3(1, 1, 0));
    float n001 = LanbaiMirrorHash(i + float3(0, 0, 1));
    float n101 = LanbaiMirrorHash(i + float3(1, 0, 1));
    float n011 = LanbaiMirrorHash(i + float3(0, 1, 1));
    float n111 = LanbaiMirrorHash(i + float3(1, 1, 1));
    float nx00 = lerp(n000, n100, u.x);
    float nx10 = lerp(n010, n110, u.x);
    float nx01 = lerp(n001, n101, u.x);
    float nx11 = lerp(n011, n111, u.x);
    return lerp(lerp(nx00, nx10, u.y), lerp(nx01, nx11, u.y), u.z);
}
// 3 octaves, periods 8 m / 2.7 m / 0.9 m; returns -1..1 (approximately)
inline float LanbaiMirrorFBM(float3 pM)
{
    float a = LanbaiMirrorNoise(pM * (1.0 / 8.0));
    float b = LanbaiMirrorNoise(pM * (1.0 / 2.7) + 17.1);
    float c = LanbaiMirrorNoise(pM * (1.0 / 0.9) + 41.7);
    return (a * 0.55 + b * 0.30 + c * 0.15) * 2.0 - 1.0;
}

// Dissolve (rim -> centre) and appear (centre -> rim) masks.  rM = distance from the axis in metres, R = radius m.
// Returns signed distance (m) to the front: > 0 kept, < 0 clipped.  amp = breakup amplitude (m).
inline float LanbaiMirrorDissolveSD(float rM, float R, float noise, float progress, float amp)
{
    float key = rM + amp * noise;
    float front = lerp(R + amp, -amp, saturate(progress));
    return front - key;
}
inline float LanbaiMirrorAppearSD(float rM, float R, float noise, float progress, float amp)
{
    float key = rM + amp * noise;
    float front = lerp(-amp, R + amp, saturate(progress));
    return front - key;
}

// ---- rim beads (连珠乳钉) on the face-side rim band ---------------------------------------------------------------
// posOS on the band (r 0.48..0.50).  Returns the bead normal in object space and a coverage 0..1 (AA by footprint).
inline float3 LanbaiMirrorBeadNormalOS(float3 posOS, float D, float footprintM, out float cover)
{
    float r = length(posOS.xz);
    float th = atan2(posOS.z, posOS.x);
    float rc = 0.49 * D;                                         // bead row, metres
    float n = max(round(6.2831853 * rc / LM_BOSS_PITCH), 3.0);   // integer bead count
    float pitch = 6.2831853 * rc / n;
    float s = th * rc;                                           // arc length, metres
    float du = (frac(s / pitch + 0.5) - 0.5) * pitch;
    float dv = r * D - rc;
    float d2 = du * du + dv * dv;
    float a = LM_BOSS_RAD;
    float inside = saturate((a * a - d2) / (0.15 * a * a));      // soft edge
    float h = sqrt(max(a * a - d2, 0.0));
    float3 T = float3(-sin(th), 0.0, cos(th));
    float3 B = float3(cos(th), 0.0, sin(th));
    float3 nb = normalize(du * T + dv * B + max(h, 1e-4) * float3(0, 1, 0));
    // detail fades out once a bead is below ~2 pixels (no sparkle in VR)
    float detail = saturate(1.5 - footprintM / (0.5 * a));
    cover = inside * detail;
    return normalize(lerp(float3(0, 1, 0), nb, cover));
}

// ---- polar ornament bands on the back (absolute periods, spec §3) -------------------------------------------------
// Height 0..1 of the back's outer bands at rM / R, theta.  footprintM fades periodic detail below ~2 px.
inline float LanbaiMirrorSaw(float x)              // triangle teeth 0..1 along x in tooth units, pointing to +v
{
    return 1.0 - abs(frac(x) * 2.0 - 1.0);
}
inline float LanbaiMirrorBandHeight(float rM, float R, float th, float footprintM, out float bandId)
{
    float q = rM / R;
    float h = 0.0;
    bandId = 0.0;
    float arcR = th * rM;                                        // arc length at this radius, metres
    // comb (栉齿) 0.80 .. 0.83, period 0.5 m
    if (q >= 0.80 && q < 0.83)
    {
        float c = abs(frac(arcR / 0.5 + 0.5) - 0.5) * 2.0;       // 0 at line centre
        h = smoothstep(0.45, 0.25, c) * saturate(1.5 - footprintM / 0.2);
        bandId = 2.0;
    }
    // wide flat rim 0.85 .. 1.00: sawtooth | double zigzag | sawtooth, tooth 1.25 m
    else if (q >= 0.85)
    {
        float sub = (q - 0.85) / 0.05;                           // 0..3
        float vloc = frac(sub);                                  // 0..1 across the sub-band
        float x = arcR / 1.25;
        float tooth = LanbaiMirrorSaw(x);
        float d = (floor(sub) == 1.0) ? abs(vloc - (0.25 + 0.5 * tooth)) : (vloc - tooth * 0.85);
        float line = (floor(sub) == 1.0) ? smoothstep(0.10, 0.04, d) + smoothstep(0.10, 0.04, abs(d - 0.22)) : step(d, 0.0);
        h = saturate(line) * saturate(1.5 - footprintM / 0.5);
        bandId = 3.0;
    }
    return h;
}

// ---- reflected sky -----------------------------------------------------------------------------------------------
// sky(dir, mip) = dark + lift * min(gain, 1) + cube(dir, mip) * gain.  The sky session owns these values; the material
// carries copies (_SkyDark, _SkyLift, _SkyCube) so the mirror reflects the same sky the eye sees around it.
inline float LanbaiMirrorGalaxyGain(float matDefault)
{
    return (_Udon_GalaxyGain.w > 0.0) ? _Udon_GalaxyGain.x : matDefault;
}
inline float LanbaiMirrorStarGain(float matDefault)
{
    return (_Udon_StarGain.w > 0.0) ? _Udon_StarGain.x : matDefault;
}

#endif // LANBAI_MIRROR_INCLUDED
