# 车的切片（座椅 + 侧窗 + 立柱）· 进引擎的五项检查 · 20261026-015952

**❌ 跑完了，有检查没过（退出码 1）**

- 测试：`bus_slice`（D-40 #1「车先出一个切片」；D-36 #1 近景按 VR 像素密度；D-40 #4 几何高光抗锯齿）
- 三层状态：Blender 离线 **云端填**；Unity 桌面 **fail**；头显 **not_tested**（工具不测头显）
- 工具 1.2.2，Unity 2022.3.22f1（批处理），显卡 NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11）
- 仓库：提交 `11c2f447c56444e171beb4f0cbe26fa8b505a6ab`，2026-10-26T01:39:27.181258-04:00 同步，条目「2026-10-26 approved serial delivery; current applied group manifests in delivery_0058」
- 场景：Assets/_LanbaiTest/bus_slice_new.unity；用时 71.2 s
- **交回**：把整个文件夹 `E:\IDMdownload\VRCC\dream\LanbaiReports/tests\bus_slice\20261026-015952` 拷到仓库的 `FromLocal/bus_slice/20261026-015952/`，再推。看到的问题写进 `FromLocal/bus_slice/问题.md`，分级 S0 阻断 / S1 严重 / S2 一般 / S3 建议。

## 检查项
| 结果 | 检查 | 量到 | 要求 | 说明 |
|---|---|---|---|---|
| ❌ fail | `no_compile_errors` | 1 | = 0 | 跑的过程中没有新的编译错误 |
| ❌ fail | `window_frame_05m` | 0.15 | ≥ 0.3 | 总导演 10-26：画面里至少 30 % 是窗框 / 胶条（Window_R1：铝框、胶条、横档、扇框、窗扣；玻璃是另一个物体，不算）。不过就是机位没对上，改 look_at_anchor |
| ❌ fail | `window_frame_10m` | 0.09 | ≥ 0.3 | 同上 |
| ⚠️ warn | `no_console_errors` | 1 | = 0（不卡） | 跑的过程中 Console 没有 Error（默认只警告；测试定义可以改成必须） |
| ⚠️ warn | `has_lightmaps` | 0 | ≥ 1（不卡） | 光照图接缝那一项要先有光照图（D-40 #1 第 4 项）。车用预烘的 _CabinTubeLM（D-32，uv1）时 Unity 的光照图是 0 张，所以只警告；接缝照样看近景图 |
| ⚠️ warn | `pillar_shimmer` | 0.03 | ≤ 0.005（不卡） | 立柱 / 铬扶手：头部微动里来回跳的像素（初值，切片第一次实测后定） |
| ⚠️ warn | `window_shimmer` | 0.01 | ≤ 0.005（不卡） | 初值 0.005，先不动（总导演 10-26）：Blender 里 1.0 m 三台是 0.0059–0.0068，但 Blender 没有高光抗锯齿，等阿白的 Unity 数再定。机位改成对着窗框的角以后，画面里铝边多了，这一项会比原来的“全是玻璃”高 |
| ✅ pass | `steps_ok` | 0 | = 0 | 每一步都跑成功了 |
| ✅ pass | `no_exceptions` | 0 | = 0 | 跑的过程中 Console 没有异常（工具自己的不算） |
| ✅ pass | `no_undeclared_writes` | 0 | = 0 | 沙盒和 allowed_writes 以外没有文件被改 |
| ✅ pass | `project_settings_untouched` | 0 | = 0 | ProjectSettings 没被改 |
| ✅ pass | `ppv2_effective` | 1 | = 1 | 截图经过了 PPv2（开 / 关 PPv2 各渲一张小图，要不一样） |
| ✅ pass | `setting_vertex_compression_off` | 1 | = 1 | Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了 |
| ✅ pass | `seat_crunch_psnr` | 48.43 | ≥ 38（不卡） | 0.5 m 处 Crunch 和不压缩比 ≥ 38 dB（初值；低了就是细节被压没了，D-40 #1） |
| ✅ pass | `window_crunch_psnr` | 75.08 | ≥ 38（不卡） | 同上 |
| ✅ pass | `pillar_crunch_psnr` | 53.34 | ≥ 38（不卡） | 同上 |
| ✅ pass | `normal_crunch100_vs_bc5` | 54.82 | ≥ 38（不卡） | 法线：只把法线做 Crunch（质量 100，ncrunch:100）和不压缩比；BC5 那一档看 tex.seat.bc5.seat_05m.psnr，两档别的贴图都是 BC7，差别只来自法线；比完总工程师给全片统一一条（D-40b #6） |

