# 门的云 GateClouds v1.5 + 门的总驱动 · 门测试场景 · 20261025-001331

**✅ 只做了预检：通过（没跑测试，不是测试通过）**

- 测试：`gate_clouds_test`（HANDOFF_LOG 2026-10-24「门的云 GateClouds v1.5 合进 main」全条 + 「门的总驱动 LanbaiGateDriver 合进 main」+「门的云第 10 轮第 1 批」（_Stars 0.055、38 张云卡））
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **not_tested（只做了预检）**；头显 **not_tested**（工具不测头显）
- 工具 1.0.0，Unity 2022.3.22f1（菜单），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `f703a951cbadf0eb6bc4df263f6d315e298dd0fc`，2026-10-25T00:13:19.2541837-04:00 同步，条目「D-41 common Udon program repair and Engineering/UnityTest」
- 场景：（没打开）；用时 0 s
- **交回**：把整个文件夹 `<project>\LanbaiReports/tests\gate_clouds_test\20261025-001331` 拷到仓库的 `FromLocal/gate_clouds_test/20261025-001331/`，再推。看到的问题写进 `FromLocal/gate_clouds_test/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 13.0 GB，E:\ 剩 85.8 GB，可用内存 10.0 GB
- ✅ consent：用户（当前聊天） 2026-10-25 同意；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 2 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Tests/GateTest.unity）
- ✅ sandbox：没有遗留的沙盒
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 f703a951cbadf0eb6bc4df263f6d315e298dd0fc（2026-10-25T00:13:19.2541837-04:00 同步，条目：D-41 common Udon program repair and Engineering/UnityTest）
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
