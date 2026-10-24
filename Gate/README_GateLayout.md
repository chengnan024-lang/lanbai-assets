# 触手之门 · GateLayout v2 文件（布局第 6 版，第 8 轮 = refine round 4 + 第 9 次运行的补丁）· 给 Unity 一侧的说明

写的人：云端美术组（门）。对象：小楠电脑上 Unity 2022.3 那一侧的会话。
**本目录里的 C# / shader 都没有在 Unity 里编译过。** shader 只用 slang 做过语法 / 类型检查（§7）。

用户的要求：「门被打断就要重搭 那就先只搭门 把门先做好」、「很好看！按照你想的来！还是不要节省不要将就啦！」。这一轮仍然只做门。
上一轮（第 7 轮）的全部交付物在 `gate/_r4/`（含那一版的 README、JSON / FBX、`GateArms_v3.fbx`、`GateMultitude_v1.fbx`、定稿 PNG + ID 渲染 `_r4/final/`）；
定稿也在 `final/_superseded/r5_final/`。文件名仍叫 `GateLayout_v2.*`（任务约定的名字），内容是第 6 版布局，JSON 的 `about` 写明了。

## 第 8 轮（refine round 4，2026-10-02）——先读这一节

依据（优先级从高到低）：美术总监第 3 轮的六条（`SPEC.md` ★★★★★：裂口内部 + 布、臂的光 / 盘绕、只有一个最亮点、车里的空白牌、后窗闸门、U8a 干净的天窗）+ 两份 r4 评审（`critique_awe_r4.md`、`critique_tech_r4.md`，都判“不通过”）。
**前后对比图**：`final/compare_r4_tear.png`、`final/compare_r4_light.png`、`final/compare_r4_multitude.png`（左 = 第 7 轮，右 = 这一版，图下是 `accept_r6.py` 量出的数）。

| 评审的阻断项 | 这一版 |
|---|---|
| 美术 B1 / 技术 B1：伤口是“云做的底座上的蜡烛火焰”；U8 前方的白停在一条尺子一样的直线上 | 套件 **v6**：透镜下半段**收尖**、白顺着云海里的一道 **V 口**流进去（`Tear_FootSkyline`：两片背光的云唇，V 尖在云面上 6 m，下面是连续的云）；5 张底座卡删掉；短的峡谷底 = 白自己的雾；Unity 里透镜脚的 alpha 在深而参差的坡上切（§2.2、`README_Tear.md` v6） |
| 美术 B1.3–B1.9：褶看不见、翻布是碎片、线是满宽的圈、支线是叶子、光晕是紫墙 | 每个抓点 3 道下垂的折痕；右边一片大翻布朝车剥开、左边一片小的被左手盘住；断纱；渐细的支线；倾斜的薄纱 + 远唇；光晕 `#7A7B9C` 以热核为中心、随距离淡出 |
| 美术 B2：群臂是一片芦苇，还盖住了云塔 | **36 条，5 簇**，3 档雾、近两档有月轮廓、主臂 3:1、真的卷、12 个姿态（含镜像）；左右的云塔回来了（§4.5） |
| 美术 B3 / 技术 M1：伤口什么也没照亮；Engel 上第二个最亮点 | 伤口高光按距离缩放 + 上限；**白前面的臂是剪影**（`OverWhite()` + 0.9 px 包边）；云头上的**光路**；4 道阴影楔；右近处的云有了起伏 |
| 技术 B2：鞭梢上等距的环 / 珠 | `thinK`：细的部分不再用主贴图（TentacleSway v2.7 + 预览材质） |
| 技术 BT-3：天空盒和雾色是两套公式 | **`LanbaiGateSky.cginc`**：天空盒 `Lanbai_GateAirSky` v3 与 TentacleSway v2.7 共用一份（§6、§7） |
| 技术 BT-4：§2.1 的 MPB 片段会抹掉每实例的相位和雾档 | §2.1 重写（每个 LOD renderer 自己的块、群臂一个全局 `_Udon_MultReveal`、只在穿过 0 时开关） |
| 技术 M4 / M5：U8 的光晕墙；淡到 0 的部件仍在光栅化 | 光晕距离淡出（U8 0.47、U8 + 3.5 起为 0）；Tear v6 预深度 pass 顶点阶段裁掉；`renderer_off_at_zero`；光路四边形按距离缩放；透明预算 **3.77 / 3.43 / 3.53 FSE**（§9） |
| AD 5 / 美术 M4 / 技术 M3：后窗是衣帽钩 + 灰鬼 | 5 根各不相同的手指（+ 一支分叉）、S 弯加粗的拱、albedo × 0.5、雾 0.35、朝月 1.5 px 冷边、银色的后地平线、柔化的正面受光云海、占位窗框 |
| AD 6 / 美术 M3 / 技术 M7：U8a 的尘、纸、没被照亮的井 | U8 + 8.0；没有尘；井被照亮、顶棚一圈光；翻布的一角是暗布 + 亮撕边 |

**没有改的**（AD 说要保留）：不对称构图、云海、云塔、根部化开、横跨白色的鞭梢（X）、月蚀时机、导出 / 验收管线。
**对评审不同意的地方**写在 §11（翻布每侧一片大的、≥ 10 道放射褶、近臂身体 ≥ 250 px、辉光后的剪影 p50 ≤ 15）。验收数在 §10，诚实的弱点在 §13。

### 第 8 轮补丁（第 9 次运行，2026-10-02）——定稿前自己看出来的六处
第 8 轮定稿渲出来后，我在 1:1 下看，又改了六处，然后重渲主视觉、U7、U8 前方、后窗（其余帧是在改动之后渲的，已经包含）：
1. **撕裂支线读成一根白角**（主视觉顶部右唇旁）：`make_rip` **v7**——顺经纬的台阶、三处还连着的收窄 + 深色横纱（一根断了）、唇上短纤维；同一张贴图、同一个材质（`README_Tear.md` v6.1）。
2. **U8 前方的脚还有 40 px 的尺子直线**（`accept_r6` 量的，第 676 行）：那是透镜碰到**平的云顶面**的交线，从 ~120 m 高往下看时露在 V 口的尖下面。新部件 **`Tear_FootSkylineIn`**：透镜前 ~8 m 一排 3–8 m 的低云头（背光边），白收在云头上（§2.2、JSON `tear.foot_skyline_inner`）。
3. **群臂的月轮廓其实被远处的轮廓衰减吃光了**：轮廓阶梯 `exp(−ρd) × (900/d)^1.2` 在 3–5 km 只剩 × 0.01–0.02。TentacleSway **v2.7c** 加 `_RimLadderFloor`（阶梯的下限）：A / B 档 0.5 / 0.3，`_RimGain` 0.40 → **2.4**（JSON `multitude.tiers`、每个实例的 `material`）。C 档不变。
4. **群臂的主臂在渲染里用的是 LOD2**（8 × 20 段，主视觉里能看到 25 m 一段的折角）。渲染现在按 §9 的 LODGroup 屏幕高度选 LOD（主臂 = LOD0），与 Unity 一致。
5. **后窗垂下的手指读成獠牙**：尖端改成画面平面里的 S 鞭梢 / 半卷 / 卷 / 分叉，各不相同（§4.7）。
6. **Engel 顶边的 L\* 100 亮条还在**（第 8 轮的 `_StreakKeep` 没打中）：是掠射角的月光高光，远距缩放 0.15 后仍有 10（线性）。Engel 材质 `_ReflectionScaleFar` → **0.01**（§5、§11）。
试过但**没用**：`Pillar_R` 的“湿亮线反射身后的云原”（`wet_env_pillar`，`wip/r9/pil_w*.png`）——只在右下边缘出几块斑点，像雪；物理上背光柱子朝向我们的一面照出的是黑的天。AD 第 3 条要的是“近处的柱子近黑、有边光”，所以保持。

---

## 上一轮（第 7 轮，refine round 3）——历史


依据：美术总监的六条（`SPEC.md` “★★★★★ AD NOTES ROUND 3”）+ 两份 r3 评审（`critique_awe_r3.md`、`critique_tech_r3.md`，都判“不通过”）。
**前后对比图**：`final/compare_r3_tear.png`、`final/compare_r3_arms.png`、`final/compare_r3_grade.png`（左 = 第 6 轮，右 = 这一版，图下有量出的数）。

| AD | 说的 | 这一版 |
|---|---|---|
| 1 | 裂口是一张贴纸：平的白 + 一圈霓虹紫描边；布像纸 | 套件 **v5**（`deliver/Tear/README_Tear.md` v5 一节）：白里有**纵深**（最宽一行偏下偏右的**热核**，往两端冷下去到 ~70%）、4 片不同形状的**薄纱**（各有亮面 / 平台 / 暗侧）、颜色暖 → 冷等亮度过渡；**唇不再画辉光**：一条断续的纤维带（1.6% W）、只在被拉薄的地方透光（`#C9C2EE → #3E3C66`）、6 道**张力褶**（暗的月牙形，从抓点出发、伸出唇外）、8 簇下垂的**散线**、3 根**被背光照透的横跨纱线**（`#BDB7D6`，带垂度与波）+ 1 根断的；翻布是**染过的深布**（外面 L\* 5–8、只在撕边 1.2–6 m 透出伤口光 `#8F86D0`），**下垂**（`FLAP_SAG 0.16`），alpha 羽化；脚**化成被照亮的雾**（`_FootMist`）+ 5 张**背光的云团**（`Tear_FootCloud_*`）+ 云海上的脚部光瓣（`_FootGlow 2.2`）。 |
| 2 | 臂读成扁的带子；抓布像爪 | 伤口成了**主光**：渲染里是两盏与白同尺寸的椭圆面光（只漫反射）+ 解析的管状光高光；Unity 里是 TentacleSway **v2.6** 的**线光源**（`_Udon_TearFoot → _Udon_TearTop`：wrap 漫反射 + Karis 代表点高光）+ **屏幕空间伤口轮廓** `_RimWound`（朝伤口那一侧的轮廓，2.5 px）+ 月轮廓 / 透光改用 `_Udon_MoonDir`。手：左手 = 一条伸向伤口的斜线（在月亮下面），右手 = 一道**卷起的浪**（拱到 +14°）；抓布的手指末端是 **1.25 圈的盘绕**（`arms4.coil_end`），不再是爪；Engel 盘住右唇 66% 高处。两根鞭梢在白前**交叉成 X**。 |
| 3 | 发灰：主视觉 APL ~32–36，上面是虚空，云有银边，只有一个最亮点 | 光雾带仰角 `BAND_EL (6, 22, 2)`、增益 0.80（+20° 以上是夜）；云海朝月一侧保留起伏 + 月光路（±7°）、远处 2–4 km 加 gamma；云塔朝月的银边 + 底部雾；光束低而斜（终点仰角 7.5° / 9°）、强度 0.35；月盘 × 0.6。主视觉 **APL 35.8、luma < 12 24%、上 25% L\* p90 4.4**、最亮 2000 px 全在伤口里（§10）。 |
| 4 | 目的地牌从车里读成「白蓝」 | **车里看是空白的**：灯箱背面 `#1A1E28` 的均匀微光（亚麻纹 ≤ 2 L\*），字只在车外那一面（§0、§8.5）。 |
| 5 | 后窗：蟹腿 + 一个像镜头污点的环 | **环（月之光环卡）删掉**；后窗组换成 2 道**巨大的拱**（`Rear_ArchA/B`，1.4 km 长、根半径 52–62 m）+ 一只**四指的手**（`Rear_Hand0…3`，2.0–2.2 km、根半径 90–110 m，像闸门一样合在路上方）；眼位贴在后窗玻璃上（§3）。 |
| 6 | U8a：一个让人糊涂的灰盒 | **U8a 改到 U8 + 7**（伤口已在头顶）：干净的车顶（暗顶棚 + 一个天窗框），**天窗里整块都是伤口的白**，光从天窗落进车里（光柱 + 尘）；天窗挪到主座位的正上前方（`gate_bus.SKY_C`，车壳仍是占位）。 |

**两份评审的其余各条**（逐条见 §11）：
- **技术 BT-1**（世界空间噪声随 GateRoot 爬动）：所有噪声改在**云海坐标**里取样：`worldPos − _Udon_GateOrigin.xyz`（新全局，= GateRoot 本帧的世界位置）。TentacleSway 的根部化开 / 云顶淡出、Tear 的脚部淡出都改了。
- **技术 BT-2**（Tear 的颜色属性被二次伽马）：`Lanbai_Tear.shader` v5 的**所有颜色属性改成 `Vector`**，填的就是线性值（§7.3）。
- **美术 B4 / 技术 M6**（“成百条黑色的巨臂”不存在）：**群臂 `Mult_000…149`**：150 条真正的 3D 臂（6 个规范姿态 MU0–MU5、GPU 实例化、新文件 `GateMultitude_v1.fbx`），在 2.6–5.6 km、|方位| 14–58° 排成 7 道**浪**，向伤口倾，三档雾（实例化 `_FogCapI`），U6 + 13 起冠从雾里出来、一边升起（每条按**实测**自身角速度 ≤ 0.95°/s 定时长），U7b 时站满、U8 前退回雾里。浪涌环（22 条）退役；远潮仍在但更早退。
- **技术 M1**：巨像 1 预先沉好，U6 + 10 冠正好在云顶，按自身角速度 ≤ 0.34°/s 升起、U8 前停（143.8 → 165.8）。**实测露出的高度比评审要的低**：U6 + 13 只有 22 m、U7 72 m、U7b 140 m、U8 276 m（评审：诗句结束时 70–80 m、U7b 300 m）——它是斜着出云的，尖端的角速度先到 0.3°/s 的上限；要更快就得放宽圣经的 0.5°/s（我们没有放宽，§13）。
- **技术 M2**：透明预算重算（近平面裁剪、CloudGlow 两个 pass 都算、脚部云团）后 U8 3.83 / U8 + 3.5 3.74 / U8 + 7 3.90 FSE（§9）。
- **技术 M3**：门柱不再“从空气里出现”：慢的雾中显现 U6 + 13.5 → U7b − 1（6.6 s），云塔不再 alpha 淡出而是**下沉**；后窗组在车后 |方位| ≥ 138° 才开始显现（§4.1）。
- **技术 M4 / 美术 M6**（背景巨物是鬼影）：两份评审方向相反（技术要更亮做阶梯，美术要更暗不像鬼）。我按美术：背景雾 1.0 → **0.45**（光雾带 − 8 左右）；远近的阶梯改由群臂的三档雾来给（§11）。
- **技术 M7**：重名 shader：全部旧版都是 `.shader.txt` 或在 `~` 文件夹里；§0 写明了**只拷哪些文件夹**。
- **美术 M1**（Engel 是灰梁）：雾 0.80 → 0.40（身体 L\* 8–11）、盘住右唇；**美术 M5**（U8 前方两根鞭梢连成 W）：交叉成 X（`CROSS`）。
- **技术 m8**：新增一张近处臂的定稿 `final/U8_near.png`（Near_1 离眼 ~16 m 从右侧窗掠过）。

