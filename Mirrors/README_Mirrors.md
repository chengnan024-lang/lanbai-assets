# 十三面白铜镜 · 镜子套件（第 9 幕 9c）+ 时间表 · README

写的人：会话「镜与白」（分支 `pkg/mirrors`）。对象：本地（Unity 2022.3.22f1 + VRChat SDK Worlds 3.10.5 + PPv2 3.4.0）与第 9 幕的组装（「天空」）。
**本目录的 C# 和 shader 都没有在 Unity 里编译过。** 做过的检查见 §7。第 10 幕（白）的包在 `Act10_White/`，见那边的 README。

## 0. 先做这几步

1. **拷**：`Mirrors/` → `Assets/Lanbai/Mirrors/`（`Tools~`、`Docs~`、`Source/` 不会被 Unity 导入，拷了也没关系；`Source/BronzeMirror.blend` 不用拷）。依赖：`Assets/Lanbai/Common/`（`LanbaiGlobals.cginc`、`LanbaiSky.cginc`、`LanbaiFog.cginc`、`LanbaiVR.cginc`）和 `Assets/Lanbai/Sky/`（星点网格 `Sky/Generated/StarPoints_BSC5.asset`、银河图 `Sky/Textures/StarSky_Glow_8192x4096.png`）。
2. **点**：先跑天空的 `蓝白/Sky/Build Star Mesh`、`蓝白/Sky/Build Sky`、`蓝白/Build/Act09`，再点 **`蓝白/Build/Mirrors`**（可重复运行：先删上一次的 `R_Mirrors` 与 `Lanbai_MirrorsDriver`）。然后 `蓝白/Director/1 Generate Dispatcher`、`2 Wire Scene`。
3. **截图推回**（`FromLocal/mirrors_test/`，桌面 1920×1080、水平 FOV 90°、主座位眼位）：t = 1030.4 正前方偏下 12°、1030.4 向下看 −60°、1113.4 正前方偏下、1116.0 抬头 +30°、1123.5 正前方偏下、1136.6 正前方偏下、1142.0 向下看；外加 §1.8 录像窗口 (g)：1119 → 1150 正前方与向下看各一段 60 fps PNG 序列（跑 `flashcheck.py`）。和 `Docs~/iterations/r2_*.png` 对照（同一时刻、同一视向，只差车厢）。

## 1. 有什么

