# 蓝白 / Lanbai · 触手库（Tentacles）v2.1

> 写给：在小楠电脑上做 Unity 2022.3 + VRChat SDK Worlds + UdonSharp（Built-in 渲染管线）的主工程会话。
> 写的人：云端 Blender 工作间（Blender 5.0.1 当 Python 模块跑，Cycles CPU 渲染）。**我们这里没有 Unity：所有 shader 都没有在 Unity 里编译过。**
> 依据：`art/ART_BIBLE.md` **v2** 的 §1、§6·4（第 4 幕 · 触手之门，含「触手 shader」一条）、§6·4c、§8.1 #5（触手 v2）；
> 以及 v1 的两份验收 `tentacles/verify_art_v1.json`、`verify_tech_v1.json`（逐条处理见第 13 节）。
> **v1 的交付原样存档在 `_v1/`**（FBX、贴图、shader、README、三张渲染）。

> **门第 8 轮（refine round 4，2026-10-02，最新）——与本库有关的只有这些：**
> - 门的触手 shader 升到 **`gate/Shaders/Lanbai_TentacleSway.shader` v2.7**，天空 / 雾色改用同目录的 **`LanbaiGateSky.cginc`**
>   （天空盒 `Lanbai_GateAirSky` **v3** 也包含它，所以天和远处被雾吃掉的臂是同一个颜色；技术 r4 BT-3）。天空盒挪到了 `gate/Shaders/`，
>   本目录的 v2 在 `_superseded~/Lanbai_GateAirSky_v2.shader.txt`。下文第 1 节清单里的 `Lanbai_GateAirSky.shader` 是历史说明。
> - **细的部分（鞭梢）不再用主贴图**（技术 r4 B2：UV0 是保角的，鞭梢上一个贴图周期 ≈ 一圈周长 ≈ 2r，贴图里任何成行的东西都会
>   每 2r 重复一次 = 等距的环 / 珠）：v2.7 `_ThinK (0.12, 0.40)`：UVRadius < 0.12 的地方法线 / 光滑度 / 反照率 → 平滑的
>   `_ThinSmooth 0.84` / `_ThinAlbedo`，只留非整数平铺的细节法线。预览材质 `Source/build_library.make_material` 加了同样的
>   `thinK`（`THIN_K`、`THIN_SMOOTH`、`THIN_ALBEDO`），本库的渲染与门的渲染一致。**本库 8 个 FBX 不变**：库里的材质 `_UseUVRadius 0`
>   时 UVRadius 读不到，`_ThinK` 设 (0, 0) 即关掉。
> - 门里的“很多小的”现在是 **`gate/GateMultitude_v2.fbx`**（12 个姿态，含镜像；36 个实例，5 簇），v1 已挪到 `gate/_r4/`。
> - 伤口高光有了远距缩放与上限（`_WoundSpecFar`、`_WoundSpecMax`）；白前面的臂变成剪影（`OverWhite()`、`_Wrap*`）。参数见
>   `gate/README_GateLayout.md` §5、§7.1。

> **门 round 4（refine round 3，2026-10-02）——与本库有关的只有这些：**
> - 门的触手 shader 升到 **`gate/Shaders/Lanbai_TentacleSway.shader` v2.6**（伤口当主光：线光源漫反射 + 管状高光 + 屏幕空间伤口轮廓
>   `_RimWound`；噪声在云海坐标里取样 `_Udon_GateOrigin`；实例化 `_FogCapI`；月轮廓统一用 `_Udon_MoonDir`）。对本库的 8 个 FBX 完全兼容：
>   不写 `_Udon_TearFoot / _Udon_TearTop` 时 `_TearDiffuse / _TearSpec / _RimWound` 设 0 即回到 v2.5 的样子。
> - 门里的“很多小的”现在是 **`gate/GateMultitude_v1.fbx`**（6 个规范姿态 MU0–MU5，每个 `_LOD0/1/2`，GPU 实例化 150 个），
>   不再用本库的变体做浪涌环。
> - **远潮的 v1 网格与 v2.1 图集挪进了 `_superseded~/`**（技术评审 r3 m10）：`TentacleTide_v1.fbx`（只有 4 套 UV，Tide v2.2 需要 UV4–UV6）、
>   `TentacleTide_v2.1_Atlas_A/B/C.png` + `.json`。门的远潮只用 `gate/TentacleTide_v2.fbx` + `gate/Textures/TentacleTide_v3_Atlas_A/B.png`。
>   下文提到 `FBX/TentacleTide.fbx` 与 `Textures/TentacleTide_Atlas_*` 的地方都是历史说明。

> **门 round 3 第 6 轮（2026-10-01）：远潮换图集。** 门里的远潮改用 `gate/Textures/TentacleTide_v3_Atlas_A/B.png`
> （+ `TentacleTide_v3_Atlas.json`，生成脚本 `gate/tide_atlas_v3.py`）：v2.1 图集的细长、带珠状边的“叶片”在 5–12 km 外排成一行，
> 读成地平线上的一排**草**。v3 的剪影来自门的 v4 臂形（粗根、t 0.45 起天鹅颈收细、上 1/3 弯过来向下），一半格子是 3–5 条臂的簇，
> 底部 7% 羽化。tide shader 升到 **v2.2**（UV6 `TideMist`：每片的根在自己的雾高度里化开）。本目录的 v2.1 图集只对库自己的
> `TentacleTide.fbx` 有效，不再用于门。

> **门 round 3（2026-10-01）：**
> - **shader 只有一份**：`gate/Shaders/Lanbai_TentacleSway.shader`（**v2.5**）和 `gate/Shaders/Lanbai_TentacleTide_v2.shader`（**v2.2**，第 6 轮）。
>   本目录原来的 `Lanbai_TentacleSway.shader`（v2.1）、`Lanbai_TentacleTide.shader`（v1）和旧的 `GateLayout.json`（v1）都挪进了
>   `_superseded~/` 并改名为 `.shader.txt` / `_v1.json`；`_v1/` 改名为 `_v1~/`。Unity 会忽略以 `~` 结尾的文件夹，所以把整个
>   `deliver/` 和 `gate/` 拷进 Assets 时，`Lanbai/TentacleSway`、`Lanbai/TentacleTide` 各只有一个文件声明（技术评审 M8）。
>   v2.4 对本库网格完全兼容：库里的材质把 `_UseUVRadius` 留 0（默认），`_FogExtra` 默认已改成 (1.5, 25)（加到密度倍数上，不再相乘）。
> - 门里用的是 `gate/GateArms_v3.fbx`（v4 自定义中心线的英雄臂 + 库变体，每个实例一个空物体父节点、`_LOD0/1/2` 子物体，第三套 UV
>   `UVRadius`）。本库的 8 个 FBX 不变。门的数据看 `gate/GateLayout_v2.json` 与 `gate/README_GateLayout.md`（v4）。
> - 变体 K（Engel）在 round 3 已不再使用；Engel 现在是自定义中心线 `ENG`。它的材质 `_ConvexCrease 0`、`_OcclusionStrength 0`
>   （借来的 H 褶皱遮罩会落在弯的错误一侧，技术评审 minor）。

