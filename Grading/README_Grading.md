# 蓝白 / Lanbai · 调色套件（PPv2 Grade Builder）· 修正版

这是美术圣经 **v2.1** 的 **§1.4 调色管线、§1.5 曝光与校准、§1.7 LUT、§1.8（曝光事件）、附录 B** 的落地工具：
15 个场景 profile + 6 个助手 / 镜头层 profile，**全部由生成器从 json 写成静态 C#**（没有手抄的数），一键建好全部 volume；
自带调色测试卡（灰阶 + 饱和色两行）、灰卡白卡、校准球、LDR 中性 LUT 验证、bloom 颜色探针，以及**自动测量并出报告**的工具；
另有给 Director 用的 UdonSharp 曝光助手 `LanbaiExposure`（EXPO_UP / EXPO_DOWN 的权重公式）。

> ⚠ **所有 C# 与 shader 都没有在 Unity 里编译或运行过**（我们这边没有 Unity）。
> 我们做过的检查见 §9：C# 用 Roslyn 对 Unity 2021.1 的引用程序集编译了两遍——一遍对 PPv2 公开 API 的桩，**一遍对真实的 PPv2 3.0.2 运行时源码**——
> 警告即错误，0 警告；数据类和 U# 的静态数学真的执行过并逐值核对；**shader 没有编译过**。
> 第一次在 Unity 里跑时请把 Console 的报错原样回传。

---

## 修正版改了什么（先读这一节）

上一版被复核判为不合格（`verify.md`）。问题不在代码，在数：

**1. 圣经附录 B1 的参数在真实的 PPv2 里显示不出圣经的目标（B1，阻断）。**
美术模拟器按 ACES 色调映射分支的工作空间算 Neutral profile（ACEScc 里做对比，ACEScg 里做白平衡 / LGG / 饱和）。
PPv2 3.x 的 Neutral 实际是：**先在 LogC 里做对比，再在线性 Rec.709 里做白平衡、lift/gamma/gain、饱和**（我们按 `Lut3DBaker.compute` / `Colors.hlsl` / `ColorGrading.cs` 源码逐行核过）。
LogC 对比把线性的黑推到 0 以下，夜间那点 lift 拉不回来：照 B1 建，15 个 profile 有 14 个测试卡超差（最多 13 码），夜黑塌成 `#000000`，违反 §1.3.5。

**修法（圣经法律第 1 条：屏幕目标是法律，参数只是起点）：** 目标一个都没动，参数按真实引擎重解。
- 新增两层数：**外观定义** = `grades_final.json` / 圣经 B1（只在美术模拟器里成立，留作记录）；**引擎参数** = `Tools~/inputs/grades_engine.json`（`Tools~/engine/solve_engine_grades.py` 解出来，套件实际写进 profile 的数）。
- 求解目标：§C 测试卡 11 格、输入 0 的黑点（夜间不压红，S7a 按圣经正文 `#030B0F`）、§A / §B / §D 的每一个屏幕目标、每幕预览测试帧的 4000 个像素、它最饱和的 1000 个像素、它交叉淡化邻居的画面，以及 800 个随机色。
- **新增 Channel Mixer**（每个场景 profile 9 个数，离恒等最多 5.3 个百分点）：线性 709 里的一个 3×3 正好就是“换一套原色”，它让引擎复现外观在 ACES（AP1）空间里对饱和色的处理——**站牌的靛、裂口伤边的紫、尾灯、钠灯、海的饱和蓝**。同一个求解器、同样的样本、只是不加 Mixer 时（试算过），§B 里饱和的填值在引擎里最多差 9–30 码（S1 尾灯、S7a / S7b 的饱和蓝）；加了以后改填前最多 4 码，按 §3 末表改填后 ≤ 3 码。测试卡第二行（8 个饱和色放进每一个 profile，包括它们根本不出现的幕）与外观最多差 11 码，换成色差 ΔE76 ≤ 4.7（`Docs~/TestCard_ColourRow.png`）。
- postExposure、bloom、所有助手、colorFilter、hueShift：**与圣经完全相同**。所以 Director 的 b、表 B3 的全部权重、每个 bloom 的 T0 都不变。
- 结果（两个按 PPv2 源码独立写成的模型一致；**这是模型的结论，Unity 里的实测要靠 §2 第 7 步**）：§C 15 × 11 格全部 ≤ 3 码；每个夜间黑点回到蓝黑、红通道 ≥ 1；§A 灰卡读数 ≤ 3 码；§B 96 个填值 ≤ 3 码（其中少数要改填，见 §3 末表）；§D 遮罩 ≤ 1 码；交叉淡化与助手叠加的中途与外观 p99 ≤ 4 码（`Docs~/xfade_report.txt`）；每幕预览帧与外观 p99 ≤ 3 码（单像素最大 12 码，出在仍用旧填值的高饱和发光体上，§3 末表已为它们改填）。图：`Docs~/Verify_SC_vs_PPv2_Neutral_fixed.png`（修正后）对比 `Docs~/Verify_SC_vs_PPv2_Neutral.png`（修正前），`Docs~/Engine_vs_Look_1/2.png`、`Engine_vs_Look_Shadows.png`（整帧与暗部 ×5）。

**2. 自检是循环论证（M1，主要）。** 旧的核对器拿同一个错的模拟器验算，所以没抓到 1。现在 `Tools~/verify_grade_data.py` 的 D 段是**引擎门限**：生成的 C# 数字过两个按 PPv2 源码写的模型（复核者的 `verify_indep/ppv2_neutral_check.py` 当门限，求解器的 `engine/ppv2_engine.py` 必须与它一致），§C、黑点、§A/§B/§D 不过就是 FAIL。美术模拟器只剩一行“仅供参考”的记录核对（D0）。测试卡参考图的脚注也改成了按数据生成的、真实的话。

**3. 小项：**
- **bloom 颜色被线性化了两次（m1）：** PPv2 的 Bloom 先 `color.linear` 再 `MaterialPropertyBlock.SetColor`，而 SetColor 在 Linear 工程里会再转一次。暖 / 冷的 bloom 会比设计的浓。套件默认写入**补偿后的颜色**（§3 表里的“补偿后”），并带一个**自动探针**（`Probe Bloom Colour`）在你们的 Unity 里实测到底转了一次还是两次，自动切换。
- **postExposure 的修整会被重建覆盖（m2）：** 现在 Build 会在报告里列出它覆盖掉的每一个不同的值。修整（§1.5 的 ±15% APL）请回传给美术侧改进 json，不要手改 profile 资产（§10）。
- **测量相机看得见 Bus 层（m3）：** 色片趟现在只渲染 `LanbaiDebug` 层；灰卡白卡另拍一趟（卡前 0.7 m，加卡片所在层）。
- **Undo（m4）：** profile 资产的修改不再记进 Undo（记了反而会在 Ctrl+Z 后留下孤儿子资产）。要回到数据，直接重跑 Build。场景里的 volume 仍可撤销。
- **`CurrentBase()` 算进了被关掉的 volume（m5）：** 现在跳过 GameObject 不活动的场景 volume（与 PPv2 一致）。**仍然请只用 weight 驱动场景 volume，永远不要关它的组件**（组件的 enabled 在 Udon 里不一定读得到，我们没有去碰）。
- **Route C 一键备用：** `蓝白/Grades/Route C/...` 用 `art/luts/hdr_external/*_HDRext33.cube`（外观本身烘成的 LUT）建 External profile 并切换；不依赖我们对 PPv2 调色数学的建模。只在测量证明 Route A 有问题时用（§6.4）。
- **圣经 v2.1：** 表 B3 换成 v2.1 的事件与权重（出海“钉住 → 放开”、入水按 S6 / S7a 两个底值、银河点燃不再是曝光事件），时间换成实测秒。

---

## 0. 文件清单

