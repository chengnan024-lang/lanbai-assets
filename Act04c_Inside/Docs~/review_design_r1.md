# 设计评审 r1（2026-10-22，三份独立评审：美术 art、技术 / VR tech、圣经逐条 bible）

评审只拿到圣经、设计稿 v1 和仓库，没拿到我的结论。阻断 / 重大的条目另有对抗式核查（多数因额度中断，只完成 4 条）。处理结果写在 `DESIGN_4c.md` v2。

## [art / blocker] The lip-8 sleeve, built from 12 near-identical glowing rings, reads as a stargate ring tunnel and strobes at about 2 Hz
DESIGN §4 builds the sleeve from 12 laminae, each 6.5–8 m behind the last. Every lamina uses the same broken-hole outline, jittered by only ±6 m and ±7°, and every one has its own 瓶覗 lip glow and fringe at ×0.8–1.0. The car crosses them at 12.4–15.5 m/s, so a bright rim passes about every 0.47 s (≈2.1 Hz). The rims sit 40–90 m from the eye and are 3–10° thick. In any 4.4° region near abeam this is a periodic bright/dark pair at more than 2 per second, which breaks §1.8 (at most 2 flashes in any 1 s). §1.8 also names FLASH_TEAR as the only authorised flash. Visually, a stack of similar glowing rings marching past is exactly the 'stargate / near-death tunnel' that §6·4c bans in its 要避免 list. The rule 'centroid drift ≥ 10 m over 85 m' does not stop this, because drift in the eye's direction is under 7°. §6·4c and §8.1 #15 describe the sleeve as 'a very thick layer of cloth' with an irregular, fibrous wall: one tear through thick cloth, not a corridor of rims.

**建议**：Only the entry lip and the exit lip glow at full fibre strength. The inner laminae are dark #1A2030 cross-sections with sparse, non-periodic fibre glints (≤15% of lip intensity, no continuous rim). Use 4–6 delaminating sheets at random spacing, not 12, and let some be partial (torn flaps that do not close the ring). Change the outline substantially through the depth: the aperture narrows by about 25% toward the middle and its centroid moves ≥ 20 m. Before signing off, run lens_tech/flashcheck.py on a 224–232 s abeam sequence and require PASS.

**核查**（refuted = False）：I could not refute the claim. It holds up against the design and the bible, with two small citation slips.

Design facts (DESIGN_4c.md §4, line 52):
- The sleeve is 12 laminae spaced 6.5–8 m apart over 85.5 m.
- Every lamina uses the same broken-hole outline, jittered by only ±6 m and ±7°.
- Every lamina has its own lip glow and fringe in #C2D8E2 at ×0.8–1.0 (line 53).
- The bible (§6·4c) puts lips and fibres at luma 200–235. The gaps are dark #1A2030 (about luma 30).

Why it strobes:
- At a fixed spot in the view, the time between rims is spacing ÷ speed. That gives 12.4–15.5 m/s ÷ 6.5–8 m ≈ 1.6–2.4 Hz, and it does not depend on how far away the rim is.
- Looking out to the side, a rim 40 m away moves at about 20°/s. Rims there are about 10° apart and 3–10° thick (the lip is 1.2% of H, about 2.3 m; the fringe is 1–4% of H, up to about 8 m).
- So one 4.4° patch of view sees fully contrasted bright/dark pairs, and the darker state is far below 0.80.
- Fog at 0.0035 over 40–90 m only lets about 81% through, so it barely softens this.
- The result is about 2 or more flashes per second for the whole 6.25 s crossing. That breaks the §1.8 limit of at most 2 flashes in any 1 s (line ~225), a rule the bible says has no exceptions.
- §1.8 and §6·5 also say FLASH_TEAR is the only authorised flash in the whole piece.
- The bible's own screenshot protocol (b), 99–368 s with one look at the car door, already covers this abeam case, so flashcheck would catch it.

Why it reads as a stargate

## [art / blocker] Lips 7–8 cannot meet clearance, offset range and dot-off-centre together, so the solver will collapse them to concentric
§6·4c fixes H at 285 (lip 7) and 195 (lip 8). It also requires offsets of ±40–180 lateral and ±30–120 vertical, and the path ≥ 40 m from every edge. Lip 8 hole: radius 68–93 m (0.7–0.95 H/2). Subtract the 40 m clearance, fringe up to 4% H (8 m) and the sleeve's ±6 m jitter, and the maximum offset is about 39 m. The table's (+40, +30) offset is 50 m, and the minimum allowed (|x|≥40, |y|≥30) is also 50 m, so the constraints have no solution. Lip 7: the triangular mouth of the fork is 157–177 m wide, so its inradius is about 49 m. The path has to sit almost exactly at the incentre, but DESIGN also asks for an offset of (+45, −35) and for the dot to be ≥ 45% of the half-width off-centre. Those cannot all hold. A solver that 'reports an error and does no hand-tuning' will fail, or someone will shrink the offsets. Either way the last lips end up centred on the path and on the dot, which is the concentric tunnel the bible forbids.

**建议**：Write to 给总控.md now and ask for a bible amendment for lips 6–8. §1.8's own law at 15–26 m/s gives v/1.05+5 = 19–30 m, so set the clearance floor to max(25 m, v/1.05+5) instead of a flat 40 m. That leaves room for ≥ 40–50 m offsets. Alternatively, raise lip 8's opening to about 0.95 H with its long axis horizontal. Fix the table values so the starting point is feasible, and have inside_layout.py print per-lip slack so infeasibility is visible during design, not at build.

**核查**（refuted = True）：The claim is half right. The lip 8 part holds. The lip 7 part, and the headline that lips 7–8 will collapse to concentric, do not.

LIP8 (holds). The bible (§6·4c l.1001) and DESIGN §2 both require |x|≥40 and |y|≥30, so the offset is at least 50 m. The clearance is max(40, v/1.05+5), which is 40 m at 15.5→12.4 m/s, measured to the fringe tip. DESIGN's own fringe is up to 4% H, about 7.8 m, so the path needs a disk of about 47.8 m. The sleeve jitters ±6 m per layer, and its centroid must drift ≥10 m through the depth (DESIGN §4), so allow about 53 m. The sleeve uses the 破洞 outline (§2): max diameter 0.85–0.95 H (≤185 m), min 0.7 H (136.5 m), with petal tips pointing inward. Take the best case, an ellipse with a=92.5 and b=68. Moving along the major axis, the clearance falls to 53 m at about 39 m from the middle. So 50 m is out of reach if 'centre' means the visual/geometric centre, which matches the reviewer's ~39 m. Putting the major axis horizontal (the proposed alternative) makes it worse, because the vertical ≥30 m then sits on the 68 m minor axis. DESIGN also contradicts itself on lip 8. §2 says the edges are "在 8° 以内" around the dot 6 s before the crossing. At about 100 m away that puts the edges within about 14 m of the dot ray, which runs about 4 m from the path, so it cannot coexist with ≥40 m clearance. §4 says "≥ 8°" instead.

LIP7 (does not hold). 0.55–0.62 H (157–177 m) is the width of the fork's triangular mouth, not its side. The fork is 285 m tall, so the mouth

