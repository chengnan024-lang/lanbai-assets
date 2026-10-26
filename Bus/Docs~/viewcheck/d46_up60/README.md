# D-46：主座位抬头 60° 看侵蚀（改前 / 改后）

**没有在 Unity 里编译、运行过。** 这是 Blender（Cycles CPU + OSL）的图，用来看侵蚀开在哪里、多大；颜色和光不是成片。

- `up60_sheet.png`：上一行是 D-46 以前的侵蚀场，下一行是 D-46（`LanbaiZenithTerm`），380 / 387 / 446 / 506 s。橙色细线是天顶 20° 那一圈。每格标了 `snell_check.py` 量的数（`../snell_hero_before_d46.json`、`../snell_hero.json`）。
- `up60_387_d46.png`、`up60_446_d46.png`、`up60_506_d46.png`：D-46 的单张。
- 机位：标准台的 `hero_up60`（眼 (0.55, 1.70, 2.05)、正前、抬头 60°、水平 90°）。
- 车：`Bus/Source/build_bus.build()` 现搭（管灯 A2）。窗外是水下的斯涅尔窗：仰角 ≥ 41.4° 是亮的天，外面是深水。玻璃全透明。不透明件只有底色 + 一层平的环境光（7a 的 `#6186A7` × 0.6）。
- 侵蚀用 `src/erode.osl` 算：一行一行照抄 `Cabin/Shaders/LanbaiCabinCommon.cginc` 的 `LanbaiCabinErodeField`（含 `LanbaiZenithTerm`、座位球、地板保留块、门组、D-26 地洞），常数是 `LanbaiCabin.shader` 的默认值。
- 对拍（`parity.json`）：水平面上 36 万个像素中心，OSL 和 `Cabin/Tools~/cabin_numpy.py` 的 `erode_field` 比 `s < 0`：387 s 1 个像素不一样（在边上），506 s 0 个；座椅高度 fade 0.25 全一样。另一个子任务用别的点（顶棚附近和低处各 100 万个）又核了一遍，符号 0 个不一样。
- 重跑：`src/` 里的 `parity.py`、`render_up60.py`、`sheet.py`（`~/bpy/bin/python`；`erode.osl` 由 Blender 自带的 OSL 编译器编到 `/tmp/bus/d46/erode.oso`，图也出到那里）。