| 路径 | 是什么 |
|---|---|
| `Editor/LanbaiGradeData.cs` | **生成的**静态数据：21 个 volume 的每一个覆盖参数（引擎参数）、优先级、初始 weight、§C 目标、引擎模型对测试卡与黑点的预测、外观定义记录、Route C 的 LUT 名、测试卡第二行。不要手改。 |
| `Editor/LanbaiGradeBuilder.cs` | 菜单 `蓝白/Grades/Build Profiles & Volumes` 等：建 profile 资产与 volume、校验、配置参考相机、bloom 颜色补偿开关、Route C、Animator 退路。 |
| `Editor/LanbaiGradeTestCard.cs` | 菜单 `蓝白/Grades/Test Card` 等：测试卡（两行）、灰卡白卡、校准球、测量模式、LDR 中性 LUT 验证、bloom 颜色探针、自动测量；以及 `Debug Window`。 |
| `Editor/Lanbai.Grading.Editor.asmdef` | Editor 程序集定义，引用 `Unity.Postprocessing.Runtime`（见 §1.3）。 |
| `Runtime/LanbaiExposure.cs` | **UdonSharp** 组件：EXPO 权重公式（静态函数）+ 一站式实例方法；标记之间那段由生成器写。 |
| `Shaders/Lanbai_TestPatch.shader` | 测试卡色片用的无光照 shader（`Lanbai/Debug/TestPatch`：`_Emission` 是 float、`_Tint` 是 Vector，都不经颜色转换，不吃雾）。 |
| `LUT/Lanbai_Neutral_1024x32.png` | 中性（恒等）LUT 条带，给 §1.7 的方向验证用。 |
| `Docs~/TestCard_Reference.png` | 15 个 profile × 11 格的 §C 目标 + 引擎预测之差 + 黑点（目标 / 预测）。 |
| `Docs~/TestCard_ColourRow.png` | 测试卡第二行（8 个饱和色）在每个 profile 下的外观值与引擎预测之差。 |
| `Docs~/TestCard_Layout.png` | 测试卡 rig 的正视图尺寸、黑点取样位置、两趟测量 + volume 叠放图。 |
| `Docs~/Verify_SC_vs_PPv2_Neutral.png` / `…_fixed.png` | 复核者的图：§C 目标 vs 真实 Neutral 通路，修正前（B1 参数）/ 修正后（套件参数）。 |
| `Docs~/Engine_vs_Look_1.png`、`_2.png`、`Engine_vs_Look_Shadows.png` | 每幕的预览测试帧：外观（目标）/ 修正前 / 修正后，含 bloom；以及暗部 ×5 与黑点。 |
| `Docs~/verify_report.txt` | 核对器的结果（含引擎门限）。 |
| `Docs~/xfade_report.txt` | 交叉淡化（11 对，每对 5 个 weight）与助手叠加（表 B3 的权重）在引擎参数下与外观的差。 |
| `verify.md` | 复核报告（上一版的问题；本版的处理见上一节与 §11）。 |
| `Tools~/engine/` | `ppv2_engine.py`（PPv2 Neutral 通路模型）、`solve_engine_grades.py`（引擎参数求解）、`engine_calib.py`（§A/§B/§D 过引擎、改填值、测试卡第二行）、`compare_frames.py`（画 Engine_vs_Look）、`xfade_check.py`（交叉淡化与助手叠加的中途）。 |
| `Tools~/gen_grade_data.py` | 生成器：`grades_engine.json` + `grades_final.json` + `calib_final.json` + `calib_engine.json` → C#、U# 生成段、本文件 §3 的表。 |
| `Tools~/verify_grade_data.py` | 核对器：C# 解析回来逐值比对、编译执行结果比对、**引擎门限**、圣经附录 B、sha256 链、在临时目录里重新生成并逐字节比对。 |
| `Tools~/verify_indep/` | 复核者的独立工具（已更新到修正版：`ppv2_neutral_check.py` 默认检查套件实际的数，`--grades …/grades_final.json` 重现原问题）。 |
| `Tools~/make_reference.py` | 画 `Docs~/TestCard_*.png`（数据取自解析回来的 C#）。 |
| `Tools~/compile_check/` | 编译检查用的桩与脚本（不进 Unity）。 |
| `Tools~/inputs/` | 本次生成所用 json 的快照。 |

以 `~` 结尾的文件夹 Unity 不会导入，放在 `Assets/` 里也没关系。

---

## 1. 导入

1. 把整个 `Grading/` 文件夹放进项目，建议 `Assets/Lanbai/Grading/`（路径随意：脚本按自己所在位置找，profile 会建在 `<这个文件夹>/Profiles/`）。**这一版替换上一版的全部文件**（Profiles/ 与 TestCard/ 是工具建的，保留即可，重跑会原地更新）。
2. 依赖：**Post Processing（com.unity.postprocessing）3.x**。用到的 API（`AddSettings<T>()`、`ParameterOverride<T>.Override()`、`SetAllOverridesTo()`、Channel Mixer 的 9 个 `mixer…` 参数、`PostProcessVolume.sharedProfile/priority/weight/isGlobal`、`GradingMode.External` / `externalLut`……）从 3.0.2 到 3.6.0 一致。**UdonSharp 1.x**、VRChat SDK Worlds。
3. **asmdef：默认保留。** `Editor/Lanbai.Grading.Editor.asmdef` 只含 Editor 平台，引用 `Unity.Postprocessing.Runtime`。
   如果 Unity 报 “Assembly has reference to non-existent assembly 'Unity.Postprocessing.Runtime'”，删掉它（连同 .meta）：所有 Editor 脚本进 `Assembly-CSharp-Editor`，**两种布局我们都编译过**。
   `Runtime/LanbaiExposure.cs` 故意**不在任何 asmdef 里**；不要把它挪进 Editor 文件夹。
4. LUT PNG 的导入设置由工具自动改好（§1.7）。也可以手动跑 `蓝白/Grades/Fix LUT Strip Import Settings`。
5. **不要把显示层 `.cube` 放进 `Assets/`**（§1.7）。只有走 Route C 时，才把 `art/luts/hdr_external/*_HDRext33.cube` 这 15 个放进 `Assets/` 任意位置（PPv2 会把它们导入成同名 Texture3D）。

---

## 2. 第一次使用（按顺序，约 15 分钟）

所有菜单都在 **`蓝白/Grades/`** 下。每个菜单背后都是一个**返回字符串的 public static 方法**（§7），远程小助手可以用反射直接调，**全程没有弹窗**。

1. **`Build Profiles & Volumes`**（`LanbaiGradeBuilder.BuildAll()`）
   - 若没有名为 `PostProcessing` 的层，就建在第一个空的用户层（22–31）里。
   - 在 `<套件>/Profiles/` 建（或原地更新）21 个 profile：`Lanbai_PP_S1.asset` … `Lanbai_PP_LENS_ARCHIVE.asset`。
   - 在当前场景根部建（或更新）`Lanbai_Grades`：`Scenes/PPV_S1…PPV_S12`、`Helpers/PPV_EXPO_UP…`、`Lens_DesktopOnly/PPV_LENS_CLEAN, PPV_LENS_ARCHIVE`，全部 **Is Global、层 PostProcessing、priority 取自 json**。
   - **初始 weight：S1 = 1、LENS_CLEAN = 1，其余全 0**（圣经 §1.4：桌面镜头层“始终为 1，包括第 1 幕”；VR 里它的父物体会在 Start 被关掉）。
   - **profile 资产的改动不进 Undo**（Ctrl+Z 只撤销场景里的 volume）：要回到数据，直接再跑一次 Build。
   - **重复运行是幂等的**。从上一版升级时，第一次重建会把旧的 B1 参数全部换成引擎参数，报告的 “Build log” 会把被替换的值逐个列出——这是预期的。
   - 之后自动校验并写报告 `<项目>/LanbaiReports/GradeBuild_Report.md`：每个 profile 的效果与覆盖参数（场景 profile 必须是同一套 **31 个**）、资产里每个数值与数据表的比对、场景里**不是我们的** PostProcessVolume、被关掉的 volume、参考相机与项目设置、当前 Route 与 bloom 颜色模式。
2. **`Configure Reference Camera (PostProcessLayer)`**：按 §1.4 设 VRC 场景描述符的 ReferenceCamera：Allow HDR 开、near 0.05、far 45 000、Clear = Skybox；PostProcessLayer：Volume Layer 只含 `PostProcessing`、Trigger = 相机本身、Anti-aliasing None、Stop NaN 开、Directly to Camera Target 关。
   **还要手动做一件事：** Project Settings → Graphics → Tier Settings（Standalone 三档）**HDR 开、HDR Mode = FP16**。PPv2 3.x 的 Dithering 在 final pass 里永远是开的，正是圣经要的。
