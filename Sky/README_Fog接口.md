# 天与雾的共用 include（`Common/Shaders/LanbaiFog.cginc`、`LanbaiSky.cginc`）· 接口说明 v1.1

> v1.1（10-23）：加海的水下参数组（`_Udon_Underwater`、`_Udon_WaterFogUp/Mid/Down`）、`LanbaiGalaxyUV()`；`_Udon_SunDisc.z` 改为日线半长。接口（三个函数的名字和参数）不变。

写的人：云端子会话「天空」，2026-10-22。**没在 Unity 里编译过**：只用 slang 查过语法和类型（`Sky/Tools~/compile_check/`），另外用 slang 在 CPU 上把门的 `LanbaiBand` 和这里的 `LanbaiHorizon` 逐方向算了一遍，结果相同（见 §4）。

## 1. 怎么用（给海、门内、门、车厢……所有自定义 shader）

```hlsl
#pragma multi_compile_fog
#include "Assets/Lanbai/Common/Shaders/LanbaiFog.cginc"     // 它自己会 include LanbaiSky.cginc 和 LanbaiVR.cginc
...
col.rgb = LanbaiApplyFog(col.rgb, i.worldPos);              // 线性颜色；不要再对同一个颜色用 UNITY_APPLY_FOG
```
材质上加两个属性（可以不加，不加就等于“不封顶、不做高度衰减”）：
```
_FogCap ("Fog Cap", Range(0, 1)) = 1
_FogHeightFalloff ("Fog Height Scale m (0 = none)", Float) = 0
```
- 叠加 / 预乘透明的 pass 用 `LanbaiApplyFogAdditive(col, posWS)`：雾只吃掉它的光，不往上加雾色。
- 表面着色器：`#pragma surface surf ... finalcolor:你的函数 nofog`，在 finalcolor 里调 `LanbaiApplyFog`。
- 天上的东西（日、月、星、远处灯点、裂口……圣经的 `_FogMode 2`）**不调雾**，用 `LanbaiSkyObjectAtten(dist, atten)` = exp(−d·atten)。

## 2. 接口（总控 §4 的最小接口，名字和参数不变；后面是加的）

| 函数 | 说明 |
|---|---|
| `float3 LanbaiHorizon(float3 dirWS)` | 该方向地平线的天空颜色 = 雾色（线性）。`dirWS` 单位向量，从相机指向像素 |
| `float LanbaiFogAmount(float3 posWS, float3 camPosWS)` | 0..1。指数雾，带 `_FogCap` 封顶与 `_FogHeightFalloff` 高度衰减 |
| `float3 LanbaiApplyFog(float3 colLinear, float3 posWS)` | 用 `LanbaiCentreEyePos()`（两眼中点）：两只眼看到的雾完全一样 |
| `float LanbaiFogAmountEx(pos, cam, density, cap, heightScale)` | 每个参数都显式给（门这种自带雾公式的 shader 可以只拿颜色） |
| `float3 LanbaiApplyFogAdditive(col, posWS)` | 叠加 pass 用 |
| `float LanbaiFogDensity()` | 这一帧的 Exp 密度：`_Udon_FogDensity` > 0 时用它，否则用 RenderSettings 的密度 |
| `float3 LanbaiSunDir(fallback)`、`LanbaiSkyMoonDir(fallback)` | `_Udon_SunDir` / `_Udon_MoonDir`（w > 0 才算设过） |
| `float LanbaiDisc(V, D, radiusDeg, softDeg, limbU)` | 日盘 / 月盘的形状（软边、临边昏暗） |
| `float3 LanbaiOtherSkyDir(V)`、`float LanbaiOtherSkyWeight(V, seamDeg)` | 第 8-ii 幕“另一片天”：下半球按 (−x, −y, z) 取样 |
| `float LanbaiSkyObjectAtten(dist, atten)` | 天上物体自己的距离衰减 |

**高度衰减**：密度 = d·exp(−max(y − 基准, 0) / H)，H = `_FogHeightFalloff`（米，0 = 不衰减），基准默认是眼睛自己的高度（全局 `_Udon_FogBase.x` 可以改），沿视线解析积分。所以水平方向和 Unity 内置的 Exp 雾完全一样，往上看的远处巨物雾少（“头清脚没”）。
**封顶**：f = min(f, `_FogCap`)；材质里没有这个属性（读到 0）就当作 1。

**什么都没设的时候**：密度 = RenderSettings、颜色 = `RenderSettings.fogColor`，也就是**和 Unity 内置雾一模一样**。所以这个 include 现在就可以放心接上，不会让任何一幕变样。

## 3. 雾色的三种模型（Udon 设全局量来选；这些全局量要先登记，见 `Sky/给总控.md`）

