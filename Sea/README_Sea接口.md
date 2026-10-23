# `Lanbai/Sea` · 接口说明（给「天空」和总控，先于实现推上来）

写的人：云端子会话「海」（分支 `pkg/sea`）。2026-10-22 起。
**状态：接口 v1.1（2026-10-23：shader 本体已推，`Sea/Shaders/`；按总工程师第 1 轮意见改了 §1、§2、§4、§5；加了第 11 幕变体 §2.5）。** 名字、模式、参数、全局量不再改名，可以加。
**都没在 Unity 里编译过。** 推上来的 shader 会用 slang 查语法，C# 用 Roslyn 查类型。

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
| `Sea/Shaders/LanbaiSeaGlobals.cginc` | 还没进 `LanbaiGlobals.cginc` 的三个全局量（`_Udon_T`、`_Udon_SeaBus`、`_Udon_SeaBusVel`），同一个守卫宏 |
| `Sea/Shaders/Lanbai_SeaSpecks.shader` | 海里远处的灯点（**四边形**网格，lens_tech `Lanbai_PointSprites` 的网格约定：每点 4 个顶点同一位置、UV0 = 角；朝两眼中点展开、≥ 1.4 px；第 8 幕天花里的 20–30 个金点也用它） |
| `Sea/Shaders/Lanbai_SeaDome.shader`、`Lanbai_SeaWaterline.shader`、`Lanbai_SeaShaft.shader`、`Lanbai_SeaParticles.shader`、`Lanbai_SeaCausticsCookie.shader` | 水下穹顶、车窗水线、水下光柱、海雪 / 播下的光 / 船体荧光 / 气泡、太阳的焦散 cookie（第 7 幕用，属性写在各文件头） |
| `Sea/Models/Sea_Disc.fbx` | 平的圆盘，半径 40 km，极坐标环（中心密）。ABOVE / BELOW 用 |
| `Sea/Models/Sea_Ceiling.fbx` | 半径 3.2 km 的圆盘（天花：2.7 km 处 50 %，渐隐带 500 m） |
| `Sea/Textures/SeaN_Large_1024.png`、`SeaN_Small_1024.png` | 两张可平铺的 FFT 海浪法线（64 m、9 m 平铺） |
| `Sea/Textures/SeaMacro_512.png` | 平静 / 起纹的宏遮罩（1.5 km 平铺，R：0 = 镜面，1 = 起纹） |
| `Sea/Textures/Cube_*.exr` | 云端给的**备用**立方图（从选定的两张 Syferfontein HDRI 做的）。天空交了正式的天、总控的烘焙器烘了每幕的立方图以后就不用它们 |

圆盘网格**跟着车走 xz**（跑步机：车不动，海是无限的，只有 y 和浪的平移在变）。浪的平移靠全局 `_Udon_SeaClock.yz`，不靠移动物体。

---

## 2. 模式与材质参数

所有颜色都是 **线性 Vector**（不经 sRGB 转换，和门的做法一样）。没写的参数用默认值。

### 2.1 三个模式共用

| 属性 | 默认 | 说明 |
|---|---|---|
| `_SEA`（KeywordEnum Above / Below / Ceiling） | Above | 模式 |
| `_NormalLarge` / `_NormalSmall` | SeaN_Large / SeaN_Small | 两张 FFT 法线 |
| `_LargeTile` / `_SmallTile` | 64 / 9 | 平铺（米） |
| `_LargeScroll` / `_SmallScroll` | (0.9, 0.35) / (−0.4, 0.7) | 各自的漂移（m/s，xz） |
| `_NormalStrength` | 1 | 总的法线强度 |
| `_WaveAmp` | 1 | 浪的振幅（7c 在 F8b 起 6 秒衰减到 0.3；别处 1） |
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
| `_SunDir` | (0.69, 0.10, 0.71, 0) | 指向太阳的单位向量（全局 `_Udon_SunDir.w > 0` 时用全局的） |
| `_SunGlitterRough` | 0.12 | 闪光路径的“浪坡”宽度（GGX α，越大路越宽越碎） |
| `_SunReflPeakEV` | 1.3 | **闪光路径的任何一点都比日盘暗至少这么多 EV**（圣经 E14：≥ 1.3）。shader 里是软钳位，色相不变 |

