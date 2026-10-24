# 第 7a 幕包（`Act07_Sea/`）· 海面之下（F2h → F5，363.26 → 644.96）

写的人：云端子会话「海」（分支 `pkg/sea`）。依据：圣经 v2.1 §6·7a，`Art/总导演裁决.md` D-09、D-17、D-21、D-23，海套件（`Sea/`，已在 main）。
**本目录的 C# 和 shader 都没在 Unity 里编译过**（检查见 §7）。

---

## 0. 先做这三件事

1. **拷**：`Act07_Sea/` 整个拷到 `Assets/Lanbai/Act07_Sea/`。它依赖已经在 main 上的：`Sea/`（海套件）、`Common/`、`GateClouds/Editor/`（搭建脚本借用它的 U# 程序资产工具 `LanbaiGateCloudsBuilder.AddUdonSharp`）、`Director/`（分发层）。`Tools~`、`Docs~` Unity 不导入。
2. **点菜单 `蓝白/Build/Act07a`**（可以重复点，先删上一次的）：它先跑 `蓝白/Sea/Create Materials`，再建本幕的材质、生成全部网格、搭场景 `R_Act07`、建 `Act07_Driver`（场景里有 `Director` 就挂在它下面）。然后点 **`蓝白/Director/1 Generate Dispatcher`**，让分发层认识新驱动。
3. **截图推回来**（`FromLocal/act07a_test/`）：主座位眼位 (0.55, 1.70, 2.05)、桌面 1920×1080、水平 90°，时间轴停在下表的 t（`LB_Journey` 的调试时钟或 Gate 的测试时钟），PPv2 profile 照表。每张附 Console 里 `[Act07]` / Udon 的报错原文。

| 张 | t | 机位 | profile | 对照参考帧 |
|---|---|---|---|---|
| A | 367.21（F3） | 正前，俯仰 0 | S7a | `Docs~/iterations/02_F3_fwd` |
| B | 367.21 | 仰 60°（天窗里的斯涅尔之窗） | S7a | `01_F3_up60` |
| C | 532.36（F3e2） | 右转 75°、仰 5°（海脊石壁） | S7a→S7b 0.34 | `08_F3e2_ridge` |
| D | 647.0（F5 后） | 左转 10°、俯 12°（远处的暖点） | S7b | `11_F5_warm` |

VR 另截一张：387 s 抬头 90°（`vr_left_fwd`），量 APL（D-09 ≤ 150）。

---

## 1. 坐标与时间

- **世界**：车固定在原点、车头朝 +z（跑步机）。**水的坐标系**：x 右、y 从海面往上（= −深度）、z = 车的前进方向。车的原点在水里的位置是 `(0, −depth(t), fwd(t))`；**`R_Sea`（所有固定在水里的东西的根）放在世界的 `(0, depth(t), −fwd(t))`**。
- **depth(t)、fwd(t)** 是圣经 §6·7a / 7b 的速度表的精确积分（每段 `v = v0 + dv · smoothstep((t − t0)/dur)`），`Act07_Sea/Tools~/act07_motion.py` 和驱动里的同一套公式；F2h 时车的原点在水下 1.0 m（水正好到窗台），眼睛在 **363.615** 没进水里。峰值加速度 0.28 m/s²（圣经 ≤ 0.28）。
- **标签**：`FromLocal/cues.json` 有的用它的；v2.1 的子标签（F3e、F3e1–3、F3i、F4p、F5p…）还没进 `cues.json`，用圣经 §2.1 的秒数（`Engineering/cues_v21_patch.json` 等本地合并）。JSON 的 `labels` 块写着每个标签取自哪里。
- **眼位**：主座位 (0.55, 1.70, 2.05) = Gate `cameras.U7` = 标准台 `hero`；`LB_Journey.heroEye` 是 (0.70, 1.77, 0.20)，两者不同，**参考帧按前者**。

## 2. 数据（`Act07_Layout.json`，唯一的数据源）

