# 第 7b 幕 · 河伯宫殿套件（`Palace/`）· 给 Unity 一侧的说明

写的人：云端会话「宫殿」（分支 `pkg/palace`）。对象：小楠电脑上 Unity 2022.3 的那一侧，以及组装第 7 幕的「海」。
**本目录里的 C# / shader 都没有在 Unity 里编译过。** 检查做法见 §7（DXC + Unity 2022.3 CGIncludes、Roslyn + U# 规则）。

## 0. 先做这几步（拷什么、点什么、截什么图）

1. 把 `Palace/` 拷到 `Assets/Lanbai/Palace/`（要有 `Assets/Lanbai/Common/`、`Assets/Lanbai/GateClouds/`（搭建脚本借它的 U# 工具）、`Assets/Lanbai/Act07_Sea/`）。
   `Source/`、`Docs~/` 不需要进 Unity（`Docs~` 本来就被忽略；`Source/` 是 Python，可以不拷）。
2. Project Settings → Player → **Vertex Compression：TexCoord0–3 不压缩**（鱼的编号在 uv2 里，CONTROL §6 第 8 条）。
3. 先跑 `蓝白/Build/Act07a`（海），再跑 **`蓝白/Build/7b 宫殿`**：`R_Palace` 会挂在 `R_Sea` 下（局部位置 (0, −250.335, 0)），驱动 `LanbaiPalaceDriver` 放在场景根上。
4. **烘焙**（§4）：只开宫殿的烘焙灯，Environment Lighting = Trilight 7b 的三个色，Bake。
5. Director 的分发表里加 `LanbaiPalaceDriver`（时间窗 643.96 → 876.16）。
6. 截图推回 `FromLocal/07b_test/`：主座位 (0.55, 1.70, 2.05)、桌面 1920×1080、水平 90°、PPv2 开（S7b）：
   **t = 655.86（F5p）、690、706、735.56（F6）、748.26（F7）**；另 F7p **812.36** 抬头向左上（yaw −25°、pitch +42°）一张。
   每张对照 `Docs~/iterations/` 里同名的参考图。

## 1. 文件

| 文件 | 是什么 |
|---|---|
| `PalaceLayout.json` | **唯一的数据源**（= 海的 `Act07_Sea/PalaceFrame_约定.json` + 宫殿的灯、门、灯焰、鱼、烘焙参数）。宫殿坐标：米、Unity 轴，x = 0 车路、y = 0 台地顶、z = 0 F5 时的车根 |
| `Models/Palace_*.fbx` | 网格（顶点就是宫殿坐标，挂在 R_Palace 下不动）。`*_LOD0` / `*_LOD1`，搭建脚本建 LODGroup。`tri_counts.json` 是三角形数 |
| `Textures/T_07b_*` | 5 套 2048²（漆、鱼鳞瓦、宝贝、石、铜：Albedo / Normal / Mask）+ 梁枋云气纹带 + 灯焰 8 帧图集 + 灯晕 |
| `Shaders/Lanbai_Palace.shader` + `LanbaiPalace.cginc` | 宫殿的不透明材质（光照贴图 + 8 盏解析宫灯的 GGX 高光 + 淤泥 + 珍珠母虹彩 + 宝贝视差 + 海草摆动 + LanbaiFog + `_Udon_PalaceVeil`） |
| `Shaders/Lanbai_PalaceFlame.shader` | 灯焰序列帧 + 灯晕卡（公告板，加色，`_FogMode 2`：exp(−0.004 d)，不吃雾、不吃 veil） |
| `Shaders/Lanbai_PalaceGlow.shader` | 门里的暖光（不透明）与门口的 3 张锥形光卡（加色） |
| `Shaders/Lanbai_PalaceFish.shader` | 1 500 条银鱼，一张合并网格、顶点里算运动（与 `Source/kit/fish.py` 同一套数学） |
| `Editor/LanbaiPalaceBuilder.cs` | 菜单 `蓝白/Build/7b 宫殿` |
| `Editor/LanbaiPalaceData.cs` | 生成的数据（`Source/gen_layout.py`），不要手改 |
| `Editor/LanbaiPalaceImport.cs` | 导入设置（只管 `Assets/Lanbai/Palace/`） |
| `Runtime/LanbaiPalaceDriver.cs` | U# 驱动：最近的 8 盏宫灯写进 `_Udon_Lamp0..7`；鱼的 lite |
| `Source/` | 生成一切的 Python（bpy 5.0.1）：布局、模块、贴图、FBX、参考渲染与后期 |
| `Docs~/` | 考据、lookdev brief、迭代图、评审稿 |

（以下各节在交付前补全：§2 坐标与运动，§3 材质，§4 烘焙，§5 驱动，§6 参考渲染与量出的数，§7 检查，§8 与评审的分歧，§9 已知弱点。）
