# 蓝白 · 天空（`Lanbai/Sky`、真实星表的星、月、银河、每一幕的天空预设）v1

写的人：云端子会话「天空」，2026-10-23。**没在 Unity 里编译过**：shader 只用 slang 查过语法和类型，C# 只用 Roslyn 对 Unity 2021.1 的引用程序集查过类型（§9）。参考图是用 slang 在 CPU 上**直接跑这里的 shader 代码**渲出来、再按调色套件的引擎参数调色的（§7），所以本地截图可以和它逐项对照。
雾与天的共用接口见 `Sky/README_Fog接口.md`（`Common/Shaders/LanbaiFog.cginc`、`LanbaiSky.cginc`）。

---

## 0. 拷什么、点什么

1. 拷 `Common/`（`Assets/Lanbai/Common/`）和 `Sky/`（`Assets/Lanbai/Sky/`）。`Tools~`、`Docs~`、`Source~` 以 `~` 结尾，Unity 不会导入。
2. 晨 / 暮的 HDRI（本地已经下载的 `syferfontein_6d_clear_puresky`、`syferfontein_0d_clear_puresky`，16K 的 `.hdr`）：放在工程任意位置，导入设置 **Texture Shape = Cube、Mapping = Latitude-Longitude Layout、BC6H、不 crunch**。
3. 菜单 **`蓝白/Sky/Build Star Mesh`** → `Sky/Generated/StarPoints_BSC5.asset`。
4. 菜单 **`蓝白/Sky/Build Preset Materials`** → `Sky/Generated/M_Sky_<预设>.mat` 七个 + `M_Sky_StarPoints.mat`。它会**在 16K 原图上重新量太阳**并改 `_RotationA`（报告 `Sky/Generated/SkyBuild_Report.txt` 里写着量到的方位 / 仰角，实时平行光照这个对齐）。
5. 菜单 **`蓝白/Sky/Create Preset Objects`** → 场景里 `Lanbai_SkyPresets` 下每个预设一个物体（U# `LanbaiSkyPreset`，并自动建它的程序资产）。各幕的驱动调 `Apply()` / `ApplyBlend()`。
6. 菜单 **`蓝白/Sky/Preview Window`**：在编辑器里点一个预设就换上天空盒、写好全局量和雾密度（只在编辑模式里有效，进 Play 会丢，见坑 9）。
7. 星：场景里建一个空物体，挂 MeshFilter = `StarPoints_BSC5.asset`、MeshRenderer = `M_Sky_StarPoints.mat`（关阴影、关光照探针）。位置无所谓（shader 不用物体变换）。

**请推回来的截图**（桌面 1920×1080、水平 90°、主座位眼位 `cameras.U7` (0.55, 1.70, 2.05)，PPv2 开，渲进 ARGBHalf 再调色）：在一个空场景里（只有天空盒 + 星，没有车）每个预设截“前方 / 车门 +45° / 天窗仰 70° / 背后”四张，和 `Sky/Docs~/presets/preset_<预设>.png` 对照；另外 Console 原样。

---

## 1. 文件

