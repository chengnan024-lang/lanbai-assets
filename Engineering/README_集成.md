# 全片集成说明（给本地，也给每个包）· v0

维护：总工程师。**随包更新**：每个包合进 main，这里加一节“这个包怎么接”。v0 先定规矩（谁写什么），具体到包的接线等包交了再补。

> 还没进 main 的东西：`Director/`（分发层 v1，总导演的工作流在做）、`Common/Tools~/compile_check/`。它们进了 main 以后归总工程师维护，本页会跟着改。

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

1. `Common/`（`LanbaiVR.cginc`、`LanbaiFog.cginc`、`LanbaiSky.cginc`、`LanbaiCaustics.cginc`）→ `Assets/Lanbai/Common/`。别的包的 shader 都 include 它们。
2. `Grading/` → 跑 `蓝白/Grades/Build Profiles & Volumes`（已经做过）。
3. 之后每个包按 main 的合并顺序（= 旅程顺序）。每个包的 README 第一节写“拷哪些文件夹、点哪个菜单”。

（包交了以后在这里一节一节补：拷什么、菜单、驱动挂在哪、分发层里填什么、接管开关勾哪个、本地截图的机位和时刻。）
