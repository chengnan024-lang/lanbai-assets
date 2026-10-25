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

**每个座位（D-33 #7b）：** `Docs~/viewcheck/seats_occlusion_1deg.json`，格式按总工程师定的：`{"step":1,"az0":-180,"el0":-30,"n_az":360,"n_el":60,"seats":[{"name","eye","occ"}]}`。`occ` 是 `n_el` 行（从 `el0` 往上）× `n_az` 格（从 `az0` 往右）连成的串，`'1'` = 穿过格子中心的射线碰到不透明件（玻璃穿过去）。座位顺序就是 `BusLayout.json` 的 `seats` 顺序（= `SetSeat` 的号），主座位 `SeatR0` 在第 0 个、眼位用合同的 (0.55, 1.70, 2.05)；别的座位用 `eye_approx`。用完整、门开着、没侵蚀的车量。仰角放到 −30…+30°（诗的块顶不超过约 +17°）。重出：`~/bpy/bin/python Bus/Source/seat_occlusion.py`。主座位那一行和 0.25° 的 `hero_occlusion.npz` 对过，99.7% 一致（差的是边上的格子）。

**第 8 幕庄子（D-33 #7a）：** 门组（折门四片、门柱、门口扶杆、门框上半、WinR1 前沿胶条和饰条）在一个软边的盒子里（世界坐标 x 0.80…1.60、y 0.45…3.00、z 2.38…3.45，边缘 0.15 m），`LanbaiCabinDriver` 在 957.4 → 965.4 用 MPB `_DoorBias` 0 → 1 把它们侵蚀掉（盒子里 tau 拉向 tau + 1，扶杆的 `_FadeResist` 不算；排在座位球保护**之后**，所以座位球留不住门柱）。门口踏步、地板不在盒子里。第 11 幕起 fade 和偏置都是 0，第 12 幕站台上车是完整的。
量法：`~/bpy/bin/python Bus/Source/zhuangzi_check.py`（真车网格打射线 0.25°；不透明件用 `cabin_numpy.erode_field` 判断那一点在 fade(t)、door_bias(t) 下还在不在，不在就穿过去；玻璃不算挡）。结果写在 `Docs~/viewcheck/zhuangzi_act8.json`：

| 语言（块） | 完整的车 | 第 8 幕、没有门组偏置 | 第 8 幕、有偏置（971.4 / 976.4 / 980 / 985 / 989.0） |
|---|---|---|---|
| zh / zht（+21.8…+48.2°，±6.4°） | 39.1% | 10.9%（门口扶杆 9.4%） | **0%** |
| ja（+23.7…+46.3°，±12.7°） | 42.9% | 15.6% | **0%** |
| en / de（+24.7…+45.3°，±10.4°） | 42.2% | 17.5% | **0%** |

### 2.2 主座位侧窗（WinR1）的真窗框（D-33：诗要放 +61° 附近）

在方位 +61°，从下往上（仰角）：车身 / 窗台 … −35.5 · 胶条 −35.3 … −33.8 · **下扇玻璃 −33.8 … +20.8** · 推拉小窗的横档 +20.8 … +23.5 · **上扇（推拉小窗）+23.5 … +43.3** · 胶条、窗顶框、窗帘横杆 +43.3 … +49 · 车身 … +54.5 · 斜面窗 +54.5 … +66 · 顶棚。
沿仰角 0°，从前往后（方位）：门把手 +36.8 … +39.8 · 门后柱 / 窗框 +39.8 … +42.8 · **折门的后叠（隔着窗玻璃看见）+42.8 … +47.0** · **WinR1 的净玻璃 +47.0 … +103.3** · 推拉窗的竖中梃 +103.3 … +107 · WinR1 +107 … +146 · 主座位那扇窗帘（全开，堆在窗的后端）+146 … +153 · 窗间柱 +153 … +154 · WinR2 …。
所以 +61° 附近的净窗是方位 **+47 … +103°**、仰角 **−33.8 … +20.8°**（下扇）；横档在 +21 … +23.5°。窗帘不进这一段（主座位那扇全开，堆在 +146° 以后）。

