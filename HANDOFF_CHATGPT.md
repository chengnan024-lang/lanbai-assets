# HANDOFF_CHATGPT · 本地 Unity 接管入口（给 ChatGPT「阿白」）

> **状态：待接管**（`Art/总导演裁决.md` D-40a #8）。阿白确认能操作小楠的电脑和 Unity 工程 `dream` 之前，本地部署一律记“待接管”，不记“已验收”。
> 写的人：总导演（云端会话「蓝白总控安排」）。最后更新：2026-10-24 UTC。
> 这一页只放三样东西：入口、规矩、真实状态。细节都链到原文件，不抄过来（抄的会过时）。冲突时的优先级：`Art/总导演裁决.md` > 这一页 > 其他文件。

---

## 0. 先读这六条

1. **分工。**
   - 云端（总导演、总工程师、各制作包、独立审片）负责设计、制作、审核，以及合并 GitHub。
   - **阿白负责本地**：把 `main` 上审过的东西搬进 Unity，搭场景、编译、排错、截图、测性能，然后回报。
   - **小楠**保留最终的审美决定权（D-40a #7），也亲自做三件事：VRChat 登录、账号操作、上传世界。
2. **Unity 工程只有一个写入者，就是你。** 以前的本地 Claude 会话「世界创建」已经停用。动手之前，先确认没有别的会话或程序开着 `dream`。
3. **顺序是：先只读，再备份，最后才写。** 高风险操作必须先备份，并且等小楠确认，见 §F。
4. **只用 `main`，只推 `FromLocal/`。** `pkg/*` 分支是半成品，不进 Unity。
5. **测试状态按事实写。**
   - 没跑过的测试，写“未测”。依赖缺了，写 BLOCKED，绝不写通过。
   - 头显里没看过的，不许写“已通过”。
   - 工具做好了，不等于验收完成。
6. **你看不到云端的上下文。** 一切以仓库里的文件和你在电脑上实际查到的为准。这一页标了“需核对”的东西，仓库里没有记录，要你去电脑上查。

---

## A. 项目基础信息

**以下是 2026-10-08 本地测试时记下的快照，不是现在的状态。** 来源：`FromLocal/gate_test/README_说明.md:5`、`FromLocal/gate_test/reports/GateTest_Verify.txt:41-44`、`CONTROL_总控.md` §6 #12。接管时逐项重新核对。

| 项 | 值 | 备注 |
|---|---|---|
| 仓库 | `https://github.com/chengnan024-lang/lanbai-assets`（私有），默认分支 `main` | 小楠的 GitHub 账号，登录走 Git Credential Manager（`Lanbai_Handoff.md:83`） |
| 本机仓库 clone | `E:\IDMdownload\VRCC\lanbai-assets` | **不要 clone 进 `Assets`**（`README.md:12`）。10-08 那次停在 `29fa6f2` |
| Unity 工程 | `dream`，按 10-08 的堆栈路径是 `E:\IDMdownload\VRCC\dream` | **需核对**（`Lanbai_Handoff.md:23`：路径以磁盘为准）。**工程本身没有 git**（`README_说明.md:149`） |
| Unity | 2022.3.22f1 | 渲染管线 Built-in，Forward，色彩空间 Linear，HDR FP16 |
| VRChat SDK | Worlds 3.10.5（`Packages/com.vrchat.worlds`） | UdonSharp 1.x 跟着 SDK 一起装，确切版本**需核对** |
| VCC（Creator Companion） | **需核对**（仓库里没有记录） | 不要自己升级或降级 SDK、VCC（§F） |
| Post Processing v2 | 3.4.0 | `.cube` 导入器（Route C）在不在，**需核对**（圣经 §9 #12） |
| TextMeshPro | 字体套件按 3.0.x 写的，装的是哪个版本**需核对** | 先跑一次 “Import TMP Essential Resources” |
| ClientSim | 版本**需核对** | 测试场景没有 VRC 场景描述符，所以 ClientSim 不会启动（`console_full.txt:85-88`） |
| 机器 | Windows（版本**需核对**），i9-13980HX，RTX 4060 Laptop（D3D11） | Python、git 的版本**需核对** |
| 头显 | **需核对**（型号、串流方式） | 设计参考：Index 100% / Quest 2 Link 1.0×，约 9 MP @ 90 Hz（圣经 §1.9） |
| 时间 | HANDOFF_LOG 用北京时间，git 用 UTC | 例：`480e711` 是 10-07 18:19 UTC，等于北京 10-08 02:19 |

