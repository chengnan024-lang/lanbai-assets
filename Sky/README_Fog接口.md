# 天与雾的共用 include（`Common/Shaders/LanbaiFog.cginc`、`LanbaiSky.cginc`）· 接口说明 v1.1

写的人：云端子会话「天空」。v1 2026-10-22，**v1.1 2026-10-23**（按总工程师第 1 轮意见改，见 §7）。**没在 Unity 里编译过**：只用 slang 查过语法和类型（37 个变体，含 SPS-I 立体、FOG_EXP2 / LINEAR、表面着色器的 ForwardAdd），另外用 slang 在 CPU 上把门的 `LanbaiBand` 和这里的 `LanbaiHorizon` 逐方向算了一遍，结果相同（§5）。

## 1. 怎么用（给海、门内、门、车厢……所有自定义 shader）

```hlsl
#pragma multi_compile_fog
#include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"     // 它会 include LanbaiSky.cginc 和 LanbaiVR.cginc
...
col.rgb = LanbaiApplyFog(col.rgb, i.worldPos);              // 线性颜色；不要再对同一个颜色用 UNITY_APPLY_FOG
```
材质上加两个属性（可以不加，不加 = 不封顶、不做高度衰减）：
```
_FogCap ("Fog Cap", Range(0, 1)) = 1
_FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
```
- **表面着色器**：`#pragma surface surf ... finalcolor:lbfog nofog`，而且 **ForwardAdd（每盏像素灯一遍）里只衰减、不加雾色**，否则每盏灯多加一份地平线色：
  ```hlsl
  void lbfog(Input IN, SurfaceOutputStandard o, inout fixed4 color) {
  #ifdef UNITY_PASS_FORWARDADD
      color.rgb = LanbaiApplyFogAdditive(color.rgb, IN.worldPos);
  #else
      color.rgb = LanbaiApplyFog(color.rgb, IN.worldPos);
  #endif
  }
  ```
- 叠加 / 预乘透明的 pass：`LanbaiApplyFogAdditive(col, posWS)`。
- 粒子、透明卡（叠很多层的）：顶点里 `o.fog = LanbaiFogVertex(posWS)`（rgb = 雾色、a = 雾量），片元里 `col = lerp(col, i.fog.rgb, i.fog.a)`（叠加的 `col *= 1 - i.fog.a`）。
- 第 4 幕想和触手一样带月晕 / 伤口空气：`LanbaiApplyFogEx(col, pos, extraAir)`，`extraAir` = `LanbaiGateFogColour(...) − LanbaiBand(V)`（要先 include 门的 `LanbaiGateSky.cginc`，见 §5）。
- 天上的东西（日、月、星、远处灯点、裂口……圣经的 `_FogMode 2`）**不调雾**，用 `LanbaiSkyObjectAtten(dist, atten)` = exp(−d·atten)。
- **include 之后不要再自己声明** `_FogCap`、`_FogHeightFalloff`、`_Udon_Fog*`（重复声明，FXC X3003）。自己已经声明了其中某个的 shader，**在 include 之前**声明它并定义对应的保护宏（§4）。

## 2. 接口（总控 §4 的最小接口，名字和参数不变；后面是加的）

| 函数 | 说明 |
|---|---|
| `float3 LanbaiHorizon(float3 dirWS)` | 该方向地平线的天空颜色 = 雾色（线性）。`dirWS` 单位向量，从相机指向像素 |
| `float LanbaiFogAmount(float3 posWS, float3 camPosWS)` | 0..1。指数雾，带 `_FogCap` 封顶与 `_FogHeightFalloff` 高度衰减 |
| `float3 LanbaiApplyFog(float3 colLinear, float3 posWS)` | 用 `LanbaiCentreEyePos()`（两眼中点）：两只眼看到的雾一样 |
| `LanbaiFogAmountEx(pos, cam, density, cap, heightScale)` | 每个参数都显式给 |
| `LanbaiApplyFogAdditive(col, posWS)` | 加法 pass：只衰减 |
| `LanbaiApplyFogEx(col, posWS, extraAir)` | 雾色上再加一项“空气” |
| `float4 LanbaiFogVertex(posWS)` | 逐顶点：rgb 雾色、a 雾量 |
| `LanbaiFogDensity()` | 这一帧的密度：`_Udon_Fog`（w > 0）→ 旧的 `_Udon_FogDensity`（> 0）→ RenderSettings |
| `LanbaiSunDir(fb)`、`LanbaiSkyMoonDir(fb)`、`LanbaiDisc(...)`、`LanbaiOtherSkyDir(V)`、`LanbaiOtherSkyWeight(V, seam)`、`LanbaiGalaxyUV(V)`、`LanbaiSkyObjectAtten(d, a)` | 天上东西用的小函数（`LanbaiSky.cginc`） |

