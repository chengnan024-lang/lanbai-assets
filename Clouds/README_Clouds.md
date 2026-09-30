# 蓝白 / Lanbai：体积云卡片（Cloud Cards）

给 Unity 主工程（Unity 2022.3 + VRChat SDK Worlds，Built-in 渲染管线）用的云海、三重天空的云。
全部是在 Blender 5.0.1 / Cycles 里用真正的体积（Principled Volume，albedo 1，前向散射，多次散射）
渲染出来再烘成带透明通道的卡片，没有用任何下载素材。

先看效果：`Renders/ContactSheet_dawn.png`、`ContactSheet_dusk.png`、`ContactSheet_moon.png`
（每张都是全部卡片按线性光叠在该预设自己的天空上）。

---

## 1. 文件清单

| 文件 | 尺寸 | 内容 / 建议用途 |
|---|---|---|
| `Cloud_Cumulus_<preset>.png` | 1024×1024 | 标准淡积云：平底、一个主穹顶、左右肩。中远景主力。 |
| `Cloud_Congestus_<preset>.png` | 1024×1024 | 浓积云：平的宽底 + 阶梯状的主塔（几个高低不同的塔顶）+ 左侧一座较矮的副塔。远景的"主角云"，少放。 |
| `Cloud_Puff_<preset>.png` | 1024×1024 | 小朵幼年积云，细节最细（体素最小）。给窗外近处飘过的云。 |
| `Cloud_Bank_<preset>.png` | 2048×1024 | 一长条连在同一个云底上的积云堤，两个高点。地平线附近的中远景。 |
| `Cloud_Strato_<preset>.png` | 2048×1024 | 层积云一片（从稍上方看，扁平的卷和缝）。云海里、巴士下方。 |
| `Cloud_Wisp_<preset>.png` | 2048×1024 | 碎积云（fractus）：一条被风撕开的长云片，纤维状、边缘半透明。贴着车窗掠过、给速度感。 |
| `CloudSea_1_<preset>.png` | 2048×512 | 云海地平线条带：柔和起伏的层积云顶，向地平线退远，远处带大气透视。 |
| `CloudSea_2_<preset>.png` | 2048×512 | 同上，更块状的云顶，远处（相机 350 m 以外）有十来座积云头冒出海面，给地平线一点尺度感。 |
| `Renders/ContactSheet_<preset>.png` | 2048 宽 | 三张总览图（dawn / dusk / moon）。 |
| `clouds_meta.json` | – | 每张图的 alpha 包围盒（UV，v=0 在底部）、平云底所在的 v 值 `cloud_base_v`、烘进去的光源方位。放 pivot / 对齐云底高度用。 |
| `Source/make_clouds.py` | – | 生成脚本（Blender 5.0.1 bpy），可完全重建以上所有图。 |

`<preset>` = `dawn`（晨）/ `dusk`（暮）/ `moon`（星夜·月光）。一共 6×3 张卡片 + 2×3 张条带。

所有 PNG：**RGBA 8-bit，直通（straight / 非预乘）alpha**，sRGB 颜色。
透明区域的颜色已经从云的边缘向外"推"满（push-pull dilation），所以无论叠在亮天还是黑天上，
边缘都不会出现黑边或白边；透明像素的 alpha 精确为 0。
卡片四周都留了边距，云不会碰到画布边缘。条带（CloudSea）的左右两端和底边做了渐隐（alpha→0），
上沿是地平线的云顶轮廓，所以多条条带可以首尾交叠围成一圈。

### 烘在图里的光照方向（用来摆放 / 镜像）

相机基本是水平看过去的（积云类略俯 0–4°，Strato 从上方 14° 俯看，条带从上方 6° 俯看），
**太阳 / 月亮都在画面右侧**：

| 预设 | 光源 | 方位（从画面正前方向右转） | 高度角 | 天空补光 |
|---|---|---|---|---|
| dawn | 金色低太阳 | 84°（右侧，略在云后） | 7° | 明亮的蓝 + 薰衣草紫（阴影面是冷的蓝紫色，整朵云是亮的） |
| dusk | 玫瑰 / 琥珀色太阳 | 72°（右后方，逆光边更亮） | 3° | 紫罗兰 |
| moon | 冷蓝月光 | 55°（右后上方，银边） | 26° | 极暗的夜空蓝 |

