# 海套件 · 技术独立评审 第 1 轮

审的版本：`pkg/sea` HEAD `dc4979b`（评审开始时是 `9b693ca`，中途 dc4979b 推上来：紫色护栏改成“旋转 + 压色度”、挪到 frag 末尾对所有模式生效；下面的行号都按 dc4979b）。
范围：`Sea/Shaders/*`、`Common/Shaders/LanbaiCaustics.cginc`（连同它 include 的 LanbaiVR / LanbaiGlobals / LanbaiFog）、`Sea/Editor/LanbaiSeaEditor.cs`、`Sea/Tools~/sea_numpy.py`（加上 `Docs~/lookdev/scene_kit.py` 里调它的地方）、两份 README、`总工程师意见.md`。
跑过：`check_shaders.py` → 10 文件 82 单元 0 错 0 警（DXC，不是 FXC）。每条下面的结论我都对着代码核过；不确定的写成“建议”。

---

## 一、必须改

### 1. 第 8 幕天花里的宫殿金点会被不透明内盘挡住，到 956.36 换材质那一帧突然冒出来
- `README_Sea接口.md:147`：`PalaceSpecks_Points` 放在天花**上方** 40–200 m（从车里看，在天花平面后面）。
- `LanbaiSeaEditor.cs:151`：内盘 `M_08_SeaCeiling` 是不透明的（队列 2000、`_ZWrite 1`）。
- `Lanbai_SeaSpecks.shader:30-32`：金点 Queue Transparent-5、默认 `ZTest LEqual`。
- **失败场景**：922.36 → 956.36 这 34 秒里，内盘写了深度，金点的每个像素都过不了深度测试，**一个都看不见**（参考图 `26_K4_r08`、`28_K4_r09` 里 25 个金点是看得见的）；956.36 内盘换成 `M_08_SeaCeilingFade`（ZWrite Off），这一帧 20–30 个金点以满亮度同时出现（此刻 p = 0，还没开始走），是一次突跳。外环那一圈（透明）里的金点倒是看得见，所以会是“只有地平线附近有金点”。
- **改**（总控 §3 禁止 ZTest Always）：(a) 金点放到天花平面**下方**（眼睛这一侧，离平面 0.5–2 m，按角大小缩放），在 shader 里用 `_CeilingMode` 按原来的距离算衰减；或 (b) 金点画进天花 shader 本身（20–30 个点，循环或小纹理）；或 (c) 内盘保持透明（违背总工程师 #6 的省钱）。选一个写进 §2.4 / §4。

### 2. `Lanbai/Sea` 没有 `_FogCap`、`_FogHeightFalloff` 属性，但 README 要云给天花设 120 m 高度衰减
- `LanbaiFog.cginc:160` 的用法说明要求把这两个写进 Properties；`Lanbai_Sea.shader:14-83` 没有，`LanbaiSeaEditor.cs` 也没写它们。
- `README_Sea.md:53`：“天花材质要用 LanbaiFog 的高度衰减（约 120 m），否则暖色的雾会把头顶的深蓝水染紫”。
- **失败场景**：云会话打开 `M_08_SeaCeiling` 的 Inspector 找不到这一项；不设 = 0 = 均匀雾 = README 自己预言的“深蓝染紫”（D-17）。
- **改**：Properties 加 `_FogCap ("Fog Cap", Range(0, 1)) = 1`、`_FogHeightFalloff ("Fog Height Scale m  0 none", Float) = 0`；`CeilingCommon()` 里按 README 写 120；三张天花材质（内盘 / 外环 / 溶化）一致。

