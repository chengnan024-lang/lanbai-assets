# 云卡 v2 套件（Clouds_v2）· 给 Unity 一侧的说明

写的人：云端会话「云」（分支 `pkg/clouds`）。依据：圣经 v2.1 §1.6、§8.1 #4；总导演裁决 D-25（通道格式、云顶微晕、编码）、D-12（晨日方位 +30°）、D-21（紫带）、D-09（VR APL）。
**shader 和 C# 都没在 Unity 里编译过。** shader 过了共用检查（`Common/Tools~/compile_check`，DXC + Unity 2022.3.22f1 的 CGIncludes，32 个变体 0 错 0 警告）；C# 过了 Roslyn（0 错）。第一次在 Unity 里跑，请把 Console 原样推到 `FromLocal/`。

## 0. 先做什么（三步）

1. 把整个 `Clouds_v2/` 拷到 `Assets/Lanbai/Clouds_v2/`（`Common/` 要在 `Assets/Lanbai/Common/`：shader 用工程根路径 include `LanbaiGlobals.cginc`、`LanbaiFog.cginc`）。`Source/`、`Docs~/` 不用拷（拷了也没事，Unity 不编译 .py，`~` 结尾的文件夹不导入）。
2. 贴图的导入设置自动设好（`Editor/LanbaiCloudsV2Editor.cs` 的 `AssetPostprocessor`，只管 `Clouds_v2/Textures/`）。
3. 菜单 **蓝白/Clouds v2/Build Materials**：按 `Textures/cards_v2.json` 给每张卡建一个四边形网格（枢轴在平云底上）和一个材质（`Generated/`）。可以重复运行。

这一版只是**套件**：卡怎么摆、什么时候亮由各幕的包做（第 6 幕 `Act06_Dawn/`、第 8 幕 `Act08_Dusk/`，下一窗）。

## 1. 卡是什么（和 v1 的区别）

v1 把光、颜色、色调映射都烘死在 PNG 里（晨的阴影是薰衣草、暮的阴影是紫红，圣经作废）。v2 和门的 `Lanbai/GateCloudCard` 同一个思路：**卡里存的是白光下的光照，颜色在 shader 里给**。

| 贴图 | 通道 | 内容 |
|---|---|---|
| `<卡>_K.png` | R | 白色太阳（Unity 照度 E = 1）在视线右侧 **15°**：几乎在云正后方，暗的云体、亮的银边 |
| | G | 太阳在右侧 **80°**：侧光 |
| | B | 太阳在右侧 **150°**：几乎在你身后，整朵受光 |
| | A | 覆盖率（直通 alpha，边上的颜色已经向外推满，不会有黑边 / 白边） |
| `<卡>_S.png` | R | 上半球均匀白天光（辐亮度 1） |
| | G | 下半球均匀白地光（辐亮度 1） |

每个通道存 `sRGB(值 / 缩放)`：太阳通道 ÷ `kscale`（6）、天光通道 ÷ `sscale`（1.5），shader 再乘回来（材质 `_KScale`）。圣经 §1.6 原写“−1 EV、×2”：晨的云顶在 S6 下要场景线性 R ≈ 4，装不下，D-25 批准改成按通道缩放。

**着色**（`Shaders/Lanbai_CloudCard.shader`；`Source/cardshade.py` 是逐行的 numpy 移植，所有参考图和求解都用它）：
```
rel = 太阳与视线（两眼中点 → 卡的枢轴）的水平夹角，0..180°
key = R/G/B 三个太阳通道按 15° / 80° / 150° 分段线性插值（两端钳住）
c   = _SunColor × key + _SkyUpColor × S.r + _GroundColor × S.g      （线性；_SunColor 已含 E）
太阳在卡的左边：水平镜像（_Mirror：0 关、1 开、2 自动）
然后 LanbaiFog（雾色 = 该方向地平线的天）、底部融化、近眼淡出、软边（SOFTPARTICLES_ON）
```
同一张卡在任何方位都按当时太阳的角度亮；同一组卡换一组颜色就是另一个时刻（暮 → 蓝时可以连续变）。

## 2. 卡的清单

| 组 | 太阳仰角 | 相机 | 形状 | 用在 |
|---|---|---|---|---|
| `dawn` | 6° | 形状默认（略俯 0–4°；Strato 俯 14°） | Cumulus、Congestus、Bank、Puff、Wisp、Strato；条带 CloudSea 1、2 | 第 6 幕：云塔、云原上的云头、地平线一圈 |
| `duskU` | 1° | 从下往上 12° | Cumulus、Bank、Strato、Wisp | 第 8 幕头顶那组 |
| `duskD` | 1° | 从上往下 12°，形状左右翻过（“下面的云是别的云”） | Congestus、Cumulus、Puff、Strato | 第 8 幕脚下那组（8-ii 另一片天里 ×0.82、数量 70%，由第 8 幕的包摆） |

每张卡的尺寸、平云底的位置（`cloud_base_v`，UV，v = 0 在底边）、不透明框在 `Textures/cards_v2.json` 的 `cards`。**建议世界尺寸**（和 v1 一样）：Cumulus 120–300 m 宽、Congestus 150–400 m（第 6 幕的云塔放到 1.5–3 km 宽）、Bank / Strato 300–800 m、Puff 20–60 m、Wisp 40–150 m、条带高 ≈ 宽 / 4。

## 3. 颜色（材质上的数；`cards_v2.json` 的 `colours`）

