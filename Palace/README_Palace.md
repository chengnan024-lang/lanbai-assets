# 第 7b 幕 · 河伯宫殿套件（`Palace/`）· 给 Unity 一侧的说明

写的人：云端会话「宫殿」（分支 `pkg/palace`）。对象：小楠电脑上 Unity 2022.3 的那一侧，以及组装第 7 幕的「海」。
**本目录里的 C# / shader 都没有在 Unity 里编译过。** 检查做法见 §7（DXC + Unity 2022.3 CGIncludes、Roslyn + U# 规则）。

## 0. 先做这几步（拷什么、点什么、截什么图）

1. 把 `Palace/` 拷到 `Assets/Lanbai/Palace/`（要有 `Assets/Lanbai/Common/`、`Assets/Lanbai/GateClouds/`（搭建脚本借它的 U# 工具）、`Assets/Lanbai/Act07_Sea/`）。
   `Source/`、`Docs~/` 不需要进 Unity（`Docs~` 本来就被忽略；`Source/` 是 Python，可以不拷）。
2. Project Settings → Player → **Vertex Compression：TexCoord0–3 不压缩**（鱼的编号在 uv2 里，CONTROL §6 第 8 条）。
3. 先跑 `蓝白/Build/Act07a`（海），再跑 **`蓝白/Build/7b 宫殿`**：`R_Palace` 会挂在 `R_Sea` 下（局部位置 (0, −250.335, 0)），驱动 `LanbaiPalaceDriver` 放在场景根上。
4. **烘焙**（§4）：只开宫殿的烘焙灯，Environment Lighting = Trilight 7b 的三个色，Bake。
5. Director 的分发表里加 `LanbaiPalaceDriver`（时间窗 643.96 → 876.16）。
6. 截图推回 `FromLocal/07b_test/`：主座位 (0.55, 1.70, 2.05)、桌面 1920×1080、水平 90°、PPv2 开（S7b）：
   **t = 655.86（F5p）、690、706、735.56（F6）、748.26（F7）**；另 F7p **812.36** 抬头向左上（yaw −25°、pitch +42°）一张。
   每张对照 `Docs~/iterations/` 里同名的参考图。

## 1. 文件

| 文件 | 是什么 |
|---|---|
| `PalaceLayout.json` | **唯一的数据源**（= 海的 `Act07_Sea/PalaceFrame_约定.json` + 宫殿的灯、门、灯焰、鱼、烘焙参数）。宫殿坐标：米、Unity 轴，x = 0 车路、y = 0 台地顶、z = 0 F5 时的车根 |
| `Models/Palace_*.fbx` | 网格（顶点就是宫殿坐标，挂在 R_Palace 下不动）。`*_LOD0` / `*_LOD1`，搭建脚本建 LODGroup。`tri_counts.json` 是三角形数 |
| `Textures/T_07b_*` | 5 套 2048²（漆、鱼鳞瓦、宝贝、石、铜：Albedo / Normal / Mask）+ 梁枋云气纹带 + 灯焰 8 帧图集 + 灯晕 |
| `Shaders/Lanbai_Palace.shader` + `LanbaiPalace.cginc` | 宫殿的不透明材质（光照贴图 + 8 盏解析宫灯的 GGX 高光 + 淤泥 + 珍珠母虹彩 + 宝贝视差 + 海草摆动 + LanbaiFog + `_Udon_PalaceVeil`） |
| `Shaders/Lanbai_PalaceFlame.shader` | 灯焰序列帧 + 灯晕卡（公告板，加色，`_FogMode 2`：exp(−0.004 d)，不吃雾、不吃 veil） |
| `Shaders/Lanbai_PalaceGlow.shader` | 门里的暖光（不透明）与门口的 3 张锥形光卡（加色） |
| `Shaders/Lanbai_PalaceFish.shader` | 1 500 条银鱼，一张合并网格、顶点里算运动（与 `Source/kit/fish.py` 同一套数学） |
| `Editor/LanbaiPalaceBuilder.cs` | 菜单 `蓝白/Build/7b 宫殿` |
| `Editor/LanbaiPalaceData.cs` | 生成的数据（`Source/gen_layout.py`），不要手改 |
| `Editor/LanbaiPalaceImport.cs` | 导入设置（只管 `Assets/Lanbai/Palace/`） |
| `Runtime/LanbaiPalaceDriver.cs` | U# 驱动：最近的 8 盏宫灯写进 `_Udon_Lamp0..7`；鱼的 lite |
| `Docs~/ref_boards/` | 分区参考板（屋顶、纹样、颜色）+ 出处 + 可能时代错位的清单（D-31 #2） |
| `Source/` | 生成一切的 Python（bpy 5.0.1）：布局、模块、贴图、FBX、参考渲染与后期 |
| `Docs~/` | 考据、lookdev brief、迭代图、评审稿 |


