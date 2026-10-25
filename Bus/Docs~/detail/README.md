# 车的零件：对照板、中性光、头部微动、盲测（D-36 / D-40 / D-40a / D-40b）

这个文件夹放车的每个零件的对照板和细节表：

- `<零件>/compare.png`：对照板（`Bus/Source/parts/compare.py` 出）；
- `<零件>/details.json`：这个零件做了哪些细节、真实尺寸、从主座位看的视距（现在有 `seat`、`window`、`poles`）。

工具都在 `Bus/Source/parts/`：`qa.py`（中性光、头部微动）、`compare.py`（对照板）、`blind.py`（盲测图）。

**先说清楚：这些工具全是 Blender 和 Python 层的。没有一样在 Unity 里编译、运行过，也没有在头显里看过。**
三层验收分开记（D-40a #4）：Blender 离线 / Unity 桌面 / VR 头显。这里的数只代表 Blender 离线那一层；
Unity 桌面那一层以总工程师的测试工具（`Engineering/UnityTest`，`LanbaiTestCapture`）出的结果为准，头显那一层由人看。

照片的署名和授权见 [`署名与授权.md`](署名与授权.md)（另一个会话写的总表）；每张照片的作者和授权也在它旁边的
`sources.json` 里，对照板和盲测图都从那里读。

---

## 1. 中性光（D-40 #2）：`qa.py --mode neutral`

```
~/bpy/bin/python Bus/Source/parts/qa.py --mode neutral --part poles
   [--views aisle_2m,flange_0.8m] [--samples 64] [--cal-samples 24] [--res-pct 100] [--env 1.0] [--flat]
```

- 只留零件自己的物体（车壳、顶棚、地板、玻璃、灯都拿掉），放在一块 18% 灰的地上，四周是均匀的白环境光
  （一个常数颜色，没有 HDRI 图）。没有车厢管灯，没有太阳。
- 不调色：Standard 视图变换、Look None。
- 机位和 `preview.py` 的 `PARTS` 完全一样（1280 × 720、水平 64°，约 20 px/°）。
- 每张图左下角有一张 18% 灰卡和一张 90% 白卡。它们只给相机看：不投影、不进反射，不影响零件的光。
- 曝光按灰卡定：先只渲灰卡那一小块（低采样），量出读数，算出 EV，让灰卡读 sRGB 118；再渲正图。
- 材质用定稿的那套（`materials.apply_details`，和 `preview.py` 一样）；`--flat` 只用 `MAT_TABLE` 的底色。
- 渲染器 Cycles（CPU、降噪）。
- 出 `/tmp/bus/parts/<零件>_<机位>_neutral.png`，和 `<零件>_neutral.json`。

JSON 里每张图记：

| 字段 | 意思 |
|---|---|
| `exposure_ev` | 灰卡定出来的曝光 |
| `grey_card_rgb_luma` | 正图里灰卡的读数（R、G、B、亮度）。应当在 118 上下 |
| `white_card_rgb_luma` | 白卡的读数（90% 反照率，约 243） |
| `part_materials` | 这个零件身上有哪些材质（这张图要认出来的就是它们） |

这张图要回答的只有一件事：**不靠灯光和调色，认不认得出是乙烯、搪瓷漆、阳极铝、橡胶、漆过的钢管。**
认不出来，就是材质的问题，不许靠灯光救（D-40 #2）。认不认得出由人看图判，JSON 只记条件。

## 2. 头部微动（D-40a #5）：`qa.py --mode flicker`

```
~/bpy/bin/python Bus/Source/parts/qa.py --mode flicker --part poles --view aisle_2m
~/bpy/bin/python Bus/Source/parts/qa.py --mode flicker --part poles --view slice:pillar_10m [--ref-samples 8]
   [--frames 90] [--fps 90] [--amp-cm 2] [--amp-deg 1] [--crop 32,24] [--ppd 20]
   [--detail-normals vinyl|none] [--tube-spec K] [--no-probe] [--shadows] [--engine eevee|workbench|cycles_point]
```

**这是 Blender 里的近似，不是 Unity 的测量。Unity 层的结果以总工程师测试工具出的为准。**

怎么渲（总导演 10-25 改过：不用 Workbench，Workbench 没有 PBR 高光，看不出要找的高光闪烁）：

- EEVEE，Render Samples = 1（`scene.eevee.taa_render_samples = 1`）：不做 TAA 累积，一个像素一个采样点，
  最接近 Unity 不开 MSAA 的一帧。实测：1 个采样时，采样点在像素中心。
- 90 帧、90 fps。头部按总工程师 Unity 工具同一条运动走：±2 cm、±1°，两个正弦叠加，平滑，每次跑都一样。
- 20 px/°。
  - 用 preview 的机位时：以 target 为中心裁 32 × 24°，按 Unity 工具的 ppd 公式是 657 × 487。
  - 用 `slice:<seat_05m|seat_10m|window_05m|window_10m|pillar_05m|pillar_10m>` 时：照 `bus_slice.json` 的机位，
    看切片物体包围盒的中心，朝主座位的眼退 0.5 / 1.0 m，40 × 30°，834 × 614。场景里只有切片的三件。
