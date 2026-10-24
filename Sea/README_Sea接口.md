# `Lanbai/Sea` · 接口说明（给「天空」和总控，先于实现推上来）

写的人：云端子会话「海」（分支 `pkg/sea`）。2026-10-22 起。
**状态：接口 v2（2026-10-23，总导演终审 `总导演终审.md` 改完）。** v1.1 → v2：材质的数改成唯一来源 `Sea/SeaMaterials.json`（§2.0）；斯涅尔之窗加 `_WindowCore`、`_WindowSunGain`（§2.3）；紫色护栏换成查找表（§2.7）；金点的队列和颜色（§2.6）；天花接缝 2.3 km（§2.4）；水下雾写 `_Udon_Fog`（§3）；`_Udon_PalaceVeil` 的定义（§3）。名字、模式不改名，只加。
**都没在 Unity 里编译过。** shader 用 `Common/Tools~/compile_check`（DXC + Unity 2022.3 的 CGIncludes）查过，C# 用 Roslyn 查类型。

`Lanbai/Sea` 在三幕里用：
- **第 6 幕（云摆）**：2 606 m 下方的海，305.4 起看得见，337.0 起是海镜 → **ABOVE**。
- **第 7 幕（海摆）**：头顶的水面 / 斯涅尔之窗（7a）→ **BELOW**；7c 车下的倒置斯涅尔之窗 → **BELOW 翻转**（同一模式，`_AirSide = -1`）。
- **第 8 幕（云摆）**：海之天花（8-i）→ **CEILING**。

- **第 11 幕（灯与假醒摆）**：路上方 80 m 的倒挂的海 → **CEILING + 第 11 幕变体**（§2.5）。

所以第 6、8 幕的海**物体归云**（R_Dawn、R_Dusk 里各放一块），第 11 幕的归灯与假醒，材质用我的 shader；第 7 幕的水面物体归我（R_Sea）。交接都在遮挡下（入水的水线、出海的水线），两块平面在交接那一帧位置相同（§5）。

---

## 1. 文件（推上来以后的位置）

| 文件 | 是什么 |
|---|---|
| `Sea/Shaders/Lanbai_Sea.shader` | 本体，三个模式（`_SEA_ABOVE` / `_SEA_BELOW` / `_SEA_CEILING`，材质上的 KeywordEnum） |
| `Sea/Shaders/LanbaiSea.cginc` | 法线、菲涅耳、斯涅尔、太阳闪光钳位、天花溶化的全部数学（Python 移植 `Sea/Tools~/sea_numpy.py` 与它逐行对应，参考图用它渲） |
| `Common/Shaders/LanbaiCaustics.cginc` | 焦散采样函数（车厢从第 1 幕起就 include 它，所以放 Common；归海） |
| `Sea/SeaMaterials.json` | **材质的数的唯一来源**：菜单 `蓝白/Sea/Create Materials` 读它建材质，参考帧（`Docs~/lookdev/scene_kit.py`）也读它 |
| `Sea/Textures/Sea_PurpleCeiling.png`、`Sea_PurpleCeiling_S11.png` | 紫色护栏的查找表（360 × 484，点采样；§2.7；证明 `Docs~/purple_scan.json`） |
| `Sea/Textures/CausticsCookie_Static_256.png` | 太阳焦散 cookie 的静态退路（§3 焦散） |
| `Sea/Shaders/Lanbai_SeaSpecks.shader` | 海里远处的灯点（**四边形**网格，lens_tech `Lanbai_PointSprites` 的网格约定：每点 4 个顶点同一位置、UV0 = 角；朝两眼中点展开、≥ 1.4 px；第 8 幕天花里的 20–30 个金点也用它，§2.6） |
| `Sea/Shaders/Lanbai_SeaDome.shader`、`Lanbai_SeaWaterline.shader`、`Lanbai_SeaShaft.shader`、`Lanbai_SeaParticles.shader`、`Lanbai_SeaCausticsCookie.shader` | 水下穹顶、车窗水线、水下光柱、海雪 / 播下的光 / 船体荧光 / 气泡、太阳的焦散 cookie（第 7 幕用，属性写在各文件头） |
| `Sea/Models/Sea_Disc.fbx` | 平的圆盘，半径 40 km，极坐标环（中心密）。ABOVE / BELOW 用 |
| `Sea/Models/Sea_Ceiling.fbx` | 天花两块：`Sea_Ceiling_Inner`（r ≤ 2.3 km）+ `Sea_Ceiling_Edge`（2.3–3.2 km），**接缝那一圈两块共用同样的 192 个角度**（§2.4） |
| `Sea/Textures/SeaN_Large_1024.png`、`SeaN_Small_1024.png` | 两张可平铺的 FFT 海浪法线（64 m、9 m 平铺） |
| `Sea/Textures/SeaMacro_512.png` | 平静 / 起纹的宏遮罩（1.5 km 平铺，R：0 = 镜面，1 = 起纹） |
| `Sea/Textures/Cube_*.exr` | 云端给的**备用**立方图（从选定的两张 Syferfontein HDRI 做的）。天空交了正式的天、总控的烘焙器烘了每幕的立方图以后就不用它们 |

