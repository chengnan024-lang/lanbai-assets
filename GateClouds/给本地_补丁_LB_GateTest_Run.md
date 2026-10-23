# 给本地：`FromLocal/gate_test/code/LB_GateTest_Run.cs` 的补丁（GateClouds 用）

门（GateClouds）写，2026-10-23。总导演裁决 D-15：本地改，门不动 `FromLocal/`。

**为什么改**：`蓝白/Gate Clouds/Build` 会关掉这几样的 renderer：
- 平面光池 `Tear_CloudGlow` 和 `Tear_CloudGlow_Additive`、光路 `Tear_LightLane`。光池现在由云海 shader 自己画；平面的会被真实云头切碎，而且会画两遍。
- 旧的等宽光束 `Shaft_00/01`。它们和新的 `GateBeam_Shaft_*` 重复。

可是 `LB_GateTest_Run` 每次 Apply 都用 `SetPB(..., on = true)` 把它们重新打开。不改的话，GateClouds 的截图和帧时间都作废（README_GateClouds §2 第 4 步）。

**怎么改**：只改 `SetPB` 的第 4 个参数（`on`），别的不动，`_Intensity` 等照写（关着的 renderer 写了也无害）。行号按 main 上的版本。

| 行 | 原文 | 改成 |
|---|---|---|
| 123 | `SetPB(tear, "Tear_CloudGlow_Additive", mpb, kAdd > 0f, "_Intensity", 0.25f * kAdd, "_FootGlow", 2.2f * kPool);` | `SetPB(tear, "Tear_CloudGlow_Additive", mpb, false, "_Intensity", 0.25f * kAdd, "_FootGlow", 2.2f * kPool);   // GateClouds: the deck draws the pool` |
| 124 | `SetPB(tear, "Tear_CloudGlow", mpb, true, "_Intensity", 1f * kPool, "_FootGlow", 0.98f * kPool);` | `SetPB(tear, "Tear_CloudGlow", mpb, false, "_Intensity", 1f * kPool, "_FootGlow", 0.98f * kPool);   // GateClouds: the deck draws the pool` |
| 127 | `SetPB(tear, "Tear_LightLane", mpb, true, "_Intensity", kLane, null, 0f);` | `SetPB(tear, "Tear_LightLane", mpb, false, "_Intensity", kLane, null, 0f);   // GateClouds: the deck draws the pool` |
| 134 | `if (st != null) SetPB(st, st.name, mpb, true, "_Intensity", F(G(OJ, "shaft"), 0.35f) * F(G(s, "gain"), 1f), null, 0f);` | `if (st != null) SetPB(st, st.name, mpb, false, "_Intensity", F(G(OJ, "shaft"), 0.35f) * F(G(s, "gain"), 1f), null, 0f);   // GateClouds: GateBeam_Shaft_* replace Shaft_00/01` |

- **125、126 两行**（`Tear_SkyFolds`、`Tear_Halo`）**不改**：它们不归云。
- `Tear_FootSkyline` / `Tear_FootSkylineIn`：Run 里没有打开它们的代码，Build 关掉就一直关着，**不用改**。
- 之后的第 128–130 行（`lane.localScale`）照旧，没有影响。

**改完以后检查**：
- 进 Play 前、后各看一眼 Hierarchy：`Tear_Root` 下 `Tear_CloudGlow`、`Tear_CloudGlow_Additive`、`Tear_LightLane`、`Shaft_00`、`Shaft_01` 的 MeshRenderer 都是关的；
- `GateBeam_Shaft_00/01` 是开的。
