# 天空包 技术审查 第 1 轮（review_tech_r1）

审查人：独立技术审查（云端），2026-10-23
对象：`pkg/sky`，HEAD `5425551`，加上审查时工作区里还没提交的改动（`Lanbai_StarPoints.shader` 的 `_UseGlobalGain` / 亮星 20 名过渡、`LanbaiSkyLayers.cginc` 的夜权重缓动、`SkyPresets.json` 的 blue_hour、`LanbaiSkyBuild.cs` 的 `SaveStarMesh`）。行号按审查时的工作区。
范围：`Sky/Shaders/Lanbai_Sky.shader`、`Sky/Shaders/LanbaiSkyLayers.cginc`、`Sky/Shaders/Lanbai_StarPoints.shader`、`Common/Shaders/LanbaiSky.cginc`、`Common/Shaders/LanbaiFog.cginc`、`Common/Shaders/LanbaiVR.cginc`（作背景）、`Sky/Editor/LanbaiSkyImport.cs`、`Sky/Editor/LanbaiSkyBuild.cs`、`Sky/Runtime/LanbaiSkyPreset.cs`、`Sky/SkyPresets.json`、`Sky/FogPresets.json`。
已跑：`check_shaders.py`（37 个变体全过，含 `Lanbai_Sky` / `Lanbai_StarPoints` 的 base 和 `USING_STEREO_MATRICES`）、`check_cs.sh`（通过）。这两个检查能证明 slang 的语法和类型没问题，也能证明 C# 对 2021.1 的引用程序集能过类型检查，证明不了 FXC 和 Udon 的行为。下面每一条都对照代码核过。

---

## 结论先说

没找到 FXC 一定会报的编译错误。几个关键的地方都对：声明都在使用之前；`[Header()]` 里没有冒号、括号、逗号；没有拿保留字当变量名；采样器 5 个；天空盒里用的都是 `texCUBElod` / `tex2Dlod`，分支里没有隐式导数；两个 shader 的 SPS-I 宏都齐，星点的位置也确实用了两眼中点。数值上，天顶和天底附近的 `normalize(V.xz + 1e-5)` 在现在的预设下不会露出奇点（方位相关的项在 22–60° 以上都乘到 0 了），星点 quad 在竖直方向也有保护。

要改的有四处：两处在运行时的数据流（全局量残留；`ApplyBlend` 的逻辑和在 Udon 里的开销），一处接口名对不上（日线），一处 VR 画质（月盘在 mip 0 上闪）。都不难改，但不改会直接看到错。

---

## 必须改

### M1 预设之间的全局量残留：日、月、带、夜会串到别的幕
- 位置：`Sky/Runtime/LanbaiSkyPreset.cs:53-70`（`Apply()`），`Sky/SkyPresets.json`（每个预设的 `globalVectors`）
- 问题：设计是“全局量 w > 0 时盖过材质值，没设（w = 0）时用材质值”，可是 `Apply()` 只写预设里列出来的名字，不写的就留着上一幕的值。按现在的 JSON：
  - `moon_night`（第 3 幕）写了 `_Udon_MoonDisc = (1, 0.6, 0, 1)` 和 `_Udon_MoonDir`，门的驱动在第 4 幕也写这两个，w = 1。`dawn`、`dusk_8i/8ii`、`blue_hour`、`star_sea`、`overcast_rain_night`（第 11–12 幕）都不写它们，所以 `LanbaiMoonTerm` 在这些幕里照样执行（`LanbaiSkyLayers.cginc` 里 `moonG = _Udon_MoonDisc.x = 1`）。这些材质没有 `_MoonTex`，圆盘是透明的，但月晕用的是材质默认的 `_MoonGlowColor` (0.275, 0.366, 0.578) × (1.6 e^(−0.9a) + 0.06 e^(−0.32a))：月亮那个方向（方位 −12°，仰角 8°）会多出一团线性约 (0.46, 0.61, 0.96) 的蓝光，3° 以外还剩约 0.05。晨的天上、第 11 幕的阴云夜里都一眼看得见；第 9 幕里它加在夜层后面，盖在星海上。
  - `dusk_8i/8ii` 写了 `_Udon_SunDisc = (1, 0.45, 0, 1)`，`blue_hour` 和 `star_sea` 不写。`blue_hour` 的材质里 `_SunGain = 0`，但全局量优先，所以蓝时里仍然画着一个增益 1 的日盘，位置用残留的 `_Udon_SunDir`（仰角 0.5°），颜色是材质默认的 `_SunColor`。
  - `blue_hour` 写了 `_Udon_SkyFx = (0, 0.9, 0, 1)` 和 `_Udon_SkyBlend`，后面的预设不写这两个，带 1 的增益和程序化权重都会被带过去。第 9 幕在夜权重是 1 的时候能盖住，夜权重还在爬的那 8 秒里盖不住。
