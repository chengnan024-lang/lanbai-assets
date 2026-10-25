# `Lanbai_Overlay` v2 · 全屏遮罩球（黑、白、晨从黑里亮起、白收缩进灯里、第二次白）

写的人：云端会话「门内」，2026-10-23。依据：圣经 v2.1 §1.8（全屏遮罩球、爬升律、E17）、§6·5、§6·5→6、§6·9→10、§6·10、§6·10→11、§6·11→12，`calib_final.md` §D；「镜与白」的 `Act10_White/WhiteSchedule.json`（`overlay.shrink`）。
**没在 Unity 里编译过。** shader 只用 slang 查过语法和类型，C# 只用 Roslyn 对 Unity 2021.1 的引用程序集加 UdonSharp / VRC 的桩做过类型检查（§6）。第一次在 Unity 里用，请把 Console 原样推回 `FromLocal/`。

## 0. 拷什么、点什么

1. 把 `Overlay/` 拷到 `Assets/Lanbai/Overlay/`（`Tools~`、`Docs~` 带 `~`，Unity 不导入）。需要 `Assets/Lanbai/Common/Shaders/LanbaiVR.cginc`（main 里已有）。
2. 菜单 **蓝白/Build/Overlay**：在场景根上建 `Lanbai_Overlay`：
   - Unity 自带的球，缩放 3（半径 1.5 m），没有碰撞体；
   - 材质 `Materials/M_Overlay_Lanbai.mat`（shader `Lanbai/Overlay`），不投影、不收影、不用探针；
   - 组件 `LanbaiOverlay`（UdonSharp）和它的程序资产 `Runtime/LanbaiOverlay.asset`。
   脚本用反射加 U# 组件，找不到 UdonSharp 的编辑器类型时，会在 Console 里说清楚，这时手动加一次。可以重复点，会先删掉上一次建的。
3. 渲染器默认**关着**，由驱动打开。场景里**只放一个**。每个客户端都在 `PostLateUpdate` 里把它移到**自己的头的位置**：只跟位置，不跟旋转，旋转永远是 0。
4. 测试：进 Play 以后，在任何 U# 里调 `overlay.SetFlat(new Color(0.012f,0,0), 1f, 0f)`，应当全黑；`Hide()` 恢复。

## 1. 它做什么

- **半径 1.5 m，每个人一只，跟着自己的头。** Cull Front + ZTest Always + 队列 Overlay+100，盖住一切，包括 1.5 m 以内的东西。整片只有它用 ZTest Always。站起来或者坐在后排的人，看到的也是满屏的黑或白，不会是一块圆盘（v1 的问题）。
- **会被调色。** 它在 PPv2 之前画，所以填色要用当时起作用的 grade 那一行（`calib_final.md` §D），再乘 2^(−ΔEV)。乘法由组件做：**调用的人把这一帧 EXPO 助手实际加上的 ΔEV 传进来**（`LanbaiExposure.SetDeltaEV` 的返回值）。
- **抖动按物体空间的方向做哈希**（`normalize(v.vertex.xyz)`）。两只眼看到的是同一个值，所以 29 秒的白里不会出现双眼闪烁。球不转，所以这也就是世界方向。幅度 ±1.5 个 8 位码，三角分布。
- **两种 alpha：**
  - **FLAT**：所有方向同一个 alpha。
  - **CURVE**：`alpha(dir) = EvOverlayAlpha(saturate((tau − lead(dir)) / T), Lfrom, Lto, Lscene, Lover)`。全场只有**一条曲线**（`Lscene` 是一个数，按“极端视向”定，E17），方向只决定它**什么时候开始**：
    - `lead(dir)` 先取“其余方向”的领先秒数，再按顺序过最多 4 个**瓣**：`lead = lerp(lead, lead_i, m_i(dir))`，`m_i` 在瓣的半角以外有一圈 ≥ 30° 的 smoothstep 软边（§1.8 的擦除软边）；
    - 后面的瓣压前面的；
    - **不用瓣时，每个方向跑的是同一条曲线，和 FLAT 用同一条曲线算出来的逐位相同**（§5 检查 1）。
- **呼吸**：rgb × (1 + 幅度 · sin(2π · 0.1 Hz · t))。第 10 幕的白用 0.02。
- 什么都不画的时候（FLAT 且 alpha 为 0，或者调了 `Hide()`）渲染器关掉，不白占一遍全屏。

## 2. 组件 `LanbaiOverlay` 的接口（UdonSharp，纯本地）