### 2.3 BELOW（第 7 幕：人在水里）

| 属性 | 默认 | 说明 |
|---|---|---|
| `_AirSide` | 1 | **+1 = 空气在平面上方**（7a：抬头看斯涅尔之窗）；**−1 = 空气在平面下方**（7c：车下的倒置斯涅尔之窗）。网格法线照旧，shader 自己翻 |
| `_WindowCube` | Cube_Dawn | 窗里看到的“另一边”的天（7a = 晨的天，7c = 暮的下半球 `ReflCube_DuskLower`） |
| `_WindowGain` | 1 | 窗的亮度（核心目标屏幕 `#E6F3F8`，填 `#D9F4FF @ +1.98`，按截图校） |
| `_Dispersion` | (1.331, 1.337) | R / B 的折射率（窗边的轻微色散）；G 用 `_IOR` |
| `_TIRColor` | (0.0222, 0.0685, 0.1651) | 全反射暗镜的颜色（7a 屏幕 `#11395E`，按调色套件改填 `#294B72`） |
| `_TIRCubeGain` | 0 | 全反射区里再加多少 `_Udon_ReflCube`（7c 映着宫殿的灯：1） |
| `_WindowEdgeSoft` | 0.6 | 窗边（临界角处）的软化，度 |

### 2.4 CEILING（第 8 幕：海之天花）

**渲染状态（总工程师 #6）**：溶化开始之前，天花只有 2.45–2.95 km 的边是半透明的。所以圆盘网格做成两块（`Sea_Ceiling.fbx` 的下一版）：**内盘 r ≤ 2.4 km 用不透明材质** `M_08_SeaCeiling`（队列 2000、`ZWrite On`、`_DiscCenter.z = 0`），**外环 2.4–3.2 km 用透明材质** `M_08_SeaCeilingEdge`（队列 2990，带 `_DiscCenter` 的渐隐）。956.36 起内盘换成透明材质 `M_08_SeaCeilingFade`，只有溶化的 9 秒付全盘混合的钱（主机位约 0.5 FSE）；外环平时只是地平线附近的一条。FSE 的实测数随第 7 幕的包给。

| 属性 | 默认 | 说明 |
|---|---|---|
| `_WaterColor` | (0.0116, 0.0296, 0.0683) | 头顶透见的深水（屏幕 `#10263F`，填 `#1C304B`） |
| `_DiscCenter` | (0, 0, 2700, 500) | 有限的圆：2.7 km 处 alpha 0.5，渐隐带 500 m（2.45 → 2.95 km） |
| `_NormalStrength` | 0.25 | 圣经：法线扰动 ≈ 0.02 rad |
| `_DissolveTime` | −1 | **天花溶化的时钟：t − 956.36（F10e）**；< 0 = 完整。驱动每帧写 |
| `_DissolveFront` | 4 | 前沿从地平线走到天顶的秒数（956.36 → 960.36） |
| `_DissolvePixel` | 5 | 每个像素自己的淡化秒数（EV 线性；≥ 5 才过爬升律） |
| `_SkyBehindCube` | Cube_Dusk | 天花后面那片天（上半球）。shader 用它算每个像素的 EV 线性 alpha |

溶化的定义（`LanbaiSea.cginc` 的 `LanbaiCeilingDissolve`，`Lanbai_SeaSpecks` 用同一个函数）：
仰角 el（度，0 = 地平线，90 = 天顶），像素进度 `p = saturate((τ − τ_front·el/90) / τ_pixel)`，τ = `_DissolveTime`。
像素的亮度沿 `L(p) = Lc^(1−p) · Ls^p` 走（Lc = 天花这个像素自己的颜色，Ls = `_SkyBehindCube` 在同一方向的颜色），alpha 由它反解；天顶的最后一个像素在 τ = 9.0（965.36）溶完，等于圣经的 ≈965.4。宫殿的灯点用 `p' = saturate((p − 0.3)/0.7)`：同一个像素里比水晚走。