**工程结构**
- 仓库里每个文件夹拷到 `Assets/Lanbai/<文件夹名>/`，比如 `Common/` → `Assets/Lanbai/Common/`。shader 的 include 写的是工程根路径（`CONTROL_总控.md:72`）。
- 名字以 `~` 结尾的文件夹（`Docs~`、`Tools~`）Unity 不导入，不用管。`Gate/Source`、`Gate/Renders` 不拷（HANDOFF_LOG「门的总驱动 LanbaiGateDriver」那一条）。
- **仓库里没有任何 `.meta`。** 重新拷要原地覆盖，**不要先删文件夹再拷**：GUID 会变，引用会断。
- 要保留本地生成的东西：各包的 `Generated/`（已 gitignore）、`Assets/Lanbai/UdonPrograms/*.asset`。

**场景和本地脚本（只在 `dream` 里，不在仓库里）**
- 测试场景 `Assets/Lanbai/Tests/GateTest.unity`：只有一台 `ReferenceCamera`，没有 VRC 场景描述符，没加进 Build Settings。门、门的云、门内都在这里搭。
- 正式世界的场景叫什么，**需核对**。仓库里只在 `LB_GateTest.cs:42` 有一个没用到的常量 `Assets/Lanbai/Scenes/Lanbai.unity`。
- 时间轴 `LB_Journey`（UdonSharp）挂在世界根的 `Systems/Journey` 上。仓库里的副本在 `FromLocal/code/timeline_v1/`（09-30 的版本，只作参考）。
- 门测试脚本 `Lanbai.Tests.LB_GateTest`（Build / Apply / Shoot / Perf / Verify / StatsBegin，副本在 `FromLocal/gate_test/code/`）**没有菜单**。以前是远程小助手 `LB_Remote` 用反射调的；`LB_Remote` 现在还在不在、能不能用，**需核对**。它的截图写进 8 位目标，HDR 在调色前就被截断了：**旧截图不能当数据用**。
- 仓库里各包的菜单都在 `蓝白/` 下面：Build、Gate、Gate Clouds、Grades、Sky、Sea、Fonts、Director、Clouds v2。每个包的 README 写了自己的那几个。

**必须满足的项目设置**（出处：圣经 §1.6；`CONTROL_总控.md` §3、§6）
- Linear 色彩空间。灯在 Inspector 里填的值就是线性照度 E（VRChat SDK 强制 `lightsUseLinearIntensity`）。
- 补光一律 Render Mode = Not Important。
- 雾只用 Exponential：Shader Stripping 里 Fog Modes 选 Custom，只勾 Exponential。
- **Vertex Compression：Color 和 TexCoord0–3 都不压缩。** 各包的要求合起来就是这样（D-40b #3）。10-08 的掩码是 4054，没有改过。这一项是改 ProjectSettings，要先备份并经小楠确认（§F）。
- 截图必须先渲进 ARGBHalf，再过 PPv2，最后转 8 位（`CONTROL_总控.md` §6 #10）。

**导入顺序和“以谁为准”**
- 导入顺序：`Engineering/README_集成.md` §6（Common → Grading → Director），然后按 §9 一幕一幕来。
- 每一包的具体步骤看 `HANDOFF_LOG.md` 里对应的那一条。**HANDOFF_LOG 最新的在最上面，新条压过旧条。**
- 接管开关以 `README_集成.md` §3（Director v1.1）为准，各包 README 里旧的“手填接管窗口”作废（D-40b #5）。

---

## B. 当前真实进度（三层验收，D-40a #4）

快照时间 2026-10-24 16:30 UTC。**这张表由总导演维护**：`main` 有新合并、`FromLocal/` 有新结果时更新。PLAN 的进度表也以这里的三层状态为准。

“Unity 桌面”“VR 头显”两栏，**只有 `FromLocal/` 里有对应版本的证据才算**。本地最后一次回报是 `480e711`（10-08 北京），之后合进 main 的东西都没进过 Unity。整个仓库里**没有任何一条头显实测**。

