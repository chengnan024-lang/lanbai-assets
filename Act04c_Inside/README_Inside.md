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
   - `Inside_BusAnchored`：穹、松散的丝线、暖白点，跟着车；**开始时也不激活**，和 `InsideRoot` 一起由驱动的 `LanbaiActivate` 开关（总导演终审 #1：2.4 km 的穹是不透明、写深度的，开着就把全片的天盖住）。shader 在门户没生效时也把它们塌缩（双保险）；
   - `LanbaiInsideDriver`（UdonSharp）和它的程序资产。字段由 `Editor/InsideLayoutData.cs` 填，这个文件由 `InsideLayout.json` 生成。
   搭完**手动**连三个引用：驱动的 `overlay`（场景里的 `Lanbai_Overlay`）、`exposure`（`Lanbai_Grades` 上的 `LanbaiExposure`）、`worldMainLight`（世界主光）。然后把驱动加进 Director 的分发层（它有 `LanbaiTick / LanbaiActivate / LanbaiWindow / LanbaiGrade`；闪光 FLASH_TEAR 走 `LanbaiGrade`，本地 `ApplyGrades` 里自己那份要删）。
   **重新点搭建菜单**会保留旧驱动上手动接的 `overlay` / `exposure` / `worldMainLight`、`tLichtDial` 和两个开关；点完请重跑 **蓝白/Director/2 Wire Scene**（驱动和天窗光斑是新物体）。
   **`writeRenderSettings`、`writeMainLight` 默认关**：本地把第 4c、5 幕的窗口（177.55 → 252.64）加进 `extWindows`、勾上 `extAtmosphere` / `extSun` 以后再勾这两个，不然两边每帧写同一个量。环境光的三色写法要本地的环境光模式是 **Trilight**。
   窗口从 177.55 开始（门的窗口里）：那一帧 `InsideRoot` 打开，但车还在裂口平面前面，门内的一切在顶点阶段塌缩，画面不变。
5. **天窗光斑（第 4 幕 U8 → U9）**：同一个搭建菜单一起建（`Skylight_Spot` + `LanbaiSkylightSpot`，三个材质 `M_04c_Skylight_*`，renderers 已填）。网格 bounds 由 `LanbaiInsideImport` 在导入时设成过道 + 天窗光柱的体积（顶点每帧在 shader 里算）。它读门写的 `_Udon_TearPos`、`_Udon_TearH`；门没写（w ≤ 0）或包络为 0 时 shader 什么都不画。renderers 开始时关，由 U# 开关。
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
- 指尖卷回：**待定（门第 10 轮，总导演 10-23 裁决这次不做）**。门内这边不为它留任何东西。

## 3. 八重光唇（数据：`InsideLayout.json` → `lips`、`sleeve`）

见 `Docs~/DESIGN_4c.md` §2 的表（s、高度、网格、旋转、偏移、净空、暖白点的位置都由 `Tools~/inside_layout.py` 求解并核对）。三种开口都由“撕裂段”组成（沿纱线直走、跳纱错一步），没有椭圆、没有透镜形、没有星形。每一重 = 不透明的布（铺到 2.2 km，雾 0.0035 下边看不见）+ 一圈毛边 + 少数下垂的长纱 +（窄端的）横纱。撕边离开布面卷曲（沿边的多尺度噪声，环上无缝，幅度 1.6% H）。

**同时看得见的光唇 ≤ 3（圣经，r06；回头看也成立：已穿过的光唇在身后 300 m 内淡出，第 8 重从袖的出口算起，总导演终审 #4）**：最近的两重全显；第三重在“上一次穿越 → 下一次穿越”之间按 smoothstep 渐显；更远的光 × 0、布的雾封顶 → 1（完全融进雾）。穿过一重的那一刻，第三重正好到 1、变成第二重，所以没有跳变。驱动每帧对每重的材质写 `_Gain` 和（布）`_FogCap`，只写变了的（`LipVisible()`，和 `Tools~/inside_drive.lip_visibility` 同一个式子）。**注意：这是直接改共享材质，编辑器里 Play 过后材质资产上的值会留着；重新点一次搭建菜单就复原。**

