# gate_clouds_test：轻量同步成功，云层构建被 Udon 资产初始化阻断

运行：20261024-154108，America/New_York。来源 main：`f40f62c8370d34b53c1ce8a6815852b400d4896d`。报告人：Lanbai-local (阿白)。

## 已完成与停止点

用户已批准轻量同步以及原首测计划。独立浅克隆只取239个导入文件与10份必要文档，原仓库保留；Git blob 与 SHA256 全部吻合。完整备份已经在先前阶段完成并验证，本次复用；未重新备份相同工程。

Unity 2022.3.22f1 加载和 C# 编译通过。UdonSharp 启动编译13个脚本成功，新增云程序后14个脚本编译也成功。门 Build 成功：28条单独触手、36条群臂、64个LODGroup。**云 Build 两次在 CopyProxyToUdon 处抛出 outdated script version；当前 Unity 桌面层不通过。编译成功不能替代序列化和场景构建成功。**

首次失败后等待 Unity 自动初始化/编译，再重试一次，仍复现。没有修改云端构建器或 SDK 来绕过校验。依据 HANDOFF_CHATGPT.md §C“中途出问题就停下，照实写进报告，不要自己修工程”，停止后续构建与验收。

启动参数中的 openfile 没有让编辑器实际切到 GateTest，初始 heartbeat 显示正式场景未脏；通过原 LB_Remote 的 open 请求安全切换后才运行 Build。正式场景文件未保存、未改写。

## 复现与工程师线索

1. 本项目 Worlds/base 3.10.5，依赖未改。按交接同步，再执行 LB_GateTest.Build("155.1")。
2. LanbaiGateCloudsBuilder.BuildMenu 首次创建 Assets/Lanbai/UdonPrograms/LanbaiGateClouds.asset，编译完成后 CopyProxyToUdon 抛出 InvalidOperationException。
3. 等编辑器更新结束，再执行同一 Build，日志再次出现 created 同一路径，然后再次抛出相同错误。

静态查到的确定差异：构建器 CallStatic 在第379行只搜索 Public|Static；第432行传入 MonoScript 调 GetUdonSharpProgramAsset。现有SDK的 MonoScript 重载在 UdonSharpEditorUtility.cs:126 是 private，public 重载在:147 接受 Type。当前反射调用找不到匹配的公开方法，返回null，使构建器反复进入新建资产分支。新资产磁盘快照 scriptVersion=0 / compiledVersion=0。

第二个需要工程师处理的生命周期问题：新建程序资产后立即 CompileSync 并不保证 scriptVersion 已到 CurrentVersion；现有SDK在之后的 EditorUpdate 升级新程序资产的序列化元数据。第一次错误后日志确有该自动流程。应由工程师使用匹配的公开查询接口，复用已有资产，并确保首次新建资产的版本初始化完成后再 CopyProxyToUdon。**这只是修复线索，未应用、未验证修复；不是升级SDK建议。**

完整异常在 remote/results/gate_20261024_cloudbuild*.json 与 console_full.txt。Unity Console 的红色计数可能仍为0，因为原远程助手捕获异常写入自己的请求结果；不能因此判成功。

## 本轮实际改动

- 按白名单同步239文件，233新增、6覆盖；来源全部核验。保留原meta；Unity为新资源生成了meta。
- LB_GateTest_Run.cs：四处旧光层保持关闭；Apply接入云；Shoot只增加实际HDR目标格式到报告，截图渲染链路未重写。
- LB_GateTest_Build.cs：每次Build按交接将Fill设为Not Important；远潮HazeNear/HazeFar/BandEl从云JSON读取；星强度读取Gate JSON的0.055。Moon和正式世界未改。
- ProjectSettings/ProjectSettings.asset：唯一差异 VertexChannelCompressionMask 4054→3846。先从安装的Unity程序集核实位定义，取消Color/UV0–3压缩；不改其他设置。
- Build自动改写测试场景和3个测试材质；云Build生成网格、材质、meta与Udon程序。现有文件共16个内容变化（含上述9个直接改写、测试场景、3材质、远程日志/心跳及EditorUserSettings），新增357个文件，逐项见 project_changes_and_protection.json。此清单不含排除的缓存，也不代表所有新增文件均为新资产。
- 备份范围7233个旧文件逐一复核，无缺失、无读取错误。所有正式场景、LB_Journey、Packages以及除批准掩码外的ProjectSettings保持原样；242项直接写入与计划后的哈希一致。UserSettings仅记录哈希，未发布其中的本机设置内容。

