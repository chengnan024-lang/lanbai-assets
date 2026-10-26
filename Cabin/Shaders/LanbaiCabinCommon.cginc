// =====================================================================================================
//  Lanbai / LanbaiCabinCommon.cginc   蓝白 · 车厢共用的数学（Lanbai/Cabin 与 Lanbai/ThinCloth 都 include）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + Unity 2022.3.22f1
//      CGIncludes), never compiled in Unity. Cabin/Tools~/cabin_numpy.py is a 1:1 numpy port of the colour maths
//      here (bleach, erosion threshold + rim, D-08 / D-21 limiter, D-40 #4 specular AA); change both together. !!!
//
//  Bible §4.8 '慢慢消失': bleach (_Udon_CabinBleach) then erosion (_Udon_CabinFade, clip on world-space 3D FBM,
//  0.3-0.8 m patches). Threshold structure is the bible's:
//      tau = fade - 0.45 (1 - heightN) - 0.25 (front term) - 0.35 (skylight term)   (+ the D-46 zenith term)
//  _ErodeForm 1 = the literal text (front term = front-ness, skylight term = exp(-d / 0.8)).
//  _ErodeForm 0 = DEFAULT, the bible's own prose ("侵蚀从天窗的边开始，然后车顶与车头"): the two terms are
//                 complemented (1 - front-ness, 1 - exp(-d / 0.8)) so the skylight edge and the front go FIRST.
//  The literal signs make the skylight and the front go LAST - the opposite of the sentence after the formula.
//  Cabin/README.md §4 and the swatches in Cabin/Docs~ show both; the director picks (Cabin/给总控_shader.md).
//  A pixel is removed where noise < tau. Noise = FBM remapped to ~uniform, then to [_ErodeNoiseRange.x, .y].
//
//  Bus frame = world frame (the bus never moves: treadmill, bible §1.6). Numbers from Bus/Source/bus_spec.py.
// =====================================================================================================
#ifndef LANBAI_CABIN_COMMON_INCLUDED
#define LANBAI_CABIN_COMMON_INCLUDED

#include "UnityCG.cginc"
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"   // _Udon_Cabin*, _Udon_SunDir ... (never declared here)
#include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"        // LanbaiHash13

// ---------------------------------------------------------------------------------------------------
// material uniforms shared by both shaders (declared BEFORE use: gate test pitfall 1)
float  _ErodeEnable;          // 0 = this material never erodes (e.g. the radio's dial glass? no: everything erodes; 0 is a debug switch)
float  _ErodeForm;            // 0 prose (default), 1 literal bible text
float4 _ErodeCoef;            // x height 0.45, y front 0.25, z skylight 0.35, w skylight falloff m 0.8
float4 _ErodeNoise;           // x base patch size m 0.55, y FBM uniformise lo, z FBM uniformise hi, w rim width m 0.03
float4 _ErodeNoiseRange;      // x, y: the uniform noise is mapped to [x, y] before the compare (-0.20, 0.25)
float4 _CabinBox;             // x floor y 0.62, y crown y 2.62, z rear z -3.65, w front z 3.50
float4 _SkyRect;              // xyz skylight glass centre (0.55, 2.62, 2.80), w half size 0.30
float4 _ErodeZenith;          // D-46 seed segment over the hero: x 0.55, z0 1.95 .. z1 2.50 (skylight's near edge), w strength 0.50
float4 _ErodeZenithShape;     // x falloff m 0.15, y sideways stretch 2 (x distances / 2), zw ceiling gate y 2.40 .. 2.50
float4 _ErodeZenithRamp;      // xy: the term comes in with the fade 0.050 -> 0.075 (t 374.5 -> 388.2)
float  _FadeResist;           // subtracted from tau for this material (stanchions 0.30: '立柱最后走')
float4 _SeatSphere;           // xyz local seat centre (world), w radius 0.9  (driver writes per client via MPB)
float4 _FloorPatch;           // x0 x1 z0 z1 of the patch kept to act 9 (>= 1.2 x 1.6 m)
float4 _HoleFull;             // D-26 full hole: centre x, centre z, half x, half z (0.55, 2.925, 0.45, 0.475)
float4 _HoleMin;              // D-26 minimum hole (0.55, 3.04, 0.30, 0.26)
float4 _DoorBoxMin;           // D-33 #7a door group box (world): xyz min, w soft margin m
float4 _DoorBoxMax;           // xyz max
float  _DoorBias;             // 0..1, driver MPB: 1 = everything in the door box is gone (by 965.4)
float4 _HoleShape;            // x corner radius m, y edge noise amplitude m, z max surface y for the hole (floor + 0.08), w unused
float  _HoleOpen;             // 0 none, 0.5 = min hole, 1 = full hole (driver writes via MPB; F8b -> 897.96)