| 部件 | 材质要点 |
|---|---|
| Sheet | 内面屏幕 `#1A2030`（填 `#262F3F`），很淡的经纱纹（对比 0.12），纹理方向跟这一重的旋转走；撕边上一道细的唇光（纤维填色 × 3，宽 0.2% H）+ 8% H 宽的透光带（× 0.10，顺经纱）+ 从撕边放射出去的张力褶（±28%，沿边周期 0.02 H）；**雾封顶 0.30**：布永远比它开口里的空气暗 12–20 luma |
| Fringe | 纤维沿经或纬（哪个更朝开口里就沿哪个），长 0.5% H（1.5–5 m），每 25–90 m 一段空缺；加色，× 2.6 |
| Hang | 每重 ≤ 14 根从上缘垂下的长纱（2–5% H），加色 |
| Threads | 窄端没断的深色纬纱，边上透光 |
| Lip8_Ply0..4 + Lip8_Wall | 袖：入口、出口发光；中间 3 层暗（× 0.12，没有毛边，两层是不合拢的布片），每层整体有 2.5–5 m 的缓慢起伏；90 根被拉出来的发丝（0.12–0.45 m 宽，每根只占深度的 25–60%，断头下垂，纤维色 × 0.03–0.10） |
| Dome | 跟车的 2.4 km 球，画 `LanbaiHorizon(dir)`（无穷远的雾），写深度 |
| Dot | 暖白点：天上的东西，不吃雾，方位 −6.5°、仰角 +4°、2.3 km；核直径 0.3° → 0.9°、辉光**直径** 4° → 12°（D-20：圣经 §1.8 的上限，按直径）；作为眩光画在 40 m 处、**每只眼各自锚定**（零视差，融合在无穷远，不在开口边的前面；方向按两眼中点）；核 `#FFC187 @ +2.79`，辉光颜色不那么橙（线性 × (1, 0.86, 0.70)），剖面 (1−r)^1.5 × 软边、亮度 × 0.32 |
| Loose | 90 根松散丝线，车坐标里朝前慢漂，颜色 = 当前纤维 × 0.25 |

纤维填色：第 1 重 `#DFCFFF @ +1.96`、第 4 重 `#CBD8FF @ +1.78`、第 8 重 `#BCEAFF @ +1.29`（圣经），中间按对数插值（JSON 里每一重都有线性值）。

## 4. 雾（天空的 `LanbaiFog` v1，“渐变”模型 B）

**交接（D-22，总导演终审 #2、#3）**：门的驱动只在 [U6, U9) 写天、雾、月、星；从第一次 t ≥ U9 的 tick 起，这里每帧写整组：`_Udon_Fog` = (密度, 0, 0, 1)、`_Udon_FogModel` = (1, 0, 0, 1)（B 渐变）、`_Udon_FogBase` = 0（不设：按眼睛高度）、`_Udon_FogCubeParams` = 0、`_Udon_StarGain` / `_Udon_GalaxyGain` = (0, 0, 0, 1)（布里面没有星）。`LanbaiActivate(false)` 时交还：门户 = 0、暖白点 = 0、上面这些通道 w = 0（下一幕的写法或默认值生效）。

驱动每帧写：`_Udon_FogDensity`（U9 → U9 + 2 s 从 0.0006 到 0.0035）、`_Udon_FogBandDir` = +Z、`_Udon_FogBandColor` = 前方的区色 × 1.0、`_Udon_HorizonColor` = (身后的区色 × 0.72, a = 2)、`_Udon_ZenithColor` = 当前 × 0.85、`_Udon_NadirColor` = 当前 × 0.80、`_Udon_FogBandWidth` = 100、`_Udon_FogShape` = (25, 90, 1, 0)、`_Udon_FogBelow` = (−90, −15, 1, 0)；`RenderSettings.fogColor` = 当前区色、`fogDensity` 同上。区色从 `#1D2336`（填 `#2A3347`）到 `#53606E`（填 `#6E808D`），在相邻两重之间按 s 平滑过渡（`InsideLayout.json` → `fog.zones`）。

