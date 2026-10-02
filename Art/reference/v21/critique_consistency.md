# 蓝白 ART BIBLE v2.1 — consistency and VR critique

**Scope.** `art/v21/ART_BIBLE.md` (2,049 lines), checked against the measured cues (`FromLocal/cues.md`, `cues.json`,
`cues_urlicht.png`, `cues_finale.png`), the v2.1 tools (`v21/tools/cues_v21.py`, `scene_data_v21.py`,
`verify_ramps_v21.py`), `v21/ramp_checks_v21.json`, the motion files it cites (`v21/work/restructure/motion_r.json`,
`v21/work/synthesis/dusk_motion.json`), `lens_tech/out/FlickerTable.cs`, `lens_tech.md` (the source of
`EvOverlayAlpha`), and `v21/score.png`.

**Method.** I grepped every label, time and second in the bible and machine-checked each "LABEL（t）" and
"LABEL ± n（t）" pair against `cues_v21.T`. I parsed the whole §2.1 table against `cues.json` plus the v2.1 sub-labels.
By hand I recomputed:

- every motion integral (3a/3b heights, the tear table, the 4c lip positions and speeds, the dawn descent, the 7a depths,
  the 7b door distances, the dusk slot angles);
- the FlickerTable cut;
- r, the 13 crossings and the snapping;
- every poem hold against the §7.4 formula, and every text share;
- every EXPO weight;
- a per-view version of the two overlay ramps.

The per-view script is `v21/work/critique/per_view_ramps.py`. It is self-contained: rerun it after any change.

**Verdict.** The timing spine is excellent. All 74 labels in §2.1 (48 measured, 26 v2.1 sub-labels) match `cues.json` and `cues_v21.py` to the hundredth of a second, and
every derived moment I recomputed is right. The three derived quantities are consistent everywhere (v_g 59.02, r 1.2265,
the 13 crossings). **Do not hand it over yet**, for these reasons:

- **One blocker.** The two overlay ramps (dawn, second white) are specified "per direction" but simulated and
  implemented with a single alpha curve. They fail the ramp law for views brighter (dawn) or darker (second white) than
  the forward test frame. The second white also fails even under the literal per-direction reading.
- **Five majors.**
  - The galaxy-ignition pin is calibrated from forward views only, so it leaves the up-view unpinned.
  - The 7c end APL (32) contradicts its own fog colour: the simulation gives APL 49.
  - The last mirror's +4 EV self-emission ramp in the white crash was never simulated.
  - No recording window covers the F1b1 sun return (282–337 s).
  - The text-share numbers put to the user use an ad-hoc partition.
- **Minor items.** The rest are leftovers, boundary mismatches between §2 and §6, and small number errors.

---

## 0. What I verified and found correct