---

## 3. 参考渲染

`Docs~/reference/`：主座位在第 1、2、4（U7、U8 抬头看天窗）、4c、6（正前、朝门）、7a、8、9、11、12 幕，后排左侧靠窗座（D-31），第 1 幕出生点看车外，主座位往左前 −45° 看空司机座和方向盘（`ref_driver`）。有侵蚀的幕（7a、8、9）里所有物体都按同一个场侵蚀，玻璃按 `LanbaiCabinDriver` 的阈值一块块关掉。场景脚本 `Docs~/lookdev/scene_acts.py`：车厢的项和 `Lanbai/Cabin` 一样（反照率 ×（光照图 × 管灯 + 环境色 × AO）、漂白、侵蚀用同一个阈值公式和系数）；**窗外是每幕的天色占位，不是那一幕的画面**，所以 APL 只能看车厢那一部分。每张的 `metrics.json` 在旁边。

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
9. **玻璃不跟着侵蚀一点点消失**（D-32 #8 批准）：`Lanbai/BusGlass` 是雨包的 shader，没有侵蚀裁剪。`LanbaiCabinDriver` 按每块玻璃中心的侵蚀阈值（和 `Lanbai/Cabin` 同一个公式，加噪声中值 0.025，约等于四周窗框没了一半）算出侵蚀走过它的时刻（在单调的 Fade(t) 上二分，开场算一次），从那一刻起 1.5 秒把染色、底透明度、水珠和反射一起淡到 0，然后关掉。按 t 算，拖时间轴也对。天窗最先（fade ≈ 0.05），后窗下扇最后（≈ 0.81）。
10. **窗帘第 10 幕飞走**（D-32 #9）：先**直着往上**，横杆升过车顶线 0.35 m 以后再平滑地弯向太阳（切线连续，转弯半径约 0.6 m），F10l 起在日光里化掉。速度不超过“0.75 × 离眼的距离”（任何路线下 ≤ 1.05 × 真距离，圣经 §1.8）；主座位旁边那幅不往里翻、离眼睛至少 0.35 m。眼睛按本地玩家座位球心 + 0.68 m 算。
11. 头像补光、座位交互（`LanbaiBusSeat`）没在 VRChat 里试过；座位的“坐下”提示靠反射调 `GetBackingUdonBehaviour`，要是退回了 `Undo.AddComponent`，23 个座位会显示默认的“Use”，本地看一眼。
12. **折门的玻璃**单独导出成 `Glass_Door0…3`（`Lanbai/BusGlass`），搭建菜单把它们挂到各自的 `Bus_Door0…3` 下面，第 11 幕关门时跟着走；侵蚀时跟门组一起走（门组偏置过半时 1.5 秒淡掉）。折门本身在 `Bus` 层：从外面看（第 1、12 幕）站灯照不到它，车厢管灯的常量照得到。
13. **顶点色**：没有顶点色的网格（外壳、轮子、收音机、灯管、门、玻璃）导出时补一层全 0 的 `Col`，免得 Unity 当成白色、整块读成满磨损 / 满积灰。
14. 后排左侧（`ref_rearL3`）：座椅顶上的扶杆穿进了贴墙的窗帘，D-36 重做座椅和侧窗时一起改。

---

## 5. 车厢切片（D-40 #1：座椅 + 侧窗 + 立柱，给本地的 Unity 测试）

**没在 Unity 里编译、导入、运行过。** C# 只过了 `bash Common/Tools~/compile_check/check_cs.sh Cabin Bus`（Roslyn：0 错误、0 警告、lint 干净）；Blender 那边只在 Blender 里读回核对过。

**是什么。** 整车之前先单独进 Unity 的三件：主座位的座椅、主座位那扇侧窗（车厢里那一半 + 玻璃）、右边第一根立柱。总工程师的测试 `Engineering/UnityTest/tests/bus_slice.json`（`pkg/engineering`）用它查 D-40 #1 的五项：贴图压缩、mip、高光闪烁、光照图接缝、法线强度。