**尾声（r06）**：出袖（231.0）以后 4 s 内，渐变的方向从 +Z 转到暖白点的方位（−6.5°），带宽 100° → 40°，侧面 × 0.45，上下 × 0.38，天顶 / 天底的起点 25° → 8°、−15° → −6°：正前方仍是圣经的 `#53606E`，画面边缘落到 luma ≈ 50，尾声 APL 63 → 51.6（目标 53）。

## 5. 车厢（给 `Lanbai/Cabin`，总导演在做）

- 穿越光带的颜色（D-08，总导演终审）：取纤维色的色相、按“灰卡在屏幕上 C* ≤ 12、h ≤ 290”去饱和（第 1–3 重原来是丁香紫 C* 14–19），亮度仍按灰卡 luma 120 解（`Tools~/build_json.py` 的 `band_colour`）。
- `_Udon_CabinAmbient`：门的 `#232A3A` × 0.3 → `#B5C3DB` × 0.30（灰卡 `#1E212B`），Trilight 门的三色 → `#3D4863` / `#4C5979` / `#1F283B`，世界主光 1.0 → 0.001：都在 180.05 → 188.05（与 S4 → S4c 同一条 smoothstep）。
- 穿越光带 `_Udon_CabinSlice` / `_Udon_CabinSliceColor`（总导演已批的接口）：前沿 1.5 m 软边 + 3.5 m 指数拖尾，从车头 +3.6 扫到车尾 −4.0；第 1 重 180.15 起，扫过 1.2 / 1.2 / 1.3 / 1.5 / 1.7 / 1.9 / 2.1 s；第 8 重 2.4 s 扫进来盖满（w = 1），228.6 起从车尾往车头退 2.4 s（w = −1：前沿**前面**亮）。颜色 = 线性 E × 纤维色，按“灰卡 ≤ luma 120”在 S4c 下解出（JSON 的 `band_colour_linear`）。
- `_Udon_RadioDial`：196.1 → 199.1 从 `#FF7703 @ +0.71`（线性 1.636, 0.302, 0.0015）线性到 `#FF7B00 @ +2.13`（4.377, 0.867, 0；屏幕 `#F2B169`），248.39 → 248.64 随黑降到 0，此后永不再亮。两个值由搭建菜单从 `InsideLayoutData` 填（和 Python 模型同一个来源；总导演终审指出原来的底值写成了 1/4）。`tLichtDial` = 196.10 是参数，本地听了再定（D-16）。

## 6. 第 5 幕

- **暖白点在闪光里放大（D-20）**：授权的 0.4 s 升起里，辉光直径 × (1 + 1.5 k)、亮度 × (1 + k)，k = ΔEV / 1.5，亮度集中到暖白点方向（读成“光淹没玻璃”），`_Udon_InsideDot.w` 是辉光倍数。参考帧 `Docs~/iterations/15_flash/`（247.90 / 248.29 / 248.50 / 248.64：APL 55.7 / 94.9 / 27.0 / 4.3）。
- `LanbaiDeltaEV(t)`：247.89 → 248.29 0 → +1.5 EV 线性，保持到 248.39，248.39 → 248.64 回到 0。**分发层把它和别的事件加起来写一次 EXPO**；单独测试时勾 `writeExposure`。
- 黑：248.39 → 248.64 遮罩 EV 线性从画面到 `#030409`（S4c 填 `#030400` × 2^(−ΔEV)），248.64 同一帧换 S6 的 `#090200`（分发层同一帧硬切 S4c → S6）；遮罩保持到 F0 + 1.0，交给第 6 幕。
- 248.64 在黑下关 `InsideRoot`（`LanbaiActivate(false)`）。

## 7. 新的全局量（总导演已登记）

`_Udon_InsideDot`：x 核直径（度）、y 辉光**直径**（度，≤ 12）、z 增益、**w 闪光里的辉光倍数**（1 平时，D-20）。