| Check | Result |
|---|---|
| §2.1 label table vs `cues.json` + `cues_v21.SUB` | All 74 labels present (13 U, 13 U_sub incl. LIP1–8, 17 F, 5 F_sub, 26 v2.1 sub-labels); file s and t identical (0 mismatches) |
| Every "LABEL（t）" / "LABEL ± n（t）" in the text | 0 mismatches (7 regex hits were ranges, not errors) |
| Timeline mapping | t = file + 3.0 / file + 240.36; U12 → F0 = 3.00 s; playback fades 246.9 → 248.64 and 1170.96 → 1173.46; silence end 1178.46; white hold 29.15 s — all match `cues.md` |
| §2.2 durations and EV column (EV = 2.2·log2(APL/50)) | Every row sums and converts correctly |
| §2.3 measured lengths | All match `cues.md` (7c uses F8 → F9 = 94.0 while §2.2 7c ends at the exit, 87.2: consistent) |
| v_g = 2700 / 45.75 = 59.02 m/s | Same value in §2, §6·3, §6·4, §6·4c, §8, §9 and App. A/C |
| Tear table at v_g | D = 1.726 / 0.791 / 0.611 km, tops +18.7° / +45.9° / +54.0°, entry at 13.8% of the lens height: all reproduce |
| 3a / 3b motion | Heights 319 / 478 / 810 / 922 / 1 087 m; peaks 1.21 / 0.96 / 0.89 m/s²; 0.28 m/s at U6k: all reproduce |
| 4c lips (one smoothstep 59.02 → 12, 54.25 s) | s = 0 / 197 / 374 / 806 / 1 198 / 1 379 / 1 589 / 1 807 / 2 105 m and v = 59.0 … 15.5 m/s: all reproduce; band gaps 2.75 … 10.7 s |
| FlickerTable with the drop threshold `t < −45.75` | Drops 6, 8 sparse dips U6 → U7, 28 dips from U7, last at 177.89, max 2 dips in any 1 s |
| Dawn descent | Cloud top 533 m at 287.9, deck base 1 134 m at 305.4, 467 m below the deck at F1b1 (atan = 6.06°), 684 m brake to the sea at F2h, 53 m / 9.8 m/s at F2, 149 m at F1z, 354 m at 337.0 |
| Dusk fall | h = 2.5 / 24.3 / 49.5 / 110.6 / 147.8 / 170.6 / 285.3 / 290.5 m; slot 0.05 … 6.1°: all reproduce |
| r and mirrors | r = 1.226546; unsnapped 1032.41 … 1091.01, 1103.82, 1114.26 … 1149.31; only #4 (+0.55) and #6 (−0.50) snap within ±0.8 s; gaps non-increasing (23.63 … 2.50); the table in §6·9 = `ramp_checks_v21.json` = `cues_v21.MIRRORS` |
| E1 | Confirmed: `cues.json` `mirror_crossings_*` gaps grow 2.5 → 23.63 s |
| Poem holds (§7.4 rule 3, ×1.3) | Li Bai 11.96 · Rilke 10.60 · dawn 9.62 · river god 13.52 · dusk 10.40 · Zhuangzi L3 10.40 (full 16.64) · Tianwen 12.74 · Qiwulun 12.74 · Li Bai II 11.18 · Keats 10.60: every table entry matches; the two exceptions are flagged |
| EXPO weights | 0.102 · 0.062 · 0.306 · 0.154 (S6) / 0.156 (S7a) · 0.797 / 0.418 · 0.111 · 0.095 · 0.270 · 0.649 · 0.241 · 0.200: all reproduce |
| Ignition pin | `w_pin_max 0.909` in the JSON = 3.91 EV at b = +0.30: consistent with B3 "≈0.91 / ≈−3.9 EV" |
| 7c fog | `#2E2228` h 345.5 C* 7.2; `#5A3A3E` h 12.7 C* 15.2: outside the purple band, as claimed |
| Cuts | 248.64 / 1149.31 / 1248.96: the same in §1.3.7, §2.1, §6.x and `score.png` (three dotted lines) |

---

## 1. Blocker

### B1. Dawn and second white: "per-direction EV-linear" is neither what was simulated nor what `EvOverlayAlpha` does; both fail for off-forward views

**Where:**
- §1.8 (lines 229–230);
- §6·5→6 (line 1051) and §6·11→12 (line 1550);
- §6.x rows 18 and 38; §8.1 row 14 (Director);
- `verify_ramps_v21.py`: `dawn_sim` (lines 122–135) and `w2` (lines 256–272).

**What the bible says.** Each direction ramps EV-linearly for 7.5 s (dawn) or 6.5 s (second white). The start times are
staggered by direction.

**What was simulated.** One alpha curve, built from the forward frame's mean luminance (`Lbar` / `L11`), drives every
pixel. Only the start time differs by direction. Only the forward frame was tested. `EvOverlayAlpha(x, Lfrom, Lto, Lscene,
Lover)` in `lens_tech.md` Appendix A takes a scalar `Lscene`, so this is also how it will be implemented.

**What that means for a viewer** (`v21/work/critique/per_view_ramps.py`; windows 0.25 / 1 / 2 s, limits 0.5 / 1.0 / 1.8):

| Ramp | View | As simulated / as it will be built | Literal per-direction EV-linear |
|---|---|---|---|
| Second white, 6.5 s | Forward (L 0.018, APL 27) | 0.18 / 0.71 / 1.42 PASS | same |
| | Side window into the night (L ≤ 0.004) | **0.69 / 1.99 / 3.14 FAIL** | **0.26 / 1.04 / 2.09 FAIL** |
| | Any view darker than luma ≈ 28 | FAIL | FAIL (needs ≥ 7.55 s) |
| Dawn, 7.5 s | Forward (APL 110) | 0.18 / 0.71 / 1.42 PASS | same |
| | Door or sunlit-cloud view (APL 150) | **0.34 / 1.19 / 2.13 FAIL** | 0.21 / 0.84 / 1.68 PASS |
| | APL 174 | **1.48 / 2.51 FAIL** | at the limit (1.80) |
| | APL 200 | **1.78 / 2.89 FAIL** | **0.96 / 1.92 FAIL** |

