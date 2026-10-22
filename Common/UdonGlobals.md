# `_Udon_` 全局量登记表

VRChat 只允许 Udon 写 `_Udon_` 前缀的全局 shader 量（`VRCShader.SetGlobal*`）。全片共用一个命名空间，所以**新加之前先在这里登记**（写进你的 `给总控.md`，总控来改这一页），名字撞了就改名。
“写的人”= 哪个驱动每帧写它；“读的”= 哪些 shader 读它。2026-10-22 从仓库里扫出来的现状。

## 已经在用的

| 全局量 | 类型 / 含义 | 写的人 | 读的 |
|---|---|---|---|
| `_Udon_T` | 时间轴秒（部分 shader 用作动画时钟） | 时间轴 | Gate、Tear、Tentacles |
| `_Udon_GateTime` | 门里的时间轴秒 | 门驱动 | Gate |
| `_Udon_GateOrigin` | xyz = GateRoot 本帧世界位置（云海坐标的原点） | 门驱动 | Gate、Tear、Tentacles |
| `_Udon_CloudTop` | x = 门的云顶世界 y（= −h_bus(t)） | 门驱动 | Gate、Tear |
| `_Udon_TearPos` / `_Udon_TearH` / `_Udon_TearFoot` / `_Udon_TearTop` | 裂口位置、高度、脚（w = 白的半宽）、顶 | 门驱动 | Gate、Tear、Tentacles |
| `_Udon_TearOpen` / `_Udon_RipProgress` / `_Udon_TearHide` / `_Udon_TearBreath` | 裂口张开、撕裂进度、隐藏、呼吸 | 门驱动 | Tear |
| `_Udon_MoonDir` / `_Udon_MoonDisc` | 指向月的单位向量；月盘增益 | 门驱动（第 3–4 幕；之后归天空） | Gate、Tentacles |
| `_Udon_MultReveal` | 群臂两组显现 | 门驱动 | Gate |
| `_Udon_FogBandDir` / `_Udon_FogBandColor` / `_Udon_FogBandWidth` / `_Udon_FogDensity` | 光雾带（`LanbaiHorizon` 的参数，圣经 §1.6） | 当前幕的驱动（第 4 幕 = 门） | Gate、Tentacles；**以后所有 `LanbaiFog` 用户** |
| `_Udon_Wetness` | 湿润 0–1（Lagarde） | 时间轴 | Rain |
| `_Udon_RainAmount` / `_Udon_RainFall` / `_Udon_FlowDir` / `_Udon_FlowDirB` / `_Udon_FlowMix` / `_Udon_RunClock` / `_Udon_RunStretch` / `_Udon_StopOffset` / `_Udon_Drip0..3` / `_Udon_OneDropA/B` | 雨套件 | 雨驱动 | Rain |
| `_Udon_Wiper*`（Time、Pivot0/1、Axis0/1、Rest0/1） | 雨刮 | 雨驱动 | Rain |
| `_Udon_Lamp0..7`、`_Udon_LampColor0..7`、`_Udon_LampDir0..7`、`_Udon_LampAxis0..7` | 解析 GGX 灯（最多 8 盏） | 当前幕的驱动 | Rain；海、宫殿、路灯都用这一套 |
| `_Udon_ReflCube` / `_Udon_ReflCube_HDR` / `_Udon_ReflExposure` | 每幕烘好的反射立方图 | 当前幕的驱动 | Rain；海、星海、暮的天花 |
| `_Udon_CabinLightmap` / `_Udon_CabinAmbient` / `_Udon_CabinBleach` / `_Udon_CabinFade` | 车厢管灯、环境色、漂白、侵蚀（圣经 §4.8） | 时间轴 / 车厢驱动 | 车厢 shader（总控在做）、Rain |
| `_Udon_CaseLight` | 公告箱纸的发光 | 第 12 幕 | Rain |
| `_Udon_Caustics` | 水下焦散强度 / 方向（圣经 §4.8） | 海驱动 | 车厢、海 |
| `_Udon_WorldS` | （本地的时间轴里用的，含义见 `FromLocal/code/timeline_v1/`） | 本地 | 本地 |

## 预留（还没人写，先占名字）

| 全局量 | 预定含义 | 归谁 |
|---|---|---|
| `_Udon_SunDir` / `_Udon_SunDisc` | 指向日的单位向量；日盘增益 | 天空 |
| `_Udon_SkyBlend` | `Lanbai/Sky` 两张立方图的混合 | 天空 |
| `_Udon_HorizonColor` / `_Udon_ZenithColor` | 地平线 / 天顶色（`LanbaiHorizon` 的底色） | 天空 |
| `_Udon_StarGain` / `_Udon_GalaxyGain` | 星点、银河辉光的增益（第 9 幕的点燃线 g(t)） | 天空 |
| `_Udon_SeaLevel` / `_Udon_SeaMode` | 海面世界 y；ABOVE / BELOW / CEILING | 海 |
| `_Udon_MirrorIndex` / `_Udon_MirrorPhase` | 第几面镜、穿越进度 | 门内（镜子） |
| `_Udon_OverlayColor` / `_Udon_OverlayAlpha` | 遮罩球填色、alpha | 门内（`Lanbai_Overlay` v2） |