`_Udon_InsidePortal`、`_Udon_InsideDot`、`_Udon_InsideFibre`、`_Udon_InsideClock`、`_Udon_InsideFog`、`_Udon_CabinSlice`、`_Udon_CabinSliceColor`、`_Udon_RadioDial`；天窗光斑另加 `_Udon_SkySpot`（x = 亮度包络，**请登记**）。

## 8. 检查

| 检查 | 怎么跑 | 结果 |
|---|---|---|
| shader（全仓的检查） | `~/bpy/bin/python Common/Tools~/compile_check/check_shaders.py Act04c_Inside Overlay` | `3 files, 38 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 4 warnings. NOT a Unity compile.` 警告：遮罩的 `ZTest Always`（允许的）；SkylightSpot 一条“自己声明 `_Udon_TearPos`”（文件里没有这个声明，像是误报）；`_Udon_SkySpot`、`_Udon_InsideGrade` 已登记（D-16）但生成的 `LanbaiGlobals.cginc` 还没重新生成，所以包里用同样的 `LANBAI_DECL_` 保护各自声明一次 |
| shader（包里自己的） | `~/bpy/bin/python Tools~/compile_check/check_shaders.py` | slang：InsideLip 6 个 Part、SkylightSpot 3 个 Part、Overlay 全过 |
| C#（全仓的检查） | `bash Common/Tools~/compile_check/check_cs.sh Act04c_Inside Overlay Grading/Runtime` | `C# CHECK OK (0 assembly error(s), 0 lint warning(s))` |
| C# | `CSC=… Tools~/compile_check/check_cs.sh` | 运行时 5 个、编辑器 4 个文件过（C# 9，警告当错误） |
| 布局 | `~/bpy/bin/python Tools~/inside_layout.py` | 净空、偏移、暖白点视线、框住、交替：全过（`Tools~/out/layout_solved.json`） |
| FBX 读回 | `~/bpy/bin/python Tools~/inside_mesh.py` | 33 / 33 个网格位置一致 |
| 天窗光斑投影 | `~/bpy/bin/python Tools~/skylight_check.py` | 与门的 25 个采样最大差 0.5 mm |
| 闪光（D-20 以后：245.9 → 249.3，60 fps；247.88 → 248.65 每帧单独渲（暖白点在放大），其余用冻住的一帧；× 2^ΔEV + 黑遮罩 + S4c → S6 硬切；`Tools~/flash_seq.py flashdyn`） | `Docs~/flashcheck/flash_dyn_245.9-249.3_60fps.json` | WCAG PASS、闪光规则 PASS（1 次）、上升 1.05 EV / 0.25 s、1.66 EV / 1 s（授权的 FLASH_TEAR）、峰值 APL 109（≤ 150） |
| 闪光（D-20 以前） | `Tools~/flash_seq.py flash …` → `Art/tools/lens_tech/flashcheck.py` | WCAG 2.3.1 PASS；蓝白闪光规则 PASS（任一秒最多 1 次）；上升 0.92 EV / 0.25 s、1.45 EV / 1 s（授权的 FLASH_TEAR，ramp law 标 FAIL 是预期的）；峰值 APL luma 105（≤ 150） |
| 进门 179.6–182.6（30 fps）、袖 224–232（15 fps） | `Tools~/render/seqs.sh`（320×180）→ flashcheck；`Docs~/flashcheck/` | 进门：WCAG PASS、蓝白闪光规则 PASS（任一秒 1.5 次）、ramp law PASS、峰值 APL 48；袖：WCAG PASS、闪光规则 PASS（1 次）、ramp law PASS（上升 0.33 EV / 1 s）、峰值 58。**注意**：这两段序列是在 r09 → r12 改材质的同时在后台渲的，前后帧不全是同一版外观（差别是布面的褶和透光，不影响闪光）；进门前半秒是门的画面，Blender 这边画不出来，只能从 U9 起 |
| 第 2、3 重 182–187、第 4 重 193–195（60 fps，总导演终审要的补段） | `Tools~/render/seqs.sh` 同样做法；`Docs~/flashcheck/` | 182–187：WCAG PASS、闪光规则 PASS（任一秒 1 次）、ramp law PASS（上升 0.63 EV / 1 s）、峰值 APL 48；193–195：WCAG PASS、闪光规则 PASS（0 次）、ramp law PASS、峰值 44 |