圆盘网格**跟着车走 xz**（跑步机：车不动，海是无限的，只有 y 和浪的平移在变）。浪的平移靠全局 `_Udon_SeaClock.yz`，不靠移动物体。

---

## 2. 模式与材质参数

所有颜色都是 **线性 Vector**（不经 sRGB 转换，和门的做法一样）。没写的参数用默认值。

### 2.0 每个材质的数（`Sea/SeaMaterials.json`，第 2 轮定稿）

下表是 JSON 里的数，和菜单建出来的材质、参考帧用的完全一样。**改数只改 JSON**，再点一次菜单。“驱动”一列是随时间变的，材质里放的是参考帧那一刻的值。

| 材质 | 参考帧 | 和 shader 默认不同的数 | 驱动随时间改的 |
|---|---|---|---|
| `M_06_Sea`（ABOVE，S6） | `33_K1_r05fwd`（俯 10°）、`23_K1_r04`（俯 45°） | `_WaterColor` (0.0163, 0.0430, 0.1070) = `#304F7A` 的填值 × 0.55；`_CalmAll` 0.85；`_SunColor` (5.856, 3.615, 2.002) = 日盘 `#FFCE9E @ +2.55`；`_ReflClamp` 2.378 = 日盘最大通道 × 2^−1.3；`_SunDir` (0.4973, 0.1045, 0.8613) = 方位 +30°、仰角 +6°（D-12）；`_SunDiscDeg` 0.53（D-18，`_Udon_SunDisc` 设了就用它的）；`_PurpleMask` R | `_CalmPatch`、`_CalmAll`（§4）、`_SunColor` × 云盖遮挡 |
| `M_07a_SeaSurface`（BELOW，S7a） | `29_K2_r06`（仰 60°）、`30_K2_r06_up90`（仰 90°）、`31_K2_r06_vr_roof`（VR） | `_WindowGain` **18**；`_WindowTint` (1.5, 1.3, 1, **0.85**)（w = 窗心的去饱和，到窗缘降到 0）；`_WindowCore` (**4.45, 3, 2, 1**)（窗心亮度上限 = 线性亮度 4.45，窗缘比窗心暗 3 EV，按视线天顶角的 2 次方走）；`_WindowRadial` (1, 2) = 关（被 `_WindowCore` 取代）；`_ReflClamp` 1.5（窗里立方图采样的上限）；`_TIRColor` (0.018, 0.058, 0.140)、**`_TIRFog` 0.3**（暗镜只吃三成的雾，D-23：暗镜 `#15395C`、对 `#11395E` ΔE 0.6）；`_PurpleMask` G+B | **VR**：`_WindowCore` = (3.2, 4, 2, 1)（§2.3 末） |
| `M_07c_SeaMirror`（BELOW 翻转，S7b） | `34_K3_r16`（俯 45°，897.96） | `_AirSide` −1；`_WindowCube` = Cube_DuskLower；`_WindowGain` **0.25**（直接是 0.25，不是“× 0.12”）；`_WindowSunColor` (24, 8.5, 5)；`_WindowSunGain` 1；`_WindowSunDir` (0, −0.0523, 0.9986, **3**)（另一个太阳在方位 0、仰角 −3°，弧半高 3°）；`_WindowSunSpread` 30；`_TIRCubeGain` 1；`_TIRColor` (0.0241, 0.0126, 0.0121) = 雾 `#3E2C2B` × 0.5；`_WaveAmp` 0.02（897.96 那一刻）；`_ReflClamp` 8；`_PurpleMask` B | `_WaveAmp`：F8 起 0.3 → **0.02**（F8b 起 6 秒，圣经“颤动停止”）；`_WindowGain` 0 →（F8b → 897.96）0.25；`_WindowSunColor` × 同一条 0 → 1 |
| `M_08_SeaCeiling` / `…Edge` / `…Fade`（CEILING，S8） | `35_K4_r10_35`、`36_K4_r10_0`、`K5_dissolve_series.png` | 共用：`_WaterColor` (0.0116, 0.0296, 0.0683)；`_FogHeightFalloff` 120；`_NormalStrength` 0.25；`_WaveRotate` (**70.7, 35**)（两张浪图的风向转到视轴上：左右均匀）；`_CalmStrength` 1（天花不要平静斑：左右一样）；`_MirrorTint` (**1.25, 1.3, 1.25**)、`_ReflGain` **1.5**（镜带“珍珠金”）；`_ReflClamp` 8；`_PurpleMask` A。Inner / Fade：`_DiscCenter` 0；Edge：`_DiscCenter` (0, 0, 2700, 800) | `_DissolveTime`（§2.4） |
| `M_11_SeaHanging`（CEILING，S11） | `37_K6_r01_glints_off`、`38_K6_r01_glints_on` | `_WaterColor` (0.0048, 0.0212, 0.0452) = 圣经第 11 幕填 `#0F283C`；`_NormalStrength` 0.1；`_GerstnerAmp` (0.6, 0.35, 0.15)；`_LampGlints` **5.4**；`_PurpleCeiling` = `Sea_PurpleCeiling_S11.png`、`_PurpleMask` R | — |

