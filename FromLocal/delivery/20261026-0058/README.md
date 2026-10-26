# 2026-10-26 本地新包接入与实际画面验证

本轮已完成获准且齐套的新公交、暮景/天空/7a、13镜与白、字幕v5、Gate r10/Inside、样板树r2及Director1.3r2接入。测试工具1.2.2及六项测试已取得用户批准并执行。03:16最终只读检查：FullPreview干净、非Play、音量1、编译正常；30个Udon程序Ready，Bus Check 0错误/0警告。树和公交切片仍有失败，不能把本轮写成全部验收通过。

工程来源是main `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`加本目录明确列出的本地补丁。`a5a75cb`是在其上回传工具方案。本次仅提交FromLocal；未修改总控HANDOFF_LOG。[逐文件源账本](integration/source_ledger.json)只覆盖实际核对的314源文件，不声称整个工程等同仓库。审阅补丁在[patches](patches)，本地Editor辅助代码仅供审查，禁止把所有入口自动重放。

## 已完成的接入与修复

|内容|实际结果|
|---|---|
|Director1.3r2|生成、接线、独立Play验证。保留_spawnFadeEnded三终态及实际限幅dbgDEV；修复HOLD倒拖回站台卡黑，真实时间超时25秒；倒拖/暂停/跨窗/自行淡入均能结束。|
|新公交|新车启用，旧模型/座位/碰撞关闭但保留；23座位与字幕深度表重绑。修正ShaderLab Header解析、5张数据贴图linear、FBX自动LOD与显式LOD重复。02:08证实FBX几何X/Z相对BusLayout反向；搭建器仅对明确180度反向烘入直属子对象，Model根identity，未知错位拒绝自动旋转。材质表补Piping/Sleeve/LatchCream。|
|CabinCube|按交付说明在主眼位、独立隐藏PreviewScene仅烘车内管灯，排除世界/玻璃/PP；最终ARGBHalf→RGBAHalf立方图最大2.476563，确认保留HDR，绑定三套玻璃材质。[方法和六面](cabin_cube_hdr)。首次max1的直接Cubemap版本已被替代，未作为最终绑定。|
|暮景/天空/7a|新窗口驱动接管天空/日光，旧暮色fallback及出海重复曝光让出。Sky在淡变中22.5→1000→22.5的回跳重新初始化缓存，回到原雨夜混合状态；2ms取样差异如实保留。[证据](sky)。|
|镜白|13镜、白驱动及Overlay已搭接；1010–1150.31关闭旧PlaceStarSea，新白1136.58–1186.46让旧第一白曝光/遮罩退出。F16仍1149.31，音乐不改。1025 SeaA/B各自运行时材质修复保留。|
|字幕v5|73页、4968深度单元、23座位、7套字体VERIFY。Udon不支持TMP直接取transform/gameObject，使用配套Renderer/Component。仅Journey写PP；字幕取实际dbgDEV；数字层24排除反射。02:23确认颜色MPB覆盖SpriteRenderer隐式_MainTex导致硬矩形，专用材质保存原Sprite贴图、Bake补同样绑定；独立Play中英柔边正常。[同帧与独立Play](HALO_FIX.md)。|
|Gate r10/Inside|新门/群臂/云与回望驱动搭接。DeliveredGate容器令Apply根查找失效，临时提取3已知根、Apply/Build后恢复层级，108群臂尺寸已烘。最终主renderer/transform数组无空位；rOcc是可选贴图数组，84个null由驱动显式跳过，不当成丢对象。|
|树r2|4预制体重建，keepalpha/lighting-alpha采用上游修复；道路杨树仍未替换。隔离ROI后闪烁仍FAIL，交原树负责人处理。|
|片尾白退出|原PP_White覆盖ACES、底层S12 Neutral，在权重归零时枚举跳变，1253.95→1254.05突然变亮。仅给FullPreview深复制独立白profile，取消tonemapper覆盖、priority150保留；原profile和正式场景文件未变。[同帧诊断/保存后独立Play](white_tail)，最终x40补测见下。|

## 最终有效测试与原失败

完整历史索引：[test_index.json](test_index.json)。每个run的原result/manifest保持原结论，补测不把原FAIL改成PASS。