## 预检（只读）
- ✅ gpu：NVIDIA GeForce RTX 4060 Laptop GPU（Direct3D11，Direct3D 11.0 [level 11.1]，显存 7956 MB）
- ✅ resources：C:\ 剩 38.5 GB，E:\ 剩 67.6 GB，可用内存 14.2 GB
- ✅ consent：用户（当前聊天） 2026-10-26 同意（工具 1.2.2，测试 gate_clouds_test、tree_sample、flicker_probe、transitions_sweep、bus_slice、bus_dropin）；备份 E:\IDMdownload\VRCC\Backups\dream_20261025-000405.zip（在）
- ✅ unity：2022.3.22f1（要 2022.3.22f1）
- ✅ editor_state：Play False，编译中 False，导入中 False（要在编辑模式、编译和导入都完成后再跑）
- ✅ color_space：Linear（要 Linear）
- ✅ package:com.vrchat.worlds：3.10.5（要 3.10.5；读自 PackageManager）
- ✅ package:com.unity.postprocessing：3.4.0（要 3.4.0；读自 PackageManager）
- ✅ udonsharp：UdonSharp.UdonSharpBehaviour 在（UdonSharp.Runtime），随 VRChat Worlds SDK
- ✅ compile：scriptCompilationFailed False，Console 里的编译错误（含 UdonSharp 的）0 条（Console 共 22 条，原样在 console.jsonl）
- ✅ open_scenes：没有没保存的改动（Assets/Lanbai/Scenes/Lanbai_FullPreview.unity）
- ✅ sandbox：有上次遗留的沙盒（有标记），开跑时删掉重建
- ⚠️ grading：有旧的 Assets/Lanbai/Grades/，有套件的 Assets/Lanbai/Grading/；layer 4 =「Water」，layer 22 =「PostProcessing」。两套调色都在：工具不删，截图用的是参考相机上的那一套（PostProcessLayer 的 volumeLayer 写在 manifest 的截图记录里）
- ✅ sync_record：仓库提交 11c2f447c56444e171beb4f0cbe26fa8b505a6ab（2026-10-26T01:39:27.181258-04:00 同步，条目：2026-10-26 approved serial delivery; current applied group manifests in delivery_0058）
- ℹ️ git_status：工程不是 git 仓库

## 前置条件
- ✅ 文件夹 Assets/Lanbai/Common
- ✅ 文件夹 Assets/Lanbai/Bus
- ✅ 文件夹 Assets/Lanbai/Bus/Editor
- ✅ 类型 LanbaiBusSliceBuilder
- ✅ 菜单 蓝白/Build/车 切片

## 步骤
- ✅ [build] 菜单 蓝白/Build/车 切片（360.3 ms）
- ✅ [after_build] assert_object **/Slice_Seat（0.6 ms）
- ✅ [after_build] assert_object **/Slice_SideWindow（0.2 ms）
- ✅ [after_build] assert_object **/Slice_Pillar（0 ms）

