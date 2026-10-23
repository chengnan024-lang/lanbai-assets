// =====================================================================================================
//  Lanbai / LanbaiSea.cginc      蓝白 · the sea's maths (bible v2.1 §6·6 海镜, §6·7a/7c, §6·8 海之天花, §8.1 #7)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only.
//      The implementer compiles it in Unity 2022.3 and checks it in a headset (one eye, then the other). !!!
//
//  Sea/Tools~/sea_numpy.py is a line-by-line Python port of this file: the reference renders use THAT, so what the
//  renders show is what this file computes. Change both together.
//
//  One flat plane, three ways of looking at it (see Sea/README_Sea接口.md):
//    ABOVE    eye in air, water below            act 6 (the sea mirror), sun glint clamped >= 1.3 EV under the disc
//    BELOW    eye in water, air on _AirSide      act 7a (Snell's window overhead), 7c (_AirSide -1: the inverted window
//                                                below the bus, the palace lamps in the dark mirror around it)
//    CEILING  eye in air below, water above      act 8-i (the sea ceiling; finite 2.7 km soft disc; dissolves edge -> zenith)
//  Colours are LINEAR Vectors (no sRGB conversion). Everything is world-anchored (stereo-safe).
// =====================================================================================================
#ifndef LANBAI_SEA_INCLUDED
#define LANBAI_SEA_INCLUDED

#include "UnityCG.cginc"
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

// ---------------------------------------------------------------------------------------------- inputs
sampler2D _NormalLarge, _NormalSmall, _Macro;
float  _LargeTile, _SmallTile, _MacroTile;
float4 _LargeScroll, _SmallScroll;          // xy = drift m/s along world x, z
float  _NormalStrength, _WaveAmp, _CalmStrength, _CalmAll;
float4 _CalmPatch;                          // xy world xz centre, z radius, w strength
float  _IOR;
float  _Smoothness;                         // microscopic water smoothness (0.97)
float  _ReflGain, _ReflClamp;
float4 _WaterColor;
float4 _DiscCenter;                         // xy centre (world xz), z radius (0 = infinite), w fade band

// _Udon_ReflCube (samplerCUBE), _Udon_ReflCube_HDR, _Udon_ReflExposure, _Udon_SeaClock (x clock s, yz water offset m,
// w > 0 = set), _Udon_SeaLevel, _Udon_SeaMode, _Udon_SunDir: declared once in LanbaiGlobals.cginc

// unresolved slope variance (Toksvig): total rms-slope^2 of each map at strength 1, from sea_textures_meta.json
#define LANBAI_SEA_VAR_LARGE 0.0121
#define LANBAI_SEA_VAR_SMALL 0.0081
#define LANBAI_SEA_TEX_N 1024.0

// ---------------------------------------------------------------------------------------------- clock / offset
inline float LanbaiSeaTime()    { return _Udon_SeaClock.w > 0.0 ? _Udon_SeaClock.x : _Time.y; }
inline float2 LanbaiSeaOffset() { return _Udon_SeaClock.w > 0.0 ? _Udon_SeaClock.yz : float2(0.0, 0.0); }

// ---------------------------------------------------------------------------------------------- cube
inline float3 LanbaiSeaCube(float3 dir, float perceptualRough)
{
    float lod = perceptualRough * (1.7 - 0.7 * perceptualRough) * 6.0;      // UNITY_SPECCUBE_LOD_STEPS
    float4 c = texCUBElod(_Udon_ReflCube, float4(dir, lod));
    float e = _Udon_ReflExposure > 0.0 ? _Udon_ReflExposure : 1.0;
    float4 hdr = _Udon_ReflCube_HDR.x > 0.0 ? _Udon_ReflCube_HDR : float4(1.0, 1.0, 0.0, 0.0);   // never set: plain linear
    float3 rgb = DecodeHDR(c, hdr) * e;
    float m = max(max(rgb.r, rgb.g), rgb.b);
    return (m > _ReflClamp) ? rgb * (_ReflClamp / m) : rgb;                  // the cube's own sun never doubles the disc
}