| 路径 | 是什么 |
|---|---|
| `Shaders/Lanbai_Sky.shader` + `LanbaiSkyLayers.cginc` | 天空盒 `Lanbai/Sky`（§2）。逻辑全在 `.cginc` 里，CPU 参考渲染跑的就是它 |
| `Shaders/Lanbai_StarPoints.shader` | 星点 `Lanbai/StarPoints`：每颗星一个高斯精灵（§4） |
| `Textures/StarSky_Glow_4096x2048.exr` | 银河辉光（世界坐标的经纬图、线性、半浮点、**没有星**）（§4） |
| `Textures/Sky_Overcast_Night_2048x1024.hdr`、`..._TownGlow_...hdr` | 阴云夜（第 1、2、11、12 幕）；带“镇子方向钠光照亮的云底”的变体 |
| `Textures/Moon_Disc_1024.png` | 月面圆盘（NASA 照片，去饱和 70%，alpha = 圆盘） |
| `Data/StarPoints_BSC5.csv` | 8 404 颗星（Yale BSC，≤ 6.5 等）：Unity 世界方向、星等、B−V、线性颜色、亮度排名 |
| `Data/StarSky.json` | 星空朝向（赤道 → Unity 世界的旋转矩阵）、银心方向、来源 |
| `Data/fit_dawn.json`、`fit_dusk.json` | 晨 / 暮 HDRI 的乘色拟合结果 |
| `SkyPresets.json` | **每一幕的天空预设**（§3）：材质值 + 驱动要写的全局量 + 量出来的数 |
| `Editor/LanbaiSkyImport.cs` | 导入设置（只管 `Sky/Textures/`） |
| `Editor/LanbaiSkyBuild.cs` | 上面 §0 的菜单 |
| `Runtime/LanbaiSkyPreset.cs` | U#：写一组预设的全局量、雾密度、天空盒 |
| `Source~/` | 生成数据的脚本（`make_starsky.py`、`make_overcast_night.py`、`make_moon_disc.py`）和下载的原始数据 |
| `Tools~/render/` | CPU 参考渲染（`shader_cpu.py`、`sky_cpu.py`）、调色（`grade.py`）、乘色拟合（`fit_hdri_tints.py`）、预设生成（`make_presets.py`） |
| `Tools~/compile_check/` | slang / Roslyn 检查、门光带等价核对 |
| `Docs~/presets/preset_*.png` | 每个预设六个视向的参考图（调好色的） |

---

## 2. `Lanbai/Sky` 的层（从下到上，颜色全是线性值，颜色属性故意用 Vector）

1. **两张立方图 A / B**（HDRI）：各自固定的 Y 旋转（`_RotationA/B`，内容的方位 += 这个角；**只在搭建时设，运行时永不旋转**）、EV、钳位（默认 16：HDRI 里的太阳被钳掉，日盘程序化画）、**四个乘色**：天顶、中天、朝日的地平线、背日的地平线（`_TintElevation` = 地平线满到几度 / 中天满在几度 / 天顶满在几度 / 方位权重的幂）。`_Blend` 混合 A → B。
   **地平线以下**换成该方位的地平线色 → `_NadirColor` 的渐变（纯天空 HDRI 的下半球没法用）；`_NadirColor.a` 把渐变中段拉向冷灰（暖 → 靛蓝的中段会经过紫）。
2. **程序化**：`LanbaiHorizon(V)`，**和雾是同一个函数**，所以雾完全吃掉的物体会消失在天里；权重 `_ProcWeight`。
3. **两条地平线带**（`_Band1/2Color/Shape/Gain`）：按仰角和**相对太阳的方位**定位的高斯带，把天拉向某个颜色。晨：地影带 + 很淡的金星带（选定的 HDRI 里没有）；蓝时：最纯的蓝带；第 12 幕：天边那一线。`Color.a` 同样把带的边缘拉向冷灰。
4. **另一片天**（第 8-ii 幕）：地平线以下按 (−x, −y, z) 取样立方图（绕前方轴转 180°，不是翻转）× `_OtherGain`（0.82）× `_OtherTint`，1° 软接缝；**它自己的太阳也画出来**，两个太阳在接缝上熔成一条线。
5. **紫色护栏** `_PurpleGuard`：圣经 §1.3.4（第 4 幕以外紫 ≤ 2%）。偏蓝、红接近绿的天在 S8 的暖调色（色温 +3、色调 +1）下会变成淡紫；护栏在 B/G 高的地方把 R/G 限在 `y` 以下。暖色、玫瑰、真正的蓝不受影响。
6. **夜**：`_NightColor` + 增益 g ×（星空底 `_StarFloorAdd` + 银河辉光 `_GlowTex`）；权重 `_NightBlend` **按方向延迟**（第 8b → 9 幕：背日和天顶先黑，前方 ±40° 的地平线带在 6 秒时仍 ≥ 50%，8 秒全黑；`_NightMaskDir/Shape`）。
7. **日盘 / 日线**（程序化，0.9°，临边昏暗，软边；`_SunShape.w` / `_Udon_SunDisc.z` > 0 时变成水平的“日线”，第 8 幕 F12 的收缩）+ 可选的日晕；**月**（`_MoonTex` 圆盘 + 门的月晕公式）。
8. 抖动（方向锚定、两眼一样，`LanbaiVR.cginc`）。

