**暂停（10-31，小楠决定全片停工）：停在 D-50 #1 做完、还没报告、没合 main。** 白的冲击改成 +0.8 EV / bloom 0.4（移植里 x35 的 1 s 升幅从 1.07 降到 0.86，按差值推 Unity ≈ 0.79）；第 13 面环到 1131 时 ≤ 88.5（全部 61–89）；w* / m12* 重跑全 PASS（白·侧上方 1 s 0.92 最高）。下一步：README §7 / §10 和 README_Act10 写进 D-50，把 commit 和 `Docs~/flashcheck/x35_d50.json`、`Docs~/iterations/x35_d50_strip.png` 交总导演，请阿白在 Unity 里重量 x35。

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

**待办（总导演 10-26，看 r8 时记的）**：第 13 面在远处时的亮环，向下 −45° 在 1131 附近到 luma 92，比圣经的 60–90 高 2。这次接受；下次动 shader 时把 `rimGlow` 压一点（约 × 0.95），压到 90 以内。r8 条带：`Docs~/iterations/r8_sheet.png`（d0fd5e4，只有图，不合）。
