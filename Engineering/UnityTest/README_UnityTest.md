# 蓝白 · Unity 测试工具（`Engineering/UnityTest/`）

写的人：总工程师（`pkg/engineering`），2026-10-24。依据：总导演 D-40 #1、D-40a。给谁用：本地 Unity 操作的「阿白」，和读结果的云端会话。

**状态：工具写完了，没在 Unity 里编译过，也没在 Unity 里跑过。** C# 只过了 `Common/Tools~/compile_check`（Roslyn + 桩，见 §11）；同步脚本在 Linux 的 PowerShell 7.4 上用假仓库测过（§11），没在 Windows 的 PowerShell 5.1 上跑过。**工具完成 ≠ Unity 验收完成**：哪一项“过了”，只看阿白跑出来的报告。

一句话：一个测试 = `tests/<test-id>.json` 一个文件。工具读它，先做只读的预检，再在沙盒里按步骤搭场景、截图、录动态序列、量性能，最后写一个输出文件夹（`manifest.json`、`summary.md`、截图……），用退出码告诉你结果。同一个测试跑几遍都行，每次一个新文件夹。

---

## 0. 每次测试，阿白照这个做

1. 仓库：在 `E:\IDMdownload\VRCC\lanbai-assets` 里 `git pull`（要在 `main` 上）。**第一次会很大**（本地停在 29fa6f2，main 领先近 500 个提交，约 1.1 GiB）：让它跑完，别中途关掉；中途断了、留下 `.git\index.lock` 的话，同步脚本会停下（§2），不自动修。
2. 同步（§2）。先只列出，看一眼，再 `-Apply`：
   ```powershell
   cd E:\IDMdownload\VRCC\lanbai-assets
   powershell -ExecutionPolicy Bypass -File "Engineering\UnityTest\Tools~\lanbai_sync.ps1" -Project "<工程>"
   powershell -ExecutionPolicy Bypass -File "Engineering\UnityTest\Tools~\lanbai_sync.ps1" -Project "<工程>" -Apply
   ```
3. 打开 Unity，等导入、编译完。Console 里有编译错误就停：把 Console 原样推回来（工具的预检也会因为编译错误 BLOCKED）。
4. 跑测试：菜单 **蓝白/Test/Run gate_clouds_test**，或者关掉 Unity 用批处理（§3）。
5. 看退出码和 `summary.md`（§4）。
6. 把整个输出文件夹 `<工程>\LanbaiReports\tests\<test-id>\<时间>\` 拷到仓库的 `FromLocal\<test-id>\<时间>\`（同名，`manifest.json` 的 `fromlocal` 一栏写着），推。看到的问题写进 `FromLocal\<test-id>\问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议（`HANDOFF_CHATGPT.md` 的约定）。BLOCKED 的也推：报告里写着缺什么。
7. 头显里的那几项（`summary.md` 末尾的清单）工具不测，要人戴头显看，写一句话。

---

## 1. 文件

| 文件 | 是什么 |
|---|---|
| `Editor/LanbaiTestRunner.cs` | 入口：`Lanbai.Test.Runner.RunCli`（批处理）、`Runner.Run`（菜单也走它）；一次运行的流程、退出码、`LANBAI_TEST_RESULT` 那一行；场景（in_place / copy / new）和按路径找物体 |
| `Editor/LanbaiTestPreflight.cs` | 只读的预检、前置条件、只查不改的项目设置、沙盒、写入核对、检查项 |
| `Editor/LanbaiTestSteps.cs` | 步骤（菜单、静态方法、组件方法、开关物体、改材质、临时改 JSON、断言……），临时改的东西结束时改回 |
| `Editor/LanbaiTestCapture.cs` | 截图（ARGBHalf → PPv2 → 8 位，照门测试）、和参考图比、双眼近似、动态序列和闪烁热图、贴图压缩对照 |
| `Editor/LanbaiTestPerf.cs` | 性能（编辑器估算，测法照门测试的 `LB_GateTest.Perf`） |
| `Editor/LanbaiTestReport.cs` | 输出：`manifest.json`、`console.jsonl`、`perf.json`、`summary.md`、`result.json` |
| `Editor/LanbaiTestLog.cs` | Console 抓取（开跑前已有的 + 跑的过程中新来的 + 编译消息） |
| `Editor/LanbaiTestMenu.cs` | 菜单 蓝白/Test/… |
| `Editor/LanbaiTestJson.cs` | 小 JSON 读写 |
| `tests/*.json` | 测试定义（§6）：`gate_clouds_test`、`act06_dawn`、`bus_slice`、`act01_spawn`（占位）、`palace_hotspot`（占位） |
| `Tools~/lanbai_sync.ps1` | 仓库 → 工程的同步脚本（§2）。在 `~` 文件夹里，Unity 不导入 |

