# Grading kit · adversarial verification

**Verdict: FAILED.** One blocker and one major issue remain. The kit's code is sound. The grade it builds is not: in real PPv2 it will not render the bible's screen targets.

> **中文摘要：** 套件的代码经得起查：拿**真实的 PPv2 源码**（不是桩）编译，0 警告；数据与 json、圣经附录 B 逐值一致；生成器可以逐字节复现。
> 问题出在上游：美术侧的 PPv2 模拟器把 **Neutral** 色调映射的调色，按 **ACES** 分支的工作空间来算（ACEScc 对比，ACEScg 白平衡、LGG、饱和）。PPv2 3.x 源码里，Neutral 走的是另一条路：先在 **LogC** 里做对比，再在**线性 Rec.709** 里做白平衡、LGG 和饱和。
> 结果是，按 `grades_final.json` 建出来的 15 个 profile 放进 Unity：
> - 测试卡有 **14/15 个 profile 超出 ±3 码**，最多差 13 码；
> - **夜间黑点从 #02060C 蓝黑塌到 #000000–#000002**，红通道被压到 0，违反圣经 §1.3.5；
> - §B 里有 23/61 个不 bloom 的目标偏差超过 3 码，例如深渊 #02070F → #000002，星海点燃前的黑 #04060E → #000000。
>
> 套件自带的 “§C 0 码” 核对用的是同一个模拟器，是循环论证，所以没抓到。
> 需要美术侧修模拟器、重解参数，再重跑生成器。在那之前，Route C 的 `HDRext33.cube` 能在 1 码以内复现 §C，可以当过渡方案。
>
> **修起来不大（复核时补做的可行性试算，见 B1 末尾）：** 其余参数全部不动，只把 14 个 profile 的 **lift 轨迹球**在真实 Neutral 通路里重解（夜间大约从 `(0.9875, 0.9905, 1, 0.008)` 变成 `(≈0.977–0.985, ≈0.989, 1, ≈0.019–0.024)`），黑点就回到 `#02060C` / `#01060D` 的蓝黑，测试卡 14 个 profile 全部回到 **≤ 3 码**；§B 超差从 23 项降到 12 项，剩下的是高饱和的填值（尾灯红、靛蓝雾），要用修好的模拟器重算 §B 填值。这些数只是指路，**不能直接抄进 json**。

Scope: bible §0–§1 (read fully), §1.4, §1.5, §1.7, §1.8 and appendix B; `WORLD.md`; every file in the kit; `art/grades_final.json`; `art/calib_final.{md,json}`. The PPv2 source is the v2 branch = com.unity.postprocessing 3.0.2, fetched from GitHub. The Neutral branch of the shaders was also checked against Graphics/master = 3.6.0.

---

## 1. What was checked, and how

