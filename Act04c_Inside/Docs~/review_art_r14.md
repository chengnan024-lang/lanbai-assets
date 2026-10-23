VERDICT: FAIL

# Art review r14 · Act 4c "门内" (independent, 2026-10-23)
I looked at all 11 frames in 14_fray next to 13_hang, plus crop_197_lowerleft_3x. Luma is Rec.709 from the PNGs. The bus, frame and pillar are not judged. Constraints hold: the dot core is 238 at (425,236) on 197/200/205. 218.75-246.4 are unchanged from r13 (mean diff ≤ 0.007), and so is 226 side. I did not re-measure clearance.

## Beauty
- **197 is calm again and better than r12/r13.** The strands in the 3× crop are short, tapered, S-curved and fade out with no blunt end. This is the best the fringe has looked.
- **181:** the rain is gone. There are still about 6 tiny free-floating curls in the fog (x 140-330, y 180-350) and two glyph-like squiggles at the top (x 250-320, y 15-45) that are attached to nothing. They read as hair on the lens.
- **205 regressed.** The r13 fringe under the arch, the one frame where strangers *could* have seen cloth, is almost gone (max change 104 luma in x 230-600, y 140-320). The new 0.6-1.5 % H cap is far shorter than the r13 205 look (≈ 6 % frame height) that B2 named as the reference.
- APL is unchanged and still below the bible on 181 (29.0 vs 30.8), 197 (34.6 vs 39.2), 200 (33.8 vs 40.7), 205 (39.7 vs 42.7, < range) and 226 side (38.9 vs 48.6). This was already true before r14.

## Blockers from r13
- **B1, 200 side-window bar: FIXED.** The region max went from 196 to 42 luma, with no bar.
- **B2, icicle/rain on 197/181: FIXED.** Taper, S and fade-out are all visible. The 181 floaters are a new nit (N4), not a blocker.

## New blockers
- **B3, D-19 cloth read (0/16 cloth, 14/16 rock/ice).** No stranger mentioned the strands. Three rounds of strand work (r12-r14) cannot move this score, because the read is decided by the sheets.
- **B4, restore the 205 fringe** to the r13 length on far lips. Cap length by distance, not by % H.

## Why strangers say rock or ice
1. **The edges are thick.** The rim is a wide rounded bevel that glows like a lit surface, plus a 2.2 % H curl. Thickness and volume say stone lip or ice shelf. Torn cloth has an edge you can barely see.
2. **The sheets ignore gravity.** Every sheet is rigid and flat, with no drape, sag or fold in its silhouette (sag is sub-pixel past 200). The near sheet on 205 and the 226 side are lumpy vertical columns with horizontal relief, so they read as a "rock pillar" or "ice column".
3. **The tears look like fractures.** The contours are isotropic and fractal-jagged, and on 218.75 the secondary tear lines inside the sheet form a crack network. Woven cloth tears along the grain, in long runs with stepped corners and a perpendicular fringe.

## One change (highest leverage)
**Let the opening's silhouette obey gravity.** On each lip, turn the upper edge into 2-4 torn flaps that hang straight down, each a tongue with vertical folds. Let the side edges fall in vertical folds whose rim undulates in depth: rim glow brightens where a fold turns toward the light and drops where it turns away, and there is no constant-width bevel.
- Flaps hang only from the top edge, so they stay above the 40 m clearance envelope.
- Keep them off the LIP4+ dot ray (the existing rule: core radius + 10 m).
- H and timings are not touched.
- Then re-run the stranger test on 205 and 226 side before doing any more strand work.

## Should / nit
- **S9:** thin the rim bevel to ≤ 0.3 % H. It goes with the change above.
- **N4:** cull the 181 floaters and squiggles that do not touch a rim.
- **S1 / S2** (the 226 side x ≈ 480 line is still there) / **S3 / S7 / S8 / N1-N3** carry over.
