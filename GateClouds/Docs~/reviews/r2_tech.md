# GateClouds 技术评审 第 2 轮（只读）

**结论：有条件通过。** 没有确定会编译失败的 BLOCKER；4 条 MAJOR，第 1、2 条要在本地测试之前改。

## MAJOR
1. **保守深度不能保证**（deck `:300`、`:459`，`deck_ref.py:271`）：`tPrev` 从 `t0` 开始，`cPrev` 却在 `ts` 采。眼离云顶 < 56.8 m（U6 前后）时 `t0 = 0`，车道外的浅视线在 `ts` 已在云头里，第一步就判撞，二分 `lo = 0`，`tHit` 可能比代理面近（违反 `SV_DepthLessEqual`），`tHit = 0` 时深度 NaN。另：峡谷唇加在 `min(H, cap)` 之后会超过 cap；`ts` 以前高过半高的近处云头被跳过。修法：`tPrev = ts`；`DeckDepth` 里 `tDepth = max(tDepth, 1.5/max(-V.y,1e-4)·1.001)`（同时兜住远平面 < 15.2 km 时的夹紧）；lip 放到 `min(H, cap)` 之前。
2. **测试场景会把 Build 关掉的东西重新打开**（`FromLocal/gate_test/code/LB_GateTest_Run.cs:123-127`）：`SetPB(..., on = true)` 每次 Apply 重开 `Tear_CloudGlow`、`Tear_CloudGlow_Additive`、`Tear_LightLane`；`LB_GateTest_Build.cs:602-609` 的旧等宽 `Shaft_00/01` Builder 没关。修法：Builder 关 `Shaft_00/01`；README §2 点名测试脚本的这几行。
3. **`CopyProxyToUdon` 的重载按反射顺序挑**（Builder `:339-355`、`:415`）：选中带 `ProxySerializationPolicy` 的重载会以 null 抛 NRE，Build 停一半。修法：`CallStatic` 优先参数个数完全相同的重载。
4. **正式世界里没人写云海依赖的全局量**（`_Udon_CloudTop / GateOrigin / TearFoot` 只有编辑器测试脚本写）：把门的总驱动 `LanbaiGateDriver` 列为上线前置条件。

## MINOR
5. 深度 pass 48 步、主 pass 上限 128；未撞回退下限一个用 `tPrev` 一个用 `tEnd`。
6. 违反 CONTROL §4：三个 shader 自己声明 `_Udon_*`，应 include `LanbaiGlobals.cginc`。
7. U# 驱动手动调 `Start()`：改名 `_Init()`，`Start` 调它。
8. `GameObject.Find("GateClouds_Driver")` 只找激活物体：改 `FindInScene`。
9. 取 MonoScript 先 AddComponent 再 Destroy：改 `AssetDatabase.FindAssets("LanbaiGateClouds t:MonoScript")`。
10. `multi_compile_shadowcaster` 不需要（多一个 `SHADOWS_CUBE` 变体）。

## 核过没问题
CGINCLUDE 宏顺序与 `SV_DepthLessEqual` 方向；ShadowCaster 在 Cast Shadows Off 时仍进 `_CameraDepthTexture`（需常开带阴影平行光，Frame Debugger 确认）；光束整条收拢；JsonUtility 字段；与 Python 参照一致（除 `tex2Dgrad` 与第 1 条）；Tear / Tide include；`[Header]`；CONTROL §6 坑没重犯。

## 处理（第 4 轮）
见 README §10 与 `Docs~/iterations/README.md` 第 09 条。