// ---------------------------------------------------------------------------------------------- Fresnel
// exact unpolarised dielectric Fresnel. cosI = cos of the incidence angle (>= 0) on the side with index n1,
// eta = n1 / n2. Returns 1 at total internal reflection.
inline float LanbaiFresnel(float cosI, float eta)
{
    cosI = saturate(cosI);
    float sinT2 = eta * eta * (1.0 - cosI * cosI);
    if (sinT2 >= 1.0) return 1.0;
    float cosT = sqrt(1.0 - sinT2);
    float rs = (eta * cosI - cosT) / (eta * cosI + cosT);
    float rp = (cosI - eta * cosT) / (cosI + eta * cosT);
    return 0.5 * (rs * rs + rp * rp);
}

// ---------------------------------------------------------------------------------------------- waves
// the fraction of a map's slope variance that its mip chain has averaged away at level lod (fit to the spectrum,
// sea_textures_meta.json 'unresolved_fraction_per_mip': 0, .07, .19, .32, .45, .59, .74, .86 ...)
inline float LanbaiSeaUnresolved(float lod)
{
    return pow(saturate(lod / 7.6), 1.15);
}
inline float LanbaiSeaLod(float2 uv)
{
    float2 dx = ddx(uv) * LANBAI_SEA_TEX_N, dy = ddy(uv) * LANBAI_SEA_TEX_N;
    return max(0.0, 0.5 * log2(max(dot(dx, dx), dot(dy, dy))));
}

// q = water-frame xz (world xz + offset). Returns the world normal of the AIR-facing side for a horizontal plane whose
// air is ABOVE (y > 0); callers flip y for air below. slopeVar = unresolved slope variance (adds to GGX alpha^2).
// Act 11 variant (Lamps/总导演意见.md §2): three long Gerstner swells on the hanging sea. Only their SLOPES are used
// (0.6 m of height is invisible from 80 m below; the light on them is what reads). Amplitude 0 = off.
float4 _GerstnerLength;      // xyz wavelengths m (60, 37, 23), w = frequency Hz (0.08)
float4 _GerstnerAmp;         // xyz amplitudes m (0.6, 0.35, 0.15); 0 = off
float4 _GerstnerDir;         // xy, zw: directions of waves 1 and 2 (world xz, unit); wave 3 = their bisector turned 90 deg
inline float2 LanbaiGerstnerSlope(float2 q, float t)
{
    float2 d1 = normalize(_GerstnerDir.xy + float2(1e-5, 0.0));
    float2 d2 = normalize(_GerstnerDir.zw + float2(0.0, 1e-5));
    float2 b = normalize(d1 + d2 + float2(1e-5, 1e-5));
    float2 d3 = float2(-b.y, b.x);
    float w = 6.2831853 * _GerstnerLength.w;
    float2 s = 0;
    float k;
    k = 6.2831853 / max(_GerstnerLength.x, 1.0); s += d1 * (k * _GerstnerAmp.x * cos(k * dot(d1, q) - w * t));
    k = 6.2831853 / max(_GerstnerLength.y, 1.0); s += d2 * (k * _GerstnerAmp.y * cos(k * dot(d2, q) - w * t * 1.27));
    k = 6.2831853 / max(_GerstnerLength.z, 1.0); s += d3 * (k * _GerstnerAmp.z * cos(k * dot(d3, q) - w * t * 1.61));
    return s;                                           // dh/dx, dh/dz
}

inline float3 LanbaiSeaNormal(float2 q, float2 worldXZ, out float slopeVar)
{
    float t = LanbaiSeaTime();
    float2 uvL = (q + _LargeScroll.xy * t) / _LargeTile;
    float2 uvS = (q + _SmallScroll.xy * t) / _SmallTile;
    float3 nL = UnpackNormal(tex2D(_NormalLarge, uvL));
    float3 nS = UnpackNormal(tex2D(_NormalSmall, uvS));
    // ripple mask: macro slicks, the calm patch under the bus (act 6, F1b2), the global calm (act 6, 337.0)
    float m = tex2D(_Macro, q / _MacroTile).r;
    float pd = length(worldXZ - _CalmPatch.xy);
    m *= 1.0 - _CalmPatch.w * (1.0 - smoothstep(0.6 * _CalmPatch.z, _CalmPatch.z, pd));
    m *= 1.0 - _CalmAll;
    float k = _NormalStrength * _WaveAmp * lerp(_CalmStrength, 1.0, m);
    // slopes (tangent-space: x = world x, y = world z)
    // n_ts = normalize(-dh/dx, -dh/dz, 1): the SLOPE is -n.xy / n.z (same sign convention as LanbaiGerstnerSlope)
    float2 s = -(nL.xy / max(nL.z, 0.2) + nS.xy / max(nS.z, 0.2)) * k;
    if (_GerstnerAmp.x + _GerstnerAmp.y + _GerstnerAmp.z > 0.0)
        s += LanbaiGerstnerSlope(q, t) * _WaveAmp;
    float vL = LANBAI_SEA_VAR_LARGE * LanbaiSeaUnresolved(LanbaiSeaLod(uvL));
    float vS = LANBAI_SEA_VAR_SMALL * LanbaiSeaUnresolved(LanbaiSeaLod(uvS));
    slopeVar = (vL + vS) * k * k;
    return normalize(float3(-s.x, 1.0, -s.y));
}

