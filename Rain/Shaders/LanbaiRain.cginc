// =====================================================================================================
//  Lanbai / LanbaiRain.cginc      蓝白 · rain maths shared by WetSurface, PuddleOverlay, BusGlass, OneDrop (bible §1.6, §4.6)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      The implementer compiles it in Unity 2022.3 and checks it in a headset (close one eye, then the other). !!!
//
//  Everything returns SLOPES (d height / d x, d height / d z) in metres per metre, world-anchored. A slope s turns
//  into a normal n = normalize(float3(-s.x, 1, -s.y)) for a horizontal puddle, or (-s.x, -s.y, 1) in tangent space.
//  The numbers (tile sizes, loop, LUT ranges) are the ones the textures were generated with: do not change them
//  without regenerating the textures (Tools~/).
//
//  v2 (after verification round 2): runners rewritten (no headless channels, no pops, distance clock, stopped drops
//  become beads), windscreen wipers, flow frames that cross-fade instead of rotating, two-interface drop optics,
//  drop transmission seen from outside, rings anchored to R_Stop, footprint band-limited ring LUTs.
// =====================================================================================================
#ifndef LANBAI_RAIN_INCLUDED
#define LANBAI_RAIN_INCLUDED

#include "UnityCG.cginc"
#include "LanbaiLamps.cginc"

// ---------------------------------------------------------------------------------------------------
// globals driven by Udon (bible §1.6 / §4.6). Unset -> 0.
// float _Udon_Wetness: declared in LanbaiGlobals.cginc // 0..1 global wetness (Lagarde model)
// float _Udon_RainAmount: declared in LanbaiGlobals.cginc // 0..1 rain on glass (station 1.0, night road 1.0, lift-off 1->0, wake 0.4)
// float4 _Udon_FlowDir: declared in LanbaiGlobals.cginc // flow FRAME A: xyz = WORLD direction of the air drag on drops (= -bus velocity dir
                              //   + up at lift-off), w = drag 0..1
// float4 _Udon_FlowDirB: declared in LanbaiGlobals.cginc // flow frame B (the frame being faded in while the flow changes), same layout
// float _Udon_FlowMix: declared in LanbaiGlobals.cginc // 0 = frame A only, 1 = frame B only; LanbaiRainState snaps A := B when the fade ends
// float4 _Udon_RunClock: declared in LanbaiGlobals.cginc // x = integral of drag dt (s), y = drag averaged over the last ~4 s (0..1)
// float _Udon_RunStretch: declared in LanbaiGlobals.cginc // 0..2 extra elongation of running drops (lift-off: 'drops streak up and back')
// float4 _Udon_StopOffset: declared in LanbaiGlobals.cginc // xyz = R_Stop world position - its home position (treadmill); 0 at home
// float4 _Udon_OneDropA: declared in LanbaiGlobals.cginc // 'that one raindrop': xyz = world start of its path, w = half-width of the swept strip (m)
// float4 _Udon_OneDropB: declared in LanbaiGlobals.cginc // xyz = world position of its head now, w = 1 while the path exists (0 = none / hidden)
// float4 _Udon_Drip0, _Udon_Drip1, _Udon_Drip2, _Udon_Drip3: declared in LanbaiGlobals.cginc // xyz = impact point in R_STOP-LOCAL world space
                              // (world point - _Udon_StopOffset at detach), w = impact time (_Time.y); w <= 0 : none
// windscreen wipers (Runtime/LanbaiWipers.cs). Two blades, tandem (same timing).
// float4 _Udon_WiperPivot0, _Udon_WiperPivot1: declared in LanbaiGlobals.cginc // xyz = pivot (world), w = blade reach r_max (m); w <= 0 : no wiper
// float4 _Udon_WiperRest0, _Udon_WiperRest1: declared in LanbaiGlobals.cginc // xyz = unit direction of the blade at rest (world), w = sweep (rad)
// float4 _Udon_WiperAxis0, _Udon_WiperAxis1: declared in LanbaiGlobals.cginc // xyz = unit rotation axis (rest turns toward +sweep about it), w = r_min (m)
// float4 _Udon_WiperTime: declared in LanbaiGlobals.cginc // x = start time of the latest cycle (_Time.y), y = one stroke (s), z = period (s),
                              // w = 1 if the cycle before it also ran (0 for the first cycle)

// how much of the hero drop's swept path covers P (0..1). Big beads are gone there; the mist stays.
inline float LanbaiOneDropSwept(float3 P)
{
    if (_Udon_OneDropB.w <= 0.0) return 0.0;
    float3 ab = _Udon_OneDropB.xyz - _Udon_OneDropA.xyz;
    float t = saturate(dot(P - _Udon_OneDropA.xyz, ab) / max(dot(ab, ab), 1e-8));
    float d = distance(P, _Udon_OneDropA.xyz + ab * t);
    float w = max(_Udon_OneDropA.w, 1e-4);
    return 1.0 - smoothstep(0.6 * w, w, d);
}

