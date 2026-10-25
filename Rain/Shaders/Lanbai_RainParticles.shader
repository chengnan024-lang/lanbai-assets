// =====================================================================================================
//  Lanbai / RainParticles     蓝白 · rain streaks, splashes, falling drips: lit only where a lamp lights them
//                                 (bible §6·1 大气, §5.4 滴水)
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Type-checked with Slang against a Unity stub only.
//      Compile in Unity 2022.3; check in a headset (one eye closed, then the other). !!!
//
//  One shader, three materials (README_Rain.md §3):
//    M_RainStreak  RainStreak_Atlas8x1_512, Stretched Billboard, TSA Grid 8 x 1, Start Frame random 0..7,
//                  Frame over Time constant 0 (each streak keeps its variant).   _Gain 0.0152, _Tint #DCE7F3
//    M_RainSplash  RainSplash_Flip4x4_512, Vertical Billboard, pivot (0, 0.375, 0), TSA Grid 4 x 4,
//                  Frame over Time linear 0 -> 16 over the 0.12 s life.                         _Gain 0.03
//    M_DripFall    RainStreak_Atlas8x1_512 cell 6 ('bright head'), Stretched Billboard, one particle per drip.
//                                                                                              _Gain 0.02
//  Colour = white (the lamps colour it, x _Tint: water scatters a little bluer than the tube; a lamp-lit streak near the
//  stop tube then reads the bible's #9AA8B4 under S1). Additive: rain adds light; it never darkens the night.
//  v2: _Tint, a stretch-axis swap toggle (_SwapUV), _AmbientColor entered as picked (sRGB #9AA4AA).
//  Brightness = sum over the 8 analytic lamps of E x phase(scattering angle) x _Gain  +  a faint ambient fill.
//  Forward scattering: rain between you and the lamp glows, rain beside it is faint (Garg & Nayar).
// =====================================================================================================
Shader "Lanbai/RainParticles"
{
    Properties
    {
        _MainTex ("Atlas: RainStreak_Atlas8x1_512 / RainSplash_Flip4x4_512 (linear, sRGB OFF)", 2D) = "black" {}
        _Gain ("Lamp gain (streaks 0.0152: backlit streak near the stop tube reads #9AA8B4 with the tint)", Float) = 0.0152
        _Tint ("Scatter tint (sRGB as picked; streaks #DCE7F3, splash / drip white)", Color) = (0.863, 0.906, 0.953, 1)
        _AmbientColor ("Unlit rain colour (sRGB as picked: #9AA4AA)", Color) = (0.604, 0.643, 0.667, 1)
        _Ambient ("Unlit rain strength (bible alpha 0.06)", Range(0, 0.3)) = 0.06
        _NearFade ("Near-eye fade: x = 0 at (m), y = 1 at (m)", Vector) = (0.3, 1.2, 0, 0)
        _InvFade ("Soft particles (1 / m)", Float) = 4
        [Toggle] _FlipV ("Flip V inside an 8x1 strip (streaks only: use if the bright head trails)", Float) = 0
        [Toggle] _SwapUV ("Swap U and V inside a cell (streaks only: use if the streak lies ACROSS its motion)", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" "IgnoreProjector" = "True" "PreviewType" = "Plane" }
        Blend One One
        ZWrite Off
        Cull Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.5
            #pragma multi_compile _ SOFTPARTICLES_ON
            #pragma multi_compile_fog
            #include "UnityCG.cginc"
            #include "LanbaiLamps.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            sampler2D _MainTex;
            float4 _MainTex_ST;
            float _Gain, _Ambient, _InvFade, _FlipV, _SwapUV;
            half4 _AmbientColor, _Tint;
            float4 _NearFade;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            struct appdata
            {
                float4 vertex : POSITION;
                half4 color : COLOR;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                half4 col : COLOR;
                float2 uv : TEXCOORD0;
                float4 proj : TEXCOORD1;
                UNITY_FOG_COORDS(2)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(wp);
                float3 toEye = normalize(_WorldSpaceCameraPos - wp);
                float3 light = LanbaiRainLight(wp, toEye) * (_Gain * _Tint.rgb) + _AmbientColor.rgb * _Ambient;
                float fade = LanbaiNearFade(wp, _NearFade.x, _NearFade.y);
                o.col = half4(light * v.color.rgb * v.color.a * fade, 1);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.proj = ComputeScreenPos(o.pos);
                COMPUTE_EYEDEPTH(o.proj.z);
                UNITY_TRANSFER_FOG(o, o.pos);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float2 uv = i.uv;
                if (_FlipV > 0.5 || _SwapUV > 0.5)
                {
                    // inside one cell of the 8 x 1 strip (per fragment: a vertex sits ON the cell edge and cannot tell)
                    float cell = floor(uv.x * 8.0);
                    float fu = uv.x * 8.0 - cell;
                    float2 c = _SwapUV > 0.5 ? float2(uv.y, fu) : float2(fu, uv.y);
                    if (_FlipV > 0.5) c.y = 1.0 - c.y;
                    uv = float2((cell + clamp(c.x, 0.002, 0.998)) / 8.0, c.y);
                }
                half4 tex = tex2D(_MainTex, uv);
                half lum = tex.r * tex.a;
                #if defined(SOFTPARTICLES_ON)
                    float sceneZ = LinearEyeDepth(SAMPLE_DEPTH_TEXTURE_PROJ(_CameraDepthTexture, UNITY_PROJ_COORD(i.proj)));
                    lum *= saturate(_InvFade * (sceneZ - i.proj.z));
                #endif
                fixed4 col = fixed4(i.col.rgb * lum, 0);
                UNITY_APPLY_FOG_COLOR(i.fogCoord, col, fixed4(0, 0, 0, 0));
                return col;
            }
            ENDCG
        }
    }
    FallBack Off
}
