// =====================================================================================================
//  v2.2 (gate round 3 run 6, 2026-10-01; UNCOMPILED): for the v3 atlases (gate/Textures/TentacleTide_v3_Atlas_A/B)
//    + UV6 'TideMist' (x = mist height m, y = root sink m): the base dissolves over the blade's own mist height,
//      alpha x saturate((y - _Udon_CloudTop.x + 8) / mist)^1.6, so the 360 bases never line up on the cloud-top line
//      (the v2 tide read as a fringe of grass along the horizon).
// =====================================================================================================
//  v2.1 (gate round 3, 2026-10-01; UNCOMPILED): tech M3 / minors
//    + _AtlasGain (0.3): the atlas colour (its painted moon rim) is scaled like the far arm rims, so no crest is ever
//      brighter than the sky behind it; fog base 0.58 -> tips 0.48 (_FogBaseTip): a -4..-6 L* tide on screen.
//    + _Reveal (material, 0..1, after the cap): f = 1 - (1 - f) x _Reveal; clip below _Udon_CloudTop.x - 2 (w > 0).
//    + the fragment shader sets up the stereo eye (UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX): Single Pass Instanced
//      reads each eye's own camera position.
//    + _BandEl.z = the band's elevation power (as TentacleSway / the sky: (12, 34, 5)).
//    + the rise depth in UV5.x is now only the visible part (size x cos(lean) + 40 m) over 14 s (GateLayout_v2.json).
// =====================================================================================================
//  v2 (gate round 2, 2026-10-01; UNCOMPILED): for gate/TentacleTide_v2.fbx (440 quads from GateLayout_v2.json tide).
//    + UV4 'TideRise' (x = rise t0 (timeline s), y = lean deg toward the wound), UV5 'TideRiseDepth' (x = depth m,
//      y = duration s): the blade rises out of the cloud on the global _Udon_GateTime (smoothstep) and LEANS toward
//      the wound in the billboard plane, so the tips form rolling crests (the tide is a surge, not a forest);
//    + fog 80 % at the base, 60 % at the tips: min(fog, lerp(0.8, 0.6, smoothstep(0, 400, height)));
//    + global _Udon_TearPos (w > 0) for the 'toward the wound' side and the band azimuth; _BandEl (12, 35).
//  Lanbai / TentacleTide            蓝白 · 触手之门 · 远潮（圆柱公告板）  Built-in RP, unlit, alpha blended
//  ART BIBLE v2 §6·4 / §8.1 #5: 300-500 impostor arms at 5-12 km within +-70 deg of the tear, 80-92 % in
//  the haze, surging toward the wound in waves (sway phase = distance to the tear / 600 m - t / 6 s).
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER !!!  Compile and check in Unity 2022.3 before use
//  (Console clean; VR Single Pass Instanced shows the same tide in both eyes; the quads turn about their
//  roots as the bus moves, never about the screen centre).
//
//  Mesh contract (FBX/TentacleTide.fbx, ONE mesh, 400 quads = 800 triangles, 3 sub-meshes = 3 atlases):
//    vertex position  the quad as seen from the GateLayout camera, in GateLayout space (object space here:
//                     put TentacleTide under the same parent as the GateLayout instances, local identity)
//    UV0 'UVMap'            atlas UV (cell already mirrored for arms right of the tear: all lean toward it)
//    UV1 'TideSway'         x = height fraction 0 (root) .. 1 (top of the cell), y = sway phase = dist / 600 m
//    UV2 'TideRootXZ'       root position x, z (object space)
//    UV3 'TideRootYOffset'  x = root y, y = this corner's signed horizontal offset from the root (m)
//  The vertex shader re-faces every quad to the camera about its own vertical root axis (cylindrical
//  billboard), adds the inward-rolling sway and applies LanbaiFog with _FogCap 0.92 (no height falloff).
//  Materials: M_TentacleTide_A / _B / _C = this shader + TentacleTide_Atlas_A / B / C (sRGB, alpha =
//  coverage, Clamp, mipmaps on). One mesh -> 3 draw calls; no shadows; keep it out of static batching.
// =====================================================================================================
Shader "Lanbai/TentacleTide"
{
    Properties
    {
        _MainTex ("TentacleTide_Atlas_X (sRGB, alpha = coverage)", 2D) = "white" {}
        _Opacity ("Opacity", Range(0, 1)) = 1
        _RimGain ("Painted Rim Gain", Range(0, 4)) = 1
        _AtlasGain ("Atlas colour gain (0.3: the painted rim never brighter than the sky)", Range(0, 1)) = 0.3
        _Reveal ("Reveal 0..1 (after the fog cap)", Range(0, 1)) = 1
        _SwayAmp ("Sway (fraction of the height at the top)", Range(0, 0.2)) = 0.04
        _SwayPeriod ("Wave Period (s)", Float) = 6
        _TearPos ("Tear Centre (world xyz, GateLayout.json)", Vector) = (0, 297, 1800, 0)

        [Header(LanbaiFog  same values as the tentacle materials and the sky)]
        _FogDensity ("Exp Fog Density (per metre)", Float) = 0.0006
        _FogCap ("Fog Cap (tide 0.92)", Range(0, 1)) = 0.92
        _FogCapFrom ("Cap blends in from x to y metres", Vector) = (1300, 1700, 0, 0)
        _HazeNear ("Haze Band Next To The Tear #484D63, linear", Vector) = (0.0648, 0.0742, 0.1248, 1)
        _HazeFar ("Haze Band 50 deg Away #2A3041, linear", Vector) = (0.0232, 0.0296, 0.0512, 1)
        _Void ("Void #070A14, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth: full to x deg, gone at y deg", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation: full to x deg, gone at y deg, power z", Vector) = (12, 34, 5, 0)
        _FogBaseTip ("Fog cap at the base (x) and the tips (y); height of the blend (z m)", Vector) = (0.58, 0.48, 400, 0)
        _BelowHorizon ("Below the horizon: from x deg to y deg, darkest factor z", Vector) = (-25, 0, 0.55, 0)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-100" "RenderType" = "Transparent" "IgnoreProjector" = "True" "DisableBatching" = "True" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float _Opacity, _RimGain, _SwayAmp, _SwayPeriod, _AtlasGain, _Reveal;
            float4 _Udon_CloudTop;     // global: x = cloud-sea top (world y); w > 0 = set
            float4 _TearPos;
            float _FogDensity, _FogCap;
            float4 _FogCapFrom, _HazeNear, _HazeFar, _Void, _BandAz, _BandEl, _BelowHorizon, _FogBaseTip;
            float _Udon_GateTime;      // global: timeline t (s); 0 = unset -> everything risen
            float4 _Udon_TearPos;      // global: the tear core (world); w > 0 = set
            float3 TearPosW() { return (_Udon_TearPos.w > 0.0) ? _Udon_TearPos.xyz : _TearPos.xyz; }

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                float2 uv3 : TEXCOORD3;
                float2 uv4 : TEXCOORD4;    // TideRise: rise t0, lean deg
                float2 uv5 : TEXCOORD5;    // TideRiseDepth: depth m, duration s
                float2 uv6 : TEXCOORD6;    // v2.2 TideMist: mist height m, sink m
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float hgt : TEXCOORD2;
                float mist : TEXCOORD3;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            // identical to LanbaiBand() in Lanbai_TentacleSway.shader
            float3 LanbaiBand(float3 V)
            {
                float el = degrees(asin(clamp(V.y, -1.0, 1.0)));
                float3 T = TearPosW() - _WorldSpaceCameraPos;
                float2 th = normalize(T.xz + float2(1e-5, 0.0));
                float2 vh = normalize(V.xz + float2(1e-5, 0.0));
                float az = degrees(acos(clamp(dot(th, vh), -1.0, 1.0)));
                float3 band = lerp(_HazeNear.rgb, _HazeFar.rgb, smoothstep(0.0, _BandAz.x, az));
                float wel = pow(saturate(1.0 - smoothstep(_BandEl.x, _BandEl.y, el)), (_BandEl.z > 0.0) ? _BandEl.z : 1.0);
                float w = (1.0 - smoothstep(_BandAz.x, _BandAz.y, az)) * wel;
                float3 sky = lerp(_Void.rgb, band, w);
                return sky * lerp(_BelowHorizon.z, 1.0, smoothstep(_BelowHorizon.x, _BelowHorizon.y, el));
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 root = float3(v.uv2.x, v.uv3.x, v.uv2.y);                 // object space
                float off = v.uv3.y;
                float h = v.vertex.y - root.y;                                    // height of this corner
                float3 camO = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1.0)).xyz;
                float2 d = root.xz - camO.xz;
                d /= max(length(d), 1e-3);
                float3 r = float3(d.y, 0.0, -d.x);                                // camera-right, horizontal
                // the tide rolls in toward the wound: phase = distance / 600 m - t / 6 s, bend grows as height^2
                float3 tearO = mul(unity_WorldToObject, float4(TearPosW(), 1.0)).xyz;
                float toward = dot(r.xz, tearO.xz - root.xz) >= 0.0 ? 1.0 : -1.0;
                float f = v.uv1.x;
                float sw = _SwayAmp * h * f * sin(6.2831853 * (v.uv1.y - _Time.y / max(_SwayPeriod, 0.1)));
                // v2: lean toward the wound in the billboard plane, then rise out of the cloud
                float lean = radians(v.uv4.y) * toward;
                float cl = cos(lean), sl = sin(lean);
                float o2 = off + toward * sw;
                float3 p = float3(root.x, root.y, root.z) + r * (o2 * cl + h * sl) + float3(0, 1, 0) * (h * cl - o2 * sl);
                float rs = (_Udon_GateTime > 0.0) ? saturate((_Udon_GateTime - v.uv4.x) / max(v.uv5.y, 0.1)) : 1.0;
                p.y -= v.uv5.x * (1.0 - rs * rs * (3.0 - 2.0 * rs));
                o.hgt = h * cl;
                o.pos = UnityObjectToClipPos(float4(p, 1.0));
                o.wpos = mul(unity_ObjectToWorld, float4(p, 1.0)).xyz;
                o.uv = v.uv0;
                o.mist = max(v.uv6.x, 1.0);
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Udon_CloudTop.w > 0.0)
                    clip(i.wpos.y - _Udon_CloudTop.x + 2.0);
                half4 c = tex2D(_MainTex, i.uv);
                // the painted rim is the only bright part of the atlas: let it be gained, then scale the whole colour
                half lum = dot(c.rgb, half3(0.2126, 0.7152, 0.0722));
                c.rgb *= lerp(1.0, _RimGain, saturate(lum * 4.0)) * _AtlasGain;
                float3 dv = i.wpos - _WorldSpaceCameraPos;
                float dist = length(dv);
                float fo = 1.0 - exp(-dist * _FogDensity);
                fo = lerp(fo, min(fo, _FogCap), smoothstep(_FogCapFrom.x, _FogCapFrom.y, dist));
                fo = min(fo, lerp(_FogBaseTip.x, _FogBaseTip.y, smoothstep(0.0, _FogBaseTip.z, i.hgt)));
                fo = 1.0 - (1.0 - fo) * _Reveal;
                c.rgb = lerp(c.rgb, LanbaiBand(dv / max(dist, 1e-3)), fo);
                c.a *= _Opacity;
                if (_Udon_CloudTop.w > 0.0)        // v2.2: the base melts over the blade's own mist height
                    c.a *= pow(saturate((i.wpos.y - _Udon_CloudTop.x + 8.0) / i.mist), 1.6);
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
