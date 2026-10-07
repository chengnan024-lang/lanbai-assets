# Fonts 套件 · 对抗式验收报告（第 2 轮）

验收对象：`deliver2/Fonts/` 全部文件（README_Fonts.md、strings_all.json、Charsets/、Subset/、Originals~/、Licenses/、Textures/、Editor/、Docs~/、Tools~/）
依据：ART_BIBLE v2 §0–§1 全文、§4.4、§4.7、§5.5、§6·3/4/6/7/8/8b/9/11/12 的诗句段、§7 全文、§7.6、§9-16；lens_story §6（片尾全文与 Coleridge 纸条）；WORLD.md。另外从 needle-mirror 下载了 **TextMeshPro 3.0.6 的真实源码**（`TMP_Text.cs`、`TMPro_Private.cs`、`TMP_FontAsset.cs`、Font Asset Creator、`TMP_SDF.shader`），逐条核对套件对 TMP 行为的假设。
日期：2026-09-30。

**结论：不通过（FAIL）。** 没有 blocker：没有缺字，字体全部有效且与上游逐字节一致，字表完整，许可齐全，C# 与 TMP 3.0.6 的真实 API 对得上。第 1 轮的 2 个 major 和 12 个 minor 都已真正修好（见 A.2）。但这一轮查出 **2 个新的 major**，两个都会让 Unity 里的实际画面偏离我们看过、认可过的校样：

1. **诗句颜色**：README 让实现方把圣经的目标色直接填进 TMP 的 Vertex Color。TMP 3.0.6 不做色彩空间转换，文字又要经过每幕的调色，所以屏幕上的颜色会偏离圣经目标 15–45 个 luma，暖白会变成冷灰。
2. **衬底尺寸**：JSON 里衬底的米制宽度按 `d·tan(全角)` 计算，比校样宽 8–27%。论点之帧里，暗衬会压到日线的右端上。

两处都容易改，改完、重新生成 JSON 并复核后，这个套件就可以交付。

---

## A. 逐项核对

### A.1 通过的部分（全部亲手复算或重做，没有照抄构建报告）

