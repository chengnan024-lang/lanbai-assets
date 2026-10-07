# 蓝白 / Lanbai · 字体与 TextMeshPro 字符表套件（Fonts）· 第 3 版（按圣经 v2.1）

这个套件落实美术圣经 **v2.1** 的 **§7 字体与诗句排版（全部）**，以及 **§5.5 / §7.6 片尾公告板与 Coleridge 纸条**、§4.7 目的地牌的字。

套件里有：
- 圣经点名的全部字体（原件 + 许可）；
- 世界里显示的**每一个字符串**（`strings_all.json`）；
- 每个 TMP 字体资产的字符表，以及按字符表裁好、已按 OFL 改名的子集字体；
- **每首诗在 TMP 里的完整摆法**：每个文本物体的字号、基线仰角、光学居中、衬底，以及圣经 v2.1 的出现 / 停留 / 退场时刻；
- **每首诗的颜色填值**：圣经的颜色是屏幕目标，这里给出按当时起作用的调色求出的 `_FaceColor` 填值，并有生成材质的编辑器脚本；
- 衬底贴图和三个编辑器 C# 文件（一次生成全部 TMP 字体资产；一次生成全部诗句材质；衬底贴图的导入设置）；
- 每种语言一张校样，另有一张三语对照的“论点之帧”校样。

> **不在本次范围：** 站牌「蓝白 / LANBAI / 藍白 / あいじろ」的字（用户说先不做）。只给站牌用的字重在站牌套件 `deliver2/Sign/Fonts/` 里。
>
> ⚠ **`Editor/` 里的三个 C# 文件都没有在 Unity 里编译或运行过**（我们这边没有 Unity）：`LanbaiTMPFontBuilder.cs`、`LanbaiPoemMaterials.cs`、`LanbaiScrimTextureImport.cs`。它们照 TextMeshPro 3.0.x（Unity 2022.3 自带的 `com.unity.textmeshpro`）的 API 写，在 Unity 外做过类型检查：Roslyn，对照 UnityEngine / UnityEditor 引用程序集和一个 TMP API 桩，警告按错误处理，**0 警告**（`Tools~/compile_check/`）。拿不准的 TMP 成员一律走反射。第一次运行请把 Console 的输出原样回传。**字体、字符表、JSON、衬底贴图和校样都不依赖这三个脚本**：手动也能做出一样的资产（§3.3、§5.4）。

---

## 0. 第 3 版改了什么

### 0.1 圣经升到 v2.1（10-02），诗句数据全部按新版重做

第 3 轮验收是按 v2 做的；验收之后圣经换成了 **v2.1（按实测乐句重排）**。§7.5 改了不少，所以这一版先把数据层整体对齐 v2.1，再处理验收意见。逐首的变化：

| # | 诗 | v2.1 改了什么 | 本套件的处理 |
|---|---|---|---|
| 1 | 李白「我欲因之梦吴越」 | 出现 **71.80（U4 − 4.0）**，停留 12.0 s | 写进 `timing`。**另查出一处旧错：** 这句出现时 S3 只以 weight ≈ 0.3 叠在 S2 上（§6·3），旧版按 S3 单独求填值，在实际调色下会读成 `#EFEAE3`（luma 234，超过 224 的上限）。现在按 S2→S3@0.30 求解，整个停留期内与目标差 0–1 码（§5.2） |
| 2 | 里尔克 | 137.30（U6 + 3.5），停留 10.0 s；**幕号 3c** | 同样是在 S3 → S4 的 30 s 交叉淡化里读的，按停留中点的混合权重（S4 w 0.195）求解，停留期内 0–1 码 |
| 3 | Urlicht | **只出 *Ach nein! / Ich ließ mich nicht abweisen!* 一联**（*Da kam ein Engelein…* 不出字）；位置 **0° / −8° / 30 m**；U8 166.15 逐词出现，≈171.5 淡尽，第二遍不出字 | 两张卡改成一张卡；给出每行的乐句标签（U8 / U8b）。字表随之变小 |
| 4 | 用户「我从天空坠入深海」 | **从晨挪到 6d 海镜**：345.36（F1z），停留 9.6 s，向下漂进自己的倒影 | 背景按海镜重画；不透明度 1.00（验收 MAJOR 3，§0.2） |
| 5 | 河伯 | 714.0（F5r + 5.1），停留 13.5 s；位置 **+10° / +6° / 15 m**（门右、深渊一侧；v2 的 −25° 会压在门上） | 改位置；校样背景改成“门在左、字在暗水上” |
| 6 | 用户「自深海坠入另一片天空」 | **从第 8 幕挪进 7c**：903.0（F8c + 0.84），停留 10.4 s；**不加暗衬**（写在暗水上） | 调色从 S8 改成 **S7b**（7c 是 S7b），重新求填值；衬底删除（§4.5）；bloom 已核查（§5.3） |
| 7 | 庄子《逍遥游》 | **只出 L1 和 L3，L2 不出**；L1 971.4、L3 976.4，一起保持到 989.0，989.0 → 993.0 退场 | 字列从 6 行改成 4 行（§4.7），字幕位 T1 → T3 |
| 8 | 天问 | 1009.21（第 9 幕第 8.0 s），到 F13（9.0 s） | 写进 `timing` |
| 9–11 | 齐物论、李白 II、济慈 | 1206.46 / 1270.96 / **1320.96**（济慈从第 70 s 改到第 66 s）；停留按 §7.4 公式 ×1.3 | 写进 `timing`，`hold_formula_s` 逐首复算（§4.10） |

### 0.2 对第 3 轮验收（`Docs~/verify_round3.md`）的逐条处理

| # | 问题 | 处理 |
|---|---|---|
| **MAJOR 1** | README 仍教 Vertex Color 填颜色、衬底 `color` 填颜色；漏写 `LanbaiPoemMaterials.cs` 与构建顺序；“两个 C# 文件”；§6 字段过期；§4.7 退场方向反了 | **README 全文重写**，与 JSON、C# 逐条对齐：Vertex Color = 白，只带 alpha（§4.1）；颜色在每首诗的材质预设的 HDR `_FaceColor` 上（§5）；衬底颜色在衬底材质的 `_Color` 上，SpriteRenderer.color = (1, 1, 1, α)（§4.5）；构建顺序 `BuildAll()` → `Build Poem Materials` → 把预设赋给 `fontSharedMaterial`（§3.2）；三个未编译的 C# 文件（开头、§10）；§7 按现在的字段重写；§4.7 退场方向与 JSON 一致。`LanbaiScrimTextureImport.cs` 的注释已改。 |
| **MAJOR 2** | 校样不是交付数据画的；没画日线 | 6 张校样和 `proof_report.json` **全部用这一版的数据重新生成，并逐块看过**（§9）。论点之帧的大图和时间条上都画了**日线 ±10°**（暖色括号）和**暗衬在 Unity 里的实际外缘**（蓝色虚线，取自 JSON 的 `azimuth_span_deg` = 2·atan(width_m / 2d)）：外缘在方位 12.0°，离日线端 2.0°。时间条多了一格 991.0：日线收到 ±3.4°，字竖着分开。 |
| **MAJOR 3** | 6 幕“深墨”在 Unity 里读成 `#575E69`（luma 93） | **`P06_Dream_Dawn` 的不透明度改成 1.00**。字心在 Unity 模型里正好是 `#1F2A3A`（luma 41，差 0 码），与背景无关；校样说明栏逐语言核对过。这是对 §7.2“不透明度 90%”的有理由的偏离：法律第 1 条，屏幕目标是法律，90% 是按亮字写的通用参数。暗字不透明并不刺眼；亮衬照常在它后面。 |
| m1 | IM FELL 子集保留了字体自己声明的保留字名 | **子集改名为 `Lanbai Slip` / `Lanbai Slip SC`**（`LanbaiSlip-Regular.ttf`、`LanbaiSlipSC-Regular.ttf`；TMP 资产 `Lanbai_Slip_Roman SDF`、`Lanbai_Slip_SC SDF`）。name ID 1/3/4/6/16/17/18 全部改，描述写明“IM FELL English Roman 的子集，按 OFL §3 改名”；脚本检查任何名字里都不再有 `IM FELL` / `FELL English`（版权、描述、许可除外）。§2b 已更正。 |
| m2 | `build_fonts.py` 离开 scratch 目录就不能跑 | **把圣经的颜色模拟器原样放进 `Tools~/colour_sim/`**（`ppv2.py`、`lutlib_core.py`、`grades_final.json` 原样复制，`lanbai_sim.py` 逐行照抄 `calib_final.solve`）。有 `art/` 时优先读 `art/grades_final.json`，并与圣经自己的求解器逐个比对（0 码）；没有 `art/` 时用自带的一份并给出提示。已在一个没有 `art/` 的副本里实跑：JSON 与正式版逐字节相同（只差生成时间）。 |
| m3 | 第 2 轮的 4 个 minor | ① 朝向写成 `Quaternion.LookRotation(父物体位置 − 头的位置, Vector3.up)`（§4.2）；② 纸条数字统一为 **173.5 × 151 mm、最长诗行 143.5 mm、降字到约 4.4 mm**，算法写在校样和 §10（站牌套件那边的事）；③ 衬底“均匀的暗”改成准确的 alpha-over 说法（§4.5）；④ 天问拆成 **20 个单字物体**（16 个汉字 + 4 个标点），JSON 里已有 `char_objects`（§4.8）。 |
| m4 | 正字与镜像字共用一个材质预设 | **每个文本物体用自己的材质实例**：预设只赋给 `fontSharedMaterial` 一次，动画改 `tmp.fontMaterial`（TMP 会给每个物体复制一份）。JSON 每个物体有 `material_instance: "own"`、`outline_softness_anim`（正字 0.9 → 0，镜像字 0.9 → 0.3）、`face_dilate`（桌面 0.05 / VR 0.10）（§4.1）。 |
| m5 | 亮字在 90% / 80% 下比目标暗 4–11 码，没写 | 写在 §5.3 的读数表里：90% 的亮字在 Unity 里比目标低 4–5 码（luma 216–220），齐物论 80% 低 12 码（luma 204，目标 215，有意的低对比），晨句 0 码。这是 §7.2 的 90% 本身的效果，校样里也一样。 |
| m6 | 「ああ、いいえ！」偏生硬 | 改成 **「いいえ！」**，仍请日语母语者定稿（§8）。 |
| m7 | `__pycache__` 打包进了套件 | 已删，`Tools~/.gitignore` 忽略 `__pycache__/`、`*.pyc`；脚本运行时建议 `PYTHONDONTWRITEBYTECODE=1`。 |
| m8 | 构建报告过期 | 文件清单（§1）和交付报告已更新：三个 C# 文件、`lanbai_color.py`、`gen_poem_materials.py`、`colour_sim/` 都在。 |

