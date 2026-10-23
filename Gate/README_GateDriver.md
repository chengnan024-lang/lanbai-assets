# 门的总驱动 `LanbaiGateDriver`（第 4 幕）

门（GateClouds 会话）写，2026-10-23，按总导演裁决 D-15。**没在 Unity / UdonSharp 里编译过**。用共用检查跑过：`Common/Tools~/compile_check/check_cs.sh GateClouds Gate`，editor + player 两组 Roslyn 和 U# 规则 lint 都过，`C# CHECK OK`。

**为什么要它**：正式世界里只有它写 `_Udon_CloudTop`、`_Udon_GateOrigin`、`_Udon_TearFoot` 这些全局量。没有它，云海不流动，云顶停在 −57.4，峡谷和光池钉死在世界里。所以它是上线的前置条件。

## 1. 文件
| 文件 | 是什么 |
|---|---|
| `Runtime/LanbaiGateDriver.cs` | 驱动（U#），CONTROL §5 接口：`LanbaiTick(t)`、`LanbaiActivate(on)`、`LanbaiWindow()` = {U6 − 20, U9 + 2} = {113.80, 181.55} |
| `Runtime/LanbaiGateTestClock.cs` | **只用于测试**的 Play 模式时钟（U#）：从 `startT` 按真实时间 × `speed` 走，每帧先 tick 门、再 tick 云。正式世界里删掉，那里由 Director 分发 |
| `Editor/LanbaiGateDriverBuilder.cs` | 菜单 **蓝白/Gate/Build Driver**（和 **… + Test Clock**） |
| `GateDriver_Bake.json` | 驱动每帧要用的数据，从 `GateLayout_v2.json` 拍平；由 `Source/gate_driver_bake.py` 生成，改了 JSON 就重跑 |

U# 的程序资产、编译和 `CopyProxyToUdon` 都用 `GateClouds/Editor/LanbaiGateCloudsBuilder.cs` 的同一套代码，所以 `GateClouds/` 必须一起拷进工程。

## 2. 每帧做什么（README_GateLayout §2、§2.1、§2.2、§4.1，和本地 `LB_GateTest_Run.Apply` 同一套算法）
- **GateRoot**：`position = (0, 150 − h_bus(t), v_g (U9 − t))`。
- **Tear_Root**：缩放 = H(t) / 1000，H 是单调 PCHIP，斜率在 bake 里，和 scipy 一致。
- **64 个实例**：
  - 位姿按 rise → lean → track → close 依次算，近处 3 条按车的坐标加 drift；
  - 单独的臂：显现按自己的关键帧，renderer 开关 + `_Reveal`，**只在值变化时写 MPB**；
  - 群臂：两组只在穿过 0 的那一帧开关 renderer，其余靠全局量 `_Udon_MultReveal`。
- **远潮**：`_Reveal` 和开关。
- **裂口**：天褶 `_Intensity`（`skyfolds_intensity_keys` × 1.0）；光晕按距离淡出，k < 0.05 时关；车厢专用的裂口光转向裂口核心。
- **全局量**：`_Udon_CloudTop`、`TearPos`、`TearH`、`MoonDir`、`GateTime`、`GateOrigin`、`TearFoot`、`TearTop`、`MultReveal`、`MoonDisc`、`TearOpen`、`RipProgress`、`TearHide`。
- **U9**：从 U9 + 0.15 s 起 `_Udon_TearHide = 1`，**所有臂的 renderer 都关**（单独的臂、群臂、远潮），天褶、光晕也关。这就是总导演说的"收掉车后的臂"：它们不会碰到 4c 门内的雾。往回拖 t 会自己恢复。
- **不归它写的**：
  - `_Udon_InsidePortal`：门内驱动写；
  - `_Udon_FogBand*`：`LanbaiGateClouds` 写，颜色和截止时间 U9 都从 `GateClouds_Layout.json` 的 `fog_band` 读；
  - Tear 套件的 CloudGlow、LightLane、FootSkyline、旧光束：云的 Build 已经永久关掉。