- 修法（二选一，推荐第一种）：
  1. 在 `LanbaiSkyPreset` 里放一份天空自己的全局量名单（和 `LanbaiSkyBuild.AllVec/AllFloat` 同一份，但不放门的 `_Udon_TearPos` 这类别人的量），`Apply()` 先把名单里每个量写成 `Vector4.zero` / `0`（也就是“没设，回到材质值”），再写预设里的值。`ApplyBlend()` 里预设没有的名字也按 0 处理。
  2. 生成 JSON 的 `make_presets.py` 给每个预设补全所有天空全局量，关掉的写成“w = 1、增益 0”，比如 `_Udon_MoonDisc = (0, 0.6, 0, 1)`、`_Udon_SunDisc = (0, 0.45, 0, 1)`。
- README §5 里补一句：“谁写了一个天空全局量，离开自己的时间窗时负责把 w 写回 0”，第 3–4 幕的月亮要特别写明。

### M2 日线的全局量：shader 读 `_Udon_SkyFx.z`，文档写的是 `_Udon_SunDisc.z`
- 位置：`Sky/Shaders/LanbaiSkyLayers.cginc:233` 读 `_Udon_SkyFx.z`；`Common/Shaders/LanbaiSky.cginc:107` 的注释、`Sky/README_Sky.md` §2 第 7 条（第 54 行）和 §4 表（第 65 行）、`Sky/给总控.md` §4 都写 `_Udon_SunDisc.z` 是“日线半长”；README 第 62 行又写 `_Udon_SkyFx.z` 是日线半长。
- 后果：第 8 幕的驱动如果照 §2 或给总控.md 去写 `_Udon_SunDisc.z`，日线不会出现；再加上 dusk 预设写的 `_Udon_SkyFx = (x, 0, 0, 1)` 会把 `_SunShape.w` 也盖掉，F12 的日线收缩就整段没有了。
- 修法：只留一个。建议用 `_Udon_SunDisc.z`，日的参数都放在一个量里，海也读这个量。shader 那行改成 `float sunLine = (_Udon_SunDisc.w > 0.0) ? _Udon_SunDisc.z : _SunShape.w;`，`_Udon_SkyFx.z` 标成“保留”，README、给总控.md 和 `Lanbai_Sky.shader` 第 25 行的头注释一起改。

