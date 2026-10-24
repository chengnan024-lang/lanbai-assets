# 蓝白 · 天空（`Lanbai/Sky`、真实星表的星、月、银河、每一幕的天空预设）v1.2

> v1.2（10-23 恢复后）：**全片一个天空盒材质**（`Sky/Generated/M_Sky.mat`），预设之间的差别全走全局量（`_Udon_SkyGlobals` + `_Udon_Sky_*` 一族 + 全局立方图 `_Udon_SkyCubeTexA/B`）；新驱动 `LanbaiSkyDriver`；预设的所有权开关（`ownsAtmosphere / ownsSkybox`，默认关）；**银河换成 ESA Gaia EDR3 的照片**（8K）；天顶不再有靶心（渐变终点钳在 90°、天顶方向的混合改成对数空间）；晨的太阳 = 0.53° 程序化日盘（D-18）+ 软封顶掉 HDRI 自己的日斑 + 小光晕，方位 +30°（D-12）；星按 D-06（3 等以上、L\* ≤ 12、光雾带 −1 EV，`_Udon_StarShape`）；8-i 地平线以下 −18° 就转蓝、8-ii 下半球向天底渐暗、第 9 幕的夜遮罩是贴着地平线的一条带（顶边平、两端收，合拢时压到几度高；不再是圆角矩形、椭圆或穹顶）。逐条见 §8 与 `Docs~/review_response_r2.md`。

> v1.1（10-23）：按第 1 轮独立美术 / 技术评审改（逐条回应 `Docs~/review_response_r1.md`）：预设写全所有全局量、日线改读 `_Udon_SunDisc.z`、月盘按像素选 mip、`ApplyBlend` 重写、HDRI 地平线霾线不取样、另一片天可取第二张 HDRI、单调的蓝时带、8-i 下半球、8-ii 天顶过渡、月夜（月面贴图 + 月晕按 calib + 星）、第 1 幕的镇子钠光预设、星更亮（`_StarScale` 1.6、`_MagSlope` 0.5、40 km）。

写的人：云端子会话「天空」，2026-10-23。**没在 Unity 里编译过**：shader 用全仓共用的检查（`Common/Tools~/compile_check`：DXC + Unity 2022.3 的 CGIncludes 原件）查过，C# 用 Roslyn 对 Unity 的引用程序集查过（§9）。参考图是用 slang 在 CPU 上**直接跑这里的 shader 代码**渲出来、再按调色套件的引擎参数调色的（§7），所以本地截图可以和它逐项对照。
雾与天的共用接口见 `Sky/README_Fog接口.md`（`Common/Shaders/LanbaiFog.cginc`、`LanbaiSky.cginc`）。

---

## 0. 拷什么、点什么

1. 拷 `Common/`（`Assets/Lanbai/Common/`）和 `Sky/`（`Assets/Lanbai/Sky/`）。`Tools~`、`Docs~`、`Source~` 以 `~` 结尾，Unity 不会导入。
2. **晨 / 暮的 HDRI 用本地的 8K / 16K 原图**（`syferfontein_6d_clear_puresky`、`syferfontein_0d_clear_puresky`，Poly Haven 的 `.hdr`），放在工程任意位置（文件名要含这两个名字，构建器按名字找）。导入设置：
   - **Texture Shape = Cube、Mapping = Latitude-Longitude Layout (Cylindrical)**；
   - **Max Size 8192**（立方图每面 = 宽 / 4：8K 图 → 每面 2048，16K 图 → 每面 4096；Unity 立方图上限 8192 每面，16K 原图也可以 8192，但显存 ×4，**建议 8192 宽 → 每面 2048**，日盘是程序化的，天本身很柔，2048 每面在头显里已经是 ~0.04°/纹素）；
   - **Format = BC6H**（HDR，不 crunch），**Generate Mip Maps 开**（地平线以下取 mip 3 的柔和版本）、Filter = Trilinear；
   - sRGB 不相关（HDR 是线性的）。
   换了原图之后要重新确认的数只有两个：①**太阳方位**——构建器在原图上重新量，写进 `_Udon_Sky_RotationA`（报告里有）；②拟合的乘色在 1K 缩略图上做的，8K 的平均色一样，**不用重拟合**；只有换了另一张 HDRI 才要跑 `Tools~/render/fit_hdri_tints.py`。
3. 菜单 **`蓝白/Sky/Build Star Mesh`** → `Sky/Generated/StarPoints_BSC5.asset`。
4. 菜单 **`蓝白/Sky/Build Sky`** → **一个**材质 `Sky/Generated/M_Sky.mat`（`Lanbai/Sky`，银河辉光、月面贴好），并设成场景的天空盒（**存一下场景**）；场景里 `Lanbai_SkyPresets` 下每个预设一个物体（U# `LanbaiSkyPreset`，填好全局量、立方图、雾色 / 环境色；自动建 `LanbaiSkyPreset`、`LanbaiSkyDriver` 的程序资产）；再在 HDRI 原图上**重新量太阳**，把旋转写进那个预设的 `_Udon_Sky_RotationA`（报告 `Sky/Generated/SkyBuild_Report.txt`，实时平行光按里面的方位 / 仰角对齐）。可以重复点：原地更新，驱动对这些物体的引用不会断。
5. 驱动：`Build Sky` 同时建好**两个** `LanbaiSkyDriver`（`Lanbai_SkyDriver_Acts1to3`、`Lanbai_SkyDriver_Acts11to12`，各管一段连续的时间窗，表来自 `SkyPresets.json` 的 `drivers`，时刻按 `FromLocal/cues.json` 的标签算好），挂进 Director 的分发层；第 6、8、8b 幕由「云」的驱动调 `LanbaiSkyPreset.Apply()` / `ApplyBlend()`。**一幕只有一个写天空全局量的驱动**（§3.1 的表）。
6. 菜单 **`蓝白/Sky/Preview Window`**：在编辑器里点一个预设就写好全局量、全局立方图和雾密度（只在编辑模式里有效，进 Play 会丢，见坑 9）。
7. **Player Settings → Other Settings → Vertex Compression：Color 和 TexCoord1 两项都关**（终审二）。星的顶点颜色按亮度 1 归一化，蓝星 / 红巨星的通道 > 1（天狼星 b = 1.24，全表最大 (1.37, 1.00, 1.40)）；排名和熄灭顺序在 TEXCOORD1。默认的顶点压缩会把颜色压成 8 位（截掉 > 1 的通道）、UV1 压成半精度。
8. 星：`Build Sky` 建**全片唯一的**主星物体 `Lanbai_Stars_BSC5`（`StarPoints_BSC5.asset` + `M_Sky_StarPoints.mat`，关阴影 / 探针；每次都把材质 `_Gain` 写回 0）。星由每个预设写的 `_Udon_StarGain` 点亮；第 9 幕不再另建一份（以前两份叠加 = 所有星 +1 EV）。