**没有改的**（AD 说要保留）：不对称构图、云海、云塔、根部化开、横跨白色的鞭梢、月蚀时机、导出 / 验收管线。

---

## 0. 交付清单（都在 `gate/`）

**拷进 Unity 的只有这些**（其余文件夹 `_r1 _r2 _r2final _r3 _r4 _stray _v0 wip critique_*` 是存档 / 工作区，**不要拷**；它们里面的旧 shader 都已改名 `.shader.txt` 或在 `~` 文件夹里，误拷了也不会被编译）：
`GateLayout_v2.json`、`GateLayout_v2.fbx`、**`GateArms_v4.fbx`**、**`GateMultitude_v2.fbx`**、`TentacleTide_v2.fbx`、`Shaders/`（3 个 `.shader` + `LanbaiGateSky.cginc`）、`Textures/`（`_retired~` 会被 Unity 忽略），以及 `../deliver/Tear/`（套件 **v6**）。
`GateArms_v3.fbx`、`GateMultitude_v1.fbx` 已挪到 `_r4/`（被 v4 / v2 取代）。

| 文件 | 是什么 |
|---|---|
| `GateLayout_v2.json` | **唯一的数据源。** 约定、shader 版本（`shaders`）、GateRoot 时间曲线、激活时间、**每帧全局量（第 8 轮多了 `_Udon_MultReveal`、光晕淡出与光路缩放的写法）**、9 个机位、灯、光雾带（含背带 65–120°）、雾（含“白前面的臂”）、**64 个触手实例**（28 条单独的臂 + 36 条群臂；终态 / U7b 位姿、缩放、相位、每实例完整材质参数（v2.7）、`reveal`、每段动画）、`multitude` 块（5 簇、3 档、显现分组、摆动）、360 片远潮、2 束光、**4 道阴影楔**、裂口（挂法、抓点、**淡出关键帧 + renderer_off_at_zero**、**脚前云头 `foot_skyline`**、**光路 `light_lane`**、峡谷）、云（光池、根部化开、云塔下沉、雾卡、地平线云团、银边、第 8 轮的云海调整）、近处臂的尾流、月蚀表、天窗光斑。 |
| `GateLayout_v2.fbx` | 同一套摆放的空物体：`GateRoot` → 每实例一个空物体（终态）、`Tear_Root`、`TideRoot`，和独立的 `NearRoot_busRelative`。`verify_layout_fbx.py` 按 Unity 的读法回读（§10.4）。 |
| `GateArms_v4.fbx` | 28 条单独的臂（含 `Rear_Hand4`、分叉 `Rear_Hand2F`、S 弯的 `Pillar_R` 与后窗拱）：每个实例一个空物体 `<id>`，下面 `<id>_LOD0/1/2`（导入器自动建 LODGroup）。UV：`UVMap`、`UVSway`（TEXCOORD1：t, phase）、`UVRadius`（TEXCOORD2.x，v2.7 的 `_ThinK` 也读它）；顶点色 `Col`。 |
| `GateMultitude_v2.fbx` | 群臂的 **12 个姿态** `MU0…MU5` + 镜像 `MU0m…MU5m`，每个一个空物体 + `_LOD0/1/2`，根在原点。36 个实例按雾档用 3 个材质（§4.5、§5）。 |
| `TentacleTide_v2.fbx` | 360 片远潮（未变），材质 `Textures/TentacleTide_v3_Atlas_A/B.png`。 |
| `Shaders/LanbaiGateSky.cginc` | **新**：天空 / 光雾带 / 月晕 / 伤口空气的唯一定义（§6、§7.0）。 |
| `Shaders/Lanbai_TentacleSway.shader` | 触手 shader **v2.7c**（§7.1；v2.7c 只加了 `_RimLadderFloor`）。 |
| `Shaders/Lanbai_GateAirSky.shader` | 天空盒 **v3**（§7.1b；从 `deliver/Tentacles` 挪到这里，v2 在 `deliver/Tentacles/_superseded~/`）。 |
| `Shaders/Lanbai_TentacleTide_v2.shader` | 远潮 shader v2.2（未改）。 |
| `Textures/Bus_DestinationBlind_1024x256.png` | 目的地牌：R = 字的透光（只给车外那一面），G = 亚麻纹。车里那一面：`emission = #1A1E28 × (0.96 + 0.04 G)`，没有字（§8.5）。 |
| `Textures/Tear_CloudLanes_1024.png`、`Textures/Occlusion/*`、`Textures/TentacleTide_v3_Atlas_*` | 光池阴影道；自定义臂的褶皱遮罩（`.png.<hash>` 是渲染的缓存标记，可忽略）；远潮图集 v3。**退役的**（浪涌环 `T_Gate_SG*`、根部袖子 `Gate_RootSleeve_512.png`）在 `Textures/_retired~/`（技术 r4 m11）。 |
| `../deliver/Tear/` | 裂口套件 **v6.1**（`README_Tear.md` 开头的 v6.1 与 v6 两节；FBX 已重建并核对；新部件 `Tear_FootSkyline`、`Tear_FootSkylineIn`（v6.1）、`Tear_LightLane`，贴图 `Tear_FootSkyline_1024x160.png`、`Tear_FootSkylineIn_512x160.png`；撕裂支线贴图 v7）。 |
| `final/keyart_239.png` | 给用户的 2.39:1 主视觉（2560×1072，U7b − 0.6 s，无车壳）。 |
| `final/U6_approach.png`、`U7_engelein.png`、`U8_side.png`、`U8_near.png`、`U8_forward.png`、`U8a_ach_nein.png`、`U8b_spot.png`、`rear_window.png` | 1920×1080，128 spp + OIDN，带车壳（占位）。 |
| `final/compare_r4_tear.png`、`compare_r4_light.png`、`compare_r4_multitude.png` | **美术 r4 要的前后对比**（第 7 轮 → 现在，图下是 `accept_r6.py` 量出的数）。 |
| `final/compare_r9_patch.png` | 第 9 次运行补丁的前后对比（第 8 轮定稿 → 现在）：撕裂支线、Engel 亮条、群臂、U8 前方的脚、后窗手指。 |
| `final/contact_sheet.png`、`final/*_metrics.json`、`final/acceptance_r5.json`、**`final/acceptance_r6.json`**、`final/fse_U8.json`、`final/motion_check.json`、`final/moon_coverage.json` | 一页总览；验收数（§10；`accept_r6.py` = 两份 r4 评审要的“完形”检查）；透明预算；运动检查；月蚀表。 |
| `gate_scene.py` | 整个门的 Blender 场景。`python3 gate_scene.py render <U6|U7|U8fwd|U8a|U8b|U8side|U8near|rear|key> W H SPP out [--set=k:v,...]`、`ids …`。 |
| `gate_layout.py` + `arms4.py` | 时间曲线、全部实例的摆放与动画；`arms4.py` = 自定义中心线臂（第 8 轮：`rad4` 的 swell、`rad_key`）。`gate_scene_shots.py` = 机位表。 |
| `gate_export.py`、`verify_layout_fbx.py`、`gate_metrics.py`、`accept_r5.py`、**`accept_r6.py`**、**`compare_r4.py`**、`motion_check.py`、`gate_fse.py`、`final_r6.sh` | 导出、FBX 回读、验收数、前后对比、运动、透明预算、定稿脚本（可续跑）。 |
| `cloud_deck.py`、`gate_bus.py` | 渲染用的云海冒充体与通用车壳。**不是交付物。** |
| `PROGRESS.md` | 工作日志。 |

---

## 1. 坐标约定（先看这个）

- Unity 世界：米，Y 上，**车固定在原点、车头朝 +Z，世界往车后移动**（与 `gate_context.md` 相同）。
- **GateRoot 本地坐标**（门里一切都是它的子物体，除了近处 3 条，§4.6）：
  - 原点 = **进入点**：U9 时车的原点穿过裂口平面的那一点，在裂口轴线上、**云顶以上 150 m**。
  - x 右（从车里看）、y 上、z 向前。**裂口面朝 −Z（朝车）。** 云顶在 GateRoot 本地 **y = −150**。
  - 设计坐标 CF（裂口脚为原点，x 右，y 远离车，z 上，云顶 z = 0）→ GateRoot 本地 = `(cx, cz − 150, cy)`。
- 每个实例：实例化 FBX 里的 `<id>`（或群臂的 `MU<k>`），挂在 GateRoot 下，`localPosition = position`、`localRotation = rotation_xyzw`、`localScale = scale`。
- **云海坐标**（第 7 轮，BT-1）：所有“贴在云上”的噪声（根部化开、云顶淡出、裂口脚的淡出）都在 `worldPos − GateRoot.position` 里取样，噪声跟云一起走，不在臂根上爬。

---

## 2. GateRoot 怎么随时间走（timeline 秒，t = 0 出发）

乐句（`cues.md` 实测）：U6 133.80 · U7 150.30 · U7b 155.10 · U8 166.15 · U8b 167.90 · U8c 171.40 · U9 179.55。

```
v_g      = 2700 / (U9 − U6) = 59.0164 m/s          （恒速）
h_bus(t) = 40                                       U6 − 20 ≤ t ≤ U6
         = 40 + 20·ss((t − U6) / (160.50 − U6))     U6 … 160.50
         = 60 + 90·ss((t − 160.50) / (U9 − 160.50)) 160.50 … U9      （峰值竖直加速度 1.49 m/s²）
GateRoot.position(t) = ( 0,  150 − h_bus(t),  59.0164 · (179.55 − t) )
GateRoot.rotation = 0，scale = 1
```

- GateRoot.z：U6 2.70 km、U7 1.73 km、U7b 1.44 km、U8 0.79 km、U9 0。云顶在世界 y = −h_bus(t)。
- `GateRoot.SetActive(true)` 在 **t = U6 − 20 = 113.80**（车还在白云遮挡里）。巨物都已站好，由 `_Reveal = 0` 与云塔藏住。
- `ReferenceCamera` 的 **far plane ≥ 14 000 m**（群臂最远 5.6 km、远潮 13 km）。

### 2.1 每帧要写的全局量（Udon，示意，**未编译**）

```csharp
float t = Timeline();
float ss(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }
float hBus = t <= U6 ? 40f : (t < 160.50f ? 40f + 20f * ss((t - U6) / (160.50f - U6))
                                         : 60f + 90f * ss((t - 160.50f) / (U9 - 160.50f)));
Vector3 gate = new Vector3(0f, 150f - hBus, 59.0164f * (U9 - t));
gateRoot.localPosition = gate;
float H = TearH(t);                          // JSON timeline.tear_H_knots，单调 PCHIP
float S = H / 1000f;
tearRoot.localScale = Vector3.one * S;
float open = 0.18f + 0.12f * tearOpen;      // 白的宽度占 H 的比例；tearOpen = _Udon_TearOpen（0 → 1）
VRCShader.SetGlobalVector(_idCloudTop,   new Vector4(-hBus, 0f, 0f, 1f));
VRCShader.SetGlobalVector(_idTearPos,    new Vector4(0f, -hBus + 0.4f * H, gate.z, 1f));
VRCShader.SetGlobalVector(_idTearH,      new Vector4(H, 0f, 0f, 1f));
VRCShader.SetGlobalVector(_idMoonDir,    new Vector4(-0.2059f, 0.1392f, 0.9686f, 1f));
VRCShader.SetGlobalFloat(_idGateTime, t);
VRCShader.SetGlobalVector(_idGateOrigin, new Vector4(gate.x, gate.y, gate.z, 1f));            // 噪声的云海坐标
Vector3 foot = tearRoot.TransformPoint(TearFootOS);   // JSON timeline.globals_every_frame._Udon_TearFoot
Vector3 top  = tearRoot.TransformPoint(TearTopOS);    // 同上 _Udon_TearTop
VRCShader.SetGlobalVector(_idTearFoot, new Vector4(foot.x, foot.y, foot.z, 0.5f * open * 1000f * S));
VRCShader.SetGlobalVector(_idTearTop,  new Vector4(top.x,  top.y,  top.z,  1f));
// ---- 第 8 轮新增 ----
// (1) 群臂：一个全局量代替 150 次 MPB 写入（技术 r4 BT-4）。两组曲线在 JSON multitude.reveal_groups
float g0 = KeyAt(multGroup0, t), g1 = KeyAt(multGroup1, t);
VRCShader.SetGlobalVector(_idMultReveal, new Vector4(g0, g1, 0f, 0f));
if ((g0 > 0f) != multOn0) { multOn0 = g0 > 0f; SetRenderers(multGroup0Renderers, multOn0); }   // 只在穿过 0 时开关
if ((g1 > 0f) != multOn1) { multOn1 = g1 > 0f; SetRenderers(multGroup1Renderers, multOn1); }
// (2) 有自己 reveal 曲线的单独臂（门柱、手、巨像、背景巨物、后窗组，共 ~26 条）：每条的 **每个 LOD renderer**
for (int i = 0; i < singleCount; i++) {
    float rv = RevealAt(i, t);                                   // keys 之间 smoothstep
    bool on = rv > 0f;
    Renderer[] rs = singleRenderers[i];                          // Start() 里缓存的 GetComponentsInChildren<Renderer>(true)
    for (int k = 0; k < rs.Length; k++) {
        rs[k].enabled = on;
        if (!on) continue;
        rs[k].GetPropertyBlock(mpb);                             // 从这个 renderer 自己的块开始（不丢 _Phase / _FogCapI）
        mpb.SetFloat(_idReveal, rv);
        rs[k].SetPropertyBlock(mpb);
    }
}
// (3) 光晕的距离淡出 + 关掉淡到 0 的部件（技术 r4 M4 / M5）
float D = Mathf.Abs(gate.z - eyeWorld.z);                        // 眼到裂口平面
float halo = Mathf.Clamp01((SmoothStep(250f, 1200f, D) - 0.25f) / 0.75f);   // 1.2 km 外 1，U8 0.47，D < ~575 m（~U8+3.5）为 0
haloMat.SetFloat(_idIntensity, haloBase * halo);  haloRenderer.enabled = halo >= 0.05f;
float Df = Vector3.Distance(eyeWorld, foot);                     // 眼到脚
laneTf.localScale = new Vector3(Mathf.Clamp(0.10f * Df / (S * 420f), 0.15f, 1f), 1f, 1f);   // 光路四边形只盖住光路
float fold = KeyAt(skyfoldsKeys, t);  foldsMat.SetFloat(_idIntensity, fold);  foldsRenderer.enabled = fold > 0f;
float add  = KeyAt(cloudglowAddKeys, t); glowAddMat.SetFloat(_idIntensity, 0.25f * add); glowAddRenderer.enabled = add > 0f;
float lane = KeyAt(laneKeys, t);  laneMat.SetFloat(_idIntensity, lane);
```