- 材质用 Lanbai/Cabin 的数（圣经 §4.2 = `build_bus.MAT_TABLE`）：
  - Roughness = 1 − 光滑度，Metallic 和底色照表；
  - 立柱、顶杆（Steel）加 Lanbai/Cabin 的握手带：y 1.62–2.42 光滑度 0.80；
  - 法线：几何法线。`--detail-normals vinyl`（默认）给乙烯加 Unity 同一张皮纹法线（0.35，30 cm 一格）；
    `none` 一张都不加。
  - 不用 `apply_details` 的程序化旧化。
- 光：
  - 10 根管灯，照 `bake_lightmap.py` 烘光照图时的样子摆，功率取它标定出来的那个（`bake_report.json`）。
  - 管灯在金属里的亮度缩到和 Unity 管灯罩的自发光一样（亮度约 1.94）。
  - preview 机位加一个球形反射探针（256 / 面），金属里映出亮着的车厢。
  - 阴影默认关：EEVEE 的软阴影在 1 个采样时每帧都是新的噪点，会被当成闪烁。关掉以后头不动，连续几帧逐像素相同（试了 4 帧，hf = 0）。

和 Unity 不一样的地方（所以数只能拿来找“哪里会闪”，不能拿来判过没过）：

- 没有 Lanbai/Cabin 的几何高光抗锯齿（D-40 #4）。Blender 的节点拿不到 ddx / ddy，所以金属上的数应当比 Unity 的差。
- 没有零件图集的法线 / 遮罩，没有 mip，没有贴图压缩。
- 漫射只有面光的直射：Unity 的光照图带反弹和 AO，所以这里暗处更暗。
- 没有 PPv2 调色。

量的数照抄 `origin/pkg/engineering:Engineering/UnityTest/Editor/LanbaiTestCapture.cs`（ee337a1），行号写在 `qa.py` 里。
每个像素的亮度 Y = 0.2126 R + 0.7152 G + 0.0722 B（8 位 sRGB，0–255）。

| 数 | 意思 |
|---|---|
| `std_mean` / `std_p99` | 每个像素亮度随时间的标准差，全画面平均 / 第 99 百分位。含真实运动带来的变化 |
| `hf_mean` / `hf_p99` | 每个像素二阶时间差分的均方根 ÷ √6。平滑的运动几乎不算，来回跳的闪烁 / 爬动才算 |
| `hf_frac` | hf > 6（`--hf-threshold`）的像素占比。总工程师的初值：立柱、侧窗 ≤ 0.005（不卡门，切片实测后再定） |
| `apl_min` / `apl_max` / `apl_max_step` | 每帧平均亮度的最小、最大，和相邻两帧的最大跳变 |
| `heat_flicker` / `heat_std` | 热图：hf / std 从 0 到 24，黑 → 紫 → 红 → 橙 → 浅黄；很小的地方显示平均画面的暗灰 |

读数时要知道：头这样动，近处的边每帧会移 2–5 个像素。一条硬边一帧就扫过一个像素，在 hf 里也算“跳”。
所以有近处高反差物体的画面，`hf_frac` 天然就大（比如 `poles aisle_2m` 是 0.43）。热图上，**顺着运动方向的一条条宽带**
是边扫过去，**面里面的碎点、碎线**才是高光闪烁或锯齿。只拿同一个机位前后两次的数比，不拿不同机位的数比。

`--ref-samples N` 是只在 Blender 里有的辅助，不是 Unity 工具的量：

- 同一条运动再渲一遍 N 个采样（抗锯齿），当作“平滑的信号”。
- `excess = max(0, hf − hf_ref)`。扫过去的边两遍都有，被减掉；剩下的近似是锯齿和高光闪烁本身。
- 出 `..._flicker_heat_excess.png`；JSON 里在 `blender_only` 下面。
- 时间大约翻 3 倍。

出 `/tmp/bus/parts/<零件>_<机位>_flicker.json`、`..._flicker_heat.png`、`..._flicker_heat_std.png`、
`..._flicker_f000.png`（第一帧）。

其他引擎（都不是默认）：

- `--engine workbench`：旧路线，**不看高光**，只能看几何边缘的爬动。
- `--engine cycles_point`：没有 libEGL 时的备用，数不能和 EEVEE 的比。

EEVEE 在没有显示器的机器上要 libEGL（`apt install libegl1 libegl-mesa0`，Mesa llvmpipe 就行；`EGL_BAD_MATCH` 的警告不碍事）。
退出码：0 成功；2 参数不对；3 没有 EGL；4 零件搭不起来。

**别的会话正在改 `seat.py` / `common.py` / `materials.py` / `build_bus.py` 的时候**，先拷一份提交过的源码再跑：

```
git archive HEAD Bus/Source Bus/Textures | tar -x -C /tmp/snap
LANBAI_BUS_SRC=/tmp/snap/Bus/Source ~/bpy/bin/python Bus/Source/parts/qa.py --mode ...
```

## 3. 对照板（D-40 #1、D-40a #4 / #6、D-40b #2）：`compare.py`