3. **关掉旧 build 的 volume**：`GradeBuild_Report.md` 的 “Scene” 一节列出了它们。
4. **`Test Card`**（`LanbaiGradeTestCard.Build()`）：建（或更新）`Lanbai_TestCard`。把它拖到主座位前 1.2–1.6 m、正面朝着座位（`Docs~/TestCard_Layout.png`）。旧的 rig 重跑一次就会长出第二行色片、黑底变高。
5. **`Verify Neutral LUT (LDR, contribution 0 vs 1)`** → 必须 **PASS**（§1.7 “先验证方向”）。
6. **`Probe Bloom Colour (single or double sRGB decode)`** → 报告写进 `BloomColour_Report.md`。结论是 “double” 时保持默认（写补偿后的颜色）；是 “single” 时它会自动切换并重建 profile。我们按源码判断是 double（约八成把握），所以默认补偿。
7. **`Measure Test Card (all 15 profiles)`** → **预期 PASS**：每个 profile 单独 weight 1、测量模式下自动读 11 格 + 黑底（输入 0），与 §C 和圣经的黑点比（±3 码）；同时读第二行饱和色，与外观和引擎模型比。**S10 那一行是自检**：k 0 必须读 `#767676`。报告的 “Unity vs the art side's model” 一节会告诉你，如果有 FAIL，是我们的解偏了（Unity = 模型 ≠ 目标）还是我们的引擎模型偏了（Unity ≠ 模型）。**任何一种都请不要手调参数**，把报告回传。
8. 在 `Lanbai_Grades` 根物体上 **Add Component → LanbaiExposure**（U# 1.x 会自动建 Udon 程序资产）。它在 Start 里按名字连好所有 volume。
9. **保存场景**（工具只把场景标脏）。把整个 `<项目>/LanbaiReports/` 推到 `FromLocal/`（圣经 §9 第 3、11、12 条要的东西就在里面）。

---

## 3. 生成出来的参数（引擎参数；与 json 逐值核对，并过了引擎门限）

**写进 Unity 的是第一张表。第二张表的“外观定义”是圣经 B1 的数，只在美术模拟器里成立，不要输进 Unity。**

<!-- lanbai:generated:table (Tools~/gen_grade_data.py; do not hand-edit) -->

**场景 profile · 引擎参数（真正写进 profile 的数；15 个；每个都覆盖同一整套 31 个参数；HDR + Neutral；colorFilter `#FFFFFF`、hueShift 0；bloom clamp 4.24（gamma）、anamorphicRatio 0、fastMode true；Vignette / Grain intensity 0）**

| Volume | 优先级 | 初始 weight | postExp | 色温 | 色调 | 饱和 | 对比 | lift | gamma | gain | Channel Mixer（R / G / B 三行，%） | bloom 强度 / 阈值 / 软膝 / 扩散 / 颜色（写入值） | T0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PPV_S1` 站牌 | 1 | 1 | +0.00 | -2.50 | +5.94 | -12.20 | +6.58 | (0.9736, 0.984, 1, 0.02) | (0.9689, 0.9837, 1, -0.085) | (0.9875, 1, 0.9934, 0.1257) | (97.36, 3.74, -4.88) / (-0.91, 102.65, -0.54) / (0.45, 1.71, 99.73) | 4 / 1.69 / 0.6 / 8 / `#FFFFFF` | 1.269 |
| `PPV_S2` 夜路 | 2 | 0 | -0.15 | -3.94 | +3.11 | -21.78 | +3.19 | (0.9726, 0.9836, 1, 0.0161) | (0.9697, 0.9818, 1, -0.0944) | (1, 0.9968, 0.9733, 0.1504) | (98.75, 1.15, -1.4) / (-0.86, 101.59, -0.53) / (-0.38, 0.63, 99.91) | 3.5 / 1.8 / 0.6 / 7.5 / `#FFFFFF` | 1.458 |
| `PPV_S3` 月海 · 基准 EV0 | 3 | 0 | -0.90 | -4.34 | +1.96 | -1.54 | +5.49 | (0.9696, 0.9818, 1, 0.0212) | (0.9747, 0.985, 1, -0.1194) | (0.9971, 1, 0.9975, 0.2036) | (99.8, 0.29, -3.45) / (-0.82, 101.3, -0.57) / (1.31, 2.3, 99.14) | 3.5 / 1.99 / 0.5 / 7 / `#FFFFFF` | 2.272 |
| `PPV_S4` 触手之门 | 4 | 0 | -0.85 | -4.19 | -0.26 | -5.17 | +6.89 | (0.9773, 0.9797, 1, 0.0202) | (0.987, 0.9838, 1, -0.1226) | (0.9986, 1, 0.998, 0.2146) | (100.23, -0.47, -3.44) / (-1.12, 101.15, -0.39) / (1.16, 2.93, 98.85) | 5 / 1.93 / 0.5 / 8.5 / `#F0F0F6`（补偿后 ≈ `#F8F8FB`） | 2.124 |
| `PPV_S4c` 门内 | 5 | 0 | -0.90 | -2.89 | +1.65 | -13.56 | +0.80 | (0.9824, 0.9835, 1, 0.0061) | (0.9893, 0.9814, 1, -0.0699) | (0.9994, 0.991, 1, 0.1188) | (99.81, 0.11, -1.08) / (-0.73, 100.56, -0.28) / (0.08, 0.42, 99.86) | 6 / 2.69 / 0.7 / 9 / `#F2F3F6`（补偿后 ≈ `#F9FAFB`） | 2.646 |
| `PPV_S6` 晨 | 6 | 0 | -0.75 | -3.79 | -0.54 | +4.28 | +3.23 | (0.9801, 0.9902, 1, 0.0083) | (1, 0.995, 0.9974, -0.0425) | (1, 0.9861, 0.9426, 0.0615) | (99.06, 0.66, -1.13) / (-0.37, 101.37, -0.18) / (0.37, 1.75, 99.62) | 4 / 2.24 / 0.6 / 8.5 / `#FFF4E8`（补偿后 ≈ `#FFFAF5`） | 2.358 |
| `PPV_S7a` 海面之下 | 7 | 0 | -0.80 | -2.15 | +1.43 | +8.38 | -12.20 | (0.9619, 0.9898, 1, 0.0128) | (0.9738, 0.9878, 1, -0.2499) | (0.9855, 0.9957, 1, 0.4132) | (100.36, 0.67, -2.61) / (-0.16, 101.08, 0.47) / (1.33, 2.13, 99.48) | 4 / 2.24 / 0.6 / 8 / `#E8FAFF`（补偿后 ≈ `#F5FDFF`） | 2.358 |
| `PPV_S7b` 深海 · 河伯 | 8 | 0 | -0.40 | -4.59 | +1.39 | +5.96 | +4.16 | (0.9653, 0.9788, 1, 0.0224) | (0.9748, 0.9888, 1, -0.1571) | (0.9974, 1, 0.9978, 0.2687) | (99.76, 0.53, -4.17) / (-0.22, 101.35, -0.9) / (1.36, 1.47, 99.28) | 6 / 1.85 / 0.6 / 7 / `#FFFFFF` | 1.548 |
| `PPV_S8` 暮 | 9 | 0 | -0.50 | +4.86 | +3.32 | +7.63 | +7.86 | (0.9731, 0.9871, 1, 0.0165) | (1, 0.9905, 0.9959, -0.0449) | (1, 0.9701, 0.9025, 0.064) | (99.01, 2.45, -0.7) / (0.1, 101.04, -0.53) / (0.44, -0.57, 99.97) | 6 / 2.02 / 0.6 / 9 / `#FFE6CC`（补偿后 ≈ `#FFF4E7`） | 1.879 |
| `PPV_S8b` 蓝时 | 10 | 0 | -0.30 | -3.98 | +2.83 | +2.13 | +0.92 | (0.9738, 0.9839, 1, 0.0131) | (0.9705, 0.9829, 1, -0.0957) | (1, 0.9996, 0.999, 0.1648) | (100.41, -0.39, -2.76) / (-0.66, 100.51, -0.3) / (0.77, 1.94, 99.31) | 4 / 1.92 / 0.6 / 8 / `#FFFFFF` | 1.680 |
| `PPV_S9a` 星海 | 11 | 0 | +0.30 | -3.87 | +1.88 | +4.32 | +3.36 | (0.9675, 0.9802, 1, 0.0199) | (0.9791, 0.9872, 1, -0.1407) | (1, 0.998, 0.9976, 0.256) | (100.95, -0.84, -4.27) / (-0.42, 100.61, -1) / (1.3, 3.42, 98.68) | 5 / 1.72 / 0.7 / 6 / `#FFFFFF` | 0.989 |
| `PPV_S9b` 星海高潮 | 12 | 0 | +0.30 | -1.80 | +1.32 | +0.40 | +9.44 | (0.9712, 0.9824, 1, 0.025) | (0.9877, 0.991, 1, -0.1017) | (1, 0.9992, 0.998, 0.1978) | (100.6, -0.45, -5.31) / (-1.24, 100.75, -1.31) / (0.79, 3.19, 98.64) | 8 / 1.7 / 0.7 / 8 / `#F4F8FF`（补偿后 ≈ `#FAFCFF`） | 0.964 |
| `PPV_S10` 白 · 中性 | 13 | 0 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | (1, 1, 1, 0) | (1, 1, 1, 0) | (1, 1, 1, 0) | (100, 0, 0) / (0, 100, 0) / (0, 0, 100) | 0 / 1.8 / 0.6 / 7.5 / `#FFFFFF` | 1.458 |
| `PPV_S11` 假醒 (= S2) | 14 | 0 | -0.15 | -3.94 | +3.11 | -21.78 | +3.19 | (0.9726, 0.9836, 1, 0.0161) | (0.9697, 0.9818, 1, -0.0944) | (1, 0.9968, 0.9733, 0.1504) | (98.75, 1.15, -1.4) / (-0.86, 101.59, -0.53) / (-0.38, 0.63, 99.91) | 3.5 / 1.8 / 0.6 / 7.5 / `#FFFFFF` | 1.458 |
| `PPV_S12` 醒 | 15 | 0 | +0.00 | -3.01 | +3.97 | -5.35 | +5.29 | (0.9748, 0.9848, 1, 0.0178) | (0.9753, 0.9877, 1, -0.0743) | (0.9953, 1, 0.997, 0.1129) | (99.21, 1.37, -4.02) / (-0.59, 101.28, -0.22) / (0.53, 2.11, 99.5) | 3.5 / 1.72 / 0.6 / 7.5 / `#FFFFFF` | 1.319 |