## 截图
| 机位 | t | 尺寸 | APL | < 12 % | 参考 APL | 文件 |
|---|---|---|---|---|---|---|
| seat_05m |  | 834×614 | 45.19 | 0 |  | `shots/seat_05m.png` |
| seat_10m |  | 834×614 | 35.74 | 17.13 |  | `shots/seat_10m.png` |
| window_05m |  | 834×614 | 25.73 | 39.67 |  | `shots/window_05m.png` |
| window_10m |  | 834×614 | 17.79 | 68.66 |  | `shots/window_10m.png` |
| pillar_05m |  | 834×614 | 21.14 | 62.18 |  | `shots/pillar_05m.png` |
| pillar_10m |  | 834×614 | 19.62 | 62.25 |  | `shots/pillar_10m.png` |
| pillar_05m_stereo |  | 1,668×614 |  |  |  | `stereo/pillar_05m_approx_LR.png` 双眼近似：两台普通相机各偏 ±32 mm 分别渲染、左右并排；不是 SPS-I 单通道立体，不是头显测试 |
| seat_05m__raw |  | 834×614 | 45.12 | 0 |  | `tex/seat/seat_05m__raw.png` |
| seat_05m__bc7 |  | 834×614 | 45.14 | 0 |  | `tex/seat/seat_05m__bc7.png` |
| seat_05m__bc5 |  | 834×614 | 45.14 | 0 |  | `tex/seat/seat_05m__bc5.png` |
| seat_05m__crunch_q50 |  | 834×614 | 45.27 | 0 |  | `tex/seat/seat_05m__crunch_q50.png` |
| seat_05m__crunch_q100 |  | 834×614 | 45.24 | 0 |  | `tex/seat/seat_05m__crunch_q100.png` |
| seat_05m__ncrunch_q100 |  | 834×614 | 45.14 | 0 |  | `tex/seat/seat_05m__ncrunch_q100.png` |
| window_05m__raw |  | 834×614 | 25.73 | 39.67 |  | `tex/window/window_05m__raw.png` |
| window_05m__bc7 |  | 834×614 | 25.73 | 39.67 |  | `tex/window/window_05m__bc7.png` |
| window_05m__bc5 |  | 834×614 | 25.73 | 39.67 |  | `tex/window/window_05m__bc5.png` |
| window_05m__crunch_q50 |  | 834×614 | 25.73 | 39.66 |  | `tex/window/window_05m__crunch_q50.png` |
| window_05m__crunch_q100 |  | 834×614 | 25.73 | 39.67 |  | `tex/window/window_05m__crunch_q100.png` |
| window_05m__ncrunch_q100 |  | 834×614 | 25.73 | 39.67 |  | `tex/window/window_05m__ncrunch_q100.png` |
| pillar_05m__raw |  | 834×614 | 21.14 | 62.18 |  | `tex/pillar/pillar_05m__raw.png` |
| pillar_05m__bc7 |  | 834×614 | 21.13 | 62.18 |  | `tex/pillar/pillar_05m__bc7.png` |
| pillar_05m__bc5 |  | 834×614 | 21.13 | 62.18 |  | `tex/pillar/pillar_05m__bc5.png` |
| pillar_05m__crunch_q50 |  | 834×614 | 21.13 | 62.18 |  | `tex/pillar/pillar_05m__crunch_q50.png` |
| pillar_05m__crunch_q100 |  | 834×614 | 21.13 | 62.18 |  | `tex/pillar/pillar_05m__crunch_q100.png` |
| pillar_05m__ncrunch_q100 |  | 834×614 | 21.13 | 62.18 |  | `tex/pillar/pillar_05m__ncrunch_q100.png` |

## 动态序列（闪烁）
编辑器里普通相机逐帧渲染。**闪烁看 `shimmer`**：每帧同一姿态另渲一张高倍超采样的参考，量“测的图 − 参考”的亮度差（0–255）随时间的抖动，真实运动不算在里面。`motion_std` 含真实运动、`hf_raw` 也会混进正常的边缘运动，只作参考。`static` 序列是相机不动的对照（只剩画面本身的时间噪声）。热图在 `seq/<id>/heat_*.png`。**这是近似，不是头显。**

| 序列 | 种类 | 帧 | shimmer 平均 / p99 / 超阈值 | motion_std 平均 | hf_raw 平均 / p99 | APL 最小 / 最大 / 最大跳变 |
|---|---|---|---|---|---|---|
| pillar_micro | micro_motion | 90 | 0.9 / 9.09 / 2.855 % | 6.85 | 1.75 / 15.35 | 18.63 / 20.32 / 0.11 |
| window_micro | micro_motion | 90 | 0.71 / 4.26 / 1.303 % | 4.55 | 1.27 / 8.27 | 17.51 / 18.8 / 0.06 |
| seat_micro | micro_motion | 90 | 0.71 / 3.87 / 0.942 % | 5.06 | 1.36 / 11.54 | 34.14 / 36 / 0.12 |

