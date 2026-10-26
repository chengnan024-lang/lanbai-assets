# 样板树（D-44 #6）· 给本地的说明

写的人：云端会话「灯与假醒」（`pkg/lamps`）。总导演 10-25 选形：**A（老的路边阔叶树）为主、B（垂枝型）点缀**，B 全程只放 1–2 棵、只在水田边；C 不做。
**C# 与 shader 都没在 Unity 里编译过。** 检查见 §7。

## 修订 r2（2026-10-25，回应本地第一次技术验收 `FromLocal/tree_sample/20261025-101954/`）

| 本地发现 | 这一版 |
|---|---|
| 叶簇在 Unity 里是整块不透明的卡（不透明队列的表面着色器把 alpha 写成 1） | **采纳阿白的补丁**：`#pragma surface … keepalpha`，`LightingTreeLeaf` 返回 `s.Alpha` |
| 搭建器最后全局 `SaveAssets`，写到了别的包的资产 | **采纳补丁**：只 `SaveAssetIfDirty` 本包的三类材质。注：仓库的 C# 检查用的是 Unity 2021.1 的引用程序集，那里没有 `SaveAssetIfDirty`（2021.2 起才有），所以检查报 3 个“找不到”；它在本地 2022.3 里编译过、跑过（验收报告）。已写给总工程师 |
| 总导演：LOD1 的叶团卡在灰天里能看出平的长方形 | 叶簇图集每一格的叶子都收进一个椭圆（离格边 ≥ 4 %），**没有一片叶被卡边切成直线**；LOD1 的叶团格（格 3）收紧成一团。LOD0 的三格同样处理（只在下边中间给小枝留口） |
| 本地强制 LOD2 的图里剪影卡发白 | 剪影卡烘焙时关掉高光和透光（以前白天光下的高光、透光被烘进了反照率，Unity 又照一遍，所以发白）；现在烘的是反照率 × AO |
| 叶在本地的灯下偏亮、偏淡 | 透光 `_TransStrength` 0.30 → **0.22**（Blender 参考同步） |
| 阿白下载的 ambientCG（Bark006、LeafSet016） | 四套都是 **HTTP 403、0 字节**（`FromLocal/cc0/20261025-1015/README.md`），实际没有文件，所以这一版没法换；贴图仍是我们自己生成的。LeafSet016 是橡树叶，和 A 的羽状小叶也不合。以后真下下来再比 |
| 闪烁数字（hero 5.3 %、right 21 %） | 照总导演：先不作数，等总工程师把测试改成只量叶缘 |

## 0. 拷什么、点什么、截什么

1. 把 `Lamps/Tree/` 拷到 `Assets/Lanbai/Lamps/Tree/`（`Source~`、`Docs~` 不会被导入）。`Common/`（`LanbaiGlobals.cginc`、`LanbaiFog.cginc`）要先在。
2. 点菜单 **蓝白/Build/Sample Trees**：在 `Generated/` 建材质、在 `Prefabs/` 建 4 个预制体 `Tree_A1`、`Tree_A2`、`Tree_A3`、`Tree_B1`（带 LODGroup）。可以重复点，原地刷新。
3. 用预制体换掉场景里的杨树 / 临落树（摆法见 §4）。
4. 测试：`UnityTest/tree_sample.json`（总工程师拷进 `Engineering/UnityTest/tests/` 后，菜单 蓝白/Test/Run tree_sample）。它出三个对照机位、主座位 20 px/° 近景、头部微动的闪烁序列和性能。把输出文件夹推回 `FromLocal/tree_sample/<时间>/`。

## 1. 四棵树

| 预制体 | 高 | 冠宽 | LOD0 / LOD1 / LOD2 三角形 | 用在哪 |
|---|---|---|---|---|
| `Tree_A1` | 10.9 m | 9.8 × 10.5 m | 8 142 / 1 326 / 4 | 路边，主力 |
| `Tree_A2` | 12.2 m | 8.4 × 11.7 m | 10 486 / 1 540 / 4 | 路边，主力 |
| `Tree_A3` | 13.0 m | 10.9 × 12.8 m | 11 996 / 1 750 / 4 | 路边，主力（最大的一棵） |
| `Tree_B1` | 10.4 m | 7.5 × 9.2 m | 5 816 / 1 666 / 4 | **只在水田边，全程 1–2 棵** |

（数以 `Tree_Info.json` 为准。）A 的三个变体是同一套代码换种子、尺度、偏冠方向长出来的，枝的走向、叶团的位置都不同；再加上摆的时候每棵转一个随机角度，一排里看不出复制。

**形**：短干，3–5 根斜伸的大枝，枝端一团团的叶云，团与团之间露天（总导演第 1 条：剪影先于细节）。羽状小叶（槐 / 榆一类的“无名”阔叶树）。

