# 海套件（`Sea/`）· 给 Unity 一侧的说明

写的人：云端子会话「海」。对象：本地（世界创建）和用海 shader 的几个会话（云：第 6、8 幕；灯与假醒：第 11 幕；海：第 7 幕）。
依据：圣经 v2.1 §6·6 / §6·7 / §6·8、§8.1 #7，`Art/总导演裁决.md` D-12、D-17、D-18，总导演终审 `Sea/总导演终审.md`。接口（属性、模式、全局量、谁摆什么、每个材质的数）在 **`README_Sea接口.md`**，这一页讲怎么拷、怎么用、怎么验。
**本目录的 shader 和 C# 都没在 Unity 里编译过。** 检查见 §5。

---

## 0. 先做这三件事

1. **拷**：`Sea/` 整个拷到 `Assets/Lanbai/Sea/`；`Common/Shaders/LanbaiCaustics.cginc` 跟着 main 的 `Common/` 走（`Assets/Lanbai/Common/Shaders/`）。`Tools~`、`Docs~` 两个文件夹 Unity 不导入，拷了也没事。
   依赖：`Common/Shaders/LanbaiVR.cginc`、`LanbaiGlobals.cginc`、`LanbaiFog.cginc`。
2. **点菜单 `蓝白/Sea/Create Materials`**：读 `Sea/SeaMaterials.json`，在 `Sea/Materials/` 建（或原地更新）7 个材质：`M_06_Sea`、`M_07a_SeaSurface`、`M_07c_SeaMirror`、`M_08_SeaCeiling`、`M_08_SeaCeilingEdge`、`M_08_SeaCeilingFade`、`M_11_SeaHanging`。**每个数都是第 2 轮定稿、参考帧用的同一个数**（表在 `README_Sea接口.md` §2.0）。贴图的导入设置由 `Editor/LanbaiSeaEditor.cs` 的 AssetPostprocessor 自动给（**只管 `Assets/Lanbai/Sea/`**）。
3. **截图推回来**（`FromLocal/sea_test/`）。空场景，相机放主座位 (0.55, 1.70, 2.05)、桌面 1920×1080、水平 90°，**远裁剪 45 000 m**（圣经；空场景默认 1 000 m 会切掉远海），摆一块 `Sea_Disc.fbx`。全局量用菜单 **`蓝白/Sea/Preview Globals/A` 或 `B`** 一键设好（只在编辑器里；重新编译或进 Play 以后要再点一次，CONTROL §6.9）：
   - **A · 斯涅尔之窗（7a）**：平面在眼睛上方 **6.3 m**，材质 `M_07a_SeaSurface`，相机**仰 60°**，PPv2 profile **S7a**。点 `Preview Globals/A`：`_Udon_Underwater` 1、`_Udon_WaterFogUp/Mid/Down` = (0.0084, 0.0267, 0.0639) / `#77A0D2` = (0.184, 0.352, 0.644) / (0.0159, 0.0733, 0.1275)、`_Udon_Fog` = (0.040, 0, 0, 1)、`_Udon_FogBase` = 0、场景雾 Exponential 0.040。天空盒在水下看不见，不用管。对照 **`Docs~/iterations/29_K2_r06/graded.png`**（再仰到 90°：`30_K2_r06_up90`）。
   - **B · 海镜（6d）**：平面在眼睛下方 **70 m**，材质 `M_06_Sea`，相机**俯 10°、正前（方位 0）**，PPv2 profile **S6**。点 `Preview Globals/B`：`_Udon_ReflCube` = `Cube_Dawn_256`、`_Udon_ReflCube_HDR` = (1, 1, 0, 0)、`_Udon_SunDir` = 方位 +30°、仰角 +6°（D-12）、`_Udon_SunDisc.y` = 0.265°（D-18）、`_Udon_Fog` = (0.00012, 0, 0, 1)、场景雾 Exponential 0.00012 填 `#FFE4F0 @ +0.31`、主相机远裁剪 45 km。天空盒请换成 `Cube_Dawn_256`（不然上面三分之一是 Unity 默认的程序天）。对照 **`33_K1_r05fwd`**（俯 45° 的：`23_K1_r04`）。
   每张附：用的 PPv2 profile、Console 里海相关的报错原文。

