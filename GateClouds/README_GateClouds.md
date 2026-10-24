# 触手之门 · 云套件 GateClouds v1.5（云海、云塔、远云、地平线云团、越远越宽的光束、阴影楔）

写的人：云端「门」会话（分支 `pkg/gate-clouds`）。对象：小楠电脑上 Unity 2022.3 那一侧的会话。2026-10-23。
**这里的 shader 和 C# 都没有在 Unity 里编译过。**
- shader：slangc 2025.6 做过语法 / 类型检查（`Tools~/slang_check.py`，三个新 shader 的每个 pass、每个关键字变体都过了，`Lanbai_Tear.shader` 和远潮也重新查过）。
- C#：mono `mcs` 对一份按 Unity API 真实签名写的桩做过类型检查（`Tools~/cs_check/`）。这不是 Unity / UdonSharp 编译。
- **共用检查**（`Common/Tools~/compile_check`，DXC + Unity 2022.3.22f1 CGIncludes / Roslyn），2026-10-23：
  - `check_shaders.py GateClouds/Shaders Tear/Lanbai_Tear.shader Gate/Shaders` → `8 files, 58 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`
  - `check_cs.sh GateClouds` → `C# CHECK OK (0 assembly error(s), 0 lint warning(s)). Not a Unity compile`
  - 为此把门 / 裂口 / 云的 shader 里自己声明的 `_Udon_` 全局量都换成 include `Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc`（`LanbaiGateSky.cginc` 也是），两个 include 碰头不再 X3003。
- 第一次在 Unity 里跑，请把 Console 原样推到 `FromLocal/`。

10-08 的门导入测试说：门在 Unity 里基本还原了定稿，看不到的是**我们漏交了云**。这个套件补这一块，并把门测试里提到的几件收尾一起做了：

| 门导入测试里缺的 / 提到的 | 这一版 |
|---|---|
| 云海：没有布局，地平线以下是一片平的灰雾 | **`Lanbai/GateCloudDeck`**：一张大四边形，每个往下看的像素对"云顶高度场"做体积步进：背光的暗云头、云头轮廓上的银边（只在月光路和裂口脚下最亮）、云槽里的雾、裂口的光池。写深度，触手根、裂口脚、云卡都和云头正确地前后遮挡。 |
| 云塔 9、远云 4、雾卡 2、地平线云团 22："LanbaiFog 里的 yaw 公告板、下沉 / 塌陷"没有 shader | **`Lanbai/GateCloudCard`** + **门专用云卡 v2**（5 种形状，Blender 体积渲染，月光从云后低角度照来，场景线性，三个光照通道）。37 张卡按 `GateLayout_v2.json` 原位置，第 10 轮给最近的 2 座云塔各加了一层背后的卡，共 39 张。云塔的塌陷、下沉、淡出由 `LanbaiGateClouds`（U#）按时间驱动。 |
| 光束卡等宽，`widen 3.2` 做不到 | **`Lanbai/GateBeam`**：从伤口出发、越远越宽的柔光瓣。 |
| 阴影楔 4 道：没有 shader 和网格 | 同一个 shader 的乘法模式。 |
| 峡谷 3 张卡没有网格 | **直接刻进云海的高度场**（AD 原话是"撕开云海本身"），谷底是白自己的雾光。 |
| 光池 `Tear_CloudGlow` 贴在平的云顶上 | 云海现在有真实的云头，平面光池会被切碎 → **光池并进云海 shader**，Build 会关掉 `Tear_CloudGlow`、`Tear_CloudGlow_Additive`、`Tear_LightLane` 的 renderer。 |
| 远潮雾带参数是旧的（§2.2 第 10 条） | 远潮 shader **v2.3**：include `LanbaiGateSky.cginc`，和触手、天空同一份雾色；默认值换成新的（§7）。 |
| TentacleSway ForwardAdd POINT 变体真的除零（§2.1） | **v2.7d**：`noforwardadd`（门里没有点光源，补光是 Not Important，这个 pass 只多画一遍）。 |
| `Lanbai_Tear.shader` 第 99 行 `[Header]` 的括号和逗号 | 改掉（第 94 行同类的也改了）；并且 include 改成公共的 `Assets/Lanbai/Common/Shaders/LanbaiVR.cginc`，**不用再从 lens_tech 拷一份**。 |

---

## 0. 先看图

`Docs~/` 里是 `Source/preview_gate.py` 合成的整帧：**云海 + 云卡 + 光束按 Unity shader 的同一套算法算出来**（`deck_ref.py` 是云海 shader 的逐行 numpy 移植），用调色套件的 PPv2 S4 引擎模型调色（`Grading/Tools~/engine/ppv2_engine.py`，无 bloom / 暗角）。触手和裂口不是我们算的，是从本地 10-08 的 Unity 截图贴回去的（只贴和"那张截图的天空 / 平雾"差 10 码以上的像素；裂口周围那圈椭圆是贴图接缝）。
**合成造成、不是目标的东西**：画面里的平顶黑块（10-08 截图里的触手 / 石碑剪影）、压在云海前面的裂口尖端（截图里没有云海挡它，Unity 里会被云头挡住），以及星星（截图里的天空盒）。这些都不是云套件的画面，评审请不要按它们打分。U8 前方、U8 侧窗和后窗没有 Unity 截图可贴，所以画面里只有云。

