# Fonts 套件 · 对抗式验收报告（verify）

验收对象：`deliver2/Fonts/`（README_Fonts.md、strings_all.json、Charsets/、Subset/、Originals~/、Licenses/、Editor/、Docs~/、Tools~/）
依据：ART_BIBLE v2 §0–§1 全文、§4.7、§5.5、§6·3/4/6/7/8/9/11/12 的诗句段、§7 全文、§7.6、§9-16；lens_story §4、§6（片尾全文）；WORLD.md。
日期：2026-09-30。

**结论：不通过（FAIL）。** 没有 blocker：没有缺字，字体有效，字表完整，许可齐全。但有 **2 个 major**，两个都出在“全世界的论点之帧”，也就是第 8 幕庄子的校样和版式上。修好以后这个套件就可以交付。

---

## A. 逐项核对：通过的部分（都亲手复算过，没有照抄构建报告）

| 项目 | 做法 | 结果 |
|---|---|---|
| 原件真实性 | Barlow、IM FELL Roman、思源宋体 LICENSE 重新从 raw.githubusercontent.com 下载，比对 md5。SourceHanSerifCN-Regular 比对 Content-Length | 逐字节一致（11 626 108 B） |
| 字重与 name 表 | fontTools 读 OS/2 usWeightClass 和 name | SC/JP Regular 400、Medium 500；Sans SC Heavy 900；Barlow SemiBold 600；Garamond 静态实例 400，没有 fvar |
| 子集字体有效性 | OTS（opentype-sanitizer）逐个检查 10 个子集；PIL/FreeType 能渲染 | 10/10 通过 |
| 思源改名（OFL RFN） | 所有 name 记录，包括 0x804 / 0x411 的本地化记录，以及 CFF 顶层 FontName / FullName / FamilyName | 用户可见的名字都已改成 Lanbai…。例外见 m5 |
| 许可 | 6 份许可文件的头部 + md5 | 各自正确。Fell 的两份一致，这是正常的（同一个 OFL.txt） |
| 字表 | 由 `by_font` 重新求字表；检查去重、按码位排序、UTF-8、无 BOM、文件末尾无换行，以及每个字符在子集和原件的 cmap 里都存在 | 10 份字表全部一致，没有缺字。`+ascii` 版是精确版的超集，且包含全部可打印 ASCII |
| 字符串完整性 | 11 首诗对照圣经 §7.5 原文逐字比对（去掉断行与句末标点后）；片尾对照 lens_story §6；站牌套件精简版对照 `deliver2/Sign/Tools~/src/credits.json`；Coleridge 纸条对照 1816 年序言；目的地牌 | 全部命中。NFC 规范化，没有组合附加符、没有控制字符 |
| 显示规则 §7.4-7 | 每首诗的 `display_by_player_language` | 正确（中文诗：zh 只看原文、ja 加書き下し、其他加 en；德文诗：de 只看原文；济慈：en / de / other 只看原文） |
| 位置、颜色、字号 §7.5 | JSON 的 place / color / opacity / scrim / size 对照圣经表 | 11/11 一致 |
| fontSize 公式 | 10·d·tan θ（TMP 3D 下 1 em = 0.1·fontSize），逐行复算 README 的字号表 | 一致（例如 16.76、23.05、9.43、6.98） |
| TMP 行距 | hhea：思源 1151/−286/0 → 1.437 em；Garamond 1007/−298 → 1.305 em | +16.3 与 +4.5 正确（TMP Line Spacing 的单位是 0.01 em） |
| 行长 ≤ 28° | 用 advance + kern + CJK 字距 0.1 em 独立复算每一行 | 最宽 27.0°（报告写 27.5°，更保守），全部通过 |
| kern 表注入 | ① 原始结构：version 0，format 0，coverage 1，按键排序，searchRange / entrySelector / rangeShift 正确，长度远小于 64 KB；② 用 HarfBuzz 按 GPOS 排版，与 kern 表对比字表内每一对字（Garamond Regular 10 000 对、Italic 9 801 对、Barlow 9 025 对）；③ 重跑 `check_kern_freetype.py` | 0 处不一致，FreeType 读回的值与表一致 |
| 图集装箱 | 按 90 pt + padding 10 估算 | 能装下。SC Regular 约 33%，与报告的 28% 同一量级 |
| C# | 用本机 Roslyn 重跑 `run_check.sh` | 类型检查通过（警告按错误处理）。另外按记忆中的 TMP 3.0.6 真实 API 逐个核对：`CreateFontAsset` 的 8 参重载、`TryAddCharacters(string, out string[, bool])`、`HasCharacters(string, out List<char>)`、`atlasPopulationMode` 的 setter（Static 时清掉 m_SourceFontFile）、`ClearFontAssetData(bool)`、字段名 m_AtlasWidth / m_AtlasRenderMode 等。签名和语义都说得通；CreateFontAsset 默认用 Mobile SDF shader，脚本随后改成 Distance Field，这是对的。**仍然没有在 Unity 里编译**，README 写明了这一点 |
| 渲染顺序建议 | 读 `deliver2/Rain/Shaders/Lanbai_BusGlass.shader`（Queue Transparent，ZWrite Off）和 `Lanbai_Overlay.shader`（Overlay+100） | “玻璃 queue + 10 = 3010”正确。玻璃不写深度，所以画在它后面的诗不会被挡掉 |
| 校样缺字 | 6 张校样全部分块看过，并 1:1 放大检查河伯、书き下し、Garamond、片尾、纸条 | 没有豆腐块，没有错字。字色取样与线性混合的预期值相差 ≤ 1 码（李白 3、暮句、齐物论、河伯） |
| 贴图检查（2 的幂、通道、法线、接缝） | — | 不适用：本套件不给 Unity 贴图，校样 PNG 放在 `Docs~`，Unity 不会导入 |