| # | Check | Method (independent of the builder's tools) | Result |
|---|---|---|---|
| 1 | Compile against the **real** PPv2 API, not the builder's `PPv2Stub.cs` | Fetched all 56 PPv2 3.0.2 `Runtime/*.cs` and compiled them against the Unity 2021.1 reference DLLs. Then compiled the kit against that DLL with `-warnaserror`, in 4 builds: the Editor asmdef layout, U# normal, U# `LANBAI_PPV_ANIMATOR_FALLBACK`, and all-in-one. Script: `Tools~/verify_indep/compile_real_ppv2.sh` | **PASS**, 0 warnings |
| 2 | The shipped C# really is generated | Re-ran `gen_grade_data.py` in a copy of the kit and compared the output with `cmp` | `LanbaiGradeData.cs`, the `LanbaiExposure.cs` region and the README table are **byte-identical** |
| 3 | Generator rejects unknown input | Injected an unknown key into a profile | Raises `ValueError` ✓ |
| 4 | Data parity | Own parser and own expectations (`Tools~/verify_indep/parity_indep.py`): 388 field comparisons against the json, calib §C = md table = json ramp, all 15 B1 rows parsed from the bible markdown, the B2 rows, the 9 B3 weights, T0 recomputed with `GammaToLinearSpaceExact`, and the U# generated region (order, postExposure, ±4, sha256) | **PASS** |
| 5 | PPv2 semantics the code relies on | Read in the source: `SetAllOverridesTo(state, excludeEnabled)`, `AddSettings` (enabled = true, hide flags), `OverrideSettings` (lerp on overrideState), `UpdateSettings` (skips weight ≤ 0, editor `IsVolumeRenderedByCamera`), `m_SettingsUpdateNeeded = true` at the end of every `Render` (so the hidden measurement camera re-blends each capture), `Init(resources)`, `PostProcessResources` GUID `d82512f9…`, dithering unconditional in the final pass, `colorFilter` passed with `SetVector` (raw), bloom colour `.linear` + `SetColor` | Matches the code ✓. Bloom colour: see m1 |
| 6 | Udon exposure of `PostProcessVolume.weight` | Fetched the official VRChat creator-docs page from GitHub raw (`Docs/docs/worlds/examples/persistence/post-processing-settings.md`): the example U# script "set[s] the weight on the target PostProcessingVolume". The U# docs list "Static user methods" as supported and method overloads as unsupported; the kit has no overloads. | Primary path confirmed. Get and cross-class static calls are still to be confirmed in the Class Exposure Tree, as the README says |
| 7 | Neutral LUT strip | Pixel test | Exact identity, green max in the top PNG row, R fastest, identical to `art/luts` ✓ |
| 8 | **Does PPv2 actually render §C / §B with these parameters?** | Own numpy model of PPv2's Neutral path, written from `Uber.shader` + `Lut3DBaker.compute` + `Colors.hlsl` + `ColorUtilities.cs` (33³ ARGBHalf LUT, trilinear, non-precise LogC). Cross-checked in both directions: switched to the ACES-branch spaces it reproduces the art simulator; S10 matches §C exactly. Script: `Tools~/verify_indep/ppv2_neutral_check.py` | **FAIL**, see B1 |
| 9 | Images | Viewed `Docs~/TestCard_Reference.png`, `Docs~/TestCard_Layout.png` and the new `Docs~/Verify_SC_vs_PPv2_Neutral.png` | Reference sheets render correctly; the claims in them are affected by B1 |
| 10 | Line-by-line read of every C# file and the shader | By hand: namespaces, usings, member names, asmdef, Editor-only placement, Undo, idempotency, U# constraints | Findings m2–m5 only |
| 11 | Second pass (continuation after the usage-limit break, 2026-09-30 14:30 UTC) | Re-fetched `Lut3DBaker.compute`, `Colors.hlsl`, `Uber.shader`, `ColorGrading.cs`, `Bloom.cs`, `Lut2DBaker.shader` from the v2 branch and re-read the Neutral path (`#else` branch of `ColorGrade`, `USE_PRECISE_LOGC 0`, `LUT_SPACE_ENCODE = LinearToLogC`, `RgbToHsv` with `EPSILON`, Rec.709 `Luminance`). Hand-computed S1 at input 0: LogC 0.0640 → contrast ×1.12 → 0.0221 → linear −0.0028; lift adds (0.0010, 0.0016, 0.0035) → (−0.0018, −0.0012, +0.0007) → clamp → `#000002`. Re-ran `compile_real_ppv2.sh` (PASS, 0 warnings), `parity_indep.py` (PASS, 388 values), `ppv2_neutral_check.py` (same numbers as below). Re-read `LanbaiExposure.cs`, `LanbaiGradeBuilder.cs`, `LanbaiGradeTestCard.cs`, the shader and the asmdef in full: no new code finding. Viewed all three PNGs again. New: lift-only feasibility probe `Tools~/verify_indep/lift_resolve_hint.py` | B1 confirmed; the fix is small (see end of B1) |

---

## 2. Findings

### B1 · BLOCKER · The grade does not render the bible's targets in real PPv2 (Neutral path mis-modelled upstream)

**Evidence.**
- `art/lens_cine/ppv2.py:grade_lut` (docstring: "unity->ACES(AP0) -> ACEScc log contrast -> ACEScg …") runs the working spaces of the **ACES-tonemapper** branch for every profile. `bible_work/lutlib_core.py` patches only bloom.
- In PPv2, both `Lut3DBaker.compute` and `Lut2DBaker.shader` (3.0.2 and 3.6.0 alike) use that path only `#if TONEMAPPING_ACES`.
- For Neutral (`#else`), PPv2 does:
  1. contrast **in LogC** around 0.4135884;
  2. `LogCToLinear`;
  3. white balance, colour filter, mixer and `LiftGammaGainHDR` in **linear Rec.709**;
  4. clamp at 0, then saturation with **Rec.709 luma**;
  5. `NeutralTonemap`.

