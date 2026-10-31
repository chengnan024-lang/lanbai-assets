# 车厢 shader 包（`Cabin/`）· v1 · 2026-10-24

`Lanbai/Cabin`（车厢所有不动的面）、`Lanbai/ThinCloth`（窗帘）、`LanbaiCabinDriver`（全片的车厢时间轴）。依据：圣经 v2.1 §4.2–4.8、§6·8 的窗帘之翼，总导演裁决 D-00、D-08、D-21、D-24、D-26、D-28，`Act07_Sea/README_Act07a.md` §9.1，门内 `给总控.md` 的 181 s 车窗反射。

**全部没有在 Unity 里编译过，也没有在 Unity 里看过一眼。** 只过了总工程师的编译检查（DXC + Unity 2022.3.22f1 的 CGIncludes 原件；C# 用 Roslyn + U# / VRC 的桩），见 §7。目标：Unity 2022.3.22f1、Built-in、VRChat SDK Worlds 3.10.5、UdonSharp、SPS-I。

---

## 0. 本地要做的事（按顺序）

1. 拷 `Cabin/` → `Assets/Lanbai/Cabin/`（`Bus/` 和 `Common/` 照旧在 `Assets/Lanbai/` 下）。`Editor/LanbaiCabinImport.cs` 会重设 `Assets/Lanbai/Cabin/` 和 `Assets/Lanbai/Bus/` 里贴图和模型的导入（§5）；拷完对 `Bus/` 右键 Reimport 一次。
2. **Project Settings → Player → Vertex Compression：TexCoord0–3 全部不勾**（CONTROL §6 第 8 条；uv0 是米制细节平铺、uv1 是 `_CabinTubeLM` 图集。脚本读不到这个设置，只能你来勾）。
3. 点菜单 **`蓝白/Build/车`**（`Bus/Editor/LanbaiBusBuild.cs`，说明见 `Bus/Editor/README_Build.md`）：它按 §2 的表建好全部材质（`Assets/Lanbai/Bus/Materials/`）、挂到 `Bus.fbx` 的各个物体上（`Cabin_Static` 用 `_CabinTubeLM`，其余 `_UseTubeLM` 0；车外 `Bus_Exterior_LOD0/1` 用 uv1 图集、`_CabinLight` 0）。车厢网格不进 Unity 的光照烘焙（`Editor/CabinTubeLM_说明.md`）。
4. 同一个菜单建 `LanbaiCabinDriver`（含程序资产）并填好引用：`cabinRenderers`（所有 `Lanbai/Cabin` 的 renderer，含车外——D-26 的洞要穿过车底）、`curtainRenderers`、`glassRenderers`（所有 `Glass_*`）、`seatCentres`、`doorPanels` + 关门位姿（第 11 幕在白里关门）、`journey`（场景里有 `LB_Journey` 时）。之后分发层（`Director/`）重新生成一次。
5. `LB_Journey` 那边按 `给总控_shader.md` §3 清掉 `SetBusAlpha` 的占位（`busRenderers` / `glassRenderers` 置空）。
6. 头显 / 桌面截图推回 `FromLocal/cabin_test/`（主座位眼位 (0.55, 1.70, 2.05)，桌面 1920×1080、水平 90°，ARGBHalf → PPv2 → 8 位）：
   - **t = 60**（第 2 幕，灯全亮）：正前、右转 90°、抬头 60°。看管灯 LM、天花孔、座椅磨亮、表盘。
   - **t = 170**（第 4 幕 U8 后）：抬头看天窗下的顶棚和座椅——**量裂口光照到的地方 C\* 和 h_ab**（D-08 要 C\* ≤ 12、h 230–290）。
   - **t = 181**：左右车窗，有没有映出车后的光唇（门内 181 s 的“人头侧影”）。
   - **t = 387 / 500 / 644**：抬头 60°，天窗边的洞和 3 cm 的边。
   - **t = 897.96 / 921.4**：俯 52°，D-26 地板洞框住的东西（对照 `Act07_Sea` 参考帧 `20_897_floorhole`、`21_921_floorhole`）。
   - **t = 950 / 958 / 965**：窗帘成翼、松开、溶进光。
   - **t = 962 / 1100 / 1145**：侵蚀到第 8 幕末、第 9 幕中、第 12 面镜后；脚下的地板补丁和自己的座位要在。
   - **t = 1180**：假醒，整个车厢完好。

---

## 1. 文件

| 文件 | 是什么 |
|---|---|
| `Shaders/LanbaiCabin.shader` | `Lanbai/Cabin`：Standard 光照的表面着色器（ForwardBase / ForwardAdd / ShadowCaster） |
| `Shaders/LanbaiThinCloth.shader` | `Lanbai/ThinCloth`：窗帘（包裹漫反射 + 透射、顶点动画、溶进光） |
| `Shaders/LanbaiCabinCommon.cginc` | 两个 shader 共用：漂白、侵蚀（FBM、阈值、3 cm 边、座位球、地板补丁、D-26 洞）、D-08 / D-21 限色器 |
| `Scripts/LanbaiCabinDriver.cs` | U# 驱动：全片的管灯、漂白、侵蚀、环境色、表盘、窗帘、D-26 洞、玻璃开关与反射增益 |
| `Editor/LanbaiCabinImport.cs` | `AssetPostprocessor`，只管 `Assets/Lanbai/Cabin/` 和 `Assets/Lanbai/Bus/` |
| `Editor/CabinTubeLM_说明.md` | `_CabinTubeLM` 从哪来（Blender 烘，不是 Unity） |
| `Tools~/cabin_numpy.py` | shader 颜色数学的 numpy 版 + 自测；写 `Docs~/` 的色块和曲线 |
| `Docs~/*.png` | `swatch_d08_limiter`、`swatch_bleach`、`curve_cabin_timeline`、`erosion_zones`、`erosion_floor_d26` |
| `给总控_shader.md` | 要总导演定的事（侵蚀公式、全局量类型、`LB_Journey` 要改的） |