## 9. 参考图（`Docs~/iterations/12_lock/`，PPv2 模拟调色后，960×540）

| t | 机位 | APL（目标） | 说明 |
|---|---|---|---|
| 181.0 | 正前 | 29.1（31） | 只有第 2、3 重 |
| 197.0 | 正前 | 34.5（39） | 暖白点刚出现；布上有横着撕口的软褶、撕口附近斑驳的透光（`crop_197.png`） |
| 200.0 | 正前 | 33.8（41） | 见 §12 |
| 205.0 | 正前 | 39.8（43） | 开口在下面通到窗台，暖白点在上半、偏一边 |
| 218.75 | 正前 | 50.8（47） | 第 8 重铺满画面 |
| 226.0 | 正前 / 侧窗 | 52.5 / 39.1（49） | 袖里：正前方飘着的纤维和暖白点；侧窗是近处厚布的断面 |
| 228.0 / 231.0 | 正前 | 54.2 / 54.6（49 / 50） | 袖的正中、出口 |
| 240.0 / 246.4 | 正前 | 52.9 / 52.9（53 / 54） | 尾声：朝暖白点的径向雾 |

迭代 01 → 12，每轮 `note.txt`；美术评审 r03、r05、r06、r08、r09、r10 = FAIL，**r11 = 有条件通过**（`Docs~/review_art_r11.md`），r12 按它的“锁定前要修”改完。陌生人测试：`Docs~/stranger_tests.md`。

## 10. 性能（FSE 是标准台量的；其余是估算，**没在头显里量过**）

| 项 | 数 | 估算 |
|---|---|---|
| 三角形 | 约 11.2 万（布 8.6 万、毛边 1.6 万、袖墙 0.4 万、穹 0.2 万、其余 0.4 万） | 顶点很便宜；看不见的光唇按 InsideRoot 下的 renderer 照样画（布是不透明的，Early-Z 挡掉后面的） |
| draw call | 36 个物体 → 约 36 | 都是同一个 shader，不同材质（每重一套，驱动要单独写 `_Gain`） |
| 不透明 | 每个像素最多 1 层布 + 穹（布从近到远排，Early-Z） | 片元：两次纹理 + 一次折痕纹理 + LanbaiFog ≈ 0.6–0.9 ms @ 9 MP |
| 透明（FSE，**量过**：标准台 `--fse`，`Docs~/fse/`） | 毛边、长纱、横纱、袖墙、松散丝线、暖白点：181.0 → 0.020、193.9 → 0.021、215.0 → 0.032、226.0 → 0.053、231.0 → 0.057；任一像素最多 2 层 | 加车厢玻璃 0.7（账本统一加）约 0.76 FSE（预算持续 4、峰值 7、每像素 8 层） |
| Udon | 每帧：s(t)、雾 12 个全局量、暖白点、车厢、只在变化时写材质的 `_Gain`（平时 0–3 个） | < 0.1 ms |
| 天窗光斑 | 3 个物体，顶点阶段投影；光柱加色 4 个面 | 只在 U8 → U9 开着 |

## 11. 已知弱点（实话）