**`Start()` 一次**（技术 r4 BT-4 的修法）：每个实例取 `GetComponentsInChildren<Renderer>(true)`（**三个 LOD 都要**），对每个 renderer：
`GetPropertyBlock(mpb)` → `SetFloat(_Phase)`、`SetFloat(_FogCapI)`（群臂：0.39 / 0.50 / 0.60）、`SetFloat(_RevealGroup)`（群臂：0 或 1）、`SetFloat(_Reveal, 1)` → `SetPropertyBlock(mpb)`。**以后每帧不再碰群臂的 MPB**。
- 旧 §2.1 的写法（一个共享的 `mpb` 每帧 `SetPropertyBlock` 给 `inst.renderer`）会把所有实例的 `_Phase` / `_FogCapI` 覆盖成最后写的那个，而且只写了 LOD0：**不要用**。
- `Renderer.GetPropertyBlock` 在当前 VRChat SDK 的 Udon 白名单里需要确认（技术 r4 BT-4 最后一条）；如果没有暴露：单独臂改成每条 3 个 renderer 各自一个 `MaterialPropertyBlock` 实例（Start 里 new 好、每帧只改 `_Reveal`）。
- `_Udon_TearFoot` 没写（w = 0）**且**材质的 `_TearFootM.w = 0`（默认）时，v2.7 的伤口光整个关掉（`WoundOn()`）——技术 r4 m4 说得对，旧 README 的“退回 v2.5”那句是错的，已改。

### 2.2 裂口（`deliver/Tear` 套件 **v6**）
- `Tear_Root`：GateRoot 子物体，`localPosition (0, −150, 0)`、`localEulerAngles (0, 180, 0)`、`localScale = H(t)/1000`。
- H(t)：PCHIP 过 (U6, 565) (U7, 616) (U7b, 640) (160.5, 715) (U8, 799) (U9, 1000)。`_Udon_TearOpen`：U6 0 → U7 0.333 → U8 1；`_Udon_RipProgress = ss((t − U7) / 16)`。
- **门里不用套件自带的 12 张光束扇**（关掉），用 JSON `shafts` 的 2 束（§8.1）。
- **抓点**：`tear.grips`（`tear_def.GRIPS`）；抓布的手指末端绕抓点盘 1.25 圈，`track` 让盘绕一直扣在布上直到 U9 − 1。第 8 轮：**左手盘住左上那片小翻布的唇**（t 300 / 165），不再是“带肘的蟹腿”（美术 r4 M6）。
- **新部件（套件 v6，`Tear_Kit.fbx` 已重建、按 Unity 读法核对）**：
  - `Tear_FootSkyline`（Part = Skyline，premultiplied，queue 2989，贴图 `Tear_FootSkyline_1024x160.png`：A = 云海自己的一排云头 + 两片分开的“唇” + 一道 V 形缺口，R = 背光的边）。一张竖直的四边形，在脚前 140 套件米（朝车）、宽 2 × 2.6 个透镜半宽；白顺着缺口流进云里。`_SkyCloud` 要填**它后面那片 CloudSea 卡的月光色**（线性；渲染里 U7 是 (0.060, 0.066, 0.082)），否则会看出一张卡。**取代 v5 的 5 张脚部云团**（在 U7 读成正面打光的底座，U8 读成白色碎屑——两份评审都点了）。
  - **`Tear_FootSkylineIn`（套件 v6.1，第 9 次运行）**：同样的 Skyline 材质（复制 `Tear_FootSkyline` 的材质、换贴图 `Tear_FootSkylineIn_512x160.png`），在透镜前 11 套件米（~8 m）、宽 2 × 1.5 个半宽、3–8 m 高的一排低云头。U8 前方从 ~120 m 高往下看时，外排 V 口的尖投影在“透镜 / 平云面”交线下面 0.9°，白就停在一条直线上；这排云头挡住那条线。Unity 的 CloudSea 卡本来是带 alpha 的云头，这张卡是保险（1 个四边形，透明预算已计入）。
  - `Tear_LightLane`（Part = Lane，`Blend DstColor One`，queue 2989）：伤口在云顶上的**光路**，从脚朝眼睛，逐像素按眼睛的方位算（`_LaneW (1.6, 5, 1400)`：脚下半宽 1.6° → 1.4 km 处 5°），颜色 `#C0B9E4 → #8F9AC0`；是乘到下面的云卡上（`dst × (1 + lane)`），所以只有云头亮、云沟仍暗（美术 r4 B3.4）。
- **淡出关键帧 `tear.fades`（第 8 轮）**——都是关键帧之间 smoothstep；标了 `renderer_off_at_zero` 的，值为 0 时 **renderer.enabled = false**（技术 r4 M5：淡到 0 的部件仍然在光栅化）：
  - `cloudglow_additive_intensity_keys`：`Tear_CloudGlow` 叠加材质 `_Intensity × k`，**U8 − 4 → U8 − 0.5** 从 1 到 0（**关 renderer**；第 7 轮是 U8 − 2 → U8 + 1，透明预算里它在 U8 时还开着）。叠加材质另设 `_NearFootCut 1`（脚 ±1.5 半宽内叠加为 0，只剩相乘的光池在云自己的起伏上）、`_FootAddK 0.25`。
  - `skyfolds_intensity_keys`：`Tear_SkyFolds` 的 `_Intensity`：**U6 + 13.5 时 0.15 → U7 时 1**（褶子跟着手来：U6 还没有手，单独的褶读成“胡须”），U8 + 2 → U8 + 6 回到 0（**关 renderer**）。门里的 `skyfolds` 覆盖值 0.55 → **1.0**（技术 r4 M8）。
  - **光晕距离淡出**：`Tear_Halo` 的 `_Intensity × k`，`k = saturate((smoothstep(250, 1200, D) − 0.25) / 0.75)`，D = |裂口平面 z − 眼 z|（每帧）：1.2 km 外 1、U8 0.47、D < ~575 m（约 U8 + 3.5）为 0；**k < 0.05 关 renderer**（光晕卡很大：U8 + 7 时哪怕很淡也有 1.3 FSE 的片元）。TentacleSway v2.7 的伤口空气项用同一个淡出（`LanbaiHaloFade()`）。
  - `lane_intensity_keys`：光路 U8 − 2 → U8 + 2 从 1 到 0.45（U8 前方的 APL）。光路四边形的 `localScale.x = clamp(0.10 × D脚 / (S × 420), 0.15, 1)`（只盖住光路本身：不缩放时 U8 有 0.38 FSE）。
  - `pool_fade_keys`：`Tear_CloudGlow_Lit` 的 `_Intensity` 与两个 CloudGlow 材质的 `_FootGlow` × k，U8 − 2 → U8 + 2 从 1 到 0.4。
  - `Tear_FootSkyline` **不下沉、一直留到 U9**（它盖住透镜和云的交界：技术 r4 B1“脚留到 U9 − 1”）。
- **透镜的预深度 pass**：v6 里，`_DepthPrepass = 0` 的材质在顶点阶段就把三角形裁掉（`float4(2, 2, 2, 1)`），不再产生片元（技术 r4 M5.1）。只有 Lens 材质设 `_DepthPrepass 1`。

---

## 3. 机位（JSON `cameras`）

| 机位 | t | 眼位（车内） | 看向 | 水平 FOV | 读法 |
|---|---|---|---|---|---|
| `U6` | U6 + 13 = 146.80 | 主座位 (0.55, 1.70, 2.05) | 正前 | 90 | 里尔克那句的最后一秒：伤口、月亮、银边的云塔；巨像 2 从月旁的云里升起，**巨像 1 的冠刚破云**（技术 M1） |
| `U7` | U7b = 155.10 | 同上 | 正前 | 90 | *…und wollt' mich abweisen*：两只手、Engel 盘住右唇、巨像 2 拿走月亮、**两侧的群臂浪**、右门柱在门玻璃里 |
| `U8side` | U8 + 0.3 = 166.45 | 主座位 | 右 112°、**仰 8°**（第 7 轮：光雾带落到左下角，给门柱一条地平线） | 84 | 右门柱从侧窗后方经过 |
| `U8near`（新） | U8 + 1.6 = 167.75 | 主座位 | 右 100°、仰 4° | 84 | 近处臂 Near_1（离眼 ~16 m、离车壳 11.5 m）从右侧窗掠过（技术 m8） |
| `U8fwd` | U8 + 3.5 = 169.65 | 主座位 | 正前 | 90 | 圣经验收帧：伤口大过挡风玻璃，两根鞭梢在白前交叉成 X |
| `U8a` | **U8 + 7 = 173.15** | 主座位 | 正前、**仰 49°** | **50** | *Ach nein!*：天窗（约占画面 37%）里整块都是伤口；一圈干净的暗框；光落进车里（顶棚上的反光 + 光柱里的尘） |
| `U8b` | U9 − 4 = 175.55 | 过道 (0.05, 2.00, −1.60) | 右 6°、俯 13° | 90 | 天窗光斑落在过道上，光束里有尘（尘只在光柱里、≤ 1.5 px） |
| `rear` | U9 − 2 = 177.55 | **贴着后窗** (0, 1.95, −3.15) | 正后、**仰 12°** | **78** | 俄耳甫斯镜头：两道巨拱 + 一只四指的手像闸门一样合在路上方，只有月光轮廓；**没有光环** |
| `key` | U7b − 0.6 = 154.50 | 主座位 | 右 6°、仰 7° | 82（2.39:1） | 主视觉：巨像 2 已拿走 ~80% 的月亮（射线法；技术 m3 更正了上一版的 “~87%”），不画车壳 |

`unity_euler_deg = (−pitch, yaw, 0)`。

---

## 4. 实例与动画（JSON `instances[*]`；距离 / 方位按 U7b 主座位）

### 4.1 显现（`reveal`）与升起——**谁什么时候出现**

`_Reveal`（instanced）在雾的上限之后作用：`f = 1 − (1 − f) × _Reveal`；`_Reveal = 0` 时 renderer 关。关键帧之间 smoothstep。