| 文件 | 是什么 |
|---|---|
| `MirrorSchedule.json` | **唯一数据源**：十三面镜的两段时间表（圣经 §6·9 定稿 E20）、每面镜的穿越时刻 / 直径 / 方位 / 镜心 / 最近镜缘距离 / 行进与穿越速度 / Hermite 运动节点 / 可见度 / 溶解 / 脉冲。生成器 `Tools~/schedule/make_schedule.py`（从 `FromLocal/cues.json` 算），核对 `Docs~/schedule_check.txt`（全部 PASS）、图 `Docs~/schedule.png` |
| `Models/BronzeMirror.fbx` | 单位直径的博局镜（根 `BronzeMirror` + `_LOD0/1/2`，51 k / 14 k / 4.7 k 三角形；球冠镜面矢高 1.5 % D、镜缘带、外侧壁、宽平缘、斜坡、主区、带穿孔的半球钮）。顶点色 R = 区号。回读检查 `Docs~/mesh_check.txt`（PASS）。生成 `Source/make_mesh.py`、检查 `Source/verify_mesh.py` |
| `Textures/` | 镜背一格 40 m 博局（`T_MirrorBack_Normal/Mask_2048`，格心带大乳；`T_MirrorBack_Centre_*` 格心不带乳：镜心那一格的钮是网格）、镜面数据图 `T_MirrorFace_2048`、铭文与十二地支字形 `T_MirrorGlyphs_1024`。生成 `Source/make_textures.py`，预览 `Docs~/textures_preview.png` |
| `Shaders/Lanbai_BronzeMirror.shader` | 镜子：镜面（反射第 9 幕的天 × 白铜菲涅耳 + 镜面自发光，白铜色调）、镜缘连珠乳钉（1.5 m 一颗，绝对尺寸）、外壁、镜背（40 m 博局格、绝对周期的栉齿 / 锯齿 / 流云纹 / 铭文带）、凝聚与溶解（FBM clip，米为单位）、第 13 面的远处柔化镜缘；第二个 pass 只在镜面写模板 |
| `Shaders/Lanbai_MirrorStars.shader` | 镜子里的星：天空的星点网格再画一遍，只在该镜的模板里；每颗星按**凸面镜**解出它的像点（不是平面镜的 y 翻转），所以星和反射的银河对得上 |
| `Shaders/Lanbai_MirrorDust.shader` | 星尘：每槽 250 个四边形的静态网格，每颗尘的一生都是时间的闭式函数（不用粒子系统 API；倒放、跳转都对） |
| `Shaders/LanbaiMirror.cginc` | 共用数学（剖面、菲涅耳、噪声、溶解、乳钉、纹带、反射的天）。**和 numpy 移植 `Tools~/port/mirror_port.py` 同名同数** |
| `Runtime/LanbaiMirrorsDriver.cs` | UdonSharp 驱动（只算，不碰 PPv2），§3 |
| `Editor/LanbaiMirrorsBuild.cs` | 菜单 `蓝白/Build/Mirrors` + 本套件的导入设置（`AssetPostprocessor`，只管 `/Mirrors/`） |
| `Editor/LanbaiMirrorsData.cs` | 生成的数组（`Tools~/schedule/bake_cs.py` 从 JSON 生成；Unity 的 JsonUtility 读不了嵌套数组） |
| `Docs~/lookdev_brief.md`、`research_tlv_form.md`、`spec_conventions.md` | 目标与量法、形制考据（约 30 个来源 + 核查记录）、网格 / 贴图 / shader 的接口约定 |
| `Docs~/iterations/` | 迭代图（r1、r2 …）、第 13 面最后 10 秒的对照（`m13_*`） |
| `Docs~/flashcheck/` | 光敏 / 爬升律的序列检查结果 |

## 2. 镜子长什么样、为什么

- **镜背的主区就是一面真镜**：克利夫兰美术馆 **1995.301**「四神博局镜」（9–100 CE，19 cm，CC0）照片的主区（r/R 0.15–0.72），去掉博物馆的打光和铜锈色块（大半径高通 + 局部对比归一，只取亮度的起伏），直接做镜背高度 → 法线和遮罩（小楠 10-24：“并不是参考，如果合适直接用”）。格心的柿蒂纹座、格角的云气纹与乳、外圈的纹带仍是程序化的（格子要能无缝平铺）。
- **一面真的汉镜**：新莽—东汉早期的四神博局镜（规矩镜 / TLV 镜），照克利夫兰美术馆的实物（`Docs~/实物参考_博局镜/`）与考据做：钮、柿蒂纹座、内方框、十二乳与十二地支（每边四乳三字，子在北）、双线外方框、T / L / V（L 同向旋转、V 尖朝方框角）、八乳（八瓣星形座 + 圆座，T 两侧各一）、四神细线、满地的云气纹、铭文带（尚方镜铭 35 字）、栉齿、锯齿、流云纹宽缘。
- **镜面朝上、素面**：看见的主要是镜面，凸 1.5 %（反射的银河像鱼眼一样弯）。镜面读作**白铜色调的银河 `#CDBF9C`**：物理的白铜菲涅耳（F0 `#D6CCB4`）不够暖，所以镜面颜色再按亮度保持往 `#CDBF9C` 的色调拉 65 %（`_BronzeTone`，迭代 r1 → r2：r1 的镜面和下方的天几乎分不出来）。
- **一面比一面大读得出来**：所有重复纹样按**米**平铺——镜缘乳钉 1.5 m 一颗（第 1 面 82 颗 → 第 12 面 1 273 颗）、镜背博局 40 m 一格（第 1 面一格 = 一面真镜，大镜子是博局的格子：六博棋盘拼成的天，总导演已批）、栉齿 0.5 m、锯齿 1.25 m、流云 3 m、铭文 2.4 m 一字（大镜子一圈圈重复同一首诗）。细节小于约 2 像素时按屏幕足迹淡出，不闪。
- **反射的就是这一幕的天**：镜面查的是天空自己的银河图和增益（`LanbaiGalaxyGainAt`、`_Udon_ZenithColor` 星空底；总导演裁决 D-29），所以镜子里的银河永远和周围的天一致（包括银心先亮 0.3 秒、x^2.5 的积累）。
- **向白的积累来自光源**：镜面自发光 = 反射的天 × (0.2 + 0.08 k) × 可见度；第 13 面在白的膨胀与保持里再 × 2^(0 → 3)（1138.78 → 1146.31，冲击里不升）。
- **穿过之后碎成尘**：2 秒从镜缘向内溶解，溶解前沿发一点 `#CDBF9C` 的光（离眼 5 m 以内淡掉：r2 里头顶刚穿过的镜子的前沿抹成了一条宽亮带），同一条前沿放出 250 颗尘，4 秒从 `#CDBF9C` 到 `#F2F6FF` 淡出、≤ 1 m/s 上升。天顶永远是开的。
- **出现**：进入“看得见的柱”时用同一个噪声从中心向外 3 秒凝聚出来，不是突然出现。F14 起下方同时看得见接下来的 3 面（镜面自发光 × 0.3）。

