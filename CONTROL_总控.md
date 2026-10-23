# 蓝白 · 总控（谁在做什么、共同约定）

> 写的人：云端会话「蓝白总控安排」（下面叫**总控**；10-22 起小楠叫它**总导演**，总控 = 总导演）。2026-10-22（北京）开始。
> 小楠的话：「你来作为蓝白总控安排一切」；「开 3 个子会话并行」；「你去和她（私密对话）对接」。
> 这一页是所有云端会话的**共同约定**。每个会话开工前先读这一页，再读 `Art/README_先读这个.md` 和圣经 `Art/ART_BIBLE.md` §1（总纲）。

---

## 0. 分工

**谁做什么、做到哪儿：见 `PLAN_总导演.md`（总计划与进度表，总导演每次巡检更新）。** 下面只列文件夹归属，免得互相踩。

| 会话 | 只改这些文件夹 | 分支 |
|---|---|---|
| 总导演（蓝白总控安排） | 根目录文档、`HANDOFF_LOG.md`、`Common/UdonGlobals.md`、`Common/Shaders/LanbaiVR.cginc` | `main` |
| 总导演（车厢，和别的包一样要过审） | `Cabin/` | `pkg/cabin` |
| 美术审片 | `Review/` | `pkg/review` |
| 总工程师 | `Common/Tools~/`、`Common/Shaders/LanbaiGlobals.cginc`、`Director/`、`Engineering/`、`Grading/`（维护） | `pkg/engineering` |
| 门（私密对话） | `GateClouds/`；修补时 `Gate/`、`Tear/`、`Tentacles/` | `pkg/gate-clouds` |
| 天空 | `Common/Shaders/LanbaiFog.cginc`、`Common/Shaders/LanbaiSky.cginc`、`Sky/`、`Act09_StarSea/` | `pkg/sky` |
| 云 | `Clouds_v2/`、`Act06_Dawn/`、`Act08_Dusk/` | `pkg/clouds` |
| 海 | `Sea/`、`Act07_Sea/`、`Common/Shaders/LanbaiCaustics.cginc` | `pkg/sea` |
| 宫殿 | `Palace/` | `pkg/palace` |
| 门内 | `Act04c_Inside/`、`Overlay/` | `pkg/inside` |
| 镜与白 | `Mirrors/`、`Act10_White/` | `pkg/mirrors` |
| 灯与假醒 | `Lamps/`、`Act11_FalseWake/` | `pkg/lamps` |

- **站牌套件不做**（小楠说先不做）。第 1、2、12 幕的路、车、站由本地做；圣经是美术依据。
- **第 3 幕**待定（门交了以后再定）。
- 分工表没写到的东西，写进自己文件夹的 `给总控.md`，总导演来分。
- **例外**：总导演、总工程师、美术审片可以往任何包的分支推 `<包>/总导演意见.md`、`<包>/总工程师意见.md`、`<包>/美术审片意见.md` 这三个文件（只有这三个）。**美术审片的意见和总导演的意见一样要逐条回应**（改，或者在 README 的“与评审的分歧”里写明理由）。所以每个会话**推之前先 `git pull --rebase origin <自己的分支>`**。
- Blender 迭代规矩、美是最高原则：见 `PLAN_总导演.md` 第四、五节。**每个会话都要照做。**

---

## 1. Git 协议

- 每个会话**只推自己的分支**（上表），**不推 `main`**。总控审过以后合并进 `main`，并写 `HANDOFF_LOG.md`（本地只看 `main` 和这个日志）。
- **只改自己的文件夹。** 要改别人的文件（包括 `Art/ART_BIBLE.md`、`HANDOFF_LOG.md`、`README.md`、`Common/` 里不归你的），写进 `<你的文件夹>/给总控.md`，总控来改。
- 每到一个里程碑就推一次，并更新 `<你的主文件夹>/STATUS.md`（最上面一行：日期时间、做到哪、下一步、有没有卡住）。总控靠它看进度。
- 大文件：PNG / FBX / blend 都直接提交（仓库已经这么做）；单个文件 < 95 MB。中间产物、wip、缓存**不提交**（放 `/tmp` 或 scratchpad）。
- 提交信息用英文一句话说清楚做了什么，正文可以中文。