// GGX alpha from the surface smoothness + the unresolved waves (Beckmann m^2 = total slope variance, GGX ~ Beckmann)
inline float LanbaiSeaAlpha(float slopeVar)
{
    float pr = 1.0 - _Smoothness;
    return sqrt(pr * pr * pr * pr + slopeVar);
}
inline float LanbaiSeaPerceptual(float alpha) { return sqrt(saturate(alpha)); }

// ---------------------------------------------------------------------------------------------- disc edge
inline float LanbaiSeaDiscAlpha(float2 worldXZ)
{
    if (_DiscCenter.z <= 0.0) return 1.0;
    float d = length(worldXZ - _DiscCenter.xy);
    float h = 0.5 * max(_DiscCenter.w, 1.0);
    return 1.0 - smoothstep(_DiscCenter.z - h, _DiscCenter.z + h, d);
}

// ---------------------------------------------------------------------------------------------- GGX helpers
inline float LanbaiGGX_D(float NdotH, float a)
{
    float a2 = a * a;
    float d = NdotH * NdotH * (a2 - 1.0) + 1.0;
    return a2 / (UNITY_PI * d * d + 1e-12);
}
inline float LanbaiSmithVis(float NdotL, float NdotV, float a)
{
    return 0.5 / (NdotL * (NdotV * (1.0 - a) + a) + NdotV * (NdotL * (1.0 - a) + a) + 1e-5);
}

// soft cap that keeps the hue (Rain kit's LanbaiSoftCap, repeated here so this file stands alone)
inline float3 LanbaiSeaSoftCap(float3 c, float peak)
{
    float m = max(max(c.r, c.g), c.b);
    return m > 1e-6 ? c * (peak * tanh(min(m / peak, 8.0)) / m) : c;
}

// ============================================================================================== ABOVE
float4 _SunColor;            // linear radiance of the sun DISC (the same number Lanbai/Sky draws the disc with)
float4 _SunDir;              // to the sun (fallback for _Udon_SunDir)
float  _SunGlitterRough;     // extra GGX alpha for the glitter path (sub-pixel wave facets that the maps do not hold)
float  _SunReflPeakEV;       // every point of the glitter path is at least this many EV under the disc (bible E14: 1.3)
float  _SunDiscDeg;          // disc angular diameter (0.9)

inline float3 LanbaiSeaSunDir()
{
    return normalize(_Udon_SunDir.w > 0.0 ? _Udon_SunDir.xyz : _SunDir.xyz);
}