**Effect.** Contrast is applied in LogC before lift, so it pushes the LogC floor (LogC(0) = 0.064) below zero. The small night lift (w 0.008 × 0.2) cannot bring it back.

Output of `python3 Tools~/verify_indep/ppv2_neutral_check.py`:

- **Test card:** 14/15 profiles would FAIL `MeasureAll` (±3). Only S10 passes, so the self-check will pass and point away from the real cause.

  | Profile | Worst patch (codes) |
  |---|---|
  | S7b | 13 |
  | S3, S4 | 11 |
  | S9b | 10 |
  | S9a | 9 |
  | S1 | 8 |
  | S2, S7a, S11, S12 | 7 |

  Mid-tones mostly stay within 1–3 codes; S8 k+2 is off by 4.
- **Night black point (input 0):**

  | | S1 | S3, S4, S7b, S9a, S9b |
  |---|---|---|
  | Bible (§1.3.5, §1.4) | `#02060C` blue-black, "永不压红到 0" | `#02060C` blue-black |
  | PPv2 | `#000002` | `#000000` |

  This breaks pillar §1.3.2 (blue in every shadow) and the OLED rule.
- **§B non-blooming targets:** 23 of 61 are off by more than 3 codes. Worst: S9a "点燃前的黑" `#04060E` → `#000000`; S7b 深渊 `#02070F` → `#000002`; S4 虚空天色 `#070A14` → `#01020A`; S2 天 `#05080F` → `#020307`.
- **§D overlay fills:** the same simulator solved these, so they are suspect too (e.g. the plunge black).
- **Route C still works:** `art/luts/hdr_external/*_HDRext33.cube`, sampled the way PPv2 External mode samples them, reproduces all 15 × 11 §C values within **1 code**. Those LUTs are baked tables of the intended look.
- Visual: `Docs~/Verify_SC_vs_PPv2_Neutral.png`. In each row, top = §C target, bottom = engine prediction. Viewed.

**Fix (owner: art side, then regenerate this kit).**
1. Add a Neutral branch to `ppv2.grade_lut` that matches the source above. `ppv2_neutral_check.py` holds a reference implementation.
2. Re-solve the parameters in `make_grades.py` so the corrected model hits the **targets**; bible law 1 says the targets stand. In practice this means lift/contrast for every night profile, e.g. a larger lift offset, or less contrast plus a toe.
3. Regenerate calib §B/§C/§D, the LUTs, the previews and the APL tables.
4. Re-run `gen_grade_data.py` and `verify_grade_data.py`.

**Interim, if the Unity side cannot wait.** Build Route C profiles:
- `gradingMode = External`, `externalLut` = the `CubeLutAssetImporter` Texture3D of `*_HDRext33.cube`, `postExposure = 0`;
- drive exposure crossfades with `LanbaiExposure.RouteCCrossfadeWeight` and call `SetDeltaEVWithBase(dEV, 0)`.

The builder does not offer this yet. It would be a small addition, `BuildProfile` with an External variant.

**How small the fix is (feasibility probe, second pass).** `python3 Tools~/verify_indep/lift_resolve_hint.py` keeps every other parameter from `grades_final.json` and re-solves only the lift trackball `(x, y, 1, w)` in the source-faithful Neutral model. The goal is the black the art simulator intended at input 0, plus the four darkest §C patches. The result is rendered through the 33³ LUT:

