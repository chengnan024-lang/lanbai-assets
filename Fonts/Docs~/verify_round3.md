# Fonts 套件 · 对抗式验收报告（第 3 轮）

- **验收对象：** `deliver2/Fonts/` 的全部文件，以磁盘上的当前状态为准，不以构建报告为准。
- **依据：**
  - ART_BIBLE v2：§0–§1 全文、§4.7、§5.5、§6·3/4/6/7/8/8b/9/11/12 的诗句段、§7 全文、§7.6、§9-16；
  - lens_story §4、§6（片尾全文与 Coleridge 纸条）；
  - WORLD.md；
  - 第 1、2 轮报告。第 2 轮报告原文已存档到 `Docs~/verify_round2.md`，本文件覆盖了原来的 `verify.md`。
- **日期：** 2026-10-02。

## 结论：不通过（FAIL）

没有 blocker，有 3 个 major、8 个 minor。

**先说现状。** 第 2 轮验收（09-30 14:59）之后，修复步骤只做了一半。各文件的修改时间如下：

| 时间（09-30） | 文件 | 状态 |
|---|---|---|
| 15:24–15:27 | `lanbai_layout.py`、`lanbai_strings.py`、`lanbai_color.py`（新）、`gen_poem_materials.py`（新）、`strings_all.json`、字表、子集、`Editor/LanbaiPoemMaterials.cs`（新）、build_report | 已重新生成 |
| 15:29 | `make_proofs.py` | 改过，但之后没有运行 |
| 14:28 | `README_Fonts.md` | 第 2 轮之前的版本，一个字没动；与 `scratchpad/ffix/README_Fonts.md`（修复步骤开始时的备份）逐字节相同 |
| 14:18–14:23 | 6 张校样、`proof_report.json` | 第 2 轮之前的版本 |

因此：
- **数据层已经修好了第 2 轮的两个 major。** 颜色改成按幕求解的填值，衬底尺寸改成 `2·d·tan(θ/2)`。这两点我独立复算过，都对。
- **实现方真正要读的 README 仍然在教错的做法。** 校样也与交付的数据不一致。
- 新的颜色模型暴露出一个它自己算出来却没人处理的问题：第 6 幕的“深墨”在 Unity 里是浅石板灰。

构建报告（`notes` / `open_issues`）是第 1 轮修复时写的，没有提到第 2 轮，也漏列了 3 个新文件：`Editor/LanbaiPoemMaterials.cs`、`Tools~/lanbai_color.py`、`Tools~/gen_poem_materials.py`。

---

## A. 逐项核对：通过的部分

每一项都是我亲手复算或重做的，没有照抄构建报告。

