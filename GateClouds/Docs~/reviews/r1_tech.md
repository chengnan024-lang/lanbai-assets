# 第 1 轮 · 技术评审（独立 agent）· 结论：不通过

BLOCKER 1：U# 驱动没有程序资产 / 可能没有底层 UdonBehaviour → Build 建程序资产、RunBehaviourSetup / UdonSharpUndo、CopyProxyToUdon、缺失时报错（已改）。
BLOCKER 2：云海 SV_Depth 关 early-Z、aniso 16、120 步 → 保守深度 + 代理面、aniso 4、自适应步长（已改）。
MAJOR 3：云卡 right 向量其实是左（已改，预览同步）。MAJOR 4：平面光池会被云头切碎（光池并进云海，关掉 Tear_CloudGlow / Lane）。MAJOR 5：云海不进深度图、软淡化用浮点开关（加 ShadowCaster pass、SOFTPARTICLES_ON）。MAJOR 6：IGN 锁屏、光束用逐眼相机（世界方向哈希、两眼中点）。MAJOR 7：四边形 vs 远裁面（README 写明 far ≥ 20 km）。
MINOR 8–14：默认平台格式、驱动懒初始化、时间窗来自布局、_Udon_InsidePortal 登记、include 路径统一、楔队列 2991、Shader.Find 空检查（都已改）。
