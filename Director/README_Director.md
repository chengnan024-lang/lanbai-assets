# Director · 分发层 v1.3（`Director/`）

维护：总工程师。**没在 Unity 里编译过**：C# 用 `Common/Tools~/compile_check/check_cs.sh` 做了 Roslyn 类型检查（editor + player 两遍、U# 规则），生成器跑过一次真生成（对门的 `LanbaiGateClouds` + 一个假的海驱动），生成结果和门的驱动一起编译通过、重复生成不变（幂等）。

## 0. 本地要做的（拷哪些、点哪个、改哪两行）

1. 拷 `Director/` → `Assets/Lanbai/Director/`（`Docs~` 不进 Unity）。
2. 拷完所有包的驱动以后：菜单 **蓝白/Director/1 Generate Dispatcher** → 等 Unity 重新编译 → **蓝白/Director/2 Wire Scene**（场景里建 `Lanbai/Director`、挂分发层、建它的 U# 程序资产、把场景里每个驱动填进去）→ **蓝白/Director/3 Report**（打印每个驱动的时间窗和重叠）。加了新包就重新点 1、2。
3. `LB_Journey` 改两行（**这是对 `LB_Journey` 的全部改动**，加上 `Engineering/README_集成.md` §3 的接管开关）：
   ```csharp
   public LanbaiActDispatcher dispatcher;            // Inspector 里拖 Lanbai/Director
   // Update() 末尾、算完 t 和 ApplyGrades 之后：
   if (dispatcher != null) dispatcher.LanbaiDispatch(t);   // 放在 ApplyGrades() 之前（它要读下面的 grade* 结果）
   // 出生的 3 秒黑场里调一次（圣经 §1.9：所有根物体在相机前激活 2 帧预热 shader）：
   if (dispatcher != null) dispatcher.LanbaiPrewarm();
   // v1.3（D-43：迟到的人只看到一次变亮，从黑开始、EV 线性、≤ 0.85 EV/s）。出生的黑开始时：
   if (dispatcher != null) dispatcher.LanbaiSpawnFadeBegin();   // 和 LanbaiPrewarm 放在一起
   // 出生的黑（3 s，圣经 §1.9）结束的那一帧，定一次：
   float T = beforeDeparture ? 3f : dispatcher.LanbaiSpawnFadeLength(t, lBlack);   // 站台（出发前）照旧 3 秒；别处按场景定，≤ 9 秒
   float L = dispatcher.LanbaiSpawnBrightestL(t);                // 淡入的目标亮度（这一刻最亮的非白视向）
   float handAt = dispatcher.LanbaiOverlayHandoverAt(t, t + T);  // [黑结束, 黑结束 + 淡入) 里第一个有驱动拿着遮罩球的时刻
   // handAt >= 0：不做淡入。遮罩球保持黑，一直到 t >= handAt 并且 dispatcher.LanbaiCoversOverlay(t) 的那一帧调
   //              dispatcher.LanbaiSpawnFadeEnd()，遮罩球交给驱动（不 Hide），驱动从黑往上升。
   //              （等了 handAt + 1 秒还没覆盖上，比如时间轴被拖走了：当作 handAt < 0，从这一刻起自己淡入）
   // handAt < 0： 自己淡入：overlay.ClearLobes(); 每帧 overlay.SetCurve(fill, dispatcher.gradeDEV, tau, T, lBlack, L, L, lBlack)，
   //              tau = 黑结束以后的秒数；tau >= T 的那一帧 overlay.Hide() 并调 dispatcher.LanbaiSpawnFadeEnd()
   // LanbaiSpawnFadeEnd 只认第一次（幂等）；不调的话 Begin 之后 15 秒当作已结束
   ```
   **接管开关（v1.1，2026-10-24）**：分发层按“这个驱动写什么”分开给窗口——
   ```csharp
   bool atm = extAtmosphere && dispatcher != null && dispatcher.LanbaiCoversAtmosphere(t);  // 这一帧不写 RenderSettings 的雾 / 环境色
   bool sun = dispatcher != null && extSun && dispatcher.LanbaiCoversSun(t);               // 这一帧不写主光
   ```
   （数组版：`atmosphereWindowsFlat`、`sunWindowsFlat`，t0, t1 成对。）**不要再用 `windowsFlat` / `LanbaiCovered(t)` 做接管开关**：那是所有驱动的窗口并起来，里面有不写 RenderSettings 的驱动（天空默认、门、第 9 幕），照它让出去那几段就没人写了（`Engineering/README_集成.md` §3）。它们只留给“关掉旧占位组”用。

