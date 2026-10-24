// Minimal stand-ins for the Built-in RP includes, so slangc can parse and type-check the kit's CGPROGRAM blocks.
// NOT Unity: a syntax / type check only (README §7).
#ifndef UNITY_STUB
#define UNITY_STUB
#define UNITY_CG_INCLUDED
#define sampler2D Sampler2D
#define sampler2D_float Sampler2D
#define tex2D(s, uv) (s).Sample(uv)
#define tex2Dgrad(s, uv, dx, dy) (s).SampleGrad(uv, dx, dy)
#define tex2Dlod(s, uv4) (s).SampleLevel((uv4).xy, (uv4).w)
#define UNITY_VERTEX_INPUT_INSTANCE_ID uint instanceID : SV_InstanceID;
#define UNITY_VERTEX_OUTPUT_STEREO
#define UNITY_SETUP_INSTANCE_ID(v)
#define UNITY_TRANSFER_INSTANCE_ID(v, o)
#define UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o)
#define UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)
#define UNITY_INSTANCING_BUFFER_START(n)
#define UNITY_INSTANCING_BUFFER_END(n)
#define UNITY_DEFINE_INSTANCED_PROP(t, n) t n;
#define UNITY_ACCESS_INSTANCED_PROP(b, n) n
#define UNITY_PI 3.14159265
float3 _WorldSpaceCameraPos;
float4 _ScreenParams;
float4 _ProjectionParams;
float4 _ZBufferParams;
float4 _Time;
float4x4 unity_CameraProjection;
float4x4 unity_ObjectToWorld;
float4x4 unity_WorldToObject;
float4x4 unity_MatrixVP;
float4x4 unity_MatrixV;
#define UNITY_MATRIX_VP unity_MatrixVP
#define UNITY_MATRIX_V unity_MatrixV

float4 UnityWorldToClipPos(float3 p) { return mul(unity_MatrixVP, float4(p, 1.0)); }
float4 UnityObjectToClipPos(float3 p) { return mul(unity_MatrixVP, mul(unity_ObjectToWorld, float4(p, 1.0))); }
float4 UnityObjectToClipPos(float4 p) { return UnityObjectToClipPos(p.xyz); }
float4 ComputeScreenPos(float4 c) { float4 o = c * 0.5; o.xy = float2(o.x, o.y * _ProjectionParams.x) + o.w; o.zw = c.zw; return o; }
float LinearEyeDepth(float z) { return 1.0 / (_ZBufferParams.z * z + _ZBufferParams.w); }
#define SAMPLE_DEPTH_TEXTURE_PROJ(s, uv) (s).Sample((uv).xy / (uv).w).r
#define COMPUTE_EYEDEPTH(o) o = 1.0
float Luminance(float3 c) { return dot(c, float3(0.2126729, 0.7151522, 0.0721750)); }
#endif
#ifndef UNITY_STUB2
#define UNITY_STUB2
#define UNITY_DECLARE_DEPTH_TEXTURE(n) Sampler2D n
#define UNITY_PROJ_COORD(a) a
#endif
#ifndef UNITY_STUB3
#define UNITY_STUB3
#define fixed half
#define fixed2 half2
#define fixed3 half3
#define fixed4 half4
float4x4 unity_MatrixP;
#define UNITY_MATRIX_P unity_MatrixP
#define UNITY_INITIALIZE_OUTPUT(type, name) name = (type)0
half3 LinearToGammaSpace(half3 c) { return pow(max(c, 0.0), 1.0 / 2.2); }
half3 GammaToLinearSpace(half3 c) { return pow(max(c, 0.0), 2.2); }
float3 UnityObjectToViewPos(float3 p) { return mul(unity_MatrixV, mul(unity_ObjectToWorld, float4(p, 1.0))).xyz; }
float3 UnityObjectToViewPos(float4 p) { return UnityObjectToViewPos(p.xyz); }
float3 UnityObjectToWorldNormal(float3 n) { return normalize(mul(n, (float3x3)unity_WorldToObject)); }
float3 UnityWorldSpaceViewDir(float3 p) { return _WorldSpaceCameraPos - p; }
float4 _WorldSpaceLightPos0;
float4 _LightColor0;
#endif
