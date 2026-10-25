# 第 10 幕 · 白（第 12 面 → F16 → 29.15 秒的白 → 白收缩进灯里）· README

写的人：会话「镜与白」（分支 `pkg/mirrors`）。**C# 没有在 Unity / UdonSharp 里编译过**（检查见 §5）。

## 0. 先做这几步

1. **拷**：`Act10_White/` → `Assets/Lanbai/Act10_White/`（`Tools~` 不导入）。
2. **搭**：先跑 `蓝白/Build/Overlay`，再跑 **`蓝白/Build/Act10 White`**（`Editor/LanbaiWhiteBuild.cs`，终审 r3 #3）：建 `LanbaiWhiteDriver` 的 U# 程序资产（走 `LanbaiMirrorsBuild.EnsureProgramAsset` 这一个调用点，D-41 总工程师的共用工具会换掉它的内容）、建常开的 `Lanbai_WhiteDriver`、挂组件、连 `Lanbai_Overlay`；场景里没有遮罩球就报错、什么都不建。可重复运行。字段的默认值 = `WhiteSchedule.json` 的数，不用改。
3. **接 Director**：分发层在窗口 {1136.58, 1188.96} 里调 `LanbaiTick(t)` 与 `LanbaiGrade(t)`；`LB_Journey.ApplyGrades` 读汇总值写 EXPO_UP / WHITE_SAT / WHITE_BLOOM / 桌面镜头层；遮罩由本驱动自己画（§2）。**`LB_Journey` 里现在的白（冲击 / 膨胀）那一段要删掉**，换成这里的（`Engineering/README_集成.md` §5）。
4. **截图推回**（`FromLocal/white_test/`）：1137.58 → 1150 与 1178 → 1190 两段 60 fps PNG 序列，正前方与向下看各一次（§1.8 录像窗口 (g)(h)），跑 `flashcheck.py`；再截 1160 一帧（桌面、VR 各一）量白的码值（桌面 `#E8F1F5`、VR `#D7E3E8`，±2 码，§1.8）。

## 1. 时间（全部由标签算，`WhiteSchedule.json`）

| t | 段 | ΔEV（EXPO_UP，b = +0.30） | WHITE_SAT | WHITE_BLOOM | 桌面镜头层 | 遮罩 |
|---|---|---|---|---|---|---|
| 1137.58 → 1138.78 | 冲击（第 12 面穿越，尾声最响的一下） | 0 → +1.0（w 0 → 0.270） | 0 → 0.42 | 0 → 0.5 | 1 | — |
| 1138.78 → 1144.78 | 膨胀（到吸气开始） | → +2.4（w → 0.649） | → 1 | → 1 | 1 → 0 | — |
| 1144.78 → 1146.31 | 保持（只有第 13 面在动）；1144.81 起遮罩（上半球先，正前方 +0.46 s，C1 = B） | +2.4 | 1 | 1 | 0 | `EvOverlayAlpha`，4.5 s，Lscene 0.06，正前方瓣 |
| 1146.31 → 1149.31 | 遮罩继续（正前方 1146.32 才看得出） | +2.4 | 1 | 1 → 0（随遮罩 EV 线性） | 0 | 同上，填值 S9b+WHITE_SAT 行 × 2^−ΔEV；F16 时正前方差 0.17 EV，剪 2 补齐 |
| **1149.31 = F16** | **剪 2**：同一帧 S9a/S9b → 0、S10 → 1、EXPO_UP → 0、WHITE_SAT → 0，填值换 S10 行 | 0 | 0 | 0 | 0 | 1 |
| 1149.31 → 1178.46 | 白 29.15 s（峰值保持 ≤ 30 s，余量 0.85 s），±2 %、0.1 Hz 呼吸 | 0 | 0 | 0 | 0 | 1，S10 行 |
| **1178.46** | 10 → 11：同一帧硬切 S11，EXPO_UP +1.0（w 0.241）与填值 × 2^−1 同帧（屏幕一码不动）；镜头层回到 1（假醒是档案） | +1.0 → 0（4 s，变暗） | 0 | 0 | 1 | S11 行 |
| 1178.46 → 1186.46 | 白收缩进灯里：管灯先、路灯 +1.5 s、头顶的海 +3 s，每个方向 5 s EV 线性 | | | | | `ShrinkAlpha(t, lead)` |