// Dave Hoskins' hash (identical to the numpy reference in Tools~/src/runners_ref.py)
inline float LanbaiHash11(float p)
{
    p = frac(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return frac(p);
}
inline float LanbaiHash21(float2 p)
{
    float3 p3 = frac(float3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return frac((p3.x + p3.y) * p3.z);
}
inline float2 LanbaiHash22(float2 p)
{
    float3 p3 = frac(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return frac((p3.xx + p3.yz) * p3.zy);
}
inline float2 LanbaiRot(float2 v, float s, float c) { return float2(c * v.x - s * v.y, s * v.x + c * v.y); }
inline float LanbaiSStep(float a, float b, float x) { float t = saturate((x - a) / (b - a)); return t * t * (3.0 - 2.0 * t); }

// normal xy from any import: plain RGB / RGBA (w = 1), BC5 (RG, w = 1) or DXT5nm (x in A, R = 1) - like UnityCG's
// UnpackNormalmapRGorAG. Returns the SLOPE (-n.xy / n.z) of the height field.
inline float2 LanbaiSlopeFromNormalTex(float4 t, float minZ)
{
    t.x *= t.w;
    float2 n = t.xy * 2.0 - 1.0;
    float nz = sqrt(saturate(1.0 - dot(n, n)));
    return -n / max(nz, minZ);
}

// where a surface of R_Stop is NOW, expressed at its home position (rings, drips and the wet mask move with it)
inline float3 LanbaiStopLocal(float3 P, float anchorToStop) { return P - _Udon_StopOffset.xyz * anchorToStop; }

// world-space footprint of one pixel (m) on a surface - call OUTSIDE branches
inline float LanbaiFootprint(float3 P) { return max(length(ddx(P)), length(ddy(P))); }

// =====================================================================================================
//  1. RAIN RIPPLES: flipbook  (Textures/Puddle/RainRipple_Flip8x8_2048.png)
//     0.5 m tile, 64 frames, loop 2.0 s (32 fps), 10 drizzle drops per tile per loop.
//     Default: import as a Texture2DArray (Texture Shape = 2D Array, Columns 8, Rows 8). Frame k = slice k.
//     Fallback (#define LANBAI_RIPPLE_ATLAS before including): sample the 2048 atlas with manual cell UVs.
// =====================================================================================================
#define LANBAI_RIPPLE_TILE   0.5
#define LANBAI_RIPPLE_FPS    32.0
#define LANBAI_RIPPLE_FRAMES 64.0

#if defined(LANBAI_RIPPLE_ATLAS)
sampler2D _RippleTex;
inline float2 LanbaiRippleFetch(float2 uv, float frame)
{
    float col = fmod(frame, 8.0);
    float row = floor(frame / 8.0);                       // frame 0 = top-left of the PNG
    float2 cell = float2(col, 7.0 - row);                 // Unity v = 0 at the bottom
    float2 f = frac(uv);
    float2 g = uv / 8.0;                                  // continuous: derivatives do not jump at the wrap
    // clamp the footprint so the mip never reaches across a whole cell (mip <= 3 of a 256 px cell)
    float2 dx = ddx(g), dy = ddy(g);
    float m = max(length(dx), length(dy)) * 2048.0;
    float k = m > 8.0 ? 8.0 / m : 1.0;
    float2 inset = clamp(f, 1.0 / 256.0, 255.0 / 256.0);
    float4 t = tex2Dgrad(_RippleTex, (cell + inset) / 8.0, dx * k, dy * k);
    return LanbaiSlopeFromNormalTex(t, 0.3);
}
#else
UNITY_DECLARE_TEX2DARRAY(_RippleTex);
inline float2 LanbaiRippleFetch(float2 uv, float frame)
{
    float4 t = UNITY_SAMPLE_TEX2DARRAY(_RippleTex, float3(uv, frame));
    return LanbaiSlopeFromNormalTex(t, 0.3);
}
#endif

// p = world XZ (m), t = time (s). layer2 = weight of a second, rotated / rescaled / time-shifted layer
// (breaks the 0.5 m lattice; 1 = double density, 0 = single). Returns world-XZ slope.
inline float2 LanbaiRippleFlipbook(float2 p, float t, float layer2)
{
    float f = t * LANBAI_RIPPLE_FPS;
    float w = frac(f);
    float f0 = fmod(floor(f), LANBAI_RIPPLE_FRAMES);
    float f1 = fmod(f0 + 1.0, LANBAI_RIPPLE_FRAMES);
    float2 uv = p / LANBAI_RIPPLE_TILE;
    float2 s = lerp(LanbaiRippleFetch(uv, f0), LanbaiRippleFetch(uv, f1), w);
    // (no branch on layer2: implicit-derivative samples must stay out of flow control)
    {
        const float sn = 0.6018150, cs = 0.7986355;       // 37 degrees
        float2 p2 = LanbaiRot(p, sn, cs) / (LANBAI_RIPPLE_TILE * 0.73) + float2(0.31, 0.57);
        float g = t * LANBAI_RIPPLE_FPS * 0.93 + 23.0;    // slightly different rate: the pair never re-syncs
        float wg = frac(g);
        float g0 = fmod(floor(g), LANBAI_RIPPLE_FRAMES);
        float g1 = fmod(g0 + 1.0, LANBAI_RIPPLE_FRAMES);
        float2 s2 = lerp(LanbaiRippleFetch(p2, g0), LanbaiRippleFetch(p2, g1), wg);
        s += LanbaiRot(s2, -sn, cs) * layer2;             // rotate the slope back into world XZ
    }
    return s;
}

// =====================================================================================================
//  2. RAIN RIPPLES: procedural cells with the physical ring LUT (bible rate 3-5 /m^2/s; the default)
//     Textures/Puddle/RippleRing_LUT_256x128.png : u = r / 0.25 m, v = age / 1.25 s.
//     R,G = full-band slope (R = slope / gain, G = log2 gain);  B,A = the SAME rings low-passed for a 4 mm pixel
//     footprint (same encoding). The shader blends by the pixel's footprint: fresh impacts no longer alias into a
//     moire disc / sparkle in VR. Each 0.6 m cell fires at most once per 1.25 s at a random point; two offset layers.
// =====================================================================================================
sampler2D _RippleRingLUT;
#define LANBAI_RING_RMAX 0.25
#define LANBAI_RING_TMAX 1.25
#define LANBAI_RING_CELL 0.6

// bl = 0 full band .. 1 band-limited (from LanbaiRingBand(footprint))
inline float2 LanbaiRingLUT(sampler2D lut, float2 d, float age, float rMax, float tMax, float2 texSize, float amp, float bl)
{
    float r = length(d);
    if (r >= rMax || age <= 0.0 || age >= tMax) return 0;
    float2 uv = float2(r / rMax, age / tMax) * (texSize - 1.0) / texSize + 0.5 / texSize;
    float4 L = tex2Dlod(lut, float4(uv, 0, 0));
    float sFull = (L.r * 2.0 - 1.0) * exp2(L.g * 14.0 - 12.0);
    float sLow = (L.b * 2.0 - 1.0) * exp2(L.a * 14.0 - 12.0);
    float s = lerp(sFull, sLow, bl) * amp;
    return s * d / max(r, 1e-5);
}
// footprint (m / pixel) -> blend toward the band-limited rows. The full band carries capillary detail up to
// k ~ 2600 rad/m, which a pixel coarser than ~1 mm can no longer hold (it sparkles), so: full detail up to 0.8 mm,
// fully band-limited from 1.8 mm (seated VR at 2 m sees ~2-3 mm along the view).
inline float LanbaiRingBand(float footprint) { return saturate((footprint - 0.0008) / 0.0010); }

// density = ripples per m^2 per s (<= ~4.4 with two layers), returns world-XZ slope
inline float2 LanbaiRippleCells(float2 p, float t, float density, float bl)
{
    float2 s = 0;
    float pFire = saturate(density * LANBAI_RING_CELL * LANBAI_RING_CELL * LANBAI_RING_TMAX * 0.5);   // per layer
    [unroll] for (int layer = 0; layer < 2; layer++)
    {
        float2 off = layer * float2(0.5, 0.5);
        float2 q = p / LANBAI_RING_CELL + off;
        float2 base = floor(q - 0.5);
        [unroll] for (int j = 0; j < 2; j++)
        [unroll] for (int i = 0; i < 2; i++)
        {
            float2 cell = base + float2(i, j);
            float2 cid = cell + layer * 97.0;
            float ph = LanbaiHash21(cid * 0.713 + 5.1);
            float tt = t / LANBAI_RING_TMAX + ph;
            float n = floor(tt);
            float age = frac(tt) * LANBAI_RING_TMAX;
            float fire = step(LanbaiHash21(cid * 1.371 + n * 0.6180339), pFire);
            float2 c = cell + LanbaiHash22(cid + n * 0.7548777);            // anywhere in the cell
            float sz = 0.8 + 0.4 * LanbaiHash11(dot(cid, float2(0.37, 0.61)) + n);
            float2 d = (q - c) * LANBAI_RING_CELL / sz;                       // metres, rescaled by drop size
            s += fire * LanbaiRingLUT(_RippleRingLUT, d, age, LANBAI_RING_RMAX, LANBAI_RING_TMAX, float2(256, 128), pow(sz, 1.5), bl);
        }
    }
    return s;
}

// =====================================================================================================
//  3. DRIP RINGS (lamp arm, sign edge, notice-case roof; bible §5.4 / §5.5 / §6·12)
//     Textures/Puddle/DripRipple_LUT_512x256.png : r 0..0.5 m, age 0..2.5 s, same 4-channel encoding.
//     A 4.5 mm drip from 2-4 m: main ring 0.4 m at 1.6 s, disturbance tau ~0.7 s, flat by 2.5 s.
//     Pl = the surface point in R_Stop-local world space (LanbaiStopLocal), like the stored impacts.
// =====================================================================================================
sampler2D _DripRippleLUT;
inline float2 LanbaiDripOne(float4 drip, float3 Pl, float t, float bl)
{
    if (drip.w <= 0.0) return 0;
    if (abs(Pl.y - drip.y) > 0.02) return 0;              // only on the surface the drop hit (fallHeight to +-1 cm)
    return LanbaiRingLUT(_DripRippleLUT, Pl.xz - drip.xz, t - drip.w, 0.5, 2.5, float2(512, 256), 1.0, bl);
}
inline float2 LanbaiDripRipples(float3 Pl, float t, float bl)
{
    return LanbaiDripOne(_Udon_Drip0, Pl, t, bl) + LanbaiDripOne(_Udon_Drip1, Pl, t, bl)
         + LanbaiDripOne(_Udon_Drip2, Pl, t, bl) + LanbaiDripOne(_Udon_Drip3, Pl, t, bl);
}

// =====================================================================================================
//  4. RAIN ON GLASS (bible §4.6): static beads + drops running in lanes + wipers
//     Textures/Glass/RainBeads_Vertical_Normal_1024 / _Data_1024 : 0.20 m tile.
//        Data R = thickness / 2.5 mm, G = persistence (bead visible while rainAmount > G), B = coverage,
//        A = contact radius / 3 mm.
//     Textures/Glass/GlassRunners_Flow_512x1024 : 0.20 x 0.40 m tile; drops run toward -v.
//        R = lane offset (0.5 + dx / 5 mm), G = lane id, B = path slope, A = lane mask.
//     Port of Tools~/src/runners_ref.py (numpy) - keep the two in sync, line for line.
// =====================================================================================================
sampler2D _BeadNormal;
sampler2D _BeadData;
sampler2D _RunnerFlow;

#define LANBAI_RUN_TU 0.20
#define LANBAI_RUN_TV 0.40
#define LANBAI_RUN_W  0.005
#define LANBAI_RUN_CUT 0.07          // the lane lattice is cut at u = 0.93, where no lane runs
#define LANBAI_RUN_FS1MAX 0.97       // a drop always stops >= 12 mm above its tile's lower edge
#define LANBAI_CAP_S2 0.6710101      // sin^2(55 deg)
#define LANBAI_CAP_C  0.5735765      // cos(55 deg)
#define LANBAI_CAP_HK 0.5205671      // (1 - cos) / sin

struct LanbaiRunOut { float2 slope; float h; float clear; };

// spherical cap (55 deg contact angle) stretched into a runner; returns (h, dh/d across, dh/d along, rho2)
inline float4 LanbaiCap(float across, float along, float a, float af, float at)
{
    float ad = along < 0.0 ? af : at;
    float rho2 = (across / a) * (across / a) + (along / ad) * (along / ad);
    float q = sqrt(max(1.0 - rho2 * LANBAI_CAP_S2, 1e-4));
    float inside = step(rho2, 1.0);
    float hmax = a * LANBAI_CAP_HK;
    float h = hmax * (q - LANBAI_CAP_C) / (1.0 - LANBAI_CAP_C) * inside;
    float dh = hmax * (-LANBAI_CAP_S2 / (2.0 * q)) / (1.0 - LANBAI_CAP_C) * inside;   // dh / d(rho2)
    return float4(h, dh * 2.0 * across / (a * a), dh * 2.0 * along / (ad * ad), rho2);
}

// q = runner-space position (m): drops move toward -y.
// dist = DISTANCE clock (m slid by a reference drop of this layer, integrated by Udon: speed changes never make heads
// jump); vAvg = that speed averaged over the last seconds (m/s; only converts distances into ages).
// bo = runner-space offset (m) from this pixel to the centre of the static bead under it (LanbaiBeadCentre): the CLEAR
// mask is evaluated there, so a runner takes a bead whole or leaves it whole - it never slices one in half.
inline LanbaiRunOut LanbaiRunners(float2 q, float dist, float vAvg, float density, float size, float stretch,
                                  float stickslip, float trailLife, float seedOff, float2 bo)
{
    LanbaiRunOut o; o.slope = 0; o.h = 0; o.clear = 0;
    float2 uv = float2(q.x / LANBAI_RUN_TU, q.y / LANBAI_RUN_TV);
    float4 f = tex2Dlod(_RunnerFlow, float4(uv, 0, 0));
    if (f.a < 0.002) return o;
    float dx = (f.r * 2.0 - 1.0) * LANBAI_RUN_W;                         // this pixel's offset from its lane centre
    // every repeat of the lane lattice gets its own identity (timing, size, speed); column taken at the lane CENTRE
    float2 tid = float2(floor(uv.x - dx / LANBAI_RUN_TU + LANBAI_RUN_CUT), floor(uv.y));
    float lane = f.g + seedOff + LanbaiHash21(float2(tid.x * 1.618 + seedOff * 3.7, tid.y * 2.414 + 0.5)) * 9.0;
    float h1 = LanbaiHash11(lane * 113.7 + 0.1);
    float h2 = LanbaiHash11(lane * 71.3 + 0.7);
    float h3 = LanbaiHash11(lane * 37.9 + 0.3);
    float h4 = LanbaiHash11(lane * 53.1 + 0.9);
    float lf = 0.55 + 0.9 * h1;                                           // this lane's speed factor
    float spd = max(lf * vAvg, 1e-4) / LANBAI_RUN_TV;                     // tile units / s (for ages)
    float lam = 0.012 + 0.028 * h2;                                       // stick-slip: a pinning site every 1.2-4 cm
    float w = 6.2831853 / lam;
    float dw = dist + stickslip * 0.9 / w * sin(w * dist + 6.2832 * h3);  // positional stick-slip, monotonic in dist
    float inst = 1.0 + stickslip * 0.9 * cos(w * dist + 6.2832 * h3);     // instantaneous speed / mean
    float s = h4 + lf * dw / LANBAI_RUN_TV;
    float cyc = floor(s);
    float fs = s - cyc;
    float y = uv.y - tid.y;                                               // 0..1 inside this tile, 1 = top
    float pth = f.b * 2.0 - 1.0;
    float ca = rsqrt(1.0 + pth * pth);
    float across = dx * ca;
    float acrossC = (dx + bo.x - pth * bo.y) * ca;                        // at the bead's centre (clear mask only)
    float yC = y + bo.y / LANBAI_RUN_TV;
    float tl = min(trailLife * 1.5, 0.75 / spd);                          // channel refill time (s), < the bead's hold
    float tp = min(trailLife * 3.0, 0.97 / spd);                          // residue pearls last longer
    float headNewPh = 0.0, actNew = 0.0;
    float2 gsum = 0;
    // pass 1: heads and channels of both cycles (kept in small arrays for pass 2)
    float kA[2], kAlong[2], kBehind[2], kAge[2], kAct[2], kCc[2], kGA[2], kGL[2], kHead[2];
    [unroll] for (int k = 0; k < 2; k++)                                   // 0 = this cycle, 1 = the previous one
    {
        float cc = cyc - k;
        float p = fs + k;                                                 // phase within cycle cc (>= 1: it has ended)
        float c1 = LanbaiHash11(lane * 19.19 + cc * 0.6180339);
        float c2 = LanbaiHash11(lane * 7.77 + cc * 0.4142136);
        float c3 = LanbaiHash11(c1 * 3.1 + c2);
        float act = saturate((density - c1) / 0.08);
        float fs0 = 0.02 + 0.48 * c2;
        float fs1 = min(LANBAI_RUN_FS1MAX, fs0 + 0.45 + 0.5 * c3);
        float ph = min(p, fs1);                                           // head phase (frozen after fs1)
        float moving = p < fs1 ? 1.0 : 0.0;
        float grow = LanbaiSStep(fs0, fs0 + 0.06, p);
        float tpost = max(p - fs1, 0.0) / spd;                            // s since it stopped
        float hold = 1.0 - LanbaiSStep(0.75 / spd, 1.00 / spd, tpost);    // stopped bead holds, then evaporates
        float merged = 1.0;
        if (k == 1) merged = 1.0 - (headNewPh >= fs1 - 0.01 ? 1.0 : 0.0) * actNew;   // the new head swallows it
        float vh = 1.0 - ph;
        float along = (y - vh) * LANBAI_RUN_TV;                           // + = behind (above) the head
        float a = size * (0.8 + 0.4 * h3) * (0.6 + 0.4 * grow) * (1.0 - 0.35 * LanbaiSStep(0.0, 1.5, tpost));
        a = max(a, 1e-5);
        float af = a * 0.9;
        float at = a * (1.0 + moving * (0.25 + stretch + 0.35 * clamp(inst, 0.0, 2.0)));
        float4 cp = LanbaiCap(across, along, a, af, at);
        float life = grow * hold * act * merged * f.a;
        // channel: from the start (fs0) down to just behind the head, refilled by the time since the head passed
        float fp = 1.0 - y;                                               // phase at which the head passed this row
        float seen = LanbaiSStep(fs0, fs0 + 0.01, fp);
        float behind = LanbaiSStep(at * 0.3, at, along) * seen * (fp <= ph ? 1.0 : 0.0);
        float age = max(p - fp, 0.0) / spd;
        // the channel and the head evaluated at the centre of the bead under this pixel: whole beads go
        float alongC = (yC - vh) * LANBAI_RUN_TV;
        float fpC = 1.0 - yC;
        float behindC = LanbaiSStep(at * 0.3, at, alongC) * LanbaiSStep(fs0, fs0 + 0.01, fpC) * (fpC <= ph ? 1.0 : 0.0);
        float fadeC = 1.0 - LanbaiSStep(0.0, tl, max(p - fpC, 0.0) / spd);
        float trailC = behindC * (1.0 - LanbaiSStep(a * 0.7, a * 1.05, abs(acrossC))) * fadeC * act * f.a;
        float adC = alongC < 0.0 ? af : at;
        float rho2C = (acrossC / a) * (acrossC / a) + (alongC / adC) * (alongC / adC);
        o.h = max(o.h, cp.x * life);
        float headClear = saturate((1.35 - rho2C) / 0.35) * life;
        o.clear = max(o.clear, max(saturate(trailC * 2.0), headClear));
        kA[k] = a; kAlong[k] = along; kBehind[k] = behind; kAge[k] = age; kAct[k] = act; kCc[k] = cc;
        kGA[k] = cp.y * life; kGL[k] = cp.z * life; kHead[k] = (cp.w < 1.15 ? 1.0 : 0.0) * life;
        if (k == 0) { headNewPh = ph; actNew = act * (p >= fs0 ? 1.0 : 0.0); }
    }
    float noHead = 1.0 - saturate(max(kHead[0], kHead[1]));
    // pass 2: residue pearls (one per 1.6 mm cell along the path, radius 0.10-0.30 mm), never inside a head
    [unroll] for (int m = 0; m < 2; m++)
    {
        const float DL = 0.0016;
        float along = kAlong[m], a = kA[m];
        float kk = floor(along / DL + 0.5);
        float r1 = LanbaiHash11(lane * 91.7 + kk * 0.7548777 + kCc[m] * 0.31);
        float r2 = LanbaiHash11(lane * 13.3 + kk * 0.5698403);
        float r3 = LanbaiHash11(r1 * 7.1 + r2);
        float pcl = (kk + (r1 - 0.5) * 0.4) * DL;
        float pca = (r2 - 0.5) * 0.7 * a;
        float pr = 0.00010 + 0.00020 * r3 * r3;
        float pd2 = ((along - pcl) * (along - pcl) + (across - pca) * (across - pca)) / (pr * pr);
        float pin = (pd2 < 1.0 ? 1.0 : 0.0) * kBehind[m] * (r3 > 0.25 ? 1.0 : 0.0) * (1.0 - LanbaiSStep(0.0, tp, kAge[m])) * kAct[m] * f.a * noHead;
        float pq = sqrt(max(1.0 - pd2 * LANBAI_CAP_S2, 1e-4));
        float phh = pr * LANBAI_CAP_HK * (pq - LANBAI_CAP_C) / (1.0 - LANBAI_CAP_C) * pin;
        float pdh = pr * LANBAI_CAP_HK * (-LANBAI_CAP_S2 / (2.0 * pq)) / (1.0 - LANBAI_CAP_C) * pin;
        float gA = kGA[m] + pdh * 2.0 * (across - pca) / (pr * pr);
        float gL = kGL[m] + pdh * 2.0 * (along - pcl) / (pr * pr);
        gsum += float2(gA * ca, gL - gA * pth * ca);
        o.h = max(o.h, phh);
    }
    o.slope = gsum;
    return o;
}

// ---------------------------------------------------------------------------------------------------
// wipers: seconds since a blade last passed P (1e4 = never), and the water line pushed ahead of the moving blade
// as a slope in the pane's tangent frame (T, Bt). The blade rubber is taken as 8 mm wide, centred on its arm line.
struct LanbaiWipe { float since; float2 slope; float h; };

inline LanbaiWipe LanbaiWiperOne(float4 piv, float4 rest, float4 axis, float3 P, float3 T, float3 Bt, float t)
{
    LanbaiWipe o; o.since = 1e4; o.slope = 0; o.h = 0;
    if (piv.w <= 0.0 || rest.w <= 0.0) return o;
    float3 v = P - piv.xyz;
    float3 e1 = rest.xyz;
    float3 e2 = normalize(cross(axis.xyz, rest.xyz));
    float x = dot(v, e1), yy = dot(v, e2);
    float r = sqrt(x * x + yy * yy);
    if (r < axis.w || r > piv.w) return o;
    float phi = atan2(yy, x);                                             // 0 at rest, + toward the sweep
    float sweep = rest.w;
    if (phi < -0.03 || phi > sweep + 0.03) return o;
    float Th = max(_Udon_WiperTime.y, 0.05);
    float per = max(_Udon_WiperTime.z, 2.0 * Th + 0.1);
    float tau = t - _Udon_WiperTime.x;                                    // time into the latest cycle
    float u = saturate(phi / sweep);
    float tOut = Th * acos(1.0 - 2.0 * u) / UNITY_PI;                     // theta(tau) = sweep (1 - cos(pi tau / Th)) / 2
    float tBack = 2.0 * Th - tOut;
    if (tau >= tBack) o.since = tau - tBack;
    else if (tau >= tOut) o.since = tau - tOut;
    else if (_Udon_WiperTime.w > 0.5) o.since = tau + per - tBack;        // the previous cycle's return stroke
    // the water line ahead of the moving blade
    if (tau > 0.0 && tau < 2.0 * Th)
    {
        float th = tau < Th ? sweep * (0.5 - 0.5 * cos(UNITY_PI * tau / Th))
                            : sweep * (0.5 + 0.5 * cos(UNITY_PI * (tau - Th) / Th));
        float dir = tau < Th ? 1.0 : -1.0;
        float omega = sweep * 0.5 * UNITY_PI / Th * sin(UNITY_PI * frac(tau / Th));   // |d theta / d tau|
        float d = (phi - th) * dir * r - 0.004;                           // metres ahead of the rubber edge
        float amp = 0.00035 * saturate(omega * r / 0.6);                  // the faster the blade, the more water
        float g = d / 0.0012;
        o.h = amp * exp(-g * g) * (d > -0.002 ? 1.0 : 0.0);
        float dhdd = -2.0 * g / 0.0012 * o.h;
        float3 ephi = -sin(phi) * e1 + cos(phi) * e2;                     // direction of increasing phi
        float3 grad = dhdd * dir * ephi;
        o.slope = float2(dot(grad, T), dot(grad, Bt));
    }
    return o;
}
inline LanbaiWipe LanbaiWipers(float3 P, float3 T, float3 Bt, float t)
{
    LanbaiWipe a = LanbaiWiperOne(_Udon_WiperPivot0, _Udon_WiperRest0, _Udon_WiperAxis0, P, T, Bt, t);
    LanbaiWipe b = LanbaiWiperOne(_Udon_WiperPivot1, _Udon_WiperRest1, _Udon_WiperAxis1, P, T, Bt, t);
    LanbaiWipe o;
    o.since = min(a.since, b.since);
    o.slope = a.slope + b.slope;
    o.h = max(a.h, b.h);
    return o;
}

struct LanbaiGlassWater
{
    float2 slope;     // pane tangent space (x = tangent, y = bitangent), dh/dx
    float thick;      // water thickness (m) - lens strength / absorption
    float cover;      // 0..1 how much of this pixel is water (drives the drop's opacity)
};

struct LanbaiRunParams
{
    float distA, vAvgA;     // distance clock and mean speed of layer A (layer B derives its own)
    float density, size, stretch, stickslip, trailLife;
};

// both runner layers in one flow frame (flowT = unit flow direction in pane axes; bOff = pane offset to the bead centre)
inline LanbaiRunOut LanbaiRunFrame(float2 pPane, float2 flowT, LanbaiRunParams rp, float2 bOff)
{
    float2 axV = -flowT;
    float2 axU = float2(axV.y, -axV.x);
    float2 pr = float2(dot(pPane, axU), dot(pPane, axV));
    float2 bo = float2(dot(bOff, axU), dot(bOff, axV));
    LanbaiRunOut A = LanbaiRunners(pr, rp.distA, rp.vAvgA, rp.density, rp.size, rp.stretch, rp.stickslip, rp.trailLife, 0.0, bo);
    LanbaiRunOut B = LanbaiRunners(pr / 0.83 + float2(0.071, 0.137), rp.distA / 0.83 + 7.3, rp.vAvgA / 0.83, rp.density,
                                   rp.size / 0.83, rp.stretch, rp.stickslip, rp.trailLife, 0.5, bo / 0.83);
    LanbaiRunOut o;
    float2 rs = A.slope + B.slope;
    o.slope = rs.x * axU + rs.y * axV;
    o.h = max(A.h, B.h * 0.83);
    o.clear = max(A.clear, B.clear);
    return o;
}

// the centre of the static bead under this pixel, as an offset in pane metres. For a spherical cap of contact radius
// a and contact angle th (sphere radius R = a / sin th): c - P = grad h * R / sqrt(1 + |grad h|^2). The beads' contact
// angles are 35-54 deg (sin ~0.707); zero off the beads, never further than a. Used so that runners and the one
// drop's swept strip take a bead WHOLE instead of slicing it along a straight edge.
inline float2 LanbaiBeadCentre(float2 bslope, float4 bd)
{
    float a = bd.a * 0.003;
    float2 off = bslope * (a / 0.707) * rsqrt(1.0 + dot(bslope, bslope));
    float l = length(off);
    off *= min(1.0, a / max(l, 1e-9));
    return bd.b > 0.5 ? off : float2(0, 0);
}

// pPane : position on the pane in metres (tangent / bitangent axes); flowA / flowB : unit flow directions of the two
// flow frames in the same axes, mix = weight of B (0 = A only; the frames cross-fade instead of rotating, so trails
// never swing about the pane's pivot); rainAmount 0..1 (= the AREA of beads left); beadTile m (0.20 default);
// Pw, Tw, Bw: world position and the pane's tangent / bitangent ('that one raindrop's swept strip is evaluated at each
// bead's centre); wipeSince: seconds since a wiper blade passed (1e4 = never), wipeRefill: s for the beads to come
// back. dBx, dBy = ddx / ddy of (pPane / beadTile), taken OUTSIDE any branch by the caller.
inline LanbaiGlassWater LanbaiGlassRain(float2 pPane, float2 dBx, float2 dBy, float2 flowA, float2 flowB, float fmix,
                                        float rainAmount, float beadTile, LanbaiRunParams rp, float3 Pw, float3 Tw,
                                        float3 Bw, float wipeSince, float wipeRefill)
{
    LanbaiGlassWater o;
    float2 buv = pPane / beadTile;
    float4 bn = tex2Dgrad(_BeadNormal, buv, dBx, dBy);
    float4 bd = tex2Dgrad(_BeadData, buv, dBx, dBy);
    float2 bslope = LanbaiSlopeFromNormalTex(bn, 0.2);
    float2 bOff = LanbaiBeadCentre(bslope, bd);
    float extraClear = LanbaiOneDropSwept(Pw + Tw * bOff.x + Bw * bOff.y);
    // a wiped pane gets its beads back one by one (each bead's persistence G staggers it) over wipeRefill seconds
    float refill = saturate(wipeSince / max(wipeRefill, 0.1));
    float vis = saturate((rainAmount * refill - bd.g) * 12.0);
    float runKeep = saturate((wipeSince - 0.4) / 1.6);                    // runners re-form after the beads

    LanbaiRunOut R = (LanbaiRunOut)0;
    [branch] if (fmix < 0.999)
    {
        LanbaiRunOut a = LanbaiRunFrame(pPane, flowA, rp, bOff);
        R.slope = a.slope * (1.0 - fmix); R.h = a.h * (1.0 - fmix); R.clear = a.clear * (1.0 - fmix);
    }
    [branch] if (fmix > 0.001)
    {
        LanbaiRunOut b = LanbaiRunFrame(pPane, flowB, rp, bOff);
        R.slope += b.slope * fmix; R.h = max(R.h, b.h * fmix); R.clear = max(R.clear, b.clear * fmix);
    }
    float big = saturate((bd.a - 0.10) / 0.05);               // trails sweep the beads, keep the mist
    float keep = vis * (1.0 - max(R.clear * runKeep, extraClear) * big);
    float ramt = rainAmount * runKeep;
    o.slope = bslope * keep + R.slope * ramt;
    o.thick = bd.r * 0.0025 * keep + R.h * ramt;
    o.cover = saturate(bd.b * keep + step(1e-6, R.h) * ramt);
    return o;
}

// =====================================================================================================
//  5. DROP OPTICS (bible §4.6: "每滴用折射向量查 _Udon_ReflCube + 宽瓣解析灯", no GrabPass)
//     I : unit view ray (eye -> surface), Nd : unit drop normal pointing OUT of the water into the air,
//     Np : unit normal of the PANE pointing OUT of the bus (toward the rain side),
//     viewerInside: the drop sits on the far side of the glass (you look out through it).
//     Inside -> out: the ray crosses the flat glass into the water (flat parallel layers: air -> water at the pane),
//     then leaves through the curved drop surface into the air (TIR possible only there).
//     Returns the radiance the drop shows (linear) for viewerInside; see LanbaiDropOutside for the other side.
// =====================================================================================================
// samplerCUBE _Udon_ReflCube: declared in LanbaiGlobals.cginc (one type for the whole film, as the sea reads it)
// float4 _Udon_ReflCube_HDR: declared in LanbaiGlobals.cginc
// float _Udon_ReflExposure: declared in LanbaiGlobals.cginc // multiplier for the cube (Udon; 0 -> treated as 1)

inline float3 LanbaiReflCube(float3 dir, float lod)
{
    float4 c = texCUBElod(_Udon_ReflCube, float4(dir, lod));
    float e = _Udon_ReflExposure > 0.0 ? _Udon_ReflExposure : 1.0;
    return DecodeHDR(c, _Udon_ReflCube_HDR) * e;
}

// the refracted ray that leaves a drop on the far side of the pane (zero vector = total internal reflection)
inline float3 LanbaiDropExit(float3 I, float3 Np, float3 Nd)
{
    float3 Iw = refract(I, -Np, 1.0 / 1.333);       // cabin air -> (glass) -> water across the flat pane
    return refract(Iw, -Nd, 1.333);                 // water -> air through the curved drop surface
}

inline float3 LanbaiDropRadiance(float3 P, float3 I, float3 Np, float3 Nd, float3 insideColour, float glintLobe)
{
    float3 t = LanbaiDropExit(I, Np, Nd);
    if (dot(t, t) < 1e-4)
    {
        // total internal reflection at the rim: the ray goes back into the cabin -> the cabin's own colour
        return insideColour * 0.6;
    }
    t = normalize(t);
    return LanbaiReflCube(t, 1.0) + LanbaiLampGlints(P, t, glintLobe);
}

// a drop seen from OUTSIDE (bus windows from the stop, the notice-case glass): mostly TRANSMISSIVE. It reflects F of
// the world and lets (1 - F) of what is behind the glass through; only its steep rim refracts light from elsewhere
// (darker), so the rim takes rimDark of the background away and puts behindRim (the colour seen there) instead.
// Returns premultiplied (rgb, alpha) to composite OVER what lies behind: out = rgb + dst * (1 - alpha).
inline float4 LanbaiDropOutside(float3 P, float3 I, float3 Np, float3 Nd, float3 behindRim, float glintLobe)
{
    float c = saturate(dot(-I, Nd));
    float F = 0.02 + 0.98 * pow(1.0 - c, 5.0);
    float3 r = reflect(I, Nd);
    float3 refl = LanbaiReflCube(r, 0.5) + LanbaiLampGlints(P, r, glintLobe * 2.0);
    float tilt = sqrt(saturate(1.0 - dot(Nd, Np) * dot(Nd, Np)));         // sin of the surface tilt
    float rimDark = LanbaiSStep(0.45, 0.85, tilt) * 0.55;
    float aT = F + (1.0 - F) * rimDark;
    return float4(refl * F + behindRim * (1.0 - F) * rimDark, aT);
}

#endif