- **距离按径向算**（眼睛到点），Unity 内置雾用的是视深：密度、颜色相同，但这里转头雾不变（VR 里该这样）；90° 视场的四角，径向比视深最多长约 1.7 倍。
- **高度衰减**：密度 = d·exp(−max(y − 基准, 0) / H)，H = `_FogHeightFalloff`（米，0 = 不衰减），沿视线解析积分。**基准请驱动写 `_Udon_FogBase.x`**（地面世界 = 地面高度，第 4 幕 = 云顶 `_Udon_CloudTop.x`）；没写时用眼睛高度（站起来差 0.3 m，H 在几百米时可忽略）。
- **封顶**：f = min(f, `_FogCap`)；材质没这个属性（读到 0）就当作 1。门的 `_FogCap` 是“距离门控的封顶”（1.3–1.7 km 之外才起作用，再 × 高度衰减），这里是“处处封顶”；门的触手不走这里，所以两者不冲突。
- **水下**（`_Udon_Underwater` > 0）：封顶和高度衰减按同一权重关掉（水是均匀的）。
- **开销**：`LanbaiApplyFog` 每像素约 200 次标量运算、约 10 个超越函数（模型 A 或 B 只算一个，立方图 / 水下 / 混合都在 `[branch]` 里）；不透明一层约 0.15 ms @ 9 MP。叠很多层的透明请用 `LanbaiFogVertex`。

## 3. 雾色的模型（Udon 设全局量来选）

| 设了什么 | 模型 |
|---|---|
| 都没设 | `unity_FogColor`（RenderSettings 的雾色） |
| 只设了 `_Udon_FogBandColor`（a > 0）**或** `_Udon_TearPos`（w > 0，门的驱动一定写） | **A，门的默认值**：= `LanbaiGateSky.cginc` 的 `LanbaiBand()`，同一套算术、同一组数 |
| `_Udon_FogModel.x`（w > 0） | **A 与 B 的混合**，0 = A「光带」，1 = B「渐变」，**连续**：两幕之间换模型可以 2–6 秒交叉（圣经 §1.6）；交叉的那几秒每像素算两份 |
| `_Udon_FogModel` 没设 | `_Udon_HorizonColor.a = 2` 选 B（v1 的写法，兼容） |
| `_Udon_FogCubeParams.x > 0` | 往预先调色、模糊过的天空立方图 `_Udon_FogCube` 混（`蓝白/Sky/Bake Fog Cube From Skybox`） |
| `_Udon_Underwater > 0`（海写） | 水下：按视线的 y 在 `_Udon_WaterFogMid` → `Up` / `Down` 之间 smoothstep，权重 = `_Udon_Underwater` |

- **A「光带」**：朝 `_Udon_FogBandDir` 的一条带（近色 → 远色，过了带宽 + 10° 是虚空色），某个仰角以上是虚空色；背后带；地平线以下变暗、去饱和。用在 4（门）。
- **B「渐变」**：地平线色从朝向（近色）到背向（远色），往上过渡到天顶色，往下过渡到天底色，没有方位截断。用在 1/2/11/12、3、6、8、8b。

全局量（线性颜色，Udon 用 `VRCShader.SetGlobalVector`，**不要用 `SetGlobalColor`**）：