---

## 2. 每一幕的包里要有什么（“拿来就能用”，2026-09-30 定的）

1. 模型（FBX，单位米，导出设置沿用 `Tentacles/Source/lib/export_unity.py`）、贴图、shader（+ `.cginc`）。
2. **布局**：JSON（唯一的数据源）+ 空物体 FBX；时间曲线全部是时间轴秒 t 的确定函数，绑 `FromLocal/cues.json` 的标签。
3. **Unity 编辑器脚本**：菜单 `蓝白/Build/<幕>`，点一下按圣经把这一幕搭起来（可重复运行、先删上一次搭的）；导入设置用 `AssetPostprocessor`，**只管自己的文件夹**。
4. **运行时驱动**（UdonSharp）：见 §5 的接口。
5. **参考渲染**：云端渲的“应该长这样”，从固定机位（主座位眼位，桌面 1920×1080、水平 90°），**按圣经的 PPv2 模拟调色**（`Grading/Tools~/engine/ppv2_engine.py`），附量出的数（APL、最亮点位置、紫占比、爬升律）。能做 numpy 版 shader 移植就做（门的做法），这样参考图和 Unity 用的是同一套数学。
6. **中文 README**：先写“拷哪些文件夹、点哪个菜单、在哪一秒从哪个机位截图推回来”，再写细节；末尾写**诚实的已知弱点**。
7. **检查**：一律用 main 上的 **`Common/Tools~/compile_check/`**（总工程师的 v1：DXC + Unity 2022.3.22f1 的 CGIncludes 原件、变体、surface shader、SPS-I / 雾 / `_Udon_` / include 的 lint，C# 用 Roslyn；门测试里本地撞上的两个真错误都能复现）。先读它的 `README_compile_check.md`。写明“没在 Unity 里编译过”。
8. **评审**：每个包交之前至少一轮独立的**美术评审 + 技术评审**（另开 agent，只给它圣经、渲染和代码，不给你的结论），改完再审，直到两份都“通过”。评审稿放 `<文件夹>/Docs~/`。

质量第一，慢慢做（小楠：「还是不要节省不要将就啦」）。

---

## 3. 共同约定（数值和坐标）

- **坐标**：Unity 世界，米，Y 上。**车固定在原点、车头朝 +Z，世界往车后移（跑步机）。** 车厢地板 y = 0.62；主座位眼位见 `Gate/GateLayout_v2.json` 的 `cameras.U7`（约 (0.55, 1.70, 2.05)）；`LB_Journey.heroEye` 是 (0.70, 1.77, 0.20)，两者不同，**以本地最新的为准，在 README 里写清你用的哪一个**。
- **时间**：时间轴秒 t（出发 = 0）。所有时刻引用 `FromLocal/cues.json` 的标签（U0–U12、F0–F16 和子标签），不写死数字；圣经 v2.1 §2 是乐句表。圣经 v2.1 晚于本地的 `timeline_v1.md`，两者冲突时**以圣经 v2.1 为准**，并在 README 里列出差异给本地。
- **调色**：PPv2 HDR + Neutral，每幕一个 profile（`Grading/` 已经生成），永不 ACES；只让发光体 bloom。无光照资产以**场景线性**值进入调色。
- **灯光强度：Inspector 值 = 线性照度 E。** VRChat SDK 强制 `lightsUseLinearIntensity = true`（本地 9/30 查到，门测试又确认了）。**圣经 §1.5 “Built-in 灯光陷阱 1”（Inspector = E^(1/2.2)）作废**；圣经和 `calib_final` 里按 gamma 换算的 Inspector 值都要按 E 重算。
- **补光**（不投影的）一律 Render Mode = **Not Important**（进球谐，不多画一遍 ForwardAdd）。
- **雾**：只用 Exponential；所有自定义 shader 走 `LanbaiFog.cginc`（§4）；`#pragma multi_compile_fog`。
- **VR**：每个自定义 shader 用 `Common/Shaders/LanbaiVR.cginc`（SPS-I 立体宏；这是 `Rain/Shaders/` 那份较新的版本，带 `LanbaiCentreEyePos()`）。公告板朝**两眼中点**。没有 ZTest Always（遮罩球除外）。
- **include 路径**：用工程根路径，`#include "Assets/Lanbai/Common/Shaders/LanbaiVR.cginc"`。本地把每个文件夹拷到 `Assets/Lanbai/<文件夹名>/`（`Common/` → `Assets/Lanbai/Common/`）。
- **反照率纪律**（§1.6）、**VR 舒适铁律**（§1.8）、**性能预算**（§1.9）、**紫只在第 4 幕**（§1.3 第 4 条）、**每帧一个最亮点**、**什么都不碰车**：没有例外。
- **命名**：shader `Lanbai/<名>`；材质 `M_<幕>_<名>`；全局量一律 `_Udon_` 前缀并先登记（`Common/UdonGlobals.md`）。

