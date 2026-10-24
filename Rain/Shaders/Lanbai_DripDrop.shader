// =====================================================================================================
//  Lanbai / DripDrop        蓝白 · the hanging drop at the skylight corner, the lamp-arm trough, the sign rim,
//                                the notice-case roof (bible §4.6 天窗, §5.4 滴水, §5.5)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  Put a Unity Quad (1 x 1, any rotation) as a child of the drip point, scale = 0.010 (the frame is 10 x 10 mm).
//  The vertex shader turns it to face the camera about the world Y axis and hangs it from the object origin
//  (the lip = the top centre of the frame). _Frame 0..15 is driven by Runtime/LanbaiDrips.cs:
//  0-11 growing (Young-Laplace, 1.5 mm lip, V_max 4.8e-8 m^3), 12-14 pinch-off, 15 recoil.
//  Shading: a water ball-lens - reflection on top, the world seen through it INVERTED below (the lamp appears
//  at the bottom of the drop), + the analytic lamps.
//  v2: stereo eye index in the fragment (M8), premultiplied fog.
// =====================================================================================================
Shader "Lanbai/DripDrop"
{
    Properties
    {
        _MainTex ("PendantDrop_Flip4x4_512 (linear)", 2D) = "black" {}
        _Frame ("Frame 0..15", Range(0, 15)) = 0
        _Size ("Frame size (m)", Float) = 0.010
        _Opacity ("Opacity", Range(0, 1)) = 0.95
        _GlintLobe ("Lamp glint lobe", Range(20, 2000)) = 200
        _Lens ("Ball-lens bend (inversion strength)", Range(0, 2)) = 1.2
        _NearFade ("Near-eye fade: x = 0 at (m), y = 1 at (m)", Vector) = (0.15, 0.35, 0, 0)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" "DisableBatching" = "True" }
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

            sampler2D _MainTex;
            float _Frame, _Size, _Opacity, _GlintLobe, _Lens;
            float4 _NearFade;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                float3 right : TEXCOORD2;
                float3 fwd : TEXCOORD3;
                float fade : TEXCOORD4;
                UNITY_FOG_COORDS(5)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 lip = mul(unity_ObjectToWorld, float4(0, 0, 0, 1)).xyz;
                float3 toCam = LanbaiCentreEyePos() - lip;                     // same sprite for both eyes
                float3 fwd = normalize(float3(toCam.x, 0.0, toCam.z) + float3(1e-5, 0, 0));   // horizontal, toward the eye
                float3 right = normalize(cross(float3(0, 1, 0), fwd));
                // quad corners -0.5..0.5 -> sprite with its top edge at the lip
                float3 wp = lip + right * (v.vertex.x * _Size) + float3(0, 1, 0) * ((v.vertex.y - 0.5) * _Size);
                o.pos = UnityWorldToClipPos(wp);
                o.uv = v.uv;
                o.wpos = wp;
                o.right = right;
                o.fwd = fwd;
                o.fade = LanbaiNearFade(wp, _NearFade.x, _NearFade.y);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // SPS-I: _WorldSpaceCameraPos is per eye only after this
                float f = clamp(floor(_Frame + 0.5), 0.0, 15.0);
                float col = fmod(f, 4.0);
                float row = floor(f / 4.0);
                float2 uv = (clamp(i.uv, 0.004, 0.996) + float2(col, 3.0 - row)) / 4.0;
                float4 t = tex2D(_MainTex, uv);
                float cov = t.a;
                if (cov < 0.004) return 0;
                float2 n2 = t.rg * 2.0 - 1.0;                    // true normal xy (+X right, +Y up, +Z toward the eye)
                float nz = sqrt(saturate(1.0 - dot(n2, n2)));
                float3 N = normalize(i.right * n2.x + float3(0, 1, 0) * n2.y + i.fwd * nz);
                float3 P = i.wpos;
                float3 V = normalize(_WorldSpaceCameraPos - P);
                float3 I = -V;
                float F = 0.02 + 0.98 * pow(1.0 - saturate(dot(N, V)), 5.0);
                float3 r = reflect(I, N);
                float3 lat = N - dot(N, V) * V;                  // outward from the lens axis
                float3 tdir = normalize(I - _Lens * lat);          // a ball lens bends rays across the axis: inverted
                float3 refl = LanbaiReflCube(r, 0.5) + LanbaiLampGlints(P, r, _GlintLobe * 2.0);
                float3 trans = LanbaiReflCube(tdir, 1.0) + LanbaiLampGlints(P, tdir, _GlintLobe);
                float3 rad = refl * F + trans * (1.0 - F);
                float a = cov * _Opacity * i.fade;
                fixed4 c = fixed4(rad * a, a);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(unity_FogColor.rgb * c.a, c.a));   // premultiplied
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
