# `LanbaiGlobals.cginc`：所有 `_Udon_` 全局量只在这里声明

维护：总工程师（总导演 10-23 批准）。**生成的，不要手改**：`python3 Common/Tools~/globals/gen_globals.py --out Common/Shaders/LanbaiGlobals.cginc`。

- **为什么**：HLSL 里同一个全局量声明两次是编译错误（FXC X3003）。以前门的 `LanbaiGateSky.cginc`、天空的 `LanbaiSky.cginc`、远潮、海……各自声明同一批名字，include 的先后一换就编译失败。现在每个名字在这里声明一次、自己一个 `#ifndef LANBAI_DECL_<名字>` 保护，include 多少次、和谁一起 include 都没事。
- **规矩**：包里的 shader / cginc **不再自己写 `_Udon_` 声明**，一律 `#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"`。检查工具（`Common/Tools~/compile_check/check_shaders.py`）对“自己声明 `_Udon_`”给警告。
- **加新全局量**：照旧写进你的 `给总控.md` → 总导演批了登记进 `Common/UdonGlobals.md` → 总工程师重新生成这个文件（类型从已经存在的 shader 声明里取；还没有 shader 声明的，按登记表 / 包的接口文档，取不到的标“type guessed”）。
- **类型待确认的**（文件里标了 `type guessed`，请登记表写清类型）：`_Udon_CabinAmbient`、`_Udon_CabinBleach`、`_Udon_CabinFade`、`_Udon_CabinSliceColor`（车厢：总导演）、`_Udon_CausticsTex`（海）、`_Udon_InsideClock` / `Dot` / `Fibre` / `Fog` / `Portal`（门内）、`_Udon_RadioDial`。

## 门的 `LanbaiGateSky.cginc` 怎么换（给「私密对话」的最小改动）

把第 32–38 行这 7 行声明：
```hlsl
float4 _Udon_TearPos;  float4 _Udon_TearH;  float4 _Udon_MoonDir;  float4 _Udon_MoonDisc;
float4 _Udon_FogBandDir;  float4 _Udon_FogBandColor;  float  _Udon_FogBandWidth;
```
换成一行：
```hlsl
#include "Assets/Lanbai/Common/Shaders/LanbaiGlobals.cginc"
```
类型都没变（生成器就是从你的声明里取的类型）。注释可以留在 `LanbaiGlobals.cginc` 的生成说明里，或者在你这里保留成纯注释。`Lanbai_TentacleSway.shader`、`Lanbai_TentacleTide_v2.shader`、`Tear/Lanbai_Tear.shader` 里如果还有自己声明的 `_Udon_*`，同样删掉、改 include。之后 `LanbaiFog` 的钩子在任何 include 顺序下都能编译。

## 天空的 `LanbaiSky.cginc` / `LanbaiFog.cginc`

把 `#ifndef LANBAI_GATE_SKY_INCLUDED ... #endif` 那一块和其余的 `_Udon_` 声明换成同一行 include（`_Udon_FogDensity` 如果按第 1 轮意见改成了 float4，先改登记表再重新生成）。