### 0.3 这一版另外改的（看校样时发现的）

- **衬底在 Unity 里的强度（§4.5）。** 圣经写的“亮衬 `#E8F1F5` α 0.25、暗衬 `#0E1A2F` α 0.30”是屏幕上的样子。Unity 在色调映射之前、在场景线性光里混合衬底，同样的 α 读出来不一样：亮衬的填值是 HDR（线性约 3.7），α 0.25 时会把海镜提亮将近一倍（`#B6BFC4`，目标 `#A3A3A3`）；暗衬 α 0.30 在亮天上又压得不够。按法律第 1 条，**SpriteRenderer 的 α 另外求解**：亮衬 **0.116**、暗衬 **0.367**。这样 Unity 里的读数与圣经的样子差 ≤ 5 码。JSON 里 `alpha` 仍是圣经的值，`sprite_color` 的 alpha 是 `alpha_unity`。
- **晨句的亮衬改成没有直边的“光”**（`Lanbai_Scrim_Block.png` 换成超椭圆）。旧的矩形衬底在亮海镜上读成一张卡片。
- **校样背景**：6d 海镜（物理菲涅尔，倒映被低日照金的云盖底面）、7c 暗水、7b 门与宫殿正面都按 v2.1 的构图重画。

### 0.4 10-07 复核时另外改的

第 3 轮的修复在 10-02 做完后，10-07 又逐项复核了一遍：三个 major、八个 minor 都按 §0.2 对照了磁盘上的文件；6 张校样全部切块重看；`build_fonts.py` 在有 `art/` 和没有 `art/` 的两个副本里各重跑一次，JSON（除生成时间）、字表、衬底贴图、C# 全部逐字节相同，子集除 `head` / `name` 的时间戳外逐表相同；三个 C# 文件重新做了 Roslyn 类型检查（0 警告）。另外改了四处：
- **天问的逐字对焦对齐圣经的“≈1011.6 就位”（§4.8）。** 原来 4 个标点也各占一个 120 ms 的错开位，20 个物体要 2.88 s，1012.09 才就位。现在标点与它前面那个字一起对焦，16 个汉字 × 120 ms：15 × 0.12 + 0.6 = **2.4 s，1011.61 就位**，与圣经 §7.5 #8 一致。`timing` 里天问的 `focus_s` 改为 2.4，并新增 `t_settled`、`focus_note`。JSON 只有这些字段变了。
- **交叉核对 ② 按调色套件的最新数据重跑。** 调色套件 10-07 更新了引擎参数（`grades_engine.json` md5 `6cb1715b1454`）。本套件的填值经它的引擎模型最多差 **3 码**（河伯的 R 通道），以前是 2 码，仍在圣经校准套件 ±3 码的容差内（§5.3）。填值本身没变：填值按圣经的 `grades_final.json` 求，这一项只是核对。
- §7 的字段表补齐（`hold_formula_count`、`layout.player`、`layout.rule`、`materials[].shader`、`face_color` 的全部字段、顶层 `_about` / `display_rule` / `generated`）；开头的“两个编辑器脚本”改为三个 C# 文件。
- §1 写明套件根目录的 `verify.md`：那是验收流程放进来的报告，Unity 会把它当 TextAsset 导入，进项目前删掉即可。
- **诗句预设的个数改正：** 按 v2.1 的诗句数据，预设是 **35 个**，加 2 个衬底材质一共 37 个。§3.2 原来写的“37 个诗句预设、PASS (39)”是旧数，脚本实际打印 `POEM MATERIALS PASS (37)`。
- §4.5 加了一条：亮衬的 `_Color` 线性值大于 1，`Sprites/Default` 的取色器不是 HDR，不要在 Inspector 里改它。
- 改完之后用这一版的 JSON 重跑了 `make_proofs.py`（rc 0，6 398 个字形 0 缺字，第 4 幕以外紫 0.00%）。6 张校样与 10-02 的那一套**逐像素相同**，`proof_report.json` 也相同：校样只画就位后的样子，不画逐字对焦的时间。

第 1、2 轮的处理记录见 `Docs~/verify_round1.md`、`Docs~/verify_round2.md` 和上一版 README 的 §0（要点都还成立，并已并入下文）。

---

## 1. 文件清单

| 路径 | 是什么 |
|---|---|
| `README_Fonts.md` | 本文件 |
| `strings_all.json` | **世界里显示的每一个字符串，每首诗、每种玩家语言的完整摆法、时刻和颜色填值**（§7）。由脚本生成，**不要手改**，要改就改 `Tools~/lanbai_strings.py`。 |
| `Charsets/charset_<字体>.txt` | 每个 TMP 字体资产的字符表：去重，按码位排序，UTF-8，**文件末尾没有换行**（有换行 TMP 会去找 U+000A）。 |
| `Charsets/charset_<拉丁字体>+ascii.txt` | 拉丁字体推荐用这一份：精确字表 + 可打印 ASCII。以后填名字时不会缺字。 |
| `Charsets/charset_ALL_CJK.txt` | 全部中日文字符的并集，只供查阅。 |
| `Subset/*.otf / *.ttf` | **生成 TMP 字体资产用的源字体**（fontTools 子集）。思源改名为 `Lanbai Serif SC/JP`、`Lanbai Sans SC`，IM FELL 改名为 `Lanbai Slip` / `Lanbai Slip SC`（OFL 保留字名，§2b）；思源里 U+2014 指向全宽中线横线；拉丁字体里注入了旧式 `kern` 表（§3.4）。 |
| `Textures/Lanbai_Scrim_Line.png`、`Lanbai_Scrim_Block.png` | 诗句衬底的 alpha 贴图（RGB 白色）。导入设置由 `Editor/LanbaiScrimTextureImport.cs` 自动设置（§3.1）。 |
| `Editor/LanbaiTMPFontBuilder.cs` + `Lanbai.Fonts.Editor.asmdef` | **（未编译）** 菜单 `蓝白/Fonts/…`：一键生成、重建、校验全部 TMP 字体资产。 |
| `Editor/LanbaiPoemMaterials.cs` | **（未编译，由脚本生成）** 菜单 `蓝白/Fonts/Build Poem Materials (solved fills)`：为每首诗生成 TMP 材质预设（HDR `_FaceColor` = 求解的填值），以及两个衬底材质（`Sprites/Default`，`_Color` = 填值）。 |
| `Editor/LanbaiScrimTextureImport.cs` | **（未编译）** AssetPostprocessor，给两张衬底贴图设好 Sprite 导入参数。 |
| `Originals~/` | 下载来的原件（Adobe 按地区的 SubsetOTF、Google Fonts 的 TTF），以及 EB Garamond 可变字体实例化出来的静态 `EBGaramond-Regular.ttf` / `EBGaramond-Italic.ttf`。 |
| `Licenses/` | 每个字体的许可全文。**要和字体放在一起进仓库。** |
| `Docs~/Proof_zh.png` `Proof_ja.png` `Proof_en.png` `Proof_de.png` | **每种语言的玩家实际看到的全部诗句**，逐幕排列，每块下面是时间、填值、Unity 模型读数和检查结果。 |
| `Docs~/Proof_Trilingual_Zhuangzi.png` | 论点之帧：英语玩家的整个画面（日线与衬底外缘已标出）；中 / 日 / 英三栏；2 × 2 时间条（+1.5 s、+5.5 s、+12 s、991.0 退场中）。 |
| `Docs~/Proof_Credits.png` | 片尾和 Coleridge 纸条全部字符串的字形校样（TMP 备用路径，不是版式）。 |
| `Docs~/build_report.txt / .json` | 子集、覆盖检查、字表、图集装箱、行距换算、光学居中、**颜色求解与两项交叉核对**、**时间表**、衬底几何、仰角检查、行宽。 |
| `Docs~/proof_report.json` | 校样里画的字形数、缺字清单、每块面板的紫面积、**每块面板的 Unity 模型读数与 bloom 检查**。 |
| `Docs~/verify_round1.md`、`verify_round2.md`、`verify_round3.md` | 三轮验收报告原文。 |
| `Tools~/lanbai_strings.py` | **全部文本与诗句数据的唯一来源**：原文、译文、書き下し、v2.1 时刻、片尾、纸条。 |
| `Tools~/lanbai_layout.py` | **全部摆法的唯一来源**：TMP 排版模型、光学居中、庄子镜像版式、衬底几何、仰角检查、时间与材质字段。JSON 和校样都调它。 |
| `Tools~/lanbai_color.py` | **全部颜色的唯一来源**：屏幕目标 → 填值（按诗句在屏幕上时实际起作用的调色，含交叉淡化）、衬底的 Unity α、合成读数、两项交叉核对。 |
| `Tools~/colour_sim/` | 圣经的 PPv2 外观模拟器（`ppv2.py`、`lutlib_core.py`、`grades_final.json` 原样复制自 `art/`；`lanbai_sim.py` 照抄 `calib_final.solve`）。 |
| `Tools~/gen_poem_materials.py` | 生成 `Editor/LanbaiPoemMaterials.cs` 里的填值表（由 `build_fonts.py` 调用）。 |
| `Tools~/build_fonts.py` | 生成 JSON、字表、子集字体、衬底贴图、材质脚本和报告。 |
| `Tools~/make_proofs.py`、`sky_dusk.py` | 画校样；`sky_dusk.py` 是第 8 幕的去紫天空（含日线收缩）与紫面积测量。 |
| `Tools~/check_kern_freetype.py`、`fetch_fonts.sh`、`compile_check/` | FreeType 字距回读、重新下载原件、C# 离线类型检查。 |
| `Tools~/.gitignore` | 忽略 `__pycache__/`、`*.pyc`。 |
| `verify.md`（如果有） | 验收流程放在套件根目录的最近一轮报告（第 3 轮的原文另存在 `Docs~/verify_round3.md`）。**不是套件的一部分**：Unity 会把根目录的 `.md` 当 TextAsset 导入，进项目前删掉。 |