---

## 2. 每个面的材质（圣经 §4.2；颜色是 Inspector 里填的 sRGB）

通用：`_Metallic` 只取 0 / 1。细节图在 `Bus/Textures/`，`_DetailTile` = 1 / 贴图边长（米）。`_UseTubeLM` = 1 的用 uv1 采样 `_CabinTubeLM`；没有 uv1 的（灯罩、收音机、目的地牌）填 0 和 `_TubeLMConst`（该处的 E，目测取周围座椅的读数）。顶点色：G 磨亮（`_WearAmount` 1 时生效）、B ≤ 0.75 晒褪、B > 0.75 开裂种子。
车外（`Bus_Exterior_LOD0/1`）：`_UseAtlas` 1，`_AtlasAlbedo` = `Bus_Exterior_Albedo_2048`（sRGB）、`_AtlasMask` = `Bus_Exterior_Mask_2048`（R 金属、G 光滑、B 湿（× `_Udon_Wetness` 把光滑推到 0.85）、A AO），都在 uv1；`_CabinLight` 0（不吃管灯 LM 和车厢环境色）、`_SHAmbientK` 1（用 Unity 的 Trilight）。轮子、雨刮同样 `_CabinLight` 0，但不用图集。

| 材质 | `_Color` | 光滑 | 金属 | 细节 / 顶点色 / 其他 |
|---|---|---|---|---|
| 座椅乙烯 | `#5A2126` | 0.45 | 0 | `Cabin_VinylGrain_N_0.25m` 0.35、tile 4；磨亮 `#6A3434` / 0.66、amount 1；晒褪 `#7A4A48` / 0.40、amount 1；开裂 `#8A6A60` / 0.20、amount 1 |
| 司机座 | `#5A2126` | 0.45 | 0 | 同上；磨亮光滑 0.70（座面） |
| 靠背扶手（铬） | `#CFD1D3` | 0.85 | 1 | 坑点 0.7 没做（§8） |
| 座椅框架 | `#3C3E3D` | 0.35 | 0 | 磨亮 `#3C3E3D` / 0.50 |
| 地板凸点橡胶 | `#323634` | 0.22 | 0 | `Cabin_FloorStud_N_0.20m`、tile 5；`_DetailMask` = `Cabin_FloorStud_M_0.20m`：`_MaskAlbedoMul` (1, 1.6, 0.92)（G 谷里的灰 ≈ `#555550`、B 斑驳）、`_MaskSmoothAdd` (0.05, −0.05, 0)；磨亮（过道）`#4A4B47` / 0.35 |
| 门口踏步包边 | `#B8BBBD` | 0.50 | 1 | 黄安全条单独一个材质 `#C9A227` / 0.40 / 0 |
| 下墙板 | `#D9D4C5` | 0.45 | 0 | 鞋痕 `#5B5A55` 用磨亮通道（G）：磨亮色 `#5B5A55` / 0.35 |
| 天花穿孔板 | `#E2DDCF` | 0.25 | 0 | `Cabin_CeilingPerf_N_0.12m`、tile 8.33；`_DetailMask` = `Cabin_CeilingPerf_M_0.12m`：`_MaskAlbedoMul` (0.15, 1, 1)（R 孔） |
| 管灯罩 | `#D8DBD6` | 0.60 | 0 | `_EmitMode` Tube、`_EmissionColor` 线性 (1.632, 2.024, 2.042)（= 填 `#E7FEFF @ +1.03`）× `_Udon_CabinLightmap`；死虫点 `_BugDots` 1 |
| 立柱、顶杆 | `#C0C3C4` | 0.55 | 1 | `_HeightSmooth` (1.62, 2.42, 0.80, 1)（离地板 1.0–1.8 m 握手处 0.80）；`_FadeResist` 0.3（立柱最后走） |
| 窗框、天窗框 | `#B8BBBD` | 0.45 | 1 | — |
| 窗胶条 | `#2B2B2B` | 0.30 | 0 | — |
| 仪表台 | `#353637` | 0.30 | 0 | 橘皮法线 0.4 没有贴图，暂用 VinylGrain 0.2 |
| 仪表 | `#353637` | 0.30 | 0 | `_EmitMode` Gauge、`_EmissionColor` (0.034, 0.117, 0.097)（`#5FA89A` × 0.3）、`_EmitTex` 的 A = 仪表的形状 |
| 方向盘 | `#2E2E2E` | 0.45 | 0 | 磨亮 `#2E2E2E` / 0.72（握处） |
| 收音机皮套 | `#4A2E1F` | 0.45 | 0 | 磨亮 0.60 |
| 收音机格栅 | `#B8BBBD` | 0.55 | 1 | — |
| 收音机旋钮 | `#CFD1D3` | 0.85 | 1 | — |
| 收音机刻度窗 | 白 | 0.30 | 0 | `_MainTex` = `_EmitTex` = `Cabin_RadioDial_512x256`（RGB 刻度面、A 背光）；`_EmitMode` Radio（× `_Udon_RadioDial`） |
| 目的地牌 | `#262626` | 0.30 | 0 | `_EmitMode` DestBlind、`_EmissionColor` (2.22, 2.28, 2.18)（`#F2F5F0` × 2.5）× `_Udon_CabinLightmap`；`_EmitTex` A = 镂空字（车内看是反字；字的贴图车包还没出） |
| 窗帘（ThinCloth） | `#A9BCCB` | 0.18 | — | 下摆 `#8898A8`；`Cabin_CurtainWeave_N_0.05m` 0.3、tile 20；`_Inward` 0 = 按车身中线 x −0.18 自动判断朝车内的方向（一个材质管两侧） |