`Act07_Sea/Tools~/act07_layout.py` 生成。搭建脚本只读其中的 `unity`（平铺的数）、`particles`、`ridge` 块（JsonUtility 读不了嵌套数组）；其余的块是给人看的同一套数（带出处和说明）：

| 块 | 内容 |
|---|---|
| `motion` | 下沉 / 前进的速度表、每个标签处的深度和速度 |
| `handover` | F2h 进水：云关掉自己的海、驱动开平面（同一个 y、先用 ABOVE 材质 `M_06_Sea`）；眼睛进水那一刻（363.615，水线挡着）换 `M_07a_SeaSurface`、`_Udon_Underwater` 0 → 1 |
| `sea` | 斯涅尔之窗：F3e1 起 8 秒里窗的增益 × 1 → 0.04（“缩暗成一枚暗币”）；`_WindowCore` 桌面 (4.45, 3, 2, 1) / VR (3.2, 4, 2, 1)，VR 下按车厢侵蚀（F2h → F5：0 → 0.25）过渡（D-23 #2） |
| `water` | 按**车的原点的深度**插值：雾的密度（0–15 m 0.040、30–60 m 0.030、145 m 起 0.018）和水下雾色上 / 中 / 下（圣经 §6·7a 大气表的屏幕色按那一深度的调色反解；浅处的“上”是暗镜的颜色 `#294B72 × 0.38`） |
| `caustics` | `_Udon_Caustics.x` 从 1（水面）到 0（15 m）、颜色 = 座椅上屏幕 `#ACD4ED`（填 `#9FCBFF @ +1.46`）、方向 +1、钟 = t |
| `sun` | 透过水面的太阳：平行光仰角 70°、方位 +30°（D-12）、`#B0D9F2`、E 1.6 → 0（15 m）、焦散 cookie（CRT 256 ARGBHalf，1.5 m 平铺） |
| `ambient_trilight` | Trilight 天 `#8FB8DE` / 赤道 `#3876AB` / 地 `#0F2E4E` |
| `cabin` | 车厢的漂白、侵蚀、环境色（**不归这个包写**，列出来是为了参考帧用同一组数，圣经 §4.8 表） |
| `shafts` | 16 道光柱（水里固定；宽 1–4 m、长 20–40 m、α 0.04–0.08，轴 = 水里折射后的太阳，偏离竖直 14.9°）；18 m 起淡、25 m 没；F4p：453 → 462.36 汇向天窗的破洞，467.6 前淡尽；F3e1：最后一道宽光柱（2 s 进、4 s 扫过座椅、2 s 出） |
| `particles` | 海雪 1 200（25 m 球，0.8–2.5 cm，`#697987` α 0.3–0.6，1.5 cm/s 下沉）、播下的光 200（F3i → F5，越往后越密，诞生 ≥ 5 m 外，任一 5° 锥内同时最多一个诞生闪，生成时检查）、船体荧光池 900（300/s、寿命 1.5–3 s，F4 起）、气泡（玻璃上 120 一次、座椅缝 40 循环） |
| `ridge` | 海脊石壁：水里固定的高度场，面向车的一面 x ≥ 12.8 m（最近点 ≥ 12 m），深 80–135 m，520 → 546 s 升过右窗，只有船体荧光照到的边亮 |
| `warm_point` | F5 远远下方唯一的暖点：宫殿约定里离车最近的灯（`Lamp_R01`，F5 时 55 m 外、低 14 m），金 `#E0A860` 在 S7b 下反解，3 秒淡入；**宫殿会话自己的灯来了以后由它替换** |
| `grade` | S7a 到 F3e，然后 S7a → S7b 线性到 F5（**`LB_Journey.ApplyGrades` 写 PPv2**，本驱动不报 ΔEV） |
| `apl_targets` | 圣经 §6·7a 的 APL：F3 85、F3e 60、F3e1 46、F3e2 35、F3e3 25、F5 16 |

## 3. 场景和驱动

`蓝白/Build/Act07a` 搭的场景：

