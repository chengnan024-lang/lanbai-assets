# 第 8 幕 · 暮 → 蓝时（Act08_Dusk）· 给 Unity 一侧的说明

写的人：云端会话「云」（分支 `pkg/clouds`），2026-10-24。依据：圣经 v2.1 §6·8、§6·8b、§6.x #25–31、§2.2、§1.8；总导演裁决 D-00、D-09、D-17 #1、D-18、D-21、D-22、D-24、D-25、D-28 #5、D-33 #4 #6 #7a；`Engineering/README_集成.md` §8（main）；`Sea/README_Sea接口.md` §2.4、§2.6、§4、§5；`Sky/SkyPresets.json`、`Sky/FogPresets.json`、`Sky/README_Sky.md` §3.1。
**C# 都没在 Unity 里编译过。** 驱动和搭建脚本过了 Roslyn（和它们依赖的云卡、门、天空代码一起编，0 错、U# lint 干净）。这一包没有新 shader：天花和金点用海的 `Lanbai/Sea`、`Lanbai/SeaSpecks`，云用 `Lanbai/CloudCard`，天用 `Lanbai/Sky`。第一次在 Unity 里跑，请把 Console 原样推到 `FromLocal/act08_test/`。

## 0. 先做什么

1. **导入顺序**：`Common/` → `GateClouds/`（搭建脚本借它的 `LanbaiGateCloudsBuilder`）→ `Sky/`（跑 `蓝白/Sky/Build Sky`：场景里要有 `dusk_8i`、`dusk_8ii`、`blue_hour` 三个 `LanbaiSkyPreset`）→ `Sea/`（跑 `蓝白/Sea/Create Materials`：要有 `M_08_SeaCeiling`、`M_08_SeaCeilingEdge`、`M_08_SeaCeilingFade`；`Models/Sea_Ceiling.fbx`；`Textures/Cube_DuskLower_256.exr`）→ `Clouds_v2/`（暮组的卡：渲完、解完颜色以后，跑 `蓝白/Clouds v2/Build Materials`）→ 最后 `Act08_Dusk/`。
2. 菜单 **蓝白/Build/Act08**：搭 `R_Dusk`（海之天花、宫殿金点、上下两组云卡、wisp）和 `Act08_Driver`（在 `Director` 下，有的话）。可以重复运行；驱动物体保留（分发层的引用、`worldSun`、两个接管开关不丢）。
3. 接管开关（`README_集成.md` §8.2、§8.3）：`Act08_Driver.writeRenderSettings`、`writeMainLight` 打勾，同时 `LB_Journey` 的 `extAtmosphere`、`extSun` 填 **922.36 → 1149.31**（主光和环境光到 F16 都归第 8 幕：第 9 幕不写，靠这里留下的值；圣经 9a 的“Trilight 落到近零”也在这里做）。
4. 分发层把 `LanbaiGrade(t)` 加进 `gradeDEV`（出海的曝光线，§4）。**不要再在 `ApplyGrades` 里另写出海的 EXPO_DOWN / EXPO_UP**，不然算两次。
5. 请截图（ARGBHalf → PPv2 → 8 位，CONTROL §6 #10），推到 `FromLocal/act08_test/`：
   | t | 机位 | 看什么 |
   |---|---|---|
   | **921.0 和 923.0** | 正前 | **标定出海的钉住量**（圣经：用 7c 末与 8 开头两张正前方截图）：923 的 APL 应该 ≈ 921 的（34）。不对的话改 `Act08_Grade.json` 的 `pin_dev` 再重跑 `act08_grade.py` |
   | 929.11 | 正前 | F9 日刃：日盘露出一半 |
   | 940.36 | 正前、车门、抬头 | 论点之帧：头顶是海、近地平变玫瑰金镜、眼高一条 3° 的天缝 |
   | 958.0 | 正前、抬头 | 天花在溶化（从地平线往天顶） |
   | 971.4 / 976.4 | 正前、车门 | 8-ii，庄子 L1 / L3（车门方向要干净） |
   | 995.0 | 正前 | 蓝时 |
   以及 921 → 936、955 → 968、986 → 1002 各录一段 60 fps（`flashcheck.py`）；VR 下抬头量 APL（D-09 ≤ 150，`paz672` 车壳到了复量）。