| 成员 | 说明 |
|---|---|
| `SetFlat(Color fill, float alpha, float appliedDeltaEV)` | 所有方向同一个 alpha；fill 是线性填色（§D），组件自己乘 2^(−ΔEV) |
| `SetCurve(Color fill, float appliedDeltaEV, float tau, float T, float Lfrom, float Lto, float Lscene, float Lover)` | 一条 EV 线性曲线。`tau` = 当前时刻 − 曲线的 t0；L 都是相对线性亮度（APL 的 luma → L ≈ (luma/255)^2.2） |
| `SetLobe(int i, Vector3 worldDir, float halfAngleDeg, float leadSeconds)` | 第 i 个瓣（0–3）；半角 ≤ 0 表示不用 |
| `SetLeadElse(float leadSeconds, float softDeg)` | 瓣以外的方向领先多少秒；软边（度，最少 30） |
| `ClearLobes()` | 清掉所有瓣，领先归零 |
| `SetBreath(float amount)` | 0–0.05 |
| `Hide()` | 关掉 |
| `PickFill(Color desktop, Color vr)` | `IsUserInVR()` 选 VR 那一列（第 10 幕的白：VR `#D7E3E8`、桌面 `#E8F1F5` 的填色不同） |
| `static EvOverlayAlpha(x, Lfrom, Lto, Ls, Lo)` | `lens_tech.md` 附录 A，地板 0.004 |
| `static FillScale(dEV)` | 2^(−ΔEV) |
| `static DurationForExtreme(L)` | T = log2(L / 0.004) / 0.85（E17 的限速） |

**谁来调**：每一幕的驱动在自己的时间窗里每帧调一个 `Set*`；分发层保证同一时刻只有一个驱动拥有遮罩。用完调 `Hide()`。

## 3. 全片的用法（每一处的参数）

| 幕 | 时刻 | 调法 | 填色（§D，线性；“桌面 / VR”只在白里不同） |
|---|---|---|---|
| 出生 | 出生的黑（3 s）之后 | 站台（出发前）：`SetCurve(fill, 0, tau, 3, L黑, L站, L站, L黑)` 3 s。别处（D-43）：有驱动的遮罩窗口要在淡入期间开始的，**不淡入**，保持黑到窗口开始，交给驱动从黑升；否则 `ClearLobes()` 后 `SetCurve(fill, ΔEV, tau, T, L黑, L, L, L黑)`，L = 这一刻最亮的非白视向，T = log2(L / L黑) / 0.85，最长约 9 s（`README_Director` §0、§3 #8） | S1 行（本地定） |
| 4c → 5 · 黑 | 248.39 → 248.64 | `SetCurve(fill, ΔEV, t − 248.39, 0.25, L画面, L黑, L画面, L黑)`（变暗，免费）；ΔEV 同时 1.5 → 0 | S4c：`#030400`（门内的驱动做，见 `Act04c_Inside/`） |
| 剪 1 | 248.64 | `SetFlat(S6 行, 1, 0)`：同一帧硬切 S4c → S6 并换填色 | S6：`#090200` |
| 5 → 6 · 预滚 | 252.64 → 254.14 | `SetFlat(S6 行, alpha, 0)`，alpha 从 1 降到 `EvOverlayAlpha(0, L黑, L晨, L晨, L黑)`（把黑抬到地板） | S6 |
| 5 → 6 · 日出 | 254.14 → 266.34 | `SetCurve(S6 行, ΔEV, t − 254.14, 8.65, L黑, L210, L210, L黑)`；瓣：天窗 / 天顶 lead 0（**`SetLeadElse(2.0, 30)`** 让其余方向晚 2.0 s）、下方 +2.2、太阳扇区（方位 +45°）+3.3 | S6 |
| 9 → 10 · 遮罩 | 1146.31 → 1149.31 | `SetCurve(S9b+WHITE_SAT 行, ΔEV, t − 1146.31, 3, L画面, L白, L画面, L白)` | 桌面 `#D6F5FF @ +0.57` / VR `#D5F6FF @ +0.06` |
| 10 · 白 | 1149.31 → 1178.46 | `SetFlat(S10 行, 1, 0)`，`SetBreath(0.02)` | 桌面 `#D5F0FF @ +1.42` / VR `#D3F0FF @ +0.83` |
| 10 → 11 · 收缩进灯里 | 1178.46 → 1186.46 | `SetCurve(S11 行, ΔEV, t − 1178.46, 5, L白, L夜, L夜, L白)`；瓣：管灯 lead 0、路灯 1.5、头顶的海 3.0（方向由「灯与假醒」给） | 桌面 `#D5F4FF @ +1.20` / VR `#D4F5FF @ +0.66` |
| 11 → 12 · 预滚 | 1240.46 → 1241.96 | `SetFlat(fill, alpha, 0)`，alpha 0 → a₀ = 0.004 / L填 | `#ADC8D5`（S11） |
| 11 → 12 · 第二次白 | 1241.96 → 1251.96 | `SetCurve(fill, 0, t − 1241.96, 8.0, 0.004, L填, 0, L填)`（**Lscene = 0**：圣经写的是 a = a₀ (L填 / 0.004)^x，就是这个）；瓣：左右侧窗 lead 0，`SetLeadElse(2.0, 30)` | `#ADC8D5`（S11） |
| 剪 3 | 1251.96 | `SetFlat(S12 行, 1, ΔEV = 0.8)` 同一帧硬切 | `#AABEC7`（S12） |

