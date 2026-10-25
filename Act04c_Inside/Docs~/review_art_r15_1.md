VERDICT: FAIL

# Art review r15.1 · Act 4c "门内" (independent, 2026-10-24)
Scope: only the director's r15.1 acceptance. That means no faces, skulls, castle walls/crenellations or regular stairs, no regression of the dot, and 197 must still read as cloth as it did in r15. Cloth in general is not judged, and B8 is accepted. I compared 16_silhouettes against 15_tongues at 1x and in 2-3x crops, plus pixel diffs and Rec.709 luma. 218.75, 226, 226 side, 228, 240 and 246.4 are identical to r15 (mean |Δ| ≤ 0.01), so the only frames that changed are 181, 197, 200 and 205.

## Blockers from r15
- **B5, faces. PARTLY FIXED.**
  - 200: **FIXED.** The skull tongue (x 40-180, y 0-140) has been removed entirely, and so has its mirror in the side window (x 790-900). Nothing replaced them.
  - 181 tongue: **FIXED.** The new near-sheet tongue (x 215-330, y 15-150) is a broad wedge with a W tip and does not read as a head.
  - 181 face: **still in the hero frame.** The grey head profile at x 50-175, y 145-360 (brow ≈ (150,185), nose ≈ (175,265), chin ≈ (145,310), neck down to 360) is unchanged, with a max pixel Δ of 6 against r15. It still reads clearly as a face.
  - Do I agree it is the glass reflecting lip 1? **Probably, but it is not proven.** For it: it has no rim glow, it is flat grey, it is absent without glass, and it stayed pixel-identical while every tongue changed.
  - However, `181.0_hero_noglass.png` is **not the same frame**. It is 640x360 and its geometry differs. The near tongue is narrow and long (≈ x 240-300, y 0-185 at 960 scale, ~3x its width, which breaks the new rule). The left sheet edge is different. Lip 2 at x 410-500, y 140-170 has two extra hanging notches. Re-render it from the identical build at 960x540 before using it as evidence.
- **B6, regular stairs. NOT FIXED.**
  - Right near sheet: the upper part (y 0-300) is smoother now. The lower half, x 815-845, y 300-530, is essentially the r15 edge. Its sawtooth teeth sit at y ≈ 322 / 355 / 401 / 445 / 473, a pitch of 28-46 px (≈1.6:1, where the target is ≥3:1). Each tooth has a dark corner blotch and horizontal banding, so it still reads as stacked slate or stairs.
  - Left near sheet, x 0-190, y 180-450: improved, with mixed step sizes. However, the diagonal still carries small stair notches roughly every 16-21 px between y 180 and 280, and a dark blotch at ≈ (60,215). The promised "plain torn line on diagonal stretches" is not visible here.
- **B7, crenellation at 205. FIXED as a crenellation, but replaced by fangs (N1).** The square stub at x 265-300, y 205-250 is gone, and no square-cornered tongue remains anywhere.

## New readings, frame by frame
- **N1, 205, teeth / fanged mouth (blocker).** Two pointed tongues now hang into the arch on either side of the dot.
  - Tongue A: x 262-312, tip at (292,274). Its right edge is a ruler-straight vertical at x ≈ 295, y 206-274.
  - Tongue B: x 430-466, y 136-198, with a two-point tip at (438,198). Its left edge is ruler-straight vertical at x ≈ 432. Its length is ≈ 1.8x its width, which breaks the ≤ 1.6x rule.
  - With the round dark opening, the pair reads as the upper canines of an open mouth, with the dot as the throat light. Each tongue alone reads as a fang or stalactite. This is worse than the crenellation it replaces.