```
python3 Bus/Source/parts/compare.py --part poles \
    --photos 照片1.jpg,照片2.jpg \
    --neutral /tmp/bus/parts/poles_aisle_2m_neutral.png,... \
    --final /tmp/bus/parts/poles_aisle_2m_day.png,... \
    [--unity 截图1.png,,截图3.png] [--headset 一句话1.txt,,] \
    [--status blender=通过,unity=未测,vr=未测] [--details ...json] [--title "..."] [--out ...png]
```

- 旧的用法照样能跑（`--part --renders --photos --title`）：`--renders` 进“Blender 定稿”那一栏。
- 出 `Bus/Docs~/detail/<零件>/compare.png`。

板上有三块。

**五栏**，一行一个机位，各栏的文件按行对齐（逗号分开；两个逗号中间空着，就是那一行没有）：

| 真车照片 | Blender 中性光 | Blender 定稿 | Unity 截图 | 头显一句话 |
|---|---|---|---|---|

- Unity 截图、头显一句话没给文件，就是一个写着“未测”的空框。后两栏空着 = 没验过，不是过了。
- 头显一句话可以是 `.txt` / `.md`（里面那一句印在框里），也可以是一张图。
- 每张照片下面一行署名（作者 · 授权），从照片所在的文件夹往上找 `sources.json`；找不到就写“没找到 sources.json（要补）”。

**三层状态**：Blender 离线 / Unity 桌面 / VR 头显，每层取 未测 / 通过 / 不通过 / 测不了。

- 默认全是“未测”。
- Unity 桌面没给截图、VR 头显没给那一句时，写了“通过”也记成“未测”，板上注明。
- Unity 的“通过”要总导演看过图才记（D-41 #4）。

**细节表**（读 `details.json`）：每处细节算“角像素 = 尺寸 ÷ 视距（弧度）× 180/π × 像素密度”，≥ 2 px 记“看得出”。

- 视距是一个范围时，近端、远端都算：
  - 两端都够：“看得出”；
  - 只有近端够：“近看得出”；
  - 都不够：“看不出”。
- 判定按 Index 约 20 px/°（D-40a #6）。
- 14 px/° 那一栏是显示面板的密度，只作参考，不判过不过（D-40b #2）。

看不出的细节，不靠加面数、提分辨率去救，把预算挪到看得见的地方（D-40a #6）；小于约 3 mm 的进法线贴图（账本）。

## 4. 细节表 `details.json`

每一条：`name`（细节）、`size_mm` 和 `size_of`（量的是哪个尺寸）、`distance_m`（[近, 远]，米）、`where`（从主座位看是哪一件）、
`modelled`（几何 / 法线 / 还没做）。

- `poles`、`window` 的尺寸取自提交过的 `poles.py`、`window.py`（1e9cafa）；视距按 `bus_spec` 的位置，从主座位的眼
  (0.55, 1.70, 2.05) 算。
- `seat` 按总导演 10-25 给的 672M 座椅事实写（`实物参考_PAZ细节/README.md` §6.1，Kolesa 1989 年的 672M）。
  座椅正在照这些事实重做，重做提交后按新代码的数对一遍。
  - 视距：前排靠背 0.6–0.8 m，自己的座垫 0.5–0.9 m，管套 0.5–0.7 m。
  - 标“约”的是估的。
  - 管子和背板的颜色按圣经座椅框那一行 `#3C3E3D`，总导演另有裁决就照裁决。trolleway 那辆的颜色不照搬。

## 5. 盲测图（D-40 #5、D-40a #2）：`blind.py`

```
python3 Bus/Source/parts/blind.py --set <名字> --photos a.jpg@0.6,0.45,0.9,b.jpg --renders r.png@0.5,0.5,1 [--seed 7]
python3 Bus/Source/parts/blind.py --demo
```

**盲测是找问题的工具，不是合格线**（D-40a #2）：挑出来的地方进下一轮的修改清单，不判过不过。

- 输入：真车照片的局部和渲染的局部，混在一起。
- 处理：所有图同一种处理。
  - 9:16 竖裁，先缩到同一个工作尺寸 540 × 960，再放到 1080 × 1920，照片和渲染的清晰度拉平；
  - 只要有一张照片是黑白的，就全部转灰；
  - 统一存 JPEG，没有标签、没有 EXIF；
  - 顺序按 `--seed` 洗过。
- 输出：`Bus/Docs~/盲测/<名字>/01.jpg …`，答案另存 `答案.json`（每张是照片还是渲染、出处、裁的位置、照片的作者和授权）。
  看图的人先别开答案。
- `ref_only/` 里的照片不拿来做盲测图（D-41 #7）。
- `--demo` 用仓库里现成的文件出一组示例（`Bus/Docs~/盲测/示例_车厢局部`）：
  - 渲染：`Bus/Docs~/parts/*/` 里 10-24 的近景；
  - 照片：trolleway 的 CC BY 2.0 照片（Artem Svetlov），裁过、缩放过；
  - 那辆车多半是 672，座椅重包过红色，颜色本身就会露馅。这一组只演示工具怎么用，不拿来下结论。
