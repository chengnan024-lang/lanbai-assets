# 触手之门 · Unity 导入测试（gate_test）

写的人：本地会话（世界创建），2026-10-08（北京）。对象：云端（小克）。
依据：`HANDOFF_LOG.md` 10-07 / 10-02 三条、`Art/README_先读这个.md`、`Gate/README_GateLayout.md`、`Tear/README_Tear.md`、`Tentacles/README_Tentacles.md`、`Grading/README_Grading.md`。
仓库版本：`29fa6f2`。Unity 2022.3.22f1、VRChat SDK Worlds 3.10.5、PPv2 3.4.0、UdonSharp（SDK 自带）。显卡 RTX 4060 Laptop，CPU i9-13980HX。

**只在测试场景 `Assets/Lanbai/Tests/GateTest.unity` 里做的。主场景、时间轴和现有系统都没改。** 模型、贴图没换，颜色、雾、光的数值也没调：对不上的地方照实截图，写在 §4。

---

## 0. 这个文件夹里有什么

| 文件 | 是什么 |
|---|---|
| `U7_unity_t155.10.png` | **主座位 U7**：t = 155.10，1920×1080，水平视角 90°（竖直 58.72°），眼位 (0.55, 1.70, 2.05) 正前。2× 超采样。 |
| `U7_engelein.png` | 云端定稿（`Gate/Renders/` 原样拷过来），放在旁边对比。 |
| `U7_compare_side_by_side.png` | 左边 Unity，右边定稿。 |
| `keyart_unity_t155.10.png` | **keyart 机位**：时间按这次的要求定在 t = 155.10。2560×1072，水平视角 82°（竖直 40.00°），右 6°、仰 7°。 |
| `keyart_unity_t154.50.png` | 同一个机位，时间用 JSON 里 keyart 自己的 t = 154.50（U7b − 0.6），和 `keyart_239.png` 是同一时刻。 |
| `keyart_compare_t154.50.png`、`keyart_compare_t155.10.png` | 上面 Unity，下面 `Gate/Renders/keyart_239.png`。 |
| `metrics_unity_vs_render.json` | 用 `gate_metrics.py` 的定义量的数：APL = sRGB 亮度（Rec.709）的平均，0–255。 |
| `perf.txt` | 帧时间、draw call、三角面（§3）。 |
| `console_errors_warnings.txt` | 这次测试期间 Console 里的**全部**报错和警告，原样（5 217 条：错误 5 184、警告 33，分类见 §5）。 |
| `console_full.txt` | 同一段时间 Console 的全部输出，原样。 |
| `shader_fixes.diff` | 两个 shader 为了能编译过做的最小修改（§2.1）。 |
| `reports/` | 导入脚本的搭建报告和核对报告（`GateTest_Build.txt`、`GateTest_Verify.txt`），调色套件自己出的 `GradeBuild_Report.md`、`GradeValidate_Report.md`。 |
| `code/` | 导入脚本（`LB_GateImport.cs` 管导入设置，`LB_GateTest*.cs` 管搭建、定时间、截图、量性能）。 |

---

## 1. 照做了的

1. **仓库**：pull 到 `29fa6f2`。VM 上 git 删不了锁文件，合并卡在一半：新文件写进去了，HEAD 没动，四个改过的文件还是旧的。我用 `git show` 补齐了这四个文件，再挪 HEAD，工作区干净。读了 HANDOFF 最上面四条和 `Art/README_先读这个.md`。
2. **测试场景**：`Assets/Lanbai/Tests/GateTest.unity`，从空场景建。里面只有一台 `ReferenceCamera`（没有 VRC 场景描述符，也没加进 Build Settings）。
3. **调色**：整个 `Grading/` 拷进 `Assets/Lanbai/Grading/`。编译**一次通过**：`Lanbai.Grading.Editor.dll` 和 `Assembly-CSharp.dll`（含 `LanbaiExposure.cs`）都没有错误和警告。U# 编译见 §2.4。
   - 跑了 `蓝白/Grades/Build Profiles & Volumes`（就是 `LanbaiGradeBuilder.BuildAll()`，远程调用的）：21 个 profile、21 个 volume，route A，1 个警告（"no VRC scene descriptor ReferenceCamera"：测试场景故意不放描述符）。
   - 新建了 `PostProcessing` 层（第 22 层）。这是套件自己建的。
   - 套件说明第 2 步要配参考相机。我选中 `ReferenceCamera` 后跑了 `Configure Reference Camera`：HDR、near 0.05、far 45 000、Skybox，PostProcessLayer 只看 `PostProcessing` 层，AA 关，Stop NaN 开，Directly to Camera Target 关。
   - 开了 `Debug Window`，Solo **S4**（场景调色只有 S4 = 1，助手都是 0）。镜头层 LENS_CLEAN 保持套件的初始值 1，所以桌面截图上有暗角和颗粒。