以 `~` 结尾的文件夹 Unity 不会导入，所以整个 `Fonts/` 放进 `Assets/` 没有问题（根目录的 `README_Fonts.md` 会作为 TextAsset 导入，无害）。

---

## 2. 哪个字体用在哪里

| TMP 字体资产（建议名） | 源字体（`Subset/`） | 用在 | 字表 | 圣经 |
|---|---|---|---|---|
| `Lanbai_SerifSC_Regular SDF` | `LanbaiSerifSC-Regular.otf`（思源宋体 CN/SC Regular） | **所有中文诗句的主行**：李白 ×2、梦中两句、河伯、庄子 ×2、天问；片尾中文姓名与书名 | 110 字 | §7.1 |
| `Lanbai_SerifSC_Medium SDF` | `LanbaiSerifSC-Medium.otf` | **中文次行**：里尔克、Urlicht、济慈的中译；片尾「蓝白」、题记、「——梦中得句」 | 53 字 | §7.1 / §5.5 |
| `Lanbai_SerifJP_Medium SDF` | `LanbaiSerifJP-Medium.otf`（源ノ明朝 JP Medium） | **日文次行**：汉诗的書き下し；德、英诗和梦中两句的日译 | 119 字 | §7.1 / §7.3 |
| `Lanbai_Garamond_Regular SDF` | `EBGaramond-Regular.Lanbai.ttf` | **英文次行**；片尾姓名 | 66（+ascii 100） | §7.1 / §5.5 |
| `Lanbai_Garamond_Italic SDF` | `EBGaramond-Italic.Lanbai.ttf` | **德文原文**（里尔克、Urlicht）、**济慈原文**；片尾角色名与西文作品名 | 44（+ascii 98） | §7.1 / §7.5 / §5.5 |
| `Lanbai_Barlow_SemiBold SDF` | `BarlowSemiCondensed-SemiBold.Lanbai.ttf` | 片尾标题 `LANBAI`（字距 +0.3 em） | 5（+ascii 95） | §5.5 |
| （可选）`Lanbai_Slip_Roman SDF` / `Lanbai_Slip_SC SDF` | `LanbaiSlip-Regular.ttf` / `LanbaiSlipSC-Regular.ttf`（IM FELL English Roman / SC 的子集，已改名） | Coleridge 纸条正文和标题。站牌套件已经把纸条烘成贴图了，只有想用 TMP 另排一张时才需要 | 37 / 16 | §5.5 |
| （可选）`Lanbai_SerifJP_Regular SDF` | `LanbaiSerifJP-Regular.otf` | 字表与 JP Medium 相同。日文永远是次行，按 §7.3 用 Medium | 119 字 | §7.1 |
| —（不做 TMP） | `LanbaiSansSC-Heavy.otf`（思源黑体 CN/SC Heavy） | 目的地牌「蓝白」：站牌套件已经做成贴图 | 2 字 | §4.7 |

- **片尾公告板和 Coleridge 纸条**的正式版本是站牌套件烘好的贴图（精简措辞，两栏）。本套件的字表同时覆盖圣经全文版和站牌精简版。
- **世界里没有 UI 字**：§1.9 的手动开关是无字拨钮，开着时旁边亮一粒暖白小灯。
- **用户要填的占位**（梦者的名字、临落树的署名、Built by）不算显示文本，没有进字表。填好后按 §6 加字。

### 2b. 许可（全部 SIL Open Font License 1.1）

| 字体 | 版权 | 保留字名（RFN） | 我们的处理 |
|---|---|---|---|
| 思源宋体 / 源ノ明朝、思源黑体 | © Adobe | **“Source”** | 子集属于修改版，改名为 `Lanbai Serif SC/JP`、`Lanbai Sans SC`：name ID 1/3/4/6/16/17/18/20、CFF 顶层名、FDArray 子字体名都改了。版权（0）、商标（7）、许可（13/14）原样保留，描述（10）写明来源与改名理由。`Originals~/` 里的原件未修改，名字不变。 |
| IM FELL English Roman / English SC | © Igino Marini | **“IM FELL English Roman”、“IM FELL English SC”**（两个原件的 name ID 0 这样声明；上游 OFL.txt 没列 RFN，我们按更严的那条） | 子集改名为 **`Lanbai Slip` / `Lanbai Slip SC`**（同上的 name ID 全部改）。片尾 Type 一行写原字体名 “IM FELL English” 是署名，不受 RFN 限制。 |
| EB Garamond | © The EB Garamond Project Authors | 无 | 实例化成静态字体再裁子集；名字规范为 `EB Garamond` / `EBGaramond-Regular`、`EBGaramond-Italic` |
| Barlow Semi Condensed | © The Barlow Project Authors | 无 | 子集，名字不变 |

- OFL 允许嵌入世界、修改、再配布，只是**不能单独卖字体**，许可全文要跟着字体走（`Licenses/`）。
- **静态 TMP 字体资产不会把 OTF/TTF 打进世界包**：Atlas Population Mode = Static 时，世界里只有 SDF 图集贴图和材质。
- 站牌套件的正式片尾目前没有 Type 一行。OFL 不强制署名；建议加一行 `Type — Source Han Serif · EB Garamond · Barlow · IM FELL (SIL OFL)`。

---

## 3. 导入与生成

### 3.1 导入
1. 把整个 `Fonts/` 文件夹放进项目，建议 `Assets/Lanbai/Fonts/`。路径随意，脚本按自己所在的位置找。
2. `Subset/` 里的字体用 Unity 默认导入设置。它们只在编辑器里当 TMP 的源，不进世界包。
3. `Textures/Lanbai_Scrim_*.png` 由 `LanbaiScrimTextureImport.cs` 自动设成：Sprite (2D and UI)、Single、**Pixels Per Unit 100**、Mesh Type Full Rect、Pivot Center、Mip Maps 开、Clamp、Bilinear、不压缩、Alpha Is Transparency 开、Max Size 512。不用这个脚本就手动这样设。**PPU 必须是 100**，JSON 的 `sprite_scale` 按它算。
4. 依赖 **TextMeshPro 3.0.x**。第一次先 `Window › TextMeshPro › Import TMP Essential Resources`。
5. 项目必须是 **Linear 色彩空间**（VRChat 世界本来就是）。填值都是按 Linear 求的。

### 3.2 构建顺序（脚本，未编译）