## 1. 文件

| 文件 | 是什么 |
|---|---|
| `Act08_Layout.json` | **唯一的数据源**（`Source/act08_layout.py` 生成，别手改）：时刻、运动 h(t)、日盘露出表、天花、金点、云卡与 wisp、天的时间表、雾、光、Trilight、出海曝光线 |
| `Act08_Grade.json` | 出海的曝光线（`Source/act08_grade.py` 在参考帧上量出来的；layout 把它并进去） |
| `Runtime/LanbaiAct08Driver.cs` | U# 驱动（§2） |
| `Editor/LanbaiAct08Builder.cs` | 菜单 蓝白/Build/Act08 |
| `Source/act08_ref.py` | 参考帧（天空会话的三个预设 + 天花的替身 + 云卡 + 车壳 + 雾，按 S7b → S8 → S8b 调色 + ΔEV） |
| `Source/act08_flash.py` | 出海、溶化、F12 三段的爬升律 / 闪烁核查 |
| `Tools~/sky_equirect.py` | 用天空会话的 CPU 版 `Lanbai/Sky` 把预设渲成等距柱状图（8-ii 带 10° 日线） |
| `Docs~/` | 参考帧、量数、核查、评审 |

## 2. 时间与写的人（`README_集成.md` §8；D-22：同一时刻一个写的人，只交还自己的量）

| t | 发生什么 | 驱动写什么 |
|---|---|---|
| **922.36** 出海 | 车从海的底面掉出去；海交还（`Underwater` 0、焦散 0、cookie 摘掉），雾不清零 | `dusk_8i.Apply()`（天雾组 + 月 + 星全写）；`_Udon_Fog` 水 0.006 → 空气 0.00015（8 s smoothstep）；主光转成暮日（方位 0°、仰角 +0.5°、`#FFA642`、**E 2.2**：D-00，圣经表里的 1.43 是作废的 gamma 值）× 日盘露出比例；Trilight 8-i（天 `#1C3350`、赤道 `#D08A70`、地 `#4C5577`）；天花 `_Udon_SeaLevel` = 1.70 + h、`SeaMode` 3、`SeaClock`、`ReflCube`；`LanbaiGrade` 钉住 |
| 922.36 → 935.36 | 下落 1.5 → 12 m/s | R_Dusk.y = h(t)（天花在车上方后退） |
| ≈927.0 → 930.8 | 日盘从天花的远边下面露出（F9 929.06 露出一半：日刃） | 主光 × 露出比例（表，0.1 s） |
| 929.11 F9 | 曝光的峰 +0.65 EV（场景 + 0.5 EV） | `LanbaiGrade` → 933.11 线性回 0 |
| 940.36 F9b | 论点之帧，天缝 3.1° | — |
| 942.26 F10 | 翼托住：−12 → +3 m/s（20 s） | — |
| 950.36 → 956.36 | wisp 淡掉（变形开始后不再经过） | 卡 `_Alpha` |
| **956.36 F10e** | 唯一的变形：天花溶化（前沿 4 s、每像素 5 s EV 线性，金点最后走）；另一片天 | 内盘换 `M_08_SeaCeilingFade`；`_DissolveTime` = t − 956.36（内盘、边、金点）；`dusk_8i.ApplyBlend(dusk_8ii, smoothstep)` 8 s；雾 → 0.00025；日线 0 → ±10°（`_Udon_SunDisc.z`）；Trilight 天 → `#465582`；上方组的近卡和下方组（另一片天的云，× 0.82、染 (0.92, 0.95, 1.05)）淡入 |
| 965.36 | 天顶最后一块水散尽 | 天花和金点的 renderer 关掉，`SeaMode` 0（自己的量） |
| 964.36 → 987.06 | 8-ii，+3 m/s 匀速上升；庄子 971.4 / 976.4（诗的驱动画） | `dusk_8ii.Apply()` 一次 |
| **987.06 F12** | 日线 6 s 收成一点并熄灭；上升 8 s 收住 | `dusk_8ii.ApplyBlend(blue_hour)` 6 s；日线 ±10° → 0、增益 → 0；主光 × (1 → 0)（地板 0.001）；雾 0.00025 → 0（线性，**1001.21 到 0**）；Trilight → 8b（8 s）；卡的颜色 → 蓝时（没有日光） |
| 993.06 → 1001.21 | 蓝时 | `blue_hour.Apply()` 一次 |
| **1001.21** | 第 9 幕起点 | **不再调 `Apply` / `ApplyBlend`**、不再写天雾组；主光 0.001、RenderSettings 和卡还在这里写 |
| 1001.21 → 1009.21 | 9a 变暗 | Trilight EV 线性落到 × 0.03；卡 EV 线性暗 6 EV，1009.21 关掉 |
| 1149.31 | 窗口关 | — |