### 2.1 三个模式共用

| 属性 | 默认 | 说明 |
|---|---|---|
| `_SEA`（KeywordEnum Above / Below / Ceiling） | Above | 模式 |
| `_NormalLarge` / `_NormalSmall` | SeaN_Large / SeaN_Small | 两张 FFT 法线 |
| `_LargeTile` / `_SmallTile` | 64 / 9 | 平铺（米） |
| `_LargeScroll` / `_SmallScroll` | (0.9, 0.35) / (−0.4, 0.7) | 各自的漂移（m/s，xz） |
| `_NormalStrength` | 1 | 总的法线强度 |
| `_WaveRotate` | (0, 0) | 两张浪图在世界 xz 里转多少度（x 大浪、y 小浪）。天花用 (70.7, 35)：把风向转到正前方，论点之帧左右的波纹一样（终审） |
| `_WaveAmp` | 1 | 浪的振幅（7c：F8 时 0.3，F8b 起 6 秒降到 0.02；别处 1） |
| `_Macro` / `_MacroTile` | SeaMacro / 1500 | 平静 / 起纹宏遮罩 |
| `_CalmStrength` | 0.15 | 平静区里法线乘多少 |
| `_CalmAll` | 0 | 0..1：把整片海压平到平静区的样子（第 6 幕 337.0 海镜落定用） |
| `_CalmPatch` | (0, 0, 0, 0) | xy = 平静斑的中心（世界 xz，m），z = 半径 m，w = 0..1 强度（F1b2 车下那块平静的海） |
| （没有 `_FlattenDist`） | | 远处的浪**全程按屏幕导数**折进粗糙度：shader 从 uv 的 ddx/ddy 算出每张法线贴图的 mip 级，把那一级已经被平均掉的斜率方差（按频谱算好的表，`Textures/sea_textures_meta.json`）加进 GGX α²。近处自然退回原样（总工程师 #4） |
| `_IOR` | 1.333 | 水的折射率（菲涅耳、斯涅尔） |
| `_WaterColor` | ABOVE (0.0156, 0.0484, 0.0954) | 水体的回散颜色（从上看进水里）。ABOVE 默认 = 第 6 幕脚下远海的填值 `#304F7A` × 0.5 的近似，按截图调 |
| `_ReflGain` | 1 | 立方图反射的乘数 |
| `_ReflClamp` | 2.4 | 立方图采样的最大通道上限（线性）。**第 6 幕 = 日盘最大通道 × 2^−1.3**（日盘填 `#FFCE9E @ +2.55` → 5.9 × 0.41 ≈ 2.4），所以立方图里的太阳在海里永远暗过日盘 1.3 EV；闪光由解析项负责（总工程师 #5）。用“不含日盘”的立方图时可以放宽。斯涅尔之窗的采样也钳在这个值 |
| `_FogMode` | 1 | 按圣经的编号：0 = 不吃雾；1 = `LanbaiApplyFog`（默认）；（2 = 天上的东西自带衰减，海不用） |
| `_DiscCenter` | (0, 0, 0, 0) | xy = 圆盘边缘的圆心（世界 xz），**z = 半径 m，w = 渐隐带 m**；z = 0 表示不裁（无限海） |

反射一律查全局 `_Udon_ReflCube`（`_Udon_ReflCube_HDR`、`_Udon_ReflExposure`，已登记，每幕由当前幕的驱动设）。

### 2.2 ABOVE（第 6 幕：从空中往下看）

| 属性 | 默认 | 说明 |
|---|---|---|
| `_SunColor` | (0, 0, 0, 0) | 日盘的线性辐亮度（**和 `Lanbai/Sky` 画日盘用的同一个数**，第 6 幕填 `#FFCE9E @ +2.55` 的线性值）。0 = 不画闪光 |
| `_SunDir` | (0.4973, 0.1045, 0.8613, 0) | 指向太阳的单位向量：方位 +30°、仰角 +6°（D-12）。全局 `_Udon_SunDir.w > 0` 时用全局的 |
| `_SunDiscDeg` | 0.53 | 日盘直径（D-18）。全局 `_Udon_SunDisc.w > 0` 时用它的 y（半径，度）× 2 |
| `_SunGlitterRough` | 0.12 | 闪光路径的“浪坡”宽度（GGX α，越大路越宽越碎） |
| `_SunReflPeakEV` | 1.3 | **闪光路径的任何一点都比日盘暗至少这么多 EV**（圣经 E14：≥ 1.3）。shader 里是软钳位，色相不变 |

### 2.3 BELOW（第 7 幕：人在水里）

