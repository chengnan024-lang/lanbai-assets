# Fins 是怎么做一个世界的：给《蓝白》的调研

> 写的人：网页调研会话（受「蓝白总控安排」委托），2026-10-24。
> 范围：VRChat 创作者 **Fins**（本名 Tom Trinh，VRChat 公司 3D 美术 / 灯光美术，个人品牌 Finsworks Interactive）。主要看 *District Roboto*、*Complex 7*、*Project: Lost Worlds*，顺带看 *Magic Heist*、*Treasure Heist*、*Submerge* 这几部乘坐类作品。
> 方法：全部读原文。播客读的是完整文字稿；日文报道读的是正文，关键截图也看了；世界说明直接从 VRChat 公开 API 取；Fins 2025-03 的进度视频截了帧来看。搜索摘要只用来找链接。
> 标注：**【确定】** = 原文明说，或截图里看得见；**【推测】** = 我根据原文推出来的，没有直接证据。原文引用保留原语言（英文文字稿是 Voices of VR 的“rough transcript”，错字照抄，例如 Magic Heist 写成 “Magic Haze”）。

---

## 0. 一页摘要

1. **文字**：Fins 的世界文字分三类。第一类是**长在世界里的字**：招牌、海报、巨大的区域标题（“SECTOR 43 / RESIDENTIAL DISTRICT”）。第二类是**拿起来读的卡片**：报纸、文件，点了以后弹出一张世界空间的卡片，右上角有一个“文 / A”翻译按钮，可以切到日文。第三类是 Lost Worlds 的**旁白和语音字幕**：显示在画面下部，开始前在设置面板里选语言（ENGLISH / 日本語），还可以关掉语音字幕。**没有任何证据表明它会自动跟客户端语言走**，都是玩家自己点。日文由人工译者 RIKU 翻译。
2. **叙事**：他想让环境叙事“跨过语言”，NPC 只发机器人的哔哔声，不说任何语言。故事靠可读的物件、收集品解锁的背景说明、口耳相传的隐藏区慢慢露出来。他反对手把手地讲。
3. **灯光**：全部烘焙。他自己的说法是“smoke and mirror”：放现实里不存在光源的隐形灯和隐形面光，把反射探针放到“不该在”的地方、改它的颜色，只为把要讲的东西提亮。先做流线和形体，灯光放在后面。贴图一换就推倒重打，常常一整天都在重打灯光。
4. **乘坐与定时段落**：从 *Mine Heist*（轨道车）、*Magic Heist*（20 分钟的轨道叙事），到 *Lost Worlds*（大约 1 小时的“VR 电影”，标签就叫 Ride），他有一条完整的乘坐类作品线。舒适性上：颠簸的吉普车被他整段砍掉；穿梭机其实是**原地旋转**，靠这个给出运动感；轨道的弯道反复磨平。
5. **多人**：*Complex 7* 写明“All actions are local”。*Magic Heist* 每个人各看各的，随时能进。*Lost Worlds* 最多 6 人，由房主同步，**开场以后不能再进人**。
6. **性能**：只做 PC 版。实时灯会让 draw call 翻倍，所以不用。世界说明里写“请预载”。他承认最重的段落在 RTX 3060 上跌到 30 fps 以下（MoguraVR 实测）。场景按段落清理再激活，反复复用原点附近的空间。
7. **对《蓝白》最有用的 10 条**见第 7 节。

---

## 1. 文字和叙事

### 1.1 区域标题和招牌：长在世界里的字

- **【确定】** District Roboto 出门后，往亮处走，街景展开的那一刻浮出世界标题，“像误入了游戏片头”。Complex 7 的区域入口也有巨大的立体标题：截图里是 “SECTOR 43” 和 “RESIDENTIAL DISTRICT” 两行，主标题白色、编号黄色，副标题小字黄色，悬在街道上空。
  - 原文：「広がる街並みと、タイトルが出現。まるでゲームのオープニングの中に迷い込んだような演出です。」——[S6]
  - 截图：[S4] 第 7 张。
- **【确定】** 2026 年更新加的 *Sub Sector 41* 是霓虹商业巷，招牌混用英文、汉字、韩文，还有很多做得很细的海报。
  - 原文：「英語のほかに、漢字やハングル語で書かれた看板が並んでおり、アジア圏の雰囲気もあります。」——[S4]
- **【推测】** 这些招牌和标题**不随玩家语言改变**，是画面的一部分。截图里看不到它们的多语版本。

### 1.2 可读物件：拿起来读的卡片，自带翻译按钮

- **【确定】** Complex 7 里散落着可以点的文件 / 报纸。点开后弹出一张卡片：白色标题栏，深紫正文区，右上角一个橙色“A / 文”翻译图标，下方中间一个“▼”翻页箭头。英文版标题是 “The Eclipse”，切成日文后是「大統領令：国家隔離命令」。文案不是逐字翻译，日文更短，按日文重写过。
  - 原文：「（ワールド内には、インタラクトできるファイルが落ちており）」「（日本語に切り替えて読むこともできます）」——[S4]，截图第 15、16 张。