> **门 round 2（2026-10-01）的补充——门里用的不是本库的原样网格：**
> - `gate/GateArms_v2.fbx`：门的 42 个实例各自烘好的网格（LOD0/1/2，同样的 UV0 / UVSway / 顶点色契约），形体是 v3
>   （肌肉 girth 剖面 + 22% 处的腹、t 0.58–0.70 收颈、三条螺旋肌束、1 : 0.8 椭圆截面；`gate/gate_layout.py` 的 `form_mult`、`gate_scene.variant_mesh`）。
> - 新变体 **K**（钩冠，只在门里用，作 Engel / Colossus_3）：在 `gate_layout.py` 里由 H 派生注册，贴图用 H（`TEX_KEY K → H`）。本库的 8 个 FBX 不变。
> - 触手 shader 的门版本是 `gate/Shaders/Lanbai_TentacleSway.shader` **v2.3**（实例化 `_Phase`、全局 `_Udon_TearPos`、target 4.0、
>   云顶淡出、轮廓阶梯、`_ReflectionScaleFar`、`_BandEl (12, 35, 1)`），说明在 `gate/README_GateLayout.md` §7。本目录的 v2.1 shader 不再用于门。
> - 远潮的门版本：`gate/TentacleTide_v2.fbx`（440 片）+ `gate/Shaders/Lanbai_TentacleTide_v2.shader`。

先看效果：
- `Renders/lineup.png`：八种并排、真实比例，8 m 的车做比例尺，夜空背景（v2：光雾带 → 虚空、月、裂口的靛紫辉光），左上角放大 A–D。
- `Renders/flyby.png`：车在云顶上约 46 m，从一条 F（154 m）浪头弯下的**凹侧下面 16 m** 经过：整条手臂从右下升起、在头顶拱过去、
  细线鞭垂到裂口前面；湿皮、凹侧的压缩皱、冷的月光轮廓；远处是体积云的云海、月和裂口。
- `Renders/tide_atlases.png`：远潮的三张剪影图集（用 v2.1 的新形状重新生成）。
- `Renders/gate.png`：**不是这一版的**。门的构图（`GATE`、`GateLayout.json`、gate.png）归「门」那一步负责，会用这里的新资产重排重渲；
  这一版没有动它们。旧的 gate.png 在 `_v1/Renders/`。

**这一版给主工程最重要的六条：**
1. **形状全部重做**（v1 读作角、刺、草叶、枯树）：家族更细长（长 / 根半径 ≈ 30–46）；半径曲线在身长 57% 以后**凹形收颈**，
   **87% 以后是几乎等粗的细线鞭**（根半径的 2–5%）——不再是一根锥形的尖（那就是爪、是角）；每条身上 2–3 个肌肉鼓包 + 截面不对称的肌肉起伏。
   八种**整条身体**的姿态都不同；**H 没有侧枝了**。→ 第 2 节。
2. **指尖多样**（bible §6·4）：甩直成线的鞭（A、F 带 S 形波）、半卷（C）、分叉的舌尖（E）、磨散（H 的四根细丝）、钩（B 向下、G 向侧）；
   只有 D 一个卷（出平面、卷径 0.26 L）。卷的大小、手性、平面各不相同，**绝不是一排一样的螺旋**。
3. **皮肤 v2.1（「生」）**：褶皱改成**一笔一笔的压缩皱**（错开、两端收尖的新月形、8–20° 螺旋倾角、中间有分叉的短桥），**只在凹侧**；
   凸侧绷紧、光滑，但有皮下肌束的缓起伏和细皮纹（**不是抛光橡胶**）；反照率 sRGB 30–44 带**蓝紫斑驳**；光滑度基底约 0.63、低频干湿斑、
   纵向黏液条到 0.86–0.92。**没有等距环节、没有 Voronoi、没有鳞片**。巨像 2–8 m 宏观起伏、1.5 km 外无细皱。→ 第 4 节。
4. **shader v2.1**（`Lanbai_TentacleSway.shader`）：月侧轮廓默认 0.8（bible 要的「每条近 / 中层剪影连续 1–3 px 冷边」），**按湿条纹断续**（不是贴纸描边）；
   裂口侧轮廓、细尖透射、shader 内高度雾、`_FogCap` + 高度衰减；**LanbaiFog 钩子**；细尖最小 1 px 宽度膨胀；`pow(saturate(..))`。
   **褶皱遮罩只作用于主法线，细节法线（皮纹）处处都有**——这是 v2.1 最重要的材质改动。→ 第 5 节。
5. **摇摆读 UV1（`UVSway`，float），不读顶点色**（顶点色在 Unity 里是 8 位，细线鞭会摆成台阶）；**每个实例按世界坐标加相位**，同一变体的几条不会同步摆。→ 第 3 节。
6. **导入**：Generate Lightmap UVs **关**（会覆盖 UV1）；Player → Vertex Compression **取消勾选 TexCoord0**；从 Standard 切过来后 **Smoothness Scale 设 1**。→ 第 4 节。

---

## 1. 文件清单