| 属性 | 默认 | 说明 |
|---|---|---|
| `_AirSide` | 1 | **+1 = 空气在平面上方**（7a：抬头看斯涅尔之窗）；**−1 = 空气在平面下方**（7c：车下的倒置斯涅尔之窗）。网格法线照旧，shader 自己翻 |
| `_WindowCube` | Cube_Dawn | 窗里看到的“另一边”的天（7a = 晨的天，7c = 暮的下半球 `ReflCube_DuskLower`） |
| `_WindowGain` | 1 | 窗里那片天的乘数（7a 18、7c 0.25，§2.0）。**不再乘日弧** |
| `_WindowTint` | (1, 1, 1, 0) | rgb 乘数；**w = 窗心的去饱和**（0..1，往窗缘按 (θ/θc)² 降到 0：窗心近白 `#E6F3F8`，窗缘留着天自己的蓝和金） |
| `_WindowCore` | (0, 0.5, 2, 0) | **窗的亮度上限**（终审 #5：窗心是全窗最亮的，窗缘的碎闪至少暗 0.5 EV）：x = 窗心的线性亮度上限，y = 到窗缘降多少 EV，z = 按**视线**的天顶角 θ/θc 的几次方，w > 0 开。软钳（tanh），色相不变；按视线不按浪的法线算，所以窗缘斜过来的浪面也亮不过窗心 |
| `_Dispersion` | (1.331, 1.337) | R / B 的折射率（窗边的轻微色散）；G 用 `_IOR` |
| `_TIRColor` | (0.0222, 0.0685, 0.1651) | 全反射暗镜的颜色（7a 屏幕 `#11395E`，按调色套件改填 `#294B72`） |
| `_TIRCubeGain` | 0 | 全反射区里再加多少 `_Udon_ReflCube`（7c 映着宫殿的灯：1） |
| `_WindowEdgeSoft` | 0.6 | 窗边（临界角处）的软化，度 |
| `_WindowSunColor` / `_WindowSunGain` | 0 / 1 | 7c 的日弧（“玫瑰金的弧，贴在窗缘”）：线性颜色 × 自己的增益。**按平的水面算**（不吃浪的法线：一道连续的线，不会被全反射的碎浪打碎），过了临界角在 ~1° 里淡掉 |
| `_WindowSunDir` / `_WindowSunSpread` | (0, −0.0087, 1, 1.2) / 14 | 空气那一侧的太阳方向；w = 弧的半高（度）。Spread = 弧沿窗缘的半宽（度） |
| `_WindowSunFloor` | 0.35 | 日弧的透射下限（贴着临界角时菲涅耳会把它擦掉） |
| `_TIRFog` | 1 | 全反射暗镜吃多少雾（1 = 物理；7a 0.3）。按窗 / 镜的比例在两者之间过渡（`LanbaiSeaBelow` 的 a = 窗的比例） |

**VR 抬头（D-09：APL ≤ 150；D-23 #2）**：用 `vr_left_fwd` 机位（Index 单眼近似）仰 90°、标准台 `bible_v2` 车壳、**车顶从仰角 40° 往上全被侵蚀掉**（方位 −180…180，最坏情况）量：桌面的数（4.45, 3, 2）APL 121.2、窗心 L\* 91.0（`32_…desktopvalues`）；VR 的数 (3.2, 4, 2, 1) APL 97.8（`31_K2_r06_vr_roof`）。第 7a 包的驱动在 VR 里按车厢侵蚀（F2h → F5：0 → 0.25）在两组数之间过渡：车顶还在时就是桌面的数。也就是说：整片视野都是窗的时候，“窗心 L\* ≥ 90”和“APL ≤ 150”不能同时成立，VR 让亮度（安全）赢，窗心的相对关系（窗心最亮、窗缘暗 1.8 EV）不变。车顶只侵蚀到天窗附近时 APL 远低于 150（同一机位、不开顶：16.8）。

### 2.4 CEILING（第 8 幕：海之天花）

**渲染状态（总工程师 #6；终审 #3 改）**：溶化开始之前，天花只有 2.3–3.1 km 的边是半透明的。网格两块：**内盘 r ≤ 2.3 km 用不透明材质** `M_08_SeaCeiling`（队列 2000、`ZWrite On`、`_DiscCenter.z = 0`），**外环 2.3–3.2 km 用透明材质** `M_08_SeaCeilingEdge`（队列 2990，`_DiscCenter` (0, 0, 2700, 800)：2.3 km 处 alpha 正好 1、2.7 km 0.5、3.1 km 0）。**接缝在 2.3 km，正是外环渐隐开始的地方**，所以两边 alpha 都是 1、连续；两块在接缝那一圈用同样的 192 个角度（同一组顶点位置，没有 T 形裂缝；`make_sea_assets.py` 生成，导入后核过）。956.36 起内盘换成透明材质 `M_08_SeaCeilingFade`，只有溶化的 9 秒付全盘混合的钱（主机位约 0.5 FSE）。

**队列**：天花不透明 2000 → 外环 / 溶化 2990 → **金点 2995**（§2.6）→ 车厢玻璃 3000。

