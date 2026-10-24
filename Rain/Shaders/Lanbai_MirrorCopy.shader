// =====================================================================================================
//  Lanbai / MirrorCopy        蓝白 · what the still puddles mirror: the sign, its pole, the lamp housing and arm, the
//                                  notice case (lens_tech §2.6; bible §5.5 '水洼的回答', §6·12 '成双的「蓝白」站牌')
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  Duplicate the objects under ONE parent placed at the water level with localScale (1, -1, 1) (Unity flips the
//  culling of negatively scaled renderers by itself: keep Cull Back). Cast Shadows OFF, Receive Shadows OFF, Light
//  Probes OFF, Contribute GI OFF, layer = a layer the reflection-probe bake ignores. Drawn only where
//  Lanbai/StencilWindow opened the puddle (stencil bit 128), after it (AlphaTest+20). Unlit: the copy shows what
//  the original LOOKS like - albedo x _Lit (the light the original receives: bible E x lamp colour, linear) +
//  emission - at FULL brightness; Lanbai/PuddleOverlay then keeps only the water's reflectance of it.
//  Do NOT copy the stop tube itself: its reflection is the analytic lamp in PuddleOverlay (else: two tubes).
//  Anything of the copy above the water plane is clipped (a footing or a buried pole end would poke out).
// =====================================================================================================
Shader "Lanbai/MirrorCopy"
{
    Properties
    {
        _MainTex ("Albedo (sRGB) - the original's texture", 2D) = "white" {}
        _Color ("Albedo tint (sRGB as picked)", Color) = (1, 1, 1, 1)
        _Lit ("Light on the original (linear: E x lamp colour; sign face 1.47 x #E4F1F3 = (1.14, 1.29, 1.32))", Vector) = (1.14, 1.29, 1.32, 0)
        _EmissionMap ("Emission (sRGB) - e.g. Notice_Credits_Emission", 2D) = "black" {}
        [HDR] _EmissionColor ("Emission colour", Color) = (0, 0, 0, 1)
        _EmissionByCaseLight ("Emission x _Udon_CaseLight (the lit credits at scene 12 +95 s)", Range(0, 1)) = 0
        _MirrorGain ("Overall gain of the copy (1)", Range(0, 3)) = 1
        _WaterY ("World height of the water plane at home (m); copies above it are clipped", Float) = 0
        _AnchorToStop ("The plane moves with R_Stop (1)", Range(0, 1)) = 1
    }
    SubShader
    {
        Tags { "Queue" = "AlphaTest+20" "RenderType" = "Opaque" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Stencil { Ref 128 ReadMask 128 Comp Equal }
        ZWrite On
        ZTest LEqual
        Cull Back

        Pass
        {
            Tags { "LightMode" = "Always" }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            #include "LanbaiRain.cginc"

            sampler2D _MainTex, _EmissionMap;
            float4 _MainTex_ST;
            half4 _Color, _EmissionColor;
            float4 _Lit;
            half _EmissionByCaseLight, _MirrorGain;
            float _WaterY, _AnchorToStop;

            struct appdata { float4 vertex : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 wpos : TEXCOORD1;
                UNITY_FOG_COORDS(2)                 // the mirrored point's distance = the reflected path: fog is right
                UNITY_VERTEX_OUTPUT_STEREO
            };
            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.wpos = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.wpos);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }
            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float waterY = _WaterY + _Udon_StopOffset.y * _AnchorToStop;
                clip(waterY + 0.002 - i.wpos.y);
                float3 alb = tex2D(_MainTex, i.uv).rgb * _Color.rgb;
                float3 em = tex2D(_EmissionMap, i.uv).rgb * _EmissionColor.rgb * lerp(1.0, saturate(_Udon_CaseLight), _EmissionByCaseLight);
                fixed4 c = fixed4((alb * _Lit.rgb + em) * _MirrorGain, 1);
                UNITY_APPLY_FOG(i.fogCoord, c);
                return c;
            }
            ENDCG
        }
    }
    FallBack Off
}
