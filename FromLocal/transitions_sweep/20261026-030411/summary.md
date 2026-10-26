# Affected-window supplement: x06 missed frames; cabin cube; preview white tone-map continuity · 20261026-030411

**❌ 跑完了，有检查没过（退出码 1）**

- 测试：`transitions_sweep`（D-44 #4：按圣经 §6.x 的交接表，每个交接前后各 7 秒；主座位每秒一张、交接点前后 1 秒 10 fps；出对比图和每帧平均对数亮度曲线，量出跳变；有意的硬切单独标）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **fail**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/Lanbai_FullPreview_copy.unity；用时 108.9 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\transitions_sweep\20261026-030411` 拷到仓库的 `FromLocal/transitions_sweep/20261026-030411/`，再推。看到的问题写进 `FromLocal/transitions_sweep/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ❌ fail | `no_undeclared_writes` | 1 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `play_ppv2_effective` | 1 | = 1 | Play 里拍的画面经过了 PPv2（开 / 关各渲一张，要不一样）；没生效，曲线就是没调色的画面 |
| ✅ pass | `sweep_x02_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x06_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x12_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x38_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x39_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x40_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.4 GB，E:\ 剩 66.3 GB，可用内存 12.7 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 23 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:39:27.181258-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件 Assets/Lanbai/Scenes/Lanbai_FullPreview.unity
- ✅ 类型 LB_Journey
- ✅ 类型 LanbaiOverlay
- ✅ 类型 LanbaiActDispatcher

## 交接扫描（Play 模式，主座位；全画面的平均对数亮度）
每个交接前后各 7 s：每秒一张（`strip_1s.png`），交接点前后 1 s 每 0.1 s 一张（`strip_fine.png`），曲线 `curve.png`（红线 = 交接时刻，纵轴 −8 … 0 EV）。**有意的**（剪 1–3、第 5 幕的黑、U9 的闪、FLASH_TEAR）单独标出，不算技术跳变。圣经 §1.8 的限速是每个视向的，这里是全画面平均，只用来找“哪里跳了”，不是验收。

| # | 交接 | t | 类别 | 相邻两张最大差 EV | 0.25 s 升 | 1 s 升 | 2 s 升 | 漏拍比例 | 图 |
|---|---|---|---|---|---|---|---|---|---|
| x02 | 开车 | 17.5 |  | 0.11 | 0.03 | 0.03 | 0.03 | 0.00 | `sweep/x02/` |
| x06 | 触云 | 99.5 |  | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | `sweep/x06/` |
| x12 | 4 → 4c：U9 管灯一闪 → 全灭 | 179.55 | **授权的闪（有意）** | 2.60 | 0.59 | 0.73 | 0.83 | 0.00 | `sweep/x12/` |
| x38 | 11 → 12：第二次白 | 1240.46 |  | 0.83 | 0.17 | 0.83 | 1.61 | 0.00 | `sweep/x38/` |
| x39 | 剪 3（S12） | 1251.96 | **硬切（有意）** | 1.45 | 0.00 | 0.52 | 0.95 | 0.00 | `sweep/x39/` |
| x40 | 收缩进站灯 | 1254.96 |  | 1.46 | 0.00 | 0.36 | 0.36 | 0.00 | `sweep/x40/` |

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，0 条）：没有。为什么：Play 模式只在内存里跑，不应该写工程里的文件；写了就会列成没声明的写入
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：1**：改了 Assets/Lanbai/Generated/Materials/LB_Tentacle.mat
- 工具临时改过、已改回的（不算没声明的写入）：4 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## 警告
- 批处理下进 Play 模式没在阿白的机器上试过；不行就用菜单跑

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 0 条。

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 交接扫描只看全画面平均和主座位往前：转头、头显里的感受另看
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）跑之前：全程预览场景能正常 Play（ClientSim 起来、旅程走），Console 没有编译错误
- [ ] （手动）跑的时候别碰编辑器：工具自己进 Play、跳转、拍、退出 Play，约 10 分钟
