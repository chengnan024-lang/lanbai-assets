# 汉代博局镜（规矩镜 / TLV mirror）形制考据——供 3D 程序化建模用

时代范围：博局（TLV）纹镜总体约从公元前 2 世纪流行到公元 2 世纪（Wikipedia "TLV mirror"）；本文针对的**四神 / 禽兽博局镜**集中在西汉晚期 – 新莽 – 东汉前中期（约公元前 1 世纪 – 公元 2 世纪），新莽至东汉早期最盛。西汉前中期已有蟠螭纹、草叶纹等配博局纹的早期形态，形制不同，本文不涉及。
写作说明：
- 本环境里 WebFetch 和 curl 打不开外网页面（DNS 或代理拒绝），所以下面的博物馆数据都来自 WebSearch 返回的目录摘要，没有逐页打开核对。
- 标"【经验值】"的数字是作者根据常见实物照片、拓本和通行图录总结的推算范围，不是某件器物的实测。建模时可以当默认参数用，但应该当作可调范围，不要当作定论。
- 标"【未核实】"的内容只有间接来源。

---

## 0. 实测数据汇总（目录著录）

| 器物 | 时代 | 直径 | 通高/厚 | 缘厚 | 来源 |
|---|---|---|---|---|---|
| Cleveland 1995.295 TLV Mirror with Multiple Nipples | 新莽 9–23 | 16.3 cm | 通高 1.2 cm | 0.6 cm | https://www.clevelandart.org/art/1995.295 |
| Cleveland 1995.298 TLV Mirror with Multiple Nipples | 新莽 9–23 | 16.9 cm | 1.1 cm | 0.5 cm | https://www.clevelandart.org/art/1995.298 （核查时补入） |
| 中国国家博物馆 "中国大宁"鎏金四神博局镜（长沙伍家岭 211 号西汉后期墓） | 西汉后期 | 18.6 cm | — | 0.6 cm | 人民日报 2021-03-20 及国博展览报道（核查时补入） |
| Cleveland 1995.296 TLV Mirror | 东汉 | 14.2 cm | 1.0 cm | 0.6 cm | https://www.clevelandart.org/art/1995.296 |
| Cleveland 1995.301 TLV Mirror with Four Spirits and Companions | 9–100 | 19 cm | 1.2 cm | 0.7 cm | https://www.clevelandart.org/art/1995.301 |
| Cleveland 1995.294 TLV Mirror with Gilt Surface（鎏金） | 东汉 | 14.2 cm | 1.2 cm | 0.6 cm | https://www.clevelandart.org/art/1995.294 |
| Met 17.118.42 Mirror with game board design and animals of the four directions | 1–2 世纪 | 16.8 cm | — | — | https://www.metmuseum.org/art/collection/search/53937 |
| Davis Museum (Wellesley) 2014.43 TLV Mirror with Shangfang Inscription | 东汉 | 18.4 cm | — | — | https://davis.emuseum.com/objects/13848/tlv-mirror-with-shangfang-inscription |
| 早稻田会津八一纪念博物馆 八乳方格规矩鸟兽文镜（尚方铭） | 东汉前期 | 18.3 cm | — | — | https://www.waseda.jp/culture/aizu-museum/other/2019/07/03/2706/ |
| 京都国立博物馆 方格规矩四神镜（汉·新）JK157 / JK179 | 新莽 | 21.1 / 16.4 cm | — | — | https://knmdb.kyohaku.go.jp/eng/6420.html 等 |
| 京都国立博物馆 JK160 | 汉 | 22.75 cm | — | — | knmdb.kyohaku.go.jp |
| 京都国立博物馆 流云文缘方格规矩四神尚方佳镜 | 汉 | 16 cm | — | — | https://knmdb.kyohaku.go.jp/eng/6441.html |
| Brooklyn 10.58 TLV-Type Mirror | 汉 | 13 cm | 1.3 cm | — | https://www.brooklynmuseum.org/opencollection/objects/21525 |
| 某商家 新莽银白博局镜 | 新莽 | 20.4 cm | — | — | https://www.michaelbackmanltd.com/object/chinese-silvered-bronze-tlv-mirror-jing/ |
| 西汉规矩镜（拍品） | 西汉 | 11.5 cm | — | 缘宽 0.45 cm | https://drouot.com/en/l/21013900-china-han-dynasty-206-bc-220-a |

从这些数据可以得到：
- 四神博局镜标准件直径多在 **14–21 cm**，常见值 16–19 cm。简化博局镜、小件可以小到 11–13 cm。
- **通高（镜面到钮顶）1.0–1.3 cm**，约为直径的 0.06–0.08。
- **缘厚 0.5–0.7 cm**，约为直径的 0.03–0.04（Cleveland 1995.298 为 0.5 cm，其余多为 0.6 cm）。
- 镜体在主纹区很薄，**约 0.2–0.35 cm**【经验值】。对照：Liang & Parker 2021（Jiafang Liang、Quentin Parker，*Heritage Science* 9:25）测过一面小汉镜（直径 59 mm），厚度 1.99–2.02 mm，见 https://heritagesciencejournal.springeropen.com/articles/10.1186/s40494-021-00496-2/tables/2 。注意：这是直径不到 6 cm 的小镜，表中"厚度"未说明是缘厚还是主区厚，不能直接当作 18 cm 博局镜的主区厚度，只能说明汉镜体可以薄到约 2 mm。