```
Tentacles/
├─ FBX/Tentacle_A.fbx … Tentacle_H.fbx     每个 FBX：空物体 Tentacle_X + 子物体 Tentacle_X_LOD0 / _LOD1 / _LOD2
├─ FBX/TentacleTide.fbx                    远潮：一个网格，400 个四边形（800 三角形），3 个子网格 = 3 张图集
├─ Textures/
│   ├─ T_Tentacle_Albedo.png               2048²  sRGB（八种共用，平铺）
│   ├─ T_Tentacle_Normal.png               2048²  切线空间，OpenGL（+Y = 沿触手向尖端）：压缩皱 + 皮下肌束
│   ├─ T_Tentacle_MetallicSmoothness.png   2048²  R = 金属度（全 0），A = 光滑度
│   ├─ T_Tentacle_DetailNormal.png         1024²  细节法线（皮纹：各向同性的细沟网、小乳突、毛孔），平铺 (4, 4.6)
│   ├─ T_Tentacle_A_Occlusion.png … _H_    1024²  每个变体一张，按 (U, t) 采样、不平铺：B = 褶皱遮罩，R = 巨像宏观起伏，G = 褶皱遮蔽
│   ├─ TentacleTide_Atlas_A/B/C.png        512×2048 RGBA，每张 8 个剪影（2 列 × 4 行，256×512 一格）——v2.1 新形状
│   └─ TentacleTide_Atlas.json             每一格：变体、转角、倾角、根的位置、格子高度（以臂长计）
├─ Lanbai_TentacleSway.shader              触手 v2.1（Built-in 表面着色器），见第 5 节
├─ Lanbai_TentacleTide.shader              远潮公告板（未改）
├─ Lanbai_GateAirSky.shader                （可选）这一段的天空盒：光雾带 + 月盘 + 银晕 + 稀疏星（未改）
├─ GateLayout.json                          门的摆放——归「门」那一步，这一版未改（见第 7 节：它是按 v1 的形状算的，要重排）
├─ Renders/lineup.png · flyby.png · tide_atlases.png（gate.png 见上）
├─ Source/build_library.py                  一个脚本从零重建以上全部（Blender 5.0.1 bpy API）
├─ Source/lib/                              它依赖的两个共享脚本（FBX 导出设置、v2 预览灯光）
└─ _v1/                                     v1 的全部交付（存档，不要导入）
```

---

## 2. 八种触手（一个家族，八种不同的「整条身体的姿态」）

**家族体态（v2.1）**：根部上方一圈肌肉鼓起（1.06）→ 很重的身体保持到身长 ~45%（半径 0.81）→ **57% 以后凹形收颈**（0.61 → 71% 处 0.23）→
**87% 以后是细线**（0.052 → 0.036 → 0.015 → 尖）。身上 2–3 个 ±6–8% 的肌肉鼓包 + 一处收缩，截面上 4 阶不对称的肌肉起伏（±5% / 3.4% / 2% / 1.2%），
所以剪影是一条活的、有肌肉的边，不是车床车出来的管子。中轴线按**曲率积分**出来（宽的弯，像毛笔一笔下去），弯曲往尖端越来越大（细的地方更柔）。

| 名字 | 弧长 | 根半径 | 姿态（整条身体） | 指尖 | LOD0 / 1 / 2 三角形 | v2 门里的用途 |
|---|---|---|---|---|---|---|
| Tentacle_A | 25 m | 0.70 m | **甩鞭**：细长，两道缓 S，出平面 | 最后 1/4 甩成直的细线，末端一个小反挑 | 5952 / 2000 / 600 | 近层；远潮 |
| Tentacle_B | 32 m | 0.95 m | **垂**：向一侧斜着升起，向前拱过去，末端在自重下垂到水平以下 | 一个短的猛禽钩（向下） | 5952 / 2000 / 600 | 近层；远潮 |
| Tentacle_C | 61.8 m | 1.35 m | **拧绳**：身体绕自己的轴拧 1.5 圈，**越往上拧得越开**（拧紧的肌肉，不是弹簧） | 细鞭向侧面半卷 | 5952 / 2000 / 600 | 近层；远潮 |
| Tentacle_D | 72 m | 2.00 m | **大 C + 松卷**：身体横扫一个大 C；末端卷成一个很大、敞开、出平面的卷（卷径 0.26 L），再把鞭梢甩出去。**全家唯一的卷** | 松卷 + 外甩 | 5952 / 2000 / 600 | 中层（×1.6–1.8） |
| Tentacle_E | 100 m | 2.75 m | **双 S**：身体来回折两次 | 79% 处**分叉的舌尖**：两根细线鞭像分叉的舌头分开，各卷各的 | 5976 / 1944 / 552 | 中层；远潮 |
| Tentacle_F | 140 m | 3.90 m | **浪头**：迎风前倾的长身，在 66% 处像浪一样卷过去 | 泻成一根长的细线鞭，**带 S 形波** + 末端小反挑 | 5952 / 2000 / 600 | 中层；**flyby 的那条**（×1.1） |
| Tentacle_G | 300 m | 10.0 m | **巨像 · 天鹅颈 + 辫**：向后斜着出云，升成一道长 S，把上三分之一向前甩过伤口、垂下来；一股肌束绕下半身 1.35 圈，中途离开主干（光从缝里漏过去）再没入 | 向侧面的一点钩 | 5980 / 2000 / 600 | 巨像；背景巨像 |
| Tentacle_H | 447 m | 12.5 m | **巨像 · 探**：斜着的巨柱，一边上升一边慢慢盘旋 0.85 圈，上半身向伤口探过去，几乎水平，像要伸手把它合上 | **磨散**：末端 9.5% 处散成四根细丝，各自波动、各卷各的（一根被扯开的绳，不是树枝） | 5968 / 1784 / 580 | 巨像；背景巨像 |

- 预算：LOD0 ≤ 6000、LOD1 ≤ 2000、LOD2 ≤ 600，全部满足（上表是重新导入后数出来的）。
- **剪影验收**（`python3 Source/build_library.py --only plot` → `wip/silhouettes_tips_cut.png`）：八种画成纯黑剪影、**t > 0.85 的尖端剪掉**、三个方向，
  八种一眼可分：细 S / 大拱 / 之字拧绳 / 大 C / 双 S / 前倾浪头 / 天鹅颈 + 辫 / 盘旋的探。
- 可以**等比缩放**：UV 是保角的，贴图密度随尺寸一起变。不要负缩放（镜像）：用绕自身轴的旋转换「手性」。
- 远处的细线鞭会细于一个像素：shader 的 `_MinWidthPx`（默认 1）把它撑到 1 px 宽，不会闪成虚线（第 5 节）。

---

## 3. 坐标与数据约定（shader 和摆放都靠它）

- 原点在根部截面中心；Blender 里沿 +Z 生长 → **Unity 里沿本地 +Y 生长**。单位米。导入后旋转 0、缩放 1（已重新导入核对）。
- **UV0**（`UVMap`）：U = 绕一圈 0→1（接缝在本地 −Y 一侧）；V = 沿长度，保角（dV = ds / 2πr），主贴图在 U、V 都能平铺。
  **V 以 0 为中心**（每个变体整体平移了整数圈，看不出来）：|V| ≤ 23（C 最大，其余 ≤ 18）。