当场景里太阳在云的**左边**时，把这张卡**水平镜像**即可：粒子系统在 Renderer 模块里把 `Flip` 的 X 设成 1
（全部镜像）或 0.5（一半随机镜像，增加变化）；Quad 则把 X 缩放取负。镜像后光照依然合理，云本身没有"正反"。
云海条带视角很宽（约 62°），所以光照在条带里是变化的：左端背着太阳（看到的是被照亮的云面），
右端朝着太阳（看到的是背光面，偏暗）。围成一圈时，让朝向太阳的那一段用"右端"、背着太阳的那一段用"左端"
（需要时镜像），光照就连贯。

---

## 2. 贴图导入设置（Texture Import Settings）

| 项 | 值 |
|---|---|
| Texture Type | Default |
| sRGB (Color Texture) | **开** |
| Alpha Source | Input Texture Alpha |
| Alpha Is Transparency | **开**（我们已经做过边缘颜色扩张，这里再开一次也无害） |
| Wrap Mode | **Clamp** |
| Filter Mode | Trilinear（Aniso 1–2 就够） |
| Generate Mip Maps | **开**（远处的云必须要 mipmap，否则 VR 里会闪） |
| Mip Maps Preserve Coverage | 关 |
| Max Size | 方卡 1024；宽卡 / 条带 2048（远景可以降到 1024） |
| Compression（PC） | High Quality → **BC7**（软渐变用 DXT5 会出色带） |

显存估算（BC7 含 mip）：方卡约 1.4 MB，宽卡约 2.8 MB，条带约 1.4 MB；三套预设全部导入约 45 MB。
如果一个场景只用一套预设（比如"星夜"段只用 `_moon`），只需加载那一套。

---

## 3. 推荐着色器

卡片已经把光照、颜色、调色全部烘进去了，**请用不受光（Unlit）的透明着色器**，不要用 Standard / Lit。

VRChat 世界工程一律是 **Linear 色彩空间**。在 Linear 下，材质上的 Color 属性（Tint / Color）的 RGB 会先被
Unity 从 sRGB 转成线性值再进 shader（alpha 不转），下面的数值都按这个算好了。

1. **首选：`Particles/Standard Unlit`**（Built-in 自带，VRChat 可用）
   - Rendering Mode = **Fade**，Color Mode = **Multiply**，Albedo 颜色保持白色 (255,255,255,255) = 原样。
   - 打开 **Soft Particles**（Near 0 / Far 按第 4 节，单位是米）和 **Camera Fading**
     （近平面淡出，VR 里云贴脸时很重要，建议 Near 1 m / Far 4 m）。
   - 想整体压暗 / 淡入淡出：改粒子的 Start Color 的 RGB / A（或材质 Color）。
2. 或 `Legacy Shaders/Particles/Alpha Blended`：
   - 这个 shader 内部把 Tint ×2。**在 Linear 工程里默认的 Tint (128,128,128,128) 不是原样**：
     RGB 0.5 被转成线性 0.214，×2 后只剩 0.43，云会整体暗一半多。要原样，把 Tint 设成
     **RGB (188, 188, 188)、A 128**（188/255 = 0.735 → 线性 0.5 → ×2 = 1；alpha 不转换，0.5 ×2 = 1）。
   - Soft Particles Factor 是"每米"的倒数：淡出距离 ≈ 1 / Factor 米（见第 4 节）。
3. 我们**没有**附带预乘（premultiplied）版本；不要用 `Alpha Blended Premultiply`，
   直通 alpha 用上面两个就对。

调暗的对照（Linear 工程）：想让云亮度变成原来的 60–75%，Standard Unlit 的 Color 设成 RGB 203–225 灰；
Legacy 的 Tint 设成 RGB 149–164 灰（alpha 都不动）。

后期处理（Post Processing）：卡片是已经色调映射过的显示值（Khronos PBR Neutral 映射）。
如果场景后期用了 ACES 色调映射，云会再被压一次、偏暗偏饱和：后期改用 Neutral 映射最好；
或者把云的亮度提到原来的 1.2–1.4 倍（Standard Unlit 的颜色最大就是 1、提不上去，这时用 Legacy shader，
Tint 设成 RGB 203–218 灰）。
Bloom 阈值建议 ≥ 1：卡片都是 LDR（≤ 1），只要不把亮度推到 1 以上就不会泛光。

---

## 4. 软粒子、排序与 VR 过度绘制（overdraw）