## 2. 坐标、父子关系、运动

- **宫殿坐标** = 海的约定：米、Unity 轴；x = 0 是车路，y = 0 是台地顶，z = 0 是 F5（644.96）时的车根。所有网格的顶点都在这个坐标里，所以 FBX 实例化在 `R_Palace` 下、局部变换为单位。
- `R_Palace` 是 `R_Sea` 的子物体，局部位置 **(0, −250.335, 0)**（= 海的 `terrace_top_depth_m`）。海的驱动让 `R_Sea = (0, depth(t), −fwd(t))`，所以 `R_Palace` 的世界位置 = −busPos(t)（海的约定 `frame.placement`）。**宫殿自己不动任何根物体。**
- 车停在台地顶上方 2.5 m（眼睛 4.2 m），宫灯的火在车地板以下：每对灯的光“从下面来”。车沿 x = 0 滑行，台地崖口在 x = −8（眼睛到石壁 8.55 m），右列灯 x = −9，左列 x = −27，神道轴线 x = −18，殿门在轴线上。
- 殿门方位（从主座位眼睛量）：706 s −6.3°、714 s −7.6°、F6 −16.2°、F7 −29.2°（海按车根量是 −27.0°；差别写在 `给总控.md`）。D-28：PAZ-672 的挡风中柱约在 −21°，F6 → F7 时殿门从中柱后面经过一次，停在它左边。
- 时刻（圣经 v2.1 §2.1；`cues.json` 里还没有 F5p / F5q / F5r / F7s / F7p，本地加进 `F_sub` 以后按标签取）：F5 644.96、F5p 655.86、阙 668.6、12 对灯 672.0 … 728.6、F6 735.56、刹停 740.26 → F7 748.26、F7s 796.86、F7p 812.36、F8 835.16、热点结束 875.16。

## 3. 材质（`Lanbai/Palace` 一个 shader，按槽配参数；搭建脚本建 `Materials/M_07b_*.mat`）

| 槽 | 反照率（§6·7b 表） | 光滑度 | 金属 | 说明 |
|---|---|---|---|---|
| Lacquer 朱漆 | `#A3201E`（贴图均值 `#A0201E`） | 0.80 | 0 | 刷痕；磨损处露黑漆底 `#282426`（掩码 R） |
| LacquerBlack 黑漆 | `#282426` | 0.75 | 0 | 黑漆例外 ≥ 38 |
| LacquerBand 梁枋带 | 黑底 `#2A2527` + 朱绘云气纹 `#9C2A1F` | 0.78 | 0 | 楚漆卷云，UV 沿梁 4 m 一个周期 |
| Gilt 鎏金 | `#C9A56A` | 0.60 | 1 | 门环、柱头箍、灯盘沿 |
| Bronze 青铜 | **`#BA926A`**（D-29） | 0.55 | 掩码 R | 铜绿 `#3E7A68` / 暗化 `#3A332A` 处金属 0（D-29：暗处按电介质） |
| Stone / StoneDark 石 | `#3B3F3A` / ×0.8 | 0.30 | 0 | 条石错缝 |
| FishScale 鱼鳞瓦 | `#CFCBC4`（均值 `#C9C5BE`） | 0.86 | 0 | 珍珠母：高光颜色 = f(N·V)：`#E7C9D5` → `#C3E3D5` → 掠射 `#B9C6EA`（`_Mode` 2）。鳞是拱起的圆头（法线倾角 p10–p90 = 10–33°，第 8 轮；之前的法线贴图几乎是平的）。**珍珠光的 smoke and mirrors（第 8 轮）**：灯在檐下、眼睛在屋面高度，屋面不可能镜面反射到灯；所以珍珠母的解析高光按“往上挪 `_NacreLift` 12 m 的灯”算、瓣放宽 `_NacreSpread` 0.06，`_LampGain` 24——灯经过时檐口的鳞上滚过一串珍珠光。别的材质不挪 |
| Cowrie 宝贝 | `#5B2A4E`、背斑 `#B89AB0` | 0.92 | 0 | 8 步视差（高度 1.5 cm，40 m 外淡掉，`_Mode` 3） |
| Tile 瓦 | 石的贴图 × `#F2F8FF` | 0.35 | 0 | 淤泥 0.7 |
| Rock 岩 | `#33362F` | 0.22 | 0 | `_LipFade` 5：从下面看下缘溶进水色（D-29） |
| Weed 海草 | `#2E3A26` | 0.55 | 0 | `_SwayAmp` 0.25 m、0.15 Hz（uv3 = 高度、相位），两面 |

