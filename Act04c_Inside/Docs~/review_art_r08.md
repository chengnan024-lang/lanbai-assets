VERDICT: FAIL

# Art review r08 · Act 4c "门内" (independent, 2026-10-23)
I looked at iterations/08_resume/*.png next to 06_review5, the metrics json, measure_r07.md, stranger_tests.md and the r07/r08 notes. Luma is Rec.709, sampled from the graded 960x540 PNGs. The bus shell, frame and pillar are placeholders and are not judged. The constraints are respected throughout: 40 m clearance, fixed H and times, lip 8 is the only planned framer, and no cloth edge is inside the forward frame from 226 to 231.

## Beauty first
- **197** is now the best frame in the act. The rain streak is gone, the nearest sheet sits darker than the one behind it (38-40 vs 51), and the dot has a soft halo instead of a sticker.
- **205** is calmer, with one ring instead of three. But it is now a big round hole with the dot near its centre, which reads as a porthole or a moon in a cave mouth.
- **218.75** still has real depth.
- **226** still reads as a striated wall: no second or third ply, and the centre line is unchanged.
- **228 and 231 forward** are almost the same picture as 240 and 246.4: a grey fog card, the dot and a few faint hairs. In the forward view, the climax (the sleeve) and the coda are the same image for about 22 s. The new fibres peak at luma 107-112, so they read as scratches on the glass, not as fibre pulled out of thick cloth.

## r06 findings
| # | r06 finding | r08 | evidence |
|---|---|---|---|
| B1 | 205 target / portal | partly | Lip 8 is delayed, so the concentric target is gone. The dot is still about 11 % (x) and 29 % (y) of half-size from lip 7's visible hole centre, so lip 7 frames the dot, and the bible gives that job to lip 8 alone. The 200 and 210 frames I asked for were not delivered. |
| B2 | one cloth-only cue | partly | (a) 197 near sheet 48 -> 38-40, ordering now correct, target 30-36. (b) Curl/back-face band: not done. (c) Folds at 0.08 H, +-25 %: not visible. Flat cloth regions have sd 0.4-0.7 luma on a mean of about 38 (about +-2 %). Sag withdrawn: accepted, the straight lines are the window. (d) Streak: fixed. No stranger test since r06. |
| S1 | dot hierarchy / glow | fixed | The 240 profile falls 238 -> 148 -> 106 at 0/30/60 px with no hard edge. The dot holds 100 % of the brightest 2000 px from 228 on. Before LIP 8 (197/205) its share is still 1 %; accepted, because the fibres must stay at 200+. |
| S2 | fibre gate | partly | PNG brightest-2000 min is 197.2 / 196.7 / 195.5 / 198.4 (181/197/205/226). The json says 210-216 (N4). |
| S3 | 218.75 flap rim | partly | Flap rim max 105 -> 146 (p99 124). Target is >= 200. The body is still a 56-luma silhouette. |
| S4 | 181 lip 3 drawn crack | open | Inside 38 vs outside 34: no darker mass behind the line. |
| N1 | coda breath | open | APL 240 -> 246.4 is +1.2 %. The glow profile is identical. The ghost fibres are still stronger at 246.4. |
| N2 | 226 centre line / plies | open | Unchanged. |
| N3 | cabin wall | open | Placeholder; deferred. |
| N4 | metrics disagree | open | The json min_luma is still not the PNG value. |

## Remaining findings
**B1 blocking: lip 7 frames the dot at 205.**
- Fix: either move lip 7's opening centre (H unchanged) so the dot sits at >= 60 % of the hole's half-width, toward the right or the top rim, or run lip 7's tear out to the sheet edge so that it becomes an open slit with no closed ring.
- Deliver 200, 205 and 210. No opening may hold the dot within 25 % of its centre until lip 8.

**B2 blocking: there is still no cloth-only cue on screen.**
- (1) Folds: what renders now is about +-2 %. The 0.08 H fold term is being averaged out, by mip/fog or because it is applied before the fog blend. Apply it after the fog, as a shading term on the cloth only, so that a flat region at 197 shows sd >= 4 luma with 3-6 visible folds per sheet.
- (2) Do the curl: on 10-20 % of each edge, add a 0.3-0.6 % H back-face band, 8-12 luma darker, behind the rim.
- (3) Bring the 197 near sheet to <= 36.
- (4) Rerun the stranger test at 197/205/226. It must name cloth, curtains or fabric, with no portal or tunnel.

**B3 blocking: 226 side APL is 38.4 against a 48.6 target, which is -21 % and outside the bible's +-15 % band.** This is a regression from r07e's air x0.75 (r06 was 42.7).
- Fix without touching the forward fog: add N2's 2nd and 3rd plies at +8-12 luma over the ply behind them, with vertical striations, and lift the sleeve's inner cloth face by about 8 luma. Target APL >= 42.

**S1 should: 228/231 forward needs a sleeve of its own, made of fibres only.**
- Fibre peaks go from 107-112 to 170-200, in the #C2D8E2 hue. They are densest at the left, right and top edges of the frame, where the walls are just out of view, and thin out toward the centre.
- Keep a clear 6-deg disc around the dot so that it stays the brightest mass.
- Orient the fibres as long arcs streaming from the frame edges back past the camera, in 2-3 depth layers with parallax drift. Read it this way: the cloth is just beyond the edges and its fibres reach in.
- Optional, only if the bible counts light as non-structure: let the fog darken 10-15 % toward the frame edges, as shadow from the walls. That also brings 228's +10 % APL back toward 49.

**S2 should:** take the 218.75 flap rim to >= 200 and add one fold (r06 S3). Give lip 3 at 181 a cloth fog cap of 0.85-0.9 (r06 S4).

**N1 nit:** grow the glow +10 % from 240 to 246.4, and fade the ghost fibres out by 246.4.
**N2 nit:** make the metrics json measure the delivered graded PNG (r06 N4).

## To pass r09
B1, B2 and B3 must be verified in the images at 200/205/210, 197 and 226, plus a fresh stranger test. S1 is the biggest remaining beauty gain.
