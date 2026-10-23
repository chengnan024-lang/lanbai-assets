// =====================================================================================================
//  Lanbai/SeaWaterline   蓝白 · the waterline on the bus glass (bible §6 -> 7 入水: '一条水线在约 1 秒里沿车窗升上去';
//                        §7 -> 8 出海: '水沿车窗向上流走（0.8 秒，从下往上的水线）')
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Syntax-checked with Slang against a Unity stub only. !!!
//
//  Put this on a COPY of the window / windscreen / skylight glass meshes (same transform, rendered after the glass:
//  Queue Transparent+20). It draws the thin water film on the glass on the water side of the line, plus the bright
//  meniscus. It reads the sea plane's world y from _Udon_SeaLevel (the driver writes it) and does nothing when
//  _Active is 0 (the driver turns the renderer off outside F2h - 0.5 .. F2h + 2 and EXIT - 0.5 .. EXIT + 1.5).
//  The glass shader (Control's Lanbai/BusGlass) can instead include LanbaiSea.cginc and call LanbaiWaterline() itself.
// =====================================================================================================
Shader "Lanbai/SeaWaterline"
{
    Properties
    {
        _Active ("Active 0..1  driver", Range(0, 1)) = 0
        _WaterBelow ("Water side  1 below the line  entry  -1 above  exit", Float) = 1
        _WaterlineColor ("Meniscus colour linear  a film strength", Vector) = (0.55, 0.70, 0.80, 0.35)
        _FilmColor ("Film colour linear", Vector) = (0.020, 0.060, 0.110, 0)
        _LevelOffset ("Level offset m", Float) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Transparent+20" "RenderType" = "Transparent" "IgnoreProjector" = "True" "ForceNoShadowCasting" = "True" }
        Blend One OneMinusSrcAlpha
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
            #include "LanbaiSea.cginc"

            float _Active, _WaterBelow, _LevelOffset;
            float4 _FilmColor;

            struct appdata { float4 vertex : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos : SV_POSITION; float3 posWS : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.posWS = mul(unity_ObjectToWorld, v.vertex).xyz;
                o.pos = UnityWorldToClipPos(o.posWS);
                return o;
            }

            float4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                if (_Active <= 0.0) discard;
                float4 w = LanbaiWaterline(i.posWS, _Udon_SeaLevel + _LevelOffset, _WaterBelow, LanbaiSeaTime());
                float a = saturate(w.a) * _Active;
                // premultiplied: film darkens/tints what is behind, the meniscus adds light
                return float4(_FilmColor.rgb * a + w.rgb * _Active, a);
            }
            ENDCG
        }
    }
    FallBack Off
}
