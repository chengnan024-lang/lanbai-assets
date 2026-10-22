# 触手之门 · 云套件 GateClouds v1（云海、云塔、远云、地平线云团、越远越宽的光束、阴影楔）

写的人：云端（这次是新开的云端会话，接着 10-08 那条日志做）。对象：小楠电脑上 Unity 2022.3 那一侧的会话。日期：2026-10-22。
**这里的 shader 和 C# 都没有在 Unity 里编译过。** shader 用 slangc 2025.6 做过语法 / 类型检查（`Tools~/slang_check.py`，三个 shader 的顶点和片元都过了）；C# 没有编译检查。第一次在 Unity 里跑，请把 Console 原样推到 `FromLocal/`。

10-08 的门导入测试说：门在 Unity 里基本还原了定稿，看不到的那部分是**我们漏交了云**。这个套件就是补这一块：

| 门导入测试里缺的 | 这一版 |
|---|---|
| 云海：JSON 里没有布局，地平线以下是一片平的灰雾 | **`Lanbai/GateCloudDeck`**：一张平铺在云下的大四边形，每个像素对一个"云顶高度场"做体积步进：背光的暗云头、云头轮廓上的银边、朝月一侧的月光路、远处化进光雾带。写入深度，触手的根、裂口的脚、云卡都和云头正确地前后遮挡。 |
| 云塔 9 张、远云 4 张、雾卡 2 张、地平线云团 22 张："卡在 LanbaiFog 里、yaw 公告板、下沉 / 塌陷"没有对应的 shader | **`Lanbai/GateCloudCard`** + **门专用云卡 v2**（5 种形状，Blender 体积渲染，月光从云后低角度照来，场景线性，光照分通道存）。37 张卡按 `GateLayout_v2.json` 原来的位置摆。云塔的塌陷、下沉、最后 2 秒淡出由 `LanbaiGateClouds`（U#）按时间驱动。 |
| 光束卡是等宽的，`widen 3.2` 做不到 | **`Lanbai/GateBeam`**：从伤口出发、越远越宽的柔光瓣。 |
| 阴影楔 4 道：没有 shader 和网格 | 同一个 `Lanbai/GateBeam`，乘法模式（`dst × (1 − a)`）。 |
| 远潮的雾带参数是旧的 | `GateClouds_Layout.json` 的 `tide_material` 给了值（§6）。 |
| 峡谷的 3 张卡没有网格 | **这一版没做**（§9）。 |

---

## 0. 先看图

`Docs~/` 里是用 `Source/preview_gate.py` 合成的整帧预览：**云海 + 云卡 + 光束按 Unity shader 的同一套算法算出来**，再用调色套件的 PPv2 S4 引擎模型调色（`Grading/Tools~/engine/ppv2_engine.py`）。触手和裂口不是我们算的，是从本地 10-08 的 Unity 截图里贴回去的（只贴非天空、非平雾的像素）。

| 文件 | 是什么 |
|---|---|
| `Docs~/compare_key.png` | keyart 机位 t = 154.50：上 = 这一版的预览，下 = 定稿 `Gate/Renders/keyart_239.png` |
| `Docs~/compare_U7.png`、`compare_U8fwd.png`、`compare_U8side.png`、`compare_rear.png` | 其他机位，同样左右 / 上下对比 |
| `Docs~/deck_only_*.png` | 只有云海（没有卡、没有光束），看云海本身 |
| `Docs~/cards_contact.png` | 5 张云卡的三个光照通道 |

---

## 1. 交付清单（拷进 Unity 的是整个 `GateClouds/`）

拷到 `Assets/Lanbai/GateClouds/`（和 `Assets/Lanbai/Gate/` 平级：两个云 shader 用 `#include "../../Gate/Shaders/LanbaiGateSky.cginc"`，和天空盒、触手共用**同一份**天空 / 雾色定义）。`Source/`、`Tools~/`、`Docs~/` 带 `~` 或是 Python，Unity 不会编译它们（`Source/` 里只有 .py，也可以不拷）。

