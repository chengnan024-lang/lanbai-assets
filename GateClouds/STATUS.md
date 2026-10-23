2026-10-23 · 第 4 轮（美术 r2 有条件通过、技术 r2 有条件通过 的全部条目）：边光碎块去掉、每个云头自己的银边、楔外 ×0.35、云谷加深、裂口脚下的光（按定稿 U8 校准）、关掉 FootSkyline 和旧光束、云卡底边羽化、远云 +13% 雾；技术：步进区间从 ts 起、深度不近于代理面、反射重载、FindInScene、_Init；共用编译检查 0 错 0 警告 · 下一步：全尺寸图 + 1:1 前后裁图 + 性能方案裁图 + 滚动序列，第 3 轮独立评审 · 阻塞：无（性能待本地实测；正式世界要门的总驱动写全局量）

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