// ---------------------------------------------------------------------------------------------------
// colour helpers
inline float LanbaiLuma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

// bible §4.8 bleach: albedo -> luminance x 0.9 tinted by _Udon_CabinAmbient, smoothness -> 0.3
inline float3 LanbaiCabinBleachAlbedo(float3 albedo, float bleach)
{
    float3 amb = max(_Udon_CabinAmbient.rgb, 0.0);
    float la = LanbaiLuma(amb);
    float3 tint = la > 1e-5 ? amb / la : float3(1.0, 1.0, 1.0);
    tint = min(tint, 1.6);                                            // a saturated ambient must not explode the tint
    float3 target = LanbaiLuma(albedo) * 0.9 * tint;
    return lerp(albedo, target, saturate(bleach));
}
inline float LanbaiCabinBleachSmooth(float s, float bleach) { return lerp(s, 0.3, saturate(bleach)); }

// ---------------------------------------------------------------------------------------------------
// D-40 #4 geometric specular anti-aliasing (VR, ~20 px/deg: the painted seat tube, the Ø32 stanchions, the window
// alu frame's 1.2 mm rounded edges, the chrome 0.85 small parts - stop-button ring, window latch, driver's levers -
// at 1-2 m).
// Tokuyoshi & Kaplanyan 2019, "Improved Geometric Specular Antialiasing", I3D '19, the normal-derivative ("deferred")
// listing, itself the screen-space form of Kaplanyan, Hill, Patney & Lefohn 2016 (HPG '16):
//     kernelRoughness2   = 2 sigma2 (dot(dndx, dndx) + dot(dndy, dndy))      sigma2: pixel filter variance (paper 1/2pi)
//     filteredRoughness2 = saturate(roughness2 + min(kernelRoughness2, kappa)) kappa: threshold (paper 0.18)
// 'roughness2' is the GGX alpha squared. Filament (surface_shading_lit.fs: computeKernelRoughness + normalFiltering,
// MaterialBuilder defaults variance 0.15 / threshold 0.2) is the same maths. Unity Standard: perceptualRoughness =
// 1 - smoothness, alpha = perceptualRoughness^2 (GGXTerm squares it again), so roughness2 = (1 - s)^4 and
// s' = 1 - filteredRoughness2^(1/4). (Adding the kernel to alpha instead of alpha^2 would be a much weaker filter:
// slope variances add in alpha^2.)
// Which normal: the CALLER picks. Filament reads the geometric (vertex) normal; the paper's deferred listing reads the
// G-buffer normal, i.e. the shading normal with the normal maps. Lanbai/Cabin defaults to the shading normal
// (_SpecAAMapNormal 1): Unity's BC5 / DXT5nm normal maps rebuild z, so a mip keeps no normal variance (no Toksvig),
// and the D-36 part masks carry no roughness-from-normal prefilter - the derivative is the only place the baked
// piping, seams and rounded edges get filtered. _SpecAAMapNormal 0 = Filament's choice. The two agree where there is
// no normal map (Steel / Alu / Chrome); they differ on the D-36 seat parts, whose one material carries the baked
// part normal and the leather grain on the tube as well as on the leatherette.
// Isotropic (Unity Standard GGX has no anisotropy): on a thin tube the widening along its axis is wasted, so the
// highlight of a directional / point light gets wider AND dimmer (cabin_numpy specaa: a Ø32 pole at 0.80 seen at 2 m
// keeps ~51 % of its energy, its flicker drops ~4x; a Ø12 chrome lever at 0.85 keeps ~14 %, flicker ~8x less).
// Hard edges with split normals are not seen (a quad never spans two triangles).
// sigma2 = 0 returns the input exactly (off). ~15 ALU: 2 derivative ops, 2 dp3, 2 sqrt, a few mad / min / saturate.
// Call it at the top level of the fragment code (no divergent branch around it: ddx / ddy). Cabin/Tools~/cabin_numpy.py
// spec_aa() is the CPU port (self-test: python3 Cabin/Tools~/cabin_numpy.py specaa).
inline float LanbaiCabinSpecAA(float smoothness, float3 nWS, float sigma2, float kappa)
{
    float3 dndx = ddx(nWS);
    float3 dndy = ddy(nWS);
    float kernelRoughness2 = min(2.0 * sigma2 * (dot(dndx, dndx) + dot(dndy, dndy)), kappa);
    float pr = 1.0 - saturate(smoothness);                            // perceptual roughness
    float roughness2 = pr * pr;
    roughness2 *= roughness2;                                         // alpha^2 = pr^4
    float filtered = 1.0 - sqrt(sqrt(saturate(roughness2 + kernelRoughness2)));
    return sigma2 > 0.0 ? filtered : smoothness;                      // select, not a branch
}