4. **门**：拷进项目的只有 README §0 列出的文件：
   - `Assets/Lanbai/Gate/`：JSON、4 个 FBX、`Shaders/`、`Textures/`
   - `Assets/Lanbai/Tentacles/`：`FBX/`、`Textures/`
   - `Assets/Lanbai/Tear/`：`FBX/`、`Textures/`、`Lanbai_Tear.shader`、`LanbaiTearParams.cs`、`Tear_Layout.json`
   - 外加 `LanbaiVR.cginc`：照 README_Tear 的要求，从 `Delivered/lens_tech/` 拷了一份放在 Tear shader 旁边。

   导入脚本 `LB_GateTest.Build("155.1")` 全部照 `GateLayout_v2.json` 搭：
   - **GateRoot**：位置按 §2 的公式（h_bus、v_g）。t = 155.10 时在 (0, 92.12, 1442.95)，云顶 y = −57.88。和 JSON 的 `samples_every_0_5_s` 核对过：z / y / H / 张开的误差 ≤ 0.05。
   - **64 个实例**：
     - 28 条单独的臂来自 `GateArms_v4.fbx`，36 条群臂来自 `GateMultitude_v2.fbx`（按 `variant` 取姿态网格）。
     - 位姿由 `anim` 现算（rise ss / trap / beta → lean → track → close，近处 3 条加 drift）。在 155.10 和 JSON 的 `position_U7b` / `rotation_U7b_xyzw` 核对过：位置最大差 0.21 m（是还在升的群臂，JSON 只保留了两位小数），转角最大差 1e-4°。
     - `GateLayout_v2.fbx` 里 61 个空物体（近处 3 条不在 GateRoot 下）的终态位置和 JSON 的 `position` 最大差 7 mm，转角差 0.00°。
   - **材质参数**：
     - 每条单独的臂一个材质，JSON 的 `material` 块逐个键照抄（按 shader 里声明的类型写；JSON 里的键 shader 全都有）。群臂按 `material_name` 用档材质，这一版只有 B / C 两档有成员，A 档没有，和 README 一致。
     - `_Phase`、`_FogCapI`、`_RevealGroup`、`_Reveal` 照 §2.1 写进**每个 LOD renderer 自己的** MaterialPropertyBlock。
     - 群臂的显现走全局 `_Udon_MultReveal`，单独的臂按各自的 `reveal` 关键帧。t = 155.10 时 56 条显现，后窗 8 条是 0、renderer 关着。
     - 贴图：皮肤共用 `Tentacles/Textures` 的四张，遮罩按 `texture_variant`：自定义的臂用 `T_Gate_<key>_Occlusion`，近处 3 条用库里的 C / D。
   - **远潮**：`TentacleTide_v2.fbx` 挂在 GateRoot 下，本地单位变换，2 个子网格按 FBX 里的材质名分配（M_TentacleTide_A / B → v3 图集 A / B）。`_Reveal` 按 `tide.reveal` 取值，155.10 时是 1。
   - **裂口**：`Tear_Root` 挂在 GateRoot 下，(0, −150, 0)、(0, 180, 0)，缩放 = H/1000（H 用单调 PCHIP，155.10 时 640.0 m，缩放 0.640）。
     - 张开 0.479、撕裂 0.216（JSON 的公式；README_Tear 表里写的 "~0.3" 是旧数）。
     - 材质表照 README_Tear §4 抄：Part、混合、队列、所有颜色和参数。门里的覆盖值和淡出关键帧照 JSON `tear.gate_overrides` / `tear.fades`。
     - 光晕的距离淡出 D = 1441 m → ×1，光路的 x 缩放 0.544。
     - 套件自带的 12 张光束扇关掉，换成 JSON `shafts` 的 2 束。
   - **全局量**：照 §2.1 每次 Apply 写一遍：`_Udon_CloudTop / TearPos / TearH / MoonDir / GateTime / GateOrigin / TearFoot / TearTop / MultReveal / MoonDisc`，加上 Tear 的 `_Udon_TearOpen / RipProgress / TearHide`。月盘增益按 `moon.disc_gain_keys` 是 0.6。
   - **光**：照 JSON `lights` 的 "inspector" 一栏原样填：月 #D6E4FF 1.0 软阴影；补光 #5A6488 0.52 自下而上；裂口光 #A99DE1 0.9 无阴影，只照车厢（§2.2）。
   - **天空**：`Lanbai/GateAirSky` v3，材质全用 shader 默认值（JSON 没有另给）。
   - **雾**：Exponential、0.0006、#505466（JSON `fog`）。
   - **导入设置**：照 README_GateLayout §9、README_Tentacles §4、README_Tear §4，用 `LB_GateImport.cs`（AssetPostprocessor）在第一次导入时就设好：
     - 模型：Mesh Compression 关、Read/Write 关、Generate Lightmap UVs 关、Normals Import、Tangents Mikk、相机 / 灯 / 动画 / 材质都不导入。
     - 贴图：sRGB、Wrap（遮罩 U 平铺、V 夹住）、Alpha Is Transparency、BC7 / BC5、最大尺寸、Mip Preserve Coverage 都按表设。
   - **时间与机位**：t = 155.10（U7b）。主座位用 JSON `cameras.U7`，keyart 用 `cameras.key`。

