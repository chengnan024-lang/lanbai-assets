# 镜与白 · 独立评审 r2（美术 + 技术，只列阻断项）

评审对象：分支 `pkg/mirrors` 工作区，2026-10-24 约 12:40 UTC（HEAD c8946e8，作者还在推 r5 图）。
看过：两份 README、`spec_conventions.md`、三个 shader + `LanbaiMirror.cginc`、`LanbaiMirrorsDriver.cs`、`LanbaiMirrorsBuild.cs`、`LanbaiMirrorsData.cs`、`LanbaiWhiteDriver.cs`、`Overlay/README_Overlay.md` §1–§3 与 `LanbaiOverlay.cs`、`Director/README_Director.md` 与生成的分发层模板、`mirror_port.py`、`make_schedule.py`、`bake_cs.py`、两份 JSON、`r4_sheet.png`、`m13_H_sheet.png`；对照圣经 §1.8、§6·9（9c）、9 → 10、第 10 幕、10 → 11，CONTROL §3 / §5 / §6，裁决 D-29、D-33 #6、D-38（在 origin/main）。

## 结论：**不通过**（1 条新的阻断；r1 的 5 条都已落实）

## r1 各条是否落实

| # | 结论 | 核对 |
|---|---|---|
| 1 穿越时镜子被剔掉 | **成立（作者的替代做法，不是 r1 的建议）** | shader 保持 `Cull Back`（`Lanbai_BronzeMirror.shader:79–83` 写了理由）；移植同一约定：眼睛在镜面球里 → 镜面全看穿（`mirror_port.py:170–172`），镜缘带顶面从上方仍画（`:180`），镜背只在眼睛低于镜背平面时画（`:184`）——与 shader 的背面剔除逐项一致（眼睛在球内时球冠上每一点都是背面，数学上成立）。m1 / m10 / m11 和白的序列都用这个约定跑过且 PASS。后果要知道：第 12 面（板在车处厚 ≈ 14 m、穿越后 5 m/s、活动到 1140.08）在冲击那一帧镜面整片消失，它的 2 s 溶解只在 ≥ 97 m 外的镜缘带那一圈和星尘上看得见，镜背一次都看不到。这是对圣经 §6·9“2.0 秒内从镜缘向内溶解”的一种读法，**请在 `给总控.md` 里登记一句**（不阻断）。 |
| 2 F16 以后没人画白 | **成立**（但见新阻断 1） | `LanbaiWhiteDriver.cs:125–162`：1146.31–F16 `SetCurve(S9b+WHITE_SAT, ΔEV 2.4, t−1146.31, 3, Ls, Lw, Ls, Lw)`、F16–1178.46 `SetFlat(S10, 1, 0)` + `SetBreath(0.02)`（先设呼吸再 SetFlat，呼吸确实写进 `_Udon_OverlayCurve.w`）、1178.46–1186.46 `SetCurve(S11, ΔEV 1→0/4 s, t−1178.46, 5, Lw, L11, L11, Lw)` + 三瓣 0 / 1.5 / 3 s、其余 3 s。参数顺序、填色线性值（与 `WhiteSchedule.json` `overlay.fills` 逐位相同）、ΔEV 与 `LanbaiGrade` 同源，都和 `Overlay/README_Overlay.md` §3 的表对得上。没有调用别的 U# 类的静态方法（自带一份 `EvOverlayAlpha`），可以。 |
| 3 全局量卡住 | **成立** | `LanbaiMirrorsDriver.cs:79–90`（`Start` 写 0）、`:125–132`（`LanbaiActivate(false)` 写 0）、`:146–152`（窗口外与 t ≥ F16 写 0，并关掉出了活动窗口的镜子）。窗口末挪到 F16 + 1 s，在白下面。 |
| 4 公告板朝每只眼 | **成立** | 尘 `Lanbai_MirrorDust.shader:128–131`、反射星 `Lanbai_MirrorStars.shader:135–142` 的四边形基都由 `LanbaiCentreEyePos()` 建；星的像点 P 仍逐眼解。 |
| 5 镜面调色后不是 `#CDBF9C` | **成立** | `_ToneColor` (1.262, 0.974, 0.484)，亮度 = 1.000，`_BronzeTone` 1；shader 两处（镜面 `:199`、星 `:133`）与移植（`:31–32`、`:213`、`:267`）同一写法。r4 图上镜面码值 B/R 0.70–0.80、G/R 0.89–0.94，读成白铜。 |
| 非阻断 | 大部分落实 | `flashcheck/` 已推；`_StencilRef` 已在 spec §6 改正；`蓝白/Build/Act10 White` 删了。仍未补：`WhiteSchedule.json` 与 `make_white_schedule.py:74` 仍引用不存在的 `Act10_White/Docs~/white_check.txt`（README 已改成指向 `flashcheck/`，JSON 跟着改一下）。 |