---

## 1. 从中心向外的解剖结构

### ASCII 径向示意（镜背俯视，取 1/4 象限，R = 镜半径）

```
 r/R: 0     .13   .24  .33 .40   .50       .62  .70  .74 .80 .83        1.0
      |      |     |    |   |     |         |    |    |   |   |          |
      [ 钮  ][钮座 ][地支][方框][ 主纹区: T · 八乳 · V · L · 四神/禽兽细线 ][铭文][栉齿][  宽平缘  ]
      半球    柿蒂   12乳  双线  T 的横画约在 .45-.50                带(可无) 短直线  锯齿/双线波折/锯齿
              或圆座 12字  凹/凸  乳在 .48-.56，V 顶在方框角外               或流云纹
                           方框  L 的外角贴主区外圈 .66-.72

 剖面（中心 → 边缘；Z 方向夸张约 5 倍）：

  Z
  |   ___
  |  /   \                                                         ______
  | |  钮  |                                                      |  缘   |
  | |      |__ 座 __ 框 _ 乳 _____ 细线浮雕 ____ 铭/栉齿 __/斜坡 |      |
  | |______________________________________________________________|______|
  |  \___________________ 镜面：微凸 (convex)，中心比边缘低 1-3 mm ______/
  +-------------------------------------------------------------------> r
```

（坐标约定：镜背向上，镜面向下。镜面凸，所以从侧面看镜面中部朝下鼓出。）

### 1.1 钮（半球形钮 / 圆钮）
- 半球形，或稍高于半球的馒头形，中间横穿一个**穿孔（钮孔）**用来系绶带。孔的方向通常与某一条 T-L 轴平行【经验值】。
- 钮直径约为镜径的 0.11–0.15（16–19 cm 镜约 2.0–2.6 cm），r/R ≈ 0.11–0.15【经验值】。
- 钮顶离镜面 1.0–1.3 cm（就是著录里的"通高"），比主区底面高约 0.7–1.0 cm。

### 1.2 钮座
最常见的两种：
- **柿蒂纹座（四叶座）**：四片尖叶沿对角线（指向方框四角）或沿 T 轴伸出。叶尖 r/R ≈ 0.20–0.25。早稻田藏镜和人民网报道的长沙鎏金镜都写作"钮中央为四叶纹"。
- **圆座**：圆座外常有一圈短栉齿或连珠，r/R ≈ 0.18–0.22。

### 1.3 方框与十二地支
- 钮座外是**方框**。常见做法有两种：一种是内外两道细凸线（双线方框），中间夹一条窄带；另一种是一道凸起的宽方带外加一道细线。框边与镜的径向对齐，四边分别朝东南西北。
- 方框内（或框带里面）布置**十二个小乳钉和十二地支字**（子丑寅卯辰巳午未申酉戌亥），两者交替排列，每边三字。Met 17.118.42 的说明就提到"inscribed with the twelve earthly branches"；早稻田藏镜解说也写作"方格内十二支铭间以小乳"。
- 地支方位（按十二辰配四方推定，建模时请以所选参考镜拓本为准）：北边为亥、子、丑，东边寅、卯、辰，南边巳、午、未，西边申、酉、戌，每边中间一字（子、卯、午、酉）正对该边的 T。四神须与之同侧：玄武—子（北）、青龙—卯（东）、朱雀—午（南）、白虎—酉（西）。地支的读序是顺时针还是逆时针，各镜不一，【未核实】。
- 方框内也可能不是地支，而是一圈铭文：Cleveland 1995.295 的"新有善铜出丹阳"铭就是绕钮一周，而不在外圈铭文带。
- 尺寸【经验值】：方框外边半边长 a ≈ 0.36–0.42 R，内框半边长 ≈ 0.28–0.33 R，框角到圆心的距离约 a·√2 ≈ 0.52–0.58 R。框带宽约 0.05–0.08 R。
- 也有无地支字、只在框内放乳钉的简化版。

### 1.4 T、L、V 纹（博局纹）的位置（最关键）
- **T**：共 4 个，分别在方框四边的**正中**。竖画沿径向朝外，根部贴着方框外边，横画平行于方框边。横画外缘 r/R ≈ 0.45–0.50，横画长约 0.12–0.16 R。
- **L**：共 4 个，在**T 的正外侧，与 T 同轴相对**，位于主纹区外圈内侧，r/R ≈ 0.62–0.72。L 是直角形：一条短画贴着外圈（切向），另一条短画朝内（径向）。四个 L 的转折方向一致，绕中心呈**同向旋转（风车状）**，不左右镜像。人民网的描述是"方框外四面正中为 T 形纹，与其外侧的 L 形纹相对"。L 的同向旋转是根据实物照片和拓本观察得出的，网上没有找到文字说明；旋转方向（顺时针或逆时针）各镜不一，也有个别 L 反向（"正 L / 反 L"在日本仿制镜研究中被用作鉴别特征，见京都府埋文论文 https://www.kyotofu-maibun.or.jp/data/kankou/kankou-pdf/ronsyuu3/part2/3-19-300.pdf ）。建议把手性做成参数。
- **V**：共 4 个，在**方框四角的对角线方向上**（人民网："方框四隅外则与 V 形纹相对"）。V 的**尖端朝向方框角**（向内），两臂向外伸到主区外圈，位置 r/R ≈ 0.58–0.70。Cammann 认为 V 使方框看起来位于一个"十"字的中央，这与 V 尖朝内、处在十字凹角上的布置相符。V 的朝向是依照片判断的，没有找到直接的文字说明【未核实】。
- 线宽：TLV 是平顶的凸起带，宽约 0.02–0.03 R，通常用双线勾边或做成实心窄带【经验值】。