// V: unit vector from the surface point TO the eye.  Returns linear radiance (before fog).
inline float3 LanbaiSeaAbove(float3 N, float3 V, float slopeVar)
{
    float a = LanbaiSeaAlpha(slopeVar);
    float NdotV = max(dot(N, V), 1e-4);
    float3 R = reflect(-V, N);
    R.y = abs(R.y);                                               // a facet tilted past the horizon still sees sky
    float F = LanbaiFresnel(NdotV, 1.0 / _IOR);
    float3 refl = LanbaiSeaCube(R, LanbaiSeaPerceptual(a)) * _ReflGain;

    // the sun's glitter path: GGX with the waves' unresolved slopes + the glitter roughness, disc as a solid angle
    float3 L = LanbaiSeaSunDir();
    float3 sun = 0;
    if (_SunColor.a >= 0.0 && max(_SunColor.r, max(_SunColor.g, _SunColor.b)) > 0.0 && L.y > -0.02)
    {
        float ag = sqrt(a * a + _SunGlitterRough * _SunGlitterRough);
        float3 H = normalize(L + V);
        float NdotL = saturate(dot(N, L));
        float NdotH = saturate(dot(N, H));
        float omega = UNITY_PI * pow(radians(0.5 * _SunDiscDeg), 2.0);              // disc solid angle
        float Fs = LanbaiFresnel(saturate(dot(V, H)), 1.0 / _IOR);
        sun = _SunColor.rgb * (omega * LanbaiGGX_D(NdotH, ag) * LanbaiSmithVis(NdotL, NdotV, ag) * NdotL * Fs);
        // E14: the reflected sun is a glitter PATH, never a second disc: cap every pixel at disc x 2^-EV (soft, hue kept)
        float discMax = max(_SunColor.r, max(_SunColor.g, _SunColor.b));
        sun = LanbaiSeaSoftCap(sun, discMax * exp2(-_SunReflPeakEV));
    }
    float3 body = _WaterColor.rgb * (1.0 - F);
    return refl * F + sun + body;
}

// ============================================================================================== BELOW
UNITY_DECLARE_TEXCUBE(_WindowCube);
float4 _WindowCube_HDR;
float  _WindowGain;
float4 _WindowTint;
float4 _Dispersion;          // x = n for red, y = n for blue (green = _IOR)
float4 _TIRColor;
float  _TIRCubeGain;
float  _AirSide;             // +1 air above the plane (7a), -1 air below (7c)
float  _WindowEdgeSoft;      // deg
float4 _WindowSunDir;        // the sun ON THE AIR SIDE (unit, world; 7c: the dusk sun's other self, az 0, el -0.5);
                             // w = elevation half-width deg of the arc (the glow hugging the horizon)
float  _WindowSunSpread;     // azimuth half-width deg of the arc (the sunset band along the window's rim)
float4 _WindowSunColor;      // its radiance (linear, rose-gold); 0 = off. Bible 7c: '太阳被压扁成一道玫瑰金的弧，贴在窗的边缘'
float  _WindowSunFloor;      // transmission floor for the sun term (Fresnel would erase a sun this close to the rim)
float4 _WindowRadial;        // x = window multiplier AT the critical angle, y = power: lerp(1, x, (theta/theta_c)^y). (1, 2) = off.
                             // Bible target, not physics: a dawn sky is brightest at its horizon = the window's rim; the
                             // bible wants a near-white core (#E6F3F8) falling to L6 (#B4D6E3) at the edge (§6·7a 构图)

inline float3 LanbaiSeaWindowCube(float3 dir)
{
    float3 rgb = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(_WindowCube, dir, 0.0), _WindowCube_HDR);
    float m = max(max(rgb.r, rgb.g), rgb.b);
    return (m > _ReflClamp) ? rgb * (_ReflClamp / m) : rgb;                  // the sun in the window stays a glint
}

// refraction water -> air through a facet. I = incident (eye -> surface, unit), Na = facet normal pointing INTO the air.
// Returns the transmitted direction (unit) and 'ok' = 0 at total internal reflection.
inline float3 LanbaiSeaRefractOut(float3 I, float3 Na, float n, out float ok)
{
    float c = dot(I, Na);                                   // > 0
    float s2 = n * n * (1.0 - c * c);
    ok = s2 < 1.0 ? 1.0 : 0.0;
    float ct = sqrt(saturate(1.0 - s2));
    return normalize(n * I + (ct - n * c) * Na);
}