**同一批 profile 的“外观定义”（圣经附录 B1 / `grades_final.json`；只在美术模拟器里成立，仅供对照，不要输进 Unity）与引擎预测**

| Profile | 色温 | 色调 | 饱和 | 对比 | lift | gamma | gain | 黑点目标（输入 0） | 引擎预测黑点 | §C 引擎预测最大误差 |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | -4 | +3 | -15 | +12 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 1, 1, 0) | `#02060D` | `#02060D` | 1 码 |
| S2 | -4 | +3 | -22 | +10 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 0.99, 0.97, 0) | `#02060C` | `#02060C` | 1 码 |
| S3 | -6 | +3 | -6 | +14 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 1, 1, 0) | `#01060E` | `#01060E` | 1 码 |
| S4 | -6 | +2 | -10 | +16 | (0.99, 0.99, 1, 0.006) | (0.98, 0.98, 1, 0) | (1, 1, 1, 0) | `#03040C` | `#03030C` | 1 码 |
| S4c | -3 | +2 | -14 | +6 | (0.99, 0.99, 1, 0.004) | (0.985, 0.98, 1, 0) | (1, 0.99, 1, 0) | `#02020A` | `#02020A` | 1 码 |
| S6 | -4 | +0 | +2 | +6 | (0.99, 0.993, 1, 0.004) | (0.995, 0.997, 1, 0) | (1, 0.98, 0.94, 0) | `#000309` | `#000309` | 1 码 |
| S7a | -4 | +1 | +4 | +8 | (0.99, 0.995, 1, 0.008) | (0.975, 0.985, 1, 0) | (0.985, 0.995, 1, 0) | `#030B0F` | `#030B0F` | 3 码 |
| S7b | -6 | +2 | +2 | +16 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 1, 1, 0) | `#01060E` | `#01060E` | 1 码 |
| S8 | +3 | +1 | +5 | +10 | (0.985, 0.99, 1, 0.006) | (0.99, 0.993, 1, 0) | (1, 0.965, 0.9, 0) | `#00050D` | `#00050D` | 1 码 |
| S8b | -5 | +4 | +0 | +8 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 1, 1, 0) | `#01060E` | `#01060E` | 1 码 |
| S9a | -6 | +4 | +0 | +14 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 1, 1, 0) | `#01060E` | `#01060E` | 1 码 |
| S9b | -4 | +3 | -4 | +16 | (0.9875, 0.9905, 1, 0.008) | (0.975, 0.985, 1, 0) | (1, 1, 1, 0) | `#01060E` | `#01060D` | 1 码 |
| S10 | +0 | +0 | +0 | +0 | (1, 1, 1, 0) | (1, 1, 1, 0) | (1, 1, 1, 0) | `#000000` | `#010101` | 1 码 |
| S11 | -4 | +3 | -22 | +10 | (0.9875, 0.9905, 1, 0.008) | (0.97, 0.98, 1, 0) | (1, 0.99, 0.97, 0) | `#02060C` | `#02060C` | 1 码 |
| S12 | -4 | +3 | -8 | +10 | (0.9875, 0.9905, 1, 0.008) | (0.975, 0.985, 1, 0) | (1, 1, 1, 0) | `#01060D` | `#01060D` | 1 码 |

**助手与镜头层（只覆盖列出的参数；与圣经表 B2 相同）**

| Volume | 优先级 | 初始 weight | 覆盖的参数 | weight 怎么走 |
|---|---|---|---|---|
| `PPV_WHITE_BLOOM` | 96 | 0 | bloomIntensity 12；bloomThreshold 0.8；bloomSoftKnee 0.8；bloomDiffusion 9；bloomColor #EEF4F8（补偿后 ≈ #F7FAFC） | crash 0 -> 0.5, swell -> 1.0, then 1 -> 0 EV-linearly WITH the 3 s overlay (so the overlay itself never blooms) |
| `PPV_WHITE_SAT` | 96 | 0 | saturation -30 | = white-ramp fraction: 0 -> 0.42 (crash) -> 1.0 (swell); hard-cut to 0 under the full overlay |
| `PPV_EXPO_DOWN` | 99 | 0 | postExposure -4 | -dEV / (b + 4) |
| `PPV_EXPO_UP` | 100 | 0 | postExposure 4 | dEV / (4 - b) |
| `PPV_LENS_CLEAN` | 199 | 1 | vignetteMode Classic；vignetteColor #02040A；vignetteCenter (0.5, 0.5)；vignetteIntensity 0.2；vignetteSmoothness 0.4；vignetteRoundness 1；vignetteRounded false；grainColored false；grainIntensity 0.06；grainSize 0.8；grainLumContrib 0.8 | 1 everywhere on desktop (scene 1 included); LENS_ARCHIVE sits above it |
| `PPV_LENS_ARCHIVE` | 200 | 0 | vignetteMode Classic；vignetteColor #02040A；vignetteCenter (0.5, 0.5)；vignetteIntensity 0.26；vignetteSmoothness 0.45；vignetteRoundness 1；vignetteRounded false；grainColored false；grainIntensity 0.2；grainSize 1；grainLumContrib 0.85 | U0 0 -> 1 over 8 s (the record starts); U3 1 -> 0 over 8 s (the sound opens); 10->11 0 -> 1 under the white; 11->12 1 -> 0 under the second white |

**`calib_final.md` §B 里要改填的值（引擎版；其余 87 项照 `calib_final.md` 原样填，引擎下误差 ≤ 3 码）**

