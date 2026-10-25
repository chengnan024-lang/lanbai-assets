// =====================================================================================================
//  Lanbai / GateVolumeDeck   (gate clouds kit, D-44 #3, 2026-10-25)   author of the cloud: 阿白
//  !!! WRITTEN WITHOUT A UNITY COMPILER; checked with Common/Tools~/compile_check (DXC + Unity CGIncludes). !!!
//
//  阿白's Lanbai/Local/VolumeCloudDeck (FromLocal/full_preview/20261025-0103/review_sources/LocalIntegration/Shaders/
//  VolumeCloudDeck.shader.txt), unchanged except for the ROOT SKIRTS (D-44 #3: the cloud gathers round every arm that
//  pierces it): density() = max(阿白's shape, LanbaiGateSkirtSet(...)) x the comfort cut x _Density, the skirts culled
//  once per ray (LanbaiCloudVolume.cginc). Its shape is now LanbaiCloudShape (the same lines), so the arms
//  (Lanbai/TentacleSway v2.8) read the very same density.
//  INTERIM: the cloud package is turning this deck into the shared version; it only has to (1) take its shape from
//  LanbaiCloudShape (or keep it identical), (2) add the lines marked [D-44], (3) leave _Udon_CloudVolume* to the gate
//  clouds driver (which copies THIS material's _NoiseVolume / _Density / _CloudWind into the globals, so the arms and the
//  deck cannot disagree). Reference render: GateClouds/Source/seam_ref.py.
// =====================================================================================================
Shader "Lanbai/GateVolumeDeck"
{
    Properties
    {
        _NoiseVolume ("Cloud density volume", 3D) = "white" {}
        _Density ("Extinction per metre", Float) = 0.036
        [Header(Tiles  deck_tiles.py)]
        [NoScaleOffset] _DetailTex ("Deck_Detail_1024 (R height, G moon path, B sky AO, A moon N.L); linear", 2D) = "gray" {}
        [NoScaleOffset] _MacroTex ("Deck_Macro_512 (R swell, G moon path, B amplitude, A brightness); linear", 2D) = "gray" {}
        [NoScaleOffset] _LanesTex ("Tear_CloudLanes_1024 (R 1 = lit, 0.15 = root shadow); linear", 2D) = "white" {}
        _Periods ("Periods m: detail, macro, micro scale, anisotropy max", Vector) = (1600, 6400, 5, 4)
        _DetailRange ("Detail height min, max (m); macro min, max (m)", Vector) = (-12, 56, -12, 12)
        _TauMax ("Moon path max (m): detail, macro", Vector) = (160, 400, 0, 0)
        _AmpRange ("Detail amplitude: macro B 0..1 maps to min..max; brightness min, max", Vector) = (0.3, 0.8, 0.75, 1.15)
        _Micro ("Micro: amplitude m, envelope, shading, -", Vector) = (4, 0.35, 0.9, 0)

        _CloudWind ("Independent wind m/s (detail xy, macro zw)", Vector) = (8, 3, -2, 1)
        [Header(March)]
        _Steps ("Max steps (mean use 16-24)", Range(16, 160)) = 128
        _Adapt ("Adaptive steps: k min, k max (x t), clearance factor, slope", Vector) = (0.004, 0.05, 0.9, 0.6)
        _MarchRange ("March from (m), to (m); far mean height above the top (m); bisections", Vector) = (12, 2500, 8, 3)
        _Comfort ("Comfort: clearance under the eye (m), lane depth under the eye (m), lane half width full, gone (m)", Vector) = (2, 57, 45, 140)
        _LodBias ("LOD bias", Range(-2, 2)) = 0

        [Header(Light)]
        _MoonColor ("Moon colour #D6E4FF, linear", Vector) = (0.6724, 0.7758, 1.0, 1)
        _MoonE ("Moon radiance on the deck", Range(0, 2)) = 0.38
        _AmbColor ("Sky ambient (HazeFar), linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _AmbK ("Sky ambient x AO (round 4: 0.35, deeper troughs)", Range(0, 2)) = 0.35
        _Phase ("HG g1, g2, mix, surface lobe softening", Vector) = (0.8, -0.18, 0.62, 0.35)
        _Skin ("Skin: sigma (1/m), edge (m), approach weight, sigma toward the moon", Vector) = (0.8, 0.5, 0.0, 0.12)
        _Skin2 ("Skin: silhouette gap (x t), sub-pixel fade (x edge / footprint), commit rise (x edge), crest cover (px)", Vector) = (0.04, 1.5, 1, 1.5)
        _Skin3 ("Skin: silhouette ramp from, to (x gap); per-head rim min, max", Vector) = (0.5, 3, 0.4, 1.6)
        _RimVarScale ("Per-head rim noise scale (x detail period)", Float) = 0.37
        _RimWedge ("Rim wedges: moon path half angle (deg), moon path gain, foot radius (m), outside", Vector) = (7, 0.9, 600, 0.16)
        _Surf ("Surface: sigma toward the moon, forward lobe, Lambert, cast-shadow scale", Vector) = (0.14, 0.015, 0.8, 0.35)
        _Ms ("Multiple scattering: k, tau scale; far rim, -", Vector) = (0.01, 0.28, 0, 0)
        _Trough ("Troughs: coarse LOD offset, depth (m), strength, fog fraction", Vector) = (3.5, 18, 0.7, 0.4)
        _Gain ("Gain", Range(0, 3)) = 0.9

        [Header(Pool and crevasse  GateLayout clouds.pool  tear.crevasse)]
        _PoolTint ("Pool tint (dst x (1 + tint x weight)), linear; w = strength", Vector) = (0.607, 0.683, 1.144, 1.5)
        _LanesRect ("Tear_CloudLanes rect in the tear frame: x0, x1, y0 (bus side), y1 (far) m", Vector) = (-2000, 2000, -2400, 1600)
        _Crev ("Crevasse: length x S (m), half width / white half width, depth (m), lip height (m)", Vector) = (230, 0.4, 25, 5)
        _CrevGlow ("Crevasse floor glow #C0B9E4 x 0.35, linear", Vector) = (0.184, 0.170, 0.272, 1)
        _FootPool ("Foot light: radius (m), offset toward the bus (m, < 0 = beyond the foot), strength, floor under the tops  (x S / 0.64)", Vector) = (160, -100, 6.0, 0.1)
        _FootPoolColor ("Foot pool colour #E2E8F3, linear", Vector) = (0.7605, 0.8070, 0.8963, 1)
        _TearFootW ("Tear foot fallback: world xyz, w = white half width (global _Udon_TearFoot wins)", Vector) = (-0.3, -57.4, 1497.6, 76)

        [Header(Fog  LanbaiGateSky)]
        _FogDensity ("Fog density (gate 0.0006), scale, moon air", Vector) = (0.0006, 1.3, 0.35, 0)
        _CloudTopY ("Cloud top world y (fallback; _Udon_CloudTop wins)", Float) = -57.4
        _GateOrigin ("GateRoot position (fallback; _Udon_GateOrigin wins)", Vector) = (0, 92.6, 1478.4, 0)
        _RimDir ("Direction to the moon (fallback; _Udon_MoonDir wins)", Vector) = (-0.2059, 0.1392, 0.9686, 0)

        // shared with LanbaiGateSky.cginc (same values as the skybox and the arms)
        _HazeNear ("Haze Band Next To The Tear, linear", Vector) = (0.1085, 0.1130, 0.1641, 1)
        _HazeFar ("Haze Band 50 deg Away, linear", Vector) = (0.0436, 0.0504, 0.0726, 1)
        _Void ("Void, linear", Vector) = (0.0021, 0.0030, 0.0070, 1)
        _BandAz ("Band azimuth", Vector) = (50, 60, 0, 0)
        _BandEl ("Band elevation", Vector) = (6, 22, 2, 0)
        _BelowHorizon ("Below the horizon", Vector) = (-25, 0, 0.55, 0)
        _BelowDesat ("Below-horizon desaturation", Range(0, 1)) = 0.6
        _BackBand ("Back band (rear view 1.25)", Range(0, 2)) = 0.55
        _TearPos ("Tear core fallback (world)", Vector) = (0, 297, 1800, 0)
        _MoonGlowColor ("Moon aureole, linear", Vector) = (0.275, 0.366, 0.578, 1)
        _MoonGlowShape ("Aureole shape", Vector) = (1.6, 0.9, 0.06, 0.32)
        _HaloColor ("Halo (unused here)", Vector) = (0.195, 0.198, 0.332, 1)
    }

    SubShader {
      Tags { "Queue"="Transparent-20" "RenderType"="Transparent" "IgnoreProjector"="True" "DisableBatching"="True" }
      Pass {
        Blend One OneMinusSrcAlpha
        Cull Off ZWrite Off ZTest LEqual
        CGPROGRAM
        #pragma vertex vert
        #pragma fragment frag
        #pragma target 4.5
        #pragma multi_compile_instancing
        #include "UnityCG.cginc"
        #include "Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc"
        #include "Assets/Lanbai/GateClouds/Shaders/LanbaiCloudVolume.cginc"   // [D-44]
        sampler3D _NoiseVolume;
        UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
        float4 _CloudWind, _MoonColor, _AmbColor, _RimDir, _GateOrigin, _FogDensity, _FootPoolColor;
        float _Density, _CloudTopY, _MoonE, _AmbK, _Gain;
        struct appdata { float4 vertex:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct v2f { float4 pos:SV_POSITION; float3 wpos:TEXCOORD0; float4 screen:TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };
        v2f vert(appdata v) {
          v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
          float3 p=mul(unity_ObjectToWorld,v.vertex).xyz;
          p.y=_WorldSpaceCameraPos.y-1.5;
          o.wpos=p;o.pos=UnityWorldToClipPos(p);o.screen=ComputeScreenPos(o.pos);return o;
        }
        float density(float3 p,float top,float3 origin,LanbaiSkirtSet sk) {
          float2 nrg;
          float shape=LanbaiCloudShape(_NoiseVolume,p,top,origin,_CloudWind.xy,_Udon_GateTime,float2(520.0,260.0),nrg);
          shape=max(shape,LanbaiGateSkirtSet(p,top,nrg,sk));                                  // [D-44] the root skirts
          // Soft comfort envelope: there are no dense billows next to the viewer's face.
          float comfort=1.0-smoothstep(_WorldSpaceCameraPos.y-40.0,_WorldSpaceCameraPos.y-18.0,p.y);
          return shape*comfort*_Density;
        }
        half4 frag(v2f i):SV_Target {
          UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
          float3 eye=_WorldSpaceCameraPos;
          float3 ray=normalize(i.wpos-eye);
          if(ray.y>=-0.0005)discard;
          float top=_Udon_CloudTop.w>0?_Udon_CloudTop.x:_CloudTopY;
          float3 origin=_Udon_GateOrigin.w>0?_Udon_GateOrigin.xyz:_GateOrigin.xyz;
          float upper=min(top+30.0,eye.y-18.0),lower=top-170.0;
          float start=max(0.0,(upper-eye.y)/ray.y);
          float end=min(4200.0,(lower-eye.y)/ray.y);
          float2 uv=UnityStereoTransformScreenSpaceTex(i.screen.xy/i.screen.w);
          float sceneEye=LinearEyeDepth(SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture,uv));
          float eyeRate=max(0.0001,-mul((float3x3)UNITY_MATRIX_V,ray).z);
          end=min(end,sceneEye/eyeRate);
          if(end<=start)discard;
          int count=ray.y > -0.35 ? 80 : 56;
          float stepLength=(end-start)/count;
          float jitter=0.2+0.6*tex3Dlod(_NoiseVolume,float4((eye+ray*start)*0.073,0)).g;
          float3 moon=LanbaiMoonDir(_RimDir.xyz);
          float3 fog=LanbaiGateFogColour(ray,1000.0,moon,_FogDensity.z,0.3);
          LanbaiSkirtSet sk=LanbaiGateSkirtCull(eye,ray,start,end);                          // [D-44]
          float3 sum=0;float transmission=1;
          float facing=pow(saturate(dot(ray,moon)),5.0);
          [loop] for(int s=0;s<80;s++) {
            if(s>=count)break;
            float t=start+(s+jitter)*stepLength;
            float3 p=eye+ray*t;
            if(_Udon_InsidePortal.y>.5 && eye.z>_Udon_InsidePortal.x && p.z>_Udon_InsidePortal.x)break;
            float den=density(p,top,origin,sk);
            if(den>0.00008) {
              float optical=density(p+moon*18.0,top,origin,sk)*22.0+density(p+moon*50.0,top,origin,sk)*38.0;
              float illumination=0.08+0.92*exp(-optical*1.7);
              float height=saturate((p.y-(top-120.0))/140.0);
              float3 light=_AmbColor.rgb*(.3+height*.35)+_MoonColor.rgb*_MoonE*illumination*(.65+facing*.35);
              if(_Udon_TearFoot.w>0) {
                float dist=length((p.xz-_Udon_TearFoot.xz)/float2(180,240));
                light+=_FootPoolColor.rgb*.09*exp(-dist*dist)*height;
              }
              light=lerp(light*_Gain,fog,1.0-exp(-LanbaiGateDensity(_FogDensity.x)*t));
              float alpha=1.0-exp(-den*stepLength);
              sum+=transmission*alpha*light;
              transmission*=1.0-alpha;
              if(transmission<0.015)break;
            }
          }
          return half4(sum,1.0-transmission);
        }
        ENDCG
      }
    }
    Fallback Off
}
