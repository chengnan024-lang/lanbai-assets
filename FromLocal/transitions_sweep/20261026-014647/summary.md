# 全片交接扫描（Play 模式，主座位，每个交接前后各 7 s） · 20261026-014647

**❌ 跑完了，有检查没过（退出码 1）**

- 测试：`transitions_sweep`（D-44 #4：按圣经 §6.x 的交接表，每个交接前后各 7 秒；主座位每秒一张、交接点前后 1 秒 10 fps；出对比图和每帧平均对数亮度曲线，量出跳变；有意的硬切单独标）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **fail**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/Lanbai_FullPreview_copy.unity；用时 586.6 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\transitions_sweep\20261026-014647` 拷到仓库的 `FromLocal/transitions_sweep/20261026-014647/`，再推。看到的问题写进 `FromLocal/transitions_sweep/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ❌ fail | `no_exceptions` | 1 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ❌ fail | `sweep_x07_missed` | 0.18 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x11_missed` | 0.82 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x13_missed` | 0.94 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x17_missed` | 0.94 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x18_missed` | 0.85 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x18b_missed` | 0.91 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ❌ fail | `sweep_x40_missed` | 0.88 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `play_ppv2_effective` | 1 | = 1 | Play 里拍的画面经过了 PPv2（开 / 关各渲一张，要不一样）；没生效，曲线就是没调色的画面 |
| ✅ pass | `sweep_x01_missed` | 0.09 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x02_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x03_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x04_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x06_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x09_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x12_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x16_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x19_missed` | 0.03 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x21a_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x21b_missed` | 0.03 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x22_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x23a_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x24_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x24a1_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x24a2_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x24a3_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x24c_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x26_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x29_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x30_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x31_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x32_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x34_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x35_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x36_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x37_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x38_missed` | 0 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |
| ✅ pass | `sweep_x39_missed` | 0.06 | ≤ 0.1 | 漏拍的比例（实时拍不满）；超过门槛，这一段的帧间量不能信 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 67.7 GB，可用内存 14.5 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 42 条，原样在 console.jsonl）
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
| x01 | 1 → 2：声音先到（S1 → S2） | 3.9 |  | 0.05 | 0.00 | 0.01 | 0.01 | 0.09 | `sweep/x01/` |
| x02 | 开车 | 17.5 |  | 0.05 | 0.01 | 0.01 | 0.01 | 0.00 | `sweep/x02/` |
| x03 | 2 → 3：灯尽（S3 0 → 0.3） | 39.1 |  | 0.05 | 0.01 | 0.03 | 0.03 | 0.00 | `sweep/x03/` |
| x04 | 声音打开 / 3a 一次升起 | 50.3 |  | 0.03 | 0.02 | 0.03 | 0.04 | 0.06 | `sweep/x04/` |
| x06 | 触云 | 99.5 |  | 0.12 | 0.02 | 0.03 | 0.03 | 0.00 | `sweep/x06/` |
| x07 | 入云（S3 0.3 → 1；R_Road → R_Night） | 107.5 |  | 0.12 | 0.01 | 0.01 | 0.01 | 0.18 | `sweep/x07/` |
| x09 | 破云（EXPO_UP +0.5 EV） | 129.1 |  | 0.52 | 0.43 | 0.44 | 0.44 | 0.00 | `sweep/x09/` |
| x11 | 3 → 4（S4；光雾带） | 133.8 |  | 0.18 | 0.00 | 0.18 | 0.18 | 0.82 | `sweep/x11/` |
| x12 | 4 → 4c：U9 管灯一闪 → 全灭 | 179.55 | **授权的闪（有意）** | 1.71 | 2.04 | 2.04 | 2.04 | 0.00 | `sweep/x12/` |
| x13 | S4 → S4c | 180.05 |  | 0.35 | 0.00 | 0.00 | 0.00 | 0.94 | `sweep/x13/` |
| x16 | 4c → 5：FLASH_TEAR → 黑 | 247.89 | **授权的闪（有意）** | 2.69 | 0.79 | 1.55 | 1.55 | 0.00 | `sweep/x16/` |
| x17 | 剪 1（S4c → S6） | 248.64 | **硬切（有意）** | 0.00 | 0.00 | 0.00 | 0.00 | 0.94 | `sweep/x17/` |
| x18 | 5 → 6：第 5 幕的黑结束、日出预滚 | 252.64 | **第 5 幕的黑（有意）** | 0.15 | 0.00 | 0.15 | 0.26 | 0.85 | `sweep/x18/` |
| x18b | 日出曲线（254.14 → 266.34） | 254.14 |  | 0.32 | 0.00 | 0.32 | 0.43 | 0.91 | `sweep/x18b/` |
| x19 | 云塔应答（F0s） | 266.36 |  | 0.63 | 0.11 | 0.62 | 1.25 | 0.03 | `sweep/x19/` |
| x21a | 太阳被云盖挡住 | 305.4 |  | 0.08 | 0.01 | 0.01 | 0.02 | 0.00 | `sweep/x21a/` |
| x21b | 太阳重现（F1b1） | 318.36 |  | 0.04 | 0.06 | 0.18 | 0.22 | 0.03 | `sweep/x21b/` |
| x22 | 6 → 7a：入水（EXPO_DOWN −0.5） | 363.26 |  | 1.10 | ⚠️ 0.59 | ⚠️ 1.07 | 1.08 | 0.06 | `sweep/x22/` |
| x23a | 光柱汇成一束 | 453 |  | 0.13 | 0.00 | 0.13 | 0.16 | 0.06 | `sweep/x23a/` |
| x24 | 7a → 7b | 474.36 |  | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | `sweep/x24/` |
| x24a1 | 间奏 F3e1：斯涅尔之窗最后一闪 | 506.36 |  | 0.59 | 0.00 | 0.03 | 0.44 | 0.00 | `sweep/x24a1/` |
| x24a2 | 间奏 F3e2：海脊石壁 | 532.36 |  | 0.03 | 0.00 | 0.00 | 0.00 | 0.00 | `sweep/x24a2/` |
| x24a3 | 间奏 F3e3：最后的藍熄灭 | 556.36 |  | 0.05 | 0.00 | 0.00 | 0.00 | 0.00 | `sweep/x24a3/` |
| x24c | 宫殿成了头顶的星座（F7p） | 812.36 |  | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 | `sweep/x24c/` |
| x26 | 7 → 8：出海（EXPO_DOWN 钉住 → 放开） | 922.36 |  | 1.39 | 0.38 | 0.69 | 0.72 | 0.06 | `sweep/x26/` |
| x29 | 8-i → 8-ii：头顶的海溶化 | 956.36 |  | 0.08 | 0.08 | 0.09 | 0.17 | 0.00 | `sweep/x29/` |
| x30 | 8 → 8b：日线收缩 | 987.06 |  | 0.19 | 0.00 | 0.10 | 0.18 | 0.00 | `sweep/x30/` |
| x31 | 8b → 9a：蓝时结束 | 1001.21 |  | 0.92 | 0.01 | 0.02 | 0.02 | 0.00 | `sweep/x31/` |
| x32 | 9b：F13 按光源点燃 | 1018.21 |  | 0.38 | 0.12 | 0.30 | 0.60 | 0.00 | `sweep/x32/` |
| x34 | 第 1 面镜子的脉冲 | 1032.41 |  | 0.13 | 0.23 | 0.39 | 0.39 | 0.00 | `sweep/x34/` |
| x35 | 9c → 10：白（第 12 面） | 1137.58 |  | 0.61 | 0.24 | 0.99 | 1.55 | 0.00 | `sweep/x35/` |
| x36 | 剪 2（S10） | 1149.31 | **硬切（有意）** | 0.30 | 0.16 | 0.34 | 0.56 | 0.06 | `sweep/x36/` |
| x37 | 10 → 11：白收缩进灯里 | 1178.46 |  | 0.79 | 0.00 | 0.00 | 0.00 | 0.00 | `sweep/x37/` |
| x38 | 11 → 12：第二次白 | 1240.46 |  | 1.07 | 0.20 | 0.93 | 1.80 | 0.00 | `sweep/x38/` |
| x39 | 剪 3（S12） | 1251.96 | **硬切（有意）** | 0.55 | 0.00 | 0.16 | 0.16 | 0.06 | `sweep/x39/` |
| x40 | 收缩进站灯 | 1254.96 |  | 0.00 | 0.00 | 0.00 | 0.00 | 0.88 | `sweep/x40/` |

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，0 条）：没有。为什么：Play 模式只在内存里跑，不应该写工程里的文件；写了就会列成没声明的写入
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：4 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## 警告
- 批处理下进 Play 模式没在阿白的机器上试过；不行就用菜单跑

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 1 条，前几条：
  - `NullReferenceException: Object reference not set to an instance of an object`

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 交接扫描只看全画面平均和主座位往前：转头、头显里的感受另看
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）跑之前：全程预览场景能正常 Play（ClientSim 起来、旅程走），Console 没有编译错误
- [ ] （手动）跑的时候别碰编辑器：工具自己进 Play、跳转、拍、退出 Play，约 10 分钟
