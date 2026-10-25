# 镜与白 · 独立评审 r1（美术 + 技术，只列阻断项）

评审对象：分支 `pkg/mirrors` 的工作区，2026-10-24 约 06:00 UTC（作者还在改，`Lanbai_BronzeMirror.shader`、`Lanbai_MirrorStars.shader`、`mirror_port.py` 在 05:58 又动过一次，下面的行号按那一版）。
看过：两份 README、`spec_conventions.md`、三个 shader + `LanbaiMirror.cginc`、两个驱动、搭建脚本、两份 JSON、numpy 移植（并用它重跑了 1116.0 / 1030.4 / 1123.5 三帧）、`r2_sheet.png`；对照圣经 §1.8、§6·9（9c）、9 → 10、第 10 幕、10 → 11，CONTROL §3 / §5 / §6，`README_LanbaiGlobals`，天空 `Lanbai_StarPoints` 的星点网格约定，`Overlay/README_Overlay.md`，`Director/README_Director.md`。

## 结论：**不通过**（5 条阻断）

已经核对过、没有问题的（不用再查）：shader / 移植 / 驱动三方的物体空间约定、镜面球心 `(0, s − ρ, 0)·D` 与半径 `ρ·D`、`y_edge = y_car − f(r_car)·D`、凸面星像的迭代与 0.5° 丢弃阈值、溶解 / 凝聚的符号距离、模板槽位（第 1–12 面 `(k−1) mod 6`、第 13 面槽 6，`64 + 槽`，同槽的镜子活动窗口不重叠）、尘槽 `k mod 3`（同槽不重叠）、MPB 属性名与 shader 属性名一一对应、`_Udon_MirrorPlane` / `_Udon_MirrorRimLight` 已登记、所有片元都有 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`、顶点里的 `_WorldSpaceCameraPos` 在 `UNITY_SETUP_INSTANCE_ID` 之后（按眼正确）、渲染队列（镜子 Geometry+20 写模板 → MirrorStars Transparent-90 读）、每面镜一个材质（模板值是渲染状态，不能走 MPB，搭建脚本做对了）、LODGroup（最后一级 0 = 不剔除）、星点 / 尘的包围盒（天空的星网格 200 km、尘网格 100 km）、白的曲线数值（冲击 / 膨胀 / 保持 / 遮罩、WHITE_SAT、WHITE_BLOOM、镜头层、F16 剪 2、29.15 s、10 → 11 的 +1 EV 与填值 × 2^−1、收缩 0 / 1.5 / 3 s × 5 s）与圣经一致、第 13 面 +3 EV 只在 1138.78 → 1146.31 EV 线性。UdonSharp：用到的 API（`MaterialPropertyBlock`、`Renderer.SetPropertyBlock`、`VRCShader.PropertyToID/SetGlobalVector`、`GameObject.SetActive`、`IsUserInVR`）都在白名单里；Tick 里的 `SetActive` 只在状态变化时调，且开关时刻镜子不可见（凝聚 0 / 溶解完），可以。

---

### 1. 镜子是实心厚板 + `Cull Back`：穿越那一帧整面镜子瞬间消失，溶解大部分看不见（第 12 面完全看不见）

- **在哪**：`Mirrors/Shaders/Lanbai_BronzeMirror.shader:77`（`Cull Back`）、`:178`（镜面分支）、`:295`（模板 pass）；移植 `Mirrors/Tools~/port/mirror_port.py:160`（镜面只在眼睛在上方时画）、`:169`（镜背只在眼睛在镜背平面以下时画）。
- **问题**：网格是闭合的厚板（镜面 y ≈ +0.015 D 到镜背主区 −0.015 D、缘 −0.037 D）。镜面在 t_cross 到达眼高之后，眼睛就在板的**里面**，直到镜背平面也越过眼睛为止。板里看出去，所有三角形都是背面 → 全被剔除：**整面镜子在穿越那一帧从下半球消失**（向下看是一帧之内从镜面跳到镜下的天），过一会儿暗的镜背天花板再一帧之内出现在头顶。按 `MirrorSchedule.json` 的运动节点算，眼睛在板里的时间：第 1–10 面 0.68 → 0.48 s（2 s 溶解的 25–35 % 看不见）、第 11 面 1.37 s（厚 8.2 m）、**第 12 面厚 14 m，镜背在活动结束（1140.08）前都没越过眼睛**：白的冲击那一面穿过以后直接没了，圣经 §6·9 的“2.0 秒从镜缘向内溶解”和镜背一次都看不到。移植用的是同一个约定，所以迭代图没暴露（r2 的 1116.0 正好在第 10 面板外 0.16 s）。
- **改**：把镜子当“一张有背面的面”画：镜面那一区 `Cull Off` + `VFACE`（或 `SV_IsFrontFace`），背面朝眼的镜面片元按镜背着色（铜绿、同一个溶解 / 前沿），模板 pass 只写正面（`clip(face)`）。其余区保持 `Cull Back`（板里向下看仍然透到下方的天，正确）。这样穿越时：下半球镜面 → 天（变暗，免费），上半球立刻是镜面背侧的铜绿天花板并开始溶解。移植里加一个对应的 `underside` 类（光线从下方打到镜面球冠 → 用镜背的颜色），重跑 t_cross + 0.1 / 0.5 / 1.0 s 的抬头与向下看，并把第 11、12 面穿越后 2 s 补进迭代图。

### 2. 白的驱动不驱动遮罩：F16 之后没有人画白（与 `Overlay/` v2 的接口不接）

- **在哪**：`Act10_White/Runtime/LanbaiWhiteDriver.cs:59–61`（`LanbaiActivate` 空）、`:63–74`（`LanbaiTick` 只读 VR）、`:112–144`（`OverlayAlpha / OverlayFillRow / OverlayBreath / ShrinkAlpha` 只算不调）；`Act10_White/README_Act10.md:49` 与 §2（“遮罩 v2 还没推”）。
- **问题**：`Overlay/`（`Lanbai_Overlay` v2，`LanbaiOverlay`）已经在仓库里，它的约定是“**每一幕的驱动在自己的时间窗里每帧调一个 `Set*`**，用完 `Hide()`”（`Overlay/README_Overlay.md` §2）。分发层（`Director/`）只汇总 `LanbaiGrade` 的 4 个数，**不调** `OverlayAlpha` 之类；`LB_Journey` 也不认识这个驱动。结果：3 s 遮罩、29.15 s 的白、10 → 11 的收缩都不会出现——而第 9 幕的根物体在 F16 已经关了，F16 之后看到的是没有白的空场景。
- **改**：驱动加 `public LanbaiOverlay overlay;`（Wire Scene 或手接），在 `LanbaiTick(t)` 里按 `Overlay/README_Overlay.md` §3 的表每帧调：1146.31–1149.31 `SetCurve(PickFill(S9b+WHITE_SAT 行), ΔEV, t − 1146.31, 3, Lscene, Lwhite, Lscene, Lwhite)`；1149.31–1178.46 `SetFlat(PickFill(S10 行), 1, 0)` + `SetBreath(0.02)`；1178.46–1186.46 `SetCurve(PickFill(S11 行), ΔEV, t − 1178.46, 5, Lwhite, Lscene11, Lscene11, Lwhite)` + 三个瓣（lead 0 / 1.5 / 3）；窗口外 / `LanbaiActivate(false)` 时 `Hide()`。填色用 `WhiteSchedule.json` `overlay.fills` 的线性值（写成驱动字段）；`appliedDeltaEV` 用这一帧本驱动 `LanbaiGrade` 的 ΔEV（这段时间只有它在动曝光——在 README 写明这个假设，或者请总控让分发层把汇总后的 `gradeDEV` 回传）。README §2 / §6 删掉“v2 还没推”。

### 3. `_Udon_MirrorPlane` / `_Udon_MirrorRimLight` 出窗后停在“第 13 面正在穿越”的值上

- **在哪**：`Mirrors/Runtime/LanbaiMirrorsDriver.cs:78–81`（`Start` 只建 ID）、`:115–119`（`LanbaiActivate` 只开关根物体）、`:133–134`、`:241–242`。
- **问题**：分发层的窗口是 `[t0, t1)`，出窗只调一次 `LanbaiActivate(false)`，不再 tick。最后一次 tick 在 F16 前一帧：第 13 面 dt ≈ −0.01 s → `_Udon_MirrorPlane` = (≈1.68 m, 镜线 ≈ 0.97, 13, ≈0)、`_Udon_MirrorRimLight.w` ≈ 0.3，**之后一直保持**——车厢在第 11 幕（假醒，同一个 `Lanbai/Cabin`）会在眼高画一条 2 cm 的亮线、侵蚀状态停在第 13 面，头像补光停在 E 0.3；往回拖时间到 1010 之前也一样。CONTROL §5 也要求驱动在 `Start()` 里写好全局量。
- **改**：加一个 `WriteIdleGlobals()`（`_Udon_MirrorPlane = (0,0,0,0)`、`_Udon_MirrorRimLight = (0,0,0,0)`），在 `Start()`、`LanbaiActivate(false)`、以及 `t < windowStart || t >= windowEnd` 时调。

### 4. 公告板朝各自的眼睛，违反 CONTROL §3“公告板朝两眼中点”

- **在哪**：`Mirrors/Shaders/Lanbai_MirrorDust.shader:128–131`（算了 `billboardEye = LanbaiCentreEyePos()` 却没用，四边形在每只眼的 `UNITY_MATRIX_V` 里展开）；`Mirrors/Shaders/Lanbai_MirrorStars.shader:130–131`（四边形的 R/U 由每只眼的 `toE` 建）。
- **问题**：两只眼看到的尘 / 反射星的四边形各转一个角度（`LanbaiVR.cginc` 明文禁止的那种）；尘就在车附近几米，偏差最大。
- **改**：尘：`float3 f = normalize(p − billboardEye); R = normalize(cross(up, f)); U = cross(f, R); Pq = p + (R·uv.x + U·uv.y)·2 rDraw; o.pos = UnityWorldToClipPos(Pq)`（`up` 在 f 接近竖直时换 (1,0,0)，同 StarPoints）。反射星：**位置 P 继续按每只眼解**（这是对的，立体视差靠它），只把四边形的基改成从 `LanbaiCentreEyePos()` 指向 P 的方向建。

### 5. 镜子读不出 `#CDBF9C`：调色后白铜的暖色只剩约一半（圣经 §6·9“镜面整体读作白铜色调的银河 `#CDBF9C`”）