| Profile | Intended black | Shipped: black / §C max | Lift-only re-solve (indicative) | Black / §C max |
|---|---|---|---|---|
| S1 | `#02060C` | `#000002` / 8 | (0.9825, 0.9897, 1, 0.0214) | `#02060C` / 3 |
| S2, S11 | `#02060C` | `#010103` / 7 | (0.9773, 0.9894, 1, 0.0187) | `#02060C` / 2 |
| S3 | `#01060D` | `#000000` / 11 | (0.9768, 0.9883, 1, 0.0224) | `#01060D` / 3 |
| S4 | `#03040B` | `#000000` / 11 | (0.9852, 0.9877, 1, 0.0231) | `#03040B` / 3 |
| S4c | `#020209` | `#010103` / 5 | (0.9882, 0.9884, 1, 0.0108) | `#020209` / 1 |
| S6 | `#000308` | `#000102` / 5 | (0.9849, 0.9926, 1, 0.0106) | `#010308` / 2 |
| S7a | `#00070B` | `#000102` / 7 | (0.9809, 0.9945, 1, 0.0171) | `#00070B` / 2 |
| S7b | `#01060D` | `#000000` / 13 | (0.9773, 0.9890, 1, 0.0240) | `#00060D` / 3 |
| S8 | `#00050C` | `#000004` / 6 | (0.9801, 0.9912, 1, 0.0169) | `#00050C` / 3 |
| S8b | `#01060D` | `#010105` / 6 | (0.9821, 0.9897, 1, 0.0172) | `#01060D` / 2 |
| S9a | `#01060D` | `#000000` / 9 | (0.9762, 0.9889, 1, 0.0221) | `#01060D` / 2 |
| S9b | `#01060D` | `#000000` / 10 | (0.9764, 0.9886, 1, 0.0239) | `#01060D` / 2 |
| S12 | `#01060C` | `#000103` / 7 | (0.9792, 0.9903, 1, 0.0186) | `#01060C` / 2 |

- The LogC contrast leaves linear black at about −0.003. A lift offset of about 0.02 instead of 0.008, with the same blue-leaning wheel, cancels that. Once lift is re-solved, all 14 non-neutral profiles pass `MeasureAll` (±3) in the model.
- §B non-blooming targets: 23/61 → **12/61** off by more than 3 codes. The rest are saturated fills: S1 尾灯 12, S7b 水雾 10, S7b 灯晕卡中段 9, S7a 全反射暗镜 9, S8b 最纯的蓝 8. Their cause is Rec.709 luma and white balance in linear 709, not the black. They are "填值", which bible law 1 says to re-solve, so the corrected simulator must re-derive §B.
- These lifts are a pointer only. The owner re-solves in `make_grades.py` with a Neutral branch, then regenerates §B/§C/§D, the LUTs, previews and APL. After that this kit is regenerated with `gen_grade_data.py` and no code changes.

### M1 · MAJOR · The kit's engine-fidelity claims are circular and mislead the implementer

- `verify_grade_data.py` section D ("§C re-simulated … 0 codes") and the builder's notes present an art-simulator round trip as evidence about the engine. That check cannot catch B1.
- `Docs~/TestCard_Reference.png` has the footnote "夜间 profile 把输入 0 抬到蓝黑（k −6 那一格永远不是纯黑，红通道也不被压到 0）". The README (§2 step 6, §6) presents `MeasureAll` PASS as the expected outcome. Both are false for the parameters as shipped.
- An implementer who sees S10 PASS and 14 FAIL will conclude "set-up fine, grades off" and start hand-tuning 14 profiles against targets from a wrong model.

**Fix (owner: kit):**
- Make an engine-faithful check a gate in `verify_grade_data.py`. `Tools~/verify_indep/ppv2_neutral_check.py` can be imported as it is.
- Until B1 is resolved:
  - add a known-issue note to README §11 ("MeasureAll 预计在暗部失败；不要手调，等美术侧重解");
  - remove the footnote claim from the reference PNG;
  - offer the Route C interim.

### Minor

- **m1 · Bloom tint probably double-linearised (unverified; needs a screenshot).**
  - PPv2 passes `settings.color.value.linear` through `MaterialPropertyBlock.SetColor` (`BloomRenderer`). `SetColor` does gamma→linear in Linear projects; the kit's own grey card relies on exactly that (`Material.SetColor("#767676")` → 0.18).
  - The art simulator linearises once. So warm and cool bloom tints come out stronger in engine:
    - S8 `#FFE6CC`: simulated (1, .79, .60), engine ≈ (1, .59, .32);
    - S6 `#FFF4E8`: engine ≈ (1, .80, .62);
    - `WHITE_BLOOM` `#EEF4F8` about 13 % dimmer (luma 0.90 → 0.78).
  - The kit's comment "PPv2 converts bloom colour with .linear itself" should say this.
  - Fix: the art side confirms with one bloom screenshot, then enters colours pre-compensated (the hex whose sRGB→linear value is the wanted linear tint).