工程里的位置：`Assets/Lanbai/Engineering/UnityTest/`（同步脚本按 `X/...` → `Assets/Lanbai/X/...` 拷）。Editor 代码没有 asmdef，编进 `Assembly-CSharp-Editor`，和门测试脚本、各包的搭建脚本在同一个程序集里，互相调得到。

---

## 2. 同步脚本 `Tools~/lanbai_sync.ps1`

**只同步 HANDOFF_LOG 当前那一条点名的文件夹 / 文件。** 仓库里的 `X/...` 拷到工程的 `Assets/Lanbai/X/...`。

- 默认只列出（新增 `+`、覆盖 `~`、本地改过 `!`、仓库里没有了 `?`），什么都不改；加 `-Apply` 才动手。
- **原地覆盖**，从不删文件夹再拷：仓库里没有 `.meta`，资源的 GUID 在工程的 `.meta` 里，删了文件夹再拷 GUID 会变、引用会断。`.meta` 一概不碰。
- 开始前先查仓库：`.git\index.lock` 在、git 用不了、有没提交的改动、不在 `main` 上，都停下（退出码 4），什么都不改，也不自动修。
- 动手前，要覆盖的文件（连同 `.meta`）和上次的同步记录先打包进 `<工程>\LanbaiSyncBackup\<时间>.zip`。
- 同步记录 `Assets\Lanbai\.lanbai_sync.json`：仓库路径、提交号、分支、条目标题、每个文件上次同步时的 SHA-256。测试工具从这里读提交号写进 `manifest.json`（点开头的文件 Unity 不导入）。
- **本地改过的文件不覆盖、不删**（工程里的哈希和上次同步时的不一样，或者没有记录又和仓库不一样）：整次拒绝，退出码 2，什么都没改；确认要用仓库的版本就加 `-Force`（照样先进备份）。第一次同步时工程里已经有旧文件的，也会走到这一条。
- **从不自动删除。** 上次由它拷进去、现在仓库里没有了的文件只列出来（`?`），要删请在 Unity 的 Project 窗口里删（连 `.meta` 一起）。工程里本来就有的（各包的 `Generated/`、`UdonPrograms/*.asset`、本地自己加的）一概不动，只数一下。
- 永远不同步：仓库根上的单个文件、`FromLocal/`、`Art/`；任何一层叫 `Source`、`Renders`、`__pycache__` 的文件夹；`.py .pyc .blend .blend1 .ps1 .sh`。
- 每次的计划另存一份在 `<工程>\LanbaiReports\sync\<时间>_plan.json`。

**HANDOFF_LOG 的约定（给写条目的人）：** 条目里写一行“同步：”，路径都放反引号里；不要的写“不同步：”。
```
同步：`Gate/Runtime/` `Gate/Editor/` `Gate/GateDriver_Bake.json` `GateClouds/`
不同步：`Gate/Source/` `Gate/Renders/`
```
没有这一行的旧条目，脚本从反引号里猜（只认仓库里真有的路径；“不要拷 / 别拷 / 先别导入”后面的算排除），猜的要加 `-AcceptGuess` 才肯 `-Apply`。

| 参数 | |
|---|---|
| `-Project <路径>` | Unity 工程（必填） |
| `-Repo <路径>` | 仓库，默认 `E:\IDMdownload\VRCC\lanbai-assets` |
| `-Entry <n>` | HANDOFF_LOG 的第 n 条，1 = 最上面、最新的（默认） |
| `-EntryMatch <字>` | 标题里含这几个字的那一条 |
| `-Paths a/,b/c.json` | 不看 HANDOFF_LOG，直接指定。只在总导演 / 总工程师明说时用 |
| `-Apply` / `-Force` / `-AcceptGuess` | 见上 |

退出码：0 完成（或只列出）；1 没有可同步的（或猜的路径没加 `-AcceptGuess`）；2 本地改过的被拒绝；3 脚本出错；4 仓库状态不对（lock 文件、没提交的改动、不在 main）。