| 步骤 | 菜单 / 方法 | 做什么 | 期望输出 |
|---|---|---|---|
| ① | `蓝白/Fonts/Build TMP Font Assets (SDF32, bible)` = `Lanbai.Fonts.EditorTools.LanbaiTMPFontBuilder.BuildAll()` | 生成 §2 表里前 6 个必需的字体资产：SDF32、90 pt、padding 10、CJK 2048² / 拉丁 1024²、单图集，材质 `TextMeshPro/Distance Field`，设为 Static；结尾自动跑 `VerifyAll()` | 每行 `OK`，最后 `VERIFY PASS`；Garamond 与 Barlow 的 kerning pairs > 0 |
| ② | `蓝白/Fonts/Build Poem Materials (solved fills)` = `Lanbai.Fonts.EditorTools.LanbaiPoemMaterials.BuildAll()` | 在 `<套件>/FontAssets/PoemMaterials/` 生成 **35 个诗句预设**（`<字体资产名> - <诗 id>`，复制字体资产的材质，`_FaceColor` 写入求解的 HDR 填值，Render Queue 3010）和 **2 个衬底材质**（`Lanbai_Scrim_Dark_S8`、`Lanbai_Scrim_Light_S6`，`Sprites/Default`，`_Color` = 填值，Queue 3009）。写完逐个回读校验 | 每行 `OK`，最后 `POEM MATERIALS PASS (37)`（35 + 2）；字体资产还没生成时，诗句预设那几行是 `SKIP`，结尾是 `… ok, … not built`；若项目不是 Linear 会有 WARNING |
| ③ | 手动 / Director | 每个 TMP 物体：`tmp.fontSharedMaterial = <它那首诗、那个字体的预设>`（JSON 每个物体的 `material` 字段就是预设名）；动画一律改 `tmp.fontMaterial`（§4.1） | — |

- 其他入口：`BuildAllFast()`（SDFAA，快的备用）、`BuildOptional()`（Slip ×2、JP Regular）、`BuildOne("EBGaramond-Italic", "SDF32")`、`VerifyAll()`。
- **再跑一次会原地重建，GUID 不变**：字体资产先写入新的尺寸和模式再 `ClearFontAssetData`；诗句材质用 `CopyPropertiesFromMaterial` 跟上新图集，再写一次颜色。字体资产重建后**一定要再跑一次 ②**。
- 如果 Console 出现 “no UpdateGlyphAdjustmentRecords we can call” 而且字距对数是 0，三个拉丁资产按 §3.3 手动做一次，勾上 Get Kerning Pairs。

### 3.3 手动生成字体资产（Window › TextMeshPro › Font Asset Creator）

| 设置 | CJK（SC Regular / SC Medium / JP Medium） | 拉丁（Garamond ×2、Barlow、Slip） |
|---|---|---|
| Source Font File | `Subset/` 里对应的那个（§3.4） | 同左 |
| Sampling Point Size | **Custom Size = 90** | **90** |
| Padding | **10** | **10** |
| Packing Method | Optimum | Optimum |
| Atlas Resolution | **2048 × 2048**（§7.2） | **1024 × 1024** |
| Character Set | **Characters from File** → `Charsets/charset_<字体>.txt` | **Characters from File** → `charset_<字体>+ascii.txt` |
| Render Mode | **SDF32**（§7.2）；嫌慢可用 SDFAA | SDF32（或 SDFAA） |
| Get Kerning Pairs | 关 | **开** |

Missing Characters 必须为 0。存成 `Lanbai_…SDF.asset` 后：Atlas Population Mode = **Static**；Shader = **`TextMeshPro/Distance Field`**；**Glow、Outline、Underlay、Bevel 全关**（§7.2）。

图集装箱（保守的货架式装箱）全部放得下圣经的尺寸：SC Regular 填充 27%、SC Medium 12%、JP Medium 28%、Garamond Regular +ascii 43%、Italic +ascii 48%、Barlow +ascii 39%。

### 3.4 为什么用 `Subset/` 当源
1. **字距：** TMP 3.0 只读旧式 `kern` 表，EB Garamond 和 Barlow 的字距只在 GPOS 里。我们按 GPOS 算好写进 `kern`：Garamond Regular 2 518 对、Italic 2 279 对、Barlow 3 916 对，FreeType 回读一致。
2. **破折号：** 只有子集里的 U+2014 是全宽、居中的横线（「——梦中得句」两条连成一条 2 em 的线，这一行字距 0）。
3. **名字：** 子集已按 OFL 改名（§2b）。
4. **小：** 全部原件 46.75 MB → 子集 0.70 MB。10 个子集都通过 OTS 检查。

---

## 4. 每句诗在 TMP 里怎么摆（数值全部在 `strings_all.json` → `poems[i].layout[玩家语言]`）

### 4.1 组件与通用设置
- 世界空间的 **`TextMeshPro`**（3D 版，不是 UGUI）。**每个“文本物体”一个组件**：一般的诗是主行一个、译文一个；庄子是 4 行加 1 个字幕位（§4.7）；天问的逐字对焦要拆成单字物体（§4.8）。
- **对齐：`TextAlignmentOptions.Baseline`**（水平居中，**第一行的基线**落在物体位置上）。RectTransform pivot (0.5, 0.5)。Wrapping 关（断行已写在字符串里），Overflow = Overflow，Extra Padding 开。第一次做好后请在物体位置放一个 1 cm 的小方块，第一行的基线应正好穿过它。
- **字号：`font_size` = 10 × 距离(m) × tan(字高°)**（TMP 3D 模式 1 em = 0.1 × fontSize 世界单位，localScale = 1）。
- **字距：** `character_spacing` = CJK 10（+0.10 em）、拉丁 0。**行距：** `line_spacing` = 思源 +16.3、EB Garamond +4.5，得到圣经的 1.6 em / 1.35 em。
- **颜色（重要，验收第 2 轮 B.1 / 第 3 轮 MAJOR 1）：**
  - **Vertex Color = 白色 (1, 1, 1)，只用 alpha**：`vertex_color` = `[1, 1, 1, alpha]`。alpha = 0.90（一般的诗）、**1.00（晨句「我从天空坠入深海」）**、0.80（齐物论）、0.45（庄子镜像字）；淡入淡出乘在这个 alpha 上。
  - **不要把圣经的 hex 填进 Vertex Color。** 那些 hex 是屏幕目标：诗句不受光，要经过每一幕的调色（Neutral 色调映射、曝光、白平衡、对比度……），而 TMP 3.0 对顶点色不做任何色彩空间转换。照字面填，李白的暖白会读成冷灰 `#ADB0B5`（luma 176）。
  - 颜色在**材质**上：每首诗、每个字体资产一个预设，HDR `_FaceColor` = §5 求出的填值。预设由 `LanbaiPoemMaterials.cs` 生成；手动做的话，复制字体资产的材质，在 HDR 取色器里输入 `fill_hdr`（hex + Intensity）。
- **每个文本物体用自己的材质实例（验收第 3 轮 m4）：** 正字和它的镜像字共用一个预设，但 `_OutlineSoftness` 的动画不同；Face Dilate 也是材质属性。所以：
  - 先 `tmp.fontSharedMaterial = 预设`（一次）；
  - 之后的动画全部改 **`tmp.fontMaterial`**（TMP 第一次访问时为这个物体复制一份）；**永远不要改预设本身**；
  - 出现（§7.4-4）：`_OutlineSoftness` 按 `outline_softness_anim` 从 0.9 到终值（正字 0，镜像字 0.3），alpha 0 → 物体的 alpha，2.5 s ease-out，单调；
  - Face Dilate：`face_dilate` 桌面 0.05、VR 0.10，开始时按 `Networking.LocalPlayer.IsUserInVR()` 设一次。
- **字心读数**：见 §5.3。没有任何一句诗会 bloom（§5.3 的 bloom 检查）。

### 4.2 摆放：父物体 + 子物体
每个 `layout` 有 `anchor = [方位°, 仰角°, 距离 m]`（§7.5 的位置）。
1. 在 anchor 的方向和距离放一个**父物体**，出现那一刻朝向玩家的头，之后固定在车厢空间里（§7.4-5、6）。**朝向必须是**
   `parent.rotation = Quaternion.LookRotation(parent.position − headPosition, Vector3.up)`
   也就是父物体的 +Z 背离观看者。TMP 只有在 +Z 背向观看者时才是正读的；写成 `parent.LookAt(head)` 会让所有字左右反过来，z = +0.01 的衬底也会跑到字前面。`Vector3.up` 保证字永远水平（地平线永不倾斜，§1.3.6）。
2. 每个文本物体做成子物体：`localPosition = (0, local_y_m, 0)`，`localScale = (1, scale_y, 1)`。
3. 需要光学居中的行按 §4.4 处理。
4. 注视规则（§7.4-6）：触发时玩家偏航与默认方位差 ≤ 50° 用默认；否则放在玩家当前朝向（按 15° 取整）朝默认偏 20°，同仰角同距离。**庄子例外，永远在 +35° / 0° / 60 m。**

JSON 同时给出每个物体的 `first_baseline_el`、`line_baselines_el`、`top_el` / `bottom_el` / `center_el`（em 框，单位度）。

### 4.3 仰角铁律（§7.3：文本中心永不高于 +10°、永不低于 −15°）
整块的中心放在 §7.5 的仰角上；**某个物体的中心会越界时，整块按最小的量移动**，`shift_deg` 写着移了多少：

| 诗 | 移动 |
|---|---|
| 河伯 | de / en / other −0.13°，ja −0.68° |
| 天问 | de / en / other −3.35°，ja −2.68° |
| 齐物论 | de / en / other −2.11°，ja −2.66° |
| 济慈 | zh / ja +0.50° |