---

## 4. 共用 include（`Common/Shaders/`）

| 文件 | 归谁 | 状态 |
|---|---|---|
| `LanbaiVR.cginc` | 总控 | ✅ 已放（= `Rain/Shaders/LanbaiVR.cginc`） |
| `LanbaiFog.cginc` | 天空 | **天空的第一件交付**：先推接口 + 能编译的最小实现，别的会话照接口写 |
| `LanbaiSky.cginc` | 天空 | 同上（`LanbaiHorizon(dir)` 等与 `Lanbai/Sky` 共用的函数） |
| `LanbaiGlobals.cginc` | 总工程师 | **所有 `_Udon_` 全局量只在这里声明一次**（每个名字单独 `#ifndef` 保护），按 `Common/UdonGlobals.md` 生成。各 shader / include 不再自己声明 `_Udon_` 量，改成 include 它（门的 `LanbaiGateSky`、天空、海、门内都要换） |
| `LanbaiCaustics.cginc` | 海 | 焦散采样 `LanbaiCabinCaustics(posWS, nWS)`；车厢从第 1 幕起就 include 它，所以放 `Common/`，不放 `Sea/` |

`LanbaiFog.cginc` 的**最小接口**（天空可以加，不能改名、不能改参数）：

```hlsl
// 线性颜色。dirWS 是单位向量（从相机指向像素）。
float3 LanbaiHorizon(float3 dirWS);                        // 该方向地平线的天空颜色 = 雾色（圣经 §1.6）
float  LanbaiFogAmount(float3 posWS, float3 camPosWS);     // 0..1，含 _FogCap 封顶与高度衰减（材质参数 _FogCap、_FogHeightFalloff）
float3 LanbaiApplyFog(float3 colLinear, float3 posWS);     // 用 LanbaiCentreEyePos()；天上的东西（_FogMode 2）不调这个
```

第 4 幕的门已经有自己的 `Gate/Shaders/LanbaiGateSky.cginc`（光雾带），**不要改它的接口**；`LanbaiFog` 在第 4 幕要和它算出同样的颜色（天空把它当作 `LanbaiFog` 的一个“幕参数组”）。

---

## 5. 运行时接口（和本地的 `LB_Journey` 怎么接）

本地已经有能跑的时间轴 `LB_Journey`（UdonSharp，代码副本在 `FromLocal/code/timeline_v1/`）：钟、幕的起点 `segStart`、运动、音频、诗、管灯、**PPv2 权重和 EXPO 公式**（`ApplyGrades`）。圣经说“现有系统能用就不要重写”，所以：

