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
//  No _Udon_ declarations here: they all live in Common/Shaders/LanbaiGlobals.cginc (ruling D-29).
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

// ---- globals: declared ONCE in Common/Shaders/LanbaiGlobals.cginc (ruling D-29); act 9 sky helpers from LanbaiSky.cginc
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
#include "Assets/Lanbai/Common/Shaders/LanbaiSky.cginc"

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

// ---- the breakup band behind the dissolve front (终审 M-3) ----------------------------------------------------
// Voronoi chunks in the mirror's plane (metres / cell size): F1, F2 (distances to the nearest two cell points) and the
// nearest cell's random id 0..1. Behind the front (s = 0 at the front .. 1 a band width inside) the cracks between chunks
// open first, then chunks drop out one by one; each chunk's crack edge glows on its own.
inline float2 LanbaiMirrorHash2(float2 p)
{
    float3 q = frac(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    q += dot(q, q.yzx + 33.33);
    return frac((q.xx + q.yz) * q.zy);
}
inline float3 LanbaiMirrorCells(float2 x)
{
    float2 i = floor(x), f = frac(x);
    float F1 = 8.0, F2 = 8.0, id = 0.0;
    for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++)
        {
            float2 g = float2(dx, dy);
            float2 o = LanbaiMirrorHash2(i + g);
            float d = length(g + o - f);
            if (d < F1) { F2 = F1; F1 = d; id = frac(o.x * 7.31 + o.y * 3.17); }
            else if (d < F2) { F2 = d; }
        }
    return float3(F1, F2, id);
}
// sdFront: the smooth front's signed distance (m, > 0 kept); xzM: position in the plane (m); cellM: chunk size (m);
// bandM: band width (m). Returns the new signed distance (< 0 = clipped) and the chunk-edge glow.
inline float LanbaiMirrorBreakup(float sdFront, float2 xzM, float cellM, float bandM, out float glow)
{
    glow = 0.0;
    if (sdFront <= 0.0 || sdFront >= bandM)
        return sdFront;
    float s = sdFront / bandM;                                   // 0 at the front .. 1 inside
    float3 c = LanbaiMirrorCells(xzM / cellM);
    float edge = (c.y - c.x) * 0.5;                              // distance to the crack, in cells
    float gap = 0.18 * (1.0 - s) * (1.0 - s);                    // cracks open toward the front
    float gone = c.z - (s * 1.3 - 0.1);                          // > 0: this chunk has already dropped out
    float shrink = 0.6 * saturate((gone + 0.25) / 0.25);        // a chunk shrinks to its centre before it drops: no pop (flash m9)
    float keep = min(edge - gap - shrink, -gone);
    glow = (1.0 - s) * saturate(1.0 - (edge - gap - shrink) / 0.06) * step(0.0, keep);
    return keep >= 0.0 ? sdFront : -1.0;
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
// Polar bands as strings of beads (review r3 #1): each band is split into rows of about rowTarget metres; every row
// uses ONE radius (its centre) and an INTEGER number of cells, so a cell is not sheared across the row and the ring
// closes on itself at theta = +-pi (no seam).  period = absolute cell length (m), or aspect * row height if aspect > 0;
// the cell count is a multiple of 'multiple' (35 for the inscription: the text closes on itself).
struct LanbaiBandCell
{
    float s;        // cell coordinate along the ring: floor = cell index, frac = position in the cell
    float v;        // 0 at the row's inner edge .. 1 at its outer edge
    float row;      // row index from the inside
    float rows;
    float rowH;     // metres
    float n;        // cells in this row
};
inline LanbaiBandCell LanbaiMirrorBandCell(float rM, float th, float r0, float r1, float rowTarget, float period,
                                           float aspect, float multiple)
{
    LanbaiBandCell c;
    float w = r1 - r0;
    c.rows = max(floor(w / rowTarget), 1.0);
    c.rowH = w / c.rows;
    float y = (rM - r0) / c.rowH;
    c.row = clamp(floor(y), 0.0, c.rows - 1.0);
    c.v = saturate(y - c.row);
    float rRow = r0 + (c.row + 0.5) * c.rowH;
    float p = (aspect > 0.0) ? aspect * c.rowH : period;
    c.n = multiple * max(round(6.2831853 * rRow / p / multiple), 1.0);
    c.s = (th + 3.14159265) * (c.n / 6.2831853);
    return c;
}
// screen derivatives of theta without the 2 pi jump at the seam (for tex2Dgrad: F9)
inline float2 LanbaiWrapDTheta(float th)
{
    float2 d = float2(ddx(th), ddy(th));
    return d - 6.2831853 * round(d / 6.2831853);
}

#define LM_CLOUD_ASPECT 5.246      // the rim cloud strip (2 units of 1995.301 band): tile length / band height (make_textures.py prints it)

// Height 0..1 of the back's outer bands at rM / R, theta.  footprintM fades periodic detail below ~2 px.
// cloudTex: T_MirrorRimCloud (Repeat in u), two units of the real 流云纹 band unwrapped from 1995.301.
inline float LanbaiMirrorBandHeight(float rM, float R, float th, float2 dth, float2 drM, float footprintM,
                                    sampler2D cloudTex, out float bandId)
{
    float q = rM / R;
    float h = 0.0;
    bandId = 0.0;
    // comb (栉齿) 0.80 .. 0.83, a line every 0.5 m, rows of ~1 m
    if (q >= 0.80 && q < 0.83)
    {
        LanbaiBandCell b = LanbaiMirrorBandCell(rM, th, 0.80 * R, 0.83 * R, 1.0, 0.5, 0.0, 1.0);
        float c = abs(frac(b.s + 0.5) - 0.5) * 2.0;             // 0 at line centre
        float gap = (b.rows > 1.0) ? smoothstep(0.0, 0.08, b.v) * smoothstep(1.0, 0.92, b.v) : 1.0;
        h = smoothstep(0.45, 0.25, c) * gap * saturate(1.5 - footprintM / 0.2);
        bandId = 2.0;
    }
    // wide flat rim 0.85 .. 1.00 (as Cleveland 1995.301): sawtooth 0.855 .. 0.89 (tooth 1.25 m, rows of ~1.1 m),
    // a fine ring, then the 流云纹 band 0.905 .. 0.975 (the real one, rows of ~1.4 m), plain outer lip
    else if (q >= 0.85)
    {
        float hh = 0.0;
        if (q >= 0.855 && q < 0.89)
        {
            LanbaiBandCell b = LanbaiMirrorBandCell(rM, th, 0.855 * R, 0.89 * R, 1.1, 1.25, 0.0, 1.0);
            hh = step(b.v, LanbaiMirrorSaw(b.s) * 0.95) * saturate(1.5 - footprintM / 0.4);
        }
        else if (q >= 0.895 && q < 0.90)
        {
            hh = 1.0;
        }
        else if (q >= 0.905 && q < 0.975)
        {
            LanbaiBandCell b = LanbaiMirrorBandCell(rM, th, 0.905 * R, 0.975 * R, 1.4, 0.0, LM_CLOUD_ASPECT, 1.0);
            float k = b.n / 6.2831853;
            float2 uv = float2(frac(b.s), b.v);
            hh = tex2Dgrad(cloudTex, uv, float2(dth.x * k, drM.x / b.rowH), float2(dth.y * k, drM.y / b.rowH)).r;
            hh *= saturate(1.5 - footprintM / 0.3);
        }
        h = hh;
        bandId = 3.0;
    }
    return h;
}

// ---- reflected sky (act 9) -------------------------------------------------------------------------------------
// The SAME sky the eye sees around the mirror (README_Act09 §4): star floor = _Udon_ZenithColor (night + g x floor add,
// written by LanbaiAct09Driver from 1009.21), glow = the sky's shared galaxy map x the per-direction gain
// (LanbaiGalaxyGainAt: the core may lead) x the glow scale x the core tint.  Roughness only blurs: extra LOD from the
// smoothness, and the LOD never drops below one texel per pixel of the REFLECTED footprint (ddx/ddy of the reflection
// vector), so the convex face's minification never shimmers.
inline float3 LanbaiMirrorSkyFloor(float3 matFloor)
{
    return (_Udon_ZenithColor.a > 0.0) ? _Udon_ZenithColor.rgb : matFloor;
}
inline float LanbaiMirrorGainAt(float3 R, float matDefault)
{
    return (_Udon_GalaxyGain.w > 0.0) ? LanbaiGalaxyGainAt(_Udon_GalaxyGain, R) : matDefault;
}
inline float3 LanbaiMirrorGalaxy(sampler2D glowTex, float4 texelSize, float3 R, float smoothness)
{
    float texelRad = 6.2831853 * max(texelSize.x, 1e-6);
    float cosEl = max(sqrt(saturate(1.0 - R.y * R.y)), 0.05);
    float foot = max(length(ddx(R)), length(ddy(R)));                       // radians of reflected sky per pixel
    float lodPix = log2(max(foot, 1e-6) / (texelRad * cosEl));
    float pr = 1.0 - smoothness;
    float lodRough = log2(max(2.0 * pr * pr, 1e-6) / texelRad);            // GGX lobe width ~ 2 alpha (rad)
    float lod = max(0.0, max(lodPix, lodRough));
    return tex2Dlod(glowTex, float4(LanbaiGalaxyUV(R), 0.0, lod)).rgb * LanbaiGalaxyScale() * LanbaiGalaxyCoreTint(R);
}
inline float LanbaiMirrorStarGain(float matDefault)
{
    return (_Udon_StarGain.w > 0.0) ? _Udon_StarGain.x : matDefault;
}

#endif // LANBAI_MIRROR_INCLUDED