所有材质：侵蚀的那一组参数用默认值（`_ErodeForm` 0 见 §4）。湿：`_WetDarken` 布 0.6、其余 1。

---

## 3. 全局量

**读**（全部来自 `Common/Shaders/LanbaiGlobals.cginc`，shader 不自己声明）：

| 全局量 | 用法 |
|---|---|
| `_Udon_CabinLightmap`（float） | 管灯：× LM、× 灯罩发光、× 目的地牌字 |
| `_Udon_CabinAmbient`（float4 rgb 线性） | 环境：反照率 × 它 × AO；侵蚀边 × 1.5；漂白的染色 |
| `_Udon_CabinBleach`（float4，读 .x） | 漂白 |
| `_Udon_CabinFade`（float4，读 .x） | 侵蚀；也决定座位球（0.97 → 1 放）和地板补丁（0.65 → 0.677 放） |
| `_Udon_CabinSlice` / `_Udon_CabinSliceColor` | 4c 穿越光带：软前沿 + 指数拖尾，w 覆盖、w < 0 从后往前退；a = 窗形权重（没 cookie，按朝向近似） |
| `_Udon_RadioDial`（float4 rgb） | 表盘背光 × 刻度图的 A |
| `_Udon_Caustics` / `Color` / `Tex` | `LanbaiCabinCaustics(posWS, nWS)`，含 7c 从下往上（.y = −1）；只在 ForwardBase |
| `_Udon_SeaLevel` / `_Udon_SeaMode` / `_Udon_Underwater` | SeaMode 1、2 时海面以下、或眼睛在水里：湿（光滑 → 0.85，布变暗） |
| `_Udon_MirrorPlane` | 第 9 幕：镜面处 2 cm 的水平光线（填 `#8D95FF @ +1.89`）× .y |
| `_Udon_MirrorRimLight` | 第 9 幕：8000 K 的镜缘光，E = .w（1 m 内钳住，外面平方反比） |
| `_Udon_SunDir` | 窗帘飞走的方向（w > 0 才用） |
| `_Udon_Fog*` 等 | 经 `LanbaiFog.cginc` |

**写**（`LanbaiCabinDriver`，`VRCShader.PropertyToID` + `SetGlobalFloat` / `SetGlobalVector`，值变了才写）：`_Udon_CabinLightmap`、`_Udon_CabinBleach`、`_Udon_CabinFade`，门内窗口 [177.55, 252.64] 之外还写 `_Udon_CabinAmbient`、`_Udon_RadioDial`（`_Udon_CabinSlice*` 只在 `Start()` 清零一次）。材质属性（MPB）：`_SeatSphere`、`_HoleOpen`、`_DoorBias`（车厢、窗帘；`_DoorBias` 是 D-33 #7a 的门组，957.4 → 965.4 从 0 到 1），`_ClothClock`、`_Sway`、`_Float`、`_Wing`、`_Release`、`_Dissolve`（窗帘），`_CabinReflGain`、`_TintStrength`、`_BaseAlpha`、`_DropOpacity`（玻璃：每块在侵蚀走过它时 1.5 秒淡掉，D-32 #8）；玻璃和窗帘的 `Renderer.enabled`。
**没有新的全局量。** 两处类型要登记表写清（`给总控_shader.md` §2）。

---

## 4. 光和“慢慢消失”怎么算的

