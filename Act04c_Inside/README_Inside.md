# 第 4c 幕（门内）+ 第 5 幕（投入）+ 天窗光斑 · 包说明

写的人：云端会话「门内」，2026-10-23。依据：圣经 v2.1 §1.8、§3、§4.8、§6·4c、§6·5、§6.x 第 12–17 行、§8.1 #6；`CONTROL_总控.md`；总导演意见（`总导演意见.md`）。
**没在 Unity 里编译过。** shader 只用 slang 查过语法和类型，C# 只用 Roslyn 对 Unity 2021.1 的引用程序集加 UdonSharp / VRC / PPv2 的桩做过类型检查（§8）。第一次导入，请把 Console 原样推回 `FromLocal/04c_test/`。
设计和每一条评审的处理：`Docs~/DESIGN_4c.md`（v2）、`Docs~/review_design_r1.md`、`Docs~/review_art_r03.md`。迭代：`Docs~/iterations/`。

## 0. 拷什么、点什么、截什么

1. 拷贝：`Act04c_Inside/` → `Assets/Lanbai/Act04c_Inside/`，`Overlay/` → `Assets/Lanbai/Overlay/`（遮罩 v2，第 5 幕的黑要用；它的编辑器脚本也被这里的搭建菜单调用）。还需要：`Common/Shaders/LanbaiVR.cginc`（main 里有）和天空的 **`Common/Shaders/LanbaiFog.cginc` + `LanbaiSky.cginc` v1**（在 `pkg/sky`，合进 main 之前先从那个分支拿）。`Tools~`、`Docs~` 带 `~`，Unity 不导入。
2. **项目设置**：Player → Vertex Compression 里**不要勾 TexCoord0–3**（门的测试已经要求过；这里 UV1 存“到撕边的米数 / 沿撕边的米数”，丝线的运动存在 UV1–3）。
3. 导入设置由 `Editor/LanbaiInsideImport.cs` 自动设（只管这个文件夹）：网格不压缩、不生成光照 UV、不导材质；贴图线性、BC7、毛边贴图 U 重复 V 夹住。
4. 菜单 **蓝白/Build/Overlay**（如果还没建过遮罩），然后 **蓝白/Build/04c 门内**：建 `Lanbai_Inside`：
   - `InsideRoot`：8 重光唇 + 袖，`Lanbai/InsideLip`，开始时**不激活**，由驱动打开；
   - `Inside_BusAnchored`：穹、松散的丝线、暖白点，跟着车；
   - `LanbaiInsideDriver`（UdonSharp）和它的程序资产。字段由 `Editor/InsideLayoutData.cs` 填，这个文件由 `InsideLayout.json` 生成。
   搭完**手动**连三个引用：驱动的 `overlay`（场景里的 `Lanbai_Overlay`）、`exposure`（`Lanbai_Grades` 上的 `LanbaiExposure`）、`worldMainLight`（世界主光）。然后把驱动加进 Director 的分发层。
5. **天窗光斑（第 4 幕 U8 → U9）**：把 `FBX/Skylight_Spot.fbx` 放在车下（车坐标 = 世界坐标，位置 0、旋转 0）。三个物体 Spot / Beam / Dust 用 `Lanbai/SkylightSpot`，Part 分别选 Spot / Beam / Dust。网格 bounds 要设大（顶点每帧在 shader 里算；`LanbaiInsideImport` 没管这个 FBX 的 bounds，请在 Mesh Renderer 上勾 “Update When Offscreen” 或者手动把 bounds 设成 20 m）。加 `LanbaiSkylightSpot`（U#），`renderers` 填这三个。它读门每帧写的 `_Udon_TearPos`、`_Udon_TearH`。
6. **截图推回来**（主座位，桌面 1920×1080、水平 90°，渲进 ARGBHalf 再过 PPv2；VR 用左眼另截一张量 APL）：

| t | 机位 | 看什么、量什么 |
|---|---|---|
| 181.0 | 正前 | 刚进门：第 2 重在眼前；雾 ≈ `#1D2336` |
| 197.0 | 正前 | 暖白点刚出现在深处，偏左上，四周是错开的几层开口 |
| 205.0 | 正前 | 第 6 重；暖白点在开口的另一侧 |
| 218.75 | 正前 | 第 8 重框住暖白点（开口上半） |
| 226.0 | 侧窗、车门、天窗 | 袖：撕开的厚布的断面、长纱；车厢上的瓶覗光带 |
| 240.0 | 正前 | 尾声：雾、暖白点、表盘、暗车厢 |
| 246.4 | 正前 | 闪光前的静 |
| 248.29 | 正前 | 闪光的峰（量 APL，VR 必须 ≤ 150） |
| 248.64 | 正前 | 全黑 `#030409` |
| 169.2 | 过道 (0.05, 2.00, −1.60) 右 6° 俯 13° | 天窗光斑最亮（luma 170–200） |