diffs/包含每个直接覆盖及测试场景/材质的差异；code/包含修改后的两个测试脚本。未新增测试架构或子代理。

## Console 分类

- S0：云驱动资产序列化版本未就绪，2次可复现。
- 已知：LB_Builder_Road.cs:450 的 CS0162（既有不可达代码警告），不是本轮新增编译失败。
- 预期时序：门Build内的Apply早于云Build，产生 GateClouds not built 提示。
- S2待工程师评估：重建时网格对象名 GateClouds_Card_Congestus 与文件名 GateClouds_Card_Congestus_crop45 不一致。
- Editor启动另有许可客户端验证/令牌缓存错误与更新查询404；随后成功解析许可并加载工程。未操作登录、未改许可、不能把这些启动信息当作本次云构建异常的原因。原始Editor日志保存在E盘工作目录，本次发布的 Console 原文包含Udon输出及完整远程助手异常；compiler_editor_excerpt.txt补充首次C#编译结果。旧compile.log只有10-08历史记录，未冒充本轮编译证据。

## 未完成项目与现场

云Build失败发生在其“关闭旧FootSkyline/旧Shaft等renderer”的收尾之前，也未产生 built:38 cards/10 towers/6 beams 成功行。后续Apply、Build Driver + Test Clock未执行，不能确认64实例驱动绑定或云参数验收。

没有生成5机位HDR验收截图、metrics、三态性能、GPU各pass或Udon毫秒数，也未进入Play/ClientSim。diagnostics/unity_partial_scene_not_acceptance.png仅用于说明编辑器现场，**不是**完整构建、指定机位、HDR链路或画质验收证据。不会据此评价或降低画质。

Quest 3 + VD用户报告可用；实际佩戴、左右眼、微动、10秒银边、后窗消失与舒适检查仍为未测。既有测试场景缺VRCSceneDescriptor与云端UnityTest工具尚未交付的入口问题仍开着；本轮没有擅自添加Descriptor或BuildSettings。

Unity保持打开，活动场景GateTest，非Play、非编译、无待执行请求；**部分云构建仍在内存，sceneDirty=true，没有将失败后的部分云场景再保存覆盖。** 磁盘上的GateTest已由成功的门Build保存，不是完整云首测场景。不得把当前工程状态当成可发布世界。

## 磁盘、备份与回退

C/E空间在主要写入前后复测，本轮导入/构建期间没有异常持续下降；最后工程复核时C约3.16GiB、E约102.95GiB。没有重复清理，TEMP/TMP、备份、Git与Unity主日志放在E。Unity自己的GI缓存仍会在C产生少量数据；后续恢复前必须再测空间。

完整备份：E:/IDMdownload/VRCC/Backups/dream_20261024-134728.zip，522183967字节，SHA256 c960d93308580f4066d7db331ea91080b5f8ee1c118d752ccac094d878add7f8。7233文件逐项CRC/SHA256及关键文件校验通过；排除Library/Temp/Logs/obj/Build，旧恢复场景独立保全。没有做恢复演练或自动回退。

若需回退：先保全当前未保存测试场景现场并关闭Unity，复测E容量，将备份解到新的E盘核验目录；按本轮差异清单恢复原测试场景、3个材质、2个测试脚本、6个被覆盖来源和ProjectSettings的原文件/meta。新增文件须按清单隔离保全而非删除，检查以后是否有未知改动后再处理。生成Udon资产及其SerializedUdonPrograms须成套核对，不只回退脚本。无恢复授权不自动执行。

恢复入口：总工程师将构建器兼容修复合入main并在HANDOFF_LOG写复测条目，或用户明确批准具体的本地最小修复；核验差异、磁盘与现场后，从门→云→Apply→Driver顺序重跑。已完成且未受影响的备份与环境审计复用。
