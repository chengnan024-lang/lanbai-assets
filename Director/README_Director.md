# Director · 分发层 v1.3 r2（`Director/`）

维护：总工程师。**没在 Unity 里编译过**：C# 用 `Common/Tools~/compile_check/check_cs.sh` 做了 Roslyn 类型检查（editor + player 两遍、U# 规则），生成器跑过一次真生成（对门的 `LanbaiGateClouds` + 一个假的海驱动），生成结果和门的驱动一起编译通过、重复生成不变（幂等）。

## 0. 本地要做的（拷哪些、点哪个、改哪两行）

1. 拷 `Director/` → `Assets/Lanbai/Director/`（`Docs~` 不进 Unity）。
2. 拷完所有包的驱动以后：菜单 **蓝白/Director/1 Generate Dispatcher** → 等 Unity 重新编译 → **蓝白/Director/2 Wire Scene**（场景里建 `Lanbai/Director`、挂分发层、建它的 U# 程序资产、把场景里每个驱动填进去）→ **蓝白/Director/3 Report**（打印每个驱动的时间窗和重叠）。加了新包就重新点 1、2。
3. `LB_Journey` 改两行（**这是对 `LB_Journey` 的全部改动**，加上 `Engineering/README_集成.md` §3 的接管开关）：
   ```csharp
   public LanbaiActDispatcher dispatcher;            // Inspector 里拖 Lanbai/Director
   // Update() 末尾、算完 t 之后、ApplyGrades() 之前（ApplyGrades 要读分发层的 grade* 结果）：
   if (dispatcher != null) dispatcher.LanbaiDispatch(t);
   // ApplyGrades() 之后：SpawnTick(t, 这一帧的总 dEV, 还没出发)（第 4 条）
   // 出生的 3 秒黑场里调一次（圣经 §1.9：所有根物体在相机前激活 2 帧预热 shader）：
   if (dispatcher != null) dispatcher.LanbaiPrewarm();
   // v1.3 r2（D-43、D-43 #7）：出生的状态机，完整的写法见下面第 4 条
   ```
