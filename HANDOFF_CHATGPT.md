# HANDOFF_CHATGPT · 本地 Unity 接管入口（给 ChatGPT「阿白」）

> **状态：已接管**（2026-10-24，阿白已确认能操作小楠的电脑和 Unity 工程 `dream`；D-40a #8）。各项测试的真实状态见 §B。
> 写的人：总导演（云端会话「蓝白总控安排」）。最后更新：2026-10-24 21:40 UTC（第 2 版：收下了阿白第一次接管的结果和三份独立复核）。
> 这一页只放三样东西：入口、规矩、真实状态。细节都链到原文件，不抄过来（抄的会过时）。
> **冲突时的优先级：**
> 1. 小楠本人的话；
> 2. `Art/总导演裁决.md`；
> 3. 比这一页“最后更新”还晚、并写明“改 HANDOFF_CHATGPT §x”的 HANDOFF_LOG 条目；
> 4. 这一页；
> 5. 其他文件。

---

## 0. 先读这七条

1. **分工。**
   - 云端（总导演、总工程师、各制作包、独立审片）负责设计、制作、审核，以及合并 GitHub。
   - **阿白负责本地**：把 `main` 上审过的东西搬进 Unity，搭场景、编译、排错、截图、测性能，然后回报。
   - 第 1、2、12 幕的路和整体组装以后也归本地（`CONTROL_总控.md` §0）。**现在不做**：等车、灯与杆、站牌套件都进 main，总导演在 HANDOFF_LOG 写了组装说明再做。
   - **小楠**保留最终的审美决定权（D-40a #7），也亲自做三件事：VRChat 登录、账号操作、上传世界。
2. **Unity 工程只有一个写入者，就是你。** 以前的本地 Claude 会话「世界创建」已经停用。`LB_Remote`（旧的远程小助手）只能由你用（§A）。
3. **顺序：先只读，再备份，最后才写。** 高风险操作先备份、等小楠确认（§F）。
4. **只用 `main`，只推 `FromLocal/`。** `pkg/*` 分支是半成品，不进 Unity。
5. **测试状态按事实写。**
   - 没跑过的测试，写“未测”；依赖缺了，写 BLOCKED，绝不写通过。
   - 头显里没看过的，不许写“已通过”。
   - 工具做好了，不等于验收完成。
6. **你看不到云端的上下文。** 一切以仓库里的文件和你在电脑上实际查到的为准。
7. **每次开工先看 HANDOFF_LOG 有没有新的一条**：`git -C <clone> fetch origin`，再 `git -C <clone> log origin/main -5 -- HANDOFF_LOG.md`。有就先读。

---

## A. 项目基础信息