§7.3 是“永不”，优先于 §7.5 的位置。只看原文的玩家都不移动。全部物体 PASS（`build_report.txt` 的 `== VERTICAL PLACEMENT ==`）。

### 4.4 光学居中
思源宋体 SC 的「？」「！」墨迹只占字身左半边，行末有这两个字的行居中时会向左偏。`optical_offsets_em` 给出每一行要向右移多少 em（只列 ≥ 0.06 em 的）：
- **每行一个物体**时：该行 `localPosition.x = line_local_x_m`；
- **多行在同一个物体里**时：打开 Rich Text，改用 `tmp_text_rich`（行首加了 `<space=…em>`，TMP 里行首空出 s，居中的行右移 s/2）。

需要移动的行：「天之苍苍，其正色邪？」+0.25、天问两行 +0.25、「我是醒着，还是睡着？」+0.25、「啊，不！」+0.31、「我不肯被拒之门外！」+0.33、「いいえ！」+0.18、「わたしは引き下がらなかった！」+0.18，另有几行 ±0.07–0.08（`build_report.txt` 的 `== OPTICAL OFFSETS ==`）。

### 4.5 衬底（§7.2：一张柔和的衬，永不描边、永不投影）
v2.1 里只有两处有衬底：**晨句（6d）的亮衬 `#E8F1F5` α 0.25**，和**庄子（8-ii）的暗衬 `#0E1A2F` α 0.30**。7c 的暮句**不加衬底**：它写在暗水上；圣经说“只有落在窗光上时才加”，而倒置的斯涅尔之窗边缘在仰角 −41.5°，字在 −12°，这个条件不会出现。数据在 `layout.scrims[]`。

- **做法：** 父物体下放一个 **SpriteRenderer**：
  - Sprite = `texture`；
  - **Material = `material`**（`Lanbai_Scrim_Light_S6` 或 `Lanbai_Scrim_Dark_S8`，由 `LanbaiPoemMaterials.cs` 生成：`Sprites/Default`，`_Color` = 求解的填值，Render Queue 3009）。手动做的话：用 `Sprites/Default` 新建材质，`_Color`（Tint）填 §5.2 的衬底填值；
  - **`SpriteRenderer.color = sprite_color` = (1, 1, 1, `alpha_unity`)**：白色在 gamma 与线性里是同一个数，所以颜色只由材质决定；alpha 用 **`alpha_unity`**（亮衬 0.116、暗衬 0.367），不是圣经的 0.25 / 0.30（原因见 §0.3）。衬底跟它的字一起淡入淡出：Udon 只改 `SpriteRenderer.color.a`（= `alpha_unity` × 字当时的淡入系数）；
  - `localPosition = (0, local_y_m, 0.01)`（在字后面一点），`localScale = sprite_scale`。
- **两张贴图：**
  - `Lanbai_Scrim_Block.png`（512 × 256，晨句）：**超椭圆的柔光**，r = (|2u−1|⁴ + |2v−1|⁴)^¼，r ≤ 0.5 平坦，之后余弦降到 0；没有直边，在海镜上读成一片光，不像一张卡。四边 alpha 为 0。每一行的两端都在核心强度的 ≥ 0.88 处。
  - `Lanbai_Scrim_Line.png`（512 × 128，庄子每行一张，镜像行也有）：竖向是纯 Hann 窗，高 = 2 × 行距；横向核心 55%，两边宽羽化。两条 Hann 带在等距的字列里按半高错开，**alpha-over 叠加**：行心 0.30，行间 1 − 0.85² = 0.2775，起伏 7.5%（行间略浅，不会出现暗条纹）。Unity 里用 `alpha_unity` 0.367 时同理：行心 0.367，行间 1 − (1 − 0.1835)² = 0.333，起伏 9%。
  - 羽化都比圣经“40 px”的下限宽，有意为之。
- **庄子的衬底永远不压在日线上：** 日线在方位 ±10°、仰角 0°（§6·8b）。衬底的米制宽度 = 2·d·tan(张角/2)，Unity 里的实际外缘（`azimuth_span_deg`）在方位 **12.0°**（L3 / L3′，宽度被收窄到 46.0°）和 12.4°（L1 / L1′），离日线端 ≥ 2°。论点之帧校样上画出来了。
- **渲染顺序：** 车窗玻璃 3000 → 衬底 3009 → 诗句 3010。玻璃不写深度，所以画在后面的衬底和字不会被挡掉。
- **亮衬的 `_Color` 大于 1**（线性约 2.8 / 3.4 / 3.7）。`Sprites/Default` 的 `_Color` 不是 `[HDR]` 属性，不要在 Inspector 里改它：非 HDR 取色器一改就把值钳到 1。改坏了重跑 §3.2 ② 就能恢复。脚本写入的值会存在 `.mat` 里，渲染时照常生效。PC 显卡把 shader 里的 `fixed` 当 float 处理，所以没有问题。如果以后出 Quest 版，`fixed` 会被钳到 2，那时要换一个 half 精度的 shader。

### 4.6 字号表（localScale = 1 时的 fontSize）

| 诗 | 距离 | 主行 | fontSize | 次行（译文） | fontSize |
|---|---|---|---|---|---|
| 3 李白（我欲因之梦吴越） | 40 m | 2.4° | 16.76 | 1.8° | 12.57 |
| 3c 里尔克 | 60 m | 2.2° 德文斜体 | 23.05 | 1.8° | 18.86 |
| 4 Urlicht（一联，逐词） | 30 m | 1.8° 德文斜体 | 9.43 | 1.8° | 9.43 |
| 6d 我从天空坠入深海 | 40 m | 2.4° | 16.76 | 1.8° | 12.57 |
| 7b 河伯 | 15 m | 2.2° | 5.76 | 1.8° | 4.71 |
| 7c 自深海坠入另一片天空 | 40 m | 2.4° | 16.76 | 1.8° | 12.57 |
| 8-ii 庄子《逍遥游》 | 60 m | 2.2° | 23.05 | 字幕 1.8° | 18.86 |
| 9a 天问 | 50 m | 2.2° | 19.21 | 1.8° | 15.71 |
| 11 庄子《齐物论》 | 10 m | 2.0° | 3.49 | 1.8° | 3.14 |
| 12 李白（惟觉时之枕席） | 40 m | 2.4° | 16.76 | 1.8° | 12.57 |
| 12 济慈 | 25 m | 1.6° 斜体 | 6.98 | 1.8° | 7.86 |

济慈的译文（1.8°）比原文（1.6°）大，这是圣经的规定（中日文次行不能小于 1.8°）。最宽的一行 27.5°，全部 ≤ 28°。

### 4.7 庄子《逍遥游》：全世界的论点之帧（§6·8、§7.5 #7；看 `Docs~/Proof_Trilingual_Zhuangzi.png`）
父物体在 **+35° / 0° / 60 m**，不跟随注视。v2.1 **只出 L1 和 L3**（L2「其远而无所至极邪？」不出）。`layout[语言].objects`：

| 物体 | 内容 | 基线仰角 | 中心仰角 | local_y_m | scale.y | 出现 | 退场（989.0 起 4 s） |
|---|---|---|---|---|---|---|---|
| L1 | 天之苍苍，其正色邪？ | +4.444° | +5.28° | +4.6631 | 1 | **971.4**（+0 s） | 向上漂 0.2° |
| L3′ | （L3 的镜像，地平线上） | +2.596° | +1.76° | +2.7204 | **−1** | **976.4**（+5 s） | 向上漂 |
| L3 | 其视下也，亦若是则已矣（**正字在地平线下，低头读**） | −2.596° | −1.76° | −2.7204 | 1 | 976.4 | **向下**漂 |
| L1′ | （L1 的镜像，地平线下） | −4.444° | −5.28° | −4.6631 | −1 | 971.4 | 向下漂 |
| T1 / T3 | 本玩家语言的译文（中文玩家没有） | 英 −8.556°，日 −8.844° | 英 −9.36°，日 −9.60° | 英 −9.0270，日 −9.3357 | 1 | T1 971.4；T3 **977.2**（+5.8 s） | T1 在 976.4 起 1 s 淡出；T3 与全体一起 989.0 → 993.0 |

- **一列等距的四行，地平线在正中那道缝里：** 从上到下 L1、L3′ | 地平线 | L3、L1′。行距全部 1.6 em，地平线两侧各留 0.3 em。翻转的那一行（L3）贴着地平线，排版恰好在“往下看与往上看一样”上翻转；L1 和它的镜像在外侧框住整列。
- **镜像字**：同一段文字，`localScale.y = −1`，放在正字基线的相反仰角上，是以地平线为轴的精确反射。镜像字 alpha 0.45（0.5 × 0.9），`_OutlineSoftness` 终值 0.3。光学居中偏移与正字相同。
- **退场方向：** 地平线上的物体向上漂，地平线下的向下漂。每一对正字 / 镜像字都上下分开，反射关系保持精确。这就是 §7.4-4“庄子的镜像字两向分开”和 §6·8“线横着收拢，字竖着分开”；§7.5 表里“正字向上漂、镜像字向下漂”是按正字在上的 L1 写的，对 L3（正字在下）照字面做会让两行往地平线靠拢。
- **字幕位**（译文不进镜像）：顶边在 −7.26°（字列底边之下 0.4 em）。T1 只显示 5 s（971.4 → 976.4 → 1 s 淡出），这是圣经两行相隔 5 s 定下的；T3 一直保持到退场。不叠成两块字幕，是为了不在“最静的画面”里加字块（E25：字块从 6 块减到 4 块）。
- **衬底**：每行一条暗衬带（4 条），各自跟着自己的行淡入；外缘离日线 ≥ 2°（§4.5）。字幕位没有衬底。
- **日线**：F12（987.06）起 6 s 从 ±10° 收成一点；庄子 989.0 → 993.0 的退场与它是同一个动作，993.06 之前字完全离开，蓝时是空的。

