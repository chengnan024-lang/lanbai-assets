# 全片账本（性能 · 透明叠绘 · 显存 · 下载 · 粒子 · Udon · 全局量）

维护：总工程师。每个包推上来就更新。数据在 `ledger_data.json`（每一项都有出处），表由 `ledger.py` 生成（下面 AUTO 那一段），全局量对账由 `globals_scan.py` 生成（`globals_report.md`）。

```bash
~/bpy/bin/python Engineering/ledgers/ledger.py           # 重算下面的表和时间线图
python3 Engineering/ledgers/globals_scan.py --fetch      # 扫 main + 所有包分支的 _Udon_ 名字，对照登记表
```

**上限（圣经 §1.9，参考机 RTX 3060 级、Index 100% / Quest 2 Link 1.0×，约 9 MP @ 90 Hz）**：世界 ≤ 5.3 ms 持续（峰值 ≤ 6.3 ms、≤ 5 秒；含常开阴影平行光约 1.0 ms）；PPv2 ≤ 1.2 ms；透明 ≤ 4 FSE 持续、≤ 7 峰值（车厢玻璃 0.7 每幕都算）；任一像素 ≤ 8 层；每幕粒子 ≤ 5 000（≤ 8 个系统）；Udon ≤ 0.4 ms；显存 ≤ 700 MB；下载 ≤ 250 MB。热点：第 4 幕 ≈ 7.1 ms、第 7b 宫殿 ≈ 6.4 ms（圣经自己写的，已经超过 5.3 的持续上限，按“热点预算”单列）。

## 一、怎么算的

### 1.1 GPU 时间的标定（第一个真实标定点：门，`FromLocal/gate_test/perf.txt`）

本地 2026-10-08 在 RTX 4060 Laptop 上实测（编辑模式、`Camera.Render()` 进 ARGBHalf、含 PPv2；前后各读 1 像素同步；合计 = CPU 提交 + 等 GPU，不重叠，偏保守）：

| | 像素 | 合计 | CPU | → GPU |
|---|---|---|---|---|
| 桌面 1920×1080，U7 | 2.07 MP | 4.8 ms | 1.1 | **3.7** |
| VR 估算：两只眼各渲一遍 1832×1920 | 7.03 MP | 10.3 ms | 2.2 | **8.1** |

两点拆成 “每遍几何 G + 每百万像素填充 F”：G ≈ **3.2 ms / 遍**，F ≈ **0.24 ms / MP**。几何占大头，和 Play 里读到的 87.7 万三角、206 draw（单遍 27.9 万三角的约 3 倍：基础 + 补光的 ForwardAdd + 深度）对得上。

换到圣经的参考条件（9.03 MP = Index 100% 2016×2240×2；SPS-I 下顶点着色仍然每只眼一次，所以几何仍按 2 遍算）：

- RTX 4060 Laptop：2 × 3.2 + 9.03 × 0.24 ≈ **8.6 ms**（全按填充缩放的另一种算法：8.1 × 9.03 / 7.03 ≈ 10.4 ms）
- RTX 3060（台式）大约比 4060 Laptop 慢 10–25%：**≈ 9.5–11 ms**

对照圣经第 4 幕的热点预算 7.1 + 1.2 = 8.3 ms：**门在还没有云海、没有车厢玻璃、没有车的时候，估计已经超了 15–35%。** 但这两个数的不确定性很大（编辑模式、MSAA 4×、像素光 8、4 级阴影、补光当时是 Important、同步读回的开销、只有两个点），所以账本里第 4 幕先按这个估计记、标成“标定估计”，同时请本地按 §3 的协议再测一次。这件事写进了 `Engineering/给总导演.md`。

### 1.2 别的包

没有实测之前，每一项按三种来源之一记（`status`）：`bible`（圣经写的数）、`package`（包自己的 README 报的数）、`engineer-estimate`（总工程师按着色复杂度 × 覆盖像素估的，写明算法）。实测来了就换成 `measured`。

### 1.3 透明叠绘 FSE

FSE（全屏等效）= 这一层在画面里覆盖的像素数 ÷ 全屏像素数，按层加。每个包按自己的透明层在主座位机位、关键时刻算（门的 `gate_fse.py` 是范例：每层渲一张覆盖掩码，数像素），报给总工程师。车厢玻璃 0.7 每一幕都算。

### 1.4 显存 / 下载

贴图：宽 × 高 × 每像素字节（BC7 / BC6H / DXT5 = 1、DXT1 = 0.5、RGBA32 = 4、RGBAHalf = 8）× 1.33（mip）。下载：Crunch 的 DXT 约 ÷ 3–5，BC7 / BC6H 不 crunch 按 LZ4 约 ÷ 1.3。网格：顶点数 × 顶点字节。音频：Vorbis 0.5 按文件长度。包的 README 要列每张贴图的尺寸和格式。

## 二、表（自动生成）

<!-- AUTO:BEGIN --><!-- AUTO:END -->

## 三、请本地测的（性能协议，给 HANDOFF 用）

1. **Play 模式**、真的 VR（SteamVR，Index 100% 或同等像素），不是编辑模式的 `Camera.Render()`。
2. 记 GPU 帧时间（SteamVR 的 Frame Timing 或 Unity Profiler 的 GPU 模块），每个机位 10 秒取中位数和 95 分位。
3. Frame Debugger 里数：深度预渲染、阴影、主 pass、ForwardAdd、透明、PPv2 各几个 draw；GPU Profiler 里最贵的 10 项。
4. 和这次对比：补光改 Not Important 前后各一次（圣经 / CONTROL §3 的要求）。
5. 记下 QualitySettings（像素光数、阴影距离、级联、MSAA、LOD Bias），VRChat 客户端会覆盖其中几项，**按 VRChat 的“高”画质设一遍再测**。