- **每个包交一个自己的驱动** `Lanbai<幕>Driver : UdonSharpBehaviour`，只写自己这一幕的全局量、根物体位置、材质参数、renderer 开关：
  ```csharp
  public void LanbaiTick(float t)       // 每帧调用一次（t = 时间轴秒）。自己判断在不在本幕的时间窗里
  public void LanbaiActivate(bool on)   // 根物体只在遮挡下（黑、白、入云、水面下）开关
  public float[] LanbaiWindow()         // {开始 t, 结束 t}：需要每帧调用的时间窗（含提前预热）
  ```
- 总控做一个很薄的分发层 `Director/LanbaiActDispatcher.cs`，由 `LB_Journey` 每帧调用一次，按时间窗把 t 发给各个驱动。**不要改 `LB_Journey`**；需要它多给什么，写进 `给总控.md`。
- 驱动在 `Start()` 里写好 MaterialPropertyBlock 和全局量（**进 Play 时编辑器写的 MPB / 全局量会丢**，门测试的教训）。
- 先确认 Udon 白名单：`Renderer.GetPropertyBlock`、`VRCShader.SetGlobal*`（必须 `_Udon_` 前缀）、`PostProcessVolume.weight`。不确定的写退路。

---

## 6. 门在 Unity 里实测踩过的坑（2026-10-08 本地的 `FromLocal/gate_test/README_说明.md`，每个人都要避开）

1. **HLSL 里变量要先声明再用**：`_CloudTopY` 声明在用它的函数后面，slang 不报错，Unity 的 d3d11 编译报错。
2. **ShaderLab 的 `[Header(...)]` 里不能有冒号、括号、逗号**（冒号是语法错误，括号逗号让标题画不出来）。
3. ForwardAdd 的 POINT 变体里出现了**真的除零**（TentacleSway）。不需要的 pass / 变体就别写，写了就保证有意义。
4. **LODGroup**：Unity 的 FBX 导入器只在 FBX **根**上建一个 LODGroup，不会给每个实例的 `<id>_LOD0/1/2` 分组 → 搭建脚本自己建。
5. FBX 里只有一个根空物体时，Unity 把它**并进模型根**（改名成文件名）。
6. 一个 renderer 上的两个材质**不能分开关** → 需要分开淡出 / 关掉的部件做成两个物体。
7. **灯的 Inspector 值 = E**（§3）。门的补光多亮了 2.2 倍就是这个原因。
8. **Vertex Compression**：TexCoord0–3 的压缩要关（触手摆动靠 UV2 的浮点）。所有依赖 UV 精度的包都在 README 里写明。
9. 编辑器里写的 MPB / 全局量**进 Play 就丢**，正式版由驱动在 `Start()` 写。
10. 截图要渲进 **ARGBHalf** 再过 PPv2 再转 8 位，否则 HDR 在调色前被夹到 1（本地的小助手截图以前都有这个问题，本地在修）。
11. U# 1.x 只编译有程序资产（`.asset`）的脚本 → 每个 U# 脚本要有程序资产；搭建脚本可以顺手建。
12. 本地环境：**Unity 2022.3.22f1、VRChat SDK Worlds 3.10.5、PPv2 3.4.0、UdonSharp（SDK 自带）**，RTX 4060 Laptop。以前的 C# 检查对的是 Unity 2021.1 的引用程序集，有差别时以 2022.3 为准。
13. JSON 里没给的值，本地会**自己推**并写进报告（门测试里推了光束宽度、平铺、补光方向等）。所以：**本地需要的每一个数都要写进 JSON 或 README**，不要只存在渲染脚本里。

---

## 7. 审片与合并（总控怎么做）

- 子会话每推一次，总控读 `STATUS.md`、看渲染和量出的数、抽查代码；有意见写进该文件夹的 `总控意见.md` 推到你的分支（或发消息），你改完再推。
- 一幕的包过了，总控合并进 `main`，在 `HANDOFF_LOG.md` 写一条给本地：拷什么、点什么、在哪一秒截什么图推回来。
- 本地推回 `FromLocal/<幕>_test/` 以后，总控把对照意见转给做这一幕的会话。