|最终证据|结果与限制|
|---|---|
|[bus_slice 023007](../../bus_slice/20261026-023007/summary.md)|**FAIL**：窗框覆盖0.238521/0.086425低于0.3，立柱微动0.011815高于0.005警戒；0错误/未声明写。025548为6机位校准，所有候选覆盖仍低，不降低阈值；其技术PASS仅指校准流程，不是公交验收。|
|[bus_dropin 023121](../../bus_dropin/20261026-023121/summary.md)|技术PASS，0错误/未声明写；不能替代近景/美术/VR检查。|
|[tree_sample 020123](../../tree_sample/20261026-020123/summary.md)|**FAIL**：隔离叶缘ROI，hero p99=18.5503>12；hero变动34.9220%、right34.7996%>5%；静止对照0%。不是旧车/灯柱混入，不能与旧全画面12.3/5.275%直接同比；0错误/越界写。|
|[镜白023133](../../flicker_probe/20261026-023133/summary.md)|技术PASS：1016–1042、1139–1156、1177–1191最大相邻EV约0.14/0.19/0.14；第一段漏8/781，另两段0。0编译错误/异常/未声明写。字体下划线缺字等警告保留，不写零警告。|
|[全片36窗023256](../../transitions_sweep/20261026-023256/summary.md)|**原FAIL保留**：x06漏4/33=12.12%，其余35窗在10%缺帧门槛内；0错误/越界写。x09/x11/x13/x35/x38等警示仍待对应负责人审图，不等于画面全通过。|
|[x06+x40最终031057](../../transitions_sweep/20261026-031057/summary.md)|补测技术PASS，0漏帧/错误/越界写；片尾正向亮度上升0.25s=0EV、1s=0EV、2s=0.45EV。最大粗步差1.46EV是向暗淡出，不是原来的正向闪白。此run只覆盖x06/x40，不伪称重跑全片。|
|F12前024253/上024327|两视角连续探测技术PASS；另有987–997每0.25秒82张固定时间图，不能混作连续采样。|
|[gate_clouds_test024458](../../gate_clouds_test/20261026-024458/summary.md)|工具PASS，23项声明内写、0未声明写/错误。重建中2条Gate对象绑定警告保留；最终编辑态主数组已齐，后续独立Play无该警告。性能估算不等于GPU/VR实测。|
|Gate正031149/回031222|HDR Cube完成及材质保护补齐后最终技术PASS，0错误/未声明写。并未证明六根回望卷手都可辨。|

## 测量与真实越界写说明

- 早期011103/013039/013334/013944混入ClientSim欢迎UI，视觉数值无效；保留原报告、公开例图及说明，不发布无效截图全集。02:08前Play/公交测试又受反向车体影响，均有PRE_AXIS_CORRECTION标记；独立树测试不受影响。旧0.51EV不能作为最终镜白的有效before。
- 工具跨重载漏存内容哈希已补，逐字节相同的mtime条目不误报；站立Teleport落车底已改实际UseStation。真实ScreenCamera与D28眼位相差0.557m，桌面不代表头显。转场重叠旧dbgT造成漏拍已补等2真实帧，停Play前退出座位消除SDK销毁顺序异常。
- **022420真实12项越界写**是11个Inside_Gain材质和LB_Cloud运行时颜色/方向。原件、差异和依据保留，恢复逐项核对的已有备份值；不是精确测试前快照。切片工具原本使用SaveAssetIfDirty，全局落盘调用链尚未归因，不能错判为切片保存函数。
- **030411真实1项越界写**是LB_Tentacle的运行时_Light2.z，保留原件/差异，从有效旧完整备份只取此单文件核对恢复。原失败不改成通过。
- Editor诊断保护仅在QuietNextPlay启用：记录Inside及旧Generated/Materials已知材质的内存值/磁盘hash/原dirty；退出只在磁盘hash不变时恢复内存，不保存资产、不覆盖本来dirty、不隐藏真实磁盘写。最终031057/031149/031222均0未声明写。[恢复回执](integration/material_guard)。

## 画面反馈与待定事项

1. 车窗0.5m/1m、40×30度、20ppd和0.3覆盖阈值不变。6种取景都不能达到覆盖；请公交负责人明确规范机位/几何定义。新车内前牌从座位看文字反向（白蓝），请同时复核。海段抬头仍见消散中车顶/碎片，未关闭美术问题。
2. 506.4尾柱已可见；532.4斜亮痕需海/7a负责人确认是否预期海脊。门回望被车厢遮挡，6卷手无法全部辨认，未标通过。桌面每首诗和3段黑边图已拍，早期poem/bars在halo修复前，有明确标注；庄子P08b中文空页是strings_all.empty_keys设计，英语另拍。
3. **时间口径待总工审定**：场景Journey S_WAKE=1249.96，新Cabin tAct12=1251.96；旧S_DAWN=251.64与新驱动252.64不同，旧S_GATE=150.3与新门窗口133.8并非同一口径。不擅自挪音乐或改高风险状态机；请先给具体同步口径与影响范围，再决定是否需要用户确认。片尾本次只修色调跳变。
4. [23时刻性能](../../performance/20261026-0300/README.md)包括870/950/990、门段、1105/1116。初轮700受预热超时没有样本，修采样器只补700。编辑器帧间隔不是纯CPU，编辑器draw含多相机，图形分配不是物理VRAM；GPU读数未验证、Udon标记不加总。相机跟随方法与旧底账不同，不作严格前后同比。

## 现场与保护

当前唯一写入者不变，旧两聊天未加载且无后台工程命令；本轮不创建子代理、部署聊天或第二定时。Unity2022.3.22f1隐藏batchmode/D3D11，窗口句柄0；focused心跳字段不当作前台证明。03:16最终编辑器检查在[integration/final_editor_audit.txt](integration/final_editor_audit.txt)。全部delivery_20261026请求已终态，严禁重放；未来只增量处理新交付/新反馈。

正式Lanbai.unity SHA256保持`16f5d9d7d2fda794cbd6353038037c493367285bc128f341bdf45762f25c5af0`；原白profile SHA256保持`896356aabfd946336e261f8eca6136830c8b3b6eac34b3d5aafdc9756e04cc3c`。最新FullPreview/源码哈希见[integration/current_hashes.json](integration/current_hashes.json)。已复用有效全备份并仅补增量；未升级Unity/SDK/依赖、清盘、删锁、强杀或正式上传。Quest3+VirtualDesktop、多人、C1=B最终验收均未实测。