| 项目 | 做法 | 结果 |
|---|---|---|
| 可复现 | 把整个套件复制到 `scratchpad/fv3/deliver2/Fonts`（`art/` 用软链接接上），重跑 `build_fonts.py`，用时 9.8 s | `strings_all.json` 除 `generated` 时间戳外完全相同；16 份字表、2 张衬底贴图、3 个 C# 文件逐字节相同；10 个子集除 `head` 的时间戳和 name ID 3 里的日期外逐表相同 |
| 原件真实性 | 重新从 raw.githubusercontent.com 下载 SourceHanSerifCN-Regular、SourceHanSerifJP-Regular、Barlow SemiBold、IMFeENrm28P 和 6 份许可，比对 md5 | 10/10 一致（第 2 轮另核过 6 个） |
| 子集有效性 | `python3 -m ots`，逐个检查 | 10/10 sanitized successfully |
| 字重与名字 | fontTools 读 OS/2、name、CFF 顶层名与 FDArray | SC/JP Regular 400，Medium 500，Sans Heavy 900，Barlow 600，Garamond 静态 400，没有 fvar。思源子集的名字全部是 `Lanbai…`，FDArray 也是。U+2014 指向全宽字形：advance 1000，墨迹 0–1000 × 360–400 |
| 字表 | 由 `by_font` 加上 139 个排版物体的全部行独立重算；检查 BOM、行尾换行、排序、去重、`+ascii` 超集；逐字查子集和原件的 cmap | 10 份精确字表、5 份 `+ascii` 都正确。ALL_CJK 226 字，等于 4 个 CJK 字表的并集。无 BOM，无行尾换行，全部 NFC。子集和原件都 0 缺字 |
| 字距 | 用 HarfBuzz 按原件 GPOS 排版，与子集的 `kern` 表比较，每个字体取 2 916 对字母和标点 | Garamond Regular、Italic、Barlow 都 0 处不一致（例如 AV −140 / −50 / −49） |
| §7.3 / §7.5 逐项 | 11 首诗：字号、译文字号、颜色目标、位置、停留，与圣经表逐一比对。每个物体检查：`font_size = 10·d·tan(字高)`，中心仰角在 [−15°, +10°]，行宽 ≤ 28°，CJK 字距 10、拉丁 0，基线节距 1.6 / 1.35 em，`local_y = d·tan(基线仰角 − anchor 仰角)` | 0 处不符 |
| 显示规则 §7.4-7 | `display_by_player_language` | 正确 |
| 第 2 轮 B.1（颜色）· 数据层 | 用圣经模拟器 `bible_work/calib_final.solve` 对 10 个目标独立求解 | 与 JSON 和 C# 里的填值逐位一致，误差 0 码。`materials` 覆盖了全部 37 个（字体资产 × 诗）组合，排版物体实际用到的组合一个不缺、也没有多余 |
| 第 2 轮 B.1 · C# | `LanbaiPoemMaterials.cs` 逐行读 | 用 `SetColor(linear.gamma)` 写入。Unity 在 Linear 项目里，小于 1 的值走 sRGB 曲线、大于 1 的值走 2.2 次方，`Color.gamma` 正是它的逆，所以 HDR 值也能精确送达；写完会回读校验。`_FaceColor` 在 TMP 里是 `[HDR]`。衬底 `_Color` 走 `Sprites/Default`，SpriteRenderer.color 为白色加 alpha。队列 3009 / 3010 |
| 第 2 轮 B.2（衬底尺寸） | 由 `width_m` 反算 Unity 里的实际张角 `2·atan(w/2d)`；`sprite_scale` 按 PPU 100 复算 | 实际张角等于设计张角（31.2°、38.74°、45.2°、40.8°、46.0°），`sprite_scale` 误差 ≤ 0.0004。L3 / L3′ 收窄到 46°，外缘在方位 12°，离 ±10° 的日线 2° |
| 第 2 轮 m1（庄子退场） | 读 JSON 各物体的 `exit` | 已改：L3 向下、L3′ 向上，每一对都朝两边分开 |
| C# 类型检查 | 用 `scratchpad/csc` 重跑 `compile_check/run_check.sh`（Roslyn，警告按错误处理，3 个文件） | `type-check OK`。**仍然没有在 Unity 里编译过** |
| 衬底贴图 | numpy / Pillow | 512×128、512×256，都是 2 的幂；RGBA，RGB 全为 255；alpha 0–1、256 级，单调，没有台阶反转，没有 NaN；四边 alpha = 0；左右、上下完全对称。法线贴图和平铺接缝不适用 |
| 许可 | 6 份许可，头部与 md5 | 齐全，与上游一致（Fell 的许可见 minor m1） |
| 原文与资料 | 11 首诗的原文与圣经逐字比对；片尾与 lens_story §6 比对；纸条与 1816 年序言比对（凭记忆核对，仍请对照扫描件） | 一致 |
| 校样目检 | 4 张语种校样各切 7–8 块，全分辨率看完；三语论点之帧切 6 块；片尾切 8 块；另外抽查了我重新生成的校样 | 没有豆腐块，没有错字。镜像字确实是上下翻转，不是旋转。破折号连续。字形都是 SC 字形（例如「觉」「镜」） |

---

## B. 第 2 轮问题的复核

| # | 数据 / C# | README | 校样 | 判定 |
|---|---|---|---|---|
| MAJOR B.1 颜色 | ✅ 已求解，`LanbaiPoemMaterials.cs` 已写好 | ❌ 仍写“Vertex Color 用圣经 §7.5 的颜色”、衬底“`color` = 衬底颜色” | ❌ 说明栏仍是旧的 | **未完成**（见 MAJOR 1） |
| MAJOR B.2 衬底尺寸 | ✅ | —（README 没写公式） | ❌ 还是旧的宽度，日线也没画出来 | **未完成**（见 MAJOR 2） |
| m1 庄子退场方向 | ✅ | ❌ §4.7 表格仍写 L3 向上、L3′ 向下 | — | README 未改 |
| m2 `LookRotation` 朝向 | — | ❌ 没写 | — | 未改 |
| m3 纸条数字 | — | ❌ 173 mm / “约 5 mm” | ❌ 174 mm / “约 4.4 mm” | 未改 |
| m4 Hann “均匀的暗” | — | ❌ 原措辞未改 | — | 未改 |
| m5 天问逐字对焦 | — | ❌ 没写 | — | 未改 |
| m6 母语者核对 | — | 仍在待办 | — | 照旧 |

