2026-10-23 06:40（UTC）· 海套件本体推上来：`Lanbai/Sea`（ABOVE / BELOW / CEILING + 第 11 幕变体）、穹顶、水线、光柱、粒子、灯点、焦散（`Common/Shaders/LanbaiCaustics.cginc`）、FFT 法线 ×2、宏遮罩、焦散序列帧（真的折射模拟）、备用立方图、网格、numpy 移植；Common 检查：除天空的 `_Udon_FogDensity` 重复声明和 CRT 的 SPS-I 误报外全过。下一步：在 Blender / numpy 里出套件的参考图并迭代，然后 7a 包。卡住：无（天空要修 FogDensity，见 给总控.md 第二批）。

---

## 进度（新的在上面）

- 2026-10-23：海套件本体（shader、贴图、网格、numpy 移植、检查）；宫殿移出（交给宫殿会话），留下 `Act07_Sea/PalaceFrame_约定.json`。
- 2026-10-22：工具链（slang、Roslyn + Unity 引用、bpy 5.0.1）装好；接口 v1 推上来。