| 幕 | 元素 | 屏幕目标（不变） | `calib_final` 的填值 → 引擎显示 | **引擎版填值** → 引擎显示 |
|---|---|---|---|---|
| S1 | 远镇钠灯点 | `#DC8F51` | `#FF7C00 @ +0.30` → `#DF8D51`（差 3） | **`#FF8103 @ +0.24`** → `#DD8F51`（差 1） |
| S1 | 尾灯 | `#B2252C` | `#CB1500` → `#B6272D`（差 4） | **`#C51104`** → `#B2252C`（差 0） |
| S3 | 光之海 钠灯 | `#E8A050` | `#FF8525 @ +1.48` → `#EC9E4F`（差 4） | **`#FF8B29 @ +1.38`** → `#E9A050`（差 1） |
| S3 | 橙色云底（城市照亮） | `#7A4A2A` | `#AA652C` → `#7E492A`（差 4） | **`#A5672D`** → `#7A4A2A`（差 0） |
| S7a | 全反射暗镜 | `#11395E` | `#2C4B72` → `#14395E`（差 3） | **`#294B72`** → `#11395E`（差 0） |
| S9a | 镜线 | `#DCE8FF` | `#8D95FF @ +1.89` → `#D9E8FF`（差 3） | **`#9095FF @ +1.89`** → `#DCE8FF`（差 0） |
| S9b | 星尘 | `#CDBF9C` | `#D0B784` → `#D0BF9A`（差 3） | **`#CCB686`** → `#CDBF9C`（差 0） |
| S11 | 头顶的海 | `#0F2438` | `#0F283C` → `#122438`（差 3） | **`#09283C`** → `#0F2438`（差 0） |
| S12 | 远镇灯 | `#E0914A` | `#FF7E1E @ +0.40` → `#E3904A`（差 3） | **`#FF8220 @ +0.33`** → `#E1914A`（差 1） |
| S12 | Lichtchen 核心 | `#FCF5DA` | `#FFC985 @ +1.83` → `#FFF5DA`（差 3） | 不改：在 ±3 以内，重解会削掉它的 bloom（×T0 2.70 -> 2.04） |

§A 灰卡 / 白卡读数（29 项）在引擎里最大差 3 码；§D 遮罩填值（10 项）最大差 1 码，全部照 `calib_final.md` 原样用。

json 里的冲突（生成器按 v2 解决）：

- LENS_CLEAN.grainLumContrib: v1 block lens_desktop_only says 0.9, v2 helpers says 0.8 -> using v2 0.8
- LENS_CLEAN.priority: v1 block lens_desktop_only says 201, v2 helpers says 199 -> using v2 199 (bible 1.4: LENS_CLEAN 199 / LENS_ARCHIVE 200, archive sits above clean)

<!-- /lanbai:generated:table -->

**每个场景 profile 覆盖的 31 个参数（工具会校验“完全相同的一套”）：**
Color Grading：gradingMode（= High Definition Range）、tonemapper（= Neutral）、temperature、tint、postExposure、colorFilter、hueShift、saturation、contrast、lift、gamma、gain、**Channel Mixer 的 9 个（mixerRedOutRedIn … mixerBlueOutBlueIn）**；
Bloom：intensity、threshold、softKnee、clamp、diffusion、anamorphicRatio、color、fastMode；Vignette：intensity（= 0）；Grain：intensity（= 0）。
圣经 §1.4 的 22 个 + Channel Mixer 9 个。S10 的 Mixer 是恒等，但也覆盖：这样任何交叉淡化都不会经过默认值。Curves 不覆盖（= 默认 = 恒等），bloom dirt 不覆盖。
**任何 profile 都没有**：Auto Exposure、Motion Blur、Depth of Field、Chromatic Aberration、Lens Distortion、Ambient Occlusion、SSR（重跑构建器会删掉它们）。

**数值语义（填错最常见的地方）：**
- lift / gamma / gain 是 PPv2 轨迹球的 `Vector4`（xyz = 色轮颜色，最大通道 1；w = 偏移），脚本直接写，不要在 Inspector 里拖。引擎参数里 gamma 的 w 是负的、gain 的 w 是正的：它们一起在线性空间里做出外观在 log 空间里的对比（PPv2 的 LogC 对比在黑附近有趾部，单靠 contrast 做不到）。
- Channel Mixer 的 9 个数是百分比（Inspector 里 Red / Green / Blue 三个输出通道各三个滑条）。
- bloom `threshold` 与 `clamp` 都是 **gamma 空间**的数（clamp 4.24 = 线性 24）。T0 列 = bloom 软膝开始的场景线性值（曝光之前）。引擎里中性灰在 T0 处仍显示为 luma ≈ 228（圣经要的“诗句与受光表面永不 bloom”不变）。
- 颜色都是“在 Inspector 取色器里输入的 hex”。**bloom 颜色**：表里写“补偿后 ≈ …”的，是工具实际写入的值（PPv2 会把它解码两次，落在圣经要的色调上）。colorFilter 全是白，PPv2 原样当线性乘数用。
- **§B 填值**：上面最后一张表列出的那几项，请填“引擎版填值”；其余照 `calib_final.md` 原样填（引擎下误差 ≤ 3 码）。§A、§D 全部照原样。

---

## 4. 给 Director 的权重规则（圣经 §1.4 / §1.8 / 附录 B · v2.1）

### 4.1 场景交叉淡化
- 旧 volume **保持 1**，新的（priority 更高）0 → 1；新的到 1 之后再把旧的设 0。**绝不一升一降**。
- **遮罩（黑 / 白）完全不透明时**：同一帧硬切（旧 1→0、新 0→1），同一帧换遮罩填色（`calib_final.md` §D）。
- 曲线：主要是曝光变化 → weight 对时间线性；主要是颜色变化 → smoothstep；可见的颜色淡化 ≥ 8 秒（时间见圣经 §6.x）。
- **只用 weight。** 不要 `SetActive(false)` 场景 / 助手 volume，也不要关它的组件。引擎参数的交叉淡化我们逐对仿真过（1→2、2→3、3→4、4→4c、6→7a、7a→7b、7b→8、8→8b、8b→9a、9a→9b、9b→10）：淡化中途与外观的差 p99 ≤ 4 码（`Docs~/xfade_report.txt`）。

### 4.2 曝光助手（PPv2 的覆盖是“插值到绝对值”，不是叠加）
EXPO_UP 的 postExposure = **+4**，EXPO_DOWN = **−4**（远目标，只覆盖这一个参数）。每帧：
1. 先改完这一帧的场景 weight；
2. 把这一帧所有曝光事件**加成一个 ΔEV**；
3. b = 场景 volume 混合后的 postExposure（PPv2 的折叠：从 0 开始，按 priority 由低到高 `pe = lerp(pe, pe_i, w_i)`；标准交叉淡化中 = lerp(pe_旧, pe_新, w_新)）；
4. **w = ΔEV / (4 − b)**（ΔEV > 0，EXPO_UP）或 **w = −ΔEV / (b + 4)**（ΔEV < 0，EXPO_DOWN），另一个设 0。结果恰好是 b + ΔEV。

```csharp
// Director（UdonSharp）里，一帧的末尾：
float dEV = beatDecay + flashEV + whiteRampEV + mirrorPulseEV;   // 先相加
float applied = exposure.SetDeltaEV(dEV);                         // 读 b、写 EXPO_UP/DOWN，返回实际加上的 EV
if (overlayVisible)                                               // §1.8：遮罩会被调色，填色要补偿
{
    Color c = fillHDR * LanbaiExposure.OverlayFillScale(applied);  // calib §D 的填值 × 2^(−ΔEV)
    c.a = overlayAlpha;
    overlayMat.SetColor("_Color", c);
}
// 不想用组件也行，纯函数：
float w = LanbaiExposure.WeightUp(dEV, LanbaiExposure.CrossfadeBase(oldIndex, newIndex, wNew));
```

附录 B 表 B3（v2.1）的权重我们用同一公式复算过（`Docs~/verify_report.txt`）：U6k 破云 0.102、U9 管灯 0.062、FLASH_TEAR 0.306、F2h 入水 EXPO_DOWN 0.154（S6 底）/ 0.156（S7a 底）、**出海钉住** EXPO_DOWN 0.675–0.68（7c 末 −2.43 EV）、**放开到 F9** EXPO_UP 0.111、镜子脉冲 0.095、白光冲击 0.270 → 膨胀 0.649、第一次白之后 0.241、第二次白之后 0.200，全部一致。**银河点燃（F13）不是曝光事件**（光源增益线，不用 EXPO）。
**引擎参数没有改动任何 postExposure**，所以这些权重与圣经完全相同。

