# Bus window framing calibration after FBX basis correction · 20261026-025548

**✅ 跑完了，工具的检查全过（退出码 0）：待总导演看图，不是验收通过**

- 测试：`bus_slice`（D-40 #1「车先出一个切片」；D-36 #1 近景按 VR 像素密度；D-40 #4 几何高光抗锯齿; local camera calibration only）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **pass（工具检查全过，待总导演看图）**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/bus_slice_new.unity；用时 2.2 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\bus_slice\20261026-025548` 拷到仓库的 `FromLocal/bus_slice/20261026-025548/`，再推。看到的问题写进 `FromLocal/bus_slice/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ⚠️ warn | `window_05_rear_coverage` | 0.13 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ⚠️ warn | `window_05_rear_upper_coverage` | 0.02 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ⚠️ warn | `window_05_front_upper_coverage` | 0.01 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ⚠️ warn | `window_10_rear_coverage` | 0.1 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ⚠️ warn | `window_10_rear_upper_coverage` | 0.07 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ⚠️ warn | `window_10_front_upper_coverage` | 0.06 | ≥ 0.3（不卡） | Calibration measurement; does not relax official gate |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `ppv2_effective` | 1 | = 1 | 截图经过了 PPv2（开 / 关 PPv2 各渲一张小图，要不一样） |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.4 GB，E:\ 剩 66.3 GB，可用内存 12.6 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 4 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:39:27.181258-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件夹 Assets/Lanbai/Common
- ✅ 文件夹 Assets/Lanbai/Bus
- ✅ 文件夹 Assets/Lanbai/Bus/Editor
- ✅ 类型 LanbaiBusSliceBuilder
- ✅ 菜单 蓝白/Build/车 切片

## 步骤
- ✅ [build] 菜单 蓝白/Build/车 切片（391.4 ms）
- ✅ [after_build] assert_object **/Slice_Seat（0.6 ms）
- ✅ [after_build] assert_object **/Slice_SideWindow（0.1 ms）
- ✅ [after_build] assert_object **/Slice_Pillar（0 ms）

## 截图
| 机位 | t | 尺寸 | APL | < 12 % | 参考 APL | 文件 |
|---|---|---|---|---|---|---|
| window_05_rear |  | 834×614 | 27.61 | 42.85 |  | `shots/window_05_rear.png` |
| window_05_rear_upper |  | 834×614 | 21.99 | 57.28 |  | `shots/window_05_rear_upper.png` |
| window_05_front_upper |  | 834×614 | 11.59 | 75.96 |  | `shots/window_05_front_upper.png` |
| window_10_rear |  | 834×614 | 21.03 | 56.37 |  | `shots/window_10_rear.png` |
| window_10_rear_upper |  | 834×614 | 18.48 | 65.98 |  | `shots/window_10_rear_upper.png` |
| window_10_front_upper |  | 834×614 | 11.86 | 75.37 |  | `shots/window_10_front_upper.png` |

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，3 条）：`Assets/Lanbai/Bus/Generated/**`、`Assets/Lanbai/UdonPrograms/**`、`Assets/SerializedUdonPrograms/**`。为什么：车的切片搭建菜单生成的网格、材质、贴图导入设置
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：11 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 0 条。

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 铬件、倒角、立柱稍远一点（1–2 m）时闪不闪（D-40 #4 的几何高光抗锯齿开着）
- [ ] 贴图在 0.5 m 处是不是糊、细节有没有被压没（mip 和压缩）
- [ ] 光照图接缝：座椅和侧窗框上看不看得到接缝
- [ ] 法线强度：凸起和缝线读得出来、又不像塑料
- [ ] 对照板第 5 栏「头显里一句话」：每件写一句
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）对照板五栏（D-40 #1）：真车照片 / Blender 中性光 / Blender 定稿 / Unity 截图（这次的 shots/）/ 头显里一句话
- [ ] （手动）Crunch 免不免由总导演定；免的话下载账总工程师重算（车的下载上限 75 MB）