## [art / major] U9 entry seam: what the gate does after U9 is undefined
(1) Lip 1 is the gate's own tear (DESIGN §2), and InsideRoot slows down from U9. Gate README §2 defines GateRoot only for t ≤ U9 (constant 59.0164 m/s). If the gate keeps moving at that speed, the wound you just came through slides away from lip 1's sheet. (2) The portal only discards Inside fragments while the eye is in front of the tear plane. Nothing discards Gate content beyond the plane once you are inside: the cloud deck at y = −150, the shafts, the halo and any arms within 2.4 km will draw in front of InsideDome inside the cloth world. Looking back, the white Tear_Lens and halo cards are seen from behind and fill lip 1's aperture with white. That aperture should frame the night and the tentacles. (3) Fog density goes from 0.0006 (gate) to 0.0035 (inside). DESIGN does not say whether this is RenderSettings or per-shader. As written it is a hard switch, which §1.6 forbids except under occlusion. (4) In the same second come the white→dark drop on crossing, the tube flash (§6.x #12) and the first slice at 180.15. The slice is a 0.9 m Gaussian moving about 8 m/s, so it makes a ~0.2 s local pulse. That puts the window at the 2-flash limit.

**建议**：State in DESIGN that from U9 GateRoot.z = −s(t), using the same s as InsideRoot, so the gate and lip 1 stay welded; this is a request to 总控 or the gate session. Add a mirror portal (_Udon_InsidePortal used the other way round): Gate shaders discard fragments with world z > plane once the eye has crossed. Tear lens, halo and shafts use Cull Back or are discarded from inside. Keep only what is behind lip 1 enabled; everything else can be disabled while occluded by lip 1's opaque sheet, which also saves most of the gate's 7.1 ms. Inside shaders compute their own 0.0035 fog through LanbaiFog so the gate's fog never changes. Render the 178.5–181.5 s frames from the hero seat, looking forward and looking back, and flashcheck that window.

**核查**（refuted = False）：The claim is substantially correct. I found one factual slip in it.

(1) Confirmed. GateLayout_v2.json timeline.GateRoot_z reads "gate_z(t) = 59.0164*(179.55 - t) for t <= U9". h_bus and tear_H_knots also stop at U9, and Gate README §2 matches. DESIGN §1 gives s(t) for t < U9 at gate speed and InsideRoot = (0,0,-s(t)) after U9, but it never says what GateRoot (or Tear_Root, H, the grips) does after U9. Lip 1 is Inside's own mesh at s=0 on InsideRoot (DESIGN §2 row 1, which follows tear_def). If GateRoot keeps moving at 59 m/s while v(t) eases down, the gate wound drifts behind lip 1. Bible §6·4c needs this seam to hold: "回头：触手伸进第一道光唇就停住，指尖卷回去" (looking back, the tentacles stop at the first lip and curl back). DESIGN does not cover that look-back beat at all.

(2) Mostly confirmed. DESIGN §3 says the portal discards only Inside fragments, and it says plainly that "门里 2.4 km 内的东西照常画在它前面" (gate content within 2.4 km draws in front of the dome as usual). Nothing discards gate content past the plane after the eye crosses. The gate cloud deck sits at world y = -h_bus(U9) = -150, under the bus, so it would show in the gaps between the opaque lip sheets. Tear_Lens is Cull Off (Tear README material table) and keeps writing depth through its prepass. No fade or renderer-off is defined for it at U9, and DESIGN §9 only turns off the tear light. Shafts are Cull Off, additive, and have no fade. So looking back, lip 1's aperture would be filled by the back of the lens and the shafts. The sl

## [art / major] The tentacles curling back at lip 1 are missing
§6·4c 构图, last bullet, and the U9 row of the table both say: 'look back: the tentacles reach into the first lip and stop; their fingertips curl back. They cannot follow in.' This is the Orpheus beat that closes act 4 and the only rear-view moment of 4c. DESIGN has no section, mesh, animation or camera for it.

**建议**：Add a section covering 2–3 Gate near/rear arms. Their tips reach the lip-1 rim at about U9+1…+4 s and curl back slowly (≤ 0.5°/s self motion, §1.2), lit only by the lip-1 fibre colour #E6E1F2 as a rim. Seen through the lip-1 aperture from the rear window, they never cross the plane. Coordinate the arm IDs and keys with Gate's JSON through 给总控.md, and add a 'rear' camera at about 183 s.

**核查**（refuted = False）：I could not refute the claim; it is correct. The bible asks for this beat twice. §6·4c 构图, last bullet (ART_BIBLE.md:1005): '回头：触手伸进第一道光唇就停住，指尖卷回去——它们跟不进来'. The §6·4c table, row I 喉 / U9 (line 1011): '回头：触手的指尖在第一道光唇前卷回去'. The same beat appears in lens_story.md:673 and in the v21 proposals. A grep of DESIGN_4c.md for 触手/回头/卷回/后窗/rear finds nothing. Its 10 sections cover only motion, the 8 lips, fog/dome/portal, the sleeve, the warm dot, cabin light, loose threads, act 5 and the skylight spot. The deliverables in §10 include no tentacle mesh, animation or rear camera. Gate does not cover the beat either. Its rear group (Rear_ArchA/B, Rear_Hand0-4) stands 0.66-2.2 km behind the bus. Its last key is the 'lean' at U9+2, and its rear camera is at U9-2 (177.55, Gate README:226/251). gate_z(t) is defined only for t <= U9 (JSON :26). No Gate arm reaches the lip-1 rim, and nothing animates after U9. DESIGN also never says what GateRoot does after U9. The world becomes InsideRoot = (0,0,-s(t)), the opaque InsideDome (r 2.4 km) writes depth, and the act-5 overlay turns R_Gate off only at 248.64. So the view out the rear window after U9 is undefined, not just missing the beat. The 'Orpheus' label is a reviewer gloss. The bible's Orpheus line (§6·4, line 927) belongs to Gate's U9 hand-closing. The 4c curl-back is still a required beat, so the claim stands at major.

## [art / major] The Lichtchen sits at the focus of expansion, giving 'light at the end of the tunnel', and the sleeve offset puts it on the wrong third
The dot is at az −2.0°, el +1.2°, essentially the vanishing point of a straight path. All lip motion radiates from it, and it grows to 12°: the near-death tunnel image §6·4c bans. In VR, 2° does not count as 'avoiding the centre'. Separately, DESIGN §4 says the dot sits upper-left inside the sleeve opening, but the sleeve offset (+40, +30) puts the opening centre right of and above the path. Since the dot is near the path direction, it appears lower-left of the opening centre.

**建议**：Move the dot to about az −8…−10°, el +4…+6°. It stays ahead and stays 'waiting for you', but is no longer the point the flow radiates from. Re-solve the sightline constraints with this direction. For the upper-left third, give lip 8 an offset of (+x, −y), e.g. (+45, −30), or pick a dot direction that is consistent with it. Verify with rendered frames at 218.75 and 224.0 from both hero eyes.

