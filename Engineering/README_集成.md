# 全片集成说明（给本地，也给每个包）· v1（2026-10-24）

维护：总工程师。**随包更新**：每个包合进 main，这里加一节“这个包怎么接”。v0 先定规矩（谁写什么），具体到包的接线等包交了再补。

> v1 加了：§8 **全片写的人时刻表**（天、雾、月、星、主光、RenderSettings、遮罩、曝光，按 D-22 及补充、D-24、D-25、D-27），§9 **一幕一幕导入**（门的驱动、门内 4c / 5 + 遮罩 v2、7a / 7c、天空套件、第 9 幕），§3 的接管开关按 §8 填。
> **本页提到的 C# 和 shader 都没在 Unity 里编译过**，只过了 `Common/Tools~/compile_check`（全仓 shader 41 个文件 / 416 个编译单元 0 错，C# OK，2026-10-24）。

---

## 1. 一句话的架构

本地的 `LB_Journey`（UdonSharp，已经能跑）是**钟**：它算 t、幕、运动、音频、诗、管灯、**全部 PPv2 权重和 ΔEV**。每个包交一个**驱动**（`Lanbai<幕>Driver`），只管自己那一幕的根物体、材质参数和自己登记过的 `_Udon_` 全局量。中间一层很薄的**分发层**（`Director/LanbaiActDispatcher.cs`）由 `LB_Journey` 每帧调一次，把 t 按时间窗发给各个驱动。

```
LB_Journey.Update()
  ├─ 钟 t、运动、音频、诗、管灯、ApplyGrades()（PPv2 权重、EXPO、镜头层）  ← 本地，已有
  └─ dispatcher.LanbaiDispatch(t)                                           ← 本地加 1 行
        └─ 对每个驱动：t 在 LanbaiWindow() 里 → LanbaiTick(t)；进出窗口时 LanbaiActivate(on)（只在遮挡下）
```

## 2. 每样东西只有一个写的人（最重要）

同一个量两个人写，后写的赢，而且每帧顺序不定（Udon 的 Update 顺序不保证）。所以：

| 资源 | 唯一的写的人 | 包要做的 |
|---|---|---|
| **PPv2 volume 的 weight**（15 个场景 + EXPO_UP/DOWN + WHITE_SAT/BLOOM + 镜头层） | **`LB_Journey.ApplyGrades`**（本地，r0097 已验证） | **驱动不碰 PPv2，也不调 `Grading/Runtime/LanbaiExposure`**。包里有曝光事件（镜子脉冲、白、入水、出海……）的，把事件曲线**写成数据**放进自己的 JSON + README（时刻用 cues 标签、ΔEV、升 / 降秒数、形状），总工程师汇总进本页 §5 的差异表，本地照表改 `ApplyGrades`。圣经 §1.4：一帧只有一个 ΔEV，所有事件相加 |
| 遮罩球的填色 / alpha（`Lanbai_Overlay` v2） | 和 ΔEV 同一个人（填色 = profile 填值 × 2^−ΔEV，要知道这一帧的 ΔEV）→ `LB_Journey` | 门内交 v2 shader；方向性的遮罩（10→11 白收缩进灯里）的参数也作为数据交 |
| `RenderSettings.fogColor / fogDensity / ambientLight`、世界主光 `sun` 的颜色 / 强度 / 方向 | 现在是 `LB_Journey`（按 `SKY_*` 预设）。**接管以后**是当时那一幕的驱动 | 见 §3 的“接管开关” |
| 天空盒材质参数 | 同上 | 同上 |
| `_Udon_*` 全局量 | 登记表（`Common/UdonGlobals.md`）“写的人”那一栏；同一个名字跨幕时，**时间窗不重叠** | 驱动在自己的时间窗里写；**交接的那一帧**由后一幕写（前一幕在窗口外就不再写） |
| 车厢（管灯、侵蚀、漂白、环境色） | `LB_Journey` 的管灯 + 车厢驱动（总导演的 `Cabin/`） | 包不碰车 |
| 根物体的激活 | 各自的驱动 `LanbaiActivate`，只在遮挡下（黑、白、入云、水下） | `LB_Journey` 现在的占位组（`gateGroup`、`skyGroup`、`deepGroup`……）在包装好以后由本地关掉 |

## 3. 接管开关（请本地在 `LB_Journey` 里加）

包一幕一幕地进来，`LB_Journey` 里原来的占位要一幕一幕地让出去。建议本地加一组布尔（Inspector 里勾）：