// ---------------------------------------------------------------------------------------------------
// world-space 3D value-noise FBM (4 octaves). Same in both eyes (world anchored).
inline float LanbaiVNoise3(float3 p)
{
    float3 i = floor(p);
    float3 f = p - i;
    float3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float n000 = LanbaiHash13(i + float3(0, 0, 0)), n100 = LanbaiHash13(i + float3(1, 0, 0));
    float n010 = LanbaiHash13(i + float3(0, 1, 0)), n110 = LanbaiHash13(i + float3(1, 1, 0));
    float n001 = LanbaiHash13(i + float3(0, 0, 1)), n101 = LanbaiHash13(i + float3(1, 0, 1));
    float n011 = LanbaiHash13(i + float3(0, 1, 1)), n111 = LanbaiHash13(i + float3(1, 1, 1));
    float x00 = lerp(n000, n100, u.x), x10 = lerp(n010, n110, u.x);
    float x01 = lerp(n001, n101, u.x), x11 = lerp(n011, n111, u.x);
    return lerp(lerp(x00, x10, u.y), lerp(x01, x11, u.y), u.z);
}
inline float LanbaiCabinFBM(float3 posWS, float patch)
{
    float3 p = posWS / max(patch, 0.05) + float3(17.3, 5.1, 9.7);   // offset: lattice not aligned with the bus origin
    float s = 0.0, a = 0.5;
    [unroll] for (int k = 0; k < 4; k++)
    {
        s += a * LanbaiVNoise3(p);
        p = p * 2.03 + float3(3.1, 7.7, 1.3);
        a *= 0.5;
    }
    return s / 0.9375;                                               // ~[0, 1], mean 0.5
}

// ---------------------------------------------------------------------------------------------------
// distance to the skylight glass square (in its plane y = _SkyRect.y): 0 on the rim and inside
inline float LanbaiSkyDist(float3 posWS)
{
    float2 q = abs(posWS.xz - _SkyRect.xz) - _SkyRect.ww;
    float dxz = length(max(q, 0.0));
    return length(float2(dxz, posWS.y - _SkyRect.y));
}