- **MPB 的写法**：不用 `GetPropertyBlock`（它在不在 Udon 白名单里还没确认）。每个 renderer 的整块值（`_Phase`、`_FogCapI`、`_RevealGroup`、`_Reveal`、群臂的 `_VariantDims` / `_OcclusionMap`）都存在驱动里，写的时候整块写。`Start` 里写一遍，因为进 Play 时编辑器写的 MPB 会丢，CONTROL §5。
- **每帧的量**：
  - 64 个 Transform；
  - 显现变化中的单独臂，约 26 条 × 3 个 LOD 的 MPB 写入。显现稳定时为 0：U7b 以后几乎都是 0；
  - 2 个裂口部件，13 个全局量；
  - 群臂 36 × 3 个 renderer 只在两次穿过 0 时各写一次；
  - 每帧还调一次 `Networking.LocalPlayer` 的头部位置，给光晕的距离用；在编辑器里没有玩家时，用 U7 的眼位。

## 3. 怎么搭
**顺序**：
1. `LB_GateTest.Build`（门）。
2. **蓝白/Gate Clouds/Build**（云）。
3. 跑一次 `LB_GateTest.Apply`（任意 t）。它会把群臂的 `_VariantDims` / `_OcclusionMap` 写进 MPB，驱动的 Build 从那里抄。
4. **蓝白/Gate/Build Driver**。

Build Driver 做的事：
- 在常开的物体 `Gate_Driver` 上加驱动（场景里有 `Director` 就挂在它下面），填好所有数组；
- 驱动的 `roots` = GateRoot、NearRoot_bus；
- Console 打印找到多少实例、多少 renderer。缺的会警告；群臂没有 `_VariantDims` 也会警告，那就是第 3 步没跑。

以后重跑门的 Build，第 2–4 步都要重跑。漏了也不会抛异常：驱动发现 Transform 或 renderer 丢了，会跳过并警告一次"请重跑"。

**Play 模式测试（头显检查、Play 里的实测）**：
- 用 **蓝白/Gate/Build Driver + Test Clock**。它多建一个 `Gate_TestClock`：从 U7（150.30）走到 U9 + 2，然后循环。`startT`、`speed`、`loop` 都能在 Inspector 里改。
- 进 Play 以后云海随 v_g 流动，云塔按时间塌陷，臂按时间显现。这样 GateClouds README §8 第 4 条的头显检查就能做：滚动 10 秒、闭单眼。
- **正式世界里删掉 `Gate_TestClock`**。
- 测试场景里**不要同时让 `LB_GateTest` 的编辑器 Apply 和时钟一起写**。编辑模式下用 `LB_GateTest.Apply`，Play 模式下用时钟。

**正式世界**：
- Director 的菜单 **1 Generate Dispatcher** → **2 Wire Scene**，会自动认出 `LanbaiGateDriver` 和 `LanbaiGateClouds`，两者的时间窗相同。
- **场景里不要再放 `Tear/LanbaiTearParams`**：它每帧写 `_Udon_TearOpen` / `RipProgress` / `TearHide`，会和驱动抢。这几个量现在归门的驱动写，登记表上本来就是"门驱动"。

## 4. 已知 / 没做
- **U9 以后 GateRoot 的去向**：照旧按 v_g 往后走，到窗口结束（U9 + 2）。门内会话要的"门内减速曲线"在门内驱动那边；臂在 U9 + 0.15 已经关掉，云海以远被 `_Udon_InsidePortal` 裁掉，所以这两秒 GateRoot 怎么走看不出来。
- **触手指尖在第 1 重唇后卷回**（门内 4 件事里的最后一件）：没做，臂在 U9 + 0.15 已经全关，这件事就不需要了。如果门内要在 4c 开头还看到指尖，需要另定。
- 天褶、光晕的 MPB 每帧整块写（`Clear` 后只写 `_Intensity`）。如果裂口材质上有别的值是靠 MPB 给的，会被清掉。按套件的现状，那些值都在材质上。
- 第一次在 Unity 里跑，请把 Console 原样推到 `FromLocal/`（含 UdonSharp 的输出）。