```csharp
public bool extAtmosphere;   // 勾上：在有驱动接管的时间窗里，不写 RenderSettings.fog* / ambientLight
public bool extSun;          //       不写 sun 的颜色 / 强度 / 方向
public bool extSkybox;       //       不写天空盒材质
public float[] extWindows;   // 成对的 {t0, t1}：哪些时间窗由驱动接管（分发层从各驱动的 LanbaiWindow() 汇总后写进来）
```

**`extWindows` 不能直接用分发层的 `windowsFlat`**：`windowsFlat` 是所有驱动的窗口并起来，里面有不写 `RenderSettings` / 主光的驱动（天空第 1–3 幕默认 `ownsAtmosphere` 关、门的驱动从来不写、第 9 幕不写），照它让出去，那几段就没人写了。**按 §8.3 的表一个开关一组窗口手填**（建议把 `extWindows` 拆成 `extAtmosphereWindows` / `extSunWindows` 两个数组；只留一个的话，填 §8.3 两列的交集，再按幕勾驱动的开关）。Director v1.1 会让每个驱动报“我写哪几样”，到时由分发层算，本地就不用手填了（还没做）。

不勾的时候行为和现在完全一样，所以可以先加、后用。**这是对 `LB_Journey` 唯一的改动请求**（加上 §1 里调分发层的那一行）。

## 4. 驱动的接口（`CONTROL_总控.md` §5）

```csharp
public void  LanbaiTick(float t)      // 每帧（t 在窗口里时）；只写自己的东西
public void  LanbaiActivate(bool on)  // 根物体开 / 关，只在遮挡下调
public float[] LanbaiWindow()         // {开始 t, 结束 t}，含预热
```

- `Start()` 里把 MaterialPropertyBlock 和全局量写一遍（进 Play 时编辑器写的会丢）。
- 时间只用 t 和 cues 标签（驱动里的标签数组由搭建脚本从 `FromLocal/cues.json` 烘进去：**Udon 运行时读不了 JSON**，所有表都要由编辑器脚本烘成 `float[]` 字段）。
- 不写 PPv2，不写 `RenderSettings`（除非这一幕已经按 §3 接管），不碰车。

## 5. 本地时间轴和圣经 v2.1 / 各包的差异（本地照这张表改）

| # | 项 | 本地现在 | 应该是 | 出处 | 状态 |
|---|---|---|---|---|---|
| 1 | 十三面镜的穿越时刻 `starCross` | `cues.json` 的 `mirror_crossings_snapped_t`（E1 的旧数列） | 1032.41, 1054.29, 1070.62, 1082.67, 1092.39, 1099.71, 1105.42, 1109.46, 1112.86, 1115.36, 1125.55, 1137.58, 1149.31 | `Mirrors/MirrorSchedule.json`（pkg/mirrors，审查中）、圣经 §6·9 | 待镜与白的包过审 |
| 2 | 镜子脉冲的面数 | `ApplyGrades` 里 `i < 9`（前 9 面） | 第 1–11 面（第 12 面是白的冲击、第 13 面是剪 2） | 圣经 §1.8 镜子脉冲 | 待确认 |
| 3 | `FLASH_TEAR` 的起点 | U12 − 0.5 | U12 − 0.75（247.89）起 0.4 秒升、保持 0.1、0.25 秒落入黑 | 圣经 §1.8 | 待确认 |
| 4 | 第 11 幕倒挂的灯 | `lampFlipHeight = 17` | 海在 80 m、灯头离路面 7 m、杆 73 m（灯与假醒按 80 m 做，待总导演定） | 圣经 §6·11、`Lamps/给总控.md` | 待总导演 |

| 5 | 海的入水 / 出海 | F2 入水、F9b 出海（旧表）；`fall*` 运动；旧的海占位 `seaA/seaB`、入水 / 出水音效在 F2 / F9b | **F2h 363.26 入水、F9s + 0.5 = 922.36 出海**；第 7 幕的根物体运动由海的驱动自己算（不读 `fall*`）；第 7 幕窗口里关掉 `LB_Journey` 的旧海占位（§3 的接管开关），入水 / 出水音效挪到新时刻 | 圣经 v2.1 §2、§6·7；`Sea/给总控.md` §5–§6 | 待海的包 |
| 6 | `cues.json` 缺 v2.1 子标签 | 只有 U6k…LIP8、F2h、F9b、F11b、F16r、F_end | 补 31 个：U2b、U3b、U4b、U4h、U5r、F0s、F1c、F1t、F1b1、F1b2、F1z、F3e、F4p、F3e1–3、F3i、F5p、F5q、F5r、F7e、F7s、F7p、F8a、F8b、F8c、F8r、F9s、F9t、F10e、F10l | **`Engineering/cues_v21_patch.json`**（和圣经 §2.1 逐个核对过，0 处不一致；标“波形”的请用耳朵确认） | 等本地合并 |