**请推回来的截图**（桌面 1920×1080、水平 90°、主座位眼位 `cameras.U7` (0.55, 1.70, 2.05)，PPv2 开，渲进 ARGBHalf 再调色）：在一个空场景里（只有天空盒 + 星，没有车）每个预设截“前方 / 车门 +45° / 天窗仰 70° / 背后”四张，`moon_night` 另加一张对着月亮的 1:1 裁切（1920 / 90°，看月面读不读得出），和 `Sky/Docs~/presets/preset_<预设>.png` 对照；另外 Console 原样。

---

## 1. 文件

| 路径 | 是什么 |
|---|---|
| `Shaders/Lanbai_Sky.shader` + `LanbaiSkyLayers.cginc` | 天空盒 `Lanbai/Sky`（§2）。逻辑全在 `.cginc` 里，CPU 参考渲染跑的就是它 |
| `Shaders/Lanbai_StarPoints.shader` | 星点 `Lanbai/StarPoints`：每颗星一个高斯精灵（§4） |
| `Textures/StarSky_Glow_8192x4096.png` | 银河辉光：ESA Gaia EDR3 全天图做的，世界坐标的经纬图，8 位 sRGB、归一到 1（材质 × `_GlowScale` = `Data/StarSky.json` 的 `glow_scale`），**没有星**（§4）。**Milky Way: ESA/Gaia/DPAC (CC BY-SA 3.0 IGO)**，https://creativecommons.org/licenses/by-sa/3.0/igo/（`Source~/data/LICENSE_Gaia_CC-BY-SA-3.0-IGO.txt`） |
| `Textures/Sky_Overcast_Night_2048x1024.hdr`、`..._TownGlow_...hdr` | 阴云夜（第 1、2、11、12 幕）；带“镇子方向钠光照亮的云底”的变体 |
| `Textures/Moon_Disc_1024.png` | 月面圆盘（NASA 照片，去饱和 70%，alpha = 圆盘） |
| `Data/StarPoints_BSC5.csv` | 8 404 颗星（Yale BSC，≤ 6.5 等）：Unity 世界方向、星等、B−V、线性颜色、亮度排名 |
| `Data/StarSky.json` | 星空朝向（赤道 → Unity 世界的旋转矩阵）、银心方向、来源 |
| `Data/fit_dawn.json`、`fit_dusk.json` | 晨 / 暮 HDRI 的乘色拟合结果 |
| `SkyPresets.json` | **每一幕的天空预设**（§3）：全局量（含 `_Udon_Sky_*` 一族）+ 量出来的数（`material` 一栏只是同样的值的材质写法，CPU 参考图用） |
| `FogPresets.json` | 每一幕的雾（`README_Fog接口.md`），含第 4 幕（门）的雾与**星**的值 |
| `Data/stars_D06.json` | 第 3、4 幕的星按 D-06 检查的结果（`Tools~/render/check_stars.py`） |
| `Editor/LanbaiSkyImport.cs` | 导入设置（只管 `Sky/Textures/`） |
| `Editor/LanbaiSkyBuild.cs` | 上面 §0 的菜单 |
| `Runtime/LanbaiSkyPreset.cs` | U#：写一组预设的全局量和全局立方图；`ownsAtmosphere`（雾密度 / 雾色 / 环境色）、`ownsSkybox` 默认关 |
| `Runtime/LanbaiSkyDriver.cs` | U#：按时间表切换 / 淡变预设（§3.1），总控 §5 的接口 |
| `Source~/` | 生成数据的脚本（`make_starsky.py`、`make_overcast_night.py`、`make_moon_disc.py`）和下载的原始数据 |
| `Tools~/render/` | CPU 参考渲染（`shader_cpu.py`、`sky_cpu.py`）、调色（`grade.py`）、乘色拟合（`fit_hdri_tints.py`）、预设生成（`make_presets.py`，含梯度自检与一个材质的逐像素核对）、星的 D-06 检查（`check_stars.py`）、预设序列测试（`test_sequence.py`） |
| `Tools~/compile_check/` | 门光带等价核对（`check_gate_equivalence.py`）、雾的 include 组合测试（`tests/`）；编译检查本身用全仓共用的 `Common/Tools~/compile_check/` |
| `Docs~/presets/preset_*.png` | 每个预设六个视向的参考图（调好色的） |

---

## 2. `Lanbai/Sky` 的层（从下到上，颜色全是线性值，颜色属性故意用 Vector）

1. **两张立方图 A / B**（HDRI）：各自固定的 Y 旋转（`_RotationA/B`，内容的方位 += 这个角；**只在搭建时设，运行时永不旋转**）、EV、钳位（默认 16：HDRI 里的太阳被钳掉，日盘程序化画）、**四个乘色**：天顶、中天、朝日的地平线、背日的地平线（`_TintElevation` = 地平线满到几度 / 中天满在几度 / 天顶满在几度 / 方位权重的幂）。`_Blend` 混合 A → B。**往天顶的过渡**（乘色、程序化的天顶）用 `LanbaiUpStep`：终点钳在 90°（终点超过 90° 时天顶是一个尖点 = 靶心；终点低于 90° 时天顶是一块平的圆盖，边上一圈），预设里往天顶走的渐变都在 90° 结束；**混合在对数空间**（`LanbaiGeoLerp`：线性光里从亮地平线到暗天顶的插值在屏幕上一直亮到 60° 再塌下去，看上去头顶一个黑圆）。`_SunRemove`：HDRI 自己的日斑（裁过的平顶，约 3°）在半径 x 内去掉。**y ≤ 0 = 补图模式**（晨用，终审 1）：圆内每一行按同一仰角，在圆的左、右两边之间插值，× (x / 角距)^z 的小光晕；天的上下渐变保住，圆上和原图一样，没有盘、没有环、没有放射线（沿半径补会画出放射线）。y > 0 = 旧的封顶模式（亮度软封顶在 y，w 把色相拉向日色）。日盘与光晕由程序化给。
   **地平线以下**换成该方位的地平线色 → `_NadirColor` 的渐变（纯天空 HDRI 的下半球没法用）；`_NadirColor.a` 把渐变中段拉向冷灰（暖 → 靛蓝的中段会经过紫）。