---

## 2. 改了的、自己定的（以及为什么）

### 2.1 为了编译通过的最小修改（`shader_fixes.diff`）

| 文件 | 报错（原样） | 改了什么 |
|---|---|---|
| `Gate/Shaders/Lanbai_TentacleSway.shader` | `Shader error in 'Lanbai/TentacleSway': 'CloudTop': function must return a value at line 421 (on d3d11)`、`undeclared identifier '_CloudTopY' at line 421 (on d3d11)` | `float _CloudTopY;` 原来声明在第 480 行，晚于第 421 行的 `CloudTop()`。把这一行声明挪到 `CloudTop()` 前面，原来那一行删掉。别的一个字没动。 |
| `Tear/Lanbai_Tear.shader` | `Shader error in '': Parse error: syntax error, unexpected $undefined, expecting TVAL_ID or TVAL_VARREF at line 106` | ShaderLab 的 `[Header(...)]` 里不能有冒号。第 106 行 `[Header(Flap: indigo silk)]` 和第 160 行 `[Header(Depth prepass: Lens only)]` 的冒号换成两个空格。只动了 Inspector 上的标题，不影响渲染。 |

改过以后五个 shader 都没有错误，`ShaderUtil.GetShaderMessages` 只剩两条警告，都没改：
- **TentacleSway**：`floating point division by zero`（ForwardAdd、POINT 变体的片元程序）。门里没有点光源，这个变体用不到，但它是真的除零，请看一下。
- **Tear**：`Failed to create material drawer Header with arguments 'Own attenuation (sky object, optional)'`。第 99 行 Header 里的括号和逗号让标题画不出来。只是警告，不影响编译和渲染。

**C#：一个都没改。** Grading 的三个 Editor 脚本、`LanbaiExposure.cs`、`LanbaiTearParams.cs` 都一次编译通过。

### 2.2 搭的时候自己定的（数据里没写，或者写的和 Unity 的实际做法对不上）

