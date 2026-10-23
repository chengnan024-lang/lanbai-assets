VERDICT: CONDITIONAL PASS

# Art review r11 · Act 4c "门内" (independent, 2026-10-23)
I looked at all frames in iterations/11_drape next to 10_folds_across, at crop_197 / crop_205, and at my own 3× stretched crops of 197 (left sheet, lip around the dot) and 205 (right flank). Luma is Rec.709 from the PNGs. The bus shell, frame and pillar are not judged. The constraints hold: 40 m clearance, fixed H and times, the dot core is never occluded, in the sleeve no edge is in the forward frame, and the cloth base is unchanged.

## Beauty first
- **This is the best the sheets have looked.** On 197 / 205 the tear now has relief: soft ridges fan out from the lip with a lit flank and a shadow flank, so the sheet looks like a surface under tension rather than a painted wall. 197 / 200 are still the best pair in the act, and they are better than in r10.
- **Orientation is fixed.** On the near-vertical left edge of 197 the ridges now run horizontally (edge-normal), and on 205 they radiate around the arch. The 1-px vertical "brushed metal" streaks are down to a faint hatch.
- **New artefact: zigzag seams.** On the 197 left sheet (the lower half, x 60-200 / y 250-400) the fold field has hard staircase "Z" kinks wherever the nearest edge point jumps. They show in the author's crop_197 and are faint but visible at 1×.
- **The mottle is too regular.** The product of two sines reads as a quilted or hammered lattice on the inner lip around the dot (197 x 380-560 and 205 right flank), not as an uneven weave.
- **No cloth-only cue yet.** The same relief would fit eroded plaster, ice or rock: 218.75 and the 226 side window read as stone. There is no sag, hem or loose thread that only cloth has. Whether "torn" is enough goes to the director, as agreed in r10.

## r10 findings
| # | r10 finding | r11 | evidence |
|---|---|---|---|
| B2 | cloth does not read as cloth | **met on the images** | Ridges are edge-normal, about 0.016 H wide, with ±flanks. The weave streaks are at 1/3. Translucency is present but regular (see S4). There is no cloth-only cue. The stranger test result goes to the director together with this review. |
| S1 | sleeve fibres = windshield scratches | open | The 228 / 240 diff vs r10 is 0.01, so nothing changed. |
| S2 | 226 side window flat, line at x ≈ 480 | open | The line is still there. APL 39.5 → 39.4. |
| S3 | 181 lip 3 line | open | Diff 1.0, all from the cloth texture. Lip 3 has no dark mass behind it. |
| N1 | coda breath | open | 240 is unchanged. 246.4 was not rendered, and 231 is the r10 file. |
| N2 | json ≠ PNG | open | The json APL now matches (35.35 / 34.31 / 40.4). min_luma is still the bloom cluster. |
| N3 | §12 B4 rewrite | not checked | 200 APL 34.31 is unchanged and still accepted. |

## Remaining items
- **S4 should, before lock: remove the zigzag seams.** Blend the ridge direction from the 2-3 nearest edge points, or blur the gradient of the distance field (about 0.02 H) before you use it. Then re-crop 197 lower-left at 2×. No staircase may be visible.
- **S5 should: break the lattice.** Replace the two-sine product with value noise at about 0.03 H, or rotate each sine per sheet so no grid shows. Keep +4-6 luma.
- **S6 should: near-sheet mean.** On my mask (197, x 0-170, luma < 60) it measures 38.5 against r10's 36.7, which is over the ≤ 37 asked. Trim the translucency gain about 30 % on the near sheet only.
- **Optional cloth-only cue (only if the director rules "torn" is not enough):** a slight gravity sag between ridges at the top of each lip, or 2-3 hanging loose threads on 197's left edge. Do not iterate this before the ruling.
- **S1 / S2 / S3 / N1 / N2 / N3** carry over from r10 unchanged.

## Gate
No blockers remain. Fix S4 before the look locks. The cloth-read question is closed for art review and now sits with the director, together with the author's stranger-test result.