同步时 Unity 开着也可以（文件是原地覆盖的），但最好先关掉，或者至少别在它导入的时候同步；同步完回到 Unity 等它导入、编译完。

---

## 3. 跑测试

### 菜单
**蓝白/Test/Run gate_clouds_test**（以及 act06_dawn、bus_slice、act01_spawn、palace_hotspot）；**Run Other Test…** 列出 `tests/` 里所有的；**Preflight Only…** 只做预检。跑的时候编辑器不响应（几分钟），跑完弹一个框，可以直接打开输出文件夹。菜单跑完，测试场景留在打开的状态（没保存）；下次跑之前要么保存、要么点 **蓝白/Test/Discard Test Scene Changes**（只对沙盒里的拷贝和 `Assets/Lanbai/Tests/` 下的场景起作用），不然预检会因为“有没保存的改动”BLOCKED。

### 批处理（**要先关掉这个工程的 Unity 编辑器**）
同一个工程同一时间只能有一个 Unity 打开（编辑器开着时，批处理会报工程被占用、直接退出，日志里没有 `LANBAI_TEST_RESULT`）。这一条没在阿白的机器上试过；不想关编辑器就用菜单。
```powershell
$unity = "C:\Program Files\Unity\Hub\Editor\2022.3.22f1\Editor\Unity.exe"
$proj  = "D:\Unity\Lanbai"
$id    = "gate_clouds_test"
& $unity -batchmode -projectPath $proj -executeMethod Lanbai.Test.Runner.RunCli -lanbaiTest $id -logFile "$proj\LanbaiReports\tests\$id.log" | Out-Null
$code = $LASTEXITCODE; "退出码 $code"
Select-String -Path "$proj\LanbaiReports\tests\$id.log" -Pattern '^LANBAI_TEST_RESULT ' | Select-Object -Last 1
Get-Content "$proj\LanbaiReports\tests\$id\last_result.json"
```
- `| Out-Null` 是为了让 PowerShell 等 Unity 退出再往下走（不然 `$LASTEXITCODE` 拿不到）。
- **不要加 `-nographics`**：截图和性能要真的显卡（预检会因为没有显卡 BLOCKED）。不用加 `-quit`（工具自己退出）。
- 只做预检：末尾加 `-lanbaiPreflightOnly`。用别的测试定义文件：`-lanbaiTestFile <路径>`（代替 `-lanbaiTest`）。
- **PPv2 在批处理下生效没有，没验证过。** 工具每次第一张截图前自己查：同一机位开 / 关 PPv2 各渲一张小图，要不一样（检查项 `ppv2_effective`）。批处理下这一项没过的话，截图就是没调色的，**改用菜单跑**，其余照旧。
- 日志的最后几行可能是 Unity 自己退出时写的；结果那一行用上面的 `Select-String` 找，或直接读 `last_result.json`。

---

## 4. 退出码，以及每种怎么办

| 退出码 | 意思 | 阿白怎么办 |
|---|---|---|
| **0** | 全部跑完，检查全过 | 拷输出文件夹到 `FromLocal/`、推；头显清单另外看 |
| **1** | 跑完了，有检查没过（或有一步失败了） | 照样拷、推。**不要自己改数值、不要自己修**：`summary.md` 的“检查项”和“步骤”写着哪里没过，云端看了再定 |
| **2** | BLOCKED：预检或前置条件不满足，什么都没搭 | 看 `summary.md` 第一段的原因。能自己补的补上再跑（没同步的同步、Unity / 包版本不对的装对、有没保存的场景先存或放弃）；补不了的（比如车的切片还没交、占位测试）照样推报告 |
| **3** | 工具自己出了异常 | 推 `manifest.json`（`error`、`error_stack`）、`console.jsonl` 和 `-logFile` 的日志；照 §9 恢复后可以重跑一次。这是总工程师的 bug |
| 日志里**没有** `LANBAI_TEST_RESULT` | Unity 没走到工具：多半是启动时就有编译错误（`-executeMethod` 根本没执行），或者工程被另一个 Unity 开着 | 打开编辑器看 Console；把 `-logFile` 的日志原样推回来。按 BLOCKED 处理 |

`summary.md` 里“三层状态”：Blender 离线（云端填）、Unity 桌面（工具填，就是这个退出码）、头显（固定 `not_tested`，工具从不标成过）。

