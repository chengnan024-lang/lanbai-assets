2026-10-23 · **可以终审了** · v1.4：终审美术、技术都是有条件通过、没有 BLOCKER（Docs~/reviews/final.md）；共用编译检查 shader 8 文件 0 错 0 警告、C# OK；终版图、裁图、EXR、2 秒滚动 mp4 都是终版代码出的；画质开关（default / auto_lite）+ 本地实测请求；本地补丁 给本地_补丁_LB_GateTest_Run.md · 合并后：LanbaiGateDriver（D-15 第一件）、云塔视差卡、终审余项（README §10 第 10 条）

## 进度
- [x] 云海 `Lanbai/GateCloudDeck` + `Deck_Detail_1024` / `Deck_Macro_512` + `Source/deck_ref.py`（逐行 numpy 移植）；独立技术审查一轮（移植对照），改完
- [x] 云卡 shader `Lanbai/GateCloudCard`（三通道光照：月 35°、月 70°、天光）
- [x] 光束 / 阴影楔 `Lanbai/GateBeam`（越远越宽）
- [x] 峡谷：直接刻进云海高度场（`_Crev`），不用卡
- [x] `Editor/LanbaiGateCloudsBuilder.cs`（蓝白/Gate Clouds/Build）、`Runtime/LanbaiGateClouds.cs`（LanbaiTick / LanbaiActivate / LanbaiWindow）
- [x] 收尾：远潮 shader v2.3（接 `LanbaiGateSky.cginc`）、TentacleSway v2.7d（`noforwardadd`，去掉 POINT 变体的除零）、`Lanbai_Tear.shader` 两处 `[Header]` 的括号 / 逗号
- [x] 检查：slangc（三个新 shader + 远潮）、mcs 对 Unity API 桩的 C# 类型检查
- [x] 门用云卡 v2（Congestus / Bank / Strato / Puff / Wisp）
- [x] `GateClouds_Layout.json`、整帧预览（key / U7 / U8 前 / 侧窗 / 后窗）、`Docs~/compare_*.png`
- [ ] 美术评审 + 技术评审 + 640 px 陌生人测试（独立 agent），改完再审
- [ ] README 收尾、HANDOFF_LOG 一条