| 属性 | 默认 | 说明 |
|---|---|---|
| `_WaterColor` | (0.0116, 0.0296, 0.0683) | 头顶透见的深水（屏幕 `#10263F`，填 `#1C304B`） |
| `_DiscCenter` | (0, 0, 2700, 800) | 有限的圆：2.7 km 处 alpha 0.5，渐隐带 800 m（2.3 → 3.1 km；圣经 ≥ 500 m）。只在外环材质上 |
| `_MirrorTint` / `_ReflGain` | (1.25, 1.3, 1.25) / 1.5 | 掠射的镜带：“珍珠金”（实测 h_ab 58、L\* 70、C\* 27，`35_K4_r10_35`），D-17 的 h ≥ 55 |
| `_NormalStrength` | 0.25 | 圣经：法线扰动 ≈ 0.02 rad |
| `_DissolveTime` | −1 | **天花溶化的时钟：t − 956.36（F10e）**；< 0 = 完整。驱动每帧写 |
| `_DissolveFront` | 4 | 前沿从地平线走到天顶的秒数（956.36 → 960.36） |
| `_DissolvePixel` | 5 | 每个像素自己的淡化秒数（EV 线性；≥ 5 才过爬升律） |
| `_SkyBehindCube` | Cube_Dusk | 天花后面那片天（上半球）。shader 用它算每个像素的 EV 线性 alpha |

溶化的定义（`LanbaiSea.cginc` 的 `LanbaiCeilingProgress` / `LanbaiCeilingLampProgress`；`Lanbai_SeaSpecks` include 同一个文件、调同一个函数）：
仰角 el（度，0 = 地平线，90 = 天顶），像素进度 `p = saturate((τ − τ_front·el/90) / τ_pixel)`，τ = `_DissolveTime`。
像素的亮度沿 `L(p) = Lc^(1−p) · Ls^p` 走（Lc = 天花这个像素自己的颜色，Ls = `_SkyBehindCube` 在同一方向的颜色），alpha 由它反解；天顶的最后一个像素在 τ = 9.0（965.36）溶完，等于圣经的 ≈965.4。宫殿的灯点用 `p' = saturate((p − 0.3)/0.7)`：同一个像素里比水晚走。

### 2.5 第 11 幕变体（倒挂的海，CEILING 模式里多出来的几个参数；`Lamps/总导演意见.md` §2）

| 属性 | 默认 | 第 11 幕 | 说明 |
|---|---|---|---|
| `_GerstnerLength` | (60, 37, 23, 0.08) | 同 | 三个长浪的波长（米）+ 频率 Hz |
| `_GerstnerAmp` | (0, 0, 0) | (0.6, 0.35, 0.15) | 振幅（米）；0 = 关（第 6、7、8 幕） |
| `_GerstnerDir` | (0.94, 0.34, 0.5, 0.866) | 同 | 第 1、2 个浪的方向（世界 xz），第 3 个是两者角平分线转 90° |
| `_NormalStrength` | 1 | 0.1 | FFT 小浪只留一点：灯的闪光是长浪上的一串光，不是一片糊 |
| `_LampGlints` | 0 | 5.4 | 读 `_Udon_Lamp0..7` 的 GGX 闪光，**和 Rain 的 `LanbaiLamps.cginc` 同一个约定**（E · NdotL · Vis · π · D · F，E = I / d²；读 `_Udon_LampAxis`（灯管当线光源）、`_Udon_LampDir`（锥角）；球光源取离反射线最近的一点，D 和 Vis 用 α、再乘 (α/α′)²，和 Rain 逐项一样）。屏幕目标 `#D08A59`：**只用 `_LampGlints` 校**（0..16），不要动 `_Udon_Lamp*.w`（路面也在读）。5.4 是用替身灯（I 15、半径 0.1 m、钠灯色）校到最亮一点 ≈ `#D08A59` 的值 |
| `_DiscCenter.z` | | 0 | 无限 |
只用浪的**斜率**（80 m 外 0.6 m 的起伏看不出高度，看得出的是灯在上面的光）。其他照 CEILING（`_DissolveTime` 保持 −1）。参考帧：`37_K6_r01_glints_off`（圣经：前 8–20 秒读成夜空）、`38_K6_r01_glints_on`。

### 2.6 `Lanbai/SeaSpecks` 的灯点：颜色、队列、淡出（终审 BLOCKER + #2）

- **颜色 = 灯点在暗处的屏幕目标，金 `#E0A860`（h_ab 74）**，按幕的调色反解成线性顶点色：S8 下 (1.566, 0.616, 0.226)，S7b 下 (1.396, 0.536, 0.142)（`Docs~/lookdev/scene_kit.py` 的 `lamp_gold()`）。**不要用满亮灯焰的 HDR 填值 `#FF5E2A @ +3.11`**：它要靠色调映射的肩部才显成金，变暗以后露出红。flux（UV1.x）按“中位的水中路径之后，点的峰值仍到这个颜色”定：第 8 幕天花 ×12（`35_K4_r10_35` 实测点心 `#E0C197`、h_ab 74–79），7c 暗镜里（烘进 `Refl_S7c` 的灯）×14、0.25°。
- **水的吸收**：天花模式 `_WaterAtten` 是 rgb (0.024, 0.020, 0.017) /m，红吸得最多：远的灯**变冷、变暗，不变红**。
- **队列 Transparent-5（2995）**：在天花的透明材质（2990）之后，**叠在天花上面**，只按自己的进度 p′ 淡出（不乘天花的 α）。956.36 前后各 1 秒、每 0.25 秒一张：`Docs~/K5_dissolve_series.png`，点的亮度表 `Docs~/K5_dissolve_series_points.txt`：25 个点到 959.85 都是全亮，964.85 最后一个灭。
- **深度**：天花模式把点沿视线挪到水面下 `max(_CeilingGap 0.5 m, _CeilingGapRel 0.02 × 距离)`（2 km 外 24 位深度的一格约 24 m，0.5 m 不够），半径按比例缩，角大小不变。
- 金点光晕的边上（叠加的金经过群青）有约 0.01 % 的像素落在 h_ab 290–330、C\* 10–15（`35_K4_r10_35` 53 px），这是加法混色必经的色相，护栏管不到（点在护栏之后叠加），面积远小于 §1.3.4 的 2 %。