（每审一个包就往这里加。）

## 7. 本地旧占位 vs 新包（门、天、海……每一幕都会碰到）

规则：**新包接管一幕时，`LB_Journey` 里那一幕的旧占位整个让出去，不并存、不逐项混合。** 做法：
1. 新包的驱动在 `LanbaiWindow()` 里报出自己的时间窗（含预热）。
2. 分发层把所有已挂上的驱动的时间窗汇总，写进 `LB_Journey.extWindows`（§3）；`LB_Journey` 在这些窗口里不写 `RenderSettings` / `sun` / 天空盒（按接管开关），并把那一幕的旧占位组（`gateGroup`、`skyGroup`、`seaA/B`、`deepGroup`……）关掉。
3. 旧占位在“哪个窗口里关”由本地在 Inspector 里给每个占位组填一个窗口（因为只有本地知道 `LB_Journey` 里哪个组对应哪一幕）；分发层只负责告诉它“哪些时间段已经有人接管”。
4. 声音、运动这类“全片一条线”的东西不按幕切：运动差异（比如海的入水时刻）写进 §5 的差异表，本地改 `LB_Journey` 的数组，而不是让驱动去覆盖。

## 6. 全片导入顺序（随包更新）

1. `Common/`（`LanbaiVR.cginc`、`LanbaiFog.cginc`、`LanbaiSky.cginc`、`LanbaiCaustics.cginc`、**`LanbaiGlobals.cginc`**）→ `Assets/Lanbai/Common/`。别的包的 shader 都 include 它们。`LanbaiGlobals.cginc` 是生成的（`Common/Tools~/globals/gen_globals.py`，按 `Common/UdonGlobals.md`，现在 182 个量），不要手改。
2. `Grading/` → 跑 `蓝白/Grades/Build Profiles & Volumes`（已经做过）。
3. `Director/` → 先拷，菜单等所有驱动拷完再点（§9.0）。
4. 之后按 §9 一幕一幕来（= 旅程顺序）。每个包的 README 第一节写“拷哪些文件夹、点哪个菜单”，§9 只写它们之间怎么接、开关怎么勾。

---

## 8. 全片写的人时刻表（本地按幕导入时的总表）

规则（D-22 及 20:40 补充、D-24）：**同一时刻一个量只有一个写的人**；交接那一帧由后一个写；前一个“交还”时**只清自己独有的量**，共享的天 / 雾 / 月 / 星通道不许写 w = 0，后一个负责写全。分发层按类名排序 tick（门在门内之前），所以重叠的那几帧后一个稳赢。根物体开着就算显存，驱动在看不见的时段 `LanbaiTick` 里早退（D-27 #4）。

### 8.1 共享的 `_Udon_` 天、雾、月、星

“天雾组” = `_Udon_Fog`、`FogModel`、`FogBand*`、`FogBase`、`FogBelow`、`FogShape`、`FogCubeParams`、`Horizon/Zenith/NadirColor`、`SkyBlend`、`SkyFx`、`Sky_*`；“月” = `MoonDir`、`MoonDisc`；“星” = `StarGain`、`StarShape`、`GalaxyGain`。