2. **程序化**：`LanbaiHorizon(V)`，**和雾是同一个函数**，所以雾完全吃掉的物体会消失在天里；权重 `_ProcWeight`。
3. **两条地平线带**（`_Band1/2Color/Shape/Gain`）：按仰角和**相对太阳的方位**定位的高斯带，把天拉向某个颜色。晨：地影带 + 很淡的金星带（选定的 HDRI 里没有）；蓝时：最纯的蓝带；第 12 幕：天边那一线。`Color.a` 同样把带的边缘拉向冷灰。
4. **另一片天**（第 8-ii 幕）：地平线以下按 (−x, −y, z) 取样立方图（绕前方轴转 180°，不是翻转）× `_OtherGain`（0.82）× `_OtherTint`，1° 软接缝；**它自己的太阳也画出来**，两个太阳在接缝上熔成一条线。
5. **紫色护栏** `_PurpleGuard`：圣经 §1.3.4（第 4 幕以外紫 ≤ 2%），**10-23 总导演加：晨 / 暮 / 蓝时里玫瑰到靛蓝的过渡守 C\* ≤ 8，h 285–330 不许出现**（D-17 的道理）。晨、暮、蓝时用双向模式 `(1, 0.75, 0.95, −1)`（终审 2 改过）：①**强蓝**（B/G ≥ 1.3、蓝压过红）R 限在 0.64 G 以内：仍是蓝（中天前方约 `#7D95C3`，圣经 `#808AB2` 一带），不变青；②**玫瑰进蓝的那一段**（B 压过 G、R 接近 G、R/B 0.6–1.35）先把 R/B 往两头推一点（蓝的一侧只减红、粉的一侧只加红、中间连续），让颜色少在中间停留，再把**中间**一窄条往**淡金白**送（同亮度微提，靠蓝的一侧偏冷、靠粉的一侧偏暖，调色后 h 60–100、低彩度）：画面上是玫瑰和蓝之间一道细的淡色缝，不是一条灰带、也不是淡紫；③**红明显压过蓝的粉不碰**（R/B > 1.5：背日的玫瑰带留粉，`#C89EA7`）。**品红粉**（R/B 1.1–1.35）也算进中间：暮的调色下它是粉，蓝时较冷的调色下会变成淡紫，8-ii → 8b 的淡变里会露出来（`test_sequence` 查到的那段）。验收：**紫带**（**h 290–330**、C\* > 8、L\* > 40，D-21 修订：圣经色板里写明的颜色一律放过，中天 `#808AB2` 在 h 285.3、车厢 `#828BAA`、暮天顶 `#3D4A80` 都不归它管）六个视向都 0%，淡变里整球也查（`test_sequence.py`）。旧的单向模式（w ≥ 0：只压 R）还在，给别处用。偏蓝、红接近绿的天在 S8 的暖调色（色温 +3、色调 +1）下会变成淡紫；护栏在 B/G 高的地方把 R/G 限在 `y` 以下。暖色、玫瑰、真正的蓝不受影响。
6. **夜**：`_NightColor` + 增益 g ×（星空底 `_StarFloorAdd` + 银河辉光 `_GlowTex`）；权重 `_NightBlend` **按方向延迟**（第 8b → 9 幕：背日和天顶先黑，前方 ±40° 的地平线带在 6 秒时仍 ≥ 50%，8 秒全黑；`_NightMaskDir/Shape` = (40, 45, 6, 22)：方位 ±40° 满、45° 软边，仰角 6° 满、22° 软边；带的顶边是方位上指数 4 的超椭圆，平着走、只在两端收；变暗的最后四分之一里仰角轴收到四分之一，最后一抹只有几度高、贴着地平线；地平线以下仰角按 4 倍算，先黑）。银河辉光在银心周围 18° 内往暖尘 `#C8B79A` 拉（`LanbaiGalaxyCoreTint`，`LanbaiSky.cginc`；烘好的图在 S9a 下偏粉灰）。
7. **日盘 / 日线**（程序化，**直径 0.53°**（D-18，`_SunShape.x` = 半径 0.265），临边昏暗，软边 ≥ 2 个 VR 像素、峰值 > 1 时按峰值锐化覆盖率；`_Udon_SunDisc.z`（没设时 `_SunShape.w`）> 0 时变成水平的“日线”，第 8 幕 F12 的收缩）+ 可选的日晕；**月**（`_MoonTex` 圆盘，按像素大小选 mip；月晕 a1·e^(−k1·度) + a2·e^(−k2·度)）。
9. **地平线霾线**：每张 pure-sky HDRI 在 0° 都有一道暗霾线，`_HorizonLift`（0.8°）以下永不取样它。**另一片天**可以取第二张 HDRI（`_OtherFromB` = 1、`_CubeB`），不再是同一张的旋转。地平线带 `Shape.y < 0` = 单调带（带中心以上取带色与天色中更暗的那个，蓝时用）。**地平线以下**：`_BelowMirror` = 1 时按镜像的仰角取这片天（天在下面继续，8-i 用），0 时把地平线的颜色带下去；两种都往 `_NadirColor` 走（`_BelowShape` = 天底在几度 / 幂 / 地平线取样的仰角 / 软样本的钳位）。
10. **开销**：天空盒每像素约 0.3–0.6 ms @ 9 MP（一张立方图 + 程序化 + 两条带 + 护栏；另一片天和夜层各多一份，都在 `[branch]` 里）。
8. 抖动（方向锚定、两眼一样，`LanbaiVR.cginc`）。