| 实例 | 层 | 长度 | U7b 距离 / 方位 | reveal | 升起 / 其他 |
|---|---|---|---|---|---|
| `Pillar_R` 右门柱 | colossus（pillar） | 1 271 m | 0.48 km / +29° | **U6 + 13.5 → U7b − 1**（147.3 → 154.1，第 7 轮放慢：技术 M3） | 站着；车经过后 `close` |
| `Pillar_L` 左门柱 | colossus（pillar） | 1 029 m | 0.82 km / −47° | 同上 | 站着；`close` |
| `Colossus_3` Engel | colossus（hero） | 2 826 m | 2.7 km / +24.5° | U7 − 2 → U7b − 1 | 站着；**末端盘住右唇 66% 高处**（盘绕半径 40 m、1.25 圈）；`lean` |
| `Hand_L0/1/2` 左手 | mid（hand） | 626–829 m | 1.1 km / −13° | U6 + 13.5 → U7 + 3 | 130.8 → 154.6 从云里滑出（藏在 reveal 0 / 云下）；`track` U7b → U9 − 1：L0/L2 的盘绕扣在抓点上，**L1 的鞭梢跟着右唇 16% 高的点**（交叉 X 的低的一笔） |
| `Hand_R0/1/2` 右手 | mid（hand） | 970–1 159 m | 1.05 km / +21…+23° | 同上 | 同上；**R1 的鞭梢跟着左唇 24% 高的点**（X 的高的一笔，在前面、更粗） |
| `Colossus_2` 拿月亮的 | colossus | 1 085 m | 2.8 km / −21° | U6 + 8 → U6 + 14 | 121.8 → 150.8 斜着滑出；`lean` 盖住月盘；`track` 到 U9 |
| `Colossus_1` 里尔克后面 | colossus | 647 m | 3.2 km / +24.6° | **U6 + 9 → U6 + 13** | **第 7 轮（技术 M1）**：预先沉好，**143.8（U6 + 10）冠在云顶**，trap 升起到 **165.8**（≤ 0.34°/s）；实测冠在云上 U6 + 13 22 m、U7 72 m、U7b 140 m、U8 276 m |
| `Colossus_bg_00…05` 背景 6 | colossus_bg | 1.1–1.4 km | 3.4–4.2 km / ±21…±52° | U7 − 2 → U7b − 0.5 | 站着，雾 **0.45**（第 7 轮） |
| **`Mult_000…149` 群臂 150**（新） | surge（multitude） | 冠高 215–490 m | 2.6–5.6 km / \|方位\| 14–58° | **U6 + 13 → U6 + 17** 从雾里出来；**U8 − 5 → U8 + 1 退回雾里** | 从云里冠先升起：t0 = 141.0…149.5（早的部分藏在 reveal 0 里），t1 = 152.3…157.6（多数 ≤ U7b）；**实测**自身角速度中位 0.91°/s、p90 0.94、最大 1.22（§4.5） |
| `Near_0/1/2` 近处 3 | near（Near_2：mid 材质） | 150–202 m | 随车（§4.6） | 无 | 升起 156–168；`drift` |
| **`Rear_ArchA/B`、`Rear_Hand0…3` 后窗 6**（新） | rear | 1.4 km（拱）/ 2.0–2.2 km（手指） | U9 − 2 时车后 0.95–1.5 km | **U9 − 8 → U9 − 3**（171.55 → 176.55） | 站着；`lean` 向路中间俯 5°（U9 − 14 → U9 + 2）；**显现开始时它们已在车后 \|方位\| ≥ 138°（结束时 ≥ 146°）**，离车 0.66–1.2 km，从雾里出来，不在侧窗里（技术 M3） |
| 远潮 360 片 | tide | 380–1 600 m | 4.8–12 km / ±24…±70° | 材质级 `_Reveal`：**U7b + 2 → U8 − 2 退回雾里**（第 7 轮提前：群臂占住主角那一刻；透明预算） | 同第 6 轮 |
| 云塔 9 张 | — | 480–990 m | 各巨物根前 140 m | — | **第 7 轮：下沉代替淡出**（技术 M3）：显现开始后 6 s 起、25 s 内沉下 0.75 × 高（≤ 0.3°/s），最后 2 s 在地平线以下才把 alpha 关掉 |

- **U6 + 13 s 时画面里只有**：伤口、月亮、云塔、巨像 2（reveal ≈ 0.9）和刚破云的巨像 1。门柱、Engel、背景、两只手、群臂都还是 reveal 0。
- 动画类型：`rise`（ss / trap / beta）、`lean`、`track`（Slerp 关键帧）、`close`、`drift`。公式在每条 `ease` 字段。

### 4.2 形体
- 全部单独的臂是按画面写控制点的中心线（`arms4.py`）：斜着出云（25–50°）、上 35% 弯下来、天鹅颈收尖、300 m 外无分叉。
- **两只手（第 7 轮，AD 2 / 美术 B2）**：两边**不再镜像**。左手（小，626–829 m）是一条在月亮下面伸向伤口的斜线；右手（大，970–1 159 m）是一道卷起的浪，拱到仰角 +14° 再落到右边的翻布上。手指的中心线平滑 45 m（`HAND_SMOOTH_M`）——上一版的“膝盖”就是没平滑的折点。
- **抓布 = 盘绕，不是爪**：每只手两根抓布的手指末端用 `arms4.coil_end` 绕抓点盘 1.25 圈（半径 7 m × R0/20、螺距 1.6 r、切向引入，引入段 ≤ 4 r），像触手缠住布边。
- **鞭梢交叉成 X**（美术 M5）：`CROSS = {L1: zf 0.16, R1: zf 0.24}`：两根各从自己这边的唇出发，斜着越过白、勾住对面的唇；U8 + 3.5 时交叉点在白的 ~30% 高度（在挡风玻璃上沿以下）。R1 在前、更粗。
- **Engel**（美术 M1）：末端盘住右唇 66% 高处（`ENGEL_GRIP_ZF 0.66`、`ENGEL_COIL_R 40`），雾 0.40：读作一条比天暗的巨臂抓着伤口，不是灰梁。
- 皮肤贴图密度按实例尺寸缩放：主贴图 tiling = R/25、细节法线 = R/4（群臂固定 (1, 4)：它们只有几十个像素，不需要；也让 150 个实例共用一个材质）。

### 4.3 云塔
`towers.items`（9 个）：每个巨物根前方 140 m 一张 `Cloud_Congestus_moon` / `Cloud_Bank_moon` 卡（480–990 m 高）。巨物显现开始后：塔**下沉**（`sink_keys`：显现开始 + 6 s → + 31 s 从 0 到 −0.75 × 高，轴心在底），最后 2 s alpha → 0（那时已在地平线以下）。朝月一侧有**银边**（月方向 ~7° 内的 e 折，`silver 0.9`），底部比顶部多 22% 的雾（站在云海里，不是放在上面）。

### 4.4 远潮（`tide`）
同第 6 轮（v3 图集、360 片、UV6 雾高化开），只改了退潮：`_Reveal` **U7b + 2 → U8 − 2**。主角那一刻“很多小的”由群臂负责；远潮是群臂后面更远的一层（在主视觉里大多被云塔与云团挡住，见 §13）。

### 4.5 群臂（`Mult_000…035`，**第 8 轮重做**）——“成百条黑色的巨臂涌向它”
- **为什么重做**：美术 r4 B2：150 条一样大小、一样雾的臂读成“一片芦苇”，还把左边的云塔都盖住了；技术 r4 M2：相位和到伤口的距离无关（“是森林，不是涌”），6 个姿态全是正缩放，U8 之前就全退了。
- **现在：更少、更大、分层**。**36 条**分成 **5 簇**（左 3、右 2，`MULT_CLUSTERS`：方位 −45 / −30.5 / −19.5 / +29.5 / +45.5，各 6–8 条，3.2–5.0 km），站在巨物云塔**之间 / 后面**，簇与簇之间留 ≥ 6° 的空光雾带（±50° 里 ≥ 35% 没有剪影）。每簇一条**主臂**（500–650 m 高），其余是它的 30–68%（高度比约 3:1）。
- **姿态 12 个**：MU0/MU1 = 伸（一根直的细鞭、微垂、**没有钩**）、MU2/MU3 = 卷（**真的卷**：半径 0.07 L、170–230°，4 km 外 ≥ 12 px）、MU4/MU5 = 落（冠向后缩、半卷）；**每个都有镜像** `MU0m…MU5m`（`GateMultitude_v2.fbx` 里是独立的网格，不靠负缩放）。这一版 36 条里 17 条用镜像。每条绕竖轴转向伤口 ±22°。
- **雾分档 = 层次**：档按到 U7b 眼睛的距离：< 3.3 km A、< 4.3 km B、更远 C；档值 0.45 / 0.58 / 0.70 × `MULT_CAP_K` 0.86 = **`_FogCapI` 0.39 / 0.50 / 0.60**（身体 ≈ 光雾带 − 10 / − 8 / − 5 L\*；JSON 每个实例的 `_FogCapI` 已经乘好）。这一版的实际分布：B 22 条、C 14 条（A 档没有成员落在 3.3 km 以内）。**每档一个材质**（`M_Multitude_TierA_near / TierB_mid / TierC_far`：`_RimGain` **2.4 / 2.4** / 0.08、`_RimLadderFloor` **0.5 / 0.3** / 0（第 9 次运行：远处阶梯原来把轮廓压到 × 0.01–0.02，等于没有）、`_RimWound` 1.75 / 0.75 / 0.60）——近的两档有月轮廓、远的融进去。
- **摆动 = 往里滚的浪**（技术 r4 M2）：`_Phase = frac(到伤口的距离 / 600 m)`，三个档的材质都用 `_SwayFrequency` 1/6 Hz、`_SwayAmplitude` 0.05、`_SwayWavelength` 1.2：波峰朝伤口走；3–5 km 外尖端 ±25 m ≈ 0.38°/s。
- **升起**：大部分藏在 `reveal 0` 里（t0 ≥ U6 + 2；显现从 **U6 + 14** 开始，技术 r4 m7），主臂 U7b − 1 前站好，其余的在 U7 … U7b + 6 还在涌（U7b 看到的是**涌到一半**）；可见部分的自身角速度 ≤ **0.6°/s**（实测中位 0.58、最大 0.60；技术 r4 m8）。
- **留到 U9 − 1**（技术 r4 M2）：在 U8 前方视角里会站到白 6° 以内的成员归第 1 组，U8 + 1 退；其余第 0 组一直留到 U9 − 1。这一版 **36 条全在第 0 组**（没有一条会站到 U8 前方的白旁边）。
- **Unity**：12 个姿态网格 × 3 个档材质；36 条本来就是 36 次 draw，GPU Instancing 开着无害。每实例的 `_Phase`、`_FogCapI`、`_RevealGroup` 在 `Start()` 里写进**每个 LOD renderer 自己的** MPB 一次（§2.1）；显现走全局 `_Udon_MultReveal`（材质 `_UseGlobalReveal 1`）。
- **“成百条”从哪来**：近处这 36 条 + 后面的远潮 360 片（§4.4，U7b + 2 → U8 − 2 退潮）。我们认为 36 条 3D 臂 + 远潮比 150 条同质的臂更像“成百条在涌”（层次 + 空隙），但 640 px 的“陌生人测试”里“hundreds”这个词不一定会出现——见 §13。

### 4.6 近处 3 条（`frame = bus`，不挂 GateRoot）
同第 6 轮：世界位置 = `(x, −h_bus(t) + y, z + v_rel·(t − t_ref))`；摆动写在材质里；Near_0 最近 14.2 m / 速度比 0.73，Near_1 11.5 m / 0.89（圣经 ≥ 8 m、≤ 1）；Near_2 48.6 m → `mid` 材质。尾流 JSON `near_wake`。**新定稿 `final/U8_near.png`** 是 Near_1 从右侧窗掠过的那一刻。

### 4.7 后窗（`Rear_ArchA/B` + `Rear_Hand0…4` + `Rear_Hand2F` + 门柱 `close`）
**第 8 轮（美术 r4 M4、技术 r4 M3：“四个一样的钩 = 衣帽钩 / 蟹腿”，“比虚空还亮的灰鬼”）**：
- 两道巨拱 `Rear_ArchA`（根半径 62 m、1.53 km）、`Rear_ArchB`（52 m、1.41 km）：中心线改成 **S 弯**，30–40% 高处**加粗 ≥ 20%**（`arms4.rad4(swell)`），尖端卷起来而不是一根尖刺。
- 手改成 **5 根不一样的手指**（2.06–2.26 km）：`Rear_Hand0` 一根直的细线到尖、`Rear_Hand1` 反手性的半卷（转了 60° 的平面里）、`Rear_Hand2` **分叉**（`Rear_Hand2F` 是叉出去的那一支，231 m）、`Rear_Hand3` 唯一保留的钩、`Rear_Hand4` 一滴垂下的尖；尖端那一段的长度因子 0.60–1.0、尖端仰角 3–9.5°（各在自己的平面里）。
- 材质 `rear`：**`_Color` 0.5（线性；sRGB Color 填 0.735）**、`_FogDensityScale` **0.35**、`_RimBackOnly 0` + `_RimPxMoon 1.5`（朝月的那一侧轮廓 1–2 px 冷边）、`_RimGain 0.5`、`_RimWound 0`、`_CloudTopColor (0.10, 0.11, 0.13)`。身体要比虚空暗（同行 ΔL\* ≤ −3，§10）。
- 后窗的地平线：光雾带的**背带**改成 |方位| 65 → 120° 渐入（侧窗也有地平线），后窗视角用 `_BackBand 1.25`（其余 0.55）：手臂压在一条银色地平线上（技术 r4 M3）。
- 渲染里加了一个占位的**后窗窗框**（4–6% 的暗边，美术 r4 M4“俄耳甫斯要有一块玻璃回头看”）；真车壳来了以后以真车壳为准。
- 显现 U9 − 8 → U9 − 3（|方位| ≥ 138°）；`lean` 向路中间俯 5°；**月之光环删掉**（第 7 轮起）。
- **第 9 次运行**：第 8 轮的后窗定稿里，垂下来的手指读成**獠牙 / 冰锥**（渐细的尖 + 22–40 m 的小钩，1 km 外只是一个尖）。
  现在尖端是**接在原长度后面、画在画面平面里的**（后窗眼看 −y，所以弯在 x–z 平面里才看得见；第 8 轮的半卷在深度方向，侧着看就是一根刺）：
  `Rear_Hand0` 一道 S 形鞭梢收成细线、`Rear_Hand1` 向画面左的 120° 半卷、`Rear_Hand2` 轻弯 + 60% 处分叉（原来 80%，只有 68 px）、`Rear_Hand3` S 形鞭梢、`Rear_Hand4` 230° 的卷。
  它们大小、方向、圈数都不一样（不是“一排一样的卷尖”）。`GateArms_v4.fbx` 里这 6 个网格已重新烘焙；动画（俯 5°）没变。对比：`wip/r9/_cmp_rear3.png`（上 = 第 8 轮，下 = 现在）。

### 4.8 这一版怎么替换 `gate_context.md` 里的四类触手