- **管灯**：`albedo × LM.rgb × _Udon_CabinLightmap`（LM 在 Blender 里烘，`Editor/CabinTubeLM_说明.md`）。**环境**：`albedo × _Udon_CabinAmbient × AO`。两者作为自发光加进去；Unity 自己的 SH 环境（Trilight + 进了球谐的 Not Important 灯）从间接漫反射里减掉（`_SHAmbientK` 0），逐顶点灯留着（7c 的玫瑰点光走这里）。反射探针的高光照常。
- **主光**：唯一带阴影的平行光 `RenderSettings.sun = Gate_Lights/Moon`（D-24），Standard BRDF。车厢不加别的带阴影平行光。
- **附加灯（ForwardAdd）**：裂口光（车厢层上唯一的附加平行光）先过 D-08 限色器；所有附加灯加上去的颜色再过 D-21 紫带护栏（只管 h_ab 290–330、C\* > 8、L\* > 40；反照率不动，所以圣经色板的颜色本身不被改）。POINT_COOKIE、DIRECTIONAL_COOKIE 变体跳过（片里没有），ForwardAdd 不带阴影变体。
- **漂白**：反照率 → 亮度 × 0.9 × 环境色的色度，光滑 → 0.3。
- **侵蚀**：世界坐标 3D FBM（4 层值噪声，基准斑块 0.55 m），先按实测分布 [0.30, 0.70] 拉成近似均匀，再映射到 [−0.20, 0.25] 和阈值比，`clip`。阈值的结构照圣经，**默认把“前方程度”和“天窗项”取补**，因为照字面会让天窗边和车头最后走（`给总控_shader.md` §1，`_ErodeForm` 1 = 字面）。边：按 `s / |∇s|` 算世界距离，3 cm 内发 `_Udon_CabinAmbient × 1.5`——天空自己的颜色，不是橙。阴影 pass 同一个 clip。
- **保护**：本地座位 0.9 m 球（每个客户端按自己头的位置挑最近的座位，1 Hz）到 fade 0.97 → 1 才放；座位下 1.2 × 1.6 m 地板补丁（x −0.16…1.04、z 0.85…2.45）到 fade 0.65（第 1 面镜）开始放；立柱 `_FadeResist` 0.3。
- **D-26 地板洞**：只在地板高度以下（y < 0.70）的面上。`_HoleOpen` 0 → 0.5（F8b → F8b + 6 s）长到最小洞（x 0.25…0.85、z 2.78…3.30），0.5 → 1（→ 897.96）长到建议洞（x 0.10…1.00、z 2.45…3.40，`Act07a` §9.1 的方位 −22…+22°、俯角 38…70°）；圆角 0.22 m、边上 ±0.10 m 的 FBM 抖动、同样的 3 cm 边。洞压过座位球和补丁。洞会吃到门口踏步的一部分（门洞 z 2.62–3.27 在右墙）。保持到假醒。
- 量出来的各区被侵蚀比例：`给总控_shader.md` §1 的表、`Docs~/erosion_zones.png`。

---

## 5. 导入（`Editor/LanbaiCabinImport.cs`）

贴图：`*TubeLM*` → 线性、RGBAHalf、不压缩、Clamp、Bilinear、有 mip；`*_N_*`、`*_Normal_*`（座椅部件 `Part_<类>_Normal_<分辨率>`，D-44 评审）→ 法线图；`*_M_*`、`*Mask*`（含 `Part_<类>_Mask_<分辨率>`）→ 线性遮罩；其余（反照率、刻度面）sRGB。细节图 Repeat、各向异性 4。模型：不生成第二套 UV（uv1 是 LM 图集）、网格压缩关、法线导入、切线 MikkTSpace、不焊点、不导相机灯光动画。项目设置的 Vertex Compression 它改不了（§0 第 2 步）。

---

## 6. 驱动的时间表（`LanbaiCabinDriver`；标签值抄自 `FromLocal/cues.json`，`cues.json` 还没有的子标签抄自圣经 v2.1 §2.1）

| 标签 / t | 管灯 | 漂白 | 侵蚀 | 环境色（线性 = sRGB 转线性 × 系数） | 表盘 | 窗帘 | 玻璃 |
|---|---|---|---|---|---|---|---|
| < 0 | 1 | 0 | 0 | 0 | 0 | 静 | 开，反射 1 |
| 0 → 3 | 1 | | | | 噪音 ±10 %（≤ 2 Hz） | | |
| U1 17.50 | | | | | 信号 ±9 % | 12 s 内到 1.5 cm / 0.8 Hz | |
| U3 50.30 | | | | | 6 s 升到 ×2、6 s 落回 | 4 s 内到 4 cm / 0.6 Hz | |
| U4h 99.50 → U5 107.50 | 1 → 0.5（EV 线性） | | | | | | |
| U6k 129.10 | | | | 4 s 淡入月 `#232A3A × 0.3` | | | |
| U6 133.80 → U9 | 0.5 → 0.3125（30 s）；**闪烁读 `LB_Journey`** | | | | | | |
| 177.55 → 252.64 | | | | **门内驱动写** | **门内驱动写**（ein Lichtchen、D-02） | | 反射 0（4c，到 U12） |
| U9 179.55 | 150 % 0.2 s，0.25 s 到 0 | | | | | | |
| U12 248.64 → F0 251.64 | 0 | | | | 0，之后永不再亮 | | **关** |
| F0 251.64 → F1 281.86 | | 0 → 0.10 | | 晨 `#98A4B8 × 0.5`（252.64 起） | | | 开，反射 0.25 |
| F2h 363.26 | | 0.10 → 0.25（→ F5） | 0 → 0.25（√，→ F5） | 1.5 s 到浅海 `#6186A7 × 0.6` | | 4 s 内上漂 15 cm / 0.2 Hz | |
| F3e 474.36 → F3e3 556.36 | | | | → 深海 `#0F1E30 × 0.3`（EV 线性） | | | |
| F9s 921.86 → 出海 922.36 | | 0.25 → 0.5（→ 962.26） | 0.25 → 0.65（→ 962.26） | 1.5 s 到暮 `#828BAA × 0.45` | | 3 s 内漂浮停、4 cm / 0.5 Hz | |
| F10 942.26 → F10e 956.36 | | | | | | 翼 0.30 → 0.60 m、0.3 → 0.5 Hz | |
| F10e 956.36 | | | | | | 松开横杆，先直着往上过车顶线 + 0.35 m，再平滑地弯向 `_Udon_SunDir`（1.2 m/s²，≤ 6 m/s；离眼近时 ≤ 0.75 ×（离眼距离 + 已飞距离），D-32 #9） | |
| F10l 961.06 → 969.06 | | | | | | 溶进光，之后 renderer 关 | |
| F12 987.06 → 1009.21 | | | | → `#232A3A × 0.3`（EV 线性） | | | 反射回 1（1009.21） |
| 镜 1–12（1032.41 … 1125.55） | | 每面 +0.025（0.5 → 0.8） | 每面 +0.027（1.2 s，0.65 → 0.97） | | | | |
| F16 1149.31 | | → 1 | → 1（自己的座位走） | | | | **关**（到 1178.46） |
| 假醒 1178.46 | **1** | 0 | 0 | 0 | 噪音 ±10 % | 1.5 cm / 0.8 Hz | 开 |
| 1238.46 | | | | | 咔哒关 | | |
| 第 12 幕 1251.96 | 1 | | | | | 系着不动 | |