全局量（都可选；没设就用材质值）：

| 全局量 | 含义 |
|---|---|
| `_Udon_SkyBlend` | x 立方图 A → B、y 程序化权重、z 夜的权重（按方向延迟）；w > 0 = 设了 |
| `_Udon_SkyFx` | x 另一片天、y 地平线带 1 的增益、z 空着；w > 0 = 设了 |
| `_Udon_GalaxyGain` | x 银河辉光与星空底的增益 g(t)（第 9 幕；旋臂）；y 银心的增益、z = 1 时用 y（点燃时银心先亮，`LanbaiGalaxyGainAt`）；w > 0 = 设了 |
| `_Udon_StarGain` | x 星点总增益（F13 那一帧 0 → 1）、y 亮星加成（> 0 = 用它）、z 亮星个数（> 0 = 用它）；w > 0 = 设了 |
| `_Udon_SunDir` / `_Udon_SunDisc` | 指向太阳；x 日盘增益、y 半径（度）、z 日线半长（度）；w > 0 = 设了 |
| `_Udon_MoonDir` / `_Udon_MoonDisc` | 指向月；x 月盘增益、y 半径（度）；w > 0 = 设了 |
| `_Udon_StarShape` | 星：x 最暗星等（> 0 盖过材质的 `_MagFloor`）、y 光雾带里的 EV（第 3–4 幕 −1）、z 带的半宽（度，0 = `_Udon_FogBandWidth`）；w > 0 = 设了 |
| `_Udon_SkyGlobals` | **一个材质**：x > 0.5 = 下面 `_Udon_Sky_*` 一族盖过材质值；y > 0.5 = 立方图 A 用全局纹理 `_Udon_SkyCubeTexA`；z 同理 B |
| `_Udon_Sky_<属性>` | `Lanbai/Sky` 的 46 个属性的全局版（名字 = `_Udon_Sky` + 材质属性名，例 `_Udon_Sky_ZenithTintA`；单个数放在 .x）。清单在 `LanbaiSkyLayers.cginc` 的 `LanbaiSkyLoadParams()` 与 `make_presets.py` 的 `SKY_V4 / SKY_F1` |
| `_Udon_SkyCubeTexA/B` | 全局立方图（`VRCShader.SetGlobalTexture`，`LanbaiSkyPreset` 写） |

`_Udon_Sky_*` 的 46 个（全是 float4，单个数在 .x）：`_Udon_Sky_ZenithTintA`、`_Udon_Sky_MidTintA`、`_Udon_Sky_HorizonTintA`、`_Udon_Sky_HorizonAntiTintA`、`_Udon_Sky_ZenithTintB`、`_Udon_Sky_MidTintB`、`_Udon_Sky_HorizonTintB`、`_Udon_Sky_HorizonAntiTintB`、`_Udon_Sky_TintElevation`、`_Udon_Sky_NadirColor`、`_Udon_Sky_BelowShape`、`_Udon_Sky_Band1Color`、`_Udon_Sky_Band1Shape`、`_Udon_Sky_Band2Color`、`_Udon_Sky_Band2Shape`、`_Udon_Sky_OtherTint`、`_Udon_Sky_NightColor`、`_Udon_Sky_StarFloorAdd`、`_Udon_Sky_NightMaskDir`、`_Udon_Sky_NightMaskShape`、`_Udon_Sky_SunDir`、`_Udon_Sky_SunColor`、`_Udon_Sky_SunShape`、`_Udon_Sky_SunGlow`、`_Udon_Sky_SunGlowColor`、`_Udon_Sky_MoonDir`、`_Udon_Sky_MoonColor`、`_Udon_Sky_MoonGlow`、`_Udon_Sky_MoonGlowColor`、`_Udon_Sky_PurpleGuard`、`_Udon_Sky_SunRemove`、`_Udon_Sky_RotationA`、`_Udon_Sky_ExposureA`、`_Udon_Sky_ClampA`、`_Udon_Sky_RotationB`、`_Udon_Sky_ExposureB`、`_Udon_Sky_ClampB`、`_Udon_Sky_Band2Gain`、`_Udon_Sky_OtherGain`、`_Udon_Sky_OtherSeam`、`_Udon_Sky_OtherFromB`、`_Udon_Sky_HorizonLift`、`_Udon_Sky_MoonRadius`、`_Udon_Sky_Exposure`、`_Udon_Sky_GlowScale`、`_Udon_Sky_BelowMirror`。
| 雾的那一组 | 见 `README_Fog接口.md` §3 |

**预设之间不留残值**：每个预设都列出全部预设用到的所有全局量（没用的 = 0 = 没设），`LanbaiSkyPreset.Apply()` 一次写全（`Tools~/render/test_sequence.py` 按片子的顺序回放核对）。

**一个材质**：全片只有 `M_Sky.mat`；材质上的值只在 `_Udon_SkyGlobals.x` = 0 时用（测试场景）。每个预设导出时，`make_presets.py` 把同一个预设按“材质路径”和“全局量路径”各渲一次逐像素比较（8 个预设都是 0 差）。全局量在进 Play 时会丢（坑 9），所以 `Apply()` 在 `Start()` 里调。

**给海（ABOVE 模式的倒影太阳）**：太阳方向读 `_Udon_SunDir`（w > 0）。日盘的线性辐亮度 = `_SunColor` × `_Udon_SunDisc.x`（没设时 × `_SunGain`）：**第 6 幕 `#FFCE9E @ +2.55` = 线性 (5.86, 3.62, 2.00)**，半径 0.265°（直径 0.53°，D-18），临边昏暗 0.55；第 8 幕 `#FF9167 @ +2.74` = 线性 (6.68, 1.89, 0.92)。海镜里的倒影太阳按圣经要比这个低 ≥ 1.3 EV。

---

## 3. 每一幕的天空预设（`SkyPresets.json`，由 `Tools~/render/make_presets.py` 生成）