| 项目 | 做法 | 结果 |
|---|---|---|
| 原件真实性 | 重新从 raw.githubusercontent.com 下载 EBGaramond[wght]、EBGaramond-Italic[wght]、IMFeENsc28P、SourceHanSerifJP-Medium、SourceHanSerifCN-Medium、SourceHanSansCN-Heavy，以及 4 份许可，比对 md5 | 10/10 逐字节一致（第 1 轮另核了 Barlow、Fell Roman、SHS CN Regular） |
| 子集有效性 | `python3 -m ots` 逐个检查 10 个子集 | 10/10 通过 |
| 字重与名字 | fontTools 读 OS/2、name、CFF 顶层名与 FDArray | SC/JP Regular 400、Medium 500，Sans Heavy 900，Barlow 600，Garamond 静态 400（没有 fvar）。思源子集的 name 1/3/4/6/16/17 和 CFF 顶层名、FDArray 名全部是 `Lanbai…`；“Source”只留在版权、商标、许可、描述里。Garamond Italic 的 PS 名是 `EBGaramond-Italic`（第 1 轮 m5、m12 已修） |
| U+2014 改指向（第 1 轮 m2） | 读 3 个 Serif 子集的 cmap 和字形边界 | U+2014 指向 U+2500 的字形：advance 1000，墨迹 0–1000 × 360–400，落在汉字中线上。`Proof_Credits.png` 放大 3 倍看，「——梦中得句」是一条连续的线，高度居中 |
| 字表 | 由 `by_font` 独立重算；检查 BOM、行尾换行、排序、去重、`+ascii` 超集；逐字查子集和原件的 cmap | 10 份字表全部与重算结果一致。无 BOM，末尾无换行，按码位排序。子集和原件都不缺字 |
| 实际显示的每个文本物体 | 遍历 `poems[].layout[5 种玩家语言]` 的全部 139 个文本物体，逐行查所用字体的字表 | 0 缺字，`tmp_asset` 与字体对应正确 |
| 原文逐字比对 | 11 首诗的原文与圣经 §7.5 表逐字比对（忽略断行和标点）；片尾对照 lens_story §6；纸条对照 lens_story 引的 1816 年序言 | 全部命中，NFC 规范化 |
| 显示规则 §7.4-7 | 每首诗的 `display_by_player_language` | 正确：中文诗 zh 只看原文、ja 加書き下し、其余加英译；德文诗 de 只看原文；济慈 en/de/other 只看原文 |
| 位置、颜色值、字号、停留 §7.5 | JSON 与圣经表逐项对照 | 11/11 一致（颜色的**用法**有问题，见 B.1） |
| 字号公式 | 查 TMP 源码：3D 模式 `m_fontScale = fontSize / pointSize × 0.1`；逐行复算 README §4.6 的表 | 1 em = 0.1 × fontSize，正确。23.05、9.43、5.76、3.49、6.98、7.86 全部复算一致 |
| Baseline 对齐 | TMP 3.0.6 `TMPro_Private.cs:3491`：`anchorOffset = (corners[0] + corners[1]) / 2`，第一行基线 y = 0 | 第一条基线落在 rect 垂直中点上，pivot (0.5, 0.5) 时就是物体位置。套件的假设正确（README 要求的 1 cm 方块验证仍然值得做） |
| 行距 | `TMPro_Private.cs:3249`：`lineOffsetDelta = −maxLineDescender + ascender + lineGap + m_lineSpacing × 0.01 em`，其中 ascender / descender 取字体的 faceInfo | 行距 = lineHeight + Line Spacing × 0.01 em。思源 1.437 + 0.163 = 1.600，Garamond 1.305 + 0.045 = 1.350，正确 |
| `<space=Xem>` 光学居中 | 查 TMP 源码的 `<space>` 处理（em 单位 = 值 × 0.1 × fontSize）和 Center 对齐（`width/2 − maxAdvance/2`，maxAdvance 包含行首空格，并减去末字的字距） | 行首空 s，行就右移 s/2。`tmp_text_rich` 写的是 2 × offset，正确。天问 `star_points` 的 x 也已含这个偏移（复算「遂」−4.695 em，一致） |
| 镜像字 `localScale.y = −1` | 查 TMP 源码：`xScale = scale × Mathf.Abs(lossyScale)`（`TMPro_Private.cs:3777`），`UpdateSDFScale` 用 `Mathf.Abs(scaleDelta)`；Distance Field shader 是 `Cull [_CullMode]`，默认 0 | 负缩放不会被误判成粗体，两面都画。镜像做法可行 |
| 庄子版式（第 1 轮 MAJOR 1） | 复算 6 行加字幕位的 em 框 | L1 +8.80、L2 +5.28、L3′ +1.76、L3 −1.76、L2′ −5.28、L1′ −8.80，节距都是 3.52°（1.6 em），地平线两侧各 0.66°。英文字幕 −12.88°、日文字幕 −13.12°，全部在 [−15°, +10°] 内。垂直检查覆盖全部 5 种语言、所有诗的每个物体，都 PASS |
| 第 8 幕去紫（第 1 轮 MAJOR 2） | 自己把论点之帧整幅面板换算到 CIE Lab 测量 | h 290–325 且 C\* > 15 的面积 **0.00%**（上限 2%）。有 10% 的像素色相落在 290–320，但 C\* ≤ 15，属于允许的低彩度靛灰。取样：上天 `#949AB0`（h 282）、日带 `#CBAA8F`（h 66） |
| 字距 kern 表 | ① 重跑 `check_kern_freetype.py`（FreeType 2.13.2）；② 用 HarfBuzz 按原件 GPOS 排版，与注入的 `kern` 表逐对比较（每个字体约 10 400 对） | FreeType 读回的值与表一致；Garamond Regular、Italic、Barlow 都是 **0 处不一致** |
| TMP 3.0 只读 `kern` 表 | 查 Font Asset Creator 源码 | “Get Kerning Pairs” → `GetKerningTable()`，读的是 FontEngine 的 `kern` 表，所以注入是必要的 |
| C# 编辑器脚本 | ① 用本机 Roslyn 重跑 `compile_check/run_check.sh`（警告按错误处理）→ OK；② 对照 TMP 3.0.6 真实源码逐个核对所用成员 | 全部存在，语义也对：`CreateFontAsset` 的 8 参重载；`TryAddCharacters(string, out string, bool includeFontFeatures = false)`（3.0.6 只有这一个带 out 的字符串重载，反射能命中，两参调用也能编译）；`HasCharacters(string, out List<char>)`；`ClearFontAssetData(bool)`（public）；`UpdateGlyphAdjustmentRecords()`（internal，反射能调）；私有字段 `m_SourceFontFile`，内部字段 `m_SourceFontFile_EditorRef`、`m_AtlasWidth/Height/Padding/RenderMode`；`TryAddCharacters` 遇到 0×0 图集会按 `m_AtlasWidth/Height` 重设尺寸。“先设尺寸、再 Clear”的顺序正确。**仍然没有在 Unity 里编译过**，README 写明了这一点 |
| 衬底贴图 | numpy/PIL 读两张 PNG | 512×128、512×256，都是 2 的幂；RGBA，RGB 全白；alpha 0–1、256 级，没有色带、没有 NaN；四边 alpha 都是 0（Clamp 下不会拉出条纹）；左右、上下完全对称；与 `scrim_alpha` 的解析剖面相差 ≤ 0.002。Line 贴图的 Hann 窗按半高错位相加恰好等于 1（见 minor m4） |
| 法线贴图、平铺接缝 | — | 不适用：本套件没有法线贴图，衬底贴图也不平铺 |
| 许可 | 6 份许可文件，头部与 md5 | 齐全且正确（Fell 两份是同一个 OFL.txt，属正常） |
| 校样目检 | 四张语种校样各切 6 块全分辨率看完；论点之帧校样看整体、左右两半、日文栏和时间条；片尾校样切 3 块，破折号放大 3 倍 | 没有豆腐块，没有错字。中、日、英、德文本都读过一遍，没有拼写错误。庄子镜像字确实是上下翻转，不是旋转；「？」「！」的位置符合 SC 字形的大陆规范；Fell 的短粗破折号是原字体的设计 |
| 子集大小 | `du -b` | 0.708 MB，与报告一致。46.75 MB 这个数只算了用作子集来源的原件，不含静态实例 |
| 范围 | 圣经 §4.4 / §4.7 / §6·2 查找所有“字” | 收音机刻度和仪表“无数字”，目的地牌已列入（贴图），站牌按用户要求不在范围内，世界里没有 UI 字。与套件一致 |