4. **出生的状态机（v1.3 r2，D-43 #7；照抄进 `LB_Journey`，字段名可以改）**。迟到的人只看到**一次**变亮：从黑开始，看到的亮度 EV 线性、≤ 0.85 EV/s。两条路：淡入期间有驱动的遮罩窗口，就**保持黑**、到点交给驱动从黑升；没有，就自己淡入，**限的是看到的亮度**（场景 × 2^dEV，驱动自己的曝光爬升也算进去），一直追到场景为止，不按固定时长。
   ```csharp
   // ---- 字段 ----
   const int SP_NONE = 0, SP_BLACK = 1, SP_HOLD = 2, SP_FADE = 3, SP_PLATFORM = 4;
   int _sp = SP_NONE;
   float _spBlackEnd, _spHandAt, _spFade0;       // _spBlackEnd / _spFade0 是 Time.time（真实秒），_spHandAt 是时间轴秒
   bool _spawnFadeEnded;                         // 测试工具 1.2.x 的 Play 阶段默认等它为 true（clock.ready_vars），不要删
   public float spawnBlack = 3f;                 // 圣经 §1.9
   public float spawnLBlack = 0.0013f;           // 出生黑的亮度（#030409）
   public Color spawnFill = Color.black;         // 出生遮罩的填色（S1 行，本地定）

   // ---- 出生那一帧（Start 里、或玩家进来那一刻），t = 时间轴秒 ----
   void SpawnBegin(float t)
   {
       if (dispatcher != null) { dispatcher.LanbaiPrewarm(); dispatcher.LanbaiSpawnFadeBegin(); }
       _sp = SP_BLACK; _spBlackEnd = Time.time + spawnBlack; _spawnFadeEnded = false;
       // 经过多久一律用 Time.time：站台上时间轴停在 0，用 t 算黑会永远不结束（阿白 10-25 指出）；t 只用来查窗口
   }

   // ---- 每帧，在 dispatcher.LanbaiDispatch(t) 和 ApplyGrades() 之后调；dEV = ApplyGrades 这一帧实际用的总 dEV ----
   //      （LB_Journey 自己的事件 + dispatcher.gradeDEV），遮罩的填色要按它补偿（SetFlat 的第 3 个参数）
   void SpawnTick(float t, float dEV, bool beforeDeparture)
   {
       if (_sp == SP_NONE || overlay == null) return;
       if (_sp == SP_BLACK)
       {
           overlay.SetFlat(spawnFill, 1f, dEV);
           if (Time.time < _spBlackEnd) return;
           if (beforeDeparture || dispatcher == null) { _sp = SP_PLATFORM; _spFade0 = Time.time; }   // 站台：照旧 3 秒
           else
           {
               float T = dispatcher.LanbaiSpawnFadeLength(t, spawnLBlack);                // 往前看了驱动的曝光爬升；没有爬升时 ≤ 9.4 秒
               _spHandAt = dispatcher.LanbaiOverlayHandoverAt(t, t + T + 0.5f);          // 分发层记下“交没交”
               if (_spHandAt >= 0f) _sp = SP_HOLD; else { _sp = SP_FADE; _spFade0 = Time.time; }
           }
       }
       if (_sp == SP_HOLD)
       {
           overlay.SetFlat(spawnFill, 1f, dEV);                                         // 保持黑
           if (t >= _spHandAt && dispatcher.LanbaiCoversOverlay(t)) { dispatcher.LanbaiSpawnFadeEnd(); _sp = SP_NONE; _spawnFadeEnded = true; return; }   // 交给驱动，不 Hide
           if (t > _spHandAt + 1f) { dispatcher.LanbaiSpawnFadeOwn(); _sp = SP_FADE; _spFade0 = Time.time; }   // 窗口没了（时间轴被拖走）：自己淡入
           else return;
       }
       if (_sp == SP_FADE)
       {
           float seen = dispatcher.LanbaiSpawnSeenL(t, dEV);                           // 最亮的非白视向，看到的亮度（≤ 1 × 2^dEV）
           float ramp = 0.004f * Mathf.Pow(2f, 0.85f * (Time.time - _spFade0));        // 从地板 0.004 起（再暗的看不出来）、EV 线性、0.85 EV/s
           if (ramp >= seen) { overlay.Hide(); dispatcher.LanbaiSpawnFadeEnd(); _sp = SP_NONE; _spawnFadeEnded = true; return; }
           // 看到的 = (1 − a)·seen + a·L黑 = ramp：a = (seen − ramp) / (seen − L黑)（遮罩画在 PPv2 之前，填色按 dEV 补偿）
           overlay.ClearLobes();
           overlay.SetFlat(spawnFill, Mathf.Clamp01((seen - ramp) / Mathf.Max(seen - spawnLBlack, 1e-5f)), dEV);
           return;
       }
       if (_sp == SP_PLATFORM)
       {
           float tau = Time.time - _spFade0;
           overlay.ClearLobes();
           overlay.SetCurve(spawnFill, dEV, tau, 3f, spawnLBlack, lPlatform, lPlatform, spawnLBlack);   // lPlatform = 站台最亮的视向
           if (tau >= 3f) { overlay.Hide(); if (dispatcher != null) dispatcher.LanbaiSpawnFadeEnd(); _sp = SP_NONE; _spawnFadeEnded = true; }
       }
   }
   ```
   - **经过多久用 `Time.time`，查窗口用 t**（10-25 改，阿白在本地补丁里先指出）：站台上时间轴固定为 0，原来 `_spBlackEnd = t + 3` 会让站台上出生的人一直黑着。旅程里 t 和真实时间同速，两种写法结果一样（`spawn_fade_sim` 的结论不变）；调试拖时间轴时，黑和淡入照真实时间走完。
   - `dEV` 要传这一帧**实际**用的总 dEV（`LanbaiExposure.SetDeltaEV` 的返回值或 `GetAppliedDeltaEV()`），不是请求值：EXPO 被夹住时两者不一样，遮罩的补偿会错。
   - `LanbaiSpawnFadeLength` 往前看：每 0.25 s 用驱动的 `LanbaiGrade(t')`（`LanbaiGradeDEVAt`）算那时看到的亮度，算出这条 0.85 EV/s 的线要多久追上。所以“淡入期间有没有窗口”问的是真的淡入时长：第 10 幕白前的 `EXPO_UP` 会把淡入拉长到碰上白的遮罩窗口，这时就改成保持黑、交给白驱动（不然淡入一结束，白驱动照自己的时间表画遮罩，一帧 +0.56 EV，`spawn_fade_sim` 的 1130 s）。
   - 为什么 FADE 不用固定的 T：驱动的曝光爬升（比如第 10 幕白之前的 `EXPO_UP`、第 8 幕出海的放开）会在淡入期间把场景再抬几 EV；按固定 T 淡完一 `Hide()`，看到的亮度一帧跳上去。追着“看到的亮度”走，就永远 ≤ 0.85 EV/s。T 只用来问“淡入期间有没有窗口”。
   - `LanbaiSpawnFadeEnd` 只认第一次；Begin 之后 25 秒没有 End 当作已结束（`spawnFadeTimeout`）。时间轴拖回锁存时刻之前，分发层忘掉这次出生（`since` = 1e6）。
   - 自己淡完（或 `LanbaiSpawnFadeOwn` 以后）结束的，分发层给驱动的 `since` = 1e6：驱动当它是一直在场的人，不会再从黑升一遍。