Route C（External LUT、profile postExposure = 0）用同一公式、b = 0：在 `LanbaiExposure` 上勾 `routeC`（`CurrentBase()` 就返回 0），曝光型交叉淡化（2→3、7b→8、11→12）用 `RouteCCrossfadeWeight(ΔEV, x)`。

### 4.3 其余助手（直接设 weight；时间见圣经表 B2）
- `WHITE_SAT`（饱和 −30）：冲击 0 → 0.42（1137.58 → 1138.78）、膨胀 → 1（→ 1144.78）、保持（→ 1146.31）；遮罩满时（1149.31）硬切 0。
- `WHITE_BLOOM`（12 / 0.8 / 0.8 / 9 / `#EEF4F8`）：冲击 0 → 0.5、膨胀 → 1、保持 1、遮罩 3 秒内 EV 线性 1 → 0（1146.31 → 1149.31）。
- `LENS_ARCHIVE`：U0 0 → 1（3.90 → 11.90）；U3 1 → 0（50.30 → 58.30）；10→11 在白遮罩下 → 1（1178.46）；11→12 在剪 3 → 0（1251.96）。`LENS_CLEAN`：桌面恒为 1；白的膨胀里降到 0（1138.78 → 1144.78）。
- `LanbaiExposure` 提供 `SetWhiteSat / SetWhiteBloom / SetLensClean / SetLensArchive(w)`。

### 4.4 顺序
volume 叠放（priority 低 → 高）：S1…S12（1–15）→ WHITE_SAT / WHITE_BLOOM（96）→ EXPO_DOWN（99）→ EXPO_UP（100）→ LENS_CLEAN（199）→ LENS_ARCHIVE（200）；调试用的 VERIFY_LDR（1000）与 DEBUG_Measure（1001）只在测试卡下面，weight 默认 0，打包时随 EditorOnly 剥离。见 `Docs~/TestCard_Layout.png` 右半。

### 4.5 VR
`LanbaiExposure.Start()` 里若 `Networking.LocalPlayer.IsUserInVR()`，把 `Lens_DesktopOnly` 整个 `SetActive(false)`：**VR 里没有暗角、没有颗粒**（圣经 §1.8；唯一例外是 PPv2 自带的 dithering）。

---

## 5. `LanbaiExposure`（UdonSharp，`BehaviourSyncMode.None`：纯本地）

| 成员 | 作用 |
|---|---|
| `static float WeightUp(dEV, b)` / `WeightDown(dEV, b)` | 公式本体；自动 clamp 到 0–1；方向不对返回 0 |
| `static float AppliedDeltaEV(wUp, wDown, b)` | 在给定权重下实际加上的 EV |
| `static float BlendedBase(float[] sceneWeights)` | PPv2 折叠求 b（索引 = `SceneId` 顺序 = priority 顺序） |
| `static float CrossfadeBase(old, new, wNew)` | 标准交叉淡化的 b |
| `static float OverlayFillScale(appliedEV)` | 2^(−ΔEV)，遮罩填色补偿 |
| `static float RouteCCrossfadeWeight(dEV, x)` | Route C 的 EV 线性交叉淡化权重 |
| `static string SceneId(i)` / `static int SceneIndex(id)` / `static float ScenePostExposure(i)` / `const SceneCount, ExpoUpTarget, ExpoDownTarget` | 生成的表 |
| `SetSceneWeight(i, w)` / `GetSceneWeight(i)` / `CurrentBase()` | 场景 volume 的 weight 与当前 b（跳过 GameObject 不活动的 volume；`routeC` 时为 0） |
| `SetDeltaEV(dEV)` → 实际 EV；`SetDeltaEVWithBase(dEV, b)`；`ClearDeltaEV()`；`GetOverlayFillScale()` | 一站式：读 b、写两个 EXPO |
| `SetWhiteSat / SetWhiteBloom / SetLensClean / SetLensArchive(w)` | 其余助手 |
| `Wire()`、`ApplyVRLensRule()`；字段 `routeC`、`disableLensInVR` | Start 自动调用：按名字连 volume；VR 关镜头层 |

`ScenePostExposure` 是编译时的表。若美术侧按 §10 改了某幕的 postExposure，重新生成后这里跟着变；**不要只在 profile 资产里改**（b 会偏一点，下次 Build 还会被覆盖）。

---

## 6. 测试卡、灰卡白卡、校准球、LUT 验证、bloom 探针（圣经 §1.5、§1.7、§9 第 3、4 条）

`Lanbai_TestCard`（**tag EditorOnly**：打包时整棵剥离；视觉部分在层 **`LanbaiDebug`**，没有就自动建；非 static、不投影、不进光照贴图）：

- **Patches/k−6 … k+4**：11 块 0.10 m 方片，间距 0.115 m，自发光 **0.18 × 2^k**（场景线性）。
- **ColourPatches/c1 … c8**（新）：8 块饱和色——站牌靛、伤口紫、尾灯红、钠灯橙、海蓝、暮玫瑰、湿叶绿、Lichtchen 暖白（场景线性，用 `SetVector` 写进 shader，不经任何颜色转换）。**不是圣经的法律值**：它检查你们的 PPv2 处理饱和色是否与我们的模型一致（Channel Mixer 靠的就是这个）。期望值见 `Docs~/TestCard_ColourRow.png`。
- **Backing**：0.0 黑底，垫在两行后面（+0.08 … −0.20 m）。色片行上方那条黑底就是**输入 0 的黑点**取样处（`Docs~/TestCard_Layout.png` 黄框）。
- **CalibCards**：灰卡 `#767676`（线性 0.18）、白卡 `#E6E6E6`（≈0.80），0.5 m，Standard，smoothness 0，**关掉 Specular Highlights 与 Reflections**（读数就是 Lambert：`calib_final.md` §A = 反照率 × E）。
  ① 世界主光的 culling 是 Bus + Tentacles + Player + PlayerLocal：量它时把 `CalibCards` 的层改成 Bus（工具重跑会保留你改的层；测量卡片那一趟会自动加上这一层）；② 烘焙灯只进 static 物体的光照贴图：量站灯 / 车厢灯管时把卡片临时设为 Contribute GI 一起烘。
- **CalibSpheres**：lookdev 的四个校准球（18% 灰、80% 白 smoothness 0.2；铬；sRGB 30 黑），Ø0.15 m。
- **DebugVolumes/PPV_DEBUG_Measure**（priority 1001）：bloom / 暗角 / 颗粒 intensity = 0 ——“测量模式”。
- **DebugVolumes/PPV_VERIFY_LDR**（priority 1000）：§1.7 的 **LDR 测试 profile**。比较 contribution 0 与 1 两张截图，必须完全相同。

### 6.1 自动测量怎么做的
隐藏相机（HDR、无 MSAA、黑底），挂一个新的 PostProcessLayer（用 PPv2 自带的 PostProcessResources 初始化）。每个 profile 单独 weight 1 + 测量模式，**拍两趟**：
1. **色片趟**：测试卡前 1.5 m、FOV 40，**只渲染 `LanbaiDebug` 层**——座椅背、柱子在别的层，永远挡不住色片。读 11 格 + 8 格 + 黑点；
2. **卡片趟**：两张卡中点前 0.7 m、FOV 60，culling = `LanbaiDebug` + 卡片所在层。

每趟渲染 3 帧后按 FP16 读回（显卡不支持时退回 8 位 sRGB），每块取中间 60% 逐像素编码成 sRGB 再平均（等于取色器平均；dithering 被平均掉）。测完所有 weight 与显隐恢复原样。
输出 `LanbaiReports/TestCard_Report.md`：灰阶 11 格 + 黑点（PASS = 全部 ±3）、**Unity vs 我们的 PPv2 模型**的诊断表、第二行饱和色表、灰卡白卡读数；`TestCard/<id>.png`（整帧）、`TestCard_AllProfiles.png`（每个 profile：上实测、下目标）。