### A.2 第 1 轮问题的复核

| # | 复核结果 |
|---|---|
| MAJOR 1 庄子字墙 | **已修**（见 A.1） |
| MAJOR 2 第 8 幕紫 | **已修**（实测 0.00%） |
| m1 光学居中 | 已修。14 行偏移，数值复算一致，TMP 机制已对照源码确认 |
| m2 破折号 | 已修（见 A.1） |
| m3 全文版片尾放不下 | 已写明 |
| m4 Type 一行 | 已更正 |
| m5 FDArray 名 | 已修 |
| m6 BusGlass | 已核实 |
| m7 書き下し「は」 | 已改（「天の蒼蒼たるは / 其れ正色なるか」），仍请母语者过目 |
| m8 Originals~ 用法 | 已改 |
| m9 C# 顺序与日志 | 已改，并对照 3.0.6 源码确认 |
| m10 纸条尺寸 | 已标注，但 README 和校样的数字不一致（见 m3） |
| m11 LITE 铭牌 | 已撤回 |
| m12 PS 名 | 已修 |

---

## B. 问题

### MAJOR B.1 诗句颜色：照 README 填进 TMP Vertex Color，屏幕上不会是圣经的颜色

- **README 的原话**（`README_Fonts.md:169`）：“Vertex Color 用圣经 §7.5 的颜色……显示亮度都在 luma 224 以下”。`strings_all.json` 的 `color` 字段也是这些 hex。
- **为什么不对：**
  1. 圣经的法律第 1 条：文中 hex 除特别注明外，都是**屏幕目标值**。§7.5 的诗句颜色没有注明是“填”，所以是目标。§1.6 又规定无光照、自发光的东西必须以场景线性值进入调色。诗句是无光照的，要经过每一幕的 PPv2 grade（Neutral 色调映射、postExposure、白平衡、对比度）。
  2. **TMP 3.0.6 不做色彩空间转换**。`TMP_Text.cs`、`TMPro_Private.cs` 里没有任何 `ColorSpace`、`linear`、`GammaToLinear`；`TMP_SDF.shader` 第 257 行是 `faceColor.rgb *= input.color.rgb`。VRChat 项目是 Linear 色彩空间，所以 Vertex Color 的字节会被**原样当作线性值**用。
- **量化**（用圣经自己的模拟器 `art/bible_work/calib_final.py` 的 `disp_hex` / `solve`，按各幕 profile 计算；这是 `calib_final.md` §B 求填值用的同一套代码）：