另外核对过、没有问题的：D-38 方案 H 的数据链（`make_schedule.py` 默认 H → JSON `scheme13 = "H"`、`rim_soft` 1135.31 / 4 s / 0.8 → `bake_cs.py` → `LanbaiMirrorsData.RimSoftStart` → 搭建脚本拷进驱动 → `_RimSoft` / `_RimSoftFrom` MPB；移植读同一个 JSON）；第 13 面 +3 EV 只在 1138.78 → 1146.31；脉冲只给第 1–11 面；尘槽 / 模板槽在驱动与搭建脚本里一致；尘网格 UV 通道（`uv2`/`uv3` = TEXCOORD1/2）与 shader 一致；反射星的收敛淡出（1.0° → 0.3°）与掠射淡出（smoothstep 0.03–0.15）shader 与移植同数；所有 `_Udon_` 量已登记。

---

## 新的阻断

### 1. 白的驱动无条件 `Hide()`：每个加入者的出生黑场在预热结束那一帧被关掉；1136.58–1146.31 里加入的人整段没有出生黑场

- **在哪**：`Act10_White/Runtime/LanbaiWhiteDriver.cs:72–80`（`LanbaiActivate(false)` 里 `ClearLobes()` + `Hide()`）、`:130–136`（窗口内但不在遮罩段的每一帧都 `SetBreath(0)` + `Hide()`，窗口是 {1136.58, 1187.46}）。
- **问题**：分发层的预热（`Director/README_Director.md` §2：出生的 3 s 黑里 `LanbaiPrewarm()`，所有驱动 `LanbaiActivate(true)` 两帧，然后按窗口逻辑关回去）意味着**每个客户端出生时**白的驱动都会收到一次 `LanbaiActivate(false)`，于是 `Hide()` 把正在画的出生黑场（`Overlay/README_Overlay.md` §3 第一行，`SetCurve` 从黑淡入）清掉、球的 renderer 关掉——预热的根物体正好在这一帧露出来（圣经 §1.9 要求预热在黑下）。驱动按类名排序，`LanbaiWhiteDriver` 排在后面，所以同一帧里别人刚写的遮罩会被它覆盖。更糟：t 落在 1136.58–1146.31（或 1186.46–1187.46）里加入的人，白的驱动在窗口内**每帧** `Hide()`，出生黑场整段被吃掉。这也违反分发层的规则 4（“窗口重叠的驱动不能写同一个全局量”）：白的驱动在它根本不画遮罩的 10 s 里每帧写遮罩的全部全局量。`LanbaiOverlay` 自己已经按总导演终审 #9 去掉了无条件 `Hide()`，门内的驱动（`LanbaiInsideDriver.LanbaiActivate`）也不在关窗时 `Hide()`。
- **改**：加 `private bool ownsOverlay;`。`DriveOverlay` 里每次调 `SetCurve` / `SetFlat` 时置 true；不在遮罩段（t < 1146.31 或 t ≥ 1186.46）时**只有 `ownsOverlay` 为真才** `ClearLobes()` + `Hide()` 一次并置 false，否则什么都不写；`LanbaiActivate(false)` 同样只在 `ownsOverlay` 时 `Hide()`。`LanbaiActivate(true)` 照旧清 `lobesSet`（D-33 #6 从 t 重建不受影响：下一帧在遮罩段里会重新 Set 并重新拿到所有权）。README §2“窗口外 `Hide()`”改成“自己画过遮罩才在离开时 `Hide()` 一次”。

---

附注（不阻断，顺手改）：
- `LanbaiWhiteDriver.cs:82–93`：`isVR` 在 `DriveOverlay` 之后才取，加入后的第一帧 VR 用户用桌面的 `lWhite` 0.86 算曲线；把取 `isVR` 挪到 `DriveOverlay(t)` 前面。
- `README_Act10.md` §0 第 3 步写 `LB_Journey.ApplyGrades` “并画遮罩（§2）”，与 §2（驱动画遮罩）矛盾，本地可能画两遍；§3 写“镜子的窗口在 F16 结束”，实际是 F16 + 1 s。
- `README_Mirrors.md` §2 第 3 条仍写“往 `#CDBF9C` 的色调拉 65 %”，现在是 100 % 的反解色调；`spec_conventions.md` §6 的 MPB 列表缺 `_RimSoftFrom`。
- 遮罩的 `lSceneMask` 0.30 是按正前方（保持末 APL ≈ 145）定的；抬头看如果更暗（APL ≈ 100），按同一条曲线 1 s 约 +1.08 EV。圣经的录像协议只要正前方与向下看，所以不阻断；本地截 (g) 时顺手加一段抬头 +45°。