**淤泥**（所有槽，按 `_SiltAmount`）：朝上的面（法线 y 0.55 起、0.85 满）× 世界坐标的值噪声，`#5E6259` / 光滑度 0.10，覆盖四到七成（圣经 §6·7b）。**高光** = 离眼睛最近 8 盏宫灯的解析 GGX（`_Udon_Lamp0..7`），漫反射 = 光照贴图。

## 4. 烘焙（本地做）

1. `蓝白/Build/7b 宫殿` 之后，`R_Palace/Palace_BakedLights` 下有 **62 盏 Baked 点光**（每盏宫灯一暖、林荫道的灯另加一靛）+ **2 盏 Baked 聚光**（门口朝外一盏、门前 7 m 朝门一盏，第 8 轮从面光改来：面光没有范围，把整面立面描成朱红，阴影发暖）。它们只照宫殿：烘焙时把别的幕的烘焙灯关掉，或用单独的烘焙场景。
   - 暖：`#FF9C2F`，range 4，**Inspector 强度 5.46**（D-00：Inspector = E；点光在 d 处 E = I × (1 − (d/r)⁴)² / d²，所以 2 m 处 E = 1.2，圣经 §6·7b 的校准），软阴影、半径 0.1。
   - 靛：`#2A557B`，range 12，强度 28，**放在灯焰上方 4 m**（水体散射的近似：灯旁仍读成金朱，8 m 外落到靛；第 3 轮定的），无阴影。
   - **门的提亮光 `DoorAccent_BakeOnly`（D-31）**：门前 7 m、朝门的聚光（70°、range 11、强度 70），`#FFD9A0`，只参与烘焙。它把门那一开间（门两侧的柱、门楣、斗拱、门前台基面）托出来，让亮着的空门是眼睛第一个落上去的地方。烘焙完可以关掉或删掉（光照贴图里已经有了）。
   - 门 `DoorSpill`：`#FFB74D` 的聚光，门面外 0.3 m、高 0.55 门高（门扇在它身后，读成光前面的暗剪影），朝外略向下，90°、range 4、强度 60（只照门槛和门口那几步；台基上“铺开的光”靠门的解析线光源在湿石面上的高光，评审 r3 #3）（`PalaceLayout.json` 的 `door_spill`）。聚光和点光一样是 InverseSquared + 范围窗，Blender 的参考渲染按同一个式子，单位对得上。
2. Lighting → Environment：**Source = Gradient（Trilight）**：天 `#0E3050`、赤道 `#0A2238`、地 `#1A1422`（圣经 §6·7b；环境光因此在光照贴图里）。
3. Lightmapping Settings：Progressive、Lightmap Resolution 4 texel/m（渲染器各自的比例已由搭建脚本设：灯 2、阙 0.8、殿 / 屋 0.6、海草 0.5、台地 0.25）、Bounces 2、Directional 可选。Falloff 用 **InverseSquared**；若你们的不是，按下表校。
4. **灰卡核对**（0.5 m 方片，albedo `#767676`、smoothness 0，S7b 调色，雾关或在 1 m 内拍）：截图读数应在 ±10 码内。

| 位置 | 说明 | 坐标（宫殿系） | 截图应读到 |
|---|---|---|---|
| lamp_2m | 右列第 1 盏灯（Lamp_R01）的灯焰旁 2 m、同高、正对灯焰 | (-7.00, 1.62, 54.39) 法线 (-1, 0, 0) | `#6E432D` |
| lamp_8m | Lamp_R01 灯焰后方 8 m（+z）、同高、正对灯焰 | (-9.00, 1.62, 62.39) 法线 (0, 0, -1) | `#010A16` |
| avenue_floor | 第 1、2 对灯之间的神道正中（铺石面上，朝上） | (-18.00, 0.13, 63.30) 法线 (0, 1, 0) | `#01060E` |
| door_floor | 殿门前 3 m 的台基面（朝上） | (-18.00, 6.01, 339.60) 法线 (0, 1, 0) | `#020C1A`（第 8 轮：门的漫反射只照门槛和门口 4 m 内；台基上的亮带是门的解析线光源的高光，灰卡 smoothness 0 量不到） |
| que_wall | 右阙阙身正面、它的灯（Lamp_Q1）旁 1 m、高 4 m | (-11.00, 4.00, 36.38) 法线 (0, 0, -1) | `#6E6279`（暖 + 靛在灰卡上；宝贝贴面上是紫） |
| stair_foot | 台阶脚下 2 m 的地面（朝上） | (-18.00, 0.13, 323.00) 法线 (0, 1, 0) | `#312214` |

