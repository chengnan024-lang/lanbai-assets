VERDICT: PASS (against the r15.2 acceptance only; follow-ups below are not gating)

# Art review r15.2 · Act 4c "门内" (independent, 2026-10-24)
Scope: only the director's r15.2 acceptance. That means no faces, skulls, teeth/fangs, castle walls/crenellations or regular stairs, and no regression of the dot against r15/r15.1. Cloth read is not judged (it moved to the headset test). The 181 left-window reflection is accepted and is not counted. I compared 17_r14_outlines against 16_silhouettes, 15_tongues and 14_fray at 1x and in 2-3x crops, with pixel diffs and Rec.709 luma.
- **Frames that changed:** only 181, 197, 200 and 205.
- **Frames that did not change:** 218.75, 226, 226 side, 228, 240 and 246.4 are pixel-identical to r15 and r15.1 (mean |Δ| ≤ 0.01, max ≤ 2). They differ from r14 (mean Δ 0.7-2.1, and 8.0 on 226 side).

## Frame by frame (face / skull / teeth / animal / castle / stairs)
- **181. Clean (apart from the accepted reflection).**
  - The near-sheet tongue and its W-tip "molar" (r15.1 N3) are gone.
  - The left near-sheet edge (x 0-275, y 5-165) is a plain torn diagonal with curls, no steps.
  - Lip 2 (x 405-610, y 60-415) is the r14 outline, and its bottom spike at (495-510, 335-390) reads as a mitten or spade, not a face.
  - The right sheet (x 590-700) and the side window are plain tears.
  - **Nothing else at 181 reads as a face.**
  - About the reflection, see "181 reflection: provenance" below.
- **197. Clean.**
  - The tongue (x 418-523), its ruler edge and specks, and the N4 hook at (523-552, 72-108) are all gone. The lip-2 right edge is a plain tear.
  - Low-risk, pre-existing r14 readings (not counted):
    - The left near-sheet notch at (200-215, 165-195) could be stretched into a "nose" on a coastline profile.
    - The lip-3 leaf with the dot at its upper left (x 390-555, y 205-365) could read faintly as an eye with a pupil.
- **200. Clean.**
  - The N2 fang (453-472, 190-228) is gone, and so is the long vertical-edged sliver at 340-382.
  - Lip 2 is back to r14's small curled hook at (340-382, 195-240), which reads as a curl, not a tooth.
  - The side-window sheet edge (x 860-960) is a wavy tear with no profile.
- **205. Clean.**
  - Both fangs are gone (N1).
  - The arch (x 170-610, y 128-420) is r14's. Its single rounded shoulder at (230-310, 150-215) is one step, not crenellation or stairs.
  - The left near sheet (x 0-140, y 210-450) is a smooth diagonal with no notches.
  - On the right near sheet, the r15.1 sawtooth at x 815-845, y 300-530 is gone. The edge is a wavy tear at x 830-885.
  - **Minor (not a blocker).** Five shallow nicks sit on the right near sheet at y ≈ 75 / 185 / 288 / 395 / 512 (x ≈ 875 / 862 / 855 / 848 / 840). The pitch is ≈ 105 px, so it is fairly regular. Each nick carries a 6-8 px dark square speck. It reads as a knuckled or riveted edge, not stairs: there are no horizontal treads. r14 had broad bulges here with no specks.
- **218.75. No new reading.** It is unchanged since r15. The r14 horizontal thorn (x 150-232, y 205-245) and the top lobe with one small step (≈ 530-545, 72-78) remain. A thorn or beak at most; it is not a face, teeth or stairs.
- **226, 226 side, 228, 240, 246.4. Clean.** These are plain fields and a plain hanging strip. On 226 side the strip edges (x 362-373 and x 653-685) have no steps.

## r15.1 items
- **N1 (205 fangs): GONE.**
- **N2 (200 fang and stalactite sliver): GONE.**
- **N3 (181 molar W-tip): GONE.**
- **N4 (197 hook): GONE.**
- **B6 (205 near-sheet stairs): GONE.**
  - Right: no sawtooth, no horizontal banding.
  - Left: no 16-21 px stair notches, and no blotch at (60,215).
  - The leftover dark specks are the minor point under 205 above.

## Dot
**No regression against r15 / r15.1.** I measured exactly the same values on all eight dot frames, to within 0.1.

| Frame | Core | RGB | 8-30 px ring |
|---|---|---|---|
| 197 | 237.6 | 251/236/214 | 59.4 |
| 205 | 237.7 | 251/236/216 | 67.3 |
| 240 | 239.6 | 252/238/219 | 130.9 |

Nothing enters the 30 px ring. The ring is still below r14 (197: 88 → 59; 240: 167 → 131). That is the B8 dim, which the director accepted, and it is unchanged.

## Regression against r14 from keeping the thin rim and pleats
- **Darker overall.**
  - APL is 0.6-1.3 below r14 everywhere: 181 29.0 → 27.8 (the lowest of any round), 197 34.6 → 33.3, 205 39.7 → 38.7, 218.75 50.8 → 49.8, 226 52.5 → 51.5.
  - The rim's p99.5 luma is 15-30 lower: 181 184 → 152, 205 191 → 173, 226 162 → 135.
  - 181 and 205 are further below the r15 targets (30.8 and 42.7).
  - This is not an acceptance item, but it should be checked in the headset.
- **Dark square specks that r14 did not have.**
  - 200 side window: (920,160), (918,300) and (905,450).
  - 205 right near sheet: the five specks listed under 205.
  - These are r15-era shading (pleats and rim modulation) and were already present in r15.1. They are small, but they are the only geometric "rhythm" left that could drift towards rivets or teeth.
- **226 side.** The bright strip is 15-25 px narrower and less wavy than r14 (right edge x 653-685, against r14's x 660-709). That is consistent with the thinner curl and introduces no stairs.

## 181 reflection: provenance (for the cabin team; not counted)
- The head profile (x 50-175, y 145-360) is **pixel-identical to r15.1** (max Δ 0).
- It is **not the r14 reflection**. In r14 that area is a blocky slab with a jaw notch, and its right edge sits ≈ 40-45 px further right (x ≈ 205-215 at y 195-285, against x ≈ 162-174 now). It reads much less as a head.
- If the glass reflects lip 1, then either lip 1 was **not** reverted to the r14 outline (5246e30), or the face shape comes from a kept r15 feature (most likely the drape pleats displacing lip 1, or the curl).
- Either way, the face in the window was introduced in r15 and is still there in r15.2. Before the headset test, confirm lip 1's geometry hash and render 181 with pleats off. The same check applies to 218.75 and later, which are byte-identical to r15: confirm whether those lips are the r14 outline.

## APL (r14 → r15.1 → r15.2)
| Frame | r14 | r15.1 | r15.2 |
|---|---|---|---|
| 181 | 29.0 | 28.6 | 27.8 |
| 197 | 34.6 | 33.8 | 33.3 |
| 200 | 33.8 | 33.6 | 33.7 |
| 205 | 39.7 | 39.9 | 38.7 |

218.75, 226, side, 228, 240 and 246.4 are the same as r15.

## Overall
**PASS.**
- No face, skull, teeth/fang, animal, castle/crenellation or regular stairs reading in any r15.2 frame, outside the accepted 181 reflection.
- The dot is unchanged against r15 and r15.1.

Non-gating follow-ups:
1. Remove the dark square specks (200 side window, 205 right near sheet).
2. Run the 181 lip-1 and pleats provenance check above.
3. In the headset, look at the APL and rim drop against r14.