**菜单 `蓝白/Build/车 切片`**（`Editor/LanbaiBusSliceBuilder.cs`；类名就是 `LanbaiBusSliceBuilder`，测试工具靠这个类名判断切片交没交）。在**当前场景**里搭（测试工具给的是沙盒里的空场景）；可以反复点，先删掉上一次的 `Lanbai_BusSlice`（没激活的也删）。整个搭建是**一步 Undo**：按一次 Ctrl+Z，新切片没了、旧切片回来、关掉的灯重新开。也可以当静态方法调：`LanbaiBusSliceBuilder.Build()` 返回一行 `OK …` / `ERROR …`。报告在 Console 的 `[Lanbai Bus Slice]`。

搭出来的东西都在根物体 `Lanbai_BusSlice` 下面，根在原点、不旋转，所以和整车是同一个坐标系（车在原点、车头 +Z）。三件从 `Models/Bus.fbx` 里拿出来、世界变换不变，FBX 实例剩下的部分删掉。

| 物体 | 里面是 | 材质 |
|---|---|---|
| `Slice_Seat` | `Seat_SeatR0`（D-36 主座位：uv0 零件图集，uv1 `_CabinTubeLM`） | `M_Bus_Part_SeatHero`（`Lanbai/Cabin`，零件图集 `Textures/Parts/Part_SeatHero_*`） |
| `Slice_SideWindow` | `Window_R1`（窗框、内胶条、横档、窗台、两扇推拉小窗、窗扣）+ `Glass_WinR1` | `Lanbai/Cabin`（`_CabinTubeLM`）；玻璃 `M_Bus_Glass_Side`（`Lanbai/BusGlass`） |
| `Slice_Pillar` | `Pole_R0`（立柱、上下法兰和螺钉、停车按钮盒） | `Lanbai/Cabin`（`_CabinTubeLM`） |
| `Slice_Globals` | `LanbaiBusSliceGlobals`（见下） | |
| `Slice_Camera` | 主座位眼位 (0.55, 1.70, 2.05)，朝 +Z；16:9 下水平 90°（竖直 58.7°），near 0.02，HDR，背景纯黑（切片外面什么都没有，按夜路算）；`PostProcessLayer`：体积层 = `PostProcessing` 层（没有这一层就警告，体积层留空），AA 关，Stop NaN 开 | |
| `Slice_Grade_S2` | 只在项目里有调色套件的 `Lanbai_PP_S2`（夜路）、也有 `PostProcessing` 层时才建：全局 PPv2 体积，权重 1。没有就警告，截图不调色 | |

- **材质和整车菜单是同一套代码**（`LanbaiBusBuild.CabinMat / GlassMat / PartMat`，用哪种由 `LanbaiBusBuild.ModeFor` 定），只是写到 `Assets/Lanbai/Bus/Generated/Materials/`。层：`Bus`（没有这一层就警告）。
- **只写 `Assets/Lanbai/Bus/Generated/`**（`bus_slice.json` 的 `allowed_writes`）：`Materials/`，只有旧 FBX 时才有 `Meshes/`（见下面 uv1 那条）。它只存自己写的那几个资源（`AssetDatabase.SaveAssetIfDirty`，一个一个存，路径不在 `Generated/` 下的不存），**不调 `AssetDatabase.SaveAssets`**：那个会把工程里所有没存的改动一起落盘（比如 U# 的程序资产、`Assets/SerializedUdonPrograms/`），测试工具会把它们算成这次搭建的写入。不建 UdonSharp 程序资产（D-41），不挂 VRChat 组件，不改导入设置，不存场景。
- **第一次在一个工程里点**会新建 `Assets/Lanbai/Bus/Generated/` 这个文件夹，连带 `Assets/Lanbai/Bus/Generated.meta`。这个 `.meta` 不在 `Generated/**` 里面，总工程师的写入核对（`writes.undeclared`）会把它算成没声明的写入，`no_undeclared_writes` 不过；第二次跑就没有了。要么 `bus_slice.json` 的 `allowed_writes` 加一条 `Assets/Lanbai/Bus/Generated.meta`，要么测试工具把 `X/**` 也算上 `X.meta`（都归总工程师改，这里改不了）。
- **Bus.fbx 的导入设置 Generate Lightmap UVs 要关着**（默认就是关的）。开着的话 Unity 自己展的 uv1 会盖掉 `_CabinTubeLM` 的图集，而且它也在 0…1 里、下面的 uv1 检查看不出来，所以菜单单独查这一项，开着就报错（只报，不改：改了要写 `Bus.fbx.meta`）。
- 场景里别的灯（沙盒默认的 Directional Light）会被**关掉**（可以 Undo），切片只吃管灯的光照图。铬件、立柱的高光来自场景默认的反射（天空盒），不是车厢里的反射探针。
- 缺物体（旧的 FBX）时 Console 报错、点名缺哪个，其余照搭。

