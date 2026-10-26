// =====================================================================================================
//  Lanbai / LanbaiCloudVolume.cginc   (gate clouds kit, D-44 #3, 2026-10-25)
//  !!! WRITTEN WITHOUT A UNITY COMPILER; checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//
//  The volume cloud under the gate (阿白's Lanbai/Local/VolumeCloudDeck, FullPreview 20261025-0103) and the arms that
//  stand in it, sharing ONE density:
//    * LanbaiCloudShape    = 阿白's density() without _Density and the comfort cut (same envelope, threshold, texture
//                            coordinates; the cloud package's shared version should call this, or keep it identical);
//    * LanbaiGateSkirt*    = the cloud gathering round every arm that pierces it (a soft billowy collar, up to 8 arms,
//                            positions from the gate clouds driver every frame); the deck takes max(shape, skirt);
//    * LanbaiCloudDensityAt / LanbaiCloudLitAt = the same density (+ skirts, + the comfort cut) and the deck's own lit
//                            colour at a point, for the ARMS (Lanbai/TentacleSway v2.8 wets its surface toward that colour
//                            by the cloud around it, so an arm going into the cloud has no contrast edge to show).
//
//  Globals (requested in GateClouds/给总控.md for Common/UdonGlobals.md; declared here behind the LanbaiGlobals guards,
//  so the generated LanbaiGlobals.cginc can take them over without a double declaration):
//    _Udon_CloudVolume      x = 1 set (the volume cloud is the gate's deck), y = extinction / m (0.036),
//                           z = horizontal period m (520), w = vertical period m (260)
//    _Udon_CloudVolumeWind  xy = wind m/s (8, 3) (with _Udon_GateTime, as the deck)
//    _Udon_CloudVolumeTex   the 128^3 density volume (R, G), the deck material's _NoiseVolume
//    _Udon_GateSkirt0..7    x, z = where the arm's axis crosses the cloud (world), y = strength 0..1 (the arm's reveal),
//                           w = its radius there (m; 0 = off)
//    _Udon_GateSkirtK       x = count (0..8), y = width x radius, z = climb above the top at the arm (m), w = strength
//  All written by LanbaiGateClouds (GateClouds/Runtime) inside the gate window; outside it x / count = 0.
// =====================================================================================================
#ifndef LANBAI_CLOUD_VOLUME_INCLUDED
#define LANBAI_CLOUD_VOLUME_INCLUDED
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"     // _Udon_TearFoot, _Udon_GateTime, ... (guarded)

#ifndef LANBAI_DECL__Udon_CloudVolume
#define LANBAI_DECL__Udon_CloudVolume
float4 _Udon_CloudVolume;
#endif
#ifndef LANBAI_DECL__Udon_CloudVolumeWind
#define LANBAI_DECL__Udon_CloudVolumeWind
float4 _Udon_CloudVolumeWind;
#endif
#ifndef LANBAI_DECL__Udon_CloudVolumeTex
#define LANBAI_DECL__Udon_CloudVolumeTex
sampler3D _Udon_CloudVolumeTex;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt0
#define LANBAI_DECL__Udon_GateSkirt0
float4 _Udon_GateSkirt0;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt1
#define LANBAI_DECL__Udon_GateSkirt1
float4 _Udon_GateSkirt1;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt2
#define LANBAI_DECL__Udon_GateSkirt2
float4 _Udon_GateSkirt2;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt3
#define LANBAI_DECL__Udon_GateSkirt3
float4 _Udon_GateSkirt3;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt4
#define LANBAI_DECL__Udon_GateSkirt4
float4 _Udon_GateSkirt4;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt5
#define LANBAI_DECL__Udon_GateSkirt5
float4 _Udon_GateSkirt5;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt6
#define LANBAI_DECL__Udon_GateSkirt6
float4 _Udon_GateSkirt6;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirt7
#define LANBAI_DECL__Udon_GateSkirt7
float4 _Udon_GateSkirt7;
#endif
#ifndef LANBAI_DECL__Udon_GateSkirtK
#define LANBAI_DECL__Udon_GateSkirtK
float4 _Udon_GateSkirtK;
#endif