```
R_Act07
├─ R_Sea                 跟水走（驱动每帧放到 (0, depth, −fwd)）
│  ├─ Sea_Plane          Sea_Disc.fbx（ABOVE → BELOW 材质由驱动换）
│  ├─ Act07_Shafts       16 道光柱（Lanbai/SeaShaft；网格在 R_Sea 物体空间 = 水的坐标）
│  ├─ Act07_Ridge        海脊石壁（Lanbai/SeaRidge，本包的 shader）
│  └─ Act07_WarmPoint    暖点（Lanbai/SeaSpecks）
├─ R_Act07Bus            在原点（粒子 shader 把物体原点当车的原点）
│  ├─ Act07_Snow / Seeds / Trails / BubblesGlass / BubblesSeats（Lanbai/SeaParticles）
│  ├─ Act07_ShaftLast    F3e1 的最后一道光柱（驱动移动、转向）
│  └─ Sea_Dome           水下的“天”（Lanbai/SeaDome，眼睛进水时开）
└─ Act07_Lights
   └─ Act07_Sun          平行光 + 焦散 cookie（CRT，Lanbai/SeaCausticsCookie）
Act07_Driver             LanbaiAct07Driver（U#）
```

网格全部由搭建脚本按 JSON 生成（`Act07_Sea/Meshes/*.asset`）：粒子要 4 分量的 UV（FBX 只能带 2 分量），bounds 按 shader 实际画到的地方给（粒子和光柱在顶点着色器里移动）。

**驱动 `LanbaiAct07Driver`**（CONTROL §5 的三个方法）：
- `LanbaiWindow()` = {F2h − 1, 出海 + 1} = {362.26, 923.36}（整个第 7 幕；本包只做 7a，F5 以后保持 7a 的终态，7b / 7c 以后接在同一个驱动里）。
- `LanbaiActivate(on)`：开关 `R_Sea`、`R_Act07Bus`、`Act07_Lights`；世界的主太阳（`worldSun`，可空）在窗口里关掉；关的时候只交还海独有的量（`_Udon_Underwater` = 0、`_Udon_Caustics.x` = 0），共享的雾、海面高度 / 模式不写 w = 0（裁决 20:40 补充）。
- `LanbaiTick(t)` 每帧：`R_Sea` 的位置；平面的材质（ABOVE → BELOW）和 `_WindowGain` / `_WindowCore`（MPB）；全局量 `_Udon_T`、`SeaLevel`、`SeaMode`、`SeaClock`、`Underwater`、`SeaBus`、`SeaBusVel`、`Fog`（+ `FogBase` = 0）、`WaterFogUp/Mid/Down`、`Caustics`（+ `Color`、`Tex`）；**接管**（`Engineering/README_集成.md` §2–3：本地在 `LB_Journey` 勾上 `extAtmosphere`、`extSun`）：`RenderSettings.fogDensity / fogColor / ambient*`、本幕的太阳；光柱、最后一道光柱、粒子、石壁、暖点、穹顶的开关和 `_Gain`。
- **不写**：PPv2（`LB_Journey`）、车厢（`_Udon_Cabin*`，车厢驱动）、F2h 之前云的海。
- `writeRenderSettings`（默认开）：本地没勾 `extAtmosphere` 时请关掉，否则和 `LB_Journey` 抢写。

## 4. 车顶的侵蚀和 VR 的窗

圣经 §4.8：车厢侵蚀 F2h → F5 从 0 到 0.25，从天窗的边开始，≈387 s 从破洞里看得见斯涅尔之窗。侵蚀的 shader 是车厢的（总导演的 `Cabin/`），所以：
- 参考帧用标准台车壳加一个“车顶的洞”近似：仰角 ≥ `70 − 120 × 侵蚀(t)` 的方向全开（387 s：约 67°）；`roofhole=40` 是最坏情况（整个车顶都没了）。
- 驱动在 VR 里（`IsUserInVR()`）按侵蚀把 `_WindowCore` 从桌面的数过渡到 VR 的数。用 `vr_left_fwd` 机位、最坏情况量：桌面的数 APL 121，VR 的数更低（Sea 套件的 `31` / `32` 帧），**D-09 ≤ 150 两组数都守住**；VR 的数是余量。