**全局量组件 `Scripts/LanbaiBusSliceGlobals.cs`。** 世界里车厢 shader 读的全局量由 `LanbaiCabinDriver`（U#）每帧写；切片里没有驱动，`_Udon_CabinLightmap` 是 0，整个车厢就是黑的。这个组件是普通的 MonoBehaviour（不是 UdonSharp：切片场景是本地测试场景，不上传），`[ExecuteAlways]`，在 OnEnable / Update 里写，类型和驱动一样（`Common/UdonGlobals.md`）：`_Udon_CabinLightmap` = 1（管灯开，`SetGlobalFloat`）；`_Udon_CabinAmbient` = (0, 0, 0, 1)（夜路 t = 30，线性）；`_Udon_CabinBleach`、`_Udon_CabinFade` = (0, 0, 0, 1)（float4，只读 .x）；穿越光带 `_Udon_CabinSlice` / `_Udon_CabinSliceColor` 关。数值可以在组件上改。**不要把它放进世界场景**：会和车厢驱动每帧打架。

**FBX 要先重导出。** `Window_R1`、`Pole_R0` 是这次才从 `Cabin_Static` 里分出来的（`Source/finish_bus.py` 的 `SEPARATE`；`BusLayout.json` 多了一项 `slice`，列出切片要的物体名，`missing` 不空就是 FBX 旧了）。旧的 `Bus.fbx` 里侧窗和立柱还合在 `Cabin_Static` 里，菜单会报这两件缺，只搭出座椅和玻璃。车厢光照图的 uv1 是全车一起排的，分出来以后整张图集都重排了，所以要按第 1 节“重做一遍”的顺序**全部重跑**：`finish_bus.py` → `bake_lightmap.py`（烘的物体已经加上 `Window_*`、`Pole_*`）→ `weather_exterior.py` → `finish_bus.py --from-blend`。只换 FBX、不重烘 `Cabin_TubeLM.exr`，整个车厢的光照图都会错位。

