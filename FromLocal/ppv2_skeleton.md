# PPv2 管线骨架（本地 → 云端，给 LanbaiGradeBuilder 对接用）

写的人：本地 Cowork 会话，2026-09-30。代码：`dream/Assets/Lanbai/Editor/LB_Grades.cs`（槽 + 项目设置）、`Scripts/LB_Journey.cs` 的 `ApplyGrades`（按时间轴驱动权重）。验证：r0097（23 个时刻的权重，下面 §4）。

## 1. GradeBuilder 生成到哪里就会被接上

- **profile 路径：`Assets/Lanbai/Grades/Profiles/Lanbai_<键>.asset`**，键 = `grades_final.json` 里的名字：
  - 场景：`S1 S2 S3 S4 S4c S6 S7a S7b S8 S8b S9a S9b S10 S11 S12`
  - 助手：`EXPO_UP EXPO_DOWN WHITE_SAT WHITE_BLOOM LENS_CLEAN LENS_ARCHIVE`
- 一键生成世界时，`Lanbai/PostProcess/Grades/<键>` 和 `Lanbai/PostProcess/Helpers/<键>` 各建一个全局 volume（layer 4），priority：场景 1–15（时间顺序）、EXPO_UP 100、EXPO_DOWN 99、WHITE_SAT / WHITE_BLOOM 96、LENS_CLEAN 199、LENS_ARCHIVE 200；weight 由 Udon 每帧写。
- **15 套场景 profile 都在 → 自动切过去**（`useGrades = true`）：旧的 8 套 ACES 权重归 0，旧的 White / Black 提到 priority 150 / 151 只当全屏遮罩（占位，等 `Lanbai_Overlay`）。缺任何一套就还用旧的 8 套。
- EXPO 公式里的底值 b 用的是 profile 里真实的 postExposure（不在就用附录 B 的数）。
- 如果 GradeBuilder 自己也建 volume：请告诉我，我这边就不建槽，改成按名字找你们的 volume。

## 2. 权重（§1.4 + §6.x 转场总表，全部是 t 的确定函数）

- 交叉淡化：旧的保持 1、新的 0 → 1，新的到 1 旧的才归 0；遮罩全满时同一帧硬切（投入 → 晨、白 → S10、假醒 → S11、醒 → S12）。
- 时刻：S1 → S2 U1 起 8 秒；S3 叠在 S2 上：U2 起 40 秒到 0.3，入云（U5）7 秒线性到 1；S4 U6 起 30 秒；S4c U9 + 0.5 起 8 秒；S6 在黑遮罩满时硬切；S7a F2 + 1 起 1.5 秒；S7b F3 → F5 线性；S8 出海（F9b）起 6 秒线性；S8b F12 起 8 秒；S9a 跟着变暗（F12 + 15 起 8 秒）；S9b F13 → F16 x^2.5。
- ΔEV 事件合成一个值：破云 +0.5（0.4 升 / 3 降）、U9 +0.3（0.2 / 0.5）、FLASH_TEAR +1.5（U12 − 0.5 起 0.4 秒 EV 线性，保持 0.1，黑遮罩 0.25 秒里归零）、入水 −0.5（0.3 / 1）、出海 +0.8（F9b + 6 起，0.4 / 4）、镜子 +0.35（0.08 / 0.35，只前 9 面）、白的冲击 → +1.0（1.2 秒）→ 膨胀 → +2.4（6 秒）→ 遮罩 3 秒里保持、第一次白之后 +1.0（4 秒衰减）、第二次白之后 +0.8（5 秒衰减）。
- `EXPO_UP = ΔEV / (4 − b)`、`EXPO_DOWN = −ΔEV / (b + 4)`，b = 按 priority 顺序 lerp 出来的场景 postExposure。
- WHITE_SAT：冲击 0 → 0.42、膨胀 → 1、遮罩满时归 0；WHITE_BLOOM：冲击 0 → 0.5、膨胀 → 1、遮罩 3 秒里 1 → 0。
- 镜头层（只在桌面）：LENS_CLEAN 一直 1（白的膨胀 6 秒里降到 0，白里 0）；LENS_ARCHIVE U0 起 8 秒到 1、U3 起 8 秒回 0、假醒 1。VR 里两个物体直接关掉。