// rounded-rectangle signed distance in the floor plane (negative inside)
inline float LanbaiRectSD(float2 p, float2 c, float2 h, float r)
{
    float2 q = abs(p - c) - (h - r);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// D-46 (总导演 10-25, act 7a): the ceiling straight above the hero seat goes first - from the zenith to the skylight's
// near edge, and the roof skin over it - then the hole spreads sideways, so the hero looking up sees the Snell window
// through it (Bus/Source/snell_check.py: 387 s >= 25 %, 446 s >= 35 %, 506 s >= 45 % of the cone, zenith 20 deg >= 30 %).
// Added to tau; only above the ceiling gate (the walls end at y 2.40: seats, stanchions, rails, walls are untouched), and
// only once the fade passes _ErodeZenithRamp.x, so the first hole opens at ~375 s, not at F2h.
inline float LanbaiZenithTerm(float3 posWS, float fade)
{
    float w = saturate((fade - _ErodeZenithRamp.x) / max(_ErodeZenithRamp.y - _ErodeZenithRamp.x, 1e-4));
    float dx = (posWS.x - _ErodeZenith.x) / max(_ErodeZenithShape.y, 0.1);
    float dz = max(max(_ErodeZenith.y - posWS.z, posWS.z - _ErodeZenith.z), 0.0);
    float g = exp(-sqrt(dx * dx + dz * dz) / max(_ErodeZenithShape.x, 0.01));
    return _ErodeZenith.w * w * g * smoothstep(_ErodeZenithShape.z, _ErodeZenithShape.w, posWS.y);
}

// The erosion field. Returns s = noise - tau (s < 0 = removed). With _Udon_CabinFade unset (0) and the hole shut
// every pixel returns a large positive s. 'protectMode' is applied inside: seat sphere, floor patch, D-26 hole.
inline float LanbaiCabinErodeField(float3 posWS, out float nUniform)
{
    float fade = _Udon_CabinFade.x;
    float hN = saturate((posWS.y - _CabinBox.x) / max(_CabinBox.y - _CabinBox.x, 0.1));
    float fN = saturate((posWS.z - _CabinBox.z) / max(_CabinBox.w - _CabinBox.z, 0.1));
    float e = exp(-LanbaiSkyDist(posWS) / max(_ErodeCoef.w, 0.05));
    float frontTerm = _ErodeForm > 0.5 ? fN : 1.0 - fN;
    float skyTerm = _ErodeForm > 0.5 ? e : 1.0 - e;
    float tau = fade - _ErodeCoef.x * (1.0 - hN) - _ErodeCoef.y * frontTerm - _ErodeCoef.z * skyTerm - _FadeResist;
    tau += LanbaiZenithTerm(posWS, fade);                            // D-46
    tau = fade > 0.0 ? tau : -10.0;                                  // fade 0 = nothing, exactly
    // D-33 #7a: the door group (folding leaves, door post, door grab, upper frame, the WinR1 front gasket) goes
    // before 965.4 so Zhuangzi's horizon column is clear. Inside a soft box, tau is pulled toward tau + 1 (+ the
    // stanchion resist back: the door grab does not get it) by _DoorBias - AFTER the protections, so the seat
    // sphere does not hold the door post.
    float3 dq = max(_DoorBoxMin.xyz - posWS, posWS - _DoorBoxMax.xyz);
    float inDoor = 1.0 - smoothstep(0.0, max(_DoorBoxMin.w, 0.01), max(max(dq.x, dq.y), dq.z));
    float tauDoor = tau + 1.0 + _FadeResist;

    // protections (bible §4.8 + §1.8 '休息参照'): seat sphere until the last step, floor patch until act 9
    float seatRelease = saturate((fade - 0.97) / 0.03);              // the 13th mirror: 0.97 -> 1
    float inSphere = 1.0 - smoothstep(_SeatSphere.w - 0.05, _SeatSphere.w, distance(posWS, _SeatSphere.xyz));
    float patchRelease = saturate((fade - 0.65) / 0.027);            // act 9: the first mirror's +0.027
    float2 pc = float2(_FloorPatch.x + _FloorPatch.y, _FloorPatch.z + _FloorPatch.w) * 0.5;
    float2 ph = float2(_FloorPatch.y - _FloorPatch.x, _FloorPatch.w - _FloorPatch.z) * 0.5;
    float inPatch = (LanbaiRectSD(posWS.xz, pc, ph, 0.02) < 0.0 && posWS.y < _CabinBox.x + 0.08) ? 1.0 : 0.0;
    float prot = max(inSphere * (1.0 - seatRelease), inPatch * (1.0 - patchRelease));
    tau = lerp(tau, -10.0, prot);
    tau = fade > 0.0 ? lerp(tau, tauDoor, saturate(_DoorBias) * inDoor) : tau;

    float n = LanbaiCabinFBM(posWS, _ErodeNoise.x);
    nUniform = saturate((n - _ErodeNoise.y) / max(_ErodeNoise.z - _ErodeNoise.y, 1e-3));
    float nr = lerp(_ErodeNoiseRange.x, _ErodeNoiseRange.y, nUniform);
    float s = nr - tau;

    // D-26 (Act07a §9.1): the soft-edged hole in the floor in front of the hero seat, from F8b. It wins over the
    // sphere and the patch (it is the director's later rule). Only surfaces at / below floor height.
    float o = saturate(_HoleOpen);
    if (o > 0.0 && posWS.y < _HoleShape.z)
    {
        float g = saturate(o * 2.0);                                 // 0 -> 0.5: grows to the minimum hole
        float k = saturate(o * 2.0 - 1.0);                           // 0.5 -> 1: minimum -> full
        float2 c = lerp(_HoleMin.xy, _HoleFull.xy, k);
        float2 h = lerp(_HoleMin.zw * g, _HoleFull.zw, k);
        float sd = LanbaiRectSD(posWS.xz, c, max(h, 0.001), min(_HoleShape.x, min(h.x, h.y)));
        sd += (nUniform - 0.5) * 2.0 * _HoleShape.y;                 // soft, eroded edge: never a square hatch
        // the rim below is measured from the gradient of s, so mixing metres and noise units in min() is fine:
        // the hole edge gets the same 3 cm rim as the general erosion
        s = min(s, sd);
    }
    return _ErodeEnable > 0.5 ? s : 10.0;
}

// clip + rim weight (0..1 inside the 3 cm band at the edge). Call from a fragment / surf function.
inline float LanbaiCabinErodeClipRim(float3 posWS)
{
    float nu;
    float s = LanbaiCabinErodeField(posWS, nu);
    clip(s);
    // rim in metres: s / |grad s| (screen-space estimate), band = _ErodeNoise.w (3 cm)
    float gs = length(float2(ddx(s), ddy(s)));
    float gp = length(float2(length(ddx(posWS)), length(ddy(posWS))));
    float dist = s / max(gs / max(gp, 1e-5), 1e-3);
    return 1.0 - smoothstep(0.0, _ErodeNoise.w, dist);
}
// shadow pass: clip only (no derivatives needed)
inline void LanbaiCabinErodeClip(float3 posWS)
{
    float nu;
    clip(LanbaiCabinErodeField(posWS, nu));
}

// ---------------------------------------------------------------------------------------------------
// D-08 / D-21 purple guard in CIE Lab (D65), on LINEAR sRGB colours.
inline float3 LanbaiLinToLab(float3 c)
{
    float3 X = float3(dot(float3(0.4124, 0.3576, 0.1805), c),
                      dot(float3(0.2126, 0.7152, 0.0722), c),
                      dot(float3(0.0193, 0.1192, 0.9505), c)) / float3(0.95047, 1.0, 1.08883);
    X = max(X, 0.0);
    float3 f = X > 0.008856 ? pow(X, 1.0 / 3.0) : 7.787 * X + 16.0 / 116.0;
    return float3(116.0 * f.y - 16.0, 500.0 * (f.x - f.y), 200.0 * (f.y - f.z));
}
inline float3 LanbaiLabToLin(float3 lab)
{
    float fy = (lab.x + 16.0) / 116.0;
    float3 f = float3(fy + lab.y / 500.0, fy, fy - lab.z / 200.0);
    float3 X = f > 0.206893 ? f * f * f : (f - 16.0 / 116.0) / 7.787;
    X *= float3(0.95047, 1.0, 1.08883);
    float3 c = float3(dot(float3(3.2406, -1.5372, -0.4986), X),
                      dot(float3(-0.9689, 1.8758, 0.0415), X),
                      dot(float3(0.0557, -0.2040, 1.0570), X));
    return max(c, 0.0);
}
// D-21 band guard: only when h_ab 290-330 AND C* > 8 AND L* > 40: C* -> 8 (soft 2 deg / 2 L* edges)
inline float3 LanbaiPurpleBand(float3 lab)
{
    float C = length(lab.yz);
    float h = degrees(atan2(lab.z, lab.y));
    h = h < 0.0 ? h + 360.0 : h;
    float w = smoothstep(288.0, 292.0, h) * (1.0 - smoothstep(328.0, 332.0, h)) * smoothstep(38.0, 42.0, lab.x);
    float Ct = lerp(C, min(C, 8.0), w);
    lab.yz *= C > 1e-4 ? Ct / C : 0.0;
    return lab;
}
// D-08 for the WOUND LIGHT's colour itself (scale invariant: evaluated at Y = 0.5): C* <= 12, and a hue inside
// 290-330 is pulled to 290 (D-08 wants h_ab 230-290). #B9B6D6 (C* 17.3, h 295) -> a cold white (C* 12, h 290).
inline float3 LanbaiWoundLightLimit(float3 lightCol)
{
    float Y = dot(float3(0.2126, 0.7152, 0.0722), lightCol);
    if (Y <= 1e-6) return lightCol;
    float3 lab = LanbaiLinToLab(lightCol * (0.5 / Y));
    float C = length(lab.yz);
    float h = degrees(atan2(lab.z, lab.y));
    h = h < 0.0 ? h + 360.0 : h;
    float pull = smoothstep(288.0, 292.0, h) * (1.0 - smoothstep(338.0, 342.0, h));
    float hn = lerp(h, 290.0, pull * saturate((h - 290.0) / 2.0 + 0.5));
    float Cn = min(C, 12.0);
    float r = radians(hn);
    lab.yz = float2(cos(r), sin(r)) * Cn;
    return LanbaiLabToLin(lab) * (Y / 0.5);
}
inline float3 LanbaiPurpleGuardLin(float3 c)
{
    float m = max(c.r, max(c.g, c.b));
    if (m <= 1e-6) return c;
    return LanbaiLabToLin(LanbaiPurpleBand(LanbaiLinToLab(c)));
}

#endif // LANBAI_CABIN_COMMON_INCLUDED
