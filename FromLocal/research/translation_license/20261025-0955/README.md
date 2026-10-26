# R4 · 诗句、译文来源与公开使用核对

核对日2026-10-25。基线main `09164c9`，没有修改Fonts或场景。覆盖11组诗句/梦句，简中、繁中、日文、英文、德语玩家的55种显示状态；天问附行和分段对象使实际显示对象为73行，详见[逐语言清单](per_language.csv)和[含文件哈希、历史提交的清单](inventory.json)。所有原文、译文全文都已在现有公开仓库，本报告没有引入私人聊天。

**结论：古典原文与现代译文应分别核对。仓库源码明确声明译文由项目云端团队自译，初入提交已找到；但这项声明不能单独排除引用了现成译本。Rilke英文有明显同句风险，暂不作“全部许可已通过”的结论。**

## 原文作者、年代与范围

| 对象 | 作者 / 卒年 | 原文来源与判断 |
|---|---|---|
| P03、P12a | 李白，762 | 《梦游天姥吟留别》；古典原文财产权期限已过。[故宫作者资料](https://www.dpm.org.cn/lemmas/240150.html) |
| P04a | Rainer Maria Rilke，1926 | 《Duineser Elegien I》，1923出版。按德国作者身后70年一般规则，原文期限已过；这不覆盖后来的译本。[原作与作者资料](https://germanhistorydocs.org/en/wilhelmine-germany-and-the-first-world-war-1890-1918/rainer-maria-rilke-duino-elegies-first-second-and-third-1912)、[德国§64](https://www.gesetze-im-internet.de/urhg/__64.html) |
| P04b | 《Des Knaben Wunderhorn》民歌文本；编者Arnim卒1831、Brentano卒1842；Mahler卒1911 | “Urlicht”来自该民歌集，并被Mahler用于第二交响曲第四乐章。旧德文文本期限已过，不能由此推出任何录音或现代译本也可用。[Mahler Foundation](https://mahlerfoundation.net/mahler/compositions/wunderhorn-12/des-knaben-wunderhorn-12-songs-introduction/)、[乐章原稿资料](https://mahlerfoundation.net/mahler/compositions/symphony-no-2/symphony-no-2-movement-4-lied-1-urlicht-sehr-feierlich-aber-schlicht/) |
| P06、P08a | 项目原创梦句；作者在世/卒年不适用 | 现有strings源注为“用户梦中得句”，不是古代公有领域文本。应以项目原作者授权使用并保留约定署名，不能自动改标CC0 |
| P07、P09 | 传统归屈原，约前278（有争议） | 《九歌·河伯》《天问》；古典原文，不连带现代标注/译文。[中国大百科条目](https://www.zgbk.com/ecph/words?Name=%E5%B1%88%E5%8E%9F&SiteID=1&SourceID=542189&Type=bkzyb&subSourceType=000003000013000003) |
| P08b、P11 | 传统归庄周，卒年有争议（常见约前286，亦有约前298）；《庄子》有复合成书问题 | 《逍遥游》《齐物论》古文原句期限已过；不把现代译者认作庄周。[学术作者资料](https://iep.utm.edu/zhuangzi-chuang-tzu-chinese-philosopher/) |
| P12b | John Keats，1821 | 《Ode to a Nightingale》，1819；英文原句期限已过。[多伦多大学诗人资料](https://rpo.library.utoronto.ca/poets/keats-john) |
| coleridge_slip | Samuel Taylor Coleridge，1834 | 纸条的散文和“Then all the charm…”诗行来自《Kubla Khan》1816版序言中的回忆及引诗。原文期限已过；图像/排版本身另论。[1816版页面影像](https://anthologydev.lib.virginia.edu/exist/apps/LiC/work/Coleridge/coleridge-kubla?view=pageImages)、[美国国会图书馆作者记录](https://www.loc.gov/item/99000692/) |

以上为来源排查，按常见中/德/美发布场景识别已过期的古典原文；不声称已逐一核验全球所有辖区。中国现行法第13条将翻译作品的权利与原作区分，第23条规定一般自然人作品期限；不能因为原作已过期就自由复制现代译文。[国家版权局现行法](https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html)

## 每种语言实际来自哪里

`Fonts/Tools~/lanbai_strings.py`第12–15行明确写：中文古诗的日文書き下し，以及所有zh/ja/en译文，由本项目云端美术团队编写。该源码和strings文件在 **29fa6f2f1cc90d1573eddc4dead39d498dee5818** 同时新增；已经检查该提交的父提交差异为A，并非把浅克隆边界误当初次提交。

| 显示语言 | 来源 | 初入 / 当前文字第一次出现 | 公开使用判断 |
|---|---|---|---|
| 简中 | 中文古诗直接原文；Rilke/Urlicht/Keats为项目自译；两句梦句为项目原创 | 29fa6f2；逐项见CSV | 古文原文可用；自译按项目作品使用，需保留归属与授权声明，不能称未知译者已去世 |
| 繁中 | 源码说明OpenCC s2tw后人工校核，古文“枕席”等保留通行字 | 5277c7d6fbea1346adb22583a6d96897c7fcfd20 | 原文繁简转换不产生外部译者来源；西文诗繁体继续继承中文译文的来源风险 |
| 日文 | 中文古文为项目書き下し，西文和梦句为项目译文 | 29fa6f2；部分当前显示断句/文字在08230756fd587a6c1f16d23a0547299c01af9c6c出现 | 没有外部译者署名；作者卒年不适用。可按项目自译路线处理，仍需母语审读与归属声明 |
| 英文 | Keats直接原文，其余是项目自译声明 | 29fa6f2；逐显示对象核对 | Rilke英文另列风险；其余未发现外部译者署名，不能捏造译者或公有领域版次 |
| 德语玩家 | **只有Rilke、Urlicht显示德文原文；其他诗实际回退英文** | 与对应原文/英文相同 | 当前没有11首全套德译；CSV的actual_language明确记录，不能把英语回退标成德文译文 |

源码链接：[初次声明](https://github.com/chengnan024-lang/lanbai-assets/blob/29fa6f2f1cc90d1573eddc4dead39d498dee5818/Fonts/Tools%7E/lanbai_strings.py)、[繁中引入](https://github.com/chengnan024-lang/lanbai-assets/commit/5277c7d6fbea1346adb22583a6d96897c7fcfd20)、[v4.1文字/布局](https://github.com/chengnan024-lang/lanbai-assets/commit/08230756fd587a6c1f16d23a0547299c01af9c6c)。CSV对所有显示文本去掉空白比较历次JSON，保留最早精确归一化匹配的提交；这证明入库来源，不证明文学创作过程。

## 必须交总控处理的疑点与替代办法

1. **P04a英文**：现句“For beauty is nothing but / the beginning of terror”与常见Stephen Mitchell版本同句。项目代码虽称自译，检索也发现该措辞被标作Mitchell（1982）。[出版社确认Mitchell译者身份](https://www.penguinrandomhouse.ca/books/154369/the-selected-poetry-of-rainer-maria-rilke-by-rainer-maria-rilke-edited-and-translated-by-stephen-mitchell/9780679722014)，[学术论文中的同句及译者引注](https://scholar.ufs.ac.za/bitstream/handle/11660/1995/KreuiterAD.pdf?sequence%5Cx3d1%5Cx26isAllowed%5Cx3dy=)。短句重合不自动证明侵权，**也不足以无条件放行**。未确认此具体译句的开放许可，译者卒年未核实，不能按Rilke的1926计算它。优先由项目依据德文独立重译并留下过程/版本；候选草稿如“Beauty is only the threshold / of what terrifies us”，须总导演审美与德语校对，不直接改工程。也可另找确实已入公有领域且有扫描版证的旧英译，不能只找匿名网页。
2. **其他所有自译**：目前证据是仓库自述和提交历史，尚缺独立作者/权利归属文件；报告不填假译者姓名/卒年。项目作者补一份自译与授权声明后，可沿此路线公开使用。若任一句其实来自现成译本，先补译者、版次、授权；拿不到就独立重译。中文Rilke短句也有常见译法重合，不能凭字面相近判断归属。
3. **原创梦句**：不是公有领域；按原作者已约定的项目使用范围，片尾署名由原作者决定。不在本次核对中自动扩为任何人可再许可。
4. **附属文字**：15项UI是项目功能提示、语言简称和数字；目的地“蓝白”是项目标题。片尾作者名、书名等按事实标注；Music内`verify:true`的演出者/录音署名，以及Photos占位仍未核验，不将诗句审查当音源、摄影或字体许可审查通过。纸条古典文本可用，但现代扫描版页面/字体许可应分别处理。

两张ISS照片另见[许可核对](../../license_check/20261025-0955/README.md)。本轮仅回传来源与待办，不重写诗句，不同步被排除的两个Fonts脚本。

补充逐显示行索引：[per_line.csv](per_line.csv)，继承所属显示对象的来源提交；换行本身不单独推断译者。
