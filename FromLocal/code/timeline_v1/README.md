# 时间线 v1 的代码（只读参考，给 Director 对接用）

从 `dream/Assets/Lanbai/` 复制过来的（2026-09-30），Unity 里跑的是那边的版本。
- `LB_Journey.cs`：UdonSharp 时间轴（钟、幕、运动、音频、诗、管灯、占位的天空 / 海 / 门 / 后处理）。
- `LB_Cues.cs`：由 `FromLocal/cues.json` + `Art/tools/lens_tech/out/FlickerTable.cs` 生成（`tools/gen_cues.py`）。
- `LB_Udon.cs`：把数据填进 LB_Journey（幕的起点、运动参数、诗的表、天空参数表）。
- `LB_JourneyQA.cs`：编辑器里读一帧状态的检查工具。
说明见 `../../timeline_v1.md`。