## 3. 运行时（`LanbaiMirrorsDriver`，挂在常开的 `Lanbai_MirrorsDriver` 上）

- `LanbaiWindow()` = {1010.0, 1150.31}：开始在天问的黑里（镜子此时都在下面、天是黑的），结束在 F16 + 1 s（白遮罩全满之下：F16 以后的几帧把第 13 面关掉、两个全局量归零）。`LanbaiActivate(on)` 只开关 `R_Mirrors`，关的时候全局量也归零；`Start()` 里写 0。
- `LanbaiTick(t)`：每面镜在自己的活动窗口里打开，算镜面在车正下方那一点的高度（Hermite 节点）、镜缘平面、位置与缩放；写每面镜的 MPB（`_RadiusM _MirrorK _EmissionK _Visibility _EmitExtraEV _Appear _Dissolve _RimSoft`，三个 LOD renderer 各一份）、星点副本的 MPB（凸面球心与半径、镜面自发光）、星尘槽的 MPB；两个全局量：
  - `_Udon_MirrorPlane` = (最近一面镜在车正下方的镜面世界 y, 镜线强度 0–1（穿越前 0.3 s → 穿越后 0.9 s）, 镜序号, 穿越进度 −1…1)：**车厢 shader 用它画 2 cm 的镜线、按它推进侵蚀**（总导演）。
  - `_Udon_MirrorRimLight` = (最近镜缘点 xyz, 目标照度 E 0–0.3)：镜缘的 8000 K 补光（D-24：不加带阴影的实时光；用不用一盏 Not Important 点光由总导演定）。
- `LanbaiGrade(t)` = {镜子脉冲 ΔEV（第 1–11 面，+0.35 EV，0.08 s 入 / 0.35 s 出）, 0, 0, 1}，没有脉冲时返回 null。**驱动不碰 PPv2**：`LB_Journey.ApplyGrades` 是唯一写曝光的（总工程师意见第 1 轮）；它现在自己算的前 9 面脉冲要删掉，换成这里的 11 面（`Engineering/README_集成.md` §5）。
- 每帧开销：活动的镜子最多 5–6 面 × 4 个 MPB，7 个星点副本、3 个尘槽的开关与 MPB，2 个 SetGlobalVector；没有分配。
- 镜子的模板：第 1–12 面用槽 (k−1) mod 6，第 13 面用槽 6，模板值 = 64 + 槽（写掩码 127，避开水洼的 128）。同时看得见的镜子不超过 5 面相邻的，所以 6 个槽不会撞。

**从 t 重建（D-33 #6）**：驱动没有跨帧的状态。每一帧（包括激活的那一帧、拖时间轴、迟到的人）都只从 t 算出每面镜的开关、位置、MPB、星点副本、尘槽和两个全局量，所以哪一帧醒来画面都是完整的。

## 4. 时间表（摘要；全部在 JSON）

