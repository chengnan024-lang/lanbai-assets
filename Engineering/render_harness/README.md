# 渲染标准台（`Engineering/render_harness/`）

所有包共用的 Blender 参考渲染台。目的只有一个：**大家的参考图用同一个机位、同一个车壳、同一套 PPv2 调色、同一套量法**，这样包和包之间、参考图和本地的 Unity 截图之间，数字可以直接比。

写的人：总工程师。Blender 5.0.1（`bpy` 模块）、Cycles CPU。**没有 GPU，没在 Unity 里跑过**；调色的数学来自 `Grading/Tools~/engine/ppv2_engine.py`（照 PPv2 源码写的），bloom / 暗角是这里照 PPv2 源码移植的（见 `lbh/grade.py` 头注）。

---

## 0. 三分钟上手

```bash
# 环境（一次）
python3.11 -m venv ~/bpy && ~/bpy/bin/pip install bpy==5.0.1 numpy scipy pillow
# 下面所有命令都用 ~/bpy/bin/python（系统 python 没有 scipy）

# 1. 渲一张：你的场景脚本 + 主座位机位 + 第 4 幕的调色 + 第 4 幕色板
~/bpy/bin/python Engineering/render_harness/lbh_render.py \
    --scene <你的包>/Docs~/lookdev/scene_r03.py --cam hero --grade S4 --act 04 --t 155.10 \
    --out /tmp/<包>/r03 --note "r03 光晕收窄、云顶压暗"

# 2. 换个调色状态重出（不用重渲）：交叉淡化中、或加一个曝光事件
~/bpy/bin/python Engineering/render_harness/lbh_grade.py --in /tmp/<包>/r03 --grade S3+S4=0.4 --dev 0.5 --act 04 --out /tmp/<包>/r03_xf

# 3. 量本地推回来的 Unity 截图（同一套定义）
~/bpy/bin/python Engineering/render_harness/lbh_grade.py --png FromLocal/<幕>_test/xxx.png --act 04 --cam hero --t 155.10 --out /tmp/u7

# 4. 联系表、迭代总览、陌生人测试、并排对照
~/bpy/bin/python Engineering/render_harness/lbh_sheet.py contact --out sheet.png /tmp/<包>/r01 /tmp/<包>/r02 /tmp/<包>/r03
~/bpy/bin/python Engineering/render_harness/lbh_sheet.py iters   --out <包>/Docs~/iterations_overview.png <包>/Docs~/iterations
~/bpy/bin/python Engineering/render_harness/lbh_sheet.py stranger --out /tmp/<包>/stranger /tmp/<包>/r03/graded.png
~/bpy/bin/python Engineering/render_harness/lbh_sheet.py pair --out pair.png unity.png ref.png --labels "Unity" "参考"

# 自检（改了标准台以后跑）
~/bpy/bin/python Engineering/render_harness/selftest.py
```

示例场景：`examples/demo_moon_sea.py`（月下云海的极简版，也是自检用的）。

---

## 1. 场景脚本怎么写

一个 `.py`，里面一个函数 `build(ctx)`：往当前的 bpy 场景里加东西。标准台负责：清空场景、Cycles 设置、世界（默认全黑）、车壳、相机、渲染、调色、量数。

```python
def build(ctx):
    S = ctx['lbh_scene']                  # lbh/scene.py：U2B、mesh_object、mat_emission、unity_directional、import_unity_fbx…
    t = ctx['t']                          # 时间轴秒（--t，或机位自带的 t）
    S.import_unity_fbx('Gate/GateArms_v4.fbx')
    S.unity_directional('Moon', 1.0, '#D6E4FF', (-0.2059, 0.1392, 0.9686))   # Unity 平行光 E = 1（Inspector = E）
    ...
    return dict(what='第 4 幕 U7，r03')   # 可选：写进 metrics.json
```

`ctx` 里有：`t`、`cam`（机位 dict）、`eye`、`act`、`args`（`--set k=v` 传进来的）、`quality`（preview / final）、`U2B`、`lbh_scene`。

### 1.1 坐标和单位（最容易错的地方）

- **场景脚本里一律写 Unity 坐标**（米，x 右、y 上、z 前；车在原点、车头朝 +Z，世界往车后移）。`S.U2B(p)` 把 Unity 点换成 Blender 点（Blender = (x, z, y)）；旋转用 `S.unity_quat_to_blender(q_xyzw)`。按 `Tentacles/Source/lib/export_unity.py` 导出的 FBX 用 `S.import_unity_fbx()` 导回来，位置不变。
- **自发光 / 无光照**：`S.mat_emission(name, rgb_linear, strength)` 写进去的线性值就是 Unity 无光照 shader 输出的场景线性值（Cycles 自发光强度 1 = 像素值 1）。
- **平行光**：`S.unity_directional(name, E, 颜色, 指向光源的方向)`。Unity 的漫反射没有 1/π（白色 Lambert、强度 1、正入射 = 1.0），Cycles 的太阳光是辐照度、漫反射除以 π，所以内部写的是 **π × E**。VRChat 里 Inspector 值 = E（`CONTROL_总控.md` §3）。
- **环境光**：`S.unity_ambient_flat(rgb)` = 均匀的 Trilight（白色 Lambert 正好收到 rgb）。
- **点光 / 聚光**：Unity 的实时点光是旧式 range 衰减，Cycles 是平方反比——**不能照抄强度**，按灰卡各自校（圣经 §1.5 陷阱 2）。这里不提供换算。

