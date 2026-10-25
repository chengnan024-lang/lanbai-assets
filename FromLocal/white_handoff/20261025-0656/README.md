# 1149秒白段交接：调色覆盖旧白遮罩的本地集成修复

运行时间：2026-10-25 06:52–06:59，America/New_York。输入仓库 main=f78abf7。场景：`Assets/Lanbai/Scenes/Lanbai_FullPreview.unity`。

本地执行窗口已完成替换，仍只有一名工程写入者；原160分钟续作迁移后复用，旧定时保持停用。工程、已有备份和12包集成继续复用。此次按用户要求后台、静音运行，最终停止Play，不抢焦点。

## 结论

修复了 flicker_1025-02 的一项确定本地集成问题：旧 `PP_White` 的优先级仍为2，白段 `PPV_S10` 的优先级为13。1149.31秒之后，旧白遮罩虽有 `weight=1`、`postExposure=11`，后面的S10仍把曝光覆盖回0；同时天空驱动切换，画面突然掉回暗天空与旧海面。

将 `PP_White.priority` 恢复为原工程已定义的 `LB_Grades.MASK_PRIORITY=150` 后，白段连续进入近白画面，原先突然变暗没有再出现。**这不是 C1=B 最终遮罩的交付或验收；S1继续保留，等正式镜与白包及工具到达后复测。**

## 实际修改

- FullPreview场景仅一行：`PP_White.priority: 2 → 150`。已对增量备份做完整文本差异核对，恰好1行替换。
- `LB_FullAssemblyBinding.cs`：绑定已交付调色时明确设置上述优先级，防止今后重新绑定退回旧值。
- 新增Editor-only `LB_WhiteHandoffAudit.cs`，用于读取绑定/运行态、临时静音、运行态单项对照和受保护的单场景保存。它不进入世界运行程序。
- 正式 `Lanbai.unity` 未改；LB_Journey、Dispatcher、Overlay、诗句、材质和.meta未被覆盖；1025秒修复完整保留。
- 永久修复仅调整白遮罩；黑遮罩仍为3。首轮运行态试验也临时把黑设为151，但其权重全程为0；最后保存后复测是白150/黑3，仍复现改善。

补丁见 [场景唯一一行差异](code/Lanbai_FullPreview.unity.patch)、[绑定工具差异](code/LB_FullAssemblyBinding.cs.patch)。原项目既定优先级见 `Assets/Lanbai/Editor/LB_Grades.cs` 的MASK_PRIORITY，以及 `LB_Builder_Scene.cs` 既有设置逻辑。

## 复测证据

旧场景与修复场景均从独立Play开始，使用同一诊断相机、固定机位、同一时段1139–1156秒，ARGBHalf → PPv2 → sRGB PNG，约每0.1秒一帧。诊断相机使用D-28基点 `(0.55,1.70,2.05)`；未更改旧车的主座位，也不是头显双眼录制。

| 条件 | 帧数 | 捕获错误 | 1148.8–1149.9秒内相邻帧平均RGB差峰值 | 1150–1155秒图像平均RGB范围 |
|---|---:|---:|---:|---:|
| 修复前，白2/黑3 | 168 | 0 | 76.678 | 30.891–33.461 |
| 独立Play临时对照，白150/黑151（黑权重0） | 168 | 0 | 2.923 | 247.663–247.914 |
| 保存后重新Play，白150/黑3 | 168 | 0 | 3.444 | 247.663–247.921 |

像素值范围0–255；这里是图像差统计，不是闪烁频率、VR舒适度或主观画质分数。三个关键运行保留完整CSV与精选帧，[全部统计](metrics.json)。

最初同一次Play内回跳的额外试验也保留，但后发现天空全局量会遗留，所以它**不用于主结论**；随后另启独立Play确认，与基线一样在白段取得 `Sky_Overcast_Night_2048x1024`、`_Udon_StarGain=(0,1,1,1)`，避免把状态遗留误当修复效果。

- [修复前1149.32秒](evidence/white_handoff_0657_before/0101.png)
- [保存后1149.31秒](evidence/white_handoff_0656_saved/0101.png)
- [保存后1152.04秒](evidence/white_handoff_0656_saved/0128.png)

补充验证白段退出：1177–1190.96秒137帧，0捕获错误；末帧已回到旧道路/车厢，运行态1193.595秒 `PP_White.weight=0`。该检查只确认没有卡在白屏，不等于假醒最终美术验收。[退出末帧](evidence/white_handoff_0659_exit/0136.png)

## 保存与现场

- 复用原全工程/增量备份，只为本次修改另备FullPreview、绑定工具及各自.meta。
- 增量备份：`E:/IDMdownload/VRCC/Backups/continuation_20261025/takeover_0650/before_mask_priority/`。
- 保存后一次Play退出出现dirty标记，未直接丢弃或盲存；先以saveAsCopy保存独立快照，逐字节SHA256与磁盘场景相同，才清理延迟Undo记录并保存。原始快照保留在同级`unsaved_preview_after_test.unity`。
- 最终心跳：编辑模式、focused=false、sceneDirty=false、compileFailed=false，无排队请求；见 [心跳](evidence/final_heartbeat.json)。Play期间AudioListener.volume=0，返回编辑模式恢复原值。
- 正式场景SHA256仍为 `16f5d9d7d2fda794cbd6353038037c493367285bc128f341bdf45762f25c5af0`。
- FullPreview修复后SHA256为 `ade220704c2ef088e27208fe0964e6854e9b345f3b8132fffb57c84cc2032343`。
- 原始全部捕获仍在本地`flicker_0315/captures/white_handoff_*`，没有覆盖旧证据；本次只上传CSV、相关结果和精选帧。

## 仍需后续交付

按f78abf7，镜与白、暮与天空、Director v1.3/测试工具1.2.0仍待终审与带“同步：”的交接条目，本轮无新增获准包可导入。诗句两个文件明确不同步。晨云、根部、样树、7a布局由既有云端负责人继续。

正式镜白接入后须关闭旧PlaceStarSea占位，并按新的flicker_probe/transitions_sweep验证C1=B、最终时间和真实双眼；当前本地F16=1149.31，与新包所述1150.31存在待接入核对的差别，本轮未擅自更改音乐时间。公交棋盘消散、镜面frustum未复现项、多人和Quest3+VD头显验收均未关闭。

本地只提交FromLocal。本轮附上[研究协作请求](../../coordination/20261025_abai_research_support_offer.md)；已提交不代表总控已读或已分派。