---

## 1. 文件

| 路径 | 是什么 |
|---|---|
| `SeaMaterials.json` | **材质的数的唯一来源**（菜单和参考帧都读它） |
| `Shaders/Lanbai_Sea.shader` + `LanbaiSea.cginc` | 海本体：ABOVE（第 6 幕海镜）/ BELOW（第 7 幕斯涅尔之窗，`_AirSide −1` = 7c 车下倒置的窗）/ CEILING（第 8 幕海之天花、第 11 幕倒挂的海） |
| `Shaders/Lanbai_SeaDome.shader` | 水下的“天”：跟着眼睛的 1.8 km 球，颜色 = `LanbaiHorizon`（水下雾色），只在 `_Udon_Underwater > 0` 时画 |
| `Shaders/Lanbai_SeaWaterline.shader` | 车窗上的水线（入水向上升、出海向上流走）：放在车窗玻璃的复制网格上（队列 Transparent+20） |
| `Shaders/Lanbai_SeaShaft.shader` | 水下光柱（≤ 16 条，绕自身轴朝两眼中点，F4p 汇成一束）；`multi_compile_fog`，场景雾关时不吃雾（和 `Lanbai/Sea` 一致） |
| `Shaders/Lanbai_SeaParticles.shader` | 海雪、播下的光、船体荧光、气泡：确定性的、t 的函数（没有 ParticleSystem，人人看到一样的）；`multi_compile_fog`；**车厢里的座椅缝气泡材质队列设 3010**（在车厢玻璃 3000 之后，不被玻璃的染色 pass 染） |
| `Shaders/Lanbai_SeaSpecks.shader` | 远处的灯点（四边形网格，≥ 1.4 px）。第 8 幕天花里的金点：**队列 2995**、颜色 = 暗处的屏幕目标金 `#E0A860`、只按自己的进度最后走（接口 §2.6） |
| `Shaders/Lanbai_SeaCausticsCookie.shader` | 7a 水下太阳的焦散 cookie（Custom Render Texture，**格式要带 alpha：ARGBHalf 或 Alpha8**；接口 §3） |
| `../Common/Shaders/LanbaiCaustics.cginc` | 焦散（车厢也用：`#include "Assets/Lanbai/Common/Shaders/LanbaiCaustics.cginc"`、`LanbaiCabinCaustics(posWS, nWS)`） |
| `Textures/SeaN_Large_1024.png`、`SeaN_Small_1024.png` | 可平铺的 FFT 浪法线（64 m、9 m）。`sea_textures_meta.json` 里有每级 mip 被平均掉的斜率方差（shader 的 Toksvig 项） |
| `Textures/SeaMacro_512.png` | 平静 / 起纹宏遮罩（1.5 km） |
| `Textures/Caustics_8x8_2048.png` | 64 帧循环焦散（0.3 Hz 一圈）：真的把阳光折射过动的水面、在 2.2 m 深处收集光子算的 |
| `Textures/CausticsCookie_Static_256.png` | 焦散 cookie 的**静态退路**（CRT 当不了 cookie 时拖进太阳的 Cookie 槽；`Tools~/make_cookie.py`） |
| `Textures/Sea_PurpleCeiling.png`、`Sea_PurpleCeiling_S11.png` | 紫色护栏的查找表（360 × 484，无压缩、无 mip、**点采样**；`Tools~/purple_scan.py` 烘，证明在 `Docs~/purple_scan.json`） |
| `Textures/ShaftStreaks_256.png` | 光柱条纹 |
| `Textures/Cube_Dawn_256.exr`、`Cube_DuskLower_256.exr`、`Cube_Dusk_256.exr` | **备用**立方图（晨 = Syferfontein HDRI，太阳在方位 +30°，D-12；暮 = 参考帧用的同一片按圣经填值合成的暮天；6 面横条、D3D 面方向、BC6H）：正式的由 `LanbaiReflectionBaker` 烘 |
| `Models/Sea_Disc.fbx` | r 40 km 的圆盘（中心密） |
| `Models/Sea_Dome.fbx` | 水下穹顶（真尺寸 r 1800 m：bounds 对） |
| `Models/Sea_Ceiling.fbx` | 天花：`Sea_Ceiling_Inner`（r ≤ 2.3 km，不透明）+ `Sea_Ceiling_Edge`（2.3–3.2 km，透明，2.7 km 处 50 %、渐隐带 800 m）；**接缝那一圈两块共用同样的 192 个角度** |
| `Editor/LanbaiSeaEditor.cs` | 导入设置 + 材质菜单 + 预览全局量的菜单 |
| `Tools~/` | `make_sea_textures.py`、`make_sea_assets.py`（贴图、网格、立方图）、`make_cookie.py`、`sea_numpy.py`（**shader 的逐行 numpy 移植**，参考图用它）、`grade.py`、`purple_scan.py`、`frame_measure.py`（按终审的量法量参考帧）、`k5_dissolve_ramps.py`、旧的 `compile_check/` |
| `Docs~/` | `lookdev_brief.md`、`lookdev/scene_kit.py`（标准台的场景脚本，读 `SeaMaterials.json`）、`iterations/`（38 轮）、`K5_dissolve_series.png`、`K5_dissolve_ramps.json`、`purple_scan.json`、评审稿和回应 |

