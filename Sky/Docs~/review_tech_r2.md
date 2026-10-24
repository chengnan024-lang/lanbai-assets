# 天空包 技术审查 第 2 轮（review_tech_r2）

审查人：独立技术审查（云端），2026-10-23。对象：`pkg/sky` 5343193（含 WIP 9a4034a 对 9e163d9 的改动）。行号按 5343193。
已跑：`check_shaders.py Sky Act09_StarSea LanbaiSky.cginc LanbaiFog.cginc`：5 个文件，0 错，1 警告（`Lanbai_StarPoints.shader:57-60` 自己声明了 `_Udon_StarShape`）。`check_cs.sh Sky Act09_StarSea`：编辑器、player、lint 都过。`test_sequence.py`：OK。另外用它的 `blend()` 补算了第 1→2 幕的淡变（见第 1 条）。这些检查都不等于 Unity 或 U# 编译，长时间的 CPU 渲染没有跑。

## 结论：有条件通过

上一轮必须改的 0–9 条，都能在代码里找到对应的改动：一个材质加全局量、驱动、预设写全、并集混合、不换材质、两个所有权开关、星的 D-06 参数、月盘 mip、日盘软边、日线读 `_Udon_SunDisc.z`。这部分是扎实的。
问题出在新的运行时路径上。按 README §3.1 的时间表真跑一遍，有几处肉眼能看到的错：第 1→2 幕整片天转 70°；8-ii→8b 最后一帧跳一下；第 9 幕星翻倍。另外驱动的时间窗盖住了整部片，序列测试也没覆盖真实的顺序。下面 1–7 条改完、测试补齐以后可以合，不用再整轮重审。

## 必须改

1. **第 1→2 幕淡变时 HDRI 在 10 秒里转 70°，结束那一帧还会换一张图**（`LanbaiSkyPreset.cs:153-156, 166-171`；README_Sky.md:117）
   - 原因：两个预设都有立方图 A（flags.y 都是 1），落到 `Vector4.Lerp`。`_Udon_Sky_RotationA` 从 −70 插到 0（补算结果：t 为 0.25/0.5/0.75 时分别是 −52.5/−35/−17.5）。纹理一直用 town 那张（`ca = cubeA`），t=1 时 `other.Apply()` 一帧换成 overcast。
   - 后果：头显里整片云天以 7°/s 旋转，违反圣经 §1.8，最后再跳一下。
   - 改法：两边都有 A 但图或旋转不同时，把 other 的图绑到 B 槽（`_Udon_SkyCubeTexB`），并把 B 的参数设成 other 的 A 参数、flags.z=1，用 `_Udon_SkyBlend.x` 从 0 插到 1。t=1 时 `other.Apply()` 把它放回 A、blend=0，画面一样。
   - 同一段淡变里 `_Udon_FogBandDir` 的模长也从 1 线性降到 0。在 t≈0.5 时 `LanbaiBandDir()`（`LanbaiSky.cginc:154`，`dot > 0.25`）会一帧从方位 −70° 跳到 +Z，雾里钠光那一侧还剩一半的颜色。方向量要和立方图参数一样处理：只按有方向的一边写，或者把颜色和方向分开插值。

