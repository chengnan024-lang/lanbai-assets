Shader "Hidden/Lanbai/DiagnosticObjectId" {
 Properties { _Color ("ID",Color)=(1,1,1,1) }
 SubShader { Tags {"RenderType"="Opaque" "Queue"="Geometry"} Pass {
  Cull Back ZWrite On ZTest LEqual Blend Off
  CGPROGRAM
  #pragma vertex vert
  #pragma fragment frag
  #include "UnityCG.cginc"
  float4 _Color;
  float4 vert(float4 p:POSITION):SV_POSITION{return UnityObjectToClipPos(p);}
  float4 frag():SV_Target{return _Color;}
  ENDCG
 } }
}