The second white is the clearer case:
- The fill `#A3B4BE` (L 0.4415) is 6.79 EV above the floor, so 6.5 s is 1.04 EV/s for every dark direction.
- The 2-s stagger sends the dark windows first, which makes the dark case the one people see.
- E9's fix therefore fails its own rule.

The dawn's 8.0 s fallback does not rescue an APL 150+ view as it will be built.

Separately, the sentence in §1.8 "全画面的变亮速度……不可能慢过它们" is wrong. The full-field EV rate is the
luminance-weighted mean of the per-pixel EV rates: it is bounded by the fastest pixel and can be slower than it. The
bible's own E2 control shows this (1.82 EV/s full field against about 2.6 EV/s per pixel). The conclusion drawn from it
is still right: making every direction obey the law is sufficient.

**Fix** (verified by the script, all views PASS):
1. **Build the curve for the extreme view and limit the rate, not the duration.** Use T = log2(L_extreme / 0.004) / 0.85
   EV/s, so the 2-s window is at most 1.70.
2. **Dawn.** Build the one `EvOverlayAlpha` curve for the brightest view (Lscene = the door / sun-sector view; APL 210
   gives T ≈ 8.6 s). Every darker view then rises more slowly (proof: L_view − F scales the same curve by
   k ≤ 1). Result: 0.21 / 0.85 / 1.70 for APL 110 to 200 alike.
   - Timeline: 254.14 + 3.7 stagger + 8.6 = ≈266.4, which is 0.1 s after F0s. This is acceptable, because the tower
     response is < 0.1 EV.
   - Alternatively, trim the sun-sector delay from +1.5 to +0.5 s.
3. **Second white.** Mirror the dawn:
   - a 1.5 s pre-roll to a₀ = 0.004 / L_fill (it lifts sub-floor pixels to the floor, which is free);
   - then a(x) = a₀·(L_fill / 0.004)^x over T = 8.0 s.
   - Every view is then ≤ 0.22 / 0.85 / 1.70.
   - Total 1.5 + 8.0 + 2.0 = 11.5 s. Acts 11 and 12 are outside the music, so move cut 3 to 1251.96 and the act-12
     clock to 1254.96. To keep 1248.96 instead, start the pre-roll at 1237.46, which is under the radio click at 1238.46.
4. **Rewrite and re-simulate.**
   - Rewrite §1.8, §6·5→6, §6·11→12, §6.x rows 18 and 38, B3 and §8.1 row 14 to say "curve built for the extreme view,
     rate-limited".
   - Add a door-view dawn frame (APL ≥ 150) and a side-window act-11 frame (L ≤ 0.004) to `verify_ramps_v21.py`.
   - Replace the §9 fallback "7.5 → 8.0 s" with this rule.
5. **Ceiling dissolve.** "每像素 5 s" is borderline at 1.71 and uses the analytic bound of 4.26 EV. Word it the same
   way: per-pixel T = ΔEV_px / 0.85 ≥ 5 s. It is a shader-side crossfade that knows both states, so it can really be
   per-pixel.

---

## 2. Major

### M1. The galaxy ignition's pin is calibrated from forward screenshots, so a viewer looking up at F13 is unpinned

**Where:** §6·9b (line 1413); B3 (lines 1974–1975); §9 item 5 (line 1790); ramp JSON (the simulation uses
"forward view pitch +6").

**Problem.**
- The Director's ΔEV(t) = target(t) − scene(t), with scene(t) taken from four forward screenshots (F13, +0.6, +1.2, +5.4).
- The waves start at the zenith and the nadir. The forward frame (top edge ≈ +56°) sees nothing until ≈ F13 + 0.45 s,
  so the pin is ≈ 0 during that time.
