# 车厢先交：FullPreview 里换上新车（D-44） · 20261026-023121

**✅ 跑完了，工具的检查全过（退出码 0）：待总导演看图，不是验收通过**

- 测试：`bus_dropin`（车包 Bus/Docs~/D44_车厢先交.md §8 第 2 条的草稿；总工程师 10-25 审过放进来）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **pass（工具检查全过，待总导演看图）**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/Lanbai_FullPreview_copy.unity；用时 5.8 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\bus_dropin\20261026-023121` 拷到仓库的 `FromLocal/bus_dropin/20261026-023121/`，再推。看到的问题写进 `FromLocal/bus_dropin/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 65.6 GB，可用内存 12.5 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 7 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:39:27.181258-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件夹 Assets/Lanbai/Common
- ✅ 文件夹 Assets/Lanbai/Bus
- ✅ 文件夹 Assets/Lanbai/Bus/Editor
- ✅ 文件夹 Assets/Lanbai/Cabin
- ✅ 文件 Assets/Lanbai/Scenes/Lanbai_FullPreview.unity
- ✅ 类型 LanbaiBusCabinDropIn
- ✅ 类型 LanbaiCabinDriver

## 步骤
- ✅ [build] LanbaiBusCabinDropIn.BuildAll()（3,705 ms）
- ✅ [build] LanbaiBusCabinDropIn.Check()（174.8 ms）
- ✅ [after_build] assert_object **/Lanbai_Bus/Model_PAZ672（0.1 ms）
- ✅ [after_build] assert_object **/Lanbai_Bus/LanbaiCabinDriver（0.1 ms）

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，5 条）：`Assets/Lanbai/Bus/Generated/**`、`Assets/Lanbai/Bus/Generated.meta`、`new:Assets/Lanbai/Bus/Programs/**`、`new:Assets/Lanbai/Bus/Programs.meta`、`new:Assets/SerializedUdonPrograms/**`。为什么：材质写进 Bus/Generated/Materials（重搭会改，放开）。草稿里的 Assets/Lanbai/UdonPrograms/** 拿掉了：udon_programs 列的程序资产工具在记快照之前就建好，搭建期间那里再有写入就是真的意外（比如改了别的脚本的程序资产），要报出来。Bus/Programs 和 SerializedUdonPrograms 只放过“新建”（new:）：万一搭建脚本自己建了程序资产、U# 编译写了新的序列化程序，算声明过；已有的文件被改或被删照常报。重存但逐字节没变的文件工具 1.2.2 起不算改动
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：56 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 0 条。

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
