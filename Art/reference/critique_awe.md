# 蓝白 / Lanbai: awe and beauty critique of ART_BIBLE v1

Reviewer stance: I read this as the user (the one who asked for 极致的美, then 「我要 震撼 宏大」, and who rejected the stylised build) and as the art director who has to sign it.

**Verdict: I won't sign v1 yet. 3 blockers, 10 majors, 4 minors.**

The bible's structure, thesis and rigour are excellent. Its weakest point is the one scene the user named when they said 震撼 宏大, the tentacle gate. Right now that scene is a 13° glowing violet slit seen through a windscreen, with ~60 countable arms, and 75% of the frame below the black floor of a headset. The gate is followed by 90 s of bright lavender tunnel, which uses up the dawn before it arrives. Around those two problems, colour discipline has drifted into three clichés: a fantasy-portal violet, teal-and-orange underwater, and pastel "cotton-candy" skies. The bible's own rules forbid all three.

Every number below is either measured on the bible's own files or verified through `bible_work/lutlib.py` (the corrected PPv2 emulation). Scripts and the proof sheet are in `art/critique_work/awe/`:
- `critique_awe_fixes.png`: the current grade and assets next to the proposed hue and grade fixes, on the same neutral mock frames (gate, dawn, dusk, undersea).
- `proposed_profiles.json`: full PPv2 parameter sets for S4, S4c, S6, S7a and S9b as proposed.
- `a1_greys.py` (colour cast of every profile on a grey ramp), `a2_pal.py` (Lab L\*/C\*/h_ab of every palette swatch), `a3_prev.py` (APL and hue-family share of every preview), `a4_prop.py` and `a5_sheet.py`.

Hue vocabulary used below is CIE Lab h_ab. **The indigo ladder L0–L7 sits at h_ab 230–283** (dark end 277–283, light end 230–257). **The tear's violet is h_ab 305–314.** "Purple" means h_ab 290–325 with C\* > 12.

---

## Keep: these are right, don't let the fixes erode them

- The thesis 「宏大在旅途，眼泪在归来」 and the frame that widens: window → roof hole → no walls → nothing.
- The 3 s of digital silence that replaces Mahler's scream. The sodium sweep crossing the cabin every 3.2 s, deliberately off the chorale's beat.
- Colossus 2 eating the moon at U7. The Orpheus rear window.
- The inverted Snell's window with the dusk sky inside it (7c). The sea as a ceiling with the palace's gold specks in it (8-i).
- The false awakening's inverted lamps and its 破绽 table. The dry rectangle under the bus.
- The dark-ink and light-ink photographic-negative pair of the user's two lines. The Zhuangzi line flipping at 其视下也.
- White never `#FFFFFF`. The ramp law. Neutral tonemapper. The cabin material table.
- The Lichtchen idea. It is the best idea in the document; only its colour is wrong (M9).

---

## BLOCKERS

### B1 · 4 触手之门: the tear is a slit in a window, not a rip across the sky

**Evidence.**
- Scale: 1.4 km at 6 km is 13.1° at U6. That is a hand-span inside a windscreen of about 75° × 33°. SPEC asked for "a rip across the whole sky, 1–2 km", and the user then raised the bar.
- Shape: the tear's width is never specified. In both explore renders (`skin/cluster.png`, `ink/hero.png`) it is a parallel-sided glowing bar of about 6:1, which reads as a lightsaber or a portal door.
- Framing: at entry the bible places the tear at +5°..+55° elevation. But §4.1 gives the windscreen top as +18° and the side-window top as +25°, so the top 30–37° of the tear sits behind the roof at the one moment it should be total. There is no way to look up.
- For all 45 s (U6 → U9), the grandest vertical object in the film is framed by the smallest frame in the film.

