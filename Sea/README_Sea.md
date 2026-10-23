# 海套件（`Sea/`）· 给 Unity 一侧的说明

写的人：云端子会话「海」。对象：本地（世界创建）和用海 shader 的几个会话（云：第 6、8 幕；灯与假醒：第 11 幕；海：第 7 幕）。
依据：圣经 v2.1 §6·6 / §6·7 / §6·8、§8.1 #7，`Art/总导演裁决.md` D-17。接口（属性、模式、全局量、谁摆什么）在 **`README_Sea接口.md`**，这一页讲怎么拷、怎么用、怎么验。
**本目录的 shader 和 C# 都没在 Unity 里编译过。** 检查见 §5。

---

## 0. 先做这三件事

1. **拷**：`Sea/` 整个拷到 `Assets/Lanbai/Sea/`；`Common/Shaders/LanbaiCaustics.cginc` 跟着 main 的 `Common/` 走（`Assets/Lanbai/Common/Shaders/`）。`Tools~`、`Docs~` 两个文件夹 Unity 不导入，拷了也没事。
   依赖：`Common/Shaders/LanbaiVR.cginc`、`LanbaiGlobals.cginc`、`LanbaiFog.cginc`（天空的）。
2. **点菜单 `蓝白/Sea/Create Materials`**：在 `Sea/Materials/` 建（或原地更新）7 个材质：`M_06_Sea`、`M_07a_SeaSurface`、`M_07c_SeaMirror`、`M_08_SeaCeiling`、`M_08_SeaCeilingEdge`、`M_08_SeaCeilingFade`、`M_11_SeaHanging`（渲染队列、混合、关键字都设好了）。贴图的导入设置由 `Editor/LanbaiSeaEditor.cs` 的 AssetPostprocessor 自动给（**只管 `Assets/Lanbai/Sea/`**）。
3. **截图推回来**（`FromLocal/sea_test/`）：一个空场景，相机放主座位 (0.55, 1.70, 2.05)、桌面 1920×1080、水平 90°，摆一块 `Sea_Disc.fbx`：
   - **A**（BELOW）：平面在眼睛上方 6.3 m，`M_07a_SeaSurface`，全局 `_Udon_ReflCube` 随便给一张天，相机仰 60°。对照 `Docs~/iterations/03_K2_r03/graded.png`。
   - **B**（ABOVE）：平面在眼睛下方 70 m，`M_06_Sea`，`_SunColor` 填日盘（`#FFCE9E @ +2.55` 的线性值），`_SunDir` 方位 +45° 仰角 6°，`_CalmAll 0.85`，相机俯 20°、右 30°。对照 `06_K1_r03fwd`。
   每张附：用的 PPv2 profile（S7a / S6）、Console 里海相关的报错原文。

---

## 1. 文件

| 路径 | 是什么 |
|---|---|
| `Shaders/Lanbai_Sea.shader` + `LanbaiSea.cginc` | 海本体：ABOVE（第 6 幕海镜）/ BELOW（第 7 幕斯涅尔之窗，`_AirSide −1` = 7c 车下倒置的窗）/ CEILING（第 8 幕海之天花、第 11 幕倒挂的海） |
| `Shaders/Lanbai_SeaDome.shader` | 水下的“天”：跟着眼睛的 1.8 km 球，颜色 = `LanbaiHorizon`（水下雾色），只在 `_Udon_Underwater > 0` 时画 |
| `Shaders/Lanbai_SeaWaterline.shader` | 车窗上的水线（入水向上升、出海向上流走）：放在车窗玻璃的复制网格上（队列 Transparent+20） |
| `Shaders/Lanbai_SeaShaft.shader` | 水下光柱（≤ 16 条，绕自身轴朝两眼中点，F4p 汇成一束） |
| `Shaders/Lanbai_SeaParticles.shader` | 海雪、播下的光、船体荧光、气泡：确定性的、t 的函数（没有 ParticleSystem，人人看到一样的） |
| `Shaders/Lanbai_SeaSpecks.shader` | 远处的灯点（四边形网格，≥ 1.4 px，第 8 幕天花里的金点最后走） |
| `Shaders/Lanbai_SeaCausticsCookie.shader` | 7a 水下太阳的焦散 cookie（Custom Render Texture） |
| `Shaders/LanbaiSeaGlobals.cginc` | 三个全局量的守卫声明（已登记；生成器补上以后这个文件自动不起作用） |
| `../Common/Shaders/LanbaiCaustics.cginc` | 焦散（车厢也用：`LanbaiCabinCaustics(posWS, nWS)`，见 `给总控.md` 第一批第 2 条） |
| `Textures/SeaN_Large_1024.png`、`SeaN_Small_1024.png` | 可平铺的 FFT 浪法线（64 m、9 m）。`sea_textures_meta.json` 里有每级 mip 被平均掉的斜率方差（shader 的 Toksvig 项） |
| `Textures/SeaMacro_512.png` | 平静 / 起纹宏遮罩（1.5 km） |
| `Textures/Caustics_8x8_2048.png` | 64 帧循环焦散（0.3 Hz 一圈）：真的把阳光折射过动的水面、在 2.2 m 深处收集光子算的 |
| `Textures/ShaftStreaks_256.png` | 光柱条纹 |
| `Textures/Cube_Dawn_256.exr`、`Cube_DuskLower_256.exr`、`Cube_Dusk_256.exr` | **备用**立方图（Syferfontein 两张 HDRI，6 面横条、D3D 面方向、BC6H）：正式的由总工程师的 `LanbaiReflectionBaker` 烘 |
| `Models/Sea_Disc.fbx` | r 40 km 的圆盘（中心密） |
| `Models/Sea_Dome.fbx` | 水下穹顶（真尺寸 r 1800 m：bounds 对） |
| `Models/Sea_Ceiling.fbx` | 天花：`Sea_Ceiling_Inner`（r ≤ 2.4 km，不透明）+ `Sea_Ceiling_Edge`（2.4–3.2 km，透明，2.7 km 处 50%、渐隐带 800 m） |
| `Editor/LanbaiSeaEditor.cs` | 导入设置 + 材质菜单 |
| `Tools~/` | `make_sea_textures.py`、`make_sea_assets.py`（贴图、网格、立方图的生成）、`sea_numpy.py`（**shader 的逐行 numpy 移植**，参考图用它）、`grade.py`、`k5_dissolve_ramps.py`、旧的 `compile_check/` |
| `Docs~/` | `lookdev_brief.md`、`lookdev/scene_kit.py`（标准台的场景脚本）、`iterations/`（20 轮）、`K5_dissolve_ramps.json`、评审稿 |

