# Rain kit: adversarial verification (round 2)

**Target:** `deliver2/Rain/`: 15 textures, 7 shaders, 3 `.cginc`, 4 U# scripts, `README_Rain.md`, 10 `Docs~` images, `Tools~`.
**Read against:** bible §0–§1 in full, then §3.3, §4.2, §4.6, §4.9, §5.4, §5.5, §6·1, 1→2, §6·2, §6·3 (rain lines), §6·11, §6·12, §8.1 #3, and `WORLD.md`.

**Status of the kit:** no kit file has changed since 14:35. The previous `verify.md` (15:13) reviewed this same state. This round re-checks every claim from scratch, including that report's own claims.

**How I checked:**
- **Textures.** Opened every texture with numpy/Pillow and checked:
  - size, channels, NaN;
  - opposite-edge seams against interior gradients, and the flipbook loop;
  - normal convention: bump height correlated with Data.R, plus a curl test;
  - drop-atlas normal signs and cell borders.
- **Code.** Read every shader and U# script line by line against Unity 2022.3 Built-in and UdonSharp 1.x. I fetched Unity's own `UnityShaderVariables.cginc` and `UnityInstancing.cginc` to confirm the stereo finding (M8).
- **Simulations:**
  - the kit's own `runners_ref.py` over 120 s, 180 lane-tiles;
  - drop refraction, kit formula against the two-interface model;
  - LUT decode;
  - colours through the bible's PPv2 simulator (`art/bible_work/lutlib.py`).
- **Compile checks.** Re-ran the kit's Slang and Roslyn checks on a clean copy. Both pass: 15/15 variants, and "C# CHECK OK".
- **Images.** Looked at every preview and sheet, plus 2–4× crops.

Evidence is in `scratchpad/vrain2/`: `phantom.py`, `heads.py`, `kymo.png`, `kymo_crop.png`, `stop_lamp.png`, `stop_bus.png`, `stop_case_sign.png`, `stop_fg.png`, `glass_c1.png`, `cells_zoom.png`, `layout_labels.png`, `splash_alpha.png`, plus the two fetched Unity CGIncludes.

## Verdict: FAIL. There are 0 blockers, 8 major issues and 17 minor issues.

The data side is strong:
- every texture is a power of two, OpenGL-convention, seamless where it tiles, and free of NaN;
- the flipbook loops;
- the ripple LUTs are physical and match §5.5;
- the wet mask meets the bible's numbers;
- the drop atlases are clean;
- the glass preview is a beautiful, believable photograph.

What fails is:
- **what the shaders do in a headset and in the story's key moments** (M1, M2, M3, M6, M8);
- **what the kit leaves out** (M4 wipers, M5 road beyond the mask, M1 stencil window);
- **the stop preview**, which does not look photographed (M7).

### Compared with the previous report
- **All 7 previous majors reproduce independently.** I recomputed each one; the numbers are below.
- **New major M8.** Five vert/frag shaders read `_WorldSpaceCameraPos` in the fragment without setting the eye index. Under SPS-I, the right eye therefore shades with the left eye's position, and window reflections lose their depth.
- **Corrections to that report:**
  - The splash atlas clips at cell borders with α up to **0.30**, not 0.03–0.04.
  - The "+1.5 EV over the bible's luma targets" point is **a conflict inside the bible**, not a kit error (see "Bible conflicts").
  - At the stop setting, runner density 0.18 means about 45 running heads per m², not "occasional" (M3 note).

---

## MAJOR

### M1. Hero puddles: the still-water reflection is about 4.5 EV too dark, ripples brighten it, and the stencil window does not ship
- **What the code does.** In the calm state, `Lanbai/PuddleOverlay` keeps `dst × Fcalm` of the mirrored copy. The README (§2.4) renders the copies "以全亮度" (at full brightness) and sets `_LampSpecular` 0 under the mirror.
- **What it looks like.** The mirrored tube is `#E7FEFF @ +1.03`, about 2.0 linear.
  - From the hero eye, the door puddle reflection point is 39° from vertical (51° depression). Fcalm = 0.0205, so the tube in the puddle reads **#2F383E under S12**. At 51° from vertical it reads #374147.
  - The bible's §6·12 palette says "静水里的灯影 **#DDE8EA**" (the lamp's image in still water). That needs an effective reflectance of **0.72**.
  - The final image of the film ("一根灯管…在一个静止的水洼里成双", one tube, doubled in a still puddle) comes out as a dark smudge.
