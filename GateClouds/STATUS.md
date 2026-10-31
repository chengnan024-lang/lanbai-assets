2026-10-31 · **暂停（小楠：《蓝白》全部制作停止，恢复日期待定）· WIP 已推，没合 main** · 停在第 11 轮（D-50 #5–#7）：#5 门测试场景没有体积云 → Build 找不到时自建 Lanbai/GateVolumeDeck（CloudDensity128 由 Textures/CloudDensity128_grids.bytes 生成，阿白的种子）已写、未在 Unity 跑；DeliveredGate 修：驱动 Build 自己量群臂 _VariantDims（GateMultitude_v2.fbx）不再靠 LB_GateTest.Apply，已写；#6 预算：参照里数了每像素密度取样（U7 174 次），试了光照隔 4 步（-40%，但亮了 1.4 APL，要改成插值或单抽头）、碰云前 2 倍步长、云里步长放大、早退 0.03（这三项画面基本不变），shader 还没改；半分辨率在 VRChat 里做不了（没有 CommandBuffer / 每眼 RT），要写进回复；#7 回头看：130–150° 侧窗在 181.0–181.6 s 以后被第 1 重的布挡住（手都在唇外），卷完最早 181.9 s，等总导演选——A 两只（L2、R1）提早 ~0.5 s 卷完、终点挪到开口左后方；B 两只指尖伸过开口进门内（要和门内一起做）；C 接受只在后窗看得到，把两只终点挪到开口左沿后面。下一步：等总导演叫；先选 A/B/C，再做 #6 的 shader（光照缓存改插值 + 步长三项）出前后 1:1 和估算，最后在 Unity 复测 #5

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
