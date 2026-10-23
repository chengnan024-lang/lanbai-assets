// =====================================================================================================================
//  Lanbai / Overlay  v2        蓝白 · 全屏遮罩球：投入的黑、晨从黑里亮起、白、白收缩进灯里、第二次白、出生的淡入
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; slang syntax check only). Compile in Unity 2022.3 + VRChat SDK. !!!
//
//  Bible v2.1 §1.8 (全屏遮罩球), E17, §6·5→6, §6·9→10, §6·10→11, §6·11→12; calib_final §D.
//  - Unity's built-in Sphere (radius 0.5) scaled x3 = r 1.5 m. Every client moves ITS OWN sphere to ITS OWN head
//    position every frame (position only, never rotation: Overlay/Runtime/LanbaiOverlay.cs). Cull Front + ZTest Always
//    + queue Overlay+100: it covers everything, including things nearer than 1.5 m. The only ZTest Always in the piece.
//  - It renders BEFORE PPv2, so it is graded: the colour is the calib §D fill of the grade in force, x 2^(-dEV) of the
//    EXPO helpers (the component does this multiplication; the shader only draws what it is given).
//  - Dither: hashed on the OBJECT-SPACE direction normalize(v.vertex.xyz) (identical for both eyes; the sphere never
//    rotates, so it is also the world direction): no binocular shimmer in a 29 s full field of white.
//  - Alpha, two modes (global _Udon_OverlayCurve.z):
//      0 FLAT   alpha = _Udon_OverlayColor.a (one value for every direction)
//      1 CURVE  alpha(dir) = EvOverlayAlpha(saturate((tau - lead(dir)) / T), Lfrom, Lto, Lscene, Lover)
//               ONE curve (Lscene is a scalar, built on the extreme view direction, E17); directions only shift its start:
//               lead(dir) = leadElse, then for each lobe i in order: lead = lerp(lead, lead_i, m_i(dir)),
//               m_i = smoothstep over a soft edge (>= 30 deg, bible §1.8) outside the lobe's half angle.
//               With no lobe (all half angles <= 0) every direction runs the same curve, exactly as FLAT-with-a-curve.
//  - Breath: rgb x (1 + amount * sin(2 pi 0.1 Hz t)), amount = _Udon_OverlayCurve.w (the white of act 10: 0.02).
//
//  Globals (registration requested in Act04c_Inside/给总控.md; _Udon_OverlayColor was reserved for this):
//    _Udon_OverlayColor      rgb = fill (linear HDR) already x 2^(-dEV); a = alpha in FLAT mode
//    _Udon_OverlayCurve      x = tau (s since the curve's t0), y = T (s, per direction), z = mode (0 flat / 1 curve), w = breath
//    _Udon_OverlayLum        x = Lfrom, y = Lto, z = Lscene, w = Lover (relative linear luminance; floor 0.004 inside)
//    _Udon_OverlayLobe0..3   xyz = world direction (unit), w = half angle (deg; <= 0 = unused)
//    _Udon_OverlayLead       x..w = lead (s) of lobe 0..3
//    _Udon_OverlayLeadElse   x = lead (s) of every direction outside the lobes, y = soft edge (deg, clamped >= 30)
// =====================================================================================================================
Shader "Lanbai/Overlay"
{
    Properties
    {
        _DitherLSB ("Dither amplitude in 8-bit LSB", Range(0, 3)) = 1.5
    }
    SubShader
    {
        Tags { "Queue" = "Overlay+100" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" "PreviewType" = "Sphere" }
        Cull Front
        ZTest Always
        ZWrite Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"         // _Udon_Overlay*, declared once (chief engineer r1 #5)
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            float _DitherLSB;

            struct appdata
            {
                float4 vertex : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 dirOS : TEXCOORD0;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dirOS = v.vertex.xyz;
                return o;
            }

            // lens_tech.md appendix A: composite luminance moves geometrically from Lfrom to Lto (constant EV per second)
            float EvOverlayAlpha(float x, float Lfrom, float Lto, float Ls, float Lo)
            {
                float a = max(Lfrom, 0.004);
                float b = max(Lto, 0.004);
                float L = a * pow(b / a, saturate(x));
                float den = Ls - Lo;
                return (abs(den) < 1e-6) ? 1.0 : saturate((Ls - L) / den);
            }

            float LobeWeight(float3 d, float4 lobe, float softDeg)
            {
                if (lobe.w <= 0.0)
                    return 0.0;
                float c = dot(d, normalize(lobe.xyz));
                float cIn = cos(radians(min(lobe.w, 179.0)));
                float cOut = cos(radians(min(lobe.w + softDeg, 180.0)));
                return smoothstep(cOut, cIn, c);
            }

            float LeadOf(float3 d)
            {
                float soft = max(_Udon_OverlayLeadElse.y, 30.0);
                float lead = _Udon_OverlayLeadElse.x;
                lead = lerp(lead, _Udon_OverlayLead.x, LobeWeight(d, _Udon_OverlayLobe0, soft));
                lead = lerp(lead, _Udon_OverlayLead.y, LobeWeight(d, _Udon_OverlayLobe1, soft));
                lead = lerp(lead, _Udon_OverlayLead.z, LobeWeight(d, _Udon_OverlayLobe2, soft));
                lead = lerp(lead, _Udon_OverlayLead.w, LobeWeight(d, _Udon_OverlayLobe3, soft));
                return lead;
            }

            float3 LinearToSrgb(float3 x)
            {
                x = max(x, 0.0);
                return (x <= 0.0031308) ? 12.92 * x : 1.055 * pow(x, 1.0 / 2.4) - 0.055;
            }
            float3 SrgbToLinear(float3 x)
            {
                return (x <= 0.04045) ? x / 12.92 : pow((x + 0.055) / 1.055, 2.4);
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d = normalize(i.dirOS);
                float alpha = _Udon_OverlayColor.a;
                if (_Udon_OverlayCurve.z > 0.5)
                {
                    float T = max(_Udon_OverlayCurve.y, 1e-3);
                    float x = (_Udon_OverlayCurve.x - LeadOf(d)) / T;
                    alpha = EvOverlayAlpha(x, _Udon_OverlayLum.x, _Udon_OverlayLum.y, _Udon_OverlayLum.z, _Udon_OverlayLum.w);
                }
                float breath = 1.0 + _Udon_OverlayCurve.w * sin(6.2831853 * 0.1 * _Time.y);
                float3 c = max(_Udon_OverlayColor.rgb, 0.0) * breath;
                // object-space dither (same value in both eyes): +-_DitherLSB 8-bit codes, triangular
                float n = LanbaiSkyDither(d) * (_DitherLSB / 255.0);
                // 总导演终审 #9: exact sRGB (UnityCG's fast gamma approximation crushed act 5's #030409 to #000000)
                c = SrgbToLinear(max(LinearToSrgb(c) + n, 0.0));
                return float4(c, saturate(alpha));
            }
            ENDCG
        }
    }
    Fallback Off
}