- **Ripples work backwards.** `brk` swaps in `LanbaiLampSpecular` at smoothness 0.97. That is the real tube radiance: peak ≈ 12 linear for F = 0.02, which clips to white. So every drip **flashes a bright ring into a dim reflection**, which is the opposite of what water does.
- **The puddles are inconsistent.** Ordinary `WetSurface` puddles also get the full analytic tube (clipped bright). The four hero puddles will therefore be the *darkest* water at the stop.
- **Not shipped.** `lens_tech.md` §2.6 says "the puddle shader writes stencil bit 128". Nothing in the kit writes stencil:
  - There is no window shader.
  - There is no mirrored-copy material: it would need Stencil Comp Equal and a way to pass the depth test *below* the opaque road, for example a window that writes far depth.
  - Copies of the tube, sign and case therefore cannot be built from this kit.
- **Fix:**
  - In calm state, show the analytic lamp at a still-water reflectance tuned to the screen target. Let the mirror copies carry only non-emissive parts (sign face, pole, case), or give copies `_MirrorGain` so emissives read about 0.7×.
  - Make broken water *darker and scattered*, not brighter: cap the broken lamp term at the calm value.
  - Ship `Lanbai/StencilWindow` (Ref 128, ColorMask 0, depth pushed to far) and `Lanbai/MirrorCopy` (Stencil Equal 128, reflected about y = 0, Cull Front), with setup notes.

### M2. Drop optics skip the flat glass/water entry refraction, so oblique drops over-report total internal reflection (TIR) and show a shifted world
`LanbaiDropRadiance(viewerInside)` calls `refract(I, -Nd, 1.333)` with **I = the ray still in air**. The ray first bends into the water at the flat pane, where sin θw = sin θ / 1.333. The kit's version makes even a flat water film go into TIR beyond 48.6°, which is impossible for parallel layers.

My own reproduction, using a 55° spherical-cap bead:

| incidence | TIR area, kit | TIR area, correct | median exit-direction error |
|---|---|---|---|
| 0° | 16 % | 16 % | 0° |
| 30° | 39 % | 30 % | 11° |
| 40° | 50 % | 37 % | 16° |
| 50° | 60 % | 44 % | 21° |
| 60° | 71 % | 50 % | 28° |

- **Where it shows.** The windscreen (azimuth −50..+25 from the hero seat) and most of the side window are seen at 20–60°.
  - There, beads turn into `insideColour × 0.6` blobs.
  - The "倒立的小灯" (the upside-down little lamp) in each drop lands in the wrong place.
  - `Lanbai/OneDrop` shares this function, so "that one raindrop" is affected too.
- **Why the preview hides it.** The preview used Cycles' real refraction.
- **Fix:** `float3 Iw = refract(I, -Npane, 1.0/1.333); float3 t = refract(Iw, -Nd, 1.333);`. Use the same pair for the TIR test, and mirror it in `glass_ref.py`.

### M3. Runners: trails keep advancing after the head is gone, then the whole channel refills in one frame
- **The bug.** In `LanbaiRunners` (and the identical `runners_ref.py`), the head fades at `fs1`. But `behind` is gated only by `traveled = (fs − fs0)·TV`, which keeps growing until the cycle wraps.
  - Because `age` is smallest right behind the phantom head position, **the crispest part of the clear channel is a moving front with no drop in it.**
  - At the wrap (fs 1→0), every bead in the recent channel reappears at once. This also happens at the end of every normal run, when the head leaves the 0.40 m tile row.
- **Measurement.** I ran the kit's own reference at the stop setting (0.03 m/s, density 0.18, trail 6 s, stick-slip 1) over 1.2 m² for 120 s, one layer:
  - **145 of 180** lane-tiles showed a headless clear channel (≥ 1 cm, up to **36 cm**);
  - on average 3.9 headless channels per m² at any moment;
  - **126 pops per m² per minute**, each refilling up to 36 cm of channel in a single frame.
  - Both layers together give about twice that.
  - `kymo_crop.png` shows it. The red head marks stop halfway down the diagonal front, the channel keeps growing without them, then disappears in one column.
