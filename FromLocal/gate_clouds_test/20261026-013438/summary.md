# Gate before approved r10 update: same isolated test/perf setup · 20261026-013438

**✅ 跑完了，工具的检查全过（退出码 0）：待总导演看图，不是验收通过**

- 测试：`gate_clouds_test`（HANDOFF_LOG 2026-10-24「门的云 GateClouds v1.5 合进 main」全条 + 「门的总驱动 LanbaiGateDriver 合进 main」+「门的云第 10 轮第 1 批」（_Stars 0.055、38 张云卡））
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **pass（工具检查全过，待总导演看图）**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:30:31.023819-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/GateTest_play.unity；用时 18 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\gate_clouds_test\20261026-013438` 拷到仓库的 `FromLocal/gate_clouds_test/20261026-013438/`，再推。看到的问题写进 `FromLocal/gate_clouds_test/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ⚠️ warn | `U7_vr_budget` | 11.55 | ≤ 8.3（不卡） | 第 4 幕预算 8.3 ms（10-08 不带云的 VR 估算已经是 10.3 ms）。编辑器估算只报不卡：超了照实推，总导演按圣经 §1.9 定砍什么 |
| ⚠️ warn | `U8fwd_vr_budget` | 11.79 | ≤ 8.3（不卡） | 同上 |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |
| ✅ pass | `setting_lights_linear_intensity` | 1 | = 1 | GraphicsSettings.lightsUseLinearIntensity = True（要 True） |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 67.8 GB，可用内存 14.6 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 3 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:30:31.023819-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
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
- ✅ [build] Lanbai.Tests.LB_GateTest.Build(155.1)（498.2 ms）
- ✅ [build] set_light Gate_Lights/Fill_from_below（1.3 ms）
- ✅ [build] 材质 ：_HazeNear = [0.1085,0.113,0.1641]，_HazeFar = [0.0436,0.0504,0.0726]，_BandEl = [6,22,2]（4 ms）
- ✅ [build] 材质 Assets/Lanbai/Tests/GateTest_Materials/M_GateAirSky.mat：_Stars = 0.055（0.3 ms）
- ✅ [build] 菜单 蓝白/Gate Clouds/Build（1,045 ms）
- ✅ [build] assert_log （0.2 ms）
- ✅ [build] Lanbai.Tests.LB_GateTest.Apply(155.1)（11 ms）
- ✅ [build] 菜单 蓝白/Gate/Build Driver + Test Clock (Play mode only)（7,722 ms）
- ✅ [build] assert_log （0 ms）
- ✅ [after_build] assert_no_component （0.8 ms）
- ✅ [after_build] assert_renderer **/Tear_CloudGlow = false（0.4 ms）
- ✅ [after_build] assert_renderer **/Tear_CloudGlow_Additive = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Tear_LightLane = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Shaft_00 = false（0.1 ms）
- ✅ [after_build] assert_renderer **/Shaft_01 = false（0.1 ms）
- ✅ [after_build] assert_renderer **/GateBeam_Shaft_00 = true（0.1 ms）
- ✅ [after_build] assert_renderer **/GateBeam_Shaft_01 = true（0.1 ms）
- ✅ [after_build] assert_light Gate_Lights/Tear_CabinOnly（0.3 ms）
- ✅ [after_build] assert_light Gate_Lights/Fill_from_below（0.1 ms）
- ✅ [after_build] collect （9.6 ms）
- ✅ [after_build] collect （9.3 ms）
- ✅ [after_build] collect （9.3 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(155.1)（13.4 ms）
- ✅ [time] Lanbai.Tests.LB_GateTest.Apply(169.65)（12 ms）
- ✅ [post] save_scene_copy （64.9 ms）
- ✅ [post] open_scene Assets/_LanbaiTest/GateTest_play.unity（247.5 ms）
- ✅ [post] add_component （0.7 ms）
- ✅ [post] save_scene （94.7 ms）

## 性能（编辑器估算，不是头显）
| 项 / 状态 | t | 电脑 1920×1080 ms | VR 估算 ms（CPU） | draw call | SetPass | 三角面 |
|---|---|---|---|---|---|---|
| U7 / all_on | 155.1 | 5.02 | 11.55（3.38） | 没量到 | 没量到 | 没量到 |
| U8fwd / all_on | 169.65 | 4.85 | 11.79（3.25） | 没量到 | 没量到 | 没量到 |

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了
- ✅ lights_linear_intensity：GraphicsSettings.lightsUseLinearIntensity = True（要 True）

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，7 条）：`Assets/Lanbai/Tests/**`、`Assets/Lanbai/GateClouds/Generated/**`、`Assets/Lanbai/GateClouds/Textures/**`、`Assets/Lanbai/GateClouds/GateClouds_Layout.json`、`Assets/Lanbai/UdonPrograms/**`、`Assets/Lanbai/Gate/Generated/**`、`Assets/SerializedUdonPrograms/**`。为什么：沙盒规则的例外：门测试本来就是这些搭建脚本搭的（LB_GateTest.Build 存 GateTest.unity 和 Tests/GateTest_Materials/；蓝白/Gate Clouds/Build 建 Generated/、设贴图导入、建 U# 程序资产；auto_lite 那一档临时改 GateClouds_Layout.json，量完逐字节写回）。别的地方被改就算没声明的写入；U# 编译把程序的序列化结果写进 Assets/SerializedUdonPrograms/（和 UdonPrograms 一起）
- 开搭之前原样备份进 `backup_before/` 的：`Assets/Lanbai/Tests/**`、`Assets/Lanbai/GateClouds/GateClouds_Layout.json`、`Assets/Lanbai/UdonPrograms/**`、`Assets/SerializedUdonPrograms/**`
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：1 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：77 个（清单在 manifest.json 的 writes.tool_touched_restored）
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