1. **LODGroup 是导入脚本建的。** README 写"导入器自动建 LODGroup"，但 Unity 的导入器只在 FBX 的**根**上建一个：`GateArms_v4` 一个组管 84 个网格，`GateMultitude_v2` 一个组管 36 个。每个实例自己的 `<id>_LOD0/1/2` 并没有分组。所以我按名字给 64 个实例各建了一个，阈值照 §9：0.25 / 0.06 / 0.005。项目的 LOD Bias 是 2.0（VRC High），实际切换会比阈值晚。
2. **Tear_Root 就是 `Tear_Kit.fbx` 的根。** FBX 里只有一个根空物体时，Unity 会把它并进模型根（名字变成 `Tear_Kit`），12 个网格直接挂在根下面。我按这个根来挂，位置和缩放照 JSON。
3. **CloudGlow 拆成两个物体。** README 写的是"同一网格两个材质"，但 JSON 要求叠加那一层淡到 0 时**单独关掉 renderer**，一个 renderer 上的两个材质做不到这一点。所以加了 `Tear_CloudGlow_Additive`，和原物体共用同一个网格，放叠加材质。原物体放相乘的那个（`_Lit`）。队列 2988 / 2989 不变。
4. **光池的 `_LanesTex` 两层都挂了。** README_Tear §4 的表只在叠加那一层写了 `_LanesTex`。但 JSON `clouds.pool` 写的是光池的权重整体 × `Tear_CloudLanes`，两层都乘，我按 JSON 来。
5. **贴图平铺和 `_VariantDims`。** JSON 的材质块里没有这两项，我按 README / 渲染脚本的规则从网格量：
   - 根半径 = 根部那一圈顶点到中心的距离 ÷ UV2.x，取中位数。
   - 主贴图平铺 = clamp(R·缩放/25, 1, 3)，细节法线 = (4, 4.6) × clamp(R·缩放/4, 1, 16)（`arms4.skin_tiling`）。群臂固定 (1, 4)。
   - `_Colossus` = 1 给 PR / PL / ENG / C1 / C2 / BG*（`arms4.COLOSSUS_KEYS`）。
   - 近处 3 条是库里的变体，用 README_Tentacles 的表（C 1.35 / 61.8，D 2.00 / 72）。网格量出来的是 1.72 / 1.30 / 1.92（表里是 2.00 / 1.35 / 2.00），差 4–14 %，可以当作这种量法的误差。
   - 群臂 12 个姿态共用档材质，所以每个实例的 `_VariantDims` 和它那个姿态的 `_OcclusionMap` 走 MPB。
   - 每条的数在 `reports/GateTest_Build.txt`。**这些都是我推出来的，请核对。**
6. **光束的宽度。** `Tear_ShaftCard` 是等宽的（半宽烘在 UV2.x = 40）。我把横截面缩放成 `half_width_m / 40`，长度缩放成 `length_m`，`_Intensity = 0.35 × gain`。JSON 的 `widen 3.2`（越远越宽）这张卡和 shader 都做不到，所以远端比定稿窄。
7. **补光方向。** JSON 只写了 `from_below: true`，没有方位，我取正下方往上照。
8. **裂口平行光。** JSON 写的是"只照车厢层"，测试场景里没有车，Culling Mask 设成 Nothing。方向照 JSON，每次 Apply 时从 `_Udon_TearPos` 指向车。
9. **灯光强度照 "inspector" 一栏原样填，没有换算。** 但 VRChat SDK 强制 `lightsUseLinearIntensity = true`（Verify 报告里查过，§1.5 那件事），所以按 E 算：
   - 补光实际是 0.52，不是 0.24（×2.2）；
   - 裂口光实际是 0.9，不是 0.8；
   - 月光 1.0 = 1.0，不受影响。
10. **远潮的雾带参数和臂不一样，我没动。** `Lanbai_TentacleTide_v2.shader` 是 v2.2，没有接 `LanbaiGateSky.cginc`，属性头上写着 "same values as the tentacle materials and the sky"，但它的默认值是旧的：
    - `_HazeNear` (0.0648, 0.0742, 0.1248)：未乘 0.8 的屏幕值；臂和天空用的是 (0.1085, 0.1130, 0.1641)。
    - `_BandEl` (12, 34, 5)：臂和天空是 (6, 22, 2)。

    JSON 也没给远潮的材质值，我就用 shader 默认值，没自己填。这需要云端定一下。
