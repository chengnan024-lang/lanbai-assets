// =====================================================================================================
//  Lanbai / MirrorStars   v1 (2026-10-22, cloud session 「镜与白」)   蓝白 · 白铜镜里反射的星点
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER. slang syntax / type check only (Mirrors/Tools~/compile_check). !!!
//
//  Draws the SKY's star-point mesh a second time, once per visible mirror, only where that mirror's face is the
//  visible surface (stencil 64 + slot, written by Lanbai/BronzeMirror pass FACESTENCIL).  Bible §6·9: 'the reflected
//  stars come from a mirrored copy of the star-point mesh, drawn only inside the mirror's stencil' (lens_tech §2.6).
//
//  Because the face is CONVEX (sagitta 1.5 % of D), a flat-mirror copy (dir.y = -dir.y) would drift up to ~7 degrees
//  away from the cube-reflected Milky Way near the rim.  So each star is placed where the convex mirror really shows
//  it: the point P on the face sphere whose reflection of the star direction d reaches the eye E,
//      v = reflect(d, n); P = (eye ray along v) on the face sphere; n = normal at P     (6 damped rounds from the flat mirror; p99 error 0.07 deg)
//  and the quad is drawn there (pulled 0.5 % toward the eye so it never z-fights with the face).
//
//  MESH CONTRACT = the sky's star mesh Sky/Generated/StarPoints_BSC5.asset (Lanbai/StarPoints): 4 vertices per star,
//    vertex.xyz = unit world direction, uv0 = corner (-1..1), uv1 = (V magnitude, rank, order, 0), colour = linear rgb
//    of luminance 1.  Brightness is Lanbai/StarPoints' own formula with the same defaults and the same _Udon_StarGain
//    (x gain, y bright boost, z bright count), so a star and its reflection are the same star.
//  Per renderer (MaterialPropertyBlock, written by LanbaiMirrorsDriver every frame):
//    _SphereC (xyz = world centre of the face sphere, w = rho in metres), _Axis (xyz = world up of the mirror,
//    w = face radius in metres), _FaceK (x = F0 scale, y = emission k x visibility x 2^extra), _Gain.
// =====================================================================================================
Shader "Lanbai/MirrorStars"
{
    Properties
    {
        _SphereC ("Face sphere centre xyz and rho w (world m)", Vector) = (0, -300, 0, 307.5)
        _Axis ("Mirror up xyz and face radius w (m)", Vector) = (0, 1, 0, 19.2)
        _FaceF0 ("Face F0 linear (#D6CCB4)", Vector) = (0.672, 0.604, 0.456, 0)
        _FaceK ("x unused, y emission k times visibility times 2 pow extra", Vector) = (1, 0.28, 0, 0)
        _BronzeTone ("White bronze tone 0 to 1 (as the face)", Range(0, 1)) = 0.65
        _ToneColor ("Tone colour linear luminance 1 (#CDBF9C)", Vector) = (1.158, 0.989, 0.630, 0)
        _Gain ("Star gain if the global is not set", Float) = 1
        _StarScale ("Star scale at the reference magnitude (as Lanbai/StarPoints)", Float) = 1.6
        _MagRef ("Reference magnitude", Float) = 0
        _MagSlope ("Magnitude slope", Range(0.2, 1)) = 0.5
        _MagFloor ("Faintest magnitude drawn", Float) = 6.5
        _BrightCount ("Bright ranks boosted (count)", Float) = 50
        _BrightBoost ("Boost of the bright ranks", Float) = 4
        _FWHM ("FWHM px", Range(1.5, 4)) = 1.6
        [IntRange] _StencilRef ("Stencil ref 64 plus slot", Range(64, 127)) = 64
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-90" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One One
        ZWrite Off
        ZTest LEqual
        Cull Off
        Stencil { Ref [_StencilRef] ReadMask 127 WriteMask 0 Comp Equal }

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "LanbaiMirror.cginc"

            float4 _SphereC, _Axis, _FaceF0, _FaceK;
            float _Gain, _StarScale, _MagRef, _MagSlope, _MagFloor, _BrightCount, _BrightBoost, _FWHM, _BronzeTone;
            float4 _ToneColor;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
                float4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 q : TEXCOORD0;          // corner in FWHM units
                half3 col : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 d = normalize(v.vertex.xyz);                                     // star direction (world; transform ignored, as StarPoints)
                float3 up = normalize(_Axis.xyz);
                float3 C = _SphereC.xyz;
                float rho = _SphereC.w;
                float3 E = _WorldSpaceCameraPos;                                        // this eye (SPS-I: per eye)
                // convex-mirror image point: start from the flat mirror, refine with the normal at the hit point.
                // v = reflect(d, n) is the direction the eye looks along; P = the eye's ray along v hitting the face
                // sphere; n = the sphere normal at P.  Damped; checked against the exact reflection in the numpy port.
                float3 n0 = up;
                float3 oc = E - C;
                float cc = dot(oc, oc) - rho * rho;
                float3 P = C + rho * up;
                [unroll] for (int k = 0; k < 7; k++)
                {
                    float3 v = reflect(d, n0);
                    float b = dot(v, oc);
                    float tq = -b - sqrt(max(b * b - cc, 0.0));
                    P = E + v * tq;
                    if (k < 6) n0 = normalize(0.5 * n0 + 0.5 * normalize(P - C));   // damped: the plain update oscillates near grazing
                }
                float3 n = normalize(P - C);
                float3 toE = normalize(E - P);
                // visible only if the star is above the mirror's horizon and P lies on the face disc
                float axial = length((P - C) - dot(P - C, up) * up);
                float ok = step(0.0, dot(d, n)) * step(0.0, dot(toE, n)) * step(axial, _Axis.w * 1.02)
                         * step(0.99996, dot(reflect(-toE, n), d));                        // not converged (> 0.5 deg): drop it
                // brightness: Lanbai/StarPoints' formula and gains
                float m = v.uv1.x;
                float flux = _StarScale * exp2(-1.3287712 * _MagSlope * (m - _MagRef)) * step(m, _MagFloor);
                bool useG = _Udon_StarGain.w > 0.0;
                float boost = (useG && _Udon_StarGain.y > 0.0) ? _Udon_StarGain.y : _BrightBoost;
                float count = (useG && _Udon_StarGain.z > 0.0) ? _Udon_StarGain.z : _BrightCount;
                flux *= lerp(1.0, boost, saturate((count - v.uv1.y) / 20.0));
                float g = useG ? _Udon_StarGain.x : _Gain;
                float3 F = LanbaiSchlick(_FaceF0.rgb, dot(n, toE));
                float3 col = v.color.rgb * (flux * g * ok) * (F + _FaceK.y);
                col = lerp(col, dot(col, float3(0.2126, 0.7152, 0.0722)) * _ToneColor.rgb, _BronzeTone);

                float3 centre = lerp(P, E, 0.005);
                float3 R = normalize(cross(abs(d.y) < 0.99 ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0), toE));
                float3 U = cross(toE, R);
                float halfPx = 2.0 * _FWHM;
                float h = halfPx * LanbaiPixelAngle() * distance(centre, E);
                float3 Pq = centre + (R * v.uv0.x + U * v.uv0.y) * h;
                o.pos = (ok > 0.0 && flux * g > 0.0) ? UnityWorldToClipPos(Pq) : float4(0.0, 0.0, -1.0, 1.0);
                o.q = v.uv0 * halfPx / _FWHM;
                o.col = (half3)col;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float k = exp(-2.7725887 * dot(i.q, i.q));                     // exp(-4 ln2 r^2), r in FWHMs (as StarPoints)
                return half4(i.col * k, 0);
            }
            ENDCG
        }
    }
    Fallback Off
}