## 2. 文件

| 路径 | 是什么 |
|---|---|
| `Models/Tree_*.fbx` | 根空物体 `Tree_X`，子物体 `Tree_X_LOD0/1/2`。LOD0/1 两个材质槽（0 树皮、1 叶），LOD2 一个（剪影卡）。顶点色 `Col`：R 柔度、G 相位、B 叶 |
| `Textures/T_Tree_LeafCluster_{Albedo,Normal,Mask}.png` | 2048² 叶簇图集 2×2：格 0–2 是 LOD0 的叶簇（一根小枝 + 22–27 片羽状复叶，卡 1.25 m），格 3 是 LOD1 的叶团（卡 2.5 m）。Albedo 的 A = 覆盖；Mask：R 叶片薄（透光），G 干光滑度，B AO |
| `Textures/T_Tree_Bark_{Albedo,Normal,Mask}.png` | 512×1024，沿干无缝。Mask：G 光滑度、B AO、A 水走的路 |
| `Textures/T_Tree_Impostor_Tree_X.png` | 1024×512，LOD2 的两张剪影卡（左：正面，右：侧面），RGB 是反照率 × AO，A 覆盖 |
| `Shaders/Lanbai_TreeBark.shader`、`Shaders/Lanbai_TreeLeaf.shader`、`Shaders/LanbaiTree.cginc` | §3 |
| `Editor/LanbaiTreeBuilder.cs` | 菜单 蓝白/Build/Sample Trees、测试用的 `TestRow`、导入设置（只管 `Lamps/Tree/`） |
| `UnityTest/tree_sample.json` | 测试定义（给 `Engineering/UnityTest/`） |
| `Tree_Info.json` | 高、冠宽、三角形、剪影卡尺寸、种子 |
| `Source~/Trees.blend` | Blender 源文件（4 棵树的三档 LOD）。生成它的代码在 `Lamps/Source/tree/` |
| `Docs~/` | 参考板、对照图、近景、闪烁检查（§6） |

## 3. 材质（`Lanbai/TreeBark`、`Lanbai/TreeLeaf`）

- **湿润**（圣经 §1.6，`_Udon_Wetness`）：树皮反照率 × lerp(1, 0.60, w)、光滑度 → 0.45、法线 ×0.6；叶反照率不变（蜡质，不吸水）、光滑度 → 0.60（圣经：湿叶 0.55–0.65）。w = `_Udon_Wetness × _WetResponse`。第 11 幕 `_Udon_Wetness` = 0 时树是干的。
- **叶 = alpha-to-coverage**（圣经 §6·1）：`AlphaToMask On`，alpha 按自己的屏幕导数锐化（(a − 0.5) / fwidth(a) + 0.5）；没有 MSAA 时退化成普通的 cutout。贴图导入开 **Mip Maps Preserve Coverage**（阈值 0.5）：远处的 mip 叶面积不缩，树冠不变稀、不闪（总导演第 2 条）。阴影 pass 是普通的 alpha test。
- **透光**：叶片薄的地方透过背光（`_TransColor` 暗黄绿 × `_TransStrength` 0.30 × Mask.R）。**钠灯下叶子不发绿发亮**（总导演第 4 条）：叶反照率是暗橄榄（覆盖处平均 sRGB 68），钠光几乎是单色橙，叶子在它下面读作暗的橄榄 / 琥珀。
- **风**（顶点）：慢摆 `_WindStrength`（叶 5 cm、树皮 3 cm）× 柔度²，0.2 Hz 左右，两层正弦；叶卡另有 1.2 cm 的小抖动。只在水平面里动，树不上下颠（圣经 §1.8）。参数在材质上，不用 `_Udon_` 全局量（风是本地的装饰，不同步）。
- **LOD2**（`_Impostor` 开）：两张交叉卡，法线不用贴图，冠的下半更暗，没有抖动、没有阴影。
- 雾走 `LanbaiFog`（`finalcolor` + `nofog`）。

## 4. 摆法（给第 1、2、11 幕的路段）

- 路边 4–15 m，间距 12–25 m 不等；**每棵绕竖轴转一个随机角度**（0–360°），A1/A2/A3 轮着用，不要连着两棵同一个。
- `Tree_B1` 只在水田边（路肩外 ≥ 10 m、贴着水田），全程 1–2 棵。
- 15–40 m 外读作剪影（圣经 §6·1，显示 3–6），比背后的天暗一档：靠雾和夜空，不要给树打补光。
- 路灯旁的那一棵：迎灯的叶团会亮一点（暗橄榄 / 琥珀），其余是剪影——这是想要的。
- 跑步机的根物体会动：**Batching Static 关**（圣经 §1.6），材质开了 GPU Instancing。预制体已经关了光照探针、反射探针（§1.6 不烘探针）。
- LODGroup：LOD0 > 25 %、LOD1 > 8 %、LOD2 > 1.2 % 屏幕高，再小就剔除；没有淡入淡出（切换的那一下在 8 % / 25 % 处，叶团与剪影卡的形是对齐的）。