- **Lesser points:**
  - Runners fade out in mid-glass instead of stopping and becoming a bead.
  - No runner can cross a 0.40 m tile row, so tall windows show segmented runs.
  - At the "still" default 0.18 there are about **45 moving heads per m²** across the two layers. That is a lot for "偶尔慢流" (occasional slow runs).
- **Fix:**
  - Use `traveled = (min(fs, fs1) − fs0)·TV`.
  - After `fs1`, freeze the head (speed 0) and shrink it into a bead over `_TrailLife`.
  - Refill the trail by "time since the head passed", carried across the wrap (evaluate the previous cycle too).
  - Consider `_RunDensityStill` ≈ 0.05.
  - Keep `runners_ref.py` in sync and re-render the Sheet_Glass strips.

### M4. Windscreen wipers are missing
- **What the bible asks for:**
  - 1→2: "雨刮开始每 5 秒扫一次，无人驾驶" (the wipers start sweeping every 5 s, with no driver).
  - §4.6: "挡风玻璃有两道更干净的雨刮弧" (the windscreen has two cleaner wiper arcs).
  - §6·2: the frame of scene 2 is "透过挂着雨珠的挡风玻璃" (through a windscreen hung with raindrops).
- **What the kit has.** Grep finds 0 hits for wiper / 雨刮 in the shaders, the scripts and the README. Through the whole of Urlicht, the blade mesh will pass over beads and runners that do not react. That is the eeriest beat of scene 2, and the most visible piece of glass in the film.
- **Fix:**
  - Add `_Udon_Wiper{0,1}` (pivot, blade length, current angle, time of the last pass) and compute "time since swept" per pixel from the arc.
  - Clear beads and runners there and refill them over 2–5 s through the existing deposition threshold `G`.
  - Draw a thin water line at the blade edge.
  - Add a small U# driver: 5 s period, starting from U1, with a smoothstep sweep.
  - Document the arcs so the dirt atlas matches.

### M5. `Stop_WetMask` stops on a straight line 27 m ahead of the hero seat, and the road beyond has no paint and no puddles
- **What happens at the edge.** At u = 1 (Z = +26 m), the mask still has:
  - paint, with A up to 0.80 (the centre dashes run into the border);
  - G at full variation (mean 0.63, σ 0.32);
  - puddles.
- **Outside the rect.** WetSurface falls back to `_WetMaskDefault` = (0, 0.5, 0, 0): no paint, no puddles, flat retention.
- **Where it shows.** The edge sits 4.4° below the horizon from the hero eye, inside the windscreen and the 30 m headlight beam. That is exactly §6·12's windscreen shot, "空路伸进薄雾" (the empty road running into the mist).
- **Scene 2.** The README sends extended road modules to the default, so **R_Road in scene 2 has no centre dashes and no puddles**, while §6·2 says "湿路同第 1 幕" (the wet road is the same as in scene 1). Painting the lines into the albedo would bypass the paint-wetness logic.
- **Fix:**
  - Feather the last 3–4 m of R, G and A into a tileable continuation.
  - Ship a `Road_WetMask` that tiles along Z (48 m = 16 × 3 m, whole 9 m dash periods) for R_Road and the stop's surroundings.
  - Or give WetSurface procedural paint (dash period, duty cycle, wear) for when the mask is off.

### M6. Notice-case glass: drops render as dark dots over the lit credits, and the case is equally wet in scenes 1 and 12
- **What the code does.** For a viewer outside the glass, `Lanbai/BusGlass` composites each bead as `refl·F + CabinCube(P, I)·(1 − F)` at α up to 0.92.
  - The README gives the case glass no `_CabinCube`, so the default is **black**.
  - Even a set cube would show the bus cabin, not the paper behind the glass.
- **Measurement.** At the README's `_RainOverride` 0.35, beads keep **94 %** of their full-rain area. **31 % of the glass** then has drop α > 0.5.
- **Impact.** The scene-12 credits (§5.5: case lit to 170–190 at +95 s, the one text the player walks up to read at 1.2 m in VR) would be seen through dark polka dots. Real drops in front of a lit sheet look *bright*, because they refract the paper.
- **Bible mismatch.** The bible says "第 1 幕满、第 12 幕少" (full in scene 1, few in scene 12). The README uses one fixed 0.35 for both.
- **Fix:**
  - For `!inside`, make drops mostly transmissive: α ≈ F plus a lamp glint, or add a `_BehindColour × _Udon_CaseLight` term.
  - Drive the case's rain per scene, about 1.0 in scene 1 and about 0.12 in scene 12. At 0.35–0.4 the evaporation threshold still keeps 94–95 % of the bead area, so "less water" needs either a lower value or a coverage-based remap.