### 1.5 八乳
- 共 8 个乳钉，**每个 T 的左右各一个**，也就是每个象限两个，分在 T-L 轴两侧，与轴的夹角约 ±18°–25°，r/R ≈ 0.48–0.56【经验值】。早稻田藏镜叫"八乳方格规矩"，克利夫兰鎏金镜的描述是"在 T、L、V 之间有八个凸起的乳丁"。
- 乳钉为半球形，直径约 0.06–0.08 R（约 0.6–0.9 cm），下面多带**圆座**或**四叶（柿蒂）小座**。乳钉比地面高约 2–3.5 mm【经验值】。
- 八乳"T 两侧各一"是根据照片观察的通行布局，网上没有找到逐件的文字说明【未核实】；早稻田藏镜和 Cleveland 1995.294 只写了"八乳"，没有写位置。
- 乳的数量要和镜型对应：八乳最常见，也有四乳博局镜和"多乳"镜（Cleveland 1995.295、1995.298 Multiple Nipples）。另一种常见变体是**方框外四角各一乳**：长沙伍家岭"中国大宁"镜就是"框外四隅各置一枚乳丁"，乳在方框角与 V 之间。这一型的乳钉位置和八乳型不同，不能混用。

### 1.6 主纹（填充纹样）
- **四神**：青龙（东）、白虎（西）、朱雀（南）、玄武（北，龟蛇相缠）。每神占一个象限（两 V 之间），并有**羽人、瑞兽、禽鸟（伴兽）**补空。Cleveland 1995.301 名为 "Four Spirits and Companions"。
- 风格是**细线浮雕（细线式、线描式）**：线条细而连贯，起伏很低，约 0.3–0.8 mm【经验值】，接近平面上勾出的阳线，**不是**唐镜那种高浮雕。
- 东汉以后有"禽兽博局镜"，多用鸟兽或云气代替四神。
- 方位：Met 的说明是方框"aligned with the four cardinal directions"，四神按方位排布。

### 1.7 铭文带
- 位于主纹区外圈，r/R ≈ 0.72–0.80，为一圈顺时针或逆时针环读的阳文，字高约 0.04–0.05 R。也有铭文放在钮外方框内的（Cleveland 1995.295）。
- 书体：汉镜铭是**篆隶过渡的镜铭体**，通常著录为"篆书"（"中国大宁"镜即记为 52 字篆书阳铭）。字形多方折简省，常有通假、减笔、缺字和反书（见华南师大学报关于西汉镜铭的论文 https://journal-s.scnu.edu.cn/cn/article/id/f220f9aa-0b9d-4adf-9224-33bbb2c1a7a5 ）。原稿写的"缪篆"是汉代印章用的篆体名称，用来称呼镜铭不准确，已改。
- 常见文本：
  - **尚方镜**："尚方作竟（镜）真大好（巧），上有仙（山）人不知老，渴饮玉泉饥食枣，浮游天下敖（遨）四海，寿如金石（为/之）国保"。七言句，常有异文（"佳竟""大巧"），全文约 35–42 字，也常有截短的。早稻田藏镜读作"尚方作竟真大巧上有山人不知老渇飲玉泉飢食"，见 https://www.waseda.jp/culture/aizu-museum/other/2019/07/03/2706/
  - **新莽镜**："新有善铜出丹阳，和以银锡清且明，左龙右虎掌四彭，朱雀玄武顺阴阳，八子九孙治中央……"（新莽"善铜"镜，常以"新"字起首）。前两句已由京都国立博物馆藏镜（"新有善銅出丹陽和以銀錫清且明"，https://knmdb.kyohaku.go.jp/eng/7904.html ）和 Cleveland 1995.295（"丹阳善铜"）佐证；后三句仍据通行著录，没有找到逐字原文页。
  - **"王氏作竟四夷服……"**：新莽时期另一类铭文。UBC MOA 有以"王氏"起首的例子：https://www.rrncommunity.org/items/496/print
  - **"中国大宁"镜**（长沙伍家岭 211 号西汉后期墓，国博藏，鎏金四神博局镜，直径 18.6 cm）：铭文 50 余字（多记为 52 字），以"中国大宁，子孙益昌"一句著称。据报道，铭文为带"兮"字的骚体句，以"圣人之作镜兮"起首，【未逐字核对】。见人民网 https://paper.people.com.cn/rmrbwap/html/2021-03/20/nw.D110000renmrb_20210320_3-05.htm 。原稿把这面镜和"王氏作竟"铭混为一条，已拆开：这是两种不同的铭文。