| 全局量 | 含义 |
|---|---|
| `_Udon_Fog` **（v1.1 新，推荐）** | x = 密度（每米），**w > 0 = 设了**：x 淡到 0 就是真的没有雾，不会跳回 RenderSettings |
| `_Udon_FogDensity`（已登记，旧） | 密度；> 0 = 设了（淡到 0 的最后一帧会跳回 RenderSettings 的密度：请改用 `_Udon_Fog`） |
| `_Udon_FogModel` **（v1.1 新）** | x = 模型混合 0（A）..1（B）；w > 0 = 设了 |
| `_Udon_FogBandDir`（已登记） | xyz 朝向（裂口 / 月 / 日）；长度 < 0.5 = 没设（门：朝裂口） |
| `_Udon_FogBandColor`（已登记） | rgb 朝向一侧的地平线色；a > 0 = 设了 |
| `_Udon_FogBandWidth`（已登记） | 近色 → 远色的方位宽度（度）；门 50 |
| `_Udon_HorizonColor`（预留） | rgb 背向一侧的地平线色；a > 0 = 设了（a = 2 是 v1 的“选 B”） |
| `_Udon_ZenithColor`（预留） | rgb 虚空 / 天顶色；第 9 幕 = 当前的星空底（镜子读） |
| `_Udon_NadirColor`（新） | rgb 天底色（B）；a > 0 = 设了 |
| `_Udon_FogShape`（新） | x 满的仰角、y 没了的仰角（> 0 = 设了）、z 幂、w 背后带增益（A） |
| `_Udon_FogBelow`（新） | x 起的仰角（< 0 = 设了）、y 止的仰角、z（A 最暗系数 / B 天底过渡的幂）、w 去饱和（A） |
| `_Udon_FogCube` + `_Udon_FogCubeParams`（新） | x 权重、y mip、z 取样最高仰角、w 曝光 |
| `_Udon_FogBase`（新） | x 高度衰减的基准高度；w > 0 = 设了 |
| `_Udon_Underwater`、`_Udon_WaterFogUp/Mid/Down`（海，已登记） | 水下组 |
| `_Udon_SunDir` / `_Udon_SunDisc`、`_Udon_MoonDir` / `_Udon_MoonDisc` | 日、月（`README_Sky.md` §2） |

**交接规则**：全局量不会自己清零，前一幕写的值会一直留着。**每个驱动在自己时间窗的开头把它用的这一组全部写一遍**（含 `.a / .w` 开关），淡变时只动 rgb / x，开关一直是 1。

**每一幕填哪几个数：`Sky/FogPresets.json`**（第 4 幕那一组 = 门的默认值；另有全片雾的过渡时刻表，按圣经 §6.x），天空的那一部分在 `Sky/SkyPresets.json`；U# `Sky/Runtime/LanbaiSkyPreset.cs` 按预设写整组。

## 4. 每个全局量自己一个保护宏

`LanbaiSky.cginc` / `LanbaiFog.cginc` / `LanbaiSkyLayers.cginc` 里的每个 `_Udon_` 声明都包在 `#ifndef LANBAI_DECL_<名字>` 里（例如 `LANBAI_DECL__Udon_TearPos`），声明后定义它。所以：
- 自己声明了某个全局量的 shader：在 include 之前写 `float4 _Udon_TearPos;` 和 `#define LANBAI_DECL__Udon_TearPos`。
- 材质参数：`LANBAI_FOG_OWN_CAP`、`LANBAI_FOG_OWN_HEIGHT`、`LANBAI_FOG_OWN_DENSITY`（旧的 `_Udon_FogDensity`）各管一个；`LANBAI_FOG_OWN_UNIFORMS` = 三个都自己来。
- 总工程师提议的全片 `Common/Shaders/LanbaiGlobals.cginc`（每个登记的全局量声明一次）定下来以后，这些声明挪过去，宏名照用。

## 5. 和门的关系（第 4 幕）

