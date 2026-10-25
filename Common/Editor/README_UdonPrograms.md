# U# 程序资产的共用工具（`Common/Editor/LanbaiUdonPrograms.cs`，D-41）

写的人：总工程师，2026-10-24。**没在 Unity 里编译过、跑过**（只过了 `Common/Tools~/compile_check`）。

## 为什么有它

本地第一次实测（`FromLocal/gate_clouds_test/问题.md` 的 gate_clouds_test-03，S0）：**蓝白/Gate Clouds/Build** 两次都在 `CopyProxyToUdon` 抛 “outdated script version”。原因有两层（阿白查到的）：

1. SDK 3.10.5 的 `UdonSharpEditorUtility.GetUdonSharpProgramAsset` **公开的重载接 `Type`**，接 `MonoScript` 的那个是 private。以前的搭建脚本按 MonoScript 反射去查，永远查不到已有的程序资产，每次都新建一个。
2. 新建的程序资产，SDK 要在**之后的** `EditorApplication.update` 里才把 `ScriptVersion` / `CompiledVersion` 升到 `CurrentVersion`。没升完就 `CopyProxyToUdon`，就抛这个异常。

各包的搭建脚本各有一份自己的写法（GateClouds、Overlay、天空、诗、Director……），有的还把 `CopyProxyToUdon` 的异常吞掉了。现在都换成这一份。

## 它做什么

| 方法 | |
|---|---|
| `Find(Type)` | 按 **Type**（SDK 的公开重载）查已有的程序资产，再扫一遍全部程序资产核对 `sourceCsScript`；有两个以上时报警告、用 SDK 给的那个 |
| `StateOf(Type)` / `AllReady(types)` | `Missing`（没有）/ `Initializing`（有，版本没到）/ `Ready`（`ScriptVersion` 和 `CompiledVersion` 都 = `CurrentVersion`，“2/2”）/ `NoScript` / `NoUdonSharp` |
| `CreateMissing(who, types, pathFor)` | 缺的才建；目标路径上已经有一个 SDK 认不出的资产时**不覆盖**，报错 |
| `RunWhenReady(who, types, build, pathFor, fail)` | **搭建菜单用**：都 Ready 就马上搭；不然先建缺的，排进 `EditorApplication.update` 等 SDK 初始化完（最多 180 秒）再搭。只有在“脚本版本到了、编译版本没到”时请一次编辑器模式的 U# 编译（`CompileSync`，默认选项）。**不手写版本号，不调 Force Upgrade**。超时报清楚每个资产的两个版本，不重建 |
| `RequireReady(who, types)` | 搭建函数被直接调（不经过菜单）时，**在动场景之前**先调：没 Ready 就抛异常、说清楚怎么办 |
| `AddComponent(go, Type)` | `UdonSharpUndo.AddComponent`（退路：`AddComponent` + `RunBehaviourSetup`）；程序资产要已经 Ready；加完查背后的 UdonBehaviour |
| `CopyProxyToUdon(proxy)` | 程序资产要已经 Ready；SDK 抛的异常**原样往上抛**（带类型和资产路径），不吞；拷完查背后的 UdonBehaviour |
| 菜单 **蓝白/U#/Program Asset Status (read only)** | 列出工程里每个 U# 类型的程序资产和两个版本，只读 |

全部走反射：没有 UdonSharp 的工程也编得过（`Available = false`，搭建脚本退回普通 `AddComponent` 并报警告）。有自己的 asmdef（`Lanbai.Common.Editor`，只在编辑器、自动引用）：没有 asmdef 的搭建脚本直接用得到，有 asmdef 的（字体的 `Lanbai.Fonts.Editor`）在 references 里加了它。

## 编辑器 reload（domain reload）了怎么办

排队等的搭建放在静态表里，编辑器一 reload（C# 编译完、某些导入）就没了。所以：

- **排队时把菜单路径记进 `SessionState`**（编辑器开着就一直在，reload 也在；关掉编辑器才清）。reload 以后工具自动**再点一次那个菜单**，Console 写一条 `[Lanbai U#] 编辑器 reload 过……自动再点一次（第 n 次）`。每个菜单最多自动续 3 次，再多就报错、不续了。
- **再点一次是安全的**：菜单是幂等的。程序资产已经建了，就按 Type 找到、复用，不会再建一个；还没初始化完，就再排一次队；已经 2/2 了，就直接搭。所以就算自动续没起作用（比如编辑器关掉又打开），**手动再点一次同一个菜单就能接上**。
- 只在“请一次 U# 编译（CompileSync）”和建资产时可能引起 reload；U# 编译本身不编 C#，一般不会 reload。
- 测试工具（`Engineering/UnityTest/`）自己排的队不是菜单：它也记在 `SessionState` 里，reload 以后**从头再跑一次**（新的输出文件夹，上一次的文件夹没有报告）；再 reload 一次就算 BLOCKED（退出码 2；批处理照样退出，不会挂住）。

## 排队的另外三条规矩（终审 r2）