### 2.7 紫色护栏（D-17 + D-21；终审 #7）

- **规则（D-21 修订，main 4dacb19，和天空同一条）**：护栏之后，在材质所在那一幕的调色下，没有任何颜色显示成 **h_ab 290–330、C\* > 8 且 L\* > 40**。圣经色板里写明的颜色一律放过：中天 `#808AB2`（h 284.3）、车厢 `#828BAA`（282.0）、暮天顶 `#3D4A80`（289.2）、另一片天的天底 / 7c 窗心 `#2E3C66`（286.3）都在 290 以下；L\* ≤ 40 的深靛蓝也放过；中间调的丁香紫拦住。
- **做法**：`Sea/Tools~/purple_scan.py` 按 OKLab 色相（0.5°）× 亮度（0.0125，到线性 27）× 饱和度 C/L（0.002）整张扫，每个调色（S6、S7a、S7b、S8、S11）分开，沿每条饱和度射线找出**紫的区间**：有的射线上紫是两段，中间夹着安全的一段（S8 下圣经中天 `#808AB2` 就在这样的缝里：比它淡的和比它浓的都显示成丁香紫，它自己不是）。所以每个纹素存两段：段 1 = (lo1, hi1]、段 2 = (lo2, hi2]，烘进 `Sea_PurpleCeiling.png`（360 × 484，RGBA = S6 / S7a / S7b / S8，四段各 121 行：lo1、hi1、lo2、hi2）和 `Sea_PurpleCeiling_S11.png`。**点采样**（导入器设 Point：两个纹素的区间一混合会凭空造出“安全的缝”），每个纹素管自己 ±0.5 格（再加一个细扫描步），lo 取最小、向下取整，hi 取最大、向上取整，两段碰上就合成一段；烘的时候用更严的阈值（h_ab 285–330.5、C\* > 7.0、L\* > 39）给 bloom 和 8 位取整留余量。
- **shader**：颜色落在段 1 里就把 OKLab 彩度缩到 s = lo1，落在段 2 里缩到 s = lo2（缝的上沿）；色相、亮度不动；**两段之外的颜色原样返回**。
- **材质选哪几个调色**（`_PurpleMask`，取所选通道 lo 的最小、hi 的最大）：`M_06` R（S6）；`M_07a` G+B（7a 从 S7a 线性过渡到 S7b）；`M_07c` B（S7b）；`M_08_*` A（S8：S7b → S8 在出海那一帧、车下切）；`M_11` 用 S11 那张表的 R。
- **为什么要两段**：290 之下照样需要。比如 S8 下 `#808AB2` 旁边那一格里，饱和度 0.04 处有一条一步宽的紫（h 290.0、C\* 7.1，在烘焙的余量里），另一段从 0.24 起；只存一段就会把 0.04 到 0.56 当成一整段紫，把中天拉灰（ΔE 17）。所以每格取它管的那一片里所有紫样本的**并集**，再取前两段。
- **证明**（`Docs~/purple_scan.json`）：每个材质 200 万个随机的色域内 HDR 颜色 + 一张**错开半格**的密网格（每个材质 1 230 万–1 530 万个色域内样本），过和 shader 一样的路径（8 位纹理、点采样）和它的调色：**剩下的紫全部是 0**。
- **圣经的颜色过护栏**（15 个，各自的材质和调色下）：**全部 ΔE 0**，包括 `#808AB2`、`#828BAA`、`#3D4A80`、`#2E3C66`。
- **证明管到哪里为止（D-23 #5，三条边界）**：
  1. **护栏之后再混合的颜色不在证明里。** 证明的是“材质输出的那个颜色”；之后的透明叠加（光柱、海雪、气泡、车厢玻璃）、雾以外的后处理混合、bloom 的扩散都在护栏之后。叠的东西各自的颜色都在 290 以下（光柱 `#B0D9F2` 一族、粒子冷蓝 / 金），蓝和金线性相加不会穿过紫，但这一条没有逐像素证明；bloom 的余量就是烘焙时更严的阈值（285 / C\* 7.0 / L\* 39）。
  2. **OKLab L > 3（线性亮度 > 27）的颜色用最后一行（L = 3）的区间**，那以上没有扫。海面在这么亮的地方只有太阳的高光（调色以后是白，C\* ≈ 0）。
  3. **7a 的调色过渡（F3e → F5，S7a → S7b）**：以前只扫了两端，过渡中间（PPv2 两个 volume 线性混合）w = 0.6 处查出漏（每 81 万个里 2 223 个）。现在 G 通道 = `S7a~`：S7a 和过渡上 w = 0.05 … 0.95（步长 0.05）所有调色的并集，证明里也逐个 w 验过（`Sea/Tools~/purple_transition.py`、`Docs~/purple_transition.json`）。步长之间（比如 w = 0.625）没有逐个验，靠的是区间随 w 连续变化、加上烘焙的余量。