另请录三段 60 fps 的 PNG 序列跑 `Art/tools/lens_tech/flashcheck.py`：179–182（进门）、224–232（袖）、246–249（闪光 → 黑）。

## 1. 它是什么

门里面是暗的。一层层撕开的布在前方错开着退去，每一层的边亮着细细的纤维，一层比一层白、一层比一层淡：从一丝紫到瓶覗；车厢暗了，收音机的表盘是唯一的暖；最深处一个暖白点在等你。第 8 重是一整块很厚的布（“袖”），长音 *Leben* 的 6.25 秒里车在它的断面之间穿过。尾声 14.8 秒只有雾、暖白点和车厢。246.39 一切停止变化；247.89 唯一的授权闪光；248.64 全黑（剪 1）。

## 2. 运动（`InsideLayout.json` → `motion`）

- v(t) = v_g + (12 − v_g)·ss((t − U9)/(U_voiceEnd − U9))，之后 12 m/s。v_g = 2700/(U9 − U6) = 59.0164 m/s（与门一样）。
- **闭式（门要照抄的那一行）**：τ = t − U9，T = U_voiceEnd − U9，x = τ/T：
  `s = v_g·τ + (12 − v_g)·T·(x³ − x⁴/2)`（τ ≤ T）；`s = v_g·T + (12 − v_g)·T/2 + 12·(τ − T)`（τ > T）；`s = v_g·τ`（τ < 0）。
- `InsideRoot.localPosition = (0, 0, −s)`。**门：U9 以后 `GateRoot.z = −s(t)`（同一个式子），裂口和第 1 重焊在一起。**
- 指尖卷回（归门）：第 1 重唇在 InsideRoot 本地 z = 0（世界 z = −s(t)），开口就是裂口透镜的轮廓（`tear_def.lips`，车在 15% 高度进入）；指尖贴在这个平面背后（z < 0 一侧）2–8 m，U9 → U9 + 6 s 卷回。

## 3. 八重光唇（数据：`InsideLayout.json` → `lips`、`sleeve`）

见 `Docs~/DESIGN_4c.md` §2 的表（s、高度、网格、旋转、偏移、净空、暖白点的位置都由 `Tools~/inside_layout.py` 求解并核对）。三种开口都由“撕裂段”组成（沿纱线直走、跳纱错一步），没有椭圆、没有透镜形、没有星形。每一重 = 不透明的布（铺到 2.2 km，雾 0.0035 下边看不见）+ 一圈毛边 + 少数下垂的长纱 +（窄端的）横纱。

| 部件 | 材质要点 |
|---|---|
| Sheet | 内面屏幕 `#1A2030`（填 `#262F3F`），竖向纤维纹，纹理方向跟这一重的旋转走；撕边上一道细的唇光（纤维填色 × 1，宽 0.25% H）+ 8% H 宽的透光带（× 0.10，顺经纱）+ 从撕边放射出去的张力褶（±12%）；**雾封顶 0.55**：布永远比它后面的空气暗 |
| Fringe | 纤维沿经或纬（哪个更朝开口里就沿哪个），长 0.5% H（1.5–5 m），每 25–90 m 一段空缺；加色 |
| Hang | 每重 ≤ 14 根从上缘垂下的长纱（2–5% H），加色 |
| Threads | 窄端没断的深色纬纱，边上透光 |
| Lip8_Ply0..4 + Lip8_Wall | 袖：入口、出口发光；中间 3 层暗（× 0.12，没有毛边，两层是不合拢的布片）；38 条被拉出来的长纱（纤维色 × 0.25） |
| Dome | 跟车的 2.4 km 球，画 `LanbaiHorizon(dir)`（无穷远的雾），写深度 |
| Dot | 暖白点：天上的东西，不吃雾，方位 −6.5°、仰角 +4°、2.3 km；核 0.3° → 0.9°、辉光 4° → 12°；核 `#FFC187 @ +2.79`，辉光颜色不那么橙（线性 × (1, 0.86, 0.70)） |
| Loose | 90 根松散丝线，车坐标里朝前慢漂，颜色 = 当前纤维 × 0.25 |

纤维填色：第 1 重 `#DFCFFF @ +1.96`、第 4 重 `#CBD8FF @ +1.78`、第 8 重 `#BCEAFF @ +1.29`（圣经），中间按对数插值（JSON 里每一重都有线性值）。