---

## 5. 输出：`<工程>/LanbaiReports/tests/<test-id>/<YYYYMMDD-HHMMSS>/`

| 文件 | |
|---|---|
| `manifest.json` | 机器读的全部：工具版本、测试 id、测试定义的 SHA-256、仓库提交（同步记录）、Unity / SDK / 包的版本、显卡、预检、前置条件、每一步的状态和用时、只查不改的设置、检查项、全部量数（`metrics`，每个量的说明在 `metric_notes`）、写入核对、警告、文件清单；三层状态在 `layers` |
| `summary.md` | 给人看的摘要：结果、检查项（没过的在前）、预检、步骤、截图表、序列表、性能表、贴图压缩、设置、写入、Console 的前几条错误、**头显清单** |
| `console.jsonl` | Console 一行一条：`source`（`console_snapshot` 开跑前已有的 / `live` 跑的过程中 / `compile` 编译消息）、`type`、`msg`、`stack`、`file`/`line`；UdonSharp 的带 `"udonsharp": true`，工具自己的带 `"tool": true` |
| `shots/*.png` | 截图（8 位 sRGB PNG，经过 PPv2）。有参考图的另有 `<机位>__vs_ref.png`（Unity 在上、参考在下） |
| `stereo/*_approx_LR.png` | 双眼近似：左右并排（§7.4） |
| `seq/<id>/0000.png…`、`heat_flicker.png`、`heat_std.png`、`numbers.json` | 动态序列的每一帧、闪烁热图、每帧 APL 和量数 |
| `tex/<id>/*.png` | 贴图压缩对照的截图（`__raw`、`__bc7`、`__crunch`） |
| `perf.json` | 性能（标明是编辑器估算，不是头显） |
| `collected/` | 测试定义要求一起交回的文件（比如改过的测试脚本） |
| `backup/` | 临时改过的文件的原样备份（比如 `GateClouds_Layout.json`） |
| `test_definition.json` | 这次用的测试定义原文 |
| `result.json` | 和日志最后一行同样的结果；上一层文件夹还有一份 `last_result.json` |

**EXR 不出**（总工程师定的）：截图是 PPv2 之后的画面，调色、色调映射都已经做了，EXR 存的也是同一个结果，只多出体积；HDR 的量（裂口的亮度之类）照旧靠 PNG 的 APL 和云端的 `gate_metrics.py`。要 PPv2 之前的线性 HDR，以后加一个 `"hdr": true` 的截图选项。

---

## 6. 测试定义 `tests/<test-id>.json`

顶层字段（全部可选，除了 `id`）：

| 字段 | |
|---|---|
| `id`、`title`、`source` | 名字、给人看的标题、依据（HANDOFF_LOG 哪一条、哪条裁决） |
| `blocked` | 写了就整个 BLOCKED（占位测试用），值是原因 |
| `requires` | 前置条件，缺一样就 BLOCKED：`unity`（默认 `2022.3.22f1`）、`packages`（默认 `com.vrchat.worlds` 3.10.5、`com.unity.postprocessing` 3.4.0）、`folders`、`files`、`types`（类型名，可以不带命名空间）、`menus`、`file_contains`（`{file 或 script, text: [...], absent: [...], why}`：脚本里有没有那几行补丁、JSON 里有没有新版本的标记）、`scene_objects`（打开场景以后查）、`scene_components` |
| `scene` | `{path, mode}`：`copy`（默认：拷进沙盒再开，原场景不动）、`in_place`（就在原场景里：门测试的 `LB_GateTest` 写死了场景路径）、`new`（沙盒里的空场景） |
| `allowed_writes` | 沙盒以外允许被改的地方（glob，`**` 跨文件夹）：只给现有搭建脚本本来就要写的地方 |
| `camera_template` | 抄设置的参考相机（场景路径）；不写就用第一台带 PostProcessLayer 的相机 |
| `time` | 怎么把场景定到时间 t 的步骤（`{t}` 换成数字），比如 `LB_GateTest.Apply("{t}")` |
| `build`、`after_build` | 搭建步骤（§6.1）。`build` 一步失败，后面的标成 skipped，截图 / 序列 / 性能都不做 |
| `post` | 截图、序列、性能都做完以后的步骤（比如把搭好的场景另存进沙盒、加 VRC 场景描述符，给 Play / ClientSim 用） |
| `settings` | 只查不改的项目设置：`vertex_compression_off`（这些通道要关压缩）、`fog_modes_kept`（Linear / Exp / Exp2 要留）、`lights_linear_intensity`；`gate` 决定没过算失败还是警告 |
| `cameras` | 机位表（§6.2），下面几项用 `"cam": "<名字>"` 引用，同名字段可以就地覆盖 |
| `shots`、`stereo`、`sequences`、`texture_compare`、`perf` | §7 |
| `checks` | 检查项（§6.3） |
| `require_ppv2` | 默认 true：有截图时检查 PPv2 生效了 |
| `headset_checklist`、`manual` | 写进 `summary.md` 末尾的头显清单和手动项（工具不做的） |

