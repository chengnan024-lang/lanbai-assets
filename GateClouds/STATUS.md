2026-10-23 · **驱动 v1.1 可以终审了** · 门的两盏灯归驱动（车厢裂口光 U9 → U9 + 0.25 降到 0，#B9B6D6；补光随臂关）；D-22 天 / 雾 / 月 / 星只在 [U6, U9) 写，数值读天空的 SkyPresets / FogPresets（moon_night → act4_gate，133.8 → 163.8）；云套件不再写光雾带；收臂加眼的位置、群臂先开关、隐藏的臂不算位姿、Start 里 TearPos.w = 0、cues / 门内 JSON 断言；窗口结束回头看那一条记在 README §4；Moon 的建议在 给总控 §8；C# 检查 OK

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
