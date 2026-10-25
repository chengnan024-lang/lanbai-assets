VERDICT: FAIL

# Art review r10 · Act 4c "门内" (independent, 2026-10-23)
I looked at all 12 frames in iterations/10_folds_across next to 09_cloth_cues, with contrast-stretched 2× crops of 197 and 205. I also read the metrics json, note.txt, README §12, stranger_tests.md r10 and ART_BIBLE §2 / §2.2 / line 611. Luma is Rec.709 from the PNGs. The bus shell, frame and pillar are not judged. The constraints hold: 40 m clearance, fixed H and times, the dot core is never occluded, and in the sleeve no edge is in the forward frame.

## Beauty first
- **The strata are gone.** On 197, 200 and 205 the contour-line banding has been removed, and the sheets now read calmer and cleaner. 197 / 200 are still the best pair in the act.
- **The new folds are not folds.** At 2× and stretched they are 1-px hairline streaks that run *screen-vertical* whatever the edge does. On the near-vertical left edge of 197 they run parallel to the tear, which is what r09 objected to. On 205 they look like brushed metal or rain. The flat cloth is now even flatter: on 197, sd at (250,230) went from 1.23 to 0.62 and at (80,580) from 2.62 to 2.00. Mid-surface interest went down.
- **228 now separates from the coda.** The diff of 228 against 240 is 6.7, above the 5 asked. However, the 12 arcs are scattered evenly, all the same length and all in one plane. They read as **scratches or hairs on the windshield**, not as a sleeve around you. Peaks are 233-240, above the 170-200 asked.
- **240 / 246.4** are byte-identical to r09 (diff 0.00).

## r09 findings
| # | r09 finding | r10 | evidence |
|---|---|---|---|
| B2 | folds read as strata / no cloth read | **partly** | The strata are fixed. The ridges do not follow the edge normal, and the fold scale is fibre-thin rather than 0.05-0.12 H. The back-face band cannot be read at 960. Stranger r10: 197 "墙", 205 "玻璃或屏幕". The pass criterion (names cloth or fabric) is not met for the third round. |
| B4 | 200 APL 34.0 / 41 | **justified** | See the note below. It moves to N3. |
| S1 | sleeve = coda | partly | The diff is > 5. The fibres read as glass scratches: they are not denser at the frame edges and have no parallax layers. |
| S2 | 226 side window flat | open | 39.1 → 39.5. The centre line is still there. |
| S3 | 181 lip 3 line | open | Diff vs r09 is 0.46. Nothing changed. |
| N1 | coda breath | open | 240 / 246.4 are identical to r09. |
| N2 | json ≠ PNG | open | The json APL is 33.97 and the PNG measures 34.3. min_luma is still the bloom cluster. |

**B4 note.** At 200, ±15 % of 40.7 is 34.6. The json gives 33.97 and I measure 34.3, so the miss is 0.3-0.6 luma (about 1 % past the band edge). That is within the gap between the json and the PNG. The bible itself (line 227) quotes its lip-5 test frame at APL 34. The 197 → 200 → 205 curve (34.9 → 34.3 → 40.3) has no visible dip. Accepted.
**I reject the stated reason.** "Excluding the placeholder cabin gives 42.1" does not hold. Bible line 611 / the palette specify the 4c cabin as a dark silhouette (`#0C0E14`, × 0.30), so a real shell will not lift it. Rewrite §12 on the grounds above. Also, the r09 lever (lip 6→7 fog or the lip 7 inner face) was not tried; only the near-cloth cap was.

## Remaining items
**B2 blocking: the cloth still does not read as cloth.**
- **Orientation.** Take the ridge direction from the gradient of the tear's distance field (the edge normal) at the nearest edge point. Do not use screen or world V. Then check it on the vertical left edge of 197: the ridges must run horizontally there.
- **Scale.** Make each fold a soft ridge 0.012-0.02 H wide (about 7-10 px at 540) and 0.05-0.12 H long, with cosine shading of ±8 luma on the 36 base: lit flank +8, shadow flank -8. Use 3-6 per sheet. Keep the hairline streaks, but at ≤ 1/3 of their current amplitude.
- **Translucency, the cheapest strong cue.** Within 0.04 H of each torn edge, let fog light come through the cloth at +4-6 luma. Mottle it with low-frequency noise (about 0.03 H) so it reads as thin weave rather than a rim glow. Keep 197's near-sheet mean ≤ 37.
- **Gate.** Run a stranger test at 197 / 205 with two new sessions. One of them must say 布, 帘 or 织物. If r11 still gets only "撕裂的墙", escalate to the director whether "torn" is a sufficient read, instead of iterating a fifth time.

**S1 should: make the sleeve fibres feel like the sleeve, not the windshield.**
- Weight their density toward the frame edges (none inside about 0.25 W of the dot).
- Use two depths: near arcs long (0.15-0.3 H) and soft at 140-160; far arcs short and sharp at 180-200.
- Vary their lengths by 3×. Peaks must be ≤ 200.

**S2 should:** add the r08 plies in the 226 side window at +8-12 luma, and remove the line at x ≈ 480.
**S3 should:** at 181, put a darker mass behind lip 3 (cloth fog cap 0.85-0.9 for lip 3 only).
**N1 nit:** from 240 to 246.4, grow the glow +10 % and fade the ghost fibres. **N2 nit:** have the json measure the graded PNG.
**N3 nit (from B4):** rewrite the §12 B4 entry without the cabin-exclusion argument. Optionally lift the lip 7 inner face +3 luma at 200 only.

## To pass r11
B2 must be verified with crops of 197 / 205 that show edge-normal folds, plus a stranger test that names cloth. That is the only blocker.