- **D-26 地板洞**（`_HoleOpen`）：F8b 877.96 → +6 s 长到最小洞（0.5），→ 897.96 全开（1），保持到假醒 1178.46。
- **接法**：`LanbaiTick(t)` / `LanbaiActivate(on)` / `LanbaiWindow()`（CONTROL §5）。窗口是 {−600, 100000}：全片，加上片尾以后（`LB_Journey` 的时钟过了 1729.96 还在走，停在“醒”），迟到的人、跳到片尾以后也拿到第 12 幕的状态；车厢是每一幕的画框，根物体不开关。`LanbaiTakesOverNothing()` 返回 true（Director §3 #7）：它的窗口不进 `windowsFlat` / `LanbaiCovered(t)`。`Start()` 里按 t = 0 写一遍全部全局量和 MPB（CONTROL §6 第 9 条）。
- **每帧的开销**：全局量最多 5 个 `SetGlobal*`（值变了才写，大部分帧 0–2 个）；窗帘动的时候 `curtainRenderers` 个 MPB 写（1 个网格就 1 次），D-26 洞长的 20 秒里 `cabinRenderers` 个；座位 1 Hz；第 4 幕读 `LB_Journey` 三个变量。
- 曝光：本包没有曝光事件，不实现 `LanbaiGrade`（曝光只由 `LB_Journey.ApplyGrades` 写）。
- 眼位：用的是车包的 (0.55, 1.70, 2.05)（= Gate `cameras.U7`、`bus_spec.EYE`），**不是** `LB_Journey.heroEye` 的 (0.70, 1.77, 0.20)；座位球中心 (0.55, 1.05, 2.05)。

---

## 7. 检查（没在 Unity 里编译过）

```
bash Common/Tools~/compile_check/setup.sh
python3 Common/Tools~/compile_check/check_shaders.py Cabin
  ---- 3 files, 24 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.
bash Common/Tools~/compile_check/check_cs.sh Cabin
  C# CHECK OK (0 assembly error(s), 0 lint warning(s)). Not a Unity compile: see README_compile_check.md.
python3 Cabin/Tools~/cabin_numpy.py
  OK（自测：Lab 往返、D-08 灯色 C* ≤ 12 / h 290、D-21 紫带里没有东西、圣经色不被改、fade 0 不切、座位球在、洞在 897.96 开、曲线对上 §4.8 表）
```
检查抓不到的：Unity 表面着色器生成器自己产生的代码（这里用的是生成器的 include 顺序 + 假入口）、FXC 独有的诊断、U# 编译器的白名单（`GetProgramVariable`、`MaterialPropertyBlock`、`VRCPlayerApi.GetTrackingData` 都是 U# 常用的，但要本地编一次确认）。

---

## 8. 诚实的已知弱点

1. 搭建菜单 `蓝白/Build/车` 有了（`Bus/Editor/LanbaiBusBuild.cs`），但同样没在 Unity 里跑过；§2 表里“没有贴图”的几项（目的地牌的字、橘皮、坑点）菜单也补不上。
2. **侵蚀公式等总导演定**（`给总控_shader.md` §1）；噪声范围 (−0.20, 0.25) 是我按 §4.8 表的几行对出来的，不是圣经给的。
3. **3 cm 的边按屏幕导数估距离**：边很斜、离得很远时宽度会抖；斜看的大面上偶尔一像素的闪。没在头显里看过。
4. **穿越光带的“窗形”是按法线朝向近似的**，没有窗的 cookie：光会落在两窗之间的墙上。要真的窗形，需要门内给一张车厢坐标的窗遮罩（或者把窗户的 z 区间编进 `_Udon_CabinSliceColor.a` 的定义）。
5. **D-08 只管附加平行光**：裂口光如果被做成 Not Important（进球谐），限色器管不到（球谐那份被环境色替掉了，所以不会紫，但车厢也不会被它照亮）。窗帘被冷白照到 C\* 15.9（h 275，不紫，但超过 D-08 的 12），没压。
6. **管灯罩的两端在跌落时发暗橙（§4.3 `#FF8A50` 5 %）没做**；第 12 幕“一根灯管的一端 3 % 微颤”也没做（一个 `_Udon_CabinLightmap` 管不到一根管子的一端）。死虫是程序生成的点，不是贴图。
7. **扶手铬的坑点、仪表台的橘皮法线、窗帘的竖向晒褪条（`#C4D2DC`，独立 512² 遮罩）没有贴图**：材质参数留了位置（`_MainTex`、`_DetailNormal`），车包出图后填。
8. 窗帘：每扇的“系起一半 / 松着 / 全开”只能在网格里做；飞走时每扇按世界位置的哈希错开，但仍是整扇平移（横杆不弯）。
9. 环境色在 7a 是按时间不是按深度；7c 的“玫瑰光自下”没进环境色（理由见 `给总控_shader.md` §6）。
10. 湿只看 `SeaMode` 1、2 和 `_Udon_Underwater`，没有水线本身的亮线。
11. `_CabinTubeLM` 的主座位座垫只有 E ≈ 0.48（校准按中段座垫平均 0.8，`给总控_shader.md` §8）。
12. 没有出参考渲染（只出了色块和曲线），所以没有 APL、紫占比的量。