## 贴图压缩对照（沙盒里的拷贝）
- `seat`：
  - raw：存储 85.33 MB；
  - bc7：存储 21.33 MB；seat_05m PSNR 54.82 dB
  - bc5：存储 21.33 MB；seat_05m PSNR 54.82 dB
  - crunch_q50：存储 3.13 MB；seat_05m PSNR 48.43 dB
  - crunch_q100：存储 3.56 MB；seat_05m PSNR 48.36 dB
  - ncrunch_q100：存储 17.01 MB；seat_05m PSNR 54.82 dB
- `window`：
  - raw：存储 34.67 MB；
  - bc7：存储 8.67 MB；window_05m PSNR 80.75 dB
  - bc5：存储 8.67 MB；window_05m PSNR 80.75 dB
  - crunch_q50：存储 1.67 MB；window_05m PSNR 75.08 dB
  - crunch_q100：存储 1.95 MB；window_05m PSNR 74.53 dB
  - ncrunch_q100：存储 8.67 MB；window_05m PSNR 80.75 dB
- `pillar`：
  - raw：存储 21.33 MB；
  - bc7：存储 5.33 MB；pillar_05m PSNR 63.74 dB
  - bc5：存储 5.33 MB；pillar_05m PSNR 63.74 dB
  - crunch_q50：存储 0.97 MB；pillar_05m PSNR 53.34 dB
  - crunch_q100：存储 1.11 MB；pillar_05m PSNR 52.82 dB
  - ncrunch_q100：存储 5.33 MB；pillar_05m PSNR 63.74 dB

## 项目设置（只查不改）
- ✅ vertex_compression_off：Player → Other Settings → Vertex Compression：要关掉 TexCoord0、TexCoord1、TexCoord2、TexCoord3、Color；现在的掩码 3846（ProjectSettings.asset 原文），都关了

## 写入
- 允许搭建脚本写的地方（沙盒规则的例外，3 条）：`Assets/Lanbai/Bus/Generated/**`、`Assets/Lanbai/UdonPrograms/**`、`Assets/SerializedUdonPrograms/**`。为什么：车的切片搭建菜单生成的网格、材质、贴图导入设置
- 沙盒 `Assets/_LanbaiTest/`（下次跑会删掉重建，也可以手动删）
- 搭建脚本按测试定义允许写的地方：0 个文件（清单在 manifest.json 的 writes.declared）
- **没声明的写入：0**
- 工具临时改过、已改回的（不算没声明的写入）：14 个（清单在 manifest.json 的 writes.tool_touched_restored）
- 工具不保存场景。

## Console
全部在 `console.jsonl`（开跑前 Console 里已有的、跑的过程中新来的、编译消息；每条带类型和堆栈）。错误 / 异常 / 编译错误共 1 条，前几条：
  - `[Lanbai Bus Slice] ERROR built Lanbai_BusSlice: 1 error(s), 1 warning(s) names from BusLayout.json 'slice' vertex compression: TexCoord0-3 and Color off (mask 3846, ProjectSettings.asset; bus_slice.j…`

## 头显里还要看的（工具不测；空着 = 没验过，不是过了）
- [ ] 铬件、倒角、立柱稍远一点（1–2 m）时闪不闪（D-40 #4 的几何高光抗锯齿开着）
- [ ] 贴图在 0.5 m 处是不是糊、细节有没有被压没（mip 和压缩）
- [ ] 光照图接缝：座椅和侧窗框上看不看得到接缝
- [ ] 法线强度：凸起和缝线读得出来、又不像塑料
- [ ] 对照板第 5 栏「头显里一句话」：每件写一句
- [ ] 远处一像素宽的细边、铬件、倒角：头显里爬不爬、闪不闪（工具的闪烁热图只是编辑器近似）
- [ ] 闭左眼、闭右眼各看一遍：两只眼看到的一样吗（工具的双眼图只是两台相机的近似）
- [ ] 帧时间：头显里实际的帧率 / 有没有掉帧（工具的 ms 是编辑器估算）
- [ ] （手动）对照板五栏（D-40 #1）：真车照片 / Blender 中性光 / Blender 定稿 / Unity 截图（这次的 shots/）/ 头显里一句话
- [ ] （手动）Crunch 免不免由总导演定；免的话下载账总工程师重算（车的下载上限 75 MB）
