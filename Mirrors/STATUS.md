2026-10-24 13:58 UTC · **可以终审了。** 新：总导演指出镜背铭文是时代错位（现代简体宋体）→ 已改：35 个铭文字直接取自克利夫兰 1995.298 铭文带照片（汉镜铭体、繁体古字形），十二地支取自 1995.301，不再用任何字体；铭文改成方格字距；对照图 `Docs~/inscription_plate.png`（上真镜 / 下我们），新的镜背预览 `Docs~/iterations/tex_r4.png`。此前：D-38 方案 H、全部序列 PASS、评审 r1/r2 阻断已改、shader 0 错误（没在 Unity 里编译）。卡点：无。

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