2. **8-ii→8b（`dusk_8ii.ApplyBlend(blue_hour)`）有三处不连续，还和日线抢写同一个量**（`SkyPresets.json` 的 blue_hour；`make_presets.py:109-116`；README_Sky.md:125）
   - a）blue_hour 不写 `_Udon_SunDir`（w=0）。淡变期间 w=1−t>0，S 用的是暮的太阳（方位 0°）；到 t=1，S 换成 `_Udon_Sky_SunDir`（0.7, 0.1, 0.7），也就是方位 45°。带 1（单调带，以太阳为中心，σ=110°，增益 0.85）一帧移动 45°：左侧 −90° 那个方向的权重从 0.72 掉到 0.47。改法：blue_hour 的 `_Udon_SunDir` 和 `_Udon_Sky_SunDir` 都写成 SUN8，w=1。
   - b）`_Udon_SunDisc` 在淡变的每一帧都被 `ApplyBlend` 整个写一遍（z 一直是 0）。§3.1 又要求同一段时间里"日线另写 `_Udon_SunDisc.z`"，结果取决于两个驱动在同一帧里谁后写，违反"一个名字一个写入者"。改法：二选一。日线的 z 和增益走预设之间的插值（8-ii 的 z=10，blue_hour 的 z=0）；或者 `ApplyBlend` 加一个排除名单，在 §3.1 里写明。
   - c）分组只认名字后缀 A/B（`LanbaiSkyPreset.cs:76-77`）。只给立方图用的 `_Udon_Sky_TintElevation / NadirColor / BelowShape / SunRemove / HorizonLift / OtherTint` 落到第 0 组照常插值。t=0.5 时 TintElevation.z=82.5（补算），立方图的权重还有 50%，于是天顶出现总导演 r2 #2 禁止的那种"平盖加一圈边"。改法：组号由 `make_presets.py` 按显式清单导出成 `int[] vecGroup`，构建器填进去，不在 Udon 里靠字符串猜。

3. **天空驱动的时间窗盖住了第 1 到 12 幕，表要手填**（`LanbaiSkyDriver.cs:34-45`；`LanbaiSkyBuild.cs` 不建驱动）
   - `LanbaiWindow()` 返回所有条目的 [最小 t0, 最大 t1]。按 README_集成 §3，`extWindows` 是分发层从各驱动的 `LanbaiWindow()` 汇总出来的。勾上 `extAtmosphere/extSkybox` 以后，`LB_Journey` 在第 4–10 幕也会让出 RenderSettings，而这些幕里没有任何人写（`ownsAtmosphere` 默认关）。
   - `presetT0/T1/fadeSec` 没有搭建脚本从 `cues.json` 烘进来，违反 README_集成 §4。长度对不上会在 `IndexAt` 或 `presets[i]` 处越界，Udon 抛异常后这个行为在整场里就停了。
   - 改法：一个实例只负责一段连续的时间窗，建两个实例（1–3 幕、11–12 幕）。`Build Sky` 按标签建好驱动并填好数组。`Start()` 里先校验四个数组长度一致，不一致就报错并不运行。

4. **第 9 幕的星画两遍**（README_Sky.md:25 第 7 步；`Act09_StarSea/Editor/LanbaiAct09Build.cs:79`）
   - README 让场景里常驻一个 `StarPoints_BSC5` 加 `M_Sky_StarPoints` 的物体，第 3、4 幕靠它。Act09 又建了一个 `Stars_BSC5`，网格和材质都一样。
   - F13 之后 `_Udon_StarGain.x=1` 是全局的，两个物体都画，叠加混合，等于 8404 颗星整体 +1 EV，第 9 幕所有标定都偏了。
   - 改法：全场景只留一个主星物体，由天空的 `Build Sky` 建；Act09 的搭建去引用它，不再新建。或者第 7 步的物体挂到天空驱动 1–3 幕实例的根下，由 `LanbaiActivate` 在遮挡下关掉。

5. **D-06 检查低估了最亮那颗星的峰值**（`Tools~/render/check_stars.py:64`，`stars_cpu.splat`）
   - splat 按星的真实亚像素位置，在像素中心取高斯值。FWHM 1.6 px 时，星落在像素角上，中心像素只有峰值的 0.58 倍；shader 也一样。头一动，星扫过像素网格，最坏情况就是正对像素中心的全峰值。
   - 现在的余量是 ΔL* 10.93 / 11.54 对 12，在最坏情况下很可能不够。改法：L* 按全峰值算，也就是把每颗星对齐到像素中心再 splat，然后重新解 `_Udon_StarGain.x`。
   - 另外，"L* ≤ 12"被改读成"比自己那块天高出 ≤ 12"（文件头第 3–6 行），这超出了 D-06 的原文。上一轮总工程师写的是绝对值（Y≈0.014）。理由可以成立，但要请总导演补一条裁决，这里不能自己定。

