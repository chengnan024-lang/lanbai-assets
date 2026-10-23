2026-10-23 06:30 UTC · 第 1 批审完：GateClouds 第 1 轮（v1.3）不通过 + 终审验收已推；门内、天空第 0 轮预审已推；晨 APL 的圣经矛盾写进给总导演 · 下一步：等门写“可以终审了”，开评审团审整帧 · 额度紧，等图时停下

# 美术审片 · 状态

- 分支 `pkg/review`，只改 `Review/`（例外：别人分支上的 `<包>/美术审片意见.md`）。
- 已有：`标准.md`（审什么、怎么量、多少算过）、`targets.json`（机器可读目标，`Tools~/build_targets.py` 从圣经生成）、`Tools~/measure.py`（量图）、`Tools~/regrade.py`（PPv2 引擎复核）、`Tools~/make_overview.py` + `overview_sources.json`（全片总览图）、`Tools~/thumbs.py`（陌生人测试缩略图）。
- 各包分支（10-22 20:30 巡检）：`pkg/sky` 有 shader 与接口，没有图；`pkg/sea` 接口文档；`pkg/lamps` lookdev brief；`pkg/inside` 只有 STATUS。`gate-clouds`、`clouds`、`palace`、`mirrors`、`cabin`、`engineering` 还没有分支。**还没有任何包推渲染。**
