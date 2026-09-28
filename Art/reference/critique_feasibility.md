# 蓝白 ART BIBLE v1: feasibility, VR safety and consistency critique

Scope: `art/ART_BIBLE.md` (1,434 lines) plus `grades_final.json`, `calib_final.md`, the 16 LUT strips, 16 `.cube`,
15 `hdr_external/*_HDRext33.cube`, palettes, previews, `score.png` and the `lens_tech` shaders and tables it adopts.
The target is Unity 2022.3 Built-in RP + PPv2 + VRChat SDK3/UdonSharp on PC VR at 90 fps.

Scripts I used are in `art/critique_work/` (`lutcheck*.py`, `bloom*.py`, `cct.py`). They import the team's own
`lens_cine/ppv2.py` emulator (with the bible's corrected AP1 matrix) so the numbers can be compared directly.

**Verdict: not ready to hand over as "law" yet. Three blockers:**
1. The helper-volume exposure maths is wrong for PPv2.
2. The authorised tear flash actually comes out at about +2.5 EV full-field and reaches VR luma ~225.
3. The full-field overlays are graded, so exposure and grade changes under them are visible.

Everything else is fixable with number changes. The LUT files themselves are correct.

---

## 0. What I verified and found correct

| Check | Result |
|---|---|
| Strip sizes | All 16 `*_1024x32.png` are 1024×32, 8-bit RGB. |
| Neutral strip = identity in the stated layout (x = b·32 + r, Unity row 0 = green 0, so PNG row 0 = green 255) | Exact at all 32³ lattice points (0 codes). PNG top row G = 255 and bottom row G = 0. Through a numpy emulation of PPv2 `ApplyLut2D` with bilinear sampling, 5,000 random colours plus (0.1,0.5,0.9), (0.9,0.2,0.05), mid-grey, black and white come back with a maximum error of 0.48 codes. |
| Neutral test is diagnostic | A row flip or an R/B transposition gives errors of about 255 codes, so the test catches both. |
| `.cube` parsing | All 16 × 32³ files and 15 × 33³ files parse with exactly N³ entries. Red is fastest: each strip matches its cube within 0.5 codes in red-fastest order and is off by about 250 codes in blue-fastest order. |
| `.cube` vs PPv2 `CubeLutAssetImporter` | Compatible: single-space separators, only `TITLE` / `LUT_3D_SIZE` / `DOMAIN_*` keywords, and `#` comments. |
| `Neutral.cube` | Identity within 5e-7. |
| S10 LUT | Identity within 0.115 codes. |
| `S10_HDRext33` | Equals Neutral(LogC⁻¹(x)) within 5e-4, using the non-precise LogC that PPv2 uses (`USE_PRECISE_LOGC 0`). |
| LUT vs HDR path (re-ran `verify.py`) | Mean 0.25–0.35 codes, p99 < 0.9 codes. See M-13 for the max-error caveat. |
| Monotonicity | No monotonicity breaks, except S2/S11: 324 lattice steps with a −0.2-code wobble. That is invisible, so no action. |
| Appendix B = `grades_final.json` | All 15 profiles match on priority, postExposure, temperature, tint, saturation, contrast, lift, gamma, gain and all four bloom numbers plus colour. Each scene's 后处理 line matches too. |
| Hex codes | 630 tokens, 417 unique, all valid `#RRGGBB`, all upper-case. |
| Kelvin labels | Sun, moon, sodium and lamp hexes are within 3–9% of blackbody CCT (McCamy): 9000 K → 8756 K, 3200 K → 3321 K, 2400 K → 2508 K, 2050 K → 2135 K, 2200 K → 2291 K, 8000 K → 7872 K. The exception is the tube (m-1). |
| PPv2 facts stated in §1.4 | Correct: Neutral 0.18 → 118/255; tonemapper enum not interpolable; weight-linear postExposure = EV-linear; "never raise one while lowering the other"; `lightsUseLinearIntensity = false` gives E = c·I^2.2, 2 → 4.6×, ×1.37 = double. |
| Photosensitivity table | `FlickerTable.cs` has 42 dips, 72–149 ms, levels 0.045–0.342. Dip starts are ≥ 0.6 s apart, and the last dip ends 1.57 s before "Gott". Both match §1.8. |
| Rest of §1.4 / §1.8 | Grain and vignette are killed in VR; no AO, SSR, DoF, motion blur or CA; no VRChat mirror. All good. |

---

## BLOCKERS

### B-1 · Helper volumes assume additive postExposure, but PPv2 lerps to an absolute value
**Where:** §1.4, §1.8, Appendix B helper table, `grades_final.json → helpers`, `make_grades.py` ("weight = EV/2.4").

PPv2 `OverrideSettings` does `param = lerp(current, override, weight)` for every overridden parameter. The override
value is an absolute target, not a delta. The bible writes BEAT_UP "+1.0, weight = the beat's EV", WHITE_RAMP "+2.4,
weight 0.42 = +1.0 EV", MIRROR_PULSE "+0.35", and so on. What the engine will actually do:

| Event | Base postExp | Intended | Actual with the bible's weight | Consequence |
|---|---|---|---|---|
| Break-out U6, BEAT_UP w 0.5 in 0.4 s | S3 −0.9 | +0.5 EV | **+0.95 EV** (0.59 EV per 0.25 s) | Breaks the 0.5 EV / 0.25 s law |
| U9, BEAT_UP w 0.3 in 0.2 s | S4 −1.1 | +0.3 | **+0.63 EV in 0.2 s** | Breaks the law, and lands on top of the 150 % tube flash |
| Exit to dusk, w 0.8 | S8 −0.5 | +0.8 | **+1.2 EV** | Overshoots APL |
| After white, w 1.0 | S11 −0.15 | +1.0 | +1.15 | About right, by luck |
| Water entry, BEAT_DOWN w 0.5 | S7a −0.8 | −0.5 | **−0.1 EV** | The impact dip disappears; bubble peak APL rises |
| FLASH_TEAR w 1 | S4c −0.7 | +1.5 | **+2.2 EV** (before bloom, see B-2) | Flash 47 % stronger than authorised |
| WHITE_RAMP crash w 0.42 / swell w 1 | S9b +0.8 | +1.0 / +2.4 | **+0.67 / +1.6 EV** | The ramp is under-driven, so the 3 s overlay has to cover the missing EV and gets steeper |
| MIRROR_PULSE w 1 | S9a→S9b, b = 0.3 + 0.5·x^2.5 | +0.35 | +0.05 at mirror 1, +0.03 at mirror 2. **Zero at x = 0.40, then negative.** Mirror 12 ≈ **−0.43 EV** | Pulses darken the frame from mirror 3 on (F13 + 62 s) |

**Fix (exact, keeps EV-linear envelopes):**
- Give each exposure helper only `postExposure`, with a far target: `H_up = +4.0`, `H_down = −4.0`.
- Every frame, the Director computes the current blended base b = Σ(weightᵢ · postExpᵢ), using the priority-ordered lerp chain it already evaluates.
- It then sets **w = ΔEV(t) / (H − b)**. The result is b + ΔEV exactly, and w is linear in ΔEV.
- Put helper bloom and saturation into separate helpers with their own weights (`FLASH_BLOOM`, `WHITE_BLOOM`, `WHITE_SAT`). Otherwise they get dragged by the corrected small exposure weights.

Values for the planned events (H = ±4):

| Event | Weight |
|---|---|
| Break-out | 0.102 |
| U9 | 0.059 |
| Dusk exit | 0.178 |
| After white | 0.241 |
| After second white | 0.200 |
| BEAT_DOWN | 0.156 |
| FLASH_TEAR desktop / VR (see B-2) | 0.319 / 0.255 |
| WHITE crash / swell end | 0.3125 / 0.75 |
| MIRROR_PULSE | 0.35 / (4 − b(t)) |

Also fix the `make_grades.py` envelope strings and the JSON `_changes` text.

Note: under Route C (External LUT, profile postExposure = 0) the old "weight = EV" happens to be correct. Say so in §1.7, and give the implementer the formula so that Routes A and C use one Director code path.

### B-2 · The "only authorised flash" is about +2.5 EV full-field and peaks near luma 225 in VR; its lead-in is unspecified
**Where:** §1.8 (FLASH_TEAR), §6·4c/5, helper table (bloom 14 / 0.6 / 0.8).

- PPv2 bloom threshold is gamma-space: linear = 0.6^2.2 = 0.325. With softKnee 0.8, bloom starts at **scene-linear 0.065**, so the whole 4c lavender mist blooms. The intensity multiplier is 2^(14/10) − 1 = 1.64, applied to the sum of about 9 pyramid levels.
- Uniform-field estimate with the emulator's bloom model on a 4c field at display 100:
  - As specified: display 225, **+2.5 EV**.
  - Even with the exposure corrected to +1.5: **+2.2 EV**, because the bloom override alone adds about 0.7 EV.
- §1.8 caps VR full-screen APL at luma 150 outside the white, and this moment is not exempted.
- U12 says "前方光点充满视野 → FLASH_TEAR", but §1.8 demands no other change in the 1.5 s before the flash. The growth of the warm point to full field is an unspecified full-field brightening, right before the flash.

**Fix:**
- FLASH_TEAR exposure through the B-1 formula: **desktop +1.5 EV, VR +1.2 EV**. Luma 100 → 150 is +1.29 EV, so +1.2 EV lands at the VR cap.
- **No bloom override.** Keep S4c's bloom, or use a separate FLASH_BLOOM of at most intensity 8 and threshold ≥ 1.0.
- The warm point stops growing at **U12 − 1.5 s**, at a maximum of 12° diameter. Its own growth follows the ramp law (≤ 0.5 EV/s of full-field L).
- Re-run `flashcheck.py` on segment (a) with real bloom, and add a VR-peak check (max full-field luma ≤ 150).

### B-3 · Overlays are graded, so any exposure or grade change under a "hidden" overlay is visible (and can over-bright the white)
**Where:** `Lanbai_Overlay.shader` (renders before PPv2, as its header says); §6 transitions 9→10, 10→11, 11→12, 5→6; `calib_final.md` §B.

- **10 → 11.** BEAT_UP starts at weight 1 ("+1.0 EV, 4 s decay"), so it must be raised while the white overlay is at alpha 1. That multiplies the white by 2 before the tonemapper. Emulated:
  - VR white #D7E3E7 (fill ≈ 1.2–1.8 scene-linear) → **#F6FDFF** (luma ≈ 250, over the 224 VR cap).
  - Desktop white → **#FFFFFF**, which breaks "never #FFFFFF".

  That is a +1 EV step at the brightest moment of the piece. The same happens at 11 → 12 (+0.8 EV).
- **9 → 10.** During the 3 s mask, WHITE_RAMP is at weight 1 (+2.4 EV, bloom 18 / 0.35 / knee 1.0, where bloom starts at scene-linear 0). The fill `#D5F0FF @ +1.42` was solved under **S10**. Under S9b + WHITE_RAMP it displays **#FFFFFF even before bloom**. Then "WHITE_RAMP → 0, S10 → 1" drops it to #E8F1F5: a visible step, plus a VR peak above the 224 cap.
- **Second white.** The fill `#ADC7D9` is solved under S10, but S11 is the live grade. That part is harmless: it gives #A3B3BE vs #A3B4BD. S12 rising under the mask shifts the held field to **#A6BAC7** (+3 / +6 / +10 codes, a visible blue drift).
- **Plunge black.** S6 rises under the black overlay, so the black goes from S4c's #02020B to S6's #000309. It is tiny, but it happens.

**Fix:**
1. While overlay alpha > 0, Udon sets `overlay.rgb = fill(profile) × 2^(−ΔEV_helpers)`. This is exact, because postExposure multiplies before the LUT.
2. Change grades under a full overlay only as **same-frame hard cuts** (old 1 → 0, new 0 → 1), and swap the overlay fill to the new profile's pre-solved fill in the same `Update`.
3. Add fills to `calib_final.md` for:
   - the white under the end state S9b + WHITE_RAMP(w=1) + WHITE_BLOOM
   - `#A3B4BE` under S11 and under S12
   - black under S6
4. Keep WHITE_BLOOM at intensity ≤ 12 and threshold ≥ 0.8 during the mask phase, or fade it to 0 over the 3 s mask.

---

## MAJOR

### M-1 · Bloom threshold, knee and clamp semantics are wrong in the prose; the no-bloom rules cannot hold, and APL targets ignore bloom
**Where:** §1.4 ("threshold ≥ 0.85 保证普通表面不 bloom", "clamp = 24"), §1.6 ("线性 < 0.9 不 bloom", "诗句线性 ≤ 0.85"), §7.2.

- **Threshold.** PPv2 converts `threshold` and `clamp` with `GammaToLinearSpace`. Bloom then starts at `lthresh·(1 − softKnee)`, not at the threshold. Current knee start, in scene-linear before postExposure:

  | Profile | Knee start (scene-linear) | ≈ display where bloom begins |
  |---|---|---|
  | S1 / S2 / S7a / S8 / S8b / S11 / S12 | 0.40 | 133–166 |
  | S3 | 0.56 | 149 |
  | S4 | 0.45 | 127 |
  | S4c | 0.24 | 107 |
  | S6 | 0.49 | 136 |
  | S7b | 0.28 | 129 |
  | S9a | 0.24 | 148 |
  | S9b | 0.14 | 135 |

  So anything displayed above about 107–166 blooms.
- **Clamp.** `clamp 24` is gamma, which is **≈ 1,088 linear**. It does not clamp at 24. For linear 24, set **clamp = 4.24**.
- **Text.** The screen targets need scene-linear 1.3–3.0, not ≤ 0.85:

  | Scene | Target | Needed scene-linear |
  |---|---|---|
  | S3 | #F2EEE6 | ≈ 2.96 |
  | S4 | #E8E4F4 | ≈ 2.43 |
  | S7b | #DDF3F6 | ≈ 2.04 |
  | S8 | #FBE8E4 | ≈ 2.26 |
  | S9a | #E9EEF8 | ≈ 1.27 |
  | S12 | #E8F1F5 | ≈ 1.77 |

  At 0.85 the text shows only #AAAFB5–#DADDE2. Either rule, "text never blooms" or the text colours, has to go.
- **Look impact** (emulator, bloom on vs off, same frames the previews use):

  | Frame | APL change | Clipping |
  |---|---|---|
  | S4 mock | 25 → **54 (+1.1 EV)** | clipping 0 → 4 % |
  | S9b | **+1.24 EV** | — |
  | S8 | +0.46 EV | — |

  Uniform-field estimates:
  - 4c mist designed at 190 → **≈231**, which breaks "永远不是满屏白".
  - S6 sky at 220 → ≈248.
  - S8 sky at 200 → ≈224.

  All §2 APL targets, previews and LUTs are bloom-free, so the in-engine APL check (±15 %) will fail by up to 1.2 EV and the implementer will "fix" it with postExposure.

**Fix:**
- Rewrite the rule as **"bloom starts at scene-linear T₀ = threshold^2.2 · (1 − softKnee)"**.
- To keep everything displayed ≤ luma 215 out of bloom (knee start 1.3× that value), use these thresholds (gamma, current knees):

  | Profile | Threshold |
  |---|---|
  | S3 | 1.98 |
  | S4 | 2.01 |
  | S4c | 2.49 |
  | S6 | 2.30 |
  | S7b | 1.84 |
  | S8 | 1.99 |
  | S9a | 1.71 |
  | S11 | 1.78 |
  | S12 | 1.70 |

- Things that must glow then need ≥ +1 EV above that (lamp cores ≥ 4–6 scene-linear; tube fill `@ +1.03` → about `@ +2.2`).
- Or keep the soft look and delete the "never blooms" sentences, capping text at luma ≤ 215.
- In both cases, re-render the previews and `score.png` APLs with bloom on, and set clamp = 4.24.

### M-2 · VR motion numbers contradict the bible's own "never broken" limits
**Where:** §1.8 vs §6.

| Place | Spec | Actual | Limit | Fix |
|---|---|---|---|---|
| 4, U8 near tentacles | 8–20 m, "近处 30–40 m/s, 眼睛处 ≤ 60°/s" | 35 m/s at 8 m = **250°/s**; at 20 m = 100°/s | ≤ 60°/s | v ≤ d · 1.05 rad/s: **8 m → ≤ 8 m/s, 20 m → ≤ 21 m/s**. The 3–6 s window crossings the bible also states already imply 15–30°/s, so keep those. |
| 3a lift | vertical 0 → 12 m/s smoothstep 8 s | peak **2.25 m/s²**, plus 1.2 m/s² forward | ≤ 1.5 m/s² | ≥ 12 s smoothstep (peak 1.5), or 14 s while forward is also accelerating |
| 6 fall | 25 → 8 m/s in the last 150 m | average **1.87 m/s²**, smoothstep peak 2.8 | ≤ 1.5 | Start braking ≥ 280 m above the sea (smoothstep, peak 1.5) |
| 6 → 7a entry | 8 m/s → "下沉 2 m/s" across a 1.2 s bubble burst | **5 m/s²** | ≤ 1.5, "any speed change ≥ 4 s" | Arrive at 2 m/s (brake from 25 m/s over ≥ 310 m), or write an explicit occlusion exception |
| 2 poles | "4–5 m, up to 150°/s, keep dark" | 140°/s | "20 m 内 ≤ 60°/s, 永不破例" | Set poles ≥ 10.5 m from the eye line (11 m/s ÷ 1.047 rad/s), or rewrite the rule: continuous low-contrast ground/grass and ≤ 4-display-level unlit poles are exempt; salient objects ≤ 60°/s |

### M-3 · The overlay sphere does not contain the other passengers' heads
**Where:** §6·5 ("r 4 m, centred on the seat"), `Lanbai_Overlay.shader`.

The sphere is centred on the hero seat (row 1, right) with a 4 m radius. A minibus cabin is about 7.5 m long. Rear-seat players and anyone who stands and walks are more than 4 m away. From outside the sphere (Cull Front, ZTest Always) you see a disc, not a full field. Those players will watch R_Gate → R_Dawn, R_Sea → R_Dusk and the scene-9 → 11 root swaps happen during "black" and "white".

**Fix (either):**
- (a) Each client moves the sphere to its own head position every frame, with radius 1.5 m. A uniform sphere following head position is not a head-locked artefact.
- (b) Centre it on the cabin centroid with **r = 6 m**, which covers the 7.5 × 2.3 × 2.0 m box with margin. The existing 2 Hz out-of-bounds return handles people outside the cabin.

### M-4 · Baked-light double counting and cabin lightmap contamination
**Where:** §1.6, §5.4, §6·1, §4.9.

- **Stop lamp.** "Baked area light + a **Mixed** point light for realtime specular". In Baked Indirect mode a Mixed light adds full realtime **diffuse and specular** to everything in range, so the road, sign and pole get the lamp twice: about +1 EV on the lamp pool, which breaks the #676F76 gray-card target. The wet road already has `_Udon_Lamp` analytic GGX, and chrome and paint get the box probe.
  **Fix:** delete the Mixed point light.
- **Headlights.** They are "baked because the bus is parked" (§6·1) *and* "realtime spot 30 m / 35°" (§4.9). That is also double on the road.
  **Fix:** don't bake headlights. Use the one realtime twin-lobe spot in scenes 1, 2, 11 and 12, gray-carded to #6B553D at 10 m.
- **Cabin lightmap.** Stop lamp, cabin tubes and bake-time sky are baked in one pass (R_Stop bake includes "车内漏光", and the bus is static at the origin). The cabin lightmap will then contain the stop lamp's pool on the door steps and seats, and it rides along into scenes 2–3 and 11 while `_Udon_CabinLightmap` = 1. Per-light bake masking isn't reliable in Unity's progressive lightmapper, and VRChat uploads a single scene.
  **Fix:** bake the cabin with only the tubes enabled (stop, headlights and sky off). Save the lightmap as a normal texture `_CabinTubeLM` (+ `_CabinTubeLMDir`), and have `Lanbai/Cabin` sample it through uv1 × `_Udon_CabinLightmap` instead of `unity_Lightmap`. Then bake R_Stop with the bus hidden or with the bus's "Contribute GI" off.

### M-5 · Avatars are unlit inside the lit cabin, and the local player's hands miss the key lights
**Where:** §1.6 (no probes, Trilight only), §6·2 (sweep culling = Bus), §1.6 (world key culling = Bus + Tentacles + Player).

- The tubes are baked, so avatars get nothing from them. Scene 2's Trilight is #0E1422 / #0C111B / #050608, which means near-black friends and hands in a brightly lit bus through scenes 1 (inside), 2, 3, 11 and 12.
- The local player's own avatar is on **PlayerLocal**, which the world key light excludes. The bible's "玩家的手接到暖轮廓" (scene 8), "照亮手" (scene 9 mirror rim) and the Lichtchen glint won't reach your own hands.

**Fix:**
- Add a cabin avatar fill: one realtime spot or point per tube row, culling = Player + PlayerLocal, no shadow, colour #E4F1F3, gray-carded to #585F64 (E 0.8), intensity × `_Udon_CabinLightmap`. Alternatively, have Udon add tube colour × level into Trilight equator/sky while the tubes are on.
- Add **PlayerLocal** (and Player) to the world key, the sodium sweep, the mirror-rim point light and the Lichtchen point light.

### M-6 · "Not Important" cookie lights lose their cookies
**Where:** §4.8 ④, §6·2 (side-spill spots, Not Important, window cookie).

Not Important lights are vertex or SH lights, and Built-in ignores cookies on them. The "cold window rectangles sliding over the grass and tree trunks" will be a smooth smear.

**Fix:** make the two side-spill spots **Important** with culling = Roadside only. The ≤ 3 unshadowed pixel lights on the bus is not affected because they don't touch Bus. Alternatively, fake the rectangles in the roadside shader with a `_Udon_WindowRect` projection.

### M-7 · Far clip 12,000 m clips the scene-3 tear and the city plain
**Where:** §1.4 (far 12,000), §6·3a (tear "约 40 km 外"; 20 × 20 km light plain), §6·6 (towers 6–12 km).

- A 40 km tear is culled.
- Plain corners are up to about 14 km away.
- A 12 km congestus sits exactly on the far plane and will flicker.

**Fix (either):**
- Place the tear proxy at 11 km, scaled to 384 m tall (still 2°). Fade city points out by 11 km into the warm 3–5° horizon band. Keep towers ≤ 11 km.
- Or set far = 45,000 m. With reversed-Z, near 0.05 m dominates precision: a 1,900 m depth step at 40 km is fine for a lone emissive.

### M-8 · Colossus 2 physically cannot eclipse the moon
**Where:** §6·4 composition, choreography U7.

The moon is at +14° elevation with a 1.2° disc, so its top is at +14.6°. A 420 m colossus at 2.5 km can reach at most atan(420/2500) = **9.5°**, and less once the bus is above the cloud tops.

**Fix (pick one):**
- Place colossus 2 at **≤ 1.5 km** (with the bus ≤ 20 m above the cloud-top plane).
- Scale it to about **720 m** tall at 2.5 km.
- Lower the moon to +8°, which also relieves the windscreen top limit.

### M-9 · Scene-4 geometry: the tear mostly sits above the roof, and the approach distance doesn't close
**Where:** §6·4 ("入口时仰角约 +5°..+55°"; "U6 时 … 远 6 km"), §4.1 (windscreen −15°..+18°, side +25°), §4.8 (roof intact until scene 7).

- **Visibility.** Entering at a "+5°..+55°" span means about 70 % of the tear is behind the roof.
  **Fix:** enter at the tear's vertical middle, so it spans ±atan(700/D). It fills the windscreen symmetrically at D ≈ 2.1 km. Keep the hero-shot framing (U6–U8) with the tear's top ≤ +16°.
- **Approach speed.** From 6 km at U6 to entry at U9 is about 45 s by §2, a closing speed of about **133 m/s**. The bus does 35 m/s and is capped at 1.5 m/s². If R_Gate "approaches" at 133 m/s while `CloudFloor_moon` scrolls at bus speed, every tentacle rooted in the cloud sea skates across it at about 100 m/s.
  **Fix:** one world speed for everything attached to the cloud sea. Either scroll the cloud floor and ring at the gate's closing speed, or start at D(U6) ≈ 2.2 km and let the tear "open" (scale 0.45 → 1.0 over U6 → U8) while the bus closes 1.6 km.

### M-10 · Scene-9 mirror schedule vs the ≥ 10 s hold and vs the white crash
**Where:** §6·9c, §6 9→10.

- With the bible's own estimates (F13 16:40, F16 19:05, so 145 s), mirror 1 at F16 − 135.4 s is F13 + 9.6 s. Ignition ends at F13 + 4.2 s, so the hold is only **5.4 s**, not ≥ 10 s.
- Mirror 10 crosses at F16 − 9.5 s, inside the WHITE_RAMP crash (F16 − 10.2 → −9.0 at 0.83 EV/s). Adding MIRROR_PULSE's +0.35 gives **1.18 EV in 1 s**, over the 1.0 EV limit.

**Fix:**
- Solve the ratio r from the real labels so that Σ d_k ≤ F16 − F13 − 14.2 s. For 145 s: **r = 1.24**, intervals 2.5, 3.1, 3.84, 4.77, 5.91, 7.33, 9.09, 11.27, 13.97, 17.33, 21.49, 26.64 s, total 127.2 s.
- Suppress MIRROR_PULSE for any crossing inside the WHITE_RAMP window (mirrors 10–12). The cabin light-line still sweeps.

### M-11 · Scene 8b timing does not fit its own compression rule
**Where:** §6·8b.

The full plan needs 6 (sun collapse) + 8–10 (blue hold) + 8 (darken) + ≥ 8 (天问) = **30–32 s**, but compression only triggers "if F13 − F12 < 25 s". The §2 table itself gives 25 s. Also, 天问's trigger "≈F12 + 20 s" is earlier than the end of darkening (F12 + 22–24 s).

**Fix:**
- Trigger compression at **< 32 s**.
- Trigger 天问 at "end of darkening", not "F12 + 20 s".
- Compressed plan: 6 + 4 + 5 + 8 = 23 s.

### M-12 · Always-on shadowed directional light and client quality settings
**Where:** §1.6, §1.9.

- The depth-texture trick costs a depth prepass, cascaded shadow maps and a full-res screen-space shadow collect at 9 MP. That is about 0.8–1.5 ms on a 3060, and it is not itemised in the 5.3 ms.
- Shadow distance, cascades, pixel-light count and soft particles come from the VRChat client's quality level, not the project. The "25 m" cannot be relied on. If a user's settings drop realtime shadows, `_CameraDepthTexture` disappears.

**Fix:**
- Itemise it: world budget = 5.3 ms **including** ≈1.0 ms fixed shadow and depth.
- Gate every custom depth fade with `#pragma multi_compile _ SOFTPARTICLES_ON`, falling back to hard edges.
- Add "verify shadow distance and cascade behaviour in the client" to §9.

### M-13 · LUT and route details that will mislead the implementer
**Where:** §1.7.

1. **Import settings.** PPv2's LUT check also requires **Aniso Level = 0** (its "Invalid LUT import settings" box). Add it.
2. **Stray `.cube` imports.** `CubeLutAssetImporter` converts **every** `.cube` under `Assets/` into a Texture3D. The 32³ sRGB→sRGB display cubes and `Neutral.cube` would become External-mode-looking assets that are wrong (not LogC). Keep them outside `Assets/` (for DaVinci/ffmpeg only), or rename them to `.cube.txt`.
3. **Neutral test wording.** "画面必须完全不变" must be defined as **LDR mode with contribution 0 vs 1**. Comparing against the HDR/Neutral S10 render differs by design (no tonemapper in LDR) and would look like an orientation bug.
4. **Screenshot-check limits.** The display-LUT round trip cannot recover highlights that clip in the S10 reference. In `verify.py`, S4's max error is **11.7 codes**. For negative-postExposure profiles (S3, S4, S4c, S6, S7a, S7b, S8, S8b), exclude pixels ≥ 254 in the S10 shot from the ±2-code check.
5. **Route C is not "equivalent" during transitions.** PPv2 blends External LUTs with `TextureLerper` in display-linear light, which is a dissolve, not EV-linear. For crossfades that change exposure (2→3, 7b→8, 11→12), drive w(t) = (2^(ΔEV·x) − 1)/(2^ΔEV − 1), or stay on Route A.
6. **Route B has no postExposure**, so every helper (BEAT, FLASH, WHITE, MIRROR) is dead. Say so.

---

## MINOR (consistency, legibility, housekeeping)

**m-1 · Tube colour temperature.** #E4F1F3 is **≈7,070 K with Duv +0.007** (slightly green), not "约 5000 K" (§4.3, §2 table). A 5000 K blackbody is #FFECD0. `score.png` plots scenes 1, 2, 11 and 12 at 5000 K in the warm colour, which is wrong for the "cool 藍白" thesis.
Fix: relabel as "≈7000 K 三基色，微绿 Duv +0.007" and redraw the score's colour-temperature lane.

**m-2 · Albedo rule broken by the bible's own tables** (§1.6: non-metal sRGB 48–231, nothing > 235, bus white ≤ 218).

- **Too dark:**

  | Item | Value | Suggested fix |
  |---|---|---|
  | Window rubber | #1A1A1A | #2B2B2B |
  | Dash | #2A2B2C | #353637 |
  | Steering wheel | #1E1E1E | #2E2E2E |
  | Destination-blind linen | #141414 | #262626 |
  | Floor | #2E3230 (R 46) | #323634 |
  | Chipped enamel ground | #22262B | — |
  | Tyre | #1C1C1C | below its own 0.02 exception → #2A2A2A |
  | Chu black lacquer | #141112 | — |
  | Fish back | #2A3A44 | — |

  Either extend the exception list explicitly (black rubber, lacquer and linen ≥ sRGB 38), or raise the values as suggested.
- **Too bright:** the sign enamel albedo #EBF6F7 (246/247, linear 0.92/0.93) breaks the 235 cap and pushes the sign into bloom. Use #DDE9EA (≤ 0.80 linear) and re-solve the lamp for #D0DBDF. Bus white #DCD6C6 (R 220) exceeds 218: use #D8D2C2.
- **Metals too dark to be metal** (Unity metallic range sRGB ≥ ~180):
  - Bronze lamp #7A5A3A metal 1 → #B08A62.
  - Chiwen #3A332A metal 1 (F0 0.04 = dielectric) → metal 0.
  - Bolt hole #0D0D0D metal 1 → metal 0.
  - Mirror rim #B8925A (B 90) → #C9A873.

**m-3 · Black floor and unreachable targets.** §1.3.5's floor is #04060B, but the plunge black #030409 (100 % of frame) and the 9a sky #04050A sit below it. `calib_final.md` already says #04050A is unreachable under S9a (best #04060E) and that the Lichtchen #FFB65A is unreachable (best #FAB45F).
Fix: floor → #030409 with an explicit exception for the plunge; update 9a to #04060E and 4c to #FAB45F in text and palettes.

**m-4 · Indigo ladder table vs scenes.**
- L3 claims the sign lettering, which is #1D3E66 albedo / #16406A screen.
- L6 claims the 门内薄雾, which is violet #6E6690 → #BDB4D8.
- L4 claims the cloud-entry mist, which is #4A5568.

Fix: move those cells to "echoes", or correct the hexes.

**m-5 · Text rules broken by the scene-8 user line.** "出海 + 6 秒" falls in the first 8 s of the scene (rule 7.4-2) and before the exposure ramp (≥ 6 s) plus the BEAT decay (4 s) settle (rule 7.4-1). Scene 8 also shows text for about 49 of about 105 s (47 % > 40 %).
Fix: exit + 12 s; trim 庄子's hold to 22 s.

**m-6 · Latin line length.** EB Garamond at 2.2° em is about 0.95° per character:

| Line | Length |
|---|---|
| Rilke (52 chars) | ≈ **48°** |
| Urlicht line 1 | ≈ 36° |
| Urlicht line 2 | ≈ 32° |

All exceed the 28° rule. Fix: break Rilke after "nichts", and Urlicht after "Engelein" and after "Ach nein!". Keats at 1.6° is about 26°, so it is fine.

**m-7 · CJK secondary lines at 1.6°** are 22 px on Index, where 鳞/阙/鱗 break up (the bible says so itself). Fix: raise to **1.8°** (25 px). Credits at 18 mm and 1.2 m are 0.86°, about 12 px on Index: raise to **Latin 24 mm, CJK names 30 mm** (keep Coleridge at 7 mm as the lean-in easter egg).

**m-8 · Camera HDR not stated.** Add to §1.4: reference camera **Allow HDR = on**, and Graphics tier settings HDR on (FP16). Without them, bloom and every `@ +n` fill clamp at 1.

**m-9 · Screen-locked dithering in VR.** PPv2 `Dithering` is a screen-locked noise, which contradicts §1.8's "no screen-locked element in VR". Fix: either whitelist it explicitly (±1 LSB, temporally varying) or disable it in VR and rely on `LanbaiSkyDither` in sky and overlay shaders.

**m-10 · Overlay dither decorrelates between eyes.** `LanbaiDitherLinear(c, wp − _WorldSpaceCameraPos)` hashes the per-eye view direction. On a surface 4 m away, the two eyes' directions differ by about 0.9° (≈22 hash cells), so each eye gets independent noise: binocular lustre on a 20–30 s full-field white or black.
Fix: hash the **object-space** direction `normalize(v.vertex.xyz)` in the overlay shader. Keep view-direction hashing only for skies at infinity.

**m-11 · Static flags.** R_Stop (slides away in scene 2), R_Road, R_Gate, R_Sea and every other moving root must have **Batching Static and Occlusion Static off**; keep Contribute GI on. Lightmaps survive movement, static batches do not.

**m-12 · Treadmill vs yaw.** The skybox never rotates and the world moves past a fixed bus, so any bus yaw makes sun, moon and stars turn with the bus. That contradicts "天日月星固定在大地坐标". Fix: allow yaw only where the sky has no features (scenes 2 and 11, overcast / sea ceiling), and state it.

**m-13 · 4c lip spacing is over-constrained.** 7 × 400 m = 2.8 km at 30 → 15 m/s in about 90 s gives at most about 2.0 km. Fix: place lip k at s(t_k) from the cue times and the speed curve; drop "间距 400 m".

**m-14 · Cloud entry.** Cloud entry is "3–8 s" but its APL ramp is "≥ 7 s". Fix: make entry ≥ 7 s.

**m-15 · Dawn reveal pops at t = 0.** `EvOverlayAlpha` starts at the 0.004 floor, so at t = 0 it jumps from the true black (#030409, L ≈ 0.0002) to about luma 20. Fix: add a 1.5 s pre-roll from L_black to 0.004 before the 7 s ramp. The metric counts it as free, and the eye sees a sunrise instead of a pop.

**m-16 · 天问 "每字 0.3 秒微闪".** Define it as monotonic ignition (overshoot ≤ 10 % of final luminance). Otherwise two 2.2° characters per 4.4° box flicker as flash pairs (box-mean Δ ≈ 0.15).

**m-17 · Other small inconsistencies:**
- 河伯 poem at 25 m can sit behind the palace façade (20–40 m). Use ≤ 15 m, or hold the palace ≥ 30 m.
- "近处触手会从 Rilke 前面经过" contradicts the choreography (nothing near until U8). §3c "还没有触手" contradicts colossus 1 rising at U6 + 10 s.
- Dawn sun disc: "#FFF3DE @ +4" is used as both fill and screen; add a calib row. Under S6 it displays about #FFF7EB or clips.
- Scene 8-ii fog (0.00025, "#C4929A 方向") has no calib row.
- Drip interval in scene 12: "2–5 s" vs "4 → 10 s". Pick one.
- The scene-4 "紫色贴花" should be implemented as an additive horizontal quad at cloud-top height, because Built-in has no decals and Projector is expensive.
- `FlickerTable` starts at U6 (about 45 s of dips) while the motif says "U7 起闪". Harmonise.

**m-18 · Performance items to itemise.**
- Scene-4 transparency: halo 2–3 × near-full-screen, 12 shaft cards, 600 fibre cards at the lips, cabin glass ≈ 0.7 FSE, cloud sea 1–2 FSE. That realistically sums to about 5–6 FSE against the "≤ 4 sustained" budget.
- Give per-element FSE caps: halo ≤ 1.5, shafts ≤ 1.0, fibres ≤ 0.8 (screen-area cap at U8), glass 0.7, cloud 1.0.
- Count cabin glass (≈0.7 FSE) in every scene's transparency budget.

---

## Re-test list after fixes
1. `make_grades.py`:
   - helpers split into exposure-only and bloom/sat
   - H = ±4 with the B-1 weight formula
   - bloom thresholds per M-1
   - clamp 4.24
   - FLASH_TEAR without the bloom override
2. `calib_final.py`: overlay fills per live grade (B-3); corrected unreachable targets (m-3).
3. `make_previews.py` and `make_score.py` with **bloom on**; re-derive the §2 APLs.
4. `flashcheck.py` segments (a)–(e) with final values plus real bloom, and a VR peak-APL check (≤ 150 except the whites; white ≤ 224).
5. Update §1.8 and §6 motion numbers per M-2, and the mirror schedule per M-10.
