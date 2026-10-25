2026-10-25 04:10 UTC · **可以终审了（只剩 C1 等总导演裁）。** 终审 r3 逐条改完（README §9）：极坐标带串珠法、铭文逐字描笔画、镜背不透明铜绿、真流云带与格角云气纹、乳钉球面、去 rim_soft、+2.7 EV、第 10 幕搭建菜单（D-41 共用工具）、迟到的人（LanbaiSpawnFade + LanbaiOverlayWindow，D-43，join_check 全 PASS）、镜缘点光、F5–F10 / C5–C8。r6 渲染用真贴图与 shader 逻辑（`Docs~/iterations/r6_sheet.png`）。全部 20 条序列重跑：19 条 PASS；**白抬头 2 s 爬 1.84 EV（限 1.8）不过 = C1**，方案 A / B 在 `给总控.md`，裁了就改。shader 0 错误、C# OK（都不是 Unity 编译）。

# 镜与白 · 进度

| 件 | 状态 |
|---|---|
| 十三面镜的两段时间表 `Mirrors/MirrorSchedule.json`（穿越、直径、方位、脉冲、运动节点、可见度、溶解） | ✅ v1（`Tools~/schedule/make_schedule.py`，核对 `Docs~/schedule_check.txt`、图 `Docs~/schedule.png`） |
| 白的曲线 `Act10_White/WhiteSchedule.json`（冲击、膨胀、保持、遮罩、第 13 面自发光、桌面镜头层、10 → 11） | ✅ v1（`Act10_White/Tools~/make_white_schedule.py`） |
| lookdev brief + 形制考据 | ✅ `Docs~/lookdev_brief.md`、`Docs~/research_tlv_form.md` |
| 镜子网格 + LOD、镜面 / 镜背贴图 | ⏳ |
| `Lanbai/BronzeMirror`、`Lanbai/MirrorStars`、`Lanbai/MirrorDust` + numpy 移植 | ⏳ |
| Blender 迭代（≥ 3 轮）+ 评审 | ⏳ |
| 驱动 `LanbaiMirrorsDriver`、`LanbaiWhiteDriver`（UdonSharp） | ⏳ |
| 搭建脚本 `蓝白/Build/Mirrors`、`蓝白/Build/Act10 White`、导入设置 | ⏳ |
| flashcheck（穿越、白） | ⏳ |
| README | ⏳ |
