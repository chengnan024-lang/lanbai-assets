# 车（PAZ-672）· `Bus/` + `Cabin/`

写的人：会话「车」（`pkg/bus`）。车型：PAZ-672（小楠 10-24 定；总导演 D-28…D-31）。
**没在 Unity 里编译、导入、运行过。** shader 和 C# 只过了 `Common/Tools~/compile_check/`（着色器 0 错 0 警告；C# OK），模型只在 Blender 里读回核对过。

---

## 0. 本地先做这几步

1. **拷文件夹**：`Bus/` → `Assets/Lanbai/Bus/`，`Cabin/` → `Assets/Lanbai/Cabin/`（`Common/`、`Rain/` 已有，要用 main 上最新的）。
2. **Project Settings → Player → Vertex Compression**：TexCoord0–3 **不压缩**（CONTROL §6 第 8 条；车厢光照图在 uv1，外观做旧图集也在 uv1）。
3. **Project Settings → Tags and Layers**：要有 **`Bus`** 和 **`BusExterior`** 两个层（圣经 §1.6 / §4.3：世界主光、钠灯扫光、Act07 的灯按 `Bus` 照车厢；站灯按 `BusExterior` 照外壳）。没有就先加，否则搭建菜单只报警告、物体留在 Default。
   搭完：车厢、玻璃、窗帘、门在 `Bus`；外壳两级 LOD、四个轮子、雨刮在 `BusExterior`。
4. 等脚本编完，点菜单 **`蓝白/Build/车`**。它会删掉上一次的 `Lanbai_Bus`，重新搭：模型、材质、外观 LOD、23 个座位的 `VRCStation`、不可见碰撞体、两盏头像补光、`LanbaiCabinDriver`、雨刮。第一次点可能报“class not compiled yet”，再点一次。点完看 Console 的 `[Lanbai Bus]` 报告。细节：`Editor/README_Build.md`。
5. **换掉本地的 v1 车**（不删，关掉）：
   - 本地 v1 车的根物体关掉；`LB_Journey.busRoot` 指向 `Lanbai_Bus`。
   - `LB_Journey.heroEye` 改成 **(0.55, 1.70, 2.05)**（诗句按它摆；门、标准台、所有包都用这个）。
   - `LB_Journey.busMin / busMax` 照 `Models/BusLayout.json` 的 `cabin_bounds`：**min (−1.35, 0.57, −3.59)、max (0.99, 2.62, 3.44)**（D-31：车厢内部；Director 按玩家根位置查，头探出玻璃 ≤ 0.6 m 不算离开）。
   - `wheels` = `Wheel_FR / FL / RR / RL`（原点在轮心，绕本地 X 转），`wheelRadius` = **0.45**。
   - `doorPivot` / `doorPivot2` **清空**：门是一扇四片的折门，开着的状态就是它的正脸（圣经：门从不关）；第 11 幕在白遮罩下关、第 12 幕前打开，都由 `LanbaiCabinDriver` 做（`BusLayout.json` 的 `door_panels`）。
   - `busRenderers` / `glassRenderers` **清空**（它们是侵蚀 shader 之前的占位，会和车厢驱动打架，见 `Cabin/给总控_shader.md` §3）。
   - `cabinLights` 拖进 `HeadFill_0 / HeadFill_1`；`cabinTubes` 拖进 `Cabin_Tubes`。
   - `fan`、`pendant`：新车没有（圣经：除了收音机和空司机座，没有道具）。清空。
   - 实例人数上限 = **23**（D-31，`seat_count`，不算司机座）。
   - **座位交互**：每个 `Station_*` 上搭建菜单挂了 `Bus/Scripts/LanbaiBusSeat.cs`（Interact → `UseStation`，提示“坐下”、2 m）。如果想继续用本地 v1 的 `LB_Seat`，把它指到这些 `Station_*` 上，再删掉 `LanbaiBusSeat`，两个只留一个。