| 文件 | 是什么 |
|---|---|
| `Docs~/compare_{key,U7,U8fwd,U8side,rear}.png` | 全尺寸（key 2560×1072，其余 1920×1080）：上 = 这一版，下 = 定稿 `Gate/Renders/` |
| `Docs~/deck_only_*.png` | 只有云海（全尺寸），对定稿 |
| `Docs~/deck_linear_{key,U7}.exr` | 云海的场景线性值（调色前），给审片按引擎复核 S4 |
| `Docs~/deck_scroll_U7_60fps.mp4` + `Docs~/deck_scroll_frames/` | U7 机位 2 秒、60 fps 的云海滚动（只有云海，960×540，不含光池），查闪烁用。**是 v1.4 的代码出的**：v1.5 只挪了光池和脚下的光，没改步进和银边，闪烁的结论不变 |
| `Docs~/cards_contact.jpg` | 5 张云卡的三个光照通道 |
| `Docs~/fse_clouds.json` | 透明叠绘（§5.3） |
| `Docs~/flashcheck_U7_720p.json`、`Docs~/crawl_map_U7_720p.png` | 第 10 轮：U7 2 秒 60 fps、1280×720 的滚动序列，跑了 `Art/tools/lens_tech/flashcheck.py` 和 `Source/measure_crawl.py` 的结果（§8 第 6 条） |
| `Docs~/perf_options_crops.png` | 性能方案 B / C 和现在的 1:1 对比（`给总控.md` §1） |
| `Docs~/iterations/` | 01–11 的迭代记录（每轮一张图一句话） |
| `Docs~/r4_crops/` | 1:1 前后对比裁图（上 = 第 3 轮，下 = v1.5）：边光碎块、U7 台阶、U8 前方、光池、云谷 |

---

## 1. 交付清单（拷进 Unity 的是整个 `GateClouds/`）

拷到 `Assets/Lanbai/GateClouds/`，和 `Assets/Lanbai/Gate/`、`Assets/Lanbai/Common/` 平级。

**先把仓库的整个 `Common/` 拷到 `Assets/Lanbai/Common/`**（v1.5，总导演 A1）。门、裂口、远潮、天空盒和三个云 shader 都 `#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"`（裂口还要 `LanbaiVR.cginc`），本地以前从来没收到过 `LanbaiGlobals.cginc`。**不拷的话 8 个 shader 全变粉。** 两个云 shader 另外 include `Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc`。`Tear/` 旁边以前拷的那份 `LanbaiVR.cginc` 可以删，现在只用 `Common/` 里的。`Source/` 是 Python，`Tools~/`、`Docs~/` 带 `~`，Unity 都不编译。

| 文件 | 是什么 |
|---|---|
| `GateClouds_Layout.json` | **唯一的数据源**：时间窗、云海、39 张卡（GateRoot 坐标、尺寸、透明度、增益、镜像、队列、雾上限、化开、云塔的塌陷 / 下沉 / 淡出关键帧）、2 束光 + 4 道楔、远潮材质值。由 `Source/gate_clouds_layout.py` 从 `GateLayout_v2.json` 生成。 |
| `Shaders/Lanbai_GateCloudDeck.shader` | 云海 v2（§3）：主 pass + ShadowCaster（进 `_CameraDepthTexture`） |
| `Shaders/Lanbai_GateCloudCard.shader` | 云卡（§4） |
| `Shaders/Lanbai_GateBeam.shader` | 光束 / 阴影楔（§5） |
| `Textures/Deck_Detail_1024.png`、`Deck_Macro_512.png` | 云海的两张周期贴图（线性数据，§3.2） |
| `Textures/GateCard_{Congestus,Bank,Strato,Puff,Wisp}.png` | 门专用云卡 v2（§4.1） |
| `Textures/deck_tiles.json`、`gate_cards.json` | 量程、通道缩放、云底位置 |
| `Editor/LanbaiGateCloudsBuilder.cs` | 菜单 **蓝白/Gate Clouds/Build**（§2） |
| `Runtime/LanbaiGateClouds.cs` | U# 驱动（§6） |
| `Source/*.py` | 生成器、参照渲染、测量（§9） |

**贴图**（显存合计约 **19–20 MB**，带 mip）：
| 贴图 | 尺寸 | 导入 / PC 格式 | 显存 |
|---|---|---|---|
| `Deck_Detail_1024.png` | 1024² RGBA | 线性（sRGB 关），**不压缩 RGBA32**（高度场压缩会出块） | 5.6 MB |
| `Deck_Macro_512.png` | 512² RGBA | 同上 | 1.4 MB |
| `GateCard_Bank / Strato / Wisp.png` | 2048×1024 RGBA | sRGB，BC7，Clamp | 2.8 MB × 3 |
| `GateCard_Congestus / Puff.png` | 1024² RGBA | sRGB，BC7，Clamp | 1.4 MB × 2 |
| `Gate/Textures/Tear_CloudLanes_1024.png`（云海读） | 1024² L | **以本地导入脚本为准（BC7）**，云的 Build 不改它的导入 | 1.4 MB |

---

## 2. 怎么搭（测试场景 `GateTest.unity` 里先做）