| t（秒） | 标签 | 写的人 | 写哪些 | 交接那一刻 / 交还什么 |
|---|---|---|---|---|
| 0 → 17.50 | 第 1 幕 → U1 | 天空 `Lanbai_SkyDriver_Acts1to3`（`overcast_rain_night_town`） | 预设的全部名字（一次 `Apply` 写 68 个） | `Start()` 先写一次，t = 0 就对 |
| 17.50 → 129.10 | U1 → U6k | 同上（`overcast_rain_night`，钠光 10 秒淡掉） | 同上 | — |
| 129.10 → 133.80 | U6k 破云 → U6 | 同上（`moon_night`，在云里切） | 同上 | **133.80 天空停写**。门的窗口 113.80 开，但 113.80 → 133.80 门不写这几组 |
| 133.80 → 179.55 | U6 → U9 | **门的驱动** `LanbaiGateDriver` | 天雾组 + 月 + 星（`StarShape` −1 EV），133.8 → 163.8 从 `moon_night` smoothstep 混到 `act4_gate`；混完常量只写一次，之后只写光带方向 | 数值只从 `Sky/SkyPresets.json`、`Sky/FogPresets.json` 读（Build Driver 时烘进去）。U9 − 0.05 起只写光带方向（冻住） |
| “门内露出来的那一帧”（眼离裂口平面 ≤ 0.7 m，或 t ≥ 179.55）→ 248.64 | U9 → 剪 1 | **门内** `LanbaiInsideDriver` | 天雾组整组（`_Udon_FogModel` = B 渐变，`StarGain` / `GalaxyGain` = (0,0,0,1)），U9 之前用 U9 的值 | 和门重叠的几帧门内后 tick，稳赢。**248.64 停写**；`LanbaiActivate(false)` 只清 `_Udon_InsidePortal`、`InsideDot`、旧的 `_Udon_FogDensity` = 0。**门内不写月**：月盘停在门最后写的值，第 6 幕要写全 |
| 248.64 → 363.26 | 剪 1 → F2h | **「云」第 6 幕**（`dawn`，黑遮罩下 `Apply`） | 天雾组 + 月 + 星，写全 | **包还没交**（D-25：只交还自己的量） |
| 363.26 → 922.36 | F2h 入水 → 出海 | **海** `LanbaiAct07Driver`（7a + 7c 一个驱动） | `_Udon_Fog`、`FogBase`、`WaterFog*`、`Underwater`、`SeaLevel`、`SeaMode`、`SeaClock`、`SeaBus*`、`Caustics*`、`ReflCube*`、**`_Udon_T`** | 363.26 之前什么都不写（云的海还在，两块水面永不并存）。**922.36 只交还海独有的**（`Underwater` = 0、`Caustics.x` = 0、主光 cookie 摘掉），雾不清零，交给第 8 幕 |
| 922.36 → 1001.21 | 出海 → 8b 末 | **「云」第 8 幕**（`dusk_8i` → `dusk_8ii` → `blue_hour`） | 天雾组 + 月 + 星 | **包还没交**。**t ≥ 1001.21 不许再调 `Apply` / `ApplyBlend`**（会成第二个写的人） |
| 1001.21 → 1149.31 | 第 9 幕 → F16 | **第 9 幕** `LanbaiAct09Driver` | `SkyBlend`、`SkyFx`、`Fog`、`GalaxyGain`、`StarGain`；1009.21 起加 `Zenith/Horizon/FogBand/NadirColor` | 窗口 992.06 开（例外：开的时候什么都看不见）。`blue_hour` 里这几个量和 1001.21 写的一样，接得上 |
| 1149.31 → 片尾 | F16 白 → 第 11、12 幕 | 天空 `Lanbai_SkyDriver_Acts11to12`（`overcast_rain_night`，白遮罩下） | 全部名字 | 第 10 幕的白里天被遮住，没人写也看不见 |

### 8.2 主光（D-24：全片只有一盏带阴影的主光 = `RenderSettings.sun` = 门测试里的 `Gate_Lights/Moon`）

| t | 写的人 | 写什么 | 备注 |
|---|---|---|---|
| 0 → 180.05 | **`LB_Journey`**（按 `SKY_*` 预设）或场景里的值 | 方向、颜色、强度 | **门的驱动 v1.2 其实不写主光**（只写车厢裂口光 `Tear_CabinOnly` 和补光 `Fill_from_below`，窗口外关）。D-24 说“U9 之前归门”，代码里是“保持场景值”。所以第 4 幕这段 `extSun` 不勾；本地要保证 177.55 那一帧主光强度 = 门内的 `mainLightGate`（1.0），不然 180.05 会跳 |
| 180.05 → 188.05 → 252.64 | **门内**（`writeMainLight`） | 只写强度：1.0 → 0.001（和 S4 → S4c 同一条 smoothstep） | 不改方向、颜色 |
| 252.64 → 363.62 | **「云」第 6 幕** | 主光转成晨日（D-24 / D-25；方位 +30°、仰角 +6° 在车门里） | 包没交 |
| 363.62（眼下水）→ 922.36 | **海**（`writeMainLight`） | 方向（仰角 70°、方位 +30°）、颜色 `#B0D9F2`、强度、焦散 cookie | 主光从不关；出海摘 cookie。往回拖到下水之前也摘 cookie、交还第 6 幕 |
| 922.36 → 1149.31 | **「云」第 8 幕**；第 9 幕不写 | 暮日 → 蓝时 | 包没交；第 9 幕要的话由第 8 幕留下的值 |
| 1149.31 → 片尾 | `LB_Journey` | — | |