（量法：`Source/calib_cards.py`。与圣经的差别：圣经写“8 m 处灰卡 `#001325`（E 0.6）”，我们读 `#010A16`——照圣经的数做，灯旁 2 m 的灰卡会被靛光压成偏蓝，和同一节“灯旁的表面读作金朱”矛盾；我们选“灯旁金朱”。写进了 `给总控.md`。）

## 5. 驱动 `LanbaiPalaceDriver`

- 时间窗 643.96 → 876.16。`LanbaiTick(t)` 每帧把离主座位眼睛最近的 8 盏宫灯写进 `_Udon_Lamp0..7`（xyz 世界位置、w = 5.46）、`_Udon_LampColor0..7`（`#FF9C2F` 线性、a = 0.1 m）、`LampDir`（全向）、`LampAxis`（0）。离开时间窗的那一帧写一次 w = 0。
- `lite`（Director 的 auto-lite）：鱼 1 500 → 700。
- **从 t 单独重建（D-33 #6）**：没有跨帧状态。每帧整组重写 8 盏解析灯（第 8 盏是殿门：竖直线光源），激活那一帧补写鱼的数量；鱼、灯焰、海草只读 `_Udon_T`。拖时间轴、迟到的人进来，第一帧就对。
- 不写：R_Palace 的位置、`_Udon_PalaceVeil`（海写）、`_Udon_T`（海写）、PPv2。

## 6. 参考渲染与量出的数

`Docs~/iterations/NN_*/`：每轮的图（PPv2 S7b 调色后）、`metrics.json`、`note.txt`。渲染：`Source/scene.py`（Cycles，烘焙灯按 Unity 的 InverseSquared + 范围窗，灯组分开）→ `Source/post.py`（LanbaiFog 式 Exp 雾 0.018、方向水色、`_Udon_PalaceVeil`、崖口下缘的溶解、门光 / 灯焰 / 灯晕按 `_FogMode 2`，然后 S7b 引擎参数 + bloom，Grading 的 `ppv2_engine.py`）。车壳 = `pkg/bus` 的 `Bus_HarnessShell_paz672.fbx`（第 7 轮起；拿不到时退回标准台 `bible_v2`）。

## 7. 检查（不是 Unity 编译）

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Palace/Shaders` → `5 files, 102 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`
- C#：`bash Common/Tools~/compile_check/check_cs.sh Palace GateClouds`（搭建脚本借 GateClouds 的 U# 工具）→ `C# CHECK OK (0 assembly error(s), 0 lint warning(s)).`
- 网格：每个模块的封闭 / 法线朝外测试（`kit/hall.py` 的 `check()`、`kit/que.py` 的 `check_closed_outward`）全过；唯一“不封闭”的是门后暗腔的发光内衬（故意朝里、前面敞开）。FBX 用 Blender 导回核对过 UV 层（海草 3 层、鱼 2 层、灯焰 2 层、远处灯点 3 层）。
- **都没有在 Unity 里编译或运行过。** 第一次跑时请把 Console 的报错原样推回 `FromLocal/07b_test/`。

## 8. 与评审的分歧（`Docs~/review_art_r3.md` 的 7 条阻断：第 4 轮逐条改；`review_art_r5.md` 复核没过的，第 8 轮再改；下面是没有照字面改的）