- 注意铭文镜的真伪：Berkeley 有一件六棱"尚方"镜被判定为伪作，因为汉代没有六棱镜，见 https://digicoll.lib.berkeley.edu/record/246460

### 1.8 栉齿纹带
- 在铭文带（或主区）外侧，是一圈**短径向直线**，排得很密。宽约 0.025–0.04 R，r/R ≈ 0.79–0.83，线数大约每 1.5–2° 一根（全圈 180–240 根）【经验值】。
- 栉齿带外侧紧接镜缘的内斜坡。

### 1.9 镜缘
- **宽平缘**：从 r/R ≈ 0.80–0.84 到 1.0，宽约 0.16–0.20 R，是四神博局镜的主流做法。缘面平，比主区明显高、厚（缘厚 0.5–0.7 cm，主区约 0.3 cm）。内侧是一段小斜坡，外侧是近乎垂直的边。
- 缘面纹饰，从内向外常见三层：**锯齿纹（三角齿）— 双线波折纹（双线锯齿或折线）— 锯齿纹**。另一种是**流云纹（云气纹）缘**，京都"流云文缘"镜和 Cammann 所说的 rolling cloud rim 都属此类。东汉中晚期还出现**画纹缘**（禽兽、羽人绕缘）。
- 缘面纹饰的起伏比主纹更低（约 0.3–0.6 mm）。外侧 0.02–0.03 R 常留一圈素面窄边。
- **三角缘**（断面是尖三角）不是四神博局镜的特征，**不要用**。补充：三角缘或斜缘在中国东汉晚期的画像镜、神兽镜上已经出现，3 世纪以后的"三角缘神兽镜"（多出于日本）是它的发展形态。所以原稿说三角缘是"魏晋以后"才有，不准确；准确的说法是"属于晚于博局镜的镜类"【据通行分期，未检到网页】。

---

## 2. 起伏高度与剖面

基准：直径 D = 18 cm（R = 9 cm）。

| 部件 | 半径比例 (r/R) | 起伏高度（以镜面为 0，占直径 D） | 来源 |
|---|---|---|---|
| 钮（半球，带穿孔） | 0 – 0.13 | 顶高 1.0–1.3 cm，约 0.06–0.075 D | Cleveland 1995.294/.295/.301 通高 1.0–1.2 cm；Brooklyn 10.58 1.3 cm |
| 钮座（柿蒂或圆座） | 0.13 – 0.24 | 高出地面 0.5–1 mm，约 0.003–0.005 D | 【经验值】；早稻田、人民网描述"四叶纹" |
| 地支带 + 十二小乳 | 0.24 – 0.33 | 小乳高 1–1.5 mm；字高出地面约 0.3–0.5 mm | Met 53937 说明；【经验值】 |
| 双线方框 | 0.30 – 0.42（框角约 0.55） | 凸线 0.5–1 mm | 【经验值】 |
| 主纹区地面（镜体） | 0.42 – 0.72 | 体厚 2–3.5 mm，约 0.012–0.02 D | Liang & Parker 2021（汉镜体厚约 2 mm）；【经验值】 |
| T / L / V | T 0.40–0.50；V 0.58–0.70；L 0.62–0.72 | 凸带 0.5–1 mm | Met 53937；人民网；【经验值】 |
| 八乳（含座） | 0.48 – 0.56，T 两侧 ±20° | 乳高 2–3.5 mm，约 0.012–0.02 D；直径 0.06–0.08 R | 早稻田"八乳"；Cleveland 1995.294；【经验值】 |
| 四神 / 羽人细线浮雕 | 0.42 – 0.72 | 0.3–0.8 mm，约 0.002–0.004 D | 【经验值】 |
| 铭文带 | 0.72 – 0.80 | 字高出地面 0.3–0.5 mm | Waseda；Davis 2014.43 |
| 栉齿纹带 | 0.79 – 0.83 | 0.3–0.5 mm | 【经验值】 |
| 缘内斜坡 | 0.82 – 0.84 | 从体厚升到缘厚 | 【经验值】 |
| 宽平缘 | 0.84 – 1.00 | 缘厚 0.5–0.7 cm，约 0.03–0.04 D；纹饰起伏 0.3–0.6 mm | Cleveland 1995.298（0.5 cm）、1995.294/.295/.296（0.6 cm）、1995.301（0.7 cm）；"中国大宁"镜 0.6 cm |
| 镜面凸度（矢高） | 全面 | 约 1–2.5 mm，约 0.006–0.014 D（D=18 cm 时曲率半径约 1.6–4 m，按 s = r²/2ρ 换算） | 沈括《梦溪笔谈》定性记载；数值是【经验值，未核实】，没有检到汉镜曲率的实测数据 |

剖面要点：
1. 镜体是"边厚中薄"的盘形：缘约是主区的 2 倍厚，钮是全镜最高点。
2. 主区地面基本平，纹饰都是低浮雕阳线，乳钉和钮是仅有的明显凸起。
3. 镜面整体微凸，所以从侧面看，镜面一侧中部比边缘略低（朝外鼓出）。

---

## 3. 镜面、合金与表面状态