### 8.3 `RenderSettings`（内置 shader 的雾色 / 雾密度 / 环境色）和接管开关怎么填

| t | 写的人 | 本地：`extAtmosphere` 窗口 | `extSun` 窗口 | 驱动上要勾的 |
|---|---|---|---|---|
| 0 → 133.80 | `LB_Journey`（或天空，勾 `ownsAtmosphere`） | 不填（要让天空写就填 0 → 133.80 并勾 `LanbaiSkyPreset.ownsAtmosphere`） | 不填 | — |
| 133.80 → 177.55 | `LB_Journey` | 不填（门不写 RenderSettings） | 不填 | — |
| 177.55 → 252.64 | 门内 | **177.55 → 252.64** | **177.55 → 252.64** | 门内 `writeRenderSettings`、`writeMainLight`；环境光模式 **Trilight** |
| 252.64 → 362.26 | 「云」第 6 幕 | 等包 | 等包 | — |
| 362.26 → 923.36 | 海 | **362.26 → 923.36** | **362.26 → 923.36** | 海 `writeRenderSettings`、`writeMainLight`；Trilight |
| 923.36 → 片尾 | `LB_Journey` / 「云」/ 天空 11–12 | 等包 | 等包 | — |

- **环境光模式**：门内和海都要 Trilight（海的驱动会自己设 `ambientMode = Trilight`）。天空的 `LanbaiSkyPreset` 写的是 `ambientLight`（= Trilight 下的天空色）。建议全片就用 Trilight，`LB_Journey` 的预设也按三色写，免得模式来回切。
- `extSkybox`：一直不勾。全片一个天空盒材质（`M_Sky.mat`，`蓝白/Sky/Build Sky` 时就设好了），预设只换全局量。

### 8.4 曝光、遮罩

| 东西 | 写的人 | 驱动报什么 |
|---|---|---|
| PPv2 weight、ΔEV（一帧一个） | **只有 `LB_Journey.ApplyGrades`** | 有曝光事件的驱动实现 `float[] LanbaiGrade(t)`，分发层加起来放进 `dispatcher.gradeDEV`（`gradeOwned` = 有人报）。现在报的：门内的 `FLASH_TEAR`（247.89 起 0.4 s 升、0.1 保持、0.25 落）。**`ApplyGrades` 里自己那份 FLASH_TEAR 要删**（不然算两次）。门内的 `writeExposure` 一直不勾 |
| 遮罩球 `Lanbai_Overlay` v2 | 248.39 → 252.64 **门内**（剪 1 的黑）；之后第 6 幕（晨从黑里亮起，包没交）；第 10 幕的白归镜与白 | 门内调 `overlay.SetFlat(…, LanbaiDeltaEV(t))` 自己补 ΔEV。场景里只放一个 |

---

## 9. 一幕一幕导入（拷什么、点什么、接什么、勾什么）

每加一个包：拷 → 点包自己的搭建菜单 → **`蓝白/Director/1 Generate Dispatcher` → 等编译 → `2 Wire Scene` → `3 Report`**（打印每个驱动的窗口和重叠，§8 以外的重叠都是错）→ 按 §8.3 填接管开关 → 在包 README 写的机位 / 时刻截图推回 `FromLocal/`。

### 9.0 Director（分发层 v1，`Director/README_Director.md`）

- `LB_Journey` 改两行：`dispatcher.LanbaiDispatch(t)`（在 `ApplyGrades()` **之前**，它要读 `gradeDEV`），出生的 3 秒黑场里 `dispatcher.LanbaiPrewarm()`。
- 分发层是**生成的**（U# 不能用 `SendCustomEvent` 传参）：Generate 把场景里能找到的驱动类写成带类型的字段；Wire 建 `Lanbai/Director` 并填字段。tick 顺序 = 类名排序（Gate 在 Inside 之前，D-22 补充靠它）。
- 反射立方图：`蓝白/Director/Bake Reflection Cubes`（`Director/ReflectionBakes.json`）。

### 9.1 天空套件（`Sky/`，第 1–3、11–12 幕，也给别的幕供预设）