L 黑 = `#030409` 的亮度 0.0013（低于地板：曲线从 0.004 起，所以先用 FLAT 预滚）。L210 = (210/255)^2.2 = 0.652。

## 4. 新的全局量（要登记，见 `Act04c_Inside/给总控.md`）

`_Udon_OverlayColor`（已预留）：rgb = 填色 × 2^(−ΔEV)，a = FLAT 的 alpha · `_Udon_OverlayCurve`：x = tau、y = T、z = 模式（0 FLAT / 1 CURVE）、w = 呼吸 · `_Udon_OverlayLum`：(Lfrom, Lto, Lscene, Lover) · `_Udon_OverlayLobe0..3`：xyz 世界方向、w 半角（度） · `_Udon_OverlayLead`：四个瓣的领先秒数 · `_Udon_OverlayLeadElse`：x 其余方向的领先、y 软边（度）。
预留表里的 `_Udon_OverlayAlpha` 用不上（alpha 放在 `_Udon_OverlayColor.a`），可以收回。

## 5. 检查（`Tools~/overlay_model.py`：shader 算术的 numpy 移植）

`~/bpy/bin/python Tools~/overlay_model.py` → `Docs~/overlay_checks.json`、`Docs~/overlay_lobes.png`。

| 检查 | 结果 |
|---|---|
| 1 不用瓣 = 所有方向同一条曲线（与 FLAT 用同一条曲线逐位相同） | 通过 |
| 2 瓣的边是软的（领先秒数每度最多变 1/30 的差 × 1.5） | 通过 |
| 3a 晨（按 APL 210 建、每方向 8.65 s、天顶先、地平线 +2.0、下方 +2.2、太阳扇区 +3.3；场景亮度从地板到 L210 九档） | 最坏 **0.21 / 0.85 / 1.70 EV**（限 0.5 / 1.0 / 1.8）通过，与圣经 `ramp_checks_v21.json` 的 0.21 / 0.84 / 1.68 一致 |
| 3c 第二次白（1.5 s 预滚 + 8.0 s，侧窗先、车厢晚 2 s；场景 0.0005–0.03） | 最坏 **0.22 / 0.85 / 1.69 EV** 通过，与圣经的 0.22 / 0.85 / 1.69 一致 |
| 3b 白的 3 s 遮罩（只算遮罩本身） | 只报告：遮罩前的冲击和膨胀已经把画面推高 2.4 EV，整段 11.73 s 的核对在「镜与白」的 `white_check` |
| 3d / 3e 黑、收缩进灯里 | 只变暗，每个方向单调 |

## 6. 编译检查

- shader：`~/bpy/bin/python Act04c_Inside/Tools~/compile_check/check_shaders.py Overlay` → slang 通过（另外 lint：Header 里没有冒号、括号、逗号；没有先用后声明）。
- C#：`CSC=<Roslyn 文件夹> Act04c_Inside/Tools~/compile_check/check_cs.sh Overlay` → 运行时和编辑器脚本都通过（C# 9，警告当错误）。Roslyn 的环境：Ubuntu 的 `dotnet-sdk-8.0`（apt）+ NuGet 的 `unity3d.sdk 2021.1.14.1` 与 `microsoft.netframework.referenceassemblies.net472`。
- **还要请本地确认的 Udon 白名单**：`VRCPlayerApi.GetTrackingData`、`VRCShader.SetGlobalVector`、`Renderer.enabled`、`PostLateUpdate`。

## 7. 已知弱点（实话）

- 球心是头的追踪点，不是两眼中点（差几厘米）。方向性的擦除因此有几厘米的视差，1.5 m 的球上看不出来。
- 抖动加在调色之前的 gamma 空间里，调色以后幅度不再正好是 ±1.5 码（白里 Neutral 的斜率接近 1，基本不变）。
- `_Time.y` 驱动的呼吸在每个客户端各自的相位上，不同步（本来就是本地效果）。
- CURVE 模式下渲染器一直开着，曲线结束以后要由调用的人 `Hide()` 或改成 FLAT。
- 编辑器里（没有 ClientSim）`Networking.LocalPlayer` 是空的，球停在搭建时的位置（主座位眼位 (0.55, 1.70, 2.05)）。