---

## 2. 几个要知道的做法

- **浪**：两张 FFT 法线滚动 + 宏遮罩；**远处的浪按屏幕导数折进粗糙度**（每张法线按自己的 mip 级查“已被平均掉的斜率方差”，加进 GGX α²）。所以第 6 幕 2.6 km 外的海不会变成闪烁的亮点，而是一条连续的闪光路。`_WaveRotate` 可以把两张图的风向转开（天花用：左右均匀）。
- **第 6 幕倒影太阳**：解析 GGX 闪光，每个像素软封顶在日盘 × 2^−1.3（E14）；日盘大小读 `_Udon_SunDisc.y`（D-18：直径 0.53°），没设用 `_SunDiscDeg` 0.53；立方图采样封顶在 `_ReflClamp`（2.378 = 日盘最大通道 × 0.41）。
- **斯涅尔之窗（7a）有意偏离物理**（D-17 批准）：真实的晨天从水下看，窗的边（地平线）比中心亮；圣经要窗心 `#E6F3F8`、往边落。做法是 **`_WindowCore`**：按**视线**的天顶角给窗一个亮度上限（窗心线性 4.45，到窗缘暗 3 EV），软钳、色相不变；窗心再去饱和到近白、窗缘留着天的蓝和向阳侧的金。换成正式的 `ReflCube_Dawn` 以后按截图校 `_WindowGain` 和 `_WindowCore.x`（窗心 `#E6F3F8`）。**VR 抬头另有一组数**（接口 §2.3 末）。
- **7c 窗里的日弧**：物理上，地平线下的太阳被折射压在窗边不到一个像素、而且菲涅耳把它吃掉。圣经要它是最亮点、一道弧，所以有 `_WindowSun*`：按**平的水面**算（不被碎浪打碎），沿窗缘 ±30°、弧半高 3°，自己的增益，**替换**它下面的蓝（叠加会变成薰衣草紫）。
- **第 8 幕天花（D-17）**：镜带“珍珠金”（`_MirrorTint (1.25, 1.3, 1.25)`、`_ReflGain 1.5`）；天花材质用 `LanbaiFog` 的高度衰减 120 m，暖色的雾不把头顶的深蓝水染紫。
- **紫色护栏（D-17 + D-21 修订）**：h_ab 290–330、C\* > 8、L\* > 40 的拦住，圣经色板里的颜色、L\* ≤ 40 的深靛蓝都放过；查找表存每条饱和度射线上的两段紫区间，按每个材质所在幕的调色证明过（接口 §2.7）。
- **天花溶化（K5）**：前沿 4 s 从地平线走到天顶，每个像素 5 s、亮度按 EV 线性（`_SkyBehindCube` 告诉 shader 后面那片天多亮）。逐像素核查（`Tools~/k5_dissolve_ramps.py`，前提已含雾、护栏、金点）：0.25 s 最坏 0.14 EV（≤ 0.5）、1 s 0.57（≤ 1.0）、2 s 1.13（≤ 1.8），**PASS**；25 个金点到 959.85 全亮、亮度从不上升、964.85 最后一个灭。
- **依赖 UV 精度（CONTROL §6 第 8 条）**：粒子、灯点、光柱的网格把种子、半径、时间轴秒（播下的光的出生时刻 558–645 s）放在 UV0–UV2。**Player Settings → Vertex Compression 不能勾 TexCoord0–2**（half 在 600 s 的步长是 0.5 s）。模型导入器里海的网格压缩是关的。
- **显存**（含 mip）：法线 2 × 1.33 MB（1024² BC5）、宏遮罩 0.33（512² BC7）、光柱条纹 0.09、焦散图集 5.33（2048² R8，不压缩：亮网只有 1–2 texel 宽）、备用立方图 3 × 0.5（6 × 256² BC6H）、紫色护栏表 2 × 0.70（360 × 484 RGBA32，不压缩）、焦散 cookie 的 CRT 0.5（256² ARGBHalf）= **约 11.9 MB**；退路 cookie 只在换上时 +0.33。不含总控烘的正式立方图。