1. **没在 Unity 里编译、跑过。** 所有颜色、APL 都是 Blender + PPv2 模拟出来的；Unity 里的雾（LanbaiFog v1）和这里的节点版本只在公式上对齐。
2. **陌生人还没说出“布”**（16 人里 0 个；“撕裂”3 个；暖白点是终点 16 / 16）。 r03 岩石 / 冰 → r05 帷幕 / 玻璃上的裂口 → r06 裂缝 / 岩壁（`Docs~/stranger_tests.md`）。暖白点每次都是视线的终点、被裂开的边框住。布的质感在 640 px 下读不出来；在头显里布有视差和缓慢的卷曲，可能好一些，但没验证。
3. 美术评审：r05、r06、r08 = FAIL，r09 见 `Docs~/review_art_r09.md`。没做的：尾声幽灵纤维的先后、226 那条竖线压暗。
4. 218.75 第 8 重铺满画面、不是“框住”：圣经的 H = 195 m 和这个时刻决定了它在 ~100 m 外，张角约 90°。框住的那几秒在 212–216。
5. 226 侧看偶尔有一条竖线：是车正要穿过的那层内层布的侧面，约 0.3 s。
6. 驱动直接改共享材质的 `_Gain`：编辑器里 Play 过后材质上的值会留着（重新点搭建菜单复原）。
7. 进门（179–182）、袖（224–232）的 flashcheck 序列没跑完（§8）。
8. 车厢光带、表盘只写了接口，画面里的车壳是 harness 的占位（窗框、黑柱不是设计）。
9. 松散丝线（90 根）从 r08 起在参考图里；袖里 × 7。
10. **228（袖的正中，全曲最响的 *Leben*）正前方几乎只有雾和暖白点**（美术审片预审 #2）。r07 把袖里的空气压暗 × 0.75（APL 62.5 → 54.2，目标 49；出袖 2.5 s 内回升 0.41 EV），但正前方还是没有布的结构：出口开口在 ~60–85 m 外比画框大，内层的两片布片不在正前方。下一轮的办法：让内层布片（净空 41–56 m）落在正前方画框的边上（50–80 m 外、40 m 净空的边在 ±34°，在 90° 画框里），重解袖的内层。代价：226 侧窗 APL 38.4（目标 49，低 22%）。
11. 尾声的纤维色 ΔE 12–14：尾声画面里没有纤维了（只有雾和暖白点），这一项按设计不适用。

## 12. 与评审的分歧

- **“第 7 重的开口中心离暖白点 ≥ 60% 半宽”（美术评审 r08 B1）**：求解器在 200 / 205 / 210 三个时刻要求 ≥ 0.75 和 ≥ 0.8，**都无解**。满足 40 m 净空（VR 铁律）、暖白点的核心始终在开口里（被布挡住再出现就是一次闪）、H = 285 m 的第 7 重候选里，最好的就是现在的 0.68。`Tools~/inside_layout.py` 里留着这个检查（`LIP7_OFF_MIN`、报告最好值）。
- **“200 的 APL 34.0 低于 41 的 −15%”（美术评审 r09 B4，r10 判为合理）**：±15% 的下沿是 34.6，差 0.3–0.6 luma，在 json 与 PNG 两种量法的差之内；圣经自己给第 5 重测试帧的 APL 就是 34；197 → 200 → 205（34.9 → 34.3 → 40.3）看不出凹下去。（之前写的“去掉占位车厢”那条理由不成立：圣经 611 行规定第 4c 幕的车厢是暗剪影 `#0C0E14` × 0.30，真车壳不会更亮，已撤回。）评审 r09 建议的“只在 200 抬第 7 重内面 3 luma”没做。
- **“226 侧窗 APL ≥ 42”（美术评审 r08 B3）**：§2.2 的 APL 目标按正前方写；正前方 226 是 52.5（目标 49）。侧窗里是近处厚布的断面（袖里本来就该暗），内层布已经 × 1.35，侧窗只从 38.4 到 39.1。

- **“上缘画一条悬链下垂”（r05 2b、r06 B2c）**：布铺到 2.2 km，没有上缘；画面里那几条直线是车窗的边。没做。
- **“205 的第 7 重往外移 40%”（r05 #3、r06 B1a）**：选了评审给的方案 (b)：第 8 重延后出现（第 7 重的极限见上一条）。
- **“内层布 ≤ 15% 的亮度”（设计评审 r1）vs “每一条边都要亮的纤维”（美术评审 r06 S3）**：取了中间，内层布边 0.30（唇光已 × 3，所以相对入口仍是 30%）。
- **尾声 APL 与雾色**：r05 我说两者冲突；评审说用径向渐变就不冲突。评审对：r06 起正前方仍是 `#53606E`，APL 51.6 / 53。

## 13. 总工程师意见第 1 轮的处理（`总工程师意见.md`）