**D-33 #6（从 t 单独重建）**：激活那一帧（`LanbaiActivate(true)`）清掉“已应用”的标记，下一帧按 t 全部重写：先 `Apply()` 当前段的预设（在混合段里先 `Apply()` 起点那一个，再 `ApplyBlend`），再写雾、日线、主光、Trilight、天花（材质、`_DissolveTime`、`SeaLevel`）、云卡；往回拖超过 0.25 s 也一样。

**不写的**：PPv2（`LB_Journey.ApplyGrades`）；车厢（侵蚀、窗帘成翼、**门组的侵蚀偏置**：D-33 #7a 归车厢驱动）；诗（`LanbaiPoemDriver`）；第 9 幕的第一批星。

## 3. 画面里的东西

| 量 | 值 | 来源 |
|---|---|---|
| 运动 | h(t)：出海 0 → F9 24.3 → F9b 147.8 → F10e **271.7（最低，956.52 速度过零）** → F11 238.0 → F12 186.1 → 1001.21 174.1 m；峰值加速度 1.21 m/s² | 圣经（`dusk_motion_final.json` 不在仓库，按圣经的数重建，逐拍对得上） |
| 太阳 | 方位 0°、仰角 +0.5°、日盘直径 0.53°（D-18） | 圣经、天空预设 |
| 日盘露出 | 按天花 2.7 km 软边（2.3 → 3.1 km）算日盘露出的面积：**927.0 第一道金线、929.06 一半（= F9 日刃）、930.8 全露** | 几何（圣经按 0.9° 的日盘写 923.9 → 932.0） |
| 天花 | `Sea_Ceiling.fbx`，R_Dusk 局部 y = 1.70（出海平面），海的材质原样 | `README_Sea接口` §2.4、§4 |
| 金点 | 25 个，天花上方 40–200 m、半径 2 km 内，S8 金 (1.566, 0.616, 0.226)、flux ×12，`_CeilingMode` 1、队列 2995；网格按 `Lanbai/SeaSpecks` 的约定生成 | `README_Sea接口` §2.6 |
| 上方组云卡 | 11 张（暮组 `duskU`：Cumulus、Bank、Strato），600 m–11 km；9 张从出海就在（只在天缝里露出来），2 张近的（900 m、1.2 km）8-ii 才淡入；+3 m/s 上升时最快 0.19°/s（≤ 0.29°/s） | 圣经 |
| 下方组云卡 | 7 张（`duskD`：Congestus、Cumulus、Puff、Strato；**另一些云**），数量 ≈ 上方的 70 %，× 0.82、染 (0.92, 0.95, 1.05)，8-ii 淡入 | 圣经 |
| wisp | 4 缕（`CloudV2_Wisp_duskU`），侧窗方向（方位 −95、−70、+100、+125）、450–560 m、出海平面下 40–150 m，沿切向 4–5 m/s 漂过；950.36 → 956.36 淡掉 | 圣经 |
| 禁区 | 日线（方位 ±15°、仰角 ±3°）和庄子块及其镜像（方位 +18 … +52°、仰角 ±8°）里**没有云卡、没有 wisp** | D-33 #7a；圣经“任何东西穿过日线” |
| 雾 | 出海 0.006 → 0.00015（8 s）；8-ii 0.00025；F12 起线性，**1001.21 到 0**（圣经写 30 s 到 1017.06，跨过了 1001.21：第 9 幕在 1001.21 写 0、`blue_hour` 的密度也是 0，一个写的人，所以在这里收到 0） | `FogPresets.json`；集成 §8.1 |
| 日线 | `_Udon_SunDisc.z`：F10e 起 8 s 长到 ±10°（太阳和它的另一个自己熔成一条线），F12 6 s 收回、增益 → 0 | 圣经 §6·8b；`dusk_8ii` 把 `_Udon_SunDisc` 列在 blendSkip 里：一个名字一个写的人 |
| 云卡颜色 | 暮组按 D-25 重解（`Clouds_v2/Textures/cards_v2.json` colours.duskU / duskD；目标云影 `#363D59`）；蓝时：没有日光，天光 / 地光 = `blue_hour` 天顶 / 天底 × 6 | D-25 |