### 6.2 怎么读报告
- **全部 PASS**：引擎与我们的模型一致，调色到位。
- **FAIL 且 “measured vs model” ≤ 2**：Unity 与模型一致，是解偏了 → 回传，我们重解。**不要手调。**
- **FAIL 且 “measured vs model” > 3**：我们的 PPv2 模型与你们的 Unity / PPv2 版本不一致 → 回传（含 `TestCard/<id>.png`），等不及就切 Route C（§6.4）。
- **S10 自检失败**：测量链路本身有问题（色彩空间、HDR、PPv2、shader）。

### 6.3 bloom 颜色探针
`Probe Bloom Colour`：藏起测试卡，放一个 0.04 m、自发光 40 的小方片，挂一个临时的、只有 bloom 的 volume（这时没有任何调色，输出是线性的），bloom 颜色分别设白与 `#808080` 各拍一张，读方片外一圈光晕的比值：**解码一次 = 0.216，两次 = 0.038**。据此设置 bloom 颜色补偿（按项目记在 EditorPrefs），变了就自动重建。报告与两张图写进 `LanbaiReports/`。

### 6.4 Route C（备用，圣经 §1.7.2）
只在测量证明 Route A（参数化 profile）在你们的 Unity 里偏离、而又等不及我们重解时用：
1. 把 `art/luts/hdr_external/*_HDRext33.cube`（15 个，仅这些）放进 `Assets/` 任意位置，等 PPv2 导入出同名 Texture3D；
2. `蓝白/Grades/Route C (External LUT fallback)/Build Route C Profiles and Switch to Route C`：建 `Profiles/RouteC/Lanbai_PPC_*.asset`（External 模式 + 该幕 LUT + postExposure 0 + 同样的 bloom），把 15 个场景 volume 指过去；
3. 在 `LanbaiExposure` 上勾 `routeC`；曝光型交叉淡化用 `RouteCCrossfadeWeight`；
4. `Measure Test Card` 照常测（LUT 就是外观本身，§C 应在 1 码以内）。
`Switch Back to Route A` 切回。Build 会保持当前所在的 Route。Route C 的限制见圣经 §1.7（External LUT 在 volume 之间是显示线性的溶解，不是 EV 线性）。

**`Debug Window`**（`蓝白/Grades/Debug Window`）：每个 volume 一根 weight 滑条；场景 profile 有 **Solo**；只有一个场景为 1 时显示它的 §C 目标色块、黑点（圣经 / 模型）与外观定义（悬停看）；测量模式、LDR LUT、显隐测试卡、测量、验证、bloom 探针、Route A / C 全在这里。Play 模式下 Director 会覆盖这里的 weight。

---

## 7. 可被远程调用的静态方法（全部返回一行结果字符串；无弹窗）

| 方法 | 菜单 |
|---|---|
| `Lanbai.Grading.LanbaiGradeBuilder.BuildAll()` | Build Profiles & Volumes |
| `LanbaiGradeBuilder.ValidateScene()` | Validate Scene & Camera |
| `LanbaiGradeBuilder.ConfigureReferenceCamera()` | Configure Reference Camera (PostProcessLayer) |
| `LanbaiGradeBuilder.RestoreInitialWeights()` / `Solo("S4")` | Restore Initial Weights / Debug Window |
| `LanbaiGradeBuilder.UseRouteC()` / `UseRouteA()` / `CurrentRouteIsC()` | Route C (External LUT fallback)/… |
| `LanbaiGradeBuilder.SetBloomColourCompensation(true/false)` | Bloom Colour/… |
| `LanbaiGradeBuilder.AddAnimatorFallback()` / `RemoveAnimatorFallback()` | Fallback/… |
| `Lanbai.Grading.LanbaiGradeTestCard.Build()` | Test Card |
| `LanbaiGradeTestCard.ToggleVisible()` | Test Card: Show or Hide |
| `LanbaiGradeTestCard.MeasureAll()` | Measure Test Card (all 15 profiles) |
| `LanbaiGradeTestCard.VerifyNeutralLut()` | Verify Neutral LUT (LDR, contribution 0 vs 1) |
| `LanbaiGradeTestCard.ProbeBloomColour()` | Probe Bloom Colour (single or double sRGB decode) |
| `LanbaiGradeTestCard.SetMeasurementMode(true/false)`、`SetLutVerify(0 / 1 / -1)` | Debug Window |
| `LanbaiGradeTestCard.FixAllLutImportSettings()` | Fix LUT Strip Import Settings |

报告都在 `<项目根>/LanbaiReports/`（在 `Assets/` 之外，不会被导入）。

---

## 8. Udon / UdonSharp 的限制（实话）

- **`PostProcessVolume.weight` 对 Udon 暴露（写）**：VRChat 官方 creator-docs 的 “Post-Processing Settings” 示例（复核者从 GitHub 原文核实）用 U# 设 volume 的 weight；多个公开 U# 项目也这样写。**读**与跨类静态调用请在你们 SDK 的 Class Exposure Tree 里确认（VRChat SDK → Udon Sharp → Class Exposure Tree，搜 `PostProcessVolume`），截图回传。
- 我们只用 `weight`（以及 `GameObject.activeInHierarchy`、`Transform.Find`）。**永远不要在运行时碰 `volume.profile`**（PPv2 会克隆一份），`priority`、`sharedProfile` 也不在运行时改。
- **静态方法：** UdonSharp 1.x 支持 static user methods。若你们的 U# 版本不认跨类静态调用，就调组件上的实例方法（同一套数学），或者把三行公式抄进 Director。
- **Udon 读不了静态 C# 数据**，所以 Director 需要的那几个数由生成器写成 `const` 和 `switch` 表放在 `LanbaiExposure.cs` 的生成段里。
- **退路（只有 Class Exposure Tree 里没有 `PostProcessVolume.weight` 时才用）：** `蓝白/Grades/Fallback/Add Animator Weight Drivers` + 脚本宏 **`LANBAI_PPV_ANIMATOR_FALLBACK`**（整份脚本不再引用 `PostProcessVolume`，我们单独编译过这个分支）。不需要退路时两样都别加。
- ClientSim 是单目的；VR 里 LENS 层是否确实关掉，要在头显里看一眼。

---

## 9. 未编译声明与我们做过的检查（不再循环论证）

**没有在 Unity 里跑过。** 我们这边做了：

1. **编译（C# 9，警告即错误，0 警告）**：`Editor/*.cs` 与 `Runtime/LanbaiExposure.cs` 对 Unity 2021.1 的引用程序集编译两遍——对 PPv2 公开 API 的桩（`Tools~/compile_check/run_check.sh`），以及**对从 GitHub 取下的真实 PPv2 3.0.2 运行时源码**（`Tools~/verify_indep/compile_real_ppv2.sh`）；U# 的正常分支与 Animator 退路分支、asmdef 布局与“全进一个程序集”的布局都编译过。证明不了 Udon 的 extern 白名单，也证明不了 2022.3 与 2021.1 之间的 Editor API 差异。
2. **真的执行过**：编译出的 `LanbaiGradeData` 与 `LanbaiExposure` 的静态数学在 .NET 下跑过，按 float32 逐值与 json 比对，v2.1 表 B3 的权重用例全部一致。
3. **`Tools~/verify_grade_data.py`（结果 `Docs~/verify_report.txt`）**：
   - A–C：C# 文本解析回来，与独立从 json 推出的期望逐项比对；编译执行结果逐项比对；U# 生成段逐项比对。
   - **D · 引擎门限**：C# 里的数过两个按 PPv2 源码独立写成的 Neutral 通路模型（LogC 对比、线性 709 的白平衡 / Channel Mixer / LGG / 饱和、33³ half LUT、三线性），两者逐格一致；§C 15 × 11 格 ≤ 3 码、黑点等于圣经要的值且夜间不压红、§A/§B/§D 全部 ≤ 3 码、C# 里的预测值等于模型。**美术模拟器不参与这一段**（它只在 D0 里核对“外观定义记录没被改动”，标明仅供参考）。故意把一个 profile 的 lift 改回 B1 的值，门限会同时报 §C、黑点压红、§B 三类错误（试过）。
   - E：圣经附录 B——B1 与外观定义记录逐值一致，B2 与助手一致，v2.1 表 B3 的 12 个权重复算一致。
   - F：sha256 链（C# 头 → 三个 json；引擎解与引擎填值 → 它们的来源）。
   - G：在临时目录里从 `Tools~/inputs/` 重新生成，C#、U# 生成段、README 表逐字节相同。