| 预设 | 幕 | 调色 | 天 | 雾色 |
|---|---|---|---|---|
| `overcast_rain_night` | 2（−0.7 EV）、11、12 开头 | S1 | `Sky_Overcast_Night`：天顶 `#070B14`（填 `#09080D`），地平线 = 雾 `#121A28`（填 `#161B27`） | 模型 B，几乎一色 |
| `overcast_rain_night_town` | 1 | S1 | 同上 + 镇子方向钠光照亮的云底 `#241E22`（−70°，本地按车站改） | 模型 B，朝镇子一侧暖 |
| `moon_night` | 3 | S3 | 程序化：天顶 `#08101F`、背月地平线 `#111B30`、月 −12° / +8°、直径 1.2°（月心 `#E0E7EF`、月晕 6° `#58668C` / 10° `#2A3553`，calib 目标 `#EAEEF4` / `#5A6A88` / `#26344F`）、星（D-06：3 等以上，增益 0.015） | 模型 B，朝月一侧亮 |
| `dawn` | 6 | S6 | `syferfontein_6d`，太阳方位 **+30°**（D-12，车门里）仰角 5.8°；天顶 `#3E64A6`、背日 45° `#AFC4E0`（拟合到 `#95B2D3`）、日侧地平线 `#F2C79A`、地影带 + 很淡的金星带、日盘直径 0.53° `#FFF3DE` + 小光晕，HDRI 的日斑软封顶 | 模型 B，从这片天的 1° 仰角取样（朝日 / 背日 / 天顶） |
| `dusk_8i` | 8-i | S8 | `syferfontein_0d`，HDRI 的余晖转到方位 0°、日盘程序化在 +0.5°；日带 `#FFB070`、玫瑰带 `#E7A0A0`、中天 `#808AB2`、天顶 `#3D4A80`；紫护栏 | 同上 |
| `dusk_8ii` | 8-ii | S8 | 同上 + 另一片天 = 1 | 同上 |
| `blue_hour` | 8b + 9 | S8b | 程序化：地平线 `#6F86B0`、最纯的蓝带 `#2E4F8A`（单调带）、天顶 `#16223F`、天底 `#1A2A4E`；夜层、银河辉光备好（第 9 幕驱动接管） | 雾密度 0 |
| `star_sea` | 9 | S9a | 夜：`#04060E` → 星空底 `#08112A` + 银河辉光（g = 1 时） | 雾关 |

量出来的数（只有天，没有车、没有云；所以 APL 不能和圣经 §2 的整帧 APL 比）在 `SkyPresets.json` 每个预设的 `measured_views` 里，图在 `Docs~/presets/`。七个预设、六个视向的紫占比（h_ab 290–325、C\* > 15）最大 1.9%（`dusk_8ii` 向下看），其余全是 0。晨另按第 6 幕的严规则（h 285–330、C\* > 12）量：0%。

**第 10 幕（白）不需要天空预设**：白由遮罩球给（`Mirrors/`、`Overlay/`），遮罩后面的一切关闭。

### 3.1 幕 → 驱动（一幕只有一个写天空全局量的）

| 幕 / 时段（t = 时间轴秒，`FromLocal/cues.json`） | 预设 | 写天空全局量的 | 怎么写 |
|---|---|---|---|
| 1（0 → 车开，站牌） | `overcast_rain_night_town` | `LanbaiSkyDriver`（天空） | `Start()` 写第一个预设，t = 0 的天就是对的 |
| 2（开车 → 离地，U1 17.50 起） | `overcast_rain_night` | `LanbaiSkyDriver` | 钠光那一侧 10 秒淡掉（`fadeSec`） |
| 3（离地 → 月下云海，U6k 129.10 破云起） | `moon_night` | `LanbaiSkyDriver` | 破云在云里（遮挡下）切；星按 D-06 |
| 4（触手之门，U6 133.80 → U12 248.64） | `moon_night`（天） + 门的雾 / 光带 | **门的驱动**写雾那一组（`FogPresets.json` 的 `act4_gate`，含 `_Udon_StarShape` 的 −1 EV）；天空盒的 `_Udon_Sky_*` 不动 | `LanbaiSkyDriver` 在 133.80 → 248.64 没有条目 |
| 5（门内） | —（门内自己的世界） | 门内 | — |
| 剪 1 → 6（248.64 → F2h 363.26，晨） | `dawn` | **「云」**（第 6 幕的包） | 黑遮罩下 `Apply()` |
| 7（海，F2h 起） | （水下组） | **海** | `_Udon_Underwater` 那一组（`README_Fog接口.md`） |
| 8-i（出海 922.36 →） | `dusk_8i` | **「云」**（第 8 幕的包） | 出海时 `Apply()`（水面下） |
| 8-ii（F10e 956.36 → 964.36） | `dusk_8ii` | 「云」 | `dusk_8i.ApplyBlend(dusk_8ii, t)`，8 秒 smoothstep |
| 8b（F12 987.06 → 993.06 → 1001.21） | `blue_hour` | 「云」 | `dusk_8ii.ApplyBlend(blue_hour, t)` 6 秒；日线另写 `_Udon_SunDisc.z` |
| 9（1001.21 → F16 1149.31） | （从 `blue_hour` 接着） | **第 9 幕的驱动**（`Act09_StarSea/`） | 1001.21 起写 `_Udon_SkyBlend / SkyFx / Fog / GalaxyGain / StarGain`，1009.21 起再加 `_Udon_ZenithColor / HorizonColor / FogBandColor / NadirColor`（= 星空底）；`_Udon_Sky_*` 留着蓝时的值。8b 的驱动在 t ≥ 1001.21 时不再 Apply / ApplyBlend |
| 10（白） | — | 遮罩球（`Mirrors/`、`Overlay/`） | 天被遮住 |
| 11、12 | `overcast_rain_night`（12 的开头） | `LanbaiSkyDriver` | 白遮罩下 `Apply()` |