## 4. 雾（天空的 `LanbaiFog` v1，“渐变”模型 B）

驱动每帧写：`_Udon_FogDensity`（U9 → U9 + 2 s 从 0.0006 到 0.0035）、`_Udon_FogBandDir` = +Z、`_Udon_FogBandColor` = 前方的区色 × 1.10、`_Udon_HorizonColor` = (身后的区色 × 0.80, a = 2)、`_Udon_ZenithColor` = 当前 × 0.88、`_Udon_NadirColor` = 当前 × 0.80、`_Udon_FogBandWidth` = 180、`_Udon_FogShape` = (25, 90, 1, 0)、`_Udon_FogBelow` = (−90, −15, 1, 0)；`RenderSettings.fogColor` = 当前区色、`fogDensity` 同上。区色从 `#1D2336`（填 `#2A3347`）到 `#53606E`（填 `#6E808D`），在相邻两重之间按 s 平滑过渡（`InsideLayout.json` → `fog.zones`）。

## 5. 车厢（给 `Lanbai/Cabin`，总导演在做）

- `_Udon_CabinAmbient`：门的 `#232A3A` × 0.3 → `#B5C3DB` × 0.30（灰卡 `#1E212B`），Trilight 门的三色 → `#3D4863` / `#4C5979` / `#1F283B`，世界主光 1.0 → 0.001：都在 180.05 → 188.05（与 S4 → S4c 同一条 smoothstep）。
- 穿越光带 `_Udon_CabinSlice` / `_Udon_CabinSliceColor`（总导演已批的接口）：前沿 1.5 m 软边 + 3.5 m 指数拖尾，从车头 +3.6 扫到车尾 −4.0；第 1 重 180.15 起，扫过 1.2 / 1.2 / 1.3 / 1.5 / 1.7 / 1.9 / 2.1 s；第 8 重 2.4 s 扫进来盖满（w = 1），228.6 起从车尾往车头退 2.4 s（w = −1：前沿**前面**亮）。颜色 = 线性 E × 纤维色，按“灰卡 ≤ luma 120”在 S4c 下解出（JSON 的 `band_colour_linear`）。
- `_Udon_RadioDial`：196.1 → 199.1 从 `#FF7703 @ +0.71` 线性到 `#FF7B00 @ +2.13`（屏幕 `#F2B169`），248.39 → 248.64 随黑降到 0，此后永不再亮。

## 6. 第 5 幕

- `LanbaiDeltaEV(t)`：247.89 → 248.29 0 → +1.5 EV 线性，保持到 248.39，248.39 → 248.64 回到 0。**分发层把它和别的事件加起来写一次 EXPO**；单独测试时勾 `writeExposure`。
- 黑：248.39 → 248.64 遮罩 EV 线性从画面到 `#030409`（S4c 填 `#030400` × 2^(−ΔEV)），248.64 同一帧换 S6 的 `#090200`（分发层同一帧硬切 S4c → S6）；遮罩保持到 F0 + 1.0，交给第 6 幕。
- 248.64 在黑下关 `InsideRoot`（`LanbaiActivate(false)`）。

## 7. 新的全局量（总导演已登记）

`_Udon_InsidePortal`、`_Udon_InsideDot`、`_Udon_InsideFibre`、`_Udon_InsideClock`、`_Udon_InsideFog`、`_Udon_CabinSlice`、`_Udon_CabinSliceColor`、`_Udon_RadioDial`；天窗光斑另加 `_Udon_SkySpot`（x = 亮度包络，**请登记**）。

## 8. 检查

| 检查 | 怎么跑 | 结果 |
|---|---|---|
| shader | `~/bpy/bin/python Tools~/compile_check/check_shaders.py` | slang：InsideLip 6 个 Part、SkylightSpot 3 个 Part、Overlay 全过；lint（Header、先用后声明）过 |
| C# | `CSC=… Tools~/compile_check/check_cs.sh` | 运行时 4 个、编辑器 4 个文件过（C# 9，警告当错误） |
| 布局 | `~/bpy/bin/python Tools~/inside_layout.py` | 净空、偏移、暖白点视线、框住、交替：全过（`Tools~/out/layout_solved.json`） |
| FBX 读回 | `~/bpy/bin/python Tools~/inside_mesh.py` | 26 / 26 个网格位置一致 |
| 天窗光斑投影 | `~/bpy/bin/python Tools~/skylight_check.py` | 与门的 25 个采样最大差 0.5 mm |

## 9. 已知弱点（实话）

见文末（每轮迭代后更新）。