// the skirt's fixed shape (seam_ref.py NEW: SkirtWmin, SkirtBase, SkirtSoft)
#define LANBAI_SKIRT_WMIN 22.0      // the collar is at least this wide (m) past the arm's surface (1/e)
#define LANBAI_SKIRT_BASE -24.0     // the collar's top far from the arm, relative to the cloud top (m)
#define LANBAI_SKIRT_SOFT 18.0      // its soft top (m)
#define LANBAI_SKIRT_LUMP 40.0      // its top rides the finer noise (G, 16-32 m cells) x this (m): lumpy, not a dome

// 阿白's density() shape: envelope (top - 170 .. top + 30) x the thresholded noise; nrg = the noise (R, G; the skirt)
float LanbaiCloudShape(sampler3D vol, float3 p, float top, float3 origin, float2 wind, float time, float2 period, out float2 nrg)
{
    float y = (p.y - (top - 170.0)) / 200.0;
    float envelope = smoothstep(0.0, 0.16, y) * (1.0 - smoothstep(0.9, 1.0, y));
    float2 xz = p.xz - origin.xz - wind * time;
    float3 uv = float3(xz.x / period.x, xz.y / period.x, (p.y - top) / period.y);
    float2 n = tex3Dlod(vol, float4(uv, 0)).rg;
    float threshold = lerp(0.14, 0.86, saturate(y));
    nrg = n;
    return smoothstep(threshold, threshold + 0.12, n.r - 0.10 * (n.g - 0.5)) * envelope;
}

float4 LanbaiGateSkirtGet(int i)
{
    return i == 0 ? _Udon_GateSkirt0 : i == 1 ? _Udon_GateSkirt1 : i == 2 ? _Udon_GateSkirt2 : i == 3 ? _Udon_GateSkirt3 :
           i == 4 ? _Udon_GateSkirt4 : i == 5 ? _Udon_GateSkirt5 : i == 6 ? _Udon_GateSkirt6 : _Udon_GateSkirt7;
}

// one collar: g = exp(-(d - r) / W) past the arm's surface; its top climbs from BASE (far) to BASE + climb (at the arm),
// lumpy with the deck's finer noise, soft over SOFT m; filled down to the deck's floor; billowy (no smooth torus)
float LanbaiGateSkirtOne(float3 p, float top, float2 nrg, float4 s)
{
    float d = length(p.xz - s.xz);
    float W = max(LANBAI_SKIRT_WMIN, _Udon_GateSkirtK.y * s.w);
    float x = max(d - s.w, 0.0) / W;
    if (x > 3.0) return 0.0;                        // past 3 W: one compare for most steps of a ray
    float g = exp(-x) * saturate((3.0 - x) * 2.0);  // tapered to 0 over the last half W (no ring at the cut)
    float skTop = top + LANBAI_SKIRT_BASE + _Udon_GateSkirtK.z * g + (nrg.y - 0.5) * LANBAI_SKIRT_LUMP;
    float v = smoothstep(skTop, skTop - LANBAI_SKIRT_SOFT, p.y) * smoothstep(top - 170.0, top - 120.0, p.y);
    float billow = smoothstep(0.30, 0.55, nrg.y + 0.25 * g);
    return _Udon_GateSkirtK.w * saturate(s.y) * g * v * billow;
}

// per ray (the deck): the skirts whose collar the segment eye + ray [t0, t1] can reach (at most 4), so the march loops
// over 0-2 of them instead of 8
struct LanbaiSkirtSet { float4 s[4]; int n; };