### M7. The stop preview does not look photographed, and the glass preview does not show the two things it is meant to show
Brief item 6: "must look photographed".

**`Preview_Stop_Night` / `_Detail_1to1`.** A photographer would not believe this image.
- **Lamp.** The arm and the pole above the lamp are drawn as **broken 1-px dark dashed lines** against the glow (`stop_lamp.png`). There is no solid arm and no pole top.
- **Bus.** It is the Sign kit's placeholder box (`stop_bus.png`):
  - it has **white** disc headlights (measured luma 254), while the bible's headlights are warm halogen **#FFC47A**, "车头灯开着，这正是诡异之处" (the headlights are on, and that is exactly what is eerie);
  - there is no headlight beam and no warm-lit rain, although `rain_scene.py` emits 900 headlight streaks;
  - in a rain-kit preview, its windscreen has **no rain on it**.
- **Notice case.** It is a black slab (`stop_case_sign.png`).
- **What works.** The wet asphalt, the drip-ringed tube reflection and the lit streaks (`stop_fg.png`) are good.

**`Preview_BusGlass_Night` / `_Detail`.** This is photographic and beautiful as rain on glass. But:
- the **runners do not read**: there are faint channels, but no visible sliding heads (`glass_c1.png`);
- **"that one raindrop" cannot be found**, even though the README says the image shows "流下的水滴、那一滴雨" (flowing drops and that one raindrop);
- **three large warm bokeh discs** dominate the left half. The town is placed at 60–350 m in view, while the bible puts it at −70° azimuth, 700–1500 m, which cannot be seen through the right-side hero window. §1.3.3 says "远处的暖光永远很小" (distant warm light is always small), and there is no depth of field in game.

**Fix:**
- Stop: re-light the stop so the bus is either out of frame or a dark silhouette with warm beams and a rain cone. Use solid arm and pole geometry, and give the case paper or glass.
- Glass: use the real right-window view from the hero seat (lamp, sign and the paddy reflection, no town). Pick a moment with 2–3 runners crossing the tube bokeh, and put the one drop on the tube bokeh with its 2 cm trail visible. Add a no-DoF frame showing what the headset sees.

### M8 (new). Stereo: five vert/frag shaders use the left eye's camera position for both eyes, so window reflections collapse onto the glass
- **The bug.**
  - `Lanbai/BusGlass` (MAIN pass), `PuddleOverlay`, `OneDrop`, `DripDrop` and `WetOverlay` compute `V = normalize(_WorldSpaceCameraPos − P)` **in the fragment shader**.
  - None of them calls `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)`, and none carries the instance ID into the fragment.
  - Under SPS-I, which VRChat PC uses, `_WorldSpaceCameraPos` is `unity_StereoWorldSpaceCameraPos[unity_StereoEyeIndex]`, and `unity_StereoEyeIndex` is a `static uint`. It is set in the vertex stage by `UNITY_SETUP_INSTANCE_ID`, and in the fragment only by that macro. Otherwise it is 0.
  - (Confirmed in `UnityShaderVariables.cginc` and `UnityInstancing.cginc`, fetched into `vrain2/`.)