6. **烘一张车厢立方图**给玻璃（`_CabinCube`）：只开管灯，在主座位眼位，不要在门附近烘、不要实时探针（门内 181 s 的教训）。三个 `M_Bus_Glass_*` 都填上。
7. **截图推回来**（`FromLocal/bus_test/`，桌面 1920×1080、水平 90°、PPv2 开、ARGBHalf 渲完再调色）：
   - 主座位正前，t = 30（夜路，管灯 1）、t = 150.30（U7）、t = 270（晨）；
   - 主座位朝门（yaw +25°）t = 270：晨日应该在门洞正中；
   - 主座位抬头 +52°，t = 169.2（天窗里的伤口）；
   - 后排左侧靠窗（眼 (−1.10, 1.70, −0.47)）正前，t = 30；
   - 第 1 幕出生点（右路肩、站牌后 14 m）看车，t = −5。
   和 `Docs~/reference/` 里的同名图并排比。

---

## 1. 有什么

| 路径 | 是什么 |
|---|---|
| `Models/Bus.fbx` | 整辆车（48 个物体，11.5 万三角形）。分组见 `Source/finish_bus.py` 头注；`Models/Bus_fbx_readback.json` 是读回核对 |
| `Models/BusLayout.json` | 唯一给 Unity 的数据：眼位、天窗、门（四片的开 / 关位姿）、轮子、管灯、头像补光、收音机、23 个座位（station 位置、眼位）、碰撞体、车厢包围盒 |
| `Models/Bus_HarnessShell_paz672.fbx` | 给总工程师的渲染标准台：`--bus fbx:Bus/Models/Bus_HarnessShell_paz672.fbx`（没有玻璃） |
| `Textures/Cabin_TubeLM.exr` | `_CabinTubeLM`（1024²，uv1）：RGB = 管灯照度 E（线性，Unity 单位），A = AO（0.5 m）。在 Blender 里只开 10 根管灯烘的；**中段座垫 E = 0.6**（圣经 §4.3 写 0.8；0.8 时座椅顶显示约 (87, 46, 52)，比圣经的“座椅顶 ≈ #4A2229”亮约 18%、偏粉，所以整体 × 0.75，待总导演批） |
| `Textures/Bus_Exterior_Albedo_2048.png` / `_Mask_2048.png` | 外观图集（uv1）：双色漆 + 做旧（轮拱 / 门槛 / 门边的锈、窗角雨痕、下 30 cm 泥点、门边掉漆、车顶氧化）；Mask：R 金属、G 光滑度、B 湿、A AO |
| `Textures/Cabin_*` | 平铺细节：穿孔顶棚（Ø3 mm / 12 mm）、凸点橡胶（Ø25 / 50 mm）、窗帘织纹、收音机刻度；座椅 / 仪表台 / 收音机皮套的法线是 Poly Haven 的 CC0 扫描皮（`leather_red_03`、`brown_leather`，Rob Tuytel） |
| 顶点色（`Cabin_Static`） | R = 积灰 / 发黄（管灯周围的顶棚、窗框四角和窗台、地板贴墙的边、踢脚线），G = 磨亮（座垫中间和前沿、靠背顶边、司机座、门口和过道地板、仪表台前沿、低处鞋痕），B = 晒褪（靠窗的靠背顶边）+ 开裂点（B > 0.75） |
| `Textures/Bus_DestBlind_1024x296.png` / `_Blank_` | 目的地牌：外看正字「蓝白」（思源黑体 Heavy，140 mm）；第 11 幕换空白 |
| `Editor/LanbaiBusBuild.cs` | 菜单 `蓝白/Build/车` |
| `Source/` | Blender 5.0.1 的全部脚本：`bus_spec.py`（唯一数据源）、`build_bus.py`（造车）、`finish_bus.py`（分组、UV、导出、读回、布局 JSON）、`bake_lightmap.py`、`weather_exterior.py`、`gen_textures.py`、`viewcheck.py`（视窗验证） |
| `Docs~/` | 简报 `lookdev_brief.md`、视窗图、迭代图、D-13 里尔克、参考渲染 |
| `../Cabin/` | 车厢 shader（`Lanbai/Cabin`、`Lanbai/ThinCloth`）、`LanbaiCabinDriver`、numpy 移植、导入设置。见 `Cabin/README.md` |

重做一遍（Blender 5.0.1 的 bpy 模块）：
```bash
~/bpy/bin/python Bus/Source/gen_textures.py
~/bpy/bin/python Bus/Source/finish_bus.py --out /tmp/bus/models          # 造车 + 存 /tmp/bus/bus_final.blend
~/bpy/bin/python Bus/Source/bake_lightmap.py --res 1024 --samples 96      # _CabinTubeLM
~/bpy/bin/python Bus/Source/weather_exterior.py --res 2048                # 外观图集，存 /tmp/bus/bus_final_ext.blend
~/bpy/bin/python Bus/Source/finish_bus.py --out Bus/Models --from-blend /tmp/bus/bus_final_ext.blend   # 导出 + 读回
~/bpy/bin/python Bus/Source/viewcheck.py --out Bus/Docs~/viewcheck       # 15 个目标
```