// N: wave normal for an air-ABOVE plane (LanbaiSeaNormal); I: unit vector eye -> surface point.
// tirFill: what the water itself looks like in the mirror (the fog colour of the reflected direction, or _TIRColor).
inline float3 LanbaiSeaBelow(float3 N, float3 I, float slopeVar)
{
    float side = _AirSide >= 0.0 ? 1.0 : -1.0;
    float3 Na = float3(N.x, N.y * side, N.z);                 // normal into the air
    if (dot(I, Na) <= 1e-4) Na = float3(0.0, side, 0.0);     // a facet seen from behind: use the flat plane
    float cosI = dot(I, Na);
    float F = LanbaiFresnel(cosI, _IOR);
    float okR, okG, okB;
    float3 Tg = LanbaiSeaRefractOut(I, Na, _IOR, okG);
    float3 Tr = LanbaiSeaRefractOut(I, Na, _Dispersion.x, okR);
    float3 Tb = LanbaiSeaRefractOut(I, Na, _Dispersion.y, okB);
    float3 win;
    win.r = LanbaiSeaWindowCube(Tr).r * okR;
    win.g = LanbaiSeaWindowCube(Tg).g * okG;
    win.b = LanbaiSeaWindowCube(Tb).b * okB;
    // radiance entering the denser medium is multiplied by n^2 (the window really is brighter than the sky)
    win *= _WindowTint.rgb * (_WindowGain * _IOR * _IOR);
    // soft edge at the critical angle (the waves make it shimmer; this only removes the 1-px stair)
    float crit = asin(1.0 / _IOR);
    float th = acos(saturate(cosI));
    float edge = 1.0 - smoothstep(crit - radians(_WindowEdgeSoft), crit, th);
    edge *= lerp(1.0, _WindowRadial.x, pow(saturate(th / crit), max(_WindowRadial.y, 0.01)));
    // the sun seen through the window: compressed against the rim by the refraction itself (T near the horizon)
    float3 wsun = 0;
    float wcover = 0.0;                                         // how much of the window the arc REPLACES (no rose-over-blue lavender)
    [branch] if (max(_WindowSunColor.r, max(_WindowSunColor.g, _WindowSunColor.b)) > 0.0)
    {
        float3 sd = normalize(_WindowSunDir.xyz);
        float dEl = degrees(asin(clamp(Tg.y, -1.0, 1.0)) - asin(clamp(sd.y, -1.0, 1.0)));
        float dAz = degrees(acos(clamp(dot(normalize(Tg.xz + float2(1e-5, 0.0)), normalize(sd.xz + float2(1e-5, 0.0))), -1.0, 1.0)));
        float re = max(_WindowSunDir.w, 0.05), ra = max(_WindowSunSpread, 0.05);
        float arc = exp(-(dEl / re) * (dEl / re)) * (0.7 * exp(-(dAz / ra) * (dAz / ra)) + 0.3 * exp(-(dAz / (0.12 * ra)) * (dAz / (0.12 * ra))));
        wsun = _WindowSunColor.rgb * (okG * arc * max(1.0 - F, _WindowSunFloor) * _WindowGain);
        wcover = saturate(arc * 1.5);
    }
    float3 R = reflect(I, Na);                                 // back into the water
    float pr = LanbaiSeaPerceptual(LanbaiSeaAlpha(slopeVar));
    float3 mirror = _TIRColor.rgb + (_TIRCubeGain > 0.0 ? LanbaiSeaCube(R, pr) * _TIRCubeGain : float3(0, 0, 0));
    return mirror * F + win * ((1.0 - F) * edge * (1.0 - wcover)) + wsun;
}

// ============================================================================================== CEILING
UNITY_DECLARE_TEXCUBE(_SkyBehindCube);
float4 _SkyBehindCube_HDR;
float4 _MirrorTint;          // the grazing mirror band's tint (D-17: toward gold, h_ab >= 60); (1, 1, 1) = none
float  _DissolveTime;        // t - F10e (956.36); < 0 = whole
float  _DissolveFront;       // 4 s: the front runs horizon -> zenith
float  _DissolvePixel;       // 5 s: each pixel's own EV-linear fade

// pixel progress of the dissolve for a view direction (unit, eye -> point). 0 = whole ceiling, 1 = gone.
inline float LanbaiCeilingProgress(float3 viewDir)
{
    if (_DissolveTime < 0.0) return 0.0;
    float el = degrees(asin(saturate(viewDir.y)));
    return saturate((_DissolveTime - _DissolveFront * el / 90.0) / max(_DissolvePixel, 0.01));
}
// the palace lamp points of the ceiling go LAST inside every pixel
inline float LanbaiCeilingLampProgress(float3 viewDir)
{
    return saturate((LanbaiCeilingProgress(viewDir) - 0.3) / 0.7);
}

inline float LanbaiLuma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