11. **`_SkyCloud`（脚前云头的颜色）。** 用的是 README 里渲染的 U7 值 (0.060, 0.066, 0.082)。Unity 里没有 CloudSea 卡可以抄。
12. **环境光。** JSON 没写，用新场景的默认值（天空盒环境光，强度 1），搭完调了一次 `DynamicGI.UpdateEnvironment()`。
13. **keyart 拍了两个时刻。** 这次要求时间定在 155.10，但 keyart 机位在 JSON 里自己的 t 是 154.50（定稿 `keyart_239.png` 就是 154.50），所以两张都拍了。
14. **截图渲进 HDR 目标再转 8 位。** 第一版截图渲进的是 8 位 sRGB 目标：场景的 HDR 值在进 PPv2 之前就被夹到 1，裂口的白被压成一块平的灰（L\* 最高只有 76）。改成渲进 ARGBHalf、PPv2 输出以后再转 sRGB，裂口的热核和 bloom 就出来了（L\* 99.5）。
    - **顺带发现**：本地远程小助手的截图（`LB_Remote` 的 shots）和 `LB_PerfCheck` 都渲进 8 位目标，以前的截图和帧时间都有这个问题。按"现有系统先不动"，这次没改它们。我自己会修。
15. **没改 Vertex Compression。** README_Tentacles §4 要求取消勾选 TexCoord0（TexCoord1/2/3 也不勾）。项目现在是 `4054`，TexCoord0 和 TexCoord2–7 都在压缩。这是整个项目的设置，会影响主场景，所以先没改，**请小楠 / 云端定**。它对编辑器里的截图有没有影响我没验证。
16. **导入脚本加了 AssetPostprocessor。** Unity 因此把项目里的**全部**模型重新导入了一遍。脚本只管 Gate / Tentacles / Tear 三个文件夹，别的模型导入结果不变，但重导时冒出了旧模型（车、卡车、一个带表情的人物）本来就有的法线报错，见 §5。

### 2.3 没做的（不在这次的清单里，或者缺东西）

**云**：都没摆，所以地平线以下是一片平的灰雾。
- 云海（CloudSea 条带和卡）：JSON 里没有它的布局，只写了"in Unity the cloud sea is the Clouds kit"。
- 云塔 9 张、远云 4 张、雾卡 2 张、地平线云团 22 张：JSON 有位置，卡在 `Delivered/Clouds_v1` 里也有，但这次的清单没有云，而且 JSON 要的"卡在 LanbaiFog 里、yaw 公告板、下沉 / 塌陷"没有对应的 shader。要摆的话，请告诉我用哪个 shader。

**缺资产**：
- 阴影楔 4 道：JSON 有布局，但没有交付对应的 shader 或网格。
- 峡谷的 3 张卡：JSON 写了 "Tear_Foot: 3 alpha cards"，但没有交付网格。

按规矩，这两样没交付的我都没自己做。

**车相关**：车壳（U7 是 `bus_shell: true`）、天窗光斑和尘、目的地牌，这次都没放，截图里没有窗框。

**驱动**：`LanbaiExposure` 组件没加（没有 Director）。`LanbaiTearParams` 也没挂。全局量由编辑器脚本的 Apply 写。

**Play 里看**：进 Play 会重载场景，MPB 和全局量都会丢，Play 里看到的门不对。要在编辑器里看，请在编辑模式下跑一次 `LB_GateTest.Apply("155.1")`（场景视图和 Game 视图就对了）。

### 2.4 UdonSharp

U# 1.x 只编译有程序资产的脚本，所以光靠 C# 编译过，还不能说明 U# 能过。我给 `LanbaiExposure`、`LanbaiTearParams` 在 `Assets/Lanbai/Tests/UdonPrograms/` 建了程序资产，再让 U# 全部重编：**`Compile of 13 scripts finished`，没有错误**。

⚠ 中间我误调了一次打包模式的编译（`CompileAllCsPrograms(forceCompile: true, editorBuild: false)`）。编辑器里没有打包用的引用，所以每个脚本都报 `Predefined type 'System.Object' is not defined`：
- 连 VRChat 自带的 `GetComponentShim.cs`、主项目的 `LB_Journey.cs` 也一样报；
- 一共 5 171 条，都在 `console_errors_warnings.txt` 里；
- 这是调用方式错了造成的，不是脚本的问题。

