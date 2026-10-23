// =====================================================================================================
//  Lanbai/SeaCausticsCookie   蓝白 · the moving caustic cookie of the underwater sun (bible §6·7a 光: '平行光自上 +
//                             动态焦散 cookie（1.5 m 平铺）')
//
//  !!! WRITTEN WITHOUT A UNITY COMPILER (cloud side). Checked with DXC + Unity 2022.3 CGIncludes (Common/Tools~/compile_check), never in Unity. !!!
//
//  A Custom Render Texture shader. Setup (the Act07 builder does it):
//    CustomRenderTexture 256 x 256, format ARGBHalf (or Alpha8): the built-in pipeline reads a directional cookie's
//    ALPHA, so the format must HAVE alpha -- an R8 / RHalf CRT reads alpha = 1 everywhere (= no cookie). The shader
//    writes the cookie into all four channels. Wrap Repeat, Update Mode Realtime, Update Period 0, Material = this.
//    Assign the CRT as the cookie of the 7a sun (directional light, Cookie Size 1.5 m).
//  The cookie tile is 1.5 m, so the two layers tile at 0.75 m and 1.5 m (integer divisions: no seam); the pattern is
//  the same atlas and clock as LanbaiCaustics.cginc. Values stay in 0.25..1 (a cookie can only take light away).
//  FALLBACK (if a CRT cannot be a light cookie in your Unity / VRChat build): Sea/Textures/CausticsCookie_Static_256.png,
//  the same pattern frozen (frame 0, same floor and gain), already imported as a Cookie with alpha from the grey
//  (LanbaiSeaImport). Switch: drag it into the 7a sun's Cookie slot instead of the CRT (README_Sea §6). The light still
//  moves across it with the bus, only the shimmer stops.
// =====================================================================================================
Shader "Lanbai/SeaCausticsCookie"
{
    Properties
    {
        _Floor ("Cookie floor", Range(0, 1)) = 0.25
        _Gain ("Cookie gain on mean-1 caustics", Range(0, 1)) = 0.3
    }
    SubShader
    {
        Lighting Off
        Blend One Zero
        Pass
        {
            Name "Cookie"
            CGPROGRAM
            #include "UnityCustomRenderTexture.cginc"
            #pragma vertex CustomRenderTextureVertexShader
            #pragma fragment frag
            #pragma target 3.5
            #include "Assets/Lanbai/Common/Shaders/LanbaiCaustics.cginc"

            float _Floor, _Gain;

            float4 frag(v2f_customrendertexture IN) : SV_Target
            {
                float2 uv = IN.localTexcoord.xy;
                float clock = _Udon_Caustics.z;
                float ph = frac(clock * LANBAI_CAUSTICS_HZ);
                float A = LanbaiCausticsLayer(uv * 2.0, ph);
                float B = LanbaiCausticsLayer(uv + float2(0.31, 0.57), frac(ph + 0.37));
                float I = min(A, B) * LANBAI_CAUSTICS_MIN_NORM;
                float c = saturate(_Floor + _Gain * I);
                return float4(c, c, c, c);
            }
            ENDCG
        }
    }
}