## 2026-10-24 补：顶点色 R = 积灰 / 发黄
`_GrimeColor` / `_GrimeAmount`（默认 0）：反照率向 `反照率 × _GrimeColor × 2` 混，按顶点色 R；光滑度 × (1 − 0.5 × R)。搭建菜单给顶棚 `#D8CBA6`（管灯周围发黄；`_GrimeAbsolute` 1，不超过 sRGB 231）、下墙 `#8C8370`、地板 `#555550`（`_GrimeAbsolute` 1：直接混到这个灰，深色地板上的积灰是更浅的，§1.6 反照率下限）、仪表台 `#6A6355`、窗框铝 `#6B5A48`（四角积灰）开到 1。总导演 r03 后的意见“太新了”。

## 2026-10-25 补：D-40 #4 几何高光抗锯齿（`LanbaiCabinSpecAA`）

**没有在 Unity 里编译过，也没有在头显里看过。** 只过了编译检查和 numpy 自测（见本节末）。

**做了什么。** `Lanbai/Cabin` 的光滑度在 `surf` 里最后一次修改之后（部件遮罩、细节遮罩、积灰、磨亮、晒褪、开裂、高度带、湿、漂白都在它前面），再按法线在屏幕上的变化（`ddx` / `ddy`）放宽一次。ForwardBase（主光、反射探针的 mip）和 ForwardAdd（裂口光，以及别的加进来的逐像素实时光）都用放宽后的值；第 9 幕的镜缘光在这个 shader 里是 `_Udon_MirrorRimLight`，在 base pass 里按漫反射加进自发光，没有高光，这个滤波管不到它。阴影 pass 只写深度，不算它。调用在 `surf` 的顶层，外面没有分支（前面的 `[branch]` 块都已经关上），所以导数是好的。所有 `Lanbai/Cabin` 材质自动带上，搭建菜单不用改（`GetOrCreate` 不碰这三个属性，手改的值重建后还在）。

**公式**（Tokuyoshi & Kaplanyan 2019《Improved Geometric Specular Antialiasing》的“延迟”版，和 Filament 的 `computeKernelRoughness` + `normalFiltering` 同一套）：

```
k  = min(2 σ² (|ddx n|² + |ddy n|²), κ)
α² = (1 − s)⁴                       Unity Standard：感知粗糙度 = 1 − 光滑度，α = 感知粗糙度²，GGX 用 α²
s' = 1 − saturate(α² + k)^(1/4)
```

核点在加到哪个量上：加在 α²（论文里的 roughness²）上，不是加在 α 或感知粗糙度上。拿 Filament 的源码（`shaders/src/surface_shading_lit.fs`、`MaterialBuilder.h` 的默认值）对过一遍，一致；numpy 里另按 Filament 的写法独立算了一遍，2000 个随机样本差 < 2e-5。

| 属性 | 默认 | 说明 |
|---|---|---|
| `_SpecAAVariance` σ² | 0.15 | 像素滤波核的方差（论文 1/2π = 0.159，Filament 0.15）。**0 = 关，原样返回输入**（是 select，不是近似的“几乎不变”） |
| `_SpecAAThreshold` κ | 0.2 | 最多给 α² 加多少（论文 0.18，Filament 0.2）。κ 0.2 时，原本是镜面的面最多被放到光滑度 0.33 |
| `_SpecAAMapNormal` | 1 | 1 = 用带法线贴图的着色法线（论文延迟版的做法）；0 = 只用插值的顶点法线（Filament 的做法） |