颜色是**解出来的**：用代表卡（积云）在侧光（rel 70°）下，让阴影体（不透明像素里亮度 10–30 百分位的中位）落到圣经的云影色、受光顶（98 百分位）落到云顶色，按该幕的 PPv2 引擎模型调色后比（`Source/card_solve.py`）。未知数是日的色温与亮度、天光 RGB、地光（= 该幕 Trilight 的地色 × 增益）。**同一组的所有卡用同一组颜色**——光是一致的，不是逐卡调色。

| 组 | 目标 | `_SunColor` | `_SkyUpColor` | `_GroundColor` | 结果（rel 70°） |
|---|---|---|---|---|---|
| 晨 | 云影 `#8593AA`、云顶 `#F6DCC4` | (6.573, 2.355, 0.3508)（2400 K，亮度 3.11 ≈ 圣经 E 3） | (0.9995, 1.149, 1.634) | (0.8431, 1.079, 1.581)（= Trilight 地 `#8FA0BE` × 增益） | 云影 `#8593A8`、云顶 `#F5DCC9` |
| 暮 | 云影 `#363D59`、云顶 `#F0A878`（设计值） | 暮组渲完后解 | | | |

晨组 6 张卡在 15° / 80° / 150° 的量数见 `Docs~/cards_dawn.json`：侧光（80°）阴影四张积云类 `#808EA5`–`#8895AA`；薄云（Strato、Wisp）本来就透光，阴影更浅；**第 6 幕的紫规则（h 285–330、C\* > 12）六张卡、三个角度都是 0 %**。

**怎么在 Unity 里调**：整组变亮暗 = 三个颜色一起乘；阴影更蓝 = 只动 `_SkyUpColor`、`_GroundColor`；受光面更金 = 只动 `_SunColor`。改完请把数推回来，我更新 json。

## 4. 材质参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `_Billboard` | 1 | 1 = 绕枢轴的 yaw 公告板，朝**两眼中点**（两只眼看到同一张卡，竖直不转）；0 = 用网格自己的朝向（世界固定的面板） |
| `_Mirror`（MPB / 实例） | 2 | 0 关、1 开、2 自动（太阳在视线左边就镜像）。**自动在太阳正好在视线上（rel ≈ 0° 或 180°）时会翻**，那里的卡请由布局固定成 0 或 1 |
| `_Gain`、`_Alpha`（MPB / 实例） | 1 | 每张卡的增益、透明度（淡入淡出） |
| `_Melt` | (−10, 60, 0, 0) | 底部融化：从枢轴上 x 米起、y 米内从透明到不透明；w = 1 时改用世界高度 z（比如云原顶） |
| `_NearFade` | (30, 120) | 离眼 x → y 米淡入（近处的卡不贴脸） |
| `_SoftFade` | 40 | 软边（米），只在 `SOFTPARTICLES_ON` 变体里（相机有深度图，圣经 §1.6 的常开带阴影主光保证了）；关着就是硬边 |
| `_RimTame` | 0.6 | D-25：逆光时一像素宽的亮边，在卡在屏幕上变小（一个像素盖过两个以上纹素）时往云体的亮度收，免得爬 |
| `_FogCap`、`_FogHeightFalloff` | 1、0 | `LanbaiFog` 的封顶与高度衰减 |
| `_SunDirFallback` | 方位 +30°、仰角 6° | `_Udon_SunDir` 没写时用（D-12） |

队列 `Transparent-10`（2990），直通 alpha，不写深度。导入：sRGB 开、Clamp、mip 开（Preserve Coverage 关）、三线性、各向异性 2、BC7。

## 5. 量出来的数

见 `Docs~/cards_dawn.png` / `.json`（暮：`cards_dusk.*`）：每张卡在 15° / 80° / 150° 下的阴影色、云顶色、卡上的紫带占比、通道有没有裁顶。

## 6. 怎么重做

```
python3.11 -m venv ~/bpy && ~/bpy/bin/pip install bpy==5.0.1 numpy scipy pillow
cd Clouds_v2/Source
~/bpy/bin/python make_clouds_v2.py --set dawn --only Cumulus Congestus Bank Puff Wisp Strato 1 2   # 每张 5 遍 Cycles，4 核约 20–40 分钟
~/bpy/bin/python card_solve.py dawn        # 解颜色 + 更新 cards_v2.json 的 cards
~/bpy/bin/python card_sheet.py dawn        # 总览图与量数
```
`make_clouds_v2.py` 从 `Clouds/Source/make_clouds.py`（v1）import 形状、体积、取景和 alpha 清理，只换了光和导出。中间文件在 `$LB_WORK`（默认 `/tmp/lb/clouds`）。`sky_fit.py` 是暂停前做的“目标天”拟合（晨 / 暮 HDRI 拉到圣经目标），现在只给总览图当背景用；正式的天是天空会话的 `Lanbai/Sky` 预设。

## 7. 已知弱点（诚实版）

- 天光是**均匀的半球**：卡不知道天在朝日一侧暖、背日一侧冷。阴影的颜色是按圣经目标解出来的，平均对，但不会随方位变。
- 太阳只烘了一个仰角（晨 6°、暮 1°）；同一组卡用在别的仰角上光会不对。
- 三个角度之间是线性插值：在两个角度中间，影子会有一点“两层”（和门的卡一样）。
- `_Mirror` 自动模式在 rel ≈ 0° / 180° 会翻，见 §4。
- 没在 Unity 里看过：BC7 压缩后暗部的色带、sRGB 采样后 ×6 的精度（太阳通道暗处每个码约 0.6 %）要本地看。