1. **把仓库的整个 `Common/` 拷到 `Assets/Lanbai/Common/`**（没有 `LanbaiGlobals.cginc`，8 个 shader 全粉）；拷 `GateClouds/` 到 `Assets/Lanbai/GateClouds/`；确认 `Assets/Lanbai/Gate/Shaders/LanbaiGateSky.cginc` 在。把仓库里改过的 `Gate/Shaders/`（远潮 v2.3、TentacleSway v2.7d）和 `Tear/Lanbai_Tear.shader` 一起更新。
2. **两个 Build 的顺序**：先跑本地的 `LB_GateTest.Build`（搭门，用 10-08 的灯），再跑 `蓝白/Gate Clouds/Build`。**以后每次重跑门的 Build，都要再跑一次云的 Build。** 忘了不会出错：`Apply`（编辑器和运行时）发现云卡 / 云塔的 renderer 丢了，会跳过并警告"请重跑 Gate Clouds/Build"。
3. **远潮材质**：`M_TentacleTide_A / B` 照 §7 填三个值（`_HazeNear`、`_HazeFar`、`_BandEl`，JSON 的 `tide_material` 里也有），或者右键属性 Reset。云的 Build 不改它们。
4. **参考相机的 far plane ≥ 20 km**（云海四边形 40 km 见方，挂在 GateRoot 下；远处的平均云面回退到 16 km）。门本来要求 ≥ 14 km，测试场景配的是 45 km。
5. 打开搭好门的场景（要有 `GateRoot`，裂口根 `Tear_Root` 或 `Tear_Kit` 在它下面）。菜单 **蓝白/Gate Clouds/Build**（或 `LanbaiGateCloudsBuilder.Build()`）。它会：
   - 设贴图导入（`Tear_CloudLanes_1024.png` 不动，归门的导入脚本）：云海两张 = sRGB 关、mip、各向异性 4、PC **不压缩 RGBA32**（高度场压缩会出块）；云卡 = sRGB 开、Clamp、mip、PC BC7、Alpha Is Transparency。
   - 建网格和材质（`GateClouds/Generated/`），在 `GateRoot/GateClouds/` 下建 `Deck`、`Cards/<id>`（37 张）、`Wedges/<id>`（4 道），裂口根下建 `GateBeam_Shaft_00/01`。
   - 关掉 `Tear_CloudGlow`、`Tear_CloudGlow_Additive`、`Tear_LightLane`（光池由云海画）、`Tear_FootSkyline`、`Tear_FootSkylineIn`（脚前的暗云唇：现在裂口脚落进云海真实的云头和峡谷里，美术 r2）以及测试场景的旧等宽光束 `Shaft_00/01`（和 `GateBeam_Shaft_*` 重复，技术 r2 #2）的 renderer。
   - 驱动 `LanbaiGateClouds` 挂在**常开的**物体 `GateClouds_Driver` 上（场景里有 `Director` 就挂在它下面），`root` = `GateRoot/GateClouds`。
   - UdonSharp（反射调用，没有 U# 也能编译）：没有程序资产就建 `Assets/Lanbai/UdonPrograms/LanbaiGateClouds.asset` 并编译；组件经 `UdonSharpUndo.AddComponent`（或 `AddComponent` + `RunBehaviourSetup`）加上；填完数组 `CopyProxyToUdon`；**没有底层 UdonBehaviour 就报错停下**，不会静默完成。
   - 按 U7b 预览一次。可以重复运行（先删上一次搭的）。
6. **测试场景的 `FromLocal/gate_test/code/LB_GateTest_Run.cs` 第 123、124、127、134 行，再在第 174 行前插一行**（逐行的原文 / 改成：`给本地_补丁_LB_GateTest_Run.md`）：`SetPB(..., on = true)` 每次 Apply 都会把上面关掉的 `Tear_CloudGlow`、`Tear_CloudGlow_Additive`、`Tear_LightLane` 重新打开（光池画两遍、平面光池被云头切碎），`Shaft_00/01` 也每帧开着。**请把这几处改成 `on = false`（或删掉），否则 §8 的截图作废**（技术 r2 #2）。第 5 处就是在 `LB_GateTest.Apply` 的 `SceneView.RepaintAll()` 之前加 `LanbaiGateCloudsBuilder.Apply(t);`（编辑模式预览云塔和卡的 property block；Play / VRChat 里由驱动写）。
7. 正式场景：分发层按 `LanbaiWindow()` 在窗口内每帧调 `LanbaiTick(t)`，在遮挡下调 `LanbaiActivate(on)`（CONTROL §5）。
8. **门的总驱动 `LanbaiGateDriver`**（`Gate/README_GateDriver.md`）每帧写 GateRoot 和全局量。**上线前置条件（技术 r2 #4）**：云海依赖的 `_Udon_CloudTop`、`_Udon_GateOrigin`、`_Udon_TearFoot` 现在只有编辑器里的测试脚本写。正式世界里要由**门的总驱动**每帧写（`给总控.md` §3），否则云海不随 v_g 流动、云顶停在 −57.4、峡谷和光池固定不动。

**读的全局量**（都已登记）：`_Udon_CloudTop`、`_Udon_GateOrigin`、`_Udon_MoonDir`、`_Udon_TearPos`、`_Udon_TearH`、`_Udon_TearFoot`，以及门内会话定义的 `_Udon_InsidePortal`（x = 裂口平面世界 z，y = 1 生效：U9 以后平面另一侧的云海、云卡、光束都不画）。**写的全局量**：没有。第 4 幕的光雾带（`_Udon_FogBand*` 和整个雾 / 月 / 星一族）按 D-22 归门的总驱动 `LanbaiGateDriver` 写（`Gate/README_GateDriver.md`）。

---

## 3. 云海 `Lanbai/GateCloudDeck` v2