- **进 Play 模式（离开编辑模式）时，排队中的搭建一律按失败结束**，Console 写清原因（“进 Play 模式了，排着队的 … 取消，没搭”）；进 Play 的那次 reload 也不自动续。回到编辑模式再点一次菜单。
- **重复的程序资产直接报错**（状态 `Conflict`）：同一个脚本有两个程序资产，U# 1.x 会让整个工程的 U# 编译失败，所以工具不挑一个接着用，菜单不搭、报出两个路径。只留一个，多余的照 `HANDOFF_CHATGPT.md` §F 挪走（经小楠确认），再点菜单。
- **从代码里调菜单（比如本地的 `LB_Remote`）时，被推迟执行要查得到**：每个菜单最近一次的状态是 `DEFERRED`（在排队等）/ `DONE` / `FAILED: 原因`，用 `Lanbai.Udon.LanbaiUdonPrograms.MenuStatus("<菜单路径>")` 查（存在 `SessionState`），日志里也写一行 `LANBAI_UDON_STATUS {"menu": "...", "status": "..."}`。**`ExecuteMenuItem` 返回 true 不等于搭好了**：看到 `DEFERRED` 就等它变成 `DONE` / `FAILED`。

## 谁换成了它

main 上（这次一起改了）：

| 包 | 文件 | 菜单（先等再搭） | 程序资产放哪（新建时） |
|---|---|---|---|
| 门的云 | `GateClouds/Editor/LanbaiGateCloudsBuilder.cs` | 蓝白/Gate Clouds/Build | `Assets/Lanbai/UdonPrograms/` |
| 门的驱动 | `Gate/Editor/LanbaiGateDriverBuilder.cs` | 蓝白/Gate/Build Driver（+ Test Clock） | 同上 |
| 第 6 幕 | `Act06_Dawn/Editor/LanbaiAct06Builder.cs` | 蓝白/Build/Act06 | 同上 |
| 第 7a 幕 | `Act07_Sea/Editor/LanbaiAct07Builder.cs` | 蓝白/Build/Act07a | 同上 |
| 遮罩球 | `Overlay/Editor/LanbaiOverlayBuild.cs` | 蓝白/Build/Overlay | 脚本旁边 |
| 门内 | `Act04c_Inside/Editor/LanbaiInsideBuild.cs` | 蓝白/Build/04c 门内（三个脚本） | 脚本旁边 |
| 天空 | `Sky/Editor/LanbaiSkyBuild.cs`（`EnsureProgramAsset` 也改成调它） | 蓝白/Sky/Build Sky、Create Preset Objects | 脚本旁边 |
| 第 9 幕 | `Act09_StarSea/Editor/LanbaiAct09Build.cs` | 蓝白/Build/Act09 | 脚本旁边 |
| 诗 | `Fonts/Editor/LanbaiPoemBake.cs`（asmdef 加了引用） | 蓝白/Fonts/Build Subtitles (v5) | 脚本旁边 |
| Director | `Director/Editor/LanbaiDirectorGen.cs` | 蓝白/Director/2 Wire Scene | 脚本旁边 |
| 测试工具 | `Engineering/UnityTest/`（测试定义的 `udon_programs`） | 蓝白/Test/…、`-executeMethod` | 默认 |

“程序资产放哪”只管**新建**的：已有的在哪都按 Type 找到、复用。

分支上的（我只能推 `pkg/engineering`，补丁在 `Engineering/D41_patches/`，各包合 main 以后打上）：`pkg/bus` 的 `Bus/Editor/LanbaiBusBuild.cs`（自己有一份 AddUdonSharp）、`pkg/mirrors` 的 `Mirrors/Editor/LanbaiMirrorsBuild.cs`（自己有一份 EnsureProgramAsset + UdonSharpUndo）、`pkg/clouds` 的 `Act08_Dusk/Editor/LanbaiAct08Builder.cs` 和 `pkg/palace` 的 `Palace/Editor/LanbaiPalaceBuilder.cs`（这两个调 `LanbaiGateCloudsBuilder.AddUdonSharp`，合 main 就跟着修好，补丁只是给菜单加“先等再搭”）。

**不改的**：`FromLocal/` 里本地的测试脚本（`LB_Udon.cs`、`LB_GateTest_Udon.cs`，D-15：本地的东西本地改）。

## 给阿白

- 你本地对 `Assets/Lanbai/GateClouds/Editor/LanbaiGateCloudsBuilder.cs` 的那处最小修复（`20261024-164251/diffs/`：`GetUdonSharpProgramAsset` 改传 `Type`）已经包含在这次里（同一个原因，换成共用工具，连 “新建以后要等初始化” 一起解决）。**以后同步时，这个文件被仓库的版本覆盖是对的**：同步脚本会把它列成“本地改过”，照 §F 的批量替换流程用 `-Force` 盖掉即可。
- `LB_GateContinuation.cs`（分阶段等程序资产的测试辅助）以后用不到：搭建菜单和测试工具自己会等。删不删你定；留着也不冲突。
- 第一次点菜单时，如果程序资产是新建的，Console 会先写一条 `[Lanbai U#] … 程序资产还没初始化完，等 SDK…`，然后自动接着搭（不用再点一次）。等了 180 秒还没好，会报每个资产的两个版本：**不要点 Force Upgrade**，先重启一次 Unity（让 SDK 在启动时做它自己的升级），再点一次菜单；还不行就把 Console 原样推回来。
- 磁盘上已经有、版本是 0 的旧程序资产（`UdonPrograms/LanbaiGateClouds.asset` 等）会被找到、复用，等 SDK 把它升好；不会再新建一个。
