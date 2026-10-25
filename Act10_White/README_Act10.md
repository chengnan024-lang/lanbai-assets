# 第 10 幕 · 白（第 12 面 → F16 → 29.15 秒的白 → 白收缩进灯里）· README

写的人：会话「镜与白」（分支 `pkg/mirrors`）。**C# 没有在 Unity / UdonSharp 里编译过**（检查见 §5）。

## 0. 先做这几步

1. **拷**：`Act10_White/` → `Assets/Lanbai/Act10_White/`（`Tools~` 不导入）。
2. **搭**：先跑 `蓝白/Build/Overlay`，再跑 **`蓝白/Build/Act10 White`**（`Editor/LanbaiWhiteBuild.cs`，终审 r3 #3）：建 `LanbaiWhiteDriver` 的 U# 程序资产（走 `LanbaiMirrorsBuild.EnsureProgramAsset` 这一个调用点，D-41 总工程师的共用工具会换掉它的内容）、建常开的 `Lanbai_WhiteDriver`、挂组件、连 `Lanbai_Overlay`；场景里没有遮罩球就报错、什么都不建。可重复运行。字段的默认值 = `WhiteSchedule.json` 的数，不用改。
3. **接 Director**：分发层在窗口 {1136.58, 1187.46} 里调 `LanbaiTick(t)` 与 `LanbaiGrade(t)`；`LB_Journey.ApplyGrades` 读汇总值写 EXPO_UP / WHITE_SAT / WHITE_BLOOM / 桌面镜头层；遮罩由本驱动自己画（§2）。**`LB_Journey` 里现在的白（冲击 / 膨胀）那一段要删掉**，换成这里的（`Engineering/README_集成.md` §5）。
4. **截图推回**（`FromLocal/white_test/`）：1137.58 → 1150 与 1178 → 1190 两段 60 fps PNG 序列，正前方与向下看各一次（§1.8 录像窗口 (g)(h)），跑 `flashcheck.py`；再截 1160 一帧（桌面、VR 各一）量白的码值（桌面 `#E8F1F5`、VR `#D7E3E8`，±2 码，§1.8）。

## 1. 时间（全部由标签算，`WhiteSchedule.json`）

| t | 段 | ΔEV（EXPO_UP，b = +0.30） | WHITE_SAT | WHITE_BLOOM | 桌面镜头层 | 遮罩 |
|---|---|---|---|---|---|---|
| 1137.58 → 1138.78 | 冲击（第 12 面穿越，尾声最响的一下） | 0 → +1.0（w 0 → 0.270） | 0 → 0.42 | 0 → 0.5 | 1 | — |
| 1138.78 → 1144.78 | 膨胀（到吸气开始） | → +2.4（w → 0.649） | → 1 | → 1 | 1 → 0 | — |
| 1144.78 → 1146.31 | 保持（只有第 13 面在动） | +2.4 | 1 | 1 | 0 | — |
| 1146.31 → 1149.31 | 遮罩 3 s | +2.4 | 1 | 1 → 0（随遮罩 EV 线性） | 0 | `EvOverlayAlpha` 0 → 1，填值 S9b+WHITE_SAT 行 × 2^−ΔEV |
| **1149.31 = F16** | **剪 2**：同一帧 S9a/S9b → 0、S10 → 1、EXPO_UP → 0、WHITE_SAT → 0，填值换 S10 行 | 0 | 0 | 0 | 0 | 1 |
| 1149.31 → 1178.46 | 白 29.15 s（峰值保持 ≤ 30 s，余量 0.85 s），±2 %、0.1 Hz 呼吸 | 0 | 0 | 0 | 0 | 1，S10 行 |
| **1178.46** | 10 → 11：同一帧硬切 S11，EXPO_UP +1.0（w 0.241）与填值 × 2^−1 同帧（屏幕一码不动）；镜头层回到 1（假醒是档案） | +1.0 → 0（4 s，变暗） | 0 | 0 | 1 | S11 行 |
| 1178.46 → 1186.46 | 白收缩进灯里：管灯先、路灯 +1.5 s、头顶的海 +3 s，每个方向 5 s EV 线性 | | | | | `ShrinkAlpha(t, lead)` |

第 13 面的镜面自发光 +2.7 EV（终审 r3 C3：原 +3，加上 WHITE_BLOOM 向下看 225 > 220）（1138.78 → 1146.31，冲击里不升）由镜子驱动写（`Mirrors/`）。

## 2. 遮罩（`Lanbai_Overlay` v2，会话「门内」）