带 `_why` 的字段只是说明，工具不读。

### 6.1 步骤

| `type` | 字段 | |
|---|---|---|
| `menu` | `path` | 执行菜单（比如 `蓝白/Gate Clouds/Build`） |
| `method` | `name`（类型全名.方法名），`arg`（一个字符串）或 `args` | 静态方法；返回 `ERROR` 开头的字符串算失败（门测试脚本的习惯，`error_prefix` 可改） |
| `call` | `object`、`component`、`method`、`args` | 场景里组件的方法（比如 U# 驱动的 `Evaluate(t)`） |
| `set_field` | `object`、`component`、`field`、`value` | 组件的公开字段（bool / float / int / string） |
| `set_active` / `set_renderer` | `path`、`value` | 开关 GameObject / Renderer |
| `set_light` | `path`，`render_mode`（`NotImportant` / `Important` / `Auto`）、`culling_mask`、`intensity`、`enabled` | |
| `set_material` | 选法 `asset` / `find`（材质名）/ `under`（场景路径下所有 renderer 的材质）/ `renderer_name`（名字通配，renderer 或它的父物体），可以同时写取并集；`props`；`min_count` | 只改有这个属性的材质；数、3 个或 4 个数（颜色 / 向量） |
| `edit_json` | `asset`、`set: {"a.b": 值}` | 临时改一个 JSON 文件：原文件逐字节备份，结束时写回 |
| `assert_log` | `contains`、`absent` | 这一组步骤开始以后的 Console 里有 / 没有这些字 |
| `assert_object` / `assert_active` / `assert_renderer` / `assert_light` / `assert_no_component` | | 断言，不对就算这一步失败 |
| `collect` | `file` 或 `script` | 把文件原样拷进输出的 `collected/` |
| `save_scene_copy` | `name` | 把当前场景另存一份进沙盒（原场景不存） |
| `open_scene` | `path` | 打开沙盒里的场景（只认沙盒里的；当前场景的改动丢掉） |
| `add_component` | `object`、`create`、`component`、`position` | 只在沙盒里的场景上加组件（比如 VRC 场景描述符） |
| `save_scene` | | 存当前场景：只存沙盒里的 |
| `refresh`、`log` | | |

每一步还可以有 `id`、`why`（写进报告）、`restore`（结束时改回；`build` 里默认不改回，截图 / 序列 / 性能里的 `before` 和性能的状态一律改回）、`continue_on_error`。

场景路径：`Root/Child/Grandchild`（含没激活的）；`**/Name` 在整个场景里深找；`**/Name/Child` 深找到 Name 再往下。

### 6.2 机位

`eye [x,y,z]`；朝向 `euler [x,y,z]`（Unity 的 localEulerAngles）或 `yaw`、`pitch`、`roll`（= `(−pitch, yaw, roll)`，和渲染夹具一样）；`hfov`（水平视角，默认 90）或 `vfov`；`w`、`h`（默认 1920×1080）、`ss`（超采样，默认 2）；`t`；`ref`（参考图：`repo:<仓库里的路径>` 按同步记录的仓库路径找，或工程里的路径）、`ref_half`（`top` / `bottom`：`compare_*.png` 上半张是这一版的参照）；`before` / `after`（这一张前后的步骤，结束改回）。

近景：`look_at [x,y,z]` 或 `look_at_object`（场景路径，取包围盒中心）+ `distance`（米）+ `toward [x,y,z]`（相机退向这个点，比如主座位的眼）；`crop_deg [宽, 高]` + `ppd`（每度像素，默认 20：D-36 #1 的 Index 密度）时，尺寸按画面中心每度 `ppd` 个像素算。

