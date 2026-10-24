# 第 1 轮 · VR 舒适 + GPU 性能评审（独立 agent）

1. BLOCKER 云海每帧估 4–8 ms（Field ~36 次 × 3 取样，aniso 16 RGBA32，SV_Depth 无 early-Z）→ 代理面 + SV_DepthLessEqual、aniso 4 / along ≤ 4、micro 分支、二分 2–3 + 插值、步数和范围收紧（已改；新估算 1.5–2.5 ms，见 README §3.4）。
2. MAJOR 透明叠绘：U8side 楔 1.85 FSE、key 4.30 合计 → 楔整条折叠、视锥 25–40°、止于眼前 300 m、条带裁到光瓣、卡片裁到包围盒（已改；fse_clouds.json）。
3. BLOCKER 近处云头角速度违反 §1.8（U6 时云头距眼 6–15 m）→ 车道（±56 m）内按比例压到眼下 57 m（已改）。MAJOR IGN 逐眼锁屏 → 世界方向哈希（已改）。MAJOR 远处 1 px 银边闪 → 亚像素淡化（已改）。MINOR 光束用两眼中点（已改）。