### 4.8 天问：逐字对焦与 16 颗星（§6·9、§7.4-4）
`_OutlineSoftness` 是材质属性，一个 TMP 物体做不了逐字对焦。主行物体里有：
- **`char_objects`（20 个）**：每个字一个 TMP 单字物体（Baseline 对齐时单字以自身 advance 居中，所以与整行完全重合，字距与 kern 已含在坐标里）。字段：`char`、`line`、`local_x_m`、`local_y_m`、`baseline_el`、`focus_delay_s`、`focus_s` 0.6、`star`（16 个汉字为 true，4 个标点为 false）。每个单字物体用自己的材质实例（§4.1）。
- **错开：** 16 个汉字依次错开 120 ms（`focus_delay_s` = 0、0.12 … 1.80），**标点与它前面那个字同时对焦**（「初」与「，」都是 0.36）。最后一个字在 1.80 + 0.6 = 2.4 s 就位，也就是 **1009.21 + 2.4 = 1011.61**（圣经 §7.5 #8 “≈1011.6 就位”）。`timing.focus_s` = 2.4、`timing.t_settled` = 1011.61。每个字照 §7.4-4：`_OutlineSoftness` 0.9 → 0、alpha 0 → 0.9，0.6 s ease-out。
- **`star_points`**：16 个汉字的字心（`x_em` 相对行中心、已含光学居中；y = 基线上方 0.38 em）。乘以 `em_m = 0.1 × fontSize` 就是局部坐标。F13（1018.21）那一帧在这些点上点燃 16 颗星，字 1.2 s 内暗下。
- 译文物体照常是一整块，与主行一起出现。

### 4.9 Urlicht：一联，逐词与歌声同步（§6·4、§7.5 #3）
- 只出 *Ach nein! / Ich ließ mich nicht abweisen!*。`timing.line_cues`：第一行绑 **U8**（166.15），第二行绑 **U8b**（167.90）。
- 逐词出现不需要额外材质：Vertex Color 是白色、只带 alpha，所以可以直接改 `textInfo.meshInfo[0].colors32` 里每个字的 alpha（或者用 `maxVisibleCharacters` 逐词推进）。译文行跟着它的原文行出现。
- 第一遍唱完后 1.5 s 内淡出（≈171.5），U8c 第二遍不出字。

### 4.10 时间表（圣经 v2.1 §7.5；每个 layout 的 `timing`）
时刻是给人看的秒数（出发 = 0）；**Director 一律绑 `cue` 标签**（法律第 2 条）。停留 = §7.4-3 公式 ×1.3（有译文），两处圣经明文例外照抄。

| 诗 | cue | 出现 | 停留 | 退场开始 → 完 | 公式 |
|---|---|---|---|---|---|
| 李白 I | U4 − 4.0 | 71.80 | 12.0 | 83.80 → 86.80 | 12.0 |
| 里尔克 | U6 + 3.5 | 137.30 | 10.0 | 147.30 → 150.30（= U7） | 10.6（例外 −0.6） |
| Urlicht | U8 / U8b | 166.15 | 与歌声同步 | → ≈171.5 | — |
| 晨句 | F1z | 345.36 | 9.6 | 354.96 → 357.96（↓） | 9.6 |
| 河伯 | F5r + 5.1 | 714.0 | 13.5 | 727.5 → 730.5 | 13.5 |
| 暮句 | F8c + 0.84 | 903.0 | 10.4 | 913.4 → 916.4（↓） | 10.4 |
| 庄子 | 天顶散尽 + 6.0 / ≈F11b | 971.4 / 976.4 | 到 989.0 | 989.0 → 993.0（4 s） | 9.6 / 10.4 |
| 天问 | 第 9 幕 + 8.0 | 1009.21 | 9.0（到 F13） | F13 1018.21 → 1019.41 | 12.7（例外 −3.7） |
| 齐物论 | 第 11 幕 + 28 | 1206.46 | 12.7 | 1219.16 → 1222.16 | 12.7 |
| 李白 II | 第 12 幕 + 16 | 1270.96 | 11.2 | 1282.16 → 1285.16 | 11.2 |
| 济慈 | 第 12 幕 + 66 | 1320.96 | 10.6 | 1331.56 → 1334.56 | 10.6 |

退场 3 s，默认向上漂 0.2°；两句坠落的句子向下漂（晨句漂进它自己的倒影，暮句漂进下面那片天）；庄子见 §4.7；天问见 §4.8。

---

## 5. 颜色：屏幕目标 → 填值

### 5.1 为什么、怎么求
圣经法律第 1 条：§7.5 / §7.2 的 hex 都是**屏幕目标**（截图上应读到的颜色）。诗句不受光，要经过它在屏幕上时**实际起作用的调色**。`Tools~/lanbai_color.py` 用圣经自己的模拟器（`calib_final.solve`，就是 `calib_final.md` §B 每一行“目标 → 填值”用的代码）在那个调色下求出场景线性的填值。
- 两首诗是在 PPv2 volume 交叉淡化里读的（PPv2 的覆盖是 `lerp(低优先级, 高优先级, weight)`，§1.4）：**李白 I**（S3 以 weight 0 → 0.3 叠在 S2 上，39.10 → 79.10，§6·3）和**里尔克**（S4 在 133.80 → 163.80 的 30 s smoothstep 里升起，§6·4）。它们按**停留中点**的混合权重求解，并核对了整个停留期。
- `fill_hdr` = Unity HDR 取色器的写法（hex + Intensity，线性 × 2^n），与 `calib_final.md` §B 相同；`fill_linear` = shader 收到的线性值。`LanbaiPoemMaterials.cs` 用 `SetColor(linear.gamma)` 写入（Linear 项目里 Unity 会把它转回线性，HDR 值也精确），写完回读校验。

### 5.2 填值表（`poems[i].face_color`、`scrim_fill`、顶层 `materials`）

| 诗 | 起作用的调色 | 屏幕目标 | `_FaceColor` 填（HDR） | 不透明度 |
|---|---|---|---|---|
| 李白 I | S2 → S3 @ w 0.30 | `#E2DDD4` | `#FFEECE @ +0.73` | 0.90 |
| 里尔克 | S3 → S4 @ w 0.195 | `#D8DDE6` | `#EFF3FF @ +1.11` | 0.90 |
| Urlicht | S4 | `#D8DDE6` | `#EEF1FF @ +1.05` | 0.90 |
| 晨句 | S6 | `#1F2A3A` | `#2F3848` | **1.00** |
| 河伯 | S7b | `#D9E2E7` | `#F2FDFF @ +0.60` | 0.90 |
| 暮句（7c） | **S7b** | `#EADCD6` | `#FFD9C4 @ +0.92` | 0.90 |
| 庄子（**AD 10-07 改为靛墨 `#27304A`**，见圣经 §7.5 #7；下面三格是旧值，以暮的包 `sky/dusk` 为准） | S8 | ~~`#EADCD6`~~ | `#FFE5E0 @ +1.00` | 0.90（镜像 0.45） |
| 天问 | S9a | `#D9E2E7` | `#EBF9FA` | 0.90 |
| 齐物论 | S11 | `#E0D6C4` | `#FFE1AE @ +0.50` | 0.80 |
| 李白 II、济慈 | S12 | `#D9E2E7` | `#E6F9FF @ +0.40` | 0.90 |

| 衬底材质 | 调色 | 屏幕目标 | `_Color` 填 | 圣经 α | **SpriteRenderer α** |
|---|---|---|---|---|---|
| `Lanbai_Scrim_Light_S6`（晨句） | S6 | `#E8F1F5` | `#DFF4FF @ +1.90` | 0.25 | **0.116** |
| `Lanbai_Scrim_Dark_S8`（庄子） | S8 | `#0E1A2F` | `#182238` | 0.30 | **0.367** |

同一首诗的每个字体资产（主行、译文）都有一份同色预设：一共 **35 个诗句预设**，加 2 个衬底材质，`materials[]` 共 37 项，与 JSON 里排版物体和衬底实际引用的材质名一一对应（不缺、不多）。

### 5.3 Unity 里会读到什么（`Docs~/proof_report.json` 的 `composite`，m5）
Unity 模型 = 背景、衬底、字按交付的填值和 α 在场景线性光里混合，再过调色；背景取校样里字下面的平均色。

