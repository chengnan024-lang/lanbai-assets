// =====================================================================================================
//  Lanbai / OneDrop        蓝白 · "那一滴雨" (bible §3.3, §4.6, §6·12): the clock of the whole dream
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  A 12 x 96 mm quad on the OUTER face of the hero window (0.3 mm off the glass), normal pointing OUT of the bus,
//  UV (0,0) bottom-left .. (1,1) top-right, v up = up. The path starts 8 mm below the top edge, pauses at
//  20 mm (scene 1: 1 cm/s after the player sits), and ends on the rubber seal 88 mm below the top
//  (scene 12: the last 60 mm in 8 s). Driven by Runtime/LanbaiOneDrop.cs (LOCAL, one per player):
//    _Progress 0..1 along the 80 mm path   _Slide 0..1 head shape (0 at rest, 1 sliding)
//    _Merge 0..1 (drop sinks into the seal) _Visible 0..1
//  Textures: OneDrop_Head_Flip4x4_512 (12 x 12 mm frames, anchor (0.5, 0.40)), OneDrop_Trail_128x1024.
//  v2: stereo eye index (M8), two-interface optics (M2), fog.
// =====================================================================================================
Shader "Lanbai/OneDrop"
{
    Properties
    {
        _Head ("OneDrop_Head_Flip4x4_512 (linear)", 2D) = "black" {}
        _Trail ("OneDrop_Trail_128x1024 (linear)", 2D) = "black" {}
        _Progress ("Progress along the 80 mm path", Range(0, 1)) = 0
        _Slide ("Head shape: 0 rest .. 1 sliding", Range(0, 1)) = 0
        _Merge ("Merge into the seal", Range(0, 1)) = 0
        _Visible ("Visible", Range(0, 1)) = 1
        _DropOpacity ("Drop opacity", Range(0, 1)) = 0.95
        _TrailOpacity ("Trail film opacity", Range(0, 1)) = 0.35
        _GlintLobe ("Lamp glint lobe", Range(20, 2000)) = 350
        _CabinColour ("Cabin colour seen at the rim (x _Udon_CabinLightmap)", Color) = (0.30, 0.30, 0.28, 1)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent+1" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One OneMinusSrcAlpha
        ZWrite Off
        Cull Off

        Pass
        {
            Tags { "LightMode" = "ForwardBase" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            #include "LanbaiRain.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            sampler2D _Head, _Trail;
            float _Progress, _Slide, _Merge, _Visible, _DropOpacity, _TrailOpacity, _GlintLobe;
            half4 _CabinColour;

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
                UNITY_FOG_COORDS(5)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.wn = UnityObjectToWorldNormal(v.normal);
                o.wt = UnityObjectToWorldDir(v.tangent.xyz);
                o.wb = cross(o.wn, o.wt) * (v.tangent.w * unity_WorldTransformParams.w);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            // one frame of the head atlas; hu = frame uv (0..1, v up); returns (nx, ny, thick, cover)
            float4 HeadFrame(float2 hu, float f)
            {
                float inb = step(0.0, hu.x) * step(hu.x, 1.0) * step(0.0, hu.y) * step(hu.y, 1.0);
                float col = fmod(f, 4.0);
                float row = floor(f / 4.0);
                float2 uv = (clamp(hu, 0.004, 0.996) + float2(col, 3.0 - row)) / 4.0;
                return tex2Dlod(_Head, float4(uv, 0, 0)) * inb;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // SPS-I: _WorldSpaceCameraPos is per eye only after this
                if (_Visible <= 0.001) return 0;
                float3 P = i.wpos;
                float3 N = normalize(i.wn);
                float3 T = normalize(i.wt);
                float3 Bt = normalize(i.wb);
                float3 V = normalize(_WorldSpaceCameraPos - P);
                float3 I = -V;
                bool inside = dot(V, N) < 0.0;

                // decal space in mm: x right, y DOWN from the top edge
                float2 pmm = float2((i.uv.x - 0.5) * 12.0, (1.0 - i.uv.y) * 96.0);
                float s = _Progress * 80.0;
                float yHead = 8.0 + s;
                float cl = (tex2Dlod(_Trail, float4(0.5, 1.0 - yHead / 96.0, 0, 0)).r - 0.5) * 8.0;   // path x (mm)
                float2 d = pmm - float2(cl, yHead);
                float shrink = 1.0 - 0.75 * _Merge;
                float2 hu = float2(0.5 + d.x / (12.0 * shrink), 0.40 - d.y / (12.0 * shrink));
                float f = _Slide * 15.0;
                float f0 = floor(f);
                float f1 = min(f0 + 1.0, 15.0);
                float4 h = lerp(HeadFrame(hu, f0), HeadFrame(hu, f1), frac(f));
                float hc = h.a * (1.0 - _Merge * _Merge);
                float2 hn = h.rg * 2.0 - 1.0;                             // atlas stores the true normal (xy)

                // trail: only where the head has already been
                float4 tr = tex2Dlod(_Trail, float4(i.uv, 0, 0));          // the trail has no mips (README §1): explicit LOD after the early-out
                float passed = step(7.6, pmm.y) * smoothstep(yHead - 0.5, yHead - 2.5, pmm.y);
                const float du = 1.0 / 128.0, dv = 1.0 / 1024.0;
                float gxp = tex2Dlod(_Trail, float4(i.uv + float2(du, 0), 0, 0)).g, gxm = tex2Dlod(_Trail, float4(i.uv - float2(du, 0), 0, 0)).g;
                float gyp = tex2Dlod(_Trail, float4(i.uv + float2(0, dv), 0, 0)).g, gym = tex2Dlod(_Trail, float4(i.uv - float2(0, dv), 0, 0)).g;
                float2 pslope = float2(gxp - gxm, gyp - gym) * 0.25 / (2.0 * float2(12.0 / 128.0, 96.0 / 1024.0));
                float pc = saturate(tr.g * 6.0) * passed;
                float film = tr.b * passed * _TrailOpacity;

                // combine: head over pearls over film
                float2 slope = lerp(pslope * pc, -hn / max(sqrt(saturate(1.0 - dot(hn, hn))), 0.25), saturate(hc * 1.5));
                float cover = max(hc, max(pc, film));
                if (cover < 0.002) return 0;
                float3 nT = normalize(float3(-slope, 1.0));
                float3 Nd = normalize(T * nT.x + Bt * nT.y + N * nT.z);
                float3 cabin = _CabinColour.rgb * saturate(_Udon_CabinLightmap);
                float a = cover * _DropOpacity * _Visible;
                fixed4 c;
                if (inside)
                    c = fixed4(LanbaiDropRadiance(P, I, N, Nd, cabin, _GlintLobe) * a, a);   // flat pane, then the drop
                else
                {
                    float4 d = LanbaiDropOutside(P, I, N, Nd, cabin * 0.35, _GlintLobe);      // seen from the stop
                    c = fixed4(d.rgb * a, d.a * a);
                }
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(unity_FogColor.rgb * c.a, c.a));
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