6. **序列测试没有对上真实的顺序**（`test_sequence.py:16-18, 93`）
   - FADES 只有 8-i→8-ii 和 8-ii→8b，漏了 §3.1 里的第 1→2 幕 10 秒淡变。第 1 条就是在这段漏掉的淡变里出的问题，`rot_ok` 本来能抓到。
   - ORDER 里有 `Apply(star_sea)`，可是 §3.1 写的是第 9 幕"从 blue_hour 接着"，运行时没人调 star_sea。这个预设实际是死的，第 9 幕用的是 blue_hour 的 `_Udon_Sky_*`。
   - 第 2 步是 `state.update()` 之后比相等，名字集合一样就必然通过，只验证了名字一致。
   - 改法：§3.1 的表做成数据，驱动数组和测试都从它生成。每段淡变加一个"t=0.999 和 `Apply(b)` 逐像素差 < 1 个 8 位码"的连续性检查，第 2 条的 a 就会被抓到；再加 t=0.5 时天顶梯度自检，第 2 条的 c 也会被抓到。

7. **8K 银河辉光没有 mip，在 VR 里会闪**（`LanbaiSkyImport.cs:52-61`；`LanbaiSkyLayers.cginc:500-503`）
   - 8192 px 对应 0.044°/texel。头显里一个像素大约 0.06–0.1°，相当于缩小 1.5–2.3 倍，还固定在 LOD 0 上采样。Gaia 照片里的细颗粒和暗隙会随头动闪烁，第 9 幕是主角（圣经 §1.8）。
   - 改法：开 mip，用和月盘一样的显式 LOD：`lod = max(0, log2(LanbaiPixelAngle() / (2π/8192)))`。桌面仍然是 LOD 0，不会糊。另外，8 位 sRGB 加 BC7 在 ×g(t) 提亮以后，暗部的渐变要在本地截图里确认没有色块。

## 建议

8. 夜遮罩的椭圆（`LanbaiSkyLayers.cginc:575-577`）两个轴共用 `soft = max(y/x, w/z)`。按 blue_hour 的 (30,45,6,22)，soft=3.67，方位方向的软边从 45° 变成 110°。方位 75° 的地平线在 x=0.75（6 秒）时权重只有 0.81，不满足圣经 §6·8b"别处 6 秒全黑"。建议两个轴各用自己的内外椭圆（e1 用 (x,z)，e2 用 (x+y, z+w)）来插。下一窗重出第 9 幕参考帧时一起核。
9. `ApplyBlend` 第一次调用时建映射表，要做 64×64 次字符串比较（`LanbaiSkyPreset.cs:133-150`），Udon 里大概几到十几毫秒，正好卡在淡变的第一帧。之后每帧写 64 个量。建议：构建器按固定顺序（排序后）写名字，映射就是恒等，只要断言一次；每对预设预先算出"两边不同"的下标表，每帧只写这些（大约 30 个）。
10. U# 白名单：`string.StartsWith/EndsWith`、`Vector4.Max`、`VRCShader.SetGlobalTexture/Vector/Float`、`RenderSettings.fogDensity/fogColor/ambientLight/skybox` 的 setter，我判断都在白名单里，但没有核实。`Cubemap` 当公有字段类型没有把握，退路是改成 `Texture`，`SetGlobalTexture` 本来收的就是 `Texture`。另外，Trilight 模式下 `ambientLight` 只等于天空色，赤道色和地面色还是 `LB_Journey` 写的，README 里写一句。
11. `LanbaiSkyBuild.cs`：
    - `:319` `GameObject.Find` 找不到未激活的根，会重复建；全程没有 Undo；JSON 里删掉的预设，对应物体留在场景里。
    - `:344` 量出来的旋转只写进运行时物体，`ApplyPresetInEditor`（`:379-396`）还用 JSON 里的旧值，所以预览和运行时不一样。
    - `:179` `M_Sky_StarPoints.mat` 只在不存在时才建，v1.1 留下的材质 `_Gain` 还是 1。
    - U# 1.x 的代理改完以后，建议用反射调一次 `UdonSharpEditorUtility.CopyProxyToUdon`。
