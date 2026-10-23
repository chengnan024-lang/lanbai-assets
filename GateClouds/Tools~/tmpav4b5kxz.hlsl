#define _PART_RIP 1
#include "unity_stub.hlsl"

    #include "unity_stub.hlsl"
    #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"   // the canonical copy (has LanbaiNearFade + LanbaiCentreEyePos); 2026-10-23

    sampler2D _MainTex; float4 _MainTex_ST;
    float4 _Tint; float _Intensity, _EmissionScale;
    float4 _TearAcrossOS, _TearAxisOS; float _OpenMin;
    float _Atten; float4 _HazeColor;
    float _RipFront;
    float4 _FlapOuterNear, _FlapOuterFar, _FlapInner, _MoonRim, _LipGlow;
    float _MoonRimMul, _OutlinePx, _SheenMul, _FlutterAmp, _Cutoff, _OuterSky, _FoldBleed;
    float4 _FibreRoot, _FibreTip; float _SwayAmp, _SwayHz;
    float _BreathEV, _BreathPeriod;
    float _SoftFade, _EdgeFadePow; float4 _NearFadeM;
    float _DepthPrepass;
    float _CloudFadeM, _RimDesat; float4 _LanesRect; sampler2D _LanesTex;
    float4 _Udon_CloudTop;     // global: x = world y of the cloud-sea top this frame; w > 0 = set
    float4 _Udon_GateOrigin;   // v5 global: xyz = GateRoot.position this frame (noise in the cloud-sea frame)
    float4 _FlapEdge; float _FlapTrans;
    float4 _FootMist; float _FootMistM; float4 _FootCloudEdge, _FootCloudCore, _CardV; float _FootGlow; float4 _FootLobe;
    float4 _FootCut, _SkyCloud; float _SkyRim, _SkyNear; float4 _LaneW, _LaneFoot, _LaneNear; float _NearFootCut, _FootAddK;

    float Hash3(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
    float VNoise(float3 x)
    {
        float3 i = floor(x); float3 f = frac(x); f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(Hash3(i), Hash3(i + float3(1, 0, 0)), f.x), lerp(Hash3(i + float3(0, 1, 0)), Hash3(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(Hash3(i + float3(0, 0, 1)), Hash3(i + float3(1, 0, 1)), f.x), lerp(Hash3(i + float3(0, 1, 1)), Hash3(i + float3(1, 1, 1)), f.x), f.y), f.z);
    }
    // 0 below the cloud top, ragged 40 m ramp above it (the white tears INTO the cloud sea)
    // v5: soft 60 m billows (+-12 m), sampled in the cloud-sea frame (Tear_Root moves with GateRoot)
    float CloudFootFadeR(float3 posWS, float lo, float hi)
    {
        if (_Udon_CloudTop.w <= 0.0) return 1.0;
        float z = posWS.y - _Udon_CloudTop.x + (VNoise((posWS - _Udon_GateOrigin.xyz) / 60.0) - 0.5) * 24.0;
        return smoothstep(lo, hi, z);
    }
    float CloudFootFade(float3 posWS) { return CloudFootFadeR(posWS, 4.0, 4.0 + _CloudFadeM); }
    // v6: the lens's deep ragged cut (cell, amplitude in m; the cloud-sea frame)
    float CloudFootFadeN(float3 posWS, float lo, float hi, float cell, float amp)
    {
        if (_Udon_CloudTop.w <= 0.0) return 1.0;
        float z = posWS.y - _Udon_CloudTop.x + (VNoise((posWS - _Udon_GateOrigin.xyz) / max(cell, 1.0)) - 0.5) * amp;
        return smoothstep(lo, hi, z);
    }
    float CardEdge(float2 uv)
    {
        float e = 2.0 * max(abs(uv.x - 0.5), abs(uv.y - 0.5));
        return 1.0 - smoothstep(0.75, 1.0, e);
    }

    // Udon globals (never set = 0)
    float _Udon_TearOpen, _Udon_RipProgress, _Udon_TearHide, _Udon_TearBreath;

    struct appdata
    {
        float4 vertex : POSITION;
        float3 normal : NORMAL;
        float4 color : COLOR;
        float2 uv0 : TEXCOORD0;
        float2 uv1 : TEXCOORD1;
        float2 uv2 : TEXCOORD2;
        UNITY_VERTEX_INPUT_INSTANCE_ID
    };

    // bible: width 18 % -> 30 % of H. Meshes are modelled at 30 %; every vertex moves with the point it hangs from.
    float3 TearOpenOffset(appdata v)
    {
        float w = lerp(_OpenMin, 1.0, saturate(_Udon_TearOpen));
        return _TearAcrossOS.xyz * (v.uv1.x * (w - 1.0));
    }
    
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile _ SOFTPARTICLES_ON
            #pragma shader_feature_local _PART_LENS _PART_RIP _PART_FLAP _PART_FIBRE _PART_HALO _PART_SHAFT _PART_FOLDS _PART_CLOUDGLOW _PART_FOOTCLOUD _PART_SKYLINE _PART_LANE

            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 data : TEXCOORD1;      // uv1.xy, uv2.xy
                float4 color : TEXCOORD2;
                float3 posWS : TEXCOORD3;
                float3 nrmWS : TEXCOORD4;
                float4 projPos : TEXCOORD5;
                float4 fade : TEXCOORD6;      // x = shaft fades, y = breathing gain
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 p = v.vertex.xyz + TearOpenOffset(v);
                float t = _Time.y;
                o.fade = float4(1, 1, 1, 1);

            #if defined(_PART_FLAP)
                // slow flutter, growing toward the torn edge (bible: giants move <= 0.5 deg/s; 2 m at >= 0.5 km is tiny)
                float ph = v.uv1.y * 6.2832 + v.uv0.x * 4.0;
                p += normalize(v.normal) * (_FlutterAmp * v.color.a * sin(t * 0.5236 + ph));    // 12 s period
            #endif
            #if defined(_PART_FIBRE)
                // 0.3 Hz sway (bible), bending more toward the tip; fibres run across, so sway along the axis
                float s = v.uv0.y * v.uv0.y;
                p += _TearAxisOS.xyz * (_SwayAmp * s * sin(6.2832 * (_SwayHz * t + v.uv1.y)));
            #endif
            #if defined(_PART_SHAFT)
                // beam billboard: each cross-section's two centre-line vertices are pushed apart across the view.
                // The beam axis rides in COLOR.rgb (object space, *0.5+0.5): normals cannot carry it through FBX.
                float3 axisOS = normalize(v.color.rgb * 2.0 - 1.0);
                float3 camOS = mul(unity_WorldToObject, float4(_WorldSpaceCameraPos, 1)).xyz;
                float3 toCam = camOS - p;
                float3 side = normalize(cross(axisOS, toCam) + 1e-6);
                p += side * ((v.uv0.x - 0.5) * 2.0 * v.uv2.x);
                // side-view fade (LanbaiEdgeOnFade for an axial billboard) and near-eye fade
                float3 axisWS = normalize(mul((float3x3)unity_ObjectToWorld, axisOS));
                float3 pw = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                float3 V = normalize(_WorldSpaceCameraPos - pw);
                float perp = length(cross(axisWS, V));
                o.fade.x = pow(saturate(perp * 1.4), _EdgeFadePow) * LanbaiNearFade(pw, _NearFadeM.x, _NearFadeM.y);
            #endif
            #if defined(_PART_HALO)
                // breathing +-0.25 EV, 8 s sine; the outer cards lag a little (uv1.y) like a breath spreading
                float sn = (_Udon_TearBreath != 0) ? _Udon_TearBreath : sin(6.2832 * (t / _BreathPeriod - v.uv1.y));
                o.fade.y = exp2(_BreathEV * sn);
            #endif

                o.pos = UnityObjectToClipPos(float4(p, 1));
                o.posWS = mul(unity_ObjectToWorld, float4(p, 1)).xyz;
                o.nrmWS = UnityObjectToWorldNormal(v.normal);
                o.uv = v.uv0;
                o.data = float4(v.uv1, v.uv2);
                o.color = v.color;
                o.projPos = ComputeScreenPos(o.pos);
                o.projPos.z = -UnityObjectToViewPos(p).z;         // eye depth of the DEFORMED vertex (not v.vertex)
                return o;
            }

            // own distance attenuation (sky objects): premultiplied colour toward the haze
            float3 Atten(float3 rgb, float a, float3 posWS)
            {
                float T = exp(-distance(posWS, _WorldSpaceCameraPos) * _Atten);
                return rgb * T + _HazeColor.rgb * a * (1 - T);
            }

            float4 frag(v2f i, fixed facing : VFACE) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float show = 1.0 - saturate(_Udon_TearHide);
                float2 uv = i.uv;

            #if defined(_PART_LENS)
                // premultiplied: the undyed white covers the sky (A = 1), the lip glow only adds light (A = 0)
                float4 tx = tex2D(_MainTex, uv);
                // v5: the foot turns into lit mist over _FootMistM m, then is CUT (alpha) just under the cloud top
                float up = CloudFootFadeN(i.posWS, 0.0, _FootMistM, 45.0, 40.0);
                float cut = CloudFootFadeN(i.posWS, _FootCut.x, _FootCut.y, _FootCut.z, _FootCut.w);   // v6: deep, ragged
                float3 rgb = lerp(_FootMist.rgb * tx.a, tx.rgb * _EmissionScale, up) * (_Intensity * cut);
                return float4(Atten(rgb, tx.a * cut, i.posWS), tx.a * cut) * show;

            #elif defined(_PART_RIP)
                // the crack runs along its length: a pointed front sweeps from u = 0 to 1 as its window fills
                float ws = i.data.z, we = i.data.w;
                float prog = saturate((_Udon_RipProgress - ws) / max(we - ws, 1e-3));
                float front = prog * (1.0 + 2.0 * _RipFront) - _RipFront;
                float wm = pow(saturate((front - uv.x) / _RipFront), 0.7);
                float2 uvr = float2(uv.x, 0.5 + (uv.y - 0.5) / max(wm, 1e-3));
                float4 tx = tex2D(_MainTex, uvr);
                float vis = step(0.0005, wm);
                float3 rgb = tx.rgb * (_EmissionScale * _Intensity) * vis;
                float a = tx.a * vis;
                return float4(Atten(rgb, a, i.posWS), a) * show;

            #elif defined(_PART_FLAP)
                // indigo silk, two-sided. Texture: R = distance inside the torn edge / 24 m, G = silk, B = loose threads,
                // A = cloth coverage. Vertex colour: R/G = tear light on inner/outer face, B = fold -> torn edge.
                // v4 (gate round 3): TWO thin welded flaps = the sky's own cloth peeling back. OUTER face = the sky colour
                // behind it (no halo: the cloth occludes the glow), so it vanishes against the sky and reads only where
                // it covers the white; INNER face (seen only on the rolled lip, vertex B > 0.6) wound-lit x (0.15 + 0.6 R).
                float4 tx = tex2D(_MainTex, uv);
                // v5: the DYED cloth. Outer face #141726 -> #0C0E18 (fold -> torn edge), inner face wound-lit, the last
                // 1.2-6 m before the torn edge (and the loose threads beyond it) transmit the wound light (#8F86D0)
                float silk = 1.0 + (tx.g - 0.5) * 0.8;
                float3 Vd = normalize(i.posWS - _WorldSpaceCameraPos);
                float3 outer = lerp(_FlapOuterNear.rgb, _FlapOuterFar.rgb, i.color.b) * silk;
                float3 inner = lerp(_FlapInner.rgb, _FlapInner.rgb * 1.4, i.color.b) * ((0.25 + 0.75 * i.color.r) * silk);
                float3 col = (facing > 0) ? outer : inner;       // normals = OUTER face
                float ndv = abs(dot(normalize(i.nrmWS), -Vd));
                col += _FlapInner.rgb * (0.35 * pow(1.0 - ndv, 4.0) * (0.05 + i.color.r));
                float distM = tx.r * 24.0;
                col += _FlapEdge.rgb * (_FlapTrans * pow(smoothstep(6.0, 1.2, distM), 1.5));
                col *= _Intensity;
                // cutout + alpha-to-coverage (MSAA); the sharpened alpha keeps frayed threads from shimmering in VR
                float cov = tx.a * show * CloudFootFade(i.posWS);   // v3b: the low flaps dissolve into the cloud top too
                clip(cov - _Cutoff);
                float a2c = saturate((cov - _Cutoff) / max(fwidth(cov), 1e-4) + 0.5);
                float T = exp(-distance(i.posWS, _WorldSpaceCameraPos) * _Atten);
                return float4(lerp(_HazeColor.rgb, col, T), a2c);

            #elif defined(_PART_FIBRE)
                float4 tx = tex2D(_MainTex, uv);
                float3 col = lerp(_FibreRoot.rgb, _FibreTip.rgb, pow(saturate(uv.y), 0.8));
                float k = tx.a * 0.95 * _Intensity;
                return float4(Atten(col * k, 0, i.posWS), 0) * show;

            #elif defined(_PART_HALO)
                float4 tx = tex2D(_MainTex, uv);                  // RGB = halo fill (#8275D0) x falloff
                // v4: per-card gain in UV2.x (the inner card x 2.8: the breathing #5B57A1 1-3 deg from the lips)
                float gk = (i.data.z > 0.0) ? i.data.z : 1.0;
                float3 rgb = tx.rgb * _Tint.rgb * (_Intensity * i.fade.y * gk) * CardEdge(uv) * CloudFootFade(i.posWS);
                return float4(Atten(rgb, 0, i.posWS), 0) * show;

            #elif defined(_PART_SHAFT)
                float4 tx = tex2D(_MainTex, uv);
                float k = tx.a * i.fade.x * _Intensity;
                #if defined(SOFTPARTICLES_ON)
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.projPos)));
                    k *= saturate((sceneZ - i.projPos.z) / _SoftFade);
                #endif
                return float4(_Tint.rgb * k, 0) * show;           // _Tint = one beam's fill (#4C4A74 x 0.5)

            #elif defined(_PART_FOLDS)
                // premultiplied: RGB = tear light raking the ridges, A = the valleys shading the sky
                float4 tx = tex2D(_MainTex, uv);
                float ke = CardEdge(uv) * CloudFootFade(i.posWS);
                float3 rgb = tx.rgb * _Tint.rgb * _Intensity * ke;
                float a = tx.a * _Intensity * ke;
                return float4(Atten(rgb, 0, i.posWS), a) * show;

            #elif defined(_PART_FOOTCLOUD)
                // v5: a cloud card in front of the foot, BACKLIT by the wound (premultiplied, queue 2989)
                float4 tx = tex2D(_MainTex, uv);
                float lum = dot(tx.rgb, float3(0.2126, 0.7152, 0.0722));
                float thick = smoothstep(0.70, 1.0, tx.a);
                float3 col = lerp(_FootCloudEdge.rgb, _FootCloudCore.rgb, thick);
                col *= (0.6 + 0.7 * min(lum / 0.35, 1.0)) * lerp(0.75, 1.35, smoothstep(_CardV.x, _CardV.y, uv.y));
                col *= i.color.r * i.color.g * _Intensity;       // R = near the axis (0.35..1), G = height lift (0.45..1)
                float a = tx.a * CloudFootFadeR(i.posWS, -8.0, 6.0);
                return float4(col * a, a) * show;

            #elif defined(_PART_SKYLINE)
                // v6: the sea's billows in front of the foot, parted round the slot (premultiplied, queue 2989). A = skyline
                // alpha, R = backlit rim. The face toward the bus is the billows' shadow side (moonlit cloud colour); the
                // rim glows brightest beside the slot (uv.x 0.5).
                float4 tx = tex2D(_MainTex, uv);
                float a = tx.a * _Intensity;
                float nearS = exp(-pow((uv.x - 0.5) / max(_SkyNear * 0.5, 1e-3), 2.0));
                float3 col = _SkyCloud.rgb * a + _FootMist.rgb * (tx.r * a * _SkyRim * (0.12 + 0.88 * nearS));
                return float4(Atten(col, a, i.posWS), a) * show;

            #elif defined(_PART_LANE)
                // v6: Blend DstColor One: out = dst x (1 + lane). The quad lies on the cloud top from the foot (uv.y 0) toward
                // the bus (uv.y 1); the glitter path follows the eye: azimuth of this point vs the foot's, seen from the eye
                float3 footWS = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float2 dp = i.posWS.xz - _WorldSpaceCameraPos.xz;
                float2 df = footWS.xz - _WorldSpaceCameraPos.xz;
                float daz = degrees(acos(clamp(dot(normalize(dp), normalize(df)), -1.0, 1.0)));
                float S = length(unity_ObjectToWorld._m00_m10_m20);
                float fr = saturate((length(df) - length(dp)) / max(_LaneW.z, 1.0));      // 0 at the foot -> 1 toward the eye
                float w = lerp(_LaneW.x, _LaneW.y, fr);
                float inl = exp(-(daz / w) * (daz / w)) * saturate((length(df) + 60.0 - length(dp)) / 120.0) * (1.0 - smoothstep(0.7, 1.0, fr));
                float3 col = lerp(_LaneFoot.rgb, _LaneNear.rgb, fr) * (inl * (1.0 - 0.45 * fr) * _Intensity);
                return float4(col, 0) * show;

            #else // _PART_CLOUDGLOW
                float4 tx = tex2D(_MainTex, uv);                  // Halo_512: A = radial falloff
                // v3: the ring roots' shadow lanes. Object space (Unity) -> tear frame metres: x = -os.x S, y = -os.z S
                float S = length(unity_ObjectToWorld._m00_m10_m20);
                float3 os = mul(unity_WorldToObject, float4(i.posWS, 1)).xyz;
                float2 cf = float2(-os.x, -os.z) * S;
                float2 luv = float2((cf.x - _LanesRect.x) / (_LanesRect.y - _LanesRect.x), (cf.y - _LanesRect.z) / (_LanesRect.w - _LanesRect.z));
                float k = tx.a * _Intensity * tex2D(_LanesTex, luv).r;
                // v6 (tech r4 B1.3): the ADDITIVE material adds no flat glow within 1.5 half widths of the foot
                float rf = length(cf) / max(_FootLobe.y * S, 1.0);
                k *= lerp(1.0, smoothstep(1.5, 3.0, rf), _NearFootCut);
                // v5: the cloud wall under the white glows (a lobe round the foot, tear-frame metres x S)
                float2 fl = float2((cf.x - _FootLobe.x * S) / max(1.6 * _FootLobe.y * S, 1.0), (cf.y - _FootLobe.z * S) / max(_FootLobe.w * S, 1.0));
                k += _FootGlow * exp(-dot(fl, fl)) * 3.6 * lerp(1.0, _FootAddK, _NearFootCut);   // v6: x 0.25 on the additive
                #if defined(SOFTPARTICLES_ON)
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.projPos)));
                    k *= saturate((sceneZ - i.projPos.z) / _SoftFade);
                #endif
                return float4(_Tint.rgb * k, 0) * show;
            #endif
            }
            