### 2.5 第 11 幕变体（倒挂的海，CEILING 模式里多出来的几个参数；`Lamps/总导演意见.md` §2）

| 属性 | 默认 | 第 11 幕 | 说明 |
|---|---|---|---|
| `_GerstnerLength` | (60, 37, 23, 0.08) | 同 | 三个长浪的波长（米）+ 频率 Hz |
| `_GerstnerAmp` | (0, 0, 0) | (0.6, 0.35, 0.15) | 振幅（米）；0 = 关（第 6、7、8 幕） |
| `_GerstnerDir` | (0.94, 0.34, 0.5, 0.866) | 同 | 第 1、2 个浪的方向（世界 xz），第 3 个是两者角平分线转 90° |
| `_LampGlints` | 0 | 0..1 | 读 `_Udon_Lamp0..7` 的 GGX 闪光（光滑度 0.97 = `_Smoothness`），屏幕目标 `#D08A59`（灯与假醒按截图校 `_Udon_Lamp*.w`） |
| `_DiscCenter.z` | | 0 | 无限 |
只用浪的**斜率**（80 m 外 0.6 m 的起伏看不出高度，看得出的是灯在上面的光）。其他照 CEILING（`_DissolveTime` 保持 −1）。

---

## 3. 全局量（新加的写进 `给总控.md` 请总控登记）

| 全局量 | 类型 / 含义 | 谁写 |
|---|---|---|
| `_Udon_SeaLevel` | float：当前那块海面的世界 y（第 6 幕：云写；第 7 幕：海写；第 8 幕：云写天花的 y；第 11 幕：灯与假醒） | 当前幕 |
| `_Udon_SeaMode` | float：0 没有海、1 ABOVE、2 BELOW（7a）、3 CEILING、4 BELOW 翻转（7c） | 当前幕 |
| `_Udon_SeaClock` | float4：x = 浪的钟（秒，用时间轴 t 即可）；yz = 海水相对车的平移（世界 xz，米，= 车走过的路），**驱动对 576 m（64 与 9 的公倍数）取模再写**，不然几百米以后 float 的小数位不够、浪会抖；w > 0 = 已设。没设时用 `_Time.y`、平移 0 | 当前幕 |
| `_Udon_Underwater`（新） | float 0..1：眼睛在水里。雾和天走水下（见 `给总控.md` 对 `LanbaiFog` 的请求） | 海 |
| `_Udon_WaterFogUp` / `_Udon_WaterFogMid` / `_Udon_WaterFogDown` | 水下雾色（朝上 / 水平 / 朝下，线性）；天空 v1.1 的 `LanbaiHorizon` 已经照这个读 | 海 |
| `_Udon_T`、`_Udon_SeaBus`、`_Udon_SeaBusVel`（新，待登记） | 时间轴秒；车的原点在水的坐标系里的位置（x, −深度, 前进）；它的速度 m/s | 海（第 7 幕） |
| `_Udon_Caustics` | float4：x = 强度 0..1（已含深度衰减），y = 方向 +1 光从上来 / −1 从下来（7c），z = 焦散的钟（秒），w = 平铺缩放（1） | 海 |
| `_Udon_CausticsColor`（新） | float4：rgb = 焦散的线性颜色 × E | 海 |
| `_Udon_CausticsTex`（新） | 焦散序列帧图集（全局纹理） | 海 |
| `_Udon_SunDir` / `_Udon_SunDisc` | 已预留给天空。ABOVE 读 `_Udon_SunDir`（w > 0 时） | 天空 |

---

## 4. 第 6、8 幕怎么用（给云；第 11 幕给灯与假醒，见 §2.5）