### 3.1 怎么画的
- **几何**：`GateRoot/GateClouds/Deck`，40 km 见方的平四边形，跟着 GateRoot 走。**顶点 shader 把它拉到眼下 1.5 m**：这是一个"代理面"，所有云头都在它下面（没有云头高过眼下 2 m），所以真实撞点总在它后面 → 输出**保守深度**（reversed-Z 下 `SV_DepthLessEqual`），early-Z 照常工作：被车厢、触手挡住的像素不跑步进。
- **抖动（第 10 轮）**：`LanbaiHash13`（Common `LanbaiVR`；替掉 `sin × 43758`，在不同 GPU 上结果一样），取的是视线和云顶平面的交点。这个交点在云海坐标里，按约 1.5 个像素的足迹量化。所以两只眼看同一片云海得到同样的抖动，而且抖动锁在世界上，不跟屏幕走。`deck_ref.py` 同步（`hash13`）。
- **步进**：从眼睛沿视线进云层，**步长按离云面的距离自适应**（`dt = clamp(0.9 × 离云面高度 / (|V.y| + 0.6), 0.004 t, 0.05 t)`，离得近才走小步；离云面超过 4 层云皮时不受 0.05 t 的上限）。**起点**（技术 r3 #1）：视线还在全强度的舒适车道里（横向 < 45 m）时，那里的云头都在眼下 57 m 以下，所以从 `min(57 m / |V.y|, 45 m / |V.x|)` 开始；出了车道就从 12 m 开始，近处高过半眼高的云头不会被跳过或平切。钻到高度场下面以后二分 3 次，再在最后一个区间里**线性插值求交**。抖动是**世界方向**的哈希（两只眼对同一个远点取同一个值，不跟屏幕走）。步进和二分只用便宜的 `tex2Dlod`；只有最后一次着色用 `tex2Dgrad`（硬件各向异性）。
- **高度场** = 宏观起伏（6.4 km）+ 振幅 × 积云头（1.6 km 周期，云头半径 9–40 m）。噪声都在**云海坐标** `worldPos − _Udon_GateOrigin` 里取，云海跟着门以 v_g 走。
- **云面**：朝月漫反射（烘好的 N·L）× 前方云头的投影（烘好的到月路径）+ 天光 × AO；菜花小鼓包做成**明暗**（同一张图缩小 5 倍的 AO），不做几何（几何会把掠过的视线截停，银边上出黑点）；云槽（低于局部平均面）变暗并填进雾。
- **银边**：云头上一层 0.5 m 的软云皮。视线越过云顶、又离开时穿过它，前向散射的月光就是银边。**只在两个楔区最亮**：月光路（月亮方位 ±7°、0.3–2.5 km、×0.9）和裂口脚下（600 m 内，×1）；别处 16%（美术 r2：× 0.35）。视线"落到"它马上要撞的云顶上时，那段云皮不算（暗的顶、亮的轮廓）；越过轮廓再撞上后面的云头，照常算。比一个像素还细的银边淡掉（防远处 1 px 闪）。
- **银边 · 第 4 轮**（美术 r2 BLOCKER / MAJOR）：① 云皮要等离云面的高度**回升一个云皮厚度**才算"越过云顶"（以前任何一点回升都算，菜花噪声让半个顶盖被算成银边 = 撕碎的亮块）；② 撞上时"是不是轮廓"是平滑的斜坡（`_Skin3.xy`），不是开关；③ **每个云头自己的银边**：计入时乘 0.4–1.6（细节贴图换一个偏移和尺度的低频噪声，`_Skin3.zw`、`_RimVarScale`），宽窄亮暗各不相同；④ 越过云顶时离云面不到 1.5 像素的，那一部分像素算云头本身的暗面（`_Skin2.w`），轮廓不再是一阶一阶的亮台阶；⑤（美术 r3）撞上前离云面已经回升了一部分的视线，按回升的比例保留银边（不再被"计入门槛"切成方头的碎块）。
- **VR 舒适（圣经 §1.8，v ≤ 1.05 d）**：云海以 59 m/s 沿 z 流过，只有车行进路径**横向 ±56 m 以内**的云头会贴近车。这条"车道"里的起伏**按比例压低**到眼下 57 m（形状保留），45 → 140 m 平滑放开。别处不受影响。
- **峡谷**：从裂口脚朝车方向 230 m × S，宽从白的 20% 收到 0，刻下 25 m，两唇隆起 5 m，谷底 = 白的雾光 `#C0B9E4 × 0.35`。
- **光池**：`× (1 + (0.607, 0.683, 1.144) × weight × Tear_CloudLanes)`，weight = 0.75 exp(−(r/420 S)²) + 0.25 exp(−r/900 S)，按**裂口坐标**算：原点 = `Tear_Root`（脚在它的本地 (0.5, 0, −30)，即朝车 30 S），+y 背离车。中心在 (0, 150 S)，也就是**根的远侧**；条带图按 `_LanesRect` (−2000, 2000, −2400, 1600) 取，第 0 行 = 远处，和 `Lanbai_Tear` 的 CloudGlow 完全一样（`GateLayout clouds.pool`）。v1.4 把中心放到了车这一侧、条带错开约 800 m（总导演 A2），v1.5 改正。强度 `_PoolTint.w` = 1.5。
- **脚下的光**（第 4 轮，美术 r2 / r3）：裂口照在脚下云头上的光，加法，`#E2E8F3 × 6.0 × exp(−(r / 160 m)²) × lerp(0.1, 1, AO²)`（主要落在云头顶上），中心在**脚的远侧 100 m**（× S / 0.64，和定稿一样光在白的后面）；同样的光也算进"越过云顶的那部分像素"（否则被照亮的云头一圈黑描边，美术 r3 #1）。v1.5 用这组值让 keyart "脚下中心 / 月光路"（p95，y 740–800）= **1.34**（圣经 ≥ 1.33；v1.4 是 0.79）；U8 前方画面下 40% p50 38、p95 142（D-15 的参照：定稿窗外 p50 63、p90 137）。
  - 历史：v1.4 初版 250 m 朝车把 U8 前方烧成白泡沫（美术 r3 BLOCKER），v1.4 收到 120 m 朝车，脚下又不够亮（终审 0.79）；v1.5 把光池中心改到远侧（总导演 A2）以后，光放在白的后面，U8 前方（在脚前 600 m）只收到一点，keyart 的脚下才亮得过月光路。
- **云槽**（第 4 轮）：天光 × AO 降到 0.35（× 0.7），槽里混雾的比例 0.75 → 0.4、强度 0.55 → 0.7（槽更暗、更深，不再被雾抬亮）。
- **雾**：`LanbaiGateFogColour`（光雾带 + 0.35 月晕）在撞点距离 × 1.3 处混。远处 2.5 km 外用平均云面。
- **深度图**：第二个 pass（`LightMode = ShadowCaster`，同一个高度场、≤ 48 步、无光照），云海进 `_CameraDepthTexture`：软粒子、裂口的光束 / 褶、云卡的深度淡化都看得到云头。renderer 的 Cast Shadows 仍是 Off。

### 3.2 两张贴图（`Source/deck_tiles.py`，月亮方向烘在里面，约 40 秒）
门里月亮不动（GateRoot 不转），所以"往月亮走要穿过多少云"和"朝月 N·L"都能烘。
| 贴图 | R | G | B | A |
|---|---|---|---|---|
| `Deck_Detail_1024`（1.6 km，1.56 m / 像素） | 高度 −12…56 m | 到月路径 0…160 m | 天空 AO | 朝月 N·L |
| `Deck_Macro_512`（6.4 km） | 起伏 −12…12 m | 到月路径 0…400 m | 振幅场（shader 映射到 0.3…0.8） | 亮度起伏 0.75…1.15 |