### M3 月盘在 mip 0 上采样：在 VR 里闪
- 位置：`Sky/Shaders/LanbaiSkyLayers.cginc:159`，`tex2Dlod(_MoonTex, float4(uv, 0.0, 0.0))`
- 问题：月盘半径 0.6°，直径 1.2°，在头显里大约 17–24 px（每像素 0.05–0.07°），贴图是 1024 px，缩小了约 45 倍。导入器给 `Moon_Disc` 开了 mip（`LanbaiSkyImport.cs:66`），但 `tex2Dlod` 用的是 mip 0，等于每个像素随便抽一个 texel。结果是月面的明暗斑每帧跳，头稍微一动整个月亮就在“沸腾”。第 3 幕月下云海那段很长，月亮又是画面焦点。
- 修法：自己算 LOD（这里在分支里，不能用隐式导数）：
  ```hlsl
  float4 _MoonTex_TexelSize;   // 和其他 uniform 一起声明
  ...
  float lod = log2(max(_MoonTex_TexelSize.z * k * LanbaiPixelAngle(), 1.0));   // k = 0.5 / tan(r)：每弧度对应多少 uv
  float4 t = tex2Dlod(_MoonTex, float4(uv, 0.0, lod));
  ```
  半径 0.6° 时算出来约 5.4。`LanbaiPixelAngle()` 读的是 `UNITY_MATRIX_P` 和 `_ScreenParams`，frag 第一行已经有 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`，所以每只眼取到的是自己的值。另一个办法是直接发一张 128 px 的月盘（贴图本身就够了，还省显存）。

### M4 `ApplyBlend()`：逻辑和注释不一致，每帧在 Udon 里也太贵
- 位置：`Sky/Runtime/LanbaiSkyPreset.cs:74-108`
- 问题：
  1. 注释（第 6–7 行）说“名字不同的在 t = 0.5 跳过去”，但找不到对应名字时 `b = a`（第 82、88 行），`(t < 0.5f ? a : b)` 两边是同一个值，**根本不会跳**。
  2. 只有 `other` 里有、`this` 里没有的名字一次都不写，t = 1 也不写。比如 `dusk_8ii → blue_hour`，`blue_hour` 有 `_Udon_SkyBlend`，`dusk_8ii` 没有，这个量就一直不会被写。这一条和 M1 叠在一起。
  3. 开销：内层循环每次迭代都读 `other.vectorNames.Length` 和 `other.vectorNames[j]`。在 U# 里读别的 behaviour 的字段，每读一次就是一次 `GetProgramVariable` extern，再加一次字符串比较 extern。12 × 11 个向量加上浮点量，每帧大约 300–500 次 extern。按 Udon 每次 extern 约 0.5–1 µs 估，可见过渡期间每帧 0.2–0.5 ms，圣经 §1.9 给全部 Udon 的预算只有 0.4 ms。这是估算，要在 Unity 里用 Profiler 实测。
- 修法：第一次遇到某个 `other` 时建一张 `int[] map`（this 的第 i 个对应 other 的第几个，−1 表示没有），把 `other` 存进一个私有字段，下次是同一个 `other` 就直接用这张表。循环前先 `string[] on = other.vectorNames; Vector4[] ov = other.vectorValues;` 拷成局部变量。名字取两边的并集，缺的一边按 `Vector4.zero` 处理（和 M1 的语义一致）。t ≥ 1 时直接调 `other.Apply()`。另外 `Build Preset Materials` 可以在报告里列出每对相邻预设的名字差异。

---

## 建议

### S1 天空盒的逐像素开销：心里要有个数，几个地方可以省
- 在 9 MP @ 90 Hz 下估的（只算天空可见的像素，天空盒在不透明物体之后画，有深度测试）：
  - 晨 / 暮（一张立方图、两条带、日、紫色保护、抖动），地平线以上：1 次 cube 采样，大约 35–45 个超越函数（`RotY` 的 sin/cos、`DecodeHDR` 里的 pow、asin×3、acos×2、每个 `normalize` 一个 rsq、带的 exp×4、`LanbaiAngleDeg` 的 atan2 + 2 sqrt、日晕 exp×2、`LinearToGammaSpace` 的 pow×3），大约 300 条 ALU。地平线以下多一次 cube 采样（`LanbaiSkyLayers.cginc:100-101`，sharp + soft），色调也多算一遍。
  - 8-ii（另一片天）在地平线以下：主路径 2 次采样 + 另一片天 1 次 + 两遍日项，A/B 混合时再翻倍，最多 6 次 cube 采样。
  - 第 9 幕：程序化 + 银河，1 次 2D 采样，大约 20 个超越函数。
  - 按 RTX 3060 粗算：天空占半屏时约 0.25–0.35 ms，全屏（第 9 幕车厢消失后、抬头看天窗）约 0.5–0.6 ms。能接受，但 README 里没有这一项，§1.9 的 5.3 ms 里也没算。
- 能省的：
  1. 8-ii 里另一片天的权重 `w ≥ 0.999` 时（地平线以下 0.5° 开外），主路径的 `LanbaiCubes` 白算了。先算 `w`，用 `[branch]` 跳过主路径，地平线以下能省 2–4 次采样。
  2. 只依赖 uniform 的量每个像素都在重算（`sin/cos(radians(_RotationA))`、`sin(radians(_BelowShape.z))`、`normalize(_SunDir)`），FXC 不会把它们挪到 CPU。可以由 `Build Preset Materials` 写进材质（比如 `_RotA_SC = (sin, cos)`），或者至少接受这点开销。
  3. 立方图都是 BC6H，`DecodeHDR` 里的 pow 用不上，直接 `raw.rgb` 就行。
  4. `LanbaiBandWeight`、`LanbaiNightWeight` 里的方位角只用来做阈值和高斯，可以直接用余弦比较，省掉 acos。
  5. `gal == 0` 时（蓝时到点燃之间）跳过 `LanbaiGalaxy` 的采样。
- README 里写一行“天空盒预计 0.3–0.6 ms @ 9 MP，请用 GPU Profiler 实测”。

### S2 `pow(负数, 2.0)`
- 位置：`Sky/Shaders/LanbaiSkyLayers.cginc:178-179`（`LanbaiBandWeight`）
- `(el - shape.x) / sigma` 可能是负的。现在能得到正确结果，只是因为 FXC 会把字面量指数 2 展开成乘法；按 HLSL 的定义，pow 对负底数是 exp2(y·log2(x)) = NaN。别的后端（或者以后换编译器）会出 NaN，PPv2 的 Stop NaN 会把那一圈地平线带涂黑。
- 修法：`float de = (el - shape.x) / max(shape.y, 0.1); float we = exp(-0.5 * de * de);`，方位那一项也这样改。

### S3 月亮在天顶时基底退化
- 位置：`Sky/Shaders/LanbaiSkyLayers.cginc:155`，`normalize(cross(float3(0,1,0), M))`
- 月亮正好在天顶时 cross 是 0，normalize 出 NaN。现在的预设月亮仰角是 8°，没事；但这个函数和镜子是共用的，以后谁把月亮调高就会出问题。照星点 shader（`Lanbai_StarPoints.shader:85`）的办法加一个保护：`abs(M.y) < 0.99 ? up : float3(1,0,0)`。

### S4 `atan2(0, 0)` 在天顶 / 天底
- 位置：`Common/Shaders/LanbaiSky.cginc:249`（`LanbaiGalaxyUV`）
- FXC 把 atan2 展开成 min/max 相除，(0, 0) 时得到 0/0。只有方向正好是 (0, ±1, 0) 的那个像素会碰到，概率很小，碰到了就是一个 NaN（PPv2 显示成黑点）。顺手改成 `atan2(V.x, V.z + 1e-7)`。

### S5 星点画在 20 km：比 20 km 更远的不透明物体会被星盖住
- 位置：`Sky/Shaders/Lanbai_StarPoints.shader:34`（`_Distance = 20000`），队列 `Transparent-400`（2600）
- 星点不写深度，做深度测试，所以只有比 20 km 近的不透明物体能挡住它们。圣经里有 30 km 的东西（3a 的裂口线）。有星的幕里如果有超过 20 km 的不透明几何（远山、远潮的不透明部分），星会画到它们前面。云卡在 Transparent 3000 之后画，能正常盖住星，这点没问题。
- 修法：`_Distance` 用 40000（far 是 45000，反向 Z 下精度没问题），或者在 README 里写明“有星的幕里不能有 20 km 以外的不透明物体”。

### S6 星点会叠到月盘上
- 星是在天空盒之后叠加画上去的，月盘后面的星会透过月盘显示出来。目前第 9 幕没有月亮，可以先不管；如果第 3 幕要星和月同时出现，在星点的顶点着色器里用 `_Udon_MoonDir/_Udon_MoonDisc` 把落在月盘里的星的 flux 设为 0。

### S7 `Bake Fog Cube From Skybox`
- 位置：`Sky/Editor/LanbaiSkyBuild.cs:370-388`
  1. `Camera.RenderToCubemap(Cubemap)` 写进 `RGBAHalf` 的 Cubemap 时会不会保留 HDR，我不能确定（这条路径内部要做一次读回）。要么在 Unity 里实测（烘完读一个已知大于 1 的方向），要么改成渲进 `RenderTexture`（`dimension = Cube`，ARGBHalf），再逐面 `ReadPixels`。
  2. `cube.Apply(true)` 是每个面各自做盒式滤波生成 mip，面和面之间不过滤。雾用 mip 3（64 → 8 px），立方体的棱上会有色差。建议导出成经纬 EXR，用导入器的 Convolution = Specular、Fixup Edge Seams 生成。
  3. 烘的时候天空盒里的日盘、月晕都会被烘进去（HDR 的日盘模糊以后就是雾里的一块亮斑）。烘之前把 `_Udon_SunDisc`、`_Udon_MoonDisc` 设成 w = 1、增益 0，`_Udon_FogCubeParams.x` 设成 0（不然 `LanbaiHorizon` 会读上一次的雾立方图，形成回环），烘完再恢复。
  4. `AssetDatabase.CreateAsset` 如果目标已经存在，会删掉重建，GUID 也会变，材质和驱动对它的引用就断了。已经存在时用 `EditorUtility.CopySerialized` 原地覆盖。

### S8 `Create Preset Objects`
- 位置：`Sky/Editor/LanbaiSkyBuild.cs:290-317`
  1. 第 295 行先 `DestroyImmediate` 整个 `Lanbai_SkyPresets` 再重建。各幕驱动在 Inspector 里引用的预设组件会全部变成 Missing，而且不会报错。改成按名字找已有的子物体，原地更新数组。
  2. U# 1.x 里改的是代理组件。保险起见，赋值以后用反射调一次 `UdonSharpEditor.UdonSharpEditorUtility.CopyProxyToUdon(c)`，免得后台的 UdonBehaviour 还是空数组（运行时 `Apply()` 什么都不做，也不报错）。最后调 `EditorSceneManager.MarkSceneDirty`。
  3. `UdonSharpUndo.AddComponent` 找不到时退回普通的 `AddComponent`，这样建出来的组件在 VRChat 里不会运行。这一条现在只打了一行 Log，建议改成 `LogError`。

### S9 16K HDRI：导入尺寸和量太阳时的内存
- `README_Sky.md` §0 第 2 条没写 Max Size。建议写明：立方面 2048（BC6H 带 mip 每张约 32 MB，两张晨暮约 64 MB）。不要让 16K 原图导成 4096 的面（每张约 130 MB，§1.9 的显存上限是 700 MB）。
- `HdrSunDirection` / `ReadHdrLuminance`（`LanbaiSkyBuild.cs:224`、`:253`）对 16384×8192 的图会开一个约 537 MB 的 float 数组，再加上整个文件的 byte[]（几百 MB），然后在 C# 里做 3×3 的全图扫描。能跑，但慢，也容易让编辑器卡住或内存不够。建议解码时直接按 4×4 块累加亮度，存到 1/16 大小的数组里，找到最亮的块以后再回原分辨率在小窗口里精确定位。

### S10 经纬图约定要在 Unity 里实测一次
- `HdrSunDirection` 和 `make_overcast_night.py` 都假设立方图导入器的经纬映射和 Skybox/Panoramic 一样（u = 0.5 − atan2(z, x)/2π，第 0 行是天顶）。如果导入器实际差一个固定旋转，HDRI 里的太阳就和程序化的日盘不在一个地方，天上会出现两个太阳。这一点云端没法验证。
- 在 README 的验收里加一步：临时把 `_ClampA` 调到 1000、`_SunGain` 设成 0，确认 HDRI 的太阳正好落在 `_Udon_SunDir` 上（偏差 < 0.2°），再改回来。

### S11 旋转的方向和 Unity 自带天空盒相反
- `LanbaiRotY`（`LanbaiSkyLayers.cginc:54-59`）的意思是“内容顺时针转 +deg”；Unity 的 Skybox/Cubemap 的 `_Rotation` 是转几何、采样不转，同一个数值方向正好相反。代码内部是自洽的（`Build Preset Materials` 也是按这个约定算的）。但本地如果从别的天空盒材质抄一个旋转值过来就会转反，在 README §3 里写一句。

### S12 “不换材质”的过渡链要和生成的材质对得上
- README §5（第 89 行）说暮 → 蓝时 → 星海用全局量连续过渡、不换材质，还说暮和蓝时可以共用 `dusk_8ii` 的材质。但 `dusk_8ii` 的材质里没有蓝时的 `_Band1Color/_Band1Shape`（用的是 shader 默认的 (14, 8, 0, 60)，不是 blue_hour 的 (12, 7, 0, 100)），也没有 `_GlowTex`。工作区里 blue_hour 已经改成 `glow: true` 并加了 `_StarFloorAdd`，方向是对的。请在 README 里写清楚整条链从哪一刻起用哪个材质、在什么时候换（例如在夜权重 = 1、银河增益 = 0 的那几秒换，两个材质算出来的都是 `_NightColor`，换了看不出来），每个材质需要哪些参数，并由 `make_presets.py` 保证这些参数一致。

---

## 小事

- `Lanbai_Sky.shader:25` 头注释说 `_Udon_SkyFx.y = mid-band gain`，其他地方都说是“带 1 的增益”，统一一下。
- 登记：`_Udon_Fog`、`_Udon_FogModel` 在代码里用了，但 `给总控.md` §1 和 §4 都没列，`Common/UdonGlobals.md` 里也没有。`_Udon_SkyFx` 等已经在 §4 里了。
- `LanbaiSkyBuild.ClearGlobals`（`:358-361`）没清 `_Udon_TearPos`、`_Udon_Underwater`、`_Udon_WaterFog*`。在编辑器里预览过门以后，`LanbaiHorizon` 会一直走第 4 幕的分支。预览窗口应该把它们也清掉（运行时的 M1 名单里不要放 `_Udon_TearPos`）。
- `LanbaiSkyImport` 没有 `GetVersion()`。在 ADB v2 下改了后处理器的代码，已经导入的贴图不会重新导入。加上 `public override uint GetVersion() { return 1; }`，以后每次改设置就把数字加 1。
- 星表的线性颜色最大到 1.40（蓝白星的 b 通道）。`SetColors(List<Color>)` 存的是 float，没问题；但如果以后把 mesh 设成不可读，又打开了 Color 的 Vertex Compression，这些值会被截到 1。README §4 里提一句（和总控 §6 第 8 条一起）。
- 工作区里新加的亮星过渡 `saturate((count - rank) / 20)`（`Lanbai_StarPoints.shader:97`）会让实际加成的个数往下偏：count = 50 时，第 30–50 名只拿到部分加成。如果要的是“前 50 名 ×4”，用 `saturate((count - rank) / 20 + 0.5)`，让过渡以 count 为中心。
- `Build Star Mesh` 里 `CopySerialized(m, old)` 以后，临时的 `m` 没有销毁（会提示 leaked mesh），加一句 `UnityEngine.Object.DestroyImmediate(m)`。`SaveStarMesh` 也一样。
- `FindCube` 用 `AssetDatabase.FindAssets(name)` 按名字模糊找，工程里如果同时有 1K 和 16K 的同名 HDRI，会拿到先找到的那个。报告里已经打印了路径，请本地看一眼。

---

## 核过、没有问题的点（省得下一轮重复查）

- FXC：`samplerCUBE` / `sampler2D` 当函数参数传是可以的（调用处是静态的）；`half4 _CubeA_HDR` 和 `DecodeHDR` 的签名对得上；`smoothstep` 两端相等时出来的 inf/NaN 会被 d3d11 的 `saturate` 归到 0–1；所有 `[branch]` 里只有显式 LOD 的采样。
- SPS-I：两个 shader 的 appdata / v2f / vert / frag 宏都齐。星点的 `UnityWorldToClipPos` 和 `LanbaiPixelAngle()` 在 vert 里 `UNITY_SETUP_INSTANCE_ID` 之后取的是每只眼自己的矩阵。位置用两眼中点，两只眼之间的差是 IPD / 20 km ≈ 3e-6 rad，可以忽略。
- 星点：quad 和视线垂直；高斯是旋转对称的，`abs(D.y) < 0.99` 换基底不会被看出来。截在 2 FWHM 处，那里的值是 exp(−11.1)，看不见。退化剔除用的是同一颗星的 4 个顶点同一个判断，4 个点叠在一起，面积为 0，而且 z = −1 本来就在裁剪范围外。`Blend One One`、`ZWrite Off`、队列 2600：在天空盒之后、云和车窗玻璃之前画，顺序是对的。FWHM 是按画面中心的像素算的，到视野边缘会变大，对 VR 来说角大小不变，是对的。
- 银河：`tex2Dlod` 不需要导数，所以 atan2 的接缝不会出问题；U 方向 Repeat、V 方向 Clamp、不生成 mip、BC6H 都对；生成脚本（`make_starsky.py:231-237`）的映射和第 0 行朝向都和 `LanbaiGalaxyUV` 一致。4096 宽 ≈ 0.088°/texel，比 VR 像素大，是放大，不会走样。
- 地平线以下的“取地平线样本”`H`：`_BelowShape.x = −75` 时，在 −75° 处 H 的仰角约 2.3°，再往下已经全是天底色，所以接近天底时 H 跑到天顶也没关系。
- `HdrSunDirection`：RLE 解码、指数 2^(e−136)、`-Y` 和 `+Y` 的行序、u/v 到方向的换算，都和它声明的约定一致；`rot = sunAz − az` 和 `LanbaiRotY` 的方向也一致。
- U# 1.x：namespace、`Vector4[]`、`string ==`、调用别的 behaviour 的 public 方法和读它的 public 字段、`VRCShader.PropertyToID/SetGlobal*`，都在 1.x 支持的范围里。`RenderSettings.fogDensity` 和 `RenderSettings.skybox` 的 setter 一般认为 Udon 可以用，但脚本注释里已经写了要核对，请本地在 SDK 3.10.5 里确认。
- `JsonUtility`：顶层是对象，数组里放可序列化的类、`float[]` 都可以；不认识的字段（`measured_views`）会被忽略；七个预设的四个数组都有，所以不会是 null。
- 导入设置：阴云夜 HDR 转立方图（Cylindrical）+ BC6H + mip；月盘 sRGB + BC7 + alphaIsTransparency + Clamp；都对。

---

## 总评：**不通过**

M1–M4 改完就可以过。四处都是局部修改，不需要重新设计。其中 M1、M2 不改的话，第一次在 Unity 里按幕串起来跑就会看到（晨的天上有一团蓝色月晕、蓝时有日盘、F12 没有日线）。M3 要在头显里才看得出来。M4 是 Udon 开销加上逻辑和注释不一致。