| 文件 | 是什么 |
|---|---|
| `GateClouds_Layout.json` | **唯一的数据源**：云海四边形、37 张卡（位置 = `GateLayout_v2.json` 的 GateRoot 坐标、尺寸、透明度、增益、镜像、队列、化开、云塔的塌陷 / 下沉 / 淡出关键帧）、2 束光 + 4 道阴影楔、远潮材质值。由 `Source/gate_clouds_layout.py` 从 `GateLayout_v2.json` 生成。 |
| `Shaders/Lanbai_GateCloudDeck.shader` | 云海（§3） |
| `Shaders/Lanbai_GateCloudCard.shader` | 云卡（§4） |
| `Shaders/Lanbai_GateBeam.shader` | 光束 / 阴影楔（§5） |
| `Textures/Deck_Detail_1024.png`、`Deck_Macro_512.png` | 云海的两张周期贴图（**线性数据，不是颜色**，§3.2） |
| `Textures/GateCard_{Congestus,Bank,Strato,Puff,Wisp}.png` | 门专用云卡 v2（§4.1） |
| `Textures/deck_tiles.json`、`gate_cards.json` | 贴图的量程、通道缩放、云底位置（生成器写的，shader 默认值和布局 JSON 已经用了它们） |
| `Editor/LanbaiGateCloudsBuilder.cs` | 菜单 **蓝白/Gate Clouds/Build**：设导入、建网格和材质（放在 `Generated/`）、在 GateRoot 下搭好全部物体、挂上驱动。可以重复运行。 |
| `Runtime/LanbaiGateClouds.cs` | U# 驱动：`Start` 写每张卡的 property block，`Apply()` 按时间让云塔塌陷、下沉、淡出。 |
| `Source/*.py` | 生成器和参照渲染（§8） |

---

## 2. 怎么搭（测试场景 `GateTest.unity` 里先做）

1. 拷 `GateClouds/` 到 `Assets/Lanbai/GateClouds/`。确认 `Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc` 在。
2. 打开搭好门的场景（要有 `GateRoot`，裂口根 `Tear_Root` 或 `Tear_Kit` 在它下面）。
3. 菜单 **蓝白/Gate Clouds/Build**（或脚本里 `LanbaiGateCloudsBuilder.Build()`）。它会：
   - 设贴图导入：云海两张 = sRGB 关、Repeat、mip、各向异性 16、**不压缩 RGBA32**（高度场压缩会出块）；云卡 = sRGB 开、Clamp、mip、BC7、Alpha Is Transparency。
   - 在 `GateRoot/GateClouds/` 下建 `Deck`、`Cards/<id>`（37 张）、`Wedges/<id>`（4 道），在裂口根下建 `GateBeam_Shaft_00/01`。
   - 挂 `LanbaiGateClouds` 并填好所有数组，然后按 U7b 预览一次。
4. 测试场景的 `LB_GateTest.Apply(t)` 里加一行 `LanbaiGateCloudsBuilder.Apply(t);`（编辑模式下预览云塔和卡的 property block；property block 不存进场景，Play / VRChat 里由 `LanbaiGateClouds.Start` 写）。
5. 正式场景：Director 每帧 `gateClouds.t = t; gateClouds.Apply();`（GateRoot 激活的那段）。

**U# 注意**：Build 用 `AddComponent<LanbaiGateClouds>()`，有 U# 时再 `CopyProxyToUdon`。如果 Inspector 里没出现对应的 Udon 程序（U# 版本差异），请手动 Add Component 一次、给它建程序资产，再跑 Build。

**不需要改的**：门、裂口、触手的任何文件；全局量还是 README_GateLayout §2.1 那一套（云海读 `_Udon_CloudTop`、`_Udon_GateOrigin`、`_Udon_MoonDir`、`_Udon_TearPos`）。**补光、月光、雾都不用改。**

---

## 3. 云海 `Lanbai/GateCloudDeck`

### 3.1 怎么画的

- **几何**：`GateRoot/GateClouds/Deck`，一张 32 km 的平四边形，在 GateRoot 本地 y = −176.6（云顶下 26.6 m，整个云层的最下面），跟着 GateRoot 走。四边形本身看不见，它只负责让"往下看的像素"跑片元。
- **每个像素**：从眼睛沿视线进云层，按**指数增长的步长**（每步 ×1.02 以上，所以竖直方向的步长处处差不多）找第一次钻到高度场下面的位置，再二分 5 次。
  - **高度场** = 宏观起伏（周期 6.4 km）+ 振幅 ×（积云头，周期 960 m）+ 菜花小鼓包（同一张图缩小 7 倍）。噪声都在**云海坐标** `worldPos − _Udon_GateOrigin` 里取，云海跟着门以 v_g 走。
  - **云面**：朝月的漫反射（贴图里烘好的 N·L）× 前面云头投下的影子（烘好的"到月亮要穿过多少米云"）+ 天光 × AO。朝月亮看，看到的是云头的背光面（暗）；从侧窗、后窗看，看到的是被月光照亮的银色一侧。
  - **云皮（银边）**：云头上方一层很薄的软云。视线**掠过云头、又离开**时，穿过这层皮，前向散射的月光（两瓣 HG，g = 0.8 / −0.18）就是那条银边。视线**落到**它要撞上的云顶时，那一段不算：定稿里是"暗的顶、亮的轮廓"，不是"亮的盖子"。
  - **雾**：`LanbaiGateFogColour`（光雾带 + 0.35 月晕），在撞上的距离 × `_FogDensity.y`（1.8）处混。
