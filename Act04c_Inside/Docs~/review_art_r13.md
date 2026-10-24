VERDICT: FAIL

# Art review r13 · Act 4c "门内" (independent, 2026-10-23)
I looked at all 11 frames in iterations/13_hang next to 12_lock, with 2-3× crops of 197 (lower-left, upper lip), 200 (lip and side window) and 205 (arch). Luma is Rec.709 from the PNGs. The bus shell, frame and pillar are not judged. The constraints hold: the dot core is 238-240 on every dot frame, and the diff inside r ≤ 12 px of the dot vs r12 is ≤ 1, so nothing occludes it. 228-246.4 are pixel-identical to r12 (diff 0.02). I did not re-measure clearance; I trust the note (sag ≤ 80 % of margin, threads cut at clearance + 2 m).

## Beauty first
- **205 is the win of this round.** The fine fringe of short, faint, slightly angled threads under the arch frames the dot. It reads as frayed weave, and it is the first frame where the sheet is unmistakably cloth. 200's inner lip is similar and also good.
- **197 got busier and colder.** A row of 9 bright, straight, parallel strands hangs below the near sheet (x 10-190, y 340-460). They end blunt on the sill and read as a stalactite or icicle fringe. With more strands at the top (x 445-480, y 20-100) the hero frame loses the calm it had in r12.
- **181 now reads as rain.** Long vertical streaks hang under the top-left mass (x 20-180, y 110-280). The longest is about 125 px (23 % of frame height), far longer than the delicate fringe on 205.
- **Sag works only where it is near.** The scallops on 181's top-left underside read as cloth that hangs between pins. On 200 / 205 / 218.75 the arch outline is indistinguishable from r12, because 1.2 % H is sub-pixel at that distance.
- **Pleats: the strata are gone, without a drape read.** The vertical column high-pass on the far sheets rose from 0.13 to 0.28 luma on 200, and from 0.51 to 1.51 on the 197 lip. It is enough to kill the "rock layers" read, but too faint to say "curtain". This is acceptable, and it is better than ridges.

## Cloth / icicle / rain / crack read
- **Cloth:** yes on 205 and 200 (fringe), and on 181 (sag). It is undermined on 197 and 181 by the long strands.
- **Icicle:** yes on 197 lower-left. Luma along a strand is flat (153-165 from y 385 to 449, 6-8 px wide at 60 %). The strands have no taper, no S, and a blunt end, so they read as ice, which is exactly what D-19 tries to avoid.
- **Rain:** yes on 181, from long uniform verticals spread over the whole sheet. It is mild on 197's top strands, which start at the window head with no visible attachment.
- **Crack:** a minor risk where strands start inside the lit sheet and cross the glowing rim (197 x ≈ 180, y 335; 205 left arch). Over cloth they read as scratches in a surface.

## Regression check
- **APL:** all within ±0.7 of r12 (181 29.5, 197 35.2, 200 34.2, 205 39.8, 218.75 50.8, 226 52.5, side 38.9). 181 < 30 and 205 < 42 are still below range, but this is pre-existing and not caused by r13. The S6 near-sheet mean is 31.0 (r12 31.1).
- **Dot dominance:** held. Brightest-cluster counts went up (197 35 → 40, 200 42 → 49) because of the strands, but no strand gets near the dot's L*. Watch 197, where the strands at luma 160-200 compete with the dot in the left half.
- **New artefact, 200 side window (x 830-860, y 15-195):** one near strand renders as a rigid 5-6 px bar at luma 195 with square ends, attached to nothing. It reads as a fluorescent tube or a scratch on the glass. This is the worst object in the act.

## Blockers
- **B1: the 200 side-window bar.** Clamp a strand's screen width to ≤ 1.5 px (fade its alpha instead of widening it), or cull strands closer than about 15 m to the eye. Re-render 200 and 205 side.
- **B2: icicle/rain read on 197 and 181.** Taper each strand (full width at the root, 30 % at the tip). Vary luma 40-100 % along the length, starting bright at the root and fading out with no blunt end. Make the S visible (amplitude ≥ 2 strand widths). Cap the on-screen length by the 205 look (≤ about 6 % frame height), and keep ≤ 5 long strands per lip. Use the 205 fringe as the reference. Re-crop 197 lower-left at 3×.

## Should / nit
- **S7:** raise sag depth toward the clearance limit on lips 4-8 so it registers past 200. Otherwise accept that sag is only a near cue.
- **S8:** start strands at the rim, not inside the lit sheet, so none crosses the glow.
- **S1 / S2** (the 226 side x ≈ 480 line is still visible) / **S3 / N1 / N2 / N3** carry over unchanged.