- By act 9 the roof is gone (erosion 0.65) and the galaxy arches overhead, so looking up is natural.
- An up-view is about 46% ignited by 0.45 s. Rough estimate: +2.4 EV above the floor in 0.45 s, which fails the 0.25-s
  window by roughly 3×. The late pin then darkens it and the swell re-brightens it: an extra flash pair.
- This is the mirror image of the control `F13_ignition_release_from_F13` that the bible already rejects.

The §9 recording "抬头" would catch it, but the specification as written would fail.

**Fix.** Pin per client. PPv2 is local, and the Director already reads each client's head pose (`GetTrackingData`) for
the overlay sphere.
- Compute scene_view(t) from the wave elevation and the local head pitch, as the ignited fraction of that client's field.
- Fallback: ramp the full pin (≈ −3.9 EV) in during F13 → F13 + 0.15 s. Darkening is free and the forward view is below
  the floor anyway. The cost is that the Tianwen letters dim at once instead of over 1.2 s.
- Also correct B3 "≈0.9 → 0": the release starts from the post-wave pin of 3.55 EV, w 0.83, not 0.91.

### M2. The 7c end APL "32" contradicts the specified 7c fog; the exit numbers quoted as primary are for the superseded fog

**Where:** §2.2 7c row (line 392); §6·7c (lines 1277, 1286–1287: "APL 24 → 32", "预付只到 APL 32"); §6·7→8 (lines 1296
and 1300); §1.8 results (line 230); §6.x row 26 (line 1644); B3 (lines 1971–1972); `scene_data_v21` PHASES
(20 → 32).

**Problem.**
- E11 changed the 7c end fog from `#2A1E30` (display luma 33.9) to `#5A3A3E` (luma 65.1), about +2 EV linear. None of
  the APL figures were updated.
- The v2.1 exit simulation shows this: the spec fill `#6C4643` gives **apl_7c_end 49**; the v2 fill gives 28.
- The start fog `#2E2228` (luma 37, reached at 897.96) alone already puts a fog-filled frame at APL ≈ 30. The score
  draws ≈ 25 at that moment and §6·7c says 24 at 902.16.
- Meanwhile §1.8, row 26 and the headline "0.39 / 0.67 / 1.12, pin 2.87 EV, w 0.80" are for the v2 fog. The true spec
  case is 1.50 EV, w 0.42, 0.38 / 0.63 / 0.72.

**Fix.** Pick one option, then make §2.2, §6·7c, §6·7→8, §6.x, B3 and the score agree.
- **(a) Beauty-first: keep the dark 7c trough (APL ≈ 32) and the big reveal at the exit.** This is the trough before
  the dusk peak (§2.3 shape 1).
  - End the fog at a darker rose of the same hue family, for example `#3A2629` (h 10, C* 10.1, luma 42.5).
  - Re-solve its fill with `calib_final.py` and re-run the exit.
- **(b) Accept APL ≈ 49.** Then:
  - make pin 1.50 EV / w 0.42 the primary everywhere;
  - change "预付只到 APL 32" to 49;
  - redraw 7c in the score.

Either way, re-run `7c_rose_prepay` with the real start and end values (the check currently assumes 24 → 32).

### M3. The last mirror's self-emission "+2 → +6 EV" in the 1.2-s crash was never simulated, and the new mirror order puts big mirrors in view exactly then

**Where:** §6·9→10 step 1 (line 1475); `verify_ramps_v21.py` §15 simulates a static S9b frame with no mirror term.

**Problem.**
- This is a ×16 luminance step in 1.2 s on a mirror face. The line is carried over from v2 and was unsimulated in both
  versions.
- In v2.1 mirrors 10–12 cross at 1139.98, 1143.74 and 1146.81, and #12 is 297 m across. Mirror 13 fills the lower
  hemisphere in the last 10 s.
- If a mirror face covers ≥ 20% of a (downward) view, +4 EV adds about log2(1 + 0.2·15) = +2.0 EV in 1.2 s on top of
  the +1.0 EV crash. That fails the 1-s window.
- "最后一面镜" does not even say which mirror.

**Fix.**
- Name the mirror.
- Put its emission rise inside the same total-luminance line as the EXPO swell, or spread +2 → +6 EV-linearly over the
  whole 10.2 s (0.39 EV/s).