---

## 3. 全局量（新加的写进 `给总控.md` 请总控登记）

| 全局量 | 类型 / 含义 | 谁写 |
|---|---|---|
| `_Udon_SeaLevel` | float：当前那块海面的世界 y（第 6 幕：云写；第 7 幕：海写；第 8 幕：云写天花的 y；第 11 幕：灯与假醒） | 当前幕 |
| `_Udon_SeaMode` | float：0 没有海、1 ABOVE、2 BELOW（7a）、3 CEILING、4 BELOW 翻转（7c） | 当前幕 |
| `_Udon_SeaClock` | float4：x = 浪的钟（秒，用时间轴 t 即可）；yz = 海水相对车的平移（世界 xz，米，= 车走过的路），**不要取模**（宏遮罩 1500 m、第 11 幕的长浪 60 / 37 / 23 m 都不是同一个公倍数，取模那一帧会整片跳；不取模时 5 km 的平移也只差 ~0.05 texel，够用。总工程师评审 r1）；w > 0 = 已设。没设时用 `_Time.y`、平移 0 | 当前幕 |
| `_Udon_Underwater` | float 0..1：眼睛在水里。雾和天走水下 | 海 |
| **`_Udon_Fog`** / `_Udon_FogBase` | **第 7 幕由海每帧写 `_Udon_Fog = (水下密度, 0, 0, 1)`**（F2h 0.040 → 0.030 → 0.018 /m，按深度），同时写 `RenderSettings.fogDensity` = 同一个数（内置 shader 读它）、`_Udon_FogBase.w = 0`。**不写旧量 `_Udon_FogDensity`**：`LanbaiFogDensity()` 先看 `_Udon_Fog.w`，第 6 幕留下的 `_Udon_Fog`（w = 1）会把它盖掉（终审 #8）。出海那一帧不清零，交给云接着写 | 海（第 7 幕） |
| `_Udon_WaterFogUp` / `_Udon_WaterFogMid` / `_Udon_WaterFogDown` | 水下雾色（朝上 / 水平 / 朝下，线性）；`LanbaiHorizon` 照这个读。7a 起点：Up = `#294B72` × 0.38 = (0.0084, 0.0267, 0.0639)，Mid = `#77A0D2`（圣经 0–15 m），Down = (0.0159, 0.0733, 0.1275)。7c：围绕 `#3E2C2B`，Up × 0.75、Mid × 1、Down × 1.45（下面窗里的暮光） | 海 |
| `_Udon_T`、`_Udon_SeaBus`、`_Udon_SeaBusVel`（已登记，D-17） | 时间轴秒；车的原点在水的坐标系里的位置（x, −深度, 前进）；它的速度 m/s。第 7 幕的分发层不写 `_Udon_T` 的话，海的驱动在 F2h → 922.36 写它（读：`Lanbai/SeaParticles`、`Lanbai/SeaSpecks`） | 海（第 7 幕） |
| `_Udon_PalaceVeil` | **float4**：x = 雾带里的密度 /m，y = 雾带上沿的世界 y（R_Palace 的世界 y + 0），z = 雾带厚度 m（雾带 y − z … y），w > 0 已设。宫殿 shader：`veil = 1 − exp(−x · 视线在雾带里的长度)`，`col = lerp(col, LanbaiHorizon(视线), veil)`；灯焰不读。F5 → F7s x 0，F7s → F7p 0 → 0.25，保持到出海。全文：`Act07_Sea/PalaceFrame_约定.json` 的 `palace_veil` | 海（第 7 幕） |
| `_Udon_Caustics` | float4：x = 强度 0..1（已含深度衰减），y = 方向 +1 光从上来 / −1 从下来（7c），z = 焦散的钟（秒），w = 平铺缩放（1） | 海 |
| `_Udon_CausticsColor` | float4：rgb = 焦散的线性颜色 × E。7a：座椅上屏幕 `#ACD4ED`（填 `#9FCBFF @ +1.46`）。**7c（从下往上）：金，屏幕 `#E2C08E`（h_ab 80），S7b 下填 (1.475, 0.779, 0.317)**，不用玫瑰（D-08：蓝的车厢会被染成丁香紫） | 海 |
| `_Udon_CausticsTex` | 焦散序列帧图集（全局纹理） | 海 |
| `_Udon_SunDir` / `_Udon_SunDisc` | 天空写。ABOVE 读 `_Udon_SunDir`（w > 0 时）和 `_Udon_SunDisc.y`（日盘半径，度；w > 0 时） | 天空 |

