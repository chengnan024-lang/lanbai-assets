// =====================================================================================================
//  Lanbai / LanbaiPalace.cginc   蓝白 · 第 7b 幕河伯宫殿的共用数学（Lanbai/Palace、Lanbai/PalaceFish、Lanbai/PalaceGlow）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with Common/Tools~/compile_check (DXC + Unity 2022.3
//      CGIncludes), never compiled or run in Unity. !!!
//
//  · 宫灯的高光：8 盏解析 GGX 点光 _Udon_Lamp0..7（圣经 §1.6；D-24：宫殿全烘焙、没有带阴影的实时光，铜灯的高光走这里）。
//    驱动每帧把离车最近的 8 盏宫灯写进去（xyz 位置、w 强度 I：正对着、距离 d 的面收到 E = I / d²，与烘焙灯同一个 I）。
//    _Udon_LampColor.a = 光源半径（灯焰 ~0.1 m，放宽 GGX 的瓣）。这一套与 Rain/Shaders/LanbaiLamps.cginc 同义，
//    但那份文件自己声明全局量（与 LanbaiGlobals.cginc 冲突），所以这里只 include LanbaiGlobals 再写一份点光的版本。
//  · _Udon_PalaceVeil：从台地下面往上看时把建筑罩进水雾（海的约定 PalaceFrame_约定.json palace_veil；海的驱动写）。
//  · 淤泥：朝上的面 × 世界空间噪声（圣经 §6·7b：覆盖 40–70%，#5E6259 / 0.10）。
// =====================================================================================================
#ifndef LANBAI_PALACE_INCLUDED
#define LANBAI_PALACE_INCLUDED

#include "UnityCG.cginc"
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

// ---- 噪声（值噪声，世界坐标；与 Palace/Source/materials.py 的淤泥同一个“朝上 × 噪声”的式子，噪声本身不逐位相同）
inline float LanbaiHash31(float3 p)
{
    p = frac(p * 0.3183099 + 0.1);
    p *= 17.0;
    return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
}

inline float LanbaiValueNoise(float3 x)
{
    float3 i = floor(x);
    float3 f = frac(x);
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(LanbaiHash31(i + float3(0, 0, 0)), LanbaiHash31(i + float3(1, 0, 0)), f.x),
                     lerp(LanbaiHash31(i + float3(0, 1, 0)), LanbaiHash31(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(LanbaiHash31(i + float3(0, 0, 1)), LanbaiHash31(i + float3(1, 0, 1)), f.x),
                     lerp(LanbaiHash31(i + float3(0, 1, 1)), LanbaiHash31(i + float3(1, 1, 1)), f.x), f.y), f.z);
}

inline float LanbaiFbm3(float3 x)
{
    return 0.55 * LanbaiValueNoise(x) + 0.30 * LanbaiValueNoise(x * 2.03 + 7.1) + 0.15 * LanbaiValueNoise(x * 4.11 + 3.7);
}

// 淤泥遮罩：nWS.y 0.55 起、0.85 满；乘噪声（coverage 0..1 ≈ 覆盖率）
inline float LanbaiSilt(float3 posWS, float3 nWS, float coverage, float scale)
{
    float up = saturate((nWS.y - 0.55) / 0.30);
    float n = LanbaiFbm3(posWS * scale);
    float m = saturate((n - (1.0 - coverage)) * 5.0 + 0.5);
    return up * m;
}

// ---- 一盏点光的 GGX 高光（Unity Standard 约定：spec = D·Vis·F·π·E·NdotL）
inline float3 LanbaiPalaceSpecOne(float4 lamp, float4 colR, float3 P, float3 N, float3 V, float alpha, float3 F0)
{
    if (lamp.w <= 0.0) return 0;
    float3 Lv = lamp.xyz - P;
    float d2 = max(dot(Lv, Lv), 1e-4);
    float3 L = Lv * rsqrt(d2);
    float NdotL = saturate(dot(N, L));
    if (NdotL <= 0.0) return 0;
    float a = saturate(alpha + colR.a * 0.5 * rsqrt(d2));          // 球光源放宽（Karis 2013）
    float a2 = a * a;
    float3 H = normalize(L + V);
    float NdotH = saturate(dot(N, H));
    float NdotV = max(dot(N, V), 1e-4);
    float LdotH = saturate(dot(L, H));
    float dd = NdotH * NdotH * (a2 - 1.0) + 1.0;
    float D = a2 / (UNITY_PI * dd * dd + 1e-7);
    float k = a * 0.5;
    float Vis = 0.25 / ((NdotL * (1.0 - k) + k) * (NdotV * (1.0 - k) + k) + 1e-5);
    float3 F = F0 + (1.0 - F0) * pow(1.0 - LdotH, 5.0);
    float E = lamp.w / d2;
    return D * Vis * F * UNITY_PI * NdotL * E * colR.rgb;
}

inline float3 LanbaiPalaceLamps(float3 P, float3 N, float3 V, float alpha, float3 F0)
{
    float3 s = 0;
    s += LanbaiPalaceSpecOne(_Udon_Lamp0, _Udon_LampColor0, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp1, _Udon_LampColor1, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp2, _Udon_LampColor2, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp3, _Udon_LampColor3, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp4, _Udon_LampColor4, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp5, _Udon_LampColor5, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp6, _Udon_LampColor6, P, N, V, alpha, F0);
    s += LanbaiPalaceSpecOne(_Udon_Lamp7, _Udon_LampColor7, P, N, V, alpha, F0);
    return s;
}

// ---- _Udon_PalaceVeil：眼 → 片元的线段落在水平雾带 [y − z, y] 里的长度 L，veil = 1 − exp(−x·L)
inline float LanbaiPalaceVeil(float3 posWS, float3 eyeWS)
{
    float4 pv = _Udon_PalaceVeil;
    if (pv.w <= 0.0 || pv.x <= 0.0) return 0.0;
    float a = min(eyeWS.y, posWS.y);
    float b = max(eyeWS.y, posWS.y);
    float ov = max(min(b, pv.y) - max(a, pv.y - pv.z), 0.0);
    float seg = length(posWS - eyeWS);
    float Lb = seg * ov / max(b - a, 1e-3);
    return 1.0 - exp(-pv.x * Lb);
}

// 珍珠母的虹彩：高光颜色 = f(N·V)：正面 → 中 → 掠射（圣经 §6·7b 鱼鳞屋）
inline float3 LanbaiNacre(float NdotV, float3 cFace, float3 cMid, float3 cGraze, float thick)
{
    float x = saturate(1.0 - NdotV + (thick - 0.5) * 0.25);
    return x < 0.5 ? lerp(cFace, cMid, x * 2.0) : lerp(cMid, cGraze, x * 2.0 - 1.0);
}

#endif