### 6.3 检查项

`{"id", "metric", "op", "value", "gate", "why"}`。`op`：`== != < <= > >=`、`between`（`value: [a, b]`）、`within_pct`（`value` + `pct`）。`gate: false` 的没过只记“警告”，不影响退出码。量不到的（那一项没跑成）：`gate` 的算失败，不是 `gate` 的算警告。

默认就有的几条（同 `id` 以测试定义为准）：`steps_ok`（每一步都成功）、`no_compile_errors`、`no_exceptions`（跑的过程中 Console 里的异常，工具自己的不算）、`no_console_errors`（只警告）、`no_undeclared_writes`、`project_settings_untouched`、`ppv2_effective`（有截图时）、每一条 `settings`。

量数（`manifest.json` 的 `metrics`）的名字：
- `shot.<id>.apl / dark_pct / clip_pct / max_luma`，有参考图时 `ref_apl / apl_ratio / ref_rmse64`。APL = 8 位 sRGB 的 Rec.709 加权平均（0–255），和门测试、渲染夹具同一个量。
- `seq.<id>.std_mean / std_p99 / hf_mean / hf_p99 / hf_frac / apl_min / apl_max / apl_max_step / frames`
- `stereo.<id>.apl_lr_diff`
- `perf.<id>.<状态>.desktop_ms / vr_ms / vr_cpu_ms / draw_calls / batches / setpass / triangles / vertices / shadow_casters`
- `tex.<id>.<档>.storage_mb`、`tex.<id>.<档>.<机位>.psnr`
- `console.compile_errors_at_start / compile_errors / exceptions / errors / warnings`、`steps.errors`、`writes.undeclared / declared / project_settings_changed`、`capture.ppv2_layer / ppv2_diff / ppv2_effective`、`settings.<名字>`、`scene.lightmaps`

---

## 7. 截图、序列、性能、贴图对照

### 7.1 截图（`shots`）
照门测试的 `LB_GateTest.Shoot`（CONTROL §6 #10）：新建一台相机，照参考相机抄设置，挂一个新的 PostProcessLayer 并用参考相机的资源 Init；渲进 HDR（DefaultHDR）RT，宽高 × `ss`，渲 3 遍；PPv2 的输出 Blit 到 8 位 sRGB RT（`ss` = 2 时正好是 2×2 平均）；读回存 PNG。文件名默认 `<机位>_unity_t<秒>.png`（门测试 10-08 的习惯），`file` 可改。

### 7.2 动态序列（`sequences`）
- `kind: "micro_motion"`（默认）：头部微动。位置 ±`amp_cm`（默认 2 cm）、角度 ±`amp_deg`（默认 1°），`fps` 默认 90、`frames` 默认 1 秒。运动是固定的两个正弦叠加，每次跑都一样。时间停在 `t`（`advance_time: true` 时一起往前走）。
- `kind: "time"`：机位不动，时间从 `t0` 走到 `t1`，每帧用 `time` 步骤定时间（比如云海滚动、黑 → 晨）。
- 尺寸默认 1280×720、`ss` 默认 1（头显里没有超采样，闪烁才看得出来）；机位按 `ppd` 算过的就用它的尺寸。`eye_offset_mm` 可以把整段挪到左眼 / 右眼的位置。
- 每个像素算两个量（亮度 0–255）：`std` 时间标准差（含真实运动带来的变化）；`hf` 二阶时间差分的均方根 ÷ √6（平滑的运动几乎不算，来回跳的闪烁 / 爬动才算，白噪声时和 `std` 同一尺度）。报全画面平均、p99、`hf` 超过 `hf_threshold`（默认 6）的像素占比；每帧的 APL、最大的帧间跳变。热图 `heat_flicker.png`（`hf`）、`heat_std.png`：黑 → 紫 → 红 → 橙 → 浅黄 = 0 → `heat_scale`（默认 24），很小的值显示平均画面的暗灰。
- **这是编辑器里普通相机逐帧渲染的近似**：没有 SPS-I、没有头显的镜片和刷新；阈值是初值，第一次实测后由总工程师定。
- 帧默认都存（`save_frames: false` 可关）：云端可以拿去跑 `flashcheck.py`。