**为什么默认用着色法线，而不是 Filament 的顶点法线。** Unity 的法线贴图是 BC5 / DXT5nm，z 是重建的，mip 里留不下法线的方差（做不了 Toksvig）；D-36 零件的遮罩 G（光滑）也没有按法线 mip 预滤。所以零件法线图里烘进去的滚边、缝线、圆角，只有在这里才会被滤到；D-40 #4 点名了倒角。代价：法线贴图很密、变化很快的地方（皮纹、地板凸点、天花孔），粗糙度按 2×2 像素块一格一格地变（d3d11 的 `ddx` 一个 quad 一个值），κ 把它封住了；而且这些面本来就糙，放宽的量看不太出来。立柱（`Steel`）、窗框（`Alu`）、铬件（`Chrome`）不是零件材质，也没有细节法线（`_DetailNormalScale` 0），两种取法结果一样。**座椅不一样**：D-36 流程里一个座位的管、框、坐垫、靠背合成一个 `Seat_<inst>`（`finish_bus.seat_parts`），只用一个零件材质 `M_Bus_Part_<type>`；`LanbaiBusBuild.PartMat` 给它 `_UsePart` 1 和烘的 `_PartNormal`，再对整个零件叠 `Cabin_SeatLeather_N`（强度 0.30）。所以顶管上的着色法线也带着烘的零件法线和皮纹，`_SpecAAMapNormal` 1 和 0 在座椅上（漆管、皮套和皮面都）结果不一样；在座椅材质上切 `_SpecAAVariance`，也是连皮面一起切。下面表里座椅那三行只算了管子本身的弯，是默认 1 时的下限；最坏（κ 封顶）漆管 0.35 → 0.22、裸弯角 0.50 → 0.28、皮套 0.66 → 0.32。皮纹叠到座椅的金属件上，是搭建菜单的事（`PartMat` 对整个零件调 `Detail`），归车包 / 总控定，不是这个滤波能决定的。头显里如果在座椅上看到块状的高光，或者弯角被放得太糙，把那个座椅材质的 `_SpecAAMapNormal` 改 0。

**成本。** 每像素约 15 条 ALU + 2 条导数指令；顶点法线的 normalize 和 lerp 再加约 6 条。没有贴图采样、没有关键字、没有新变体。

**`Lanbai/ThinCloth`（窗帘）不加。** 它的光照里根本没有高光：`LightingThinCloth` 只有包裹漫反射 + 透射 + 间接漫反射，`o.Specular` / `o.Gloss` 写 0，GI 调用不带光滑度（不取反射探针），`_Glossiness` 0.18 没有被读。没有可滤的东西，加了只多花 ALU。以后要是给布加高光：0.18 的 α² = 0.45，κ 0.2 也几乎看不出变化。

**numpy 的数**（`python3 Cabin/Tools~/cabin_numpy.py specaa`，20 px/°）。法线每像素转 10°：0.35 → 0.342、0.45 → 0.437、0.55 → 0.527、0.80 → 0.678。目标件在 1 m / 2 m 处的放宽后光滑度（管子正对视线处 / 偏 60° 处；座椅按 27145d8（r5，按 672M 重做）的 `Bus/Source/parts/seat.py`：漆管 Ø25（`R_T` 0.0125），顶管横段套 Ø55 黑皮套（`R_SLEEVE` 0.0275），两个弯角裸露，座椅再改尺寸就重跑一次；铬件按 HEAD 的 `parts/poles.py` `_Ring`、`parts/window.py` 窗扣的 1.2 mm 倒角和 `parts/driver.py` 门控拉杆的 r 0.006）：

| 件 | 原光滑度 | 1 m | 2 m |
|---|---|---|---|
| 座椅顶管（漆，`#3C3E3D`）Ø25，只算几何（下限，见上） | 0.35 | 0.349 / 0.345 | 0.345 / 0.330 |
| 同上，裸露的弯角磨处 | 0.50 | 0.497 / 0.489 | 0.489 / 0.459 |
| 顶管横段的黑皮套 Ø55，手扶处磨亮，只算几何 | 0.66 | 0.658 / 0.653 | 0.653 / 0.633 |
| 立柱 Ø32 不锈钢 | 0.55 | 0.548 / 0.541 | 0.541 / 0.515 |
| 立柱握手段 | 0.80 | 0.777 / 0.732 | 0.732 / 0.645 |
| 窗框铝，型材 1.2 mm 圆角上 | 0.45 | 0.298 / 0.265 | 0.265 / 0.265（κ 封顶） |
| 铬，1.2 mm 倒角（立柱上停车按钮下的铬环、推拉窗扣） | 0.85 | 0.375 / 0.331 | 0.331 / 0.331（κ 封顶） |
| 铬，司机的门控拉杆 Ø12 | 0.85 | 0.712 / 0.600 | 0.600 / 0.439 |

亚像素移动的闪（一行像素横穿管子，0–2 像素 32 步，主光的镜面点偏视线 30°，看整行高光能量和最亮像素的变异系数）：握手段 0.80 在 2 m 处，能量的 CV 从 0.58 降到 0.14、最亮像素从 0.66 降到 0.28；1 m 处 0.12 → 0.05、0.27 → 0.17。铬拉杆 Ø12（0.85）闪得最凶：能量 CV 1 m 处 1.30 → 0.20、2 m 处 2.04 → 0.26，最亮像素 1.31 → 0.34、2.04 → 0.38（不开时高光比一个像素还窄，挪一点就整个没了）。0.35–0.66 的几件（漆管、皮套、立柱非握手段）本来就不怎么闪（能量 CV ≤ 0.01、最亮像素 CV ≤ 0.06），开不开差不多。1.2 mm 的倒角在 1–2 m 只有 1–3 个像素宽，这个一行像素的模型量不了（覆盖的变化比高光的变化大），表里只有光滑度。**副作用**：滤波是各向同性的，管子顺着轴向没有法线变化，放宽的那一半白白浪费，所以细管上的高光会变暗变宽——握手段的高光总能量 1 m 处剩 77 %、2 m 处剩 51 %，铬拉杆剩 29 % / 14 %（相对超采样的真值；0.35–0.66 的几件损失 ≤ 6 %）。越光滑、越细的件暗得越多，铬件最明显。这些是点状高光（平行光、点光：主光、裂口光）的数，numpy 只算了这一种；反射探针里顺着管子拉长的高光（立柱上管灯的长竖高光）放宽后主要是变宽变模糊，应该暗得少，没有算。各向异性的版本要自己写 BRDF（Standard 的 GGX 只有各向同性），这次没做。硬边（拆开的法线、没有倒角）看不见：quad 不跨三角形取导数，那是几何边的锯齿，归 MSAA。