---

## 2. 视窗（主座位 (0.55, 1.70, 2.05)）

**15 / 15 个取景目标看得见**（`Docs~/viewcheck/hero_map.png`，0.5° 网格对真网格打射线，每个目标 9 条）。车型、门、挡风的来龙去脉见 `Docs~/lookdev_brief.md` §2、§6–8。

| 窗 | 方位 | 仰角 |
|---|---|---|
| 挡风左片 / 中柱 / 右片 | −55.5 … −28.5 / **−28.30 … −26.35** / −26.5 … +20.5 | −16 … +20.5 |
| 右 A 柱 | +20.5 … +21.8 | |
| 门洞（开着） | +21.8 … +38.4（折门的后叠在 +38.4 … +46.9，躲在门后柱后面） | −42 … +36 |
| 主座位侧窗 | +42 … +146 | −39 … +48 |
| 天窗 | ±31 | +41.5 … +63.5 |
| 右侧第一扇斜面窗 | +44 … +155 | +41.5 … +71 |

- 晨日（D-12，+30° / +6°）在门洞正中，±1.5° 全清，头往左 5 cm 也清。
- 里尔克（D-13 A，D-30 单语块）：+5.5°、顶边 −2.5°、60 m，四种语言块里都没有遮挡（`Docs~/D-13_里尔克候选.md`）。
- 收音机（D-14）：仪表台上、方向盘右边，正好在 −20° / −12°。
- **头左右各移 5 cm**（总导演要的检查，`viewcheck.py --eye`）：头往左时河伯滑到中柱后、坠入深海滑到收音机后；头往右时银心滑到中柱后、庄子 8-ii 碰到门把手 / 窗框。都是细件扫过，不是整块盖住。
- 云唇的路径（「云」的 `lip_path_v1`）：只被 A 柱挡（+18.4 … +21.1°）；太阳的两次出入都在门洞正中。
- 右外后视镜从主座位看不见（D-28e）。

### 2.1 别的包怎么查遮挡（D-33）

**最快：查表（不要 Blender）。** `Docs~/viewcheck/hero_occlusion.npz` = 从主座位眼位按 0.25° 网格（方位 −180…180、仰角 −60…80）对**现在这辆车**（r03b：四片折门往后叠、低装右镜、雨刮停在挡风下沿以下）打射线，记第一个碰到的不透明件；玻璃不算遮挡。
```python
import sys; sys.path.insert(0, 'Bus/Source')
from occlusion_lookup import Occlusion
occ = Occlusion()                                   # 默认读 Bus/Docs~/viewcheck/hero_occlusion.npz
occ.rect(az0, az1, el0, el1)                        # {'blocked': 0..1, 'by': {不透明件: 占比}, 'window': {窗: 占比}, 'cells': n}
occ.point(az, el)                                   # ('WindscreenR' | 'open' | 件名, 是否不透明)
```
命令行：`python3 Bus/Source/occlusion_lookup.py --rect=-1.1,12.1,-8.0,-2.5`（方位 0 = 车头、+ = 右；仰角 + = 上；度）。
0.25° 的网格会漏掉比它细的东西（中柱连胶条约 2°，不会漏；4 mm 的雨刮杆远看会漏）。要精确就直接对网格打：`~/bpy/bin/python Bus/Source/viewcheck.py --out <目录> --step 0.1 --eye x,y,z --export-grid 0.1`（要 Blender 5.0.1 的 bpy；建车约 5 秒，0.1° 全景约 5 分钟）。车改了，车的会话会重出这张表。

### 2.2 主座位侧窗（WinR1）的真窗框（D-33：诗要放 +61° 附近）