**第 6 幕（ABOVE）**
1. 圆盘 `Sea_Disc.fbx` 放在 R_Dawn 下，xz 跟车（0, 0），y = 海面（F0 时在车下 2 606 m，随下降上升）；材质 `M_06_Sea`（模式 Above）。
2. 每帧写 `_Udon_SeaLevel` = 海面 y、`_Udon_SeaMode` = 1、`_Udon_SeaClock` = (t, 0, 0, 1)（第 6 幕车不前进，平移 0）。`_Udon_ReflCube` = 晨的立方图（从海面附近烘：要含云盖的底面）。
3. `_SunColor` = 日盘的线性值、`_SunDir` = 太阳方向；305.4 → 318.36 太阳被云盖挡住时 `_SunColor` × 同一个遮挡系数（和平行光一起，0.1 → 1）。
4. 平静：328.36（F1b2）起 `_CalmPatch` = (0, 0, 300, 0 → 1，6 秒 smoothstep)，**车正下方一块平静的海**；337.0 起 `_CalmAll` 0 → 0.85（8 秒 smoothstep）：海镜落定。入水前最后 5 秒（357.96 →）镜子填满下半个视野，靠近时反射的内容不流动——**浪的平移保持 0**。
5. 倒影太阳的钳位在 shader 里（`_SunReflPeakEV` 1.3），不用驱动管。

**第 8 幕（CEILING）**
1. 圆盘 `Sea_Ceiling.fbx` 放在 R_Dusk 下，xz 跟车，**y = 出海那一帧我写的 `_Udon_SeaLevel`**，之后按 `dusk_motion_final.json` 的 h(t) 往上退（0 → 272 m，F10e）。材质 `M_08_SeaCeiling`（模式 Ceiling），法线朝下（网格翻过来，或 x 轴转 180°）。
2. `_Udon_ReflCube` = `ReflCube_DuskLower`（天花的镜面反射的是**下面**的暮天）；`_SkyBehindCube` = 暮的上半球。
3. 溶化：956.36 起每帧写 `_DissolveTime = t − 956.36`；≥ 9.0（965.36）以后关掉 renderer。宫殿的金点：`PalaceSpecks_Points` 放在天花上方 40–200 m，材质 `Lanbai/SeaSpecks` 设 `_CeilingMode 1`，读同一个 `_DissolveTime`，自己最后走。
4. `_Udon_SeaMode` = 3；`_Udon_Underwater` = 0（出海那一帧我写 0）。

---

## 5. 交接（同一块水面，两个物体）

| 时刻 | 从 → 到 | 交接 |
|---|---|---|
| **F2h 363.26 入水** | 云的 ABOVE 平面 → 海的平面 | **两块平面永不同时存在**（总工程师 #3：共面会 z-fighting 闪）。**F2h 那一帧**云关掉自己的海、海的平面开（同一个 y、同一个材质参数，**先用 ABOVE 材质**）；眼睛下水那一帧（≈363.62 = F2h + 0.36，水线遮挡中）海的平面换成 BELOW 材质，`_Udon_Underwater` 0 → 1。`_Udon_SeaLevel` 从 F2h 起归海。`Lanbai/Sky` 在水下被穹顶挡住 |
| **F9s + 0.5 = 922.36 出海** | 海的 BELOW 翻转平面（7c，在车下）→ 云的 CEILING 平面 | 同样不并存：车（眼睛）穿过平面的那一帧（922.36）海关掉自己的平面、云开天花，我写最后一次 `_Udon_SeaLevel` = 平面 y、`_Udon_Underwater` = 0；之后归云。**雾的全局量我在那一帧不清零**（交给云的驱动接着写，总工程师建议）。水线由下往上 0.8 秒流走（车窗上的水线是我的 `Lanbai/SeaWaterline`，车厢玻璃 shader 也可以 include `LanbaiSea.cginc` 的 `LanbaiWaterline()`） |

两个时刻的具体数（平面在车坐标里的 y、速度）写进第 7 幕的布局 JSON（`Act07_Sea/Act07_Layout.json` 的 `handover` 块），推第 7a 包时一起给。