| 诗 | profile | 圣经目标（luma） | 照 README 填 → 屏幕（luma） | 需要的填值（HDR 取色器） |
|---|---|---|---|---|
| 3 李白 | S3 | `#E2DDD4`（221） | `#ADB0B5`（176）：暖白变成冷灰 | `#FFECCD @ +1.21` |
| 4a/4b 里尔克、Urlicht | S4 | `#D8DDE6`（221） | `#ADB3BC`（178） | `#EEF1FF @ +1.05` |
| 6 晨句（深墨） | S6 | `#1F2A3A`（41） | `#49596A`（87）：深墨变成浅石板灰，“暗字写在亮上”的底片关系没了 | `#2F3848` |
| 7 河伯 | S7b | `#D9E2E7`（224） | `#C0C7CF`（198） | `#F2FDFF @ +0.60` |
| 8 暮句、庄子 | S8 | `#EADCD6`（223） | `#C5BDB8`（190）：论点之帧的字变暗、变灰 | `#FFE5E0 @ +1.00` |
| 9a 天问 | S9a | `#D9E2E7`（224） | `#DADFE5`（222），碰巧接近 | `#EBF9FA` |
| 11 齐物论 | S11 | `#E0D6C4`（215） | `#CBCAC9`（202）：暖色没了 | `#FFE1AE @ +0.50` |
| 12 李白、济慈 | S12 | `#D9E2E7`（224） | `#CED2D7`（210） | `#E6F9FF @ +0.40` |

  即使实现方知道要把 hex 先转成线性，结果也只好一点（例如 S3 → `#A3A5A7`，luma 165）。多数填值都**大于 1（HDR）**，Color32 的 Vertex Color 根本表示不了。校样画的是目标色（在线性光里混合），所以校样好看，Unity 里的实际画面却会是上表中间那一列。
- **为什么是 major：** 所有诗句的颜色和亮度都会偏，而且正好偏在三个关键处：论点之帧、两句梦中句的“互为底片”、李白的暖白。这直接违反圣经的第一条法律，而实现方会照着 README 字面去做。
- **修法：**
  1. 在 `lanbai_strings.py` / `build_fonts.py` 里，用 `bible_work/calib_final.solve()` 为每首诗（按它所在幕的 profile）求出填值，写进 JSON，例如 `face_color_fill: "#FFECCD @ +1.21"`。
  2. README §4.1 改成：Vertex Color = **白色**（只用 alpha 表示不透明度：0.90、0.80、0.45）；颜色填到**每首诗自己的材质实例的 `_FaceColor`**。`_FaceColor` 是 `[HDR]` 颜色，Unity 会把它转成线性，Intensity 就是 `@ +n`。Face Dilate 本来就要改材质实例，正好一起做。
  3. 衬底的 `#0E1A2F` α0.30 和 `#E8F1F5` α0.25 同样在调色之前混合，也按同一方法求解或核实，并写明 SpriteRenderer.color 在 Linear 项目里的处理方式。
  4. 删掉“显示亮度都在 luma 224 以下”这句无依据的断言，改成求解后复算的“屏幕 luma ≤ 224”。

### MAJOR B.2 衬底的米制尺寸按 `d·tan(全角)` 计算：Unity 里比校样宽 8–27%，论点之帧的暗衬压到日线上

- **代码：** `Tools~/lanbai_layout.py:327` 写的是 `wm, hm = em_m(d, w_deg), em_m(d, h_deg)`，也就是 `d·tan(w)`。一块张角 w 的平面宽度应为 `2·d·tan(w/2)`。`width_m`、`height_m`、`sprite_scale` 都由它得出，Director 会直接拿去用。校样（`make_proofs.draw_scrims`）按 `width_deg` 画，所以 README 说的“JSON 和校样都调它，所以两者不会对不上”，对衬底来说不成立。
- **量化**（Unity 里实际的张角 = `2·atan(width_m / 2d)`）：

| 衬底 | 设计张角 | Unity 实际张角 | 方位范围（Unity） |
|---|---|---|---|
| 6 晨句 | 31.2° | 33.7°（+8%） | −31.8° … +1.8° |
| 8 暮句 | 38.7° | 43.7°（+14%） | −36.9° … +6.9° |
| 庄子 L1 / L1′ | 45.2° | 53.5°（+21%） | 8.3° … 61.7° |
| 庄子 L2 / L2′ | 40.8° | 46.7°（+16%） | 11.7° … 58.3° |
| **庄子 L3 / L3′** | 49.6° | **60.9°（+27%）** | **4.6°** … 65.4°（设计是 10.2° … 59.8°） |