**`LanbaiSkyDriver`**：每个实例只管一段连续的时间窗（`LanbaiWindow()` 就是它，分发层按它让出 RenderSettings），四个数组由 `Build Sky` 从 `SkyPresets.json` 填，`Start()` 检查长度一致（不一致就报错、不运行）。`presets[i]` 在 `[presetT0[i], presetT1[i])` 里是当前的；进入时从 `presets[i − 1]` 用 `fadeSec[i]` 秒 smoothstep 淡入（0 = 硬切，只能在遮挡下）；不在任何条目里的时段什么都不写（别的驱动在写）。每次换条目 `Apply()` 一次，淡变期间每帧 `ApplyBlend`。
**`ApplyBlend` 的规矩**（一个材质以后不换材质）：两边名字相同、顺序相同（构建器排好序，映射是恒等），每个量按 `SkyPresets.json` 导出的**组**（`vecGroups`，不在 Udon 里猜名字）处理：立方图 A / B 的参数（乘色、旋转、EV、钳位）和立方图层共用的参数（`TintElevation`、`NadirColor`、`BelowShape`、`SunRemove`、`HorizonLift`、`OtherTint`、`BelowMirror`）不和“没有图的那一边”插值，由有图的一边给；**两边都有图 A 但不是同一张（或旋转不同，第 1 → 2 幕）时走 B 槽交叉淡化**：对面的图绑到 `_Udon_SkyCubeTexB`、它的 A 参数放进 B 槽、`_Udon_SkyBlend.x` = t，t = 1 时 `other.Apply()` 把它放回 A，画面一样——天不会转；`_Udon_SkyGlobals` 取最大值；方向量（雾带方向、日、月、夜遮罩）一边是零就不拉、两边都有就归一化插值；`blendSkip` 里的名字这一段不写（`dusk_8ii` 的 `_Udon_SunDisc`：F12 起日线由「云」的驱动写，一个名字一个写入者）。`Tools~/render/test_sequence.py` 用同样的规则按片子顺序回放，并查淡变中点的天顶梯度、t = 0.999 与 `Apply(b)` 的差（< 1 个显示码）。
**所有权**：`ownsAtmosphere`（`RenderSettings` 的雾密度 / 雾色 / 环境色，给内置 shader）、`ownsSkybox`（把 `M_Sky.mat` 设成天空盒；构建时已经设好，一般不用）**默认都关**，由负责那一幕的驱动决定开不开。`ownsAtmosphere` 只写 `RenderSettings.ambientLight`；环境光是 Trilight 模式时赤道色 / 地面色仍归 `LB_Journey`。

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

展开（`Lanbai_StarPoints.shader` 的 vert）：中心 C = 两眼中点 + D × `_Distance`（40 km）；右 R = normalize(cross(up, D))（D 接近竖直时 up 换成 x）、上 U = cross(D, R)；半边长 h = 2 × FWHM 像素 × `LanbaiPixelAngle()` × `_Distance`；P = C + (R·uv0.x + U·uv0.y)·h。亮度 = `_StarScale`（1.6）× 10^(−0.4 × `_MagSlope`（0.5）× (m − `_MagRef`（0）))，排名在亮星个数以内的 × 亮星加成（按 20 个排名平滑过渡），`_UseGlobalGain` = 0 的材质不读全局增益，× `_Udon_StarGain.x`，× 顺序遮罩；片元是 exp(−4 ln2 r²)（r 以 FWHM 为单位），叠加混合。镜子在模板里画第二遍时，把 D 换成镜面反射后的方向即可（平面镜：D' = reflect(D, n)；凸 1.5% 的鱼眼在镜子 shader 里做）。

**银河辉光**（`StarSky_Glow_8192x4096.png`）：**照片**——ESA/Gaia/DPAC 的 Gaia EDR3 全天彩色图（银道坐标的经纬图，经 `mw_plot` 包（MIT，H. Leung）取得，`Source~/data/`）。**授权 CC BY-SA 3.0 IGO，署名原文（D-11）：“Milky Way: ESA/Gaia/DPAC (CC BY-SA 3.0 IGO)”**，授权链接 https://creativecommons.org/licenses/by-sa/3.0/igo/，授权文件 `Source~/data/LICENSE_Gaia_CC-BY-SA-3.0-IGO.txt`；这张衍生纹理也是 CC BY-SA 3.0 IGO（片尾公告板要补这一行，见 `给总控.md`）。做法（`Source~/make_starsky.py`）：显示值 → 线性；3×3 开运算去掉点状的星（星由星表精灵画，留一半细颗粒）；减掉高银纬的天光背景；亮度曲线 ^1.6，最亮的 0.1%（人马、盾牌、天鹅的星云团）到填值、带的主体远低于它（带内中位 0.07、90% 分位 0.21）；软膝；然后按圣经的色板重新上色：旋臂冷（填 `#6A758A`，屏幕 `#6F82A0`），**暖尘只在核球**（银心 ±13° 的高斯 × 图自己的红蓝比，填 `#CBAE82`，屏幕 `#C8B79A`）。暗尘带（大暗隙）、星云团、麦哲伦云都是照片里本来就有的。8192×4096（0.044°/纹素），8 位 sRGB PNG 归一到 1（半浮点 EXR 是 135 MB，超过仓库上限），材质 × `_GlowScale`（`Data/StarSky.json` 的 `glow_scale`，现在 0.5006；8 位 sRGB 在暗处的台阶比一个显示码细，再加 shader 的抖动）。导入：sRGB 开、**有 mip**（shader 按像素大小选 LOD：桌面 1080p / 90° 是 mip 0，头显约 mip 1，头动时不闪）、U 重复 V 钳、BC7、Max Size 8192（`LanbaiSkyImport.cs` 自动设）。星空底 `#0D0F23` 不在图里，`Lanbai/Sky` 加。
映射（`LanbaiSky.cginc` 的 `LanbaiGalaxyUV`）：u = 0.5 + atan2(V.x, V.z) / 2π，v = 0.5 + asin(V.y) / π；不用 mip（圣经：任何模糊都不要）。