## 5. 测试（`UnityTest/tree_sample.json`）

搭建：`蓝白/Build/Sample Trees` → S1 调色单开 → 关掉 `LB_Journey` 的占位组（若把路也关了，删掉这一步重跑）→ `LanbaiTreeBuilder.TestRow` 把 7 棵树放在本地 9-30 对照的 7 个位置（并藏起场景里原来的杨树 / 临落树）。
出图：`overview`、`right`、`left`（`FromLocal/trees` 的机位）、`hero`（主座位、20 px/°）；序列：`hero_micro`（±2 cm / ±1° 的头部微动，90 帧）、`hero_static`（对照）、`right_micro`（远树）。
门槛（初值，第一次实测后总工程师定）：`shimmer_p99` ≤ 12、`shimmer_frac` ≤ 2 %。

## 6. 云端的图（`Docs~/`）

- `Tree_Board_phase1.png`：第一阶段的参考板（问题、三个候选形）。
- `Tree_Board_final.png`：正式版总览：四棵树三档 LOD、三个对照机位（Blender，和本地的杨树、临落树并排）、主座位近景、闪烁检查的数。
- `compare_{overview,right,left}_blender.png`、`hero_20ppd_blender.png`：给测试当参照图。`lineup_lod0_1_2.png`：四棵树三档 LOD。
- **闪烁代理**（`hero_shimmer.json`、`hero_shimmer_heat.png`，`Lamps/Source/tree/lt_shimmer.py`）：主座位 20 px/° 的那一帧，头部 ±2 cm / ±1° 微动 12 帧；只渲覆盖率（白的叶、黑的底，点采样），2× 尺寸 2×2 平均 ≈ MSAA 4× 的 alpha-to-coverage，对 4× 尺寸 4×4 平均的参考，逐像素量差的时间标准差。
  - 最坏情况（白叶黑底）：均值 6.9、p99 36、叶缘均值 11.9（0–255）——这是覆盖率本身在 4 个样本下的跳动，任何 cutout 叶子都有；
  - 乘以第 1 幕夜里叶缘的局部对比（中位 4.1 码）：**均值 0.15、p99 1.35、> 4 码的像素 0.13 %**。夜里叶和背后的天只差几个码，所以叶缘的跳动看不出来。
  - 不含 mip（Cycles 不用 mip）、不含锐化的 A2C；Unity 的 `hero_micro` 序列才是判定。
- 渲染是 Blender Cycles，按第 1 幕：雾 Exp 0.009 `#161B27`、天 `#0E1220`（相机看到的）、Trilight 天 `#1A2438` 照物体，S1 调色（`Grading/Tools~/engine`）。灯是灯包的眼镜蛇钠灯（峰值 I = 40，按 Unity 单位），放在本地对照的 (6.3, 11)。**没有车、雨、站牌**（只比树）。

## 7. 检查

- shader：`python3 Common/Tools~/compile_check/check_shaders.py Lamps/Tree/Shaders` → `3 files, 64 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.`
- C#：`bash Common/Tools~/compile_check/check_cs.sh Lamps/Tree` → `C# CHECK OK (0 assembly error(s), 0 lint warning(s))`。
- **没在 Unity 里编译过、没在头显里看过。** 第一次导入请把 Console 原样推回来。

## 8. 来源与许可

整棵树（骨架、网格、叶簇与树皮贴图）都是 `Lamps/Source/tree/` 里我们自己的代码生成的，**没用任何外部素材**，可以按 CC0 公开。云端连不上 Poly Haven / ambientCG；没有用 Tripo，没有开任何收费任务。

## 9. 诚实的已知弱点

- Blender 的参考图用的是光线追踪的阴影：路灯旁那棵树的下层叶团被上层叶卡挡住，比 Unity 里（路灯不投影）暗。Unity 里迎灯的叶团会更亮一些。
- 闪烁只在 Blender 里做了“覆盖率”的代理检查（§6）；真正的判定是 Unity 测试的 `hero_micro` 序列和头显。
- 叶团用的是同一张图集的 3 格，近看（< 5 m）能认出重复的小枝形；乡道上树都在 4 m 以外。
- LOD2 两张交叉卡，正侧之间 45° 看时有一点“十字”感；这一档只在 ~90 m 外出现。
- B1（垂枝）的细枝帘是卡片，风里整片摆，没有一根根的枝条运动。
