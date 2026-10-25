// =====================================================================================================
//  LanbaiTree.cginc       蓝白 · 样板树（D-44 #6）共用：顶点风、湿润（圣经 §1.6 Lagarde）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. Checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//
//  Vertex colour (written by Lamps/Source/tree/lt_build.py, FBX "Col", linear):
//      R = flexibility 0 (trunk) .. 1 (twig, leaf card)   G = phase 0..1   B = 1 on leaf cards
//  Wind (material, no _Udon_ global; the motion is local decoration, not synced):
//      sway    = _WindStrength * R^2 * sin(t * _WindFreq + 0.07 * dot(rootXZ, 1) + 1.3 * G)        (metres, along _WindDir)
//      flutter = _Flutter * B * sin(t * _FlutterFreq + 6.283 G)                                    (metres, along the normal)
//  VR (bible §1.8): slow (0.15-0.35 Hz sway), small (<= 6 cm at the crown); nothing jitters (no 1-4 Hz component
//  above 1 cm: flutter is 1.2 cm at most).
//  Wetness: w = _Udon_Wetness * _WetResponse
//      bark:   albedo x lerp(1, 0.60, w), smoothness lerp(s, 0.45, w), normal x lerp(1, 0.6, w)      (bible §1.6)
//      leaves: albedo unchanged (waxy, not porous), smoothness lerp(s, 0.60, w)                     (bible: wet leaf 0.55-0.65)
// =====================================================================================================
#ifndef LANBAI_TREE_INCLUDED
#define LANBAI_TREE_INCLUDED

#include "UnityCG.cginc"
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"

float4 _WindDir;          // xyz world direction (normalised in the shader), w unused
float  _WindStrength;     // metres at R = 1
float  _WindFreq;         // rad / s
float  _Flutter;          // metres
float  _FlutterFreq;      // rad / s
float  _WetResponse;      // 0..1: how much this material follows _Udon_Wetness

inline float LanbaiTreeWet()
{
    return saturate(_Udon_Wetness * _WetResponse);
}

// objectPos / objectNormal in object space; returns the displaced object-space position
inline float3 LanbaiTreeWind(float3 objectPos, float3 objectNormal, float4 vcol)
{
    float t = _Time.y;
    float3 root = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
    float flex = vcol.r * vcol.r;
    float sway = _WindStrength * flex * sin(t * _WindFreq + 0.07 * (root.x + root.z) + 1.3 * vcol.g);
    // a second, slower, smaller component so the crown never moves as one rigid sheet
    sway += 0.35 * _WindStrength * flex * sin(t * _WindFreq * 0.61 + 4.0 * vcol.g);
    float flut = _Flutter * vcol.b * sin(t * _FlutterFreq + 6.2831853 * vcol.g);
    float3 dirW = normalize(_WindDir.xyz + float3(0, 1e-4, 0));
    float3 dirO = mul((float3x3)unity_WorldToObject, dirW);
    dirO.y = 0;                                   // horizontal only: the tree never bobs (VR, bible §1.8)
    return objectPos + dirO * sway + objectNormal * flut;
}

#endif