全局量（都可选；没设就用材质值）：

| 全局量 | 含义 |
|---|---|
| `_Udon_SkyBlend` | x 立方图 A → B、y 程序化权重、z 夜的权重（按方向延迟）；w > 0 = 设了 |
| `_Udon_SkyFx` | x 另一片天、y 地平线带 1 的增益、z 日线的半长（度）；w > 0 = 设了 |
| `_Udon_GalaxyGain` | x 银河辉光与星空底的增益 g(t)（第 9 幕）；w > 0 = 设了 |
| `_Udon_StarGain` | x 星点总增益（F13 那一帧 0 → 1）、y 亮星加成（> 0 = 用它）、z 亮星个数（> 0 = 用它）；w > 0 = 设了 |
| `_Udon_SunDir` / `_Udon_SunDisc` | 指向太阳；x 日盘增益、y 半径（度）、z 日线半长（度）；w > 0 = 设了 |
| `_Udon_MoonDir` / `_Udon_MoonDisc` | 指向月；x 月盘增益、y 半径（度）；w > 0 = 设了 |
| 雾的那一组 | 见 `README_Fog接口.md` §3 |

**给海（ABOVE 模式的倒影太阳）**：太阳方向读 `_Udon_SunDir`（w > 0）。日盘的线性辐亮度 = `_SunColor` × `_Udon_SunDisc.x`（没设时 × `_SunGain`）：**第 6 幕 `#FFCE9E @ +2.55` = 线性 (5.86, 3.62, 2.00)**，半径 0.45°（直径 0.9°），临边昏暗 0.55；第 8 幕 `#FF9167 @ +2.74` = 线性 (6.68, 1.89, 0.92)。海镜里的倒影太阳按圣经要比这个低 ≥ 1.3 EV。

---

## 3. 每一幕的天空预设（`SkyPresets.json`，由 `Tools~/render/make_presets.py` 生成）

| 预设 | 幕 | 调色 | 天 | 雾色 |
|---|---|---|---|---|
| `overcast_rain_night` | 1、2（−0.7 EV）、11、12 开头 | S1 | `Sky_Overcast_Night`：天顶 `#070B14`（填 `#09080D`），地平线 = 雾 `#121A28`（填 `#161B27`） | 模型 B，几乎一色 |
| `moon_night` | 3 | S3 | 程序化：天顶 `#08101F`、背月地平线 `#111B30`、月 −12° / +8°、直径 1.2°、月晕 | 模型 B，朝月一侧亮 |
| `dawn` | 6 | S6 | `syferfontein_6d`，太阳方位 +45° 仰角 5.8°；天顶 `#3E64A6`、背日 45° `#AFC4E0`（拟合到 `#9FBDDB`）、日侧地平线 `#F2C79A`、地影带 + 很淡的金星带、日盘 `#FFF3DE` | 模型 B，从这片天的 1° 仰角取样（朝日 / 背日 / 天顶） |
| `dusk_8i` | 8-i | S8 | `syferfontein_0d`，HDRI 的余晖转到方位 0°、日盘程序化在 +0.5°；日带 `#FFB070`、玫瑰带 `#E7A0A0`、中天 `#808AB2`、天顶 `#3D4A80`；紫护栏 | 同上 |
| `dusk_8ii` | 8-ii | S8 | 同上 + 另一片天 = 1 | 同上 |
| `blue_hour` | 8b | S8b | 程序化：地平线 `#6F86B0`、最纯的蓝带 `#2E4F8A`、天顶 `#16223F`、天底 `#1A2A4E`；夜的定向遮罩备好 | 雾密度 0 |
| `star_sea` | 9 | S9a | 夜：`#04060E` → 星空底 `#08112A` + 银河辉光（g = 1 时） | 雾关 |

