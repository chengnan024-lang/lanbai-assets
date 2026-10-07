# 蓝白 / Lanbai · 雨套件（Rain Kit）v2

美术圣经里所有“水”的落地：**§1.6 湿润模型**（湿沥青、水洼、车下干矩形）、**§4.6 车窗 / 挡风 / 天窗上的雨**（静止水珠、流动的水滴、雨刮）、
**§6·1 雨夜的站台**（只在被照亮的地方看得见的雨、溅花、水洼雨纹、灯臂滴水）、**§6·2 夜路**（同样的湿路、挡风玻璃上的雨与雨刮）、
**§6·12 醒来**（静止的水洼、成双的「蓝白」站牌、滴水的涟漪、**那一滴雨**）、**§8.1 第 3 项**（`RainRipple_512`、水滴法线、流动水滴、雨丝图集、溅花图集、`Stop_WetMask` 2048×512、“那一滴雨”贴花、天窗滴水）。

> ⚠ **所有 shader 与 C# 都没有在 Unity 里编译或运行过**（云端没有 Unity）。目标：Unity 2022.3、Built-in RP、VRChat SDK Worlds、UdonSharp 1.x、PPv2。
> 做过的检查（§12）：9 个 shader + 3 个 `.cginc` 用 Slang 前端对一份手写的 Unity 桩做了类型检查（14 个关键字变体全过）；
> 5 个 U# 脚本用 Roslyn（C# 9、警告即错误）对 Unity 2021.1 的 UnityEngine 引用程序集 + UdonSharp / VRC.SDKBase 桩做了类型检查（通过）。
> 这**不能**证明它们在 Unity / UdonSharp 里能编译——只能证明没有拼写、类型、参数个数这一类错误。
> 第一次导入时请把 Console 的报错原样回传；每个自定义 shader 都要在头显里看一遍（§10 的立体检查）。

预览图（Blender Cycles，用的就是本套件的贴图与 shader 数学，按圣经的 PPv2 调色）见 §11：
`Docs~/Preview_Stop_Night.png`（出生点的第一帧）、`Docs~/Preview_BusGlass_Night.png`（照片：贴着主座位车窗往前看，玻璃整面清晰、窗外的灯管与站牌化成光斑）/ `_NoDoF.png`（同一个视线，头显里看到的样子，车厢灯开着）、
`Docs~/Sheet_StillPuddle.png`（第 12 幕静止水洼里的灯影与成双的站牌，Unity 逐像素模拟）。

---

## v2 改了什么（验收第 2 轮：8 个主要问题、17 个次要问题）