- **UV1**（`UVSway`，**float 精度**）：**x = t**（根 0 → 尖 1，沿弧长），**y = 每个变体的相位**。**摇摆读它；`_OcclusionMap` 也按 (U, t) 读它。**
  - 分叉 / 磨散的细丝从分叉点的 t 继续涨到 1；G 的辫状肌束用它所缠绕的主干位置的 t，摇摆时和主干一起动。
  - 为什么不用顶点色：Unity 把 FBX 顶点色存成 `UNorm8`（256 级），鞭梢最后几个百分点的环在 t 上相隔不到 1/255，好几圈共用一个 t → 摇摆时整块转、在台阶处跳。
- **顶点色 `Col`**（线性导出）：R = t、G = 相位（8 位副本，只留给工具）、**B = 半径 / 根半径**（0 → ~1.06；尖端靛紫、细尖透射、1 px 膨胀、巨像起伏的尺度都用它；8 位足够）、A = 1。
- **相位**：每个**变体**一个（A 0.137 · B 0.853 · C 0.421 · D 0.694 · E 0.288 · F 0.566 · G 0.019 · H 0.745）；
  **shader 再按每个实例的世界坐标加一个偏移**（`frac(dot(物体位置, (0.0131, 0.0071, 0.0113)))`，GPU Instancing 下也成立），同一变体的几条不会同步摆。
- 网格：光滑法线、法线朝外（有向体积为正）、无零面积三角形；尖端闭合（扇形），根部是硬边的平盖。G 的肌束根部略低于原点（埋在云里）。

---

## 4. 导入设置与皮肤

### 模型（FBX）
| 页 | 设置 |
|---|---|
| Model | Scale Factor **1**，Convert Units **开**，Bake Axis Conversion **关**（导出时已经烘好了），Import BlendShapes / Visibility / Cameras / Lights 关 |
| | Mesh Compression Off，**Read/Write 关**，Optimize Mesh 开，Generate Colliders 关 |
| | Normals **Import**，Tangents **Calculate Mikktspace**，**Generate Lightmap UVs 关（必须：它会覆盖 UV1 = 摇摆数据）** |
| Rig / Animation / Materials | Animation Type **None**；Import Animation 关；Material Creation Mode **None**，手动指定材质 |

- `TentacleTide.fbx` 同样设置（它有 4 套 UV：UV0 图集、UV1 摆动、UV2/UV3 根的位置和偏移，**全部要保留**）。
- 触手**不要**勾 Contribute GI / Lightmap Static（UV1 是摇摆数据；触手也在动）。
- 导入后 Unity 会按 `_LOD0/_LOD1/_LOD2` 命名自动在 `Tentacle_X` 上建 **LOD Group**。
- **一分钟自检**：选 `Tentacle_A_LOD0` 的网格，Inspector 预览的顶点属性里应该有 `TexCoord1 Float32 x 2` 和 `Color UNorm8 x 4`。
- **顶点压缩**（Player → Other Settings → Vertex Compression）：**取消勾选 TexCoord0**。默认它会把 UV0 压成 half：V 到 ±23 时误差约 0.008，
  等于主贴图 16 px、细节贴图 37 px，褶皱间距会不均匀。**TexCoord1/2/3 也保持不勾**（UV1 是摇摆的 t；远潮把米制坐标放在 UV2/UV3 里）。

### 贴图
| 贴图 | Texture Type | sRGB | 其他 |
|---|---|---|---|
| T_Tentacle_Albedo | Default | **开** | Wrap Repeat，Trilinear，Aniso 8，Max 2048，BC7 |
| T_Tentacle_Normal | **Normal map** | （自动关） | Repeat，Trilinear，Aniso 8，Max 2048，BC5 |
| T_Tentacle_MetallicSmoothness | Default | **关** | Alpha Source = Input Texture Alpha，**Alpha Is Transparency 关**，Repeat，Trilinear，BC7 |
| T_Tentacle_DetailNormal | **Normal map** | （自动关） | Repeat，Trilinear，Aniso 8，Max 1024 |
| T_Tentacle_X_Occlusion（8 张） | Default | **关** | **Wrap Mode Per-axis：U Repeat、V Clamp**，Trilinear，Max 1024，BC7（不要 BC1：B 通道的遮罩要精度） |
| TentacleTide_Atlas_A/B/C | Default | **开** | **Alpha Is Transparency 开**，Clamp，Mipmap 开，Max 2048，BC7 |

Mipmap 全部要开（远处的细节靠 mip 才不会闪）。

### 皮肤 v2.1（「生」，ART BIBLE v2 §6·4 材质）
- **反照率 sRGB 30–44**（线性 0.013–0.025；实测每通道 30–44，均值 sRGB (34, 34, 40)）：蓝黑的皮上有 20–30% 的**蓝紫斑驳**——
  石板蓝和梅紫两种斑，中臂上 0.3–3 m 大小（像鲸、鳗的皮），稀疏的暗色小斑点；褶皱里、湿条纹上略深。湿皮的「墨」来自镜面，不来自反照率。
- **光滑度**：基底约 0.63，低频**干湿斑** ±0.10（0.53–0.74），**纵向黏液条**（沿 V、5–20 cm 宽、长长一段一段、会蜿蜒、边缘柔和）到 0.86–0.92；
  褶皱里略湿、皱之间的卷边略干。实测全图 0.52–0.92，均值 0.63，p90 0.74。没有任何宽于 ~30 cm 的区域光滑度恒定。
- **褶皱只在弯曲的凹侧**（被压缩的一侧）：共用法线贴图里的是**一笔一笔的压缩皱**——一行一行、行距 0.25–0.6 × 该处半径（±40%），每一行断成
  错开的几笔（每笔占周长 12–40%，两端收尖成新月形），**倾斜 8–20°（大多同一手性，像螺旋）**，每笔深浅不同（很多浅的、少数深的），两侧各一道软的皮卷，
  行与行之间偶尔有斜的短桥（皱会分叉、合并）。**哪里出现由每个变体的曲率烘焙遮罩决定**（`*_Occlusion` 的 B：凹侧 ±70° 内为 1，按弯曲的压缩量
  r/R_弯 渐强；凸侧和直段为 0）。遮罩 > 0.5 的面积：A 2%、B 14%、C 17%、D 8%、E 10%、F 3%、G 10%、H 14%。
- **凸侧**：绷紧、光滑——**但不是抛光的橡胶**：主法线里的皮下肌束（沿身体方向的长而缓的起伏）只在凹侧满强度、凸侧 6%；
  而**细节法线**（各向同性的细沟网、小乳突、毛孔，按 (4, 4.6) 平铺）**处处都有、不受遮罩**。长长的黏液亮线才读得出尺度。
