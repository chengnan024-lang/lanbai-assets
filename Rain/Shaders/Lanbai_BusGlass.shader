// =====================================================================================================
//  Lanbai / BusGlass        蓝白 · windows, windscreen, door glass, skylight, notice-case glass (bible §4.6, §5.5)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3 (Built-in RP); check in a headset with one eye closed, then the other. !!!
//
//  No GrabPass (lens_tech §2.6). Two passes, both two-sided:
//    TINT  Blend DstColor Zero      : what you see through the glass x old-glass green (#E9EFEA)
//    MAIN  Blend One OneMinusSrcAlpha (premultiplied), composited back to front:
//          rain on the OUTER face (static beads + running drops + wiper arcs, LanbaiRain.cginc)
//          -> dirt atlas (optional, UV0) -> the glass surface facing you (cabin reflection from inside:
//          baked cube, box-projected, x Fresnel x _Udon_CabinLightmap; world cube + lamps from outside).
//          From INSIDE each drop shows its REFRACTED view (two interfaces: flat pane, then the curved drop):
//          _Udon_ReflCube + the analytic lamps as small bright points; total internal reflection at the rim shows
//          the cabin. From OUTSIDE a drop is mostly transmissive (reflection + a darker rim), never a dark dot.
//  MESH CONTRACT: normals point OUT of the bus / case (toward the rain side); tangents imported; rain is mapped in
//  METRES on the pane's tangent / bitangent (UV-independent), pivot = object origin + _PivotOffset.
//  v2: stereo eye index in the fragment (M8), fog, wipers, flow frames, distance clock, case transmission.
// =====================================================================================================
Shader "Lanbai/BusGlass"
{
    Properties
    {
        [Header(Glass)]
        _Tint ("Old-glass tint (multiplies the view; sRGB as picked)", Color) = (0.914, 0.937, 0.918, 1)
        _TintStrength ("Tint strength", Range(0, 1)) = 1
        _BaseAlpha ("Base alpha", Range(0, 0.3)) = 0.06
        _DirtTex ("Dirt atlas RGBA (UV0; a = coverage, up to 0.25)", 2D) = "black" {}
        _DirtColor ("Dirt colour x (sRGB)", Color) = (0.427, 0.416, 0.376, 1)

        [Header(Cabin reflection  seen from inside)]
        _CabinCube ("Cabin cubemap (baked, tubes on)", Cube) = "black" {}
        _CabinReflGain ("Gain (night 1, day scenes 0.25)", Range(0, 2)) = 1
        _CabinBoxMin ("Box projection min (world)", Vector) = (-1.2, 0.3, -4.5, 0)
        _CabinBoxMax ("Box projection max (world)", Vector) = (1.2, 2.6, 4.5, 0)
        _CabinProbePos ("Cube capture position (world)", Vector) = (0, 1.6, 0, 0)

        [Header(Seen from outside  what lies behind the glass)]
        _BehindColour ("Behind the glass (notice case: the sheet, sRGB; bus: black = use the cabin cube)", Color) = (0, 0, 0, 1)
        _BehindLight ("Behind colour x: 0 = constant, 1 = _Udon_CaseLight (the case's own tube)", Range(0, 1)) = 0

        [Header(Rain)]
        _RainOverride ("Rain amount override (-1 = _Udon_RainAmount; area of beads left)", Range(-1, 1)) = -1
        _BeadNormal ("RainBeads_Vertical_Normal_1024 (linear, Default type)", 2D) = "bump" {}
        _BeadData ("RainBeads_Vertical_Data_1024 (linear)", 2D) = "black" {}
        _RunnerFlow ("GlassRunners_Flow_512x1024 (linear, uncompressed)", 2D) = "black" {}
        _BeadTile ("Bead tile (m)", Float) = 0.2
        _RunSpeedStill ("Runner speed, standing (m/s; bible 0.02-0.05)", Float) = 0.03
        _RunSpeedDrive ("Runner speed at road speed (m/s)", Float) = 0.22
        _RunDensityStill ("Runner density, standing ('occasional')", Range(0, 1)) = 0.05
        _RunDensityDrive ("Runner density at road speed", Range(0, 1)) = 0.75
        _RunSize ("Runner contact half-width (m)", Float) = 0.0030
        _TrailLife ("Trail life (s)", Float) = 6
        _StickSlip ("Stick-slip", Range(0, 1)) = 1
        _PaneFaceWind ("Pane faces the wind (windscreen 1): drag pushes drops UP", Range(0, 1)) = 0
        _PivotOffset ("Runner pivot offset (object space)", Vector) = (0, 0, 0, 0)
        _DropOpacity ("Drop opacity", Range(0, 1)) = 0.92
        _GlintLobe ("Lamp glint lobe (higher = smaller point)", Range(20, 2000)) = 350
        _DetailFade ("Runner detail fade: pixel size (m) where heads vanish", Float) = 0.004

        [Header(Wipers  windscreen only)]
        _Wipers ("Wiper blades sweep this pane (windscreen 1)", Range(0, 1)) = 0
        _WipeRefill ("Beads back after a wipe (s; bible 2-5)", Range(0.5, 8)) = 3
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        ZWrite Off
        Cull Off

        // ---------------------------------------------------------------------------- pass 1: tint
        Pass
        {
            Name "TINT"
            Tags { "LightMode" = "ForwardBase" }      // both passes ForwardBase: rendered in declaration order
            Blend DstColor Zero
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            half4 _Tint;
            half _TintStrength;
            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; UNITY_FOG_COORDS(0) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                fixed4 c = fixed4(lerp(half3(1, 1, 1), _Tint.rgb, _TintStrength), 1);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(1, 1, 1, 1));      // far glass: the fog, not the tint
                return c;
            }
            ENDCG
        }

        // ---------------------------------------------------------------------------- pass 2: glass + rain
        Pass
        {
            Name "MAIN"
            Tags { "LightMode" = "ForwardBase" }
            Blend One OneMinusSrcAlpha
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            #include "LanbaiRain.cginc"
            #include "LanbaiVR.cginc"

            sampler2D _DirtTex;
            float4 _DirtTex_ST;
            half4 _DirtColor;
            half _BaseAlpha;
            samplerCUBE _CabinCube;
            float4 _CabinCube_HDR;
            half _CabinReflGain;
            float4 _CabinBoxMin, _CabinBoxMax, _CabinProbePos;
            half4 _BehindColour;
            half _BehindLight;
            half _RainOverride;
            float _BeadTile, _RunSpeedStill, _RunSpeedDrive, _RunDensityStill, _RunDensityDrive, _RunSize, _TrailLife, _StickSlip;
            float _PaneFaceWind, _DropOpacity, _GlintLobe, _DetailFade, _Wipers, _WipeRefill;
            float4 _PivotOffset;
            float _Udon_CabinLightmap;        // bible §4.3: 1 = tubes on (unset = 0 -> no cabin reflection)
            float _Udon_CaseLight;            // bible §6·12: the notice case's tube, 0..1

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 tangent : TANGENT;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float3 wn : TEXCOORD2;
                float3 wt : TEXCOORD3;
                float3 wb : TEXCOORD4;
                float3 pivot : TEXCOORD5;
                UNITY_FOG_COORDS(6)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = TRANSFORM_TEX(v.uv, _DirtTex);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                o.wt = UnityObjectToWorldDir(v.tangent.xyz);
                o.wb = cross(o.wn, o.wt) * (v.tangent.w * unity_WorldTransformParams.w);
                o.pivot = mul(unity_ObjectToWorld, float4(_PivotOffset.xyz, 1.0)).xyz;
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            // box-projected lookup into the cabin cube (the cabin is small: parallax matters)
            float3 CabinCube(float3 P, float3 dir)
            {
                float3 rbmax = (_CabinBoxMax.xyz - P) / dir;
                float3 rbmin = (_CabinBoxMin.xyz - P) / dir;
                float3 rb = lerp(rbmin, rbmax, step(0.0, dir));
                float fa = min(min(rb.x, rb.y), rb.z);
                float3 d = P + dir * max(fa, 0.0) - _CabinProbePos.xyz;
                return DecodeHDR(texCUBElod(_CabinCube, float4(d, 1.0)), _CabinCube_HDR);
            }

            // the flow of water on this pane in one flow frame (fd = _Udon_FlowDir or _Udon_FlowDirB):
            // gravity + air drag. bible §4.6: side windows at road speed lean back 30-60 deg (drag 1 -> 50 deg,
            // 0.5 -> 26 deg); lift-off (air pushing up and back) drags them UP and back; the windscreen
            // (_PaneFaceWind 1) pushes them up its face. Returns the UNnormalised flow (its length gates runners).
            float2 PaneFlow(float4 fd, float3 N, float3 T, float3 Bt)
            {
                float3 up = float3(0, 1, 0);
                float2 g = float2(dot(-up, T), dot(-up, Bt));
                float drag = saturate(fd.w);
                float3 dW = fd.xyz;
                float2 dSide = float2(dot(dW, T), dot(dW, Bt));
                float2 upT = float2(dot(up, T), dot(up, Bt));
                float lift = saturate(dW.y * 1.5);
                float face = _PaneFaceWind * saturate(dot(N, -dW));
                return g * (1.0 - 0.3 * drag) + dSide * (drag * (0.84 + 2.0 * lift)) + upT * (1.6 * drag * face);
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // SPS-I: _WorldSpaceCameraPos is per eye only after this
                float3 P = i.wpos;
                float3 N = normalize(i.wn);                 // OUT of the bus
                float3 T = normalize(i.wt);
                float3 Bt = normalize(i.wb);
                float3 V = normalize(_WorldSpaceCameraPos - P);
                float3 I = -V;
                bool inside = dot(V, N) < 0.0;              // the eye is on the cabin side
                float t = _Time.y;
                float cabinOn = saturate(_Udon_CabinLightmap);

                // ---- the glass surface facing the eye: reflection
                float NdotV = abs(dot(N, V));
                float Fg = 0.04 + 0.96 * pow(1.0 - NdotV, 5.0);
                float3 refl;
                if (inside)
                    refl = CabinCube(P, reflect(I, -N)) * (cabinOn * _CabinReflGain);
                else
                    refl = LanbaiReflCube(reflect(I, N), 0.3) + LanbaiLampSpecular(P, N, V, 0.97, 0.04) / max(Fg, 0.04);
                float3 frontRGB = refl * Fg;

                // ---- dirt (on the glass, lit by ambient + a little cabin light)
                half4 dirt = tex2D(_DirtTex, i.uv);
                float3 dirtLit = _DirtColor.rgb * dirt.rgb * (ShadeSH9(half4(N, 1)) + cabinOn * 0.15);

                // ---- rain (outer face)
                float rain = _RainOverride >= 0.0 ? _RainOverride : _Udon_RainAmount;
                float2 pPane = float2(dot(P - i.pivot, T), dot(P - i.pivot, Bt));
                float2 buv = pPane / _BeadTile;
                float2 dBx = ddx(buv), dBy = ddy(buv);            // outside the branch
                float fp = max(length(ddx(pPane)), length(ddy(pPane)));
                float3 waterRGB = 0;                               // premultiplied, over what lies behind
                float waterA = 0;
                [branch] if (rain > 0.001)
                {
                    // two flow frames cross-faded by LanbaiRainState (trails never swing about the pivot)
                    float2 flA = PaneFlow(_Udon_FlowDir, N, T, Bt);
                    float2 flB = PaneFlow(_Udon_FlowDirB, N, T, Bt);
                    float fmix = saturate(_Udon_FlowMix);
                    float lenA = length(flA), lenB = length(flB);
                    float2 flowA = lenA > 1e-4 ? flA / lenA : float2(0, -1);
                    float2 flowB = lenB > 1e-4 ? flB / lenB : flowA;
                    float slopeOk = saturate(lerp(lenA, lenB, fmix) * 3.0);             // horizontal skylight: no runners
                    float drag = saturate(lerp(_Udon_FlowDir.w, _Udon_FlowDirB.w, fmix));
                    LanbaiRunParams rp;
                    // distance clock: still x t + (drive - still) x integral(drag dt): speed changes never jump heads
                    rp.distA = _RunSpeedStill * t + (_RunSpeedDrive - _RunSpeedStill) * _Udon_RunClock.x;
                    rp.vAvgA = max(lerp(_RunSpeedStill, _RunSpeedDrive, saturate(_Udon_RunClock.y)), 0.005);
                    rp.density = lerp(_RunDensityStill, _RunDensityDrive, drag) * slopeOk * saturate((_DetailFade - fp) / (0.5 * _DetailFade));
                    rp.size = _RunSize;
                    rp.stretch = _Udon_RunStretch + 0.8 * drag;
                    rp.stickslip = _StickSlip * (1.0 - 0.6 * drag);                    // wind-driven runs are steadier
                    rp.trailLife = _TrailLife;

                    LanbaiWipe wp = (LanbaiWipe)0;
                    wp.since = 1e4;
                    if (_Wipers > 0.5) wp = LanbaiWipers(P, T, Bt, t);

                    LanbaiGlassWater W = LanbaiGlassRain(pPane, dBx, dBy, flowA, flowB, fmix, rain, _BeadTile, rp,
                                                         P, T, Bt, wp.since, _WipeRefill);
                    W.slope += wp.slope * rain;                                          // the water line at the blade
                    W.thick += wp.h * rain;
                    W.cover = saturate(W.cover + step(1e-6, wp.h) * rain);
                    if (W.cover > 0.002)
                    {
                        float3 nT = normalize(float3(-W.slope, 1.0));
                        float3 Nd = normalize(T * nT.x + Bt * nT.y + N * nT.z);
                        // thin film at the bead edges is nearly invisible; the lens body is what reads
                        float c = W.cover * _DropOpacity * saturate(W.thick / 0.00015 + 0.25);
                        if (inside)
                        {
                            float3 cabin = CabinCube(P, reflect(I, -Nd)) * cabinOn;
                            waterRGB = LanbaiDropRadiance(P, I, N, Nd, cabin, _GlintLobe) * c;
                            waterA = c;
                        }
                        else
                        {
                            float3 tIn = refract(refract(I, Nd, 1.0 / 1.333), N, 1.333);   // into the cabin / case
                            if (dot(tIn, tIn) < 1e-4) tIn = I;
                            float3 behind = CabinCube(P, normalize(tIn)) * (cabinOn * _CabinReflGain)
                                          + _BehindColour.rgb * lerp(1.0, saturate(_Udon_CaseLight), _BehindLight);
                            float4 d = LanbaiDropOutside(P, I, N, Nd, behind * 0.35, _GlintLobe);
                            waterRGB = d.rgb * c;
                            waterA = d.a * c;
                            // where water covers the pane, the bare glass's own reflection is replaced by the drop's
                            frontRGB *= 1.0 - c;
                        }
                    }
                }

                // ---- composite, premultiplied
                float3 rgb; float alpha;
                if (inside)
                {
                    // back to front: drops (outer face) -> dirt -> the inner surface's cabin reflection on top
                    rgb = waterRGB; alpha = waterA;
                    rgb = dirtLit * dirt.a + rgb * (1.0 - dirt.a); alpha = dirt.a + alpha * (1.0 - dirt.a);
                    rgb = frontRGB + rgb * (1.0 - _BaseAlpha);    alpha = _BaseAlpha + alpha * (1.0 - _BaseAlpha);
                }
                else
                {
                    // back to front: dirt -> the outer surface (bare-glass reflection, or the water on it)
                    rgb = dirtLit * dirt.a; alpha = dirt.a;
                    rgb = frontRGB + rgb * (1.0 - _BaseAlpha);    alpha = _BaseAlpha + alpha * (1.0 - _BaseAlpha);
                    rgb = waterRGB + rgb * (1.0 - waterA);        alpha = waterA + alpha * (1.0 - waterA);
                }
                fixed4 col = fixed4(rgb, alpha);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, col, fixed4(unity_FogColor.rgb * col.a, col.a));
                return col;
            }
            ENDCG
        }
    }
    FallBack Off
}