第 13 面的镜面自发光 +2.7 EV（终审 r3 C3：原 +3，加上 WHITE_BLOOM 向下看 225 > 220）（1138.78 → 1146.31，冲击里不升）由镜子驱动写（`Mirrors/`）。

## 2. 遮罩（`Lanbai_Overlay` v2，会话「门内」）

- **驱动在自己的窗口里拥有遮罩**（`Overlay/README_Overlay.md` §2–§3 的约定：每幕的驱动每帧调 `Set*`，用完 `Hide()`；评审 r1 #2）：字段 `overlay` 接场景里的 `Lanbai_Overlay`（Wire Scene 或手接）。1146.31 → F16 `SetCurve`（S9b+WHITE_SAT 行，`PickFill` 选桌面 / VR）、F16 → 1178.46 `SetFlat`（S10 行）+ `SetBreath(0.02)`、1178.46 → 1186.46 `SetCurve`（S11 行）+ 三个瓣（管灯 0 s、路灯 1.5 s、头顶的海 3 s，其余 3 s；方向字段 `lobeDir` 等第 11 幕给）；**只收回自己画的**：遮罩只在本驱动自己 `Set*` 过之后、离开这三段（或 `LanbaiActivate(false)`）时 `ClearLobes()` + `Hide()` 一次，别的时候什么都不写（评审 r2 #1：出生的 3 s 黑、分发层的预热都不会被它清掉）。填色是 `WhiteSchedule.json` `overlay.fills` 的线性值（= `calib_final.md` §D），2^−ΔEV 由遮罩组件按传进去的 ΔEV 乘（这个窗口里白是唯一的曝光事件，所以就是本驱动的 ΔEV）。
- 另外保留只读的 `OverlayAlpha(t)`、`OverlayFillRow(t)`、`OverlayBreath(t)`、`ShrinkAlpha(t, lead)` 给测试用。
- 遮罩在 PPv2 之前画：`rgb = 填值 × 呼吸 × 2^(−ΔEV)`，ΔEV = 这一帧 EXPO_UP 实际加上的曝光（写曝光的一方算）。
- **遮罩（C1 = B，总导演 10-25）**：`tMaskStart` 1144.81、`maskSeconds` 4.5、`lSceneMask` 0.06（实测最暗的视向：侧上方 +30°，L 0.058–0.060），一个正前方瓣（`maskLobeDir` (0, 0.1, 1)、半角 25°、软边 30°、领先 0.46 s）：上半球从吸气开始变白，正前方 1146.32 才看得出；F16 剪 2 时正前方差 0.17 EV，一步补齐。四个白序列（正前、向下、抬头、侧上）PASS，侧上 1 s 正好 1.00 EV。
- 方向瓣的方向（管灯、路灯、海）属于第 11 幕的布局（「灯与假醒」），v2 推出来以后在 Wire Scene 里填；没有瓣时退路 = 全方向同一条曲线（变暗免费）。