| 内容 | 云端制作 | 进 main | Blender 离线（总导演终审） | Unity 桌面 | VR 头显 | 现在能不能导入 |
|---|---|---|---|---|---|---|
| 门（Gate / Tear / Tentacles）+ 门的云 GateClouds v1.5 + 驱动 v1.2 + 第 10 轮第 1 批 | 完成（剩 4 项等本地截图） | ✅ | 通过 | **只测过旧版本**（10-08，`29fa6f2`：没有云，没有驱动）。当前版本：未测 | 未测 | **可以，第一个测** |
| `Common/`（include 和全局量） | 完成 | ✅ | — | 未测 | — | 门测试前必须拷 |
| 调色 Grading | 完成 | ✅ | — | 10-08 编译过、建过 21 个 profile（和现在是同一份文件）；测试卡、Bloom 探针一直没交回 | 未测 | 已在工程里（**需核对**） |
| 门内（4c、5）+ 遮罩 Overlay | 完成 | ✅ | 通过 | 未测 | 未测（D-19 “布”要在头显里判） | 门测试之后 |
| 天空 Sky | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后，导入后重跑 Gate/Build Driver |
| 海（Sea、7a、7c） | 完成 | ✅ | 通过 | 未测 | 未测 | 门测试之后 |
| 第 6 幕 晨 | 完成 | ✅（`c468254`） | 通过 | 未测 | 未测 | 门测试之后；先要有 Common、GateClouds、Sky、Sea、Overlay、Clouds_v2 |
| 第 9 幕 星海 | 完成 | ✅ | 通过 | 未测 | 未测 | 顺序：门内 → 天空 → 7a → 第 9 幕 |
| 诗与字体 v4.1、Director v1.1、雨 | 完成 | ✅ | 通过 | 未测（工程里的雨是旧版本） | 未测 | 门测试之后 |
| 车（PAZ-672M，`Bus/` + `Cabin/`） | 制作中（D-36，座椅第 4 轮） | ❌ | 没过 | 未测 | 未测 | **BLOCKED**：等座椅 + 侧窗 + 立柱的切片 |
| 宫殿（7b） | 制作中（美术第 5 轮没过） | ❌ | 没过 | 未测 | 未测 | BLOCKED |
| 第 8 幕 暮 | 制作中 | ❌ | — | 未测 | 未测 | BLOCKED |
| 镜与白（第 9 幕的镜 + 第 10 幕） | 终审中 | ❌ | 进行中 | 未测 | 未测 | BLOCKED |
| 灯与假醒（第 11 幕） | 暂停 | ❌ | — | — | — | BLOCKED |
| 站牌套件 | 没开始（D-40a #1：车的切片和门测试之后才开工） | — | — | — | — | — |
| 第 1、2、12 幕的组装 | 只有 09-30 的旧场景截图 | — | — | 旧版本 | 未测 | 等车、灯、站牌 |
| 测试工具 `Engineering/UnityTest/` | 总工程师在做 | ❌ | — | 未测 | — | 到 main 以后，HANDOFF_LOG 会写一条 |

---

## C. 第一次接管：安全、可重复的步骤

**第一次只做第 1–4 步，然后回报。** 小楠说可以了，再做第 5–7 步。每一步都可以重做；中途出问题就停下，照实写进报告，不要自己修工程。

