# 镜与白 · 进度

2026-10-25 · 终审（10-25 13:13，对 fa6ae23）逐条改完，见 `README_Mirrors.md` §10；Unity 里的技术验收归阿白（D-46）。

| 件 | 状态 |
|---|---|
| 十三面镜的时间表 `MirrorSchedule.json` | ✅ 方案 H（D-38）；M-1 钮的检查（第 1 面钮离车厢 1.85 m、第 2 面 2.71 m）、M-8 第 1 面 1024.41 起凝聚；`make_schedule.py` 全 PASS |
| 网格 + LOD、镜背 / 镜面 / 字形 / 流云贴图 | ✅ M-5 花瓣、M-6 照片镜像、M-7 铭文笔画 |
| `Lanbai/BronzeMirror`、`MirrorStars`、`MirrorDust` + numpy 移植 | ✅ M-2 无极点立方体图、M-3 碎块带 + 尘、M-4 第 13 面远处的模糊盘与亮环；shader 检查 0 / 0 |
| 驱动 `LanbaiMirrorsDriver` | ✅ M1 减少外部调用（每帧约 1 000–1 500 次，手数估算，README §3）、M2 数组长度检查、G1；C# 检查 0 / 0 |
| 搭建 `蓝白/Build/Mirrors` | ✅ D-41 共用工具 |
| 迭代图 | ✅ r7（`Docs~/iterations/r7_sheet.png`）+ M-11 关键帧 1920×1080（`r7_key_*.png`、`Docs~/visibility_21ppd.md`） |
| flashcheck | ✅ §7 |
| 没做 / 做不了 | Unity 编译、头显实测、带车厢的合成（D-46：阿白） |