- **后果：** 8-ii 里日线在方位 ±10°、仰角 0°（§6·8b：F12 时从 ±10° 收缩），圣经 §6·8 要求庄子“**永远不压在日线上**”，“要避免”里也有“任何东西穿过日线”。按 Unity 实际几何模拟 L3 + L3′ 两张衬底，仰角 0° 处的暗衬不透明度：方位 +8° 是 0.059，+10° 是 0.127，+12° 是 0.195；按设计尺寸（也就是校样），这三处分别是 0、0、0.024。日线右半段会被暗衬压暗、先于左半段淡掉，全片唯一的对称构图变得不对称。对照图：`scratchpad/fv2/scrim_unity_vs_proof.png`（红线 = 日线 ±10°，蓝线 = Unity 里暗衬的边 4.6°，绿线 = 设计的边 10.2°）。
- **修法：** 改成 `wm = 2·d·tan(w/2)`，`hm = 2·d·tan(h/2)`，重新生成 JSON。另外建议把 L3 / L3′ 衬底的外缘从 10.2° 再收进来 ≥ 2°（例如 core 放宽、总宽减小），给日线的辉光留出余量。重出论点之帧校样时，把日线 ±10° 画上去。

### minor

- **m1 庄子第三行的退场方向与 §7.4-4 “镜像字两向分开”相反。** 现在 L3（正字，在地平线下）向上漂，L3′（镜像，在地平线上）向下漂，两者朝地平线、日线的高度**靠拢**；L1、L2 两对则是分开的。圣经 §6·8 写“正字向上、镜像字向下”，那是按正字在上写的；§7.4-4 说“庄子的镜像字两向分开”。建议统一成：地平线上的物体向上漂，地平线下的向下漂。这样每一对都分开，反射关系也保持精确。
- **m2 “朝向玩家的头”说得不够死。** TMP 的字只有在物体 +Z 背向观看者时才是正读的。如果实现方写 `parent.LookAt(head)`，所有字都会左右反过来，z = +0.01 的衬底也会跑到字的前面。README §4.2 请写明：`parent.rotation = Quaternion.LookRotation(parent.position − headPos, Vector3.up)`。
- **m3 纸条数字前后不一致。** README 写 173 × 151 mm、“把字降到约 5 mm”；`Proof_Credits.png` 的说明写 174 × 151 mm、最长诗行 144 mm、“约 4.4 mm”。请统一，并写明算法（页边距是多少）。
- **m4 “一整块均匀的暗”只在相加时成立。** 衬底是 alpha-over 叠加，不是相加：两条 Hann 带在行间的合成不透明度是 1 − (1 − 0.15)² = 0.2775，行心是 0.300，有 7.5% 的起伏（行间略浅，不会出现暗条纹）。视觉上可以忽略，README 的措辞可以改准确一点。
- **m5 天问的“逐字对焦”（softness 0.9 → 0，0.6 s，120 ms 错开）不能在一个 TMP 物体上做。** `_OutlineSoftness` 是材质属性，没法逐字设置。建议 README 注明：天问按 `star_points` 拆成 16 个单字物体（每字一个材质实例，或者改顶点数据），也方便 F13 时逐字变暗。这个主要是 Director 的事，这里只提醒一句。
- **m6 仍然要人工核对的（沿用）：** 書き下し请日语母语者过目，英译请英语母语者过目（例如齐物论 “did Zhou dream … or does a butterfly dream …” 的时态混用是不是有意的）；演出者信息与 1816 年纸条原文按 §9-16 核对。

---

## C. 通过所需

1. **B.1：** 为每首诗求出按其所在幕 profile 的填值，写进 JSON；README 改成“Vertex Color 白 + alpha，颜色填材质实例的 HDR `_FaceColor`”；衬底颜色同样处理；用求解后的值复算屏幕 luma ≤ 224。
2. **B.2：** 衬底尺寸改用 `2·d·tan(θ/2)`，重新生成 `strings_all.json`；L3 / L3′ 衬底离开日线 ±10°；重出论点之帧校样并在图上标出日线范围。

minor 建议一起改，不是通过条件。改完请重跑 `build_fonts.py` 和 `make_proofs.py`，并更新 README §0。