### 3.3 能调的（材质上；默认值 = 我们定的 = `deck_ref.DEFAULTS`）
| 想要 | 调 |
|---|---|
| 整体亮 / 暗 | `_Gain`（0.9）；只调月光 `_MoonE`（0.38） |
| 银边更亮 / 更宽 | `_Skin.x`（0.8）、`_Skin.y`（0.5 m）；楔外的银边 `_RimWedge.w`（0.16） |
| 月光路更宽 / 更亮 | `_RimWedge.x`（7°）、`_RimWedge.y`（0.9） |
| 每个云头银边差多少 | `_Skin3.zw`（0.4–1.6）；噪声尺度 `_RimVarScale`（0.37） |
| 轮廓台阶更软 | `_Skin2.w`（1.5 像素；再大银边会变细变暗） |
| 远处细银边闪得少一点 | `_Skin2.y`（亚像素淡化，第 10 轮 3 → 1.5；再小远处的银边就淡没了） |
| 脚下的光 | `_FootPool`（半径 120 m、朝车 60 m、强度 2.0、槽里的底 0.1）、`_FootPoolColor` |
| 云槽深浅 | `_AmbK`（0.35）、`_Trough.z`（0.7）、`_Trough.w`（0.4） |
| 侧窗 / 后窗的云更亮 | `_Surf.z`（朝月漫反射 0.8） |
| 远处更快化进雾 | `_FogDensity.y`（1.3） |
| 光池强弱 | `_PoolTint.w`（0.4） |
| 云卡底边 | `_Feather`（底部 15% 羽化、天光通道底部 30% 淡掉） |
| 省性能 | 只用 `auto_lite`（`_Adapt.y` 0.05 → 0.09，见 §3.4）。不要缩 `_MarchRange.y`：方案 B 在地平线前出一条亮带 |
| 后窗视角 | 和天空盒一样，`_BackBand` 1.25 |

### 3.4 性能（**参照渲染里数的，必须在 Unity 实测**）
- `deck_ref.py`（和 shader 同一套步进）：第 4 轮（新起点之后）keyart **24.2**、U7 16.4、U8 前方 15.6、U8 侧窗 20.3 步 / 像素（p90 30–47；第 3 轮是 20.5–21），8% 的像素在 2.5 km 内没撞上（用平均云面）。每步 2 次 `tex2Dlod`（近处 3 次），撞上后 3 次二分（各 2–3 次），最后着色 1 次各向异性 + 3 次 `tex2Dlod`。
- 估算（两只眼 2×1832×1920，云海占约一半，early-Z 去掉车厢挡住的约 1/4）：每帧约 **170 M 次双线性取样 + ~5 G 条 ALU**，在 RTX 3060 / 4060L 上大约 **1.5–2.5 ms**；深度 pass 另加约 0.3–0.6 ms（只在相机有深度图时）。**这超过总工程师给的 1–1.5 ms 目标的上沿**。我没有自己降画质：方案写在 `给总控.md`，请总导演定；本地先实测。
- **画质开关**（总导演 10-23、D-15：先合并，实测以后再按圣经 §1.9 的顺序砍，不先动云海的美）：`GateClouds_Layout.json` 的 `deck.quality` 选一档，Build 时把这一档的 `_Adapt`、`_MarchRange`、`_Steps` 写进 `M_GateCloudDeck`：
  | 档 | `_Adapt` | `_MarchRange` | `_Steps` | 平均步数 / 画面 |
  |---|---|---|---|---|
  | `default`（默认） | (0.004, **0.05**, 0.9, 0.6) | (12, 2500, 8, 3) | 128 | keyart 24.2、U7 16.4、U8 前方 15.6、U8 侧窗 20.3 |
  | `auto_lite` | (0.004, **0.09**, 0.9, 0.6) | 同上 | 128 | 少 9–16% 步；画面差平均 ≤ 0.08 码、p99 ≤ 1 码（`Docs~/perf_options_crops.png` 的 C） |
  切换：把 JSON 里的 `"quality": "default"` 改成 `"auto_lite"`，重新 Build（名字写错 = 用 `default` 并报警告）。直接在材质上改 `_Adapt.y` 也行，但下一次 Build 会被档位的值盖掉。
- **请本地实测（推到 `FromLocal/gate_clouds_test/`）**：导入后，在 **U7（t = 155.10）和 U8 前方（t = 169.65）** 两个机位（必要时加 U8 侧窗）量第 4 幕的帧时间，**有云 / 没云各一次**。"没云"= 关掉 `GateRoot/GateClouds`（云海、云卡、楔）**和** `Tear_Root/GateBeam_Shaft_00/01`。**只用一种测法**：编辑模式的 `LB_GateTest.Perf` / `Shoot`（`cam=U7`、`cam=U8fwd`）。要看 GPU Profiler / Frame Debugger 时，先用 `StatsBegin("cam=…")` 摆好相机，再在 Game 视图里抓。有余力再用 `auto_lite` 量一次。附 GPU Profiler 或 RenderDoc 里最贵的几项。总导演拿到真数据以后再定砍哪里。

---

## 4. 云卡 `Lanbai/GateCloudCard` + 门专用云卡 v2

### 4.1 云卡 v2（`Source/gate_cards.py`，Blender 5.1 / Cycles 真体积，和 v1 同一个形状生成器）
门里月亮在云塔**后面**、只高 8°，每座云塔和月亮的夹角都不一样。所以 v2 是**场景线性**、**光照分通道**的：
| 通道 | 内容 |
|---|---|
| R | 月光从云后右侧 35° 照来（月亮差不多在云正后方：暗的云体、宽的银边） |
| G | 月光从云后右侧 70° 照来（月亮偏到一边：右侧受光） |
| B | 天光（地平线的光雾带、头顶的夜、下面被月光照亮的云海） |
| A | 覆盖率（直通 alpha） |

每个通道存 `sRGB(线性值 / 缩放)`（导入 sRGB 开，shader 读到的就是 `线性 / 缩放`），缩放在 `gate_cards.json`（材质 `_Scale`）。