| 设了什么 | 模型 | 用在 |
|---|---|---|
| 都没设 | `unity_FogColor` | 默认 |
| 只设了 `_Udon_FogBandColor`（a > 0，门的驱动本来就写它） | **A，门的默认值**：= `Gate/Shaders/LanbaiGateSky.cginc` 的 `LanbaiBand()`，同一套算术、同一组数（`GateLayout_v2.json` `sky_band` 第 8 轮） | 第 4 幕 |
| `_Udon_HorizonColor.a = 1` | **A「光带」**：朝 `_Udon_FogBandDir` 的一条带（近色 → 远色），某个仰角以上是虚空色；背后带；地平线以下变暗、去饱和 | 3、4、4c、夜 |
| `_Udon_HorizonColor.a = 2` | **B「渐变」**：地平线色从朝向（近色）到背向（远色），往上过渡到天顶色，往下过渡到天底色；没有方位截断 | 晨、暮、蓝时、水下 |
| `_Udon_FogCubeParams.x > 0` | 叠加：往一张**预先调好色、模糊过的天空立方图**（`_Udon_FogCube`）混，权重 x | 有 HDRI 的幕（晨、暮）：雾色就等于物体背后的天（`蓝白/Sky/Bake Fog Cube From Skybox`） |
| `_Udon_Underwater > 0`（海写） | **水下参数组**（海的请求）：雾色按视线的 y 在 `_Udon_WaterFogMid` → `Up` / `Down` 之间 smoothstep，权重 = `_Udon_Underwater`；**水下时 `_FogCap` 和高度衰减不起作用**（水是均匀的） | 第 7 幕 |

全局量（线性颜色）：

| 全局量 | 含义 |
|---|---|
| `_Udon_FogBandDir`（已登记） | xyz 朝向（裂口 / 月 / 日）；长度 < 0.5 = 没设（门：朝裂口） |
| `_Udon_FogBandColor`（已登记） | rgb 朝向一侧的地平线色；a > 0 = 设了 |
| `_Udon_FogBandWidth`（已登记） | 近色 → 远色的方位宽度（度）；门 50 |
| `_Udon_HorizonColor`（预留给天空） | rgb 背向一侧的地平线色；**a = 模型**（1 光带 / 2 渐变） |
| `_Udon_ZenithColor`（预留给天空） | rgb 虚空 / 天顶色 |
| `_Udon_NadirColor`（新） | rgb 天底色（模型 B）；a > 0 = 设了 |
| `_Udon_FogShape`（新） | x 满的仰角、y 没了的仰角（> 0 = 设了）、z 幂、w 背后带增益（模型 A） |
| `_Udon_FogBelow`（新） | x 起的仰角（< 0 = 设了）、y 止的仰角、z 模型 A 最暗系数 / 模型 B 天底过渡的幂、w 地平线下去饱和（模型 A） |
| `_Udon_FogCube`（新，贴图）+ `_Udon_FogCubeParams`（新） | x 权重、y mip、z 取样的最高仰角、w 曝光乘数 |
| `_Udon_FogBase`（新） | x 高度衰减的基准高度；w > 0 = 设了 |
| `_Udon_FogDensity`（已登记） | Exp 密度；> 0 = 设了 |
| `_Udon_SunDir` / `_Udon_SunDisc`（预留给天空） | 日的方向；x 日盘增益、y 半径（度）、z 软边（度）；w > 0 = 设了 |
| `_Udon_MoonDir` / `_Udon_MoonDisc`（已登记） | 月（第 3–4 幕门写，之后天空写） |

每一幕的参数组在 `Sky/SkyPresets.json`（见 `Sky/README_Sky.md` §3），由那一幕的驱动写；U# 小组件 `Sky/Runtime/LanbaiSkyPreset.cs` 按预设写整组。

## 4. 和门的关系（第 4 幕）

- **算出来一样**：`Sky/Tools~/compile_check/check_gate_equivalence.py` 把仓库里原样的 `LanbaiGateSky.cginc` 和 `LanbaiSky.cginc` 一起用 slang 编成 CPU 程序，在 2 万个方向、4 个眼位、两种情况（只开门的默认值 / 门驱动写了光带的全局量）上比 `LanbaiBand(V)` 与 `LanbaiHorizon(V)`：**最大差 1.2 × 10⁻⁷**（浮点舍入）。前提是门的材质用 shader 默认值（门的测试就是这样），而且第 4 幕里 `_Udon_FogBandColor` 被写过（a > 0）。
- **include 的顺序**：`LanbaiGateSky.cginc` 里的 `_Udon_FogBand*`、`_Udon_TearPos`、`_Udon_TearH`、`_Udon_MoonDir`、`_Udon_MoonDisc` 没有保护。**两个都要用的 shader：先 include `LanbaiGateSky.cginc`，再 include `LanbaiFog.cginc`**（这边会跳过那几个声明）。反过来是“重复声明”的编译错误（`tests/T_FogThenGate_ExpectFail.shader` 专门验证了这一点）。
- 所以 `Lanbai_TentacleSway.shader` 里那行注释掉的 `// #include "LanbaiFog.cginc"`（写在 GateSky 之前）**不要照原样打开**：它会和 GateSky、和 TentacleSway 自己的 `_FogCap`、`_Udon_FogDensity` 重复声明。触手只在第 4 幕出现，第 4 幕里 `LanbaiBand` 就等于 `LanbaiHorizon`，所以触手**维持现状就对**。已写进 `给总控.md`。

## 5. 检查怎么跑

```
python3.11 -m venv ~/bpy && ~/bpy/bin/pip install numpy slangpy
cd Sky/Tools~/compile_check
~/bpy/bin/python -I check_shaders.py tests ../../Shaders     # 每个 CGPROGRAM、每种关键字组合
~/bpy/bin/python -I check_gate_equivalence.py               # 门的光带 = LanbaiHorizon
```
slang 通过只说明 HLSL 写得对、类型对，不说明 Unity 的 FXC / 表面着色器生成器一定接受。**请本地在 Unity 2022.3 里编译一次**，Console 原样推回来。
