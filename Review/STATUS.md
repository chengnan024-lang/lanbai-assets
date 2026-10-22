2026-10-22 20:40 UTC · 审片标准 v1（标准.md + targets.json + 量图工具）已推；门的定稿 + 本地 Unity 截图的练习审片在跑（评审团 + 对抗核查）· 下一步：写练习审片结论、全片审片总表，开始巡检各包分支 · 没有卡住

# 美术审片 · 状态

- 分支 `pkg/review`，只改 `Review/`（例外：别人分支上的 `<包>/美术审片意见.md`）。
- 已有：`标准.md`（审什么、怎么量、多少算过）、`targets.json`（机器可读目标，`Tools~/build_targets.py` 从圣经生成）、`Tools~/measure.py`（量图）、`Tools~/regrade.py`（PPv2 引擎复核）、`Tools~/make_overview.py` + `overview_sources.json`（全片总览图）、`Tools~/thumbs.py`（陌生人测试缩略图）。
- 各包分支（10-22 20:30 巡检）：`pkg/sky` 有 shader 与接口，没有图；`pkg/sea` 接口文档；`pkg/lamps` lookdev brief；`pkg/inside` 只有 STATUS。`gate-clouds`、`clouds`、`palace`、`mirrors`、`cabin`、`engineering` 还没有分支。**还没有任何包推渲染。**