**软粒子**：云卡和巴士、触手、云海平面相交时，没有软粒子会出现硬切线。软粒子需要相机深度图；
VRChat 世界里常用的做法是放一盏开了阴影（Hard Shadows）的实时 Directional Light（强度可以很低、
Culling Mask 只选一个空层），这样 `_CameraDepthTexture` 会生成。两个 shader 的软粒子还都要求画质设置里的
Soft Particles 开关打开（VRChat 里由客户端的画质设置决定），所以请进客户端实测一下交界处。
淡出距离的填法：
- `Particles/Standard Unlit`：Soft Particles 的 Far Fade 直接填米数（Near 0）。
- `Legacy .../Alpha Blended`：Soft Particles Factor 是**倒数**，淡出距离 ≈ 1 / Factor 米
  （范围 0.01–3，所以最长约 100 m）。**数值越小越软**。
- 建议：远景大卡和条带与云海平面相交处 20–100 m（Legacy Factor 0.01–0.05）；
  近景 Puff / Wisp 贴着巴士 1–3 m（Legacy Factor 0.3–1）。

**排序**：
- 地平线条带 `CloudSea_*`：做成一个大圆环（圆柱面）上的若干 Quad，半径 1500–4000 m，
  相邻条带左右重叠约 15%（两端本来就是渐隐的），Render Queue 设成 `Transparent-20`（2980），永远在最后面。
- 远景云卡（Cumulus / Congestus / Bank）：一个粒子系统，Sort Mode = **By Distance**，Render Queue 2990。
- 近景（Puff / Wisp / Strato 贴窗）：另一个粒子系统，Render Queue 3000，Sort Mode = By Distance。
- 分成"远 / 近"两个系统，比一个系统里混排更稳定，不会前后跳。

**VR 下的 billboard**：Particle System Renderer → Render Mode = Billboard，
Render Alignment = **Facing**（朝向相机位置而不是相机平面，头一转云不会"跟着转"），关掉 Allow Roll。
远处的大云也可以直接用固定朝向的 Quad（更稳），只要大致朝向巴士即可。
Max Particle Size：默认 0.5 会把贴近的大云"缩小"，近景系统请调到 2–4。

**Overdraw（VR 最大的开销）**：
- 同一像素上叠起来的大面积半透明卡尽量 ≤ 3–4 层；满屏的近景云一次最多 1–2 张，快速掠过即可。
- 近景 Wisp 本身就是半透明的，用它做"穿云"效果比堆很多 Puff 便宜得多。
- 远景用少量大卡（每张 200–400 m 宽）比大量小卡便宜；条带一圈 6–10 个 Quad 足够。
- 给近景系统开 Camera Fading，云贴近镜头时淡出，避免满屏全透明像素。

**建议尺寸（世界空间）**：Cumulus 卡 120–300 m 宽；Congestus 150–400 m；Bank / Strato 300–800 m；
Puff 20–60 m（窗外近景）；Wisp 40–150 m；条带高度 ≈ 宽度 / 4。
积云类卡片（Cumulus / Congestus / Puff / Bank）都有一条水平的平云底，它在图里的位置写在
`clouds_meta.json` 的 `cloud_base_v`：做 Quad 时把 pivot 放在这条线上，所有云放在同一高度，
就会形成统一的"凝结高度"，天空一下子就像真的。（Strato / Wisp / CloudSea 没有平云底，这个值只是不透明部分的下沿。）
条带 `CloudSea_*` 的上沿是地平线：把条带的上沿放在视平线（或略低一点），远处的云海已经带了大气透视（越远越接近天空色）。

---

## 5. 怎么重新生成（Blender 5.0.1 API）

`Source/make_clouds.py` 是一个独立脚本，用 Blender 当 Python 模块运行（`pip install bpy==5.0.1`
或 Blender 5.0.1 自带的 Python），只依赖 numpy / scipy / Pillow：

```
python3 make_clouds.py                                  # 全部：6 种云 × 3 预设 + 2 条带 × 3，外加总览图
python3 make_clouds.py --only Cumulus Puff --preset dusk # 只重做其中几张
python3 make_clouds.py --only 1 2                       # 只重做两条云海条带（名字 1 / 2）
python3 make_clouds.py --sheets                         # 只重新拼总览图 + clouds_meta.json
python3 make_clouds.py --test --only Bank               # 快速低清预览（约 0.45 倍分辨率、32 采样）
python3 make_clouds.py --keep-exr                       # 同时把线性 EXR 留在脚本旁的 exr/ 目录
python3 make_clouds.py --repost                         # 不重渲，只用留下的 EXR 重做 alpha / 调色 / 大气透视
```