### 7.3 性能（`perf`）
照门测试的 `LB_GateTest.Perf`，和 10-08 起的数可以对上：一次渲染的 draw call / batches / SetPass / 三角面 / 投影物体（ProfilerRecorder 同一帧里渲染前后的差 + UnityStats）；帧时间预热 4 次、取 24 次的中位数，合计 = CPU 提交 + 等 GPU 画完（渲染前后各读 1 个像素同步，不重叠地算，偏保守）；电脑 1920×1080 一次，VR 估算 1832×1920 渲两次（竖直 100°，同一方向）。每项可以有几种“状态”（`states`：`steps` 做完量、量完改回，`teardown` 再搭一次）。**全是编辑器估算，不是头显。** 编辑模式手动 Render 时 ProfilerRecorder 可能读成 0（门测试 10-08 见过），那就以 Game 视图 / Frame Debugger 为准（手动项）。

### 7.4 双眼近似（`stereo`）
两台普通相机各往左、右偏 `ipd_mm / 2`（默认 64 mm → ±32 mm），分别渲染、左右并排存一张。**标明是近似：不是 SPS-I 单通道立体，不是头显测试。** 能看出来的只有“两只眼看到的东西差不多”这一层；每只眼的抖动 / 噪声是不是一致，要看头显。

### 7.5 贴图压缩对照（`texture_compare`）
选中材质（选法和 `set_material` 一样）上的所有贴图，各拷一份进沙盒、按每一档设导入（`raw` 不压缩 RGBA32、`bc7`、`crunch`：DXT1/DXT5 Crunched，`crunch_quality` 默认 50），材质也拷一份换上这些贴图；场景里用到原材质的 renderer 临时换成拷贝，拍 `shots` 里列的机位，换回。报每一档的存储大小（编辑器读数），以及和 `raw` 那张比的 PSNR。**原贴图的导入设置不动。** 原贴图的 mip、各向异性、过滤、sRGB 写进 `manifest.json` 的 `textures`。

---

## 8. 沙盒和写入

- 工具只往 **`Assets/_LanbaiTest/`**（带标记文件 `.lanbai_test_sandbox`）和输出文件夹写。开跑时删掉上次遗留的沙盒：**只删带标记的**；`Assets/_LanbaiTest/` 在、却没有标记，预检 BLOCKED。
- **工具从不保存场景**，也不 `SaveAssets`；材质值、物体开关这些在内存里改，结束时改回。
- 项目设置（顶点压缩、雾的变体剔除、光强）只查不改。
- 跑之前、跑之后各记一次 `Assets/`（大小 + 修改时间）和 `ProjectSettings/*.asset`（内容哈希）：沙盒和 `allowed_writes` 以外的每一处改动都列进 `writes.undeclared`，检查项 `no_undeclared_writes` 不过。
- **例外，要总导演知道：** `gate_clouds_test` 在原场景 `Assets/Lanbai/Tests/GateTest.unity` 里跑（`in_place`），由门测试脚本和门的搭建菜单去写 `Tests/`、`GateClouds/Generated/`、贴图导入设置、`UdonPrograms/`——HANDOFF_LOG 那几条本来就要这样搭；`auto_lite` 那一档临时改 `GateClouds_Layout.json`，量完逐字节写回。这些都列在它的 `allowed_writes` 里。`act06_dawn` 把主场景拷进沙盒再搭，但第 6 幕的搭建脚本会写 `Act06_Dawn/Generated/`。

---

## 9. 出了问题怎么恢复

1. **删沙盒**：菜单 **蓝白/Test/Delete Sandbox**，或关掉 Unity 后手动删 `Assets/_LanbaiTest/` 和 `Assets/_LanbaiTest.meta`。里面只有拷贝，删了没有损失。
2. **测试场景有没保存的改动**：**蓝白/Test/Discard Test Scene Changes**（不保存，从磁盘重新打开），或自己存。
3. **同步坏了**：关掉 Unity，把 `<工程>\LanbaiSyncBackup\<时间>.zip` 解压到工程根上覆盖（zip 里的路径从 `Assets/` 起，同步记录也在里面）：
   ```powershell
   Expand-Archive -Path "<工程>\LanbaiSyncBackup\<时间>.zip" -DestinationPath "<工程>" -Force
   ```
   新增的文件不在 zip 里（它们之前不存在）；要撤掉就看 `<工程>\LanbaiReports\sync\<时间>_plan.json` 的 `ADD` 那几项手动删。