- **呼吸按 t 算**（F5）：Overlay v2 的 shader 用 `_Time` 算呼吸的相位，倒放 / 迟到的人相位不对；所以本驱动 `SetBreath(0)`，自己把 `1 + 0.02 sin(2π·0.1·(t − F16))` 乘进填色。从收缩倒回白或遮罩时清掉方向瓣（F5）。
- **迟到的人**（终审 r3 #4、D-43）：
  - 分发层（Director v1.2）每帧在 `LanbaiTick` 之前调 `LanbaiSpawnFade(since)`：since = 离分发层锁存的“黑场结束时刻”过了几秒，黑场里为 −1；那时本驱动不写遮罩。
  - **`LanbaiOverlayWindow()` = {1144.81, 1188.96}**（遮罩开始 → 整个窗口结束；窗口为此延到收缩结束后 2.5 s）：在这个时段里任何时刻结束黑场的人，都由本驱动从黑升起，**只亮一次**，≤ 0.8 EV/s（D-43 限 0.85，留余量）：
    - 黑场在 1146.31 → 1168.8 之间结束：遮罩不透明，填色从黑（0.004）按 EV 线性升到白（桌面 9.7 s、VR 9.5 s）；升完已经过了 F16，接上正常的白（同为不透明白，没有缝）。
    - 黑场结束得更晚（升到白会撞上 1178.46 的收缩）或者在收缩里：保持全黑到收缩结束（1186.46），再用黑纱按 EV 线性放出第 11 幕（约 2 s）。不会先白再暗。
  - 核对（D-43 #5 的 1140 / 1150 / 1180 及边界 1146.31、1160、1169、1169.5、1175、1178.46、1186，桌面与 VR，三种视向）：全部 PASS，最坏 0.31 / 0.91 / 1.70 EV（0.25 / 1 / 2 s）。`Tools~/join_check.py` → `Mirrors/Docs~/flashcheck/join_white.json`。1140 进来的人由分发层按 D-43 #4 保持黑、1146.31 交给本驱动。

**从 t 重建（D-33 #6）**：`LanbaiGrade(t)`、遮罩的每一种状态都只由 t 决定；唯一缓存的是“方向瓣已经设过”，`LanbaiActivate` 时清掉，下一帧按 t 重设。

## 3. VR 与桌面

- 峰值：桌面 `#E8F1F5`（luma 239）、VR `#D7E3E8`（luma ≈ 224），由 `IsUserInVR()` 选填值列。VR 里没有镜头层（`LanbaiExposure` 在 VR 关掉 `Lens_DesktopOnly`）。
- 白里没有 logo、字、形状、暗角；遮罩后面的一切在 F16 关掉（镜子的窗口在 F16 + 1 s 结束、F16 起第 13 面关掉；R_Road 干燥版与 R_False 由第 11 幕 / Director 在白里激活）。

## 4. 爬升律

圣经的仿真（`ramp_checks_v21.json` `9_to_10_white`）：正前方 / 向下看 0.19 / 0.73 / 1.21 EV，PASS。我们的序列（numpy 移植 + 第 9 幕的天 + 镜子 + 遮罩，`Mirrors/Docs~/flashcheck/`）见那边的 json。

## 5. 检查

`bash Common/Tools~/compile_check/check_cs.sh Mirrors Act10_White Overlay` → C# CHECK OK（含 `Editor/LanbaiWhiteBuild.cs`）。

## 6. 诚实的已知弱点

- 没在 Unity / 头显里验证；遮罩 v2 的方向瓣的方向要等第 11 幕的布局。
- 序列检查里 WHITE_SAT / WHITE_BLOOM 按权重混进 PPv2 的参数（numpy 引擎模型）；遮罩按显示线性近似合成。
- 遮罩按 C1 = B 改了以后，最暗的侧上方 1 s 爬 1.00 EV，正好在限上（numpy 移植）；在 Unity 里实测时先量这一条。
- 10 → 11 的收缩（C7）：第 11 幕的场景不在本包，用均匀的 L 0.012（APL 30）+ 4 s 衰减的 +1 EV 合成，六个视向桌面 / VR 全 PASS（只有变暗，闪烁 0.5 次 / s），`Mirrors/Tools~/port/shrink_check.py` → `Mirrors/Docs~/flashcheck/shrink_*.json`；第 11 幕到了要用真场景重跑。
- `LENS_CLEAN` 回到 1 的时刻圣经没写，取 10 → 11 的遮罩下（1178.46）。
