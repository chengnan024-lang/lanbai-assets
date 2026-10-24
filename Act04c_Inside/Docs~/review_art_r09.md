VERDICT: FAIL

# Art review r09 · Act 4c "门内" (independent, 2026-10-23)
I looked at all 12 frames in iterations/09_cloth_cues next to 08_resume, plus the metrics json, note.txt, README §12, stranger_tests.md r09 and ART_BIBLE §2 / §2.2. Luma is Rec.709 from the graded PNGs. The bus shell, frame and pillar are not judged. The constraints hold: 40 m clearance, fixed H and times, and the dot core is never occluded. At 226 the sleeve edge shows only through the side glass, beyond the windshield frame.

## Beauty first
- **197 / 200** are the best pair in the act. Each has a dark near sheet, a lit inner face and a halo dot sitting near lip 7's rim, not in its centre. At 200 the new right-hand sleeve edge gives a strong depth cue.
- **The folds are visible now** (197 flat cloth sd 7.7 against r08's ~0.5), but they draw the wrong thing. On 205 (upper left) and 200 (left) they are **iso-bands of the tear's distance field**: parallel copies of the torn outline that repeat its notches like contour lines or tree rings. This reads as rock strata or wood grain, which explains why the stranger still says "wall". Real tension folds run *across* the tear, radiating out from it, and fade within about 0.1 H.
- **205** has the same arch as r08 (pixel diff 3.9 mean, from the folds only). It still reads as a round gap, but the bottom is open to the sill and the dot sits high and off-centre. It is an arch, not a target.
- **210 / 218.75** are good: open fog, receding sheets and real depth.
- **226 fwd → 246.4**: the forward sleeve is still the coda image. 228 vs r08 differs by 0.7 luma mean, and 246.4 vs r08 by 0.01. "Loose fibres ×7" cannot be seen: the peaks are 135-148, against the 170-200 asked.

## r08 findings
| # | r08 finding | r09 | evidence |
|---|---|---|---|
| B1 | lip 7 frames dot | justified | My r08 ask was ≥ 0.60 of the half-width. r09 delivers 0.68 and shows that 0.75 and 0.8 have no solution (README §12). 200/205/210 are delivered. 200: the dot is at the rim. 205: the dot is in an open-bottomed arch, with no ring and no concentric rims. 210: unframed. It reads as an opening, not a target. Accepted. |
| B2 | cloth-only cue | partly | Folds are rendered after the fog (sd ≥ 4 met). The back-face band is present but faint. The 197 near sheet is ~36-38 (target ≤ 36, borderline). Stranger r09: first time "被撕裂", but still "墙" at 197 and "墙上的圆缺口" at 205. The pass criterion (names cloth or fabric) is not met. |
| B3 | 226 side APL | justified | Bible §2 line 143 and §2.2 define APL as the forward desktop view. The forward 226 is 52.5 against 49 (+7 %), in band. The side window at 39.1 is not a bible gate; my r08 B3 was misapplied. It moves to S2. |
| S1 | sleeve of fibres (228/231) | open | Unchanged from r08 (see above). |
| S2 | 218.75 rim / 181 lip 3 | partly | 218.75 is improved by the folds. 181 lip 3 is still a drawn line. |
| N1 | coda breath | open | The 240 → 246.4 glow profile is identical (239/149/107 vs 240/150/108). |
| N2 | metrics json | open | The json min_luma still does not match the PNG. |

## Remaining items
**B2 blocking: the folds read as strata.**
- Fix: replace the sin(distance-to-edge) banding with anisotropic folds. Run the ridge direction along the edge normal, i.e. perpendicular to the tear.
- Use 3-6 folds per sheet, at 0.08 H spacing along the edge. Set length 0.05-0.12 H, tapering to zero, with ±25 % shading from a cosine of the fold normal and no hard iso-lines.
- Widen the back-face band so it reads at 960 px: 0.5 % H and -10 luma, on 15-20 % of the edge.
- Rerun the stranger test at 197/205. It must say cloth, curtain or fabric.

**B4 blocking (new): 200 forward APL is 34.0 against 41 (-17 %), outside the bible's ±15 %.**
- Fix: lift the lip 6 → 7 fog, or the lip 7 inner face, by about 3 luma at 200 only, keeping the near sheet ≤ 36. Target APL ≥ 35.

**S1 should: the forward sleeve at 226-231 still matches the coda.**
- Use the r08 S1 fix: fibre peaks at 170-200 in #C2D8E2, densest at the frame edges, a 6° clear disc around the dot, and 2-3 parallax layers of long arcs.
- Check by diffing 228 against 240 (it should be > 5 luma mean).

**S2 should: the 226 side window is still one flat column with the centre line (39.1).**
- Use the r08 N2 plies at +8-12 luma, and remove the vertical line at x ≈ 480.

**S3 should:** give lip 3 at 181 a darker mass behind it (cloth fog cap 0.85-0.9).
**N1 nit:** grow the glow +10 % from 240 to 246.4 and fade the ghost fibres. **N2 nit:** make the json measure the graded PNG.

## To pass r10
B2 must be verified with images at 197/200/205 and a fresh stranger test. B4 needs the APL of 200 in band. S1 is the biggest beauty gain left.