随后用正常模式重编，干净。U# 重编时重写了主项目已有的程序资产（`Assets/Lanbai/UdonPrograms/*.asset`、`Assets/SerializedUdonPrograms/*`、`Assets/UdonSharp/UtilityScripts/*.asset`），内容是同样的源码重新编译的结果。Unity 同时存了一次 `ProjectSettings.asset` 和两个 SDK 包里的资产。项目没有 git，没法对比它们具体改了什么；我的代码没有改项目设置的地方。

---

## 3. 性能（`perf.txt`）

**帧时间**：编辑模式，一台相机渲进 HDR 的 RenderTexture，含 PPv2；前后各读 1 个像素做 GPU 同步；预热 4 次，取 24 次的中位数。

| | 合计 | 其中 CPU |
|---|---|---|
| 电脑 1920×1080，U7 机位 | **4.8 ms**（4.5–5.3） | 1.1 ms |
| VR 估算：两只眼 1832×1920×2，竖直视角 100°，同一方向渲两次 | **10.3 ms**（10.0–11.0） | 2.2 ms |

渲进 8 位目标时是 3.3 / 6.6 ms，那个数不对（HDR 被夹了，带宽也少一半）。

**Draw call 和三角面**：Play 里读 Game 视图那一帧，和 Stats 窗口同一个来源。UnityStats 和 ProfilerRecorder 读到的数一致。Game 视图当时是 971×436，水平视角对到 90°。

| | 数 |
|---|---|
| Draw call / Batches | **206 / 206** |
| SetPass | 204 |
| 实例化合批的 draw call | 104 |
| 三角面 | **877 435** |
| 顶点 | 469 444 |
| 投影物体 | 0（近处 3 条在 155.10 还在云下） |

按视锥 + LODGroup 规则数（每个 renderer 只算一次，不含额外 pass）：看得见的 renderer 68 个（LOD0 31、LOD1 21，其余 16 个是没有 LOD 的裂口部件），**单次三角面 279 348**。
- 大头：群臂合计 45 k，每条主臂和巨像 16.8 k（LOD0），裂口 15.6 k。
- 实测三角面大约是单次的 3 倍。我猜是三份：基础 pass、第二盏平行光（补光）的 ForwardAdd、深度贴图。**没验证。** 想关掉补光再测一次对照，但当时 Unity 窗口没在出帧，读不到数。

---

## 4. 对上的、对不上的（照实写，数值都没动）

### 量出来的数（`metrics_unity_vs_render.json`）

| | Unity U7 | 定稿 U7 | Unity keyart 154.50 | 定稿 keyart |
|---|---|---|---|---|
| APL | 35.1（没有车壳） | 26.4（有车壳；README：透过玻璃 36.8） | 37.8 | 35.2 |
| 亮度 < 12 的像素 | 24.8 % | 29.1 % | 26.0 % | 26.4 % |
| 上 25 % 的 L\* p90 | 5.4 | 9.0 | 4.3 | 3.8 |
| L\* > 85 的像素 | 0.65 % | 0.59 % | 1.06 % | 1.06 % |
| 最亮 2000 像素的外框 | (970, 365)–(1003, 461) | (970, 364)–(1003, 461) | (1151, 475)–(1182, 586) | (1149, 473)–(1268, 587) |

### 对上的

- **构图几乎重合**：裂口的位置和大小、两根鞭梢交叉成 X、Engel 盘住右唇、左右手的盘绕、巨像 2 盖住月亮（月晕在它左边）、右门柱、左右两侧的群臂、背景巨物。
- **最亮的 2000 像素全在裂口里**，U7 的外框和定稿一个像素都不差。
- 裂口有热核、有 bloom，L\* 最高 99.5。一帧只有一个最亮点。

### 对不上的（请云端判断）

1. **没有云海、云塔、远云**（§2.3）。地平线以下是平的灰雾，下 45 % 的 APL 比定稿亮：keyart 49.6 对 47.6，U7 42.3 对 26.7（U7 那一项里定稿还有车壳）。
   - 定稿里云塔挡住的群臂，在 Unity 里整条露着，看起来比定稿多、比定稿清楚。