- **驱动在自己的窗口里拥有遮罩**（`Overlay/README_Overlay.md` §2–§3 的约定：每幕的驱动每帧调 `Set*`，用完 `Hide()`；评审 r1 #2）：字段 `overlay` 接场景里的 `Lanbai_Overlay`（Wire Scene 或手接）。1146.31 → F16 `SetCurve`（S9b+WHITE_SAT 行，`PickFill` 选桌面 / VR）、F16 → 1178.46 `SetFlat`（S10 行）+ `SetBreath(0.02)`、1178.46 → 1186.46 `SetCurve`（S11 行）+ 三个瓣（管灯 0 s、路灯 1.5 s、头顶的海 3 s，其余 3 s；方向字段 `lobeDir` 等第 11 幕给）；**只收回自己画的**：遮罩只在本驱动自己 `Set*` 过之后、离开这三段（或 `LanbaiActivate(false)`）时 `ClearLobes()` + `Hide()` 一次，别的时候什么都不写（评审 r2 #1：出生的 3 s 黑、分发层的预热都不会被它清掉）。填色是 `WhiteSchedule.json` `overlay.fills` 的线性值（= `calib_final.md` §D），2^−ΔEV 由遮罩组件按传进去的 ΔEV 乘（这个窗口里白是唯一的曝光事件，所以就是本驱动的 ΔEV）。
- 另外保留只读的 `OverlayAlpha(t)`、`OverlayFillRow(t)`、`OverlayBreath(t)`、`ShrinkAlpha(t, lead)` 给测试用。
- 遮罩在 PPv2 之前画：`rgb = 填值 × 呼吸 × 2^(−ΔEV)`，ΔEV = 这一帧 EXPO_UP 实际加上的曝光（写曝光的一方算）。
- `EvOverlayAlpha` 的标量 `Lscene`（3 秒遮罩那一段）= `lSceneMask` 0.13：变白的遮罩按**最暗的视向**建（§1.8 E17；抬头看 APL ≈ 100 时 L ≈ 0.13，评审 r2），数值由 `Mirrors/Tools~/port/flash_seq.py` 的白序列选（`Mirrors/Docs~/flashcheck/wf.json`、`wd.json`）。
- 方向瓣的方向（管灯、路灯、海）属于第 11 幕的布局（「灯与假醒」），v2 推出来以后在 Wire Scene 里填；没有瓣时退路 = 全方向同一条曲线（变暗免费）。

- **呼吸按 t 算**（F5）：Overlay v2 的 shader 用 `_Time` 算呼吸的相位，倒放 / 迟到的人相位不对；所以本驱动 `SetBreath(0)`，自己把 `1 + 0.02 sin(2π·0.1·(t − F16))` 乘进填色。从收缩倒回白或遮罩时清掉方向瓣（F5）。
- **迟到的人**（终审 r3 #4，裁决：出生淡入优先）：本地玩家的出生淡入结束之前，本驱动不写遮罩（分发层调 `LanbaiSpawnFadeEnd(t)` 告诉它结束的时刻；总工程师加这一行之前，驱动用 `t − Time.timeSinceLevelLoad + 3 s` 代替）。在遮罩或白里（1146.31 → 1178.46）进来的人：从黑（L 0.004）按 ≤ 0.85 EV/s 的 EV 线性曲线升到白（桌面 log2(0.86/0.004)/0.85 = 9.1 s，VR 8.9 s），之后接正常的状态；在收缩里（≥ 1178.46）进来的人：本驱动不写（出生淡入已经淡到第 11 幕）。**请分发层在白的窗口里把出生淡入停在黑**（不淡到场景），再交给本驱动。

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
- **3 秒遮罩对暗的朝上视向不合爬升律**（终审 r3 C1，已实测，等总导演裁）：1146.31 时最暗的视向是侧上方 +30°（yaw 90°），L = 0.058（384 px）/ 0.060（1920×1080），不是 `lSceneMask` 0.13；照现在的曲线，那个视向 1 s 爬 1.62 EV、2 s 爬 2.80 EV（≤ 1.0 / 1.8），正上方 1.09 / 2.08 也不过。方案见 `Mirrors/给总控.md` 10-25 条；没裁之前驱动不改。
- 10 → 11 的收缩（C7）：第 11 幕的场景不在本包，用均匀的 L 0.012（APL 30）+ 4 s 衰减的 +1 EV 合成，六个视向桌面 / VR 全 PASS（只有变暗，闪烁 0.5 次 / s），`Mirrors/Tools~/port/shrink_check.py` → `Mirrors/Docs~/flashcheck/shrink_*.json`；第 11 幕到了要用真场景重跑。
- `LENS_CLEAN` 回到 1 的时刻圣经没写，取 10 → 11 的遮罩下（1178.46）。