| 旧（`LB_Builder_Gate.cs`） | 新（本 JSON） |
|---|---|
| 隧道（380 m）+ 裂口后 700×700 黑板 + `RiftGlow` | **全部删掉。** 开阔的云海、天上的一道裂口（`deliver/Tear` v6），天空 = `Lanbai/GateAirSky` v3 的光雾带（与触手的雾同一个 include）。 |
| 1. 簇状小触手 ~700 根 | **群臂 36 条，5 簇**（§4.5，3D，12 个姿态含镜像）+ 远潮 360 片（§4.4，一半是 3–5 条的簇） |
| 2. 6 根巨型骨架触手 | 两根门柱 + Engel + 巨像 1、2 + 背景 6（§4.1），各藏在云塔里 |
| 3. 14 根擦车 | 近处 3 条（§4.6），带摆动的距离 / 速度检查，不擦车 |
| 4. 90 根裂口边缘放射细触手 | 两只手的 4 根**盘住布的手指** + 2 根**交叉成 X 的鞭梢** + Engel 的盘绕 + 套件 v6 的散线与断纱 |
| 程序化 Tube + 三盏点光 | `GateArms_v4.fbx` + `GateMultitude_v2.fbx`（LODGroup）+ `Lanbai/TentacleSway` **v2.7** + 实时平行光（月）+ **伤口线光源（shader 内，§6）** |
| （新）后窗 | 两道 S 弯巨拱 + 五指（各不相同）的手 + 门柱 `close`（§4.7） |

---

## 5. 材质（`instances[*].material` 已经是完整参数；按种类做材质）

| 种类 | `_FogDensityScale` | `_FogCap` / 高度 | `_RimPx` | `_RimGain` | `_RimWound` | `_ReflectionScaleFar` | `_WoundSpecFar`（v2.7） | 其他 |
|---|---|---|---|---|---|---|---|---|
| `pillar` 门柱 | 0.05 | 1 / 0 | 3.5 | 0.25 | 5 | 0.08（`_ReflFarRange` 150–450） | 0.5 | |
| `mid` 手（Near_2 也用） | 0.30 / 0.375 | 1 / 0 | 2.0 | 0.45 | 5 | 0.30 | 1.0 | |
| `hero` Engel | 0.40 | 0.92 / 5 000 | 1.2 | 0.15 | 5 | **0.01**（第 9 次运行；原 0.15） | **0.15** | `_ConvexCrease 0`、`_OcclusionStrength 0` |
| `colossus` 巨像 1、2 | 0.55 / 0.12 | 0.92 / 5 000 | 1.0（**巨像 2：2.2**） | 0.08（**巨像 2：0.9**） | 3 | 0.20 | 0.3 | 巨像 2 = 月亮正在它背后：2–4 px 月轮廓（美术 r4 M1.4） |
| `bg` 背景 | 0.45 | 0.92 / 5 000 | 1.0 | 0.05 | 1.5 | 0.15 | 0.15 | |
| `surge` 群臂（3 个档材质） | 1.0 | 0.92 / 5 000，**`_FogCapI` 0.39 / 0.50 / 0.60 每实例** | 1.0 | **2.4 / 2.4 / 0.08**（+ `_RimLadderFloor` 0.5 / 0.3 / 0，第 9 次运行） | **1.75 / 0.75 / 0.60** | 0.15 | 0.15 | `_UseGlobalReveal 1`、摆动 1/6 Hz / 0.05 / 波长 1.2、tiling (1, 4) |
| `near` 近处 | 1.0 | 1 / 0 | 5.0 | 1.0 | 5 | 0.60 | 1.0 | **`_WoundSpecMax 0.6`** |
| `rear` 后窗 | **0.35** | 1 / 0 | 2.5 | **0.5** | 0 | 1.0 | 1.0 | `_RimBackOnly 0`、**`_RimPxMoon 1.5`**、**`_Color` 0.735（sRGB = 线性 0.5）**、`_CloudTopColor (0.10, 0.11, 0.13)` |

**全体（v2.6 起）**：`_CloudTopColor (0.050, 0.056, 0.068)`、`_CloudFade 46`、`_RootDissolve 18`、`_FogDensity 0.0006`、`_FogExtra (1.5, 25)`、`_FogCapFrom (1300, 1700)`、`_UseUVRadius 1`、`_MoonGlowFog 0.35`、`_HaloFog 0.35`、`_BandEl (6, 22, 2)`、`_HazeNear / _HazeFar` = 第 6 轮 × 0.80、
伤口光：`_TearDiffuse 2`、`_TearDiffuseRef 600`、`_TearWrap 0.4`、`_TearSpec 1`、`_TearSpecRadiance 2.2`、`_RimWound 5`、`_RimWoundPx 2.5`、`_RimWoundDeg 6`、`_RimWoundNear (0.76, 0.80, 0.90)`。

**第 8 轮新增（v2.7，全体）**：
- **细的部分**（技术 r4 B2：鞭梢上等距的环 / 珠子）：`_ThinK (0.12, 0.40)`——UVRadius < 0.12 的地方主贴图（法线、光滑度、反照率）全部让位给 `_ThinSmooth 0.84` / `_ThinAlbedo (0.017, 0.017, 0.022)`，只留非整数平铺的细节法线；月轮廓的湿项用这个光滑度。原因：UV0 是保角的，鞭梢上一个贴图周期 ≈ 一圈周长 ≈ 2r，贴图里任何成行的东西都会每 2r 重复一次。
- **伤口高光的远距缩放与上限**（技术 r4 M1、美术 r4 B3.1：Engel 上 L\* 100 的亮条）：`woundSpec × lerp(1, _WoundSpecFar, smoothstep(_ReflFarRange))`，再 × (0.4 + 0.6 湿条纹)，眼睛仰角 +25° 以上没有（`_WoundSpecEl (25, 18)`），最后 `min(…, _WoundSpecMax 0.35)`（近处 0.6）。
- **白前面的臂 = 它的背光面**（美术 r4 B3.2）：`OverWhite()`——点在裂口平面**前面**、屏幕上落在白里或白边 `_OverWhiteRamp 1.5°` 以内：表面 × `_OverWhiteDim 0.12`、雾 × (1 − `_OverWhiteFog 0.6`)、伤口空气 × (1 − `_OverWhiteAir 0.85`)，两侧轮廓各一道 `_WrapPx 0.9` px 的白色包边（`_WrapGain 1.2`、`_WrapColor (0.80, 0.80, 0.92)`）。透镜沿轴的半宽曲线 `_TearHW0 / _TearHW1`（8 个结点 × 全局半宽，JSON 每个材质里都有；与开口和 H 无关）。
- **湿条纹的远处高光 `_StreakKeep`（v2.7b）**：远距的高光缩放 `_ReflectionScaleFar` 放过长的湿条纹（光滑度 0.80–0.90）的比例：近处 / 后窗 0.8、手与门柱 0.5、巨像 0.15、**Engel / 背景 / 群臂 0**。渲染从第 3 轮起就这么做（“长长的亮线才读得出尺度”），shader 却没有：r4 主视觉顶边 Engel 上那条 L\* 100 的亮条是**月光**的高光，不是伤口的。**第 9 次运行更正**：关掉保留的湿条纹它还在——是整个高光在掠射角的月光亮点（远距缩放 0.15 之后仍有 10（线性），比伤口的白还亮），所以 **Engel 材质的 `_ReflectionScaleFar` 0.15 → 0.01**（渲染 `spec_hero` 同步），只剩轮廓光。
- `_BackBand 0.55`、`_HaloColor (0.195, 0.198, 0.332)`（光晕 v6 `#7A7B9C`）、`_TearFootM.w 0`（没有 Udon 时伤口光关掉）、`_UseGlobalReveal 0`（群臂 1）、`_SwayWavelength 0.9`（群臂 1.2）。
- **光滑度**：`T_Tentacle_MetallicSmoothness` 的 A 仍是 0.52–0.81（圣经 0.70–0.90）。这是对上一轮“塑胶”评审的有意回答；写进了修订 v2.3（§12，技术 r4 m1）。如果 AD 不批，shader 里一行就能映射回去：`smoothV = lerp(0.72, 0.90, saturate((ms.a − 0.52) / 0.29))`。

## 6. 光与天空

- **月**：实时平行光 `#D6E4FF`，E 1.0，软阴影，朝月 (−0.2059, 0.1392, 0.9686)（−12° / +8°）。补光 `#5A6488` E 0.24 自下而上。
- **伤口 = 主光（第 7 轮，AD 2）**：
  - **触手上**：不用 Unity 灯。TentacleSway v2.6 在 shader 里把伤口当作**线光源**（`_Udon_TearFoot → _Udon_TearTop`，宽 = `_Udon_TearFoot.w`）：漫反射 = 线段上最近点方向的 wrap（0.4）× `_TearDiffuse × (600 / d)²`；高光 = Karis 代表点的管状光（GGX）× `_TearSpecRadiance`；**伤口轮廓 `_RimWound`**：屏幕上朝伤口那一侧的 2.5 px 轮廓（按屏幕方向判断，所以远的细臂也接得住），离伤口 6° 以内最强。渲染里对应的是两盏与白同尺寸的椭圆面光（`gate_scene.tear_area_lights`）+ 解析的管状高光（`add_tear_spec`）+ 同样的屏幕空间轮廓。
  - **车厢里**：原来的伤口平行光（`#A99DE1`，E 0.8，无阴影，从 `_Udon_TearPos` 指向车）**只照车厢**（Culling Mask = 车厢层），不再照触手（否则重复）。
- **光雾带**（第 7 轮，AD 3）：方位 `#484D63` → 50° `#2A3041` → 60° 虚空，**× 0.80**；**仰角 `w_el = (1 − smoothstep(6°, 22°, el))^2`**（`_BandEl = (6, 22, 2)`）：+7° 以下满、+10° 0.71、+13° 0.32、+16° 0.09、+20° 起是夜 `#070A14`。后方另有一条“背带”：**第 8 轮从 |方位| 65° 渐入到 120°**（原来 110–150°；侧窗也要有地平线），`_BackBand` 0.55，后窗视角 1.25。
- **一个定义（第 8 轮，技术 r4 BT-3）**：天空盒 `Lanbai_GateAirSky` **v3** 与触手的雾色都 `#include "LanbaiGateSky.cginc"`：`LanbaiBand()`（带 + 背带 + 地平线下的去饱和）、`LanbaiMoonAir()`、`LanbaiWoundAir()`（光晕 v6 的三张卡、以热核为中心、× 距离淡出 `LanbaiHaloFade()`）。上一版的天空盒还是 v2 的带（+15° 满、+35° 才到夜、没有 × 0.8 / 幂次 / 背带），远处被雾吃掉的臂会成为比天暗的剪纸。**验收（Unity）**：U7 机位开 / 关雾各截一张，一条完全被雾吃掉的臂在 el 10–25° 处与天一样（ΔL\* ≤ 1）。
- **月**：月盘 × 0.6（主视觉 / U7）；月蚀表 `final/moon_coverage.json`（同第 6 轮）：U7b − 0.6 ≈ 80%（主视觉留一线月）、U7b 95%、+0.5 100%、+1.0 96%、+1.5 92%、+2 88%；Udon 在 U7b + 1.5 起 2 s 内把天空盒月盘淡出。**淡出后月晕的核心项也乘月盘权重**（× 0.35，技术 m1）：U8 前方的月是一团 L\* ≤ 70 的软光，不再像雾里的月亮。

---

## 7. shader（**未编译**）

只做过 slang 的语法 / 类型检查（`Shaders/slang_check/`：`run_check27.py` = TentacleSway v2.7 的 base / SHADOWCASTER / FORWARDADD 三个组合；`run_check_sky.py` = GateAirSky v3；`run_check_tear6.py` = Tear v6 的 11 个 Part + 两种预深度 pass；**全部通过**）。这不是 Unity 编译：Unity 的内建函数来自 `unity_stub.slang`。

### 7.0 `LanbaiGateSky.cginc` v1（新，第 8 轮）
**v2（门驱动 v1.2，D-22）**：include `LanbaiSky.cginc`；`_Udon_FogModel.w > 0` 时 `LanbaiBand(V)` = `LanbaiHorizon(V)`；新增 `LanbaiGateDensity(材质密度)`（`_Udon_Fog` 优先）。见 `README_GateDriver.md` §2。
天空与雾色的唯一定义（§6）。放在两个 shader 同一个文件夹。属性（两个 shader 都暴露）：`_HazeNear _HazeFar _Void _BandAz _BandEl _BelowHorizon _BelowDesat _BackBand _MoonGlowColor _MoonGlowShape _HaloColor _TearPos`；全局：`_Udon_TearPos _Udon_TearH _Udon_MoonDir _Udon_MoonDisc _Udon_FogBandDir _Udon_FogBandColor _Udon_FogBandWidth`。

### 7.1 `Lanbai_TentacleSway.shader` **v2.7c**（相对 v2.6；v2.7c = 第 9 次运行加的 `_RimLadderFloor`，`_RimGain` 范围 0–4）
1. 天空 / 雾色改用 `LanbaiGateSky.cginc`（含背带、光晕 v6、距离淡出）。
2. **细的部分**：`_ThinK`、`_ThinSmooth`、`_ThinAlbedo`（§5；技术 r4 B2）。
3. **伤口高光**：`_WoundSpecFar`（按种类）、`_WoundSpecMax`、`_WoundSpecEl`；光源半径上限 `min(hw / d, 0.6)`（不再漏到背对白的面上；技术 r4 M1）。**v2.7b `_StreakKeep`**（§5）：按种类关掉远处湿条纹保留的高光。Engel 的亮条是掠射角的月光高光（第 9 次运行：Engel 材质 `_ReflectionScaleFar` 0.01）。
4. **白前面的臂**：`OverWhite()` + `_OverWhite*` + 包边 `_Wrap*` + 半宽曲线 `_TearHW0/1`（美术 r4 B3.2）。
5. **伤口光开关**：`WoundOn()` = `_Udon_TearFoot.w > 0` 或 `_TearFootM.w > 0`；默认 `_TearFootM.w = 0`（技术 r4 m4）。
6. **群臂的显现**：`_UseGlobalReveal` + 实例化 `_RevealGroup` + 全局 `_Udon_MultReveal`（技术 r4 BT-4）；头注释里的三档雾改成 0.39 / 0.50 / 0.60（m3）。
7. **v2.7c `_RimLadderFloor`**：远处轮廓阶梯的下限，`ladder = max(exp(−ρd) × clamp((900/d)^1.2, 0.12, 1), _RimLadderFloor) × _RimGain`。默认 0（其他种类不变）；群臂 A / B 档材质 0.5 / 0.3、`_RimGain` 2.4。slang 三个 pass 通过。