**太阳的焦散 cookie（7a）**：`Lanbai_SeaCausticsCookie` 是 Custom Render Texture 的 shader。**CRT 的格式必须带 alpha**（ARGBHalf 或 Alpha8）：内置管线的平行光 cookie 读的是 **alpha**，R8 / RHalf 的 CRT 读出来 alpha 恒为 1（= 没有 cookie）。shader 把同一个值写进四个通道。**退路**：`Sea/Textures/CausticsCookie_Static_256.png`（同一图案冻在第 0 帧，同样的底 0.25、增益 0.3，alpha 里也是它；导入器设成 Cookie 类型、alpha 来自输入）。切换：把它拖进 7a 太阳的 Cookie 槽，替掉 CRT；光仍随车动，只是不闪了。

---

## 4. 第 6、8 幕怎么用（给云；第 11 幕给灯与假醒，见 §2.5）

**第 6 幕（ABOVE）**
1. 圆盘 `Sea_Disc.fbx` 放在 R_Dawn 下，xz 跟车（0, 0），y = 海面（F0 时在车下 2 606 m，随下降上升）；材质 `M_06_Sea`（模式 Above）。
2. 每帧写 `_Udon_SeaLevel` = 海面 y、`_Udon_SeaMode` = 1、`_Udon_SeaClock` = (t, 0, 0, 1)（第 6 幕车不前进，平移 0）。`_Udon_ReflCube` = 晨的立方图（从海面附近烘：要含云盖的底面）。
3. `_SunColor` = 日盘的线性值、`_SunDir` = 太阳方向；305.4 → 318.36 太阳被云盖挡住时 `_SunColor` × 同一个遮挡系数（和平行光一起，0.1 → 1）。
4. 平静：328.36（F1b2）起 `_CalmPatch` = (0, 0, 300, 0 → 1，6 秒 smoothstep)，**车正下方一块平静的海**；337.0 起 `_CalmAll` 0 → 0.85（8 秒 smoothstep）：海镜落定。入水前最后 5 秒（357.96 →）镜子填满下半个视野，靠近时反射的内容不流动——**浪的平移保持 0**。
5. 倒影太阳的钳位在 shader 里（`_SunReflPeakEV` 1.3），不用驱动管。

**第 8 幕（CEILING）**
1. 圆盘 `Sea_Ceiling.fbx` 放在 R_Dusk 下，xz 跟车，**y = 出海那一帧我写的 `_Udon_SeaLevel`**，之后按 `dusk_motion_final.json` 的 h(t) 往上退（0 → 272 m，F10e）。两个子网格两个材质：**`Sea_Ceiling_Inner` → `M_08_SeaCeiling`**（956.36 换成 `M_08_SeaCeilingFade`），**`Sea_Ceiling_Edge` → `M_08_SeaCeilingEdge`**。网格法线已经朝下（导出时就是 −Y），不用再翻。
2. `_Udon_ReflCube` = `ReflCube_DuskLower`（天花的镜面反射的是**下面**的暮天）；`_SkyBehindCube` = 暮的上半球。
3. 溶化：956.36 起每帧写 `_DissolveTime = t − 956.36`，**写三个材质**：`M_08_SeaCeilingFade`（内盘此刻换成它）、`M_08_SeaCeilingEdge`、金点的 `Lanbai/SeaSpecks`；≥ 9.0（965.36）以后关掉 renderer。宫殿的金点：`PalaceSpecks_Points` 放在天花上方 40–200 m，材质 `Lanbai/SeaSpecks` 设 `_CeilingMode 1`、**队列 2995**、顶点色 = §2.6 的金，读同一个 `_DissolveTime`，自己最后走。
4. `_Udon_SeaMode` = 3；`_Udon_Underwater` = 0（出海那一帧我写 0）。

---

## 5. 交接（同一块水面，两个物体）

| 时刻 | 从 → 到 | 交接 |
|---|---|---|
| **F2h 363.26 入水** | 云的 ABOVE 平面 → 海的平面 | **两块平面永不同时存在**（总工程师 #3：共面会 z-fighting 闪）。**F2h 那一帧**云关掉自己的海、海的平面开（同一个 y、同一个材质参数，**先用 ABOVE 材质**）；眼睛下水那一帧（≈363.62 = F2h + 0.36，水线遮挡中）海的平面换成 BELOW 材质，`_Udon_Underwater` 0 → 1。`_Udon_SeaLevel` 从 F2h 起归海。`Lanbai/Sky` 在水下被穹顶挡住 |
| **F9s + 0.5 = 922.36 出海** | 海的 BELOW 翻转平面（7c，在车下）→ 云的 CEILING 平面 | 同样不并存：车（眼睛）穿过平面的那一帧（922.36）海关掉自己的平面、云开天花，我写最后一次 `_Udon_SeaLevel` = 平面 y、`_Udon_Underwater` = 0；之后归云。**雾的全局量我在那一帧不清零**（交给云的驱动接着写，总工程师建议）。水线由下往上 0.8 秒流走（车窗上的水线是我的 `Lanbai/SeaWaterline`，车厢玻璃 shader 也可以 include `LanbaiSea.cginc` 的 `LanbaiWaterline()`） |

两个时刻的具体数（平面在车坐标里的 y、速度）写进第 7 幕的布局 JSON（`Act07_Sea/Act07_Layout.json` 的 `handover` 块），推第 7a 包时一起给。