两段：第 1–10 面 r = 1.3083 加速到 F15 *tragen!*（1032.41 → 1115.36），尾声三声钟 1125.55、1137.58（白的冲击）、F16（剪 2）。直径 40 m × 1.2^k（第 10 面 206 m）、360 m、620 m、2.4 km。每面镜远处在柱里慢慢等（≤ 4 m/s，尾声的 18–20 m/s），最后几秒加速到行进速度（3 → 40 m/s，尾声 ≤ 20 m/s）、接近车时减速到穿越速度（1.7 → 10 m/s，尾声 6 / 5 m/s）；穿越前镜面填满下方 45° 锥的时间 2.3–4.9 s（≥ 2 s），尾声 5.3 / 7.3 s（≥ 4 s）。镜缘离车厢包围盒 ≥ 10 m，§1.8 的 v ≤ 1.05 d 全部满足（最大 0.56）。镜子之间不相交，同时溶解最多 1 面。

**本地 `timeline_v1` 的 `starCross` 请换成这 13 个 `t_cross`**（`cues.json` 的 `mirror_crossings_*` 与 `mirror_r = 1.2265` 是 E1 / E20 作废的）。

## 5. 迭代（`Docs~/iterations/`，numpy 移植 = shader 同一套数学，画在第 9 幕的 CPU 天上；没有车厢）

| 轮 | 改了什么 | 为什么 |
|---|---|---|
| r1 | 第一版 | 镜面和下方的天几乎分不出来（反射的上半天 ≈ 下半天）；溶解前沿在头顶抹成一条白带 |
| r2 | 镜面往 `#CDBF9C` 的白铜色调拉 65 %；前沿光变暗（`#CDBF9C` × 0.8、0.3 m）并在离眼 5 m 内淡掉 | 镜子第一次读成“一面托着金色银河的镜子” |
| r3 | 镜面颜色只取亮度 × 白铜色调（不再和蓝的天混） | 第 13 面在白的膨胀里（1142 向下看）蓝 + 暖的混合变成薰衣草：D-21 紫带 8.9 %（> 2 %） |
| r4（评审 r1） | 色调按引擎调色反解成 (1.262, 0.974, 0.484)、`_BronzeTone` 1：S9a / S9b 下正好 `#CDBF9C`；镜背剪影固定在 `#16302A`（不是黑）；穿越时板的里面不画（薄的镜面平面扫过你）；溶解前沿近眼淡出；尘与反射星朝两眼中点 | 评审 r1 的 5 条阻断（`Docs~/review_r1.md` 末尾有逐条回应）；flash 序列 m10 的两个失败（见 §8） |
| 第 13 面 | 方案 A / C / D / E 对照（§6） | 总导演意见第 5 条 |

## 6. 第 13 面最后 10 秒（等总导演定）

见 `Docs~/iterations/m13_A_sheet.png`、`m13_C_sheet.png` 与 `m13_*.json`（1137.58 → 1149.31 每 0.5 s，正前方 + 向下看，镜缘对比 = 镜缘内外 3 px 的 luma 中位差，角速度 = 镜缘俯角对时间的导数）。

## 7. 检查（不是 Unity 编译）

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Mirrors/Shaders` → `4 files, 40 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`
- C#：`bash Common/Tools~/compile_check/check_cs.sh Mirrors Act10_White` → `C# CHECK OK (0 assembly error(s), 0 lint warning(s))`。
- 数据：`make_schedule.py` 全部 PASS；网格回读 PASS。

## 8. 诚实的已知弱点

- **没在 Unity 里编译过、没进过头显**。FXC 独有的诊断（如分支里的梯度指令 X3570：镜面 / 镜缘 / 镜背三个区的反射在 `if` 里用 `ddx`）检查工具抓不到。
- 迭代图没有车厢（标准台的车壳还没合成进来），镜面没有抛光纹和镜面贴图，镜背只按剪影算；APL 是“天 + 镜子”的数，不能直接和圣经 §2.2 的整帧比。
- 字形是思源宋体处理的，不是真的镜铭篆隶（找不到可用的字体）；在星空前是暗剪影，读不出来。
- 四神是程序化的细线，比真镜简单得多；镜背主区的云气纹比实物疏。
- 反射的星：凸面像点的迭代 p99 误差 0.07°，近掠射的极少数星不收敛时直接丢掉（误差 > 0.5°）。
- 星尘在大镜子上很稀（250 颗撒在几百米的盘上，70 % 在车附近 40 m 内）。