量出来的数（只有天，没有车、没有云；所以 APL 不能和圣经 §2 的整帧 APL 比）在 `SkyPresets.json` 每个预设的 `measured_views` 里，图在 `Docs~/presets/`。七个预设、六个视向的紫占比（h_ab 290–325、C\* > 15）最大 1.9%（`dusk_8ii` 向下看），其余全是 0。晨另按第 6 幕的严规则（h 285–330、C\* > 12）量：0%。

**第 10 幕（白）不需要天空预设**：白由遮罩球给（`Mirrors/`、`Overlay/`），遮罩后面的一切关闭。

晨、暮、蓝时交给「云」（第 6、8 幕的包），它的驱动在对应时刻调 `LanbaiSkyPreset.Apply()`，或者自己写同样的全局量。**过渡**（暮 → 蓝时的 6 秒、蓝时 → 星海的 8 秒、0 → 1 的另一片天）用 `_Udon_SkyBlend` / `_Udon_SkyFx` 的连续值写，不换材质；换材质（`RenderSettings.skybox`）只在遮挡下。暮与蓝时可以放在**同一个材质**里：`dusk_8ii` 的材质 + `_Udon_SkyBlend.y` 0 → 1 就是“立方图 → 程序化蓝时”。

---

## 4. 星与银河

**星点**：Yale Bright Star Catalogue（第 5 版，公有领域）里 ≤ 6.5 等的 **8 404 颗**（圣经说“约 9 000”，BSC 到 6.5 等就是这么多）。朝向按圣经 §6·9：**银心在方位 −30°、仰角 +12°**，银河从左前方拱过天顶到右后方，再从脚下穿过（地平线以下是同一片星空的另一半，不是倒影）。用的是真正的旋转（赤道坐标 → 东北天，行列式 +1），星座的手性是真的。

**星点网格的顶点格式**（给「镜与白」画镜中的第二遍）：

| 通道 | 内容 |
|---|---|
| `vertex.xyz`（POSITION） | 这颗星的 **Unity 世界单位方向**（四个顶点相同）。物体变换不用 |
| `uv0.xy`（TEXCOORD0） | 四个角 (−1,−1) (1,−1) (1,1) (−1,1) |
| `uv1`（TEXCOORD1，float4） | x = V 星等、y = 亮度排名（0 = 最亮）、z = 顺序 0..1（脚本化出现 / 熄灭用，默认 = 排名 / N）、w = 0 |
| `color`（COLOR） | 线性 rgb，亮度归一为 1（B−V 黑体色，向白收 45%） |
| 三角形 | 每颗星 (0, 2, 1)、(0, 3, 2) |

展开（`Lanbai_StarPoints.shader` 的 vert）：中心 C = 两眼中点 + D × `_Distance`（20 km）；右 R = normalize(cross(up, D))（D 接近竖直时 up 换成 x）、上 U = cross(D, R)；半边长 h = 2 × FWHM 像素 × `LanbaiPixelAngle()` × `_Distance`；P = C + (R·uv0.x + U·uv0.y)·h。亮度 = `_StarScale` × 10^(−0.4 × `_MagSlope` × (m − `_MagRef`))，排名 < 亮星个数的 × 亮星加成，× `_Udon_StarGain.x`，× 顺序遮罩；片元是 exp(−4 ln2 r²)（r 以 FWHM 为单位），叠加混合。镜子在模板里画第二遍时，把 D 换成镜面反射后的方向即可（平面镜：D' = reflect(D, n)；凸 1.5% 的鱼眼在镜子 shader 里做）。