- **【推测】** 卡片是**世界空间**的：第二张截图里卡片明显倾斜、有透视，不像贴在屏幕上的 HUD。切换由**每张卡片上的按钮**完成，不跟客户端语言走。世界说明写着 “All actions are local”（[S7]），所以按了只影响自己。
- **【确定】** 这次日文翻译由人工译者完成。译者 RIKU 的 X 简介里列有 “Complex7('26)”“Project Lost Worlds”——[S13]。
- **【确定】** 2023 年 Fins 就说过要尽量本地化，理由是日、韩玩家会觉得“被落下”。
  - 原文："A lot of my fans are from other community, like Japanese or Korean community, where sometimes they can't enjoy the world as much. And I take the effort to try to include translation."——[S1] 00:07:17

### 1.3 Lost Worlds 的旁白、语音字幕和语言设置

- **【确定】** 开场在湖边，往湖走几步会出现一块面板。面板上是 **SETTINGS → Language: ENGLISH / 日本語**，下面是 **Voice Subtitles: ON** 开关；右边写 “Make sure all players are ready. New players will not be able to join after this point.” 和 **CONTINUE** 按钮。MoguraVR 提醒要在按 Ready 之前切好语言。
  - 原文：「パネルの設定欄で字幕を日本語に切り替えられるので、スタート（Ready）ボタンを押す前に設定を変更しておきましょう。」——[S5]（日文版），截图第 2 张。
- **【确定】** 字幕显示在**画面下部**，白色无底衬，两行居中，字号偏小。截图里同时有上下黑边（四角切成斜角），像电影遮幅。
  - 原文：「（字幕はこのように、画面下部に表示されるシステム）」——[S5]，截图第 3 张。
- **【推测】** 这是**跟着视野**的字幕（头锁或近似头锁），至少在序章是这样，配合遮幅黑边。从一张静帧判断不了它在头显里是完全头锁，还是慢跟随的面板，也判断不了截图是不是桌面模式拍的。《蓝白》圣经 §1.8 禁止任何锁屏元素，这一点**不要学**。值得学的是“语音字幕可以关”。
- **【确定】** 世界说明双语，写明 “1 Hour English ⁄ Japanese Support / 対応言語：英語／日本語”——[S7]。Raindance 的演职员表写 “Japanese Translation: Riku”——[S8b]。
- **【确定】** 2023 年 Fins 说过，NPC 会有“chat box”，因为文字比语音好翻译。
  - 原文："they're going to have chat box where that would be easier to, you know, translate between language."——[S1] 00:25:38
- **没找到**：字幕或卡片的**淡入淡出时长、停留时长**。所有来源都没写，截图也看不出。

### 1.4 故事怎么露出来

- **【确定】** 他的目标是**跨过语言**的环境叙事，让人看一眼就懂发生了什么。
  - 原文："I try to make it in a way that transcends language barrier."——[S1] 00:07:17
- **【确定】** NPC 只发机器人的“哔啵”声，不说任何语言。
  - 原文："the sound they make this is like a little bit bop robot sound. So there is no like certain language that you have to understand"——[S1] 00:25:38
- **【确定】** 不手把手：他推崇 Dr. Morrow（应为 Dr. Morro）的环境叙事，只给够你自己形成解读的量。
  - 原文："they don't give away too much to the point like hand holding you"——[S1] 00:11:48
- **【确定】** 用收集换背景：District Roboto 集齐 20 只小猫机器人后，可以克隆机器人头像，每个头像台上写着那台机器人的来历，同时暗示“人类为什么不见了”——[S3] 00:23:20。Complex 7 里地上的报纸讲出“未确认物体撞击 → 病毒 → 全国隔离令”——[S4]。
- **【确定】** 动线是“暖 → 冷 → 奖励”。Complex 7 从温暖的公寓出发，出门下雨，进入黑暗的地铁隧道，出站后是城市中心。他说这是对探索的奖励。
  - 原文："It went from this very home feeling, this very warm feeling, to this very dark and cold place in the tunnel"——[S1] 00:09:54
- **【确定】** 每件东西都要经得起一问“它为什么在这”：这是从游乐园排队区学来的，排队的路本身就在给你做开场。
  - 原文："every single thing you look at and you think of like why is this thing here and if you think for a moment it makes sense"——[S2] 00:34:39
  - 原文："When you wait in line for like a particular ride, the line actually designed to like kind of onboarding you"——[S2] 00:34:39
- **【确定】** Lost Worlds 的开场：看不见的叙述者讲童年，母亲的声音说“总有一天你会去那里”，远处一枚火箭升空。之后是太空港的简报大厅：观众坐在一排排座椅上看一段“行程介绍片”（进度视频里能看到 “ITINERARY INTRODUCTION VIDEO / UNISA ASTORIA” 的片头），再乘自动步道去发射台——[S5]、[S12c]。
- **【确定】** 场景要先有故事。
  - 原文："it needs to have a story before it exists."——[S3] 00:23:20

---

## 2. 画面：灯光是重点

### 2.1 “smoke and mirror”：为了讲故事而作弊的光

- **【确定】** 他不追求光的物理正确，会在需要的地方造光。
  - 原文："So when it comes to the lighting, it's just a weird form of like smoke and mirror, I would say."——[S1] 00:18:42
  - 原文："you have to make an invisible light where it's light casting but there is an actual light, no light casting object exists in the world, it's just there just to emphasize on that particular area."——[S1] 00:18:42
- **【确定】** 例子是一屋子书里的“那一本”：怎么让烛光旁边那本藏着关键信息的书，从一百本书里跳出来。
  - 原文："what if you want to emphasize this book near this candle that had like an important piece of information"——[S1] 00:18:42
- **【确定】** 具体手段有：**只参与烘焙的隐形面光**（运行时不存在），用来拉对比、把物体推到玩家眼前；**把反射探针放到“不该在”的位置**、改探针颜色；手动补光探针、手放灯。
  - 原文："basically invisible plane of light that casting light after baking"——[S3] 00:20:43
  - 原文："placing a reflection probe that might not be where it's supposed to be, just so that it delivers a narrative and immersive visual to the players to see."——[S3] 00:20:43
- **【确定】** 作弊的尺度取决于观众愿意相信多少。魔法世界里屋里可以有太阳，写实世界就得守规矩。
  - 原文："people are not going to question if there's a sun outside, under, inside a building because it's magic."——[S3] 00:20:43
- **【确定】** 他用光来分区和定情绪：霓虹区“这里最热闹”，又黑又脏的区“这里出过事”。
  - 原文："lighting is a balance in art between realism, storytelling, and all of that."——[S3] 00:17:15
- **【确定】** 2026 年的更新让区域的亮暗交替成为节奏：*Sub Sector 41* 霓虹刺眼 → 隔离区偏暗、路边有不明生物 → *Complex 7* 本区灯笼、暖光，“又回到明亮的气氛”——[S4]。

### 2.2 烘焙、探针、发光体

- **【确定】** Complex 7 **全部烘焙**。原因是保真度高、draw call 本来就高，再加实时灯就会翻倍。
  - 原文："So all the lighting in Complex 7 is baked for performance purpose, of course."——[S1] 00:20:26
  - 原文："So any more real-time lighting would just double the draw call. It's not acceptable."——[S1] 00:20:26
- **【确定】** 头像的光（动态物体）一直在修。District Roboto 后来更新为支持 **REDSIM 的 VRC Light Volumes**；Paradisa 的更新说明写着修了“broken light probes / lighting / avatar too bright”——[S7]。
- **【确定】** Lost Worlds 的 “Shader and Technical Advisor” 是 **Orels**——[S8b]。（【推测】就是做 ORL shaders 的那位 orels。）
- **没找到**：雾、调色 / LUT、后期栈的具体参数；发光体（emissive）怎么参与烘焙；具体的探针密度。所有访谈都只讲到“放什么、为什么放”，没讲参数。

### 2.3 工作流：灯光放在后面，而且一定会返工

- **【确定】** 先定玩家的流线、比例和形体语言（方的、尖的、圆的给不同感觉），然后定材质，**灯光靠后**。白模不是灰的，是上了色的方块，先在上面打光，再换成正式资产。
  - 原文："Lighting is more later on."——[S3] 00:56:17
  - 原文："They are colored. And then I would make the lighting on them."——[S2] 00:09:00
- **【确定】** 一换贴图，之前的光就可能不成立，只能拆了重来，常常一整天都在重打灯光。
  - 原文："it's not unusual for me to spend entire days back in the lighting over and over and over again."——[S1] 00:20:26
- **【确定】** 用一张“hero art”锁住调色板、气氛和光，免得做到后面走样。
  - 原文："you probably want to do like they call it like hero art."——[S2] 00:07:57
- **【确定】** 参考图板用 PureRef，每个项目一个，按区域分块（他举的例子是埃及项目：金字塔、内景、河、人物各一块）。
  - 原文："Every project I make has a separate folder."——[S10b]
- **【确定】** 灯光的师承：Stray 的联合创始人 Koola 的 UE4 灯光作品。District Roboto 起初只是对 Stray 的灯光练习——[S3] 00:14:09、[S7]、[S6]。

### 2.4 比例和构图

- **【确定】** Lost Worlds 的 Astoria 号长度相当于“五六个 Complex 7 首尾相接”。气态巨行星 Stratos 接近真实行星尺度的一半，需要专门的 shader 才能在那么远的地方画出来。他说以后可能也得“作弊”缩尺，但目前坚持用真实尺度。
  - 原文："you need to have about five or six Complex 7 line up back to back to actually get to the length of Astoria."——[S2] 00:31:14
- **【确定】** **窗框就是演出装置**：Bolt 穿梭机的前窗是镶在框里的窗，迟迟不让你看到 Astoria 的全貌。MoguraVR 的记者说自己像游客一样探着身子找角度。Hercules 降落船则反过来，前面是整面大玻璃，让人一眼看全峡谷。
  - 原文：「これが「アストリア」の全容をなかなか見せないという“演出装置”として機能します。」——[S5]
- **【确定】** 第一部雨景世界 *Shark's Fin Cafe*（2018）把 Shadertoy 上的车窗雨滴 shader 移植到窗玻璃上，号称 VRChat 第一个。
  - 原文："So I made the cafe and I made it rainy and made, you know, the whole glass with the condensation and the rain dripping down."——[S10a]

---

## 3. 体验设计

### 3.1 视线引导

- **【确定】** 他主要靠光引导视线（见 2.1）。可拾取物用闪光粒子标记，但他承认对电影节观众不够清楚，要改。
  - 原文："even then, I found that it wasn't clear enough, especially in the films and cinema people."——[S3] 00:44:01
- **【确定】** 他用开着的门勾起好奇心：出生点是安逸的家，门开着，走廊一直延伸下去。
  - 原文："people always have the open door like, wait, there's more to this?"——[S1] 00:09:54
- **【确定】** Magic Heist 有**注视触发**：盯着墙上的诅咒看，它就会爆开。
  - 原文："if you look the gaze at it, it would pop."——[S3] 00:32:21
- **【确定】** Lost Worlds 有机器人导游 Reggie / Reginald 带路，正式版里可以把它静音。
  - 原文："you can turn up Reggie or you can mute him."——[S2] 00:44:31

### 3.2 载具和定时段落：Fins 的乘坐类作品线

| 作品 | 年份 | 形式 | 关键点 |
|---|---|---|---|
| *Submerge* | 2019（Spookality） | 潜水艇下潜到最深的海，约 30 分钟 | “A ride to the depths below.” ——[S12d]（我**没进过**这个世界，只读了发布帖） |
| *Mine Heist* | VRChat 官方 Game Jam | 坐上轨道车，左右倾身吃金币、躲障碍 | 原型。弯道由 Cyan 写代码平滑，一遍遍重跑去磨——[S3] |
| *Magic Heist* | 2021 Raindance（Spirit of Raindance 奖） | 约 20 分钟的轨道叙事，配音、注视机关、结尾“Boss” | “ride attraction style”——[S2]；“20 minute narrative experience”——[S3] |
| *Treasure Heist* | 2022 威尼斯竞赛 | 解谜 + 后半段乘坐 | 因为 Magic Heist 的反馈（晕、想下车自己走）才加了步行部分——[S3] |
| *Project: Lost Worlds — Journey to Erios* | 2024 威尼斯（demo）；2026-06-26 公开 | “两部曲的电影式体验”第一部，约 1 小时（Raindance 写 90–120 分钟） | 标签 `author_tag_Ride`，最多 6 人——[S7]、[S8b] |

- **【确定】** 定时段落按“清理 → 激活”切场景，并反复复用同一块空间：农舍出生点，后来就是 Erios 星球的位置。
  - 原文："Every scene have a transition and every transition have its own cleaning and activating."——[S2] 00:29:00
- **【确定】** **载具原地不动、只转**，运动感靠画面给。他还发现一个暴露点：旋转会让头像的头发被甩乱。
  - 原文："the space shuttle is actually just moving stationary, it's just rotating stationary, but it gives you that sense of motion."——[S2] 00:29:00
  - 原文："You're literally seeing your avatar and your friend's avatar's hair is starting to go wonky"——[S2] 00:29:00
  - Mogura 的截图（Bolt 机舱）里能看到同行者头像的辫子在飘——[S5] 第 15 张。
- **【确定】** 段落节奏靠试映来修：发射倒计时一开始太长，听了 Kent Bye 的意见剪短。
  - 原文："At first it was a bit too long and I got great feedback. from Ken and then I cut it down."——[S2] 00:18:57
- **【确定】** 高潮处留白：升空后地球“滚下车窗”，**没有旁白，只有音乐**，留时间给人自己想。
  - 原文："there's no narration nothing it's just a little music and a little give people that time to think"——[S2] 00:18:57
- **【确定】** 时间跳跃用“醒来”来切：序章结束后跳到 38 年后，主角在太空港“醒来”；登船后再跳几个月——[S5]。

### 3.3 声音和音乐

- **【确定】** 2026 年的更新在城市深处加了电梯，通往 **live house**，台上是机器人乐队。主唱和别的机器人型号不同，身体是曲线的。
  - 原文：「ロボットたちの街なので、中で演奏しているバンドも当然ロボット。」——[S4]
- **【确定】** 他的世界里有给钱就演奏的街头音乐家机器人。District Roboto 往吉他盒里投币，它会弹一首——[S6]；Complex 7 也有这样的计划——[S1] 00:25:38。
- **【确定】** Lost Worlds 的音乐来自 AudioNetwork 曲库——[S9b]。配音演员署名：Reginald、叙述者、“妈妈”各一人——[S8b]。发射段的台词是他听了几小时 NASA 航天飞机发射录音后改写的——[S2] 00:18:57。
- **【确定】** 音乐授权是真金白银：Treasure Heist 的素材、音乐、授权、配音加起来将近 1000 美元——[S1] 00:30:57。
- **没找到**：live house 的曲目来源；空间音频、混响区的做法。

### 3.4 多人一起看

- **【确定】** 三种模式他都做过：
  1. **全本地**：Complex 7 “All actions are local.”——[S7]。NPC 也打算做成本地的，避免网络同步出错。原文："it might be local where it just doesn't ruin the experience by trying to network the NPC."——[S1] 00:25:38
  2. **各看各的乘坐**：Magic Heist 不同步，任何人随时进、随时坐，各自看到的进度不同。原文："Magic Heist is a solo, non-sync group experience."——[S3] 01:01:00
  3. **全组同步**：Treasure Heist、Lost Worlds。开发难度是前者的四五倍。原文："The difficulty of the development is increased by four or fivefold."——[S3] 01:01:00
- **【确定】** Lost Worlds 由房主同步，**中途加入不支持**。开场面板直接提示“开始后新玩家进不来”，实例上限 6 人。他说以后可以加一个“追上大家”的按钮。
  - 原文："it's master reliant which means late joining right now it's not possible"——[S2] 00:32:45
- **【确定】** 他设计社交传播：隐藏区靠朋友之间、推特上口耳相传，模仿早年游戏论坛里互传秘籍的感觉——[S1] 00:14:53。

### 3.5 VR 舒适

- **【确定】** 早期 Lost Worlds 原型是开吉普车越野（Joe Hunting 的纪录片 *We Met in Virtual Reality* 里那段就是）。他因为晕动症把它整段砍了，重写了故事。
  - 原文："having a drip on bumpy surface and going off-roading probably not the most comfortable thing ever especially if you have motion sickness"——[S2] 00:39:13
- **【确定】** 轨道车的弯道一遍遍重跑来磨平；他承认这不能让所有人都不晕。
  - 原文："we see where the turn is a little bit too tight or too sudden, we had to smooth that out."——[S3] 00:27:20
- **【确定】** Magic Heist 的观众反馈是：有人晕，有人想下车自己走——[S3] 00:36:37。
- **没找到**：亮度上限、闪光控制（光敏安全）方面的任何说法。

### 3.6 在威尼斯和 Raindance 怎么展出

- **【确定】** 2022 年威尼斯：Treasure Heist 进竞赛，Magic Heist 和 District Roboto 进 VRChat Worlds Gallery。他发现电影节观众和 VRChat 玩家是两类人：前者觉得谜题太难，后者觉得太简单——[S3]。
- **【确定】** 2023 年威尼斯：Complex 7 进 **Venice Immersive 竞赛单元**，片长标 30 分钟。他特意为电影节做了一个**极度线性**的版本，正式版再开放支线——[S9a]、[S1] 00:13:41。
  - 原文："right now it's extremely linear and it's also kind of designed for the festival"——[S1] 00:13:41
- **【确定】** 2024 年威尼斯：Lost Worlds demo 进竞赛，完成度 30–40%；由两名人类导览员带小组，加上机器人导游 Reggie——[S2]、[S11]。
- **【确定】** Raindance：2023 年 Complex 7 提名 Best Immersive World，办了“作者带逛”。2026 年 Lost Worlds 在 VRChat 里办了作者问答，Fins 还参加了 “The World Builder's Blueprint” 圆桌——[S8a]、[S8b]、[S8c]。

---

## 4. 性能

- **【确定】** 只做 PC 版。他在 VRChat 的本职是做 Quest 优先的内容，个人作品则反过来，保真度优先。将来的 Quest 版最多给“半个体验”，比如只能待在公寓里。
  - 原文："maybe they don't get to go outside the apartment or maybe they get to see a little bit of like the city center"——[S1] 00:22:04
- **【确定】** 性能是硬底线。
  - 原文："If it's laggy or uncomfortable to play, people are not going to have a good time."——[S1] 00:20:26
- **【确定】** 世界说明里都写着要预载：Complex 7 是 “［World Pre-Loading HIGHLY Recommended］”，Lost Worlds 是 “PLEASE PRELOAD THE WORLD!”——[S7]。
- **【确定】** 实测：Lost Worlds 最后降落 Erios 之后很吃 PC，MoguraVR 的 RTX 3060 长时间低于 30 fps，记者建议配置不够的人先用桌面模式。
  - 原文：「自分の環境（RTX 3060）では30FPSを下回る状態が続きました。」——[S5]
- **【确定】** 遮挡剔除：他基本不用，因为烘焙出来的遮挡数据是“永久的”，一块空间烘了就不能再给别的场景复用。只有 Astoria 号内部这种不复用的空间才用。
  - 原文："I don't get to do occlusion cooling too much because the occlusion cooling is permanent."——[S2] 00:29:00
- **【确定】** 浮点误差：Astoria 号太远，坐穿梭机到达时已经开始出现浮点误差——[S2] 00:31:14。
- **【确定】** 2026 年 Complex 7 的大更新同时改善了灯光和性能、修了 bug（Fins 本人对 MoguraVR 说的）。
  - 原文：「Finsによると、今回のアップデートでは、エリア追加のほかライティングが改善され、不具合の修正やパフォーマンスの改善も行われたとのこと。」——[S4]
- **没找到**：LOD 策略、贴图预算、包体大小、目标帧率的具体数字。

---

## 5. 他本人的创作理念

- **【确定】** 光是叙事工具，不是写实的副产品（见 2.1）。
- **【确定】** 公开标准极严：做过约 100 个世界，只公开约 35 个；没有存在理由、没过 QA 的不放出来。
  - 原文："I have an extremely strict public standard."——[S2] 00:10:21
- **【确定】** 做文化题材要考据，要尊重原文化。Treasure Heist 的埃及墓里误用了希腊符号，被人指出后他认错并改掉。
  - 原文："One of the things people point out is that I have Greek symbols on some of the Egyptian tombs."——[S3] 00:46:18
- **【确定】** 截止日期“既是朋友也是敌人”。
  - 原文："Deadline is a friend and enemy at the same time."——[S2] 00:13:37
- **【确定】** Complex 7 的作者自述：技术有限，只希望把人带去另一个世界，哪怕只是片刻。
  - 原文："my wish is that this project will bring the players to another world even if briefly"——[S9a]
- **【确定】** VR 是现实的朋友，不是替代品。
  - 原文："it can be a friend to reality. It's not a replacement."——[S1] 00:34:36
- **【确定】** *Lost Worlds* 的“lost”指成年后丢掉的童年想象。叙述者就是他自己——[S2] 00:18:57。

---

## 6. 查不到或没核实的

- **innovatopia.jp**：几轮搜索都没找到它报道 Fins 的文章，所以没有用。
- **YouTube 的讲座和实况**：YouTube 页面在这里拿不到描述。Glitches.VR 访谈有视频版，我读的是文字版。2026-06-19 的 Raindance 圆桌有没有录像，没查到。
- **Virtual Worldhoppers 的长评**（Complex 7）：网站证书过期，换方式抓取返回 503，没读到。
- **X / 推特**：只能逐条读已知帖子（见来源表），时间线读不到。
- **Lost Worlds 的语言设置是每人各自生效还是全房间统一**：面板截图看不出来。Complex 7 写了 “All actions are local”，所以那边的卡片翻译应该是本人生效（推测）。
- **日期冲突**：Voices of VR #1444 说 Lost Worlds 2025 年公开，2025-03 的进度视频片尾写 “SUMMER 2025”；实际公开时间是 **2026-06-26**（VRChat API 的 `publicationDate`，Raindance 页面同日）。时长：世界说明和 Mogura 写约 1 小时，Raindance 写 90–120 分钟。

---

## 7. 对《蓝白》最有用的 10 条

> 每条都对上了我们自己的条目。“学”是建议照做，“对照”是我们已经这样做、Fins 的经验印证了，“不学”是 Fins 这么做但我们不该跟。

1. **【学】用窗框藏住大景，让人探身去找。** Bolt 的窗框“迟迟不让人看到全貌”，记者像游客一样探着身子找角度（[S5]）。《蓝白》整片 20 分钟都在 PAZ 的车窗里（圣经 §4），A 柱、中柱、挡风上沿就是现成的遮幅。巨像、宫殿、裂口这类大景，可以先只露一角，等乐句到了再全部给出。**要量的一件事**：圣经 §1.8 规定，离开车厢包围盒的人会在 0.5 秒遮罩下被送回座位。如果我们鼓励探身去看，就要确认正常的探身不会触发它。
2. **【学】每一幕只挑一个“要读的东西”，用隐形光去提亮它。** Fins 的“烛台边那本书”（[S1]），手段是只参与烘焙的隐形面光，加上挪了位置、改了颜色的反射探针（[S3]）。对《蓝白》：第 7b 幕河伯宫殿的“那一扇门”，第 9 幕“那一面镜”，都可以照此打光。诗句不加光（圣经 §7.2 不许辉光），要提亮的是诗句**对着的那个画面焦点**。
3. **【学】语言要有看得见的手动开关，不要只靠客户端语言。** Fins 的两种做法都是玩家自己点：卡片上的“文 / A”按钮，开场面板上的 ENGLISH / 日本語（[S4]、[S5]），译者署名（[S8b]、[S13]）。D-30 现在按客户端语言自动选（`FromLocal/code/timeline_v1/LB_Journey.cs` 调用 `VRCPlayerApi.GetCurrentLanguage()`）。**【推测】** 很多中、日玩家的 VRChat 界面是英文的，他们会被自动分到英文诗。（**10-24 补充，【确定】**：客户端 2024.1.1（2024-02-14）起，新装的客户端第一次启动会按操作系统语言自动设置界面语言，原文是 “we'll now attempt to detect the language of your operating system on first launch and automatically localize if your language is available.”——[S14]。所以这个风险主要落在以前手动设过英文界面的老玩家身上，比我原先估计的小。另外，繁体中文的代码是 `zh-HK`，不是 `zh-TW`——[S15]。）建议保留自动选择当默认，同时在第 1 幕站牌或公告板上放一个 **中 / 日 / EN 三选一**，只对本人生效。日文書き下し最好请母语者校一遍，Fins 的日文也是人工译者做的。
4. **【对照】高潮处不放字，只留音乐。** Fins 在“地球滚下车窗”那一段刻意不放旁白，只给音乐（[S2]）。这和我们 §7.4-2 的“高峰上没有字”是同一个判断，可以把这条当作外部印证。
5. **【学】请外人试看，按反馈剪节奏。** 发射段一开始太长，Fins 听了 Kent Bye 的意见才剪短（[S2]）。Magic Heist 是试映以后才知道观众想下车（[S3]）。《蓝白》的时间轴锁在马勒上，剪不了音乐，但每幕“先有画面、后有字”的 4–12 秒间隔，以及字幕停留的公式，都值得找没看过的人坐一遍再定。
6. **【对照】零颠簸，车不动。** Fins 因为晕动症砍掉了整段颠簸吉普；穿梭机是原地转、世界在动；轨道车的弯道一遍遍磨（[S2]、[S3]）。这和圣经 §1.8 的“零颠簸、车不动世界动、偏航 ≤ 3°/s”完全一致。他补了一个我们可以顺手检查的点：**只要乘员所在的参照系真的在转，头像的头发和 PhysBones 就会被甩**（[S2]，Mogura 截图里能看到）。第 2、11 幕的偏航如果是转车厢而不是转世界，要在头显里看一眼同车人的头发。
7. **【对照 + 学】迟到的人：我们的做法比 Fins 好，但要学他把话说清楚。** Lost Worlds 是房主同步，开场后锁死不让人进，上限 6 人（[S2]、[S5]）。我们的 `timeline_v1` 只同步“发车的服务器时刻”，迟到的人按 t 进入当前段落，这一点更好，保留。要学的是**在发车前用明白的话告诉大家**。Fins 的面板写的是 “Make sure all players are ready. New players will not be able to join after this point.”。我们可以在站牌或公告板上写“车将在 X 秒后开出，之后上车的人会从路上加入”。另外建议把**实例人数上限设成座位数**（Lost Worlds 就是 6）。
8. **【学】场景只在遮挡下切换；遮挡剔除只给固定不动的段落用。** Fins 按“清理 → 激活”换场景，复用原点附近的空间；烘焙的遮挡剔除是“永久的”，复用的空间就用不上（[S2]）。我们 §1.9 已经规定根物体只在黑、白、入云、水下时切换，这和他一致。**【推测】** 要补一条：如果某一幕的外景是整体移动的（车不动世界动），那一幕的几何就不能当静态遮挡体去烘焙遮挡剔除。宫殿（7b）这类热点要提前确认它在那一段里是静止的，才能吃到遮挡剔除的好处。
9. **【学】写明“请预载”，给低配一个退路。** Fins 每个大世界的说明里都写了预载，最重的段落在 RTX 3060 上跌破 30 fps（[S5]、[S7]）。我们的预算是 3060 级跑 90 Hz（§1.9），已有 auto-lite 和出生时预热 shader。建议在世界说明里加一句双语“请预载”，并且在第 4 幕、第 7b 幕两个热点按 Mogura 的配置（3060）实测一遍。
10. **【学】汉代宫殿的考据：每个区一块参考板，再找懂行的人挑错。** Fins 做埃及墓时，一边开着几小时的纪录片，一边按区分 PureRef 参考板，还是漏了希腊符号，被人指出才改（[S3]、[S10b]）。第 7b 幕“鱼鳞屋兮龙堂，紫贝阙兮朱宫”要做汉代的宫：建议按屋顶、门阙、纹样、器物、颜色分板，每板注明出处（墓葬、画像石、明器），交给懂汉代的人挑一轮“时代错位”。以后如果需要网页考据，可以找这个会话。

---

## 附 A · 世界元数据（VRChat 公开 API，2026-10-24 读取）

| 世界 | ID | 上限 | 首次上传 → 公开 | 最近更新 | 访问 / 收藏 | 说明里的关键句 |
|---|---|---|---|---|---|---|
| District Roboto | `wrld_ca2c5edc-b44b-4c68-863a-9a94b04889d5` | 80 | 2021-09-07 | 2026-04-13 | 38.0 万 / 5.0 万 | “Updated to support Red Sim's Light Volume … Originally started as a lighting study” |
| Complex 7 | `wrld_ff414a30-31e3-44bb-9c8e-3d721e895b0b` | 80 | 2023-02-07 → 2023-11-04 | 2026-08-27（v58） | 61.0 万 / 9.9 万 | “［World Pre-Loading HIGHLY Recommended］All actions are local” |
| Paradisa | `wrld_6c6dae9a-b166-49fd-9410-737fc8c1c3fe` | 80 | 2025-07-19 | 2025-08-01 | 24.6 万 / 2.7 万 | “fixed broken light probes⁄lighting⁄avatar too bright issue” |
| Project Lost Worlds | `wrld_cb43c149-c9cb-4b9a-b228-ac8833cb69ff` | **6** | 2024-04-06 → **2026-06-26** | 2026-08-28（v134） | 46.1 万 / 4.8 万 | “PLEASE PRELOAD … 1 Hour English ⁄ Japanese Support”；标签 `author_tag_Ride` |

## 附 B · 来源

| 编号 | 来源 | 日期 | 读了什么 |
|---|---|---|---|
| S1 | [Voices of VR #1283 · The Exquisite Lighting in Fins' "Complex 7"](https://voicesofvr.com/1283-the-exquisite-lighting-in-fins-complex-7-vrchat-world/) | 2023-09-26（2023-08-31 威尼斯采访） | 完整文字稿 |
| S2 | [Voices of VR #1444 · Project: Lost Worlds](https://voicesofvr.com/1444-fins-latest-vrchat-adventure-project-lost-worlds-is-a-cinematic-interstellar-safari-with-dinosaurs/) | 2024-09-16（2024-09-01 采访） | 完整文字稿 |
| S3 | [Voices of VR #1143 · Treasure Heist / Magic Heist / District Roboto](https://voicesofvr.com/1143-vrchat-world-builder-fins-and-his-3-experiences-in-venice-immersive-2022-treasure-heist-magic-heist-and-district-roboto/) | 2022（2022-09-09 在 VRChat 里采访） | 完整文字稿 |
| S4 | [MoguLive · 【連載 映えるVRChatワールド】「Complex 7」大型アプデ](https://www.moguravr.com/hotogenic-vrchat-world-2025-0117/) | 2026-01-17 | 正文 + 25 张截图里的 6 张 |
| S5 | [MoguLive · 「Project Lost Worlds」体験レポート](https://www.moguravr.com/?p=318599)（[英文版](https://www.moguravr.com/project-lost-worlds-report-en/)） | 2026-07-17 | 日、英正文 + 47 张截图里的 8 张 |
| S6 | [MoguLive · 「District Roboto」を歩いてみよう](https://www.moguravr.com/?p=189838) | 2022-08-04 | 正文 |
| S7 | VRChat 公开 API：`https://api.vrchat.cloud/api/1/worlds/<ID>`（ID 见附 A） | 2026-10-24 读取 | 世界说明、上限、日期、标签 |
| S8a | [Raindance Immersive · District Roboto: Complex 7](https://raindanceimmersive.com/complex-7) | 2023 | 正文 |
| S8b | [Raindance Immersive · Project Lost Worlds: Journey to Erios](https://www.raindanceimmersive.com/2026-project-lost-worlds-journey-to-erios/) | 2026 | 正文、演职员表 |
| S8c | [Raindance Immersive · The World Builder's Blueprint](https://www.raindanceimmersive.com/the-world-builders-blueprint-crafting-iconic-virtual-worlds) | 2026 | 圆桌介绍、Fins 简历 |
| S9a | [La Biennale · Complex 7](https://www.labiennale.org/en/node/13211)；[2023 Venice Immersive 入选名单](https://www.labiennale.org/en/news/official-2023-venice-immersive-selection-announced) | 2023 | 作者自述、单元 |
| S9b | [La Biennale · Project: Lost Worlds](https://labiennale.org/en/node/15481) | 2024 | 梗概、作者自述、音乐署名 |
| S10a/b | [Glitches.VR · Interview with Fins Part 1](https://glitchesvr.substack.com/p/interview-with-fins-part-1)、[Part 2](https://glitchesvr.substack.com/p/interview-with-fins-part-2) | 2024-08-15 / 16 | 全文 |
| S11 | [UploadVR · Project: Lost Worlds In VRChat Shows Considerable Promise](https://www.uploadvr.com/project-lost-worlds-venice-immersive/) | 2024-09 | 全文 |
| S12a | [Fins on X · Complex 7 发布预告](https://x.com/VRCFins/status/1712984816344576237) | 2023-10-14 | 正文 |
| S12b | [Fins on X · Complex 7 完成](https://x.com/VRCFins/status/1720621794573291535) | 2023-11-04 | 正文 |
| S12c | [Fins on X · Lost Worlds 进度视频](https://x.com/VRCFins/status/1905655782672355621) | 2025-03-28 | 正文 + 视频每 7 秒一帧（共 30 帧） |
| S12d | [Fins on X · Submerge](https://x.com/VRCFins/status/1188867547275251712) | 2019-10-28 | 正文 |
| S13 | [RIKU（译者）on X](https://x.com/Riku7302) | 2026-10-24 读取 | 简介里的翻译作品表 |
| S14 | [VRChat 2024.1.1 更新说明](https://docs.vrchat.com/docs/vrchat-202411) | 2024-02-14 | 全文（首次启动按系统语言本地化；`GetCurrentLanguage()` 改为返回 RFC 5646 代码） |
| S15 | [VRChat 公开配置](https://api.vrchat.cloud/api/1/config) 的 `availableLanguageCodes`；SDK 3.10.5 ClientSim `ClientSimSettings.cs` | 2026-10-24 读取 | 语言代码表（`zh-CN` 简体，`zh-HK` 繁体） |

X 帖子是通过 fxtwitter 的公开接口读的，帖子的原地址照列。