2. **脚前云头 `Tear_FootSkyline` 读成一个暗的小土包**，坐在灰雾上。它后面本来应该是云海，现在没有可以接的东西。光池和光路在脚下两侧各拉出一条蓝色的横线，也是同一个原因（底下没有云卡可以照）。
3. **天上有星星。** GateAirSky 自带稀疏的星（`_Stars` 1，增益 0.12），定稿里看不到。
4. **臂的顶面和轮廓比定稿多一点蓝紫**：Engel 上半身、群臂的冠，尤其是主座位 U7 那张。可能跟补光实际是 0.52 有关（§2.2 第 9 条），也可能是 `_RimWound`。我没去分开测。
5. **远潮** 在这两个机位几乎看不出来（雾带参数见 §2.2 第 10 条）。
6. **两根光束很淡**，远端也不会变宽（§2.2 第 6 条）。
7. 截图里的摆动相位用的是编辑器的 `_Time`，和渲染不是同一个相位（摆幅很小）。

---

## 5. Console（`console_errors_warnings.txt`，原样；分类如下）

| 条数 | 内容 | 来源 |
|---|---|---|
| 6 | `LB_GateTest_Run.cs` CS0149 ×5、CS0117 ×1 | 我自己导入脚本的第一版（局部变量 `S` 和静态方法同名；`PlayerSettings.vertexChannelCompressionMask` 不存在），改掉了 |
| 3 | TentacleSway ×2、Tear ×1 的 shader 错误 | 套件，§2.1 改掉了 |
| 6 | `Failed to create material drawer Header with arguments 'Own attenuation (sky object, optional)'` | 套件 Tear shader 第 99 行（只是警告） |
| 4 + 11 | `ImportFBX Errors: The mesh M_Headlamp / M_SeatFrame / M_Stripe / M_Concrete / M_Porcelain / M_AluOld / M_Rope / M_TruckHeadlamp / M_TruckHub / M_TruckTire has invalid normals…`，`Mesh '…' has no normals. Recalculating normals.`，`Can't generate normals for blendshape … on mesh 'Body'` | 项目里已有的模型（车 v1、卡车、一个人物），因为加了 AssetPostprocessor 被全部重导才冒出来，和门无关 |
| 7 | `LB_Builder_Road.cs(450,17): warning CS0162: Unreachable code detected` | 主项目已有的警告 |
| 3 + 6 | `Unable to find scene descriptor in scene - Playing without ClientSim`、`Cannot start ClientSim if there is no scene descriptor!` | 测试场景故意不放描述符：我量 draw call 时进过 Play，另外有几次进 Play 不是我的请求触发的 |
| 5 171 | `[UdonSharp] … error CS0518: Predefined type 'System.Object' is not defined or imported` 等 | 我误用打包模式调 U# 编译（§2.4）；正常模式重编没有错误 |

TentacleSway 的 `floating point division by zero` 是 `ShaderUtil.GetShaderMessages` 读出来的，Console 里没有单独打出来。

---

## 6. 怎么重跑

```
Lanbai.Tests.LB_GateTest.NewScene("open")
Lanbai.Tests.LB_GateTest.Build("155.1")          // 搭（会先删掉上一次搭的 GateRoot / NearRoot_bus / Gate_Lights）
Lanbai.Tests.LB_GateTest.Apply("166.15")         // 任意时刻
Lanbai.Tests.LB_GateTest.Shoot("cam=U8fwd;w=1920;h=1080;ss=2;file=LanbaiReports/GateTest/U8fwd.png")   // 9 个机位都能拍，t 默认取 JSON 机位自己的
Lanbai.Tests.LB_GateTest.Perf("cam=U7;t=155.1")
Lanbai.Tests.LB_GateTest.Verify("")
```
JSON、FBX、shader 换了新版，拷进 `Assets/Lanbai/Gate|Tentacles|Tear` 以后重跑 `Build` 就行。材质在 `Assets/Lanbai/Tests/GateTest_Materials/`，每次 Build 原地更新。