在方位 +61°，从下往上（仰角）：车身 / 窗台 … −35.5 · 胶条 −35.3 … −33.8 · **下扇玻璃 −33.8 … +20.8** · 推拉小窗的横档 +20.8 … +23.5 · **上扇（推拉小窗）+23.5 … +43.3** · 胶条、窗顶框、窗帘横杆 +43.3 … +49 · 车身 … +54.5 · 斜面窗 +54.5 … +66 · 顶棚。
沿仰角 0°，从前往后（方位）：门把手 +36.8 … +39.8 · 门后柱 / 窗框 +39.8 … +42.8 · **折门的后叠（隔着窗玻璃看见）+42.8 … +47.0** · **WinR1 的净玻璃 +47.0 … +103.3** · 推拉窗的竖中梃 +103.3 … +107 · WinR1 +107 … +146 · 主座位那扇窗帘（全开，堆在窗的后端）+146 … +153 · 窗间柱 +153 … +154 · WinR2 …。
所以 +61° 附近的净窗是方位 **+47 … +103°**、仰角 **−33.8 … +20.8°**（下扇）；横档在 +21 … +23.5°。窗帘不进这一段（主座位那扇全开，堆在 +146° 以后）。

---

## 3. 参考渲染

`Docs~/reference/`：主座位在第 1、2、4（U7、U8 抬头看天窗）、4c、6（正前、朝门）、7a、8、9、11、12 幕，后排左侧靠窗座（D-31），第 1 幕出生点看车外。场景脚本 `Docs~/lookdev/scene_acts.py`：车厢的项和 `Lanbai/Cabin` 一样（反照率 ×（光照图 × 管灯 + 环境色 × AO）、漂白、侵蚀用同一个阈值公式和系数）；**窗外是每幕的天色占位，不是那一幕的画面**，所以 APL 只能看车厢那一部分。每张的 `metrics.json` 在旁边。

---

## 4. 诚实的已知弱点

1. **没在 Unity 里跑过**：材质参数、头像补光的强度（菜单给的是起始值 0.5 / 6 m，每排一盏在 z 0，6 m 才够到车头车尾；要用灰卡 `#585F64` 在座位处校）、雨刮枢轴的朝向、VRCStation 的坐姿高度都要本地看。
2. **车厢的亮度**：光照图按“中段座垫 E = 0.6”校（圣经写 0.8；按座椅顶的显示目标 `#4A2229` 降了 0.75 倍）；主座位自己的座垫约 0.35（它在右排管灯的尽头、天窗旁边）。要和本地的画面对过再定。
3. **侵蚀公式**：圣经 §4.8 的写法和它的下一句话打架，`Lanbai/Cabin` 默认按“下一句话”（`Cabin/给总控_shader.md` §1），等总导演批。
4. **外观做旧是程序算的**（位置 + 噪声），还没用 PAZ 的照片（总导演说照片可以直接用；没来得及）。0.3 m 看锈和雨痕还偏规整。
5. **玻璃的车厢立方图**要本地烘（第 0 节第 6 步）。
6. 门的“关”只在第 11 幕用，是四片平移到门框里（没有做折叠的动画）；白遮罩下看不见过程。
7. 车高 2.74 m（原车 2.95 m），因为天窗玻璃 2.62 要和顶棚齐平（D-28a）。
8. `Cabin_Static` 一个物体 2.8 万顶点、十几种材质：draw call 是材质数。要省的话按材质合并贴图图集（没做）。
9. **玻璃不跟着侵蚀一点点消失**：`Lanbai/BusGlass` 是雨包的 shader，没有侵蚀裁剪。`LanbaiCabinDriver` 按每块玻璃中心的侵蚀阈值（和 `Lanbai/Cabin` 同一个公式，加噪声中值 0.025）在侵蚀走过它时把那块玻璃关掉：天窗最先（fade ≈ 0.05），后窗下扇最后（≈ 0.85）。一块一块地走，不是像墙那样一片一片地走。参考渲染也是这样做的。
10. **窗帘第 10 幕飞走**改成**直着往上**从已经没了的车顶出去（稍微偏向太阳），速度不超过“0.75 × 离眼睛的距离”（任何路线下 ≤ 1.05 × 真距离，圣经 §1.8）；主座位旁边那幅不往里翻、离眼睛至少 0.35 m。眼睛按本地玩家座位球心 + 0.68 m 算。
11. 头像补光、座位交互（`LanbaiBusSeat`）没在 VRChat 里试过。`Common/Tools~/compile_check` 的 SDK 桩没有 `VRCStation`，我是加了一个临时桩（不在仓库里）检查过的。