**来源：阿白 10-24 的接管核对**（`FromLocal/takeover/20261024/接管核对.md`、`inventory.json`）。以后有变化，以你最新的核对为准，并写进回报。

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/chengnan024-lang/lanbai-assets`，**公开**（任何人都能看到你推的东西，见 §F），默认分支 `main` |
| 本机原 clone | `E:\IDMdownload\VRCC\lanbai-assets`（停在 `480e711`）。10-24 普通 pull 两次中断，**这个 clone 不动** |
| 本机安全检出 | 阿白另建的浅克隆 + 部分检出（D-41 #5 批准）。以后都用它；路径以你的报告为准 |
| Unity 工程 | `E:\IDMdownload\VRCC\dream`，**本身没有 git** |
| 正式世界场景 | `Assets/Lanbai/Scenes/Lanbai.unity`（**不改**）。Build Settings 的场景列表是空的 |
| 测试场景 | `Assets/Lanbai/Tests/GateTest.unity`：没有 VRC 场景描述符，ClientSim 起不来 |
| Unity | 2022.3.22f1（`E:\VRR\2022.3.22f1\Editor\Unity.exe`）；Unity Hub 3.22.3 |
| VCC | 2.4.5（`E:\VRR\VRChat Creator Companion\`） |
| SDK | Worlds / Base 3.10.5（嵌入 Packages）；UdonSharp、ClientSim 跟着 SDK 装 |
| PPv2 | 3.4.0（SDK Base 声明依赖 3.2.2；差异照实记，不动） |
| TMP | manifest 写 2.1.6，lock 写 3.0.6；Essential Resources 已经在。**不要再 Import**（会覆盖 TMP Settings） |
| 渲染 | Built-in、Forward、Linear、HDR；`lightsUseLinearIntensity = true`；雾只留 Exponential |
| Vertex Compression | 10-24 小楠批准后改成 **3846**（Color、TexCoord0–3 不压缩，D-40b #3） |
| 机器 | Windows 11 家庭中文版 10.0.26200；i9-13980HX；约 31.6 GiB 内存；RTX 4060 Laptop 8 GB，驱动 610.62 |
| 头显 | Quest 3 + Virtual Desktop（小楠确认可用）。怎么把测试送进头显还没定（§C 第 6 步） |
| 其他 | Git 2.56.0、Python 3.11.1；Editor.log 默认在 `C:\Users\29742\AppData\Local\Unity\Editor\`（会被别的工程覆盖，**dream 用 `-logFile` 写到 E 盘**） |
| 时间 | HANDOFF_LOG 用北京时间；git 用 UTC；你的运行文件夹按本机时间（America/New_York）命名，报告里注明时区 |

**拷什么，不拷什么**（同步脚本也是这一套规则）
- 只拷 HANDOFF_LOG 那一条“同步：”行点名的路径，拷到 `Assets/Lanbai/<文件夹名>/`。
- **永远不拷：**
  - `Art/`、`Research/`、`FromLocal/`、仓库根目录的文件；
  - `Engineering/`，测试工具 `Engineering/UnityTest/` 到了按它的 README 拷，是唯一的例外；
  - 任何一层叫 `Source`、`Renders`、`__pycache__` 的文件夹，名字以 `~` 结尾的文件夹；
  - `.py .pyc .blend .blend1 .ps1 .sh` 文件。
- 为什么：`FromLocal/` 里有 `LB_Journey`、`LB_GateTest` 的 .cs 副本，拷进去会重复定义，整个 Assembly-CSharp 编不过；`.blend` 会让 Unity 去调 Blender。
- **只增不删。**
  - 仓库里没有 `.meta`，工程里的 `.meta` 和本地生成的东西都必须留着：各包的 `Generated/`、`Generated_*.asset`、`Grading/Profiles/`、`Act04c_Inside/Materials/`、`UdonPrograms/*.asset`。
  - 例外：重拷 `Director/` 会把 `LanbaiActDispatcher.cs` 换回模板，拷完要重跑 `蓝白/Director/1 Generate Dispatcher`。
  - 手工拷只用 robocopy，**先演练（`/L` 只列不拷）**：
  ```
  robocopy "<检出>\<包>" "E:\IDMdownload\VRCC\dream\Assets\Lanbai\<包>" /E /L /XD Source Renders __pycache__ Docs~ Tools~ Source~ Originals~ /XF *.py *.pyc *.blend *.blend1 *.ps1 *.sh .gitignore /NP /LOG:"<运行文件夹>\copy_<包>_dryrun.txt"
  ```
  - 演练清单里“会被覆盖”的文件，和上一次拷进去的版本比哈希；不一样就是本地改过的，先问小楠。确认以后去掉 `/L` 再跑一次，日志放进运行文件夹。robocopy 退出码 0–7 是成功，≥ 8 是失败。
  - **禁止**：`/MIR`、`/PURGE`、`/MOV`、`/MOVE`、资源管理器“剪切”、任何“同步 / 镜像”模式、先删再拷。目标里多出来的文件一律不动，写进报告。
- **旧副本和重名 shader。** 拷之前跑 `git -C <检出> diff --name-status --diff-filter=DR <上次拷进去的 commit> HEAD -- <包>`，列出仓库里删掉或改名的文件，在 Unity 里对应的旧副本交小楠决定挪不挪。
  - 已知一处：`Assets/Lanbai/Delivered/lens_tech/` 里有 v1 的 `Lanbai/Overlay` shader，和 `Overlay/Shaders/Lanbai_Overlay.shader`（v2）同名。**导入门内 / Overlay 之前必须先处理**，否则 `Shader.Find` 会随机拿到旧的那个。
- **已知的本地副本**：`Rain/Shaders/LanbaiVR.cginc` 在仓库里已经挪到 `Common/Shaders/`。

**工程里只在本地有的东西**
- `LB_Journey`（时间轴，UdonSharp）在 `Assets/Lanbai/Scripts/`，挂在世界根的 `Systems/Journey` 上。仓库里的副本在 `FromLocal/code/timeline_v1/`，只作参考。
- `Lanbai.Tests.LB_GateTest`（`Tests/Editor/`）：Build / Apply / Shoot / Perf / Verify / StatsBegin / StatsRead，**没有菜单**。
- `LB_Remote`（`Assets/Lanbai/Editor/Remote/`，队列在 `dream\LanbaiRemote\requests|results\`）：
  - 你可以用它在 Unity 里执行命令；别的会话、别的程序不许往它的队列里放请求。
  - 它的通用截图是 8 位的，**不能当验收截图**；验收截图一律走 ARGBHalf → PPv2 → 8 位。
  - 不要包装或调用 `LB_GateTest.NewScene("force")`：它会新建并覆盖 `GateTest.unity`。
- 你自己加的测试辅助 `Tests/Editor/LB_GateContinuation.cs` 可以留着，测试工具到了以后再决定去留。
- 上一任的本地记录（只读）：`Assets\Lanbai\蓝白_使用说明.txt`、`E:\IDMdownload\VRCC\Claude outputs\` 里的「进度与决定」。

**导入顺序和“以谁为准”**
- **门测试只拷门需要的东西**：`Common/`、门那四条 HANDOFF_LOG 点名的 `Gate/`、`GateClouds/`、`Tear/` 文件。**不拷 `Director/`、`Sky/`，不点任何 `蓝白/Director/…` 菜单。**
- 门测试以后的导入，以 HANDOFF_LOG 为每一包写的条目为准：门内、天空、海、第 6、7a、9 幕、诗都会各有一条，**现在还没有**。`Engineering/README_集成.md` §6 / §9 是背景说明；它和 HANDOFF_LOG 冲突的地方，以 HANDOFF_LOG 和 D-40b 为准：
  - §9 每包流程里的 Director 1/2/3 步；
  - “天空先拷”；
  - “拷四个整文件夹”。
- HANDOFF_LOG 最新的在最上面，**新条压过旧条**。

---

## B. 当前真实进度（三层验收，D-40a #4）

快照：2026-10-24 21:40 UTC。**这张表由总导演维护**，`main` 有新合并、`FromLocal/` 有新结果时更新。

三层的状态只用这几个值：未测 / 通过 / 不通过 / 这一层测不了。不适用写“—”。BLOCKED 的测试，那一层记“未测（BLOCKED：缺 X）”。“Unity 桌面”“VR 头显”两栏只认 `FromLocal/` 里对应版本的证据。

| 内容 | 云端制作 | 进 main | 离线检查（compile_check + 总导演终审） | Unity 桌面 | VR 头显 | 下一步 |
|---|---|---|---|---|---|---|
| 门（Gate / Tear / Tentacles）+ 门的云 v1.5 + 驱动 v1.2 + 第 10 轮第 1 批 | 完成（剩 4 项等实测） | ✅ | 通过 | **不通过**：门 Build 过了，云 Build 被搭建脚本的 bug 挡住（`gate_clouds_test-03`），然后资源不够崩溃（`-05`）。截图、性能、Play 都未测 | 未测 | 等 D-41 #1 的修复，以及小楠处理内存和 C 盘（D-41 #6） |
| `Common/` | 完成 | ✅ | 通过 | 已导入、已编译（10-24） | — | — |
| 调色 Grading | 完成 | ✅ | 通过 | 10-08 编译过、建过 profile；测试卡、Bloom 探针没交回 | 未测 | 门测试之后 |
| 门内（4c、5）+ Overlay | 完成 | ✅ | 通过 | 未测（BLOCKED：没有导入条目；`Lanbai/Overlay` 重名） | 未测 | 门测试之后 |
| 天空 Sky | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后 |
| 海（Sea、7a、7c） | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后 |
| 第 6 幕 晨 | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后；先要有 Common、GateClouds、Sky、Sea、Overlay、Clouds_v2 |
| 第 9 幕 星海 | 完成 | ✅ | 通过 | 未测（缺第 8 幕：第 9 幕只写 5–9 个天空量，其余来自第 8 幕） | 未测 | 等第 8 幕 |
| 诗与字体 v4.1、Director v1.1、雨 | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后 |
| 车（PAZ-672M） | 制作中（座椅第 5 轮） | ❌ | — | 未测（BLOCKED：切片没交） | 未测 | 切片 = 菜单 `蓝白/Build/车 切片`（类 `LanbaiBusSliceBuilder`），先合 main |
| 宫殿（7b） | 终审中 | ❌ | 进行中 | 未测 | 未测 | — |
| 第 8 幕 暮 | 制作中 | ❌ | — | 未测 | 未测 | — |
| 镜与白（第 9 幕的镜 + 第 10 幕） | 退回修改（D-41 附近的终审） | ❌ | 不通过 | 未测 | 未测 | — |
| 灯与假醒（第 11 幕）、站牌套件 | 暂停 / 没开始 | — | — | — | — | 站牌：D-40a #1 |
| 测试工具 `Engineering/UnityTest/` + 同步脚本 v2 + D-41 共用 U# 工具 | 完成 | ✅（ac4f6a0） | 通过（两轮终审） | 未测 | — | 复测条目见 HANDOFF_LOG（北京 10-25 11:40） |

---

## C. 接管与测试的步骤

**10-24 第一次接管已经做完**，结果在 `FromLocal/takeover/20261024/`。以后换机器、长时间中断、或者小楠要求重新接管时，照这一节重做。每一步都可以重做；中途出问题就停下，照实写进报告。

**第 1 步：只读检查**
- 只读磁盘上的文件。**不启动 Unity**，不点 Unity Hub / VCC 的 Open：打开工程会重编脚本、改写程序资产、重存 ProjectSettings。
- Unity 已经开着，就停下来问小楠。
- 要查的：
  - 谁在用工程；
  - 各个版本（`ProjectVersion.txt`、`Packages\manifest.json`、`vpm-manifest.json`）；
  - 项目设置：`m_ActiveColorSpace`、`VertexChannelCompressionMask`、`m_FogStripping`、`m_CurrentQuality`；
  - `Assets\Lanbai\` 的目录树和修改时间；
  - `Assets\Lanbai\Delivered\` 的内容，以及所有 `.shader` 文件里的 `Shader "…"` 名字，标出重名的；
  - 两套调色（`Grades/` + layer 4，`Grading/` + layer 22）；
  - `LB_Remote` 的队列里有没有没处理的请求；
  - 备份；
  - clone 的 `git status`、`.git\index.lock`、`git log origin/main..HEAD`（有输出 = 本地有没推上去的旧提交：停下来问）；
  - 环境；
  - 上一任的本地记录。

**第 2 步：记录和备份**
- 写 `FromLocal/takeover/<YYYYMMDD-HHMMSS>/接管核对.md`（人读）和 `inventory.json`（机器读）。
- 整工程备份：排除 `Library`、`Temp`、`Logs`、`obj`、`Build`，打成 zip 放到 `E:\IDMdownload\VRCC\Backups\`，写大小和 SHA256，逐文件核对。做法照 10-24 那次。
- 备份做完之前，不启动 Unity。

**第 3 步：环境核对。** 和 §A 对。**不升级、不降级 Unity、VCC、SDK、任何包。**

**第 4 步：写一页计划**：拷什么、改哪几个文件、动不动 ProjectSettings。交小楠确认。

**第 5 步：导入和编译**（小楠说可以以后）
1. 用安全检出更新到 `main` 的最新版（`git pull --ff-only`）。失败就停，不手修 HEAD。
2. 按 §A 的规则拷：先演练，再拷，日志进运行文件夹。
3. 编译：每次关或重开 Unity 之前，先把 Editor.log 拷进运行文件夹（`editor_<序号>.log`）；`console_full.txt` 就是它的原样拷贝。
   - 编不过：先停，把日志推回来告诉小楠。小楠同意以后，只对报错的那几行做能编过的最小修改，不改 JSON、数值、材质；diff 放进 `diffs/`。以后同步会以云端合进 main 的修法为准。
   - 不要在 build 模式下调 UdonSharp 编译：10-08 这样做出了 5 171 条假报错，其中 4 023 条是 CS0518。
   - 不要自己新写任何 AssetPostprocessor：哪怕只管几个文件夹，也会让全工程的模型重新导入。包自带的照常拷。
4. **弹窗一律按“不改”回答：**
   - Hub 提示换版本或升级：取消；
   - API Updater：选 **No Thanks**；
   - VCC / SDK 的更新、Resolve：不点；
   - TMP Importer：不点 Import；
   - 编译出错、问要不要进 Safe Mode：选 **Enter Safe Mode**，记下错误，关掉，问小楠。

**第 6 步：截图和性能**
- 优先用测试工具（`Engineering/UnityTest/README_UnityTest.md`，合 main 以后 HANDOFF_LOG 会写一条）。
- 工具没到之前，门照 HANDOFF_LOG 的四条做，**从旧到新**：
  1. 「门的云 GateClouds v1.5」；
  2. 「门的总驱动 LanbaiGateDriver」；
  3. 「门的驱动更新到 v1.2」；
  4. 「门的云第 10 轮第 1 批」。

  新条压过旧条：`_Stars` 用 0.055；Console 的成功行是 `built: deck, 38 cards (10 towers), 6 beams`。
- **截图**：HDR 链路（ARGBHalf → PPv2 → 8 位），命名 `<机位>_unity_t<秒>.png`。
- **性能**，每一行写清楚是哪一种：

  | 类型 | 什么时候 | 怎么量 | 能判预算吗 |
  |---|---|---|---|
  | 编辑模式估算 | 门：U7 155.10、U8fwd 169.65，三种状态（全开 / 关云海 / 关整个 GateClouds 和两束光） | 24 次取中位数和范围 | 只作估算 |
  | Udon 毫秒 | 150.3、166.15、约 178 | 见下面的 ClientSim | — |
  | Play + 头显 | U7、U8 166.15、U8+7 173.15 | 每个 10 秒，取中位数和 p95，列 GPU 最贵的 10 项（账本 §三、§五） | **只有这一种能判预算**。第 4 幕：世界 ≤ 7.1 ms + PPv2 1.2 ms = 8.3 ms |

  - 账本 §三 #5 要求换 Quality 档，属于改 ProjectSettings，先问小楠。
  - 头显的实测再汇总一份到 `FromLocal/perf.md`。
- **ClientSim / Udon 计时**：把搭好的场景另存为 `Assets/_LanbaiTest/GateTest_play.unity`，只在这份拷贝上加 VRC Scene Descriptor，再进 Play 量；`GateTest.unity` 本身不加。做不到就记“未测（ClientSim 起不来）”。
- **动态检查**（D-40a #5），每一项单独记：高光闪烁、纹理闪烁（摩尔纹）、空间尺度、双眼立体（闭左眼 / 闭右眼）、光照变化、VR 舒适。
  - Unity 层的头部微动序列（±2 cm、±1°、90 fps）由测试工具出。工具没到之前记“未测（等工具）”，**不拿静态截图代替**。
  - 头显层由人看。门那几条要看的：「门的总驱动」第 7 条，加上「第 10 轮第 1 批」最后一句（细银边爬不爬、闪不闪）。
- **头显通路还没定**，两条路都碰到 §F 的界线：
  - Unity Play 进头显：要装 XR 插件，属于改 Packages；
  - VRChat SDK 的 Build & Test：要登录 VRChat，只有小楠能做。

  总工程师会出方案。在那之前，头显层记“这一层测不了（没有头显通路）”。**不要自己装 XR 插件。**

**第 7 步：回传**：见 §E。

---

## D. 第一批测试（小楠定的优先级；可以按“东西到没到”调整，但依赖缺了只能记 BLOCKED）

| 优先 | test-id（= `FromLocal/` 下的文件夹名） | 测什么 | 现在 | 依赖 |
|---|---|---|---|---|
| 1 | `bus_slice` | PAZ-672M 车厢切片：材质；贴图压缩（Crunch / BC7，法线 BC5 / Crunch，0.5 m）；mip；光照图接缝；铬件和倒角的高光闪烁；法线强度；每处细节标“在 20 px/° 下看得出 / 看不出”（面板约 14 px/° 那一栏只作参考） | BLOCKED：切片没交 | 车把切片交进 main，HANDOFF_LOG 写一条 |
| 2 | `gate_clouds_test` | 触手之门：机位 key / U7 / U8fwd / U8side / rear；三种状态的性能；Udon；头显 | **进行中**：S0 问题 -03、-05 开着 | D-41 #1、#6 |
| 3 | `act06_test` | 第 6 幕晨，三个视向（`Act06_Dawn/README_Act06.md` §0），车门方向的 VR APL | 门测试之后 | Common、GateClouds、Sky、Sea、Overlay、Clouds_v2；正式场景要先拷进沙盒再搭 |
| 4 | `act01_spawn` | 第 1 幕出生点：构图、雨夜、第一印象 | BLOCKED | 车、灯与杆、站牌套件 |
| 5 | `palace_hotspot` | 宫殿：画面和性能热点（≤ 6.4 ms） | BLOCKED | 宫殿过审、合并 |

其他包 README 里已经用过的回传文件夹名照用：`04c_test`、`act07a_test`、`sea_test`；以后还会有 `bus_test`、`07b_test`、`act08_test`、`mirrors_test`、`white_test`。

---

## E. 回传协议

**路径**
- 每跑一次一个新文件夹：`FromLocal/<test-id>/<YYYYMMDD-HHMMSS>/`，不覆盖旧的。
- 每个 test-id 下面一份 `问题.md`，跨多次运行一直用同一份。
- 接管核对放在 `FromLocal/takeover/<YYYYMMDD-HHMMSS>/`。

**每次运行的文件夹里放什么**（照 10-24 你的做法；`FromLocal/gate_test/README_说明.md` 也是样板）

| 文件 | 内容 |
|---|---|
| `manifest.json` | 见下面单列 |
| `README_说明.md` | 做了什么；自己定了什么（JSON 和 README 里没给、你推定的值）；没做的；Console 分类；对上的和没对上的 |
| `shots/` | HDR 截图 |
| `seq/` | 动态序列 |
| `console_full.txt`、`console_errors_warnings.txt` | Editor.log 原样，包括 UdonSharp |
| `perf.md` | 一行一个“机位 × 状态”，列：类型（估算 / Play + 头显）、分辨率和视角、GPU 毫秒（中位数和范围，或中位数和 p95）、CPU 毫秒、draw / batches / SetPass / 三角面 / 投影物体、两个驱动的 Udon 毫秒、QualitySettings |
| `diffs/` | 你改过的每一个文件的 diff |

`manifest.json` 里要有：
- test-id，测试场景（原场景还是沙盒拷贝）；
- 照做的是 HANDOFF_LOG 的哪几条（写条目标题）；
- `copied`：每个拷进 Unity 的文件夹，拷完那一刻检出的 commit。这次没重拷的写“10-08 / 29fa6f2”或“不知道”；
- Unity / SDK / 各包的版本、机器、测试工具的版本；
- 每一步的状态：`done / failed / skipped / BLOCKED`，BLOCKED 要写 `blocked_by`；
- 三层状态 `{blender_offline, unity_desktop, vr_headset}`，取值“未测 / 通过 / 不通过 / 这一层测不了”；
- 静态、动态分两块记。

**谁能记“通过”**（D-41 #4）
- `vr_headset` 只能由真戴过头显的人填。
- `unity_desktop`：测试工具退出码 0，只记“工具检查全过（待总导演看图）”；这一层的“通过”由总导演看完截图后在 §B 记。
- 三层都过了以后，小楠看了实际效果仍然可以要求改（D-40a #7）。

**用测试工具跑的时候**：工具的输出文件夹原样就是运行文件夹。
- `summary.md` 代替 `README_说明.md`；另写一页 `README_说明.md`，只记工具没记的：自己定了什么、手动项、头显。
- `console.jsonl` 代替两个 console 文件；`perf.json` 代替 `perf.md`。
- 工具里的状态对应关系：pass = 工具检查全过；fail = 不通过；blocked / not_tested / pending_cloud / error = 未测。

**问题分级和处理**（D-41 #3）
- 分级：
  - **S0 阻断**：编不过、导入失败、崩溃、违反 VR 舒适铁律（圣经 §1.8）、闪光超限；
  - **S1 严重**：画面明显错；超性能预算（只按 Play + 头显判）；
  - **S2 一般**：和参考图有可见差异，但不影响读画面；
  - **S3 建议**。
- `问题.md` 一行一个问题，列：编号（`<test-id>-NN`）、分级、层、现象、证据（文件路径）、状态。
- 状态的取值：开着 / 云端已修 `<commit>` / 桌面复测通过 `<运行>` / 头显复测通过 `<运行>` / 已关 / 不修（写理由）。
- 总导演在 HANDOFF_LOG 里写“问题处理：`<编号>` 定 S? / 关闭 / 不修（理由）”，你下次推送时照抄进 `问题.md`。头显层的问题，没有“头显复测通过”不能关。小楠可以开新问题，也可以重开任何已关的问题。

**Git**（在安全检出里做；所有命令都写 `git -C <检出>`）
```
git -C <检出> pull --ff-only origin main
git -C <检出> add FromLocal/<test-id>/          # 只加这一个路径，加完 git status 确认没有别的
git -C <检出> -c user.name="Lanbai-local (阿白)" -c user.email="<和你 10-24 提交时同一个>" commit -m "FromLocal/<test-id>: <一句英文>"
git -C <检出> push origin HEAD:main
```
- **不碰 `FromLocal/` 以外的任何文件。** 云端的会话都不改 `FromLocal/`，所以这条路不会和云端冲突。
- `git status` 不干净：不要 stash、不要 reset，先问小楠。
- push 被拒（non-fast-forward）：再 `pull --ff-only` 一次再推；还不行就停。
- **禁止**：`push --force`、`reset --hard`、`clean`、`checkout -- .`、`--global` 改身份。
- **大文件**：提交前跑 `Get-ChildItem <运行文件夹> -Recurse -File | Where-Object Length -gt 95MB`。有输出，就把那些文件留在本地 `E:\IDMdownload\VRCC\FromLocal_big\<test-id>\<运行>\`，报告里写路径和大小。`.rdc`、Profiler `.data`、zip、工程备份一律不提交。
- **编码**：你写的 `.md`、`.json`、`.txt` 一律 UTF-8 无 BOM、LF。PowerShell 5.1 里用 `[IO.File]::WriteAllText($p,$s,(New-Object Text.UTF8Encoding $false))`，不要用 `>`、`Out-File`、`Set-Content`。JSON 提交前用 Python 读一遍，确认能解析。

**通知和接收**
- 推完以后，用一句话告诉小楠路径。总导演的定时巡检（每 2 小时 40 分钟）也会看 `FromLocal/` 有没有新的运行文件夹。
- 总导演读结果、定分级，再分给负责的会话：
  - 编译、性能、工具、Udon、搭建脚本 → 总工程师；
  - 门 → 门；门内、Overlay → 门内；海、7a → 海；天空、第 9 幕 → 天空；第 6、8 幕 → 云；宫殿 → 宫殿；车的切片 → 车；镜与白 → 镜与白；
  - 第 1 幕的组装问题回给你；它的料按件给车、灯与杆、站牌套件。
- **复测流程**：云端修好、合进 main → HANDOFF_LOG 写一条“复测 `<test-id>`：`<问题编号>`”，第一行是“同步：”行 → 你用同一个 test-id 再跑一次，结果放新的运行文件夹 → 更新 `问题.md`。

---

## F. 协作边界（小楠 10-24 定）

- **只有阿白写本地 Unity 工程。** 云端照常在自己的分支上做，不等本地。
- **动手前先核实**：当前的文件、进程、版本、未保存和未提交的改动。不覆盖已有的成果；不认识的改动，先问。
- **高风险操作先备份，并经小楠确认。** 包括：
  - 删除任何东西：要删就挪到 `E:\IDMdownload\VRCC\_to_delete\<YYYYMMDD>\<原相对路径>`，在 `Assets` 外面；`.meta` 一起挪，挪之前关 Unity，清单写进报告。**不要在 `Assets` 里建 `_to_delete`**；
  - 批量替换，包括同步脚本的 `-Force`；
  - 改 `ProjectSettings`、`Packages`、SDK、VCC；
  - 改正式世界的场景；改 `LB_Journey`；
  - 任何架构上的改动。技术架构归总工程师；HANDOFF_LOG 里 09-28 那几条“技术怎么实现由你决定”，作废。
- **不手调数值**：材质、JSON、LOD 照包里的来。超预算、不好看，照实报，不自己砍。
- **JSON 和 README 里没给的值**：只在测试场景里推定，写进“自己定了什么”；正式场景里不推定，先问。
- **没有 HANDOFF_LOG 的明文，不把门接进正式世界，不点 `蓝白/Director/2 Wire Scene`。**
- 各会话不能假定别人知道自己的上下文。
- 没完成的 VR 测试，不许标成通过。
- **资源**：启动 Unity 之前，先看 C 盘、E 盘的空间和可用内存。不够就停，告诉小楠（D-41 #6）。不关小楠的程序，不清理小楠的文件。
- VRChat 登录、账号操作、上传世界：只由小楠做。
- **仓库是公开的**（D-41 #7）。不推这些东西：
  - 密码、令牌、登录状态；
  - `UserSettings` 的内容（只记哈希，10-24 你就是这么做的）；
  - 小楠的私人文件，以及与项目无关的本机信息；
  - 别人有版权的图片（只写链接）。
  路径、版本、硬件型号可以写。

---

## G. 已知的坑和已经裁掉的矛盾

- **坑**：
  - `CONTROL_总控.md` §6 那 13 条；
  - 第 5 步那几条：UdonSharp 的 build 模式、自写的 AssetPostprocessor、弹窗；
  - 编辑模式下的 `Camera.Render()`，ProfilerRecorder 和 UnityStats 看不到；
  - 大 pull 会中断：用安全检出；
  - **各包搭建脚本建 U# 程序资产的 bug**（D-41 #1，总工程师在修）。
- **已经裁定的**（D-40b、D-41）：
  - 主座位眼位 (0.55, 1.70, 2.05)；
  - “看不看得见”按 20 px/° 判，面板约 14 px/° 只作参考；
  - Vertex Compression：Color + TexCoord0–3 不压缩；
  - 性能按 Play + 头显判；
  - 接管开关以 `README_集成.md` §3 为准；
  - 天空在门测试之后导入；
  - overlay 通道上，出生淡入优先。

## H. 名词

- **小楠**：项目的主人。
- **总导演 / 总控**：云端会话「蓝白总控安排」。
- **总工程师**：云端会话，管技术和测试工具。
- **「网络搜索协助」**：能上网查资料的云端会话。
- **「世界创建」**：以前的本地会话（它管云端叫“小克”）。
- **t**：时间轴秒，出发 = 0。乐句标签 U0–U12、F0–F16 在 `FromLocal/cues.json`。
- **E**：线性照度，灯的 Inspector 值。
- **APL**：画面平均亮度（sRGB 亮度 0–255）。
- **FSE**：全屏透明层的等效数。
- **D-xx**：`Art/总导演裁决.md` 里的裁决编号。

## I. 文档地图（按读的顺序）

1. 这一页。
2. `HANDOFF_LOG.md`：云端写给本地的，最新的在上面。
3. `Art/总导演裁决.md`：所有裁决，压过圣经。最上面几条（D-40a、D-40b、D-41）和你直接有关。
4. `Engineering/README_集成.md`：背景说明，冲突时以 HANDOFF_LOG 为准。
5. `Art/ART_BIBLE.md`：§1.6 光照和材质、§1.8 VR 舒适、§1.9 性能、§9 截图清单。
6. `Engineering/ledgers/README_账本.md`：性能账本和实测协议（§三、§五）。
7. `CONTROL_总控.md`：协作约定，§6 是 Unity 的坑。
8. 各包的 README：自己的菜单、要截的图、回传要求。
9. `FromLocal/gate_test/README_说明.md`，以及你 10-24 的报告：回报写法的样板。
10. `Lanbai_Handoff.md`：**历史文件**。只适用于 Claude 的部分，不适用。
11. `Engineering/UnityTest/README_UnityTest.md`：测试工具。还在终审，到了 main 会在 HANDOFF_LOG 写一条。