- **算出来一样**：`Sky/Tools~/compile_check/check_gate_equivalence.py` 把仓库里原样的 `LanbaiGateSky.cginc` 和 `LanbaiSky.cginc` 一起用 slang 编成 CPU 程序，在 2 万个方向、4 个眼位、两种情况上比 `LanbaiBand(V)` 与 `LanbaiHorizon(V)`：**最大差 1.2 × 10⁻⁷**。前提：门的材质用 shader 默认值，第 4 幕里 `_Udon_FogBandColor` 或 `_Udon_TearPos` 被写过。
- **include 顺序**：门的 GateSky 对它的全局量没有保护。两个都要用的 shader：**先 include `LanbaiGateSky.cginc`，再 include `LanbaiFog.cginc`**（反过来是重复声明，`tests/T_FogThenGate_ExpectFail.shader` 验证）。
- **TentacleSway**：它自己声明了 `_FogCap` 和 `_Udon_FogDensity`，没有 `_FogHeightFalloff`。要接 `LanbaiFog` 的话：GateSky 之后、把那两个声明挪到 include 之前、`#define LANBAI_FOG_OWN_CAP` 和 `#define LANBAI_FOG_OWN_DENSITY`（`tests/T_TentacleSwayCase.shader` 就是这个情况，slang 通过）。第 4 幕里两者相等，**维持现状也对**。

## 6. 检查怎么跑

```
python3.11 -m venv ~/bpy && ~/bpy/bin/pip install numpy slangpy
cd Sky/Tools~/compile_check
~/bpy/bin/python -I check_shaders.py tests ../../Shaders     # 每个 CGPROGRAM、关键字组合、SPS-I、FOG_EXP2 / LINEAR、ForwardAdd
~/bpy/bin/python -I check_gate_equivalence.py               # 门的光带 = LanbaiHorizon
./check_cs.sh                                               # C#（README_Sky.md §9）
```
slang 通过只说明 HLSL 写得对、类型对。**请本地在 Unity 2022.3 里编译一次**，Console 原样推回来。

## 7. v1 → v1.1 改了什么（总工程师第 1 轮意见 `Sky/总工程师意见.md`）

| 意见 | 改了 |
|---|---|
| 必须 1：一个宏藏三个名字 | 拆成 `LANBAI_FOG_OWN_CAP / _HEIGHT / _DENSITY`，旧宏 = 三个都；测试 `T_OwnCapOnly`、`T_TentacleSwayCase`、`T_OwnAllThree` |
| 必须 2：共用全局量只防了门一家 | 每个 `_Udon_` 名字自己一个 `LANBAI_DECL_<名字>` 保护（§4）；`T_OwnAllThree` 里先声明 `_Udon_TearPos` 再 include |
| 必须 3：密度“值兼作开关”，淡到 0 会跳 | 新 `_Udon_Fog`（x 密度、w 开关）；旧的保留兼容；README 写明淡变只动 rgb / x |
| 必须 4：模型 A/B 不能交叉 | 新 `_Udon_FogModel.x` 连续混合（平时 `[branch]` 只算一个） |
| 必须 5：表面着色器 ForwardAdd 多加雾色 | §1 的写法、`T_SurfaceFinalColor` 加了 ForwardAdd 变体 |
| 必须 6：本地要的数 | `Sky/FogPresets.json`（每幕一组 + 过渡时刻表）、`Sky/SkyPresets.json` |
| 建议：第 4 幕的触发 | `_Udon_TearPos.w > 0` 也当作第 4 幕 |
| 建议：月晕 | `LanbaiApplyFogEx(col, pos, extraAir)` |
| 建议：高度基准 | README 要求驱动写 `_Udon_FogBase`；对照写在 §2 |
| 建议：性能 | `[branch]`、`LanbaiFogVertex`、开销写进 §2 |
| 建议：模型 A 除零 | smoothstep 两端加了防护 |
| 建议：`SetGlobalVector`、交接规则、径向距离 | §3、§2 |
| 建议：检查脚本 | 注释里的 include 不展开；加 SPS-I、FOG_EXP2 / LINEAR、ForwardAdd 变体 |
| 小事：带的方向用每只眼的相机 | 改成两眼中点 |
| 海：水下雾两套机制 | 按海的接口原样加（`_Udon_Underwater` 等已在 main 登记），没有另开模型 B 的一组：海的驱动只管它自己的四个量 |
