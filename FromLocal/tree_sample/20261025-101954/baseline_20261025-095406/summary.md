# 样板树（D-44 #6）：三个对照机位 + 主座位 20 px/° 近景 + 头部微动的闪烁序列 + 性能 · 20261025-095406

**❌ 跑完了，有检查没过（退出码 1）**

- 测试：`tree_sample`（总导演 D-44 #6、10-25 选形（A 为主、B 点缀）；Lamps/Tree/README_样板树.md；FromLocal/trees/README.md 的机位与位置）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **fail**；头显 **not_tested**（工具不测头显）
- 工具 1.2.1，Unity 2022.3.22f1（菜单），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `f703a951cbadf0eb6bc4df263f6d315e298dd0fc`，2026-10-25T00:13:19.2541837-04:00 同步，条目「D-41 common Udon program repair and Engineering/UnityTest」
- 场景：Assets/_LanbaiTest/Lanbai_copy.unity；用时 1.2 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\tree_sample\20261025-095406` 拷到仓库的 `FromLocal/tree_sample/20261025-095406/`，再推。看到的问题写进 `FromLocal/tree_sample/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ❌ fail | `steps_ok` | 1 | = 0 | 每一步都跑成功了 |
| ❌ fail | `no_undeclared_writes` | 33 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ❌ fail | `hero_shimmer` | — | 12 | 初值：叶缘在 4× 超采样参考下的差，p99 ≤ 12（0–255）。第一次实测后由总工程师定 没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错） |
| ❌ fail | `hero_shimmer_frac` | — | 0.02 | 超过阈值 4 的像素 ≤ 2 % 没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错） |
| ❌ fail | `right_shimmer_frac` | — | 0.02 | 远树（LOD1 / LOD2）同样不能闪 没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错） |
| ⚠️ warn | `overview_apl` | — | （不卡） | 圣经第 1 幕 APL 22；这个机位里有车和灯，只作参考 没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错） |
| ⚠️ warn | `row_tris` | — | 400000（不卡） | 整个画面的三角面，参考；7 棵树 LOD0 合计约 6 万 没量到（这一项的截图 / 序列 / 性能没跑成，或名字写错） |
| ✅ pass | `no_compile_errors` | 0 | = 0 | 跑的过程中没有新的编译错误 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_console_errors` | 0 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.4 GB，E:\ 剩 70.6 GB，可用内存 10.2 GB
- ✅ consent：用户（当前聊天） 2026-10-25 同意（工具 1.2.1，测试 gate_clouds_test、tree_sample）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
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
- ✅ sync_record：仓库提交 f703a951cbadf0eb6bc4df263f6d315e298dd0fc（2026-10-25T00:13:19.2541837-04:00 同步，条目：D-41 common Udon program repair and Engineering/UnityTest）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件夹 Assets/Lanbai/Common
- ✅ 文件夹 Assets/Lanbai/Grading
- ✅ 文件夹 Assets/Lanbai/Lamps/Tree
- ✅ 文件 Assets/Lanbai/Scenes/Lanbai.unity
- ✅ 文件 Assets/Lanbai/Lamps/Tree/Models/Tree_A1.fbx
- ✅ 文件 Assets/Lanbai/Lamps/Tree/Models/Tree_A2.fbx
- ✅ 文件 Assets/Lanbai/Lamps/Tree/Models/Tree_A3.fbx
- ✅ 文件 Assets/Lanbai/Lamps/Tree/Models/Tree_B1.fbx
- ✅ 类型 Lanbai.Lamps.LanbaiTreeBuilder
- ✅ 类型 Lanbai.Grading.LanbaiGradeBuilder
- ✅ 菜单 蓝白/Build/Sample Trees

## 步骤
- ✅ [build] 菜单 蓝白/Build/Sample Trees（515.9 ms）
- ❌ [build] Lanbai.Grading.LanbaiGradeBuilder.Solo(S1)（8.2 ms）
  - **返回里没有「solo S1」：no volumes: run Build Profiles & Volumes first**
- ⏭️ [build] set_field_objects_active  = false
- ⏭️ [build] Lanbai.Lamps.LanbaiTreeBuilder.TestRow()
- ⏭️ [build] assert_object Lanbai_TreeTestRow

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，2 条）：`Assets/Lanbai/Lamps/Tree/Generated/**`、`Assets/Lanbai/Lamps/Tree/Prefabs/**`。为什么：蓝白/Build/Sample Trees 只写这两处（材质、预制体）；导入设置由 LanbaiTreeImport 在 Lamps/Tree/ 里改
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：20 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：33**：改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip1_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip1_Hang.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip1_Sheet.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip2_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip2_Hang.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip2_Sheet.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip2_Threads.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip3_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip3_Hang.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip3_Sheet.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip3_Threads.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip6_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip6_Hang.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip6_Sheet.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip6_Threads.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip7_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip7_Hang.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip7_Sheet.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip8_Ply0_Fringe.mat；改了 Assets/Lanbai/Act04c_Inside/Materials/M_04c_Lip8_Ply0_Sheet.mat …
- 工具不保存场景。

## 警告
- 搭建有一步失败，后面的截图、序列、性能都没做

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 6 条，前几条：
  - `Selected texture format 'RGB(A) Compressed BC7' for platform 'DefaultTexturePlatform' is not valid with the current texture type 'Default'.`
  - `Selected texture format 'RGB(A) Compressed BC7' for platform 'DefaultTexturePlatform' is not valid with the current texture type 'Default'.`
  - `ImportFBX Errors:`
  - `ImportFBX Errors:`
  - `ImportFBX Errors:`
  - `ImportFBX Errors:`

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 坐在主座位看右手第一棵树：叶簇边缘不爬、不闪；风是慢的摆，不是抖
- [ ] 两只眼各闭一次：叶卡、剪影卡（远处）两眼一致（alpha-to-coverage 需要 MSAA：VRChat 默认开）
- [ ] 钠灯下：迎灯的叶团是暗的橄榄 / 琥珀，不是亮绿；其余是剪影，比背后的天暗
- [ ] 远处的树（LOD2 两张交叉卡）走过去时不读成两块板
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）Frame Debugger 看一棵 LOD0：两个 draw（树皮、叶），叶在 AlphaTest 队列、AlphaToMask 开
