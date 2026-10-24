VERDICT: FAIL

# Art review r05 · Act 4c "门内" (independent, 2026-10-23)
Looked at: iterations/05_cloth/*.png against 04_fibres and 03_sleeve, the metrics json for each, lookdev_brief.md, review_art_r03.md and the r04/r05 notes.
The bus frame and the black A-pillar are placeholders and are not judged.
Luma values are Rec.709 samples from the 960x540 renders.

## Overall
r05 is a real step forward from r03. The sleeve side view (226) is now the best frame in the act. The torn edges now have
irregular, multi-scale contours and the black wall bars are gone. 181 is moody and quiet.
The forward frames 197/205/218.75, however, are almost identical to r04 (197 is pixel-for-pixel the same composition). The two core
blockers from r03 are still open: the fibres are too dark, and the cloth does not read as cloth.
The coda is still an empty grey card. A stranger would now say "torn paper or cave openings with a light at the end",
not "torn cloth / curtains".

## Findings
1. **blocking: the fibres are still far under the bible.** The brightest-2000 px `min_luma` is 136-161 in every frame
   (target 200-235). The rim at 181 samples at luma 68. The torn edge glows like a soft rim light, not like lit fibres.
   Fix: give the lip fibres their own emissive term, so that the peak fibre pixel reaches luma 210-230 at the nearest lip and
   about 200 by lip 8. Keep the rim 1-2 px wide at 1080p and let it fall off over 0.5% H so APL does not rise.
   Re-measure until brightest `min_luma` >= 200 at 181/197.
2. **blocking: the cloth face reads as a flat cut-out plane (paper/rock), not cloth.** At 197 the cloth (luma 52) is
   brighter than the opening next to it (46). At 181 cloth 29 vs opening 33 is almost no separation. The surface carries a uniform
   vertical streak texture that looks like rain on glass or wood grain. The ±12 % tension folds from r04 cannot be seen at
   any hero frame, and the top edges are straight lines.
   Fix: (a) the cloth face must be 12-20 luma darker than the fog in its own opening at every t (brief: inner face
   #1A2030), so lower the cloth's fog fraction rather than the fog. (b) Raise the fold amplitude to ±25-30 % shading,
   0.6-1.5 m wavelength, running from the tear outwards, and add a visible sag (a catenary dip of 3-5 % of span) on each sheet's
   upper boundary. (c) Cut the vertical streak texture to 30 % contrast and break it up with the weave direction following the folds.
   (d) Let 10-20 % of the lip length curl toward the camera, so that the back face shows a thin darker band behind the glowing edge (cloth has
   two sides, paper cut-outs don't).
3. **blocking: 181 and 205 still read as a tunnel/cave.** At 181 four or five openings nest inside one another, hole-in-hole,
   all left of centre (brief: ≤ 3 layers visible). At 205 the lip-6 and lip-7 rings wrap almost concentrically around the dot.
   The r04 "alternate left/right, ≥ 60 % off-centre" rule is not visible on screen.
   Fix: at 181, fog lips 4+ out completely (fog density ×1.5 beyond lip 3, or cull them), so that only lips 2-3 and a hint of 4
   read. At 205, shift lip 7's opening centre by ≥ 40 % of its width away from the dot (dot near one edge of the hole,
   not in the middle). Then check in the image, not the solver, that no two visible openings share a centre within 25 %.
4. **should: the dot is the destination at 197 and 218.75, but it is not the brightest mass after LIP4.** The brightest centroid
   is at az −11.5° at 197 and +10.8° at 205, which is the fibres, not the dot at −6.5°/+4°. The core 0.3° is only a few pixels,
   so the glow must carry the "2000 brightest px". Fix: make the glow radius a ramp of 4° at 197 → 8° at 218 → 12° at
   240, as the brief asks. It is about 3° now (≈ 30 px at 960 w). Put glow luma at 4° ≈ 170, and keep its colour at (240, 225, 205).
5. **should: lip 8 does not frame the dot at 218.75.** The dot floats in a wide empty fog field with walls left and right. The
   dark mass at the top centre reads as a hanging rock or stalactite, not as a cloth edge. The long draped strands on the right read as
   cobweb or cracked ice. Fix: close lip 8's opening to about 35-45 % of the frame width, so that its torn rim encloses the
   dot on at least three sides with the dot in the upper third of the hole. Give the top hanging edge the same frayed glowing rim and
   folds as the other edges (no unlit dark silhouettes anywhere). Cut the long strands to ≤ 8 per lip and make them hang
   (vertical-ish catenaries), not criss-cross.
6. **should: the coda (240, 246.4) is a flat grey card.** The fog samples at luma 74 (edge) to 86 (centre), which is almost uniform. APL is 63 vs a target of 53.
   The two frames are identical. The r05 note calls APL and fog colour a "conflict", but that only holds if the fog is uniform.
   Fix: use a radial gradient centred on the dot. Keep the centre (within 10°) at #53606E (luma ≈ 94, which is where the brief
   measures it, "正前方"). Fall off to luma 45-55 at the window edges and 35-40 at the floor/top. This brings APL to about 53 and
   adds the depth that is missing. Add one or two very faint ghost fibres of lip 8 drifting off the frame edges at 240 (gone by
   246.4). Let the dot glow grow slightly between 240 and 246.4 (+10 %), so the "stillness before the flash" breathes rather than
   freezes.
7. **should: the 226 sleeve reads as a curtain wall but still not as "inside thick cloth".** The irregular frayed edge and the fine wall hairs
   work (big improvement on r03/r04). Three problems remain: the long diagonal strands crossing the window look like cables or rigging,
   the right-hand ply edge has horizontal striations that read as layered paper or wood grain, and the central vertical bright line is
   still in the frame. The note says it is real and lasts about 0.3 s, which is acceptable in motion, but it is the strongest line in
   the still. Fix: halve the length of the diagonal strands and drop their luma by 30 %. Make the striations follow
   the fold direction (mostly vertical) with ±40 % width variance. Add a 2nd and 3rd ply visible beyond the near ply, each 8-12
   luma lighter, so the eye counts thickness.
8. **nit: the dye progression is there but weak.** Lip 1 is lavender and the lips at 218 are cyan-grey, which reads correctly once item 1 restores the
   luma. Re-check `purple_pct` (0.2 % at 181) after the brightness fix.
9. **nit: APL in the forward frames is on target** (181 30.4, 197 39.1, 205 45.2, 218.75 53.9 vs 46.6, which is +16 %, just over). Fixing item 2 (darker
   cloth) will bring 218.75 in. 226 side is 46.2 (in range).

## To pass r06
Items 1-3 fixed and verified in the image. The brightest `min_luma` must be ≥ 200 in the pre-LIP4 frames, with the dot owning the brightest cluster after LIP4.
The coda needs a visible gradient (item 6). Stranger test at 197 and 226 must say "torn cloth / curtains".