- **在哪**：`Lanbai_BronzeMirror.shader:47–48`、`:192`（色调 lerp）；`Lanbai_MirrorStars.shader:32–33`、`:127`；`mirror_port.py:30–31`；README `Mirrors/README_Mirrors.md:33`、`:61`（“r2 第一次读成托着金色银河的镜子”）。
- **问题**：用当前移植（`BRONZE_TONE` 已经是 0.85，r3 的“色度只取色调、亮度保持”写法，06:00 前后的版本）重跑，镜面最亮 3 % 像素（= 反射的银河）调色后的码值：1030.4 向下看 −60° **(76, 74, 68)**、1030.4 正前方偏下 (163, 158, 144)、1123.5 (224, 218, 205)；B/R = 0.89 / 0.88 / 0.92，目标 `#CDBF9C` 是 **0.76**。线性里的色调已经是 `#CDBF9C` 的 85 %，调色后只剩这些：S9a / S9b 的 temperature −6 / −4、tint +3 / +4、夜间 lift 与对比把暖色吃掉了大半；向下看（镜子接近时最常见的视向）反射的银河是灰的，镜面中位数还偏蓝 (17, 20, 24)。色调是在调色**之前**按线性拉的，没有对调色做补偿——再提 `_BronzeTone` 也到不了目标。
- **改**：在移植里对“调色后的色相”求解 `_ToneColor`（把调色的冷偏与 lift 预先抵掉，例如对 S9a、S9b 两个 profile 在镜面实际的亮度段上反解出线性色调），`_BronzeTone` 取 1 或保留 0.85 但用补偿后的颜色；验收标准写进 README：向下看与正前方两个视向、1030 / 1092 / 1123 三个时刻，反射银河最亮 3 % 的 B/R ≤ 0.80、G/R 0.90–0.95。MirrorStars 用同一个颜色。改完重出 r3 图（r2_sheet 里的 1116.0 宽亮带当前代码已经不出了，图是旧的，一并重出）。