12. `ClearGlobals()`（`:407`）额外清了 `_Udon_FogCubeParams/_Udon_FogBase`，运行时的 `Apply()` 不清，预览和运行时又不一致。这两个是天空自己的量，应该放进每个预设（值写 0）。`_Udon_TearPos/_Udon_Underwater` 归门和海，请各自在出窗口时把 w 写回 0。overcast 的 `FogBandDir=0` 时，`LanbaiBandDir()` 会退回到门留下来的裂口方向。
13. `LanbaiSunTerm` 不会出 NaN：`pow(edge, ·)` 的底 ≥ 0，指数 > 1。日斑去除里 `q^8`（`:399-400`）在 `p_SunRemove.y` 接近 0 时会溢出成 inf，结果是那一块变黑（不是 NaN）。现在所有预设的 y 都是 2.4 或 2.5，碰不到。可以加一个 `q = min(q, 1e4)` 当保险。
14. `LanbaiHorizonGradient` 改成了 `LanbaiUpStep` 加 `LanbaiGeoLerp`（`LanbaiSky.cginc:186-209`），这个函数是雾共用的。模型 B 的雾色（第 3、6、8、8b 幕，海也 include 它）跟着变了，海和云按旧函数出的参考图对不上。请在 `给总控.md` 里通知这两家。每个像素会多出大约 9 次 log2/exp2，开销可以接受。
15. 第 3→4 幕交接时，门把 `_Udon_StarShape.y` 从 0 写成 −1，光雾带里的星会一帧暗 1 EV。建议门按 U6 那段 smoothstep 把 y 从 0 渐变到 −1，写进 `act4_gate.stars` 的 note。
16. 文档和登记：
    - `Common/UdonGlobals.md:42` 还写着 SkyFx.z = 日线半长，`:46` StarGain 的写入者还是"第 9 幕"，都过时了。
    - `_Udon_Sky_*` 在登记表里是按一族登记的，`gen_globals` 会丢掉带 `*` 的族，`LanbaiGlobals.cginc` 永远不会生成这 45 个名字。建议逐个登记，或者让生成器从 `SKY_V4/SKY_F1` 展开。
    - `Lanbai_StarPoints` 的 `_Udon_StarShape` 请等登记以后改成 include。

## 核过没问题的

- `#ifndef LANBAI_DECL__Udon_<名>` 的守卫名和 `LanbaiGlobals.cginc` 的写法一致。所有声明都在使用之前（`_GlowScale` 在 `LanbaiSkyLoadParams` 前面）。
- 全局立方图不是材质属性，所以不会被材质值盖掉。解码用 `(1,1,0,0)`，对 BC6H 和 RGBAHalf 都对。
- 月盘的显式 LOD 公式是对的。日盘软边 ≥ 2 px，再乘峰值锐化以后，可见的边大约 1.2 px。`LanbaiUpStep` 的分母有下限。`LanbaiGeoLerp` 有 1e-6 下限。天顶和天底的方位用 `+1e-5` 兜住了。
- 两个 shader 的立体宏齐全。抖动按方向锚定。星点按中眼位置摆放、按每只眼的像素角定大小。星点加了 `DisableBatching`，FWHM 的范围是 1.5–4。
- 驱动在淡变结束那一帧（`lastWasFade`）和重新进入窗口时都会补一次 `Apply()`，跳帧和时间轴跳转都能收敛。`Start()` 写 t=0 的预设。
- 每个预设都列全 64+1 个名字，按片子顺序回放没有残值。上一轮第 2 条的残值问题已经解决。