---

## B. 问题

### MAJOR 1：庄子镜像版式违反 §7.3 的垂直位置铁律。对英 / 日 / 其他语言玩家，论点之帧变成一堵约 59° 高的字墙

- **现象：** README §4 和 `make_proofs.zhuangzi_mirror` 定下的排法是：每个“单元”= 原文 + 该玩家的译文，整个单元一起镜像；单元离地平线 0.9 em，单元之间 0.75 em。按校样代码自己的 `block_metrics` 复算，**正字**所在的仰角是：
  - **en / de / other：** L1 单元 +21.4°..+29.5°（中心 **+25.5°**），L2 单元 +11.7°..+19.8°（中心 **+15.8°**）；镜像向下一直到 −29.5°。共 18 行字，纵向跨度约 59°。
  - **ja：** L1 中心 **+22.7°**，L2 中心 **+15.2°**，跨度 ±25.6°。
  - **zh：** L1 中心 **+10.8°**（也超了）。
- **违反的条文：** 圣经 §7.3 “垂直位置：中心在 −15°..+10° 之间……**永不高于 +10°、永不低于 −15°**”，以及“用眼睛读，不用脖子”。§6·8 的意图是三行贴着地平线，正好在“往下看与往上看一样”那几个字上翻转。现在的排法下，英语玩家在 t = 0 看到的第一行独自悬在 +25° 的天上，离地平线很远。
- **证据：** `Docs~/Proof_Trilingual_Zhuangzi.png` 英文栏（地平线在 y = 1194；L1 在 y ≈ 345，按 30 px/° 约 +28°）；`Proof_en.png` / `Proof_de.png` 里的 8-ii 面板。`build_report.txt` 只查了行宽，没有查垂直范围。open issues 里给的备选（“只镜像原文”）仍会让英语玩家的 L1 单元中心落在 +19° 左右，同样不合规。
- **修法（先选一个，重排后重新出校样）：**
  1. 单元间距和离地平线的间距收到 0.4–0.5 em，zh 就合规了（L1 中心约 +8.8°）。
  2. 译文**不进镜像**，只挂在“最新出现的那一行”正字下面，下一行出现时淡出。L1 的译文占用的正是 L2、L3′ 在 +6 秒和 +13 秒才会填上的空位，所以永远不会叠高。每个文本物体的中心都要落在 [−15°, +10°]。
  3. 或者请美术总监对 8-ii 明确豁免 §7.3，豁免写进 README。
  4. 不论选哪一种，都在 `build_report` 里加一项“每个文本物体的中心仰角”检查，并在校样上画仰角刻度（±10° / −15° 线）。

### MAJOR 2：第 8 幕校样的背景违反 §1.3.4 的紫色定量律，论点之帧呈现的正是 v2 删掉的“蒸汽波日落”

- **现象：** 在 CIE Lab 里逐像素测量，h_ab 290–325 且 C\* > 15 的面积：
  - `Proof_Trilingual_Zhuangzi.png` 中文栏 **40.4%**；
  - `Proof_en.png` 的 8-ii 面板 **38.3%**、第 8 幕梦句面板 **11.7%**（其他语言的校样同源）。

  圣经的上限是：第 4 / 4c 幕以外 **≤ 2%**。取样：行 251 `#8D8BAF`（h 294）、行 502 `#9F8EAA`（h 313）、行 1506 `#8C7F9F`（h 307）。
- **原因：** 背景在线性光里，从 `#808AB2` 到玫瑰色 `#D9A3A0` / `#E7A0A0` 铺了约 20° 宽的渐变，中间色必然是紫。另外，圣经把玫瑰色金星带放在**背日方向**（§6·8 的 HDRI 标准），庄子这句却在离太阳 +35° 的一侧，那里的地平线应该是琥珀色日带 `#FFB070` 过渡到中天 `#808AB2`。圣经自己的测试帧只有 0.8% 紫。
- **为什么是 major：** 任务书写明校样要画在“圣经的背景色”上；这张是整个世界的关键帧，用户要的是“极致的美”；v2 专门为第 8 幕删掉了紫（§1.1、§6·8：“16.5% 的画面是紫：一张‘蒸汽波’日落”）。
- **修法：** 第 8 / 8-ii 的背景改成：天缝琥珀 → 日带 → 中天 `#808AB2` → 天顶 `#3D4A80`，过渡走低彩度的暖灰或靛，不经过紫；庄子方位不画玫瑰带（最多一条 ≤ 1° 的低彩度带）。重新测量 ≤ 2% 后再出图。

