# Director · 分发层 v1（`Director/`）

维护：总工程师。**没在 Unity 里编译过**：C# 用 `Common/Tools~/compile_check/check_cs.sh` 做了 Roslyn 类型检查（editor + player 两遍、U# 规则），生成器跑过一次真生成（对门的 `LanbaiGateClouds` + 一个假的海驱动），生成结果和门的驱动一起编译通过、重复生成不变（幂等）。

## 0. 本地要做的（拷哪些、点哪个、改哪两行）

1. 拷 `Director/` → `Assets/Lanbai/Director/`（`Docs~` 不进 Unity）。
2. 拷完所有包的驱动以后：菜单 **蓝白/Director/1 Generate Dispatcher** → 等 Unity 重新编译 → **蓝白/Director/2 Wire Scene**（场景里建 `Lanbai/Director`、挂分发层、建它的 U# 程序资产、把场景里每个驱动填进去）→ **蓝白/Director/3 Report**（打印每个驱动的时间窗和重叠）。加了新包就重新点 1、2。
3. `LB_Journey` 改两行（**这是对 `LB_Journey` 的全部改动**，加上 `Engineering/README_集成.md` §3 的接管开关）：
   ```csharp
   public LanbaiActDispatcher dispatcher;            // Inspector 里拖 Lanbai/Director
   // Update() 末尾、算完 t 和 ApplyGrades 之后：
   if (dispatcher != null) dispatcher.LanbaiDispatch(t);
   // 出生的 3 秒黑场里调一次（圣经 §1.9：所有根物体在相机前激活 2 帧预热 shader）：
   if (dispatcher != null) dispatcher.LanbaiPrewarm();
   ```
   接管开关要的“哪些时间段有驱动接管”：`dispatcher.windowsFlat`（t0, t1 成对）或 `dispatcher.LanbaiCovered(t)`。

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

## 4. 已知的

- 没在 Unity / UdonSharp 里编译过。U# 的“对带类型的数组里的元素调用带参数的方法”是 U# 1.x 支持的写法，但要本地编一次确认；如果报错，退路是驱动加一对 `public float lanbaiT; public void _LanbaiTickEv() { LanbaiTick(lanbaiT); }`，分发层改成 `SetProgramVariable` + `SendCustomEvent`（生成器里改三行）。
- `Docs~/LanbaiActDispatcher_example_generated.cs.txt` 是生成结果的样子（门 + 一个假的海驱动）。

## 5. 以后（Director 这一层还要做的）

- `LanbaiReflectionBaker.cs`（圣经 §8.1 #14）：每幕一张 `_Udon_ReflCube`（256/面、BC6H、含天空与云卡）；第 7 幕的 `ReflCube_Dawn`、`Refl_S7c`、`ReflCube_DuskLower`。海现在自带的临时烘焙在它做好以后替换。
- 离开车厢包围盒的人 0.5 秒遮罩下送回座位（圣经 §1.8，Director 2 Hz 检查）——和本地的 `busMin/busMax` 对一下谁做。
- auto-lite（圣经 §1.9：第 1 幕静止时测 10 秒帧时，超过 1.25 倍帧间隔就自动启用砍法）。