- **N2, 200, single fang (minor).** A new tongue at x 453-472, y 190-228, about 30 px from the dot, has a vertical left edge and a narrow V. It is ≈ 2x its width, which breaks the ≤ 1.6x rule. Left of the pillar, the lip-2 sliver (x 340-382, y 198-272) is now a long point with a vertical edge, and it reads as a stalactite. It is mostly hidden by the near sheet.
- **N3, 181, molar (minor).** The new tongue's W tip at (240-290, 130-150), on a block with a straight left edge, can read as an upturned two-cusp tooth. It is not a face.
- **N4, 197, hook (minor).** The thin hooked fringe at x 523-552, y 72-108, right of the tongue, reads as a small fang or hook. It is stable across the strip.
- **Pattern.** Every new tongue (181 x ≈ 220, 197 x ≈ 523, 200 x ≈ 453, 205 x ≈ 295 / 432) has one ruler-straight vertical side and one diagonal side. That cut-blade geometry is what produces the fang read. The brief asked for asymmetric tapers, not one axis-aligned edge.
- **Not seen:** skulls, animals or castle walls. 218.75 still has its r15 stalactite top (x 400-560) and spike, unchanged. That is not new, but it remains open.

## Dot
**No regression.** The core is unchanged everywhere (237.6-239.6, RGB ≈ 251/236/215), and the 8-30 px ring matches r15 to within 0.1. No tongue enters the 30 px ring. The nearest are the 200 fang (≈ 30 px) and the 205 fang B (≈ 40 px above).

## 197 and the strip: cloth read
- **Weaker than r15. Conditional.**
  - The tongue that carried r15's cloth read is gone: the left near-sheet tongue at x 290-360, which had a pleat seam and a stepped tip.
  - The new 197 tongue hangs into lip 2 at x 418-523, y 25-157, with a ratio of ≈ 1.26.
  - It has faint full-length vertical pleats, a slanted two-point torn end and the swing curls. It still reads as a hanging flap or banner, but it is flatter and more cut-paper/shield-like than r15. The cause is the ruler-straight right edge at x ≈ 520, y 35-145.
  - Four dark square specks remain on it, at ≈ (435,58), (515,45), (457,115) and (513,110). They are small "mottle", which the brief said was removed.
  - The new left sheet edge (x 140-330) is a soft draped fold and reads as cloth.
- **Strip, 8 tiles.** The tongue is stable and grows smoothly with no pops. The mean frame Δ is 4.8-6.1, and 8.5-11.7 on the tongue region. It reads as the same flap throughout.

## 181: glass reflection and harness question
- **Source.** I agree it is most likely the preview glass reflecting lip 1's gate tear, for the reasons under B5. The noglass frame does not prove it, because it comes from a different geometry state.
- **Does it still read as a face?** Yes, clearly, as a human head profile facing right.
- **Is it a harness artifact?** Only partly. In Built-in RP the glass reflects a reflection-probe cubemap, not live geometry, so the moving lip will not reflect the way the preview raytraces it. But if the bus probe is baked or realtime with lip 1 in view, a static, mirrored version of the same tear can still show in the glass, view-dependent in the headset.
- **Also check lip 1 itself.** The tear's outline is the face. Lip 1 seen *directly* (before or at the gate) may read as a head profile too.
- **Before calling B5 closed:** check the headset or Unity Game view at 181 with the real glass and probe, and check lip 1 in direct view.

## APL (r15 → r15.1)
181 28.8 → 28.8 · 197 34.2 → 34.0 · 200 35.9 → 33.9 (because the tongue was removed) · 205 39.7 → 40.0 · all other frames unchanged.

## Required for r15.2
1. Remove the axis-aligned straight side from all tongues, so that both sides taper and lean.
2. At 205, keep at most one tongue in the arch, kept off the dot's left/right symmetry, with no point. Or remove both tongues.
3. Apply the B6 rule to the right near sheet's lower half (x 815-845, y 300-530) and the left diagonal (y 180-280). Remove the dark corner blotches.
4. Enforce the ≤ 1.6x rule at 200 (453-472) and 205 (fang B).
5. Remove the specks on the 197 tongue.
6. Re-render noglass at 960x540 from the same build, and verify the 181 reflection in Unity with the real probe.