### 3.1 凸面
- 沈括《梦溪笔谈·器用》："古人铸鉴，鉴大则平，鉴小则凸。凡鉴洼则照人面大，凸则照人面小……仍复量鉴之小大，增损高下，常令人面与鉴大小相若。"（原文据通行本，本次未取到网页原文。）意思是小镜要做得更凸，才能照全人脸。
- 本次没有检到汉博局镜曲率的实测论文。NTU 关于"透光镜"的研究用相位测量反射术测过镜面形貌，但只讨论微米级起伏：https://dr.ntu.edu.sg/server/api/core/bitstreams/2ae17ba9-810e-4f8e-9b0f-9866667aa0f6/content
- 关于凸面怎么来的：Temple 的说法（经 Wikipedia 转述）是铸成后刮磨出凸面，薄处应力大，更容易外凸：https://en.wikipedia.org/wiki/Chinese_magic_mirror
- 注意沈括说的是"鉴大则平，鉴小则凸"：凸度随镜径减小而增大。直径 16–21 cm 的博局镜在汉镜里属中大型，凸度应比小镜低，不宜做得太凸。
- 建模建议：镜面做成球冠，矢高取 0.6%–1.0% D（18 cm 镜约 1.1–1.8 mm），做成参数，小镜取上限、大镜取下限【经验值，未核实】。

### 3.2 合金
- 汉镜是**高锡青铜**（铜-锡-铅）：
  - 汉代镜平均 Cu 67.07%、Sn 25.42%、Pb 4.47%；王莽时期两面镜 Sn 22.36–22.71%、Pb 5.70–5.79%（汇编数据，见 https://link.springer.com/10.1186/s40494-024-01247-9 、https://en.maiask.ru/data/documents/13_RavichTreisterENG.htm ）。
  - 临淄西汉镜 41 面，Cu:Sn:Pb 约 14:5:1（即 Sn 约 25%）：https://katalog.hcu-hamburg.de/vufind/Search2Record/SPR055490751
  - 六安盘螭镜研究认为，文景时期从高铅低锡转向低铅高锡，这是汉式镜传统的开端：https://en.ustc.edu.cn/info/1007/5080.htm 【未核实：原页打不开。这一说法和战国镜本已高锡的通行认识有出入，只当作该研究的个案结论】
- 新鲜抛光的颜色：锡含量约 19% 以上时，δ 相（Cu₃₁Sn₈）成为主相，青铜呈**银色**（见 Liang & Parker 2021 https://link.springer.com/10.1186/s40494-021-00496-2 ）。所以锡 22–26% 的汉镜呈**银白色，略带淡黄的暖调**；含铅越多越偏灰（所谓"白铜""银光"），**不是金黄色**。原稿写"金黄色是低锡青铜（< 10% Sn）的颜色"，不准确：低锡（约 5–10%）偏红铜到红金色，约 10–15% 才是典型的金黄色，15–19% 渐变为浅黄。具体阈值据冶金常识，【未逐一核实】。高锡青铜硬而脆，断口是银灰色。
- 注意：也有学者指出，部分古镜是低锡青铜表面镀锡，而不是整体高锡（见 hmsjournal 检索结果），汉代主流仍是整体高锡。另外汇编数据显示，汉镜含锡量随时代略降、含铅量上升，所以东汉镜可以比新莽镜略灰、略暖。

### 3.3 出土表面状态（材质变体）
- **黑漆古**：乌黑如漆、光亮，表层富含 SnO₂，是铜被选择性溶出后锡氧化留下的。多见于湖南、湖北、江西等南方潮湿地区：https://archaeology.pku.edu.cn/2019gudaiqingtongqibiaomiangaoxixiucengyanjiuzongshu_liuwei.pdf 。Met 17.118.42 就著录为 "Bronze with black patina"。
- **绿漆古**：漆古的另一种，呈墨绿或灰绿光泽。
- **水银沁（银白古）**：银白色、有镜面光泽，同样是富锡表层，多见于北方。商家也叫 "silvered"。
- **铜锈**：铜绿（孔雀石，翠绿或粉绿，疏松颗粒）、蓝锈（蓝铜矿）、红斑（赤铜矿，暗红）、枣皮红，多出现在钮孔、缘边和凹处，凸起处常被磨亮。
- 致密的 SnO₂ 膜能保护基体：https://www.scientific.net/AMR.337.743
- 建模建议：做几个材质预设，即"银白抛光（新）""黑漆古""水银沁""绿锈斑驳"。锈和污垢用 AO 和曲率遮罩，积在纹饰凹处和钮根，凸棱处磨亮。

---

## 4. 宇宙图式的解读