## 0.5 曝光：驱动只算，`ApplyGrades` 唯一写（总导演 10-23 对镜子的裁决）

圣经 §1.4：一帧只有一个 ΔEV、PPv2 的权重只有一个写的人——就是本地的 `LB_Journey.ApplyGrades`。有曝光事件的包（镜子脉冲、白、以后的入水 / 出海……）在驱动里加**可选的第 4 个方法**：

```csharp
public float[] LanbaiGrade(float t)   // {ΔEV, WHITE_SAT 权重, WHITE_BLOOM 权重, 桌面镜头层乘数}，这一帧没有事件就 return null
```

分发层在窗口里的驱动 `LanbaiTick` 之后调它，汇总成 `gradeDEV`（相加）、`gradeWhiteSat` / `gradeWhiteBloom`（取大）、`gradeLensClean`（取小），`gradeOwned` = 有没有驱动报了。`ApplyGrades` 里：
```csharp
if (dispatcher != null && dispatcher.gradeOwned) {
    dEV += dispatcher.gradeDEV;                       // 然后照常 w = ΔEV/(4 − b) 解 EXPO_UP / EXPO_DOWN
    wSat = Mathf.Max(wSat, dispatcher.gradeWhiteSat);
    wBloom = Mathf.Max(wBloom, dispatcher.gradeWhiteBloom);
    lensClean *= dispatcher.gradeLensClean;
}
```
并且**删掉 `ApplyGrades` 里同一件事件自己的那一份**（例如镜与白的包装好以后，`starCross` 的镜子脉冲和白的冲击 / 膨胀不再由 `ApplyGrades` 算）——哪些要删，每个包合进 main 时写进 `Engineering/README_集成.md` §5。镜与白的 `ownsExposure = false` 就是这个模式。

## 1. 为什么分发层是生成出来的

UdonSharp 只有通过**那个类自己的类型**的引用，才能调另一个行为上带参数的方法（`LanbaiTick(float t)`）；对一个笼统的 `UdonSharpBehaviour` / `UdonBehaviour` 只能 `SendCustomEvent`，传不了参数。所以分发层对每个驱动类有一个带类型的数组（`d0`、`d1`……），代码由编辑器脚本按工程里实际有的驱动生成。好处：`CONTROL_总控.md` §5 的接口一个字都不用改，包按原样写就能接上（门的 `LanbaiGateClouds` 已经是这个样子）。

生成器怎么认驱动：`UdonSharpBehaviour` 的子类，且有这三个公开方法——`void LanbaiTick(float)`、`void LanbaiActivate(bool)`、`float[] LanbaiWindow()`。

## 2. 每帧做什么

```
for 每个驱动（按类名、再按场景层级排序，固定顺序）：
    inside = t ∈ [t0, t1)                       （t0, t1 = LanbaiWindow()，Start() 里读一次）
    inside 变了 → LanbaiActivate(inside)        （进 / 出窗口各一次；跳时间、迟到的人也对）
    inside       → LanbaiTick(t)
```
- **预热**：`LanbaiPrewarm()` 之后的 `prewarmFrames`（默认 2）次分发里，所有驱动都 `LanbaiActivate(true)`、不 tick；之后按窗口逻辑关回去。
- **开销**：每个驱动每帧一次比较；窗口里的再加它自己的 `LanbaiTick`。账本里 Udon ≤ 0.4 ms 是全片合计，每个驱动的 `LanbaiTick` 要在 README 里报自己的循环次数（多少个 renderer / MPB 写入）。

