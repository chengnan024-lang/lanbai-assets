# `_Udon_` 全局量对账（自动生成：`Engineering/ledgers/globals_scan.py`）

登记表 = `origin/main:Common/UdonGlobals.md`。扫的分支：`origin/main` (1cc54e5)、`origin/pkg/engineering` (b194b65)、`origin/pkg/inside` (4bea446)、`origin/pkg/lamps` (d512f2c)、`origin/pkg/sea` (ce2cec9)、`origin/pkg/sky` (a686dde)。
write = C# 里 `SetGlobal*`；decl = shader 里声明；id / ref = 其他引用；doc = 只在文档里。

## 要处理的（17）

- `_Udon_CloudTopY`：只在文档里、没登记
  - `main` `Gate/Source/gate_scene.py` doc 
  - `pkg/engineering` `Gate/Source/gate_scene.py` doc 
  - `pkg/inside` `Gate/Source/gate_scene.py` doc 
  - `pkg/lamps` `Gate/Source/gate_scene.py` doc 
  - `pkg/sea` `Gate/Source/gate_scene.py` doc 
  - `pkg/sky` `Gate/Source/gate_scene.py` doc 
- `_Udon_FogBand`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` ref 
  - `pkg/sky` `Sky/Tools~/compile_check/tests/T_FogThenGate_ExpectFail.shader` ref 
- `_Udon_FogBase`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiFog.cginc` decl float4
- `_Udon_FogBelow`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_FogCube`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl samplerCUBE
- `_Udon_FogCubeParams`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_FogShape`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_HorizonColor`：预留名已在代码里用（请把登记从“预留”挪到“已经在用”）
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_NadirColor`：**没登记**
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_RainRate`：只在文档里、没登记
  - `main` `Art/reference/lens_lookdev.md` doc 
  - `pkg/engineering` `Art/reference/lens_lookdev.md` doc 
  - `pkg/inside` `Art/reference/lens_lookdev.md` doc 
  - `pkg/lamps` `Art/reference/lens_lookdev.md` doc 
  - `pkg/sea` `Art/reference/lens_lookdev.md` doc 
  - `pkg/sky` `Art/reference/lens_lookdev.md` doc 
- `_Udon_SeatPos`：只在文档里、没登记
  - `main` `Art/reference/lens_lookdev.md` doc 
  - `pkg/engineering` `Art/reference/lens_lookdev.md` doc 
  - `pkg/inside` `Art/reference/lens_lookdev.md` doc 
  - `pkg/lamps` `Art/reference/lens_lookdev.md` doc 
  - `pkg/sea` `Art/reference/lens_lookdev.md` doc 
  - `pkg/sky` `Art/reference/lens_lookdev.md` doc 
- `_Udon_SunDir`：预留名已在代码里用（请把登记从“预留”挪到“已经在用”）
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_SunDisc`：预留名已在代码里用（请把登记从“预留”挪到“已经在用”）
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4
- `_Udon_TubeLevels0`：只在文档里、没登记
  - `main` `Art/reference/lens_tech.md` doc 
  - `pkg/engineering` `Art/reference/lens_tech.md` doc 
  - `pkg/inside` `Art/reference/lens_tech.md` doc 
  - `pkg/lamps` `Art/reference/lens_tech.md` doc 
  - `pkg/sea` `Art/reference/lens_tech.md` doc 
  - `pkg/sky` `Art/reference/lens_tech.md` doc 
- `_Udon_TubeLevelsN`：只在文档里、没登记
  - `main` `Art/reference/lens_tech.md` doc 
  - `pkg/engineering` `Art/reference/lens_tech.md` doc 
  - `pkg/inside` `Art/reference/lens_tech.md` doc 
  - `pkg/lamps` `Art/reference/lens_tech.md` doc 
  - `pkg/sea` `Art/reference/lens_tech.md` doc 
  - `pkg/sky` `Art/reference/lens_tech.md` doc 
- `_Udon_WindowRect`：只在文档里、没登记
  - `main` `Art/reference/critique_feasibility.md` doc 
  - `pkg/engineering` `Art/reference/critique_feasibility.md` doc 
  - `pkg/inside` `Art/reference/critique_feasibility.md` doc 
  - `pkg/lamps` `Art/reference/critique_feasibility.md` doc 
  - `pkg/sea` `Art/reference/critique_feasibility.md` doc 
  - `pkg/sky` `Art/reference/critique_feasibility.md` doc 
- `_Udon_ZenithColor`：预留名已在代码里用（请把登记从“预留”挪到“已经在用”）
  - `pkg/sky` `Common/Shaders/LanbaiSky.cginc` decl float4

## 全表