## 5. 参考帧（`Docs~/iterations/`，标准台 `bible_v2` 车壳，PPv2 引擎模拟，主座位眼位）

渲法：`Docs~/lookdev/scene_7a.py`。海面是海套件的 numpy 移植（= `LanbaiSea.cginc`），光柱、粒子、石壁、暖点是各自 shader 的 numpy 照抄，数全部从 `Act07_Layout.json` 和 `Sea/SeaMaterials.json` 读。车壳内壁是占位的暗灰（反照率 0.023），环境色用 §2 `cabin` 的数。**车厢里面的东西（最后一道光柱落在座椅上、座椅缝的气泡、焦散）标准台画不出来**：车外是一张贴在 20 km 外的卡，车壳挡在前面。重渲：`bash Act07_Sea/Tools~/render_7a.sh`。

| 帧 | t / 机位 | APL（目标） | 看什么 / 量到的 |
|---|---|---|---|
| `01_F3_up60` | 367.21，仰 60° | 25.3（场景 84：抬头那一张不按它比） | 车顶还完整，只有天窗里一块斯涅尔之窗：窗心最亮、往外变暗、窗外是暗镜 |
| `02_F3_fwd` | 367.21，正前 | 76.6（84） | 光柱斜着往下、海雪往上漂过；水平线以上是暗镜透过来（`_TIRFog` 0.3）：**一道柔的过渡，不是硬线**（竖直方向 100 px 里亮度每 6 px 变 1–5 码值，水平线以下是平的） |
| `03_387_vr_auto` | 387，`vr_left_fwd` 仰 90°，VR | 46.0 | 车顶按 t 侵蚀（仰角 ≥ 67° 全开）：破洞里看得见窗 |
| `04_387_vr_worst` | 同上，车顶仰角 40° 以上全没了 | **121.6（D-09 ≤ 150）** | 最坏情况。海套件 `31` / `32`（同一机位、没有光柱和粒子）：VR 的数 97.8、桌面的数 121.2 |
| `05_F4_trails` | 446.5，右转 80°、俯 10° | 75.4（66） | 船体第一批荧光（右窗） |
| `06_F4p_gather` | 462.36，仰 35° | 45.3（63） | 光柱汇进天窗的破洞 |
| `07_F3e1_last` | 512.0，仰 40° | 31.6（44） | 窗缩成一枚暗币（`_WindowGain` 0.04）；**最后一道光柱扫过座椅画不出来**（在车里，见 §8） |
| `08_F3e2_ridge` | 532.36，右转 75°、仰 5° | 37.1（35） | 海脊：面和水差不多暗，只有起伏的棱被船体荧光描出来（`#8AC6FF` 一族）。高度场按网格逐像素求交（不是平面近似） |
| `09_F3e3_dark` | 556.36，正前 | 17.1（25） | 最后的蓝熄灭。窗里的水 = 圣经 145 m 的 `#0D181F` 一带（量到车外平均 ≈ `#121C27`）；差在车壳占位（见 §8 第 4 条） |
| `10_seeding` | 612.0，仰 10° | 15.5（19） | 播下的光一颗一颗固定在水里 |
| `11_F5_warm` | 647.0，左转 10°、俯 12° | 11.7（16） | 远处下方唯一的暖点（占位灯 `Lamp_R01`，55 m） |
| `12_7c_897_fwd` | 897.96，正前（海套件 K3） | **29.9（D-23：30–34）** | 7c 出海前的暗低谷：比下沿低 0.1（在测量误差里，但是贴着下沿） |

