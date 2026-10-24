VERDICT: FAIL

# Art review r06 · Act 4c "门内" (independent, 2026-10-23)
Looked at iterations/06_review5/*.png next to 05_cloth, the metrics json, lookdev_brief.md, review_art_r05.md and the r06 note. Luma values are Rec.709, sampled from the graded 960x540 PNGs. The bus shell, frame and pillar are placeholders and are not judged.

## Beauty first
This round is clearly better. 181 is now calm and readable: two lips, a dark cabin, crisp lit edges. It is the best opening frame so far.
218.75 has real depth now that the cobweb strands are gone. The coda finally has air, because the radial fog pulls the eye to the dot.
226 is quieter, since the rigging-like strands are broken and dim.
Two things still stop the act from reading "一层一层撕开的布": 205 is a target (rings round the dot), and the cloth is still a flat cut plane with rain-streak texture.
A stranger at 205 would say "portal" or "tunnel"; at 197 they would say "torn paper" or "cracked ice".

## r05 findings
| # | r05 finding | r06 | evidence |
|---|---|---|---|
| 1 | fibres too dark (min_luma >= 200) | partly | PNG brightest-2000 min is 194.8 / 194.4 / 193.4 / 196.3 (181/197/205/226), up from 125-145. The rim now reads as lit fibre. The json says 208-214 for the same frames (see N4). |
| 2 | cloth reads as a flat cut-out | partly | 181 near cloth is 30 (target ~31) and 205/218 cloth is 10-25 under its opening: good. But at 197 the nearest sheet is 40-55, lighter than the sheet behind it (40), with only ~51 in the slit. The folds (+-28 %), sag and curl/back-face are not visible in any frame. The vertical streak still reads as rain/wood grain at 197 and 218. |
| 3 | tunnel/cave (<= 3 lips, no concentric) | partly | 181 is fixed (2 lips, no hole-in-hole). 205 is unchanged from r05: lip 7's hole centre is about 15 % of its half-width from the dot, and lip 8's ring sits inside it, so three concentric shapes = target. |
| 4 | dot not the brightest mass after LIP4; glow 4->12 deg | open | Share of the brightest-2000 px on the dot: 197 1 %, 205 1 %, 218.75 18 %. Fibres x3 made this worse. Measured glow radius: 197/205 ~1.7 deg, 218.75 ~2.2 deg, 240/246.4 ~4 deg with a hard cutoff (brief: 4 deg at LIP4 -> 12 deg at 246.4). |
| 5 | lip 8 framing at 218.75 | partly | The strands are cut: big win. Lip 8 filling the frame is accepted (H and t are fixed), and the side walls plus top flap do enclose the dot. But the top flap (luma 56) is still an unlit dark silhouette with no rim, so it reads as a hanging rock. |
| 6 | coda grey card | fixed | Gradient is centre 85 -> edges 51/61; APL 51.6/52.2 vs 52.6/54.4. Ghost fibres are present. Still to do: N3. |
| 7 | 226 sleeve | partly | The strands are shorter and dimmer: good. The centre bright vertical line is unchanged, and no 2nd/3rd ply can be counted. The ply's striations are still horizontal. |
| 8 | dye progression | fixed | Lavender at lip 1 (purple_pct 0.33 %, only near lip 1); cyan-grey by 218. |
| 9 | APL | fixed | 32.3 / 39.0 / 43.2 / 52.0 / 42.7 / 51.6 / 52.2. Only 218.75 is +11.6 %, inside the 15 % band. |

## Findings
**B1 blocking: 205 is a target/portal.** Lip 8's ring is legal on its own (the bible lets it frame the dot), but at 205 it is drawn inside lip 7's hole, and both share a centre with the dot (all three centres within 25 % of lip 7's width).
The r06 note says the layout check holds "≥ 0.6 the whole time", but the image shows ~0.15. The check is measuring something other than what lands on screen.
Fix (pick one): (a) move lip 7's opening centre so the dot sits at >= 60 % of its half-width (it is not a fixed bible value; H is). Or (b) hold lip 8's fade-in until lip 7 is <= 3 s from crossing, so lip 8 never shows inside lip 7. Or (c) make lip 7's tear run to the sheet's edge (an open slit or flap, not a closed hole), so no ring exists.
Re-check in screen space at 200, 205 and 210: no two visible openings, nor an opening and the dot, may share a centre within 25 %.

**B2 blocking: the cloth still needs one cloth-only cue on screen.** Fix: (a) at 197, take the nearest sheet down to luma 30-36. It is the translucency band or the weave term lifting the whole face; limit the band to <= 3 % H from the edge. Nearest must be darkest.
(b) Make the r05 2(d) curl real: on 10-20 % of each lip, the edge turns toward the camera and shows a 0.3-0.6 % H back-face band that is 8-12 luma darker, behind the glowing rim.
(c) The folds must be visible at hero distance: the 0.02 H wavelength is too fine at 100-400 m. Use 0.06-0.12 H with +-25 % shading, and add the 3-5 % catenary sag to the top boundaries (the 197 top edges are still straight).
(d) Cut the streak further (0.12 still reads as rain at 197 left). Rotate it to follow the folds.

**S1 should: dot hierarchy and glow (r05 #4).** Extend the glow profile to the brief's radius (4 deg at LIP4 -> 12 deg at 246.4, smootherstep), with a long exp tail and no hard support edge. At 240 it reads as a frosted disc or sticker (luma 118 -> 84 inside 12 px).
After LIP4, make the inner ~2.4 deg (≈ 26 px at 960 w, 2000 px) a plateau at least 10 luma above the fibre p99.9 in the frame. If needed, clamp fibre peaks at 197/205 to 200-210.

**S2 should: close the fibre gate.** Fibre gain x1.04 lifts 193-196 to >= 200 (APL cost ~0.2). Do not widen the rim.

**S3 should: 218.75 top flap rim.** Give it the same frayed lit edge (luma >= 200) and a fold or two, so that no unlit silhouette remains.

**S4 should: 181 lip 3 reads as a drawn crack.** Its cloth has a fog cap of ~1, so only a glowing outline floats in the fog (inside 38 vs outside 36). Give the fading third lip a cloth fog cap of 0.85-0.9, so a faint darker mass sits behind the line.

**N1 nit: coda breath.** The glow grows +3 % from 240 to 246.4 (asked +10 %). The ghost fibres are stronger at 246.4 than at 240; reverse that, so they are gone by 246.4.
**N2 nit: 226 centre line.** Accepted as a 0.3 s event. In this still, drop its luma by 30 %. Add 2nd/3rd plies at +8-12 luma, with vertical striations.
**N3 nit: coda right cabin wall** (53) is lighter than the cabin target #0C0E14. Placeholder; check once the real shell is in.
**N4 nit: metrics disagree.** The json brightest `min_luma` (208-214) is not the graded-PNG value (193-196). Make the harness measure the delivered 8-bit graded image, or state what it measures.

## To pass r07
B1 and B2 must be verified in the image at 197, 205 and 226. The stranger test at 197/205/226 must say "torn cloth / curtains" with no "portal" or "tunnel".
