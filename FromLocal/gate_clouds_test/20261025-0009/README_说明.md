# 门测试本地部署与正式修复复测 · 2026-10-25

本地 GateTest 已部署并保存，Unity 的隐藏窗口问题已修复，最后留在前台循环播放。正式修复来源 main `f703a951`，共用 Udon 工具、门与云构建代码、UnityTest 已按文件哈希核对。64 个门实例、38 张云卡、10 层云塔、6 道光束正常；三份 Udon 程序资产均为 2/2，正式场景、设置、依赖和既有 .meta 保持。

## 工具结果与实际界限

[完整工具报告](../20261025-001346/summary.md)：UnityTest 1.0.0 完成，退出码 0，16 项检查、0 项 fail，未声明写入 0。另有 [预检](../20261025-001331/summary.md)。这是工具检查结果，整体 Unity 验收仍待总导演看图；Quest 3 + Virtual Desktop 未实测。

工具报告结束后，SDK `UdonSharpEditorUtility.cs:931` 的延迟回调出现一次 `MissingReferenceException`，未被工具报告的 Console 计数收进来，不能据报告的 0 errors 宣称整个过程无异常。完整补充记录在 evidence/console_formal.txt。没有改 SDK、没有改版本号或 Force Upgrade。

工具 post 还无条件新建 VRCWorld，和已有 GateTest_ClientSim 形成两个描述符。保留原始沙盒输出及备份后，只在最终场景移除本轮新建的空 VRCWorld，保留已配置的相机、出生点与测试地板；再将最终场景保存回 GateTest，验证三驱动绑定并进行独立 Play 复测。最终证据见 runtime_samples.json、finalize_tool 与 final_preview 请求。原始沙盒保持作故障证据，后续应使用 GateTest。

## 静态和动态

本目录 shots/ 是正式修复后、完整工具运行前的五机位 HDR 截图；完整工具自己的五图、双眼近似与 286 帧序列在 20261025-001346。均未重着色。HDR 目标实际为 ARGBHalf / R16G16B16A16_SFloat，经 PPv2 后输出 8 位 PNG。key 为 2560×1072，其余 1920×1080，2× 超采样。

rear 按交接临时将相关材质 _BackBand 从 0.55 提到 1.25 拍摄，finally 恢复。没有自行改审美参数。手动五图的测量见 metrics_unity_vs_render.json；使用仓库原始色彩公式，未算连通区域或对象遮罩，不把整帧 APL 当云海单独亮度。

逐图已看：key/U7 主体完整；U8fwd 裂口脚下光区明显更亮；U8side 的近臂占画面较大且高光细；rear 高光较硬、整体偏暗。近景云有明显层纹。工具记录 U8fwd APL 62.91，对照 40.94；rear 20.51，对照 29.43。参考是合成图，比例只作线索，交总导演判断。

工具微动 shimmer 超阈值比例：U7 12.63%、U8fwd 19.645%、云滚动 11.407%；静止对照 0%。这些是编辑器近似警告，不是头显舒适通过。Play 中时钟、云驱动、shader 时间一致，穿门隐藏与循环恢复见 runtime_samples.json。

## 性能与 Console

详见 perf.md 和完整工具 perf.json。编辑器双眼估算 U7 10.99 ms、U8fwd 11.35 ms；关云海 deck 后降至 5.44 / 6.26 ms，提示云海是后续排查重点。估算不能判真实 VR 超预算。Play 的一帧统计为 181 draw/batches、175 SetPass、571251 三角；ProfilerRecorder 中位数为 0，不采信为有效数据。两个驱动各自 Udon 毫秒、真实 GPU/头显帧时间均未测。

既有 C# warning：LB_Builder_Road.cs:450 不可达代码。三个 shader 在 LanbaiGateSky.cginc:53 有 LanbaiBand 可能未初始化警告，没有编译错误。工具捕获期间还有 active RenderTexture 释放警告和重建中短暂的旧引用警告。报告后 SDK 异常单列，不抹去。

## 保全、回退与回传

先正常退出原隐藏 Unity，再完成已逐文件 CRC/SHA256 校验的全备份 dream_20261025-000405.zip（571971007 字节，7658 文件）；随后正常可见启动。不是强杀。源码替换均先演练、核对本地补丁与正式修复；没有复制仓库 .meta、没有清空 Generated、没有全量导入。

audit.json 给出本轮前后哈希，diffs/ 给出已有文本文件的差异，synced_sources.json 给出实际同步清单。local_helpers/ 是本地测试适配器副本，不能再导回 Unity 造成重复类。完整工具另有 220 文件 backup_before，留在本地；公开导出保留其哈希清单。完整原日志留本地，公开文本仅替换本机路径前缀，public_export.json 列出原始/导出哈希；图片不变。

C 盘最初约 2.35 GiB，先执行已有轻量流程；清理聊天释放空间到约 13 GiB 后，新工具真实预检通过才运行完整流程。当前会话未参与清盘。问题关闭由总导演决定，本轮不自行关闭。