**请在 Unity 确认**：`addshadow` 的 shadow caster 执行 surf 里的 clip；SPS-I 下像素轮廓、`_RimWound` 与 0.9 px 的包边逐眼看；`_Phase / _FogCapI / _RevealGroup` 在 GPU Instancing 下真的走 `UNITY_ACCESS_INSTANCED_PROP`；`OverWhite()` 在 U7 / U8 前方让两根交叉的鞭梢变成剪影（与 `final/U7_engelein.png` 对照）。

### 7.1b `Lanbai_GateAirSky.shader` **v3**（从 `deliver/Tentacles` 挪到 `gate/Shaders/`）
`#include "LanbaiGateSky.cginc"`：`LanbaiGateSkyColour(V, moonD, aureoleGain, discColor)` = 带 + 月晕（× 月盘权重）+ 月盘（0.05° 软边）。v2 在 `deliver/Tentacles/_superseded~/`。天空盒材质的 `_BackBand` 后窗视角时设 1.25（或接受较暗的后地平线）。

### 7.2 `Lanbai_TentacleTide_v2.shader` v2.2
未改。

### 7.3 `deliver/Tear/Lanbai_Tear.shader` **v6**
v5 的一切（颜色都是 `Vector`、填线性值；噪声在云海坐标）+ 第 8 轮：预深度 pass 在 `_DepthPrepass = 0` 时顶点阶段就裁掉（技术 r4 M5.1）；透镜脚的深而参差的切口（`CloudFootFadeN(−30, 18)`，35 m 格 / ±40 m）；新 Part **Skyline**（`_SkyCloud`、`_SkyRim`、`_SkyNear`）与 **Lane**（`_LaneW`、`_LaneFoot`、`_LaneNear`）；CloudGlow 的 `_NearFootCut`、`_FootAddK`；光晕 v6 卡与颜色。细节在 `README_Tear.md` v6 一节。

### 7.4 重名 shader（技术 M7）
`Lanbai/TentacleSway`、`Lanbai/TentacleTide`、`Lanbai/Tear` 在 `gate/` 与 `deliver/` 里各只有**一个** `.shader`：旧版本都是 `.shader.txt` 或在 `~` 文件夹里（`gate/Shaders/_archive~`、`gate/_r1/code/Shaders/*.shader.txt`、`gate/_r2/code/Shaders/*.shader.txt`、`gate/_r3/code/Shaders~`、`gate/_r3/deliver_Tear~`、`deliver/Tentacles/_superseded~`、`_v1~`、`deliver/Tear/_v1~`、`_v2~`）。最稳妥的做法仍是 §0 那句：**只拷列出的文件**。

---

## 8. 光束、云、远景

### 8.1 光束（`shafts.items`，**2 束**，挂 `Tear_Root`）
从透镜 30–36% 高处出发，**低而斜**（第 7 轮，AD 3）：左束穿过左手与巨像 2 之间向左外，终点仰角 7.5°；右束穿过右手与 Engel 之间，终点 9°；4–9° 宽、一个平滑的瓣、不等亮（1.0 / 0.6），整体 `shaft 0.35`。上面的天保持是夜。

### 8.2 云
- **脚下的峡谷（第 8 轮重新打开，短的）**：`look.crevasse 0.9`、`seam_lip 0.5`；230 m × S 朝车、宽 = 透镜宽的 20% → 0，底色 = 白自己的雾（`F_MIST_LENS × 0.55`，不再是薰衣草色），两壁随峡谷结束（第 7 轮的发丝线是因为壁没有在峡谷末端停下）。
- **伤口的脚**：套件 v6 的尖脚 + 脚部雾 + **脚前云头 `Tear_FootSkyline`**（V 口）+ CloudGlow 的脚部光瓣（相乘 × 2.6、叠加 × 0.25；叠加的 CloudGlow 在脚 ±1.5 半宽内为 0）。
- **光路**（新）：`Tear_LightLane`（§2.2）；渲染里是云海冒充体上的一层（只亮云头）。
- **云海（第 8 轮）**：远处 1–3 km 的起伏保留 0.45（原 0.12）、右近处保留 62% × 1.15、左右云塔恢复；Unity 一侧按 JSON `clouds.round8_deck` 调 CloudSea 卡的增益。
- **光池**：`Tear_CloudGlow_Lit`（相乘）+ `Tear_CloudGlow`（叠加 0.25，U8 − 2 → U8 + 1 淡出）。
- **云海的明暗（AD 3 “朝月一侧有银色的浪尖和深的谷”）**：渲染里的云海冒充体做了一次“朝月”调色（逐像素方位：朝月半边保留 60%（近）→ 30%（远）的起伏、2–4 km 外 gamma 1.35、±7° 的**月光路**在 0.3–2.5 km 的模糊浪尖上、去饱和 0.7）。**Unity 一侧**：`deliver/Clouds` 的 CloudSea 卡在朝月方位（−40…−4°）用对比更高的 moon 变体、并在 ±7° 的月方位楔里给浪尖的月轮廓 × 1.6（JSON `clouds.round4_grade`、`clouds.silver_lining`）；验收数见 §10（朝月云 p5 / p95 / 局部 σ）。
- **云塔**：§4.3（银边、底部雾、下沉）。
- **地平线云团**：同第 6 轮（22 张）。

### 8.3 天窗光斑（`skylight_spot`）
四角投影（JSON 每 0.5 s，按新的天窗位置 `SKY_C (0.55, 2.62, 2.80)` 重算）；卡的画法同第 6 轮（倒过来的软透镜 + 地板凸点）。光斑增益 1.15（技术 m7：上一版 luma p50 134，目标 170–200）。光柱里 300 颗尘：只在光柱里、0.7–1.4 mm、越靠近天窗越密（美术 M5：上一版像过道里的星空）。

### 8.4 后窗的月之光环——**删掉**（AD 5）
JSON `glory` 保留结构、`ring_gain 0 / core_gain 0`、`round4: REMOVED`——不要做。

### 8.5 目的地牌（AD 4）
车里那一面是空白的灯箱背面：自发光 `#12151C × (0.96 + 0.04 G)`，**屏幕目标 L\* 6–8**（技术 r4 m13：渲染原来约 3、这一版 × 2.3 到 ~7；原来写的 `#1A1E28` 约 11.6 偏亮；AD 要“几乎看不见的均匀微光”，在 Unity 里按屏幕读数微调）；`Bus_DestinationBlind_1024x256.png` 的 R（镜像「蓝白」）**只给车外那一面**（第 1 / 12 幕从车外看）。

---

## 9. 导入设置、LOD、透明预算

| 文件 | 设置 |
|---|---|
| `GateArms_v4.fbx` | Mesh Compression **Off**；Read/Write Off；**Generate Lightmap UVs Off**（会覆盖 UV1 = UVSway）；Normals Import；Tangents Calculate Mikk；Import Cameras / Lights Off。LODGroup 屏幕高度：**LOD0 > 25%、LOD1 > 6%、LOD2 > 0.5%**（门柱永远不能掉到 LOD2）。英雄臂 16.8 k / 5.8 k / 1.2 k 三角；近处臂 24 k / 6 k / 2 k。 |
| `GateMultitude_v2.fbx` | 同上；3 个档材质勾 **Enable GPU Instancing**；LODGroup 同上（3 km 外基本在 LOD1 / LOD2；**主臂在主视觉 / U7 里是 LOD0**——第 9 次运行起渲染也按这条规则选 LOD）。Cast Shadows Off。 |
| `TentacleTide_v2.fbx` | Mesh Compression **Off**；Generate Lightmap UVs Off；7 套 UV 全部保留。 |
| 投影 | GateRoot 下全部臂 **Cast Shadows Off**；只有近处 3 条（`NearRoot`）投影。 |
| `deliver/Tear/FBX/*` | 同 `README_Tear.md`。 |

**透明叠绘（`gate_fse.py` → `final/fse_U8.json`，桌面 16:9 / 90°，全屏等效）**——第 8 轮按技术 r4 M5 重算：
透镜的预深度 pass **单列一行**（其它 Tear 材质的预深度在顶点阶段就裁掉，不再算）；光晕按距离淡出、< 0.05 关 renderer；淡到 0 的部件（叠加 CloudGlow、SkyFolds、光晕）不算；新加脚前云头（只算云面以上）与光路（按 Udon 的 x 缩放）；脚部云团退役。
第一次算出来是 4.47 / 4.38 / 5.03（光晕卡在 U8 + 7 哪怕淡到 0.05 也有 1.3 FSE、光路四边形不缩放时 0.38、叠加 CloudGlow 在 U8 还开着）；改了三处（光晕淡出重映射 + 关、叠加 CloudGlow 提前到 U8 − 0.5 关、光路按距离缩放）之后：

| 帧 | 透镜 | 透镜预深度 | 光晕 | 天之布褶 | CloudGlow | 脚前云头 | 光路 | 云塔 | 远云 | 光束 | 车窗（估） | 云海卡（估） | **合计** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U8 | 0.111 | 0.111 | 0.432 | 0.146 | 0.452 | 0.036 | 0.134 | 0.413 | 0.295 | 0.042 | 0.7 | 0.9 | **3.77** |
| U8 + 3.5 | 0.180 | 0.180 | 0（关） | 0.234 | 0.362 | 0.085 | 0.073 | 0.379 | 0.297 | 0.045 | 0.7 | 0.9 | **3.43** |
| U8 + 7 | 0.321 | 0.321 | 0（关） | 0（关） | 0.375 | 0.230 | 0.046 | 0.305 | 0.299 | 0.031 | 0.7 | 0.9 | **3.53** |

上限 4.0。车窗玻璃 0.7、云海卡 0.9 仍是评审的估计，真车 / 真云卡进来后要重算。

---

## 10. 验收数（第 9 次运行的定稿上量；`gate_metrics.py` + `accept_r5.py` + `accept_r6.py`，层的归属来自同机位的 ID 渲染）

（`final/*_metrics.json` / `metrics_summary.json` = 圣经 §6·4 的老定义；`final/acceptance_r5.json` = r3 评审 §5 的定义；`final/acceptance_r6.json` = r4 评审要的“格式塔”检查。
第 8 轮的定稿（主视觉 / U7 / U8 前方 / 后窗）在 `final/_superseded/r6_pre_r9/`，第 7 轮在 `final/_superseded/r5_final/`。补丁前后的对比：`final/compare_r9_patch.png`；r4 评审要的三张对比：`final/compare_r4_tear.png`、`compare_r4_light.png`、`compare_r4_multitude.png`。）

### 10.1 圣经 §6·4 + AD 的色调

| 项 | **U7**（圣经验收帧，U7b，带通用车壳） | 主视觉 `keyart_239` | U8 前方（U8 + 3.5） | 目标 | 判定 |
|---|---|---|---|---|---|
| APL | **26.4（透过玻璃 36.8）** | **35.2** | 43.0（透过玻璃 63.2；不算白 ~35） | AD：主视觉 32–36；U7 透过玻璃 33–38（§12）；圣经 U7–U8 36–42 | ✓ / ✓ / ✗（1 点） |
| luma < 12 | 29.1% | 26.4% | 18.4% | ≤ 40% | ✓ |
| 强紫（C\* > 30） | 0.01% | 0.01% | 0.03% | ≤ 10% | ✓ |
| 上 18% 的天 L\* p90 | 3.1 | 2.9 | 14.2（伤口在上面） | ≤ 5 | ✓ / ✓ / — |
| 光雾带峰值 L\* | 26.4 | 26.7 | — | 26–28 | ✓ |
| 月 L\* 最大 | 50.1（巨像 2 正盖住月） | 79.7 | 46.7 | ≤ 82 | ✓ |
| 伤口以外 L\* > 80 | **27 px** | **160 px（0.006%；第 8 轮 702）** | 1 367 px（= 占位挡风玻璃下沿的一条反光线，§13） | ~0 | ✓ / ≈ / 车壳 |
| 最亮 2000 px 在伤口里 | 100% | 100% | 100% | 全部 | ✓ |
| L\* 中位：门柱 / 手冠 / 巨像冠 / Engel / 背景巨物 / 身后光雾 | 2.8 / 15.9 / 6.4 / 2.4 / 10.6 / 22.1 | 1.5 / 16.9 / 4.2 / 2.1 / 8.7 / 22.5 | — / 14.2 / 6.1 / 24.4 / 12.1 / 24.3 | v2.3 的阶梯：近 3–6 / 巨物 9–14 / 伤口照亮的中层冠 16–22 / 光雾 22–28；远的永远不比它的天亮 | 门柱 ✓；手 ✓；巨像 / Engel 比提案暗（有意：剪影） |
| 月蚀（巨像 2 盖住月盘） | U7b 100%、+0.5 100%、+1.0 98%（`final/moon_coverage.json`） | | | “…und wollt’ mich abweisen” | ✓ |

### 10.2 r4 评审要的格式塔检查（`accept_r6.py`）