---

## C. 问题

### MAJOR 1 · README 仍在教第 2 轮判定为错的做法，而且与 JSON、C# 互相矛盾

**错误的指示（实现方会照字面执行）：**
- `README_Fonts.md:169`：“**颜色：** Vertex Color 用圣经 §7.5 的颜色……显示亮度都在 luma 224 以下”。
  - 照这样做，屏幕上的颜色正是第 2 轮 B.1 表里的那些错误值。例如李白 `#ADB0B5`（luma 176），暖白变成了冷灰。
  - 同一个文件的 `strings_all.json` → `colour_rule` 写的却是“Vertex Color = 白（只用 alpha），颜色填在每首诗材质的 `_FaceColor`”。
- `README_Fonts.md:203–205`：衬底用“内置 `Sprites/Default`，另建一个材质”，“`color` = 衬底颜色”。
  - JSON 给的却是 `material: Lanbai_Scrim_Dark_S8` 和 `sprite_color: [1, 1, 1, α]`。
  - 照 README 做，暗衬会浅成 `#364B65`（luma 72），目标是 `#0E1A2F`（25）；亮衬会暗成 `#B2B7BA`，目标是 `#E8F1F5`。
  - `LanbaiScrimTextureImport.cs:7` 的注释也还写着 “colour and alpha go on SpriteRenderer.color”。

**缺失的内容：**
- 文件清单、§3.2、§9-1 里都没有 `Editor/LanbaiPoemMaterials.cs`（菜单 `蓝白/Fonts/Build Poem Materials`）。
- 没有写“先跑 `BuildAll()`，再跑 Poem Materials，然后把预设赋给每个 TMP 物体的 `fontSharedMaterial`”这条流程。
- 开头的警告和 §9-1 仍然说 “Editor/ 里的**两个** C# 文件未编译”，实际上是三个。
- 文件清单里没有 `lanbai_color.py`、`gen_poem_materials.py`。
- §6 的 JSON 结构仍写 `color`。实际字段已经改名为 `color_target`，并新增了 `face_color`、`scrim_fill`、`profile`，物体级的 `vertex_color` / `material`，以及顶层的 `materials`、`colour_rule`；衬底新增了 `material`、`sprite_color`、`azimuth_span_deg`，L3 / L3′ 还有 `note`。
- §0 仍是“第 2 版对第 1 轮的处理”，没有对第 2 轮的逐条回应。

**其他过期的地方：**
- §4.7 表格的 L3 / L3′ 退场方向与 JSON 相反。
- §8（`:341`）和 §1（`:66`）说“校样直接取自 JSON 的 layout，两者不会对不上”，现在不成立（见 MAJOR 2）。

**为什么是 major：** 第 2 轮 B.1 是 major，因为实现方会照 README 字面去做。这一点到现在没有任何改变，修好的只是实现方不会去读的那一层。

**修法：**
1. 按第 2 轮 C.1 改写 README 的 §0、§1、§3.2、§4.1、§4.5、§4.7、§6、§8、§9：
   - Vertex Color 用白色，只承载 alpha；
   - 每首诗用一个材质预设，HDR `_FaceColor` 填求解值（同时给出 `fill_hdr` 和 `fill_linear`）；
   - 衬底用 `Lanbai_Scrim_*_S6/S8` 材质，SpriteRenderer.color 为 (1, 1, 1, α)；
   - 写明构建顺序和三个未编译的 C# 文件。
2. 改掉 `LanbaiScrimTextureImport.cs` 的注释。
3. 在 `open_issues` 里补上三个新文件。

### MAJOR 2 · 交付的校样不是交付的数据画出来的；第 2 轮 C.2 没有做