---

附注（不阻断，顺手改）：`README_Mirrors.md` §1 / §4 和 `README_Act10.md` §2 / §4 引用的 `Docs~/flashcheck/`（`wf.json`、`wd.json`）和 `WhiteSchedule.json` 里的 `Act10_White/Docs~/white_check.txt` 都不存在，`lSceneMask = 0.30` 目前没有证据，请在交本地前补上或删掉这些说法；`LanbaiWhiteDriver.cs:10` 提到的菜单 `蓝白/Build/Act10 White` 不存在；`spec_conventions.md` §6 把 `_StencilRef` 列成 MPB 参数（它是渲染状态，只能在材质上，搭建脚本是对的，文档改一下）。

---

## 作者的回应（镜与白，提交 0358a87 起）

| # | 处理 |
|---|---|
| 1 穿越时镜子被剔掉 | **先照建议改了（`Cull Off` + `VFACE`，板的里面按镜背着色），又改回 `Cull Back`，理由写在 shader 里：** 第 10 面的板在车那里厚 6 m，10 m/s 穿过要 0.6 s，里面画暗色 = 每次穿越一次 0.6 s 的暗凹 = 一对闪烁（flash 序列 m10：每秒 2.5 次，> 2）。所以板的里面不画：镜面平面扫过眼睛时，向下看直接从这一面的镜面换到下一面的镜面（这就是圣经“镜面到达你眼睛时”的那一下），眼睛低于镜背以后头顶才出现镜背。这样“消失”不是 bug，是一个薄平面扫过你；镜背改成固定的剪影亮度 `_BackFill`（S9a/S9b 下 `#16302A`，圣经上限 `#1E3B34`，和星空自己的亮度接近），所以它出现、溶解都几乎不改亮度。numpy 移植同样处理（眼睛在镜面球里 = 看穿）。 |
| 2 F16 以后没人画白 | **改了。** `LanbaiWhiteDriver` 在自己的窗口里拥有 `Lanbai_Overlay` v2：3 s 遮罩 `SetCurve`、29.15 s 白 `SetFlat` + 呼吸 0.02、10 → 11 `SetCurve` + 三个瓣（0 / 1.5 / 3 s，其余 3 s）、窗口外 `Hide()`；填色取 `WhiteSchedule.json` 的线性值，`PickFill` 选 VR 列。 |
| 3 全局量卡住 | **改了。** `Start()`、`LanbaiActivate(false)`、窗口外都写 0；窗口结束挪到 F16 + 1 s（白遮罩下），F16 之后的那几帧把第 13 面关掉、全局量归零。 |
| 4 公告板朝每只眼 | **改了。** 尘与反射的星都朝两眼中点（`LanbaiCentreEyePos()`）；星的像点仍逐眼解。 |
| 5 镜面调色后不是 `#CDBF9C` | **改了。** `_ToneColor` 按引擎调色反解：(1.262, 0.974, 0.484)，`_BronzeTone` = 1（镜面颜色只取亮度 × 这个色调：r3 里蓝 + 暖的混合在第 13 面上变成了薰衣草，D-21 的紫带 8.9 %）。S9a / S9b 下正好显示 `#CDBF9C`。 |
| 非阻断 | `flashcheck/` 的结果随这一轮推；`蓝白/Build/Act10 White` 的说法删了（白的驱动字段默认值就是 JSON 的数）；spec §6 改正 `_StencilRef` 只在材质上；`r2_sheet.png` 由 r4 取代。 |