**第 3、4 幕的星（D-06）**：同一张星表、同一个增益（`moon_night` 的 `_Udon_StarGain.x` = 0.015，第 4 幕 `FogPresets.json` 的 `act4_gate.stars` 写同一个数），只留 **3 等以上**（`_Udon_StarShape.x` = 3，圣经 §6·4“只有 mag < 3 的星”），**没有银河**（`_Udon_GalaxyGain.x` = 0），第 4 幕光雾带里**再暗 1 EV**（`_Udon_StarShape.y` = −1，带 = `_Udon_FogBandDir` ± `_Udon_FogBandWidth`、仰角 10° 以下，软边 10° / 15°），FWHM 1.6 px（材质的范围 1.5–4，单像素的星在头显里会闪）。**L\* ≤ 12 我的读法**：1080p、水平 90°、调色之后，最亮那颗星**比它所在的天高出的 L\*** ≤ 12（绝对的 L\* ≤ 12 做不到：月夜朝月一侧的地平线天本身就超过 L\* 12，那里一颗星都不能有）；`Tools~/render/check_stars.py` 在四个视向、两幕各量一次（月盘 ±3° 除外），按**最坏情况**（每颗星正对像素中心，全峰值）量，结果第 3 幕最亮的星比它的天高 ΔL\* 11.6、第 4 幕 11.4（≤ 12，通过；0.015 是通过的最大增益）（`Data/stars_D06.json`）。读法不对请总导演改，脚本里改 `L_MAX` 和量法就行。
**每个预设都写星**：阴云夜、晨、暮、蓝时 = 0；`star_sea` 也写 0（第 9 幕的驱动从 F13 起写），预览图画的是点燃后的状态。

**第 9 幕的全局量**（镜子读的）：`_Udon_GalaxyGain.x` = 银河辉光 + 星空底的增益（点燃的 g(t)，之后 x^2.5 曲线上 1.0 → 1.8），`.y` = 银心的增益（点燃时比旋臂早一点，`.z` = 1 时用；按方向的增益 = `LanbaiGalaxyGainAt(_Udon_GalaxyGain, 方向)`）；`_Udon_StarGain.x` = 星点总增益（F13 一帧 0 → 1），`.y` = 亮星加成（×4 → ×8），`.z` = 亮星个数（50 → 200）；`_Udon_ZenithColor.rgb` = **当前的星空底**（= `_NightColor` + g × `_StarFloorAdd`，第 9 幕的驱动从 1009.21 起每帧写，`_Udon_HorizonColor / FogBandColor / NadirColor` 同值，所以 `LanbaiHorizon` 也落在星空底上）。所以镜子反射的天 = `_Udon_ZenithColor` + `LanbaiGalaxyGainAt(_Udon_GalaxyGain, 反射方向)` × `LanbaiGalaxySample(StarSky_Glow, 它的 _TexelSize, 反射方向, LanbaiGalaxyScale())`（`LanbaiSky.cginc` 的共用函数：乘 glow_scale、银心的暖色、按像素大小选 LOD，图开了 mip）+ 星点第二遍。（`_CubeB` 在 `Lanbai/Sky` 里是第二张 HDRI，不是银河。）

---

## 5. 月、阴云夜

- 月面：NASA 阿波罗 11 号拍的满月（AS11-44-6667，`github.com/nasa/NASA-3D-Resources` 的 `Moon.jpg`，NASA 媒体无版权）。圣经点名的 CGI Moon Kit 连不上，这张是真的满月照片，1.2° 的圆盘用它足够。去饱和 70%，最亮的高地 ≈ 0.95，亮度由 `_MoonColor`（S3 填 `#F0F5FF @ +1.67`）定。
- 阴云夜：程序化的低对比层积云底（1.2 km 高的云面上做分形噪声，所以往地平线方向自然压扁），±7% 的明暗；值是 S1 的填值（天顶 `#09080D`、地平线 = 雾 `#161B27`）。第 2 / 11 幕在 S2 下 −0.7 EV。带镇子钠光的变体：钠光在方位 0°，`_RotationA` 转到镇子的方位。

---

## 6. 晨 / 暮 HDRI 的乘色是怎么来的

`Tools~/render/fit_hdri_tints.py`：在 CPU 上跑真的 `LanbaiSkyLayers.cginc`，对几个区域的平均色做最小二乘，目标是调色之后的屏幕值（引擎求逆得到填值）。v1.2 起**天顶区间总是在 90° 结束、中天最高 40°**（往天顶的变暗铺在 ≥ 50° 上，头顶不出圆斑），HDRI 的太阳在 1K 图上量出来再转到预设的方位（晨 +30°，D-12）；几个起点取最好的。
- 晨（S6）：天顶 `#3E64A6` → `#3F65A7` ✓、日侧地平线 `#F2C79A` ✓、背日 45° `#AFC4E0` → **`#95B2D3`**（v1.1 是 `#9FBDDB`：这张 HDRI 背日中天不够亮，再让 45° 变亮就得把变暗挤到 60° 以上，头顶就是一个蓝斑；总导演 r1 的“不许有形状”是阻断，所以让给它；D-18 让本地按 8K 再校）；另三个圣经没写数的约束：日上方 25–35° 淡蓝、日侧 10–16° 暖珍珠白、侧窗 10–20° 淡蓝。
- 暮（S8）：天顶 `#3D4A80` ✓、中天 `#808AB2`（前 `#808EB8` / 侧 `#6C7CA6` / 后 `#6A7BA6`）、日带 `#FFB070` → `#FFB677`、**日上方 9–15° 玫瑰带 `#E7A0A0` → `#DD9895`、22–32° 往中天走 `#8A96B6` → `#B3ACC5`**（美术预审 r0 #1：原来这里是近白的粉，再翻到 8-ii 的下半球）、背日低空 `#7E88AE`。
- 地影带和金星带 / 玫瑰带用地平线带给，增益压低到紫 ≤ 2%（现在最大 0.39%）。

---

## 7. 参考图怎么来的（和 Unity 是同一套数学）

