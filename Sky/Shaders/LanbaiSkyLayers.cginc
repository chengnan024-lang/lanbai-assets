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
float4 _SunDir, _SunColor, _SunShape, _SunGlow, _SunGlowColor;
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
// azimuth weight ^ _TintElevation.w) -> mid over [0, _TintElevation.y], mid -> zenith over [_TintElevation.y,
// _TintElevation.z]; the horizon tint is full below _TintElevation.x.
float3 LanbaiCubeTint(float3 Vs, float3 zt, float3 mt, float3 ht, float3 hat, float3 S)
{
    float el = LanbaiElevationDeg(Vs);
    float3 hTint = lerp(hat, ht, LanbaiSunward(Vs, S, _TintElevation.w));
    float t1 = smoothstep(_TintElevation.x, max(_TintElevation.y, _TintElevation.x + 0.1), el);
    float t2 = smoothstep(_TintElevation.y, max(_TintElevation.z, _TintElevation.y + 0.1), el);
    return lerp(lerp(hTint, mt, t1), zt, t2);
}

float3 LanbaiCubeUpper(samplerCUBE cube, half4 hdr, float3 Vs, float rot, float ev, float clampV,
                       float3 zt, float3 mt, float3 ht, float3 hat, float3 S, float lod)
{
    // the HDRI's own horizon (a dark haze / ground line in every 'pure sky') is never sampled: lift to _HorizonLift deg
    float3 Vl = Vs;
    Vl.y = max(Vl.y, sin(radians(_HorizonLift)));
    float3 d = LanbaiRotY(normalize(Vl), rot);
    half4 raw = texCUBElod(cube, float4(d, lod));
    float3 c = DecodeHDR(raw, hdr);
    c = min(c * exp2(ev), clampV);
    return c * LanbaiCubeTint(Vs, zt, mt, ht, hat, S);
}

// a full-sphere HDRI layer: upper = the tinted HDRI; lower = its horizon (clamped to _BelowShape.w so the sun does
// not leak a column below it) -> _NadirColor
float3 LanbaiCubeLayer(samplerCUBE cube, half4 hdr, float3 V, float rot, float ev, float clampV,
                       float3 zt, float3 mt, float3 ht, float3 hat, float3 S)
{
    if (V.y >= 0.0)
        return LanbaiCubeUpper(cube, hdr, V, rot, ev, clampV, zt, mt, ht, hat, S, 0.0);
    float3 H = normalize(float3(V.x, sin(radians(_BelowShape.z)), V.z));
    float hc = (_BelowShape.w > 0.0) ? _BelowShape.w : clampV;
    float el = LanbaiElevationDeg(V);
    float3 hzSharp = LanbaiCubeUpper(cube, hdr, H, rot, ev, clampV, zt, mt, ht, hat, S, 0.0);
    float3 hzSoft = LanbaiCubeUpper(cube, hdr, H, rot, ev, hc, zt, mt, ht, hat, S, 3.0);
    float3 hz = lerp(hzSharp, hzSoft, smoothstep(0.0, 3.0, -el));          // continuous at the horizon, no streaks below
    float t = smoothstep(0.0, 1.0, saturate(el / min(_BelowShape.x, -0.1)));
    t = pow(t, max(_BelowShape.y, 0.01));
    float3 c = lerp(hz, _NadirColor.rgb, t);
    // the middle of a warm -> indigo gradient passes through mauve: desaturate it toward a cold grey (_NadirColor.a)
    float lum = dot(c, float3(0.2126, 0.7152, 0.0722));
    return lerp(c, lum * float3(0.90, 0.97, 1.13), saturate(_NadirColor.a * 4.0 * t * (1.0 - t)));
}

float3 LanbaiCubes(float3 V, float3 S, float blend)
{
    float3 c = 0;
    [branch] if (blend < 0.999)
        c = LanbaiCubeLayer(_CubeA, _CubeA_HDR, V, _RotationA, _ExposureA, _ClampA,
                            _ZenithTintA.rgb, _MidTintA.rgb, _HorizonTintA.rgb, _HorizonAntiTintA.rgb, S) * (1.0 - blend);
    [branch] if (blend > 0.001)
        c += LanbaiCubeLayer(_CubeB, _CubeB_HDR, V, _RotationB, _ExposureB, _ClampB,
                             _ZenithTintB.rgb, _MidTintB.rgb, _HorizonTintB.rgb, _HorizonAntiTintB.rgb, S) * blend;
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
    float edge = smoothstep(radius + 0.5 * _SunShape.y, radius - 0.5 * _SunShape.y, a);
    float r = saturate(a / max(radius, 1e-3));
    float limb = 1.0 - _SunShape.z * (1.0 - sqrt(saturate(1.0 - r * r)));
    float3 c = _SunColor.rgb * (edge * limb);
    c += _SunGlowColor.rgb * (_SunGlow.x * exp(-_SunGlow.y * a) + _SunGlow.z * exp(-_SunGlow.w * a));
    return c * gain;
}

