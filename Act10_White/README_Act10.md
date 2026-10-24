# 第 10 幕 · 白（第 12 面 → F16 → 29.15 秒的白 → 白收缩进灯里）· README

写的人：会话「镜与白」（分支 `pkg/mirrors`）。**C# 没有在 Unity / UdonSharp 里编译过**（检查见 §5）。

## 0. 先做这几步

1. **拷**：`Act10_White/` → `Assets/Lanbai/Act10_White/`（`Tools~` 不导入）。
2. **挂**：一个常开的空物体 `Lanbai_WhiteDriver`，加 `LanbaiWhiteDriver`（U# 程序资产照 CONTROL §6 第 11 条建；`蓝白/Build/Mirrors` 会顺手建 `LanbaiMirrorsDriver` 的，这一个请在 Director 的 Wire Scene 里一起接，或手建）。字段的默认值 = `WhiteSchedule.json`，不用改。
3. **接 Director**：分发层在窗口 {1136.58, 1187.46} 里调 `LanbaiTick(t)` 与 `LanbaiGrade(t)`；`LB_Journey.ApplyGrades` 读汇总值写 EXPO_UP / WHITE_SAT / WHITE_BLOOM / 桌面镜头层，并画遮罩（§2）。**`LB_Journey` 里现在的白（冲击 / 膨胀）那一段要删掉**，换成这里的（`Engineering/README_集成.md` §5）。
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

第 13 面的镜面自发光 +3 EV（1138.78 → 1146.31，冲击里不升）由镜子驱动写（`Mirrors/`）。

## 2. 遮罩（`Lanbai_Overlay` v2，会话「门内」）

- 驱动只给数，不碰材质：`OverlayAlpha(t)`、`OverlayFillRow(t)`（0 = S9b+WHITE_SAT、1 = S10、2 = S11；`calib_final.md` §D 的行，`WhiteSchedule.json` `overlay.fills` 里有线性值）、`OverlayBreath(t)`（乘在填色上）、`ShrinkAlpha(t, lead)`（v2 的方向瓣：领先 0 / 1.5 / 3 s）。`IsUserInVR()` 选 VR 列。
- 遮罩在 PPv2 之前画：`rgb = 填值 × 呼吸 × 2^(−ΔEV)`，ΔEV = 这一帧 EXPO_UP 实际加上的曝光（写曝光的一方算）。
- `EvOverlayAlpha` 的标量 `Lscene`（3 秒遮罩那一段）= `lSceneMask` 0.30：变白的遮罩按**最暗的视向**建（§1.8 E17），数值由 `Mirrors/Tools~/port/flash_seq.py` 的白序列选（`Mirrors/Docs~/flashcheck/wf.json`、`wd.json`）。
- 方向瓣的方向（管灯、路灯、海）属于第 11 幕的布局（「灯与假醒」），v2 推出来以后在 Wire Scene 里填；没有瓣时退路 = 全方向同一条曲线（变暗免费）。

## 3. VR 与桌面

- 峰值：桌面 `#E8F1F5`（luma 239）、VR `#D7E3E8`（luma ≈ 224），由 `IsUserInVR()` 选填值列。VR 里没有镜头层（`LanbaiExposure` 在 VR 关掉 `Lens_DesktopOnly`）。
- 白里没有 logo、字、形状、暗角；遮罩后面的一切在 F16 关掉（镜子的窗口在 F16 结束；R_Road 干燥版与 R_False 由第 11 幕 / Director 在白里激活）。

## 4. 爬升律

圣经的仿真（`ramp_checks_v21.json` `9_to_10_white`）：正前方 / 向下看 0.19 / 0.73 / 1.21 EV，PASS。我们的序列（numpy 移植 + 第 9 幕的天 + 镜子 + 遮罩，`Mirrors/Docs~/flashcheck/`）见那边的 json。

## 5. 检查

`bash Common/Tools~/compile_check/check_cs.sh Mirrors Act10_White` → C# CHECK OK。

## 6. 诚实的已知弱点

- 没在 Unity / 头显里验证；遮罩 v2 还没推，填色补偿与方向瓣按圣经的接口写。
- 序列检查里 WHITE_SAT / WHITE_BLOOM 没有模拟，遮罩按显示线性近似合成。
- `LENS_CLEAN` 回到 1 的时刻圣经没写，取 10 → 11 的遮罩下（1178.46）。