### 1.2 车壳占位（`bus_shell.json`）

- 默认 `--bus bible_v2`：按圣经 §4.1 / §4.6 的**角度合同**挖窗（从主座位眼睛看：挡风 −50..+25 / −15..+22，门玻璃 +30..+65，天窗 −5..+25 / +40..+68，侧窗、后窗）。和门的渲染（`Gate/Source/gate_bus.py`）是同一套角度。
- `--bus local_v1`：本地 v1 车实测的视窗（`FromLocal/shots/s9_2_view_limits/`，眼睛 (0.70, 1.77, 0.20)）。想知道“在本地现在的车里看得见吗”用这个。
- `--bus none`：不要车壳（主视觉、key art）。`--bus fbx:<路径>`：用真车（总导演的 `Cabin/` 交了以后）。
- 外形：长 7.0、宽 2.08、地板 0.62、顶棚 2.45（`FromLocal/gate_context.md` §0）。内壁是中性暗灰，**只为构图和遮挡**；`--interior-ambient r,g,b` 给内壁一点环境光（代替 `_Udon_CabinAmbient`）；`--glass` 加 4% 菲涅尔的薄玻璃。
- 窗洞是从眼睛出发的棱锥挖的，所以**只有从这个眼位看，窗的角度才准**。换眼位（过道、后窗）时窗框的形状是近似的。

### 1.3 机位（`cameras.json`）

| 名字 | 是什么 |
|---|---|
| `hero` | **标准机位**：主座位 (0.55, 1.70, 2.05)、正前、1920×1080、水平 90°。= 本地门测试 U7 截图的机位 |
| `hero_up60` / `hero_galcore` / `hero_down` / `hero_door` / `hero_side` / `hero_aisle_seat` / `hero_rear` / `hero_skylight` | 圣经 §1.8 截图协议要的几个视向（同一个眼位） |
| `hero_journey` | `LB_Journey.heroEye` (0.70, 1.77, 0.20)：本地 v1 车的主座位（诗句的位置按它算） |
| `vr_left_fwd` | VR 单眼近似（1832×1920、竖直 100° → 水平 97.3°），量 VR 下的 APL ≤ 150 |
| `gate_U6` … `gate_key` | 门的 9 个机位（带时刻），原样抄自 `Gate/GateLayout_v2.json` |

`--yaw / --pitch / --hfov / --res` 可以临时改。**新机位请写进 `cameras.json`**（告诉总工程师），不要在包的脚本里各写一份。Unity 那边：`localEulerAngles = (−pitch, yaw, 0)`，Field of View 填竖直角（16:9 下水平 90° = 竖直 58.72°）。

两个主座位眼位不一样（`CONTROL_总控.md` §3 说过）：门用 (0.55, 1.70, 2.05)，本地 v1 车是 (0.70, 1.77, 0.20)。**报告里写清用的哪一个**；`metrics.json` 的 `cam` 栏会自动记下来。

### 1.4 质量

`--quality preview`（默认）：机位分辨率减半、48 采样 + OIDN 降噪，960×540 一张十几秒到一分钟。`--quality final`：全分辨率、384 采样。`--samples`、`--res` 可以直接给。4 核机器上 final 一张几分钟到十几分钟，**先用 preview 迭代，定了再出 final**。

---

## 2. 调色（PPv2 模拟）

- `--grade S4`：一个场景 profile（`Grading/Tools~/inputs/grades_engine.json` 里的**引擎解**，不是圣经附录 B 的手抄值）。
- 可叠：`--grade S3+S4=0.4` = S3 权重 1、S4 权重 0.4（PPv2 的语义：按 priority 从低到高，每个参数 `lerp(当前, 覆盖值, w)`，从 PPv2 默认值开始）。
- `--dev 0.5`：这一帧的曝光事件 ΔEV。标准台按圣经 §1.4 自动解 `EXPO_UP` / `EXPO_DOWN` 的权重（w = ΔEV/(4 − b)）。
- `--lens clean`：桌面镜头层（暗角；**颗粒不模拟**，它是噪声，对 APL 的影响可以忽略）。**和本地的桌面截图比的时候加上**（本地截图里 LENS_CLEAN = 1）；VR 用 `--vr`（没有任何镜头层）。
- bloom 按 PPv2 fastMode 的源码移植（半分辨率金字塔、二次软膝阈值、4-tap 下采样 / 上采样），阈值和 clamp 是 gamma 值（圣经 §1.4）。`metrics.json` 的 `bloom_share_of_APL` = 开 bloom 和关 bloom 的 APL 差。
- `--bloom-tint double`（默认）：按 Unity 的实际行为，bloom 的颜色被线性化**两次**（PPv2 `Bloom.cs` 用 `MaterialPropertyBlock.SetColor` 传已经是线性的颜色，线性工程里会再转一次；见 `Engineering/给总导演.md`）。`Grading` 做了补偿以后改用 `single`。白色的 bloom 两种一样。
- 输入必须是**场景线性**：标准台把 Blender 的 View Transform 设成 Standard、曝光 0，EXR 里存的就是线性值，**不要在场景脚本里改色彩管理**。

