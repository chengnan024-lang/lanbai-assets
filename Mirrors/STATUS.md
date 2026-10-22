2026-10-22 20:40（北京 10-23 04:40）· M-A 推了：十三面镜两段时间表 `MirrorSchedule.json`（+ 生成器与核对，全部 PASS）、白的曲线 `Act10_White/WhiteSchedule.json`、lookdev brief。下一步：镜子网格 + LOD、贴图、`Lanbai/BronzeMirror` shader 与 numpy 移植，Blender 第 1 轮。卡点：无（遮罩 v2、Director 的曝光归属、天空第 9 幕的全局量含义见 `给总控.md`）。

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