### minor

- **m1 行末「？」「！」的光学偏心，与去逗号的理由自相矛盾。** 思源宋体 SC 的「？」墨迹只占 35–458/1000，「！」只占 194–303，都在字身左半边。所以“天之苍苍，其正色邪？”“遂古之初，谁传道之？”“我是醒着，还是睡着？”“我不肯被拒之门外！”这些行，居中时会向左偏约 0.3 em（2.2° 字号下约 0.7°）。这正是套件为了去掉行末逗号给出的理由。建议：在 JSON 里给这些行加 `optical_offset_em ≈ +0.27`，由 Director 把行物体向右平移；或者在 README 里写明接受这个偏差。
- **m2 片尾「—— 梦中得句」的破折号断开、位置偏低。** SC 字体里 U+2014 是比例宽的 em dash：advance 890/901，墨迹 44–857，高度 244–299。两条之间留有约 0.1 em 的缝，字距设 0 也消不掉，而且线落在拉丁字的高度，低于汉字的中线。`Proof_Credits.png` 放大后看得见。TMP 备用路径建议改用 U+2E3A「⸺」（字体里有，一整条 1714 宽）；想要居中的高度，就用两个 U+2500（0–1000，360–400，首尾相接）。站牌套件烘的贴图可能有同样的问题，请转告站牌套件。
- **m3 片尾“全文版”按 §5.5 的下限字号根本放不下。** `Proof_Credits.png` 里全文版的纸约 2.7 m 长，而圣经允许的最大纸长是 1 400 mm（箱体 1 000 × 1 500）。open issue 里“请美术总监在全文版和精简版之间选一个”，应当写明全文版在规格上不可行，实际只能用精简版（或者把字号下限作为豁免提出来）。
- **m4 README §2 说“世界内的署名已经在片尾的 Type 一行里”，不准确。** 正式版（站牌套件的 `credits.json`）没有 Type 和 Skies 两行。OFL 不强制署名，所以要么在站牌套件里补上，要么改 README 的说法。
- **m5 改名还留了尾巴。** 思源子集 CFF FDArray 的 FontName 仍是 `SourceHanSerifCN-Regular-Ideographs` 之类，用户看不到，但 README 写的“CFF 字体名都改了”不完全属实。用 fontTools 顺手改成 `LanbaiSerifSC-Regular-*` 即可。
- **m6 open issue 过期。** `deliver2/Rain/Shaders/Lanbai_BusGlass.shader` 现在在，Queue = Transparent（3000），ZWrite Off。README 的 3010 是对的，这条应改为“已核实”。
- **m7 書き下し请母语者复核。** 《逍遥游》L1 的通行训读是「天の蒼蒼たる**は**、其れ正色なるか」，现在缺了「は」。README 已经要求母语者过目，这里点名。
- **m8 README §5 的一处说法。** 它说“可以从 `Originals~` 里拿原件做源字体”，但 Unity 不导入以 `~` 结尾的文件夹。应写成“先把原件复制到 `Assets/` 里”。
- **m9 C# 原地重建的顺序。** `SetRenderSettings` 放在 `ClearFontAssetData` 之后，TMP 清理时按旧的 m_AtlasWidth/Height 重建空闲矩形。一旦 Specs 改了图集尺寸，装箱就会出错。应把设字段挪到清理之前。另外，`TryFetchKerning` 找不到零参数的 `UpdateGlyphAdjustmentRecords` 时什么也不输出；建议加一行 Log，并先试 `TryAddCharacters(string, out string, bool includeFontFeatures = true)` 这个三参重载（通过反射）。
- **m10 校样里的 Coleridge 纸条尺寸不对。** 校样上约 173 × 150 mm（横），圣经 §5.5 是 120 × 170 mm（竖）。这张只用来查字形，版式以站牌套件为准，但图不应给人错误的版式印象；要么标注“尺寸非规格”，要么按规格排。
- **m11 “LITE”铭牌。** 圣经 §6·12 把“UI 提示”和“济慈之后的任何字”列为要避免的东西，而这块铭牌是常驻的一个英文词，在济慈之后仍然可见。它已经作为提案标出；我们建议改成**无字的开关**（开的时候旁边亮一粒暖白小灯，这一半保留），这样也就不需要 Barlow 的 `LITE` 字形。
- **m12 外观上的小问题。** EB Garamond Italic 的静态实例和子集，PostScript 名是 `EBGaramondItalic-Italic`（instancer 改名留下的）；另外，因为没有连字，“fish”“butterfly”里 f 的钩会碰到 i 的点或 l。后一条套件已经注明，可以接受。

---

## C. 通过所需

修掉 MAJOR 1（重排庄子版式，或拿到明确豁免；重新出 `Proof_Trilingual_Zhuangzi.png` 和四张语种校样里的 8-ii 面板，并在报告里给出每个文本物体的中心仰角）和 MAJOR 2（第 8 幕背景按圣经去紫，测量 ≤ 2%）。minor 建议一起改，但不是通过条件。