- **m2 · In-engine trims are lost.**
  - Bible §1.5 asks the implementer to trim postExposure (±15 % APL) in Unity. Re-running `Build Profiles & Volumes` resets every profile to the json, and `ValidateScene` reports trims as errors.
  - `LanbaiExposure.ScenePostExposure` is a compile-time copy, so b drifts by the size of the trim (weight error ≈ ΔEV·Δb/(4−b), under 3 % — harmless).
  - Fix: the README says trims must be sent back to `grades_final.json` (art side) and regenerated; never edit the profile assets by hand.
- **m3 · Measurement camera can see the Bus layer.** `MeasureAll` adds the grey card's layer to the culling mask. The README tells the implementer to move the cards to `Bus`. The camera then renders the whole bus from about the seat position, 1.5 m in front of the rig, and seat backs or pillars can cover patches, giving false FAILs. Fix: render the patches with the debug layer only, and sample the cards in a separate pass.
- **m4 · Undo leaves orphans.** Sub-assets created with `AddSettings` + `AddObjectToAsset`, or destroyed with `DestroyImmediate`, are not recorded with Undo. Ctrl+Z after a build can leave orphan or null effect entries; PPv2 strips nulls on load. Cosmetic.
- **m5 · `CurrentBase()` counts disabled volumes.** It ignores `enabled` and `activeInHierarchy`, but PPv2 skips disabled volumes. If the Director deactivates a scene volume's GameObject instead of setting weight 0, b is wrong. Document "weights only, never deactivate scene volumes", or check `v.enabled && v.gameObject.activeInHierarchy`.

---

## 3. Confirmed correct (no action)

**Profiles and volumes**
- All 21 profiles and volumes match the json and bible B1/B2/B3.
- Every scene profile overrides exactly the 22 §1.4 parameters: HDR + Neutral on every scene profile, Vignette/Grain intensity 0, clamp 4.24, fastMode true, anamorphic 0.
- Helpers override only their own parameters. Priorities are 1–15 / 96 / 99 / 100 / 199 / 200, with LENS_ARCHIVE above LENS_CLEAN. Initial weights: S1 = 1 and LENS_CLEAN = 1; the latter follows bible §1.4, which overrides the brief.
- The v1/v2 json conflict is resolved to v2 and logged.

**Editor code**
- Idempotent rebuild: effects are pruned, `SetAllOverridesTo(false)` runs before re-overriding, volumes are found by name, and stale `PPV_*` volumes are removed.
- The re-sort trick (toggle `enabled`) is correct for PPv2's dirty-layer sort.
- The reference-camera settings match §1.4.
- Menus are backed by public static methods that return strings.
- The Editor asmdef only references `Unity.Postprocessing.Runtime`, and dropping the asmdef also compiles.
- The test card follows §1.5: 11 float-emission patches 0.18·2^k, fog-free, on the debug layer, tagged EditorOnly; grey `#767676` and white `#E6E6E6` cards with Standard, smoothness 0, specular and reflections off; the four lookdev balls.
- §1.7: LDR verification profile at contribution 0 vs 1, and LUT import settings including Aniso 0.
- `MeasureAll` should run in edit mode. The S10 self-check will read about `#777777` (1 code; 33³ LUT).

**UdonSharp**
- `LanbaiExposure` implements w = dEV/(4−b) and −dEV/(b+4), the PPv2 fold for b, 2^−ΔEV overlay compensation, the Route C weight, VR lens-off at Start, and the Animator fallback.
- It uses no overloads, no generics and no `List`.

---

## 4. Files added by the verifier (nothing else in the kit was changed)

- `verify.md`: this report.
- `Docs~/Verify_SC_vs_PPv2_Neutral.png`: §C target vs engine prediction, per profile.
- `Tools~/verify_indep/ppv2_neutral_check.py`: source-faithful PPv2 Neutral model; §C, §B and Route C checks; renders the PNG with `--png`.
- `Tools~/verify_indep/parity_indep.py`: independent data parity check.
- `Tools~/verify_indep/compile_real_ppv2.sh`: compiles the kit against the real PPv2 3.0.2 runtime source (needs `CSC_HOME`).
- `Tools~/verify_indep/lift_resolve_hint.py`: a lift-only feasibility probe for the B1 fix. Its values are indicative and must not be shipped.

Still uncompiled in Unity: all C# and the shader. The compile above proves types against real PPv2 plus Unity 2021.1 references only. It does not prove the Udon extern whitelist or 2022.3 Editor API differences.