- Add the term to the white simulation, with forward and down views.

### M4. No recording window covers the one brightening that was only bounded by hand (F1b1, 318.36)

**Where:** §1.8 screenshot protocol (line 224); §9 item 9 (line 1794); ramp JSON `F1b1_sun_returns` ("analytic … mean
rate ×1.3").

**Problem.**
- The recordings are 99–282, 337–368, 898–970, 1016–1026, 1119–1150 and 1178–1256 s.
- The descent from 282 to 337 has no recording, although it contains the sun leaving at the deck edge (305.4) and
  returning in 2.2 s (318.36). On the return, the directional light goes 0.1 → 1 on the cabin, so the gold bands on
  the seats rise about 3.3 EV locally.
- Neither the sodium sweeps (25–39 s) nor the 12 bronze sweeps (672–729 s) are recorded either. Both are periodic
  cabin-wide light bands, which the flash rule applies to.

**Fix.** Extend (a) to 99–368 s, or add 282–337 s. Add 17–40 s and 668–735 s. Record F1b1 looking forward, at the aisle
or seats, and out of the door.

### M5. The text-share figures behind the user decision use an ad-hoc partition; by the bible's own scene rows, other scenes break 40%

**Where:** §6·4 poem note (line 960); §7.4 rule 2 (line 1697); §7.4 check (line 1723).

**Problem.** The check mixes units:
- 3 = U3 → U6k, but 3c and 4 are lumped together;
- 6 = F0 → F2h, although §2.2 splits 6 / 6b / 6c / 6d;
- 9a, 11 and 12 are omitted.

Recomputed with the on-screen spans (appear → gone):

| Unit | Share |
|---|---|
| 3c + 4 | (13.0 + 8.3 + 5.35) / 50.45 = **52.8%**, fallback 36.4% (the bible says 54% and 38%) |
| Act 4 alone (U7 → U9, 29.25 s) | **46.7%**, fallback 18.3% |
| **3c alone (21.2 s, Rilke)** | **61%** |
| **6d alone (26.26 s, dawn line)** | **48%** |
| **9a as in §2.2 (1001.21 → 1018.21)** | **≥ 53%** |
| 9a as in §6 (1009.21 → 1018.21) | 100% |

**Fix.**
- Define "幕" for rule 2 once. The natural choice is §2.2's act headers, merging 3a–3c, 6–6d, 8/8b and 9a–9c.
- Recompute. With acts: 3 = 28%, 4 = 46.7% (fallback 18%), 6 = 11%, 7b = 9%, 7c = 15%, 8 = 33%, 9 = 7%, 11 = 25%.
- Present the user with **"act 4: 47% with the full lyrics, 18% with Ach nein only"**.

---

## 3. Minor

### Leftovers of the old estimates

1. **Stale ignition split.** §2 (line 273) and §6·9c (line 1430) still say "扣掉点燃 4.2 s + 保持 10 s". v2.1 is 1.2 +
   4.2 = 5.4 s of ignition plus an 8.8 s hold; the sum of 14.2 s and r are unchanged.
   - Fix: say "点燃 5.4 s + 保持 8.8 s".
   - Also ask the local team to set `cues.json` `derived.hold_after_ignite` to 8.8 when they replace
     `mirror_crossings_snapped_t` (§9 item 1).
2. **"相隔八分钟的两片天"** (§6·6, line 1064). Dawn (254–265) and dusk (922–987) are about 11 minutes apart.
3. **Appendix C M-2 "晨从 310 m 刹车"** (line 2016) is the v2 figure. v2.1 brakes 684 m above the sea from 327.26; add
   "(v2)".

### §2 vs §6 contradictions

4. **Braking start.** §2.1 F6 (line 335) and the §6·7b table/prose (lines 1205 and 1225) say "车开始刹" at F6 = 735.56.
   The motion line (line 1213) and `motion_r.json` brake 740.26 → 748.26, which is what yields 35 m at F7. Fix: say
   "F6 + 4.7（740.26）起 8 秒刹停".
5. **Blue hour / act 9 boundaries.**
   - §2.2: 8b = 987.06 → 1001.21 and 9a = 1001.21 → 1018.21.
   - §6: 8b = 987.06 → 1009.21, and act 9 and 9a start at 1009.21.
   - Score: 蓝时 starts at 993.06 and 9 星海 at 1009.21.
   - Consequence: under §6, Tianwen appears in the first 0 s of act 9, against §7.4 rule 2; the check at line 1723
     marks ✓. Rule 1 exempts Tianwen, rule 2 does not.
   - Fix: adopt one boundary (9a from 1001.21 makes Tianwen +8.0 s), and list Tianwen as a rule-2 exception if needed.
6. **7b-ii start.** §2.2 says 668.60 (the gate pass); the §6 table says 672.0 (first lamp pair). §2.1 F5q says "12 对灯
   依次经过", but the first pair passes at 672.0, before F5q (675.36). Cosmetic; align the wording.
7. **Cabin fade table** (§4.8, lines 594–595).
   - The 1–3 row ends at 150.30 while the act-4 row starts at 133.80.
   - The act-4 row says "灯管 1 → FlickerTable", but the tubes were halved at U4h (E 0.4, §6·3), and §6·4 gives
     "基准 E 0.25". When 0.4 → 0.25 happens is never stated.
   - Fix: 1–3 → 133.80; act 4: "0.5 → 基准 E 0.25（U6 起，随 S4）+ FlickerTable".
8. **Act 11 timeline** (line 1528): "0–4 秒 白收缩进灯里（→ 1182.46；收缩全程 8 秒）" reads as two durations. Split it:
   0–4 s tubes and lamps, 4–8 s the sea.

### Motion and position numbers

9. **Dawn line exit height.** §6·6 (line 1090) says "→ 357.96，此时离海 17 m". 17 m is the height at 357.4
   (`motion_r.json`). At 357.96 it is **14.2 m**.
10. **7a depths.** The table (line 1155) says "363.26 → 373.26 | 0 → 7 m". 7 m is at F3 (367.21); at 373.26 the depth
    is **10.75 m**. At ≈387 it is **12.8 m**, not 10 m (line 1157). The F4, F3e and F5 depths are right.
11. **1→2 beat table** (line 749): "14.1 → 17.1" mixes file and timeline seconds in a t column. The *rot!* ends at
    t = 17.1 (file 14.1), 0.4 s before U1.
12. **River god separation.**
    - The lamp columns are at 9 and 27 m, so the door is 18 m to the left. The door's azimuth on the straight glide is
      −atan(18 / d): −6.1° at 706, −7.3° at 714, −12.2° at 730.5, −15.5° at 735.56. It only reaches −17° at 59 m
      (≈737.5) and −27° at 35 m.
    - So during the poem (714.0 → 730.5) it sits **17–22°** from the poem at +10°, not "≥ 27°" (lines 1257 and 1723).
      Rule 5 (≥ 12°) still holds.
    - "门在 −17° → −27°" describes F6 → F7 only. A fixed 18 m offset cannot give −17° earlier without yaw, which is
      forbidden outside acts 2 and 11.
    - Fix: correct the numbers, or state the actual door offset in `PalaceLayout.json`.
13. **In-cloud geometry.** The rise curve puts the bus above the nominal cloud top (1 047 m) at ≈118.1 s, 11 s before
    the breakout, while fog 0.067 is held to U6k. Say the cloud layer tops out at ≈1 085 m with wisps above, or that
    the 1 047 m figure is the post-breakout floor.

### Poems and §7.4

14. **Dusk line (903.0) vs rule 1.**
    - The line appears 0.84 s after F8c starts the 7c "曝光预付" (APL 24 → 32, 902.16 → 921.4), plus the new upward
      caustics and fog shift.
    - Rule 1 demands that the exposure ramps be over. The rise is only about 0.05 EV/s, so this is a wording problem,
      not a comfort one.
    - Either reword rule 1 ("EXPO 助手的爬升与衰减已结束；≤ 0.1 EV/s 的场景漂移不算"), or list the line as an
      exception.
15. **Keats (1321.96)** appears 14 s after its image settles (the Lichtchen is lost among the fireflies at ≈56 s =
    1307.96). Rule 1 says 4–12 s. This is carried over from v2, but the §7.4 check marks it ✓. Move it to ≈66 s
    (1317.96) or state the anchor.
16. **Urlicht lyric vs the tear core at U7.** At 150.30 the widest, brightest part of the lens (40% of the height) is at
    +5.0° on azimuth 0. The lyric at 0° / −6° is **11°** away, just under rule 5's 12°. It passes after about U7b. Put
    the lyric at −8° or −9°.
17. **Blue-hour stars vanish.**
    - §3.3 chains lamps → gold points → "蓝时的第一批星正好从那里出现" → the 16 Tianwen stars.
    - But §6·8b lights the first stars (993–1001), and the darkening then ends in "`#04060E`，没有星" (9a).
    - The chain as written has the stars disappear right before they are supposed to become the Tianwen stars.
    - Fix: say the first stars go out with the darkening, the zenith one last (it becomes the hand-off). Or keep that
      one star through 9a and make it the first of the 16.

### VR details

18. **White hold definition.** §1.8 (line 231) says "白光膨胀的最后 2 秒会越过 150 进入白，属于白". Counted that way,
    the time above VR luma 150 runs from ≈1144.3 to 1178.46, plus part of the 8-s shrink: about 34–38 s. That is not
    29.15 s.
    - The 30-s cap in `lens_tech` §3.3 is for holding the peak level. Say so explicitly ("峰值 `#D7E3E8` 保持
      1149.31 → 1178.46 = 29.15 s；爬升与收缩不计").
    - Or buy margin by cutting the digital silence from 5 s to 3 s.
19. **FLASH_TEAR APL.** §1.8 and §6·5 quote APL 34 → 59, measured on the lip-5 test frame. §2.2 says 4c ends at
    APL 55, so the real peak is about 83. That is still under VR 150; quote it.
20. **Pre-roll floor.** "真黑 L ≈ 0.0002" (line 1050) is wrong for `#030409`, which is L ≈ 0.0013 in sRGB-linear.
    The pre-roll lifts the frame from luma ≈ 4 to ≈ 13 in 1.5 s. It is free under the law, but it is not "看不出来".
21. **Palace hotspot duration.**
    - §1.9 (line 256) and §6·7b (line 1261) say the 6.4 ms stretch lasts 67 s (668.6 → 735.56). §9 item 10 says
      672–729, which is 57 s.
    - The palace is in view and baked-lit from F5 (644.96) through F8 (835.16) and into 7c, about 190–210 s. In v2,
      7b was about 95 s.
    - Budget the whole of 7b.

### Score (`v21/score.png` / `scene_data_v21.py`)

22. **9c end APL.** The score draws 9c 30 → **72** (`PHASES`, the S9b simulated frame); §2.2 and §6·9 say 30 → **80**
    (+1.5). Pick one.
23. **Scene headers** follow §6 (蓝时 at 993.06, 9 at 1009.21), not §2.2 (see item 5).
24. **Missing sub-labels.** The v2.1 sub-label lane omits F1t, F1b2, F7e, F8r and F9t, although §2.1 gives each an
    image ("云墙最高", "海镜的第一块", "静止", "水里最后的静止", "天花的镜带变厚"). Add them, or say the lane shows a
    subset.
25. **7c** is drawn 18 → 20 → 32 (see M2).

### Cue data

26. **F8r sits inside the sung phrase.** F8r ("一口气的休止", file 680.0 = 920.36) comes before the end of *Bereite dich
    zu leben!* (file 681.3 = 921.66 per `cues.md`, which §2.1 F8c itself quotes). On `cues_finale.png` the vocal line
    drops at about 681–682 and the swell rises from about 682.5. The "last still frame in the water" would land while
    the choir is still singing *leben*. Add F8r to the by-ear list in §9 item 1 (F9s is already there).

---

## 4. Suggested order of edits

1. **B1:** rate-based overlay ramps, extreme-view curve, second-white pre-roll and 8.0 s, re-simulated with
   door-view and side-window frames.
2. **M1:** per-client ignition pin.
3. **M2:** choose the 7c end (a or b) and propagate it.
4. **M3:** the mirror emission ramp.
5. **M4:** the recording windows.
6. **M5:** the text-share partition and the user question.
7. Minor items 1–26. Almost all are one-line edits.

Then re-run `make_score_v21.py` and `verify_ramps_v21.py`, and add three events: the per-view dawn, the per-view
second white, and the white crash with the mirror term.