- **天圆地方**：圆形镜背代表天，中央方框代表地（"中国"）。Met 的说明是："The square world—aligned with the four cardinal directions and inscribed with the twelve earthly branches… is surrounded by the circular heavens, in turn ringed by the waves of the cosmic ocean"；TLV 纹则"recall the measuring tools (规、矩) associated with Fu Xi and Nüwa"。见 https://www.metmuseum.org/art/collection/search/53937
- **Lien-sheng Yang (杨联陞) 1947**：提出 TLV 纹与**六博棋盘（博局）**有关（Wikipedia "TLV mirror" 确认是 1947 年由哈佛的杨联陞提出）。1952 年他在 HJAS 15.1–2 发表补证 "An Additional Note on the Ancient Game of Liu-po"。另可参考劳榦 1964 年的 "Evolution of the Ancient Game Liu-po and the TLV-Board"，以及周铮 1987 年主张把"规矩镜"改称"博局镜"。原稿说杨"最早"提出这一联系，这一点没有核实到，已删去"最早"。
- **Schuyler Cammann 1948**，"The 'TLV' Pattern on Cosmic Mirrors of the Han Dynasty"，*JAOS* 68: 159–167。他的读法是：中央钮是昆仑（世界之山），方框是中国，V 使方框看起来位于一个"十"字的中央（这一句经 Wikipedia 转述核实），由此表达"五方"；T 是通向四方的门，L 是更远的门或洞穴，云纹缘就是天（这几项是二手转述，【未核实原文】）。他认为整个图式表达"五方"（东南西北中）。见 https://www.semanticscholar.org/paper/The-%22TLV%22-Pattern-on-Cosmic-Mirrors-of-the-Han-Cammann/a95062e228c2edb09907ea3810b6494f771a8a26 ，转述见 https://library.hungaricana.hu/hu/view/ORSZ_IPMU_Ime_09_1966/?pg=173
- **Michael Loewe 1979**，*Ways to Paradise: The Chinese Quest for Immortality*，第 3 章 "TLV mirrors and their significance"。他把 TLV 镜与马王堆帛画、西王母图像并列，作为汉代宇宙观和升仙思想的主要图像材料，并讨论了式盘（shi）、六博与镜纹的同构：https://taylorfrancis.com/chapters/mono/10.4324/9781003290131-3/tlv-mirrors-significance-michael-loewe
- **Lillian Lan-ying Tseng (曾蓝莹)**：
  - "Representation and Appropriation: Rethinking the TLV Mirror in Han China"，*Early China* 29 (2004)。她主张把讨论重点从"图案是什么"转到"它在汉代文化中如何被使用"，主要依据是 1993 年江苏东海尹湾汉墓出土的木牍《博局占》（用博局图占卜）。见 https://resolve.cambridge.org/core/journals/early-china/article/representation-and-appropriation-rethinking-the-tlv-mirror-in-han-china/71D2C9018A2A0BB67982F7FC35A7DCF2
  - *Picturing Heaven in Early China*（Harvard East Asian Monographs 336, 2011），其中"Constructing the Cosmic View"一章讨论博局镜：https://muse.jhu.edu/book/61552
- 李学勤《〈博局占〉与规矩纹》（《文物》1997 年第 1 期）【据记忆，未检到网页】。尹湾《博局占》图把六十甲子排在博局 TLV 位置上，证明"博局"就是汉人自己对这种图式的称呼，所以中文学界多改称"博局镜"。
- Nelson-Atkins 的说明认为镜纹类似六博棋盘，四神也和六博的方位相合：https://art.nelson-atkins.org/objects/2130/mirror-with-tlv-patterns-and-four-direction-animals ；Met 61417 也有同类说明：https://www.metmuseum.org/art/collection/search/61417
- 对建模的意义：TLV 要严格按四方对称和十二辰等分来做（4 重旋转对称，L 带手性），四神的方位要对，地支按 30° 间隔排列。这些都是这件器物的"意义"所在。

---

## 5. 给建模师的"要"与"不要"

**要：**
1. 主体结构保持严格的 **4 重旋转对称**（C4）。L 纹四个同向旋转，**不要做成镜像对称**（D4）。四神是唯一打破对称的元素。
2. 八乳**每个 T 的两侧各一个**，每个乳下带圆座或四叶座。四乳型（方框外四角各一乳，如"中国大宁"镜）和多乳镜是别的型，不要混用。
3. T 贴在方框边的中点；L 在 T 外、贴主区外圈；**V 的尖朝方框角，开口朝外**。
4. 方框内是 12 小乳 + 12 地支，每边三字，子、卯、午、酉分居北、东、南、西各边正中，与四神方位一致。
5. 宽平缘明显高于主区（缘厚约为主区的 2 倍），缘上做锯齿、双线波折、锯齿三层，或做流云纹。缘内侧接栉齿纹带。
6. 主纹用细线低浮雕（< 1 mm），只有钮和乳钉是明显凸起。
7. 镜面做微凸球冠（矢高约 1% D）。镜面不铸纹饰，是素面抛光的。
8. 钮做出穿孔。
9. 颜色：新器为银白、略带淡黄暖调的高光金属（含铅高的偏灰）；出土状态做成黑漆古、水银沁或绿锈。
10. 参数范围：D = 14–21 cm（默认 18），通高约 0.065 D，缘厚约 0.033 D（0.03–0.04），主区厚约 0.015 D，镜面矢高约 0.008 D。

