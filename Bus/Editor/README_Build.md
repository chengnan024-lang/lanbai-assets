# `蓝白/Build/车`（`Bus/Editor/LanbaiBusBuild.cs`）

**没在 Unity 里跑过**：只过了 `bash Common/Tools~/compile_check/check_cs.sh Bus`（Roslyn，editor 一遍：OK）。UdonSharp、VRCStation、`LanbaiCabinDriver`、`LanbaiWipers` 都用反射找，所以没有这些程序集也能编；找不到时 Console 的报告里会写“要手动加什么”。

## 菜单做什么（可以反复点：先删掉上一次的 `Lanbai_Bus`）

1. 读 `Assets/Lanbai/Bus/Models/Bus.fbx` 和 `BusLayout.json`。FBX 实例化到根物体 `Lanbai_Bus` 下、原点、不旋转，**解包**（之后 FBX 更新了就再点一次菜单）。
2. 材质建在 `Assets/Lanbai/Bus/Materials/`（已有就更新），按 Blender 的材质名 `M_Bus_<名>` 对 `build_bus.py` 的 MAT_TABLE（脚本里抄了一份）和圣经 §4.2：
   - `Cabin_Static` → `M_Bus_<名>`（`Lanbai/Cabin`，`_UseTubeLM` 1、`_CabinTubeLM` = `Cabin_TubeLM.exr`）；
   - 其余 `Cabin_*`、车门 → `M_Bus_<名>_NoLM`（`_UseTubeLM` 0、常数 E）；
   - `Bus_Exterior_LOD0/1` → `M_Bus_<名>_ExtAtlas`（uv1 图集 `Bus_Exterior_Albedo_2048` + `Bus_Exterior_Mask_2048`，不吃车厢光）；
   - 轮子、雨刮 → `M_Bus_<名>_Ext`；
   - `Cabin_Curtains` → `M_Bus_Curtain_Cloth`（`Lanbai/ThinCloth`，一个材质管两侧）；
   - 每个 `Glass_*` → `Lanbai/BusGlass`，三种（雨套件 §5.2）：`M_Bus_Glass_Windscreen`（`_PaneFaceWind` 1、`_Wipers` 1、竖向水珠、α 0.06）、`M_Bus_Glass_Skylight`（横向水珠、α 0.08）、`M_Bus_Glass_Side`（侧窗、车顶斜面窗、后窗、眉窗、目的地窗、门玻璃：竖向、α 0.06）。玻璃不投影。
   - 细节贴图、磨亮 / 晒褪 / 开裂、立柱握手处、灯罩发光、收音机表盘：照 `Cabin/README.md` §2。
3. 车外 LODGroup（CONTROL §6 第 4 条）：新建 `Bus_Exterior`，LOD0 > 12 % 屏高、LOD1 > 0.5 %。
4. `Seats/`：每个座位一个 `Station_<名>`（主座位叫 `Station_SeatR0_HERO`），放在 `station_pos`、朝 +Z，`VRCStation`（Immobilize、seated、进出点 = 子物体 `Enter`）+ 一个触发盒子当交互目标。`Colliders/`：`colliders` 里的每个盒子（不可见，只有 BoxCollider）。
5. `HeadFill/`：两盏头像补光（点光、Not Important、不投影、culling = Player + PlayerLocal、`#E4F1F3`、强度 0.8、range 3 m）。
6. `LanbaiCabinDriver`：建物体、程序资产（`Assets/Lanbai/Bus/Programs/`，CONTROL §6 第 11 条）、填引用：所有 `Lanbai/Cabin` renderer（含车外：D-26 的洞要穿过车底）、窗帘、所有玻璃、座位中心、主座位、四扇门和关门的位姿、`journey`（场景里有 `LB_Journey` 就自动填）。
7. 雨刮：`Rain/Runtime/LanbaiWipers.cs` 在、FBX 里有 `WiperPivot_L/_R`，就建 `LanbaiWipers` 物体并填 `pivot`。缺一样就跳过，报告里写。

## 点完之后要看的

- Console 里 `[Lanbai Bus] built Lanbai_Bus` 的报告：有没有 `MISSING SHADER`、`texture missing`、`unknown material`、`no field`、“class not compiled yet”（第一次导入时脚本还没编完，再点一次）。
- **车厢立方图**：`M_Bus_Glass_*` 的 `_CabinCube` 是空的（报告会说）。在主座位眼位 (0.55, 1.70, 2.05) 只开管灯烘一张车厢立方图（不要在门附近烘、不要实时探针：门内 181 s 的教训），三个玻璃材质都填上。
- **`LB_Journey.cabinLights`** 拖进 `HeadFill_0/1`（它按 `_Udon_CabinLightmap` 的同一条曲线缩放强度）；用灰卡在座位处校到 `#585F64`（Inspector 值 = E，D-00）。
- **雨刮枢轴的朝向**：`LanbaiWipers` 要求枢轴的本地 +Y = 雨刮静止时的臂、+Z = 转轴。FBX 里不是的话要改 FBX 或加一层空物体。
- 主座位的 `VRCStation`：坐下去眼睛应该在 (0.55, 1.70, 2.05) 附近；`LB_Udon` 的座位脚本按名字找 station 的话，名字对一下。
- Project Settings → Player → Vertex Compression：TexCoord0–3 不压缩（CONTROL §6 第 8 条）。
- 分发层（`Director/`）重新生成一次，认出 `LanbaiCabinDriver`。
- 目的地牌：`Bus/Textures` 里还没有 `*DestBlind*` 字的贴图，所以牌子暂时不发光（报告会说）。