LanbaiSkirtSet LanbaiGateSkirtCull(float3 eye, float3 ray, float t0, float t1)
{
    LanbaiSkirtSet o;
    o.n = 0;
    o.s[0] = o.s[1] = o.s[2] = o.s[3] = 0;
    int count = (int)min(_Udon_GateSkirtK.x, 8.0);
    float2 a = eye.xz + ray.xz * t0, b = eye.xz + ray.xz * t1;
    float2 ab = b - a;
    float ab2 = max(dot(ab, ab), 1e-4);
    [loop] for (int i = 0; i < 8; i++)
    {
        if (i >= count || o.n >= 4) break;
        float4 s = LanbaiGateSkirtGet(i);
        if (s.w <= 0.0) continue;
        float2 q = a + ab * saturate(dot(s.xz - a, ab) / ab2);
        float reach = s.w + 3.0 * max(LANBAI_SKIRT_WMIN, _Udon_GateSkirtK.y * s.w);
        if (length(q - s.xz) < reach)
        {
            if (o.n == 0) o.s[0] = s; else if (o.n == 1) o.s[1] = s; else if (o.n == 2) o.s[2] = s; else o.s[3] = s;
            o.n++;
        }
    }
    return o;
}

float LanbaiGateSkirtSet(float3 p, float top, float2 nrg, LanbaiSkirtSet k)
{
    float m = 0.0;
    [loop] for (int i = 0; i < 4; i++)
    {
        if (i >= k.n) break;
        m = max(m, LanbaiGateSkirtOne(p, top, nrg, k.s[i]));
    }
    return m;
}

// all 8 (the arms: one point, no ray)
float LanbaiGateSkirtAll(float3 p, float top, float2 nrg)
{
    float m = 0.0;
    int count = (int)min(_Udon_GateSkirtK.x, 8.0);
    [loop] for (int i = 0; i < 8; i++)
    {
        if (i >= count) break;
        float4 s = LanbaiGateSkirtGet(i);
        if (s.w > 0.0) m = max(m, LanbaiGateSkirtOne(p, top, nrg, s));
    }
    return m;
}

// ---- for the arms ---------------------------------------------------------------------------------------------------
bool LanbaiCloudVolumeOn() { return _Udon_CloudVolume.x > 0.5; }

// extinction (1/m) at p: the deck's density (+ skirts) x the comfort cut under the eye, from the globals
float LanbaiCloudDensityAt(float3 p, float top, float3 origin, float time)
{
    float2 nrg;
    float s = LanbaiCloudShape(_Udon_CloudVolumeTex, p, top, origin, _Udon_CloudVolumeWind.xy, time, _Udon_CloudVolume.zw, nrg);
    s = max(s, LanbaiGateSkirtAll(p, top, nrg));
    float comfort = _WorldSpaceCameraPos.y < top - 170.0 ? 1.0                // under the deck: no cut (the deck's rule)
                  : 1.0 - smoothstep(_WorldSpaceCameraPos.y - 40.0, _WorldSpaceCameraPos.y - 18.0, p.y);
    return s * comfort * _Udon_CloudVolume.y;
}

// the deck's lit colour at p (its frag's `light` before the gain and the fog): sky ambient x height + the moon x the
// two-sample self-shadow x (0.65 + 0.35 facing^5) + the foot pool; moonE / amb / moonCol = the deck material's values
float3 LanbaiCloudLitAt(float3 p, float top, float3 origin, float time, float3 moon, float facing,
                        float3 ambCol, float3 moonCol, float moonE)
{
    float optical = LanbaiCloudDensityAt(p + moon * 18.0, top, origin, time) * 22.0
                  + LanbaiCloudDensityAt(p + moon * 50.0, top, origin, time) * 38.0;
    float illumination = 0.08 + 0.92 * exp(-optical * 1.7);
    float height = saturate((p.y - (top - 120.0)) / 140.0);
    float3 light = ambCol * (0.3 + height * 0.35) + moonCol * moonE * illumination * (0.65 + facing * 0.35);
    if (_Udon_TearFoot.w > 0.0)                     // the deck's foot pool (#E2E8F3 x 0.09, 180 x 240 m)
    {
        float dist = length((p.xz - _Udon_TearFoot.xz) / float2(180.0, 240.0));
        light += float3(0.7605, 0.8070, 0.8963) * 0.09 * exp(-dist * dist) * height;
    }
    return light;
}

#endif