- 6 张校样和 `proof_report.json` 生成于 14:18–14:23，在第 2 轮验收之前，也在数据修复（15:27）之前。所以：
  - 论点之帧里，L3 / L3′ 的衬底仍是旧的 49.6° 宽。在 `Proof_Trilingual_Zhuangzi.png` 上，它的外缘正好落在日线右端（方位约 10°）。JSON 里是 46°，外缘在方位 12°。
  - 所有说明栏都还是“`#E2DDD4 × 90%`”这样的旧写法，没有填值，也没有 Unity 模型的读数。
  - `make_proofs.py` 在 15:29 改过（加了 `colour_line`、`unity_check`），但从来没有运行。
- 第 2 轮 C.2 要求“重出论点之帧校样，并在图上标出日线范围”，两件都没做。我在副本里跑了新版 `make_proofs.py`（rc = 0，5 分 15 秒，0 缺字，紫 ≤ 0.01%）：说明栏正确了，衬底也变窄了，**但日线 ±10° 仍然没有画出来**。
- 我跑出来的那一套在 `scratchpad/fv3/deliver2/Fonts/Docs~/`，可以对照。
- **为什么是 major：** 这个套件的约定是“看过才算做完”，而交付的校样不是交付的数据，第 2 轮的通过条件也没有满足。
- **修法：**
  1. 在 `make_proofs.py` 的论点之帧大图和时间条上，画出日线 ±10°（第 8 幕 8-ii 的范围）和衬底的 Unity 外缘；
  2. 重跑，逐块重看，更新 README §8。

### MAJOR 3 · 第 6 幕“深墨”在 Unity 里是浅石板灰：屏幕目标差 52 luma，套件自己算出来了却没处理

- §7.5 第 6 幕的屏幕目标是**深墨 `#1F2A3A`（luma 41）**，“暗字写在亮上”，与暮那句的亮字 `#EADCD6` 互为照相底片。
- 我用套件自己的 Unity 模型 `lanbai_color.composite_check` 复算：在第 6 幕代表背景 `#B5B2B6` 上加亮衬 α 0.25，字的填值是 `#2F3848`。不同不透明度下的结果：

| 字的不透明度 | Unity 屏幕 | luma |
|---|---|---|
| **0.90（套件现在的值，§7.2 的通用值）** | **`#575E69`** | **93** |
| 0.95 | `#414A55` | 73 |
| 0.99 | `#283241` | 49 |
| 1.00 | `#1F2A3A` | 41（= 目标） |

- 我重新生成的英文校样，说明栏写的就是“字 #585F69 … luma 94”。交付的校样里，取字心最暗的 40 个像素，平均是 `#434A56`（luma 73），肉眼看也是灰字，不是墨字。
- 第 2 轮把“深墨变成浅石板灰（#49596A，luma 87）”判为 major 的核心理由。B.1 的修复只解决了“填值”，没有解决这个问题：现在的结果（luma 93）比那时还浅。
- **原因：** Unity 在线性帧缓冲里做 alpha 混合，10% 的明亮天光（线性约 0.6）透过来，就把暗字抬起来了。圣经 §7.2 的“不透明度 90%”是按亮字写的通用参数。法律第 1 条：屏幕目标是法律，参数只是起点，“改参数去追目标，永远不改目标”。
- **修法：**
  1. 把 `P06_Dream_Dawn` 的 `opacity` 设为 1.00，至少 0.99。暗字不透明并不刺眼。
  2. 重新生成，并在 README 里写明这是对 §7.2 的一处有理由的偏离。
  3. 也可以交给美术总监裁决，但要写明不改的代价：晨那句会读成灰字。

### minor

- **m1 IM FELL 子集保留了字体自己声明的保留字名。**
  - 两个原件的 name ID 0 写着 “With Reserved Font Name IM FELL English Roman” / “… IM FELL English SC”。
  - 子集属于修改版，但 family / full / PS 名原样保留（`IM FELL English`、`IM_FELL_English_Roman`）。README §2b 写的是“RFN：无”。
  - 上游 `OFL.txt` 没有列出 RFN，所以上游自己就有矛盾。
  - 这两个字体是可选的（纸条已经由站牌套件烘成贴图），稳妥的做法任选其一：像思源一样改名为 `Lanbai Fell …`；或者只交付原件、不交付子集。同时更正 §2b。
