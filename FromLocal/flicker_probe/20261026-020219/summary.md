# flicker_dusk_front · 20261026-020219

**✅ 跑完了，工具的检查全过（退出码 0）：待总导演看图，不是验收通过**

- 测试：`flicker_probe`（Approved 1.2.2 scoped flicker probe; actual saved FullPreview; as-is only, legacy diagnostic toggles are not relevant to delivered replacement.）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **pass（工具检查全过，待总导演看图）**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/Lanbai_FullPreview_copy.unity；用时 26 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\flicker_probe\20261026-020219` 拷到仓库的 `FromLocal/flicker_probe/20261026-020219/`，再推。看到的问题写进 `FromLocal/flicker_probe/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `play_ppv2_effective` | 1 | = 1 | Play 里拍的画面经过了 PPv2（开 / 关各渲一张，要不一样）；没生效，曲线就是没调色的画面 |
| ✅ pass | `probe_f12_as_is_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 67.1 GB，可用内存 13.9 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 41 条，原样在 console.jsonl）
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

## 闪烁探测（Play 模式，30 fps）
帧间的量只用有效的相邻两帧（中间没漏拍、实际间隔 ≤ 1.5 × 1/fps）；每个变体之前，上一个变体关掉的东西逆序还原。一次跑一组变体：每个变体把同一段重拍一遍，只差 `toggles` 里关掉的那一样。看 `max_step_ev` 和 `flicker_px_frac` 哪个变体明显变小；局部的闪看每个变体的 `flicker_count.png`（相邻帧差 > 24 的次数）和 `diff_*_heat.png`（差最大的 8 对）。**探测不改、不删任何东西**：退出 Play 就全回去了。

| 探测 | 变体 | 关了什么 | 相邻两帧最大差 EV | > 0.1 EV 的次数 | 局部闪的像素占比 | 实际帧率 / 漏拍比例 | 图 |
|---|---|---|---|---|---|---|---|
| f12 | as_is | （都开着） | 0.08 | 0.00 | 0.00 | 4.00 / 0.00 | `probe/f12/as_is/` |

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，0 条）：没有。为什么：同上
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：4 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## 警告
- 批处理下进 Play 模式没在阿白的机器上试过；不行就用菜单跑

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 1 条，前几条：
  - `[Lanbai Bus Slice] ERROR built Lanbai_BusSlice: 1 error(s), 1 warning(s)`

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）结果和录屏一起放进 FromLocal/flicker_1025/<时间>/；工具只拍主座位往前，闪在别的方向就把 camera 的 yaw / pitch 改了再跑