**Fix.**
1. **The sky keeps tearing.** At U6 the tear is 1.4 km (13°), whole inside the windscreen and centred at about +4°. From U6 the upper end propagates at **45 m/s**, which is ≤ 0.5°/s at 6 km and so obeys the bible's own rule for giant objects. The lower end runs down into the cloud sea. Size: **2.2 km by U7, 3.0–3.5 km by U8**, which is 45–49° at 3 km, so the rip runs off the top of the windscreen and the passenger has to look up to follow it. At U7 two secondary rips branch from the upper end: 600 m and 900 m long, 20–40 m wide, 25–40° off the axis, like stress tears in cloth. The U7 "fingers interlacing to close it" now visibly fails, and that struggle is the drama.
2. **Shape.** An asymmetric lens with maximum width 25–32% of its height, widest at 40% of its height. Width animates from 0.35 km to 0.9 km between U6 and U8. Edges are flaps of the indigo "silk" peeled outward by 50–150 m. The flaps' outer faces get a moon rim (`#A9C2FF`, 1–3 px) and their inner faces take the tear light. Keep the 600 fibre cards and 150 loose threads.
3. **A roof hatch.** Add one emergency roof hatch: 0.6 × 0.6 m clear glass, aluminium frame `#B8BBBD` / 0.45 / metal 1, mounted over the front entrance area just ahead of row 1. From the hero seat it frames about +40..+70° elevation at azimuth −20..+10° (⚑ confirm with §9 item 2).
   - U8–U9: the tear light falls through it as a 0.6 m square patch (cookie; display 170–200; `#E2E8F3`) that slides back along the aisle as the bus climbs. Light from something too big to see, landing on the floor.
   - The same hatch shows dawn and dusk sky overhead in 6 and 8, carries rain and drips in 1 and 12, and is where the roof erosion starts in 7. The first hole in the roof is the window that was already there.
4. Keep the moon being eaten at U7 and the ≥ 15% negative space on each side. The frame is now exceeded at the top, not the sides.

### B2 · 4 触手之门: fantasy-portal violet, and black on black

**Evidence.**
- The halo `#6B45C8` is the most saturated colour in the whole film (C\* 78, h_ab 307).
- The tear light `#CE8BFF` is orchid (C\* 67, h_ab 314). The thin-tip transmission `#6A3CFF` is C\* 111, an electric violet.
- This is the colour of every MMO portal and every "void" VRChat world, and the explore renders show exactly that read.
- It also contradicts the bible's own image (§6·4: the tear is torn indigo silk "露出底下未染的白"). Undyed white is not lavender.
- Value: under S4 the skin-cluster mock drops from APL 41.9 to 26.5, and **74.5% of its pixels fall below luma 12**. The void `#070A14` (L\* 3.0) and the tentacle body `#0B0C12` (L\* 3.4) are 0.4 L\* apart, below the black floor of every LCD headset.
- The mass of the arms, which is what makes them colossal, is invisible. Only rim lines survive, so the scene becomes a line drawing.
- The tentacle albedo, linear 0.004–0.009, is darker than any real material (the darkest natural surfaces are about 0.02). That gives a CG black-hole read.
- S4's grey ramp is tinted h 233–237° (violet-blue), and it tints the cabin too.

**Fix** (screen targets; re-solve the "填" fills with `calib_final.py`). Violet stays as "the other", but dusked, and only at the wound:

| element | v1 | new |
|---|---|---|
| tear core | `#F4EEFF` | **`#F5F2EC`** (undyed, C\* 3) |
| lip fibres | `#F1EAFF` | `#E2E8F3` |
| edge glow | `#C9B2FF` | `#C0B9E4` |
| halo (still breathes ±0.25 EV / 8 s) | `#6B45C8` | **`#5B57A1`** (C\* 45, h 298) |
| shafts, overlap | `#3A2A70` | `#31335A` |
| tear directional light (E 0.80 unchanged) | `#CE8BFF` | `#A99DE1` |
| tentacle tear-side rim | `#B48CFF` | `#A99DE1` |
| thin-tip transmission | `#6A3CFF` | `#5B57A1` |
| cloud sea under the tear | `#4E4F7A` | `#495270` |
| tentacle albedo (sRGB) | 14–24 | **30–44** (linear 0.013–0.025); the inky read comes from the wet streak specular |

**Luminous haze band (the value fix).** The sky within 50° of the tear's azimuth, from 0° to 15° elevation, is not void.
- It runs from `#484D63` (L\* 33) next to the tear to `#2A3041` (L\* 20) at 50°. The void `#070A14` begins only beyond 60° azimuth or above +35°.
- Fog colour at the tear azimuth equals this band, following the bible's own rule that fog colour equals the horizon colour.
- Arms now read as dark masses against light, which is how Villeneuve- and Colossus-scale shots work, instead of black against black.

