# 蓝白 · Unity 测试工具（`Engineering/UnityTest/`）

写的人：总工程师（`pkg/engineering`），2026-10-24。依据：总导演 D-40 #1、D-40a。给谁用：本地 Unity 操作的「阿白」，和读结果的云端会话。

**状态：工具写完了，没在 Unity 里编译过，也没在 Unity 里跑过。** C# 只过了 `Common/Tools~/compile_check`（Roslyn + 桩，见 §11）；同步脚本在 Linux 的 PowerShell 7.4 上用假仓库测过（§11），没在 Windows 的 PowerShell 5.1 上跑过。**工具完成 ≠ Unity 验收完成**：哪一项“过了”，只看阿白跑出来的报告。

一句话：一个测试 = `tests/<test-id>.json` 一个文件。工具读它，先做只读的预检，再在沙盒里按步骤搭场景、截图、录动态序列、量性能，最后写一个输出文件夹（`manifest.json`、`summary.md`、截图……），用退出码告诉你结果。同一个测试跑几遍都行，每次一个新文件夹。

---

## 0. 每次测试，阿白照这个做

1. 仓库：照 `HANDOFF_CHATGPT.md` §C 第 5 步，把**你在用的那个仓库**（D-41 #5 批准的浅克隆 + 部分检出）更新到最新的 `main`。下面的 `<仓库>` 都指它。同步脚本会核对它的 HEAD 等于 `origin/main`，不等就停（§2）；`.git\index.lock` 在也停，不自动修。
2. 同步（§2）。先只列出，看一眼，再 `-Apply`。**第一次同步（以及任何要 `-Force` 的时候）属于“批量替换”（`HANDOFF_CHATGPT.md` §F），三步缺一不可**：
   1. 先整工程备份，照 `HANDOFF_CHATGPT.md` §C 第 2 步：关掉 Unity；排除 `Library`、`Temp`、`Logs`、`obj`、`Build`，打成 zip 放到 `E:\IDMdownload\VRCC\Backups\`；写下大小和 SHA256（`Get-FileHash <zip> -Algorithm SHA256`），逐文件核对。这个 zip 的路径就是 `CONSENT.json` 的 `backup`（§3）。备份做完之前不开 Unity；
   2. 把只列出的那份清单（屏幕上的输出，和 `<工程>\LanbaiReports\sync\<时间>_plan.json`）推到仓库的 `FromLocal/takeover/`，给小楠看；
   3. 小楠确认以后，才跑 `-Apply -Force`。

   平时（不用 `-Force`）：
   ```powershell
   cd "<仓库>"
   cmd /c "git show HEAD:Engineering/UnityTest/Tools~/lanbai_sync.ps1 > %TEMP%\lanbai_sync.ps1"   # 部分检出里脚本可能不在工作区：从提交里原样取出
   powershell -ExecutionPolicy Bypass -File "$env:TEMP\lanbai_sync.ps1" -Repo "<仓库>" -Project "<工程>"
   powershell -ExecutionPolicy Bypass -File "$env:TEMP\lanbai_sync.ps1" -Repo "<仓库>" -Project "<工程>" -Apply
   ```
   （用 `cmd /c` 重定向是为了字节原样：PowerShell 5.1 自己的 `>` 会按控制台编码转一遍，中文会坏。工作区里有这个脚本的话直接用它也行。）
3. **开 Unity 之前**过 `HANDOFF_CHATGPT.md` 的几道关：C 盘 / E 盘空间和可用内存（不够就停，告诉小楠）、备份、弹窗一律按“不改”回答；**第一次用这个工具之前要小楠同意**（工具的预检会查同意记录，§3）。然后打开 Unity，等导入、编译完。Console 里有编译错误就停：把 Console 原样推回来（工具的预检也会因为编译错误 BLOCKED）。
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
| `Editor/LanbaiTestPlay.cs` | **Play 阶段**（1.2.0，§7.6）：存状态、进 Play、跳转、拍、退出 Play、reload 以后收尾；交接扫描的曲线和拼图 |
| `tests/*.json` | 测试定义（§6）：`gate_clouds_test`、`act06_test`、`bus_slice`、`transitions_sweep`、`flicker_probe`（这两个在 Play 模式里拍，§7.6）、`tree_sample`（灯包的样板树，D-44 #6）、`act01_spawn`（占位）、`palace_hotspot`（占位） |
| `tests/data/transitions_table.json` | 交接扫描用的交接表（圣经 §6.x，36 个；`kind` = check / cut / black / flash） |
| `Tools~/lanbai_sync.ps1` | 仓库 → 工程的同步脚本（§2）。在 `~` 文件夹里，Unity 不导入 |

工程里的位置：`Assets/Lanbai/Engineering/UnityTest/`（同步脚本按 `X/...` → `Assets/Lanbai/X/...` 拷）。Editor 代码没有 asmdef，编进 `Assembly-CSharp-Editor`，和门测试脚本、各包的搭建脚本在同一个程序集里，互相调得到。

---

## 2. 同步脚本 `Tools~/lanbai_sync.ps1`

**只同步 HANDOFF_LOG 当前那一条点名的文件夹 / 文件。** 仓库里的 `X/...` 拷到工程的 `Assets/Lanbai/X/...`。

- 默认只列出（新增 `+`、覆盖 `~`、本地改过 `!`、仓库里没有了 `?`、这次排除了 `-`），什么都不改；加 `-Apply` 才动手。
- **最后一行总是 `LANBAI_SYNC_RESULT {json}`**（v2.1）：退出码、状态（`listed` / `applied` / `refused_local_modified` / `path_not_in_head` / `guess_not_accepted` / `stopped` / `error`）、各类个数。判断结果看这一行，不靠屏幕上的中文。
- **文件从提交取，不从工作区取**：`git ls-tree -r HEAD` 列、`git cat-file` 逐个取出（取出来先核对 blob 哈希再覆盖）。所以部分检出的仓库也能用，不会悄悄少拷；`HANDOFF_LOG.md` 也从 HEAD 读。
- **原地覆盖**，从不删文件夹再拷：资源的 GUID 在工程的 `.meta` 里，删了文件夹再拷 GUID 会变、引用会断。工程里的 `.meta` 一概不碰，**仓库里的 `.meta` 一律不同步**。
- **`-Repo` 必须写**，并且它的 HEAD 必须等于 `origin/main`。开始前还查：`.git\index.lock` 在、git 用不了或任何一步出错（按出错处理，不当成“干净”）、有没提交的改动，都停下（退出码 4），什么都不改，也不自动修。
- 动手前，要覆盖的文件（连同 `.meta`）和上次的同步记录先打包进 `<工程>\LanbaiSyncBackup\<时间>.zip`。
- 同步记录 `Assets\Lanbai\.lanbai_sync.json`：仓库路径、提交号、条目标题，**每个文件**上次同步时的 git blob 哈希、来自哪个提交、什么时候同步的。测试工具从这里读提交号写进 `manifest.json`（点开头的文件 Unity 不导入）。
- **本地改过的文件不覆盖、不删**（工程里的哈希和上次同步时的不一样，或者没有记录又和仓库不一样）：整次拒绝，退出码 2，什么都没改。**停，告诉小楠**；要用仓库的版本盖掉，`-Force` 属于批量替换，照 §0 第 2 条的三步（备份、推清单、小楠确认）。第一次同步时工程里已经有旧文件的，也会走到这一条。
- 第一次同步时工程里已经有 10-08 以来的旧文件，没有同步记录、内容又和仓库不一样，一定会被拒绝：照 §0 第 2 条的三步做。
- **点名的路径在 HEAD 里一个文件都没有**（拼错了、还没合进 main）：报错退出（退出码 1，`path_not_in_head`），什么都不改。
- **这次排除了的（`-`）和仓库里没有了的（`?`）分开**：上次同步过、这次被“不同步：”或跳过规则挡掉的文件记成 `EXCLUDED`，工程里的照旧不动、记录也留着；不会被当成“仓库里没有了”。
- **工程里没有 `Assets/Lanbai` 就拒绝**（退出码 4）：`-Project` 指错了，或者不是蓝白的工程；不替人新建。
- **从不自动删除。** 上次由它拷进去、现在仓库里没有了的文件只列出来（`?`），要删照 `HANDOFF_CHATGPT.md` §F（挪到 `_to_delete`、连 `.meta`、经小楠确认）。工程里本来就有的（各包的 `Generated/`、`UdonPrograms/*.asset`、本地自己加的）一概不动，只数一下。
- 永远不同步（和 `HANDOFF_CHATGPT.md` §A 的 robocopy 一样，另加 `.meta`）：仓库根上的单个文件、`FromLocal/`、`Art/`；任何一层叫 `Source`、`Renders`、`__pycache__`、`Docs~`、`Tools~`、`Source~`、`Originals~` 的文件夹；`.py .pyc .blend .blend1 .ps1 .sh .meta`；`.gitignore`。
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
| `-Repo <路径>` | 仓库（必填；HEAD 要等于 `origin/main`） |
| `-Entry <n>` | HANDOFF_LOG 的第 n 条，1 = 最上面、最新的（默认） |
| `-EntryMatch <字>` | 标题里含这几个字的那一条 |
| `-Paths a/,b/c.json` | 不看 HANDOFF_LOG，直接指定。只在总导演 / 总工程师明说时用 |
| `-Apply` / `-Force` / `-AcceptGuess` | 见上 |

退出码：0 完成（或只列出）；1 没有可同步的、点名的路径在 HEAD 里没有、或者猜的路径没加 `-AcceptGuess`；2 本地改过的被拒绝；3 脚本出错；4 仓库或工程状态不对（lock 文件、没提交的改动、不在 main、工程里没有 `Assets/Lanbai`）。

同步时 Unity 开着也可以（文件是原地覆盖的），但最好先关掉，或者至少别在它导入的时候同步；同步完回到 Unity 等它导入、编译完。

---

## 3. 跑测试

### 开跑之前工具自己查的几道关（HANDOFF_CHATGPT，只读）
- **资源**：C 盘剩 ≥ 10 GB、工程所在盘剩 ≥ 10 GB、可用内存 ≥ 6 GB（测试定义的 `resources` 可改：`min_c_gb`、`min_project_gb`、`min_free_ram_gb`）。不够就 BLOCKED：**停，告诉小楠**（工具和阿白都不替小楠关程序、清文件；VRChat 开着就请小楠关）。
- **写入检查**（1.2.2）：按文件大小和修改时间比；材质、`.asset`、预制体、`.meta` 这类 ≤ 4 MB 的小文件开搭前另记内容哈希，存了但逐字节没变的列在 `tool_touched_restored`，不算“改了”（10-25 Sea / SeaB / WetGround 就是这种）。
- **小楠的同意**：第一次用这个工具之前要小楠同意。同意以后，阿白写 `<工程>/LanbaiReports/tests/CONSENT.json`：`{"by": "小楠", "date": "YYYY-MM-DD", "tool_version": "1.2.2", "tests": ["gate_clouds_test", "transitions_sweep", "flicker_probe", "tree_sample"], "backup": "整工程备份的 zip 路径", "note": "小楠原话"}`。没有这个文件就 BLOCKED；**同意的范围**：`tool_version` 要和工具的版本一样（工具升了版本要重新问），`tests` 里要有这次跑的测试，不然 BLOCKED；备份的路径这台机器上找不到，只警告。工具只读它，不替人写。
- **弹窗**：工具自己不弹（批处理没有；菜单只有开始前和跑完的两个框）。Unity / Hub / VCC / SDK 的弹窗照 HANDOFF_CHATGPT §C 第 5 步一律按“不改”回答。

### 菜单
**蓝白/Test/Run gate_clouds_test**（以及 act06_test、bus_slice、**transitions_sweep (Play mode)**、**flicker_probe (Play mode)**、act01_spawn、palace_hotspot）；**Run Other Test…** 列出 `tests/` 里所有的；**Preflight Only…** 只做预检。跑的时候编辑器不响应（几分钟），跑完弹一个框，可以直接打开输出文件夹。菜单跑完，测试场景留在打开的状态（没保存）。**不要保存它**：下次跑之前点 **蓝白/Test/Discard Test Scene Changes**（只对沙盒里的拷贝和 `Assets/Lanbai/Tests/` 下的场景起作用；别的已打开场景有没保存的改动时它不动，停，告诉小楠），不然预检会因为“有没保存的改动”BLOCKED。

### 批处理（**要先关掉这个工程的 Unity 编辑器**）
同一个工程同一时间只能有一个 Unity 打开（编辑器开着时，批处理会报工程被占用、直接退出，日志里没有 `LANBAI_TEST_RESULT`）。这一条没在阿白的机器上试过；不想关编辑器就用菜单。
```powershell
$unity = "E:\VRR\2022.3.22f1\Editor\Unity.exe"          # HANDOFF_CHATGPT §A；以那里写的为准
$proj  = "E:\IDMdownload\VRCC\dream"
$id    = "gate_clouds_test"
& $unity -batchmode -projectPath $proj -executeMethod Lanbai.Test.Runner.RunCli -lanbaiTest $id -logFile "$proj\LanbaiReports\tests\$id.log" | Out-Null
$code = $LASTEXITCODE; "退出码 $code"
Select-String -Path "$proj\LanbaiReports\tests\$id.log" -Pattern '^LANBAI_TEST_RESULT ' -Encoding UTF8 | Select-Object -Last 1
Get-Content "$proj\LanbaiReports\tests\$id\last_result.json" -Encoding UTF8
```
- `| Out-Null` 是为了让 PowerShell 等 Unity 退出再往下走（不然 `$LASTEXITCODE` 拿不到）。
- **编码**：Unity 的日志和工具写的 JSON 都是 UTF-8 没有 BOM；PowerShell 5.1 的 `Select-String` / `Get-Content` 不加 `-Encoding UTF8` 会按系统编码读，中文变乱码（结果行的 JSON 也就读不对）。路径里有中文的话，整条命令用 PowerShell 跑，不要经 `cmd`。
- **不要加 `-nographics`**：截图和性能要真的显卡（预检会因为没有显卡 BLOCKED）。不用加 `-quit`（工具自己退出）。
- 只做预检：末尾加 `-lanbaiPreflightOnly`。只做预检的结果是 `preflight_ok`（不是 `pass`：没跑测试），三层状态里 Unity 桌面记 `not_tested`，也不覆盖 `last_result.json`。用别的测试定义文件：`-lanbaiTestFile <路径>`（代替 `-lanbaiTest`）。
- **PPv2 在批处理下生效没有，没验证过。** 工具每次第一张截图前自己查：同一机位开 / 关 PPv2 各渲一张小图，要不一样（检查项 `ppv2_effective`）。批处理下这一项没过的话，截图就是没调色的，**改用菜单跑**，其余照旧。
- 等的过程中编辑器 reload 了（编译完之类）：工具从头再跑一次（新的输出文件夹，上一次那个没有报告）；再 reload 一次就 BLOCKED（退出码 2），批处理照样退出。
- 要等 U# 程序资产初始化的时候（测试定义的 `udon_programs` 有新建的，D-41），`RunCli` 先返回，批处理的编辑器循环接着转，等好了再跑、跑完再退出；所以**别加 `-quit`**。菜单也一样：先返回，跑完再弹框。
- **结果以这一次运行的结果行为准**：每次一开始就在输出文件夹里写 `result.json` = `running`，跑完盖成结果。`Unity.exe` 自己的退出码不可靠（Unity 自己出错也会给 1，看起来和“检查没过”一样）：读这次的 `result.json`，或日志里这次的 `LANBAI_TEST_RESULT` 那一行（日志的最后几行可能是 Unity 自己退出时写的，用 `Select-String` 找）。`result.json` 还是 `running` = 没跑完（崩了或被关了）。

---

## 4. 退出码，以及每种怎么办

| 退出码 | 意思 | 阿白怎么办 |
|---|---|---|
| **0** | 全部跑完，检查全过 | 拷输出文件夹到 `FromLocal/`、推；头显清单另外看 |
| **1** | 跑完了，有检查没过（或有一步失败了） | 照样拷、推。**不要自己改数值、不要自己修**：`summary.md` 的“检查项”和“步骤”写着哪里没过，云端看了再定 |
| **2** | BLOCKED：预检或前置条件不满足，什么都没搭 | 看 `summary.md` 第一段的原因。**只有“没同步”这一种自己补**（照 §0 重新同步再跑）；Unity / 包版本不对、有没保存的场景、资源不够、没有小楠的同意、别的任何原因：**停，告诉小楠**（`HANDOFF_CHATGPT.md` §F：不装、不升降版本，不替人保存场景）。补不了的（比如车的切片还没交、占位测试）照样推报告 |
| **3** | 工具自己出了异常（工具自己代码里的异常，哪怕只在一张截图里，也算 3；被调的搭建脚本抛的、步骤判的失败算 1） | 推 `manifest.json`（`error`、`error_stack`）、`console.jsonl` 和 `-logFile` 的日志；照 §9 恢复后可以重跑一次。这是总工程师的 bug |
| 日志里**没有** `LANBAI_TEST_RESULT` | Unity 没走到工具：多半是启动时就有编译错误（`-executeMethod` 根本没执行），或者工程被另一个 Unity 开着 | 打开编辑器看 Console；把 `-logFile` 的日志原样推回来。按 BLOCKED 处理 |

`summary.md` 里“三层状态”：Blender 离线（云端填）、Unity 桌面（工具填，就是这个退出码）、头显（固定 `not_tested`，工具从不标成过）。

---

## 5. 输出：`<工程>/LanbaiReports/tests/<test-id>/<YYYYMMDD-HHMMSS>/`

| 文件 | |
|---|---|
| `manifest.json` | 机器读的全部：工具版本、测试 id、测试定义的 SHA-256、仓库提交（同步记录）、**每个文件夹拷进来时的提交**（`copied`：从同步记录按 `Assets/Lanbai/` 下的第一层文件夹汇总，`summary.md` 里也印；一个文件夹混了多个提交会警告，D-43 #6）、Unity / SDK / 包的版本、显卡、预检、前置条件、每一步的状态和用时、只查不改的设置、检查项、全部量数（`metrics`，每个量的说明在 `metric_notes`）、写入核对、警告、文件清单；三层状态在 `layers` |
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
| `allowed_writes` | 沙盒以外允许被改的地方（glob，`**` 跨文件夹）：只给现有搭建脚本本来就要写的地方。前面加 `new:`（1.2.2）= 只放过新建的文件，那里已有的文件被改、被删照常报（`SerializedUdonPrograms` 这类 U# 自己写的地方用它）。`udon_programs` 列的程序资产工具在记快照之前就建好，不用为它们开 `Assets/Lanbai/UdonPrograms/**` |
| `backup_before` | 开搭之前原样拷进输出 `backup_before/` 的文件（glob） |
| `camera_template` | 抄设置的参考相机（场景路径）；不写就用第一台带 PostProcessLayer 的相机 |
| `time` | 怎么把场景定到时间 t 的步骤（`{t}` 换成数字），比如 `LB_GateTest.Apply("{t}")` |
| `udon_programs` | 测试要用到的 U# 脚本名（D-41）：开搭之前用 `Common/Editor/LanbaiUdonPrograms` 建好它们的程序资产、等 SDK 初始化完（2/2，最多 180 秒）再搭。等不到算 BLOCKED。少列了的话，搭建菜单会在半路排队等，那一步算失败（报告里说清楚是少列了哪个） |
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
| `method` | `name`（类型全名.方法名），`arg`（一个字符串）或 `args`，`expect` | 静态方法；返回 `ERROR` 开头的字符串算失败（门测试脚本的习惯，`error_prefix` 可改）；写了 `expect` 时，返回里没有这几个字也算失败 |
| `call` | `object`、`component`、`method`、`args` | 场景里组件的方法（比如 U# 驱动的 `Evaluate(t)`） |
| `set_field` | `object`、`component`、`field`、`value` | 组件的公开字段（bool / float / int / string） |
| `set_active` / `set_renderer` | `path`、`value` | 开关 GameObject / Renderer |
| `set_light` | `path`，`render_mode`（`NotImportant` / `Important` / `Auto`）、`culling_mask`、`intensity`、`enabled` | |
| `set_field_objects_active` | `component`、`fields`（字段名，可以用 `*`）、`value`、`optional` | 组件上这些字段指着的物体（GameObject / 组件，单个或数组）开关；比如关掉 `LB_Journey` 的旧占位组。`optional`：没有这个组件 / 字段只记一句 |
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

`eye [x,y,z]`；朝向 `euler [x,y,z]`（Unity 的 localEulerAngles）或 `yaw`、`pitch`、`roll`（= `(−pitch, yaw, roll)`，和渲染夹具一样）；`hfov`（水平视角，默认 90）或 `vfov`；`w`、`h`（默认 1920×1080）、`ss`（超采样，默认 2）；`t`；`ref`（参考图：`repo:<仓库里的路径>` 按同步记录的仓库路径找，或工程里的路径）、`ref_half`（`top` / `bottom`：`compare_*.png` 上半张是这一版的参照）；`before`（定好时间以后、拍之前的步骤，拍完改回）/ `after`（拍完以后的步骤，不登记改回）。

近景：`look_at [x,y,z]` 或 `look_at_object`（场景路径，取包围盒中心；加 `look_at_anchor [ax, ay, az]`（1.2.2）就取包围盒里的那个点，每轴 0 = min、1 = max，比如对着窗扣、窗框的一个角）+ `distance`（米）+ `toward [x,y,z]`（相机退向这个点，比如主座位的眼）；`crop_deg [宽, 高]` + `ppd`（每度像素，默认 20：D-36 #1 的 Index 密度）时，尺寸按画面中心每度 `ppd` 个像素算。
截图可以写 `coverage_of [路径, ...]`（1.2.2）：同一机位关掉这些物体再渲一张，亮度差 > 2 的像素占比记成 `shot.<id>.coverage`（下限：和背景一样亮的像素数不进去），用来保证画面里真的有要审的东西（`bus_slice` 的侧窗：窗框 / 胶条 ≥ 30 %）。

### 6.3 检查项

`{"id", "metric", "op", "value", "gate", "why"}`。`op`：`== != < <= > >=`、`between`（`value: [a, b]`）、`within_pct`（`value` + `pct`）。`gate: false` 的没过只记“警告”，不影响退出码。量不到的（那一项没跑成）：`gate` 的算失败，不是 `gate` 的算警告。

默认就有的几条（同 `id` 以测试定义为准）：`steps_ok`（每一步都成功）、`no_compile_errors`、`no_exceptions`（跑的过程中 Console 里的异常，工具自己的不算）、`no_console_errors`（只警告）、`no_undeclared_writes`、`project_settings_untouched`、`ppv2_effective`（有截图时）、每一条 `settings`。

量数（`manifest.json` 的 `metrics`）的名字：
- `shot.<id>.apl / dark_pct / clip_pct / max_luma`，有参考图时 `ref_apl / apl_ratio / ref_rmse64`。APL = 8 位 sRGB 的 Rec.709 加权平均（0–255），和门测试、渲染夹具同一个量。
- `seq.<id>.shimmer_mean / shimmer_p99 / shimmer_frac`（闪烁的主量）、`motion_std_mean / motion_std_p99`、`hf_raw_mean / hf_raw_p99 / hf_raw_frac`（参考）、`apl_min / apl_max / apl_max_step / frames`
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
- `kind: "static"`：机位不动、时间不动的**对照**，只剩画面本身的时间噪声（抖动、时间性效果）。和同一机位的 `micro_motion` 一起看，才知道微动带来了多少闪烁。
- 尺寸默认 1280×720、`ss` 默认 1（头显里没有超采样，闪烁才看得出来）；机位按 `ppd` 算过的就用它的尺寸。`eye_offset_mm` 可以把整段挪到左眼 / 右眼的位置。
- **闪烁的主量 `shimmer`**（终审 r2 改）：每一帧在**同一个姿态**再渲一张高倍超采样的参考（`reference_ss`，默认 4×；0 = 不渲），逐像素量“测的图 − 参考图”的亮度差（0–255）随时间的标准差。真实的运动（边缘挪动）两张图一起挪，差里没有；剩下的是采样不足带来的闪烁、爬动、摩尔纹。报全画面平均、p99、超过 `shimmer_threshold`（默认 4）的像素占比，热图 `heat_shimmer.png`。
- **只量被测物**（1.2.2，阿白 10-25 树的验收）：序列可以写 `"isolate": {"keep": ["根物体名", ...], "roi_dilate_px": 4}`。这个序列里只留这些根物体下的 Renderer，别的（旧车柱、灯杆、路、占位）关掉，结束还原；灯光不动。同一机位“有 / 没有被测物”各渲一张，亮度差 > 2 的像素再外扩 `roi_dilate_px` 就是 ROI（`seq/<id>/roi.png`，ROI 外压暗）。`shimmer_*` 三项只在 ROI 里算（占比的分母是 ROI），另报 `seq.<id>.roi_frac`。`keep` 里的物体找不到、ROI 是空的，这一项出错。
- **MSAA**（1.2.2，阿白 10-25）：机位可以写 `"msaa": 1 | 2 | 4 | 8`（默认 1）。用 alpha-to-coverage 的东西（树叶）要写 4：没有 MSAA 就是整块卡片。
- 另外两个量**只作参考，不是闪烁**：`motion_std`（逐像素亮度的时间标准差，含真实运动）、`hf_raw`（二阶时间差分的均方根 ÷ √6；平滑运动大多不算，但正常的边缘运动也会进来一部分）；热图 `heat_motion_std.png`、`heat_hf_raw.png`。还有每帧的 APL、最大的帧间跳变。热图颜色：黑 → 紫 → 红 → 橙 → 浅黄，很小的值显示平均画面的暗灰。
- **这是编辑器里普通相机逐帧渲染的近似**：没有 SPS-I、没有头显的镜片和刷新；阈值是初值，第一次实测后由总工程师定。
- 帧默认都存（`save_frames: false` 可关）：云端可以拿去跑 `flashcheck.py`。

### 7.3 性能（`perf`）
照门测试的 `LB_GateTest.Perf`，和 10-08 起的数可以对上：一次渲染的 draw call / batches / SetPass / 三角面 / 投影物体（ProfilerRecorder 同一帧里渲染前后的差 + UnityStats）；帧时间预热 4 次、取 24 次的中位数，合计 = CPU 提交 + 等 GPU 画完（渲染前后各读 1 个像素同步，不重叠地算，偏保守）；电脑 1920×1080 一次，VR 估算 1832×1920 渲两次（竖直 100°，同一方向）。每项可以有几种“状态”（`states`：`steps` 做完量、量完改回，`teardown` 再搭一次）。**全是编辑器估算，不是头显。** 编辑模式手动 Render 时 ProfilerRecorder 可能读成 0（门测试 10-08 见过），那就以 Game 视图 / Frame Debugger 为准（手动项）。

### 7.4 双眼近似（`stereo`）
两台普通相机各往左、右偏 `ipd_mm / 2`（默认 64 mm → ±32 mm），分别渲染、左右并排存一张。**标明是近似：不是 SPS-I 单通道立体，不是头显测试。** 能看出来的只有“两只眼看到的东西差不多”这一层；每只眼的抖动 / 噪声是不是一致，要看头显。

### 7.5 贴图压缩对照（`texture_compare`）
选中材质（选法和 `set_material` 一样）上的所有贴图，各拷一份进沙盒、按每一档设导入（`raw` 不压缩 RGBA32、`bc7`、`bc5`（只对法线贴图；别的贴图这一档用 BC7）、`crunch` 或 `crunch:<质量>`（DXT1/DXT5 Crunched，法线是 DXT5nm；不写质量用 `crunch_quality`，默认 50）。量数名和文件名里冒号换成 `_q`，比如 `crunch:100` → `crunch_q100`；`ncrunch:<质量>` 只把法线贴图做 Crunch、别的贴图用 BC7，和 `bc5` 那一档只差在法线上；D-40b #6 的法线对照 = `bc5` 对 `ncrunch:100`），材质也拷一份换上这些贴图；场景里用到原材质的 renderer 临时换成拷贝，拍 `shots` 里列的机位，换回。报每一档的存储大小（编辑器读数），以及和 `raw` 那张比的 PSNR。**原贴图的导入设置不动。** 原贴图的 mip、各向异性、过滤、sRGB 写进 `manifest.json` 的 `textures`。

### 7.6 Play 阶段（`play`；1.2.0，D-44 #4）：`transitions_sweep`、`flicker_probe`

测试定义里有 `play` 的，编辑模式的那一半照常（预检、把场景拷进沙盒、`build`），然后**工具自己进 Play 模式**（ClientSim 照常起来，旅程照常走）：用旅程的调试跳转把时间轴拨到每一段开头前 `settle_s` 秒，时间轴实时走，每走过一个要拍的时刻就用工具自己的相机拍一张；全部拍完退出 Play，reload 以后照常写报告。**跑的时候别碰编辑器**（别点停止、别改脚本：Play 里 reload 了这次就作废，退出码 3）。

- **先等准备好**（1.2.1）：本地玩家有了、旅程的 `clock.ready_vars` 都为 true（默认 `_journeyReady`、`_spawnFadeEnded`）、分发层的 `spawnFadeSince` ≥ 0（出生淡入结束）、再过至少 2 帧；60 s 还没好记 **BLOCKED**（退出码 2）。然后核对 Udon 变量的名字和类型（`time_var` / `seek_var` 要是 float，没有这个变量就 BLOCKED），开 / 关 PPv2 各渲一张（`play.ppv2_effective`，没生效算 fail），把 ClientSim 的玩家挪到主座位（`seat_player`，默认 true；每一段开拍前再挪一次；`play.head_cam_dist_max` 记头离相机最远多少）。
- 时间轴：`clock` = `{"component": "LB_Journey", "time_var": "dbgT", "seek_var": "debugSeekSeconds", "seek_event": "_DebugSeekVar", "ready_vars": [...]}`（默认就是这些，和本地的旅程进度面板一样）。
- 相机：`camera.relative_to` = `{"component": "LB_Journey", "field": "busRoot"}`（或场景路径），`eye`（车的局部坐标；默认 D-28 的主座位 (0.55, 1.70, 2.05)；`LB_Journey.heroEye` 是作废的旧值，不再用），`yaw` / `pitch` / `roll`（度），`hfov`、`w`、`h`（默认 640×360）。车动相机跟着动。`overlay_follow_camera`（默认 true）：每张拍之前把遮罩球挪到相机这里（它平时跟着玩家的头），拍完放回。
- 每张记**要的时刻和实际的时刻**（时间轴是实时走的，编辑器一帧拍不完会晚一点：照实记，不补）。**帧间的量**（相邻两张的差、闪烁计数、差图）**只用有效的相邻两张**：中间没漏拍、实际间隔 ≤ 1.5 × 安排的间隔。每段记 `achieved_fps`、`missed_frac`；`missed_frac` 超过 `play.max_missed_frac`（默认 0.1）算 fail。拍的循环里不写盘：PNG 都在一段拍完以后写。每张还记平均对数亮度 mean(log2(max(L, 0.004)))（L = 线性亮度，从 8 位 sRGB 读回来换算）和 APL。
- **`sweep`**（交接扫描）：`table`（默认 `data/transitions_table.json`）或 `transitions`，`only`（只扫这几个 id），`pre_s` / `post_s`（7 / 7）、`coarse_fps`（1）、`fine_s` / `fine_fps`（交接点前后 1 s、10 fps）。每个交接出 `sweep/<id>/strip_1s.png`（每秒一张，从左上按时间排）、`strip_fine.png`（交接点前后 1 s，每 0.1 s 一张）、`curve.png`（横轴时间，纵轴 −8 … 0 EV，红线 = 交接时刻）、`frames.csv`；量数 `sweep.<id>.max_step_ev`（相邻两张、间隔 ≤ 0.15 s 的最大差）、`rise_025` / `rise_1` / `rise_2`（窗口里最多升了多少 EV）。`summary.md` 里一张表：有意的（`cut` 剪 1–3、`black` 第 5 幕的黑、`flash` U9 和 FLASH_TEAR）单独标，“要查”的超过圣经 §1.8 的三个窗口标 ⚠️。**全画面平均、主座位往前**：只用来找“哪里跳了”，不是验收（圣经的限速是每个视向的）。
- **`probes`**（闪烁探测）：每个 `{id, t0, t1, fps, variants: [{id, why, toggles: [...]}]}`（默认 1016–1042 s、30 fps）。每个变体把同一段重拍一遍，**拍每一张之前**把它的 `toggles` 再做一遍（旅程可能每帧改回去）：
  `set_active {path, value}`、`set_renderer {path, value}`、`set_components_enabled {component（类型名，含子类）, value}`、`field_objects_active {component, fields, value}`（组件字段指着的物体）、`field_renderers {component, fields, enabled?, mpb_float?}`（字段里的 renderer：开关、或者往 MaterialPropertyBlock 写几个 float）、`udon_var {component, var, value}`、`global_float` / `global_vector {name（只许 _Udon_）, value}`；都可以 `optional`。
  **每个变体之前，上一个变体改过的东西逆序还原**（第一次改之前记下原值；全局量、MaterialPropertyBlock、Udon 变量也还原：全局量退出 Play 以后还在）；收尾和所有中断（Play 被退出、工具出错）也还原。
  每个变体出 `probe/<id>/<变体>/frames.csv`（每帧的平均对数亮度、APL、和上一帧的平均差）、`curve.png`、`flicker_count.png`（每个像素相邻帧差 > 24 的次数：局部的闪在哪）、`max_diff.png`、差最大的 8 对 `diff_<t>_heat.png` + `diff_<t>_frame.png`；量数 `max_step_ev`、`steps_over_01ev`、`flicker_px_frac`，以及每个变体比第一个变体（对照）的 `max_step_vs_<对照>`。**探测不改、不删任何东西**：toggles 只在 Play 里，退出 Play 就回去了。
- 编辑器里普通相机，不是头显、不是 SPS-I；每次跑出来的帧时刻会差几毫秒。批处理下进 Play 没试过：用菜单跑。
- **中断和收尾**（1.2.1）：整个 Play 阶段有总超时（每段长度 + settle + 20 s，再加 120 s；`play.timeout_s` 可改）；Console 的 Error Pause 停住 Play 时工具恢复它、记次数（`play.error_pauses`，超过 20 次算出错）；收尾自己出错也照样写 `result.json` 和 `LANBAI_TEST_RESULT`（退出码 3）。进 / 出 Play 两次 reload 之间的 Console 都接上（reload 之前没存的行写进 `_state/console_bridge.jsonl`），同样的行只留一条、记 `repeat` 次数；跑完 `_state/` 删掉。

---

## 8. 沙盒和写入

- 工具只往 **`Assets/_LanbaiTest/`**（带标记文件 `.lanbai_test_sandbox`）和输出文件夹写。开跑时删掉上次遗留的沙盒：**只删带标记的**；`Assets/_LanbaiTest/` 在、却没有标记，预检 BLOCKED。
- **工具从不保存场景**，也不 `SaveAssets`；材质值、物体开关这些在内存里改，结束时改回。
- 项目设置（顶点压缩、雾的变体剔除、光强）只查不改。
- 工具临时改过又改回的（`set_material` 改过的材质、`edit_json` 写回的文件）：**按字节核对**：落盘的内容和开跑前磁盘上的逐字节一样，单独列在 `writes.tool_touched_restored`，不算没声明的写入；不一样（比如被后面搭建脚本的 `SaveAssets` 按另一种序列化落了盘）就照常算写入，注明“工具临时改过的”。
- **改回失败**：试两次，还不行就留着，之后每次改回和收尾时再试，报告的警告里写着；收尾时 `edit_json` 改过的文件还写不回去，**退出码 3**（工程里留着测试改过的值），原文件在输出的 `backup/`：停，告诉小楠。
- 跑之前、跑之后各记一次 `Assets/`（大小 + 修改时间）和 `ProjectSettings/*.asset`（内容哈希）：沙盒和 `allowed_writes` 以外的每一处改动都列进 `writes.undeclared`，检查项 `no_undeclared_writes` 不过。
- **例外（总导演已批准，条件是下面三样）：** 每次的 `summary.md` 和 `manifest.json` 都写全 `allowed_writes`；`edit_json` 改的文件在任何情况下都逐字节写回（改回栈在每一项的 `finally` 和整次运行的 `finally` 里都会跑；只有 Unity 本身崩掉时写不回，那就照 §9 第 4 条从 `backup/` 拷回）；测试定义的 `backup_before`（门测试：`Assets/Lanbai/Tests/**` 和 `GateClouds_Layout.json`）在开搭之前原样拷进本次输出的 `backup_before/`。
- 例外的具体内容： `gate_clouds_test` 在原场景 `Assets/Lanbai/Tests/GateTest.unity` 里跑（`in_place`），由门测试脚本和门的搭建菜单去写 `Tests/`、`GateClouds/Generated/`、贴图导入设置、`UdonPrograms/`——HANDOFF_LOG 那几条本来就要这样搭；`auto_lite` 那一档临时改 `GateClouds_Layout.json`，量完逐字节写回。这些都列在它的 `allowed_writes` 里。`act06_test` 把主场景拷进沙盒再搭，但第 6 幕的搭建脚本会写 `Act06_Dawn/Generated/`。

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
- **Play 阶段（§7.6）没在 Unity 里跑过**：进 / 出 Play 的两次 reload 之间靠 `SessionState` 和输出文件夹的 `_state/` 接上；在 Play 里用反射调 `UdonBehaviour.GetProgramVariable / SetProgramVariable / SendCustomEvent`，用 `UdonSharpEditorUtility.GetBackingUdonBehaviour` 找旅程背后的 UdonBehaviour；在 `EditorApplication.update` 里手动 `Camera.Render()`。第一次跑请把 Console 原样推回来。
- **除了 §7.6 的两个，Play 模式的东西工具不做**：Udon 时间（ClientSim + Profiler）、门的时钟在 Play 里走的画面、头显里的一切。都列在 `summary.md` 的手动项和头显清单里。`GateTest.unity` 没有 VRC 场景描述符，Play 时 ClientSim 起不来；所以 `gate_clouds_test` 最后把搭好的场景另存成 `Assets/_LanbaiTest/GateTest_play.unity`、只在这份拷贝上加描述符，量 Udon 时间就在它里面按 Play（手动项第 1 条）。
- **工具不碰的两样**：不调 UdonSharp 的任何编译（U# 在 build 模式下编译会出几千条假 CS0518，还会改写程序资产；工具只用编辑器自己的编译）；不加 AssetPostprocessor（加一个全局的，全工程的模型都会重导入）。
- 预检会报告工程里是不是有两套调色（旧的 `Assets/Lanbai/Grades/` + layer 4、套件的 `Assets/Lanbai/Grading/` + layer 22），只报告，不删；每张截图记下参考相机 PostProcessLayer 的 volumeLayer（`pp_volume_layer`）。
- `act06_test` 在编辑模式里直接调 U# 驱动的 C# 方法（`LanbaiActivate`、`Evaluate(t)`）来定时间，没试过；驱动里用到只有 Udon 里才有的东西，会在那一步报错。主场景里车不在原点的话，机位的 `eye` 要改。
- 闪烁、APL、PSNR 的阈值都是初值，第一次实测后定；性能的预算检查只报不卡（编辑器估算）。
- `LB_GateTest.*` 本来没有菜单（以前是本地的远程小助手 `LB_Remote` 用反射调的，不在仓库里）：现在由这个工具的菜单和 `-executeMethod` 调。
- 同步脚本只在 PowerShell 7.4（Linux）上测过，Windows PowerShell 5.1 没跑过；文件是带 BOM 的 UTF-8（5.1 读中文要 BOM）。

---

## 11. 检查

- C#：`bash Common/Tools~/compile_check/check_cs.sh Engineering/UnityTest` → `C# CHECK OK (0 assembly error(s), 0 lint warning(s))`（UnityEditor 2021.1 引用程序集 + PPv2 桩；不是 Unity 编译）。
- 测试定义：8 个 `tests/*.json` 和 `tests/data/transitions_table.json` 都是合法 JSON，`gate_clouds_test` 的机位、时间、文件名对过 `Gate/GateLayout_v2.json` 的 `cameras` 和 HANDOFF_LOG。
- 同步脚本：PowerShell 7.4.6 上用一个假仓库 + 假工程走过：只列出、`-Apply`、第二次全部“一样”、本地改过被拒（退出码 2，什么都没改）、`-Force`（先备份再覆盖）、仓库删了的文件只列出不删、工程里多出来的不动、没有“同步：”行时猜路径并要求 `-AcceptGuess`、`.git/index.lock` / 没提交的改动 / 不在 main 都停（退出码 4）；对真仓库的两条门的条目只列出过一次（猜到的路径见 `Engineering/给总导演.md`）。
