// Minimal stand-in for UnityCG / HLSLSupport / surface-shader glue, so Slang can PARSE and TYPE-CHECK the kit's
// CG blocks. Signatures follow Unity 2022.3 Built-in. Passing here proves the HLSL is well-formed and well-typed;
// it does NOT prove that Unity's FXC / surface-shader generator accepts it. That check is the implementer's.
#define half float
#define half2 float2
#define half3 float3
#define half4 float4
#define fixed float
#define fixed2 float2
#define fixed3 float3
#define fixed4 float4
#define UNITY_PI 3.14159265359
struct sampler2D { Texture2D<float4> t; SamplerState s; };
struct samplerCUBE { TextureCube<float4> t; SamplerState s; };
float4 tex2D(sampler2D s, float2 uv) { return s.t.Sample(s.s, uv); }
float4 tex2Dlod(sampler2D s, float4 uv) { return s.t.SampleLevel(s.s, uv.xy, uv.w); }
float4 tex2Dgrad(sampler2D s, float2 uv, float2 dx, float2 dy) { return s.t.SampleGrad(s.s, uv, dx, dy); }
float4 texCUBE(samplerCUBE s, float3 d) { return s.t.Sample(s.s, d); }
float4 texCUBElod(samplerCUBE s, float4 d) { return s.t.SampleLevel(s.s, d.xyz, d.w); }
#define UNITY_DECLARE_TEX2DARRAY(tex) Texture2DArray<float4> tex; SamplerState sampler##tex
#define UNITY_SAMPLE_TEX2DARRAY(tex, coord) tex.Sample(sampler##tex, coord)
#define UNITY_SAMPLE_TEX2DARRAY_LOD(tex, coord, lod) tex.SampleLevel(sampler##tex, coord, lod)
#define UNITY_DECLARE_TEXCUBE(tex) TextureCube<float4> tex; SamplerState sampler##tex
#define UNITY_SAMPLE_TEXCUBE_LOD(tex, coord, lod) tex.SampleLevel(sampler##tex, coord, lod)
#define UNITY_DECLARE_DEPTH_TEXTURE(tex) Texture2D<float4> tex; SamplerState sampler##tex
#define SAMPLE_DEPTH_TEXTURE_PROJ(tex, uv) (tex.Sample(sampler##tex, (uv).xy / (uv).w).r)
#define UNITY_PROJ_COORD(a) a
half3 DecodeHDR(half4 data, half4 decodeInstructions) { return data.rgb * decodeInstructions.x; }
float4 _Time;
float3 _WorldSpaceCameraPos;
float4 _ScreenParams;
float4 _ProjectionParams;
float4 _ZBufferParams;
float4x4 unity_ObjectToWorld;
float4x4 unity_WorldToObject;
float4x4 UNITY_MATRIX_P;
float4x4 UNITY_MATRIX_V;
float4x4 UNITY_MATRIX_VP;
float4x4 UNITY_MATRIX_MV;
float4 unity_FogColor;
float4 unity_WorldTransformParams;
float LinearEyeDepth(float z) { return 1.0 / (_ZBufferParams.z * z + _ZBufferParams.w); }
float4 UnityObjectToClipPos(float3 p) { return mul(UNITY_MATRIX_VP, mul(unity_ObjectToWorld, float4(p, 1.0))); }
float4 UnityObjectToClipPos(float4 p) { return UnityObjectToClipPos(p.xyz); }
float4 UnityWorldToClipPos(float3 p) { return mul(UNITY_MATRIX_VP, float4(p, 1.0)); }
float3 UnityObjectToWorldDir(float3 d) { return normalize(mul((float3x3)unity_ObjectToWorld, d)); }
float3 UnityObjectToWorldNormal(float3 n) { return normalize(mul(n, (float3x3)unity_WorldToObject)); }
float3 UnityObjectToViewPos(float3 p) { return mul(UNITY_MATRIX_V, mul(unity_ObjectToWorld, float4(p, 1.0))).xyz; }
float4 ComputeScreenPos(float4 p) { float4 o = p * 0.5; o.xy = float2(o.x, o.y * _ProjectionParams.x) + o.w; o.zw = p.zw; return o; }
#define COMPUTE_EYEDEPTH(o) o = -UnityObjectToViewPos(v.vertex.xyz).z
half3 UnpackNormal(half4 p) { half3 n; n.xy = p.wy * 2 - 1; n.z = sqrt(1 - saturate(dot(n.xy, n.xy))); return n; }
half3 UnpackScaleNormal(half4 p, half s) { half3 n = UnpackNormal(p); n.xy *= s; return normalize(n); }
half3 ShadeSH9(half4 n) { return half3(0.1, 0.1, 0.1); }
float3 GammaToLinearSpace(float3 c) { return c * c; }
float3 LinearToGammaSpace(float3 c) { return sqrt(c); }
#define TRANSFORM_TEX(tex, name) (tex.xy * name##_ST.xy + name##_ST.zw)
#define UNITY_VERTEX_INPUT_INSTANCE_ID uint instanceID : SV_InstanceID;
#define UNITY_VERTEX_OUTPUT_STEREO uint stereoTargetEyeIndex : SV_RenderTargetArrayIndex;
#define UNITY_SETUP_INSTANCE_ID(v)
#define UNITY_INITIALIZE_OUTPUT(type, name) name = (type)0
#define UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o) o.stereoTargetEyeIndex = 0
#define UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)
#define UNITY_FOG_COORDS(idx) float1 fogCoord : TEXCOORD##idx;
#define UNITY_TRANSFER_FOG(o, outpos) o.fogCoord = outpos.z
#define UNITY_APPLY_FOG_COLOR(coord, col, fogCol) col.rgb = lerp((fogCol).rgb, (col).rgb, saturate((coord).x))
#define UNITY_APPLY_FOG(coord, col) UNITY_APPLY_FOG_COLOR(coord, col, unity_FogColor)

// ---- v2 additions: reflection probe 0, appdata_full, reversed Z
TextureCube<float4> unity_SpecCube0; SamplerState samplerunity_SpecCube0;
float4 unity_SpecCube0_HDR;
float4 unity_SpecCube0_BoxMax;
float4 unity_SpecCube0_BoxMin;
float4 unity_SpecCube0_ProbePosition;
struct appdata_full { float4 vertex : POSITION; float4 tangent : TANGENT; float3 normal : NORMAL; float4 texcoord : TEXCOORD0;
                      float4 texcoord1 : TEXCOORD1; float4 texcoord2 : TEXCOORD2; float4 texcoord3 : TEXCOORD3; float4 color : COLOR; };
#define UNITY_REVERSED_Z 1
// ---- surface-shader glue (what the generator provides to surf())
#define INTERNAL_DATA half3 internalSurfaceTtoW0; half3 internalSurfaceTtoW1; half3 internalSurfaceTtoW2;
#define WorldNormalVector(data, normal) float3(dot(data.internalSurfaceTtoW0, normal), dot(data.internalSurfaceTtoW1, normal), dot(data.internalSurfaceTtoW2, normal))
struct SurfaceOutputStandard { half3 Albedo; float3 Normal; half3 Emission; half Metallic; half Smoothness; half Occlusion; half Alpha; };

// ---- Act04c_Inside additions (门内 / 镜 / 白 / 灯 / 假醒): fog params, fwidth-based helpers
float4 unity_FogParams;
