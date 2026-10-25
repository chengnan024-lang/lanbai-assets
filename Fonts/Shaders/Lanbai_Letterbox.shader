// =====================================================================================================================
//  Lanbai / Letterbox  v1       蓝白 · 桌面的遮幅黑边（D-45 #15.3，字体套件第 5 版，总工程师）
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side; Common/Tools~/compile_check only). Compile in Unity 2022.3 + VRChat
//      SDK 3.10.5. DESKTOP ONLY: the driver never turns it on in VR (bible §1.8: nothing head-locked in VR). !!!
//
//  One Quad in front of the screen camera at 0.9 m, scaled to cover the view (LanbaiPoemDriver.Letterbox). The shader
//  draws two black bars that crop the view to _Cut.x (2.39:1), with the bars' inner corners cut at _Cut.y = tan(45°),
//  _Cut.w of the bar's height deep (0.5 until Fins is measured: a bar of height h loses a triangle 0.5h x 0.5h / tan).
//  _Slide 0..1 slides the bars in from the screen edges (0 = none, 1 = full height). _ScreenAspect = width / height.
//  All three are set per frame by the driver's MaterialPropertyBlock; the numbers are data (subtitle_rig.letterbox).
//  Queue Overlay+5: after the world, under the subtitles (Overlay+9 / +10) and the overlay sphere (Overlay+100).
//  ZTest Always: the bars must also cover anything nearer than 0.9 m (listed with the subtitles in compile_check;
//  the bible's sentence on ZTest Always needs the letterbox added, see Engineering/给总导演.md). Not in mirrors / the
//  photo camera.
// =====================================================================================================================
Shader "Lanbai/Letterbox"
{
    Properties
    {
        _Slide ("Slide (0 none, 1 full)", Range(0, 1)) = 0
        _ScreenAspect ("Screen aspect (w / h)", Float) = 1.7778
        _Cut ("Target aspect, tan corner, overscan, corner depth (fraction of the bar)", Vector) = (2.39, 1, 1.02, 0.5)
    }
    SubShader
    {
        Tags { "Queue" = "Overlay+5" "IgnoreProjector" = "True" "RenderType" = "Transparent" "ForceNoShadowCasting" = "True" "PreviewType" = "Plane" }
        Cull Off
        ZWrite Off
        ZTest Always
        Lighting Off
        Blend SrcAlpha OneMinusSrcAlpha

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 3.0
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            #include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"

            float _Slide;
            float _ScreenAspect;
            float4 _Cut;
            float _VRChatMirrorMode;
            float _VRChatCameraMode;

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
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_VRChatMirrorMode != 0 || _VRChatCameraMode != 0) discard;
                // bar height as a fraction of the view height: (1 - screenAspect / targetAspect) / 2 (none if the screen
                // is already wider than the target)
                // the quad is _Cut.z (overscan) times the view: measure in view units, centred on the quad
                float os = max(_Cut.z, 1.0);
                float bar = saturate(0.5 * (1.0 - _ScreenAspect / max(_Cut.x, 0.01))) * _Slide;
                float2 v = (i.uv - 0.5) * os + 0.5;                         // view coordinates (0..1 across the view)
                float y = min(v.y, 1.0 - v.y);                            // distance from the nearer top / bottom edge
                float xs = min(v.x, 1.0 - v.x) * _ScreenAspect;           // distance from the nearer side, in view heights
                float tanC = max(_Cut.y, 0.01);
                float cut = max(0.0, saturate(_Cut.w) * bar - xs * tanC); // the 45° corner cut, _Cut.w of the bar deep (D-45 #15 r2: small)
                float h = bar - cut;
                float aa = fwidth(y) + 1e-5;
                float a = 1.0 - smoothstep(h - aa, h + aa, y);
                return float4(0, 0, 0, a);
            }
            ENDCG
        }
    }
}