| 全局量 | 登记 | 出现在 |
|---|---|---|
| `_Udon_CabinAmbient` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_CabinBleach` | 在用 | （只在文档） |
| `_Udon_CabinFade` | 在用 | （只在文档） |
| `_Udon_CabinLightmap` | 在用 | main（decl:float,ref）；pkg/engineering（decl:float,ref）；pkg/inside（decl:float,ref）；pkg/lamps（decl:float,ref）；pkg/sea（decl:float,ref）；pkg/sky（decl:float,ref） |
| `_Udon_CaseLight` | 在用 | main（decl:float）；pkg/engineering（decl:float）；pkg/inside（decl:float）；pkg/lamps（decl:float）；pkg/sea（decl:float）；pkg/sky（decl:float） |
| `_Udon_Caustics` | 在用 | （只在文档） |
| `_Udon_CausticsColor` | 在用 | （只在文档） |
| `_Udon_CausticsTex` | 在用 | （只在文档） |
| `_Udon_CloudTop` | 在用 | main（decl:float4,write:Vector）；pkg/engineering（decl:float4,write:Vector）；pkg/inside（decl:float4,write:Vector）；pkg/lamps（decl:float4,write:Vector）；pkg/sea（decl:float4,write:Vector）；pkg/sky（decl:float4,write:Vector） |
| `_Udon_CloudTopY` | — | （只在文档） |
| `_Udon_Drip0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_Drip1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Drip2` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Drip3` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_FlowDir` | 在用 | main（decl:float4,id,ref）；pkg/engineering（decl:float4,id,ref）；pkg/inside（decl:float4,id,ref）；pkg/lamps（decl:float4,id,ref）；pkg/sea（decl:float4,id,ref）；pkg/sky（decl:float4,id,ref） |
| `_Udon_FlowDirB` | 在用 | main（decl:float4,id,ref）；pkg/engineering（decl:float4,id,ref）；pkg/inside（decl:float4,id,ref）；pkg/lamps（decl:float4,id,ref）；pkg/sea（decl:float4,id,ref）；pkg/sky（decl:float4,id,ref） |
| `_Udon_FlowMix` | 在用 | main（decl:float,id,ref）；pkg/engineering（decl:float,id,ref）；pkg/inside（decl:float,id,ref）；pkg/lamps（decl:float,id,ref）；pkg/sea（decl:float,id,ref）；pkg/sky（decl:float,id,ref） |
| `_Udon_FogBand` | — | pkg/sky（ref） |
| `_Udon_FogBandColor` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_FogBandDir` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_FogBandWidth` | 在用 | main（decl:float）；pkg/engineering（decl:float）；pkg/inside（decl:float）；pkg/lamps（decl:float）；pkg/sea（decl:float）；pkg/sky（decl:float） |
| `_Udon_FogBase` | — | pkg/sky（decl:float4） |
| `_Udon_FogBelow` | — | pkg/sky（decl:float4） |
| `_Udon_FogCube` | — | pkg/sky（decl:samplerCUBE） |
| `_Udon_FogCubeParams` | — | pkg/sky（decl:float4） |
| `_Udon_FogDensity` | 在用 | main（decl:float）；pkg/engineering（decl:float）；pkg/inside（decl:float）；pkg/lamps（decl:float）；pkg/sea（decl:float）；pkg/sky（decl:float） |
| `_Udon_FogShape` | — | pkg/sky（decl:float4） |
| `_Udon_GalaxyGain` | 预留 | （只在文档） |
| `_Udon_GateOrigin` | 在用 | main（decl:float4,ref,write:Vector）；pkg/engineering（decl:float4,ref,write:Vector）；pkg/inside（decl:float4,ref,write:Vector）；pkg/lamps（decl:float4,ref,write:Vector）；pkg/sea（decl:float4,ref,write:Vector）；pkg/sky（decl:float4,ref,write:Vector） |
| `_Udon_GateTime` | 在用 | main（decl:float,write:Float）；pkg/engineering（decl:float,write:Float）；pkg/inside（decl:float,write:Float）；pkg/lamps（decl:float,write:Float）；pkg/sea（decl:float,write:Float）；pkg/sky（decl:float,write:Float） |
| `_Udon_HorizonColor` | 预留 | pkg/sky（decl:float4） |
| `_Udon_Lamp0` | 在用 | main（decl:float4,ref）；pkg/engineering（decl:float4,ref）；pkg/inside（decl:float4,ref）；pkg/lamps（decl:float4,ref）；pkg/sea（decl:float4,ref）；pkg/sky（decl:float4,ref） |
| `_Udon_Lamp1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp2` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp3` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp4` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp5` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp6` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_Lamp7` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_LampAxis1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis2` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis3` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis4` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis5` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis6` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampAxis7` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_LampColor1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor2` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor3` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor4` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor5` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor6` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampColor7` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_LampDir1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir2` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir3` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir4` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir5` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir6` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_LampDir7` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_MirrorIndex` | 预留 | （只在文档） |
| `_Udon_MirrorPhase` | 预留 | （只在文档） |
| `_Udon_MoonDir` | 在用 | main（decl:float4,ref,write:Vector）；pkg/engineering（decl:float4,ref,write:Vector）；pkg/inside（decl:float4,ref,write:Vector）；pkg/lamps（decl:float4,ref,write:Vector）；pkg/sea（decl:float4,ref,write:Vector）；pkg/sky（decl:float4,ref,write:Vector） |
| `_Udon_MoonDisc` | 在用 | main（decl:float4,ref,write:Vector）；pkg/engineering（decl:float4,ref,write:Vector）；pkg/inside（decl:float4,ref,write:Vector）；pkg/lamps（decl:float4,ref,write:Vector）；pkg/sea（decl:float4,ref,write:Vector）；pkg/sky（decl:float4,ref,write:Vector） |
| `_Udon_MultReveal` | 在用 | main（decl:float4,write:Vector）；pkg/engineering（decl:float4,write:Vector）；pkg/inside（decl:float4,write:Vector）；pkg/lamps（decl:float4,write:Vector）；pkg/sea（decl:float4,write:Vector）；pkg/sky（decl:float4,write:Vector） |
| `_Udon_NadirColor` | — | pkg/sky（decl:float4） |
| `_Udon_OneDropA` | 在用 | main（decl:float4,id）；pkg/engineering（decl:float4,id）；pkg/inside（decl:float4,id）；pkg/lamps（decl:float4,id）；pkg/sea（decl:float4,id）；pkg/sky（decl:float4,id） |
| `_Udon_OneDropB` | 在用 | main（decl:float4,id）；pkg/engineering（decl:float4,id）；pkg/inside（decl:float4,id）；pkg/lamps（decl:float4,id）；pkg/sea（decl:float4,id）；pkg/sky（decl:float4,id） |
| `_Udon_OverlayAlpha` | 预留 | （只在文档） |
| `_Udon_OverlayColor` | 预留 | （只在文档） |
| `_Udon_RainAmount` | 在用 | main（decl:float,id,ref）；pkg/engineering（decl:float,id,ref）；pkg/inside（decl:float,id,ref）；pkg/lamps（decl:float,id,ref）；pkg/sea（decl:float,id,ref）；pkg/sky（decl:float,id,ref） |
| `_Udon_RainFall` | 在用 | main（decl:float,id）；pkg/engineering（decl:float,id）；pkg/inside（decl:float,id）；pkg/lamps（decl:float,id）；pkg/sea（decl:float,id）；pkg/sky（decl:float,id） |
| `_Udon_RainRate` | — | （只在文档） |
| `_Udon_ReflCube` | 在用 | main（decl:UNITY_DECLARE_TEXCUBE,ref）；pkg/engineering（decl:UNITY_DECLARE_TEXCUBE,ref）；pkg/inside（decl:UNITY_DECLARE_TEXCUBE,ref）；pkg/lamps（decl:UNITY_DECLARE_TEXCUBE,ref）；pkg/sea（decl:UNITY_DECLARE_TEXCUBE,ref）；pkg/sky（decl:UNITY_DECLARE_TEXCUBE,ref） |
| `_Udon_ReflCube_HDR` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_ReflExposure` | 在用 | main（decl:float）；pkg/engineering（decl:float）；pkg/inside（decl:float）；pkg/lamps（decl:float）；pkg/sea（decl:float）；pkg/sky（decl:float） |
| `_Udon_RipProgress` | 在用 | main（id,ref,write:Float）；pkg/engineering（id,ref,write:Float）；pkg/inside（id,ref,write:Float）；pkg/lamps（id,ref,write:Float）；pkg/sea（id,ref,write:Float）；pkg/sky（id,ref,write:Float） |
| `_Udon_RunClock` | 在用 | main（decl:float4,id,ref）；pkg/engineering（decl:float4,id,ref）；pkg/inside（decl:float4,id,ref）；pkg/lamps（decl:float4,id,ref）；pkg/sea（decl:float4,id,ref）；pkg/sky（decl:float4,id,ref） |
| `_Udon_RunStretch` | 在用 | main（decl:float,id,ref）；pkg/engineering（decl:float,id,ref）；pkg/inside（decl:float,id,ref）；pkg/lamps（decl:float,id,ref）；pkg/sea（decl:float,id,ref）；pkg/sky（decl:float,id,ref） |
| `_Udon_SeaClock` | 在用 | （只在文档） |
| `_Udon_SeaLevel` | 在用 | （只在文档） |
| `_Udon_SeaMode` | 在用 | （只在文档） |
| `_Udon_SeatPos` | — | （只在文档） |
| `_Udon_SkyBlend` | 预留 | （只在文档） |
| `_Udon_StarGain` | 预留 | （只在文档） |
| `_Udon_StopOffset` | 在用 | main（decl:float4,id,ref）；pkg/engineering（decl:float4,id,ref）；pkg/inside（decl:float4,id,ref）；pkg/lamps（decl:float4,id,ref）；pkg/sea（decl:float4,id,ref）；pkg/sky（decl:float4,id,ref） |
| `_Udon_SunDir` | 预留 | pkg/sky（decl:float4） |
| `_Udon_SunDisc` | 预留 | pkg/sky（decl:float4） |
| `_Udon_T` | 在用 | （只在文档） |
| `_Udon_TearBreath` | 在用 | main（id,ref）；pkg/engineering（id,ref）；pkg/inside（id,ref）；pkg/lamps（id,ref）；pkg/sea（id,ref）；pkg/sky（id,ref） |
| `_Udon_TearFoot` | 在用 | main（decl:float4,write:Vector）；pkg/engineering（decl:float4,write:Vector）；pkg/inside（decl:float4,write:Vector）；pkg/lamps（decl:float4,write:Vector）；pkg/sea（decl:float4,write:Vector）；pkg/sky（decl:float4,write:Vector） |
| `_Udon_TearH` | 在用 | main（decl:float4,ref,write:Vector）；pkg/engineering（decl:float4,ref,write:Vector）；pkg/inside（decl:float4,ref,write:Vector）；pkg/lamps（decl:float4,ref,write:Vector）；pkg/sea（decl:float4,ref,write:Vector）；pkg/sky（decl:float4,ref,write:Vector） |
| `_Udon_TearHide` | 在用 | main（id,ref,write:Float）；pkg/engineering（id,ref,write:Float）；pkg/inside（id,ref,write:Float）；pkg/lamps（id,ref,write:Float）；pkg/sea（id,ref,write:Float）；pkg/sky（id,ref,write:Float） |
| `_Udon_TearOpen` | 在用 | main（decl:float,id,write:Float）；pkg/engineering（decl:float,id,write:Float）；pkg/inside（decl:float,id,write:Float）；pkg/lamps（decl:float,id,write:Float）；pkg/sea（decl:float,id,write:Float）；pkg/sky（decl:float,id,write:Float） |
| `_Udon_TearPos` | 在用 | main（decl:float4,ref,write:Vector）；pkg/engineering（decl:float4,ref,write:Vector）；pkg/inside（decl:float4,ref,write:Vector）；pkg/lamps（decl:float4,ref,write:Vector）；pkg/sea（decl:float4,ref,write:Vector）；pkg/sky（decl:float4,ref,write:Vector） |
| `_Udon_TearTop` | 在用 | main（decl:float4,write:Vector）；pkg/engineering（decl:float4,write:Vector）；pkg/inside（decl:float4,write:Vector）；pkg/lamps（decl:float4,write:Vector）；pkg/sea（decl:float4,write:Vector）；pkg/sky（decl:float4,write:Vector） |
| `_Udon_TubeLevels0` | — | （只在文档） |
| `_Udon_TubeLevelsN` | — | （只在文档） |
| `_Udon_Underwater` | 在用 | （只在文档） |
| `_Udon_WaterFogDown` | 在用 | （只在文档） |
| `_Udon_WaterFogMid` | 在用 | （只在文档） |
| `_Udon_WaterFogUp` | 在用 | （只在文档） |
| `_Udon_Wetness` | 在用 | main（decl:float,id,ref）；pkg/engineering（decl:float,id,ref）；pkg/inside（decl:float,id,ref）；pkg/lamps（decl:float,id,ref）；pkg/sea（decl:float,id,ref）；pkg/sky（decl:float,id,ref） |
| `_Udon_WindowRect` | — | （只在文档） |
| `_Udon_Wiper` | 在用 | （只在文档） |
| `_Udon_WiperAxis0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_WiperAxis1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_WiperPivot0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_WiperPivot1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_WiperRest0` | 在用 | main（decl:float4）；pkg/engineering（decl:float4）；pkg/inside（decl:float4）；pkg/lamps（decl:float4）；pkg/sea（decl:float4）；pkg/sky（decl:float4） |
| `_Udon_WiperRest1` | 在用 | main（ref）；pkg/engineering（ref）；pkg/inside（ref）；pkg/lamps（ref）；pkg/sea（ref）；pkg/sky（ref） |
| `_Udon_WiperTime` | 在用 | main（decl:float4,id）；pkg/engineering（decl:float4,id）；pkg/inside（decl:float4,id）；pkg/lamps（decl:float4,id）；pkg/sea（decl:float4,id）；pkg/sky（decl:float4,id） |
| `_Udon_WorldS` | 在用 | （只在文档） |
| `_Udon_ZenithColor` | 预留 | pkg/sky（decl:float4） |