| 诗 | Unity 字心读数 | 目标 | 差 | 说明 |
|---|---|---|---|---|
| 晨句 | `#1F2A3A`（luma 41） | `#1F2A3A`（41） | **0 码** | 不透明度 1.00；90% 时会是 `#575E69`（luma 93） |
| 李白 I、里尔克、Urlicht | `#DDD8CF` / `#D3D8E2`（luma 216） | 221 | 5 码 | 90% 时 10% 的暗背景透进来，§7.2 的 90% 本身就是这个效果，校样里一样 |
| 河伯、天问、李白 II、济慈 | `#D4DDE3`（luma 220） | 224 | 4–5 码 | 同上 |
| 暮句 | `#E6D7D1`（luma 218） | 222 | 5 码 | 同上 |
| 庄子 | `#E7D9D2`（luma 220） | 222 | 4 码 | 背景是亮的另一片天，所以差得更少 |
| 齐物论 | `#D6CBB8`（luma 204） | 215 | 12 码 | 80%：圣经要的“低对比” |

- **衬底处：** 晨句的亮衬下 Unity `#A0A4A6`，圣经的样子（校样）`#A4A3A2`；庄子暗衬下 Unity `#AF978B`，校样 `#AC988D`，都在 5 码以内（用 `alpha_unity`；若照搬 0.25 / 0.30，晨句会亮约 19 码）。
- **李白 I 与里尔克在停留期内：** 李白 71.80（w 0.274）差 1 码，74.30 以后 0 码；里尔克 137.30 差 1 码，139.8–142.3 0 码，147.3（w 0.425）差 1 码（`build_report.txt` 的 `== COLOUR ==`）。
- **bloom：** 用圣经的 PPv2 bloom 模型（二次阈值、clamp、1920 px 画面的金字塔层数、半分辨率预过滤）在 1080p / 90° 下算了每块面板的字：**只有暮句在 S7b 下有一点点进入预过滤**（红通道略高于阈值），字外的光晕 ≤ 0.4 码、字上 ≤ 0.8 码，看不见；其余全部 0。诗句不会 bloom（§1.6）。
- **两项交叉核对**（`build_report.txt`）：① 用 `art/bible_work/calib_final.solve` 重求每个单一调色下的填值：与本套件逐个相同（0 码）；② 用调色套件（`deliver2/Grading`）按 PPv2 源码写的**引擎模型**和它重新求解的引擎参数（Grading 验收 B1 的修法）跑每个填值：与目标最多差 **3 码**（10-07 的引擎参数，`grades_engine.json` md5 `6cb1715b1454`；最大的是河伯的 R 通道，其余 0–2 码），在圣经校准套件 ±3 码的容差之内。所以即使调色套件改成引擎参数，这些填值仍然成立。若以后调色参数再变，重跑 `build_fonts.py` 即可，填值和 C# 表会一起更新。

### 5.4 手动做材质（不用脚本时）
1. 复制对应字体资产的材质（例如 `Lanbai_SerifSC_Regular SDF Material`），改名为 `Lanbai_SerifSC_Regular SDF - P03_LiBai_Dream`；
2. Face Color 点开 HDR 取色器，hex 填 `fill_hdr` 的前半，Intensity 填 `@` 后面的数（例如 `#FFEECE`、+0.73）；没有 `@` 的直接填 hex；
3. Render Queue 3010；
4. 衬底：`Sprites/Default` 新建材质，Tint 同样填 §5.2 的值，Render Queue 3009。

---

## 6. 字符表文件与加字

| 文件 | 字数 | 给哪个资产 |
|---|---|---|
| `charset_SourceHanSerifSC-Regular.txt` | 110 | SC Regular |
| `charset_SourceHanSerifSC-Medium.txt` | 53 | SC Medium |
| `charset_SourceHanSerifJP-Medium.txt` | 119 | JP Medium |
| `charset_SourceHanSerifJP-Regular.txt` | 119 | （可选）JP Regular，与 Medium 相同 |
| `charset_EBGaramond-Regular.txt` / `+ascii` | 66 / 100 | Garamond Regular（推荐 +ascii） |
| `charset_EBGaramond-Italic.txt` / `+ascii` | 44 / 98 | Garamond Italic（推荐 +ascii） |
| `charset_BarlowSemiCondensed-SemiBold.txt` / `+ascii` | 5 / 95 | Barlow（推荐 +ascii） |
| `charset_IMFellEnglish-Roman.txt` / `+ascii` | 37 / 98 | （可选）Slip Roman（文件名沿用原字体名，只是字表） |
| `charset_IMFellEnglishSC.txt` / `+ascii` | 16 / 95 | （可选）Slip SC |
| `charset_SourceHanSansSC-Heavy.txt` | 2 | 目的地牌（贴图，不做 TMP） |
| `charset_ALL_CJK.txt` | 207 | 中日文并集，只供查阅 |

**加字或改字：**
1. 改 `Tools~/lanbai_strings.py`；
2. `pip install fonttools numpy scipy pillow`，然后 `PYTHONDONTWRITEBYTECODE=1 python3 Tools~/build_fonts.py`（字表、子集、JSON、衬底贴图、材质脚本、报告全部重新生成，约 10 s）。**不需要 `art/`**：颜色求解器在 `Tools~/colour_sim/` 里（§0.2 m2）；有 `art/` 时自动改用并核对圣经的那一份；
3. `python3 Tools~/make_proofs.py`（校样，约 5 分钟）；
4. Unity 里依次跑 §3.2 的 ① 和 ②。

只加一两个字的话，也可以直接把字加进 charset 文件，用 Font Asset Creator 重做那一个资产。子集里没有的字，**先把 `Originals~/` 里的原件复制到 `Assets/` 下面**（Unity 不导入 `~` 结尾的文件夹）再做源；原件没有 `kern` 表，U+2014 也是原样的。**占位名字填好之后一定要这样加字**，否则 TMP 会显示方框。

---

## 7. `strings_all.json` 的结构（给 Director 用）

```
_about / generated / display_rule   说明、生成时间、显示规则（§7.4-7）的文字版
fonts{key}              源字体、子集文件、字表文件、TMP 资产名、图集、TMP 行距；rfn_names（保留字名）
by_font{key}[]          {text, used_by[]}：这个字体要显示的每一个字符串
poems[]                 id, scene, bible, source, source_en, size_main, size_tr（度）, color_target（屏幕目标）, opacity,
                        opacity_note（晨句）, scrim（'light' | 'dark' | null）, scrim_note（暮句）, place[方位, 仰角, 距离],
                        cue, t_appear, hold_s, t_exit, t_gone, exit_s（庄子）, hold_formula_s, hold_formula_count（公式里数的字 / 词数）,
                        hold_note, line_cues（Urlicht）,
                        trigger, exit, treatment, staging, mirror / tr_display（庄子）,
                        grade（求解用的调色，例如 "S2→S3@0.299"）, profile, face_color{grade, profile, target, fill_hdr, fill_linear,
                        solve_error_codes, screen_of_fill, screen_luma, x_T0, bloom_share_opaque, bloom_share_at_alpha, alpha,
                        naive_vertex_colour_screen / _luma（照字面填 Vertex Color 会读成什么）, grade_note, screen_over_hold[] 与
                        single_profile_fill_would_be（李白 I、里尔克）}, scrim_fill{同上},
                        original{lang, font, lines[], tmp_text}, translations{zh|ja|en}{font, lines[], tmp_text},
                        segments[]{main[], zh[], ja[], en[], t, label, upright}, display_by_player_language{zh, ja, en, de, other}
  layout{zh|ja|en|de|other}       ← 这个玩家语言下的完整摆法（每首诗一张卡）
    player, anchor[方位, 仰角, 距离], block_center_el, shift_deg, translation, rule（庄子：字列规则的文字版）
    timing{cue, t_appear, focus_s, hold_s, t_exit, t_gone, exit, hold_formula_s, line_cues?, note?,
           t_settled? / focus_note?（天问：逐字对焦 2.4 s，1011.61 就位，§4.8）}
    objects[]  role(main|translation|mirror|caption), id（庄子）, lang, font, tmp_asset, size_deg, font_size,
               character_spacing, line_spacing, alignment='Baseline', lines[], tmp_text, tmp_text_rich,
               optical_offsets_em[], line_local_x_m[], first_baseline_el, line_baselines_el[], top_el, bottom_el, center_el,
               width_deg[], local_y_m, scale_y,
               alpha, vertex_color[1,1,1,alpha], material（预设名）, material_instance='own',
               outline_softness_anim[0.9, 终值], face_dilate{desktop, vr},
               （庄子另有）appear_s, appear_t, exit_at_s, exit_t, exit_s, fade_out_at_s, fade_out_t, fade_out_s, exit, outline_softness
               （天问另有）star_points[], char_objects[]
    scrims[]   style(block|line), texture, kind(light|dark), color_target, alpha（圣经）, alpha_unity, alpha_note,
               material, sprite_color[1,1,1,alpha_unity], for_object, appear_s, center_el, width_deg, height_deg,
               width_m, height_m, local_y_m, sprite_scale[3], render_queue=3009, azimuth_span_deg[2], note?
materials[]             name, kind(tmp_face|scrim), tmp_asset, poem, profile, target, fill_hdr, fill_linear；衬底另有 shader、
                        render_queue、alpha（圣经）（LanbaiPoemMaterials 的表）
colour_rule             颜色规则的文字说明
credits / credits_signkit_variant / coleridge_slip / destination_roll / ui（空）/ ui_note / charsets
layout_model / zhuangzi_rule   排版模型与庄子规则的文字说明
```