- **不要等距环节、不要 Voronoi、不要鳞片**（全部没有；v1 细节法线里那些绕身体的细环纹也去掉了）。
- **巨像（G、H）**：`*_Occlusion` 的 R 是 2–8 m 的宏观起伏——**各个方向的坑和鼓包**，像湿的侵蚀玄武岩（v1 是沿身体的沟，远看成了树皮），
  shader 用 4 个采样求梯度；**1.0–1.5 km 以外细褶皱淡出为 0**；主贴图平铺 3×3（5.0）。

---

## 5. 材质与 shader

### 5.0 材质（每个变体一个，因为 `_OcclusionMap` 是每个变体自己的）
| 材质 | 用在 | 与默认值不同的设置 |
|---|---|---|
| `M_Tentacle_A` … `_F` | 近层、中层 | `_OcclusionMap` = 该变体的 Occlusion，`_VariantDims` 见下；中层实例 `_FogDensityScale` 0.25（5.3） |
| `M_Tentacle_G_Colossus`、`M_Tentacle_H_Colossus` | 巨像、背景巨像 | `_Colossus` 1，`_MacroStrength` **0.35**，`_FogCapHeight` **1600**；**`_MainTex` Tiling (3, 3)、`_DetailNormalMap` Tiling (12, 13.8)**；摆幅 0.02–0.035、频率 0.03–0.045 |
| `M_TentacleTide_A/B/C` | 远潮（TentacleTide.fbx 的 3 个子网格） | `Lanbai/TentacleTide` + 对应图集 |

`_VariantDims`（根半径 m、弧长 m，物体空间）：**A (0.70, 25)、B (0.95, 32)、C (1.35, 61.8)、D (2.00, 72)、E (2.75, 100)、F (3.90, 140)、G (10.0, 300)、H (12.5, 447)**。
（v2.1 的半径比 v1 细；**v1 的数字不能再用**——1 px 膨胀和巨像起伏的尺度都靠它。）
**巨像的主贴图平铺 3×3**：共用的皮肤按根半径保角，放到 300–450 m 的巨像上，黏液条和肌束会变成几米宽的竖纹，远看像树皮（v1 被说成「带环的树干」）。
平铺 3 以后它们回到合理的尺寸，2–8 m 的尺度交给 `*_Occlusion` 的宏观起伏。`_OcclusionMap` 按**原始 UV0.x**（不带平铺）和 t 采样，所以平铺不影响它。

### 5.1 保底：Standard（Metallic）也能用
- Albedo / Metallic（Source = **Metallic Alpha**，Smoothness 滑条 **1**）/ Normal Map / Detail Normal（Tiling 4, 4.6）照常；**不要**把 `*_Occlusion` 挂到 Standard 的 Occlusion 槽
  （Standard 用 UV0 读它，而它要按 (U, t) 读）。
- Standard 没有摇摆、凹侧遮罩、轮廓光、透射、LanbaiFog——压缩皱会在凸侧也出现（它们是一笔一笔的，不是环，所以不会读成蚯蚓，但不对），雾用 Unity 自带的。

### 5.2 推荐：`Lanbai/TentacleSway` v2.1（Lanbai_TentacleSway.shader）

> **这个 shader 是在没有 Unity 的环境里写的，没有在 Unity 里编译过。** 我们用 slang 编译器 + 一份 Unity 内置函数的桩文件，把 CGPROGRAM 部分按
> 四种 pass 组合（前向、`UNITY_PASS_SHADOWCASTER`、`UNITY_PASS_FORWARDADD`、定义了 `LANBAI_FOG_INCLUDED`）都编译过一遍：**无错误**
> （只有 slang 自己对 float→half 隐式转换的提示，PC 上的 FXC 不会报）。这只证明语法和类型没错，**不能代替 Unity 的表面着色器生成器**。请在 Unity 2022.3 里检查：
> Console 没有报错和警告（前向 pass、ForwardAdd pass 和 `addshadow` 生成的阴影 pass 都要看）；Play 时根不动、尖在摆、**细线鞭平滑不成台阶**、
> 同一变体的几条**不同步**、影子跟着摆、远处的细线至少 1 px 宽不闪；VR（Single Pass Stereo）里闭一只眼、再闭另一只眼各看一遍；远处的触手融进天空。
> 有问题就先退回 5.1 的 Standard（贴图槽名字一样，切 shader 不丢贴图）。

- **从 Standard 切过来后，把 `Smoothness Scale`（`_Glossiness`）设成 1**（Standard 的滑条改的是 `_GlossMapScale`，`_Glossiness` 会停在 0.5，光滑度就减半了），
  `_DetailNormalMap` 的 Tiling 重新设成 (4, 4.6)。
- `#pragma surface surf Standard fullforwardshadows vertex:vert addshadow finalcolor:lanbaiFog nofog`，`multi_compile_instancing`。
- **摇摆**（UV1 + `_Time`，不需要骨骼）：每一圈绕根部转一个小角度，∝ t^Stiffness，沿身体向上行进的慢波，两个平面叠加；根部不动；相位 = UV1.y + 实例世界坐标的偏移。

  | 参数 | 默认 | 建议 |
  |---|---|---|
  | `_SwayAmplitude` | 0.05 | 尖端弯曲角（弧度）。近层 ≤ 0.05，中层 0.05–0.09，巨像 0.02–0.035 |
  | `_SwayFrequency` | 0.06 | 赫兹。小的 0.08–0.12，巨像 0.03–0.045（大东西动得慢，才显得大） |
  | `_SwayWavelength` | 0.9 | 占全长的比例。0.6–1.2 像在涌动 |
  | `_SwayStiffness` | 2 | t 的指数，越大根部越稳 |
  | `_SwaySecondary` | 0.6 | 第二个平面的摆动比例 |
  | `_MinWidthPx` | 1 | 细尖最小宽度（像素）：顶点沿法线外推 max(0, ½·像素宽 − 半径)，半径 = B × `_VariantDims.x` × 物体缩放；阴影 pass 里不做 |

  **包围盒**：摇摆（和 1 px 膨胀）不在网格包围盒里，尖端最多移出「摆幅 × 长度」（F 在 0.09 时约 12 m）。近层实例摆幅 ≤ 0.05；
  屏幕边缘的近层还会「闪没」或丢影子，就用脚本把 Renderer 的 `localBounds` 每边放大 10–15%。
- **法线（v2.1 改了）**：主法线（压缩皱 + 皮下肌束）强度 = 掠射压平（`_GrazingFlatten` **0.5**，N·V 0.05–0.5）× lerp(`_ConvexCrease` **0.06**, 1, 遮罩 B)
  × （巨像）1.0–1.5 km 淡出；**细节法线（皮纹）只乘掠射压平，不乘遮罩**（`_DetailNormalMapScale` 1）。如果 Unity 里近层的边缘出现锯齿状的台阶，把 `_GrazingFlatten` 提到 0.65。