**S4 grade:**
- postExposure −1.10 → **−0.85**
- temperature −7 → −6
- tint +5 → **+2**
- saturation −4 → **−10**
- contrast +22 → **+16**
- gamma (0.98, 0.975, 1, 0) → (0.98, 0.98, 1, 0)
- gain (1, 0.985, 1, 0) → (1, 1, 1, 0)
- bloom colour `#F2ECFF` → `#F0F0F6`

Result: the grey-ramp hue moves from 233–237° to 216–235°, and 18% grey goes from luma 78 to 87.

**Acceptance on the U7–U8 forward screenshot:**
- ≤ 40% of pixels below luma 12.
- Violet pixels (h_ab 290–320, C\* > 30) ≤ 10% of the frame.
- Three depth layers with ≥ 8 L\* between neighbours: near bodies 3–6, mid 10–16, far crowns 18–26, haze behind 20–33.
- APL 36–42.

Proof: `critique_awe_fixes.png`, row 1.

### B3 · 4c 门内: a bright lavender ring tunnel that spends the dawn before it arrives

**Evidence.**
- Brightness: the mist runs from luma 110 to 190 and APL from 60 to 100 over 90 s. Then come 3 s of black and the dawn at APL 110. The dawn is only **+0.3 EV** above what the eye has been adapted to for a minute and a half. The film's great release, 光作为召唤, lands on a tired eye.
- Colour: 67% of the 4c mock is violet. Together with the gate that makes about 2 minutes of violet (10% of the runtime) straight before the first colour scene. Rule §1.3.4 is kept on paper and broken on screen.
- Layout: "the same mesh × 0.80 every 400 m, centred on the path" produces exactly the concentric almond tunnel in `Preview_S4c`. That is the slit-scan stargate / near-death tunnel, and it also has an unintended anatomical read. It contradicts the scene's own "avoid regular concentric ellipses".
- `score.png` draws 4c as ladder L6 瓶覗 (`#B4D6E3`, h 230), but the palette is lavender (`#BDB4D8`, h 301).

**Fix.**
- **Dark grace.**
  - APL goes from 30 to 55, not 60 to 100. The mist between lips runs from `#1D2336` (luma about 25) at lip 1 to `#53606E` (luma about 70) at lip 8.
  - Lips and fibres stay thin and bright (luma 200–235): the light comes in lines, not fog.
  - The dial `#FFB65A` and the warm point `#FFF1DC` become the brightest warm things for 90 s. That is what "ein Lichtchen" needs.
