Shader "Hidden/Lanbai/SamplingTimeDiagnostic" {
 Properties { _Mode ("Mode",Float)=0 _Period ("Period",Float)=4 }
 SubShader { Pass { Cull Off ZWrite Off ZTest Always Blend Off
 CGPROGRAM
 #pragma vertex vert_img
 #pragma fragment frag
 #pragma target 3.0
 #include "UnityCG.cginc"
 float _Mode,_Period;
 float4 frag(v2f_img i):SV_Target {
   if(_Mode<0.5)return float4(_Time.y,_SinTime.w,_CosTime.w,unity_DeltaTime.x);
   float2 p=floor(i.pos.xy);
   float k=(fmod(p.x,_Period)<0.5&&fmod(p.y,_Period)<0.5)?1:0;
   return float4(k,k,k,1);
 }
 ENDCG
 } }
}
