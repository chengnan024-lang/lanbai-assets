// =====================================================================================================
//  Lanbai/SeaSpecks   蓝白 · far lamp points in the sea (bible §6·7b '远处点点灯火 PalaceSpecks_Points.fbx') and the
//                     20–30 golden palace points inside the act-8 sea ceiling (§6·8 构图 8-i; they go LAST, §6·8 8-ii)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with DXC + Unity 2022.3 CGIncludes (Common/Tools~/compile_check), never in Unity. !!!
//
//  MESH CONTRACT = lens_tech's Lanbai_PointSprites (finite mode): every point = 1 quad = 4 vertices with the SAME
//  POSITION (object space, m) and UV0 = corner (-1..1); UV1.x = flux (linear peak at the minimum size), UV1.y = radius m;
//  COLOR rgb = linear colour, a = flicker amount 0..1; UV2.x = flicker phase, UV2.y = flicker Hz (clamped <= 1.5 Hz).
//  Light: no fog colour, own extinction exp(-d * _Atten) (bible: 灯焰与门光 '_FogMode 2, _Atten 0.004').
//  Ceiling mode (_CeilingMode 1): each point fades with the ceiling's dissolve, LAST in its own pixel
//  (LanbaiCeilingLampProgress from LanbaiSea.cginc, same _DissolveTime / _DissolveFront / _DissolvePixel as the ceiling
//  material). The points are ADDED ON TOP of the ceiling and fade only by their own progress (bible: 宫灯最后走).
//  The points sit ABOVE the ceiling (in the water), but the ceiling's inner disc is opaque and writes depth: so in ceiling
//  mode every point is moved along its own eye ray to max(_CeilingGap, _CeilingGapRel x distance) BELOW the plane
//  (_Udon_SeaLevel = the ceiling's y; the relative gap beats 24-bit depth at 2 km), its radius scaled to keep its angular
//  size, and dimmed by the water it shines through: exp(-_WaterAtten.rgb x path), red absorbed most, so a far lamp turns
//  cooler and darker, never redder. Colour: the vertex colour is the lamp's SCREEN target in the dark (gold #E0A860,
//  README_Sea接口 §2.6), not the full-flame fill.
//  Draw order: Transparent-5 (2995): AFTER the ceiling's transparent edge / fade materials (2990), before the cabin
//  glass (3000). (Final review BLOCKER: at 2980 the fading ceiling covered every point at 956.36.)
//  The mesh's bounds must enclose the drawn positions (the builder sets 4 km bounds).
// =====================================================================================================
Shader "Lanbai/SeaSpecks"
{
    Properties
    {
        _Tint ("Tint linear", Vector) = (1, 1, 1, 1)
        _Gain ("Gain  driver", Float) = 1
        _MinFWHM ("Minimum FWHM px", Range(0.8, 3)) = 1.4
        _Atten ("Extinction per m", Float) = 0.004
        _Flicker ("Flicker amount", Range(0, 0.3)) = 0.06
        _CeilingMode ("Ceiling mode  act 8", Float) = 0
        _CeilingGap ("Ceiling mode  min m below the plane", Float) = 0.5
        _CeilingGapRel ("Ceiling mode  gap as a fraction of the distance", Float) = 0.02
        _WaterAtten ("Ceiling mode  water extinction per m  rgb", Vector) = (0.024, 0.020, 0.017, 0)
        _DissolveTime ("Dissolve clock", Float) = -1
        _DissolveFront ("Dissolve front s", Float) = 4
        _DissolvePixel ("Dissolve per pixel s", Float) = 5
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-5" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
            #include "LanbaiSea.cginc"                   // LanbaiCeilingLampProgress (+ _DissolveTime / Front / Pixel)

            float4 _Tint, _WaterAtten;
            float _Gain, _MinFWHM, _Atten, _Flicker, _CeilingMode, _CeilingGap, _CeilingGapRel;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                float4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 col : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float t = _Udon_T > 0.0 ? _Udon_T : _Time.y;
                float3 P = mul(unity_ObjectToWorld, float4(v.vertex.xyz, 1.0)).xyz;
                float3 eye = LanbaiCentreEyePos();
                float3 toP = P - eye;
                float dist = length(toP);
                float rScale = 1.0;
                float3 waterT = 1.0;
                if (_CeilingMode > 0.5)
                {
                    float3 dirP = toP / max(dist, 1e-3);
                    if (dirP.y > 1e-3 && P.y > _Udon_SeaLevel - _CeilingGap)
                    {
                        float tSurf = (_Udon_SeaLevel - eye.y) / dirP.y;            // where the ray meets the water
                        float gap = max(_CeilingGap, _CeilingGapRel * tSurf);
                        float tp = max(tSurf - gap / dirP.y, 0.05);
                        waterT = exp(-_WaterAtten.rgb * max(dist - tSurf, 0.0));
                        rScale = tp / max(dist, 1e-3);
                        P = eye + dirP * tp;
                        toP = P - eye;
                        dist = tp;
                    }
                }
                float cov;
                float r = v.uv1.y * rScale + LanbaiInflate(v.uv1.y * rScale, dist, _MinFWHM, cov);
                float3 fwd = -toP / max(dist, 1e-3);
                float3 rightV = normalize(cross(float3(0.0, 1.0, 0.0), fwd) + float3(1e-5, 0.0, 0.0));
                float3 upV = cross(fwd, rightV);
                o.pos = UnityWorldToClipPos(P + (rightV * v.uv0.x + upV * v.uv0.y) * r);
                o.uv = v.uv0;
                float hz = min(v.uv2.y, 1.5);
                float fl = 1.0 - _Flicker * v.color.a * (0.5 + 0.5 * sin(6.2831853 * (hz * t + v.uv2.x)));
                // ceiling mode: the water term (waterT) IS the extinction; _Atten (the far city's own fade in 7b) is not applied
                float k = v.uv1.x * _Gain * fl * (_CeilingMode > 0.5 ? 1.0 : exp(-dist * _Atten)) * cov * cov;
                if (_CeilingMode > 0.5)
                    k *= 1.0 - LanbaiCeilingLampProgress(-fwd);
                o.col = v.color.rgb * _Tint.rgb * waterT * k;
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float r2 = dot(i.uv, i.uv);
                if (r2 > 1.0) discard;
                float g = exp(-r2 * 5.5) * (1.0 - r2);                 // gaussian, FWHM ~ 0.7 of the quad radius
                return float4(i.col * g, 0.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