**显示规则（§7.4-7）：** 原文永远是主行，玩家自己的语言在下面。中文诗和梦中两句：中文玩家只看原文，日文玩家加書き下し或日译，其他人加英文。德文诗：德语玩家只看原文，中、日玩家加中译、日译，其他人加英文。济慈：英语、德语和“其他”只看原文，中、日玩家加中译、日译。玩家语言用 `VRCPlayerApi.GetCurrentLanguage()` 取，映射到 zh / ja / en / de / other，然后直接取 `layout[那个值]`。

---

## 8. 译文与書き下し（请母语者过目）

圣经要求“原文 + 自己的语言”，但圣经里没有译文。下面全部是美术组为这个世界写的。**上线前请一位日语母语者看書き下し和日译，一位英语母语者看英译。** 原文与圣经逐字一致。

| 幕 | 原文 | 書き下し / 日译 | 英译 | 中译 |
|---|---|---|---|---|
| 3 | 我欲因之梦吴越 / 一夜飞度镜湖月 | 我之に因りて / 呉越を夢みんと欲し / 一夜飛んで度る鏡湖の月 | I would dream my way to Wu and Yue, / and in one night fly across / the moon on Mirror Lake. | — |
| 3c | Denn das Schöne ist nichts / als des Schrecklichen Anfang | 美とは、恐ろしいものの / 始まりにほかならない | For beauty is nothing but / the beginning of terror | 因为美无非是 / 恐怖的开端 |
| 4 | Ach nein! / Ich ließ mich nicht abweisen! | **いいえ！**（第 3 版改）/ わたしは引き下がらなかった！ | Ah no! / I would not be turned away! | 啊，不！ / 我不肯被拒之门外！ |
| 6d | 我从天空坠入深海 | わたしは空から / 深い海へ墜ちた | I fell from the sky / into the deep sea | — |
| 7b | 鱼鳞屋兮龙堂 / 紫贝阙兮朱宫 / 灵何为兮水中 | 魚鱗の屋、龍の堂 / 紫貝の闕、朱の宮 / 霊何為れぞ水中にある | Houses of fish-scale, halls of dragons, / purple-shell gates, a vermilion palace — / O spirit, why do you dwell in the water? | — |
| 7c | 自深海坠入另一片天空 | 深い海から / もうひとつの空へ墜ちた | From the deep sea I fell / into another sky | — |
| 8-ii L1 | 天之苍苍，其正色邪？ | 天の蒼蒼たるは / 其れ正色なるか | The sky, so blue, so blue — / is that its true colour? | — |
| 8-ii L3 | 其视下也，亦若是则已矣 | 其の下を視るや / 亦た是くの若くならんのみ | Looking down from there, / it would be just the same. | — |
| 9a | 遂古之初，谁传道之？ / 上下未形，何由考之？ | 遂古の初め、誰か之を伝へ道ふ / 上下未だ形あらず / 何に由りて之を考ふる | At the far beginning of things, / who was there to tell of it? / When above and below had no form, / how could it be known? | — |
| 11 | 不知周之梦为胡蝶与 / 胡蝶之梦为周与 | 知らず / 周の夢に胡蝶と為れるか / 胡蝶の夢に周と為れるか | I cannot tell — / did Zhou dream he was a butterfly, / or does a butterfly dream it is Zhou? | — |
| 12 | 惟觉时之枕席 / 失向来之烟霞 | 惟だ覚めし時の枕席のみ / 向来の煙霞を失ふ | Only the pillow and mat of waking — / lost, the mists and rosy clouds of before. | — |
| 12 | Fled is that music:—Do I wake or sleep? | あの調べは消えた / わたしは醒めているのか / 眠っているのか | —（英文原文） | 那乐声已远去 / 我是醒着，还是睡着？ |

v2.1 不再显示的（已从字表和 JSON 删除）：Urlicht 的 *Da kam ein Engelein / und wollt' mich abweisen.* 一联及其译文；庄子 L2「其远而无所至极邪？」及其書き下し、英译。

几个决定：断行处的「，」「、」去掉（断行本身就是停顿），行末「？」「！」保留并做光学居中；書き下し用历史假名遣与日本字形；河伯取「朱宫」。齐物论英译的时态混用（did … or does …）是有意的。

---

## 9. 校样（`Docs~/`），每一张都逐块看过
- **`Proof_zh / ja / en / de.png`**：这四种语言的玩家在整趟旅程里看到的每一句，按圣经的视角比例（1° = 26 px），**全部取自这一版的 JSON**。每块说明栏：v2.1 的时刻、屏幕目标与填值（以及求解用的调色）、**Unity 模型读数**、bloom 检查、每个物体的中心仰角、紫的面积、光学居中。字和衬底按屏幕目标、不透明度和圣经的衬底强度在显示线性光里画——这就是 Unity 里应当得到的样子，说明栏里的 Unity 读数说明它确实会得到（§5.3）。背景是按各幕色板值画的示意，不是渲染。
- **`Proof_Trilingual_Zhuangzi.png`**：见 §4.7。大图和 2 × 2 时间条上都标了**日线 ±10°**和**暗衬在 Unity 里的实际外缘**（方位 12.0°，离日线端 2.0°）；最后一格是 991.0，日线收到 ±3.4°、字在分开。
- **`Proof_Credits.png`**：片尾和纸条的全部字符串（不是版式）。全文版片尾按 §5.5 下限字号要 3 196 mm 长，圣经允许的纸最长 1 400 mm，所以公告板只能用站牌套件的精简版。纸条的尺寸与算法见 §10-7。
- **检查结果**（`proof_report.json`）：画出 6 398 个字形，**0 缺字，没有豆腐块**；`build_fonts.py` 另外逐字对照了子集和原件的 cmap（PASS）。紫：第 4 幕以外所有面板 0.00%（上限 2%）；6d 按更严的规则（h 285–330、C\* > 12）也是 0%。

---

## 10. 已知限制、需要你们确认的
1. **三个 C# 文件都没有在 Unity 里编译过**（见开头）。`LanbaiTMPFontBuilder` 直接调用 `TMP_FontAsset.CreateFontAsset`（8 参）、`TryAddCharacters(string, out string)`、`HasCharacters(string, out List<char>)` 等，`ClearFontAssetData`、三参 `TryAddCharacters`、`UpdateGlyphAdjustmentRecords`、字距表走反射；`LanbaiPoemMaterials` 只用 `Material`、`AssetDatabase`、`PlayerSettings.colorSpace`、`Shader.Find("Sprites/Default")`；`LanbaiScrimTextureImport` 只用 `TextureImporter` 的标准属性。报错请原样回传。
2. **对齐方式：** 全部仰角按 `TextAlignmentOptions.Baseline` 给出（第一行基线落在物体位置；第 2 轮已对照 TMP 3.0.6 源码确认）。第一次做好后请按 §4.1 用小方块验证一次。
3. **`<space=…em>` 与居中**按 TMP 3.0 的行宽算法推出（第 2 轮已对照源码）。不想依赖它就每行一个物体、用 `line_local_x_m`。
4. **字距：** 请看 `VerifyAll()` 里 Garamond / Barlow 的 kerning pairs 是否大于 0。
5. **颜色依赖调色：** 填值是按圣经 `grades_final.json` 的外观模型求的，并已用调色套件的引擎模型核对（≤ 3 码，§5.3）。调色参数一改，就重跑 `build_fonts.py` 和 §3.2 ②。请在第一次实机截图时用取色器读一下李白 I（≈71.8 s 后）和晨句的字心：应为 `#DDD8CF` 左右（luma ≈ 216）和 `#1F2A3A`。
6. **需要核对的文本（圣经 §9-16）：** 片尾的演出者信息（Ferrier / Klemperer 1951；Walter / NYP 1958 等）请对照实际音源；Coleridge 纸条的文字请对照 1816 年 *Christabel* 那一卷的扫描件。書き下し与译文请母语者过目（§8）。
7. **请转告站牌套件：** ① 「——梦中得句」的破折号用全宽、居中、首尾相接的写法，这一行字距 0；② 片尾建议加 Type 一行；③ **纸条尺寸**与圣经 120 × 170 mm 不符，需要美术总监决定：IM FELL 7 mm、行距 1.22 时，最长诗行 143.5 mm，纸按“左边距 11 + 诗行缩进 9 + 最长诗行 143.5 + 余量 1 + 右边距 9”= **173.5 mm** 宽、151 mm 高；要放进 120 mm 宽，字得降到 7 × (120 − 29) / 143.5 ≈ **4.4 mm**。
8. **我们对圣经的延伸**（理由都在上文）：晨句不透明度 1.00（§0.2 MAJOR 3）；衬底的 SpriteRenderer α 另外求解（§0.3）；行末逗号去掉；庄子只镜像原文、译文进字幕位、上下分开退场（§4.7）；块超出 §7.3 范围时整块平移（§4.3）；衬底羽化比 40 px 宽、晨句衬底是超椭圆；世界里没有 UI 字。