- **深度**：写 `SV_Depth`（撞上的那一点），所以触手的根、裂口脚、云卡、光束都按真实的云头前后遮挡。`Tear_CloudGlow(_Lit)` 还是照原来那样乘上去，光池不用改。
- **不让云头撞车**：离眼 150–400 m 以内，云头最高到眼下 6 m（`_MarchRange.w`）。U6 前车只在云顶上 40 m。

### 3.2 两张贴图（`Source/deck_tiles.py` 生成，月亮方向烘在里面）

月亮在门里不动（GateRoot 不转），所以"往月亮方向走要穿过多少云"和"朝月的 N·L"都可以预先烘好。
| 贴图 | R | G | B | A |
|---|---|---|---|---|
| `Deck_Detail_1024`（周期 960 m，0.94 m / 像素） | 高度 −12…44 m | 到月亮的云路径 0…160 m | 天空 AO | 朝月 N·L |
| `Deck_Macro_512`（周期 6.4 km） | 起伏 −12…12 m | 到月亮的云路径 0…400 m | 积云头的振幅 0.3…0.8 | 亮度起伏 0.75…1.15 |

### 3.3 能调的（材质上，默认值 = 我们定的）

| 想要 | 调 |
|---|---|
| 整体亮 / 暗 | `_Gain`；只调月光 `_MoonE`（0.38） |
| 银边更亮 / 更宽 | `_Skin.x`（密度 0.8）、`_Skin.y`（厚度 0.5 m） |
| 侧窗 / 后窗的云更亮 | `_Surf.z`（朝月漫反射 0.8） |
| 远处更快化进雾 | `_FogDensity.y`（1.8） |
| 云头更高 / 更平 | `_AmpRange.xy`（0.3, 0.8） |
| 省性能 | `_Steps`（120 → 64），`_StepK`（0.02 → 0.035）；远处会更早用平均云面 |
| 后窗视角 | 和天空盒一样，`_BackBand` 1.25 |

### 3.4 性能（参照渲染里数的，Unity 里请实测）

在 keyart、U7、U8 前方三个机位，平均每个往下看的像素走 **21–30 步**（p90 33–41），每步取 3 次贴图，加二分 5 次（各 3 次）；13% 的像素在 1.6 km 内没撞上，用远处的平均云面。没有 GrabPass、没有屏幕空间效果。**请在同一个测试场景里按 10-08 的方法量一次帧时间**（有 / 没有云海各一次），最好附上 GPU Profiler 里最贵的几项。如果 VR 估算超预算，先把 `_Steps` 降到 64、`_StepK` 提到 0.035 再量。

---

## 4. 云卡 `Lanbai/GateCloudCard` + 门专用云卡 v2

### 4.1 云卡 v2（`Source/gate_cards.py`，Blender 5.1 / Cycles 真体积，和 v1、定稿云海同一个形状生成器）

v1 云卡是给第 3 幕打的光（月在右前上方 26°），而且烘进了显示变换。门里月亮在云塔**后面**、只高 8°，而且每座云塔和月亮的夹角都不一样。所以 v2 是**场景线性**的，**光照分通道**：

| 通道 | 内容 |
|---|---|
| R | 月光从云后右侧 35° 照来（月亮差不多在云正后方：暗的云体、宽的银边） |
| G | 月光从云后右侧 70° 照来（月亮偏到一边：右侧被照亮） |
| B | 天光（地平线的光雾带、头顶的夜、下面被月光照亮的云海） |
| A | 覆盖率（直通 alpha） |

每个通道存的是 `sRGB(线性值 / 缩放)`，缩放在 `gate_cards.json`（材质 `_Scale`）。shader 按**这张卡的视线和月亮的水平夹角**在 R 和 G 之间插值（35° → R，70° → G），月亮在卡的左边时镜像（builder 按 U7b 的眼位算好，`_Mirror`）。颜色在 shader 里给：月光 `#D6E4FF × _MoonE`，天光 `_SkyColor × _SkyE`，然后进门的雾。

### 4.2 37 张卡（位置都是 `GateLayout_v2.json` 原来的）