---

## 2. 几个要知道的做法

- **浪**：两张 FFT 法线滚动 + 宏遮罩；**远处的浪按屏幕导数折进粗糙度**（每张法线按自己的 mip 级查“已被平均掉的斜率方差”，加进 GGX α²）。所以第 6 幕 2.6 km 外的海不会变成闪烁的亮点，而是一条连续的闪光路。
- **第 6 幕倒影太阳**：解析 GGX 闪光，每个像素软封顶在日盘 × 2^−1.3（E14）；立方图采样封顶在 `_ReflClamp`（第 6 幕 2.4 = 日盘最大通道 × 0.41），立方图里的太阳在海里永远不会成为第二个日盘。
- **斯涅尔之窗（7a）有意偏离物理**（D-17 批准）：真实的晨天从水下看，窗的边（地平线）比中心亮；圣经要核心 `#E6F3F8`、边落到 L6。`_WindowGain 2.2`、`_WindowTint (1.35, 1.2, 1)`、`_WindowRadial (0.55, 1.3)` 是按**备用**立方图调的（`03_K2_r03`），**换成正式的 `ReflCube_Dawn` 以后按截图重校**（核心 `#E6F3F8`）。
- **7c 窗里的日弧**：物理上，地平线下 0.5° 的太阳被折射压在窗边不到一个像素、而且菲涅耳把它吃掉。圣经要它是最亮点、一道弧，所以加了 `_WindowSun*`：围着太阳方位 ±16°、折射后仰角 0…−22° 的一道金色弧，**替换**它下面的蓝（叠加会变成薰衣草紫）。7c 的数：`_WindowGain 0.2`、`_WindowTint (0.6, 0.9, 1)`、弧 `#FFB27A @ +2.74 × 0.82 × 4.5`（`12_K3_r13`）。
- **第 8 幕天花（D-17）**：镜带往金偏（`_MirrorTint (1, 1.2, 0.85)`，h_ab 39 → 62），再加 OKLab 的“紫色护栏”`_PurpleGuard`：色相落在紫带里的颜色色度压到 ≤ 0.02（≈ C\* 5）。仰 35°：紫 36% → **0%**（`18_K4_r06_35`）。另外天花材质要用 `LanbaiFog` 的高度衰减（约 120 m），否则暖色的雾会把头顶的深蓝水染紫（`给总控.md` 第三批第 1 条，请云设）。
- **天花溶化（K5）**：前沿 4 s 从地平线走到天顶，每个像素 5 s、亮度按 EV 线性（`_SkyBehindCube` 告诉 shader 后面那片天多亮）。逐像素核查（`Tools~/k5_dissolve_ramps.py`）：0.25 s 最坏 0.16 EV（≤ 0.5）、1 s 0.64（≤ 1.0）、2 s 1.27（≤ 1.8），**PASS**。宫灯金点同一像素里晚 30% 才开始走。

---

