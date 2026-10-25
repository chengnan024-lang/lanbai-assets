# gate_clouds_test 本地接续回报

本轮已实际接管并完成新的完整工程源文件备份、最新 main 同步、最小兼容修复和 C# 编译。**尚未完成云 Build、驱动挂接及截图**：Unity 普通启动与无图形批处理均崩溃，已停止继续启动。没有 Play、性能或头显验收结论。

## 当前工程现场

- 历史回报停在 dirty 场景；本轮接管发现 Unity 已被先行重启，当前场景 dirty=false。保存的 GateTest SHA256 仍为 `59e907722cc5c348673effb0ebe8601c5eced806a5d6161ed838c359d1999e2f`。旧内存中的失败云 Build 不能假称已恢复。本轮未关闭未保存场景；先保留 scene/meta/heartbeat 后正常退出已保存的 Unity。
- 当前编辑器已退出，无新待执行 remote 请求。已排队但未执行的 `gate_continue_1638_prepare` 被移到 E 盘 preserved，避免下次启动意外写入。历史请求和结果保留。
- 本轮比对完整备份：正式场景、全部 ProjectSettings/Packages、LB_Journey 均未变化；没有文件缺失。测试场景尚未被本轮保存覆盖。
- 原 clone 的中断 pack 保留；独立安全检出 `pull --ff-only origin main` 成功，HEAD=`98b6dbd497f6887e2986b9affdbf1a6559e5f321`。相关资产目录与已导入的 f40f62c 相同，复用已核验的 239 文件，未再次全量导入。

## 备份

`E:\IDMdownload\VRCC\Backups\dream_20261024-163541.zip`

- 571,820,591 字节，7590 文件、3120 meta。
- SHA256：`f2fbfbb11d23995fcf61e7b0682765f02e0b82a3288ccde4ee34c48f91128fda`。
- 逐项读取并核对 CRC、SHA256，关键文件齐全，归档期间源文件元数据未变。未进行恢复演练。
- 按交接排除可重建的根目录 Library、Temp、Logs、obj、Build；包含 Assets、Packages、ProjectSettings、UserSettings 等完整源工程内容。
- 历史 13:47 备份仍保留，不混称当前快照。

## 具体修改与回退清单

1. `Assets/Lanbai/GateClouds/Editor/LanbaiGateCloudsBuilder.cs`：程序资产查询传 `Type`，匹配 SDK 3.10.5 的公开重载。原代码传 MonoScript，而对应重载是 private，公开反射命不中会重复创建已有程序资产。这是针对历史失败的最小修复，**只通过 C#，尚未实际复测云 Build**。
2. 新增测试工具 `Assets/Lanbai/Tests/Editor/LB_GateContinuation.cs` 与 meta：分阶段创建/等待三个程序资产由已安装 SDK 正常初始化，验证版本与绑定后才保存 GateTest；有空间检查与 180 秒阶段超时。未手动伪造版本号，未调用 Force Upgrade，未打包 Player。
3. 新增 `Assets/Lanbai/UdonPrograms/LanbaiGateDriver.asset`、`LanbaiGateTestClock.asset` 及各自 meta。崩溃时仍为 scriptVersion=0/compiledVersion=0；不要直接跳到 Build。已有 clouds 程序仍为 2/2。
4. `ProjectSettings` 修改清单：**零**。既有批准的 Vertex Compression 3846 保持。SDK、依赖、正式场景、LB_Journey 修改清单：**零**。
5. 回退：确认 Editor 已关闭，先保留本轮补丁和新增资产；从 16:35 完整备份只取原 CloudBuilder 文件恢复。新增 helper/driver/clock 资产连同 meta 仅在明确决定回退后移到 E 盘 preserved，不删除。不要整包覆盖未知新改动。场景无需回退，字节未变。

所有差异在 `diffs/`。新工具中固定 38 卡片、10 塔层、64 门实例来自本次布局，用于检测缺项；如上游布局改变应同步验证计数。没有自行手调材质、JSON 或 LOD。

## 实测结果与问题

- C#：两次启动均编译成功。已知 `LB_Builder_Road.cs:450 CS0162` 警告仍在。
- 普通启动：D3D11 纹理分配 `0x8007000e`，resource view `0x80070057`，随后场景视图绘制 SIGSEGV；准备请求未执行。
- 一次有界无图形启动：成功载入 GateTest、复用 clouds 并创建 driver/clock 程序资产；随后内存分配/GC SIGSEGV，没有进入云 Build。运行期间启动本机命令也报 `0x800705AF`（分页文件太小）。无图形模式的环境探针警告不当成视觉结果。
- 构建前后 C 盘约 237→234 MB，E 约 109.97 GB；未发生本步骤明显的持续写入增长，但整机可提交内存仍不足。最新 VRChat private bytes 约14.78 GB，未终止。
- 屏幕截取受遮挡且崩溃前构建未完成，本轮不提供伪验收截图。五机位、动态序列、Play、GPU/Udon 毫秒和头显均未测。

## 连续推进的准确入口

资源阻断解除后，先复测 C/E 与内存、确认无第二 Editor/写入者，再沿用当前备份和补丁继续。允许已安装 SDK 完成 driver/clock 初始化与正常 editor Udon 编译；确认三个程序资产都 2/2 后，执行 Cloud Build → Apply(155.1) → Build Clock → 绑定验证 → 仅保存 GateTest。不要从头重复239文件导入。

然后按交接拍 key、U7、U8fwd、U8side、rear，检查真实 HDR 目标、亮度和视觉内容；rear 拍摄临时 BackBand=1.25，结束恢复0.55。继续把缺失、错误效果与参考差异逐项登记，未做的动态/性能/头显项保持未测。不得接入正式世界。

已为当前对话设置35分钟、95分钟各一次进度/目的检查，以及每160分钟续作；续作遇未解除的资源阻断保持安静，不重复启动、不重启机器。