// ---- OKLab (Ottosson 2020), linear sRGB in / out ------------------------------------------------------------------
inline float3 LanbaiLinToOklab(float3 c)
{
    float l = 0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b;
    float m = 0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b;
    float s = 0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b;
    l = pow(max(l, 0.0), 1.0 / 3.0); m = pow(max(m, 0.0), 1.0 / 3.0); s = pow(max(s, 0.0), 1.0 / 3.0);
    return float3(0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                  1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                  0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s);
}
inline float3 LanbaiOklabToLin(float3 L)
{
    float l = L.x + 0.3963377774 * L.y + 0.2158037573 * L.z;
    float m = L.x - 0.1055613458 * L.y - 0.0638541728 * L.z;
    float s = L.x - 0.0894841775 * L.y - 1.2914855480 * L.z;
    l = l * l * l; m = m * m * m; s = s * s * s;
    return max(float3(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                     -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                     -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s), 0.0);
}

// Purple guard (Art/总导演裁决.md D-17; bible §1.3.4: outside acts 4 / 4c no region > 2 % may be h_ab 290-325 & C* > 15).
// Measured (Sea/Docs~/review_r1_response.md): under the S7b / S8 grades the colours that DISPLAY as violet come from linear
// OKLab hues ~260..335, which overlaps the bible's own blues (OKLab 253..273). So the guard does two things:
//   * 258..300 deg: ROTATE the hue back toward ultramarine (_PurpleGuard.z, OKLab ~252), chroma kept: blues stay blue;
//   * 300..345 deg: pull the chroma to <= _PurpleGuard.y (the true violets become a low-chroma neutral, D-17's 'C* <= 8').
// Applied to the FINAL colour of every sea mode (after fog). x = 0 off / 1 on.
float4 _PurpleGuard;         // x on, y max OKLab chroma for violets (0.02 ~ CIE C* 5), z target hue deg (252)
inline float3 LanbaiPurpleGuard(float3 c)
{
    if (_PurpleGuard.x <= 0.0) return c;
    float3 L = LanbaiLinToOklab(c);
    float C = length(L.yz);
    if (C <= 1e-4) return c;
    float h = degrees(atan2(L.z, L.y));
    h = h < 0.0 ? h + 360.0 : h;
    float rot = smoothstep(258.0, 266.0, h) * (1.0 - smoothstep(296.0, 304.0, h));
    float vio = smoothstep(296.0, 304.0, h) * (1.0 - smoothstep(335.0, 345.0, h));
    float hz = _PurpleGuard.z > 0.0 ? _PurpleGuard.z : 252.0;
    float h2 = lerp(h, hz + (h - hz) * 0.15, rot * _PurpleGuard.x);
    float C2 = lerp(C, min(C, _PurpleGuard.y), vio * _PurpleGuard.x);
    float r = radians(h2);
    L.yz = float2(cos(r), sin(r)) * C2;
    return LanbaiOklabToLin(L);
}

// alpha that makes   lerp(sky, ceil, alpha)   follow L(p) = Lc^(1-p) Ls^p  (EV-linear per pixel, bible §1.8)
inline float LanbaiEvLinearAlpha(float Lc, float Ls, float p)
{
    Lc = max(Lc, 1e-5); Ls = max(Ls, 1e-5);
    if (abs(Lc - Ls) < 1e-3) return 1.0 - p;                    // equally bright: a linear fade is the EV-linear one
    float Lp = exp2(lerp(log2(Lc), log2(Ls), p));
    return saturate((Lp - Ls) / (Lc - Ls));
}