- **m2 `build_fonts.py` 现在硬依赖 `KIT/../../art/bible_work`。**
  - 离开 scratchpad 的目录结构就不能用：放进仓库 lanbai-assets 后，`Art/` 里没有 `bible_work`，大小写也不同；放进 Unity 项目也一样。`lanbai_color.sim()` 会直接 `SystemExit`，JSON 和字表一个都不写，README §5 “加字或改字”的流程因此断掉。
  - 修法：缺少 `bible_work` 时，沿用上一版 JSON 里的 `face_color` / `scrim_fill` 并给出警告；或者把求解器的最小部分放进 `Tools~`。README 写明。
- **m3 第 2 轮的 4 个 minor 在 README 里都没改**（m2 LookRotation、m3 纸条数字、m4 alpha-over 措辞、m5 天问拆成 16 个单字物体）。改法照第 2 轮报告。
- **m4 同一首诗的预设被正字和镜像字共用，但两者的材质参数不同。**
  - 例如庄子的 L1 和 L1′ 都用 `Lanbai_SerifSC_Regular SDF - P08b_Zhuangzi_Xiaoyao`。正字的 `_OutlineSoftness` 要从 0.9 动画到 0，镜像字要一直保持 0.3；VR 的 Face Dilate 也是按材质设的。
  - 如果 Director 直接改共享的预设，二者会互相干扰。
  - 修法（README 写明）：每个文本物体用自己的材质实例（TMP 的 `fontMaterial`，或者 Udon 侧复制一份），预设只作为初值；或者另出一份镜像字预设，softness 固定 0.3。
- **m5 亮字在 90% / 80% 不透明度下比目标暗 4–11 码。**
  - Unity 模型的读数：李白 216（目标 221），里尔克 216（221），河伯、天问、第 12 幕 219.5（224），暮 218.5（222.5），齐物论 204（215，按 80% 低对比，属于有意为之）。
  - 都在可接受范围内，但 README 应当写明“屏幕读数比目标低几码”。如果要严格追目标，可以对典型背景解合成后的填值。
- **m6 日译「ああ、いいえ！」（Ach nein!）偏生硬。** 建议改成「いいえ！」或「いいえ、いやです！」，仍请日语母语者定稿。英译、書き下し的其余部分我读过，没有发现错误；齐物论的时态混用读来自然，可以保留。
- **m7 `Tools~/__pycache__/` 被打包进了套件**（4 个 .pyc，约 86 KB）。Unity 不会导入它，但它不该进仓库。修法：删掉，或加进 `.gitignore`。
- **m8 构建报告过期。** `files` 漏了 3 个新文件；`notes` / `open_issues` 只讲第 1 轮，并写着 “Both C# files”。

---

## D. 通过所需（只列 major）

1. **MAJOR 1：** README 全面改成数据层已经采用的颜色和衬底做法（Vertex Color 白加 alpha；每首诗一个预设，HDR `_FaceColor` 填求解值；衬底材质填 `_Color`，SpriteRenderer.color 白加 alpha）；写入 `LanbaiPoemMaterials.cs` 和构建顺序；§0 逐条回应第 2 轮；§4.7、§6、§8、§9 与 JSON 对齐；改掉 `LanbaiScrimTextureImport.cs` 的注释。
2. **MAJOR 2：** 在论点之帧校样上画出日线 ±10° 和 Unity 实际的衬底外缘，然后重跑 `make_proofs.py`，把 6 张校样和 `proof_report.json` 换成新版，逐块重看。
3. **MAJOR 3：** 让第 6 幕的屏幕读数达到 `#1F2A3A`（opacity 1.0），重新生成，并在说明栏里核对 Unity 模型读数 ≈ luma 41。

minor 建议一起改，不是通过条件。

## E. 证据与副本

- **重新生成的副本：** `scratchpad/fv3/deliver2/Fonts/`。`build_fonts.py` 和新版 `make_proofs.py` 都跑通了；`Docs~/` 里有新校样，`proof_report.json` 里有 55 条 `composite` 记录。
- **我看过的切块：** `scratchpad/fv3/crops/`，包括 `s_*`、`tri_*`、`cr_*` 和新校样的 `n_*`。
- **上游比对文件：** `scratchpad/fv3/up/`。
- **第 2 轮报告原文：** `Docs~/verify_round2.md`。
