# §1.7 中性 LUT 验证 —— 通过

**结论：contribution 0 和 1 两张图除了会动的东西（雨丝、玻璃上的雨滴）以外逐像素一致，没有系统性偏移。条带方向、sRGB、压缩、Aniso 都是对的，LanbaiGradeBuilder 生成的 LUT 可以直接用这套导入设置。**

## 怎么测的（本地 r0092，2026-09-30 17:04）

- 条带：`Art/luts/Lanbai_Neutral_1024x32.png` 原样复制到 `dream/Assets/Lanbai/Grades/LUT/`。
- 导入设置（`LB_GradeTest.FixStripImport` 改的）：Default、sRGB **关**、无 mip、Clamp、Bilinear、Aniso 0、不压缩（RGB24）、NPOT None、Max 2048。
  - Unity 默认导入是 sRGB 开、mip 开、Repeat、Aniso 1、压缩、ToNearest，**全都要改**——GradeBuilder 生成 LUT 时请照这个设（或者调 `LB_GradeTest.FixStripImport(path)`）。
- 测试 volume：全局 PostProcessVolume，priority 10000，layer = 4（Water，现在的 LAYER_PP），ColorGrading = **LDR** 模式、Lookup Texture = 中性条带，其余调色参数全中性。
- 同一帧附近各拍一张 contribution 0 / 1（1920×1080，跟帧渲染），两个机位：站牌（夜 + 雨 + 路灯）、车厢（灯管 + 车窗外的雨）。

## 数字（c1 − c0，8-bit 码值）

| 机位 | 平均偏差 R/G/B | 8×8 块均值 \|d\| 中位数 | 8×8 块 p95 | 逐像素 \|d\|≤2 |
|---|---|---|---|---|
| 站牌 | −0.16 / −0.16 / −0.14 | 0.33 | 2.0 | 84% |
| 车厢 | +0.08 / +0.06 / −0.02 | 0.27 | 3.7 | 82% |

按亮度分段（0–16、16–48、48–96、96–160、160–255），每段的平均偏差都在 ±0.6 码以内。
错一项会是什么样：sRGB 开着读条带，中灰会整体偏几十码；条带方向反了颜色会串；压缩了会有色阶。这里都没有。

剩下的 \|d\| 全在会动的地方（见 `lut_pair_*.jpg` 第三格，差值 ×8）：挡风玻璃外的雨丝、车门口的雨、侧窗玻璃上的雨滴。静止的车厢内饰、座椅、灯管都是黑的（完全一样）。PPv2 3.4.0 的 dithering 一直开着，也会贡献 ±1 码的噪声。

## 文件

- `lut_pair_stop.jpg`、`lut_pair_cabin.jpg`：contribution 0 | contribution 1 | \|差\|×8（每格缩到 960×540）。
- 原图（1920×1080）在本地 `dream/LanbaiRemote/shots/r0092/`，要的话再推。