## 4. 出海的曝光线（`LanbaiGrade`）

圣经：“这条线写的是‘场景 + 曝光’的总亮度”。`Source/act08_grade.py` 在参考帧（正前、`bible_v2` 车壳、S7b → S8 调色 + bloom）上量：
1. 出海那一帧压到 **APL 34**（7c 末）：要 ΔEV **−3.92**（圣经的仿真是 2.43 EV、w 0.68；参考帧的天比圣经仿真亮，所以钉得更多）。
2. 总亮度 EV 线性放开 6.75 s，F9 顶到“场景 + 0.5 EV”：ΔEV **+0.65**。
3. 4 s 线性回 0（933.11）。
放开的速度约 0.68 EV/s（2 秒窗 1.36 EV，限 1.8）。**实机要标定**：§0 第 5 条。

## 5. 参考帧与量数

（见下一节的表；暮组卡还在渲，参考帧里先用晨组同形状的卡当替身，颜色是暮的设计值，json 的 `cards_standin` 列出来了）

## 6. 已知弱点（诚实版）

- **暮组的云卡还没渲完、颜色没解**：参考帧里的云是替身（形状对、光的方向是晨的 6° 不是暮的 1°）。卡渲完以后：`card_solve.py` 解 duskU / duskD 的颜色（D-25）→ 重出参考帧。
- **天花是替身**：参考帧里按 `Lanbai/Sea` CEILING 的算术画（菲涅耳 2 % → 掠射 60 %、玫瑰金镜 × (1.25, 1.3, 1.25) × 1.5、2.7 km 软边、溶化的进度公式），反射用暮天的下半球（= `ReflCube_DuskLower` 该有的内容），**没有法线扰动、没有海的紫色护栏**（D-17 / D-21 的两段 LUT 在海的 shader 里，参考帧没有）：所以紫的占比另给一个“不算天花”的数。
- **正式的 `ReflCube_DuskLower` 没烘**：驱动先用海包里的 `Cube_DuskLower_256.exr`（退路）。
- **车壳**：`bible_v2` 角度窗；车顶和上墙按侵蚀从仰角 60° 打开到 962.26 时的 +12°（近似车厢驱动的侵蚀）。`paz672` 到了复量 D-09。
- **日线是两条平行的线**：天空的 `_Udon_SunDisc.z` 在太阳和它的镜像（仰角 ±0.5°）上各画一条，中间隔 1°，看起来是“=”而不是“熔成一条线”。这是天空 shader 的画法，我只写长度；要一条就请天空改（`给总控.md`）。
- **暮 HDRI 太阳右边的亮度边**（天空会话的已知弱点）在 8-i 的参考帧里看得见：日的右边地平线上一段暗带。