## 3. 参考图（`Docs~/iterations/`，标准台、PPv2 引擎模拟、主座位眼位 (0.55, 1.70, 2.05)、不带车壳）

| 帧 | 轮 | 定稿 | 量出的 |
|---|---|---|---|
| K2 斯涅尔之窗（F3 367.21，深 6.3 m，仰 60°，S7a） | 01–03 | `03_K2_r03` | 窗是最亮点；窗外暗镜 `#22 4A 71`（目标 `#11395E`，雾 0–15 m 让近窗的一圈亮一点）；紫 0% |
| K1 海镜（6d ≈ 350 s，离海 70 m，S6） | 04–06 | `06_K1_r03fwd` | 闪光路 ≤ 日盘 −1.3 EV；APL 161（**天是备用 HDRI 缩放的，偏亮不是海的问题**）；紫 0% |
| K3 倒置的窗（7c 897.96，俯 45°，S7b） | 07–12 | `12_K3_r13…` | 金弧在窗边、是最亮点；紫 1.3%（最大连通块 1.1%）；APL 45（雾和窗的增益决定，目标 30 是正前方的） |
| K4 海之天花（F9b 940.36，h 148 m，S8） | 13–19 | `18_K4_r06_35`、`19_K4_r07_0` | 仰 35°：APL 67、紫 0%；正前：紫 6%，**全在地平线以下的替身暮天里**（圣经天顶 `#3D4A80` 自己就是 h 289°，天空的事） |
| K5 溶化中（958.56，仰 35°，S8） | 20 | `20_K5_r01` | APL 78.7（目标 79）；紫 0% |

渲法：车外由 `sea_numpy.py` 对标准台相机的每个像素算好，贴在一张只给相机光线看的远卡上（`scene_kit.py`）。

---

## 4. 对评审意见的回应

- **总工程师第 1 轮（`总工程师意见.md`，接口 v1）**：8 条“必须改”全改（溶化 alpha 按亮度标量解、分母小时退回线性；灯点用四边形；入水 / 出海两块平面不并存；Toksvig 全程按屏幕导数；`_ReflClamp` 按日盘；天花拆内盘 / 外环；第 6、8 幕归云；焦散放 Common）。建议里：焦散有 `[branch]` 提前退出、`tex2Dgrad` 防 mip 缝；`_FogMode` 用圣经编号；`_SunDir` 在 shader 里 normalize；平移对 576 m 取模（驱动）；第 11 幕变体已加。没采纳的一条：**水下雾仍用 `_Udon_WaterFog*` 三色**（天空 v1.1 已经照这个读，不改成模型 B 的参数，免得两个会话都要改）。
- 美术 / 技术独立评审第 1 轮与陌生人测试：原稿 `Docs~/review_r1_art.md`、`review_r1_tech.md`、`review_r1_stranger.md`；**逐条回应 `Docs~/review_r1_response.md`**（技术 6 条必须改全改；美术逐帧改了第 2 轮帧 21–28）。

---

## 5. 检查

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Sea/Shaders Common/Shaders/LanbaiCaustics.cginc` → **`10 files, 82 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`**（用 main 的 `LanbaiFog.cginc`）
- C#：`bash Common/Tools~/compile_check/check_cs.sh Sea` → **`C# CHECK OK (0 assembly error(s), 0 lint warning(s))`**
- **没在 Unity 里编译过，没在头显里看过**（每个 shader 都要闭一只眼、再闭另一只各看一遍）。

---

## 6. 诚实的已知弱点

1. 参考图的天是替身（K1 缩放的 HDRI、K4 / K5 按圣经填值合成的暮天），云 / 天空交了真天以后要重渲；窗、镜带的几个调色参数是按替身调的。
2. 备用立方图没有云、没有云盖；面方向按 D3D 约定写，**没在 Unity 里核对**（导入后看一眼太阳是否在方位 +45°）。
3. 光柱、粒子、水线、穹顶、焦散 cookie 只过了编译检查，还没出参考图（它们是第 7a 包的事，会在那个包里出图）。
4. 焦散 cookie 用 Custom Render Texture 当平行光 cookie：Built-in / VRChat 里能不能用没验证；不行就退回 `Caustics_8x8_2048` 的一帧静态图。
5. K2 窗外暗镜比目标亮约 1 档（`#22 4A 71` 对 `#11395E`）：是 0–15 m 的雾色把近窗那一圈提亮的；按圣经两个目标都对，同时满足要在 7a 包里和雾一起再调。
6. 7c 的日弧、斯涅尔之窗的径向衰减都是为了追圣经画面的**非物理**参数（D-17 批准）。

## 7. 与评审的分歧

见 `Docs~/review_r1_response.md` 末节：APL 目标是正前方的（特写帧不可比）；替身天的数不归海；7c 窗缘留一点颤动是有意的。