| 组 | 张数 | 卡 | 队列 | 底部化开（云顶以上） |
|---|---|---|---|---|
| 云塔 `tower` | 9 | Congestus ×7、Bank ×2 | 3000 | −20 → +70 m |
| 远云 `far` | 4 | Congestus ×2、Bank ×2 | 2990 | −10 → +120 m |
| 地平线云团 `horizon` | 22 | Strato、Puff、Bank | 2990 | −10 → +120 m |
| 雾卡 `mist` | 2 | Wisp | 3000 | −10 → +50 m |

- yaw 公告板（竖直不转），朝**两眼中点**，两只眼看到同一张卡。
- 卡宽 = JSON 的 `width_m` 对应**云本身**的宽度（不是贴图宽），高度按贴图比例；底边（平云底）在 JSON 的位置上。
- 云塔：揭开后 25 s 塌到 0.72 高（底部不动），揭开后 6 s 起下沉 0.75 个塔高，最后 2 秒淡出、关 renderer（JSON `towers`，没改）。
- 透明度 = JSON `opacity`；远云和地平线云团的增益 0.6。
- 云海写了深度，所以卡的下半截被云头挡住，这就是"从云海里长出来"。`_SoftFade`（默认 0 = 关）：相机有深度图时可以开 20–40 m，交界更软。

---

## 5. 光束和阴影楔 `Lanbai/GateBeam`

- **光束**（2 束，挂裂口根，裂口物体空间，和 JSON 一样）：起点、轴、半宽 46.9 / 40.6、长 3437.5、**越远越宽 ×3.2**、强度 0.35 × (1.0 / 0.6)。横向一个柔光瓣，伤口端短淡入、往外 (1 − z)^1.3 淡出；顺着轴看时淡掉、离眼 60–460 m 淡入；颜色 = 裂口套件原来的光束填色 `(0.0362, 0.0343, 0.0873)`。加法，队列 2998。
- **阴影楔**（4 道，挂 GateRoot）：同一个 shader，`_Mode = 1`，`Blend Zero OneMinusSrcAlpha`，alpha 0.30–0.42，越远越宽 ×2.5。队列 2990（在光束和云卡之前，乘在光雾上）。
- 网格是 builder 生成的 33 行条带；朝眼睛转是 shader 做的。

---

## 6. 远潮的材质值（gate_test §2.2 第 10 条）

`Lanbai_TentacleTide_v2.shader` 还是 v2.2，自己算光雾带。请在 `M_TentacleTide_A / B` 上填和触手、天空一样的值：
`_HazeNear (0.1085, 0.1130, 0.1641)`、`_HazeFar (0.0436, 0.0504, 0.0726)`、`_BandEl (6, 22, 2)`。（它没有背带和地平线下的去饱和，远潮在方位 24–70°、地平线以上，影响很小。）

---

## 7. 请截图（推到 `FromLocal/gate_clouds_test/`）

和 10-08 同一个测试场景、同样的 HDR 截图方法：
1. keyart 机位 t = 154.50、U7 t = 155.10、U8 前方 t = 169.65、U8 侧窗 t = 166.45、后窗 t = 177.55（后窗时天空盒和云海的 `_BackBand` = 1.25）。
2. 每张配 `Docs~/compare_*.png` 里的定稿，量 `gate_metrics.py` 那几项（APL、亮度 < 12、上 25% L\* p90、最亮 2000 像素外框）。
3. 帧时间：有 / 没有 `GateClouds`（把 `GateRoot/GateClouds` 关掉）各一次，桌面 + VR 估算；GPU Profiler 最贵的几项。
4. Console 原样。
5. 头显里看一眼：云海的银边会不会闪（远处 1 px 的轮廓），两眼的云卡是否一致。

---

## 8. 源文件（都可以重跑）

| 文件 | 做什么 |
|---|---|
| `Source/deck_tiles.py` | 烘云海的两张贴图（numpy，约 40 秒） |
| `Source/deck_ref.py` | 云海 shader 的**逐行 numpy 移植**：同样的步进、LOD、光照、雾，从 `GateLayout_v2.json` 的任一机位渲，用 S4 引擎模型调色。改 shader 的数就改这里的 `DEFAULTS` |
| `Source/gate_cards.py` | 云卡 v2（Blender 5.1 bpy；3 个光组一次渲完，用降噪后的 Combined 按光组比例拆通道） |
| `Source/gate_clouds_layout.py` | 写 `GateClouds_Layout.json` |
| `Source/preview_gate.py` | 整帧预览（云海 + 卡 + 光束，可贴回 Unity 截图里的触手） |
| `Tools~/slang_check.py` | shader 的 slangc 语法 / 类型检查（`unity_stub.hlsl` 代替 UnityCG） |

---

## 9. 已知问题 / 还弱的地方（诚实版）

（见下文，随预览更新。）
