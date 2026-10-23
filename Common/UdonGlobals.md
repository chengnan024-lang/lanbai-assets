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
| `_Udon_CabinLightmap` / `_Udon_CabinAmbient` / `_Udon_CabinBleach` / `_Udon_CabinFade` | 车厢管灯（float）、环境色（float4，rgb 线性）、漂白（float 0–1）、侵蚀（float 0–1）（圣经 §4.8） | 时间轴 / 车厢驱动 | 车厢 shader（总控在做）、Rain |
| `_Udon_CaseLight` | 公告箱纸的发光 | 第 12 幕 | Rain |
| `_Udon_Caustics` | float4：x 强度 0..1（已含深度衰减）、y 方向 +1 从上 / −1 从下（7c）、z 焦散的钟（秒）、w 平铺缩放（定义见 `Sea/README_Sea接口.md` §3） | 海驱动 | 车厢、海 |
| `_Udon_CausticsColor` / `_Udon_CausticsTex` | 焦散的线性颜色 × E（float4）；焦散序列帧图集（全局纹理，`sampler2D`） | 海驱动 | 车厢、海 |
| `_Udon_SeaLevel` / `_Udon_SeaMode` | 当前海面世界 y；0 无、1 ABOVE、2 BELOW、3 CEILING、4 BELOW 翻转（7c） | 当前幕（6、8 = 云；7 = 海） | 海、车厢 |
| `_Udon_SeaClock` | float4：x 浪的钟、yz 海水相对车的平移（世界 xz）、w > 0 已设 | 当前幕 | 海 |
| `_Udon_Underwater` | 0..1：眼睛在水里 | 海 | `LanbaiFog`、海、车厢玻璃 |
| `_Udon_WaterFogUp` / `_Udon_WaterFogMid` / `_Udon_WaterFogDown` | 水下雾色（朝上 / 水平 / 朝下，线性） | 海 | `LanbaiFog` |
| `_Udon_MirrorPlane` | float4：x 当前镜面在车正下方的世界 y、y 镜线强度 0–1、z 镜序号 1–13（0 无）、w 穿越进度 −1…1 | 镜子驱动 | 车厢、`Lanbai/BronzeMirror`、星尘 |
| `_Udon_MirrorRimLight` | float4：xyz 最近镜缘点世界位置、w 目标照度 E（0–0.3，8000 K） | 镜子驱动 | 车厢 / 头像补光 |
| `_Udon_OverlayColor` | rgb 填色 × 2^(−ΔEV)，a FLAT 模式的 alpha | `LanbaiOverlay`（由当时拥有遮罩的幕调用） | `Lanbai/Overlay` |
| `_Udon_OverlayCurve` / `_Udon_OverlayLum` | 曲线（tau、T、模式、呼吸）；(Lfrom, Lto, Lscene, Lover) | 同上 | 同上 |
| `_Udon_OverlayLobe0..3` / `_Udon_OverlayLead` / `_Udon_OverlayLeadElse` | 方向领先瓣（方向、半角）；各瓣领先秒数；其余方向领先与软边 | 同上 | 同上 |
| `_Udon_InsidePortal` | float4：x 裂口平面世界 z，y = 1 门户生效 | 门内驱动 | 门内 shader、**门的 shader / 驱动** |
| `_Udon_InsideDot` / `_Udon_InsideFibre` / `_Udon_InsideClock` / `_Udon_InsideFog` | 全部 float4：暖白点（核心直径°、辉光直径°、增益）；纤维填色（rgb）+ 增益（a）；丝线时钟（x）；当前区雾色（rgb）+ 密度（a） | 门内驱动 | `Lanbai/InsideLip` 等 |
| `_Udon_CabinSlice` / `_Udon_CabinSliceColor` | 都是 float4：车厢穿越光带（x 前沿的车坐标 z、y 软边 m、z 指数拖尾长度 m、w 覆盖 0–1）；rgb 颜色 × E、a 窗形遮罩权重 | 门内驱动（第 9 幕镜子也用） | `Lanbai/Cabin` |
| `_Udon_RadioDial` | float4：rgb 收音机表盘发光填值（线性） | 时间轴 / 门内驱动（4c、5） | `Lanbai/Cabin` |
| `_Udon_SkyBlend` | float4：x 立方图 A → B、y 程序化权重、z 夜的权重（按方向延迟）、w > 0 已设 | 当前幕（6、8 = 云；9 = 天空） | `Lanbai/Sky` |
| `_Udon_SkyFx` | float4：x 另一片天、y 地平线带 1 的增益、z 日线半长（度）、w > 0 已设 | 同上 | `Lanbai/Sky` |
| `_Udon_SunDir` / `_Udon_SunDisc` | 指向日的单位向量（w > 0 已设）；x 增益、y 半径（度）、z 日线半长（度）、w > 0 已设 | 6、8 幕的驱动 | `Lanbai/Sky`、海 |
| `_Udon_HorizonColor` / `_Udon_ZenithColor` | 地平线 / 天顶色（`LanbaiHorizon` 的底色）；第 9 幕的 `_Udon_ZenithColor` = 星空底 | 当前幕 | `LanbaiFog`、`Lanbai/Sky`、镜子 |
| `_Udon_GalaxyGain` | float4：x 银河辉光 + 星空底的增益（含点燃线 g(t)）、w > 0 已设 | 第 9 幕（天空） | `Lanbai/Sky`、镜子 |
| `_Udon_StarGain` | float4：x 星点总增益、y 亮星加成、z 亮星个数、w > 0 已设 | 第 9 幕（天空） | `Lanbai/StarPoints`、镜子 |
| `_Udon_Fog` / `_Udon_FogBase` | float4：x 指数雾密度 / m、w > 0 已设（x = 0 真的是无雾）；x 高度衰减的基准世界高度、w > 0 已设 | 当前幕 | `LanbaiFog` |
| `_Udon_NadirColor` / `_Udon_FogShape` / `_Udon_FogBelow` / `_Udon_FogModel` | 天底色（模型 B）；带 / 地平线满和消失的仰角、幂、背带增益；地平线以下的暗化；A 带 ↔ B 渐变的混合（定义见 `Sky/README_Fog接口.md`） | 当前幕 | `LanbaiSky` / `LanbaiFog` |
| `_Udon_FogCube` / `_Udon_FogCubeParams` | 预染色、预模糊的雾立方图（`samplerCUBE`，线性 HDR）；权重、mip、最大仰角、曝光 | 当前幕 | `LanbaiSky` |
| `_Udon_SeaBus` / `_Udon_SeaBusVel` | float4：车的原点在水的坐标系里的位置（x、−深度、前进的路），w > 0 已设；它的速度 m/s | 第 7 幕驱动（海） | `Lanbai/SeaParticles`（海雪、播下的光、船体荧光） |
| `_Udon_SkySpot` | float4：x 天窗光斑的亮度包络 0..1（U8 → ≈169.2 从 −5 EV 按 EV 线性升到 1，→ U9 平滑降到 0.6，U9 → U9 + 0.25 s 到 0），yzw 不用（D-16） | `LanbaiSkylightSpot`（门内） | `Lanbai/SkylightSpot` |
| `_Udon_InsideGrade` | float4：rgb 第 4 → 4c 交叉淡化期间布的填色乘数，a > 0 有效（没人写时当 1）（D-16，预留） | 门内驱动 | `Lanbai/InsideLip` |
| `_Udon_PalaceVeil` | 从台地下方罩住宫殿建筑的雾（第 7b 幕 F7p；定义见 `Act07_Sea/PalaceFrame_约定.json`）（D-17） | 第 7 幕驱动（海） | 宫殿 shader |
| `_Udon_SkyGlobals` / `_Udon_Sky_*`（一族，约 45 个） / `_Udon_SkyCubeTexA` / `_Udon_SkyCubeTexB` | 一个天空材质，各预设的差别全走全局量；`_Udon_Sky_<材质属性名>`；两张全局立方图（定义见 `Sky/README`）（D-18） | 天空预设 / `LanbaiSkyDriver` | `Lanbai/Sky` |
| `_Udon_StarShape` | float4：x 最暗星等、y 雾带内的 EV、z 带半宽（D-18） | 天空预设 | `Lanbai/StarPoints` |
| `_Udon_WorldS` | （本地的时间轴里用的，含义见 `FromLocal/code/timeline_v1/`） | 本地 | 本地 |

## 预留（还没人写，先占名字）

（目前没有。）