- 拷 `Sky/`；`蓝白/Sky/Build Star Mesh` → `蓝白/Sky/Build Sky (one material + preset objects)`：一个天空盒材质 + 预设物体 + 两个驱动实例（`Lanbai_SkyDriver_Acts1to3`、`_Acts11to12`）。
- 门、门内、第 9 幕都从 `SkyPresets.json` / `FogPresets.json` 读数，**天空要先拷**，不然门的 Build Driver 会警告、只写一条光带色。
- `ownsAtmosphere` / `ownsSkybox` 默认关；要不要让天空写 RenderSettings 见 §8.3 第一行。
- 显存：星图 BC7 42.7 MB、HDRI 立方图每张 31.9 MB（账本 §6）。

### 9.2 第 4 幕：门（`Gate/`、`GateClouds/`、`Tear/`、`Tentacles/`）

- 拷四个文件夹 → `蓝白/Gate Clouds/Build` → `蓝白/Gate/Build Driver`（调试用 `Build Driver + Test Clock`，只在 Play 里）。
- `LanbaiGateDriver` 挂在常开的物体上，`LanbaiActivate` 只开关 `GateRoot`、`NearRoot_bus`。窗口 113.80 → 181.55。
- 写：门自己的 13 个全局量 + [U6, U9) 的天雾月星（§8.1）；车厢裂口光、补光。**不写** RenderSettings、主光、PPv2。
- 门测试脚本的补丁：`GateClouds/给本地_补丁_LB_GateTest_Run.md`（本地改，门不动 `FromLocal/`）。
- 性能：第 4 幕估算 10.3–12.1 ms，预算按 D-27 是热点例外 ≤ 7.1 ms，**等本地 U7 / U8 / U8+7 实测**，砍法顺序见账本 §5。Udon：门的驱动估 0.5–0.8 ms/帧，要本地量。

### 9.3 第 4c、5 幕：门内 + 遮罩 v2（`Act04c_Inside/`、`Overlay/`）

- 拷两个文件夹 → `蓝白/Build/Overlay`（场景只要一个）→ `蓝白/Build/04c 门内`。
- 手接三个引用：`overlay`、`exposure`（接上也不勾 `writeExposure`）、`worldMainLight`（空着会按名字接 `Gate_Lights/Moon`）。
- 窗口 177.55 → 252.64；从 177.55 起 `InsideRoot` 就开着，但在顶点阶段塌缩，画面不变。
- 勾 `writeRenderSettings`、`writeMainLight` 的前提：§8.3 的两个窗口已经填好。
- `ApplyGrades` 里删掉 FLASH_TEAR 自算（§8.4）。天窗光斑（U8 → U9）同一个菜单建。

### 9.4 第 7 幕：7a + 7c（`Sea/`、`Act07_Sea/`；7b 宫殿还没交）

- 拷 `Sea/` → `蓝白/Sea/Create Materials`；拷 `Act07_Sea/` → `蓝白/Build/Act07a`（7c 在同一个驱动里）。合 `cues_v21_patch.json`。Vertex Compression 不勾 TexCoord0–2。
- `worldSun` = 世界主光（空着自动接 `RenderSettings.sun`）。7c 车窗的水线要手复制玻璃网格（`README_Act07a.md` 第 11 步）。
- 窗口 362.26 → 923.36；入水 / 出海时刻和旧占位见 §5 第 5 条；第 7 幕里**关掉 `seaA/seaB`、`deepGroup`**。
- 写 `_Udon_T`（这一段分发层不写它，登记表已改）。
- **第 7 幕的常驻窗口里，海、宫殿、鱼、海雪要同时放得下**（账本 §6）；7c 的倒置窗按 D-26 从车厢地板的侵蚀洞里看（车厢包做）。

### 9.5 第 9 幕：星海（`Act09_StarSea/`）

- 依赖天空套件（主星是天空的 `Lanbai_Stars_BSC5`）。拷 → `蓝白/Build/Act09`。
- 窗口 992.06 → 1149.31；1001.21 起接天雾星（§8.1）。**第 8 幕的驱动在 t ≥ 1001.21 不许再 `Apply`**——第 8 幕的包交来时要查。
- 两个星的 renderer 搭建时关着，由 Tick 开。

### 9.6 还没交的（这几格在 §8 里写着“等包”）

第 6 幕晨、第 8 幕暮（「云」）、7b 宫殿、第 10 幕白（镜与白）、第 11 幕灯与假醒、车厢。每个交来时总工程师照 §8 核一遍交接，再在这里加一节。