`Tools~/render/shader_cpu.py`：把仓库里原样的 `LanbaiVR.cginc`、`LanbaiSky.cginc`、`LanbaiSkyLayers.cginc` 拼上 Unity 桩，用 slangpy 编成 CPU 计算程序，一个像素一个方向地跑 `LanbaiSkyColour()`。立方图用经纬图模拟（Unity 的经纬图约定：u = 0.5 − atan2(z, x)/2π，v = 1 − acos(y)/π），mip 3 用一份模糊过的副本代替。然后 `grade.py` 加 bloom、过调色套件的引擎（`Grading/Tools~/inputs/grades_engine.json`，也就是套件实际写进 profile 的参数）。

---

## 8. 和圣经的出入（请总导演看）

1. **地平线带**：圣经只给了 `_ZenithTint / _HorizonTint` 两个乘色。选定的晨 HDRI 里**没有地影带和金星带**，乘色拉不出来，所以加了两条可调的带，效果是“很淡”的那一种（第 6 幕的淡紫规则）。
2. **紫色护栏**：暮 HDRI 背日方向本身是蓝紫，乘色压不住局部；护栏是 shader 里的一行，只动“偏蓝而红接近绿”的颜色。
3. **背日 45° `#AFC4E0`** 拟合到 `#95B2D3`（§6；D-18 让本地按 8K 再校）。
4. **星**：8 404 颗（BSC 到 6.5 等），带内外密度比 1.67（星表真数，D-18：保持）；银河带的对比由 Gaia 图给。
5. **晨的太阳**：方位 +30°（D-12，车门里），日盘直径 0.53°（D-18），**仰角 5.8°**（D-12 写 +6°：仰角跟着 HDRI 自己的太阳走，差 0.2°，改成 6.0 会让程序化日盘和 HDRI 的光不同心）。HDRI 自己的日斑用 `_SunRemove` 的**补图模式**去掉（圆内按同一仰角在圆的左右两边插值，保住天的上下渐变，没有盘、没有环、没有放射线），日盘 `#FFCE9E @ +3.05`；1080p 1:1 截图和量的数在 `Docs~/presets/dawn_sun_1080_*.png / .json`（日心比 0.5° 处高 20.7 码值，VR −0.6 EV 时 36.8）。
6. **天顶过渡的形状**：圣经只给了各高度的颜色；“往天顶的渐变终点在 90°、中天 → 天顶在对数空间混合”是我为了天上没有圆盘 / 靶心定的（总导演 r1 阻断 2）。代价：晨的背日 45° 离目标多远见第 3 条。
7. **D-06 的 L\* ≤ 12** 是我的读法（§4），请总导演确认。
8. **月面填值** `#F0F5FF @ +2.17`（calib 是 +1.67）：月面贴图平均反照率 < 1，提 0.5 EV 后月心读到 `#E0E7EF`。
9. **与评审的分歧**：第 1 轮见 `Docs~/review_response_r1.md`；第 2 轮（总导演、总工程师、美术预审）见 `Docs~/review_response_r2.md`。**D-09（第 8 幕带车厢 VR ≤ 150）**：标准台 `Engineering/render_harness` 的 `vr_left_fwd` 机位 + `bible_v2` 车壳、S8 调色、天空 = 这里的预设当世界：8-i（t 940）**VR APL 79.6**（圣经 78.4）、8-ii（t 960）**81.6**（圣经 81.6），都 ≤ 150，紫 0%，`_OtherGain` 不用降（数也写在 `SkyPresets.json` 的 `measured_views.vr_cabin_bible_v2`）。

---

## 9. 检查

```
bash Common/Tools~/compile_check/setup.sh                                         # 一次
~/bpy/bin/python Common/Tools~/compile_check/check_shaders.py Sky Act09_StarSea Common/Shaders/LanbaiSky.cginc Common/Shaders/LanbaiFog.cginc
bash Common/Tools~/compile_check/check_cs.sh Sky Act09_StarSea
~/bpy/bin/python -I Sky/Tools~/compile_check/check_gate_equivalence.py            # 第 4 幕：门的光带 = LanbaiHorizon
cd Sky/Tools~/render
~/bpy/bin/python make_presets.py        # 预设 + 每个视向的 APL / 紫 / 梯度自检 + 一个材质的逐像素核对
~/bpy/bin/python check_stars.py         # D-06
~/bpy/bin/python test_sequence.py       # 预设按片子顺序回放、淡变规则
```
结果：shader 0 错误 1 警告（`_Udon_StarShape` 由我自己声明，D-18 允许，等并进 `LanbaiGlobals.cginc`）；C# 0 错误、lint 干净；门光带等价 1.2e-7；8 个预设梯度自检全过、一个材质逐像素 0 差、紫最大 0.01%、紫带（h 285–330、C\* > 8、L\* > 40）晨 / 暮 / 蓝时全是 0%；D-06 通过；序列测试通过。**都不等于 Unity 编译过**；U# 里 `RenderSettings.skybox / fogColor / ambientLight` 的赋值和 `VRCShader.SetGlobalTexture` 是否在 Udon 白名单里要本地确认（`ownsSkybox / ownsAtmosphere` 默认关，关着就不调）。

---

## 10. 诚实的已知弱点

- 参考图里的 HDRI 是 1024 × 512 的缩略版（本地原图 8K / 16K），所以天看起来软；颜色和布局才是要对照的。
- **Unity 经纬图导入的方位约定**我是按 `Skybox/Panoramic` 的公式假定的；`Build Sky` 在原图上量太阳，报告里的方位就是对齐用的——如果本地看到太阳不在车门里（+30°），请把报告和截图推回来。
- 银河是 Gaia 的照片重新上色的；Gaia 图本身是“恒星的光”（不是天文摄影里那种把气体和尘一起拍进去的长曝光），所以银心比长曝光照片稍“干”。640 px 陌生人测试的结果在 `Docs~/review_art_r2.md`。
- 晨的地平线以下是粉棕（h 40–58），有 HDRI 带来的淡竖纹，第 6 幕被云原盖住；8-i 地平线以下是这片天的镜像（暗一些），往天底变暗。
- 暮日右边约 2° 的地平线上有一道 HDRI 自己的亮度边（余晖的核结束处），本地 8K 里看。
- 星点的亮度标定（`_StarScale`、`_MagSlope`）要等第 9 幕按 F13 那一帧的截图定。