**银河辉光**（`StarSky_Glow_4096x2048.exr`）：**不是 NASA 的星图**（NASA SVS 从云端连不上），是用三份真实数据生成的：J. R. Vieira 的银河轮廓表（5 级亮度，经 d3-celestial 的 `mw.json`，BSD-3）给形状、星云团和暗带；Hipparcos（ESA 1997，经 d3-celestial 的 `stars.14.json`）里 6.5–11 等的暗星给颗粒和宽的盘；银心 ±15° 染成暖尘色。多尺度（3° 的柔光 + 1° 的结构 + 0.25° 的颗粒）。数值是填值：最亮的漫射处 = S9a 填 `#6A758A`（屏幕 `#6F82A0`）、银心暖尘 = 填 `#CBAE82`（屏幕 `#C8B79A`）；星空底 `#0D0F23` 不在图里，`Lanbai/Sky` 加。
映射（`LanbaiSky.cginc` 的 `LanbaiGalaxyUV`）：u = 0.5 + atan2(V.x, V.z) / 2π，v = 0.5 + asin(V.y) / π；不用 mip（圣经：任何模糊都不要）。

**第 9 幕的全局量**（镜子读的）：`_Udon_GalaxyGain.x` = 银河辉光 + 星空底的增益（点燃的 g(t)，之后 x^2.5 曲线上 1.0 → 1.8）；`_Udon_StarGain.x` = 星点总增益（F13 一帧 0 → 1），`.y` = 亮星加成（×4 → ×8），`.z` = 亮星个数（50 → 200）；`_Udon_ZenithColor.rgb` = **当前的星空底**（= `_NightColor` + g × `_StarFloorAdd`，第 9 幕的驱动每帧写；雾是关的，所以它在 `LanbaiHorizon` 里也不会造成别的影响）。所以镜子反射的天 = `_Udon_ZenithColor` + `_Udon_GalaxyGain.x` × 辉光图（`LanbaiGalaxyUV(反射方向)`，材质上赋同一张 `StarSky_Glow`）+ 星点第二遍。（`_CubeB` 在 `Lanbai/Sky` 里是第二张 HDRI，不是银河。）

---

## 5. 月、阴云夜

- 月面：NASA 阿波罗 11 号拍的满月（AS11-44-6667，`github.com/nasa/NASA-3D-Resources` 的 `Moon.jpg`，NASA 媒体无版权）。圣经点名的 CGI Moon Kit 连不上，这张是真的满月照片，1.2° 的圆盘用它足够。去饱和 70%，最亮的高地 ≈ 0.95，亮度由 `_MoonColor`（S3 填 `#F0F5FF @ +1.67`）定。
- 阴云夜：程序化的低对比层积云底（1.2 km 高的云面上做分形噪声，所以往地平线方向自然压扁），±7% 的明暗；值是 S1 的填值（天顶 `#09080D`、地平线 = 雾 `#161B27`）。第 2 / 11 幕在 S2 下 −0.7 EV。带镇子钠光的变体：钠光在方位 0°，`_RotationA` 转到镇子的方位。

---

## 6. 晨 / 暮 HDRI 的乘色是怎么来的

`Tools~/render/fit_hdri_tints.py`：在 CPU 上跑真的 `LanbaiSkyLayers.cginc`，对几个区域的平均色做最小二乘，目标是调色之后的屏幕值（引擎求逆得到填值）。
- 晨（S6）：天顶 `#3E64A6` ✓、日侧地平线 `#F2C79A` ✓、背日 45° `#AFC4E0`（得 `#9FBDDB`，差 ~10 码：天顶和背日 45° 在这张 HDRI 里亮度差不够大，再拉就会把背日的中天推到发白）；另外加了三个圣经没写数的约束让画面干净：日上方 25–35° 淡蓝 `#B4C6D8`（不许发紫红）、日侧 10–16° 暖珍珠白、侧窗 10–20° 淡蓝。
- 暮（S8）：天顶 `#3D4A80` ✓、中天 `#808AB2`（前 / 侧 / 后三处）✓、日带 `#FFB070` ✓、背日低空 `#7E88AE`（h < 285）。
- 地影带和金星带 / 玫瑰带用地平线带给，增益压低到紫 ≤ 2%。

---

## 7. 参考图怎么来的（和 Unity 是同一套数学）