// Act 11: the street lamps' GGX glints on the hanging sea (_Udon_Lamp0..7: xyz position, w intensity I with E = I / d^2;
// _Udon_LampColor rgb linear, a = source radius m; omni). Smoothness 0.97 (alpha from LanbaiSeaAlpha + this).
float  _LampGlints;          // 0..1 (0 = off: acts 6 / 8)
inline float3 LanbaiCeilingLampOne(float4 lamp, float4 colR, float3 P, float3 Nw, float3 V, float a, float eta)
{
    if (lamp.w <= 0.0) return float3(0.0, 0.0, 0.0);
    float3 toL = lamp.xyz - P;
    float d2 = max(dot(toL, toL), 1e-2);
    float3 L = toL * rsqrt(d2);
    float NdotL = saturate(dot(Nw, L));
    float NdotV = max(dot(Nw, V), 1e-4);
    float aP = saturate(a + colR.a / (2.0 * sqrt(d2)));                       // sphere widening (Karis)
    float3 H = normalize(L + V);
    float F = LanbaiFresnel(saturate(dot(V, H)), eta);
    return colR.rgb * (lamp.w / d2 * NdotL * LanbaiGGX_D(saturate(dot(Nw, H)), aP) * LanbaiSmithVis(NdotL, NdotV, aP) * F * (a * a) / (aP * aP));
}
inline float3 LanbaiCeilingLamps(float3 P, float3 Nw, float3 V, float a, float eta)
{
    float3 s = 0;
    s += LanbaiCeilingLampOne(_Udon_Lamp0, _Udon_LampColor0, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp1, _Udon_LampColor1, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp2, _Udon_LampColor2, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp3, _Udon_LampColor3, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp4, _Udon_LampColor4, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp5, _Udon_LampColor5, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp6, _Udon_LampColor6, P, Nw, V, a, eta);
    s += LanbaiCeilingLampOne(_Udon_Lamp7, _Udon_LampColor7, P, Nw, V, a, eta);
    return s;
}

// N: wave normal for an air-ABOVE plane; I: unit vector eye -> point (going UP). Returns rgb (linear) + alpha.
inline float4 LanbaiSeaCeiling(float3 N, float3 I, float slopeVar, float2 worldXZ, float3 P)
{
    float3 Nw = float3(N.x, -N.y, N.z);                       // the facet faces DOWN, toward the eye
    float cosI = saturate(dot(-I, Nw));
    float F = LanbaiFresnel(cosI, 1.0 / _IOR);
    float3 R = reflect(I, Nw);                                 // down: the dusk below (ReflCube_DuskLower)
    R.y = -abs(R.y);
    float a = LanbaiSeaAlpha(slopeVar);
    float3 refl = LanbaiSeaCube(R, LanbaiSeaPerceptual(a)) * _ReflGain * _MirrorTint.rgb;
    float3 c = refl * F + _WaterColor.rgb * (1.0 - F);
    [branch] if (_LampGlints > 0.0)
        c += LanbaiCeilingLamps(P, Nw, -I, a, 1.0 / _IOR) * _LampGlints;
    float alpha = LanbaiSeaDiscAlpha(worldXZ);
    float p = LanbaiCeilingProgress(I);
    if (p > 0.0)
    {
        float3 sky = DecodeHDR(UNITY_SAMPLE_TEXCUBE_LOD(_SkyBehindCube, I, 0.0), _SkyBehindCube_HDR);
        // the colour moves with the same alpha; the LUMINANCE follows the EV-linear line
        float aEv = LanbaiEvLinearAlpha(LanbaiLuma(c), LanbaiLuma(sky), p);
        alpha *= aEv;
    }
    return float4(c, alpha);
}

// ============================================================================================== waterline
// The waterline on the bus glass (entry 6 -> 7: rising; exit 7 -> 8: the water runs UP off the glass).
// posWS: glass point; level: the plane's world y (+ a wobble); waterBelow: +1 water under the line (entry), -1 above (exit)
// Returns rgb (emissive add: meniscus highlight) and a = how much the water film tints the glass (0..1).
float4 _WaterlineColor;      // meniscus highlight (linear), a = film tint strength
inline float4 LanbaiWaterline(float3 posWS, float level, float waterBelow, float t)
{
    float wob = 0.012 * sin(posWS.x * 7.3 + t * 2.1) + 0.007 * sin(posWS.z * 11.1 - t * 3.3) + 0.004 * sin((posWS.x + posWS.z) * 23.0 + t * 5.0);
    float h = (posWS.y - (level + wob)) * (waterBelow >= 0.0 ? 1.0 : -1.0);   // < 0 = in the water
    float px = max(fwidth(posWS.y), 1e-4);
    float meniscus = exp(-0.5 * (h / max(0.004, 1.5 * px)) * (h / max(0.004, 1.5 * px)));   // ~4 mm meniscus, >= 1.5 px
    float film = 1.0 - smoothstep(-px, px, h);
    return float4(_WaterlineColor.rgb * meniscus, film * _WaterlineColor.a);
}

#endif // LANBAI_SEA_INCLUDED
