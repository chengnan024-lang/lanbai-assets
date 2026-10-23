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
//      P = C + rho * normalize(d + normalize(E - P))           (fixed point, 4 iterations, converges for a convex face)
//  and the quad is drawn there (pulled 0.5 % toward the eye so it never z-fights with the face).
//
//  MESH CONTRACT = Lanbai/PointSprites infinite mode (Art/tools/lens_tech/shaders/Lanbai_PointSprites.shader):
//    4 vertices per star with the same POSITION = direction * 9000, UV0 = corner (-1..1), UV1.x = flux,
//    COLOR.rgb = linear colour.  (Twinkle is ignored: the stars never twinkle, bible §6·9.)
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
        _Gain ("Star gain if the global is not set", Float) = 1
        _MinFWHM ("Minimum drawn size FWHM in pixels", Range(0.8, 3)) = 1.4
        _FluxCut ("Hide reflected stars dimmer than", Float) = 0
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
            float _Gain, _MinFWHM, _FluxCut;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 corner : TEXCOORD0;
                half3 col : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 d = normalize(mul((float3x3)unity_ObjectToWorld, v.vertex.xyz));   // star direction (world)
                float3 up = normalize(_Axis.xyz);
                float3 C = _SphereC.xyz;
                float rho = _SphereC.w;
                float3 E = _WorldSpaceCameraPos;                                        // this eye (SPS-I: per eye)
                // convex-mirror image point: start at the apex, iterate the bisector condition
                float3 P = C + rho * up;
                [unroll] for (int k = 0; k < 4; k++)
                    P = C + rho * normalize(d + normalize(E - P));
                float3 n = normalize(P - C);
                float3 toE = normalize(E - P);
                // visible only if the star is above the mirror's horizon and P lies on the face disc
                float axial = length((P - C) - dot(P - C, up) * up);
                float ok = step(0.0, dot(d, n)) * step(0.0, dot(toE, n)) * step(axial, _Axis.w * 1.02);
                float g = LanbaiMirrorStarGain(_Gain);
                float3 F = LanbaiSchlick(_FaceF0.rgb, dot(n, toE));
                float flux = v.uv1.x * g * ok * step(_FluxCut, v.uv1.x * g);
                float3 col = v.color.rgb * flux * (F + _FaceK.y);

                float3 centre = lerp(P, E, 0.005);
                float dist = distance(centre, E);
                float rDraw = (_MinFWHM / 1.4133) * LanbaiPixelAngle() * dist;
                float4 vc = mul(UNITY_MATRIX_V, float4(centre, 1.0));
                vc.xy += v.uv0 * (2.0 * rDraw) * ok;                                   // collapsed when not visible
                o.pos = mul(UNITY_MATRIX_P, vc);
                o.corner = v.uv0;
                o.col = (half3)col;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                // Gaussian of sigma = 0.6 rDraw over a quad of half-size 2 rDraw (same as Lanbai/PointSprites)
                float r2 = dot(i.corner, i.corner) * 4.0;
                float gsn = exp(-r2 / (2.0 * 0.36));
                return half4(i.col * gsn, 0);
            }
            ENDCG
        }
    }
    Fallback Off
}