| 项 | 主视觉 | U7 | U8 前方 | U6 | 目标 | 判定 |
|---|---|---|---|---|---|---|
| 白前面臂的剪影 L\*（辉光前 p50 / PNG 上 p50 / p90） | 5.7 / 27.7 / 59.2 | 9.1 / 26.0 / 65.4 | 3.9 / 25.1 / 67.8 | — | 辉光前 p50 ≤ 15、p90 ≥ 60 | 辉光前 ✓；PNG 上 p50 ✗（S4 的 bloom，§13） |
| 白最下 5% 处的宽 / 最大宽 | 0.33 | 0.32 | 0.46 | 0.32 | 尖的脚（< ~0.5） | ✓ |
| 白的底边最长“尺子”段（列） | 4 | 8 | **18（第 8 轮 40）** | 3 | < 20 | ✓ |
| 脚下 60 px 带 L\* 标准差 / p95 | 14.5 / 70.6 | 14.0 / 68.5 | 15.9 / 71.3 | 12.0 / 58.1 | ≥ 6–8 | ✓ |
| 天之布高通标准差（1.5 个宽以内） | 4.2 | 5.0 | 5.9 | 4.5 | ≥ 6 | ✗（接近） |
| 唇外 6 px 的 C\* / 标准差 | 14.5 / 23.1 | 13.5 / 23.7 | 10.7 / 21.9 | 15.7 / 17.5 | C\* ≤ 15–18 | ✓ |
| 沿轴明度差 / 每唇暗褶段 | 17.5 / 2·2 | 17.5 / 5·6 | 14.2 / 2·3 | 16.0 / 5·2 | ≥ 18 / ≥ 3 | 接近 / U7 ✓ |
| 群臂：≥ 30 px 的成员 / 内部明度差中位 / ≥ 6 的比例 / 空出的光雾带 | 10 / 3.3 / 0% / 69% | 12 / 2.6 / 9% / 69% | 2 / 3.6 / 0% / 88% | 0 | ≥ 70% 的成员 ≥ 6；空出 ≥ 35% | 空隙 ✓；体积 ✗（§13） |
| 光路 p95 / p5 | 53.4 / 8.9 | 54.5 / 9.5 | 73.6 / 23.8 | 47.0 / 4.9 | 峰 45–60、沟 ≤ 20 | ✓（U8 前方的沟偏亮） |
| 1–3 km 云海行标准差中位 | 9.5 | 9.2 | 9.2 | 7.2 | ≥ 7 | ✓ |
| 朝月云海 p5 / p95 / 局部 σ / 月光路 | 8.0 / 49.5 / 5.1 / +13.1 | 9.0 / 48.2 / 5.3 / +10.0 | — | 6.9 / 44.6 / 3.1 / +6.3 | ≤ 6 / ≥ 50 / ≥ 8 / 看得见 | 月光路 ✓；p5、σ ✗ |
| 手的截面明度差中位（L0 / L1 / L2 / R0 / R1 / R2） | 26.9 / 36.3 / 31.4 / 10.4 / 26.0 / 3.2 | 24.7 / 37.1 / 32.5 / 9.7 / 24.9 / 29.3 | | | ≥ 12 | 5 / 6 ✓（R2 在主视觉里藏在翻布后面） |

**细臂上的环 / 珠**（技术 r4 B2）：`accept_r6.periodicity` 第 9 次运行加了 `ring_band`（最长的连续一段、小缺口补上、高通、周期 4–64 个 bin）——原来的整窗数（U8 近 36、侧 75）主要是被挡住的那几段插值成平线 + 一两处大高光，看图没有环（`wip/r9/_period.png`、`wip/r9/_c_u8side_whip.png` 拉满对比度）。`ring_band`：U8 近 Near_1 **3.4**（第 7 轮 9.8）、U8 侧 **6.6**、后窗各臂 ≤ 4.3（目标 ≤ 8）。

### 10.3 其他帧

| 帧 | APL | luma < 12 | 其他 |
|---|---|---|---|
| U6（U6 + 13） | 29.8 | 18.6% | 月 L\* 92.5（U6 时月盘还没淡：`disc_gain_keys` U7 → U7b − 1 才 × 0.6，月蚀前月是第二光源）；最亮 2000 px 89% 在伤口里 |
| U8a（U8 + 8.0） | 92.1 | 0% | 白（L\* > 80）占画面 20.3%、占天窗开口 40.6%（目标 70% ✗）；最亮 2000 px 100% 在天窗里；没有尘（`specks` 的 73 个小块都是翻布撕边的纤维，`wip/r9/_u8a_specks.png`） |
| U8b（U9 − 4） | 56.3 | 9.0% | 光斑在过道上；挡风玻璃仍是平的白 |
| U8side（U8 + 0.3） | 21.4 | 35.0% | 鞭梢的高光连续（没有“灯带”），`ring_band` 6.6 |
| U8near（U8 + 1.6） | 20.4 | 33.6% | `ring_band` 3.4 |
| 后窗（U9 − 2） | 25.0 | 43.0% | 7 条 ≥ 6% 画面宽的臂、互相交叉；手指尖各不相同（§4.7） |

**透明叠绘**（`final/fse_U8.json`，含新的 `Tear_FootSkylineIn` 0.01–0.05）：U8 **3.78**、U8 + 3.5 **3.45**、U8 + 7 **3.58**（≤ 4.0）。
**运动**（`final/motion_check.json`）：巨物 ≤ 0.49°/s、手 ≤ 0.91、群臂 ≤ 0.60、后窗组 ≤ 0.31（新的指尖不变）、远潮冠中位 0.45 / 最大 0.85；两眼顶点角速度最大 58.7°/s（≤ 60）；Hand_L1 的鞭梢离车壳 55.9 m（U9 − 0.9 s，我们自己的 ≥ 62 m 代理线没过，§13）。

### 10.4 导出核对
- `GateLayout_v2.json`：64 个实例（28 条单独的臂 + 36 条群臂）、360 片远潮、机位、`tear`（含 `foot_skyline_inner`）、`multitude.tiers`（含 `_RimLadderFloor`）、`multitude.lod_rule`。
- `GateLayout_v2.fbx`：`verify_layout_fbx.py` 按 Unity 的读法回读 64 个实例：位置误差 ≤ 5 mm、旋转矩阵误差 1.6e-6、缩放 1.7e-4。
- `GateArms_v4.fbx`：112 个物体（28 × `<id>` + `_LOD0/1/2`，后窗手指是新的指尖），~579 k 三角（三级合计）；`GateMultitude_v2.fbx`：48 个物体（12 姿态 × 4）。
- `deliver/Tear/FBX/Tear_Kit.fbx` v6.1：新增 `Tear_FootSkylineIn`，`verify_fbx.py` 通过。

---

## 11. 对两份 r4 评审的回应（第 7 轮对 r3 评审的回应在 `_r4/README_GateLayout.md` §11）

### 11.1 美术评审（`critique_awe_r4.md`）
| 条 | 评审说 | 这一版 | 同意 / 不同意 |
|---|---|---|---|
| B1.1 脚 | 蜡烛火焰立在云做的底座上；要撕开云海本身（宽的、体积的峡谷），删掉 5 张底座卡 | 底座卡删掉；透镜下半段收尖（云顶处 0.24 × 最宽）；脚前一张**云头剪影卡**（两片分开的唇 + 一道 V 口，V 尖在云面上 6 m，下面是连续的云桥），白顺着 V 流进去；峡谷底 230 m × S（`crevasse 0.9`，底色 = 白自己的雾，不是薰衣草色）；云面上的脚部光瓣只相乘云自己的起伏 | **同意方向，实现不同**：我们没有做高度场的凹槽（冒充体是投影的平面，凹槽在 U7 的距离读不出体积）；用的是剪影卡 + 峡谷底色。U8 前方仍能看到 V 尖底下一小段平的白（§13） |
| B1.2 背光的东西 | 白前面的一切都要背光（核 L\* 15–25、边 75–90） | 云头卡的边 = `_FootMist × 1.2`（离缺口越近越亮），面向车的一面是云的背光面 | 同意 |
| B1.3 褶 | ≥ 10 道放射褶，像被拉的床单 | 每个抓点 3 道**下垂**的折痕（暗面为主），门里 × 1.0；放射版（v6 / v6b）读成“日芒”与“草的排线”，所以没有用 ≥ 10 道放射线；U6 时 × 0.15（没有手时读成胡须） | **部分不同意**：放射的条数到了 10 就读成光芒（我们渲了两版），我们只要“被拉扯”的读法 |
| B1.4 翻布 | 每侧至少一片大的 | 右边一片大的（150 m、朝车剥开、盖住 ~20 m 的白），左边一片**小而高**、左手的盘绕扣住它的唇 | **不同意“每侧一片大的”**：两片对称的大翻布在 U6 读成豆荚 / 阴唇（测试图在 `wip/r6/`），不对称是故意的 |
| B1.5 线 | 不要满宽的圈 | `THREADS6`：只从一侧唇出发、断的、从不超过局部宽度 85% | 同意 |
| B1.6 支线 | 不要叶子 / 吸管 | `make_rip` v6：从根部连着、渐细、无薰衣草色；U8a 不再看到“吸管”（换到 U8 + 8.0 之后它在框外） | 同意 |
| B1.7 内部 | 薄纱不是光柱 | `VEILS6` 倾斜的柔和台阶 + 右唇里的远墙 `FAR_LIP` | 同意 |
| B1.8 光晕 | C\* ≤ 15，不要紫墙 | `#7A7B9C`、以热核为中心、唇加权；U8 起随距离淡出 | 同意 |
| B1.9 散线 | 不像胡须 | `FRAYS6`：渐细、下垂、成簇 | 同意（U8 前方近看仍是细线，§13） |
| B2 群臂 | 一片芦苇，还盖住了云塔；要 25–35 条、分层、留空 | 36 条 5 簇、3 档雾 × 0.86、近的两档有月轮廓、主臂 3:1、真的卷、镜像、云塔回来了 | 同意（36 比 35 多一条）；“成百条”的读法要靠远潮在后面撑，§13 |
| B3.1 Engel 亮条 | 第二个最亮点 | 伤口高光 × `_WoundSpecFar`（Engel 0.15）、上限 0.35、仰角 +25° 以上没有；**亮条其实是掠射角的月光高光**（关掉伤口高光它还在，关掉臂的高光它才消失；第 8 轮以为是保留的湿条纹，`_StreakKeep` 没去掉它）：第 9 次运行 Engel 的 `_ReflectionScaleFar` 0.15 → **0.01**（远距缩放后它仍有 10 线性） | 同意 |
| B3.2 白前面的臂 | 灰橡胶，要剪影 + 包边 | `OverWhite()`：表面 × 0.12、雾 × 0.4、两侧 0.9 px 白色包边 | 同意。**说明**：后期 S4 的辉光把剪影抬高 ~+15 L\*（PNG 上的 p50 ≈ 30，辉光前 ≈ 15）；评审的“p50 ≤ 15”在辉光后量做不到，除非减弱辉光（会伤到“唯一最亮点”的发光感）。我们按辉光前的数报 |
| B3.3 光路 | 没有朝观众来的光 | `Tear_LightLane` + 渲染里云头上的光路（只亮云头）；U8 前淡到 0.45 | 同意 |
| B3.4 阴影楔 | 光雾里没有阴影体积 | 4 道楔（α 0.30–0.42），从挡住伤口的手臂背后放射出去 | 同意 |
| B3.5 右近处的云 | 一块泥 | 右近处保留 62% 起伏、× 1.15 | 同意 |
| M1 尺度 | 云海到地平线、云塔、Pillar_R、巨像 2 | 远处 1–3 km 起伏保留 0.45、两侧云塔恢复、Pillar_R S 弯 + 收细到 0.7（湿亮线不明显，§13）、巨像 2 月轮廓 2–4 px + 卷尖、贴着它的群臂挪开 | 大部分同意；远方的积雨云砧没有加 |
| M2 银边 | 霓虹线 / 闪电 | 只在离月 ≤ 15° 的卡上、用模糊后的 alpha 边、塔身 × 0.85 | 同意 |
| M3 U8a | 尘、纸边、井没被照亮、吸管 | 没有尘；井的侧面被伤口照亮（L\* 40–60）、顶棚一圈 30 → 20 的光；U8 + 8.0；翻布的一角是暗布 + 亮撕边 | 同意。纸边的锯齿（贴图放大）没有改，§13 |
| M4 后窗 | 衣帽钩、比虚空亮、雾原、无窗框 | 5 根不同的手指（直线 / 反手半卷 / 分叉 / 钩 / 垂滴）、拱 S 弯 + 加粗、albedo × 0.5、雾 0.35、背带 1.25、雾原换成柔化的正面受光云海 + 远处融进带里、占位窗框 | 同意 |
| M5 近处 / 侧面 | 缆绳、环、珠 | `thinK`：环与珠都没有了（FFT 峰 / 中位数见 §10） | **“近臂身体 ≥ 250 px 宽”不同意**：近臂在 U8 + 1.6 时与眼同高的是它的中上段（粗的身体在眼睛下面 50–78°，车窗下沿挡住）；我们试了靠窗往下看（`wip/r6/near_lean*.png`）：只看到车壁和细的那一段。要看到粗的身体得把近臂做得更粗 / 更高，这会改变近层的尺度阶梯，留给 AD 决定 |
| M6 左下抓点 | 带肘的蟹腿 | 左手改成盘住左上那片小翻布的唇（t 300 / 165），右唇的盘绕保留 | 同意 |
| m1 U8b | 挡风玻璃是一块平的白；凸点像音箱网 | 凸点对比 × 0.4；挡风玻璃仍是平的白（§13） | 部分 |
| m2 纤维图集 | 像白桦林 | 弯曲交叉 | 同意 |
| m3 速度 | ≤ 1.0°/s | 群臂 ≤ 0.60 | 同意 |
| m4 Hand_R2 | 平、躲在翻布后 | 未单独处理（右翻布更大了，它更看不见） | — |