| # | 意见 | 处理 |
|---|---|---|
| 一.1 | 曝光接口名对不上 Director v1 | 加了 `public float[] LanbaiGrade(float t)`（{ΔEV, 0, 0, 1} 或 null）；`LanbaiDeltaEV` 留给遮罩补偿 |
| 一.2 | RenderSettings / 主光默认就写 | `writeRenderSettings`、新加的 `writeMainLight` 默认 false；§0 第 4 条写了什么时候勾、Trilight 模式 |
| 一.3 | U9 前后两个驱动都写雾带 | 我这边不变（U9 以前只写门户）；门那边 U9 以后不写，由总工程师协调 |
| 一.4 | 全局量没登记 | `_Udon_SkySpot`、`_Udon_InsideGrade` 写进 `给总控.md` |
| 一.5 | shader 自己声明 `_Udon_*` | 三个 shader 都改成 include `LanbaiGlobals.cginc`；还没登记的两个名字用同样的 `LANBAI_DECL_` 保护自己声明（生成的文件以后会先到）。另：天空的 `LanbaiFog.cginc` 对 `_Udon_FogDensity` 用的是 `LANBAI_FOG_OWN_DENSITY` 而不是 `LANBAI_DECL__Udon_FogDensity`，和 `LanbaiGlobals.cginc` 一起会重复定义；InsideLip 在 include 之前 `#define LANBAI_FOG_OWN_DENSITY` 绕过，已写进给总控 |
| 二 | 透明叠绘没有数 | 量了（§10、`Docs~/fse/`）：最多 0.057 FSE、每像素最多 2 层 |
| 二 | 跨类 static 调用 | 驱动里复制了一份 `EvOverlayAlpha` |
| 二 | 遮罩补偿用自己的 ΔEV | 前提写在这里：248.39 → 248.64 只有 FLASH_TEAR 一个曝光事件，所以“自己的 = 这一帧全部”；以后别的包在这段加曝光事件，补偿要改成读分发层的 ΔEV |
| 二 | S4c → S6 由谁切 | 注释改成“`LB_Journey.ApplyGrades` 在同一帧硬切” |
| 二 | 177.55 激活 | §0 第 4 条写了 |
| 三 | 用全仓检查 | 跑了，结果在 §8 |
| 三 | `tLichtDial` 196.10 vs cues.json 193.1 | 用圣经的 196.10（“ein Lichtchen”的字在 196.1 唱出）；cues.json 的 193.1 是注释里的估计。请本地听一下，以本地为准时改驱动的 `tLichtDial` |

## 14. 美术审片预审（`美术审片意见.md`，第 0 轮）的处理

| 意见 | 处理 |
|---|---|
| 纤维只有法律亮度的一半 | r06 / r07：最亮 2000 px 阈值 192–210（181–226），纤维三色 ΔE 2.7–16（r05 13.6–27.5）；见 `Docs~/measure_r07.md` |
| 228 主机位没渲、正前方是灰卡 | 渲了（228 正前 / 车门 / 天窗）；袖里空气压暗；结构问题还在，写在 §11 第 10 条和下一轮的办法 |
| 第 8 重的解不是 D-02 批的种子 107 | 暖白点挪到 −6.5° / +4° 以后重解，现在是种子 128、偏移 (−44.7, +10.6)、净空 52.5 m（审片看到的种子 115 是 r03 那一版）；已写进 `给总控.md` 请总导演重新批 |
| APL 提前到顶、尾声没有变亮的弧线 | r06 起：181 30.3 → 205 43.6 → 218.75 51.3 → 240 52.3 → 246.4 52.9（目标 31 → 43 → 47 → 53 → 54） |
| 181 三层开口套在一起 | r06 起“同时看得见 ≤ 3 重”真的成立，181 只有第 2、3 重 |
| 表盘 | 表盘归车厢（总导演），这里只写 `_Udon_RadioDial`（§5）；参考图里的车壳是占位，没有表盘 |
| flashcheck | 闪光那一段 PASS（§8）；光唇扫过、第 8 重升降的序列没跑完（§8） |