**不要：**
1. **不要用唐镜纹样**：海兽葡萄镜（瑞兽葡萄）、葵花形或菱花形镜边、宝相花、鸾鸟衔绶、螺钿或金银平脱。唐镜多是高浮雕、厚体，与汉镜明显不同。
2. **不要用日本和镜**的元素（松鹤、菊花、带柄镜、草书铭、长柄），也不要用**三角缘神兽镜**的三角缘和神兽环列。
3. **不要做六边形或八边形外形**（汉代没有六棱镜，见 Berkeley 伪作记录），也不要把镜做成带柄式。
4. **不要做成金黄色**，也不要做成亮金属铜色或红铜色。鎏金镜（Cleveland 1995.294）是少数特例，要单独说明。
5. **不要把乳钉数量做错**（如 6、10、12 个大乳），不要把十二地支的小乳和主区八乳混在一起。
6. **不要把 V 的方向做反**（开口朝内），也不要把 L 放在方框角上。
7. **不要用三角缘或连弧缘**（连弧纹是另一类昭明镜、日光镜的内区特征），不要把缘做得和主区等高。
8. **不要使用楷书或宋体铭文**，铭文应是篆隶之间的汉镜铭体（方折、简省）。
9. **不要高浮雕四神**（那是东汉晚期神兽镜、画像镜的风格）。
10. **不要在镜面一侧放纹饰**，也不要把镜面做成平面或凹面。

---

## 主要来源
- Cleveland Museum of Art：1995.294 https://www.clevelandart.org/art/1995.294 ；1995.295 https://www.clevelandart.org/art/1995.295 ；1995.296 https://www.clevelandart.org/art/1995.296 ；1995.301 https://www.clevelandart.org/art/1995.301
- Metropolitan Museum 17.118.42：https://www.metmuseum.org/art/collection/search/53937 ；61417：https://www.metmuseum.org/art/collection/search/61417
- Davis Museum 2014.43：https://davis.emuseum.com/objects/13848/tlv-mirror-with-shangfang-inscription
- Brooklyn Museum：https://www.brooklynmuseum.org/opencollection/objects/21525
- 京都国立博物馆：https://knmdb.kyohaku.go.jp/eng/6420.html 、https://knmdb.kyohaku.go.jp/eng/6441.html
- 早稻田大学会津八一纪念博物馆：https://www.waseda.jp/culture/aizu-museum/other/2019/07/03/2706/
- Nelson-Atkins：https://art.nelson-atkins.org/objects/2130/mirror-with-tlv-patterns-and-four-direction-animals
- 人民日报 2021-03-20《铜镜文化的魅力》：https://paper.people.com.cn/rmrbwap/html/2021-03/20/nw.D110000renmrb_20210320_3-05.htm
- Wikipedia "TLV mirror"：https://en.wikipedia.org/wiki/TLV_mirror
- Cammann 1948 (JAOS 68)：https://www.semanticscholar.org/paper/The-%22TLV%22-Pattern-on-Cosmic-Mirrors-of-the-Han-Cammann/a95062e228c2edb09907ea3810b6494f771a8a26
- Loewe 1979：https://taylorfrancis.com/chapters/mono/10.4324/9781003290131-3/tlv-mirrors-significance-michael-loewe
- Tseng 2004 (Early China)：https://resolve.cambridge.org/core/journals/early-china/article/representation-and-appropriation-rethinking-the-tlv-mirror-in-han-china/71D2C9018A2A0BB67982F7FC35A7DCF2 ；Tseng 2011：https://muse.jhu.edu/book/61552
- 刘薇 2019 古代青铜器表面高锡锈层综述（北大）：https://archaeology.pku.edu.cn/2019gudaiqingtongqibiaomiangaoxixiucengyanjiuzongshu_liuwei.pdf
- 合金数据：https://link.springer.com/10.1186/s40494-024-01247-9 ；https://en.maiask.ru/data/documents/13_RavichTreisterENG.htm ；https://katalog.hcu-hamburg.de/vufind/Search2Record/SPR055490751 ；https://en.ustc.edu.cn/info/1007/5080.htm ；https://www.scientific.net/AMR.337.743
- Liang & Parker 2021 (Heritage Science)：https://heritagesciencejournal.springeropen.com/articles/10.1186/s40494-021-00496-2
- 透光镜：https://en.wikipedia.org/wiki/Chinese_magic_mirror ；https://dr.ntu.edu.sg/server/api/core/bitstreams/2ae17ba9-810e-4f8e-9b0f-9866667aa0f6/content

---

## 核查记录（2026-10-22，汉镜专业视角复核）

核查方法：WebFetch 在本环境仍然无法解析外网域名，所以全部核查都靠 WebSearch 返回的摘要完成，没有逐页打开原文。下面分三类列出：已改正的、已补充的、仍未核实的。