**头显里怎么看**（`bus_slice` 切片，主座位眼位 (0.55, 1.70, 2.05)，Play 模式里在 Inspector 改材质）：
1. 看这几件，各在 1 m 和 2 m：前排座椅背上的顶管（两侧和两个裸露弯角的漆管、横段的黑皮套）、Ø32 立柱的握手段、侧窗的铝框（圆角边）、立柱上停车按钮下面那圈铬环和侧窗的推拉扣（铬 0.85，1.2 mm 倒角）。头慢慢左右挪几厘米。
2. 把这些材质的 `_SpecAAVariance` 在 0 和 0.15 之间来回切。`M_Bus_Steel`、`M_Bus_Alu`、`M_Bus_Chrome` 各是一个材质，切一个就是那一类全切；座椅是零件材质 `M_Bus_Part_<type>`，切它就是连皮面一起切。按上面的数，预期：漆管和皮套几乎看不出差别（漆管本来就糙；皮套 Ø55，每像素转得少）；立柱握手段 2 m 处的高光不再爬、不再一闪一闪，但会暗一点、宽一点；窗框圆角边上那条一像素的亮线安静下来；铬环和窗扣的倒角从一闪一闪的亮点变成稳定的、发缎面的边（光滑度被封到 0.33–0.38）。
3. 座椅上 `_SpecAAMapNormal` 1 和 0 各看一眼，看三处：顶管两个裸露的漆弯角、黑皮套、坐垫的皮面。1 时皮面上有没有 2×2 的块状高光，弯角和皮套是不是被皮纹放得太糙（最坏 0.22 / 0.28 / 0.32，见上）。
4. 每件写一句（对照板第 5 栏）：0.15 时还闪不闪、立柱的高光是不是暗得不像抛光的不锈钢了、铬件还像不像铬。暗了就只把那一类材质的 σ² 降到 0.08–0.10，不要整个关掉。
5. 想要数：`bus_slice` 的微动序列 `pillar_micro` / `window_micro` / `seat_micro`，看 `seq.<id>.shimmer_mean` / `shimmer_frac`（测的图减同一姿态 4× 超采样参考图之后，逐像素亮度差随时间的标准差；`hf_raw_*` 带着正常的边缘运动，工程标了只作参考）。检查项是 `pillar_shimmer` / `window_shimmer`，`shimmer_frac ≤ 0.005`（初值，不卡）；`seat_micro` 没有检查项，只出数。用 0.15 跑一次，再把切片材质（`Assets/Lanbai/Bus/Generated/Materials/`）改 0 跑一次，两次的数一起推回。**两点要知道。** 一、这三条序列的相机是 1.0 m 的 `pillar_10m` / `window_10m` / `seat_10m`，2 m 那一档只能在头显里看。二、切片相机是 `"ss": 2`（按 40 px/° 着色再缩到 20），`ddx` 只有头显的一半、核只有四分之一，2× 本身又已经滤掉了大半的闪。numpy 按这个算（`specaa` 输出的最后一段）：立柱握手段 0.80 在 1 m 处能量 CV 关 0.004 / 开 0.002（头显那样 1 像素着色一次是 0.12 / 0.05），铬拉杆 0.64 / 0.15。所以切片里 0 和 0.15 的差，在漆管、立柱上基本看不出来，窗扣这类铬件会大一些；要在切片里看到头显那样的差，得把这三台相机的 `ss` 改 1 再跑一次（`bus_slice.json` 是工程的文件，我没有改）。

**检查**（不是 Unity 编译）：
```
~/bpy/bin/python Common/Tools~/compile_check/check_shaders.py Cabin/Shaders
  ---- 3 files, 24 translation units (DXC on, CGIncludes 2022.3.22f1): 0 errors, 0 warnings. NOT a Unity compile.
python3 Cabin/Tools~/cabin_numpy.py specaa
  specaa OK（平的法线不变；σ² 0 原样返回；每像素 10° 光滑度下降、只降不升、在 [0, 1] 里；和 Filament 写法一致；
  对 κ、σ²、每像素转角都单调不增，κ 封顶；x、y 导数一样算；立柱握手段 2 m 的闪至少减半；铬拉杆 2 m 的闪
  至少降到 1/4、能量剩不到一半；切片相机 ss 2 时立柱 1 m 的闪本来就少了 3/4 以上、滤波拿走的能量比 1 次着色少）
```
另做了一次反向检查：在临时拷贝里往这段代码塞一个没声明的名字，ForwardBase 和 ForwardAdd 的 8 个编译单元报错，ShadowCaster 的 4 个不报——这段确实在两个前向 pass 里编译、不在阴影 pass 里。整套自测（`python3 Cabin/Tools~/cabin_numpy.py`）现在先跑这一项；我是在临时拷贝里跑的整套（它会重写 `Docs~/` 的 PNG），通过。
