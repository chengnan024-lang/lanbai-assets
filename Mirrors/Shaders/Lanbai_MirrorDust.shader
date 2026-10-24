// =====================================================================================================
//  Lanbai / MirrorDust   v1 (2026-10-22, cloud session 「镜与白」)   蓝白 · 镜子碎成的星尘
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Mirrors/Tools~/compile_check). !!!
//
//  Bible §6·9: after it crosses, each mirror dissolves rim -> centre over 2.0 s and releases 250 motes that drift UP
//  (<= 1 m/s), #CDBF9C -> #F2F6FF, fading over 4 s; at most 3 mirrors dissolve together (<= 750 motes).  The 'dust'
//  motif's third ring.
//
//  No particle system: a static mesh of 250 quads per slot (3 slots), every mote's whole life is a closed-form
//  function of the timeline time, so seeking / restarting just works and nothing depends on the Udon particle API.
//  The mote is born where the dissolve front passes it (the same front as Lanbai/BronzeMirror, without the noise),
//  at the face height of that moment, then rises slowly with a gentle drift.
//
//  MESH CONTRACT (made by the build script, Mirrors/Editor/LanbaiMirrorsBuilder.cs -> MirrorDust_250.asset):
//    4 vertices per mote, all at the origin; UV0 = corner (-1..1); UV1 = (u1, u2) and UV2 = (u3, u4) uniform seeds.
//  Per renderer (MaterialPropertyBlock, LanbaiMirrorsDriver): _DustNow (timeline t), _DustT0 (crossing t),
//    _DustC (xyz = world position of the mirror centre at the crossing (face-edge height), w = radius m),
//    _DustCar (xy = car xz minus centre xz, metres; z = face rise speed m/s after the crossing; w = D),
//    _DustOn (0/1).
// =====================================================================================================
Shader "Lanbai/MirrorDust"
{
    Properties
    {
        _DustNow ("Timeline now", Float) = 0
        _DustT0 ("Crossing time", Float) = -100
        _DustC ("Mirror centre at crossing xyz and radius w", Vector) = (0, 0, 0, 20)
        _DustCar ("Car minus centre xy, rise speed z, diameter w", Vector) = (0, 0, 1.7, 40)
        _DustOn ("On", Float) = 0
        _Dur ("Dissolve duration s", Float) = 2
        _Fade ("Fade s", Float) = 4
        _Rise ("Rise speed m per s (max 1)", Range(0, 1)) = 0.6
        _NearFrac ("Fraction born near the car", Range(0, 1)) = 0.7
        _NearRadius ("Near region radius m", Float) = 40
        _ColA ("Colour at birth linear (#CDBF9C)", Vector) = (0.61, 0.52, 0.33, 0)
        _ColB ("Colour at the end linear (#F2F6FF)", Vector) = (0.89, 0.92, 1.0, 0)
        _Flux ("Peak brightness at minimum size", Float) = 6
        _SizeM ("Physical radius m", Float) = 0.05
        _MinFWHM ("Minimum drawn size FWHM in pixels", Range(0.8, 3)) = 1.4
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-80" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One One
        ZWrite Off
        ZTest LEqual
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"
            #include "LanbaiMirror.cginc"

            float _DustNow, _DustT0, _DustOn, _Dur, _Fade, _Rise, _NearFrac, _NearRadius, _Flux, _SizeM, _MinFWHM;
            float4 _DustC, _DustCar, _ColA, _ColB;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 corner : TEXCOORD0;
                half3 col : TEXCOORD1;
                float3 posWS : TEXCOORD2;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            // birth position (xz relative to the mirror centre, metres) from the seeds: most motes near the car
            float2 DustXZ(float2 s1, float2 s2, float R)
            {
                float a = 6.2831853 * s1.y;
                float2 dir = float2(cos(a), sin(a));
                float2 nearP = _DustCar.xy + dir * (sqrt(s1.x) * min(_NearRadius, R));
                float2 anyP = dir * (sqrt(s1.x) * R);
                float2 p = (s2.x < _NearFrac) ? nearP : anyP;
                float l = length(p);
                return (l > 0.985 * R) ? p * (0.985 * R / l) : p;               // stays on the disc
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float R = _DustC.w;
                float D = _DustCar.w;
                float2 xz = DustXZ(v.uv1, v.uv2, R);
                float q = length(xz) / R;                                           // 0 centre .. 1 rim
                float tBorn = _DustT0 + _Dur * (1.0 - q);                           // the front passes it (rim first)
                float age = _DustNow - tBorn;
                float alive = step(0.0, age) * step(age, _Fade) * _DustOn;
                // face height at birth: the face point rises at _DustCar.z after the crossing; convex cap offset
                float sagM = LM_SAG * D;
                float rFace = LM_FACE_R * D;
                float capHere = sagM * (1.0 - saturate(q * R / rFace) * saturate(q * R / rFace));
                float yBorn = _DustC.y + _DustCar.z * max(tBorn - _DustT0, 0.0) + capHere;
                // slow rise with a gentle drift (<= 1 m/s total), different per mote
                float rise = _Rise * (0.6 + 0.4 * v.uv2.y);
                float wob = 0.25 * sin(6.2831853 * (0.11 * age + v.uv2.y));
                float3 p = float3(_DustC.x + xz.x + wob * v.uv1.y, yBorn + rise * age, _DustC.z + xz.y + wob * (1.0 - v.uv1.x));

                float x = saturate(age / _Fade);
                float bright = saturate(age / 0.25) * (1.0 - x) * (1.0 - x);       // no birth flash: 0.25 s rise, quadratic fade
                float3 col = lerp(_ColA.rgb, _ColB.rgb, x) * bright * alive;

                float dist = distance(p, _WorldSpaceCameraPos);
                float rMin = (_MinFWHM / 1.4133) * LanbaiPixelAngle() * dist;
                float rDraw = max(_SizeM, rMin);
                float peak = _Flux * (_SizeM / rDraw) * (_SizeM / rDraw);            // flux-conserving when inflated
                float near = LanbaiNearFade(p, 0.3, 1.0);                            // nothing inside 0.3 m of the eye
                float3 toC = normalize(LanbaiCentreEyePos() - p);                   // faces the centre eye (CONTROL §3)
                float3 Rb = normalize(cross(abs(toC.y) < 0.99 ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0), toC));
                float3 Ub = cross(toC, Rb);
                o.pos = UnityWorldToClipPos(p + (Rb * v.uv0.x + Ub * v.uv0.y) * (2.0 * rDraw * alive));
                o.corner = v.uv0;
                o.col = (half3)(col * peak * near);
                o.posWS = p;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float r2 = dot(i.corner, i.corner) * 4.0;
                float3 c = i.col * exp(-r2 / (2.0 * 0.36));
                c = LanbaiApplyFogAdditive(c, i.posWS);
                return half4(c, 0);
            }
            ENDCG
        }
    }
    Fallback Off
}