## 3. 驱动要遵守的（审查时会查）

1. **驱动所在的物体永远是激活的**。`LanbaiActivate` 开关的是**另一个**根物体（`public GameObject root;`）。驱动把自己所在的物体关掉的话，Udon 不再跑它的 `Update`，之后能不能再收到调用取决于 VRChat 的实现，不要赌（Wire Scene 会提示挂在未激活物体上的驱动）。
2. 窗口的开始和结束都要落在**遮挡**里（黑、白、入云、水下）：激活 / 关闭根物体的那一帧不能被看见（圣经 §1.9）。
3. `Start()` 里写好 MaterialPropertyBlock 和全局量（`CONTROL_总控.md` §6 第 9 条）。
4. 只写自己的东西（`Engineering/README_集成.md` §2）：不碰 PPv2、不写 `RenderSettings`（除非这一幕已经由接管开关交给你）、不碰车。两个窗口重叠的驱动不能写同一个全局量——**3 Report** 会列出所有重叠。
5. 每个 U# 脚本要有程序资产（U# 1.x 只编有 `.asset` 的脚本）：各包的搭建脚本自己建。
6. **（v1.1）报出自己写什么**：会在自己的窗口里写 `RenderSettings` 的雾 / 环境色的驱动，加 `public bool LanbaiWritesAtmosphere()`；写那一盏主光的，加 `public bool LanbaiWritesSun()`。已经有 `public bool writeRenderSettings` / `writeMainLight` 字段的驱动（门内、海）不用加，生成器直接读字段。分发层在 `Start()` 读一次（之后在 Inspector 里改开关要重进 Play）。**3 Report** 会在每个驱动后面标 `[atmosphere]` / `[sun]`，两个都写同一样的驱动窗口重叠时报 `ERROR`。
7. **（v1.1）不接管任何占位组的驱动**（比如摆诗的 `LanbaiPoemDriver`，窗口是全片）：加 `public bool LanbaiTakesOverNothing()` 返回 true。分发层照样调它，但它的窗口**不进** `windowsFlat` / `LanbaiCovered(t)`——不然 `LanbaiCovered(t)` 处处为真，`LB_Journey` 会在第 6、7b、8、10、11 幕还是占位的时候把占位组全关掉（D-33 评审 #2）。
   - 现在 main 上：门内、海按字段报（默认关，本地勾上才算）；门、第 9 幕不写；**天空的 `LanbaiSkyDriver` 还没有 `LanbaiWritesAtmosphere()`**——它的 `LanbaiSkyPreset.ownsAtmosphere` 打开时才写 RenderSettings，请天空下次醒来加一行（返回任一预设的 `ownsAtmosphere`），在那之前它被当成“不写”。