- **巨像宏观起伏**（`_Colossus` 1）：R 的梯度（U 方向 1 texel = 2πr/1024 米，r = `_VariantDims.x` × 顶点色 B；t 方向 = 弧长/1024 米）× `_MacroStrength`（0.35）叠到法线上。
- **每个变体的贴图按 (原始 U, t) 采样**：`Input.rawU` 在 vert() 里取 UV0.x（不带 `_MainTex` 的平铺），`Input.swayT` 取 UV1.x。
- **轮廓光（ART BIBLE v2 §6·4 触手 shader）**，都在雾的里面（远处自动变弱）：
  - **月侧**：`#9DB8FF × pow(saturate(1 − N·V), 5) × saturate(0.3 − N·L_月) × _RimMoon`（**0.8**）× **湿度**。湿度 = lerp(`_RimWet` 0.25, 1, saturate((光滑度 − 0.58)/0.30))：
    轮廓顺着黏液条一段亮一段暗，像湿皮在掠射角的反光，不是贴纸描边。这就是 bible「每条近 / 中层剪影都要有连续 1–3 px 的轮廓」的那一道冷边
    （v1 的 0.10 在虚空前面根本看不见，近处的巨臂就成了黑压黑）。`_RimDir` = JSON 的 `moon.direction_toward_moon`。
  - **裂口侧**：`#A99DE1 × pow(saturate(1 − N·V), 4) × 朝裂口 × 接近度 × _RimTear`（0.08），接近度 < 200 m 为 1、> 1.2 km 为 0（`_TearProximity`）；`_TearPos` = JSON 的 `tear.centre`。
- **细尖透射**：`(1 − B)² × 裂口光 × #5B57A1 × _TipGlow`（**2.2**，v1 是 4.5，会发出电蓝色），只在细处、朝裂口的一侧、裂口在它背后时——细鞭像逆光的耳朵一样**微微**透光。
  「细处」按**相对半径**算：B = 半径 / 根半径 < 0.10 时满强度、0.35 以上为 0（`smoothstep(0.10, 0.35, B)`）。所以它是一个**比例**，不是米：
  A 上是半径 < 7 cm，H 上是半径 < 1.25 m。
- **尖端靛紫**：B < 0.22 处反照率 × `_TipTint`（**0.86, 0.80, 1.10**，v1 的 0.62/0.45/1.35 太蓝）。
- **所有颜色参数故意声明成 Vector、填线性值**：Color 类型在 Linear 项目里会被当成 sRGB 再转换，雾就对不上天空了。
- 标签里有 `DisableBatching = True`。**不要勾 Batching Static。** 可以开 GPU Instancing。Fallback 是 Standard。

### 5.3 LanbaiFog（shader 自己的雾，所以写了 `nofog`）
```
h   = max(y − _CloudTopY, 0)                                   云顶之上的高度
ρ   = 密度 · _FogDensityScale · (1 + _FogExtra.x · exp(−h / _FogExtra.y))      ← shader 内的高度雾：云顶上方 60 m 内 ×1.5，根部溶进云海
f   = 1 − exp(−d · ρ)
f   = lerp(f, min(f, _FogCap) · exp(−h / _FogCapHeight), smoothstep(_FogCapFrom.x, _FogCapFrom.y, d))
col = lerp(col, 雾色(视线方向), f)                              ForwardAdd pass 只乘 (1 − f)
```
- 密度 `_FogDensity` **0.0006**（100 m 6%、500 m 26%、1 km 45%、3 km 83%），`_FogExtra` (0.5, 60)。
- **1.5 km 以外**（1300→1700 m 渐入）：`_FogCap` 0.6，且 × exp(−h / 500 m)（巨像 1600 m）——**雾永远不会比同一仰角的天更亮**。
- **雾色 = 天上的光雾带**：方位（从「相机→裂口」的水平方向量起）0° 的 `#484D63` → 50° 的 `#2A3041`，仰角 15° 以上 / 方位 50° 以外渐变到
  虚空 `#070A14`（+35° 以上 / 60° 以外全是虚空），地平线以下略暗。**天空盒必须画同一条带**（`Lanbai_GateAirSky.shader`，或同一公式写进 `Lanbai/Sky`）。
- **LanbaiFog 钩子（v2.1 新增）**：
  - bible §1.6 说所有自定义 shader 的雾色都走 `LanbaiFog.cginc` 的 `LanbaiHorizon(viewDir)`（和 `Lanbai/Sky` 共用）。那个文件还没有（§8.1 #8）。
    **有了以后**：把它放在 shader 旁边，**取消 shader 里 `// #include "LanbaiFog.cginc"` 那一行的注释**；它要 `#define LANBAI_FOG_INCLUDED` 并提供
    `half3 LanbaiHorizon(float3 viewDirWS)`，shader 就自动改用它（`LanbaiFogColour()`）。没有它时用 shader 自带的 `LanbaiBand()`（同一条带的副本）。
  - **Udon 全局覆盖**（`VRCShader.SetGlobal*`，不设就是 0，材质上的值生效）：`_Udon_FogBandDir`（xyz：带中心的世界方向，即裂口方向）、
    `_Udon_FogBandColor`（rgb：裂口旁的带色，线性；a > 0 才生效）、`_Udon_FogBandWidth`（方位，度；> 0 才生效）、`_Udon_FogDensity`（> 0 才生效）。
    名字取自 bible §1.6；如果 Director 用了别的语义，改 `LanbaiBand()` 顶上那几行即可。
- **分层的两个旋钮**（三个纵深层在亮的光雾前分开 ≥ 8 L\*）：中层 `_FogDensityScale` **0.25**；巨像 `_FogCapHeight` **1600**；远潮 `_FogCap` 0.92、无高度衰减。
  如果主工程的光雾带亮度不同，这两个数要在 U7 的截图上重新对一次 L\*。
- 颜色参数是 bible 的**屏幕值**（线性）。Unity 里用 bible 的**填值**（例如裂口旁 `#67697D`），由 S4 调色压回屏幕值；预览里是把天空和雾统一 ×1.9 来抵消 AgX + S4 的压暗。

---

## 6. LOD Group 建议