5. **接管开关（v1.1，2026-10-24）**：分发层按“这个驱动写什么”分开给窗口——
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

8. **拿着遮罩球的驱动要让出生淡入（v1.2；v1.3 r2 照 D-43 #7 改写，和这一条有出入的以裁决为准）**：迟到的人在驱动占着遮罩球的时候进来（第 6 幕的晨、第 10 幕的白），驱动每帧写遮罩球，会和 `LB_Journey` 的出生淡入抢同一个通道。所以有 `LanbaiOverlay` 字段的驱动加两个方法：
   ```csharp
   public void    LanbaiSpawnFade(float since)   // 分发层每帧在 LanbaiTick 之前调（窗口里）
   public float[] LanbaiOverlayWindow()          // {t0, t1}，Start 里读一次
   ```
   - `since < 0`：出生的黑 / 淡入还在走，**这一帧不碰遮罩球**（`Hide()` 也不调）。
   - `since ≥ 0`：= `t − _fadeEndT`（`_fadeEndT` 是 `LanbaiSpawnFadeEnd()` 之后第一次 `LanbaiDispatch` 的**时间轴时刻**，锁存一次），这个人是**交给我的**：从交接那一刻起，从黑按 ≤ 0.85 EV/s 升到场景，曲线**按这一段最亮的非白视向建**（不按平均亮度），和自己的曲线取更暗的，升完再 `Hide()`。
   - `since` = 1e6：没有交给我（一直在场的人、自己淡完的人、旧的本地）：照自己的时间表。
   - **`LanbaiOverlayWindow` 报到哪一刻（D-43 #7）**：从开始写遮罩球，只报到**交接过来的人还能在我自己控制的那一段里被完整升起来**的最后一刻 = 控制段的结束 − 一次完整爬升 − 一点余量。窗口之后交给 `LB_Journey` 自己淡入。现在三个：
     - 第 6 幕：252.64 → 351.2（控制段到 363.62，爬升 8.65 s + 最晚方向的提前 3.3 s，余量 0.5 s）；
     - 门内：248.39 → 252.64（这一段画面本身就是黑，交过来的人要升到的就是黑，到 252.64 由第 6 幕的预滚从黑接着升）；
     - 第 10 幕的白（镜与白，`pkg/mirrors`）：1144.11 → 1188.96。它的控制段到 1188.96，在白里交接过来的人升到白要 9.7 s，所以窗口晚段交接过来的人它不升到白，而是保持黑、白收完以后从黑升到第 11 幕（约 2 s，在 1188.96 之前完成）。这是同一条规矩的另一种做法：交接过来的人都在它自己的控制段里升完。
   - 实现了 `LanbaiSpawnFade` 没实现 `LanbaiOverlayWindow` 的：生成器**不放进**窗口表，**3 Report 报 ERROR**。分发层第一次被问到时建表（懒构建）。
   - **窗口之外**：`LB_Journey` 自己淡入（§0 第 4 条的状态机），限看到的亮度 = 场景 × 2^dEV。场景亮度 = 窗口里的驱动可选报的 `public float LanbaiBrightestL(float t)`（第 6 幕 0.652、门内 0.2），没人报按 1；一律限 ≤ 1。
   - **数值核对**：`Director/Tools~/spawn_fade_sim.py`（v1.3 r2）。Python 移植的是真代码：分发层、§0 第 4 条的状态机、门内、第 6 幕，和镜与白 `pkg/mirrors` 962567b 的**真白驱动**（含 `LanbaiGrade`）；看到的亮度 = (1 − a)·场景·2^ΣdEV + a·填色。判据：圣经 §1.8 的三个窗口，加“任何 1 / 2 / 4 s 窗口 ≤ 0.85 EV/s”，从出生量到和一直在场的人一样为止。结果在 `Docs~/spawn_fade_sim.md`：
     - D-43 的进场时刻 + 1125.75 / 1130 / 1134.25（复核 DIR13-4）、两条 0.5 s 卡顿、一条“拖回锁存时刻之前”（DIR13-2）全过；
     - 175–372 s 每 0.1 s 一个进场（1971 个）全过；
     - 1120–1200 s 每 0.1 s（801 个）：**用镜与白现在的白驱动有 24 个不过**（1183.6–1185.9 进场，最坏一帧 +1.53 EV：它从黑升到第 11 幕的那条线从“白收完”算起、不从交接算起，窗口也报到了升不完的地方），**照 `Engineering/D43r2_patches/pkg-mirrors_LanbaiWhiteDriver.patch` 改了以后 801 个全过**；
     - 负对照全部复现：v1.2 的做法 +7.35 EV；拖回不忘掉出生 +7.35 EV；r1 的固定时长淡入 1130 s 1 s 升 1.46 EV；FLASH_TEAR 不压 +0.57 EV；r1 整套 + 淡入结束在闪光里 +0.47 EV。
   - `LB_Journey` 没调 `LanbaiSpawnFadeBegin` 时（旧的本地）`since` = 1e6，等于不限制。分发层的 `spawnFadeSince` 在 Inspector 里看得到。**3 Report** 对“有 `LanbaiOverlay` 字段、没有 `LanbaiSpawnFade`”的驱动报 WARNING。