## [art / major] The lips risk a 'neon outline on a black cutout' look, and the fringe is one texture tiled everywhere
The sheet is unlit #1A2030. The lip glow is only 0–1.2% H wide, which is 2.3 m on lip 8. The fringe is additive, uses one 2048×256 comb texture around every perimeter (lip 1 is about 2.5 km of edge, plus 12 sleeve laminae), and is widened to ≥ 1 px with fwidth but its alpha is not scaled by coverage. At distance this gives uniform bright 1-px wires that shimmer and repeat, which reads as Tron or vector art, not 'light walking in the threads' (§6·4c) or the dye thinning. §6·4 asks for ≥ 1 px widening with glow scaled by coverage; DESIGN does that only for the loose threads.

**建议**：Use two terms. Keep the sharp lip (0–1.2% H). Add a wide, faint translucency band (5–15% H, ≤ 15% of lip intensity, modulated by the fibre noise and fogged) so the cloth near the tear visibly thins and glows from inside. Scale fringe alpha by coverage. Ship 3 comb variants plus a world-noise bundle mask with a per-lip seed, and break the perimeter UV with random 3–15 m bundle gaps. Rotate the fibre grain with each lip's rotation around the path (warp/weft), not world-vertical, so the tear 'steps' follow the weave.

## [art / major] The 0.9 m Gaussian cabin slice reads as a scanner bar
DESIGN §6 sweeps a symmetric Gaussian slice, 0.9 m half-width, through the cabin in 1.2–2.1 s. Each seat lights and darkens within about 0.2–0.3 s: a photocopier or scanner bar, CG not grace. The §3.3 motif and §6·4c call for a soft band of light, with the slowing carried by the sweep. On lip 8, the light reaches the hero seat (z ≈ 2.05, near the front) at about 225.5 and the trailing edge reaches it at about 229.3. That is 3.8 s apart, not the '6 s between one rise and one fall' the bible describes, and the seat goes dark before the long *Leben* and the sleeve end at 231.0.

**建议**：Make the profile asymmetric. Use a soft leading edge (about 1.5 m) and a trailing exponential afterglow (3–4 m, i.e. 0.6–1.0 s at a fixed point), so it reads as light passing through a gap and lingering. Shape it by the windows (the slice enters through window and skylight apertures, not as a solid plane through the seats). For lip 8, time the out-sweep so the hero seat stays lit until about 230.3, or say explicitly that the 6 s figure is cabin-wide. Re-check the 180.15 slice against the U9 tube flash.

## [art / major] Act 5 flash has nothing bright to flood: +1.5 EV over grey fog
By 246.39 every lip is behind the car (DESIGN §8). The forward frame holds only #53606E fog, the dark cabin, the dial and the 12° dot. Raising exposure +1.5 EV on that frame gives a murky grey lift. It does not give §6·5's 'light floods the glass in one heartbeat', the palette's 'last frame of tear light #F5F2EC', or 'the last 0.3 s keeps the lip shapes bright … the eye draws its own afterimage'. DESIGN does not address the afterimage line or the #F5F2EC palette entry at all.

**建议**：Render 247.89–248.64 from the hero seat, looking forward and back, and report APL and clipped regions. Resolve with 总控/AD what the bright shape is: (a) the Lichtchen core and inner glow, which clip toward #F5F2EC under +1.5 EV (check its fill), plus the windscreen frame silhouetted against it; or (b) keep lip 8's exit rim in view (e.g. its rear rim seen through the skylight or rear window). Do not add anything in the frozen 1.5 s window. Specify the afterimage target frame.

## [art / major] Fog is a single global colour on a uniform dome: a flat void, and the dye thinning does not read spatially
DESIGN §3 gives one fog colour per zone, switched at each crossing (4 s smoothstep), and InsideDome is uniform. Every crossing re-tints all lips, near and far, ahead and behind, at once. The view backward is as pale as the view forward. There is no gradient anywhere, so the space reads as a CG void with no up/down or forward/back. The bible's idea that the dye thins lip by lip (§6·4c 染料越来越薄, §3.1 L1 → L6) should be visible in depth, paler ahead.