| 验收 | v2 的做法 | 见 |
|---|---|---|
| **M1** 主角水洼太暗、涟漪反而更亮、模板窗没有交付 | 新 shader `Lanbai/StencilWindow`（开窗 + 把深度推到远平面）与 `Lanbai/MirrorCopy`（镜像副本）；`PuddleOverlay` 静水反射率改为 `_MirrorReflectance` 0.30（Schlick 到掠射 1），灯管不再是副本而是解析灯，核心钉在圣经的 `#DDE8EA`（`_LampPeak` 1.45）；涟漪里的灯每个碎面都**以静水的灯影为上限**——只会变暗、变散，永不更亮。顺带修了 `LanbaiLamps.cginc` 的 GGX 分母 ε（1e-7 → 1e-14：原来把 α 0.002 的水面灯峰压到 0.005，所以 v1 的“破碎灯管”实际是黑的）。普通 `WetSurface` 水洼用同一条规则。 | §2.4 |
| **M2** 水滴光学只算了一次界面 | `LanbaiDropExit`：车内空气 → 平板 → 水，再水 → 空气（两次 `refract`），全反射判定用同一对；`glass_ref.py` 同步。全反射面积 30° / 45° / 60° = 30 / 41 / 50 %（`Sheet_Drops`）。`OneDrop` 共用这个函数。 | §5、§6 |
| **M3** 流滴：头没了拖痕还在长，然后整条一帧复原 | `LanbaiRunners` 重写：头在 fs1（≤ 0.97）停住 → 变圆 → 停留 → 蒸发；拖痕按“头经过之后的时间”被新水珠占回；同时算上一个周期，跨周期边界连续；距离时钟（速度变化时头不跳）；位置性的走走停停；密度按 0.08 的带宽淡入淡出。站台实测（120 s、单层）：无头通道 0.09 个/m²（旧 3.9）、一帧复原 0（旧 126/m²/min）；`_RunDensityStill` 0.18 → **0.05**（两层同时在滑约 6.8 个/m²，旧 45）。 | §5.4 |
| **M4** 没有雨刮 | 新 `LanbaiWipers.cs` + `BusGlass` 的 `_Wipers`：每像素算“刮片多久前扫过这里”，水珠按各自的 G 在 `_WipeRefill`（3 s）内一颗颗回来，流滴随后再形成，刮片前沿推着一条细水线。U1 开始、U4 + 20 s 停（扫完这一下再停）。 | §5.5 |
| **M5** 湿润图在车头前 27 m 处一条直线断掉，外面的路没有虚线和水洼 | 新 `Road_WetMask_2048x512`：同一条路面 60 m 一个周期，沿路无缝（Wrap U Repeat）；`Stop_WetMask` 的最后 3 m 就是路面遮罩（两张图分辨率不同，重采样差约 1–2 %），站台特有的东西在两端淡出；`WetSurface` 的 `_WetMaskMode`：Stop（矩形外自动接路面遮罩）/ Road（R_Road 模块用 UV2）/ Off。虚线 3 m 实、周期 60/7 = 8.57 m（每个 60 m 模块整数段）。 | §4 |
| **M6** 公告箱玻璃上的水珠是黑点，且第 1、12 幕一样湿 | 从车外看，水珠主要是**透明**的：反射 F + 透过 (1 − F)，只有陡的边缘偏折到别处、取 `_BehindColour × _Udon_CaseLight`；水珠 Data.G 改为按**面积**重排，`_RainOverride` = 剩下的水珠面积：第 1 幕 1.0、第 12 幕 0.25（约 23 %）。 | §5.3 |
| **M7** 站台预览不像照片；车窗预览看不出流滴与那一滴雨 | 两张都重做：站台改为圣经 §6·1 出生点的第一帧（3:2，实心灯臂与灯杆、圆形尾灯、亮着的车窗是真玻璃、灯锥里的雨、低角度的车头灯光锥、柔和的灯晕，`spawn_walk` 水洼映出灯管）；车窗改为主座位右窗的真实几何（灯管与站牌在它们真实的方向和距离上，没有小镇），竖构图 50 mm，那一滴雨和它 2 cm 的拖痕停在灯管的光斑上，流滴的通道从光斑里穿过；照片版用“移轴”合成让整面玻璃清晰（§11），另给一张无景深、车厢灯开着的“头显里看到的”。 | §11 |
| **M8** 立体：5 个 vert/frag shader 在片元里读相机位置却没设眼索引 | `BusGlass`（两个 Pass）、`PuddleOverlay`、`OneDrop`、`DripDrop`、`WetOverlay` 以及新的两个 shader，片元第一行都是 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)`；`LanbaiVR.cginc` 与 `art/lens_tech/shaders/LanbaiVR.cginc` 里错误的注释已改正。 | §10 |
| 次要 1 雨纹锚在世界上 | 雨纹与滴水环用 R_Stop 局部坐标（`_AnchorToStop`，`_Udon_StopOffset`），滴水落点按站台局部存。 | §2、§7 |
| 次要 2 1 → 2 没有白可以藏滴水 | 站台的滴水一直滴到入云（U5 `StopDrips`）；U1 只停车上的那一滴（`StopBusDrips`）。 | §7 |
| 次要 3 粒子系统 13 个 | 所有站台滴水共用 1 个下落 + 1 个溅花系统，车上 1 个；第 1 幕合计 7 个（≤ 8）。 | §3.1 |
| 次要 4 标成 linear 的颜色被 Unity 转了 sRGB | 所有颜色属性都按“取色器里看到的 sRGB”填（`_AmbientColor` #9AA4AA、`_BottomColour` 0.11 …）。 | §1 |
| 次要 5 雨丝颜色与线宽 | `_Tint` #DCE7F3、`_Gain` 0.0152；可见线（半高全宽）= 四边形宽的 1/8 → Start Size 0.032–0.048 m 得 4–6 mm。 | §3 |
| 次要 6 拉伸轴可能转了 90° | `_SwapUV` 开关（另有 `_FlipV`）。 | §3 |
| 次要 7 溅花碰到格子边 | 重新打包：整帧绕撞击点缩到 0.84、四边 8 % 淡出；Start Size × 1/0.84。 | §3 |
| 次要 8 车内倒影被水珠打洞 | 合成顺序改为：水滴 → 污渍 → 朝你的那一面的倒影 × (1 − 底 alpha)。 | §5 |
| 次要 9 `Hide()` 留下一条空带 | 1.5 s 内把那一滴和它扫过的窄带一起淡出（发布的宽度 × 淡出）。 | §6 |
| 次要 10 流向改变时整片流滴绕轴转 | 两个固定的流向帧 A/B，变化 > 6° 或拖拽 > 0.12 时 1.2 s 交叉淡入。 | §5.4 |
| 次要 11 新落下的一滴是摩尔纹圆盘 | LUT 的 B、A 通道改为**按足迹低通**的同一组环；shader 按像素足迹在两者之间插值（≤ 0.8 mm 全频带，≥ 1.8 mm 低通）。 | §2.1 |
| 次要 12 雾 | `BusGlass`、`OneDrop` 加了 `multi_compile_fog`；预乘输出按 `fogColor × α` 混合。仍用 `unity_FogColor`（`LanbaiFog` 那个文件交付之后再换）。 | §10 |
| 次要 13 干路上还有 15 % 光带 | `_DryLampFloor`（默认 0.15；R_Road 设 0：第 11 幕没有光带）。 | §2.2 |
| 次要 14 滴水落点不在水里 | 灯臂、公告箱的落点移进各自的水洼（16 mm / 14 mm 深）；站牌的滴水落在混凝土基座顶面那一层积水上（`_WetMaskDefault` (0.3, 0.9, 0, 0)）。 | §7 |
| 次要 15 没有新一轮的预设 | `Preset_NewRound`（20 s 里雨回来）；`Preset_Depart` 改为 12 s（与 1→2 的 12 s smoothstep 同步）。 | §9 |
| 次要 16 文档与文字 | 水洼比例、唇口（半径 1.5 mm / Ø3 mm）、LUT 的 B/A 通道、`Sheet_Glass` 的“平铺”、布局图的标签都已改。 | §0、§4 |
| 次要 17 `Tools~` 杂物与写死的路径 | 删掉 `compile_check/out/`、`__pycache__`、过时的脚本；所有工具改用 `rainpaths.py` 找文件（环境变量见 §13）。 | §13 |

没有改的、以及验收里我们认为不对的地方，见 §14。

---

## 0. 文件清单

以 `~` 结尾的文件夹 Unity 不会导入，可以原样放进 `Assets/`。

| 路径 | 是什么 |
|---|---|
| **Textures/Puddle/** | |
| `RainRipple_Flip8x8_2048.png` | **圣经里的 `RainRipple_512`**（512 px/m）。水洼雨纹**法线** flipbook：8×8 = 64 帧，每帧 256 px = 0.5 × 0.5 m 水面；循环 2.0 s（32 fps）；空间与时间都无缝。RGB = 切线空间法线（OpenGL：+Y = PNG 的上方），线性。帧 0 = 左上，行优先。**可选**（默认是程序化环，§2.1）。 |
| `RippleRing_LUT_256x128.png` | 默认的程序化雨纹用的一滴雨（Ø0.95 mm 毛毛雨）的径向剖面：u = 半径 / 0.25 m，v = 年龄 / 1.25 s。**R,G = 全频带**坡度：坡度 = (R·2−1)·2^(G·14−12)；**B,A = 同一组环按 4 mm 像素足迹低通**（波数谱 × exp(−(k/600)²)），编码相同。v2 新增 B,A。 |
| `DripRipple_LUT_512x256.png` | 滴水（4.5 mm 水滴从 2–4 m 落下）的径向剖面：u = 半径 / 0.5 m，v = 年龄 / 2.5 s，通道同上。1.6 s 扩到 0.4 m、τ 0.7 s、2.5 s 内完全平复——倒影每次都回来（§5.5）。 |
| **Textures/Glass/** | |
| `RainBeads_Vertical_Normal_1024.png` / `_Data_1024.png` | 竖直玻璃上的静止水珠（车窗、挡风、车门玻璃、站牌面、公告箱玻璃）：0.20 m 平铺。沉积 + 并合模拟，大于 2.1 mm 的已经滑走。Normal = RGB 切线法线；Data：R = 厚度 / 2.5 mm，**G = 残留阈值（v2：按面积重排：rainAmount = a 时约剩 a 的水珠面积，大珠最后走）**，B = 覆盖，A = 接触半径 / 3 mm。 |
| `RainBeads_Horizontal_Normal_1024.png` / `_Data_1024.png` | 水平面上的水珠（**天窗**顶面、公告箱顶、长凳）：不滑落，可到 3.4 mm。编码同上。 |
| `GlassRunners_Flow_512x1024.png` | **流动水滴**的“泳道”图：0.20 × 0.40 m 平铺，12 条蜿蜒的泳道，水滴沿 −v 流。R = 本像素离泳道中线的偏移（0.5 + dx / 5 mm），G = 泳道 id，B = 路径斜率，A = 泳道遮罩。水滴头、拖痕、残留小珠都在 shader 里算（§5.4）。 |
| **Textures/Particles/** | |
| `RainStreak_Atlas8x1_512.png` | 雨丝图集：8 格 × 1 行，每格 64 × 512。R = 亮度，A = alpha（颜色和明暗由灯决定，§3）。v = 1（上）= 水滴头，v = 0 = 尾。8 种：plain / beaded / beaded_fine / twin / faint / wobble / bright_head / twin_beaded。可见的线（半高全宽）= 格宽的 1/8。 |
| `RainSplash_Flip4x4_512.png` | 沥青水膜上的**皇冠溅花**：Ø2.2 mm、5 m/s 的雨滴落在 0.3 mm 水膜上，Cycles 16 帧（0–32 ms，播 0.12 s）。**v2 重新打包**：整帧绕撞击点缩到 0.84、四边 8 % 淡出——一格 128 px = **57 mm**，撞击点仍在 (0.5, 0.125)。R = 亮度，A = alpha。 |
| **Textures/Drops/** | |
| `OneDrop_Head_Flip4x4_512.png` | **那一滴雨**（4 mm）的头：帧 0 静止（重力下垂）… 帧 15 滑动（前沿陡、后尾拉长）。一帧 12 × 12 mm，锚点 (0.5, 0.40)。R,G = 法线 xy，B = 厚度 / 5 mm，A = 覆盖。 |
| `OneDrop_Trail_128x1024.png` | 它的 80 mm 路径（12 × 96 mm 贴花）：顶下 8 mm 起步，+20 mm 停住（第 1 幕），+80 mm 落到胶条（第 12 幕）。R = 路径中线（0.5 + dx / 4 mm），G = 残留小珠高度 / 0.25 mm，B = 湿痕，A = 1。 |
| `PendantDrop_Flip4x4_512.png` | 天窗框角 / 灯臂槽 / 站牌下缘 / 公告箱顶沿的悬滴：帧 0–11 按 Young–Laplace 方程长大（**唇口半径 1.5 mm（Ø3 mm）**，最大 4.8e-8 m³ ≈ Ø4.5 mm），12–14 颈缩断裂（带卫星滴），15 回弹。一帧 10 × 10 mm，唇口在顶边中点。编码同 Head。 |
| `StepWet_Decal_256.png` | 天窗滴水在车门踏步上积出的湿斑（0.12 m 方）：R = 水膜，G = 小水珠高度 / 1 mm，B = 溅开的环，A = 总遮罩。 |
| **Textures/Stop/** | |
| `Stop_WetMask_2048x512.png` | 站台 48 × 12 m 的湿润图（2.34 cm / 像素）：**R 水洼深度、G 水膜保持、B 车下的干矩形、A 磨旧的白漆线**。路面有水 **17.9 %**、路肩 **9.9 %**（圣经 15–25 %）。最后 3 m 与 `Road_WetMask` 一致（重采样差约 1–2 %）。§4。 |
| `Road_WetMask_2048x512.png` | **v2 新增**：同一条路面的一个 **60 m 周期**（2.93 cm / 像素），沿路无缝平铺；路面 18.0 %、路肩 8.0 % 有水。给站台矩形外的路（自动）和 R_Road 模块（UV2）用。§4。 |
| **Shaders/** | |
| `Lanbai_WetSurface.shader` | `Lanbai/WetSurface`：Standard 表面着色器（光照贴图、雾、阴影照常）+ Lagarde 湿润 + 水洼（静水镜像 + 灯影上限）+ 雨纹 + 滴水环 + 8 盏解析灯的 GGX 长光带。§2、§4。 |
| `Lanbai_StencilWindow.shader` | **v2 新增** `Lanbai/StencilWindow`：主角水洼的“窗”——标记模板位 128，在窗里画镜子的天空并把深度推到远平面。§2.4。 |
| `Lanbai_MirrorCopy.shader` | **v2 新增** `Lanbai/MirrorCopy`：水洼里的镜像副本（站牌、杆、灯罩与灯臂、公告箱），只在窗里画，不受光：反照率 × `_Lit` + 发光。§2.4。 |
| `Lanbai_PuddleOverlay.shader` | `Lanbai/PuddleOverlay`：主角水洼的**水面**：静水保留 R(θ) 的镜像 + 解析灯管的灯影（核心钉在圣经目标），涟漪把它打碎（只会更暗、更散），写深度并清掉模板位。§2.4。 |
| `Lanbai_RainParticles.shader` | `Lanbai/RainParticles`：雨丝、溅花、下落的滴水——只在灯照到的地方亮（8 盏解析灯 × 前向散射相函数）。加色。§3。 |
| `Lanbai_BusGlass.shader` | `Lanbai/BusGlass`：车窗、挡风、车门玻璃、天窗、公告箱玻璃。无 GrabPass。静止水珠 + 流滴 + 雨刮 + 那一滴雨扫过的窄带；从车内看每滴水折射 `_Udon_ReflCube` + 解析灯，从车外看水滴大部分透明。§5。 |
| `Lanbai_OneDrop.shader` | `Lanbai/OneDrop`：那一滴雨的贴花。§6。 |
| `Lanbai_DripDrop.shader` | `Lanbai/DripDrop`：悬滴（面向两眼中点的 10 mm 小卡，球透镜：灯在水滴下半部倒立）。§7。 |
| `Lanbai_WetOverlay.shader` | `Lanbai/WetOverlay`：车门踏步上的湿斑。§7。 |
| `LanbaiRain.cginc` | 共用的雨的数学：flipbook / 程序化雨纹 / 滴水环（含足迹低通）、玻璃上的水珠、流滴、雨刮、水滴光学。**所有常数都是生成贴图时用的，改了就要重生成贴图。** |
| `LanbaiLamps.cginc` | 8 盏解析灯（`_Udon_Lamp0..7`）：GGX 镜面（湿路光带、水洼里的灯管，含“静水灯影上限”）、雨的散射、水滴里的小灯点。 |
| `LanbaiVR.cginc` | 共用的 VR 小工具（几何镜面抗锯齿、两眼中点……）。与 `art/lens_tech/shaders/LanbaiVR.cginc` 相同，只多了 `LanbaiCentreEyePos()`；两份的立体注释都已改正（§10）。 |
| **Runtime/**（UdonSharp，全部本地、不同步） | |
| `LanbaiRainState.cs` | 雨与湿度的全局量、流向帧 A/B、流滴的距离时钟、每幕预设（§9）。 |
| `LanbaiWipers.cs` | **v2 新增**：无人驾驶的雨刮（§5.5）。 |
| `LanbaiLamps.cs` | 把 8 盏解析灯写成全局量（§8）。 |
| `LanbaiDrips.cs` | 所有滴水（§7）。v2：共用粒子系统、落点按站台局部存、`StopBusDrips`。 |
| `LanbaiOneDrop.cs` | 那一滴雨（每个玩家自己的一滴，§6）。 |
| **Docs~/** | |
| `Preview_Stop_Night.png`、`Preview_Stop_Detail_1to1.png` | 第 1 幕，出生点的第一帧（1800 × 1200，§11）；1:1 细节：灯与站牌、灯下的湿路、`spawn_walk` 水洼里的灯管倒影。 |
| `Preview_BusGlass_Night.png`、`Preview_BusGlass_NoDoF.png`、`Preview_BusGlass_Detail_1to1.png` | 主座位右窗（1000 × 1500 竖构图）：照片（窗外虚化、玻璃整面清晰）、头显里看到的（无景深，车厢灯开着）、1:1 细节（左原图、右标注：那一滴雨与它走过的路、三颗流滴与它们的通道）。 |
| `Sheet_StillPuddle.png` | 第 12 幕静止水洼与第 1 幕被雨纹打碎的水洼，按 v2 shader 规则逐像素模拟 + PPv2 调色；与 v1 并排。 |
| `Sheet_Puddles.png`、`Sheet_PuddleCells.png`、`Sheet_Glass.png`、`Sheet_Particles.png`、`Sheet_Drops.png` | 每张贴图“是什么”和 v2 数学的图解（流滴的时空图、雨刮序列、水滴的两次折射、公告箱玻璃……）。 |
| `Verify_Round2.md` | 第 2 轮验收报告原文（本版逐条处理，见文首的表与 §14）。 |
| `Stop_WetMask_Layout.png`、`Stop_Layout.json` | 两张湿润图的平面布局；JSON 里有映射公式、水洼比例、所有点位（出生点、主座位眼、站牌、灯管、公告箱、三个滴水落点与它们落到的面）、4 个主角水洼的轮廓（Unity 局部 XZ）。 |
| **Tools~/** | 生成一切的 Python（`src/`）、预览场景（`preview/`）、编译检查（`compile_check/`）、生成参数（`meta/*.json`）。§13。 |

---

## 1. 导入

1. 整个 `Rain/` 放进 `Assets/Lanbai/Rain/`（路径随意）。shader 之间用相对 `#include`，三个 `.cginc` 必须和 `.shader` 在同一个文件夹。
2. **所有贴图都是数据，不是颜色：sRGB (Color Texture) 一律关。** Texture Type 一律 **Default**（法线也是：shader 自己解包，兼容 RGB / BC5 / DXT5nm）。
3. 逐张设置：

| 文件 | Shape | Mip | Wrap | Filter / Aniso | PC 格式 | Max Size |
|---|---|---|---|---|---|---|
| `RainRipple_Flip8x8_2048`（可选） | **2D Array，Columns 8，Rows 8** | 开 | Repeat | Bilinear / 4 | BC7（或 BC5） | 2048 |
| `RippleRing_LUT_256x128`、`DripRipple_LUT_512x256` | 2D | **关** | **Clamp** | Bilinear / 0 | **None（RGBA32）**——四个通道都是数据 | 原尺寸 |
| `RainBeads_*_Normal_1024` | 2D | 开 | Repeat | Trilinear / 4 | BC7（或 BC5） | 1024 |
| `RainBeads_*_Data_1024` | 2D | 开 | Repeat | Trilinear / 4 | BC7 | 1024 |
| `GlassRunners_Flow_512x1024` | 2D | **关** | Repeat | Bilinear / 0 | **None（RGBA32）**——R 是毫米级偏移 | 1024 |
| `RainStreak_Atlas8x1_512`、`RainSplash_Flip4x4_512` | 2D | 开 | Clamp | Bilinear / 0 | BC7 | 512 |
| `OneDrop_Head_Flip4x4_512`、`OneDrop_Trail_128x1024`、`PendantDrop_Flip4x4_512` | 2D | **关** | Clamp | Bilinear / 0 | None（RGBA32） | 原尺寸 |
| `StepWet_Decal_256` | 2D | 开 | Clamp | Bilinear / 0 | BC7 | 256 |
| `Stop_WetMask_2048x512` | 2D | 开 | **Clamp** | Trilinear / 8 | BC7 | 2048 |
| `Road_WetMask_2048x512` | 2D | 开 | **Per-axis：U = Repeat，V = Clamp** | Trilinear / 8 | BC7 | 2048 |

   - 全部 “Alpha Is Transparency” **关**。Non-Power-of-2 = None（全部是 2 的幂）。
   - 2D Array 的片序：Unity 从左上开始、逐行向右——与帧序一致。不支持 2D Array 时在 `#include "LanbaiRain.cginc"` 之前 `#define LANBAI_RIPPLE_ATLAS`。
4. **颜色属性按取色器里看到的 sRGB 填**（v2 的所有默认值已经是这样）：Unity 会把 Color 属性从 sRGB 转成线性，shader 收到的就是对的线性值。只有标了 “linear” 的 **Vector** 属性（例如 `_Lit`）是直接的线性数。
5. 依赖：Built-in RP、VRChat SDK Worlds、UdonSharp 1.x。shader 需要 `#pragma target 3.5`（PC DX11）。
6. 唯一的关键字是 `_RIPPLE_FLIPBOOK`（`WetSurface`、`PuddleOverlay`，默认关 = 程序化环），其余全部是普通属性——用脚本批量建材质时不需要 `EnableKeyword`。

---

## 2. 水洼：雨纹、滴水环、静水镜像

### 2.1 三种“水面的动”

| | 什么时候用 | 数量 | 贴图 |
|---|---|---|---|
| **程序化环**（默认） | 第 1 幕所有水洼，包括主角水洼：圣经 §6·1 “水洼雨纹 3–5 个/m²/s” | `_RippleDensity` 精确控制（默认 4 个/m²/s，最多 4.4）；每个 0.6 m 格子在随机时刻、随机位置落一滴（大小 ×0.8–1.2），两层错开 | `RippleRing_LUT_256x128` |
| **Flipbook**（`_RippleFlipbook` 勾上）= 圣经的 `RainRipple_512` | 更密的雨、远处的水面、水田 | 约 20 滴/m²/s（比圣经密约 3 倍；用在第 1 幕水洼时 `_RippleLayer2` 0、`_RippleStrength` 0.7） | `RainRipple_Flip8x8_2048`（2D Array） |
| **滴水环** | 灯臂、站牌下缘、公告箱顶沿的滴水落点 | `LanbaiDrips.cs` 写 `_Udon_Drip0..3`（站台局部落点 + 落地时刻） | `DripRipple_LUT_512x256` |

- **物理：** 有限水深的毛细–重力波色散 + 黏性与表面膜阻尼，Hankel 变换精确求解（`Tools~/src/ripple_physics.py`）：一滴雨是一组向外扩、越外越细的环。
- **v2 足迹低通（验收次要 11）：** 全频带里有到 k ≈ 2600 rad/m 的毛细细纹，比 1 mm 粗的像素装不下，新落下的一滴会闪成摩尔纹圆盘。shader 用 `LanbaiRingBand(LanbaiFootprint(P))` 在 LUT 的全频带（R,G）与低通（B,A）之间插值：像素足迹 ≤ 0.8 mm 全频带，≥ 1.8 mm 全低通（坐着看 2 m 外的水洼，沿视线约 2–3 mm）。`Sheet_PuddleCells` 上排是远看、下排是凑近看。
- **锚在站台上（次要 1）：** `_AnchorToStop` 1（R_Stop 上的材质）时，雨纹与滴水环用 `P − _Udon_StopOffset`，跑步机移动 R_Stop 时环跟着水洼走。R_Road 用 UV2 的米数（§4）。
- 所有函数返回世界 XZ 坡度，在水洼里与“沥青法线 × 0.05”相加。`_RippleStrength` 1 = 物理值。雨停了（第 12 幕）：`_Udon_RainFall` 0 → 只剩滴水环。

### 2.2 `Lanbai/WetSurface` 材质（湿路、路肩、混凝土、长凳）

| 属性 | 站台路面（R_Stop） | 路肩碎石 | R_Road 模块 | 混凝土（杆、基座） | 长凳木板 |
|---|---|---|---|---|---|
| `_MainTex` / `_BumpMap` / `_HeightMap` | 沥青 2K，每 3 m 一平铺 | 碎石 | 同站台路面 | 混凝土 | 橡木 |
| `_Smoothness`（干） | 0.20 | 0.25 | 0.20 | 0.25 | 0.35 |
| `_Porosity` | 0.50 | 0.55 | 0.50 | 0.55 | 0.60 |
| `_FilmSmoothMin / Max` | 0.74 / 0.84 | 0.50 / 0.60 | 0.74 / 0.84 | 0.30 / 0.40 | 0.50 / 0.60 |
| `_WetMaskMode` | **Stop** | Stop | **Road** | Off | Off |
| `_StopOrigin` | R_Stop 在“家”的世界位置 + 偏航 | 同左 | — | — | — |
| `_AnchorToStop` | 1 | 1 | 0 | 1（站台上的） | 1 |
| `_DryLampFloor` | 0.15 | 0.15 | **0**（第 11 幕“没有光带”） | 0.15 | 0.15 |
| `_WetMaskDefault`（Off 时） | — | — | — | (0, 0.5, 0, 0)；**站牌基座顶面 (0.3, 0.9, 0, 0)**（§7） | (0, 0.5, 0, 0) |

- 湿润由全局 `_Udon_Wetness` 驱动。**水膜**：反照率 × `_Porosity`、光滑度 0.74–0.84（遮罩 G）、法线 × 0.6；**水洼**：反照率 × 0.25、光滑度 0.97、沥青法线 × 0.05 + 雨纹；**车下**（B）：反照率 × 0.8、光滑度 0.45；**白漆**（A）：线性 0.45、湿 0.70。
- **变干的顺序**（第 12 幕湿度 0.85 → 路拱 0.55）：`wLocal = 1 − (1 − wet) × _DryBias × (1 − G)`；水位随湿度下降，浅的水洼先消失。
- **静水（v2，M1）：** 朝上的水洼（`smoothstep(0.85, 0.97, N.y)`）里，探针反射按 `_PuddleMirror` 0.30 + Schlick 到掠射 1 的“静水反射率”加到物理 Fresnel 之上；解析灯管在水里的像同样放大，**但核心钉在 `_LampPeak` 1.45**（圣经 §6·12 “静水里的灯影 #DDE8EA” 在 S12 下的线性最大通道），涟漪经过时每个碎面都以它为上限——普通水洼与主角水洼规则一致，不会再有“最暗的反而是主角水洼”。
- **光带：** 8 盏解析灯的 GGX 作为 emission 加上去（`_LampSpecular` 1）——圣经“灯光在湿沥青上拉成一条长长的白光带指向你”，不需要实时灯。Meta Pass 里不加（不进烘焙）。
- **VR：** 最终法线做了几何镜面抗锯齿（`LanbaiSpecAA`）。

### 2.3 在哪一层放哪个水洼

- 普通水洼 = 湿润图的 R 通道，不需要网格，`WetSurface` 自己画。
- 4 个**主角水洼**（`Docs~/Stop_Layout.json` → `hero_puddles`，Unity 局部 XZ 轮廓）：`door`（从主座位透过开着的门看见灯管与站牌的倒影）、`lamp_drip`（灯臂滴水正下方）、`notice_case`（公告箱脚，第 12 幕 +95 s 映出亮起的字幕）、`spawn_walk`（出生点第一帧映出灯管）。它们用 §2.4 的模板镜像。

### 2.4 模板镜像水洼（`Lanbai/StencilWindow` + `Lanbai/MirrorCopy` + `Lanbai/PuddleOverlay`）

**画的顺序（队列）：** 路面与一切不透明物体（≤ 2450）→ **StencilWindow**（AlphaTest+10 = 2460）→ **MirrorCopy**（AlphaTest+20 = 2470）→ 天空盒 → **PuddleOverlay**（Transparent−20）。

1. **窗：** 每个主角水洼按轮廓做一片平面网格，放在水面高度（路面上方 1–2 mm）。同一个网格放两个 Renderer（或两个子网格）：一个 `Lanbai/StencilWindow`，一个 `Lanbai/PuddleOverlay`。
   - StencilWindow Pass 1：正常深度测试（前面的杆、人照样挡住水洼），只写模板位 128；Pass 2：只在这些像素上画镜子的天空（`_MirrorSky`，第 1 / 12 幕 #070B14）并把深度推到远平面——低于路面的镜像副本才能通过深度测试，之后画的天空盒也盖不掉它。位 128 不碰头像 shader 常用的低位。
2. **镜像副本：** 把站牌（面、背、杆、五金、时刻表板）、灯杆、灯罩与灯臂、公告箱复制一份，放到**一个**父物体下，父物体放在水面高度、`localScale = (1, −1, 1)`（Unity 会自己翻转负缩放物体的剔除，保持 Cull Back）。副本用 `Lanbai/MirrorCopy`：Cast / Receive Shadows 关、Light Probes 关、Contribute GI 关，层 = 反射探针烘焙不看的层。
   - **不要复制灯管本身**：它在水里的像是 PuddleOverlay 里的解析灯（复制了就是两根灯管）。
   - 副本不受光：显示的是原物“看起来”的样子 = 反照率 × `_Lit` + 发光，全亮度；水面再只留下水的反射率。`_Lit` = 原物受到的光（线性，E × 灯色）：站牌面 **(1.14, 1.29, 1.32)**（= 1.47 × #E4F1F3），站牌杆约 0.9 ×，灯杆槽下 1.2 ×、槽上 0.08 ×，公告箱按烘焙结果取（灰卡在 Lightmap 里的读数 ÷ 反照率）。
   - 公告箱的纸：`_EmissionMap` = 字幕发光图，`_EmissionByCaseLight` 1（第 12 幕 +95 s `_Udon_CaseLight` 亮起时副本跟着亮）。
   - `_WaterY` = 水面的世界高度（在家时）：副本高于水面的部分被裁掉（基座、埋进地里的杆端不会冒出来）；`_AnchorToStop` 1。
3. **水面：** `Lanbai/PuddleOverlay`，预乘：`out = src.rgb + dst × (1 − src.a)`。
   - **静水：** 保留副本的 R(θ) = `_MirrorReflectance`（0.30）+ (1 − R0)(1 − cos θ)^5——**这不是物理的 2 %**：圣经的静水要让站牌“成双”（「成双的「蓝白」站牌」），0.30 是按 S12 屏幕目标定的（`Sheet_StillPuddle`：灯管核心实测 #E2E8EB，目标 #DDE8EA）。灯管 = 解析灯以同一反射率进入水面，核心上限 `_LampPeak` 1.45。
   - **碎水：** 坡度 ≥ `_BreakSlope`（0.04）的地方，清晰的镜像被**换成**沿起伏法线查立方图 + 解析灯；每个碎面以静水灯影为上限 → 被打碎的倒影只会更暗、更散；环衰减后镜像自己回来（τ 0.7 s，2.5 s 内复原，§5.5）。
   - `_RainRings` 第 1 幕 1、第 12 幕 0（只有滴水环）；`_BottomColour` 0.11（sRGB，水底的湿沥青）；`_AnchorToStop` 1。
   - 写深度（窗把它推到了远平面，后面的透明物体要正确遮挡），并清掉模板位 128。
4. **反射探针：** 站台的盒投影探针**烘焙时把灯管的发光网格关掉**——灯管的镜面由解析灯负责，否则每个光滑面上都有两根灯管。`_SkyFromCube` 只在探针里没有灯时才设 1。
5. 主角水洼平面所在的路面照常用 `WetSurface`（它的水洼会被 PuddleOverlay 盖住）。

---

## 3. 雨丝、溅花、滴落（`Lanbai/RainParticles`，三个材质）

**原则（圣经 §6·1）：雨只在被照亮的地方看得见。** 粒子本身是白的；亮度 = Σ 8 盏解析灯的照度 E × 散射相函数 × `_Gain` × `_Tint` + 很淡的环境（`_AmbientColor` × `_Ambient`）。雨滴强烈前向散射：你和灯之间的雨发光，灯旁边的雨暗，你身后的雨几乎看不见。加色混合。

| 材质 | 贴图 | `_Gain` / `_Tint` | Renderer | Texture Sheet Animation |
|---|---|---|---|---|
| `M_RainStreak` | `RainStreak_Atlas8x1_512` | **0.0152 / #DCE7F3**（站灯管旁逆光的一根雨丝在 S1 下读 `#9AA8B4`） | Stretched Billboard，Speed Scale 0.065，Length Scale 0 | Grid 8 × 1；Start Frame 随机 0–7；Frame over Time 常数 0 |
| `M_RainSplash` | `RainSplash_Flip4x4_512` | 0.03 / 白 | Vertical Billboard，Pivot (0, 0.375, 0) | Grid 4 × 4；Frame over Time 线性 0 → 16（0.12 s 放完） |
| `M_DripFall` | `RainStreak_Atlas8x1_512` 第 6 格 | 0.02 / 白 | Stretched Billboard，Speed Scale 0.03 | Grid 8 × 1，Start Frame 常数 6 |

- `_AmbientColor` **#9AA4AA**（sRGB，按取色器填）、`_Ambient` 0.06（圣经 α 0.06）。`_NearFade` (0.3, 1.2)：离眼 0.3 m 内看不见、1.2 m 起全亮。`_InvFade` 4（软粒子）。
- **线宽（次要 5）：** 可见的线 = 四边形宽的 **1/8** → 雨丝 Start Size **0.032–0.048 m** 得 4–6 mm（圣经）。
- **方向的两个开关（次要 6）：** 雨丝的亮头在尾部 → 勾 `_FlipV`；雨丝横躺在运动方向上（拉伸轴转了 90°）→ 勾 `_SwapUV`。⚑ 第一次截图确认。
- **溅花（次要 7）：** 图集已缩到 0.84，所以 Start Size 要 × 1/0.84：**0.048–0.067 m**。

### 3.1 第 1 幕的粒子系统（圣经 §6·1；§1.9 ≤ 8 个系统）

| # | 系统 | 形状 / 位置 | 数量 | 其余 |
|---|---|---|---|---|
| 1 | **灯锥雨** | Box 10 × 0.1 × 10 m，中心在灯池正上方、离地 5 m | **1 800** 活跃（Lifetime 1.0 s、Rate 1 800/s） | Start Speed 0，Velocity over Lifetime（World）Y −4.6..−5.4、沿风 0.7 m/s（8° 风斜）；Start Size 0.032–0.048；Simulation Space **Custom → R_Stop**（跑步机移动时雨跟着站台） |
| 2 | **车头灯雨** | 一个 Box 覆盖两条光束（22 m、35°），上沿离地 3 m | 900 | 同上；颜色来自车头灯那盏解析灯 |
| 3 | **其他地方** | 围绕站台 24 × 13 × 6 m 的 Box | **560** | 只有 `_Ambient` 那一点点 + 灯的散射 |
| 4 | **溅花** | Box 8 × 0 × 8 m 平放在灯池路面上 | Rate 200/s，Lifetime 0.12 s（≈ 24 活跃） | Start Size 0.048–0.067 m；Custom → R_Stop |
| 5–7 | **滴水** `stopFall`、`stopSplash`、`busFall` | 见 §7（Emission Rate 0，脚本 `Emit(1)`） | ≤ 4 + 4 + 2 | |

合计 7 个系统、约 3 290 活跃（≤ 3 300）。圣经的蛾子另算，仍 ≤ 8。夜路（第 2 幕）：雨系统挂在车上（Local），再给 Velocity over Lifetime 一个 −车速 的分量；8 盏灯槽由 Director 移到最近的钠灯上。

---

## 4. 湿润图与站台 / 路的坐标（`Stop_WetMask`、`Road_WetMask`）

**R_Stop 局部坐标：** +Z = 车头方向，+X = 车门 / 站牌一侧，Y 向上（与 Sign 套件预览舞台相同：stage x = Z，stage y = −X）。

| 遮罩 | 映射 | 覆盖 |
|---|---|---|
| `Stop_WetMask` | `u = (Z + 22) / 48`，`v = (5 − X) / 12` | Z −22..26 m、X −7..5 m |
| `Road_WetMask`（站台矩形外） | `u = frac((Z + 21) / 60)`，`v = (5 − X) / 12` | 沿路无限 |
| `Road_WetMask`（R_Road 模块，`_WetMaskMode` Road） | `u = UV2.x / 60`，`v = (5 − UV2.y) / 12` | 同上 |

- **R_Road 的 UV2 约定：** UV2.x = 沿路的**米数**、UV2.y = 横向的 X（米，与 R_Stop 的 X 同号：+X = 站牌一侧）。UV2.x 在模块之间要连续增加（第 k 块 = 60 k + 局部米数），并且与站台接上的那一块满足 UV2.x ≡ Z + 21 (mod 60)——虚线、水洼、水膜就从站台一直延伸进雾里。模块最好是 60 m（或它的整数分之一，例如 20 m、30 m）：虚线周期 60/7 = 8.57 m、3 m 实，每个 60 m 正好 7 段。
- **接缝（M5）：** 遮罩不再在矩形边上断掉：`Stop_WetMask` 的最后 3 m 与 `Road_WetMask` 在同一位置相同（两张图分辨率不同，重采样差约 1–2 %），站台特有的地形（门口的纵向凹、车道更深的轮辙、路肩旧车辙、四个主角水洼）在两端淡出；矩形外 `WetSurface` 自动采样路面遮罩。两张遮罩来自同一个 60 m 周期的路面高度场（2 % 路拱、轮辙、边缘沉降、补丁、坑洞）→ 优先洪泛填洼。
- `Docs~/Stop_Layout.json` 有全部点位：主座位眼 (X −0.85, Z −1.3)、站牌 (3.1, 3.4)、灯杆 (3.34, 1.72)、灯管 (2.38, 2.44)、公告箱 (3.37, 6.65)、出生点 (1.8, −10.6)、三处滴水落点与它们落到的面、车 (Z −7.9..0.1，X −2.75..−0.45)。把 R_Stop 摆成与这些点一致，或者按你们的布局改 `_StopOrigin`。
- `_StopOrigin` = R_Stop **在家时**的世界位置 + 偏航（w，度）；`LanbaiRainState` 每帧写 `_Udon_StopOffset`，遮罩跟着路走。
- 通道：**R** 水深 = `sqrt(depth / 8 mm)`；**G** 水膜保持（路拱最先干）；**B** 车下（潮而不湿；第 12 幕它还在——车从未开动过）；**A** 磨旧白漆（中心虚线 3 m 实、磨掉 60 %；两侧边线断续、剩 40 %；没有黄线）。
- 有水的比例：站台路面 **17.9 %**、路肩 **9.9 %**；路面遮罩路面 **18.0 %**、路肩 **8.0 %**（圣经 15–25 %）。

---

## 5. 车窗、挡风、天窗、公告箱玻璃上的雨（`Lanbai/BusGlass`，圣经 §4.6）

### 5.1 网格约定

- **法线朝车外 / 箱外**（朝雨那一侧）；导入切线。雨按**米**铺在玻璃的切线 / 副切线上，与 UV 无关（UV0 只给污渍图集用）。流滴的轴心 = 物体原点 + `_PivotOffset`：每扇窗做成单独的物体，原点在玻璃中心附近。
- 两个 Pass 都是双面、不写深度：TINT（`Blend DstColor Zero`，乘旧玻璃的绿 #E9EFEA，带雾）+ MAIN（预乘 alpha）。
- **MAIN 的合成顺序（v2，次要 8）：** 外表面的雨（水珠 + 流滴 + 雨刮）→ 污渍 → 朝你的那一面的反射 × (1 − 底 alpha)——车内倒影不再被水珠打洞。

### 5.2 材质

| 属性 | 车窗 / 车门玻璃 | 挡风玻璃 | 天窗 | 公告箱玻璃 |
|---|---|---|---|---|
| `_BeadNormal` / `_BeadData` | `RainBeads_Vertical_*` | Vertical | **`RainBeads_Horizontal_*`** | Vertical |
| `_BaseAlpha` | 0.06 | 0.06 | 0.08 | 0.06 |
| `_PaneFaceWind` | 0 | **1** | 0 | 0 |
| `_Wipers` | 0 | **1** | 0 | 0 |
| `_RainOverride` | −1（= `_Udon_RainAmount`） | −1 | −1 | **第 1 幕 1.0、第 12 幕 0.25**（Director 在第二次白下改） |
| `_BehindColour` / `_BehindLight` | 黑 / 0（用车厢立方图） | 黑 / 0 | 黑 / 0 | **纸色 #E8E3D3 / 1**（× `_Udon_CaseLight`） |
| `_CabinCube` | 车厢立方图 | 同 | 同 | 不需要 |

- **水滴的光学（M2）：** 从车内看，每滴水的出射方向 = `refract(refract(I, −Np, 1/1.333), −Nd, 1.333)`：先过平板进水，再从弯曲的水面出去；查 `_Udon_ReflCube` + 8 盏解析灯的宽瓣小灯点——夜里每滴水里都有一盏倒立的站灯。出不去（全反射）的边缘显示车厢颜色 × 0.6。
- **从车外看（M6）：** 水滴主要透明：反射 F（Schlick，F0 0.02）的世界 + 透过 (1 − F) 的后面；只有陡的边缘（倾角 0.45–0.85）偏折到别处，取 `behindRim`（公告箱 = `_BehindColour × lerp(1, _Udon_CaseLight, _BehindLight)` × 0.35；车 = 车厢立方图）。字读得出来，不再是黑点（`Sheet_Drops` 右下）。
- **车内倒影：** `_CabinCube`（烘焙的车厢立方图，管灯开）盒投影 × Fresnel × `_Udon_CabinLightmap` × `_CabinReflGain`（夜里 1，白天场景 0.25）。立体正确（§10）。
- Director 给的全局量：`_Udon_ReflCube`、**`_Udon_ReflCube_HDR`**（BC6H / RGBAHalf 的 HDR 立方图填 (1, 1, 0, 0)，不填就是黑）、`_Udon_ReflExposure`（0 = 当 1）、`_Udon_CabinLightmap`、`_Udon_CaseLight`（圣经 §6·12 做法：+95 s “嗒”一声 + 1.5 s 缓亮）。

### 5.3 各幕的雨状态

站 1.0（静止水珠 + 偶尔慢流 2–5 cm/s）· 1 → 2 车滑出 12 s 内被推向后斜 · 夜路 1.0（后斜 30–60°、拉长）· 离地 20 秒内 1 → 0（向上向后拉丝、蒸发）· 4–10 干净 · 11 假醒 0 · **12 醒 0.4 = 剩约 40 % 的水珠面积，留下的是大的**（v2 按面积重排了 G；v1 的 0.4 实际剩 95 %）。公告箱：第 1 幕 1.0、第 12 幕 0.25。

### 5.4 流滴（v2，M3 与次要 10）

- **一颗流滴的一生：** 在 fs0（0.02–0.5）出现并长大 → 沿泳道滑 → 在 fs1（≤ 0.97，离格子下沿至少 12 mm）**停住**，变圆、缩小 → 停留 0.75/速度 → 蒸发。拖痕按“头经过之后的时间”被新水珠占回（≤ 0.75/速度），残留小珠留得更久；上一个周期也同时计算，跨周期边界连续；新一颗经过旧水珠时把它吞掉。没有任何东西会在没有头的情况下移动或复原。
- **距离时钟：** 头的位置由 `_Udon_RunClock.x`（∫ 拖拽 dt，`LanbaiRainState` 积分）推，不是 `_Time × 速度`——车速变化时头不会跳；`.y` = 拖拽的 4 s 平均，用来把距离换成年龄。走走停停是**位置性的**（玻璃上每 1.2–4 cm 一个钉扎点），站台上 × (1 − 0.6 拖拽)。
- **流向帧 A/B：** `_Udon_FlowDir`（帧 A）、`_Udon_FlowDirB`、`_Udon_FlowMix`。流向变化 > 6° 或拖拽变化 > 0.12 时，B 设为新流向、1.2 s 内淡入，然后 A := B（流向稳定 1 s 后也会落到精确值）。整片流滴不再绕窗中心转，而是在两个固定的帧之间交叉淡入；淡入期间每像素算两次流滴。
- 数值：`_RunSpeedStill` 0.03 m/s（每条泳道 × 0.55–1.45）、**`_RunDensityStill` 0.05**（“偶尔”：两层同时在滑约 6.8 个/m²）、`_RunSpeedDrive` 0.22、`_RunDensityDrive` 0.75、`_RunSize` 0.003 m、`_TrailLife` 6 s、`_StickSlip` 1、`_DetailFade` 0.004（远处车窗的流滴按像素大小淡出）。
- **整颗地带走（v2）：** 流滴的通道、那一滴雨扫过的窄带，判断“这颗静止水珠还在不在”时取的是**这颗水珠的中心**（`LanbaiBeadCentre`：由水珠的坡度和接触半径反推，c − P = ∇h · R / √(1 + |∇h|²)），而不是当前像素——流滴把一颗水珠整颗吞掉，或者整颗留下，不会再把水珠切成直边的半球。水珠不是理想球冠，个别水珠边上会留下一圈极淡的水痕，像真的残水。
- 泳道格子 0.40 m 高，一颗流滴不跨格子：它最长滑 0.39 m，在离下沿 ≥ 12 mm 处停成一颗水珠——高窗上看到的是“滑一段、停住”的水滴，而不是被切断的线（§14）。

### 5.5 雨刮（v2，M4；`LanbaiWipers.cs`）

1. 每个雨刮做一个**枢轴** Transform 放在转轴上：局部 **+Y = 停放时刮臂的方向**（沿挡风玻璃下沿），局部 **+Z = 转轴**（大致垂直玻璃）。刮臂 + 刮片网格是它的子物体。两个雨刮就两个枢轴，拖进 `pivot[]`。
2. `sweepDegrees` 95（扫反了就填负数）、`rMin` 0.14、`rMax` 0.66（刮胶从离轴 0.14 m 到 0.66 m）、`strokeSeconds` 0.65（一次往或返）、`periodSeconds` 5（圣经：每 5 秒一次）。运动 = (1 − cos) 平滑往返，然后停放到下一次。
3. 挡风玻璃材质 `_Wipers` 1、`_WipeRefill` 3 s（圣经 2–5 s）。shader 由 `_Udon_WiperPivot/Rest/Axis{0,1}` 与 `_Udon_WiperTime` 每像素反算“刮片多久前经过这里”：刮过的弧里水珠按各自的 G 一颗颗回来，流滴在 0.4–2 s 后再形成，刮片前沿推着一条细水线。
4. Director：**U1（17.50）`StartWipers`**，**U4 + 20 s（95.8）`StopWipers`**（扫完这一下再停放）；第 11、12 幕从不启动。
5. **污渍图集：** 挡风玻璃 `_DirtTex` 里画两道“更干净的雨刮弧”（圣经 §4.6）时，弧的圆心 = 两个枢轴，半径 0.14–0.66 m，张角 = `sweepDegrees`，从停放方向开始——与 shader 里刮净的区域重合。`Sheet_Glass` 有 0.9 × 0.55 m 的序列。

---

## 6. 那一滴雨（`Lanbai/OneDrop` + `LanbaiOneDrop.cs`，圣经 §3.3、§4.6、§6·1、§6·12）

**整场梦只花了一滴雨的时间。**

1. 在**主座位车窗的外表面**贴一个 Quad，缩放 **0.012 × 0.096 m**，离玻璃 0.3 mm（车外一侧），法线朝车外，UV (0,0) 左下、v 向上 = 向上。位置：坐着的玩家眼睛能看见、并且**正好落在窗外灯管或站牌的光斑上**的地方（`Docs~/Preview_BusGlass_*` 用的是窗上 x −1.73、z 2.11）。⚑ 在头显里确认。
2. 把 `LanbaiOneDrop` 挂在任意物体上，`decal` = 这个 Quad 的 Renderer。本地：每个玩家都有自己的一滴。
3. Director 调用（`SendCustomEvent`）：

| 时刻 | 调用 | 效果 |
|---|---|---|
| 新一轮开始 | `ResetRound` | 回到起点（顶下 8 mm），圆的，可见 |
| 第 1 幕：本地玩家坐下 | `BeginSlide` | 约 1 cm/s、走走停停，2 s 滑 20 mm，停住、慢慢变圆 |
| 1 → 2 之后 | `Hide` | **1.5 s 内淡出，连同它扫过的那条窄带**（`hideSeconds`）；它停在原处 |
| 第 12 幕：第二次白收缩进灯管的那一刻 | `ShowAtRest` | 它恰好还在那里 |
| 第 12 幕 0 s | `FinishSlide` | 8 s 滑完剩下的 60 mm，落到胶条上，0.6 s 沉进胶条消失 |

- 它滑过的窄带（半宽 2.2 mm）上，BusGlass 的大水珠被扫走（`_Udon_OneDropA/B`；隐藏时宽度随淡出变 0——第 2–11 幕窗上不会留下一条空带）。光学与 BusGlass 相同（两次折射，M2）。

---

## 7. 滴水：灯臂、站牌下缘、公告箱顶沿、天窗框角（`Lanbai/DripDrop`、`Lanbai/WetOverlay`、`LanbaiDrips.cs`）

**每个滴水点：** 一个空物体放在**唇口**（`dripPoint[i]`）；它的子物体是一个 Quad（位置 0、缩放 0.010、材质 `Lanbai/DripDrop`，`_MainTex` = `PendantDrop_Flip4x4_512`），拖给 `pendant[i]`。

**共用的粒子系统（v2，次要 3）：** 所有站台滴水共用一个下落系统 `stopFall`（`M_DripFall`，Simulation Space = **Custom → R_Stop**，Gravity 1，Start Speed 0，Start Size 0.020 m）和一个溅花系统 `stopSplash`（`M_RainSplash`，Custom → R_Stop）；车上的滴水用 `busFall`（World）。三个都是 Play On Awake 开、Emission Rate 0、Shape 关——脚本把发射器移到唇口再 `Emit(1)`。**Lifetime** 设成最长那一滴的下落时间 √(2h/9.81) 再加一点（例如 1.0 s）；粒子落到地面以下前被 Lifetime 结束。`stopRoot` = R_Stop（落点按站台局部存，环跟着水洼走）。

| 点 | 唇口 | `fallHeight`（到它落到的那个面，**±1 cm**） | 落到 | `intervalMin/Max`（第 1 幕） | `wakeIntervalStart/End`（第 12 幕） | `ringsWater` | `onBus` |
|---|---|---|---|---|---|---|---|
| 灯臂 | 灯管槽外端最低点 | **3.90 m**（预览舞台） | `lamp_drip` 水洼（16 mm 深） | 1.5 / 4 | 4 / 10（8 分钟内拉长） | ✔ | |
| 站牌下缘 | 牌面下缘，杆前 5 cm | **1.92 m** | **基座顶面的积水**（400 × 400 混凝土、高出地面 30 mm） | 1.5 / 4 | 4 / 10 | ✔ | |
| 公告箱顶沿 | 滴水檐前角 | **2.16 m** | `notice_case` 水洼（14 mm 深） | 3.5 / 6 | 3.5 / 6（§5.5） | ✔ | |
| 天窗框角 | 车外框角 | 按你们的车量（预览约 2.5 m） | 车门踏步（湿斑） | 4 / 7 | 4 / 7 | | ✔ |

- `fallHeight` 要在你们的场景里量到 ±1 cm：环只画在离唇口 `fallHeight` 的那个面上（`LanbaiDripRipples` 的高度容差 2 cm）。数值上表是 Sign 套件预览舞台的。
- **站牌基座：** 基座顶面用 `WetSurface`，`_WetMaskMode` Off、**`_WetMaskDefault` (0.3, 0.9, 0, 0)**（一层薄积水 + 最后干），`_AnchorToStop` 1——滴水环画在它上面。（`Stop_WetMask` 在基座所在的位置没有水洼：基座比路面高 30 mm。）
- 每一滴：悬滴长大（帧 0–11，历时一个间隔）→ 0.12 s 颈缩断裂（12–14）→ 回弹（15）→ 一颗粒子落下 → **落地那一刻**：涟漪（4 个 `_Udon_Drip` 槽轮流用，断裂时就写好了落地时刻）、溅花、踏步更湿。
- **Director：** 第 1 幕 `BeginStop`（Start 时也会自己调）；**U1 `StopBusDrips`**（车开始动：只停天窗那一滴，站台的继续滴——1 → 2 是一个连续镜头，看得见的悬滴不能消失）；**U5 `StopDrips`**（入云，在云的白里）；第 12 幕 `BeginWake`（第一滴约 8 s 后；8 分钟内从 4 s 拉长到 10 s）。
- **踏步湿斑：** 车门踏步上方 1 mm 放一个 0.12 m 的 Quad（法线朝上），材质 `Lanbai/WetOverlay`（`StepWet_Decal_256`），拖给 `stepWet`。每滴 +0.12，每秒 −0.004，最低 0.15。

---

## 8. 8 盏解析灯（`LanbaiLamps.cs`、`LanbaiLamps.cginc`）

湿路的长光带、水洼里的灯管、每滴水里的小灯点、灯锥里发光的雨丝，全都来自这 8 盏在 shader 里算的灯（圣经 §1.6：不许有 Mixed 灯）。

| 槽 | 第 1 / 12 幕 | Transform | intensity（E = I / d²） | 颜色 | radius | halfLength | coneCos | emitAxis |
|---|---|---|---|---|---|---|---|---|
| 0 | 站灯管 | 灯管中心，局部 X 沿灯管 | **15**（灯池中心 E 1.0） | #E4F1F3 | 0.013 | 0.6 | 0.05 | 0（局部 −Y） |
| 1–2 | 两个车头灯 | 灯罩中心，局部 +Z 朝前 | 4 | #FFC47A | 0.08 | 0 | 0.954（35°） | 1 |
| 3–4 | 两个尾灯 | | 0.6 | #CB1500 | 0.05 | 0 | 0.2 | 1 |
| 5 | 车门漏出的光 | 门洞中心，局部 −Y 朝下 | 2 | #E4F1F3 | 0.25 | 0 | 0 | 0 |
| 6–7 | 两条亮着的车窗 | 窗带中心 | 1.5 | #C9DCE0 | 0.3 | 0.9 | 0 | 1 |

- **v2 修正：** GGX 分母的 ε 从 1e-7 改为 1e-14。旧值在光滑度 0.97–0.998（水面）时把灯峰压到原来的千分之一，所以 v1 里水面上的灯管几乎看不见；现在是物理值，再由“静水灯影上限”（`LanbaiLampSpecularCapped`）管住。
- 数值是起点：先按灰卡调烘焙灯，再让解析灯的镜面对上圣经目标。`gain[]` 给 Director 做淡入淡出。夜路：把槽 0、5–7 的 Transform 移到最近的钠灯上（`everyFrame` 开）。

---

## 9. 全局量与每幕数值（`LanbaiRainState.cs`）

| 全局量 | 含义 | 谁写 |
|---|---|---|
| `_Udon_Wetness` | 路 / 站台湿度（Lagarde） | RainState |
| `_Udon_RainFall` | 雨还在下（水洼雨纹） | RainState |
| `_Udon_RainAmount` | 玻璃上的水 = **剩下的水珠面积** | RainState |
| `_Udon_FlowDir`、`_Udon_FlowDirB`、`_Udon_FlowMix` | 流向帧 A、B（xyz = 空气推水滴的世界方向，w = 拖拽 0..1）与淡入量 | RainState |
| `_Udon_RunClock` | x = ∫ 拖拽 dt（流滴的距离时钟），y = 拖拽的 4 s 平均 | RainState |
| `_Udon_RunStretch` | 流滴额外拉长 | RainState |
| `_Udon_StopOffset` | R_Stop 离“家”的位移（跑步机） | RainState |
| `_Udon_WiperPivot0/1`、`_Udon_WiperRest0/1`、`_Udon_WiperAxis0/1`、`_Udon_WiperTime` | 雨刮 | Wipers |
| `_Udon_OneDropA/B` | 那一滴雨扫过的路径 | OneDrop |
| `_Udon_Drip0..3` | 滴水落点（站台局部）+ 落地时刻 | Drips |
| `_Udon_Lamp*0..7` | 解析灯 | Lamps |
| `_Udon_ReflCube`、`_Udon_ReflCube_HDR`、`_Udon_ReflExposure`、`_Udon_CabinLightmap`、`_Udon_CaseLight` | 每幕立方图、车厢灯、公告箱灯 | **Director（不在本套件）** |

**预设**（`SendCustomEvent`；数值在 `seconds` 秒内线性滑过去）：

| 时刻 | 调用 | wet | rain（玻璃） | fall | drag | dragUp | stretch | 秒 |
|---|---|---|---|---|---|---|---|---|
| 第 1 幕 | `Preset_Stop` | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| U1 车滑出 | `Preset_Depart` | 1 | 1 | 1 | 1 | 0 | 0 | **12**（与 1→2 的 12 s smoothstep 到 10 m/s 同步） |
| 第 2 幕 | `Preset_NightRoad` | 1 | 1 | 1 | 1 | 0 | 0 | 2 |
| 离地 U4 | `Preset_LiftOff` | 1 | **1 → 0** | 0 | 1 | 0.9 | 1.6 | **20** |
| 4–10、11 假醒 | `Preset_Dry` | 0 | 0 | 0 | 0 | 0 | 0 | 0（在遮挡下） |
| 第 12 幕（第二次白之下） | `Preset_Wake` | **0.85** | **0.4**（剩 40 % 的大水珠） | 0 | 0 | 0 | 0 | 0 |
| **新一轮**（下车、再上车、坐下） | `Preset_NewRound` | 1 | 1 | 1 | 0 | 0 | 0 | **20**（“雨在 20 秒里回来”） |

或者直接 `SetTargets(wet, rain, fall, drag, dragUp, stretch, seconds)`；车速变化时 `SetBusSpeed(m/s)`（10 m/s = 满拖拽）。流向帧的阈值与淡入时间在 Inspector 里（`frameAngleStep` 6°、`frameDragStep` 0.12、`frameFadeSeconds` 1.2）。

**第 12 幕时间线里本套件的调用：** 第二次白下 `Preset_Wake`、`LanbaiDrips.BeginWake`、公告箱玻璃 `_RainOverride` 0.25、主角水洼 `_RainRings` 0；白收缩进灯管时 `LanbaiOneDrop.ShowAtRest`；0 s `FinishSlide`；+95 s Director 让 `_Udon_CaseLight` 0 → 1（1.5 s）。

---

## 10. VR 与性能

- **没有任何屏幕锁定的东西。** 雨纹、水珠、流滴、雨刮全部锚在世界 / 玻璃上（米为单位）。
- **立体（M8）：** 在片元里读 `_WorldSpaceCameraPos` 的 shader（`BusGlass` 两个 Pass、`PuddleOverlay`、`OneDrop`、`DripDrop`、`WetOverlay`、`StencilWindow`、`MirrorCopy`）片元第一行都调用 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)`——SPS-I 下 `unity_StereoEyeIndex` 是一个 static，片元里只有这个宏会设它，不设就是 0（右眼用左眼的位置）。`LanbaiVR.cginc` 两份的注释已改正：**片元里只要读了相机位置（或深度图）就需要这个宏**。`WetSurface` 是表面着色器、`RainParticles` 只在顶点里用相机位置，都没问题。
  - **检查：** 闭一只眼看不出这个错误（每只眼单独看都合理）。要看的是**车窗里车厢倒影的深度**：两眼都睁开，倒影应该在玻璃“后面”1–2 m 处（车厢在你身后的距离），而不是贴在玻璃上；水洼里的灯管倒影应该在“地面以下”。
- **闪烁与光敏安全（圣经 §1.8）：** 雨丝亮度随灯连续变化；水洼里被打碎的灯是许多远小于 1°² 的闪点，并且 v2 只会更暗；滴水节奏 ≥ 1.5 s；雨刮 0.4 Hz 以下（5 s 一次）。
- **细线：** 雨丝四边形比可见的线宽 8 倍；湿路与水洼做了几何镜面抗锯齿；雨纹按像素足迹低通；远处车窗的流滴按像素大小淡出。
- **近眼：** 雨丝 0.3 m 内不可见、1.2 m 起全亮；悬滴 0.15 / 0.35 m。那一滴雨离眼约 0.4–0.6 m。
- **开销（估计，3060 级，9 MP）：** WetSurface 每像素最多 2 次遮罩采样 + 8 次 LUT 采样 + 8 盏灯的 GGX；BusGlass 每像素 2 次水珠采样 + 2 层流滴（各 1 次 LOD0 采样 + 算术；流向淡入的 1.2 s 内 × 2）+ 雨刮（只有挡风玻璃，2 个刮片的解析计算）+ 立方图 + 8 盏灯的小灯点——在圣经给玻璃的 0.7 FSE 预算内。模板镜像水洼：每个窗多一次全屏覆盖的小面积绘制 + 副本（约 10 个 drawcall）。粒子第 1 幕 ≈ 3 290 活跃、7 个系统。**需要砍的时候：** 先把“其他地方”560 → 300，再把车头灯雨 900 → 600。
- 贴图显存约 **20 MB**（新增的 `Road_WetMask` BC7 ≈ 1.4 MB）。
- **雾：** 所有自定义 shader 都有 `multi_compile_fog`（v2 补了 `BusGlass`、`OneDrop`）；预乘输出按 `fogColor × α` 混合。目前用 `unity_FogColor`；`LanbaiFog` 那个文件交付后再统一换。

---

## 11. 预览图（`Docs~/`）

都是 Blender 5 Cycles 渲染，用的是本套件的贴图与 shader 数学（numpy 移植：`glass_ref.py`、`runners_ref.py`、`cells_ref.py`、`lamps_ref.py`），按圣经的 PPv2 模拟调色（S1，K = 1.76，指数雾 0.009），与其他套件的预览同一条管线。均匀采样（自适应采样 + 降噪会把有光泽的车漆和湿路“揉成锡纸”，已排除）。

- **`Preview_Stop_Night.png`**（1800 × 1200）— 第 1 幕，**出生点的第一帧**：眼高 1.62 m，站牌杆后 15 m、右侧路肩，24 mm。圣经 §6·1 的构图：车尾与右侧车身在左（x 0–0.52），红尾灯，一排冷光车窗；灯管与站牌在 14 m 外略偏右（x ≈ 0.68 / 0.71），是世界上最亮的东西；车头灯的低光锥贴着路面溶进车前的雾里；灯管在湿沥青上拉出一列碎光指向你，`spawn_walk` 水洼映出灯管。**用 3:2 而不是 16:9**：从出生点的眼高看，灯管在水洼里的像在俯角 21°，16:9 的画框刚好把它切在下边缘外。
  - 路面 = `WetSurface` 的节点移植（两张遮罩、同样的 Lagarde 数值、静水灯影按 `_LampPeak` 封顶）；水洼雨纹 = 程序化环（`cells_ref.py`，足迹低通）+ 灯臂、公告箱的滴水环；雨丝亮度 = `RainParticles` 的公式（× `_Tint`、`_Gain` 0.0152）；溅花用重新打包的图集；车窗是真玻璃（外表面贴着本套件的水珠）。尾灯读 `#AF242C`（圣经 `#B2252C`）：这一张渲染时尾灯发光还是旧值（5 倍），出图前在线性空间里把尾灯像素 × 0.12 校正（等于用正确的发光重渲，只差它照在保险杠上的那一点红光）；`rain_scene.py` 已改成正确的值。
  - **灯晕（不是本套件的东西，记一笔）：** 预览里圣经那张 r 1.6 m 的光晕卡用了更陡的衰减（幂 3.2），再加一张 r 4.5 m、极淡的雾光——细雨里的灯是一团柔光加一条长尾，不是一张有边的圆片。做站台的人在 Unity 里调光晕卡时可以照这个来。
- **`Preview_Stop_Detail_1to1.png`** — 同一张的 1:1 像素：灯与站牌、灯下的湿路与碎光、`spawn_walk` 水洼里灯管的倒影与雨纹。
- **`Preview_BusGlass_Night.png`**（900 × 1350 竖构图）— 主座位右窗，**几何是真的**：灯管在 5.4 m 外、站牌在 6.4 m 外，都在它们真实的方向上；没有小镇（它在 −70°，从这扇窗看不到）。相机贴着车窗（离玻璃 15 cm，比坐直的主座位眼往窗靠 25 cm、往后 0.65 m），50 mm，往前斜看——**从坐直的主座位眼看，灯管与站牌在 +41°，在开着的车门里，不在主座位车窗里**（圣经 §4.1、§6·1 的布局本来就是这样），只有把头靠向车窗才能透过这块玻璃看见它们。
  - 玻璃外表面的法线 = `BusGlass` 的数学在第 1 幕某一时刻（t = 1067.5 s）的结果（`preview/glass_normals.py`：静止水珠 + 两层 v2 流滴 + 那一滴雨停在 2 cm 处、连同它扫过的窄带）；Cycles 把窗外真实地折射进每一滴水里：每颗水珠里都有一根倒立的小灯管。那一滴雨和它 2 cm 的拖痕停在灯管的光斑上；选的时刻有流滴的通道从光斑里穿过。**预览的流滴密度是 0.3**（游戏里站台默认 0.05，“偶尔”）：一张静止的图要看得出“流”。
  - **照片是“移轴”合成的（诚实地说）：** 视线与玻璃法线成 56°，普通镜头在这个距离只有一条竖窄带是清晰的。所以照片 = 无景深渲染里的水滴 + 同一镜头、干的平玻璃、f/2.8 对焦在玻璃上的渲染里的窗外（灯管与站牌的光斑），按玻璃上水的覆盖混合（`preview/tilt_composite.py`）——等于用移轴镜头把焦平面放在玻璃上。照片里车厢灯是关的，否则内侧玻璃会映出天花上的灯管。
- **`Preview_BusGlass_NoDoF.png`** — 同一个镜头、同一时刻，**没有景深、车厢灯开着**（座垫 E ≈ 1）：头显里看到的样子。内侧玻璃上有天花灯管与车厢的倒影（圣经 §4.6 的车内倒影；游戏里由 `_CabinReflGain` × `_Udon_CabinLightmap` 控制），窗外的灯管与站牌是清晰的。
- **`Preview_BusGlass_Detail_1to1.png`** — 照片的 1:1（左原图、右标注）：① 那一滴雨（4 mm）停在 2 cm 处，虚线是它走过的路（大水珠被带走，只剩雾状小珠与残珠）；②③④ 三颗流滴与它们刷出的通道（③ 的通道竖着穿过灯管的光斑）；灯管光斑前每一颗水珠都是一个暗的小透镜，里面有一根倒立的小灯管。它们是“水滴中的水滴”，游戏里眼睛靠动认出它们——所以静止的图上要标出来。标注的位置由套件的数学算出（`preview/detail_glass.py`）。
- **`Sheet_StillPuddle.png`** — 不是渲染，是 v2 shader 规则的逐像素模拟（`src/still_puddle.py`）：第 12 幕静水（灯管核心实测 #E2E8EB，圣经 #DDE8EA；成双的站牌）、第 1 幕被雨纹打碎（只会更暗）、v1 规则（一块暗斑）。

**与 Unity 的差别（诚实地说）：**
- 预览里水滴折射的是真实的三维场景，Unity 里是立方图 + 解析灯（圣经不许 GrabPass）：游戏里水滴里的“世界”更简单，小灯点一样亮。
- 车窗的两张都是“靠向车窗往前看”的视线。坐直时这扇窗外是灯照着的路肩、草和田；水珠里仍然有倒立的小灯（一颗水珠的折射视野有几十度宽，靠窗前沿的水珠能把 +41° 的灯管折射进来），但没有灯管的光斑。那一滴雨放在哪块光斑上，见 §14。
- 车、灯、站牌、公告箱、田、山是 Sign 套件的预览舞台（`deliver2/Sign/Tools~/src/stage.py`）；车是它的占位车（一个方盒子），不是最终的车模型。车头灯光束是圣经的“假体积光锥”（叠加卡，预览里随高度淡出，免得远端在山上画出一道白拱）。
- 景深是照片的语言；游戏里没有景深——所以有 `_NoDoF` 那一张。

---

## 12. 没有编译过的东西，和我们做过的检查

- **Shader（9 个 + 3 个 .cginc）没有在 Unity 里编译过。** `Tools~/compile_check/check_shaders.py` 把每个 CGPROGRAM 连同 include 展开，接上手写的 Unity 桩（`unity_stub.slang`：UnityCG、表面着色器输入、纹理 / 立方图宏、`appdata_full`、`UNITY_REVERSED_Z`……），用 Slang 做前端类型检查；表面着色器的 `vertex:vert` 函数也会被调用一次。每个关键字组合（全关、各自开、全开）共 **14 个变体，全部通过**（在本版所有改动之后重新跑过）。它**不**检查：Unity 的表面着色器生成器、ShaderLab 语法（Stencil、队列、渲染状态）、寄存器 / 采样器上限、平台编译器的警告。
  - 这一版另外手工过了一遍“导数不能进分支”：所有 `ddx` / `ddy`、隐式导数的 `tex2D` 都在任何提前 `return` / 动态分支之前（`OneDrop` 的拖痕改用 `tex2Dlod`，`WetOverlay` 的镜面抗锯齿挪到提前返回之前）；分支里只用 `tex2Dlod` / `tex2Dgrad`。
- **U#（5 个脚本）没有在 UdonSharp 里编译过。** `Tools~/compile_check/check_cs.sh`：Roslyn 4.x、C# 9、警告即错误，对 Unity 2021.1 UnityEngine 引用程序集 + `UdonStub.cs`——**通过**。用到的 API（`ParticleSystem.Emit(int)`、`Transform.position/rotation/localRotation`、`Quaternion.AngleAxis`、`Material.SetFloat`、`VRCShader.*`、`Mathf.*`、`Random.Range`）都是 Udon 常见的；没有暴露的话 Console 会直接说。
- **第一次在 Unity 里要看的（⚑）：**
  1. 模板镜像：窗、副本、水面三个队列的顺序；副本在水洼外完全看不见；天空盒没有盖掉窗；水面之后的透明物体（雨丝）被正确遮挡。
  2. 立体：车窗里车厢倒影的深度、水洼里灯管倒影的深度（§10）。
  3. 雨丝方向（`_FlipV` / `_SwapUV`）；溅花撞击点在粒子位置。
  4. 雨刮：刮净的弧与刮片网格重合（枢轴的 +Y / +Z 约定）；扫的方向（`sweepDegrees` 的符号）。
  5. `_Udon_ReflCube_HDR` 是否填了；站灯那盏解析灯的强度按灰卡；静水灯影的屏幕值（S12 下 #DDE8EA 附近）。
  6. 滴水环落在水面上（`fallHeight` ±1 cm）。
  7. 那一滴雨在主座位上看得见的位置。
  8. `WetSurface` 的 Meta Pass（它直接读 `IN.internalSurfaceTtoW0..2`；Meta Pass 里解析灯已经关掉）。

---

## 13. `Tools~`（重生成）

所有贴图都由脚本生成，数值与 shader 常数一一对应（`meta/*.json` 是生成时的参数快照）。Python 3 + numpy / scipy / Pillow / matplotlib；带 “bpy” 的用 Blender 5 的 Python 模块（Cycles CPU）。

**找文件：** 所有脚本经 `src/rainpaths.py` 找贴图与数据：依次在 `$RAIN_OUT`、`<工具>/../out`、本套件的 `Textures/*/`、`Docs~/`、`Tools~/meta/` 里找，所以在套件里直接就能跑。生成器写到 `$RAIN_OUT`（默认 `Tools~/out/`，生成后再拷进 `Textures/`）。项目根（有 `deliver2/` 与 `art/` 的那一层）自动往上找，也可以 `LANBAI_ROOT=...`。预览的缓存（地面贴图、Sign 的贴图、玻璃法线）在 `$RAIN_PREVIEW`（默认 `Tools~/preview/../preview`）。

| 脚本 | 产出 |
|---|---|
| `src/ripple_physics.py` | 毛细–重力波的径向解（Hankel 变换、有限水深、黏性与表面膜阻尼；`kc` = 足迹低通） |
| `src/make_ripples.py`、`src/make_luts.py` | `RainRipple_Flip8x8_2048`、`RippleRing_LUT`、`DripRipple_LUT`（R,G 全频带 + B,A 低通） |
| `src/beads_sim.py`、`src/make_beads.py`、`src/remap_bead_G.py` | 水珠沉积 + 并合模拟 → `RainBeads_*`；G 按面积重排（`beads.json` 里有 rainAmount → 剩余面积的表） |
| `src/make_runners.py` | `GlassRunners_Flow` |
| `src/runners_ref.py`、`src/glass_ref.py`、`src/cells_ref.py`、`src/lamps_ref.py` | `LanbaiRunners`、整块玻璃（含雨刮、两次折射）、程序化雨纹 / 滴水环、解析灯（含静水上限）的 numpy 参考实现——**与 `.cginc` 逐行对应，改一个就要改另一个** |
| `src/runner_metrics.py` | 流滴的验收指标（无头通道、一帧复原、在滑的水滴数）+ `Sheet_Glass` 的时空图 |
| `src/make_streaks.py` | `RainStreak_Atlas8x1_512` |
| `src/render_splash.py`（bpy）、`src/pack_splash.py`、`src/exr.py` | 溅花的 Cycles 渲染与打包（v2：缩到 0.84、四边淡出） |
| `src/pendant.py`、`src/make_drops.py` | Young–Laplace 悬滴、那一滴雨、踏步湿斑 |
| `src/make_wetmask.py` | 60 m 周期的路面高度场 → 填洼 → `Stop_WetMask` + `Road_WetMask` + `Stop_Layout.json`（含滴水落点检查） |
| `src/make_docs.py` | `Docs~/Sheet_*.png`、`Stop_WetMask_Layout.png`（`python3 make_docs.py <套件> [puddle cells glass drops particles wetmask]`） |
| `src/still_puddle.py` | `Docs~/Sheet_StillPuddle.png`（需要 `art/lens_cine/ppv2.py` 与 `art/bible_work/lutlib_core.py`） |
| `preview/make_ground.py` | 预览用的沥青 / 碎石地面贴图（写到 `$RAIN_PREVIEW`） |
| `preview/rain_scene.py`（bpy） | 站台预览（`SHOT=spawn`）与车窗预览（`SHOT=window`；`GLASS_MODE=drops / clear / mask`：带水的玻璃、干的平玻璃、水的覆盖遮罩）；需要 Sign 套件的 `Tools~/src/stage.py` |
| `preview/tilt_composite.py` | 车窗照片的“移轴”合成：`drops`（无景深）的水滴 + `clear`（有景深）的窗外，按 `mask` 混合（§11） |
| `preview/detail_glass.py` | `Preview_BusGlass_Detail_1to1.png`（1:1 裁切 + 标注） |
| `preview/glass_normals.py`（bpy 只用来写 EXR） | 车窗预览的玻璃外表面法线（套件数学） |
| `preview/post_preview.py` | 预览调色（复用 Sign 套件的 `post.py`：PPv2 模拟、bloom、雾、镜头层） |
| `compile_check/` | §12 的两个检查。输出写到 `$CHECK_OUT`（默认系统临时目录），**不写进套件**；`check_cs.sh` 需要 `CSC=<Roslyn 所在文件夹>` |

v2 删掉了：`compile_check/out/`、`__pycache__/`、`src/cells_look.py`（被 `cells_ref.py` 取代）、`preview/glass_scene.py`（被 `rain_scene.py SHOT=window` 取代）、`preview/cam_search.py`（临时脚本）。

---

## 14. 没有改的，以及与圣经的冲突（请美术总监裁定）

**验收里我们不同意或没有照做的：**
- **“没有一颗流滴能跨过 0.40 m 的格子行，高窗上是一段一段的”（M3 附带）：** 没有改格子。v2 里流滴总是在离下沿 ≥ 12 mm 处**停成一颗水珠**（不再在玻璃中间淡出），所以看到的是“滑 18–38 cm、停住”的水滴，不是被切断的线；站台 3 cm/s 时一颗要滑 6–13 s，“偶尔慢流”里没有需要更长的滑。跨格子的连续流滴要把泳道图做成无缝的竖向长条或在格子边交接身份，开销翻倍，留到确实需要时再做。
- **“破碎的灯管在 ≈ 12 处削成白色”（M1）：** v1 的 HLSL 实际上因为 GGX 分母的 ε 把它压到了约 0.005（几乎是黑的）——验收用的是物理公式，而不是套件里的代码。结论不变（v1 是错的），v2 两头都修了：ε 改正，并且封顶。
- **M1 建议的“镜像副本发光体 0.7×”：** 没有用。灯管根本不做副本（改由解析灯 + `_LampPeak` 精确地钉在屏幕目标上），副本只有不发光的部分（站牌、杆、箱）和公告箱的纸。

- **M7 “车窗预览用主座位右窗的真实视线：灯管、站牌、水田里的倒影”：** 从坐直的主座位眼看，灯管（+41°）、站牌，以及它们在水田 / 水洼里的倒影（倒影与灯在同一方位）都在开着的车门里，不在主座位右窗（+60..+150°）里——这是圣经 §4.1 / §6·1 的布局，不是预览的选择。所以两张车窗预览用的是“把头靠向车窗、往前斜看”的真实视线（§11），并在这里记下。
- **M7 “车要么出画，要么是暗剪影”：** 站台预览保留圣经 §6·1 出生点的构图（车尾与右侧车身在左半边）。车身迎灯一侧被站灯照亮是圣经 §4.9 写明的（“车身迎灯一侧接到冷光”），所以它不是暗剪影；白色圆头灯、没有光锥、车窗上没有雨这几条都已改掉（车头朝外，看不到车头灯本身，只看得到贴地的光锥；车窗是挂水珠的真玻璃）。车是 Sign 套件舞台里的方盒子占位车，最终的车模型来了以后照同样的灯再拍一次。公告箱从出生点看正好藏在站牌后面（它在站牌后 3.3 m、同一条视线上），所以这一帧里看不到它；它的玻璃现在让灯光照进箱里，不再是黑块。

**与圣经的冲突（不是套件的错）：**
- **§5.4 的屏幕目标与 §1.6 的反照率：** “湿路在灯池里 10–18、池外 2–5”在圣经自己的 S1 模拟器里需要反照率 0.004–0.006；按 §1.6 的湿沥青反照率（线性 0.02–0.035）、灯池 E 1.0 读 36–50。预览按物理数（灯池约 40–50）。请先定哪一条是法。
- **§5.5 的视角与站台布局：** “站在箱前低头 30–40° 恰好看见灯管”需要灯管在视线后方 7.9 m，布局里它离箱 4.3 m。`notice_case` 水洼映出的是亮起的字幕（与站牌），记作偏离。
- **§6·3：** “入云……水滴横向拉丝”与“U4 + 20 秒前玻璃干净”矛盾；套件跟后者（`Preset_LiftOff` 20 s 内 1 → 0）。
- **“醒 0.4”：** v1 的 0.4 实际留下 95 % 的水珠面积；v2 把 G 按面积重排后，0.4 = 剩 40 % 的面积（大的留下）。如果圣经的意思是“几乎和第 1 幕一样，只是没有流滴”，把 `Preset_Wake` 的 rain 改成 0.9 即可。
- **§6·1 “红尾灯在湿路上拉成两条竖倒影”**：从出生点的眼高（1.62 m，离车尾 3.9 m）看，尾灯在湿路上的镜面点在俯角约 34°，在任何正常构图的画框之外；走近车尾才看得到。预览照实画（看不到），记作偏离。
- **§6·1 的虚线 “3 m 实 / 6 m 空”**（周期 9 m）与 60 m 路模块不能整除；套件用 60/7 = 8.57 m 的周期（3 m 实、5.57 m 空），每个模块整数段、无缝。
- **静水反射率：** 物理的水正视只有 2 %；圣经要“成双的「蓝白」站牌”与 #DDE8EA 的灯影，套件用 0.30（艺术值，按 S12 屏幕目标定）。
- **主座位车窗里看不见灯管**（§11）：圣经 §3.3 / §4.6 写“那一滴雨”在主座位车窗上、“每一滴雨里有一盏倒立的小灯”，但从坐着的眼睛看，灯管在门的方向。需要决定那一滴雨放在哪块光斑上。