- **Colour: the dye thins as you go deeper.**
  - Lip fibres: lip 1 `#E6E1F2` (faint violet, C\* ~8) → lip 4 `#D9DFEE` → lip 8 **`#C2D8E2`** (瓶覗, the ladder's L6) → the warm point.
  - Violet exists only at the outer wound. 4c becomes the first glimpse of 藍白 and foreshadows scene 10.
  - Trilight: sky `#4A4270` → `#3D4863`, equator `#5A5288` → `#4C5979`, ground `#2A2440` → `#1F283B`.
  - Cabin ambient: `#C9B8FF` × 0.35 → `#B5C3DB` × 0.30.
- **Break the tunnel.**
  - Use three lip meshes: a single rip, a forked rip, and a ragged hole.
  - Heights, in order: **1400, 1050, 1250, 700, 820, 460, 380, 260 m**. Not a geometric series.
  - Offset each lip's centre by ±40–180 m laterally and ±30–120 m vertically from the path, and rotate each about the path axis by ±0–35°. No two consecutive lips share a mesh or a rotation sign.
  - Spacing comes from the phrase timing. The path keeps ≥ 40 m clearance from every lip.
  - Fog 0.0015 → **0.0035** (90% at 660 m), so the seat never shows more than 3 lips at once.
- **S4c:**
  - postExposure −0.7 → **−0.9**
  - temperature −4 → −3
  - tint +6 → **+2**
  - saturation −8 → **−14**
  - Grey hue moves from 244–248° to 233–240°.
- Result: FLASH_TEAR fires from APL ~55 into the black, and the dawn at 110 is **+2.2 EV** above the last 90 s. That is how a peak lands.

---

## MAJORS

### M1 · 4: the colossi are fogged into ghosts, and fog and sky disagree

**Evidence.** With Exp fog 0.0006, the fog fraction is 78% at 2.5 km, **85% at 3.2 km** and 91% at 4 km.
- Colossus 1 carries the choreographed beat "the horror stands behind *Anfang*", and it sits at 3.2 km. It renders as 85% fog colour `#1B2240` (L\* 14) against a sky that is darker above the horizon (void L\* 3).
- So it comes out as a pale smudge brighter than the sky, ΔL\* ≈ 5–10. That is an inverted ghost, not a titan.
- It is also physically wrong. A fogged object can never be brighter than the sky at its own elevation, because that sky is the fog at infinity.

**Fix.**
- Every tentacle beyond 1.5 km gets `_FogCap` 0.6 plus a height falloff: fog × exp(−max(0, y − y_cloudsea) / 500 m).
  - Crowns end up 35–45% fogged and crisp, with a moon rim of 2–4 px.
  - Roots end up around 60% and still dissolve into the cloud sea through the existing root fog.
- Their crowns (L\* 12–20) now sit in front of the B2 haze band (L\* 20–33). Heads are clear and feet are lost, which is the Colossus read.

### M2 · 4: "countless" can be counted

**Evidence.** At most about 60 arms plus 11–15 colossi are ever visible. The story says 无数, and SPEC asked for "a tide, a flock, a crowd of arms".

**Fix.** Add a **far tide**.
- **Instances:** 300–500 impostor tentacles.
- **Atlases:** 3 alpha atlases × 8 silhouettes, 512×2048 BC7, cut from the LOD renders with the moon-side rim painted in.
- **Placement:** heights 150–600 m, distance 5–12 km, in an arc ±70° around the tear.
- **Rendering:** cylindrical billboards in one instanced draw, about 1k triangles, fogged 80–92%.
- **Motion:** vertex sway with phase = (distance to the tear) / 600 m − t / 6 s. A wave rolls toward the tear every 6 s: the tide.
- **Entry:** the tide rises out of the cloud sea with the U7 surge, from 0 to full over 12 s at ≤ 0.3°/s.
- **Cost:** about 0.2 ms. In the §1.9 cut order it sits after the mid-layer LOD step.

### M3 · 4: the 「生」 skin reads as earthworm

**Evidence.** `skin/hero.png` and `cluster.png` show regular annular rings at a near-constant pitch. At 25–40 m past a window this reads as earthworm, millipede or grub: small and crawling, the opposite of an angel's arm.

**Fix.**
- No constant-pitch annulations.
- Transverse creases appear **only on the concave side of each bend** (compression). Their pitch is 0.25–0.6 × the local radius, randomised ±40%, with depth proportional to curvature. The cloud side bakes a per-variant crease mask from Blender curvature (1024², B channel of `*_Occlusion`).
- The convex side is smooth and stretched, carrying the 5–20 cm longitudinal mucus streaks already specified. Those long shining lines are what read as scale.
- Colossi get 2–8 m macro relief (scar channels, erosion like wet basalt) and no creases at all beyond 1.5 km.

### M4 · 6 晨: lavender candy, and a grade that makes the dawn heavy

**Evidence.**
- After S6, 25.7% of the dawn mock is violet.
- Several targets lean toward the tear's hue:

  | target | colour | h_ab | note |
  |---|---|---|---|
  | cloud shadow | `#8E8FB5` | 292 | halfway to the tear's hue |
  | cabin ambient | `#A9A3C8` | 298 | halfway to the tear's hue |
  | Belt of Venus | `#D9B3B9` | — | pink |

- Pink, peach and lavender together are the stock "cotton-candy" sky. It is also the same recipe as dusk: warm highlights over lavender shadows, with gains of (1, .97, .92) against (1, .965, .90). Two skies 8 minutes apart would look alike.
- S6 also weighs the dawn down:
  - 18% grey → luma 84 (neutral is 118).
  - The mock's APL drops from 159 to 126.
  - Contrast +12 pushes the cloud shadows back toward the muddy grey that the art-director notes already rejected.

**Fix.** Make the dawn **two colours on white: 藍 and gold.** Save rose, violet and amber for dusk, so that dusk's "most colour" means something.
- **Palette:**
  - cloud shadow → **`#8593AA`** (h 272, C\* 14)
  - Belt of Venus → `#CFB7B7` (C\* 9, pearl rather than pink)
  - cabin ambient → `#98A4B8`
  - Rule: in scene 6, no area > 2% with h_ab 285–330 and C\* > 12.
  - Add an HDRI pick criterion: the anti-sun sky at 20–40° elevation must measure h_ab 255–275.
- **S6 grade:**
  - temperature −3 → −4
  - tint +2 → **0**
  - saturation +4 → +2
  - contrast +12 → **+6**
  - gain (1, 0.97, 0.92) → (1, 0.98, 0.94)
  - postExposure: retune to APL 110 (the mock suggests −0.8 to −0.9)

Proof: `critique_awe_fixes.png`, row 2. It is a crude hue remap of a mock, so read it for direction only.

### M5 · 8 暮: the tear's violet comes back, and the mirror is Uyuni

**Evidence.**
- Colour:
  - The mid-sky `#9C7FB8` and cloud shadow `#4A3560` sit at h_ab 311, **the tear's own hue**.
  - Other violet targets: curtain wings `#C9B8D8` (311), cabin ambient `#9C7FB8`, Trilight ground `#6A4A78` (317), 8-ii Trilight sky `#5A4E86` (302).
  - 16.5% of the dusk mock is violet. The palette is peach, rose and violet: the vaporwave sunset.
- Cliché: a sun on a horizon with a perfect vertical mirror is 天空之镜 / Uyuni, one of the most-built VRChat world types. 8-ii as specified (paired, flipped cloud cards over a flipped HDRI) is exactly that world.

**Fix, colour.** Shadows become indigo-slate and warmth stays only in the light (§1.3.2).
- mid-sky → **`#8687B2`** (h 292, C\* 24)
- cloud shadow → **`#363D59`** (h 285)
- curtain wings → `#C3BAD2`
- cabin ambient → `#8688AC`
- Trilight ground → `#4C5577`
- 8-ii Trilight sky → `#465582`

Proof: `critique_awe_fixes.png`, row 3.

**Fix, cliché.**
- (a) **8-i is the original image**: the sea as a ceiling, palace specks, the 3° slot. Hold it until F11, about 60–70 s instead of 40 s.
- (b) In 8-ii there is **no surface anywhere**: no specular plane, no ripple, no sheen at the seam.
- (c) Make it **another sky, not a reflection**, which is what 亦若是 actually says.
  - For y < 0, sample the HDRI at (−x, −y, z). That is a 180° rotation about the forward axis, not a flip.
  - The sun and the gradient still meet on the seam, so the burning line survives unchanged, but the clouds below are different clouds.
  - Lower cloud cards use different variants from the upper ones, at 70% of the count. Keep the ×0.82 and the (0.92, 0.95, 1.05) tint.
  - Nobody will be able to say "it's a mirror", but everybody will feel that the sky is the same above and below.

### M6 · 7a 海面之下: a teal pool with Avatar-cyan bioluminescence, and S7a crushes red

**Evidence.**
- S7a's grey ramp: −5 stops → **`#00100F` (R = 0)**, and 18% grey sits at hue 191°. That is the digital cyan §1.4 tested and rejected, and it breaks rule §1.3.5 ("never crush red to 0").
- The palette sits outside the ladder the bible declares:

  | swatch | colour | h_ab |
  |---|---|---|
  | caustic | `#9ED8E0` | 211 |
  | light shafts | `#7FC4DD` | 232 |
  | shallow water | `#2B7FA8` | 249 |
  | bioluminescence | `#5CD6F5` | 225 |
  | ladder L3 | `#1F4E79` | 270 |
  | ladder L4 | `#3A7CA8` | 257 |
  | ladder L5 | `#7FB2CC` | 241 |

- After grading, 58% of the mock is teal. Open ocean at 0–30 m is ultramarine; teal reads as coast or aquarium. `#5CD6F5` is the stock sci-fi glow.

**Fix: use the ladder the bible already declared.**
- **Palette:**
  - shallow → **`#3876AB`** (≈ L4)
  - light shafts → `#90BFE9`
  - caustic → `#ACD4ED`
  - total-internal-reflection mirror → `#11395E`
  - marine snow → `#697987`
  - bioluminescence → **`#8AC6FF`** (h 262)
- **Fog and sky, screen values:**
  - 0–15 m: `#2A8497` → `#507DA6`
  - 15–60 m: `#0F4263` → `#1A4163`, reaching L3 `#1F4E79` at 30 m
  - water-sky gradient top: `#7FD0D0` → `#94CAE9`
  - water-sky gradient middle: `#1C6A7A` → `#3E6486`
  - sun through water: `#A8DCEB` → `#B0D9F2`
  - shallow cabin ambient: `#3E8D95` → `#6186A7`
- **S7a:**
  - tint −2 → **+1**
  - lift (0.985, 1, 1, 0.006) → **(0.99, 0.995, 1, 0.008)**, so black → `#030B0F`
  - gamma → (0.975, 0.985, 1, 0)
  - gain → (0.985, 0.995, 1, 0)
  - Grey hue moves to 201–209° (blue).
- Keep the Snell's window core `#E6F3F8`.

Proof: `critique_awe_fixes.png`, row 4.

### M7 · 7b 河伯: teal and orange, and a 220 m palace nobody can see

**Evidence.**
- Each lamp is a 2200 K orange light plus a teal secondary light `#1E6F73` (h 203), falling off to `#1E5F66` (h 209): the blockbuster teal-orange.
- The physics given to justify it is also off for deep clear water. Red goes first, green next, and what remains is blue (h_ab ≈ 265–275), not teal.
- Scale: with fog 0.018 the fog is 90% at 128 m, so the 220 m complex is invisible beyond about 130 m.

**Fix: 朱 + 靛, cinnabar and indigo.** These are the two oldest Chinese pigments (lacquer, blue-and-white), and they are also the name.
- secondary light → **`#2A557B`**
- falloff → **`#26496C`** (→ L3)
- halo card gradient: `#FFC46A` → `#2A557B` → 0
- bioluminescence as in M6
- vermilion, gold, nacre and cowrie unchanged

**Scale by lamps:** two rows of 12 lamps along the processional axis at an 18 m pitch. Flames use `_FogMode 2` with `_Atten` 0.004. Their converging perspective lines show the 220 m that the fog hides.

### M8 · 9 星海: milky black, a dark ceiling, unreadable scale, and the dust motif missing

**Evidence.**
- (a) S9b postExposure +0.8 maps 18% grey to luma 151 and a −5-stop star background to luma 24 (`#14181E`). The deep of space goes milky exactly at fff; `Preview_S9b` shows it.
- (b) The bible never says what a mirror does after it crosses. If they keep rising, mirror 12 (297 m, 40 m/s) is 60 m overhead at F16 − 1 s. Its dark patina back (≤ `#1E3B34`) then covers **63% of the upper hemisphere's solid angle**, with mirror 11 adding another 24%. The Milky Way arch is eclipsed by a bronze ceiling at the climax.
- (c) A mirror twice as big and twice as far away looks the same size, and speed scales with size. So 「一面比一面大」 will not register.
- (d) §3.3 lists 星尘 for scene 9, but scene 9 has no dust particles.

**Fix.**
- (a) **Black stays black.** S9b postExposure +0.8 → **+0.3** (= S9a), contrast +12 → **+16**, night lift. The −5-stop background → `#0E1218`. The climb to APL 80 comes from **light sources**, all on the x^2.5 curve:
  - mirror-face emission = reflected sky × (0.2 + 0.08·k), so mirror 12 sits about +1.3 EV over the sky it reflects
  - Milky Way glow gain 1.0 → 1.8
  - top 200 star sprites HDR ×4 → ×8
- (b) **Each mirror turns to dust after it crosses.**
  - The mirror dissolves over 2.0 s (FBM clip, from the rim inward).
  - It releases 250 dust sprites, `#CDBF9C` → `#F2F6FF`, which rise and fade over 4 s.
  - At most 3 mirrors dissolve at once (≤ 750 particles).
  - That is the 星尘, and the zenith stays open.
- (c) **Constant absolute ornament.** Rim bosses at a 1.5 m pitch (84 on mirror 1, 622 on mirror 12) and TLV relief tiled at D / 40 m. Bigger mirrors show more repeats, so the eye can count size.
- (d) **Show the column from F14.**
  - The next 3 mirrors are visible below, with faces at 0.3× emission.
  - The 13th (≥ 2 km across) is visible the whole time as a faint vast disc 5–6 km down: rim thread at display luma 60–90, growing ≤ 0.5°/s until its last 10 s.
  - Awe here is anticipating the enormous.

### M9 · 12 醒: the Lichtchen is lime

**Evidence.**
- The firefly `#D4F06A` is C\* 67, the **second most saturated colour in the film** after the tear halo, at a hue (h_ab 115) that appears nowhere else. In `Preview_S12` the fireflies read as neon UI dots.
- The Lichtchen chain was built warm: the dial `#FFB65A` → the 4c warm point `#FFF1DC` ("ein Lichtchen"). It pays off in a colour the viewer has never seen.

**Fix.**
- **The one Lichtchen:** core **`#FCF5DA`** (C\* 14, warm white that rhymes with `#FFF1DC`), halo `#EBECA6` at α 0.30. The HDR core stays ×4.
- **The 46 field fireflies:** `#DEEA88` (C\* 50). They still read as firefly-green at distance.
- **Restraint: cut the "田野回答" 12 m/s travelling wave.** It turns the promised light into the trigger for an effect.
  - Instead, the Lichtchen flies out to the field and joins the 46. At the same colour and 20 m away, the player loses it.
  - Then Keats at 70 s: *Fled is that music*. The loss is the payoff.
  - If the wave stays, it comes ≥ 60 s after the Lichtchen joins and never before Keats.

### M10 · 1 站牌: the film opens with a vintage filter

**Evidence.**
- The first desktop frame gets LENS_ARCHIVE (monochrome grain 0.20, vignette 0.26) plus saturation −15. That frame is where the user will decide "beautiful or not", on their own PC.
- The grain stands for the 1951 mono record, but scene 1 has no music.
- Scenes 1 and 12 are the same place and the same reality: *the bus never moved*. The bible makes 12 CLEAN because "the real world is clear, the archive is the lie". By its own logic, scene 1 must be clean too.

**Fix.**
- Scene 1 uses **LENS_CLEAN**.
- LENS_ARCHIVE fades in over 8 s from **U0**, the radio's first note, so the grain is the record.
- It fades back to CLEAN over 8 s at **U3**, when the sound opens. Grain and vignette interpolate, so no occlusion is needed.
- Scene 11 keeps ARCHIVE.

---

## MINORS

### m1 · Poems: no coloured glows

The Rilke line has a violet glow, the Hebo line a cyan glow, and the Li Bai line a warm glow. Together they read as "magic text" or game subtitles.
- Turn glow off for every poem.
- Contrast comes only from the local dark underlay (`#0E1A2F` α 0.30, 40 px), and only where §7.2 already requires it (scenes 6, 7a, 8).
- Rilke's text colour `#E8E4F4` → `#E4E8F0`. The voice is human and should carry no violet.

### m2 · 天问: no flicker, no particle shatter

"0.3 s micro-flicker per character" and "shatters into the first stars" amount to After Effects text-disintegrate.
- Each character focuses in (softness 0.9 → 0 over 0.6 s, 120 ms stagger) and then holds steady.
- At F13 the characters dim over 1.2 s while **one star ignites at each character's centre**: 16 sprites, HDR ×6, FWHM 1.6 px.
- The 16 stars stay for all of scene 9: a small constellation where the question was.

### m3 · The bus never moved: one raindrop as the clock

Place a 4 mm drop decal on the hero-seat window.
- In scene 1 it starts sliding when the player sits, stops after 2 cm, and then hides with the rest of the rain state.
- In scene 12 the same drop is exactly there. It finishes its slide to the seal within 8 s after the second white.
- The whole dream took one raindrop. Local only, zero cost.

### m4 · Regenerate the charts after the fixes

`score.png` draws 4c as L6 while its palette is lavender, so the chart misreports the bible. After applying the fixes, regenerate palettes 04, 04c, 06, 07a, 07b, 08 and 12, the S4/S4c/S6/S7a/S9b LUTs and previews, and `score.png`. Update rule §1.3.4 to the measurable version:

> Outside scenes 4 and 4c, no area larger than 2% of the frame has h_ab 290–325 with C\* > 15.

---

## Patch list (v1 → v2, for the bible editor)

| § | item | v1 | v2 |
|---|---|---|---|
| 6·4 | tear size and behaviour | 1.4 km slit, 13° at U6 | 1.4 → 2.2 (U7) → 3.0–3.5 km (U8), tearing at 45 m/s; lens, width 25–32%; 2 branch rips; peeled flaps |
| 4.1 | roof | none | 0.6 m clear roof hatch over the front entrance; tear-light patch U8–U9 |
| 6·4 | colours | see B2 table | see B2 table |
| 6·4 | haze band | void around the tear | `#484D63` → `#2A3041` within ±50° az, 0–15° elev |
| 6·4 | tentacle albedo | sRGB 14–24 | 30–44 |
| 6·4 | far tentacles | — | fog cap 0.6 + height falloff 500 m; far tide of 300–500 impostors |
| 6·4 | skin normal | annular rings | concave-side creases only; convex streaks |
| App. B | S4 | −1.10 / −7 / +5 / −4 / +22 | −0.85 / −6 / +2 / −10 / +16; gamma (0.98, 0.98, 1, 0); gain neutral; bloom `#F0F0F6` |
| 6·4c | APL and mist | 60→100; mist 110–190 | 30→55; mist `#1D2336`→`#53606E`; fibres → `#C2D8E2` |
| 6·4c | lips | ×0.80 concentric | irregular heights, offsets, rotations; 3 meshes; fog 0.0035 |
| App. B | S4c | −0.7 / −4 / +6 / −8 | −0.9 / −3 / +2 / −14 |
| 6·6 | shadow, belt, ambient | `#8E8FB5`, `#D9B3B9`, `#A9A3C8` | `#8593AA`, `#CFB7B7`, `#98A4B8` |
| App. B | S6 | temp −3 / tint +2 / sat +4 / contrast +12 / gain (1, .97, .92) | −4 / 0 / +2 / +6 / (1, .98, .94); postExposure to APL 110 |
| 6·7a | water palette | `#2B7FA8` `#7FC4DD` `#9ED8E0` `#0F3A5A` `#5E7C86` `#5CD6F5` | `#3876AB` `#90BFE9` `#ACD4ED` `#11395E` `#697987` `#8AC6FF` |
| 6·7a | fog and sky | `#2A8497` `#0F4263` `#7FD0D0` `#1C6A7A` | `#507DA6` `#1A4163` `#94CAE9` `#3E6486` |
| App. B | S7a | tint −2; lift (0.985, 1, 1, 0.006) | tint +1; lift (0.99, 0.995, 1, 0.008); gamma (0.975, 0.985, 1, 0); gain (0.985, 0.995, 1, 0) |
| 6·7b | lamp secondary and falloff | `#1E6F73` / `#1E5F66` | `#2A557B` / `#26496C`; 2 × 12 lamps at 18 m |
| 6·8 | violet targets | `#9C7FB8` `#4A3560` `#C9B8D8` `#6A4A78` `#5A4E86` | `#8687B2` `#363D59` `#C3BAD2` `#4C5577` `#465582` |
| 6·8 | structure | 8-i 40 s; mirrored copies | 8-i until F11; 8-ii samples (−x, −y, z); different lower cards; no surface |
| App. B | S9b | postExposure +0.8 / contrast +12 | +0.3 / +16; light from mirror emission, Milky Way gain 1→1.8, stars ×8 |
| 6·9 | mirrors | undefined after crossing | dissolve to dust in 2 s; bosses at 1.5 m; column visible from F14 |
| 6·12 | fireflies | `#D4F06A`; field wave | Lichtchen `#FCF5DA` / `#EBECA6`; field `#DEEA88`; no wave, the Lichtchen is lost among them |
| 1.4 | desktop lens | ARCHIVE in 1 | CLEAN in 1; ARCHIVE from U0 to U3 |
| 7 | poems | coloured glows; 天问 flicker + shatter | no glows; 天问 focus-in, then 16 stars |