紫（D-21：h_ab 290–330、C\* > 8、L\* > 40）：12 帧里只有 `11_F5_warm` 的 4 个像素（h 290.1、L\* 40.7），在播下的光的芯上——圣经的填色 `#5E7AFF @ +2.73` 在 S7b 下，精灵在护栏之后画（`Sea/README_Sea接口.md` §2.7 第 1 条边界）。已问总控（`Sea/给总控.md` 第五批第 8 条）。

## 6. 和别的包的接口

- **云（第 6 幕）**：F2h 那一帧云关掉自己的海、本驱动开平面（同一个 y = 车上方 1.0 m、同一个 ABOVE 材质）。两块平面永不同时存在（`Sea/README_Sea接口.md` §5）。
- **宫殿（第 7b 幕）**：暖点是占位，宫殿的灯来了就删（`warm_point.replaced_by`）。`_Udon_PalaceVeil` 由本驱动在 7b 里写（`PalaceFrame_约定.json` 的 `palace_veil`）——7b 组装时加。
- **7c 和出海**：同一个驱动的下一段。D-23 要求的“出海前的暗低谷”在这个包里先量了一张（`12_7c_897_fwd`）。
- **本地**：`LB_Journey` 的接管开关（`extAtmosphere`、`extSun`、`extWindows`）；第 7 幕窗口里关掉旧的海占位（`seaA/seaB`、`deepGroup`），入水 / 出水音效挪到 F2h / 922.36（`Engineering/README_集成.md` §5 第 5 条）。

## 7. 检查

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Act07_Sea/Shaders Sea/Shaders` → 0 错 0 警。
- C#：`bash Common/Tools~/compile_check/check_cs.sh Act07_Sea Sea GateClouds` → OK（搭建脚本用到 `Sea/Editor` 和 `GateClouds/Editor`，一起编）。
- 数据：`~/bpy/bin/python Act07_Sea/Tools~/act07_layout.py`（重生 JSON：播种的 5° 锥检查在生成时做）。
- **没在 Unity 里编译过，没在头显里看过。**

## 8. 诚实的已知弱点

1. **立方图是退路**：斯涅尔之窗用海套件的备用 `Sea/Textures/Cube_Dawn_256.exr` 校的；正式的 `ReflCube_Dawn` 烘好以后重校一次窗心（D-23）。
2. **车里的效果参考帧画不出来**：最后一道光柱扫过座椅、座椅缝的气泡、焦散落在车里——标准台的车外是一张卡，车壳是占位的暗灰。驱动和 shader 都写了，没有图证明。请本地截图（§0 的 A–D 以外再加一张 512 s 看座椅）。
3. **侵蚀是近似**：参考帧用“仰角 ≥ 70 − 120 × 侵蚀 的方向全开”代替车厢的侵蚀 shader；VR 的 `_WindowCore` 按同一条时间表自己算（读不到车厢的值）。
4. **深处几帧的 APL 低于目标**（09：17 对 25、10：15 对 19、11：12 对 16）：窗外的水和圣经的颜色对得上，差在车里——占位车壳反照率 0.023、车里的环境色到 60 m 已经降到 (0.0014, 0.0039, 0.0089)。车厢驱动的真环境色 / 漂白上来以后应该会补上；如果补不上，海这边能做的是提深处的雾色，那会偏离圣经 §6·7a 的表，要总导演定。
5. **7c 的暗低谷 29.9**：贴着 D-23 的下沿 30。7c 包按 D-23 重做窗、雾的时候一起抬。远处的灯在这一帧偏橙（D-23 7c：要 h 78–80），也归 7c 包。
6. **水平线的过渡**：前方看去水平线上下是一道柔的过渡（`LanbaiHorizon` 的上 / 中雾色 + 暗镜），水平线以下突然平了，会有一点马赫带。在头显里看一眼。
7. **numpy 和 shader 的差别**：粒子用溅射近似（没有真的 alpha 排序）；光柱用一根的解析积分；海脊的法线是双线性面的中心差分（Unity 用网格的平滑法线）。
8. **没在 Unity 里编译过，没在头显里看过**；PPv2 是模拟。