### 4.2 shader 的接口（给「天空」「云」会话对齐）
- 属性：`_MainTex`（上面的四通道卡）、`_Scale`、`_MoonColor × _MoonE`（0.146）、`_SkyColor × _SkyE`（0.89）、`_Lining`（月亮 15° 内软的前向散射边，0.35）、`_Melt`（云顶以上的化开区间）、`_FogDensity`（密度、倍率、月晕、**上限**）、`_SoftFade`（`SOFTPARTICLES_ON` 时的深度淡化，30 m）。
- 每张卡的 `_Mirror`、`_Gain`、`_Alpha` 是实例化属性，由驱动的 property block 写。
- 光照：按卡的视线和月亮的水平夹角在 R（35°）和 G（70°）之间插值；月亮在卡左边时镜像（builder 按 U7b 的眼位算好）。
- 雾：`LanbaiGateFogColour`（第 4 幕的 `LanbaiGateSky.cginc`），`min(1 − e^(−ρd), 上限)`。换幕时把这一行换成 `LanbaiApplyFog` 就行，别的不用动。
- yaw 公告板，朝**两眼中点**；网格裁到云的 alpha 包围盒。

### 4.3 39 张卡
| 组 | 张数 | 卡 | 队列 | 化开（云顶以上） | 雾上限 |
|---|---|---|---|---|---|
| 云塔 `tower` | 9 + 2 | Congestus ×7、Bank ×2；背层 Puff ×2 | 3000 | −30 → +120 m | 0.5 |
| 远云 `far` | 4 | Congestus、Bank | 2990 | −10 → +120 m | 0.70 |
| 地平线云团 `horizon` | 22 | Strato、Puff、Bank（宽 ×0.8–1.3、高 ×0.55–1.65，打破对称） | 2990 | −10 → +120 m | 0.70 |
| 雾卡 `mist` | 2 | Wisp | 3000 | −10 → +50 m | 0.7 |
- 云塔高度按 JSON 的 `height_m`；揭开后 25 s 塌到 0.72，6 s 起下沉 0.75 个塔高，最后 2 秒淡出、关 renderer（JSON `towers`，没改）。
- 云海写深度，卡的下半截被云头挡住 = "从云海里长出来"。
- **云塔的背层（第 10 轮，美术 r3 #5、陌生人 r2 的"平纸板"；`给总控` §7 方案 A、D-15）**：离 U7b 眼睛最近的 2 座（`Tower_Colossus_3`、`Tower_Colossus_2`）各加一张 `<id>_Back`：
  - 沿视线往后挪它距离的 15%，横向错开四分之一宽；
  - 换一个同比例的轮廓（Congestus 后面放 Puff），0.85 倍宽，增益 0.8，透明度 0.9；
  - 塌陷、下沉、淡出的关键帧和前面那张一样，一起塌。
  
  车动起来时两层互相滑开（视差），云顶读成前后两层，不再是一张剪影。只加 2 座是为了 keyart 云卡的透明叠绘守住 ≤ 0.9：加 3 座是 1.03，2 座是 0.89。
- 第 4 轮（美术 r2）：卡的最下 15% 羽化、天光通道（B）在最下 30% 淡掉（不再有一条亮的底边；网格的 uv2.y = 裁过的四边形从下到上 0…1）；远云和地平线云团的雾上限 0.62 → 0.70（+13%）。

---

## 5. 光束和阴影楔 `Lanbai/GateBeam`

### 5.1 光束（2 束，挂裂口根，裂口物体空间）
起点、轴、半宽 46.9 / 40.6、长 3437.5、**越远越宽 ×3.2**、强度 0.35 × (1.0 / 0.6)；横向一个柔光瓣（条带裁到光瓣 4% 处），伤口端短淡入、往外 (1 − z)^1.3 淡出；顺着轴看淡掉、离眼 60–460 m 淡入；颜色 = 裂口套件的光束填色 `(0.0362, 0.0343, 0.0873)`。加法，队列 2998。朝两眼中点。
### 5.2 阴影楔（4 道，挂 GateRoot）
乘法（`dst × (1 − a)`），alpha 0.30–0.42，越远越宽 ×2.5，队列 2991。**只在朝裂口方向 25–40° 以内画**（它们是光雾带里的影子），而且**止于离眼 300 m 之前**（U8 时 900 m 的楔会伸过车身、横在侧窗外）。
整条看不见时（顺轴、全在近处淡出区、在视锥外），顶点阶段把整条折叠成退化三角形，不光栅化。
### 5.3 透明叠绘（`Docs~/fse_clouds.json`，`preview_gate.py --fse`，云海深度剔除后的光栅覆盖）
| 机位 / 时刻 | 云卡 | 光束 | 楔 | 每像素最多层数 |
|---|---|---|---|---|
| U7b 155.10 | 0.59（第 10 轮加背层后 0.62） | 0.09 | 0.42 | 12（0.1% 像素 > 8） |
| U8 166.15 | 0.42 | 0.14 | 0.09 | 10 |
| U8 + 3.5 | 0.34 | 0.12 | 0 | 8 |
| U8 + 7 | 0.29 | 0.06 | 0 | 5 |
| U8 侧窗 | 0.02 | 0.15 | 0 | 1 |
| keyart 154.50 | 0.85（第 10 轮 0.89） | 0.12 | 0.56 | 12 |
线：云卡 ≤ 0.9 ✓，光束 + 楔 ≤ 0.7 ✓（keyart 0.68）。每像素 ≤ 8 层在 U7b / keyart 有 0.1% 的像素超（云塔、远云、地平线云团叠在月亮附近），请在 Unity 里看。

---

