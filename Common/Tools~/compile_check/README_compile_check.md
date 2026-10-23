# 全仓共用的编译检查（`Common/Tools~/compile_check/`）

维护：总工程师（起头是总导演的工作流，额度用完时停在一半，总工程师接手补完）。**它不是 Unity 编译**：能证明的比 slang 多很多，但“没在 Unity 里编译过”这句话照样要写进每个包的 README。

```bash
bash Common/Tools~/compile_check/setup.sh                       # 一次（幂等）：东西都放 ~/.cache/lanbai_check，不进仓库
python3 Common/Tools~/compile_check/check_shaders.py <文件夹或文件> ...   # shader（需要 python3 能 import 到 pcpp；用 ~/bpy/bin/python 最省事）
bash Common/Tools~/compile_check/check_cs.sh <文件夹> ...                 # C#
```

退出码：有 ERROR = 1。每个包交之前跑一遍，把输出的最后一行写进 README 的“检查”一节。

## shader：`check_shaders.py`

| 查什么 | 怎么查 | 抓得到的（举例） |
|---|---|---|
| ShaderLab | 自己的解析（`lib/shaderlab.py`） | `[Header(...)]` 里的冒号（Unity 整个 shader 导入失败）、括号逗号（标题画不出来）；`[KeywordEnum]` / `[Toggle]` 的关键字没有 `#pragma` 声明；`ZTest Always`（只有遮罩球可以） |
| HLSL | **DXC**（微软的 HLSL 编译器，`lib/dxc.py`）+ **Unity 2022.3.22f1 自带的 CGIncludes 原件**（setup 从 Unity 官方的 built-in shader 源码拉的，不是桩）。每个程序块、每个关键字变体（太多时取“全关、每个单开、全开”）、顶点和片元各编一次，`#line` 指回原文件原行 | **门测试里本地真撞上的两个错误都能复现**：`_CloudTopY` 先用后声明（`undeclared identifier '_CloudTopY'`）、`[Header(Flap: indigo silk)]` 的冒号。slang 两个都没抓到 |
| 表面着色器 | Unity 会生成代码，这里不重现生成器：按生成器的顺序先 include UnityCG / Lighting / UnityPBSLighting / AutoLight，补上 `INTERNAL_DATA`、`WorldNormalVector` 这些生成器给的宏，用一个假入口编译——HLSL 的语义检查覆盖所有函数体，所以每个函数都被类型检查。按 pass 编三遍：ForwardBase、ForwardAdd（除非 `noforwardadd`）、ShadowCaster（有 `addshadow` 时） | 表面着色器里的声明顺序、类型错误、ForwardAdd 里才出现的错误 |
| 蓝白的规矩（编译器管不到的） | 文本规则 | **SPS-I**：顶点 / 片元程序缺 `UNITY_VERTEX_INPUT_INSTANCE_ID` / `UNITY_VERTEX_OUTPUT_STEREO` / `UNITY_SETUP_INSTANCE_ID` / `UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO`；片元读了每只眼不同的量（`_WorldSpaceCameraPos`、`UNITY_MATRIX_V/P/VP`、深度图、`LanbaiCentreEyePos`……）却没在第一行写 `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX`。**雾**：调了 `LanbaiApplyFog` 却没有 `#pragma multi_compile_fog`（雾会整个编译没了）；和 `UNITY_APPLY_FOG` 同时用。**`_Udon_` 名字**没登记。**include 路径**：Common 的文件要写 `Assets/Lanbai/Common/Shaders/...` |
| 单独的 `.cginc` | 没被本次检查的 `.shader` 用到的，单独编一次 | 文件内部先用后声明、重复定义 |

**抓不到的**：FXC（Unity 在 d3d11 上真正用的编译器）独有的诊断——常量折叠出来的除零（X4008，门测试里 TentacleSway 的 ForwardAdd POINT 变体那个）、部分“循环里用梯度指令”（X3570）；DXC 在个别地方比 FXC 严。表面着色器生成器自己产生的代码。好不好看。

## C#：`check_cs.sh`（`lib/cs_check.py`）

按 Unity 的程序集划分（asmdef、Editor 文件夹）用 Roslyn 编两遍：
- **editor**：UnityEngine / UnityEditor 2021.1.14.1（nuget 上最新的 UnityEditor 引用程序集）+ UdonSharp / VRChat SDK / PPv2 / TMP 的桩，定义 `UNITY_EDITOR`。
- **player**：只有运行时程序集、**没有 UnityEditor**（抓“编辑器 API 漏进了运行时代码”），对 **UnityEngine 2022.3.62 的模块 + 真的 PPv2 / TMP 运行时 DLL**。
- 外加两条 lint：`VRCShader.PropertyToID("_Udon_...")` 的名字对照登记表；UdonSharp 1.x 不支持的写法（try/throw、interface、struct、泛型集合、LINQ、yield、async）。

**抓不到的**：UdonSharp 编译器本身的限制（只有 U# 编译器知道哪些 API 在 Udon 白名单里——桩只覆盖了常用的那几个；一个方法在桩里有，不代表 Udon 暴露了它）、程序资产（U# 1.x 只编有 `.asset` 的脚本，`CONTROL_总控.md` §6 第 11 条）。

## 文件

| 文件 | 是什么 |
|---|---|
| `setup.sh`、`lib/setup_fetch.py` | 拉 Roslyn、引用程序集、Unity 2022.3 运行时、CGIncludes、DXC、pcpp / slangpy，记进 `~/.cache/lanbai_check/env.json` |
| `check_shaders.py`、`lib/hlsl_tu.py`、`lib/shaderlab.py`、`lib/dxc.py` | shader 检查 |
| `check_cs.sh`、`lib/cs_check.py`、`stubs/*.cs` | C# 检查 |

各包以前自己带的检查（`Grading/Tools~/compile_check/`、`Rain/Tools~/compile_check/`、`Sky/Tools~/compile_check/`……）可以继续留着做自己的特殊测试（比如天空的门光带等价核对），但**交付时以这一份的结果为准**。

## 已知的缺口（下一步）

- `stubs/unity_stub.hlsl` 还没有：setup 拉不到 CGIncludes 时没有退路（现在 setup 一定会拉，所以先不补）。
- 没有 slang 的第二遍（DXC 已经覆盖 slang 能查的全部，而且更严）。
- 想加：一个 shader 里 `_Udon_` 全局量的**类型**和登记表 / 别的 shader 不一致（float 对 float4）——现在由 `Engineering/ledgers/globals_scan.py` 在全仓层面查。