- **The effect.** The right eye shades every pixel with the left eye's view vector. The cabin reflection in the windows and the lamp highlights on the glass then appear **painted on the glass, at glass depth, instead of at the depth of what they reflect**. That is the classic "flat reflection" VR defect.
  - It matters most in §6·2, where "右窗是一面黑镜：车厢的倒影" (the right window is a black mirror: the cabin's reflection), viewed for minutes from 0.5 m.
  - The rippled puddle highlights have a smaller version of the same problem.
- **Why it slipped through.** The kit's `LanbaiVR.cginc` header copies the bible's `lens_tech` guidance that the macro is needed "only if the fragment reads `_CameraDepthTexture`". That guidance is wrong, and other kits that copied it are at risk.
- **Why the test won't catch it.** The usual "close one eye, then the other" check does not reveal it: each eye looks plausible on its own.
- **Fix:**
  - Add `UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);` as the first line of each of those five fragment shaders (the `v2f` structs already have `UNITY_VERTEX_OUTPUT_STEREO`).
  - Or compute V in the vertex shader.
  - Correct the comment in `LanbaiVR.cginc` and in `art/lens_tech/shaders/LanbaiVR.cginc`.
  - `WetSurface` is a surface shader, and `RainParticles` uses the camera position only in the vertex shader. Both are fine.

---

## MINOR

1. **Rings are world-anchored.**
   - Cells and the flipbook use raw `P.xz`, and drip impacts are stored in world space.
   - When R_Stop slides away at 1→2, the rings stay put while the puddles move, which shows through the open door.
   - Fix: use `P − _Udon_StopOffset` for R_Stop materials, and store impacts in stop-local space.
2. **The drip instructions cannot be followed.**
   - README §7 says to call `StopDrips` at 1→2 "在白 / 遮挡下" (under the white or an occluder). There is none at 1→2, which is one continuous shot.
   - The hanging drops would vanish in view.
   - Keep the drips running until cloud entry; this depends on item 1.
3. **Particle budget.**
   - README setup: lamp cone 1 + headlights 2 + elsewhere 1 + splash 1 + 4 drip falls + up to 4 drip splashes = **13 systems**. Moths come on top.
   - Bible §1.9 allows ≤ 8 systems. 3 300 + 24 + drips is also just over §6·1's "≤ 3 300".
   - Fix: one shared drip system and one shared splash system with `Emit(EmitParams, 1)`.
4. **Colour properties labelled "linear" get sRGB-converted by Unity.**
   - `_AmbientColor` (0.323, 0.371, 0.402) arrives as (0.085, 0.113, 0.134), 3.3× too dark.
   - `_BottomColour` 0.012 arrives as 0.0009.
   - Enter sRGB values (#9AA4AA; about 0.11) or mark the properties `[Linear]`/HDR.
5. **Streak colour and width.**
   - A lamp-lit streak at the target lightness under S1 is **#9EA8AE** (C* 4.8, h 245), against the bible's **#9AA8B4** (C* 8.2, h 253, ΔE 3.6). Add a `_Tint` of about #DCE7F3.
   - The visible line is FWHM 8 of 64 px, 1/8 of the quad. That gives 2.5–3.8 mm, not the README's "1/5 → 4–6 mm"; the bible asks for 4–6 mm.
6. **Stretched Billboard axis.** `_FlipV` covers a head/tail flip but not a 90° swap of the stretch axis. Add a U/V-swap toggle so a wrong guess about Unity's stretch axis is a checkbox.
7. **Splash atlas.**
   - Frames 9–11 and 13–15 reach their cell borders with α **up to 0.30** (frame 10: column 0 to 126).
   - The spray is cut on a straight line and bleeds into neighbouring cells under bilinear filtering and mips.
   - Re-pack with a scale-down or padding.
8. **Hero-glass compositing order (from inside).** Drops are drawn *over* the inner-surface cabin reflection. The reflection then has holes wherever there is a bead (about 31 % of the area at full rain). Add the reflection after the drops.
9. **`LanbaiOneDrop.Hide()`** leaves `_Udon_OneDropB.w = 1`. In scenes 2–11, a 4.4 mm × 22 mm bead-free strip stays on the rainy hero window with no drop in it. Publish w = 0 while it is hidden.
10. **The runner field rotates rigidly about each pane's pivot when the flow changes.**
    - During the 15 s departure (0→50°) and the 20 s lift-off, existing trails swing around the window centre (about 0.35 m at the pane edge).
    - It is documented, but it reads as swirling. Freeze the existing runners' frame, or cross-fade two frames.
11. **Ring aliasing.** The ring LUT's first rows reach slope **4.0**. A fresh impact renders as a moiré disc (`cells_zoom.png`), which will sparkle for about 50 ms per drop in VR, especially in PuddleOverlay, which has no spec AA. Band-limit young rows by footprint.
12. **Fog.**
    - `BusGlass` and `OneDrop` lack `#pragma multi_compile_fog`, against bible §1.6 ("所有自定义 shader", all custom shaders). The windows seen from the spawn (10–14 m, about 10 % fog) will be crisper than the body.
    - `DripDrop` applies `UNITY_APPLY_FOG` to premultiplied output; it should lerp toward `fogColour × α`.
    - All rain shaders use `unity_FogColor`, not `LanbaiFog`. That is acceptable until that file ships; say so.
13. **Dry road.** WetSurface keeps 15 % of the analytic lamp at wet 0 (`saturate(wet·2+0.15)`). Scene 11 wants "没有光带" (no light bands). It is harmless at smoothness 0.2, but expose the floor as a property and set it to 0 for R_Road.
14. **Drip landing points.**
    - The case drip lands **0.11 m outside** its `notice_case` puddle.
    - The sign drip lands 1 cm from the pole axis, on the 400×400 concrete base, where there is no puddle.
    - Bible §5.4: "每滴下面水洼一圈涟漪" (a ring in the puddle under each drop).
    - Move the drip points, or add a sign puddle off the base.
15. **Missing presets.** There is no preset for a new round's "雨在 20 秒里回来" (the rain comes back within 20 s, §6·12); `Preset_Stop` snaps instantly. Add `Preset_NewRound` (20 s).
16. **Documentation and text:**
    - **Puddle fractions** — the README/JSON give 18.7 % / 8.9 %, the layout sheet says 20 % / 8 %, and I measured **19.8 % / 9.9 %**.
    - **Sheet_Glass** uses "**瓷砖**" (ceramic tile) where "平铺" (tiling) is meant, twice, and has a large empty band.
    - **Stop_WetMask_Layout:** "站牌 sign" is printed on top of "滴 drip: sign" (unreadable), and "公告箱" covers a marker (`layout_labels.png`).
    - **Lip size** — README "1.5 mm 唇口" and the sheet's "唇 Ø3 mm" describe the same lip; say radius.
    - **LUT channels** — the B/A channels (height, for previews) are not documented in the README.
17. **Tools~ clutter and hard-coded paths.**
    - `compile_check/out/` ships a DLL and 19 generated `.slang` files, and `src/__pycache__/` ships too.
    - `cells_look.py` and `check_cs.sh` hard-code cloud scratch paths. `glass_ref.py` and `pack_splash.py` hard-code `../out/`.
    - Unity ignores `~` folders, but clean them anyway.

## Bible conflicts to raise with the art director (not kit errors)
- **§5.4 luma targets against §1.6 albedos.**
  - The bible says "湿路在灯池里 10–18、池外 2–5" (wet road reads 10–18 in the lamp pool, 2–5 outside).
  - But through the bible's own S1 simulator, wet asphalt at the bible's albedo (linear 0.02–0.035) under the pool's E 1.0 reads **luma 36–50**. Reading 10–18 would need an albedo of 0.004–0.006.
  - The stop preview (pool 47, APL 32) follows the physical numbers. The bible should decide which one is law before anyone tunes toward either.
- **§5.5 against the stop layout.** "站在箱前低头 30–40° 恰好看见灯管" (standing at the case and looking down 30–40°, you see the tube) needs the tube 7.9 m behind the viewer along the line of sight. In the layout it is 4.3 m from the case. The kit's `notice_case` puddle mirrors the credits instead. That is reasonable, but it should be recorded as a deviation.
- **§6·3:**
  - "入云…水滴横向拉丝" (on entering the cloud … the drops streak sideways) contradicts "U4 + 20 秒前玻璃干净" (the glass is clean by U4 + 20 s). The kit follows the latter.
  - "醒 0.4" (wake: 0.4) is ambiguous. The kit's 0.4 keeps 95 % of the bead area, so scene 12's glass is as beaded as scene 1's, minus the runners.

---

## Checked and correct

| check | result |
|---|---|
| Sizes and names | All 15 textures are power-of-two (2048², 2048×512, 1024², 512×1024, 512², 512×256, 256×128, 128×1024, 256²). Flipbooks are atlases with the frame count in the name (Flip8x8, Flip4x4, Atlas8x1). No NaN. |
| Channels | They match the README: RGB normals; RGBA data, flow, LUTs, drops and wet mask; streak and splash as R = luminance (R = G = B), A = alpha. |
| Normal convention | **OpenGL (G = +Y up)**. Bead normals correlate with the Data.R height gradient: +0.989 as OpenGL, −0.989 if flipped. Flipbook curl residual is 0.0015–0.0018 as OpenGL against 0.006–0.015 as DX. Bumps point outward. The drop atlases' normals correlate +1.00 with x and +0.93–1.00 with y. Flat = (128, 128, 255). |
| Tiling and loop | Bead normal/data opposite edges differ by no more than interior steps (for example 8.86 vs 10.47, 5.44 vs 5.59). Flipbook frames: edge 0.83/0.94 vs interior 0.85/0.84. Loop 63→0 difference 2.86, inside the frame-to-frame range 1.08–4.02 (median 2.23). |
| Ripple LUTs | Last rows are 0, so nothing pops at the end of a cycle. Drip ring front 0.43 m at 1.6 s, slope envelope τ 0.66 s, below `_BreakSlope` 0.04 from 0.8 s, below 0.004 from 2.15 s, flat by 2.4 s. That matches §5.5 (0.4 m at 1.6 s, τ 0.7 s, back within 2.5 s). Cell density formula is right (max 4.44 /m²/s). |
| Stop_WetMask | Road puddles 19.8 % (bible 15–25), shoulder 9.9 %. B covers exactly Z −7.80..0.05, X −2.71..−0.48 (bus Z −7.9..0.1, X −2.75..−0.45), with R = 0 inside. ×0.8 and 0.45 per §4.9. Dashes and edge lines are worn, no yellow. The `WetMaskUV` yaw/v-flip matches the PNG orientation (bus rect rows 183–277 as plotted). |
| Hero puddles | From the hero eye, the tube reflects at (0.01, −0.28) at 51° depression and the sign at (0.97, −1.06) at 35°, both **inside `door`**, seen through the open door at 1.36 m height. From the spawn, the tube reflects inside `spawn_walk` at 23°. |
| Drops | OneDrop head 3.9 mm wide (bible 4 mm). It never touches the frame edge, and RG = 128, B = 0 outside it. The path is 20 mm at ~1 cm/s, then 60 mm in 8 s (§4.6, §6·12). The pendant grows to 4.1 × 5.2 mm (4.8e-8 m³ ≈ Ø4.5 mm), lip at the top edge. |
| Streak atlas | Head at the top (v = 1), side borders at α 0, top edge ≤ 0.055. |
| Bible numbers in code | Porosity 0.5/0.55/0.6. Film smoothness 0.74–0.84. Puddle ×0.25, 0.97, N × 0.05. Paint 0.45 linear (entered as sRGB 0.70, correct) / 0.70. Shelter ×0.8 / 0.45. Glass tint #E9EFEA, α 0.06 (skylight 0.08), F0 0.04, smoothness 0.97. Tube I 15 gives E 0.99 at 3.9 m. Drip intervals 1.5–4 / 4→10 s over 480 s / 3.5–6 / 4–7. Rain-state presets per §4.6. Lean 50.2° at drag 1 and 26° at 0.5 (inside §4.6's 30–60° at road speed); windscreen climbs; lift-off goes up and back. |
| VR (besides M8) | SPS-I macros are in every vert/frag. The depth texture is read correctly (with the post-vertex macro). The pendant faces the centre eye. Near fades are 0.3/1.2 m and 0.15/0.35 m. Nothing is screen-locked, there is no ZTest Always, and WetSurface has geometric spec AA. |
| Globals | All are `_Udon…`. Lamp colours are converted sRGB→linear in `LanbaiLamps.cs`. `_Time.y` and `Time.timeSinceLevelLoad` are used consistently for the drip impact times. |
| Compile checks | Re-ran on a clean copy: `check_shaders.py` 15/15 OK, `check_cs.sh` "C# CHECK OK". This proves types and argument counts only. **All 7 shaders, 3 `.cginc` and 4 U# scripts remain uncompiled in Unity.** Notable unverified risk: `WetSurface` reads `IN.internalSurfaceTtoW0..2` directly (it should be fine with `worldNormal; INTERNAL_DATA` plus o.Normal, but check the Meta pass). |
| VRAM | About 18 MB by my count (README says about 20). |
| Licences | No fonts, third-party textures or models ship. Fonts appear only rendered into the `Docs~` PNGs. Nothing to license. |
| README | It is in Chinese and covers every shipped file, the import settings, frame counts, speeds, tiling in metres, the global Udon variables, presets, VR notes and what is uncompiled. Errors in it are listed in M1, M6, minor 2, 4, 5 and 16. |