## 3. 量的数（`metrics.json`）

定义和门的 `gate_metrics.py`、本地门测试的报告一致（已经用本地的 `U7_unity_t155.10.png` 核对：APL 35.1、亮度 < 12 占 24.77%、L\* > 85 占 0.65%、最亮 2000 px 外框 (970, 365)–(1003, 461)，四项都和本地报告的数一样）。

| 键 | 是什么 | 对照 |
|---|---|---|
| `APL` | sRGB 显示码的 Rec.709 亮度平均，0–255 | 圣经 §2 每一段的目标（`target`，按 `--t` 查 `Art/tools/v21/scene_data_v21.py`），±15% |
| `EV_display` | log2(显示线性亮度平均)，爬升律的 L | §1.8 |
| `brightest` | 最亮的 2000 px（1080p 下；别的分辨率按像素数缩放）：外框、重心、重心的方位 / 仰角、分成几团（`clusters_ge5pct` = 占 5% 以上的团数） | §1.3 第 1 条：每帧一个最亮点，在眼睛该去的地方 |
| `purple_pct` | h_ab 290–325 且 C\* > 15 的占比 | §1.3 第 4 条：第 4、4c 幕以外 ≤ 2% |
| `violet_strong_pct` / `lavender_act6_pct` | C\* > 30 的紫（第 4 幕 ≤ 10%）；h 285–330 且 C\* > 12（第 6 幕 ≤ 2%） | §1.3 第 4 条 |
| `palette` | 本幕色板每一色：最接近的那 1% 像素的 ΔE76、ΔE < 10 的像素占比；每个像素到最近一色的 ΔE（中位、p90） | `Art/palettes/`、`scene_data_v21.SCENES` |
| `top25_Lstar` | 画面上 1/4 的 L\*（平均、中位、p90） | 门测试的“上 25%” |
| `clip_black_pct` / `clip_white_pct` | 纯黑（三通道 ≤ 3）、纯白（≥ 252）的占比 | §1.3 第 5 条：大于 2% 不许 |
| `luma_lt12_pct`、`Lstar_gt85_pct` | 门的两个数 | |

色板用 ΔE76（CIE Lab，D65）。ΔE 中位数大不一定是错（色板只列关键色），要看每一色的 `closest_dE_p1`：某个关键色在画面里根本找不到（p1 很大），才说明画面缺了它。

## 4. 迭代存档的约定（`PLAN_总导演.md` 第四节）

每一轮一个目录：`<包>/Docs~/iterations/NN_<一个词>/`，放 `graded.png`（可以缩到 1280 宽）、`metrics.json`、`note.txt`（一句话：这一轮改了什么）。`--note` 会自动写 `note.txt`；把 `--out` 目录里的这三个文件拷过去就行（**不要提交 `linear.exr` / `linear.npy`**，它们只在 `/tmp`）。交的时候：

```bash
~/bpy/bin/python Engineering/render_harness/lbh_sheet.py iters --out <包>/Docs~/iterations_overview.png <包>/Docs~/iterations
```

## 5. 陌生人测试

`--out` 目录里自动有 `stranger/img_<hash>.png`（640 px 宽、没有字、文件名不透露意图）和一个提问文件。开一个**不给任何背景**的 agent，只给它这张图和提问文件里的那句话。它的回答原样记进评审稿。

## 6. 已知的近似（诚实版）

1. **不是 Unity**：Cycles 的路径追踪 ≠ Unity Built-in 的前向渲染。材质要和 Unity 一致，最好的办法是把 shader 的数学移植成 numpy / 发光节点（门的做法），场景里尽量用 `mat_emission` 写确定的线性值；Principled BSDF 的高光、多次弹射在 Unity 里没有。
2. **点光 / 聚光**的衰减和 Unity 实时灯不同（§1.1）。
3. **bloom** 是照源码移植的，但没和 Unity 逐像素对过；**颗粒**不模拟；`Dithering` 不模拟。
4. **VR**：只是单眼的近似视场，立体视差、SPS-I 都不模拟。
5. **车壳**是角度合同的占位，不是真车。真车（`Cabin/`）来了就换 `--bus fbx:`。
6. 透明叠绘（FSE）不在这里量——每个包按自己的透明层算，交给总工程师记进 `Engineering/ledgers/`（算法见那边的 README）。
