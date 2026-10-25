# `_CabinTubeLM` 是什么、从哪来

- **不是 Unity 烘的。** 在 Blender 里由 `Bus/Source/bake_lightmap.py` 烘（圣经 §1.6 / §4.3：只有车、只开 10 根灯管；站灯、车头灯、天光都关），输出 `Bus/Textures/Cabin_TubeLM.exr`（RGBA half）。Unity 里**不要**对车厢做 Lightmapping，Cabin_Static 的 Contribute GI 关掉也行（它不进场景的光照贴图）。
- 采样：`Cabin_Static` 的 **uv1**（唯一的图集）。uv0 是米制的盒投影，给细节平铺用。
- **RGB = 管灯照度 E**（Unity 单位、线性 HDR；灯全亮时）。shader 里：`albedo × LM.rgb × _Udon_CabinLightmap`。校准：7 个中段座垫的平均 E = 0.80（`Bus/Docs~/bake_report.json`）。
- **A = AO**（0.5 m 半径）。shader 里：`albedo × _Udon_CabinAmbient × AO`。
- 导入（`LanbaiCabinImport.cs` 自动做）：sRGB 关、RGBAHalf、不压缩、Clamp、Bilinear、有 mip。压成 BC6H 也行（只要 HDR），但 A 通道会丢——所以不压。
- 没有 uv1 的物体（收音机、目的地牌、管灯罩、窗帘）：材质上 `_UseTubeLM = 0`，改用常数 `_TubeLMConst`（rgb = 那个位置的 E），AO 当 1。
- 车改了（`bus_spec.py` / `finish_bus.py` 重跑）就要重烘：uv1 图集跟着网格变。