**已改正**
1. **时代范围**：原稿写"西汉晚期起"。Wikipedia 记 TLV 镜约从公元前 2 世纪产到公元 2 世纪，所以改为两层说法：博局纹总体从公元前 2 世纪起；四神博局镜集中在西汉晚期到东汉。
2. **缘厚**：原稿写 0.6–0.7 cm，补入 Cleveland 1995.298 的 0.5 cm 后，改为 0.5–0.7 cm（约 0.03–0.04 D）。第 0、1.9、2、5 节的数值都同步改了。
3. **Liang & Parker 2021**：作者已核实（Jiafang Liang、Quentin Parker，HKU，*Heritage Science* 9:25）。59 mm 是这面小镜的直径，厚度约 2 mm。原稿把这 2 mm 当作"体厚"来支撑主区厚度，但表中没有说明是哪个部位的厚度，镜子也太小，已注明不能直接套用到 18 cm 镜上。
4. **铭文混条**：原稿把"王氏作竟四夷服"和长沙伍家岭"中国大宁"镜写在同一条里。实际上"中国大宁"镜是另一种 50 余字的骚体铭，据报道以"圣人之作镜兮"起首，已拆成两条，并补了该镜的出土单位（211 号西汉后期墓）、直径 18.6 cm 和缘厚 0.6 cm。
5. **书体**：原稿写"缪篆"，这是汉代印章篆体的名称，不适合称呼镜铭。已改为"篆隶过渡的镜铭体"，著录一般记作"篆书"。
6. **高锡青铜颜色**：原稿第 3.2 节写"略带暖灰"，第 5 节写"偏冷灰"，前后矛盾。按 δ 相约 19% Sn 以上呈银色（Liang & Parker 2021），统一为"银白、略带淡黄暖调，含铅越多越灰"。原稿"金黄色 = <10% Sn"也改正了：低锡偏红，约 10–15% 才是金黄。
7. **镜面凸度**：按矢高公式 s = r²/2ρ 重新核算了比例和曲率半径。结合沈括"鉴大则平"，中大型博局镜的默认矢高从 0.8–1.2% D 降到 0.6–1.0% D。仍然是经验值。
8. **三角缘**：原稿说三角缘是"魏晋以后"才有，改为东汉晚期画像镜、神兽镜已经出现。结论不变：博局镜不用三角缘。
9. **杨联陞 1947**：删去没有核实的"最早"，补了 1952 年 HJAS 15 的补证篇名，以及劳榦 1964、周铮 1987。

**已补充（原稿的缺口）**
- 十二地支与四方、四神的对应（子北、卯东、午南、酉西，每边中间一字对 T），建模必须一致。
- 铭文可以放在钮外方框内（Cleveland 1995.295 的"丹阳善铜"铭就绕钮一周），不一定在外圈。
- 四乳变体（方框外四隅各一乳，见"中国大宁"镜），与八乳型的乳钉位置不同。
- L 的旋转手性在不同镜上可以不同，日本研究中有"正 L / 反 L"的鉴别，建议把手性做成参数。
- 已有学者区分"低锡青铜表面镀锡"，以及汉镜锡量随时代下降、铅量上升的趋势。
- 第 0 节补入两件实测器物：Cleveland 1995.298（16.9 / 1.1 / 0.5 cm）和"中国大宁"镜（18.6 cm，缘厚 0.6 cm）。

**仍未核实（保留标注）**
- V 尖朝方框角、L 同向旋转、八乳在 T 两侧：都和人民网"方框四隅外与 V 相对、T 与 L 相对"以及 Cammann"十字"说相符，但没有找到逐件的文字说明，只来自照片观察。
- 新莽"善铜"铭后三句、"中国大宁"铭全文、李学勤 1997、六安镜"高铅低锡→低铅高锡"的结论，以及所有标【经验值】的高度和比例数据。
- Cleveland 各件的通高和缘厚：搜索摘要只确认了 1995.295 的直径 16.3 cm 和重 756 g，以及 1995.298 的全部尺寸；其余数据沿用原稿。
- Met 17.118.42 的直径 16.8 cm 只见于 Curationist 转录，Met 页面没有直接确认。

**本次核查用到的来源**
- Wikipedia "TLV mirror"：https://en.wikipedia.org/wiki/TLV_mirror
- Cleveland 1995.295：https://www.clevelandart.org/art/1995.295 ；1995.298：https://www.clevelandart.org/art/1995.298
- Liang & Parker 2021（作者信息）：https://commoncore.hku.hk/2021/02/25/research_article_liang_parker/ ；正文：https://link.springer.com/10.1186/s40494-021-00496-2
- 人民日报 2021-03-20《铜镜文化的魅力》：https://paper.people.com.cn/rmrbwap/html/2021-03/20/nw.D110000renmrb_20210320_3-05.htm
- 国博"中国大宁"镜报道：https://www.visitbeijing.com.cn/article/47QoQxHCmY8 、https://www.thepaper.cn/newsDetail_forward_10117247
- 京都国立博物馆"新有善铜"铭镜：https://knmdb.kyohaku.go.jp/eng/7904.html
- 早稻田会津八一纪念博物馆：https://www.waseda.jp/culture/aizu-museum/?p=2706
- 京都府埋藏文化财论集（正 L 字文）：https://www.kyotofu-maibun.or.jp/data/kankou/kankou-pdf/ronsyuu3/part2/3-19-300.pdf
- 西汉镜铭篆隶问题：https://journal-s.scnu.edu.cn/cn/article/id/f220f9aa-0b9d-4adf-9224-33bbb2c1a7a5
- Met 53937 / 61417：https://metmuseum.org/art/collection/search/53937 、https://www.metmuseum.org/art/collection/search/61417 ；Curationist：https://www.curationist.org/es/works/work-met-53937
- 六博盘布局：https://en.wikipedia.org/wiki/Liubo 、https://www.babelstone.co.uk/Blog/2009/05/lost-game-of-liubo-part-1-funerary.html
- 镀锡与高锡区分：https://hmsjournal.org/index.php/home/article/view/665/645
