# 测试工具 1.2.2：待本轮版本确认

源版本 main 11c2f44。已审阅差异并完成本地增量备份，尚未替换或运行1.2.2。当前工程仍用已授权1.2.1；Director迁移所需的编译和场景内诊断照常进行。

新版8个文件变更：树样本改为FullPreview/MSAA4、隔离背景并只量叶缘ROI；读回像素强制GPU完成并减去空渲染基线，记录各进程物理显存；小文件WriteGuard按内容哈希；新车侧窗机位与覆盖率检查；增加bus_dropin定义。仅更换项目内的Editor测试代码和测试定义，不升级Unity、SDK或依赖，不上传世界。

拟运行范围：既有gate_clouds_test、tree_sample、flicker_probe、transitions_sweep，以及已交付新车的bus_slice/bus_dropin；都使用测试副本、后台静音，保留原场景。真实头显与多人仍未测。现有完整备份复用，新增工具备份43个文件，共431183字节。

版本确认依据：[HANDOFF_LOG](../../../HANDOFF_LOG.md)北京04:40明确“CONSENT的tool_version要改成1.2.2”“这要重新问小楠”；[工具README](../../../Engineering/UnityTest/README_UnityTest.md)要求版本与范围对应。取得这一次明确确认后更新本地CONSENT并继续，不将入口助手回复视为用户批准。