`Tools~/render/shader_cpu.py`：把仓库里原样的 `LanbaiVR.cginc`、`LanbaiSky.cginc`、`LanbaiSkyLayers.cginc` 拼上 Unity 桩，用 slangpy 编成 CPU 计算程序，一个像素一个方向地跑 `LanbaiSkyColour()`。立方图用经纬图模拟（Unity 的经纬图约定：u = 0.5 − atan2(z, x)/2π，v = 1 − acos(y)/π），mip 3 用一份模糊过的副本代替。然后 `grade.py` 加 bloom、过调色套件的引擎（`Grading/Tools~/inputs/grades_engine.json`，也就是套件实际写进 profile 的参数）。

---

## 8. 和圣经的出入（请总导演看）

1. **地平线带**：圣经只给了 `_ZenithTint / _HorizonTint` 两个乘色。选定的晨 HDRI（syferfontein_6d，太阳 5.8°）里**没有地影带和金星带**（背日地平线是一片偏绿的亮霾），乘色拉不出来，所以加了两条可调的带。效果是“很淡”的那一种。
2. **紫色护栏**：暮 HDRI 背日方向本身是藍紫（本地量的 h 281、C\* 42），乘色只能按仰角 / 方位整体调，压不住局部；不加护栏时背后、侧面的视向紫占 35–72%。护栏是 shader 里的一行，只动“偏蓝而红接近绿”的颜色。
3. **背日 45° `#AFC4E0`** 只到 `#9FBDDB`（见 §6）。
4. **星的数量** 8 404（圣经“约 9 000”）；**银河带内外星密度比 1.67**（圣经引用 NASA 图“约 4.7 倍”，那是含更暗星的图；到 6.5 等的真实星表就是这个比例）。银河的“带”主要靠辉光读出来。
5. 日盘的“HDRI 里的太阳钳在 16”照做；第 8 幕 HDRI 的太阳已经落下（最亮是 3.7° 的余晖），日盘完全程序化（圣经也是这么写的）。

---

## 9. 检查

```
cd Sky/Tools~/compile_check
~/bpy/bin/python -I check_shaders.py ../../Shaders tests     # slang：每个 CGPROGRAM、每种关键字组合
~/bpy/bin/python -I check_gate_equivalence.py               # 第 4 幕：门的光带 = LanbaiHorizon（最大差 1.2e-7）
./check_cs.sh                                               # Roslyn：Editor + Runtime，警告即错误
```
结果：slang 9 个变体全过；C# 编译通过（0 警告）。**都不等于 Unity 编译过**；尤其 U# 的 `RenderSettings.skybox` 赋值是否在 Udon 白名单里没确认（不在的话把 `setSkybox` 关掉，见 `LanbaiSkyPreset.cs` 开头）。

---

## 10. 诚实的已知弱点

- 参考图里的 HDRI 是 1024 × 512 的缩略版（本地的原图是 16K），所以天看起来软；颜色和布局才是要对照的。
- 拟合用的是 1K 图；16K 图的平均色应当一样，但**太阳方位**要以 Unity 里量的为准（`Build Preset Materials` 会重新量并写进报告）。
- **Unity 经纬图导入的方位约定**我是按 `Skybox/Panoramic` 的公式假定的；如果本地看到太阳不在车门里（方位 +45°），报告里量到的方位会说明差多少——请把截图推回来。
- 银河辉光是用星表和轮廓表生成的，不是照片：远看像，近看大暗带（Great Rift）的细节比 NASA 图少。第 9 幕的包里会再调（这一版只保证颜色、位置和“没有硬边”）。
- 晨的地平线以下（天底 `#6F8FA8` 的渐变）读起来偏灰，第 6 幕这里被云原盖住；暮的地平线以下在 8-i 是灰紫的雾渐变，被下方的云卡盖住。
- `dusk_8ii` 向下看紫 1.9%，贴着 2% 的线。
- 星点的亮度标定（`_StarScale`、`_MagSlope`）要等第 9 幕的包按 F13 那一帧的截图定；现在的默认值只是让星“看得见、不刺眼”。