### 11.2 技术评审（`critique_tech_r4.md`）
| 条 | 这一版 |
|---|---|
| **B1** U8 前方尺子一样的脚 | 透镜尖脚 + 深而参差的 alpha 切口（Unity）；脚前云头卡留到 U9（不下沉）；叠加 CloudGlow 在脚 ±1.5 半宽内为 0（`_NearFootCut`）；渲染里 V 口的尖在云面上 6 m，云面与透镜平面的交线被唇挡住 |
| **B2** 鞭梢上的环 / 珠 | `thinK`（v2.7 + 预览材质），§5 |
| **BT-3** 天空盒与雾色对不上 | `LanbaiGateSky.cginc`，天空盒 v3 与 TentacleSway v2.7 共用（§6、§7） |
| **BT-4** MPB 片段 | §2.1 重写：Start() 每个 LOD renderer 用自己的块；群臂一个全局 `_Udon_MultReveal`；只在穿过 0 时开关 renderer |
| **M1** Engel 亮条 | `_WoundSpecFar` / `_WoundSpecMax`，渲染同（`TSPEC_FAR`） |
| **M2** 群臂是“田野” | 相位 = frac(距离 / 600)、1/6 Hz / 0.05 / 波长 1.2、一半镜像、留到 U9 − 1（第 1 组没有成员）；**没有做 MU6 分叉姿态**（卷 / 伸 / 落三族 + 镜像已经 12 个网格） |
| **M3** 后窗 | 见 11.1 M4；`_RimPxMoon 1.5`、`_Color 0.5`、`_FogDensityScale 0.35` |
| **M4** U8 的边与光晕墙 | 光晕距离淡出（重映射后 U8 0.47、U8 + 3.5 起为 0）；纤维带断开（≤ ~50% 亮） |
| **M5** 预深度 pass、淡到 0 不关 | 顶点阶段裁掉；`renderer_off_at_zero`；`gate_fse.py` 把透镜预深度单列（§9） |
| **M6** 修订 v2.3 不全 | §12 补了深度阶梯、光晕 C\*、速度、撕裂速度、光滑度、U8 APL |
| **M7** U8a | 见 11.1 M3；ID 渲染里天窗玻璃 / 光柱 / 光圈都算透明（m12） |
| **M8** 张力褶看不见 | 见 11.1 B1.3；`skyfolds` 1.0 |
| m1 光滑度 | 写进 v2.3（§12）；不批就一行映射 |
| m3 头注释 | 改了 |
| m4 “退回 v2.5”的说法 | 改成 `WoundOn()` 关掉（shader + README） |
| m5 光晕项 | v6 三张卡、以热核为中心、× 距离淡出（cginc） |
| m6 背带 | 在 cginc 里，65 → 120° |
| m7 时间 | 群臂与手的显现从 U6 + 14 起；群臂在 U7 … U7b + 6 还在涌。**巨像 1 的“先竖直出云”没有做**（§13） |
| m8 群臂速度 | ≤ 0.60（藏起来的那一段先升） |
| m9 撕裂速度 | v2.3 改成 ≤ 16 m/s |
| m10 占位车壳最亮 | 侧面两帧的车壳漆暗到 `#6A675F`、灯管 0.18；雨刮 roughness 0.55 |
| m11 退役贴图 | `Textures/_retired~/` |
| m12 U8a ID | 修了 |
| m13 目的地牌亮度 | 两边都以**屏幕 L\* 6–8** 为准：渲染里车里那一面的发光 × 2.3（原来 L\* ~3）；README §8.5 的写法改成屏幕目标（发光 `#12151C` 左右，原来的 `#1A1E28` ≈ 11.6 偏亮） |
| m14 纤维带颜色 | +6 L\*、b\* −5 |
| m15 朝月云 | 渲染不变（去饱和 0.7、gamma 1.35）；Unity 一侧的写法见 JSON `clouds.round4_grade` |
| m16 A 柱挡住里尔克线 | 仍开放（等真车） |

## 12. 圣经 §6·4 修订提案 v2.3（第 8 轮补全；**待用户与美术总监批准**，未改动圣经原文）

以下是这一版**实际用的值**与圣经表的差别。美术 r4 §4 已经**批准**了色调几行（主视觉 APL 32–36、U7 透过玻璃 33–38、光雾带 (6, 22, 2)）和“最宽在 40–47%”；“群臂替代主角窗口的远潮”要等 B2 的验收过了才批。技术 r4 M6 指出 v2.3 漏了几条，第 8 轮补上（标 ◆）：

| 项 | 圣经 v2 | 本布局 | 理由 |
|---|---|---|---|
| 中层 | 24–40 条、100–250 m、离脚 400–900 m | 两只手（6 根手指，626–1 159 m） | “少数巨大的 + 很多小的，没有中号的”；中号的臂读成一丛植物 |
| 很多小的 | 远潮 300–500 条、5–12 km、雾 80–92% | **群臂 36 条 3D 臂，5 簇**（3.2–5.6 km、主臂 500–650 m、雾上限 0.39 / 0.50 / 0.60）+ 远潮 360 片在后面 | 第 7 轮的 150 条同质群臂读成“芦苇”（美术 r4 B2）；这一版要的是层次与空隙 |
| ◆ 很多小的：速度 | ≤ 0.3°/s（远潮）；巨物 ≤ 0.5°/s | 群臂可见部分 **≤ 0.6°/s**（实测最大 0.60）；摆动浪尖 ~0.38°/s；手 ≤ 0.93°/s（手在 0.5–0.6 km，按中层算） | 0.3°/s 时 U7 起升的臂在主角那一刻还在云下；美术 r4 m3 接受 ≤ 1.0 |
| 近层 | 25–72 m | 150–202 m | 8–20 m 处 25–72 m 的臂只看得到一截 |
| 巨像 | 300–450 m | 门柱 1.0–1.3 km、Engel 2.8 km、背景 1.1–1.4 km、巨像 1 0.65 km、巨像 2 1.1 km、后窗组 1.4–2.3 km | 公里外 400 m 的东西只有指甲大 |
| 雾上限 | 0.6、高度 500 m | 0.92、5 000 m（远层）；显现用 `_Reveal` | 0.6 时巨物是比天亮的鬼影 |
| 远潮雾 | 80–92% | 48–58% | 按圣经数远潮完全看不见 |
| ◆ 深度阶梯 | 远 10–16 → 中 18–26（L\*），每级 ≥ 8 | **近 3–6 / 巨物 9–14 / 被伤口照亮的中层冠 16–22 / 光雾带 22–28**，每级 ≥ 6，远的永远不比它的天亮 | 圣经的阶梯在“伤口是主光”之后是倒的：巨物冠 9–14 在手（20）之下（技术 r4 M6 的措辞） |
| ◆ 光晕 C\* | 45 | 0–1° ~25、1–4° 13–20，**唇外 6 px ≤ 18** | 两份评审都要求“不要紫墙”（美术 r4 B1.8 要 ≤ 15） |
| ◆ 裂口顶撕裂速度 | ≤ 0.5°/s | **≤ 16 m/s**（H(U7b) 640 → H(U8) 799 固定时 0.5°/s 需要 ≤ 12.8 m/s，做不到；实测 16.1 m/s = 0.60°/s） | 技术 r4 m9 |
| ◆ 触手光滑度 | 0.70–0.90，湿条纹 0.90，干 0.72 | 贴图 A 0.52–0.81（中位 0.62）；细的部分 0.84（`_ThinSmooth`） | 对“塑胶 / 乙烯”评审的有意回答；不批的话 shader 一行映射回去（§5） |
| ◆ U8 前方 APL | ≤ 42 | **≤ 42，不算白自己的像素**（伤口占 ~7% 画面、贡献 ~14 APL） | 技术 r4 §2 |
| U7 验收 APL | 36–42 | 主视觉 32–36（AD）；U7 透过玻璃 33–38 | **已批**（美术 r4 §4） |
| 光雾带仰角 | +15° 以上渐回虚空，+35° 虚空 | (6, 22, 2)：+13° 0.32、+20° 起是夜 | **已批** |
| 裂口最宽处 | 40% H | 40–47% | **已批** |
| 后窗 | 只有轮廓光 | 只有轮廓光（身体比虚空暗、朝月 1.5 px 冷边）；月之光环删掉；后窗组在 \|方位\| ≥ 138° 才显现 | AD 5 |
| 月蚀 | 挡到之后只剩银晕 | 100% 只有 ~1.5 s，之后 Udon 淡出月盘、月晕核心 × 0.35 | 视差 |
| GateRoot 激活 | — | U6 − 20 s，巨物已站好 | 技术 B1（r2） |

---

## 13. 已知问题 / 还弱的地方（诚实版，第 9 次运行）

1. **640 px 的“陌生人测试”**（主视觉缩到 640 宽，一句话）：*“夜空里被撕开的一道发光的口子，下面是云海；巨大的黑触手从两边拱过来，两根在光前交叉、一根缠住口子的边；远处云塔之间还站着更多弯着的臂；左边低处一个月亮。”*
   不再出现“蜡烛 / 火焰底座 / 角 / 芦苇 / 草 / 獠牙”。**但白本身在 640 px 仍是一片竖着的叶形 / 透镜形**（圣经要的 45/55 透镜就是这个形），“布被撕开”要到 1:1 才读得出（翻布、断纱、撕裂支线、褶）。“成百条”这个词也说不出来：群臂是左右云塔之间几道暗的弧。
2. **群臂的体积**：内部明度差中位 3.3（主视觉）/ 2.6（U7），评审要 70% 的成员 ≥ 6。第 9 次运行修了两处真问题（远处轮廓阶梯把月轮廓吃掉了 → `_RimLadderFloor`；主臂是 LOD2 的折角 → 按屏幕高度选 LOD），但 1 px 的轮廓被测量里 2 px 的腐蚀量掉，眼睛看到的改进也很小（`compare_r9_patch.png` 第 3 行）。它们读成雾里的剪影弧，不读成圆的。
3. **白前面的剪影**：辉光前 p50 4–9 L\*（✓），PNG 上（S4 的 bloom 之后）p50 25–28（评审要 ≤ 15）。要在 PNG 上过线只能减弱 bloom，白就不“发光”了。
4. **天之布的褶**：高通标准差 4.2–5.9（目标 ≥ 6）；褶在 1:1 看得见，640 px 读不出“被拉开的床单”。
5. **U8 前方的脚**：尺子段 40 → 18 列（✓），白收在一排低的背光云头上；但那排云头整体仍近乎水平，两片 V 唇是光滑的灰色云团（近看像软石头），不是有体积的峡谷。U8 前方 APL 43.0（> 42；不算白约 35）。
6. **U8 前方的反光线**：伤口以外 L\* > 80 的 1 301 px 是占位车壳挡风玻璃下沿的一条细反光（第 8 轮以为是雨刮，不是）。真车壳来了以后在 Unity 里看。
7. **U8a**：白占天窗开口 40.6%（目标 70%）；右下角是 Engel 盘绕的一段弧；天窗里放大后伤口的唇有锯齿（2048 宽的发光贴图）。开口里看到什么只由眼位和时间决定（俯仰 / 视角不改变它），U8 + 8.5 时盘绕成了黑轮胎（第 8 轮试过）。
8. **U8near / U8side**：近臂与眼同高的是它细的中上段，读成“缆绳”；两帧都偏暗（luma < 12 约 34–35%）；最亮的是占位车壳的 B 柱。
9. **U8b**：挡风玻璃里是一块平的白。
10. **Pillar_R**：S 弯、收细做了；长的湿亮线（L\* 25–40）**试了没用**——物理上背光柱子朝向我们的那面照出的是黑的天，加一项“反射身后云原”只在右下边缘出几块像雪的斑（`wip/r9/pil_w*.png`）。按 AD 第 3 条“近处柱子近黑、有边光”保留。
11. **后窗**：手指尖现在各不相同（S 鞭梢 / 半卷 / 卷 / 分叉），读成“一只触手的手在身后合上”；但云原仍是柔化的灰雾，不是正面受光的银色云原；右边两条臂凸面上有短的暗色皱纹，近看像划痕。
12. **U6**：月 L\* 92.5（月蚀前、月盘还没淡，`disc_gain_keys` 的设计）；伤口仍是最亮的（L\* 96–98），但最亮 2000 px 只有 89% 在伤口里。
13. **巨像 1（里尔克那一拍）**：仍按 ≤ 0.3°/s 斜着出云，U6 + 13 只露 ~30 m（评审要竖直出云、70–80 m）。
14. **Hand_L1** 的鞭梢在 U9 − 0.9 s 离车壳 55.9 m（我们自己的 ≥ 62 m 代理线；眼角速度 58.7°/s ≤ 60 满足）。
15. **没做的**：远方积雨云砧（美术 M1.2）、朝月云海 p5 ≤ 6 / σ ≥ 8（现在 8.0 / 5.1）、A 柱挡住里尔克线（等真车）、发光贴图 4096 宽的唇（U8a 的锯齿）。
16. **Unity 里才验得出的**：BT-3 的“开 / 关雾 ΔL\* ≤ 1”；`OverWhite()` 在头显两眼里的一致性；`Tear_FootSkyline` / `Tear_FootSkylineIn` 的 `_SkyCloud` 要与 CloudSea 卡一样，否则看得出卡；`Renderer.GetPropertyBlock` 是否在 Udon 白名单里；`_RimLadderFloor` 在 VR 里 1 px 的远处轮廓会不会闪（如果闪，降到 0.3 / 0.2）。
17. **shader / C# 都没在 Unity 编译**，只过了 slang 的语法 / 类型检查（TentacleSway v2.7c 三个 pass、GateAirSky v3、Tear v6 十一个部件 + 两种预深度 pass；Tear v6.1 没改 shader）。
18. 车高、近层长度、巨物尺寸、群臂与远潮、速度、深度阶梯、光滑度都偏离了圣经表（§12 的修订提案 v2.3，**待用户与 AD 批准**）。车壳仍是通用占位（U7 / U8 的整帧 APL、天窗位置、目的地牌位置都要等真车再定）。