**uv 层的顺序（座椅的 uv1，已修）。** `Lanbai/Cabin` 从 uv1 读 `_CabinTubeLM`，FBX 的 uv 按 Blender 里 uv 层的顺序进 Unity（第一层 uv0、第二层 uv1、第三层 uv2）。以前 D-36 的座椅导出的是 `UVMap, UVMetric, UVLightmap`：Unity 里座椅的 uv1 是米制的盒投影（约 −2.3…2.3），光照图在 uv2，整车和切片的 15 个座位都把 `_CabinTubeLM` 采错。现在 `finish_bus.py` 的 `lm_uv_order` 把每个进光照图的单独物体（`Seat_*`、`Window_*`、`Pole_*`）都排成 **`UVMap, UVLightmap, UVMetric`**（`Cabin_Static` 本来就是 `UVMap, UVLightmap`）：
- 正常导出时在存 `.blend` 之前排（`bake_lightmap.py`、`weather_exterior.py` 读到的就是排好的）；`--from-blend` 导出时再排一次，所以拿修之前存的 `.blend` 重导出也对。只是换层的顺序，uv 的数一个不变（层按名字读、删掉、按顺序加回去），所以已经烘好的 `Cabin_TubeLM.exr` 不用为这个重烘。
- `bake_lightmap.py`、`parts/texbake.py`、材质节点都按**名字**找 uv 层（`'UVLightmap'`、`'UVMap'`），不受顺序影响。
- 导出后按读回的 FBX 再查一遍：这三类物体的 uv 层不是正好这三层、这个顺序，就进 `readback problems`。
- 切片菜单还会查每件的 uv1，**对新导出的 FBX 什么都不做**（uv1 在 0…1 里，报告里写一句“uv1 = the _CabinTubeLM atlas”，不复制、不写文件）。它只是给旧 FBX 留的保险：uv1 出了 0…1、而 uv2 在 0…1 里，说明这个 `Bus.fbx` 是修之前导出的，切片就复制一份网格、把 uv1 和 uv2 对调，存到 `Generated/Meshes/<名>_uv1LM.asset`，并报一条警告：整车菜单用这个 FBX 会采错，要重导出。

**整车菜单的改动。** `Editor/LanbaiBusBuild.cs` 只改了可见性（`internal`）、材质文件夹参数（默认还是 `Bus/Materials`），外加一处：`Window_*`、`Pole_*` 和 `Cabin_Static`、`Seat_*` 一样用带管灯光照图的材质（`ModeFor`）。不加这一处，重导出 FBX 以后这两件在整车里会掉成“车外”的材质。别的物体的材质、层、组件都和原来一样。

**Blender 那边的核对**（10-25，在 `HEAD` 的 `Bus/Source` 快照上、换进这次的 `finish_bus.py` 和 `bake_lightmap.py` 跑的；输出都在临时目录，没写 `Models/`、`Textures/`）：
- `~/bpy/bin/python -I <快照>/Bus/Source/finish_bus.py --out <临时>/slicecheck --blend <临时>/slicecheck/bus_final.blend --no-part-bake`：69 个物体，读回没有问题。`Bus_fbx_readback.json` 里 `Seat_SeatR0`、`Window_R1`、`Pole_R0`（以及另外 14 个座位）的 uv 层都是 `UVMap, UVLightmap, UVMetric`，`Cabin_Static` 是 `UVMap, UVLightmap`。把读回的 FBX 按层的**序号**查：三件的第二层（Unity 的 uv1）都在 0…1 里，第三层是米制坐标（座椅约 −2.3…2.3）。15 个座位被重排了，`Window_R1`、`Pole_R0` 本来就是对的。
- `Window_R1` 14 556 顶点、28 044 三角形，`Pole_R0` 2 040 顶点、4 020 三角形，`Seat_SeatR0` 3 506 顶点、6 912 三角形（这是 `HEAD` 的座椅，还不是在重做的 672M 座椅）；顶点色照旧按位置算；外面的 `WinR1_Fillet`、`WinR1_Gasket` 留在 `Bus_Exterior_LOD0`。
- 单独测 `lm_uv_order`：把 17 件的层顺序打乱（座椅改回修之前的顺序，另外两件让 `UVMap` 不在第一层），排回来以后顺序对，每一层的 uv 和打乱前逐个相等，再调一次什么都不改。
- 用打乱后存的 `.blend` 跑 `finish_bus.py --from-blend`：17 件读回都是 `UVMap, UVLightmap, UVMetric`。
- 用排好的 `.blend` 跑 `bake_lightmap.py --res 256 --samples 4`（只是看它能不能跑）：`Cabin_Static` + 15 个座位 + `Window_R1` + `Pole_R0` 都按名字找到 `UVLightmap`，烘完了。正式的 1024²、96 采样没跑。