**建议**：Make the fog colour directional through LanbaiFog/LanbaiHorizon: forward (+Z, toward the dot) lerps toward the next zone's colour, backward toward the previous zones, with a gentle vertical term (darker below, ≤ 6–8 L*). Drive it continuously by s rather than in 7 steps. Optionally let the sheet's inner face thin a little too (#1A2030 → about #222A38 by lip 8), so the near cloth is not sooty against pale fog in segment III.

## [art / major] Loose threads converge on the bus, then freeze abruptly
DESIGN §7 has 90 threads drift toward the path axis (the bus) from 3–25 m. That is a swarm closing in on the viewer from every side: radial inward flow, menace rather than grace, close to §1.3.8 'nothing touches you'. At 246.39 their clock simply stops, so drifting threads halt dead mid-air. That stop is itself a visible change inside the 1.5 s stillness window that §1.8/§6·5 require.

**建议**：Read the bible's '慢漂向中心' as toward the far centre, ahead toward the dot. Threads drift mostly forward, 0.2–0.5 m/s in the bus frame, with only a slight convergence, and are respawned behind. Ease their drift speed to 0 with smoothstep over 4 s ending at 246.39, rather than stopping the clock.

## [art / major] The broken-hole shape (4–6 everted petals) invites a flower or anatomical reading
DESIGN §2 specifies 4–6 torn petals turned outward around a hole, with glowing rims. A radially symmetric everted ring of petals with a glowing lip is the same anatomical association §6·4c warns against with the almond, and it repeats on lips 4, 6 and all 12 sleeve laminae.

**建议**：Use 2–3 unequal flaps: one large flap hanging down along the warp, one small curl, and the rest ragged edge. No ≥ 4-fold radial arrangement; the inside_def check should reject angular symmetry above a threshold. Keep 'at least two corners pointing inward'.

## [art / minor] Weft threads and hanging broken threads are not in the clearance or speed checks
The 2–5 dark weft threads span the opening, and 1–2 broken ones hang into it. Nothing in §2 checks their distance to the path or the v ≤ 1.05·d law (§1.8). A hanging thread near the path at 59 m/s would whip past.

**建议**：Include the Threads geometry, including the hanging ends, in the clearance solver with the same max(40 m, v/1.05+5) rule, and restrict them to the narrow ends, away from the path.

## [art / minor] No per-segment acceptance frames or metrics from the hero seat
CONTROL §2.5 requires reference renders with APL, brightest-point position, purple share and ramp checks. §6·4c sets APL 30 → 55, one brightest point, and ≤ 3 lips visible. DESIGN lists none of the frames or numbers. It also never describes what the windscreen frame contains at any moment: the large lips 2–3 are mostly seen at their edges in the side windows and skylight.

**建议**：Add a camera table, e.g. 181, 185, 193.9, 197, 205, 218.75, 226, 232, 240, 246.4, 248.3, forward, plus rear at 183 and up at 186. For each, give target APL, brightest element, visible-lip count and where the next lip's edge crosses the windscreen. Use cameras.U7, and also check LB_Journey.heroEye.

## [art / minor] Dial extinguish time is inconsistent
DESIGN §6 says the dial goes out with the flash from 247.89, while §8 has it go out at 248.64 under the mask. §6·5 says it goes out during the flash.

**建议**：Choose one. Recommended: dim it over 247.89–248.64 together with the black mask, in step with ΔEV, so its dimming never reads as a separate event inside the flash.

## [tech / blocker] 入口门户只单向：车过平面后，门的世界在平面另一侧的部分漏进门内
DESIGN §3 只在相机还在平面前面时丢弃门内的片元。反方向没有对应的处理：相机过了平面以后，门里位于平面远侧（+z）的东西照样渲染。具体有：云顶在世界 y = −150（门 README §2：U9 后 h_bus 停在 150），云海卡和 GateCloudDeck 会在窗外下方 150 m 处继续铺开，Exp 0.0035 下只吃掉约 41%；平面远侧的巨像、群臂（距离 1.1–5.6 km）、远潮，在 2.4 km 以内的部分会出现在门内，挡在光唇之间；Tear_Lens 和翻卷布的背面也会露出来。§6·4c 写明门内是暗的、只有布和雾，“要避免：前方出现触手”。穹（r 2.4 km）只挡住更远的东西和天空盒，挡不住 150 m 处的云海。

**建议**：做成双向门户。门那边所有 shader（TentacleSway、Tide、GateCloudDeck、云卡、Tear）在相机 z > _Udon_InsidePortal 时，丢掉世界 z > portal 的部分：整个物体都在远侧的，在顶点阶段塌缩，代价为零；跨平面的云海按像素 clip。或者在本地头部过平面那一帧，由 Udon 关掉远侧的门 renderer，云海另做按像素 clip。这一条要写进 给总控.md，交给门（私密对话）去改。另外写清回头看 LIP1 开口时看见什么：门的天还是穹的雾色。

## [tech / blocker] LIP1 的净空被新加的毛边吃掉：撕边到路径约 75 m，毛边 1–4% H = 10–40 m
表里 LIP1 写的是“由门决定”，§2 的净空约束也把第 1 重排除在外。用 tear_def.lips() 算车的进入高度（云顶以上 150 m，套件 README §3 写的是 15%，设计稿写 14%，两处不一致）：左唇在 −75 m，右唇在 +86 m。设计稿给每一重都加了向开口里伸 1–4% H 的毛边，H = 1000 时就是 10–40 m，最坏情况毛边尖离路径约 35 m。§1.8 要求 v ≤ 1.05·d，59 m/s 下需要 ≥ 61 m（按设计稿自己的 max(40, v/1.05+5) 算）；35 m 时 v/d ≈ 1.7。

**建议**：让 inside_layout.py 也对 LIP1 跑净空检查，并且把门自己的 Tear 纤维、翻卷布、拉链纱都算进去。LIP1 的毛边限制在 ≤ (75 − 61 − 1.05) ≈ 12 m（约 1.2% H），或者只在离路径 > 120 m 的那段边上加毛边。进入高度的 14% / 15% 统一成一个数，写进 InsideLayout.json。

## [tech / blocker] 袖的 12 层光唇在周边视野里形成 1.6–2.4 Hz 的闪烁
§4：袖是 12 层亮唇（瓶覗色唇辉加毛边，luma 200+），层距 6.5–8 m，层与层之间是暗的 #1A2030 断面。车速 15.5 → 12.4 m/s，侧向约 60–70 m、方位 40–90° 的任何一块 4.4° 区域，每 0.42–0.65 s 就有一道亮环经过：亮暗交替、对比远超 0.10、暗态 < 0.80。这就是 §1.8 定义的闪烁，频率 1.6–2.4 次/秒，超过“任意 1 秒内最多 2 次”。而且这段正落在“唯一授权闪光”之前、Urlicht 最响的那一句里。

**建议**：任选一种或组合：(a) 只让入口层和出口层的唇亮，内部各层唇辉相对相邻断面的亮度差 < 10%，连续的“书页毛边”感靠低对比的纤维纹理来做，不靠逐层发光；(b) 把层距加大到 ≥ 0.55 s × v（15.5 m/s 时 ≥ 8.5 m，层数相应减少）。然后用 flashcheck.py 在 60 fps 下核对 224–231 s，看正前、左右 60° 和 90° 各一遍，结果写进 README。

## [tech / major] U9 之后 GateRoot 仍以恒速 v_g 前进，InsideRoot 在减速，两者分开
门 README §2：GateRoot.z = 59.0164·(179.55 − t)，没有终点。DESIGN §1：InsideRoot = (0, 0, −s(t))，s 在减速。按积分算，两者的差在 U9 + 5 s 是 1.9 m，+10 s 是 14.5 m，+20 s 是 104 m。结果是门的 Tear（透镜、翻卷布、纤维）和 LIP1 的“内面”布分家，回头看能看出来，_Udon_InsidePortal 也会有两个来源。

**建议**：约定 t ≥ U9 时 GateRoot.z = −s(t)，由门内驱动写，或者由门的驱动调用同一个闭式 s(t)。portal 的 z 只从一处来（InsideRoot 原点），写进 给总控.md 和门的 README。

## [tech / major] 雾、环境光、主光和 LB_Journey 抢着写；雾密度在 U9 的变法没写
FromLocal/code/timeline_v1/LB_Journey.cs 的 S_INSIDE 分支每帧都写 RenderSettings.fogDensity（在 U9 硬切到 0.0035）、fogColor（线性从 #2A3347 到 #6E808D）、ambientLight（平的，= fogC×0.8）和 sun.intensity。DESIGN §3、§6 要的是按区换色（Lab 插值，4 s smoothstep）、Trilight、主光 0.001。哪一个最后写，取决于 Udon 的执行顺序，两边会互相覆盖。另外，设计稿没写雾密度怎么从 0.0006 变到 0.0035：§1.6 规定 2–6 秒交叉，只有遮挡下才能硬切。U9 时后排的人和回头看的人还看得见门，所以不是遮挡。门的 shader 读的是同一个全局密度。

**建议**：在 给总控.md 里提出：门内驱动只报告雾色、密度、环境三色和主光强度，由分发层统一写一次（做法同 ΔEV），或者明确由分发层在 4c 时段压住 LB_Journey 的这几项。门内的 shader 用自己登记的 _Udon_InsideFogDensity / Color，不碰 RenderSettings 的密度，这样门的 shader 在过平面前后保持 0.0006 不跳；或者把密度在过平面前后 2–3 s 内爬升。和天空会话约定 LanbaiFog 的 4c 参数组（雾带宽 0、颜色 = 区色）。

## [tech / major] 门户用片元丢弃会关掉 Early-Z，而且第 4 幕热点期间也在白算
“在相机还在裂口平面前面”这个条件，对一次绘制来说是一个统一值，但设计稿用片元 discard 来做。后果有两个：(1) 所有 Sheet、袖的层、穹（每个都接近全屏，2.2–2.4 km）在整整 69 s 里都没有 Early-Z，8–20 层不透明的纤维噪声全部着色；(2) U9 之前 InsideRoot 已经激活（§1.9：根物体只在遮挡下开关，U9 没有遮挡），每帧要光栅化几个全屏，再全部丢掉，而这段正是第 4 幕 ≈ 7.1 ms 的热点。另外，用每只眼自己的相机位置判断，歪头时两只眼会有一帧一只在里、一只在外。还有，过平面那一帧，门的透镜平面可能被近裁面切掉，露出一帧平面后面的东西。

**建议**：在顶点阶段判断，不满足就把顶点塌缩到 float4(2,2,2,1)（Tear 的 _DepthPrepass 用的就是这个办法），片元里不写 discard。条件用 LanbaiCentreEyePos()，两只眼同一帧切换。阈值提前一点（portalZ − 0.7 m，约等于一帧行程加近裁面），门的透镜在这一帧之前一直保留。同样的条件也写进 ShadowCaster pass。

## [tech / major] ShadowCaster 和深度图没交代：大布、穹会污染深度图或投影
§1.6 规定常开一盏带阴影的世界主光，_CameraDepthTexture 是用各物体的 ShadowCaster pass 画出来的。如果门内的 shader 带 ShadowCaster，但没做门户剔除：U9 之前门内的布就会进入第 4 幕的深度图，门的光束 40 m 软淡、云卡软粒子会被它们截断；穹（r 2.4 km，包住车）如果投影，会把整个车厢罩进阴影，还会把级联的包围盒撑大。如果 shader 不带 ShadowCaster：毛边就不能用深度软淡。

**建议**：所有门内 renderer 都设 Cast Shadows Off、Receive Off。穹和 Sheet 不写 ShadowCaster pass（毛边如果需要软淡，就用 SOFTPARTICLES_ON 的退路）；如果要写，就和主 pass 一样做顶点阶段的门户塌缩。这几条写进 README 的导入和搭建清单。

## [tech / major] U9 这一秒里亮度台阶叠加，闪烁计数没核
门 README §10：U9 − 4 时“挡风玻璃仍是平的白”（APL 56）。过平面那一帧，画面一下子变成门内的暗（雾 #1D2336，APL 约 30），这本身就是一次相对亮度变化 ≫ 0.10。同一秒里还有：管灯一闪（+0.3 EV、0.2 s，然后 0.25 s 内灭，§6.x #12）、天窗光斑在 0.25 s 内灭（地板那块区域）、180.15 的车厢光带（亮起再落下）。179.55–180.55 这一秒的变化顺序是 升、降、降、升，在同一块区域里正好碰到“≤ 2 次/秒”的上限，前排和后排还差 0.05 s。设计稿把光带推迟到 180.15，却没把过平面这一步算进去。

**建议**：用 flashcheck.py 核对 179.0–181.5 s（正前、抬头看天窗、低头看过道），并把结果写进 README。如果不通过：过平面后的近处雾先保持亮，在 1–1.5 s 内退暗（相当于“白变薄”）；或者请门在 U9 前最后 1 s 先把透镜的白压暗。光带 180.15 的时刻要以测出来的结果为准。

## [tech / major] 没有第 4c 幕的 §1.9 预算；袖的毛边会超过每像素 8 层；LOD 的写法行不通
设计稿里没有 FSE 表，也没有 ms 估计。几个问题：(1) R_Gate 按 §6·5 要到 248.64 才关，69 s 里门（约 7 ms 级）一直和 InsideRoot 叠着渲染；(2) 从袖口沿轴往里看，12 层叠加毛边在开口边缘的那一圈里一层压一层，超过 §1.9“任一像素 ≤ 8 层”；(3) 每一重都有 Fringe 和 Threads，还有 90 根丝线，车厢玻璃 0.7 FSE 每一幕都要算进去；(4) “最近两重之外 LOD”对半径 2.2 km、包围盒包住相机的大布不起作用，屏幕高度永远 > 100%，LODGroup 不会切换。

**建议**：做一张 FSE 和 ms 表（帧取 LIP2、LIP4、LIP8 入口、LIP8 中段、U12），做法照门的 gate_fse.py。门的 renderer 在离车 ≥ 1.5 km（Exp 0.0035 下 ≥ 99.5% 被雾吃掉，约 U9 + 28 s）以后就关，这时看不见，不违反只在遮挡下开关的规则。每一重的 Sheet 拆成两个网格：撕边附近的细节带（可以做 LOD、按距离开关）和粗的外环。袖只给离相机最近的 ≤ 6 层加毛边，用脚本统计每个像素的层数。

## [tech / major] “回头：触手停在第一道光唇前、指尖卷回去”没人负责
§6·4c 构图的最后一条要求回头时看见这个画面，但 DESIGN 里没有对应的部分。门那边的动画只做到 U9 + 2（后窗组 lean），之后没有。与此同时，回头看 LIP1 开口时：穹会挡住 2.4 km 以外的门的天和远处的东西；在 0.0035 的雾里，600 m 处的触手已被吃掉约 88%；门的 shader 用的雾色是光雾带色，不是门内的区色，触手会读成颜色不对的鬼影。

**建议**：在 给总控.md 里分工：谁做指尖卷回的动画（门的实例加 U9 → U9 + 6 的 track 或 curl 曲线），在门内驱动的哪段时间窗里运行；回头时门的物体用哪个雾色、哪个密度（和上面雾的那一条一起定）；穹在 LIP1 开口方向上是否让开。

## [tech / minor] 天窗光斑：核心点的公式漏了偏移和旋转；Mesh.vertices 这条路不必走
§9 写的是“GateRoot 位置 + Tear_Root 缩放 × 本地核心点”，漏了 Tear_Root 的 localPosition (0, −150, 0) 和 localEulerAngles (0, 180, 0)：x 镜像、z 取反。Udon 的 Mesh 是能写 vertices 的，但要先实例化网格、每帧调 RecalculateBounds。“4 个子 Transform”这条退路，最后还是要由 Udon 用 MPB 把 4 个点推给 shader。在 U# 里再写一遍 PCHIP 的 H(t)，也有可能和门的实现跑偏。强度包络写的是“0 → 最亮”，没写形状。

**建议**：直接用 gateTearRoot.TransformPoint(核心本地点)，或者读门每帧已经写好的 _Udon_TearPos。投影放进顶点 shader：单位方块的 4 个顶点按 uv 索引角点，用天窗四角常量和全局核心点算出落点，网格在搭建时把 bounds 设大。这样不需要任何 Udon 网格操作。和 skylight_spot.samples 的 25 个采样逐点核对（≤ 1 cm）保留。包络改成 EV 线性。

## [tech / minor] 填色按 S4c 解，但 LIP1–3 的光带和区 1–2 的雾发生在 S4 → S4c 的交叉淡化里
S4 → S4c 在 180.05 → 188.05（§6.x #13）。设计稿里光带强度“座椅顶 ≤ luma 120（S4c 下）”、雾填值、Lab 屏幕插值都是按 S4c 算的，前三重的读数会偏。Udon 也没法每帧做调色的反运算。

**建议**：inside_layout.py 按每个时刻实际混合后的调色，预先算出填值表（线性 rgb 对时间），写进 InsideLayout.json，Udon 只做查表插值。

## [tech / minor] 暖白点的视线约束只看主座位，也没把横纱算进去
§2 的视线约束只从 cameras.U7 的眼位检查，只检查“布边”。横纱（2–5 根）横跨在开口里，可能从暖白点前面扫过，造成一闪一闪的遮挡。其他座位和站着的人的眼位也没核。横纱本身也没做净空检查。

**建议**：把视线约束扩展到车厢里所有眼位的包络（各座位，y 1.1–1.9），横纱也当作遮挡物算进射线检查；对横纱也跑 v ≤ 1.05·d 的净空检查。

## [tech / minor] 加色部件的雾、渲染队列、包围盒
加色的毛边、暖白点、光柱如果按常规雾混向雾色，远处会发出雾色的光，应该雾向黑。暖白点、毛边的队列必须在遮罩球之前，否则会在全黑的第 5 幕里透出来。90 根丝线和其他顶点动画的网格，包围盒不加大会被视锥剔除。另外，0.4–1.5 cm 粗的丝线在 3–25 m 外只有约 0.03–0.3 px，按覆盖率缩放后基本看不见。

**建议**：加色部件用 UNITY_APPLY_FOG_COLOR(c, 0)；所有门内透明部件的队列都低于 Lanbai_Overlay；搭建脚本把顶点动画网格的 bounds 设大；丝线要么加粗，要么接受它“几乎看不见”，并在 README 里写明。

## [tech / minor] 246.39 “一切停止变化”，可世界仍以 12 m/s 前进
s(t) 从 2077.5 m 继续走到 2104.5 m。从 12 m/s 到停，在 ≥ 4 s 内做 smoothstep，峰值 4.5 m/s²，超过 §1.8 的 1.5 m/s²，所以确实停不下来。往前看没有东西，运动看不出；回头时，LIP8 的袖在 185–212 m 外慢慢后退（雾约 50%）。这和 §1.8、§6·5 字面上的“闪光前 1.5 s 内不许有任何变化”不一致。

**建议**：在 README 里写明这一点，并说明往前看什么都不动、只有回头能看出后退；或者在 246.39 以后把 LIP8 及之后的 renderer 关掉，这时它已被雾吃掉约 50%，关掉会被看见，所以更稳的做法是让布局保证 246.39 时最后一重已经 ≥ 99% 被雾吃掉。

## [tech / minor] 第 5 幕的测试和接口缺口
第 5 幕要用 Lanbai_Overlay v2，而它属于包 2 还没开始，包 1 没法单独测试。§1.8 要求的 VR 峰值 APL 检查（> 150 就降 ΔEV）没写进流程。_Udon_InsidePortal、_Udon_CabinSlice、_Udon_CabinSliceColor、_Udon_RadioDial 还没在 Common/UdonGlobals.md 登记。

**建议**：包 1 和包 2 一起交，或者先给一个最小的遮罩球用来测试。README 的截图协议里加上 247.5–248.7 的 VR APL 测量。新的全局量写进 给总控.md 请求登记，并注明 _Udon_CabinSlice 各分量的语义归车厢 shader 的负责人（总控）确认。

## [bible / blocker] U9 交接：雾、环境光、Trilight、主光从第 4 幕的值怎么过渡到 4c 的值，设计稿没写
设计 §3 和 §6 只写了 4c 自己的目标值：Exp 0.0035，区雾色，_Udon_CabinAmbient #B5C3DB×0.30，Trilight #3D4863/#4C5979/#1F283B，主光 →0.001。它没写这些量从门的状态出发，在什么时刻、用多长、什么曲线变过去。门的状态是：光雾带 0.0006 加上 LanbaiGateSky 方向雾色，环境 月#232A3A×0.3（§4.8 表），月光平行光 E 1.0（Gate README §6）。门内入口靠 portal 逐像素切换，所以这些全局量如果不另行规定，就会在 U9 那一帧硬切。§1.6 规定：雾色与密度 2–6 秒交叉，永不硬切（遮挡下除外）。U9 不在遮挡下。环境光 #232A3A→#B5C3DB 是让车厢变亮约 2+ EV，要受 §1.8 爬升律约束；它还和 U9 管灯一闪（§6.x #12）、第 1 重光带（180.15）落在同一秒，会让闪烁计数超过 2 次/秒。另外，设计稿没说这些雾要通过 LanbaiFog.cginc 的“幕参数组”来算，也没说 RenderSettings.fog 不切换（§1.6，CONTROL §3/§4）。

**建议**：加一节“U9 交接表”，逐项写清：雾密度 0.0006→0.0035，雾色从 LanbaiGateSky 到区 1 #1D2336，_Udon_CabinAmbient、Trilight 三色、主光 E 1.0→0.001。每项给出起止时刻和曲线：smoothstep 2–6 s；变暗的项可以和 S4→S4c 一起走 180.05→188.05；变亮的环境光要错开 179.55–181.35 的管灯一闪和第 1 重光带，并按 0.25/1/2 s 窗口核对爬升律。明确写：所有自定义 shader 走 LanbaiFog.cginc，第 4c 幕作为一个参数组；RenderSettings.fogColor 和密度同步写；fog 开关永不切换。把 U9±3 s 纳入 flashcheck 录像窗 (b) 一起验收。

## [bible / blocker] “同时看得见的光唇 ≤ 3 重”这条检查按设计自己的 s 值和雾必然失败
设计 §2 要求布局脚本每秒数一次：第 4 重往后都 ≥ 90%，不满足就报错。s_k 由标签和速度积分固定（§1 已核对），雾 0.0035 也固定，90% 落在 658 m。重算结果：t≈201.6–202.4（U11 前约 0.8 s），前方 658 m 内有 4 重（第 5、6、7、8 重），第 8 重袖口在约 609–650 m 处，雾只有约 88%。脚本按规格必然报错，而且解不出来，因为几何没有可调的自由度。圣经 §6·4c 构图写的是“雾 Exp 0.0035……座位上同时看得见的光唇 ≤ 3 重”。

**建议**：把“看得见”定义成可算的量，例如：不计正在穿越（距离 < 某 m）的那一重；或者阈值按光唇屏幕亮度对雾色的对比 ≤ 若干码，而不是固定的 90%。如果坚持字面阈值，就把这 0.8 s 的例外写进 README 和 给总控.md，请总控在圣经里注明。不能改雾密度，0.0035 是圣经定值。

## [bible / major] 第 4→5 重旋转同号，违反“相邻两重旋转不同号”
设计 §2 表的旋转是：第 4 重 +30°，第 5 重 +8°，同为正号。圣经 §6·4c 构图要求：相邻两重不用同一种网格、旋转不同号。设计 §2 的约束列表也写了这条，表格却自相矛盾。第 1 重写成“0（=裂口轴斜 4°）”，实际有 4° 的倾斜，符号不明确；它可能和第 2 重的 +12° 同号。

**建议**：把第 5 重改成负号，例如 −8°；然后检查第 6 重 −30° 的符号，可以把第 6 重翻成正号，或者第 5 重取 −8°、第 6 重改 +30°，保证整个序列严格交替。给第 1 重的 4° 写明符号约定（裂口顶端右倾，对应 + 还是 −），并让第 2 重取相反符号。

## [bible / major] 第 8 重（以及第 4、7 重）的起点数值和净空 ≥ 40 m 互相矛盾
圣经 §6·4c 要求路径离每一重的边 ≥ 40 m。设计又把要求收紧为 ≥ max(40, v/1.05+5)，含纤维毛边的尖。按设计自己的开口规格估算：第 8 重 H 195，袖用破洞轮廓，最小直径 0.7H，半径约 68 m，偏移 (+40,+30) 离中心 50 m，净空约 18 m；再减毛边 2–8 m、层间中心抖动 ±6 m、形心漂移 ≥ 10 m，就接近 0。即使取最大直径 0.95H，也只有约 42 m 减毛边，仍不到 40 m。第 4 重：最小半径 184 m，偏移 156 m，净空约 28 m 再减毛边 5–21 m。第 7 重：分叉口半宽 78–88 m，|x| 45 m，净空约 33–43 m 再减毛边。设计说“数值是起点、求解器会核对”，但第 8 重的偏移下限（|x| ≥ 40、|y| ≥ 30，即离中心 ≥ 50 m）和它的开口尺寸在规格内根本不可兼得。

**建议**：第 8 重：把开口最小直径提到 ≥ 0.9H 并限制袖层抖动，或者把偏移降到范围下限并接受“只按一个轴偏”（如 (+40, 0)）。这需要圣经允许纵向 |y| < 30，要写进 给总控.md。第 4、7 重先按“半宽 − |偏移| − 毛边 ≥ 净空”反解偏移上限，再填表，不要让求解器从必败的起点开始。

## [bible / major] 第 8 重框住暖白点：§2 和 §4 互相矛盾，“偏左上”与偏移方向也矛盾
设计 §2：穿越前 6 秒，第 8 重开口边在暖白点四周都在 8° 以内（要求紧框）。设计 §4：四周离边 ≥ 8°（要求留余量）。两条方向相反。几何上，−6 s（t=218.75）车离袖口约 108 m，开口最小半径 68 m 对应角半径约 32°，“边都在 8° 以内”做不到。另外，暖白点在方位 −2.0°、仰角 +1.2°；袖口中心偏移 (+40,+30)，在 108 m 处约为右 20°、上 14°。所以暖白点在开口中心的左下，不是 §4 写的左上（三分线）。距中心约 25°，离边约 7°，已不到 8°。圣经 §6·4c 的要求只是：只有第 8 重的开口从主座位正好框住前方的暖白点。

**建议**：统一成一条：例如“穿越前 6 s，暖白点在第 8 重开口内，离边 ≥ 8°，位于开口中心的左上象限”。为此把第 8 重偏移改成右下，例如 (+40, −30)，或者把暖白点仰角调高；然后和上一条的净空一起重解。写明“框住”在哪个时刻、按哪个距离计算。

## [bible / major] 回头看见什么、门的根物体 U9 之后怎么走，设计稿没写（圣经要求触手在第一道光唇前卷回去）
圣经 §6·4c 构图和表格 U9 行要求：回头时，触手伸进第一道光唇就停住，指尖卷回去，它们跟不进来。Gate README 没有这一段：GateRoot 的公式只定义到 t ≤ U9，速度恒为 59.0164 m/s；抓点的 track 只到 U9 − 1。设计把第 1 重定为“裂口本身的内面”，放在 InsideRoot 里，InsideRoot 按 −s(t) 减速。如果门不跟着改，U9 之后门（Tear_Lens、触手、后窗组）会继续以 59 m/s 退去，和第 1 重分离。设计也没说从里面回看时 Tear_Lens 背面、门的云海和触手怎么显示，以及哪些在穹（2.4 km、写深度）里面照常画。§6.x #17 的 R_Gate 关、R_Dawn 开，设计 §8 只写了 InsideRoot 关。

**建议**：规定 U9 起 GateRoot.position = (0,0,−s(t))，和 InsideRoot 同一条曲线，或者由 4c 驱动接管门的位置。给“指尖卷回”定一个负责方和动画：指尖贴在第 1 重唇后、U9→U9+3 s 卷回，作为门包的补丁写进 给总控.md。写明回看时 Tear_Lens 背面剔除，或画成第 1 重布的内面。剪 1 时由谁关 R_Gate、开 R_Dawn，要写进接口。

## [bible / major] 袖 12 层毛边叠加会超过“任一像素 ≤ 8 层”，4c 也没有性能预算
设计 §4：袖是 12 层布，每层都有唇辉和毛边（§2 规定毛边是透明加色）。从主座位看进袖里，12 圈毛边加上其余光唇的毛边、横纱，再加车厢玻璃，会在同一些像素上叠层。圣经 §1.9 要求：任一像素 ≤ 8 层，透明持续 ≤ 4 FSE（含车厢玻璃 0.7）。另外，R_Gate 在整个 4c 期间仍开着（§6.x #17 才在 248.64 关），第 4 幕本身约 7.1 ms。设计没给 4c 的 ms/FSE 预算。圣经 §6·4c 做法要求“最近两重之外 LOD”，设计也没写。

**建议**：袖只在入口层和出口层画透明毛边，中间层改成 alpha-test 或不透明的“断面”；或者把 12 层毛边合进一个 pass，并按深度限层。加一张 4c 的预算表：几何、透明 FSE、最大叠层、门在 4c 期间还有哪些部件开着；写明 LOD 规则（最近两重之外用 LOD）。按 §8.2 第 10 条把 4c 列入 perf.md 的实测项。

## [bible / minor] 雾的换区窗口有重叠，第 1 区在 U9 之前就开始变
设计 §3：换区从穿越前 1.5 s 到穿越后 2.5 s，用 4 s smoothstep。按这个规则，第 1 重（179.55）的窗口是 178.05–182.05，起点在门里，会把门的雾提前改掉。第 2 重 181.4–185.4 和第 3 重 184.45–188.45 两两重叠，没定义叠加方式。圣经 §1.6 要求 2–6 s 交叉，永不硬切。

**建议**：区 1 的雾由“U9 交接”那条曲线负责，不套这个通用规则。对相邻且重叠的窗口，写成按 s 的单一连续函数（例如按 s 做 PCHIP 插值），不要写成多个 smoothstep 分段。

## [bible / minor] 表盘熄灭的时刻在设计里写了两个，而且可能和闪光组成反向变化
设计 §6 写“247.89 起随闪光熄灭”，§8 写“248.64（剪 1）……表盘熄灭”。如果表盘在 247.89–248.29 熄灭，而同时全画面 +1.5 EV 在升，表盘所在的 4.4° 区域会先升后降或先降后升，可能多出一次闪烁（§1.8）。圣经 §6·5 和 §6.x #16 写的是：在闪光中熄灭，永不再亮。

**建议**：只保留一个定义。建议让表盘发光随黑遮罩一起在 248.39→248.64 降到 0，让它所在区域的亮度单调；或者在 247.89 起让它的发光乘 2^(−ΔEV)，保持屏幕亮度不变，然后在遮罩下归零。用 flashcheck 核对表盘区域。

## [bible / minor] 表盘填值：圣经已给出，设计却写“在 S4c 下解出”
圣经 §4.4 表给了：4c 提亮一档后屏幕 #F2B169，填 #FF7B00 @ +2.13，×T0 1.66（S4c 下能达到的最饱和值，附录 C 可行 m-3）。设计 §6 写“填值在 S4c 下解出”，有重新求解、得出另一个值的风险。

**建议**：直接写入 #FF7B00 @ +2.13（×T0 1.66），在 S4c 下核对能否达到 #F2B169。

## [bible / minor] 光唇的填值和亮度区间、暗车厢剪影、最后一帧裂口之光都没有写进设计
圣经 §6·4c 大气：光唇与纤维本身 luma 200–235，填值第 1 重 #DFCFFF @ +1.96、第 4 重 #CBD8FF @ +1.78、第 8 重 #BCEAFF @ +1.29。色板：暗车厢剪影 #0C0E14。§6·5 色板：最后一帧裂口之光 #F5F2EC。设计只给了屏幕色，没给填值，没给 luma 上下限，也没说加色毛边叠在唇辉上之后不超过 235。CONTROL §6.13 要求：每个数都写进 JSON 或 README。

**建议**：在 InsideLayout.json 和 README 里写入三个填值和插值规则、luma 200–235 的验收，以及 #0C0E14 和 #F5F2EC 的验收帧（例如 248.39 的正前方）。

## [bible / minor] 第 8 重“一升一降相隔约 6 秒”对任何座位都不成立
设计 §6：2.4 s 扫进，停 1.45 s，2.4 s 扫出，共 6.25 s。对一个固定座位，从被照亮到变暗大约 3.4–3.9 s（前排座位在约 225.2 亮、约 228.6 暗），不是 6 s。圣经 §6·4c 和 §6.x #14a 写“一升一降相隔 6 秒”，同时又写“进 2.4 s · 保持 · 出 2.4 s，共 6.25 s”，圣经自己也有歧义。设计照抄了“约 6 秒”，但按它自己的数算不出来。

**建议**：把扫出改成从车尾向车头退，这样前排的亮持续约 6 s；或者把文字改成“每个座位亮 ≥ 3.4 s，升降间隔 > 1 s，不成闪烁对”。把这个歧义写进 给总控.md。

## [bible / minor] “最后 0.3 秒光唇形状保持明亮、黑场保持空（残像）”被遗漏
圣经 §6·5 构图/光写道：最后 0.3 秒让光唇的形状保持明亮而黑场保持空，眼睛会自己画出一个残像。设计 §8 只有均匀的 EvOverlayAlpha 黑遮罩，没有处理这一句，也没说明为什么不做。

**建议**：二选一，写进设计。（a）在 248.34–248.64 期间，遮罩在光唇和暖白点区域晚 0.1–0.15 s 才盖满（按世界方向，不锁屏），并用 flashcheck 核对。（b）认定这句话描述的是生理上的残像，不需要实现，写进 给总控.md 请总控确认。

## [bible / minor] 246.39 的“一切停止变化”和世界仍以 12 m/s 移动矛盾
设计 §1 规定 v=12 m/s 一直到 U12；§8 说 246.39 一切停止变化。在 246.39 时，第 8 重袖离车后约 185 m，雾吃掉约 48%，从后窗看得见，它在 246.39–248.64 期间还在后退约 27 m。圣经 §1.8 和 §6·5 要求：闪光之前 1.5 秒内不许有任何其他变化。

**建议**：在 246.39 冻结 InsideRoot 的位置（v 在之前已经是常数，冻结只是不再移动后方已经远去的布，不算速度变化）；或者在 246.39 前把后方各重淡进雾里，并说明理由。

## [bible / minor] 驱动接口、InsideRoot 的激活时刻、#12/#13 归谁负责，都没写
CONTROL §5 要求每个驱动提供 LanbaiTick / LanbaiActivate / LanbaiWindow；§1.9 和 CONTROL §5 要求根物体只在遮挡下开关。设计 §8 引入了新接口 LanbaiDeltaEV(t)，但没写这三个标准方法，也没写 InsideRoot 什么时候激活（portal 能让它提前开着，但要在遮挡下打开，例如 U6−20 在白云中和 GateRoot 一起）。§6.x #12（U9 管灯 150% 一闪，EXPO_UP +0.3，w 0.062）和 #13（S4→S4c 180.05→188.05）由谁驱动、由谁报告 ΔEV，没写。第 5 幕“遮罩后面的一切渲染器关闭”：90 根丝线和暖白点如果在车坐标里、不挂在 InsideRoot 下，设计没说怎么关。新的全局量 _Udon_InsidePortal / _Udon_CabinSlice / _Udon_RadioDial 也要先在 Common/UdonGlobals.md 登记。

**建议**：补上三个标准方法和时间窗（含预热）、InsideRoot 的激活时刻（在遮挡下）、#12/#13 的负责方（写进 给总控.md）、248.64 要关掉的全部渲染器清单，以及全局量的登记申请。

## [bible / minor] 数值小错：进入高度 14%，v_g 常数
设计 §2 第 1 重写“车在透镜约 14% 高度进入”。Gate README §1 规定进入点在云顶以上 150 m，H(U9)=1000，Tear README §3 表写“进入（15% 高）”。设计 §1 用 59.02，门用 59.0164；设计又写 t<U9 时“和门同速”，两个常数在 U9 有微小的速度跳变，数值不同。CONTROL §3 要求时刻和速度从 cues.json 读，不写死；设计里 180.15、196.1、246.39 等都是写死的数字。

**建议**：改成 15%。v_g 统一从 cues.json 读，门和 4c 用同一个值；时刻写成标签表达式（U9+0.6、U12−2.25、ein Lichtchen 子标签等）。

## [bible / minor] 天窗光斑细节和门的 JSON 不一致或缺失
设计 §9 写“地板凸点 × 0.4”，GateLayout_v2.json skylight_spot.note 写的是透镜 0.35→1.0 × (0.86 + 0.14 凸点)。JSON 的 25 个采样只到 178.15，178.15→179.55 没有核对点。强度包络只定了 U8=0、169.2 最亮、U9 熄灭，169.2→U9 之间的曲线没定义（圣经 §6·4 表：U8–U9，≈169.2 最亮）。U9 熄灭时它和管灯一闪、portal 切换、第 1 重光带落在同一秒，没有闪烁核对。尘粒尺寸没写（Gate README §8.3：0.7–1.4 mm，只在光柱里，越靠近天窗越密）。

**建议**：按 JSON 改成 0.86+0.14 凸点和 0.35 透镜底；178.15 之后用闭式投影，在 179.55 加一个核对点；写出 169.2→U9 的包络（例如 smoothstep 衰减到 0.6，再在 0.25 s 内灭）；把 U9 一秒窗口列入 flashcheck；补上尘粒参数。

## [bible / minor] 闪光的 VR 峰值保护和验收帧没写
圣经 §1.8 和附录 B：仿真测试帧是第 5 重（APL 34→59）；4c 末 APL 55，峰值 APL 83–95；如果实测 VR 峰值 APL > 150，ΔEV 降到正好 150。§2.2 写 APL 30→55、EV −1.6→+0.3。设计 §8 只写了 +1.5 EV 曲线：没有 APL 检查点，没有第 5 重测试帧，没有 VR 下的回退。黑遮罩球的规格也没写（跟随每个人的头，r 1.5 m，§1.8 和 §6·5）。

**建议**：写入：参考渲染在第 5 重测试帧（202.4）和 246.39 量 APL（目标 34 和 55）；闪光峰值验收 ≤ 150，超过就按公式降 ΔEV；黑遮罩使用 Overlay v2 的跟头球，r 1.5 m。
