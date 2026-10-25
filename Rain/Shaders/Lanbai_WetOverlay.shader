// =====================================================================================================
//  Lanbai / WetOverlay        蓝白 · the wet spot on the door step under the skylight drip (bible §4.6 天窗)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  A 0.12 x 0.12 m quad laid 1 mm above the step (normal up), UV 0..1. Premultiplied overlay: water on the
//  aluminium tread plate darkens it a little and adds gloss - the cabin tubes and the stop lamp reflected in a
//  film and in beads. _Wet (0..1) is raised by Runtime/LanbaiDrips.cs at every drip and dries slowly.
//  Texture StepWet_Decal_256: R film, G bead height / 1 mm, B edge ring, A mask.
//  v2: stereo eye index in the fragment (M8), premultiplied fog.
// =====================================================================================================
Shader "Lanbai/WetOverlay"
{
    Properties
    {
        _MainTex ("StepWet_Decal_256 (linear)", 2D) = "black" {}
        _Wet ("Wetness 0..1 (Udon)", Range(0, 1)) = 0.6
        _Darken ("Darkening at full film", Range(0, 0.6)) = 0.18
        _Smoothness ("Water smoothness", Range(0.5, 1)) = 0.93
        _ReflGain ("Reflection gain", Range(0, 2)) = 1
        _SizeM ("Quad size (m)", Float) = 0.12
    }
    SubShader
    {
        Tags { "Queue" = "Transparent-10" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One OneMinusSrcAlpha
        ZWrite Off
        Offset -1, -1

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
            float4 _MainTex_TexelSize;
            float _Wet, _Darken, _Smoothness, _ReflGain, _SizeM;

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

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);   // SPS-I: _WorldSpaceCameraPos is per eye only after this
                float4 m = tex2D(_MainTex, i.uv);
                // the spot grows from the centre as _Wet rises, and shrinks back to the ring as it dries
                float r = length(i.uv - 0.5) * 2.0;
                float grow = smoothstep(_Wet * 1.25, _Wet * 1.25 - 0.25, r);
                float film = m.r * grow;
                float2 e = _MainTex_TexelSize.xy;
                float gx = tex2D(_MainTex, i.uv + float2(e.x, 0)).g - tex2D(_MainTex, i.uv - float2(e.x, 0)).g;
                float gy = tex2D(_MainTex, i.uv + float2(0, e.y)).g - tex2D(_MainTex, i.uv - float2(0, e.y)).g;
                float px = _SizeM / 256.0;                          // metres per texel
                float2 slope = float2(gx, gy) * 0.001 / (2.0 * px) * grow;
                float cover = saturate(max(film, m.g * 4.0 * grow) + m.b * grow * 0.5) * m.a;
                float3 N0 = normalize(i.wn), T = normalize(i.wt), Bt = normalize(i.wb);
                float3 N = normalize(N0 - T * slope.x - Bt * slope.y);
                float s = LanbaiSpecAA(N, _Smoothness);            // ddx / ddy: before any early-out
                if (cover < 0.003) return 0;
                float3 P = i.wpos;
                float3 V = normalize(_WorldSpaceCameraPos - P);
                float F = 0.02 + 0.98 * pow(1.0 - saturate(dot(N, V)), 5.0);
                float3 spec = LanbaiLampSpecular(P, N, V, s, 0.02) + LanbaiReflCube(reflect(-V, N), (1.0 - s) * 6.0) * F * _ReflGain;
                float a = cover * _Darken;
                fixed4 c = fixed4(spec * cover, a);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, c, fixed4(unity_FogColor.rgb * c.a, c.a));   // premultiplied
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