8. **（v1.2）拿着遮罩球的驱动要让出生淡入**：迟到的人在驱动占着遮罩球的时候进来（比如第 10 幕 1146–1186 的白），驱动每帧写遮罩球，会和 `LB_Journey` 的出生淡入抢同一个通道，淡入一结束画面一帧从黑跳到白（+7.5 EV）。所以：有 `LanbaiOverlay` 字段的驱动加
   ```csharp
   public void LanbaiSpawnFade(float since)   // 分发层每帧在 LanbaiTick 之前调（窗口里）
   ```
   `since < 0`：出生的黑 / 淡入还在走，**这一帧不碰遮罩球**（`Hide()` 也不调）；`since ≥ 0`：= `t − _fadeEndT`，`_fadeEndT` 是 `LanbaiSpawnFadeEnd()` 之后第一次 `LanbaiDispatch` 的**时间轴时刻**，锁存一次（不拿 `Time.time` 算，卡顿时 t 和 since 一起走，不会跳过 266.4 一下 `Hide()`）。淡入结束在驱动自己的遮罩窗口里的，从黑起按 **≤ 0.85 EV/s** 升，和自己的曲线取更暗的，跑完再 `Hide()`。
   **遮罩窗口**（v1.3，D-43）：实现了 `LanbaiSpawnFade` 的驱动**必须**实现 `public float[] LanbaiOverlayWindow()`，报“从开始写遮罩球，到还来得及在自己窗口里把一个人从黑升起来的最后一刻”（窗口结束 − 一次完整的爬升）。在这一段里任何时刻交接过来的人，驱动都从黑往上升，升完再 `Hide()`，**过了自己曲线原定的结束时刻也一样**（第 6 幕：252.64 → 351.2，266.4 以后亮着的那一段也算；门内 248.39 → 252.64）。没实现的，生成器**不放进**窗口表，**3 Report 报 ERROR**（不再拿整个窗口去顶）。分发层第一次被问到时建表（懒构建，`LB_Journey` 在自己的 `Start()` 里问也行），`LB_Journey` 用 `LanbaiOverlayHandoverAt` 判断（见 §0 第 3 条）。
   **窗口之外的出生淡入**（v1.3）：`LB_Journey` 自己淡入，EV 线性，T = log2(L / L黑) / 0.85，最长 9 秒；L 是这一刻最亮的非白视向：在窗口里的驱动可选报 `public float LanbaiBrightestL(float t)`（第 6 幕报 0.652，门内 0.2），没人报就按 1（= 9 秒）。站台（出发前）照旧 3 秒。
   **数值核对**：`Director/Tools~/spawn_fade_sim.py`（分发层、`LB_Journey` 的出生、门内、第 6 幕的 Python 移植；第 10 幕的白是按 D-43 写的替身）。进场 238、244、249、255、260、263.5、266、267、270、1140、1150、1180 s 全过，结果在 `Docs~/spawn_fade_sim.md`；负对照（v1.2 的做法）在 263.5 s 一帧 +7.35 EV，复现了 D-43 说的问题。
   `LB_Journey` 没调 `LanbaiSpawnFadeBegin` 时（旧的本地）`since` = 1e6，等于不限制。分发层的 `spawnFadeSince` 在 Inspector 里看得到。**3 Report** 会对“有 `LanbaiOverlay` 字段、没有 `LanbaiSpawnFade`”的驱动报 WARNING。**接口只有这一个**：镜与白的白驱动改用 `LanbaiSpawnFade(float since)`（总导演已通知），生成器不认别的签名。

## 4. 已知的

- 没在 Unity / UdonSharp 里编译过。U# 的“对带类型的数组里的元素调用带参数的方法”是 U# 1.x 支持的写法，但要本地编一次确认；如果报错，退路是驱动加一对 `public float lanbaiT; public void _LanbaiTickEv() { LanbaiTick(lanbaiT); }`，分发层改成 `SetProgramVariable` + `SendCustomEvent`（生成器里改三行）。
- `Docs~/LanbaiActDispatcher_example_generated.cs.txt` 是生成结果的样子（v1.1：main 上的五个驱动——第 7 幕、第 9 幕、门、门内、天空；用和生成器同样的模板生成，和五个驱动的源码一起过了 Roslyn 检查，0 错 0 警告）。

## 5. 以后（Director 这一层还要做的）

- `LanbaiReflectionBaker.cs`（圣经 §8.1 #14）：每幕一张 `_Udon_ReflCube`（256/面、BC6H、含天空与云卡）；第 7 幕的 `ReflCube_Dawn`、`Refl_S7c`、`ReflCube_DuskLower`。海现在自带的临时烘焙在它做好以后替换。
- 离开车厢包围盒的人 0.5 秒遮罩下送回座位（圣经 §1.8，Director 2 Hz 检查）——和本地的 `busMin/busMax` 对一下谁做。**D-31 #3 定了规则**：按 `VRCPlayerApi.GetPosition()`（根）判断，不按头；头探出玻璃 ≤ 0.6 m 不触发；包围盒从「车」的 `BusLayout.json` 读（PAZ 车宽 2.44 m，中线 x = −0.18）。`BusLayout.json` 进 main 以后做。
- auto-lite（圣经 §1.9：第 1 幕静止时测 10 秒帧时，超过 1.25 倍帧间隔就自动启用砍法）。