float3 LanbaiMoonTerm(float3 V, float gain)
{
    float3 M = LanbaiSkyMoonDir(_MoonDir.xyz);
    float radius = (_Udon_MoonDisc.w > 0.0) ? _Udon_MoonDisc.y : _MoonRadius;
    float am = LanbaiAngleDeg(V, M);
    float3 c = _MoonGlowColor.rgb * (_MoonGlow.x * exp(-_MoonGlow.y * am) + _MoonGlow.z * exp(-_MoonGlow.w * am));
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
        c = lerp(c, t.rgb * _MoonColor.rgb, t.a);
    }
    return c * gain;
}

float3 LanbaiGalaxy(float3 V)
{
    return tex2Dlod(_GlowTex, float4(LanbaiGalaxyUV(V), 0.0, 0.0)).rgb;
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
    [branch] if (band1Gain > 0.0 && _Band1Shape.y < 0.0)
        c = LanbaiMonotonicBand(c, V, S, _Band1Color, _Band1Shape, band1Gain);
    else if (band1Gain > 0.0)
        c = LanbaiBandBlend(c, _Band1Color, saturate(band1Gain * LanbaiBandWeight(V, S, _Band1Shape)));
    [branch] if (_Band2Gain > 0.0)
        c = LanbaiBandBlend(c, _Band2Color, saturate(_Band2Gain * LanbaiBandWeight(V, S, _Band2Shape)));
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
// x = 0.75 (6 s), the front horizon band (|az| < 40 deg of _NightMaskDir, below ~12 deg) is still 50 % at 0.75 and
// reaches 1 at x = 1. (bible §6·8b: front band >= 50 % at 1007.2, black at 1009.21; elsewhere black in 6 s)
float LanbaiNightWeight(float3 V, float x)
{
    float az = LanbaiAzimuthDeg(V, _NightMaskDir.xyz);
    float el = LanbaiElevationDeg(V);
    float f = (1.0 - smoothstep(_NightMaskShape.x, _NightMaskShape.x + _NightMaskShape.y, az))
            * (1.0 - smoothstep(_NightMaskShape.z, _NightMaskShape.z + _NightMaskShape.w, abs(el)));
    float d = 0.5 * f;
    float w = saturate((x - d) / (0.75 - 0.25 * f));
    return w * w * (3.0 - 2.0 * w);                       // eased: no visible edge where neighbouring directions differ
}

float3 LanbaiSkyColour(float3 V)
{
    float blend = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.x : _Blend;
    float proc  = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.y : _ProcWeight;
    float night = (_Udon_SkyBlend.w > 0.0) ? _Udon_SkyBlend.z : _NightBlend;
    float other = (_Udon_SkyFx.w > 0.0) ? _Udon_SkyFx.x : _OtherSky;
    float bandG = (_Udon_SkyFx.w > 0.0) ? _Udon_SkyFx.y : _Band1Gain;
    float sunLine  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.z : _SunShape.w;
    float gal   = (_Udon_GalaxyGain.w > 0.0) ? _Udon_GalaxyGain.x : _GalaxyGain;
    float sunG  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.x : _SunGain;
    float sunR  = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.y : _SunShape.x;
    float moonG = (_Udon_MoonDisc.w > 0.0) ? _Udon_MoonDisc.x : _MoonGain;
    float3 S = LanbaiSunDir(_SunDir.xyz);

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
        float w = other * LanbaiOtherSkyWeight(V, _OtherSeam);
        float3 Vo = LanbaiOtherSkyDir(V);
        Vo.y = abs(Vo.y);
        // the other sky: the same cubes rotated 180 deg about +Z, or (_OtherFromB = 1) cube B: other air, other light
        float3 o = (_OtherFromB > 0.5) ? LanbaiCubes(Vo, S, 1.0) : LanbaiCubes(Vo, S, blend);
        if (sunG > 0.0)
            o += LanbaiSunTerm(Vo, S, sunG, sunR, sunLine);
        c = lerp(c, o * _OtherGain * _OtherTint.rgb, w);
    }

    c = LanbaiPurpleGuard(c, _PurpleGuard);

    // 4. night
    [branch] if (night > 0.001)
    {
        float3 n = _NightColor.rgb + gal * (_StarFloorAdd.rgb + LanbaiGalaxy(V));
        c = lerp(c, n, LanbaiNightWeight(V, night));
    }

    // 5. moon
    [branch] if (moonG > 0.0)
        c += LanbaiMoonTerm(V, moonG);

    return max(c, 0.0) * exp2(_Exposure);
}

#endif // LANBAI_SKY_LAYERS_INCLUDED