## 6. 驱动 `LanbaiGateClouds`（UdonSharp）
- 接口（CONTROL §5）：`LanbaiTick(t)`、`LanbaiActivate(on)`（开关 `root`，不关自己）、`LanbaiWindow()` = 布局 JSON 的 `window` = {U6 − 20, U9 + 2}。
- `Start` → `_Init()`：每张卡写 property block（`_Mirror`、`_Gain`、`_Alpha`）。不写全局量（光雾带归门的总驱动，D-22）。`LanbaiTick` 里懒初始化调的也是 `_Init()`（同一帧被激活又被调时 `Start` 还没跑；不把事件方法当普通方法调，技术 r2 #7）。
- 云塔：`localScale.y × sag`、`localPosition.y + sink`、`_Alpha = opacity × alpha`，alpha 0 时关 renderer。
- 用到的 Udon API：`MaterialPropertyBlock`、`Renderer.SetPropertyBlock`、`VRCShader.PropertyToID / SetGlobalVector`。没有 `GetPropertyBlock`。

---

## 7. 远潮（gate_test §2.2 第 10 条）
`Lanbai_TentacleTide_v2.shader` 是 **v2.3**：雾色 = `LanbaiGateFogColour`（和触手一样，含背带、地平线下去饱和、月晕）。新默认值 `_HazeNear (0.1085, 0.1130, 0.1641)`、`_HazeFar (0.0436, 0.0504, 0.0726)`、`_BandEl (6, 22, 2)`。**已有的材质 `M_TentacleTide_A / B` 保留旧值**：请填上这三项（或右键属性 Reset）。

---

## 8. 请截图 / 实测（推到 `FromLocal/gate_clouds_test/`）
和 10-08 同一个测试场景、同样的 HDR 截图方法：
1. 用 `LB_GateTest.Shoot` 拍 keyart t = 154.50、U7 t = 155.10、U8 前方 t = 169.65、U8 侧窗 t = 166.45、后窗 t = 177.55。后窗那张：把天空盒、云海、云卡、触手材质的 `_BackBand` 都改成 1.25，拍完改回 0.55。每张配 `Docs~/compare_*.png` 的定稿，量 `gate_metrics.py` 那几项（或总工程师的 `Engineering/render_harness/lbh_grade.py --png`）。
2. **帧时间**：按 §3.4 的方法（`LB_GateTest.Perf`，U7 / U8 前方，有云 / 没云：没云 = 关掉 `GateRoot/GateClouds` 和 `Tear_Root/GateBeam_Shaft_00/01`）；GPU Profiler / RenderDoc 最贵的几项。
3. Console 原样（包括 UdonSharp 的）。
4. **Play 模式 + 头显**（门的总驱动已经有了：`Gate/README_GateDriver.md`；测试场景用 **蓝白/Gate/Build Driver + Test Clock**，进 Play 后云海按 v_g 流动）：云海滚动 10 秒看银边闪不闪；闭左眼、闭右眼各看一遍；车道读起来自然不自然。
5. Frame Debugger 里确认 `UpdateDepthTexture` 画了云海（ShadowCaster pass）。
6. **（云端已做，第 10 轮）闪烁和银边爬行**：U7 机位 155.1 → 157.1 s，60 fps，1280 × 720，120 帧 PNG，参照渲染。
   - **flashcheck**：一般闪烁 0、红闪 0，WCAG 2.3.1 PASS，蓝白闪烁规则 PASS，亮度爬升律 PASS（任意 1 s 最大升 0.04 EV，APL 42）。
   - flashcheck 按 4.4° 的块量，看不到 1–2 px 的银边在滚动里闪。所以另用 `measure_crawl.py` 逐像素量：相邻帧差 > 12 码，并且 10 帧里正负翻转 ≥ 2 次，就算"爬"。
     - 第 10 轮前，云海区里 0.19% 的像素在爬，集中在月光路和裂口脚下远处很细的银边上；
     - 亚像素淡化 `_Skin2.y` 从 3 降到 1.5 以后是 0.147%（−23%）。银边 p95 / p99.5 从 135 / 155 变成 124 / 149，仍在美术 r2 的目标里。
     - 图：`Docs~/crawl_map_U7_720p.png`，红色 = 在爬的像素。剩下的是远处一个像素宽的轮廓，头显里请照 §8 第 4 条确认。

---

## 9. 源文件（都能重跑）
| 文件 | 做什么 |
|---|---|
| `Source/deck_tiles.py` | 烘云海的两张贴图（numpy） |
| `Source/deck_ref.py` | 云海 shader 的**逐行 numpy 移植**（`render_deck`），任一机位渲、S4 调色、打印平均步数；改 shader 的数就改这里的 `DEFAULTS` |
| `Source/gate_cards.py` | 云卡 v2（Blender 5.1 bpy；3 个光组一次渲完，用降噪后的 Combined 按光组比例拆通道） |
| `Source/gate_clouds_layout.py` | 写 `GateClouds_Layout.json` |
| `Source/preview_gate.py` | 整帧预览（云海 + 卡 + 光束；`--over` 贴回 Unity 截图的触手；`--fse` 量透明叠绘） |
| `Source/measure_comb.py` | 美术审片的"轮廓梳齿"量法 |
| `Source/measure_rims.py` | 第 4 轮的量法：云海区（画面下 45%）p5 / p50 / p95 / p99.5，边光像素（比 15 px 中值亮 12 码以上）的 p95 / p99.5 |
| `Tools~/slang_check.py`、`Tools~/cs_check/check_cs.sh` | shader / C# 检查 |

---