---

## 3. 参考图（`Docs~/iterations/`，标准台、PPv2 引擎模拟、主座位眼位 (0.55, 1.70, 2.05)、除注明外不带车壳）

量法：`Tools~/frame_measure.py`（sRGB → Lab D65，CIEDE2000，和终审的量法一样）。

| 帧 | 定稿 | 量出的 |
|---|---|---|
| K2 斯涅尔之窗（F3 367.21，深 6.3 m，仰 60°，S7a） | **`29_K2_r06`** | 窗心（天顶 15° 内）中位 `#EAEFF4`、L\* 94.2，对 `#E6F3F8` ΔE2000 3.4；**全帧最亮在天顶 0.9°**；窗缘（天顶 38–50°）p99.9 比窗心中位暗 0.97 EV、最亮点比窗心最亮点暗 1.0 EV；暗镜（天顶 52–62°）`#1F4060`、L\* 26.2，对 `#11395E` ΔE 2.5；APL 138 |
| K2 仰 90° | `30_K2_r06_up90` | 窗心 L\* 94.2；不带车壳 APL 187（桌面的数，VR 见下一行） |
| K2 VR 抬头（387 s，`bible_v2` 车壳 + 车顶仰角 40° 以上全侵蚀，VR） | **`31_K2_r06_vr_roof`** | VR 的 `_WindowCore` (3.2, 4, 2)：**APL 147.8 ≤ 150**（D-09）；窗心 L\* 85.2；对照 `32_…desktopvalues`（桌面的数）APL 178.1 |
| K1 海镜正前（6d 350 s，离海 70 m，俯 10°，S6） | **`33_K1_r05fwd`**（对照 B） | 圣经雾 `#FFE4F0`、太阳方位 +30°、日盘 0.53°；闪光路 ≤ 日盘 −1.3 EV；地平线带 C\* 5–9（第 1 轮的“橄榄色”是 C\* 8.6–10、h 109–115，现在色相 93–159、更灰）；APL 162（替身 HDRI 天偏亮） |
| K1 俯 45° | `23_K1_r04` | 水体色对 `#1C3D63` ΔE 3.8 |
| K3 倒置的窗（7c 897.96，俯 45°，S7b） | **`34_K3_r16`** | **全帧最亮 = 窗缘那一道连续的日弧**（最亮 0.2 % 中位 `#E0A58B`、h_ab 50、L\* 73，对 `#C98A7A` ΔE 9.2——比它亮、偏金）；窗心 `#32354B`（h 289，靛灰：深 36 m 的雾吃掉一半），往窗缘过渡到暖的一圈 `#4E3B39`（h 29）；暗镜里 45 个分得开的金点（h_ab 中位 62，52–71）；同一颜色的最大一片 21 %（第 1 轮 39 %） |
| K4 海之天花（F9b 940.36，h 148 m，仰 35°，S8） | **`35_K4_r10_35`** | 镜带（仰角 2–7°）`#D3A284`、h_ab 58、L\* 70、C\* 27（“珍珠金”，第 1 轮 `#B68A61` L\* 47–61）；左右波纹比 1.09（第 1 轮 1.75）；金点心 `#E0C197` 一类，h_ab 74–79；紫：只有金点光晕边上 53 px（0.01 %） |
| K4 正前 | `36_K4_r10_0` | 镜带 h_ab 65、L\* 74；左右 1.16；地平线以下是替身暮天（不归海） |
| K5 溶化（956.36 ± 1 s，每 0.25 s；再 959.36 / 962.36 / 965.36） | **`../K5_dissolve_series.png`** | 金点在 956.36 那一帧和之后都在，最后走（`K5_dissolve_series_points.txt`） |
| K6 第 11 幕抬头（1190 s，仰 60°，S11） | **`37_K6_r01_glints_off`**、**`38_K6_r01_glints_on`** | 填 `#0F283C`；灯闪关：APL 33，读成夜空；灯闪开：一串钠黄的光落在长浪上（替身灯 8 盏） |