## 3. 相机和项目设置

- 参考相机：near **0.05**、far **45 000**、Allow HDR、Clear = Skybox；PostProcessLayer：AA None、Stop NaN、Directly to Camera Target 关（PPv2 3.4 的 dithering 一直开着，没有开关）。Volume layer 还是 4（Water），没有另建 "PostProcessing" 层。
- 雾：Shader Stripping 改成只留 Exponential（场景一直是 Exponential）。
- **⚠ 圣经 §1.5 的"Built-in 灯光陷阱 1"写反了：VRChat SDK（`com.vrchat.base/Editor/VRCSDK/Dependencies/VRChat/EnvConfig.cs`）强制 `lightsUseLinearIntensity = true`（还有 `lightsUseColorTemperature = true`），它就是按客户端的设置来配编辑器的。** 所以在 VRChat 里灯的线性照度 E = 颜色_线性 × 强度，**不是** × 强度^2.2；平行光的 Inspector 值应该 = E，不是 E^(1/2.2)。calib_final 里所有"Inspector"一栏和按 gamma 换算的灯光强度请重算。（我 9/30 按圣经把它改成过 false，SDK 在下次编译时就改回了 true——现在是 true，和客户端一致。）
- HDR：Tier Settings 同样被 SDK 的 EnvConfig 清空（客户端用自己的）；桌面默认就是 HDR FP16，所以没问题，我这边只查不改。

## 4. 验证（r0097：没有 profile，强制 useGrades = true，只看权重）

| t | 幕 | 权重 | ΔEV / b |
|---|---|---|---|
| 11 | 夜路 | S1 1 · LENS_ARCHIVE 0.97 | |
| 23 | 夜路 | S1 1 · S2 0.77 | b −0.12 |
| 111 | 入云 | S2 1 · S3 0.65 | |
| 135.2 | 破云后 1.4 秒 | S3 1 · S4 0.006 · EXPO_UP 0.068 | +0.33 / −0.90 |
| 249.4 | 投入 | S6 1 · 黑 1 | |
| 257 | 晨揭开 | S6 1 · 黑 0.59 | |
| 353.3 | 入水 | S6 1 · S7a 0.07 · EXPO_DOWN 0.009 | −0.03 |
| 947.5 | 出海 | S8 1 · EXPO_UP 0.145 | +0.65 / −0.50 |
| 1006 | 变暗 | S8b 1 · S9a 0.49 | |
| 1143 | 白的膨胀 | S9a 1 · S9b 0.88 · EXPO_UP 0.441 · WHITE_SAT 0.68 · WHITE_BLOOM 0.73 · LENS_CLEAN 0.55 | +1.63 / +0.30 |
| 1149 | 遮罩 | 白 0.90 · S9b 0.99 · EXPO_UP **0.649** · WHITE_SAT 1 · WHITE_BLOOM 0.10 | +2.40 / +0.30 |
| 1161 | 白 | S10 1 · 白 1 | |
| 1181 | 假醒 | S11 1 · 白 0.68 · EXPO_UP 0.088 · LENS_ARCHIVE 1 | +0.36 / −0.15 |
| 1253 | 醒 | S12 1 · 白 0.12 · EXPO_UP 0.078 | +0.31 / 0 |

1149 秒那一行的 EXPO_UP = 0.649 和附录 B 表里"膨胀 w = 0.649 at b = +0.3"一致。

## 5. 等你们的

- `LanbaiGradeBuilder.cs` 生成 21 个 profile 到上面的路径 → 一键生成世界 → 自动切换，我拍 §9 第 3 条的调色测试卡。
- `Lanbai_Overlay` v2（遮罩球，EV 线性 alpha + 填值补偿）→ 换掉现在当遮罩用的旧 White / Black。
- 如果 `LanbaiDirector` 要接管权重，`ApplyGrades` 就是现在的实现，可以直接对照。