| | LOD0 | LOD1 | LOD2 | Culled |
|---|---|---|---|---|
| 近层（A–D） | > 25 % 屏高 | > 7 % | > 1 % | — |
| 中层（D–F ×1.6–1.8） | > 25 % | > 7 % | > 1 % | < 1 % |
| 巨像（G、H） | > 40 % | > 12 % | 一直保留（Cull 0 %） | — 远景轮廓要一直在 |
| 远潮 | 不用 FBX 触手：用 `TentacleTide.fbx` 公告板 | | | |

Fade Mode 选 None。只有近层投射阴影（bible：只有 60 m 内的近层投影）。

---

## 7. 门的摆放（GateLayout.json）——归「门」那一步

- **这一版没有动 `GateLayout.json`、`GATE` 和 gate.png**（门的构图由另一步负责）。现在的 `GateLayout.json`（443 条：近 2、中 30、巨像 3、背景巨像 8、远潮 400）
  是按 **v1 的形状**算的：每条的滚转是「让尖端指向裂口」自动求的，`length_m` 也是 v1 的弧长。**v2.1 的形状、长度和尖端都变了，这份 JSON 必须由门那一步重新生成**
  （`python3 Source/build_library.py --only layout`，脚本里的 `gate_instances()` 会按新形状重新求滚转）。在那之前不要按它摆。
- 远潮的**图集和 `TentacleTide.fbx` 已经用 v2.1 的形状重新生成**（位置和数量不变：`GATE['tide']` 的种子没变），可以直接用；`TentacleTide_Atlas.json` 里是新的格子数据。
- JSON 的格式、坐标约定（Blender (x, y, z) → Unity 布局 (x, z, y)，巴士相机在 (0, 50, 0)，云顶 y = 0，裂口在方位 0）、灯光参数和用法都和 v1 一样，见 `_v1/README_Tentacles.md` 第 7 节。

---

## 8. 性能

- 每条 LOD0 ≤ 6000 三角形；门里（按 v1 的数量）近 2 + 中 30（大多 LOD1/LOD2）+ 巨像 3 + 背景 8 ≈ 90k 三角形；远潮 800 三角形。
- 同一变体 + 同一 LOD + 同一材质可以 GPU Instancing。只有近层投射阴影。
- 贴图显存（含 mip，BC7/BC5）：3 × 2048² ≈ 16 MB + 细节法线 1.3 MB + 8 × 1024² Occlusion ≈ 11 MB + 3 × 512×2048 图集 ≈ 4 MB。
- shader v2.1 比 v2 多：顶点里一次 `mul` + 一次 `distance`（1 px 膨胀），片元里两次乘法（湿度）。可以忽略。

---

## 9. 重新生成（全部可复现）

```
python3 Source/build_library.py --only tex,fbx,check,tide     # 资产：贴图 → 8×3 LOD → FBX → 重新导入检查 → 远潮图集 / 网格
python3 Source/build_library.py --only lineup,flyby           # 两张渲染（1920×1080，64 spp；CPU 上各要十几到几十分钟）
python3 Source/build_library.py --only plot                   # 剪影验收图（wip/）：t > 0.85 剪掉后的黑剪影
python3 Source/build_library.py --only flyby --res 960 540 --samples 16 --tag _test   # 快速试渲
python3 Source/build_library.py --only layout,gate            # 门（归门那一步）
```
- 需要 Blender 5.0.1 当 Python 模块（`import bpy`），以及 numpy、scipy、Pillow；`Source/lib/` 里是 `export_unity.py`（唯一的 FBX 导出设置）和 `preview_rig.py`（v2 预览：光雾带天空、月、补光、裂口）。
- 渲染需要旁边的 `Clouds/` 文件夹（云卡片），lineup 的字体在 `scratchpad/fonts/`（Barlow Semi Condensed、思源黑体，OFL；找不到时退回 DejaVu）。
- 形状在 `VARIANTS` 和 `RAD_K`，皮肤在 `tex_fields / _crease_strokes / tex_albedo / tex_smoothness / tex_detail / occlusion_map`，
  shader 的预览复刻在 `make_material`（常量 `RIM`、`RIM_WET`、`CONVEX_KEEP`、`GRAZING_FLATTEN`、`DETAIL_STRENGTH`、`TRANS_GAIN`、`TIP_TINT`、`FOG`），
  lineup 在 `LINEUP_LOOK / shot_lineup`，flyby 在 `FLY / FLY_LOOK / flyby_hero / shot_flyby`。

---

## 10. 两张渲染里做了什么（以及 Unity 里对应的是什么）

**lineup.png**
- 正交相机、真实比例；八种从小到大排开，都朝右（裂口在画面右边外面）伸；8 m 的车（一个亮着暖色车窗的小盒子）悬在云海上方做比例尺；100 m 比例尺；
  左上角是 A–D 的放大（同一场景、同样的灯）。
- 光：月（`#D6E4FF`）从左后方高处——左上缘的冷边；裂口光（`#A99DE1`）从右边——朝右的一侧淡紫边；云海反光从下面（宽角度，湿的腹面一层柔光）；
  从相机一侧的一点冷的柔光，让皮肤读得出来（这一盏只在 lineup 里有，门里没有）。
- 背景是一块只给相机看的天幕：地平线处是光雾带（朝裂口的右边 `#484D63`、左边 `#2A3041`），往上到虚空 `#070A14`；右边低处是裂口的靛紫辉光 `#5B57A1`；
  左上角是月盘和银晕 `#5A6A88`；稀疏的星只在虚空里。根部埋在云工作间交付的月光云海卡片里（压扁成一条远处的云层）。
- 名字、弧长、姿态（英文 + 中文）；字体 Barlow Semi Condensed / 思源黑体。

**flyby.png**（bible §6·4 U8 *Ach nein!*：近处的臂与车同向涌过车窗）
- 一条 F ×1.1（154 m），根埋在云下 30 m，从车的右后方升起，朝裂口方向（方位 −30°）探出去，身体向车倾 28°；**车在它浪头的凹侧下面，离皮肤 16 m**
  （最近的顶点 16.1 m，bible 的近层 8–20 m，≥ 8 m；什么都不碰车），车在云顶上 45.9 m（bible 40–60 m）。相机朝方位 +28°、抬头 19°、18 mm，车速方向有真实的运动模糊。
- 整条手臂从右下升起、在上方拱过去，细线鞭垂到裂口前面——它在「涌向裂口」，你在它下面。看得见的是它的**凹侧**：压缩皱只在这里；凸侧（上缘）是绷紧的，只有冷边。
- 远处：云工作间的体积云卡片做成的云海（加了几片近一点的薄云）、月、裂口（共享预览里的替身）。**这张里故意没有远处的巨像**：在 bible 的巨像距离
  （1.3–4 km）上，18 mm 的画面会把 450 m 的巨像缩成云上一根灰色的细刺——正是 v1 被否决的「草芽」读法；巨像和中层的一圈留给 gate.png（长焦、从挡风玻璃看）。