4. **复核者自己的工具**（`Tools~/verify_indep/`，已更新到修正版）：`ppv2_neutral_check.py` 对套件实际写入的数：0/15 个 profile 超差、§B 61 个不 bloom 的目标 0 个超差、Route C 1 码以内；加 `--grades Tools~/inputs/grades_final.json` 可重现原问题（14/15 超差）。`parity_indep.py`：PASS。
5. **交叉淡化与助手**：`Tools~/engine/xfade_check.py` 按 PPv2 的方式把两幕的引擎参数线性插值（lift / gamma / gain / Mixer 都插），与外观参数同样插值后比较两幕的预览帧：11 对淡化、每对 5 个 weight，加上表 B3 的 EXPO / WHITE_SAT 叠加，p99 最多 4 码（`Docs~/xfade_report.txt`）。
6. **图都看过**：`Docs~/` 里的每一张。
7. **shader 没有编译过**。`Lanbai_TestPatch.shader` 很小，只用 `UnityCG.cginc` 的标准宏；若报错，`Test Card` 会直接说找不到 shader。

最可能需要你们修的地方（按可能性）：Editor API 在 2022.3 上的细小差异；隐藏测量相机 + PostProcessLayer 在编辑模式下的初始化（`MeasureAll` 的 S10 自检行会立刻暴露）；U# 的静态跨类调用；bloom 探针在你们显卡上读不到光晕（报告会写 INCONCLUSIVE，默认设置不变）。

---

## 10. 改调色（给美术侧）

一条链，顺序不能乱：
1. 改 `art/bible_work/make_grades.py` → `grades_final.json`（外观定义；`calib_final.py` → `calib_final.json`）；
2. `python3 Tools~/engine/solve_engine_grades.py --frames <预览帧 npz> --neighbours 0.3 --jobs 3`（预览帧用 `art/bible_work/make_previews.SOURCES` 导出；每个 profile 10 秒到 6 分钟，`--jobs` 并行，结果与单进程相同）→ `Tools~/inputs/grades_engine.json`；
3. `python3 Tools~/engine/engine_calib.py` → `Tools~/inputs/calib_engine.json`（§B 改填值、测试卡第二行）；
4. `python3 Tools~/gen_grade_data.py` → `bash Tools~/compile_check/run_check.sh`（需要 `CSC_HOME`）→ `python3 Tools~/verify_grade_data.py`（必须 PASS）；
5. `python3 Tools~/engine/xfade_check.py --frames … > Docs~/xfade_report.txt`（p99 应 ≤ 4）、`python3 Tools~/verify_indep/ppv2_neutral_check.py --png Docs~/Verify_SC_vs_PPv2_Neutral_fixed.png`；
6. `python3 Tools~/make_reference.py`、`python3 Tools~/engine/compare_frames.py --frames …`，**看图**。

生成器会拒绝过期的输入：`grades_engine.json` 记着它是从哪一份 `grades_final.json` / `calib_final.json` 解出来的（sha256），对不上就停。
**Unity 里的 postExposure 修整（§1.5，±15% APL）请回传数值**，美术侧写进 `grades_final.json` 再走一遍这条链；直接改 profile 资产会在下一次 Build 被覆盖（Build 报告会列出来）。
Unity 里只需重跑 `Build Profiles & Volumes`（原地更新）与 `Measure Test Card`。

---

## 11. 已知问题 / 需要回传的东西

- **复核时的已知问题“MeasureAll 会在暗部失败”在这一版已经修掉**（引擎参数）。所以 MeasureAll 应当 PASS。万一你们那边仍在暗部 FAIL：**不要手调任何 profile**（14 个 profile 互相牵连，手调会把交叉淡化和 §B 填值全部打乱）；看报告的 “Unity vs the art side's model” 一节判断是解偏了还是模型偏了，把 `LanbaiReports/` 回传。等不及就用 Route C（§6.4，External LUT 就是外观本身烘成的表，不依赖我们对 PPv2 调色数学的建模）。
- **复核的处理**：B1（阻断）→ 引擎参数 + Channel Mixer，已修；M1（循环论证）→ 引擎门限，已修；m1 → 默认补偿 + 自动探针；m2 → Build 报告列出被覆盖的值 + §10 流程；m3 → 两趟测量；m4 → profile 资产不记 Undo（说明见 §2）；m5 → `CurrentBase()` 跳过不活动的 volume。
- **我们的 PPv2 模型是按源码写的，没在 GPU 上验证过。** 已知的近似：GPU 三线性插值的权重精度、half 精度的舍入，都在 1 码量级。`MeasureAll` 的 “Unity vs model” 一节就是为它准备的。
- **bloom 颜色**：补偿与否取决于 `MaterialPropertyBlock.SetColor` 在 Linear 工程里是否再转一次 sRGB。我们判断会（所以默认补偿），探针会在你们那边实测。
- **json 里的一处旧冲突已按 v2 解决**：`grades_final.json` 还留着 v1 的 `lens_desktop_only` 块（LENS_CLEAN priority 201、颗粒亮度贡献 0.9）；我们用 v2（199 / 0.8）。美术侧下次重跑 `make_grades.py` 时删掉那个块。
- **colorFilter**：PPv2 把它原样当线性乘数（不 `.linear`），美术模拟器按“hex → 线性”处理。现在全是白色，没有影响；以后若要非白的 colorFilter，两边先对齐。
- **`WHITE_BLOOM` 的 diffusion 9 高于 S9b 的 8**：迭代次数变化处 bloom 半径可能轻微跳一下，发生在白光膨胀里，被白吞掉，可接受。
- **请回传到 `FromLocal/`：** 整个 `LanbaiReports/`（`GradeBuild_Report.md`、`TestCard_Report.md`、`TestCard_AllProfiles.png`、`TestCard/*.png`、`NeutralLUT_Report.md` 与两张图、`BloomColour_Report.md` 与两张图），Class Exposure Tree 里 `PostProcessVolume` 那一行的截图，PPv2 的版本号，以及第一次编译时 Console 的任何报错原文。

---

## 12. 给圣经的修订提议（美术总监合并进下一版）

这一版套件与圣经 v2.1 的正文有四处不一致，都是法律第 1 条（目标不变、参数追目标）推出来的，需要写回圣经：

1. **§1.4 “夜间 lift 固定为 `(0.9875, 0.9905, 1, 0.008)`”** 与 **附录 B1 的色温 / 色调 / 饱和 / 对比 / lift / gamma / gain**：这些是**外观定义**（美术模拟器的数）。写进 Unity 的是 `grades_engine.json` 的引擎参数（本文 §3 第一张表）。建议 B1 加一列“引擎参数见 Grading 套件 README §3”，§1.4 那句改成“夜间黑点抬到 `#02060C` 蓝黑且不压红（引擎参数见套件）”。“禁止把 lift 色轮拖向蓝”的理由（红通道变负、数码青）仍成立：引擎参数的红通道 lift 是正的，黑点红 ≥ 1。
2. **§1.4 “每个场景 profile 覆盖同一整套参数”** 与 **附录 B 表头 “Channel Mixer 与 Curves 默认”**：引擎实现加了 **Channel Mixer**（9 个，离恒等 ≤ 5.3 个百分点），覆盖集从 22 变成 31。理由：线性 709 的 3×3 就是换原色，用它复现外观在 AP1 空间里对饱和色的处理（不加时 §B 的饱和填值差 9–30 码，加了改填后 ≤ 3 码）。管线结构（HDR、Neutral、volume 架构、助手）不变。
3. **`calib_final.md` §B**：本文 §3 末表那几项在引擎里要改填（目标不变）。
4. **bloom 颜色**：圣经里的 hex 仍是“设计的色调”；写进 Unity 的值由工具按 PPv2 的双重解码补偿（探针确认）。
