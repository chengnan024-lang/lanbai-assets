2026-10-23 13:50 UTC · 第 1、2 步完成：简报 + 视窗几何 + 白模，主座位 15/15 目标看得见（里尔克按 D-04 挪到 +12°）。下一步：完整的车（做旧、贴图、UV1、LOD、Station）。卡点：门角度 / 晨日 / 里尔克要总导演定（给总控.md 第 1、2 条），不挡后面的活。

# 车 · 状态

- `Docs~/lookdev_brief.md`：考据 + 视窗解（第 1 步）
- `Source/bus_spec.py`（唯一数据源）、`Source/build_bus.py`（Blender 5.0.1 造车 + 导 FBX）、`Source/viewcheck.py`（0.5° 射线视窗图）
- `Docs~/viewcheck/hero_map.png`、`rear_L3_map.png`：视窗图；`Docs~/iterations/01_*`：白模的标准台渲染
- 重跑：`~/bpy/bin/python Bus/Source/viewcheck.py --out Bus/Docs~/viewcheck`
