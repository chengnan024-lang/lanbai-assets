# 样板树第一次本地技术验收：不通过；透明卡片缺陷已做最小修复

来源 main09164c9，Unity2022.3.22f1/RTX4060 Laptop；工具1.2.1加本地捕获修正，**不是原版工具通过**。现有道路杨树未替换，四棵样树只生成预制体与测试沙盒/Play临时对照。

## 实际发现与修复

1. 原定义拷正式Lanbai后找不到Grades，先失败退出（095406）。改用FullPreview拷贝、去掉误关道路组的可选步骤后，完成4图+225帧微动/静态序列（100058）。
2. 叶簇变成整块不透明卡片。先只把测试RenderTexture改为MSAA4，101751控制图仍复现；然后仅在叶shader加入keepalpha、LightingTreeLeaf明确返回s.Alpha，101954图中的卡片裁切恢复。依据[Unity2022.3表面着色器说明](https://docs.unity3d.com/cn/2022.3/Manual/SL-SurfaceShaders.html)：不透明surface默认把alpha置1。补丁在patches/，需要云端采纳。没有改变美术色值/叶簇造型。
3. 工具原RenderTexture固定MSAA1，不满足A2C测试。新增每相机可选msaa字段，默认仍1，树变体设4；同时避免释放当前active RT的警告。未改ProjectSettings画质。
4. TreeBuilder最后全局SaveAssets缩成只保存本包材质。原第一次报告33个额外mtime写入没有完整的逐文件事前哈希，不能全部免责；后续3个Sea/SeaB/WetGround报警逐字节hash相同，见write_guard_content_check.json。工具仍按mtime判失败，没篡改为pass。

## 仍未通过

|指标|修复后|门槛|
|---|---:|---:|
|hero微动shimmer p99|12.30|≤12|
|hero超阈值比例|5.275%|≤2%|
|right超阈值比例|21.129%|≤2%|
|hero静态超阈值比例|0%|≤2%|

测试新编译错误/异常/Console Error均0，PPv2差分有效。微动是整幅画面且含旧车柱、灯、道路和未隔离占位；主座位被旧车柱遮住，所以这些数字**不是纯叶缘或头显结论**。请总工程师先修夹具ROI/遮挡/背景隔离，再定树叶闪烁；不据此自动改灯包美术。

## 同灯光对照与LOD

supplement中*_fixed是修复后独立Play、同机位/同地面/Environment灯层的杨树、临落树、样板树12图；sample_lod1/2_fixed另8图是**强制LOD诊断**，不是自然距离切换。早先无fixed的跨幕回拖/单采样图不当作最终夜色/抗锯齿比较。D28主座位镜头仍有旧车柱遮挡，不能拿裁掉车柱的图冒充乘客视野。

|树|LOD0三角|LOD1三角|LOD2三角|结构draw槽0/1/2|约0→1 / 1→2米|
|---|---:|---:|---:|---|---|
|A1|8142|1326|4|2/2/1|110.2 /344.2|
|A2|10486|1540|4|2/2/1|103.8 /324.3|
|A3|11996|1750|4|2/2/1|141.2 /441.3|
|B1|5816|1666|4|2/2/1|84.8 /264.9|

距离根据本机lodBias=2、55°、实际LODGroup包围范围计算，是近似，不是FrameDebugger实测draw call。7棵20–40m比较组基本都是LOD0，不能声称right图已自然测到LOD1/2。叶cluster及4张impostor贴图MipMapsPreserveCoverage均true，证据assets.txt。工具perf draw/triangles没有量到，结构统计不能冒充GPU测量。

final/保留修复后全部原帧、热图、指标、Console和测试定义。100058基线仅保留端点样本/热图/指标/静态图，完整239MB原帧留本地；避免再公开一套近重复序列。公开manifest只隐去用户授权私密备注。工具仍读取旧sync记录f703a951，**实际包来源见本报告09164c9**；未伪改原始测试版本记录。

道路树替换、最终审美、头显双眼/微动、真实GPU预算均未通过。禁止把101751单图控制的exit0解释为样板树整体验收通过。