也可以用 Blender 5.0.1 本体后台运行：`blender -b -P make_clouds.py -- --only Cumulus`
（Blender 自带 numpy，但不带 scipy / Pillow，需要先用 Blender 自己的 Python 装：
`<blender>/5.0/python/bin/python3.11 -m pip install scipy pillow`）。
选项：`--out 目录`、`--samples 40`、`--bounces 14`（体积反弹次数）、`--scale 0.5`、`--keep-exr`、`--repost`。
第一次运行会生成噪声缓存 `cache/noise_128_7.npz`（约 20 秒），之后复用；固定随机种子，结果可复现。
实测（4 核 CPU，同时还有别的渲染在跑）：1024² 每张 3–5 分钟，2048×1024 每张 4–9 分钟，
2048×512 条带每张 8–17 分钟（看同时有多少别的渲染），全部 24 张约 2.5–3.5 小时。
`--repost` 重做全部 24 张的后处理约 5 分钟。

脚本结构（改外观从这里下手）：
- `PRESETS`：每个预设 = 一个太阳灯（颜色、强度、方位、高度）+ 一个自己设计的渐变天空（天顶 / 向阳地平线 /
  背阳地平线 / 地面反光 / 太阳光晕）+ 色调映射曝光。
- `SHAPES`：每种云的形状函数。云的密度场用 numpy 生成：分层的球体 SDF（主体 → 花椰菜穹顶 → 更小的穹顶），
  平的凝结云底，Worley 噪声做的"鼓包"位移，Perlin 噪声做的毛边和碎丝；然后通过一个只有顶点的网格 +
  几何节点 `Volume Cube`（Sample Index）变成真正的体积网格交给 Cycles。
- `postprocess()`：读线性 EXR（预乘）→（只对条带）大气透视 + 两端 / 底边"散开"（渐隐区里云之间的暗缝
  先变透明、被照亮的云顶留得最久，所以边缘跟着云的形状散开，而不是一个几何的圆角矩形渐变；参数在 `ERODE`）
  → alpha 做一次引导滤波（guided filter）：以降噪过的颜色和轻微平滑的 alpha 为引导，把 Cycles 没降噪的
  alpha 回归到颜色上（半透明区的颗粒和薄边"灰尘"噪点都去掉，轮廓不变软）→ 反预乘 → 边缘颜色 push-pull 扩张，
  薄云丝的颜色只会被提亮到附近云体的颜色、不会变暗（所以黑天上没有褐色烟边，银边也保留）
  → 用场景的色调映射（Khronos PBR Neutral）→ 抖动量化成 8-bit 直通 alpha PNG。

---

## 6. 小结给主会话

- 晨 / 暮 / 月三套光已经烘好，只要按段落换贴图（或两套交叉淡入淡出），不要再给云打光。
- 条带围地平线、宽卡做中景、方卡做主角、Puff / Wisp 贴窗掠过，这是最省也最像真的组合。
- 月光预设的逆光银边和触手之门的冷蓝轮廓光是同一个方向感，放在触手那一段会很协调。
- 月光下的云海条带（`CloudSea_*_moon`）是从上方被月光照亮的云顶，比单朵月光云卡亮很多（这是对的）；
  在触手 / 裂口那一段如果它抢了紫色光晕的戏，把条带亮度压到原来的 60–75%（数值见第 3 节"调暗的对照"），
  要更暗就再往下调。
- 自检：每张卡都叠在亮天（0.80, 0.87, 0.96）和近黑天（0.015, 0.02, 0.04）上检查过边缘，包括 3 倍放大的轮廓裁切，
  没有黑边或白边；薄云丝在黑天上呈现为暗淡的薄纱（这就是真实的云边），不是描边。

### 复查后改动（verify pass）

- `Congestus`：换了形状。旧版在塔顶放了一个比"脖子"还宽的头，看起来像一只坐着的小熊；
  现在是阶梯状的主塔 + 较矮的副塔，塔顶都在塔身宽度以内。三套预设都重渲了。
- `dawn` 预设：天空补光 ×3（更蓝、更偏薰衣草色），太阳 30 → 26。旧版阴影面是发闷的褐紫灰
  （云体中位像素约 (70,51,63)），现在是冷的蓝紫色、整朵云是亮的。全部 `_dawn` 都重渲了。
- `CloudSea_2`：原来离相机很近的那座积云塔去掉了（所有积云头都在 350 m 以外）；体积网格加高，
  积云头的顶不再被网格顶（z = 44 m）削平。三套预设都重渲了。
- 后处理：alpha 改用引导滤波（Wisp 等半透明区的颗粒没了）；条带两端 / 底边改成跟着云散开。
  全部 24 张都用新的后处理重出了。
- 第 3、4 节：Linear 色彩空间下 Legacy 粒子 shader 的 Tint 数值、Soft Particles Factor 是倒数，都改正了。