## 4. 已知的

- 没在 Unity / UdonSharp 里编译过。U# 的“对带类型的数组里的元素调用带参数的方法”是 U# 1.x 支持的写法，但要本地编一次确认；如果报错，退路是驱动加一对 `public float lanbaiT; public void _LanbaiTickEv() { LanbaiTick(lanbaiT); }`，分发层改成 `SetProgramVariable` + `SendCustomEvent`（生成器里改三行）。
- `Docs~/LanbaiActDispatcher_example_generated.cs.txt` 是生成结果的样子（v1.1：main 上的五个驱动——第 7 幕、第 9 幕、门、门内、天空；用和生成器同样的模板生成，和五个驱动的源码一起过了 Roslyn 检查，0 错 0 警告）。

## 5. 以后（Director 这一层还要做的）

- `LanbaiReflectionBaker.cs`（圣经 §8.1 #14）：每幕一张 `_Udon_ReflCube`（256/面、BC6H、含天空与云卡）；第 7 幕的 `ReflCube_Dawn`、`Refl_S7c`、`ReflCube_DuskLower`。海现在自带的临时烘焙在它做好以后替换。
- 离开车厢包围盒的人 0.5 秒遮罩下送回座位（圣经 §1.8，Director 2 Hz 检查）——和本地的 `busMin/busMax` 对一下谁做。**D-31 #3 定了规则**：按 `VRCPlayerApi.GetPosition()`（根）判断，不按头；头探出玻璃 ≤ 0.6 m 不触发；包围盒从「车」的 `BusLayout.json` 读（PAZ 车宽 2.44 m，中线 x = −0.18）。`BusLayout.json` 进 main 以后做。
- auto-lite（圣经 §1.9：第 1 幕静止时测 10 秒帧时，超过 1.25 倍帧间隔就自动启用砍法）。
