2026-10-24 12:30 UTC · 第 13 面方案 G（2.4 km，先快后慢、快的时候镜缘柔化）与 H（17 km，一直慢）都过了总导演的镜缘规则、白的序列也都 PASS，推荐 H，等总导演挑；镜背主区改用克利夫兰 1995.301 的照片；穿越序列 m1/m10/m11 PASS。下一步：按挑定的方案改时间表、重跑全部序列与定稿图、第二轮评审。卡点：等总导演挑方案。

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