**第 1 步：只读检查（不写任何文件，不开 Unity 也行）**
1. **谁在用。** 有没有 Unity 进程开着 `dream`，有没有别的 AI 会话或脚本在跑。有，就停，问小楠。
2. **版本。** 读 `dream\ProjectSettings\ProjectVersion.txt`、`Packages\manifest.json`、`Packages\vpm-manifest.json`（SDK、UdonSharp、PPv2、TMP、ClientSim 的版本）。
3. **项目设置。** 读 `ProjectSettings\ProjectSettings.asset`：色彩空间、Vertex Compression 掩码。读 `GraphicsSettings.asset`：雾的 stripping。读 Quality 的当前档。
4. **目录。** `Assets\Lanbai\` 的目录树，每个子文件夹最近的修改时间；有哪些场景；`Tests\Editor\LB_GateTest*.cs` 和 `LB_Remote` 在不在。
5. **调色。** 有没有两套调色并存：旧的 `Assets\Lanbai\Grades\` + layer 4 “Water”，套件的 `Assets\Lanbai\Grading\` + layer 22 “PostProcessing”。只记录，不删。
6. **备份。** `dream\Backups\` 里有什么（已知有 `蓝白_20260928_1200_整轮跑通.unitypackage`）。
7. **仓库 clone。** `git status`、`git log -1`，有没有 `.git\index.lock`（10-08 卡过一次）、stash、没跟踪的文件。
8. **环境。** Windows 版本、VCC 版本、Unity Hub 和 Editor 的安装路径、`Editor.log` 在哪、Python 和 git 的版本、显卡驱动、头显型号和串流方式（不知道就问小楠）。

**第 2 步：记录和备份**
1. 把第 1 步的结果写成 `FromLocal/takeover/<YYYYMMDD>/接管核对.md`（人读）和 `inventory.json`（机器读）。“需核对”的每一项都要有答案，或者写“查不到”。
2. **备份整个工程。** 关掉 Unity，把 `dream` 打成 zip，排除 `Library`、`Temp`、`Logs`、`obj`、`Build`，存到 `E:\IDMdownload\VRCC\Backups\dream_<YYYYMMDD-HHMM>.zip`。报告里写大小和 SHA256。
   - `ExportPackage` 不包括 `ProjectSettings`、`Packages`，不能代替整包备份。
3. **建议，要小楠同意：在 `dream` 里建一个只在本地用的 git 仓库。** 用 Unity 标准的 `.gitignore`，永远不推到远端。好处是以后每次改动都能 diff。10-08 那次，UdonSharp 重编改写了程序资产和 ProjectSettings，因为没有 git，没法知道具体改了什么。

**第 3 步：环境和依赖核对**
- 和 §A 的表逐项对。不一样的地方写进报告。
- **不要升级或降级 Unity、VCC、SDK、任何包**。要换，先问小楠。

**第 4 步：选第一个测试场景**
- 第一个测**门**：`GateTest.unity`，test-id 是 `gate_clouds_test`。理由见 §D。
- 写一页计划：要拷哪些文件夹，要改哪几个文件，预计要动 ProjectSettings 的哪几项。交给小楠确认。
- 到这里，第一次接管结束。把 `FromLocal/takeover/...` 推上去（§E），告诉小楠。

**第 5 步：导入和编译**（小楠说可以以后）
1. `git pull` main。这一次会很大：从 `29fa6f2` 到现在差将近 500 个提交，pack 约 1.1 GiB。pull 失败就停，不要手修 HEAD。
2. 拷文件。总工程师的同步脚本到了以后用它：它先 dry-run，覆盖前备份，本地改过的文件不覆盖。在那之前手工拷，只拷那一条 HANDOFF_LOG 点名的文件夹，原地覆盖。
3. 编译。Console 全部原样保存，包括 UdonSharp 的输出。编不过的话，只做能编过的最小修改，并把 diff 推回来（HANDOFF_LOG「门的云 GateClouds v1.5」那一条的“现在先别做”）。
   - 不要在 build 模式下调 UdonSharp 编译：10-08 这样做出了 5 171 条假 CS0518，还改写了程序资产（`README_说明.md:144-149`）。
   - 不要加全局的 AssetPostprocessor：会让全工程的模型都重新导入（`README_说明.md:120`）。

**第 6 步：截图和性能测试**
- 优先用测试工具（`Engineering/UnityTest/`，到 main 以后 HANDOFF_LOG 会写一条）。
- 工具没到之前，门测试照 HANDOFF_LOG 的四条做，**从旧到新**：「门的云 GateClouds v1.5」→「门的总驱动 LanbaiGateDriver」→「门的驱动更新到 v1.2」→「门的云第 10 轮第 1 批」（HANDOFF_LOG 里的条目标题）。新条压过旧条：
  - `_Stars` 用 0.055，不用 0；
  - 有了驱动以后，允许进 Play 测 Udon；
  - 头显检查照「门的总驱动 LanbaiGateDriver」那一条最后的头显部分做。
- `LB_GateTest` 没有菜单。如果 `LB_Remote` 不能用，可以在 `Assets\Lanbai\Tests\Editor\` 下面加一个只包装这几个静态方法的菜单文件。这是测试用的文件，要写进报告并推回副本。
- 性能：编辑模式的数只是估算。预算按 Play 模式加真头显算（`Engineering/ledgers/README_账本.md` §三）。
- 动态检查（D-40a #5）：头部微动序列、闪烁、闭左眼和闭右眼各看一次。
- 头显检查只能由人戴上头显做。你能操作头显的话照做；不能，就标“这一层测不了”，交给小楠实测。

**第 7 步：回传**：见 §E。

---

## D. 第一批测试（小楠定的优先级；可以按“东西到没到”调整，但依赖缺了只能记 BLOCKED）

| 优先 | test-id | 测什么 | 现在 | 依赖 | 回传到 |
|---|---|---|---|---|---|
| 1 | `bus_slice` | PAZ-672M 车厢切片：材质；贴图压缩 Crunch vs BC7（0.5 m）；mip；光照图接缝；铬件和倒角的高光闪不闪；法线强度（D-40 #1） | **BLOCKED**：切片还没交 | 车交切片 + HANDOFF_LOG 一条 | `FromLocal/bus_slice/` |
| 2 | `gate_clouds_test` | 触手之门：机位 key / U7 / U8fwd / U8side / rear；三种状态的性能；Udon 毫秒数；头显检查 | **能测**（要先拷 `Common/`） | HANDOFF_LOG 门的四条（§C 第 6 步） | `FromLocal/gate_clouds_test/` |
| 3 | `act06_test` | 第 6 幕晨，三个视向：正前 / 车门 / 天窗（`Act06_Dawn/README_Act06.md` §0），车门方向的 VR APL | 门测试之后 | Common、GateClouds、Sky、Sea、Overlay、Clouds_v2 | `FromLocal/act06_test/` |
| 4 | `act01_spawn` | 第 1 幕出生点：构图、雨夜的氛围、第一印象 | **BLOCKED** | 车、灯与杆、站牌套件 | `FromLocal/act01_test/` |
| 5 | `palace_hotspot` | 宫殿：画面和性能热点（≤ 6.4 ms） | **BLOCKED** | 宫殿过审、合并 | `FromLocal/palace_test/` |

**现在实际只能做第 2 项。** 所以第一个测门，这不改小楠定的优先级：车的切片一到，就排到最前面。

---

## E. 回传协议

**路径**
- 每跑一次一个新文件夹：`FromLocal/<test-id>/<YYYYMMDD-HHMMSS>/`，不覆盖旧的。
- test-id 沿用已经约定的名字：`gate_clouds_test`、`act06_test`、`04c_test`、`act07a_test`、`sea_test`。新的照 §D。
- 每个 test-id 下面有一份 `问题.md`，跨多次运行一直用同一份（见下面）。

**每次运行的文件夹里放什么**（格式照 `FromLocal/gate_test/README_说明.md`，那是最好的样板）

| 文件 | 内容 |
|---|---|
| `manifest.json` | test-id；拷进 Unity 的仓库 commit（clone 的 `git rev-parse HEAD`）；Unity、SDK、各包的版本；机器；测试工具的版本；每一步的状态；三层状态 `{blender_offline, unity_desktop, vr_headset}`，取值“未测 / 通过 / 不通过 / 这一层测不了”。`vr_headset` 只能由真戴过头显的人填 |
| `README_说明.md` | 做了什么，自己定了什么（JSON 和 README 里没给、你推定的值），哪些没做，Console 分类，对上的和没对上的 |
| `shots/` | 截图，命名 `<机位>_unity_t<秒>.png`（HDR 截法） |
| `seq/` | 动态序列（单个文件 < 95 MB；太大就留在本地，报告里写在哪） |
| `console_full.txt`、`console_errors_warnings.txt` | 原样，包括 UdonSharp |
| `perf.*` | 帧时间等。标清楚是“编辑模式估算”还是“Play + 头显实测” |
| `diffs/` | 你为了编过、测过改的每一个文件的 diff |

**问题分级**（写进 `问题.md`）
- **S0 阻断**：编不过、导入失败、崩溃、违反 VR 舒适铁律（圣经 §1.8）、闪光超限。
- **S1 严重**：画面明显错（缺东西、颜色或亮度错、穿模、闪烁）；超性能预算。
- **S2 一般**：和参考图有可见差异，但不影响读画面。
- **S3 建议**。

`问题.md` 一行一个问题，列：编号（`<test-id>-NN`）、分级、层（Unity 桌面 / VR 头显）、现象、证据（文件路径）、状态。
- 状态的取值：开着 / 云端已修 `<commit>` / 本地复测通过 `<运行文件夹>` / 不修（写理由）。
- 问题只由总导演关；美术问题，小楠也可以关。头显层的问题，必须在头显里复测过才能关。

**Git**（沿用以前本地的做法：直接提交到 main，只碰 `FromLocal/`）
```
git pull --rebase origin main
git add FromLocal/<test-id>/            # 只加这一个路径，加完用 git status 确认没有别的东西
git commit -m "FromLocal/<test-id>: <一句英文>"     # 作者名用 "Lanbai-local (阿白)"
git push origin main
```
push 失败，请小楠转告。**不要碰 `FromLocal/` 以外的任何文件。** 云端不改 `FromLocal/`（D-15），所以这条路不会和云端冲突。

**通知和接收**
- 推完以后，用一句话告诉小楠路径。小楠转给总导演。总导演每 2 小时 40 分钟巡检一次，也会看 `FromLocal/`。
- 总导演读结果、定分级，再按 `PLAN_总导演.md` 第三节的交付图分给负责的会话：
  - 编译、性能、工具、Udon → 总工程师；
  - 画面 → 做这一幕的包；
  - 诗 → 总工程师（字体）。
- **复测**：云端修好并合进 main → HANDOFF_LOG 写一条“复测 `<test-id>`：`<问题编号>`，拷什么” → 你用同一个 test-id 再跑一次（新文件夹） → 更新 `问题.md` 的状态。

---

## F. 协作边界（小楠 10-24 定）

- **只有阿白写本地 Unity 工程**，避免多个 AI 同时写。云端照常在自己的分支上做，不等本地。
- **动手前先核实**当前的文件、进程、版本、未保存和未提交的改动，不覆盖已有的成果。不认识的改动，先问。
- **高风险操作要先备份，并经小楠确认。** 包括：
  - 删除任何东西（要删先挪进 `_to_delete/`）；
  - 批量替换；
  - 改 `ProjectSettings`、`Packages`、SDK、VCC；
  - 改正式世界的场景；
  - 改 `LB_Journey`；
  - 任何架构上的改动。
  - 技术架构归总工程师。HANDOFF_LOG 里 09-28 那几条说“技术怎么实现由你决定”，那是写给前任的，**作废**。
- **不手调数值。** 材质、JSON、LOD 都照包里的来。超预算、不好看，照实报，不要自己砍（HANDOFF_LOG「门的云 GateClouds v1.5」那一条的“要量的”和“现在先别做”）。
- **JSON 和 README 里没给的值：** 只在测试场景里自己推定，并写进报告的“自己定了什么”。正式场景里不推定，先问。
- **没有 HANDOFF_LOG 的明文，不把门接进正式世界，不点 `蓝白/Director/2 Wire Scene`**（HANDOFF_LOG「门的总驱动 LanbaiGateDriver」那一条的“别做”）。
- **各会话不能假定别人知道自己的上下文**：以仓库里的交接资料和实际查到的为准。
- **没完成的 VR 测试，不许标成通过。**
- VRChat 登录、账号操作、上传世界：只由小楠做。

---

## G. 接管前要知道的坑和已经裁掉的矛盾

- **坑**：`CONTROL_总控.md` §6 那 13 条（10-08 门测试踩的），加上第 5 步里那两条（UdonSharp 的 build 模式、全局 AssetPostprocessor）。另外两条：
  - 编辑模式下的 `Camera.Render()`，ProfilerRecorder 和 UnityStats 看不到；
  - 10-08 那次 VM 里 git 删不了锁文件，HEAD 卡了一半，是手工修的。
- **已经裁定的矛盾**（D-40b）：
  - 主座位眼位用 (0.55, 1.70, 2.05)，`LB_Journey.heroEye` 的旧值作废；
  - 像素密度：闪烁和锯齿按渲染目标约 20 px/° 查，“看不看得见”按面板约 14 px/° 判；
  - Vertex Compression 是 Color 和 TexCoord0–3 都不压缩；
  - 性能按 Play + 头显定；
  - 接管开关以 `README_集成.md` §3 为准；
  - 天空在门测试之后再导入（以 HANDOFF_LOG「天空套件合进 main」那一条为准，不按 `README_集成.md` §9.1）。

---

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
2. `HANDOFF_LOG.md`：云端写给本地的每一包怎么导入，最新的在上面。
3. `Engineering/README_集成.md`：导入顺序、写的人时刻表、每一幕的接法。
4. `Art/总导演裁决.md`：所有裁决，压过圣经。
5. `Art/ART_BIBLE.md` 的几节：§1.6 光照和材质规则、§1.8 VR 舒适铁律、§1.9 性能预算、§9 要截图的清单。
6. `Engineering/ledgers/README_账本.md`：性能账本和本地实测协议（§三）。
7. `CONTROL_总控.md`：协作约定，§6 是 Unity 的坑。
8. 各包的 README（`<包>/README_*.md`）：自己的菜单、要截的图、回传要求。
9. `FromLocal/gate_test/README_说明.md`：回报写法的样板。
10. `Lanbai_Handoff.md`：**历史文件**，写给以前的本地 Claude。路径、备份的信息还有用；里面的技能、ListAgents、SendMessage、/remote-control 这些只有 Claude 能用，**不适用**。
11. `Engineering/UnityTest/README`：测试工具，**还在做**，到了会在 HANDOFF_LOG 写一条。