4. **`GateClouds_Layout.json` 的画质档没改回来**（工具在 auto_lite 那一档中途被强行关掉时可能发生）：原样在输出文件夹的 `backup/` 里，拷回去，再点一次 **蓝白/Gate Clouds/Build**。
5. **重跑**：每次都是新文件夹，旧的不会被盖掉。

---

## 10. 已知的限制（没验证过的地方）

- **没在 Unity 里编译过、跑过。** 下面几处用了内部 API 或没把握的读法，第一次跑请特别看：
  - 开跑前的 Console 用反射读 `UnityEditor.LogEntries`（读不到会在 `console.jsonl` 里记一条，编译错误照样靠 `EditorUtility.scriptCompilationFailed` 卡住）；
  - 菜单在不在用反射读 `Menu.GetMenuItems`（读不准时当“在”，执行时再报错，不会误判 BLOCKED）；
  - 顶点压缩的掩码按 `1 << VertexAttribute` 读（先试 `PlayerSettings.vertexChannelCompressionMask`，读不到再读 `ProjectSettings.asset` 原文）；
  - 贴图存储大小用 `TextureUtil.GetStorageMemorySizeLong`（反射）。
- **批处理下 PPv2 生效没有，不知道**：工具自己查（§3），不行就用菜单。
- **Play 模式的东西工具不做**：Udon 时间（ClientSim + Profiler）、门的时钟在 Play 里走的画面、头显里的一切。都列在 `summary.md` 的手动项和头显清单里。`GateTest.unity` 没有 VRC 场景描述符，Play 时 ClientSim 起不来；所以 `gate_clouds_test` 最后把搭好的场景另存成 `Assets/_LanbaiTest/GateTest_play.unity`、只在这份拷贝上加描述符，量 Udon 时间就在它里面按 Play（手动项第 1 条）。
- **工具不碰的两样**：不调 UdonSharp 的任何编译（U# 在 build 模式下编译会出几千条假 CS0518，还会改写程序资产；工具只用编辑器自己的编译）；不加 AssetPostprocessor（加一个全局的，全工程的模型都会重导入）。
- 预检会报告工程里是不是有两套调色（旧的 `Assets/Lanbai/Grades/` + layer 4、套件的 `Assets/Lanbai/Grading/` + layer 22），只报告，不删；每张截图记下参考相机 PostProcessLayer 的 volumeLayer（`pp_volume_layer`）。
- `act06_dawn` 在编辑模式里直接调 U# 驱动的 C# 方法（`LanbaiActivate`、`Evaluate(t)`）来定时间，没试过；驱动里用到只有 Udon 里才有的东西，会在那一步报错。主场景里车不在原点的话，机位的 `eye` 要改。
- 闪烁、APL、PSNR 的阈值都是初值，第一次实测后定；性能的预算检查只报不卡（编辑器估算）。
- `LB_GateTest.*` 本来没有菜单（以前是本地的远程小助手 `LB_Remote` 用反射调的，不在仓库里）：现在由这个工具的菜单和 `-executeMethod` 调。
- 同步脚本只在 PowerShell 7.4（Linux）上测过，Windows PowerShell 5.1 没跑过；文件是带 BOM 的 UTF-8（5.1 读中文要 BOM）。

---

## 11. 检查

- C#：`bash Common/Tools~/compile_check/check_cs.sh Engineering/UnityTest` → `C# CHECK OK (0 assembly error(s), 0 lint warning(s))`（UnityEditor 2021.1 引用程序集 + PPv2 桩；不是 Unity 编译）。
- 测试定义：5 个 `tests/*.json` 都是合法 JSON，`gate_clouds_test` 的机位、时间、文件名对过 `Gate/GateLayout_v2.json` 的 `cameras` 和 HANDOFF_LOG。
- 同步脚本：PowerShell 7.4.6 上用一个假仓库 + 假工程走过：只列出、`-Apply`、第二次全部“一样”、本地改过被拒（退出码 2，什么都没改）、`-Force`（先备份再覆盖）、仓库删了的文件只列出不删、工程里多出来的不动、没有“同步：”行时猜路径并要求 `-AcceptGuess`、`.git/index.lock` / 没提交的改动 / 不在 main 都停（退出码 4）；对真仓库的两条门的条目只列出过一次（猜到的路径见 `Engineering/给总导演.md`）。
