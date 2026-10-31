// =====================================================================================================================
//  Lanbai / Subtitle  v1        蓝白 · 诗句字幕（D-45，字体套件第 5 版，总工程师）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; Common/Tools~/compile_check only). Compile in Unity 2022.3 + VRChat
//      SDK 3.10.5 + TextMeshPro 3.0.x, and look at it in a headset with one eye, then the other (bible §1.8). !!!
//
//  A TextMeshPro (3D) distance-field shader for the subtitle lines (Art/字幕方案_D-45.md I.4, B.4, C.5–C.7):
//  - Queue Overlay+10, ZTest Always, ZWrite Off, Cull Off: drawn after every world object (rails, pillars, avatars,
//    hands cannot cut it), before the overlay sphere (Overlay+100), which still covers it. D-45 #10 allows ZTest Always.
//  - The SDF maths is TMP's (same property names, so TMP's padding / ScaleRatio code and the material inspector numbers
//    mean the same): scale from the screen-space size of a texel, bias from _FaceDilate; no outline, no glow, no bevel.
//  - Underlay (UNDERLAY_ON, offset 0): the always-on dark halo hugging the strokes (B.4 #3). Unlike TMP it is
//    multiplied by the line's alpha (_FaceColor.a), so a fading line takes its halo with it.
//  - _FaceColor comes per line from the driver's MaterialPropertyBlock: rgb = the solved linear fill x 2^(-dEV), a = the
//    line's alpha; the vertex colour is white (alpha 1).
//  - Not in mirrors, not in the hand-held / photo camera (_VRChatMirrorMode / _VRChatCameraMode != 0: discard, C.7).
//  - SPS-I: the LanbaiVR.cginc macros; the fragment reads no per-eye value (the scale is computed per eye in the
//    vertex shader from UNITY_MATRIX_P).
// =====================================================================================================================
Shader "Lanbai/Subtitle"
{
    Properties
    {
        _FaceColor ("Face colour (linear fill, alpha = line alpha)", Color) = (1, 1, 1, 1)
        _FaceDilate ("Face dilate", Range(-1, 1)) = 0.10
        _UnderlayColor ("Underlay colour", Color) = (0, 0, 0, 0.5)
        _UnderlayOffsetX ("Underlay offset x", Range(-1, 1)) = 0
        _UnderlayOffsetY ("Underlay offset y", Range(-1, 1)) = 0
        _UnderlayDilate ("Underlay dilate", Range(-1, 1)) = 0.15
        _UnderlaySoftness ("Underlay softness", Range(0, 1)) = 0.30
        _OutlineColor ("Outline colour (unused)", Color) = (0, 0, 0, 1)
        _OutlineWidth ("Outline width (unused)", Range(0, 1)) = 0
        _OutlineSoftness ("Outline softness", Range(0, 1)) = 0
        _WeightNormal ("Weight normal", Float) = 0
        _WeightBold ("Weight bold", Float) = 0.5
        _ShaderFlags ("Flags", Float) = 0
        _ScaleRatioA ("Scale ratio A", Float) = 1
        _ScaleRatioB ("Scale ratio B", Float) = 1
        _ScaleRatioC ("Scale ratio C", Float) = 1
        _MainTex ("Font atlas", 2D) = "white" {}
        _TextureWidth ("Texture width", Float) = 2048
        _TextureHeight ("Texture height", Float) = 2048
        _GradientScale ("Gradient scale", Float) = 11
        _ScaleX ("Scale x", Float) = 1
        _ScaleY ("Scale y", Float) = 1
        _PerspectiveFilter ("Perspective correction", Range(0, 1)) = 0.875
        _Sharpness ("Sharpness", Range(-1, 1)) = -0.1
        _VertexOffsetX ("Vertex offset x", Float) = 0
        _VertexOffsetY ("Vertex offset y", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Overlay+10" "IgnoreProjector" = "True" "RenderType" = "Transparent" "ForceNoShadowCasting" = "True" }
        Cull Off
        ZWrite Off
        ZTest Always
        Lighting Off
        Fog { Mode Off }
        Blend One OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #pragma shader_feature_local __ UNDERLAY_ON
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            sampler2D _MainTex;
            float4 _FaceColor;
            float _FaceDilate;
            float4 _UnderlayColor;
            float _UnderlayOffsetX, _UnderlayOffsetY, _UnderlayDilate, _UnderlaySoftness;
            float _OutlineWidth, _OutlineSoftness;
            float _WeightNormal, _WeightBold;
            float _ScaleRatioA, _ScaleRatioC;
            float _TextureWidth, _TextureHeight, _GradientScale;
            float _ScaleX, _ScaleY, _PerspectiveFilter, _Sharpness;
            float _VertexOffsetX, _VertexOffsetY;
            float _VRChatMirrorMode;
            float _VRChatCameraMode;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                fixed4 color : COLOR;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;                  // TMP 3.0: y = the glyph's scale (negative = bold)
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 pos : SV_POSITION;
                float4 col : COLOR;
                float2 uv : TEXCOORD0;
                float4 param : TEXCOORD1;                 // x unused, y scale, z bias, w weight
                float4 under : TEXCOORD2;                 // xy underlay uv, z underlay scale, w underlay bias
                UNITY_VERTEX_OUTPUT_STEREO
            };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float4 p = v.vertex;
                p.x += _VertexOffsetX;
                p.y += _VertexOffsetY;
                o.pos = UnityObjectToClipPos(p);
                // screen-space size of one texel -> the distance-field scale (as TMP: sharp at any depth / screen size)
                float2 pixelSize = o.pos.w;
                pixelSize /= float2(_ScaleX, _ScaleY) * abs(mul((float2x2)UNITY_MATRIX_P, _ScreenParams.xy));
                float scale = rsqrt(dot(pixelSize, pixelSize));
                scale *= abs(v.uv1.y) * _GradientScale * (_Sharpness + 1);
                if (UNITY_MATRIX_P[3][3] == 0)
                    scale = lerp(abs(scale) * (1 - _PerspectiveFilter), scale,
                                 abs(dot(UnityObjectToWorldNormal(v.normal), normalize(WorldSpaceViewDir(p)))));
                float bold = step(v.uv1.y, 0);
                float weight = lerp(_WeightNormal, _WeightBold, bold) / 4.0;
                weight = (weight + _FaceDilate) * _ScaleRatioA * 0.5;
                float bias = (0.5 - weight) + (0.5 / scale);
                o.param = float4(0, scale, bias, weight);
                o.uv = v.uv0;
                o.col = v.color;
                float bScale = scale / (1 + (_UnderlaySoftness * _ScaleRatioC) * scale);
                float bBias = (0.5 - weight) * bScale - 0.5 - ((_UnderlayDilate * _ScaleRatioC) * 0.5 * bScale);
                float2 bOff = float2(-(_UnderlayOffsetX * _ScaleRatioC) * _GradientScale / _TextureWidth,
                                     -(_UnderlayOffsetY * _ScaleRatioC) * _GradientScale / _TextureHeight);
                o.under = float4(v.uv0 + bOff, bScale, bBias);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_VRChatMirrorMode != 0 || _VRChatCameraMode != 0) discard;
                float lineA = _FaceColor.a * i.col.a;
                float c = tex2D(_MainTex, i.uv).a;
                float scale = i.param.y;
                float sd = (i.param.z - c) * scale;
                float softness = (_OutlineSoftness * _ScaleRatioA) * scale;
                float coverage = 1 - saturate((sd + softness * 0.5) / (1.0 + softness));
                float4 col = float4(_FaceColor.rgb * i.col.rgb * lineA, lineA) * coverage;    // premultiplied
            #if UNDERLAY_ON
                float d = tex2D(_MainTex, i.under.xy).a * i.under.z;
                float ua = saturate(d - i.under.w) * _UnderlayColor.a * lineA;
                col += float4(_UnderlayColor.rgb * ua, ua) * (1 - col.a);
            #endif
                return col;
            }
            ENDCG
        }
    }
}
