2026-10-23 02:00 UTC · 第 3 轮（总工程师 + 美术审片预审 + 四份评审的余项）：云海步进只用 tex2Dlod、各向异性只在着色、线性插值求交（梳齿 53% → 4.7%）、ShadowCaster 深度 pass、驱动挂常开物体 + 写 _Udon_FogBandColor + U# 程序资产、楔只朝裂口且止于眼前 300 m（FSE 全部在线内）、裂口 shader 用公共 LanbaiVR、README 重写（含与评审的分歧）、EXR · 下一步：全尺寸 PNG、2 秒滚动序列、第 2 轮独立评审 · 性能估算 1.5–2.5 ms 待实测，方案在 给总控.md

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