渲法：车外由 `sea_numpy.py` 对标准台相机的每个像素算好，贴在一张只给相机光线看的远卡上（`scene_kit.py`）。参考帧的材质数全部从 `SeaMaterials.json` 读（`--set M.<属性>=…` 才会覆盖）。

---

## 4. 对评审意见的回应

- **总导演终审（`总导演终审.md`）**：§一 9 条、§二 11 条逐条改完，**逐条回应在 `Docs~/review_final_response.md`**。
- 总工程师第 1 轮、美术 / 技术第 1 轮与陌生人测试：`Docs~/review_r1_*.md`，回应 `Docs~/review_r1_response.md`。

---

## 5. 检查

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Sea/Shaders Common/Shaders/LanbaiCaustics.cginc` → **`9 files, 142 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`**
- C#：`bash Common/Tools~/compile_check/check_cs.sh Sea` → **`C# CHECK OK (0 assembly error(s), 0 lint warning(s))`**
- 紫色护栏：`~/bpy/bin/python Sea/Tools~/purple_scan.py`（约 10 分钟）→ 每个材质剩下的紫 0。
- 溶化：`~/bpy/bin/python Sea/Tools~/k5_dissolve_ramps.py` → PASS。
- **没在 Unity 里编译过，没在头显里看过**（每个 shader 都要闭一只眼、再闭另一只各看一遍）。

---

## 6. 诚实的已知弱点

1. 参考图的天是替身（K1 缩放的 HDRI、K4 / K5 按圣经填值合成的暮天、K3 窗里是合成暮天的镜像），云 / 天空交了真天以后要重渲；窗、镜带的调色参数是按替身调的。
2. 备用立方图没有云、没有云盖；面方向按 D3D 约定写，导入评审核过（太阳在 +X 面左边缘），现在方位改成 +30°，**导入后看一眼太阳是否在方位 +30°**。
3. 光柱、粒子、水线、穹顶、焦散 cookie 只过了编译检查，还没出参考图（第 7a 包的事）。
4. 焦散 cookie 用 CRT 当平行光 cookie：格式改成带 alpha 以后理论上可以，Built-in / VRChat 里没验证；不行就换 `CausticsCookie_Static_256.png`。
5. K2 暗镜 L\* 26 对目标 23（ΔE 2.5）：下限是圣经的水下雾中间色 `#77A0D2` 在 0.040 /m 下的那部分；再压要动雾（7a 包里和雾一起调）。
6. VR 抬头、车顶全开时，窗心 L\* 只能到 85（APL 150 的代价）；桌面 94.2。
7. 7c 的日弧、斯涅尔之窗的亮度上限都是为了追圣经画面的**非物理**参数（D-17 批准）。
8. 第 11 幕的 `_LampGlints 5.4` 是按替身灯校的；灯与假醒按真灯截图只改这一个数。

## 7. 与评审的分歧

- （紫色护栏 285 / 290 的分歧已由 D-21 修订定为 290–330、L\* > 40，圣经色板放过。照做了。）
- 早先的：APL 目标是正前方的（特写帧不可比）；替身天的数不归海（`Docs~/review_r1_response.md` 末节）。
