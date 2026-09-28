// =====================================================================================================
//  Lanbai / PointSprites        蓝白 · stars, town lights, the sea of lights, palace specks, far lamps
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Compile and check in Unity 2022.3 + VRChat SDK. !!!
//
//  WHY: a light point stored as texels (a star in a cubemap, a street light in a 2048 tile) is sub-pixel in
//  VR. It sparkles and crawls every time the head moves and vanishes in the mip chain. Here every point is a
//  tiny camera-facing Gaussian, never narrower than _MinFWHM pixels on screen, with its brightness conserved when it
//  is drawn larger than it really is. One draw call per mesh (5 000-10 000 points = 10-20 k triangles).
//
//  MESH CONTRACT (the cloud side ships these as FBX; extract_stars.py writes the star one):
//    each point = 1 quad = 4 vertices with the SAME POSITION (the point) and UV0 = corner (-1..1, -1..1)
//    POSITION  finite mode : the point in object space (metres)
//              infinite mode: direction * 9000 (the length only makes the bounds huge so it is never culled;
//                             the shader normalises it)
//    UV1.x     flux  (linear; finite: surface brightness when resolved; infinite: peak brightness at the minimum size)
//    UV1.y     size  (finite: physical radius in metres; infinite: ignored)
//    COLOR     rgb = linear colour 0..1 (write LINEAR values; Unity does not convert vertex colours)
//              a   = twinkle amount 0..1
//    UV2.x     twinkle phase 0..1;  UV2.y twinkle frequency (Hz, clamped to <= 1.5 Hz: VR comfort)
//  Import: Mesh Compression Off, Read/Write off, Optimize Mesh on, Weld Vertices OFF, normals None.
// =====================================================================================================
Shader "Lanbai/PointSprites"
{
    Properties
    {
        [Toggle(LANBAI_INFINITE)] _Infinite ("Infinite (stars: position is a direction)", Float) = 0
        [HDR] _Tint ("Tint (HDR)", Color) = (1, 1, 1, 1)
        _Gain ("Gain (Udon ramps this)", Float) = 1
        _MinFWHM ("Minimum drawn size: FWHM in pixels", Range(0.8, 3)) = 1.4
        _Falloff ("Unresolved dimming (1 = physical, 0 = none)", Range(0, 1)) = 0.6
        _FluxCut ("Hide points dimmer than (flux * gain)", Float) = 0
        _FarDist ("Infinite mode: draw distance (m, < camera far clip)", Float) = 9000
        _Atten ("Finite mode: extinction per metre (exp(-d * atten))", Float) = 0.00008
        _Twinkle ("Twinkle amount (x vertex alpha)", Range(0, 0.4)) = 0
        [Toggle(LANBAI_MIRROR_Y)] _MirrorY ("Mirror copy (flip Y, draw only below the mirror plane)", Float) = 0
        _MirrorGain ("Mirror copy gain", Range(0, 1)) = 0.81
        [IntRange] _StencilRef ("Stencil Ref (mirror copies: 128)", Range(0, 255)) = 0
        [Enum(UnityEngine.Rendering.CompareFunction)] _StencilComp ("Stencil Comp (mirror copies: Equal)", Float) = 8
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-100" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" "PreviewType" = "Plane" }
        Blend One One
        ZWrite Off
        ZTest LEqual
        Cull Off
        Stencil { Ref [_StencilRef] ReadMask 128 WriteMask 0 Comp [_StencilComp] }

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #pragma shader_feature_local LANBAI_INFINITE
            #pragma shader_feature_local LANBAI_MIRROR_Y
            #include "UnityCG.cginc"
            #include "LanbaiVR.cginc"

            half4 _Tint;
            float _Gain, _MinFWHM, _Falloff, _FluxCut, _FarDist, _Atten, _Twinkle, _MirrorGain;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
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

                float flux = v.uv1.x * _Gain;
                float pxAng = LanbaiPixelAngle();
            #if defined(LANBAI_INFINITE)
                float3 dir = normalize(mul((float3x3)unity_ObjectToWorld, v.vertex.xyz));
                #if defined(LANBAI_MIRROR_Y)
                    dir.y = -dir.y;
                    flux *= _MirrorGain * step(dir.y, 0.0);
                #endif
                float dist = _FarDist;
                float3 centre = _WorldSpaceCameraPos + dir * dist;
                float rMin = (_MinFWHM / 1.4133) * pxAng * dist;   // FWHM = 2.355 * 0.6 * rDraw
                float rDraw = rMin;
                float peak = flux;
            #else
                float3 centre = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1)).xyz;
                float dist = distance(centre, _WorldSpaceCameraPos);
                float scale = length(unity_ObjectToWorld._m00_m10_m20);
                float rPhys = v.uv1.y * scale;
                float rMin = (_MinFWHM / 1.4133) * pxAng * dist;   // FWHM = 2.355 * 0.6 * rDraw
                float rDraw = max(rPhys, rMin);
                // unresolved: spread over rDraw, dim by (rPhys/rDraw)^(2*falloff)
                float peak = flux * pow(saturate(rPhys / rDraw), 2.0 * _Falloff) * exp(-dist * _Atten);
            #endif
                // twinkle, slow (<= 1.5 Hz); vertex alpha says how much this point is allowed to twinkle
                float hz = min(v.uv2.y, 1.5);
                peak *= 1.0 + _Twinkle * v.color.a * sin(6.2831853 * (hz * _Time.y + v.uv2.x));

                // camera-facing quad in view space; half-size = 2 * rDraw so a Gaussian of sigma = 0.6 rDraw fits
                float4 vc = mul(UNITY_MATRIX_V, float4(centre, 1));
                vc.xy += v.uv0 * (2.0 * rDraw);
                o.pos = mul(UNITY_MATRIX_P, vc);
                o.corner = v.uv0;
                o.col = (half3)(v.color.rgb * _Tint.rgb * peak);
                // hide points below the cut (collapse the quad)
                if (peak < _FluxCut) o.pos = float4(0, 0, -1, 1);
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                // Gaussian, sigma = 0.3 in corner units (0.6 rDraw); the quad edge is at 3.3 sigma
                float r2 = dot(i.corner, i.corner);
                half g = (half)exp(-r2 * 5.5555);
                return half4(i.col * g, 0);
            }
            ENDCG
        }
    }
    Fallback Off
}