## 10. 评审记录与分歧
四份独立评审（美术、技术、VR 与性能、640 px 陌生人；`Docs~/reviews/`）+ 总工程师 + 美术审片预审。第 1 轮全部"不通过"，第 2、3 轮的改动见 `Docs~/iterations/README.md` 和 `给总控.md`。**与评审的分歧**（照 CONTROL §0 写明理由）：
1. **近处云头（美术 r1 #3 "近景云团大、占画宽 1/3"）× VR 铁律**：定稿里车正前下方的大云头离眼只有 10–35 m，以 59 m/s 掠过，违反圣经 §1.8。我们守铁律：车行进路径 ±56 m 的车道里云头按比例压到眼下 57 m。所以 keyart / U7 画面中下方的近景云头比定稿矮、小。车道外照常。
2. **楔外的银边（美术 r1 #2 要 ≤ 30%）**：第 3 轮用 45%，第 4 轮照美术 r2 改到 16%（× 0.35），配合每个云头 0.4–1.6 的起伏，右半边仍有零星的边，不再是一片死灰。**这一条不再有分歧。**
3. **性能目标（VR r1 ≤ 1 ms、总工程师 1–1.5 ms）**：估算 1.5–2.5 ms，见 §3.4 和 `给总控.md`，等实测和总导演决定；我们没有自己降画质。
4. **美术审片 P1 建议"跨过云顶的比例软混合"**：用的是"最贴近云面的点离撞点多远"这个判据（越过了轮廓才计入），配合自适应步长和线性求交；量出的梳齿比例 4.7%（审片目标 ≤ 8%，第 1 轮 53%，定稿 1%）。
5. **云谷 p5 ≈ 20（美术 r2）**：天光 × 0.7、槽里少混雾之后，U7 的 p5 = 19，keyart 26、U8 前方 23。keyart / U8 前方压不到 20，原因是 0.5–1 km 处的大气雾本身就有 ~0.03 线性（≈ 26 码）；把雾减 30% 只降 2 码，却丢掉纵深，所以没减。要更暗只能动雾，请美术定。
6. **轮廓台阶（美术 r2 BLOCKER / r3 #1–2，r3 不接受上一版的说法）**：这一轮又改了三处：被照亮的云头不再有黑描边（越过云顶的那部分像素也算脚下的光）；撞上前已经回升了一部分的视线按比例保留银边（方头碎块）；U8 前方的白色光池收到 120 m。剩下的是低机位（U7 眼高 60 m）掠射时近水平轮廓的像素锯齿，在 1:1 裁图里可以看到一阶一阶的水平段。要再软只能多采样（每像素两条视线，代价约 ×1.6），没有做，留给实测后总导演定。
7. **U8 侧窗 −0.5 EV（美术 r2）**：没改。侧窗的云海已经是五个机位里最暗、最软的（云海 p50 30，边光 p99.5 只有 67 码；keyart 157）。再降 0.5 EV 会读成一片黑；侧窗竖条纹在 1:1 的 deck-only 里没找到（`Docs~/r4_crops/U8side_troughs.png`）。如果审片看的是带卡的整帧，请指出位置。
8. **U8 前方 p50 ≤ 30 / rear p5 ≤ 15（美术 r3 #1、#4）的参照**：这两个目标是拿定稿整帧量的，定稿 `U8_forward` 和 `rear_window` 都是**从车厢里往外看**，下 40% 有一大块黑的车厢内饰和窗框。只量定稿窗外的云：U8 前方脚边 p50 63、p90 137；rear 两条触手之间的云 p5 59 / p50 69 / p95 89、y 300 的天 9 码（我们 8 码）。所以 U8 前方我们按"不烧白"改到 p50 36 / p95 96；rear 的云海（p5 35、p50 47）已经比定稿窗外的云暗，没有再压。rear 读起来空，是因为预览里没有触手（这个机位没有 Unity 截图可贴），定稿的层次来自触手。
9. **云塔视差卡（美术 r3 #5、陌生人 r2）**：这一窗口没做（总导演要求只收尾）。`给总控.md` §7 的方案 A（前排 3 座各加一张错开的卡，+0.2–0.3 FSE）等合并后做。
10. **终审（美术、技术都是有条件通过，没有 BLOCKER）留到合并后的几项**，`Docs~/reviews/final.md` 有全文要点：
   - 美术 #1：keyart 裂口脚下的光（中心 p95 105，左边月光路 132；目标中心 ≥ 170、比值 ≥ 1.8）。试过雾里的散射光（只到 143），没有放进去；等第一张 Unity 截图复量。
   - 美术 #2：key / U7 还有几处方头碎块（key x 885–904 y 1040–1057 等）。
   - 美术 #3：U8 前方光池里云团要有暗心（p5 ≤ 25），等带裂口的 Unity 截图复核。
   - 美术 #4、#5：rear 雾带、U8 侧窗质感偏硬。
   - 技术 #1：放开的步长加上限（`min(dFree, 0.15 t)`），约 0.03–0.07% 像素的击中点会远 5% 以上。
   - 技术 #4：`Hash3` 还是 `sin` 哈希。不同 GPU 抖动值不同，但两只眼一致。等实测时看有没有规则纹理，有再换整数哈希。
   - 技术 #5：179.55 写死。换成从 layout 的 U9 推，并给 `towerRenderers[i]` 判空。

---

## 11. 已知问题 / 还弱的地方（诚实版）
1. **云海的质感**：读成"背光的积云海 + 月光路"，但还不如定稿的"棉团"那么蓬松：近处云头的体积层次（团里有团）不够，部分中景仍有"沙丘 / 等高线"的感觉。高度场只能表示"一层"云面，表示不了悬垂和团块下面的空隙。
2. **性能**未实测（§3.4）。
3. **车道**：车正下方一条压低的云道，在前方视角里可能看得出是一条"路"（月光路在它左边）。如果读起来别扭，可以把 `_Comfort.z/w` 收窄到 (40, 100)（仍满足 56 m），或者把车道里的云海做得更平、更暗。
4. 每像素 > 8 层透明在 U7b / keyart 有 0.1% 像素。
5. 云卡只有两个月光角度（35° / 70°），月亮几乎正对 / 正背的卡是外推的。
6. 驱动只管云；门内会话要的 U9 交界四件事（GateRoot 减速、`_Udon_TearHide`、门户裁剪的 renderer 开关、触手卷回）属于**门的总驱动**，这一版只做了 shader 一侧的 `_Udon_InsidePortal` 裁剪（`给总控.md`）。
7. 预览里的触手和裂口是 10-08 的 Unity 截图贴回去的，接缝（裂口周围的椭圆）不是云的问题。
8. 陌生人 r2："云塔像平纸板、和触手相像"——第 4 轮只做了底边羽化和远处加雾；云塔本身仍是一张公告板（没有视差）。要更立体需要多层卡或体积，留作下一轮的选项（`给总控.md`）。