### 3. 顶点着色器“搬家”的网格没有约定 bounds：会被视锥裁掉
Unity 按网格自己的 bounds（顶点原位置）做视锥裁剪，shader 里把顶点挪到别处不更新它。
- `Lanbai_SeaDome.shader:14,49`：“Mesh: any closed sphere (Unity's built-in sphere is fine); its scale and position are ignored”。内置球半径 0.5 m。**失败场景**：穹顶物体放在车原点（0,0,0），眼睛在 (0.55, 1.70, 2.05) 朝 +Z 看——0.5 m 的包围盒在身后，整个穹顶被裁掉，水下看到的是天空盒（或黑）；一回头又出现。
- `Lanbai_SeaParticles.shader:13-14,110`：SEED 的 POSITION 是“水的坐标系”里的固定点，画在 `pos − _Udon_SeaBus`。车前进 / 下沉 430 m 以后，网格 bounds 还在原来的水坐标里，渲染位置早已不在那里 → 随朝向整批消失。TRAIL 顶点往后挪 `vel × age`（最多 3.5 m/s × 3 s），超出船体 bounds。
- `Lanbai_SeaShaft.shader:9-10,271`：4 个顶点都在中心点，bounds 只包住 16 个中心点，40 m 长的光柱伸出去 20 m。
- **改**：在网格契约里写明（Act07 的生成器做）：`mesh.bounds` 设成覆盖实际绘制范围（穹顶：transform 缩放到 ≥ 2 × `_Radius`，shader 本来就只用 `normalize(v.vertex)`；粒子 / 光柱：以车为中心 ±300 m 的盒）。README 的“scale and position are ignored”改掉。

### 4. 车外的海雪 / 种下的光 / 荧光 / 光柱画在车厢玻璃之后
- `Lanbai_BusGlass.shader:67`（Rain）：Queue Transparent（3000）、ZWrite Off。
- `Lanbai_SeaParticles.shader:49` Transparent+10（3010），`Lanbai_SeaShaft.shader:30` Transparent+5（3005）。（天花 2990、金点 2995 是对的。）
- **失败场景**：第 7a 透过车窗看海雪：玻璃先画（带车厢灯的反射 / 着色），雪后画，预乘混合把玻璃的反射盖掉、也不吃玻璃的着色——雪看起来贴在玻璃前面；加法的光柱不被玻璃衰减，比透过玻璃应有的亮。
- **改**：车外的种类（SNOW、SEED、TRAIL、光柱）放到 2980–2995；只有“贴在玻璃上 / 车厢里”的气泡留在 > 3000。粒子材质按种类设 `renderQueue`（生成器或材质菜单里做）。

### 5. “平移对 576 m 取模”和宏遮罩（1 500 m）、Gerstner（60 / 37 / 23 m）不兼容
- `README_Sea接口.md:124`：驱动对 576 m 取模后写 `_Udon_SeaClock.yz`。`LanbaiSea.cginc:115` 宏遮罩 `q / _MacroTile`（1 500 m），`:101-103` Gerstner 相位 `k·dot(d, q)`（576/60 = 9.6、576/37、576/23 都不是整数）。
- **失败场景**：第 11 幕倒挂的海（`_GerstnerAmp` 打开，车在路上走），平移每过 576 m 取一次模，三个长浪的相位和宏遮罩整片跳一次——头顶整片“灯在浪上的光”同时换位置。第 7 幕不触发（`act07_motion.fwd` 最多 307 m）。
- 顺带：取模的理由不成立。平移 5 km 时 float 的间距 ≈ 0.5 mm，对 9 m 平铺是 5e-5 uv（约 0.05 texel），几十 km 内都不会抖。
- **改**（选一）：(a) 不取模（或按 ≥ 20 km 才取）；(b) 宏遮罩平铺改 1 152 / 1 728 m，Gerstner 波长改 64 / 36 / 24 m（576 的约数），numpy 同步改。

### 6. 参考图和材质生成器的天花边宽不一致
- `scene_kit.py`（K4）：`DiscCenter=(0, 0, 2700, a.get('band', 800))`，`26_K4_r08` 的 note 也写“edge band 800 m”。
- `LanbaiSeaEditor.cs:171`、`README_Sea接口.md:94`：500 m。
- **失败场景**：Unity 里出来的天花边缘比定稿的图硬，而且和“参考图用 numpy、所以图就是 shader 算的”这条承诺对不上。
- **改**：定一个数，生成器、README、scene_kit 的默认值三处一致。

---

## 二、建议

**数学 / 数值**
1. **FFT 法线的斜率符号反了**（`LanbaiSea.cginc:121,127` 和 `sea_numpy.py:225,229` 一样）。贴图存的是 `n_ts = normalize(−dh/dx, −dh/dz, 1)`（`make_sea_textures.py:15,97`），所以 `n.xy / n.z = −dh/dx`；代码把它当成 `+dh/dx`，再算 `(−s.x, 1, −s.y)`，得到的是 `(+dh/dx, 1, +dh/dz)`，等于把 FFT 的浪 h 取反。高斯海统计上看不出来，但 Gerstner（`:123`，`+dh/dx`）和 FFT 在第 11 幕的符号相反，注释也是错的。改 `s = −(…)`，或者把注释改成“FFT 的高度场取反，无所谓”。numpy 是一致的，所以这条不算移植错。
2. **各向异性 4 和 Toksvig 的 mip 估计不一致**：`LanbaiSeaLod`（`:79-83`）按最大轴估 mip（和 numpy 的三线性一样），但导入设置是 `anisoLevel = 4`（`LanbaiSeaEditor.cs:27`），硬件在掠射时取的 mip 更细。结果是贴图里已经留了一部分斜率，shader 又把同一部分当“未分辨”加进 α²（重复计算）；而且第 6 幕从 2.6 km 高处看出去，近地平线全是掠射，Unity 和参考图就差在这一带。可以给 SeaN_ 关各向异性，或者用 `tex2Dlod(uv, LanbaiSeaLod(uv))` 让采样和方差用同一个 mip。
3. **溶化的 EV 线性按雾前的颜色解**：`LanbaiSeaCeiling` 的 `LanbaiLuma(c)`（`:415`）用的是雾之前的 c；frag 之后还有 `LanbaiApplyFog` 和 `LanbaiPurpleGuard`（`Lanbai_Sea.shader:153-155`）。天花要开 120 m 高度衰减的雾（必须改 2），屏幕上真实的亮度曲线就偏离 EV 线性。`k5_dissolve_ramps.py` 的 PASS 是不带雾测的。建议把雾量传进去，用雾后的 Lc 解，或者带雾重跑 K5。
4. `_Udon_ReflCube_HDR` 没设时 `DecodeHDR` 返回 0（CGIncludes 2022.3 `UnityCG.cginc:515`：`decodeInstructions.x * …`）：反射全黑。`_Udon_ReflExposure` 有“0 当 1”的兜底（`:52`），HDR 参数没有。建议同样兜底：`.x <= 0` 时用 (1, 1, 0, 0)；Rain 的 README 写了“不填就是黑”，海的 README 没写。
5. `LanbaiSeaBelow:284` 的 `cond ? LanbaiSeaCube(...) : 0` 在 HLSL 里两边都会求值，7a 每个像素白白多采一次立方图。改成 `[branch] if`。
6. `_CalmPatch.z = 0` 时 `smoothstep(0, 0, pd)`（`:117`）除以 0；saturate 之后不出 NaN、w = 0 时也被乘掉，但和 numpy 的 `max(cp[2], 1e-3)`（`sea_numpy.py:222`）不是逐行对应。照 numpy 加上 guard。
7. `LanbaiOklabToLin` 的 `max(…, 0)`：护栏把高色度的蓝转到 252° 时可能出色域，负的通道被截成 0，色相会被推偏。现在所有模式都要过护栏，建议在 K2 / K3 的图上统计一下截掉的像素数。

**性能（第 7b 幕 6.4 ms 热点）**
8. **`Lanbai_SeaDome.shader:56` 的 `discard`**：一个 ZWrite On 的不透明 shader 带了 discard，多数 GPU 就关掉 early-Z。穹顶在 Geometry+450、宫殿后面画，被宫殿挡住的每个像素照样要跑 `LanbaiHorizon` 和抖动（约 250 ALU）× 两眼。驱动本来就会开关 renderer，把 discard 删掉。
9. **第 7b 的 BELOW 水面在 236–430 m 头顶，雾已经饱和**，但每个像素仍要做 3 次 2D 采样、3–4 次立方图采样、护栏和雾。建议驱动在深度超过约 100 m（雾 > 0.999）时关掉水面 renderer，或者在 shader 开头按雾量 `[branch]` 提前返回（这时法线采样要换成 tex2Dlod / grad）。
10. 光柱、粒子的透明 FSE 没有报（圣经 §1.9：持续 ≤ 4、玻璃 0.7 要算进去）。总工程师 #6 要的“天花在主机位的实测 FSE”也还是“随第 7 幕的包给”，属于没完全关掉。
11. 粒子 / 光柱的雾是逐像素算的（`LanbaiFogAmount` + `LanbaiHorizon`）。`LanbaiFogVertex` 就是为这种情况写的，可以挪到顶点。

**渲染状态 / 接线**
12. 溶化的 `_DissolveTime` 是材质属性，驱动每帧要写三处：`M_08_SeaCeilingFade`、`M_08_SeaCeilingEdge`、金点材质。README §4 只写了一处。建议改成一个全局量（`_Udon_SeaDissolve`，登记），或者在 README 里列清三处。
13. ABOVE 模式算了 `col.a = LanbaiSeaDiscAlpha`（`Lanbai_Sea.shader:151`），但 ABOVE 材质是 `Blend One Zero`，`_DiscCenter` 的软边在 ABOVE 下不起作用。要么注明“ABOVE 只能无限”，要么 ABOVE 设 `_DiscCenter` 时也走透明。
14. 顶点压缩（总控 §6 第 8 条）：SEED 的出生时刻放在 UV2.x（558–645 s）。UV 被压成 half 的话精度是 0.5 s，出生会对齐到 0.5 s 的格子上。README 里要写明“UV0–2 不压缩”。
15. 粒子 / 光柱 shader 没有 `"DisableBatching"="True"`。它们用 `unity_ObjectToWorld` 取原点和轴（`Particles:139`、`Shaft:265-266`），被静态合批后这个矩阵变成单位矩阵。
16. `LanbaiSeaEditor.cs:68` 的 `maxTextureSize = 1536` 不是 2 的幂，Inspector 的下拉框会显示成空。256 的面用默认的 2048 就行。`:104` 用 `System.IO.Directory.CreateDirectory` 建了文件夹，紧接着 `AssetDatabase.CreateAsset`，个别版本会报“folder not found”；稳妥的做法是 `AssetDatabase.CreateFolder`，或者先 Refresh。
17. 焦散图集的每格 256 px 之间没有留边（`make_sea_textures.py:213`）。`tex2Dgrad` 解决了 mip 的缝，但双线性过滤在格子边上会混进相邻的另一帧，每 0.6 / 1.1 m 一条 1 texel × 2^mip 宽的线。车厢掠射处的 mip 高，线也宽。每格留 4 px 的边（总工程师原建议）。
18. 文档：`README_Sea接口.md:101` 写的 `LanbaiCeilingDissolve` 在 cginc 里不存在（实际叫 `LanbaiCeilingProgress`），SeaSpecks 用的也不是同一个函数，是复制的一份（`Specks:87-92`）。`LanbaiSeaGlobals.cginc` 和 `LanbaiCaustics.cginc:204` 的注释“not yet in LanbaiGlobals”已经过时（`LanbaiGlobals.cginc:394-440` 已登记），可以删掉。

---

## 三、核过、没问题的

- **SPS-I**：7 个眼睛可见的 shader 都有四个宏，frag 第一行是 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`。之后才读 `_WorldSpaceCameraPos`：Sea 的视线、菲涅耳、斯涅尔窗按每只眼算，这是对的；`LanbaiNearFade` 也在这之后。公告板（Particles、Specks、Shaft）和穹顶都朝 `LanbaiCentreEyePos()`。雾用中心眼。CRT cookie 不进眼睛，正确地跳过。
- **全局量**：所有 `_Udon_` 都带守卫，只声明一次（`LanbaiGlobals.cginc` 已登记 SeaClock / SeaLevel / SeaBus / SeaBusVel / T / Underwater / Caustics* / ReflCube* / Lamp*）。没发现重复声明（X3003），也没发现“先用后声明”（总控 §6 第 1 条）。FXC 保留字没被拿来当变量名；采样器 ≤ 7。
- **NaN / 除零**：Fresnel 的 TIR 有分支，分母在非 TIR 时不为 0。折射的 sqrt 有 saturate。EV 线性反解有 max 和分母兜底（总工程师 #1 ✓）。紫色护栏 C ≤ 1e-4 时提前返回，不会算 atan2(0, 0)。GGX 和 Smith 加了 ε。`LanbaiInflate`、`normalize` 有 ε 或兜底向量。
- **精度**：浪的 uv = (q + 漂移 × t) / 平铺，t ≤ 1 200 s 时小平铺的 uv ≤ 约 110，误差远小于 1 texel；`_Time.y` 兜底跑 2 小时也只到 uv 约 640。第 6 幕 2.6 km、40 km 圆盘的世界坐标精度够。焦散的帧号 fmod 循环正确。
- **render state**：`[Enum]` + `Blend [_SrcBlend] [_DstBlend]` / `ZWrite [_ZWrite]` / `Cull [_Cull]`，材质菜单按模式设好 `renderQueue` 和 RenderType。KeywordEnum + `shader_feature_local`：材质菜单显式 Enable / Disable 关键字，三个变体都有材质引用（M_06 / M_07a / M_08）。`M_08_SeaCeilingFade` 只被驱动引用，只要它在驱动的序列化字段里，就会被打进包。
- **导入**：NormalMap + CompressedHQ → BC5，`UnpackNormal`（RGorAG）能正确解。Caustics 用 SingleChannel Red + Uncompressed → R8。Cube EXR 是 1536×256（核了 dataWindow），`TextureShape.TextureCube` + `AutoCubemap` 认得出 6×1 横条，BC6H 覆盖设置正确；Window / SkyBehind 只采 LOD 0，卷积不影响。
- **numpy 移植**：逐函数对过 `sea_normal`、`gerstner_slope`、`fresnel`、`cube`、`above`、`refract_out`、`below`、`purple_guard`（dc4979b 的新版，scene_kit 在雾之后调，和 frag 顺序一致）、`ceiling_progress`、`ev_linear_alpha`、`ceiling_lamps`、`ceiling`、`disc_alpha`。数学一致。差别只有：numpy 没有 `_Udon_SunDir`、`_Udon_ReflExposure` 的兜底，没有 `_SunColor.a` 的判断，`_CalmPatch` 多了 guard（建议 6）。参考图参数和材质不一致的那一处见必须改 6。
- **总工程师第 1 轮 8 条**：#1 ✓（`:352-358`）；#2 ✓ 四边形 + 中心眼 + ≥ 1.4 px（但见必须改 1：第 8 幕被挡）；#3 ✓ 两块平面不并存（§5）；#4 ✓ 按 mip 的未分辨方差（各向异性的偏差见建议 2）；#5 ✓ `_ReflClamp` 2.4（我估了第 6 幕闪光峰值：解析项约 0.01，立方图 ≤ 2.4 × F，约 0.35，远低于日盘 × 0.41）；#6 △ 内盘 / 外环拆开了，FSE 实测还没给；#7 ✓；#8 ✓。

---

## 结论：**不通过**

数学和 numpy 移植是扎实的。SPS-I、全局量、NaN 这些也都做干净了。不通过的原因是“必须改”的 6 条，其中第 1–4 条都是进了 Unity 或头显以后肯定会撞上的：第 8 幕金点看不见然后突然冒出来；天花缺高度雾的属性，会被染紫；穹顶 / 粒子 / 光柱被视锥裁掉；海雪画在玻璃之后。每一条的改法都是一两行或一个约定，改完就可以过。
