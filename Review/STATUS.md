2026-10-23 01:40 UTC · 门的练习审片写完（有条件通过：3 条阻断、13 条次要；评审团 4 视角 + 11 张陌生人测试 + 10 条阻断各一个反驳者）；GateClouds 第 0 轮预审已推到 pkg/gate-clouds（云海轮廓梳齿）；给总导演 5 件事 · 下一步：等 GateClouds 整帧预览与门内 4c 设计稿，一到就开正式审片 · 没有卡住

# 美术审片 · 状态

- 分支 `pkg/review`，只改 `Review/`（例外：别人分支上的 `<包>/美术审片意见.md`）。
- 已有：`标准.md`（审什么、怎么量、多少算过）、`targets.json`（机器可读目标，`Tools~/build_targets.py` 从圣经生成）、`Tools~/measure.py`（量图）、`Tools~/regrade.py`（PPv2 引擎复核）、`Tools~/make_overview.py` + `overview_sources.json`（全片总览图）、`Tools~/thumbs.py`（陌生人测试缩略图）。
- 各包分支（10-22 20:30 巡检）：`pkg/sky` 有 shader 与接口，没有图；`pkg/sea` 接口文档；`pkg/lamps` lookdev brief；`pkg/inside` 只有 STATUS。`gate-clouds`、`clouds`、`palace`、`mirrors`、`cabin`、`engineering` 还没有分支。**还没有任何包推渲染。**
