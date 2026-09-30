# 云卡 v1 导入 Unity 的检查（r0099，2026-09-30）

- 24 张贴图进了 `dream/Assets/Lanbai/Delivered/Clouds_v1/`，按 `Clouds/README_Clouds.md` §2 设了导入：Default、sRGB、Alpha Is Transparency、Clamp、Trilinear、Aniso 2、mip、PC **BC7**、方卡 1024 / 宽卡和条带 2048。
- 每张一个材质（`Delivered/Clouds_v1/Materials/LBC_<卡>_<预设>.mat`）：`Particles/Standard Unlit`，Fade、Multiply、白色原样；软粒子（条带 100 m、远景卡 50 m、近景卡 2 m）+ 近处淡出 1–4 m；Render Queue：条带 2980、远景卡 2990、近景卡 3000（README §3、§4）。
- 检查板：每套预设的 8 张卡放在 README §6 自检用的两种天（线性 0.80/0.87/0.96 和 0.015/0.02/0.04）前面，**关掉后处理和雾**看原样，1920×1080。边缘没有黑边白边，alpha、颜色和你们的 ContactSheet 一致。晨卡的阴影面偏薰衣草（你们已经知道，v2 按选定的 HDRI 重打光）。
- **还没摆进场景**：圣经 §1.6 要求 v2 之前用 inverse-Neutral 的 `Lanbai/UnlitCardHDR`（还没收到），而且 v2 要等 HDRI 选定后重出（候选在 `FromLocal/hdri/`）。布局按你们的布局 JSON 来。
- 顺带：`Art/tools/lens_tech/shaders/` 的 `Lanbai/Overlay` 和 `Lanbai/PointSprites` 复制进了 `Delivered/lens_tech/`，**Unity 2022.3.22 编译通过**（没有错误和警告，isSupported = true）。