- 后期：S4 调色的 numpy 近似、屏幕空间光柱、左边的窗柱和几滴雨（你在车里）。

**只在预览里有的**：天空 / 雾 ×1.9（抵消 AgX + S4 的压暗）；Mip 模拟（Cycles 没有贴图 mip）；云海高度场；屏幕空间光柱；窗柱与雨滴；numpy 调色；
flyby 里湿皮反射云海时云只暗 20%（门里是 65%）；lineup 的正面柔光。

---

## 11. 验收（这一版实测）

| 项 | 结果 |
|---|---|
| UV 集合 | 8 个 FBX 的每个 LOD 都是 UV0 `UVMap` + UV1 `UVSway`，重新导入核对；`Col` 在（R 0→1、G = 相位、B 0→1.06、A 1） |
| 预算 | LOD0 ≤ 6000 / LOD1 ≤ 2000 / LOD2 ≤ 600，全部满足；有向体积为正、最小三角形面积 > 0 |
| 剪影验收 | 八种（尖端剪掉、三个方向）一眼可分；D 的卷径 0.26 L（≥ 0.2 L）；卷只有 D 一个 |
| 反照率 | sRGB 每通道 30–44（均值 34 / 34 / 40） |
| 光滑度 | 0.52–0.92，均值 0.63；黏液条纵向 |
| 褶皱 | 只在凹侧（遮罩），一笔一笔、错开、倾斜；无环节、无 Voronoi、无鳞片 |
| shader | slang 编译（桩文件）四种 pass 组合无错误；Unity 未编译 |
| flyby | 离皮肤 16.1 m；车高 45.9 m；手臂在车的上方拱过去 |

---

## 12. 已知限制（老实说）

- **三个 shader 都没在 Unity 里编译过**（这里没有 Unity）。`Lanbai_TentacleSway.shader` 用 slang 做过语法 / 类型检查，另外两个是 v1 原样。
- **`GateLayout.json` 是 v1 形状的**（第 7 节）：要由门那一步重排后才能用。`Renders/gate.png` 同理。
- 近层手臂在 bible 的灯光下（月在前方低处）基本是**逆光的剪影**：看得见的皮肤在轮廓带、凹侧的湿反光和裂口光里；朝相机的一面是墨黑（bible 就是这么要的）。
  lineup 为了看清皮肤加了一盏正面柔光，门里没有。
- 1 px 膨胀在预览里没有（Cycles 不需要），只有 shader 里有；远处极细的线鞭在 Unity 里会比预览略粗。
- 巨像 H 末端的四根细丝在 2 km 外只有 1–2 px 宽（加上 1 px 膨胀），读作「散开的尖」而不是四根。
- C 的拧绳段贴图会随身体扭转（看起来像皮肤随拧绳一起拧）。
- 远潮公告板在 VR 里是平面：离得 5–12 km、雾 80–92%，看不出来；但不要把它们用在 3 km 以内。

## 13. 修复记录（v1 验收 → v2.1）

| 验收（`verify_art_v1.json` / `verify_tech_v1.json`） | 做了什么 |
|---|---|
| 剪影像角 / 刺 / 草叶 / 枯树（blocker） | 家族更细长（L/R 30–46）；半径曲线 57% 后凹形收颈、87% 后等粗细线（不再是锥形的尖）；2–3 个肌肉鼓包 + 截面肌肉起伏加大；八种整条身体的姿态（细 S / 大拱 / 拧绳 / 大 C / 双 S / 浪头 / 天鹅颈 / 盘旋的探）；**H 去掉三根侧枝**，改成盘旋上升、末端磨散；G 的辫根不再鼓成瘤 |
| 指尖是一排一样的蕨卷（blocker） | 甩直（A、F 带 S 波）、半卷（C）、分叉舌尖（E）、磨散（H）、钩（B、G），卷只有 D（出平面、0.26 L）；大小、手性、平面各不相同 |
| 轮廓锯齿（major） | 压缩皱改成两端收尖的一笔一笔（升余弦的卷边），倾斜 8–20°（螺旋），每笔自己的深浅和相位；主法线在掠射角压平；只在凹侧 |
| 皮肤像垃圾袋 / 清漆 / 乳胶（blocker） | 反照率 30–44 + 蓝紫斑驳；光滑度基底 ~0.63 + 低频干湿斑 + 纵向黏液条 0.86–0.92（柔边、蜿蜒）；褶皱只在凹侧（每个变体的曲率遮罩）；**凸侧有皮纹不再是抛光橡胶**（细节法线不受遮罩）；无环、无 Voronoi、无鳞；巨像 2–8 m 宏观起伏改成各向的坑与鼓包、主贴图平铺 3×3（不再像树皮 / 带环的树干） |
| 边光一圈发白 / 发紫、贴纸描边（major / minor） | 月侧轮廓按湿条纹断续；细尖透射 4.5 → 2.2；尖端靛紫变淡 |
| flyby 是一块直的锥形楔子（major） | 新构图：F 的浪头在车上方拱过去，车在凹侧下 16 m，细鞭垂到裂口前；月光从左前方给剪影勾冷边；云海卡片、巨像、窗柱与雨滴做比例 |
| 顶点色 8 位 → 摇摆台阶（技术 major） | UV1 `UVSway` = (t, 相位) float，shader 读 UV1；导入写明 Generate Lightmap UVs 关 |
| 同变体同步摆动（minor） | shader 按实例世界坐标加相位偏移 |
| UV0 半精度（minor） | V 居中；README 写明 Vertex Compression 取消 TexCoord0 |
| README：实例数 / B 阈值 / Smoothness Scale / 包围盒（minor） | 实例数按现在的 JSON 写（443，且注明要重排）；B 阈值写成相对半径（比例）；切换后 Smoothness Scale 设 1；包围盒写明放大 `localBounds` |
| `pow(1 − ndv, …)` 警告 X3571（minor） | 全部改成 `pow(saturate(1 − ndv), …)` |
| lineup 标签重叠（minor） | 重新排版（两行错开 + 引线；A–D 放到放大图里） |
| **bible §6·4 触手 shader** | 月侧 `#9DB8FF` 公式、裂口侧 `#A99DE1` × 接近度、细尖透射 `#5B57A1`、shader 内高度雾、`_FogCap` + 高度衰减、LanbaiFog 钩子、细尖 1 px |
