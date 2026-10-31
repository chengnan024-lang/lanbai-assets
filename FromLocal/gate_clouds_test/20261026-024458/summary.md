# 门的云 GateClouds v1.5 + 门的总驱动 · 门测试场景 · 20261026-024458

**✅ 跑完了，工具的检查全过（退出码 0）：待总导演看图，不是验收通过**

- 测试：`gate_clouds_test`（HANDOFF_LOG 2026-10-24「门的云 GateClouds v1.5 合进 main」全条 + 「门的总驱动 LanbaiGateDriver 合进 main」+「门的云第 10 轮第 1 批」（_Stars 0.055、38 张云卡））
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **pass（工具检查全过，待总导演看图）**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/GateTest_play.unity；用时 94.2 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\gate_clouds_test\20261026-024458` 拷到仓库的 `FromLocal/gate_clouds_test/20261026-024458/`，再推。看到的问题写进 `FromLocal/gate_clouds_test/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ⚠️ warn | `U7_vr_budget` | 11.62 | ≤ 8.3（不卡） | 第 4 幕预算 8.3 ms（10-08 不带云的 VR 估算已经是 10.3 ms）。编辑器估算只报不卡：超了照实推，总导演按圣经 §1.9 定砍什么 |
| ⚠️ warn | `U8fwd_vr_budget` | 12.11 | ≤ 8.3（不卡） | 同上 |
| ⚠️ warn | `U8fwd_apl_vs_ref` | 1.26 | 0.85 … 1.15（不卡） | 同上 |
| ⚠️ warn | `U7_shimmer` | 0.07 | ≤ 0.01（不卡） | 头部微动 1 秒里来回跳（shimmer > 4/255）的像素 ≤ 1%：初值，第一次实测后由总工程师定 |
| ⚠️ warn | `U8fwd_shimmer` | 0.08 | ≤ 0.01（不卡） | 同上 |
| ⚠️ warn | `deck_roll_shimmer` | 0.06 | ≤ 0.01（不卡） | 云海滚动：同上 |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `ppv2_effective` | 1 | = 1 | 截图经过了 PPv2（开 / 关 PPv2 各渲一张小图，要不一样） |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |
| ✅ pass | `setting_lights_linear_intensity` | 1 | = 1 | GraphicsSettings.lightsUseLinearIntensity = True（要 True） |
| ✅ pass | `key_apl_vs_ref` | 1.1 | 0.85 … 1.15（不卡） | 和 compare_key.png 上半张（这一版的参照）比 APL；参照是贴图合成的，只看大数，不卡 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 66.6 GB，可用内存 13.1 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 22 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:39:27.181258-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件夹 Assets/Lanbai/Common
- ✅ 文件夹 Assets/Lanbai/Gate
- ✅ 文件夹 Assets/Lanbai/GateClouds
- ✅ 文件夹 Assets/Lanbai/Tear
- ✅ 文件夹 Assets/Lanbai/Tentacles
- ✅ 文件夹 Assets/Lanbai/Tests
- ✅ 文件 Assets/Lanbai/Tests/GateTest.unity
- ✅ 文件 Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc
- ✅ 文件 Assets/Lanbai/Gate/GateLayout_v2.json
- ✅ 文件 Assets/Lanbai/Gate/GateDriver_Bake.json
- ✅ 文件 Assets/Lanbai/GateClouds/GateClouds_Layout.json
- ✅ 类型 Lanbai.Tests.LB_GateTest
- ✅ 类型 LanbaiGateCloudsBuilder
- ✅ 类型 LanbaiGateDriverBuilder
- ✅ 类型 LanbaiGateDriver
- ✅ 类型 LanbaiGateClouds
- ✅ 脚本 LB_GateTest_Run 含「LanbaiGateCloudsBuilder.Apply(t)」
- ✅ 脚本 LB_GateTest_Run 含「SetPB(tear, "Tear_CloudGlow_Additive", mpb, false」
- ✅ 脚本 LB_GateTest_Run 含「SetPB(tear, "Tear_CloudGlow", mpb, false」
- ✅ 脚本 LB_GateTest_Run 含「SetPB(tear, "Tear_LightLane", mpb, false」
- ✅ 脚本 LB_GateTest_Run 含「SetPB(st, st.name, mpb, false」
- ✅ 文件 Assets/Lanbai/GateClouds/GateClouds_Layout.json 含「Tower_Colossus_2_Back」
- ✅ 文件 Assets/Lanbai/GateClouds/GateClouds_Layout.json 含「"quality": "default"」
- ✅ 文件 Assets/Lanbai/Gate/GateLayout_v2.json 含「"_Stars": 0.055」

## 步骤
- ✅ [build] Lanbai.Tests.LB_GateTest.Build(155.1)（437.9 ms）
- ✅ [build] set_light Gate_Lights/Fill_from_below（1.2 ms）
- ✅ [build] 材质 ：_HazeNear = [0.1085,0.113,0.1641]，_HazeFar = [0.0436,0.0504,0.0726]，_BandEl = [6,22,2]（2.9 ms）
- ✅ [build] 材质 Assets/Lanbai/Tests/GateTest_Materials/M_GateAirSky.mat：_Stars = 0.055（0.2 ms）
- ✅ [build] 菜单 蓝白/Gate Clouds/Build（998.2 ms）
- ✅ [build] assert_log （0.2 ms）
- ✅ [build] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.3 ms）
- ✅ [build] 菜单 蓝白/Gate/Build Driver + Test Clock (Play mode only)（7,593 ms）
- ✅ [build] assert_log （0 ms）
- ✅ [after_build] assert_no_component （0.3 ms）
- ✅ [after_build] assert_renderer **/Tear_CloudGlow = false（0.5 ms）
- ✅ [after_build] assert_renderer **/Tear_CloudGlow_Additive = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Tear_LightLane = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Shaft_00 = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Shaft_01 = false（0.1 ms）
- ✅ [after_build] assert_renderer **/GateBeam_Shaft_00 = true（0.1 ms）
- ✅ [after_build] assert_renderer **/GateBeam_Shaft_01 = true（0.1 ms）
- ✅ [after_build] assert_light Gate_Lights/Tear_CabinOnly（0.6 ms）
- ✅ [after_build] assert_light Gate_Lights/Fill_from_below（0.1 ms）
- ✅ [after_build] collect （9.8 ms）
- ✅ [after_build] collect （9.5 ms）
- ✅ [after_build] collect （9.5 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(154.5)（12.7 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.5 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（11.9 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(166.45)（34.8 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(177.55)（11.6 ms）
- ✅ [before] 材质 M_GateAirSky：_BackBand = 1.25（14 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（25 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（12.2 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.6 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.7 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（12.3 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(160)（12.5 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.8 ms）
- ✅ [perf_state U7/deck_off] set_active GateRoot/GateClouds/Deck = false（0.1 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11 ms）
- ✅ [perf_state U7/clouds_off] set_active GateRoot/GateClouds = false（0 ms）
- ✅ [perf_state U7/clouds_off] set_active **/GateBeam_Shaft_00 = false（0.2 ms）
- ✅ [perf_state U7/clouds_off] set_active **/GateBeam_Shaft_01 = false（0.1 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.7 ms）
- ✅ [perf_state U7/auto_lite] 临时改 Assets/Lanbai/GateClouds/GateClouds_Layout.json：deck.quality = "auto_lite"（30.2 ms）
- ✅ [perf_state U7/auto_lite] 菜单 蓝白/Gate Clouds/Build（925.5 ms）
- ✅ [perf_state U7/auto_lite] assert_log （0 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（16.1 ms）
- ✅ [perf_teardown] 菜单 蓝白/Gate Clouds/Build（950.1 ms）
- ✅ [perf_teardown] assert_log （0 ms）
- ✅ [perf_teardown] Lanbai.Tests.LB_GateTest.Apply(155.1)（13 ms）
- ✅ [perf_teardown] 菜单 蓝白/Gate/Build Driver + Test Clock (Play mode only)（7,450 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（34.3 ms）
- ✅ [perf_state U8fwd/deck_off] set_active GateRoot/GateClouds/Deck = false（0 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（11.9 ms）
- ✅ [perf_state U8fwd/clouds_off] set_active GateRoot/GateClouds = false（0.1 ms）
- ✅ [perf_state U8fwd/clouds_off] set_active **/GateBeam_Shaft_00 = false（0.2 ms）
- ✅ [perf_state U8fwd/clouds_off] set_active **/GateBeam_Shaft_01 = false（0.1 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（11.8 ms）
- ✅ [perf_state U8fwd/auto_lite] 临时改 Assets/Lanbai/GateClouds/GateClouds_Layout.json：deck.quality = "auto_lite"（29.4 ms）
- ✅ [perf_state U8fwd/auto_lite] 菜单 蓝白/Gate Clouds/Build（887.7 ms）
- ✅ [perf_state U8fwd/auto_lite] assert_log （0 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（11.4 ms）
- ✅ [perf_teardown] 菜单 蓝白/Gate Clouds/Build（973.9 ms）
- ✅ [perf_teardown] assert_log （0 ms）
- ✅ [perf_teardown] Lanbai.Tests.LB_GateTest.Apply(155.1)（11.7 ms）
- ✅ [perf_teardown] 菜单 蓝白/Gate/Build Driver + Test Clock (Play mode only)（7,494 ms）
- ✅ [post] save_scene_copy （66 ms）
- ✅ [post] open_scene Assets/_LanbaiTest/GateTest_play.unity（260.2 ms）
- ✅ [post] add_component （0.5 ms）
- ✅ [post] save_scene （89.7 ms）

## 截图
| 机位 | t | 尺寸 | APL | < 12 % | 参考 APL | 文件 |
|---|---|---|---|---|---|---|
| key | 154.5 | 2,560×1,072 | 38.38 | 18.09 | 34.88 | `shots/key_unity_t154.50.png` |
| U7 | 155.1 | 1,920×1,080 | 35.8 | 19.89 | 29.39 | `shots/U7_unity_t155.10.png` |
| U8fwd | 169.65 | 1,920×1,080 | 51.62 | 13.92 | 40.94 | `shots/U8fwd_unity_t169.65.png` |
| U8side | 166.45 | 1,920×1,080 | 15.77 | 45.1 | 20.65 | `shots/U8side_unity_t166.45.png` |
| rear | 177.55 | 1,920×1,080 | 20.53 | 29.23 | 29.43 | `shots/rear_unity_t177.55.png` |
| U7_stereo |  | 3,840×1,080 |  |  |  | `stereo/U7_approx_LR.png` 双眼近似：两台普通相机各偏 ±32 mm 分别渲染、左右并排；不是 SPS-I 单通道立体，不是头显测试 |
| U8fwd_stereo |  | 3,840×1,080 |  |  |  | `stereo/U8fwd_approx_LR.png` 双眼近似：两台普通相机各偏 ±32 mm 分别渲染、左右并排；不是 SPS-I 单通道立体，不是头显测试 |

## 动态序列（闪烁）
编辑器里普通相机逐帧渲染。**闪烁看 `shimmer`**：每帧同一姿态另渲一张高倍超采样的参考，量“测的图 − 参考”的亮度差（0–255）随时间的抖动，真实运动不算在里面。`motion_std` 含真实运动、`hf_raw` 也会混进正常的边缘运动，只作参考。`static` 序列是相机不动的对照（只剩画面本身的时间噪声）。热图在 `seq/<id>/heat_*.png`。**这是近似，不是头显。**

| 序列 | 种类 | 帧 | shimmer 平均 / p99 / 超阈值 | motion_std 平均 | hf_raw 平均 / p99 | APL 最小 / 最大 / 最大跳变 |
|---|---|---|---|---|---|---|
| U7_micro | micro_motion | 90 | 1.44 / 14.14 / 7.066 % | 3.78 | 1.32 / 13.37 | 35.76 / 36.37 / 0.04 |
| U7_static | static | 45 | 0.72 / 1.08 / 0 % | 0.63 | 0.64 / 1.01 | 35.98 / 35.98 / 0 |
| U8fwd_micro | micro_motion | 90 | 1.47 / 13.47 / 7.699 % | 5.81 | 1.46 / 13.69 | 51.06 / 51.71 / 0.51 |
| deck_roll | time | 61 | 1.27 / 11.96 / 5.747 % | 3.63 | 1.15 / 9.95 | 39.54 / 40.85 / 0.04 |

## 性能（编辑器估算，不是头显）
| 项 / 状态 | t | 电脑 1920×1080 ms | VR 估算 ms（CPU） | draw call | SetPass | 三角面 |
|---|---|---|---|---|---|---|
| U7 / all_on | 155.1 | 5.2 | 11.62（3.68） | 没量到 | 没量到 | 没量到 |
| U7 / deck_off | 155.1 | 3.4 | 6.42（3.62） | 没量到 | 没量到 | 没量到 |
| U7 / clouds_off | 155.1 | 3.52 | 6.21（3.24） | 没量到 | 没量到 | 没量到 |
| U7 / auto_lite | 155.1 | 5.32 | 11.66（3.88） | 没量到 | 没量到 | 没量到 |
| U8fwd / all_on | 169.65 | 4.96 | 12.11（3.47） | 没量到 | 没量到 | 没量到 |
| U8fwd / deck_off | 169.65 | 3.05 | 6.93（3.29） | 没量到 | 没量到 | 没量到 |
| U8fwd / clouds_off | 169.65 | 3.03 | 6.62（3.03） | 没量到 | 没量到 | 没量到 |
| U8fwd / auto_lite | 169.65 | 5.22 | 11.97（3.38） | 没量到 | 没量到 | 没量到 |

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了
- ✅ lights_linear_intensity：GraphicsSettings.lightsUseLinearIntensity = True（要 True）

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，7 条）：`Assets/Lanbai/Tests/**`、`Assets/Lanbai/GateClouds/Generated/**`、`Assets/Lanbai/GateClouds/Textures/**`、`Assets/Lanbai/GateClouds/GateClouds_Layout.json`、`Assets/Lanbai/UdonPrograms/**`、`Assets/Lanbai/Gate/Generated/**`、`Assets/SerializedUdonPrograms/**`。为什么：沙盒规则的例外：门测试本来就是这些搭建脚本搭的（LB_GateTest.Build 存 GateTest.unity 和 Tests/GateTest_Materials/；蓝白/Gate Clouds/Build 建 Generated/、设贴图导入、建 U# 程序资产；auto_lite 那一档临时改 GateClouds_Layout.json，量完逐字节写回）。别的地方被改就算没声明的写入；U# 编译把程序的序列化结果写进 Assets/SerializedUdonPrograms/（和 UdonPrograms 一起）
- 开搭之前原样备份进 `backup_before/` 的：`Assets/Lanbai/Tests/**`、`Assets/Lanbai/GateClouds/GateClouds_Layout.json`、`Assets/Lanbai/UdonPrograms/**`、`Assets/SerializedUdonPrograms/**`
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：23 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：56 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 0 条。

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 云海滚 10 秒（Play，时钟在走）：远处的细银边、月光路、裂口脚下一像素宽的细银边，爬不爬、闪不闪
- [ ] 闭左眼、闭右眼各看一遍（云海的抖动已改成两只眼一致、锁在世界上）
- [ ] 179.4–181.6 往后窗看一眼，报看到什么（臂在 U9 − 0.05 消失；回头看云海是不是一下子没了）
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）Udon 时间（ClientSim + Profiler）：工具跑完会把搭好的场景另存成 Assets/_LanbaiTest/GateTest_play.unity 并加上 VRC 场景描述符（只在沙盒里）；菜单跑完它就是打开着的场景（批处理跑完就在 Unity 里打开它）。在它里面把 Gate_TestClock 的 startT 改成 147，按 Play，等 ClientSim 起来，用 Profiler 量 LanbaiGateDriver、LanbaiGateClouds 各占多少 ms：U7 150.3、U8 166.15、约 178；看 147.8 和时钟循环回跳那一帧有没有尖峰。沙盒下次跑测试时会被删掉，量完不用留
- [ ] （手动）GPU Profiler / Frame Debugger（或 RenderDoc）：U7 全开那一帧，最贵的几项、云海那一项各占多少 ms（编辑模式：先 LB_GateTest.StatsBegin("cam=U7") 把参考相机摆好，在 Game 视图里抓，不要进 Play）
- [ ] （手动）Frame Debugger 里看一眼 UpdateDepthTexture 有没有画云海（ShadowCaster pass）
- [ ] （手动）蓝白/Grades/Probe Bloom Colour：要测试卡的场景，门测试场景里跑不了，单独跑一次，把 LanbaiReports/BloomColour_Report.md 一起推
- [ ] （手动）每张图按 gate_metrics.py / lbh_grade.py 量的 metrics_unity_vs_render.json：云端拿到截图后做（Blender 离线那一层）