1. **门扇**：门后整个暗腔是发光内衬，门扇衬在光前面。第 8 轮查出参考渲染的一个错：内衬的一半没进 doorglow 灯组，后期把它涂黑了（评审看到的“两团黄斑中间露出黑的室内几何”）；修好以后门洞整个是光。门口的溢出光挪到门面外 0.3 m，门扇在它身后，读成光前面的暗剪影；D-31 的提亮光仍把朝外那扇的边照出一点朱红。
2. **门口光卡**：α 0.03（圣经 0.06 在这套光下读成实心光柱）。
3. **F7p / F7pb 的“30 盏灯在头顶”**：参考图取 F7p + 4 s。从台地下面看，灯排正好压在崖顶的剪影线上（眼睛在台地顶面以下 19 m，灯在 60–270 m 外、仰角 5–20°），几十厘米的崖边会把火吃成断续的虚线、把晕切成半月。第 8 轮的 smoke and mirrors：眼睛在台地顶面以下时，火和晕的深度测试往眼睛挪 min(0.25 d, 40 m)，晕没有靛环（只剩暖芯），所以沿崖边是一串稳定的暖点；远在台地后面的灯（挡住它的岩体比这厚）照样被挡。平时（眼睛在台地上方）晕往眼睛挪 min(4 m, d/2)：晕是灯和眼睛之间那段水的散射，不该被栏杆、柱子切成半月。
4. **APL**：见 §9 第一条。
5. **珍珠母的珍珠光**：物理上做不到（灯在檐下、眼睛在屋面高度，屋面的镜面方向朝上），用“挪高的镜中灯”（§3 FishScale 行）。
6. **阙前的灯**：圣经的灯是 1.85 m；阙基 3 m 高，矮灯照不到宝贝贴面，阙前这两盏做成 3.85 m 的立灯，靛光不抬高、范围 5 m——暖 + 靛只在灯旁混成紫。

## 9. 诚实的已知弱点

- **没在 Unity 里跑过**：烘焙结果、面光单位（Blender 的瓦和 Unity 面光的强度没有对上，按 §4 的灰卡校）、`Lanbai/PalaceFlame` 的最小像素放大、鱼的顶点运动，都只在云端模拟过。
- **车壳用的是 `pkg/bus` 的渲染壳**（PAZ-672）。F7 门在中柱后面（D-34 #5）：两个 −40° 研究在 `Docs~/iterations/07_F7_minus40_paz672/`，推荐 B（路径右移 9.35 m），门 / 车关系**待海确认**。
- **APL**：第 8 轮的参考图用 `pkg/bus` 的 PAZ-672 车壳，按圣经 §6·7b 侵蚀 0.25、车厢只吃 `#0F1E30` × 0.3（`Source/bus_erosion.py`，照抄车的 `scene_acts.py` 的侵蚀场）。车厢在 7b 几乎是黑的、占画面 43%，所以全帧 APL 12–12.3（F5p、F6、F7），**车窗里的部分 16–17**（圣经 F5 的目标 16）。水色已经在圣经的 `#04121E`。我没有为了全帧 APL 把灯调过校准；要回到 13 以上得动 S7b 的 postExposure（约 +0.2 EV，在 §1.5 的 ±15% 里），归调色 / 总导演（`给总控.md` 第 9 条）。
- 宫殿离灯 8 m 以外基本读不出形，只有屋脊剪影和灯——这是圣经“用灯来量尺度”的意思，但在头显里可能嫌太黑。
- **第 8 轮修的交付错**：`Palace_Lamps.fbx` 里林荫道的灯此前被转了 ±90°（屏板开口顺着神道，不朝神道中线；参考渲染一直是对的），已重导出。
- **宝贝贴面**只有贴图 + 视差，没有几何浮雕；阙身中段在远处是一块平的暗紫。
- **鱼**：参考图里很小、几乎看不见（1 500 条 12–20 cm 在 35 m 外是亚像素）；“转身穿过灯光时闪”只有解析高光，没有专门的闪烁项。
- **鳞片头**在 LOD1 去掉了，80 m 外屋檐读不出“鳞”。
- **右平（坡道）没做**；台基面没有铺地砖纹。
- **银鱼的 B 群**（720 s 从诗前面游过）是一条直线经过，之前和之后都在很远的雾里；没有和环面上的鱼群接起来。
- **远处灯点** `PalaceSpecks_Points.fbx` 按海的 `Lanbai/SeaSpecks` 的网格约定做，搭建脚本不摆它（海摆，第 7、8 幕都用）。
- `Rain/Shaders/LanbaiLamps.cginc` 与 `LanbaiGlobals.cginc` 冲突，宫殿自己写了一份解析灯（`给总控.md` 第 5 条）。

## 10. 素材来源（CC0，照小楠的话“合适直接用”）

- 朱漆 `T_07b_Lacquer_*`：克利夫兰美术馆 **1969.129**（乐浪出土漆盘残片，新莽 9 CE）内面的一块，去光、无缝、均值校到圣经 `#A3201E`，剥落处做磨损遮罩（`Source/tex/from_photos.py`）。
- 梁枋带的云纹按克利夫兰美术馆 **1991.7**（西汉漆耳杯）的笔意程序生成；照片里的纹样带是弯的，这一窗没拉直。
- 屋顶的形制对照大都会博物馆 **49519、49520**、克利夫兰美术馆 **1989.71** 的东汉陶楼（`Docs~/ref_boards/01_roof.png`）。
